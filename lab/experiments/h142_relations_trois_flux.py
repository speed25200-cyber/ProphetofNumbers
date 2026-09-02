"""h142 — les RELATIONS DE POIDS 3 SUR Z/4 sous le flux continu (§7.14) : TYPE_3 a shift 1.

Le plan 1 de r_i = r_(i-K) + r_(i-L) mod 2^32 (bit 0 de la sortie glibc x = r >> 1) est
lineaire dans le plan 1 y de l'etat et QUADRATIQUE dans le plan 0 p :
    r1_i = <alpha_i, y> xor <alpha'_i, p> xor e2(alpha_i ^ p).
Sur trois positions a, b, c avec alpha_a xor alpha_b xor alpha_c = 0 (x^a + x^b + x^c = 0
mod x^L + x^K + 1) la partie en y disparait :
    r1_a xor r1_b xor r1_c = <beta, p> xor maj(<alpha_a,p>, <alpha_b,p>, <alpha_c,p>),
et (-1)^maj = ((-1)^x + (-1)^y + (-1)^z - 1)/2 : la statistique Lambda(p) = sum_R u_R eps_R(p),
u_R = t_a t_b t_c (produit des trois bits mous du §7.13), est UNE transformee de
Walsh-Hadamard de 2^L. Var Lambda = V = sum tau0^2 tau0^2 tau0^2 exactement sous H0 pour
tout p (une relation par triple de tirages), et E Lambda(p_vrai) = V : z_attendu = sqrt(V).
Ce que h140 ne pouvait pas faire (2^62 etats a shift 1 pour TYPE_3) se fait en 2^31 : les
44 trinomes primitifs de degre 15 a 31, TYPE_3 (3, 31) en tete, sous le flux (un seul
etat pour les 70 560 tirages). La meme WHT sur les mots (p = 0) est le test EXACT du plan
0 a shift 0 (zlin) ; p trouve, y suit par la WHT des mots (z_y ~ 0,66 sqrt(N)) et la
coherence des classes de residus confirme.

Temoins : etats plantes puis tirages nuls, avec le binaire compile par ce script.
Pre-enregistre AVANT tout decodage de l'archive ; consigne UNE ligne au registre.
Reprise : /tmp/h142_journal.txt. H142_DRY=1 : essai a blanc (3 trinomes, 2 variantes,
5 000 tirages, rien n'est consigne). H142_TEMOIN31=0 : saute le temoin TYPE_3 sur 70 560.
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
DRY = os.environ.get("H142_DRY") == "1"
TEMOIN31 = os.environ.get("H142_TEMOIN31", "1") == "1" and not DRY
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H142_TMP", "/tmp")
EXP_ID = "h142.relations_trois_flux"
MMAX = 20_000_000


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


NOMS = {(1, 15): "TYPE_2", (3, 31): "TYPE_3"}
TRINOMES = [(K, L) for L in range(15, 32) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 44 and (3, 31) in TRINOMES and (1, 15) in TRINOMES
ORDRE = [(3, 31)] + [t for t in TRINOMES if t[1] == 17] + [t for t in TRINOMES if t[1] not in (17, 31)] \
    + [t for t in TRINOMES if t[1] == 31 and t != (3, 31)]
assert sorted(ORDRE) == sorted(TRINOMES)
VARIANTES = [("fy", s) for s in (20, 21, 22, 23, 24, 79, 80)] + [("shuffle", s) for s in (79, 80)]
SCHEMAS = ("Fisher-Yates partiel par modulo aux pas 20 a 24, 79 et 80 ; "
           "Collections.shuffle vingt dernieres cases aux pas 79 et 80")
if DRY:
    ORDRE = [(1, 15), (3, 17), (3, 31)]
    VARIANTES = [("fy", 20), ("shuffle", 79)]

NBFILS = os.environ.get("SWEEP_THREADS", "2")
ENV = dict(os.environ, SWEEP_THREADS=NBFILS)
BIN = os.path.join(TMP, "lfg_rel3_flux_h142")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "lfg_rel3_flux.c"), "-lm"],
               check=True, capture_output=True)


def lance(args, env=None):
    p = subprocess.run(["nice", "-n", "10", BIN] + [str(a) for a in args], capture_output=True, text=True,
                       timeout=24 * 3600, env=env or ENV)
    assert p.returncode == 0, (args, p.stderr[-2000:])
    return p.stdout.strip().split("\n")


def champs(l):
    dd = {}
    for t in l.split():
        if "=" in t:
            a, b = t.split("=", 1)
            try:
                dd[a] = int(b, 16) if b.startswith("0x") else (int(b) if b.lstrip("-").isdigit() else float(b))
            except ValueError:
                dd[a] = b
    return dd


def lit(lignes, prefixe):
    for l in reversed(lignes):
        if l.startswith(prefixe + " "):
            return champs(l)
    raise RuntimeError("pas de ligne " + prefixe)


# ==========================================================================
rule("1. L'ARCHIVE SOUS LE FLUX : UN SEUL ETAT POUR 70 560 TIRAGES")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
assert np.all(np.diff(TS) > 0)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
if DRY:
    NTOT = 5000
SUFF = "_dry" if DRY else ""
FARCH = os.path.join(TMP, f"h142_archive{SUFF}.txt")
with open(FARCH, "w") as fh:
    for t in range(NTOT):
        fh.write(" ".join(str(v) for v in NUM[t].tolist()) + "\n")
NRUNS = len(ORDRE) * len(VARIANTES)
say(f"""
   {NTOT} tirages tries, dans l'ordre du temps, un seul flux ; {len(ORDRE)} trinomes primitifs de degre
   15 a 31 (TYPE_3 (3, 31) en tete, TYPE_2 (1, 15) compris) x {len(VARIANTES)} variantes ({SCHEMAS}) :
   {NRUNS} decodages, chacun a shift 1 (relations, 2^L) et a shift 0 (plan 0 lineaire, 2^L).""")

# ==========================================================================
rule("2. PRE-ENREGISTREMENT (avant tout decodage de l'archive)")
# ==========================================================================

JOURNAL = os.path.join(TMP, f"h142_journal{SUFF}.txt")
FJETON = os.path.join(TMP, "h142_jeton.json")
HYPOTHESE = (
    "L'archive triee (70 560 tirages dans l'ordre du temps) n'est pas, sous le FLUX CONTINU (un "
    "seul etat, aucun reamorcage), engendree par un Fibonacci retarde additif r_i = r_(i-K) + "
    "r_(i-L) mod 2^32 lu a pas constant, pour les 44 trinomes primitifs de degre 15 a 31 (TYPE_2 "
    "(1, 15) et TYPE_3 (3, 31) compris), ni a shift 1 (x = r >> 1, glibc random() : plan 1 observe, "
    "decode par les relations de poids 3 sur Z/4 du §7.14, 2^L etats p du plan 0) ni a shift 0 "
    f"(x = r : plan 0 observe, WHT lineaire exacte des mots), sous les schemas : {SCHEMAS}"
)
STATISTIQUE = (
    "nombre D de statistiques (decodage x shift) DETECTEES : z >= Z1 = Q^-1(10^-7 / 2^L), z = "
    "Lambda/sqrt(V) au maximum sur les 2^L etats (shift 1 : L <= 28 WHT exacte ; L > 28 chi2 des "
    "2^(L-28) WHT partielles puis evaluation exacte des 256 meilleurs p_bas x tous les p_haut, "
    "maximum sur un sous-ensemble donc conservatif) et zlin = max WHT des mots / sqrt(sum t^2) "
    "(shift 0) ; parmi elles, CONFIRMEES : plan suivant y de z_y >= Z1 et 0 contradiction des "
    "classes de residus"
)
NULL = (
    "borne d'union exacte : sous H0 E[t] = 0 (symetrie des classes admissibles), une relation par "
    "triple de tirages => Var Lambda(p) = V pour tout p (§7.14), z de variance 1, "
    f"P(detection) <= 10^-7 par statistique, E[D] <= {2 * NRUNS} x 10^-7 = {2 * NRUNS * 1e-7:.1e}"
)
VERDICT = (
    "conforme si D = 0 ; ETAT TROUVE si une detection est confirmee (z_y >= Z1 ET 0 contradiction) ; "
    "DETECTION NON CONFIRMEE sinon (anomalie a examiner, non conforme)"
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
rule("3. TEMOINS (etat plante puis tirages nuls, binaire de ce script)")
# ==========================================================================

TEMOINS_CAS = [(3, 17, 20, "fy", 1, 20000), (3, 17, 79, "shuffle", 1, 8000), (1, 15, 80, "shuffle", 1, 8000),
               (3, 17, 20, "fy", 0, 20000), (3, 31, 20, "fy", 1, 70560)]
if not TEMOIN31:
    TEMOINS_CAS = TEMOINS_CAS[:4]
if DRY:
    TEMOINS_CAS = [(3, 17, 20, "fy", 1, 5000)]
TEMOINS, FP_TOTAL = [], 0
say(f"       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'shift':>5} {'N':>6} {'Z1':>5} {'z_att':>6} {'z':>6} {'detect':>6} {'ident':>5} {'fp':>2} {'sec':>7}")
for i, (K, L, S, mode, shift, n) in enumerate(TEMOINS_CAS):
    t0 = time.time()
    lignes = lance(["--selftest-flux", K, L, S, mode, n, 4200 + i], dict(ENV, LFG_SHIFT=str(shift)))
    dd, rel, ver = lit(lignes, "AUTOTEST"), lit(lignes, "RELATIONS"), lit(lignes, "VERITE")
    FP_TOTAL += dd["faux_positifs"]
    z = ver["zmax"] if shift else ver["zlin"]
    TEMOINS.append((K, L, S, mode, shift, n, dd, rel, ver))
    say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {shift:>5} {n:>6} {dd['Z1']:>5.2f} {rel['z_attendu']:>6.2f} {z:>6.2f} "
        f"{dd['detectes']:>3}/{dd['plantes']:<2} {dd['identifies']:>3}/{dd['plantes']:<1} {dd['faux_positifs']:>2} {time.time() - t0:>7.1f}")
say(f"   faux positifs sur les flux nuls : {FP_TOTAL}")
assert FP_TOTAL == 0

# ==========================================================================
rule("4. LE DECODAGE DE L'ARCHIVE")
# ==========================================================================

DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 2:
            DEJA[t[0]] = champs(l)
    say(f"   reprise : {len(DEJA)} decodages deja faits, ecrits dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")
say(f"""
       {'K':>2} {'L':>2} {'S':>3} {'mode':>7} {'Z1':>5} {'M':>9} {'z_att':>6} {'zmax':>6} {'z2':>6} {'zy':>6} {'zlin':>6} {'contra':>6} {'sec':>7}""")
LIG, DETEC = [], []
for K, L in ORDRE:
    for mode, S in VARIANTES:
        cle = f"flux,{K},{L},{S},{mode}"
        Z1 = seuil(L)
        if cle in DEJA:
            r = DEJA[cle]
        else:
            lignes = lance([K, L, S, mode, FARCH, MMAX])
            rel, fin = lit(lignes, "RELATIONS"), lit(lignes, "FIN")
            fl = lit(lignes, "FLUX") if rel["M"] > 0 else {}
            r = dict(M=rel["M"], paires=rel["paires"], z_att=rel["z_attendu"], zmax=fl.get("zmax", 0.0),
                     pmax=fl.get("pmax", 0), z2=fl.get("z2", 0.0), rang_chi=fl.get("rang_chi", 0),
                     zy=fl.get("zy", 0.0), y=fl.get("y", 0), contra=fl.get("contradictions", -1),
                     zlin=fin["zlin"], plin=fl.get("plin", 0), sec=fin["sec"],
                     det=int(fin["detecte"]), det_lin=int(fin["detecte_lin"]))
            jr.write(cle + " " + " ".join(f"{k}={v:#x}" if k in ("pmax", "y", "plin") else f"{k}={v}"
                                          for k, v in r.items()) + "\n")
            jr.flush()
        conf = (r["det"] or r["det_lin"]) and r["zy"] >= Z1 and r["contra"] == 0
        LIG.append((K, L, S, mode, r, conf))
        if r["det"] or r["det_lin"]:
            DETEC.append((K, L, S, mode, r, conf))
        say(f"       {K:>2} {L:>2} {S:>3} {mode:>7} {Z1:>5.2f} {r['M']:>9} {r['z_att']:>6.2f} {r['zmax']:>6.2f} {r['z2']:>6.2f} "
            f"{r['zy']:>6.2f} {r['zlin']:>6.2f} {r['contra']:>6} {r['sec']:>7.1f}"
            + ("" if not (r["det"] or r["det_lin"]) else "   !! CONFIRME" if conf else "   !!"))

D_TOT = sum(l[4]["det"] + l[4]["det_lin"] for l in LIG)
C_TOT = sum(1 for l in LIG if l[5])
SEC = sum(l[4]["sec"] for l in LIG)
ZMAX = max(l[4]["zmax"] for l in LIG)
ZLIN = max(l[4]["zlin"] for l in LIG)
ZATT_MIN = min(l[4]["z_att"] for l in LIG)
ZATT_MAX = max(l[4]["z_att"] for l in LIG)
M_MIN = min(l[4]["M"] for l in LIG)
lmax = max(LIG, key=lambda l: l[4]["zmax"])
llin = max(LIG, key=lambda l: l[4]["zlin"])
say(f"""
   {len(LIG)} decodages, {2 * len(LIG)} statistiques ; D = {D_TOT} detectee, {C_TOT} confirmee ;
   z max (relations, shift 1) = {ZMAX:.2f} (x^{lmax[1]}+x^{lmax[1]-lmax[0]}+1 {lmax[3]} pas {lmax[2]}, Z1 = {seuil(lmax[1]):.2f}) ;
   zlin max (plan 0, shift 0) = {ZLIN:.2f} (x^{llin[1]}+x^{llin[1]-llin[0]}+1 {llin[3]} pas {llin[2]}, Z1 = {seuil(llin[1]):.2f}) ;
   z attendu si l'hypothese etait vraie : {ZATT_MIN:.1f} a {ZATT_MAX:.1f} (M de {M_MIN:,} a {MMAX:,} relations) ;
   {SEC/60:.1f} min de decodage cumulees.""")
for K, L, S, mode, r, conf in DETEC:
    say(f"     !! x^{L}+x^{L-K}+1 {mode} pas {S} : {r}")
if D_TOT == 0:
    say(f"""     AUCUNE DETECTION : sous le flux continu, aucun des 44 trinomes de degre 15 a 31 — TYPE_3
     a shift 1 compris, ce que h140 ne pouvait pas tester — n'engendre l'archive, a shift 1 ni a shift 0.""")

# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = ("conforme" if D_TOT == 0 else "ETAT TROUVE" if C_TOT else "DETECTION NON CONFIRMEE")
    puiss = "; ".join(
        f"x^{L}+x^{L-K}+1 {mode} pas {S} shift {shift} N={n} : z_attendu {rel['z_attendu']:.1f}, z {ver['zmax'] if shift else ver['zlin']:.1f}, "
        f"detectes {dd['detectes']}/{dd['plantes']}, identifies (p, y, coherence) {dd['identifies']}/{dd['plantes']}"
        for K, L, S, mode, shift, n, dd, rel, ver in TEMOINS)
    lab.record(
        TOK, float(D_TOT), p=1.0 if D_TOT == 0 else min(1.0, 2 * len(LIG) * 1e-7), verdict=verdict,
        power_at=(f"temoins plantes + nuls de ce script : {puiss} — {FP_TOTAL} faux positif sur les flux nuls ; "
                  f"sur l'archive z attendu {ZATT_MIN:.1f} a {ZATT_MAX:.1f} pour un etat vrai (Z1 de "
                  f"{seuil(15):.2f} a {seuil(31):.2f})"),
        notes=(f"RELATIONS DE POIDS 3 SUR Z/4 SOUS LE FLUX (§7.14) : {len(LIG)} decodages ({len(ORDRE)} trinomes "
               f"de degre 15 a 31 x {len(VARIANTES)} variantes), {2 * len(LIG)} statistiques (shift 1 par les "
               f"relations, shift 0 par la WHT lineaire des mots). D = {D_TOT}, {C_TOT} confirme ; z max {ZMAX:.2f} "
               f"(relations), zlin max {ZLIN:.2f}. M de {M_MIN:,} a {MMAX:,} relations. {SEC/60:.1f} min de "
               f"decodage. NON COUVERT : reamorcage (par nuit M ~ 10^-3 : rien), TYPE_4 (1, 63), shift >= 2, "
               f"rejet, troncature, Fibonacci soustractif, pas variable."))
    h = lab.holm()
    say(f"   consigne : {EXP_ID}   verdict {verdict}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")
say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
