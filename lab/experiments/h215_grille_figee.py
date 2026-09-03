"""h215 — LA GRILLE FIGÉE : le même excès, mais sans aucune nulle simulée
(RAPPORT §238).

POURQUOI UNE TROISIÈME LECTURE
==============================
Le §236 a vu `k = 10` dépasser son `95ᵉ` centile. Le §237 refait la nulle proprement. Mais
les deux reposent sur des **répliques** — donc sur une simulation de ce que la chaîne complète
fait au hasard. Il existe une façon de poser la même question sans simuler quoi que ce soit.

> **Si l'on fige la grille avant la tranche de mesure, la nulle devient exacte.**

Une grille de dix numéros **fixée d'avance** rapporte, sous SRS, exactement `2,5` justes par
tirage, avec une variance hypergéométrique connue :

    Var(justes) = k·(20/80)·(60/80)·(80−k)/79 = 1,66139   pour k = 10

Sur `27 424` tirages indépendants, l'écart-type de la moyenne vaut `0,007782` — **calculé, pas
estimé**. Plus de répliques, plus de sur-apprentissage résiduel, plus de géométrie de traits à
faire coïncider entre l'archive et sa nulle : la sélection s'est faite sur des données
disjointes, donc elle ne peut rien fabriquer.

CE QUE ÇA SÉPARE
================
Un excès de justes peut venir de deux choses très différentes :

  * **un biais persistant sur des numéros précis** — alors une grille figée sur la première
    moitié le garde sur la seconde, et le test le voit ;
  * **une sélection qui bouge** — le modèle recompose sa grille à chaque tirage, et l'excès
    n'est qu'un artefact de cette recomposition, qui ne survit pas au gel.

**Le §236 ne peut pas distinguer les deux. Celui-ci le peut.**

DEUX GRILLES, CHOISIES SUR LA TRANCHE D'AJUSTEMENT SEULE
=========================================================
  **A** — les dix numéros de score moyen le plus élevé sous le modèle du §236 ;
  **B** — les dix numéros de taux historique le plus élevé, sans modèle du tout.

Chacune jouée **sans changer une seule fois** sur les `27 424` tirages de la tranche de
mesure, et sur chacune de ses deux moitiés.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h213_modele_non_lineaire as H13                                 # noqa: E402

POOL, DRAWN, K = 80, 20, 10
EXP_ID = "h215.grille_figee"
FJETON = "/tmp/h215_jeton.json"


def say(*a):
    print(*a, flush=True)


def var_exacte(k):
    """variance hypergeometrique du nombre de justes d'une grille FIXE de k numeros."""
    return k * (DRAWN / POOL) * ((POOL - DRAWN) / POOL) * (POOL - k) / (POOL - 1)


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    TS = np.asarray(A.ts).astype(np.int64)
    BONUS = np.asarray(A.bonus).astype(np.int64)
    BOOST = np.asarray(A.boost).astype(np.int64)
    N = len(M)
    veille = np.zeros(N, np.int8)
    veille[np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1]] = 1
    coupe = H13.CHAUFFE + int((N - H13.CHAUFFE) * H13.PART)
    milieu = coupe + (N - coupe) // 2
    VAR = var_exacte(K)

    HYP = (f"L'exces de justes vu au §236 a k = 10 ne survit pas au gel de la grille. Le "
           f"§236 et le §237 reposent tous deux sur des REPLIQUES, donc sur une simulation "
           f"de ce que la chaine fait au hasard. Ici la nulle devient EXACTE : une grille de "
           f"dix numeros fixee AVANT la tranche de mesure rapporte, sous SRS, exactement 2,5 "
           f"justes par tirage, de variance hypergeometrique connue "
           f"k(20/80)(60/80)(80-k)/79 = {VAR:.5f}, soit un ecart-type de la moyenne de "
           f"{sqrt(VAR/(N-coupe)):.6f} sur les {N-coupe} tirages de mesure — CALCULE, pas "
           f"estime. Plus de repliques, plus de sur-apprentissage residuel, plus de "
           f"geometrie de traits a faire coincider entre l'archive et sa nulle : la "
           f"selection s'est faite sur des donnees disjointes, donc elle ne peut rien "
           f"fabriquer. Et cela SEPARE deux choses que le §236 ne peut pas distinguer — un "
           f"biais persistant sur des numeros precis, qu'une grille figee garde, et une "
           f"selection qui bouge, dont l'exces ne survit pas au gel. Deux grilles, choisies "
           f"sur la tranche d'ajustement seule : A les dix numeros de score moyen le plus "
           f"eleve sous le modele du §236, B les dix numeros de taux historique le plus "
           f"eleve, sans modele du tout")
    STAT = (f"nombre moyen de justes de chaque grille FIGEE sur la tranche de mesure entiere "
            f"et sur chacune de ses deux moities, soit 6 statistiques")
    NUL = (f"EXACTE, sans simulation : grille fixee d'avance -> E[justes] = k/4 = 2,5 par "
           f"theoreme, et Var = {VAR:.5f} par la loi hypergeometrique. Les tirages etant "
           f"independants sous SRS, la moyenne sur n tirages a pour ecart-type "
           f"racine(Var/n) exactement")
    VER = ("BIAIS PERSISTANT si une grille figee depasse +3 ecarts-types sur la tranche "
           "entiere ET sur ses deux moities ; sinon l'exces du §236 ne tient pas au gel, "
           "donc il vient de la recomposition de la grille et non d'un biais sur des "
           "numeros precis")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="A")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    # --- grille A : le modele du §236, score moyen sur la tranche d'ajustement
    Xb = H13.base(M, BONUS, BOOST, veille, H13.CHAUFFE, coupe)
    nf = Xb.shape[2]
    w, b, mu, sd = H13.ajuster(Xb[H13.CHAUFFE:coupe].reshape(-1, nf),
                               M[H13.CHAUFFE:coupe].reshape(-1).astype(np.float64))
    Saj = H13.scorer(Xb[H13.CHAUFFE:coupe].reshape(-1, nf), w, b, mu, sd)
    moy = Saj.reshape(-1, POOL).mean(axis=0)
    GA = np.argsort(-moy)[:K]
    del Xb, Saj

    # --- grille B : les dix plus chauds de la tranche d'ajustement, sans modele
    GB = np.argsort(-M[H13.CHAUFFE:coupe].mean(axis=0))[:K]

    say(f"\n   grille A (modele du §236) : {sorted((GA + 1).tolist())}")
    say(f"   grille B (dix plus chauds) : {sorted((GB + 1).tolist())}")
    say(f"   recouvrement des deux grilles : {len(set(GA.tolist()) & set(GB.tolist()))}/10")
    say(f"\n   variance exacte des justes : {VAR:.5f}   (grille FIXE de dix)")

    say(f"\n   {'grille':>8} | {'tranche':>16} | {'tirages':>8} | {'justes':>9} | "
        f"{'ecart-type':>10} | {'z':>7} | {'p':>9}")
    tout = []
    for nom, G in (("A", GA), ("B", GB)):
        for lib, a, z2 in (("entiere", coupe, N), ("moitie 1", coupe, milieu),
                           ("moitie 2", milieu, N)):
            n = z2 - a
            j = float(M[a:z2][:, G].sum(axis=1).mean())
            se = sqrt(VAR / n)
            zz = (j - K / 4) / se
            p = float(erfc(abs(zz) / sqrt(2)))
            tout.append((nom, lib, j, zz, p))
            say(f"   {nom:>8} | {lib:>16} | {n:8d} | {j:9.5f} | {se:10.6f} | {zz:+7.2f} | "
                f"{p:9.4g}")

    zmax = max(t[3] for t in tout)
    pmin = min(t[4] for t in tout)
    persistant = all(t[3] > 3.0 for t in tout if t[0] == "A") or \
        all(t[3] > 3.0 for t in tout if t[0] == "B")
    verdict = "BIAIS PERSISTANT" if persistant else "conforme"
    say(f"\n   z maximal {zmax:+.2f}   p minimal {pmin:.4g}   ->   {verdict}")
    if not persistant:
        say("   -> une grille FIGEE ne garde pas l'exces du §236 : il vient de la "
            "recomposition,")
        say("      pas d'un biais sur des numeros precis.")

    TOK["m_extra"] = 5
    lab.record(
        TOK, float(zmax), p=float(pmin), verdict=verdict,
        power_at=(f"la nulle etant EXACTE, la puissance se calcule au lieu de se mesurer : "
                  f"l'ecart-type de la moyenne vaut {sqrt(VAR/(N-coupe)):.6f} juste sur la "
                  f"tranche entiere, donc le test voit a trois sigma un exces de "
                  f"{3*sqrt(VAR/(N-coupe)):.5f} juste, soit un deplacement de marge de "
                  f"{3*sqrt(VAR/(N-coupe))/K:.6f} par numero. Le seuil de RENTABILITE, par "
                  f"l'hypergeometrique non centrale de Fisher a la mise la moins chere de "
                  f"CHF 1,50, est a +0,162 juste : sept fois plus haut"),
        notes=(f"LA GRILLE FIGEE (§238) — troisieme lecture de l'exces du §236, celle-ci "
               f"SANS AUCUNE NULLE SIMULEE. Une grille de dix fixee avant la tranche de "
               f"mesure a une nulle exacte : 2,5 justes, variance hypergeometrique "
               f"{VAR:.5f}, ecart-type de la moyenne {sqrt(VAR/(N-coupe)):.6f} calcule. Cela "
               f"separe un biais PERSISTANT sur des numeros precis (qu'une grille figee "
               f"garde) d'une SELECTION QUI BOUGE (dont l'exces ne survit pas au gel), ce "
               f"que le §236 ne pouvait pas distinguer. "
               + " ; ".join(f"{t[0]} {t[1]} : {t[2]:.5f} juste, z = {t[3]:+.2f}"
                            for t in tout)
               + f". {verdict}."))
    say("   consigne.")
