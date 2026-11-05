"""labscript shot for the tau measurement, option C (PBS, uniform gray value), prep-lab setup.

Untested sketch. Sync preamble copied from Scripts/test_array_ripple.py (yb-prep-lab).
Put it in userlib/labscriptlib/prep_lab/Scripts/ next to tau_schedule.py.

ONE shot runs ALL phase pairs automatically: for every pair (phi1, phi2) in
tau_schedule.pairs() the whole SLM shows phi1 for HOLD frames, then phi2 for HOLD
frames. So per shot you get every jump in both directions (phi1->phi2 inside a
pair, phi2->next phi1 between pairs). Run it once per temperature + LUT offset.

runmanager globals:
    SLM_TEMP_C     SLM head temperature, 25 / 50 / 75      (bookkeeping only)
    LUT_OFFSET     LUT offset, 0..255 as in labscript      (bookkeeping only)
    HOLD           frames per block, default 14 (9.7 ms ~ 6 tau at 1.6 ms)
    SAVE_SCOPE_TRACE  1 = the BLACS plugin tau_scope saves the scope trace of each shot
                   to tau_flip_csv (same subfolders and name as the shot, with .csv)
    N_CYCLES       repeats of the whole pair list, keep at 1 (714 frames, buffer max 752)
                   Every frame is a full 1024x1024 bitmap: 714 frames ~ 0.7 GB in the shot file.
                   For averaging rather repeat the shot in runmanager.
    N_PARTS, PART  optional: split the list over N_PARTS shots, PART = 0..N_PARTS-1 is this one.
                   Shorter shots keep more light, which falls during a long shot.
Temperature and LUT offset are NOT set here: set them on the SLM / Madowlark config
and load the LUT calibrated for that setting first. With a calibrated LUT the phase
is linear in gray value (g = phi / 2pi * 255), which tau_schedule uses.

Scope: record the WHOLE shot in one acquisition (about 0.5 s, so 60 ms/div at 10 % reference):
    ch1 = SLM frame trigger line (one pulse per frame), ch2 = PD behind the PBS,
    ch3 = reference PD (1 % arm). Trigger once on the first ch1 edge,
    >= 200 kS/s, save as CSV. tau_analyse.py cuts it into the transitions.
"""
import sys
from pathlib import Path

from labscriptlib.prep_lab.connection_table import *
from labscript import start, stop
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tau_schedule import gray_sequence, part_sequence, MAX_FRAMES

FRAME_RATE = 1436.113
N = 1024

try:
    SLM_TEMP_C = float(SLM_TEMP_C)
except NameError:
    SLM_TEMP_C = 25.0
try:
    LUT_OFFSET = int(LUT_OFFSET)
except NameError:
    LUT_OFFSET = 0
try:
    requested_hold = int(HOLD)
except NameError:
    requested_hold = 14
try:
    requested_n_cycles = int(N_CYCLES)
except NameError:
    requested_n_cycles = 1

hold = max(1, requested_hold)
n_cycles = max(1, requested_n_cycles)

grays = gray_sequence(hold, n_cycles)
while len(grays) > MAX_FRAMES:
    if hold > 1:
        hold -= 1
        grays = gray_sequence(hold, n_cycles)
    elif n_cycles > 1:
        n_cycles -= 1
        grays = gray_sequence(hold, n_cycles)
    else:
        raise AssertionError(f"cannot fit any valid tau sequence into {MAX_FRAMES} frames")

if hold != requested_hold or n_cycles != requested_n_cycles:
    print(f"warning: clamped HOLD/N_CYCLES to safe values: HOLD={hold}, N_CYCLES={n_cycles}")

try:
    n_parts = int(N_PARTS)
except NameError:
    n_parts = 1
if n_parts > 1:
    grays = part_sequence(hold, int(PART), n_parts)

print(f"tau flip: {SLM_TEMP_C} C, LUT offset {LUT_OFFSET}, {len(grays)} frames, "
      f"{len(grays) / FRAME_RATE * 1e3:.0f} ms")

frames = np.empty((len(grays), N, N), dtype=np.uint8)
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

MOG_AOM.go_high(t)   # light on for the whole sequence
t_end = Madowlark.program_bitmap_sequence(t, frames, FRAME_RATE,
                                          trigger_duration=1e-4,
                                          flip_immediate=False)
MOG_AOM.go_low(t_end)

stop(t_end + 100e-6)
