"""Render extracted Bayer DNGs to a viewing MP4; no CNN or learned restoration.

Optional desktop dependencies: rawpy (LibRaw), Pillow and FFmpeg. The GVID and
full-resolution editable frames remain the RAW deliverables. This is a reduced
resolution viewing export, using ordinary demosaicing/white balance/color.
"""

import argparse
import json
import math
from fractions import Fraction
from pathlib import Path
import subprocess


def render(source, output, width=1280, height=960, fps=None, exposure_ev=0.0):
    import rawpy
    from PIL import Image, ImageOps

    source = Path(source)
    output = Path(output)
    if (
        width < 16
        or height < 16
        or width > 8192
        or height > 8192
        or width % 2
        or height % 2
    ):
        raise ValueError("viewing dimensions must be even and in 16..8192")
    if not math.isfinite(exposure_ev) or not -5 <= exposure_ev <= 5:
        raise ValueError("exposure EV must be finite and in -5..5")
    if output.exists():
        raise FileExistsError(output)
    report = json.loads((source / "extraction.json").read_text())
    if not report["end_marker_verified"] or not report["frames"]:
        raise ValueError("requires verified extraction")
    rate = Fraction(fps) if fps else Fraction(report["fps_num"], report["fps_den"])
    if not 0 < rate <= 240:
        raise ValueError("invalid viewing frame rate")
    if fps is None:
        origin = report["frames"][0]["pts_ns"]
        for i, frame in enumerate(report["frames"]):
            expected = origin + i * 1000000000 * report["fps_den"] // report["fps_num"]
            if abs(frame["pts_ns"] - expected) > 1:
                raise ValueError(
                    "viewing exporter requires nominal CFR timestamps or an explicit --fps reinterpretation"
                )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(rate),
        "-i",
        "pipe:0",
        "-an",
        "-map_metadata",
        "-1",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in report["frames"]:
            path = source / f"{frame['index']:06d}.dng"
            with rawpy.imread(str(path)) as raw:
                pixels = raw.postprocess(
                    half_size=True,
                    use_camera_wb=True,
                    no_auto_bright=True,
                    output_bps=8,
                    exp_shift=2.0**exposure_ev,
                )
            image = Image.fromarray(pixels)
            fitted = ImageOps.contain(
                image, (width, height), method=Image.Resampling.LANCZOS
            )
            canvas = Image.new("RGB", (width, height), "black")
            canvas.paste(
                fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2)
            )
            process.stdin.write(canvas.tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError("FFmpeg viewing export failed")
    except BaseException:
        if not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
        raise
    return dict(
        frames=len(report["frames"]),
        width=width,
        height=height,
        playback_rate=str(rate),
        exposure_ev=exposure_ev,
        cnn=False,
        rendering="LibRaw half-size demosaic, source WB/color, downscaled viewing export",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=960)
    p.add_argument(
        "--fps", help="Optional viewing-rate override; does not change RAW timestamps"
    )
    p.add_argument(
        "--exposure-ev",
        type=float,
        default=0.0,
        help="Viewing exposure only; RAW data is unchanged",
    )
    print(json.dumps(render(**vars(p.parse_args()))))
