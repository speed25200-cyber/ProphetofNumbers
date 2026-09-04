"""Combinatorial unranking is the one architecture where SORTING LOSES NOTHING.

Every attack so far has been throttled by the same fact: the archive publishes the 20
numbers in ascending order, so the generator's output order — 89.6 bits per draw — is
destroyed, and only 4-6 bits of side channel survive.

But that assumes the generator produced an ORDER. A large class of real lottery
implementations does not shuffle at all: they draw one integer in [0, C(80,20)) and
*unrank* it into a combination. That is the textbook way to get a provably uniform
combination without a shuffle, and it is what you write if you want a draw to be
auditable from a single published number.

Under that architecture the sorted combination IS the generator output, in full:
C(80,20) = 3.54e18 = 2^61.6. Not 4 bits per draw — 61.6 bits per draw, with nothing
lost to sorting. Three consecutive values then pin an arbitrary LCG mod 2^64 in closed
form, with no assumption on the multiplier at all.

This computes the rank of every draw under the conventions an implementer could
plausibly use (lex / colex, 0-based / 1-based), and verifies each formula against
brute-force enumeration on small alphabets before trusting it on the archive.
"""
import numpy as np, math
from load import load

n_, k_ = 80, 20
TOT = math.comb(n_, k_)

def table(n, k):
    """C(a,b) for a<=n+1, b<=k+1.  Entries above 2^64 cannot be reached by a valid
    (subset, position) pair here, so they are parked at 0; the archive spot-check below
    recomputes real draws with big ints and would catch it if one ever were."""
    T = np.zeros((n + 2, k + 2), dtype=np.uint64)
    for a in range(n + 2):
        for b in range(k + 2):
            v = math.comb(a, b)
            T[a][b] = v if v < (1 << 64) else 0
    return T

def colex_rank(rows, T):
    """rows: (N,k) 0-based ascending.  rank = sum_i C(c_i, i+1)"""
    N, k = rows.shape
    r = np.zeros(N, dtype=np.uint64)
    for i in range(k):
        r += T[rows[:, i], i + 1]
    return r

def lex_rank(rows, T, n):
    """rows: (N,k) 0-based ascending.  Inner run-sum collapsed by hockey-stick:
       sum_{v=p+1}^{c-1} C(n-1-v, k-i-1) = C(n-1-p, k-i) - C(n-c, k-i)"""
    N, k = rows.shape
    r = np.zeros(N, dtype=np.uint64)
    prev = np.full(N, -1, dtype=np.int64)
    for i in range(k):
        c = rows[:, i].astype(np.int64)
        r += T[n - 1 - prev, k - i] - T[n - c, k - i]
        prev = c
    return r

# --- verify both formulas by brute force before touching the archive ---
from itertools import combinations
for (n, k) in ((5, 2), (7, 3), (9, 4), (12, 5)):
    T = table(n, k)
    combs = list(combinations(range(n), k))
    rows = np.array(combs, dtype=np.int64)
    lx = lex_rank(rows, T, n)
    assert list(lx) == list(range(len(combs))), "lex formula wrong at n=%d k=%d" % (n, k)
    cx = colex_rank(rows, T)
    order = sorted(range(len(combs)), key=lambda j: tuple(reversed(combs[j])))
    assert [int(cx[j]) for j in order] == list(range(len(combs))), "colex wrong n=%d k=%d" % (n, k)
print("rank formulas verified by brute force at n,k = (5,2) (7,3) (9,4) (12,5)")

ids, ts, nums, boost, bonus = load()
N = nums.shape[0]
print("draws: %d   C(80,20) = %d = 2^%.3f" % (N, TOT, math.log2(TOT)))

T80 = table(81, 21)
rows0 = nums.astype(np.int64) - 1          # 0-based, values 0..79
rows1 = nums.astype(np.int64)              # left 1-based, as if the alphabet were 0..80

# spot-check the vectorised ranks against exact big-int arithmetic on real draws
def colex_slow(row0):
    return sum(math.comb(int(c), i + 1) for i, c in enumerate(row0))
def lex_slow(row0, n=80, k=20):
    r = 0; prev = -1
    for i, c in enumerate(row0):
        for v in range(prev + 1, int(c)):
            r += math.comb(n - 1 - v, k - i - 1)
        prev = int(c)
    return r
chk = [0, 1, 7, 12345, N // 2, N - 1]
cx_v = colex_rank(rows0, T80); lx_v = lex_rank(rows0, T80, 80)
for j in chk:
    assert int(cx_v[j]) == colex_slow(rows0[j]), "colex mismatch at draw %d" % j
    assert int(lx_v[j]) == lex_slow(rows0[j]),   "lex mismatch at draw %d"   % j
print("vectorised ranks match exact big-int arithmetic on draws %s" % chk)

streams = {
    "colex0": colex_rank(rows0, T80),
    "lex0":   lex_rank(rows0, T80, 80),
    "colex1": colex_rank(rows1, T80),
}
for name, a in streams.items():
    a = a.astype(np.uint64)
    a.tofile("rank_%s.bin" % name)
    print("  %-7s min=%d max=%d  span/2^61.6=%.3f   -> rank_%s.bin" %
          (name, int(a.min()), int(a.max()), (int(a.max()) - int(a.min())) / TOT, name))

# sanity: under any fair scheme the rank must be uniform on [0,TOT)
a = streams["colex0"].astype(np.float64)
print("\nuniformity of the colex0 rank stream (the null says uniform on [0,C)):")
print("  mean/C = %.6f   (0.5)" % (a.mean() / TOT))
print("  sd/C   = %.6f   (%.6f)" % (a.std() / TOT, 1 / math.sqrt(12)))
h, _ = np.histogram(a / TOT, bins=64, range=(0, 1))
chi = ((h - N / 64.0) ** 2 / (N / 64.0)).sum()
print("  chi2 on 64 bins = %.1f (df 63)  z = %+.2f" % (chi, (chi - 63) / math.sqrt(2 * 63)))
