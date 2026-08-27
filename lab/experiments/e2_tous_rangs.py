"""L'étalement est-il optimal à TOUS les rangs, ou seulement au sommet ?

`e1_audit_grilles.py` a corrigé la géométrie du paquet en maximisant
`P(au moins une grille pleine)`. Ce choix d'objectif n'avait pas été
justifié — et il ne va pas de soi : une table de gains de Keno paie
plusieurs rangs (k, k−1, k−2…), et une géométrie optimale au sommet
pourrait être mauvaise en dessous.

La question est réelle parce que les deux régimes tirent en sens opposé.
Étaler DÉCORRÈLE les grilles : bon pour que l'UNE d'elles fasse un gros
score. Concentrer les CORRÈLE : quand ça marche, tout marche ensemble.
Selon le rang visé, l'un ou l'autre pourrait gagner.

On calcule donc `P(au moins une grille atteint t hits)` pour tout t, sur
les trois géométries, et on regarde s'il existe une dominance ou un
arbitrage. S'il y a arbitrage, le choix d'objectif doit être explicite
dans le produit ; s'il y a dominance, la question est close.

Le barème réel n'étant pas publié (cf. §5 du rapport), on ne peut pas
pondérer les rangs — mais une dominance rendrait cette ignorance sans
conséquence, ce qui est exactement le résultat qu'on espère.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from math import comb
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_audit_grilles as e1


def spread_pack(F, k):
    """La géométrie corrigée : préférence de couverture (Swarm.spreadPenalty)."""
    BIG = 1e6
    cover = np.zeros(POOL)
    grids = []
    for name, src in F.items():
        cap = max(2, -(-k // 5) + 1) if name == "nexus" else k
        for variant in range(4):
            s = (-src if variant == 2 else src).copy()
            if variant == 3:
                s = s - 0.4 * e1.POP
            g = e1.greedy(s - BIG * cover, k, cap)
            grids.append(g)
            cover[g] += 1
    return grids


def tiers(grids, k, reps, rng, block=250_000):
    """P(au moins une grille atteint t hits), pour t = 1..k. Monte-Carlo.

    Les rangs bas sont fréquents, donc mesurables ; le rang k est traité à
    part par le calcul exact (`e1`), le Monte-Carlo y étant sans objet.
    """
    idx = np.array(grids)
    hi = np.zeros(k + 1)
    done = 0
    while done < reps:
        b = min(block, reps - done)
        m = lab.srs(b, rng)
        mx = m[:, idx].sum(2).max(1)
        for t in range(1, k + 1):
            hi[t] += int((mx >= t).sum())
        done += b
    return hi / reps


def p_full_exact(grids, k):
    """P(au moins une grille pleine), exacte — l'ordre 3 est négligeable."""
    def pset(m):
        return comb(DRAWN, m) / comb(POOL, m) if m <= DRAWN else 0.0
    s = len(grids) * pset(k)
    for i in range(len(grids)):
        for j in range(i + 1, len(grids)):
            s -= pset(len(set(grids[i]) | set(grids[j])))
    return s


def main():
    t0 = time.time()
    rng = np.random.default_rng(20260827)
    REPS = 3_000_000

    print("=" * 78)
    print("L'ÉTALEMENT EST-IL OPTIMAL À TOUS LES RANGS ?")
    print("=" * 78)

    for k in (5, 10):
        F = e1.three_fields(lab.srs(400, rng))
        packs = {
            "app (avant correctif)": e1.pack_app(F, k),
            "étalée (après)": spread_pack(F, k),
            "concentrée (anti-témoin)": [sorted(rng.choice(30, k, replace=False).tolist())
                                         for _ in range(12)],
        }
        print(f"\nmise {k} — {REPS:,} réplicats, plus le rang plein en exact")
        res = {n: tiers(g, k, REPS, rng) for n, g in packs.items()}
        exact = {n: p_full_exact(g, k) for n, g in packs.items()}

        header = f"  {'géométrie':<26}" + "".join(f"{'t=' + str(t):>12}" for t in range(1, k + 1))
        print(header)
        for n in packs:
            row = "".join(f"{res[n][t]:>12.4f}" if res[n][t] > 1e-4 else f"{res[n][t]:>12.2e}"
                          for t in range(1, k + 1))
            print(f"  {n:<26}{row}")
        print(f"  {'(rang plein, exact)':<26}" +
              "".join(f"{'':>12}" for _ in range(1, k)) + f"{exact['étalée (après)']:>12.3e}")

        ref = res["étalée (après)"]
        print(f"\n  Rapport étalée / app, rang par rang :")
        gains = []
        for t in range(1, k + 1):
            a = res["app (avant correctif)"][t]
            g = ref[t] / a if a > 0 else float("inf")
            gains.append(g)
            if t <= 3 or t >= k - 2:
                print(f"    t = {t:<3} {g:.4f}")
        exact_gain = exact["étalée (après)"] / exact["app (avant correctif)"]
        print(f"    t = {k} (exact) {exact_gain:.4f}")
        dominant = all(x >= 0.999 for x in gains) and exact_gain >= 0.999
        print(f"\n  -> l'étalement domine à tous les rangs : {'OUI' if dominant else 'NON'}")

    print(f"\n{'=' * 78}\ntotal {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Rangs hauts : le Monte-Carlo n'y suffit pas, le calcul exact décide
# ---------------------------------------------------------------------------

def p_single_at_least(k, t):
    """P(une grille de k atteint t hits) — hypergéométrique exacte."""
    tot = comb(POOL, k)
    return sum(comb(DRAWN, h) * comb(POOL - DRAWN, k - h) for h in range(t, k + 1)) / tot


def p_pair_at_least(k, s, t):
    """P(DEUX grilles de k, partageant s numéros, atteignent chacune t hits).

    Décomposition exacte : les deux grilles sont A∪C et B∪C avec |C| = s et
    |A| = |B| = k−s. La loi jointe de (|A∩D|, |B∩D|, |C∩D|) est
    hypergéométrique multivariée. C'est ce terme qui porte tout l'effet de la
    duplication : deux grilles identiques gagnent ensemble, donc comptent
    pour une seule occasion.
    """
    m = k - s
    rest = POOL - (2 * m + s)
    tot = comb(POOL, DRAWN)
    acc = 0.0
    for c in range(0, min(s, DRAWN) + 1):
        for a in range(0, min(m, DRAWN - c) + 1):
            if a + c < t:
                continue
            for b in range(0, min(m, DRAWN - c - a) + 1):
                if b + c < t:
                    continue
                r = DRAWN - a - b - c
                if r < 0 or r > rest:
                    continue
                acc += comb(m, a) * comb(m, b) * comb(s, c) * comb(rest, r)
    return acc / tot


def p_any_at_least_exact(grids, k, t):
    """Inclusion-exclusion à l'ordre 2. Valide uniquement quand S1 est petit —
    aux rangs bas la somme dépasse 1 et il faut le Monte-Carlo."""
    s1 = len(grids) * p_single_at_least(k, t)
    s2 = 0.0
    for i in range(len(grids)):
        for j in range(i + 1, len(grids)):
            s = len(set(grids[i]) & set(grids[j]))
            s2 += p_pair_at_least(k, s, t)
    return s1 - s2, s1, s2


def high_tiers():
    rng = np.random.default_rng(20260827)
    print("\n" + "=" * 78)
    print("RANGS HAUTS — CALCUL EXACT (le Monte-Carlo y compte 4 à 250 événements)")
    print("=" * 78)
    for k, ts in ((5, (4, 5)), (10, (8, 9, 10))):
        F = e1.three_fields(lab.srs(400, rng))
        packs = {"app (avant)": e1.pack_app(F, k), "étalée (après)": spread_pack(F, k)}
        print(f"\n  mise {k}")
        print(f"  {'rang':>6}{'app (avant)':>18}{'étalée (après)':>18}{'rapport':>11}")
        for t in ts:
            vals = {}
            for n, g in packs.items():
                p, s1, s2 = p_any_at_least_exact(g, k, t)
                vals[n] = p
            r = vals["étalée (après)"] / vals["app (avant)"]
            flag = "" if r >= 0.999 else "   <-- l'étalement PERD ici"
            print(f"  {t:>6}{vals['app (avant)']:>18.6e}{vals['étalée (après)']:>18.6e}"
                  f"{r:>11.4f}{flag}")
