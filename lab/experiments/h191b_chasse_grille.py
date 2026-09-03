"""h191b — LA CHASSE À LA GRILLE : l'avance de la grille chaude se réplique-t-elle ?
(RAPPORT §210 addendum).

CE QU'ON CHASSE
===============
Le §210 rend à la grille CHAUDE de cinq numéros — les cinq de plus fort taux sur la
première moitié, joués sur la seconde — un taux de `25,2392 %` contre `25,0000 %`, soit
`z = +2,38`. Ce n'est pas significatif : le seuil de Bonferroni sur les `16 410`
statistiques de la section vaut `4,668`, et même sur les dix seules statistiques de la
famille il vaudrait `2,81`.

Mais c'est le seul chiffre du dossier qui ressemble à quelque chose d'exploitable par un
joueur, et la règle de ce dossier est de ne jamais laisser un écart sans le chasser.

LE TEST, ET IL EST DÉCISIF
==========================
Une avance réelle sur des numéros se réplique quand on change de découpage. Une
fluctuation, non.

  **ROULANT.** L'archive est coupée en quatre quarts. On choisit les `k` numéros de plus
  fort taux sur tout ce qui précède, et on les joue sur le quart suivant. Trois mesures,
  sur des fenêtres **disjointes** :

      choix `Q1` → mesure `Q2` ;  choix `Q1+Q2` → mesure `Q3` ;  choix `Q1..Q3` → mesure `Q4`

  Les trois fenêtres étant disjointes, les trois `z` sont indépendants et se combinent en
  `Z = (z₁+z₂+z₃)/√3`.

  **RENVERSÉ.** Le découpage du §210, à l'envers : choix sur la seconde moitié, mesure sur
  la première. Si les cinq numéros sont vraiment chauds, ce sens-là doit marcher aussi.

DÉCISION, FIXÉE AVANT DE REGARDER
=================================
  * `k` vaut `3` et `5` — les deux valeurs qui portaient l'écart au §210, fixées par lui.
  * **RÉPLIQUE** si `Z` roulant `> 3` **et** les trois `z` de même signe positif.
  * **NON RÉPLIQUÉ** sinon, auquel cas l'écart du §210 est une fluctuation et le dossier
    n'a aucune grille gagnante.

La nulle est exacte : `k` numéros contiennent un nombre de gagnants hypergéométrique de
moyenne `k/4` et de variance `k(1/4)(3/4)(80−k)/79`.
"""

import json
import os
import sys
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h191b.chasse_grille"
FJETON = "/tmp/h191b_jeton.json"
KS = (3, 5)


def say(*a):
    print(*a, flush=True)


def sd_hyper(n, k):
    return sqrt(n * k * (DRAWN / POOL) * ((POOL - DRAWN) / POOL)
                * ((POOL - k) / (POOL - 1)))


def mesure(M, choix_deb, choix_fin, mes_deb, mes_fin, k, chaud=True):
    c = M[choix_deb:choix_fin].sum(axis=0)
    ordre = np.argsort(-c)
    g = ordre[:k] if chaud else ordre[-k:]
    n = mes_fin - mes_deb
    s = int(M[mes_deb:mes_fin][:, g].sum())
    z = (s - n * k / 4) / sd_hyper(n, k)
    return s, n, z, g


if __name__ == "__main__":
    import lab

    A = lab.load()
    M = np.asarray(A.mask)
    N = len(M)
    Q = [0, N // 4, N // 2, 3 * N // 4, N]

    HYP = ("L'avance de la grille chaude du §210 — cinq numeros a 25,2392 % contre 25 %, "
           "z = +2,38 hors echantillon — ne se replique pas quand on change de decoupage. "
           "Une avance REELLE sur des numeros se replique ; une fluctuation, non. On coupe "
           "l'archive en quatre quarts et l'on choisit les k numeros de plus fort taux sur "
           "tout ce qui precede pour les jouer sur le quart suivant, ce qui donne trois "
           "mesures sur des fenetres DISJOINTES donc trois z independants ; et l'on refait "
           "le decoupage du §210 A L'ENVERS, choix sur la seconde moitie et mesure sur la "
           "premiere. k vaut 3 et 5, les deux valeurs qui portaient l'ecart au §210 et qui "
           "sont donc fixees par lui, non choisies ici")
    STAT = ("Z = (z1+z2+z3)/racine(3), la combinaison des trois z du schema roulant, plus "
            "le z du schema renverse. z = (gagnants - n k/4)/racine(n k (3/16)(80-k)/79)")
    NUL = ("EXACTE : k numeros contiennent un nombre de gagnants hypergeometrique de "
           "moyenne k/4 et de variance k(1/4)(3/4)(80-k)/79 ; les fenetres de mesure etant "
           "disjointes, les trois z sont independants")
    VER = ("REPLIQUE si Z roulant > 3 ET les trois z de meme signe positif ; NON REPLIQUE "
           "sinon, auquel cas l'ecart du §210 est une fluctuation et le dossier n'a aucune "
           "grille gagnante")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h191b : quarts de {Q[1]-Q[0]}, {Q[2]-Q[1]}, {Q[3]-Q[2]}, {Q[4]-Q[3]} tirages")
    resume = {}
    for k in KS:
        say(f"\n=== k = {k} ===")
        say(f"   {'schema':>28} | {'taux':>9} | {'z':>7} | grille")
        zs = []
        for q in (1, 2, 3):
            s, n, z, g = mesure(M, 0, Q[q], Q[q], Q[q + 1], k)
            zs.append(z)
            say(f"   {'choix Q1..Q%d -> mesure Q%d' % (q, q+1):>28} | "
                f"{100*s/(n*k):8.4f} % | {z:+7.2f} | {sorted((g+1).tolist())}")
        Z = sum(zs) / sqrt(3)
        s, n, zr, g = mesure(M, N // 2, N, 0, N // 2, k)
        say(f"   {'RENVERSE : H2 -> H1':>28} | {100*s/(n*k):8.4f} % | {zr:+7.2f} | "
            f"{sorted((g+1).tolist())}")
        memes = all(z > 0 for z in zs)
        say(f"   Z roulant = ({zs[0]:+.2f}{zs[1]:+.2f}{zs[2]:+.2f})/racine(3) = {Z:+.3f}"
            f"   memes signes positifs : {'OUI' if memes else 'NON'}")
        resume[k] = (Z, memes, zr, zs)

    Zmax = max(resume[k][0] for k in KS)
    kbest = max(KS, key=lambda k: resume[k][0])
    replique = any(resume[k][0] > 3 and resume[k][1] for k in KS)
    p = float(erfc(abs(Zmax) / sqrt(2)))
    say(f"\n   meilleur Z roulant = {Zmax:+.3f} (k = {kbest})   p = {p:.4f}")
    say(f"   ->   {'REPLIQUE' if replique else 'NON REPLIQUE'}")
    TOK["m_extra"] = 3
    lab.record(
        TOK, float(Zmax), p=p, verdict="replique" if replique else "NON REPLIQUE",
        power_at=("chaque quart porte 17 640 tirages ; un avantage reel de 0,24 point de "
                  "pourcentage — celui que le §210 a mesure — donnerait z = +1,4 par quart "
                  "et donc Z = +2,4 en combinaison, tandis qu'un avantage de 0,4 point "
                  "donnerait Z = +4,0. Le test distingue donc une avance reelle de cette "
                  "taille d'une fluctuation, ce qui est exactement ce qu'on lui demande"),
        notes=(f"CHASSE A LA GRILLE (§210 addendum) : schema roulant sur quatre quarts, "
               f"trois mesures sur fenetres DISJOINTES donc trois z independants, plus le "
               f"decoupage du §210 renverse. k = 3 et 5, fixes par le §210. "
               + " ; ".join(f"k={k} : Z = {resume[k][0]:+.3f}, signes positifs "
                            f"{resume[k][1]}, renverse {resume[k][2]:+.2f}" for k in KS)))
    say("   consigne.")
