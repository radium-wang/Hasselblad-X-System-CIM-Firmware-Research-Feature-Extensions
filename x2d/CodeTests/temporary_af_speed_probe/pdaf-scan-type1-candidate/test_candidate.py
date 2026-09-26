"""Offline tests for the PDAF Type1 scan candidate; never accesses USB."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_candidate as candidate
import evaluate_benchmark as benchmark


class CandidateTests(unittest.TestCase):
    def stock_fixture(self):
        data = bytearray(candidate.FUNCTION_END - candidate.FUNCTION_START)
        for site in candidate.PATCH_SITES:
            offset = site["context_address"] - candidate.FUNCTION_START
            data[offset : offset + len(site["context"])] = site["context"]
        return bytes(data)

    def test_patch_changes_only_immediate_byte_at_two_sites(self):
        original = self.stock_fixture()
        with mock.patch.object(candidate, "ORIGINAL_FUNCTION_SHA256", candidate.digest(original)), \
             mock.patch.object(candidate, "CANDIDATE_FUNCTION_SHA256", ""):
            expected = bytearray(original)
            for site in candidate.PATCH_SITES:
                offset = site["address"] - candidate.FUNCTION_START
                expected[offset : offset + 4] = candidate.CANDIDATE_INSTRUCTION
            with mock.patch.object(candidate, "CANDIDATE_FUNCTION_SHA256", candidate.digest(expected)):
                patched, records = candidate.patch_function(original)
        changes = [index for index, pair in enumerate(zip(original, patched)) if pair[0] != pair[1]]
        self.assertEqual(changes, [site["address"] - candidate.FUNCTION_START + 2
                                   for site in candidate.PATCH_SITES])
        self.assertEqual([record["candidateDisassembly"] for record in records],
                         ["mov w9, #1", "mov w9, #1"])

    def test_context_mismatch_is_rejected(self):
        original = bytearray(self.stock_fixture())
        original[candidate.PATCH_SITES[0]["context_address"] - candidate.FUNCTION_START] ^= 1
        with mock.patch.object(candidate, "ORIGINAL_FUNCTION_SHA256", candidate.digest(original)):
            with self.assertRaisesRegex(candidate.CandidateError, "control context mismatch"):
                candidate.patch_function(bytes(original))

    def test_benchmark_summary_and_gates(self):
        rows = []
        for trial in range(1, 21):
            rows.extend((
                {"variant": "stock", "direction": "near-to-far", "trial": trial,
                 "duration_ms": 500.0, "success": 1, "overshoot": 0},
                {"variant": "candidate", "direction": "near-to-far", "trial": trial,
                 "duration_ms": 400.0, "success": 1, "overshoot": 0},
            ))
        result = benchmark.summarize(rows)
        self.assertTrue(result["pass"])
        self.assertEqual(result["delta"]["medianImprovementPercent"], 20.0)

    def test_benchmark_csv_requires_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timings.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=sorted(benchmark.REQUIRED_COLUMNS))
                writer.writeheader()
                writer.writerow({"variant": "stock", "direction": "near-to-far", "trial": 1,
                                 "duration_ms": 500, "success": 1, "overshoot": 0})
            with self.assertRaisesRegex(benchmark.BenchmarkError, "both stock and candidate"):
                benchmark.summarize(benchmark.load_rows(path))


if __name__ == "__main__":
    unittest.main()
