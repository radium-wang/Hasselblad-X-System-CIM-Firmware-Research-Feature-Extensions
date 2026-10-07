#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Offline stock-ABI audio bridge build; explicit firmware and Zig, no device calls."""
import argparse, hashlib, io, json, os, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1] / "native"
AUDIO_SHA='1a196a3f3c9095042999c429aaf38bcfa2e800f12d4121a6f465cbc4ca18000c'
LIBC_SHA='40e9ea6efccfe8757b4afac57972c9a5cce745224d2dcf34ecddf3dfc0a3f7a6'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--system',type=Path,required=True);p.add_argument('--zig',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.system=a.system.resolve();a.out=a.out.resolve();assert not a.out.is_relative_to(a.system)
 exports=set();libs=[];dependencies=[]
 for n in ['libc.so','libaudioclient.so']:
  lib=a.system/'lib64'/n;raw=lib.read_bytes();elf=ELFFile(io.BytesIO(raw));assert elf['e_machine']=='EM_AARCH64'
  assert sha(raw)==(AUDIO_SHA if n=='libaudioclient.so' else LIBC_SHA), 'Unsupported stock library: '+n
  exports.update(s.name for s in elf.get_section_by_name('.dynsym').iter_symbols() if s['st_shndx']!='SHN_UNDEF')
  libs.append(str(lib));dependencies.append(dict(name=n,sha256=sha(raw)))
 a.out.mkdir(parents=True,exist_ok=True);target=a.out/'libdoom_audio.so'
 env=dict(os.environ,ZIG_LOCAL_CACHE_DIR=str(a.out/'zig-local'),ZIG_GLOBAL_CACHE_DIR=str(a.out/'zig-global'))
 cmd=[str(a.zig),'cc','-target','aarch64-linux-gnu','-mcpu=cortex_a53','-O2','-g0','-fPIC','-shared','-nostdlib','-fno-stack-protector','-Wl,--strip-all','-Wl,--no-undefined','-Wl,-z,noexecstack','-Wl,-soname,libdoom_audio.so',str(ROOT/'audio_bridge.c'),*libs,'-o',str(target)]
 with (a.out/'audio-build.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 raw=target.read_bytes();elf=ELFFile(io.BytesIO(raw));imports={s.name for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name and s['st_shndx']=='SHN_UNDEF'}
 assert imports<=exports,imports-exports
 assert elf['e_machine']=='EM_AARCH64' and elf['e_type']=='ET_DYN'
 assert not any((s['p_flags']&3)==3 for s in elf.iter_segments())
 result=dict(sha256=sha(raw),bytes=len(raw),dependencies=dependencies,imports=sorted(imports),sourceSha256=sha((ROOT/'audio_bridge.c').read_bytes()),ringHeaderSha256=sha((ROOT/'audio_ring.h').read_bytes()),deviceValidated=False)
 (a.out/'audio-build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
