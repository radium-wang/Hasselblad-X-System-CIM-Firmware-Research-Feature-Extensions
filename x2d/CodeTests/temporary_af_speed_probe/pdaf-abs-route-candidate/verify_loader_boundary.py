#!/usr/bin/env python3
"""Verify the stock X2D 4.2.0 AF-S loader/interposition boundary offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from elftools.elf.elffile import ELFFile


EXPECTED_EDGES = (
    ("bin/camera-service", "libdcam_frwk.so"),
    ("lib64/libdcam_frwk.so", "libduml_hal_cam.so"),
    ("lib64/libduml_hal_cam.so", "librcam.so"),
    ("lib64/librcam.so", "libaaa.so"),
)
LIBAAA_SHA256 = "feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7"
AFS_SYMBOL = "_exec_pdaf_afs_process"
AFS_ADDRESS = 0x90128
AFS_PLT = 0x2F250
AFS_GOT = 0x1DE390
AFS_CALL = 0x921B4


class BoundaryError(RuntimeError):
    pass


def needed(elf: ELFFile) -> set[str]:
    dynamic = elf.get_section_by_name(".dynamic")
    if dynamic is None:
        raise BoundaryError("ELF has no .dynamic section")
    return {tag.needed for tag in dynamic.iter_tags() if tag.entry.d_tag == "DT_NEEDED"}


def verify(root: Path) -> dict:
    for source, target in EXPECTED_EDGES:
        path = root / source
        with path.open("rb") as stream:
            if target not in needed(ELFFile(stream)):
                raise BoundaryError(f"expected dependency missing: {source} -> {target}")

    library = root / "lib64/libaaa.so"
    if hashlib.sha256(library.read_bytes()).hexdigest() != LIBAAA_SHA256:
        raise BoundaryError("not the exact stock X2D 4.2.0 libaaa.so")
    with library.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_machine"] != "EM_AARCH64":
            raise BoundaryError("libaaa.so is not AArch64")
        dynsym = elf.get_section_by_name(".dynsym")
        rela = elf.get_section_by_name(".rela.plt")
        plt = elf.get_section_by_name(".plt")
        code = elf.get_section_by_name(".text")
        dynamic = elf.get_section_by_name(".dynamic")
        if any(section is None for section in (dynsym, rela, plt, code, dynamic)):
            raise BoundaryError("required dynamic-linking section missing")

        symbols = [symbol for symbol in dynsym.iter_symbols() if symbol.name == AFS_SYMBOL]
        if len(symbols) != 1:
            raise BoundaryError("AF-S symbol is missing or ambiguous")
        symbol = symbols[0]
        if (symbol["st_value"] != AFS_ADDRESS
                or symbol["st_info"]["bind"] != "STB_GLOBAL"
                or symbol["st_other"]["visibility"] != "STV_DEFAULT"):
            raise BoundaryError("AF-S symbol is not the expected interposable export")

        for tag in dynamic.iter_tags():
            if tag.entry.d_tag == "DT_SYMBOLIC":
                raise BoundaryError("library has DT_SYMBOLIC")
            if tag.entry.d_tag == "DT_FLAGS" and tag.entry.d_val & 0x2:
                raise BoundaryError("library has DF_SYMBOLIC")

        relocations = []
        for index, relocation in enumerate(rela.iter_relocations()):
            if dynsym.get_symbol(relocation["r_info_sym"]).name == AFS_SYMBOL:
                relocations.append((index, relocation))
        if len(relocations) != 1:
            raise BoundaryError("AF-S PLT relocation is missing or ambiguous")
        index, relocation = relocations[0]
        plt_address = plt["sh_addr"] + 32 + index * 16
        if plt_address != AFS_PLT or relocation["r_offset"] != AFS_GOT:
            raise BoundaryError("AF-S PLT/GOT location differs from stock")

        decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        callers = [insn.address for insn in decoder.disasm(code.data(), code["sh_addr"])
                   if insn.mnemonic == "bl" and insn.op_str == f"#{AFS_PLT:#x}"]
        if callers != [AFS_CALL]:
            raise BoundaryError(f"AF-S PLT callers differ from stock: {callers}")
        runners = [symbol for symbol in dynsym.iter_symbols() if symbol.name == "pdaf_lib_run"]
        if len(runners) != 1 or not (runners[0]["st_value"] <= AFS_CALL
                                    < runners[0]["st_value"] + runners[0]["st_size"]):
            raise BoundaryError("AF-S call is not within pdaf_lib_run")

    return {
        "status": "STATIC_INTERPOSITION_BOUNDARY_ONLY_NOT_DEVICE_VALIDATED",
        "firmware": "X2D 100C 4.2.0",
        "neededChain": [f"{a} -> {b}" for a, b in EXPECTED_EDGES],
        "afSymbol": AFS_SYMBOL,
        "afSymbolAddress": hex(AFS_ADDRESS),
        "symbolBinding": "STB_GLOBAL/STV_DEFAULT",
        "pltAddress": hex(AFS_PLT),
        "gotAddress": hex(AFS_GOT),
        "callSite": hex(AFS_CALL),
        "caller": "pdaf_lib_run",
        "observedInProcess": False,
        "preloadTestedOnDevice": False,
        "candidateInstalled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system_root", type=Path, help="exact extracted X2D 4.2.0 /system root")
    args = parser.parse_args()
    print(json.dumps(verify(args.system_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (BoundaryError, FileNotFoundError) as exc:
        raise SystemExit(f"error: {exc}") from exc
