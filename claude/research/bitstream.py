import numpy as np, zlib, lzma, bz2
from math import comb, erfc, sqrt, log
from load import load
ids, ts, nums, boost, bonus = load()
N=len(ids)
CT=[[comb(n,k) if n>=k else 0 for k in range(21)] for n in range(81)]
nn=nums.astype(int)
rank=np.zeros(N,dtype=object)
for k in range(20): rank += np.array([CT[v-1][k+1] for v in nn[:,k]],dtype=object)
TOT=comb(80,20); B=61; LIM=1<<B
keep=[int(r) for r in rank if int(r)<LIM]
print("colex ranks: %d total, %d < 2^61 kept (%.4f, expect %.4f) -> %d bits"
      % (N,len(keep),len(keep)/N, LIM/TOT, len(keep)*B))
bits=np.zeros(len(keep)*B,dtype=np.uint8)
for i,r in enumerate(keep):
    for b in range(B): bits[i*B+b]=(r>>(B-1-b))&1
n=len(bits); print("stream n = %d bits"%n)

def P(x): return erfc(abs(x)/sqrt(2))
print("\n--- NIST-style battery ---")
s=2*bits.astype(np.int64)-1; S=s.sum()
print("1 monobit            : ones=%.6f  z=%+.3f  p=%.4f"%(bits.mean(), S/sqrt(n), P(S/sqrt(n))))
Mb=20000; Nb=n//Mb
pi=bits[:Nb*Mb].reshape(Nb,Mb).mean(1)
chi=4*Mb*((pi-0.5)**2).sum()
print("2 block-frequency    : blocks=%d chi2=%.1f df=%d z=%+.3f"%(Nb,chi,Nb,(chi-Nb)/sqrt(2*Nb)))
V=int((bits[1:]!=bits[:-1]).sum())+1; pih=bits.mean()
z=(V-2*n*pih*(1-pih))/(2*sqrt(n)*pih*(1-pih))
print("3 runs               : V=%d z=%+.3f p=%.4f"%(V,z,P(z)))
# longest run of ones in 10^4-bit blocks (just report max run)
d=np.diff(np.concatenate([[0],bits,[0]]));st=np.where(d==1)[0];en=np.where(d==-1)[0]
print("4 longest run of 1s  : %d  (expect ~%.1f)"%((en-st).max(), np.log2(n)))
# binary matrix rank 32x32 over GF(2)
Q=32; nm=n//(Q*Q); rk=np.zeros(nm,dtype=int)
bb=bits[:nm*Q*Q].reshape(nm,Q,Q)
for i in range(nm):
    A=bb[i].copy(); r=0
    for c in range(Q):
        pv=np.nonzero(A[r:,c])[0]
        if len(pv)==0: continue
        A[[r,r+pv[0]]]=A[[r+pv[0],r]]
        rows=np.nonzero(A[:,c])[0]; rows=rows[rows!=r]
        A[rows]^=A[r]; r+=1
        if r==Q: break
    rk[i]=r
c32=(rk==32).sum(); c31=(rk==31).sum(); c30=(rk<=30).sum()
e=np.array([0.2888,0.5776,0.1336])*nm
chi=((np.array([c32,c31,c30])-e)**2/e).sum()
print("5 binary matrix rank : n=%d  [32,31,<=30]=[%d,%d,%d] exp=[%.0f,%.0f,%.0f] chi2=%.2f (df2)"%(nm,c32,c31,c30,e[0],e[1],e[2],chi))
# DFT spectral
f=np.abs(np.fft.rfft(s))[:n//2]; T=sqrt(log(1/0.05)*n); N0=0.95*n/2; N1=(f<T).sum()
dz=(N1-N0)/sqrt(n*0.95*0.05/4)
print("6 DFT spectral       : below-T=%d expect=%.0f z=%+.3f p=%.4f"%(N1,N0,dz,P(dz)))
# serial / approximate entropy m=10
for m in (8,12,16):
    v=np.zeros(n,dtype=np.int64)
    for i in range(m): v=(v<<1)|np.roll(bits,-i)
    c=np.bincount(v[:n],minlength=1<<m).astype(float)
    chi=((c-n/(1<<m))**2/(n/(1<<m))).sum()
    print("7 serial m=%-2d        : chi2=%.1f df=%d z=%+.3f"%(m,chi,(1<<m)-1,(chi-((1<<m)-1))/sqrt(2*((1<<m)-1))))
# cumulative sums
cu=np.cumsum(s); print("8 cusum              : max|S|=%d  (expect ~%.0f)"%(np.abs(cu).max(), 1.6*sqrt(n)))
# linear complexity (Berlekamp-Massey) on blocks of 5000
def bm(seq):
    n_=len(seq); c=np.zeros(n_,dtype=np.int8); b=np.zeros(n_,dtype=np.int8); c[0]=b[0]=1
    L=0;m=-1
    for N_ in range(n_):
        d=seq[N_]
        for i in range(1,L+1): d^=c[i]&seq[N_-i]
        if d==1:
            t=c.copy()
            for i in range(n_-(N_-m)): c[N_-m+i]^=b[i]
            if L<=N_//2: L=N_+1-L; m=N_; b=t
    return L
Mlc=5000; nlc=min(120, n//Mlc); Ls=[bm(bits[i*Mlc:(i+1)*Mlc].astype(np.int8)) for i in range(nlc)]
Ls=np.array(Ls); mu=Mlc/2+ (4+((-1)**(Mlc+1)))/18
print("9 linear complexity  : blocks=%d  mean L=%.2f  expect %.2f  sd_obs=%.2f  z=%+.3f"
      %(nlc,Ls.mean(),mu,Ls.std(),(Ls.mean()-mu)/(Ls.std()/sqrt(nlc)+1e-9)))
# compression
raw=np.packbits(bits).tobytes()
print("\n--- compression (raw = %d bytes) ---"%len(raw))
for nm_,f_ in [("zlib-9",lambda b: zlib.compress(b,9)),("bz2-9",lambda b: bz2.compress(b,9)),("lzma",lambda b: lzma.compress(b))]:
    c_=f_(raw); print("   %-7s -> %d bytes  ratio=%.6f  (excess %.4f%%)"%(nm_,len(c_),len(c_)/len(raw),100*(len(c_)/len(raw)-1)))
