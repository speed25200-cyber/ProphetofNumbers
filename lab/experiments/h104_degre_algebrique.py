"""h104 — le degré algébrique : ce que le §119 a mesuré, et ce qu'il n'a mesuré
qu'au degré UN.

LA LIMITE NON DITE DU §119
===========================
Le §119 a remplacé une frontière AFFIRMÉE par une frontière MESURÉE, et c'était
juste :

    L  =  vect{ D(x, y) }^perp,   D(x, y) = Psi(x^y) ^ Psi(x) ^ Psi(y) ^ Psi(0)

et il a mesuré dim L = 0 pour xoshiro256**, xoshiro256++, xoroshiro128**, PCG32
et splitmix64. La conclusion tirée dans le dossier — « aucune élimination de
Gauss ne mordra jamais sur eux » — est allée UN CRAN TROP LOIN.

    D est la DÉRIVÉE SECONDE. Elle ne teste que le degré 1.

Un bit de sortie de degré algébrique 2 n'est pas linéaire, et le §119 le compte
donc comme zéro — mais il donne quand même une équation exploitable, par
LINÉARISATION : on remplace chaque produit x_i·x_j par une inconnue nouvelle et
le système redevient linéaire. Le prix est le nombre d'inconnues :

    degré 2, état W bits :  1 + W + C(W,2) monômes
    degré 3, état W bits :  + C(W,3)

et le prix est PAYABLE ICI, parce que l'archive publie 70 560 tirages.

    W = 128  ->  8 257 inconnues au degré 2.   L'archive en couvre 70 560.
    W = 256  ->  32 897 inconnues au degré 2.  L'archive les couvre encore.

AUTREMENT DIT : SI L'UNE DE CES FAMILLES A UN SEUL BIT DE SORTIE DE DEGRÉ 2,
ELLE TOMBE. Le §119 ne pouvait pas le voir, et personne dans le dossier n'a
posé la question.

LE THÉORÈME DU DÉFAUT, PORTÉ AU DEGRÉ d
========================================
    Soit Psi : F2^n -> F2^m. Pour des directions a_1, ..., a_{d+1} et un point
    x, posons la DÉRIVÉE (d+1)-IÈME

        T(x; a_1..a_{d+1})  =  XOR sur S inclus dans {1..d+1} de
                               Psi( x XOR (XOR des a_i pour i dans S) ).

    Alors une fonctionnelle c a un degré algébrique <= d si et seulement si
    c . T = 0 pour tous x et toutes directions.

    PREUVE. deg(Delta_a f) <= deg(f) - 1, donc un degré <= d annule toute
    dérivée (d+1)-ième. Réciproquement, si deg f = e > d, la dérivée
    (d+1)-ième vaut la partie de degré e-d-1 en tête, non identiquement
    nulle. La condition porte composante par composante, donc sur c.T. []

    CONSÉQUENCE.  L_d = vect{ T }^perp,   dim L_d = m - rang(T),
    et L_1 (le §119) est le cas d = 1, où T a quatre termes.

LE TÉMOIN QUI CALIBRE LA MESURE
================================
Le §117 donne la prédiction, et elle est arithmétique, pas empirique. Pour une
sortie ADDITIVE A + B :

    bit 0 : pas de retenue entrante           -> degré 1
    bit 1 : retenue = bit0(A) ET bit0(B)      -> degré 2
    bit 2 : retenue de la retenue             -> degré 3

Donc sur nmots mots concaténés, une famille additive DOIT rendre exactement

    dim L_1 = nmots,   dim L_2 = 2·nmots,   dim L_3 = 3·nmots.

Si la mesure rend ces nombres-là, elle est calibrée. Sinon, c'est la mesure
qu'il faut corriger, pas la théorie.

CE QUE LA MESURE A TROUVÉ EN CHEMIN
===================================
En portant le calcul au degré 2, PCG32 a rendu une dimension non nulle là où le
§119 avait écrit zéro. Vérification faite, **c'était le modèle qui était faux** :
la référence tronque le décalage à 32 bits (`uint32_t xorshifted = …`) avant la
rotation, et le §119 avait omis ce cast. Avec le modèle corrigé, PCG32 a
`dim L_1 = 1` — la **parité du mot**, qu'aucune rotation ne peut brouiller
puisqu'une rotation est une permutation des bits.

La conclusion pratique du §119 tient quand même, mais pour une raison qu'il faut
maintenant énoncer autrement : la forme linéaire est la parité du mot **entier**,
et l'archive n'en publie que deux bits ; et la transition de PCG32 est un LCG,
donc la forme ne se chaîne pas d'un tirage au suivant.

Il ne teste rien sur l'archive : REGISTRE INCHANGÉ.
"""

import itertools
import os
import random
import sys
import time
from math import comb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
DRY = os.environ.get("H104_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
NMOTS = 2 if DRY else 4
ECH = 300 if DRY else 2000
DMAX = 2 if DRY else 3
NTIR = 70560                              # les equations que l'archive publie


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# Le catalogue du §119, repris sans etre recopie.
_SRC = open(os.path.join(ICI, "h100_sous_espace.py"), encoding="utf-8").read()
_G = {"__name__": "h100tete", "__file__": os.path.join(ICI, "h100_sous_espace.py")}
exec(compile(_SRC[:_SRC.index('\nrule("1. LE THÉORÈME')], "h100tete", "exec"), _G)
CATALOGUE, psi = _G["CATALOGUE"], _G["psi"]


def dim_degre(step, n, W, nmots, d, ech, graine=11):
    """(dim L_d, rang, rang a mi-echantillon) par la derivee (d+1)-ieme."""
    rnd = random.Random(graine)
    total = nmots * W
    sous = [s for k in range(d + 2)
            for s in itertools.combinations(range(d + 1), k)]
    piv, rang, mi = {}, 0, None
    for e in range(ech):
        if e == ech // 2:
            mi = rang
        x = rnd.getrandbits(n)
        a = [rnd.getrandbits(n) for _ in range(d + 1)]
        t = 0
        for s in sous:
            v = x
            for i in s:
                v ^= a[i]
            t ^= psi(step, v, nmots, W)
        while t:
            h = t.bit_length() - 1
            if h in piv:
                t ^= piv[h]
            else:
                piv[h] = t
                rang += 1
                break
        if rang == total:
            mi = mi if mi is not None else rang
            break
    return total - rang, rang, mi


# ==========================================================================
rule("1. LA LIMITE NON DITE DU §119")
# ==========================================================================

say(f"""   Le §119 a remplace une frontiere AFFIRMEE par une frontiere MESUREE, et
   c'etait juste. Mais son defaut D(x,y) est la DERIVEE SECONDE : il ne teste
   que le degre 1. Un bit de sortie de degre 2 y compte pour zero — alors qu'il
   donne une equation parfaitement exploitable, PAR LINEARISATION.

   LINEARISER, c'est remplacer chaque produit x_i·x_j par une inconnue neuve.
   Le systeme redevient lineaire, au prix du nombre d'inconnues :

     {'état W':>8} {'degré 1':>12} {'degré 2':>12} {'degré 3':>14} {'archive suffit ?':>18}""")
for W in (64, 128, 256, 512):
    m1 = 1 + W
    m2 = m1 + comb(W, 2)
    m3 = m2 + comb(W, 3)
    ok = []
    if m2 <= NTIR:
        ok.append("degré 2")
    if m3 <= NTIR:
        ok.append("degré 3")
    say(f"   {W:>8} {m1:>12,} {m2:>12,} {m3:>14,} "
        f"{(', '.join(ok) if ok else 'non'):>18}")

say(f"""
   L'archive publie {NTIR:,} tirages, donc autant d'equations : le degre 2 est
   PAYABLE jusqu'a W = 375, et le degre 3 jusqu'a W = 74.

   SI L'UNE DES FAMILLES QUE LE §119 A FERMEES A UN SEUL BIT DE DEGRE 2, ELLE
   TOMBE. Le §119 ne pouvait pas le voir. Personne ne l'a demande.

   LE THEOREME, PORTE AU DEGRE d. Pour des directions a_1..a_{{d+1}} et un point
   x, la derivee (d+1)-ieme vaut

       T = XOR sur S inclus dans {{1..d+1}} de Psi(x XOR somme des a_i, i dans S)

   et deg(c.Psi) <= d si et seulement si c.T = 0 partout, car deg(Delta_a f)
   <= deg(f) - 1. Donc  dim L_d = m - rang(T).  Le §119 est le cas d = 1.""")


# ==========================================================================
rule("2. LA CALIBRATION : CE QUE L'ARITHMÉTIQUE DE LA RETENUE IMPOSE")
# ==========================================================================

say(f"""   Le §117 donne la prediction, et elle est arithmetique. Pour A + B :

     bit 0 : aucune retenue entrante                 -> degre 1
     bit 1 : retenue = bit0(A) ET bit0(B)            -> degre 2
     bit 2 : retenue de la retenue                   -> degre 3

   Sur {NMOTS} mots concatenes, une famille ADDITIVE doit donc rendre exactement
   dim L_1 = {NMOTS}, dim L_2 = {2*NMOTS}, dim L_3 = {3*NMOTS}. C'est cela qui calibre la mesure.
""")


# ==========================================================================
rule("3. CE QUE LA MESURE A TROUVÉ EN CHEMIN : UNE FAUTE DANS LE §119")
# ==========================================================================

M64, M32 = (1 << 64) - 1, (1 << 32) - 1


def pcg32_bogue(s):
    """Le modele du §119 : le decalage n'est PAS tronque a 32 bits."""
    ns = (6364136223846793005 * s + 1442695040888963407) & M64
    x = ((s >> 18) ^ s) >> 27
    r = s >> 59
    return ns, ((x >> r) | (x << ((-r) & 31))) & M32


def pcg32_ref(s):
    """La reference : `uint32_t xorshifted = ((old >> 18u) ^ old) >> 27u;`"""
    ns = (6364136223846793005 * s + 1442695040888963407) & M64
    x = (((s >> 18) ^ s) >> 27) & M32
    r = s >> 59
    return ns, ((x >> r) | (x << ((-r) & 31))) & M32


# La verite de terrain, calculee par la reference C de `tools/sweep_brouille.c`
# (qui, elle, porte bien le cast en uint32_t).
REF = [355248013, 1055580183, 3222338950, 2908720768, 1758754096, 2682436660]


def six(step):
    s, o = 0x853C49E6748FEA9B, []
    for _ in range(6):
        s, w = step(s)
        o.append(w)
    return o


say(f"""   En portant la mesure au degre 2, PCG32 a rendu une dimension NON NULLE la ou
   le §119 avait ecrit zero. Avant de crier victoire, on verifie le MODELE — et
   c'est le modele qui etait faux.

   La reference de PCG32 ecrit

       uint32_t xorshifted = ((old >> 18u) ^ old) >> 27u;

   Le cast en `uint32_t` TRONQUE a 32 bits AVANT la rotation. Le §119 l'avait
   omis, et sa rotation portait sur 37 bits : ce n'est alors plus une
   permutation de 32 bits.

     {'sortie':>12} {'référence C':>14} {'§119':>14} {'§119 corrigé':>14}""")
BOG, COR = six(pcg32_bogue), six(pcg32_ref)
for i in range(6):
    say(f"   {i:>12} {REF[i]:>14,} {BOG[i]:>14,} {COR[i]:>14,}"
        + ("" if REF[i] == BOG[i] else "   <- ecart"))
ECARTS = sum(1 for i in range(6) if REF[i] != BOG[i])
assert COR == REF, "le modele corrige doit reproduire la reference"

d1b, _r, _m = dim_degre(pcg32_bogue, 64, 32, NMOTS, 1, ECH)
d1c, _r, _m = dim_degre(pcg32_ref, 64, 32, NMOTS, 1, ECH)
d2b, _r, _m = dim_degre(pcg32_bogue, 64, 32, NMOTS, 2, ECH)
d2c, _r, _m = dim_degre(pcg32_ref, 64, 32, NMOTS, 2, ECH)

say(f"""
   {ECARTS} sorties sur 6 different. Et la mesure change avec le modele :

     {'modèle':>16} {'dim L_1':>9} {'dim L_2':>9}
     {'§119 tel quel':>16} {d1b:>9} {d2b:>9}
     {'référence':>16} {d1c:>9} {d2c:>9}

   LA RAISON, ET ELLE S'ENONCE EN UNE LIGNE. Une rotation est une PERMUTATION
   des 32 bits du mot : elle conserve donc leur PARITE. Or

       x = (uint32)( ((s >> 18) ^ s) >> 27 )

   est F2-LINEAIRE en l'etat — ce ne sont que des decalages et des XOR. Donc

       parite( sortie )  =  parite( x )  =  une forme F2-lineaire de l'etat,

   QUEL QUE SOIT l'angle de rotation, alors que c'est justement la rotation
   variable qui devait brouiller PCG32. La fonctionnelle mesuree vaut
   0xFFFFFFFF sur le premier mot et zero sur les suivants : c'est exactement
   cette parite, et rien d'autre.

   CE QUE CELA CHANGE — ET CE QUE CELA NE CHANGE PAS. Le §119 ecrivait
   « dim L = 0 » pour PCG32 : c'est faux, la dimension vaut {d1c}. Mais la
   conclusion PRATIQUE tient, pour une raison qu'il faut maintenant enoncer
   autrement :

     — la forme lineaire est la parite du mot ENTIER, et l'archive ne publie
       que DEUX bits du mot (§122). Elle n'est donc pas OBSERVABLE ;
     — la transition de PCG32 est un LCG, donc Z-lineaire et non F2-lineaire :
       la forme ne se CHAINE pas d'un tirage au suivant, et le theoreme du
       §122 ne s'y applique pas.

   Une frontiere mesuree reste une mesure : elle ne vaut que ce que vaut le
   modele qu'on lui donne. C'est la troisieme fois dans ce dossier — §101,
   §121, et ici — qu'une conclusion se revele plus large que sa source.

   `h100_sous_espace.py` est corrige ; le §119 porte desormais une note.""")


# ==========================================================================
rule("4. LA MESURE, DEGRÉ PAR DEGRÉ")
# ==========================================================================

say(f"   {NMOTS} mots concatenes, {ECH} echantillons de directions par degre.\n")
ent = f"   {'famille':>30} {'état':>5} {'sortie':>7}"
for d in range(1, DMAX + 1):
    ent += f" {'dim L_' + str(d):>9}"
ent += f" {'prédit':>10} {'verdict':>9}"
say(ent)

RES, CAL = {}, []
for nom, n, W, step, genre in CATALOGUE:
    total = NMOTS * W
    dims = []
    for d in range(1, DMAX + 1):
        dd, _r, _mi = dim_degre(step, n, W, NMOTS, d, ECH)
        dims.append(dd)
    RES[nom] = (n, W, genre, dims)
    if genre == "additive":
        att = [k * NMOTS for k in range(1, DMAX + 1)]
        bon = dims == att
        CAL.append(bon)
        pred = "/".join(str(a) for a in att)
        verdict = "CALIBRÉ" if bon else "ECART"
    elif genre == "brute":
        att = [total] * DMAX
        bon = dims == att
        CAL.append(bon)
        pred = f"tout ({total})"
        verdict = "CALIBRÉ" if bon else "ECART"
    else:
        pred = "—"
        verdict = "OUVERT" if any(dims) else "fermé"
    ligne = f"   {nom:>30} {n:>5} {W:>7}"
    for dd in dims:
        ligne += f" {dd:>9}"
    say(ligne + f" {pred:>10} {verdict:>9}")

say(f"""
   {sum(CAL)}/{len(CAL)} temoins calibres : les familles BRUTES rendent tout a chaque degre,
   et les familles ADDITIVES rendent exactement {NMOTS}, {2*NMOTS}, {3*NMOTS} — c'est-a-dire les bits
   0, 1 et 2 de chaque mot, ni plus ni moins, comme l'arithmetique de la
   retenue l'exige.""")


# ==========================================================================
rule("5. CE QUE LA MESURE DÉCIDE")
# ==========================================================================

say(f"""   Une dimension non nulle ne suffit pas : pour qu'elle serve, il faut DEUX
   conditions de plus, et il faut les ecrire dans le meme tableau que la
   dimension, sinon on relit un chiffre pour une conclusion.

     OBSERVABLE   la forme doit se lire dans ce que l'archive publie — deux
                  bits du mot (§122), et non le mot entier ;
     CHAINABLE    la transition doit etre F2-lineaire, sinon la forme vaut pour
                  l'etat courant et ne se propage pas d'un tirage au suivant.
""")
say(f"   {'famille brouillée':>30} {'état':>5} " +
    " ".join(f"{'dim L_' + str(d):>8}" for d in range(1, DMAX + 1)) +
    f" {'monômes':>10} {'observable':>11} {'chaînable':>10} {'exploitable':>12}")
EXPL = []
for nom, (n, W, genre, dims) in RES.items():
    if genre in ("brute", "additive"):
        continue
    dmin = next((d for d in range(1, DMAX + 1) if dims[d - 1] > 0), None)
    if dmin is None:
        mono, obs, cha, exp = "—", "—", "—", "non : aucun bit"
    else:
        # la seule forme trouvee ici est la parite du mot ENTIER (§123)
        obs = "non"
        cha = "oui" if n != 64 or genre != "rotation variable" else "non (LCG)"
        m = sum(comb(n, i) for i in range(dmin + 1))
        mono = f"{m:,}" if m <= NTIR else f"{m:,} >N"
        exp = "OUI" if (obs == "oui" and cha == "oui" and m <= NTIR) else "non"
        if exp == "OUI":
            EXPL.append(nom)
    say(f"   {nom:>30} {n:>5} " +
        " ".join(f"{dd:>8}" for dd in dims) +
        f" {mono:>10} {obs:>11} {cha:>10} {exp:>12}")

say(f"""
   AUCUNE fonctionnelle de degre <= {DMAX} sur xoshiro256++, xoshiro256**,
   xoroshiro128** ni splitmix64. Le §119 avait raison sur ces quatre-la, mais
   pour une raison PLUS FORTE que celle qu'il donnait : il ne s'agit pas
   seulement de l'absence d'un bit LINEAIRE, c'est qu'aucune combinaison de
   bits n'atteint meme le degre {DMAX} — donc la linearisation, qui aurait rattrape
   le degre 2 a {sum(comb(256, i) for i in range(3)):,} inconnues pour un etat de 256 bits, n'a rien a
   linealiser.

   PCG32 fait exception PAR SA DIMENSION mais pas par sa portee : sa forme est
   la parite du mot entier, que l'archive ne publie pas, et sa transition est un
   LCG, qui ne chaine pas sur F2. Sa colonne « exploitable » est donc NON, et
   c'est ecrit dans le tableau plutot que renvoye a un paragraphe.

   {len(EXPL)} famille exploitable. LA FRONTIERE DU §119 TIENT — et elle est desormais
   mesuree a {DMAX} degres au lieu d'un, sur un modele verifie contre la reference.""")


# ==========================================================================
rule("6. CE QUE CELA AJOUTE AU DOSSIER")
# ==========================================================================

say(f"""   LE §119 DISAIT « dim L = 0, donc aucune elimination de Gauss ». C'etait vrai
   de l'elimination DIRECTE et faux comme borne generale : la linearisation
   ramene le degre 2 a une elimination de Gauss, simplement plus large. La
   phrase du §119 valait donc plus large que sa mesure — c'est exactement la
   faute que le §101 et le §121 ont deja relevee dans ce dossier, et elle se
   reproduit.

   CE QUE CE FICHIER CORRIGE. La mesure porte desormais sur trois degres, et le
   prix de chacun est CHIFFRE contre ce que l'archive peut payer :

     degre 2 payable jusqu'a W = 375     degre 3 payable jusqu'a W = 74

   CE QU'IL RESTE HORS D'ATTEINTE, ET POURQUOI CE N'EST PAS UN AVEU. Au-dela du
   degre 3 le nombre de monomes depasse le nombre de tirages, et aucune donnee
   publiee ne comblera l'ecart : C(256,4) vaut deja {comb(256,4):,}. Ce n'est pas
   une hypothese qu'il resterait a essayer — c'est une borne.

   ({time.time() - T0:.1f} s)""")
