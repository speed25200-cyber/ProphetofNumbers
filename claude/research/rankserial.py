"""Generic serial dependence in the rank stream.

The rank has been attacked algebraically — LCG, lagged Fibonacci, multiply-with-carry,
F2-linear, scrambled — and every one came back empty. But those all test SPECIFIC
structures. Nothing has asked the model-free question: is rank_d independent of
rank_{d+k} at all?

That matters because it is the one test that does not need the generator to be named. A
weak generator whose family nobody thought to enumerate would still leave a contingency
table that does not factorise.

Also tests the rank against the two other published fields, since under a single-stream
architecture they come from consecutive outputs of the same generator.
"""
import numpy as np, math
from load import load
ids, ts, nums, boost, bonus = load()
C = math.comb(80, 20)
r = np.fromfile("rank_colex0.bin", dtype=np.uint64)
N = len(r)

B = 16
q = (r.astype(np.float64) / C * B).astype(np.int64).clip(0, B-1)
print("rank quantised into %d equal bins, %d draws\n" % (B, N))

def chi2(tab):
    tab = tab.astype(np.float64)
    row = tab.sum(1, keepdims=True); col = tab.sum(0, keepdims=True); n = tab.sum()
    exp = row * col / n
    m = exp > 0
    c = (((tab - exp) ** 2 / np.where(m, exp, 1))[m]).sum()
    df = (tab.shape[0] - 1) * (tab.shape[1] - 1)
    return c, df, (c - df) / math.sqrt(2 * df)

print("serial: rank bin at lag k")
worst = (0, 0.0)
for k in list(range(1, 11)) + [20, 50, 100, 179, 500, 1000]:
    t = np.zeros((B, B), dtype=np.int64)
    np.add.at(t, (q[:-k], q[k:]), 1)
    c, df, z = chi2(t)
    if abs(z) > abs(worst[1]): worst = (k, z)
    print("   lag %4d : chi2 = %8.1f (df %d)  z = %+6.2f" % (k, c, df, z))
print("   worst lag %d, z = %+.2f  (16 lags tested, so |z| up to ~2.7 is expected)" % worst)

print("\nrank bin against the other published fields")
pos = np.full(N, -1, dtype=np.int64)
for j in range(20): pos = np.where(nums[:, j] == bonus, j, pos)
for name, other, m in (("boost", boost.astype(np.int64), int(boost.max()) + 1),
                       ("bonus position", pos, 20),
                       ("bonus value", bonus.astype(np.int64), 81)):
    t = np.zeros((B, m), dtype=np.int64)
    np.add.at(t, (q, other), 1)
    keep = t.sum(0) > 0
    c, df, z = chi2(t[:, keep])
    print("   rank x %-15s chi2 = %8.1f (df %4d)  z = %+6.2f" % (name, c, df, z))

# and the same against the NEXT draw's fields, which is where a single stream would show
print("\nrank bin against the NEXT draw's fields (single-stream hypothesis)")
for name, other, m in (("boost", boost.astype(np.int64), int(boost.max()) + 1),
                       ("bonus position", pos, 20)):
    t = np.zeros((B, m), dtype=np.int64)
    np.add.at(t, (q[:-1], other[1:]), 1)
    keep = t.sum(0) > 0
    c, df, z = chi2(t[:, keep])
    print("   rank x next %-11s chi2 = %8.1f (df %4d)  z = %+6.2f" % (name, c, df, z))
