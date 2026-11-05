"""Compare gray scans (same runs) taken at different times, and with the 25 C scan.

usage: drift_compare.py SEQ [SEQ ...]
"""
import glob
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts")
import gray_scan_analyse as g  # noqa: E402

DAY = r"C:\Experiments\prep_lab\gray_scan_csv\2026\11\05"
base = pd.read_csv(DAY + r"\lut_check_levels.csv")
base = base[base.label == "offset 0 load 1"]

scans = {}
for seq in sys.argv[1:]:
    rows, _ = g.read_load(DAY + "\\" + seq)
    scans[seq] = rows
    p = rows.groupby("gray").ratio.mean()
    fit, rms = g.fit_phase(p.index.to_numpy(), p.to_numpy())
    print(f"{seq}: levels {len(rows)}, ref at start {rows.sort_values('time_ms').ref_V.iloc[0] * 1e3:.2f} mV, "
          f"PD max {rows.pd_V.max() * 1e3:.1f} mV, ratio {p.min():.2f}..{p.max():.2f}, "
          f"gray at max {p.idxmax()}, at min {p.idxmin()}, fit range {fit[0] / np.pi:.2f} pi, theta {fit[3]:.2f}")

keys = list(scans)
for a, b in zip(keys[:-1], keys[1:]):
    m = scans[a].merge(scans[b], on=["run", "gray"], suffixes=("_a", "_b"))
    d = m.ratio_b - m.ratio_a
    span = m.ratio_a.max() - m.ratio_a.min()
    print(f"{a} -> {b}: RMS change {np.sqrt((d ** 2).mean()) / span * 100:.2f} % of peak-to-peak, "
          f"mean change {d.mean() / span * 100:+.2f} %, largest {d.abs().max() / span * 100:.1f} % at gray {m.gray[d.abs().idxmax()]}")
for k in keys:
    m = scans[k].merge(base, on=["run", "gray"], suffixes=("_a", "_b"))
    d = m.ratio_a - m.ratio_b
    print(f"{k} against 25 C offset 0: RMS {np.sqrt((d ** 2).mean()) / (m.ratio_b.max() - m.ratio_b.min()) * 100:.1f} %")
