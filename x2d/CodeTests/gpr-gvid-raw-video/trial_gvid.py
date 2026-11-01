"""Real-image GVID quality/geometry matrix with native decode and local movies."""

import argparse, json, math, subprocess, sys, tempfile, time
from fractions import Fraction
from pathlib import Path
import numpy as np
import rawpy
from PIL import Image

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("root", type=Path)
p.add_argument("--build", type=Path, required=True)
p.add_argument("--gpr-source", type=Path, required=True)
p.add_argument("--only")
args = p.parse_args()
ROOT = args.root.resolve()
trial = json.loads((ROOT / "trial.json").read_text())
sys.path.insert(0, str(args.gpr_source.resolve() / "tools"))
import raw_media as media
import stock_video

ENCODER = args.build.resolve() / "gvid_raw_demo"
DECODER = args.build.resolve() / "gvid_decode_frame"
labels = trial["labels"]
results = []
for label in labels:
    prepared = ROOT / "prepared" / label
    settings = json.loads((prepared / "settings.json").read_text())
    rate = Fraction(str(settings["fps"]))
    lines = [
        line.split("\t") for line in (prepared / "frames.tsv").read_text().splitlines()
    ]

    def relative(name):
        path = Path(name)
        return path if path.is_absolute() else prepared / path

    for q in range(6):
        key = f"{label}-q{q}"
        if args.only and args.only != key:
            continue
        folder = ROOT / "gvid" / key
        folder.mkdir(parents=True, exist_ok=True)
        receipt = folder / "result.json"
        if receipt.exists():
            results.append(json.loads(receipt.read_text()))
            continue
        clip = folder / "clip.gvid"
        cached = folder / "encoded.json"
        if cached.exists():
            saved = json.loads(cached.read_text())
            events = saved["events"]
            summary = events[-1]
            encode_wall = saved["encode_wall_seconds"]
        else:
            if clip.exists():
                raise FileExistsError("unfinished existing case " + key)
            print("START", key, flush=True)
            start = time.perf_counter()
            command = [
                str(ENCODER),
                str(settings["width"]),
                str(settings["height"]),
                str(settings["count_bits"]),
                str(q),
                str(rate),
                str(prepared / "frames.tsv"),
                str(clip),
                str(settings["width"] * 2),
            ]
            encoded = subprocess.run(
                command, capture_output=True, text=True, check=True
            )
            encode_wall = time.perf_counter() - start
            (folder / "capture.jsonl").write_text(encoded.stdout)
            events = [json.loads(line) for line in encoded.stdout.splitlines()]
            summary = events[-1]
            cached.write_text(
                json.dumps(dict(events=events, encode_wall_seconds=encode_wall)) + "\n"
            )
        print("DECODE", key, flush=True)
        width, height = settings["width"], settings["height"]
        movie = folder / "review-1080p.mp4"
        native_prores = q == 3 and label in ("4k12", "8k11")
        prores_encoder = trial["prores_encoder"]
        prores_pix = (
            "p210le" if prores_encoder == "prores_videotoolbox" else "yuv422p10le"
        )
        half = not native_prores
        input_width = width // 2 if half else width
        input_height = height // 2 if half else height
        graph = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos:out_color_matrix=bt709:out_range=tv,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[view]"
        if native_prores:
            graph = f"[0:v]split=2[a][b];[a]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos:out_color_matrix=bt709:out_range=tv,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[view];[b]scale=out_color_matrix=bt709:out_range=tv,format={prores_pix}[prores]"
        ff = [
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
            f"{input_width}x{input_height}",
            "-framerate",
            str(rate),
            "-i",
            "pipe:0",
            "-filter_complex_threads",
            "4",
            "-filter_complex",
            graph,
            "-map",
            "[view]",
            "-an",
            "-map_metadata",
            "-1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "16",
            "-threads",
            "4",
            "-pix_fmt",
            "yuv420p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-movflags",
            "+faststart",
            str(movie),
        ]
        if native_prores:
            ff += [
                "-map",
                "[prores]",
                "-an",
                "-map_metadata",
                "-1",
                "-c:v",
                prores_encoder,
                "-profile:v",
                "3",
            ]
            ff += (
                ["-allow_sw", "0"]
                if prores_encoder == "prores_videotoolbox"
                else ["-alpha_bits", "0", "-threads", "4"]
            )
            ff += [
                "-pix_fmt",
                prores_pix,
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-colorspace",
                "bt709",
                str(folder / "gvid-to-prores-hq.mov"),
            ]
        sse = 0
        pixels_count = 0
        maximum_error = 0
        count = 0
        render_start = time.perf_counter()
        with (
            tempfile.TemporaryDirectory(prefix="gvid-matrix-", dir=ROOT) as temporary,
            (folder / "render.log").open("w") as log,
        ):
            temporary = Path(temporary)
            vc5 = temporary / "frame.vc5"
            rawpath = temporary / "frame.raw"
            dng = temporary / "frame.dng"
            process = subprocess.Popen(ff, stdin=subprocess.PIPE, stderr=log)
            try:
                with clip.open("rb") as stream:
                    header = stock_video.read_header(stream)
                    for frame in stock_video.records(stream, header):
                        index = frame["index"]
                        meta = frame["metadata"]["raw_metadata"]
                        media.validate(meta, header)
                        expected = json.loads(relative(lines[index][1]).read_text())
                        if frame["metadata"] != expected or frame["pts_ns"] != int(
                            lines[index][2]
                        ):
                            raise ValueError("metadata/PTS differs")
                        vc5.write_bytes(frame["payload"])
                        subprocess.run(
                            [
                                str(DECODER),
                                str(settings["count_bits"]),
                                str(vc5),
                                str(rawpath),
                            ],
                            check=True,
                            capture_output=True,
                        )
                        if rawpath.stat().st_size != width * height * 2:
                            raise ValueError("wrong decoded size")
                        reference = np.memmap(
                            relative(lines[index][0]),
                            dtype="<u2",
                            mode="r",
                            shape=(height, width),
                        )
                        restored = np.memmap(
                            rawpath, dtype="<u2", mode="r", shape=(height, width)
                        )
                        for row in range(0, height, 128):
                            difference = restored[row : row + 128].astype(
                                np.int32
                            ) - reference[row : row + 128].astype(np.int32)
                            sse += int(
                                np.sum(difference.astype(np.int64) ** 2, dtype=np.int64)
                            )
                            maximum_error = max(
                                maximum_error, int(np.max(np.abs(difference)))
                            )
                        del reference, restored
                        pixels_count += width * height
                        media.write(dng, meta, rawpath.read_bytes(), "dng")
                        if index in (0, len(lines) - 1):
                            again = media.extract(dng, settings["count_bits"])
                            for group in ("image", "exif", "gps"):
                                if sorted(
                                    meta[group], key=lambda t: t["code"]
                                ) != sorted(again[group], key=lambda t: t["code"]):
                                    raise ValueError("typed calibration differs")
                        with rawpy.imread(str(dng)) as raw:
                            rgb = raw.postprocess(
                                half_size=half,
                                use_camera_wb=True,
                                no_auto_bright=True,
                                output_bps=16,
                                exp_shift=2.0 ** trial["viewing_exposure_ev"],
                                user_flip=0,
                                gamma=(2.222, 4.5),
                            )
                        if rgb.shape != (input_height, input_width, 3):
                            raise ValueError("render geometry differs")
                        if index == 0:
                            preview = Image.fromarray((rgb >> 8).astype(np.uint8))
                            preview.thumbnail((1000, 750))
                            preview.save(folder / "first-frame.png")
                        process.stdin.write(rgb.astype("<u2", copy=False).tobytes())
                        rawpath.unlink()
                        dng.unlink()
                        count += 1
                        if count % 60 == 0:
                            print(
                                key,
                                "decoded/rendered",
                                count,
                                "of",
                                len(lines),
                                flush=True,
                            )
                    if not header["_end_marker_verified"] or count != len(lines):
                        raise ValueError("incomplete clip")
                process.stdin.close()
                if process.wait():
                    raise RuntimeError("FFmpeg render failed: " + key)
            except BaseException:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                raise
        # Full error-fatal viewing decode and frame count, not just a successful mux.
        movies = [movie] + ([folder / "gvid-to-prores-hq.mov"] if native_prores else [])
        movie_receipts = []
        for path in movies:
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-xerror",
                    "-i",
                    str(path),
                    "-map",
                    "0:v:0",
                    "-f",
                    "null",
                    "-",
                ],
                check=True,
                capture_output=True,
            )
            probe = json.loads(
                subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-count_frames",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=codec_name,profile,width,height,pix_fmt,nb_read_frames,r_frame_rate",
                        "-of",
                        "json",
                        str(path),
                    ],
                    text=True,
                )
            )["streams"][0]
            if int(probe["nb_read_frames"]) != len(lines):
                raise ValueError("wrong movie frame count")
            movie_receipts.append(
                dict(file=path.name, bytes=path.stat().st_size, probe=probe)
            )
        mse = sse / pixels_count
        peak = (1 << settings["source_count_bits"]) - 1
        report = dict(
            case=key,
            settings=settings,
            quality=q,
            source_model=trial["source_model"],
            verified_interval_timelapse=False,
            frames=count,
            summary=summary,
            encode_wall_seconds=encode_wall,
            file_pipeline_fps=count / encode_wall,
            nominal_payload_mbps=summary["payload_bytes"]
            * 8
            * float(rate)
            / count
            / 1e6,
            rmse_counts=math.sqrt(mse),
            psnr_db=None if mse == 0 else 10 * math.log10(peak * peak / mse),
            psnr_peak_counts=peak,
            max_abs_error_counts=maximum_error,
            encode_max_ms=max(row["encode_ms"] for row in events[:-1]),
            codec_deadline_misses=sum(
                row["encode_ms"] > 1000 / float(rate) for row in events[:-1]
            ),
            all_native_decoded=True,
            all_metadata_and_pts_verified=True,
            end_marker_verified=True,
            first_last_typed_dng_calibration_verified=True,
            decode_render_verify_seconds=time.perf_counter() - render_start,
            movies=movie_receipts,
            cnn=False,
            complete=True,
        )
        receipt.write_text(json.dumps(report, indent=2) + "\n")
        results.append(report)
        (ROOT / "gvid-results.json").write_text(json.dumps(results, indent=2) + "\n")
        from camera_trial import report as update_report

        update_report(ROOT)
        print(
            "PASS",
            key,
            "encode_ms",
            summary["encode_mean_ms"],
            "Mbps",
            round(report["nominal_payload_mbps"], 1),
            "PSNR",
            round(report["psnr_db"], 2),
            flush=True,
        )
print("GVID completed cases", len(results), flush=True)
