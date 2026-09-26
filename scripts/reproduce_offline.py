#!/usr/bin/env python3
"""Run every safe, repository-contained reproduction check.

The runner never connects to a camera, writes firmware, installs a payload, or
starts an experiment with device side effects. Optional firmware roots are
read-only inputs for tests that explicitly opt in through environment vars.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run publication checks and all safe offline tests. "
            "No camera or firmware-writing operation is performed."
        )
    )
    for option, variable, help_text in (
        ("--source-system-root", "X2D_SOURCE_SYSTEM_ROOT", "read-only X2D II system root"),
        ("--source-vendor-root", "X2D_SOURCE_VENDOR_ROOT", "read-only X2D II vendor root"),
        ("--target-system-root", "X2D_TARGET_SYSTEM_ROOT", "read-only X2D system root"),
        ("--target-vendor-root", "X2D_TARGET_VENDOR_ROOT", "read-only X2D vendor root"),
    ):
        parser.add_argument(option, dest=variable.lower(), help=help_text)
    return parser.parse_args()


def command_label(command: list[str], cwd: Path) -> str:
    rendered = " ".join(command[1:] if command and command[0] == PYTHON else command)
    return f"{rendered} (in {cwd.relative_to(ROOT) if cwd != ROOT else '.'})"


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    print(f"\n>>> {command_label(command, cwd)}")
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    args = parse_args()
    values = {
        "X2D_SOURCE_SYSTEM_ROOT": args.x2d_source_system_root,
        "X2D_SOURCE_VENDOR_ROOT": args.x2d_source_vendor_root,
        "X2D_TARGET_SYSTEM_ROOT": args.x2d_target_system_root,
        "X2D_TARGET_VENDOR_ROOT": args.x2d_target_vendor_root,
    }
    supplied = [name for name, value in values.items() if value]
    if supplied and len(supplied) != len(values):
        missing = sorted(set(values) - set(supplied))
        raise SystemExit(
            "Firmware roots must be supplied together; missing: " + ", ".join(missing)
        )

    env = os.environ.copy()
    env.update({name: value for name, value in values.items() if value})
    if not supplied:
        print("No firmware roots supplied; input-gated tests will be skipped.")
    else:
        print("Using firmware roots as read-only test inputs; no device access is performed.")

    run([PYTHON, "scripts/validate_public_repo.py"], ROOT, env)
    run(
        [PYTHON, "x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/check_loader_component.py"],
        ROOT,
        env,
    )
    run(
        [PYTHON, "-m", "unittest", "test_candidate.py"],
        ROOT / "x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate",
        env,
    )
    run(
        [PYTHON, "-m", "unittest", "discover", "-s",
         "x2d/object-recognition/CodeTests/offline-contract", "-p", "test_*.py"],
        ROOT,
        env,
    )
    run(
        [PYTHON, "-m", "unittest", "discover", "-s",
         "x2d/CodeTests/shutter-animation-preview", "-p", "test_analyze_blackout.py"],
        ROOT,
        env,
    )
    run(
        [PYTHON, "-m", "unittest", "x2d/CodeTests/factory-debug-ui/test_factory_debug_ui.py"],
        ROOT,
        env,
    )
    print("\nOFFLINE REPRODUCTION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
