"""Extract two fixed analysis ELFs from official 4.2.0 ota.zip, never run firmware."""
import argparse
import hashlib
import io
import zipfile
from pathlib import Path
import brotli
from dissect.extfs import ExtFS
from offline_elf import HASHES

OTA_SHA = '03c7e1e508bf17246e0be3e0b39d821683845561571dea57c09fcf0a3c9d736b'

def ranges(text):
    nums = list(map(int, text.split(',')))
    if not nums or nums[0] != len(nums) - 1 or nums[0] % 2:
        raise ValueError('Invalid range list')
    result = list(zip(nums[1::2], nums[2::2]))
    if any(not 0 <= a < b <= 131072 for a, b in result):
        raise ValueError('Range outside fixed firmware bounds')
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('ota')
    p.add_argument('--out', default='input')
    args = p.parse_args()
    raw = Path(args.ota).read_bytes()
    if hashlib.sha256(raw).hexdigest() != OTA_SHA:
        raise ValueError('Expected official X2D 4.2.0 ota.zip')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        lines = z.read('system.transfer.list').decode('ascii').splitlines()
        if lines[0] != '4' or lines[2:4] != ['0', '0']:
            raise ValueError('Unsupported transfer format')
        commands = [line.split() for line in lines[4:] if line.strip()]
        if any(len(c) != 2 or c[0] not in ('new', 'zero', 'erase') for c in commands):
            raise ValueError('Unsupported transfer operation')
        commands = [(op, ranges(rs)) for op, rs in commands]
        payload = brotli.decompress(z.read('system.new.dat.br'))
    expected = sum((b-a)*4096 for op, rs in commands if op == 'new' for a, b in rs)
    if expected != len(payload):
        raise ValueError('Payload size mismatch')
    size = max(b for _, rs in commands for _, b in rs) * 4096
    image = io.BytesIO(bytes(size))
    pos = 0
    for op, rs in commands:
        for a, b in rs:
            length = (b-a)*4096
            image.seek(a*4096)
            if op == 'new':
                image.write(payload[pos:pos+length]); pos += length
            else:
                image.write(bytes(length))
    image.seek(0)
    fs = ExtFS(image)
    entries = {}
    for name, expected_hash in HASHES.items():
        data = fs.get('/lib64/' + name).open().read()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError('Extracted ELF hash mismatch: ' + name)
        entries[name] = data
    out = Path(args.out)
    if any((out / name).exists() for name in entries):
        raise FileExistsError('Output exists; choose a fresh output directory')
    out.mkdir(parents=True, exist_ok=True)
    for name, data in entries.items():
        (out / name).write_bytes(data)
        print(name, len(data), HASHES[name])

if __name__ == '__main__':
    main()
