import numpy as np, subprocess, os
from math import comb
N=70560
def fy_stream(nextu, n=N):
    out=np.zeros((n,20),dtype=np.int8)
    for t in range(n):
        a=list(range(1,81))
        for i in range(20):
            j=i+ (nextu()*(80-i))//(1<<32)
            a[i],a[j]=a[j],a[i]
        out[t]=sorted(a[:20])
    return out
class XS32:
    def __init__(s,seed): s.x=seed
    def __call__(s):
        x=s.x; x^= (x<<13)&0xffffffff; x^= x>>17; x^=(x<<5)&0xffffffff; s.x=x; return x
class MINSTD:
    def __init__(s,seed): s.x=seed
    def __call__(s): s.x=(16807*s.x)%2147483647; return (s.x<<1)&0xffffffff
rng=np.random.default_rng(12345)
class STRONG:
    def __init__(s): s.buf=[]; 
    def __call__(s):
        if not s.buf: s.buf=list(rng.integers(0,1<<32,size=100000,dtype=np.uint64))
        return int(s.buf.pop())
print("generating 3 synthetic archives (70560 draws each)...")
SETS={"xorshift32(weak,2^32 state)":fy_stream(XS32(0xDEADBEEF)),
      "minstd(weak,2^31 state)":fy_stream(MINSTD(123456789)),
      "PCG64(strong)":fy_stream(STRONG())}
from load import load
ids,ts,nums,boost,bonus=load(); SETS["REAL Loto Express"]=nums

def indic(nn):
    n=nn.shape[0]; M=np.zeros((n,80),np.float64); M[np.repeat(np.arange(n),20),nn.reshape(-1)-1]=1; return M
p=0.25; p2=(20*19)/(80.*79); VF=p*(1-p)-(p2-p*p)
print("\n%-30s %8s %8s %8s %8s"%("archive","chi2 z","lag1 z","maxlag z","seedhunt"))
for name,nn in SETS.items():
    M=indic(nn); n=M.shape[0]
    c=M.sum(0); chi=(((c-n*p)**2).sum()/(n*p*(1-p)) - 80)/np.sqrt(2*80)
    F=np.zeros_like(M); F[1:]=M[:-1]; f=F[220:]-F[220:].mean(1,keepdims=True); y=M[220:]
    z1=(f*(y-p)).sum()/np.sqrt(VF*(f*f).sum())
    X=M-p; n2=1<<int(np.ceil(np.log2(2*n)))
    Fx=np.fft.rfft(X,n=n2,axis=0); ac=np.fft.irfft(Fx*np.conj(Fx),n=n2,axis=0)[:n].sum(1)
    L=np.arange(n); ov=ac/(n-L)+5.0
    zl=(ov-5.)/(np.sqrt(20*.25*.75*60/79)/np.sqrt(n-L)); zl=np.abs(zl[1:50000]).max()
    # write bin & run seedhunt on this archive
    lo=np.zeros(n,np.uint64); hi=np.zeros(n,np.uint64)
    for j in range(20):
        v=nn[:,j].astype(np.int64)-1; m=v<64
        lo[m]|=(np.uint64(1)<<v[m].astype(np.uint64)); hi[~m]|=(np.uint64(1)<<(v[~m]-64).astype(np.uint64))
    with open("cal.bin","wb") as f:
        f.write(np.uint32(n).tobytes()); f.write(np.arange(n,dtype=np.uint32).tobytes())
        f.write(np.zeros(n,np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
        f.write(nn.astype(np.uint8).tobytes()); f.write(np.ones(n,np.uint8).tobytes()); f.write(np.ones(n,np.uint8).tobytes())
    os.replace("cal.bin","draws_cal.bin")
    print("%-30s %+8.2f %+8.2f %8.2f  (see below)"%(name,chi,z1,zl))
np.save("calib_sets.npy", np.array([v for v in SETS.values()],dtype=np.int8))
print("\nsynthetic archives saved; running seedhunt against the weak ones next")
