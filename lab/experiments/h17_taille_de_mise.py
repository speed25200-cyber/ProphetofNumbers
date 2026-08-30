"""h17 — combien miser, et ce que le gain rapporte vraiment.

La question qu'il serait malhonnête de ne pas poser
----------------------------------------------------
h16 établit un gain conditionnel de +29,5 % par franc misé, en ne jouant
qu'au-dessus du seuil de bascule. C'est une espérance. Ce n'est pas de
l'argent.

Entre les deux il y a la VARIANCE, et elle est ici démesurée : on gagne une
fois sur 7 753 et l'on touche 10 000 fois la mise. Une espérance positive
sur une loi aussi dissymétrique ne se convertit en croissance qu'à condition
de miser une fraction minuscule du capital — et si cette fraction tombe sous
le prix minimal d'un ticket, la stratégie n'est pas jouable, quelle que soit
son espérance.

Ce fichier calcule les trois nombres qui manquent :

  1. la fraction de capital à miser (Kelly), et le taux de croissance qui
     en résulte ;
  2. ce que l'étalement de h13 y change — et la réponse est un facteur n,
     le même que sur la probabilité de toucher, mais cette fois sur la
     CROISSANCE ;
  3. le capital minimal en dessous duquel le ticket le moins cher force déjà
     à surmiser — et surmiser dans un jeu aussi dissymétrique ne réduit pas
     le gain, il l'annule.

Le cadre
--------
Un franc misé sur une grille pleine rapporte J francs (la cagnotte), avec
J ≈ S(1 + α) = l'espérance de la cagnotte SACHANT qu'elle dépasse le seuil.
Les rangs intermédiaires sont ignorés : inconnus, ils ne peuvent qu'ajouter,
donc tous les chiffres ci-dessous sont des bornes basses.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRAWS_PER_DAY = 24 * 12                 # un tirage toutes les cinq minutes


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    return math.comb(DRAWN, k) / math.comb(POOL, k)


def kelly(q: float, b: float):
    """Fraction optimale et taux de croissance pour un pari (q, cote nette b)."""
    f = q - (1 - q) / b
    if f <= 0:
        return 0.0, 0.0
    g = q * math.log1p(f * b) + (1 - q) * math.log1p(-f)
    return f, g


def growth(f: float, q: float, b: float) -> float:
    if f <= 0 or f >= 1:
        return -math.inf
    return q * math.log1p(f * b) + (1 - q) * math.log1p(-f)


# Paramètres tirés du dossier : mise 6, seuil et gain conditionnel de h16.
K = 6
P1 = p_full(K)
S = 1 / P1
ALPHA = 2287 / S                        # relevé du 30 août 2026
J = S * (1 + ALPHA)                     # E[cagnotte | au-dessus du seuil]
FAV = math.exp(-1 / ALPHA)              # fraction de tirages favorables (h15)


# --------------------------------------------------------------------------
# 1. Une grille seule
# --------------------------------------------------------------------------

rule("1. UNE GRILLE SEULE — l'espérance ne dit pas ce qu'on gagne")

say(f"""   mise {K} numéros, p = 1/{S:,.0f}, cagnotte conditionnelle J = {J:,.0f} fois
   la mise, gain espéré +{ALPHA:.1%} par franc, occasions {FAV:.2%} des tirages.""")

f1, g1 = kelly(P1, J - 1)
say(f"""
   fraction de Kelly            {f1:.3e}  du capital, par occasion
   croissance par occasion      {g1:.3e}  en logarithme
   croissance par jour          {g1 * FAV * DRAWS_PER_DAY:.3e}
   croissance annualisée        {math.exp(g1 * FAV * DRAWS_PER_DAY * 365) - 1:+.1%}""")

say(f"""
   Lecture. L'espérance est de +{ALPHA:.1%} par franc, mais la croissance
   optimale ne consomme que {f1:.3e} du capital à chaque occasion — parce
   qu'à cette dissymétrie, miser davantage détruit plus de capital dans les
   {1 - P1:.4%} de pertes qu'il n'en gagne dans le reste.""")


# --------------------------------------------------------------------------
# 2. L'étalement de h13, mesuré en CROISSANCE
# --------------------------------------------------------------------------

rule("2. CE QUE L'ÉTALEMENT RAPPORTE — le facteur n, cette fois en croissance")

say("""   h13 montrait que n grilles disjointes touchent le rang plein n fois
   plus souvent, à espérance identique. La question est de savoir si ce gain
   de PROBABILITÉ se convertit en gain de CROISSANCE. Il se convertit, et
   presque exactement au même facteur.

   n grilles disjointes, capital étalé également : une seule peut être
   pleine, la cote nette devient J/n − 1 et la probabilité n·p.""")

say(f"\n   n grilles   fraction Kelly   croissance/occasion   rapport à n=1   croissance/an")
base = None
for n in (1, 2, 4, 8, 13):
    q = n * P1
    b = J / n - 1
    f, g = kelly(q, b)
    if base is None:
        base = g
    say(f"   {n:<11} {f:<16.3e} {g:<21.3e} ×{g / base:<13.2f} "
        f"{math.exp(g * FAV * DRAWS_PER_DAY * 365) - 1:+.1%}")

say(f"""
   Le rapport suit n à moins de 0,2 % près. {POOL // K} grilles disjointes font donc
   croître le capital {POOL // K} fois plus vite, pour la même espérance et le même
   argent misé — c'est le seul endroit du dossier où une géométrie de
   grilles se traduit en francs, et elle s'y traduit intégralement.

   La raison est que l'étalement ne touche pas l'espérance mais la
   DISSYMÉTRIE : n grilles disjointes gagnent n fois plus souvent n fois
   moins gros, ce qui laisse la moyenne intacte et divise la variance par n.
   Or la croissance de Kelly est, au premier ordre, le carré de l'avantage
   divisé par la variance.

   Le nombre maximal de grilles disjointes est ⌊80/k⌋ = {POOL // K} à la mise {K}.""")


# --------------------------------------------------------------------------
# 3. Vérification par simulation
# --------------------------------------------------------------------------

rule("3. VÉRIFICATION — le capital simulé croît-il au taux prédit ?")

rng = np.random.default_rng(20260830)
say("   Capital rejoué sur des millions d'occasions, à la fraction de Kelly.")
say("\n   n    occasions      croissance simulée   prédite      écart")
for n in (1, 13):
    q = n * P1
    b = J / n - 1
    f, g = kelly(q, b)
    trials = 40_000_000
    wins = rng.binomial(trials, q)
    # log-capital = wins·ln(1+f·b) + (trials−wins)·ln(1−f)
    logcap = wins * math.log1p(f * b) + (trials - wins) * math.log1p(-f)
    sim = logcap / trials
    sd = math.sqrt(q * (1 - q)) * abs(math.log1p(f * b) - math.log1p(-f)) / math.sqrt(trials)
    z = (sim - g) / sd
    say(f"   {n:<4} {trials:<14,} {sim:<20.4e} {g:<12.4e} {z:+.2f} σ")
    assert abs(z) < 4


# --------------------------------------------------------------------------
# 4. Le capital minimal — et c'est la contrainte qui décide
# --------------------------------------------------------------------------

rule("4. LE CAPITAL MINIMAL — la contrainte qui décide de tout")

say("""   La fraction de Kelly est un pourcentage du capital. Le ticket, lui, a
   un prix plancher. Si le premier tombe sous le second, on ne peut pas
   miser Kelly : on est forcé de SURMISER, et dans un jeu à cette
   dissymétrie surmiser ne réduit pas le gain, il l'annule.

   Capital minimal = prix d'un tour complet ÷ fraction de Kelly.""")

n = POOL // K
q = n * P1
b = J / n - 1
f_star, g_star = kelly(q, b)
say(f"\n   prix du ticket   coût d'un tour de {n} grilles   capital minimal pour Kelly")
for price in (0.50, 1.00, 2.00, 5.00):
    tour = price * n
    say(f"   CHF {price:<13.2f} CHF {tour:<25,.2f} CHF {tour / f_star:>14,.0f}")

say(f"""
   En dessous de ces montants, jouer un tour complet revient à miser plus
   que Kelly. De combien la croissance s'effondre-t-elle alors ?""")

say("\n   mise / Kelly   croissance/occasion   croissance annualisée")
for mult in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0):
    f = f_star * mult
    g = growth(f, q, b)
    ann = math.exp(g * FAV * DRAWS_PER_DAY * 365) - 1 if g > -math.inf else -1
    tag = "  <- optimum" if mult == 1.0 else ("  <- croissance nulle ou pire"
                                              if g <= 0 else "")
    say(f"   ×{mult:<13.1f} {g:>+20.3e}   {ann:>+20.1%}{tag}")

say(f"""
   La courbe est brutale : à deux fois Kelly la croissance est déjà
   quasiment nulle, au-delà elle est négative. Un joueur qui disposerait de
   CHF 1 000 et miserait un tour à CHF 1 la grille miserait
   ×{n * 1.0 / (1000 * f_star):.0f} Kelly — très au-delà du point où l'espérance positive
   cesse de produire de la croissance.

   C'est la conclusion pratique du dossier, et elle tempère h16 sans le
   contredire : le gain est réel, il est même important en espérance, mais
   il ne se convertit en capital qu'à partir d'une réserve de l'ordre de
   plusieurs dizaines de milliers de francs. En dessous, le pari reste
   favorable en espérance et perdant en croissance — ce qui, pour quelqu'un
   qui joue plus d'une fois, est ce qui compte.""")


# --------------------------------------------------------------------------
# 5. Ce que les rangs intermédiaires changeraient
# --------------------------------------------------------------------------

rule("5. CE QUE LE BARÈME INCONNU CHANGERAIT — dans le bon sens")

say("""   Tout ce qui précède ignore les rangs intermédiaires, faute de barème.
   Ils ne peuvent qu'ajouter, et ils ajoutent DEUX fois : ils augmentent
   l'espérance, et ils réduisent la dissymétrie — or c'est la dissymétrie qui
   écrase la fraction de Kelly.

   Modèle minimal : une fraction ρ de la mise revient par des rangs
   intermédiaires assimilés à un gain fréquent et petit (probabilité 1/10,
   remboursement ρ·10 fois la mise). Effet sur la croissance :""")

say("\n   ρ (retour des rangs intermédiaires)   fraction Kelly   croissance/occasion   ×")
for rho in (0.0, 0.20, 0.40, 0.60):
    # Deux issues : cagnotte (rare, énorme) et rang intermédiaire (fréquent).
    # Kelly numérique sur le mélange.
    q_small, b_small = 0.10, rho * 10 - 1
    best = (0.0, -math.inf)
    for f in np.linspace(1e-6, 0.02, 4000):
        g = (q * math.log1p(f * b) + q_small * math.log1p(f * b_small)
             + (1 - q - q_small) * math.log1p(-f))
        if g > best[1]:
            best = (f, g)
    say(f"   {rho:<37.2f} {best[0]:<16.3e} {best[1]:<21.3e} "
        f"×{best[1] / g_star:.1f}")

say(f"""
   Un retour intermédiaire de 40 % suffirait à multiplier la croissance par
   un facteur important — non parce qu'il rapporte davantage, mais parce
   qu'il rend la loi moins dissymétrique et autorise donc une mise plus
   grande. C'est une raison de plus de vouloir le barème : il ne déplace pas
   seulement l'espérance, il déplace la TAILLE DE MISE admissible, et c'est
   elle qui décide si le gain devient de l'argent.

   Réserve. Le modèle ci-dessus est délibérément grossier — un seul rang
   intermédiaire fictif — et ne sert qu'à montrer le SENS et l'ordre de
   grandeur de l'effet, pas à le chiffrer. Le barème réel le remplacerait
   immédiatement.""")

rule(f"total {time.time() - T0:.0f}s")
