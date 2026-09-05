import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums).astype(np.int8)

print("="*72); print("E15 TRIPLE co-occurrence chi-square (all C(80,3)=82160 triples)")
Mf = M.astype(np.float32)
cnt3 = np.zeros(0)
# count triples via combination over sorted numbers: 20C3 = 1140 per draw
from itertools import combinations
idx3 = np.array(list(combinations(range(20),3)))
a = nums[:, idx3[:,0]].astype(np.int64)-1; b = nums[:, idx3[:,1]].astype(np.int64)-1; c = nums[:, idx3[:,2]].astype(np.int64)-1
key = (a*80 + b)*80 + c
H = np.bincount(key.reshape(-1), minlength=80*80*80)
mask = np.zeros(80*80*80, dtype=bool)
ii = np.array(list(combinations(range(80),3)))
kk = (ii[:,0]*80+ii[:,1])*80+ii[:,2]
obs = H[kk].astype(np.float64)
p3 = (20*19*18)/(80.0*79*78); E3 = N*p3
V3 = N*p3*(1-p3)
S3 = ((obs-E3)**2).sum()/V3
df = len(kk)
print("  triples=%d  E=%.2f  mean_obs=%.3f" % (df, E3, obs.mean()))
print("  Sum z^2 = %.1f   E=%d  sd=%.1f  -> z = %+.2f" % (S3, df, np.sqrt(2*df), (S3-df)/np.sqrt(2*df)))
print("  max |z| = %.2f  (expect ~%.2f for %d tests)" % (np.abs((obs-E3)/np.sqrt(V3)).max(), np.sqrt(2*np.log(df)), df))

print("="*72); print("E16 bonus / boost leakage into the draw and the NEXT draw")
Z=[]
for name, v in [("bonus", bonus), ("boost", boost)]:
    vv = v.astype(np.float64); vv = (vv-vv.mean())/vv.std()
    cur = (Mf - 0.25).T @ vv / np.sqrt(N*0.25*0.75)
    nxt = (Mf[1:] - 0.25).T @ vv[:-1] / np.sqrt((N-1)*0.25*0.75)
    print("  %-6s vs current draw: max|z|=%.2f  sum z^2=%.1f (E=80)" % (name, np.abs(cur).max(), (cur**2).sum()))
    print("  %-6s vs NEXT draw   : max|z|=%.2f  sum z^2=%.1f (E=80)" % (name, np.abs(nxt).max(), (nxt**2).sum()))
# boost autocorrelation & boost vs previous boost
bs=(boost.astype(float)-boost.mean())/boost.std()
print("  boost lag1 corr z = %+.2f ; bonus lag1 corr z = %+.2f" %
      (np.corrcoef(bs[:-1],bs[1:])[0,1]*np.sqrt(N), np.corrcoef(bonus[:-1],bonus[1:])[0,1]*np.sqrt(N)))

print("="*72); print("E17 time-of-day / slot structure")
import datetime
tod = ((ts - 0) % 86400)
slot = (tod//300).astype(int)
us = np.unique(slot); print("  distinct 5-min slots used: %d" % len(us))
# chi2 of number x slot
sl = np.searchsorted(us, slot)
T = np.zeros((len(us),80))
np.add.at(T, sl, Mf)
rows = np.bincount(sl, minlength=len(us)).astype(float)
E = rows[:,None]*0.25
Zt = (T-E)/np.sqrt(E*0.75)
print("  number x slot: sum z^2=%.1f  (df=%d)  z=%+.2f  max|z|=%.2f" %
      ((Zt**2).sum(), len(us)*80, ((Zt**2).sum()-len(us)*80)/np.sqrt(2*len(us)*80), np.abs(Zt).max()))

print("="*72); print("E18 draws right after the overnight gap (cold-start signature)")
dt = np.diff(ts); first = np.concatenate([[0], np.where(dt>1000)[0]+1])
print("  %d day-starts" % len(first))
Fm = Mf[first]; c=Fm.sum(0); e=len(first)*0.25
print("  first-of-day number freq: sum z^2=%.1f (E=80) max|z|=%.2f" %
      ((((c-e)/np.sqrt(e*0.75))**2).sum(), np.abs((c-e)/np.sqrt(e*0.75)).max()))
ov = (Mf[first[1:]-1]*Mf[first[1:]]).sum(1)
print("  overlap(last of day d, first of day d+1) mean=%.4f (expect 5.0) z=%+.2f" %
      (ov.mean(), (ov.mean()-5)/ (np.sqrt(20*0.25*0.75*(60/79))/np.sqrt(len(ov)))))
