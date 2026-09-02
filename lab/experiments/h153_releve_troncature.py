"""h153 — le relevement de la lecture par TRONCATURE : des classes a l'etat complet, puis
au tirage suivant (THEORIE_ETAT §7.24 (vii) ; RAPPORT §173).

CE QUE LE §172 LAISSE OUVERT
===========================
Le crible de classes rend un L-uplet de classes — six virgule trois deux bits par mot — et
laisse les 25,68 bits bas de chaque mot. Le §7.24 (vii) affirme que les `delta` du
quasi-morphisme les rendent par un reseau. Ce fichier le MESURE au lieu de l'affirmer.

L'EQUATION
==========
Ecrivons `r_i = M_i + s_i` ou `M_i = ceil(c_i * 2^32 / 80)` est le bas de la classe (connu)
et `s_i` dans `[0, W)` avec `W = 2^32/80` (inconnu, 25,68 bits). La recurrence
`r_i = r_{i-K} + r_{i-L} - 2^32 e_i` donne

    s_i = s_{i-K} + s_{i-L} + D_i,   D_i = M_{i-K} + M_{i-L} - M_i - 2^32 e_i,

et `e_i` dans {0, 1} est DETERMINE : une seule des deux valeurs met `D_i` dans
`(-2W, W)`. Les `s_i` sont donc des formes affines ENTIERES des `L` premieres :
`s_i = sum_m a_{i,m} s_m + beta_i`, avec `a_i = a_{i-K} + a_{i-L}` sur les entiers.

La contrainte `0 <= s_i < W` pour tout `i < T` est alors un probleme de VECTEUR LE PLUS
PROCHE dans un reseau de rang `L` plonge dans `Z^T` — exactement la forme que
`lab/lll_exact.py` sait resoudre en exact (LLL par la matrice de Gram, puis Babai).

COMBIEN DE MOTS ?
=================
Chaque coordonnee `i >= L` rapporte `log2(somme_m |a_{i,m}|)` bits, et les `a` croissent
exponentiellement : le compte est donc QUADRATIQUE en `T`, pas lineaire. Il faut

    somme_{i=L}^{T-1} log2(somme_m |a_{i,m}|)  >=  25,68 * L,

soit quelques dizaines de mots — une a deux fenetres de tirage, pas cent.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lll_exact import babai                                             # noqa: E402

M32 = 1 << 32
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ le generateur planté

def engendre(K, L, graine, ntir, shift):
    """une suite (K, L) lue par troncature avec rejet ; renvoie (tirages tries, classes,
    mots, etat initial)."""
    rng = random.Random(graine)
    r = [rng.randrange(M32) for _ in range(L)]
    etat = list(r)
    i = L
    W = 1 << (32 - shift)

    def mot():
        nonlocal i
        r.append((r[i - K] + r[i - L]) % M32)
        i += 1
        return r[i - 1]

    def classe(x):
        return ((x >> shift) * POOL) // W

    tirages, cls, mots = [], [], []
    del etat[:]                       # l'etat pertinent est celui des L PREMIERS MOTS EMIS
    for _ in range(ntir):
        vus = set()
        while len(vus) < DRAWN:
            x = mot()
            mots.append(x)
            c = classe(x)
            cls.append(c)
            vus.add(c)
        tirages.append(sorted(v + 1 for v in vus))
    return tirages, cls, mots, mots[:L]


# ------------------------------------------------------------------ le relèvement

def coefficients(K, L, T):
    """a[i] : les L coefficients ENTIERS de s_i sur (s_0, ..., s_{L-1})."""
    a = [[1 if m == i else 0 for m in range(L)] for i in range(L)]
    for i in range(L, T):
        a.append([a[i - K][m] + a[i - L][m] for m in range(L)])
    return a


def log2_det(K, L, T, a=None):
    """log2 du determinant du reseau {(somme_m a_{i,m} x_m)_{i<T}}, EXACT.

    `det(Lambda)^2 = det(A^T A)` ou `A` est la matrice `T x L` des coefficients. La matrice
    de Gram est entiere ; son determinant se calcule sans fraction par l'elimination de
    Bareiss (chaque pivot divise exactement), ce qui evite l'annulation catastrophique
    d'un calcul flottant — les colonnes de `A` sont presque paralleles (elles suivent
    toutes la racine dominante du trinome), donc le determinant est minuscule devant les
    entrees et un float64 n'en garde aucun chiffre.
    """
    a = a if a is not None else coefficients(K, L, T)
    G = [[sum(a[i][p] * a[i][q] for i in range(T)) for q in range(L)] for p in range(L)]
    prev = 1
    for c in range(L):
        if G[c][c] == 0:
            p = next((r for r in range(c + 1, L) if G[r][c] != 0), None)
            if p is None:
                return -1.0
            G[c], G[p] = G[p], G[c]
        for r in range(c + 1, L):
            for q in range(c + 1, L):
                G[r][q] = (G[r][q] * G[c][c] - G[r][c] * G[c][q]) // prev
            G[r][c] = 0
        prev = G[c][c]
    d = G[L - 1][L - 1]
    if d <= 0:
        return -1.0
    import math
    b = d.bit_length()
    return 0.5 * (b - 53 + math.log2(float(d >> max(0, b - 53)))) if b > 53 else 0.5 * math.log2(d)


def mots_utiles(K, L, cible_bits, marge=10.0, tmax=20000):
    """plus petit T tel que log2 det du reseau atteigne cible_bits + marge.

    C'est LE bon critere, et il remplace tout compte en « nombre de mots » : le point vrai
    est l'unique point du reseau dans la boite `[0, W)^T` des que le volume de la boite
    tient dans une maille, c'est-a-dire des que `log2 det >= L * (32 - log2 80)`. La
    vitesse a laquelle le determinant croit est celle de la racine dominante du trinome,
    qui tend vers 1 quand le degre monte — d'ou des T tres differents d'un trinome a
    l'autre.
    """
    lo, hi = 2 * L, 4 * L
    while hi < tmax and log2_det(K, L, hi) < cible_bits + marge:
        lo, hi = hi, int(hi * 1.6) + 10
    if hi >= tmax:
        return -1
    while hi - lo > max(5, L // 2):
        mi = (lo + hi) // 2
        if log2_det(K, L, mi) >= cible_bits + marge:
            hi = mi
        else:
            lo = mi
    return hi


def releve(cls, K, L, T, shift=0, marge=2):
    """des classes aux L mots initiaux. Renvoie (etat, s) ou (None, raison)."""
    W = M32 // POOL                       # 53 687 091
    Mb = [(c * M32 + POOL - 1) // POOL for c in cls[:T]]     # bas de la classe
    largeur = W + 1 + (2 * marge if shift else 0)
    # (i) les e_i, determines
    a = coefficients(K, L, T)
    beta = [0] * T
    for i in range(L, T):
        base = Mb[i - K] + Mb[i - L] - Mb[i]
        cand = [e for e in (0, 1, 2) if -2 * largeur < base - e * M32 < largeur]
        if len(cand) != 1:
            return None, f"e_{i} indetermine ({len(cand)} candidats)"
        D = base - cand[0] * M32
        beta[i] = beta[i - K] + beta[i - L] + D
    # (ii) CVP : 0 <= sum_m a[i][m] s_m + beta_i < largeur
    B = [[a[i][m] for i in range(T)] for m in range(L)]
    cible = [largeur // 2 - beta[i] for i in range(T)]
    v, R, coeffs = babai(B, cible)
    # les coordonnees 0..L-1 de v SONT (s_0, ..., s_{L-1}) : a[m][m'] = delta
    s = [v[m] for m in range(L)]
    if any(not (0 <= x < largeur) for x in s):
        return None, f"s hors bornes : {s[:4]}"
    return [Mb[m] + s[m] for m in range(L)], s


def rejoue(etat, K, L, ntir, shift):
    """rejoue les tirages a partir des L PREMIERS MOTS CONSOMMES (et non d'une graine
    anterieure) : le mot `etat[0]` est le premier mot du premier tirage."""
    r = list(etat)
    n = 0                    # indice du prochain mot a consommer
    W = 1 << (32 - shift)
    tirages = []
    for _ in range(ntir):
        vus = set()
        while len(vus) < DRAWN:
            if n >= len(r):
                r.append((r[len(r) - K] + r[len(r) - L]) % M32)
            vus.add(((r[n] >> shift) * POOL) // W)
            n += 1
        tirages.append(sorted(v + 1 for v in vus))
    return tirages


if __name__ == "__main__":
    say("h153 — relevement de la troncature (synthetique : aucune donnee reelle n'est lue)\n")
    CAS = [(2, 5, ""), (1, 6, ""), (3, 7, "TYPE_1"), (1, 15, "TYPE_2"), (3, 17, ""),
           (3, 31, "TYPE_3"), (1, 63, "TYPE_4")]
    if "--gros" in sys.argv:
        CAS = [c for c in CAS if c[1] >= 15]
    elif "--petit" in sys.argv:
        CAS = [c for c in CAS if c[1] < 15]
    say(f"{'K,L':>7} {'nom':>7} | {'shift':>5} | {'T requis':>8} | {'T utilise':>9} | "
        f"{'etat exact':>10} | {'tirage suiv':>11} | {'sec':>6}")
    bilan = []
    for K, L, nom in CAS:
        for shift in (0, 1):
            Treq = mots_utiles(K, L, 25.68 * L)
            if Treq < 0:
                say(f"{K:3d},{L:3d} {nom:>7} | {shift:5d} | hors de portee (determinant trop lent)")
                continue
            T = Treq
            ntir = max(3, T // 20 + 4)
            tir, cls, mots, etat = engendre(K, L, 4242 + K + 100 * L, ntir + 1, shift)
            if len(cls) < T:
                say(f"{K:3d},{L:3d} {nom:>7} | {shift:5d} | {Treq:8d} | pas assez de mots")
                continue
            t0 = time.time()
            e, s = releve(cls, K, L, T, shift)
            sec = time.time() - t0
            if e is None:
                say(f"{K:3d},{L:3d} {nom:>7} | {shift:5d} | {Treq:8d} | {T:9d} | "
                    f"{'ECHEC':>10} | {s:>9} | {sec:6.1f}")
                bilan.append(False)
                continue
            juste = (e == etat)
            pred = rejoue(e, K, L, ntir + 1, shift)[ntir] if juste else None
            bon = pred == tir[ntir]
            say(f"{K:3d},{L:3d} {nom:>7} | {shift:5d} | {Treq:8d} | {T:9d} | "
                f"{'OUI' if juste else 'non':>10} | {'20/20' if bon else 'non':>9} | {sec:6.1f}")
            bilan.append(juste and bon)
    say(f"\n   relevement : {sum(bilan)}/{len(bilan)} cas exacts")
