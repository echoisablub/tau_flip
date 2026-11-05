"""Transitions and frame schedule for the tau flip. Shared by shot and analysis.
 
All values are gray levels g (phase g * 2pi / 255, as in daemon and sim).
Each pair (lo, hi) is shown as blocks lo, hi, lo, so both directions lo->hi and hi->lo
are measured. The step from one pair to the next is an extra transition (kept, flagged).
 
1. Wraps: 240 <-> 16 and 208 <-> 48 (the pixel travels the long way, ~200 / ~160 grays).
2. Sort range |dg| = 4, 8, 16, 24, centred on g = 64 and g = 192. In the 36-frame sort the
   planned step is pi/36 (dg ~ 3.5), the largest actual step 0.54 rad (dg ~ 22).
3. Larger steps |dg| = 32, 64, 127, centred on g = 64.
4. Optional (OPTIONAL = True): dg = 16 centred on g = 16, 112, 160, 240.
"""
import numpy as np
 
MAX_FRAMES = 752
OPTIONAL = True
 
WRAPS = [(16, 240), (48, 208)]
STEPS = [4, 8, 16, 24]
CENTRES = [64, 192]
LARGE = [32, 64, 127]
LARGE_CENTRE = 64
OPT_CENTRES = [16, 112, 160, 240]


def _centred(c, dg):
    lo = int(np.clip(round(c - dg / 2), 0, 255 - dg))
    return (lo, lo + dg)
 
 
def pairs(optional=OPTIONAL):
    """(lo, hi, group) for every measured pair."""
    out = [(lo, hi, "wrap") for lo, hi in WRAPS]
    out += [(*_centred(c, dg), f"step{dg}@{c}") for c in CENTRES for dg in STEPS]
    out += [(*_centred(LARGE_CENTRE, dg), f"step{dg}@{LARGE_CENTRE}") for dg in LARGE]
    if optional:
        out += [(*_centred(c, 16), f"opt16@{c}") for c in OPT_CENTRES]
    return out
 
 
def blocks(n_cycles=1, optional=OPTIONAL):
    """Gray value of every block in display order."""
    return [g for _ in range(n_cycles) for lo, hi, _g in pairs(optional) for g in (lo, hi, lo)]
 
 
def gray_sequence(hold, n_cycles=1, optional=OPTIONAL):
    """Gray value of every frame."""
    return np.repeat(blocks(n_cycles, optional), hold)
 
 
def transitions(n_cycles=1, optional=OPTIONAL):
    """(from_g, to_g, group) at the start of every block after the first.
    group is 'extra' for the step between two pairs and 'none' when nothing changes."""
    out = []
    for _ in range(n_cycles):
        for lo, hi, grp in pairs(optional):
            out += [(None, lo, "extra"), (lo, hi, grp), (hi, lo, grp)]
    out = out[1:]                                  # the very first block has no predecessor
    prev = blocks(n_cycles, optional)
    fixed = []
    for k, (a, b, grp) in enumerate(out):
        a = prev[k]                                # actual previous block value
        fixed.append((a, b, "none" if a == b else grp))
    return fixed
 
 
if __name__ == "__main__":
    b = blocks()
    print(f"{len(pairs())} pairs, {len(b)} blocks, {len(b) * 14} frames at HOLD = 14")
    for a, c, g in transitions():
        print(f"{a:>3} -> {c:>3}  {g}")
 