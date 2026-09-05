"""If the nightly restart reseeds from something low-entropy, the FIRST draw of each
block is where it shows — and it shows as a relationship BETWEEN blocks, which no
per-draw test can see.

358 block openings give 63 903 pairs. Under the null each pair overlaps hypergeometrically
(mean 5), and over that many pairs chance reaches 13. A shared or adjacent seed would put
a pair far above that, model-free — no need to guess which generator.

Three shapes are checked: every pair of openings, adjacent days specifically (a seed that
walks with the date), and openings against the closing draw of the previous block (a
reseed that does not actually take effect).
"""
import numpy as np, math
from load import load
ids, ts, nums, boost, bonus = load()
first = np.load("firstofday.npy")
N = len(ids)

M = np.zeros((N, 80), dtype=np.uint8)
M[np.repeat(np.arange(N), 20), nums.reshape(-1) - 1] = 1

def tail(k):
    T = math.comb(80, 20)
    return sum(math.comb(20, j) * math.comb(60, 20 - j) for j in range(k, 21)) / T

F = M[first].astype(np.int16)
ov = F @ F.T
iu = np.triu_indices(len(first), 1)
pairs = ov[iu]
npair = len(pairs)
print("block openings: %d, pairs: %d" % (len(first), npair))
print("  mean overlap %.4f (null 5.0000)   max %d" % (pairs.mean(), pairs.max()))
for k in range(12, 18):
    obs = int((pairs >= k).sum()); exp = npair * tail(k)
    if exp < 1e-3 and obs == 0: break
    print("    >=%2d : %4d observed, %8.2f expected" % (k, obs, exp))

adj = ov[np.arange(len(first)-1), np.arange(1, len(first))]
print("\n  adjacent blocks only (%d pairs): mean %.4f, max %d, expected max ~%d"
      % (len(adj), adj.mean(), adj.max(), 11))

last = np.concatenate((first[1:] - 1, [N - 1]))
cross = (M[first].astype(np.int16) * M[last].astype(np.int16)).sum(1)
print("  opening vs previous block's close (%d pairs): mean %.4f, max %d"
      % (len(cross), cross.mean(), cross.max()))

# the same statistic on an equal number of ordinary draws, as a control
rng = np.random.default_rng(3)
idx = rng.choice(N, size=len(first), replace=False)
G = M[idx].astype(np.int16); og = G @ G.T
pg = og[np.triu_indices(len(idx), 1)]
print("\n  control, %d ordinary draws chosen at random: mean %.4f, max %d"
      % (len(idx), pg.mean(), pg.max()))
print("\n%s" % ("NOTHING: block openings behave exactly like any other draws"
                if pairs.max() <= 14 else "INVESTIGATE"))
