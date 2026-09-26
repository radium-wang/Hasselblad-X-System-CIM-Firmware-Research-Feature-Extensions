"""X2D II 1.3.16.2 离线解包与地区线索索引；不连接设备。"""
import ast
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.research-cache' / 'x2d2'
OUT = ROOT / 'x2d2' / 'research' / '1.3.16.2'
sys.path.insert(0, str(ROOT / '.research-cache' / 'python'))
from Crypto.Cipher import AES
import brotli
from dissect.extfs import ExtFS

data = (CACHE / 'X2DII_100C_v1_3_16_2.cim').read_bytes()
assert len(data) == 364814336
source = (ROOT / '.research-cache' / 'reference-source.txt').read_bytes()
assert hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest() == '35469a59ee6357de7bfe90dbbafe03d248e3b7e9'
constants = {}
for n in ast.walk(ast.parse(source)):
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id in {'STATIC_KEY', 'IV_SALT', 'MAGIC_HASH_SALT'}:
        constants[n.targets[0].id] = bytes(ast.literal_eval(n.value.args[0]))
header = data[:128].split(b'\x1a')[0].decode('ascii')
assert header.startswith('VHABCIM\r\n')
y, m, d = map(int, re.search(r'(\d{4})-(\d{2})-(\d{2})', header).groups())
stamp = bytes([y // 100, y % 100, m, d, *map(int, re.search(r'(\d{2}):(\d{2}):(\d{2})', header).groups())]) + bytes(9)
iv = hashlib.md5(constants['IV_SALT'] + stamp).digest()
def decrypt(off, size):
    assert off >= 128 and size > 0 and off + (size + 15) // 16 * 16 <= len(data)
    out = bytearray()
    for p in range(0, size, 4096):
        n = min(4096, size-p)
        out.extend(AES.new(constants['STATIC_KEY'], AES.MODE_CBC, iv).decrypt(data[off+p:off+p+(n+15)//16*16])[:n])
    return out

table = decrypt(128, 8192)
names = {'ota.zip', 'hbl-upgrade', 'hbl-post-upgrade', 'exMCU_hb722.cont', 'exMCUloader.cont', 'hb722_charger.cont'}
entries = []
for match in re.finditer(rb'\x00{16,}(?P<name>[\x20-\x7e]{3,})\x00', table):
    name = match.group('name').decode()
    if name not in names or match.start() < 24:
        continue
    off, size, check = struct.unpack_from('>II16s', table, match.start()-24)
    content = decrypt(off, size)
    assert hashlib.md5(content + constants['MAGIC_HASH_SALT']).digest() == check
    entries.append(dict(name=name, offset=off, size=size, checksumVerified=True, sha256=hashlib.sha256(content).hexdigest()))
    if name == 'ota.zip':
        (CACHE / name).write_bytes(content)
assert {e['name'] for e in entries} == names and len(entries) == 6
manifest = dict(model='X2D II 100C', firmware='1.3.16.2', source='official-firmware-static', size=len(data), sha256=hashlib.sha256(data).hexdigest(), entries=entries)
del data, content
print('六个容器条目校验通过', flush=True)
selected = CACHE / 'selected'
selected.mkdir(exist_ok=True)
results = []
with zipfile.ZipFile(CACHE / 'ota.zip') as ota:
    for part in ('system', 'vendor'):
        lines = ota.read(part+'.transfer.list').decode().splitlines()
        assert lines[0] == '4' and lines[2:4] == ['0','0']
        commands = []
        for line in lines[4:]:
            command, text = line.split()
            assert command in ('new','zero','erase')
            nums = list(map(int, text.split(',')))
            assert nums[0] == len(nums)-1 and nums[0] % 2 == 0
            pairs = list(zip(nums[1::2], nums[2::2]))
            assert all(0 <= a < b <= 262144 for a,b in pairs)
            commands.append((command,pairs))
        payload = brotli.decompress(ota.read(part+'.new.dat.br'))
        assert len(payload) == sum((b-a)*4096 for c,rs in commands if c=='new' for a,b in rs)
        path = CACHE / (part+'.img')
        with path.open('wb') as f:
            f.truncate(max(b for c,rs in commands for a,b in rs)*4096)
            p=0
            for c,rs in commands:
                if c != 'new': continue
                for a,b in rs:
                    n=(b-a)*4096
                    f.seek(a*4096); f.write(payload[p:p+n]); p+=n
        del payload
        with path.open('rb') as f:
            fs=ExtFS(f)
            for entry in ('/bin/camera-system','/bin/camera-test','/bin/camera-gui','/bin/dji_network','/bin/msg2dbus','/bin/phocus','/etc/init/camera-test.rc'):
                try: content=fs.get(entry).open().read()
                except FileNotFoundError: continue
                target=selected/(part+'-'+Path(entry).name)
                target.write_bytes(content)
                strings=[s.decode('ascii') for s in re.findall(rb'[\x20-\x7e]{5,}',content) if re.search(rb'wifi.?region|2gonly|ProdConfig|is_2gonly|setWiFiModeList|Identity/Wifi|UsbhostHandler',s,re.I)]
                results.append(dict(partition=part,path=entry,bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),strings=strings))
        print(part+' 解包完成',flush=True)
manifest['binaries']=results
(OUT/'initial-evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
