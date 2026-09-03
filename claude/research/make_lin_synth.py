"""SYNTHETIC archive from xorshift64 (hi-32 output) to validate lin_break.

Not Loto Express data. Layout: 20 Fisher-Yates indices then one boost word (W=21),
bonus = the first ball drawn. lin_break gen 0 mode 0 W 21 must come out CONSISTENT.
"""
import numpy as np, sys
M64 = (1 << 64) - 1
CUM = [0.512, 0.750, 0.900, 0.950, 0.975, 1.0]; VAL = [1, 2, 3, 4, 5, 10]

class XS64:
    def __init__(s, x): s.x = x & M64
    def next(s):
        x = s.x
        x ^= (x << 13) & M64
        x ^= x >> 7
        x ^= (x << 17) & M64
        s.x = x
        return x >> 32                      # hi 32 bits

D = int(sys.argv[1]) if len(sys.argv) > 1 else 300
g = XS64(0x0123456789ABCDEF)
for _ in range(97): g.next()                # unknown warm-up

nums = np.zeros((D, 20), np.uint8); boost = np.zeros(D, np.uint8); bonus = np.zeros(D, np.uint8)
for d in range(D):
    a = list(range(1, 81)); row = []
    for i in range(20):
        u = g.next(); j = i + ((u * (80 - i)) >> 32)
        a[i], a[j] = a[j], a[i]; row.append(a[i])
    x = g.next() / 2**32
    boost[d] = VAL[next(k for k, c in enumerate(CUM) if x < c)]
    bonus[d] = row[0]
    nums[d] = sorted(row)

lo = np.zeros(D, np.uint64); hi = np.zeros(D, np.uint64)
for j in range(20):
    v = nums[:, j].astype(np.int64) - 1; m = v < 64
    lo[m] |= (np.uint64(1) << v[m].astype(np.uint64))
    hi[~m] |= (np.uint64(1) << (v[~m] - 64).astype(np.uint64))
with open("draws_lin.bin", "wb") as f:
    f.write(np.uint32(D).tobytes()); f.write(np.arange(D, dtype=np.uint32).tobytes())
    f.write(np.zeros(D, np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
    f.write(nums.tobytes()); f.write(boost.tobytes()); f.write(bonus.tobytes())
print("wrote draws_lin.bin : %d synthetic draws, xorshift64(hi32), W=21, bonus=first ball" % D)
