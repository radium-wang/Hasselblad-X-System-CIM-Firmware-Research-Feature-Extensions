#!/usr/bin/env python3
"""Validate the plan and fail closed when an installable build is requested.

This tool reads JSON and prints gate state. It does not build, sign, copy, or
install a firmware package and never accesses a camera.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MODULE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = MODULE_ROOT / "readiness-manifest.json"
TARGET_MODEL = "X2D II 100C"
TARGET_FIRMWARE = "1.3.16.2"
TARGET_PLATFORM = "10.00.09.77"

REQUIRED_BOOLEAN_GATES = (
    ("geometry", "coordinate_space_verified", "crop coordinate space is unverified"),
    ("backend", "interface_identified", "preview/capture crop interface is unidentified"),
    ("backend", "runtime_adapter_present", "runtime crop adapter is absent"),
    ("backend", "preview_verified", "preview crop is not hardware-verified"),
    ("backend", "capture_verified", "saved capture crop is not hardware-verified"),
    ("distribution", "vendor_signature_available", "vendor-authorized signature is unavailable"),
    (
        "distribution",
        "normal_updater_acceptance_verified",
        "normal CFexpress/Phocus updater acceptance is unverified",
    ),
    ("recovery", "cold_boot_recovery_verified", "cold-boot recovery is unverified"),
)


class ManifestError(ValueError):
    pass


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be an object")
    return value


def validate_manifest(data: object) -> dict[str, Any]:
    manifest = _mapping(data, "manifest")
    if manifest.get("schema_version") != 1:
        raise ManifestError("schema_version must be 1")

    target = _mapping(manifest.get("target"), "target")
    for key in ("model", "firmware", "platform"):
        if not isinstance(target.get(key), str) or not target[key].strip():
            raise ManifestError(f"target.{key} must be a non-empty string")
    expected_target = {
        "model": TARGET_MODEL,
        "firmware": TARGET_FIRMWARE,
        "platform": TARGET_PLATFORM,
    }
    for key, expected in expected_target.items():
        if target[key] != expected:
            raise ManifestError(f"target.{key} must be {expected}")

    for section in ("geometry", "backend", "distribution", "recovery", "deferred"):
        _mapping(manifest.get(section), section)
    distribution = manifest["distribution"]
    if distribution.get("channel") != "cfexpress-phocus":
        raise ManifestError("distribution.channel must be cfexpress-phocus")
    if not isinstance(distribution.get("installable"), bool):
        raise ManifestError("distribution.installable must be boolean")

    for section, key, _message in REQUIRED_BOOLEAN_GATES:
        value = manifest[section].get(key)
        if not isinstance(value, bool):
            raise ManifestError(f"{section}.{key} must be boolean")
    if not isinstance(manifest["backend"].get("raw_effect_verified"), bool):
        raise ManifestError("backend.raw_effect_verified must be boolean")
    for key in ("crop_metadata", "gps"):
        if not isinstance(manifest["deferred"].get(key), bool):
            raise ManifestError(f"deferred.{key} must be boolean")
    return manifest


def readiness_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers = [
        message
        for section, key, message in REQUIRED_BOOLEAN_GATES
        if not manifest[section][key]
    ]
    if not manifest["distribution"]["installable"]:
        blockers.append("manifest deliberately marks this candidate non-installable")
    return blockers


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ManifestError(f"cannot read manifest: {error}") from error
    except json.JSONDecodeError as error:
        raise ManifestError(f"invalid JSON: {error}") from error
    return validate_manifest(data)


def report(manifest: dict[str, Any]) -> dict[str, object]:
    blockers = readiness_blockers(manifest)
    return {
        "target": manifest["target"],
        "channel": manifest["distribution"]["channel"],
        "installable": not blockers,
        "declared_installable": manifest["distribution"]["installable"],
        "blockers": blockers,
        "raw_effect_verified": manifest["backend"]["raw_effect_verified"],
        "raw_effect_required_for_installable": False,
        "deferred": manifest["deferred"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="print a machine-readable report")
    parser.add_argument(
        "--require-installable",
        action="store_true",
        help="fail unless every backend, signing, updater and recovery gate is verified",
    )
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
    except ManifestError as error:
        print(f"READINESS MANIFEST INVALID: {error}", file=sys.stderr)
        return 1

    result = report(manifest)
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        state = "INSTALLABLE" if result["installable"] else "NOT INSTALLABLE"
        print(f"{state}: {result['target']['model']} {result['target']['firmware']}")
        for blocker in result["blockers"]:
            print(f"- {blocker}")
    if args.require_installable and not result["installable"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
