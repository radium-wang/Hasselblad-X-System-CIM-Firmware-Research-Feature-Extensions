#!/usr/bin/env python3
"""Rotate only the stock X2D 100C 4.2.0 main-screen logo by 180 degrees offline."""

import argparse
import hashlib
from pathlib import Path

from extract_main_startup_logo import EXPECTED_SHA256, encode_png, rodata_mapping

PALETTE_ADDRESS = 0x17AD78
PIXELS_ADDRESS = 0x17AD89
WIDTH = 162
HEIGHT = 128
PALETTE = bytes.fromhex('0010203040506070808f9fafbfcfdfefff')


def rotate(elf):
    if hashlib.sha256(elf).hexdigest() != EXPECTED_SHA256:
        raise ValueError('requires unchanged official 4.2.0 eagle-backend.so')
    vma, section_offset, section_size = rodata_mapping(elf)
    if not (vma <= PALETTE_ADDRESS < PIXELS_ADDRESS and
            PIXELS_ADDRESS + WIDTH * HEIGHT <= vma + section_size):
        raise ValueError('stock main logo is outside .rodata')
    palette_offset = section_offset + PALETTE_ADDRESS - vma
    pixel_offset = section_offset + PIXELS_ADDRESS - vma
    if elf[palette_offset:pixel_offset] != PALETTE:
        raise ValueError('unexpected stock main-screen palette')
    original_indexes = elf[pixel_offset:pixel_offset + WIDTH * HEIGHT]
    if len(original_indexes) != WIDTH * HEIGHT or max(original_indexes) >= len(PALETTE):
        raise ValueError('invalid stock image indexes')
    rotated_indexes = original_indexes[::-1]
    patched = elf[:pixel_offset] + rotated_indexes + elf[pixel_offset + WIDTH * HEIGHT:]
    if patched[:pixel_offset] != elf[:pixel_offset] or patched[pixel_offset + WIDTH * HEIGHT:] != elf[pixel_offset + WIDTH * HEIGHT:]:
        raise AssertionError('unexpected binary change outside logo pixels')
    if patched[pixel_offset:pixel_offset + WIDTH * HEIGHT][::-1] != original_indexes:
        raise AssertionError('180-degree rotation does not reverse to stock image')
    grayscale = bytes(PALETTE[index] for index in rotated_indexes)
    return patched, grayscale, sum(a != b for a, b in zip(original_indexes, rotated_indexes))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original-elf', type=Path, required=True)
    p.add_argument('--output-elf', type=Path, required=True)
    p.add_argument('--preview', type=Path, required=True)
    args = p.parse_args()
    if not args.output_elf.name.endswith('.NOT_FOR_DEVICE'):
        p.error('binary candidate filename must end in .NOT_FOR_DEVICE')
    if args.output_elf.exists() or args.preview.exists():
        raise FileExistsError('outputs must not already exist')
    patched, grayscale, changed = rotate(args.original_elf.read_bytes())
    args.output_elf.parent.mkdir(parents=True, exist_ok=True)
    with args.output_elf.open('xb') as f:
        f.write(patched)
    with args.preview.open('xb') as f:
        f.write(encode_png(WIDTH, HEIGHT, grayscale))
    print('changed_logo_index_bytes', changed)
    print('candidate_elf_sha256', hashlib.sha256(patched).hexdigest())
    print('preview_sha256', hashlib.sha256(args.preview.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
