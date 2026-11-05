"""Evaluate gray scans: phase range of each LUT, and whether the LUTs share one I(voltage) curve.

Usage:
    python gray_scan_analyse.py LOADS.csv [--out-prefix PATH]

LOADS.csv (written by the measurement) has the columns label, offset, folder, lut_path.
Every folder holds the traces of one LUT load; the run number is the end of the file name.
A row is one LUT load, so the same offset can appear twice.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gray_scan_schedule import HOLD, shot_levels  # noqa: E402
from tau_analyse import FRAME_RATE, frame_edges  # noqa: E402

WINDOW = 5e-3     # settled value: mean over the last 5 ms of a block
N_BLOCKS = 18
DARK_GAP = 3e-3   # stay this far from the sequence when measuring the dark level


def read_trace(path, run):
    """One row per measured level; the lead-in block is dropped."""
    d = pd.read_csv(path).to_numpy()
    t, ch1, ch2, ch3 = d[:, 0], d[:, 1], d[:, 2], d[:, 3]
    edges = frame_edges(t, ch1)
    n_frames = N_BLOCKS * HOLD
    if len(edges) < n_frames:
        raise ValueError(f"{path.name}: {len(edges)} trigger edges, expected {n_frames}")
    edges = edges[-n_frames:]
    starts = edges[::HOLD]
    block_time = HOLD / FRAME_RATE
    # Both PDs read well above zero with the light off; measure that outside the sequence.
    dark = (t < edges[0] - DARK_GAP) | (t > edges[-1] + DARK_GAP)
    dark2, dark3 = ch2[dark].mean(), ch3[dark].mean()
    rows = []
    for k, gray in enumerate(shot_levels(run), start=1):
        end = starts[k] + block_time
        late = (t >= end - WINDOW) & (t < end)
        early = (t >= end - 2 * WINDOW) & (t < end - WINDOW)
        pd_late, ref_late = ch2[late].mean() - dark2, ch3[late].mean() - dark3
        ratio = pd_late / ref_late
        rows.append(dict(run=run, direction="up" if run < 4 else "down", gray=int(gray),
                         block=k, time_ms=(end - starts[0]) * 1e3,
                         pd_V=pd_late, ref_V=ref_late, dark_pd_V=dark2, dark_ref_V=dark3, ratio=ratio,
                         settle=ratio - (ch2[early].mean() - dark2) / (ch3[early].mean() - dark3)))
    clipped = max(np.mean(ch2 >= np.max(ch2) - 1e-9), np.mean(ch2 <= np.min(ch2) + 1e-9)) > 1e-3
    return rows, clipped


def read_load(folder):
    rows = []
    clipped = []
    for path in sorted(Path(folder).glob("*.csv")):
        match = re.search(r"_(\d+)(?:_rep\d+)?\.csv$", path.name)
        if not match:
            continue
        trace_rows, flag = read_trace(path, int(match.group(1)))
        rows += trace_rows
        if flag:
            clipped.append(path.name)
    return pd.DataFrame(rows), clipped


def phase(gray, total, c1, c2):
    x = gray / 255
    return total * (x + c1 * x * (1 - x) + c2 * x * (1 - x) * (1 - 2 * x))


def model(p, gray):
    total, c1, c2, theta, a, b = p
    return a * np.cos((phase(gray, total, c1, c2) + theta) / 2) ** 2 + b


def fit_phase(gray, y):
    """Best of many starts, with free phase range and free curvature of phi(gray)."""
    span = y.max() - y.min()
    low = [0.0, -1.0, -1.0, -2 * np.pi, 0.0, y.min() - span]
    high = [4 * np.pi, 1.0, 1.0, 2 * np.pi, 3 * span, y.max()]
    best = None
    for total in np.array([1.0, 1.5, 2.0, 2.5, 3.0]) * np.pi:
        for theta in np.linspace(-np.pi, np.pi, 8, endpoint=False):
            start = [total, 0.0, 0.0, theta, span, y.min()]
            res = least_squares(lambda p: model(p, gray) - y, start, bounds=(low, high))
            if best is None or res.cost < best.cost:
                best = res
    return best.x, np.sqrt(2 * best.cost / len(y))


def rms_between(x_a, y_a, x_b, y_b):
    """RMS difference of curve b from curve a, on the part of x they share."""
    lo, hi = max(x_a.min(), x_b.min()), min(x_a.max(), x_b.max())
    inside = (x_b >= lo) & (x_b <= hi)
    order = np.argsort(x_a)
    return np.sqrt(np.mean((np.interp(x_b[inside], x_a[order], y_a[order]) - y_b[inside]) ** 2)), int(inside.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loads")
    ap.add_argument("--out-prefix")
    args = ap.parse_args()

    loads = pd.read_csv(args.loads)
    prefix = args.out_prefix or str(Path(args.loads).with_suffix(""))
    curves = {}
    summary = []
    all_rows = []
    for load in loads.itertuples():
        rows, clipped = read_load(load.folder)
        voltage = np.loadtxt(load.lut_path)[:, 1]
        rows["voltage"] = voltage[rows.gray]
        rows.insert(0, "label", load.label)
        rows.insert(1, "offset", load.offset)
        all_rows.append(rows)

        by_dir = {d: rows[rows.direction == d].sort_values("gray") for d in rows.direction.unique()}
        mean = rows.groupby("gray").ratio.mean()
        gray, y = mean.index.to_numpy(), mean.to_numpy()
        curves[load.label] = dict(offset=load.offset, gray=gray, y=y, voltage=voltage[gray], by_dir=by_dir)

        p, rms = fit_phase(gray, y)
        fits = {d: fit_phase(r.gray.to_numpy(), r.ratio.to_numpy())[0][0] for d, r in by_dir.items()
                if len(r) >= 12}
        if len(by_dir) == 2:
            hysteresis = np.sqrt(np.mean((by_dir["up"].ratio.to_numpy() - by_dir["down"].ratio.to_numpy()) ** 2))
        else:
            hysteresis = np.nan
        grid = np.arange(256)
        summary.append(dict(
            label=load.label, offset=load.offset, range_pi=p[0] / np.pi,
            range_up_pi=fits.get("up", np.nan) / np.pi, range_down_pi=fits.get("down", np.nan) / np.pi,
            c1=p[1], c2=p[2], theta_rad=p[3], fit_rms=rms, amplitude=p[4], contrast_min=y.min(), contrast_max=y.max(),
            gray_at_max=int(gray[y.argmax()]), gray_at_min=int(gray[y.argmin()]),
            end_difference=abs(y[-1] - y[0]), up_down_rms=hysteresis,
            max_settle=rows.settle.abs().max(), clipped=";".join(clipped)))
        curves[load.label]["fit"] = (grid, model(p, grid))

    all_rows = pd.concat(all_rows)
    all_rows.to_csv(prefix + "_levels.csv", index=False)
    summary = pd.DataFrame(summary)
    summary.to_csv(prefix + "_summary.csv", index=False)
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print(summary.round(4).to_string(index=False))

    base_label = loads.label.iloc[0]
    base = curves[base_label]
    print(f"\nRMS difference from {base_label} (fraction of its peak-to-peak)")
    span = base["y"].max() - base["y"].min()
    compare = []
    for label, c in curves.items():
        if label == base_label:
            continue
        by_gray, n_g = rms_between(base["gray"], base["y"], c["gray"], c["y"])
        by_volt, n_v = rms_between(base["voltage"], base["y"], c["voltage"], c["y"])
        compare.append(dict(label=label, against_gray=by_gray / span, against_voltage=by_volt / span, levels_compared=n_v))
        print(f"  {label}: against gray {by_gray / span:.3f}, against voltage {by_volt / span:.3f} ({n_v} levels)")
    pd.DataFrame(compare).to_csv(prefix + "_collapse.csv", index=False)
    plot(curves, prefix + ".png")
    print("wrote", prefix + ".png")


def plot(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#2a78d6", "#c2571a", "#3a8f5c", "#8a5cc2", "#6b6a65"]
    markers = ["o", "s", "^", "D", "v"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
    for i, (label, c) in enumerate(curves.items()):
        color, marker = colors[i % len(colors)], markers[i % len(markers)]
        for ax, x in zip(axes, (c["gray"], c["voltage"])):
            ax.plot(x, c["y"], color=color, marker=marker, ms=3.5, lw=0, label=label)
        axes[0].plot(*c["fit"], color=color, lw=1.5)
        order = np.argsort(c["voltage"])
        axes[1].plot(c["voltage"][order], c["y"][order], color=color, lw=1)
    axes[0].set(xlabel="gray value", ylabel="PD / reference, settled",
                title="Against gray: lines are the phase fit")
    axes[1].set(xlabel="LUT voltage value (12 bit)",
                title="Against voltage: the same LUTs should share one curve")
    for ax in axes:
        ax.grid(color="#e4e3df", lw=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
