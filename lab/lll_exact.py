"""LLL et plus proche vecteur (Babai) EXACTS, pour les réseaux de petit rang
dont les vecteurs sont très longs et très grands.

Pourquoi ce fichier existe
--------------------------
`lll.py` orthogonalise en flottants : suffisant quand les entrées valent ≈ 2^70 et
que chaque candidat est ensuite vérifié. Le relèvement de l'état haut d'un
Fibonacci retardé (THEORIE_ETAT §7.8) pose un problème différent : un réseau de
rang L = 7 dans Z^n avec n ≈ 400 à 1000 coordonnées et des entrées jusqu'à
2^200 (les formes entières croissent comme M(f)^n). Là, un float64 ne réduit
rien : la base « réduite » est fausse et Babai renvoie n'importe quoi (mesuré :
0 succès sur 8 tailles de fenêtre, alors que le point du réseau dans la boîte
est unique).

Choix de conception : tout passe par la matrice de Gram, calculée UNE fois en
entiers exacts (L² produits scalaires de longueur n). LLL et Babai ne
manipulent ensuite que des rationnels exacts de dimension L (Fraction), et la
matrice unimodulaire U est suivie ; la base réduite est U·B, reconstruite à la
fin. Le coût est dominé par les L² produits scalaires initiaux, pas par la
réduction.
"""

from fractions import Fraction


def _gso_gram(G):
    """Gram-Schmidt exact à partir de la matrice de Gram : (mu, normes carrées des b*)."""
    n = len(G)
    mu = [[Fraction(0)] * n for _ in range(n)]
    Bs = [Fraction(0)] * n
    for i in range(n):
        for j in range(i):
            s = Fraction(G[i][j])
            for k in range(j):
                s -= mu[i][k] * mu[j][k] * Bs[k]
            mu[i][j] = s / Bs[j] if Bs[j] else Fraction(0)
        s = Fraction(G[i][i])
        for k in range(i):
            s -= mu[i][k] * mu[i][k] * Bs[k]
        Bs[i] = s
    return mu, Bs


def lll_gram(G, delta=Fraction(99, 100)):
    """LLL sur une matrice de Gram entière ; renvoie (U, G_reduite) avec U unimodulaire,
    base réduite = U · base."""
    n = len(G)
    G = [list(row) for row in G]
    U = [[int(i == j) for j in range(n)] for i in range(n)]

    def swap(k):
        U[k], U[k - 1] = U[k - 1], U[k]
        G[k], G[k - 1] = G[k - 1], G[k]
        for row in G:
            row[k], row[k - 1] = row[k - 1], row[k]

    mu, Bs = _gso_gram(G)
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            q = round(mu[k][j])
            if q:
                # mise à jour de Gram exacte : G'[k][t] = G[k][t] - q G[j][t] (t != k),
                # G'[k][k] = G[k][k] - 2 q G[k][j] + q² G[j][j]
                gkk = G[k][k] - 2 * q * G[k][j] + q * q * G[j][j]
                for t in range(n):
                    if t != k:
                        G[k][t] -= q * G[j][t]
                        G[t][k] = G[k][t]
                G[k][k] = gkk
                U[k] = [a - q * b for a, b in zip(U[k], U[j])]
                mu, Bs = _gso_gram(G)
        if Bs[k] >= (delta - mu[k][k - 1] * mu[k][k - 1]) * Bs[k - 1]:
            k += 1
        else:
            swap(k)
            mu, Bs = _gso_gram(G)
            k = max(k - 1, 1)
    return U, G


def _matvec(U, B):
    """U · B pour U entière n×n et B liste de n vecteurs."""
    out = []
    for row in U:
        v = [0] * len(B[0])
        for coef, b in zip(row, B):
            if coef:
                for t in range(len(v)):
                    v[t] += coef * b[t]
        out.append(v)
    return out


def gram(B):
    return [[sum(x * y for x, y in zip(bi, bj)) for bj in B] for bi in B]


def lll(B):
    """Base réduite exacte (liste de vecteurs entiers)."""
    U, _ = lll_gram(gram(B))
    return _matvec(U, B)


def babai(B, target):
    """Plus proche plan de Babai, exact. Renvoie (coefficients sur la base réduite,
    vecteur du réseau, base réduite)."""
    n = len(B)
    U, G = lll_gram(gram(B))
    R = _matvec(U, B)
    mu, Bs = _gso_gram(G)
    # produits scalaires <w, b_i> pour w = cible, puis mis à jour quand w <- w - c b_i
    wb = [sum(x * y for x, y in zip(target, b)) for b in R]
    coeffs = [0] * n
    for i in range(n - 1, -1, -1):
        # <w, b*_i> = <w, b_i> - sum_{j<i} mu_ij <w, b*_j>
        wbs = [Fraction(0)] * n
        for a in range(i + 1):
            s = Fraction(wb[a])
            for j in range(a):
                s -= mu[a][j] * wbs[j]
            wbs[a] = s
        if Bs[i] == 0:
            continue
        c = round(wbs[i] / Bs[i])
        coeffs[i] = c
        if c:
            for j in range(n):
                wb[j] -= c * G[i][j]
    v = [0] * len(target)
    for i in range(n):
        if coeffs[i]:
            for t in range(len(v)):
                v[t] += coeffs[i] * R[i][t]
    return v, R, coeffs


def _autotest():
    import random
    rng = random.Random(7)
    # un réseau de rang 3 planté dans Z^40 avec des entrées ≈ 2^120 ; on cache un point
    # et on cherche le plus proche d'une cible bruitée
    B = [[rng.getrandbits(120) - (1 << 119) for _ in range(40)] for _ in range(3)]
    G0 = [rng.randrange(-1000, 1000) for _ in range(3)]
    p = [sum(G0[j] * B[j][t] for j in range(3)) for t in range(40)]
    target = [x + rng.randrange(-1000, 1000) for x in p]
    v, R, _ = babai(B, target)
    assert v == p, "autotest : point caché non retrouvé"
    # les bases engendrent le même réseau : les normes réduites ne dépassent pas les originales
    nr = [sum(x * x for x in b) for b in R]
    assert min(nr) <= min(sum(x * x for x in b) for b in B)
    print("autotest lll_exact : ok")


if __name__ == "__main__":
    _autotest()
