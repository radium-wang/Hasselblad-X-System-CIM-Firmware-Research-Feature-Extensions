#!/usr/bin/env python3
"""Inspect a Qt 6.4 QML compiled unit embedded in an ELF symbol.

This is intentionally a small, read-only parser.  It is sufficient for the
QML data structures used by the X2D 4.2.0 camera-gui (Qt 6.4.1) and prints the
imports, objects, properties, and bindings, including stored script source.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile


UNIT_HEADER_SIZE = 248
OBJECT_SIZE = 84
BINDING_SIZE = 24
PROPERTY_SIZE = 12

BINDING_TYPES = {
    0: "Invalid",
    1: "Boolean",
    2: "Number",
    3: "String",
    4: "Null",
    5: "Translation",
    6: "TranslationById",
    7: "Script",
    8: "Object",
    9: "AttachedProperty",
    10: "GroupProperty",
}

BINDING_FLAGS = {
    0x001: "signal-expression",
    0x002: "signal-object",
    0x004: "on-assignment",
    0x008: "readonly-init",
    0x010: "resolved-enum",
    0x020: "list-item",
    0x040: "alias",
    0x080: "deferred",
    0x100: "custom-parser",
    0x200: "function-expression",
    0x400: "property-observer",
}


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def location(raw: int) -> str:
    return f"{raw & 0xFFFFF}:{raw >> 20}"


def find_symbol(elf: ELFFile, query: str):
    symtab = elf.get_section_by_name(".symtab")
    if symtab is None:
        raise ValueError("ELF has no .symtab")
    matches = [symbol for symbol in symtab.iter_symbols() if query in symbol.name]
    if not matches:
        raise ValueError(f"no symbol contains {query!r}")
    exact = [symbol for symbol in matches if symbol.name == query]
    if exact:
        return exact[0]
    if len(matches) != 1:
        names = "\n  ".join(symbol.name for symbol in matches[:20])
        raise ValueError(f"symbol query is ambiguous:\n  {names}")
    return matches[0]


def extract_symbol(elf: ELFFile, symbol) -> bytes:
    section_index = symbol.entry["st_shndx"]
    if not isinstance(section_index, int):
        raise ValueError(f"symbol has no concrete section: {section_index}")
    section = elf.get_section(section_index)
    start = int(symbol.entry["st_value"]) - int(section["sh_addr"])
    size = int(symbol.entry["st_size"])
    return section.data()[start : start + size]


class Unit:
    def __init__(self, data: bytes):
        self.data = data
        if len(data) < UNIT_HEADER_SIZE or data[:8] != b"qv4cdata":
            raise ValueError("symbol does not begin with a Qt compiled-unit header")

        self.version = u32(data, 8)
        self.qt_version = u32(data, 12)
        self.unit_size = u32(data, 24)

        values = struct.unpack_from("<35I", data, 108)
        self.flags = values[0]
        pairs = values[1:31]
        names = (
            "strings",
            "functions",
            "classes",
            "template_objects",
            "blocks",
            "lookups",
            "regexps",
            "constants",
            "js_classes",
            "translations",
            "local_exports",
            "indirect_exports",
            "star_exports",
            "import_entries",
            "module_requests",
        )
        self.tables = {
            name: (pairs[index * 2], pairs[index * 2 + 1])
            for index, name in enumerate(names)
        }
        self.root_function = values[31]
        self.source_file_index = values[32]
        self.final_url_index = values[33]
        self.qml_offset = values[34]
        self.strings = self._read_strings()

    def _read_strings(self) -> list[str]:
        count, table_offset = self.tables["strings"]
        result = []
        for index in range(count):
            string_offset = u32(self.data, table_offset + index * 4)
            length = i32(self.data, string_offset)
            if length < 0:
                raise ValueError(f"negative string length at index {index}")
            raw = self.data[string_offset + 4 : string_offset + 4 + length * 2]
            result.append(raw.decode("utf-16le", errors="replace"))
        return result

    def string(self, index: int) -> str:
        if index == 0xFFFFFFFF:
            return "<none>"
        if not 0 <= index < len(self.strings):
            return f"<bad-string:{index}>"
        return self.strings[index]

    def constant(self, index: int) -> str:
        count, offset = self.tables["constants"]
        if not 0 <= index < count:
            return f"<bad-constant:{index}>"
        raw = self.data[offset + index * 8 : offset + index * 8 + 8]
        bits = struct.unpack("<Q", raw)[0]
        number = struct.unpack("<d", raw)[0]
        return f"{number!r} [0x{bits:016x}]"

    def lookup(self, index: int) -> tuple[int, str]:
        count, offset = self.tables["lookups"]
        if not 0 <= index < count:
            return (-1, f"<bad-lookup:{index}>")
        raw = u32(self.data, offset + index * 4)
        return (raw & 0xF, self.string(raw >> 4))


def binding_value(unit: Unit, binding_type: int, value: int, string_index: int) -> str:
    if binding_type == 1:
        return "true" if value else "false"
    if binding_type == 2:
        return unit.constant(value)
    if binding_type == 3:
        return repr(unit.string(string_index))
    if binding_type == 4:
        return "null"
    if binding_type in (5, 6):
        return f"translation[{value}]"
    if binding_type == 7:
        return f"function[{value}] {unit.string(string_index)!r}"
    if binding_type in (8, 9, 10):
        return f"object[{value}]"
    return f"value=0x{value:x} string={unit.string(string_index)!r}"


def dump(unit: Unit, show_strings: bool, show_functions: bool, show_lookups: bool) -> None:
    major = (unit.qt_version >> 16) & 0xFF
    minor = (unit.qt_version >> 8) & 0xFF
    patch = unit.qt_version & 0xFF
    print(
        f"unit: version=0x{unit.version:x} qt={major}.{minor}.{patch} "
        f"size={unit.unit_size} flags=0x{unit.flags:x}"
    )
    print(
        "tables: "
        + ", ".join(f"{name}={count}" for name, (count, _) in unit.tables.items())
    )
    print(f"source: {unit.string(unit.source_file_index)}")
    print(f"url:    {unit.string(unit.final_url_index)}")

    if show_strings:
        print("\nstrings:")
        for index, value in enumerate(unit.strings):
            print(f"  [{index:3}] {value!r}")

    if show_functions:
        count, table_offset = unit.tables["functions"]
        print("\nfunctions:")
        for index in range(count):
            function_offset = u32(unit.data, table_offset + index * 4)
            base = function_offset
            code_offset = u32(unit.data, base)
            code_size = u32(unit.data, base + 4)
            name_index = u32(unit.data, base + 8)
            n_formals = u16(unit.data, base + 14)
            n_registers = u32(unit.data, base + 36)
            raw_location = u32(unit.data, base + 40)
            code = unit.data[base + code_offset : base + code_offset + code_size]
            print(
                f"  [{index:3}] name={unit.string(name_index)!r} "
                f"formals={n_formals} registers={n_registers} "
                f"codeSize={code_size} @{location(raw_location)} "
                f"code={code.hex()}"
            )

    if show_lookups:
        count, _ = unit.tables["lookups"]
        print("\nlookups:")
        for index in range(count):
            lookup_type, name = unit.lookup(index)
            print(f"  [{index:4}] type={lookup_type} name={name!r}")

    qml = unit.qml_offset
    import_count, imports_offset, object_count, objects_offset = struct.unpack_from(
        "<4I", unit.data, qml
    )
    print(f"\nqml: imports={import_count} objects={object_count}")
    for index in range(import_count):
        base = qml + imports_offset + index * 20
        import_type, uri_index, qualifier_index, raw_location = struct.unpack_from(
            "<4I", unit.data, base
        )
        print(
            f"  import[{index}] type={import_type} uri={unit.string(uri_index)!r} "
            f"as={unit.string(qualifier_index)!r} @{location(raw_location)}"
        )

    for object_index in range(object_count):
        object_relative = u32(unit.data, qml + objects_offset + object_index * 4)
        base = qml + object_relative
        inherited_index = u32(unit.data, base)
        id_index = u32(unit.data, base + 4)
        flags_and_id = u32(unit.data, base + 8)
        n_functions = u16(unit.data, base + 16)
        n_properties = u16(unit.data, base + 18)
        properties_offset = u32(unit.data, base + 24)
        n_aliases = u16(unit.data, base + 32)
        n_enums = u16(unit.data, base + 34)
        n_signals = u16(unit.data, base + 44)
        n_bindings = u16(unit.data, base + 46)
        bindings_offset = u32(unit.data, base + 48)
        raw_location = u32(unit.data, base + 60)
        object_id = (flags_and_id >> 16) & 0xFFFF
        if object_id & 0x8000:
            object_id -= 0x10000

        print(
            f"\nobject[{object_index}] type={unit.string(inherited_index)!r} "
            f"id={unit.string(id_index)!r} objectId={object_id} "
            f"@{location(raw_location)}"
        )
        print(
            f"  counts: functions={n_functions} properties={n_properties} "
            f"aliases={n_aliases} enums={n_enums} signals={n_signals} "
            f"bindings={n_bindings}"
        )

        for property_index in range(n_properties):
            prop = base + properties_offset + property_index * PROPERTY_SIZE
            name_index, property_data, prop_location = struct.unpack_from(
                "<3I", unit.data, prop
            )
            type_value = property_data & 0x0FFFFFFF
            modifiers = []
            if property_data & (1 << 28):
                modifiers.append("required")
            if property_data & (1 << 29):
                modifiers.append("builtin")
            if property_data & (1 << 30):
                modifiers.append("list")
            if property_data & (1 << 31):
                modifiers.append("readonly")
            print(
                f"  property[{property_index}] {unit.string(name_index)!r} "
                f"type={type_value} {'|'.join(modifiers) or '-'} "
                f"@{location(prop_location)}"
            )

        for binding_index in range(n_bindings):
            item = base + bindings_offset + binding_index * BINDING_SIZE
            (
                property_name_index,
                flags_and_type,
                value,
                string_index,
                binding_location,
                value_location,
            ) = struct.unpack_from("<6I", unit.data, item)
            binding_flags = flags_and_type & 0xFFFF
            binding_type = flags_and_type >> 16
            flag_names = [
                name for flag, name in BINDING_FLAGS.items() if binding_flags & flag
            ]
            rendered = binding_value(unit, binding_type, value, string_index)
            print(
                f"  binding[{binding_index}] {unit.string(property_name_index)!r} "
                f"{BINDING_TYPES.get(binding_type, str(binding_type))} "
                f"flags={'|'.join(flag_names) or '-'} value={rendered} "
                f"@{location(binding_location)} value@{location(value_location)}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("symbol", help="exact symbol name or unique substring")
    parser.add_argument("--strings", action="store_true", help="also dump all strings")
    parser.add_argument("--functions", action="store_true", help="also dump function metadata")
    parser.add_argument("--lookups", action="store_true", help="also dump lookup names")
    parser.add_argument(
        "--aot-symbol",
        help="also decode the associated QQmlPrivate::AOTCompiledFunction array",
    )
    args = parser.parse_args()

    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        symbol = find_symbol(elf, args.symbol)
        data = extract_symbol(elf, symbol)
        aot_data = None
        symbols_by_address: dict[int, list[str]] = {}
        if args.aot_symbol:
            aot_symbol = find_symbol(elf, args.aot_symbol)
            aot_data = extract_symbol(elf, aot_symbol)
            symtab = elf.get_section_by_name(".symtab")
            for item in symtab.iter_symbols():
                address = int(item.entry["st_value"])
                if address:
                    symbols_by_address.setdefault(address, []).append(item.name)
    print(f"symbol: {symbol.name} size={len(data)}")
    unit = Unit(data)
    if unit.unit_size > len(data):
        raise ValueError(
            f"compiled unit declares {unit.unit_size} bytes but symbol has {len(data)}"
        )
    dump(unit, args.strings, args.functions, args.lookups)
    if aot_data is not None:
        # Qt 6.4.1 AOTCompiledFunction is 48 bytes on LP64:
        # qintptr extraData (the function index), QMetaType, QList<QMetaType>,
        # and a native function pointer.  The middle 32 bytes are opaque here.
        print(f"\naot: entries={len(aot_data) // 48}")
        for index in range(len(aot_data) // 48):
            function_index = struct.unpack_from("<q", aot_data, index * 48)[0]
            return_type = struct.unpack_from("<Q", aot_data, index * 48 + 8)[0]
            function = struct.unpack_from("<Q", aot_data, index * 48 + 40)[0]
            function_names = symbols_by_address.get(function, [])
            preferred_names = [name for name in function_names if not name.startswith("$")]
            function_name = (preferred_names or function_names or [""])[0]
            print(
                f"  [{index:2}] functionIndex={function_index:3} "
                f"returnType=0x{return_type:x} function=0x{function:x} {function_name}"
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
