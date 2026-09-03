"""h216 — « CHAUD RESTE CHAUD », testé à pleine puissance et sans une seule simulation
(RAPPORT §239).

D'OÙ VIENT CETTE SECTION
========================
Le §238 a figé deux grilles de dix numéros choisies sur la tranche d'ajustement. Celle du
modèle du §236 est retombée **exactement** sur la nulle : `2,50018` juste contre `2,5`, soit
`z = +0,02` — l'excès du §236 vient de la recomposition de la grille, pas d'un biais sur des
numéros précis.

Mais la seconde grille, **les dix numéros les plus chauds**, a rendu `2,51583`, soit
`z = +2,03`. Ce n'est rien après multiplicité, et c'est la plus vieille hypothèse du jeu :

> **Un numéro sorti souvent sort-il ensuite plus souvent ?**

Le §238 ne la testait que sur **une** coupure et **une** grille. On peut faire beaucoup mieux,
et sans simuler quoi que ce soit.

LE TEST EXACT, ET POURQUOI IL EST EXACT
=======================================
À chaque tirage `t`, on choisit les dix numéros les plus chauds sur la fenêtre `[t−w, t)` —
donc sur des tirages **strictement antérieurs** — puis on compte les justes au tirage `t+d`.

Sous SRS, la grille est une fonction du passé et le tirage à venir en est indépendant, donc

    E[justes] = k/4 = 2,5   EXACTEMENT, à chaque t

et de plus les termes sont **non corrélés** : pour `s > t`,
`E[h_t·h_s] = E[h_t·E[h_s | passé]] = 2,5·E[h_t] = 2,5²`. Donc

    Var(moyenne sur n tirages) = Var(hypergéométrique)/n = 1,66139/n   EXACTEMENT

Sur près de soixante-dix mille tirages, l'écart-type de la moyenne tombe à `0,0049` — contre
`0,0078` pour la coupure unique du §238. **La puissance monte d'un facteur `1,6`, et la nulle
reste calculée au lieu d'être estimée.**

CE QU'ON BALAIE
===============
Quatre fenêtres de sélection (`500`, `1 000`, `2 000`, `5 000` tirages), trois horizons de
mesure (`d = 1`, `10`, `100`), et les deux bouts du classement — les plus **chauds** et les
plus **froids**. Vingt-quatre statistiques, chacune avec sa nulle exacte.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN, K = 80, 20, 10
EXP_ID = "h216.chaud_reste_chaud"
FJETON = "/tmp/h216_jeton.json"
FENETRES = (500, 1000, 2000, 5000)
HORIZONS = (1, 10, 100)
VAR = K * (DRAWN / POOL) * ((POOL - DRAWN) / POOL) * (POOL - K) / (POOL - 1)


def say(*a):
    print(*a, flush=True)


def taux_glissant(M, w):
    """(N,80) : taux de sortie de chaque numero sur la fenetre [t-w, t), STRICTEMENT
    anterieure. Les t < w sont marques invalides."""
    C = np.cumsum(M, axis=0, dtype=np.int32)
    Cp = np.zeros_like(C)
    Cp[1:] = C[:-1]
    A = np.full(M.shape, np.nan, np.float32)
    A[w:] = (Cp[w:] - Cp[:-w]) / w
    return A


def joue(M, A, w, d, chaud=True):
    """selectionne les K extremes sur la fenetre finissant en t, mesure au tirage t+d."""
    N = len(M)
    deb, fin = w, N - d
    S = A[deb:fin] if chaud else -A[deb:fin]
    top = np.argpartition(-S, K - 1, axis=1)[:, :K]
    cible = M[deb + d:fin + d]
    h = cible[np.arange(len(top))[:, None], top].sum(axis=1)
    return float(h.mean()), len(h)


if __name__ == "__main__":
    import lab

    A_ = lab.load()
    M = np.asarray(A_.mask)
    N = len(M)

    HYP = (f"Un numero sorti souvent ne sort pas ensuite plus souvent. Le §238 a fige les "
           f"dix plus chauds sur UNE coupure et a rendu z = +2,03 ; c'est la plus vieille "
           f"hypothese du jeu et elle merite un test a pleine puissance. A chaque tirage t "
           f"on choisit les dix plus chauds sur la fenetre [t-w, t) — donc sur des tirages "
           f"STRICTEMENT anterieurs — puis on compte les justes au tirage t+d. La nulle est "
           f"EXACTE et ne demande aucune simulation : la grille etant fonction du passe et "
           f"le tirage a venir en etant independant sous SRS, E[justes] = k/4 = 2,5 "
           f"exactement a chaque t ; et les termes sont NON CORRELES puisque pour s > t, "
           f"E[h_t h_s] = E[h_t E[h_s | passe]] = 2,5 E[h_t], donc Var(moyenne sur n) = "
           f"{VAR:.5f}/n exactement. Sur pres de {N} tirages l'ecart-type de la moyenne "
           f"tombe a {sqrt(VAR/N):.4f} contre {sqrt(VAR/27424):.4f} pour la coupure unique "
           f"du §238 : la puissance monte d'un facteur 1,6 et la nulle reste calculee au "
           f"lieu d'etre estimee. On balaie quatre fenetres de selection {FENETRES}, trois "
           f"horizons de mesure {HORIZONS}, et les deux bouts du classement — les plus "
           f"chauds et les plus froids")
    STAT = (f"nombre moyen de justes d'une grille des {K} extremes glissants, pour "
            f"{len(FENETRES)} fenetres x {len(HORIZONS)} horizons x 2 bouts = "
            f"{len(FENETRES)*len(HORIZONS)*2} statistiques, chacune contre sa nulle exacte")
    NUL = (f"EXACTE, sans simulation : E[justes] = {K/4} par theoreme, "
           f"Var = {VAR:.5f} par la loi hypergeometrique, termes non correles par "
           f"conditionnement sur le passe. L'ecart-type de la moyenne vaut racine(Var/n) "
           f"exactement, n etant le nombre de tirages mesures")
    VER = (f"MEMOIRE si un |z| depasse le seuil de Bonferroni interne a "
           f"{len(FENETRES)*len(HORIZONS)*2} statistiques (|z| > 3,29 pour alpha = 5 %) ; "
           f"conforme sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="A")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # --- selftest : la nulle exacte, verifiee sur du SRS
    say("\n   selftest : la nulle exacte, sur une archive SRS")
    W = lab.srs(N, np.random.default_rng(216))
    Aw = taux_glissant(W, 1000)
    j, n = joue(W, Aw, 1000, 1, True)
    se = sqrt(VAR / n)
    say(f"      SRS, fenetre 1000, d = 1 : {j:.5f} juste sur {n} tirages, "
        f"z = {(j - K/4)/se:+.2f}")
    del W, Aw

    say(f"\n   variance exacte {VAR:.5f} ; seuil de Bonferroni interne |z| > 3,29")
    say(f"\n   {'bout':>7} | {'fenetre':>8} | {'d':>4} | {'tirages':>8} | {'justes':>9} | "
        f"{'z':>7} | {'p':>9}")
    lignes = []
    for w in FENETRES:
        Aw = taux_glissant(M, w)
        for d in HORIZONS:
            for chaud in (True, False):
                j, n = joue(M, Aw, w, d, chaud)
                se = sqrt(VAR / n)
                z = (j - K / 4) / se
                p = float(erfc(abs(z) / sqrt(2)))
                lignes.append((("chauds" if chaud else "froids"), w, d, n, j, z, p))
                say(f"   {'chauds' if chaud else 'froids':>7} | {w:8d} | {d:4d} | {n:8d} | "
                    f"{j:9.5f} | {z:+7.2f} | {p:9.4g}")
        del Aw

    zmax = max(abs(l[5]) for l in lignes)
    arg = max(lignes, key=lambda l: abs(l[5]))
    pmin = min(l[6] for l in lignes)
    verdict = "MEMOIRE" if zmax > 3.29 else "conforme"
    say(f"\n   |z| maximal {zmax:.2f} ({arg[0]}, fenetre {arg[1]}, d = {arg[2]})   "
        f"p = {pmin:.4g}   ->   {verdict}")
    say(f"   converti en marge : {(arg[4]-K/4)/K:+.6f} par numero contre 0,25")

    TOK["m_extra"] = len(lignes) - 1
    lab.record(
        TOK, float(zmax), p=float(pmin), verdict=verdict,
        power_at=(f"la nulle etant exacte, la puissance se calcule : l'ecart-type de la "
                  f"moyenne vaut {sqrt(VAR/(N-5000)):.6f} juste sur la plus courte des "
                  f"series, donc le test voit a trois sigma un exces de "
                  f"{3*sqrt(VAR/(N-5000)):.5f} juste, soit un deplacement de marge de "
                  f"{3*sqrt(VAR/(N-5000))/K:.6f} par numero. Le seuil de RENTABILITE, par "
                  f"l'hypergeometrique non centrale de Fisher a la mise la moins chere de "
                  f"CHF 1,50, est a +0,162 juste — plus de dix fois plus haut"),
        notes=(f"CHAUD RESTE CHAUD (§239) — la plus vieille hypothese du jeu, testee a "
               f"pleine puissance et SANS UNE SEULE SIMULATION. A chaque tirage on prend les "
               f"dix extremes de la fenetre [t-w, t) et on mesure au tirage t+d ; la grille "
               f"etant fonction du passe, E = 2,5 exactement et les termes sont non "
               f"correles, donc Var(moyenne) = {VAR:.5f}/n exactement. "
               f"{len(lignes)} statistiques ({len(FENETRES)} fenetres x {len(HORIZONS)} "
               f"horizons x chauds/froids). |z| maximal {zmax:.2f} ({arg[0]}, fenetre "
               f"{arg[1]}, d = {arg[2]}) contre un seuil de Bonferroni interne de 3,29, "
               f"p = {pmin:.4g}."))
    say("   consigne.")
