"""Do the split-shot traces with the short scope window hold the whole sequence and a dark part?

usage: window_check.py SEQ
"""
import glob
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts")
from tau_analyse import frame_edges  # noqa: E402
from tau_schedule import part_sequence  # noqa: E402

folder = r"C:\Experiments\prep_lab\tau_flip_csv\2026\11\05" + "\\" + sys.argv[1]
for part, path in enumerate(sorted(glob.glob(folder + r"\*_tau_flip_labscript_*.csv"))):
    t, c1, c2, c3 = pd.read_csv(path).to_numpy().T
    e = frame_edges(t, c1)
    expected = len(part_sequence(13, part, 3))
    before = t < e[0] - 3e-3
    after = t > e[-1] + 3e-3
    print(f"part {part}: {len(t)} points, dt {(t[1] - t[0]) * 1e9:.0f} ns, t {t[0] * 1e3:.1f}..{t[-1] * 1e3:.1f} ms, "
          f"edges {len(e)} (expected {expected}), first {e[0] * 1e3:.2f} last {e[-1] * 1e3:.2f} ms, "
          f"dark before {before.sum()} after {after.sum()} points, "
          f"dark ch2 {c2[before].mean() * 1e3:.2f}/{c2[after].mean() * 1e3:.2f} ch3 {c3[before].mean() * 1e3:.2f}/{c3[after].mean() * 1e3:.2f} mV, "
          f"ch2 max {c2.max() * 1e3:.1f} mV, ref start {(c3[(t >= e[0]) & (t < e[0] + 2e-3)].mean() - c3[after].mean()) * 1e3:.2f} mV")
