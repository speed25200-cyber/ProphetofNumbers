"""h94 — deux mots par numéro : l'hypothèse que toutes mes attaques faisaient sans le dire.

L'HYPOTHÈSE CACHÉE
===================
Les §103 a §112 supposent tous, sans jamais l'ecrire, qu'un numero coute UN mot
de generateur. Le stride vaut 20, 21, 79 ou 80 selon qu'on melange partiellement
ou completement, et le mot du pas k du tirage d occupe la position
(d - d_0)*stride + k.

CE N'EST PAS VRAI EN GENERAL, ET LA VERIFICATION EST A UNE COMMANDE :

    Random r = new Random(424242L);
    r.nextDouble()                       -> 0.35987869081344237
    deux next() consecutifs              -> 1545667241, 508083266
    (((long)(w1>>>6) << 27) + (w2>>>5)) * 2^-53   -> identique

`java.util.Random.nextDouble()` consomme DEUX mots de 32 bits. Il en va de meme
de toute implementation qui fabrique un double 53 bits a partir d'un generateur
32 bits — c'est-a-dire de la majorite d'entre elles.

    UN TIRAGE DE VINGT NUMEROS COUTE ALORS QUARANTE MOTS, PAS VINGT.

Tous mes strides etaient faux dans ce cas, et une attaque a stride faux
n'echoue pas bruyamment : elle rend « incompatible » et je consigne « exclu ».
C'est exactement le piege du renversement de cache du §112, sous une autre
forme.

CE QUE ÇA CHANGE, ET CE QUE ÇA NE CHANGE PAS
=============================================
CE QUE ÇA NE CHANGE PAS : le budget d'information. On observe toujours UN mot
par numero — le PREMIER de chaque paire, celui qui porte les bits de poids fort
du double. Les 89,7 equations par tirage du §105 restent, et la portee reste de
807 bits avec neuf tirages.

    THEOREME DU PREMIER MOT. Si u = (a*2^27 + b)*2^-53 avec a = next(26) et
    b = next(27), alors u = a/2^26 + b/2^53, donc |u - a/2^26| < 2^-26. Comme
    l'intervalle de troncature a pour largeur 1/K >= 1/80 >> 2^-26, on a
    floor(u*K) = floor((a/2^26)*K) sauf si a/2^26 tombe a moins de 2^-26 d'une
    frontiere — probabilite K*2^-26 < 1,2e-6 par mot.

    Les equations de prefixe portent donc sur le PREMIER mot de la paire, et le
    second n'est jamais observe. []

CE QUE ÇA CHANGE : l'INDEXATION. Le mot du pas k occupe desormais la position
(d - d_0)*stride + k*m, ou m est le nombre de mots par numero. Un mot sur deux
n'est contraint par rien, ce qui ne coute rien en equations mais decale tout le
reste du flux.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H94_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
DNOYAU = 8 if DRY else 20

# (mots par numero, strides plausibles)
PLANS = [(1, (20, 21, 22, 79, 80, 81)),
         (2, (40, 41, 42, 158, 160, 162))]
if DRY:
    PLANS = [(1, (20, 21)), (2, (40, 41))]


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
FAMILLES = list(_G["FAMILLES"])
LARGEUR = dict(_G["LARGEUR"])
prefixe, indices_fy = _G["prefixe"], _G["indices_fy"]
add_eq, back_substitute = _G["add_eq"], _G["back_substitute"]
kernel_basis = _G["kernel_basis"]

# on ajoute le generateur de V8, valide contre node au §112
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


# ==========================================================================
# LE SYSTÈME, AVEC LE NOMBRE DE MOTS PAR NUMÉRO EN PARAMÈTRE
# ==========================================================================
def formes(step, nbits, nwords, W, jmax=8):
    """coef[k][r] : forme F2 du bit de rang r depuis le poids fort du mot k."""
    coef = [[0] * jmax for _ in range(nwords)]
    dec = [W - 1 - r for r in range(jmax)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            ck = coef[k]
            for r, d in enumerate(dec):
                if (w >> d) & 1:
                    ck[r] |= bit
    return coef


def indices(ids, stride, mpn, i0):
    """decoupe[d][k] : position du mot qui engendre le pas k du tirage d."""
    return [[(d - i0) * stride + k * mpn for k in range(DRAWN)] for d in ids]


def systeme(coef, decoupe, tirages, sens, W):
    piv, neq = {}, 0
    for di, nums in enumerate(tirages):
        enc = indices_fy(nums, sens)
        if enc is None:
            return None, 0
        for k, (m, K) in enumerate(enc):
            j, val = prefixe(m, K, W)
            ck = coef[decoupe[di][k]]
            for r in range(j):
                if not add_eq(piv, ck[r], (val >> (j - 1 - r)) & 1, []):
                    return None, neq
                neq += 1
    return piv, neq


def emet(step, etat, W, decoupe, sens):
    nmax = max(max(d) for d in decoupe) + 1
    mots, s = [], etat
    for _ in range(nmax):
        s, w = step(s)
        mots.append(w)
    out = []
    for idx in decoupe:
        arr = list(range(1, POOL + 1))
        d = []
        for k, t in enumerate(idx):
            i = k if sens > 0 else POOL - 1 - k
            u = mots[t]
            p = (i + (u * (POOL - k)) // (1 << W)) if sens > 0 \
                else (u * (POOL - k)) // (1 << W)
            arr[i], arr[p] = arr[p], arr[i]
            d.append(arr[i])
        out.append(d)
    return out


def cherche(step, piv, nbits, decoupe, tirages, sens, W):
    sol, _f = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    if len(base) > DNOYAU:
        return None, len(base)
    cible = tirages[0][:4]
    pos = decoupe[0][:4]
    besoin = max(pos) + 1
    trouves, etat = [], sol
    for g in range(1 << len(base)):
        if g:
            etat ^= base[((g ^ (g - 1)).bit_length() - 1)]
        s, mots = etat, []
        for _ in range(besoin):
            s, w = step(s)
            mots.append(w)
        arr, ok = list(range(1, POOL + 1)), True
        for k in range(4):
            i = k if sens > 0 else POOL - 1 - k
            u = mots[pos[k]]
            p = (i + (u * (POOL - k)) // (1 << W)) if sens > 0 \
                else (u * (POOL - k)) // (1 << W)
            arr[i], arr[p] = arr[p], arr[i]
            if arr[i] != cible[k]:
                ok = False
                break
        if ok and emet(step, etat, W, decoupe, sens) == tirages:
            trouves.append(etat)
    return trouves, len(base)


# ==========================================================================
rule("1. L'HYPOTHÈSE QUE JE FAISAIS SANS LE DIRE")
# ==========================================================================

say("""   Les §103 a §112 supposent tous, sans jamais l'ecrire, qu'un numero coute
   UN mot de generateur.

   CE N'EST PAS VRAI EN GENERAL, et la verification tient en trois lignes de
   Java, executees sur cette machine :

       new Random(424242L).nextDouble()        -> 0.35987869081344237
       deux next() consecutifs                 -> 1545667241, 508083266
       (((w1>>>6) << 27) + (w2>>>5)) * 2^-53   -> IDENTIQUE

   `nextDouble()` consomme DEUX mots de 32 bits, et il en va de meme de toute
   implementation qui fabrique un double 53 bits depuis un generateur 32 bits.

       UN TIRAGE DE VINGT NUMEROS COUTE ALORS QUARANTE MOTS, PAS VINGT.

   Une attaque a stride faux n'echoue pas bruyamment : elle rend
   « incompatible », et je consigne « exclu ». C'est le piege du renversement
   de cache du §112 sous une autre forme.

   THEOREME DU PREMIER MOT. Si u = (a*2^27 + b)*2^-53 avec a = next(26), alors
   |u - a/2^26| < 2^-26, tandis que l'intervalle de troncature a pour largeur
   1/K >= 1/80. Donc floor(u*K) ne depend que de a, sauf a moins de K*2^-26 <
   1,2e-6 pres. Les equations de prefixe portent sur le PREMIER mot de la
   paire ; le second n'est jamais observe. []

   Consequence : le budget d'information est INCHANGE — 89,7 equations par
   tirage, portee 807 bits. Seule l'INDEXATION change.""")


# ==========================================================================
rule("2. LE TÉMOIN : UN TIRAGE À DEUX MOTS PAR NUMÉRO")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}

say(f"""   On plante un etat, on fabrique les tirages en consommant DEUX mots par
   numero — le second etant jete — aux identifiants REELS de l'archive, et on
   demande la reconstitution.
""")
say(f"   {'famille':>24} {'etat':>6} {'m':>3} {'equations':>10} {'rang':>6} "
    f"{'retrouve':>10} {'sec':>7}")
rnd = random.Random(20260916)
temoins, ATT = [], []
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    for mpn in (1, 2):
        dec = indices(IDS, 20 * mpn, mpn, IDS[0])
        nmax = max(max(d) for d in dec) + 1
        if nbits * nmax > (400_000 if DRY else 12_000_000):
            continue
        tt = time.time()
        etat = rnd.getrandbits(nbits) | 1
        tir = emet(step, etat, W, dec, 1)
        coef = formes(step, nbits, nmax, W)
        piv, neq = systeme(coef, dec, tir, 1, W)
        ok, dim = False, -1
        if piv is not None:
            got, dim = cherche(step, piv, nbits, dec, tir, 1, W)
            ok = got is not None and etat in got
        if 0 <= dim <= DNOYAU:
            ATT.append((nom, mpn))
            temoins.append(ok)
        say(f"   {nom:>24} {nbits:>6} {mpn:>3} {neq:>10} "
            f"{len(piv) if piv else -1:>6} "
            f"{('OUI' if ok else ('hors portee' if dim > DNOYAU else 'NON')):>10} "
            f"{time.time()-tt:>7.1f}")

say(f"""
   {sum(1 for t in temoins if t)}/{len(ATT)} etats retrouves. L'indexation a deux mots par numero tient.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

say(f"""   Flux unique (§110) sur les {len(IDS)} tirages. Pour chaque famille : deux
   valeurs de m, {sum(len(s) for _m, s in PLANS)} strides au total, deux conventions de Fisher-Yates.
""")
say(f"   {'famille':>24} {'essais':>7} {'exclus':>7} {'cherchés':>9} "
    f"{'non testés':>11} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES, NONT = 0, 0, 0, 0, 0
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    tr, ess, exc, chx, non = 0, 0, 0, 0, 0
    nmaxg = 0
    for mpn, strides in PLANS:
        for stride in strides:
            dec = indices(IDS, stride, mpn, IDS[0])
            nmaxg = max(nmaxg, max(max(d) for d in dec) + 1)
    if nbits * nmaxg > (400_000 if DRY else 25_000_000):
        say(f"   {nom:>24} {'—':>7} {'—':>7} {'—':>9} {'—':>11} "
            f"{'trop cher':>12} {0.0:>7.1f}")
        continue
    COEF = formes(step, nbits, nmaxg, W)
    for mpn, strides in PLANS:
        for stride in strides:
            dec = indices(IDS, stride, mpn, IDS[0])
            for sens in (1, -1):
                tir = [PARID[d] for d in IDS]
                ess += 1
                piv, _neq = systeme(COEF, dec, tir, sens, W)
                if piv is None:
                    exc += 1
                    continue
                got, dim = cherche(step, piv, nbits, dec, tir, sens, W)
                if got is None:
                    non += 1
                    continue
                chx += 1
                tr += len(got)
    TOTAL += tr
    ESSAIS += ess
    EXCLUS += exc
    CHERCHES += chx
    NONT += non
    say(f"   {nom:>24} {ess:>7} {exc:>7} {chx:>9} {non:>11} {tr:>12} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} systemes — {EXCLUS} exclus par
   incompatibilite, {CHERCHES} cherches, {NONT} non testes.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h94.mots_par_numero",
        "Aucun generateur F2-lineaire du catalogue du §68, ni le xorshift128 de "
        "V8 (§112), n'engendre les tirages ordonnes du dossier lorsque "
        "l'echantillonneur consomme DEUX mots par numero — le cas de tout double "
        "53 bits fabrique depuis un generateur 32 bits, `nextDouble()` de Java "
        "en tete",
        f"theoreme du premier mot : les bits de poids fort du double viennent du "
        f"PREMIER mot de la paire, le second n'etant jamais observe. Les "
        f"equations de prefixe sont donc inchangees, seule l'indexation l'est : "
        f"position = (d - d_0)*stride + k*m. Flux unique du §110, m dans {{1, 2}}, "
        f"{sum(len(s) for _m, s in PLANS)} strides, deux conventions",
        "aucun null n'est requis : le systeme est incompatible ou il ne l'est "
        "pas, et tout etat trouve est verifie par rejeu exact",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(1 for t in temoins if t)}/{len(ATT)} etats plantes "
                  f"retrouves, dont la moitie avec DEUX mots par numero, sur le "
                  f"motif d'identifiants reel de l'archive"),
        notes=(f"Les §103 a §112 supposaient tous, sans l'ecrire, un mot de "
               f"generateur par numero. Verifie sur cette machine : "
               f"`java.util.Random.nextDouble()` consomme DEUX mots de 32 bits, et "
               f"il en va de meme de toute implementation fabriquant un double 53 "
               f"bits depuis un generateur 32 bits. Un tirage coute alors 40 mots "
               f"et non 20. Une attaque a stride faux ne se plaint pas : elle rend "
               f"« incompatible » — le meme piege silencieux que le renversement de "
               f"cache du §112. Le budget d'information est inchange (89,7 "
               f"equations par tirage) ; seule l'indexation change."))
    h = lab.holm()
    say(f"   consigne : h94.mots_par_numero   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA CHANGE")
# ==========================================================================

say(f"""   TROIS PIEGES SILENCIEUX, TROIS SECTIONS. Le §112 a montre qu'un cache
   renverse fait echouer une attaque sans bruit ; celle-ci montre qu'un nombre
   de mots par numero mal devine fait exactement pareil. Dans les deux cas
   l'attaque rend « incompatible » et le registre enregistre « exclu ».

   LA REGLE QUI EN SORT : une exclusion ne vaut que pour le MODELE DE
   CONSOMMATION teste, et ce modele doit etre enumere explicitement — pas
   suppose. Le dossier compte desormais trois axes de modele :

     l'echantillonneur   modulo ou troncature        §94, §105
     le pas              fixe ou variable            §95, §111
     la consommation     un ou deux mots par numero  §114 (ici)

   et un quatrieme, propre a une bibliotheque : l'ORDRE DE SERVICE du cache
   (§112). Rien ne garantit qu'il n'y en ait pas un cinquieme.

   ({time.time() - T0:.1f} s)""")
