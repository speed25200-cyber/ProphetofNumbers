"""h37 — le plus grand trou d'information du dossier, et ce qu'il vaut.

Le trou
--------
L'archive est TRIÉE : n1..n20 est croissant sur les 70 560 lignes. Le §11 le
dit sans détour — un tirage ordonné porterait 122,69 bits contre 61,62 pour
l'ensemble trié, « le plus gros gain d'information disponible, et il n'est
pas dans les données dont on dispose ».

Conséquence que personne n'a formulée : contre toute hypothèse portant sur
l'ORDRE des boules, l'archive n'a pas une puissance faible. Elle a une
puissance EXACTEMENT NULLE — la statistique n'est pas calculable. C'est donc
une famille de déviations sans aucun plafond, et elle est immense : l'espace
ordonné compte 80!/60! = 2^122,69 issues contre 2^61,62 pour l'espace trié.

Les §41 à §43 viennent de montrer que le plafond d'un biais indétectable
croît en m^(1/4). Une famille invisible a un plafond infini. Sur ce critère,
le canal de l'ordre est un trou bien plus grand que le troisième ordre que
h27 est en train de borner.

La question
-----------
Ce trou vaut-il quelque chose À UN JOUEUR ? C'est une question différente de
celle qu'ont poursuivie les §17 à §35, qui cherchaient à récupérer le
générateur. Ici on demande : à supposer que l'ordre soit biaisé et que le
joueur le sache, que gagne-t-il ?

La réponse est un théorème d'une ligne, et elle est nette.

Ce fichier ne teste pas l'archive : comme h1, h14, h17, h25, h30, h31 et
h32, il démontre.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
RNG = np.random.default_rng(20260902)
POOL, DRAWN = 80, 20
N_ARCHIVE = 70_560
DRAWS_PER_DAY = 204


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# 1. LA TAILLE DU TROU
# ==========================================================================

rule("1. CE QUE L'ARCHIVE TRIÉE NE PEUT PAS VOIR")

bits_sorted = math.log2(math.comb(POOL, DRAWN))
bits_ordered = sum(math.log2(POOL - i) for i in range(DRAWN))
say(f"""   Un tirage trié     : log2 C(80,20)   = {bits_sorted:.4f} bits
   Un tirage ordonné  : log2 (80!/60!)   = {bits_ordered:.4f} bits
   Rapport                                = x{bits_ordered/bits_sorted:.3f}

   L'archive de {N_ARCHIVE:,} tirages porte donc {N_ARCHIVE*bits_sorted/1e6:.2f} Mbit, et en porterait
   {N_ARCHIVE*bits_ordered/1e6:.2f} si l'ordre y était. Les {N_ARCHIVE*(bits_ordered-bits_sorted)/1e6:.2f} Mbit manquants ne sont pas
   difficiles à exploiter : ils sont ABSENTS.

   La famille la plus simple qui vit dans ce trou : la loi de position,
   P(le numéro n sort en position j), soit 80 x 20 = 1 600 cellules. Aucun
   test du dossier ne la touche, et aucun ne le peut — sur des données
   triées la position n'existe pas. La puissance n'est donc pas faible :
   elle est nulle, et le plafond de cette famille est INFINI.""")


# ==========================================================================
# 2. LE THÉORÈME — et il vide le trou
# ==========================================================================

rule("2. CE QUE CE TROU VAUT À UN JOUEUR : EXACTEMENT ZÉRO")

say("""   THÉORÈME. Le gain d'un ticket ne dépend du tirage que par le nombre de
   numéros cochés qui en font partie — c'est-à-dire par l'ENSEMBLE tiré, et
   jamais par l'ordre dans lequel les boules sont sorties. Donc pour toute
   déviation qui modifie la loi de l'ORDRE en laissant inchangée la loi
   marginale de l'ENSEMBLE, l'espérance de gain de toute grille est
   rigoureusement inchangée.

   La démonstration tient en une ligne : E[gain] = somme sur les ensembles S
   de P(S) x gain(S), et une déviation d'ordre pur ne touche aucun P(S).

   Autrement dit, dans le langage du §41 : le vecteur d'avantage `a` de la
   famille « ordre pur » est le vecteur NUL, et le plafond
   ||a|| x (2m)^(1/4) x racine(z/N) vaut zéro quel que soit m, aussi grand
   soit-il, et quelle que soit la taille de l'archive.

   Le plus grand trou d'information du dossier a donc un plafond
   d'exploitation exactement nul. Un plafond infini en DÉTECTION, un plafond
   nul en EXPLOITATION : les deux à la fois, sans contradiction, parce que
   ce ne sont pas les mêmes questions.""")

# Vérification : une déviation d'ordre pur laisse-t-elle vraiment les
# marginales d'ensemble intactes ? On le mesure plutôt que de le supposer.
say("""
   VÉRIFICATION. On fabrique un générateur dont l'ORDRE est massivement
   biaisé — les petits numéros sortent systématiquement les premiers — mais
   dont l'ensemble tiré reste uniforme par construction, puisqu'on ne fait
   que PERMUTER l'ordre de sortie d'un tirage uniforme. Si le théorème est
   juste, aucune statistique d'ensemble ne doit bouger.""")


def draw_uniform_set(rng):
    return rng.choice(POOL, size=DRAWN, replace=False)


def biased_order(s, rng, strength):
    """Réordonne un ensemble : les petits numéros vers le début."""
    if rng.random() < strength:
        return np.sort(s)
    return rng.permutation(s)


REPS = 200_000
counts_free = np.zeros(POOL)
counts_bias = np.zeros(POOL)
pos_first_free = np.zeros(POOL)
pos_first_bias = np.zeros(POOL)
for _ in range(REPS):
    s = draw_uniform_set(RNG)
    o_free = RNG.permutation(s)
    o_bias = biased_order(s, RNG, 0.9)
    counts_free[s] += 1
    counts_bias[s] += 1
    pos_first_free[o_free[0]] += 1
    pos_first_bias[o_bias[0]] += 1

chi_set = float(((counts_bias - REPS * DRAWN / POOL) ** 2
                 / (REPS * DRAWN / POOL)).sum())
chi_pos = float(((pos_first_bias - REPS / POOL) ** 2 / (REPS / POOL)).sum())
chi_pos_free = float(((pos_first_free - REPS / POOL) ** 2 / (REPS / POOL)).sum())

# Le null n'est pas tabulé : il est SIMULÉ. Écrire « attendu 79 » serait
# exactement l'erreur que la règle n° 1 du labo interdit — les 80 comptes
# d'ensemble somment à 20N par construction, donc leur chi2 n'a pas 79 pour
# espérance. Le §1 de l'audit s'y est trompé une fois (0,76 df et non 1,00).
NULL_REPS = 60
null_set, null_pos = [], []
for _ in range(NULL_REPS):
    cs = np.zeros(POOL)
    cp = np.zeros(POOL)
    for _ in range(REPS // 10):
        s = draw_uniform_set(RNG)
        cs[s] += 1
        cp[RNG.permutation(s)[0]] += 1
    n = REPS // 10
    null_set.append(float(((cs - n * DRAWN / POOL) ** 2 / (n * DRAWN / POOL)).sum()))
    null_pos.append(float(((cp - n / POOL) ** 2 / (n / POOL)).sum()))
mu_set, sd_set = float(np.mean(null_set)), float(np.std(null_set, ddof=1))
mu_pos, sd_pos = float(np.mean(null_pos)), float(np.std(null_pos, ddof=1))

say(f"""
   Null SIMULÉ sur {NULL_REPS} archives propres ({REPS//10:,} tirages chacune) :
     chi2 d'ensemble   {mu_set:.1f} ± {sd_set:.1f}   (et non 79 : les 80 comptes
                       somment à 20N, l'espérance naïve est fausse — c'est
                       l'erreur que le §1 de l'audit a commise une fois)
     chi2 de position  {mu_pos:.1f} ± {sd_pos:.1f}

   sur {REPS:,} tirages, biais d'ordre à 90 % :

     chi2 des 80 marginales d'ENSEMBLE          {chi_set:>12.1f}
     chi2 de la loi de la PREMIÈRE boule        {chi_pos:>12.1f}
     le même, ordre libre (témoin négatif)      {chi_pos_free:>12.1f}

   Le biais d'ordre est colossal — la loi de la première boule sort à
   {chi_pos:,.0f} contre {mu_pos:.0f} ± {sd_pos:.0f} au null simulé, soit z = {(chi_pos-mu_pos)/sd_pos:,.0f} — et les
   marginales d'ensemble ne bougent PAS ({chi_set:.1f} contre {mu_set:.1f} ± {sd_set:.1f},
   z = {(chi_set-mu_set)/sd_set:+.2f}). C'est le théorème, vérifié : un générateur peut être massivement
   défaillant dans son ordre sans qu'un joueur y perde ou y gagne un
   centime, et sans qu'aucune des 39 voies du dossier ne puisse le voir.""")


# ==========================================================================
# 3. LA SEULE FAÇON DONT L'ORDRE PEUT VALOIR QUELQUE CHOSE
# ==========================================================================

rule("3. PAR OÙ L'ORDRE PEUT MALGRÉ TOUT PAYER")

say("""   Le théorème du §2 ferme la voie DIRECTE : un biais d'ordre pur ne
   rapporte rien. Il en laisse exactement deux ouvertes, et il faut les
   nommer parce qu'elles sont de nature très différente.

   VOIE 1 — l'ordre comme SYMPTÔME. Un biais d'ordre n'est pas exploitable,
   mais il révèle que la source n'est pas ce qu'on croit. Or une source
   défaillante dans son ordre l'est probablement aussi ailleurs, et cet
   ailleurs, lui, peut toucher les ensembles. L'ordre est donc un
   INSTRUMENT DE DIAGNOSTIC à haute sensibilité — deux fois plus
   d'information par tirage — pointé sur une question dont la réponse
   intéresse le joueur indirectement.

   VOIE 2 — l'ordre comme LEVIER ALGÉBRIQUE. C'est celle que les §17 à §35
   ont poursuivie : un tirage ordonné publie 122,69 bits, assez pour
   contenir deux sorties de 64 bits, ce qui rend la récupération d'état
   linéaire au lieu de combinatoire. Si un générateur était récupéré, le
   tirage suivant ne serait plus aléatoire CONDITIONNELLEMENT à l'état —
   l'invariance ne s'appliquerait plus du tout, faute d'uniformité. Ce n'est
   pas un avantage marginal, c'est la fin du théorème.

   La distinction est celle-ci, et elle range tout le dossier :

     un biais d'ordre           -> plafond d'exploitation nul (théorème §2)
     un GÉNÉRATEUR récupéré     -> plafond illimité, invariance caduque

   L'ordre ne vaut donc rien par ce qu'il RÉVÈLE, et tout par ce qu'il
   permettrait de PRÉDIRE. C'est exactement le corollaire du théorème M
   (§31) — « une variable visible seulement après la clôture ne peut pas
   entrer dans la politique » — appliqué à la bonne variable.""")


# ==========================================================================
# 4. CE QUE CELA DIT DE LA COLLECTE
# ==========================================================================

rule("4. CONSÉQUENCE POUR LA COLLECTE DE DONNÉES")

say("""   L'app conserve désormais l'ordre de sortie et en accumule un toutes les
   cinq minutes (§34). Que faut-il en attendre, et à quelle échéance ?

   Pour la VOIE 2 — la récupération — le §27 a tranché : quatre à cinq
   tirages CONSÉCUTIFS suffisent aux trois modèles de source, et le pas
   impair est le schéma convergent. C'est une question de minutes, pas de
   mois, et l'app y répond seule.

   Pour la VOIE 1 — le diagnostic — la loi de position à 1 600 cellules
   demande un volume, et le §41 donne la règle : le plafond de détection
   décroît en 1/racine(N). En prenant le cas marginal comme unité :""")

say("\n   tirages ordonnés   durée de collecte   plafond de détection relatif")
for n in (100, 1_000, 10_000, 70_560):
    rel = ((1600 / 80) ** 0.25) * math.sqrt(N_ARCHIVE / n)
    days = n / DRAWS_PER_DAY
    dur = f"{days*24:.0f} h" if days < 2 else f"{days:.0f} j"
    say(f"   {n:>16,}   {dur:>17}   x{rel:>10.1f}")

say(f"""
   Lecture. Il faudrait environ {int(N_ARCHIVE * math.sqrt(1600/80)):,} tirages ordonnés — {N_ARCHIVE*math.sqrt(1600/80)/DRAWS_PER_DAY/365:.1f} ans de
   collecte — pour que la loi de position soit contrainte aussi finement que
   les marginales le sont aujourd'hui. La voie 1 est donc un projet long,
   et le §2 vient de montrer qu'elle ne rapporterait rien directement même
   en aboutissant.

   LA CONSÉQUENCE PRATIQUE, et elle inverse une priorité du dossier :
   accumuler des tirages ordonnés pour BORNER la famille de l'ordre est un
   mauvais investissement — des années de collecte pour fermer une famille
   dont le plafond d'exploitation est nul par théorème. Les capturer pour
   la voie 2 en est un excellent : cinq consécutifs suffisent, l'app les
   obtient en vingt-cinq minutes, et c'est la seule voie du dossier dont
   l'aboutissement rendrait l'invariance caduque.

   LIMITES.
   1. Le théorème du §2 suppose que le gain ne dépend que du nombre de hits.
      C'est vrai du barème d'un keno, et le §26 l'a déjà utilisé. Il serait
      faux si un rang payait selon l'ordre — aucun keno connu ne le fait,
      mais c'est une hypothèse sur le produit et non un théorème.
   2. La voie 1 suppose qu'un défaut d'ordre soit corrélé à un défaut
      d'ensemble. C'est plausible et non démontré ; le dossier n'a aucun
      moyen de l'établir.
   3. Le calendrier du §4 applique la loi d'échelle du §41, dont la
      constante n'est pas transportable — seuls les RAPPORTS le sont, et
      c'est ainsi que la table est lue.

   Registre : inchangé. h37 ne teste pas l'archive — il démontre.""")

say(f"\n   ({time.time() - T0:.1f} s)")
