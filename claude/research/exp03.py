import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums).astype(np.float64)
p=0.25; cnt = M.sum(0); E=N*p
VAR = N*p*(1-p)
print("="*72); print("E8  CORRECT global uniformity (report used E as variance -> wrong)")
print(" report chi2/df = 0.6784 using denom E=%.0f" % E)
print(" correct denom Var = N p(1-p) = %.0f" % VAR)
S = ((cnt-E)**2).sum()/VAR
print(" Sum z^2 = %.3f    E[.]=80  sd=%.2f  -> z = %+.2f" % (S, np.sqrt(2*79*(80/79)**2), (S-80)/12.73))
print(" report-style chi2 recomputed: %.4f /79 = %.4f  (x0.75 of truth)" % (((cnt-E)**2/E).sum(), ((cnt-E)**2/E).sum()/79))

print("="*72); print("E9  VARIANCE-RATIO / balancing test (detects deck or negative feedback)")
print(" window W: observed Var of per-number count vs SRS-null Var; ratio<1 => balancing")
for W in [2,3,4,5,8,10,16,20,40,80,100,200,400,1000,4000]:
    nb = N//W
    B = M[:nb*W].reshape(nb, W, 80).sum(1)          # counts per number in each block
    obs = B.var(axis=0, ddof=1).mean()
    null = W*p*(1-p)
    se = null*np.sqrt(2.0/(nb-1))/np.sqrt(80)       # ~ sd of mean-of-80 variances (corr ignored)
    print("  W=%5d blocks=%6d  Var_obs=%8.4f  Var_null=%8.4f  ratio=%.5f  z~%+.2f"
          % (W, nb, obs, null, obs/null, (obs-null)/se))

print("="*72); print("E10 order statistics of the sorted draw vs exact SRS")
mean_exact = np.array([(k+1)*81/21 for k in range(20)])
obs = nums.astype(float).mean(0)
# exact sd of k-th order stat of 20-subset of 80 (beta-binomial): var = (k)(21-k)(81)(80-20)/((21^2)(22))
k = np.arange(1,21)
var_exact = k*(21-k)*81*(80-20)/(21.0**2*22)
sd = np.sqrt(var_exact/N)
z = (obs-mean_exact)/sd
print("  pos: " + " ".join("%2d" % i for i in range(1,21)))
print("  z  : " + " ".join("%+.1f" % v for v in z))
print("  max|z| = %.2f  (80 tests-ish)" % np.abs(z).max())

print("="*72); print("E11 modular / algebraic constraints on the 20-set")
s = nums.astype(np.int64).sum(1)
for m in [2,3,4,5,7,8,9,11,13,16,17,20,40,79,80,81]:
    r = s % m; c = np.bincount(r, minlength=m); e = N/m
    chi = ((c-e)**2/e).sum()
    print("  sum mod %3d : chi2=%9.2f  df=%3d  z=%+.2f" % (m, chi, m-1, (chi-(m-1))/np.sqrt(2*(m-1))))
x = np.zeros(N, dtype=np.int64)
for j in range(20): x ^= nums[:,j].astype(np.int64)
c = np.bincount(x, minlength=128); e = N/ (np.count_nonzero(c))
print("  XOR of 20 numbers: distinct values=%d  chi2~%.1f" % (np.count_nonzero(c), ((c[c>0]-N/np.count_nonzero(c))**2/(N/np.count_nonzero(c))).sum()))
