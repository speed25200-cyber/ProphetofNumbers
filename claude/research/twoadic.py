"""2-adic complexity: the with-carry counterpart of Berlekamp-Massey.

bm.c settles the F2-linear class without enumerating it, because a linear recurring
sequence has small LINEAR complexity. The carry families have the exact analogue: an FCSR
with connection integer q emits the 2-adic expansion of p/q, so its sequence has small
2-ADIC complexity — and every multiply-with-carry generator is an FCSR (Marsaglia's MWC
with multiplier a over base b corresponds to q = a*b - 1).

So rankmwc, which needs a published multiplier, generalises: this needs none. And the two
tests together cover both linear worlds — over GF(2), and over the 2-adics — without
naming a single generator.

The minimisation is a 2-dimensional lattice problem. Pairs (t, r) with r = t*S mod 2^n
form the lattice spanned by (1, S) and (0, 2^n), and the Euclidean algorithm on
(2^n, S) walks exactly its best approximations, so the shortest vector is the smallest
max(|r_i|, |t_i|) along that walk.
"""
import math, sys, numpy as np

def two_adic_complexity(bits):
    n = len(bits)
    S = int("".join(str(int(b)) for b in reversed(bits)), 2) if n else 0
    M = 1 << n
    r0, t0 = M, 0
    r1, t1 = S, 1
    best = None
    while r1:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        t0, t1 = t1, t0 - q * t1
        c = max(abs(r0), abs(t0))
        if c and (best is None or c < best): best = c
    return math.log2(best) if best else 0.0

def fcsr_bits(p, q, n):
    """the 2-adic expansion of p/q, q odd — what an FCSR with connection integer q emits"""
    out = []
    for _ in range(n):
        b = p & 1
        out.append(b)
        p = (p - b * q) // 2
    return out

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print("2-adic complexity, %d bits per stream (detects up to ~%d)\n" % (N, N // 2))
    rng = np.random.default_rng(23)

    import random as _r
    _r.seed(23)
    print("controls:")
    for qbits in (64, 128, 256, 1024):
        # Python ints throughout: a numpy int64 silently overflows on these shifts, which
        # produced a nonsense connection integer and a nonsense control the first time.
        q = _r.getrandbits(qbits) | 1 | (1 << (qbits - 1))
        p = _r.getrandbits(qbits - 1) | 1
        c = two_adic_complexity(fcsr_bits(p, q, N))
        print("   FCSR, connection integer of %4d bits : complexity %8.1f" % (qbits, c))
    # a real MWC: q = a*2^32 - 1
    a = 4294967118
    q = a * (1 << 32) - 1
    p = 123456789
    print("   MWC a=%d (q = a*2^32-1, %d bits) : complexity %8.1f"
          % (a, q.bit_length(), two_adic_complexity(fcsr_bits(p, q, N))))
    rb = rng.integers(0, 2, N)
    print("   random bits                          : complexity %8.1f   (n/2 = %d)"
          % (two_adic_complexity(rb), N // 2))

    print("\nreal archive:")
    import glob, os
    files = sorted(glob.glob("bits_rank_colex0_bit*.bin")) + \
            sorted(glob.glob("bits_mulhi_colex0_bit*.bin")) + \
            ["bits_bonus_bit0.bin", "bits_bonus_bit1.bin", "bits_boost_bit0.bin",
             "bits_bonusrank_bit0.bin"]
    worst = (None, 1e18)
    for f in files:
        if not os.path.exists(f): continue
        b = np.fromfile(f, dtype=np.uint8)[:N]
        c = two_adic_complexity(b)
        if c < worst[1]: worst = (f, c)
        print("   %-32s complexity %8.1f" % (f, c))
    print("\n   lowest of all: %s at %.1f, against n/2 = %d" % (worst[0], worst[1], N//2))
    print("   %s" % ("NOTHING: no FCSR or multiply-with-carry generator of connection\n"
                     "   integer below %d bits produces any of these streams" % (N//2)
                     if worst[1] > N/2 - 200 else "INVESTIGATE"))
