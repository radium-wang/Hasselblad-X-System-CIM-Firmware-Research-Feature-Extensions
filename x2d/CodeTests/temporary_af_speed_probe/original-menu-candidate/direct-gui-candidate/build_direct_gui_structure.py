"""Build an OFFLINE, NOT-FOR-DEVICE ELF-layout prototype.

This relocates the ELF program-header table and places prevalidated QML units
in a new read-only PT_LOAD segment. The optional AF-C experiment adds the
three-item popup and gate, but still does not create an install transaction.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
ROOT = D.parents[4]
sys.path.insert(0, str(D.parent))
sys.path.insert(0, str(ROOT / "x2d/CodeTests/temporary_af_speed_probe"))
from inspect_menu_resources import GUI_SHA, load_gui  # noqa: E402
from build_bootstrap_unit import build as build_bootstrap_unit  # noqa: E402

MAIN_CACHE_OFFSET = 0x20ACC78
MAIN_STOCK_ADDEND = 0x17B67F0
CLONE_SHA = "cc35325bead73358bdca313219e22d7b698b8cf7e9c8260015dc51ea77d207a5"
PROBE_BOOTSTRAP_URL = "file:///blackbox/.codex-x2d-direct-probe/X2dNativeMenuBootstrap.qml"
POPOVER_CACHE_OFFSET = 0x20AD2C0
POPOVER_STOCK_ADDEND = 0x1876EA0
POPOVER_SHA = "0958c3b8b3909228f2fec9e551f8a1fd7f867056810c47b982b1b21fbd830420"
GATE_OFFSET = 0x18A2A64
PAGE_SIZE = 0x10000
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")


def aligned(value, unit):
    return (value + unit - 1) & -unit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Explicit filename ending in .NOT_FOR_DEVICE")
    parser.add_argument("--afc-experiment", action="store_true",
                        help="Also embed three-item popup and turn on the AF-C capability gate")
    parser.add_argument("--blackbox-probe", action="store_true",
                        help="Use a /blackbox bootstrap URL for a non-overwriting runtime probe")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.name.endswith(".NOT_FOR_DEVICE"):
        parser.error("output name must end in .NOT_FOR_DEVICE")
    if output.exists():
        parser.error("refusing to overwrite an existing file")

    firmware = load_gui()
    stock = firmware.data
    if args.blackbox_probe:
        symbol = next(s for s in firmware.symbols if
                      s.name.endswith("32_app_qml_mainmenu_MainScreen_qml7qmlDataE"))
        original_unit = firmware.read(symbol["st_value"], symbol["st_size"])
        clone = build_bootstrap_unit(original_unit, PROBE_BOOTSTRAP_URL)
    else:
        clone = (D.parent / "main-screen-bootstrap-device.bin").read_bytes()
        assert hashlib.sha256(clone).hexdigest() == CLONE_SHA
        assert len(clone) == 16624
    assert clone[:8] == b"qv4cdata"
    assert clone[76:92] == hashlib.md5(clone[92:]).digest()
    blobs = [("MainScreen", clone, MAIN_CACHE_OFFSET, MAIN_STOCK_ADDEND)]
    if args.afc_experiment:
        popover = (D.parent / "native-package/popover-afc.bin").read_bytes()
        assert hashlib.sha256(popover).hexdigest() == POPOVER_SHA
        assert popover[76:92] == hashlib.md5(popover[92:]).digest()
        blobs.append(("PopoverFocusMode", popover,
                      POPOVER_CACHE_OFFSET, POPOVER_STOCK_ADDEND))

    with io.BytesIO(stock) as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_AARCH64" and elf["e_type"] == "ET_DYN"
        headers = list(elf.iter_segments())
        assert len(headers) == elf["e_phnum"] == 9
        assert elf["e_phentsize"] == PROGRAM_HEADER.size
        assert headers[0]["p_type"] == "PT_PHDR"
        assert headers[1]["p_type"] == "PT_INTERP"
        assert elf["e_phoff"] + 9 * PROGRAM_HEADER.size == headers[1]["p_offset"]
        assert all(header["p_type"] != "PT_NULL" for header in headers)
        loads = [header for header in headers if header["p_type"] == "PT_LOAD"]
        assert len(loads) == 2
        new_file = aligned(len(stock), PAGE_SIZE)
        new_virtual = aligned(max(h["p_vaddr"] + h["p_memsz"] for h in loads), PAGE_SIZE)
        count = len(headers) + 1
        table_size = count * PROGRAM_HEADER.size
        positions = {}
        segment_payload = bytearray()
        for name, data, _, _ in blobs:
            position = aligned(table_size + len(segment_payload), 8)
            segment_payload.extend(bytes(position - table_size - len(segment_payload)))
            positions[name] = (position, new_virtual + position)
            segment_payload.extend(data)
        segment_size = table_size + len(segment_payload)

        # Preserve the old file entirely except e_phoff/e_phnum, exact
        # RELATIVE addends, and the optional four-byte AF-C gate.
        patched = bytearray(stock)
        struct.pack_into("<Q", patched, 32, new_file)
        struct.pack_into("<H", patched, 56, count)
        rela = elf.get_section_by_name(".rela.dyn")
        assert rela is not None and rela["sh_entsize"] == 24
        by_target = {}
        target_offsets = {target for _, _, target, _ in blobs}
        for index, relocation in enumerate(rela.iter_relocations()):
            if relocation["r_offset"] in target_offsets:
                assert relocation["r_offset"] not in by_target
                by_target[relocation["r_offset"]] = (index, relocation)
        changed = [(32, 40), (56, 58)]
        for name, _, target, stock_addend in blobs:
            index, relocation = by_target[target]
            assert relocation["r_info_type"] == 1027
            assert relocation["r_addend"] == stock_addend
            addend_file_offset = rela["sh_offset"] + index * rela["sh_entsize"] + 16
            struct.pack_into("<q", patched, addend_file_offset, positions[name][1])
            changed.append((addend_file_offset, addend_file_offset + 8))
        assert stock[GATE_OFFSET:GATE_OFFSET + 4] == bytes(4)
        if args.afc_experiment:
            assert loads[0]["p_offset"] == loads[0]["p_vaddr"] == 0
            assert GATE_OFFSET + 4 < loads[0]["p_filesz"]
            struct.pack_into("<I", patched, GATE_OFFSET, 1)
            changed.append((GATE_OFFSET, GATE_OFFSET + 4))
        cursor = 0
        for begin, end in sorted(changed):
            assert patched[cursor:begin] == stock[cursor:begin]
            cursor = end
        assert patched[cursor:len(stock)] == stock[cursor:]

        # ELF64 AArch64 Program Header: type, flags, file offset, virtual,
        # physical, file bytes, memory bytes, alignment.
        new_table = bytearray(stock[elf["e_phoff"]:elf["e_phoff"] + 9 * PROGRAM_HEADER.size])
        PROGRAM_HEADER.pack_into(new_table, 0, 6, 4, new_file, new_virtual,
                                 new_virtual, table_size, table_size, 8)
        new_table.extend(PROGRAM_HEADER.pack(1, 4, new_file, new_virtual,
                                             new_virtual, segment_size, segment_size,
                                             PAGE_SIZE))
        assert len(new_table) == table_size
        patched.extend(bytes(new_file - len(patched)))
        patched.extend(new_table)
        patched.extend(segment_payload)

    # Parse the result independently. Structural acceptance is deliberately
    # narrower than target-loader or GUI acceptance.
    with io.BytesIO(patched) as stream:
        verified = ELFFile(stream)
        segments = list(verified.iter_segments())
        assert len(segments) == count
        assert segments[0]["p_type"] == "PT_PHDR"
        assert segments[0]["p_offset"] == new_file
        assert segments[-1]["p_type"] == "PT_LOAD"
        assert segments[-1]["p_flags"] == 4
        assert segments[-1]["p_offset"] == new_file
        assert segments[-1]["p_vaddr"] == new_virtual
        assert segments[-1]["p_filesz"] == segment_size
        assert new_file % PAGE_SIZE == new_virtual % PAGE_SIZE
        for name, data, _, _ in blobs:
            position, _ = positions[name]
            assert patched[new_file + position:new_file + position + len(data)] == data
        rela = verified.get_section_by_name(".rela.dyn")
        found = {r["r_offset"]: r["r_addend"] for r in rela.iter_relocations()
                 if r["r_offset"] in target_offsets}
        assert found == {target: positions[name][1] for name, _, target, _ in blobs}
        assert len(stock) < new_file and len(patched) == new_file + segment_size
        assert patched[GATE_OFFSET:GATE_OFFSET + 4] == (
            bytes.fromhex("01000000") if args.afc_experiment else bytes(4))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patched)
    print(json.dumps({
        "sourceSha256": GUI_SHA,
        "output": str(output),
        "outputSha256": hashlib.sha256(patched).hexdigest(),
        "newReadonlySegmentVirtual": hex(new_virtual),
        "newQmlUnitVirtuals": {name: hex(address) for name, (_, address) in positions.items()},
        "afcGateChanged": args.afc_experiment,
        "sidecarsPackaged": False,
        "bootstrapUrl": PROBE_BOOTSTRAP_URL if args.blackbox_probe else
                        "file:///system/etc/X2dNativeMenuBootstrap.qml",
        "runtimeFeatureControllerImplemented": False,
        "targetLoaderTested": False,
        "deviceValidated": False,
        "installable": False,
    }, indent=2))


if __name__ == "__main__":
    main()
