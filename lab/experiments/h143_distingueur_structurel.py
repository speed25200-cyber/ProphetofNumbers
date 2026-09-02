"""h143 — le DISTINGUEUR STRUCTUREL (§7.15) : toutes les relations de poids 3 du plan 0, sans etat,
retard L quelconque (TYPE_4 (1, 63) compris), sous le flux ET par bloc de nuit.

Un Fibonacci retarde r_i = r_(i-K) o r_(i-L) (o = +, - mod 2^32 ou xor) a un plan 0 qui verifie
EXACTEMENT b_i = b_(i-K) xor b_(i-L), polynome f = x^L + x^(L-K) + 1 (pour xor, tous les plans).
Quand la sortie est x = r (shift 0 ; pour xor tout shift), le bit 0 des mots pairs k = 0..18 est
observe mollement par l'ensemble trie : la variable molle du tirage est T = (impairs - pairs)/20,
C(k') = E[(T - E0) (-1)^b_k'] ~ 0,038 pour chaque mot pair (calibrage). Toute RELATION DE POIDS 3
(d, j) — x^j + x^d + 1 = 0 mod f, ENUMEREES TOUTES jusqu'a l'etendue de l'archive (puissances de x
mod f triees) — envoie (t_a, mot k) sur deux autres tirages (t_a + d1, t_a + d2) ; le MOTIF (d1, d2)
recoit w += C C C. La statistique est
    Lambda = sum_motifs w_p sum_ta T_ta T_(ta+d1) T_(ta+d2),  V = tau^6 sum_p w_p^2 n_p,  z = Lambda/sqrt(V),
    z_attendu = sqrt(sum_p w_p^2 n_p)/tau^3,
exacte sous H0 (T centres independants, triples distincts non correles), SANS borne d'union sur
2^L : le seuil est celui de la grille, Zc = Q^-1(10^-7 / NTESTS). Elle se somme sur les blocs
(mode bloc : un etat par nuit). Ce qu'elle ne voit pas : + et - a shift 1 (glibc random() : le plan
1 est equilibre sur les relations, §7.15) — c'est le domaine de h142 (WHT 2^L, L <= 31).

Grille : tous les trinomes primitifs de degre 7 a 63 (les deux orientations K et L-K), les retards
classiques (55, 89, 100, 127, 250, 258, 521, 1279) ; 9 variantes (FY partiel par modulo aux pas 20 a
24, 79, 80 ; Collections.shuffle aux pas 79 et 80) ; flux (un etat) et bloc (370 blocs de nuit).

Temoins : etats plantes (+ shift 0, - shift 0, xor shift 1 et 3, bloc 370) puis tirages nuls, et
le TEMOIN NEGATIF (+ shift 1 : aucune detection attendue), avec le binaire compile par ce script.
Pre-enregistre AVANT tout decodage de l'archive ; consigne UNE ligne au registre.
Reprise : /tmp/h143_journal.txt. H143_DRY=1 : essai a blanc (3 trinomes, 2 variantes, 5 000
tirages, rien n'est consigne).
"""
import json
import math
import os
import random
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H143_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H143_TMP", "/tmp")
EXP_ID = "h143.distingueur_structurel"


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


# ----------------------------------------------------------------- trinomes primitifs (test d'ordre)
def _premier(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):        # deterministe sous 3,3e24
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _rho(n):
    if n % 2 == 0:
        return 2
    rg = random.Random(n)
    while True:
        y, c, m = rg.randrange(1, n), rg.randrange(1, n), 128
        g, r, q = 1, 1, 1
        while g == 1:
            x = y
            for _ in range(r):
                y = (y * y + c) % n
            k = 0
            while k < r and g == 1:
                ys = y
                for _ in range(min(m, r - k)):
                    y = (y * y + c) % n
                    q = q * abs(x - y) % n
                g = math.gcd(q, n)
                k += m
            r *= 2
        if g == n:
            g = 1
            while g == 1:
                ys = (ys * ys + c) % n
                g = math.gcd(abs(x - ys), n)
        if g != n:
            return g


def facteurs_premiers(n):
    f = set()
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        while n % p == 0:
            f.add(p)
            n //= p
    pile = [n] if n > 1 else []
    while pile:
        m = pile.pop()
        if m == 1:
            continue
        if _premier(m):
            f.add(m)
            continue
        d = _rho(m)
        pile += [d, m // d]
    return f


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


_FACT = {}


def primitif(K, L):
    p = (1 << L) | (1 << K) | 1
    n = (1 << L) - 1
    if _powmod(2, n, p, L) != 1:
        return False
    if L not in _FACT:
        _FACT[L] = facteurs_premiers(n)
    return all(_powmod(2, n // q, p, L) != 1 for q in _FACT[L])


NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3", (1, 63): "TYPE_4"}
t_prim = time.time()
PRIMITIFS = [(K, L) for L in range(7, 64) for K in range(1, L) if primitif(K, L)]
assert all(t in PRIMITIFS for t in NOMS) and (24, 55) in PRIMITIFS and (31, 55) in PRIMITIFS
CLASSIQUES = [(38, 89), (51, 89), (37, 100), (63, 100), (30, 127), (97, 127), (103, 250), (147, 250),
              (83, 258), (175, 258), (32, 521), (489, 521), (216, 1279), (1063, 1279), (418, 1279), (861, 1279)]
TETE = [(1, 63), (3, 31), (1, 15), (3, 7)]
ORDRE = TETE + CLASSIQUES + [t for t in sorted(PRIMITIFS, key=lambda t: (-t[1], t[0])) if t not in TETE]
VARIANTES = [("fy", s) for s in (20, 21, 22, 23, 24, 79, 80)] + [("shuffle", s) for s in (79, 80)]
CIBLES = ("flux", "bloc")
SCHEMAS = ("Fisher-Yates partiel par modulo aux pas 20 a 24, 79 et 80 ; "
           "Collections.shuffle vingt dernieres cases aux pas 79 et 80")
if DRY:
    ORDRE = [(1, 63), (3, 31), (24, 55)]
    VARIANTES = [("fy", 20), ("shuffle", 79)]
NTESTS = len(ORDRE) * len(VARIANTES) * len(CIBLES)
ZC = Qinv(1e-7 / NTESTS)

BIN = os.path.join(TMP, "lfg_struct_flux_h143")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN, os.path.join(DEPOT, "tools", "lfg_struct_flux.c"), "-lm"],
               check=True, capture_output=True)
ENV = dict(os.environ, STRUCT_NTESTS=str(NTESTS))


def champs(l):
    dd = {}
    for t in l.split():
        if "=" in t:
            a, b = t.split("=", 1)
            b = b.replace("(tronquees)", "").replace("(plein)", "")
            try:
                dd[a] = int(b) if b.lstrip("-").isdigit() else float(b)
            except ValueError:
                dd[a] = b
    return dd


def lit(lignes, prefixe):
    for l in reversed(lignes):
        if l.startswith(prefixe + " "):
            return champs(l)
    raise RuntimeError("pas de ligne " + prefixe)


def lance(args, env=None):
    p = subprocess.run(["nice", "-n", "10", BIN] + [str(a) for a in args], capture_output=True, text=True,
                       timeout=24 * 3600, env=env or ENV)
    assert p.returncode == 0, (args, p.stderr[-2000:])
    return p.stdout.strip().split("\n")


# ==========================================================================
rule("1. L'ARCHIVE : UN FLUX, 370 BLOCS DE NUIT ; LA GRILLE")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
assert np.all(np.diff(TS) > 0)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
coupe = np.flatnonzero(np.diff(TS) != 300)
DEB = np.r_[0, coupe + 1]
if DRY:
    NTOT = 5000
    DEB = DEB[DEB < NTOT]
SUFF = "_dry" if DRY else ""
FARCH = os.path.join(TMP, f"h143_archive{SUFF}.txt")
with open(FARCH, "w") as fh:
    for t in range(NTOT):
        fh.write(" ".join(str(v) for v in NUM[t].tolist()) + "\n")
FBLOCS = os.path.join(TMP, f"h143_blocs{SUFF}.txt")
with open(FBLOCS, "w") as fh:
    for d in DEB:
        fh.write(f"{int(d)}\n")
NBLOCS = len(DEB)
par_degre = {}
for K, L in PRIMITIFS:
    par_degre.setdefault(L, []).append(K)
say(f"""
   {NTOT} tirages tries, dans l'ordre du temps : un FLUX (un seul etat) et {NBLOCS} BLOCS de nuit
   (ruptures de la cadence de 300 s, un etat par bloc). {len(PRIMITIFS)} trinomes primitifs de degre 7 a
   63 (test d'ordre, {time.time() - t_prim:.1f} s ; degres representes : {sorted(par_degre)}) + {len(CLASSIQUES)} retards
   classiques (89, 100, 127, 250 = R250, 258, 521 = R521, 1279) = {len(ORDRE)} trinomes x {len(VARIANTES)} variantes
   ({SCHEMAS}) x {len(CIBLES)} cibles = {NTESTS} statistiques ; Zc = Q^-1(10^-7 / {NTESTS}) = {ZC:.2f}.""")

# ==========================================================================
rule("2. PRE-ENREGISTREMENT (avant tout decodage de l'archive)")
# ==========================================================================

JOURNAL = os.path.join(TMP, f"h143_journal{SUFF}.txt")
FJETON = os.path.join(TMP, "h143_jeton.json")
HYPOTHESE = (
    "L'archive triee (70 560 tirages dans l'ordre du temps) n'est engendree, ni sous le FLUX CONTINU "
    f"(un seul etat) ni par BLOC DE NUIT ({NBLOCS} blocs, un etat par bloc), par aucun Fibonacci retarde "
    "r_i = r_(i-K) o r_(i-L) lu a pas constant dont le plan 0 est observe (o = + ou - mod 2^32 a shift 0, "
    "x = r ; o = xor a tout shift), pour les "
    f"{len(PRIMITIFS)} trinomes primitifs de degre 7 a 63 (TYPE_1 a TYPE_4 compris, les deux orientations) "
    f"et les {len(CLASSIQUES)} retards classiques (89, 100, 127, 250, 258, 521, 1279), sous les schemas : {SCHEMAS}"
)
STATISTIQUE = (
    "nombre D de statistiques (trinome x variante x cible) DETECTEES : z >= Zc = Q^-1(10^-7 / "
    f"{NTESTS}) = {ZC:.2f}, z = Lambda/sqrt(V), Lambda = somme sur les MOTIFS (d1, d2) de toutes les "
    "relations de poids 3 (d, j) de f = x^L + x^(L-K) + 1 (j <= etendue, enumerees par tri des puissances "
    "de x mod f) du poids w_p (somme des C(k) C(k1) C(k2) calibres) fois somme_ta T_ta T_(ta+d1) "
    "T_(ta+d2), T = (impairs - pairs)/20 centre ; V = tau^6 somme_p w_p^2 n_p (§7.15)"
)
NULL = (
    "sous H0 les T des tirages sont independants et centres (moyenne empirique), deux triples de "
    "tirages distincts sont non correles : E Lambda = 0, Var Lambda = V exactement (tau^2 = variance "
    f"empirique de T) ; z de variance 1, P(z >= Zc) <= 10^-7 par statistique, E[D] <= {NTESTS} x 10^-7 "
    f"= {NTESTS * 1e-7:.1e} (queue gaussienne, calibree sur les flux nuls des temoins)"
)
VERDICT = (
    "conforme si D = 0 ; DETECTION sinon (anomalie a examiner : le trinome, la variante et la cible "
    "detectes sont alors le point de depart d'un decodage de l'etat, non conforme)"
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

# (K, L, S, mode, op, shift, N, nbloc, detection attendue)
TEMOINS_CAS = [(1, 63, 20, "fy", "add", 0, 70560, 1, 1), (1, 63, 20, "fy", "add", 1, 70560, 1, 0),
               (24, 55, 22, "fy", "sub", 0, 70560, 1, 1), (37, 100, 20, "fy", "xor", 3, 70560, 1, 1),
               (1, 63, 20, "fy", "add", 0, 70560, 370, 1), (3, 31, 79, "shuffle", "add", 0, 20000, 1, 1),
               (103, 250, 80, "shuffle", "xor", 1, 70560, 1, 1)]
if DRY:
    TEMOINS_CAS = [(1, 63, 20, "fy", "add", 0, 5000, 1, 1), (1, 63, 20, "fy", "add", 1, 5000, 1, 0)]
TEMOINS, FP_TOTAL, RATES = [], 0, 0
say(f"       {'K':>3} {'L':>4} {'S':>3} {'mode':>7} {'op':>3} {'shift':>5} {'N':>6} {'blocs':>5} {'Zc':>5} {'z_att':>7} {'z':>7} {'attendu':>7} {'detect':>6} {'fp':>2} {'sec':>6}")
for i, (K, L, S, mode, op, shift, n, nbloc, attendu) in enumerate(TEMOINS_CAS):
    t0 = time.time()
    lignes = lance(["--selftest", S, mode, n, 4300 + i, f"{K},{L}", nbloc], dict(ENV, LFG_OP=op, LFG_SHIFT=str(shift)))
    dd, ver, nul = lit(lignes, "AUTOTEST"), lit(lignes, "VERITE"), lit(lignes, "NUL")
    FP_TOTAL += dd["faux_positifs"]
    RATES += int(ver["detecte"] != attendu)
    TEMOINS.append((K, L, S, mode, op, shift, n, nbloc, attendu, dd, ver, nul))
    say(f"       {K:>3} {L:>4} {S:>3} {mode:>7} {op:>3} {shift:>5} {n:>6} {nbloc:>5} {dd['Zc']:>5.2f} {ver['z_attendu']:>7.2f} {ver['z']:>7.2f} "
        f"{attendu:>7} {ver['detecte']:>6} {dd['faux_positifs']:>2} {time.time() - t0:>6.1f}"
        + ("" if ver["detecte"] == attendu else "   !! RATE"))
say(f"   faux positifs sur les flux nuls : {FP_TOTAL} ; temoins rates : {RATES}")
assert FP_TOTAL == 0 and RATES == 0

# ==========================================================================
rule("4. LE DECODAGE DE L'ARCHIVE")
# ==========================================================================

DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 2:
            DEJA[t[0]] = champs(l)
    say(f"   reprise : {len(DEJA)} statistiques deja faites, ecrites dans {JOURNAL}")
jr = open(JOURNAL, "a", encoding="utf-8")
LIG, DETEC = [], []
for cible in CIBLES:
    for mode, S in VARIANTES:
        restants = [(K, L) for K, L in ORDRE if f"{cible},{K},{L},{S},{mode}" not in DEJA]
        if restants:
            t0 = time.time()
            p = subprocess.Popen(["nice", "-n", "10", BIN, str(S), mode, FARCH, FBLOCS if cible == "bloc" else "-"]
                                 + [f"{K},{L}" for K, L in restants], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, env=ENV)
            calib, sec = {}, {}
            for l in p.stdout:
                l = l.rstrip("\n")
                if l.startswith("CALIB ") or l.startswith("DATA "):
                    calib[l.split()[0]] = l
                elif l.startswith("FIN "):
                    d = champs(l)
                    K, L = int(l.split()[1]), int(l.split()[2])
                    r = dict(relations=d["relations"], motifs=d["motifs"], triples=d["triples"], z_att=d["z_attendu"],
                             z=d["z"], zmax_motif=d["zmax_motif"], det=int(d["detecte"]), sec=0.0)
                    sec[(K, L)] = r
                elif l.startswith("SEC "):
                    t = l.split()
                    K, L = int(t[1]), int(t[2])
                    r = sec[(K, L)]
                    r["sec"] = float(t[3])
                    cle = f"{cible},{K},{L},{S},{mode}"
                    DEJA[cle] = r
                    jr.write(cle + " " + " ".join(f"{k}={v}" for k, v in r.items()) + "\n")
                    jr.flush()
            p.wait()
            assert p.returncode == 0, (cible, S, mode, p.stderr.read()[-2000:])
            say(f"\n   {cible} {mode} pas {S} : {len(restants)} trinomes en {time.time() - t0:.0f} s ; "
                + " ; ".join(calib.get(k, "") for k in ("CALIB", "DATA")))
        say(f"\n   {cible} {mode} pas {S} :")
        say(f"       {'K':>4} {'L':>4} {'rel':>6} {'motifs':>6} {'triples':>10} {'z_att':>7} {'z':>6} {'zmax_m':>6} {'sec':>6}")
        for K, L in ORDRE:
            r = DEJA[f"{cible},{K},{L},{S},{mode}"]
            LIG.append((cible, K, L, S, mode, r))
            if r["det"]:
                DETEC.append((cible, K, L, S, mode, r))
            say(f"       {K:>4} {L:>4} {r['relations']:>6} {r['motifs']:>6} {r['triples']:>10} {r['z_att']:>7.1f} {r['z']:>6.2f} "
                f"{r['zmax_motif']:>6.2f} {r['sec']:>6.1f}" + ("   !! DETECTION" if r["det"] else "") + f"  {NOMS.get((K, L), '')}")

D_TOT = sum(l[5]["det"] for l in LIG)
SEC = sum(l[5]["sec"] for l in LIG)
# Une statistique sans motif (aucune relation ne retombe sur trois mots pairs de rang <= 18 :
# typique des pas 79 et 80) est VIDE : z = 0 par construction, elle ne teste rien.
PLEINES = [l for l in LIG if l[5]["motifs"] > 0]
VIDES = len(LIG) - len(PLEINES)
ZMAX = max(PLEINES, key=lambda l: l[5]["z"])
ZMIN = min(PLEINES, key=lambda l: l[5]["z"])
ZATT_FLUX = [l[5]["z_att"] for l in PLEINES if l[0] == "flux"] or [0.0]
ZATT_BLOC = [l[5]["z_att"] for l in PLEINES if l[0] == "bloc"] or [0.0]
zs = np.array([l[5]["z"] for l in PLEINES])
say(f"""
   {len(LIG)} statistiques dont {VIDES} vides (aucun motif) ; D = {D_TOT} detectee(s) ; z max = {ZMAX[5]['z']:.2f} (x^{ZMAX[2]}+x^{ZMAX[2]-ZMAX[1]}+1 {ZMAX[4]} pas {ZMAX[3]}
   {ZMAX[0]}), z min = {ZMIN[5]['z']:.2f}, moyenne {zs.mean():.3f}, ecart-type {zs.std():.3f} (1 attendu sous H0, sur les {len(PLEINES)} pleines) ; Zc = {ZC:.2f} ;
   z attendu si l'hypothese etait vraie : flux {min(ZATT_FLUX):.1f} a {max(ZATT_FLUX):.1f}, bloc {min(ZATT_BLOC):.1f} a {max(ZATT_BLOC):.1f} ;
   {SEC/60:.1f} min de calcul cumulees.""")
for cible, K, L, S, mode, r in DETEC:
    say(f"     !! x^{L}+x^{L-K}+1 {mode} pas {S} {cible} : {r}")
if D_TOT == 0:
    say(f"""     AUCUNE DETECTION : ni sous le flux ni par bloc, aucun Fibonacci retarde a plan 0 observe
     (+ et - a shift 0, xor a tout shift) de retard 7 a 63 ou classique n'engendre l'archive.""")

# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    TOK["m_extra"] = 0
    verdict = "conforme" if D_TOT == 0 else "DETECTION"
    puiss = "; ".join(
        f"x^{L}+x^{L-K}+1 {op} shift {shift} {mode} pas {S} blocs {nbloc} N={n} : z_attendu {ver['z_attendu']:.1f}, z {ver['z']:.1f}, "
        f"detecte {ver['detecte']} (attendu {attendu}), nul z {nul['z']:.2f}"
        for K, L, S, mode, op, shift, n, nbloc, attendu, dd, ver, nul in TEMOINS)
    lab.record(
        TOK, float(D_TOT), p=1.0 if D_TOT == 0 else min(1.0, NTESTS * 1e-7), verdict=verdict,
        power_at=(f"temoins plantes + nuls de ce script : {puiss} — {FP_TOTAL} faux positif sur les flux nuls, "
                  f"{RATES} temoin rate ; sur l'archive z attendu flux {min(ZATT_FLUX):.1f} a {max(ZATT_FLUX):.1f}, "
                  f"bloc {min(ZATT_BLOC):.1f} a {max(ZATT_BLOC):.1f} pour un etat vrai (Zc = {ZC:.2f})"),
        notes=(f"{len(LIG)} statistiques ({len(ORDRE)} trinomes x {len(VARIANTES)} variantes x flux/bloc) dont {VIDES} vides (0 motif), D = {D_TOT}, "
               f"z max {ZMAX[5]['z']:.2f} (x^{ZMAX[2]}+x^{ZMAX[2]-ZMAX[1]}+1 {ZMAX[4]} pas {ZMAX[3]} {ZMAX[0]}), "
               f"moyenne {zs.mean():.3f}, ecart-type {zs.std():.3f} ; {SEC/60:.1f} min ; journal {JOURNAL}"))
    say("   registre : une ligne ajoutee ; Holm :")
    for h in lab.holm(alpha=0.05):
        if h.get("exp_id") == EXP_ID or h.get("id") == EXP_ID:
            say(f"     {h}")
say(f"\n   duree totale {(time.time() - T0) / 60:.1f} min")
