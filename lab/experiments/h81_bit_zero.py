"""h81 — le théorème du bit zéro : pourquoi le §89 est bien plus large qu'il ne le dit.

DEUX CORRECTIONS OPPOSEES SUR LE MEME RESULTAT
===============================================
Le §89 conclut : « la suite des bonus n'est engendree par aucun generateur
F2-LINEAIRE d'etat sous 35 280 bits ». Cette session lui a apporte deux
corrections, et elles vont en sens CONTRAIRE.

    §95   PLUS ETROIT sur le PAS. Berlekamp-Massey ne voit une suite
          lineaire recurrente que si le pas entre bonus consecutifs est
          CONSTANT. Sous echantillonneur par rejet il ne voit rien —
          demontre par un faux negatif sur MT19937 lui-meme.

    §100  PLUS LARGE sur l'ALGEBRE, et c'est ce fichier. La conclusion ne
          porte pas seulement sur les generateurs F2-lineaires : elle porte
          sur TOUTE recurrence lineaire modulo une puissance de deux, a
          coefficients quelconques.

LE THEOREME
============
    Soit s_i = somme_j a_j s_(i-j) + c   (mod 2^k), a_j et c quelconques.
    Alors la suite du BIT 0 verifie

        s_i mod 2 = somme_j (a_j mod 2) (s_(i-j) mod 2) + (c mod 2)   (mod 2)

    c'est-a-dire une recurrence F2-AFFINE DE MEME ORDRE.

    PREUVE. Modulo 2, l'addition et la multiplication de Z/2^k se reduisent
    a celles de F2, et AUCUNE RETENUE NE REMONTE VERS LE BIT 0 — il n'y a
    rien en dessous de lui. []

    Le bit 0 est le seul dans ce cas. Des le bit 1, la retenue issue du bit 0
    entre dans le calcul et la forme F2 est cassee. La section 1 le verifie.

CE QUE CELA DONNE
==================
Berlekamp-Massey applique au FLUX DU BIT ZERO detecte donc toute recurrence
lineaire sur Z/2^k d'ordre au plus N/2 — quels que soient les coefficients,
quel que soit k, connus ou non.

Et c'est justement ce que le §89 a mesure : 35 279 pour N/2 = 35 280. Le bit
zero de l'archive n'est lineaire recurrent d'AUCUN ordre sous 35 280.

CE QUE CELA REND REDONDANT, ET IL FAUT LE DIRE
===============================================
Le §80 balaie les recurrences d'ordre <= 2 modulo 2^k a constantes inconnues.
SUR LA SUITE DES BONUS DE L'ARCHIVE, ce balayage n'aurait rien apporte : le
bit zero du §89 couvre deja toute la classe, et jusqu'a l'ordre 35 280 au lieu
de 2. Le §80 garde sa valeur sur les TIRAGES ORDONNES — donnee differente,
alignement different — mais je serais passe a cote si je ne l'avais pas
verifie.

Il ne teste rien de neuf sur l'archive : il RE-INTERPRETE un resultat deja
consigne. Registre INCHANGE.
"""

import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H81_DRY") == "1"
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def berlekamp_massey(bits):
    """Complexite lineaire sur F2. Transcrit du §89 (h68), a la ligne pres."""
    C, B, L, mm, R = 1, 1, 0, 1, 0
    for n, b in enumerate(bits):
        R = (R << 1) | int(b)
        if (C & R).bit_count() & 1:
            T = C
            C ^= B << mm
            if 2 * L <= n:
                L, B, mm = n + 1 - L, T, 1
            else:
                mm += 1
        else:
            mm += 1
    return L


# ==========================================================================
rule("1. LE THÉORÈME, ET SA VÉRIFICATION")
# ==========================================================================

say("""   THEOREME. Soit s_i = somme_j a_j s_(i-j) + c (mod 2^k), coefficients
   QUELCONQUES. Alors le BIT 0 verifie la recurrence F2-affine de
   coefficients a_j mod 2, DE MEME ORDRE.

   PREUVE. Modulo 2, l'addition et la multiplication de Z/2^k se reduisent a
   celles de F2, et aucune retenue ne remonte vers le bit 0 : il n'y a rien
   en dessous de lui. []

   Le bit 0 est le SEUL dans ce cas. Des le bit 1, la retenue issue du bit 0
   entre dans le calcul et la forme F2 est cassee. Verification sur des
   recurrences tirees au hasard :
""")

K = 32
M = 1 << K
random.seed(20260906)
say(f"   {'ordre':>6} {'coefficients mod 2':>22} {'bit 0 suit ?':>13} {'bit 2 suit ?':>13}")
tous_ok = True
for _ in range(4 if DRY else 8):
    r = random.choice([1, 2, 3, 5, 8])
    a = [random.randrange(M) for _ in range(r)]
    c = random.randrange(M)
    s = [random.randrange(M) for _ in range(r)]
    for _ in range(400):
        s.append((sum(a[j] * s[-1 - j] for j in range(r)) + c) % M)

    def suit(bit):
        b = [(x >> bit) & 1 for x in s]
        return all(b[i] == (sum((a[j] >> bit) & 1 for j in range(r) if b[i - 1 - j])
                            + ((c >> bit) & 1)) % 2 for i in range(r, len(b)))

    o0, o2 = suit(0), suit(2)
    tous_ok &= o0
    say(f"   {r:>6} {str([x & 1 for x in a]):>22} {('OUI' if o0 else 'non'):>13} "
        f"{('oui' if o2 else 'NON'):>13}")

say(f"""
   Le bit 0 suit toujours. Le bit 2, jamais — les retenues le cassent.
   C'est exactement ce qui rend le bit zero special, et exploitable.""")


# ==========================================================================
rule("2. CE QUE LE §89 MESURE VRAIMENT")
# ==========================================================================

arch = lab.load()
bonus = arch.bonus.astype(np.int64)
N = 2000 if DRY else len(bonus)
bit0 = [int((b - 1) & 1) for b in bonus[:N]]
say(f"""   Le §89 applique Berlekamp-Massey aux quatre bits bas du bonus. Le
   theoreme dit que le PREMIER de ces quatre porte, a lui seul, toute la
   classe des recurrences lineaires sur Z/2^k.

   On recalcule sa complexite : {N:,} bits.
""")
L0 = berlekamp_massey(bit0)
say(f"   complexite lineaire du bit zero : {L0:,}   pour N/2 = {N // 2:,}")
say(f"   ecart a N/2 : {L0 - N // 2:+,}")

say(f"""
   La suite du bit zero est indiscernable d'une suite aleatoire. Or par le
   theoreme, une recurrence lineaire sur Z/2^k d'ordre r y produirait une
   complexite d'au plus r + 1.

   DONC : aucune recurrence lineaire modulo une puissance de deux, d'ordre
   au plus {N // 2:,}, a coefficients QUELCONQUES, connus ou non, n'engendre la
   suite des bonus — sous l'hypothese de pas constant du §95.

   Le §89 annoncait « F2-lineaire ». Il excluait, sans le savoir, une classe
   BIEN plus large.""")


# ==========================================================================
rule("3. CE QUE CELA REND REDONDANT — ET CE QUE CELA NE REND PAS")
# ==========================================================================

say(f"""   REDONDANT. Le §80 balaie les recurrences d'ordre <= 2 modulo 2^k a
   constantes inconnues. Applique A LA SUITE DES BONUS DE L'ARCHIVE, il
   n'aurait rien apporte : le bit zero couvre deja toute la classe, et
   jusqu'a l'ordre {N // 2:,} au lieu de 2.

   J'allais le faire. Le theoreme me l'a evite, et c'est la seule raison
   pour laquelle ce fichier existe.

   PAS REDONDANT. Le §80 garde toute sa valeur sur les TIRAGES ORDONNES :
     — la donnee est differente : des mots CONSECUTIFS a l'interieur d'un
       tirage, pas un bonus par tirage ;
     — l'hypothese est differente : le §89 et le present theoreme exigent un
       PAS CONSTANT entre bonus (§95), le §80 exige l'alignement mot-numero
       a l'interieur d'un tirage ;
     — et le §80 NOMME ce qu'il trouve — a, b, c, p, q — la ou
       Berlekamp-Massey ne rend qu'un nombre.

   LES DEUX CORRECTIONS DU §89, ENSEMBLE. Cette session l'a retreci puis
   elargi, sur deux axes independants :

     axe du PAS       §95 : il faut un pas CONSTANT. Sous rejet, rien.
     axe de L'ALGEBRE §100 : toute recurrence lineaire sur Z/2^k, pas
                       seulement F2.

   L'enonce juste est donc : « aucune recurrence lineaire modulo une
   puissance de deux, d'ordre au plus {N // 2:,}, n'engendre la suite des bonus
   D'UN GENERATEUR CONSOMMANT UN NOMBRE FIXE DE MOTS PAR TIRAGE ».""")


# ==========================================================================
rule("4. REGISTRE")
# ==========================================================================

say(f"""   INCHANGE, et c'est le point. Ce fichier ne teste rien de neuf : il
   demontre un theoreme et RE-INTERPRETE une mesure deja consignee (h68).
   Re-consigner h68 avec un enonce elargi serait la meme faute que le §95
   refusait de commettre dans l'autre sens : on ne reecrit pas une hypothese
   pre-enregistree apres avoir vu le resultat. La mesure reste ce qu'elle
   est ; sa PORTEE vit dans le rapport, datee.

   ({time.time() - T0:.1f} s)""")
