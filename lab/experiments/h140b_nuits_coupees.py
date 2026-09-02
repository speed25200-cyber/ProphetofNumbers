"""h140b — les DOUZE NUITS COUPEES de h140, decodees ENTIERES (decodage mou, §7.13).

h140 coupe l'archive aux ruptures de la cadence de 300 s : 369 ruptures, 370 blocs.
Or 24 de ces ruptures ne sont pas des pauses de nuit : douze fois, UN tirage porte un
horodatage decale de 1 a 5 s (un ecart +d suivi de -d, identifiants consecutifs), et la
coupe rend ces douze nuits en trois blocs (82 a 143 tirages, un singleton, le reste)
au lieu d'un bloc de 204. Sous l'hypothese que h140 teste — un generateur REAMORCE
chaque nuit, un etat par nuit — ces douze nuits sont un seul flux ; decodees en deux
moities, le z attendu y tombe a 9,2 sqrt(n/204) = 5,8 (n = 82) a 7,7 (n = 143), sous les
seuils Z1 = 8,31 (TYPE_3) et 8,23 (TYPE_2 a shift 1) : h140 y est SANS PUISSANCE pour
les grands trinomes. Ce script referme ce trou : les douze nuits, 204 tirages chacune,
sous la grille par bloc de h140 (shift 0 : les 31 trinomes de degre <= 17 et TYPE_3 ;
shift 1 : degre <= 11 et TYPE_2 ; neuf variantes), avec ses seuils et son outil.

Temoins : la batterie de h140 vaut ici (meme regime, blocs de 204) ; une batterie
courte est refaite avec le binaire compile par ce script (l'outil corrige : une ombre
ne remplace l'etat rendu que confirmee).

Pre-enregistre AVANT tout decodage de l'archive ; consigne UNE ligne au registre.
Reprise : /tmp/h140b_journal.txt. H140B_DRY=1 : essai a blanc (3 nuits, 2 variantes,
trinomes de degre <= 7 et TYPE_3, rien n'est consigne).
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H140B_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H140B_TMP", "/tmp")
EXP_ID = "h140b.nuits_coupees"
POOL = 80
MOTS10 = [(0, 4), (2, 1), (4, 2), (6, 1), (8, 3), (10, 1), (12, 2), (14, 1), (16, 6), (18, 1)]
NBT = 4                                                       # temoins courts : plantes = nuls = NBT


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def Qinv(cible):
    lo, hi = 0.0, 20.0
    for _ in range(200):
        z = 0.5 * (lo + hi)
        if 0.5 * math.erfc(z / math.sqrt(2)) > cible:
            lo = z
        else:
            hi = z
    return 0.5 * (lo + hi)


def seuil(nbits, alpha=1e-7):
    return Qinv(alpha / 2.0 ** nbits)


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
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3"}
TRINOMES = [(K, L) for L in range(2, LMAX + 1) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 31 and (3, 7) in TRINOMES and (1, 15) in TRINOMES
VARIANTES = [("fy", s) for s in (20, 21, 22, 23, 24, 79, 80)] + [("shuffle", s) for s in (79, 80)]
SCHEMAS = ("Fisher-Yates partiel par modulo aux pas 20 a 24, 79 et 80 ; "
           "Collections.shuffle vingt dernieres cases aux pas 79 et 80")
GRILLE = [                                                    # la grille PAR BLOC de h140
    (0, TRINOMES + [(3, 31)]),
    (1, [t for t in TRINOMES if t[1] <= 11] + [(1, 15)]),
]
if DRY:
    GRILLE = [(s, [t for t in tr if t[1] <= 7 or t == (3, 31)][:3]) for s, tr in GRILLE]
    VARIANTES = [("fy", 20), ("shuffle", 79)]

NBFILS = os.environ.get("SWEEP_THREADS", "1")
ENV = dict(os.environ, SWEEP_THREADS=NBFILS)
BIN = os.path.join(TMP, "lfg_soft_wht_h140b")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_soft_wht.c"), "-lm"],
               check=True, capture_output=True)


def env_de(K, L, shift):
    e = dict(ENV)
    if L > 24:
        e["WHT_B"] = "18"
        e["WHT_ZSTOP"] = "%.3f" % seuil(L if shift == 0 else 2 * L)
    return e


def lit_blocs(lignes):
    out = []
    for l in lignes:
        if not l.startswith("BLOC "):
            continue
        t = l.split()
        out.append(dict(b=int(t[1]), t0=int(t[2]), n=int(t[3]), nobs=int(t[4]), z1=float(t[5]),
                        z1b=float(t[6]), meth=t[7], couv=float(t[8]), plans=t[9:12],
                        z2=float(t[12]), z2b=float(t[13]), meth2=t[14], couv2=float(t[15]),
                        delta=int(t[16])))
    return out


def lit_fin(lignes):
    for l in reversed(lignes):
        if l.startswith("FIN "):
            t = l.split()
            return dict(nblocs=int(t[6]), zmax=float(t[7]), bloc_zmax=int(t[8]), sec=float(t[11]))
    raise RuntimeError("pas de ligne FIN")


def lance(args, K, L, shift):
    p = subprocess.run([BIN] + [str(a) for a in args], capture_output=True, text=True,
                       timeout=12 * 3600, env=env_de(K, L, shift))
    assert p.returncode == 0, (args, p.stderr[-2000:])
    return p.stdout.strip().split("\n")


def masque(ens, k, e, mode):
    m = 0
    for v in ens:
        if mode == "fy":
            if v >= k + 1:
                m |= 1 << ((v - 1 - k) % (1 << e))
        else:
            if v <= POOL - k:
                m |= 1 << ((v - 1) % (1 << e))
    return m


def coherent_bloc(plans, K, L, S, mode, shift, ens):
    npl = len(plans)
    nb = npl - shift
    if nb <= 0:
        return None, None, 0
    MOD = 1 << npl
    n = S * (len(ens) - 1) + POOL + L
    r = [sum(((plans[j] >> i) & 1) << j for j in range(npl)) for i in range(L)] + [0] * (n - L)
    for i in range(L, n):
        r[i] = (r[i - K] + r[i - L]) % MOD
    nev = 0
    for t, e_t in enumerate(ens):
        for k, e in MOTS10:
            ee = min(e, nb)
            x = (r[S * t + k] >> shift) % (1 << ee)
            m = masque(e_t, k, ee, mode)
            if m != (1 << (1 << ee)) - 1:
                nev += 1
            if not (m >> x) & 1:
                return False, t, nev
    return True, None, nev


# ==========================================================================
rule("1. LES DOUZE NUITS COUPEES")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
d = np.diff(TS)
SAUTS = np.flatnonzero((d != 300) & (d < 3600))               # ruptures qui ne sont pas des pauses
PAUSES = np.flatnonzero(d >= 3600)
DEBN, FINN = np.r_[0, PAUSES + 1], np.r_[PAUSES + 1, NTOT]
NUITS = []                                                    # (debut, fin, ecarts, positions)
for a, b in zip(DEBN, FINN):
    j = [int(x) for x in SAUTS if a <= x < b]
    if j:
        NUITS.append((int(a), int(b), [int(d[x]) for x in j], [x - int(a) + 1 for x in j]))
assert all(np.diff(IDS[a:b]).tolist() == [1] * (b - a - 1) for a, b, _, _ in NUITS)
if DRY:
    NUITS = NUITS[:3]
NB = len(NUITS)
say(f"   {NTOT} tirages, {len(DEBN)} nuits (pauses >= 1 h), {len(SAUTS)} sauts de cadence hors pause ;")
say(f"   {NB} nuits coupees par un saut, identifiants consecutifs dans chacune :")
for a, b, ec, pos in NUITS:
    say(f"      tirages {a:>6}..{b - 1:<6} ({b - a} tirages, identifiants {int(IDS[a])}..{int(IDS[b - 1])}) : "
        f"ecarts {ec} aux rangs {pos}  ->  blocs h140 de {pos[0] - 1}, 1 et {b - a - pos[0]} tirages")
ENS = []
for a, b, _, _ in NUITS:
    ENS += [NUM[t].tolist() for t in range(a, b)]
FARCH = os.path.join(TMP, "h140b_archive.txt")
with open(FARCH, "w") as fh:
    for e in ENS:
        fh.write(" ".join(str(v) for v in e) + "\n")
FBLOCS = os.path.join(TMP, "h140b_blocs.txt")
with open(FBLOCS, "w") as fh:
    off = 0
    for a, b, _, _ in NUITS:
        fh.write(f"{off}\n")
        off += b - a
NRUNS = sum(len(tr) * len(VARIANTES) for _, tr in GRILLE)
say(f"""
   {NRUNS} decodages de {NB} nuits entieres ({len(ENS)} tirages) : {len(VARIANTES)} variantes ({SCHEMAS}),
   shift 0 ({len(GRILLE[0][1])} trinomes, TYPE_3 compris) et shift 1 ({len(GRILLE[1][1])} trinomes, TYPE_2 compris).
   z attendu pour un etat vrai : 9,2 par nuit de 204 (h140 : 5,8 a 7,7 sur les moities).""")

# ==========================================================================
rule("2. PRE-ENREGISTREMENT (avant tout decodage de l'archive)")
# ==========================================================================

JOURNAL = os.path.join(TMP, "h140b_journal.txt")
FJETON = os.path.join(TMP, "h140b_jeton.json")
HYPOTHESE = (
    f"Aucune des {NB} nuits de l'archive triee que h140 a decodees en deux moities (un tirage "
    "a l'horodatage decale de 1 a 5 s, identifiants consecutifs) n'est, prise ENTIERE (204 "
    "tirages, un etat par nuit : generateur reamorce chaque nuit), engendree par un Fibonacci "
    "retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu a pas constant : les 31 trinomes "
    "primitifs de degre <= 17 et TYPE_3 (3, 31) a shift 0 (x = r, plan 0), les trinomes de "
    "degre <= 11 et TYPE_2 a shift 1 (x = r >> 1, plans 0 et 1, 2^(2L)), sous les schemas : "
    f"{SCHEMAS}. Decodage MOU (§7.13), outil, seuils et grille par bloc de h140, sur les nuits "
    "entieres au lieu des moities"
)
STATISTIQUE = (
    "nombre D de (decodage, nuit) DETECTES : z1 >= Z1 = Q^-1(10^-7 / 2^nbits), nbits = L a "
    "shift 0 et 2L a shift 1 (z1 = z de l'etat de R maximal) ; parmi eux, nombre CONFIRMES : "
    "plan shift + 1 de z2 >= Z2 = Q^-1(10^-3 / 2^L) et coherence exacte des plans rendus avec "
    "les masques de residus de la nuit"
)
NULL = (
    "borne d'union exacte (lemme du §7.13 : z(p) de variance 1 sous H0 pour tout etat) : "
    f"P(detection d'une nuit) <= 10^-7, E[D] <= {NRUNS} decodages x {NB} nuits x 10^-7 "
    f"~ {NRUNS * NB * 1e-7:.1e}"
)
VERDICT = (
    "conforme si D = 0 ; ETAT TROUVE si une nuit detectee est confirmee (z2 >= Z2 ET coherence "
    "exacte) ; DETECTION NON CONFIRMEE sinon (anomalie a examiner, non conforme)"
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
rule("3. TEMOINS COURTS (binaire de ce script, blocs de 204)")
# ==========================================================================

TEMOINS_CAS = [(3, 7, 20, "fy", 0), (3, 7, 20, "fy", 1), (1, 15, 80, "shuffle", 1),
               (3, 31, 20, "fy", 0), (3, 31, 80, "shuffle", 0)]
if DRY:
    TEMOINS_CAS = TEMOINS_CAS[:2]
TEMOINS, FP_TOTAL = [], 0
say(f"       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'Z1':>5} {'detect':>6} {'ident':>5} {'conf':>4} {'fp':>2} {'sec':>6}")
for i, (K, L, S, mode, shift) in enumerate(TEMOINS_CAS):
    t0 = time.time()
    lignes = lance(["--selftest", K, L, S, mode, shift, NBT, 4200 + i, 204], K, L, shift)
    dd = {}
    for l in lignes:
        if l.startswith("AUTOTEST "):
            for t in l.split():
                if "=" in t:
                    a, b = t.split("=")
                    dd[a] = float(b) if a == "Z1" else int(b)
    FP_TOTAL += dd["faux_positifs"]
    TEMOINS.append((K, L, S, mode, shift, dd))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {dd['Z1']:>5.2f} {dd['detectes']:>3}/{dd['plantes']:<2} "
        f"{dd['etape1_ok']:>3}/{dd['plantes']:<1} {dd['etape2_ok']:>2}/{dd['plantes']:<1} {dd['faux_positifs']:>2} {time.time() - t0:>6.1f}")
say(f"   faux positifs sur les blocs nuls : {FP_TOTAL}")
assert FP_TOTAL == 0

# ==========================================================================
rule("4. LE DECODAGE DES DOUZE NUITS ENTIERES")
# ==========================================================================

DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 6:
            DEJA[t[0]] = (int(t[1]), int(t[2]), float(t[3]), int(t[4]), float(t[5]), t[6:])
    say(f"   reprise : {len(DEJA)} decodages deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")
say(f"""
       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'etats':>6} {'Z1':>5} {'nuits':>5} {'detec':>5} {'conf':>4} {'z1 max':>7} {'sec':>8}""")
LIG, DETEC = [], []
for shift, trin in GRILLE:
    for K, L in trin:
        for mode, S in VARIANTES:
            cle = f"nuit,{K},{L},{S},{mode},{shift}"
            nb_ = L if shift == 0 else 2 * L
            Z1, Z2 = seuil(nb_), seuil(L, 1e-3)
            if cle in DEJA:
                ndet, nconf, zmax, bmax, sec, det = DEJA[cle]
                det = [x for x in det if x != "-"]
            else:
                lignes = lance([K, L, S, mode, shift, FARCH, FBLOCS], K, L, shift)
                bl, fin = lit_blocs(lignes), lit_fin(lignes)
                assert fin["nblocs"] == NB
                zmax, bmax, sec = fin["zmax"], fin["bloc_zmax"], fin["sec"]
                det, nconf = [], 0
                for x in bl:
                    if x["z1"] < Z1:
                        continue
                    plans = [int(p, 16) for p in x["plans"] if p != "-"]
                    ens = ENS[x["t0"]:x["t0"] + x["n"]]
                    ok, tf, nev = coherent_bloc(plans, K, L, S, mode, shift, ens)
                    conf = x["z2"] >= Z2 and ok is True
                    nconf += conf
                    det.append(f"{x['b']}:{x['z1']:.2f}:{x['z2']:.2f}:{'+'.join(x['plans'])}:{x['delta']}:"
                               f"{'coherent' if ok else 'incoherent_t%d' % tf if ok is False else 'sans_plan'}:{nev}:"
                               f"{'CONFIRME' if conf else 'non_confirme'}")
                ndet = len(det)
                jr.write(f"{cle} {ndet} {nconf} {zmax} {bmax} {sec} {' '.join(det) if det else '-'}\n")
                jr.flush()
            LIG.append((K, L, S, mode, shift, ndet, nconf, zmax, bmax, sec))
            for e in det:
                DETEC.append((K, L, S, mode, shift, e))
            say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {'2^%d' % nb_:>6} {Z1:>5.2f} {NB:>5} "
                f"{ndet:>5} {nconf:>4} {zmax:>7.2f} {sec:>8.1f}" + ("" if ndet == 0 else "   !!"))

D_TOT = sum(l[5] for l in LIG)
C_TOT = sum(l[6] for l in LIG)
SEC = sum(l[9] for l in LIG)
ZMAX = max(l[7] for l in LIG)
lmax = max(LIG, key=lambda l: l[7])
say(f"""
   {len(LIG)} decodages x {NB} nuits = {len(LIG) * NB} (decodage, nuit) ; D = {D_TOT} detecte, {C_TOT} confirme ;
   z1 max = {ZMAX:.2f} (x^{lmax[1]}+x^{lmax[1]-lmax[0]}+1 {lmax[3]} pas {lmax[2]} shift {lmax[4]}, nuit {lmax[8]}) ;
   {SEC/60:.1f} min de decodage cumulees.""")
for K, L, S, mode, shift, e in DETEC:
    say(f"     !! x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : {e}")
if D_TOT == 0:
    say(f"""     AUCUNE DETECTION : les {NB} nuits que h140 ne pouvait lire qu'a moitie ne portent pas
     davantage, entieres, les plans bas d'un Fibonacci retarde reamorce chaque nuit.""")

# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = ("conforme" if D_TOT == 0 else "ETAT TROUVE" if C_TOT else "DETECTION NON CONFIRMEE")
    puiss = "; ".join(
        f"x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} : detectes {dd['detectes']}/{dd['plantes']}, "
        f"identifies {dd['etape1_ok']}/{dd['plantes']}, confirmes {dd['etape2_ok']}/{dd['plantes']}"
        for K, L, S, mode, shift, dd in TEMOINS)
    lab.record(
        TOK, float(D_TOT), p=1.0 if D_TOT == 0 else min(1.0, len(LIG) * NB * 1e-7), verdict=verdict,
        power_at=(f"batterie de h140 (12 plantes + 12 nuls par classe, blocs de 204) et temoins courts "
                  f"de ce script ({NBT} plantes + {NBT} nuls) : " + puiss
                  + f" — {FP_TOTAL} faux positif sur les blocs nuls"),
        notes=(f"LES {NB} NUITS COUPEES DE h140, ENTIERES : {len(LIG)} decodages ({len(LIG) * NB} "
               f"(decodage, nuit)), {len(VARIANTES)} variantes, shift 0 ({len(GRILLE[0][1])} trinomes) et "
               f"shift 1 ({len(GRILLE[1][1])}). D = {D_TOT} detecte, {C_TOT} confirme, z1 max {ZMAX:.2f}. "
               f"{SEC/60:.1f} min de decodage. NON COUVERT : comme h140 (TYPE_3 shift 1, TYPE_4, "
               f"degres 15 hors TYPE_2 et 17 a shift 1, rejet, troncature, Fibonacci soustractif)."))
    h = lab.holm()
    say(f"   consigne : {EXP_ID}   verdict {verdict}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")
say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
