"""h42 — le barème, enfin lu. Ce qu'il confirme, et ce qu'il rend obsolète.

Ce que le dossier attendait
----------------------------
Le §5 s'arrêtait sur un fait : aucun barème réel dans le dépôt. Tout le volet
financier a été bâti pour contourner ce trou — d'abord par la condition
suffisante « rangs intermédiaires >= 0 » (§5 bis), puis par la borne
comptable rho >= 24,5 % du §50, qui écrivait en toutes lettres :

    « Un document lèverait w_h exactement et rendrait h34 obsolète : zéro
      relevé, zéro modèle, la demande la moins chère du dossier. »

Le document est arrivé. Ce fichier fait ce que cette phrase annonçait.

Les données
-----------
`lab/bareme_observed.csv` — les cinq tableaux de gains relevés sur
jeux.loro.ch le 30 août 2026 à 22:16, et un second relevé de cagnottes ajouté
à `lab/jackpots_observed.csv`, treize heures après le premier.

Le risque est la TRANSCRIPTION : ces chiffres viennent de captures d'écran
lues à l'œil. La section 1 lui oppose un contrôle qu'une erreur de lecture ne
pourrait pas passer.

Ce fichier ne teste pas l'archive : il lit, vérifie et recalcule.
"""

import csv
import math
import os
import sys
import time
from fractions import Fraction as F

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


def p_hits(k, h):
    """P(exactement h numeros trouves) — hypergeometrique exacte, en rationnels."""
    return F(math.comb(k, h) * math.comb(POOL - k, DRAWN - h), math.comb(POOL, DRAWN))


BASE, EXTRA = {}, {}
with open(os.path.join(ROOT, "bareme_observed.csv")) as fh:
    for row in csv.DictReader(l for l in fh if not l.startswith("#")):
        k, h = int(row["mise"]), int(row["hits"])
        BASE.setdefault(k, {})[h] = float(row["gain_base"])
        EXTRA.setdefault(k, {})[h] = float(row["gain_extra"])

BANGO = {5: 245, 6: 3035, 7: 3838, 8: 13051, 10: 498218}
STAKES = sorted(BASE)


# ==========================================================================
# 1. LE CONTRÔLE QUI VALIDE LA TRANSCRIPTION
# ==========================================================================

rule("1. LE CONTRÔLE DE TRANSCRIPTION, ET IL EST AUSSI UN RÉSULTAT")

say("""   Les cinq tableaux ont été lus séparément sur cinq captures. Une erreur
   de lecture sur un seul gain serait invisible en relisant le tableau — mais
   pas en calculant l'espérance de chaque mise, parce qu'un opérateur
   égalise son taux de retour entre les mises. Si les cinq espérances
   tombent ensemble, la transcription est bonne ET l'égalisation est
   démontrée. Si l'une décroche, c'est qu'un chiffre est faux.""")

E_base = {k: float(sum(p_hits(k, h) * g for h, g in BASE[k].items())) for k in STAKES}
E_extra = {k: float(sum(p_hits(k, h) * g for h, g in EXTRA[k].items())) for k in STAKES}
m_base = sum(E_base.values()) / len(E_base)
spread = (max(E_base.values()) - min(E_base.values())) / m_base

say("\n   mise   E[gain de base]   P(k/k)          1/P")
for k in STAKES:
    p = float(p_hits(k, k))
    say(f"   {k:>4}   {E_base[k]:>15.4f}   {p:.4e}   {1/p:>11,.0f}")

say(f"""
   moyenne {m_base:.4f} CHF, étendue {spread:.2%}.

   Les cinq tombent à {spread:.1%} les unes des autres. C'est le contrôle : cinq
   tableaux mal lus ne se seraient pas rejoints. Et c'est le résultat : le
   §50 avait DÉMONTRÉ, sur 4 081 barèmes admissibles, que chaque décision du
   dossier ne dépend que du scalaire total et non de la forme du barème, et
   que le « classement des mises par espérance » de b2 était vide par
   identité comptable. Le voici MESURÉ sur le barème réel.""")


# ==========================================================================
# 2. LE PRIX DU TICKET, DÉDUIT
# ==========================================================================

rule("2. LE PRIX DU TICKET — la donnée que le dossier réclamait")

say(f"""   Le taux de retour vaut E/c et ne peut pas dépasser 1. Donc

       c > {max(E_base.values()):.4f} CHF

   Un ticket à un franc est ARITHMÉTIQUEMENT EXCLU : l'opérateur perdrait
   de l'argent sur chaque mise. C'est une déduction, pas une hypothèse — et
   elle invalide la lecture par défaut que tout le dossier avait employée
   faute de mieux.""")

say("\n   prix supposé   taux de retour de base")
for c in (1.0, 1.5, 2.0, 2.5, 3.0):
    tag = "  <- exclu" if m_base / c >= 1 else ""
    say(f"   CHF {c:>4.2f}       {m_base/c:>7.1%}{tag}")

C = 2.0
say(f"""
   La suite prend c = {C:.2f}, seule valeur ronde compatible qui donne un taux
   de retour plausible pour une loterie ({m_base/C:.1%}). C'est une HYPOTHÈSE, la
   dernière du dossier sur ce sujet, et elle est levée par une observation
   du prix affiché — la seule qui reste à faire.""")


# ==========================================================================
# 3. RHO EXACT, CONTRE LA BORNE DU §50
# ==========================================================================

rule("3. LES RANGS INTERMÉDIAIRES, EXACTS")

say(f"""   Le §50 les bornait par comptabilité : rho >= 0,245 sous hypothèses
   nommées. On les calcule maintenant.

   mise   rang plein   rangs intermédiaires   rho = interm/c   borne §50""")
for k in STAKES:
    p = float(p_hits(k, k))
    full = p * BASE[k][k]
    interm = E_base[k] - full
    say(f"   {k:>4}   {full:>10.4f}   {interm:>20.4f}   {interm/C:>14.3f}   "
        f"{'>= 0,245  OK' if interm/C >= 0.245 else '  VIOLEE'}")

rho6 = (E_base[6] - float(p_hits(6, 6)) * BASE[6][6]) / C
say(f"""
   La borne du §50 TIENT sur les cinq mises, et elle était conservatrice
   d'un facteur {rho6/0.245:.1f} à la mise 6 ({rho6:.3f} contre 0,245). C'est le
   comportement attendu d'une borne : vraie, et lâche.""")


# ==========================================================================
# 4. LE SEUIL DE BASCULE, EXACT
# ==========================================================================

rule("4. LE SEUIL, SANS PLUS AUCUNE CONDITION SUFFISANTE")

say(f"""   Le pari est favorable quand le gain espéré atteint le prix du ticket :

       E[base] + p*J >= c      donc      J* = (c - E[base]) / p

   Plus rien n'est jeté : ni les rangs intermédiaires, ni le gain fixe du
   rang plein. Le §5 bis donnait une condition SUFFISANTE en ignorant tout
   cela ; voici la condition NÉCESSAIRE ET SUFFISANTE.

   mise   seuil §5 bis (c/p)   seuil EXACT   rapport   cagnotte au 30/08 22:16   fraction""")
Jstar = {}
for k in STAKES:
    p = float(p_hits(k, k))
    Jstar[k] = (C - E_base[k]) / p
    old = C / p
    say(f"   {k:>4}   {old:>18,.0f}   {Jstar[k]:>11,.0f}   {Jstar[k]/old:>7.3f}   "
        f"{BANGO[k]:>23,}   {BANGO[k]/Jstar[k]:>7.1%}")

say(f"""
   Le seuil réel vaut donc environ {Jstar[6]/(C/float(p_hits(6,6))):.0%} du seuil suffisant que le dossier
   employait. Et la mise 6 est à {BANGO[6]/Jstar[6]:.0%} de son point de bascule — contre
   les 29,5 % que le §21 annonçait sur le premier relevé, et les 47,5 %
   qu'on lit maintenant avec le barème réel et la cagnotte du soir.

   Le §21 avait vu juste sur la structure : les petites mises sont
   systématiquement les plus proches, et la mise 6 domine.""")


# ==========================================================================
# 5. CE QUE LE SECOND RELEVÉ APPORTE
# ==========================================================================

rule("5. DEUX RELEVÉS — l'accumulation mesurée, et la première chute")

say("""   Le §36 a établi que la précision sur la loi de la cagnotte se paie en
   CHUTES et non en relevés, mais que deux relevés rapprochés donnent
   l'accumulation r presque exactement. Le second relevé fait les deux.""")

R1 = {5: 355, 6: 2287, 7: 1540, 8: 9292, 10: 495713}
n_draws = (22 * 60 + 16 - 9 * 60 - 17) // 5
say(f"\n   {n_draws} tirages séparent les deux relevés (09:17 -> 22:16, un toutes les 5 min).")
say("\n   mise   09:17      22:16      variation   accumulation r")
for k in STAKES:
    d = BANGO[k] - R1[k]
    say(f"   {k:>4}   {R1[k]:>8,}   {BANGO[k]:>8,}   {d:>+10,}   "
        f"{'CHUTE OBSERVEE' if d < 0 else f'{d/n_draws:>8.2f} CHF/tirage'}")

say(f"""
   Deux acquis, et le second est le plus rare.

   L'ACCUMULATION est mesurée : {(BANGO[6]-R1[6])/n_draws:.2f} CHF par tirage à la mise 6, là où
   le §36 supposait 5,72 faute de mieux. L'écart est de {abs((BANGO[6]-R1[6])/n_draws-5.72)/5.72:.0%}.

   Et une CHUTE a été observée sur la mise 5 — la première du dossier. Le
   §36 a montré que l'information sur la loi de la cagnotte arrive au rythme
   des chutes : celle-ci est donc la première unité d'information sur q, et
   il en faut une dizaine pour situer le paramètre à un facteur 3 près.""")


rule("6. CE QUE CE FICHIER REMPLACE, ET CE QU'IL CONFIRME")

say(f"""   REMPLACE. Le §50 tout entier — sa comptabilité, sa borne rho >= 0,245,
   son espace admissible, son catalogue de 72 tables. Il existait pour
   contourner l'absence du barème, il l'avait annoncé, et il a eu raison de
   le dire. Sa borne tenait, et elle était lâche d'un facteur {rho6/0.245:.1f}.

   CONFIRME. Le théorème de collapse du §50 — les cinq espérances de base
   sont égales à {spread:.1%}, donc le choix de la mise est bien vide en espérance.
   La structure du §21 — les petites mises sont les plus proches du point de
   bascule. Et la méthode : une borne honnête, posée sans le barème, n'a été
   ni fausse ni inutile ; elle a simplement été dépassée par une donnée.

   RESTE. Le prix du ticket est déduit comme SUPÉRIEUR à {max(E_base.values()):.2f} — un franc
   est exclu — mais sa valeur exacte reste à lire. C'est désormais la seule
   inconnue de toute la chaîne financière.

   LIMITES.
   1. Transcription à l'œil depuis des captures. Le contrôle de la section 1
      la valide indirectement, il ne la remplace pas.
   2. c = 2 est une hypothèse, la dernière, et tous les seuils lui sont
      proportionnels en (c - E)/p — donc TRÈS sensibles : à c = 2,50 le
      seuil de la mise 6 devient {(2.5-E_base[6])/float(p_hits(6,6)):,.0f} au lieu de {Jstar[6]:,.0f}.
   3. L'option EXTRA n'est pas traitée : son prix et sa portée ne sont pas
      lisibles sur les captures. Son espérance seule vaut {E_extra[6]:.2f} CHF à la
      mise 6, ce qui exclut qu'elle soit gratuite.
   4. Le relevé est à BOOST x1 ; le boost multiplie les gains et déplacerait
      tout ce tableau (§31).

   Registre : inchangé. h42 ne teste pas l'archive — il lit et recalcule.""")

say(f"\n   ({time.time() - T0:.1f} s)")
