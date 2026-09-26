#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).with_name("factory_debug_ui.py")
SPEC = importlib.util.spec_from_file_location("factory_debug_ui", TOOL)
assert SPEC and SPEC.loader
debug_ui = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(debug_ui)


def status(**overrides):
    result = {
        "device": debug_ui.EXPECTED_DEVICE,
        "usb_config": "rndis,mass_storage,bulk,acm",
        "usb_state": "rndis,mass_storage,bulk,acm",
        "camera_gui_service": "running",
        "camera_gui_pid": "123",
        "camera_gui_context": debug_ui.EXPECTED_PROCESS_CONTEXT,
        "camera_gui_sha256": debug_ui.EXPECTED_STOCK_GUI_SHA256,
        "debug_mode": "false",
        "debug_options": "None",
        "osd_clock": "Off",
        "osd_clock_size": "Default",
        "sutest_gui": "0",
        "testmode": "0",
        "adb_in_usb_config": False,
        "adb_in_usb_state": False,
        "stock_gui_hash_matches": True,
        "gui_process_context_matches": True,
        "factory_unlocked_trigger_present": False,
    }
    result.update(overrides)
    return result


class FactoryDebugUiTests(unittest.TestCase):
    def test_restore_state_accepts_production_values(self):
        debug_ui.require_restore_state(status())

    def test_restore_state_rejects_adb_in_either_property(self):
        for key in ("adb_in_usb_config", "adb_in_usb_state"):
            with self.subTest(key=key):
                with self.assertRaises(debug_ui.DebugUiError):
                    debug_ui.require_restore_state(status(**{key: True}))

    def test_restore_state_rejects_debug_value(self):
        with self.assertRaises(debug_ui.DebugUiError):
            debug_ui.require_restore_state(status(debug_mode="true"))

    def test_target_guard_rejects_non_stock_gui(self):
        with self.assertRaises(debug_ui.DebugUiError):
            debug_ui.require_target(status(camera_gui_sha256="0"))

    def test_restart_requires_explicit_confirmation(self):
        with self.assertRaises(SystemExit):
            debug_ui.main(["restart-gui"])


if __name__ == "__main__":
    unittest.main()
