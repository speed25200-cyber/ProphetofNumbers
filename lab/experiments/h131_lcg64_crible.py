"""h131 — le crible des bits bas (§149) étendu à la FAMILLE des LCG de module
2^W : musl, newlib, MMIX (deux sorties), glibc TYPE_0, MSVC, l'exemple de la
norme C.

CE QUE LE §149 FAISAIT, ET CE QU'IL LAISSAIT
============================================
Le §149 exclut les 2^48 états de `java.util.Random` en n'en criblant que 2^21,
parce que (i) 80 = 16·5, donc (v−1) mod 16 = les bits r..r+3 de l'état, et
(ii) un LCG de module 2^W est AUTONOME modulo 2^m. Mais java n'est qu'UN LCG.
Le même argument vaut pour TOUT LCG de module une puissance de deux dont la
sortie est un décalage `s >> r` — et c'est ainsi que sont écrits :

    musl     rand()   a = 6364136223846793005, c = 1,  W = 64, sortie s >> 33
    newlib   rand()   même a, c = 1,                   W = 64, (s >> 32) & 0x7fffffff
    MMIX     Knuth    même a, c = 1442695040888963407, W = 64, sortie s >> 32
    MMIX     mot entier  même a et c,                   W = 64, sortie s (r = 0)
    glibc    TYPE_0   a = 1103515245, c = 12345,       W = 31, sortie s
    MSVC     rand()   a = 214013, c = 2531011,         W = 32, (s >> 16) & 0x7fff
    ANSI C   exemple  a = 1103515245, c = 12345,       W = 32, (s >> 16) & 0x7fff

Pour chacun le crible coûte 2^(r+4) et le relèvement 2^(W−r−4) : 2^37 + 2^27
pour musl, 2^36 + 2^28 pour newlib et MMIX, 2^4 + 2^27 pour glibc TYPE_0
(seize candidats bas excluent 2^31 états), 2^20 + 2^12 pour MSVC. Pour le mot
entier de MMIX (r = 0) le crible n'a que SEIZE candidats et le relèvement en
aurait 2^60 : si aucun des seize ne survit, les 2^64 états sont exclus SANS
relèvement ; s'il en survit un, il reste hors de portée et on le dit.

LE SAUT AFFINE
==============
D'un tirage au suivant l'état avance de STRIDE mots ; la récurrence étant
affine, ce saut est UNE multiplication-addition (a^STRIDE, c·Σa^i) : le crible
coûte ~4 opérations par candidat au lieu de ~4·STRIDE.

LES DEUX MOTS SÛRS (lemme, THEORIE_ETAT.md §7.6)
================================================
Dans un Fisher-Yates partiel comme dans un shuffle complet, le numéro visé
par le mot k est SÛREMENT tiré si 16 | k et 16 | (80 − k) : car alors
j_k ≡ x_k (mod 16) quelle que soit la case, et la valeur visée finit dans
une case tirée — au mot k si la case est intacte, au premier mot k' < k qui
l'a visée sinon. Pour k ≤ 19 ce sont les mots 0 et 16, et eux seuls. Le
crible lit donc DEUX mots par tirage (0,744 bit par tirage au lieu de 0,372)
et n'a plus qu'UN survivant structurel par état vrai : celui du mot 0. À un
seul mot il en avait deux — le registre du mot 16 est un FANTÔME, c'est lui
qui faisait « 2 candidats bas » dans les témoins du §149.

LE MODE À REJET, ET LE LEMME DES DÉCALÉS
=========================================
Le §149 déclarait le tirage par rejet des doublons (v = x mod 80 + 1 jusqu'à
vingt distincts) hors du crible, à cause de son pas variable. C'est l'inverse :
sous le rejet, CHAQUE mot du tirage — accepté ou doublon — vaut un numéro de
l'ensemble publié, donc tous les σ ≥ 20 mots sont contraints. Le crible
branche sur la fin du tirage (σ = 20..48) et sur 0..P mots perdus entre deux
tirages : un faux candidat survit à un tirage avec probabilité
Σ_{σ≥20} ρ^σ (P+1) = 0,127 pour P = 4, soit 2,98 bits par tirage — huit fois
le mode à pas constant. Ses survivants structurels sont les registres DÉCALÉS
du vrai flux (mots 0..σ₀−20 du premier tirage, plus des décalages de
probabilité géométrique) — tous des f^k(vrai), aucun étranger.

TÉMOIN
=======
`tools/lcg64_sieve.c --selftest` (6/6) : à un mot, l'état planté est retrouvé
AVEC son fantôme du mot 16 et eux seuls, le relèvement rend l'état exact et
rejette le fantôme ; à deux mots (modulo pas 21, shuffle pas 79) l'état est
seul survivant et se relève exactement ; sous le rejet avec deux mots perdus
plantés, tous les survivants sont des décalés f^k(vrai), les structurels sont
tous présents, le relèvement est exact ; une fenêtre aléatoire ne rend rien
sous le pas constant ni sous le rejet.

Il TESTE l'archive : il consigne au registre.
"""

import os
import subprocess
import sys
import time
from math import comb, log2

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H131_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H131_TMP", "/tmp")
POOL, DRAWN = 80, 20

# (nom, a, c, W, r, masque de sortie, note)
DESIGNS = [
    ("musl rand()", 6364136223846793005, 1, 64, 33, 0, "s >> 33"),
    ("newlib rand()", 6364136223846793005, 1, 64, 32, 0x7FFFFFFF, "(s >> 32) & 0x7fffffff"),
    ("MMIX (Knuth)", 6364136223846793005, 1442695040888963407, 64, 32, 0, "s >> 32"),
    ("MMIX mot entier", 6364136223846793005, 1442695040888963407, 64, 0, 0, "s, les 64 bits"),
    ("glibc TYPE_0", 1103515245, 12345, 31, 0, 0, "s, module 2^31"),
    ("MSVC rand()", 214013, 2531011, 32, 16, 0x7FFF, "(s >> 16) & 0x7fff"),
    ("ANSI C rand()", 1103515245, 12345, 32, 16, 0x7FFF, "(s >> 16) & 0x7fff"),
]
if DRY:
    DESIGNS = DESIGNS[3:]
# mode 0 : Fisher-Yates partiel par modulo, 20 mots + 0..4 perdus (param = pas) ;
# mode 1 : Collections.shuffle, les vingt dernieres cases, 79 mots + 0..1 perdu ;
# mode 2 : rejet des doublons, pas variable, param = mots perdus maximum entre
#          deux tirages (le crible branche sur 0..param)
PERDUS_REJET = 4
PAS = ([(0, s) for s in (20, 21, 22, 23, 24)] + [(1, s) for s in (79, 80)]
       + [(2, PERDUS_REJET)])
if DRY:
    PAS = [(0, 20), (1, 79), (2, 2)]


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


BIN = os.path.join(TMP, "lcg64_sieve_h131")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lcg64_sieve.c")],
               check=True, capture_output=True)
ENV = dict(os.environ, SWEEP_THREADS=os.environ.get("SWEEP_THREADS", "4"))


# ==========================================================================
rule(f"1. LE THÉORÈME, ET LES {len(DESIGNS)} GÉNÉRATEURS QU'IL ATTEINT")
# ==========================================================================

P_VIDE = comb(75, 20) / comb(80, 20)
FILTRE = 1 - P_VIDE                       # rho : un residu mod 16 est permis
BITS_1 = -log2(FILTRE)                    # un mot par tirage
BITS_2 = -2 * log2(FILTRE)                # les deux mots surs, 0 et 16
SIGMAX = 48
SURV_REJET = sum(FILTRE ** s for s in range(DRAWN, SIGMAX + 1)) * (PERDUS_REJET + 1)
BITS_REJET = -log2(SURV_REJET)

say(f"""   Le §149 crible les 2^21 bits bas de java.util.Random et en exclut les 2^48
   etats. L'argument ne doit rien a java : il vaut pour TOUT LCG de module 2^W
   dont la sortie est un decalage s >> r, parce que 80 = 16 x 5 fait de
   (v-1) mod 16 les bits r..r+3 de l'etat, et qu'un LCG mod 2^W est AUTONOME
   modulo 2^(r+4). Crible 2^(r+4), relevement 2^(W-r-4).

   Un residu mod 16 est permis avec probabilite rho = 1 - C(75,20)/C(80,20) =
   {FILTRE:.4f}. Le crible lit les DEUX mots surs de chaque tirage (0 et 16, les
   seuls k <= 19 tels que 16 | k et 16 | 80-k) : {BITS_2:.3f} bit par tirage au
   lieu de {BITS_1:.3f}, et un seul survivant structurel par etat vrai.
   Sous le REJET des doublons, chaque mot du tirage est contraint : le crible
   branche sur sigma = 20..{SIGMAX} et sur 0..{PERDUS_REJET} mots perdus, un faux candidat
   survit a un tirage avec probabilite {SURV_REJET:.4f} — {BITS_REJET:.2f} bits par tirage.

       {'generateur':>16} {'a':>20} {'c':>20} {'W':>3} {'r':>3} {'crible':>7} {'releve':>7}  sortie""")
for nom, a, c, w, r, mk, note in DESIGNS:
    say(f"       {nom:>16} {a:>20} {c:>20} {w:>3} {r:>3} {'2^%d' % (r+4):>7} "
        f"{'2^%d' % (w-r-4):>7}  {note}")

st = subprocess.run([BIN, "--selftest", "40"], capture_output=True, text=True, env=ENV)
AUTO = st.stdout.strip().split("\n")[-1]
say(f"""
   temoin de l'outil (W = 40, r = 13, meme code que W = 64) : {AUTO}
   — a un mot l'etat plante est retrouve AVEC SON FANTOME DU MOT 16 et eux
   seuls, le relevement rend l'etat exact et rejette le fantome ; a deux mots
   (modulo pas 21, shuffle pas 79) il est seul survivant et se releve
   exactement ; sous le rejet (deux mots perdus plantes) tous les survivants
   sont des decales f^k(vrai), les structurels sont tous la, le relevement est
   exact ; une fenetre aleatoire ne rend rien, ni a pas constant ni sous rejet.""")
assert AUTO.endswith("6/6"), AUTO


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

MASQ = np.zeros(NJ, dtype="<u2")
for i, S in enumerate(ENS):
    m = 0
    for v in S:
        m |= 1 << ((v - 1) % 16)
    MASQ[i] = m
FMASQ = os.path.join(TMP, "h131_masques.u16")
MASQ.tofile(FMASQ)
NB_PERMIS = np.array([bin(int(m)).count("1") for m in MASQ])

say(f"""   {NJ} tirages CONSECUTIFS (espaces de 300 s), identifiants {ID0} a
   {int(IDS[deb[k]+NJ-1])}. Residus mod 16 permis : {NB_PERMIS.mean():.2f} sur 16 en moyenne
   (attendu 16 x {FILTRE:.3f} = {16*FILTRE:.2f}), filtre mesure {NB_PERMIS.mean()/16:.3f}.

   Survivants attendus par hasard, deux mots par tirage : 2^(r+4) x {FILTRE:.3f}^(2 x {NJ})
   — pour musl 2^37 x {FILTRE**(2*NJ):.1e} = {2**37 * FILTRE**(2*NJ):.1e} ; sous le rejet
   2^37 x {SURV_REJET:.3f}^{NJ} = {2**37 * SURV_REJET**NJ:.1e}.""")


# ==========================================================================
rule("3. LE CRIBLE, PUIS LE RELÈVEMENT")
# ==========================================================================

say(f"""   Pour chaque generateur et chaque mode : crible des 2^(r+4) bas contre les
   {NJ} masques (deux mots par tirage a pas constant, tous les mots sous rejet),
   puis relevement des 2^(W-r-4) hauts de chaque survivant, qui doit reproduire
   l'ENSEMBLE du tirage {ID0} (filtre 1/C(80,20) = {1/comb(80,20):.1e}). Sous le
   rejet les survivants attendus d'un vrai etat sont ses DECALES f^k(vrai) ; le
   relevement du registre du mot 0 rend l'etat.

       {'generateur':>16} {'mode':>5} {'param':>5} {'crible':>7} {'bas':>5} {'releves':>8} {'sec':>7}""")

JOURNAL = os.path.join(TMP, "h131_journal.txt")
DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 4:
            DEJA[t[0]] = (int(t[1]), int(t[2]), t[3:])
    say(f"   reprise : {len(DEJA)} cribles deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")

LIG, TROUV = [], []
for nom, a, c, w, r, mk, note in DESIGNS:
    for mode, pas in PAS:
        cle = f"{a},{c},{w},{r},{mk},{mode},{pas}"
        t0 = time.time()
        if cle in DEJA:
            nb, nrel, etats = DEJA[cle]
            etats = [e for e in etats if e != "-"]
        else:
            p = subprocess.run([BIN, str(a), str(c), str(w), str(r), str(mk), str(mode),
                                str(pas), FMASQ, str(NJ)],
                               capture_output=True, text=True, timeout=36000, env=ENV)
            assert p.returncode == 0, (cle, p.stderr)
            bas = [int(l.split()[1]) for l in p.stdout.split("\n") if l.startswith("BAS")]
            nb = len(bas)
            etats = []
            NON_RELEVES = []
            if w - r - 4 > 40 and bas:
                NON_RELEVES = bas                     # 2^(W-r-4) hors de portee
                bas = []
            for b in bas[:64]:
                q = subprocess.run([BIN, "--lift", str(a), str(c), str(w), str(r), str(mk),
                                    str(mode), str(b)] + [str(v) for v in ENS[0]],
                                   capture_output=True, text=True, timeout=36000, env=ENV)
                etats += [l.split("=")[1] for l in q.stdout.split("\n")
                          if l.startswith("TROUVE")]
            nrel = len(etats)
            for b in NON_RELEVES:
                etats.append(f"bas_{b}_non_releve_2^{w-r-4}")
            jr.write(f"{cle} {nb} {nrel} {' '.join(etats) if etats else '-'}\n")
            jr.flush()
        LIG.append((nom, mode, pas, r + 4, nb, nrel))
        for e in etats:
            TROUV.append((nom, mode, pas, e))          # etat releve OU bas non releve
        say(f"       {nom:>16} {mode:>5} {pas:>5} {'2^%d' % (r+4):>7} {nb:>5} {nrel:>8} "
            f"{time.time()-t0:>7.1f}")

TOT_BAS = sum(l[4] for l in LIG)
say(f"""
   {TOT_BAS} candidat bas survivant sur {len(LIG)} cribles, {len(TROUV)} etat complet releve.""")
for nom, mode, pas, e in TROUV:
    say(f"     !! {nom} {libelle(mode, pas)} : etat = {e}")
if not TROUV:
    say(f"""     AUCUN. Les {len(DESIGNS)} generateurs — {', '.join(d[0] for d in DESIGNS)},
     soit {', '.join('2^%d' % d[3] for d in DESIGNS)} etats — sont exclus
     sur l'archive sous chacun des {len(PAS)} modes : {'; '.join(libelle(m, p) for m, p in PAS)}
     (Fisher-Yates partiel par modulo jusqu'a quatre appels perdus, shuffle des
     vingt dernieres cases jusqu'a un appel perdu, rejet des doublons jusqu'a
     {PERDUS_REJET} appels perdus entre deux tirages), SANS que l'amorcage soit suppose.

   CE QUI RESTE HORS DU CRIBLE, ET IL FAUT LE DIRE : la sortie par troncature
   (x * 80) >> 32, dont le residu mod 16 depend des bits HAUTS ; les vingt
   PREMIERES cases d'un shuffle complet ; plus de {PERDUS_REJET} appels perdus entre deux
   tirages a rejet ; PCG et tout LCG dont la sortie est permutee ; les
   generateurs F2-lineaires primitifs (xorshift, MT19937), qui n'ont AUCUN
   quotient invariant (Theoreme Q) ; le Fibonacci retarde de la glibc
   (quotient 2^155, hors enumeration).""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h131.lcg64_crible",
        "Aucun etat d'aucun des sept LCG de module 2^W a sortie decalee — musl "
        "rand() (a = 6364136223846793005, c = 1, s >> 33), newlib rand() (meme "
        "a, c = 1, (s >> 32) & 0x7fffffff), MMIX de Knuth (meme a, c = "
        "1442695040888963407, s >> 32 et le mot entier s), glibc TYPE_0 (a = 1103515245, c = 12345, "
        "module 2^31), MSVC rand() (a = 214013, c = 2531011, (s >> 16) & 0x7fff), "
        "l'exemple de la norme C (a = 1103515245, c = 12345, (s >> 16) & 0x7fff) — "
        "n'engendre les tirages de l'archive, sous aucun des trois schemas : "
        "Fisher-Yates partiel par modulo aux pas 20 a 24 (jusqu'a quatre appels "
        "perdus), Collections.shuffle vingt dernieres cases aux pas 79 a 80 "
        "(jusqu'a un appel perdu), rejet des doublons v = x mod 80 + 1 jusqu'a "
        f"vingt distincts avec 0 a {PERDUS_REJET} appels perdus entre deux tirages. "
        "L'attaque crible les 2^(r+4) bits BAS — (v-1) mod 16 = les bits r..r+3 "
        "de l'etat, et le LCG mod 2^W est AUTONOME mod 2^(r+4) — en lisant les "
        "DEUX mots surs de chaque tirage (0 et 16) a pas constant et TOUS les "
        "mots sous le rejet, puis releve les 2^(W-r-4) bits hauts. Generalise "
        "le §149 (java, un mot, pas constant) a la famille et au rejet. Le "
        "design a ete renforce (deux mots, mode a rejet) AVANT cette "
        "consignation, sur des temoins plantes, jamais sur l'archive",
        "nombre d'etats complets compatibles, obtenus en criblant les bits bas "
        "puis en relevant les bits hauts, l'etat complet devant reproduire "
        f"l'ENSEMBLE des vingt numeros du tirage {ID0}",
        f"aucun null n'est requis : le crible garde un candidat bas avec "
        f"probabilite {FILTRE:.3f}^2 par tirage a pas constant et {SURV_REJET:.3f} "
        f"sous le rejet, donc au plus {FILTRE**2:.3f}^{NJ} x 2^37 = "
        f"{2**37 * FILTRE**(2*NJ):.1e} pour le plus large des cribles",
        "conforme si aucun etat complet n'est compatible et qu'aucun candidat "
        "bas ne reste non releve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(TROUV)), p=1.0,
        verdict="conforme" if not TROUV else "ETAT TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} — a un mot, l'etat plante est "
                  f"retrouve AVEC SON FANTOME DU MOT 16 et eux seuls, le relevement "
                  f"rend l'etat exact et rejette le fantome ; a deux mots (modulo "
                  f"pas 21, shuffle pas 79) il est seul survivant et se releve "
                  f"exactement ; sous le rejet avec deux mots perdus plantes, tous "
                  f"les survivants sont des decales f^k(vrai), les structurels sont "
                  f"tous presents, le relevement est exact ; une fenetre aleatoire "
                  f"ne rend rien, ni a pas constant ni sous rejet"),
        notes=(f"GENERALISE LE §149 A LA FAMILLE DES LCG DE MODULE 2^W ET AU REJET : "
               f"le crible des bits bas ne doit rien a java. Saut affine (a^pas, "
               f"c*somme a^i) d'un tirage au suivant. {NJ} tirages consecutifs "
               f"depuis {ID0}, filtre mesure {NB_PERMIS.mean()/16:.3f} par mot. "
               f"{len(LIG)} cribles, {TOT_BAS} candidat bas, {len(TROUV)} etat "
               f"releve. LEMME DES DEUX MOTS SURS : les mots 0 et 16 (16 | k et "
               f"16 | 80-k) visent un numero surement tire ; le crible les lit "
               f"tous deux ({BITS_2:.3f} bit/tirage) et n'a qu'un survivant "
               f"structurel ; a un mot le registre du mot 16 est un fantome, les "
               f"'2 candidats bas' des temoins du §149. LEMME DES DECALES : sous "
               f"le rejet chaque mot vaut un numero publie, le crible branche sur "
               f"sigma = 20..{SIGMAX} et 0..{PERDUS_REJET} perdus ({BITS_REJET:.2f} bits/"
               f"tirage), ses survivants structurels sont les registres decales "
               f"f^k(vrai). NON COUVERT : troncature (x*80)>>32, vingt premieres "
               f"cases d'un shuffle, plus de {PERDUS_REJET} perdus sous rejet, sorties "
               f"permutees (PCG), F2-lineaires primitifs (aucun quotient, "
               f"Theoreme Q), Fibonacci retarde glibc (quotient 2^155)."))
    h = lab.holm()
    say(f"   consigne : h131.lcg64_crible   {len(TROUV)} etat sur {len(LIG)} cribles")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
