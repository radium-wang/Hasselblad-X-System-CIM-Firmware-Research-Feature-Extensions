#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline build: explicit upstream, compiler and output; never downloads/deploys."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

PIN = "361f452f3e89cdfaf04624db1c7641e3db410da9"
PUGI_PIN = "27b68329de32cf9c601ca8eb6c588fd639960c40"
ROOT = Path(__file__).resolve().parents[1]

def commit(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--compiler", default="clang++", help="clang++ executable, or Zig executable with --arm64")
    p.add_argument("--arm64", action="store_true", help="Zig 0.13.0 ARM64 Linux musl static build; not installation")
    a = p.parse_args()
    upstream = a.upstream.resolve()
    if commit(upstream) != PIN or commit(upstream / "pugixml") != PUGI_PIN:
        p.error("Upstream/submodule commit does not match the documented input pins")
    sources = sorted(upstream.glob("shijima/**/*.cc"))
    pugi = upstream / "pugixml/src/pugixml.cpp"
    if not sources or not pugi.is_file():
        p.error("Missing libshijima sources or pugixml submodule")
    output = a.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    compiler = [a.compiler, "c++", "-target", "aarch64-linux-musl", "-static", "-s"] if a.arm64 else [a.compiler]
    flags = ["-std=c++14", "-O2", "-Wno-unused-result", "-DSHIJIMA_DUK_STATIC_BUILD", "-pthread",
             "-I" + str(upstream), "-I" + str(upstream / "pugixml/src")]
    env = os.environ.copy()
    if a.arm64:
        env.update(ZIG_GLOBAL_CACHE_DIR=str(output.parent / "zig-global"),
                   ZIG_LOCAL_CACHE_DIR=str(output.parent / "zig-local"))
    subprocess.run(compiler + flags + [str(s) for s in sources + [pugi, ROOT / "native/engine.cc"]]
                   + ["-o", str(output)], check=True, env=env)
    report = {"libshijimaCommit": PIN, "pugixmlCommit": PUGI_PIN,
              "target": "aarch64-linux-musl" if a.arm64 else "host",
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "bytes": output.stat().st_size, "deviceValidated": False}
    output.with_name(output.name + ".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
