#!/usr/bin/env python3
"""Summarize saved getevent/proc/GPU/Weston text without device access.

Clock domains remain separate. No raw input lines, PID or filesystem paths are
included in the JSON report. CPU percentages require explicit clock_ticks.
"""
import argparse
import json
import math
import re
import statistics
from pathlib import Path

TOUCH = re.compile(r"\[\s*([0-9]+(?:\.[0-9]+)?)\]\s+.*\bEV_SYN\s+SYN_REPORT\b")
UPTIME = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s+[0-9]+(?:\.[0-9]+)?\s*$")
PROC = re.compile(r"^\s*(\d+)\s+\((.*)\)\s+(.*)$")
GPU = re.compile(r"GPU Utilisation:\s*(\d+)%")
FRAME = re.compile(r"Framerate:\s*(\d+),\s*no-buf vsync:\s*(\d+)")

def distribution(values):
    if not values:
        return {"count": 0, "median": None, "p95": None, "min": None, "max": None}
    ordered = sorted(values)
    return {"count": len(values), "median": statistics.median(values),
            "p95": ordered[math.ceil(.95 * len(ordered)) - 1],
            "min": ordered[0], "max": ordered[-1]}

def analyze(text, clock_ticks=None):
    if clock_ticks is not None and (not math.isfinite(clock_ticks) or clock_ticks <= 0):
        raise ValueError("clock_ticks must be finite and positive")
    intervals, gpu, frames, cpu, nices = [], [], [], [], set()
    touch_last = uptime = proc_last = None
    reports = reversals = duplicate_touch = rejected_proc = 0
    active_span = 0.0
    for line in text.splitlines():
        m = TOUCH.search(line)
        if m:
            stamp = float(m[1])
            if not math.isfinite(stamp):
                continue
            reports += 1
            if touch_last is not None:
                delta = stamp - touch_last
                if delta < 0:
                    reversals += 1
                elif delta == 0:
                    duplicate_touch += 1
                else:
                    intervals.append(delta * 1000); active_span += delta
            touch_last = stamp
        m = UPTIME.match(line)
        if m:
            value = float(m[1])
            uptime = value if math.isfinite(value) else None
        m = PROC.match(line)
        if m and m[2] == "camera-gui":
            try:
                f = m[3].split() # starts with field 3 (state); comm may contain spaces/parentheses
                current = (int(m[1]), int(f[19]), uptime, int(f[11]) + int(f[12]))
                nice = int(f[16])
                if uptime is None or current[3] < 0:
                    raise ValueError("no preceding sample clock or invalid ticks")
                nices.add(nice)
                if proc_last is not None:
                    pid, start, t, ticks = proc_last
                    dt, dc = uptime - t, current[3] - ticks
                    if (pid, start) == current[:2] and dt > 0 and dc >= 0:
                        cpu.append(dc / dt)
                    else:
                        rejected_proc += 1
                proc_last = current
            except (ValueError, IndexError):
                rejected_proc += 1
                proc_last = None
        m = GPU.search(line)
        if m and 0 <= int(m[1]) <= 100:
            gpu.append(int(m[1]))
        m = FRAME.search(line)
        if m:
            frames.append({"fps": int(m[1]), "noBufferVsync": int(m[2])})
    touch = {"reports": reports, "intervalMs": distribution(intervals),
             "forwardSpanSeconds": active_span, "gapsOver40Ms": sum(i > 40 for i in intervals),
             "clockReversals": reversals, "duplicateTimestamps": duplicate_touch}
    process = {"ticksPerSecond": distribution(cpu), "niceValues": sorted(nices),
               "rejectedComparisonsOrSamples": rejected_proc, "clockTicks": clock_ticks}
    if clock_ticks is not None:
        process["percentOfOneCore"] = distribution([x * 100 / clock_ticks for x in cpu])
    return {"touch": touch, "guiCpu": process, "gpuPercent": distribution(gpu),
            "westonWindows": frames,
            "limitations": ["Touch, uptime and compositor clocks are not aligned.",
                            "Event intervals and average FPS do not measure touch-to-photon latency.",
                            "Idle/lift gaps are retained, not classified as dropped input."]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("--clock-ticks", type=float, help="Explicit USER_HZ; percentage is per one core")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.trace.read_text(errors="replace"), a.clock_ticks)
    except (OSError, ValueError) as error:
        p.error(str(error))
    payload = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(payload)
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()
