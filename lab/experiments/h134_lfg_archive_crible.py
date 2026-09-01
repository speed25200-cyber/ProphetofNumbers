"""h134 — l'archive TRIÉE contre le Fibonacci retardé de la glibc, par ses bits
BAS : crible des 2^{5L} états bas mod 32 (tous les trinômes primitifs de
degré L ≤ 7, TYPE_1 = (3, 7) compris), puis RELÈVEMENT des 27L bits hauts par
la chaîne mod 5 et le CVP (§154, THEORIE_ETAT §7.8), sous les trois schémas.

CE QUE LE §154 LAISSAIT
=======================
Le §154 relève un état bas connu (r_i mod 32) en état 32 bits à partir de
tirages TRIÉS : la chaîne mod 5 en programmation dynamique (paquets, fusions),
puis un CVP sur ~360 mots (mesure de Mahler). Il restait à OBTENIR l'état bas
sur l'archive. Or l'archive triée ne donne que (v−1) mod 16 = les bits 1..4
de chaque mot r_i (v = ((r_i >> 1) mod 80) + 1, 80 = 16·5), et la récurrence
r_i = r_{i−K} + r_{i−L} mod 2^32 est AUTONOME modulo 32 : l'état bas vit dans
2^{5L} — 2^35 pour L = 7, énumérables.

LE CRIBLE VECTORISÉ
===================
Chaque mot bas est une forme linéaire r_i = Σ_j α_ij r_j mod 32 des L mots
initiaux (α par la récurrence) ; l'énumération est L boucles imbriquées à
sommes courantes, les seize premières formes sont testées d'un coup en
registre vectoriel (1,6 % passent), les seize suivantes sur les rescapés
(2,6·10⁻⁴), le reste en scalaire. Trois schémas :
  mode 0 — Fisher-Yates partiel par modulo, pas 20..24, les deux mots SÛRS
           0 et 16 de chaque tirage (lemme du §152) ;
  mode 1 — Collections.shuffle, vingt dernières cases, pas 79..80, le mot 16
           (i = 63, module 64) et le mot 0 ;
  mode 2 — REJET des doublons mot à mot, σ = 20..48 mots par tirage et 0..4
           mots perdus entre deux tirages.

LE LEMME DES COURSES (mode 2)
=============================
Sous le rejet, l'ensemble des départs possibles du tirage d est un INTERVALLE
[a, b]. Une course de R ≥ 20 mots permis à partir de s couvre les départs
s..min(b, s + R − 20), et la réunion de leurs départs suivants est l'intervalle
[s + 20, min(s + R, b' + 48) + P]. La récursion sur les intervalles remplace le
branchement (P+1)^n de la définition mot à mot ; l'autotest vérifie l'égalité
des deux (mêmes survivants, mêmes empreintes) sur 2^20 états.

TÉMOINS
=======
`tools/lfg_low_sieve.c --selftest 5` (7/7) : modulo pas 20 et 22, shuffle pas
79 — l'état planté est seul survivant ; rejet avec mots perdus plantés — le
vrai est là, tous les survivants sont ses décalés f^k(vrai), les structurels
sont tous présents ; deux fenêtres aléatoires ne rendent rien ; vectorisé
contre scalaire — mêmes comptes, mêmes empreintes. Puis, DANS LE RÉGIME DE
L'ARCHIVE (204 tirages, masques identiques) : un état 32 bits planté sous le
rejet avec 0..4 mots perdus entre tirages est criblé (2^35), ses survivants
bas sont relevés par `lab.lfg_releve.releve_etat(perdus_inter=4)` sur les
nd = 2,5·n*/25 premiers tirages (8 à 30), et l'état relevé RÉGÉNÈRE les 204 —
il prédit ceux qu'il n'a pas vus. Réglages fixés sur ces témoins AVANT la
consignation : à L ≤ 3 la chaîne mod 5 produisait des faux jumeaux (δ ≡ 0
mod 10 sans δ = 0, probabilité 5^-L) que la clé ne refusionnait jamais —
une liste de représentants par clé les refusionne ; les états DÉGÉNÉRÉS 16·e
(résidus 0 et 8 seulement) survivent au crible d'un témoin de période 112,
ils sont comptés à part.

Il TESTE l'archive : il consigne au registre.
"""

import os
import random
import subprocess
import sys
import time
from math import comb, log2

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402
from lfg_releve import (mahler, mots_necessaires, regenere, regenere_tirages,   # noqa: E402
                        releve_etat, suite_basse)

T0 = time.time()
DRY = os.environ.get("H134_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H134_TMP", "/tmp")
POOL, DRAWN, SIGMAX = 80, 20, 48
PERDUS_REJET = 4
MOTS_PAR_TIRAGE = 80 * sum(1 / d for d in range(61, 81)) + PERDUS_REJET / 2   # ≈ 25.0 mots
ND_MAX = 30


def nd_releve(K, L):
    """Tirages donnés à la chaîne mod 5 : 2,5 fois n*(K, L) mots, au plus ND_MAX.
    Fixé sur les témoins AVANT la consignation : (3, 4) échoue à 8 tirages et
    passe à 12 ; (3, 7) échoue à 12 et passe à 20 ; le facteur 2,5 couvre les deux."""
    return int(min(ND_MAX, -(-2.5 * mots_necessaires(K, L) // MOTS_PAR_TIRAGE)))


# trinômes primitifs x^L - x^{L-K} - 1 de degré L <= 7 : (K, L, nom glibc)
TRINOMES = [(1, 2, ""), (1, 3, ""), (2, 3, ""), (1, 4, ""), (3, 4, ""), (2, 5, ""), (3, 5, ""),
            (1, 6, ""), (5, 6, ""), (1, 7, ""), (3, 7, "TYPE_1"), (4, 7, ""), (6, 7, "")]
PAS = ([(0, s) for s in (20, 21, 22, 23, 24)] + [(1, s) for s in (79, 80)]
       + [(2, PERDUS_REJET)])
if DRY:
    TRINOMES = [t for t in TRINOMES if t[1] <= 4]
    PAS = [(0, 20), (1, 79), (2, PERDUS_REJET)]


def libelle(mode, pas):
    return {0: f"modulo pas {pas}", 1: f"shuffle pas {pas}",
            2: f"rejet, {pas} perdus max"}[mode]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "lfg_low_sieve_h134")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_low_sieve.c")],
               check=True, capture_output=True)
ENV = dict(os.environ, SWEEP_THREADS=os.environ.get("SWEEP_THREADS", "4"))


def crible(K, L, mode, pas, fmasq, n):
    """Lance l'outil ; rend (liste des états bas [r_0..r_{L-1}] mod 32, dernière ligne)."""
    p = subprocess.run([BIN, str(K), str(L), str(mode), str(pas), fmasq, str(n)],
                       capture_output=True, text=True, timeout=36000, env=ENV)
    assert p.returncode == 0, (K, L, mode, pas, p.stderr)
    lignes = p.stdout.strip().split("\n")
    bas = [int(l.split()[1]) for l in lignes if l.startswith("BAS")]
    return [[(b >> (5 * j)) & 31 for j in range(L)] for b in bas], lignes[-1]


def masques(ens):
    m = np.zeros(len(ens), dtype="<u2")
    for i, S in enumerate(ens):
        x = 0
        for v in S:
            x |= 1 << ((v - 1) % 16)
        m[i] = x
    return m


def tirage_rejet(seq, p):
    """Tirage par rejet à partir du mot p : (numéros triés, position suivante)."""
    vus = []
    while len(vus) < DRAWN:
        v = (seq[p] >> 1) % POOL + 1
        if v not in vus:
            vus.append(v)
        p += 1
    return sorted(vus), p


def tirage_modulo(seq, p):
    """Fisher-Yates partiel par modulo, vingt mots à partir de p (convention de l'autotest)."""
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        j = k + (seq[p + k] >> 1) % (POOL - k)
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return sorted(out), p + DRAWN


def degenere(bas):
    """Etat bas 16·e, e dans F_2^L : residus 0 et 8 seulement (dont l'etat nul)."""
    return all(x % 16 == 0 for x in bas)


def decalage(bas_a, bas_b, K, L, kmax=None):
    """k tel que bas_b = f^k(bas_a) mod 32 (|k| <= kmax), ou None. Par defaut kmax
    couvre la periode (2^L - 1) x 16 du bas : tout etat du cycle de bas_a est atteint."""
    if kmax is None:
        kmax = (2 ** L - 1) * 16 + SIGMAX
    n = 2 * kmax + L + 1
    av = suite_basse(bas_a, K, L, n)
    # en arrière : r_{i-L} = r_i - r_{i-K}
    ar = list(bas_a)
    for _ in range(kmax):
        ar.insert(0, (ar[L - 1] - ar[L - 1 - K]) & 31)
    tout = ar[:kmax] + av                       # tout[kmax + i] = f^i(bas_a)[0]
    for k in range(-kmax, kmax + 1):
        if tout[kmax + k:kmax + k + L] == list(bas_b):
            return k
    return None


# ==========================================================================
rule("1. LE THÉORÈME : 2^{5L} BAS ÉNUMÉRABLES, 27L HAUTS RELEVÉS")
# ==========================================================================

P_VIDE = comb(75, 20) / comb(80, 20)
FILTRE = 1 - P_VIDE
BITS_2 = -2 * log2(FILTRE)
SURV_REJET = sum(FILTRE ** s for s in range(DRAWN, SIGMAX + 1)) * (PERDUS_REJET + 1)
BITS_REJET = -log2(SURV_REJET)

say(f"""   r_i = r_(i-K) + r_(i-L) mod 2^32 est autonome modulo 32 ; l'archive triee
   donne (v-1) mod 16 = bits 1..4 de r_i. Etat bas : 5L bits, 2^35 au plus pour
   L <= 7 ; un residu est permis avec probabilite rho = {FILTRE:.4f}.
   Pas constant, deux mots surs par tirage : {BITS_2:.3f} bit/tirage ; sous le rejet
   (sigma = 20..{SIGMAX}, 0..{PERDUS_REJET} perdus) un faux survit avec probabilite {SURV_REJET:.4f}
   ({BITS_REJET:.2f} bits/tirage). Le releve (§154) demande n* = L(27 - log2 5)/log2 M(f)
   mots ; la chaine mod 5 recoit nd = 2,5 n* / {MOTS_PAR_TIRAGE:.1f} tirages (au plus {ND_MAX}).

       {'K':>2} {'L':>2} {'bas':>5} {'hauts':>6} {'M(f)':>7} {'n*':>5} {'nd':>3}  trinome""")
for K, L, nom in TRINOMES:
    m = mahler(K, L)
    say(f"       {K:>2} {L:>2} {'2^%d' % (5*L):>5} {'2^%d' % (27*L):>6} {m:>7.4f} "
        f"{mots_necessaires(K, L):>5.0f} {nd_releve(K, L):>3}  x^{L}-x^{L-K}-1 {nom}")

st = subprocess.run([BIN, "--selftest", "5"], capture_output=True, text=True, env=ENV)
AUTO = st.stdout.strip().split("\n")[-1]
say(f"""
   temoin de l'outil (L = 5, K = 2, 60 tirages) : {AUTO}
   — modulo pas 20 et 22, shuffle pas 79 : l'etat plante est seul survivant ;
   rejet avec perdus plantes : le vrai est la, tous les survivants sont ses
   decales f^k(vrai), les structurels sont tous presents ; deux fenetres
   aleatoires ne rendent rien ; vectorise = scalaire (comptes et empreintes).""")
assert AUTO.endswith("7/7"), AUTO


# ==========================================================================
rule("2. L'ARCHIVE : LES MASQUES")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
coupe = np.flatnonzero(np.diff(TS) != 300)
deb = np.r_[0, coupe + 1]
fin = np.r_[coupe + 1, len(TS)]
k = int(np.argmax(fin - deb))
NJ = int(fin[k] - deb[k])
ENS = [NUM[deb[k] + i].tolist() for i in range(NJ)]
ID0 = int(IDS[deb[k]])
SUIVANT = NUM[deb[k] + NJ].tolist() if deb[k] + NJ < len(NUM) else None
if DRY:
    NJ = 60
    ENS = ENS[:NJ]

MASQ = masques(ENS)
FMASQ = os.path.join(TMP, "h134_masques.u16")
MASQ.tofile(FMASQ)
NB_PERMIS = np.array([bin(int(m)).count("1") for m in MASQ])

say(f"""   {NJ} tirages CONSECUTIFS (espaces de 300 s), identifiants {ID0} a
   {ID0 + NJ - 1}. Residus mod 16 permis : {NB_PERMIS.mean():.2f} sur 16 en moyenne
   (attendu {16*FILTRE:.2f}), filtre mesure {NB_PERMIS.mean()/16:.3f}.

   Survivants attendus par hasard pour L = 7 : 2^35 x {FILTRE:.3f}^(2 x {NJ}) =
   {2**35 * FILTRE**(2*NJ):.1e} a pas constant, 2^35 x {SURV_REJET:.3f}^{NJ} = {2**35 * SURV_REJET**NJ:.1e}
   sous le rejet. Un survivant serait un evenement.""")


# ==========================================================================
rule("3. TÉMOINS PLANTÉS DANS LE RÉGIME DE L'ARCHIVE")
# ==========================================================================

say(f"""   Pour chaque trinome : un etat 32 bits au hasard, {NJ} tirages par REJET
   avec t mod 5 mots perdus entre deux tirages (0..4), masques au format de
   l'archive, crible 2^(5L) en mode 2, relevement de chaque survivant bas sur
   les nd premiers tirages, verification sur les {NJ}. Pour TYPE_1 aussi :
   modulo pas 20 (le bas est trouve, il n'est pas releve : le Fisher-Yates
   n'a pas de chaine mod 5). `decal' : tous les survivants sont des decales
   f^k(vrai) du cycle du vrai, ou DEGENERES (16·e, residus 0 et 8 seulement :
   ils survivent des que 0 et 8 sont dans les {NJ} masques, ce que la periode
   (2^L - 1) x 16 du bas impose pour L <= 3 — sur l'archive c'est {FILTRE:.2f}^{NJ}).

       {'K':>2} {'L':>2} {'mode':>5} {'nd':>3} {'surv':>5} {'vrai':>5} {'decal':>6} {'degen':>5} {'releves':>8} {'regen 204':>10} {'sec':>6}""")

FMASQ_T = os.path.join(TMP, "h134_temoin.u16")
TEMOINS = []
TEMOINS_OK = True
rng = random.Random(134)
for K, L, nom in TRINOMES:
    if DRY and L < 4:
        continue
    for mode in ((2, 0) if nom == "TYPE_1" else (2,)):
        t0 = time.time()
        etat = [rng.getrandbits(32) for _ in range(L)]
        NW = 60 * NJ + L + 200
        seq = regenere(etat, K, L, NW)
        ens, p = [], 0
        for t in range(NJ):
            if mode == 2:
                S, p = tirage_rejet(seq, p)
                p += t % (PERDUS_REJET + 1)
            else:
                S, p = tirage_modulo(seq, p)
            ens.append(S)
        masques(ens).tofile(FMASQ_T)
        pas = PERDUS_REJET if mode == 2 else 20
        bas_vrai = [x & 31 for x in etat]
        surv, _ = crible(K, L, mode, pas, FMASQ_T, NJ)
        vrai_la = bas_vrai in surv
        nd = nd_releve(K, L)
        decal = [decalage(bas_vrai, b, K, L) for b in surv]
        n_degen = sum(1 for b in surv if degenere(b))
        tous_decales = all(d is not None or degenere(b) for d, b in zip(decal, surv))
        releves, regen = [], 0
        if mode == 2:
            for b in surv:
                sts, _ = releve_etat(b, ens[:nd], K, L, perdus_inter=PERDUS_REJET)
                for s in sts:
                    if s not in releves:
                        releves.append(s)
            regen = sum(regenere_tirages(regenere(s, K, L, NW), ens, PERDUS_REJET)
                        for s in releves)
            ok = vrai_la and tous_decales and etat in releves and regen == len(releves) >= 1
        else:
            ok = vrai_la and surv == [bas_vrai]
        TEMOINS_OK &= ok
        TEMOINS.append((K, L, mode, len(surv), vrai_la, tous_decales, n_degen,
                        len(releves), regen, nd, ok))
        say(f"       {K:>2} {L:>2} {mode:>5} {nd:>3} {len(surv):>5} {str(vrai_la):>5} "
            f"{str(tous_decales):>6} {n_degen:>5} {len(releves) if mode == 2 else '-':>8} "
            f"{regen if mode == 2 else '-':>10} {time.time()-t0:>6.1f}"
            + ("" if ok else "   ECHEC"))
say(f"""
   temoins : {'TOUS CONFORMES' if TEMOINS_OK else 'ECHEC'} — sous le rejet, le vrai etat bas survit,
   les survivants sont ses decales (ou degeneres), l'etat 32 bits plante est parmi
   les releves et chaque releve regenere les {NJ} tirages (les {NJ} - nd non vus sont PREDITS).""")
assert TEMOINS_OK


# ==========================================================================
rule("4. LE CRIBLE DE L'ARCHIVE, PUIS LE RELÈVEMENT")
# ==========================================================================

say(f"""   {len(TRINOMES)} trinomes x {len(PAS)} modes = {len(TRINOMES) * len(PAS)} cribles contre les {NJ} masques.
   Survivant en mode 2 : releve par la chaine mod 5 + CVP sur nd tirages, l'etat
   devant regenerer les {NJ}. Survivant en mode 0/1 : rapporte comme bas non releve.

       {'K':>2} {'L':>2} {'mode':>5} {'param':>5} {'crible':>7} {'bas':>5} {'releves':>8} {'sec':>7}""")

JOURNAL = os.path.join(TMP, "h134_journal.txt")
DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 4:
            DEJA[t[0]] = (int(t[1]), int(t[2]), t[3:])
    say(f"   reprise : {len(DEJA)} cribles deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")

LIG, TROUV = [], []
for K, L, nom in TRINOMES:
    NW = 60 * NJ + L + 200
    for mode, pas in PAS:
        cle = f"{K},{L},{mode},{pas},{NJ}"
        t0 = time.time()
        if cle in DEJA:
            nb, nrel, etats = DEJA[cle]
            etats = [e for e in etats if e != "-"]
        else:
            surv, _ = crible(K, L, mode, pas, FMASQ, NJ)
            nb = len(surv)
            etats = []
            if mode == 2:
                for b in surv[:64]:
                    sts, _ = releve_etat(b, ENS[:nd_releve(K, L)], K, L,
                                         perdus_inter=PERDUS_REJET)
                    for s in sts:
                        if regenere_tirages(regenere(s, K, L, NW), ENS, PERDUS_REJET):
                            etats.append("etat_" + "_".join(str(x) for x in s))
                        else:
                            etats.append("releve_" + "_".join(str(x) for x in s)
                                         + f"_ne_regenere_pas_les_{NJ}")
                nrel = sum(1 for e in etats if e.startswith("etat_"))
            else:
                nrel = 0
                for b in surv[:64]:
                    etats.append("bas_" + "_".join(str(x) for x in b) + "_non_releve_FY")
            jr.write(f"{cle} {nb} {nrel} {' '.join(etats) if etats else '-'}\n")
            jr.flush()
        LIG.append((K, L, mode, pas, 5 * L, nb, nrel))
        for e in etats:
            TROUV.append((K, L, mode, pas, e))
        say(f"       {K:>2} {L:>2} {mode:>5} {pas:>5} {'2^%d' % (5*L):>7} {nb:>5} {nrel:>8} "
            f"{time.time()-t0:>7.1f}")

TOT_BAS = sum(l[5] for l in LIG)
N_ETATS = sum(1 for t in TROUV if t[4].startswith("etat_"))
say(f"""
   {TOT_BAS} candidat bas survivant sur {len(LIG)} cribles, {N_ETATS} etat complet releve.""")
for K, L, mode, pas, e in TROUV:
    say(f"     !! x^{L}-x^{L-K}-1 {libelle(mode, pas)} : {e}")
    if e.startswith("etat_"):
        s = [int(x) for x in e.split("_")[1:]]
        seq = regenere(s, K, L, 60 * NJ + L + 200)
        # prediction du tirage suivant la fenetre : tous les departs vivants apres les NJ tirages
        say(f"        tirage suivant predit (premier depart) : {tirage_rejet(seq, 0)[0]}")
        if SUIVANT is not None:
            say(f"        tirage suivant reel de l'archive (id {ID0 + NJ}) : {SUIVANT}")
if not TROUV:
    say(f"""     AUCUN. Les {len(TRINOMES)} trinomes primitifs de degre <= 7 — TYPE_1 (3, 7) de la glibc
     compris —, soit 2^{5*max(t[1] for t in TRINOMES)} etats bas au plus, sont exclus sur l'archive triee
     sous chacun des {len(PAS)} modes : {'; '.join(libelle(m, p) for m, p in PAS)}.
     Pour TYPE_1 c'est l'ENSEMBLE des 2^224 etats qui est exclu : tout etat a un
     bas, et aucun bas ne survit.

   CE QUI RESTE HORS DU CRIBLE : TYPE_2 (1, 15), TYPE_3 (3, 31), TYPE_4 (1, 63)
   — 2^75, 2^155, 2^315 etats bas, hors enumeration (frontiere du §7.8) ; la
   sortie par troncature (x * 80) >> 32 ; plus de {PERDUS_REJET} mots perdus entre
   deux tirages ; les vingt premieres cases d'un shuffle complet.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h134.lfg_low_crible",
        "Aucun etat d'aucun Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod "
        "2^32 a sortie r >> 1 de degre L <= 7 — les treize trinomes primitifs, dont "
        "TYPE_1 (K = 3, L = 7) de la glibc random() — n'engendre les tirages TRIES "
        "de l'archive sous aucun des trois schemas : Fisher-Yates partiel par "
        "modulo aux pas 20 a 24, Collections.shuffle vingt dernieres cases aux pas "
        "79 a 80, rejet des doublons v = ((r >> 1) mod 80) + 1 jusqu'a vingt "
        f"distincts avec 0 a {PERDUS_REJET} mots perdus entre deux tirages. L'attaque "
        "crible les 2^(5L) etats BAS mod 32 — (v-1) mod 16 = les bits 1..4 de r_i, "
        "et la recurrence est autonome mod 32 — en lisant les deux mots surs a pas "
        "constant et tous les mots sous le rejet (lemme des courses : recursion sur "
        "des intervalles de departs), puis releve les 27L bits hauts de chaque "
        "survivant par la chaine mod 5 en programmation dynamique et un CVP "
        "(§154), l'etat releve devant regenerer les tirages. Le design a ete "
        "fixe AVANT cette consignation sur des temoins plantes, jamais sur l'archive",
        "nombre d'etats complets (32 bits x L) compatibles, obtenus en criblant "
        "les bits bas puis en relevant les bits hauts, l'etat devant regenerer "
        f"l'ENSEMBLE des {NJ} tirages tries de la fenetre depuis {ID0}",
        f"aucun null n'est requis : un candidat bas survit a un tirage avec "
        f"probabilite {FILTRE:.3f}^2 a pas constant et {SURV_REJET:.3f} sous le rejet, "
        f"donc au plus 2^35 x {FILTRE**2:.3f}^{NJ} = {2**35 * FILTRE**(2*NJ):.1e} faux "
        f"survivants pour le plus large des cribles",
        "conforme si aucun etat complet n'est compatible et qu'aucun candidat "
        "bas ne reste non releve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(TROUV)), p=1.0,
        verdict="conforme" if not TROUV else "ETAT TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} (L = 5 : modulo pas 20 et 22, shuffle "
                  f"pas 79 -> l'etat plante seul survivant ; rejet avec perdus plantes "
                  f"-> le vrai present, tous les survivants decales ; fenetres "
                  f"aleatoires -> rien ; vectorise = scalaire). Dans le regime de "
                  f"l'archive ({NJ} tirages, memes masques) : "
                  + "; ".join(f"x^{L}-x^{L-K}-1 mode {m} : {n} survivants, vrai "
                              f"{'present' if v else 'ABSENT'}, "
                              f"{'tous decales' if d else 'ETRANGERS'}"
                              + (f" ({dg} degeneres)" if dg else "")
                              + (f", {r} releves sur {nd} tirages dont {g} regenerent les {NJ}"
                                 if m == 2 else "")
                              for K, L, m, n, v, d, dg, r, g, nd, ok in TEMOINS)),
        notes=(f"L'ARCHIVE TRIEE CONTRE TYPE_1 PAR SES BITS BAS : crible 2^(5L) mod 32 "
               f"(vectorise, formes lineaires des L mots initiaux, {len(LIG)} cribles) "
               f"puis relevement 27L bits (chaine mod 5 + CVP, §154, n* = "
               f"{mots_necessaires(3, 7):.0f} mots pour TYPE_1). {NJ} tirages consecutifs "
               f"depuis {ID0}, filtre mesure {NB_PERMIS.mean()/16:.3f}. {TOT_BAS} candidat "
               f"bas, {N_ETATS} etat releve. LEMME DES COURSES : sous le rejet les "
               f"departs possibles du tirage d forment un intervalle ; une course de R "
               f">= 20 mots permis depuis s couvre les departs s..min(b, s+R-20) et "
               f"leurs departs suivants forment [s+20, min(s+R, b'+48)+P] ; la "
               f"recursion sur les intervalles remplace le branchement (P+1)^n. "
               f"CHAINE MOD 5 AVEC PERDUS : la cle porte un compteur de mots perdus "
               f"entre tirages (0..{PERDUS_REJET}, classe et residu libres), le "
               f"verificateur memoise les departs vivants. NON COUVERT : TYPE_2/3/4 "
               f"(2^75, 2^155, 2^315 bas), troncature (x*80)>>32, plus de "
               f"{PERDUS_REJET} perdus, vingt premieres cases d'un shuffle."))
    h = lab.holm()
    say(f"   consigne : h134.lfg_low_crible   {len(TROUV)} etat sur {len(LIG)} cribles")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
