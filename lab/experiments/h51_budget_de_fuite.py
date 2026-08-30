"""h51 — le budget de fuite, et le calendrier de collecte qu'il impose.

Ce que le §68 laisse ouvert
============================
Le theoreme de la fuite modulaire ferme les familles F2-lineaires d'etat
<= 128 bits, POUR TOUTE GRAINE. Ses limites sont nommees et toutes de la meme
forme : il faudrait PLUS de tirages ordonnes consecutifs.

  - sorties additives (xorshift128+, xoroshiro128+) : lineaires sur le seul
    bit 0, donc 20 equations par tirage au lieu de 80 ;
  - MT19937 : lineaire, mais 19 937 bits d'etat.

« Plus de tirages » n'est pas une limite theorique, c'est une COMMANDE. Ce
fichier la chiffre, famille par famille, et en fait un calendrier.

Et il decouvre en chemin que l'echantillonneur decide de tout
==============================================================
Le §68 a etabli la fuite pour l'echantillonnage par REJET MODULO 80 : chaque
numero publie out mod 16, soit 4 bits, car v2(80) = 4.

Un Fisher-Yates ne tire pas modulo 80 mais modulo 80-i au pas i. La fuite par
pas vaut alors v2(80-i), et ces valuations sont pour la plupart NULLES : 79,
77, 75... sont impairs et ne publient rien du tout.

Le budget par tirage n'est donc pas une propriete du jeu mais de
l'IMPLEMENTATION, et l'ecart entre deux implementations legitimes se chiffre.

Il ne teste pas l'archive : il compte et il planifie. Registre : inchange.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(n):
    """Valuation 2-adique : le nombre de bits de poids faible qu'un modulo n
    publie exactement."""
    k = 0
    while n % 2 == 0:
        n //= 2
        k += 1
    return k


# ==========================================================================
rule("1. LE BUDGET DE FUITE, ÉCHANTILLONNEUR PAR ÉCHANTILLONNEUR")
# ==========================================================================

say("""   Un modulo par n publie exactement v2(n) bits de poids faible du mot :
   out mod n connu entraine out connu modulo 2^v2(n). C'est le theoreme du
   §68, ecrit pour un n quelconque.
""")

rejet = DRAWN * v2(POOL)
fy = sum(v2(POOL - i) for i in range(DRAWN))

say(f"   REJET MODULO {POOL} — chaque numero passe par le meme modulo {POOL}.")
say(f"     v2({POOL}) = {v2(POOL)}  ->  {v2(POOL)} bits par numero x {DRAWN} = {rejet} bits par tirage\n")

say(f"   FISHER-YATES — le pas i tire modulo {POOL}-i. Les valuations :")
line = []
for i in range(DRAWN):
    n = POOL - i
    line.append(f"{n}:{v2(n)}")
say("     " + "  ".join(line[:10]))
say("     " + "  ".join(line[10:]))
say(f"     somme = {fy} bits par tirage\n")

say(f"""   L'ECART. {rejet} bits contre {fy} : le rejet modulo {POOL} fuit {rejet/fy:.1f} fois plus
   qu'un Fisher-Yates, sur exactement le meme jeu et les memes 20 numeros.
   La difference tient entierement a ce que {POOL} = 16 x 5 est divisible par 16
   alors que 79, 77, 75, 73, 71, 69, 67, 65, 63 et 61 sont impairs et ne
   publient RIEN.

   Un seul pas de Fisher-Yates rapporte plus que tous les autres : le
   dix-septieme, qui tire modulo 64 = 2^6 et publie six bits d'un coup — la
   meme borne dont le §34 signalait qu'elle est traitee a part par
   `nextInt`. La ou java.util.Random change de chemin, la fuite est maximale.""")

MULT = 0
say(f"""
   MULTIPLY-SHIFT ((out * n) >> 32) — {MULT} bit lineaire. Ce n'est pas une
   fuite modulaire mais un encadrement : le numero dit dans quel intervalle
   de longueur 2^32/n tombe le mot. C'est un probleme de RESEAU, pas
   d'algebre lineaire sur F2, et il sort du cadre de ce fichier.""")


# ==========================================================================
rule("2. COMBIEN DE TIRAGES ORDONNÉS CONSÉCUTIFS, FAMILLE PAR FAMILLE")
# ==========================================================================

# (nom, bits d'etat, bits lineaires par mot de sortie, note)
FAMS = [
    ("xorshift32", 32, 4, "F2-lineaire"),
    ("xorshift64", 64, 4, "F2-lineaire"),
    ("xorshift96 / taus88", 96, 4, "F2-lineaire"),
    ("xorshift128", 128, 4, "F2-lineaire"),
    ("xoshiro256 (etat seul)", 256, 4, "F2-lineaire si sortie non brouillee"),
    ("xorshift128+", 128, 1, "sortie ADDITIVE : seul le bit 0 est lineaire"),
    ("xoroshiro128+", 128, 1, "sortie ADDITIVE : seul le bit 0 est lineaire"),
    ("MT19937", 19937, 4, "lineaire, mais l'etat est enorme"),
]

say(f"   {'famille':<26} {'etat':>7} {'bits/mot':>9} {'bits/tirage':>12} "
    f"{'tirages requis':>15}")
sched = []
for nom, bits, bpw, note in FAMS:
    per = DRAWN * bpw
    need = -(-bits // per)
    sched.append((nom, bits, need, note))
    say(f"   {nom:<26} {bits:>7,} {bpw:>9} {per:>12} {need:>15}")

say(f"""
   Le dossier possede CINQ tirages ordonnes, dont UNE seule paire
   consecutive. La colonne de droite dit donc exactement ce qui manque.""")


# ==========================================================================
rule("3. LE CALENDRIER DE COLLECTE")
# ==========================================================================

say("""   L'app collecte l'ordre de sortie a chaque tirage depuis le §38 (elle le
   calculait deja et le jetait). Un tirage toutes les cinq minutes, 204 par
   session. Ce que chaque palier ferme :
""")
say(f"   {'tirages ordonnés':>18}  {'durée de collecte':>18}   ce qui devient testable")
paliers = [(1, "xorshift32, xorshift64"),
           (2, "xorshift96, xorshift128, taus88 — le §68 s'arrête ici"),
           (4, "xoshiro256 (si la sortie n'est pas brouillée)"),
           (7, "xorshift128+ et xoroshiro128+ — les familles ADDITIVES"),
           (13, "toute famille additive jusqu'à 256 bits"),
           (250, "MT19937 — la dernière famille linéaire courante")]
for n, quoi in paliers:
    mins = n * 5
    d = f"{mins} min" if mins < 120 else f"{mins/60:.1f} h"
    say(f"   {n:>18}  {d:>18}   {quoi}")

say(f"""
   LA LECTURE QUI COMPTE. MT19937 — la famille la plus repandue du logiciel
   ordinaire, celle de `random` en Python et de `mt_rand` en PHP — demande
   250 tirages ordonnes CONSECUTIFS, soit {250*5/60:.1f} heures de collecte
   ininterrompue. Ce n'est pas hors de portee : c'est une session et demie.

   Et une session dure 204 tirages, donc 250 consecutifs traversent
   NECESSAIREMENT une coupure nocturne. Si le systeme se re-amorce a
   l'ouverture (le regime C du §65), la chaine casse et il faut 250
   consecutifs DANS une session — impossible, puisqu'une session n'en compte
   que 204.

   D'ou une conclusion qu'aucune collecte ne changera :""")

say(f"""
     MT19937 n'est attaquable par cette voie QUE si le generateur tourne en
     continu a travers les coupures. S'il se re-amorce chaque matin, la
     fenetre maximale est de 204 tirages, soit {204*DRAWN*4:,} bits — contre
     {19937:,} necessaires. Il manque un facteur {19937/(204*DRAWN*4):.1f}.

   Le §65 a mesure que le systeme SE COUPE 345 fois dans l'archive. La
   question « continu ou re-amorce » n'est donc pas academique : elle decide
   si la plus repandue des familles est atteignable ou non.""")


# ==========================================================================
rule("4. CE QUE CELA AJOUTE, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   AJOUTE.
   1. Le budget de fuite est une propriete de l'ECHANTILLONNEUR, pas du jeu :
      {rejet} bits par tirage pour un rejet modulo {POOL}, {fy} pour un Fisher-Yates,
      un rapport de {rejet/fy:.1f}. Le §68 avait etabli la fuite, pas son budget.
   2. Le pas modulo 64 du Fisher-Yates publie six bits a lui seul, plus que
      les dix-neuf autres reunis moins un.
   3. Chaque limite du §68 devient un NOMBRE DE TIRAGES A COLLECTER, donc une
      duree. La plus lointaine, MT19937, vaut 20,8 heures — et se heurte a la
      coupure de session, ce qui la rend conditionnelle a une question deja
      posee au §65.

   NE FAIT PAS.
   1. Rien ici ne touche l'archive : c'est un calcul de budget, pas un test.
   2. Le multiply-shift ne fuit aucun bit lineaire ; il demande une attaque
      par reseau, non traitee.
   3. Les generateurs a sortie brouillee non lineairement (PCG, xoshiro** et
      ++, splitmix64) et tout CSPRNG restent hors d'atteinte quel que soit le
      nombre de tirages collectes. Aucun calendrier ne les concerne.

   Registre : inchange. h51 ne teste pas l'archive — il compte.

   ({time.time() - T0:.2f} s)""")
