"""Énumération EXACTE des points d'un réseau dans une boîte — Babai sans son heuristique.

POURQUOI CE FICHIER EXISTE
==========================
Les §230 et §232 relèvent l'état d'un LCG tronqué par **réseau + Babai**, et rendent zéro sur
`368 640` relèvements. Ce zéro est le plus large du dossier, et il repose sur une
**heuristique** : le plan le plus proche de Babai ne rend pas toujours le vecteur le plus
proche. Le §232 le disait, et s'en protégeait par un crible exhaustif — mais seulement pour
`m ≤ 2³²`, là où l'énumération des `m/80` candidats est possible. Le §250 a étendu ce crible à
toute cette moitié. **Au-dessus de `2³²`, l'heuristique reste seule.**

Or l'énoncé qu'on veut n'est pas « Babai n'a rien trouvé ». C'est :

> Il n'existe **aucun** point du réseau dans la boîte des contraintes.

Et cet énoncé-là se démontre, sans jamais faire confiance à un arrondi : on **énumère** tous
les points du réseau dans la boule qui circonscrit la boîte, puis on filtre par la boîte.

LA BOÎTE, ET POURQUOI ELLE EST LA BONNE FIGURE
==============================================
La contrainte n'est pas « proche de la cible » mais, coordonnée par coordonnée :

    lo_i <= x*A_i + B_i mod m <= hi_i

c'est-à-dire un **pavé** de côtés `hi_i − lo_i`, et non une boule. Babai vise le centre du
pavé, ce qui est déjà une approximation de la question. On énumère donc dans la boule de rayon
`R = ½·sqrt(sum (hi_i − lo_i)²)` — qui contient le pavé tout entier — et l'on rejette ensuite
ce qui tombe hors du pavé. Aucun point du pavé ne peut échapper à cette boule.

    volume du pave    (m/80)^n / m^(n-1) = m / 80^n
    n = 14, m = 2^64  ->  2^64 / 80^14 ~ 2^-24

Donc, sous l'hypothèse nulle, l'énumération ne rend **rien** — et c'est bien pour cela qu'un
seul point trouvé serait un résultat.

L'ARITHMÉTIQUE EST EXACTE, ET C'EST TOUT L'INTÉRÊT
==================================================
Tout est en `Fraction` et en entiers : la décomposition de Gram-Schmidt, les bornes de
Fincke-Pohst, le test d'appartenance au pavé. Un énumérateur en flottants perdrait le sens de
l'exercice — des normes carrées de l'ordre de `2¹²⁸` ne tiennent pas dans une mantisse de
cinquante-trois bits, et « je n'ai rien trouvé » redeviendrait une opinion.
"""

from fractions import Fraction
from math import isqrt

from lll_exact import _gso_gram, gram, lll_gram, _matvec


def _projections(R, mu, Bs, t):
    """coordonnees de la cible sur la base de Gram-Schmidt, exactes."""
    n = len(R)
    tb = [sum(x * y for x, y in zip(t, b)) for b in R]
    G = [[sum(x * y for x, y in zip(bi, bj)) for bj in R] for bi in R]
    tbs = [Fraction(0)] * n
    for a in range(n):
        s = Fraction(tb[a])
        for j in range(a):
            s -= mu[a][j] * tbs[j]
        tbs[a] = s
    return [tbs[i] / Bs[i] if Bs[i] else Fraction(0) for i in range(n)], G


def _bornes(centre: Fraction, q: Fraction):
    """les entiers x tels que (x - centre)^2 <= q, sous forme (min, max). Exact.

    C'est ici qu'une premiere version se trompait : elle bornait par le plus petit entier
    dont le carre DEPASSE q, ce qui rejette le tout premier candidat et fait croire au
    niveau qu'il est epuise. L'enumeration rendait alors un noeud et zero point — y compris
    sur un point qu'on venait d'y planter.
    """
    if q < 0:
        return 1, 0                                   # intervalle vide
    r = isqrt(q.numerator * q.denominator) // q.denominator      # floor(sqrt(q))
    lo, hi = int(centre) - r - 2, int(centre) + r + 2
    while lo <= hi and (Fraction(lo) - centre) ** 2 > q:
        lo += 1
    while hi >= lo and (Fraction(hi) - centre) ** 2 > q:
        hi -= 1
    return lo, hi


def prepare(B):
    """reduit la base UNE FOIS et rend (R, mu, Bs).

    Le reseau ne depend que de (m, A, n) — ni du canal, ni de la regle de troncature, ni de
    la fenetre, qui ne changent que le PAVE. Or c'est la reduction qui coute, pas le
    parcours : sur un module de 2^64 en dimension 14, la reduction exacte prend une dizaine
    de secondes et l'enumeration visite sept noeuds. Separer les deux divise le balayage par
    le nombre de paves qui partagent un meme reseau.

    Et la qualite de la reduction ne change **rien** au resultat : n'importe quelle base du
    meme reseau donne le meme ensemble de points. Elle ne change que le nombre de noeuds
    visites. C'est ce qui distingue cette methode de Babai, dont la reponse, elle, depend
    de la base.
    """
    U, G0 = lll_gram(gram(B))
    return (_matvec(U, B),) + _gso_gram(G0)


def points_dans_boule(B, t, rho, noeuds_max=2_000_000, prep=None):
    """TOUS les points du reseau engendre par B a distance carree <= rho de t.

    Fincke-Pohst / Schnorr-Euchner, en arithmetique exacte. Renvoie
    `(liste des points, nombre de noeuds visites, complet)`. `complet` vaut False si le
    budget de noeuds a ete epuise — auquel cas le resultat n'autorise AUCUNE conclusion
    negative, et l'appelant doit le dire plutot que de conclure.
    """
    R, mu, Bs = prep if prep is not None else prepare(B)
    n = len(R)
    c, _ = _projections(R, mu, Bs, t)

    sortie, noeuds = [], 0
    coeff = [0] * n
    # centre[i] = c_i - sum_{j>i} mu_ji * (x_j - c_j) : mis a jour en descendant
    centre = [Fraction(0)] * n
    reste = [Fraction(0)] * n            # rho - somme des ecarts des niveaux > i
    lo, hi = [0] * n, [0] * n

    def ouvre(i):
        """fixe les bornes ENTIERES du niveau i, puis place le curseur juste avant."""
        if Bs[i] == 0:                    # base degeneree : un seul choix possible
            lo[i] = hi[i] = round(centre[i])
        else:
            lo[i], hi[i] = _bornes(centre[i], reste[i] / Bs[i])
        coeff[i] = lo[i] - 1

    i = n - 1
    centre[i], reste[i] = c[i], Fraction(rho)
    ouvre(i)
    while True:
        noeuds += 1
        if noeuds > noeuds_max:
            return sortie, noeuds, False
        coeff[i] += 1
        if coeff[i] > hi[i]:              # ce niveau est epuise : on remonte
            i += 1
            if i == n:
                break
            continue
        # par construction des bornes, le rayon est respecte : rien a retester
        if i == 0:
            v = [0] * len(t)
            for k in range(n):
                if coeff[k]:
                    for s in range(len(v)):
                        v[s] += coeff[k] * R[k][s]
            sortie.append(v)
            continue
        d = Fraction(coeff[i]) - centre[i]
        reste[i - 1] = reste[i] - d * d * Bs[i]
        # decomposition GSO de l'erreur : sum_i x_i b_i - t a pour i-eme coordonnee
        #     e_i = x_i + sum_{j>i} x_j mu_ji - c_i,
        # donc le centre du niveau i vaut c_i - sum_{j>i} mu_ji x_j. Une premiere version
        # y soustrayait mu_ji (x_j - c_j) : le terme en c_j n'a rien a y faire, et le point
        # plante n'etait alors meme pas dans le reseau engendre par les coefficients visites.
        s = c[i - 1]
        for j in range(i, n):
            s -= mu[j][i - 1] * coeff[j]
        centre[i - 1] = s
        i -= 1
        ouvre(i)
    return sortie, noeuds, True


def points_dans_pave(B, los, his, noeuds_max=2_000_000, prep=None):
    """TOUS les points du reseau dont la coordonnee i tient dans [los_i, his_i].

    C'est la vraie question — la contrainte est un pave, pas une boule. On enumere dans la
    boule circonscrite au pave, qui le contient tout entier, puis on filtre exactement.
    """
    n = len(los)
    t = [Fraction(los[i] + his[i], 2) for i in range(n)]
    rho = sum(Fraction(his[i] - los[i], 2) ** 2 for i in range(n))
    dans, noeuds, complet = points_dans_boule(B, t, rho, noeuds_max, prep)
    return ([v for v in dans if all(los[i] <= v[i] <= his[i] for i in range(n))],
            noeuds, complet)


def _autotest():
    """On PLANTE un point dans le pave et l'on exige que l'enumeration le rende. Sans
    temoin, « aucun point » ne veut rien dire — c'est la lecon du §223 et du §232."""
    import random

    rng = random.Random(20260904)
    ok = True
    for essai in range(6):
        n = 5 + essai
        m = 1 << 40
        A = rng.randrange(3, m) | 1
        Ai, pw = [], 1
        for _ in range(n):
            pw = (pw * A) % m
            Ai.append(pw)
        base = [Ai] + [[m if j == i else 0 for j in range(n)] for i in range(n)]
        x = rng.randrange(1, m)
        pt = [(x * Ai[i]) % m for i in range(n)]
        # un pave de demi-largeur m/160 autour du point plante : il y est, par construction
        demi = m // 160
        los = [pt[i] - demi for i in range(n)]
        his = [pt[i] + demi for i in range(n)]
        trouves, noeuds, complet = points_dans_pave(base, los, his)
        dedans = any(all(v[i] == pt[i] for i in range(n)) for v in trouves)
        ok &= dedans and complet
        print(f"   dim {n:2d} : {len(trouves):4d} point(s) dans le pave, {noeuds:6d} noeuds, "
              f"le point plante {'TROUVE' if dedans else 'MANQUE'}"
              f"{'' if complet else '  (BUDGET EPUISE)'}")
    # Temoin NEGATIF, et il doit avoir la MEME TAILLE DE PAVE que le probleme reel : un
    # pave minuscule rend zero en un noeud, ce qui ne teste rien du parcours. On garde donc
    # la demi-largeur m/160 et l'on deplace seulement le centre, au hasard.
    for n in (8, 10, 12):
        m = 1 << 40
        A = rng.randrange(3, m) | 1
        Ai, pw = [], 1
        for _ in range(n):
            pw = (pw * A) % m
            Ai.append(pw)
        base = [Ai] + [[m if j == i else 0 for j in range(n)] for i in range(n)]
        cible = [rng.randrange(m) for _ in range(n)]
        demi = m // 160
        tr, nd, cp = points_dans_pave(base, [x - demi for x in cible],
                                      [x + demi for x in cible])
        att = m / 80.0 ** n
        print(f"   temoin NEGATIF dim {n:2d} : {len(tr)} point(s), {nd:6d} noeuds "
              f"(esperance de volume : {att:.2e})")
        ok &= (len(tr) == 0 and cp)
    print(f"   -> {'CALIBRE' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    import sys

    print("cvp_exact : enumeration exacte, temoins plantes")
    sys.exit(0 if _autotest() else 1)
