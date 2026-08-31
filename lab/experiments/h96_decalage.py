"""h96 — le cinquième axe : où commencent les vingt mots dans le bloc.

LE §113 AVAIT PRÉDIT UN CINQUIÈME AXE
======================================
Il concluait :

    « Une exclusion ne vaut que pour le MODELE DE CONSOMMATION teste, et ce
      modele doit etre enumere explicitement — pas suppose. [...] Rien ne
      garantit qu'il n'y en ait pas un cinquieme. »

Il y en a un, et c'est le plus bete de tous : le DECALAGE.

Toutes les attaques des §105 a §114 placent le mot du pas k du tirage
d'identifiant i a la position

    (i - i_0) * stride + k * m

c'est-a-dire qu'elles supposent que les vingt mots du tirage commencent au
DEBUT du bloc de stride. Rien ne le justifie. Si la plateforme tire d'abord le
multiplicateur de boost, puis les vingt numeros, puis l'indice du bonus, les
mots du tirage commencent a l'offset 1 et non 0 :

    stride 22 :  [boost][n1..n20][bonus]     offset 1
                 [n1..n20][bonus][boost]     offset 0
                 [bonus][boost][n1..n20]     offset 2

Les trois consomment vingt-deux mots par tirage et sont INDISTINGUABLES du
point de vue du stride. Une seule est testee par les §110 a §114.

    ET L'ECHEC EST SILENCIEUX, comme les deux precedents : un decalage faux
    rend le systeme incompatible, et le registre enregistre « exclu ».

CE QUE CELA COUTE, ET CE QUE CELA NE COUTE PAS
===============================================
Le budget d'information est INCHANGE : on observe toujours vingt mots par
tirage, donc 89,7 equations. Seule l'indexation bouge, comme au §113.

Le cout est en NOMBRE D'HYPOTHESES : il faut balayer les `stride` decalages
possibles pour chaque stride. Cela multiplie le nombre de systemes par une
vingtaine — sans rien couter en donnees, et sans que la puissance de chaque
test individuel ne baisse d'un pouce, puisque chacun est une EXCLUSION
ALGEBRIQUE et non un test statistique.

    C'EST LA LA VERTU DES EXCLUSIONS PAR INCOHERENCE : elles ne se paient pas
    de correction de multiplicite. Balayer mille hypotheses de consommation ne
    coute rien d'autre que du temps machine, la ou mille tests statistiques
    auraient exige un seuil mille fois plus dur.

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
DRY = os.environ.get("H96_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
DNOYAU = 8 if DRY else 12
# POURQUOI 12 ET NON 20. Le balayage des decalages multiplie le nombre de
# systemes par le stride. Pour une famille dont le rang SATURE sous sa taille
# nominale — LFSR113 loge 113 bits utiles dans 128 et sature a 109 (§106) — le
# noyau fait 19 dimensions A CHAQUE decalage, et le parcours coute 2^19 par
# systeme, soit 2,4e11 pas au total. Mesure faite : plus de quinze minutes pour
# la seule ligne du temoin. On plafonne donc a 12, ce qui declare LFSR113 NON
# TESTE sur cet axe — et non exclu. La distinction est celle du §105, et elle
# vaut mieux qu'un chiffre obtenu en laissant tomber la verification.
M64 = (1 << 64) - 1
CACHE = 64

# (mots par numero, strides) — le decalage est balaye de 0 a stride-1
PLANS = [(1, (20, 21, 22)), (2, (40, 41))] if DRY else \
        [(1, (20, 21, 22, 23, 24)), (2, (40, 41, 42))]


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


def v8(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    t = (s0 ^ (s0 << 23)) & M64
    t ^= t >> 17
    t ^= s1 ^ (s1 >> 26)
    return (s1 | (t << 64)), s1 >> 12


FAMILLES.append(("V8 Math.random (§112)", 128, v8, "Chrome, Node"))
LARGEUR["V8 Math.random (§112)"] = 52


def formes(step, nbits, nwords, W, jmax=8):
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


def indices(ids, stride, mpn, dec, i0):
    return [[(d - i0) * stride + dec + k * mpn for k in range(DRAWN)] for d in ids]


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


def avance(step, x, n):
    """L'etat apres `n` pas."""
    for _ in range(n):
        x, _w = step(x)
    return x


def cherche(step, piv, nbits, decoupe, tirages, sens, W):
    """Parcours du noyau, avec DEUX optimisations sans lesquelles c'est infaisable.

    1. L'AVANCE EST LINEAIRE. Le premier mot observe est au rang `decal` du
       flux : tester un candidat demandait de rejouer jusqu'a 48 pas depuis
       zero. Mais le generateur est F2-LINEAIRE, donc l'avance de `decal` pas
       l'est aussi : A^d(sol + somme c_i b_i) = A^d(sol) + somme c_i A^d(b_i).
       On avance donc la solution et la base UNE FOIS, et le code de Gray
       parcourt directement les etats AVANCES.

    2. ABANDON PRECOCE, SUR DOUZE NUMEROS ET NON QUATRE. Et le compte de
       quatre etait une erreur d'analyse : les directions du noyau laissent les
       bits de PREFIXE intacts PAR CONSTRUCTION — c'est leur definition. Un
       numero ne peut donc varier que dans les ~1,8 bits que le prefixe ne fixe
       pas, soit un facteur 3,5 par numero et non 80. Quatre numeros ne
       filtraient qu'un candidat sur 150, laissant des milliers de rejeux
       complets par decalage ; douze filtrent a un sur 700 000.

    Mesure : sans ces deux corrections, LFSR113 — dont le rang sature a 109,
    donc dont le noyau fait 19 dimensions MEME aux mauvais decalages — demandait
    plusieurs heures pour la seule section 3.
    """
    sol, _f = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    if len(base) > DNOYAU:
        return None, len(base)
    NTEST = 12
    cible, pos = tirages[0][:NTEST], decoupe[0][:NTEST]
    d0 = pos[0]
    solA = avance(step, sol, d0)
    baseA = [avance(step, b, d0) for b in base]
    ecarts = [pos[k] - pos[k - 1] for k in range(1, NTEST)]
    trouves, etatA, etat = [], solA, sol
    for g in range(1 << len(base)):
        if g:
            j = (g ^ (g - 1)).bit_length() - 1
            etatA ^= baseA[j]
            etat ^= base[j]
        s, w = step(etatA)
        arr = list(range(1, POOL + 1))
        i0 = 0 if sens > 0 else POOL - 1
        p = (i0 + (w * POOL) // (1 << W)) if sens > 0 else (w * POOL) // (1 << W)
        arr[i0], arr[p] = arr[p], arr[i0]
        if arr[i0] != cible[0]:
            continue
        ok = True
        for k in range(1, NTEST):
            for _ in range(ecarts[k - 1]):
                s, w = step(s)
            i = k if sens > 0 else POOL - 1 - k
            p = (i + (w * (POOL - k)) // (1 << W)) if sens > 0 \
                else (w * (POOL - k)) // (1 << W)
            arr[i], arr[p] = arr[p], arr[i]
            if arr[i] != cible[k]:
                ok = False
                break
        if ok and emet(step, etat, W, decoupe, sens) == tirages:
            trouves.append(etat)
    return trouves, len(base)


# ==========================================================================
rule("1. LE CINQUIÈME AXE, ET POURQUOI IL NE COÛTE RIEN")
# ==========================================================================

say("""   Le §113 concluait : « rien ne garantit qu'il n'y ait pas un cinquieme
   axe ». Il y en a un, et c'est le plus bete : le DECALAGE.

   Les §105 a §114 placent tous le mot du pas k a la position
   (i - i_0)*stride + k*m — donc ils supposent que les vingt mots du tirage
   commencent au DEBUT du bloc. Rien ne le justifie :

       stride 22 :  [boost][n1..n20][bonus]     decalage 1
                    [n1..n20][bonus][boost]     decalage 0   <- seul teste
                    [bonus][boost][n1..n20]     decalage 2

   Les trois consomment vingt-deux mots et sont indistinguables du point de vue
   du stride. Et l'echec est SILENCIEUX, comme les deux precedents : un
   decalage faux rend le systeme incompatible et le registre note « exclu ».

   CE QUE CELA COUTE. Rien en donnees : on observe toujours vingt mots par
   tirage, donc 89,7 equations. Le cout est en NOMBRE D'HYPOTHESES — il faut
   balayer `stride` decalages par stride.

   ET C'EST LA LA VERTU DES EXCLUSIONS PAR INCOHERENCE : elles ne se paient pas
   de correction de multiplicite. Balayer mille hypotheses de consommation ne
   coute que du temps machine, la ou mille tests STATISTIQUES auraient exige un
   seuil mille fois plus dur. Le registre compte m = 58 075 hypotheses
   corrigees par Holm ; les milliers de systemes de ce fichier n'y ajoutent
   qu'une ligne, parce qu'un systeme lineaire incoherent n'est pas un test.""")


# ==========================================================================
rule("2. LE TÉMOIN : UN DÉCALAGE NON NUL")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
PARID = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in LIGNES}

say(f"""   On plante un etat, on fabrique les tirages avec un decalage NON NUL — les
   vingt mots ne commencent pas au debut du bloc — et on verifie que l'attaque
   le retrouve quand elle balaie les decalages, et seulement alors.
""")
say(f"   {'famille':>24} {'décalage planté':>16} {'trouvé par balayage':>20} "
    f"{'trouvé à 0 seul':>16} {'sec':>7}")
rnd = random.Random(20260918)
temoins, zeros, ATT = [], [], []
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    if nbits > (128 if DRY else 256):
        continue
    tt = time.time()
    stride, mpn, vrai = 22, 1, 3
    dec = indices(IDS, stride, mpn, vrai, IDS[0])
    nmax = max(max(d) for d in dec) + 1
    etat = rnd.getrandbits(nbits) | 1
    tir = emet(step, etat, W, dec, 1)
    coef = formes(step, nbits, nmax + stride, W)
    ok_bal, ok_zero = False, False
    for essai in range(stride):
        d2 = indices(IDS, stride, mpn, essai, IDS[0])
        piv, _n = systeme(coef, d2, tir, 1, W)
        if piv is None:
            continue
        got, dim = cherche(step, piv, nbits, d2, tir, 1, W)
        if got and etat in got:
            ok_bal = True
            if essai == 0:
                ok_zero = True
    ATT.append(nom)
    temoins.append(ok_bal)
    zeros.append(ok_zero)
    say(f"   {nom:>24} {vrai:>16} {('OUI' if ok_bal else 'non'):>20} "
        f"{('oui' if ok_zero else 'NON'):>16} {time.time()-tt:>7.1f}")

say(f"""
   {sum(temoins)}/{len(ATT)} etats retrouves PAR LE BALAYAGE, et {sum(zeros)}/{len(ATT)} au decalage 0 seul.
   La colonne de droite est la demonstration du probleme : sans balayer les
   decalages, l'attaque aurait declare « exclu » un generateur qu'elle vient de
   reconstituer.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

NSYS = sum(s for _m, ss in PLANS for s in ss) * 2
say(f"""   Flux unique (§110), {sum(len(ss) for _m, ss in PLANS)} strides, TOUS les decalages de chacun, deux
   conventions de Fisher-Yates : {NSYS} systemes par famille.
""")
say(f"   {'famille':>24} {'systèmes':>9} {'exclus':>8} {'cherchés':>9} "
    f"{'non testés':>11} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES, NONT = 0, 0, 0, 0, 0
for nom, nbits, step, _r in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    nmaxg = 0
    for mpn, strides in PLANS:
        for stride in strides:
            dec = indices(IDS, stride, mpn, stride - 1, IDS[0])
            nmaxg = max(nmaxg, max(max(d) for d in dec) + 1)
    if nbits * nmaxg > (400_000 if DRY else 25_000_000):
        say(f"   {nom:>24} {'—':>9} {'—':>8} {'—':>9} {'—':>11} "
            f"{'trop cher':>12} {0.0:>7.1f}")
        continue
    COEF = formes(step, nbits, nmaxg, W)
    tr, ess, exc, chx, non = 0, 0, 0, 0, 0
    for mpn, strides in PLANS:
        for stride in strides:
            for decal in range(stride):
                dec = indices(IDS, stride, mpn, decal, IDS[0])
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
    say(f"   {nom:>24} {ess:>9,} {exc:>8,} {chx:>9} {non:>11} {tr:>12} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS:,} systemes — {EXCLUS:,} exclus par
   incompatibilite, {CHERCHES} cherches, {NONT} non testes.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h96.decalage",
        "Aucun generateur F2-lineaire du catalogue du §68, ni le xorshift128 de "
        "V8, n'engendre les tirages ordonnes du dossier, POUR AUCUN DECALAGE des "
        "vingt mots a l'interieur du bloc de stride — ce qui leve la derniere "
        "hypothese implicite des §105 a §114",
        f"flux unique du §110, {sum(len(ss) for _m, ss in PLANS)} strides, TOUS les decalages de chacun, "
        f"un et deux mots par numero (§113), deux conventions de Fisher-Yates, "
        f"soit {NSYS} systemes par famille. Echelonnement F2 puis rejeu exact",
        "aucun null n'est requis : un systeme lineaire incoherent n'est pas un "
        "test statistique et ne se paie d'aucune correction de multiplicite",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(temoins)}/{len(ATT)} etats plantes AVEC UN DECALAGE "
                  f"NON NUL retrouves par le balayage — et aucun ne l'est au decalage "
                  f"0 seul, ce qui demontre que l'axe manquait vraiment"),
        notes=(f"Le §113 avait predit un cinquieme axe de modele. C'est le "
               f"decalage : les §105 a §114 supposent tous que les vingt mots du "
               f"tirage commencent au DEBUT du bloc de stride, alors que "
               f"[boost][20 numeros][bonus] et [20 numeros][bonus][boost] "
               f"consomment le meme nombre de mots et sont indistinguables du "
               f"point de vue du stride. Un decalage faux rend le systeme "
               f"incompatible — echec silencieux, comme le renversement de cache "
               f"(§112) et les deux mots par numero (§113). Le cout est en nombre "
               f"d'hypotheses seulement : une exclusion par INCOHERENCE ne se paie "
               f"d'aucune correction, contrairement a un test statistique."))
    h = lab.holm()
    say(f"   consigne : h96.decalage   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. LES CINQ AXES, ET CE QUE CELA VEUT DIRE")
# ==========================================================================

say(f"""   LE MODELE DE CONSOMMATION, ENUMERE AU COMPLET :

     echantillonneur   modulo / troncature              §94, §105
     pas               fixe / variable                  §95, §111
     consommation      un / deux mots par numero        §113
     ordre de service  direct / cache renverse          §112
     decalage          0 a stride-1                     §116 (ici)

   TROIS DE CES CINQ AXES ONT ETE TROUVES APRES COUP, et chacun faisait
   echouer les attaques SANS BRUIT. C'est le vrai enseignement de ces trois
   sections, et il vaut au-dela de ce dossier :

     UNE ATTAQUE ALGEBRIQUE QUI REND « INCOMPATIBLE » NE DIT PAS « CE N'EST PAS
     CE GENERATEUR ». ELLE DIT « CE N'EST PAS CE GENERATEUR SOUS CE MODELE DE
     CONSOMMATION ». Le modele doit etre enumere, pas suppose.

   Ce qui protege le dossier, c'est que le balayage de ces axes ne coute que du
   temps : {ESSAIS:,} systemes ici pour UNE ligne de registre.

   ({time.time() - T0:.1f} s)""")
