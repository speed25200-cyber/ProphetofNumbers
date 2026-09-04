"""How far the linear-complexity test actually reaches.

Berlekamp-Massey was introduced here for F2-linear generators. But its reach is wider than
that, and the reason is simple enough to check rather than argue: the LOW BIT of any
integer linear recurrence mod 2^k is itself an F2-linear recurring sequence of the same
order, because the carries only propagate upward.

So an LCG, a lagged Fibonacci, and a multiple recursive generator mod 2^64 all leave a
low-bit stream of tiny linear complexity — and the archive's low-bit streams sit at n/2.
This plants each one and measures what BM returns, so the claim rests on a measurement.
"""
import numpy as np, subprocess, os

M = (1 << 64) - 1
N = 4000
rng = np.random.default_rng(31)

def emit(seq, name):
    np.array([x & 1 for x in seq], dtype=np.uint8).tofile(name)

cases = {}

x = 0x123456789ABCDEF
s = []
for _ in range(N):
    s.append(x); x = (x * 6364136223846793005 + 1442695040888963407) & M
cases["LCG mod 2^64 (order 1)"] = s

u = [int(v) for v in rng.integers(0, 1 << 62, size=31)]
for _ in range(N): u.append((u[-31] + u[-3]) & M)
cases["lagged Fibonacci 3,31"] = u[31:]

c = [int(v) | 1 for v in rng.integers(0, 1 << 62, size=3)]
v = [int(t) for t in rng.integers(0, 1 << 62, size=3)]
for _ in range(N): v.append((c[0]*v[-1] + c[1]*v[-2] + c[2]*v[-3] + 12345) & M)
cases["MRG order 3 mod 2^64"] = v[3:]

w = [int(t) for t in rng.integers(0, 1 << 62, size=7)]
cc = [int(t) | 1 for t in rng.integers(0, 1 << 62, size=7)]
for _ in range(N): w.append(sum(cc[i]*w[-1-i] for i in range(7)) & M)
cases["MRG order 7 mod 2^64"] = w[7:]

st = 12345
sm = []
for _ in range(N):
    st = (st + 0x9E3779B97F4A7C15) & M
    z = st
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    sm.append(z ^ (z >> 31))
cases["splitmix64 (not linear)"] = sm

print("low bit of each construction, linear complexity from bm.c, %d bits\n" % N)
for name, seq in cases.items():
    f = "/tmp/claude-0/-home-user/42392201-ee98-5b6b-8911-209869d2ab7f/scratchpad/lb.bin"
    emit(seq[:N], f)
    out = subprocess.run(["./bm", f], capture_output=True, text=True).stdout
    comp = out.split("complexity")[1].split()[0]
    print("  %-26s complexity %6s   (n/2 = %d)" % (name, comp, N // 2))
print()
print("Any integer linear recurrence mod 2^k is caught by the low bit alone, whatever its")
print("order. The archive's low-bit streams sit at n/2, so that whole class is out too.")
