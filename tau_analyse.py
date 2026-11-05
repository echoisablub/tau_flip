"""Cut one scope recording of the tau flip shot into transitions and fit tau.

Usage:
    python tau_analyse.py trace.csv --hold 14 [--temp 25 --offset 0]
                          [--out tau_25C_O000.csv] [--plot]

trace.csv: columns time [s], ch1 (frame trigger), ch2 (PD behind PBS),
           optional ch3 (reference PD). One header line.

Model (option C, PBS): the PD sees i(t) = A * cos^2(phi(t) / 2) + B with
    phi(t) = phi_to + (phi_from - phi_to) * exp(-(t - t0 - d) / tau),
phi_from / phi_to = g * 2pi / 255 from the commanded gray values (calibrated LUT),
t0 = output-trigger edge of the block. Free: tau, A, B, delay d.
Fitting the intensity with fixed end phases also handles transitions that pass
through phi = pi (wraps, large steps): the PD signal dips through its minimum and
the fit follows it. The mirror ambiguity phi <-> 2pi - phi does not change tau.
Also reports the 10-90 % time of the intensity change (only meaningful when the
transition stays on one side of pi). 'up' / 'down' = gray value (voltage) up / down.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tau_schedule import transitions  # noqa: E402

FRAME_RATE = 1436.113
TWO_PI = 2 * np.pi


def falling_edges(t, x):
    thr = 0.5 * (np.min(x) + np.max(x))
    idx = np.flatnonzero((x[:-1] > thr) & (x[1:] <= thr))
    return t[idx + 1]


def make_model(phi_from, phi_to):
    def f(dt, tau, A, B, d):
        s = np.clip(dt - d, 0, None)
        phi = phi_to + (phi_from - phi_to) * np.exp(-s / tau)
        return A * np.cos(phi / 2) ** 2 + B
    return f


def t_10_90(dt, y):
    a, b = np.median(y[:5]), np.median(y[-max(5, len(y) // 10):])
    if abs(b - a) < 1e-9:
        return np.nan
    frac = (y - a) / (b - a)
    return dt[np.argmax(frac >= 0.9)] - dt[np.argmax(frac >= 0.1)]


def analyse(t, ch1, ch2, ch3, hold):
    edges = falling_edges(t, ch1)
    trans = transitions(1)
    n_blocks = len(trans) + 1
    if len(edges) < n_blocks * hold:
        print(f"warning: {len(edges)} trigger edges, expected {n_blocks * hold}")
    starts = edges[::hold]
    sig = ch2 if ch3 is None else ch2 * np.mean(ch3) / ch3     # remove laser drift
    a_guess = np.max(sig) - np.min(sig)
    rows = []
    for k, (g_from, g_to, grp) in enumerate(trans):
        if grp == "none" or k + 1 >= len(starts):
            continue
        t0 = starts[k + 1]
        t1 = starts[k + 2] if k + 2 < len(starts) else t0 + hold / FRAME_RATE
        m = (t >= t0) & (t < t1)
        dt, y = t[m] - t0, sig[m]
        row = dict(group=grp, g_from=g_from, g_to=g_to, dg=g_to - g_from,
                   direction="up" if g_to > g_from else "down", t0=t0)
        if len(dt) < 20:
            rows.append(dict(row, note="too few samples"))
            continue
        f = make_model(g_from * TWO_PI / 255, g_to * TWO_PI / 255)
        try:
            p, cov = curve_fit(f, dt, y, p0=(1.5e-3, a_guess, np.min(sig), 0.0),
                               bounds=([1e-5, 0, -np.inf, -2e-4], [0.05, np.inf, np.inf, 5e-4]),
                               maxfev=20000)
            row.update(tau_ms=p[0] * 1e3, dtau_ms=np.sqrt(cov[0, 0]) * 1e3, delay_us=p[3] * 1e6)
        except RuntimeError:
            row.update(note="fit failed")
        row["t10_90_ms"] = t_10_90(dt, y) * 1e3
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--hold", type=int, default=14)
    ap.add_argument("--temp", default="")
    ap.add_argument("--offset", default="")
    ap.add_argument("--out", default="tau_results.csv")
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()

    d = np.loadtxt(a.trace, delimiter=",", skiprows=1)
    ch3 = d[:, 3] if d.shape[1] > 3 else None
    rows = analyse(d[:, 0], d[:, 1], d[:, 2], ch3, a.hold)
    for r in rows:
        r.update(temp_C=a.temp, lut_offset=a.offset)
    keys = ["temp_C", "lut_offset", "group", "g_from", "g_to", "dg", "direction",
            "tau_ms", "dtau_ms", "delay_us", "t10_90_ms", "t0", "note"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        tau = f"{r['tau_ms']:.3f} ms" if "tau_ms" in r else r.get("note", "")
        print(f"{r['g_from']:>3} -> {r['g_to']:>3}  {r['group']:<12} {r['direction']:<5} tau = {tau}")
    print(f"wrote {a.out}")

    if a.plot:
        import matplotlib.pyplot as plt
        ok = [r for r in rows if "tau_ms" in r and r["group"] != "extra"]
        for direc, c in (("up", "C0"), ("down", "C3")):
            s = [r for r in ok if r["direction"] == direc]
            plt.plot([abs(r["dg"]) for r in s], [r["tau_ms"] for r in s], "o", color=c, label=f"gray {direc}")
        plt.xscale("log")
        plt.xlabel("|delta g|")
        plt.ylabel("tau / ms")
        plt.legend()
        plt.title(f"{a.temp} C, LUT offset {a.offset}")
        plt.savefig(Path(a.out).with_suffix(".png"), dpi=150)


if __name__ == "__main__":
    main()
