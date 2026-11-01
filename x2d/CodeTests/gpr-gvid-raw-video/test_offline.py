"""Small synthetic integration check; imports only stdlib and the GPR tools."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument("--binary", type=Path, required=True)
p.add_argument("--gpr-source", type=Path, required=True)
p.add_argument("--decoder", type=Path)
args = p.parse_args()
sys.path.insert(0, str(args.gpr_source.resolve() / "tools"))
import stock_video
import raw_media
from extract import extract


def calibration():
    def tag(code, kind, data, count):
        return raw_media.record(code, kind, count, data)

    def words(code, values):
        return tag(code, 4, struct.pack("<" + "I" * len(values), *values), len(values))

    return dict(
        schema=raw_media.SCHEMA,
        width=128,
        height=96,
        sample_bits=16,
        cfa="RGGB",
        exif=[],
        gps=[],
        image=[
            tag(271, 2, b"Test\0", 5),
            tag(272, 2, b"Offline\0", 8),
            tag(50708, 2, b"Offline\0", 8),
            tag(50706, 1, b"\1\4\0\0", 4),
            tag(33421, 3, struct.pack("<2H", 2, 2), 2),
            tag(33422, 1, bytes((0, 1, 1, 2)), 4),
            tag(50713, 3, struct.pack("<2H", 1, 1), 2),
            words(50714, [0]),
            words(50717, [65535]),
            tag(
                50721,
                10,
                struct.pack(
                    "<18i", 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1
                ),
                9,
            ),
            tag(50728, 5, struct.pack("<6I", 1, 1, 1, 1, 1, 1), 3),
            tag(50778, 3, struct.pack("<H", 21), 1),
        ],
    )


with tempfile.TemporaryDirectory(prefix="x2d-gvid-offline-") as temp:
    root = Path(temp)
    expected = []
    lines = []
    for i in range(3):
        raw = root / f"{i}.raw"
        raw.write_bytes(
            struct.pack(
                "<" + "H" * (128 * 96),
                *((x * 71 + i * 17017) & 65535 for x in range(128 * 96)),
            )
        )
        value = dict(
            synthetic=True,
            frame=i,
            source_kind="offline_contract_test",
            raw_metadata=calibration(),
        )
        (root / f"{i}.json").write_text(json.dumps(value))
        expected.append(value)
        lines.append(f"{i}.raw\t{i}.json\t{i * 40000000}")
    manifest = root / "frames.tsv"
    manifest.write_text("\n".join(lines) + "\n")
    target = root / "clip.gvid"
    command = [
        str(args.binary.resolve()),
        "128",
        "96",
        "16",
        "3",
        "25",
        str(manifest),
        str(target),
    ]
    run = subprocess.run(command, capture_output=True, text=True, check=True)
    events = [json.loads(line) for line in run.stdout.splitlines()]
    result = events[-1]
    assert [e["index"] for e in events[:-1]] == [0, 1, 2]
    assert result["frames"] == 3 and result["complete"] and result["cnn"] is False
    with target.open("rb") as file:
        header = stock_video.read_header(file)
        frames = list(stock_video.records(file, header))
    assert (header["width"], header["height"], header["sample_bits"]) == (128, 96, 16)
    assert header["_end_marker_verified"] and len(frames) == 3
    assert [f["metadata"] for f in frames] == expected
    assert [f["pts_ns"] for f in frames] == [0, 40000000, 80000000]
    assert all(f["payload"].startswith(b"VC-5") for f in frames)
    assert len({hashlib.sha256(f["payload"]).digest() for f in frames}) == 3
    # Odd row pitch puts alternate rows at unaligned addresses. Padding must
    # never enter the image. The native demo overwrites the borrowed source
    # immediately after submit, before waiting for the encoder.
    padded_lines = []
    for i in range(3):
        packed = (root / f"{i}.raw").read_bytes()
        padded = b"".join(
            packed[y * 256 : (y + 1) * 256] + bytes([255]) * 17 for y in range(96)
        )
        (root / f"{i}-padded.raw").write_bytes(padded)
        padded_lines.append(f"{i}-padded.raw\t{i}.json\t{i * 40000000}")
    padded_manifest = root / "padded.tsv"
    padded_manifest.write_text("\n".join(padded_lines) + "\n")
    callback_command = command.copy()
    callback_command[-2:] = [str(padded_manifest), str(root / "callback.gvid")]
    callback_command.append("273")
    callback_run = subprocess.run(
        callback_command, capture_output=True, text=True, check=True
    )
    assert (
        json.loads(callback_run.stdout.splitlines()[-1])["input_mode"]
        == "copied_callback"
    )
    with (root / "callback.gvid").open("rb") as file:
        copied_header = stock_video.read_header(file)
        copied_frames = list(stock_video.records(file, copied_header))
    assert copied_header["_end_marker_verified"]
    assert [f["payload"] for f in copied_frames] == [f["payload"] for f in frames]
    assert [f["metadata"] for f in copied_frames] == expected
    decoded = extract(
        target,
        root / "decoded",
        args.decoder or args.binary.resolve().with_name("gvid_decode_frame"),
        args.gpr_source,
    )
    assert (
        len(decoded["frames"]) == 3
        and decoded["end_marker_verified"]
        and decoded["cnn"] is False
    )
    assert len({f["decoded_raw_sha256"] for f in decoded["frames"]}) == 3
    truncated = root / "truncated.gvid"
    truncated.write_bytes(target.read_bytes()[:-48])
    try:
        extract(
            truncated,
            root / "must-not-exist",
            args.decoder or args.binary.resolve().with_name("gvid_decode_frame"),
            args.gpr_source,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete recording accepted")
    assert not (root / "must-not-exist").exists()
    digest = hashlib.sha256(target.read_bytes()).digest()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert hashlib.sha256(target.read_bytes()).digest() == digest
    # The same uint16 storage must not silently imply a smaller count domain.
    for bits in (12, 14):
        invalid_domain = command.copy()
        invalid_domain[3] = str(bits)
        invalid_domain[-1] = str(root / f"invalid-domain-{bits}.gvid")
        rejected = subprocess.run(invalid_domain, capture_output=True, text=True)
        assert rejected.returncode != 0
        assert "sample exceeds declared count domain" in rejected.stderr
    manifest.write_text(
        "\n".join([lines[0], lines[1].rsplit("\t", 1)[0] + "\t0"]) + "\n"
    )
    invalid_pts = command[:-1] + [str(root / "invalid-pts.gvid")]
    assert subprocess.run(invalid_pts, capture_output=True).returncode != 0
    manifest.write_text("\n".join(lines) + "\n")
    (root / "1.raw").write_bytes(b"bad")
    failed = command[:-1] + [str(root / "invalid.gvid")]
    assert subprocess.run(failed, capture_output=True).returncode != 0
    assert not any(m in sys.modules for m in ("torch", "tensorflow", "coremltools"))
print(
    "PASS: distinct RGGB16 frames, native decode, calibrated GPR/DNG extraction, PTS/CRC/END3, exclusive output, invalid domain/PTS/truncation/short-input rejection; no CNN imports"
)
