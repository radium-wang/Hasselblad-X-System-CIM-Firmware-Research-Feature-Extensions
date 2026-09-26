"""Read-only feasibility audit for embedding the menu extension in stock GUI.

No binary is written or connected camera accessed. Run with X2D_SYSTEM_ROOT
pointing at an extracted, hash-pinned 4.2.0 /system tree.
"""
import io
import json
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "x2d/CodeTests/temporary_af_speed_probe"))
from inspect_menu_resources import GUI_SHA, load_gui  # noqa: E402

CACHE_RELOCATIONS = {
    "ControlScreenViewModel": (0x20AC690, 0x16C6300),
    "MainScreen": (0x20ACC78, 0x17B67F0),
    "PopoverFocusMode": (0x20AD2C0, 0x1876EA0),
}
GATE_VADDR = 0x18A2A64


def main():
    binary = load_gui()
    with io.BytesIO(binary.data) as stream:
        elf = ELFFile(stream)
        headers = list(elf.iter_segments())
        phdr = next(segment for segment in headers if segment["p_type"] == "PT_PHDR")
        interp = next(segment for segment in headers if segment["p_type"] == "PT_INTERP")
        loads = [segment for segment in headers if segment["p_type"] == "PT_LOAD"]
        bss = elf.get_section_by_name(".bss")
        dynstr = elf.get_section_by_name(".dynstr")
        following = min(section["sh_offset"] for section in elf.iter_sections()
                        if section["sh_offset"] > dynstr["sh_offset"])
        relocations = {}
        for section in elf.iter_sections():
            if section["sh_type"] != "SHT_RELA":
                continue
            for relocation in section.iter_relocations():
                offset = relocation["r_offset"]
                for name, (expected_offset, expected_addend) in CACHE_RELOCATIONS.items():
                    if offset != expected_offset:
                        continue
                    assert name not in relocations
                    assert relocation["r_info_type"] == 1027  # R_AARCH64_RELATIVE
                    assert relocation["r_addend"] == expected_addend
                    relocations[name] = {
                        "target": hex(offset),
                        "stockAddend": hex(relocation["r_addend"]),
                        "type": "R_AARCH64_RELATIVE",
                    }
        assert set(relocations) == set(CACHE_RELOCATIONS)
        assert binary.read(GATE_VADDR, 4) == bytes(4)
        assert len(headers) == elf["e_phnum"] == 9
        assert not any(segment["p_type"] == "PT_NULL" for segment in headers)
        assert elf["e_phoff"] + elf["e_phentsize"] * elf["e_phnum"] == interp["p_offset"]
        assert phdr["p_offset"] == elf["e_phoff"]
        assert bss["sh_type"] == "SHT_NOBITS" and bss["sh_size"] > 0
        assert all((segment["p_flags"] & 3) != 3 for segment in loads)
        report = {
            "stockGuiSha256": GUI_SHA,
            "readOnly": True,
            "programHeaders": len(headers),
            "spareProgramHeader": False,
            "programHeaderGapBytes": interp["p_offset"] - (elf["e_phoff"] + elf["e_phentsize"] * elf["e_phnum"]),
            "dynstrFollowingGapBytes": following - (dynstr["sh_offset"] + dynstr["sh_size"]),
            "bssBytesReservedForStockProgram": bss["sh_size"],
            "cacheRelocations": relocations,
            "afcGateStockValue": "00000000",
            "verdict": "In-place expansion is unsafe: a new mapped segment and program-header relocation need separate loader validation; BSS is not free space.",
            "deviceValidated": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
