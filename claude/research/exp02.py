import numpy as np
from math import comb
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums)

print("="*70); print("E5  colex rank of each draw in [0, C(80,20))")
C = np.array([[comb(n,k) if n>=k else 0 for k in range(21)] for n in range(81)], dtype=object)
nn = nums.astype(int)
rank = np.zeros(N, dtype=object)
for k in range(20):
    rank += np.array([C[v-1][k+1] for v in nn[:,k]], dtype=object)
TOT = comb(80,20)
r = np.array([float(x)/TOT for x in rank])
print(" C(80,20) =", TOT, " ~2^%.2f" % (np.log2(TOT)))
print(" mean(r) = %.6f (0.5)  std = %.6f (0.2887)" % (r.mean(), r.std()))
ks = np.abs(np.sort(r) - (np.arange(N)+1)/N).max()
print(" KS stat = %.5f  crit(5%%)= %.5f" % (ks, 1.36/np.sqrt(N)))
print(" lag1 corr of r = %.5f  (|z|=%.2f)" % (np.corrcoef(r[:-1],r[1:])[0,1], np.corrcoef(r[:-1],r[1:])[0,1]*np.sqrt(N)))

print("  LCG recovery attempt on rank sequence (modulus via gcd of dets):")
from math import gcd
for off in (0, 1000, 50000):
    x = rank[off:off+40]
    t = [x[i+1]-x[i] for i in range(len(x)-1)]
    g = 0
    for i in range(len(t)-2):
        g = gcd(g, abs(t[i+2]*t[i] - t[i+1]*t[i+1]))
    print("   off=%6d gcd = %d  (>=C(80,20)? %s)" % (off, g, g>=TOT))

print("="*70); print("E6  lag-1 transition matrix 80x80 z-scores")
Mf = M.astype(np.float64)
T = Mf[:-1].T @ Mf[1:]
E = (N-1)*0.25*0.25
Z = (T-E)/np.sqrt(E*(1-0.0625))
print(" max|z| = %.3f at" % np.abs(Z).max(), np.unravel_index(np.abs(Z).argmax(), Z.shape))
print(" #|z|>3 = %d (expect %.1f)   #|z|>4 = %d (expect %.3f)" % ((np.abs(Z)>3).sum(), 6400*0.0027, (np.abs(Z)>4).sum(), 6400*6.3e-5))
print(" mean z = %.4f  std z = %.4f (expect 0,1)" % (Z.mean(), Z.std()))
# diagonal structure: b = a + d mod 80
for d in range(0,6):
    dz = np.array([Z[a,(a+d)%80] for a in range(80)])
    print("   diag d=%d: mean z = %+.4f (se %.3f)" % (d, dz.mean(), 1/np.sqrt(80)))

print("="*70); print("E7  timestamp structure")
dt = np.diff(ts)
odd = np.where((dt!=300)&(dt<1000))[0]
print(" non-300s intra-day steps: %d" % len(odd))
for i in odd[:25]:
    print("   id %d -> %d : dt=%d" % (ids[i], ids[i+1], dt[i]))
print(" daily gaps:", sorted(set(dt[dt>1000].tolist())))
