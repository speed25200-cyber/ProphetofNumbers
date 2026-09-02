"""Relèvement par réseau sous le FLUX CONTINU et des tirages ORDONNÉS —
la voie 5 du 7.12 de THEORIE_ETAT, mise en machine.

Cadre. Un LFG additif glibc (K, L), r_i = r_{i-K} + r_{i-L} mod 2^32, lu au
pas S = 20 par un Fisher-Yates partiel par modulo : au mot k du tirage t,
j_k = x_i mod (80 - k), i = S t + k, x = r >> 1. Si les tirages sont ORDONNÉS
(vidéos), j_k est exact (ordered.fy_indices). On coupe r_i = l_i + 2^m h_i :
l = r mod 2^m connu (m = 1 : le seul plan 0, 2^L hypothèses ; m = 7 : le crible
du 7.11), h_i inconnu sur 32 - m bits, et un bit de DÉBORDEMENT c_i par mot
engendré :

    h_i = h_{i-K} + h_{i-L} + kappa_i - 2^(32-m) c_i,   kappa_i = (l_{i-K} + l_{i-L}) >> m

Avec x_i = (l_i >> 1) + 2^(m-1) h_i et 80 - k = 2^e o_k, l'observation devient

    2^(m-1) h_i  ==  j_k - (l_i >> 1)   (mod 80 - k)

soit h_i modulo q_k = (80 - k) / 2^min(m-1, e) : pour m = 1 le module ENTIER
80 - k (122,7 bits par tirage), pour m = 7 la partie impaire o_k (100,7 bits).
Sur Z, h_i = <A_i, H> + <C_i, c> + g_i (H les L mots initiaux hauts, c les
débordements) : chaque observation est une congruence linéaire en (H, c), et
(H, c) est un point ENTIER BORNÉ d'un réseau d'indice prod q_k^T. Centré et mis
à l'échelle (2H - 2^(32-m) z, 2^(33-m) c - 2^(32-m) z, 2^(32-m) z), c'est un
plus-court-vecteur de sa classe z = ±1 par plongement de Kannan ; la réduction
(LLL puis BKZ) le trouve ou non selon l'écart à l'heuristique gaussienne.

Le plan 0 (bit 0 de r) n'apparaît jamais dans x, mais il commande les retenues
du plan 1, qui est le bit 0 de x, observé exactement aux dix mots pairs de
chaque tirage : `plan0_survivants` essaie les 2^L plans 0 et garde ceux dont le
plan 1, affine en ses L bits initiaux, est compatible (10 T équations sur L
inconnues). La chaîne complète, `pipeline`, part des seuls tirages ordonnés :
plan 0 par crible linéaire, bits hauts par le réseau avec m = 1.

Ce module ne touche PAS l'archive : l'archive est triée, pas ordonnée. C'est
un témoin d'outil sur données plantées — il prouve que les équations du 7.12
sont justes et que la voie 5 est un algorithme là où le compte le dit.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ordered import fy_indices  # noqa: E402

POOL, DRAWN, S = 80, 20, 20
N32 = 1 << 32
ODD, E = [], []
for k in range(DRAWN):
    n, e = POOL - k, 0
    while n % 2 == 0:
        n //= 2
        e += 1
    ODD.append(n)
    E.append(e)


def lfg(etat, K, L, n):
    """Les n premiers mots r_0..r_{n-1} (les L premiers sont l'état)."""
    r = list(etat)
    for i in range(L, n):
        r.append((r[i - K] + r[i - L]) % N32)
    return r


def tirage_fy(mots):
    """Fisher-Yates partiel par modulo : vingt mots -> tirage ORDONNÉ."""
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        j = k + (mots[k] >> 1) % (POOL - k)
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return out


# ----------------------------------------------------------------- plan 0
def plan0_survivants(indices, K, L, T):
    """Les plans 0 (L bits initiaux) dont le plan 1 est compatible avec le bit 0
    de x aux mots pairs. Rend la liste des suites l = r mod 2 (n_mots bits)."""
    n_mots = L + S * T
    obs = [(L + S * t + k, indices[t][k] & 1) for t in range(T) for k in range(DRAWN) if E[k] >= 1]
    survivants = []
    for p in range(1 << L):
        p0 = [(p >> j) & 1 for j in range(L)]
        for i in range(L, n_mots):
            p0.append(p0[i - K] ^ p0[i - L])
        # plan 1 : u_i = u_a ^ u_b ^ kappa_i, affine en (u_0..u_{L-1}) : (masque, constante)
        aff = [(1 << j, 0) for j in range(L)]
        for i in range(L, n_mots):
            ma, ca = aff[i - K]
            mb, cb = aff[i - L]
            aff.append((ma ^ mb, ca ^ cb ^ (p0[i - K] & p0[i - L])))
        # élimination de Gauss sur GF(2)
        pivots = {}
        ok = True
        for i, bit in obs:
            m, c = aff[i]
            c ^= bit
            while m:
                h = m.bit_length() - 1
                if h in pivots:
                    pm, pc = pivots[h]
                    m ^= pm
                    c ^= pc
                else:
                    pivots[h] = (m, c)
                    break
            else:
                if c:
                    ok = False
                    break
        if ok:
            survivants.append(p0)
    return survivants


# ----------------------------------------------------------------- réseau
def coefficients(low, K, L, n, m):
    """h_i = <A_i, H> + <C_i, c> + g_i sur Z, pour i < n, à partir de l = r mod 2^m.
    A_i : L entiers ; C_i : dict {mot engendré: coefficient} ; g_i : entier."""
    HB = 32 - m
    A, C, g = [], [], []
    for i in range(n):
        if i < L:
            A.append([1 if j == i else 0 for j in range(L)])
            C.append({})
            g.append(0)
            continue
        a, b = i - K, i - L
        A.append([A[a][j] + A[b][j] for j in range(L)])
        ci = dict(C[a])
        for j, v in C[b].items():
            ci[j] = ci.get(j, 0) + v
        ci[i] = ci.get(i, 0) - (1 << HB)
        C.append(ci)
        g.append(g[a] + g[b] + ((low[a] + low[b]) >> m))
    return A, C, g


def congruences(low, indices, K, L, T, m):
    """Les lignes (coefficients mod q_k sur (H, c), second membre mod q_k, q_k) :
    <M, (H, c)> == rho (mod q) pour chaque mot observé de module q_k > 1."""
    n_mots = L + S * T
    A, C, g = coefficients(low, K, L, n_mots, m)
    gen = list(range(L, n_mots))                       # mots engendrés, dans l'ordre
    pos = {i: L + q for q, i in enumerate(gen)}        # colonne de c_i
    nvar = L + len(gen)
    lignes = []
    for t in range(T):
        for k in range(DRAWN):
            d = min(m - 1, E[k])
            q = (POOL - k) >> d
            if q == 1:
                continue
            i = L + S * t + k
            u = indices[t][k] - (low[i] >> 1)
            assert u % (1 << d) == 0, "plans bas incohérents avec l'indice"
            mult = 1 << (m - 1 - d)                    # inversible modulo q
            b = (pow(mult, -1, q) * (u >> d)) % q
            row = [0] * nvar
            for j in range(L):
                row[j] = A[i][j] % q
            for j, v in C[i].items():
                row[pos[j]] = v % q
            lignes.append((row, (b - g[i]) % q, q))
    return lignes, nvar


def kernel_basis(lignes, nvar, L, m, W=1 << 50):
    """Base du réseau plongé : (H, c, z) entiers avec <M,(H,c)> == rho z (mod q),
    aux coordonnées centrées y = (2H - 2^HB z, 2^(HB+1) c - 2^HB z, 2^HB z) — le
    vecteur planté (z = 1) y a toutes ses coordonnées dans ±2^HB. LLL à poids W
    sur les colonnes de contrainte ; les lignes à contrainte nulle forment la base."""
    from fpylll import IntegerMatrix, LLL
    HB = 32 - m
    R = len(lignes)
    dim = nvar + 1 + R
    B = IntegerMatrix(dim, nvar + 1 + R)
    for j in range(nvar):
        B[j, j] = 2 if j < L else 1 << (HB + 1)
        for r, (row, rho, q) in enumerate(lignes):
            B[j, nvar + 1 + r] = W * row[j]
    for j in range(nvar):
        B[nvar, j] = -(1 << HB)
    B[nvar, nvar] = 1 << HB
    for r, (row, rho, q) in enumerate(lignes):
        B[nvar, nvar + 1 + r] = W * ((-rho) % q)
    for r, (row, rho, q) in enumerate(lignes):
        B[nvar + 1 + r, nvar + 1 + r] = W * q
    LLL.reduction(B)
    base = []
    for i in range(dim):
        row = [B[i, j] for j in range(nvar + 1 + R)]
        if any(row[nvar + 1:]):
            continue
        if any(row[: nvar + 1]):
            base.append(row[: nvar + 1])
    return base


def reduire(base, beta_max=80, temps_max=None, verbose=False):
    """LLL puis BKZ progressif ; rend (matrice réduite, beta atteint)."""
    from fpylll import IntegerMatrix, LLL, BKZ
    from fpylll.algorithms.bkz2 import BKZReduction
    A = IntegerMatrix.from_matrix(base)
    LLL.reduction(A)
    t0 = time.time()
    yield A, 2
    if beta_max < 10:
        return
    bkz = BKZReduction(A)
    strat = os.environ.get("FPLLL_STRATEGIES", BKZ.DEFAULT_STRATEGY)   # default.json de fplll
    if not os.path.exists(strat if isinstance(strat, str) else strat.decode()):
        strat = None                                                     # énumération sans élagage
    for beta in range(10, beta_max + 1, 10):
        par = BKZ.Param(block_size=beta, strategies=strat, max_loops=4,
                        flags=BKZ.MAX_LOOPS | BKZ.AUTO_ABORT | BKZ.GH_BND)
        bkz(par)
        if verbose:
            print(f"      BKZ-{beta}  {time.time() - t0:7.1f} s", flush=True)
        yield A, beta
        if temps_max and time.time() - t0 > temps_max:
            return


def decoder(row, nvar, L, m):
    """Une ligne réduite de coordonnée z = ±2^HB -> les L mots hauts H_j mod 2^HB.

    Le réseau contient des vecteurs courts PARASITES, plus courts que la cible
    (norme 2^(HB+1,5) contre 2^(HB+3,7)) : pour chaque mot initial r_j,
    r_j + 2^32 ne change rien modulo 2^32, et (H_j, c_{j+L}) -> (H_j - 2^HB,
    c_{j+L} - 1) (avec c_{j+K} - 1 aussi si j >= L - K) est une symétrie exacte ;
    de même le débordement du mot 16 du dernier tirage (module impair 1) se
    confond avec celui du mot 19 quand m > 1. Une ligne réduite de coordonnée
    z = ±2^HB est donc la cible à ces parasites près : on ne lit que H mod 2^HB,
    et on vérifie par régénération."""
    HB = 32 - m
    z = row[nvar]
    if abs(z) != 1 << HB:
        return None
    s = 1 if z > 0 else -1
    H = []
    for j in range(L):
        v = s * row[j] + (1 << HB)
        if v % 2:
            return None
        H.append((v // 2) % (1 << HB))
    return H


def coherent(etat, low, indices, K, L, T, m):
    """L'état régénéré rend-il les plans bas ET les indices ordonnés observés ?"""
    r = lfg(etat, K, L, L + S * T)
    if any(r[i] % (1 << m) != low[i] for i in range(L + S * T)):
        return False
    return all((r[L + S * t + k] >> 1) % (POOL - k) == indices[t][k]
               for t in range(T) for k in range(DRAWN))


def relever(low, indices, K, L, T, m=1, beta_max=80, verbose=False, temps_max=None):
    """Relève l'état complet (les L mots r_0..r_{L-1}) ; rend (etat, beta) ou (None, beta)."""
    lignes, nvar = congruences(low, indices, K, L, T, m)
    base = kernel_basis(lignes, nvar, L, m)
    assert len(base) == nvar + 1, (len(base), nvar + 1)
    beta = 2
    for A, beta in reduire(base, beta_max, temps_max, verbose):
        for i in range(A.nrows):
            row = [A[i, j] for j in range(nvar + 1)]
            H = decoder(row, nvar, L, m)
            if H is None:
                continue
            etat = [low[j] + (H[j] << m) for j in range(L)]
            if coherent(etat, low, indices, K, L, T, m):
                return etat, beta
    return None, beta


def pipeline(indices, K, L, T, beta_max=80, verbose=False, temps_max=None):
    """Des seuls tirages ordonnés à l'état : plan 0 par crible, puis réseau (m = 1)."""
    t0 = time.time()
    surv = plan0_survivants(indices, K, L, T)
    if verbose:
        print(f"      plan 0 : {len(surv)} survivant(s) sur 2^{L}  {time.time() - t0:.1f} s", flush=True)
    for low in surv:
        etat, beta = relever(low, indices, K, L, T, 1, beta_max, verbose, temps_max)
        if etat is not None:
            return etat, beta, len(surv)
    return None, None, len(surv)


def _temoin(K, L, T, graine, m, beta_max=80, verbose=True):
    """Plante un état, T tirages ordonnés ; relève (m > 1 : plans bas donnés ;
    m = 1 : chaîne complète) ; vérifie l'état et prédit le tirage T + 1."""
    rng = random.Random(graine)
    etat = [rng.getrandbits(32) for _ in range(L)]
    n_mots = L + S * (T + 1)
    r = lfg(etat, K, L, n_mots)
    tirages = [tirage_fy(r[L + S * t: L + S * t + DRAWN]) for t in range(T + 1)]
    indices = [fy_indices(tir) for tir in tirages[:T]]           # j_k lus dans l'ordre
    t0 = time.time()
    if m == 1:
        trouve, beta, nsurv = pipeline(indices, K, L, T, beta_max, verbose)
        via = f"plan 0 : {nsurv} surv."
    else:
        low = [v % (1 << m) for v in r]
        trouve, beta = relever(low, indices, K, L, T, m, beta_max, verbose)
        via = f"l = r mod 2^{m} donne"
    dt = time.time() - t0
    if trouve is None:
        print(f"   ({K},{L}) T={T} m={m} graine {graine} : ECHEC jusqu'a BKZ-{beta}  {dt:.1f} s  [{via}]")
        return False
    r2 = lfg(trouve, K, L, n_mots)
    pred = tirage_fy(r2[L + S * T: L + S * T + DRAWN])
    ok = trouve == etat and pred == tirages[T]
    print(f"   ({K},{L}) T={T} m={m} graine {graine} : "
          f"{'ETAT EXACT, tirage T+1 predit' if ok else 'FAUX'}  BKZ-{beta}  {dt:.1f} s  [{via}]")
    return ok


if __name__ == "__main__":
    # usage : reseau_ordonne.py K L T [graines] [beta_max] [m]
    K, L = int(sys.argv[1]), int(sys.argv[2])
    T = int(sys.argv[3])
    graines = [int(g) for g in sys.argv[4].split(",")] if len(sys.argv) > 4 else [1]
    beta_max = int(sys.argv[5]) if len(sys.argv) > 5 else 80
    m = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    res = [_temoin(K, L, T, g, m, beta_max) for g in graines]
    print(f"   {sum(res)}/{len(res)} reussites")
