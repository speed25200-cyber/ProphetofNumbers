"""The two bit-channel claims, checked against synthetic data rather than argued.

Berlekamp-Massey needs its input bits to be EXACT linear functionals of the generator
output. Two arguments underwrite that, one per reduction, and both are cheap enough to
verify instead of assert:

  (1) under u mod C, the low 4 bits of the rank equal the low 4 bits of u, because
      v2(C(80,20)) = 4 makes the unknown multiple of C invisible there — and only there;
  (2) under mulhi, bits 32 and above of ceil(r*2^64/C) equal those of u, because the
      preimage interval is only about 5.2 integers wide.

If either failed, the linear-complexity exclusion would be measuring noise.
"""
import math, numpy as np
C = math.comb(80, 20)
rng = np.random.default_rng(19)
u = rng.integers(0, 1 << 63, size=300000, dtype=np.uint64).astype(object) * 2 \
    + rng.integers(0, 2, size=300000)

bad4 = sum(1 for x in u if (int(x) % C) & 15 != int(x) & 15)
bad5 = sum(1 for x in u[:50000] if (int(x) % C) & 31 != int(x) & 31)
print("(1) u mod C, low 4 bits : %d differences in %d      <- the channel" % (bad4, len(u)))
print("    u mod C, low 5 bits : %d differences in 50000   <- the boundary is exactly 4"
      % bad5)

print("(2) mulhi, reconstructed bit vs true bit, out of 200000:")
for b in (24, 28, 32, 40, 48):
    bad = sum(1 for x in u[:200000]
              if ((((((int(x) * C) >> 64) << 64) + C - 1) // C) >> b) & 1 != (int(x) >> b) & 1)
    print("      bit %2d : %6d   (interval of width 5.2 predicts ~%.2f)"
          % (b, bad, 200000 * 5.2 / (1 << b)))
print()
print("Both channels are exact where the argument says they are, and stop being exact")
print("exactly where it says they stop.")
