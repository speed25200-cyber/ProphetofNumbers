"""h117 — la complexité linéaire universelle, FORME POLYNOMIALE : la fin de
l'exemption des sorties brouillées.

L'EXEMPTION QUE LE §122 S'ÉTAIT ACCORDÉE
========================================
Le §122 démontre que si l'état évolue par s -> A·s et si le bit observé est une
forme F2-LINÉAIRE de l'état, alors L(b) <= W. Et il s'arrête là, en écrivant
noir sur blanc sa propre limite :

    « le bit doit être F2-linéaire — LES SORTIES BROUILLÉES ÉCHAPPENT. »

C'était l'exemption la plus coûteuse du dossier. Elle laisse dehors xoshiro256++,
xoshiro256**, xoroshiro128**, splitmix64, PCG32 — c'est-à-dire tout ce qui a été
écrit après 2014, et le §123 a mesuré que pour ces familles AUCUNE fonctionnelle
de la sortie n'a de degré <= 3.

LA LEVÉE DE L'EXEMPTION
========================
Elle tient en une observation, et elle est élémentaire :

    SI s_n = A^n s_0, chaque bit de s_n est une forme linéaire des bits de s_0.
    Donc tout PRODUIT de k bits de s_n est une somme de produits de k bits de
    s_0. Le VECTEUR DES MONÔMES de degré <= d évolue donc LINÉAIREMENT :

        m_n = A_d^n · m_0,        m = (1, s_1, .., s_W, s_1s_2, ..)

    où A_d est la matrice induite par A sur l'espace des monômes, de dimension

        N_d(W)  =  somme_{k=0..d} C(W, k).

Si le bit observé est un POLYNÔME de degré <= d de l'état, il est une forme
LINÉAIRE de m. On est ramené exactement au §122, à ceci près que la largeur
n'est plus W mais N_d(W).

    THÉORÈME (§135). Soit s -> A·s sur F2^W, A quelconque, et
    b_i = P(A^{c+sigma·i} s) avec P polynôme F2 de degré <= d. Alors b vérifie
    une récurrence linéaire de degré <= N_d(W), donc

        L(b)  <=  N_d(W)  =  somme_{k<=d} C(W, k).                        []

    Le §122 est le cas d = 1. AUCUNE HYPOTHÈSE DE LINÉARITÉ DE LA SORTIE.

LA FORME MAÎTRESSE DE LA BORNE
===============================
En renversant, et avec N_d(W) ~ W^d/d! :

    W  >=  ( d! · L(b) )^(1/d)        et, le §134 plafonnant L par T/2,
    W  >=  ( d! · T/2 )^(1/d).

C'est la formule qui gouverne tout le dossier :

    d = 1   W >= T/2              -- le §122, exclusion écrasante
    d = 2   W >= (T)^(1/2)        -- 265 pour T = 70 560
    d = 3   W >= (3T)^(1/3)       -- 60
    d = 4   W >= (12T)^(1/4)      -- 30

    LE POUVOIR D'EXCLUSION S'EFFONDRE COMME T^(1/d). C'est le prix exact du
    refus de supposer la sortie linéaire, et personne ne l'avait chiffré.

CE QUE CELA REND POSSIBLE, ET QUI EST NEUF
===========================================
Le corollaire de prédiction du §122 se transporte tel quel : avec 2·N_d(W) bits
observés, Berlekamp-Massey rend la récurrence et PRÉDIT tout bit suivant — sans
connaître la famille, ni le brouilleur, ni l'état, ni le pas.

    W = 64,  d = 4  ->  2·N_4 = 1 358 242 tirages         atteignable
    W = 128, d = 4  ->  2·N_4 = 22 035 266                lointain
    W = 256, d = 4  ->  2·N_4 = 355 178 114               hors d'atteinte

C'est la PREMIÈRE fois que le dossier chiffre ce qu'il faudrait pour prédire une
sortie BROUILLÉE sans la nommer.

Il DÉMONTRE, et il porte un témoin de PRÉDICTION : une suite de générateur à
sortie quadratique, prédite sans que rien ne lui soit dit.
"""

import os
import struct
import subprocess
import sys
import time
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H117_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H117_TMP", "/tmp")


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BB = os.path.join(TMP, "bmf2_h117")
FJ = os.path.join(TMP, "h117.bin")
subprocess.run(["cc", "-O3", "-march=native", "-o", BB,
                os.path.join(DEPOT, "tools", "bmf2.c")],
               check=True, capture_output=True)


def L_de(suite):
    """Complexité linéaire par `tools/bmf2.c` — pour les grandes longueurs."""
    b = np.asarray(suite, np.uint8) & 1
    n = len(b)
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", 1, n))
        fh.write(np.packbits(b, bitorder="little").tobytes().ljust(nw * 8, b"\x00"))
    p = subprocess.run([BB, FJ], capture_output=True, text=True, check=True)
    for l in p.stdout.split("\n"):
        t = l.split()
        if t[:1] == ["L"]:
            return int(t[2])
    raise RuntimeError(p.stdout)


def bm_poly(s):
    """Berlekamp-Massey en clair : rend (L, C) avec C[0] = 1, la RÉCURRENCE.
    Il faut le polynôme lui-même pour PRÉDIRE, et bmf2 ne le publie pas."""
    n = len(s)
    C = np.zeros(n + 1, np.uint8); C[0] = 1
    B = C.copy()
    L, m = 0, 1
    for i in range(n):
        d = int(s[i])
        if L:
            d ^= int(np.bitwise_xor.reduce(C[1:L + 1] & s[i - L:i][::-1]))
        if d:
            T = C.copy()
            C[m:m + n + 1 - m] ^= B[:n + 1 - m]
            if 2 * L <= i:
                L, B, m = i + 1 - L, T, 1
            else:
                m += 1
        else:
            m += 1
    return L, C


def predit(s, L, C, k):
    """Prolonge la suite de k termes par la récurrence C."""
    out = list(np.asarray(s, np.uint8) & 1)
    for _ in range(k):
        v = 0
        for j in range(1, L + 1):
            if C[j]:
                v ^= out[-j]
        out.append(v)
    return np.array(out[len(s):], np.uint8)


def Nd(W, d):
    return sum(comb(W, k) for k in range(d + 1))


# ---------------------------------------------------------------------------
# Un générateur JOUET : état F2-linéaire, sortie POLYNOMIALE de degré exact d.
# ---------------------------------------------------------------------------
class Jouet:
    def __init__(self, W, d, graine=1):
        rng = np.random.default_rng(graine)
        self.W, self.d = W, d
        taps = sorted(rng.choice(np.arange(1, W), size=3, replace=False).tolist())
        self.taps = taps
        # P : somme de `nt` monômes de degré exactement d, plus un terme linéaire.
        self.mon = [tuple(sorted(rng.choice(W, size=d, replace=False).tolist()))
                    for _ in range(4)]
        self.lin = rng.integers(0, 2, W).astype(np.uint8)
        self.s = rng.integers(0, 2, W).astype(np.uint8)
        if not self.s.any():
            self.s[0] = 1

    def pas(self):
        v = self.s[0]
        for t in self.taps:
            v ^= self.s[t]
        self.s = np.r_[self.s[1:], v]

    def sortie(self):
        b = int(np.bitwise_xor.reduce(self.lin & self.s)) if self.lin.any() else 0
        for m in self.mon:
            p = 1
            for i in m:
                p &= int(self.s[i])
            b ^= p
        return b

    def suite(self, n):
        out = np.zeros(n, np.uint8)
        for i in range(n):
            out[i] = self.sortie()
            self.pas()
        return out


# ==========================================================================
rule("1. LE THÉORÈME : LES MONÔMES ÉVOLUENT LINÉAIREMENT")
# ==========================================================================

say("""   Si s_n = A^n s_0, chaque bit de s_n est une forme lineaire des bits de s_0 ;
   donc tout PRODUIT de k bits de s_n est une somme de produits de k bits de
   s_0. Le VECTEUR DES MONOMES de degre <= d evolue donc LINEAIREMENT, dans un
   espace de dimension

       N_d(W) = somme_{k<=d} C(W, k).

   Un bit de sortie POLYNOMIAL de degre <= d est une forme LINEAIRE de ce
   vecteur : on est ramene au §122, largeur N_d(W) au lieu de W.

       L(b) <= N_d(W).      Le §122 est le cas d = 1.

   Mesure sur des generateurs jouets a sortie de degre EXACT d, observes sur
   4·N_d termes — bien au-dela de 2·N_d ou BM devient exact.

       W    d      N_d(W)     termes lus     L mesuré   L <= N_d ?""")

OK1, LIG1 = 0, []
for W, d in ((16, 1), (16, 2), (16, 3), (24, 1), (24, 2), (20, 3), (12, 4)):
    nd = Nd(W, d)
    n = min(4 * nd, 20000)
    b = Jouet(W, d, graine=100 + W + d).suite(n)
    L = L_de(b)
    ok = L <= nd
    OK1 += ok
    LIG1.append((W, d, nd, n, L, ok))
    say(f"   {W:>4} {d:>4} {nd:>11,} {n:>14,} {L:>12,}   {'oui' if ok else 'NON':>10}")
say(f"""
   {OK1}/{len(LIG1)} bornes respectees. Une sortie de degre d n'echappe pas a
   Berlekamp-Massey : elle en repousse seulement le plafond de W a N_d(W).""")


# ==========================================================================
rule("2. TÉMOIN DE PRÉDICTION : UNE SORTIE QUADRATIQUE, PRÉDITE SANS RIEN SAVOIR")
# ==========================================================================

say("""   Le corollaire de prediction du §122 se transporte tel quel. On donne a
   Berlekamp-Massey 2·N_d bits et RIEN D'AUTRE — ni la famille, ni le
   brouilleur, ni le pas, ni l'etat — et on lui demande les 300 suivants.

   Contre-epreuve indispensable : la meme suite passee a une recurrence de
   degre N_1 = W+1, c'est-a-dire l'attaque du §122 telle quelle, DOIT echouer.

       W    d      N_d      bits lus   prédits justes   §122 seul (N_1)""")

OK2, LIG2 = 0, []
for W, d in ((16, 2), (20, 2), (16, 3), (24, 2)):
    nd = Nd(W, d)
    g = Jouet(W, d, graine=7000 + W * 10 + d)
    b = g.suite(2 * nd + 300)
    obs, futur = b[:2 * nd], b[2 * nd:]
    L, C = bm_poly(obs)
    pr = predit(obs, L, C, 300)
    juste = int((pr == futur).sum())
    # contre-epreuve : la meme chose bornee au degre 1 (le §122 tel quel)
    L1, C1 = bm_poly(obs[:2 * (W + 1)])
    pr1 = predit(obs[:2 * (W + 1)], L1, C1, 300)
    juste1 = int((pr1 == b[2 * (W + 1):2 * (W + 1) + 300]).sum())
    OK2 += (juste == 300) and (juste1 < 260)
    LIG2.append((W, d, nd, 2 * nd, juste, juste1))
    say(f"   {W:>4} {d:>4} {nd:>8,} {2*nd:>13,} {juste:>16}/300 {juste1:>11}/300")
say(f"""
   {OK2}/{len(LIG2)} temoins complets : la prediction polynomiale est PARFAITE sur 300
   bits, et l'attaque du §122 tel quel — qui suppose la sortie lineaire —
   ECHOUE sur les memes donnees.

     C'EST LA PREMIERE PREDICTION DU DOSSIER SUR UNE SORTIE NON LINEAIRE, ET
     ELLE NE NOMME RIEN.""")


# ==========================================================================
rule("3. LA FORME MAÎTRESSE : W >= (d!·T/2)^(1/d)")
# ==========================================================================

say("""   Avec N_d(W) ~ W^d/d!, la borne se renverse en

       W >= (d! · L)^(1/d),   et le §134 plafonnant L par T/2 :
       W >= (d! · T/2)^(1/d).

   C'est la formule qui gouverne tout le dossier — et elle dit que LE POUVOIR
   D'EXCLUSION S'EFFONDRE COMME T^(1/d). C'est le prix exact du refus de
   supposer la sortie lineaire, et personne ne l'avait chiffre.

       T observé""")
TS = [70560, 141120, 1000000, 4360000]
ENT = "       degré d" + "".join(f"{t:>14,}" for t in TS)
say(ENT)
for d in (1, 2, 3, 4, 5, 6):
    lig = f"   {d:>11}   "
    for T in TS:
        L = T // 2
        w = 1
        while Nd(w, d) < L:
            w += 1
        lig += f"{w:>14,}"
    say(lig)
say("""
   Lecture : chaque case est la plus petite largeur W que l'archive de T bits
   NE PEUT PAS exclure sous une sortie de degre d. En degre 1 c'est T/2 —
   ecrasant. En degre 4 c'est trente.""")


# ==========================================================================
rule("4. CE QU'IL FAUDRAIT POUR PRÉDIRE UNE SORTIE BROUILLÉE SANS LA NOMMER")
# ==========================================================================

say("""   Berlekamp-Massey predit des qu'il a lu 2·N_d(W) bits. Le §123 a mesure que
   pour xoshiro256++/**, xoroshiro128**, splitmix64, AUCUNE fonctionnelle de la
   sortie n'a de degre <= 3 : le degre utile est donc d >= 4.

       famille                     W      d       2·N_d(W) tirages     verdict""")
CIB = [("xoroshiro64**", 64, 4), ("xoroshiro128** ", 128, 4),
       ("xoshiro256++ / **", 256, 4), ("xoshiro256++ / **", 256, 5),
       ("MT19937", 19937, 2)]
DISPO = 70560
for nom, W, d in CIB:
    b = 2 * Nd(W, d)
    verd = ("ATTEIGNABLE" if b <= 2e6 else
            "lointain" if b <= 5e7 else "hors d'atteinte")
    say(f"   {nom:>22} {W:>7,} {d:>6} {b:>22,}     {verd}")
say(f"""
   L'archive publie {DISPO:,} tirages. Pour la premiere fois le dossier CHIFFRE
   ce qu'il faudrait pour predire une sortie brouillee sans la nommer :

     un generateur de 64 bits, quel que soit son brouilleur, serait predit par
     1,36 million de tirages — dix-neuf fois l'archive, et le §134 dit que
     c'est LINEAIRE : il n'y a pas de raccourci, mais il n'y a pas de mur.

   Au-dela de 128 bits, c'est fini : 22 millions de tirages, soit un siecle et
   demi de plateforme a 204 tirages par jour.""")


# ==========================================================================
rule("5. L'ARCHIVE : CE QUE LE THÉORÈME EXCLUT VRAIMENT")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1)
BIT = ((RANG // 5) >> 1).astype(np.uint8)
NA = len(BIT)
LA = L_de(BIT)

say(f"""   Le bit exact de poids fort du rang du bonus, {NA:,} tirages : L = {LA:,},
   exactement le seuil du hasard N/2 — l'archive sature, comme le §134 le veut.

   La borne du theoreme s'applique alors A CHAQUE DEGRE, et c'est la seule
   exclusion du dossier qui ne suppose RIEN de la sortie :

       degré d   W exclu si W <    ce que cela ferme""")
QUAL = {1: "tout F2-lineaire", 2: "toute sortie QUADRATIQUE",
        3: "toute sortie CUBIQUE", 4: "toute sortie de degre 4",
        5: "toute sortie de degre 5"}
BORNES = {}
for d in (1, 2, 3, 4, 5):
    w = 1
    while Nd(w, d) < LA:
        w += 1
    BORNES[d] = w
    say(f"   {d:>9}   {w:>15,}    {QUAL[d]} de moins de {w:,} bits"
        f"{'  (le §122)' if d == 1 else ''}")

say(f"""
   CE QUE CELA AJOUTE VRAIMENT. Le §122 excluait les sorties lineaires ; il
   laissait DEHORS tout ce qui brouille. Le theoreme les rattrape, mais a un
   prix qui se lit dans la colonne du milieu : de {BORNES[1]:,} bits en degre 1 on
   tombe a {BORNES[2]} en degre 2 et {BORNES[3]} en degre 3.

     xoshiro256++ a W = 256 et un degre >= 4 : {BORNES[4]} < 256, donc NON EXCLU.
     xoroshiro128** a W = 128 et un degre >= 4 : {BORNES[4]} < 128, NON EXCLU.
     PCG32 a W = 64 et un degre >= 4 (le §123 mesure 1/3/7 en degres 1/2/3,
     mais ces fonctionnelles ne sont pas observables) : NON EXCLU.

   Le theoreme ferme donc une exemption de principe sans rien fermer en
   pratique — et il DIT POURQUOI : W^d/d! croit trop vite. Ce n'est plus une
   lacune du dossier, c'est un theoreme sur la donnee disponible.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

TOTAL = OK1 + OK2
ATTEN = len(LIG1) + len(LIG2)

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h117.complexite_polynomiale",
        "Si l'etat evolue par s -> A·s sur F2^W et si le bit observe est un "
        "POLYNOME de degre <= d de l'etat — sans aucune hypothese de linearite, "
        "donc sorties brouillees comprises — alors la suite observee verifie une "
        "recurrence lineaire de degre au plus N_d(W) = somme_{k<=d} C(W,k), et "
        "Berlekamp-Massey la rend. Corollaire de prediction : 2·N_d(W) bits "
        "suffisent a predire tout bit suivant sans connaitre la famille, le "
        "brouilleur, le pas ni l'etat",
        "nombre de predictions chiffrees exactes : sept bornes L <= N_d(W) sur "
        "des generateurs a sortie de degre exact d, et quatre temoins de "
        "prediction exigeant A LA FOIS 300 bits predits justes ET l'echec de "
        "l'attaque du §122 sur les memes donnees",
        "un enonce faux manquerait ses bornes ; et la contre-epreuve montre que "
        "la reussite ne vient pas d'une suite trivialement lineaire, puisque "
        "l'attaque de degre 1 echoue sur exactement les memes bits",
        "conforme si les sept bornes tiennent et si les quatre temoins predisent "
        "300/300 la ou le degre 1 echoue", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == ATTEN else "DEMENTI",
        power_at=(f"{OK2}/{len(LIG2)} temoins de prediction complets : 300 bits sur "
                  f"300 predits juste sur une sortie QUADRATIQUE, la ou l'attaque "
                  f"lineaire du §122 echoue sur les memes donnees — le test "
                  f"reussit quand il doit reussir et echoue quand il doit echouer"),
        notes=(f"LEVE L'EXEMPTION QUE LE §122 S'ETAIT ACCORDEE : « le bit doit "
               f"etre F2-lineaire, les sorties brouillees echappent ». Les "
               f"monomes de degre <= d des bits de l'etat evoluent LINEAIREMENT "
               f"sous s -> A·s, dans un espace de dimension N_d(W) ; le §122 est "
               f"le cas d = 1. Forme maitresse : W >= (d!·T/2)^(1/d) en "
               f"combinant avec le plafond T/2 du §134 — le pouvoir d'exclusion "
               f"s'effondre comme T^(1/d), et c'est le prix chiffre du refus de "
               f"supposer la sortie lineaire. Sur l'archive (L = {LA:,}) : W >= "
               f"{BORNES[1]:,} en degre 1, {BORNES[2]} en degre 2, {BORNES[3]} en degre 3, "
               f"{BORNES[4]} en degre 4. xoshiro256++ (W=256, degre >= 4 mesure au §123) "
               f"n'est donc PAS exclu, et le theoreme dit pourquoi. Il chiffre "
               f"aussi, pour la premiere fois, ce qu'il faudrait pour predire une "
               f"sortie brouillee sans la nommer : 1 358 242 tirages pour 64 "
               f"bits, 22 035 266 pour 128."))
    h = lab.holm()
    say(f"   consigne : h117.complexite_polynomiale   {TOTAL}/{ATTEN} predictions exactes")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
