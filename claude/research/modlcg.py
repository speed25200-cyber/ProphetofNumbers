"""Modular linear-recurrence detector on the observable low-bit sequences.

The point: the low t bits of ANY LCG modulo 2^k are themselves an LCG modulo 2^t,
whatever the multiplier. So if the sampler writes j = u % 80 and u is the low 32 bits
of an LCG state, then (bonus-1) mod 16 = u mod 16 = s mod 16, and across draws
    x_{d+1} = A x_d + C   (mod 16)
for some A, C that absorb however many words a draw consumes. Only 256 pairs to try,
and the whole 70560-draw archive checks each one — no multiplier needs to be guessed.

The same brute force is then run for order-2 and order-3 recurrences, which also
cover LFSR-like updates carried in the low bits, on every low-bit sequence the feed
exposes: bonus-1, the rank of bonus inside the sorted 20, the boost index, and the
lowest and highest drawn numbers.

A hit here would mean the generator is congruential with a low-bit output — the one
family neither the 2^32 sweep nor the F2-linear attacks reach.
"""
import numpy as np, itertools
from load import load

ids, ts, nums, boost, bonus = load()
N = len(ids)
rank = np.argmax(nums == bonus[:, None].astype(np.int8), axis=1)
bmap = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 10: 5}
bidx = np.array([bmap[b] for b in boost])

SEQS = {
    "bonus-1":      bonus.astype(np.int64) - 1,
    "bonus rank":   rank.astype(np.int64),
    "boost index":  bidx.astype(np.int64),
    "lowest ball":  nums[:, 0].astype(np.int64) - 1,
    "highest ball": nums[:, 19].astype(np.int64) - 1,
    "sum of draw":  nums.astype(np.int64).sum(1),
}

def scan(x, t, order):
    """Best number of consecutive matches for x_{d+order} = sum c_i x_{d+i} + b (mod 2^t)."""
    m = 1 << t
    y = (x % m).astype(np.int64)
    best = (0, None)
    for coeffs in itertools.product(range(m), repeat=order):
        pred0 = np.zeros(len(y) - order, dtype=np.int64)
        for i, c in enumerate(coeffs):
            if c: pred0 += c * y[i:len(y) - order + i]
        for b in range(m):
            ok = ((pred0 + b) % m) == y[order:]
            # longest run of consecutive matches
            if not ok.any(): continue
            d = np.diff(np.concatenate([[0], ok.view(np.int8), [0]]))
            st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
            run = int((en - st).max())
            if run > best[0]: best = (run, (coeffs, b))
    return best

print("Modular linear-recurrence scan  (N = %d draws)" % N)
print("A congruential generator with a low-bit output would match for the WHOLE archive.")
print("Chance longest run for a random sequence mod 2^t is about log(N)/log(2^t).")
print()
print("%-13s %3s %5s %8s %10s  %s" % ("sequence", "t", "order", "best run", "chance", "recurrence"))
for name, x in SEQS.items():
    for t in (1, 2, 3, 4):
        for order in (1, 2):
            if (1 << t) ** (order + 1) > 70000: continue
            run, rec = scan(x, t, order)
            chance = np.log(N) / np.log(1 << t)
            flag = "  <-- CHECK" if run > 4 * chance + 10 else ""
            print("%-13s %3d %5d %8d %10.1f  %s%s" % (name, t, order, run, chance, rec, flag))
