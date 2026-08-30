"""h8 — deux tirages ordonnés, et le test qui les relie.

Ce que le second tirage ajoute
-------------------------------
h7 traitait chaque tirage isolément : la chaîne 2-adique était testée à
l'intérieur d'un tirage. Deux tirages permettent de la tester ENTRE eux —
et c'est beaucoup plus fort, parce qu'un générateur ne se réinitialise pas
entre deux tirages.

Les deux tirages disponibles sont 1381023 et 1381026 : **non consécutifs,
trois tirages d'écart**. Ce n'est pas un obstacle si l'échantillonneur
consomme un nombre FIXE de sorties par tirage — un mélange de Fisher-Yates
en consomme exactement 20 (une par numéro, sans rejet). L'état avance alors
d'un nombre connu de pas : 3 × d, où d est le nombre de sorties par tirage.
On ne connaît pas d (le bonus, le boost ou un autre jeu peuvent en consommer
aussi), donc on le balaie — c'est une inconnue de plus, pas un mur.

Sous « LCG mod 2^64 + Fisher-Yates », la chaîne des 6 bits de poids faible
est entièrement déterminée par (A, C, s₀) mod 64, soit 2^17 = 131 072
triplets. Chaque tirage impose 22 bits de contrainte 2-adique, donc deux
tirages en imposent **44** : sous H0 il survit 2^17 / 2^44 triplets, c'est-à-
dire zéro avec une marge de dix ordres de grandeur. Sous l'hypothèse, le
vrai triplet survit forcément.

Autrement dit : le test ne peut se tromper que dans un sens, et ce sens est
celui du silence.

Ce que ce test NE couvre pas, dit d'emblée : un échantillonneur multiply-shift
(⌊s·m / 2⁶⁴⌋) filtre les bits de poids FORT et laisse le levier 2-adique
sans prise ; un générateur non congruentiel n'a pas de chaîne 2-adique ; un
tirage physique n'a pas d'état. Ces classes demandent une réduction de
réseau, pas plus de tirages.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
M64 = (1 << 64) - 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------

def fy_indices(order):
    """Reconstruit les indices d'un Fisher-Yates partiel à partir de l'ordre."""
    arr = list(range(1, POOL + 1))
    out = []
    for i, n in enumerate(order):
        j = arr.index(n, i)
        out.append(j - i)
        arr[i], arr[j] = arr[j], arr[i]
    return out


def constraints_2adic(order):
    """(position dans le tirage, résidu, module) pour chaque borne paire."""
    out = []
    for i, p in enumerate(fy_indices(order)):
        m = POOL - i
        v = (m & -m).bit_length() - 1        # valuation 2-adique de 80−i
        if v > 0:
            out.append((i, p % (1 << v), 1 << v))
    return out


def joint_survivors(draws, steps_per_draw, k=6):
    """Triplets (A, C, s₀) mod 2^k compatibles avec TOUS les tirages.

    `draws` : liste de (décalage en tirages depuis le premier, ordre).
    L'état au début du tirage de décalage g est s₀ avancé de g·steps_per_draw.
    """
    m = 1 << k
    plan = [(g * steps_per_draw, constraints_2adic(o)) for g, o in draws]
    horizon = max(base + DRAWN for base, _ in plan)
    surv = []
    for a in range(1, m, 2):
        for c in range(m):
            for s0 in range(m):
                # Orbite complète des bits bas, une fois par (a, c, s0).
                orbit, s = [], s0
                for _ in range(horizon):
                    orbit.append(s)
                    s = (a * s + c) % m
                ok = True
                for base, cons in plan:
                    for (i, res, mod) in cons:
                        if orbit[base + i] % mod != res:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    surv.append((a, c, s0))
    return surv


def lcg_fy_stream(a, c, s, n_draws):
    """n_draws tirages consécutifs par « LCG mod 2^64 + Fisher-Yates »."""
    out = []
    for _ in range(n_draws):
        arr = list(range(1, POOL + 1))
        order = []
        for i in range(DRAWN):
            s = (a * s + c) & M64
            j = i + s % (POOL - i)
            arr[i], arr[j] = arr[j], arr[i]
            order.append(arr[i])
        out.append(order)
    return out


# --------------------------------------------------------------------------
# 1. Les données
# --------------------------------------------------------------------------

rule("1. LES DEUX TIRAGES ORDONNÉS")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]), [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
rows.sort()

for did, order in rows:
    assert len(set(order)) == DRAWN and all(1 <= n <= POOL for n in order)
    say(f"   {did} : {order}")
base_id = rows[0][0]
gaps = [(did - base_id, order) for did, order in rows]
say(f"\n   écarts en tirages depuis {base_id} : {[g for g, _ in gaps]}")
say(f"   contraintes 2-adiques par tirage : "
    f"{[len(constraints_2adic(o)) for _, o in gaps]}")
bits = sum(sum(math.log2(m) for _, _, m in constraints_2adic(o)) for _, o in gaps)
say(f"   bits de contrainte au total : {bits:.0f}  contre 2^17 = 131 072 triplets")
say(f"   survivants attendus sous H0 : 2^17 / 2^{bits:.0f} = {2 ** 17 / 2 ** bits:.2e}")


# --------------------------------------------------------------------------
# 2. Témoins
# --------------------------------------------------------------------------

rule("2. TÉMOINS — le test joint sépare-t-il vraiment ?")

say("   TÉMOIN POSITIF — deux tirages d'un vrai « LCG + Fisher-Yates »,")
say("   séparés de 3 tirages, exactement comme les données réelles :")
for name, a, c in (("PCG/Numerical Recipes", 6364136223846793005, 1442695040888963407),
                   ("multiplicatif impair", 2862933555777941757, 3037000493)):
    stream = lcg_fy_stream(a, c, 0x0123456789ABCDEF, 4)
    pair = [(0, stream[0]), (3, stream[3])]
    t = time.time()
    surv = joint_survivors(pair, steps_per_draw=DRAWN)
    say(f"     {name:<24} survivants : {len(surv):>6}"
        f"   ({time.time() - t:.0f}s)")

say("\n   TÉMOIN NÉGATIF — 20 paires d'ordres uniformes :")
rng = np.random.default_rng(2026)
zeros = 0
t = time.time()
for _ in range(20):
    pair = [(g, [int(x) for x in rng.permutation(POOL)[:DRAWN] + 1]) for g in (0, 3)]
    if len(joint_survivors(pair, steps_per_draw=DRAWN)) == 0:
        zeros += 1
say(f"     zéro survivant dans {zeros}/20 cas   ({time.time() - t:.0f}s)")


# --------------------------------------------------------------------------
# 3. Le verdict, en balayant le nombre de sorties par tirage
# --------------------------------------------------------------------------

rule("3. LE VERDICT — balayage du nombre de sorties consommées par tirage")
say("   d = 20 si seul le tirage consomme le générateur ; d = 21 si le bonus")
say("   en consomme une de plus, et ainsi de suite. On balaie plutôt que de")
say("   supposer.")
say("\n   d      survivants")
found = []
t = time.time()
for d in range(20, 41):
    n = len(joint_survivors(gaps, steps_per_draw=d))
    if n:
        found.append((d, n))
    say(f"   {d:<6} {n:>6}{'   <-- SIGNATURE' if n else ''}")
say(f"   ({time.time() - t:.0f}s)")

rule("4. CE QUE CELA ÉTABLIT")
if found:
    say(f"   SIGNATURE TROUVÉE : {found}")
    say("   L'hypothèse « LCG mod 2^64 + Fisher-Yates » survit sur les 6 bits")
    say("   bas. Étape suivante : remonter les bits par élévation de Hensel,")
    say("   puis prédire le tirage suivant.")
else:
    say("""   Aucun triplet ne survit, pour aucun nombre de sorties par tirage de
   20 à 40. L'hypothèse « LCG modulo une puissance de deux + Fisher-Yates »
   est écartée par les deux tirages CONJOINTEMENT — un test que ni l'archive
   triée ni un tirage isolé ne permettaient.

   Ce que cela ne dit pas : rien sur un échantillonneur multiply-shift (les
   bits de poids fort filtrent, le levier 2-adique n'a pas de prise), rien
   sur un générateur non congruentiel, rien sur un tirage physique. Ces
   classes-là demandent une réduction de réseau — et donc des tirages
   ordonnés CONSÉCUTIFS, où la chaîne d'état est la plus contrainte.""")

rule(f"total {time.time() - T0:.0f}s")
