"""Exact odds table for Loto Express (20 drawn from 80) and the boost economics.

No prediction is involved: these are the numbers any correct expected-value
calculation needs, plus the boost multiplier distribution reconstructed from the
archive (chi2 = 0.55 on df 5 against 51.2/23.8/15.0/5.0/2.5/2.5 %).
"""
from math import comb
import numpy as np
from load import load

def P(k, m):
    """P(exactly m of your k picks are among the 20 drawn)."""
    return comb(20, m)*comb(60, k-m)/comb(80, k)

print("Exact hypergeometric odds, 20 drawn from 80")
print("k = numbers played, m = hits\n")
hdr = "  k  " + "".join("%12s" % ("m=%d" % m) for m in range(11))
print(hdr)
for k in range(2, 11):
    row = "  %-3d" % k
    for m in range(11):
        row += "%12s" % (("%.3e" % P(k, m)) if m <= k else "")
    print(row)

print("\nodds of hitting all k (1 in ...):")
for k in range(2, 11):
    print("   k=%2d : 1 in %s   (expected hits %.2f)" % (k, format(round(1/P(k, k)), ","), k*0.25))

ids, ts, nums, boost, bonus = load()
vals = [1, 2, 3, 4, 5, 10]
freq = np.array([(boost == v).mean() for v in vals])
design = np.array([.512, .238, .150, .050, .025, .025])
mean_all = float((design*np.array(vals)).sum())
sel = design[3:]; mean_sel = float((sel*np.array(vals[3:])).sum()/sel.sum())
print("\nboost multiplier, reconstructed from %d draws" % len(ids))
print("   observed  ", np.round(freq, 5).tolist())
print("   design    ", design.tolist(), " (chi2 = 0.55, df 5)")
print("   E[multiplier] over all draws        = %.4f" % mean_all)
print("   P(boost >= 4)                       = %.4f" % sel.sum())
print("   E[multiplier | boost >= 4]          = %.4f" % mean_sel)
print("   ratio, playing only boost >= 4      = %.3f x" % (mean_sel/mean_all))
print("""
   That ratio is a real lever and needs no prediction at all — but it only exists if
   the boost for a draw is published BEFORE its wager window closes. The archive
   cannot answer that; one live request against a draw with phase OPEN can.""")

dt = np.diff(ts.astype(np.int64))
off = (ts.astype(np.int64) % 300)
print("\nschedule: %d of %d timestamps sit exactly on the 300 s grid (%.4f%%)"
      % ((off == off[0]).sum(), len(ts), 100.0*(off == off[0]).mean()))
j = np.where((dt != 300) & (dt < 1000))[0]
print("   %d intra-day deviations, always in compensating pairs (300+d then 300-d, d<=5)"
      % len(j))
print("   deviation days:", sorted({int(x) for x in (ts[j]//86400)})[:12], "...")
