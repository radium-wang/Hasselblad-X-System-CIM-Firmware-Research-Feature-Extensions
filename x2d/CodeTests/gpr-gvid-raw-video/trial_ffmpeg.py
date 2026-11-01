"""X2D-relevant ProRes profiles/scales and H.264 bitrate checks on a real timelapse."""

from pathlib import Path
import argparse, json, re, subprocess, time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
parser.add_argument("--only")
args = parser.parse_args()
ROOT = args.root.resolve()
trial = json.loads((ROOT / "trial.json").read_text())
OUT = ROOT / "ffmpeg-matrix"
OUT.mkdir(exist_ok=True)
frames = trial["frames"]
modes = [
    ("1080p", 1920, 1080, 60, [5, 10, 20, 40]),
    ("4k", 3840, 2160, 24, [10, 25, 50, 100]),
    ("4k", 3840, 2160, 30, [10, 25, 50, 100]),
    ("8k", 8192, 3424, 24, [50, 100, 200, 400]),
]
profiles = ["proxy", "lt", "standard", "hq", "4444", "4444xq"]
results = []


def run_case(scale, w, h, fps, encoder, profile=None, bitrate=None):
    name = f"{scale}-{fps}fps-{encoder}-" + (
        profiles[profile] if profile is not None else str(bitrate) + "mbps"
    )
    if args.only and name != args.only:
        return
    folder = OUT / name
    folder.mkdir(exist_ok=True)
    receipt = folder / "result.json"
    if receipt.exists():
        results.append(json.loads(receipt.read_text()))
        return
    master = ROOT / "movies" / f"master-{scale}-24fps.nut"
    if not master.exists():
        master = master.with_suffix(".mkv")
    suffix = ".mp4" if encoder == "libx264" else ".mov"
    output = folder / ("clip" + suffix)
    if output.exists():
        raise FileExistsError("unfinished output " + name)
    pix = (
        "yuv420p"
        if encoder == "libx264"
        else ("yuv422p10le" if profile < 4 else "yuv444p10le")
    )
    input_pix = pix
    if encoder == "prores_videotoolbox":
        input_pix = "p210le" if profile < 4 else "p410le"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-nostdin",
        "-n",
        "-threads",
        "4",
        "-i",
        str(master),
        "-an",
        "-map_metadata",
        "-1",
        "-vf",
        f"format={input_pix},settb=1/{fps},setpts=N:strip_fps=1",
        "-r",
        str(fps),
        "-enc_time_base",
        f"1:{fps}",
        "-fps_mode",
        "cfr",
        "-c:v",
        encoder,
        "-threads",
        "6",
    ]
    if profile is not None:
        command += ["-profile:v", str(profile)]
        if encoder == "prores_ks":
            command += ["-alpha_bits", "0"]
        else:
            command += ["-allow_sw", "0"]
    else:
        command += [
            "-preset",
            "fast",
            "-b:v",
            f"{bitrate}M",
            "-minrate",
            f"{bitrate}M",
            "-maxrate",
            f"{bitrate}M",
            "-bufsize",
            f"{bitrate * 2}M",
            "-x264-params",
            "nal-hrd=cbr:force-cfr=1:filler=1",
            "-g",
            str(fps * 2),
        ]
    command += [
        "-pix_fmt",
        input_pix,
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
        "-movflags",
        "+faststart",
        str(output),
    ]
    print("ENCODE", name, flush=True)
    start = time.perf_counter()
    encoded = subprocess.run(command, capture_output=True, text=True)
    wall = time.perf_counter() - start
    (folder / "encode.log").write_text(encoded.stderr)
    report = dict(
        case=name,
        scale=scale,
        width=w,
        height=h,
        fps=fps,
        encoder=encoder,
        profile=profiles[profile] if profile is not None else None,
        target_mbps=bitrate,
        frames=frames,
        source_model=trial["source_model"],
        source_interval_timelapse_verified=False,
        cnn=False,
        hardware_required=encoder == "prores_videotoolbox",
        encode_wall_seconds=wall,
        encode_command=command,
    )
    if encoded.returncode:
        report.update(
            status="unsupported_or_failed",
            returncode=encoded.returncode,
            error_tail=encoded.stderr[-1600:],
        )
    else:
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,profile,codec_tag_string,width,height,pix_fmt,nb_frames,avg_frame_rate,r_frame_rate,color_range,color_space,color_transfer,color_primaries:format=duration,size,bit_rate",
                    "-of",
                    "json",
                    str(output),
                ],
                text=True,
            )
        )
        stream = probe["streams"][0]
        if (stream["width"], stream["height"], int(stream.get("nb_frames", 0))) != (
            w,
            h,
            frames,
        ):
            raise ValueError("unexpected output dimensions/count")
        ps = folder / "psnr.log"
        ss = folder / "ssim.log"
        metric_pix = "yuv444p10le"
        graph = f"[0:v]format={metric_pix},settb=1/1000,setpts=N*1000[d];[1:v]format={metric_pix},settb=1/1000,setpts=N*1000[r];[d]split[dp][ds];[r]split[rp][rs];[dp][rp]psnr=stats_file={ps}[p];[ds][rs]ssim=stats_file={ss}[s]"
        verify = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "info",
            "-nostdin",
            "-xerror",
            "-threads",
            "4",
            "-i",
            str(output),
            "-threads",
            "4",
            "-i",
            str(master),
            "-filter_complex_threads",
            "4",
            "-filter_complex",
            graph,
            "-map",
            "[p]",
            "-fps_mode",
            "passthrough",
            "-f",
            "null",
            "-",
            "-map",
            "[s]",
            "-fps_mode",
            "passthrough",
            "-f",
            "null",
            "-",
        ]
        checked = subprocess.run(verify, capture_output=True, text=True)
        (folder / "decode-quality.log").write_text(checked.stderr)
        if checked.returncode:
            raise RuntimeError(
                "full decode/metrics failed " + name + " " + checked.stderr[-1000:]
            )
        psrows = ps.read_text().splitlines()
        ssrows = ss.read_text().splitlines()
        if len(psrows) != frames or len(ssrows) != frames:
            raise ValueError("metrics frame count differs")
        psnr = re.findall(r"PSNR.*?average:([\d.inf]+)", checked.stderr)
        ssim = re.findall(r"SSIM.*?All:([\d.]+)", checked.stderr)
        if not psnr or not ssim:
            raise ValueError("missing quality summary")
        duration = float(probe["format"]["duration"])
        report.update(
            status="passed",
            bytes=output.stat().st_size,
            actual_mbps=output.stat().st_size * 8 / duration / 1e6,
            encode_pipeline_fps=frames / wall,
            psnr_db=float(psnr[-1]) if psnr[-1] != "inf" else None,
            ssim=float(ssim[-1]),
            all_frames_decoded=True,
            metric_frames=len(psrows),
            probe=probe,
            metric_pixel_format=metric_pix,
        )
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    results.append(report)
    (ROOT / "ffmpeg-results.json").write_text(json.dumps(results, indent=2) + "\n")
    from camera_trial import report as update_report

    update_report(ROOT)
    print(
        report["status"].upper(),
        name,
        "seconds",
        round(wall, 2),
        "Mbps",
        round(report.get("actual_mbps", 0), 1),
        flush=True,
    )


for scale, w, h, fps, rates in modes:
    for encoder in trial["prores_encoders"]:
        for profile in range(6):
            run_case(scale, w, h, fps, encoder, profile=profile)
    for bitrate in rates:
        run_case(scale, w, h, fps, "libx264", bitrate=bitrate)
print(
    "FFmpeg cases",
    len(results),
    "passed",
    sum(r["status"] == "passed" for r in results),
    "failed/unsupported",
    sum(r["status"] != "passed" for r in results),
    flush=True,
)
