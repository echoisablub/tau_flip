"""Compile and run the split tau sequence, wait for the CSVs. Saved globals are not modified.

usage: run_parts.py N_REPEATS LUT_OFFSET TEMP_C [N_PARTS] [HOLD]
"""
import pathlib
import sys
import threading
import time

import runmanager
from labscript_utils.labconfig import LabConfig
from labscript_utils.ls_zprocess import zmq_get

SCRIPT = r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts\tau_flip_labscript.py"
LOG = pathlib.Path(r"C:\Users\admin\labscript-suite\logs\BLACS.log")

repeats = int(sys.argv[1])
offset = int(sys.argv[2])
temp = int(sys.argv[3])
n_parts = int(sys.argv[4]) if len(sys.argv) > 4 else 3
hold = int(sys.argv[5]) if len(sys.argv) > 5 else 13

config = LabConfig()
chosen = [dict(PART=p, N_PARTS=n_parts, HOLD=hold, LUT_OFFSET=offset, SLM_TEMP_C=temp, SAVE_SCOPE_TRACE=1)
          for _ in range(repeats) for p in range(n_parts)]
attrs, out_dir, prefix = runmanager.new_sequence_details(SCRIPT, config=config, increment_sequence_index=True)
print("sequence", attrs["sequence_index"], out_dir)
files = list(runmanager.make_run_files(out_dir, {}, chosen, attrs, prefix))

for path in files:
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

for path in files:
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
