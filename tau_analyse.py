"""Cut one scope recording of the tau flip shot into transitions and fit tau.

Usage:
    python tau_analyse.py trace.csv [trace2.csv ...] --hold 14 [--temp 25 --offset 0]
                          [--out tau_25C_O000.csv] [--plot]

trace.csv: columns time [s], ch1 (frame trigger), ch2 (PD behind PBS),
           optional ch3 (reference PD). One header line.
Several traces of the same sequence are averaged per transition before the fit.

Model (option C, PBS): the PD sees
    i(t) = A * cos^2(phi(t) / 2) + B + m * t, with
    phi(t) = theta + phi_to + (phi_from - phi_to) * exp(-(t - t0 - d) / tau).
phi_from / phi_to = g * 2pi / 255 from the commanded gray values (calibrated LUT).
t0 = output-trigger edge of the block. Free: tau, A, B, drift m, delay d, phase bias theta.
theta covers the bias of the PBS arm, and m the slow signal drift during a block. The
fit also handles transitions that pass through an intensity extremum.
A fit counts as usable (fit_ok = 1) only if the step is well above the noise, the curve
describes the data, tau fits well inside the window, and the response isn't late. The note column gives the reason
otherwise. The 10-90 % time is only meaningful when the transition stays on one side of an
extremum. 'up' / 'down' = gray value (voltage) up / down.
"""
import argparse
import csv
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tau_schedule import parts, transitions  # noqa: E402

FRAME_RATE = 1436.113
TWO_PI = 2 * np.pi
TAU_MIN = 5e-5   # fit limits for tau, in s
TAU_MAX = 0.03
BIN_WIDTH = 5e-5  # fit and plot bin width, in s
REF_SMOOTH = 1e-3  # averaging time of the reference PD, in s
RIPPLE_FREQ = FRAME_RATE / 2  # the signal ripples at half the frame rate, locked to the frames
DARK_GAP = 3e-3   # stay this far from the sequence when measuring the dark level, in s
PRE_EDGE = 1e-3   # the fit window opens this long before the trigger edge...
POST_END = 1e-3   # ...and closes this long before the next edge, in s
DELAY_MAX = 8e-3
MIN_STEP_TO_NOISE = 5
MIN_R2 = 0.7
MIN_STEP_V = 5e-3  # smaller steps did not reproduce between shots; scales with PD signal
LATE_DELAY = 2e-3  # a later response is not explained by the normal trigger delay
COLOR_DATA = "#a3a29c"
COLOR_FIT = "#2a78d6"
COLOR_LIMIT = "#d03b3b"
COLOR_TEXT = "#0b0b0b"
COLOR_MUTED = "#52514e"
COLOR_GRID = "#e4e3df"


def falling_edges(t, x):
    thr = 0.5 * (np.min(x) + np.max(x))
    idx = np.flatnonzero((x[:-1] > thr) & (x[1:] <= thr))
    return t[idx + 1]


def make_model(phi_from, phi_to):
    def f(dt, tau, A, B, m, d, theta, r_sin, r_cos, r2_sin, r2_cos):
        s = np.clip(dt - d, 0, None)
        phi = theta + phi_to + (phi_from - phi_to) * np.exp(-s / tau)
        return A * np.cos(phi / 2) ** 2 + B + m * dt + ripple(dt, r_sin, r_cos, r2_sin, r2_cos)
    return f


def ripple(dt, r_sin, r_cos, r2_sin, r2_cos):
    """Ripple at half the frame rate and at the frame rate."""
    angle = 2 * np.pi * RIPPLE_FREQ * dt
    return (r_sin * np.sin(angle) + r_cos * np.cos(angle)
            + r2_sin * np.sin(2 * angle) + r2_cos * np.cos(2 * angle))


def frame_edges(t, ch1):
    """Longest run of evenly spaced trigger edges, without stray edges before or after it."""
    edges = falling_edges(t, ch1)
    gaps = np.diff(edges)
    regular = np.abs(gaps - np.median(gaps)) < 0.02 * np.median(gaps)
    best_start = best_len = start = 0
    for i, ok in enumerate(np.append(regular, False)):
        if not ok:
            if i - start > best_len:
                best_start, best_len = start, i - start
            start = i + 1
    return edges[best_start:best_start + best_len + 1]


def smooth(x, n):
    """Moving average over n samples."""
    if n < 2:
        return x
    c = np.cumsum(np.insert(x, 0, 0.0))
    half = n // 2
    lo = np.clip(np.arange(len(x)) - half, 0, len(x))
    hi = np.clip(np.arange(len(x)) + half + 1, 0, len(x))
    return (c[hi] - c[lo]) / (hi - lo)


def bin_mean(x, n):
    n_bins = len(x) // n
    return x[:n_bins * n].reshape(n_bins, n).mean(axis=1)


def fit_transition(dt, y, g_from, g_to, a_max):
    """Fit one transition from several starting points; returns (f, p, cov) of the best fit."""
    f = make_model(g_from * TWO_PI / 255, g_to * TWO_PI / 255)
    span = max(np.ptp(y), 1e-6)
    lower = [TAU_MIN, 0, -np.inf, -np.inf, -PRE_EDGE, -np.pi, -np.inf, -np.inf, -np.inf, -np.inf]
    upper = [TAU_MAX, a_max, np.inf, np.inf, DELAY_MAX, np.pi, np.inf, np.inf, np.inf, np.inf]
    best = None
    for theta in np.linspace(-np.pi, np.pi, 8, endpoint=False):
        for d in (0.0, 2e-3, 5e-3):
            for tau in (0.5e-3, 3e-3):
                p0 = (tau, min(span, a_max), np.min(y), 0.0, d, theta, 0.0, 0.0, 0.0, 0.0)
                try:
                    p, cov = curve_fit(f, dt, y, p0=p0, bounds=(lower, upper), max_nfev=400)
                except (RuntimeError, ValueError):
                    continue
                sse = np.sum((f(dt, *p) - y) ** 2)
                if best is None or sse < best[0]:
                    best = (sse, p, cov)
    return (f, best[1], best[2]) if best else (f, None, None)


def judge_fit(f, p, dt, y, min_step=MIN_STEP_V):
    """Quality numbers of a fit, and the reason if it isn't usable."""
    wave = ripple(dt, *p[6:])
    no_drift = y - p[3] * dt - wave
    curve = f(dt, *p) - p[3] * dt - wave
    noise = np.std(no_drift - curve)
    step = np.ptp(curve)
    total = np.sum((no_drift - no_drift.mean()) ** 2)
    r2 = 1 - np.sum((no_drift - curve) ** 2) / total if total > 0 else 0.0
    if step < MIN_STEP_TO_NOISE * noise:
        note = "step below noise"
    elif r2 < MIN_R2:
        note = "poor fit"
    elif step < min_step:
        note = "step too small"
    elif p[0] <= TAU_MIN * 1.05 or p[0] >= np.ptp(dt) / 2:
        note = "tau too long or short"
    elif p[4] > LATE_DELAY:
        note = "late response"
    else:
        note = ""
    return step, noise, r2, note


def t_10_90(dt, y):
    a, b = np.median(y[:5]), np.median(y[-max(5, len(y) // 10):])
    if abs(b - a) < 1e-9:
        return np.nan
    frac = (y - a) / (b - a)
    return dt[np.argmax(frac >= 0.9)] - dt[np.argmax(frac >= 0.1)]


def shot_part(trace):
    """(part, n_parts) of a trace, from the shot file next to the CSV tree."""
    shot = Path(str(trace).replace("tau_flip_csv", "tau_flip_labscript")).with_suffix(".h5")
    if not shot.exists():
        return 0, 1
    with h5py.File(shot, "r") as f:
        return int(f["globals"].attrs.get("PART", 0)), int(f["globals"].attrs.get("N_PARTS", 1))


def transition_segments(t, ch1, ch2, ch3, hold, part=0, n_parts=1):
    """Cut one trace into binned transitions; returns (rows, largest useful amplitude)."""
    edges = frame_edges(t, ch1)
    trans = transitions(1)
    # A split shot starts with its first block twice, see tau_schedule.part_sequence.
    shown, lead = (parts(n_parts)[part], 1) if n_parts > 1 else (list(range(len(trans) + 1)), 0)
    n_frames = (len(shown) + lead) * hold
    if len(edges) < n_frames:
        print(f"warning: {len(edges)} trigger edges, expected {n_frames}")
    edges = edges[-n_frames:]     # a stray edge before the sequence can look regular
    starts = edges[lead * hold::hold]
    sample = t[1] - t[0]
    on = (t >= edges[0]) & (t <= edges[-1])
    if ch3 is None:
        sig = ch2
    else:
        # Both PDs read well above zero with the light off. Without subtracting that,
        # dividing by the reference removes only part of the drop in light power.
        dark = (t < edges[0] - DARK_GAP) | (t > edges[-1] + DARK_GAP)
        ref = smooth(ch3, int(REF_SMOOTH / sample)) - np.mean(ch3[dark])    # remove light drift, not noise
        sig = (ch2 - np.mean(ch2[dark])) * np.mean(ref[on]) / ref
    a_max = 1.5 * (np.percentile(sig[on], 99.9) - np.percentile(sig[on], 0.1))
    n_bin = max(1, int(BIN_WIDTH / sample))
    rows = []
    for j, block in enumerate(shown[1:], start=1):
        g_from, g_to, grp = trans[block - 1]
        if grp == "none" or j >= len(starts):
            continue
        t0 = starts[j]
        t1 = starts[j + 1] if j + 1 < len(starts) else t0 + hold / FRAME_RATE
        m = (t >= t0 - PRE_EDGE) & (t < t1 - POST_END)
        rows.append(dict(group=grp, g_from=g_from, g_to=g_to, dg=g_to - g_from,
                         direction="up" if g_to > g_from else "down", t0=t0, _block=block,
                         _dt_bin=bin_mean(t[m] - t0, n_bin), _y_bin=bin_mean(sig[m], n_bin)))
    return rows, a_max


def average_segments(traces):
    """Average the same transition over several traces."""
    averaged = []
    for same in zip(*traces):
        n = min(len(r["_y_bin"]) for r in same)
        row = dict(same[0])
        row["_dt_bin"] = np.mean([r["_dt_bin"][:n] for r in same], axis=0)
        row["_y_bin"] = np.mean([r["_y_bin"][:n] for r in same], axis=0)
        averaged.append(row)
    return averaged


def fit_rows(rows, a_max, min_step=MIN_STEP_V):
    """Fit every transition and add the results to its row."""
    for row in rows:
        dt_b, y_b = row["_dt_bin"], row["_y_bin"]
        if len(dt_b) < 20:
            row.update(note="too few samples", fit_ok=0)
            continue
        f, p, cov = fit_transition(dt_b, y_b, row["g_from"], row["g_to"], a_max)
        if p is None:
            row.update(note="fit failed", fit_ok=0)
        else:
            step, noise, r2, note = judge_fit(f, p, dt_b, y_b, min_step)
            row.update(tau_ms=p[0] * 1e3, dtau_ms=np.sqrt(cov[0, 0]) * 1e3, delay_us=p[4] * 1e6,
                       theta_rad=p[5], step_V=step, noise_V=noise, r2=r2,
                       ripple_V=np.hypot(p[6], p[7]), ripple2_V=np.hypot(p[8], p[9]),
                       note=note, fit_ok=int(not note))
            wave = ripple(dt_b, *p[6:])     # shown without the ripple, in data and fit
            row["_y_fit"] = f(dt_b, *p) - wave
            row["_y_plot"] = y_b - wave
        after = dt_b >= 0
        row["t10_90_ms"] = t_10_90(dt_b[after], y_b[after]) * 1e3
    return rows


def plot_fits(rows, path, title):
    """One panel per transition: measured signal, fitted curve and tau."""
    import matplotlib.pyplot as plt

    rows = [r for r in rows if "_y_bin" in r]
    n_cols = 7
    n_rows = int(np.ceil(len(rows) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.3 * n_cols, 1.75 * n_rows + 1),
                             sharex=True, squeeze=False)
    for ax in axes.flat[len(rows):]:
        ax.set_visible(False)
    for ax, r in zip(axes.flat, rows):
        flagged = not r.get("fit_ok", 0)
        ax.plot(r["_dt_bin"] * 1e3, r.get("_y_plot", r["_y_bin"]), color=COLOR_DATA, lw=1, label="measured")
        if "_y_fit" in r:
            ax.plot(r["_dt_bin"] * 1e3, r["_y_fit"], color=COLOR_FIT, lw=2, label="fit")
            result = f"τ = {r['tau_ms']:.2f} ms"
        else:
            result = "no fit"
        if flagged:
            result += f" ({r.get('note', '')})"
        ax.set_title(f"{r['g_from']} → {r['g_to']}  {r['group']}\n{result}", fontsize=8,
                     color=COLOR_LIMIT if flagged else COLOR_TEXT)
        ax.tick_params(labelsize=7, colors=COLOR_MUTED, length=2)
        ax.grid(color=COLOR_GRID, lw=0.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(COLOR_GRID)
    for col in range(n_cols):
        visible = [ax for ax in axes[:, col] if ax.get_visible()]
        visible[-1].tick_params(labelbottom=True)
        visible[-1].set_xlabel("time since trigger / ms", fontsize=7, color=COLOR_MUTED)
    for ax in axes[:, 0]:
        ax.set_ylabel("PD signal / V", fontsize=7, color=COLOR_MUTED)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.995), ncol=2,
               frameon=False, fontsize=9)
    fig.suptitle(f"{title}: relaxation fit per transition\n"
                 "Red titles: fit not usable, reason in brackets. Each panel has its own y scale. "
                 "The fitted ripple (718 and 1436 Hz) is removed from both curves. "
                 "Time 0 is the trigger edge.", fontsize=10, color=COLOR_TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", nargs="+")
    ap.add_argument("--hold", type=int, default=14)
    ap.add_argument("--temp", default="")
    ap.add_argument("--offset", default="")
    ap.add_argument("--out", default="tau_results.csv")
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--min-step-mv", type=float, default=MIN_STEP_V * 1e3,
                    help="smaller steps are flagged; scale it with the PD signal")
    a = ap.parse_args()

    segments = {}
    a_max = 0.0
    for trace in a.trace:
        d = pd.read_csv(trace).to_numpy()
        ch3 = d[:, 3] if d.shape[1] > 3 else None
        part, n_parts = shot_part(trace)
        trace_rows, trace_a_max = transition_segments(d[:, 0], d[:, 1], d[:, 2], ch3, a.hold, part, n_parts)
        segments.setdefault(part, []).append(trace_rows)
        a_max = max(a_max, trace_a_max)
    if len(segments) != n_parts:
        print(f"warning: traces of {len(segments)} parts, expected {n_parts}")
    rows = []
    for same_part in segments.values():
        averaged = average_segments(same_part)
        for r in averaged:
            r.update(temp_C=a.temp, lut_offset=a.offset, n_shots=len(same_part))
        rows += averaged
    rows = fit_rows(sorted(rows, key=lambda r: r["_block"]), a_max, a.min_step_mv * 1e-3)
    keys = ["temp_C", "lut_offset", "n_shots", "group", "g_from", "g_to", "dg", "direction",
            "tau_ms", "dtau_ms", "delay_us", "t10_90_ms", "t0", "fit_ok", "note",
            "theta_rad", "step_V", "noise_V", "r2", "ripple_V", "ripple2_V"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        tau = f"{r['tau_ms']:.3f} ms" if "tau_ms" in r else "-"
        flag = "" if r.get("fit_ok") else f"  [{r.get('note', '')}]"
        print(f"{r['g_from']:>3} -> {r['g_to']:>3}  {r['group']:<12} {r['direction']:<5} tau = {tau}{flag}")
    n_ok = sum(1 for r in rows if r.get("fit_ok"))
    print(f"usable fits: {n_ok} of {len(rows)}")
    print(f"wrote {a.out}")

    if a.plot:
        import matplotlib.pyplot as plt
        ok = [r for r in rows if r.get("fit_ok") and r["group"] != "extra"]
        for direc, c in (("up", "C0"), ("down", "C3")):
            s = [r for r in ok if r["direction"] == direc]
            plt.plot([abs(r["dg"]) for r in s], [r["tau_ms"] for r in s], "o", color=c, label=f"gray {direc}")
        plt.xscale("log")
        plt.xlabel("|delta g|")
        plt.ylabel("tau / ms")
        plt.legend()
        plt.title(f"{a.temp} C, LUT offset {a.offset}")
        plt.savefig(Path(a.out).with_suffix(".png"), dpi=150)
        out = Path(a.out)
        plot_fits(rows, out.with_name(out.stem + "_fits.png"), f"{a.temp} C, LUT offset {a.offset}")


if __name__ == "__main__":
    main()
