"""Settled PD signal against gray value: uniform gray levels, see gray_scan_schedule.py.

Tests the phase range of the loaded LUT; the LUT is the one in the SLM config.
Same wiring as tau_flip_labscript.py. The BLACS plugin tau_scope saves the trace to
gray_scan_csv if SAVE_SCOPE_TRACE is true; gray_scan_analyse.py evaluates it.

runmanager globals:
    SCAN_RUN          0..7, which part of the scan this shot shows
    LUT_OFFSET        offset of the loaded LUT (bookkeeping only)
    SAVE_SCOPE_TRACE  1 = save the scope trace
"""
import sys
from pathlib import Path

from labscriptlib.prep_lab.connection_table import *
from labscript import start, stop
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gray_scan_schedule import gray_sequence

FRAME_RATE = 1436.113
N = 1024

grays = gray_sequence(int(SCAN_RUN))
print(f"gray scan: run {int(SCAN_RUN)}, LUT offset {LUT_OFFSET}, {len(grays)} frames, "
      f"{len(grays) / FRAME_RATE * 1e3:.0f} ms")

frames = np.empty((len(grays), N, N), dtype=np.uint8)
for i, g in enumerate(grays):
    frames[i] = g

t = 10e-6
init()
start()

# Sync preamble as in tau_flip_labscript.py (ADwin locks to the SLM refresh)
Madowlark_trigger.go_high(t)
t += 500e-6
Madowlark_trigger.go_low(t)
slm_hold.go_high(t)
slm_hold.go_low(t + 1e-6)
Madowlark_trigger.go_high(t + 1e-6)
t += 400e-6

MOG_AOM.go_high(t)   # light on for the whole sequence
t_end = Madowlark.program_bitmap_sequence(t, frames, FRAME_RATE,
                                          trigger_duration=1e-4,
                                          flip_immediate=False)
MOG_AOM.go_low(t_end)

stop(t_end + 100e-6)
