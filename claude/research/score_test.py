import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums).astype(np.float32)
p=0.25; p2=(20*19)/(80.0*79); VF = (p*(1-p)) - (p2-p*p)     # variance factor for within-draw-centered weights
print("within-draw variance factor = %.7f" % VF)
Y = M - p
def zscore(F, start):
    """F: (N,80) feature, uses rows [start:]. Centered within draw. Returns exact score-test z."""
    f = F[start:]; y = M[start:]
    f = f - f.mean(axis=1, keepdims=True)
    U = (f*(y-p)).sum()
    V = VF*(f*f).sum()
    return U/np.sqrt(V) if V>0 else 0.0

res=[]
# --- lag indicators L=1..200
for L in range(1,201):
    F=np.zeros_like(M); F[L:]=M[:-L]
    res.append(("lag%d"%L, zscore(F,220)))
# --- window counts
cs=np.cumsum(M,axis=0)
for W in [2,3,5,8,13,21,34,55,89,144,233,377,610,1000,2000,5000,10000,30000]:
    F=np.zeros_like(M); F[W:]=cs[W-1:-1]-np.concatenate([np.zeros((1,80),np.float32),cs[:-W-1]])
    res.append(("win%d"%W, zscore(F,max(W+1,220))))
# --- gap
lastseen=np.full(80,-5000.0); G=np.zeros_like(M)
for t in range(N):
    G[t]=t-lastseen; lastseen=np.where(M[t]>0,t,lastseen)
res.append(("loggap", zscore(np.log1p(np.clip(G,0,300)).astype(np.float32),220)))
for g in range(0,12):
    res.append(("gap==%d"%g, zscore((G==g).astype(np.float32),220)))
# --- bonus of previous draws
for L in range(1,11):
    F=np.zeros_like(M); F[np.arange(L,N), bonus[:-L]-1]=1
    res.append(("prevbonus%d"%L, zscore(F,220)))
# --- pairwise co-occurrence propagation from previous draw (train co-matrix on 1st half only)
H=N//2; CO=(M[:H].T@M[:H]).astype(np.float64); np.fill_diagonal(CO,0)
CO=(CO-CO.mean())/CO.std()
prev=np.zeros_like(M); prev[1:]=M[:-1]
res.append(("coprev(1sthalf)", zscore((prev@CO).astype(np.float32),H)))
# --- same 5-min slot history
slot=((ts%86400)//300).astype(int); us=np.unique(slot); sm=np.searchsorted(us,slot)
S=np.zeros((len(us),80)); F=np.zeros_like(M)
for t in range(N):
    F[t]=S[sm[t]]; S[sm[t]]+=M[t]
res.append(("slot_hist", zscore(F,20000)))
# --- interaction: both in t-1 and t-2
F=np.zeros_like(M); F[2:]=M[:-2]*M[1:-1]; res.append(("prev1&2", zscore(F,220)))
F=np.zeros_like(M); F[2:]=(1-M[:-2])*(1-M[1:-1]); res.append(("absent1&2", zscore(F,220)))
# --- neighbour numbers in previous draw (j-1 or j+1 drawn)
nb=np.zeros_like(M); nb[1:,1:]+=M[:-1,:-1]; nb[1:,:-1]+=M[:-1,1:]
res.append(("neighb_prev", zscore(nb,220)))
# --- static structural
idx=np.arange(80)
for nm,v in [("parity",(idx%2).astype(np.float32)),("value",idx.astype(np.float32)),
             ("decade",(idx//10).astype(np.float32)),("mod7",(idx%7).astype(np.float32))]:
    res.append(("static_"+nm, zscore(np.repeat(v[None,:],N,0),220)))

res=np.array(res,dtype=object)
z=np.array([r[1] for r in res],dtype=float)
K=len(z)
print("\n%d predictors tested (exact score test, all %d draws)" % (K,N))
print("Bonferroni 5%% threshold |z| > %.2f" % (abs(np.percentile(np.random.default_rng(0).standard_normal(4000000),100*(1-0.05/(2*K)))) if False else 4.05))
o=np.argsort(-np.abs(z))
print("\n top 15 by |z|:")
for i in o[:15]: print("   %-18s z = %+7.3f" % (res[i][0], z[i]))
print("\n sum z^2 = %.1f over %d tests (E=%d, sd=%.1f) -> z=%+.2f" % ((z**2).sum(),K,K,np.sqrt(2*K),((z**2).sum()-K)/np.sqrt(2*K)))
print(" #|z|>2 = %d (exp %.1f) ; #|z|>3 = %d (exp %.2f) ; #|z|>4 = %d (exp %.3f)"
      % ((np.abs(z)>2).sum(),K*0.0455,(np.abs(z)>3).sum(),K*0.0027,(np.abs(z)>4).sum(),K*6.3e-5))
np.save("score_z.npy", z)
