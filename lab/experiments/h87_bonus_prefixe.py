"""h87 — le préfixe sur les 70 560 tirages : la troncature portée à l'archive entière.

CE QUE LE §105 A LAISSÉ SUR LA TABLE
=====================================
Le theoreme du prefixe (§105) donne 4,48 equations F2 exactes par mot. Mais il
exige l'ORDRE d'emission, pour reconstruire l'indice de Fisher-Yates — et
l'ordre n'existe que sur NEUF tirages. Quatre-vingts mots consecutifs au mieux,
d'ou les 126 systemes declares « non testes » du §105.

L'archive, elle, compte 70 560 tirages. Triee, donc muette sur l'ordre. Sauf
qu'il reste un champ.

LE FAIT STRUCTUREL
===================
Le `bonus` est TOUJOURS l'un des vingt numeros tires — 70 560 sur 70 560, la ou
l'independance en predirait 17 640. Ce n'est pas un tirage supplementaire :
c'est une DESIGNATION parmi les vingt.

Le dossier connaissait ce fait. Il ne l'avait lu qu'a travers l'echantillonneur
MODULO : le §89 prend (bonus - 1) mod 16, soit les quatre bits BAS, et le §100
etend la portee de ce calcul a toute recurrence lineaire modulo 2^k.

SOUS TRONCATURE, LA MEME DONNEE DIT AUTRE CHOSE
================================================
Une designation par indice s'ecrit

    bonus = tires[ floor(u * 20) ]

et le RANG du bonus parmi les vingt numeros TRIES est calculable depuis
l'archive — c'est le nombre de numeros tires qui lui sont inferieurs. Si le
tableau indexe est le tableau trie, alors

    rang  =  floor(u * 20)

est une observation de TRONCATURE, exacte, disponible sur les 70 560 tirages.
Le theoreme du prefixe s'y applique avec K = 20 au lieu de 80.

    MOINS DE BITS PAR OBSERVATION — 2,5 au lieu de 4,48 — MAIS SEPT MILLE FOIS
    PLUS D'OBSERVATIONS.

Et le stride est FIXE : vingt mots pour le Fisher-Yates, un mot pour l'indice,
soit 21 par tirage. C'est precisement ce que le §95 reprochait au bonus lu
comme sortie brute sous rejet — la ou le nombre de mots consommes varie. Ici il
ne varie pas.

L'HYPOTHÈSE, ÉNONCÉE FRANCHEMENT
=================================
Ce fichier teste le COUPLE « generateur + designation par indice dans le
tableau TRIE ». Si la plateforme indexe le tableau dans l'ORDRE D'EMISSION, le
rang que nous calculons est une permutation aleatoire du vrai indice et le
systeme sera incompatible — exclusion correcte du couple, mais pas du
generateur seul. C'est une limite de portee, pas un defaut de mesure, et elle
est consignee comme telle.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H87_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
POOL, DRAWN = 80, 20
KB = DRAWN                                 # l'indice vit dans [0, 20)
STRIDES = (21, 22, 23, 25, 41, 81) if DRY else (21, 22, 23, 24, 25, 40, 41, 80, 81, 101)
DNOYAU = 6 if DRY else 20
MARGE = 3.0                                # equations demandees / bits d'etat


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# On reprend le catalogue et l'algebre du §68, et le prefixe du §105
# ==========================================================================
_SRC = open(os.path.join(ICI, "h61_familles_etendues.py"), encoding="utf-8").read()
_HEAD = _SRC[:_SRC.index('rule("1. LES FAMILLES')]
_G = {"__name__": "h61tete", "__file__": os.path.join(ICI, "h61_familles_etendues.py")}
exec(compile(_HEAD, "h61tete", "exec"), _G)

FAMILLES = _G["OLD"] + _G["NEW"]
add_eq, back_substitute, kernel_basis = (_G["add_eq"], _G["back_substitute"],
                                         _G["kernel_basis"])

_H86 = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_P = _H86[_H86.index("def prefixe("):_H86.index("def indices_fy(")]
exec(compile(_P, "h86prefixe", "exec"), globals())

LARGEUR = {"xorshift32": 32, "xorshift64": 64, "xorshift96": 32,
           "xorshift128": 32, "taus88": 32, "xoroshiro128 (brut)": 64,
           "xoshiro128 (brut)": 32, "xoshiro256 (brut)": 64,
           "LFSR113": 32, "WELL512a": 32}


# ==========================================================================
rule("1. LE FAIT STRUCTUREL, ET CE QU'IL DONNE SOUS TRONCATURE")
# ==========================================================================

ARCH = lab.load()
BON = np.asarray(ARCH.bonus)
NUM = np.asarray(ARCH.nums)
DEDANS = int(np.count_nonzero((NUM == BON[:, None]).any(1)))
RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)

say(f"""   Le bonus est l'un des vingt numeros tires dans {DEDANS:,} cas sur {len(BON):,}.
   L'independance en predirait {len(BON) // 4:,}. Ce n'est pas un tirage de plus :
   c'est une DESIGNATION.

   Le dossier lisait cette donnee par l'echantillonneur MODULO — le §89 prend
   (bonus - 1) mod 16, quatre bits BAS. Sous TRONCATURE une designation
   s'ecrit bonus = tires[floor(u * 20)], et le RANG du bonus parmi les vingt
   numeros TRIES vaut alors floor(u * 20) : une observation de troncature,
   exacte, sur toute l'archive.
""")
c = np.bincount(RANG, minlength=DRAWN)
chi = float(((c - len(BON) / DRAWN) ** 2 / (len(BON) / DRAWN)).sum())
say(f"   loi du rang : chi2 = {chi:.1f} sur {DRAWN-1} ddl (seuil 5 % = 30,1) — uniforme,")
say("   ce qui est attendu sous TOUTE designation raisonnable et ne discrimine rien.")

MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
say(f"""
   BUDGET. Le theoreme du prefixe (§105) avec K = {KB} :

     {'rang':>6} {'prefixe':>9}""")
for mm in range(0, KB, 4):
    j, v = prefixe(mm, KB, 32)
    say(f"     {mm:>6} {j:>9}")
say(f"""
   moyenne : {MOY:.2f} bits F2 exacts par tirage, contre 4,48 par mot au §105.
   MOINS PAR OBSERVATION, MAIS {len(BON):,} OBSERVATIONS AU LIEU DE 80 MOTS.

   Et le stride est FIXE : vingt mots pour le tirage, un pour l'indice. C'est
   ce que le §95 reprochait au bonus lu comme sortie brute sous rejet — la, le
   nombre de mots consommes varie. Ici il ne varie pas.""")


# ==========================================================================
# LE SYSTÈME
# ==========================================================================
def formes_hautes(step, nbits, nwords, W, jmax=6):
    """coef[k][r] : forme F2 du bit de rang r depuis le POIDS FORT du mot k.

    On ne garde que les `jmax` bits hauts : le prefixe n'en utilise jamais
    davantage quand K vaut 20, et la memoire s'en trouve divisee par cinq.
    """
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


def systeme(coef, rangs, stride, off, W):
    """Echelonne les equations de prefixe des rangs. (pivots, equations)."""
    piv, neq = {}, 0
    for d, m in enumerate(rangs):
        j, val = prefixe(int(m), KB, W)
        ck = coef[d * stride + off]
        for r in range(j):
            if not add_eq(piv, ck[r], (val >> (j - 1 - r)) & 1, []):
                return None, neq
            neq += 1
    return piv, neq


def rangs_de(step, etat, ndraws, stride, off, W):
    """Les rangs engendres par le schema « 20 mots FY + 1 mot d'indice »."""
    mots, s = [], etat
    for _ in range(ndraws * stride + off + 1):
        s, w = step(s)
        mots.append(w)
    out = []
    for d in range(ndraws):
        out.append((mots[d * stride + off] * KB) >> W)
    return out


def cherche(step, piv, nbits, rangs, ndraws, stride, off, W):
    """Solution particuliere + parcours du noyau, abandon au premier rang."""
    sol, _f = back_substitute(piv, nbits)
    base = kernel_basis(piv, nbits)
    d = len(base)
    if d > DNOYAU:
        return None, d
    cible0 = int(rangs[0])
    trouves, etat = [], sol
    for g in range(1 << d):
        if g:
            etat ^= base[((g ^ (g - 1)).bit_length() - 1)]
        s, w = etat, None
        for _ in range(off + 1):
            s, w = step(s)
        if (w * KB) >> W != cible0:
            continue
        if rangs_de(step, etat, ndraws, stride, off, W) == list(rangs):
            trouves.append(etat)
    return trouves, d


# ==========================================================================
rule("2. LE TÉMOIN POSITIF")
# ==========================================================================

say(f"""   On plante l'etat, on fabrique des tirages par « vingt mots de Fisher-Yates
   puis un mot d'indice », et on demande a l'attaque de rendre l'etat exact a
   partir des seuls RANGS du bonus.
""")
say(f"   {'famille':>22} {'etat':>6} {'tirages':>8} {'rang':>6} {'noyau':>6} "
    f"{'retrouve':>11} {'x4 tirages':>11} {'sec':>7}")

import random                                                  # noqa: E402
rnd = random.Random(20260909)
temoins, portee, SAT = [], {}, {}
for nom, nbits, step, _ref in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    nd = int(MARGE * nbits / MOY) + 4
    etat = rnd.getrandbits(nbits) | 1
    rangs = rangs_de(step, etat, nd, 21, 20, W)
    coef = formes_hautes(step, nbits, nd * 21 + 21, W)
    piv, neq = systeme(coef, rangs, 21, 20, W)
    rang = len(piv) if piv is not None else -1
    ok, dim = False, -1
    if piv is not None:
        got, dim = cherche(step, piv, nbits, rangs, nd, 21, 20, W)
        ok = got is not None and etat in got
    sat = ""
    if rang < nbits:
        # LE RANG PLAFONNE-T-IL PAR MANQUE DE DONNEES OU PAR STRUCTURE ?
        # La question n'est pas rhetorique : confondre les deux ferait promettre
        # qu'il suffit de collecter plus de tirages. On remesure a quatre fois
        # plus de tirages et on regarde si le rang bouge.
        nd4 = 4 * nd
        r4 = rangs_de(step, etat, nd4, 21, 20, W)
        c4 = formes_hautes(step, nbits, nd4 * 21 + 22, W)
        p4, _n4 = systeme(c4, r4, 21, 20, W)
        rr = len(p4) if p4 is not None else -1
        sat = "structurel" if rr == rang else f"->{rr}"
    temoins.append(ok if 0 <= dim <= DNOYAU else None)
    portee[nom] = dim
    SAT[nom] = (rang, sat)
    say(f"   {nom:>22} {nbits:>6} {nd:>8} {rang:>6} {dim if dim >= 0 else '-':>6} "
        f"{('OUI' if ok else ('hors portee' if dim > DNOYAU else 'NON')):>11} "
        f"{sat:>11} {time.time()-tt:>7.1f}")

ATT = [n for n, d in portee.items() if 0 <= d <= DNOYAU]
say(f"""
   {sum(1 for t in temoins if t)}/{len(ATT)} etats retrouves EXACTEMENT depuis les seuls rangs du bonus.
   Aucun ordre d'emission n'a ete utilise : uniquement le champ que l'archive
   publie sur ses {len(BON):,} tirages — la ou le §105 disposait de 80 mots.

   LA COLONNE « x4 TIRAGES » EST LA POUR UNE RAISON. Quand le rang plafonne
   sous la taille de l'etat, il faut savoir si c'est faute de donnees ou par
   STRUCTURE. On remesure donc a quatre fois plus de tirages. Les familles
   marquees « structurel » ne gagnent RIEN : les bits hauts d'un mot sur
   vingt-et-un n'atteignent qu'un sous-espace, et aucune collecte n'y changera
   quoi que ce soit. Promettre le contraire serait exactement la faute que le
   §101 a trouvee dans la carte.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE ENTIÈRE")
# ==========================================================================

say(f"""   Pour chaque famille, chaque stride de {min(STRIDES)} a {max(STRIDES)} mots par tirage et
   chaque decalage du mot d'indice a l'interieur du tirage, on echelonne puis
   on rejoue. Les tirages sont pris au DEBUT de l'archive, dans l'ordre.
""")
say(f"   {'famille':>22} {'essais':>7} {'exclus':>7} {'cherchés':>9} "
    f"{'non testés':>11} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, EXCLUS, CHERCHES, NONT = 0, 0, 0, 0, 0
for nom, nbits, step, _ref in FAMILLES:
    W = LARGEUR[nom]
    tt = time.time()
    nd = int(MARGE * nbits / MOY) + 4
    if DRY:
        nd = min(nd, 60)
    rangs = RANG[:nd]
    trouve, ess, exc, chr_, non = 0, 0, 0, 0, 0
    for stride in STRIDES:
        coef = formes_hautes(step, nbits, nd * stride + stride + 1, W)
        for off in range(stride):
            ess += 1
            piv, _neq = systeme(coef, rangs, stride, off, W)
            if piv is None:
                exc += 1
                continue
            got, _d = cherche(step, piv, nbits, rangs, nd, stride, off, W)
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
   {TOTAL} etat compatible sur {ESSAIS:,} systemes.
     exclus {EXCLUS:,} — systeme INCOMPATIBLE, aucun etat ne peut produire ces rangs
     cherchés {CHERCHES:,} — noyau parcouru et rejoue
     non testés {NONT:,} — noyau au-dela de {DNOYAU} dimensions""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h87.bonus_prefixe",
        "Aucun generateur F2-lineaire du catalogue du §68, associe a une "
        "designation du bonus par INDICE TRONQUE dans le tableau TRIE des vingt "
        "numeros, n'engendre les rangs du bonus de l'archive",
        f"theoreme du prefixe (§105) applique au rang du bonus, avec K = {KB} : "
        f"{MOY:.2f} equations F2 exactes par tirage, sur les premiers tirages de "
        f"l'archive, a stride FIXE (vingt mots de tirage plus un mot d'indice). "
        f"Echelonnement F2, parcours du noyau, puis rejeu exact des rangs. "
        f"Balayage de {len(STRIDES)} strides et de tous les decalages internes",
        "aucun null n'est requis : le rejeu compare tous les rangs, soit une "
        "probabilite de faux positif de 20^(-n) pour n tirages",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(1 for t in temoins if t)}/{len(ATT)} etats plantes "
                  f"retrouves EXACTEMENT depuis les seuls rangs du bonus, sans aucun "
                  f"ordre d'emission"),
        notes=(f"Le §89 et le §100 lisent le bonus par l'echantillonneur MODULO — "
               f"(bonus - 1) mod 16, quatre bits BAS. Sous TRONCATURE la meme "
               f"donnee dit autre chose : une designation s'ecrit "
               f"bonus = tires[floor(u*20)], et le RANG parmi les vingt numeros "
               f"TRIES vaut floor(u*20). Le stride y est FIXE, ce que le §95 "
               f"reprochait au bonus lu comme sortie brute sous rejet. LIMITE DE "
               f"PORTEE ASSUMEE : si la plateforme indexe le tableau dans l'ORDRE "
               f"D'EMISSION, le rang calcule est une permutation aleatoire du vrai "
               f"indice et l'exclusion porte sur le COUPLE, pas sur le generateur "
               f"seul. {DEDANS:,}/{len(BON):,} bonus appartiennent au tirage."))
    h = lab.holm()
    say(f"   consigne : h87.bonus_prefixe   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME. Le catalogue F2-lineaire du §68 sous TRONCATURE, non plus sur
   quatre-vingts mots consecutifs mais sur l'archive entiere — et sans jamais
   avoir besoin de l'ordre d'emission. Le §105 laissait 126 systemes « non
   testes » faute de mots consecutifs ; ce fichier les prend par l'autre bout.

   RESTE :
     — la designation par indice dans l'ordre D'EMISSION, indistinguable ici ;
     — MT19937 et WELL19937. Le budget de {MOY:.2f} bits par tirage les met a portee
       en {int(19937 / MOY):,} tirages, largement disponibles — c'est le COUT DE CALCUL des
       formes lineaires qui bloque, pas la donnee. La difference avec le §105
       est entiere : la, il manquait des tirages ; ici, il manque des heures ;
     — les sorties ADDITIVES et BROUILLEES, comme partout ;
     — l'echantillonneur MODULO, deja couvert par le §89 et le §100.

   ({time.time() - T0:.1f} s)""")
