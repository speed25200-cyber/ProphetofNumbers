"""h20 — Fisher-Yates à indices MODULAIRES, la case restée vide.

La grille des échantillonneurs, et le trou dedans
--------------------------------------------------
Pour tirer 20 numéros sur 80 dans un ordre, une implémentation fait l'une de
ces choses, et le dossier les a couvertes ainsi :

    rejet sur « s mod 80 »                       h7, h10   testé
    rejet sur multiply-shift                     h11       testé (constantes connues)
    Fisher-Yates à indice multiply-shift         h11       testé (constantes connues)
    dérangement d'une sortie large (unrank)      h12       testé (constantes inconnues)
    **Fisher-Yates à indice MODULAIRE**          —         JAMAIS TESTÉ

La dernière ligne est pourtant la plus courante de toutes : c'est ce qu'on
écrit quand on tape `arr[i + rand() % (80 - i)]`. Et elle est la PLUS
exposée du lot, pour une raison précise que ce fichier exploite.

Le levier, et pourquoi il est écrasant
---------------------------------------
À l'étape i, l'indice vaut p_i = s_i mod m_i avec m_i = 80 − i. Les modules
parcourent donc 80, 79, 78, …, 61 — et dix d'entre eux sont PAIRS. Or
p_i mod 2^v publie s_i mod 2^v dès que 2^v divise m_i :

    m = 80 → 2⁴     m = 72 → 2³     m = 64 → **2⁶**
    m = 76 → 2²     m = 68 → 2²
    m = 78, 74, 70, 66, 62 → 2¹

Un seul tirage publie donc 4+1+2+1+3+1+2+1+6+1 = 22 bits de poids faible de
l'état, répartis sur dix pas connus. Cinq tirages en publient 110.

Et 110 bits de contrainte pèsent contre 17 bits d'inconnues seulement, si
l'on travaille modulo 2⁶ : a impair (5 bits libres), c (6 bits), s₀ (6 bits).
Le rapport est de 6 contre 1. Sous l'hypothèse nulle, le nombre de triplets
survivants attendu est 2¹⁷ · 2⁻¹¹⁰ — c'est-à-dire zéro, et de très loin.

Autrement dit : si le tirage sort d'un Fisher-Yates à indices modulaires
piloté par un générateur congruentiel, ce test le voit. S'il ne voit rien,
la famille entière tombe — et cette fois sans avoir eu besoin de deviner la
moindre constante.

Ce que le test ne peut pas faire
---------------------------------
Il vit dans les bits de poids FAIBLE et ne remonte pas au-delà de 2⁶, faute
de module divisible par une puissance de deux plus grande. Il IDENTIFIE donc
la famille sans livrer l'état complet. Si des survivants apparaissaient, la
suite serait un relèvement contraint par les modules impairs — mais c'est un
problème qu'on ne pose que s'il se présente.
"""

import csv
import math
import os
import sys
import time
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
N64 = 1 << 64
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(x: int) -> int:
    return (x & -x).bit_length() - 1


# --------------------------------------------------------------------------
# Les deux variantes de Fisher-Yates partiel
# --------------------------------------------------------------------------

def fy_forward_indices(order):
    """p_i = j − i pour `arr[i], arr[j] = arr[j], arr[i]`, j = i + (s mod 80−i)."""
    arr = list(range(1, POOL + 1))
    out = []
    for i, n in enumerate(order):
        j = arr.index(n, i)
        out.append(j - i)
        arr[i], arr[j] = arr[j], arr[i]
    return out


def fy_forward_draw(a, c, s):
    arr = list(range(1, POOL + 1))
    order = []
    for i in range(DRAWN):
        s = (a * s + c) % N64
        j = i + s % (POOL - i)
        arr[i], arr[j] = arr[j], arr[i]
        order.append(arr[i])
    return order, s


MODULI = [POOL - i for i in range(DRAWN)]           # 80, 79, …, 61


# --------------------------------------------------------------------------
# Le test 2-adique
# --------------------------------------------------------------------------

def constraints(draws, steps_per_draw=DRAWN):
    """[(pas global, résidu, valuation)] : ce que les modules pairs publient."""
    out = []
    for offset, order in draws:
        p = fy_forward_indices(order)
        base = steps_per_draw * offset
        for i, pi in enumerate(p):
            v = v2(MODULI[i])
            if v > 0:
                # L'état au pas (base + i + 1) : le premier appel du tirage
                # consomme une sortie, d'où le +1.
                out.append((base + i + 1, pi % (1 << v), v))
    return out


def survivors(cons, K):
    """Triplets (a, c, s₀) mod 2^K compatibles avec toutes les contraintes."""
    mod = 1 << K
    keep = []
    for a in range(1, mod, 2):
        # Chaîne des états, précalculée : s_t = A_t·s₀ + C_t (mod 2^K).
        tmax = max(t for t, _, _ in cons)
        A = [1] * (tmax + 1)
        C = [0] * (tmax + 1)
        for t in range(1, tmax + 1):
            A[t] = A[t - 1] * a % mod
        for c in range(mod):
            for t in range(1, tmax + 1):
                C[t] = (C[t - 1] * a + c) % mod
            for s0 in range(mod):
                ok = True
                for t, r, v in cons:
                    if ((A[t] * s0 + C[t]) - r) % (1 << v):
                        ok = False
                        break
                if ok:
                    keep.append((a, c, s0))
    return keep


# --------------------------------------------------------------------------
# 1. Le compte d'information
# --------------------------------------------------------------------------

rule("1. LE COMPTE — combien de bits ce modèle publie-t-il ?")

per_draw = sum(v2(m) for m in MODULI)
say("   module   valuation 2-adique   bits publiés sur l'état")
for m in MODULI:
    if v2(m):
        say(f"   {m:<8} {v2(m):<20} {v2(m)}")
say(f"\n   par tirage : {per_draw} bits de poids faible, sur "
    f"{sum(1 for m in MODULI if v2(m))} pas connus")
for K in (4, 5, 6):
    unk = (K - 1) + K + K
    say(f"   modulo 2^{K} : {5 * min(per_draw, 5 * K):>3} bits de contrainte "
        f"(5 tirages) contre {unk} bits d'inconnues — survivants attendus "
        f"sous H0 : {2 ** unk * 2 ** -min(5 * per_draw, 999):.1e}")


# --------------------------------------------------------------------------
# 2. Témoins
# --------------------------------------------------------------------------

rule("2. TÉMOINS — le test récupère-t-il un générateur qu'il ignore ?")

OFFSETS = [0, 3, 5, 7, 8]                            # les écarts RÉELS
KNOWN = [("MMIX / PCG", 6364136223846793005, 1442695040888963407),
         ("L'Ecuyer 64", 2862933555777941757, 3037000493),
         ("Knuth 3935", 3935559000370003845, 2691343689449507681)]

say("   Tirages fabriqués en « LCG + Fisher-Yates à indices modulaires »,")
say("   aux écarts réels de l'archive.\n")
say("   générateur         K   survivants   (a, c, s₀) vrai retrouvé   temps")
ok_pos = 0
for name, a, c in KNOWN:
    seed = 0x0123456789ABCDEF
    draws, s = [], seed
    cur = 0
    for off in OFFSETS:
        while cur < off:
            for _ in range(DRAWN):
                s = (a * s + c) % N64
            cur += 1
        order, _ = fy_forward_draw(a, c, s)
        draws.append((off, order))
    cons = constraints(draws)
    for K in (6,):
        t = time.time()
        keep = survivors(cons, K)
        mod = 1 << K
        want = (a % mod, c % mod, seed % mod)
        hit = want in keep
        ok_pos += 1 if hit else 0
        say(f"   {name:<18} {K}   {len(keep):<12} {'OUI' if hit else 'NON':<25} "
            f"{time.time() - t:.1f}s")

say("\n   TÉMOIN NÉGATIF — ordres uniformes, aucun générateur derrière :")
import random
rnd = random.Random(2026)
faux = 0
for rep in range(4):
    draws = [(off, rnd.sample(range(1, POOL + 1), DRAWN)) for off in OFFSETS]
    keep = survivors(constraints(draws), 6)
    faux += 1 if keep else 0
    say(f"     réplicat {rep + 1} : {len(keep)} survivant(s)")
say(f"     réplicats avec au moins un survivant : {faux}/4")


# --------------------------------------------------------------------------
# 3. Les tirages réels
# --------------------------------------------------------------------------

rule("3. LES CINQ TIRAGES ORDONNÉS RÉELS")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]),
                     [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
rows.sort()
base_id = rows[0][0]
real = [(d - base_id, order) for d, order in rows]
say(f"   {len(real)} tirages, décalages {[o for o, _ in real]}")
cons = constraints(real)
say(f"   contraintes 2-adiques extraites : {len(cons)}, "
    f"soit {sum(v for _, _, v in cons)} bits")

for K in (4, 5, 6):
    t = time.time()
    keep = survivors(cons, K)
    say(f"   modulo 2^{K} : {len(keep)} triplet(s) survivant(s)   "
        f"({time.time() - t:.1f}s)")
    if K == 6:
        final = keep

rule("4. VERDICT")
if final:
    say(f"   {len(final)} triplet(s) (a, c, s₀) modulo 64 survivent aux "
        f"{sum(v for _, _, v in cons)} bits de contrainte.")
    for tri in final[:10]:
        say(f"     a ≡ {tri[0]}, c ≡ {tri[1]}, s₀ ≡ {tri[2]}  (mod 64)")
    say("""
   Ce n'est PAS encore une prédiction : le test vit dans les six bits de
   poids faible et n'identifie que la famille. Le relèvement vers l'état
   complet demanderait les modules impairs, et c'est un problème qu'on ne
   pose que si celui-ci a des survivants — ce qui est le cas ici.""")
else:
    say(f"""   Aucun survivant, à tous les modules testés.

   L'hypothèse « Fisher-Yates à indices modulaires piloté par un générateur
   congruentiel » est donc écartée sur les cinq tirages ordonnés, et elle
   l'est sans avoir eu à deviner la moindre constante : le test résout
   (a, c, s₀) au lieu de les énumérer.

   C'était la dernière case vide de la grille des échantillonneurs. Les cinq
   familles standard de production d'un tirage ordonné de 20 sur 80 sont
   maintenant couvertes, chacune avec ses témoins positifs et négatifs.

   Ce que cela laisse ouvert, et il faut le dire : un générateur dont l'état
   ne suit pas une récurrence affine — chiffrement par bloc, éponge,
   générateur matériel — ne laisse aucune prise à aucune de ces attaques.
   C'est le cas le plus probable pour un opérateur certifié, et aucune
   analyse de sorties publiques ne peut le trancher.""")

rule(f"total {time.time() - T0:.0f}s")
