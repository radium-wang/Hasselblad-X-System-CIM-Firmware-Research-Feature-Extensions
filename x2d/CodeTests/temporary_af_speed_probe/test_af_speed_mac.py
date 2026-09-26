"""Offline host-guard tests for x2d_af_speed_mac.py. Never opens USB."""

import json
import io
import re
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest import mock

import x2d_af_speed_mac as af
from test_transaction import MOCK


class FakeReader:
    def __init__(self):
        self.commands = []

    def factory_shell(self, command, capture_ms=None):
        self.commands.append((command, capture_ms))
        return "OK"


class MacHostTests(unittest.TestCase):
    def test_manual_restore_verifies_original_then_cleans_owned_files(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        plan = dict(state="MANUAL_ACTIVE", snapshot=snap,
                    device_root="/tmp/afw-1234abcd", mode="manual", seconds=0,
                    original=af.EXPECTED_ORIGINAL, candidate=af.EXPECTED_CANDIDATE)
        cleaned = []

        def shell(_reader, command, capture_ms=None):
            if command.startswith("cat /tmp/afw-"):
                return "9876"
            if command.startswith("test -d /proc/"):
                return "GONE"
            if command.startswith("sh -n "):
                return "READY"
            if command.startswith("sh /tmp/afw-"):
                return "RESTORED\nEXIT:0"
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            af.save_plan(Path(directory), plan)
            stack.enter_context(mock.patch.object(af, "current_state", side_effect=(
                "CANDIDATE_ACTIVE", "ORIGINAL_VERIFIED")))
            stack.enter_context(mock.patch.object(af, "plain_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "checked_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "verify_service_resumed"))
            stack.enter_context(mock.patch.object(af, "cleanup_owned", side_effect=lambda *args: cleaned.append(args[1])))
            with redirect_stdout(io.StringIO()) as output:
                af.restore(FakeReader(), Path(directory))
            self.assertEqual(af.load_plan(Path(directory))["state"], "ORIGINAL_VERIFIED")
            self.assertIn("RESTORED_AND_VERIFIED", output.getvalue())
        self.assertEqual(cleaned, ["/tmp/afw-1234abcd"])

    def test_uncertain_manual_install_keeps_recovery_files(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        sends = []
        cleaned = []

        def shell(_reader, command, capture_ms=None):
            if command.startswith("umask 077; mkdir "):
                return "READY"
            if command.startswith("sh -n "):
                return "SYNTAX_OK"
            if command.startswith("sh /tmp/afw-"):
                sends.append(command)
                raise af.ExperimentError("USB reply lost")
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(mock.patch.object(af, "load_artifacts", return_value=(
                {}, {"function-original.bin": b"original", "function-candidate.bin": b"candidate"})))
            stack.enter_context(mock.patch.object(af, "snapshot", return_value=snap))
            stack.enter_context(mock.patch.object(af, "checked_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "upload"))
            stack.enter_context(mock.patch.object(af, "cleanup_owned", side_effect=lambda *args: cleaned.append(args)))
            with self.assertRaisesRegex(af.ExperimentError, "USB reply lost"):
                af.install_manual(FakeReader(), Path(directory))
            self.assertEqual(af.load_plan(Path(directory))["state"], "DISPATCHED_OR_UNCERTAIN")
        self.assertEqual(len(sends), 1)
        self.assertEqual(cleaned, [])

    def test_manual_install_has_no_timer_and_keeps_recovery_files(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        uploaded = {}
        cleaned = []

        def shell(_reader, command, capture_ms=None):
            if command.startswith("umask 077; mkdir "):
                return "READY"
            if command.startswith("sh -n "):
                return "SYNTAX_OK"
            if command.startswith("sh /tmp/afw-"):
                return "9876"
            if command.startswith("head -c 4096 "):
                return "ACTIVE_UNTIL_RESTART\nEXIT:0"
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(mock.patch.object(af, "load_artifacts", return_value=(
                {}, {"function-original.bin": b"original", "function-candidate.bin": b"candidate"})))
            stack.enter_context(mock.patch.object(af, "snapshot", return_value=snap))
            stack.enter_context(mock.patch.object(af, "checked_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "upload", side_effect=lambda _r, _d, name, payload: uploaded.__setitem__(name, payload)))
            stack.enter_context(mock.patch.object(af, "current_state", return_value="CANDIDATE_ACTIVE"))
            stack.enter_context(mock.patch.object(af, "verify_service_resumed"))
            stack.enter_context(mock.patch.object(af, "cleanup_owned", side_effect=lambda *args: cleaned.append(args)))
            stack.enter_context(mock.patch.object(af.time, "sleep"))
            with redirect_stdout(io.StringIO()) as output:
                af.install_manual(FakeReader(), Path(directory))
            plan = af.load_plan(Path(directory))
            self.assertEqual((plan["mode"], plan["seconds"], plan["state"]),
                             ("manual", 0, "MANUAL_ACTIVE"))
            self.assertTrue(uploaded["window"].endswith(b"tx_install_until_restart\nexit $?\n"))
            self.assertIn("no timer", output.getvalue())
        self.assertEqual(cleaned, [])

    def test_bounded_run_verifies_restoration_before_cleanup(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        uploads = []
        cleanup = []
        reads = ["ACTIVE\nACTIVE_AT:1790376000.123456789",
                 "ACTIVE\nACTIVE_AT:1790376000.123456789\nRESTORED\n"
                 "RESTORED_AT:1790376015.987654321\nEXIT:0"]

        def shell(_reader, command, capture_ms=None):
            if command.startswith("umask 077; mkdir "):
                return "READY"
            if command.startswith("sh -n "):
                return "SYNTAX_OK"
            if command.startswith("sh /tmp/afw-"):
                return "9876"
            if command.startswith("head -c 4096 "):
                return reads.pop(0)
            if command.startswith("test ! -f /tmp/afw-"):
                return "1790376001.100 349 349 D camera-service: Entered: x2d::StateSequenceAF\n" \
                       "1790376001.400 349 349 D camera-service: " \
                       "StateAfSingle::handleAfResult AF result: HblmTypes::E_AutoFocusResult_Success"
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(mock.patch.object(af, "load_artifacts", return_value=(
                {}, {"function-original.bin": b"original", "function-candidate.bin": b"candidate"})))
            stack.enter_context(mock.patch.object(af, "snapshot", return_value=snap))
            stack.enter_context(mock.patch.object(af, "checked_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "upload", side_effect=lambda *args: uploads.append(args[2])))
            stack.enter_context(mock.patch.object(af, "current_state", return_value="ORIGINAL_VERIFIED"))
            stack.enter_context(mock.patch.object(af, "verify_service_resumed"))
            stack.enter_context(mock.patch.object(af, "cleanup_owned", side_effect=lambda *args: cleanup.append(args[1])))
            stack.enter_context(mock.patch.object(af, "start_af_log_capture", return_value=af.time.monotonic()))
            stack.enter_context(mock.patch.object(af.time, "sleep"))
            with redirect_stdout(io.StringIO()) as output:
                af.run(FakeReader(), 15, Path(directory), capture_af_log=True)
            plan = af.load_plan(Path(directory))
            self.assertEqual(plan["state"], "ORIGINAL_VERIFIED")
            self.assertEqual(plan["active_at_device"], "1790376000.123456789")
            self.assertEqual(plan["restored_at_device"], "1790376015.987654321")
            self.assertIn("StateAfSingle::handleAfResult", plan["af_event_log"])
            self.assertEqual(plan["af_event_pairs"][0]["duration_ms"], 300.0)
            self.assertTrue(plan["af_event_pairs"][0]["in_window"])
            self.assertEqual(plan["af_log_capture"], "bounded-main-buffer")
            self.assertIn("ORIGINAL_VERIFIED", output.getvalue())
            self.assertIn("AF_LOG_SAVED", output.getvalue())
        self.assertEqual(uploads, ["original", "candidate", "window", "restore"])
        self.assertEqual(len(cleanup), 1)

    def test_uncertain_dispatch_does_not_retry_or_delete_recovery(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        sends = []
        cleaned = []

        def shell(_reader, command, capture_ms=None):
            if command.startswith("umask 077; mkdir "):
                return "READY"
            if command.startswith("sh -n "):
                return "SYNTAX_OK"
            if command.startswith("sh /tmp/afw-"):
                sends.append(command)
                raise af.ExperimentError("USB reply lost")
            if command.startswith("head -c 4096 "):
                return "ACTIVE"
            self.fail(f"unexpected command: {command}")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(mock.patch.object(af, "load_artifacts", return_value=(
                {}, {"function-original.bin": b"original", "function-candidate.bin": b"candidate"})))
            stack.enter_context(mock.patch.object(af, "snapshot", return_value=snap))
            stack.enter_context(mock.patch.object(af, "checked_shell", side_effect=shell))
            stack.enter_context(mock.patch.object(af, "upload"))
            stack.enter_context(mock.patch.object(af, "cleanup_owned", side_effect=lambda *args: cleaned.append(args)))
            stack.enter_context(mock.patch.object(af.time, "sleep"))
            with self.assertRaisesRegex(af.ExperimentError, "restoration unverified"):
                af.run(FakeReader(), 15, Path(directory))
            self.assertEqual(af.load_plan(Path(directory))["state"], "DISPATCHED_OR_UNCERTAIN")
        self.assertEqual(len(sends), 1)
        self.assertEqual(cleaned, [])

    def test_device_transaction_fault_paths_without_usb(self):
        core = (af.HERE / "transaction.sh").read_text(encoding="utf-8")
        cases = ("success", "preflight", "freeze", "pc_busy", "original_mismatch",
                 "write_candidate", "verify_candidate", "thaw_candidate", "wait_error",
                 "interrupted", "write_original", "identity", "restore_busy")
        for case in cases:
            with self.subTest(case=case):
                script = f"CASE={case}\n{MOCK}\n{core}\ntx_run\nexit $?\n"
                result = subprocess.run(["sh"], input=script, text=True,
                                        capture_output=True, timeout=5)
                self.assertNotIn("BUG_RESUMED_PARTIAL", result.stdout)
                if case in ("success", "restore_busy"):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("RESTORED state=original paused=0", result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        for case in cases[:8]:
            with self.subTest(manual_case=case):
                script = f"CASE={case}\n{MOCK}\n{core}\ntx_install_until_restart\nexit $?\n"
                result = subprocess.run(["sh"], input=script, text=True,
                                        capture_output=True, timeout=5)
                self.assertNotIn("BUG_RESUMED_PARTIAL", result.stdout)
                if case == "success":
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("ACTIVE_UNTIL_RESTART state=candidate paused=0", result.stdout)
                    self.assertNotIn("RESTORED state=", result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_script_templates_are_bounded_and_syntactically_valid(self):
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                    product_address=0x12346000)
        window, restore = af.make_scripts(snap, "/tmp/afw-1234abcd", 15)
        manual, _ = af.make_scripts(snap, "/tmp/afw-1234abcd", 0, manual=True)
        for payload in (window, restore, manual):
            subprocess.run(["sh", "-n"], input=payload, check=True)
        self.assertIn(b"tx_run", window)
        self.assertIn(b"backend_wait", window)
        self.assertIn(b"backend_is_candidate", restore)
        self.assertNotIn(b"tx_install_until_restart\n", window)
        self.assertTrue(manual.endswith(b"tx_install_until_restart\nexit $?\n"))
        with self.assertRaises(af.ExperimentError):
            af.make_scripts(snap, "/system/bin", 15)
        with self.assertRaises(af.ExperimentError):
            af.make_scripts(snap, "/tmp/afw-1234abcd", 500)

    def test_hblshell_limit_is_checked_before_sending(self):
        reader = FakeReader()
        self.assertEqual(af.checked_shell(reader, "echo OK"), "OK")
        with self.assertRaises(af.ExperimentError):
            af.checked_shell(reader, "x" * 232)
        with self.assertRaises(af.ExperimentError):
            af.checked_shell(reader, "echo 非ASCII")
        self.assertEqual(len(reader.commands), 1)

    def test_device_timestamps_require_precise_complete_markers(self):
        self.assertEqual(af.device_transaction_times(
            "ACTIVE_AT:1790376000.123456789\nRESTORED_AT:1790376015.987654321\n"),
            {"active_at_device": "1790376000.123456789",
             "restored_at_device": "1790376015.987654321"})
        self.assertEqual(af.device_transaction_times("ACTIVE_AT:1790376000.%N\n"), {})

    def test_af_pairing_ignores_orphans_and_checks_whole_window(self):
        log = ("1790378390.000 349 349 D camera-service: StateAfSingle::handleAfResult "
               "AF result: HblmTypes::E_AutoFocusResult_Success\n"
               "1790378390.724 349 349 D camera-service: Entered: x2d::StateSequenceAF\n"
               "1790378391.196 349 349 D camera-service: StateAfSingle::handleAfResult "
               "AF result: HblmTypes::E_AutoFocusResult_Success\n"
               "1790378417.733 349 349 D camera-service: Entered: x2d::StateSequenceAF\n"
               "1790378418.113 349 349 D camera-service: StateAfSingle::handleAfResult "
               "AF result: HblmTypes::E_AutoFocusResult_Success\n")
        pairs = af.af_event_pairs(log, "1790378390.000000000", "1790378400.000000000")
        self.assertEqual([pair["duration_ms"] for pair in pairs], [472.0, 380.0])
        self.assertEqual([pair["in_window"] for pair in pairs], [True, False])

    def test_bounded_af_logger_command_is_scoped_and_checked(self):
        class CaptureReader(FakeReader):
            def factory_shell(self, command, capture_ms=None):
                self.commands.append((command, capture_ms))
                if command.startswith("busybox timeout -t 65 logcat "):
                    return "4321"
                if command.startswith("test -f /tmp/afw-1234abcd/af.log"):
                    return "READY"
                raise AssertionError(f"unexpected command: {command}")

        reader = CaptureReader()
        self.assertIsInstance(af.start_af_log_capture(reader, "/tmp/afw-1234abcd", 349, 45), float)
        command, capture_ms = reader.commands[0]
        self.assertLessEqual(len(command.encode("ascii")), 231)
        self.assertIn("--pid=349", command)
        self.assertIn("-f /tmp/afw-1234abcd/af.log", command)
        self.assertEqual(capture_ms, 10000)
        with self.assertRaises(af.ExperimentError):
            af.start_af_log_capture(reader, "/tmp/other", 349, 45)

    def test_cleanup_only_touches_fixed_owned_path(self):
        reader = FakeReader()
        af.cleanup_owned(reader, "/tmp/afw-1234abcd")
        commands = [item[0] for item in reader.commands]
        self.assertTrue(commands[-1] == "rmdir /tmp/afw-1234abcd")
        self.assertTrue(all(len(command.encode("ascii")) <= 231 for command in commands))
        self.assertTrue(all("{" not in command for command in commands))
        self.assertTrue(all(re.search(r"^rm -f (?:/tmp/afw-1234abcd/[a-z0-9.]+ ?)+$", command)
                            for command in commands[:-1]))
        with self.assertRaises(af.ExperimentError):
            af.cleanup_owned(reader, "/tmp")

    def test_plan_is_atomic_and_rejects_wrong_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            plan = dict(state="PREPARED_NOT_UPLOADED", device_root="/tmp/afw-1234abcd",
                        original=af.EXPECTED_ORIGINAL, candidate=af.EXPECTED_CANDIDATE,
                        seconds=15,
                        snapshot=dict(pid=123, start=456, address=0x12345000,
                                      product_address=0x12346000,
                                      length=af.EXPECTED_END - af.EXPECTED_ENTRY,
                                      boot="11111111-2222-3333-4444-555555555555"))
            af.save_plan(directory, plan)
            self.assertEqual(af.load_plan(directory), plan)
            self.assertEqual((directory / ".gitignore").read_text(), "*\n!.gitignore\n")
            plan["candidate"] = "0" * 64
            (directory / "plan.json").write_text(json.dumps(plan))
            with self.assertRaises(af.ExperimentError):
                af.load_plan(directory)

    def test_uncertain_recovery_is_never_reissued(self):
        reader = FakeReader()
        plan = dict(state="RECOVERY_DISPATCHED_OR_UNCERTAIN",
                    device_root="/tmp/afw-1234abcd", original=af.EXPECTED_ORIGINAL,
                    candidate=af.EXPECTED_CANDIDATE)
        with mock.patch.object(af, "load_plan", return_value=plan):
            with self.assertRaisesRegex(af.ExperimentError, "already dispatched"):
                af.restore(reader, Path("/not/accessed"))
        self.assertEqual(reader.commands, [])

    def test_status_never_interprets_unknown_bytes_as_original(self):
        reader = FakeReader()
        snap = dict(pid=123, start=456,
                    boot="11111111-2222-3333-4444-555555555555",
                    address=0x12345000, length=1068)
        plan = dict(snapshot=snap)
        with mock.patch.object(af, "check_usb_identity"), \
             mock.patch.object(af, "plain_shell", return_value="123"), \
             mock.patch.object(af, "process_identity", return_value=(456, snap["boot"])), \
             mock.patch.object(af, "memory_hash", return_value="0" * 64):
            self.assertEqual(af.current_state(reader, plan), "UNKNOWN_BYTES")


if __name__ == "__main__":
    unittest.main()
