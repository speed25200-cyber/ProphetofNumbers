"""Locate the 14/20 prefix the block sweep reported.

seedhunt prints an alarm line to stderr for any prefix of 14 or more, naming the
generator, mapping, sampler and seed. Re-running the same blocks with stderr captured
names it exactly. At this trial count chance expects 0.02 such prefixes, so it is worth
looking at before it is called noise — and a genuine generator match would be 20/20,
not 14, which is the check that settles it.
"""
import numpy as np, subprocess, math, sys
from load import load
ids, ts, nums, boost, bonus = load()
first = np.load("firstofday.npy")

WIN_S, WIN_MS = 3600, 120000   # the ORIGINAL, wider windows
def pref(k):
    p = 1.0
    for i in range(k): p *= (20 - i) / (80 - i)
    return p

hits = []; trials = 0
for n, idx in enumerate(first[:41]):
    t = int(ts[idx]); midnight = t - (t % 86400)
    for wname, lo, hi in (("ts_sec", t-WIN_S, t+WIN_S),
                          ("mid_sec", midnight-WIN_S, midnight+WIN_S),
                          ("ts_ms", t*1000-WIN_MS, t*1000+WIN_MS),
                          ("mid_ms", midnight*1000-WIN_MS, midnight*1000+WIN_MS)):
        r = subprocess.run(["./seedhunt", str(idx), str(lo), str(hi), "4"],
                           capture_output=True, text=True, timeout=3600)
        trials += (hi - lo) * 256
        for line in r.stderr.splitlines():
            if "!!" in line:
                hits.append((int(idx), wname, line.strip()))
                print("  ALARM  idx=%d %s  %s" % (idx, wname, line.strip()))
        for row in r.stdout.splitlines():
            if "best=" not in row: continue
            v = int(row.split("best=")[1].split("/")[0])
            if v >= 13:
                print("  prefix %d  idx=%d %s  %s" % (v, idx, wname, row.strip()))
    if n % 10 == 0: print("  ...%d/41" % n); sys.stdout.flush()

print("\ntrials: %.3e" % trials)
for k in (13, 14, 15, 16):
    print("  chance expects %.4f prefixes of length >= %d" % (trials*pref(k), k))
print("\nalarms found: %d" % len(hits))
for h in hits: print("   ", h)
