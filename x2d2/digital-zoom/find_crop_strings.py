#!/usr/bin/env python3
"""Find the existing aspect-crop call in a local extract.

Digital zoom is not a new sensor mode. The body already records a rectangle
for 16:9, square and XPan. This only prints matching text from files you
already extracted. It does not unpack a CIM, write a file, or talk to a camera.

Run from this directory, pointing at your own extract, not at this repo:

    python3 find_crop_strings.py /path/to/local/extract
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from pathlib import Path
from typing import BinaryIO, Iterator

NEEDLES = (
    "setcrop",
    "croprect",
    "cropwindow",
    "croparea",
    "aspectratio",
    "imageaspect",
    "sensorcrop",
    "readoutwindow",
    "xpan",
)

SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf",
    ".zip", ".gz", ".pyc",
}

DEFAULT_CHUNK_SIZE = 64 * 1024
MAX_EXCERPT_LENGTH = 160


def _files(root: Path) -> Iterator[Path]:
    """Yield regular files deterministically without following symbolic links."""

    if root.is_symlink():
        return
    try:
        if root.is_file():
            yield root
            return
        if not root.is_dir():
            return
    except OSError:
        return

    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        dirnames[:] = sorted(
            name for name in dirnames
            if not (directory_path / name).is_symlink()
        )
        for name in sorted(filenames):
            path = directory_path / name
            try:
                if not path.is_symlink() and path.is_file():
                    yield path
            except OSError:
                continue


def _open_readonly(path: Path) -> BinaryIO:
    """Open a file read-only and ask the OS not to follow a final symlink."""

    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    return os.fdopen(descriptor, "rb")


def _matching_ascii_strings(
    stream: BinaryIO,
    needles: tuple[str, ...],
    chunk_size: int,
) -> Iterator[str]:
    """Yield bounded excerpts from matching printable-ASCII runs.

    State is retained between reads, so both the printable run and a needle may
    cross a chunk boundary. Memory use stays bounded even for a very long run.
    """

    longest_needle = max((len(needle) for needle in needles), default=0)
    if longest_needle == 0:
        return

    search_tail = ""
    before_match: deque[str] = deque(maxlen=MAX_EXCERPT_LENGTH)
    excerpt: list[str] | None = None

    def finish_run() -> str | None:
        nonlocal search_tail, before_match, excerpt
        result = None
        if excerpt is not None:
            result = "".join(excerpt)
        search_tail = ""
        before_match.clear()
        excerpt = None
        return result

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        for byte in chunk:
            if 32 <= byte < 127:
                character = chr(byte)
                if excerpt is None:
                    before_match.append(character)
                elif len(excerpt) < MAX_EXCERPT_LENGTH:
                    excerpt.append(character)

                search_tail = (search_tail + character.casefold())[-longest_needle:]
                if excerpt is None and any(needle in search_tail for needle in needles):
                    excerpt = list(before_match)
            else:
                result = finish_run()
                if result is not None:
                    yield result

    result = finish_run()
    if result is not None:
        yield result


def scan(
    root: Path,
    needles: tuple[str, ...] = NEEDLES,
    limit: int = 40,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[tuple[str, str]]:
    """Scan local files without modifying them or following symbolic links."""

    if limit <= 0:
        raise ValueError("limit must be a positive integer")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")

    hits: list[tuple[str, str]] = []
    lowered = tuple(item.casefold() for item in needles if item)
    if not lowered:
        return hits

    root_is_file = root.is_file() and not root.is_symlink()
    for path in _files(root):
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            with _open_readonly(path) as stream:
                for text in _matching_ascii_strings(stream, lowered, chunk_size):
                    if root_is_file:
                        display_path = path.name
                    else:
                        try:
                            display_path = path.relative_to(root).as_posix()
                        except ValueError:
                            # _files() must never escape root, but fail closed if
                            # a platform-specific path representation surprises us.
                            continue
                    hits.append((display_path, text))
                    if len(hits) >= limit:
                        return hits
        except OSError:
            continue
    return hits


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path, help="file or directory you extracted locally")
    parser.add_argument("--limit", type=_positive_int, default=40)
    parser.add_argument("--json", action="store_true", help="print a JSON array instead of text")
    args = parser.parse_args(argv)
    if not args.extract.exists():
        print(f"error: not found: {args.extract}", file=sys.stderr)
        return 1
    hits = scan(args.extract, limit=args.limit)
    if args.json:
        json.dump(
            [{"path": path, "text": text} for path, text in hits],
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        print()
        return 0
    if not hits:
        print("no crop or aspect strings")
        return 0
    for path, text in hits:
        print(f"{path}\n  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
