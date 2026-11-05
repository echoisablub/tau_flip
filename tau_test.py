"""Quick check of the tau flip wiring (scope trigger, PD signal), no globals needed.

Untested sketch. Shows gray 0 and 127 alternating, 14 frames each, 280 frames in total.
The AOM stays on for about 195 ms: lower the light power first.
"""
from labscriptlib.prep_lab.connection_table import *
from labscript import start, stop
import numpy as np

FRAME_RATE = 1436.113
grays = np.repeat([0, 127] * 10, 14)
frames = np.empty((len(grays), 1024, 1024), dtype=np.uint8)
for i, g in enumerate(grays):
    frames[i] = g

t = 10e-6
init()
start()

# Sync preamble as in test_array_ripple.py (ADwin locks to the SLM refresh)
Madowlark_trigger.go_high(t)
t += 500e-6
Madowlark_trigger.go_low(t)
slm_hold.go_high(t)
slm_hold.go_low(t + 1e-6)
Madowlark_trigger.go_high(t + 1e-6)
t += 400e-6

MOG_AOM.go_high(t)
t_end = Madowlark.program_bitmap_sequence(t, frames, FRAME_RATE,
                                          trigger_duration=1e-4,
                                          flip_immediate=False)
MOG_AOM.go_low(t_end)

stop(t_end + 100e-6)
