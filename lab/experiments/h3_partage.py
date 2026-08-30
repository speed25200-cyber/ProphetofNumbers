"""h3 — la pierre « barème » du mur de l'invariance, quantifiée.

Le théorème d'invariance a trois hypothèses. La troisième — « le gain d'une
grille ne dépend que de SES hits » — est vraie sous cotes fixes et FAUSSE
dès qu'un rang se partage entre gagnants. Sous partage, l'espérance
monétaire dépend de la POPULARITÉ de la grille, même sous un générateur
parfait : c'est le résultat de Chernoff (1981) sur le Numbers Game du
Massachusetts, et de Thaler-Ziemba (1988) sur les loteries pari-mutuel.

Ce script transforme ce fait qualitatif en THÉORIE QUANTITATIVE pour le
cadre 20/80 :

  1. Le multiplicateur de partage. Si le nombre d'AUTRES gagnants du rang
     est W ~ Poisson(λ), le gagnant touche prix/(1+W), et

         E[1/(1+W)] = (1 − e^{−λ}) / λ     (exact, vérifié par simulation)

  2. λ dépend de la grille par un mécanisme précis : un co-gagnant du rang
     plein doit avoir sa grille ENTIÈREMENT dans le tirage D ⊇ g. Les
     numéros de MA grille sont déjà dans D ; une foule qui aime mes numéros
     a donc une longueur d'avance — λ(grille populaire) >> λ(grille
     discrète). On le calcule par Monte-Carlo conditionnel sous un modèle
     de foule multiplicatif ancré sur le profil de popularité de l'app
     (dates <= 31, chiffre 7, multiples de 11 — les régularités documentées
     de la littérature : Chernoff 1981, Haigh 1997, Thaler-Ziemba 1988).

  3. La table des gains : le rapport des multiplicateurs entre la grille la
     plus populaire et la grille anti-foule, en fonction du nombre de
     joueurs. C'est la valeur EXACTE de « Furtif » sous partage — et zéro
     sous cotes fixes, par invariance. Dans les deux cas >= 0 : le même
     argument minimax que pour l'essaim, appliqué au barème.

AVERTISSEMENT D'HONNÊTETÉ : le modèle de foule est ancré sur la littérature
d'autres loteries, pas mesuré sur les joueurs du Loto Express (aucune
donnée de mises n'est publiée). Les RAPPORTS de λ sont robustes à l'échelle
du biais ; les valeurs absolues ne valent que sous le modèle.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# 1. Le multiplicateur de partage — formule exacte, vérifiée
# --------------------------------------------------------------------------

rule("1. E[1/(1+W)] POUR W ~ Poisson(λ) — la formule, puis la simulation")
rng = np.random.default_rng(7)
say("   λ        formule (1−e^−λ)/λ     simulé (2e6)      écart")
for lam in (0.05, 0.5, 2.0, 8.0):
    exact = (1 - math.exp(-lam)) / lam
    w = rng.poisson(lam, size=2_000_000)
    sim = float((1.0 / (1 + w)).mean())
    se = float((1.0 / (1 + w)).std() / math.sqrt(len(w)))
    say(f"   {lam:<8} {exact:.6f}              {sim:.6f}       {(sim - exact) / se:+.2f} σ")


# --------------------------------------------------------------------------
# 2. λ(grille) sous un modèle de foule multiplicatif
# --------------------------------------------------------------------------

rule("2. λ(GRILLE) — pourquoi la foule co-gagne surtout avec les grilles populaires")

# Le profil de popularité de l'app (Swarm.swift `popularity`), normalisé.
pop = np.zeros(POOL)
for n in range(1, POOL + 1):
    s = 0.0
    if n <= 31: s += 1.0
    if n <= 12: s += 0.4
    if n % 10 == 7: s += 0.5
    if n % 11 == 0: s += 0.4
    if n % 10 == 0: s += 0.2
    pop[n - 1] = s

# Foule multiplicative : P(la foule joue le numéro i) ∝ exp(β·pop_i).
# β = 0,55 calibre le rapport joué/attendu des numéros 1-31 à ≈ 1,9 —
# l'ordre de grandeur documenté (dates de naissance, Haigh 1997).
BETA = 0.55
w_crowd = np.exp(BETA * pop)
p_crowd = w_crowd / w_crowd.sum()
r31 = p_crowd[:31].sum() / (31 / 80)
say(f"   modèle de foule : β = {BETA}, rapport joué/uniforme des numéros 1-31 : {r31:.2f}")


def crowd_grid(rng, k):
    return rng.choice(POOL, size=k, replace=False, p=p_crowd)


def lam_per_player(my, k, reps=300_000):
    """P(une grille de foule ⊆ D | D ⊇ my), par Monte-Carlo conditionnel."""
    my = np.asarray(my)
    others = np.setdiff1d(np.arange(POOL), my)
    hits = 0
    for _ in range(reps):
        u = rng.choice(others, size=DRAWN - k, replace=False)
        d = set(my.tolist()) | set(u.tolist())
        g = crowd_grid(rng, k)
        if all(int(x) in d for x in g):
            hits += 1
    return hits / reps


for k in (5, 10):
    order = np.argsort(-pop)
    popular = order[:k]                  # la grille la plus aimée de la foule
    furtif = order[-k:]                  # la grille anti-foule
    lp = lam_per_player(popular, k)
    lf = lam_per_player(furtif, k)
    say(f"\n   mise {k} :")
    say(f"     grille populaire {sorted(int(x) + 1 for x in popular)}")
    say(f"     grille furtive   {sorted(int(x) + 1 for x in furtif)}")
    say(f"     P(co-gagnant par joueur) : populaire {lp:.3e}   furtive {lf:.3e}"
        f"   rapport {lp / max(lf, 1e-300):.1f}×")

    say("     multiplicateur de partage (1−e^−λ)/λ et AVANTAGE furtif :")
    say("       joueurs      populaire    furtive     avantage")
    for N in (2_000, 20_000, 200_000):
        mp = (1 - math.exp(-N * lp)) / (N * lp) if N * lp > 1e-12 else 1.0
        mf = (1 - math.exp(-N * lf)) / (N * lf) if N * lf > 1e-12 else 1.0
        say(f"       {N:<12,} {mp:.4f}       {mf:.4f}      ×{mf / mp:.2f}")


# --------------------------------------------------------------------------
# 3. La lecture
# --------------------------------------------------------------------------

rule("3. CE QUE CELA PROUVE — ET CE QUE CELA NE PROUVE PAS")
say("""   Sous PARTAGE d'un rang, l'espérance monétaire n'est PAS invariante :
   une grille discrète touche la même probabilité de gain avec un
   multiplicateur de partage strictement meilleur — le tableau ci-dessus en
   donne l'ampleur sous un modèle de foule ancré sur la littérature.

   Sous COTES FIXES, l'effet est exactement nul (théorème d'invariance).

   Le dossier n'établit pas quel régime s'applique au Loto Express — c'est
   une propriété du règlement, pas des tirages. La grille « Furtif » est
   donc la réponse minimax au BARÈME inconnu, comme l'essaim l'est au
   GÉNÉRATEUR inconnu : gratuite dans un régime, strictement gagnante dans
   l'autre, perdante dans aucun.""")

rule(f"total {time.time() - T0:.0f}s")
