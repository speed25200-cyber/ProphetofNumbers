"""Targeted seed hunt on the 24 clock deviations.

The schedule is a strict 300 s grid: 70548 of 70560 timestamps sit exactly on it. The
24 exceptions always come in compensating pairs (300+d then 300-d, d <= 5 s), which is
what a scheduler hiccup looks like — and a hiccup can mean a service restarted. A
service that restarts reseeds, and a reseed from the wall clock at that moment is a
seed an attacker can enumerate.

So these 24 draws are not like the others: they are the only moments in the archive
where a fresh, clock-derived seed is plausible. The general sweep used draw 0 as its
target; this one aims at each post-deviation draw specifically, over the seed windows a
clock would actually produce — seconds, milliseconds, and a nanosecond window around
the observed timestamp.
"""
import subprocess, numpy as np, sys
from load import load

ids, ts, nums, boost, bonus = load()
dt = np.diff(ts.astype(np.int64))
jit = np.where((dt != 300) & (dt < 1000))[0]

# The draw published off-grid is at index i+1; the one after it is back on the grid.
targets = sorted({int(i)+1 for i in jit})
print("Clock deviations: %d, giving %d suspect draws" % (len(jit), len(targets)))
print("These are the only moments where a fresh clock-derived seed is plausible.\n")

WINDOWS = [
    ("unix seconds +/-30", lambda t: (t-30, t+30)),
    ("milliseconds +/-2s", lambda t: (t*1000-2000, t*1000+2000)),
    ("nanoseconds +/-2ms", lambda t: (t*10**9-2*10**6, t*10**9+2*10**6)),
]

worst = 0; worst_line = ""
for k, idx in enumerate(targets):
    t = int(ts[idx])
    for name, win in WINDOWS:
        lo, hi = win(t)
        out = subprocess.run(["./seedhunt", str(idx), str(lo), str(hi), "4"],
                             capture_output=True, text=True, timeout=1800).stdout
        best = 0; line = ""
        for row in out.splitlines():
            if "best=" not in row: continue
            v = int(row.split("best=")[1].split("/")[0])
            if v > best: best, line = v, row.strip()
        if best > worst: worst, worst_line = best, "draw %d (id %d) %s :: %s" % (idx, ids[idx], name, line)
        print("  draw %5d id %d  %-20s best %2d/20" % (idx, ids[idx], name, best))
    sys.stdout.flush()

print("\nbest over every suspect draw and window: %d/20" % worst)
print("  %s" % worst_line)
print("\n  %s" % ("NOTHING: no clock-derived reseed at any deviation" if worst < 16
                  else "INVESTIGATE"))
