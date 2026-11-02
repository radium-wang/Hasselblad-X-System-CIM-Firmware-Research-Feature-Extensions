"""将 X2D FFF/3FR 转成原始像素 DNG 及有损 GPR；不需要外部颜色参考。"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from camera_trial import ensure_build, natural
from prepare import prepare


def check_metadata(media, expected, path):
    actual = media.extract(path, 16)
    for key in ("width", "height", "sample_bits", "cfa"):
        if expected[key] != actual[key]:
            raise ValueError("exported geometry/domain differs")
    for key in ("image", "exif", "gps"):
        if sorted(expected[key], key=lambda t: t["code"]) != sorted(
            actual[key], key=lambda t: t["code"]
        ):
            raise ValueError("exported typed calibration differs")


def main():
    import numpy as np
    import rawpy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+", help="X2D files or folders")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("both", "dng", "gpr"), default="both")
    parser.add_argument(
        "--reference", type=Path, help="Optional same-model color profile override"
    )
    parser.add_argument("--quality", type=int, choices=range(6), default=3)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--build", type=Path, help="Reuse a build of this module")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("limit must be 1..1000")
    files = []
    for source in args.inputs:
        if source.is_dir():
            files.extend(
                sorted(
                    (
                        p
                        for p in source.iterdir()
                        if p.is_file() and p.suffix.lower() in (".fff", ".3fr", ".dng")
                    ),
                    key=natural,
                )
            )
        elif source.is_file():
            files.append(source)
        else:
            parser.error("input does not exist: " + str(source))
    files = files[: args.limit]
    if not files:
        parser.error("no FFF/3FR/DNG input files")
    if args.reference is not None and not args.reference.is_file():
        parser.error("reference does not exist")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    build, gpr_source = ensure_build(root, args.build)
    prepared = root / "prepared"
    prepare(files, prepared, gpr_source, args.reference, 24)
    sys.path.insert(0, str(gpr_source / "tools"))
    import raw_media as media
    import stock_video

    rows = [
        line.split("\t") for line in (prepared / "frames.tsv").read_text().splitlines()
    ]
    exports = root / "frames"
    exports.mkdir()
    results = []
    for i, (raw_name, meta_name, _) in enumerate(rows):
        frame = json.loads((prepared / meta_name).read_text())
        meta = frame["raw_metadata"]
        result = dict(
            index=i,
            width=meta["width"],
            height=meta["height"],
            calibration_source=frame["calibration_source"],
            color_profile_kind=frame["color_profile_kind"],
        )
        if args.format in ("both", "dng"):
            path = exports / f"{i:06d}.dng"
            media.write(path, meta, (prepared / raw_name).read_bytes(), "dng")
            check_metadata(media, meta, path)
            reference = np.memmap(
                prepared / raw_name,
                dtype="<u2",
                mode="r",
                shape=(meta["height"], meta["width"]),
            )
            with rawpy.imread(str(path)) as raw:
                if not np.array_equal(raw.raw_image, reference):
                    raise ValueError("DNG sensor samples differ from prepared RAW")
            del reference
            result.update(
                dng=path.name,
                dng_samples_exact=True,
                dng_typed_calibration_verified=True,
            )
        results.append(result)
        if args.format != "gpr":
            print("Exported original-sample DNG", i + 1, "of", len(rows), flush=True)
    if args.format in ("both", "gpr"):
        meta = json.loads((prepared / rows[0][1]).read_text())["raw_metadata"]
        clip = root / "encoded.gvid"
        encoded = subprocess.run(
            [
                str(build / "gvid_raw_demo"),
                str(meta["width"]),
                str(meta["height"]),
                "16",
                str(args.quality),
                "24",
                str(prepared / "frames.tsv"),
                str(clip),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        (root / "encode.jsonl").write_text(encoded.stdout)
        count = 0
        with (
            clip.open("rb") as file,
            tempfile.TemporaryDirectory(dir=root) as temporary,
        ):
            temporary = Path(temporary)
            header = stock_video.read_header(file)
            for frame in stock_video.records(file, header):
                i = frame["index"]
                if i != count or i >= len(rows):
                    raise ValueError("unexpected frame index")
                expected = json.loads((prepared / rows[i][1]).read_text())
                if frame["metadata"] != expected or frame["pts_ns"] != int(rows[i][2]):
                    raise ValueError("frame metadata or timestamp differs")
                meta = frame["metadata"]["raw_metadata"]
                path = exports / f"{i:06d}.gpr"
                media.write(path, meta, frame["payload"], "gpr")
                check_metadata(media, meta, path)
                _, payload = media.extract(path, 16, with_payload=True)
                if payload != frame["payload"]:
                    raise ValueError("GPR VC-5 payload differs")
                vc5, decoded = temporary / "frame.vc5", temporary / "frame.raw"
                vc5.write_bytes(payload)
                subprocess.run(
                    [str(build / "gvid_decode_frame"), "16", str(vc5), str(decoded)],
                    check=True,
                    capture_output=True,
                )
                if decoded.stat().st_size != meta["width"] * meta["height"] * 2:
                    raise ValueError("native GPR decode sample count differs")
                results[i].update(
                    gpr=path.name,
                    gpr_lossy=True,
                    gpr_quality=args.quality,
                    gpr_native_decoded=True,
                    gpr_payload_and_typed_calibration_verified=True,
                )
                vc5.unlink()
                decoded.unlink()
                count += 1
                print("Verified lossy GPR", count, "of", len(rows), flush=True)
            if count != len(rows) or not header["_end_marker_verified"]:
                raise ValueError("incomplete encoded recording")
    receipt = dict(
        source_model="X2D 100C",
        frames=results,
        rawpy_version=rawpy.__version__,
        libraw_version=list(rawpy.libraw_version),
        cnn=False,
        original_dng_samples="unaltered after even-origin / multiple-of-eight alignment crop",
        color_limits="LibRaw model D65 profile or operator override; not Phocus rendering or new camera calibration",
        complete=True,
    )
    (root / "conversion.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Converted and verified", len(results), "frames:", exports)


if __name__ == "__main__":
    main()
