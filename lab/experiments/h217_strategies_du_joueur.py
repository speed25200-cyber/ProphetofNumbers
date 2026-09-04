"""h217 — LES STRATÉGIES DU JOUEUR, avec la nulle exacte du §239
(RAPPORT §240).

POURQUOI CETTE SECTION EXISTE
=============================
Le §239 a tué « chaud reste chaud » avec une nulle **calculée** — pas simulée — sur toute
l'archive. Ce protocole-là est le meilleur du dossier pour cette question précise :

    grille choisie sur le passé,  mesurée sur l'avenir
    -> E[justes] = k/4 EXACTEMENT, et Var(moyenne) = 1,66139/n EXACTEMENT

Il ne coûte rien de l'appliquer aux **autres** stratégies — celles qu'un joueur essaie
vraiment, et qu'il paye parfois cher dans une application de loterie.

LES SEPT RÈGLES
===============
  **chauds** — les dix de plus fort taux sur les mille tirages précédents ;
  **froids** — les dix de plus faible taux ;
  **en retard** — les dix dont la dernière sortie est la plus ancienne. Ce n'est **pas** la
     même chose que « froids » : l'un compte les sorties, l'autre mesure une attente, et
     c'est la forme exacte de l'erreur du joueur (« il est dû ») ;
  **récents** — les dix sortis le plus récemment ;
  **liés au tirage précédent** — les dix de plus fort levier de co-occurrence
     `Ĉ(n,m) = P(n,m ensemble)/(P(n)P(m)) − 1` sommé sur les vingt numéros du tirage `t−1`.
     C'est le canal que le §7.37 désigne comme celui qui paie, joué pour de vrai ;
  **opposés au tirage précédent** — les dix de plus faible levier ;
  **grille fixe** — `1` à `10`, qui ne dépend de rien. Le contrôle : sa nulle est exacte par
     construction, donc son `z` mesure le bruit de l'instrument et rien d'autre.

Trois horizons (`d = 1`, `10`, `100`) : vingt et une statistiques, chacune avec sa nulle
exacte, sur soixante-dix mille tirages ou trente-cinq mille selon la règle.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN, K = 80, 20, 10
EXP_ID = "h217.strategies_du_joueur"
FJETON = "/tmp/h217_jeton.json"
FEN = 1000
HORIZONS = (1, 10, 100)
VAR = K * (DRAWN / POOL) * ((POOL - DRAWN) / POOL) * (POOL - K) / (POOL - 1)


def say(*a):
    print(*a, flush=True)


def scores(M, coupe_lift):
    """(nom, score (N,80), premier t utilisable) pour chaque regle. Tout est causal :
    le score du tirage t n'utilise que des tirages STRICTEMENT anterieurs."""
    N = len(M)
    Mf = M.astype(np.float32)
    C = np.cumsum(Mf, axis=0, dtype=np.float32)
    Cp = np.zeros_like(C)
    Cp[1:] = C[:-1]

    taux = np.full(Mf.shape, np.nan, np.float32)
    taux[FEN:] = (Cp[FEN:] - Cp[:-FEN]) / FEN

    idx = np.where(Mf > 0, np.arange(N, dtype=np.float32)[:, None], -1.0)
    der = np.maximum.accumulate(idx, axis=0)
    derp = np.zeros_like(der)
    derp[1:] = der[:-1]
    derp[0] = -1.0
    attente = np.arange(N, dtype=np.float32)[:, None] - derp      # ecart depuis la sortie

    T = Mf[:coupe_lift]
    co = (T.T @ T) / len(T)
    marg = T.mean(axis=0)
    lift = (co / np.maximum(marg[:, None] * marg[None, :], 1e-9) - 1.0).astype(np.float32)
    np.fill_diagonal(lift, 0.0)
    prev = np.zeros_like(Mf)
    prev[1:] = Mf[:-1]
    lien = prev @ lift

    fixe = np.zeros((N, POOL), np.float32)
    fixe[:, :K] = 1.0

    return [("chauds", taux, FEN),
            ("froids", -taux, FEN),
            ("en retard", attente, FEN),
            ("recents", -attente, FEN),
            ("lies au tirage precedent", lien, coupe_lift),
            ("opposes au tirage precedent", -lien, coupe_lift),
            ("grille fixe 1-10 (controle)", fixe, FEN)]


def joue(M, S, deb, d):
    N = len(M)
    fin = N - d
    top = np.argpartition(-S[deb:fin], K - 1, axis=1)[:, :K]
    cible = M[deb + d:fin + d]
    h = cible[np.arange(len(top))[:, None], top].sum(axis=1)
    return float(h.mean()), len(h)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    COUPE = N // 2

    HYP = (f"Aucune des sept regles qu'un joueur essaie vraiment ne bat k/4 = {K/4}. Le §239 "
           f"a tue « chaud reste chaud » avec une nulle CALCULEE et non simulee — grille "
           f"choisie sur le passe, mesuree sur l'avenir, donc E[justes] = k/4 exactement a "
           f"chaque t et Var(moyenne) = {VAR:.5f}/n exactement, les termes etant non "
           f"correles par conditionnement sur le passe. Il ne coute rien d'appliquer ce "
           f"protocole aux autres regles. Sept : les dix plus chauds et les dix plus froids "
           f"sur les {FEN} tirages precedents ; les dix EN RETARD, dont la derniere sortie "
           f"est la plus ancienne — ce qui n'est PAS « froids », l'un comptant les sorties "
           f"et l'autre mesurant une attente, et c'est la forme exacte de l'erreur du joueur "
           f"(« il est du ») ; les dix RECENTS ; les dix de plus fort LEVIER DE CO-OCCURRENCE "
           f"avec le tirage precedent, canal que le §7.37 designe comme celui qui paie, joue "
           f"pour de vrai ; les dix de plus faible levier ; et la grille fixe 1-10, qui ne "
           f"depend de rien et dont le z mesure le bruit de l'instrument et rien d'autre. "
           f"Trois horizons d = {HORIZONS}")
    STAT = (f"nombre moyen de justes de chaque regle a chaque horizon, {7*len(HORIZONS)} "
            f"statistiques, chacune contre sa nulle exacte")
    NUL = (f"EXACTE, sans simulation : E = {K/4} par theoreme, Var = {VAR:.5f} par la loi "
           f"hypergeometrique, termes non correles. L'ecart-type de la moyenne vaut "
           f"racine(Var/n) exactement")
    VER = (f"STRATEGIE GAGNANTE si un |z| depasse le seuil de Bonferroni interne a "
           f"{7*len(HORIZONS)} statistiques (|z| > 3,38 pour alpha = 5 %) ; conforme sinon")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="A")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say("\n   selftest : les sept regles sur une archive SRS")
    W = lab.srs(N, np.random.default_rng(217))
    for nom, S, deb in scores(W, COUPE):
        j, n = joue(W, S, deb, 1)
        say(f"      {nom:>30} : {j:.5f}  z = {(j - K/4)/sqrt(VAR/n):+5.2f}")
    del W

    say(f"\n   variance exacte {VAR:.5f} ; seuil de Bonferroni interne |z| > 3,38")
    say(f"\n   {'regle':>30} | {'d':>4} | {'tirages':>8} | {'justes':>9} | {'z':>7} | "
        f"{'p':>9}")
    lignes = []
    for nom, S, deb in scores(M, COUPE):
        for d in HORIZONS:
            j, n = joue(M, S, deb, d)
            z = (j - K / 4) / sqrt(VAR / n)
            p = float(erfc(abs(z) / sqrt(2)))
            lignes.append((nom, d, n, j, z, p))
            say(f"   {nom:>30} | {d:4d} | {n:8d} | {j:9.5f} | {z:+7.2f} | {p:9.4g}")

    zmax = max(abs(l[4]) for l in lignes)
    arg = max(lignes, key=lambda l: abs(l[4]))
    pmin = min(l[5] for l in lignes)
    verdict = "STRATEGIE GAGNANTE" if zmax > 3.38 else "conforme"
    say(f"\n   |z| maximal {zmax:.2f} ({arg[0]}, d = {arg[1]})   p = {pmin:.4g}   ->   "
        f"{verdict}")
    say(f"   le meilleur des sept, en marge : {(arg[3]-K/4)/K:+.6f} par numero contre 0,25 ; "
        f"il en faudrait +0,016 pour l'equilibre a CHF 1,50")

    TOK["m_extra"] = len(lignes) - 1
    lab.record(
        TOK, float(zmax), p=float(pmin), verdict=verdict,
        power_at=(f"la nulle etant exacte, la puissance se calcule : l'ecart-type de la "
                  f"moyenne vaut {sqrt(VAR/(N-FEN)):.6f} juste sur les regles a fenetre "
                  f"glissante et {sqrt(VAR/(N-COUPE)):.6f} sur celles a levier, donc le test "
                  f"voit a trois sigma un exces de {3*sqrt(VAR/(N-COUPE)):.5f} juste. Le "
                  f"seuil de RENTABILITE, par l'hypergeometrique non centrale de Fisher a la "
                  f"mise la moins chere de CHF 1,50, est a +0,162 juste : plus de dix fois "
                  f"plus haut. Le controle « grille fixe » borne le bruit de l'instrument"),
        notes=(f"LES STRATEGIES DU JOUEUR (§240) — le protocole a nulle EXACTE du §239 "
               f"applique aux sept regles qu'un joueur essaie vraiment : chauds, froids, en "
               f"retard (l'erreur du joueur, distincte de « froids »), recents, lies au "
               f"tirage precedent par le levier de co-occurrence du §7.37, opposes, et une "
               f"grille fixe de controle. {len(lignes)} statistiques x 3 horizons. |z| "
               f"maximal {zmax:.2f} ({arg[0]}, d = {arg[1]}) contre un seuil de Bonferroni "
               f"interne de 3,38, p = {pmin:.4g}."))
    say("   consigne.")
