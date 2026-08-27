"""Audit de la production de grilles : correcte ? optimale pour gagner ?

Deux questions distinctes, et il faut les séparer.

CORRECTION — le code fait-il ce qu'il annonce ? Vérifié ici sur les
formules exactes et sur les invariants que la structure impose.

OPTIMALITÉ — à espérance figée (`E[hits] = k/4` quel que soit le choix,
et `E[gain] invariant sous TOUTE table de gains par grille`, cf. §6 du
rapport), la seule chose optimisable est la GÉOMÉTRIE du paquet de 12.
`b1_geometrie.py` l'avait bornée entre deux hypothèses de corrélation
inter-familles. Ce fichier la mesure.

Le paquet est 3 familles (alpha, omega, nexus) × 4 variantes :
    I       top-k du champ
    II      top-k suivant, banni de I — disjoint par construction
    Anti    top-k du champ INVERSÉ
    Furtif  top-k du champ pénalisé par la popularité humaine

Trois sources de duplication possibles, et elles ne se valent pas :
  1. Furtif contre I — même champ, même sens, seule une pénalité les
     sépare. C'est mesurable exactement, sans rien supposer des têtes :
     les champs sont des z-scores, donc du bruit standardisé.
  2. Anti contre I — opposés dans le classement, donc disjoints tant que
     le plafond par dizaine ne mord pas.
  3. Les trois familles entre elles — mélanges des mêmes 26 têtes sur le
     même historique, donc corrélées.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN


def popularity():
    """`Swarm.popularity` (Swarm.swift:1122), transcrit à l'identique."""
    p = np.zeros(POOL)
    for n in range(1, POOL + 1):
        s = 0.0
        if n <= 31: s += 1.0
        if n <= 12: s += 0.4
        if n % 10 == 7: s += 0.5
        if n % 11 == 0: s += 0.4
        if n % 10 == 0: s += 0.2
        p[n - 1] = s
    return p


POP = popularity()


def greedy(score, k, cap, banned=frozenset()):
    """`greedyPick` réduit au plafond par dizaine et au bannissement.

    Les ajustements propres à nexus (PMI, équilibre pair/impair) et à omega
    (pénalité d'adjacence) sont omis : ils perturbent l'ordre à la marge et
    ne changent pas la question posée, qui est la duplication entre grilles.
    """
    picked, dec = [], [0] * 8
    for n in np.argsort(-score):
        if n in banned or n in picked:
            continue
        d = n // 10
        if dec[d] >= cap:
            continue
        picked.append(int(n)); dec[d] += 1
        if len(picked) == k:
            break
    return picked


def pack_app(fields, k):
    """Les 12 grilles telles que `makeGrids` les produit."""
    grids = []
    for name, src in fields.items():
        cap = max(2, -(-k // 5) + 1) if name == "nexus" else k
        first = greedy(src, k, cap)
        second = greedy(src, k, cap, banned=frozenset(first))
        anti = greedy(-src, k, cap)
        stealth = greedy(src - 0.4 * POP, k, cap)
        grids += [first, second, anti, stealth]
    return grids


def jaccard(a, b):
    A, B = set(a), set(b)
    return len(A & B) / len(A | B)


def geometry(grids, k):
    """Ce qui décide : couverture, duplication, et loi du paquet."""
    cover = np.zeros(POOL, int)
    for g in grids:
        cover[g] += 1
    dup = [len(set(a) & set(b)) for i, a in enumerate(grids) for b in grids[i + 1:]]
    return {
        "numeros couverts": int((cover > 0).sum()),
        "recouvrement moyen entre 2 grilles": float(np.mean(dup)),
        "paires de grilles identiques": int(sum(1 for d in dup if d == k)),
        "couverture max d'un numero": int(cover.max()),
    }


def outcome(grids, k, reps, rng):
    """Loi du paquet sous H0 : variance, tout-perdre, au moins une pleine."""
    idx = np.array([[n for n in g] for g in grids])
    tot = np.empty(reps); mx = np.empty(reps, int); full = 0
    B = 200_000
    done = 0
    tots, mxs = [], []
    while done < reps:
        b = min(B, reps - done)
        m = lab.srs(b, rng)
        h = m[:, idx].sum(2)                      # (b, 12) hits par grille
        tots.append(h.sum(1)); mxs.append(h.max(1))
        full += int((h == k).any(1).sum())
        done += b
    tot = np.concatenate(tots); mx = np.concatenate(mxs)
    return {"E[total]": float(tot.mean()), "Var(total)": float(tot.var(ddof=1)),
            "P(zero hit)": float((tot == 0).mean()), "E[max]": float(mx.mean()),
            "P(>=1 grille pleine)": full / reps}


# ---------------------------------------------------------------------------
# Émulation des trois champs — la question qui décide
# ---------------------------------------------------------------------------

def zs(v):
    s = v.std()
    return (v - v.mean()) / s if s > 0 else v * 0


def three_fields(mask):
    """alpha (momentum), omega (reversion), nexus (ensemble).

    Fidèle à ce qui détermine la géométrie : les têtes `momentum` suivent la
    fréquence RÉCENTE (EWMA, Hawkes, spectral court-long, Markov), les têtes
    `reversion` suivent le RETARD (Weibull, hasard, écart-z, adjacence,
    pression de rangée). Or le retard est, à peu de chose près, l'opposé de
    la fréquence récente — c'est ce que ce fichier vérifie.
    """
    n = POOL
    e8 = np.full(n, 0.25); e25 = np.full(n, 0.25); e64 = np.full(n, 0.25)
    h23 = np.zeros(n); h39 = np.zeros(n); h87 = np.zeros(n)
    a = np.full(n, 2.0); b = np.full(n, 6.0)
    gap = np.zeros(n)
    for row in mask:
        hit = row.astype(float)
        for arr, m in ((None, None),):
            pass
        e8 = (1 - 1/8) * e8 + (1/8) * hit
        e25 = (1 - 1/25) * e25 + (1/25) * hit
        e64 = (1 - 1/64) * e64 + (1/64) * hit
        h23 = np.exp(-1/2.3) * h23 + hit
        h39 = np.exp(-1/3.9) * h39 + hit
        h87 = np.exp(-1/8.7) * h87 + hit
        a = (1 - 1/33) * a + hit
        b = (1 - 1/33) * b + (1 - hit)
        gap = np.where(row, 0, gap + 1)

    momentum = [zs(e8), zs(e25), zs(e64), zs(h23), zs(h39), zs(h87),
                zs(e8 - e64), zs(e25 - e64)]                     # spectral court-long
    reversion = [zs(gap), zs(np.sqrt(np.maximum(gap, 0))), zs(gap ** 1.25),
                 zs(gap ** 1.55), zs(gap - gap.mean()), zs(gap)]  # Weibull/hasard/écart-z
    structure = [zs(a / (a + b)), zs(a), zs(b)]
    alpha = np.mean(momentum, axis=0)
    omega = np.mean(reversion, axis=0)
    nexus = np.mean(momentum + reversion + structure, axis=0)
    return {"alpha": zs(alpha), "omega": zs(omega), "nexus": zs(nexus)}


def main():
    rng = np.random.default_rng(20260827)
    print("=" * 78)
    print("AUDIT — la production de grilles est-elle optimale pour gagner ?")
    print("=" * 78)

    print("\n1. FURTIF DUPLIQUE-T-IL LA VARIANTE I ?")
    print("   Mesure pure : les champs sont des z-scores, donc du bruit standardisé.")
    print(f"   {'mise':>5}{'recouvrement I/Furtif':>26}{'Jaccard':>11}")
    for k in (5, 10):
        ov, jc = [], []
        for _ in range(4000):
            src = rng.standard_normal(POOL)
            f = greedy(src, k, k)
            s = greedy(src - 0.4 * POP, k, k)
            ov.append(len(set(f) & set(s))); jc.append(jaccard(f, s))
        print(f"   {k:>5}{np.mean(ov):>18.2f} / {k:<5}{np.mean(jc):>11.2f}")

    print("\n2. LES TROIS FAMILLES SONT-ELLES INDÉPENDANTES ?")
    cors = {"alpha/omega": [], "alpha/nexus": [], "omega/nexus": []}
    for _ in range(300):
        F = three_fields(lab.srs(400, rng))
        cors["alpha/omega"].append(np.corrcoef(F["alpha"], F["omega"])[0, 1])
        cors["alpha/nexus"].append(np.corrcoef(F["alpha"], F["nexus"])[0, 1])
        cors["omega/nexus"].append(np.corrcoef(F["omega"], F["nexus"])[0, 1])
    for kk, v in cors.items():
        print(f"   corr({kk:<12}) = {np.mean(v):+.3f}  ± {np.std(v):.3f}")

    print("\n3. GÉOMÉTRIE RÉELLE DU PAQUET DE 12")
    for k in (5, 10):
        F = three_fields(lab.srs(400, rng))
        grids = pack_app(F, k)
        g = geometry(grids, k)
        print(f"\n   mise {k} :")
        for kk, v in g.items():
            print(f"     {kk:<38} {v}")
        # duplication par paire nommee
        names = [f"{f}.{v}" for f in ("alpha", "omega", "nexus")
                 for v in ("I", "II", "Anti", "Furtif")]
        pairs = [(names[i], names[j], len(set(grids[i]) & set(grids[j])))
                 for i in range(12) for j in range(i + 1, 12)]
        pairs.sort(key=lambda t: -t[2])
        print(f"     paires les plus dupliquées :")
        for a, b, d in pairs[:5]:
            print(f"       {a:<14} {b:<14} {d}/{k} numéros communs")


if __name__ == "__main__":
    main()


def optimal_pack(k, rng):
    """La géométrie de référence : disjointe si possible, sinon équilibrée."""
    if 12 * k <= POOL:
        perm = rng.permutation(POOL)
        return [sorted(perm[i * k:(i + 1) * k].tolist()) for i in range(12)]
    cover = np.zeros(POOL, int)
    grids = []
    for _ in range(12):
        order = np.lexsort((rng.random(POOL), cover))
        g = sorted(order[:k].tolist())
        cover[g] += 1
        grids.append(g)
    return grids


def compare(reps=4_000_000):
    rng = np.random.default_rng(4242)
    print("\n" + "=" * 78)
    print("4. CE QUE LA DUPLICATION COÛTE")
    print("=" * 78)
    for k in (5, 10):
        F = three_fields(lab.srs(400, rng))
        packs = {
            "app (mesurée)": pack_app(F, k),
            "optimale (disjointe/équilibrée)": optimal_pack(k, rng),
            "12 grilles aléatoires": [sorted(rng.choice(POOL, k, replace=False).tolist())
                                      for _ in range(12)],
        }
        print(f"\n   mise {k} — {reps:,} réplicats")
        print(f"   {'géométrie':<34}{'couvre':>8}{'Var(tot)':>10}"
              f"{'P(0 hit)':>11}{'P(>=1 pleine)':>15}")
        for name, g in packs.items():
            o = outcome(g, k, reps, rng)
            cov = len({n for gg in g for n in gg})
            print(f"   {name:<34}{cov:>5}/80{o['Var(total)']:>10.2f}"
                  f"{o['P(zero hit)']:>11.2e}{o['P(>=1 grille pleine)']:>15.3e}")
            assert abs(o["E[total]"] - 3 * k) < 0.02, "E[total] doit valoir 3k partout"
        print(f"   (contrôle : E[total] = {3*k} vérifié sur les trois — l'espérance est invariante)")
