"""固定版本 GUI 的通用 QRC 文本读取辅助函数，仅供离线解析。"""
import struct
from firmware_image import system_elf

GUI_SHA = '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0'


def resource(binary, tree_address, names_address, data_address, node, expected_name):
    if node < 0:
        raise ValueError('Negative resource index')
    row = binary.read(tree_address + node * 22, 22)
    name_offset, flags = struct.unpack_from('>IH', row)
    length = struct.unpack('>H', binary.read(names_address + name_offset, 2))[0]
    name = binary.read(names_address + name_offset + 6, length * 2).decode('utf-16-be')
    if flags != 0 or name != expected_name:
        raise ValueError('Unexpected resource name or compression flags')
    offset = struct.unpack_from('>I', row, 10)[0]
    size = struct.unpack('>I', binary.read(data_address + offset, 4))[0]
    return binary.read(data_address + offset + 4, size).decode('utf-8')
