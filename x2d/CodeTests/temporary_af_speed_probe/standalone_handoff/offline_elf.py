"""Standalone, read-only ELF inspection. No device access or repository imports."""
import argparse
import hashlib
import io
import lzma
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

HASHES = {
    'libaaa.so': 'feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7',
    'librcam.so': '72ebc8deebce4a29047c475e77ab4edbf2860abb1f572fea45260fe17ad0bda5',
}

class Binary:
    def __init__(self, path, expected):
        self.data = Path(path).read_bytes()
        if hashlib.sha256(self.data).hexdigest() != expected:
            raise ValueError('Firmware hash mismatch')
        self.elf = ELFFile(io.BytesIO(self.data))
        if self.elf['e_machine'] != 'EM_AARCH64':
            raise ValueError('Expected AArch64')
        debugelf = self.elf
        if not debugelf.get_section_by_name('.symtab'):
            debug = self.elf.get_section_by_name('.gnu_debugdata')
            if debug:
                debugelf = ELFFile(io.BytesIO(lzma.decompress(debug.data())))
        sym = debugelf.get_section_by_name('.symtab')
        self.symbols = list(sym.iter_symbols()) if sym else []
        dyn = self.elf.get_section_by_name('.dynsym')
        if dyn:
            self.symbols.extend(dyn.iter_symbols())
        self.names = {s['st_value']: s.name for s in self.symbols if s['st_value']}
        rel = self.elf.get_section_by_name('.rela.plt')
        plt = self.elf.get_section_by_name('.plt')
        if rel and plt:
            dyn = self.elf.get_section(rel['sh_link'])
            for i, r in enumerate(rel.iter_relocations()):
                self.names[plt['sh_addr'] + 32 + i * 16] = dyn.get_symbol(r['r_info_sym']).name + '@plt'
        self.cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        self.cs.detail = True

    def read(self, address, size):
        for seg in self.elf.iter_segments():
            if seg['p_type'] != 'PT_LOAD':
                continue
            start = seg['p_vaddr']
            if start <= address and address + size <= start + seg['p_filesz']:
                offset = seg['p_offset'] + address - start
                return self.data[offset:offset + size]
        raise ValueError('Requested range is not fully file-backed')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('elf')
    p.add_argument('--kind', choices=HASHES, default='libaaa.so')
    p.add_argument('--symbol', default='_exec_pdaf_afs_process')
    args = p.parse_args()
    b = Binary(args.elf, HASHES[args.kind])
    matches = {(s['st_value'], s['st_size']) for s in b.symbols if s.name == args.symbol and s['st_value'] and s['st_size']}
    if len(matches) != 1:
        raise ValueError('Expected exactly one defined function with size')
    start, size = matches.pop()
    print(f'{args.symbol} ELF VA={start:#x}, bytes={size}')
    for ins in b.cs.disasm(b.read(start, size), start):
        name = ''
        if ins.mnemonic in ('bl', 'b') and ins.op_str.startswith('#'):
            name = b.names.get(ins.operands[0].imm, '')
        print(f'{ins.address:08x}: {ins.mnemonic:8} {ins.op_str:36} {name}')

if __name__ == '__main__':
    main()
