"""Non-CNN GVID extraction using the pinned dependency's container and DNG code."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(clip, output, decoder, gpr_source):
    sys.path.insert(0, str(Path(gpr_source).resolve() / "tools"))
    import raw_media
    import stock_video

    output = Path(output)
    with Path(clip).open("rb") as file:
        header = stock_video.read_header(file)
        if (header["version"], header["bayer"]) != (3, "RGGB"):
            raise ValueError("demo requires RGGB GVID v3")
        verified = []
        for frame in stock_video.records(file, header):
            meta = frame["metadata"]["raw_metadata"]
            raw_media.validate(meta, header)
            verified.append(
                (
                    frame["pts_ns"],
                    digest(frame["payload"]),
                    digest(json.dumps(meta, sort_keys=True).encode()),
                )
            )
        if not verified or not header["_end_marker_verified"]:
            raise ValueError("recording is incomplete")
        output.mkdir(parents=True, exist_ok=False)
        file.seek(0)
        header = stock_video.read_header(file)
        rows = []
        for frame in stock_video.records(file, header):
            i = frame["index"]
            meta = frame["metadata"]["raw_metadata"]
            raw_media.validate(meta, header)
            check = (
                frame["pts_ns"],
                digest(frame["payload"]),
                digest(json.dumps(meta, sort_keys=True).encode()),
            )
            if i >= len(verified) or check != verified[i]:
                raise ValueError("source changed after verification")
            stem = output / f"{i:06d}"
            vc5 = stem.with_suffix(".vc5")
            vc5.write_bytes(frame["payload"])
            raw_media.write(stem.with_suffix(".gpr"), meta, frame["payload"], "gpr")
            raw = stem.with_suffix(".raw")
            subprocess.run(
                [
                    str(Path(decoder).resolve()),
                    str(header["sample_bits"]),
                    str(vc5),
                    str(raw),
                ],
                check=True,
                capture_output=True,
            )
            if raw.stat().st_size != header["width"] * header["height"] * 2:
                raise ValueError("decoded sample count differs")
            raw_media.write(stem.with_suffix(".dng"), meta, raw.read_bytes(), "dng")
            restored = raw_media.extract(
                stem.with_suffix(".dng"), header["sample_bits"]
            )
            # Typed tag bytes, including crop, black/white and color matrices,
            # must survive packaging. This is not a lossless sensor-pixel claim.
            for key in ("width", "height", "sample_bits", "cfa"):
                if meta[key] != restored[key]:
                    raise ValueError("exported geometry/domain differs")
            for group in ("image", "exif", "gps"):
                if sorted(meta[group], key=lambda t: t["code"]) != sorted(
                    restored[group], key=lambda t: t["code"]
                ):
                    raise ValueError("exported calibration differs")
            rows.append(
                dict(
                    index=i,
                    pts_ns=frame["pts_ns"],
                    payload_sha256=check[1],
                    decoded_raw_sha256=digest(raw.read_bytes()),
                    calibration_preserved=True,
                )
            )
        if len(rows) != len(verified) or not header["_end_marker_verified"]:
            raise ValueError("second pass incomplete")
    result = dict(
        frames=rows,
        width=header["width"],
        height=header["height"],
        sample_bits=header["sample_bits"],
        fps_num=header["fps_num"],
        fps_den=header["fps_den"],
        cnn=False,
        end_marker_verified=True,
    )
    (output / "extraction.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("clip", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--decoder", type=Path, required=True)
    p.add_argument("--gpr-source", type=Path, required=True)
    result = extract(**vars(p.parse_args()))
    print(
        json.dumps(
            dict(frames=len(result["frames"]), cnn=False, end_marker_verified=True)
        )
    )
