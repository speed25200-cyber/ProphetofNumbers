"""SYNTHETIC archive validating the modulo variants of channel_break — not real data.

Layout: 20 Fisher-Yates indices taken with j = i + u % (80-i), then one boost word
(W=21); bonus = the first ball drawn, so bonus-1 = u % 80 and only the LOW four bits
of u are pinned. channel_break mode 6 W 21 must be CONSISTENT and mode 0 must reject.
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
D=int(sys.argv[1]) if len(sys.argv)>1 else 7000
g=MT(0x0DDBA11); [g.next() for _ in range(59)]

nums=np.zeros((D,20),np.uint8); boost=np.zeros(D,np.uint8); bonus=np.zeros(D,np.uint8)
for d in range(D):
    a=list(range(1,81)); row=[]
    for i in range(20):
        u=g.next(); j=i + u % (80-i)          # modulo mapping, not mulhi
        a[i],a[j]=a[j],a[i]; row.append(a[i])
    x=g.next()/2**32
    boost[d]=VAL[next(k for k,c in enumerate(CUM) if x<c)]
    bonus[d]=row[0]; nums[d]=sorted(row)

lo=np.zeros(D,np.uint64); hi=np.zeros(D,np.uint64)
for j in range(20):
    v=nums[:,j].astype(np.int64)-1; m=v<64
    lo[m]|=(np.uint64(1)<<v[m].astype(np.uint64)); hi[~m]|=(np.uint64(1)<<(v[~m]-64).astype(np.uint64))
with open("draws_synth2.bin","wb") as f:
    f.write(np.uint32(D).tobytes()); f.write(np.arange(D,dtype=np.uint32).tobytes())
    f.write(np.zeros(D,np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
    f.write(nums.tobytes()); f.write(boost.tobytes()); f.write(bonus.tobytes())
print("wrote draws_synth2.bin : %d synthetic draws, modulo mapping, W=21, bonus=first ball"%D)
