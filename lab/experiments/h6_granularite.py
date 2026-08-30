"""h6 — le budget d'entropie du tirage, lu directement dans ses rangs.

L'idée, et pourquoi elle est décisive
--------------------------------------
h4 a montré que le rang combinatoire d'un tirage vit dans [0, M) avec
M = C(80,20) ≈ 2^61,6165. Cela veut dire qu'un tirage HONNÊTE consomme
61,62 bits d'entropie. Et cela ouvre une question que personne n'a posée :

    combien de bits la source en fournit-elle RÉELLEMENT ?

Si l'implémentation écrit `unrank(floor(u * M))` où `u` est un double —
`Math.random()` en JavaScript, `random.random()` en Python — alors u ne
porte que **53 bits**, et les rangs atteignables ne sont que 2^53 valeurs
sur 2^61,6 : un ensemble de densité 1/392. Autrement dit, **99,74 % des
rangs deviennent impossibles**, et un rang réel les évite tous.

Le test tient en une ligne d'arithmétique exacte. r est atteignable par
⌊k·M / 2^B⌋ si et seulement si l'intervalle [r·2^B/M, (r+1)·2^B/M) contient
un entier — c'est-à-dire

    k_min = ⌈r·2^B / M⌉    et    k_min · M < (r+1) · 2^B

Sur 70 560 tirages, le pouvoir de séparation est écrasant : sous une source
53 bits on attend **70 560 rangs atteignables sur 70 560** ; sous une source
honnête, **180**. Il n'existe pas de zone grise.

Et l'enjeu n'est pas académique. Si le test se déclenchait, l'espace d'états
s'effondrerait de 2^61,6 à 2^B — 2^53 est déjà à portée d'un balayage, 2^32
tient dans une seconde. La prédiction exacte redeviendrait possible, par la
force brute cette fois, là où l'attaque algébrique de h4 est muette (elle
suppose un LCG ; ce test-ci ne suppose RIEN sur la récurrence, seulement sur
la largeur de la source).

Le mapping `s mod M` se teste encore plus simplement : si s < 2^B avec
B < 61,62, alors r = s et le rang maximal observé ne peut pas dépasser 2^B.

Témoins des deux côtés, comme toujours : des archives fabriquées à B bits
doivent sortir à 100 % d'atteignabilité, des archives équitables doivent
retomber exactement sur la densité théorique 2^B/M.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
from ranks import rank_of, unrank, M, BIN

T0 = time.time()
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def rank_of_draw(nums) -> int:
    return sum(BIN[n - 1][i + 1] for i, n in enumerate(sorted(nums)))


def reachable(r: int, b: int) -> bool:
    """r est-il de la forme ⌊k·M / 2^B⌋ pour un entier k < 2^B ?"""
    two_b = 1 << b
    k_min = (r * two_b + M - 1) // M          # ⌈r·2^B / M⌉
    return k_min < two_b and k_min * M < (r + 1) * two_b


WIDTHS = [24, 31, 32, 48, 53, 56, 60, 61, 62, 63, 64]


def profile(ranks, widths=WIDTHS):
    return {b: sum(1 for r in ranks if reachable(r, b)) for b in widths}


# --------------------------------------------------------------------------
# 1. Témoins
# --------------------------------------------------------------------------

rule("1. TÉMOINS — le test sépare-t-il vraiment les deux mondes ?")

rng = np.random.default_rng(31337)
say("   TÉMOINS POSITIFS — archives fabriquées à B bits (mapping ⌊u·M⌋) :")
say("   B      atteignables / 2 000     attendu si source honnête")
for b in (32, 48, 53):
    ranks = [(int(rng.integers(0, 1 << 32)) << max(0, b - 32) |
              int(rng.integers(0, 1 << max(1, b - 32)))) % (1 << b) for _ in range(2000)]
    ranks = [(k * M) >> b for k in ranks]
    hit = sum(1 for r in ranks if reachable(r, b))
    say(f"   {b:<6} {hit:>6} / 2 000            {2000 * min(1.0, (1 << b) / M):>8.1f}")

say("\n   TÉMOIN NÉGATIF — archives équitables (rangs uniformes sur [0, M)) :")
say("   B      atteignables / 20 000    densité observée   théorie 2^B/M")
fair = [int(rng.integers(0, 1 << 62)) % M for _ in range(20_000)]
for b in (48, 53, 56, 60):
    hit = sum(1 for r in fair if reachable(r, b))
    theo = min(1.0, (1 << b) / M)
    say(f"   {b:<6} {hit:>6} / 20 000          {hit / 20000:.6f}         {theo:.6f}")


# --------------------------------------------------------------------------
# 2. L'archive réelle
# --------------------------------------------------------------------------

rule("2. L'ARCHIVE RÉELLE — 70 560 tirages")

arch = lab.load()
t = time.time()
ranks = [rank_of_draw([int(n) + 1 for n in np.flatnonzero(row)]) for row in arch.mask]
T = len(ranks)
say(f"   {T} rangs en {time.time() - t:.0f}s")

rmax = max(ranks)
say(f"\n   MAPPING « s mod M » — le rang maximal borne la source par le bas :")
say(f"     rang maximal observé : {rmax:,}  =  2^{math.log2(rmax):.4f}")
for b in (32, 48, 53, 56, 60, 61):
    say(f"     source {b} bits : {'EXCLUE' if rmax >= (1 << b) else 'compatible'}"
        f"   (2^{b} = {1 << b:,})")

say(f"\n   MAPPING « ⌊u·M⌋ » — atteignabilité des {T:,} rangs :")
say("   B      atteignables    attendu sous source honnête    écart")
t = time.time()
prof = profile(ranks)
for b in WIDTHS:
    hit = prof[b]
    p = min(1.0, (1 << b) / M)
    exp = T * p
    if p >= 1.0:
        say(f"   {b:<6} {hit:>10,}    {exp:>12,.1f}                 (tout est atteignable)")
        continue
    sd = math.sqrt(T * p * (1 - p))
    z = (hit - exp) / sd if sd > 0 else float("nan")
    verdict = "  <-- SOURCE ÉTROITE" if z > 6 else ""
    say(f"   {b:<6} {hit:>10,}    {exp:>12,.1f}    {z:+8.2f} σ{verdict}")
say(f"   ({time.time() - t:.0f}s)")


# --------------------------------------------------------------------------
# 3. Ce que cela borne
# --------------------------------------------------------------------------

rule("3. CE QUE CELA ÉTABLIT")

narrow = [b for b in WIDTHS if (1 << b) < M and prof[b] > T * min(1.0, (1 << b) / M)
          + 6 * math.sqrt(T * min(1.0, (1 << b) / M) * (1 - min(1.0, (1 << b) / M)))]
if narrow:
    b = min(narrow)
    say(f"   Source ÉTROITE détectée à {b} bits : l'espace d'états s'effondre")
    say(f"   de 2^61,62 à 2^{b}. La prédiction exacte redevient une question de")
    say(f"   force brute — {1 << b:,} candidats.")
else:
    say(f"""   Aucune granularité détectée. Le rang du tirage se comporte comme
   s'il consommait ses {math.log2(M):.2f} bits pleins :

     * le mapping « s mod M » exclut toute source de moins de 61 bits — le
       rang maximal observé vaut 2^{math.log2(rmax):.4f} ;
     * le mapping « ⌊u·M⌋ » exclut un double 53 bits de façon écrasante :
       on observe {prof[53]:,} rangs atteignables pour {T * (1 << 53) / M:,.0f}
       attendus sous une source honnête.

   Ce test ne suppose RIEN sur la récurrence du générateur — ni LCG, ni
   xorshift, ni rien. Il ne mesure que la LARGEUR de la source. C'est donc
   un complément exact de l'attaque algébrique de h4, qui suppose une
   récurrence mais pas une largeur.

   Ce qu'il ne peut pas voir, dit franchement : si le tirage n'est pas
   produit en dérangeant un entier — rejet, Fisher-Yates, tirage physique —
   le rang n'est pas une image de la source et sa granularité ne veut rien
   dire. C'est la même limite que h4, et c'est l'ordre de sortie des boules
   qui la lèverait.""")

rule(f"total {time.time() - T0:.0f}s")
