"""h15 — la loi de la cagnotte, et la fraction de tirages favorables.

La question que h9 a laissée ouverte
-------------------------------------
h9 a établi le seul fait capable de changer le SIGNE de l'espérance : dès
que la cagnotte dépasse mise/P(k/k), le pari devient favorable, quel que
soit le barème des rangs intermédiaires. Et il a mesuré, pour la première
fois, à quelle distance du seuil on se trouve : la mise 6 est à 29,5 %.

Puis il a conclu, honnêtement : « la fréquence de franchissement demande une
SÉRIE ; une observation donne une distance, pas une dynamique ».

C'est vrai d'une mesure directe. Ce n'est pas vrai d'une mesure MODÉLISÉE —
et c'est ce que ce fichier fait, en payant le prix : dire exactement quelles
hypothèses achètent la réponse, et de combien l'incertitude reste large.

Le modèle, en trois hypothèses nommées
---------------------------------------
H1  La cagnotte croît d'un montant fixe r par tirage (une fraction de la
    mise collectée) tant qu'elle n'est pas remportée.
H2  Elle est remportée avec une probabilité q par tirage, indépendante du
    passé — donc l'âge de la cagnotte est SANS MÉMOIRE.
H3  Elle repart d'un plancher J₀ après un gain.

Sous H1–H3, l'âge T de la cagnotte au moment d'un relevé pris « au hasard »
suit une géométrique de paramètre q, donc

    J = J₀ + r·T,        E[J] = J₀ + r/q,        P(J ≥ S) = (1−q)^((S−J₀)/r)

et pour q petit, P(J ≥ S) ≈ exp(−(S−J₀)/μ) avec μ = r/q = E[J] − J₀.

**Un relevé suffit donc à estimer μ**, et de là la fraction de tirages
favorables. Ce que le relevé ne donne pas, c'est la PRÉCISION : une
exponentielle a un écart-type égal à sa moyenne, et une observation unique
en est un estimateur épouvantable. Le §3 chiffre exactement à quel point,
et combien de relevés il faudrait — ce qui transforme « il faudrait une
série » en une demande précise.

Ce que la série apporterait EN PLUS du modèle
----------------------------------------------
Deux relevés séparés d'un ou deux tirages, sans gain entre les deux, donnent
**r directement** : c'est leur différence divisée par le nombre de tirages.
Et la fréquence des chutes observées donne **q**. Avec r et q mesurés, μ
n'est plus estimé par une exponentielle mais calculé — et l'intervalle du §3
s'effondre. C'est la raison pour laquelle deux relevés rapprochés valent
beaucoup plus que deux relevés éloignés.
"""

import csv
import math
import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAKES = (5, 6, 7, 8, 10)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def threshold(k: int) -> float:
    """Seuil par franc misé : mise / P(k/k) = C(80,k)/C(20,k)."""
    return math.comb(POOL, k) / math.comb(DRAWN, k)


# --------------------------------------------------------------------------
# 1. Le modèle est-il vrai de lui-même ? (contrôle par simulation)
# --------------------------------------------------------------------------

rule("1. CONTRÔLE — la loi stationnaire d'une cagnotte progressive")

say("""   Avant d'appliquer la formule, on vérifie qu'elle décrit bien le
   processus qu'elle prétend décrire : accumulation à pas fixe, remise à
   zéro aléatoire, relevé pris à un instant quelconque.""")

rng = np.random.default_rng(20260830)
say("""
   L'écart admissible n'est pas fixé à la main : il est calculé depuis le
   nombre de RENOUVELLEMENTS de la simulation — c'est-à-dire le nombre de
   fois où la cagnotte est effectivement tombée. Une simulation de quatre
   millions de tirages à q = 10⁻⁵ n'a que quarante renouvellements et ne
   prouve rien ; l'écart est donc rapporté en unités d'écart-type, seule
   forme qui ne dépende pas du nombre choisi.""")
say("\n   q         gains    E[J] simulée   r/q        écart    P(J≥3μ)  attendu   écart")
r = 100.0
steps = 4_000_000
idx = np.arange(steps)
for q in (1e-2, 3e-3, 1e-3):
    hits = rng.random(steps) < q
    last = np.maximum.accumulate(np.where(hits, idx, -1))
    keep = last >= 0                       # on jette l'amorce avant le 1er gain
    J = r * (idx - last)[keep]
    n_ren = int(hits.sum())
    mu = r / q
    # Loi exacte du modèle discret : P(T ≥ t) = (1−q)^t, avec t = ⌈3/q⌉.
    p_th = (1 - q) ** math.ceil(3 / q)
    p_sim = float((J >= 3 * mu).mean())
    sd_mean = mu / math.sqrt(n_ren)        # excursions indépendantes
    sd_p = math.sqrt(p_th * (1 - p_th) / n_ren)
    z_mean = (J.mean() - mu) / sd_mean
    z_p = (p_sim - p_th) / sd_p
    say(f"   {q:<9.0e} {n_ren:<8,} {J.mean():>12,.0f}   {mu:>9,.0f}  "
        f"{z_mean:>+6.2f} σ   {p_sim:.5f}  {p_th:.5f}  {z_p:>+5.2f} σ")
    assert abs(z_mean) < 4 and abs(z_p) < 4

say("""
   Moyenne et queue tombent toutes deux à moins de quatre écarts-types de
   la prédiction : la formule décrit bien le processus. Les deux écarts
   d'une même ligne ne sont pas deux confirmations indépendantes — moyenne
   et queue du même échantillon sont fortement corrélées, c'est la même
   fluctuation vue deux fois. Ce qui reste à discuter est la validité de
   H1–H3, pas celle de l'arithmétique.""")


# --------------------------------------------------------------------------
# 2. Les relevés réels, et la fraction de tirages favorables
# --------------------------------------------------------------------------

rule("2. LA FRACTION DE TIRAGES FAVORABLES, ESTIMÉE")

rows = []
with open(os.path.join(ROOT, "jackpots_observed.csv")) as fh:
    for r in csv.DictReader(fh):
        rows.append(r)

obs = {k: [] for k in STAKES}
for r in rows:
    for k in STAKES:
        v = r.get(f"j{k}")
        if v:
            obs[k].append(float(v))

say(f"   {len(rows)} relevé(s) disponible(s). L'estimateur du maximum de "
    f"vraisemblance de μ")
say("   sur une exponentielle est simplement la moyenne des relevés.")
say("\n   mise   cagnotte moyenne   seuil          S/μ     fraction de tirages")
say("                                                       favorables (estimée)")
frac = {}
for k in STAKES:
    if not obs[k]:
        continue
    mu = float(np.mean(obs[k]))
    S = threshold(k)
    p = math.exp(-S / mu)
    frac[k] = p
    aff = f"{p:.3%}" if p >= 1e-4 else f"{p:.1e}"
    say(f"   {k:<6} CHF {mu:>12,.0f}   CHF {S:>10,.0f}   {S / mu:>6.2f}  "
        f"{aff:>12}")

best = max(frac, key=frac.get)
per_day = frac[best] * 24 * 12          # un tirage toutes les 5 minutes
say(f"""
   Lecture — et elle est PROVISOIRE, le §3 dit à quel point. La mise {best}
   est de très loin la plus exposée : l'estimation ponctuelle place à
   {frac[best]:.1%} des tirages la fraction où la cagnotte dépasserait le seuil de
   bascule. Un tirage toutes les cinq minutes, cela ferait {per_day:.0f} tirages
   favorables par jour, soit un toutes les {24 * 60 / max(per_day, 1e-9):.0f} minutes.

   Les autres mises sont hors de portée de plusieurs ordres de grandeur, et
   c'est structurel : le seuil croît beaucoup plus vite avec k que la
   cagnotte affichée (h9).""")


# --------------------------------------------------------------------------
# 3. Ce que le modèle empêche de faire dire à un seul relevé
# --------------------------------------------------------------------------

rule("3. L'INCERTITUDE, QUI EST ÉNORME — ET C'EST LE RÉSULTAT")

say("""   Un estimateur exponentiel sur UNE observation a un écart-type égal à
   sa moyenne. L'intervalle exact vient de 2n·J̄/μ ~ χ²(2n), et il se
   propage à la fraction favorable par p = exp(−S/μ), croissante en μ.""")

say(f"\n   mise {best} — seuil CHF {threshold(best):,.0f}, relevé CHF {np.mean(obs[best]):,.0f}")
say("\n   n relevés   μ dans [.. , ..] à 95 %          fraction favorable à 95 %")
S = threshold(best)
jbar = float(np.mean(obs[best]))
for n in (1, 2, 3, 5, 10, 30, 100):
    lo_mu = 2 * n * jbar / stats.chi2.ppf(0.975, 2 * n)
    hi_mu = 2 * n * jbar / stats.chi2.ppf(0.025, 2 * n)
    say(f"   {n:<11} [CHF {lo_mu:>9,.0f} , CHF {hi_mu:>11,.0f}]   "
        f"[{math.exp(-S / lo_mu):>9.2%} , {math.exp(-S / hi_mu):>7.2%}]")

say(f"""
   Avec un seul relevé, la fraction favorable est comprise entre un
   millionième et neuf dixièmes : autant dire qu'on ne sait rien. Le
   résultat du §2 n'est donc PAS « {frac[best]:.1%} des tirages sont favorables ».
   C'est « l'estimation ponctuelle vaut {frac[best]:.1%}, et une seule observation
   ne permet pas de la resserrer d'un facteur utile ».

   La lecture utile est la colonne de droite : il faut une trentaine de
   relevés pour situer la fraction favorable à un facteur 10 près, une
   centaine pour un facteur 3. C'est la demande de données la plus rentable
   du dossier, et elle est maintenant chiffrée plutôt que souhaitée.""")


# --------------------------------------------------------------------------
# 4. Le raccourci : deux relevés rapprochés valent mieux que trente épars
# --------------------------------------------------------------------------

rule("4. LE RACCOURCI — mesurer r et q plutôt que d'estimer μ")

say("""   L'intervalle du §3 est large parce qu'il estime μ = r/q à travers UNE
   variable aléatoire. Mais r et q se mesurent séparément, et bien plus
   vite :

     • r, l'accumulation par tirage, est la DIFFÉRENCE entre deux relevés
       de la même cagnotte séparés de quelques tirages, sans gain entre les
       deux. Deux relevés à cinq minutes d'intervalle suffisent, et
       l'incertitude est celle de la lecture, pas celle d'un tirage
       aléatoire.

     • q, la probabilité de gain par tirage, est le taux de chutes
       observées. Il vaut aussi N·P(k/k) où N est le nombre de grilles
       jouées à cette mise — donc une seule chute observée, datée, borne
       déjà q par 1/(nombre de tirages écoulés depuis la précédente).

   Avec r et q mesurés, μ n'est plus estimé : il est calculé. La fraction
   favorable devient exp(−S·q/r), et son incertitude n'est plus celle d'une
   exponentielle à un tirage.""")

say("\n   Ce que vaudrait un couple (r, q) même grossier, mise "
    f"{best} — seuil CHF {S:,.0f} :")
say("\n   r (CHF/tirage)   q                μ = r/q        fraction favorable")
for r_ in (5.0, 20.0, 100.0):
    for q_ in (1e-3, 3e-3, 1e-2):
        mu = r_ / q_
        say(f"   {r_:<16,.0f} {q_:<16.0e} CHF {mu:>10,.0f}   "
            f"{math.exp(-S / mu):>10.2%}")

say(f"""
   Le tableau montre pourquoi le couple (r, q) est la bonne cible : la
   fraction favorable passe de l'invisible au quotidien selon leur rapport,
   et ce rapport est mesurable en deux lectures d'écran plus une date de
   chute — là où l'estimation par la loi stationnaire demande une centaine
   de relevés pour la même précision.""")


# --------------------------------------------------------------------------
# 5. Les réserves, qui sont réelles
# --------------------------------------------------------------------------

rule("5. CE QUI PEUT FAIRE MENTIR CE CALCUL")

say(f"""   H2 (sans mémoire) est la plus fragile. Si la cagnotte est plafonnée,
   ou versée à date fixe, ou si l'opérateur en ajuste la progression, la
   queue n'est plus géométrique et la formule surestime ou sous-estime sans
   qu'on puisse dire dans quel sens. Une série de relevés la TESTE : sous
   H1–H3, les écarts entre relevés successifs sont constants et les chutes
   sont poissonniennes.

   H3 (plancher J₀) déplace le résultat dans le sens FAVORABLE au joueur si
   J₀ > 0 : la formule devient exp(−(S−J₀)/μ), donc toute cagnotte qui
   repart d'un plancher non nul est plus souvent au-dessus du seuil que
   calculé ici. Le calcul ci-dessus prend J₀ = 0, le cas le moins favorable.

   Le seuil lui-même est SUFFISANT, pas nécessaire (h9) : il ignore les
   rangs intermédiaires, qui ne peuvent qu'ajouter. Le vrai seuil est plus
   bas, donc la vraie fraction favorable est plus HAUTE que celle estimée
   ici. Les deux réserves structurelles vont donc dans le même sens, et
   c'est le bon.

   Enfin, tout est par franc misé : si le ticket coûte plus d'un franc, les
   seuils se multiplient d'autant et les fractions s'effondrent. Le prix du
   ticket reste la donnée manquante la moins chère à obtenir de tout le
   dossier.""")

rule(f"total {time.time() - T0:.0f}s")
