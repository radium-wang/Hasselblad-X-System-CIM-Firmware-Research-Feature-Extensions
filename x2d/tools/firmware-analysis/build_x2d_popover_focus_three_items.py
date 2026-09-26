#!/usr/bin/env python3
"""Build a reversible X2D 4.2.0 three-item focus-popover QML clone.

The stock PopoverFocusMode.qml hard-codes ``numItems: 2``.  Adding AF-C to
ControlScreenViewModel therefore creates a working third delegate outside the
two-item popover geometry.  This tool changes only that verified numeric
constant from 2 to 3 in a standalone compiled-QML clone.  It never edits the
camera-gui input file.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile

from qml_unit_dump import BINDING_SIZE, Unit, extract_symbol, find_symbol, u16, u32


STOCK_SHA256 = "16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0"
UNIT_SYMBOL = "PopoverFocusMode_qml7qmlDataE"
EXPECTED_UNIT_SIZE = 0x34F0
EXPECTED_QML_OFFSET = 0x2B78
EXPECTED_OBJECTS = 9
EXPECTED_FUNCTIONS = 44
EXPECTED_STRINGS = 135
EXPECTED_CONSTANTS = 12
LIST_TYPE = "HblListView"
LIST_ID = "list"
NUM_ITEMS = "numItems"
QV4_DOUBLE_ENCODE_MASK = 0xFFFC000000000000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encoded_double(value: float) -> int:
    raw = struct.unpack("<Q", struct.pack("<d", value))[0]
    return raw ^ QV4_DOUBLE_ENCODE_MASK


def object_offsets(unit: Unit) -> list[int]:
    count = u32(unit.data, unit.qml_offset + 8)
    table = u32(unit.data, unit.qml_offset + 12)
    return [
        u32(unit.data, unit.qml_offset + table + index * 4)
        for index in range(count)
    ]


def find_num_items_constant(unit: Unit) -> tuple[int, int, int]:
    matches = []
    for object_index, relative in enumerate(object_offsets(unit)):
        base = unit.qml_offset + relative
        if unit.string(u32(unit.data, base)) != LIST_TYPE:
            continue
        if unit.string(u32(unit.data, base + 4)) != LIST_ID:
            continue
        count = u16(unit.data, base + 46)
        table = u32(unit.data, base + 48)
        for binding_index in range(count):
            binding = base + table + binding_index * BINDING_SIZE
            fields = struct.unpack_from("<6I", unit.data, binding)
            binding_type = fields[1] >> 16
            if unit.string(fields[0]) == NUM_ITEMS and binding_type == 2:
                matches.append((object_index, binding_index, fields[2]))
    if len(matches) != 1:
        raise ValueError(f"expected one numItems numeric binding, found {matches}")
    return matches[0]


def build_clone(unit: Unit) -> bytes:
    if unit.unit_size != EXPECTED_UNIT_SIZE or unit.qml_offset != EXPECTED_QML_OFFSET:
        raise ValueError(
            f"unexpected unit geometry: size=0x{unit.unit_size:x} "
            f"qml=0x{unit.qml_offset:x}"
        )
    if len(object_offsets(unit)) != EXPECTED_OBJECTS:
        raise ValueError("unexpected object count")
    if unit.tables["functions"][0] != EXPECTED_FUNCTIONS:
        raise ValueError("unexpected function count")
    if unit.tables["strings"][0] != EXPECTED_STRINGS:
        raise ValueError("unexpected string count")
    constant_count, constant_table = unit.tables["constants"]
    if constant_count != EXPECTED_CONSTANTS:
        raise ValueError("unexpected constant count")

    object_index, binding_index, constant_index = find_num_items_constant(unit)
    if (object_index, binding_index, constant_index) != (4, 9, 0):
        raise ValueError(
            "numItems binding no longer matches verified X2D 4.2.0 context: "
            f"{(object_index, binding_index, constant_index)}"
        )
    constant_offset = constant_table + constant_index * 8
    if u32(unit.data, constant_offset) | (u32(unit.data, constant_offset + 4) << 32) != encoded_double(2.0):
        raise ValueError("stock numItems constant is not encoded double 2")

    blob = bytearray(unit.data[: unit.unit_size])
    struct.pack_into("<Q", blob, constant_offset, encoded_double(3.0))
    blob[76:92] = hashlib.md5(blob[92:]).digest()

    verified = Unit(bytes(blob))
    if verified.unit_size != EXPECTED_UNIT_SIZE:
        raise ValueError("clone unitSize changed")
    verified_object, verified_binding, verified_constant = find_num_items_constant(verified)
    if (verified_object, verified_binding, verified_constant) != (4, 9, 0):
        raise ValueError("clone numItems binding changed unexpectedly")
    verified_constant_offset = verified.tables["constants"][1]
    raw = struct.unpack_from("<Q", verified.data, verified_constant_offset)[0]
    if raw != encoded_double(3.0):
        raise ValueError("clone numItems constant is not encoded double 3")
    return bytes(blob)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("camera_gui", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    digest = sha256(args.camera_gui)
    if digest != STOCK_SHA256:
        raise ValueError(
            "camera-gui is not the exact supported X2D 4.2.0 build:\n"
            f"  expected {STOCK_SHA256}\n  actual   {digest}"
        )
    with args.camera_gui.open("rb") as stream:
        elf = ELFFile(stream)
        symbol = find_symbol(elf, UNIT_SYMBOL)
        unit = Unit(extract_symbol(elf, symbol))
    clone = build_clone(unit)
    if args.output.exists():
        if args.output.read_bytes() == clone:
            print(f"unchanged: {args.output}")
        else:
            raise ValueError(f"refusing to overwrite different output: {args.output}")
    else:
        args.output.write_bytes(clone)
    print(f"source symbol: {symbol.name}")
    print(f"stock unit:   {len(unit.data)} bytes, numItems=2")
    print(f"clone unit:   {len(clone)} bytes, numItems=3")
    print(f"SHA-256:      {hashlib.sha256(clone).hexdigest()}")
    print(f"output:       {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
