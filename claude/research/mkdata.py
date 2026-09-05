import numpy as np
from load import load
ids, ts, nums, boost, bonus = load()
N=len(ids)
lo = np.zeros(N, dtype=np.uint64); hi = np.zeros(N, dtype=np.uint64)
for j in range(20):
    v = nums[:,j].astype(np.int64)-1
    m = v < 64
    lo[m] |= (np.uint64(1) << v[m].astype(np.uint64))
    hi[~m] |= (np.uint64(1) << (v[~m]-64).astype(np.uint64))
with open("draws.bin","wb") as f:
    f.write(np.uint32(N).tobytes())
    f.write(ids.astype(np.uint32).tobytes())
    f.write(ts.astype(np.uint32).tobytes())
    f.write(lo.tobytes()); f.write(hi.tobytes())
    f.write(nums.astype(np.uint8).tobytes())
    f.write(boost.astype(np.uint8).tobytes()); f.write(bonus.astype(np.uint8).tobytes())
print("wrote draws.bin  N=",N)
