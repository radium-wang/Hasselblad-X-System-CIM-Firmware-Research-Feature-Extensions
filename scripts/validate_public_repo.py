#!/usr/bin/env python3
"""Fail closed on common publication mistakes in this repository."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".a", ".bin", ".cim", ".dat", ".elf", ".enc", ".img", ".model",
    ".o", ".ota", ".p12", ".pem", ".pyc", ".so", ".wad", ".zip",
}
IGNORED_PARTS = {".git", "__pycache__"}
TEXT_SUFFIXES = {
    "", ".c", ".cc", ".cjs", ".cpp", ".cs", ".h", ".hpp", ".html", ".js",
    ".json", ".md", ".ps1", ".py", ".qml", ".s", ".sh", ".svg", ".txt",
}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SENSITIVE = {
    "macOS user path": re.compile("/" + r"Users/[^/\s`\"']+"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s`\"']+"),
    "known device serial shape": re.compile(r"\bXT\d{8,}\b"),
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}


def files() -> list[Path]:
    return [
        path for path in ROOT.rglob("*")
        if path.is_file() and not any(part in IGNORED_PARTS for part in path.parts)
    ]


def main() -> int:
    problems: list[str] = []
    all_files = files()
    for path in all_files:
        rel = path.relative_to(ROOT)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden artifact: {rel}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in SENSITIVE.items():
            if pattern.search(text):
                problems.append(f"{name}: {rel}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(rel))
            except SyntaxError as error:
                problems.append(f"python syntax: {rel}:{error.lineno}: {error.msg}")
        if path.suffix == ".md":
            for match in MARKDOWN_LINK.finditer(text):
                link = match.group(1).split("#", 1)[0].strip().replace("%20", " ")
                if not link or "://" in link or link.startswith(("mailto:", "/")):
                    continue
                target = (path.parent / link).resolve()
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    problems.append(f"link leaves repository: {rel} -> {link}")
                    continue
                if not target.exists():
                    problems.append(f"broken link: {rel} -> {link}")

    if problems:
        print("PUBLICATION CHECK FAILED")
        for problem in sorted(set(problems)):
            print(f"- {problem}")
        return 1
    print(f"PUBLICATION CHECK PASSED: {len(all_files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
