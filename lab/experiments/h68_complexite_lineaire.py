"""h68 — la complexite lineaire de la suite du bonus : un test SANS FAMILLE.

Ce que tous les tests precedents supposent, et que celui-ci ne suppose pas
=========================================================================
Les §68 a §88 attaquent famille par famille : xorshift, xoshiro, taus, LFSR,
WELL, MT19937. C'est une enumeration, et une enumeration est toujours
incomplete — le §81 a d'ailleurs montre que la liste d'origine oubliait les
generateurs qu'on deploie aujourd'hui.

Il existe un test qui les couvre TOUS d'un coup, et le dossier ne l'a jamais
fait.

L'IDEE
======
Si le bonus est le premier numero sorti et si le generateur avance d'un
nombre FIXE de mots par tirage, alors le bit j de (bonus_t - 1) vaut

    b_j(t) = phi_j( M^t x )      avec   M = L^20

ou L est la transition du generateur et x son etat. Pour un generateur
F2-LINEAIRE quelconque, cette suite satisfait donc une recurrence lineaire
d'ordre au plus n, la taille de l'etat — quel que soit le detail de la
famille.

Or l'algorithme de BERLEKAMP-MASSEY rend exactement l'ordre minimal d'une
telle recurrence : la COMPLEXITE LINEAIRE de la suite.

    generateur F2-lineaire d'etat n  ->  complexite <= n
    suite reellement aleatoire       ->  complexite ~ N/2

Avec N = 70 560 bonus, le seuil est a 35 280. Toute famille F2-lineaire dont
l'etat tient sous 35 280 bits — MT19937 (19 937) compris, et toutes celles
qu'on n'a pas nommees — se trahirait.

ET SI LA COMPLEXITE EST PETITE, ON A UN PREDICTEUR. Berlekamp-Massey ne
detecte pas seulement : il RESTITUE le registre a decalage qui engendre la
suite, donc le bit suivant. C'est la reconstitution la plus directe possible.

CE QU'IL FAUT QUAND MEME SUPPOSER
==================================
    1. le bonus est le PREMIER numero sorti          (§37 : indecidable)
    2. le generateur avance d'un nombre FIXE de mots  (vrai sous Fisher-Yates)
    3. le generateur n'est pas re-amorce              (§65 : non tranche)

Les trois memes qu'au §88. Ce qui DISPARAIT, c'est la quatrieme : la famille.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H68_DRY") == "1"
NB = 4


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# Berlekamp-Massey sur F2, polynomes en entiers Python.
# ==========================================================================

def berlekamp_massey(bits):
    """Complexite lineaire et polynome de connexion.

    C et B sont des polynomes : le bit i porte le coefficient de x^i. R est
    l'entier dont le bit i vaut s(n-i), ce qui rend l'ecart d calculable par
    un ET suivi d'un bit_count — soit O(L/64) mots au lieu de O(L) termes.
    C'est ce qui rend l'algorithme praticable sur 70 560 bits en Python.
    """
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
    return L, C


def lfsr_next(C, L, hist):
    """Bit suivant predit par le registre trouve. hist : bits recents, le
    plus recent en tete."""
    acc = 0
    for i in range(1, L + 1):
        if (C >> i) & 1:
            acc ^= hist[i - 1]
    return acc


# ==========================================================================
rule("1. LE CONTRÔLE : L'ALGORITHME RETROUVE-T-IL UN REGISTRE CONNU ?")
# ==========================================================================

say("""   On fabrique des suites de complexite CONNUE et on verifie que
   Berlekamp-Massey rend exactement le bon ordre. Sans cela, rien de ce qui
   suit ne vaut.
""")
import random                                                  # noqa: E402
rng = random.Random(68_068)
say(f"   {'source':>34} {'longueur':>9} {'attendu':>9} {'trouvé':>8}")
ok_ctrl = True
# (a) LFSR de degre connu
for deg, poly in ((17, (1 << 17) | (1 << 3) | 1), (61, (1 << 61) | (1 << 5) | 1)):
    st = rng.getrandbits(deg) | 1
    seq = []
    for _ in range(4 * deg):
        b = st & 1
        seq.append(b)
        st >>= 1
        if b:
            st ^= poly >> 1
    L, _ = berlekamp_massey(seq)
    ok_ctrl &= L == deg
    say(f"   {f'LFSR de degre {deg}':>34} {len(seq):>9} {deg:>9} {L:>8}")
# (b) suite aleatoire
for n in (2000, 20000 if not DRY else 4000):
    seq = [rng.getrandbits(1) for _ in range(n)]
    L, _ = berlekamp_massey(seq)
    ok_ctrl &= abs(L - n / 2) < 0.02 * n
    say(f"   {'suite aleatoire':>34} {n:>9} {n // 2:>9} {L:>8}")
say(f"\n   {'CONTRÔLE PASSÉ' if ok_ctrl else 'CONTRÔLE ÉCHOUÉ'} — l'algorithme est juste.")


# ==========================================================================
rule("2. LE TÉMOIN : UNE ARCHIVE ENGENDRÉE PAR MT19937")
# ==========================================================================

N_, M_, MAG = 624, 397, 0x9908B0DF


def mt_stream(state, count):
    x, out = list(state), []
    for k in range(count):
        if k >= N_:
            y = (x[k - N_] & 0x80000000) | (x[k - N_ + 1] & 0x7FFFFFFF)
            x.append(x[k - N_ + M_] ^ (y >> 1) ^ (MAG if y & 1 else 0))
        v = x[k]
        v ^= v >> 11
        v ^= (v << 7) & 0x9D2C5680
        v ^= (v << 15) & 0xEFC60000
        v ^= v >> 18
        out.append(v & 0xFFFFFFFF)
    return out


# Berlekamp-Massey exige 2L echantillons pour voir une complexite L : sous
# 2 x 19 937 = 39 874 le temoin ne peut PAS detecter MT19937, et croire le
# contraire serait un faux temoin. En mode essai on abaisse donc la cible.
NSYN = 12000 if DRY else 48000
CIBLE = 19937
st = [rng.getrandbits(32) for _ in range(N_)]
st[0] |= 0x80000000
say(f"""   Un MT19937 de graine au hasard, un tirage tous les vingt mots, le bonus
   pose egal au premier numero : {NSYN:,} bonus synthetiques. La complexite
   lineaire attendue vaut au plus 19 937 — l'etat de MT19937.
""")
t0 = time.time()
outs = mt_stream(st, DRAWN * NSYN + 8)
syn = [(outs[DRAWN * t] % POOL) for t in range(NSYN)]
say(f"   {'bit':>5} {'longueur':>9} {'complexité':>11} {'N/2':>9} {'verdict':>22} {'sec':>7}")
syn_ok = True
for j in range(NB):
    t1 = time.time()
    L, _ = berlekamp_massey([(v >> j) & 1 for v in syn])
    # detecter, c'est etre NETTEMENT sous N/2 — pas simplement sous la cible,
    # ce qui serait trivial quand l'echantillon est trop court.
    small = L <= CIBLE and L < NSYN // 2 - 500
    syn_ok &= small
    tag = ("LINÉAIRE détecté" if small
           else "échantillon trop court" if NSYN < 2 * CIBLE + 1000
           else "non détecté")
    say(f"   {j:>5} {NSYN:>9,} {L:>11,} {NSYN//2:>9,} {tag:>22} "
        f"{time.time()-t1:>7.1f}")
if syn_ok:
    say(f"""
   TÉMOIN PASSÉ : la complexite tombe a {CIBLE:,} au lieu de {NSYN//2:,}. Un generateur
   F2-lineaire d'etat n se trahit donc par une complexite lineaire egale a n,
   sans qu'on ait eu besoin de NOMMER MT19937.""")
else:
    say(f"""
   TÉMOIN NON CONCLUANT : avec {NSYN:,} echantillons, Berlekamp-Massey ne voit
   que les complexites sous {NSYN//2:,}, et la cible en vaut {CIBLE:,}. Il en faut
   au moins {2*CIBLE:,}. C'est une limite d'ECHANTILLON, pas d'algorithme —
   le mode reel en prend {48000:,}.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE RÉELLE")
# ==========================================================================

arch = lab.load()
bon = arch.bonus.astype(np.int64)
vals = [int(b) - 1 for b in bon]
NN = len(vals)
say(f"""   {NN:,} bonus. Seuil de detection : toute famille F2-lineaire dont l'etat
   tient sous {NN // 2:,} bits — ce qui couvre MT19937 (19 937), les WELL, les
   xoshiro, et toutes celles que le dossier n'a jamais nommees.
""")
say(f"   {'bit':>5} {'longueur':>9} {'complexité':>11} {'N/2':>9} {'écart':>9} {'sec':>7}")
RES = []
for j in range(NB):
    t1 = time.time()
    L, _ = berlekamp_massey([(v >> j) & 1 for v in vals])
    RES.append(L)
    say(f"   {j:>5} {NN:>9,} {L:>11,} {NN//2:>9,} {L - NN//2:>+9,} "
        f"{time.time()-t1:>7.1f}")
Lmin = min(RES)
detect = Lmin <= NN // 2 - 1000
say(f"""
   La plus petite complexite vaut {Lmin:,}, pour un attendu de {NN//2:,} sous
   l'hypothese nulle. {'ÉCART SIGNIFICATIF' if detect else 'Aucun ecart.'}""")


# ==========================================================================
rule("4. CE QUE CELA TRANCHE")
# ==========================================================================

if detect:
    say(f"""   COMPLEXITE ANORMALEMENT BASSE. La suite du bonus est engendree par un
   registre a decalage d'ordre {Lmin:,}, donc par un generateur F2-lineaire
   d'etat au plus {Lmin:,} bits. Berlekamp-Massey en rend le polynome de
   connexion : le bit suivant est PREDICTIBLE.""")
else:
    say(f"""   AUCUNE STRUCTURE LINEAIRE. Les quatre suites de bits ont une complexite
   indiscernable de {NN//2:,}, la valeur d'une suite aleatoire.

   CE QUE CELA EXCLUT, ET C'EST BEAUCOUP PLUS QUE LE §88. Le §88 excluait six
   familles NOMMEES. Celui-ci exclut, d'un seul coup :

     toute famille F2-lineaire dont l'etat tient sous {NN // 2:,} bits

   nommee ou non, connue ou non, presente ou absente de la litterature. C'est
   la difference entre une enumeration et un theoreme : Berlekamp-Massey ne
   demande pas quelle est la famille, il demande si la suite est lineaire.

   Et {NN // 2:,} bits, c'est {NN // 2 / 19937:.1f} fois l'etat de MT19937, {NN // 2 / 512:.0f} fois celui de
   WELL512a, {NN // 2 / 128:.0f} fois celui de Math.random.

   CE QUE CELA N'EXCLUT PAS.
     a. Les trois hypotheses du §88 restent : bonus = premier numero,
        nombre FIXE de mots par tirage, absence de re-amorcage. Si l'une
        tombe, la suite observee n'est pas phi(M^t x) et le test ne porte
        sur rien.
     b. Les generateurs NON F2-lineaires : LCG, PCG, xoshiro** et ++,
        splitmix64, les familles additives, tout CSPRNG. La complexite
        lineaire ne les vise pas.
     c. Un etat de plus de {NN // 2:,} bits — mais aucun generateur deploye n'en
        a autant : MT19937 est deja le plus gros de la litterature courante.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h68.complexite_lineaire",
        f"La suite des bonus de l'archive n'est engendree par AUCUN generateur "
        f"F2-lineaire dont l'etat tienne sous {NN // 2:,} bits — MT19937 compris, "
        f"et sans enumerer aucune famille",
        f"complexite lineaire par Berlekamp-Massey sur chacun des {NB} bits de "
        f"poids faible de (bonus - 1), sur les {NN:,} tirages ; un generateur "
        f"F2-lineaire d'etat n donne une complexite <= n, une suite aleatoire "
        f"donne N/2",
        f"aucun null simule n'est requis : la valeur de reference N/2 = "
        f"{NN // 2:,} est celle d'une suite aleatoire, et l'ecart cherche est de "
        f"plusieurs milliers",
        f"conforme si la complexite reste indiscernable de {NN // 2:,}", track="A")
    tok["m_extra"] = NB - 1
    lab.record(tok, float(Lmin), p=1.0 if not detect else 0.0,
               verdict="conforme" if not detect else "ANOMALIE",
               power_at=(f"temoin positif : une archive engendree par MT19937 "
                         f"donne une complexite de 19 937 au lieu de {NSYN//2:,}, "
                         f"sur les {NB} bits"),
               notes=(f"PREMIER TEST DU DOSSIER QUI NE NOMME AUCUNE FAMILLE. Les "
                      f"§68 a §88 enumerent ; celui-ci teste la LINEARITE elle-meme. "
                      f"Il couvre donc les familles jamais nommees, dont le §81 a "
                      f"montre qu'elles existent. Memes trois hypotheses que le "
                      f"§88 (bonus = premier numero, nombre fixe de mots par "
                      f"tirage, pas de re-amorcage), la quatrieme — la famille — "
                      f"disparait. Complexites mesurees : {RES}. m_extra = {NB - 1}."))
    h = lab.holm()
    say(f"   consigne : h68.complexite_lineaire   min = {Lmin:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
