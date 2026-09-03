"""Builds a SYNTHETIC ordered capture to exercise keno_break end-to-end.

These are not Loto Express draws and are never mixed with the real archive: they
come from a known MT19937 seed so the tool's answer can be checked against ground
truth. The real archive is only ever read through load.py.
"""
class MT:
    def __init__(s, seed):
        s.mt = [0]*624; s.mt[0] = seed
        for i in range(1, 624):
            s.mt[i] = (1812433253*(s.mt[i-1] ^ (s.mt[i-1] >> 30)) + i) & 0xffffffff
        s.i = 624
    def next(s):
        if s.i >= 624:
            for k in range(624):
                y = (s.mt[k] & 0x80000000) | (s.mt[(k+1) % 624] & 0x7fffffff)
                s.mt[k] = s.mt[(k+397) % 624] ^ (y >> 1) ^ (0x9908b0df if y & 1 else 0)
            s.i = 0
        y = s.mt[s.i]; s.i += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680; y &= 0xffffffff
        y ^= (y << 15) & 0xefc60000; y &= 0xffffffff
        y ^= y >> 18
        return y

g = MT(0x13579BDF)
for _ in range(41):                 # unknown warm-up, hidden from the solver
    g.next()
while g.i not in (0, 624):
    g.next()

rows = []
for _ in range(420):
    a = list(range(1, 81)); row = []
    for i in range(20):
        j = i + ((g.next()*(80-i)) >> 32)
        a[i], a[j] = a[j], a[i]
        row.append(a[i])
    rows.append(row)

with open("ordered_demo.txt", "w") as f:
    f.write("\n".join(" ".join(map(str, r)) for r in rows) + "\n")
with open("sorted_demo.txt", "w") as f:
    f.write("\n".join(" ".join(map(str, sorted(r))) for r in rows) + "\n")
print("wrote ordered_demo.txt and sorted_demo.txt (420 synthetic draws)")
