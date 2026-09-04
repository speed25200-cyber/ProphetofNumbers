"""The 358 nightly restarts, which are the natural reseed moments.

The schedule is not continuous: draws run in daily blocks separated by a 25 500 s break,
and every block starts at 04:05 UTC. If the service is restarted nightly and reseeds
from the clock, the FIRST draw of each block is where that seed would show — and no sweep
so far has aimed there. jitter_seeds aimed at the 24 clock deviations; seedhunt aimed at
a handful of arbitrary draws.

Both output models are tested at each of the 358 boundaries: the shuffle model
(seedhunt, scoring a Fisher-Yates prefix) and the unranking model (rankseed, comparing
the full 61.6-bit rank). Windows cover the block's own timestamp and the preceding
midnight, at second and millisecond granularity.
"""
import numpy as np, subprocess, math, sys, datetime

first = np.load("firstofday.npy")
from load import load
ids, ts, nums, boost, bonus = load()

def pref(k):
    p = 1.0
    for i in range(k): p *= (20 - i) / (80 - i)
    return p

WIN_S  = 3600          # +/- 1 h in seconds
WIN_MS = 120000        # +/- 2 min in milliseconds

best_prefix = 0; best_line = ""; hits = 0; trials_sh = 0; trials_rs = 0
for n, idx in enumerate(first):
    t = int(ts[idx])
    midnight = t - (t % 86400)
    windows = [
        ("ts_sec",  t - WIN_S,  t + WIN_S),
        ("mid_sec", midnight - WIN_S, midnight + WIN_S),
        ("ts_ms",   t*1000 - WIN_MS, t*1000 + WIN_MS),
        ("mid_ms",  midnight*1000 - WIN_MS, midnight*1000 + WIN_MS),
    ]
    for wname, lo, hi in windows:
        # shuffle model
        out = subprocess.run(["./seedhunt", str(idx), str(lo), str(hi), "4"],
                             capture_output=True, text=True, timeout=3600).stdout
        trials_sh += (hi - lo) * 256
        for row in out.splitlines():
            if "best=" not in row: continue
            v = int(row.split("best=")[1].split("/")[0])
            if v > best_prefix:
                best_prefix = v
                best_line = "idx %d (%s) %s :: %s" % (idx, datetime.datetime.utcfromtimestamp(t).date(), wname, row.strip())
        # unranking model
        out2 = subprocess.run(["./rankseed2", "rank_colex0.bin", str(idx), str(lo), str(hi), "4"],
                              capture_output=True, text=True, timeout=3600).stdout
        trials_rs += (hi - lo) * 20 * 3 * 2
        if "total hits: 0" not in out2:
            hits += 1
            print("*** RANK HIT at idx %d window %s ***" % (idx, wname)); print(out2)
    if n % 40 == 0:
        print("  %3d/%d blocks done   best prefix so far %d/20" % (n, len(first), best_prefix))
        sys.stdout.flush()

print()
print("blocks tested: %d   seed-tests: shuffle %.3e, unranking %.3e" % (len(first), trials_sh, trials_rs))
print("shuffle model  : best matching prefix %d/20" % best_prefix)
print("   %s" % best_line)
print("   chance at this trial count expects: >=%d in %.2f cases, >=%d in %.3f" % (
    best_prefix, trials_sh*pref(best_prefix), best_prefix+1, trials_sh*pref(best_prefix+1)))
print("unranking model: %d hits (a single one would be conclusive at 2^-61.6)" % hits)
print()
print("NOTHING" if hits == 0 else "INVESTIGATE")
