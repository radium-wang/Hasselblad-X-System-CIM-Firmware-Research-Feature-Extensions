from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE_ROOT))

from crop_geometry import (  # noqa: E402
    Sensor,
    X2DII_100C,
    achievable_windows,
    aspect_base_window,
    describe,
    native_aspect,
    physical_size_mm,
    window_for_zoom,
    zoom_for_window,
)


class GeometryTest(unittest.TestCase):
    ASPECTS = (None, 1.0, 3 / 2, 16 / 9, 65 / 24)

    def test_every_aspect_reaches_two_x_from_its_own_base(self) -> None:
        sensor = X2DII_100C
        for aspect in self.ASPECTS:
            with self.subTest(aspect=aspect):
                base = aspect_base_window(sensor, aspect)
                windows = achievable_windows(sensor, aspect)
                self.assertEqual(windows[0], base)
                self.assertAlmostEqual(zoom_for_window(base, base), 1.0)
                top_zoom = zoom_for_window(base, windows[-1])
                self.assertGreaterEqual(top_zoom, 2.0)
                self.assertLess(top_zoom - 2.0, 0.002)
                self.assertLess(windows[-1].width, base.width)
                self.assertLess(windows[-1].height, base.height)
                self.assertTrue(describe(sensor, windows[-1], base)["cfa_aligned"])

    def test_base_keeps_largest_sensor_side(self) -> None:
        sensor = X2DII_100C
        native = native_aspect(sensor)
        for aspect in (1.0, 3 / 2, 16 / 9, 65 / 24):
            base = aspect_base_window(sensor, aspect)
            if aspect >= native:
                self.assertEqual(base.width, sensor.width_px)
            else:
                self.assertEqual(base.height, sensor.height_px)

    def test_windows_are_nested_and_monotonic(self) -> None:
        for aspect in self.ASPECTS:
            windows = achievable_windows(X2DII_100C, aspect)
            base = windows[0]
            prior_zoom = 0.0
            for previous, current in zip(windows, windows[1:]):
                self.assertLessEqual(current.width, previous.width)
                self.assertLess(current.height, previous.height)
                self.assertGreaterEqual(current.x, previous.x)
                self.assertGreaterEqual(current.y, previous.y)
                current_zoom = zoom_for_window(base, current)
                self.assertGreater(current_zoom, prior_zoom)
                prior_zoom = current_zoom

    def test_named_requests_never_undershoot(self) -> None:
        for aspect in self.ASPECTS:
            base = aspect_base_window(X2DII_100C, aspect)
            for zoom in (1.0, 1.1, 1.25, 1.5, 1.75, 2.0):
                window = window_for_zoom(X2DII_100C, aspect, zoom)
                self.assertGreaterEqual(zoom_for_window(base, window) + 1e-12, zoom)

    def test_describe_separates_digital_zoom_and_total_sensor_crop(self) -> None:
        base = aspect_base_window(X2DII_100C, 16 / 9)
        result = describe(X2DII_100C, base, base)
        self.assertEqual(result["digital_zoom"], 1.0)
        self.assertGreater(result["sensor_crop_factor"], 1.0)

    def test_physical_size_uses_independent_axis_pitch(self) -> None:
        sensor = Sensor(width_px=100, height_px=100, width_mm=40.0, height_mm=20.0)
        window = window_for_zoom(sensor, 1.0, 2.0)
        width_mm, height_mm = physical_size_mm(sensor, window)
        self.assertAlmostEqual(width_mm, 20.0)
        self.assertAlmostEqual(height_mm, 10.0)

    def test_invalid_inputs_fail_closed(self) -> None:
        invalid = (0.0, -1.0, math.nan, math.inf, -math.inf)
        for aspect in invalid:
            with self.subTest(aspect=aspect):
                with self.assertRaises(ValueError):
                    aspect_base_window(X2DII_100C, aspect)
        for zoom in invalid:
            with self.subTest(zoom=zoom):
                with self.assertRaises(ValueError):
                    window_for_zoom(X2DII_100C, None, zoom)
        for alignment in (0, -2, 1.5, True):
            with self.subTest(alignment=alignment):
                with self.assertRaises(ValueError):
                    achievable_windows(X2DII_100C, None, alignment)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
