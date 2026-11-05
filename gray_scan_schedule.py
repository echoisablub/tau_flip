"""Gray levels of the settled gray scan. Shared by shot and analysis.

68 levels over 0..255, split over 4 interlaced shots, each measured upwards (runs 0-3) and
downwards (runs 4-7). A shot has 18 blocks: the first level twice, so that it settles from
whatever the SLM showed before. 18 * 28 = 504 frames, below the ~512 frame / ~360 ms limit
seen in the tau measurement.
"""
import numpy as np

HOLD = 28
N_RUNS = 8
LEVELS = np.round(np.linspace(0, 255, 68)).astype(int)


def shot_levels(run):
    """Measured gray levels of one run, in display order."""
    levels = LEVELS[run % 4::4]
    return levels if run < 4 else levels[::-1]


def gray_sequence(run):
    """Gray value of every frame, including the lead-in block."""
    levels = shot_levels(run)
    return np.repeat(np.concatenate(([levels[0]], levels)), HOLD)
