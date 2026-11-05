"""Scan until the curve stops changing, then run the 75 C measurement; give up at the deadline.

usage: wait_stable.py PREVIOUS_SEQ DEADLINE_HHMM
"""
import datetime
import pathlib
import re
import subprocess
import sys
import time

import numpy as np

SCRATCH = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts")
import gray_scan_analyse as g  # noqa: E402

PY = sys.executable
ROOT = r"C:\Users\admin\labscript-suite"
DAY = r"C:\Experiments\prep_lab\gray_scan_csv\2026\11\05"
TEMP = "75"
LIMIT = 2.0        # % of peak-to-peak between two scans
INTERVAL = 120


def say(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


def scope(*commands):
    subprocess.run([PY, str(SCRATCH / "scope_set.py"), *commands], capture_output=True, text=True, cwd=ROOT, check=True)


def scan():
    scope("ACQ:RES 5.5E-07")
    try:
        run = subprocess.run([PY, str(SCRATCH / "scan_shots.py"), "0", "0,4", TEMP], capture_output=True, text=True, cwd=ROOT)
    finally:
        scope("ACQ:RES 5.5E-08")
    if run.returncode or "NO RESULT" in run.stdout:
        raise RuntimeError(f"scan failed: {run.stderr[-400:]}")
    return "%04d" % int(re.search(r"OUTPUT_DIR (\d+)", run.stdout).group(1))


def change(a, b):
    rows_a, _ = g.read_load(DAY + "\\" + a)
    rows_b, _ = g.read_load(DAY + "\\" + b)
    m = rows_a.merge(rows_b, on=["run", "gray"], suffixes=("_a", "_b"))
    d = m.ratio_b - m.ratio_a
    span = m.ratio_a.max() - m.ratio_a.min()
    fit, _ = g.fit_phase(*(lambda s: (s.index.to_numpy(), s.to_numpy()))(rows_b.groupby("gray").ratio.mean()))
    return np.sqrt((d ** 2).mean()) / span * 100, fit[0] / np.pi


now = datetime.datetime.now()
hh, mm = int(sys.argv[2][:2]), int(sys.argv[2][2:])
deadline = now.replace(hour=hh, minute=mm, second=0)
previous = sys.argv[1]
stable = False
while datetime.datetime.now() < deadline:
    start = time.time()
    time.sleep(INTERVAL)
    current = scan()
    rms, hub = change(previous, current)
    say(f"scan {current}: change from {previous} {rms:.2f} %, range {hub:.2f} pi")
    previous = current
    if rms < LIMIT:
        stable = True
        break

if not stable:
    say("NOT STABLE by the deadline; measurement not started")
    sys.exit(0)

say("STABLE: starting the measurement")
scope("TIM:RANG 0.2")
try:
    with open(SCRATCH / "parts_75C.log", "w") as log:
        subprocess.run([PY, str(SCRATCH / "parts_sweep.py"), TEMP, "3", "0", "50", "100", "150"], stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
finally:
    scope("TIM:RANG 0.55")
say("measurement finished")
for line in open(SCRATCH / "parts_75C.log"):
    if re.search("RESULT|STOPPED|COMPLETE|RESTART|back at", line):
        print(line.strip()[:110], flush=True)
end = scan()
rms, hub = change(previous, end)
say(f"final scan {end}: change from {previous} {rms:.2f} %, range {hub:.2f} pi")
