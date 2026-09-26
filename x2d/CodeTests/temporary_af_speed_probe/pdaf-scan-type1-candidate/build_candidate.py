#!/usr/bin/env python3
"""Build and verify a two-instruction X2D 4.2.0 PDAF scan-speed candidate.

This tool is offline-only.  It reads an exact stock libaaa.so and writes the
original/candidate function plus a JSON manifest.  It never opens USB or
changes a camera.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from elftools.elf.elffile import ELFFile


LIBAAA_SHA256 = "feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7"
FUNCTION_NAME = "_exec_pdaf_afs_process"
FUNCTION_START = 0x90128
FUNCTION_END = 0x90878
ORIGINAL_FUNCTION_SHA256 = "042cc441a57fa5004b53f1f69a260799b4bb53768b311cf7d357d382ccce096d"
CANDIDATE_FUNCTION_SHA256 = "824a398ddac6ad99be93240422b356cadad2ff036fee26bb867dad37cb0d701a"

# Preserve the original instruction form (ORR-immediate alias) so each site
# changes only the immediate encoding byte: mov w9,#2 -> mov w9,#1.
ORIGINAL_INSTRUCTION = bytes.fromhex("e9031f32")
CANDIDATE_INSTRUCTION = bytes.fromhex("e9030032")

PATCH_SITES = (
    {
        "address": 0x9065C,
        "context_address": 0x90650,
        "context": bytes.fromhex("ff330179e003142aa8008052e9031f323501881a"),
        "path": "first in-range PDAF direction scan",
    },
    {
        "address": 0x90824,
        "context_address": 0x90818,
        "context": bytes.fromhex("ff2b0179e003142aa8008052e9031f323501881a"),
        "path": "second in-range PDAF direction scan",
    },
)


class CandidateError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_elf_range(data: bytes, elf: ELFFile, start: int, end: int) -> bytes:
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        segment_start = segment["p_vaddr"]
        segment_end = segment_start + segment["p_filesz"]
        if segment_start <= start and end <= segment_end:
            offset = segment["p_offset"] + start - segment_start
            return data[offset : offset + end - start]
    raise CandidateError("target function is not backed by one PT_LOAD segment")


def decode_one(code: bytes, address: int) -> str:
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    instructions = list(decoder.disasm(code, address))
    if len(instructions) != 1 or instructions[0].size != 4:
        raise CandidateError(f"could not decode one instruction at {address:#x}")
    instruction = instructions[0]
    return f"{instruction.mnemonic} {instruction.op_str}".strip()


def patch_function(original: bytes) -> tuple[bytes, list[dict]]:
    expected_size = FUNCTION_END - FUNCTION_START
    if len(original) != expected_size:
        raise CandidateError(f"function size mismatch: expected {expected_size}, got {len(original)}")
    if digest(original) != ORIGINAL_FUNCTION_SHA256:
        raise CandidateError("stock _exec_pdaf_afs_process hash mismatch")

    candidate = bytearray(original)
    records = []
    for site in PATCH_SITES:
        context_offset = site["context_address"] - FUNCTION_START
        observed_context = original[context_offset : context_offset + len(site["context"])]
        if observed_context != site["context"]:
            raise CandidateError(f"control context mismatch at {site['context_address']:#x}")
        offset = site["address"] - FUNCTION_START
        observed = original[offset : offset + 4]
        if observed != ORIGINAL_INSTRUCTION:
            raise CandidateError(f"stock instruction mismatch at {site['address']:#x}")
        candidate[offset : offset + 4] = CANDIDATE_INSTRUCTION
        records.append(
            {
                "address": site["address"],
                "path": site["path"],
                "originalHex": observed.hex(),
                "candidateHex": CANDIDATE_INSTRUCTION.hex(),
                "originalDisassembly": decode_one(observed, site["address"]),
                "candidateDisassembly": decode_one(CANDIDATE_INSTRUCTION, site["address"]),
            }
        )

    changed_offsets = [index for index, pair in enumerate(zip(original, candidate)) if pair[0] != pair[1]]
    expected_changed_offsets = [site["address"] - FUNCTION_START + 2 for site in PATCH_SITES]
    if changed_offsets != expected_changed_offsets:
        raise CandidateError(f"unexpected changed bytes: {changed_offsets!r}")
    if digest(candidate) != CANDIDATE_FUNCTION_SHA256:
        raise CandidateError("candidate function hash mismatch")
    return bytes(candidate), records


def build(library: Path, output: Path) -> dict:
    data = library.read_bytes()
    if digest(data) != LIBAAA_SHA256:
        raise CandidateError("libaaa.so is not the exact first-generation X2D 4.2.0 input")
    elf = ELFFile(io.BytesIO(data))
    if elf["e_machine"] != "EM_AARCH64":
        raise CandidateError("libaaa.so is not AArch64")
    original = read_elf_range(data, elf, FUNCTION_START, FUNCTION_END)
    candidate, patches = patch_function(original)

    output.mkdir(parents=True, exist_ok=True)
    (output / "function-original.bin").write_bytes(original)
    (output / "function-candidate.bin").write_bytes(candidate)
    manifest = {
        "status": "OFFLINE_VERIFIED_NOT_DEVICE_TESTED",
        "model": "X2D 100C first generation",
        "firmware": "4.2.0",
        "librarySha256": LIBAAA_SHA256,
        "function": FUNCTION_NAME,
        "entry": FUNCTION_START,
        "end": FUNCTION_END,
        "functionBytes": len(original),
        "originalFunctionSha256": digest(original),
        "candidateFunctionSha256": digest(candidate),
        "patches": patches,
        "scope": {
            "stillDirectionScanType": {"original": 2, "candidate": 1},
            "recordingDirectionScanType": {"original": 5, "candidate": 5},
            "absolutePositionCommandsChanged": False,
            "entryConditionsChanged": False,
            "stopOrCancelLogicChanged": False,
        },
        "offlineMetric": {
            "assumption": "stock dynamic calculation with slow_scale=0.5 before FPS/conditional boost",
            "originalRelativeRequest": 0.25,
            "candidateRelativeRequest": 0.5,
            "requestedScanSpeedRatio": 2.0,
            "affectedStaticBranches": 2,
            "changedInstructions": 2,
            "changedBytes": 2,
        },
        "limitations": [
            "Does not affect direct absolute-position focus commands.",
            "Does not prove a 2x motor speed or 2x end-to-end focus-time improvement.",
            "Must not be stacked with the existing 3/3/2 lens_ctrl_get_focus_speed candidate.",
            "No camera, lens, USB, thermal, power, overshoot, or convergence test was run.",
        ],
    }
    (output / "candidate.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path, help="exact stock X2D 4.2.0 libaaa.so")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "outputs")
    args = parser.parse_args()
    manifest = build(args.library, args.output)
    summary = {
        "status": manifest["status"],
        "functionBytes": manifest["functionBytes"],
        "changedInstructions": manifest["offlineMetric"]["changedInstructions"],
        "changedBytes": manifest["offlineMetric"]["changedBytes"],
        "requestedScanSpeedRatio": manifest["offlineMetric"]["requestedScanSpeedRatio"],
        "candidateFunctionSha256": manifest["candidateFunctionSha256"],
        "deviceModified": False,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (CandidateError, FileNotFoundError) as error:
        raise SystemExit(f"error: {error}") from error
