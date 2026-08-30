"""La prédiction elle-même : les numéros du prochain tirage.

Ce fichier fait ce que tout le dossier a servi à cadrer — il sort vingt
numéros. Il les sort avec l'appareil complet : les 26 têtes de l'essaim,
leurs poids AdaHedge appris en marche avant sur 70 560 tirages, et le champ
qu'elles opposent au tirage qui n'a pas encore eu lieu.

Et il dit, dans le même souffle, ce que ces vingt numéros valent — parce
qu'une prédiction sans son espérance n'est pas une prédiction, c'est une
liste.

Ce que le dossier a établi, et qui s'applique ici sans exception
----------------------------------------------------------------
Sous un tirage uniforme de 20 parmi 80, le nombre de bons numéros d'une
sélection de k numéros suit la même loi hypergéométrique QUELLE QUE SOIT la
sélection. L'espérance vaut k/4, exactement, pour ces vingt numéros comme
pour n'importe quels vingt autres.

Trente-deux voies d'investigation, 3 328 tests consignés, zéro significatif
après correction de multiplicité. Cinq familles de générateurs couvertes sur
les tirages ordonnés, chacune avec ses témoins : aucun état retrouvé.

Ces vingt numéros ne sont donc pas « les bons numéros du prochain tirage ».
Ce sont les vingt numéros que l'appareil le mieux calibré du dossier propose,
et leur espérance de hits est exactement celle de vingt numéros pris au
hasard. Le dire est le seul usage honnête qu'on puisse en faire.

Ce sur quoi le dossier a trouvé prise
--------------------------------------
Deux choses, et aucune ne concerne le choix des numéros :

  la GÉOMÉTRIE du portefeuille (h13, h17) — n grilles disjointes touchent le
  rang plein n fois plus souvent que n grilles identiques, à coût et à
  espérance égaux, et font croître le capital n fois plus vite ;

  le MOMENT (h15, h16) — ne miser qu'au-dessus du seuil de bascule de la
  cagnotte rapporte μ/S par franc, soit +29,5 % au dernier relevé.

C'est pourquoi ce fichier ne rend pas seulement vingt numéros mais aussi le
portefeuille disjoint qui les met en œuvre.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab
import swarm_py as sp

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.abspath(__file__))


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    return math.comb(DRAWN, k) / math.comb(POOL, k)


# --------------------------------------------------------------------------
# 1. Les données, jusqu'au dernier tirage connu
# --------------------------------------------------------------------------

rule("1. CE SUR QUOI LA PRÉDICTION S'APPUIE")

a = lab.load()
masks = [a.mask]
recent = []
path = os.path.join(ROOT, "draws_ordered.csv")
if os.path.exists(path):
    with open(path) as fh:
        for row in csv.DictReader(fh):
            nums = [int(row[f"o{i}"]) for i in range(1, DRAWN + 1)]
            recent.append((int(row["id"]), sorted(nums)))
recent.sort()
if recent:
    extra = np.zeros((len(recent), POOL), bool)
    for i, (_, nums) in enumerate(recent):
        for x in nums:
            extra[i, x - 1] = True
    masks.append(extra)
mask = np.concatenate(masks, axis=0)
# Les numéros de tirage, alignés sur `mask` : c'est eux qui portent le temps.
# Un trou entre deux tirages absorbés fait d'abord décroître les têtes du
# temps manquant (swarm_py, advance) — par tirage ÉCOULÉ, pas absorbé.
ids = np.concatenate([a.ids, np.array([d for d, _ in recent], np.int64)]) \
    if recent else a.ids

say(f"   archive          {len(a):,} tirages, jusqu'au {int(a.ids.max()):,}")
if recent:
    say(f"   tirages récents  {len(recent)} relevés à la main : "
        f"{', '.join(str(d) for d, _ in recent)}")
    say(f"   NOTE : {recent[0][0] - int(a.ids.max()) - 1} tirages manquent entre les deux. "
        f"Les têtes décroissent")
    say("          du temps ÉCOULÉ (h23) : le trou éteint la mémoire courte au lieu")
    say("          de la geler à trois jours d'âge. Ce qu'il coûte malgré cela — ")
    say("          l'information des tirages non vus — est mesuré dans")
    say("          experiments/h23_trou_recence.py, et rien d'autre n'est affirmé.")
say(f"   total            {len(mask):,} tirages absorbés")
next_id = (recent[-1][0] if recent else int(a.ids.max())) + 1
say(f"   prédiction pour  le tirage {next_id:,} (le suivant du dernier connu)")


# --------------------------------------------------------------------------
# 2. Ce que l'essaim a valu, mesuré
# --------------------------------------------------------------------------

rule("2. CE QUE L'ESSAIM A VALU — mesuré, pas annoncé")

say("   Rejeu en marche avant sur les 20 000 derniers tirages : chaque")
say("   prédiction est notée sur le tirage qu'elle n'a pas encore vu.")
res = sp.run(mask[-20_000:], keep_picks=False, ids=ids[-20_000:])
ov = res["ov_ens"]
z = sp.z_of(ov)
say(f"\n   recouvrement moyen de l'ensemble : {ov.mean():.4f} sur {len(ov):,} tirages")
say(f"   espérance exacte sous l'invariance : {DRAWN * DRAWN / POOL:.4f}")
say(f"   écart standardisé : {z:+.2f} σ")
say(f"   meilleur tirage : {ov.max()}/20   pire : {ov.min()}/20")
say(f"""
   Lecture. L'essaim fait jeu égal avec le hasard, à {abs(z):.1f} σ près — et il ne
   peut rien faire d'autre : l'espérance de hits est la même pour toute
   sélection. Ce chiffre n'est pas un échec de l'essaim, c'est la mesure du
   théorème.""")


# --------------------------------------------------------------------------
# 3. La prédiction
# --------------------------------------------------------------------------

rule(f"3. LES VINGT NUMÉROS — tirage {next_id:,}")

pred = sp.predict_next(mask, ids=ids)
top20 = pred["top20"]
ranking = pred["ranking"]

say("   Les vingt numéros que l'essaim place en tête :\n")
for i in range(0, DRAWN, 10):
    say("      " + "  ".join(f"{n:>2}" for n in top20[i:i + 10]))

say(f"\n   Classement complet, du plus au moins soutenu :")
for i in range(0, POOL, 20):
    say("      " + " ".join(f"{n:>2}" for n in ranking[i:i + 20]))

pmf = [math.comb(DRAWN, h) * math.comb(POOL - DRAWN, DRAWN - h) / math.comb(POOL, DRAWN)
       for h in range(DRAWN + 1)]
mean = sum(h * p for h, p in enumerate(pmf))
say(f"""
   Ce que cette sélection vaut, exactement :
     espérance de bons numéros   {mean:.4f} sur 20
     et pour n'importe quels vingt autres numéros, {mean:.4f} également.
     P(au moins 10 bons)         {sum(pmf[10:]):.4%}
     P(les 20)                   1 sur {1 / pmf[20]:,.0f}""")


# --------------------------------------------------------------------------
# 4. Le portefeuille — le seul endroit où le choix change quelque chose
# --------------------------------------------------------------------------

rule("4. LE PORTEFEUILLE — ce qui, lui, change réellement les chances")


def portfolio(k: int, n: int, order: list) -> list:
    """n grilles de k numéros : couverture équilibrée, recouvrement minimal.

    Reprend la construction de h13 : la couverture décide d'abord, le
    recouvrement induit ensuite, et le classement de l'essaim ne sert que de
    départage — puisqu'il ne déplace pas l'espérance, il ne peut servir qu'à
    cela, et c'est déjà ce qu'il fait de mieux.
    """
    rank = {x: i for i, x in enumerate(order)}
    grids, cover = [], {x: 0 for x in order}
    for _ in range(n):
        g = set()
        for _ in range(k):
            best, key_best = None, None
            for x in order:
                if x in g:
                    continue
                trial = g | {x}
                ov = max((len(gg & trial) for gg in grids), default=0)
                key = (cover[x], ov, rank[x])
                if key_best is None or key < key_best:
                    key_best, best = key, x
            g.add(best)
        for x in g:
            cover[x] += 1
        grids.append(g)
    return [sorted(g) for g in grids]


for k in (6, 10):
    n = POOL // k
    pf = portfolio(k, n, ranking)
    oms = [len(set(pf[i]) & set(pf[j]))
           for i in range(n) for j in range(i + 1, n)]
    p1 = p_full(k)
    say(f"\n   {n} grilles DISJOINTES de {k} numéros "
        f"(recouvrement max {max(oms)}, seuil neutre {k * k / POOL:.2f}) :")
    for i, g in enumerate(pf):
        say(f"      {i + 1:>2}. " + "  ".join(f"{x:>2}" for x in g))
    say(f"      une grille pleine : 1 sur {1 / p1:,.0f}")
    say(f"      AU MOINS une des {n} : 1 sur {1 / (n * p1):,.0f}   "
        f"soit ×{n} — exactement le facteur de h13")

say(f"""
   Et c'est tout ce que le choix des numéros peut faire. Le facteur {POOL // 6}
   ci-dessus ne vient pas d'une meilleure prédiction : il vient de ce que
   treize grilles disjointes offrent treize occasions distinctes là où treize
   grilles quelconques s'en partagent moins. L'espérance de gain, elle, est
   identique — sauf sur un rang partagé, où la disjonction la fait monter
   (h13 §4).""")


# --------------------------------------------------------------------------
# 5. Quand jouer, et combien
# --------------------------------------------------------------------------

rule("5. QUAND JOUER, ET COMBIEN — les deux vrais leviers")

S6 = 1 / p_full(6)
say(f"""   MOMENT (h15, h16). Le pari devient favorable dès que la cagnotte de la
   mise 6 dépasse CHF {S6:,.0f} par franc misé — condition suffisante, qui ne
   suppose rien du barème des rangs intermédiaires. Au dernier relevé
   (CHF 2 287), le gain conditionnel disponible une fois ce seuil franchi
   vaut +29,5 % par franc, et le seuil est atteint sur environ 3,4 % des
   tirages. Ne pas jouer en dessous : c'est la politique optimale, et h18
   démontre qu'attendre PLUS que le seuil est également une erreur.

   TAILLE (h17). À ce seuil, la fraction de Kelly sur treize grilles
   disjointes vaut 3,8·10⁻⁴ du capital. Un tour de treize grilles à CHF 1
   correspond donc à un capital de CHF 34 000. En dessous, on mise au-dessus
   de Kelly, et la croissance devient négative dès trois fois Kelly — le pari
   reste favorable en espérance et devient perdant en croissance.

   Ces deux leviers sont les seuls que trente-deux voies d'investigation
   aient trouvés. Les vingt numéros du §3 n'en sont pas un.""")

rule(f"total {time.time() - T0:.0f}s")
