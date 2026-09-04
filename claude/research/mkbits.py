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
