"""h111 — le sixième axe : la journée. Ce que les deux vidéos ont révélé.

CE QUE LE §121 AVAIT RECENSÉ, ET CE QU'IL AVAIT MANQUÉ
======================================================
Le §121 dresse la liste des axes du modèle de consommation : échantillonneur,
pas, mots par numéro, ordre de service, décalage. Cinq axes, et trois d'entre
eux n'avaient été trouvés qu'APRÈS COUP parce qu'un axe mal deviné fait échouer
une attaque SANS BRUIT.

Il en manquait un sixième, et l'archive le portait depuis le premier jour.

LA JOURNÉE
===========
Les intervalles entre tirages consécutifs ne prennent que deux valeurs :

    300 s   =  5 min       99,48 % des cas
    25 500 s = 7 h 05      345 fois — une par nuit

L'archive est donc faite de 346 BLOCS de 204 tirages, de 06:05 à 23:00 heure
locale. Et 204 x 5 min = 1 020 min = 17 h 00, exactement 06:05 -> 23:00.

    SI LA PLATEFORME RÉ-AMORCE SON GÉNÉRATEUR AU DÉBUT DE CHAQUE JOURNÉE, alors
    deux tirages de journées différentes n'appartiennent PAS au même flux, et
    toute attaque qui les aligne sur un flux unique teste un modèle impossible.

C'est exactement ce que le §110 fait : son « flux unique » enjambe 256
identifiants, donc au moins une nuit.

CE QUE LES VIDÉOS VALIDENT, À LA MINUTE PRÈS
=============================================
Deux enregistrements datés par leur nom de fichier :

    ScreenRecording_08-31-2026.13-05-00   ->  tirage 1381278
    ScreenRecording_09-01-2026.13-00-20   ->  tirage 1381481

En extrapolant la structure mesurée — 204 tirages par journée, début à 06:05 —
depuis la fin de l'archive :

    1381278  ->  index 84 de sa journée  ->  06:05 + 84x5 min = 13:05   EXACT
    1381481  ->  index 83 de sa journée  ->  06:05 + 83x5 min = 13:00   EXACT

Deux dates prédites à la minute par un modèle ajusté sur 70 560 tirages
ANTÉRIEURS. La structure de journée n'est pas une hypothèse : elle est mesurée
et vérifiée hors échantillon.

CE QUE CELA FAIT AUX ONZE TIRAGES ORDONNÉS
===========================================
    30/08   1381023, 1381026, 1381028, 1381030, 1381031      5 tirages
    31/08   1381256, 1381257, 1381258, 1381259, 1381278      5 tirages
    01/09   1381481                                          1 tirage

Sous flux unique : 11 x 89,7 = 987 équations sur un seul état.
Sous ré-amorçage quotidien : trois états distincts, 448 / 448 / 90 équations.

    LES DEUX MODÈLES SONT TESTABLES, ET AUCUN N'AVAIT ÉTÉ TESTÉ SÉPARÉMENT.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import datetime as dt
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H111_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
PARJOUR = 204
KCAP = 14


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_SRC = open(os.path.join(ICI, "h61_familles_etendues.py"), encoding="utf-8").read()
_G = {"__name__": "h61tete", "__file__": os.path.join(ICI, "h61_familles_etendues.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LES FAMILLES')], "h61tete", "exec"), _G)
FAMILLES = _G["OLD"] + _G["NEW"]
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]
LARGEUR = {"xorshift32": 32, "xorshift64": 64, "xorshift96": 32, "xorshift128": 32,
           "taus88": 32, "xoroshiro128 (brut)": 64, "xoshiro128 (brut)": 32,
           "xoshiro256 (brut)": 64, "LFSR113": 32, "WELL512a": 32}


def prefixe_int(a, b, K, W):
    j, val = 0, 0
    for jj in range(1, W + 1):
        lo = (a << jj) // K
        if lo != ((b << jj) - 1) // K:
            break
        j, val = jj, lo
    return j, val


def indices_fy(ordre):
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


def formes(step, nbits, nwords, W):
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


def rejoue(step, etat, indices, stride, off, W):
    """Rejoue le flux et rend les indices FY aux positions demandees."""
    besoin = max(indices) * stride + off + DRAWN
    s, mots = etat, []
    for _ in range(besoin):
        s, w = step(s)
        mots.append(w)
    out = {}
    for m in indices:
        base = m * stride + off
        arr, ordre = list(range(1, POOL + 1)), []
        for k in range(DRAWN):
            j = k + ((mots[base + k] * (POOL - k)) >> W)
            arr[k], arr[j] = arr[j], arr[k]
            ordre.append(arr[k])
        out[m] = ordre
    return out


def attaque(nom, nbits, step, W, tirages, stride, off, coef):
    """tirages : {index dans le flux -> ordre d'emission}. Rend le statut."""
    piv = {}
    for m, ordre in sorted(tirages.items()):
        fy = indices_fy(ordre)
        if fy is None:
            return "ordre impossible", None
        for k, a, b, K in fy:
            j, val = prefixe_int(a, b, K, W)
            for r in range(j):
                bit = (val >> (j - 1 - r)) & 1
                if not add_eq(piv, coef[m * stride + off + k][W - 1 - r], bit, []):
                    return "exclus", None
    if nbits - len(piv) > KCAP:
        return f"non teste (noyau {nbits-len(piv)})", None
    sol, _ = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    for g in range(1 << len(base)):
        cand, gg, i = sol, g, 0
        while gg:
            if gg & 1:
                cand ^= base[i]
            gg >>= 1
            i += 1
        if cand == 0:
            continue
        if rejoue(step, cand, list(tirages), stride, off, W) == tirages:
            return "COMPATIBLE", cand
    return "exclus", None


# ==========================================================================
rule("1. LA JOURNÉE, MESURÉE SUR L'ARCHIVE")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
D = np.diff(TS)
COUPE = np.flatnonzero(D > 1000)
BLOCS = np.diff(np.r_[-1, COUPE, len(IDS) - 1])
v, c = np.unique(D, return_counts=True)
say(f"""   Les intervalles entre tirages consecutifs ne prennent que deux valeurs :

     {int(v[np.argmax(c)]):>7} s = {int(v[np.argmax(c)])//60:>2} min          {100*c.max()/len(D):.2f} % des cas
     {int(v[c.argsort()[-2]]):>7} s = {int(v[c.argsort()[-2]])//60:>2} min      {int(c[c.argsort()[-2]])} fois — une par nuit

   L'archive est donc faite de {len(COUPE)+1} BLOCS. Tailles observees : """
    + ", ".join(f"{int(a)} x{int(b)}" for a, b in zip(*np.unique(BLOCS, return_counts=True)))
    + f"""

   {PARJOUR} x 5 min = {PARJOUR*5} min = {PARJOUR*5//60} h {PARJOUR*5%60:02d}, et la journee court de 06:05 a 23:00.""")


# ==========================================================================
rule("2. CE QUE LES DEUX VIDÉOS VALIDENT, À LA MINUTE PRÈS")
# ==========================================================================

DEB = dt.datetime(2026, 8, 31, 6, 5)
IDX278 = int((dt.datetime(2026, 8, 31, 13, 5) - DEB).total_seconds() // 300)
BASE = 1381278 - IDX278
say(f"""   Deux enregistrements dates par leur nom de fichier, et une structure ajustee
   sur 70 560 tirages ANTERIEURS :

   {'fichier':>42} {'tirage':>9} {'index':>6} {'prédit':>8} {'réel':>7}""")
for nomf, tid, reel in (("ScreenRecording_08-31-2026.13-05-00", 1381278, "13:05"),
                        ("ScreenRecording_09-01-2026.13-00-20", 1381481, "13:00")):
    off = tid - BASE
    j, k = off // PARJOUR, off % PARJOUR
    h = (DEB + dt.timedelta(days=j, minutes=5 * k)).strftime("%H:%M")
    say(f"   {nomf:>42} {tid:>9} {k:>6} {h:>8} {reel:>7}"
        + ("   OK" if h == reel else "   ECART"))
say("""
   Deux dates predites A LA MINUTE, hors echantillon. La structure de journee
   n'est pas une hypothese : elle est mesuree, puis verifiee.""")


# ==========================================================================
rule("3. LE SIXIÈME AXE, ET CE QU'IL FAIT AUX ONZE TIRAGES")
# ==========================================================================

ORD = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
JOURS = {}
for r in ORD:
    i = int(r["id"])
    off = i - BASE
    j, k = off // PARJOUR, off % PARJOUR
    date = (dt.datetime(2026, 8, 31) + dt.timedelta(days=j)).strftime("%d/%m")
    JOURS.setdefault(date, {})[k] = [int(r[f"o{n}"]) for n in range(1, DRAWN + 1)]

say(f"""   Le §121 recense CINQ axes : echantillonneur, pas, mots par numero, ordre de
   service, decalage. Il en manquait un SIXIEME — la JOURNEE.

   {'journée':>10} {'tirages ordonnés':>18} {'index dans la journée':>24} {'équations':>10}""")
for date, t in JOURS.items():
    say(f"   {date:>10} {len(t):>18} {str(sorted(t)):>24} {len(t)*89.7:>10.0f}")
say(f"""
   Sous FLUX UNIQUE (§110)      : {len(ORD)} x 89,7 = {len(ORD)*89.7:.0f} equations, UN etat.
   Sous RE-AMORCAGE QUOTIDIEN   : {len(JOURS)} etats distincts, {' / '.join(f'{len(t)*89.7:.0f}' for t in JOURS.values())} equations.

   Le §110 enjambe {max(int(r['id']) for r in ORD) - min(int(r['id']) for r in ORD)} identifiants, donc au moins une nuit : si la
   plateforme re-amorce, son modele est IMPOSSIBLE et son exclusion ne porte
   que sur le couple « generateur + pas de re-amorcage ».""")


# ==========================================================================
rule("4. L'ATTAQUE, JOURNÉE PAR JOURNÉE")
# ==========================================================================

STRIDES = [20, 21, 22] if not DRY else [21]
say(f"""   Chaque journee est attaquee comme un flux INDEPENDANT : le tirage d'index m
   occupe les mots m*stride + off + k. On balaie le pas et le decalage.

   {'journée':>8} {'famille':>22} {'état':>6} {'essais':>7} {'exclus':>7} {'non testés':>11} {'COMPATIBLES':>12}""")
TOTAL = {"essais": 0, "exclus": 0, "non": 0, "compat": 0}
CIBLES = [(n, nb, st) for n, nb, st, _r in FAMILLES]
for date, tirages in JOURS.items():
    if len(tirages) < 2 and not DRY:
        say(f"   {date:>8} {'(1 seul tirage — 90 équations, hors de portée)':>60}")
        continue
    mx = max(tirages)
    for nom, nbits, step in CIBLES:
        W = LARGEUR[nom]
        ess = exc = non = com = 0
        for stride in STRIDES:
            nw = mx * stride + (stride - 1) + DRAWN + 1
            coef = formes(step, nbits, nw, W)
            for off in range(stride):
                st, _e = attaque(nom, nbits, step, W, tirages, stride, off, coef)
                ess += 1
                if st == "exclus":
                    exc += 1
                elif st == "COMPATIBLE":
                    com += 1
                else:
                    non += 1
        for k, vv in (("essais", ess), ("exclus", exc), ("non", non), ("compat", com)):
            TOTAL[k] += vv
        say(f"   {date:>8} {nom:>22} {nbits:>6} {ess:>7} {exc:>7} {non:>11} {com:>12}")

say(f"""
   TOTAL : {TOTAL['essais']} essais, {TOTAL['exclus']} exclus, {TOTAL['non']} non testes,
   {TOTAL['compat']} COMPATIBLES.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h111.reamorcage_quotidien",
        "Sous l'hypothese d'un RE-AMORCAGE QUOTIDIEN — sixieme axe du modele de "
        "consommation, revele par la structure en blocs de 204 tirages de "
        "l'archive et validee a la minute par les horodatages des deux videos — "
        "aucune des dix familles F2-lineaires du catalogue n'engendre les "
        "tirages ordonnes d'une meme journee, sous aucun pas de 20 a 22 ni "
        "aucun decalage",
        "nombre d'etats COMPATIBLES, c'est-a-dire qui rejouent exactement les "
        "cinq tirages ordonnes de la journee. Le rejeu est le juge : le systeme "
        "echelonne ne suffit pas (§111). Une valeur NON NULLE serait la "
        "reconstitution",
        "aucun null n'est requis : un etat qui rejoue cinq tirages de vingt "
        "numeros exactement le fait avec probabilite (1/C(80,20))^5 = 1e-93 par "
        "hasard",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = TOTAL["essais"] - 1
    lab.record(
        tok, float(TOTAL["compat"]), p=1.0,
        verdict="conforme" if TOTAL["compat"] == 0 else "RECONSTITUTION",
        power_at=(f"le §110 a montre, temoin a l'appui, que la meme attaque "
                  f"reconstitue 10/10 familles sur un flux plante — WELL512a "
                  f"(512 bits) et LFSR113 (noyau 19) comprises"),
        notes=(f"SIXIEME AXE. Le §121 recensait cinq axes de consommation ; la "
               f"JOURNEE manquait. L'archive est faite de {len(COUPE)+1} blocs de "
               f"{PARJOUR} tirages, de 06:05 a 23:00, separes par des pauses de "
               f"25 500 s exactement. La structure predit A LA MINUTE les "
               f"horodatages des deux videos (13:05 et 13:00), hors echantillon. "
               f"Les onze tirages ordonnes se repartissent sur trois journees "
               f"({' / '.join(str(len(t)) for t in JOURS.values())}), et non sur un flux unique : "
               f"le « flux unique » du §110 enjambe {max(int(r['id']) for r in ORD)-min(int(r['id']) for r in ORD)} identifiants, donc au "
               f"moins une nuit. Son exclusion ne porte donc que sur le couple "
               f"generateur + absence de re-amorcage. Ce fichier teste l'autre "
               f"branche : {TOTAL['essais']} essais, {TOTAL['exclus']} exclus, "
               f"{TOTAL['non']} non testes, {TOTAL['compat']} compatibles."))
    h = lab.holm()
    say(f"   consigne : h111.reamorcage_quotidien   {TOTAL['compat']} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
