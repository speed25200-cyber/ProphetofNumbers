"""SYNTHETIC archives from xorshift128+ (V8) and xoshiro256+ — not real data.

These two have an F2-linear state update but an ADDITIVE output, so only bit 0 of the
output is exactly linear. Layout: j = i + u % (80-i) with u the low 32 bits of the
sum, one boost word after the twenty indices (W=21), bonus = the first ball drawn.
lin_break mode 9 (bit 0 only) must come out CONSISTENT for the matching generator and
reject the other one.

  python3 make_plus_synth.py xs128p | xoshiro256p  [ndraws]
"""
import numpy as np, sys
M64 = (1 << 64) - 1
CUM = [0.512, 0.750, 0.900, 0.950, 0.975, 1.0]; VAL = [1, 2, 3, 4, 5, 10]

class XS128P:                       # V8 Math.random core
    def __init__(s, a, b): s.s0 = a & M64; s.s1 = b & M64
    def next(s):
        s1 = s.s0; s0 = s.s1
        s.s0 = s0
        s1 ^= (s1 << 23) & M64
        s1 ^= s1 >> 17
        s1 ^= s0
        s1 ^= s0 >> 26
        s.s1 = s1
        return (s.s0 + s.s1) & M64

class XOSHIRO256P:
    def __init__(s, v): s.s = [x & M64 for x in v]
    def next(s):
        r = (s.s[0] + s.s[3]) & M64
        t = (s.s[1] << 17) & M64
        s.s[2] ^= s.s[0]; s.s[3] ^= s.s[1]; s.s[1] ^= s.s[2]; s.s[0] ^= s.s[3]
        s.s[2] ^= t
        s.s[3] = ((s.s[3] << 45) | (s.s[3] >> 19)) & M64
        return r

which = sys.argv[1] if len(sys.argv) > 1 else "xs128p"
D = int(sys.argv[2]) if len(sys.argv) > 2 else 900
g = XS128P(0x0123456789ABCDEF, 0xFEDCBA9876543210) if which == "xs128p" \
    else XOSHIRO256P([0x1234, 0xABCDEF, 0xDEADBEEFCAFE, 0x9E3779B97F4A7C15])
for _ in range(37): g.next()

nums = np.zeros((D, 20), np.uint8); boost = np.zeros(D, np.uint8); bonus = np.zeros(D, np.uint8)
for d in range(D):
    a = list(range(1, 81)); row = []
    for i in range(20):
        u = g.next() & 0xffffffff          # low 32 bits, then a modulo mapping
        j = i + u % (80 - i)
        a[i], a[j] = a[j], a[i]; row.append(a[i])
    x = (g.next() & 0xffffffff)/2**32
    boost[d] = VAL[next(k for k, c in enumerate(CUM) if x < c)]
    bonus[d] = row[0]; nums[d] = sorted(row)

lo = np.zeros(D, np.uint64); hi = np.zeros(D, np.uint64)
for j in range(20):
    v = nums[:, j].astype(np.int64) - 1; m = v < 64
    lo[m] |= (np.uint64(1) << v[m].astype(np.uint64))
    hi[~m] |= (np.uint64(1) << (v[~m] - 64).astype(np.uint64))
out = "draws_%s.bin" % which
with open(out, "wb") as f:
    f.write(np.uint32(D).tobytes()); f.write(np.arange(D, dtype=np.uint32).tobytes())
    f.write(np.zeros(D, np.uint32).tobytes()); f.write(lo.tobytes()); f.write(hi.tobytes())
    f.write(nums.tobytes()); f.write(boost.tobytes()); f.write(bonus.tobytes())
print("wrote %s : %d synthetic draws from %s, W=21, bonus = first ball" % (out, D, which))
