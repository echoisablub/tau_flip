"""Split tau sequence for a list of LUT offsets; LUT back at offset 0 of that temperature at the end.

usage: parts_sweep.py TEMP_C REPEATS OFFSET [OFFSET ...]
"""
import csv
import ctypes
import ctypes.wintypes as wt
import datetime
import hashlib
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(r"C:\Users\admin\labscript-suite")
SCRATCH = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / r"userlib\user_devices\Hamamatsu_LCOS_SLM\config.json"
LOG = ROOT / r"logs\BLACS.log"
CSV_DAY = pathlib.Path(r"C:\Experiments\prep_lab\tau_flip_csv") / datetime.datetime.now().strftime(r"%Y\%m\%d")
TITLE = "blacs - the labscript suite"
TEMP = int(sys.argv[1])
LUT = r"C:\Users\admin\Desktop\Lut tests\Luts_13_07\%dC\{}\slm.lut" % TEMP
PY = sys.executable

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


def run_offset(offset, repeats):
    say(f"=== offset {offset}: {repeats} repeats of 3 shots")
    run = subprocess.run([PY, str(SCRATCH / "run_parts.py"), str(repeats), str(offset), str(TEMP)],
                         capture_output=True, text=True, cwd=str(ROOT))
    lines = [l for l in run.stdout.splitlines() if l.strip()]
    failures = [l for l in lines if l.startswith("NO RESULT") or "failed" in l or "not armed" in l]
    if run.returncode or failures:
        raise RuntimeError(f"shots failed at offset {offset}: {failures[:3]} {run.stderr[-500:]}")
    sequence = int(next(l for l in lines if l.startswith("OUTPUT_DIR")).split()[1])
    folder = CSV_DAY / f"{sequence:04d}"
    found = len(list(folder.glob("*_tau_flip_labscript_*.csv")))
    if found != 3 * repeats:
        raise RuntimeError(f"expected {3 * repeats} traces in {folder}, found {found}")
    lut = LUT.format(offset)
    path = CSV_DAY / f"tau_parts_loads_{TEMP}C.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["offset", "folder", "lut_path", "lut_sha256", "time"])
        w.writerow([offset, folder, lut, hashlib.sha256(pathlib.Path(lut).read_bytes()).hexdigest(),
                    time.strftime("%Y-%m-%d %H:%M:%S")])
    say(f"RESULT {offset} {folder}")


repeats = int(sys.argv[2])
offsets = [int(x) for x in sys.argv[3:]]
try:
    for offset in offsets:
        set_lut(offset)
        restart_blacs()
        run_offset(offset, repeats)
    say("SWEEP COMPLETE")
except Exception as exc:
    say(f"STOPPED: {exc}")
finally:
    set_lut(0)
    try:
        restart_blacs()
        say("LUT back at offset 0 and loaded")
    except Exception as exc:
        say(f"CONFIG IS BACK AT OFFSET 0, BUT THE RESTART FAILED: {exc}")
