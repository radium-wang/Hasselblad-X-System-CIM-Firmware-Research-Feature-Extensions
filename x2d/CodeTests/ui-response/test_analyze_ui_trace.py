"""Synthetic saved traces: timing gaps, CPU clock domains and sanitized output."""
import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "tools/analyze_ui_trace.py"
SPEC = importlib.util.spec_from_file_location("ui_trace", PATH)
MOD = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)

def proc(pid=10, start=100, ticks=100, nice=-15):
    fields = ["0"] * 22
    fields[0] = "S"; fields[11] = str(ticks); fields[12] = "0"
    fields[16] = str(nice); fields[19] = str(start)
    return str(pid) + " (camera-gui) " + " ".join(fields)

class TraceTests(unittest.TestCase):
    def test_touch_keeps_lift_gaps_and_splits_clock_reversals(self):
        values = [1, 1.007, 1.014, 1.100, .2, .2, .207]
        result = MOD.analyze("\n".join("[ %s] /dev/input/event0: EV_SYN SYN_REPORT 00000000" % v for v in values))
        touch = result["touch"]
        self.assertEqual(touch["reports"], 7)
        self.assertAlmostEqual(touch["intervalMs"]["median"], 7)
        self.assertAlmostEqual(touch["intervalMs"]["p95"], 86)
        self.assertEqual(touch["gapsOver40Ms"], 1)
        self.assertEqual(touch["clockReversals"], 1)
        self.assertEqual(touch["duplicateTimestamps"], 1)

    def test_cpu_requires_explicit_hz_and_never_touch_clock(self):
        text = "1.0 4.0\n" + proc(ticks=100) + "\n[999] EV_SYN SYN_REPORT 0\n3.0 8.0\n" + proc(ticks=180)
        r = MOD.analyze(text)
        self.assertEqual(r["guiCpu"]["ticksPerSecond"]["median"], 40)
        self.assertNotIn("percentOfOneCore", r["guiCpu"])
        self.assertEqual(MOD.analyze(text, 100)["guiCpu"]["percentOfOneCore"]["median"], 40)
        self.assertEqual(r["guiCpu"]["niceValues"], [-15])

    def test_restarts_reuse_duplicate_times_and_tick_resets(self):
        samples = [(1, proc()), (2, proc(pid=11)), (3, proc(pid=11, start=200)),
                   (3, proc(pid=11, start=200, ticks=110)),
                   (4, proc(pid=11, start=200, ticks=5)),
                   (5, proc(pid=11, start=200, ticks=25))]
        r = MOD.analyze("\n".join(str(t) + " 0\n" + s for t, s in samples))
        self.assertEqual(r["guiCpu"]["rejectedComparisonsOrSamples"], 4)
        self.assertEqual(r["guiCpu"]["ticksPerSecond"]["median"], 20)

    def test_malformed_samples_reset_cpu_chain_and_no_raw_echo(self):
        text = "1 0\n" + proc() + "\n10 (camera-gui) S malformed\n2 0\n" + proc(ticks=200)
        text += "\nPRIVATE_FIXTURE_PATH and identification must not be copied\nGPU Utilisation: 105%\nGPU Utilisation: 4%"
        text += "\nFramerate: 58, no-buf vsync: 1\nFramerate: 0, no-buf vsync: 0"
        r = MOD.analyze(text)
        self.assertEqual(r["guiCpu"]["ticksPerSecond"]["count"], 0)
        self.assertEqual(r["gpuPercent"]["median"], 4)
        self.assertEqual([f["fps"] for f in r["westonWindows"]], [58, 0])
        self.assertNotIn("PRIVATE_FIXTURE", json.dumps(r))

    def test_empty_and_invalid_hz(self):
        self.assertIsNone(MOD.analyze("")["touch"]["intervalMs"]["p95"])
        for hz in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError): MOD.analyze("", hz)

if __name__ == "__main__":
    unittest.main()
