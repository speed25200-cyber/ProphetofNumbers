"""SYNTHETIC archive for validating channel_break — not Loto Express data.

Layout generated: per draw the stream emits
    r=0..19  the 20 Fisher-Yates indices (so the first ball is bonus)
    r=20     the boost, from the thresholds reconstructed from the real archive
    r=21     one unused word
so W=22, bonus = first ball drawn, boost at r=20. channel_break mode 0 W 22 must
find the alignment and reach rank 19937.
"""
import numpy as np, sys

class MT:
    def __init__(s, seed):
        s.mt=[0]*624; s.mt[0]=seed
        for i in range(1,624): s.mt[i]=(1812433253*(s.mt[i-1]^(s.mt[i-1]>>30))+i)&0xffffffff
        s.i=624
    def next(s):
        if s.i>=624:
            for k in range(624):
                y=(s.mt[k]&0x80000000)|(s.mt[(k+1)%624]&0x7fffffff)
                s.mt[k]=s.mt[(k+397)%624]^(y>>1)^(0x9908b0df if y&1 else 0)
            s.i=0
        y=s.mt[s.i]; s.i+=1
        y^=y>>11; y^=(y<<7)&0x9d2c5680; y&=0xffffffff
        y^=(y<<15)&0xefc60000; y&=0xffffffff; y^=y>>18
        return y

CUM=[0.512,0.750,0.900,0.950,0.975,1.0]; VAL=[1,2,3,4,5,10]
D=int(sys.argv[1]) if len(sys.argv)>1 else 6000
SKIP=int(sys.argv[2]) if len(sys.argv)>2 else 173
g=MT(0x51D0BEEF)
for _ in range(SKIP): g.next()          # unknown alignment, hidden from the tool

nums=np.zeros((D,20),np.uint8); boost=np.zeros(D,np.uint8); bonus=np.zeros(D,np.uint8)
for d in range(D):
    a=list(range(1,81)); row=[]
    for i in range(20):
        u=g.next(); j=i+((u*(80-i))>>32)
        a[i],a[j]=a[j],a[i]; row.append(a[i])
    u=g.next(); x=u/2**32
    boost[d]=VAL[next(k for k,c in enumerate(CUM) if x<c)]
    g.next()                            # the unused 22nd word
    bonus[d]=row[0]                     # bonus IS the first ball drawn
    nums[d]=sorted(row)

lo=np.zeros(D,np.uint64); hi=np.zeros(D,np.uint64)
for j in range(20):
    v=nums[:,j].astype(np.int64)-1; m=v<64
    lo[m]|=(np.uint64(1)<<v[m].astype(np.uint64)); hi[~m]|=(np.uint64(1)<<(v[~m]-64).astype(np.uint64))
with open("draws_synth.bin","wb") as f:
    f.write(np.uint32(D).tobytes()); f.write(np.arange(D,dtype=np.uint32).tobytes())
    f.write(np.zeros(D,np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
    f.write(nums.tobytes()); f.write(boost.tobytes()); f.write(bonus.tobytes())
print("wrote draws_synth.bin : %d synthetic draws, W=22, bonus=first ball, skip=%d" % (D,SKIP))
