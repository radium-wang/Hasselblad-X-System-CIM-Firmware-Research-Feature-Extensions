#!/usr/bin/env python3
"""离线执行二代原厂帧转换函数；只验证描述符字节适配，不接设备／像素／AF。

输入为精确版本原厂 ELF 和合成帧描述符。Unicorn 运行原厂机器码；仅模拟
memset 和日志，禁止跳入其他代码。内存映射句柄为测试哨兵，不是机内地址。
生成的描述符只供这个转换入口，不能冒充完整 DSH frame 或有效帧租约。
"""
import argparse
import hashlib
import io
import json
import platform
import struct
import sys
from pathlib import Path

SOURCE_SHA = '98351d0906f3056cf780c5bf2adce65f544bb258c18dd62cfadb01607bdb1788'
ENTRY, END = 0x29a6fc, 0x29a958
WORK, STACK, TLS, STOP = 0x10000000, 0x11000000, 0x12000000, 0x13000000
CONVERTER_CORE_BYTES = 0x68
FRAME_MANAGER_RECORD_BYTES = 0x84


class EmulationUnavailable(RuntimeError):
    """宿主原生模拟器不安全；拒绝进入，而不是捕获 SIGILL 后继续。"""


def require_safe_emulation_host():
    # 已观察到 Darwin/arm64 + Unicorn 2.1.4 在首次 mem_map 的
    # init_cache_info 中执行 mrs ctr_el0 导致进程 SIGILL。
    # 未验证修复版本前保守禁用该平台，不提供强制绕过开关。
    if platform.system() == 'Darwin' and platform.machine().lower() in ('arm64', 'aarch64'):
        raise EmulationUnavailable(
            '本工具暂禁用 Apple Silicon macOS 上的 Unicorn 执行：'
            '已观察到 init_cache_info/CTR_EL0 引发 SIGILL；'
            '请使用 --descriptor-only 做纯数据检查。未执行原厂函数。')


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def require_complete_frame_record(record):
    """仅检查入队记录尺寸；不证明元数据语义、缓冲区持有或运行安全。

二代转换器只产出 0x68 字节核心，PushImage 却复制 0x84 字节。
不能将缺少的元数据补零冒充原厂完整记录；调用方须另行取得真实字段。
本函数不会调用 PushImage，也不会申请或释放帧。
"""
    if len(record) != FRAME_MANAGER_RECORD_BYTES:
        raise ValueError('FrameManager requires a complete 0x84-byte record; '
                         'a 0x68-byte converter core is not sufficient')
    return bytes(record)


def adapt_descriptor_for_converter(old, buffer_bytes):
    """转换一代 NV12 描述子集；不获取、复制、持有或释放像素缓冲区。

只接受已知两平面格式。buffer_bytes 必须由真实持有者提供；本工具仅使用
合成值。输出缺失二代完整帧的其他字段，禁止用于 DSH 回调本身。
"""
    if len(old) < 0x88:
        raise ValueError('short first-generation descriptor')
    fmt, width, height, count = (u32(old, x) for x in (0x28, 0x38, 0x3c, 0x80))
    if fmt != 2 or count != 2 or not width or not height or width % 2 or height % 2:
        raise ValueError('only nonempty even-sized two-plane NV12 is verified')
    if not 0 < buffer_bytes <= 0xffffffff:
        raise ValueError('explicit valid backing-buffer size required')
    new = bytearray(0xb8)
    new[:0x40] = old[:0x40]
    regions = []
    for i in range(count):
        src, dst = 0x40 + 16 * i, 0x40 + 28 * i
        stride, offset, rows = struct.unpack_from('<III', old, src)
        expected_rows = height if i == 0 else height // 2
        if stride < width or rows != expected_rows or offset + stride * rows > buffer_bytes:
            raise ValueError('plane geometry exceeds or mismatches backing buffer')
        region = (offset, offset + stride * rows)
        if any(region[0] < end and start < region[1] for start, end in regions):
            raise ValueError('overlapping NV12 planes')
        regions.append(region)
        struct.pack_into('<II', new, dst, stride, offset)
        struct.pack_into('<I', new, dst + 12, rows)
    struct.pack_into('<II', new, 0xb0, count, u32(old, 0x84))
    return bytes(new)


def execute_original(elf_data, descriptor, flags=0x1234):
    require_safe_emulation_host()
    # 门禁必须先于导入原生库、创建引擎及任何内存映射。
    from elftools.elf.elffile import ELFFile
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1,
        UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X30, UC_ARM64_REG_SP,
        UC_ARM64_REG_PC, UC_ARM64_REG_TPIDR_EL0)

    if hashlib.sha256(elf_data).hexdigest() != SOURCE_SHA:
        raise ValueError('unrecognized original X2D II dji_ml')
    if len(descriptor) != 0xb8:
        raise ValueError('converter fixture must be 0xb8 bytes')
    elf = ELFFile(io.BytesIO(elf_data))
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    for segment in elf.iter_segments():
        if segment['p_type'] != 'PT_LOAD':
            continue
        start = segment['p_vaddr'] & ~0xfff
        end = (segment['p_vaddr'] + segment['p_memsz'] + 0xfff) & ~0xfff
        uc.mem_map(start, end - start)
        uc.mem_write(segment['p_vaddr'], segment.data())
    for address in (WORK, STACK, TLS, STOP):
        uc.mem_map(address, 0x10000)
    uc.mem_write(WORK, descriptor)
    uc.mem_write(WORK + 0x1000, struct.pack('<H', flags))
    # Shared-map record supplied explicitly: original routine reads +18/+08/+28.
    mapping = bytearray(0x30)
    for offset, value in ((0x18, 0x1111222233334444), (8, 0x5555666677778888),
                          (0x28, 0x9999aaaabbbbcccc)):
        struct.pack_into('<Q', mapping, offset, value)
    uc.mem_write(WORK + 0x2000, bytes(mapping))
    uc.mem_write(WORK + 0x3000, b'\xa5' * 0x100)
    for reg, value in ((UC_ARM64_REG_X0, WORK), (UC_ARM64_REG_X1, WORK + 0x1000),
            (UC_ARM64_REG_X2, WORK + 0x2000), (UC_ARM64_REG_X3, WORK + 0x3000),
            (UC_ARM64_REG_SP, STACK + 0xf000), (UC_ARM64_REG_TPIDR_EL0, TLS),
            (UC_ARM64_REG_X30, STOP)):
        uc.reg_write(reg, value)
    calls = []

    def hook(machine, address, size, unused):
        if address == STOP:
            machine.emu_stop(); return
        if ENTRY <= address < END:
            return
        calls.append(hex(address))
        if address == 0x6b840:  # memset only
            destination = machine.reg_read(UC_ARM64_REG_X0)
            length = machine.reg_read(UC_ARM64_REG_X2)
            if destination != WORK + 0x3000 or length != 0x68:
                raise RuntimeError('unexpected memory operation')
            machine.mem_write(destination, bytes([machine.reg_read(UC_ARM64_REG_X1) & 255]) * length)
        elif address in (0x28e7f8, 0x28e8b8):  # log / error text only
            machine.reg_write(UC_ARM64_REG_X0, 0)
        else:
            raise RuntimeError('unexpected original call; refused: ' + hex(address))
        machine.reg_write(UC_ARM64_REG_PC, machine.reg_read(UC_ARM64_REG_X30))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(ENTRY, STOP + 4, timeout=1000000, count=10000)
    if uc.reg_read(UC_ARM64_REG_PC) != STOP:
        raise RuntimeError('original function did not return within budget')
    guard = bytes(uc.mem_read(WORK + 0x3068, 0x98))
    if guard != b'\xa5' * 0x98:
        raise RuntimeError('output guard overwritten')
    return uc.reg_read(UC_ARM64_REG_X0) & 0xffffffff, bytes(uc.mem_read(WORK + 0x3000, 0x68)), calls


def fixture(width=1280, height=720, stride=1344, offset=256):
    result = bytearray(0x88)
    struct.pack_into('<I', result, 0x28, 2)
    struct.pack_into('<Q', result, 0x30, 123456789)
    struct.pack_into('<II', result, 0x38, width, height)
    struct.pack_into('<III', result, 0x40, stride, offset, height)
    struct.pack_into('<III', result, 0x50, stride, offset + stride * height, height // 2)
    struct.pack_into('<II', result, 0x80, 2, 123)
    return bytes(result), offset + stride * (height + height // 2)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dji-ml', type=Path)
    p.add_argument('--descriptor-only', action='store_true',
                   help='仅检查合成描述符，不导入或调用 Unicorn，不读取固件')
    a = p.parse_args()
    if not a.descriptor_only:
        try:
            require_safe_emulation_host()
        except EmulationUnavailable as error:
            print(str(error), file=sys.stderr)
            return 2
        if a.source_dji_ml is None:
            p.error('执行模拟需要 --source-dji-ml；纯数据检查使用 --descriptor-only')
    old, size = fixture()
    donor = adapt_descriptor_for_converter(old, size)
    if a.descriptor_only:
        print(json.dumps({'status': 'descriptor_only', 'descriptor_bytes': len(donor),
            'planes': u32(donor, 0xb0), 'frame_id': u32(donor, 0xb4),
            'converter_core_bytes': CONVERTER_CORE_BYTES,
            'frame_manager_record_bytes': FRAME_MANAGER_RECORD_BYTES,
            'ready_for_frame_manager': False,
            'original_converter_executed': False, 'device_accessed': False,
            'live_buffer_ownership_verified': False}, indent=2))
        return 0
    code, output, calls = execute_original(a.source_dji_ml.read_bytes(), donor)
    print(json.dumps({'original_converter_return': code, 'format': u32(output, 0x18),
        'width': u32(output, 0x1c), 'height': u32(output, 0x20), 'planes': u32(output, 0x24),
        'plane_records': [list(struct.unpack_from('<III', output, 0x28 + i * 12)) for i in range(2)],
        'timestamp': struct.unpack_from('<Q', output, 0x58)[0], 'frame_id': u32(output, 0x60),
        'mocked_calls': calls, 'device_accessed': False, 'live_buffer_ownership_verified': False}, indent=2))


if __name__ == '__main__':
    sys.exit(main())
