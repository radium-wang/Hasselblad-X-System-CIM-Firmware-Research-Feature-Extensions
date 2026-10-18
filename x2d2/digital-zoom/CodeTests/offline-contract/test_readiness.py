from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
CHECKER = MODULE_ROOT / "tools" / "check_readiness.py"
MANIFEST = MODULE_ROOT / "readiness-manifest.json"


class ReadinessGateTest(unittest.TestCase):
    def test_plan_is_valid_but_explicitly_not_installable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(CHECKER), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertFalse(result["installable"])
        self.assertFalse(result["declared_installable"])
        self.assertGreaterEqual(len(result["blockers"]), 8)
        self.assertTrue(result["deferred"]["crop_metadata"])
        self.assertTrue(result["deferred"]["gps"])

    def test_require_installable_fails_closed(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(CHECKER), "--require-installable"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("NOT INSTALLABLE", completed.stdout)
        self.assertIn("signature", completed.stdout)

    def test_declared_installable_cannot_override_missing_gates(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["distribution"]["installable"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--require-installable"],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("NOT INSTALLABLE", completed.stdout)

    def test_invalid_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{}", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(CHECKER), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("MANIFEST INVALID", completed.stderr)

    def test_wrong_firmware_or_platform_is_rejected(self) -> None:
        original = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for key, value in (("firmware", "1.3.16.1"), ("platform", "other")):
            with self.subTest(key=key):
                data = json.loads(json.dumps(original))
                data["target"][key] = value
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "manifest.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    completed = subprocess.run(
                        [sys.executable, str(CHECKER), str(path)],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                self.assertEqual(completed.returncode, 1)
                self.assertIn(f"target.{key}", completed.stderr)

    def test_raw_effect_status_is_typed_but_intentionally_nonblocking(self) -> None:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            valid = subprocess.run(
                [sys.executable, str(CHECKER), str(path), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(valid.stdout)
            self.assertFalse(report["raw_effect_verified"])
            self.assertFalse(report["raw_effect_required_for_installable"])

            data["backend"]["raw_effect_verified"] = "unknown"
            path.write_text(json.dumps(data), encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(CHECKER), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("backend.raw_effect_verified", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
