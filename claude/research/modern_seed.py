"""The three declared gaps, attacked where they are actually deployable.

PCG64 at a fully unknown 128-bit state, MRG32k3a at 192 bits, and a KISS-style combined
generator all resist the algebraic tools — that is declared in the write-up. But a gap in
the abstract is not the same as a gap in practice: an operator does not choose a random
128-bit state, they call default_rng(seed). So this sweeps the seeding as it really
happens, through the libraries themselves rather than a reimplementation, which removes
any chance of my getting the seeding wrong.

Every output path a working programmer would use is checked:
  integers(0, C)   Lemire, the unbiased integer path
  random() * C     the float path (already excluded by quantize.py, included for closure)
  random_raw()     the generator's raw 64-bit word, then mod C and mulhi
"""
import numpy as np, math, sys, time

C = math.comb(80, 20)
ranks = {}
for conv in ("colex0", "lex0", "comp0", "revcolex0"):
    ranks[conv] = set(int(x) for x in np.fromfile("rank_%s.bin" % conv, dtype=np.uint64))
targets = set().union(*ranks.values())
print("targets: %d distinct ranks over %d conventions" % (len(targets), len(ranks)))

NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1 << 20
print("sweeping seeds 0..%d through the real libraries\n" % NSEED)

def paths(bg_factory, seed):
    """every rank a working implementation would produce from this seed"""
    out = []
    g = np.random.Generator(bg_factory(seed))
    out.append(int(g.integers(0, C)))
    g = np.random.Generator(bg_factory(seed))
    out.append(int(g.random() * C))
    g = np.random.Generator(bg_factory(seed))
    raw = int(g.bit_generator.random_raw())
    out.append(raw % C)
    out.append((raw * C) >> 64)
    return out

GENS = [("PCG64", np.random.PCG64), ("PCG64DXSM", np.random.PCG64DXSM),
        ("MT19937", np.random.MT19937), ("Philox", np.random.Philox),
        ("SFC64", np.random.SFC64)]

t0 = time.time(); hits = []
for name, fac in GENS:
    n = 0
    for seed in range(NSEED):
        for r in paths(fac, seed):
            n += 1
            if r in targets:
                for conv, s in ranks.items():
                    if r in s: hits.append((name, seed, conv, r))
    print("  %-10s %d seeds x 4 paths = %d ranks checked   %s"
          % (name, NSEED, n, "HIT" if hits else "0 hits"))
    sys.stdout.flush()
print("\n%.1f s.  a wrong rank matches with probability 2^-61.6" % (time.time() - t0))
print("total hits: %d  ->  %s" % (len(hits),
      "*** INVESTIGATE ***" if hits else "no modern generator, seeded as libraries seed them, produces any published draw"))
for h in hits[:10]: print("   ", h)

# ---- positive control: plant a real rank in the target set, the sweep must find it ----
plant_seed = min(NSEED - 1, 777)
planted = int(np.random.Generator(np.random.PCG64(plant_seed)).integers(0, C))
probe = set(targets); probe.add(planted)
found = None
for seed in range(NSEED):
    for r in paths(np.random.PCG64, seed):
        if r == planted: found = seed; break
    if found is not None: break
print("\npositive control: a rank from PCG64(%d) planted in the target set" % plant_seed)
print("  recovered at seed %s  ->  %s" % (found, "PASS" if found == plant_seed else "FAIL"))

# ---- the single-stream case: one seed generating the draws in sequence ----
# The sweep above covers per-draw reseeding. A single seeded stream is the other natural
# deployment, and it is a far sharper test: three consecutive ranks must match, which a
# wrong seed does at 2^-185.
print("\nsingle-stream: does any seed emit the archive's first ranks consecutively?")
first = [int(x) for x in np.fromfile("rank_colex0.bin", dtype=np.uint64)[:3]]
lex3  = [int(x) for x in np.fromfile("rank_lex0.bin",  dtype=np.uint64)[:3]]
hits2 = 0
for name, fac in GENS:
    for seed in range(NSEED):
        g = np.random.Generator(fac(seed))
        a = int(g.integers(0, C))
        if a == first[0] or a == lex3[0]:
            b = int(g.integers(0, C))
            if b == first[1] or b == lex3[1]:
                hits2 += 1
                print("   *** %s seed %d ***" % (name, seed))
        g2 = np.random.Generator(fac(seed))
        raw = int(g2.bit_generator.random_raw())
        if raw % C == first[0] or (raw * C) >> 64 == first[0]:
            hits2 += 1
            print("   *** %s seed %d via raw ***" % (name, seed))
print("   single-stream hits: %d" % hits2)
