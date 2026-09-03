import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums).astype(np.float32)
print("="*72); print("E12  SPECTRAL: FFT of each number's 0/1 series (detects any periodicity)")
X = M - 0.25
F = np.fft.rfft(X, axis=0)
P = (np.abs(F)**2)/ (N*0.25*0.75)     # normalized periodogram ~ Exp(1) under white noise
P = P[1:]                              # drop DC
agg = P.sum(axis=1)/80                 # average over 80 numbers -> ~Gamma(80,1/80), sd=1/sqrt(80)
k = np.arange(1, len(agg)+1)
top = np.argsort(-agg)[:15]
print("  aggregate periodogram: mean=%.4f (1.0) sd=%.4f (%.4f)" % (agg.mean(), agg.std(), 1/np.sqrt(80)))
print("  top-15 frequencies (bin, period in draws, power, z):")
for t in top:
    per = N/(t+1)
    print("    bin=%6d  period=%10.2f draws  power=%.4f  z=%+.2f" % (t+1, per, agg[t], (agg[t]-1)*np.sqrt(80)))
print("  max single-number power: %.2f  (expect ~%.2f for %d Exp(1) draws)" %
      (P.max(), np.log(P.size), P.size))
# per-number max
mx = P.max(axis=0); print("  per-number max power: min=%.2f max=%.2f  (expect %.2f)" % (mx.min(), mx.max(), np.log(len(P))))

print("="*72); print("E13  periodicity of the SUM series and the colex-rank series")
for name, s in [("sum", nums.astype(np.float64).sum(1)), ("bonus", bonus.astype(np.float64)),
                ("boost", boost.astype(np.float64)), ("n1", nums[:,0].astype(np.float64)),
                ("n20", nums[:,19].astype(np.float64))]:
    s = s - s.mean()
    Pp = np.abs(np.fft.rfft(s))**2
    Pp = Pp[1:]/ (Pp[1:].mean())
    j = Pp.argmax()
    print("   %-6s max power = %8.2f at bin %6d (period %9.2f)  p_bonf ~ %.3g"
          % (name, Pp[j], j+1, N/(j+1), len(Pp)*np.exp(-Pp[j])))

print("="*72); print("E14  autocorrelation of per-number indicator at lags 1..40 (pooled)")
Xc = M - 0.25
ac = []
for L in range(1,41):
    c = (Xc[:-L]*Xc[L:]).sum()/ ((N-L)*80*0.25*0.75)
    ac.append(c)
ac=np.array(ac); se = 1/np.sqrt((N)*80)
print("   se ~ %.5f" % se)
print("   " + " ".join("L%d:%+.1f" % (i+1, ac[i]/se) for i in range(40)))
print("   max|z| = %.2f" % np.abs(ac/se).max())
