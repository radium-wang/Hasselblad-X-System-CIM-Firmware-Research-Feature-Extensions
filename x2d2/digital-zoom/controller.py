"""Fail-closed lifecycle controller for the offline digital-crop planner.

A future camera adapter must implement :class:`CropWindowSink` and publish a
complete capability contract. Unknown capabilities are planning-only: this
controller will never pretend that a crop was applied.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from crop_geometry import (
    ZOOM_MAX,
    Sensor,
    Window,
    X2DII_100C,
    achievable_windows,
    at_least_index,
    describe,
    zoom_for_window,
)

MODES = frozenset({"shooting", "review", "menu", "playback"})
TARGET_MODEL = "X2D II 100C"
TARGET_FIRMWARE = "1.3.16.2"


@dataclass(frozen=True)
class CropCapability:
    """Coordinate and effect contract declared by a crop backend."""

    available: bool = False
    target_model: str = "unknown"
    coordinate_space: str = "unknown"
    x_alignment: int = 1
    y_alignment: int = 1
    width_alignment: int = 1
    height_alignment: int = 1
    affects_preview: bool = False
    affects_capture: bool = False
    affects_raw: bool = False
    reversible: bool = False
    firmware_version: str = "unknown"

    def __post_init__(self) -> None:
        for name in (
            "available",
            "affects_preview",
            "affects_capture",
            "affects_raw",
            "reversible",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        for name in ("x_alignment", "y_alignment", "width_alignment", "height_alignment"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.target_model, str) or not self.target_model.strip():
            raise ValueError("target_model must not be empty")
        if not isinstance(self.coordinate_space, str) or not self.coordinate_space.strip():
            raise ValueError("coordinate_space must not be empty")
        if not isinstance(self.firmware_version, str) or not self.firmware_version.strip():
            raise ValueError("firmware_version must not be empty")
        object.__setattr__(self, "target_model", self.target_model.strip())
        object.__setattr__(self, "coordinate_space", self.coordinate_space.strip())
        object.__setattr__(self, "firmware_version", self.firmware_version.strip())

    @property
    def alignment(self) -> int:
        return math.lcm(
            self.x_alignment,
            self.y_alignment,
            self.width_alignment,
            self.height_alignment,
        )

    @property
    def ready(self) -> bool:
        return (
            self.available
            and self.target_model.casefold() != "unknown"
            and self.coordinate_space.casefold() != "unknown"
            and self.affects_preview
            and self.affects_capture
            and self.reversible
            and self.firmware_version.casefold() != "unknown"
        )


class CropWindowSink:
    """Backend interface; no X2D II implementation is known in this repository."""

    capability = CropCapability()

    def apply(self, window: Window) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError


TEST_CAPABILITY = CropCapability(
    available=True,
    target_model=TARGET_MODEL,
    coordinate_space="synthetic-test-pixels",
    x_alignment=2,
    y_alignment=2,
    width_alignment=2,
    height_alignment=2,
    affects_preview=True,
    affects_capture=True,
    affects_raw=False,
    reversible=True,
    firmware_version=TARGET_FIRMWARE,
)


@dataclass
class RecordingSink(CropWindowSink):
    """Host-test sink. It is never selected implicitly by :class:`ZoomSession`."""

    capability: CropCapability = TEST_CAPABILITY
    applied: Window | None = None
    apply_calls: list[Window] = field(default_factory=list)
    release_calls: int = 0

    def apply(self, window: Window) -> None:
        self.applied = window
        self.apply_calls.append(window)

    def release(self) -> None:
        self.release_calls += 1
        self.applied = None


class ZoomSession:
    """Keep selection, visibility, and backend application as separate state."""

    def __init__(
        self,
        sensor: Sensor = X2DII_100C,
        sink: CropWindowSink | None = None,
        *,
        feature_enabled: bool = False,
        aspect: float | None = None,
    ) -> None:
        self.sensor = sensor
        self.sink = sink
        self.aspect = aspect
        self.mode = "shooting"
        self.feature_enabled = bool(feature_enabled)
        self.requested_zoom = 1.0
        self.faulted = False
        self.last_error: str | None = None
        self.closed = False
        self._backend_active = False
        self._release_pending = False
        self._applied_window: Window | None = None
        self._rebuild()
        self._sync_backend()

    @property
    def capability(self) -> CropCapability:
        if self.sink is None:
            return CropCapability()
        capability = getattr(self.sink, "capability", None)
        return capability if isinstance(capability, CropCapability) else CropCapability()

    @property
    def backend_ready(self) -> bool:
        return (
            self.sink is not None
            and self.capability.ready
            and self.capability.target_model == TARGET_MODEL
            and self.capability.firmware_version == TARGET_FIRMWARE
        )

    @property
    def alignment(self) -> int:
        backend_alignment = self.capability.alignment if self.backend_ready else 1
        return math.lcm(self.sensor.cfa_quad, backend_alignment)

    @property
    def visible(self) -> bool:
        return not self.closed and self.mode == "shooting" and self.feature_enabled

    @property
    def wants_crop(self) -> bool:
        return self.visible and self.index > 0 and not self.faulted

    @property
    def live(self) -> bool:
        return self.wants_crop and self._backend_active

    def _ensure_open(self) -> None:
        if self.closed:
            raise RuntimeError("zoom session is closed")

    def _rebuild(self) -> None:
        self.windows = achievable_windows(
            self.sensor,
            self.aspect,
            self.alignment,
            ZOOM_MAX,
        )
        index = at_least_index(self.windows, self.requested_zoom)
        self.index = max(0, index)

    def _current(self) -> Window:
        return self.windows[self.index]

    def _release_backend(self, *, force: bool = False) -> None:
        if self.sink is None:
            self._backend_active = False
            self._release_pending = False
            self._applied_window = None
            return
        if not self._backend_active and not self._release_pending and not force:
            return
        try:
            self.sink.release()
        except Exception as error:  # A release fault must remain visible to the caller.
            self.last_error = f"release failed: {error}"
            self.faulted = True
            self._release_pending = True
            return
        self._backend_active = False
        self._release_pending = False
        self._applied_window = None

    def _sync_backend(self) -> None:
        if not self.wants_crop or not self.backend_ready:
            self._release_backend()
            return
        window = self._current()
        if self._backend_active and self._applied_window == window:
            return
        try:
            assert self.sink is not None
            self.sink.apply(window)
        except Exception as error:
            self.last_error = f"apply failed: {error}"
            self.faulted = True
            # apply() may have changed state before reporting failure.
            self._release_pending = True
            self._release_backend(force=True)
            return
        self._backend_active = True
        self._release_pending = False
        self._applied_window = window
        self.last_error = None

    def set_aspect(self, aspect: float | None) -> None:
        self._ensure_open()
        windows = achievable_windows(
            self.sensor,
            aspect,
            self.alignment,
            ZOOM_MAX,
        )
        index = max(0, at_least_index(windows, self.requested_zoom))
        self.aspect = aspect
        self.windows = windows
        self.index = index
        self._sync_backend()

    def set_mode(self, mode: str) -> None:
        self._ensure_open()
        if mode not in MODES:
            raise ValueError(f"unsupported mode: {mode}")
        if self.mode == mode:
            if self._release_pending:
                self._sync_backend()
            return
        self.mode = mode
        self._sync_backend()

    def set_feature_enabled(self, enabled: bool) -> None:
        self._ensure_open()
        enabled = bool(enabled)
        if self.feature_enabled == enabled:
            if self._release_pending:
                self._sync_backend()
            return
        self.feature_enabled = enabled
        if not enabled:
            self.requested_zoom = 1.0
            self.index = 0
        self._sync_backend()

    def set_bar(self, on: bool) -> None:
        """Compatibility alias for the original candidate API."""

        self.set_feature_enabled(on)

    def request_zoom(self, zoom: float) -> None:
        self._ensure_open()
        if not self.visible:
            return
        if not math.isfinite(float(zoom)):
            raise ValueError("zoom must be finite")
        self.requested_zoom = min(max(float(zoom), 1.0), ZOOM_MAX)
        index = at_least_index(self.windows, self.requested_zoom)
        if index >= 0:
            self.index = index
        self._sync_backend()

    def step(self, steps: int) -> None:
        self._ensure_open()
        if isinstance(steps, bool) or not isinstance(steps, int):
            raise ValueError("steps must be an integer")
        if not self.visible:
            return
        self.index = min(max(self.index + steps, 0), len(self.windows) - 1)
        achieved = zoom_for_window(self.windows[0], self._current())
        self.requested_zoom = min(max(achieved, 1.0), ZOOM_MAX)
        self._sync_backend()

    def clear_fault(self) -> None:
        """Allow an explicit retry after the caller has inspected a backend fault."""

        self._ensure_open()
        if self._release_pending:
            self._release_backend(force=True)
            if self._release_pending:
                return
        self.faulted = False
        self.last_error = None
        self._sync_backend()

    def close(self) -> None:
        if self.closed:
            if self._release_pending:
                self._release_backend(force=True)
            return
        self._release_backend(force=self._release_pending)
        self.closed = True

    def __enter__(self) -> "ZoomSession":
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def readout(self) -> dict[str, object]:
        base = self.windows[0]
        current = self._current()
        geometry = describe(self.sensor, current, base)
        if self.faulted or self._release_pending:
            application_state = "faulted"
        elif self.closed:
            application_state = "closed"
        elif self.live:
            application_state = "applied"
        elif self.index == 0:
            application_state = "base"
        elif not self.backend_ready:
            application_state = "backend-unavailable"
        else:
            application_state = "released"
        return {
            "mode": self.mode,
            "feature_enabled": self.feature_enabled,
            "visible": self.visible,
            "requested_zoom": self.requested_zoom,
            "selected_window": asdict(current),
            "base_window": asdict(base),
            "applied_window": asdict(self._applied_window) if self._applied_window else None,
            "digital_zoom": geometry["digital_zoom"],
            "sensor_crop_factor": geometry["sensor_crop_factor"],
            "megapixels": geometry["megapixels"],
            "backend_ready": self.backend_ready,
            "application_state": application_state,
            "faulted": self.faulted,
            "release_pending": self._release_pending,
            "last_error": self.last_error,
            "capability": asdict(self.capability),
        }
