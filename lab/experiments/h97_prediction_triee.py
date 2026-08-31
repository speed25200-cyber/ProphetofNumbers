"""h97 — prédire depuis l'archive TRIÉE : boucler la chaîne.

CE QUI MANQUAIT, ET C'EST UN VRAI TROU
=======================================
Le §109 a construit un predicteur : il annonce les vingt numeros du tirage
suivant, dans l'ordre, et 15 generateurs plantes sur 15 le confirment. Mais il
part des tirages ORDONNES — et le dossier n'en compte que NEUF.

Le §114, lui, reconstitue MT19937 a etat complet depuis les RANGS DU BONUS des
70 560 tirages TRIES — la donnee dont on dispose en masse. Mais il s'arrete a
l'etat : il n'a jamais PREDIT.

    D'un cote un predicteur sans donnees, de l'autre des donnees sans
    prediction. Ce fichier soude les deux.

LE THÉORÈME DE PRÉDICTION DEPUIS UNE DONNÉE PARTIELLE
======================================================
    Le rang du bonus ne publie que 3,20 bits par tirage — moins d'un
    vingtieme des 61,6 bits que contient l'ensemble tire. On pourrait croire
    qu'un predicteur bati dessus ne rendra qu'une prediction PARTIELLE.

    C'EST FAUX, ET C'EST TOUT L'INTERET. Une fois l'etat identifie, la sortie
    du generateur est ENTIEREMENT determinee : les vingt numeros, leur ORDRE
    D'EMISSION — jamais observe —, le rang du bonus, et tous les tirages
    suivants. La quantite d'information de l'OBSERVATION ne borne pas celle de
    la PREDICTION ; elle ne borne que le NOMBRE DE TIRAGES qu'il faut observer.

        observation : 3,20 bits par tirage
        prediction  : 61,6 bits par tirage, plus l'ordre, a horizon infini

    Autrement dit : on observe un vingtieme, et on rend tout. []

    C'est la difference de nature entre une approche statistique — ou l'edge
    se degrade a chaque pas (§107, §108) — et une reconstitution d'etat, ou
    l'horizon est infini parce qu'il n'y a plus rien d'aleatoire.

CE QUE CE FICHIER MESURE
=========================
Pour chaque famille : le nombre de tirages TRIES a observer pour que le tirage
SUIVANT soit annonce exactement — vingt numeros dans l'ordre d'emission, plus le
bonus — puis la verification a dix tirages d'horizon.

REGISTRE : INCHANGE. Ce fichier ne teste aucune hypothese neuve sur l'archive ;
il rejoue les exclusions des §106 et §114 et ne consigne rien.
"""

import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
DRY = os.environ.get("H97_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H97_TMP", "/tmp")
POOL, DRAWN, KB = 80, 20, 20
STRIDE, OFF = 21, 20
HORIZON = 10


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_H86 = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_H86[:_H86.index('rule("1. LE TH')], "h86tete", "exec"), _G)
FAMILLES = list(_G["FAMILLES"])
LARGEUR = dict(_G["LARGEUR"])
prefixe = _G["prefixe"]

_H95 = open(os.path.join(ICI, "h95_mt19937.py"), encoding="utf-8").read()
_M = {"__name__": "h95tete", "__file__": os.path.join(ICI, "h95_mt19937.py")}
exec(compile(_H95[:_H95.index('rule("1. LE MUR')], "h95tete", "exec"), _M)

M64 = (1 << 64) - 1


def v8(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    t = (s0 ^ (s0 << 23)) & M64
    t ^= t >> 17
    t ^= s1 ^ (s1 >> 26)
    return (s1 | (t << 64)), s1 >> 12


FAMILLES.append(("V8 Math.random (§112)", 128, v8, "Chrome, Node"))
LARGEUR["V8 Math.random (§112)"] = 52
MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB


# ==========================================================================
# TIRER, ET PRÉDIRE
# ==========================================================================
def tirages_depuis(mots, nd, W):
    """Les tirages complets : numeros DANS L'ORDRE D'EMISSION, et rang du bonus."""
    out = []
    for d in range(nd):
        arr = list(range(1, POOL + 1))
        ordre = []
        for k in range(DRAWN):
            u = mots[d * STRIDE + k]
            j = k + (u * (POOL - k)) // (1 << W)
            arr[k], arr[j] = arr[j], arr[k]
            ordre.append(arr[k])
        rang = (mots[d * STRIDE + OFF] * KB) >> W
        out.append((ordre, sorted(ordre), rang, sorted(ordre)[rang]))
    return out


def mots_de(step, etat, n):
    mots, s = [], etat
    for _ in range(n):
        s, w = step(s)
        mots.append(w)
    return mots


def formes_generiques(step, nbits, positions, W, jmax=6):
    """Les formes de poids fort aux positions demandees, par vecteurs unitaires."""
    besoin = set(positions)
    nmax = max(positions) + 1
    out = {p: [0] * jmax for p in positions}
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nmax):
            s, w = step(s)
            if k in besoin:
                ok = out[k]
                for r in range(jmax):
                    if (w >> (W - 1 - r)) & 1:
                        ok[r] |= bit
    return out


def ecrire(chemin, formes, rangs, positions, nbits):
    W8 = (nbits + 63) // 64
    n = 0
    with open(chemin, "wb") as f:
        f.write(struct.pack("<ii", nbits, 0))
        for d, r in enumerate(rangs):
            j, val = prefixe(int(r), KB, 32)
            fp = formes[positions[d]]
            for k in range(j):
                f.write(fp[k].to_bytes(W8 * 8, "little"))
                f.write(bytes([(val >> (j - 1 - k)) & 1]))
                n += 1
        f.seek(4)
        f.write(struct.pack("<i", n))
    return n


def resoudre(chemin, binaire, nbits):
    p = subprocess.run([binaire, chemin], capture_output=True, text=True, timeout=3600)
    d = dict(kv.split("=") for kv in p.stdout.split("\n")[0].split())
    sol = None
    for l in p.stdout.split("\n"):
        if l.startswith("solution="):
            h = l.split("=")[1]
            mots = [int(h[i:i + 16], 16) for i in range(0, len(h), 16)]
            sol = sum(m << (64 * i) for i, m in enumerate(mots))
    return int(d["rang"]), int(d["incoherent"]), sol


# ==========================================================================
rule("1. LE THÉORÈME DE PRÉDICTION DEPUIS UNE DONNÉE PARTIELLE")
# ==========================================================================

say(f"""   CE QUI MANQUAIT. Le §109 predit — quinze generateurs sur quinze, horizon
   dix — mais il part des tirages ORDONNES, et le dossier n'en compte que NEUF.
   Le §114 reconstitue MT19937 depuis les 70 560 tirages TRIES, mais il s'arrete
   a l'etat : il n'a jamais predit.

   D'un cote un predicteur sans donnees, de l'autre des donnees sans
   prediction. Ce fichier soude les deux.

   THEOREME. Le rang du bonus ne publie que {MOY:.2f} bits par tirage — moins d'un
   vingtieme des 61,6 bits que contient l'ensemble tire. On pourrait croire
   qu'un predicteur bati dessus ne rendra qu'une prediction PARTIELLE.

   C'est faux. Une fois l'etat identifie, la sortie est ENTIEREMENT determinee :
   les vingt numeros, leur ORDRE D'EMISSION — jamais observe —, le rang du
   bonus, et tous les tirages suivants.

       observation : {MOY:.2f} bits par tirage
       prediction  : 61,6 bits par tirage, PLUS l'ordre, a horizon INFINI

   La quantite d'information de l'OBSERVATION ne borne pas celle de la
   PREDICTION ; elle ne borne que le NOMBRE DE TIRAGES a observer. []

   C'est la difference de nature avec les §107 et §108, ou l'edge s'evanouit
   dans le bruit : ici il n'y a pas d'edge, il n'y a plus rien d'aleatoire.""")


# ==========================================================================
rule("2. LA DÉMONSTRATION : OBSERVER DES ENSEMBLES, ANNONCER UN ORDRE")
# ==========================================================================

BIN = os.path.join(TMP, "f2solve97")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "f2solve.c")], check=True,
               capture_output=True)

say(f"""   Pour chaque famille : on plante un etat, on fabrique des tirages, on ne
   garde que les RANGS DU BONUS — pas les numeros, pas l'ordre — on reconstitue,
   puis on ANNONCE le tirage suivant : ses vingt numeros DANS L'ORDRE
   D'EMISSION, et son bonus. Puis on verifie a {HORIZON} tirages d'horizon.
""")
say(f"   {'famille':>24} {'état':>6} {'tirages triés':>14} {'tirage +1':>11} "
    f"{'bonus +1':>9} {f'horizon {HORIZON}':>11} {'sec':>7}")

import random                                                  # noqa: E402
rnd = random.Random(20260919)
RES = []
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    nd = int(nbits / MOY) + 8
    if DRY and nbits > 128:
        continue
    tt = time.time()
    etat = rnd.getrandbits(nbits) | 1
    nmots = (nd + HORIZON + 2) * STRIDE
    mots = mots_de(step, etat, nmots)
    vrai = tirages_depuis(mots, nd + HORIZON + 1, W)
    rangs = [t[2] for t in vrai[:nd]]
    pos = [d * STRIDE + OFF for d in range(nd)]
    F = formes_generiques(step, nbits, pos, W)
    ch = os.path.join(TMP, "h97.bin")
    ecrire(ch, F, rangs, pos, nbits)
    rang, inc, sol = resoudre(ch, BIN, nbits)
    ok1 = okb = okh = False
    if sol is not None and not inc:
        m2 = mots_de(step, sol, nmots)
        pred = tirages_depuis(m2, nd + HORIZON + 1, W)
        ok1 = pred[nd][0] == vrai[nd][0]
        okb = pred[nd][3] == vrai[nd][3]
        okh = pred[nd:nd + HORIZON] == vrai[nd:nd + HORIZON]
    RES.append((nom, ok1, okb, okh))
    say(f"   {nom:>24} {nbits:>6} {nd:>14,} {('EXACT' if ok1 else 'non'):>11} "
        f"{('exact' if okb else 'non'):>9} "
        f"{(f'{HORIZON}/{HORIZON}' if okh else '—'):>11} {time.time()-tt:>7.1f}")

# ---- MT19937, par la voie du §114 ----
if not DRY:
    tt = time.time()
    NDM = int(19937 / MOY) + 200
    MT = _M["mt_init_etat"](20260919)
    mots = _M["mt_mots"](MT, (NDM + HORIZON + 2) * STRIDE)
    vrai = tirages_depuis(mots, NDM + HORIZON + 1, 32)
    rangs = [t[2] for t in vrai[:NDM]]
    pos = [d * STRIDE + OFF for d in range(NDM)]
    F = _M["formes_aux_positions"](pos)
    ch = os.path.join(TMP, "h97mt.bin")
    ecrire(ch, F, rangs, pos, 19937)
    rang, inc, sol = resoudre(ch, BIN, 19937)
    ok1 = okb = okh = False
    if sol is not None and not inc:
        mt2, bit = [0] * 624, 0
        for i in range(624):
            for b in range(32):
                if i == 0 and b < 31:
                    continue
                if (sol >> bit) & 1:
                    mt2[i] |= 1 << b
                bit += 1
        m2 = _M["mt_mots"](mt2, (NDM + HORIZON + 2) * STRIDE)
        pred = tirages_depuis(m2, NDM + HORIZON + 1, 32)
        ok1 = pred[NDM][0] == vrai[NDM][0]
        okb = pred[NDM][3] == vrai[NDM][3]
        okh = pred[NDM:NDM + HORIZON] == vrai[NDM:NDM + HORIZON]
    RES.append(("MT19937 (§114)", ok1, okb, okh))
    say(f"   {'MT19937 (§114)':>24} {19937:>6} {NDM:>14,} "
        f"{('EXACT' if ok1 else 'non'):>11} {('exact' if okb else 'non'):>9} "
        f"{(f'{HORIZON}/{HORIZON}' if okh else '—'):>11} {time.time()-tt:>7.1f}")

N1 = sum(1 for _n, a, _b, _c in RES if a)
NB = sum(1 for _n, _a, b, _c in RES if b)
NH = sum(1 for _n, _a, _b, c in RES if c)
say(f"""
   {N1}/{len(RES)} tirages suivants annonces EXACTEMENT — vingt numeros DANS L'ORDRE
   D'EMISSION, un ordre que l'observation ne contenait a aucun moment.
   {NB}/{len(RES)} bonus exacts. {NH}/{len(RES)} horizons de {HORIZON} tirages entierement exacts.

   ET C'EST LA LE POINT : l'observation ne portait que sur des ENSEMBLES TRIES
   et un rang. L'ordre d'emission a ete PREDIT, jamais vu.""")


# ==========================================================================
rule("3. CE QU'IL FAUDRAIT OBSERVER, PAR FAMILLE")
# ==========================================================================

say(f"""   {MOY:.2f} equations par tirage trie : un etat de n bits demande n/{MOY:.2f}
   tirages. L'archive en compte 70 560.

     {'état':>8} {'tirages triés requis':>22} {'archive suffit ?':>17}""")
for n in (32, 64, 128, 256, 512, 1024, 19937, 200000):
    b = int(n / MOY) + 1
    say(f"     {n:>8} {b:>22,} {('OUI' if b <= 70560 else 'non'):>17}")
say(f"""
   La donnee n'est donc PAS le facteur limitant jusqu'a ~{int(70560*MOY):,} bits d'etat.
   Ce qui limite, c'est le cout de calcul des formes lineaires — et le §114 a
   montre qu'il tombe avec un solveur en C.""")


# ==========================================================================
rule("4. SUR L'ARCHIVE, ET CE QUE CELA VEUT DIRE")
# ==========================================================================

say(f"""   Applique aux vrais rangs du bonus, ce predicteur ne rend RIEN : les §106
   et §114 ont montre que tous les systemes sont incoherents, pour toutes les
   familles F2-lineaires testees et pour MT19937.

   Il n'y a donc pas de prediction a annoncer, et il serait malhonnete d'en
   fabriquer une. Ce que ce fichier etablit, c'est autre chose :

     LA CHAINE EST COMPLETE ET VERIFIEE DE BOUT EN BOUT. Ensembles tries ->
     rangs du bonus -> equations F2 -> etat -> ORDRE D'EMISSION et tirages
     FUTURS. Chaque maillon est mesure, et le dernier — celui qui manquait —
     rend {N1}/{len(RES)} tirages exacts sur generateurs plantes.

   Si un jour un generateur du catalogue rend un systeme COHERENT sur l'archive,
   il n'y aura rien de plus a inventer : la prediction sortira du meme code, a
   horizon infini.

   REGISTRE : INCHANGE. Ce fichier ne teste aucune hypothese neuve — il rejoue
   les exclusions des §106 et §114.

   ({time.time() - T0:.1f} s)""")
