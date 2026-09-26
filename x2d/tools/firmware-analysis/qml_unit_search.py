#!/usr/bin/env python3
"""Find Qt 6.4 compiled QML units whose string table matches a query."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile

from qml_unit_dump import Unit, extract_symbol


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("elf", type=Path)
    parser.add_argument("queries", nargs="+")
    args = parser.parse_args()
    lowered = [query.casefold() for query in args.queries]

    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        if symtab is None:
            raise ValueError("ELF has no .symtab")
        for symbol in symtab.iter_symbols():
            if "qmlDataE" not in symbol.name or not int(symbol.entry["st_size"]):
                continue
            try:
                unit = Unit(extract_symbol(elf, symbol))
            except (ValueError, IndexError):
                continue
            matches = [
                (index, value)
                for index, value in enumerate(unit.strings)
                if any(query in value.casefold() for query in lowered)
            ]
            if matches:
                print(symbol.name)
                for index, value in matches:
                    print(f"  [{index}] {value!r}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
