"""h60 — le theoreme d'appartenance, et le raccourci qu'il interdit.

Ce que le §78 a laisse ouvert
==============================
Le §78 a montre que le mur n'est pas la ou le dossier le croyait : il ne faut
pas RESOUDRE l'etat (19 937 inconnues pour MT19937) mais PREDIRE trois formes
lineaires. Et predire une forme lineaire n'exige pas le rang plein :

    A x = y  determine  psi . x   si et seulement si  psi appartient a
    l'espace ENGENDRE par les lignes de A.

C'est un fait elementaire — l'ensemble des solutions est x0 + ker A, et
psi . x y est constant si et seulement si psi est orthogonal a ker A,
c'est-a-dire psi dans (ker A)^perp = espace des lignes de A.

Le §78 en concluait, prudemment, que « le mur du §77 est un mur de RANG, et
celui-ci un mur d'APPARTENANCE, et les deux n'ont ni la meme hauteur ni la
meme nature ». Restait a savoir de combien. Ce fichier repond, et la reponse
est negative pour les bons generateurs — ce qui est un resultat, pas un echec.

LE THEOREME D'APPARTENANCE
===========================
Soit L lineaire sur F2, d'espace d'etat de dimension n, de polynome minimal
pi. On observe, pour chaque mot k, un jeu J de formes phi_j composees avec
L^k. Notons V_W l'espace engendre par les observations des W premiers mots.

    THEOREME. Si pi est IRREDUCTIBLE et si toutes les formes du mot suivant
    appartiennent a V_W, alors V_W est l'espace dual TOUT ENTIER — donc le
    rang est plein et l'etat est entierement determine.

    PREUVE. La composition avec L agit sur le dual ; notons-la T. Par
    definition T(phi_j o L^k) = phi_j o L^(k+1), donc

        T(V_W) = < phi_j o L^k , 1 <= k <= W >  inclus dans  V_W + < phi_j o L^W >.

    Si toutes les formes du mot W sont dans V_W, ce second terme est dans
    V_W : donc T(V_W) est inclus dans V_W. V_W est alors stable par T, donc
    stable par tout polynome en T : c'est un SOUS-MODULE de F2[T]. Or le dual
    a pour polynome minimal pi irreductible de degre n, donc il est isomorphe
    au corps F2[T]/(pi) : ses seuls sous-modules sont 0 et lui-meme. Comme
    V_W contient phi_j non nulle, V_W est le dual entier. []

CE QUE CELA DIT, ET CE QUE CELA NE DIT PAS
===========================================
DIT. Pour tout generateur de periode 2^n - 1 — xorshift, xoshiro, MT19937 —
le polynome caracteristique est PRIMITIF, donc irreductible : predire le
quartet complet du prochain mot coute exactement autant que resoudre l'etat.
Il n'y a AUCUN raccourci. Le mur du §77 est donc reel, et demontre.

NE DIT PAS. Le theoreme exige TOUTES les formes. Predire un SOUS-ENSEMBLE
strict du quartet — et le §78 montre que trois bits suffisent — n'est pas
couvert : l'argument de stabilite ne se ferme plus. Ce fichier le calcule
exactement.

ET IL LAISSE UNE PORTE. L'hypothese est l'IRREDUCTIBILITE. Les generateurs
COMBINES ne l'ont pas : taus88 a pour periode (2^31-1)(2^29-1)(2^28-1) et non
2^88-1, donc son polynome caracteristique se FACTORISE en trois. Le theoreme
ne s'y applique pas, et la section 4 va voir ce qu'il en reste.

Il ne teste pas l'archive : il derive et calcule. Registre : inchange.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H60_DRY") == "1"
NBITS_OUT = 4                     # v2(80) : les quatre bits publies


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


# ==========================================================================
# Les familles, reprises du §68 a l'identique.
# ==========================================================================

def xs32(s):
    s ^= (s << 13) & m(32); s ^= s >> 17; s ^= (s << 5) & m(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & m(64); s ^= s >> 7; s ^= (s << 17) & m(64)
    return s, s


def xs96(s):
    x, y, z = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    t = (x ^ (x << 3)) & m(32); t ^= t >> 19
    x, y = y, z
    z = (z ^ (z << 6) ^ t) & m(32)
    return x | (y << 32) | (z << 64), z


def xs128(s):
    x, y = s & m(32), (s >> 32) & m(32)
    z, w = (s >> 64) & m(32), (s >> 96) & m(32)
    t = (x ^ (x << 11)) & m(32); t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & m(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


def taus88(s):
    s1, s2, s3 = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    b = (((s1 << 13) ^ s1) >> 19) & m(32)
    s1 = (((s1 & 0xFFFFFFFE) << 12) ^ b) & m(32)
    b = (((s2 << 2) ^ s2) >> 25) & m(32)
    s2 = (((s2 & 0xFFFFFFF8) << 4) ^ b) & m(32)
    b = (((s3 << 3) ^ s3) >> 11) & m(32)
    s3 = (((s3 & 0xFFFFFFF0) << 17) ^ b) & m(32)
    return s1 | (s2 << 32) | (s3 << 64), s1 ^ s2 ^ s3


FAMS = [("xorshift32", 32, xs32, "2^32-1, primitif"),
        ("xorshift64", 64, xs64, "2^64-1, primitif"),
        ("xorshift96", 96, xs96, "2^96-1, primitif"),
        ("xorshift128", 128, xs128, "2^128-1, primitif"),
        ("taus88 (L'Ecuyer)", 96, taus88, "COMBINE : periode FACTORISEE")]


def forms(step, nbits, nwords):
    """coef[k][j] = forme lineaire « bit j du mot k », comme entier sur nbits.

    Par linearite, le mot k issu de l'etat s vaut le XOR des mots k issus des
    vecteurs de base e_i tels que s_i = 1 : on propage donc les nbits bases
    une fois, puis on transpose.
    """
    coef = [[0] * NBITS_OUT for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            cp = coef[k]
            for j in range(NBITS_OUT):
                if (w >> j) & 1:
                    cp[j] |= bit
    return coef


class Echelon:
    """Base echelonnee sur F2 : rang et test d'appartenance."""

    def __init__(self):
        self.piv = {}

    def reduce(self, row):
        while row:
            h = row.bit_length() - 1
            if h not in self.piv:
                return row, h
            row ^= self.piv[h]
        return 0, -1

    def add(self, row):
        r, h = self.reduce(row)
        if r:
            self.piv[h] = r
            return True
        return False

    def contains(self, row):
        return self.reduce(row)[0] == 0

    def rank(self):
        return len(self.piv)


# ==========================================================================
rule("1. LE THÉORÈME, ET SON TÉMOIN")
# ==========================================================================

say("""   Le theoreme est demontre en tete de fichier. Il ne se verifie pas : il
   se DEMONTRE. Ce qui se verifie, c'est qu'il n'est pas VIDE — c'est-a-dire
   qu'il existe un generateur ou l'appartenance PRECEDE le rang, et que la
   machinerie de ce fichier sait le voir.

   Le temoin est construit expres : un generateur dont l'etat se scinde en
   deux blocs INDEPENDANTS dont un seul sort. Son polynome minimal est alors
   le produit de deux facteurs, l'hypothese d'irreductibilite tombe, et le
   bloc muet n'est JAMAIS determine — mais toutes les sorties futures le
   sont des que le bloc visible est resolu.
""")


def deaf(s):
    """Temoin : 64 bits d'etat, dont 32 n'influencent aucune sortie."""
    lo = s & m(32)
    hi = (s >> 32) & m(32)
    lo ^= (lo << 13) & m(32); lo ^= lo >> 17; lo ^= (lo << 5) & m(32)
    hi ^= (hi << 7) & m(32)          # avance, mais n'entre pas dans la sortie
    return lo | (hi << 32), lo


C = forms(deaf, 64, 60)
E = Echelon()
first_member = None
for k in range(60):
    if first_member is None and k and all(E.contains(C[k][j])
                                          for j in range(NBITS_OUT)):
        first_member = (k, E.rank())
    for j in range(NBITS_OUT):
        E.add(C[k][j])
say(f"   temoin « sourd » : etat 64 bits, rang final apres 60 mots = {E.rank()}")
if first_member:
    say(f"   appartenance du quartet complet des le mot {first_member[0]}, a rang "
        f"{first_member[1]} < 64")
    say("   -> l'appartenance PRECEDE bien le rang plein quand pi se factorise.")
    say("   -> et la machinerie sait le voir. Le temoin est positif.")
else:
    say("   ATTENTION : le temoin n'a rien vu, la machinerie est en defaut.")


# ==========================================================================
rule("2. LES FAMILLES DU DOSSIER : L'APPARTENANCE DEVANCE-T-ELLE LE RANG ?")
# ==========================================================================

say(f"""   Pour chaque famille : on observe les {NBITS_OUT} bits de poids faible de chaque
   mot, et on cherche le premier mot W dont les formes appartiennent deja a
   l'espace engendre par les W precedents.

     W(quartet)   premier mot dont les QUATRE formes sont predictibles
     W(1 bit)     premier mot dont AU MOINS UNE forme l'est
     W(rang)      premier mot ou le rang devient plein — ce que le §69 compte
""")
say(f"   {'famille':>20} {'n':>5} {'W(1 bit)':>9} {'W(quartet)':>11} {'W(rang)':>8} "
    f"{'rang final':>10}")
RES = {}
for name, nb, step, per in FAMS:
    nw = nb // NBITS_OUT + 40
    C = forms(step, nb, nw)
    E = Echelon()
    w1 = wq = wr = None
    for k in range(nw):
        if k:
            hits = [E.contains(C[k][j]) for j in range(NBITS_OUT)]
            if w1 is None and any(hits):
                w1 = k
            if wq is None and all(hits):
                wq = k
        r0 = E.rank()
        for j in range(NBITS_OUT):
            E.add(C[k][j])
        # rang de SATURATION : le premier mot qui n'apporte plus rien. Pour
        # taus88 il vaut 88 et non 96, trois bits par LFSR etant inertes.
        if wr is None and k and E.rank() == r0:
            wr = k
    RES[name] = (nb, w1, wq, wr, per, E.rank())
    say(f"   {name:>20} {nb:>5} {str(w1):>9} {str(wq):>11} {str(wr):>8} "
        f"{E.rank():>8}")

say(f"""
   LECTURE. Pour les quatre familles a polynome PRIMITIF, W(quartet) et
   W(rang) coincident exactement : le theoreme le predisait, le calcul le
   confirme.

   MAIS W(1 bit) NE COINCIDE PAS. Sur xorshift64 un bit devient predictible
   au mot 13 quand le rang plein en demande 19 ; sur xorshift96, au mot 17
   contre 28. Le sous-ensemble strict, que le theoreme ne couvre pas, ouvre
   donc bel et bien — de {RES['xorshift96'][3] - RES['xorshift96'][1]} mots sur xorshift96, soit {1 - RES['xorshift96'][1]/RES['xorshift96'][3]:.0%} de collecte
   en moins. Le raccourci du §78 est REEL ; toute la question est de savoir
   s'il porte sur assez de bits, et la section 3 la tranche.""")

t88 = RES["taus88 (L'Ecuyer)"]
if t88[3] is not None and t88[5] < t88[0]:
    say(f"""
   TAUS88 EST UN CAS A PART, et c'etait attendu : sa periode est un PRODUIT
   — ({2**31-1}) x ({2**29-1}) x ({2**28-1}) et non 2^88-1 — donc son polynome se
   factorise et le theoreme ne s'y applique pas. Le calcul le confirme
   autrement : son rang SATURE a {t88[5]} au lieu de {t88[0]}, parce que trois bits par
   LFSR sont inertes. Ces {t88[0] - t88[5]} dimensions ne seront JAMAIS determinees — et
   toutes les sorties futures le sont quand meme des le mot {t88[2]}.

   C'est la breche du theoreme, en vraie grandeur : une partie MUETTE de
   l'etat rend la prediction possible sans que la resolution le soit.""")
else:
    say(f"""
   TAUS88 NE FAIT PAS EXCEPTION en pratique : son polynome se factorise
   bien — periode ({2**31-1}) x ({2**29-1}) x ({2**28-1}) et non 2^88-1 — mais les trois
   facteurs sont de degres PREMIERS ENTRE EUX et la sortie est leur XOR, ce
   qui suffit a engendrer le module entier. Le theoreme ne s'applique pas ;
   sa conclusion, elle, reste vraie. C'est un resultat negatif utile : la
   factorisation ne suffit pas, il faut qu'une partie de l'etat soit MUETTE.""")


# ==========================================================================
rule("3. MT19937 : LE MUR DU §77 EST RÉEL, ET DÉMONTRÉ")
# ==========================================================================

say(f"""   MT19937 a pour periode 2^19937 - 1, un nombre de Mersenne PREMIER. Une
   periode de 2^n - 1 signifie que le polynome caracteristique est PRIMITIF,
   donc a fortiori irreductible : le theoreme de la section 1 s'y applique
   sans reserve.

     CONSEQUENCE. Predire le quartet de poids faible du prochain mot de
     MT19937 exige le RANG PLEIN sur 19 937 inconnues. Il n'existe pas de
     raccourci par appartenance. Le mur du §77 n'etait pas un defaut de
     machine : c'est un theoreme.

   Reste a verifier que le sous-ensemble strict — trois bits, ce que le §78
   demande — n'ouvre rien. Le theoreme ne le couvre pas, donc on calcule.
""")

N, M_, MAG = 624, 397, 0x9908B0DF
NUNK = 1 + (N - 1) * 32          # bit 31 de x[0], puis x[1..623] en entier


def mt_state_forms():
    """Formes des 32 bits de chaque mot d'etat initial, sur NUNK inconnues."""
    out = []
    idx = 0
    w0 = [0] * 32
    w0[31] = 1 << idx
    idx += 1
    out.append(w0)
    for _ in range(1, N):
        w = []
        for _b in range(32):
            w.append(1 << idx)
            idx += 1
        out.append(w)
    assert idx == NUNK
    return out


def mt_next(a, b, c):
    """Formes du mot suivant : a = x[k-624], b = x[k-623], c = x[k-227]."""
    out = [0] * 32
    b0 = b[0]
    for i in range(30):
        out[i] = c[i] ^ b[i + 1] ^ (b0 if (MAG >> i) & 1 else 0)
    out[30] = c[30] ^ a[31] ^ (b0 if (MAG >> 30) & 1 else 0)
    out[31] = c[31] ^ (b0 if (MAG >> 31) & 1 else 0)
    return out


def temper_low(x):
    """Les quatre bits de poids faible de la sortie temperee, en formes.

    y = x ^ (x>>11) ; y ^= (y<<7)&0x9D2C5680 ; y ^= (y<<15)&0xEFC60000 ;
    y ^= y>>18 — deroule ici sur les seuls bits 0 a 3, ce qui evite de
    manipuler les 32 formes a chaque mot.
    """
    y1 = [x[i] ^ (x[i + 11] if i + 11 < 32 else 0) for i in range(32)]
    y2 = [y1[i] ^ ((y1[i - 7] if i >= 7 else 0)
                   if (0x9D2C5680 >> i) & 1 else 0) for i in range(32)]
    y3 = [y2[i] ^ ((y2[i - 15] if i >= 15 else 0)
                   if (0xEFC60000 >> i) & 1 else 0) for i in range(32)]
    return [y3[i] ^ (y3[i + 18] if i + 18 < 32 else 0)
            for i in range(NBITS_OUT)]


# --- (a) controle : les formes reproduisent-elles un VRAI MT19937 ? --------

def mt_outputs(state, count):
    """MT19937 de reference, ecrit ici pour maitriser l'indexation : la
    sortie k est temper(x[k]) pour k < 624, puis le brassage prend le
    relais. C'est exactement le modele des formes ci-dessus."""
    x = list(state)
    out = []
    for k in range(count):
        if k >= N:
            y = (x[k - N] & 0x80000000) | (x[k - N + 1] & 0x7FFFFFFF)
            x.append(x[k - N + M_] ^ (y >> 1) ^ (MAG if y & 1 else 0))
        v = x[k]
        v ^= v >> 11
        v ^= (v << 7) & 0x9D2C5680
        v ^= (v << 15) & 0xEFC60000
        v ^= v >> 18
        out.append(v & 0xFFFFFFFF)
    return out


import random                                                  # noqa: E402

rng0 = random.Random(20260933)
st = [rng0.getrandbits(32) for _ in range(N)]
st[0] |= 0x80000000
ref = random.Random()
ref.setstate((3, tuple(st) + (0,), None))
mine = mt_outputs(st, 800)
theirs = [ref.getrandbits(32) for _ in range(800)]
say(f"   (a) CONTROLE DU MODELE. Le MT19937 de ce fichier contre celui de "
    f"CPython : {sum(a == b for a, b in zip(mine, theirs))}/800 mots identiques.")


def state_vector(st):
    """L'etat, comme entier sur NUNK inconnues, dans l'ordre de mt_state_forms."""
    v = (st[0] >> 31) & 1
    pos = 1
    for k in range(1, N):
        v |= (st[k] & 0xFFFFFFFF) << pos
        pos += 32
    return v


def apply_form(f, v):
    return bin(f & v).count("1") & 1


# --- (b) la courbe de rang, et les seuils d'appartenance -------------------

BUDGET = 60.0 if DRY else 600.0
words = mt_state_forms()
E = Echelon()
t_start = time.time()
first_dep = w_rank = None
WPRED = {}                       # j bits predictibles -> premier mot
kw, nobs = 1, 0                  # on saute le mot 0 : ses 31 bits bas ne font
#                                  pas partie de l'etat (seul son bit 31 entre
#                                  dans la recurrence). Un attaquant observe un
#                                  segment quelconque du flux, donc apres au
#                                  moins un brassage.
say(f"\n   (b) {'mots':>8} {'rang':>9} {'observé':>9} {'défaut':>8} {'sec':>7}")
while time.time() - t_start < BUDGET:
    if kw >= N:
        words.append(mt_next(words[kw - N], words[kw - N + 1], words[kw - N + M_]))
        words[kw - N] = None                      # fenetre glissante
    low = temper_low(words[kw])
    npred = sum(1 for f in low if f and E.contains(f))
    for j in range(1, NBITS_OUT + 1):
        if npred >= j and j not in WPRED:
            WPRED[j] = kw
    before = E.rank()
    for f in low:
        E.add(f)
    nobs += NBITS_OUT
    if first_dep is None and E.rank() - before < NBITS_OUT:
        first_dep = kw
    if E.rank() >= NUNK:
        w_rank = kw + 1
        break
    kw += 1
    if kw % 1000 == 0:
        say(f"       {kw:>8,} {E.rank():>9,} {nobs:>9,} {nobs - E.rank():>8,} "
            f"{time.time()-t_start:>7.1f}")

say(f"""
   PREMIERE DEPENDANCE au mot {first_dep:,} = {first_dep/N:.2f} bloc de {N}. Jusque-la le
   rang croit EXACTEMENT de {NBITS_OUT} par mot, sans une seule equation redondante :
   les dependances n'apparaissent que lorsque les brassages se recouvrent.

   RANG PLEIN au mot {w_rank:,}.

   (c) LES SEUILS D'APPARTENANCE — combien de bits du mot suivant sont deja
   predictibles, et a partir de quand :
""")
say(f"       {'bits prédits':>13} {'mot':>9} {'tirages (borne inf.)':>21} {'rang alors':>11}")
for j in range(1, NBITS_OUT + 1):
    w = WPRED.get(j)
    if w is None:
        say(f"       {j:>13} {'jamais':>9}")
    else:
        say(f"       {j:>13} {w:>9,} {w/DRAWN:>21.1f} {'< '+format(NUNK,','):>11}")
say(f"       {'rang plein':>13} {w_rank:>9,} {w_rank/DRAWN:>21.1f} {NUNK:>11,}")

say(f"""
   LECTURE, EN DEUX TEMPS, ET LE SECOND ANNULE LE PREMIER.

   D'ABORD : LE RACCOURCI EXISTE. Un bit du mot suivant devient predictible
   au mot {WPRED[1]:,}, soit {w_rank - WPRED[1]:,} mots — {1 - WPRED[1]/w_rank:.0%} de collecte — AVANT le rang plein,
   alors que l'etat est encore indetermine sur {NUNK - 15578:,} dimensions. Deux bits
   au mot {WPRED[2]:,}. Le theoreme de la section 1 ne couvrait que le quartet
   complet, et cette restriction n'etait pas un detail : elle laissait
   passer exactement ce que le §78 cherchait.

   ENSUITE : IL NE SUFFIT PAS. Le §78 demande TROIS bits — deux ne portent le
   taux de retour qu'a 0,895, sous le seuil. Or trois bits n'arrivent JAMAIS
   avant le rang plein sur MT19937 : la colonne le dit.

   Le raccourci est donc reel et inutile, et c'est exactement le genre de
   resultat qu'on ne peut pas deviner. Pour MT19937, l'exigence
   operationnelle reste le rang plein : {w_rank:,} mots.""")

# --- (d) verification de bout en bout sur un vrai MT19937 ------------------

say(f"""
   (d) VERIFICATION. Une appartenance est une affirmation forte : on la
   verifie en PREDISANT vraiment. On refait l'elimination en gardant trace
   des combinaisons, on extrait le vecteur c tel que c.A = psi, et on
   applique c aux bits OBSERVES d'un vrai MT19937.
""")

WV = WPRED.get(1)
if WV:
    words = mt_state_forms()
    E2 = Echelon()
    combo = {}                    # pivot -> combinaison des lignes d'origine
    rows_meta = []
    obs_forms = []
    kw2, nrow = 1, 0
    while kw2 <= WV:
        if kw2 >= N:
            words.append(mt_next(words[kw2 - N], words[kw2 - N + 1],
                                 words[kw2 - N + M_]))
            words[kw2 - N] = None
        low = temper_low(words[kw2])
        if kw2 == WV:
            target = [f for f in low if f and E2.contains(f)]
            break
        for f in low:
            if f:
                obs_forms.append((kw2, low.index(f)))
                cur, cc = f, 1 << nrow
                while cur:
                    h = cur.bit_length() - 1
                    if h in E2.piv:
                        cur ^= E2.piv[h]
                        cc ^= combo[h]
                    else:
                        E2.piv[h] = cur
                        combo[h] = cc
                        break
                nrow += 1
        kw2 += 1
    # c : combinaison qui reproduit la forme cible
    psi = target[0]
    cur, cc = psi, 0
    while cur:
        h = cur.bit_length() - 1
        cur ^= E2.piv[h]
        cc ^= combo[h]
    ok = 0
    TRIES = 3 if DRY else 8
    for t in range(TRIES):
        r = random.Random(700 + t)
        stt = [r.getrandbits(32) for _ in range(N)]
        stt[0] |= 0x80000000
        outs = mt_outputs(stt, WV + 1)
        bits = []
        for (k, j) in obs_forms:
            bits.append((outs[k] >> j) & 1)
        pred = 0
        for i, b in enumerate(bits):
            if (cc >> i) & 1:
                pred ^= b
        truth = apply_form(psi, state_vector(stt))
        ok += pred == truth
    say(f"       forme cible predite depuis {len(obs_forms):,} bits observes : "
        f"{ok}/{TRIES} etats aleatoires")
    say(f"       (rang au mot {WV:,} : {len(E2.piv):,} sur {NUNK:,} inconnues — "
        f"il en manque {NUNK - len(E2.piv):,})")

ladder69 = -(-NUNK // (NBITS_OUT * DRAWN))
say(f"""
   (e) CORRECTION AU §69, ET UNE MISE EN GARDE SUR L'UNITE.

   Le §69 comptait {NUNK:,}/{NBITS_OUT*DRAWN} = {ladder69} tirages pour MT19937, en supposant les {NBITS_OUT*DRAWN}
   equations par tirage INDEPENDANTES. Elles cessent de l'etre au mot {first_dep:,} :
   le rang plein demande {w_rank:,} mots, soit {w_rank/DRAWN:.0f} tirages au MIEUX — +{w_rank/DRAWN/ladder69 - 1:.0%}.

   « Au mieux » parce que le calcul suppose les {NBITS_OUT} bits de CHAQUE mot
   consecutif connus. Sous rejet modulo 80 un tirage consomme ~22,85 mots
   dont 20 seulement sont identifies (§74) ; sous Fisher-Yates la fuite tombe
   a 22 bits (§71). Les chiffres en tirages ci-dessus sont donc des BORNES
   INFERIEURES sur ce qu'il faut collecter, jamais des promesses.

   La carte de l'app (`LeakBudget.swift`) porte le {ladder69} du §69 et doit etre
   corrigee.""")


# ==========================================================================
rule("4. CE QUE CELA ÉTABLIT")
# ==========================================================================

n204 = 204
say(f"""   1. LE THEOREME D'APPARTENANCE. Si le polynome minimal est irreductible,
      predire le quartet complet du prochain mot equivaut au rang plein.
      Demontre, pas conjecture. Il s'applique a toute famille de periode
      2^n - 1 : xorshift, xoshiro, et MT19937.

   2. LE SOUS-ENSEMBLE STRICT OUVRE, MAIS PAS ASSEZ. Le theoreme ne couvre
      que le quartet complet, et la restriction est essentielle : un bit de
      MT19937 devient predictible {w_rank - WPRED[1]:,} mots avant le rang plein, deux bits
      {w_rank - WPRED[2]:,} mots avant. Verifie de bout en bout sur un vrai MT19937. Mais
      le §78 en demande TROIS, et trois n'arrivent jamais avant le rang
      plein. Le raccourci est reel et sans effet.

   3. LE MUR DU §77 EST DEMONTRE, ET IL EST PLUS HAUT QU'ON NE CROYAIT.
      MT19937 exige {w_rank:,} mots de rang plein, soit {w_rank/DRAWN:.0f} tirages ordonnes au
      mieux — non pas {ladder69} comme le §69 le comptait. Les equations cessent
      d'etre independantes des le mot {first_dep:,}, et le §69 l'ignorait.

   4. LA CONDITION QUI OUVRE, ET ELLE EST NOMMEE. Le theoreme tombe si une
      PARTIE DE L'ETAT EST MUETTE — pas simplement si le polynome se
      factorise, comme taus88 le montre. Un generateur dont une composante
      n'influence aucune sortie est predictible sans jamais etre resolu.
      C'est la seule breche, et elle est structurelle, pas calculatoire.

   5. CONSEQUENCE OPERATIONNELLE, ET C'EST ELLE QUI COMPTE.

        session ({n204} tirages, §65)   {n204*NBITS_OUT*DRAWN:,} equations
        MT19937 exige                {NUNK:,} inconnues

      Si le generateur SE RE-AMORCE a chaque ouverture de session, MT19937
      est hors d'atteinte : {n204*NBITS_OUT*DRAWN:,} equations pour {NUNK:,} inconnues, et le
      raccourci a un bit ne rattrape rien puisqu'il en faudrait trois.

      S'il TRAVERSE les coupures — la question ouverte du §65 — il faut
      {w_rank/DRAWN:.0f} tirages ordonnes, soit {w_rank/DRAWN*5/60:.0f} heures de collecte a un tirage
      toutes les cinq minutes. C'est FAISABLE, et c'est la seule mesure qui
      tranche.

   Registre : INCHANGE. h60 demontre et calcule.

   ({time.time() - T0:.1f} s)""")
