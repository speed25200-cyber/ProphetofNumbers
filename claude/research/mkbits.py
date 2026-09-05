"""Emit every observable bit stream, one byte per bit, for Berlekamp-Massey.

A stream is worth testing when the bit could plausibly be an F2-linear functional of a
generator state. Under the unranking hypothesis the rank's low 4 bits are exactly the
generator output's low 4 bits (v2(C(80,20)) = 4, so the unknown multiple of C never
reaches them) — those are the cleanest. The bonus and boost channels are the ones the
earlier attacks used, retested here without any assumption about how they are mapped.
"""
import numpy as np
from load import load

ids, ts, nums, boost, bonus = load()
N = len(ids)
out = {}

for conv in ("colex0", "lex0", "colex1"):
    r = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64)
    for b in range(4):                       # only 4: v2(C)=4 bounds what is k-free
        out["rank_%s_bit%d" % (conv, b)] = ((r >> np.uint64(b)) & np.uint64(1)).astype(np.uint8)

bo = (bonus.astype(np.int64) - 1)            # 0..79
for b in range(7):
    out["bonus_bit%d" % b] = ((bo >> b) & 1).astype(np.uint8)

# bonus as a rank inside the sorted draw (0..19) — the other reading of that column
pos = np.full(N, -1, dtype=np.int64)
for j in range(20):
    pos = np.where(nums[:, j] == bonus, j, pos)
ok = pos >= 0
print("bonus is one of the 20 drawn numbers in %d/%d draws" % (ok.sum(), N))
for b in range(5):
    out["bonusrank_bit%d" % b] = ((np.where(ok, pos, 0) >> b) & 1).astype(np.uint8)

bs = boost.astype(np.int64)
for b in range(3):
    out["boost_bit%d" % b] = ((bs >> b) & 1).astype(np.uint8)

# low bit of each sorted position: not a clean functional, but free to test
for j in (0, 9, 19):
    out["pos%d_bit0" % j] = (nums[:, j].astype(np.int64) & 1).astype(np.uint8)

for k, v in out.items():
    assert v.shape[0] == N and v.max() <= 1
    v.tofile("bits_%s.bin" % k)
print("wrote %d streams of %d bits each" % (len(out), N))

# --- the complementary channel, for the mulhi reduction ---------------------------
# Under u mod C the LOW 4 bits of u are k-free (v2(C)=4) and the high bits are not.
# Under mulhi it is the other way round: r = floor(u*C/2^64) pins u to an interval of
# about 5.2 integers, so every bit above position ~3 is determined — and above position
# 32 the chance the interval straddles a carry is 5.2/2^32, i.e. 8e-5 expected errors
# across the whole archive. Those planes are exact linear functionals of u, which is
# what Berlekamp-Massey needs, so the F2-linear exclusion covers this reduction too.
import math as _m
C = _m.comb(80, 20)
hi = {}
for conv in ("colex0", "lex0", "comp0"):
    r = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64)
    a = np.array([( (int(x) << 64) + C - 1 ) // C for x in r], dtype=object)   # ceil(r*2^64/C)
    a = np.array([int(v) & ((1 << 64) - 1) for v in a], dtype=np.uint64)
    for b in (32, 40, 48, 56, 63):
        hi["mulhi_%s_bit%d" % (conv, b)] = ((a >> np.uint64(b)) & np.uint64(1)).astype(np.uint8)
for k, v in hi.items():
    v.tofile("bits_%s.bin" % k)
print("wrote %d high bit planes for the mulhi reduction" % len(hi))
