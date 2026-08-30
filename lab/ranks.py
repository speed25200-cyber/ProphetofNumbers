"""Primitives du rang combinatoire — partagées par h4, h5 et h6.

Ce module existe pour une raison précise : `h5` et `h6` importaient leurs
primitives depuis `h4_rangs.py`, qui est un SCRIPT. Importer un script en
rejoue tout le corps — h4 refaisait donc son archive et son attaque à chaque
import, en polluant la sortie des deux autres expériences. Les primitives
sont ici, sans effet de bord, et les scripts restent des scripts.

Le fait central, celui qui rend toute la classe d'attaques possible :

    M = C(80, 20) = 3 535 316 142 212 174 320 ≈ 2^61,6165

Un tirage de 20 numéros parmi 80 porte donc 61,62 bits — et un état de
64 bits n'en cache que 2,38 derrière son rang.
"""

import math

POOL, DRAWN = 80, 20

# C(n, k) pour n ≤ 80, k ≤ 20 — la même récurrence que le Swift.
BIN = [[math.comb(n, k) if k <= n else 0 for k in range(DRAWN + 1)]
       for n in range(POOL + 1)]
M = BIN[POOL][DRAWN]


def rank_of(nums) -> int:
    """Rang colex du sous-ensemble trié (numéros 1..80) — bijectif sur [0, M)."""
    return sum(BIN[n - 1][i + 1] for i, n in enumerate(sorted(nums)))


def unrank(r: int) -> list:
    """Inverse exact de `rank_of` : du rang vers les 20 numéros."""
    out = []
    for i in range(DRAWN, 0, -1):
        c = i - 1
        while BIN[c + 1][i] <= r:
            c += 1
        out.append(c + 1)
        r -= BIN[c][i]
    return sorted(out)


def candidates(r: int, b: int, mapping: str) -> list:
    """États de b bits compatibles avec un rang observé — au plus 6 pour b = 64."""
    mod = 1 << b
    if mapping == "mod":
        out, s = [], r
        while s < mod:
            out.append(s)
            s += M
        return out
    lo = (r * mod + M - 1) // M
    hi = ((r + 1) * mod + M - 1) // M
    return [s for s in range(lo, min(hi, mod))]


# Contrôles de bijectivité, exécutés à l'import : une table fausse doit
# échouer ici, pas silencieusement au milieu d'une expérience.
assert unrank(rank_of([1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                       11, 12, 13, 14, 15, 16, 17, 18, 19, 80])) == \
    sorted([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 80])
assert rank_of(list(range(1, 21))) == 0
assert rank_of(list(range(61, 81))) == M - 1
assert M == math.comb(80, 20)
