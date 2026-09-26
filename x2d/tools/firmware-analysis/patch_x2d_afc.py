#!/usr/bin/env python3
"""Toggle the hidden AF-C menu gate in X2D 100C 4.2.0 camera-gui.

The patch changes only the four-byte little-endian Boolean value attached to
the compiled-QML property ``CameraUI.canChangeAfc``.  On the known stock file
the effective binary difference is one byte (00 -> 01).  The embedded QML MD5
is deliberately left untouched: it is a source/dependency checksum and is
already stale after Qt's qmlsc link stage in the vendor binary.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

from elftools.elf.elffile import ELFFile

from qml_unit_dump import BINDING_SIZE, Unit, extract_symbol, find_symbol, u16, u32


CAMERA_UI_SYMBOL = "CameraUI_qml7qmlDataE"
PROPERTY_NAME = "canChangeAfc"
BOOLEAN_BINDING_TYPE = 1

# Hasselblad X2D 100C firmware 4.2.0, /system/bin/camera-gui.
STOCK_SHA256 = "16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0"

# Filled after producing and independently verifying the one-byte patch.
PATCHED_SHA256 = "08adea27596e3eb3a36c902b9f8815a73bf968e085cab6e9b34474828067a37a"


@dataclass(frozen=True)
class PatchSite:
    file_offset: int
    unit_offset: int
    current_value: int
    symbol_name: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def symbol_file_offset(elf: ELFFile, symbol) -> int:
    section_index = symbol.entry["st_shndx"]
    if not isinstance(section_index, int):
        raise ValueError(f"symbol has no concrete section: {section_index}")
    section = elf.get_section(section_index)
    return int(section["sh_offset"]) + (
        int(symbol.entry["st_value"]) - int(section["sh_addr"])
    )


def find_patch_site(path: Path) -> PatchSite:
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbol = find_symbol(elf, CAMERA_UI_SYMBOL)
        symbol_base = symbol_file_offset(elf, symbol)
        unit = Unit(extract_symbol(elf, symbol))

    qml = unit.qml_offset
    _import_count, _imports_offset, object_count, objects_offset = struct.unpack_from(
        "<4I", unit.data, qml
    )
    matches: list[PatchSite] = []
    for object_index in range(object_count):
        object_relative = u32(unit.data, qml + objects_offset + object_index * 4)
        object_base = qml + object_relative
        binding_count = u16(unit.data, object_base + 46)
        bindings_offset = u32(unit.data, object_base + 48)
        for binding_index in range(binding_count):
            binding = object_base + bindings_offset + binding_index * BINDING_SIZE
            property_name_index, flags_and_type, value = struct.unpack_from(
                "<3I", unit.data, binding
            )
            binding_type = flags_and_type >> 16
            if (
                unit.string(property_name_index) == PROPERTY_NAME
                and binding_type == BOOLEAN_BINDING_TYPE
            ):
                value_offset = binding + 8
                matches.append(
                    PatchSite(
                        file_offset=symbol_base + value_offset,
                        unit_offset=value_offset,
                        current_value=value,
                        symbol_name=symbol.name,
                    )
                )

    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one Boolean binding for {PROPERTY_NAME!r}, "
            f"found {len(matches)}"
        )
    return matches[0]


def validate_hash(digest: str, target_value: int, force: bool) -> None:
    expected = STOCK_SHA256 if target_value == 1 else PATCHED_SHA256
    if digest == expected:
        return
    if force:
        print(
            f"warning: accepting unrecognized input SHA-256 due to --force: {digest}",
            file=sys.stderr,
        )
        return
    label = "stock" if target_value == 1 else "patched"
    raise ValueError(
        f"input SHA-256 is not the known X2D 4.2.0 {label} binary:\n"
        f"  expected {expected}\n"
        f"  actual   {digest}\n"
        "Refusing to patch. Use --force only after independently verifying the file."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="source camera-gui executable")
    parser.add_argument("output", type=Path, help="new patched executable")
    parser.add_argument(
        "--disable",
        action="store_true",
        help="restore canChangeAfc=false (input must match the known patched hash)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow an unknown hash; structural and current-value checks still apply",
    )
    args = parser.parse_args()

    source = args.input.resolve()
    destination = args.output.resolve()
    if source == destination:
        raise ValueError("input and output must be different files")
    if not source.is_file():
        raise ValueError(f"input is not a regular file: {source}")

    target_value = 0 if args.disable else 1
    input_digest = sha256(source)
    validate_hash(input_digest, target_value, args.force)

    site = find_patch_site(source)
    expected_current = 1 - target_value
    if site.current_value != expected_current:
        raise ValueError(
            f"{PROPERTY_NAME} has value {site.current_value}, expected "
            f"{expected_current}; refusing to patch"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    with destination.open("r+b") as stream:
        stream.seek(site.file_offset)
        before = stream.read(4)
        if before != struct.pack("<I", expected_current):
            raise ValueError(
                f"file-offset verification failed at 0x{site.file_offset:x}: "
                f"read {before.hex()}"
            )
        stream.seek(site.file_offset)
        stream.write(struct.pack("<I", target_value))

    verified = find_patch_site(destination)
    if verified.current_value != target_value:
        raise ValueError("post-write QML verification failed")

    output_digest = sha256(destination)
    print(f"symbol:        {site.symbol_name}")
    print(f"property:      {PROPERTY_NAME}")
    print(f"file offset:   0x{site.file_offset:x}")
    print(f"unit offset:   0x{site.unit_offset:x}")
    print(f"change:        {expected_current} -> {target_value}")
    print(f"input SHA-256: {input_digest}")
    print(f"output SHA-256:{output_digest}")
    print(f"output:        {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
