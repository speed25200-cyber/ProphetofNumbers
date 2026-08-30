"""h49 — les deux courbes, et l'ordre ou elles se croisent.

La question que quarante voies laissent sans reponse chiffree
==============================================================
Le dossier a mesure quatre plafonds d'omniscience, un par ordre de couplage :
+1,33 % (marginal), +3,21 % (lineaire), +6,27 % (quadratique), +9,81 %
(cubique). Ils MONTENT avec l'ordre — le §41 en donne la loi, m^(1/4) a ||a||
constant, et le §64 a confirme la prediction au troisieme ordre.

La marge de l'operateur, elle, est fixe : 41,1 % (taux de retour de base
58,9 %, mesure au §62 avec le prix du ticket confirme).

Deux courbes, l'une qui monte et l'autre qui ne bouge pas : elles se croisent.
PERSONNE N'A CALCULE OU. C'est pourtant la seule facon de repondre a « quel
mur faut-il franchir », parce que la reponse n'est ni « le plafond est trop
bas » ni « la marge est trop haute » — elle est dans la position du
croisement, et dans ce qu'il faudrait savoir pour l'atteindre.

Ce que ce fichier calcule
=========================
1. La loi d'echelle plafond(m), ajustee sur les QUATRE points mesures.
2. Son extrapolation jusqu'a la marge, ordre par ordre.
3. Au point de croisement : combien de coefficients a estimer, et combien
   d'evenements binaires l'archive en contient.

Il ne teste pas l'archive : il ajuste et il extrapole. Registre : inchange.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
N_DRAWS, POOL = 70_560, 80
EVENTS = N_DRAWS * POOL
MARGE = 41.1                      # % — 100 - 58,9 (§62, prix du ticket confirme)

# Les quatre plafonds MESURES, chacun consigne au registre par son experience.
PTS = [(0, POOL, 1.33, "marginal (c0)"),
       (1, POOL * POOL, 3.21, "lineaire lag-1 (c1)"),
       (2, POOL * math.comb(POOL, 2), 6.27, "quadratique (h24, §40)"),
       (3, POOL * math.comb(POOL, 3), 9.81, "cubique (h27, §64)")]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def cells(d):
    return POOL if d == 0 else POOL * math.comb(POOL, d)


rule("1. LES QUATRE PLAFONDS MESURÉS, ET CE QU'ILS COÛTENT DÉJÀ")

say(f"""   L'archive contient {N_DRAWS:,} tirages de {POOL} indicatrices, soit
   {EVENTS:,} evenements binaires. C'est TOUT le budget d'information
   disponible, et il ne depend pas de l'ordre auquel on regarde.
""")
say(f"   {'ordre':>6} {'m cellules':>16} {'plafond':>10} {'evenements/cellule':>20}   famille")
for d, m, c, nom in PTS:
    say(f"   {d:>6} {m:>16,} {c:>9.2f} % {EVENTS / m:>19,.2f}   {nom}")

say("""
   La derniere colonne est celle qu'on ne regarde jamais, et c'est elle qui
   decide : a l'ordre 3 il y a deja MOINS D'UN evenement par cellule.""")


rule("2. LA LOI D'ÉCHELLE, AJUSTÉE SUR LES QUATRE POINTS")

xs = [math.log(m) for _, m, _, _ in PTS]
ys = [math.log(c) for _, _, c, _ in PTS]
n = len(xs)
b = (n * sum(x * y for x, y in zip(xs, ys)) - sum(xs) * sum(ys)) / \
    (n * sum(x * x for x in xs) - sum(xs) ** 2)
A = math.exp((sum(ys) - b * sum(xs)) / n)

say(f"""   plafond = {A:.4f} x m^{b:.4f}

   Le §41 predit l'exposant 1/4 a ||a|| constant. L'ajustement donne {b:.3f} :
   l'ecart est exactement la decroissance de ||a|| que le §41 mesurait et que
   le §64 a prolongee — une deviation repartie sur des cellules de plus en
   plus fines se convertit de moins en moins bien en avantage.

   Controle sur les quatre points mesures :""")
for d, m, c, _ in PTS:
    fit = A * m ** b
    say(f"     ordre {d} : ajuste {fit:>6.2f} %   mesure {c:>6.2f} %   ecart {abs(fit-c)/c:>5.1%}")


rule("3. OÙ LES DEUX COURBES SE CROISENT")

say(f"""   Une courbe monte (le plafond), l'autre ne bouge pas (la marge, {MARGE} %).
   Le croisement existe donc. Le voici.
""")
say(f"   {'ordre':>6} {'m cellules':>20} {'plafond':>10} {'evenem./cellule':>18}  ")
cross = None
for d in range(0, 8):
    m = cells(d)
    c = A * m ** b
    epc = EVENTS / m
    if c >= MARGE and cross is None:
        cross = (d, m, c, epc)
    tag = "  <= CROISEMENT" if cross and cross[0] == d else ""
    say(f"   {d:>6} {m:>20,} {c:>9.2f} % {epc:>17,.4f}{tag}")

d, m, c, epc = cross
say(f"""
   LE CROISEMENT EST À L'ORDRE {d}, et voici ce qu'il coûte.

     plafond d'omniscience        {c:.1f} %   (au-dessus de la marge de {MARGE} %)
     coefficients à estimer       {m:,}
     événements binaires dispo    {EVENTS:,}
     événements par coefficient   {epc:.5f}

   Au moment PRÉCIS où un adversaire omniscient rattraperait enfin la maison,
   il lui faudrait estimer {m/1e9:.1f} milliards de coefficients à partir de
   {EVENTS/1e6:.1f} millions d'événements : UN événement pour {1/epc:,.0f} coefficients.

   Ce n'est pas difficile — c'est SOUS-DÉTERMINÉ. Le système a {m/EVENTS:,.0f} fois
   plus d'inconnues que d'équations, et aucune méthode d'estimation ne
   fabrique de l'information qui n'est pas là.""")


rule("4. LES DEUX FAÇONS DE FRANCHIR, ET CE QU'ELLES COÛTENT")

need_draws = m / POOL
say(f"""   A) MONTER EN ORDRE jusqu'au croisement.
      Il faudrait au minimum UNE observation par coefficient, donc

        {m:,} / {POOL} = {need_draws:,.0f} tirages
        a 288 tirages par jour : {need_draws/288/365.25:,.0f} ANS d'archive.

      Et une observation par coefficient n'apprend rien : il en faudrait des
      dizaines. Multipliez par vingt.

   B) FAIRE TOMBER LA MARGE jusqu'au plus haut plafond MESURE.
      Il faudrait que la marge passe de {MARGE} % a {PTS[3][2]} %, donc un taux de
      retour de {100-PTS[3][2]:.1f} % au lieu des {100-MARGE:.1f} % mesures au §62.
      Aucune loterie ne rend {100-PTS[3][2]:.1f} %.

   C) Il n'y a pas de C. Les deux leviers sont ceux-la, et aucun n'est
      actionnable.""")


rule("5. CE QUE CE CALCUL ÉTABLIT, ET CE QU'IL NE DIT PAS")

say(f"""   ÉTABLI. Le mur de la piste A n'est pas « le plafond est trop bas » ni
   « la marge est trop haute ». C'est que les deux courbes se croisent
   DU MAUVAIS COTE de l'apprentissage : la ou le plafond devient suffisant,
   le nombre de parametres a estimer depasse le nombre d'observations d'un
   facteur {m/EVENTS:,.0f}. Le plafond et l'apprenabilite ne sont pas deux obstacles
   independants — c'est un seul obstacle, vu deux fois.

   LIMITES, et elles sont serieuses.
   1. C'est une EXTRAPOLATION de trois ordres au-dela du dernier point
      mesure. La loi tient sur quatre points et le §64 a confirme une
      prediction faite d'avance, mais rien ne garantit qu'elle tienne
      jusqu'a l'ordre {d}.
   2. Les plafonds sont d'OMNISCIENCE stricte. Le joueur reel en capte une
      fraction (§45, §59, §61) — le croisement reel serait donc encore PLUS
      loin, jamais plus proche. Le calcul est conservateur dans le bon sens.
   3. La marge de {MARGE} % suppose le barème releve (§56) et le prix de
      CHF 2 (§62). Les deux sont observes, mais la seconde source est de
      seconde main.
   4. Le comptage « evenements par coefficient » traite les {POOL} indicatrices
      d'un tirage comme independantes ; elles ne le sont pas (leur somme
      vaut {20} exactement). Le budget reel est donc PLUS PETIT que
      {EVENTS:,}, ce qui ne fait qu'aggraver la conclusion.

   Registre : inchange. h49 ne teste pas l'archive — il ajuste et extrapole.

   ({time.time() - T0:.2f} s)""")
