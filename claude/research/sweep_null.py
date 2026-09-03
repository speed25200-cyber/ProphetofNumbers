"""Does the finished 2^32 sweep match its null exactly?

A wrong seed survives step i of Fisher-Yates with probability (20-i)/(80-i), not 1/4 —
the pool shrinks and so does the number of target values still unmatched. So the
distribution of "longest leading prefix matched" over 2^32 seeds is fully predictable,
and comparing the observed maxima against it shows both that the sweep is behaving and
that nothing came near a real hit.
"""
import re
from math import comb

SEEDS = 1 << 32
p = 1.0
Pk = [1.0]
for i in range(20):
    p *= (20 - i)/(80 - i)
    Pk.append(p)

rows = []
for line in open("sweep32.log"):
    m = re.search(r"best=\s*(\d+)/20", line)
    if m:
        rows.append(int(m.group(1)))
n = len(rows)
print("combos in sweep: %d   seeds each: %d   total seed-tests: %.2e" % (n, SEEDS, n*SEEDS))
print("(a wrong seed matches k leading balls with probability prod (20-i)/(80-i))\n")
print("  k   P(>=k)      exp. seeds/combo   exp. combos with max>=k   observed")
for k in range(10, 19):
    e_seeds = SEEDS*Pk[k]
    e_combos = n*(1 - pow(2.718281828459045, -e_seeds)) if e_seeds < 30 else n
    obs = sum(1 for r in rows if r >= k)
    print("  %2d  %.3e   %14.2f   %20.1f   %8d" % (k, Pk[k], e_seeds, e_combos, obs))
print("\n  P(a seed matches all 20) = %.3e = 1/C(80,20); over %.2e tests that is %.4f expected"
      % (Pk[20], n*SEEDS, n*SEEDS*Pk[20]))
print("  observed maxima: max %d/20 over the whole sweep" % max(rows))
zero = sum(1 for r in rows if r == 0)
print("  %d combos scored 0 (degenerate mapping/sampler pairs that never produce a legal index)" % zero)
