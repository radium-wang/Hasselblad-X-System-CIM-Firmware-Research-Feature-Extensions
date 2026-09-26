#!/usr/bin/env python3
"""离线打包一次原厂模型容器校验；不连接相机，不执行原厂函数。"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from audit_native_bundle import needed, version_surface, check_versions
from audit_symbol_surface import dynamic_symbols

MODULE = Path(__file__).resolve().parents[1]
SOURCE = MODULE / 'CodeTests/native-loader-probe/model_container_probe.c'
REMOTE = '/blackbox/.codex-x2d-model-container-probe'
OWNER = 'codex-x2d-model-container-only-1'
MODEL_HASH = '6aff65ef7c658a6ebef11d17fa923eaf881ff78bd74042482d7b6945cbf852f0'
MODEL_SIZE = 4206912
DONOR_CA_HASH = '96e605e3940856eec88e6d17e698cebdedde0b5d26ccc2da7088ce2707d4d84b'
REVISION = 'original-model-container-v3'
MODELS = {
    'donor-pet': (MODEL_SIZE, MODEL_HASH, 'model/ml/yolov8-n-pet.json.eng.enc'),
    'stock-face': (746144, '8f0dfe58f8dc1b4d4107d9ad47beaedba1e3694198eaff09b3130662b14acaca',
                   'model/ml/faceEye.tflite.eng.enc'),
}
PINNED = {
    'bin/camera-gui': '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0',
    'lib64/libfw_util.so': 'd422ec46eeb66147e09771c7bde606e8cd17b615421353f8e3893a09a709435d',
    'lib64/libfw_util_ca.so': '91577855dd2f81ee901f0d4e7bbba1ccbc384f89df77d2cf2e403520de33a639',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_model(data, model='donor-pet'):
    if model not in MODELS:
        raise ValueError('unsupported model input')
    size, sha256, _ = MODELS[model]
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError('requires untouched pinned original model: ' + model)
    if data[:4] != b'IM*H' or struct.unpack_from('<I', data, 0x9c)[0] != 1:
        raise ValueError('unsupported original container header')


def stock_dependencies(root):
    remaining = ['libfw_util.so', 'ld-android.so']
    entries = {}
    while remaining:
        name = remaining.pop()
        if name in entries:
            continue
        path = root / 'lib64' / name
        entries[name] = {'name': name, 'sha256': digest(path)}
        remaining.extend(needed(path))
    return [entries[n] for n in sorted(entries)]


def audit_donor_ca(target, source):
    """只读检查唯一二代库、实际 GOT 槽、完整混合依赖；不加载 ELF。"""
    donor = source / 'lib64/libfw_util_ca.so'
    if digest(donor) != DONOR_CA_HASH:
        raise ValueError('requires untouched pinned donor CA library')
    with donor.open('rb') as stream:
        elf = ELFFile(stream)
        for tag in elf.get_section_by_name('.dynamic').iter_tags():
            if tag.entry.d_tag in ('DT_INIT', 'DT_INIT_ARRAY', 'DT_PREINIT_ARRAY') and tag.entry.d_val:
                raise ValueError('unexpected donor initializer')
        symbols = elf.get_section_by_name('.dynsym')
        if symbols.get_symbol_by_name('fw_util_verify_load2ion')[0]['st_value'] != 0x1700:
            raise ValueError('unexpected donor entry')
    with (target / 'lib64/libfw_util.so').open('rb') as stream:
        elf = ELFFile(stream)
        relocations = elf.get_section_by_name('.rela.plt')
        symbols = elf.get_section(relocations['sh_link'])
        slots = [r['r_offset'] for r in relocations.iter_relocations()
                 if symbols.get_symbol(r['r_info_sym']).name == 'fw_util_verify_load2ion'
                 and r['r_info_type'] == 1026]
        if slots != [0x1ffe0]:
            raise ValueError('unexpected stock verifier call slot')
    nodes, queue = {}, ['libfw_util.so']
    while queue:
        name = queue.pop()
        if name in nodes:
            continue
        path = donor if name == 'libfw_util_ca.so' else target / 'lib64' / name
        nodes[name] = path
        queue.extend(needed(path))
    surfaces = {n: version_surface(p) for n, p in nodes.items()}
    symbols = {n: dynamic_symbols(p) for n, p in nodes.items()}
    exports = set().union(*(s[1] for s in symbols.values()))
    if check_versions(surfaces) or any(s[0] - exports for s in symbols.values()):
        raise ValueError('mixed original library dependency gap')
    return {'donor_library': 'libfw_util_ca.so', 'sha256': DONOR_CA_HASH,
            'library_count': len(nodes), 'versioned_import_failures': [],
            'system_libraries_replaced': False, 'algorithm_executed': False}


def payload_files(loader):
    if loader not in ('stock', 'donor-ca'):
        raise ValueError('unsupported loader variant')
    result = {'probe', 'model.enc', 'owner', 'manifest.json', 'run.sh'}
    if loader == 'donor-ca':
        result.add('libfw_util_ca.so')
    return result


def device_script(loader='stock'):
    payload_files(loader)
    extra = ' "$base/libfw_util_ca.so"' if loader == 'donor-ca' else ''
    return f'''#!/system/bin/sh
set -u
base={REMOTE}
[ "$(cat "$base/owner" 2>/dev/null)" = {OWNER} ] || exit 50
cleanup() {{
  trap - EXIT HUP INT TERM
  rm -f "$base/probe" "$base/model.enc" "$base/manifest.json" "$base/SHA256SUMS" "$base/run.sh"{extra} || exit 72
  echo PAYLOAD_CLEANED >"$base/done"
}}
trap cleanup EXIT
trap 'exit 70' HUP INT TERM
cd "$base" || exit 51
sha256sum -c SHA256SUMS >verify.log 2>&1 || exit 52
chmod 0700 probe || exit 53
timeout -s KILL 12 env -u LD_PRELOAD -u LD_LIBRARY_PATH "$base/probe" >result 2>&1
rc=$?
echo "PROBE_EXIT=$rc" >>result
exit 0
'''


def validate_package(package, report):
    """独立上机入口再次绑定当前源码、脚本、固定模型与依赖证据。"""
    if report.get('probe_revision') != REVISION:
        raise ValueError('unknown model container probe revision')
    if report.get('source_sha256') != digest(SOURCE) or report.get('builder_sha256') != digest(Path(__file__)):
        raise ValueError('stale source or builder')
    loader = report.get('loader')
    if (package / 'run.sh').read_text() != device_script(loader):
        raise ValueError('device script differs from reviewed script')
    if report.get('inference_called') is not False or report.get('secure_verifier_called') is not True or \
            report.get('real_frames_used') is not False:
        raise ValueError('incorrect operation declaration')
    libraries = {e['name']: e['sha256'] for e in report['stock_base_libraries']}
    for name in ('libfw_util.so', 'libfw_util_ca.so'):
        if libraries.get(name) != PINNED['lib64/' + name]:
            raise ValueError('stock verification library mismatch')
    if loader == 'donor-ca' and digest(package / 'libfw_util_ca.so') != DONOR_CA_HASH:
        raise ValueError('donor CA library changed')
    model = report.get('input_model')
    validate_model((package / 'model.enc').read_bytes(), model)
    if report.get('model_sha256') != MODELS[model][1]:
        raise ValueError('model identity mismatch')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-system-root', type=Path, required=True)
    p.add_argument('--source-vendor-root', type=Path)
    p.add_argument('--target-vendor-root', type=Path)
    p.add_argument('--model', choices=tuple(MODELS), default='donor-pet')
    p.add_argument('--source-system-root', type=Path)
    p.add_argument('--loader', choices=('stock', 'donor-ca'), default='stock')
    p.add_argument('--ndk', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not a.output.is_dir() or any(a.output.iterdir()):
        p.error('output must exist and be empty')
    for relative, expected in PINNED.items():
        if digest(a.target_system_root / relative) != expected:
            p.error('wrong X2D 4.2.0 input: ' + relative)
    vendor = a.source_vendor_root if a.model == 'donor-pet' else a.target_vendor_root
    if vendor is None:
        p.error('selected model requires the corresponding vendor root')
    model = vendor / MODELS[a.model][2]
    validate_model(model.read_bytes(), a.model)
    donor_audit = None
    if a.loader == 'donor-ca':
        if not a.source_system_root:
            p.error('donor-ca requires --source-system-root')
        donor_audit = audit_donor_ca(a.target_system_root, a.source_system_root)
    compiler = a.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/clang'
    flags = ['-DUSE_DONOR_CA=1'] if a.loader == 'donor-ca' else []
    if a.model == 'stock-face':
        flags.append('-DUSE_STOCK_FACE_MODEL=1')
    subprocess.run([str(compiler), '--target=aarch64-linux-android28', '-std=c11', '-O2',
                    '-Wall', '-Wextra', '-Werror', '-fPIE', '-pie', '-fstack-protector-strong',
                    '-Wl,-z,defs', '-Wl,-z,relro,-z,now', str(SOURCE), '-ldl',
                    '-o', str(a.output / 'probe')] + flags, check=True)
    for symbol, provider, version in version_surface(a.output / 'probe')[0]:
        if (symbol, version) not in version_surface(a.target_system_root / 'lib64' / provider)[1]:
            p.error('unavailable target import: ' + symbol)
    shutil.copyfile(model, a.output / 'model.enc')
    if a.loader == 'donor-ca':
        shutil.copyfile(a.source_system_root / 'lib64/libfw_util_ca.so', a.output / 'libfw_util_ca.so')
    report = {'kind': 'model-container', 'probe_revision': REVISION,
              'loader': a.loader, 'donor_audit': donor_audit,
              'algorithm_called': False, 'af_called': False, 'inference_called': False,
              'secure_verifier_called': True, 'real_frames_used': False,
              'source_sha256': digest(SOURCE), 'builder_sha256': digest(Path(__file__)),
              'stock_base_libraries': stock_dependencies(a.target_system_root),
              'input_model': a.model, 'model_sha256': MODELS[a.model][1], 'timeout_seconds': 12,
              'purpose': 'original verify-to-memory only; no plaintext export or inference'}
    (a.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    (a.output / 'owner').write_text(OWNER + '\n')
    (a.output / 'run.sh').write_text(device_script(a.loader))
    subprocess.run(['/bin/sh', '-n', str(a.output / 'run.sh')], check=True)
    validate_package(a.output, report)
    (a.output / 'SHA256SUMS').write_text(''.join(
        digest(path) + '  ' + path.name + '\n' for path in sorted(a.output.iterdir())))
    print(json.dumps({'built': True, 'device_accessed': False, 'kind': report['kind']}))


if __name__ == '__main__':
    main()
