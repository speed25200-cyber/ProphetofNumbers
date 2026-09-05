import numpy as np
from load import load, indicator
from math import comb
ids, ts, nums, boost, bonus = load()
N=len(ids); M=indicator(nums).astype(np.float64)

print("="*74); print("E19  FULL LAG SCAN: mean overlap at EVERY lag 1..70559 (via FFT)")
X=M-0.25
n2=1<<(int(np.ceil(np.log2(2*N))))
Fx=np.fft.rfft(X,n=n2,axis=0)
ac=np.fft.irfft(Fx*np.conj(Fx),n=n2,axis=0)[:N].sum(1)   # sum over 80 numbers
L=np.arange(N); cnt=(N-L).astype(float)
ov = ac/cnt + 20*20/80.0*0 + 5.0*0
ov = ac/cnt + 5.0   # E[sum_j (M-.25)(M-.25)] + 5 = mean overlap
sd_single=np.sqrt(20*0.25*0.75*60/79)
z=(ov-5.0)/(sd_single/np.sqrt(cnt))
zz=z[1:60000]
print("  lags scanned: %d   sd of single overlap = %.4f"%(len(zz),sd_single))
print("  max |z| = %.3f at lag %d   (expect max ~%.2f for %d lags)"%(np.abs(zz).max(),int(np.abs(zz).argmax())+1,np.sqrt(2*np.log(len(zz))),len(zz)))
o=np.argsort(-np.abs(zz))[:8]
for i in o: print("     lag %6d  mean overlap %.5f  z=%+.3f"%(i+1,ov[i+1],zz[i]))
print("  #|z|>4 = %d (expect %.2f) ; #|z|>4.5 = %d (expect %.3f)"%((np.abs(zz)>4).sum(),len(zz)*6.3e-5,(np.abs(zz)>4.5).sum(),len(zz)*6.8e-6))

print("="*74); print("E20  BOOST channel (separate low-entropy output of the same generator)")
vals=[1,2,3,4,5,10]; c=np.array([(boost==v).sum() for v in vals]); f=c/N
print("  counts:",c.tolist()); print("  freq  :",np.round(f,6).tolist())
for guess,label in [([.512,.238,.15,.05,.025,.025],"512/238/150/50/25/25 per 1000"),
                    ([.5,.25,.15,.05,.025,.025],"500/250/..."),
                    ([525/1024,244/1024,154/1024,51/1024,25/1024,25/1024],"x/1024")]:
    g=np.array(guess); e=N*g; chi=((c-e)**2/e).sum()
    print("   vs %-28s chi2=%7.2f df=5  p~%.4f"%(label,chi,np.exp(-chi/2)))
b=boost.astype(float)
print("  serial: lag-1..8 z =", " ".join("%+.2f"%(np.corrcoef(b[:-L],b[L:])[0,1]*np.sqrt(N-L)) for L in range(1,9)))
# pair n-gram
code={1:0,2:1,3:2,4:3,5:4,10:5}
bc=np.array([code[x] for x in boost])
P2=np.bincount(bc[:-1]*6+bc[1:],minlength=36).reshape(6,6).astype(float)
E2=np.outer(P2.sum(1),P2.sum(0))/P2.sum()
print("  boost pair chi2 = %.2f  df=25  z=%+.2f"%(((P2-E2)**2/E2).sum(),(((P2-E2)**2/E2).sum()-25)/np.sqrt(50)))
P3=np.bincount((bc[:-2]*6+bc[1:-1])*6+bc[2:],minlength=216).astype(float)
E3=N*np.prod(np.meshgrid(f,f,f,indexing='ij'),axis=0).reshape(-1)
print("  boost triple chi2 = %.2f df=215 z=%+.2f"%(((P3-E3)**2/E3).sum(),(((P3-E3)**2/E3).sum()-215)/np.sqrt(430)))
# boost vs draw content
Z=((M-0.25).T@((b-b.mean())/b.std()))/np.sqrt(N*0.25*0.75)
print("  boost vs 80 numbers: sum z^2=%.1f (E=80) max|z|=%.2f"%((Z**2).sum(),np.abs(Z).max()))
# runs of identical boost
runs=1+int((bc[1:]!=bc[:-1]).sum()); pe=1-(f**2).sum()
print("  boost runs=%d expect=%.0f z=%+.2f"%(runs,1+(N-1)*pe,(runs-1-(N-1)*pe)/np.sqrt((N-1)*pe*(1-pe))))

print("="*74); print("E21  BONUS channel: is the bonus a separate uniform pick of 1..20?")
rank=np.argmax(nums==bonus[:,None].astype(np.int8),axis=1)
r2=np.bincount(rank[:-1]*20+rank[1:],minlength=400).reshape(20,20).astype(float)
E=np.outer(r2.sum(1),r2.sum(0))/r2.sum()
print("  bonus-rank pair chi2=%.1f df=361 z=%+.2f"%(((r2-E)**2/E).sum(),(((r2-E)**2/E).sum()-361)/np.sqrt(722)))
print("  bonus-rank vs boost chi2 done earlier (85.3/95) -> independent")
