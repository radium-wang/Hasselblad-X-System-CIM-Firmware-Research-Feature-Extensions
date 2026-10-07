#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Offline build; explicit upstream and compiler paths, no downloads/device calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1] / "native"
PIN = 'dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--arm64', action='store_true')
    p.add_argument('--zig', type=Path)
    a = p.parse_args()
    a.upstream = a.upstream.resolve()
    a.out = a.out.resolve()
    commit = subprocess.check_output(['git', '-C', str(a.upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != PIN:
        p.error('Unsupported upstream revision')
    if subprocess.check_output(['git', '-C', str(a.upstream), 'status', '--porcelain'], text=True).strip():
        p.error('Upstream must be unmodified')
    src = a.upstream / 'doomgeneric'
    if a.out.resolve().is_relative_to(a.upstream.resolve()):
        p.error('Output must be separate from upstream')
    a.out.mkdir(parents=True, exist_ok=True)
    # This revision includes SDL_mixer.h under FEATURE_SOUND but uses no SDL types
    # or functions in i_sound.c. Our module has its own mixer and stock client bridge.
    headers = a.out / 'sound-headers'
    headers.mkdir(exist_ok=True)
    (headers / 'SDL_mixer.h').write_text('/* Unused upstream include; no SDL ABI declarations. */\n')
    makefile = (src / 'Makefile').read_text()
    objects = re.search(r'^SRC_DOOM = (.+)$', makefile, re.M).group(1).split()
    sources = [src / (n[:-2] + '.c') for n in objects if n != 'doomgeneric_xlib.o']
    sources.append(ROOT / 'doomgeneric_x2d_file.c')
    sources.append(ROOT / 'doom_sound.c')
    compiler = [str(a.zig), 'cc', '-target', 'aarch64-linux-musl', '-static'] if a.arm64 else ['clang']
    if a.arm64 and not a.zig:
        p.error('--arm64 requires --zig')
    output = a.out / ('doom-x2d-arm64' if a.arm64 else 'doom-host')
    flags = ['-O2', '-DNORMALUNIX', '-DLINUX', '-DSNDSERV', '-D_DEFAULT_SOURCE', '-DFEATURE_SOUND',
             '-DDOOMGENERIC_RESX=320', '-DDOOMGENERIC_RESY=200', '-Wno-unused-result',
             '-I' + str(src), '-I' + str(headers), *map(str, sources), '-lm', '-o', str(output)]
    env = dict(os.environ, ZIG_LOCAL_CACHE_DIR=str(a.out / 'zig-local'),
               ZIG_GLOBAL_CACHE_DIR=str(a.out / 'zig-global'))
    with (a.out / (output.name + '.build.log')).open('w') as log:
        subprocess.run(compiler + flags, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = {'upstreamCommit': commit, 'binary': output.name, 'bytes': output.stat().st_size,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'sourceFiles': len(sources),
              'backendSha256': hashlib.sha256((ROOT / 'doomgeneric_x2d_file.c').read_bytes()).hexdigest(),
              'soundSourceSha256': hashlib.sha256((ROOT / 'doom_sound.c').read_bytes()).hexdigest(),
              'ringHeaderSha256': hashlib.sha256((ROOT / 'audio_ring.h').read_bytes()).hexdigest(),
              'resolution': [320, 200], 'sound': 'DMX effects, shared RAM', 'music': False, 'deviceValidated': False}
    if a.arm64:
        from elftools.elf.elffile import ELFFile
        with output.open('rb') as handle:
            e = ELFFile(handle)
            assert e['e_machine'] == 'EM_AARCH64'
            assert not any(s['p_type'] in ('PT_INTERP', 'PT_DYNAMIC') for s in e.iter_segments())
            assert not any((s['p_flags'] & 3) == 3 for s in e.iter_segments())
            result.update(elf='AArch64', static=True, interpreter=None, writableExecutableSegments=False)
    (a.out / (output.name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
