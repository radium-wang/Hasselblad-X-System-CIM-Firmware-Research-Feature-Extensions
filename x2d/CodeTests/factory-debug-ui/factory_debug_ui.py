#!/usr/bin/env python3
"""Inspect and, when explicitly requested, restart the stock X2D GUI.

The research finding is that the stock GUI chooses its unlocked maintenance
branch when the current USB configuration contains ``adb`` and the GUI is
started again.  This tool deliberately assumes that an already-authorized ADB
device exists; it does not enable ADB, open a factory shell, change properties,
remount /system, upload files, or run arbitrary shell text.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time


EXPECTED_DEVICE = "eagle2_ec1706_native"
EXPECTED_STOCK_GUI_SHA256 = (
    "16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0"
)
EXPECTED_PROCESS_CONTEXT = "u:r:hbl_camera_service:s0"
EXPECTED_GUI_PATH = "/system/bin/camera-gui"
REQUIRED_RESTORE_VALUES = {
    "debug_mode": "false",
    "debug_options": "None",
    "osd_clock": "Off",
    "sutest_gui": "0",
    "testmode": "0",
}


class DebugUiError(RuntimeError):
    """A bounded ADB inspection or GUI lifecycle check failed."""


class Adb:
    """Run only fixed, non-interactive ADB operations."""

    def __init__(self, adb_path: str = "adb", serial: str | None = None, timeout: float = 8.0):
        self.adb_path = adb_path
        self.serial = serial
        self.timeout = timeout

    def _base(self) -> list[str]:
        command = [self.adb_path]
        if self.serial:
            command.extend(["-s", self.serial])
        return command

    def run(self, *arguments: str) -> str:
        command = self._base() + list(arguments)
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DebugUiError(f"ADB command failed: {error}") from error
        if result.returncode:
            raise DebugUiError(
                f"ADB command returned {result.returncode}: {' '.join(command)}\n"
                + result.stdout.rstrip()
            )
        return result.stdout.strip()

    def shell(self, *arguments: str) -> str:
        return self.run("shell", *arguments)

    def fixed_shell(self, command: str) -> str:
        """Run a constant shell expression; callers cannot supply shell text."""
        return self.run("shell", "sh", "-c", command)

    def wait_for_state(self, expected: str, timeout: float = 12.0) -> str:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            last = self.shell("getprop", "init.svc.camera-gui")
            if last == expected:
                return last
            time.sleep(0.25)
        raise DebugUiError(
            f"camera-gui did not reach {expected!r}; last state was {last!r}"
        )


def prop(adb: Adb, name: str) -> str:
    return adb.shell("getprop", name).strip()


def read_status(adb: Adb) -> dict[str, str | bool]:
    """Read the fixed state surface used by the debug-UI finding."""
    pid = adb.shell("pidof", "camera-gui")
    process_context = ""
    if pid:
        process_context = adb.fixed_shell(
            "p=$(pidof camera-gui); cat /proc/$p/attr/current 2>/dev/null"
        )
    status: dict[str, str | bool] = {
        "device": prop(adb, "ro.product.device"),
        "usb_config": prop(adb, "sys.usb.config"),
        "usb_state": prop(adb, "sys.usb.state"),
        "camera_gui_service": prop(adb, "init.svc.camera-gui"),
        "camera_gui_pid": pid,
        "camera_gui_context": process_context,
        "camera_gui_sha256": adb.shell("sha256sum", EXPECTED_GUI_PATH).split()[0],
        "debug_mode": adb.fixed_shell(
            "/system/bin/odindb-send --print-cmdline -s system -p debug_mode 2>/dev/null"
        ),
        "debug_options": adb.fixed_shell(
            "/system/bin/odindb-send --print-cmdline -s system -p debug_options 2>/dev/null"
        ),
        "osd_clock": adb.fixed_shell(
            "/system/bin/odindb-send --print-cmdline -s gui -p osd_clock 2>/dev/null"
        ),
        "osd_clock_size": adb.fixed_shell(
            "/system/bin/odindb-send --print-cmdline -s gui -p osd_clock_size 2>/dev/null"
        ),
        "sutest_gui": prop(adb, "hbl.sutest_gui"),
        "testmode": prop(adb, "persist.hbl.testmode"),
    }
    status["adb_in_usb_config"] = "adb" in str(status["usb_config"]).split(",")
    status["adb_in_usb_state"] = "adb" in str(status["usb_state"]).split(",")
    status["stock_gui_hash_matches"] = (
        status["camera_gui_sha256"] == EXPECTED_STOCK_GUI_SHA256
    )
    status["gui_process_context_matches"] = EXPECTED_PROCESS_CONTEXT in str(
        status["camera_gui_context"]
    )
    status["factory_unlocked_trigger_present"] = bool(
        status["adb_in_usb_config"]
        and status["camera_gui_service"] == "running"
    )
    return status


def require_target(status: dict[str, str | bool]) -> None:
    if status["device"] != EXPECTED_DEVICE:
        raise DebugUiError(
            f"unexpected device {status['device']!r}; expected {EXPECTED_DEVICE!r}"
        )
    if status["camera_gui_sha256"] != EXPECTED_STOCK_GUI_SHA256:
        raise DebugUiError("camera-gui is not the exact stock 4.2.0 executable")
    if not status["gui_process_context_matches"]:
        raise DebugUiError("camera-gui is not running in the expected SELinux domain")


def require_restore_state(status: dict[str, str | bool]) -> None:
    if status["adb_in_usb_config"] or status["adb_in_usb_state"]:
        raise DebugUiError("USB configuration still contains adb")
    for name, expected in REQUIRED_RESTORE_VALUES.items():
        actual = str(status[name]).strip()
        if actual.lower() != expected.lower():
            raise DebugUiError(f"{name} is {actual!r}; expected {expected!r}")


def restart_stock_gui(adb: Adb) -> dict[str, str | bool]:
    before = read_status(adb)
    require_target(before)
    if not before["adb_in_usb_config"]:
        raise DebugUiError(
            "sys.usb.config does not contain adb; the unlocked stock branch "
            "cannot be tested from this ADB-only tool"
        )
    adb.shell("setprop", "ctl.stop", "camera-gui")
    adb.wait_for_state("stopped")
    adb.shell("setprop", "ctl.start", "camera-gui")
    adb.wait_for_state("running")
    after = read_status(adb)
    require_target(after)
    return after


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Inspect the stock X2D debug/maintenance UI trigger. "
            "No ADB enablement or arbitrary shell is included."
        )
    )
    root.add_argument("--adb-path", default="adb")
    root.add_argument("--serial", help="authorized ADB device selector")
    root.add_argument("--timeout", type=float, default=8.0)
    sub = root.add_subparsers(dest="action", required=True)
    sub.add_parser("inspect", help="read and print the fixed state surface")
    restart = sub.add_parser(
        "restart-gui",
        help="restart stock camera-gui after an explicit USB-ADB confirmation",
    )
    restart.add_argument(
        "--confirm-restart",
        action="store_true",
        help="confirm that live view may be interrupted briefly",
    )
    sub.add_parser("restore-check", help="verify a production-locked state without writing")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    adb = Adb(args.adb_path, args.serial, args.timeout)
    if args.action == "restart-gui" and not args.confirm_restart:
        raise SystemExit("restart-gui requires --confirm-restart")
    status = restart_stock_gui(adb) if args.action == "restart-gui" else read_status(adb)
    if args.action == "restore-check":
        require_restore_state(status)
        status["restore_check"] = True
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
