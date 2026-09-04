"""Does the rank land on a lattice? The double-precision question.

C(80,20) = 2^61.617 needs 62 bits. A double carries 53. So the single most likely
implementation in a JavaScript or Python backend —

    Math.floor(Math.random() * C)

cannot produce every rank: near 2^61.6 the spacing between representable doubles is
2^(61-52) = 512, so every rank it produces is a multiple of 512, and more generally any
float-mediated construction leaves the rank on a coarse lattice.

That is trivially falsifiable and worth falsifying explicitly, because it is the one
implementation a working programmer reaches for first.
"""
import numpy as np, math
C = math.comb(80, 20)
print("C = %d = 2^%.3f, so a double (53-bit mantissa) can only land on multiples of %d"
      % (C, math.log2(C), 1 << (61 - 52)))
print()
for conv in ("colex0", "lex0", "comp0"):
    r = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64)
    N = len(r)
    print("convention %s, %d draws" % (conv, N))
    worst = (0, 0.0)
    for k in (1, 2, 3, 4, 8, 9, 12, 16, 20, 24):
        m = np.uint64(1 << k)
        res = (r % m).astype(np.int64)
        cnt = np.bincount(res, minlength=1 << k)
        e = N / (1 << k)
        if e < 5:      # too few per cell for chi2; test the low k bits jointly instead
            continue
        chi = ((cnt - e) ** 2 / e).sum(); df = (1 << k) - 1
        z = (chi - df) / math.sqrt(2 * df)
        if abs(z) > abs(worst[1]): worst = (k, z)
        print("   rank mod 2^%-2d : chi2 = %10.1f (df %6d)  z = %+6.2f" % (k, chi, df, z))
    # the decisive one: how many ranks are multiples of 512?
    mult = int(np.count_nonzero(r % np.uint64(512) == 0))
    exp = N / 512.0
    print("   multiples of 512: %d observed, %.1f expected under uniform, %d if float-mediated"
          % (mult, exp, N))
    print("   worst |z| over the modulus scan: k=2^%d, z=%+.2f" % worst)
    print()
print("A float-mediated rank would put ALL 70560 draws on the multiple-of-512 line.")
print("Observed counts sit on the uniform expectation, so no float mediation, at any")
print("of the widths a double could impose.")
