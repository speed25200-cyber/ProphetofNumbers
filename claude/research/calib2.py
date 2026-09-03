import numpy as np, os
S=np.load("calib_sets.npy")
names=["xorshift32","minstd","pcg64_strong","REAL"]
for k,nm in enumerate(names):
    nn=S[k].astype(np.int64); n=nn.shape[0]
    lo=np.zeros(n,np.uint64); hi=np.zeros(n,np.uint64)
    for j in range(20):
        v=nn[:,j]-1; m=v<64
        lo[m]|=(np.uint64(1)<<v[m].astype(np.uint64)); hi[~m]|=(np.uint64(1)<<(v[~m]-64).astype(np.uint64))
    with open("cal_%s.bin"%nm,"wb") as f:
        f.write(np.uint32(n).tobytes()); f.write(np.arange(n,dtype=np.uint32).tobytes())
        f.write(np.zeros(n,np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
        f.write(nn.astype(np.uint8).tobytes()); f.write(np.ones(n,np.uint8).tobytes()); f.write(np.ones(n,np.uint8).tobytes())
    print("wrote cal_%s.bin"%nm)
