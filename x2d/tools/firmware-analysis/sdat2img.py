#!/usr/bin/env python3
"""Rebuild a full Android block image from a full-OTA *.new.dat.br file."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import brotli


BLOCK_SIZE = 4096


def parse_ranges(spec: str) -> list[tuple[int, int]]:
    values = [int(value) for value in spec.split(",")]
    endpoint_count = values[0]
    endpoints = values[1:]
    if endpoint_count != len(endpoints) or endpoint_count % 2:
        raise ValueError(f"invalid range set: {spec}")
    return list(zip(endpoints[::2], endpoints[1::2]))


def decompress_brotli(source: Path, destination: Path) -> None:
    decoder = brotli.Decompressor()
    with source.open("rb") as src, destination.open("wb") as dst:
        while chunk := src.read(1024 * 1024):
            dst.write(decoder.process(chunk))
    if not decoder.is_finished():
        raise ValueError(f"incomplete Brotli stream: {source}")


def copy_exact(src, dst, byte_count: int, sha1: hashlib._Hash) -> None:
    remaining = byte_count
    while remaining:
        chunk = src.read(min(1024 * 1024, remaining))
        if not chunk:
            raise EOFError(f"new-data stream ended with {remaining} bytes missing")
        dst.write(chunk)
        sha1.update(chunk)
        remaining -= len(chunk)


def rebuild(transfer_list: Path, compressed_data: Path, output_image: Path) -> None:
    lines = [line.strip() for line in transfer_list.read_text().splitlines() if line.strip()]
    version = int(lines[0])
    if version not in {1, 2, 3, 4}:
        raise ValueError(f"unsupported transfer-list version: {version}")

    command_start = 2 if version == 1 else 4
    commands: list[tuple[str, list[tuple[int, int]]]] = []
    max_block = 0
    for line in lines[command_start:]:
        operation, _, spec = line.partition(" ")
        if operation not in {"new", "zero", "erase"}:
            raise ValueError(f"full OTA expected; unsupported operation: {operation}")
        ranges = parse_ranges(spec)
        commands.append((operation, ranges))
        max_block = max(max_block, *(end for _, end in ranges))

    new_data = compressed_data.with_suffix("")
    print(f"decompressing {compressed_data.name} -> {new_data.name}")
    decompress_brotli(compressed_data, new_data)

    expected_new_bytes = sum(
        (end - start) * BLOCK_SIZE
        for operation, ranges in commands
        if operation == "new"
        for start, end in ranges
    )
    if new_data.stat().st_size != expected_new_bytes:
        raise ValueError(
            f"new-data size mismatch: got {new_data.stat().st_size}, "
            f"expected {expected_new_bytes}"
        )

    digest = hashlib.sha1()
    with new_data.open("rb") as src, output_image.open("w+b") as dst:
        dst.truncate(max_block * BLOCK_SIZE)
        for operation, ranges in commands:
            if operation != "new":
                continue
            for start, end in ranges:
                dst.seek(start * BLOCK_SIZE)
                copy_exact(src, dst, (end - start) * BLOCK_SIZE, digest)

    print(
        f"wrote {output_image} ({max_block} blocks, "
        f"new-data SHA-1 {digest.hexdigest()})"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("transfer_list", type=Path)
    parser.add_argument("new_dat_br", type=Path)
    parser.add_argument("output_image", type=Path)
    args = parser.parse_args()
    rebuild(args.transfer_list, args.new_dat_br, args.output_image)


if __name__ == "__main__":
    main()
