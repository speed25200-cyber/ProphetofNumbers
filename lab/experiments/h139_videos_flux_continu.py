"""h139 — les douze tirages ORDONNÉS des vidéos sous le FLUX CONTINU : le crible
EXACT des plans bas (THEORIE_ETAT §7.12, RAPPORT §159).

CE QUE L'ORDRE CHANGE
=====================
h137 et h138 criblent l'ARCHIVE TRIÉE : le tirage t ne livre que des ensembles,
le bit 0 de x_k n'est lu qu'à travers un masque, et le plan 1 exige une
linéarisation cubique sur ~1 000 monômes. Les vidéos donnent douze tirages
ORDONNÉS (lab/draws_ordered.csv) : le mot k du tirage y est lu EXACTEMENT
modulo 80 − k, donc ses e_k = v2(80 − k) bits bas sont EXACTS —
e = 4, 1, 2, 1, 3, 1, 2, 1, 6, 1 aux mots pairs, 22 bits par tirage, dont 10 au
plan 0 de x, 5 au plan 1, 3 au plan 2, 2 au plan 3, 1 aux plans 4 et 5. Sous
un Fibonacci retardé additif r_i = r_{i−K} + r_{i−L} mod 2^32 lu x = r ≫ shift :

    plan 0 de r : LFSR, linéaire dans ses L bits initiaux p ;
    plan 1 de r : affine dans ses L bits initiaux y, de constante δ_i(p)
                  QUADRATIQUE en p (δ_i = δ_{i−K} ⊕ δ_{i−L} ⊕ p0_{i−K} p0_{i−L}) ;
    plan q ≥ 2 : affine dans ses L bits initiaux, les retenues étant des
                  constantes une fois les plans inférieurs connus (Hensel).

    shift 1 (glibc) : le plan 0 est muet, le plan 1 est le bit 0 de x. Les
    observations du bit 0 sont n équations affines en y ; leur noyau à gauche
    Λ (n − rang vecteurs λ) donne n − rang conditions Q_λ(p) = ⟨λ, obs⟩ qui ne
    portent QUE sur p, chacune une forme quadratique Q_λ = ⊕ λ_i Γ_i. Les 2^L
    plans 0 sont passés au crible par TABLE DE VÉRITÉ : la table d'une forme
    quadratique sur 2^L points se construit en 2^L opérations (doublement : la
    restriction à p_a = 1 est la table à p_a = 0 XOR une forme linéaire), 64
    formes à la fois par tranchage de bits sur uint64, et 2^31 points par
    tranches de 2^22 (le terme croisé haut-bas est linéaire dans les bits bas).
    Un survivant p livre y par Gauss, puis les plans 2, 3, … par Hensel.
    shift 0 : le plan 0 est le bit 0 de x, tout est linéaire plan par plan.

LES CELLULES
============
32 trinômes (les 31 primitifs L ≤ 17 de h137 et (3, 31), TYPE_3 compris pour la
première fois sous le flux continu, la voie étant exacte) × {fy, shuffle} ×
pas S ∈ {20, 21, 22, 23, 24, 79, 80} × shift ∈ {0, 1} × ordre d'affichage
{direct, inverse}. Trois jeux :
    AB : jours A et B, dix tirages, l'état CONTINU à travers 237 identifiants
         (flux continu), le jour C (deux tirages, 44 bits) tenu en RÉSERVE ;
    A, B : cinq tirages chacun, l'état libre en début de jour (réamorçage
         journalier), L ≤ 17 seulement (TYPE_3 n'y est pas décidable).
Une cellule est DÉCISIVE si la marge Σ_p (n_p − L) sur les plans décidables
(n_p > L) vaut au moins 20 bits : 1 792 + 1 736 + 1 736 = 5 264 cellules, moins
de 2^{−20} faux survivant attendu chacune, 0,005 en tout.

TÉMOINS ET TÉMOIN NÉGATIF
=========================
États plantés aux identifiants RÉELS sous sept schémas (TYPE_1, TYPE_2, TYPE_3
compris, fy et shuffle, shifts 0 et 1, ordres direct et inverse) : l'état bas
planté doit être le survivant de sa cellule (puissance mesurée). Le témoin
TYPE_1 est ensuite RELEVÉ complètement par le réseau de lab/reseau_ordonne.py
(m = 7, quatre tirages consécutifs du jour B), l'état complet vérifié, le
satellite +22, le jour A (récurrence inversée) et le jour C rejoués. Témoin
négatif : douze permutations aléatoires, toute la grille, zéro survivant.

Il TESTE les vidéos : il consigne au registre AVANT de lire les tirages réels.
"""

import csv
import json
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402
from ordered import fy_indices                               # noqa: E402
import reseau_ordonne as RO                                   # noqa: E402

T0 = time.time()
DRY = os.environ.get("H139_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
CSV = os.path.join(DEPOT, "lab", "draws_ordered.csv")
JOURNAL = os.environ.get("H139_JOURNAL", "/tmp/h139_journal.json")
EXP_ID = "h139.videos_flux_continu"
GRAINE = 20260902
POOL, DRAWN = 80, 20
M32 = 1 << 32
LOW_MAX = int(os.environ.get("H139_LOW", "22"))              # tranche du crible 2^L
CAP_BRANCHES = 1 << 12                                        # noyaux énumérés au plus
MARGE_MIN = 20                                                # bits : cellule décisive

E = RO.E                                                      # e_k = v2(80 − k)
MOTS_OBS = [k for k in range(DRAWN) if E[k] >= 1]             # dix mots par tirage


def say(*a):
    print(*a, flush=True)


def rule(t):
    say("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


# --------------------------------------------------------------------------
# trinômes (h137) et TYPE_3
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


TRINOMES = [(K, L) for L in range(2, 18) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 31 and (3, 7) in TRINOMES and (1, 15) in TRINOMES
TRINOMES.append((3, 31))
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3"}
MODES = ("fy", "shuffle")
PAS = (20, 21, 22, 23, 24, 79, 80)
SHIFTS = (0, 1)
ORDRES = ("direct", "inverse")
if DRY:
    TRINOMES = [(3, 7), (1, 15), (3, 31)]
    PAS = (20, 80)


# --------------------------------------------------------------------------
# les vidéos
# --------------------------------------------------------------------------
def lire_videos():
    out = []
    with open(CSV) as fh:
        for row in csv.DictReader(fh):
            out.append((int(row["id"]), [int(row[f"o{i}"]) for i in range(1, 21)]))
    return out


VIDEOS = lire_videos()
ID_REF = VIDEOS[0][0]                                          # 1381023
JOUR_A = [v for v in VIDEOS if v[0] <= 1381031]
JOUR_B = [v for v in VIDEOS if 1381256 <= v[0] <= 1381278]
JOUR_C = [v for v in VIDEOS if v[0] >= 1381481]
assert len(JOUR_A) == 5 and len(JOUR_B) == 5 and len(JOUR_C) == 2
JEUX = {"AB": JOUR_A + JOUR_B, "A": JOUR_A, "B": JOUR_B}
NOYAU_B = [1381256, 1381257, 1381258, 1381259]


# --------------------------------------------------------------------------
# indices ordonnés : j_k = x_k mod (80 − k) pour chaque échantillonneur
# --------------------------------------------------------------------------
def indices_shuffle(order):
    """Retrait par échange avec le dernier (Collections.shuffle lu par ses
    vingt dernières cases) : au pas k, la case j reçoit l'ancien dernier."""
    arr = list(range(1, POOL + 1))
    out = []
    for k, v in enumerate(order):
        j = arr.index(v)
        assert j <= POOL - 1 - k
        out.append(j)
        arr[POOL - 1 - k], arr[j] = arr[j], arr[POOL - 1 - k]
    return out


def indices(order, mode):
    return fy_indices(order) if mode == "fy" else indices_shuffle(order)


def tirage(mots, mode, shift):
    """Vingt mots r -> tirage ordonné (ordre de génération) sous le schéma."""
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        x = mots[k] >> shift
        if mode == "fy":
            j = k + x % (POOL - k)
            arr[k], arr[j] = arr[j], arr[k]
            out.append(arr[k])
        else:
            j = x % (POOL - k)
            i = POOL - 1 - k
            arr[i], arr[j] = arr[j], arr[i]
            out.append(arr[i])
    return out


def observations(jeu, mode, shift, ordre, S, L):
    """{plan p: [(mot i, bit)]} — le mot du tirage d, position k, est
    i = L + S (d − id_ref_du_jeu) + k ; bit β de j_k pour β < e_k, plan β + shift."""
    id0 = jeu[0][0]
    obs = {}
    for d, order in jeu:
        seq = order if ordre == "direct" else order[::-1]
        idx = indices(seq, mode)
        for k in MOTS_OBS:
            i = L + S * (d - id0) + k
            for beta in range(E[k]):
                obs.setdefault(beta + shift, []).append((i, (idx[k] >> beta) & 1))
    return obs


def n_mots(jeu, S, L):
    return L + S * (jeu[-1][0] - jeu[0][0]) + DRAWN


# --------------------------------------------------------------------------
# algèbre sur GF(2)
# --------------------------------------------------------------------------
def gauss(eqs, L):
    """eqs : [(masque, bit)] sur L inconnues. Rend (solution, noyau) ou None."""
    piv = {}
    for m, c in eqs:
        while m:
            h = m.bit_length() - 1
            if h in piv:
                pm, pc = piv[h]
                m ^= pm
                c ^= pc
            else:
                piv[h] = (m, c)
                break
        else:
            if c:
                return None
    for h in sorted(piv):
        m, c = piv[h]
        for h2 in piv:
            if h2 > h and (piv[h2][0] >> h) & 1:
                piv[h2] = (piv[h2][0] ^ m, piv[h2][1] ^ c)
    sol = sum(c << h for h, (m, c) in piv.items())
    noyau = []
    for f in range(L):
        if f in piv:
            continue
        v = 1 << f
        for h, (m, c) in piv.items():
            if (m >> f) & 1:
                v |= 1 << h
        noyau.append(v)
    return sol, noyau


def noyau_gauche(masques):
    """Base de {λ : Σ λ_i masque_i = 0} (entiers sur n bits)."""
    n = len(masques)
    piv = {}
    base = []
    for i, m in enumerate(masques):
        tag = 1 << i
        while m:
            h = m.bit_length() - 1
            if h in piv:
                pm, pt = piv[h]
                m ^= pm
                tag ^= pt
            else:
                piv[h] = (m, tag)
                break
        else:
            base.append(tag)
    return base


def parite(x):
    return bin(x).count("1") & 1


def masques_lfsr(K, L, n):
    """α_i : le plan (quel qu'il soit) au mot i est ⟨α_i, bits initiaux⟩ ⊕ cte."""
    a = [1 << i for i in range(L)]
    for i in range(L, n):
        a.append(a[i - K] ^ a[i - L])
    return a


def formes_retenue(alpha, K, L, n):
    """Γ_i : δ_i(p) = ⊕_a Γ_i[a][a] p_a ⊕ ⊕_{a<b} Γ_i[a][b] p_a p_b, la constante du
    plan 1 en fonction du plan 0 initial p. Tableau (n, L) uint64, ligne a = bits b ≥ a."""
    G = np.zeros((n, L), dtype=np.uint64)
    ar = np.arange(L, dtype=np.uint64)
    haut = np.array([~((1 << (a + 1)) - 1) & ((1 << L) - 1) for a in range(L)], dtype=np.uint64)
    for i in range(L, n):
        u, v = np.uint64(alpha[i - K]), np.uint64(alpha[i - L])
        ub = (u >> ar) & np.uint64(1)
        vb = (v >> ar) & np.uint64(1)
        prod = (np.where(ub == 1, v, np.uint64(0)) ^ np.where(vb == 1, u, np.uint64(0))) & haut
        prod |= (ub & vb) << ar
        G[i] = G[i - K] ^ G[i - L] ^ prod
    return G


def evalue_forme(rows, p):
    """rows : L entiers (ligne a = bits b ≥ a) ; valeur de la forme en p."""
    v = 0
    for a in range(len(rows)):
        if (p >> a) & 1:
            v ^= parite(int(rows[a]) & p)
    return v


# --------------------------------------------------------------------------
# le crible du plan 0 par tables de vérité (shift 1)
# --------------------------------------------------------------------------
def table_lineaire(coefs, nbits):
    """Table sur 2^nbits points de la forme linéaire ⊕ coefs[a] p_a (uint64)."""
    t = np.zeros(1 << nbits, dtype=np.uint64)
    for a in range(nbits):
        t[1 << a: 2 << a] = t[: 1 << a] ^ coefs[a]
    return t


def crible_plan0(L, LIN, G, cibles, low_max=LOW_MAX):
    """LIN[a], G[a][b] (a < b) : formes quadratiques tranchées sur uint64 (bit j =
    forme j). Rend, pour chaque cible j, les p ∈ [0, 2^L) tels que Q(p) = cibles[j]."""
    low = min(L, low_max)
    nlo = 1 << low
    T = np.zeros(nlo, dtype=np.uint64)
    for a in range(low):
        la = table_lineaire([G[b][a] for b in range(a)], a)
        T[1 << a: 2 << a] = T[: 1 << a] ^ LIN[a] ^ la
    survivants = {j: [] for j in range(len(cibles))}
    cibles64 = [np.uint64(c) for c in cibles]
    for h in range(1 << (L - low)):
        hb = [b for b in range(low, L) if (h >> (b - low)) & 1]
        if hb:
            qh = 0
            for b in hb:
                qh ^= int(LIN[b])
            for x, a in enumerate(hb):
                for b in hb[x + 1:]:
                    qh ^= int(G[a][b])
            M = [np.uint64(0)] * low
            for a in range(low):
                m = 0
                for b in hb:
                    m ^= int(G[a][b])
                M[a] = np.uint64(m)
            tab = T ^ table_lineaire(M, low) ^ np.uint64(qh)
        else:
            tab = T
        for j, c in enumerate(cibles64):
            for p in np.flatnonzero(tab == c):
                survivants[j].append((h << low) | int(p))
    return survivants


# --------------------------------------------------------------------------
# Hensel : plan q affine dans ses L bits initiaux, plans inférieurs connus
# --------------------------------------------------------------------------
def suite_basse(bas, K, L, n, q):
    """r_i mod 2^q pour i < n, depuis les L mots initiaux bas (mod 2^q)."""
    mod = (1 << q) - 1
    r = list(bas) + [0] * (n - L)
    for i in range(L, n):
        r[i] = (r[i - K] + r[i - L]) & mod
    return r


def hensel(bas, q, obs_q, alpha, K, L, n):
    """bas : L mots mod 2^q. Rend la liste des bas mod 2^(q+1) cohérents avec obs_q
    (le plan q observé), ou None si le noyau dépasse CAP_BRANCHES."""
    r = suite_basse(bas, K, L, n, q)
    eps = [0] * n
    for i in range(L, n):
        eps[i] = eps[i - K] ^ eps[i - L] ^ (((r[i - K] + r[i - L]) >> q) & 1)
    res = gauss([(alpha[i], b ^ eps[i]) for i, b in obs_q], L)
    if res is None:
        return []
    sol, noyau = res
    if len(noyau) > 12:
        return None
    out = []
    for c in range(1 << len(noyau)):
        w = sol
        for t, v in enumerate(noyau):
            if (c >> t) & 1:
                w ^= v
        out.append([bas[j] | (((w >> j) & 1) << q) for j in range(L)])
    return out


# --------------------------------------------------------------------------
# une cellule : (K, L, mode, S, shift, ordre) sur un jeu
# --------------------------------------------------------------------------
class Prepare:
    """Ce qui ne dépend que de (K, L, S) et du jeu : masques, formes de retenue,
    noyau à gauche du plan 1 (shift 1)."""

    def __init__(self, K, L, S, jeu):
        self.K, self.L, self.S = K, L, S
        self.n = n_mots(jeu, S, L)
        self.alpha = masques_lfsr(K, L, self.n)
        # positions observées au plan « bit 0 de x » (les mêmes pour tous les schémas)
        id0 = jeu[0][0]
        self.pos1 = [L + S * (d - id0) + k for d, _ in jeu for k in MOTS_OBS]
        self.lam = noyau_gauche([self.alpha[i] for i in self.pos1])
        self.G = None
        self.LIN = self.GG = None

    def formes(self):
        if self.G is None:
            self.G = formes_retenue(self.alpha, self.K, self.L, self.n)
            NF = min(64, len(self.lam))
            Gobs = self.G[self.pos1]                              # (n_obs, L)
            Q = np.zeros((NF, self.L), dtype=np.uint64)
            for j in range(NF):
                sel = [t for t in range(len(self.pos1)) if (self.lam[j] >> t) & 1]
                Q[j] = np.bitwise_xor.reduce(Gobs[sel], axis=0)
            L = self.L
            arj = np.arange(NF, dtype=np.uint64)
            self.LIN = [np.uint64(int(np.bitwise_or.reduce(((Q[:, a] >> np.uint64(a)) & np.uint64(1)) << arj)))
                        for a in range(L)]
            self.GG = [[np.uint64(int(np.bitwise_or.reduce(((Q[:, a] >> np.uint64(b)) & np.uint64(1)) << arj)))
                        if b > a else np.uint64(0) for b in range(L)] for a in range(L)]
            self.NF = NF
        return self.LIN, self.GG

    def cible(self, obs1):
        """obs1 : [(i, bit)] alignés sur pos1 -> uint64 des ⟨λ_j, obs⟩."""
        assert [i for i, _ in obs1] == self.pos1
        vec = 0
        for t, (_, b) in enumerate(obs1):
            vec |= b << t
        return sum(parite(self.lam[j] & vec) << j for j in range(self.NF))


def marge(jeu, L, shift):
    """Plans décidables (n_p > L) et marge en bits ; le plan 0 muet du shift 1
    coûte L bits."""
    T = len(jeu)
    npl = [10 * T, 5 * T, 3 * T, 2 * T, T, T]                  # par plan de x
    plans, m = [], (-L if shift == 1 else 0)
    for beta, n in enumerate(npl):
        if n > L:
            plans.append(beta + shift)
            m += n - L
        else:
            break
    return plans, m


def cellule(prep, jeu, mode, shift, ordre, survivants_p=None):
    """Rend (liste des états bas survivants [L mots mod 2^(P+1)], P, n_sieve).
    P = dernier plan décidé ; None en cas de noyau trop grand (sous-déterminé)."""
    K, L, S, alpha, n = prep.K, prep.L, prep.S, prep.alpha, prep.n
    obs = observations(jeu, mode, shift, ordre, S, L)
    plans, _ = marge(jeu, L, shift)
    if shift == 0:
        res = gauss([(alpha[i], b) for i, b in obs[0]], L)
        if res is None:
            return [], 0, 0
        sol, noyau = res
        if len(noyau) > 12:
            return None, 0, 0
        etats = []
        for c in range(1 << len(noyau)):
            p = sol
            for t, v in enumerate(noyau):
                if (c >> t) & 1:
                    p ^= v
            etats.append([(p >> j) & 1 for j in range(L)])
        n_sieve = len(etats)
        q0 = 1
    else:
        LIN, GG = prep.formes()
        if survivants_p is None:
            survivants_p = crible_plan0(L, LIN, GG, [prep.cible(obs[1])])[0]
        n_sieve = len(survivants_p)
        etats = []
        Gobs = prep.G[prep.pos1]
        for p in survivants_p:
            eqs = [(alpha[i], b ^ evalue_forme(Gobs[t], p)) for t, (i, b) in enumerate(obs[1])]
            res = gauss(eqs, L)
            if res is None:
                continue
            sol, noyau = res
            if len(noyau) > 12:
                return None, 1, n_sieve
            for c in range(1 << len(noyau)):
                y = sol
                for t, v in enumerate(noyau):
                    if (c >> t) & 1:
                        y ^= v
                etats.append([((p >> j) & 1) | (((y >> j) & 1) << 1) for j in range(L)])
        q0 = 2
    P = q0 - 1
    for q in range(q0, max(plans) + 1):
        if q not in obs:
            break
        suiv = []
        for bas in etats:
            r = hensel(bas, q, obs[q], alpha, K, L, n)
            if r is None:
                return None, P, n_sieve
            suiv.extend(r)
            if len(suiv) > CAP_BRANCHES:
                return None, P, n_sieve
        etats = suiv
        P = q
        if not etats:
            break
    return etats, P, n_sieve


def verifie_reserve(bas, P, K, L, S, mode, shift, ordre, jeu, reserve):
    """L'état bas (mod 2^(P+1)) au mot 0 du jeu, prolongé, rend-il les bits bas
    des tirages de réserve ? Rend (bits justes, bits testés)."""
    id0 = jeu[0][0]
    n = L + S * (reserve[-1][0] - id0) + DRAWN
    r = suite_basse(bas, K, L, n, P + 1)
    ok = tot = 0
    for d, order in reserve:
        seq = order if ordre == "direct" else order[::-1]
        idx = indices(seq, mode)
        for k in MOTS_OBS:
            i = L + S * (d - id0) + k
            for beta in range(E[k]):
                if beta + shift <= P:
                    tot += 1
                    ok += ((r[i] >> (beta + shift)) & 1) == ((idx[k] >> beta) & 1)
    return ok, tot


# --------------------------------------------------------------------------
# la grille
# --------------------------------------------------------------------------
def grille(jeux, videos_par_jeu, trinomes=TRINOMES, seulement=None, verbose=False):
    """Passe toutes les cellules décisives ; rend {(jeu, K, L, mode, S, shift, ordre):
    (nsurv, P, n_sieve, [états], sec)}. `seulement` : sous-ensemble de cellules."""
    res = {}
    for nom in jeux:
        jeu = videos_par_jeu[nom]
        for S in PAS:
            for K, L in trinomes:
                if nom != "AB" and L > 17:
                    continue
                cells = [(mode, shift, ordre) for mode in MODES for shift in SHIFTS for ordre in ORDRES
                         if seulement is None or (nom, K, L, mode, S, shift, ordre) in seulement]
                if not cells:
                    continue
                prep = Prepare(K, L, S, jeu)
                # shift 1 : un seul crible pour les quatre cibles (mode, ordre)
                cibles1 = [(mode, ordre) for mode, shift, ordre in cells if shift == 1]
                surv1 = {}
                if cibles1:
                    LIN, GG = prep.formes()
                    obs1 = [observations(jeu, mode, 1, ordre, S, L)[1] for mode, ordre in cibles1]
                    sv = crible_plan0(L, LIN, GG, [prep.cible(o) for o in obs1])
                    surv1 = {c: sv[j] for j, c in enumerate(cibles1)}
                for mode, shift, ordre in cells:
                    t0 = time.time()
                    etats, P, n_sieve = cellule(prep, jeu, mode, shift, ordre,
                                                surv1.get((mode, ordre)) if shift == 1 else None)
                    dt = time.time() - t0
                    ns = None if etats is None else len(etats)
                    res[(nom, K, L, mode, S, shift, ordre)] = (ns, P, n_sieve, etats or [], dt)
                    if verbose or (ns is None or ns > 0):
                        say(f"      {nom:>2} ({K:>2},{L:>2}) {mode:>7} S={S:>2} shift={shift} {ordre:>7} : "
                            f"{'SOUS-DETERMINE' if ns is None else f'{ns} survivant(s)'} "
                            f"jusqu'au plan {P}, crible {n_sieve}  {dt:.1f} s")
    return res


def resume(res, jeux):
    say(f"\n       {'jeu':>3} {'cellules':>8} {'decisives':>9} {'survivantes':>11} {'sous-det.':>9} {'sec':>7}")
    tot_dec = tot_surv = 0
    for nom in jeux:
        cl = [(k, v) for k, v in res.items() if k[0] == nom]
        dec = [(k, v) for k, v in cl if marge(JEUX[nom], k[2], k[5])[1] >= MARGE_MIN]
        surv = sum(1 for k, v in dec if v[0])
        sous = sum(1 for k, v in dec if v[0] is None)
        sec = sum(v[4] for k, v in cl)
        tot_dec += len(dec)
        tot_surv += surv
        say(f"       {nom:>3} {len(cl):>8} {len(dec):>9} {surv:>11} {sous:>9} {sec:>7.0f}")
    return tot_dec, tot_surv


# --------------------------------------------------------------------------
# témoins plantés aux identifiants réels
# --------------------------------------------------------------------------
def planter(K, L, mode, S, shift, ordre, ids, rng):
    """État aléatoire ; tirages ordonnés (affichés selon `ordre`) aux identifiants."""
    etat = [rng.getrandbits(32) for _ in range(L)]
    n = L + S * (ids[-1] - ids[0]) + DRAWN
    r = RO.lfg(etat, K, L, n)
    videos = []
    for d in ids:
        i = L + S * (d - ids[0])
        gen = tirage(r[i: i + DRAWN], mode, shift)
        videos.append((d, gen if ordre == "direct" else gen[::-1]))
    return etat, r, videos


TEMOINS = [
    (3, 7, "fy", 20, 1, "direct"),
    (3, 7, "fy", 20, 0, "inverse"),
    (1, 15, "fy", 21, 1, "direct"),
    (4, 9, "shuffle", 79, 1, "inverse"),
    (3, 17, "shuffle", 24, 0, "direct"),
    (3, 31, "fy", 20, 1, "direct"),
    (3, 31, "shuffle", 80, 1, "inverse"),
]
if DRY:
    TEMOINS = [TEMOINS[0], TEMOINS[1], TEMOINS[5]]


def temoin(K, L, mode, S, shift, ordre, rng):
    """Plante aux 12 identifiants réels ; crible AB (et A, B si L ≤ 17) sur la
    cellule plantée ; l'état bas planté doit être parmi les survivants ; la
    réserve C doit être rendue. Rend (ok, dict des résultats)."""
    ids = [d for d, _ in VIDEOS]
    etat, r, vid = planter(K, L, mode, S, shift, ordre, ids, rng)
    jeux = {"AB": vid[:10], "A": vid[:5], "B": vid[5:10]}
    out = {}
    ok_tot = True
    for nom in (["AB", "A", "B"] if L <= 17 else ["AB"]):
        jeu = jeux[nom]
        if marge(jeu, L, shift)[1] < MARGE_MIN:
            continue
        t0 = time.time()
        prep = Prepare(K, L, S, jeu)
        etats, P, n_sieve = cellule(prep, jeu, mode, shift, ordre)
        dt = time.time() - t0
        # l'état bas planté AU MOT 0 DU JEU : les L mots qui précèdent le premier tirage
        i0 = L + S * (jeu[0][0] - ids[0]) - L
        vrai = [r[i0 + j] & ((1 << (P + 1)) - 1) for j in range(L)]
        trouve = etats is not None and vrai in etats
        ns = None if etats is None else len(etats)
        res_c = ""
        if nom == "AB" and trouve:
            okb, totb = verifie_reserve(vrai, P, K, L, S, mode, shift, ordre, jeu, vid[10:])
            res_c = f", reserve C {okb}/{totb}"
            trouve = trouve and okb == totb
        ok_tot &= trouve
        out[nom] = (ns, P, n_sieve, trouve, dt)
        say(f"      {NOMS.get((K, L), '')!s:>6} ({K},{L}) {mode} S={S} shift={shift} {ordre} jeu {nom} : "
            f"{ns} survivant(s) jusqu'au plan {P} (crible {n_sieve}), "
            f"{'ETAT BAS PLANTE RETROUVE' if trouve else 'ECHEC'}{res_c}  {dt:.1f} s")
    return ok_tot, out, (etat, r, vid)


def releve_type1(bas_ref, K, L, S, jeu, vid_all, vrai_etat=None, verbose=True):
    """Relève l'état complet de TYPE_1 (fy, S = 20, shift 1, direct) par le réseau
    de lab/reseau_ordonne.py sur les quatre tirages consécutifs du jour B (m = 7),
    puis rejoue le satellite +22, le jour A (récurrence inversée) et le jour C.
    bas_ref : l'état bas (mod 2^7) au mot 0 du jeu AB."""
    assert (K, L, S) == (3, 7, 20)
    id0 = jeu[0][0]
    par_id = dict(vid_all)
    nB = 4
    i_fen = L + S * (NOYAU_B[0] - id0) - L                       # premier mot de la fenêtre
    n_tot = L + S * (max(par_id) - id0) + DRAWN
    r7 = suite_basse(bas_ref, K, L, n_tot, 7)
    low = r7[i_fen: i_fen + L + S * nB]
    idx = [fy_indices(par_id[d]) for d in NOYAU_B]
    t0 = time.time()
    etat, beta = RO.relever(low, idx, K, L, nB, m=7, beta_max=40, verbose=verbose)
    dt = time.time() - t0
    if etat is None:
        say(f"      relèvement TYPE_1 : ECHEC jusqu'à BKZ-{beta}  {dt:.1f} s")
        return False
    # état complet de la fenêtre -> tout le flux, en avant et en arrière
    r = [0] * n_tot
    r[i_fen: i_fen + L] = etat
    for i in range(i_fen + L, n_tot):
        r[i] = (r[i - K] + r[i - L]) % M32
    for i in range(i_fen - 1, -1, -1):                           # r_{i} = r_{i+L} − r_{i+L−K}
        r[i] = (r[i + L] - r[i + L - K]) % M32
    ok = True
    for d in sorted(par_id):
        i = L + S * (d - id0)
        pred = tirage(r[i: i + DRAWN], "fy", 1)
        bon = pred == par_id[d]
        ok &= bon
        say(f"         {d} ({'jour B noyau' if d in NOYAU_B else 'rejoué'}) : "
            f"{'tirage rendu' if bon else 'FAUX'}")
    if vrai_etat is not None:
        exact = r[i_fen: i_fen + L] == vrai_etat
        say(f"      état complet {'EXACT' if exact else 'FAUX'} (BKZ-{beta}, {dt:.1f} s)")
        ok &= exact
    else:
        say(f"      relèvement : BKZ-{beta}, {dt:.1f} s ; tirages suivants (fy, pas 20, shift 1) :")
        for d in range(max(par_id) + 1, max(par_id) + 4):
            i = L + S * (d - id0)
            rr = RO.lfg(r[i_fen: i_fen + L], K, L, i - i_fen + DRAWN)
            say(f"         {d} : {tirage(rr[i - i_fen: i - i_fen + DRAWN], 'fy', 1)}")
    return ok


# ==========================================================================
rule("1. LES DOUZE TIRAGES ORDONNÉS, LES CELLULES, LES MARGES")
# ==========================================================================
say(f"   {len(VIDEOS)} tirages ordonnés, identifiants {VIDEOS[0][0]}..{VIDEOS[-1][0]} ; "
    f"jour A {[d for d, _ in JOUR_A]}, jour B {[d for d, _ in JOUR_B]}, jour C {[d for d, _ in JOUR_C]}")
say(f"   bits exacts par tirage : e_k = {[E[k] for k in MOTS_OBS]} aux mots {MOTS_OBS} = {sum(E)} bits")
say(f"   {len(TRINOMES)} trinômes × {len(MODES)} modes × pas {PAS} × shifts {SHIFTS} × ordres {ORDRES}")
say(f"\n       {'jeu':>3} {'T':>2} {'L':>2} {'shift':>5} {'plans décidés':>14} {'marge (bits)':>12}")
for nom, jeu in JEUX.items():
    for L in (2, 7, 15, 17, 31):
        if nom != "AB" and L > 17:
            continue
        for shift in SHIFTS:
            plans, m = marge(jeu, L, shift)
            say(f"       {nom:>3} {len(jeu):>2} {L:>2} {shift:>5} {str(plans):>14} {m:>12}")
n_cells = {nom: sum(1 for S in PAS for K, L in TRINOMES if nom == "AB" or L <= 17) * len(MODES) * len(SHIFTS) * len(ORDRES)
           for nom in JEUX}
say(f"\n   cellules : {n_cells} = {sum(n_cells.values())} ; "
    f"faux survivants attendus < {sum(n_cells.values())} × 2^-{MARGE_MIN} = {sum(n_cells.values()) / 2 ** MARGE_MIN:.4f}")

# ==========================================================================
rule("2. AUTOTESTS DU CRIBLE (données plantées, aucune lecture des vidéos)")
# ==========================================================================
rng = random.Random(GRAINE)
# 2a. la table de vérité par tranches = la table directe (L = 15, tranche 2^8)
K, L, S = 1, 15, 20
etat, r, vid = planter(K, L, "fy", S, 1, "direct", [d for d, _ in VIDEOS], rng)
prep = Prepare(K, L, S, vid[:10])
LIN, GG = prep.formes()
cib = [prep.cible(observations(vid[:10], "fy", 1, "direct", S, L)[1]),
       prep.cible(observations(vid[:10], "shuffle", 1, "inverse", S, L)[1])]
t0 = time.time()
s_direct = crible_plan0(L, LIN, GG, cib, low_max=22)
s_tranche = crible_plan0(L, LIN, GG, cib, low_max=8)
assert s_direct == s_tranche, "tables directe et par tranches différentes"
p_vrai = sum(((etat[j] & 1) << j) for j in range(L))                   # plan 0 de l'état planté
assert p_vrai in s_direct[0], "le plan 0 planté n'est pas survivant"
say(f"   2a. TYPE_2 fy S=20 shift 1 : crible direct = crible par tranches de 2^8 "
    f"({len(s_direct[0])} et {len(s_direct[1])} survivants pour les deux cibles ; "
    f"le plan 0 planté survit ; {len(prep.lam)} vecteurs du noyau, {prep.NF} formes)  {time.time() - t0:.1f} s")
# 2b. la forme quadratique = la simulation (δ_i à des p aléatoires)
G = prep.G
for _ in range(20):
    p = rng.getrandbits(L)
    p0 = [(p >> j) & 1 for j in range(L)]
    d = [0] * L
    for i in range(L, prep.n):
        p0.append(p0[i - K] ^ p0[i - L])
        d.append(d[i - K] ^ d[i - L] ^ (p0[i - K] & p0[i - L]))
    for i in rng.sample(range(L, prep.n), 30):
        assert evalue_forme(G[i], p) == d[i]
say("   2b. Γ_i(p) = δ_i(p) simulée sur 20 plans 0 × 30 mots : conforme")
# 2c. les sept témoins
say("\n   2c. témoins plantés aux identifiants réels (l'état bas planté doit survivre ;\n"
    "       AB : la réserve C doit être rendue) :")
POW = {}
temoins_ok = True
temoin_t1 = None
for (K, L, mode, S, shift, ordre) in TEMOINS:
    ok, out, plante = temoin(K, L, mode, S, shift, ordre, rng)
    temoins_ok &= ok
    POW[(K, L, mode, S, shift, ordre)] = out
    if (K, L, mode, S, shift, ordre) == (3, 7, "fy", 20, 1, "direct"):
        temoin_t1 = plante
# 2d. le relèvement TYPE_1 par le réseau, sur le témoin planté
say("\n   2d. relèvement complet du témoin TYPE_1 (réseau m = 7, quatre tirages du jour B) :")
etat, r, vid = temoin_t1
bas_ref = [v & 127 for v in etat]
i_fen = 7 + 20 * (NOYAU_B[0] - vid[0][0]) - 7
releve_ok = releve_type1(bas_ref, 3, 7, 20, vid[:10], vid, vrai_etat=r[i_fen: i_fen + 7])
temoins_ok &= releve_ok
# 2e. témoin négatif : douze permutations aléatoires, toute la grille
say("\n   2e. témoin négatif : douze permutations aléatoires aux mêmes identifiants, toute la grille")
faux = [(d, rng.sample(range(1, POOL + 1), DRAWN)) for d, _ in VIDEOS]
jeux_faux = {"AB": faux[:10], "A": faux[:5], "B": faux[5:10]}
t0 = time.time()
res_faux = grille(["AB", "A", "B"], jeux_faux)
dec_faux, surv_faux = resume(res_faux, ["AB", "A", "B"])
say(f"   témoin négatif : {surv_faux} cellule(s) décisive(s) survivante(s) sur {dec_faux}  {time.time() - t0:.0f} s")
say(f"\n   autotests : {'CONFORMES' if temoins_ok and surv_faux == 0 else 'ECHEC'}  ({time.time() - T0:.0f} s)")
if not (temoins_ok and surv_faux == 0):
    say("   ARRET : crible non conforme, rien n'est consigné.")
    sys.exit(1)
if os.environ.get("H139_AUTOTEST") == "1":
    say("   H139_AUTOTEST=1 : arrêt après les autotests, rien n'est consigné et les vidéos ne sont pas criblées.")
    sys.exit(0)

# ==========================================================================
rule("3. PRÉ-ENREGISTREMENT")
# ==========================================================================
HYP = ("Les douze tirages ORDONNES des videos (identifiants 1381023..1381483) sont produits par un "
       "Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 — les 31 trinomes primitifs L <= 17 "
       "ou (3, 31) — lu x = r >> shift (shift 0 ou 1) en FLUX CONTINU a pas constant S dans "
       "{20, 21, 22, 23, 24, 79, 80} par Fisher-Yates partiel par modulo (fy) ou par retrait par echange "
       "avec le dernier (shuffle), l'ordre affiche etant l'ordre de generation ou son inverse ; "
       "soit avec continuite de l'etat a travers les 237 identifiants des jours A et B (jeu AB, "
       "32 trinomes), soit avec un etat libre en debut de jour (jeux A et B, 31 trinomes L <= 17). "
       "Alors la cellule vraie a un etat bas survivant du crible exact des plans bas.")
STAT = ("Nombre de cellules DECISIVES (marge >= 20 bits : 1792 AB + 1736 A + 1736 B) ayant au moins un "
        "etat bas survivant a tous les plans decidables (n_p > L) ; pour AB, un survivant doit aussi rendre "
        "les bits bas du jour C tenu en reserve.")
NUL = ("Analytique : chaque cellule fausse survit avec probabilite <= 2^-marge <= 2^-20 (chaque condition "
       "de coherence est un bit), soit < 0,005 cellule survivante attendue sur les 5264 ; temoin negatif : "
       "douze permutations aleatoires sur toute la grille (0 attendu) ; puissance : sept etats plantes aux "
       "identifiants reels sous sept schemas (TYPE_1, TYPE_2, TYPE_3 compris), le temoin TYPE_1 releve "
       "completement par le reseau (lab/reseau_ordonne.py, m = 7) et ses satellites rejoues.")
DEC = ("0 cellule survivante : ces 32 x 56 echantillonneurs a flux continu (AB) et les 31 x 56 a "
       "reamorcage journalier (A, B) sont EXCLUS pour les tirages des videos, la puissance etant mesuree "
       "par les temoins ; >= 1 : l'etat bas est identifie, le jour C rendu, et le relevement complet "
       "(reseau) puis la prediction des tirages suivants sont tentes et rapportes.")
tok = lab.preregister(EXP_ID, HYP, STAT, NUL, DEC, track="B")
say(f"   jeton scellé : {tok['seal']}  ({tok['registered_at']})")
with open(JOURNAL.replace(".json", "_jeton.json"), "w") as fh:
    json.dump(tok, fh, ensure_ascii=False, indent=1)

# ==========================================================================
rule("4. LES VIDÉOS : toute la grille")
# ==========================================================================
t0 = time.time()
res = grille(["AB", "A", "B"], JEUX)
dec_reel, surv_reel = resume(res, ["AB", "A", "B"])
say(f"   {surv_reel} cellule(s) décisive(s) survivante(s) sur {dec_reel}  {time.time() - t0:.0f} s")
survivants = {k: v for k, v in res.items() if v[0]}
sous = {k: v for k, v in res.items() if v[0] is None}
if sous:
    say(f"   cellules sous-déterminées (noyau > 2^12, hors décision) : {len(sous)}")
    for k in list(sous)[:20]:
        say(f"      {k}")
details = []
for k, (ns, P, n_sieve, etats, dt) in survivants.items():
    nom, K, L, mode, S, shift, ordre = k
    say(f"\n   SURVIVANT {k} : {ns} état(s) bas jusqu'au plan {P}")
    for bas in etats[:4]:
        say(f"      état bas (mod 2^{P + 1}) : {bas}")
        if nom == "AB":
            okc, totc = verifie_reserve(bas, P, K, L, S, mode, shift, ordre, JEUX["AB"], JOUR_C)
            say(f"      réserve C : {okc}/{totc} bits bas rendus")
            details.append((k, bas, okc, totc))
            if (K, L, mode, S, shift, ordre) == (3, 7, "fy", 20, 1, "direct") and okc == totc:
                say("      relèvement complet par le réseau :")
                releve_type1([b & 127 for b in bas], K, L, S, JEUX["AB"], VIDEOS)
stat = sum(1 for k, v in res.items() if v[0] and marge(JEUX[k[0]], k[2], k[5])[1] >= MARGE_MIN
           and (k[0] != "AB" or any(kk == k and okc == totc for kk, _, okc, totc in details)))

# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================
pw = "; ".join(f"({K},{L},{mode},S={S},shift={shift},{ordre}) "
               + ",".join(f"{nom}:{'ok' if v[3] else 'ECHEC'}" for nom, v in out.items())
               for (K, L, mode, S, shift, ordre), out in POW.items())
n_tot = sum(n_cells.values())
p_val = min(1.0, n_tot / 2 ** MARGE_MIN) if stat >= 1 else 1.0
verdict = ("IDENTIFIE : etat bas survivant" if stat >= 1 else
           "conforme au hasard : 0 cellule survivante, les 32 x 56 flux continus (AB) et 31 x 56 "
           "reamorcages journaliers (A, B) sont exclus pour les videos")
notes = (f"cellules decisives {dec_reel} ({n_cells}) ; survivantes {surv_reel} (stat {stat}) ; "
         f"sous-determinees {len(sous)} ; temoin negatif {surv_faux}/{dec_faux} ; "
         f"temoins : {pw} ; relevement TYPE_1 {'ok' if releve_ok else 'ECHEC'} ; "
         f"tranche 2^{LOW_MAX} ; {time.time() - T0:.0f} s")
lab.record(tok, observed=float(stat), p=p_val,
           power_at="7 etats plantes aux identifiants reels (TYPE_1, TYPE_2, TYPE_3, fy/shuffle, "
                    "shifts 0/1, ordres direct/inverse) : etat bas retrouve dans chaque cellule "
                    + ("(tous)" if temoins_ok else "(ECHECS, voir notes)")
                    + " ; temoin TYPE_1 releve completement par le reseau et satellites rejoues",
           verdict=verdict, notes=notes)
with open(JOURNAL, "w") as fh:
    json.dump({"cells": {" ".join(map(str, k)): [v[0], v[1], v[2], v[4]] for k, v in res.items()},
               "survivants": {" ".join(map(str, k)): v[3] for k, v in survivants.items()},
               "temoins": {" ".join(map(str, k)): {n: list(v) for n, v in out.items()} for k, out in POW.items()},
               "temoin_negatif": [surv_faux, dec_faux], "stat": stat, "seal": tok["seal"]}, fh)
say(f"   consigné : {EXP_ID}  observed = {stat}  verdict : {verdict}")
say(f"   m du registre : {len(lab.ledger())}  ({time.time() - T0:.0f} s)")
