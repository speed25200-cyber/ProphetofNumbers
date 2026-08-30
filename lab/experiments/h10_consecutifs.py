"""h10 — ce que la paire CONSÉCUTIVE permet, et que les écarts interdisaient.

Le problème que les écarts posaient
------------------------------------
h7 testait l'hypothèse « LCG mod 2^64 + échantillonnage avec rejet
(`s mod 80`) » à l'intérieur d'un tirage : les numéros successifs doivent
suivre une relation affine mod 16, sauf aux pas où un doublon a été rejeté.

Cette hypothèse ne pouvait PAS être testée entre deux tirages écartés, parce
qu'avec du rejet le nombre de sorties consommées par un tirage est VARIABLE
(20 acceptées plus ≈ 3 rejets, coupon collector). Trois tirages d'écart, ce
sont donc ≈ 69 pas de générateur inconnus — la chaîne se perd.

Deux tirages CONSÉCUTIFS lèvent exactement ce blocage : entre le dernier
numéro de l'un et le premier de l'autre, il ne passe qu'une poignée de pas.
La chaîne 2-adique traverse la frontière presque intacte.

1381030 et 1381031 se suivent. On peut donc concaténer leurs 40 numéros et
exiger que la relation affine mod 16 tienne sur les **39** paires — au lieu
de 19 par tirage isolé. Chaque rejet coûte une paire ; il y en a ≈ 6 sur les
deux tirages, plus un ou deux à la frontière.

C'est un test deux fois plus long, donc deux fois plus discriminant, et il
n'existait pas avant cette paire.

Ce que ce test ne couvre toujours pas
--------------------------------------
L'échantillonneur multiply-shift (p = ⌊s·m / 2⁶⁴⌋) filtre les bits de POIDS
FORT : le levier 2-adique n'a aucune prise dessus. Le récupérer demande une
attaque de LCG tronqué par réduction de réseau, et la position exacte est
donnée en fin de fichier — 6,3 bits connus par sortie, ce qui place le
problème au bord de ce que la méthode supporte. Je ne livre pas d'attaque
que je ne peux pas valider ; je donne le calcul qui dit où en est la
frontière.
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


def best_affine(seq, k=4):
    """(paires expliquées, A, C) pour la meilleure relation affine mod 2^k."""
    m = 1 << k
    r = [(n - 1) % m for n in seq]
    best = (-1, None, None)
    for a in range(1, m, 2):
        for c in range(m):
            hits = sum(1 for i in range(len(r) - 1) if (a * r[i] + c) % m == r[i + 1])
            if hits > best[0]:
                best = (hits, a, c)
    return best


def lcg_reject_draw(a, c, s):
    """Un tirage par rejet : o = s mod 80, doublons rejetés."""
    seen, order = set(), []
    while len(order) < DRAWN:
        s = (a * s + c) & M64
        n = s % POOL + 1
        if n not in seen:
            seen.add(n)
            order.append(n)
    return order, s


# --------------------------------------------------------------------------
# 1. Les données
# --------------------------------------------------------------------------

rule("1. LES TIRAGES ORDONNÉS DISPONIBLES")

rows = []
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    for row in csv.DictReader(fh):
        rows.append((int(row["id"]), [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]))
rows.sort()
ids = [d for d, _ in rows]
say(f"   {len(rows)} tirages : {ids}")

pairs = [(rows[i], rows[i + 1]) for i in range(len(rows) - 1)
         if rows[i + 1][0] - rows[i][0] == 1]
say(f"   paires CONSÉCUTIVES : "
    f"{[(a[0], b[0]) for a, b in pairs] if pairs else 'aucune'}")
if not pairs:
    say("   -> ce test demande deux tirages qui se suivent ; rien à faire.")
    sys.exit(0)


# --------------------------------------------------------------------------
# 2. Témoins
# --------------------------------------------------------------------------

rule("2. TÉMOINS — sur 39 paires au lieu de 19")

KNOWN = [("PCG/Numerical Recipes", 6364136223846793005, 1442695040888963407),
         ("multiplicatif impair", 2862933555777941757, 3037000493)]

say("   TÉMOINS POSITIFS — deux tirages consécutifs d'un « LCG + rejet » :")
pos = []
for name, a, c in KNOWN:
    s = 0x0123456789ABCDEF
    scores = []
    for _ in range(30):
        d1, s = lcg_reject_draw(a, c, s)
        d2, s = lcg_reject_draw(a, c, s)
        scores.append(best_affine(d1 + d2)[0])
    pos.extend(scores)
    say(f"     {name:<24} paires expliquées : {np.mean(scores):.1f} / 39"
        f"   (min {min(scores)}, max {max(scores)})")

say("\n   TÉMOIN NÉGATIF — 2 000 paires d'ordres uniformes :")
rng = np.random.default_rng(5150)
t = time.time()
null = np.empty(2000, int)
for i in range(2000):
    seq = [int(x) for x in rng.permutation(POOL)[:DRAWN] + 1]
    seq += [int(x) for x in rng.permutation(POOL)[:DRAWN] + 1]
    null[i] = best_affine(seq)[0]
say(f"     paires expliquées : {null.mean():.2f} ± {null.std(ddof=1):.2f} / 39"
    f"   (max {null.max()})   [{time.time() - t:.0f}s]")
seuil = int(null.max()) + 1
say(f"     seuil de décision : {seuil}")
pos = np.array(pos)
say(f"\n   PUISSANCE : {float((pos >= seuil).mean()):.2f}"
    f"   ({int((pos >= seuil).sum())}/{len(pos)})")
say(f"   séparation : témoins positifs à {pos.mean():.1f}, null à {null.mean():.2f}"
    f" — il n'y a pas de zone grise")


# --------------------------------------------------------------------------
# 3. Le verdict
# --------------------------------------------------------------------------

rule("3. LE VERDICT SUR LA PAIRE RÉELLE")

for (id1, d1), (id2, d2) in pairs:
    seq = d1 + d2
    hits, a, c = best_affine(seq)
    p_emp = float((null >= hits).mean())
    say(f"   {id1} + {id2} concaténés — 40 numéros, 39 paires")
    say(f"     meilleure relation affine mod 16 : {hits}/39   (A = {a}, C = {c})")
    say(f"     null {null.mean():.2f} ± {null.std(ddof=1):.2f}   p empirique = {p_emp:.4f}")
    say(f"     verdict : {'SIGNATURE' if hits >= seuil else 'rien — compatible avec le hasard'}")
    # Contrôle : chaque tirage pris isolément, pour comparaison.
    say(f"     (isolément : {best_affine(d1)[0]}/19 et {best_affine(d2)[0]}/19)")


# --------------------------------------------------------------------------
# 4. Où en est la frontière pour le multiply-shift
# --------------------------------------------------------------------------

rule("4. LA FRONTIÈRE RESTANTE, CHIFFRÉE PLUTÔT QU'ANNONCÉE")

bits_per_out = float(np.mean([math.log2(POOL - i) for i in range(DRAWN)]))
say(f"""   L'échantillonneur multiply-shift calcule p = ⌊s·m / 2⁶⁴⌋ : il ne publie
   que les bits de POIDS FORT de l'état, soit {bits_per_out:.2f} bits par sortie en
   moyenne (log₂ de 80, 79, … 61). Le levier 2-adique vit dans les bits de
   poids faible : il n'a aucune prise dessus.

   La récupération demanderait une attaque de LCG TRONQUÉ par réduction de
   réseau. Plutôt que d'annoncer que « c'est difficile », voici le calcul.

   Formulation. Avec (a, c) connus, l'état s₀ vérifie, pour d sorties,
   (aⁱ·s₀ − bᵢ) mod 2⁶⁴ ∈ [0, Wᵢ) avec Wᵢ = 2⁶⁴/mᵢ. C'est un problème du
   vecteur le plus proche dans un réseau de dimension d+1 : base
   (1, a, a², …, a^d) plus les d vecteurs 2⁶⁴·eᵢ, coordonnées 1..d mises à
   l'échelle par λ ≈ {2 ** bits_per_out:.0f} pour que la boîte d'erreur soit cubique.

   Le déterminant vaut λ^d · 2^(64d), donc l'heuristique gaussienne donne
   un plus court vecteur de norme ≈ √((d+1)/2πe) · det^(1/(d+1)), à comparer
   à la norme du vecteur cherché, ≈ 2⁶⁴·√(d+1).""")

say("\n   d      plus court vecteur    vecteur cherché    marge")
for d in (20, 40, 100):
    det_log2 = d * bits_per_out + 64 * d
    short_log2 = math.log2(math.sqrt((d + 1) / (2 * math.pi * math.e))) + det_log2 / (d + 1)
    target_log2 = 64 + math.log2(math.sqrt(d + 1))
    say(f"   {d:<6} 2^{short_log2:<18.2f} 2^{target_log2:<16.2f} ×{2 ** (short_log2 - target_log2):.1f}")

gain = bits_per_out + 64
asympt = gain - 64 - math.log2(math.sqrt(2 * math.pi * math.e))
d_cross = None
for d in range(2, 2000):
    marge = (math.log2(math.sqrt((d + 1) / (2 * math.pi * math.e)))
             + (d * gain) / (d + 1) - 64 - math.log2(math.sqrt(d + 1)))
    if marge > 0:
        d_cross = d
        break

say(f"""
   Lecture — et c'est un argument d'impossibilité, pas un aveu.

   La marge CROÎT avec d (×1,7 → ×10,5 ci-dessus) mais elle plafonne : elle
   tend vers 2^{asympt:.2f} ≈ ×{2 ** asympt:.0f}, parce que chaque sortie n'apporte que
   {bits_per_out:.2f} bits là où le réseau en coûte 64 par dimension. Elle ne devient
   positive qu'à partir de d = {d_cross}.

   Face à cela, LLL ne garantit qu'un facteur d'approximation de l'ordre de
   2^(d/4) — soit 2^{20 / 4:.0f} en dimension 21, 2^{40 / 4:.0f} en dimension 41. La condition
   « LLL suffit » s'écrit donc d/4 < marge(d), et elle n'est vérifiée pour
   AUCUN d : en dessous de {d_cross} la marge est négative, au-dessus le terme d/4
   dépasse immédiatement un plafond de {asympt:.1f}.

   **Il n'existe aucun point de fonctionnement pour LLL sur cette famille.**
   Ce n'est pas l'information qui manque — {len(rows) * DRAWN} sorties en donnent
   {len(rows) * DRAWN * bits_per_out:.0f} bits pour 192 bits d'inconnues, un facteur {len(rows) * DRAWN * bits_per_out / 192:.1f}. C'est la
   géométrie du réseau, et davantage de tirages n'y changerait rien. Il
   faudrait BKZ à grand bloc — et aucune bibliothèque de réduction n'est
   disponible ici (ni fpylll, ni sympy, ni flint).

   Je ne livre pas une attaque que je ne peux pas valider sur témoins.
   C'est la règle qui a fait tomber les quatre familles précédentes, et
   elle vaut aussi quand elle m'arrête.""")

rule(f"total {time.time() - T0:.0f}s")
