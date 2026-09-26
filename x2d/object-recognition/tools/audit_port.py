#!/usr/bin/env python3
"""Offline X2D II -> X2D object-recognition compatibility audit.

This program only reads extracted firmware trees.  It never contacts a camera,
changes an image, or stages files for installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
OBJECT_MODES = (
    "E_ObjectDetection_Off",
    "E_ObjectDetection_Human",
    "E_ObjectDetection_Pet",
    "E_ObjectDetection_Vehicle",
)
BACKEND_TOKENS = (
    "object_detection",
    "E_ObjectDetection",
    "ObjectInfo",
    "updateDetectedObjects",
    "onAfObjectDetectionCb",
)
ACCELERATOR_PATHS = (
    "lib/modules/vision_cnn.ko",
    "lib/modules/vision_vcr.ko",
    "lib/modules/vision_sgbm.ko",
)
DSP_PATHS = (
    "firmware/dspf/ss_dsp0.fw",
    "firmware/dspf/ss_dsp1.fw",
    "firmware/dspf/ss_dsp2.fw",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {"size": path.stat().st_size, "sha256": sha256(path)}


def parse_build_prop(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def contains_tokens(path: Path, tokens: Iterable[str]) -> dict[str, bool]:
    data = path.read_bytes()
    return {token: token.encode("ascii") in data for token in tokens}


def needed_libraries(path: Path) -> list[str]:
    try:
        from elftools.elf.elffile import ELFFile
    except ImportError as exc:  # pragma: no cover - exercised by CLI users
        raise RuntimeError("pyelftools is required to inspect ELF dependencies") from exc

    with path.open("rb") as stream:
        elf = ELFFile(stream)
        dynamic = elf.get_section_by_name(".dynamic")
        if dynamic is None:
            return []
        return sorted(
            {
                tag.needed
                for tag in dynamic.iter_tags()
                if tag.entry.d_tag == "DT_NEEDED"
            }
        )


def model_inventory(vendor_root: Path) -> list[dict[str, Any]]:
    base = vendor_root / "model" / "ml"
    if not base.is_dir():
        return []
    inventory = []
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        inventory.append({"path": path.relative_to(vendor_root).as_posix(), **file_record(path)})
    return inventory


def model_formats(models: list[dict[str, Any]]) -> list[str]:
    formats: set[str] = set()
    for model in models:
        name = model["path"]
        if name.endswith(".json.eng.enc"):
            formats.add("json.eng.enc")
        elif name.endswith(".tflite.eng.enc"):
            formats.add("tflite.eng.enc")
        elif name.endswith(".eng.enc"):
            formats.add("other.eng.enc")
    return sorted(formats)


def relative_hashes(root: Path, paths: Iterable[str]) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for relative in paths:
        path = root / relative
        result[relative] = file_record(path) if path.is_file() else None
    return result


def inspect_firmware(system_root: Path, vendor_root: Path) -> dict[str, Any]:
    build = parse_build_prop(system_root / "build.prop")
    camera_service = system_root / "bin" / "camera-service"
    ml_runtime = system_root / "bin" / "dji_ml"
    dependencies = needed_libraries(ml_runtime)
    dependency_records: dict[str, dict[str, Any] | None] = {}
    for name in dependencies:
        candidate = system_root / "lib64" / name
        dependency_records[name] = file_record(candidate) if candidate.is_file() else None

    models = model_inventory(vendor_root)
    return {
        "platform": {
            "product": build.get("ro.product.name"),
            "device": build.get("ro.product.device"),
            "model": build.get("ro.product.model"),
            "android_release": build.get("ro.build.version.release"),
            "android_sdk": build.get("ro.build.version.sdk"),
            "abi": build.get("ro.product.cpu.abi"),
            "incremental": build.get("ro.build.version.incremental"),
        },
        "camera_service": {
            **file_record(camera_service),
            "object_modes": contains_tokens(camera_service, OBJECT_MODES),
            "backend_contract": contains_tokens(camera_service, BACKEND_TOKENS),
        },
        "ml_runtime": {
            **file_record(ml_runtime),
            "needed": dependencies,
            "dependency_records": dependency_records,
        },
        "models": models,
        "model_formats": model_formats(models),
        "accelerator_modules": relative_hashes(system_root, ACCELERATOR_PATHS),
        "dsp_firmware": relative_hashes(vendor_root, DSP_PATHS),
    }


def all_present(flags: dict[str, bool]) -> bool:
    return bool(flags) and all(flags.values())


def differing_records(
    source: dict[str, dict[str, Any] | None],
    target: dict[str, dict[str, Any] | None],
) -> list[str]:
    differing = []
    for name in sorted(set(source) & set(target)):
        left = source[name]
        right = target[name]
        if left is None or right is None or left["sha256"] != right["sha256"]:
            differing.append(name)
    return differing


def evaluate(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    source_dependencies = source["ml_runtime"]["dependency_records"]
    target_dependencies = target["ml_runtime"]["dependency_records"]
    missing_target_dependencies = sorted(
        name for name in source["ml_runtime"]["needed"]
        if target_dependencies.get(name) is None
    )
    differing_common_dependencies = differing_records(source_dependencies, target_dependencies)
    differing_accelerator_modules = differing_records(
        source["accelerator_modules"], target["accelerator_modules"]
    )
    differing_dsp_firmware = differing_records(source["dsp_firmware"], target["dsp_firmware"])

    source_contract = all_present(source["camera_service"]["backend_contract"])
    target_contract = all_present(target["camera_service"]["backend_contract"])
    source_modes = all_present(source["camera_service"]["object_modes"])
    target_modes = all_present(target["camera_service"]["object_modes"])

    blockers = []
    if source["platform"]["device"] != target["platform"]["device"]:
        blockers.append("source and target use different Eagle2 device variants")
    if not source_contract or not source_modes:
        blockers.append("source firmware does not expose the expected object-recognition contract")
    if not target_contract or not target_modes:
        blockers.append("target camera-service lacks the object-recognition property/callback contract")
    if missing_target_dependencies:
        blockers.append("target userspace lacks dependencies required by the source ML runtime")
    if source["model_formats"] != target["model_formats"]:
        blockers.append("model filename formats differ; cross-load compatibility remains unverified")
    if differing_accelerator_modules:
        blockers.append("vision kernel modules differ between source and target")
    if differing_dsp_firmware:
        blockers.append("DSP firmware differs between source and target")
    if differing_common_dependencies:
        blockers.append("shared ML runtime libraries have different ABIs/builds")

    return {
        "same_android_sdk": source["platform"]["android_sdk"] == target["platform"]["android_sdk"],
        "same_abi": source["platform"]["abi"] == target["platform"]["abi"],
        "same_device_variant": source["platform"]["device"] == target["platform"]["device"],
        "source_backend_contract_complete": source_contract,
        "target_backend_contract_complete": target_contract,
        "source_modes_complete": source_modes,
        "target_modes_complete": target_modes,
        "missing_target_dependencies": missing_target_dependencies,
        "differing_common_dependencies": differing_common_dependencies,
        "differing_accelerator_modules": differing_accelerator_modules,
        "differing_dsp_firmware": differing_dsp_firmware,
        "direct_binary_transplant_ready": not blockers,
        "blockers": blockers,
    }


def build_report(
    source_system: Path,
    source_vendor: Path,
    target_system: Path,
    target_vendor: Path,
) -> dict[str, Any]:
    source = inspect_firmware(source_system, source_vendor)
    target = inspect_firmware(target_system, target_vendor)
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "X2D II object-recognition backend to first-generation X2D",
        "io_contract": {
            "input": "live-view frames consumed by the ML graph",
            "control": {
                "property": "camera.object_detection",
                "values": list(OBJECT_MODES),
                "related_property": "camera.arbitrary_tracking",
            },
            "output": "ObjectInfo lists, AF object-detection callbacks, and tracking target updates",
        },
        "source": source,
        "target": target,
        "compatibility": evaluate(source, target),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-system-root", type=Path, required=True)
    parser.add_argument("--source-vendor-root", type=Path, required=True)
    parser.add_argument("--target-system-root", type=Path, required=True)
    parser.add_argument("--target-vendor-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="write deterministic JSON to this path")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="return status 2 when direct binary transplantation is not safe",
    )
    args = parser.parse_args()

    report = build_report(
        args.source_system_root.resolve(strict=True),
        args.source_vendor_root.resolve(strict=True),
        args.target_system_root.resolve(strict=True),
        args.target_vendor_root.resolve(strict=True),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.require_ready and not report["compatibility"]["direct_binary_transplant_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
