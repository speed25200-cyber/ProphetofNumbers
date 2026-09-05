"""Feasibility of a lattice attack on a 64-bit LCG whose output is the HIGH half.

This is the one classical family the rest of the work does not reach: seedhunt's 2^32
sweep covers every LCG modulo 2^32 and every 64-bit LCG reachable from a 32-bit seed;
the F2-linear attacks do not apply to a congruential update; modlcg only sees a
congruential generator whose output carries the LOW bits. What is left is an LCG
modulo 2^64 with an arbitrary 64-bit state and output s >> 32.

The bonus channel pins each state: bonus-1 = (u*80)>>32 with u = s >> 32 puts s in an
interval of width 2^57.7 out of 2^64, i.e. 6.3 bits per draw. Differencing removes the
unknown increment, leaving a Hidden Number Problem, and LLL is the standard tool.

It does not work here, and the script measures exactly why rather than asserting it.
Centre every quantity: with e_d = D_d - Dc_d bounded by 2^58.7 and e_d = A^d e_0 + b_d
(mod 2^64), the target vector has norm about sqrt(K+1)*2^58.7 while the Gaussian
heuristic for the lattice sits at ((2^64)^(K-1) * 2^58.7)^(1/(K+1)). The target only
becomes the shortest vector past K ~ 30, and by then LLL's approximation factor
(~2^(n/4), so 2^7 or worse) swamps the 2^0.6 margin. Classical truncated-LCG attacks
assume half the bits of each output are visible; 6.3 bits out of 64 is far below that.

Conclusion recorded honestly: this family is NOT excluded. It is the one gap left, and
capturing the draw order closes it — 20 ordered indices per draw is 126 bits, well
past what the lattice needs.

Usage: python3 lcg_lll.py selftest   |   python3 lcg_lll.py margins
"""
import sys, math
from fractions import Fraction

M = 1 << 64

def lll(B, delta=Fraction(99, 100)):
    """Integer LLL with exact rational Gram-Schmidt, GSO refreshed only on swaps."""
    B = [row[:] for row in B]
    n = len(B)
    def dot(u, v): return sum(x*y for x, y in zip(u, v))
    def gso():
        Bs = []; mu = [[Fraction(0)]*n for _ in range(n)]
        for i in range(n):
            v = [Fraction(x) for x in B[i]]
            for j in range(i):
                d = dot(Bs[j], Bs[j])
                mu[i][j] = Fraction(dot([Fraction(x) for x in B[i]], Bs[j]), d) if d else Fraction(0)
                v = [a - mu[i][j]*b for a, b in zip(v, Bs[j])]
            Bs.append(v)
        return Bs, mu
    Bs, mu = gso()
    k = 1; guard = 0
    while k < n and guard < 40000:
        guard += 1
        changed = False
        for j in range(k-1, -1, -1):
            q = mu[k][j]
            r = int(q + Fraction(1, 2)) if q >= 0 else -int(-q + Fraction(1, 2))
            if r:
                B[k] = [a - r*b for a, b in zip(B[k], B[j])]
                changed = True
        if changed:
            Bs, mu = gso()
        if dot(Bs[k], Bs[k]) >= (delta - mu[k][k-1]**2) * dot(Bs[k-1], Bs[k-1]):
            k += 1
        else:
            B[k], B[k-1] = B[k-1], B[k]
            Bs, mu = gso()
            k = max(k-1, 1)
    return B

def hnp(A, cen, bound):
    """Centred HNP: find e_0 with |e_d| <= bound where e_d = A^d e_0 + b_d (mod M)."""
    K = len(cen) - 1
    Dc = [(cen[d+1] - cen[d]) % M for d in range(K)]
    beta = [(pow(A, d, M)*Dc[0] - Dc[d]) % M for d in range(1, K)]
    n = K + 1
    rows = []
    for i in range(K-1):
        rows.append([M if j == i else 0 for j in range(K-1)] + [0, 0])
    rows.append([pow(A, d, M) for d in range(1, K)] + [1, 0])
    rows.append(beta + [0, bound])
    red = lll(rows)
    for v in red:
        if abs(v[-1]) != bound:
            continue
        sgn = 1 if v[-1] < 0 else -1
        e = [sgn*x for x in v[:K-1]]
        e0 = sgn*v[-2]
        if abs(e0) <= bound and all(abs(x) <= bound for x in e):
            return e0
    return None

def interval(j, k=80):
    lo = (j << 32)//k + (1 if ((j << 32) % k) else 0)
    hi = ((j+1) << 32)//k + (1 if (((j+1) << 32) % k) else 0)
    return lo << 32, hi << 32

def synth_centres(K, a, c, W, seed=0xC0FFEE1234567890):
    s = seed; cen = []
    for d in range(K+1):
        lo, hi = interval(((s >> 32)*80) >> 32)
        assert lo <= s < hi
        cen.append((lo+hi)//2)
        for _ in range(W):
            s = (a*s + c) % M
    return cen

def selftest(Ks=(13, 20), a=6364136223846793005, c=1442695040888963407, W=21):
    print("selftest: synthetic LCG64 (MMIX), W=%d, output s>>32, bonus = first ball" % W)
    print("  positive AND negative controls both have to pass before any real run\n")
    bound = interval(0)[1] - interval(0)[0]
    other = 2862933555777941757
    ok = True
    for K in Ks:
        cen = synth_centres(K, a, c, W)
        good = hnp(pow(a, W, M), cen, bound)
        badW = hnp(pow(a, W+1, M), cen, bound)
        badA = hnp(pow(other, W, M), cen, bound)
        # random data, correct multiplier: must also be rejected
        rnd = [((i*0x9E3779B97F4A7C15) % M) for i in range(K+1)]
        badD = hnp(pow(a, W, M), rnd, bound)
        print("  K=%2d  correct a,W: %-10s | wrong W: %-9s | wrong a: %-9s | random data: %s"
              % (K, "RECOVERED" if good is not None else "missed",
                 "false hit" if badW is not None else "rejected",
                 "false hit" if badA is not None else "rejected",
                 "false hit" if badD is not None else "rejected"))
        ok = ok and good is not None and badW is None and badA is None and badD is None
    print("\n  %s" % ("controls pass: the attack discriminates, real runs are meaningful"
                      if ok else "controls FAIL: no real result may be reported from this tool"))
    return ok

def real(K=20, maxW=48):
    """Run the recovered attack against the real archive."""
    from load import load
    ids, ts, nums, boost, bonus = load()
    bound = interval(0)[1] - interval(0)[0]
    print("real archive: %d draws, K=%d constraints, W swept 1..%d" % (len(ids), K, maxW))
    print("  bonus = first ball drawn, LCG64 with output s>>32, increment differenced away\n")
    starts = [0, 5000, 20000, 50000]
    hits = []
    for name, a in MULTIPLIERS.items():
        found = []
        for W in range(1, maxW+1):
            A = pow(a, W, M)
            for st in starts:
                cen = [ (interval(int(bonus[st+d])-1)[0] + interval(int(bonus[st+d])-1)[1])//2
                        for d in range(K+1) ]
                if hnp(A, cen, bound) is not None:
                    found.append((W, st))
        print("  %-26s a=%-22d %s" % (name, a, ("HIT " + str(found)) if found else "no fit at any W"))
        hits += found
    print("\n  total hits: %d  ->  %s" % (len(hits),
          "INVESTIGATE" if hits else "no 64-bit LCG with a standard multiplier fits the archive"))

def margins():
    bound = 2*((interval(0)[1]-interval(0)[0])//2)
    print("bits known per draw from the bonus channel: %.2f" % (64 - math.log2(bound)))
    print(" K   dim   target    Gaussian   margin    LLL factor needed")
    for K in (13, 20, 30, 40, 60, 80, 120):
        n = K+1
        logdet = 64*(K-1) + math.log2(bound)
        gauss = math.log2(math.sqrt(n/(2*math.pi*math.e))) + logdet/n
        tgt = math.log2(math.sqrt(n)) + math.log2(bound)
        print("%3d  %4d  2^%.1f   2^%.1f   2^%+.1f    2^%.1f" % (K, n, tgt, gauss, gauss-tgt, n/4.0))
    print("\nLLL delivers roughly 2^(n/4); the margin has to exceed that. It never does.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "margins": margins()
    elif len(sys.argv) > 1 and sys.argv[1] == "real": real()
    else: selftest()
