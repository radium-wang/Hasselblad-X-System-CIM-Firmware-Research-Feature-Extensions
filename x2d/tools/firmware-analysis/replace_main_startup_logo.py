#!/usr/bin/env python3
"""仅在电脑上生成 X2D 100C 4.2.0 主屏 Logo 的 ELF 替换候选。"""

import argparse
import hashlib
import struct
import zlib
from pathlib import Path

from extract_main_startup_logo import EXPECTED_SHA256, encode_png, rodata_mapping


PALETTE_ADDRESS = 0x17AD78
PIXELS_ADDRESS = 0x17AD89
WIDTH = 162
HEIGHT = 128


def read_png_grayscale(path: Path, convert_to_gray: bool = False) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("目标图片必须是 PNG")
    position = 8
    header = None
    compressed = bytearray()
    finished = False
    while position + 12 <= len(data):
        length = struct.unpack_from(">I", data, position)[0]
        kind = data[position + 4 : position + 8]
        end = position + 12 + length
        if end > len(data):
            raise ValueError("PNG 块越界")
        body = data[position + 8 : position + 8 + length]
        expected_crc = struct.unpack_from(">I", data, position + 8 + length)[0]
        if zlib.crc32(kind + body) != expected_crc:
            raise ValueError("PNG 块 CRC 错误")
        if kind == b"IHDR":
            if header is not None or len(body) != 13:
                raise ValueError("PNG IHDR 无效")
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            compressed.extend(body)
        elif kind == b"IEND":
            finished = True
            break
        elif kind in (b"PLTE", b"tRNS"):
            raise ValueError("请先把索引色或透明图片转为不透明灰度 PNG")
        elif kind[0] & 0x20 == 0:
            raise ValueError(f"不支持 PNG 必需块 {kind!r}")
        position = end
    if header is None or not compressed or not finished:
        raise ValueError("PNG 缺少图像数据")
    width, height, depth, color_type, compression, filtering, interlace = header
    if (width, height) != (WIDTH, HEIGHT):
        raise ValueError(f"图片必须是 {WIDTH}×{HEIGHT}，实际为 {width}×{height}")
    if depth != 8 or color_type not in (0, 2, 6) or (compression, filtering, interlace) != (0, 0, 0):
        raise ValueError("仅支持 8 位、非交错的灰度或不透明 RGB/RGBA PNG")
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    row_size = width * channels
    raw = zlib.decompress(bytes(compressed))
    if len(raw) != height * (row_size + 1):
        raise ValueError("PNG 解压长度异常")
    grayscale = bytearray()
    previous = bytearray(row_size)
    for y in range(height):
        offset = y * (row_size + 1)
        filter_type = raw[offset]
        row = bytearray(raw[offset + 1 : offset + 1 + row_size])
        if filter_type > 4:
            raise ValueError("PNG 行滤镜无效")
        for x in range(row_size):
            left = row[x - channels] if x >= channels else 0
            above = previous[x]
            upper_left = previous[x - channels] if x >= channels else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            else:
                predictor = 0
            row[x] = (row[x] + predictor) & 0xFF
        if channels == 1:
            grayscale.extend(row)
        else:
            for x in range(0, row_size, channels):
                if row[x] != row[x + 1] or row[x] != row[x + 2]:
                    if not convert_to_gray:
                        raise ValueError("主屏原厂绘制路径仅支持灰度；目标图片含彩色像素。可显式使用 --convert-to-gray")
                if channels == 4 and row[x + 3] != 255:
                    raise ValueError("主屏原厂绘制路径不支持透明像素")
                grayscale.append((54 * row[x] + 183 * row[x + 1] + 19 * row[x + 2] + 128) // 256)
        previous = row
    return width, height, bytes(grayscale)


def make_candidate(original: bytes, grayscale: bytes) -> tuple[bytes, int, bytes]:
    if len(grayscale) != WIDTH * HEIGHT:
        raise ValueError("灰度像素数量与主屏 Logo 尺寸不匹配")
    if hashlib.sha256(original).hexdigest() != EXPECTED_SHA256:
        raise ValueError("原厂 ELF SHA-256 不匹配，拒绝按固定偏移写入")
    vma, file_offset, size = rodata_mapping(original)
    if not (vma <= PALETTE_ADDRESS < PIXELS_ADDRESS and PIXELS_ADDRESS + WIDTH * HEIGHT <= vma + size):
        raise ValueError("主屏 Logo 不在原厂 .rodata 范围内")
    palette_offset = file_offset + PALETTE_ADDRESS - vma
    pixels_offset = file_offset + PIXELS_ADDRESS - vma
    palette = original[palette_offset:pixels_offset]
    if palette != bytes.fromhex("0010203040506070808f9fafbfcfdfefff"):
        raise ValueError("原厂 Logo 调色板不匹配")
    indexes = bytes(min(range(len(palette)), key=lambda i: abs(palette[i] - pixel)) for pixel in grayscale)
    patched = bytearray(original)
    old_indexes = original[pixels_offset : pixels_offset + WIDTH * HEIGHT]
    patched[pixels_offset : pixels_offset + WIDTH * HEIGHT] = indexes
    if patched[:pixels_offset] != original[:pixels_offset] or patched[pixels_offset + WIDTH * HEIGHT :] != original[pixels_offset + WIDTH * HEIGHT :]:
        raise AssertionError("候选修改超出 Logo 字节范围")
    if bytes(palette[index] for index in indexes) != bytes(palette[index] for index in patched[pixels_offset : pixels_offset + WIDTH * HEIGHT]):
        raise AssertionError("候选图像回读不匹配")
    changed = sum(a != b for a, b in zip(old_indexes, indexes))
    return bytes(patched), changed, bytes(palette[index] for index in indexes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_elf", type=Path)
    parser.add_argument("replacement_png", type=Path)
    parser.add_argument("output_elf", type=Path, help="必须以 .NOT_FOR_DEVICE 结尾的本地候选文件")
    parser.add_argument("--preview", type=Path, help="可选：输出按原厂调色板量化后的主屏预览 PNG")
    parser.add_argument("--convert-to-gray", action="store_true", help="显式将彩色输入转为主屏支持的灰度")
    args = parser.parse_args()
    if not args.output_elf.name.endswith(".NOT_FOR_DEVICE"):
        parser.error("输出文件名必须以 .NOT_FOR_DEVICE 结尾")
    if args.output_elf.resolve() == args.original_elf.resolve():
        parser.error("输出不能覆盖原厂 ELF")
    if args.preview and args.preview.resolve() in (args.replacement_png.resolve(), args.original_elf.resolve(), args.output_elf.resolve()):
        parser.error("预览输出不能覆盖输入或候选 ELF")
    _, _, grayscale = read_png_grayscale(args.replacement_png, args.convert_to_gray)
    candidate, changed, result = make_candidate(args.original_elf.read_bytes(), grayscale)
    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    args.output_elf.write_bytes(candidate)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        args.preview.write_bytes(encode_png(WIDTH, HEIGHT, result))
        print(f"量化后预览：{args.preview}")
    print(f"已生成离线候选：{args.output_elf}")
    print(f"Logo 索引字节变化：{changed}/{WIDTH * HEIGHT}")
    print(f"图像按原厂 17 级灰度表量化；回读像素 SHA-256：{hashlib.sha256(result).hexdigest()}")
    print(f"候选 ELF SHA-256：{hashlib.sha256(candidate).hexdigest()}")


if __name__ == "__main__":
    main()
