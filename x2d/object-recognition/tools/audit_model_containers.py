#!/usr/bin/env python3
"""只读比较原厂模型容器与相关错误分支；不解密、验签、导出密钥或接设备。

格式字段名参考公开 IMaH 结构描述，并与本项目原厂读取指令交叉核对。
不使用公开工具的密钥表或执行其代码。摘要一致不是签名验证成功。
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile

SOFT_VERIFY_SHA256 = '696c145a40004c769009bd83128bbaef6f7fb67072b54123fb5194be51f93826'


def inspect_container(data):
    if len(data) < 192 or data[:4] != b'IM*H':
        raise ValueError('not a complete IM*H header')
    u32 = lambda offset: struct.unpack_from('<I', data, offset)[0]
    version, size, header, signature, payload = (u32(o) for o in (4, 8, 16, 20, 24))
    count = u32(156)
    if version != 2 or not 1 <= count <= 1024:
        raise ValueError('unsupported version or chunk count')
    if header != 192 + 32 * count or header > len(data):
        raise ValueError('inconsistent chunk table size')
    if size != len(data) or header + signature + payload != len(data):
        raise ValueError('inconsistent total size')
    if signature not in (64, 256, 384):
        raise ValueError('unsupported signature extent')
    chunks = []
    for index in range(count):
        start = 192 + index * 32
        offset, length, attributes = struct.unpack_from('<III', data, start + 4)
        if offset > payload or length > payload - offset:
            raise ValueError('chunk outside payload')
        chunks.append({'offset': offset, 'bytes': length, 'attributes': attributes})
    def identifier(offset):
        value = data[offset:offset + 4]
        if not all(32 <= b <= 126 for b in value):
            raise ValueError('nonprintable identifier; not exported')
        return value.decode('ascii')
    # Whitelist output fields. Never export scramble material, signatures, IVs,
    # arbitrary strings, payload bytes or the raw header.
    return {
        'file_sha256': hashlib.sha256(data).hexdigest(), 'file_bytes': len(data),
        'header_version': version, 'header_bytes': header, 'signature_bytes': signature,
        'payload_bytes': payload, 'auth_algorithm_raw': u32(36),
        'auth_algorithm_low16': u32(36) & 0xffff,
        'auth_identifier': identifier(40), 'encryption_identifier': identifier(44),
        'os_arch_compression_anti_bytes': list(data[32:36]), 'chunk_count': count,
        'chunks': chunks,
        'stored_payload_sha256_matches': hashlib.sha256(data[header + signature:]).digest() == data[160:192],
        'signature_verified': False, 'decrypted': False,
    }


def audit_models(vendor):
    root = vendor / 'model/ml'
    paths = sorted(root.rglob('*.enc'))
    if not paths:
        raise ValueError('no model containers')
    return [{'file': p.relative_to(root).as_posix(), **inspect_container(p.read_bytes())} for p in paths]


def audit_related_error_branch(system):
    path = system / 'lib64/libfw_verify_util.so'
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOFT_VERIFY_SHA256:
        raise ValueError('requires pinned X2D II 1.3.16.2 soft verification library')
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        def read_va(address, length):
            for segment in elf.iter_segments():
                base = segment['p_vaddr']
                if segment['p_type'] == 'PT_LOAD' and base <= address and address + length <= base + segment['p_filesz']:
                    return segment.data()[address - base:address - base + length]
            raise ValueError('address outside file-backed ELF segment')
        expected = {
            0x18e8: 0x79404a61,  # reads auth algorithm low 16 bits
            0x18ec: 0x7100183f,  # compares against 6, not this model corpus's 3
            0x1960: 0x97fffe0a,  # calls sec_cipher_ecc_sha256_verify PLT
            0x1968: 0x35000c48,  # nonzero verification result -> error block
            0x1b00: 0x12800134,  # error block returns -10
        }
        for address, word in expected.items():
            if read_va(address, 4) != struct.pack('<I', word):
                raise ValueError('unexpected original instruction')
        if read_va(0x1e62, 64).split(b'\0', 1)[0] != b'ecdsa verify fail: res=%d\n':
            raise ValueError('unexpected original diagnostic string')
    return {
        'library_sha256': SOFT_VERIFY_SHA256,
        'entry': 'plt_fw_verify_file_soft', 'auth_algorithm_low16_required': 6,
        'signature_failure_return': -10,
        'same_as_executed_tee_path': False,
        'actual_tee_error_meaning_proven': False,
        'usable_as_model_verifier_substitute': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-vendor-root', type=Path, required=True)
    p.add_argument('--source-vendor-root', type=Path, required=True)
    p.add_argument('--source-system-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    target, source = audit_models(a.target_vendor_root), audit_models(a.source_vendor_root)
    fields = ('header_version', 'header_bytes', 'signature_bytes', 'auth_algorithm_raw',
              'auth_identifier', 'encryption_identifier', 'os_arch_compression_anti_bytes', 'chunk_count')
    layouts = {json.dumps({k: row[k] for k in fields}, sort_keys=True) for row in target + source}
    report = {'scope': 'X2D 4.2.0 / X2D II 1.3.16.2 original model containers',
              'target_models': target, 'source_models': source,
              'common_public_layout': json.loads(next(iter(layouts))) if len(layouts) == 1 else None,
              'all_stored_payload_digests_match': all(r['stored_payload_sha256_matches'] for r in target + source),
              'related_error_branch': audit_related_error_branch(a.source_system_root),
              'device_accessed': False, 'firmware_executed': False,
              'key_material_exported': False, 'signature_verified': False}
    with a.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'target_models': len(target), 'source_models': len(source),
                      'common_public_layout': report['common_public_layout'],
                      'all_stored_payload_digests_match': report['all_stored_payload_digests_match'],
                      'actual_tee_error_meaning_proven': False, 'device_accessed': False}))


if __name__ == '__main__':
    main()
