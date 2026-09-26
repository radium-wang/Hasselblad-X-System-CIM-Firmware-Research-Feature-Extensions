"""离线构建临时音频试听库。需要 ZIG、X2D_SYSTEM_IMAGE 及固件解析依赖。"""
from pathlib import Path
import os, sys, subprocess, io, hashlib, json
sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parents[1]/'tools'))
from firmware_image import system_file
from elftools.elf.elffile import ELFFile


def main():
    out = D/'outputs/device-package'
    out.mkdir(parents=True, exist_ok=True)
    libs, exports, dependencies = [], set(), []
    for name in ['libc.so', 'libaudioclient.so']:
        data=system_file('/lib64/'+name)
        path=out/name; path.write_bytes(data); libs.append(str(path))
        elf=ELFFile(io.BytesIO(data))
        exports.update(s.name for s in elf.get_section_by_name('.dynsym').iter_symbols() if s['st_shndx']!='SHN_UNDEF')
        dependencies.append(dict(name=name,sha256=hashlib.sha256(data).hexdigest()))
    target=out/'libx2d_audio_preview.so'
    subprocess.run([os.environ.get('ZIG','zig'),'cc','-target','aarch64-linux-gnu','-O2','-g0','-fPIC','-shared','-nostdlib','-fno-stack-protector','-Wl,--strip-all','-Wl,--no-undefined','-Wl,-z,noexecstack','-Wl,-soname,libx2d_audio_preview.so',str(D/'audio_preview.c'),*libs,'-o',str(target)],check=True)
    elf=ELFFile(io.BytesIO(target.read_bytes()))
    imports={s.name for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name and s['st_shndx']=='SHN_UNDEF'}
    assert imports<=exports, imports-exports
    assert elf['e_machine']=='EM_AARCH64'
    assert not any((s['p_flags']&3)==3 for s in elf.iter_segments())
    (out/'audio-build.json').write_text(json.dumps(dict(dependencies=dependencies,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),imports=sorted(imports)),indent=2)+'\n')
    print('PASS: audio imports, architecture, segment permissions; not a speaker test.')


if __name__=='__main__': main()
