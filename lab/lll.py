"""Réduction de réseau LLL, et plus proche vecteur par Babai.

Pourquoi ce fichier existe
--------------------------
h10 concluait qu'aucun point de fonctionnement n'existait pour LLL sur la
famille multiply-shift. Cette conclusion utilisait la borne PIRE CAS de LLL,
2^(d/4) — soit 2¹⁰ en dimension 41. C'est la mauvaise borne : en pratique
LLL atteint un facteur d'Hermite racine de δ₀ ≈ 1,0219, donc un facteur
d'approximation de δ₀^d ≈ 2,4 en dimension 40, pas 1024. Face à une marge
mesurée à ≈ ×18, l'attaque devient plausible. h10 se trompait, et la seule
façon honnête de trancher est de l'implémenter.

Aucune bibliothèque de réduction n'est disponible ici (ni fpylll, ni sympy,
ni flint), d'où cette implémentation.

Choix de conception : la base reste en entiers EXACTS, l'orthogonalisation
de Gram-Schmidt est en flottants. Les entrées valent ≈ 2⁷⁰, donc un
float64 perd des bits — c'est sans conséquence, parce que LLL ne sert ici
qu'à PROPOSER des candidats : chacun est ensuite vérifié en arithmétique
entière exacte contre les tirages observés. Un candidat faux est rejeté,
jamais accepté par erreur.
"""

import math


def _gso(basis):
    """Gram-Schmidt en flottants : renvoie (mu, normes carrées des b*)."""
    n = len(basis)
    fb = [[float(x) for x in row] for row in basis]
    bstar = []
    mu = [[0.0] * n for _ in range(n)]
    norms = [0.0] * n
    for i in range(n):
        v = fb[i][:]
        for j in range(i):
            if norms[j] == 0.0:
                mu[i][j] = 0.0
                continue
            d = sum(fb[i][t] * bstar[j][t] for t in range(len(v)))
            mu[i][j] = d / norms[j]
            m = mu[i][j]
            for t in range(len(v)):
                v[t] -= m * bstar[j][t]
        bstar.append(v)
        norms[i] = sum(x * x for x in v)
    return mu, norms, bstar


def lll(basis, delta=0.99, max_rounds=400):
    """Réduit une base entière. La base rendue est exacte (entiers)."""
    b = [list(map(int, row)) for row in basis]
    n = len(b)
    mu, norms, _ = _gso(b)
    k = 1
    rounds = 0
    while k < n and rounds < max_rounds * n:
        rounds += 1
        for j in range(k - 1, -1, -1):
            if abs(mu[k][j]) > 0.5:
                q = int(round(mu[k][j]))
                if q:
                    b[k] = [b[k][t] - q * b[j][t] for t in range(len(b[k]))]
                    mu, norms, _ = _gso(b)
        if norms[k] >= (delta - mu[k][k - 1] ** 2) * norms[k - 1]:
            k += 1
        else:
            b[k], b[k - 1] = b[k - 1], b[k]
            mu, norms, _ = _gso(b)
            k = max(k - 1, 1)
    return b


def babai(basis, target):
    """Plus proche vecteur approché (plan le plus proche de Babai)."""
    b = lll(basis)
    mu, norms, bstar = _gso(b)
    n = len(b)
    w = [float(x) for x in target]
    coeffs = [0] * n
    for i in range(n - 1, -1, -1):
        if norms[i] == 0.0:
            continue
        c = sum(w[t] * bstar[i][t] for t in range(len(w))) / norms[i]
        ci = int(round(c))
        coeffs[i] = ci
        for t in range(len(w)):
            w[t] -= ci * float(b[i][t])
    out = [0] * len(target)
    for i in range(n):
        if coeffs[i]:
            for t in range(len(out)):
                out[t] += coeffs[i] * b[i][t]
    return out, b


def hermite_factor(basis):
    """δ₀ empirique de la base réduite — sert à contrôler que LLL a travaillé."""
    b = lll(basis)
    n = len(b)
    shortest = min(math.sqrt(sum(float(x) * float(x) for x in row)) for row in b)
    _, norms, _ = _gso(b)
    logdet = sum(0.5 * math.log(v) for v in norms if v > 0)
    if shortest <= 0 or n == 0:
        return float("nan")
    return math.exp((math.log(shortest) - logdet / n) / n)
