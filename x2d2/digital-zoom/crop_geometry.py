"""Pure geometry for an aspect-preserving X2D II digital crop.

The selected aspect ratio defines the 1.0x base window. Digital zoom is
measured from that base, not from the full sensor. This distinction matters:
16:9 at 1.0x is already shorter than the native sensor but is not digital
zoom.

This module is deliberately camera-independent. It neither identifies nor
calls a preview, capture, RAW, or sensor-window API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

REF_35_W_MM = 36.0
REF_35_H_MM = 24.0
ZOOM_MAX = 2.0


@dataclass(frozen=True)
class Sensor:
    width_px: int = 11656
    height_px: int = 8742
    width_mm: float = 43.8
    height_mm: float = 32.9
    cfa_quad: int = 2


# Public 100 MP dimensions. The coordinate space and alignment required by an
# X2D II runtime backend remain unverified for firmware 1.3.16.2.
X2DII_100C = Sensor()


@dataclass(frozen=True)
class Window:
    x: int
    y: int
    width: int
    height: int


def _hyp(a: float, b: float) -> float:
    return math.hypot(a, b)


def _require_finite_positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _validate_alignment(alignment: int) -> int:
    if isinstance(alignment, bool) or not isinstance(alignment, int) or alignment <= 0:
        raise ValueError("alignment must be a positive integer")
    return alignment


def _validate_sensor(sensor: Sensor) -> None:
    if not isinstance(sensor.width_px, int) or sensor.width_px <= 0:
        raise ValueError("sensor width_px must be a positive integer")
    if not isinstance(sensor.height_px, int) or sensor.height_px <= 0:
        raise ValueError("sensor height_px must be a positive integer")
    _require_finite_positive(sensor.width_mm, "sensor width_mm")
    _require_finite_positive(sensor.height_mm, "sensor height_mm")
    _validate_alignment(sensor.cfa_quad)


def _align_down(value: float, alignment: int) -> int:
    alignment = _validate_alignment(alignment)
    return int(math.floor(value / alignment) * alignment)


def _effective_alignment(sensor: Sensor, alignment: int | None) -> int:
    requested = sensor.cfa_quad if alignment is None else _validate_alignment(alignment)
    return math.lcm(sensor.cfa_quad, requested)


def sensor_diag_px(sensor: Sensor) -> float:
    _validate_sensor(sensor)
    return _hyp(sensor.width_px, sensor.height_px)


def sensor_diag_mm(sensor: Sensor) -> float:
    _validate_sensor(sensor)
    return _hyp(sensor.width_mm, sensor.height_mm)


def native_aspect(sensor: Sensor) -> float:
    _validate_sensor(sensor)
    return sensor.width_px / sensor.height_px


def pixel_pitch_um(sensor: Sensor) -> tuple[float, float]:
    """Return independent horizontal and vertical pitches from public figures."""

    _validate_sensor(sensor)
    return (
        1000.0 * sensor.width_mm / sensor.width_px,
        1000.0 * sensor.height_mm / sensor.height_px,
    )


def pitch_um(sensor: Sensor) -> float:
    """Backward-compatible horizontal pitch helper."""

    return pixel_pitch_um(sensor)[0]


def _window_diag(window: Window) -> float:
    return _hyp(window.width, window.height)


def is_aligned(window: Window, alignment: int) -> bool:
    alignment = _validate_alignment(alignment)
    return all(
        value % alignment == 0
        for value in (window.x, window.y, window.width, window.height)
    )


def _validate_window(sensor: Sensor, window: Window) -> None:
    if window.width <= 0 or window.height <= 0:
        raise ValueError("window dimensions must be positive")
    if window.x < 0 or window.y < 0:
        raise ValueError("window origin must be non-negative")
    if window.x + window.width > sensor.width_px:
        raise ValueError("window exceeds sensor width")
    if window.y + window.height > sensor.height_px:
        raise ValueError("window exceeds sensor height")


def centre_window(
    sensor: Sensor,
    width: int,
    height: int,
    alignment: int | None = None,
) -> Window | None:
    """Return an aligned, nearly symmetric window, or ``None`` if it cannot fit."""

    _validate_sensor(sensor)
    alignment = _effective_alignment(sensor, alignment)
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError("width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ValueError("height must be a positive integer")
    if width % alignment or height % alignment:
        raise ValueError("window dimensions must match alignment")
    if width > sensor.width_px or height > sensor.height_px:
        return None
    x = _align_down((sensor.width_px - width) / 2, alignment)
    y = _align_down((sensor.height_px - height) / 2, alignment)
    window = Window(x, y, width, height)
    _validate_window(sensor, window)
    return window


def aspect_base_window(
    sensor: Sensor,
    aspect: float | None = None,
    alignment: int | None = None,
) -> Window:
    """Largest centred aligned window for ``aspect``; this is digital 1.0x."""

    _validate_sensor(sensor)
    alignment = _effective_alignment(sensor, alignment)
    target = native_aspect(sensor) if aspect is None else _require_finite_positive(aspect, "aspect")

    if target >= native_aspect(sensor):
        width = _align_down(sensor.width_px, alignment)
        height = _align_down(width / target, alignment)
    else:
        height = _align_down(sensor.height_px, alignment)
        width = _align_down(height * target, alignment)
    if width < alignment or height < alignment:
        raise ValueError("aspect does not produce a non-empty aligned window")
    window = centre_window(sensor, width, height, alignment)
    if window is None:  # Defensive: the width/height calculation must fit.
        raise ValueError("aspect base window does not fit the sensor")
    return window


def zoom_for_window(base: Window, window: Window) -> float:
    """Linear digital zoom relative to an aspect base window."""

    if base.width <= 0 or base.height <= 0 or window.width <= 0 or window.height <= 0:
        raise ValueError("base and window dimensions must be positive")
    return _window_diag(base) / _window_diag(window)


def achievable_windows(
    sensor: Sensor,
    aspect: float | None = None,
    alignment: int | None = None,
    zoom_max: float = ZOOM_MAX,
) -> list[Window]:
    """Enumerate nested aspect windows through the first one reaching ``zoom_max``."""

    _validate_sensor(sensor)
    alignment = _effective_alignment(sensor, alignment)
    zoom_max = _require_finite_positive(zoom_max, "zoom_max")
    if zoom_max < 1.0:
        raise ValueError("zoom_max must be at least 1.0")
    target = native_aspect(sensor) if aspect is None else _require_finite_positive(aspect, "aspect")
    base = aspect_base_window(sensor, target, alignment)
    out: list[Window] = [base]
    seen: set[tuple[int, int]] = {(base.width, base.height)}
    if zoom_max <= 1.0:
        return out

    height = base.height - alignment
    while height >= alignment:
        width = _align_down(height * target, alignment)
        if width > base.width:
            width = _align_down(base.width, alignment)
            height = _align_down(width / target, alignment)
        if width < alignment or height < alignment:
            break
        dimensions = (width, height)
        if dimensions not in seen:
            window = centre_window(sensor, width, height, alignment)
            if window is not None:
                seen.add(dimensions)
                out.append(window)
                if zoom_for_window(base, window) >= zoom_max - 1e-12:
                    break
        height -= alignment

    if not out:
        raise ValueError("no aligned windows are achievable")
    if zoom_for_window(base, out[-1]) < zoom_max - 1e-12:
        raise ValueError("zoom_max cannot be reached with this aspect and alignment")
    return out


def at_least_index(windows: list[Window], zoom: float) -> int:
    """Index of first window reaching ``zoom`` relative to ``windows[0]``."""

    if not windows:
        return -1
    zoom = _require_finite_positive(zoom, "zoom")
    base = windows[0]
    for index, window in enumerate(windows):
        if zoom_for_window(base, window) >= zoom - 1e-12:
            return index
    return len(windows) - 1


def window_for_zoom(
    sensor: Sensor,
    aspect: float | None,
    zoom: float,
    alignment: int | None = None,
    zoom_max: float = ZOOM_MAX,
) -> Window:
    """Return the first aligned window that does not undershoot a requested zoom."""

    zoom = _require_finite_positive(zoom, "zoom")
    zoom_max = _require_finite_positive(zoom_max, "zoom_max")
    if zoom < 1.0 or zoom > zoom_max:
        raise ValueError(f"zoom must be between 1.0 and {zoom_max}")
    # A valid lower request must not depend on whether this sensor/aspect can
    # also reach the configured upper cap.
    windows = achievable_windows(sensor, aspect, alignment, zoom)
    return windows[at_least_index(windows, zoom)]


def physical_size_mm(sensor: Sensor, window: Window) -> tuple[float, float]:
    _validate_sensor(sensor)
    _validate_window(sensor, window)
    pitch_x_um, pitch_y_um = pixel_pitch_um(sensor)
    return window.width * pitch_x_um / 1000.0, window.height * pitch_y_um / 1000.0


def describe(sensor: Sensor, window: Window, base: Window | None = None) -> dict[str, object]:
    """Describe a window without claiming a camera backend can apply it."""

    _validate_sensor(sensor)
    _validate_window(sensor, window)
    base = base or aspect_base_window(sensor)
    _validate_window(sensor, base)
    crop_width_mm, crop_height_mm = physical_size_mm(sensor, window)
    crop_diagonal_mm = _hyp(crop_width_mm, crop_height_mm)
    digital_zoom = zoom_for_window(base, window)
    sensor_crop_factor = sensor_diag_px(sensor) / _window_diag(window)
    return {
        "window": window,
        "base_window": base,
        "digital_zoom": digital_zoom,
        "achieved_zoom": digital_zoom,
        "sensor_crop_factor": sensor_crop_factor,
        "megapixels": window.width * window.height / 1e6,
        "crop_width_mm": crop_width_mm,
        "crop_height_mm": crop_height_mm,
        "crop_diagonal_mm": crop_diagonal_mm,
        "equivalent_factor_35mm": _hyp(REF_35_W_MM, REF_35_H_MM) / crop_diagonal_mm,
        "cfa_aligned": is_aligned(window, sensor.cfa_quad),
    }


def full_frame_zoom(sensor: Sensor, aspect: float | None = None) -> float:
    """Factor at which the selected aspect base reaches a 35 mm diagonal."""

    base = aspect_base_window(sensor, aspect)
    width_mm, height_mm = physical_size_mm(sensor, base)
    return _hyp(width_mm, height_mm) / _hyp(REF_35_W_MM, REF_35_H_MM)


def stops(sensor: Sensor, aspect: float | None = None) -> list[tuple[str, float]]:
    """Suggested UI stops; ``FF eq.`` is total diagonal equivalence."""

    ff_zoom = min(max(full_frame_zoom(sensor, aspect), 1.0), ZOOM_MAX)
    return [
        ("1.0", 1.0),
        ("FF eq.", ff_zoom),
        ("1.5", 1.5),
        ("2.0", ZOOM_MAX),
    ]
