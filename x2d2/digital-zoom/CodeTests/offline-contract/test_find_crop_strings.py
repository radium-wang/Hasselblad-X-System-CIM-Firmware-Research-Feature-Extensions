"""Offline contracts for the bounded, read-only crop-string scanner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
SCANNER = MODULE_ROOT / "find_crop_strings.py"
sys.path.insert(0, str(MODULE_ROOT))

from find_crop_strings import scan  # noqa: E402


class FindCropStringsTest(unittest.TestCase):
    def test_hits_crop_name_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ui.txt").write_bytes(b"prefix setCropRect(x,y,w,h) suffix\x00other")
            (root / "noise.txt").write_bytes(b"battery and shutter only")
            hits = scan(root)
        self.assertEqual(len(hits), 1)
        self.assertIn("setCropRect", hits[0][1])

    def test_short_xpan_symbol_is_not_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "crop.tbl"
            fixture.write_bytes(b"\x00xpan\x00")
            hits = scan(Path(directory))
        self.assertEqual(hits, [("crop.tbl", "xpan")])

    def test_scans_shared_static_and_object_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {
                root / "libcamera.so": b"\x7fELF\x00shared_setCropWindow\x00",
                root / "libcamera.a": b"!<arch>\n\x00static_setCropArea\x00",
                root / "camera.o": b"\x7fELF\x00object_setCropRect\x00",
            }
            for path, payload in fixtures.items():
                path.write_bytes(payload)
            hits = scan(Path(directory))
        self.assertEqual({path for path, _ in hits}, {path.name for path in fixtures})
        self.assertTrue(any("setCropWindow" in text for _, text in hits))

    def test_match_may_cross_a_chunk_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_chunk = b"\x00prefix-setCr"
            fixture = Path(directory) / "camera.bin"
            fixture.write_bytes(first_chunk + b"opRect-suffix\x00")
            hits = scan(Path(directory), chunk_size=len(first_chunk))
        self.assertEqual(len(hits), 1)
        self.assertIn("setCropRect", hits[0][1])

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links are unavailable")
    def test_does_not_follow_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            extract = base / "extract"
            extract.mkdir()
            target = base / "outside.so"
            target.write_bytes(b"outside_setCropRect_secret\x00")
            try:
                (extract / "linked.so").symlink_to(target)
            except OSError as error:
                self.skipTest(f"cannot create a symbolic link: {error}")
            hits = scan(extract)
        self.assertEqual(hits, [])

    def test_json_cli_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "libcamera.so"
            fixture.write_bytes(b"\x00camera_setCropRect_ready\x00")
            completed = subprocess.run(
                [sys.executable, str(SCANNER), "--json", directory],
                check=True,
                capture_output=True,
                text=True,
            )
        payload = json.loads(completed.stdout)
        self.assertEqual(
            payload,
            [{"path": fixture.name, "text": "camera_setCropRect_ready"}],
        )

    def test_paths_are_relative_to_avoid_leaking_extract_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "vendor" / "lib64"
            nested.mkdir(parents=True)
            (nested / "libcamera.so").write_bytes(b"\x00camera_setCropRect_ready\x00")
            hits = scan(root)
        self.assertEqual(hits[0][0], "vendor/lib64/libcamera.so")
        self.assertNotIn(directory, hits[0][0])

    def test_limit_is_enforced_and_must_be_positive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.so").write_bytes(b"\x00first_setCropRect\x00")
            (root / "b.o").write_bytes(b"\x00second_setCropRect\x00")
            self.assertEqual(len(scan(root, limit=1)), 1)
            with self.assertRaisesRegex(ValueError, "positive integer"):
                scan(root, limit=0)
            with self.assertRaisesRegex(ValueError, "positive integer"):
                scan(root, limit=-1)
            completed = subprocess.run(
                [sys.executable, str(SCANNER), "--limit", "0", directory],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("positive integer", completed.stderr)


if __name__ == "__main__":
    unittest.main()
