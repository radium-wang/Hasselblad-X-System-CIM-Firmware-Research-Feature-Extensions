from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULE_ROOT))

from controller import (  # noqa: E402
    CropCapability,
    CropWindowSink,
    RecordingSink,
    TEST_CAPABILITY,
    ZoomSession,
)


class FailingSink(CropWindowSink):
    capability = TEST_CAPABILITY

    def __init__(self) -> None:
        self.release_calls = 0

    def apply(self, window: object) -> None:
        raise RuntimeError("synthetic apply fault")

    def release(self) -> None:
        self.release_calls += 1


class UnknownSink(CropWindowSink):
    def __init__(self) -> None:
        self.calls = 0

    def apply(self, window: object) -> None:
        self.calls += 1

    def release(self) -> None:
        self.calls += 1


class ReleaseFailsOnceSink(RecordingSink):
    def release(self) -> None:
        self.release_calls += 1
        if self.release_calls == 1:
            raise RuntimeError("synthetic release fault")
        self.applied = None


class ControllerTest(unittest.TestCase):
    def test_capability_rejects_ambiguous_types_and_unknown_labels(self) -> None:
        with self.assertRaises(ValueError):
            CropCapability(available=1)  # type: ignore[arg-type]
        unknown = CropCapability(
            available=True,
            coordinate_space="  UNKNOWN ",
            affects_preview=True,
            affects_capture=True,
            reversible=True,
            firmware_version="  unknown ",
        )
        self.assertFalse(unknown.ready)

    def test_disabled_by_default_and_no_implicit_sink(self) -> None:
        session = ZoomSession()
        self.assertFalse(session.feature_enabled)
        self.assertFalse(session.backend_ready)
        self.assertEqual(session.readout()["application_state"], "base")

    def test_apply_review_restore_and_close_lifecycle(self) -> None:
        sink = RecordingSink()
        session = ZoomSession(sink=sink)
        session.set_feature_enabled(True)
        session.request_zoom(1.5)
        self.assertEqual(len(sink.apply_calls), 1)
        self.assertTrue(session.live)

        session.request_zoom(1.5)
        self.assertEqual(len(sink.apply_calls), 1, "identical apply must be deduplicated")
        session.set_mode("review")
        self.assertEqual(sink.release_calls, 1)
        session.set_mode("review")
        self.assertEqual(sink.release_calls, 1, "identical release must be deduplicated")
        session.set_mode("shooting")
        self.assertEqual(len(sink.apply_calls), 2)
        session.close()
        self.assertEqual(sink.release_calls, 2)
        session.close()
        self.assertEqual(sink.release_calls, 2)

    def test_review_retains_selection_and_aspect_change_retains_factor(self) -> None:
        sink = RecordingSink()
        session = ZoomSession(sink=sink, feature_enabled=True)
        session.request_zoom(1.5)
        session.set_mode("review")
        selected = session.readout()["selected_window"]
        session.set_mode("shooting")
        self.assertEqual(session.readout()["selected_window"], selected)
        session.set_aspect(16 / 9)
        result = session.readout()
        self.assertEqual(result["requested_zoom"], 1.5)
        self.assertGreaterEqual(result["digital_zoom"], 1.5)
        self.assertEqual(result["application_state"], "applied")

    def test_invalid_aspect_does_not_corrupt_active_selection(self) -> None:
        sink = RecordingSink()
        session = ZoomSession(sink=sink, feature_enabled=True)
        session.request_zoom(1.5)
        before = session.readout()
        with self.assertRaises(ValueError):
            session.set_aspect(0.0)
        after = session.readout()
        self.assertEqual(after["selected_window"], before["selected_window"])
        self.assertEqual(after["requested_zoom"], before["requested_zoom"])
        self.assertEqual(after["application_state"], "applied")

    def test_disabling_releases_and_resets_to_base(self) -> None:
        sink = RecordingSink()
        session = ZoomSession(sink=sink, feature_enabled=True)
        session.request_zoom(2.0)
        session.set_feature_enabled(False)
        result = session.readout()
        self.assertEqual(result["digital_zoom"], 1.0)
        self.assertEqual(result["requested_zoom"], 1.0)
        self.assertIsNone(sink.applied)

    def test_step_at_cap_preserves_two_x_target_across_aspects(self) -> None:
        session = ZoomSession(sink=RecordingSink(), feature_enabled=True, aspect=16 / 9)
        session.step(10000)
        self.assertEqual(session.readout()["requested_zoom"], 2.0)
        session.set_aspect(65 / 24)
        result = session.readout()
        self.assertEqual(result["requested_zoom"], 2.0)
        self.assertGreaterEqual(result["digital_zoom"], 2.0)

    def test_missing_or_unknown_capability_never_claims_application(self) -> None:
        session = ZoomSession(feature_enabled=True)
        session.request_zoom(1.5)
        self.assertEqual(session.readout()["application_state"], "backend-unavailable")

        sink = UnknownSink()
        unknown = ZoomSession(sink=sink, feature_enabled=True)
        unknown.request_zoom(1.5)
        self.assertEqual(sink.calls, 0)
        self.assertFalse(unknown.readout()["backend_ready"])

    def test_wrong_model_or_firmware_sink_is_never_called(self) -> None:
        for capability in (
            replace(TEST_CAPABILITY, target_model="X2D 100C"),
            replace(TEST_CAPABILITY, firmware_version="1.3.16.1"),
        ):
            with self.subTest(capability=capability):
                sink = RecordingSink(capability=capability)
                session = ZoomSession(sink=sink, feature_enabled=True)
                session.request_zoom(1.5)
                self.assertFalse(session.backend_ready)
                self.assertEqual(sink.apply_calls, [])
                self.assertEqual(session.readout()["application_state"], "backend-unavailable")

    def test_apply_failure_faults_and_attempts_release(self) -> None:
        sink = FailingSink()
        session = ZoomSession(sink=sink, feature_enabled=True)
        session.request_zoom(1.5)
        result = session.readout()
        self.assertTrue(result["faulted"])
        self.assertEqual(result["application_state"], "faulted")
        self.assertIn("synthetic apply fault", result["last_error"])
        self.assertEqual(sink.release_calls, 1)
        self.assertIsNone(result["applied_window"])

    def test_failed_release_remains_pending_and_close_retries(self) -> None:
        sink = ReleaseFailsOnceSink()
        session = ZoomSession(sink=sink, feature_enabled=True)
        session.request_zoom(1.5)
        session.set_mode("review")
        result = session.readout()
        self.assertTrue(result["faulted"])
        self.assertTrue(result["release_pending"])
        self.assertIn("synthetic release fault", result["last_error"])
        session.close()
        self.assertEqual(sink.release_calls, 2)
        self.assertFalse(session.readout()["release_pending"])

    def test_readout_is_json_serialisable(self) -> None:
        session = ZoomSession(sink=RecordingSink(), feature_enabled=True)
        session.request_zoom(1.25)
        json.dumps(session.readout(), sort_keys=True)

    def test_menu_and_playback_release_crop(self) -> None:
        for mode in ("menu", "playback"):
            with self.subTest(mode=mode):
                sink = RecordingSink()
                session = ZoomSession(sink=sink, feature_enabled=True)
                session.request_zoom(1.5)
                session.set_mode(mode)
                self.assertFalse(session.live)
                self.assertIsNone(sink.applied)


if __name__ == "__main__":
    unittest.main()
