import numpy as np
from load import load, indicator
ids, ts, nums, boost, bonus = load()
N = len(ids); M = indicator(nums)

print("="*70); print("E1  bonus rank inside sorted 20")
rank = np.argmax(nums == bonus[:,None].astype(np.int8), axis=1)
cnt = np.bincount(rank, minlength=20); exp = N/20
chi2 = ((cnt-exp)**2/exp).sum()
print(" counts:", cnt.tolist())
print(" chi2 =", round(chi2,2), "df=19  (uniform if ~19)")
print(" z per rank:", np.round((cnt-exp)/np.sqrt(exp*(1-1/20)),2).tolist())

print("="*70); print("E2  bonus value distribution vs its own null")
bc = np.bincount(bonus, minlength=81)[1:]
# null: P(bonus=v) = P(v in draw)/20 -> expected = N/80
print(" chi2 =", round((((bc-N/80)**2)/(N/80)).sum(),2), "df=79")
print(" top5:", np.argsort(-bc)[:5]+1, bc[np.argsort(-bc)[:5]])

print("="*70); print("E3  boost vs bonus-rank independence")
tab = np.zeros((6,20))
bmap = {1:0,2:1,3:2,4:3,5:4,10:5}
for b,r in zip(boost, rank): tab[bmap[b], r] += 1
rowm = tab.sum(1, keepdims=True); colm = tab.sum(0, keepdims=True)
E = rowm*colm/N
print(" chi2 =", round((((tab-E)**2)/E).sum(),2), "df =", 5*19)

print("="*70); print("E4  GF(2) rank of 70560x80 indicator matrix")
rows = np.zeros(N, dtype=object)
packed = np.packbits(M, axis=1).view(np.uint8)
# build integer per row
pw = (1 << np.arange(80, dtype=object))
vals = [int(np.dot(M[i].astype(object), pw)) for i in range(0, N, 1)] if False else None
# fast: use python ints via bytes
ints = np.zeros(N, dtype=object)
for i in range(N):
    ints[i] = int.from_bytes(np.packbits(M[i][::-1]).tobytes(), 'big')
basis = []
piv = []
for v in ints:
    x = v
    for b,p in zip(basis,piv):
        if (x >> p) & 1: x ^= b
    if x:
        p = x.bit_length()-1
        basis.append(x); piv.append(p)
    if len(basis) >= 80: break
print(" GF(2) rank =", len(basis), "/80  (80 = no deterministic F2 relation besides parity check below)")

# parity of full weight = 20 => even => all-ones mask always 0
ones = M.sum(1)
print(" weight always 20:", bool(np.all(ones==20)))
