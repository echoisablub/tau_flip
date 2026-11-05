"""Compile and run gray scan shots, wait for the CSVs. Saved globals are not modified.

usage: scan_shots.py LUT_OFFSET RUN[,RUN...] TEMP_C
"""
import pathlib
import sys
import threading
import time

import runmanager
from labscript_utils.labconfig import LabConfig
from labscript_utils.ls_zprocess import zmq_get

SCRIPT = r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts\gray_scan_labscript.py"
LOG = pathlib.Path(r"C:\Users\admin\labscript-suite\logs\BLACS.log")

offset = int(sys.argv[1])
runs = [int(x) for x in sys.argv[2].split(",")]
temp = int(sys.argv[3])

config = LabConfig()
chosen = [dict(SCAN_RUN=r, LUT_OFFSET=offset, TEMP_C=temp, SAVE_SCOPE_TRACE=1) for r in runs]
attrs, out_dir, prefix = runmanager.new_sequence_details(SCRIPT, config=config, increment_sequence_index=True)
print("sequence", attrs["sequence_index"], out_dir)
files = list(runmanager.make_run_files(out_dir, {}, chosen, attrs, prefix))
# The CSV name ends in the run number, which the analysis reads as SCAN_RUN.
names = []
for path, r in zip(files, runs):
    target = pathlib.Path(path).with_name(f"{prefix}_{r}.h5")
    names.append(path if pathlib.Path(path) == target else str(pathlib.Path(path).replace(target)))

for path in names:
    done = threading.Event()
    result = {}

    def callback(ok):
        result["ok"] = ok
        done.set()

    runmanager.compile_labscript_async(SCRIPT, path, stream_port=None, done_callback=callback)
    done.wait(300)
    print("compiled", pathlib.Path(path).name, result.get("ok"))
    if not result.get("ok"):
        raise SystemExit("compile failed")

for path in names:
    pos = LOG.stat().st_size
    print("BLACS:", zmq_get(42517, "localhost", path, timeout=60).strip())
    start = time.time()
    finished = False
    while time.time() - start < 240 and not finished:
        time.sleep(2)
        with open(LOG, "rb") as f:
            f.seek(pos)
            chunk = f.read()
            pos += len(chunk)
        for line in chunk.decode("utf-8", "replace").splitlines():
            if "Scope trace saved" in line or "Scope export failed" in line or "not armed" in line or "timed out" in line:
                print(line[24:175])
                finished = True
    print("finished" if finished else "NO RESULT", round(time.time() - start), "s")

print("OUTPUT_DIR", attrs["sequence_index"])
