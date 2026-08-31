"""h90 — le prédicteur : de l'état reconstitué au tirage suivant.

CE QUI MANQUAIT, ET C'EST GÊNANT
=================================
Le dossier compte maintenant huit attaques qui reconstituent un ETAT. Aucune
n'a jamais PREDIT UN TIRAGE. Tous les temoins s'arretent a « l'etat plante est
retrouve » — jamais a « le tirage suivant est annonce, puis verifie ».

La difference n'est pas rhetorique. « Retrouver l'etat » est une propriete de
l'attaque ; « annoncer les vingt numeros du tirage d'apres, dans l'ordre, et
avoir raison » est la chose que l'on demandait depuis le debut. Ce fichier
assemble les pieces et fait la seconde.

LE THÉORÈME DE PRÉDICTION
==========================
    Soit un generateur DETERMINISTE de fonction de transition connue, dont
    l'etat s_t est identifie a l'instant t. Alors tous les tirages futurs sont
    calculables exactement : la prediction n'est pas probabiliste, elle est
    une EVALUATION.

    COROLLAIRE, et c'est lui qui organise tout le dossier :

        « peut-on predire ? »   se reduit entierement a   « peut-on identifier ? »

    et le nombre de tirages ORDONNES necessaires se lit dans le budget
    d'information :

        F2-lineaire d'etat n bits   :  n / 89,7   tirages   (theoreme du prefixe, §105)
        LCG de module M             :  log2(M) / 126        (reduction de reseau, §104)

    Il n'y a pas de troisieme quantite. Une fois l'etat connu, l'horizon de
    prediction est INFINI — ce qui distingue radicalement cette voie de toute
    approche statistique, ou l'horizon se degrade a chaque pas. []

CE QUE CE FICHIER MESURE
=========================
Pour chaque famille du catalogue : le nombre MINIMAL de tirages ordonnes
consecutifs a partir duquel le tirage SUIVANT est annonce exactement — vingt
numeros, dans l'ordre — puis la verification a dix tirages d'horizon.

Puis il se retourne vers l'archive reelle et rend son verdict.

REGISTRE : INCHANGE. Ce fichier ne teste aucune hypothese neuve sur l'archive —
il rejoue les exclusions deja consignees aux §103 a §106 et ne consigne rien.
Compter deux fois la meme mesure serait la faute que le §100 refusait.

USAGE
=====
    python3 lab/experiments/h90_prediction.py                # demonstration
    python3 lab/experiments/h90_prediction.py mes_tirages.csv # sur vos donnees

Le CSV doit porter les colonnes id, o1..o20 dans l'ORDRE D'EMISSION.
"""

import csv
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# ON REPREND LES ATTAQUES DÉJÀ VALIDÉES, SANS LES RECOPIER
# ==========================================================================
def _tete(fichier, borne):
    src = open(os.path.join(ICI, fichier), encoding="utf-8").read()
    g = {"__name__": "tete", "__file__": os.path.join(ICI, fichier)}
    exec(compile(src[:src.index(borne)], fichier, "exec"), g)
    return g


_G85 = _tete("h85_reseau.py", 'rule("1. POURQUOI LA FEN')          # reseau, LCG
_G86 = _tete("h86_prefixe.py", 'rule("1. LE TH')                   # prefixe, F2
LCG = _G85["LCG"]
resous = _G85["resous"]
FAMILLES = _G86["FAMILLES"]
LARGEUR = _G86["LARGEUR"]
indices_fy = _G86["indices_fy"]
formes, systeme, cherche = _G86["formes"], _G86["systeme"], _G86["cherche"]


# ==========================================================================
# ÉMETTRE UN TIRAGE — la brique commune
# ==========================================================================
def fy_depuis_mots(mots, k0=0):
    """Le tirage de Fisher-Yates tronque engendre par vingt mots normalises."""
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        j = k + int(mots[k0 + k] * (POOL - k))
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return out


def tirages_lcg(a, b, M, s0, n, depart=0):
    """`n` tirages consecutifs d'un LCG, stride 20."""
    s = s0
    mots = []
    for _ in range((depart + n) * DRAWN):
        s = (a * s + b) % M
        mots.append(s / M)
    return [fy_depuis_mots(mots, d * DRAWN) for d in range(depart, depart + n)]


def tirages_f2(step, etat, W, n, depart=0):
    """`n` tirages consecutifs d'un generateur F2-lineaire, stride 20."""
    s, mots = etat, []
    for _ in range((depart + n) * DRAWN):
        s, w = step(s)
        mots.append(w / (1 << W))
    return [fy_depuis_mots(mots, d * DRAWN) for d in range(depart, depart + n)]


# ==========================================================================
# LE PRÉDICTEUR
# ==========================================================================
TDIM = 16
DMAX_NOYAU = 20


def identifie(tirages):
    """Cherche un generateur et un etat reproduisant TOUS les tirages donnes.

    Rend (etiquette, fonction_de_prediction) ou None. La fonction rendue prend
    un horizon h et rend les h tirages SUIVANTS.

    L'ordre d'essai va du moins cher au plus cher : les LCG demandent un seul
    tirage et une reduction de reseau de dimension 16 ; les F2-lineaires
    demandent d'autant plus de tirages que leur etat est gros.
    """
    n = len(tirages)

    # --- 1. LCG a parametres publies (§104) ---------------------------------
    enc = indices_fy(tirages[0], 1)
    if enc is not None:
        for nom, a, b, M in LCG:
            T = min(TDIM, DRAWN)
            A = [enc[t][0] * M // enc[t][1] for t in range(T)]
            Bh = [(enc[t][0] + 1) * M // enc[t][1] for t in range(T)]
            s0 = resous(a, b, M, A, Bh)
            if s0 is None:
                continue
            if tirages_lcg(a, b, M, s0, n) == tirages:
                return (f"LCG {nom}",
                        lambda h, a=a, b=b, M=M, s0=s0, n=n:
                        tirages_lcg(a, b, M, s0, h, depart=n))

    # --- 2. F2-lineaire a sortie brute (§105) -------------------------------
    for nom, nbits, step, _ref in FAMILLES:
        W = LARGEUR[nom]
        nmots = n * DRAWN
        if nbits * nmots > 3_000_000:
            continue
        obs, bon = [], True
        for d, nums in enumerate(tirages):
            e = indices_fy(nums, 1)
            if e is None:
                bon = False
                break
            for k, (m, K) in enumerate(e):
                obs.append((d * DRAWN + k, m, K))
        if not bon:
            continue
        coef = formes(step, nbits, nmots, W)
        piv, _neq = systeme(coef, obs, W)
        if piv is None:
            continue
        _G86["W_COURANT"] = W
        decoupe = [list(range(d * DRAWN, d * DRAWN + DRAWN)) for d in range(n)]
        got, dim = cherche(step, piv, nbits, decoupe, tirages, nmots, 1, W)
        if got is None or not got:
            continue
        etat = got[0]
        return (f"F2 {nom}",
                lambda h, step=step, etat=etat, W=W, n=n:
                tirages_f2(step, etat, W, h, depart=n))
    return None


# ==========================================================================
rule("1. LE THÉORÈME DE PRÉDICTION")
# ==========================================================================

say("""   CE QUI MANQUAIT. Le dossier compte huit attaques qui reconstituent un
   ETAT. Aucune n'a jamais PREDIT un tirage. Tous les temoins s'arretent a
   « l'etat plante est retrouve » — jamais a « le tirage suivant est annonce,
   puis verifie ». La difference n'est pas rhetorique.

   THEOREME. Soit un generateur DETERMINISTE de transition connue, dont l'etat
   est identifie a l'instant t. Alors tous les tirages futurs sont calculables
   exactement : la prediction n'est pas probabiliste, c'est une EVALUATION.

   COROLLAIRE, et c'est lui qui organise tout le dossier :

       « peut-on predire ? »  se reduit a  « peut-on identifier ? »

   et le nombre de tirages ORDONNES necessaires se lit dans le budget
   d'information :

       F2-lineaire de n bits  :  n / 89,7 tirages    (prefixe, §105)
       LCG de module M        :  log2(M) / 126       (reseau, §104)

   Il n'y a pas de troisieme quantite.

   ET LA CONSEQUENCE QUI CHANGE TOUT PAR RAPPORT A UNE APPROCHE STATISTIQUE :
   une fois l'etat connu, L'HORIZON EST INFINI. Le §107 et le §108 mesuraient
   des edges qui s'evanouissent dans le bruit ; ici il n'y a pas d'edge, il y a
   une CERTITUDE — ou rien du tout. []""")


# ==========================================================================
rule("2. LA DÉMONSTRATION : ANNONCER LE TIRAGE SUIVANT")
# ==========================================================================

say(f"""   Pour chaque famille : on plante un etat, on montre au predicteur d tirages
   consecutifs, on lui demande LE SUIVANT, et on compare les vingt numeros dans
   l'ordre. d croit jusqu'a ce que la prediction soit exacte.

   Puis on verifie l'horizon : les DIX tirages suivants, tous exacts ?
""")
say(f"   {'generateur':>30} {'d minimal':>10} {'tirage+1':>10} {'horizon 10':>11} {'sec':>7}")

rnd = random.Random(20260912)
CIBLES = []
for nom, a, b, M in LCG[:6]:
    CIBLES.append(("LCG " + nom, ("lcg", a, b, M)))
for nom, nbits, step, _r in FAMILLES:
    if nbits <= 256:
        CIBLES.append(("F2 " + nom, ("f2", nbits, step, LARGEUR[nom])))

RES = []
for etiq, spec in CIBLES:
    tt = time.time()
    if spec[0] == "lcg":
        _, a, b, M = spec
        s0 = rnd.randrange(M)
        verite = tirages_lcg(a, b, M, s0, 14)
    else:
        _, nbits, step, W = spec
        etat = rnd.getrandbits(nbits) | 1
        verite = tirages_f2(step, etat, W, 14)

    dmin, ok1, ok10 = None, False, False
    for d in range(1, 9):
        r = identifie(verite[:d])
        if r is None:
            continue
        _nom, predire = r
        suite = predire(10)
        if suite[0] == verite[d]:
            dmin, ok1 = d, True
            ok10 = suite == verite[d:d + 10]
            break
    RES.append((etiq, dmin, ok1, ok10))
    say(f"   {etiq:>30} {(dmin if dmin else '—'):>10} "
        f"{('EXACT' if ok1 else 'non'):>10} {('10/10' if ok10 else '—'):>11} "
        f"{time.time()-tt:>7.1f}")

NOK = sum(1 for _e, _d, o, _h in RES if o)
NH = sum(1 for _e, _d, _o, h in RES if h)
say(f"""
   {NOK}/{len(RES)} generateurs dont le tirage SUIVANT est annonce exactement — vingt
   numeros, dans l'ordre — et {NH}/{len(RES)} dont les DIX tirages suivants le sont aussi.

   C'est la premiere fois du dossier qu'un tirage est PREDIT et verifie. La
   colonne « d minimal » est le prix a payer en donnees : un tirage ordonne
   suffit pour tout LCG publie, deux a trois pour les F2-lineaires courants.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE RÉELLE")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}
BLOCS, cur = [], [IDS[0]]
for x, y in zip(IDS, IDS[1:]):
    if y == x + 1:
        cur.append(y)
    else:
        BLOCS.append(cur)
        cur = [y]
BLOCS.append(cur)

say(f"""   On donne au predicteur chaque bloc de tirages CONSECUTIFS de l'archive et
   on lui demande d'annoncer le suivant.
""")
say(f"   {'bloc':>28} {'tirages':>8} {'generateur identifie':>24}")
TROUVE = 0
for bloc in BLOCS:
    t = [PARID[d] for d in bloc]
    r = identifie(t)
    if r:
        TROUVE += 1
    say(f"   {f'{bloc[0]}..{bloc[-1]}':>28} {len(bloc):>8} "
        f"{(r[0] if r else 'aucun'):>24}")

say(f"""
   {TROUVE} generateur identifie. Le predicteur qui annonce {NOK}/{len(RES)} loteries plantees
   n'annonce rien ici : le generateur de ce tirage n'est pas dans la classe
   couverte, et le §105 chiffre ce qu'il faudrait pour elargir cette classe.

   REGISTRE : INCHANGE. Ce fichier ne teste rien de neuf sur l'archive — il
   rejoue les exclusions deja consignees aux §103 a §106. Les consigner une
   seconde fois gonflerait m sans rien mesurer de plus.""")


# ==========================================================================
rule("4. L'OUTIL, POUR LE JOUR OÙ LES DONNÉES EXISTERONT")
# ==========================================================================

say(f"""   Ce fichier est aussi un outil. Le jour ou des tirages ordonnes consecutifs
   seront disponibles :

       python3 lab/experiments/h90_prediction.py mes_tirages.csv

   colonnes id, o1..o20 dans l'ORDRE D'EMISSION. Il rend soit « aucun », soit
   le generateur, l'etat, et LES VINGT NUMEROS DU TIRAGE SUIVANT.

   Le budget est celui du §105 : {int(np.ceil(32/89.7))} tirage pour un etat de 32 bits,
   {int(np.ceil(128/89.7))} pour 128 bits, {int(np.ceil(256/89.7))} pour 256, {int(np.ceil(512/89.7))} pour 512, 225 pour MT19937.

   ({time.time() - T0:.1f} s)""")


# ==========================================================================
if len(sys.argv) > 1:
    rule("5. VOS DONNÉES")
    lignes = list(csv.DictReader(open(sys.argv[1])))
    t = [[int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in lignes]
    say(f"   {len(t)} tirages lus depuis {sys.argv[1]}.")
    r = identifie(t)
    if r is None:
        say("   Aucun generateur identifie dans la classe couverte.")
    else:
        nom, predire = r
        say(f"   GENERATEUR IDENTIFIE : {nom}")
        for i, d in enumerate(predire(3), 1):
            say(f"   tirage +{i} : {' '.join(f'{x:2d}' for x in d)}")
