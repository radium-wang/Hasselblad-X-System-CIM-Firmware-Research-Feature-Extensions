#!/usr/bin/env python3
"""Enable or restore the dormant AF-C UI gate in X2D 100C firmware 4.2.0.

This tool intentionally accepts only the exact known stock or patched
``/system/bin/camera-gui`` binary.  It changes the little-endian Boolean value
for the compiled-QML property ``CameraUI.canChangeAfc`` from 0 to 1 (or back).

It does not install anything on a camera and it does not create an OTA/CIM.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path


TOOL_VERSION = "1.0"
TARGET_DESCRIPTION = "Hasselblad X2D 100C firmware 4.2.0 /system/bin/camera-gui"
FILE_SIZE = 47_614_272
ELF_BUILD_ID = "043ca393141faabc947759e1d4f6f802"

# File offset of the 32-bit little-endian Boolean value.  Only its first byte
# differs between the two valid states.
PATCH_OFFSET = 0x018A2A64
HIDDEN_VALUE = bytes.fromhex("00 00 00 00")
ENABLED_VALUE = bytes.fromhex("01 00 00 00")

# Extra structural guards around the patch site.  SHA-256 validation remains
# the primary identity check.
PREFIX = bytes.fromhex("54 00 c0 01 54 00 20 03 56 00 00 00 08 00 01 00")
SUFFIX = bytes.fromhex("00 00 00 00 53 00 c0 01 53 00 a0 02")

STOCK_SHA256 = "16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0"
PATCHED_SHA256 = "08adea27596e3eb3a36c902b9f8815a73bf968e085cab6e9b34474828067a37a"


class PatchError(Exception):
    """An expected validation or patching failure."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, expected_digest: str, expected_value: bytes) -> str:
    if not path.is_file():
        raise PatchError(f"not a regular file: {path}")
    size = path.stat().st_size
    if size != FILE_SIZE:
        raise PatchError(f"unexpected size: expected {FILE_SIZE}, got {size}")

    digest = sha256(path)
    if digest != expected_digest:
        raise PatchError(
            "SHA-256 mismatch; refusing to touch an unknown firmware binary\n"
            f"  expected: {expected_digest}\n"
            f"  actual:   {digest}"
        )

    with path.open("rb") as stream:
        stream.seek(PATCH_OFFSET - len(PREFIX))
        prefix = stream.read(len(PREFIX))
        value = stream.read(4)
        suffix = stream.read(len(SUFFIX))
    if prefix != PREFIX or suffix != SUFFIX:
        raise PatchError("compiled-QML context does not match the known binary")
    if value != expected_value:
        raise PatchError(
            f"unexpected value at 0x{PATCH_OFFSET:x}: "
            f"expected {expected_value.hex()}, got {value.hex()}"
        )
    return digest


def classify(path: Path) -> tuple[str, str]:
    if not path.is_file():
        raise PatchError(f"not a regular file: {path}")
    digest = sha256(path)
    if digest == STOCK_SHA256:
        validate_file(path, STOCK_SHA256, HIDDEN_VALUE)
        return "stock (AF-C menu hidden)", digest
    if digest == PATCHED_SHA256:
        validate_file(path, PATCHED_SHA256, ENABLED_VALUE)
        return "patched (AF-C menu enabled)", digest
    raise PatchError(
        "unrecognized file; it is neither the exact stock nor known patched binary\n"
        f"  SHA-256: {digest}"
    )


def compare_single_change(
    before_path: Path, after_path: Path, before_byte: int, after_byte: int
) -> None:
    differences: list[tuple[int, int, int]] = []
    position = 0
    with before_path.open("rb") as before, after_path.open("rb") as after:
        while True:
            left = before.read(1024 * 1024)
            right = after.read(1024 * 1024)
            if not left and not right:
                break
            if len(left) != len(right):
                raise PatchError("output size changed unexpectedly")
            for index, (old, new) in enumerate(zip(left, right)):
                if old != new:
                    differences.append((position + index, old, new))
                    if len(differences) > 1:
                        raise PatchError("more than one byte changed")
            position += len(left)

    expected = [(PATCH_OFFSET, before_byte, after_byte)]
    if differences != expected:
        raise PatchError(
            f"unexpected binary difference: expected {expected}, got {differences}"
        )


def patch(mode: str, source: Path, destination: Path) -> None:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if source == destination:
        raise PatchError("input and output must be different files")
    if os.path.lexists(destination):
        raise PatchError(f"output already exists; refusing to overwrite: {destination}")

    if mode == "enable":
        input_digest = STOCK_SHA256
        output_digest = PATCHED_SHA256
        current_value = HIDDEN_VALUE
        new_value = ENABLED_VALUE
    else:
        input_digest = PATCHED_SHA256
        output_digest = STOCK_SHA256
        current_value = ENABLED_VALUE
        new_value = HIDDEN_VALUE

    validate_file(source, input_digest, current_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        shutil.copy2(source, destination)
        created = True
        with destination.open("r+b") as stream:
            stream.seek(PATCH_OFFSET)
            if stream.read(4) != current_value:
                raise PatchError("patch-site value changed between validation and write")
            stream.seek(PATCH_OFFSET)
            stream.write(new_value)
            stream.flush()
            os.fsync(stream.fileno())

        validate_file(destination, output_digest, new_value)
        compare_single_change(source, destination, current_value[0], new_value[0])
    except Exception:
        if created:
            try:
                destination.unlink()
            except OSError:
                pass
        raise

    print(f"target:          {TARGET_DESCRIPTION}")
    print(f"ELF Build ID:    {ELF_BUILD_ID}")
    print(f"operation:       {mode}")
    print(f"property:        CameraUI.canChangeAfc")
    print(f"file offset:     0x{PATCH_OFFSET:x}")
    print(f"change:          {current_value.hex()} -> {new_value.hex()}")
    print(f"input SHA-256:   {input_digest}")
    print(f"output SHA-256:  {output_digest}")
    print(f"output:          {destination}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=TOOL_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="identify and validate a file")
    inspect_parser.add_argument("file", type=Path)

    for name, help_text in (
        ("enable", "enable the AF-C menu gate"),
        ("disable", "restore the original hidden state"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("input", type=Path)
        command.add_argument("output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "inspect":
        path = args.file.expanduser().resolve()
        state, digest = classify(path)
        print(f"target:        {TARGET_DESCRIPTION}")
        print(f"state:         {state}")
        print(f"SHA-256:       {digest}")
        print(f"file:          {path}")
        return 0

    patch(args.command, args.input, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PatchError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
