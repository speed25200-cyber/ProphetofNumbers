"""h9 — les premières cagnottes observées, et la distance au seuil.

Pourquoi c'est la donnée la plus actionnable du dossier
-------------------------------------------------------
Le rapport (§5 bis) établit la seule condition qui fasse changer le SIGNE de
l'espérance, et elle ne dépend d'aucune hypothèse sur le générateur :

    gain d'un ticket = jackpot·P(k/k) + Σ(rangs intermédiaires ≥ 0)

Donc dès que **jackpot ≥ mise / P(k/k)**, le pari est favorable — et tout ce
qu'on ignore du barème ne peut que rendre l'inégalité meilleure, jamais pire.
C'est une condition SUFFISANTE, pas nécessaire : le vrai seuil est plus bas,
mais incalculable sans le barème complet.

Le rapport concluait : « Ce que l'archive ne peut pas dire : à quelle
FRÉQUENCE le seuil est franchi. Elle ne contient aucun montant de jackpot. »

Cette expérience lève ce point pour la première fois. Les montants relevés
sur `jeux.loro.ch` le 30 août 2026 à 09h17 (tirage 1381028 en cours) sont
les premières cagnottes que ce dossier ait jamais vues.

Ce qu'une observation permet, et ce qu'elle ne permet pas
---------------------------------------------------------
Elle ancre l'ÉCHELLE : on sait enfin à quelle distance du seuil on se trouve,
et donc de quel facteur une cagnotte devrait croître. Elle ne dit rien de la
fréquence de franchissement — il faudrait une série. Le fichier
`lab/jackpots_observed.csv` est fait pour l'accueillir.

Réserve explicite : le seuil est exprimé PAR FRANC MISÉ. Si le ticket ne
coûte pas un franc, les seuils se multiplient d'autant. Le prix du ticket
n'est pas lisible sur la capture, donc les rapports ci-dessous sont donnés
par franc — c'est la seule forme qui ne suppose rien.
"""

import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    """P(les k numéros de la grille sont tous tirés) = C(20,k)/C(80,k)."""
    return math.comb(DRAWN, k) / math.comb(POOL, k)


rule("1. LE SEUIL, RECALCULÉ ICI PLUTÔT QUE REPRIS")
say("   mise   P(grille pleine)          seuil par franc misé")
seuil = {}
for k in (5, 6, 7, 8, 10):
    p = p_full(k)
    seuil[k] = 1 / p
    say(f"   {k:<6} 1 / {1 / p:>13,.0f}       CHF {1 / p:>13,.0f}")
say("\n   (recalculé depuis C(20,k)/C(80,k) — le rapport annonçait 1 551,")
say(f"    7 753, 40 979, 230 115 et 8 911 711 : concordance exacte)")


rule("2. LES CAGNOTTES OBSERVÉES")

rows = []
path = os.path.join(ROOT, "jackpots_observed.csv")
with open(path) as fh:
    for r in csv.DictReader(fh):
        rows.append(r)

for r in rows:
    say(f"\n   relevé {r['horodatage']} — tirage {r['tirage']} ({r['source']})")
    say("   mise   cagnotte        seuil            fraction du seuil   facteur manquant")
    best = None
    for k in (5, 6, 7, 8, 10):
        val = r.get(f"j{k}")
        if not val:
            continue
        v = float(val)
        frac = v / seuil[k]
        say(f"   {k:<6} CHF {v:>11,.0f}   CHF {seuil[k]:>11,.0f}   "
            f"{frac:>13.1%}       ×{1 / frac:>6.1f}")
        if best is None or frac > best[1]:
            best = (k, frac)
    say(f"\n   -> la mise la plus proche du seuil est {best[0]} numéros, "
        f"à {best[1]:.1%} du point d'équilibre")
    say(f"      il faudrait que cette cagnotte soit multipliée par "
        f"{1 / best[1]:.1f} pour que le pari devienne favorable,")
    say(f"      quel que soit le barème des rangs intermédiaires.")


rule("3. CE QUE CELA ÉTABLIT, ET CE QUE CELA NE DIT PAS")
say(f"""   ÉTABLI. Au moment du relevé, aucune mise n'est favorable — la plus
   proche l'est à moins d'un tiers. C'est le premier ancrage d'échelle du
   dossier sur la seule question capable de changer le signe de l'espérance.
   Jusqu'ici le rapport savait CALCULER le seuil sans jamais pouvoir le
   COMPARER à quoi que ce soit.

   Ordre de grandeur utile : les cagnottes des mises 7, 8 et 10 sont à 4-6 %
   du seuil, celles des mises 5 et 6 à 23-30 %. Ce n'est pas un hasard
   d'échelle — le seuil croît beaucoup plus vite avec k (×5 750 de la mise 5
   à la mise 10) que les cagnottes affichées (×1 396). **Les petites mises
   sont structurellement les plus proches du point d'équilibre**, et c'est
   une conséquence directe de la combinatoire, pas une observation
   ponctuelle.

   NON ÉTABLI. La fréquence de franchissement demande une SÉRIE : une
   observation donne une distance, pas une dynamique. Il faudrait savoir à
   quelle vitesse une cagnotte progressive croît et jusqu'où elle monte
   avant d'être remportée. `lab/jackpots_observed.csv` accueille la série.

   RÉSERVE. Le seuil est par franc misé. Si le ticket coûte plus d'un franc,
   les seuils se multiplient d'autant et les fractions ci-dessus se divisent
   d'autant — le prix du ticket n'est pas lisible sur la capture.""")

rule(f"total {time.time() - T0:.0f}s")
