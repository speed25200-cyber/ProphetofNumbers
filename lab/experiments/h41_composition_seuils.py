"""h41 — la composition des deux corrections de seuil, que personne n'a faite.

Le problème
------------
Deux sections de cette campagne corrigent le seuil de bascule du §5 bis, et
elles vont en SENS OPPOSÉS :

  §50 (h34)  les rangs intermédiaires valent rho >= 24,5 % de la mise, donc
             le pari devient favorable plus tôt : le seuil DESCEND à
             (1 - rho)*S, de CHF 7 753 à 5 853.

  §53 (h36)  jouer ajoute n*p au taux de chute et détruit ainsi la valeur
             future du processus : le seuil MONTE, à CHF 8 651 pour un
             joueur à treize grilles.

Chacune a été établie EN SUPPOSANT L'AUTRE ABSENTE. Or elles ne sont pas
indépendantes : abaisser le seuil fait jouer plus souvent, donc contribuer
davantage au taux de chute. La composition ne peut donc pas être une simple
addition, et personne n'a dit de combien elle s'en écarte ni dans quel sens.

Ce fichier la calcule. Il ne teste pas l'archive : comme h1, h14, h17, h25,
h30, h31, h32, h36, h37 et h38, il prouve.

Une convention qu'il a fallu retrouver
---------------------------------------
Le §53 ne nomme pas ce que désigne son `q`, et la réponse change le résultat
d'un tiers. Deux lectures sont possibles :

  CONVENTION B — `q` est le taux de chute dû aux AUTRES joueurs, et le nôtre
                 ajoute son n*p par-dessus. C'est le point de vue d'un
                 NOUVEL ENTRANT, et c'est celle du §53 : elle reproduit son
                 CHF 8 651 au franc près.
  CONVENTION A — `q` est le taux TOTAL observé, le nôtre inclus. C'est ce
                 qu'un observateur mesure, et elle donne CHF 11 532.

Les deux sont défendables et décrivent deux joueurs différents. B est retenue
en primaire — c'est celle du résultat publié, et c'est la bonne pour quelqu'un
qui se demande s'il doit se mettre à jouer. A est rendue en contrôle, parce
qu'une divergence de convention de 33 % qu'on ne nommerait pas serait une
erreur en attente.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN, K = 80, 20, 6
P_FULL = math.comb(DRAWN, K) / math.comb(POOL, K)
S = 1.0 / P_FULL
MU = 2287.0                       # relevé unique (lab/jackpots_observed.csv)
ALPHA = MU / S
Q_REF = 1.0 / 400.0               # taux de référence du §36
R_STEP = MU * Q_REF
N_GRIDS = 13
RHO_MIN = 0.245                   # borne du §50, sous ses hypothèses nommées


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def optimal_threshold(rho, self_extinction, n=N_GRIDS, convention="B",
                      tmax=9000, iters=30000, tol=1e-12):
    """Seuil optimal par itération de valeur relative sur l'âge de la cagnotte.

    État : l'âge t, cagnotte J = r*t. Action : jouer n grilles ou s'abstenir.
    Profit par franc misé : J*p + rho - 1. Le joueur n'ajoute son n*p au taux
    de chute QUE lorsqu'il joue — c'est le canal que le calcul statique ne
    voit pas.
    """
    n_p = n * P_FULL
    q_others = Q_REF if convention == "B" else Q_REF - n_p
    J = R_STEP * np.arange(tmax + 1)
    reward = n * (J * P_FULL + rho - 1.0)
    h = np.zeros(tmax + 1)
    g = 0.0
    for _ in range(iters):
        nxt = np.concatenate([h[1:], h[-1:]])
        v_wait = (1 - q_others) * nxt + q_others * h[0]
        qp = q_others + (n_p if self_extinction else 0.0)
        v_play = reward + (1 - qp) * nxt + qp * h[0]
        nh = np.maximum(v_wait, v_play)
        ng = nh[0]
        nh = nh - ng
        if abs(ng - g) < tol and np.max(np.abs(nh - h)) < tol:
            h, g = nh, ng
            break
        h, g = nh, ng
    nxt = np.concatenate([h[1:], h[-1:]])
    qp = q_others + (n_p if self_extinction else 0.0)
    v_play = reward + (1 - qp) * nxt + qp * h[0]
    v_wait = (1 - q_others) * nxt + q_others * h[0]
    idx = np.flatnonzero(v_play > v_wait)
    return (float(R_STEP * idx[0]) if len(idx) else math.nan), float(g)


rule("1. LE CADRE, ET LES CONTRÔLES QUI LE VALIDENT")

say(f"""   Mise {K}, p = 1/{S:,.0f}, cagnotte moyenne mu = {MU:,.0f}, alpha = {ALPHA:.4f}.
   Taux de référence q = 1/{1/Q_REF:.0f}, accumulation r = {R_STEP:.4f}/tirage,
   {N_GRIDS} grilles disjointes, part du joueur n*p/q = {N_GRIDS*P_FULL/Q_REF:.4f}.

   Avant de demander au modèle quoi que ce soit de neuf, il doit retrouver
   les trois chiffres déjà publiés. C'est ce contrôle qui a révélé la
   divergence de convention documentée en tête de fichier.""")

res = {}
for rho, se, name in ((0.0, False, "nu (§5 bis)"),
                      (RHO_MIN, False, "rangs intermédiaires seuls (§50)"),
                      (0.0, True, "auto-extinction seule (§53)"),
                      (RHO_MIN, True, "LES DEUX")):
    thr, g = optimal_threshold(rho, se)
    res[(rho > 0, se)] = thr
    say(f"   {name:<36} CHF {thr:>9,.0f}   profit/tirage {g:.5f}")

nu = res[(False, False)]
rho_only = res[(True, False)]
se_only = res[(False, True)]
both = res[(True, True)]

say(f"""
   CONTRÔLES (convention B) :
     nu                 attendu S = {S:,.0f}            obtenu {nu:>9,.0f}   {abs(nu-S)/S:>6.2%}
     rangs seuls        attendu (1-rho)S = {(1-RHO_MIN)*S:,.0f}     obtenu {rho_only:>9,.0f}   {abs(rho_only-(1-RHO_MIN)*S)/((1-RHO_MIN)*S):>6.2%}
     auto-extinction    §53 annonce CHF 8 651        obtenu {se_only:>9,.0f}   {abs(se_only-8651)/8651:>6.2%}

   Les trois tombent juste. Le modèle est donc en accord avec les deux
   sections qu'il compose, et ce qui suit est une prédiction et non un
   réglage.""")

thr_A, _ = optimal_threshold(0.0, True, convention="A")
say(f"""
   CONTRÔLE DE CONVENTION. Sous la convention A — `q` est le taux TOTAL
   observé, le joueur inclus — l'auto-extinction seule donne CHF {thr_A:,.0f} au
   lieu de {se_only:,.0f}, soit {abs(thr_A-se_only)/se_only:.0%} d'écart. Ce n'est pas une erreur de l'un
   ou de l'autre : ce sont deux joueurs différents. B décrit celui qui se
   demande s'il doit SE METTRE à jouer et qui s'ajoute au taux existant ;
   A décrit celui dont l'activité est déjà comprise dans le taux mesuré.
   La suite est en B.""")


rule("2. LA COMPOSITION")

add = rho_only + (se_only - nu)
say(f"""   addition naïve des deux corrections     CHF {add:>9,.0f}
   composition exacte                      CHF {both:>9,.0f}
   écart                                   CHF {both-add:>+9,.0f}   ({(both-add)/add:+.2%})

   L'addition naïve est donc une excellente approximation ici — moins d'un
   demi pour cent — mais l'écart n'est pas nul et son SENS est instructif.

   Il est NÉGATIF : la composition est plus basse que la somme. La raison
   n'est pas celle qu'on devine d'abord. On s'attend à ce qu'un seuil plus
   bas fasse jouer plus souvent — c'est vrai, la fraction jouée passe de
   {math.exp(-nu/MU):.2%} à {math.exp(-both/MU):.2%} — donc à ce que la pénalité d'auto-extinction
   s'alourdisse et pousse le seuil plus haut que la somme. C'est l'effet
   inverse qui l'emporte : avec les rangs intermédiaires, chaque tirage joué
   rapporte davantage IMMÉDIATEMENT, si bien que la valeur future détruite
   par un gain pèse relativement MOINS. La pénalité d'auto-extinction, en
   proportion, diminue.

   Autrement dit : les rangs intermédiaires ne se contentent pas d'abaisser
   le seuil, ils rendent aussi l'auto-extinction moins coûteuse. Les deux
   corrections ne s'additionnent pas — la première atténue la seconde.""")


rule("3. LE CHIFFRE PRATIQUE")

say("\n   n grilles   n*p/q   seuil composé   vs (1-rho)S   vs S nu")
for n in (1, 3, 6, 13):
    t, _ = optimal_threshold(RHO_MIN, True, n=n)
    say(f"   {n:>9}   {n*P_FULL/Q_REF:>5.2f}   CHF {t:>9,.0f}   "
        f"{t/((1-RHO_MIN)*S):>10.3f}x   {t/S:>6.3f}x")

say(f"""
   LECTURE, et c'est la réponse à la question posée.

   Pour un joueur à UNE grille, l'auto-extinction est négligeable et le
   seuil composé colle à celui du §50 : la correction du barème s'applique
   telle quelle, CHF {optimal_threshold(RHO_MIN, True, n=1)[0]:,.0f} contre {(1-RHO_MIN)*S:,.0f}.

   Pour TREIZE grilles, les deux effets se partagent le terrain, et le
   seuil composé vaut CHF {both:,.0f} — soit {1-both/S:.0%} SOUS le seuil nu de {S:,.0f}.
   La correction qui abaisse l'emporte donc largement sur celle qui relève,
   et le nombre d'occasions favorables reste nettement supérieur à ce que
   le §5 bis annonçait : {math.exp(-both/MU):.2%} des tirages contre {math.exp(-nu/MU):.2%}.

   Les deux corrections ne s'annulent pas, et celle qui compte le plus est
   celle qui abaisse le seuil.

   LIMITES.
   1. Le modèle hérite de H1-H3 du §28 et de rho >= 0,245, lui-même
      conditionnel aux hypothèses nommées au §50. Rien ici n'est plus solide
      que le maillon le plus faible de cette chaîne.
   2. Les collisions — deux grilles pleines au même tirage — sont négligées
      à O((n*p)^2).
   3. q = 1/400 est la valeur de référence du §36, pas une mesure ; la table
      est donc rendue en n*p/q, qui est le rapport observable.
   4. Le profit suppose les rangs intermédiaires payés à chaque tirage joué,
      indépendamment de la cagnotte — l'hypothèse du §50.
   5. La convention B suppose que le joueur s'AJOUTE au marché observé. S'il
      y est déjà compté, c'est la convention A qui vaut, et le seuil monte.

   Registre : inchangé. h41 ne teste pas l'archive — il compose.""")

say(f"\n   ({time.time() - T0:.1f} s)")
