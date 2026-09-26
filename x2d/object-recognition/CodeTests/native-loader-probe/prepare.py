#!/usr/bin/env python3
"""生成无初始化入口的临时链接诊断副本；不接设备，不运行固件。"""
import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))
from adapt_original_tls import adapt

BASE = {'libc.so', 'libdl.so', 'ld-android.so'}
OWNER = 'codex-x2d-original-link-only-1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_initializers(data):
    elf = ELFFile(io.BytesIO(data))
    result = bytearray(data)
    changes = []
    for section in elf.iter_sections():
        if section['sh_type'] in ('SHT_DYNSYM', 'SHT_SYMTAB'):
            if any(s['st_info']['type'] in ('STT_GNU_IFUNC', 'STT_LOOS') for s in section.iter_symbols()):
                raise ValueError('IFUNC is not allowed in this link-only probe')
        if section['sh_type'] in ('SHT_RELA', 'SHT_REL'):
            if any(r['r_info_type'] == 1032 for r in section.iter_relocations()):
                raise ValueError('AArch64 IRELATIVE is not allowed')
    dynamic = elf.get_section_by_name('.dynamic')
    disabled = {'DT_INIT', 'DT_FINI', 'DT_INIT_ARRAYSZ', 'DT_FINI_ARRAYSZ', 'DT_PREINIT_ARRAYSZ'}
    for index, tag in enumerate(dynamic.iter_tags()):
        if tag.entry.d_tag in ('DT_RPATH', 'DT_RUNPATH'):
            raise ValueError('unexpected search path in private library')
        if tag.entry.d_tag in disabled:
            struct.pack_into('<Q', result, dynamic['sh_offset'] + index * 16 + 8, 0)
            changes.append(tag.entry.d_tag)
    after = ELFFile(io.BytesIO(result))
    for section in elf.iter_sections():
        if section['sh_flags'] & 4:
            assert after.get_section_by_name(section.name).data() == section.data()
    for tag in after.get_section_by_name('.dynamic').iter_tags():
        if tag.entry.d_tag in disabled:
            assert tag.entry.d_val == 0
    return bytes(result), changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-system-root', type=Path, required=True)
    p.add_argument('--target-system-root', type=Path, required=True)
    p.add_argument('--bundle-audit', type=Path, required=True)
    p.add_argument('--ndk', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not a.output.is_dir() or any(a.output.iterdir()): p.error('output must exist and be empty')
    manifest = json.loads(a.bundle_audit.read_text())
    entries = {v['name']: v for v in manifest['original_file_manifest']}
    if entries['libdsp_frwk.so']['origin'] != 'X2D-4.2.0': p.error('must retain first-generation DSP')
    queue = ['libnn_framework.so', 'libcnntk_cbb.so']; selected = set()
    while queue:
        name = queue.pop()
        if name in selected: continue
        if not re.fullmatch(r'[A-Za-z0-9_+.-]+\.so', name): p.error('invalid library name')
        selected.add(name); queue.extend(entries[name]['needed'])
    prepared = []
    for name in sorted(selected):
        item = entries[name]
        root = a.source_system_root if item['origin'].startswith('X2DII') else a.target_system_root
        path = root / 'lib64' / name
        original = path.read_bytes()
        if sha(original) != item['sha256']: p.error('input hash mismatch: ' + name)
        if name in BASE: continue
        data = adapt(original, name)[0] if name == 'libnn_framework.so' else original
        data, disabled = no_initializers(data)
        prepared.append((name, data, {'name': name, 'origin': item['origin'],
                          'original_sha256': sha(original), 'probe_sha256': sha(data),
                          'disabled_tags': disabled}))
    (a.output / 'lib').mkdir()
    for name, data, _ in prepared:
        (a.output / 'lib' / name).write_bytes(data)
    compiler = a.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/clang'
    subprocess.run([str(compiler), '--target=aarch64-linux-android28', '-O2', '-Wall', '-Wextra',
                    '-Werror', '-fPIE', '-pie', str(HERE / 'link_probe.c'), '-ldl',
                    '-o', str(a.output / 'probe')], check=True)
    report = {'purpose': 'link-only, all private constructors/destructors suppressed; never a functional candidate',
              'files': [r for _, _, r in prepared],
              'stock_base_libraries': [entries[n] for n in sorted(BASE)],
              'algorithm_called': False, 'af_called': False}
    (a.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    (a.output / 'owner').write_text(OWNER + '\n')
    remote = '/blackbox/.codex-x2d-native-linkprobe'
    cleanup = '\n'.join('rm -f ' + remote + '/lib/' + name for name, _, _ in prepared)
    runner = f'''#!/system/bin/sh
set -u
base={remote}
[ "$(cat "$base/owner" 2>/dev/null)" = {OWNER} ] || exit 50
cleanup() {{
  trap - EXIT HUP INT TERM
{cleanup}
  rmdir "$base/lib" 2>/dev/null || true
  rm -f "$base/probe" "$base/manifest.json" "$base/SHA256SUMS" "$base/run.sh"
  echo PAYLOAD_CLEANED >"$base/done"
}}
trap cleanup EXIT
trap 'exit 70' HUP INT TERM
cd "$base" || exit 51
sha256sum -c SHA256SUMS >verify.log 2>&1 || exit 52
chmod 0700 probe || exit 53
timeout 15 env LD_LIBRARY_PATH="$base/lib" "$base/probe" >result 2>&1
rc=$?
echo "PROBE_EXIT=$rc" >>result
exit 0
'''
    (a.output / 'run.sh').write_text(runner)
    subprocess.run(['/bin/sh', '-n', str(a.output / 'run.sh')], check=True)
    files = sorted(f for f in a.output.rglob('*') if f.is_file())
    (a.output / 'SHA256SUMS').write_text(''.join(sha(f.read_bytes()) + '  ' + f.relative_to(a.output).as_posix() + '\n' for f in files))
    print(json.dumps({'private_libraries': len(prepared), 'bytes': sum(len(d) for _, d, _ in prepared),
                      'constructor_calls_allowed': False, 'af_calls_allowed': False}))


if __name__ == '__main__':
    main()
