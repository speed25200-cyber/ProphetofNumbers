"""h110 — la chaîne complète, et le poste de réception.

CE QUE CE FICHIER EST
======================
Les §105 à §128 disent CE QUI EST RECONSTITUABLE SOUS QUELLES HYPOTHÈSES. Ils ne
disent nulle part, en un seul endroit exécutable : voici la machine, elle prend
des tirages en entrée et elle rend l'état puis les tirages suivants.

Ce fichier est cette machine, et il la valide de bout en bout sur un JUMEAU
NUMÉRIQUE du plateau — un simulateur qui reproduit tous les invariants mesurés
de l'archive réelle.

    LE JUMEAU. Fisher-Yates par troncature sur 80 ; le bonus par un mot d'indice
    sur K = 20 ; le BOOST par une table de 80 secteurs (39, 2, 19, 12, 4, 2, 2)
    — la grille du §125 — dont le ×1,5 est fondu dans le seau « 1 » comme dans
    l'archive ; pas de 22 mots par tirage.

    LA CHAÎNE. observer -> bits exacts par le théorème du préfixe -> système F2
    -> pivot de Gauss -> état -> REJOUER pour vérifier -> prédire.

CE QU'IL MESURE, ET C'EST LE CHIFFRE QUE LE DOSSIER DEVAIT DONNER
=================================================================
Combien de tirages faut-il, par famille et par régime d'observation, pour
reconstituer l'état EXACTEMENT et prédire le tirage suivant SANS ERREUR ?

    régime O   l'ORDRE d'émission est connu   (une vidéo)
    régime T+  trié, bonus + boost exact       (l'archive, §125)
    régime T   trié, bonus seul                (l'archive avant le §125)

Le rapport entre O et T est ce que vaut UNE VIDÉO, chiffré en tirages.

LE POSTE DE RÉCEPTION
======================
`reconstituer(...)` prend exactement ce qu'une vidéo de tirage donne — les vingt
numéros DANS L'ORDRE, le bonus, le boost — et rend l'état ou l'incompatibilité.
Il est écrit pour être appelé le jour où la donnée arrive, pas pour la
démonstration.

Il ne teste rien sur l'archive : REGISTRE INCHANGÉ.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H110_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
POOL, DRAWN = 80, 20
STRIDE = 22                               # 20 Fisher-Yates + 1 bonus + 1 boost
KB = 20
# La grille du §125, dans l'ordre des multiplicateurs. Le ×1,5 (2 secteurs) est
# fondu dans le seau « 1 » de l'archive, exactement comme la plateforme le fait.
SECTEURS = [("1", 39), ("1", 2), ("2", 19), ("3", 12), ("4", 4), ("5", 2), ("10", 2)]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# Le catalogue et l'algebre du §68/§86, repris sans etre recopies.
_SRC = open(os.path.join(ICI, "h61_familles_etendues.py"), encoding="utf-8").read()
_G = {"__name__": "h61tete", "__file__": os.path.join(ICI, "h61_familles_etendues.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LES FAMILLES')], "h61tete", "exec"), _G)
FAMILLES = {n: (nb, st) for n, nb, st, _r in _G["OLD"] + _G["NEW"]}
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]
LARGEUR = {"xorshift32": 32, "xorshift64": 64, "xorshift96": 32, "xorshift128": 32,
           "taus88": 32, "xoroshiro128 (brut)": 64, "xoshiro128 (brut)": 32,
           "xoshiro256 (brut)": 64, "LFSR113": 32, "WELL512a": 32}


# ==========================================================================
# LE JUMEAU NUMÉRIQUE
# ==========================================================================
def table_boost():
    """La table de 80 secteurs -> valeur affichee, grille du §125."""
    t = []
    for val, k in SECTEURS:
        t += [val] * k
    assert len(t) == POOL
    return t


TBOOST = table_boost()
BORNES = {}
_a = 0
for _v, _k in SECTEURS:
    BORNES.setdefault(_v, [_a, _a + _k])
    BORNES[_v][1] = _a + _k                # le seau « 1 » couvre 0..40
    _a += _k


def jumeau(step, etat, ndraws, W):
    """Un tirage du plateau simule. Rend, par tirage :
       (numeros dans l'ORDRE, rang du bonus, numero du bonus, boost affiche)."""
    s, out = etat, []
    for _ in range(ndraws):
        arr = list(range(1, POOL + 1))
        ordre = []
        for k in range(DRAWN):
            s, w = step(s)
            j = k + ((w * (POOL - k)) >> W)
            arr[k], arr[j] = arr[j], arr[k]
            ordre.append(arr[k])
        s, w = step(s)
        rang = (w * KB) >> W
        s, w = step(s)
        sect = (w * POOL) >> W
        out.append((ordre, rang, sorted(ordre)[rang], TBOOST[sect]))
    return out, s


# ==========================================================================
# LA CHAÎNE : OBSERVATIONS -> ÉQUATIONS -> ÉTAT
# ==========================================================================
def prefixe_int(a, b, K, W):
    """(longueur, valeur) du prefixe binaire determine par u dans [a/K, b/K)."""
    j, val = 0, 0
    for jj in range(1, W + 1):
        lo = (a << jj) // K
        if lo != ((b << jj) - 1) // K:
            break
        j, val = jj, lo
    return j, val


def indices_fy_ordre(ordre):
    """L'indice de Fisher-Yates a chaque pas, depuis l'ORDRE d'emission."""
    arr = list(range(1, POOL + 1))
    out = []
    for k, v in enumerate(ordre):
        j = arr.index(v)
        if j < k:
            return None
        out.append((k, j - k, j - k + 1, POOL - k))
        arr[k], arr[j] = arr[j], arr[k]
    return out


def observations(tir, regime):
    """Les intervalles exacts d'un tirage, sous le regime demande.
       Rend une liste de (indice du mot dans le tirage, a, b, K)."""
    ordre, rang, _bon, boost = tir
    obs = []
    if regime == "O":
        fy = indices_fy_ordre(ordre)
        if fy is None:
            return None
        obs += fy
    if regime in ("O", "T+", "T"):
        obs.append((DRAWN, rang, rang + 1, KB))
    if regime in ("O", "T+"):
        a, b = BORNES[boost]
        obs.append((DRAWN + 1, a, b, POOL))
    return obs


def systeme(coef, obs, W):
    """Echelonne. Rend (pivots, nb d'equations) ou (None, n) si incompatible."""
    piv, neq = {}, 0
    for k, a, b, K in obs:
        j, val = prefixe_int(a, b, K, W)
        for r in range(j):
            bit = (val >> (j - 1 - r)) & 1
            if not add_eq(piv, coef[k][W - 1 - r], bit, []):
                return None, neq
            neq += 1
    return piv, neq


def formes(step, nbits, nwords, W):
    """coef[k][b] : masque F2 de la forme lineaire du bit b du mot k."""
    coef = [[0] * W for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            ck = coef[k]
            while w:
                b = (w & -w).bit_length() - 1
                ck[b] |= bit
                w &= w - 1
    return coef


def reconstituer(nom, tirages, regime, dmax=None, kcap=20):
    """LE POSTE DE RECEPTION.

    Prend des tirages sous la forme qu'une VIDEO donnerait et rend
    (etat, tirages consommes, equations, statut).

    LE RANG NE SUFFIT PAS COMME CRITERE, et le §106 l'a appris a ses depens :
    taus88 sature a 88 bits sur 96, LFSR113 a 113 sur 128 — leurs bits morts ne
    seront JAMAIS determines. On prend donc une solution particuliere, on
    parcourt le noyau, ET ON REJOUE. Le rejeu est le seul juge.

    Le systeme est tenu INCREMENTALEMENT : `add_eq` n'ecrase jamais un pivot
    existant, donc ajouter les equations d'un tirage a l'echelonnement deja
    fait donne le meme resultat que tout recalculer, en O(D) au lieu de O(D²).
    """
    nbits, step = FAMILLES[nom]
    W = LARGEUR[nom]
    D = len(tirages) if dmax is None else min(dmax, len(tirages))
    coef = formes(step, nbits, D * STRIDE, W)
    piv, neq, rang_max, rang_essaye = {}, 0, 0, -1
    for d, tir in enumerate(tirages[:D]):
        o = observations(tir, regime)
        if o is None:
            return None, d, neq, "ordre impossible"
        for k, a, b, K in o:
            j, val = prefixe_int(a, b, K, W)
            for r in range(j):
                bit = (val >> (j - 1 - r)) & 1
                if not add_eq(piv, coef[d * STRIDE + k][W - 1 - r], bit, []):
                    return None, d + 1, neq, "incompatible"
                neq += 1
        rang_max = max(rang_max, len(piv))
        # On ne parcourt le noyau qu'une fois par NIVEAU DE RANG : tant que le
        # rang monte, l'enumeration serait refaite pour rien ; quand il
        # plafonne, c'est justement le moment de la faire.
        if nbits - len(piv) > kcap or len(piv) == rang_essaye:
            continue
        rang_essaye = len(piv)
        sol, _libres = back_substitute(piv, nbits)
        base = kernel_basis(piv, nbits)
        for g in range(1 << len(base)):
            cand = sol
            gg, i = g, 0
            while gg:
                if gg & 1:
                    cand ^= base[i]
                gg >>= 1
                i += 1
            if cand == 0:
                continue
            rejoue, _ = jumeau(step, cand, d + 1, W)
            if rejoue == tirages[:d + 1]:
                return cand, d + 1, neq, "resolu"
    return None, D, neq, f"sous-determine (rang {rang_max} sur {nbits})"


# ==========================================================================
rule("1. LE JUMEAU NUMÉRIQUE, ET CE QU'IL REPRODUIT")
# ==========================================================================

ND = 400 if DRY else 4000
_nb, _st = FAMILLES["WELL512a"]
TIR, _ = jumeau(_st, 0x1234567 | (1 << (_nb - 1)), ND, LARGEUR["WELL512a"])

boosts = [t[3] for t in TIR]
vals, cnt = np.unique(boosts, return_counts=True)
attendu = {v: sum(k for vv, k in SECTEURS if vv == v) / POOL for v in vals}
khi = sum((c - ND * attendu[v]) ** 2 / (ND * attendu[v]) for v, c in zip(vals, cnt))
rangs = np.array([t[1] for t in TIR])
khir = float(((np.bincount(rangs, minlength=KB) - ND / KB) ** 2 / (ND / KB)).sum())
tous_distincts = all(len(set(t[0])) == DRAWN for t in TIR)
bonus_dedans = all(t[2] in t[0] for t in TIR)

say(f"""   Le jumeau reproduit le plateau tel que le dossier l'a mesure :

     Fisher-Yates par TRONCATURE sur 80          §105
     le bonus par un mot d'indice sur K = 20     §106
     le BOOST par une table de 80 secteurs       §125
       (39, 2, 19, 12, 4, 2, 2), le ×1,5 fondu dans le seau « 1 »
     pas de {STRIDE} mots par tirage                    §113, §115

   {'invariant':>38} {'attendu':>14} {'jumeau':>14}""")
say(f"   {'20 numeros distincts par tirage':>38} {'oui':>14} {('oui' if tous_distincts else 'NON'):>14}")
_LIB = "le bonus est l'un des 20"
say(f"   {_LIB:>38} {'oui':>14} {('oui' if bonus_dedans else 'NON'):>14}")
say(f"   {'loi du boost, khi2 (5 ddl)':>38} {'~5':>14} {khi:>14.2f}")
say(f"   {'uniformite du rang, khi2 (19 ddl)':>38} {'~19':>14} {khir:>14.2f}")
for v, c in zip(vals, cnt):
    say(f"   {'boost ×' + str(v):>38} {attendu[v]:>14.4f} {c/ND:>14.4f}")


# ==========================================================================
rule("2. LA CHAÎNE, DE BOUT EN BOUT")
# ==========================================================================

say(f"""   observer -> bits exacts (theoreme du prefixe) -> systeme F2 -> pivot de
   Gauss -> etat -> REJOUER pour verifier -> predire.

   Le rejeu n'est pas facultatif : le §111 avait consigne 15 104 « etats
   compatibles » dont aucun ne reproduisait le tirage, faute de rejouer.

   {'famille':>22} {'état':>6} {'régime':>7} {'tirages':>8} {'équations':>10} {'rejeu exact':>28} {'prédit':>8}""")

CIBLES = ["xorshift128", "taus88", "LFSR113", "WELL512a"]
REGIMES = [("O", 40), ("T+", 400 if not DRY else 60), ("T", 500 if not DRY else 60)]
BILAN = {}
for nom in CIBLES:
    nbits, step = FAMILLES[nom]
    W = LARGEUR[nom]
    vrai = 0
    g = np.random.default_rng(20260903 + nbits)
    while vrai == 0:
        vrai = int(g.integers(0, 1 << 32)) | (1 << (nbits - 1))
    for regime, plafond in REGIMES:
        tirages, apres = jumeau(step, vrai, plafond + 3, W)
        etat, d, neq, statut = reconstituer(nom, tirages, regime, dmax=plafond)
        exact = etat is not None
        pred = "—"
        if exact:
            # on rejoue depuis l'etat trouve et on annonce les 3 tirages suivants
            suite, _ = jumeau(step, etat, d + 3, W)
            pred = "3/3" if suite[d:d + 3] == tirages[d:d + 3] else "ECHEC"
        BILAN[(nom, regime)] = (d if exact else None, neq)
        say(f"   {nom:>22} {nbits:>6} {regime:>7} {(d if exact else '—'):>8} "
            f"{neq:>10} {('OUI' if exact else statut):>28} {pred:>8}")


# ==========================================================================
rule("3. CE QUE VAUT UNE VIDÉO, CHIFFRÉ EN TIRAGES")
# ==========================================================================

say(f"""   {'famille':>22} {'état':>6} {'régime O':>10} {'régime T+':>11} {'régime T':>10} {'O vaut':>10}""")
for nom in CIBLES:
    nbits = FAMILLES[nom][0]
    o = BILAN[(nom, "O")][0]
    tp = BILAN[(nom, "T+")][0]
    t = BILAN[(nom, "T")][0]
    gain = f"×{t/o:.0f}" if (o and t) else "—"
    say(f"   {nom:>22} {nbits:>6} {(o or '—'):>10} {(tp or '—'):>11} {(t or '—'):>10} {gain:>10}")

say(f"""
   LE RAPPORT DE LA DERNIERE COLONNE EST CE QUE VAUT UNE VIDEO. Un tirage dont
   on connait l'ORDRE d'emission remplace des dizaines de tirages tries, parce
   que l'ordre transforme 4,32 bits de BRANCHEMENT en 4,48 bits d'EQUATIONS
   gratuites (§110).

   ET LE §125 SE LIT DANS LA COLONNE T+ CONTRE T : le canal boost aux bornes
   EXACTES economise des tirages, sans qu'aucune donnee nouvelle soit requise.""")


# ==========================================================================
rule("4. LE POSTE DE RÉCEPTION")
# ==========================================================================

say(f"""   `reconstituer(nom, tirages, regime)` prend EXACTEMENT ce qu'une video de
   tirage donne :

       tirages = [ ([n1..n20] DANS L'ORDRE, rang du bonus, bonus, boost), ... ]

   et rend l'etat, ou « incompatible » — ce qui est une exclusion, pas un echec.
   Il est ecrit pour etre appele le jour ou la donnee arrive.

   CE QU'IL FAUT LUI DONNER, PAR FAMILLE, EN REGIME O :""")
for nom in CIBLES:
    o = BILAN[(nom, "O")][0]
    if o:
        say(f"     {nom:>22} : {o} tirage(s) ordonne(s)")
say(f"""
   Et pour MT19937 (19 937 bits), le §114 a montre que le solveur C fait le
   travail : {19937/94.05:.0f} tirages ordonnes suffisent au meme compte de bits.

   LE DOSSIER A NEUF TIRAGES ORDONNES, ET AUCUN NE PORTE DE BONUS (§127). La
   chaine est donc complete, validee, et ARMEE — il lui manque une seule
   entree, et cette entree se filme.

   ({time.time() - T0:.1f} s)""")
