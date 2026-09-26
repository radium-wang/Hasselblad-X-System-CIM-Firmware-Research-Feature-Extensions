#!/usr/bin/env python3
"""Build a reversible X2D 4.2.0 ControlScreen QML-unit clone with AF-C.

The stock ControlScreenViewModel contains only two FocusModeListItem objects:
AF-S and MF.  This tool does not edit camera-gui.  It extracts the exact
compiled QML unit from a hash-pinned stock executable and emits a standalone
clone containing a third list item:

    Continuous Autofocus / AF-C icon / E_FocusModes_Afc

The clone is intended to be embedded in a temporary LD_PRELOAD library.  The
library changes the CachedQmlUnit pointer before the main executable registers
its QML cache; the stock executable and /system inode remain untouched.
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
UNIT_SYMBOL = "ControlScreenViewModel_qml7qmlDataE"
EXPECTED_UNIT_SIZE = 0x115C4
EXPECTED_QML_OFFSET = 0xF430
EXPECTED_OBJECTS = 13
EXPECTED_FUNCTIONS = 204
EXPECTED_STRINGS = 650

FOCUS_ITEM_TYPE = "FocusModeListItem"
FOCUS_MODEL = "focusModeModel"
AFS_TEXT = "Autofocus"
AFC_TEXT = "Continuous Autofocus"
AFC_ICON = "image://svg/ic_controlscreen_focus_mode_AF-C"
HBLM_TYPES_LOOKUP = 423
AFC_ENUM_LOOKUP = 424


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def align8(value: int) -> int:
    return (value + 7) & ~7


def append_aligned(blob: bytearray, data: bytes) -> int:
    while len(blob) & 7:
        blob.append(0)
    offset = len(blob)
    blob.extend(data)
    while len(blob) & 7:
        blob.append(0)
    return offset


def string_record(text: str) -> bytes:
    raw = text.encode("utf-16le")
    data = struct.pack("<i", len(text)) + raw + b"\0\0"
    return data + b"\0" * (align8(len(data)) - len(data))


def object_layout(unit: Unit) -> tuple[int, list[int]]:
    qml = unit.qml_offset
    _imports, _imports_offset, count, table_offset = struct.unpack_from(
        "<4I", unit.data, qml
    )
    offsets = [u32(unit.data, qml + table_offset + index * 4) for index in range(count)]
    return table_offset, offsets


def object_block(unit: Unit, offsets: list[int], index: int) -> bytes:
    start = unit.qml_offset + offsets[index]
    end = (
        unit.qml_offset + offsets[index + 1]
        if index + 1 < len(offsets)
        else unit.unit_size
    )
    return unit.data[start:end]


def binding_fields(block: bytes | bytearray, index: int) -> tuple[int, ...]:
    table = u32(block, 48)
    return struct.unpack_from("<6I", block, table + index * BINDING_SIZE)


def find_focus_objects(unit: Unit, offsets: list[int]) -> tuple[int, int, int]:
    parent = -1
    afs = -1
    mf = -1
    for index, relative in enumerate(offsets):
        base = unit.qml_offset + relative
        inherited = unit.string(u32(unit.data, base))
        bindings = u16(unit.data, base + 46)
        binding_offset = u32(unit.data, base + 48)
        if inherited == "QtObject":
            names = [
                unit.string(u32(unit.data, base + binding_offset + item * BINDING_SIZE))
                for item in range(bindings)
            ]
            if names.count(FOCUS_MODEL) == 2:
                parent = index
        if inherited != FOCUS_ITEM_TYPE:
            continue
        values: dict[str, tuple[int, ...]] = {}
        for item in range(bindings):
            fields = struct.unpack_from(
                "<6I", unit.data, base + binding_offset + item * BINDING_SIZE
            )
            values[unit.string(fields[0])] = fields
        text_fields = values.get("text")
        if not text_fields:
            continue
        text = unit.string(text_fields[3])
        if text == AFS_TEXT:
            afs = index
        elif text == "Manual Focus":
            mf = index
    if min(parent, afs, mf) < 0:
        raise ValueError(
            f"could not resolve exact focus model (parent={parent}, afs={afs}, mf={mf})"
        )
    return parent, afs, mf


def build_clone(unit: Unit) -> bytes:
    if unit.unit_size != EXPECTED_UNIT_SIZE or unit.qml_offset != EXPECTED_QML_OFFSET:
        raise ValueError(
            f"unexpected unit geometry: size=0x{unit.unit_size:x} "
            f"qml=0x{unit.qml_offset:x}"
        )
    if unit.tables["functions"][0] != EXPECTED_FUNCTIONS:
        raise ValueError("unexpected function count")
    if unit.tables["strings"][0] != EXPECTED_STRINGS:
        raise ValueError("unexpected string count")

    old_object_table, object_offsets = object_layout(unit)
    if len(object_offsets) != EXPECTED_OBJECTS:
        raise ValueError("unexpected object count")
    parent_index, afs_index, mf_index = find_focus_objects(unit, object_offsets)
    if (parent_index, afs_index, mf_index) != (1, 6, 5):
        raise ValueError(
            "focus model no longer matches the verified X2D 4.2.0 layout: "
            f"{(parent_index, afs_index, mf_index)}"
        )

    blob = bytearray(unit.data[: unit.unit_size])

    # Add the label to a replacement string-offset table.  The AF-C icon is
    # already present in the stock unit because current-mode rendering knows
    # about AF-C even though the selection list omits it.
    afc_text_index = len(unit.strings)
    afc_text_offset = append_aligned(blob, string_record(AFC_TEXT))
    string_count, old_string_table = unit.tables["strings"]
    string_offsets = [u32(unit.data, old_string_table + i * 4) for i in range(string_count)]
    string_offsets.append(afc_text_offset)
    new_string_table = append_aligned(
        blob, b"".join(struct.pack("<I", value) for value in string_offsets)
    )

    # Clone the tiny AF-S expression function and change only its two lookup
    # operands from HblmTypes/E_FocusModes_Afs to the already existing
    # HblmTypes/E_FocusModes_Afc lookup pair.
    function_count, old_function_table = unit.tables["functions"]
    function_offsets = [
        u32(unit.data, old_function_table + i * 4) for i in range(function_count)
    ]
    afs_function_index = binding_fields(object_block(unit, object_offsets, afs_index), 3)[2]
    if afs_function_index != 191:
        raise ValueError(f"unexpected AF-S function index: {afs_function_index}")
    afs_function_offset = function_offsets[afs_function_index]
    next_function_offset = function_offsets[afs_function_index + 1]
    function = bytearray(unit.data[afs_function_offset:next_function_offset])
    code_offset = u32(function, 0)
    code_size = u32(function, 4)
    expected_code = bytes.fromhex("2f dc 02 00 00 3d dd 02 00 00 18 06 02")
    if function[code_offset : code_offset + code_size] != expected_code:
        raise ValueError("AF-S bytecode no longer matches the verified context")
    struct.pack_into("<I", function, code_offset + 1, HBLM_TYPES_LOOKUP)
    struct.pack_into("<I", function, code_offset + 6, AFC_ENUM_LOOKUP)
    if unit.lookup(HBLM_TYPES_LOOKUP)[1] != "HblmTypes" or unit.lookup(
        AFC_ENUM_LOOKUP
    )[1] != "E_FocusModes_Afc":
        raise ValueError("AF-C lookup pair does not match expected names")
    afc_function_index = function_count
    afc_function_offset = append_aligned(blob, bytes(function))
    function_offsets.append(afc_function_offset)
    new_function_table = append_aligned(
        blob, b"".join(struct.pack("<I", value) for value in function_offsets)
    )

    # Clone the AF-S FocusModeListItem, give it a distinct label/icon and bind
    # its focusMode to the new AF-C function.  valid remains literal true: the
    # clone exists only in this explicit temporary runtime experiment.
    afc_object = bytearray(object_block(unit, object_offsets, afs_index))
    if len(afc_object) != 0xB8 or u16(afc_object, 46) != 4:
        raise ValueError("unexpected FocusModeListItem block layout")
    afc_icon_index = unit.strings.index(AFC_ICON)
    binding_table = u32(afc_object, 48)
    struct.pack_into("<I", afc_object, binding_table + 0 * BINDING_SIZE + 12, afc_text_index)
    struct.pack_into("<I", afc_object, binding_table + 1 * BINDING_SIZE + 12, afc_icon_index)
    struct.pack_into("<I", afc_object, binding_table + 3 * BINDING_SIZE + 8, afc_function_index)
    afc_object_offset = append_aligned(blob, bytes(afc_object))
    afc_object_index = len(object_offsets)

    # Clone the QtObject that owns focusModeModel.  Insert the new list-item
    # binding between the existing AF-S and MF bindings, preserving both.
    parent = object_block(unit, object_offsets, parent_index)
    old_bindings = u16(parent, 46)
    parent_binding_offset = u32(parent, 48)
    if len(parent) != 0x280 or old_bindings != 16 or parent_binding_offset != 0xFC:
        raise ValueError("unexpected focus-model parent layout")
    before_insert = parent_binding_offset + 4 * BINDING_SIZE
    new_binding = bytearray(parent[
        parent_binding_offset + 3 * BINDING_SIZE:
        parent_binding_offset + 4 * BINDING_SIZE
    ])
    if unit.string(u32(new_binding, 0)) != FOCUS_MODEL:
        raise ValueError("focus list binding context mismatch")
    struct.pack_into("<I", new_binding, 8, afc_object_index)
    parent_clone = bytearray(parent[:before_insert])
    parent_clone.extend(new_binding)
    parent_clone.extend(parent[before_insert : parent_binding_offset + old_bindings * BINDING_SIZE])
    while len(parent_clone) & 7:
        parent_clone.append(0)
    struct.pack_into("<H", parent_clone, 46, old_bindings + 1)
    parent_object_offset = append_aligned(blob, bytes(parent_clone))

    # Replace the QML object-offset table.  Object 1 now points at the expanded
    # parent clone; original objects remain immutable and object 13 is AF-C.
    new_object_offsets = list(object_offsets)
    new_object_offsets[parent_index] = parent_object_offset - unit.qml_offset
    new_object_offsets.append(afc_object_offset - unit.qml_offset)
    new_object_table = append_aligned(
        blob, b"".join(struct.pack("<I", value) for value in new_object_offsets)
    )

    # Unit header fields: unitSize, string/function tables.  QmlUnit fields:
    # nObjects and offsetToObjects (relative to QmlUnit).
    struct.pack_into("<I", blob, 24, len(blob))
    struct.pack_into("<II", blob, 112, len(string_offsets), new_string_table)
    struct.pack_into("<II", blob, 120, len(function_offsets), new_function_table)
    struct.pack_into("<II", blob, unit.qml_offset + 8, len(new_object_offsets), new_object_table - unit.qml_offset)

    # qv4 compiler checksum: MD5 of all bytes after md5Checksum.  The embedded
    # vendor unit's checksum is not used as a signature, but keeping it
    # internally coherent makes the clone independently inspectable.
    blob[76:92] = hashlib.md5(blob[92:]).digest()
    struct.pack_into("<I", blob, 24, len(blob))

    # Parse the result again and prove the new model has three independent
    # list bindings and the old unit geometry was not edited in place.
    verified = Unit(bytes(blob))
    if verified.unit_size != len(blob):
        raise ValueError("generated unitSize mismatch")
    _table, verified_offsets = object_layout(verified)
    if len(verified_offsets) != 14:
        raise ValueError("generated object count is not 14")
    parent_base = verified.qml_offset + verified_offsets[parent_index]
    focus_bindings = []
    for index in range(u16(verified.data, parent_base + 46)):
        item = parent_base + u32(verified.data, parent_base + 48) + index * BINDING_SIZE
        fields = struct.unpack_from("<6I", verified.data, item)
        if verified.string(fields[0]) == FOCUS_MODEL:
            focus_bindings.append(fields[2])
    if focus_bindings != [afs_index, afc_object_index, mf_index]:
        raise ValueError(f"generated focus list order mismatch: {focus_bindings}")
    generated = verified.qml_offset + verified_offsets[afc_object_index]
    rendered: dict[str, tuple[int, ...]] = {}
    for index in range(u16(verified.data, generated + 46)):
        item = generated + u32(verified.data, generated + 48) + index * BINDING_SIZE
        fields = struct.unpack_from("<6I", verified.data, item)
        rendered[verified.string(fields[0])] = fields
    if verified.string(rendered["text"][3]) != AFC_TEXT:
        raise ValueError("generated AF-C label mismatch")
    if verified.string(rendered["icon"][3]) != AFC_ICON:
        raise ValueError("generated AF-C icon mismatch")
    if rendered["focusMode"][2] != afc_function_index:
        raise ValueError("generated AF-C function binding mismatch")
    if rendered["valid"][2] != 1:
        raise ValueError("generated AF-C validity mismatch")
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
    print(f"stock unit:   {len(unit.data)} bytes, 13 objects, 2 focus items")
    print(f"clone unit:   {len(clone)} bytes, 14 objects, 3 focus items")
    print("focus order:  Autofocus -> Continuous Autofocus -> Manual Focus")
    print(f"SHA-256:      {hashlib.sha256(clone).hexdigest()}")
    print(f"output:       {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
