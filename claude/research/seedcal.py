"""Calibrate seedhunt's background distribution.

seedhunt's max overlap over ~1e9 seed-tests came out at 12, where independent draws
would put it near 15-16. Either the tool is losing sensitivity or its trials are not
independent draws. This reimplements one variant from scratch and histograms the
overlap, so the answer comes from the distribution rather than from a guess.
"""
import numpy as np, math
from load import load

ids, ts, nums, boost, bonus = load()
target = np.zeros(81, dtype=bool); target[nums[500]] = True

NS = 200000
seeds = np.arange(1, NS+1, dtype=np.int64)
x = seeds.copy()
a = np.tile(np.arange(1, 81, dtype=np.int16), (NS, 1))
hit = np.zeros(NS, dtype=np.int32)
for i in range(20):
    x = (16807 * x) % 2147483647
    j = i + (x % (80 - i))
    rows = np.arange(NS)
    tmp = a[rows, i].copy(); a[rows, i] = a[rows, j]; a[rows, j] = tmp
    hit += target[a[rows, i]]

obs = np.bincount(hit, minlength=21)[:21]
tot = math.comb(80, 20)
exp = np.array([math.comb(20,k)*math.comb(60,20-k)/tot for k in range(21)]) * NS
print("minstd16807 / mod / fisher_yates_fwd, %d seeds, target = draw 500" % NS)
print(" ov   observed   hypergeom")
for k in range(0, 15):
    if exp[k] < 0.01 and obs[k] == 0: continue
    print("  %2d %9d %11.2f" % (k, obs[k], exp[k]))
m = np.arange(21)
print("\n mean overlap  observed %.4f   hypergeometric %.4f" % (
    (obs*m).sum()/NS, 20*20/80))
print(" max overlap   observed %d" % hit.max())
sel = exp > 5
chi = (((obs[sel]-exp[sel])**2)/exp[sel]).sum(); df = sel.sum()-1
print(" chi2 = %.1f (df %d)  z = %+.2f" % (chi, df, (chi-df)/math.sqrt(2*df)))
