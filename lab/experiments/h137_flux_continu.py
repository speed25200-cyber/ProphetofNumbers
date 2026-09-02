"""h137 — le FLUX CONTINU : l'archive TRIEE entiere (70 560 tirages, 370 journees,
343 pauses nocturnes) contre tout Fibonacci retarde additif de degre L <= 17 lu
a pas constant, par 2^L hypotheses de plan 0 et une linearisation cubique des
plans 1 et 2 (THEORIE_ETAT §7.11).

CE QUE LES §155-156 LAISSAIENT
==============================
Le §155 crible les 2^(5L) etats bas d'une FENETRE de 204 tirages, le §156
montre que les trois plans muets (2^(3L)) suffisent sur cette fenetre — mais
2^45 pour TYPE_2 (1, 15) coute 4 a 5 annees-coeur. L'archive, elle, compte
70 560 tirages. Si le generateur n'est jamais reensemence — un seul flux, lu a
pas constant S a travers les pauses — alors le tirage t lit les mots
x_(S t + k), et les 70 560 tirages sont 70 560 lectures du MEME etat.

L'ATTAQUE
=========
Plan 0 (bit 0 des L mots initiaux) : 2^L hypotheses, 131 072 a L = 17.
Sous une hypothese, le plan 1 est AFFINE en ses L bits initiaux y
(p1_i = <alpha_i, y> + delta_i, delta portant les retenues du plan 0), et le
plan 2 est affine en z et QUADRATIQUE en y. L'archive triee lit, par mot k
(k = 0, 4, 8, 12, 16 ; e = 4, 2, 3, 2, 6 bits), le residu x_k mod 2^e parmi
ceux que l'ensemble permet. Deux evenements par (tirage, mot, parite a) :
  MORT   aucun residu permis de parite a  ->  p1_i = 1 - a  (lineaire en y)
  FORCE  tous les residus permis de parite a ont le meme bit 1 = f
         ->  (p1_i + a + 1)(p2_i + f) = 0  (cubique en y, lineaire en z)
linearises sur les monomes {y, z, yy, yz, yyy, 1} : M = 1140 a L = 17.
~0,06 evenement par tirage ; le vrai plan 0 n'est jamais contredit et livre y
(et z) ; un faux plan 0 meurt a l'equation rang + 1..3 (~1 005 a L = 17, sur
~3 600 disponibles dans 60 000 tirages). Les survivants sont RELEVES plan par
plan (retenues exactes, plis des masques) jusqu'au plan 5 + shift, verifies
par simulation sur les tirages ajustes, puis testes sur les 10 560 RETENUS.

TEMOINS
=======
`tools/lfg_flux_continu.c --selftest` : un etat plante sous (K, L, S, mode,
shift) doit ressortir SEUL (1 survivant, 0 indecis, etat bas retrouve) et
un ensemble aleatoire ne rend rien — dans le regime de l'archive (60 000
tirages), pour TYPE_1 modulo pas 20 (shift 1 et 0), (4, 9) shuffle pas 79 et
80, TYPE_2 modulo pas 21, (3, 17) modulo pas 20.

Il TESTE l'archive : il consigne au registre, pre-enregistrement AVANT le
crible (jeton scelle, conserve dans le journal pour la reprise).
"""

import json
import os
import subprocess
import sys
import time
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H137_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H137_TMP", "/tmp")
POOL, DRAWN = 80, 20
MOTS = [(0, 4), (4, 2), (8, 3), (12, 2), (16, 6)]            # (k, e) : x_k mod 2^e
N_RETENUS = 10560                                             # tirages retenus (hold-out)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# trinomes primitifs x^L + x^K + 1 sur GF(2), L <= 17 (K <-> L-K : reciproques,
# tous deux primitifs ; la recurrence (K, L) a pour polynome x^L + x^(L-K) + 1)
# --------------------------------------------------------------------------

def _mulmod(a, b, p, L):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if (a >> L) & 1:
            a ^= p
    return r


def _powmod(a, e, p, L):
    r = 1
    while e:
        if e & 1:
            r = _mulmod(r, a, p, L)
        a = _mulmod(a, a, p, L)
        e >>= 1
    return r


def _facteurs(n):
    f, d = set(), 2
    while d * d <= n:
        while n % d == 0:
            f.add(d)
            n //= d
        d += 1
    if n > 1:
        f.add(n)
    return f


def primitif(K, L):
    p = (1 << L) | (1 << K) | 1
    n = (1 << L) - 1
    if _powmod(2, n, p, L) != 1:
        return False
    return all(_powmod(2, n // q, p, L) != 1 for q in _facteurs(n))


LMAX = 17
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2"}
TRINOMES = [(K, L) for L in range(2, LMAX + 1) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 31 and (3, 7) in TRINOMES and (1, 15) in TRINOMES
VARIANTES = [("fy", s) for s in (20, 21, 22, 23, 24, 79, 80)] + [("shuffle", s) for s in (79, 80)]
SHIFTS = (0, 1)
if DRY:
    TRINOMES = [t for t in TRINOMES if t[1] <= 9]
    VARIANTES = [("fy", 20), ("shuffle", 79)]

NBFILS = os.environ.get("SWEEP_THREADS", "3")
ENV = dict(os.environ, SWEEP_THREADS=NBFILS)
BIN = os.path.join(TMP, "lfg_flux_continu_h137")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_flux_continu.c")],
               check=True, capture_output=True)


def lit_bas(lignes):
    """Derniere ligne BAS -> dict des compteurs."""
    for l in reversed(lignes):
        if l.startswith("BAS "):
            d = {}
            for t in l.split():
                if "=" in t:
                    a, b = t.split("=")
                    d[a] = float(b) if a == "s" else int(b)
            return d
    raise RuntimeError("pas de ligne BAS")


def crible(K, L, S, mode, shift, fichier, n):
    """Lance l'outil sur n tirages du fichier ; rend (survivants bas, compteurs BAS)."""
    p = subprocess.run([BIN, str(K), str(L), str(S), mode, str(shift), fichier, str(n)],
                       capture_output=True, text=True, timeout=8 * 3600, env=ENV)
    assert p.returncode == 0, (K, L, S, mode, shift, p.stderr[-2000:])
    lignes = p.stdout.strip().split("\n")
    surv = [[int(x) for x in l.split()[6:]] for l in lignes if l.startswith("SURVIVANT ")]
    return surv, lit_bas(lignes)


def selftest(K, L, S, mode, shift, n, graine):
    p = subprocess.run([BIN, "--selftest", str(K), str(L), str(S), mode, str(shift),
                        str(n), str(graine)], capture_output=True, text=True,
                       timeout=8 * 3600, env=ENV)
    lignes = p.stdout.strip().split("\n")
    bas = [l for l in lignes if l.startswith("BAS ")]
    return p.returncode == 0 and lignes[-1] == "AUTOTEST OK", lit_bas(bas[:1]) if bas else {}


# --------------------------------------------------------------------------
# le flux bas et les masques, cote Python (pour les tirages RETENUS)
# --------------------------------------------------------------------------

def masque(ens, k, e, mode):
    m = 0
    for v in ens:
        if mode == "fy":
            if v >= k + 1:
                m |= 1 << ((v - 1 - k) % (1 << e))
        else:                                   # shuffle : mot k <-> case i = 79 - k
            if v <= POOL - k:
                m |= 1 << ((v - 1) % (1 << e))
    return m


def coherent(bas, K, L, S, mode, shift, ens, t0):
    """L'etat bas (mod 2^(6+shift)) lu a partir du tirage t0 est-il coherent avec
    les ensembles ens[t0:] ? Le flux bas est autonome modulo 2^(6+shift)."""
    MOD = 1 << (6 + shift)
    n = S * len(ens) + DRAWN
    r = list(bas) + [0] * (n - L)
    for i in range(L, n):
        r[i] = (r[i - K] + r[i - L]) % MOD
    for t in range(t0, len(ens)):
        for k, e in MOTS:
            x = (r[S * t + k] >> shift) % (1 << e)
            if not (masque(ens[t], k, e, mode) >> x) & 1:
                return False, t
    return True, None


# ==========================================================================
rule("1. L'HYPOTHESE DU FLUX CONTINU ET LE COUT DE L'ATTAQUE")
# ==========================================================================

P_VIDE = comb(75, 20) / comb(80, 20)
say(f"""   Un seul flux r_i = r_(i-K) + r_(i-L) mod 2^32, lu a pas constant S a travers
   les pauses : le tirage t lit x_(S t + k) = r_(S t + k) >> shift. Plan 0 devine
   (2^L), plan 1 affine en y, plan 2 affine en z et quadratique en y ; les
   evenements MORT / FORCE (~0,06 par tirage) sont linearises sur M monomes.

       {'K':>2} {'L':>2} {'hyp':>6} {'M':>5}  trinome""")
for K, L in TRINOMES:
    M = 2 * L + comb(L, 2) + L * L + comb(L, 3) + 1
    say(f"       {K:>2} {L:>2} {'2^%d' % L:>6} {M:>5}  x^{L}+x^{L-K}+1 {NOMS.get((K, L), '')}")
say(f"""
   {len(TRINOMES)} trinomes x {len(VARIANTES)} variantes (fy = Fisher-Yates partiel par modulo,
   pas {', '.join(str(s) for m, s in VARIANTES if m == 'fy')} ; shuffle = Collections.shuffle vingt dernieres
   cases, pas {', '.join(str(s) for m, s in VARIANTES if m == 'shuffle')}) x shifts {SHIFTS} = {len(TRINOMES)*len(VARIANTES)*len(SHIFTS)} cribles.
   Tout decalage constant du flux est absorbe par l'etat initial : la place des
   mots perdus dans un pas S > 20 (ou > 79) est sans objet.""")


# ==========================================================================
rule("2. L'ARCHIVE : 60 000 TIRAGES AJUSTES, 10 560 RETENUS")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
ENS = [NUM[t].tolist() for t in range(NTOT)]
N_FIT = NTOT - N_RETENUS
if DRY:
    N_FIT = 3000
FARCH = os.path.join(TMP, "h137_archive.txt")
with open(FARCH, "w") as fh:
    for t in range(NTOT):
        fh.write(" ".join(str(v) for v in ENS[t]) + "\n")
coupes = int(np.sum(np.diff(TS) != 300))
NEV = 0
for t in range(N_FIT):
    for k, e in MOTS:
        m = masque(ENS[t], k, e, "fy")
        for a in (0, 1):
            perm = [r for r in range(1 << e) if (m >> r) & 1 and (r & 1) == a]
            if not perm or len({(r >> 1) & 1 for r in perm}) == 1:
                NEV += 1

say(f"""   {NTOT} tirages, identifiants {int(IDS[0])} a {int(IDS[-1])}, {coupes} ruptures de la
   cadence de 300 s (pauses). Ajustement sur les {N_FIT} premiers (jusqu'a l'identifiant
   {int(IDS[N_FIT-1])}), les {NTOT - N_FIT} derniers RETENUS pour la prediction.
   Evenements (fy) dans les {N_FIT} tirages ajustes : {NEV} ({NEV/N_FIT:.4f} par tirage),
   contre un rang de 1 003 a L = 17 : un faux plan 0 a ~{NEV - 1003} equations de
   trop pour survivre.""")


# ==========================================================================
rule("3. PRE-ENREGISTREMENT (avant le crible)")
# ==========================================================================

JOURNAL = os.path.join(TMP, "h137_journal.txt")
FJETON = os.path.join(TMP, "h137_jeton.json")
HYPOTHESE = (
    "Aucun etat d'aucun Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 "
    f"de degre L <= {LMAX} — les {len(TRINOMES)} trinomes primitifs, dont TYPE_1 (3, 7) et "
    "TYPE_2 (1, 15) de la glibc random() — lu a PAS CONSTANT a travers les pauses "
    "(un seul flux, jamais reensemence) n'engendre les tirages TRIES de l'archive "
    "sous aucun des schemas : Fisher-Yates partiel par modulo aux pas 20 a 24, 79 "
    "et 80 ; Collections.shuffle vingt dernieres cases aux pas 79 et 80 ; sortie "
    "x = r >> 1 (glibc) ou x = r. L'attaque devine le plan 0 des L mots initiaux "
    "(2^L), linearise le plan 1 (affine en y) et le plan 2 (affine en z, quadratique "
    "en y) sur les evenements MORT et FORCE des masques de residus, releve les "
    "survivants jusqu'au plan 5 + shift et les verifie par simulation. Design fixe "
    "AVANT cette consignation sur des temoins plantes, jamais sur l'archive"
)
STATISTIQUE = (
    f"nombre d'etats bas (mod 2^(6+shift)) survivants au crible des {N_FIT} premiers "
    f"tirages tries (identifiants {int(IDS[0])} a {int(IDS[N_FIT-1])}) ET coherents "
    f"avec les {NTOT - N_FIT} tirages RETENUS ; nombre d'indecis (noyau > 2^12)"
)
NULL = (
    "aucun null n'est requis : sous un faux plan 0 les equations sont contradictoires "
    "des le rang atteint (~1 005 evenements a L = 17, temoins) et l'archive en "
    f"fournit ~{NEV} ; un faux survivant a une probabilite < 2^-1000"
)
VERDICT = (
    f"conforme si aucun survivant et aucun indecis sur les {len(TRINOMES)*len(VARIANTES)*len(SHIFTS)} "
    "cribles ; ETAT TROUVE si un survivant est coherent avec les tirages retenus ; "
    "FAUX SURVIVANT sinon"
)
if not DRY:
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        TOK = lab.preregister("h137.flux_continu", HYPOTHESE, STATISTIQUE, NULL, VERDICT,
                              track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
else:
    say("   MODE ESSAI : pas de jeton.")


# ==========================================================================
rule("4. TEMOINS DANS LE REGIME DE L'ARCHIVE")
# ==========================================================================

TEMOINS_SPEC = [(3, 7, 20, "fy", 1, 1), (3, 7, 20, "fy", 0, 2), (4, 9, 79, "shuffle", 1, 3),
                (4, 9, 80, "shuffle", 0, 4), (1, 15, 21, "fy", 1, 5), (3, 17, 20, "fy", 1, 6)]
if DRY:
    TEMOINS_SPEC = TEMOINS_SPEC[:4]
say(f"""   Un etat 32 bits plante, {N_FIT} tirages engendres sous (K, L, S, mode, shift),
   crible 2^L : l'etat bas doit ressortir SEUL (1 survivant, 0 indecis), puis un
   ensemble aleatoire de {N_FIT} tirages ne doit rien rendre.

       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'evts':>5} {'M':>5} {'rang':>5} {'sec':>7}  resultat""")
TEMOINS = []
TEMOINS_OK = True
for K, L, S, mode, shift, gr in TEMOINS_SPEC:
    t0 = time.time()
    ok, d = selftest(K, L, S, mode, shift, N_FIT, gr)
    TEMOINS_OK &= ok
    TEMOINS.append((K, L, S, mode, shift, ok, d))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {d.get('evenements', 0):>5} {d.get('M', 0):>5} "
        f"{d.get('rang_max', 0):>5} {time.time()-t0:>7.1f}  {'AUTOTEST OK' if ok else 'ECHEC'}")
say(f"\n   temoins : {'TOUS CONFORMES' if TEMOINS_OK else 'ECHEC'}")
assert TEMOINS_OK


# ==========================================================================
rule("5. LE CRIBLE DE L'ARCHIVE")
# ==========================================================================

DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 6:
            DEJA[t[0]] = (int(t[1]), int(t[2]), int(t[3]), float(t[4]), t[5:])
    say(f"   reprise : {len(DEJA)} cribles deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")

say(f"""
       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'hyp':>6} {'evts':>5} {'rang':>5} {'surv':>4} {'indec':>5} {'sec':>8}""")
LIG, TROUV = [], []
# du moins cher au plus cher : shift 0 (lineaire) puis shift 1, L croissant
ORDRE = [(K, L, S, mode, shift) for shift in SHIFTS for K, L in TRINOMES for mode, S in VARIANTES]
for K, L, S, mode, shift in ORDRE:
    cle = f"{K},{L},{S},{mode},{shift},{N_FIT}"
    t0 = time.time()
    if cle in DEJA:
        nsurv, nind, nev, sec, etats = DEJA[cle]
        etats = [e for e in etats if e != "-"]
        rang = -1
    else:
        surv, d = crible(K, L, S, mode, shift, FARCH, N_FIT)
        nsurv, nind, nev, rang, sec = d["survivants"], d["indecis"], d["evenements"], d["rang_max"], d["s"]
        etats = []
        for b in surv[:64]:
            ok, t_ech = coherent(b, K, L, S, mode, shift, ENS, N_FIT)
            etats.append(("etat_" if ok else "faux_") + "_".join(str(x) for x in b)
                         + ("" if ok else f"_echoue_au_tirage_{t_ech}"))
        jr.write(f"{cle} {nsurv} {nind} {nev} {sec} {' '.join(etats) if etats else '-'}\n")
        jr.flush()
    LIG.append((K, L, S, mode, shift, nsurv, nind, nev, sec))
    for e in etats:
        TROUV.append((K, L, S, mode, shift, e))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {'2^%d' % L:>6} {nev:>5} "
        f"{rang if rang >= 0 else '-':>5} {nsurv:>4} {nind:>5} {sec:>8.1f}"
        + ("" if nsurv == 0 and nind == 0 else "   !!"))

N_SURV = sum(l[5] for l in LIG)
N_IND = sum(l[6] for l in LIG)
N_ETATS = sum(1 for t in TROUV if t[5].startswith("etat_"))
N_FAUX = sum(1 for t in TROUV if t[5].startswith("faux_"))
SEC = sum(l[8] for l in LIG)
say(f"""
   {len(LIG)} cribles, {N_SURV} survivant, {N_IND} indecis, {N_ETATS} etat coherent avec les
   {NTOT - N_FIT} tirages retenus, {N_FAUX} faux survivant ; {SEC/3600:.2f} h de crible cumulees.""")
for K, L, S, mode, shift, e in TROUV:
    say(f"     !! x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : {e}")
    if e.startswith("etat_"):
        bas = [int(x) for x in e.split("_")[1:]]
        MOD = 1 << (6 + shift)
        n = S * (NTOT + 1) + DRAWN
        r = list(bas) + [0] * (n - L)
        for i in range(L, n):
            r[i] = (r[i - K] + r[i - L]) % MOD
        # mot 0 du tirage suivant : premier swap, numero tire = 1 + (x_0 mod 80),
        # x_0 mod 16 connu -> cinq candidats (fy : case 0 ; shuffle : case 79)
        x0 = (r[S * NTOT] >> shift) % 16
        cand = sorted(1 + (x0 + 16 * q) for q in range(5))
        say(f"        tirage suivant (id {int(IDS[-1]) + 1}) : un des vingt numeros est parmi {cand}")
if not TROUV and N_IND == 0:
    say(f"""     AUCUN. Sous l'hypothese du flux continu, les {len(TRINOMES)} trinomes primitifs de
     degre <= {LMAX} — TYPE_1 et TYPE_2 compris, 2^(32 L) etats chacun — sont exclus
     sur l'archive sous {len(VARIANTES)} variantes et 2 shifts.

   CE QUI RESTE HORS DU CRIBLE : TYPE_3 (3, 31) et TYPE_4 (1, 63) — 2^31 et 2^63
   plans 0, hors enumeration ici ; le rejet des doublons (pas variable) ; la
   troncature (x * 80) >> 32 ; les vingt premieres cases d'un shuffle ; un
   reensemencement entre deux journees ; le Fibonacci SOUSTRACTIF.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = ("conforme" if N_SURV == 0 and N_IND == 0
               else "ETAT TROUVE" if N_ETATS else "FAUX SURVIVANT" if N_FAUX else "INDECIS")
    lab.record(
        TOK, float(N_ETATS + N_IND), p=1.0, verdict=verdict,
        power_at=("temoins dans le regime de l'archive (" + f"{N_FIT} tirages) : "
                  + "; ".join(f"x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : "
                              f"{'AUTOTEST OK' if ok else 'ECHEC'} ({d.get('evenements', 0)} "
                              f"evenements, rang {d.get('rang_max', 0)}/{d.get('M', 0)}, "
                              f"{d.get('s', 0):.0f} s)"
                              for K, L, S, mode, shift, ok, d in TEMOINS)
                  + " — l'etat plante ressort seul, un ensemble aleatoire ne rend rien"),
        notes=(f"LE FLUX CONTINU : {len(LIG)} cribles (2^L plans 0, plans 1-2 par "
               f"linearisation cubique sur {{y, z, yy, yz, yyy, 1}}, M = 1140 a L = 17, "
               f"Gauss incremental par blocs de 64 hypotheses, relevement des survivants "
               f"jusqu'au plan 5 + shift) sur les {N_FIT} premiers tirages tries, "
               f"{NEV} evenements fy. {N_SURV} survivant, {N_IND} indecis, {N_ETATS} etat "
               f"coherent avec les {NTOT - N_FIT} retenus, {N_FAUX} faux. {SEC/3600:.2f} h "
               f"de crible. NON COUVERT : TYPE_3/4, rejet, troncature, vingt premieres "
               f"cases d'un shuffle, reensemencement, Fibonacci soustractif."))
    h = lab.holm()
    say(f"   consigne : h137.flux_continu   verdict {verdict}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
