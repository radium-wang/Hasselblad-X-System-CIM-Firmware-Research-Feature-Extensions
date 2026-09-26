#!/usr/bin/env python3
"""离线 ELF 元数据实验：保留一代 DSP，将 TLS 导入绑定至二代原厂 FastRTPS。

只生成新副本，不运行固件、不接设备。静态成功不证明 TLS 或硬件 ABI 可用。
依赖 pyelftools；仅接受固定 SHA-256 的二代 1.3.16.2 文件。
"""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from audit_native_bundle import audit, check_versions, needed, version_surface

PINS = {
    'dji_ml': '98351d0906f3056cf780c5bf2adce65f544bb258c18dd62cfadb01607bdb1788',
    'libnn_framework.so': '97915622e7b985f3940fd5ff1f910308519d2ae4bfb43a34659c1a9342c88a4e',
}
SYMBOL = '__emutls_get_address'
PROVIDER = 'libduml_fastrtps.so'
VERSION = 'libduml_fastrtps_v_lz'
PROVIDER_SHA256 = 'd474ccfc8d0ba6b1f9b95021b6ec35ab655ace935e53029e428adb0663d100f2'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def align(value, boundary):
    return (value + boundary - 1) & -boundary


def elf_hash(name):
    result = 0
    for byte in name.encode():
        result = (result << 4) + byte
        high = result & 0xf0000000
        if high:
            result ^= high >> 24
        result &= ~high
    return result


def adapt(data, name):
    if name not in PINS or digest(data) != PINS[name]:
        raise ValueError('unrecognized original input; no adaptation allowed')
    elf = ELFFile(io.BytesIO(data))
    if elf.elfclass != 64 or not elf.little_endian or elf['e_machine'] != 'EM_AARCH64':
        raise ValueError('expected little-endian ARM64 ELF')
    result = bytearray(data)
    versions = elf.get_section_by_name('.gnu.version')
    needs = elf.get_section_by_name('.gnu.version_r')
    dynstr = elf.get_section_by_name('.dynstr')
    dynamic = elf.get_section_by_name('.dynamic')
    imports = []
    for index, symbol in enumerate(elf.get_section_by_name('.dynsym').iter_symbols()):
        if symbol.name == SYMBOL and symbol['st_shndx'] == 'SHN_UNDEF':
            imports.append(index)
    if len(imports) != 1:
        raise ValueError('expected exactly one TLS import')
    target_index = None
    old_index = None
    maximum = 1
    for dependency, auxiliaries in needs.iter_versions():
        for version in auxiliaries:
            index = version['vna_other'] & 0x7fff
            maximum = max(maximum, index)
            if dependency.name == PROVIDER and version.name == VERSION:
                target_index = index
            if dependency.name == 'libdsp_frwk.so' and version.name == 'libdsp_frwk_v_lz':
                old_index = index
    slot = versions['sh_offset'] + 2 * imports[0]
    if old_index is None or struct.unpack_from('<H', data, slot)[0] != old_index:
        raise ValueError('unexpected original TLS version binding')
    added_load = False
    if target_index is None:
        # Fixed libnn image: keep both original LOAD segments and all code/data.
        # Reuse its second PT_NOTE header for a new read-only metadata LOAD.
        # The note bytes and section remain intact; no constructor is executed.
        if name != 'libnn_framework.so':
            raise ValueError('unapproved metadata expansion')
        segments = list(elf.iter_segments())
        notes = [i for i, segment in enumerate(segments) if segment['p_type'] == 'PT_NOTE']
        loads = [s for s in segments if s['p_type'] == 'PT_LOAD']
        if len(notes) != 2 or len(loads) != 2:
            raise ValueError('unexpected program headers')
        target_index = maximum + 1
        strings = dynstr.data()
        provider_offset = strings.find(PROVIDER.encode() + b'\0')
        if provider_offset < 0:
            raise ValueError('provider must already be DT_NEEDED')
        version_offset = len(strings)
        strings += VERSION.encode() + b'\0'
        new_needs = bytearray(needs.data())
        cursor = 0
        while True:
            following = struct.unpack_from('<I', new_needs, cursor + 12)[0]
            if not following:
                break
            cursor += following
        struct.pack_into('<I', new_needs, cursor + 12, len(new_needs) - cursor)
        new_needs += struct.pack('<HHIII', 1, 1, provider_offset, 16, 0)
        new_needs += struct.pack('<IHHII', elf_hash(VERSION), 0, target_index, version_offset, 0)
        needs_offset = align(len(strings), 8)
        payload = strings + b'\0' * (needs_offset - len(strings)) + new_needs
        file_offset = align(len(result), 0x10000)
        address = align(max(s['p_vaddr'] + s['p_memsz'] for s in loads), 0x10000)
        result.extend(b'\0' * (file_offset - len(result)))
        result.extend(payload)
        header = elf['e_phoff'] + notes[-1] * elf['e_phentsize']
        struct.pack_into('<IIQQQQQQ', result, header, 1, 4, file_offset, address,
                         address, len(payload), len(payload), 0x10000)
        replacement = {'DT_STRTAB': address, 'DT_STRSZ': len(strings),
                       'DT_VERNEED': address + needs_offset,
                       'DT_VERNEEDNUM': needs.num_versions() + 1}
        found = set()
        for index, tag in enumerate(dynamic.iter_tags()):
            if tag.entry.d_tag in replacement:
                struct.pack_into('<Q', result, dynamic['sh_offset'] + index * 16 + 8,
                                 replacement[tag.entry.d_tag])
                found.add(tag.entry.d_tag)
        if found != set(replacement):
            raise ValueError('missing dynamic metadata entry')
        for index, section in enumerate(elf.iter_sections()):
            if section.name in ('.dynstr', '.gnu.version_r'):
                is_strings = section.name == '.dynstr'
                offset = 0 if is_strings else needs_offset
                size = len(strings) if is_strings else len(new_needs)
                sh = elf['e_shoff'] + index * elf['e_shentsize']
                struct.pack_into('<QQQ', result, sh + 16, address + offset, file_offset + offset, size)
                if not is_strings:
                    struct.pack_into('<I', result, sh + 44, needs.num_versions() + 1)
        added_load = True
    struct.pack_into('<H', result, slot, target_index)
    updated = ELFFile(io.BytesIO(result))
    preserved = []
    for section in elf.iter_sections():
        # Every allocated section except the three explicit metadata sections
        # must remain byte-for-byte identical, not just the algorithm .text.
        if section['sh_flags'] & 2 and section['sh_type'] != 'SHT_NOBITS' and section.name not in (
                '.dynstr', '.gnu.version_r', '.gnu.version', '.dynamic'):
            after = updated.get_section_by_name(section.name)
            if after is None or after.data() != section.data():
                raise ValueError('unexpected modification to ' + section.name)
            if section['sh_flags'] & 4:
                preserved.append({'section': section.name, 'sha256': digest(section.data())})
    return bytes(result), {'input_sha256': digest(data), 'output_sha256': digest(result),
                           'symbol': SYMBOL, 'provider': PROVIDER, 'version': VERSION,
                           'old_version_index': old_index, 'new_version_index': target_index,
                           'added_read_only_load': added_load,
                           'preserved_executable_sections': preserved,
                           'device_execution_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-system-root', required=True, type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--target-system-root', type=Path,
                        help='optional offline mixed-bundle version audit; never loads firmware')
    args = parser.parse_args()
    if not args.output_directory.is_dir() or any(args.output_directory.iterdir()):
        parser.error('output directory must exist and be empty; no files will be overwritten')
    provider = args.source_system_root / 'lib64' / PROVIDER
    if digest(provider.read_bytes()) != PROVIDER_SHA256 or (SYMBOL, VERSION) not in version_surface(provider)[1]:
        parser.error('original TLS provider fingerprint/export mismatch')
    prepared = []
    for name, relative in (('dji_ml', 'bin/dji_ml'), ('libnn_framework.so', 'lib64/libnn_framework.so')):
        source = args.source_system_root / relative
        original = source.read_bytes()
        patched, report = adapt(original, name)
        prepared.append((name, source, patched, report))
    reports = {}
    for name, source, patched, report in prepared:
        destination = args.output_directory / name
        with destination.open('xb') as output:
            output.write(patched)
        old_imports, old_exports = version_surface(source)
        new_imports, new_exports = version_surface(destination)
        expected = [(symbol, PROVIDER, VERSION) if symbol == SYMBOL else (symbol, provider, version)
                    for symbol, provider, version in old_imports]
        if new_imports != expected or new_exports != old_exports or needed(source) != needed(destination):
            raise RuntimeError('post-write contract mismatch; do not use generated files')
        report['version_surface_verified'] = True
        report['source_unchanged'] = digest(source.read_bytes()) == report['input_sha256']
        reports[name] = report
    if args.target_system_root:
        bundle = audit(args.source_system_root, args.target_system_root)
        surfaces = {}
        for item in bundle['original_file_manifest']:
            name = item['name']
            if name in reports:
                path = args.output_directory / name
            else:
                root = args.source_system_root if item['origin'].startswith('X2DII') else args.target_system_root
                path = root / item['path']
            surfaces[name] = version_surface(path)
        reports['mixed_bundle_static_check'] = {
            'retained_target_dsp': 'libdsp_frwk.so' in bundle['retained_target_libraries'],
            'unversioned_symbol_closure': bundle['unversioned_symbol_closure'],
            'versioned_import_count': sum(len(v[0]) for v in surfaces.values()),
            'versioned_import_failures': check_versions(surfaces),
            'provider_sha256': PROVIDER_SHA256,
            'device_execution_approved': False,
        }
    manifest = args.output_directory / 'adaptation.json'
    with manifest.open('x') as output:
        json.dump(reports, output, indent=2)
        output.write('\n')
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
