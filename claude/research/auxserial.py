"""Serial structure in the auxiliary fields, which nothing has tested directly.

rankserial.py asks whether the RANK is independent of itself at a lag. The boost and the
bonus have had their bit planes measured by bm and twoadic, and their joint distribution
with the rank checked, but never their own serial structure at a range of lags. Under a
single-stream architecture they are consecutive outputs of the same generator, so a weak
one would show here as readily as in the rank.
"""
import numpy as np, math
from load import load
ids, ts, nums, boost, bonus = load()
N = len(ids)

pos = np.full(N, -1, dtype=np.int64)
for j in range(20): pos = np.where(nums[:, j] == bonus, j, pos)

def chi2(tab):
    tab = tab.astype(np.float64)
    r = tab.sum(1, keepdims=True); c = tab.sum(0, keepdims=True); n = tab.sum()
    e = r * c / n; m = e > 0
    v = (((tab - e) ** 2 / np.where(m, e, 1))[m]).sum()
    df = (int((r > 0).sum()) - 1) * (int((c > 0).sum()) - 1)
    return v, df, (v - df) / math.sqrt(2 * df)

LAGS = [1, 2, 3, 4, 5, 10, 20, 50, 100, 179, 358, 1000]
for name, a, k in (("boost", boost.astype(np.int64), int(boost.max()) + 1),
                   ("bonus position", pos, 20),
                   ("bonus value", bonus.astype(np.int64), 81)):
    worst = (0, 0.0)
    print("%s, self at lag k:" % name)
    for L in LAGS:
        t = np.zeros((k, k), dtype=np.int64)
        np.add.at(t, (a[:-L], a[L:]), 1)
        v, df, z = chi2(t)
        if abs(z) > abs(worst[1]): worst = (L, z)
        print("   lag %4d : chi2 = %9.1f (df %5d)  z = %+6.2f" % (L, v, df, z))
    print("   worst: lag %d, z = %+.2f   (%d lags tested, |z| to ~2.6 expected)\n"
          % (worst[0], worst[1], len(LAGS)))

# and the cross-field tests at lag 0 and 1
print("cross-field:")
for na, a, ka in (("boost", boost.astype(np.int64), int(boost.max()) + 1),
                  ("bonus position", pos, 20)):
    for nb, b, kb in (("boost", boost.astype(np.int64), int(boost.max()) + 1),
                      ("bonus position", pos, 20)):
        if na >= nb: continue
        for L in (0, 1):
            t = np.zeros((ka, kb), dtype=np.int64)
            if L == 0: np.add.at(t, (a, b), 1)
            else: np.add.at(t, (a[:-1], b[1:]), 1)
            v, df, z = chi2(t)
            print("   %s x %s at lag %d : chi2 = %8.1f (df %3d)  z = %+6.2f"
                  % (na, nb, L, v, df, z))
