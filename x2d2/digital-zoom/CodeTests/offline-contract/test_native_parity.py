from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE_ROOT))

from crop_geometry import (  # noqa: E402
    X2DII_100C,
    aspect_base_window,
    is_aligned,
    native_aspect,
    window_for_zoom,
)


class DzSensor(ctypes.Structure):
    _fields_ = [
        ("width_px", ctypes.c_int),
        ("height_px", ctypes.c_int),
        ("width_mm", ctypes.c_double),
        ("height_mm", ctypes.c_double),
        ("cfa_quad", ctypes.c_int),
    ]


class DzWindow(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
    ]


@unittest.skipUnless(shutil.which("cc"), "host C compiler is unavailable")
class NativeParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        library = Path(cls.temporary.name) / "libdigital_zoom.so"
        source = MODULE_ROOT / "native" / "digital_zoom.c"
        subprocess.run(
            [
                shutil.which("cc") or "cc",
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-shared",
                "-fPIC",
                str(source),
                "-lm",
                "-o",
                str(library),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.library = ctypes.CDLL(str(library))
        cls.library.dz_window_for_zoom.argtypes = [
            ctypes.POINTER(DzSensor),
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_int,
            ctypes.POINTER(DzWindow),
        ]
        cls.library.dz_window_for_zoom.restype = ctypes.c_int
        cls.library.dz_aspect_base.argtypes = [
            ctypes.POINTER(DzSensor),
            ctypes.c_double,
            ctypes.c_int,
            ctypes.POINTER(DzWindow),
        ]
        cls.library.dz_aspect_base.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_native_matches_python_for_all_supported_aspects(self) -> None:
        sensor = DzSensor(
            X2DII_100C.width_px,
            X2DII_100C.height_px,
            X2DII_100C.width_mm,
            X2DII_100C.height_mm,
            X2DII_100C.cfa_quad,
        )
        for aspect in (native_aspect(X2DII_100C), 1.0, 3 / 2, 16 / 9, 65 / 24):
            for zoom in (1.0, 1.1, 1.25, 1.5, 1.75, 2.0):
                with self.subTest(aspect=aspect, zoom=zoom):
                    native = DzWindow()
                    status = self.library.dz_window_for_zoom(
                        ctypes.byref(sensor), aspect, zoom, 2, ctypes.byref(native)
                    )
                    self.assertEqual(status, 0)
                    python = window_for_zoom(X2DII_100C, aspect, zoom)
                    self.assertEqual(
                        (native.x, native.y, native.width, native.height),
                        (python.x, python.y, python.width, python.height),
                    )

    def test_native_rejects_out_of_range_zoom(self) -> None:
        sensor = DzSensor(11656, 8742, 43.8, 32.9, 2)
        output = DzWindow()
        for zoom in (0.0, 2.1):
            status = self.library.dz_window_for_zoom(
                ctypes.byref(sensor), 4 / 3, zoom, 2, ctypes.byref(output)
            )
            self.assertEqual(status, -1)

    def test_direct_base_api_combines_backend_and_cfa_alignment(self) -> None:
        sensor = DzSensor(11656, 8742, 43.8, 32.9, 2)
        for requested_alignment in (1, 3, 5, 7):
            with self.subTest(alignment=requested_alignment):
                native = DzWindow()
                status = self.library.dz_aspect_base(
                    ctypes.byref(sensor), 1.5, requested_alignment, ctypes.byref(native)
                )
                self.assertEqual(status, 0)
                python = aspect_base_window(X2DII_100C, 1.5, requested_alignment)
                self.assertEqual(
                    (native.x, native.y, native.width, native.height),
                    (python.x, python.y, python.width, python.height),
                )
                self.assertTrue(is_aligned(python, X2DII_100C.cfa_quad))
                self.assertTrue(is_aligned(python, requested_alignment))


if __name__ == "__main__":
    unittest.main()
