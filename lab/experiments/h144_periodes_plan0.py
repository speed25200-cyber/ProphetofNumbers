"""h144 — le balayage d'autocorrelation du plan 0 : les relations de poids 2.

Le 7.15 (h143) teste les relations de poids 3 d'un trinome donne. Ici on ne suppose plus rien du
generateur, seulement qu'UN bit lu par l'echantillonneur (la parite du numero designe, mots pairs,
§7.15 (ii)) satisfait une relation de poids 2 :

    periodique      b_(p+qP) = b_p               pour tout p, q >= 1        (famille B, periode P)
    anti-periodique b_(p+qH) = b_p xor (q mod 2)  pour tout p, q >= 1        (famille C, demi-periode H)
    isolee          b_(p+D)  = b_p  ou  1 xor b_p  pour tout p               (famille A, un seul decalage D)

Ce que cela couvre : TOUT generateur congruentiel de module 2^W a sortie decalee de s (le bit s de
l'etat a pour periode 2^(s+1) et pour anti-periode 2^s, quels que soient a ≡ 1 mod 4, c impair, W),
donc java.util.Random (s = 17), MSVC (s = 16), glibc TYPE_0 (s = 0), et n'importe quel LCG maison ;
tout registre a decalage ou Fibonacci retarde dont la periode du plan 0 (2^L − 1) tient dans le flux ;
le plan 1 de random() TYPE_1 et TYPE_2 de la glibc (periode exacte 2 (2^L − 1) = 254 et 65 534 du bit 1 d'un
Fibonacci additif) ; et toute relation lineaire de poids 2. Le pas S (mots par tirage) place les mots ; le balayage porte
sur TOUS les decalages D de 1 a Dmax = S x (N − 10 000), tous les P et H jusqu'a Dmax/2.

Statistique (§7.16) : T_t = (impairs − pairs)/20, NON centre (E T = 0 exactement sous H0 : 40 impairs,
40 pairs) ; A(d) = somme_t T_t T_(t+d), d >= 1 (FFT) ; un decalage D = S q + rho envoie le mot pair k du
tirage t sur le mot k + rho du tirage t + q (ou k + rho − S du tirage t + q + 1) ; c_q(rho), c_(q+1)(rho)
= nombre de mots pairs qui retombent sur un mot pair de rang <= 18 ; Lambda_A(D) = c_q A(q) + c_(q+1)
A(q+1) (le terme q = 0, deux mots du MEME tirage, n'est pas un produit de tirages distincts : il est
exclu des familles A, B, C et porte la famille D), V_A = tau^4 (c_q^2 n_q + c_(q+1)^2 n_(q+1)) ; les
familles B et C somment Lambda_A sur les multiples (comptes signes agreges s_d quand deux multiples
retombent sur le meme d). z = Lambda / sqrt(V), de variance 1 exactement sous H0 (tirages independants,
E T = 0 : deux paires distinctes sont non correlees). Signal si la relation est vraie :
z_att = (C^2/tau^2) sqrt(somme_d e_d^2 n_d), C = 3/79 (§7.15 (iii)).
Famille D (une statistique) : E[T^2] = 3/79 exactement sous H0 ; une relation de poids 2 ENTRE DEUX MOTS
PAIRS DU MEME TIRAGE (periode <= 18) rend les deux parites designees egales (ou opposees) et deplace
E[T^2] de delta_D = (40/79)(E[T^2 | memes parites] − E[T^2 | opposees]) = 236/79079 = 0,00298 par paire
(exact, hypergeometrique) : z_D = (moy(T^2) − 3/79) sqrt(N) / et(T^2) ; une seule paire donne z ≈ 15 sur l'archive.
Ni centrage ni retrait de moyenne : un bit constant sur la grille paire (periode divisant S) donne
E T = ±10 C et se lit dans la famille B (P divisant S : tous les retards).

Seuil : bilateral, Zc = Q^-1(10^-7 / (2 M)), M = nombre total de statistiques de la grille (toutes
familles, tous pas, flux et bloc, + 1 pour D) ; n_d >= 10 000 pour toute statistique.

Temoins : la detection attendue n'est pas fixee a la main mais PREDITE au premier ordre (§7.16 (ix)) :
T_t ≈ C (U_t − mu), U_t = somme des 20 signes designes (-1)^j reellement tires par l'echantillonneur temoin,
mu = E U = -+ somme des 1/b sur les dix bornes impaires b = 61..79 = -+0,1438 (E T = 0 exactement, mais
r mod b est pair (b+1)/2 fois sur b : Fisher-Yates lit j = k + (r mod b) avec k impair quand b l'est, mu = -0,1438 ;
Collections.shuffle lit j = r mod b, mu = +0,1438 ; sans ce centrage la constante mu^2 n_d de A_U(d) donne
un z_att fantome ≈ 40 dans la famille « tous les retards », P = S ou P = 1, et le mauvais signe en donne un de 150) ;
A_att(d) = C^2 A_(U−mu)(d) passe dans la meme grille donne z_att en chaque statistique (relations exactes ET
correlations partielles du generateur : retenue des LCG aux retards 2^(s-j), bornes impaires, borne 64 de
Java) ; famille D : E[T^2] - 3/79 ≈ (memes - opp)(Var U - sigma_U^2)/4, sigma_U^2 = 20 − somme 1/b^2 = 19,9979.
Un temoin est rate si la detection observee contredit la prediction hors d'une marge de 2 autour de Zc.

Usage : python3 lab/experiments/h144_periodes_plan0.py
        H144_DRY=1 : temoins et flux nuls a l'echelle de l'archive (structure des blocs seulement,
        aucune statistique de l'archive n'est calculee), sans jeton, sans balayage.
"""
import json
import math
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H144_DRY") == "1"
TMP = os.environ.get("H144_TMP", "/tmp")
EXP_ID = "h144.periodes_plan0"
ALPHA = 1e-7
NMIN = 10000
PAS = [20, 21, 22, 23, 24, 79, 80]
KPAIRS = list(range(0, 20, 2))
C_TH = 3.0 / 79.0                      # E[T (-1)^b_k] pour un mot pair, calibrage exact du §7.15 (iii)
TAU2_TH = 3.0 / 79.0                   # E[T^2] exact sous H0 (hypergeometrique 20 parmi 40 + 40)


def _moments_D():
    """sous H0 : et(T^2) exact ; et decalage exact de E[T^2] quand deux numeros designes ont la meme parite
    (au lieu de la meme parite avec probabilite 39/79) : delta_D = (40/79)(E[T^2 | memes] - E[T^2 | opposees])."""
    from fractions import Fraction as Fr
    from math import comb

    def hyp(Npop, K, n):
        return {x: Fr(comb(K, x) * comb(Npop - K, n - x), comb(Npop, n))
                for x in range(max(0, n - (Npop - K)), min(n, K) + 1)}

    p = hyp(80, 40, 20)
    et2 = sum(pr * Fr((x - 10) ** 2, 100) for x, pr in p.items())
    et4 = sum(pr * Fr((x - 10) ** 4, 10000) for x, pr in p.items())
    assert et2 == Fr(3, 79)

    def cond(p1, p2):
        return sum(pr * Fr((p1 + p2 + x - 10) ** 2, 100) for x, pr in hyp(78, 40 - p1 - p2, 18).items())

    memes = (cond(1, 1) + cond(0, 0)) / 2
    delta = Fr(40, 79) * (memes - cond(1, 0))
    assert Fr(39, 79) * memes + Fr(40, 79) * cond(1, 0) == et2
    return math.sqrt(float(et4 - et2 * et2)), float(delta), float(memes - cond(1, 0))


STD_T2_H0, DELTA_D, MEMES_OPP = _moments_D()   # 0.052908 (aplatissement 2.94) ; 236/79079 = 0.0029844 par paire ; 0.0058940


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


# ----------------------------------------------------------------- la statistique T et ses autocorrelations
def statT(NUM):
    """T = (impairs - pairs)/20 par tirage, NON centre ; tau2 = moyenne empirique de T^2."""
    T = (2.0 * (NUM % 2).sum(1) - 20.0) / 20.0
    return T, float((T * T).mean())


def famille_D(T):
    """z_D = (moy(T^2) - 3/79) sqrt(N) / et(T^2) : relations de poids 2 entre mots pairs d'un meme tirage."""
    T2 = T * T
    return float((T2.mean() - TAU2_TH) * math.sqrt(len(T)) / T2.std())


def z_attendu_D(relations, N, kset=KPAIRS):
    """z attendu de la famille D : paires (k, k + qP) de mots pairs <= 18 d'un meme tirage, signees ;
    chaque paire deplace E[T^2] de delta_D (additif au premier ordre : exact pour une paire, -10 % a
    dix numeros designes de meme parite), et(T^2) prise sous H0."""
    m = 0.0
    for P, alt in relations:
        for q in range(1, 19):
            if q * P > 18:
                break
            sg = -1.0 if (alt and q % 2 == 1) else 1.0
            m += sg * sum(1 for k in kset if k + q * P <= 18 and (k + q * P) % 2 == 0)
    return abs(m) * DELTA_D * math.sqrt(N) / STD_T2_H0


def autocorr_flux(Tc, dmax):
    n = len(Tc)
    m = 1
    while m < 2 * n:
        m *= 2
    F = np.fft.rfft(Tc, m)
    A = np.fft.irfft(F * np.conj(F), m)[:dmax + 1]
    nd = (n - np.arange(dmax + 1)).astype(np.float64)
    return A, nd


def autocorr_bloc(Tc, DEB, dmax):
    """somme sur les blocs [DEB[b], DEB[b+1]) des autocorrelations internes."""
    N = len(Tc)
    fins = list(DEB[1:]) + [N]
    A = np.zeros(dmax + 1)
    nd = np.zeros(dmax + 1)
    for d0, d1 in zip(DEB, fins):
        x = Tc[d0:d1]
        n = len(x)
        m = 1
        while m < 2 * n:
            m *= 2
        F = np.fft.rfft(x, m)
        a = np.fft.irfft(F * np.conj(F), m)[:min(dmax, n - 1) + 1]
        A[:len(a)] += a
        nd[:n] += n - np.arange(n)
    return A, nd


def dmax_tirages(nd):
    """plus grand d tel que n_d >= NMIN (et d+1 aussi utilisable)."""
    ok = np.flatnonzero(nd >= NMIN)
    return int(ok.max()) - 1


# ----------------------------------------------------------------- la grille d'un pas S
def tables_c(S, kset=KPAIRS):
    """c_q[rho], c_(q+1)[rho] : mots pairs k de kset retombant sur un mot pair de kset apres un decalage rho
    (la grille prend kset = tous les mots pairs <= 18 ; un temoin peut en retirer un, ex. Java a la borne 64)."""
    rho = np.arange(S)
    cq = np.zeros(S, dtype=np.int64)
    cq1 = np.zeros(S, dtype=np.int64)
    ks = np.asarray(sorted(kset))
    for k in kset:
        kk = k + rho
        cq += ((kk < S) & np.isin(kk, ks)).astype(np.int64)
        cq1 += ((kk >= S) & np.isin(kk - S, ks)).astype(np.int64)
    return cq, cq1


def accumule(S, P, signe_alterne, Dmax, cq, cq1, ndmax):
    """comptes signes s_d des paires (mot pair -> mot pair) engendrees par les multiples qP <= Dmax."""
    q = np.arange(1, Dmax // P + 1)
    D = q * P
    dd = D // S
    rho = D % S
    sg = np.where(q % 2 == 1, -1.0, 1.0) if signe_alterne else np.ones(len(q))
    w0 = sg * cq[rho]
    w0[dd == 0] = 0.0                              # deux mots du meme tirage : hors des familles A, B, C
    s = np.bincount(dd, weights=w0, minlength=ndmax + 2)
    s += np.bincount(dd + 1, weights=sg * cq1[rho], minlength=ndmax + 2)
    return s[:ndmax + 1]


def grille(A, nd, S, tau2, dmax):
    """z des trois familles pour le pas S. Retourne dict de tableaux (index = D, P ou H ; 0 inutilise)."""
    cq, cq1 = tables_c(S)
    Dmax = S * dmax - 1
    D = np.arange(Dmax + 1)
    q = D // S
    r = D % S
    w0 = np.where(q == 0, 0, cq[r])                # D < S : deux mots du meme tirage, hors de A (famille D)
    LamA = w0 * A[q] + cq1[r] * A[q + 1]
    VA = tau2 ** 2 * (w0 ** 2 * nd[q] + cq1[r] ** 2 * nd[q + 1])
    LamA[0] = 0.0
    VA[0] = 0.0
    Pmax = Dmax // 2
    LamB = LamA[:Pmax + 1].copy()
    VB = VA[:Pmax + 1].copy()
    LamC = -LamA[:Pmax + 1].copy()
    VC = VA[:Pmax + 1].copy()
    P0 = 2 * S                                     # au-dela, les multiples ne se recouvrent jamais (§7.16 (iv))
    Qmax = Dmax // P0
    for qq in range(2, Qmax + 1):
        pm = min(Pmax, Dmax // qq)
        if pm < P0:
            break
        sl = LamA[qq * P0: qq * pm + 1: qq]
        sv = VA[qq * P0: qq * pm + 1: qq]
        LamB[P0:pm + 1] += sl
        VB[P0:pm + 1] += sv
        LamC[P0:pm + 1] += (sl if qq % 2 == 0 else -sl)
        VC[P0:pm + 1] += sv
    for P in range(1, min(P0, Pmax + 1)):        # petits P et H : accumulation explicite (recouvrements)
        s = accumule(S, P, False, Dmax, cq, cq1, dmax)
        LamB[P] = float(np.dot(s, A[:dmax + 1]))
        VB[P] = tau2 ** 2 * float(np.dot(s * s, nd[:dmax + 1]))
        s = accumule(S, P, True, Dmax, cq, cq1, dmax)
        LamC[P] = float(np.dot(s, A[:dmax + 1]))
        VC[P] = tau2 ** 2 * float(np.dot(s * s, nd[:dmax + 1]))

    def z_de(L, V):
        z = np.zeros(len(L))
        ok = V > 0
        z[ok] = L[ok] / np.sqrt(V[ok])
        return z, ok
    zA, okA = z_de(LamA, VA)
    zB, okB = z_de(LamB, VB)
    zC, okC = z_de(LamC, VC)
    return dict(zA=zA, okA=okA, zB=zB, okB=okB, zC=zC, okC=okC, Dmax=Dmax, Pmax=Pmax)


def z_attendu(S, relations, nd, dmax, tau2, kset=KPAIRS):
    """z attendu de la statistique adaptee a une verite : relations = liste de (P, alterne)
    (periode pure ou anti-periode) ; matched filter s = e ; z_att = (C^2/tau2) sqrt(somme e^2 n)."""
    cq, cq1 = tables_c(S, kset)
    Dmax = S * dmax - 1
    best = 0.0
    for P, alt in relations:
        if P > Dmax:
            continue
        e = accumule(S, P, alt, Dmax, cq, cq1, dmax)
        best = max(best, C_TH ** 2 / tau2 * math.sqrt(float(np.dot(e * e, nd[:dmax + 1]))))
    return best


def resume(g, Zc):
    """max |z| par famille et nombre de detections."""
    out = {}
    for fam, key, ok in (("A", "zA", "okA"), ("B", "zB", "okB"), ("C", "zC", "okC")):
        z = g[key]
        m = np.abs(z)
        i = int(m.argmax())
        det = int((m >= Zc).sum())
        okv = g[ok]
        out[fam] = dict(zmax=float(z[i]), arg=i, det=det, n=len(z) - 1, pleines=int(okv.sum()),
                        moy=float(z[okv].mean()) if okv.any() else 0.0,
                        et=float(z[okv].std()) if okv.any() else 0.0)
    return out


# ----------------------------------------------------------------- generateurs temoins (flux de mots -> tirages)
def flux_lcg(npos, a, c, W, s, x0):
    mask = (1 << W) - 1
    out = np.empty(npos, dtype=np.uint64)
    x = x0 & mask
    for i in range(npos):
        x = (a * x + c) & mask
        out[i] = x >> s
    return out


def flux_lfg(npos, K, L, graine, shift=0):
    """Fibonacci additif r_i = r_(i-K) + r_(i-L) mod 2^32, sortie r >> shift (shift 1 : random() de la glibc)."""
    rng = random.Random(graine)
    r = [rng.getrandbits(32) for _ in range(L)]
    out = np.empty(npos, dtype=np.uint64)
    for i in range(npos):
        if i >= L:
            r.append((r[i - K] + r[i - L]) & 0xFFFFFFFF)
        out[i] = r[i] >> shift
    return out


def flux_mt(npos, graine):
    rng = random.Random(graine)
    return np.array([rng.getrandbits(31) for _ in range(npos)], dtype=np.uint64)


def tirages(words, N, S, mode, java=False):
    """tirages tries (N x 20) : fy partiel (20 premiers) ou shuffle (20 dernieres cases), pas S.
    Retourne aussi U_t = somme des signes designes (-1)^j des 20 pas qui fixent le tirage (fy : k = 0..19 ;
    shuffle : cases 79..60), tels que l'echantillonneur les a REELLEMENT tires (bornes paires et impaires,
    borne 64 de Java comprise) : c'est la verite au premier ordre, T ≈ C U (§7.16 (ix))."""
    words = words.tolist()
    NUM = np.empty((N, 20), dtype=np.int64)
    U = np.empty(N, dtype=np.float64)
    for t in range(N):
        base = S * t
        arr = list(range(1, 81))
        u = 0
        if mode == "fy":
            for k in range(20):
                r = words[base + k]
                b = 80 - k
                j = k + ((b * r) >> 31 if (java and b & (b - 1) == 0) else r % b)
                u += 1 - 2 * (j & 1)
                arr[k], arr[j] = arr[j], arr[k]
            NUM[t] = sorted(arr[:20])
        else:
            for i in range(79, 79 - S, -1):
                if i <= 0:
                    break
                r = words[base + 79 - i]
                b = i + 1
                j = ((b * r) >> 31 if (java and b & (b - 1) == 0) else r % b)
                if i >= 60:
                    u += 1 - 2 * (j & 1)
                arr[i], arr[j] = arr[j], arr[i]
            NUM[t] = sorted(arr[60:])
        U[t] = u
    return NUM, U


def tirages_nuls(N, graine):
    rng = np.random.default_rng(graine)
    return np.sort(np.array([rng.choice(80, 20, replace=False) + 1 for _ in range(N)]), axis=1), None


# ==========================================================================
rule("1. L'ARCHIVE : UN FLUX, 370 BLOCS DE NUIT ; LA GRILLE ET SON SEUIL")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
assert np.all(np.diff(TS) > 0)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
NTOT = len(NUM)
coupe = np.flatnonzero(np.diff(TS) != 300)
DEB = np.r_[0, coupe + 1]
NBLOCS = len(DEB)
LMAX = int(np.diff(np.r_[DEB, NTOT]).max())
# la structure seule (N, blocs) fixe les n_d, les Dmax, M et le seuil : rien de l'archive n'est lu ici
_, ND_FLUX = autocorr_flux(np.ones(NTOT), NTOT - 1)
DMAX_FLUX = dmax_tirages(ND_FLUX)
_, ND_BLOC = autocorr_bloc(np.ones(NTOT), DEB, LMAX - 1)
DMAX_BLOC = dmax_tirages(ND_BLOC)
M_ABC = sum(2 * (S * dm - 1) for S in PAS for dm in (DMAX_FLUX, DMAX_BLOC))
M_TOTAL = M_ABC + 1                                  # + la famille D
ZC = Qinv(ALPHA / (2 * M_TOTAL))
say(f"""
   {NTOT} tirages tries, dans l'ordre du temps : un FLUX (un seul etat) et {NBLOCS} BLOCS de nuit
   (ruptures de la cadence de 300 s, un etat par bloc ; bloc le plus long {LMAX} tirages).
   T = (impairs - pairs)/20 non centre (E T = 0, E T^2 = 3/79 = {TAU2_TH:.5f} exactement sous H0).
   Autocorrelations d >= 1 : flux d <= {DMAX_FLUX} (n_d >= {NMIN}), bloc d <= {DMAX_BLOC} (n_d = somme des blocs >= {NMIN}).
   Pas S : {PAS} (fy et shuffle placent les mots de la meme facon : un seul balayage par pas).
   Familles : A (un decalage D <= Dmax = S x dmax - 1), B (periode P <= Dmax/2, tous les multiples),
   C (anti-periode H <= Dmax/2, signes alternes), D (E T^2 = 3/79 : paires d'un meme tirage) ;
   M = {M_TOTAL} statistiques bilaterales ; Zc = Q^-1(10^-7 / (2 M)) = {ZC:.2f}.""")

# ==========================================================================
rule("2. PRE-ENREGISTREMENT (avant tout balayage de l'archive)")
# ==========================================================================

JOURNAL = os.path.join(TMP, f"h144_journal{'_dry' if DRY else ''}.txt")
FJETON = os.path.join(TMP, "h144_jeton.json")
HYPOTHESE = (
    f"L'archive triee ({NTOT} tirages dans l'ordre du temps) n'est engendree, ni sous le FLUX CONTINU "
    f"(un seul etat) ni par BLOC DE NUIT ({NBLOCS} blocs), par aucun generateur dont le bit lu par "
    "l'echantillonneur a modulo (parite du numero designe, mots pairs k <= 18, §7.15 (ii)) satisfait une "
    "relation de poids 2 : periodique (b_(p+qP) = b_p, P <= Dmax/2), anti-periodique (b_(p+qH) = b_p xor "
    "(q mod 2), H <= Dmax/2) ou isolee (b_(p+D) = b_p ou son complement, D <= Dmax = S(dmax) - 1), aux pas "
    f"S = {PAS} ; ce qui couvre tout LCG de module 2^W a sortie decalee de s (a = 1 mod 4, c impair, W et "
    "s quelconques, 2^s <= Dmax : java.util.Random s = 17, MSVC s = 16, glibc TYPE_0 s = 0, LCG maison), "
    "tout registre ou Fibonacci retarde de periode du plan 0 <= Dmax/2, le plan 1 de random() TYPE_1 et TYPE_2 "
    "(periode 2 (2^L - 1) = 254 et 65 534), et toute relation lineaire de poids 2"
)
STATISTIQUE = (
    "nombre D de statistiques |z| >= Zc = Q^-1(10^-7 / (2 M)) = "
    f"{ZC:.2f} (bilateral, M = {M_TOTAL}) parmi les familles A, B, C x {len(PAS)} pas x flux/bloc, plus la "
    "famille D ; z = Lambda / sqrt(V), Lambda = somme_(d>=1) s_d A(d), A(d) = somme_t T_t T_(t+d), "
    "T = (impairs - pairs)/20 NON centre, s_d = comptes (signes) des paires mot pair -> mot pair de rang <= 18 "
    "de tirages distincts engendrees par la relation, V = tau^4 somme_d s_d^2 n_d, tau^2 = moyenne empirique "
    "de T^2 ; famille D : z_D = (moy(T^2) - 3/79) sqrt(N) / et(T^2) (paires de mots pairs d'un meme tirage) (§7.16)"
)
NULL = (
    "sous H0 (20 numeros uniformes parmi 80, tirages independants) E T = 0 et E T^2 = 3/79 exactement ; deux "
    "paires de tirages distinctes sont non correlees : E Lambda = 0, Var Lambda = V exactement, "
    f"n_d >= {NMIN} pour toute statistique ; queue gaussienne : P(|z| >= Zc) <= 10^-7 / M, E[D] <= 10^-7 "
    "(verifiee sur les flux nuls des temoins : max |z| sur la grille entiere)"
)
VERDICT = (
    "conforme si D = 0 ; DETECTION sinon (le pas, la famille et le decalage detectes designent alors la "
    "periode du bit lu : point de depart d'une identification du generateur, non conforme)"
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
rule("3. TEMOINS (generateurs plantes, puis flux nuls ; meme grille, meme seuil)")
# ==========================================================================

NT = NTOT
NPOS = 80 * NT + 100
JAVA = (0x5DEECE66D, 0xB, 48, 17)
GLIBC0 = (1103515245, 12345, 31, 0)
MSVC = (214013, 2531011, 32, 16)
MMIX = (6364136223846793005, 1442695040888963407, 64, 20)
MMIX19 = (6364136223846793005, 1442695040888963407, 64, 19)
MMIX22 = (6364136223846793005, 1442695040888963407, 64, 22)


def verite_lcg(s):
    return [(1 << s, True), (1 << (s + 1), False)]


# (nom, fabrique(N) -> (NUM, U), pas vrai, cible vraie, relations exactes (P, alterne) pour z_rel, kset de z_rel,
#  detection attendue d'apres les seules relations exactes — indicative : la prediction au premier ordre decide)
TEMOINS_CAS = [
    ("java.util.Random shuffle 79", lambda: tirages(flux_lcg(NPOS, *JAVA, 0x1234567), NT, 79, "shuffle", java=True),
     79, "shuffle", "flux", verite_lcg(17), [k for k in KPAIRS if k != 16], 1),
    ("java.util.Random fy 20", lambda: tirages(flux_lcg(NPOS, *JAVA, 0x7654321), NT, 20, "fy", java=True),
     20, "fy", "flux", verite_lcg(17), [k for k in KPAIRS if k != 16], 1),
    ("glibc TYPE_0 (s=0) fy 20", lambda: tirages(flux_lcg(NPOS, *GLIBC0, 42), NT, 20, "fy"),
     20, "fy", "flux", verite_lcg(0), KPAIRS, 1),
    ("MSVC rand (s=16) fy 21", lambda: tirages(flux_lcg(NPOS, *MSVC, 99), NT, 21, "fy"),
     21, "fy", "flux", verite_lcg(16), KPAIRS, 1),
    ("MMIX 64 bits >>20 fy 22", lambda: tirages(flux_lcg(NPOS, *MMIX, 7), NT, 22, "fy"),
     22, "fy", "flux", verite_lcg(20), KPAIRS, 1),
    ("MMIX 64 bits >>19 shuffle 79", lambda: tirages(flux_lcg(NPOS, *MMIX19, 8), NT, 79, "shuffle"),
     79, "shuffle", "flux", verite_lcg(19), KPAIRS, 1),
    # 2^22 = 36 mod 79 : chaque multiple visible des relations EXACTES retombe sur un mot non lu (z_rel = 0) ;
    # mais la retenue du LCG laisse des correlations partielles aux retards 2^(s-j) (§7.16 (ix)) : z_att en juge
    ("MMIX 64 bits >>22 shuffle 79 (angle mort exact)",
     lambda: tirages(flux_lcg(NPOS, *MMIX22, 10), NT, 79, "shuffle"), 79, "shuffle", "flux", verite_lcg(22), KPAIRS, 0),
    ("MMIX 64 bits >>22 fy 20 (exact hors portee)",
     lambda: tirages(flux_lcg(NPOS, *MMIX22, 9), NT, 20, "fy"), 20, "fy", "flux", verite_lcg(22), KPAIRS, 0),
    ("Fibonacci (3,17) + shift 0 fy 20", lambda: tirages(flux_lfg(NPOS, 3, 17, 5), NT, 20, "fy"),
     20, "fy", "flux", [((1 << 17) - 1, False)], KPAIRS, 1),
    ("Fibonacci (3,17) + shift 0 shuffle 79", lambda: tirages(flux_lfg(NPOS, 3, 17, 6), NT, 79, "shuffle"),
     79, "shuffle", "flux", [((1 << 17) - 1, False)], KPAIRS, 1),
    # random() de la glibc TYPE_2 (1,15), shift 1 : le bit 1 du Fibonacci additif a pour periode 2 (2^15 - 1)
    ("glibc random() TYPE_2 (1,15) shift 1 fy 20", lambda: tirages(flux_lfg(NPOS, 1, 15, 15, shift=1), NT, 20, "fy"),
     20, "fy", "flux", [(2 * ((1 << 15) - 1), False)], KPAIRS, 1),
]


def tirages_par_bloc(fab_words, S, mode, graines):
    """un etat frais par bloc de nuit (positions repartant de 0)."""
    out = np.empty((NT, 20), dtype=np.int64)
    U = np.empty(NT, dtype=np.float64)
    fins = list(DEB[1:]) + [NT]
    for b, (d0, d1) in enumerate(zip(DEB, fins)):
        n = d1 - d0
        out[d0:d1], U[d0:d1] = tirages(fab_words(S * n + 100, graines + b), n, S, mode)
    return out, U


TEMOINS_BLOC = [
    ("glibc TYPE_0 (s=0) fy 20, un etat par nuit",
     lambda: tirages_par_bloc(lambda npos, g: flux_lcg(npos, *GLIBC0, g), 20, "fy", 1000), 20, "fy", "bloc", verite_lcg(0), KPAIRS, 1),
    ("MSVC (s=16) fy 20, un etat par nuit (hors portee)",
     lambda: tirages_par_bloc(lambda npos, g: flux_lcg(npos, *MSVC, g), 20, "fy", 2000), 20, "fy", "bloc", verite_lcg(16), KPAIRS, 0),
    ("glibc random() TYPE_1 (3,7) shift 1 fy 20, un etat par nuit",
     lambda: tirages_par_bloc(lambda npos, g: flux_lfg(npos, 3, 7, g, shift=1), 20, "fy", 3000), 20, "fy", "bloc", [(2 * ((1 << 7) - 1), False)], KPAIRS, 1),
]
NULS = [("nul PCG64 a", lambda: tirages_nuls(NT, 11)), ("nul PCG64 b", lambda: tirages_nuls(NT, 12)),
        ("nul MT19937 (random.Random) fy 20", lambda: tirages(flux_mt(NPOS, 13), NT, 20, "fy")),
        ("nul MT19937 shuffle 80", lambda: tirages(flux_mt(NPOS, 14), NT, 80, "shuffle"))]


def autocorr_cible(X, cible):
    if cible == "flux":
        A, nd = autocorr_flux(X, NTOT - 1)
        return A, nd, DMAX_FLUX
    A, nd = autocorr_bloc(X, DEB, LMAX - 1)
    return A, nd, DMAX_BLOC


def argmax_grille(g):
    """(z, (famille, index)) du plus grand |z| des trois familles d'une grille."""
    best = (0.0, ("A", 0))
    for fam in "ABC":
        z = g["z" + fam]
        i = int(np.abs(z).argmax())
        if abs(z[i]) > abs(best[0]):
            best = (float(z[i]), (fam, i))
    return best


MU_IMPAIR = sum(1.0 / b for b in range(61, 81) if b % 2 == 1)        # somme des 1/b sur les dix bornes impaires : 0,14383
SIG2_U = 20.0 - sum(1.0 / b ** 2 for b in range(61, 81) if b % 2 == 1)  # somme des variances des vingt signes : 19,99792


def mu_U(mode):
    """E U sous H0 : a une borne impaire b, r mod b est pair (b+1)/2 fois sur b, E(-1)^(r mod b) = 1/b ;
    Fisher-Yates lit j = k + (r mod b) avec b = 80 - k, donc k impair quand b l'est : E(-1)^j = -1/b ;
    Collections.shuffle lit j = r mod b : E(-1)^j = +1/b. Les bornes paires sont centrees."""
    return -MU_IMPAIR if mode == "fy" else MU_IMPAIR


def prediction(U, S, mode, cible, tau2):
    """z attendus au premier ordre (§7.16 (ix)) : T ≈ C (U − mu) donne A_att(d) = C^2 A_(U−mu)(d), passe dans
    la MEME grille (cible, S) que l'observation ; le centrage est celui de H0 (E T = 0 exactement, E U = mu
    = mu_U(mode) : les bornes impaires biaisent les signes designes, pas le tirage) ; famille D : E[T^2] - 3/79 ≈
    (memes - opp) (Var U - sigma_U^2)/4 (chaque paire de signes designes de covariance rho deplace E T^2
    de (memes - opp) rho/2)."""
    Uc = U - mu_U(mode)
    AU, nd, dm = autocorr_cible(Uc, cible)
    z, ou = argmax_grille(grille(C_TH ** 2 * AU, nd, S, tau2, dm))
    zD = MEMES_OPP * (float((Uc * Uc).mean()) - SIG2_U) / 4.0 * math.sqrt(len(U)) / STD_T2_H0
    return z, ou, zD


def evalue(NUMx, cle=None, point=None):
    """toute la grille sur un jeu de tirages : dict (cible, S) -> resume, z_D, tau2, n_d, et le z observe
    au point (famille, index) de la grille cle = (cible, S)."""
    Tx, tau2x = statT(NUMx)
    Af, ndf = autocorr_flux(Tx, NTOT - 1)
    Ab, ndb = autocorr_bloc(Tx, DEB, LMAX - 1)
    res, z_point = {}, None
    for cible, A, nd, dm in (("flux", Af, ndf, DMAX_FLUX), ("bloc", Ab, ndb, DMAX_BLOC)):
        for S in PAS:
            g = grille(A, nd, S, tau2x, dm)
            res[(cible, S)] = resume(g, ZC)
            if cle == (cible, S) and point is not None:
                z_point = float(g["z" + point[0]][point[1]])
    return res, famille_D(Tx), tau2x, dict(flux=ndf, bloc=ndb), z_point


def zmax_global(res):
    best = (0.0, None)
    for cle, r in res.items():
        for fam in "ABC":
            if abs(r[fam]["zmax"]) > abs(best[0]):
                best = (r[fam]["zmax"], (cle[0], cle[1], fam, r[fam]["arg"]))
    return best


def attendu_de(zmax_att):
    """detection attendue d'apres la prediction au premier ordre : marge de 2 autour de Zc, '?' entre."""
    if zmax_att >= ZC + 2:
        return 1
    if zmax_att <= ZC - 2:
        return 0
    return "?"


MARGE = 2.0
TEMOINS, RATES, FP_TOTAL, INDET = [], 0, 0, 0
say(f"""   z_rel : forme fermee des seules relations exactes listees (matched filter) ; z_att : prediction au premier
   ordre T ≈ C (U − mu) sur la grille vraie (U = signes designes reellement tires par l'echantillonneur temoin :
   relations exactes ET partielles ; mu = E U = -+{MU_IMPAIR:.4f} : dix bornes impaires, signe - pour fy, + pour shuffle),
   ou = (famille, index) du max ;
   z@ = z observe en ce point ; zmax = max de la grille vraie ; att = 1 si max(|z_att|, |zD_att|) >= Zc + {MARGE:.0f},
   0 si <= Zc - {MARGE:.0f}, ? entre (non compte).""")
say(f"   {'temoin':>60} {'S':>3} {'cible':>5} {'z_rel':>7} {'z_att':>8} {'ou':>11} {'z@':>8} {'zmax':>8} {'zD_att':>7} {'zD':>7} {'att':>3} {'det':>3} {'collat':>6} {'sec':>6}")
for nom, fab, S, mode, cible, verite, kset, _attendu_main in TEMOINS_CAS + TEMOINS_BLOC:
    t0 = time.time()
    NUMx, Ux = fab()
    _, tau2x = statT(NUMx)
    z_att, ou, zD_att = prediction(Ux, S, mode, cible, tau2x)
    res, zD, tau2x, nds, z_pt = evalue(NUMx, (cible, S), ou)
    r = res[(cible, S)]
    dm = DMAX_FLUX if cible == "flux" else DMAX_BLOC
    z_rel = max(z_attendu(S, verite, nds[cible], dm, tau2x, kset), z_attendu_D(verite, NT, kset))
    zmax = max((r[f]["zmax"] for f in "ABC"), key=abs)
    attendu = attendu_de(max(abs(z_att), abs(zD_att)))
    det = int(any(r[f]["det"] > 0 for f in "ABC") or abs(zD) >= ZC)
    collat = sum(res[c][f]["det"] > 0 for c in res if c != (cible, S) for f in "ABC")
    rate = attendu != "?" and det != attendu
    RATES += int(rate)
    INDET += int(attendu == "?")
    ou_txt = f"{ou[0]}{ou[1]}"
    TEMOINS.append((nom, S, cible, z_rel, z_att, ou_txt, z_pt, zmax, zD_att, zD, r, attendu, det, collat))
    say(f"   {nom:>60} {S:>3} {cible:>5} {z_rel:>7.1f} {z_att:>8.1f} {ou_txt:>11} {z_pt:>8.1f} {zmax:>8.1f} {zD_att:>7.1f} "
        f"{zD:>7.1f} {str(attendu):>3} {det:>3} {collat:>6} {time.time() - t0:>6.1f}" + ("   !! RATE" if rate else ""))
    say(f"   {'':>60}     A: D={r['A']['arg']} ({r['A']['zmax']:.1f}) ; B: P={r['B']['arg']} ({r['B']['zmax']:.1f}) ; "
        f"C: H={r['C']['arg']} ({r['C']['zmax']:.1f}) ; tau^2 = {tau2x:.4f}")
NULS_RES = []
for nom, fab in NULS:
    t0 = time.time()
    res, zD, tau2x, _, _ = evalue(fab()[0])
    fp = sum(res[c][f]["det"] for c in res for f in "ABC") + int(abs(zD) >= ZC)
    FP_TOTAL += fp
    zm, ou = zmax_global(res)
    NULS_RES.append((nom, zm, ou, zD, fp))
    say(f"   {nom:>60} : max |z| sur les {M_ABC} statistiques A/B/C = {zm:.2f} ({ou}), z_D = {zD:.2f}, "
        f"tau^2 = {tau2x:.5f}, faux positifs {fp}, {time.time() - t0:.1f} s")
say(f"   faux positifs sur les flux nuls : {FP_TOTAL} ; temoins rates : {RATES} (indetermines {INDET}) ; Zc = {ZC:.2f} ; "
    f"max |z| nul attendu ~ sqrt(2 ln M_eff) ~ {math.sqrt(2 * math.log(4 * len(PAS) * (DMAX_FLUX + DMAX_BLOC))):.1f}")
assert FP_TOTAL == 0 and RATES == 0
if DRY:
    say(f"\n   MODE ESSAI : pas de balayage de l'archive. duree {(time.time() - T0) / 60:.1f} min")
    sys.exit(0)

# ==========================================================================
rule("4. LE BALAYAGE DE L'ARCHIVE")
# ==========================================================================

T_ARCH, TAU2 = statT(NUM)
Z_D = famille_D(T_ARCH)
A_FLUX, _ = autocorr_flux(T_ARCH, NTOT - 1)
A_BLOC, _ = autocorr_bloc(T_ARCH, DEB, LMAX - 1)
CIBLES = [("flux", A_FLUX, ND_FLUX, DMAX_FLUX), ("bloc", A_BLOC, ND_BLOC, DMAX_BLOC)]
say(f"   archive : moyenne de T = {T_ARCH.mean():+.5f} (e-t {math.sqrt(TAU2 / NTOT):.5f}), tau^2 = moy(T^2) = {TAU2:.5f} "
    f"(3/79 = {TAU2_TH:.5f}) ; famille D : z_D = {Z_D:+.2f}" + ("   !! DETECTION" if abs(Z_D) >= ZC else ""))
jr = open(JOURNAL, "w", encoding="utf-8")
jr.write(f"D z_D={Z_D:.3f} tau2={TAU2:.5f} moyT={T_ARCH.mean():.5f} det={int(abs(Z_D) >= ZC)}\n")
LIG, DETEC = [], []
say(f"   {'cible':>5} {'S':>3} {'Dmax':>8} | {'A: zmax':>8} {'D':>8} {'moy':>6} {'e-t':>6} | {'B: zmax':>8} {'P':>8} | {'C: zmax':>8} {'H':>8} | det")
for cible, A, nd, dm in CIBLES:
    for S in PAS:
        t0 = time.time()
        g = grille(A, nd, S, TAU2, dm)
        r = resume(g, ZC)
        det = sum(r[f]["det"] for f in "ABC")
        LIG.append((cible, S, g["Dmax"], r, det))
        if det:
            DETEC.append((cible, S, r))
        jr.write(f"{cible},{S} Dmax={g['Dmax']} " + " ".join(
            f"{f}_zmax={r[f]['zmax']:.3f} {f}_arg={r[f]['arg']} {f}_det={r[f]['det']} {f}_moy={r[f]['moy']:.4f} {f}_et={r[f]['et']:.4f}"
            for f in "ABC") + f" det={det} sec={time.time() - t0:.1f}\n")
        jr.flush()
        say(f"   {cible:>5} {S:>3} {g['Dmax']:>8} | {r['A']['zmax']:>8.2f} {r['A']['arg']:>8} {r['A']['moy']:>6.3f} {r['A']['et']:>6.3f} | "
            f"{r['B']['zmax']:>8.2f} {r['B']['arg']:>8} | {r['C']['zmax']:>8.2f} {r['C']['arg']:>8} | {det}"
            + ("   !! DETECTION" if det else ""))
jr.close()
D_TOT = sum(l[4] for l in LIG) + int(abs(Z_D) >= ZC)
ZM, OU = Z_D, ("archive", "-", "D", 0)
for cible, S, Dmax, r, det in LIG:
    for f in "ABC":
        if abs(r[f]["zmax"]) > abs(ZM):
            ZM, OU = r[f]["zmax"], (cible, S, f, r[f]["arg"])
ETS = [r["A"]["et"] for _, _, _, r, _ in LIG]
say(f"""
   {M_TOTAL} statistiques ; D = {D_TOT} detectee(s) ; max |z| = {ZM:.2f} ({OU}) ; z_D = {Z_D:+.2f} ; ecart-type
   des z de la famille A par grille : {min(ETS):.3f} a {max(ETS):.3f} (1 attendu sous H0) ; Zc = {ZC:.2f}.""")
if D_TOT == 0:
    say(f"""   AUCUNE DETECTION : aucun bit lu de l'archive n'est periodique ni anti-periodique a une periode
   <= {max(l[2] for l in LIG) // 2} positions, sous aucun pas de {PAS[0]} a {PAS[-1]}, ni sous le flux ni par nuit : aucun
   LCG de module 2^W a decalage s <= {int(math.log2(max(l[2] for l in LIG) // 2))} (a, c, W quelconques), aucun registre de periode
   <= Dmax/2, aucune relation de poids 2 entre tirages distincts ni au sein d'un tirage (E T^2 = 3/79).""")

# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

TOK["m_extra"] = 0
verdict = "conforme" if D_TOT == 0 else "DETECTION"
puiss = "; ".join(f"{nom} (pas {S}, {cible}) : z_rel {z_rel:.1f}, z_att {z_att:.1f} en {ou_txt} (observe {z_pt:.1f}), "
                  f"zmax {zmax:.1f} (zA {r['A']['zmax']:.1f}, zB {r['B']['zmax']:.1f}, zC {r['C']['zmax']:.1f}), "
                  f"zD_att {zD_att:.1f}, zD {zD:.1f}, detecte {det} (attendu {attendu}), grilles collaterales {collat}"
                  for nom, S, cible, z_rel, z_att, ou_txt, z_pt, zmax, zD_att, zD, r, attendu, det, collat in TEMOINS)
nuls = "; ".join(f"{nom} : max |z| {zm:.2f}, z_D {zD:.2f}" for nom, zm, ou, zD, fp in NULS_RES)
lab.record(
    TOK, float(D_TOT), p=1.0 if D_TOT == 0 else min(1.0, 1e-7), verdict=verdict,
    power_at=(f"temoins plantes de ce script (meme grille, meme seuil Zc = {ZC:.2f} ; attendu = prediction au premier "
              f"ordre T ≈ C U, marge {MARGE:.0f}) : {puiss} — {RATES} temoin rate, {INDET} indetermine ; flux nuls : {nuls} — "
              f"{FP_TOTAL} faux positif sur {len(NULS)} x {M_TOTAL} statistiques"),
    notes=(f"M = {M_TOTAL} statistiques ({len(PAS)} pas x flux/bloc x familles A, B, C, + D), D = {D_TOT}, max |z| {ZM:.2f} "
           f"({OU}), z_D = {Z_D:.2f}, ecart-type des z (famille A) {min(ETS):.3f} a {max(ETS):.3f} ; tau^2 = {TAU2:.5f}, "
           f"moyenne de T {T_ARCH.mean():.5f} ; Dmax flux {DMAX_FLUX} tirages, bloc {DMAX_BLOC} ; journal {JOURNAL}"))
say("   registre : une ligne ajoutee ; Holm :")
for h in lab.holm(alpha=0.05):
    if h.get("exp_id") == EXP_ID or h.get("id") == EXP_ID:
        say(f"     {h}")
say(f"\n   duree totale {(time.time() - T0) / 60:.1f} min")
