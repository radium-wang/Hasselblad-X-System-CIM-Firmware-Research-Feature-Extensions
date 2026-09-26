#!/usr/bin/env python3
"""Read-only, conservative dynamic-symbol audit for an ML runtime transplant.

All system/lib64 libraries are treated as visible. This overestimates what the
Android linker can actually load, so a missing strong symbol is a hard blocker;
zero missing symbols would still not establish ABI or device compatibility.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile


def dynamic_symbols(path: Path) -> tuple[set[str], set[str]]:
    """Return strong undefined imports and globally exported symbol names."""
    with path.open("rb") as stream:
        symbols = ELFFile(stream).get_section_by_name(".dynsym")
        if symbols is None:
            return set(), set()
        imports: set[str] = set()
        exports: set[str] = set()
        for symbol in symbols.iter_symbols():
            if not symbol.name:
                continue
            binding = symbol.entry.st_info.bind
            visibility = symbol.entry.st_other.visibility
            if symbol.entry.st_shndx == "SHN_UNDEF":
                if binding == "STB_GLOBAL":
                    imports.add(symbol.name)
            elif binding in ("STB_GLOBAL", "STB_WEAK") and visibility in (
                "STV_DEFAULT", "STV_PROTECTED"
            ):
                exports.add(symbol.name)
        return imports, exports


def library_exports(system_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in sorted((system_root / "lib64").glob("*.so")):
        _, exports = dynamic_symbols(path)
        result[path.name] = exports
    return result


def providers(name: str, libraries: dict[str, set[str]]) -> list[str]:
    return sorted(library for library, exports in libraries.items() if name in exports)


def build_report(source_system: Path, target_system: Path) -> dict[str, object]:
    source_imports, _ = dynamic_symbols(source_system / "bin" / "dji_ml")
    target_imports, _ = dynamic_symbols(target_system / "bin" / "dji_ml")
    source_libraries = library_exports(source_system)
    target_libraries = library_exports(target_system)
    target_available = set().union(*target_libraries.values())
    source_available = set().union(*source_libraries.values())
    missing = sorted(source_imports - target_available)
    return {
        "scope": "X2D II dji_ml imports against X2D system/lib64",
        "method": "unversioned ELF dynamic names; all lib64 libraries assumed visible",
        "source_strong_import_count": len(source_imports),
        "source_unresolved_in_source": sorted(source_imports - source_available),
        "target_strong_import_count": len(target_imports),
        "target_unresolved_in_target": sorted(target_imports - target_available),
        "source_imports_missing_in_target": [
            {
                "symbol": name,
                "source_providers": providers(name, source_libraries),
                "source_only_providers": [
                    library for library in providers(name, source_libraries)
                    if library not in target_libraries
                ],
            }
            for name in missing
        ],
        "source_imports_missing_in_target_count": len(missing),
        "direct_runtime_substitution_symbol_complete": not missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-system-root", required=True, type=Path)
    parser.add_argument("--target-system-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.source_system_root, args.target_system_root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
