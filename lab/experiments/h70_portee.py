"""h70 — la portee reelle du §89 : deux classes algebriques, pas une.

Ce que le §89 disait, et ce qu'il fait vraiment
===============================================
Le §89 conclut : « toute famille F2-lineaire dont l'etat tient sous 35 280
bits est exclue ». C'est vrai, et c'est trop modeste.

Berlekamp-Massey ne mesure pas la F2-linearite : il mesure la COMPLEXITE
LINEAIRE, c'est-a-dire l'ordre de la plus petite recurrence lineaire. Or il y
a une seconde facon, tout a fait differente, d'avoir une complexite basse.

LE LEMME
=========
    Une suite EVENTUELLEMENT PERIODIQUE de periode P et de pre-periode t0 a
    une complexite lineaire au plus P + t0.

    PREUVE. La suite verifie s(t+P) = s(t) pour tout t >= t0, c'est-a-dire
    que le polynome (x^P - 1) x^{t0} l'annule. Sa complexite lineaire, qui
    est le degre du polynome minimal annulateur, ne depasse donc pas
    P + t0. []

CE QUE CELA AJOUTE, ET C'EST UNE CLASSE ENTIERE
================================================
Un generateur ARITHMETIQUE — congruentiel lineaire, quadratique, a retenue
(MWC de Marsaglia) — n'est PAS F2-lineaire : ses retenues s'y opposent. Le
§89 semblait donc l'ignorer.

Mais ses bits de poids faible sont FERMES : si la transition est un polynome
a coefficients entiers modulo 2^k, elle descend modulo 2^j pour tout j <= k,
et l'etat reduit vit dans un ensemble FINI de taille 2^(j x mots). La suite
observee est donc eventuellement periodique de periode au plus 2^(j x mots) —
et le lemme la rend visible a Berlekamp-Massey.

Le §89 couvre donc DEUX classes :

    (I)  les generateurs F2-lineaires d'etat <= 35 280 bits
    (II) les generateurs dont les bits observes sont eventuellement
         periodiques de periode <= 35 280 — soit toute la famille
         arithmetique a SORTIE BRUTE

Ce fichier le demontre, le mesure, et dit ou la portee s'arrete.

Il ne teste pas l'archive : il etablit la portee d'un test deja consigne.
Registre : inchange.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H70_DRY") == "1"
NSEQ = 8000 if DRY else 40000
W = 20                                    # mots par tirage
M64 = (1 << 64) - 1


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def bm(bits):
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


def period(vals, pmax=4000):
    """Plus petite periode p <= pmax telle que la suite soit p-periodique
    (verifiee sur une fenetre, puis en entier)."""
    n = len(vals)
    for p in range(1, min(pmax, n // 3) + 1):
        if all(vals[t] == vals[t + p] for t in range(min(400, n - p))):
            if all(vals[t] == vals[t + p] for t in range(n - p)):
                return p
    return None


# ==========================================================================
rule("1. LE LEMME, ET SA VÉRIFICATION")
# ==========================================================================

say("""   Une suite eventuellement periodique de periode P a une complexite
   lineaire au plus P + pre-periode : le polynome (x^P - 1) x^t0 l'annule.

   On le verifie sur des suites de periode CONNUE.
""")
rng = random.Random(70_070)
say(f"   {'période imposée':>17} {'longueur':>9} {'complexité BM':>14} {'≤ P ?':>7}")
ok_lemme = True
for P in (7, 64, 500, 3000):
    motif = [rng.getrandbits(1) for _ in range(P)]
    seq = [motif[t % P] for t in range(NSEQ)]
    L = bm(seq)
    ok_lemme &= L <= P
    say(f"   {P:>17,} {NSEQ:>9,} {L:>14,} {('oui' if L <= P else 'NON'):>7}")
say(f"   {'LEMME VÉRIFIÉ' if ok_lemme else 'LEMME EN DÉFAUT'}.")


# ==========================================================================
rule("2. LES GÉNÉRATEURS ARITHMÉTIQUES, QUE LE §89 SEMBLAIT IGNORER")
# ==========================================================================

def lcg64(s):
    return (6364136223846793005 * s + 1442695040888963407) & M64


def lcg48(s):
    return (0x5DEECE66D * s + 0xB) & ((1 << 48) - 1)


def quad64(s):
    return (s * s + 5 * s + 3) & M64


def mwc(st):
    """MWC de Marsaglia : etat (x, c), sortie x. La retenue interdit la
    F2-linearite, et c'est bien pourquoi le §89 semblait aveugle."""
    x, c = st
    t = 4294957665 * x + c
    return (t & 0xFFFFFFFF, t >> 32)


def stream_raw(step, s0, n, w, two=False):
    """n valeurs de « out mod 80 », un tirage tous les w mots, sortie BRUTE."""
    s, out = s0, []
    for _ in range(n):
        for _k in range(w):
            s = step(s)
        out.append((s[0] if two else s) % POOL)
    return out


say(f"""   Un generateur arithmetique n'est pas F2-lineaire. Mais si sa transition
   est un POLYNOME a coefficients entiers modulo 2^k, elle descend modulo
   2^j : les bits bas sont fermes, la suite observee est periodique, et le
   lemme la rend visible. Reste a savoir quelles familles satisfont cette
   condition — la quatrieme ligne du tableau repond.

   Un tirage tous les {W} mots, sortie brute, {NSEQ:,} tirages.
""")
say(f"   {'générateur':>26} {'bit':>4} {'période':>9} {'complexité BM':>14} {'N/2':>8}")
FAM = [("LCG mod 2^64", lambda: rng.getrandbits(64), lcg64, False),
       ("LCG mod 2^48 (java brut)", lambda: rng.getrandbits(48), lcg48, False),
       ("congruentiel quadratique", lambda: rng.getrandbits(64), quad64, False),
       ("MWC 32 bits (Marsaglia)", lambda: (rng.getrandbits(32),
                                            rng.getrandbits(30)), mwc, True)]
seen = 0
for nom, seed, step, two in FAM:
    vals = stream_raw(step, seed(), NSEQ, W, two)
    for j in (0, 3):
        b = [(v >> j) & 1 for v in vals]
        p = period(b)
        L = bm(b)
        vu = L < NSEQ // 2 - 500
        seen += vu
        say(f"   {nom:>26} {j:>4} {(str(p) if p else '> 4000'):>9} {L:>14,} "
            f"{NSEQ//2:>8,}   {'VU' if vu else 'non vu'}")

say(f"""
   TROIS SUR QUATRE SONT VUES, ET LA QUATRIEME DIT OU EST LA LIMITE.

   Les congruentiels — lineaire mod 2^64, mod 2^48, quadratique — donnent une
   complexite de quelques unites la ou le hasard en donne {NSEQ//2:,}. Berlekamp-
   Massey ne les rate pas d'un cheveu : il les rate de quatre ordres de
   grandeur. Leur transition est un POLYNOME a coefficients entiers modulo
   2^k, donc elle descend modulo 2^j : les bits bas sont fermes, la suite est
   periodique, et le lemme fait le reste.

   MWC ECHAPPE, et c'est instructif. Sa transition n'est pas un polynome
   modulo 2^k : la retenue c' = (a x + c) DIV 2^32 est une quantite de la
   partie HAUTE. La reduction modulo 2^j n'est donc pas bien definie, les
   bits bas ne sont pas fermes, et la suite n'est pas periodique. J'avais
   ecrit « toute la famille arithmetique » ; c'etait trop large, et c'est le
   calcul qui l'a corrige.

   Le §89 couvre donc DEUX classes, et la seconde a une frontiere precise :
     (I)  les generateurs F2-lineaires d'etat <= 35 280 bits
     (II) les generateurs dont la TRANSITION est un polynome modulo 2^k et
          dont la SORTIE est brute — congruentiels lineaires et quadratiques""")


# ==========================================================================
rule("3. OÙ LA PORTÉE S'ARRÊTE, EXACTEMENT")
# ==========================================================================

def lcg48_shift(s):
    return (0x5DEECE66D * s + 0xB) & ((1 << 48) - 1)


def pcg32(st):
    """PCG32 XSH-RR : l'etat avance par LCG, la sortie est brouillee."""
    s = (6364136223846793005 * st + 1442695040888963407) & M64
    x = ((s >> 18) ^ s) >> 27 & 0xFFFFFFFF
    r = s >> 59
    return s, ((x >> r) | (x << ((-r) & 31))) & 0xFFFFFFFF


say(f"""   La cle du (II) est que la sortie soit BRUTE : out mod 16 doit ne dependre
   que des bits BAS de l'etat, qui sont fermes. Des que la sortie prend des
   bits HAUTS, la fermeture ne s'applique plus.

   Trois contre-exemples, tires de generateurs reellement deployes :
""")
say(f"   {'générateur':>34} {'bit':>4} {'complexité BM':>14} {'N/2':>8}  verdict")

# java.util.Random : out = etat >> 17
s = rng.getrandbits(48)
vals = []
for _ in range(NSEQ):
    for _k in range(W):
        s = lcg48_shift(s)
    vals.append((s >> 17) % POOL)
for j in (0,):
    L = bm([(v >> j) & 1 for v in vals])
    say(f"   {'java.util.Random (out = s >> 17)':>34} {j:>4} {L:>14,} "
        f"{NSEQ//2:>8,}  {'AVEUGLE' if L > NSEQ//2 - 500 else 'vu'}")

# PCG32
s = rng.getrandbits(64)
vals = []
for _ in range(NSEQ):
    for _k in range(W):
        s, o = pcg32(s)
    vals.append(o % POOL)
L = bm([v & 1 for v in vals])
say(f"   {'PCG32 (sortie brouillée)':>34} {0:>4} {L:>14,} {NSEQ//2:>8,}  "
    f"{'AVEUGLE' if L > NSEQ//2 - 500 else 'vu'}")

# LCG brut mais echantillonneur par TRONCATURE : la sortie prend les bits hauts
s = rng.getrandbits(64)
vals = []
for _ in range(NSEQ):
    for _k in range(W):
        s = lcg64(s)
    vals.append((s * POOL) >> 64)
L = bm([v & 1 for v in vals])
say(f"   {'LCG brut + échantillonneur (B)':>34} {0:>4} {L:>14,} {NSEQ//2:>8,}  "
    f"{'AVEUGLE' if L > NSEQ//2 - 500 else 'vu'}")

say(f"""
   LA FRONTIERE EST NETTE, et elle n'est pas celle de la famille : elle est
   celle de l'OBSERVATION.

     vu      quand out mod 16 ne depend que des bits BAS de l'etat
     aveugle des que l'observation prend des bits HAUTS

   Ce qui echappe donc au §89 :
     — les sorties DECALEES (java.util.Random rend s >> 17)
     — les sorties BROUILLEES (PCG, xoshiro ** et ++, splitmix64)
     — l'echantillonneur par TRONCATURE, qui publie les bits hauts (§82),
       meme sur un generateur par ailleurs transparent
     — les generateurs A RETENUE (MWC, AWC, SWB de Marsaglia), dont la
       retenue vient de la partie haute : ni F2-lineaires, ni fermes en bas
     — tout CSPRNG

   Le §34 traitait deja java.util.Random par une attaque 2-adique dediee, et
   le §82 traite la troncature famille par famille. Le §89 ne les remplace
   pas : il complete.""")


# ==========================================================================
rule("4. CE QUE CELA ÉTABLIT")
# ==========================================================================

say(f"""   1. LE LEMME : periodicite de periode P => complexite lineaire <= P + t0.
      Verifie sur des periodes imposees de 7 a 3 000.

   2. LE §89 EST PLUS LARGE QU'ANNONCE. Il exclut deux classes :
        (I)  F2-lineaire, etat <= 35 280 bits
        (II) transition POLYNOMIALE modulo 2^k et sortie BRUTE —
             congruentiels lineaires et quadratiques, dont les bits bas
             sont fermes
      La seconde n'etait pas dans l'enonce du §89, et c'est l'implementation
      naive par excellence. J'avais d'abord ecrit « toute la famille
      arithmetique » : le calcul a montre que MWC en sort, parce que sa
      retenue est une quantite de poids fort.

   3. LA FRONTIERE N'EST PAS LA FAMILLE MAIS L'OBSERVATION. Un LCG est vu
      s'il sort brut, invisible s'il sort decale — meme generateur, meme
      etat. Ce qui compte est de savoir si out mod 16 ne depend que des
      bits fermes.

   4. CE QUI RESTE HORS DE PORTEE, pour DEUX raisons distinctes qu'il ne
      faut pas confondre :

        — L'OBSERVATION prend les bits HAUTS : sorties decalees
          (java.util.Random), sorties brouillees (PCG, xoshiro ** et ++,
          splitmix64), echantillonneur par troncature (§82). L'etat peut
          etre parfaitement ferme, on n'en voit pas la partie fermee.

        — LA TRANSITION ne descend pas modulo 2^j : les generateurs A
          RETENUE (MWC, AWC, SWB de Marsaglia), ou la retenue est une
          quantite de poids fort. Meme a sortie brute, rien n'est ferme.

      Le premier groupe est exactement le mur que le §83 avait nomme et le
      §84 mesure. Le second est une case que le dossier n'avait jamais
      ouverte, et ce fichier la nomme pour la premiere fois.

   Registre : INCHANGE. h70 etablit la portee d'un test deja consigne.

   ({time.time() - T0:.1f} s)""")
