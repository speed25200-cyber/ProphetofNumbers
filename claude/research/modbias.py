"""The absence of modulo bias is itself a measurement, not just another exclusion.

Every other test here asks "does family X fit?" and answers no. This one constrains the
implementation directly. If the operator computes rank = u mod C from a w-bit uniform
without rejection, the ranks below (2^w mod C) receive one more preimage than the rest,
and the excess is not subtle: 3.3 percentage points at w = 64, 16 at w = 62.

So its absence says something, and its presence would have handed over the word width.
"""
import numpy as np, math, sys
C = math.comb(80, 20)
conv = sys.argv[1] if len(sys.argv) > 1 else "colex0"
r = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64).astype(object)
N = len(r)
print("convention %s, %d draws, C = %d\n" % (conv, N, C))
print(" width  q   P(rank<R0) uniform   naive u%C    observed     z vs naive   z vs uniform")
for w in (62, 63, 64):
    W = 1 << w
    q = W // C
    R0 = W - q * C
    p_unif  = R0 / C
    p_naive = (q + 1) * R0 / W
    obs = float(np.count_nonzero(r < R0)) / N
    z_naive = (obs - p_naive) / math.sqrt(p_naive * (1 - p_naive) / N)
    z_unif  = (obs - p_unif)  / math.sqrt(p_unif  * (1 - p_unif)  / N)
    print("   %2d   %d       %.5f          %.5f     %.5f    %+8.1f      %+7.2f"
          % (w, q, p_unif, p_naive, obs, z_naive, z_unif))
print()
print("A positive control: draw 70560 ranks the naive way and confirm the test sees it.")
rng = np.random.default_rng(7)
u = rng.integers(0, 1 << 63, size=N, dtype=np.uint64).astype(object) * 2 + rng.integers(0, 2, size=N)
naive = np.array([int(x) % C for x in u], dtype=object)
W = 1 << 64; q = W // C; R0 = W - q * C
p_unif = R0 / C; p_naive = (q + 1) * R0 / W
obs = float(np.count_nonzero(naive < R0)) / N
print("  planted naive u%%C at w=64: observed %.5f, uniform says %.5f, naive says %.5f"
      % (obs, p_unif, p_naive))
print("  z vs uniform %+.1f  -> the test does detect the bias it is looking for"
      % ((obs - p_unif) / math.sqrt(p_unif * (1 - p_unif) / N)))
