"""Has the response changed? Compare 50 C scans with the 25 C curve of signal against voltage."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\admin\labscript-suite\userlib\labscriptlib\prep_lab\Scripts")
import gray_scan_analyse as g  # noqa: E402

DAY = r"C:\Experiments\prep_lab\gray_scan_csv\2026\11\05"
LUT50 = r"C:\Users\admin\Desktop\Lut tests\Luts_13_07\50C\0\slm.lut"
old = pd.read_csv(DAY + r"\lut_check_levels.csv")
curve = old[old.label.isin(["offset 0 load 1", "offset 150 load 1"])].groupby("voltage").ratio.mean()
v25, y25 = curve.index.to_numpy(), curve.to_numpy()
span = y25.max() - y25.min()
volt = np.loadtxt(LUT50)[:, 1]

for seq in sys.argv[1:]:
    rows, _ = g.read_load(DAY + "\\" + seq)
    m = rows.groupby("gray").ratio.mean()
    v = volt[m.index.to_numpy()]
    inside = (v >= v25.min()) & (v <= v25.max())
    pred = np.interp(v[inside], v25, y25)
    d = m.to_numpy()[inside] - pred
    print(f"{seq}: {inside.sum()} levels; RMS against the 25 C signal(voltage) curve {np.sqrt((d ** 2).mean()) / span * 100:.1f} %, "
          f"largest {np.abs(d).max() / span * 100:.1f} %")
    # At which voltages do the extrema sit?
    y = m.to_numpy()
    print(f"   50 C LUT: max at gray {m.index[y.argmax()]} = {volt[m.index[y.argmax()]]:.0f}, "
          f"min at gray {m.index[y.argmin()]} = {volt[m.index[y.argmin()]]:.0f}")
print(f"25 C curve: max at {v25[y25.argmax()]:.0f}, min at {v25[(v25 > 1500)][y25[v25 > 1500].argmin()]:.0f} (and {v25[v25 < 1400][y25[v25 < 1400].argmin()]:.0f})")
