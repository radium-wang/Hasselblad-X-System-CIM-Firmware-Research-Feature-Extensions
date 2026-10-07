# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Add one passive Loader to the exact stock MainScreen, within its original slot."""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile

def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def strings(b):
    n,t=struct.unpack_from('<II',b,112)
    return [b[(o:=u32(b,t+i*4))+4:o+4+u32(b,o)*2].decode('utf-16le') for i in range(n)]

def build(original,url,loader_name='X2dDoomLoader'):
    assert len(original)==15084 and u32(original,244)==12056
    names=strings(original)
    fn_count,fn_table=struct.unpack_from('<II',original,120)
    debug_names={u32(original,u32(original,fn_table+i*4)+8) for i in range(fn_count)}
    removed=[i for i,s in enumerate(names) if s.startswith('expression for ')]
    assert set(removed)<=debug_names
    # Retain every runtime string index. Anonymous binding display names remain non-empty and unique, with shorter labels.
    names=[('@'+str(i) if i in removed else s) for i,s in enumerate(names)]
    def name(s):
        if s not in names:names.append(s)
        return names.index(s)
    loader_type=name('Loader');empty=name('');objname=name('objectName')
    source=name('source');label=name(loader_name);source_url=name(url)
    string_table=u32(original,116)
    blob=bytearray(original[:string_table])
    def append(raw):
        blob.extend(bytes(-len(blob)%8));at=len(blob);blob.extend(raw)
        blob.extend(bytes(-len(blob)%8));return at
    st=append(bytes(4*len(names)))
    for i,s in enumerate(names):
        raw=s.encode('utf-16le');at=append(struct.pack('<I',len(raw)//2)+raw+b'\0\0')
        struct.pack_into('<I',blob,st+4*i,at)
    old_qml=u32(original,244)
    n,table=struct.unpack_from('<II',original,old_qml+8)
    old_offsets=list(struct.unpack_from('<'+str(n)+'I',original,old_qml+table))
    qml=append(original[old_qml:old_qml+old_offsets[0]])
    offsets=[old_qml+o-qml for o in old_offsets]
    assert n==13
    root=bytearray(original[old_qml+old_offsets[0]:old_qml+old_offsets[1]])
    bc=struct.unpack_from('<H',root,46)[0];bt=u32(root,48)
    bindings=root[bt:bt+bc*24];assert bc==7 and len(root)==328
    new_bt=len(root);root.extend(bindings)
    root.extend(struct.pack('<6I',empty,8<<16,n,0,0,0))
    struct.pack_into('<H',root,46,bc+1);struct.pack_into('<I',root,48,new_bt)
    loader=bytearray(84)
    struct.pack_into('<4I',loader,0,loader_type,empty,0xffff0000,0xffffffff)
    struct.pack_into('<H',loader,46,2);struct.pack_into('<I',loader,48,84)
    loader.extend(struct.pack('<6I',objname,3<<16,0,label,0,0))
    loader.extend(struct.pack('<6I',source,3<<16,0,source_url,0,0))
    offsets[0]=append(root)-qml;offsets.append(append(loader)-qml)
    table=append(struct.pack('<'+str(len(offsets))+'I',*offsets))-qml
    struct.pack_into('<II',blob,qml+8,len(offsets),table)
    struct.pack_into('<II',blob,112,len(names),st)
    assert len(blob)<=old_qml,'Passive Loader must fit within reclaimed debug metadata'
    blob.extend(original[len(blob):])
    struct.pack_into('<I',blob,244,qml);struct.pack_into('<I',blob,24,len(blob))
    blob[76:92]=hashlib.md5(blob[92:]).digest()
    assert len(blob)==len(original),'Must never overwrite the adjacent stock unit'
    assert blob[120:236]==original[120:236]
    assert blob[248:string_table]==original[248:string_table],'Functions and lookup tables changed'
    assert strings(blob)[:len(strings(original))]==names[:len(strings(original))]
    assert [qml+o for o in offsets[1:n]]==[old_qml+o for o in old_offsets[1:]]
    assert blob[old_qml:]==original[old_qml:],'Stock object bytes and absolute positions changed'
    return bytes(blob)

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system',type=Path,required=True)
    p.add_argument('--url',required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--loader-name',default='X2dDoomLoader')
    a=p.parse_args()
    if not a.url.startswith('file:///'):p.error('An explicit local file URL is required')
    if a.out.resolve().is_relative_to(a.system.resolve()):p.error('Output must be separate from firmware')
    raw=(a.system/'bin/camera-gui').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0'
    elf=ELFFile(io.BytesIO(raw))
    symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name.endswith('32_app_qml_mainmenu_MainScreen_qml7qmlDataE'))
    sec=elf.get_section(symbol['st_shndx']);at=symbol['st_value']-sec['sh_addr']
    unit=build(sec.data()[at:at+symbol['st_size']],a.url,a.loader_name)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(unit)
    print(json.dumps(dict(bytes=len(unit),sha256=hashlib.sha256(unit).hexdigest(),deviceAccess=False)))
if __name__=='__main__':main()
