"""用本地 X2D 照片运行一次可复现的 GVID / ProRes 电脑试验。"""

import argparse
import copy
from fractions import Fraction
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def run(command):
    subprocess.run([str(v) for v in command], check=True)


def natural(path):
    return [int(v) if v.isdigit() else v.lower() for v in re.split(r"(\d+)", path.name)]


def scaled_inputs(base, output, gpr_source, labels, frames):
    import numpy as np
    from PIL import Image

    sys.path.insert(0, str(gpr_source / "tools"))
    import raw_media as media

    settings = {
        "4k12": (3840, 2160, 12, 12, "30"),
        "8k11": (8192, 3424, 11, 12, "24"),
        "fhd60raw12": (3840, 1296, 12, 12, "60"),
        "x2d100mp14": (None, None, 14, 14, "6"),
        "x2d100mp16": (None, None, 16, 16, "27/10"),
    }
    rows = [line.split("\t") for line in (base / "frames.tsv").read_text().splitlines()]

    def tag(code, values):
        return media.record(
            code, 4, len(values), struct.pack("<" + "I" * len(values), *values)
        )

    for label in labels:
        folder = output / label
        if (folder / "settings.json").exists():
            continue
        folder.mkdir(parents=True, exist_ok=False)
        width, height, source_bits, count_bits, fps = settings[label]
        rate = Fraction(fps)
        lines = []
        for index, (raw_name, json_name, _) in enumerate(rows):
            frame = json.loads((base / json_name).read_text())
            meta = copy.deepcopy(frame["raw_metadata"])
            w0, h0 = meta["width"], meta["height"]
            if width is None:
                w, h = w0, h0
            else:
                w, h = width, height
            pixels = np.memmap(base / raw_name, dtype="<u2", mode="r", shape=(h0, w0))
            if width is None:
                result = np.asarray(pixels).copy()
            else:
                aspect = w / h
                cw = min(w0, int(h0 * aspect)) // 2 * 2
                ch = min(h0, int(cw / aspect)) // 2 * 2
                left = ((w0 - cw) // 2) // 2 * 2
                top = ((h0 - ch) // 2) // 2 * 2
                roi = pixels[top : top + ch, left : left + cw]
                result = np.empty((h, w), dtype=np.uint16)
                for yy in range(2):
                    for xx in range(2):
                        plane = Image.fromarray(roi[yy::2, xx::2].astype(np.float32))
                        resized = np.asarray(
                            plane.resize((w // 2, h // 2), Image.Resampling.LANCZOS)
                        )
                        result[yy::2, xx::2] = np.clip(
                            np.rint(resized), 0, 65535
                        ).astype(np.uint16)
            shift = 16 - source_bits
            result >>= shift
            tags = []
            for record in meta["image"]:
                code = record["code"]
                if code in (50715, 50716, 50830, 51125):
                    raise ValueError(
                        f"spatial calibration {code} needs a dedicated transform"
                    )
                if code in (51008, 51009, 51022) and media.unpack_record(
                    record
                ) != bytes(4):
                    raise ValueError(
                        "nonempty opcode lists cannot be rescaled by this trial"
                    )
                if width is not None and code in (50829, 50719, 50720, 700):
                    continue
                if code == 50714 and shift:
                    if record["type"] == 5:
                        values = struct.unpack(
                            "<" + "I" * (record["count"] * 2),
                            media.unpack_record(record),
                        )
                        rationals = [
                            (n, d * (1 << shift))
                            for n, d in zip(values[::2], values[1::2])
                        ]
                    else:
                        rationals = [(n, 1 << shift) for n in media.values(record)]
                    values = [v for pair in rationals for v in pair]
                    record = media.record(
                        code,
                        5,
                        len(rationals),
                        struct.pack("<" + "I" * len(values), *values),
                    )
                if code == 50717 and shift:
                    record = tag(code, [int(v) >> shift for v in media.values(record)])
                tags.append(record)
            if width is not None:
                tags += [
                    tag(50829, [0, 0, h, w]),
                    tag(50719, [0, 0]),
                    tag(50720, [w, h]),
                ]
            meta.update(width=w, height=h, sample_bits=count_bits, image=tags)
            for i, record in enumerate(meta["exif"]):
                if record["code"] in (40962, 40963):
                    meta["exif"][i] = tag(
                        record["code"], [w if record["code"] == 40962 else h]
                    )
            media.validate(meta)
            frame.update(
                raw_metadata=meta,
                source_sensor_mode_simulated=False,
                count_preparation=f"16-bit still counts shifted by {shift}",
                geometry_preparation="center-even-crop and separate-CFA-plane Lanczos; not sensor-mode emulation",
            )
            result.astype("<u2", copy=False).tofile(folder / f"{index:06d}.raw")
            (folder / f"{index:06d}.json").write_text(
                json.dumps(frame, separators=(",", ":"))
            )
            lines.append(
                f"{index:06d}.raw\t{index:06d}.json\t{index * 1000000000 * rate.denominator // rate.numerator}"
            )
        (folder / "frames.tsv").write_text("\n".join(lines) + "\n")
        (folder / "settings.json").write_text(
            json.dumps(
                dict(
                    label=label,
                    width=w,
                    height=h,
                    count_bits=count_bits,
                    source_count_bits=source_bits,
                    fps=fps,
                    frames=frames,
                    source_model="X2D 100C",
                    interval_timelapse=False,
                ),
                indent=2,
            )
            + "\n"
        )
        print("Prepared", label, frames, "frames", flush=True)


def render_masters(base, root, gpr_source, exposure):
    import rawpy

    sys.path.insert(0, str(gpr_source / "tools"))
    import raw_media as media

    movies = root / "movies"
    if (movies / "masters.json").exists():
        return
    movies.mkdir(exist_ok=True)
    rows = [line.split("\t") for line in (base / "frames.tsv").read_text().splitlines()]
    first = json.loads((base / rows[0][1]).read_text())["raw_metadata"]
    width, height = first["width"], first["height"]
    graph = "[0:v]split=3[a][b][c];"
    outputs = [
        ("1080p", 1920, 1080, "a"),
        ("4k", 3840, 2160, "b"),
        ("8k", 8192, 3424, "c"),
    ]
    filters = []
    for label, w, h, source in outputs:
        cw = min(width, int(height * w / h)) // 2 * 2
        ch = min(height, int(cw * h / w)) // 2 * 2
        filters.append(
            f"[{source}]crop={cw}:{ch}:(iw-ow)/2:(ih-oh)/2,scale={w}:{h}:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv444p10le[v{label}]"
        )
    graph += ";".join(filters)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb48le",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        "24",
        "-i",
        "pipe:0",
        "-filter_complex_threads",
        "4",
        "-filter_complex",
        graph,
    ]
    for label, _, _, _ in outputs:
        command += [
            "-map",
            f"[v{label}]",
            "-an",
            "-map_metadata",
            "-1",
            "-c:v",
            "rawvideo",
            "-pix_fmt",
            "yuv444p10le",
            "-f",
            "nut",
            "-threads",
            "4",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            str(movies / f"master-{label}-24fps.nut"),
        ]
    temporary = root / "render-frame.dng"
    with (movies / "render.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for i, (raw_name, json_name, _) in enumerate(rows):
                meta = json.loads((base / json_name).read_text())["raw_metadata"]
                media.write(temporary, meta, (base / raw_name).read_bytes(), "dng")
                with rawpy.imread(str(temporary)) as raw:
                    rgb = raw.postprocess(
                        use_camera_wb=True,
                        no_auto_bright=True,
                        output_bps=16,
                        output_color=rawpy.ColorSpace.sRGB,
                        gamma=(2.222, 4.5),
                        exp_shift=2**exposure,
                        user_flip=0,
                    )
                process.stdin.write(rgb.astype("<u2", copy=False).tobytes())
                temporary.unlink()
                if (i + 1) % 10 == 0:
                    print("Rendered source masters", i + 1, "of", len(rows), flush=True)
            process.stdin.close()
            if process.wait():
                raise RuntimeError(
                    "FFmpeg reference master failed; see movies/render.log"
                )
        except BaseException:
            if process.poll() is None:
                process.terminate()
            process.wait()
            raise
    (movies / "masters.json").write_text(
        json.dumps(dict(frames=len(rows), viewing_exposure_ev=exposure)) + "\n"
    )


def report(root):
    rows = []
    for receipt in sorted(root.glob("gvid/*/result.json")):
        r = json.loads(receipt.read_text())
        movie = receipt.parent / "review-1080p.mp4"
        link = html.escape(str(movie.relative_to(root)))
        quality = (
            f"{r['psnr_db']:.2f} dB RAW"
            if r["psnr_db"] is not None
            else "zero sample error"
        )
        links = f'<a href="{link}">MP4</a> · <a href="{html.escape(str((receipt.parent / "clip.gvid").relative_to(root)))}">GVID</a>'
        prores = receipt.parent / "gvid-to-prores-hq.mov"
        if prores.exists():
            links += f' · <a href="{html.escape(str(prores.relative_to(root)))}">ProRes HQ</a>'
        rows.append(
            f"<tr><td>{html.escape(r['case'])}</td><td>{r['summary']['encode_mean_ms']:.2f} ms</td><td>{r['nominal_payload_mbps']:.1f} Mb/s</td><td>{quality}</td><td>{links}</td></tr>"
        )
    for receipt in sorted(root.glob("ffmpeg-matrix/*/result.json")):
        r = json.loads(receipt.read_text())
        movie = next(receipt.parent.glob("clip.*"), None)
        view = (
            f'<a href="{html.escape(str(movie.relative_to(root)))}">View</a>'
            if movie and r["status"] == "passed"
            else html.escape(r["status"])
        )
        details = html.escape(str(receipt.relative_to(root)))
        view += f' · <a href="{details}">Details / errors</a>'
        rows.append(
            f"<tr><td>{html.escape(r['case'])}</td><td>{r['encode_wall_seconds']:.2f} s total</td><td>{r.get('actual_mbps', 0):.1f} Mb/s</td><td>{r.get('ssim', 0):.6f} SSIM</td><td>{view}</td></tr>"
        )
    text = (
        '<!doctype html><meta charset="utf-8"><title>X2D RAW video trial</title><style>body{font:16px system-ui;margin:3rem;max-width:1200px}td,th{padding:.5rem;text-align:left;border-bottom:1px solid #ddd}table{border-collapse:collapse}</style><h1>X2D RAW video trial</h1><p>Local desktop experiment using operator photographs. Nominal playback rates do not establish camera acquisition. GVID time is codec mean per frame; FFmpeg time is total encode pipeline time. RAW and rendered-image quality metrics have different domains. No CNN. No photos are uploaded.</p><table><tr><th>Case</th><th>Time</th><th>Measured bitrate</th><th>Quality</th><th>Movie</th></tr>'
        + "".join(rows)
        + "</table>"
    )
    (root / "report.html").write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photos", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reference",
        type=Path,
        help="Same-model calibrated DNG/GPR; required for FFF/3FR",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--all",
        action="store_true",
        help="All X2D-relevant presets instead of the quick 4K Q3 trial",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show selected photo count and matrix without creating outputs",
    )
    parser.add_argument("--build", type=Path, help="Reuse a build of this module")
    parser.add_argument("--exposure-ev", type=float, default=0)
    args = parser.parse_args()
    if (
        not 2 <= args.limit <= 1000
        or not math.isfinite(args.exposure_ev)
        or abs(args.exposure_ev) > 5
    ):
        parser.error("limit must be 2..1000 and exposure EV finite in -5..5")
    for tool in ("cmake", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            parser.error("missing executable: " + tool)
    if args.all:
        options = subprocess.check_output(
            ["ffmpeg", "-hide_banner", "-h", "filter=setpts"], text=True
        )
        if "strip_fps" not in options:
            parser.error(
                "full matrix needs FFmpeg with setpts strip_fps (tested with 8.1.1)"
            )
    if not args.photos.is_dir():
        parser.error("photo directory does not exist: " + str(args.photos))
    encoders = subprocess.check_output(
        ["ffmpeg", "-hide_banner", "-encoders"], text=True
    )
    for required_encoder in ("libx264", "prores_ks"):
        if not re.search(r"^ V\S*\s+" + required_encoder + r"\s", encoders, re.M):
            parser.error("FFmpeg is missing required encoder: " + required_encoder)
    files = sorted(
        [
            p
            for p in args.photos.iterdir()
            if p.suffix.lower() in (".fff", ".3fr", ".dng")
        ],
        key=natural,
    )[: args.limit]
    if len(files) < 2:
        parser.error("requires at least two FFF/3FR/DNG photos")
    reference = args.reference or next(
        (p for p in files if p.suffix.lower() == ".dng"), None
    )
    if reference is None:
        parser.error(
            "FFF/3FR input needs --reference with one same-model calibrated DNG/GPR"
        )
    if not reference.is_file():
        parser.error("reference file does not exist: " + str(reference))
    if args.plan:
        print(
            json.dumps(
                dict(
                    selected_photos=len(files),
                    run="full matrix" if args.all else "4K Q3 + ProRes HQ",
                    gvid_quality_presets=list(range(6)) if args.all else [3],
                    modes=[
                        "4K24/30",
                        "8K24",
                        "FHD60 RAW input",
                        "full-resolution 14/16-bit",
                    ]
                    if args.all
                    else ["4K30"],
                    uploads=False,
                ),
                indent=2,
            )
        )
        return
    root = args.output.resolve()
    if root.is_relative_to(args.photos.resolve()):
        parser.error("output must be outside the source photo directory")
    root.mkdir(parents=True, exist_ok=True)
    print("Selected", len(files), "photos; checking input identity", flush=True)
    identity = dict(
        inputs=[
            dict(
                path=str(p.resolve()),
                bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            )
            for p in files
        ],
        all=args.all,
        exposure_ev=args.exposure_ev,
        reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
    )
    identity_path = root / "private-input-manifest.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        parser.error(
            "existing output belongs to different inputs/options; choose a new output directory"
        )
    identity_path.write_text(json.dumps(identity, indent=2) + "\n")
    build = args.build.resolve() if args.build else root / "build"
    if not (build / "gvid_raw_demo").exists():
        run(["cmake", "-S", HERE, "-B", build, "-DCMAKE_BUILD_TYPE=Release"])
        run(["cmake", "--build", build, "-j", "4"])
    cache = (build / "CMakeCache.txt").read_text()
    match = re.search(r"^GPR_SOURCE_DIR:PATH=(.+)$", cache, re.M)
    gpr_source = Path(match.group(1)) if match else build / "_deps/gpr_dependency-src"
    if not (gpr_source / "tools/raw_media.py").exists():
        raise ValueError("cannot locate pinned GPR tools in build")
    base = root / "base16"
    if not (base / "preparation.json").exists():
        from prepare import prepare

        prepare(files, base, gpr_source, reference, 24)
    sys.path.insert(0, str(gpr_source / "tools"))
    import raw_media

    first = json.loads((base / "000000.json").read_text())["raw_metadata"]
    model = next(t for t in first["image"] if t["code"] == 272)
    if b"X2D 100C" not in raw_media.unpack_record(model):
        raise ValueError("this trial targets first-generation X2D 100C")
    decoders = subprocess.check_output(
        ["ffmpeg", "-hide_banner", "-decoders"], text=True
    )
    prores = ["prores_ks"] + (
        ["prores_videotoolbox"] if "prores_videotoolbox" in encoders else []
    )
    labels = (
        ["4k12", "8k11", "fhd60raw12", "x2d100mp14", "x2d100mp16"]
        if args.all
        else ["4k12"]
    )
    trial = dict(
        frames=len(files),
        source_model="X2D 100C",
        interval_timelapse_verified=False,
        labels=labels,
        prores_encoders=prores,
        prores_encoder="prores_ks",
        viewing_exposure_ev=args.exposure_ev,
        prores_raw_encoder_available=bool(
            re.search(r"^ V\S*\s+prores_raw\s", encoders, re.M)
        ),
        prores_raw_decoder_available="prores_raw" in decoders,
        prores_raw_decode_exercised=False,
        full_matrix=args.all,
        cnn=False,
    )
    (root / "trial.json").write_text(json.dumps(trial, indent=2) + "\n")
    scaled_inputs(base, root / "prepared", gpr_source, labels, len(files))
    command = [
        sys.executable,
        HERE / "trial_gvid.py",
        root,
        "--build",
        build,
        "--gpr-source",
        gpr_source,
    ]
    if not args.all:
        command += ["--only", "4k12-q3"]
    try:
        run(command)
    finally:
        report(root)
    if args.all:
        render_masters(base, root, gpr_source, args.exposure_ev)
        try:
            run([sys.executable, HERE / "trial_ffmpeg.py", root])
        finally:
            report(root)
    report(root)
    print("Open local report:", root / "report.html")


if __name__ == "__main__":
    main()
