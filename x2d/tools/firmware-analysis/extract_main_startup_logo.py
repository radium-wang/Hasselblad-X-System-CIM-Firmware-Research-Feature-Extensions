#!/usr/bin/env python3
"""从 X2D 100C 4.2.0 原厂 eagle-backend.so 离线还原主屏启动图。"""

import argparse
import hashlib
import struct
import zlib
from pathlib import Path


EXPECTED_SHA256 = "a0ac02a51d87d08fa61fd0d1e79af15db248af4b5b32603b9483d09f9b7f6217"
IMAGES = (
    ("original-main-logo.png", 0x17AD78, 0x17AD89, 162, 128),
    ("original-earth-explorer-logo.png", 0x17FE89, 0x17FF5C, 570, 426),
)


def rodata_mapping(elf: bytes) -> tuple[int, int, int]:
    if elf[:4] != b"\x7fELF" or elf[4:6] != b"\x02\x01":
        raise ValueError("输入不是小端 ELF64")
    shoff = struct.unpack_from("<Q", elf, 0x28)[0]
    entsize, count, names_index = struct.unpack_from("<HHH", elf, 0x3A)
    names_offset = struct.unpack_from("<Q", elf, shoff + names_index * entsize + 0x18)[0]
    for index in range(count):
        section = shoff + index * entsize
        name_offset = struct.unpack_from("<I", elf, section)[0]
        end = elf.index(0, names_offset + name_offset)
        name = elf[names_offset + name_offset : end]
        if name == b".rodata":
            return struct.unpack_from("<QQQ", elf, section + 0x10)
    raise ValueError("未找到 .rodata")


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def encode_png(width: int, height: int, grayscale: bytes) -> bytes:
    rows = b"".join(b"\0" + grayscale[y * width : (y + 1) * width] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(rows, 9))
        + png_chunk(b"IEND", b"")
    )


def extract(elf: bytes, address: int, pixels_address: int, width: int, height: int, mapping: tuple[int, int, int]) -> bytes:
    vma, file_offset, size = mapping
    if not (vma <= address < pixels_address and pixels_address + width * height <= vma + size):
        raise ValueError("图像范围不在 .rodata 内")
    palette_offset = file_offset + address - vma
    source_offset = file_offset + pixels_address - vma
    palette = elf[palette_offset:source_offset]
    indexes = elf[source_offset : source_offset + width * height]
    if not indexes or max(indexes) >= len(palette):
        raise ValueError("图像索引超出调色板")
    return encode_png(width, height, bytes(palette[index] for index in indexes))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eagle_backend", type=Path, help="从原厂 system 镜像提取的 eagle-backend.so")
    parser.add_argument("output_dir", type=Path, help="本地输出目录")
    args = parser.parse_args()
    elf = args.eagle_backend.read_bytes()
    actual = hashlib.sha256(elf).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"输入 SHA-256 不匹配：{actual}")
    mapping = rodata_mapping(elf)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, palette_address, pixels_address, width, height in IMAGES:
        output = args.output_dir / name
        output.write_bytes(extract(elf, palette_address, pixels_address, width, height, mapping))
        print(f"{output}: {width}x{height}")


if __name__ == "__main__":
    main()
