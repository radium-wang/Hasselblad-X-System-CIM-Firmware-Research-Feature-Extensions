#!/usr/bin/env python3
"""Read-only inspection of pinned X2D II 1.3.18.1 original MCU containers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ORIGINALS = {
    "app": ("exMCU_hb722.cont", "f4ffdae8350d7a7f536940f8965f26e24a9d6bfe6337dc8a031b9a81bbb64d11", 1854048, 0, 0x207E070F),
    "loader": ("exMCUloader.cont", "cc998e8f5c0e960482370a92881eca6353ac0a66cb9a34d9d5ca22285f418b3b", 15168, 2, 0x3B5CA7C9),
}


def content_crc(data: bytes) -> int:
    """STM32 word-fed CRC; the container checksum field is treated as zero."""
    if len(data) < 512 or len(data) % 4:
        raise ValueError("container must contain a 512-byte header and aligned words")
    table = []
    for n in range(256):
        value = n << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
        table.append(value)
    crc = 0xFFFFFFFF
    for offset in range(0, len(data), 4):
        word = 0 if offset == 12 else struct.unpack_from("<I", data, offset)[0]
        for shift in (24, 16, 8, 0):
            crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ (word >> shift)) & 255]
    return crc


def inspect(path: Path, kind: str) -> dict:
    name, expected_sha, size, expected_target, expected_crc = ORIGINALS[kind]
    # Read at most the known original size plus one byte; never write an input.
    with path.open("rb") as source:
        data = source.read(size + 1)
    if len(data) != size:
        raise ValueError("input size does not match the pinned original")
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise ValueError("SHA-256 does not match the pinned 1.3.18.1 original")
    magic, version, target, length, stored = struct.unpack_from("<IHHII", data)
    if (magic, version, target, length) != (0xBEEFC0DE, 0x100, expected_target, size - 512):
        raise ValueError("original header fields do not match documented structure")
    calculated = content_crc(data)
    if stored != calculated or calculated != expected_crc:
        raise ValueError("original CRC reproduction failed")
    return {
        "model": "Hasselblad X2D II 100C", "firmware": "1.3.18.1",
        "name": name, "bytes": size, "sha256": digest,
        "target": target, "payload_bytes": length,
        "stored_crc": f"0x{stored:08x}", "calculated_crc": f"0x{calculated:08x}",
        "match": True,
        "scope": "original identity, header and CRC only; no loader emulation or device validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(ORIGINALS), required=True)
    parser.add_argument("--input", type=Path, required=True, help="operator-supplied original container")
    args = parser.parse_args()
    try:
        result = inspect(args.input, args.kind)
    except (OSError, ValueError, struct.error) as error:
        # Do not echo an operator's personal input path in shareable output.
        message = str(error) if not isinstance(error, OSError) else "cannot read input file"
        print(f"EXMCU CHECK FAILED: {message}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
