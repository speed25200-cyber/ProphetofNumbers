"""Segmented audit: a localised effect would be washed out by the global tests.

If the operator ever changed generator, or one server behaved differently for a
stretch, a bias confined to part of the archive would barely move a statistic computed
over all 70560 draws. So the same tests are rerun inside 14 consecutive blocks of
about 5000 draws each, and also per calendar month, and the per-block results are
compared against their own null.
"""
import numpy as np
from math import comb
from load import load, indicator

ids, ts, nums, boost, bonus = load()
N = len(ids); M = indicator(nums).astype(np.float64)
p = 0.25; p2 = (20*19)/(80.0*79); VF = p*(1-p) - (p2 - p*p)

def block_stats(lo, hi):
    m = M[lo:hi]; n = hi - lo
    c = m.sum(0)
    chi = ((c - n*p)**2).sum()/(n*p*(1-p))                 # E = 80, sd = 12.73
    ov = (m[:-1]*m[1:]).sum(1)
    zov = (ov.mean() - 5.0)/(np.sqrt(20*.25*.75*60/79)/np.sqrt(n-1))
    f = np.zeros_like(m); f[1:] = m[:-1]
    fc = f - f.mean(1, keepdims=True)
    zrep = (fc*(m - p)).sum()/np.sqrt(VF*(fc*fc).sum())    # "was in the previous draw"
    g = np.zeros_like(m); last = np.full(80, -5000.0)
    for t in range(n):
        g[t] = t - last; last = np.where(m[t] > 0, t, last)
    gl = np.log1p(np.clip(g, 0, 300)); gl = gl - gl.mean(1, keepdims=True)
    zgap = (gl*(m - p)).sum()/np.sqrt(VF*(gl*gl).sum())
    bc = np.array([(boost[lo:hi] == v).sum() for v in (1, 2, 3, 4, 5, 10)])
    e = n*np.array([.512, .238, .150, .050, .025, .025])
    chib = ((bc - e)**2/e).sum()
    return chi, zov, zrep, zgap, chib

print("14 blocks of ~%d draws" % (N//14))
print("%-6s %-16s %8s %8s %8s %8s %8s" % ("block", "ids", "sum z^2", "z_ovlap", "z_repeat", "z_gap", "chi2 boost"))
print("%-6s %-16s %8s %8s %8s %8s %8s" % ("", "", "E=80 sd12.7", "E=0", "E=0", "E=0", "df=5"))
res = []
for b in range(14):
    lo = b*(N//14); hi = (b+1)*(N//14) if b < 13 else N
    s = block_stats(lo, hi); res.append(s)
    print("%-6d %-16s %8.1f %+8.2f %+8.2f %+8.2f %8.2f"
          % (b, "%d-%d" % (ids[lo], ids[hi-1]), s[0], s[1], s[2], s[3], s[4]))
r = np.array(res)
print("\nacross blocks:")
print("  sum z^2   : mean %.1f (E=80)  min %.1f  max %.1f   sd %.1f (E=12.7)"
      % (r[:, 0].mean(), r[:, 0].min(), r[:, 0].max(), r[:, 0].std(ddof=1)))
for k, nm in ((1, "z_ovlap"), (2, "z_repeat"), (3, "z_gap")):
    print("  %-9s : mean %+.3f  max|z| %.2f   (14 blocks, expect max ~2.5)"
          % (nm, r[:, k].mean(), np.abs(r[:, k]).max()))
print("  chi2 boost: mean %.2f (E=5)  max %.2f" % (r[:, 4].mean(), r[:, 4].max()))
print("\nchance max |z| over 14 blocks x 3 statistics = 42 tests is about 2.9")
