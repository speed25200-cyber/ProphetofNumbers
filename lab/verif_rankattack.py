"""Vérification par exécution de `Prophet/Services/RankAttack.swift`.

Aucune toolchain Swift n'est joignable ici : `verif_swift.py` contrôle la
syntaxe, ce fichier contrôle la LOGIQUE. Il transcrit fidèlement le Swift —
même formules, même ordre d'opérations, mêmes cas limites — et exige que
chaque brique se comporte comme annoncé.

Les quatre endroits où ce code peut être faux en silence, et qui sont donc
testés en priorité :

  1. la table des binomiaux (une récurrence décalée d'un cran passerait
     inaperçue sur les petits rangs) ;
  2. `unrank` comme inverse EXACT de `rank`, aux deux bouts du domaine ;
  3. `candidates` pour le mapping ⌊s·M/2^b⌋ — la division 128 bits et le cas
     r = M−1, où la borne haute vaut 2^b et ne tient pas dans un UInt64 ;
  4. l'inversion de la sortie splitmix64, où une constante fausse donnerait
     un inverse silencieusement faux.
"""

import math
import random

POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1


# --------------------------------------------------------------------------
# Transcription du Swift
# --------------------------------------------------------------------------

def build_binomial():
    """Récurrence EXACTE du Swift, pas math.comb — c'est elle qu'on teste."""
    t = [[0] * (DRAWN + 1) for _ in range(POOL + 1)]
    for n in range(POOL + 1):
        t[n][0] = 1
        for k in range(1, DRAWN + 1):
            if k <= n:
                t[n][k] = t[n - 1][k - 1] + (t[n - 1][k] if k <= n - 1 else 0)
    return t


BIN = build_binomial()
MOD = BIN[POOL][DRAWN]


def rank(nums):
    s = sorted(nums)
    if len(s) != DRAWN or s[0] < 1 or s[-1] > POOL:
        return None
    return sum(BIN[n - 1][i + 1] for i, n in enumerate(s))


def unrank(value):
    r, out, i = value, [], DRAWN
    while i >= 1:
        c = i - 1
        while c + 1 <= POOL and BIN[c + 1][i] <= r:
            c += 1
        out.append(c + 1)
        r -= BIN[c][i]
        i -= 1
    return sorted(out)


def mask(b):
    return M64 if b >= 64 else (1 << b) - 1


def candidates(r, b, floor_mapping):
    m = mask(b)
    out = []
    if not floor_mapping:
        s = r
        while s <= m:
            out.append(s)
            if s + MOD > M64:
                break
            s += MOD
        return out

    def ceil_div(hi, lo):
        v = (hi << 64) | lo
        q, rem = divmod(v, MOD)
        return q if rem == 0 else q + 1

    shift = 64 - b
    lo_a = ceil_div(r >> shift, (r << b) & M64)
    rb = r + 1
    s = lo_a
    if rb >= MOD:                       # cas limite r = M−1
        while s <= m:
            out.append(s)
            if s == m:
                break
            s += 1
        return out
    lo_b = ceil_div(rb >> shift, (rb << b) & M64)
    while s < lo_b and s <= m:
        out.append(s)
        s += 1
    return out


def rank_of(s, b, floor_mapping):
    if not floor_mapping:
        return s % MOD
    full = s * MOD
    hi, lo = full >> 64, full & M64
    return hi if b >= 64 else ((hi << (64 - b)) | (lo >> b)) & M64


def inverse64(x):
    if x % 2 == 0:
        return None
    inv = 1
    for _ in range(7):
        inv = (inv * (2 - x * inv)) & M64
    return inv


GOLDEN = 0x9E3779B97F4A7C15
SM_A, SM_B = 0xBF58476D1CE4E5B9, 0x94D049BB133111EB
XS_MUL = 0x2545F4914F6CDD1D


def unshift_right(y, k):
    x = y
    for _ in range(64 // k + 1):
        x = y ^ (x >> k)
    return x & M64


def splitmix_output(state):
    w = (state + GOLDEN) & M64
    w = ((w ^ (w >> 30)) * SM_A) & M64
    w = ((w ^ (w >> 27)) * SM_B) & M64
    return w ^ (w >> 31)


def splitmix_state(out):
    w = unshift_right(out, 31)
    w = (w * inverse64(SM_B)) & M64
    w = unshift_right(w, 27)
    w = (w * inverse64(SM_A)) & M64
    return unshift_right(w, 30)


def xorshift_step(state):
    s = state
    s ^= s >> 12
    s = (s ^ (s << 25)) & M64
    s ^= s >> 27
    return s


def solve_lcg(ranks, b, floor_mapping, starts, confirm):
    m = mask(b)
    limit = min(starts, max(0, len(ranks) - confirm - 3))
    for t0 in range(limit):
        c = [candidates(ranks[t0 + i], b, floor_mapping) for i in range(3)]
        for s0 in c[0]:
            for s1 in c[1]:
                inv = inverse64((s1 - s0) & m)
                if inv is None:
                    continue
                for s2 in c[2]:
                    a = ((s2 - s1) & m) * inv & m
                    cc = (s1 - a * s0) & m
                    s, good = s2, True
                    for j in range(3, 3 + confirm):
                        s = (a * s + cc) & m
                        if rank_of(s, b, floor_mapping) != ranks[t0 + j]:
                            good = False
                            break
                    if not good:
                        continue
                    for j in range(3 + confirm, len(ranks) - t0):
                        s = (a * s + cc) & m
                        if rank_of(s, b, floor_mapping) != ranks[t0 + j]:
                            good = False
                            break
                    if not good:
                        continue
                    s = (a * s + cc) & m
                    return {"family": f"LCG 2^{b}", "a": a, "c": cc,
                            "predicted": unrank(rank_of(s, b, floor_mapping))}
    return None


def solve(draw_ranks, starts=24, confirm=20):
    if len(draw_ranks) < confirm + 4:
        return None
    for floor_mapping in (False, True):
        for b in (64, 63, 62):
            r = solve_lcg(draw_ranks, b, floor_mapping, starts, confirm)
            if r:
                return r
    return None


# --------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------

def main():
    ok = True
    rng = random.Random(20260830)
    print("=" * 74)
    print("VÉRIFICATION PAR EXÉCUTION — RankAttack.swift")
    print("=" * 74)

    # 1. La table des binomiaux contre math.comb.
    worst = max(abs(BIN[n][k] - math.comb(n, k))
                for n in range(POOL + 1) for k in range(min(n, DRAWN) + 1))
    good = worst == 0 and MOD == math.comb(80, 20)
    print(f"\n1. table des binomiaux : écart max à math.comb = {worst}, "
          f"M = {MOD:,}   {'ok' if good else 'ÉCHEC'}")
    ok &= good

    # 2. rank/unrank : bijection, y compris aux deux bouts.
    bad = 0
    for _ in range(4000):
        g = sorted(rng.sample(range(1, POOL + 1), DRAWN))
        if unrank(rank(g)) != g:
            bad += 1
    edges = (rank(list(range(1, 21))) == 0
             and rank(list(range(61, 81))) == MOD - 1
             and unrank(0) == list(range(1, 21))
             and unrank(MOD - 1) == list(range(61, 81)))
    good = bad == 0 and edges
    print(f"2. rank/unrank : {bad} échecs sur 4 000 tirages aléatoires, "
          f"bornes {'exactes' if edges else 'FAUSSES'}   {'ok' if good else 'ÉCHEC'}")
    ok &= good

    # 3. candidates : exhaustivité et correction, par force brute.
    #    Pour chaque rang tiré, tout état candidat doit redonner le rang, et
    #    aucun état voisin ne doit manquer.
    bad = 0
    counts = {}
    for b in (64, 63, 62):
        for fm in (False, True):
            for _ in range(300):
                r = rng.randrange(MOD)
                cand = candidates(r, b, fm)
                counts.setdefault((b, fm), []).append(len(cand))
                for s in cand:
                    if rank_of(s, b, fm) != r:
                        bad += 1
                # exhaustivité : les voisins immédiats hors liste ne collent pas
                if cand:
                    for s in (cand[0] - 1, cand[-1] + 1):
                        if 0 <= s <= mask(b) and rank_of(s, b, fm) == r:
                            bad += 1
    # Cas limite r = M−1, celui qui piégeait la division 128 bits.
    for b in (64, 63, 62):
        for fm in (False, True):
            cand = candidates(MOD - 1, b, fm)
            for s in cand:
                if rank_of(s, b, fm) != MOD - 1:
                    bad += 1
    print(f"3. candidates : {bad} incohérences sur 1 800 rangs × 6 réglages, "
          f"cas limite r = M−1 inclus   {'ok' if bad == 0 else 'ÉCHEC'}")
    for key in sorted(counts):
        c = counts[key]
        print(f"     b = {key[0]}, {'floor' if key[1] else 'mod  '} : "
              f"{min(c)}–{max(c)} candidats (théorie 2^{key[0]}/M = "
              f"{2 ** key[0] / MOD:.2f})")
    ok &= bad == 0

    # 4. inverse64 et l'inversion splitmix64.
    bad = sum(1 for _ in range(2000)
              if (lambda x: (x * inverse64(x)) & M64 != 1)(rng.randrange(1, M64, 2)))
    sm_bad = sum(1 for _ in range(2000)
                 if (lambda s: splitmix_state(splitmix_output(s)) != (s + GOLDEN) & M64)(
                     rng.randrange(M64)))
    xs_bad = sum(1 for _ in range(2000)
                 if (lambda s: ((xorshift_step(s) * XS_MUL) & M64)
                     * inverse64(XS_MUL) & M64 != xorshift_step(s))(rng.randrange(M64)))
    good = bad == 0 and sm_bad == 0 and xs_bad == 0
    print(f"4. inverse64 {bad} échecs, inversion splitmix64 {sm_bad}, "
          f"xorshift64* {xs_bad} (sur 2 000 chacun)   {'ok' if good else 'ÉCHEC'}")
    ok &= good

    # 5. Témoins positifs : récupération ET prédiction exacte.
    print("\n5. témoins positifs — récupération et prédiction du tirage suivant :")
    known = [("PCG/NR", 6364136223846793005, 1442695040888963407),
             ("multiplicatif impair", 2862933555777941757, 3037000493)]
    for name, a, c in known:
        for fm in (False, True):
            s = 0x0123456789ABCDEF
            ranks, states = [], []
            for _ in range(40):
                s = (a * s + c) & M64
                states.append(s)
                ranks.append(rank_of(s, 64, fm))
            res = solve(ranks[:-1], starts=4)
            hit = res is not None and res["a"] == a and res["c"] == c
            pred = res is not None and res["predicted"] == unrank(ranks[-1])
            print(f"     {name:<22} {'floor' if fm else 'mod  '} : "
                  f"récupéré {'OUI' if hit else 'NON'}, "
                  f"prédiction exacte {'OUI' if pred else 'NON'}   "
                  f"{'ok' if hit and pred else 'ÉCHEC'}")
            ok &= hit and pred

    # 6. Témoin négatif : silence sur des tirages équitables.
    faux = 0
    for _ in range(10):
        ranks = [rank(sorted(rng.sample(range(1, POOL + 1), DRAWN))) for _ in range(40)]
        if solve(ranks, starts=3) is not None:
            faux += 1
    print(f"\n6. témoin négatif : {faux}/10 fausses récupérations sur des "
          f"tirages équitables   {'ok' if faux == 0 else 'ÉCHEC'}")
    ok &= faux == 0

    # 7. Les assertions exactes des tests Swift, rejouées ici.
    #    Même LCG que `syntheticHistory()`, mêmes tailles, mêmes attentes.
    def synthetic_ranks(count, seed=20260824):
        s = seed
        def nxt():
            nonlocal s
            s = (s * 6364136223846793005 + 1) & M64
            return s >> 33
        out = []
        for _ in range(count):
            st = set()
            while len(st) < DRAWN:
                st.add(nxt() % 80 + 1)
            nxt(); nxt()                      # boost et bonus, comme en Swift
            out.append(rank(sorted(st)))
        return out

    print("\n7. les assertions des tests Swift, rejouées :")
    checks = []

    a, c = 6364136223846793005, 1442695040888963407
    for fm in (False, True):
        s = 0x0123456789ABCDEF
        ranks = []
        for _ in range(40):
            s = (a * s + c) & M64
            ranks.append(rank_of(s, 64, fm))
        res = solve(ranks[:-1], starts=24, confirm=20)
        good = res is not None and res["predicted"] == unrank(ranks[-1])
        checks.append((f"témoin positif, mapping {'floor' if fm else 'mod'} : "
                       f"20 numéros prédits exacts", good,
                       "oui" if good else "NON"))

    for count, seed, label in ((60, 20260824, "60 tirages"),
                               (60, 987654321, "60 tirages, autre graine"),
                               (8, 20260824, "8 tirages (trop court)")):
        r = solve(synthetic_ranks(count, seed), starts=24, confirm=20)
        checks.append((f"témoin négatif, {label} : silence", r is None,
                       "silence" if r is None else "FAUSSE SOLUTION"))

    cnt64 = [len(candidates(rng.randrange(MOD), 64, fm))
             for fm in (False, True) for _ in range(200)]
    good = min(cnt64) >= 5 and max(cnt64) <= 6
    checks.append(("ambiguïté bornée à 6 états par tirage (b = 64)", good,
                   f"{min(cnt64)}–{max(cnt64)}"))

    for label, good, val in checks:
        print(f"     {label:<58} {val:>16}   {'ok' if good else 'ÉCHEC'}")
        ok &= good

    # 8. Le détecteur de LARGEUR de source, et ses assertions Swift.
    def reachable(r, b):
        if b >= 62:
            return True
        two_b = 1 << b
        k_min = (r * two_b + MOD - 1) // MOD
        return k_min < two_b and rank_of(k_min, b, True) == r

    def narrow_width(ranks):
        n = len(ranks)
        if n < 24:
            return None
        widths = (24, 31, 32, 48, 53, 56, 60, 61)
        share = {b: (1 << b) / MOD for b in widths}
        rate = {b: sum(1 for r in ranks if reachable(r, b)) / n for b in widths}
        for b in widths:
            if share[b] < 0.8 and rate[b] >= 0.9:
                return b
        for b in widths:
            p, sd = share[b], math.sqrt(n * share[b] * (1 - share[b]))
            if rate[b] * n > n * p + 8 * max(sd, 1):
                return b
        return None

    def narrow_ranks(bits, count=60):
        seed = 0xDEADBEEF12345678
        out = []
        for _ in range(count):
            seed = (seed * 6364136223846793005 + 1) & M64
            k = seed >> (64 - bits)
            out.append((k * MOD) >> bits)
        return out

    print("\n8. détecteur de largeur de source :")
    checks = []
    for bits in (32, 48, 53):
        got = narrow_width(narrow_ranks(bits))
        checks.append((f"source {bits} bits détectée", got == bits, str(got)))
    for count, seed, label in ((200, 20260824, "200 tirages"),
                               (200, 13579, "200 tirages, autre graine"),
                               (10, 20260824, "10 tirages (trop court)")):
        got = narrow_width(synthetic_ranks(count, seed))
        checks.append((f"témoin négatif, {label} : silence", got is None,
                       "silence" if got is None else f"FAUX {got}"))
    seed, honest = 4242, 0
    for _ in range(400):
        seed = (seed * 6364136223846793005 + 1) & M64
        if reachable(seed % MOD, 53):
            honest += 1
    checks.append(("densité honnête à 53 bits (~1 sur 400)", honest < 10, str(honest)))
    for label, good, val in checks:
        print(f"     {label:<58} {val:>16}   {'ok' if good else 'ÉCHEC'}")
        ok &= good

    print(f"\n{'=' * 74}")
    print("VERDICT :", "RankAttack se comporte comme annoncé"
          if ok else "AU MOINS UNE BRIQUE EST FAUSSE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
