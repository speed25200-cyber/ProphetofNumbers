"""h18 — la valeur de VOIR, et le théorème qui unifie tout le dossier.

L'énoncé qui manquait
----------------------
Le dossier a exploré deux voies apparemment sans rapport. La première :
choisir les numéros, fermée par le théorème d'invariance. La seconde :
choisir le MOMENT, ouverte par h16, avec un gain conditionnel de +29,5 %.

Elles ne sont pas sans rapport. Elles sont deux cas d'un même énoncé, et le
formuler explique d'un coup pourquoi l'une est fermée et l'autre ouverte.

    THÉORÈME DE LA VALEUR DE VOIR. Soit X une quantité OBSERVABLE avant la
    mise et qui multiplie le gain, et R₀ le retour par franc misé à X = 1.
    Une politique de jeu est un ensemble A de valeurs de X sur lesquelles on
    mise. Son profit par tirage vaut

        E[(R₀·X − 1)·1{X ∈ A}]

    qui est maximisé, terme à terme, par A = {x : R₀·x > 1}. **La politique
    optimale est donc « miser si et seulement si le pari est favorable »**,
    quelle que soit la loi de X. Et la valeur de voir X plutôt que de miser
    à l'aveugle vaut

        V = E[(R₀·X − 1)⁺] − (R₀·E[X] − 1)⁺

    c'est-à-dire exactement l'écart de Jensen de la fonction convexe
    x ↦ (R₀x − 1)⁺.

Pourquoi cela referme l'invariance et ouvre le reste
-----------------------------------------------------
Le théorème d'invariance dit que la loi du nombre de bons numéros ne dépend
pas de la grille choisie. En langage de ce théorème-ci : **choisir des
numéros ne produit aucun X**. La variable est dégénérée, l'écart de Jensen
est nul, et il n'y a rien à voir — littéralement.

La cagnotte, elle, est un X : elle varie, elle est affichée, elle multiplie
le gain. Le boost aussi, SI son tirage est publié avant la clôture des
mises. Ces deux-là ont un écart de Jensen strictement positif, et c'est la
seule raison pour laquelle ils rapportent quelque chose.

Le dossier cherchait donc au mauvais endroit pendant trente voies : la
question n'était jamais « quels numéros » mais « quelles variables sont
visibles avant la clôture ».
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = 80, 20
DRAWS_PER_DAY = 24 * 12


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    return math.comb(DRAWN, k) / math.comb(POOL, k)


K = 6
P1 = p_full(K)
S = 1 / P1
ALPHA = 2287 / S


# --------------------------------------------------------------------------
# 1. Le théorème, et sa vérification
# --------------------------------------------------------------------------

rule("1. LE THÉORÈME — la politique optimale est « miser si c'est favorable »")

say("""   Énoncé : pour X observable avant la mise et multipliant le gain, le
   profit par tirage d'une politique A vaut E[(R₀X − 1)·1{X ∈ A}], donc la
   politique optimale est A = {x : R₀x > 1}.

   La démonstration tient en une ligne — chaque valeur de x contribue
   indépendamment, on garde celles dont la contribution est positive — mais
   elle mérite d'être vérifiée numériquement, parce que l'intuition suggère
   souvent d'attendre « bien au-dessus » du seuil, et c'est faux.""")

rng = np.random.default_rng(20260830)
say("\n   loi de X                 R₀     seuil optimal   profit optimal   profit au seuil")
for name, xs, ps in (
        ("uniforme {1..10}", np.arange(1, 11), np.full(10, 0.1)),
        ("géométrique p=0,4", np.arange(1, 21), 0.4 * 0.6 ** np.arange(20)),
        ("deux points {1, 8}", np.array([1, 8]), np.array([0.9, 0.1]))):
    ps = ps / ps.sum()
    for r0 in (0.3, 0.6):
        gains = r0 * xs - 1
        # Balayage de TOUS les seuils possibles, pour vérifier que l'optimum
        # est bien celui que le théorème désigne.
        best = (None, -math.inf)
        for t in xs:
            mask = xs >= t
            prof = float((gains[mask] * ps[mask]).sum())
            if prof > best[1]:
                best = (float(t), prof)
        seuil_th = 1 / r0
        mask_th = xs > seuil_th
        prof_th = float((gains[mask_th] * ps[mask_th]).sum())
        say(f"   {name:<24} {r0:<6.2f} {best[0]:<15.0f} {best[1]:<16.5f} "
            f"{prof_th:.5f}")
        assert abs(best[1] - prof_th) < 1e-12

say("""
   Le balayage exhaustif retrouve à chaque fois le profit du seuil de
   bascule 1/R₀ : attendre davantage coûte des occasions plus vite qu'il
   n'apporte de gain. C'est le même énoncé que h16 démontrait pour la
   cagnotte, ici sans aucune hypothèse sur la loi.""")


# --------------------------------------------------------------------------
# 2. Le boost, sa loi exacte, et ce que sa visibilité vaudrait
# --------------------------------------------------------------------------

rule("2. LE BOOST — la loi exacte sur 70 560 tirages")

a = lab.load()
vals, counts = np.unique(a.boost, return_counts=True)
probs = counts / counts.sum()
e_boost = float((vals * probs).sum())
say(f"   {len(a):,} tirages archivés.\n")
say("   boost   probabilité   contribution à E[X]")
for v, p in zip(vals, probs):
    say(f"   {int(v):<7} {p:<13.5f} {v * p:.5f}")
say(f"   E[boost] = {e_boost:.4f}")

say("""
   Ce que vaudrait la VISIBILITÉ du boost avant la clôture des mises, par
   franc misé, selon le taux de retour de base R₀ — c'est l'écart de Jensen
   du théorème. « à l'aveugle » est ce que rapporte la meilleure politique
   sans voir X : miser toujours si R₀·E[X] > 1, jamais sinon.""")

say("\n   R₀      à l'aveugle   en voyant le boost   valeur de voir   seuil de jeu")
for r0 in (0.40, 0.50, 0.60, 0.70, 0.80):
    blind = max(0.0, r0 * e_boost - 1)
    seen = float((np.maximum(r0 * vals - 1, 0) * probs).sum())
    seuil = min([int(v) for v in vals if r0 * v > 1], default=None)
    say(f"   {r0:<7.2f} {blind:<13.5f} {seen:<20.5f} {seen - blind:<16.5f} "
        f"{('boost ≥ ' + str(seuil)) if seuil else 'jamais'}")

say(f"""
   Lecture. À un taux de retour de 50 %, voir le boost avant de miser vaut
   {float((np.maximum(0.5 * vals - 1, 0) * probs).sum()) - max(0.0, 0.5 * e_boost - 1):.3f} franc par franc misé. Ce n'est pas un raffinement : c'est un
   renversement complet du signe de l'espérance, obtenu sans toucher aux
   numéros et sans rien supposer du générateur.

   C'est aussi la raison pour laquelle l'app instrumente cette question
   depuis §4 du rapport plutôt que d'en spéculer. La réponse est binaire et
   se mesure sur l'appareil : le boost du tirage OUVERT est-il affiché avant
   la clôture des mises, ou seulement avec le résultat ?

   RÉSERVE. Le mécanisme exact du boost n'est pas vérifiable hors ligne.
   S'il s'agit d'une option payante coûtant une seconde mise, les chiffres
   ci-dessus se divisent par deux et le seuil se décale — la politique
   optimale reste « prendre l'option si et seulement si B/2 > 1 », soit
   boost ≥ 3, ce qui arrive {float(probs[vals >= 3].sum()):.1%} du temps.""")


# --------------------------------------------------------------------------
# 3. La combinaison — le boost déplace le seuil de la cagnotte
# --------------------------------------------------------------------------

rule("3. LA COMBINAISON — deux variables visibles valent plus que la somme")

say(f"""   La cagnotte et le boost multiplient tous deux le gain, donc le pari
   est favorable dès que B·J·p ≥ 1, c'est-à-dire J ≥ S/B. Le boost ne fait
   pas qu'ajouter : il ABAISSE le seuil de la cagnotte d'un facteur B.

   Et par absence de mémoire (h16), le gain conditionnel au-dessus de S/B
   vaut B·p·E[J | J ≥ S/B] − 1 = B·p·(S/B + μ) − 1 = **B·α**.

   Le boost multiplie donc l'avantage ET la fréquence des occasions. Avec
   α = {ALPHA:.1%} :""")

say("\n   boost   seuil de cagnotte   fréquence   avantage   profit par tirage   poids")
tot = 0.0
for v, p in zip(vals, probs):
    seuil = S / v
    freq = math.exp(-1 / (ALPHA * v))
    edge = ALPHA * v
    prof = freq * edge
    tot += p * prof
    say(f"   {int(v):<7} CHF {seuil:<15,.0f} {freq:<11.2%} {edge:<+10.1%} "
        f"{prof:<19.5f} {p:.4f}")

blind_edge = ALPHA * e_boost
blind_freq = math.exp(-1 / blind_edge)
blind = blind_freq * blind_edge
say(f"""
   profit par tirage en voyant le boost   {tot:.5f}
   profit par tirage à l'aveugle          {blind:.5f}   (seuil CHF {S / e_boost:,.0f}, {blind_freq:.1%} des tirages)
   gain de la visibilité                  ×{tot / blind:.2f}

   La visibilité du boost vaudrait donc, sur la seule voie de la cagnotte,
   un facteur {tot / blind:.2f} sur le profit par tirage — et cela s'ajoute au
   renversement du §2, qui porte sur les rangs à gain fixe.""")


# --------------------------------------------------------------------------
# 4. Ce que cela fait à la taille de mise
# --------------------------------------------------------------------------

rule("4. ET À LA TAILLE DE MISE (h17)")

say("""   Un avantage plus grand et un seuil plus bas ne changent pas seulement
   l'espérance : ils changent la fraction de Kelly, donc la croissance, donc
   le capital minimal nécessaire pour jouer sans surmiser.

   Présentation en TEMPS DE DOUBLEMENT plutôt qu'en rendement annualisé.
   Annualiser revient à composer sur cent mille paris, ce qui produit
   toujours des nombres astronomiques et ne renseigne sur rien : à
   +295 % d'avantage la composition annuelle donne 10³⁶ %, chiffre
   arithmétiquement juste et humainement vide. Le temps de doublement dit la
   même chose sans exploser.""")

n = POOL // K
say(f"\n   boost   avantage   part des tirages   fraction Kelly   croissance/occasion   capital min. à CHF 1")
total_g = 0.0
for v, pb in zip(vals, probs):
    edge = ALPHA * v
    J = S + v * (ALPHA * S)               # v·E[J | J ≥ S/v] = S + v·μ
    q = n * P1
    b = J / n - 1
    f = q - (1 - q) / b
    if f <= 0:
        say(f"   {int(v):<7} {edge:<+10.1%} défavorable")
        continue
    g = q * math.log1p(f * b) + (1 - q) * math.log1p(-f)
    freq = math.exp(-1 / (ALPHA * v)) * pb        # part de TOUS les tirages
    total_g += freq * g
    say(f"   {int(v):<7} {edge:<+10.1%} {freq:<18.2%} {f:<16.3e} {g:<21.3e} "
        f"CHF {n * 1.0 / f:>9,.0f}")

# Référence : la même politique sans voir le boost (h17 en est le cas v = 1).
q = n * P1
J1 = S * (1 + ALPHA)
b1 = J1 / n - 1
f1 = q - (1 - q) / b1
g1 = q * math.log1p(f1 * b1) + (1 - q) * math.log1p(-f1)
base_g = math.exp(-1 / ALPHA) * g1

say(f"""
   politique combinée (voir le boost)   {total_g:.3e} par tirage,
       doublement du capital en {math.log(2) / total_g / DRAWS_PER_DAY:,.0f} jours
   politique de h17 (boost ignoré)      {base_g:.3e} par tirage,
       doublement en {math.log(2) / base_g / DRAWS_PER_DAY:,.0f} jours
   rapport                              ×{total_g / base_g:.1f}

   AVERTISSEMENT SUR CES NOMBRES. Ils sont tous proportionnels à α, et α est
   estimé sur UN relevé de cagnotte — h16 donne un intervalle de +8 % à
   +1165 %. Un α trois fois plus petit rallonge le temps de doublement d'un
   facteur bien supérieur à trois, la croissance de Kelly étant quadratique
   en l'avantage. Ces chiffres disent un ORDRE DE GRANDEUR et une
   COMPARAISON entre politiques ; ils ne disent pas un rendement.

   Trois autres hypothèses les portent, et aucune n'est vérifiée : que le
   boost multiplie aussi la cagnotte progressive et pas seulement les rangs
   fixes ; qu'il soit visible avant la clôture ; et qu'on puisse miser une
   fraction arbitraire du capital, alors que le ticket a un prix plancher
   (h17 §4). La dernière colonne donne le capital minimal correspondant.

   Ce qui reste solide, indépendamment de α : le RAPPORT entre les deux
   politiques. Voir le boost vaut un facteur, et ce facteur ne dépend pas de
   l'échelle de la cagnotte.""")


# --------------------------------------------------------------------------
# 5. Ce que le théorème dit du reste du dossier
# --------------------------------------------------------------------------

rule("5. CE QUE LE THÉORÈME DIT DU RESTE DU DOSSIER")

say(f"""   Le théorème de la valeur de voir donne une grille de lecture qui
   range d'un coup trente voies d'investigation.

   VALEUR NULLE, ET DÉMONTRÉE TELLE. Le choix des numéros. L'invariance dit
   que la loi du gain ne dépend pas de la grille : la variable est
   dégénérée, l'écart de Jensen est nul. Aucune quantité de statistiques sur
   les numéros chauds, froids, les retards ou les paires ne peut créer un
   écart de Jensen là où la loi ne varie pas. C'est pourquoi les 3 313 tests
   du registre ne pouvaient PAS trouver autre chose que zéro.

   VALEUR NULLE, MAIS PAR ACCIDENT. La récupération du générateur (h4–h14).
   Elle créerait un X énorme — la certitude du tirage suivant — mais aucun
   générateur n'a été trouvé. La voie est ouverte en théorie et vide en
   pratique.

   VALEUR POSITIVE ET MESURÉE. La cagnotte (h15, h16, h17) : +{ALPHA:.1%} par
   franc au-dessus du seuil, {math.exp(-1 / ALPHA):.1%} des tirages.

   VALEUR POSITIVE ET NON MESURÉE. Le boost, si visible. C'est aujourd'hui
   la seule case du tableau qui soit à la fois grande et vide, et elle se
   remplit avec une observation faite sur l'appareil, pas avec du calcul.

   VALEUR NULLE PAR CONSTRUCTION. Tout ce qui n'est visible qu'APRÈS la
   clôture des mises. Le théorème le dit sans détour : une variable qu'on ne
   peut pas voir avant de miser ne peut pas entrer dans A, donc ne vaut
   rien, si informative soit-elle. C'est la réponse générale à « l'ordre de
   sortie des boules aiderait-il ? » — il n'aide que s'il permet de PRÉDIRE,
   jamais parce qu'il informe.""")

rule(f"total {time.time() - T0:.0f}s")
