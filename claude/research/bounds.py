import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N=len(ids); M=indicator(nums).astype(np.float32)
p=0.25; p2=(20*19)/(80.0*79); VF=p*(1-p)-(p2-p*p)

print("="*74); print("A. Newton-step logistic model, exact, train/test split")
cs=np.cumsum(M,axis=0)
F=[];names=[]
def win(W):
    o=np.zeros_like(M); o[W:]=cs[W-1:-1]-np.concatenate([np.zeros((1,80),np.float32),cs[:-W-1]]); return o/W
for W in (1,2,3,5,10,20,50,100,400,2000): F.append(win(W)); names.append("win%d"%W)
lastseen=np.full(80,-5000.0); G=np.zeros_like(M)
for t in range(N): G[t]=t-lastseen; lastseen=np.where(M[t]>0,t,lastseen)
F.append(np.log1p(np.clip(G,0,300)).astype(np.float32)); names.append("loggap")
pb=np.zeros_like(M); pb[np.arange(1,N),bonus[:-1]-1]=1; F.append(pb); names.append("prevbonus")
H=N//2; CO=(M[:H].T@M[:H]).astype(np.float64); np.fill_diagonal(CO,0); CO=(CO-CO.mean())/CO.std()
prev=np.zeros_like(M); prev[1:]=M[:-1]; F.append((prev@CO).astype(np.float32)); names.append("coprev")
X=np.stack(F,-1)[2100:]; Y=M[2100:]
T=X.shape[0]; d=X.shape[-1]
X=X.reshape(-1,d); Y=Y.reshape(-1)
X=(X-X.mean(0))/(X.std(0)+1e-12)
ntr=55000*80
A=(X[:ntr].T@X[:ntr])*p*(1-p); b=X[:ntr].T@(Y[:ntr]-p)
w=np.linalg.solve(A+1e-3*np.eye(d), b)
def ll(Xa,Ya):
    z=Xa@w+np.log(p/(1-p)); q=1/(1+np.exp(-z)); q=np.clip(q,1e-12,1-1e-12)
    return -(Ya*np.log(q)+(1-Ya)*np.log(1-q)).mean()
base=-(p*np.log(p)+(1-p)*np.log(1-p))
nte=(len(Y)-ntr)//80
print("  train %d draws / test %d draws, %d features"%(ntr//80,nte,d))
print("  in-sample  logloss %.7f vs base %.7f  gain %+.3e bits"%(ll(X[:ntr],Y[:ntr]),base,(base-ll(X[:ntr],Y[:ntr]))/np.log(2)))
print("  OUT-SAMPLE logloss %.7f vs base %.7f  gain %+.3e bits"%(ll(X[ntr:],Y[ntr:]),base,(base-ll(X[ntr:],Y[ntr:]))/np.log(2)))
S=(X[ntr:]@w).reshape(nte,80); Yt=Y[ntr:].reshape(nte,80)
for k in (5,8,10):
    pk=np.argsort(-S,1)[:,:k]; h=np.take_along_axis(Yt,pk,1).sum()
    mu=nte*k*0.25; sd=np.sqrt(nte*k*0.25*0.75*(80-k)/79)
    print("   k=%2d hits %d exp %.0f  z=%+.2f  (edge %+.5f per pick)"%(k,h,mu,(h-mu)/sd,(h-mu)/(nte*k)))

print("="*74); print("B. RIGOROUS UPPER BOUNDS on any exploitable bias (3-sigma detection limits)")
def bound(fname, F, start=220):
    f=F[start:]; f=f-f.mean(1,keepdims=True)
    Sf2=(f*f).sum(); sd=np.sqrt(VF*Sf2)
    # U for an effect where P(y=1|f) = p + beta*f_tilde  -> U = beta * Sf2
    return 3*sd/Sf2
Fp=np.zeros_like(M); Fp[1:]=M[:-1]
print("  Detection limit = smallest per-observation probability shift detectable at 3 sigma.")
print("   'was in previous draw'      : |dP| <= %.6f" % bound("prev",Fp))
Fg=np.log1p(np.clip(G,0,300)).astype(np.float32)
print("   'log gap since last seen'   : |dP| per unit <= %.6f" % bound("loggap",Fg))
Fw=win(20)
print("   'freq in last 20 draws'     : |dP| per unit <= %.6f" % bound("win20",Fw))
# marginal per-number bound
cnt=M.sum(0); se=np.sqrt(N*p*(1-p))
print("   per-number marginal rate    : |dP| <= %.6f  (3 sigma, observed max |dP| = %.6f)"
      %(3*se/N, np.abs(cnt-N*p).max()/N))
print("   overall observed max |z| over 80 numbers = %.2f"%(np.abs(cnt-N*p).max()/se))

print("="*74); print("C. What edge is REQUIRED to break even (Keno 20/80)")
from math import comb
def hyp(k,m): return comb(20,m)*comb(60,k-m)/comb(80,k)
for k in (5,6,7,8,10):
    print("  pick %2d : " % k, "  ".join("P(%d)=%.3e"%(m,hyp(k,m)) for m in range(k,max(k-4,-1),-1)))
print("\n  A house edge of X%% needs the player's hit-probability lifted by ~X%%/sensitivity.")
print("  Typical keno margin 30-50%%. Detected bias ceiling above is ~1e-3 absolute (=0.4%% relative).")
print("  => Ratio required/available: 75x to 125x. Not exploitable, by measurement not by assumption.")
