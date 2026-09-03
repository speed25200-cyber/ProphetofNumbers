import numpy as np, hashlib, struct, datetime, itertools, sys
from math import comb
from load import load
ids, ts, nums, boost, bonus = load()
N=len(ids)
TRUE=[frozenset(nums[i].tolist()) for i in range(N)]
C8020=comb(80,20)
CT=[[comb(n,k) if n>=k else 0 for k in range(21)] for n in range(81)]

def unrank_colex(r):
    out=[]
    for k in range(20,0,-1):
        n=k-1
        while n+1<=80 and CT[n+1][k]<=r: n+=1
        out.append(n+1); r-=CT[n][k]
    return frozenset(out)

def fy_bytes(d, mod='pair'):          # Fisher-Yates driven by digest byte stream
    a=list(range(1,81)); out=[]; p=0
    for i in range(20):
        k=80-i
        if p+2>len(d): d=d+hashlib.sha256(d).digest(); 
        v=(d[p]<<8)|d[p+1]; p+=2
        j=i+(v%k); a[i],a[j]=a[j],a[i]; out.append(a[i])
    return frozenset(out)
def fy_words(d, mulhi=True):
    a=list(range(1,81)); out=[]; p=0
    for i in range(20):
        k=80-i
        if p+4>len(d): d=d+hashlib.sha256(d).digest()
        u=int.from_bytes(d[p:p+4],'big'); p+=4
        j=i+(((u*k)>>32) if mulhi else (u%k)); a[i],a[j]=a[j],a[i]; out.append(a[i])
    return frozenset(out)
def rej_bytes(d):
    s=[]; p=0; dd=d
    while len(s)<20:
        if p>=len(dd): dd=dd+hashlib.sha256(dd).digest()
        b=dd[p]; p+=1
        if b>=240: continue
        v=b%80+1
        if v not in s: s.append(v)
    return frozenset(s)
def bigint_colex(d):
    return unrank_colex(int.from_bytes(d,'big')%C8020)

DERIV=[("fy_bytes",fy_bytes),("fy_words_mulhi",lambda d:fy_words(d,True)),
       ("fy_words_mod",lambda d:fy_words(d,False)),("rej_bytes",rej_bytes),
       ("bigint_colex",bigint_colex)]
HASH=[("md5",hashlib.md5),("sha1",hashlib.sha1),("sha256",hashlib.sha256),
      ("sha512",hashlib.sha512),("sha3_256",hashlib.sha3_256),("blake2b",hashlib.blake2b)]

def inputs(i):
    I=int(ids[i]); T=int(ts[i]); idx=I-1309614
    dtu=datetime.datetime.utcfromtimestamp(T)
    yield "id",            str(I).encode()
    yield "idx",           str(idx).encode()
    yield "ts",            str(T).encode()
    yield "tsms",          str(T*1000).encode()
    yield "id_ts",         ("%d-%d"%(I,T)).encode()
    yield "le_id",         struct.pack("<I",I)
    yield "be_id",         struct.pack(">I",I)
    yield "be_ts",         struct.pack(">I",T)
    yield "be_id_ts",      struct.pack(">II",I,T)
    yield "lotoexpress_id",("lotoexpress:%d"%I).encode()
    yield "loro_id",       ("loro%d"%I).encode()
    yield "iso",           dtu.strftime("%Y-%m-%dT%H:%M:%SZ").encode()
    yield "date_draw",     dtu.strftime("%Y%m%d").encode()+str(I).encode()

TEST=[0,1,2,3,7,100,1000,5000,20000,50000,70559]
best={}
for hn,hf in HASH:
    for inm,_ in inputs(0):
        for dn,df in DERIV:
            hitmax=0
            for i in TEST:
                inp=dict(inputs(i))[inm]
                try: cand=df(hf(inp).digest())
                except Exception: cand=frozenset()
                h=len(cand & TUP) if False else len(cand & TRUE[i])
                hitmax=max(hitmax,h)
                if h>=15: print("  !! STRONG %s/%s/%s draw %d : %d/20"%(hn,inm,dn,i,h))
            best[(hn,inm,dn)]=hitmax
srt=sorted(best.items(), key=lambda kv:-kv[1])
print("schemes tested: %d   (each on 11 real draws)"%len(best))
print("best overlaps (max over draws; 20 = total break, ~9-10 = chance):")
for k,v in srt[:12]: print("   %-9s %-15s %-15s  %2d/20"%(k[0],k[1],k[2],v))
print("median best = %.1f  |  none >= 15: %s"%(np.median(list(best.values())), all(v<15 for v in best.values())))
