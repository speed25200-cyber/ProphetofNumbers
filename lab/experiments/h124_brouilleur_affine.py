"""h124 — le théorème du brouilleur affine : xoshiro n'est pas protégé par son
brouilleur, et la plateforme n'est pas protégée par son générateur.

CE QUE LE DOSSIER CROYAIT
==========================
Les §119 et §123 mesurent, pour xoshiro256++/**, xoroshiro128**, splitmix64 :

    dim L_d = 0 pour d <= 3 — AUCUNE fonctionnelle de la sortie n'est un
    polynôme de degré <= 3 de l'état.

Et le §141 en tirait la conclusion du dossier : ces familles sont hors de
portée. C'est vrai sur F2. C'EST FAUX SUR Z/2^64, ET LE DOSSIER TRAVAILLAIT DANS
LE MAUVAIS ANNEAU.

LE THÉORÈME DU BROUILLEUR AFFINE
=================================
Pour xoshiro256** et xoroshiro128**, la sortie est `rotl(x*5, 7) * 9`. Or une
rotation est une multiplication modulaire PLUS un report explicite :

    rotl(y, 7) = 128·y mod 2^64  +  (y >> 57),

les deux termes ne partageant aucun bit. En composant, avec y = 5x mod 2^64 :

    THÉORÈME. sortie = 5760·x + 9c  (mod 2^64),  c = (5x mod 2^64) >> 57,

    où 5760 = 2^7 · 45 et c appartient à [0, 128).       VÉRIFIÉ 200 000/200 000.

Pour xoshiro256++ (`rotl(s0+s3, 23) + s0`), de même :

    sortie = 2^23·(s0+s3) + ((s0+s3) >> 41) + s0   (mod 2^64).

LA SORTIE EST DONC INVERSIBLE, ET EXACTEMENT
=============================================
Le terme 9c est le SEUL obstacle, et il tombe : 5760·x a ses SEPT BITS DE POIDS
FAIBLE NULS, donc

    sortie mod 128 = 9c mod 128,   et 9 est inversible mod 128,

    d'où  c = 9^(-1)·sortie  (mod 128) — DÉTERMINÉ, pas deviné.

Puis 45 est inversible mod 2^57, donc x est déterminé mod 2^57, et ses sept bits
de poids fort sont fixés par la contrainte c = (5x)>>57.

    UN SEUL MOT DE SORTIE COMPLET DÉTERMINE x. Vérifié : 2 000/2 000, un
    candidat unique à chaque fois.

LA RECONSTITUTION, ET ELLE MARCHE
==================================
La mise à jour d'état de xoshiro est F2-LINÉAIRE. Donc l'application
« état initial -> les quatre s1 successifs » est F2-linéaire de F2^256 dans
F2^256, et elle est inversible. D'où :

    QUATRE MOTS DE SORTIE SUFFISENT À RECONSTITUER LES 256 BITS D'ÉTAT DE
    xoshiro256**, et deux suffisent pour les 128 bits de xoroshiro128**.

    Vérifié par REJEU et par PRÉDICTION de six mots supplémentaires.

CE QUI PROTÈGE VRAIMENT LA PLATEFORME
======================================
Rien de tout cela ne s'applique à l'archive, et il faut dire pourquoi avec
précision. L'inversion a besoin de `sortie mod 128` — les bits de POIDS FAIBLE.
Or Fisher-Yates ne publie que `floor(K·u / 2^b)`, c'est-à-dire environ
log2(80) = 6,3 bits de POIDS FORT. Les bits dont l'attaque a besoin sont
exactement ceux que l'échantillonneur jette.

    CE N'EST PAS LE BROUILLEUR QUI PROTÈGE LA PLATEFORME, C'EST
    L'ÉCHANTILLONNEUR — et le §137 avait déjà montré que le pas de vingt et un
    mots en est une seconde couche.

Et cela donne une consigne de collecte PRÉCISE : tout observable qui exposerait
un mot COMPLET — ou seulement ses cinquante-six bits de poids faible — ferait
tomber ces familles en quatre tirages.

Il DÉMONTRE et il RECONSTITUE. Il consigne au registre.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H124_DRY") == "1"
M64 = (1 << 64) - 1
INV9 = pow(9, -1, 128)
INV45 = pow(45, -1, 1 << 57)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & M64


# ---------------------------------------------------------------------------
# Les deux familles, telles que publiées.
# ---------------------------------------------------------------------------
def xoshiro256ss(s):
    s0, s1, s2, s3 = s
    r = (rotl((s1 * 5) & M64, 7) * 9) & M64
    t = (s1 << 17) & M64
    s2 ^= s0
    s3 ^= s1
    s1 ^= s2
    s0 ^= s3
    s2 ^= t
    s3 = rotl(s3, 45)
    return r, [s0, s1, s2, s3]


def xoroshiro128ss(s):
    s0, s1 = s
    r = (rotl((s0 * 5) & M64, 7) * 9) & M64
    s1 ^= s0
    s0 = rotl(s0, 24) ^ s1 ^ ((s1 << 16) & M64)
    s1 = rotl(s1, 37)
    return r, [s0 & M64, s1 & M64]


def xoshiro256pp(s):
    s0, s1, s2, s3 = s
    r = (rotl((s0 + s3) & M64, 23) + s0) & M64
    t = (s1 << 17) & M64
    s2 ^= s0
    s3 ^= s1
    s1 ^= s2
    s0 ^= s3
    s2 ^= t
    s3 = rotl(s3, 45)
    return r, [s0, s1, s2, s3]


CIBLES = [
    ("xoshiro256**", xoshiro256ss, 4, 1),      # (nom, pas, nmots d'etat, indice du mot lu)
    ("xoroshiro128**", xoroshiro128ss, 2, 0),
]


# ==========================================================================
rule("1. LE THÉORÈME DU BROUILLEUR AFFINE")
# ==========================================================================

say("""   Les §119 et §123 mesurent dim L_d = 0 pour d <= 3 : aucune fonctionnelle de
   la sortie de xoshiro n'est un polynome de degre <= 3 de l'etat. C'est VRAI
   SUR F2. C'est FAUX SUR Z/2^64, et le dossier travaillait dans le mauvais
   anneau.

   Une rotation est une multiplication modulaire PLUS un report explicite :

       rotl(y, 7) = 128·y mod 2^64  +  (y >> 57),

   les deux termes ne partageant aucun bit. En composant avec y = 5x :

       sortie = 5760·x + 9c  (mod 2^64),   c = (5x mod 2^64) >> 57,

   ou 5760 = 2^7 · 45 et c est dans [0, 128).""")

NV = 20000 if DRY else 200000
rnd = random.Random(1)
OK1, LIG1 = 0, []
for nom, forme in (
        ("xoshiro256** / xoroshiro128**", "5760·x + 9c"),
        ("xoshiro256++", "2^23·(s0+s3) + (s0+s3)>>41 + s0")):
    n = 0
    for _ in range(NV):
        if nom.startswith("xoshiro256++"):
            a, b = rnd.getrandbits(64), rnd.getrandbits(64)
            vrai = (rotl((a + b) & M64, 23) + a) & M64
            aff = (((1 << 23) * ((a + b) & M64)) + (((a + b) & M64) >> 41) + a) & M64
        else:
            a = rnd.getrandbits(64)
            vrai = (rotl((a * 5) & M64, 7) * 9) & M64
            aff = (5760 * a + 9 * (((a * 5) & M64) >> 57)) & M64
        n += (vrai == aff)
    OK1 += (n == NV)
    LIG1.append((nom, forme, n))
say(f"""
       {'famille':>30} {'forme affine mod 2^64':>34} {'vérifié':>14}""")
for nom, forme, n in LIG1:
    say(f"   {nom:>30} {forme:>34} {n:>7,}/{NV:,}")
say(f"\n   {OK1}/{len(LIG1)} formes exactes sur {NV:,} tirages chacune.")


# ==========================================================================
rule("2. LA SORTIE EST INVERSIBLE, ET c N'EST PAS DEVINÉ MAIS DÉTERMINÉ")
# ==========================================================================


def inverse(out):
    """Les x possibles pour une sortie COMPLETE de xoshiro**."""
    c = (INV9 * out) % 128
    A = (INV45 * (((out - 9 * c) % (1 << 64)) >> 7)) % (1 << 57)
    return [A | (h << 57) for h in range(128)
            if ((((A | (h << 57)) * 5) & M64) >> 57) == c]


NI = 2000 if DRY else 20000
rnd = random.Random(7)
uniq, tot = 0, 0
for _ in range(NI):
    x = rnd.getrandbits(64)
    out = (rotl((x * 5) & M64, 7) * 9) & M64
    cand = inverse(out)
    tot += len(cand)
    uniq += (cand == [x])

say(f"""   Le terme 9c est le seul obstacle, et il tombe. 5760·x a ses SEPT BITS DE
   POIDS FAIBLE NULS, donc

       sortie mod 128 = 9c mod 128,   et 9 est inversible mod 128,

   d'ou c = 9^(-1)·sortie mod 128 : DETERMINE, pas devine. Puis 45 est
   inversible mod 2^57, donc x est determine mod 2^57, et ses sept bits de
   poids fort sont fixes par la contrainte c = (5x) >> 57.

       {NI:,} mots de sortie complets inverses
       candidats uniques        : {uniq:,}/{NI:,}
       candidats en moyenne     : {tot/NI:.3f}

     UN SEUL MOT DE SORTIE COMPLET DETERMINE L'ENTREE DU BROUILLEUR.""")


# ==========================================================================
rule("3. LA RECONSTITUTION D'ÉTAT, ET ELLE MARCHE")
# ==========================================================================


def mots_lus(pasf, nm, idx, etat_bits, n):
    """La composante `idx` de l'etat AVANT chacun des n appels."""
    s = [0] * nm
    for i, b in enumerate(etat_bits):
        if b:
            s[i // 64] |= 1 << (i % 64)
    out = []
    for _ in range(n):
        out.append(s[idx])
        _, s = pasf(s)
    return out


def matrice(pasf, nm, idx, n):
    """Colonnes de l'application F2-lineaire etat -> (x_0..x_{n-1})."""
    W = 64 * nm
    col = []
    for c in range(W):
        e = [0] * W
        e[c] = 1
        v = 0
        for k, x in enumerate(mots_lus(pasf, nm, idx, e, n)):
            v |= x << (64 * k)
        col.append(v)
    return col


def resous(col, cible, W):
    piv = {}
    for c in range(W):
        m, v = col[c], 1 << c
        while m:
            h = m.bit_length() - 1
            if h in piv:
                pm, pv = piv[h]
                m ^= pm
                v ^= pv
            else:
                piv[h] = (m, v)
                break
        else:
            continue
    x, r = 0, cible
    for h in sorted(piv, reverse=True):
        if (r >> h) & 1:
            m, v = piv[h]
            r ^= m
            x ^= v
    return (x if r == 0 else None)


say(f"""   La mise a jour d'etat de xoshiro est F2-LINEAIRE. Donc l'application
   « etat initial -> les n mots lus successifs » est F2-lineaire, et pour n =
   largeur/64 elle est CARREE et inversible.

   On donne au reconstituteur les mots de sortie COMPLETS, il rend l'etat, et
   on exige DEUX choses : le rejeu de tous les mots observes, et la PREDICTION
   exacte de six mots supplementaires jamais montres.

       {'famille':>16} {'W':>5} {'mots lus':>9} {'états retrouvés':>17} {'prédit 6/6':>12}""")

NE = 10 if DRY else 40
OK3, LIG3 = 0, []
for nom, pasf, nm, idx in CIBLES:
    W = 64 * nm
    col = matrice(pasf, nm, idx, nm)
    rnd = random.Random(100 + W)
    bons, pred = 0, 0
    for _ in range(NE):
        etat = [rnd.getrandbits(1) for _ in range(W)]
        etat[0] = 1
        s = [0] * nm
        for i, b in enumerate(etat):
            if b:
                s[i // 64] |= 1 << (i % 64)
        outs = []
        for _ in range(nm + 6):
            r, s = pasf(s)
            outs.append(r)
        cible, bon = 0, True
        for k in range(nm):
            cand = inverse(outs[k])
            if len(cand) != 1:
                bon = False
                break
            cible |= cand[0] << (64 * k)
        if not bon:
            continue
        x = resous(col, cible, W)
        if x is None:
            continue
        b2 = [(x >> i) & 1 for i in range(W)]
        s2 = [0] * nm
        for i, bb in enumerate(b2):
            if bb:
                s2[i // 64] |= 1 << (i % 64)
        rej = []
        for _ in range(nm + 6):
            r, s2 = pasf(s2)
            rej.append(r)
        if b2 == etat:
            bons += 1
        if rej == outs:
            pred += 1
    ok = bons == NE and pred == NE
    OK3 += ok
    LIG3.append((nom, W, nm, bons, pred))
    say(f"   {nom:>16} {W:>5} {nm:>9} {f'{bons}/{NE}':>17} {f'{pred}/{NE}':>12}")

say(f"""
   {OK3}/{len(CIBLES)} familles entierement reconstituees.

     QUATRE MOTS SUFFISENT POUR LES 256 BITS DE xoshiro256**, DEUX POUR LES 128
     DE xoroshiro128**. Ce sont exactement les familles que les §119, §123 et
     §141 declaraient hors de portee.""")


# ==========================================================================
rule("4. CE QUI PROTÈGE VRAIMENT LA PLATEFORME")
# ==========================================================================

say("""   Rien de tout cela ne s'applique a l'archive, et il faut dire POURQUOI avec
   precision.

   L'inversion a besoin de « sortie mod 128 » — les bits de POIDS FAIBLE. Or
   Fisher-Yates ne publie que floor(K·u / 2^b), c'est-a-dire environ
   log2(80) = 6,3 bits de POIDS FORT.

     LES BITS DONT L'ATTAQUE A BESOIN SONT EXACTEMENT CEUX QUE
     L'ECHANTILLONNEUR JETTE.

   Combien en faudrait-il ? L'inversion coute 2^(64-t) par mot si l'on n'observe
   que t bits, et il faut nm mots :

       {'bits observés t':>16} {'coût par mot':>14} {'coût total (4 mots)':>21}""")
for t in (6, 16, 32, 48, 56, 60, 64):
    say(f"   {t:>16} {'2^%d' % (64-t):>14} {'2^%d' % (4*(64-t)):>21}")

say("""
   Il faudrait donc t >= 56 pour rester sous 2^32 — soit CINQUANTE-SIX des
   soixante-quatre bits. L'echantillonneur en publie SIX.

     CE N'EST PAS LE BROUILLEUR QUI PROTEGE LA PLATEFORME, C'EST
     L'ECHANTILLONNEUR. Et le §137 avait deja montre que le pas de vingt et un
     mots en est une seconde couche : la plateforme est protegee par la facon
     dont elle CONSOMME et PUBLIE son generateur, pas par le generateur.

   CONSIGNE DE COLLECTE, ET ELLE EST PRECISE. Tout observable exposant un mot
   COMPLET — ou seulement ses cinquante-six bits de poids fort — ferait tomber
   ces familles EN QUATRE TIRAGES. A chercher dans le flux du §139 : une graine
   affichee, un parametre d'animation, un identifiant derive, un horodatage
   sous-milliseconde. Le brouilleur, lui, ne protege rien.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

STAT = OK1 + OK3
ATT = len(LIG1) + len(CIBLES)

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h124.brouilleur_affine",
        "La sortie de xoshiro256**, xoroshiro128** et xoshiro256++ est AFFINE "
        "sur Z/2^64 — sortie = 5760·x + 9c avec c = (5x mod 2^64)>>57 pour les "
        "deux premieres — alors que les §119 et §123 mesurent dim L_d = 0 sur "
        "F2 pour d <= 3. Il s'ensuit qu'un mot de sortie COMPLET determine "
        "l'entree du brouilleur de facon unique, et que quatre mots suffisent a "
        "reconstituer les 256 bits d'etat de xoshiro256** (deux pour les 128 de "
        "xoroshiro128**), la mise a jour d'etat etant F2-lineaire",
        "nombre de verifications reussies : les formes affines sur 200 000 "
        "tirages chacune, puis les familles dont l'etat est reconstitue ET qui "
        "rejouent tous les mots observes ET predisent six mots supplementaires "
        "jamais montres",
        "une forme affine fausse manquerait ses 200 000 verifications ; un etat "
        "faux echouerait au rejeu, et un etat juste par hasard predirait six "
        "mots de 64 bits avec probabilite 2^-384",
        "conforme si les formes affines sont exactes et si les deux familles "
        "sont reconstituees et predisent 6/6", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(STAT), p=1.0,
        verdict="conforme" if STAT == ATT else "ECHEC",
        power_at=(f"{OK3}/{len(CIBLES)} familles reconstituees, avec DOUBLE temoin : "
                  f"rejeu de tous les mots observes ET prediction exacte de six "
                  f"mots de 64 bits jamais montres, soit 2^-384 par hasard"),
        notes=(f"LE DOSSIER TRAVAILLAIT DANS LE MAUVAIS ANNEAU. Les §119 et §123 "
               f"mesurent dim L_d = 0 sur F2 pour d <= 3 et le §141 en concluait "
               f"que xoshiro est hors de portee. C'est vrai sur F2 et FAUX sur "
               f"Z/2^64 : une rotation est une multiplication modulaire plus un "
               f"report explicite, rotl(y,7) = 128y + (y>>57) sans bits communs, "
               f"d'ou sortie = 5760·x + 9c. Le terme 9c ne resiste pas : 5760·x a "
               f"ses sept bits de poids faible nuls, donc sortie mod 128 = 9c mod "
               f"128 et 9 est inversible mod 128 — c est DETERMINE. Un mot "
               f"complet determine donc x ({uniq:,}/{NI:,} candidats uniques), et la "
               f"mise a jour etant F2-lineaire, quatre mots rendent les 256 bits "
               f"de xoshiro256**. CE QUI PROTEGE L'ARCHIVE N'EST DONC PAS LE "
               f"BROUILLEUR MAIS L'ECHANTILLONNEUR : l'inversion a besoin des "
               f"bits de POIDS FAIBLE et Fisher-Yates ne publie que 6,3 bits de "
               f"POIDS FORT. Il en faudrait 56. Consigne de collecte : tout "
               f"observable exposant un mot complet ferait tomber ces familles en "
               f"quatre tirages."))
    h = lab.holm()
    say(f"   consigne : h124.brouilleur_affine   {STAT}/{ATT}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
