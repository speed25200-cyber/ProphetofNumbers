import numpy as np
from math import comb
from load import load, indicator
rng=np.random.default_rng(2026)
ids,ts,nums,boost,bonus=load(); N=len(ids); M=indicator(nums).astype(np.int8)

print("="*74)
print("E27  Is the lag-1 overlap chi2 real?  -> profile over lags 1..60 + SRS control")
e=np.array([comb(20,k)*comb(60,20-k)/comb(80,20) for k in range(21)])
def hist_chi(Mx,L):
    ov=(Mx[:-L]&Mx[L:]).sum(1); n=len(ov)
    h=np.bincount(ov,minlength=21).astype(float); ee=e*n
    m=ee>5; return ((h[m]-ee[m])**2/ee[m]).sum(), m.sum()-1
c=[hist_chi(M,L)[0] for L in range(1,61)]
df=hist_chi(M,1)[1]
c=np.array(c)
print("  df=%d ; chi2 by lag 1..60:"%df)
print("   "+" ".join("%.0f"%v for v in c))
print("  lag-1 = %.2f ; rank among 60 lags = %d ; mean %.2f (E=%d) ; max %.2f at lag %d"
      %(c[0], 1+int((c>c[0]).sum()), c.mean(), df, c.max(), 1+int(c.argmax())))
print("  -> a real lag-1 effect would make lag 1 an outlier among the 60; it is not")

print("\n  SRS control: 4 independent synthetic archives, same size")
for r in range(4):
    S=np.zeros((N,80),np.int8)
    for t in range(N): S[t, rng.choice(80,20,replace=False)]=1
    cc=np.array([hist_chi(S,L)[0] for L in range(1,16)])
    print("   run %d : lag-1 chi2 = %6.2f | lags1-15 max = %6.2f mean = %5.2f"%(r,cc[0],cc.max(),cc.mean()))

print("="*74)
print("E28  The gap-pair chi2 = 2759 : artefact of a wrong null, or real?")
nn=nums.astype(int)
def gappair(nn_):
    g=np.concatenate([nn_[:,:1]-1,np.diff(nn_,axis=1)-1,80-nn_[:,-1:]],axis=1)
    a=np.clip(g[:,:-1],0,7).reshape(-1); b=np.clip(g[:,1:],0,7).reshape(-1)
    T=np.bincount(a*8+b,minlength=64).reshape(8,8).astype(float)
    E=np.outer(T.sum(1),T.sum(0))/T.sum()
    return ((T-E)**2/E).sum()
print("  real archive : chi2 = %.1f"%gappair(nn))
for r in range(4):
    S=np.sort(np.array([rng.choice(80,20,replace=False)+1 for _ in range(N)]),axis=1)
    print("  SRS control %d: chi2 = %.1f"%(r,gappair(S)))
print("  -> the 21 gaps must sum to 60, so they are dependent by construction;")
print("     the product-of-marginals null is simply wrong. Compare to the controls.")
