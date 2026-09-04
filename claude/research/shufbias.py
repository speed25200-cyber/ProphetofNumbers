"""The two shuffle bugs that would actually hand over an edge.

Everything so far excludes generators. This asks a different question: if the operator
shuffles correctly but writes the shuffle WRONG — the two mistakes real code makes — the
numbers stop being equally likely, and that is precisely the exploitable bias we want.

  (1) the naive shuffle:  for i in 0..n-1: swap(a[i], a[random(n)])
      — random(n) over the whole array instead of the remaining tail. n^n orderings
        mapped onto n! permutations, so they cannot come out equal.

  (2) sort(() => Math.random() - 0.5)
      — an inconsistent comparator. The result depends on the sort algorithm and is
        wildly non-uniform in practice.

Both are simulated here to measure how large a marginal bias they would leave, so the
archive's own marginals can be compared against something concrete rather than against
"nothing".
"""
import numpy as np, math

n, k, T = 80, 20, 400000
rng = np.random.default_rng(11)

def naive_shuffle_counts(T):
    cnt = np.zeros(n, dtype=np.int64)
    a0 = np.arange(n)
    for _ in range(T):
        a = a0.copy()
        j = rng.integers(0, n, size=n)
        for i in range(n):
            a[i], a[j[i]] = a[j[i]], a[i]
        cnt[a[:k]] += 1
    return cnt

def bad_comparator_counts(T):
    """A merge sort driven by a coin-flip comparator, as JS engines do for larger arrays."""
    cnt = np.zeros(n, dtype=np.int64)
    def msort(x):
        if len(x) <= 1: return x
        m = len(x)//2
        L, R = msort(x[:m]), msort(x[m:])
        out = []; i = j = 0
        while i < len(L) and j < len(R):
            if rng.random() < 0.5: out.append(L[i]); i += 1
            else: out.append(R[j]); j += 1
        out.extend(L[i:]); out.extend(R[j:])
        return out
    for _ in range(T):
        a = msort(list(range(n)))
        for v in a[:k]: cnt[v] += 1
    return cnt

for name, fn, TT in (("naive shuffle", naive_shuffle_counts, T),
                     ("sort(random()-0.5)", bad_comparator_counts, 40000)):
    c = fn(TT)
    p = c / TT
    dev = p - k/n
    # what |z| would the archive show if the operator had this bug?
    N = 70560
    z = dev * N / math.sqrt(N * (k/n) * (1 - k/n))
    print("%-20s  max |P(v drawn) - 0.25| = %.5f   ->  archive would show max |z| = %.1f"
          % (name, np.abs(dev).max(), np.abs(z).max()))
    o = np.argsort(-np.abs(dev))[:5]
    print("                      worst numbers:", [(int(v)+1, round(float(dev[v]), 5)) for v in o])

print()
print("The archive's own marginals: max |z| = 2.72 over the 80 numbers, Sum z^2 = 71.46")
print("for an expectation of 80. Both bugs above would be far outside that.")
