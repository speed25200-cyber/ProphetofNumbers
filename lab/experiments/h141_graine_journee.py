"""h141 — la GRAINE de random() : l'archive TRIEE entiere (70 560 tirages, 370
blocs de cadence — 333 de 204 tirages —, 346 journees) contre TOUT amorcage de
random() par srandom(graine 32 bits), une graine par BLOC ou une graine par
TIRAGE, quelle que soit la SOURCE de la graine (THEORIE_ETAT §7.4 addendum).

CE QUE LE §63 LAISSAIT
======================
Le §63 testait les graines de CONVENTION (time(NULL) a la seconde du tirage,
identifiant, melanges) sur la glibc, six echantillonneurs, decalage 0. Restaient
ouvertes : (i) une graine QUELCONQUE (pid, adresse, getrandom, horloge d'un
autre fuseau, compteur) — 2^32 possibilites, jamais balayees contre l'archive ;
(ii) les autres libc (FreeBSD/macOS, musl) ; (iii) les tables TYPE_1, TYPE_2,
TYPE_4 d'initstate ; (iv) les decalages (mots consommes avant le premier
tirage) ; (v) une graine par TIRAGE et non par journee.

L'ATTAQUE : TOUTES LES GRAINES, D'UN COUP, CONTRE TOUTE L'ARCHIVE
==================================================================
Une graine est 32 bits : 2^32 amorcages, chacun engendre un flux de mots
x_0, x_1, ... et, par echantillonneur (21 : rejet, Fisher-Yates partiel, dos,
retrait par echange, naif, selection ; modulo ou flottant ; tete ou queue) et
decalage o (o mots consommes avant le tirage), UN ensemble de 20 numeros.

  Par BLOC (une graine par journee, `--balaye`) : les 370 premiers ensembles
  de bloc sont un index bitmap M[v] (v = 1..80 : les blocs dont l'ensemble
  contient v). Une emission est testee numero par numero : ET des masques,
  chaine morte des ~5 premiers numeros pour une fausse graine (une graine
  fausse touche un bloc donne avec probabilite 1/C(80,20) = 2,8e-19 ; sur
  2^32 graines x 149 combinaisons x 370 blocs : 6,6e-4 fausse touche attendue).

  Par TIRAGE (une graine par tirage, `--archive`) : index INVERSE des
  5-sous-ensembles — chacun des 70 560 tirages tries y inscrit ses C(20,5) =
  15 504 sous-ensembles au rang combinatoire C(a,1)+C(b,2)+C(c,3)+C(d,4)+C(e,5)
  < C(80,5) = 24 040 016 : 1,09e9 entrees, 4,4 Go. Une emission lit le rang de
  ses cinq plus petits numeros, parcourt les ~45 tirages candidats et verifie
  l'inclusion des 20 numeros par deux ET de 64 bits. Fausse touche : nt/C(80,20)
  = 2e-14 par (graine, combinaison) ; 3e-3 attendue sur 2^32 x 32.

  Par CONVENTION (`--horloge`, `--pid`) : par tirage, ts+d et id+d (|d| <= 300),
  les melanges du §63, et pid, ts^pid, ts+pid (pid < 32 768), tous
  echantillonneurs, decalages 0..8 — ce que le balayage exhaustif ne couvre pas
  (decalages > 1 par tirage, melanges de ts et pid).

CONFIRMATION
============
Une TOUCHE (graine, echantillonneur, decalage, bloc ou tirage) est CONFIRMEE
si (a) `--suite` reproduit le tirage SUIVANT du meme bloc (probabilite d'une
fausse continuation 1/C(80,20)), ou (b) deux touches partagent une convention
(meme graine - ts, meme graine - id, meme graine ^ ts, meme graine). Une
touche isolee non confirmee est rapportee telle quelle (elle est attendue avec
probabilite ~3e-3 par balayage exhaustif de l'archive).

TEMOINS
=======
`tools/lfg_graine_journee.c --selftest` : les cinq amorcages de la glibc
(srandom, initstate 32/64/128/256) compares a la libc REELLE de la machine
(0 ecart exige) et 149 ensembles plantes par variante (16 variantes) retrouves
exactement (149/149), 0 fausse touche. `--selftest-archive` : 149 plantes noyes
dans 20 000 tirages aleatoires, retrouves par l'index inverse (4 variantes),
0 fausse touche ; vitesse mesuree. Les amorcages BSD et musl sont transcrits
de leurs sources et ne peuvent PAS etre verifies contre une libc reelle ici
(pas de musl-gcc ni de BSD sur la machine) : dit tel quel.

Il TESTE l'archive : il consigne au registre, pre-enregistrement AVANT tout
balayage (jeton scelle, conserve pour la reprise). Le PLAN est journalise
(`/tmp/h141_journal.txt`) et repris segment par segment ; le nombre de fils
se relit dans `/tmp/h141_fils` avant chaque segment (defaut SWEEP_THREADS).
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
DRY = os.environ.get("H141_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H141_TMP", "/tmp")
EXP_ID = "h141.graine_journee"
POOL, DRAWN = 80, 20
NVAR, NECH = 16, 21
NOMS_VAR = ["glibc_T3", "glibc_T1", "glibc_T2", "glibc_T4", "bsd_new_T3", "bsd_old_T3",
            "musl_T3", "bsd_new_T1", "bsd_new_T2", "bsd_new_T4", "bsd_old_T1", "bsd_old_T2",
            "bsd_old_T4", "musl_T1", "musl_T2", "musl_T4"]
ECH_PARTIELS = 11                                             # 0..6, 13, 14, 19, 20
ECH_COMPLETS = 10                                             # 7..12, 15..18


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def combos(OP, OC):
    return ECH_PARTIELS * (OP + 1) + ECH_COMPLETS * (OC + 1)


# ==========================================================================
rule("1. THEORIE — la graine, une par bloc ou une par tirage (§7.4 addendum)")
# ==========================================================================
say(__doc__)

# ==========================================================================
rule("2. L'ARCHIVE : 370 blocs de cadence, premiers ensembles, tirages ts id")
# ==========================================================================
A = lab.load()
TS, IDS, NUMS = np.asarray(A.ts, np.int64), np.asarray(A.ids, np.int64), np.asarray(A.nums, np.int64)
NTOT = len(TS)
assert np.all(np.diff(IDS) > 0), "archive non triee par identifiant"
ENS = np.sort(NUMS, axis=1)
COUPES = np.flatnonzero(np.diff(TS) != 300) + 1
DEBUTS = np.concatenate([[0], COUPES])
FINS = np.concatenate([COUPES, [NTOT]])
NB = len(DEBUTS)
TAILLES = FINS - DEBUTS
JOURS = len(set((TS // 86400).tolist()))
say(f"   {NTOT} tirages, {NB} blocs de cadence (dont {int(np.sum(TAILLES == 204))} de 204 tirages, "
    f"{int(np.sum(TAILLES == 1))} singletons), {JOURS} journees calendaires")

F_JOURS = os.path.join(TMP, "h141_jours.txt")
F_ARCH = os.path.join(TMP, "h141_archive.txt")
F_ARCH_TSID = os.path.join(TMP, "h141_archive_tsid.txt")
with open(F_JOURS, "w") as fh:
    for d in DEBUTS:
        fh.write(" ".join(str(int(v)) for v in ENS[d]) + "\n")
with open(F_ARCH, "w") as fh:
    for t in range(NTOT):
        fh.write(" ".join(str(int(v)) for v in ENS[t]) + "\n")
with open(F_ARCH_TSID, "w") as fh:
    for t in range(NTOT):
        fh.write(f"{int(TS[t])} {int(IDS[t])} " + " ".join(str(int(v)) for v in ENS[t]) + "\n")
say(f"   ecrit {F_JOURS} ({NB} lignes), {F_ARCH} et {F_ARCH_TSID} ({NTOT} lignes)")

# ==========================================================================
rule("3. L'OUTIL ET SES TEMOINS (libc reelle, plantes, index inverse)")
# ==========================================================================
BIN = os.path.join(TMP, "lfg_graine_journee_h141")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_graine_journee.c")],
               check=True, capture_output=True)
F_FILS = os.path.join(TMP, "h141_fils")


def fils():
    try:
        return str(max(1, int(open(F_FILS).read().strip())))
    except Exception:
        return os.environ.get("SWEEP_THREADS", "2")


def lance(args, timeout=None):
    env = dict(os.environ, SWEEP_THREADS=fils())
    p = subprocess.run([BIN] + [str(a) for a in args], capture_output=True, text=True,
                       timeout=timeout, env=env)
    return p.returncode, p.stdout.strip().split("\n")


rc, L = lance(["--selftest", 8, 4])
LIBC = [l for l in L if l.startswith("LIBC ")]
PLANTES = [l for l in L if l.startswith("PLANTES ")]
AUTO = [l for l in L if l.startswith("AUTOTEST ")]
for l in LIBC + PLANTES + AUTO:
    say("   " + l)
TEMOIN_OK = rc == 0 and bool(AUTO) and AUTO[-1].endswith(" OK") and "libc=OK" in AUTO[-1]
assert TEMOIN_OK, "autotest libc/plantes en echec — rien ne sera balaye"

rc, L = lance(["--selftest-archive", 20000, 1, 0])
PL_ARCH = [l for l in L if l.startswith("PLANTES_ARCHIVE ")]
AUTO_ARCH = [l for l in L if l.startswith("AUTOTEST_ARCHIVE ")]
for l in PL_ARCH + AUTO_ARCH:
    say("   " + l)
TEMOIN_ARCH_OK = rc == 0 and bool(AUTO_ARCH) and AUTO_ARCH[-1].endswith(" OK")
assert TEMOIN_ARCH_OK, "autotest de l'index inverse en echec — rien ne sera balaye"
US_ARCH = float(PL_ARCH[0].split("us_par_graine=")[1].split()[0]) if PL_ARCH else float("nan")
say(f"   index inverse : {US_ARCH:.1f} us par graine pour {combos(1, 0)} combinaisons "
    f"sur 20 000 tirages (la machine est chargee : temps mur)")


def suite(V, g, e, o, n):
    """Les n tirages successifs (tries) engendres depuis la graine g, echantillonneur e,
    decalage o — le chemin de CONFIRMATION d'une touche."""
    rc, L = lance(["--suite", V, g, e, o, n])
    out = []
    for l in L:
        if l.startswith("TIRAGE ") and " trie " in l:
            out.append([int(x) for x in l.split(" trie ")[1].split()])
    return out


# temoin du chemin de confirmation : un bloc synthetique de trois tirages engendres
# depuis une graine connue doit etre TOUCHE par le balayage par bloc (jour 0, cette
# graine, cet echantillonneur, ce decalage) et `--suite` doit rendre ses tirages suivants
G_TEM, E_TEM, O_TEM = 987654321, 4, 2
S_TEM = suite(0, G_TEM, E_TEM, O_TEM, 3)
assert len(S_TEM) == 3 and all(len(s) == DRAWN for s in S_TEM)
F_TEM = os.path.join(TMP, "h141_temoin_bloc.txt")
with open(F_TEM, "w") as fh:
    fh.write(" ".join(str(v) for v in S_TEM[0]) + "\n")
rc, L = lance(["--balaye", 0, G_TEM - 5, G_TEM + 5, F_TEM, 8, 4])
T_TEM = [l for l in L if l.startswith("TOUCHE ") and f"graine={G_TEM} " in l
         and f"ech={E_TEM} " in l and f"decalage={O_TEM} " in l and "jour=0" in l]
T_FAUX = [l for l in L if l.startswith("TOUCHE ") and f"graine={G_TEM} " not in l]
assert rc == 0 and len(T_TEM) == 1 and not T_FAUX, (rc, L[-5:])
say(f"   temoin de confirmation : bloc synthetique (graine {G_TEM}, ech {E_TEM}, decalage "
    f"{O_TEM}) touche exactement, 0 fausse touche ; `--suite` rend ses 3 tirages")

# ==========================================================================
rule("4. PRE-ENREGISTREMENT (avant tout balayage de l'archive)")
# ==========================================================================
JOURNAL = os.path.join(TMP, "h141_journal.txt")
FJETON = os.path.join(TMP, "h141_jeton.json")
F_TOUCHES = os.path.join(TMP, "h141_touches.txt")
HYPOTHESE = (
    "Aucun bloc et aucun tirage de l'archive TRIEE n'a son ensemble de 20 numeros produit "
    "par random() amorce par srandom(graine 32 bits) — glibc (TYPE_3 random(), et TYPE_1/2/4 "
    "d'initstate), FreeBSD moderne, 4.4BSD/macOS, musl — sous les 21 echantillonneurs "
    "(rejet, Fisher-Yates partiel, dos, retrait par echange, naif, selection ; modulo ou "
    "flottant ; tete ou queue) et les decalages balayes, ni par les graines de convention "
    "(ts+d, id+d, |d| <= 300 ; melanges du §63 ; pid, ts^pid, ts+pid, pid < 32768). "
    "Balayage : toutes les 2^32 graines contre les 370 premiers ensembles de bloc (index "
    "bitmap) et contre les 70 560 tirages (index inverse des 5-sous-ensembles), par "
    "segments journalises ; la couverture effective (variantes, decalages, intervalles) "
    "est celle du journal a la consignation. Design fixe AVANT cette consignation sur "
    "la libc reelle et des plantes, jamais sur l'archive"
)
STATISTIQUE = (
    "nombre de touches CONFIRMEES : (a) `--suite` depuis la graine touchee reproduit le "
    "tirage suivant du meme bloc, ou (b) deux touches partagent une convention (meme "
    "graine - ts, graine - id, graine ^ ts, ou meme graine) ; nombre de touches isolees"
)
NULL = (
    "fausse touche par (graine, combinaison, bloc) = 1/C(80,20) = 2,8e-19 ; par balayage "
    "exhaustif d'une variante : ~7e-4 (blocs, 149 combinaisons) et ~3e-3 (tirages, 32 "
    "combinaisons) ; fausse continuation 2,8e-19 ; fausse convention partagee < 1e-5"
)
VERDICT = (
    "conforme si 0 touche confirmee ; ETAT TROUVE si une touche est confirmee (continuation "
    "ou convention partagee) ; TOUCHE ISOLEE si des touches non confirmees subsistent"
)
if not DRY:
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
else:
    say("   MODE ESSAI : pas de jeton.")

# ==========================================================================
rule("5. LE PLAN, SEGMENT PAR SEGMENT (journalise, repris)")
# ==========================================================================
SEG = 1 << 28
N_SEG = (1 << 32) // SEG


def segments(lo=0, hi=1 << 32):
    a = lo
    while a < hi:
        b = min(a + SEG, hi)
        yield a, b
        a = b


PLAN = []                                                     # (mode, V, lo, hi, OP, OC)
for V in (0, 4, 5, 6):                                        # conventions, decalages 0..8
    PLAN.append(("--horloge", V, 300, 0, 8, 8))
for a, b in segments():                                       # glibc random() : une graine par tirage
    PLAN.append(("--archive", 0, a, b, 1, 0))
for a, b in segments():                                       # glibc random() : une graine par bloc
    PLAN.append(("--balaye", 0, a, b, 8, 4))
PLAN.append(("--pid", 0, 32768, 0, 0, 0))
for V in (4, 6):                                              # FreeBSD, musl : par tirage
    for a, b in segments():
        PLAN.append(("--archive", V, a, b, 0, 0))
PLAN.append(("--archive", 5, 0, 1, 0, 0))                     # 4.4BSD : graine 0 et graines >= 2^31
for a, b in segments(1 << 31, 1 << 32):                       # (les autres coincident avec la glibc)
    PLAN.append(("--archive", 5, a, b, 0, 0))
for V in (1, 2, 3):                                           # initstate TYPE_1/2/4 : par bloc
    for a, b in segments():
        PLAN.append(("--balaye", V, a, b, 2, 2))
for V in (4, 6):                                              # FreeBSD, musl : par bloc
    for a, b in segments():
        PLAN.append(("--balaye", V, a, b, 8, 4))
PLAN.append(("--balaye", 5, 0, 1, 8, 4))
for a, b in segments(1 << 31, 1 << 32):
    PLAN.append(("--balaye", 5, a, b, 8, 4))
if DRY:
    PLAN = [("--horloge", 0, 2, 0, 1, 0), ("--archive", 0, 0, 1 << 16, 1, 0),
            ("--balaye", 0, 0, 1 << 18, 8, 4), ("--pid", 0, 64, 0, 0, 0)]
say(f"   {len(PLAN)} segments (2^28 graines par segment exhaustif)")


def cle(seg):
    return " ".join(str(x) for x in seg)


FAITS = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL):
        if l.startswith("FAIT "):
            p = l.split()
            FAITS[" ".join(p[1:7])] = l.strip()
say(f"   deja faits : {len(FAITS)}")


def execute(seg):
    """Lance un segment ; consigne TOUCHE dans F_TOUCHES et FAIT dans le journal."""
    mode, V, x, y, OP, OC = seg
    if mode in ("--horloge", "--pid"):
        args = [mode, V, F_ARCH_TSID, x, OP, OC]
    else:
        args = [mode, V, x, y, F_ARCH if mode == "--archive" else F_JOURS, OP, OC]
    env = dict(os.environ, SWEEP_THREADS=fils())
    t0 = time.time()
    p = subprocess.Popen([BIN] + [str(a) for a in args], stdout=subprocess.PIPE, text=True, env=env)
    touches, fin, dernier_avance = [], "", ""
    with open(F_TOUCHES, "a") as ft:
        for l in p.stdout:
            l = l.rstrip("\n")
            if l.startswith("TOUCHE "):
                touches.append(l)
                ft.write(f"{cle(seg)} | {l}\n")
                ft.flush()
                say("   " + l)
            elif l.startswith("FIN "):
                fin = l
            elif l.startswith("DEBUT "):
                say("   " + l)
            elif l.startswith("AVANCE "):
                dernier_avance = l
    rc = p.wait()
    assert rc == 0 and fin, (seg, rc, dernier_avance)
    sec = time.time() - t0
    with open(JOURNAL, "a") as fj:
        fj.write(f"FAIT {cle(seg)} touches={len(touches)} sec={sec:.1f} fils={env['SWEEP_THREADS']} "
                 f"| {fin}\n")
    say(f"   {fin}   ({sec / 3600:.2f} h mur)")
    return touches


for seg in PLAN:
    if cle(seg) in FAITS:
        continue
    say(f"\n   segment {cle(seg)}   ({time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})")
    execute(seg)

# ==========================================================================
rule("6. LES TOUCHES : continuation et conventions")
# ==========================================================================
TOUCHES = []
if os.path.exists(F_TOUCHES):
    for l in open(F_TOUCHES):
        if "| TOUCHE " not in l:
            continue
        segk, tl = l.split(" | TOUCHE ", 1)
        d = {}
        for tok in tl.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                d[k] = v
        d["segment"] = segk.strip()
        TOUCHES.append(d)
say(f"   {len(TOUCHES)} touche(s) brutes")


CONFIRMEES, ISOLEES = [], []
for d in TOUCHES:
    V, g, e, o = int(d["variante"]), int(d["graine"]), int(d["ech"]), int(d["decalage"])
    d["nom"] = NOMS_VAR[V]
    if "jour" in d:
        t = int(DEBUTS[int(d["jour"])])
    else:
        t = int(d["tirage"])
    b = int(np.searchsorted(DEBUTS, t, side="right") - 1)
    d["t"], d["bloc"] = t, b
    d["delta_ts"], d["delta_id"], d["xor_ts"] = g - int(TS[t]), g - int(IDS[t]), g ^ int(TS[t])
    S = suite(V, g, e, o, 3)
    d["continuation"] = 0
    if S and S[0] == ENS[t].tolist():
        for k in (1, 2):
            if k < len(S) and t + k < FINS[b] and S[k] == ENS[t + k].tolist():
                d["continuation"] = k
            else:
                break
    if d["continuation"]:
        CONFIRMEES.append(d)
for cle_conv in ("delta_ts", "delta_id", "xor_ts", "graine"):
    vus = {}
    for d in TOUCHES:
        vus.setdefault((d["variante"], d["ech"], d[cle_conv]), []).append(d)
    for k, grp in vus.items():
        if len({x["t"] for x in grp}) >= 2:
            for x in grp:
                x["convention"] = f"{cle_conv}={k[2]}"
                if x not in CONFIRMEES:
                    CONFIRMEES.append(x)
ISOLEES = [d for d in TOUCHES if d not in CONFIRMEES]
for d in TOUCHES:
    say(f"   {d.get('nom', '')} graine={d['graine']} ech={d['ech']} dec={d['decalage']} "
        f"tirage={d['t']} bloc={d['bloc']} continuation={d['continuation']} "
        f"convention={d.get('convention', '-')} delta_ts={d['delta_ts']} delta_id={d['delta_id']}")
say(f"   confirmees : {len(CONFIRMEES)}   isolees : {len(ISOLEES)}")

# ==========================================================================
rule("7. COUVERTURE (journal) ET CONSIGNATION")
# ==========================================================================
COUV = {}
SEC_TOT = 0.0
for l in open(JOURNAL) if os.path.exists(JOURNAL) else []:
    if not l.startswith("FAIT "):
        continue
    p = l.split()
    mode, V, x, y, OP, OC = p[1], int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6])
    sec = float([t for t in p if t.startswith("sec=")][0][4:])
    SEC_TOT += sec
    k = (mode, V, OP, OC)
    c = COUV.setdefault(k, {"graines": 0, "sec": 0.0, "segments": 0, "touches": 0, "D": x})
    if mode in ("--archive", "--balaye"):
        c["graines"] += y - x
    else:                                                     # conventions : graines= de la ligne FIN
        c["graines"] += int([t for t in p if t.startswith("graines=")][-1][8:])
    c["sec"] += sec
    c["segments"] += 1
    c["touches"] += int([t for t in p if t.startswith("touches=")][0][8:])
LIGNES = []
for (mode, V, OP, OC), c in sorted(COUV.items()):
    if mode in ("--archive", "--balaye"):
        etendue = f"{c['graines']:,} graines ({100 * c['graines'] / 2 ** 32:.1f} % de 2^32)"
    else:
        etendue = f"{c['graines']:,} graines de convention (D={c['D']}, sur les {NTOT} tirages)"
    LIGNES.append(f"{mode} {NOMS_VAR[V]} OP={OP} OC={OC} : {etendue}, {combos(OP, OC)} combinaisons, "
                  f"{c['touches']} touche(s), {c['sec'] / 3600:.2f} h")
    say("   " + LIGNES[-1])
say(f"   total : {SEC_TOT / 3600:.1f} h mur")

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = ("ETAT TROUVE" if CONFIRMEES else "TOUCHE ISOLEE" if ISOLEES else "conforme")
    lab.record(
        TOK, float(len(CONFIRMEES)), p=1.0, verdict=verdict,
        power_at=("libc reelle : " + " ; ".join(l.split(" ", 1)[1] for l in LIBC)
                  + " ; plantes : " + " ; ".join(l.split(" ", 1)[1] for l in PLANTES)
                  + " ; index inverse : " + " ; ".join(l.split(" ", 1)[1] for l in PL_ARCH)),
        notes=(f"LA GRAINE DE random() : {len(TOUCHES)} touche(s) brute(s), {len(CONFIRMEES)} "
               f"confirmee(s), {len(ISOLEES)} isolee(s). Couverture : " + " | ".join(LIGNES)
               + f". {SEC_TOT / 3600:.1f} h mur. NON COUVERT : pid >= 32768 dans les melanges, "
               "initstate BSD/musl aux decalages non balayes, premier tirage publie = deuxieme "
               "tirage engendre au-dela des decalages balayes, amorcages BSD/musl non verifies "
               "contre une libc reelle, graines de plus de 32 bits (srandom48, MT19937, "
               "std::mt19937 : autres generateurs)."))
    h = lab.holm()
    say(f"   consigne : {EXP_ID}   verdict {verdict}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
