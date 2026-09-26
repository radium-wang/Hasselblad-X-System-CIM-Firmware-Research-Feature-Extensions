#!/usr/bin/env python3
"""离线构建独立帧描述符合成自检包；不会接相机或运行 ARM 程序。"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from audit_native_bundle import version_surface

MODULE = Path(__file__).resolve().parents[1]
REMOTE = '/blackbox/.codex-x2d-frame-descriptor-probe'
OWNER = 'codex-x2d-frame-descriptor-only-1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-system-root', type=Path, required=True)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_dir() or any(args.output.iterdir()):
        parser.error('output must exist and be empty')
    gui = args.target_system_root / 'bin/camera-gui'
    if hashlib.sha256(gui.read_bytes()).hexdigest() != '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0':
        parser.error('not the pinned X2D 4.2.0 system input')
    compiler = args.ndk / 'toolchains/llvm/prebuilt/darwin-x86_64/bin/clang'
    flags = [str(compiler), '--target=aarch64-linux-android28', '-std=c11', '-O2',
             '-Wall', '-Wextra', '-Werror', '-Wl,-z,defs', '-Wl,-z,relro,-z,now']
    subprocess.run(flags + ['-fPIC', '-shared', str(MODULE / 'native/frame_descriptor_adapter.c'),
                           '-o', str(args.output / 'libx2d_frame_adapter.so')], check=True)
    subprocess.run(flags + ['-fPIE', '-pie', str(MODULE / 'CodeTests/offline-contract/frame_adapter_device_probe.c'),
                           '-L' + str(args.output), '-lx2d_frame_adapter',
                           '-o', str(args.output / 'probe')], check=True)
    base = []
    for name in ('libc.so', 'libdl.so', 'ld-android.so'):
        path = args.target_system_root / 'lib64' / name
        base.append({'name': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for filename in ('probe', 'libx2d_frame_adapter.so'):
        for symbol, provider, version in version_surface(args.output / filename)[0]:
            exports = version_surface(args.target_system_root / 'lib64' / provider)[1]
            if (symbol, version) not in exports:
                parser.error('target runtime import unavailable: ' + symbol)
    report = {'kind': 'frame-descriptor', 'algorithm_called': False, 'af_called': False,
              'real_frames_used': False, 'stock_base_libraries': base,
              'purpose': 'synthetic descriptor checks only; no original firmware execution',
              'timeout_seconds': 10}
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'owner').write_text(OWNER + '\n')
    script = f'''#!/system/bin/sh
set -u
base={REMOTE}
[ "$(cat "$base/owner" 2>/dev/null)" = {OWNER} ] || exit 50
cleanup() {{
  trap - EXIT HUP INT TERM
  rm -f "$base/probe" "$base/libx2d_frame_adapter.so" "$base/manifest.json" "$base/SHA256SUMS" "$base/run.sh"
  echo PAYLOAD_CLEANED >"$base/done"
}}
trap cleanup EXIT
trap 'exit 70' HUP INT TERM
cd "$base" || exit 51
sha256sum -c SHA256SUMS >verify.log 2>&1 || exit 52
chmod 0700 probe || exit 53
timeout 10 env LD_LIBRARY_PATH="$base" "$base/probe" >result 2>&1
rc=$?
echo "PROBE_EXIT=$rc" >>result
exit 0
'''
    (args.output / 'run.sh').write_text(script)
    subprocess.run(['/bin/sh', '-n', str(args.output / 'run.sh')], check=True)
    files = sorted(args.output.iterdir())
    (args.output / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in files))
    print(json.dumps({'built': True, 'device_accessed': False, 'kind': 'frame-descriptor'}))


if __name__ == '__main__':
    main()
