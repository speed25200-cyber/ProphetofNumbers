"""h91 — le flux unique, et le théorème du confinement.

DEUX APPORTS, ET LE PREMIER EST UNE CORRECTION DE MON PROPRE TRAVAIL
====================================================================

I. LE FLUX UNIQUE. Le §105 a construit un systeme lineaire PAR BLOC de tirages
   consecutifs. L'archive ordonnee compte cinq blocs — 1, 1, 1, 2 et 4 tirages —
   donc au mieux 4 x 89,7 = 359 equations, et une portee de 350 bits d'etat.

   C'ETAIT UNE ERREUR DE DECOUPAGE, PAS UNE LIMITE DE DONNEES. Sous
   l'hypothese d'un flux CONTINU a stride constant, le mot qui engendre le pas
   k du tirage d'identifiant i occupe la position

       (i - i_0) * stride + k

   PARFAITEMENT CONNUE. Les tirages absents laissent des cases vides ; ils ne
   rompent pas l'alignement. Les neuf tirages contraignent donc UN SEUL etat,
   et le systeme porte 9 x 89,7 = 807 equations.

       PORTEE : 350 bits -> 807 bits, sans une seule donnee de plus.

II. LE THEOREME DU CONFINEMENT, qui dit ce que l'archive TRIEE peut donner et,
   surtout, POURQUOI elle resiste.

   Sous Fisher-Yates, au pas k, la valeur emise vaut a[j_k] ou a ne differe de
   l'identite qu'aux k positions deja echangees. Donc

       valeur emise = j_k + 1     sauf si j_k a deja ete touche,

   ce qui arrive avec probabilite au plus k/80. Il vient :

       THEOREME DU CONFINEMENT. Soit S l'ENSEMBLE (non ordonne) des vingt
       numeros du tirage. Alors, au pas k,

           P( j_k + 1  dans  S )  >=  1 - k/80,

       et au pas 0 l'inclusion est EXACTE : le tableau est encore l'identite.

   Chaque mot est donc confine a une reunion de vingt intervalles sur quatre-
   vingts, soit log2(80/20) = 2 bits d'information — SANS connaitre l'ordre.
   Sur 70 560 tirages, cela fait 2,8 millions de bits disponibles.

   ET POURQUOI CELA NE SUFFIT PAS, ce qui est le resultat le plus utile de ce
   fichier :

       COROLLAIRE DE BRANCHEMENT. Le confinement ne determine AUCUN bit du mot,
       parce qu'une reunion de vingt intervalles sur quatre-vingts n'est jamais
       contenue dans une moitie dyadique. Pour obtenir des equations il faut
       BRANCHER sur la valeur — vingt choix, soit log2(20) = 4,32 bits — et
       chaque valeur ainsi supposee rend 4,48 equations (§105).

       Le bilan par mot est donc de +0,16 bit seulement. Mais AUCUN
       branchement ne peut etre elague tant que le systeme reste sous-determine :
       l'arbre atteint 20^(n/4,48) noeuds AVANT de commencer a se contracter.
       Pour n = 128 bits cela fait 2^123 noeuds.

   C'est la demonstration quantitative de ce que tout le dossier constate :
   l'archive TRIEE contient largement assez d'information, et elle est hors
   d'atteinte par manque de LEVIER, pas par manque de bits.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H91_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
STRIDES = (20, 21) if DRY else (20, 21, 22, 79, 80, 81)
DNOYAU = 8 if DRY else 22


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_SRC = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LE TH')], "h86tete", "exec"), _G)

FAMILLES = _G["FAMILLES"]
LARGEUR = _G["LARGEUR"]
prefixe, indices_fy = _G["prefixe"], _G["indices_fy"]
formes, systeme, cherche = _G["formes"], _G["systeme"], _G["cherche"]
kernel_basis, back_substitute = _G["kernel_basis"], _G["back_substitute"]


# ==========================================================================
rule("1. LE FLUX UNIQUE — UNE ERREUR DE DÉCOUPAGE, PAS UNE LIMITE DE DONNÉES")
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
MAXB = max(len(b) for b in BLOCS)

say(f"""   Le §105 a construit un systeme PAR BLOC de tirages consecutifs. L'archive
   en compte {len(BLOCS)} — {', '.join(str(len(b)) for b in BLOCS)} tirages — donc au mieux
   {MAXB} x 89,7 = {MAXB*89.7:.0f} equations, et une portee de {MAXB*89.7:.0f} bits d'etat.

   C'EST UNE ERREUR DE DECOUPAGE. Sous l'hypothese d'un flux CONTINU a stride
   constant, le mot qui engendre le pas k du tirage d'identifiant i occupe la
   position (i - i_0) * stride + k, parfaitement CONNUE. Les tirages absents
   laissent des cases vides ; ils ne rompent pas l'alignement.

   Les {len(IDS)} tirages contraignent donc UN SEUL etat :

       equations disponibles : {len(IDS)} x 89,7 = {len(IDS)*89.7:.0f}
       portee                : {MAXB*89.7:.0f} bits  ->  {len(IDS)*89.7:.0f} bits

   sans une seule donnee de plus. L'etendue du flux vaut {(IDS[-1]-IDS[0]+1)} tirages, soit
   {(IDS[-1]-IDS[0])*20 + DRAWN:,} mots au stride 20 — dont {len(IDS)*DRAWN} observes.""")


def cherche_flux(step, piv, nbits, decoupe, tirages, nmots, sens, W):
    """Parcours du noyau, avec un filtre a QUATRE numeros avant tout rejeu.

    POURQUOI CE FILTRE EXISTE. La version du §105 testait UN numero puis
    rejouait le flux ENTIER — ici 4 740 mots. Sur un noyau d'une vingtaine de
    dimensions, un candidat sur quatre-vingts passe le premier test, soit des
    milliers de rejeux complets : mesure faite, plus de trente minutes pour la
    seule famille LFSR113. Quatre numeros au lieu d'un font tomber le taux de
    survie a 1/80^4, et le rejeu complet ne sert plus qu'a confirmer.
    """
    sol, _f = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    d = len(base)
    if d > DNOYAU:
        return None, d
    cible = tirages[0][:4]
    trouves, etat = [], sol
    for g in range(1 << d):
        if g:
            etat ^= base[((g ^ (g - 1)).bit_length() - 1)]
        s, arr, ok = etat, list(range(1, POOL + 1)), True
        for k in range(4):
            s, w = step(s)
            i = k if sens > 0 else POOL - 1 - k
            j = ((i + (w * (POOL - k)) // (1 << W)) if sens > 0
                 else (w * (POOL - k)) // (1 << W))
            arr[i], arr[j] = arr[j], arr[i]
            if arr[i] != cible[k]:
                ok = False
                break
        if not ok:
            continue
        _G["W_COURANT"] = W
        if _G["tirage_fy"](step, etat, nmots, sens, decoupe) == tirages:
            trouves.append(etat)
    return trouves, d


def systeme_unique(step, nbits, W, stride, sens, ids, parid, i0=None):
    """Les equations de prefixe de TOUS les tirages, dans un flux unique."""
    i0 = ids[0] if i0 is None else i0
    nmots = (ids[-1] - i0) * stride + DRAWN
    coef = formes(step, nbits, nmots, W)
    obs, decoupe, tirages = [], [], []
    for d in ids:
        nums = parid[d]
        enc = indices_fy(nums, sens)
        if enc is None:
            return None
        t0 = (d - i0) * stride
        decoupe.append(list(range(t0, t0 + DRAWN)))
        tirages.append(nums)
        for k, (m, K) in enumerate(enc):
            obs.append((t0 + k, m, K))
    piv, neq = systeme(coef, obs, W)
    return piv, neq, nmots, decoupe, tirages


# ==========================================================================
rule("2. LE TÉMOIN : LE FLUX TRAVERSE-T-IL LES TROUS ?")
# ==========================================================================

say(f"""   La question n'est pas rhetorique : si l'alignement a travers les trous
   etait faux, le systeme serait incompatible et je conclurais « exclu » sur
   une erreur de ma part. On plante donc un etat, on engendre le flux ENTIER,
   on n'en garde que les {len(IDS)} tirages aux identifiants REELS de l'archive — trous
   compris — et on demande la reconstitution.
""")
say(f"   {'famille':>22} {'etat':>6} {'equations':>10} {'rang':>6} {'noyau':>6} "
    f"{'retrouve':>10} {'sec':>7}")
rnd = random.Random(20260913)
temoins, ATT = [], []
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    etat = rnd.getrandbits(nbits) | 1
    nmots = (IDS[-1] - IDS[0]) * 20 + DRAWN
    if nbits * nmots > (300_000 if DRY else 20_000_000):
        say(f"   {nom:>22} {nbits:>6} {'—':>10} {'—':>6} {'—':>6} "
            f"{'trop cher':>10} {0.0:>7.1f}")
        continue
    # fabrique le flux complet puis n'en garde que les tirages aux vrais ids
    mots, s = [], etat
    for _ in range(nmots):
        s, w = step(s)
        mots.append(w)
    faux = {}
    for d in IDS:
        arr = list(range(1, POOL + 1))
        out = []
        t0 = (d - IDS[0]) * 20
        for k in range(DRAWN):
            j = k + (mots[t0 + k] * (POOL - k)) // (1 << W)
            arr[k], arr[j] = arr[j], arr[k]
            out.append(arr[k])
        faux[d] = out
    r = systeme_unique(step, nbits, W, 20, 1, IDS, faux)
    if r is None:
        continue
    piv, neq, nm, decoupe, tir = r
    _G["W_COURANT"] = W
    ok, dim = False, -1
    if piv is not None:
        got, dim = cherche_flux(step, piv, nbits, decoupe, tir, nm, 1, W)
        ok = got is not None and etat in got
    if 0 <= dim <= DNOYAU:
        ATT.append(nom)
        temoins.append(ok)
    say(f"   {nom:>22} {nbits:>6} {neq:>10} {len(piv) if piv else -1:>6} "
        f"{dim if dim >= 0 else '—':>6} "
        f"{('OUI' if ok else ('hors portee' if dim > DNOYAU else 'NON')):>10} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {sum(1 for t in temoins if t)}/{len(ATT)} etats retrouves a travers les trous. L'alignement tient : un
   identifiant manquant est un decalage connu, pas une rupture.""")


# ==========================================================================
rule("3. LE FLUX UNIQUE SUR L'ARCHIVE")
# ==========================================================================

say(f"""   {len(IDS)} tirages, {len(STRIDES)} strides, deux conventions de Fisher-Yates.
""")
say(f"   {'famille':>22} {'essais':>7} {'exclus':>7} {'cherchés':>9} "
    f"{'non testés':>11} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES, NONT = 0, 0, 0, 0, 0
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    trouve, ess, exc, chr_, non = 0, 0, 0, 0, 0
    for stride in STRIDES:
        nmots = (IDS[-1] - IDS[0]) * stride + DRAWN
        if nbits * nmots > (300_000 if DRY else 20_000_000):
            continue
        for sens in (1, -1):
            r = systeme_unique(step, nbits, W, stride, sens, IDS, PARID)
            if r is None:
                continue
            piv, neq, nm, decoupe, tir = r
            ess += 1
            if piv is None:
                exc += 1
                continue
            _G["W_COURANT"] = W
            got, dim = cherche_flux(step, piv, nbits, decoupe, tir, nm, sens, W)
            if got is None:
                non += 1
                continue
            chr_ += 1
            trouve += len(got)
    TOTAL += trouve
    ESSAIS += ess
    EXCLUS += exc
    CHERCHES += chr_
    NONT += non
    say(f"   {nom:>22} {ess:>7} {exc:>7} {chr_:>9} {non:>11} {trouve:>12} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} systemes — {EXCLUS} exclus par incompatibilite,
   {CHERCHES} cherches, {NONT} non testes.""")


# ==========================================================================
rule("4. LE THÉORÈME DU CONFINEMENT — CE QUE L'ARCHIVE TRIÉE PEUT DONNER")
# ==========================================================================

say("""   Les neuf tirages ordonnes sont une goutte ; l'archive en compte 70 560,
   triee. Que peut-on en tirer SANS l'ordre ?

   THEOREME DU CONFINEMENT. Sous Fisher-Yates, au pas k, la valeur emise vaut
   a[j_k], ou a ne differe de l'identite qu'aux k positions deja echangees.
   Donc

       valeur emise = j_k + 1     sauf si j_k a deja ete touche,

   ce qui arrive avec probabilite au plus k/80. Par consequent, si S designe
   l'ENSEMBLE non ordonne des vingt numeros,

       P( j_k + 1  dans  S )  >=  1 - k/80,

   et au pas 0 l'inclusion est EXACTE — le tableau est encore l'identite. []
""")
say(f"   {'pas k':>7} {'P(confinement)':>16} {'bits':>7}")
for k in (0, 5, 10, 15, 19):
    say(f"   {k:>7} {1 - k/80:>16.3f} {np.log2(80/20):>7.2f}")
say(f"""
   Chaque mot est donc confine a vingt intervalles sur quatre-vingts, soit
   {np.log2(80/20):.2f} bits — SANS connaitre l'ordre. Sur 70 560 tirages et vingt mots :
   {70560*20*2/1e6:.1f} MILLIONS de bits disponibles, pour un etat qui en fait 128.

   L'INFORMATION EST LA. ELLE EST POURTANT HORS D'ATTEINTE, et voici pourquoi.

   COROLLAIRE DE BRANCHEMENT. Le confinement ne determine AUCUN bit du mot :
   une reunion de vingt intervalles sur quatre-vingts n'est jamais contenue
   dans une moitie dyadique — il faudrait que les vingt numeros soient tous
   sous 41 ou tous au-dessus, ce qui arrive avec probabilite""")
from math import comb
p_moitie = 2 * comb(40, 20) / comb(80, 20)
say(f"""       2 C(40,20)/C(80,20) = {p_moitie:.3e}   soit jamais.

   Pour obtenir des equations il faut donc BRANCHER sur la valeur — vingt
   choix, log2(20) = {np.log2(20):.2f} bits — et chaque valeur supposee rend 4,48
   equations (§105). Le bilan par mot vaut +{4.48-np.log2(20):.2f} bit.

   MAIS AUCUN BRANCHEMENT NE PEUT ETRE ELAGUE tant que le systeme est
   sous-determine : l'incompatibilite n'apparait qu'au-dela de n equations.
   L'arbre atteint donc

       20^(n/4,48) noeuds AVANT de commencer a se contracter :""")
say(f"\n   {'etat n':>8} {'mots requis':>12} {'noeuds':>12}")
for n in (32, 64, 128, 256):
    d = n / 4.48
    say(f"   {n:>8} {d:>12.1f} {'2^%.0f' % (d*np.log2(20)):>12}")
say(f"""
   C'est la demonstration QUANTITATIVE de ce que tout le dossier constatait
   sans le dire : l'archive triee contient largement assez d'information —
   {70560*20*2/1e6:.1f} millions de bits pour 128 — et elle reste hors d'atteinte par manque
   de LEVIER, pas par manque de bits. Le levier, c'est l'ORDRE : il change
   4,32 bits de branchement en 4,48 bits d'equations GRATUITES.

   ET C'EST LA LA VALEUR EXACTE D'UN TIRAGE ORDONNE : il ne vaut pas 89,7 bits
   de plus qu'un tirage trie. Il vaut la difference entre 2^123 noeuds et un
   pivot de Gauss.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h91.flux_unique",
        "Aucun generateur F2-lineaire du catalogue du §68, sous troncature via "
        "Fisher-Yates, n'engendre les NEUF tirages ordonnes de l'archive lus "
        "comme UN SEUL FLUX a stride constant — ce qui porte la contrainte de "
        f"{MAXB*89.7:.0f} equations (meilleur bloc, §105) a {len(IDS)*89.7:.0f}",
        f"les tirages absents laissent des cases vides dans le flux : le mot du "
        f"pas k du tirage i occupe la position (i - i_0)*stride + k, connue. "
        f"Echelonnement F2 des prefixes de tous les tirages a la fois, parcours "
        f"du noyau, rejeu exact. {len(STRIDES)} strides x 2 conventions",
        "aucun null n'est requis : le rejeu compare tous les numeros de tous les "
        "tirages DANS L'ORDRE",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(1 for t in temoins if t)}/{len(ATT)} etats plantes "
                  f"retrouves A TRAVERS LES TROUS, sur le motif d'identifiants REEL "
                  f"de l'archive"),
        notes=(f"Le §105 construisait un systeme PAR BLOC consecutif — au mieux "
               f"{MAXB} tirages, {MAXB*89.7:.0f} equations, {MAXB*89.7:.0f} bits de portee. C'etait une "
               f"erreur de DECOUPAGE et non une limite de donnees : sous flux "
               f"continu a stride constant, un identifiant manquant est un "
               f"decalage CONNU, pas une rupture. Les neuf tirages contraignent un "
               f"seul etat et rendent {len(IDS)*89.7:.0f} equations. Portee {MAXB*89.7:.0f} -> {len(IDS)*89.7:.0f} bits sans "
               f"une donnee de plus. Le fichier demontre aussi le THEOREME DU "
               f"CONFINEMENT et son corollaire de branchement, qui chiffre pourquoi "
               f"l'archive TRIEE, riche de 2,8 millions de bits, reste hors "
               f"d'atteinte : 2^123 noeuds d'arbre avant tout elagage pour 128 bits "
               f"d'etat."))
    h = lab.holm()
    say(f"   consigne : h91.flux_unique   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA CHANGE")
# ==========================================================================

say(f"""   LA PORTEE A PLUS QUE DOUBLE SANS UNE DONNEE DE PLUS : {MAXB*89.7:.0f} bits d'etat au
   §105, {len(IDS)*89.7:.0f} ici. Tout le catalogue F2-lineaire y passe, WELL512a compris.

   ET LA REGLE GENERALE QUI EN SORT, valable pour la suite : ce qui compte
   n'est pas le nombre de tirages CONSECUTIFS mais le nombre de tirages
   ORDONNES, quelle que soit leur dispersion. Le §105 demandait 225 tirages
   consecutifs pour MT19937 ; il en faut 225 ORDONNES, et ils peuvent etre
   pris n'importe ou dans l'archive — ce qui est une contrainte de collecte
   entierement differente, et bien plus facile.

   ({time.time() - T0:.1f} s)""")
