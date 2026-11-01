"""Prepare operator-supplied X2D FFF or calibrated Bayer DNG for the offline demo.

Optional host dependencies: rawpy, numpy, tifffile. No demosaicing or CNN is
used here. FFF requires a same-model reference DNG/GPR for camera color tags;
FFF supplies per-shot WB, black/white, crop and orientation. Manufacturer lens
correction/opcode processing is not reconstructed by that FFF adapter.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys


def prepare(inputs, output, gpr_source, reference=None, fps=24):
    import numpy as np
    import rawpy
    import tifffile

    sys.path.insert(0, str(Path(gpr_source).resolve() / "tools"))
    import raw_media as media
    import stock_crop

    if not inputs or not 0 < fps <= 240:
        raise ValueError("requires inputs and an integer rate in 1..240")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    color_codes = {
        271,
        272,
        50706,
        50707,
        50708,
        50710,
        50711,
        50718,
        50721,
        50722,
        50723,
        50724,
        50778,
        50779,
    }
    reference_meta = media.extract(reference, 16) if reference else None

    def words(code, values):
        return media.record(
            code, 4, len(values), struct.pack("<" + "I" * len(values), *values)
        )

    def numeric(tag):
        values = tag.value if isinstance(tag.value, (list, tuple)) else (tag.value,)
        kind = int(tag.dtype)
        if kind not in (3, 4, 5):
            raise ValueError("unsupported FFF calibration numeric type")
        return media.record(
            tag.code,
            kind,
            tag.count,
            struct.pack("<" + ("H" if kind == 3 else "I") * len(values), *values),
        )

    rows = []
    manifest = []
    for index, name in enumerate(inputs):
        path = Path(name)
        is_fff = path.suffix.lower() == ".fff"
        if is_fff:
            if reference_meta is None:
                raise ValueError("FFF requires --reference from the same camera model")
            tags = {t["code"]: t for t in reference_meta["image"]}
            if b"X2D 100C" not in media.unpack_record(tags[272]):
                raise ValueError("reference must identify X2D 100C")
            with tifffile.TiffFile(path) as file:
                parent = file.pages[0]
                if parent.tags["Model"].value != "X2D 100C":
                    raise ValueError("FFF adapter is verified only for X2D 100C")
                sensor = next(
                    page for page in parent.pages if page.photometric == 32803
                )
                calibration = [
                    numeric(sensor.tags[50714]),
                    numeric(sensor.tags[50717]),
                    numeric(parent.tags[50728]),
                    numeric(parent.tags[50727]),
                ]
                crop_origin = tuple(sensor.tags[50719].value)
                crop_size = tuple(sensor.tags[50720].value)
                orientation = int(parent.tags[274].value)
        elif path.suffix.lower() in (".dng", ".gpr"):
            if path.suffix.lower() == ".gpr":
                raise ValueError(
                    "use uncompressed sensor input, not an already-lossy GPR"
                )
            meta = media.extract(path, 16)
        else:
            raise ValueError("input must be X2D FFF or calibrated Bayer DNG")
        with rawpy.imread(str(path)) as raw:
            if is_fff:
                pixels = raw.raw_image_visible
                phase = "".join(
                    chr(raw.color_desc[int(i)])
                    for i in raw.raw_colors_visible[:2, :2].flat
                )
                if phase != "RGGB":
                    raise ValueError("demo requires RGGB")
                h, w = pixels.shape
                origin = (
                    crop_origin[0] - raw.sizes.left_margin,
                    crop_origin[1] - raw.sizes.top_margin,
                )
                image = [
                    copy.deepcopy(t)
                    for t in reference_meta["image"]
                    if t["code"] in color_codes
                ]
                image += [
                    media.record(274, 3, 1, struct.pack("<H", orientation)),
                    media.record(33421, 3, 2, struct.pack("<2H", 2, 2)),
                    media.record(33422, 1, 4, bytes((0, 1, 1, 2))),
                    media.record(50713, 3, 2, struct.pack("<2H", 1, 1)),
                    *calibration,
                    words(50829, (0, 0, h, w)),
                    words(50719, origin),
                    words(50720, crop_size),
                ]
                meta = dict(
                    schema=media.SCHEMA,
                    width=w,
                    height=h,
                    sample_bits=16,
                    cfa="RGGB",
                    image=image,
                    exif=[],
                    gps=[],
                )
            else:
                pixels = raw.raw_image
                if pixels.shape != (meta["height"], meta["width"]):
                    raise ValueError("LibRaw storage and DNG dimensions disagree")
                if meta["cfa"] != "RGGB":
                    raise ValueError("demo requires RGGB")
            if pixels.dtype != np.uint16:
                raise ValueError("requires uint16 sensor samples")
            meta, crop = stock_crop.aligned(meta)
            raw_path = output / f"{index:06d}.raw"
            pixels[: meta["height"], : meta["width"]].astype("<u2", copy=False).tofile(
                raw_path
            )
        frame = dict(
            raw_metadata=meta,
            source_kind="libraw_fff_sensor_samples"
            if is_fff
            else "libraw_dng_sensor_samples",
            calibration_source="reference color matrices plus per-shot FFF tags"
            if is_fff
            else "source_dng",
            calibration_limits="manufacturer lens/opcode processing not reproduced"
            if is_fff
            else "declared supported DNG tags",
            timestamp_source="synthetic_nominal_playback_rate",
        )
        meta_path = output / f"{index:06d}.json"
        meta_path.write_text(json.dumps(frame, separators=(",", ":")))
        manifest.append(
            f"{raw_path.name}\t{meta_path.name}\t{index * 1000000000 // fps}"
        )
        rows.append(
            dict(
                index=index,
                width=meta["width"],
                height=meta["height"],
                crop=crop,
                raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            )
        )
    if len({(r["width"], r["height"]) for r in rows}) != 1:
        raise ValueError("sequence dimensions differ")
    (output / "frames.tsv").write_text("\n".join(manifest) + "\n")
    (output / "preparation.json").write_text(
        json.dumps(dict(frames=rows, cnn=False, fps=fps), indent=2) + "\n"
    )
    return dict(
        frames=len(rows),
        width=rows[0]["width"],
        height=rows[0]["height"],
        cnn=False,
        fps=fps,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--reference", type=Path)
    p.add_argument("--gpr-source", required=True, type=Path)
    p.add_argument("--fps", type=int, default=24)
    print(json.dumps(prepare(**vars(p.parse_args()))))
