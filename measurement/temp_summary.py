"""Summary of one temperature. usage: temp_summary.py FOLDER"""
import glob
import sys

import numpy as np
import pandas as pd

S = r"C:\Users\admin\AppData\Local\Temp\claude\98438b99de0ec3f2\0c6e0d78-3821-4b63-9b2b-08b6cbc431a9\scratchpad"
folder = sys.argv[1]
OFF = [0, 50, 100, 150]
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 100)
bins = [0, 8, 16, 24, 64, 127, 300]
labels = ["<=8", "16", "17-24", "25-64", "65-127", ">127"]
rows = []
for o in OFF:
    a = pd.read_csv(rf"{S}\{folder}\avg_O{o:03d}.csv")
    tau = np.array([pd.read_csv(f).tau_ms for f in sorted(glob.glob(rf"{S}\{folder}\O{o:03d}_*.csv"))])
    rows.append(pd.DataFrame(dict(offset=o, a=a.g_from, b=a.g_to, dg=(a.g_to - a.g_from).abs(), tau=a.tau_ms,
                                  spread=(tau.max(0) - tau.min(0)) / np.median(tau, 0) * 100, step=a.step_V * 1e3,
                                  noise=a.noise_V * 1e3, ok=a.fit_ok, delay=a.delay_us / 1e3, theta=a.theta_rad, note=a.note.fillna(""))))
t = pd.concat(rows)
t["group"] = pd.cut(t.dg, bins, labels=labels)
t.to_csv(rf"{S}\{folder}_table.csv", index=False)
print("median spread %")
print(t.groupby(["group", "offset"], observed=True).spread.median().unstack().round(1).to_string())
for o in OFF:
    x = t[t.offset == o]
    print(o, "usable", int(x.ok.sum()), "spread<20", int((x.spread < 20).sum()), "noise %.3f" % x.noise.median(),
          "max delay of steps>15mV %.2f" % x[x.step > 15].delay.max(), "median theta %.2f" % x[x.ok == 1].theta.median(), x.note.replace("", "OK").value_counts().to_dict())
big = [(16, 240), (48, 208), (0, 127), (4, 126), (240, 16), (208, 48), (127, 0)]
for a, b in big:
    x = t[(t.a == a) & (t.b == b)].set_index("offset")
    print(f"{a:>3}->{b:<3} " + " | ".join(f"{x.tau[o]:5.2f}{' ' if x.ok[o] else '*'} sp{x.spread[o]:4.0f}% {x.step[o]:4.0f}mV" for o in OFF))
