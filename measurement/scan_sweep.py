"""Gray scan for a list of LUT offsets at 25 C.

usage: scan_sweep.py TEMP_C NAME RUNS OFFSET [OFFSET ...]
    NAME    name of the LOADS file in gray_scan_csv\\<date>
    RUNS    all, or comma separated run numbers (0,4)
The LUT goes back to offset 0, and the scope to its old resolution, at the end.
"""
import ctypes
import ctypes.wintypes as wt
import csv
import datetime
import hashlib
import pathlib
import re
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(r"C:\Users\admin\labscript-suite")
SCRATCH = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / r"userlib\user_devices\Hamamatsu_LCOS_SLM\config.json"
LOG = ROOT / r"logs\BLACS.log"
CSV_DAY = pathlib.Path(r"C:\Experiments\prep_lab\gray_scan_csv") / datetime.datetime.now().strftime(r"%Y\%m\%d")
TITLE = "blacs - the labscript suite"
TEMP = int(sys.argv[1])
LUT = r"C:\Users\admin\Desktop\Lut tests\Luts_13_07\%dC\{}\slm.lut" % TEMP
PY = sys.executable
SCOPE = ("169.254.211.142", 5025)
SCOPE_RES_FINE = "5.5E-08"
SCOPE_RES_SCAN = "5.5E-07"

user32 = ctypes.windll.user32
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def say(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


def blacs_window():
    found = []

    def visit(hwnd, _):
        buf = ctypes.create_unicode_buffer(300)
        user32.GetWindowTextW(hwnd, buf, 300)
        if buf.value == TITLE:
            found.append(hwnd)
        return True

    user32.EnumWindows(EnumProc(visit), 0)
    return found[0] if found else None


def set_lut(offset):
    text = CONFIG.read_bytes().decode("utf-8")
    escaped = LUT.format(offset).replace("\\", "\\\\")
    new, n = re.subn(r'("lut_path":\s*")[^"]*(")', lambda m: m.group(1) + escaped + m.group(2), text)
    if n != 1:
        raise RuntimeError(f"expected one lut_path in config, found {n}")
    CONFIG.write_bytes(new.encode("utf-8"))
    say(f"lut_path = {LUT.format(offset)}")


def restart_blacs():
    hwnd = blacs_window()
    if hwnd is None:
        raise RuntimeError("BLACS window not found")
    user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE, the same as clicking the X
    end = time.time() + 120
    while blacs_window() is not None:
        if time.time() > end:
            raise RuntimeError("BLACS did not close within 120 s; not forcing it")
        time.sleep(1)
    time.sleep(5)
    say("BLACS closed")
    pos = LOG.stat().st_size
    subprocess.Popen([str(ROOT / r".venv\Scripts\blacs-gui.exe")], cwd=str(ROOT), close_fds=True,
                     creationflags=subprocess.DETACHED_PROCESS)
    end = time.time() + 180
    ready = False
    while time.time() < end and not ready:
        time.sleep(2)
        with open(LOG, "rb") as f:
            f.seek(pos)
            text = f.read().decode("utf-8", "replace")
        init = "BLACS.Madowlark.mainloop: returning worker results to function _initialise_worker" in text
        ready = init and "BLACS.AnalysisSubmission.mainloop: Processed signal" in text and blacs_window() is not None
    if not ready:
        raise RuntimeError("BLACS did not finish starting within 180 s")
    with open(LOG, "rb") as f:
        f.seek(pos)
        text = f.read().decode("utf-8", "replace")
    problems = [l[:170] for l in text.splitlines() if "Madowlark" in l and ("ERROR" in l or "Traceback" in l)]
    if problems:
        raise RuntimeError("SLM errors during start: " + " | ".join(problems[:3]))
    time.sleep(10)
    say("BLACS ready")


def scope_resolution(value):
    with socket.create_connection(SCOPE, timeout=5) as s:
        s.sendall(f"ACQ:RES {value}\n*OPC?\n".encode())
        s.makefile("rb").readline()
        s.sendall(b"ACQ:RES?\n")
        reply = s.makefile("rb").readline().decode().strip()
    say(f"scope resolution {reply} s")


def run_load(label, offset, runs, name):
    say(f"=== {label}: runs {runs}")
    run = subprocess.run([PY, str(SCRATCH / "scan_shots.py"), str(offset), ",".join(map(str, runs)), str(TEMP)],
                         capture_output=True, text=True, cwd=str(ROOT))
    lines = [l for l in run.stdout.splitlines() if l.strip()]
    for line in lines:
        if line.startswith(("sequence", "finished", "NO RESULT")) or "failed" in line:
            say(line[:150])
    if run.returncode or any(l.startswith("NO RESULT") for l in lines):
        raise RuntimeError(f"shots failed for {label}: {run.stderr[-800:]}")
    sequence = int(next(l for l in lines if l.startswith("OUTPUT_DIR")).split()[1])
    folder = CSV_DAY / f"{sequence:04d}"
    found = len(list(folder.glob("*.csv")))
    if found != len(runs):
        raise RuntimeError(f"expected {len(runs)} traces in {folder}, found {found}")
    lut = LUT.format(offset)
    sha = hashlib.sha256(pathlib.Path(lut).read_bytes()).hexdigest()
    path = CSV_DAY / f"{name}.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["label", "offset", "folder", "lut_path", "lut_sha256", "time"])
        w.writerow([label, offset, folder, lut, sha, time.strftime("%Y-%m-%d %H:%M:%S")])
    say(f"RESULT {label} {folder}")


name = sys.argv[2]
runs = list(range(8)) if sys.argv[3] == "all" else [int(x) for x in sys.argv[3].split(",")]
offsets = [int(x) for x in sys.argv[4:]]

seen = {}
try:
    CSV_DAY.mkdir(parents=True, exist_ok=True)
    scope_resolution(SCOPE_RES_SCAN)
    for offset in offsets:
        set_lut(offset)
        restart_blacs()
        seen[offset] = seen.get(offset, 0) + 1
        run_load(f"offset {offset} load {seen[offset]}", offset, runs, name)
    say("SCAN COMPLETE")
except Exception as exc:
    say(f"STOPPED: {exc}")
finally:
    try:
        scope_resolution(SCOPE_RES_FINE)
    except Exception as exc:
        say(f"SCOPE RESOLUTION NOT RESTORED: {exc}")
    set_lut(0)
    try:
        restart_blacs()
        say("LUT back at offset 0 and loaded")
    except Exception as exc:
        say(f"CONFIG IS BACK AT OFFSET 0, BUT THE RESTART FAILED: {exc}")
