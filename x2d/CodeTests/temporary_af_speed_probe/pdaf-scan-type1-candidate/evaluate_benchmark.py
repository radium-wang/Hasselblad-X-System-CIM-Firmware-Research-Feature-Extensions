#!/usr/bin/env python3
"""Evaluate paired AF-S timing CSVs without accessing a camera."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = {"variant", "direction", "trial", "duration_ms", "success", "overshoot"}
VARIANTS = {"stock", "candidate"}


class BenchmarkError(RuntimeError):
    pass


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise BenchmarkError("cannot calculate a percentile of an empty sample")
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != REQUIRED_COLUMNS:
            raise BenchmarkError("CSV columns must be exactly: " + ",".join(sorted(REQUIRED_COLUMNS)))
        rows = []
        seen = set()
        for line_number, row in enumerate(reader, 2):
            if row["variant"] not in VARIANTS:
                raise BenchmarkError(f"line {line_number}: variant must be stock or candidate")
            if not row["direction"].strip():
                raise BenchmarkError(f"line {line_number}: direction is empty")
            try:
                trial = int(row["trial"])
                duration = float(row["duration_ms"])
                success = int(row["success"])
                overshoot = int(row["overshoot"])
            except ValueError as error:
                raise BenchmarkError(f"line {line_number}: invalid numeric field") from error
            if trial < 1 or not math.isfinite(duration) or duration <= 0:
                raise BenchmarkError(f"line {line_number}: trial and duration must be positive")
            if success not in (0, 1) or overshoot not in (0, 1):
                raise BenchmarkError(f"line {line_number}: success and overshoot must be 0 or 1")
            key = (row["variant"], row["direction"], trial)
            if key in seen:
                raise BenchmarkError(f"line {line_number}: duplicate variant/direction/trial")
            seen.add(key)
            rows.append({"variant": row["variant"], "direction": row["direction"],
                         "trial": trial, "duration_ms": duration,
                         "success": success, "overshoot": overshoot})
    return rows


def summarize(rows: list[dict]) -> dict:
    by_variant = defaultdict(list)
    pairs = defaultdict(set)
    for row in rows:
        by_variant[row["variant"]].append(row)
        pairs[(row["direction"], row["trial"])].add(row["variant"])
    if set(by_variant) != VARIANTS:
        raise BenchmarkError("both stock and candidate samples are required")
    incomplete = sorted(key for key, variants in pairs.items() if variants != VARIANTS)
    if incomplete:
        raise BenchmarkError(f"unpaired direction/trial samples: {incomplete[:5]!r}")
    counts = {name: len(items) for name, items in by_variant.items()}
    if counts["stock"] != counts["candidate"]:
        raise BenchmarkError("stock and candidate sample counts differ")

    result = {}
    for variant, items in sorted(by_variant.items()):
        successful = [row["duration_ms"] for row in items if row["success"]]
        if not successful:
            raise BenchmarkError(f"{variant} has no successful samples")
        result[variant] = {
            "samples": len(items),
            "medianSuccessfulMs": statistics.median(successful),
            "p95SuccessfulMs": percentile(successful, 0.95),
            "successRate": sum(row["success"] for row in items) / len(items),
            "overshootRate": sum(row["overshoot"] for row in items) / len(items),
        }

    stock = result["stock"]
    candidate = result["candidate"]
    delta = {
        "medianImprovementPercent":
            (stock["medianSuccessfulMs"] - candidate["medianSuccessfulMs"])
            / stock["medianSuccessfulMs"] * 100.0,
        "p95ImprovementPercent":
            (stock["p95SuccessfulMs"] - candidate["p95SuccessfulMs"])
            / stock["p95SuccessfulMs"] * 100.0,
        "successRateDeltaPoints": (candidate["successRate"] - stock["successRate"]) * 100.0,
        "overshootRateDeltaPoints": (candidate["overshootRate"] - stock["overshootRate"]) * 100.0,
    }
    # Conservative experiment gate, not a safety certification.
    gates = {
        "atLeast20PairedSamples": counts["stock"] >= 20,
        "medianAtLeast10PercentFaster": delta["medianImprovementPercent"] >= 10.0,
        "p95NotSlower": delta["p95ImprovementPercent"] >= 0.0,
        "successRateNotDownMoreThan1Point": delta["successRateDeltaPoints"] >= -1.0,
        "overshootRateNotHigher": delta["overshootRateDeltaPoints"] <= 0.0,
    }
    return {"stock": stock, "candidate": candidate, "delta": delta,
            "gates": gates, "pass": all(gates.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(load_rows(args.csv))
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    try:
        main()
    except (BenchmarkError, FileNotFoundError) as error:
        raise SystemExit(f"error: {error}") from error
