import numpy as np
from load import load, indicator
rng = np.random.default_rng(7)
ids, ts, nums, boost, bonus = load()
N=len(ids); M = indicator(nums).astype(np.float32)

def build_features(M, ts, boost, bonus, start=2000):
    N,K = M.shape
    cs = np.cumsum(M, axis=0)
    def win(w):                      # count of each number in the w draws before t
        out = np.zeros_like(M)
        out[w:] = cs[w-1:-1] - np.concatenate([np.zeros((1,K),np.float32), cs[:-w-1]])
        return out
    F = []
    names=[]
    for w in (1,2,3,5,10,20,50,100,400,2000):
        F.append(win(w)/w); names.append("cnt%d"%w)
    # gap since last appearance
    gap = np.zeros_like(M); last = np.full(K, -1.0, dtype=np.float32)
    G = np.zeros_like(M)
    lastseen = np.full(K,-1000.0)
    for t in range(N):
        G[t] = t - lastseen
        lastseen = np.where(M[t]>0, t, lastseen)
    G = np.clip(G, 0, 200)
    F.append(np.log1p(G)); names.append("loggap")
    # co-occurrence score with previous draw (train-side co-matrix computed on first 40k only)
    CO = (M[:40000].T @ M[:40000]); np.fill_diagonal(CO,0)
    COn = CO/ (M[:40000].sum(0)[:,None]+1e-9)
    prev = np.zeros_like(M); prev[1:] = M[:-1]
    F.append(prev @ COn.astype(np.float32)/20.0); names.append("coprev")
    F.append(prev); names.append("prev")
    p2 = np.zeros_like(M); p2[2:] = M[:-2]; F.append(p2); names.append("prev2")
    tod = ((ts % 86400)/86400.0).astype(np.float32)
    F.append(np.repeat(np.sin(2*np.pi*tod)[:,None],K,1)); names.append("sin_tod")
    F.append(np.repeat(np.cos(2*np.pi*tod)[:,None],K,1)); names.append("cos_tod")
    pb = np.zeros(N,np.float32); pb[1:]=boost[:-1]
    F.append(np.repeat(pb[:,None],K,1)); names.append("prevboost")
    bo = np.zeros_like(M); bo[np.arange(1,N), bonus[:-1]-1]=1; names.append("prevbonus"); F.append(bo)
    X = np.stack(F, axis=-1)          # (N,80,f)
    return X[start:], M[start:], names

X, Y, names = build_features(M, ts, boost, bonus)
T = X.shape[0]
X = X.reshape(-1, X.shape[-1]); Y = Y.reshape(-1)
mu, sd = X.mean(0), X.std(0)+1e-9
X = (X-mu)/sd
print("rows=%d  feats=%d  %s" % (len(Y), X.shape[1], names))

ntr = 55000*80          # first 55000 draws (after offset) for train
Xtr,Ytr = X[:ntr], Y[:ntr]; Xte,Yte = X[ntr:], Y[ntr:]
nte_draws = (len(Y)-ntr)//80
print("train draws=%d  test draws=%d" % (ntr//80, nte_draws))

def fit(Xt, Yt, lam=1.0, iters=300, lr=0.5):
    n,d = Xt.shape; w = np.zeros(d); b = np.log(0.25/0.75)
    for it in range(iters):
        z = Xt@w + b; p = 1/(1+np.exp(-z)); g = (p-Yt)
        gw = Xt.T@g/n + lam*w/n; gb = g.mean()
        w -= lr*gw*10; b -= lr*gb*10
    return w,b
w,b = fit(Xtr,Ytr)
print("\nweights (|w| desc):")
for i in np.argsort(-np.abs(w))[:8]:
    print("   %-10s %+.5f" % (names[i], w[i]))

def logloss(X_,Y_,w,b):
    z = X_@w+b; p=1/(1+np.exp(-z)); p=np.clip(p,1e-9,1-1e-9)
    return -(Y_*np.log(p)+(1-Y_)*np.log(1-p)).mean()
base = -(0.25*np.log(0.25)+0.75*np.log(0.75))
print("\nOUT-OF-SAMPLE  (last %d draws)" % nte_draws)
print("  baseline logloss = %.6f" % base)
print("  model    logloss = %.6f   gain = %+.3e bits/obs" % (logloss(Xte,Yte,w,b), (base-logloss(Xte,Yte,w,b))/np.log(2)))
print("  in-sample gain   = %+.3e bits/obs" % ((base-logloss(Xtr,Ytr,w,b))/np.log(2)))

S = (Xte@w).reshape(nte_draws,80); Yt2 = Yte.reshape(nte_draws,80)
print("\n  top-k pick performance on held-out draws:")
for k in (5,6,7,8,10,15,20):
    pick = np.argsort(-S, axis=1)[:,:k]
    hits = np.take_along_axis(Yt2, pick, 1).sum()
    mean = nte_draws*k*0.25
    var  = nte_draws*(k*0.25*0.75*(80-k)/79)
    print("    k=%2d hits=%7d  expected=%9.1f  z=%+6.2f   hits/draw=%.4f vs %.4f"
          % (k, hits, mean, (hits-mean)/np.sqrt(var), hits/nte_draws, k*0.25))
    # anti-pick (worst k) as control
    pick2 = np.argsort(S, axis=1)[:,:k]
    h2 = np.take_along_axis(Yt2, pick2, 1).sum()
    print("       anti-pick hits=%7d z=%+6.2f" % (h2, (h2-mean)/np.sqrt(var)))
