"""Vérification par exécution de la logique ajoutée à Swarm.swift.

`verif_swift.py` établit que la syntaxe est valide. Il ne dit rien de ce que
le code CALCULE. Ce fichier transcrit fidèlement les fonctions ajoutées —
même formule, même ordre d'opérations — et vérifie que chaque assertion des
tests Swift serait satisfaite.

Ce n'est pas une compilation : un désaccord de types resterait invisible.
Mais l'ordre des arguments des initialiseurs par membre, qui est ici le
risque de typage le plus probable, est contrôlé séparément, et la syntaxe
l'est par une grammaire Swift réelle. Ce qui restait non vérifié était la
justesse numérique — c'est l'objet de ce fichier.
"""
from math import comb as exact_comb


def comb(n, k):
    """Transcription littérale de `SwarmEngine.comb` (produit incrémental)."""
    if k < 0 or k > n:
        return 0.0
    if k == 0 or k == n:
        return 1.0
    kk = min(k, n - k)
    r = 1.0
    for i in range(1, kk + 1):
        r *= (n - kk + i) / i
    return r


POOL, DRAWN = 80, 20


def hypergeometric_p_all(k):
    return comb(DRAWN, k) / comb(POOL, k)


def hypergeometric_tail(k, t):
    if t > k:
        return 0.0
    acc = 0.0
    for h in range(max(0, t), k + 1):
        acc += comb(DRAWN, h) * comb(POOL - DRAWN, k - h)
    return acc / comb(POOL, k)


def pack_p_all_hit(grids, stake):
    if not grids:
        return 0.0
    acc = len(grids) * hypergeometric_p_all(stake)
    for i in range(len(grids)):
        a = set(grids[i])
        for j in range(i + 1, len(grids)):
            acc -= hypergeometric_p_all(len(a | set(grids[j])))
    return max(0.0, acc)


def greedy_pick(score, k, cap, banned=frozenset()):
    """`greedyPick` réduit au plafond par dizaine et au bannissement."""
    picked, dec = [], [0] * 8
    order = sorted(range(POOL), key=lambda n: -score[n])
    for n in order:
        if n in banned or n in picked:
            continue
        d = n // 10
        if dec[d] >= cap:
            continue
        picked.append(n); dec[d] += 1
        if len(picked) == k:
            break
    if len(picked) < k:                      # branche de repli, plafond ignoré
        for n in order:
            if n in banned or n in picked:
                continue
            picked.append(n)
            if len(picked) == k:
                break
    return sorted(picked)


def make_grids(fields, stake, spread_penalty=1e6):
    """`makeGrids` : préférence de couverture sur les 3 familles x 4 variantes."""
    cover = [0.0] * POOL
    grids = []
    pop = [0.0] * POOL
    for n in range(1, POOL + 1):
        s = 0.0
        if n <= 31: s += 1.0
        if n <= 12: s += 0.4
        if n % 10 == 7: s += 0.5
        if n % 11 == 0: s += 0.4
        if n % 10 == 0: s += 0.2
        pop[n - 1] = s
    for name in ("alpha", "omega", "nexus"):
        src = fields[name]
        cap = max(2, -(-stake // 5) + 1) if name == "nexus" else stake
        base = [src[i] - spread_penalty * cover[i] for i in range(POOL)]
        first = greedy_pick(base, stake, cap)
        for n in first: cover[n] += 1
        base = [src[i] - spread_penalty * cover[i] for i in range(POOL)]
        second = greedy_pick(base, stake, cap, banned=frozenset(first))
        for n in second: cover[n] += 1
        base = [-src[i] - spread_penalty * cover[i] for i in range(POOL)]
        anti = greedy_pick(base, stake, cap)
        for n in anti: cover[n] += 1
        base = [src[i] - 0.4 * pop[i] - spread_penalty * cover[i] for i in range(POOL)]
        stealth = greedy_pick(base, stake, cap)
        for n in stealth: cover[n] += 1
        grids += [first, second, anti, stealth]
    return grids, cover


def main():
    import random
    rng = random.Random(20260827)
    ok = True

    print("=" * 74)
    print("VÉRIFICATION PAR EXÉCUTION — chaque assertion des tests Swift")
    print("=" * 74)

    # 1. comb : la formule incrémentale du code contre la valeur exacte.
    worst = max(abs(comb(n, k) - exact_comb(n, k)) / max(exact_comb(n, k), 1)
                for n in (60, 80) for k in range(0, 21))
    print(f"\n1. comb() incrémental contre exact : écart relatif max {worst:.2e}"
          f"  {'ok' if worst < 1e-12 else 'ÉCHEC'}")
    ok &= worst < 1e-12

    # 1 bis. overlapSD : la formule fermée du code contre la loi terme à terme.
    # C'est testDisplayedSigmaUsesTheExactLawNotAnEstimate.
    tot = exact_comb(80, 20)
    mean = sum(o * exact_comb(20, o) * exact_comb(60, 20 - o) / tot for o in range(21))
    square = sum(o * o * exact_comb(20, o) * exact_comb(60, 20 - o) / tot for o in range(21))
    sd_loi = (square - mean * mean) ** 0.5
    sd_code = (20 * 0.25 * (1 - 0.25) * (80 - 20) / (80 - 1)) ** 0.5
    a = abs(mean - 5.0) < 1e-9
    b = abs(sd_loi - sd_code) < 1e-9
    c = abs(sd_code - 1.6876317) < 1e-6
    print(f"\n1 bis. overlapSD : espérance {mean:.12f} (attendu 5)  "
          f"{'ok' if a else 'ÉCHEC'}")
    print(f"       loi terme à terme {sd_loi:.12f} contre formule fermée "
          f"{sd_code:.12f}  {'ok' if b else 'ÉCHEC'}")
    print(f"       valeur affichée dans le test 1,6876317  {'ok' if c else 'ÉCHEC'}")
    ok &= a and b and c

    # 1 ter. testRestartMixtureSeesALateDefectThatACumulativeBetCannot :
    # même arithmétique, même graine, même LCG que le test Swift — forme
    # martingale par BLOCS (h2) : au 1er pas du bloc j, S += w_j = 1/(j(j+1)),
    # puis S *= f ; N = S + 1/(bloc_courant + 2).
    import math as _m

    def _lae(a, b):
        if a == -_m.inf:
            return b
        if b == -_m.inf:
            return a
        hi = max(a, b)
        return hi + _m.log1p(_m.exp(min(a, b) - hi))

    def _traj(defect_first):
        seed = 20260827
        m64 = (1 << 64) - 1

        def bern(q):
            nonlocal seed
            seed = (seed * 6364136223846793005 + 1442695040888963407) & m64
            return 1.0 if (seed >> 33) / 2147483648.0 < q else 0.0

        theta, pb = 0.40, 0.25
        log_m = _m.log(pb * _m.exp(theta) + (1 - pb))
        quiet, loud, block = 20000, 400, 16
        cum, sr, mc, mn, n = 0.0, -_m.inf, 0.0, 0.0, 0.0
        for t in range(quiet + loud):
            biased = t < loud if defect_first else t >= quiet
            x = 1.0 if biased else bern(pb)
            lf = theta * x - log_m
            cum += lf
            if t % block == 0:
                j = t // block + 1
                sr = _lae(sr, -_m.log(j * (j + 1)))
            sr = min(700, sr + lf)
            mc = max(mc, cum)
            n = _m.exp(min(700, sr)) + 1.0 / (t // block + 2)
            mn = max(mn, n)
        return _m.exp(cum), _m.exp(mc), n, mn

    lc_f, lc_s, ln_f, _ = _traj(False)
    ec_f, ec_s, en_f, en_s = _traj(True)
    checks = [
        ("valeur finale du pari cumule identique tot/tard",
         abs(lc_f - ec_f) <= 1e-12 * max(1.0, ec_f), f"{lc_f:.3e} contre {ec_f:.3e}"),
        ("defaut TARDIF : sup du pari cumule sous 20", lc_s < 20, f"{lc_s:.3f}"),
        ("defaut TARDIF : martingale par blocs au-dessus de 1e40", ln_f > 1e40, f"{ln_f:.3e}"),
        ("temoin, defaut TOT : sup du pari cumule au-dessus de 20", ec_s > 20, f"{ec_s:.3e}"),
        ("temoin, defaut TOT : sup de la martingale au-dessus de 1e45", en_s > 1e45, f"{en_s:.3e}"),
        ("defaut TOT : richesse relancee depensee en fin de course", en_f < 1, f"{en_f:.3e}"),
    ]
    print("\n1 ter. melange de relances par blocs, forme martingale (h2) :")
    for label, good, val in checks:
        print(f"       {label:<56} {val:>12}   {'ok' if good else 'ÉCHEC'}")
        ok &= good

    for stake in (5, 6, 7, 8, 10):
        tail = [hypergeometric_tail(stake, t) for t in range(stake + 1)]
        p_all = hypergeometric_p_all(stake)

        # 2. testTailLawIsExactHypergeometric
        ref = []
        for t in range(stake + 1):
            e = sum(exact_comb(20, h) * exact_comb(60, stake - h) for h in range(t, stake + 1))
            ref.append(e / exact_comb(80, stake))
        a = abs(tail[0] - 1.0) < 1e-12
        b = all(abs(tail[t] - ref[t]) < 1e-9 for t in range(stake + 1))
        c = all(tail[t] <= tail[t - 1] for t in range(1, stake + 1))
        d = abs(tail[stake] - p_all) < 1e-12
        ok &= a and b and c and d

        # 3. testGridPackIsSpread + testGridPackHasNoNearDuplicatePair
        fields = {n: [rng.gauss(0, 1) for _ in range(POOL)] for n in ("alpha", "omega", "nexus")}
        grids, cover = make_grids(fields, stake)
        distinct = len({n for g in grids for n in g})
        want = min(12 * stake, 80)
        max_cover = int(max(cover))
        ceiling_cov = (12 * stake + 79) // 80
        pairs_max = max(len(set(grids[i]) & set(grids[j]))
                        for i in range(12) for j in range(i + 1, 12))
        e = distinct == want
        f = max_cover <= ceiling_cov
        g = pairs_max <= stake // 2
        ok &= e and f and g

        # 4. testPackProbabilityIsExactAndNearItsCeiling
        pack = pack_p_all_hit(grids, stake)
        ceiling = 12 * p_all
        h = p_all < pack <= ceiling and pack > 0.98 * ceiling
        ok &= h

        print(f"\n  mise {stake}")
        print(f"    loi de survie exacte, décroissante, tail[k]=P(pleine)   "
              f"{'ok' if a and b and c and d else 'ÉCHEC'}")
        print(f"    couverture {distinct}/{want} attendus, max {max_cover}<={ceiling_cov}   "
              f"{'ok' if e and f else 'ÉCHEC'}")
        print(f"    recouvrement max entre 2 grilles {pairs_max} <= {stake // 2}   "
              f"{'ok' if g else 'ÉCHEC'}")
        print(f"    paquet 1/{1/pack:,.0f} contre 1/{1/p_all:,.0f} seule, "
              f"{pack / ceiling:.5f} du plafond   {'ok' if h else 'ÉCHEC'}")

    print(f"\n{'=' * 74}")
    print("VERDICT :", "toutes les assertions des tests Swift sont satisfaites"
          if ok else "AU MOINS UNE ASSERTION ÉCHOUERAIT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
