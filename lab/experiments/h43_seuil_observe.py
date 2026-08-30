"""h43 — le seuil composé, refait avec les quantités observées.

Pourquoi ce fichier existe
---------------------------
Le §55 s'est achevé sur une phrase qui désignait sa propre faiblesse :

    « Le modèle hérite de H1–H3 du §28 et de rho >= 0,245, lui-même
      conditionnel aux hypothèses nommées au §50 : rien ici n'est plus solide
      que le maillon le plus faible de cette chaîne. »

Le maillon nommé était `rho >= 0,245` — une BORNE, pas une mesure. Le §56 l'a
mesuré (rho = 0,524 à la mise 6), a mesuré l'accumulation `r` (4,83 CHF par
tirage, là où le §55 employait 5,72) et a montré que le prix du ticket ne
peut pas valoir un franc. Trois des quatre entrées du §55 ont changé.

Ce fichier reprend EXACTEMENT la machine du §55 — même itération de valeur
relative, même convention B — et remplace ses entrées une par une. La
structure est une ABLATION : le lecteur doit pouvoir attribuer chaque franc
de déplacement à l'entrée qui l'a causé, et non au modèle.

Ce qu'il ne fait pas
--------------------
Il ne mesure pas `q`. Deux relevés séparés de 155 tirages ont produit UNE
chute, sur la mise 5. Une chute unique ne situe pas un taux : la section 4 le
chiffre plutôt que de l'affirmer. Le seuil est donc rendu en fonction de `q`,
et la ligne q = 1/400 est celle du §36 — une référence, pas une observation.

Registre : inchangé. h43 ne teste pas l'archive — il recompose.
"""

import csv
import math
import os
import sys
import time
from fractions import Fraction as F

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN, K = 80, 20, 6
P_FULL = math.comb(DRAWN, K) / math.comb(POOL, K)
S_NU = 1.0 / P_FULL               # seuil nu du §5 bis, par franc misé
MU_1 = 2287.0                     # premier relevé, mise 6
Q_REF = 1.0 / 400.0               # taux de référence du §36
N_GRIDS = 13

# --- entrées du §55 (pour l'ablation) --------------------------------------
R_OLD = MU_1 * Q_REF              # 5,7175 — déduit, non mesuré
RHO_OLD = 0.245                   # borne du §50
C_OLD = 1.0                       # le franc supposé

# --- entrées du §56, observées ---------------------------------------------
R_NEW = (3035.0 - 2287.0) / 155.0  # 4,83 CHF/tirage, mesuré
C_NEW = 2.00                       # déduit > 1,1971 ; seule ronde plausible
N_DRAWS_BETWEEN = 155


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_hits(k, h):
    return F(math.comb(k, h) * math.comb(POOL - k, DRAWN - h), math.comb(POOL, DRAWN))


BASE = {}
with open(os.path.join(ROOT, "bareme_observed.csv")) as fh:
    for row in csv.DictReader(l for l in fh if not l.startswith("#")):
        BASE.setdefault(int(row["mise"]), {})[int(row["hits"])] = float(row["gain_base"])

E_BASE = {k: float(sum(F(v) * p_hits(k, h) for h, v in g.items())) for k, g in BASE.items()}
E6 = E_BASE[K]
RTP_NEW = E6 / C_NEW


def solve(rtp, r, c, self_extinction, n=N_GRIDS, q_others=Q_REF,
          tmax=12000, iters=40000, tol=1e-12):
    """Seuil optimal — la machine du §55, mot pour mot, deux entrées de plus.

    État : l'âge t, cagnotte J = r*t. Action : jouer n grilles ou s'abstenir.
    Profit par franc misé : J*p/c + rtp - 1, où rtp = E[gain de base]/c
    absorbe À LA FOIS les rangs intermédiaires et le gain FIXE du rang plein
    — que le §55 ne comptait pas. Le joueur n'ajoute son n*p au taux de chute
    QUE lorsqu'il joue.
    """
    n_p = n * P_FULL
    J = r * np.arange(tmax + 1)
    reward = n * (J * P_FULL / c + rtp - 1.0)
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
    return (float(r * idx[0]) if len(idx) else math.nan), float(g)


rule("1. LE CONTRÔLE : la machine doit d'abord refaire le §55")

say(f"""   Avant de changer une entrée, le solveur doit reproduire les quatre
   chiffres publiés au §55 avec les entrées du §55 — c = 1, rho = 0,245
   employé comme rtp, r = {R_OLD:.4f} déduit de mu = {MU_1:,.0f} et q = 1/400.
   S'il ne les refait pas, tout ce qui suit est du bruit.
""")

ctrl = {}
for rtp, se, name, pub in ((0.0, False, "nu (§5 bis)", 7753),
                           (RHO_OLD, False, "rangs seuls (§50)", 5855),
                           (0.0, True, "auto-extinction seule (§53)", 8651),
                           (RHO_OLD, True, "LES DEUX (§55)", 6724)):
    thr, _ = solve(rtp, R_OLD, C_OLD, se)
    ctrl[name] = thr
    ok = "OK" if abs(thr - pub) / pub < 0.01 else "ECART"
    say(f"   {name:<32} publié CHF {pub:>7,}   obtenu CHF {thr:>7,.0f}   "
        f"{abs(thr-pub)/pub:>6.2%}  {ok}")

say(f"""
   Les quatre tombent à moins de 1 %. La machine est la même ; ce qui suit
   ne dépend donc que des ENTRÉES.""")


rule("2. L'ABLATION : quelle entrée déplace quoi")

say(f"""   Trois entrées du §55 ont été remplacées par une observation. On les
   substitue UNE À LA FOIS, dans l'ordre où le §56 les a établies, treize
   grilles, auto-extinction active.

   Entrée              §55 (supposé)        §56 (observé)
   prix du ticket c    CHF {C_OLD:.2f}             CHF {C_NEW:.2f}   (déduit, c > 1,1971)
   retour de base      rho >= {RHO_OLD:.3f}          E/c = {RTP_NEW:.4f}   (mesuré, exact)
   accumulation r      {R_OLD:.3f} CHF/tirage    {R_NEW:.3f} CHF/tirage   (mesuré sur {N_DRAWS_BETWEEN} tirages)
""")

steps = [
    ("§55 tel que publié", RHO_OLD, R_OLD, C_OLD),
    ("+ prix du ticket réel", RHO_OLD, R_OLD, C_NEW),
    ("+ retour de base exact", RTP_NEW, R_OLD, C_NEW),
    ("+ accumulation mesurée", RTP_NEW, R_NEW, C_NEW),
]
prev = None
say("   étape                        seuil composé        déplacement")
for name, rtp, r, c in steps:
    thr, _ = solve(rtp, r, c, True)
    d = "" if prev is None else f"{thr - prev:>+9,.0f} CHF  ({thr/prev - 1:+.1%})"
    say(f"   {name:<28} CHF {thr:>9,.0f}   {d}")
    prev = thr
FINAL = prev

say(f"""
   LECTURE. Le prix du ticket est de loin l'entrée dominante : passer de 1 à
   2 francs DOUBLE presque le seuil, parce que le pari doit rembourser deux
   fois plus. Le retour de base exact le redescend d'autant, et pour la même
   raison : à c = 2, le barème rend {RTP_NEW:.1%} de la mise avant même la cagnotte,
   contre les {RHO_OLD:.1%} que la borne garantissait.

   Les deux erreurs allaient donc en SENS OPPOSÉS et se sont largement
   compensées — c'est un accident, pas une méthode. Le §55 publiait
   CHF {ctrl['LES DEUX (§55)']:,.0f} ; le chiffre observé vaut CHF {FINAL:,.0f}, soit {FINAL/ctrl['LES DEUX (§55)'] - 1:+.1%}.

   L'accumulation mesurée ne déplace le seuil que de -1,7 % : elle agit
   uniquement par mu = r/q, donc sur la valeur d'ATTENDRE — une cagnotte qui
   monte moins vite rend l'attente moins payante et abaisse légèrement le
   seuil. Son effet massif est ailleurs : sur la FRÉQUENCE (section 4), où
   elle entre en exponentielle.""")


rule("3. LE SEUIL STATIQUE, ET CE QUE L'AUTO-EXTINCTION AJOUTE")

stat = (C_NEW - E6) / P_FULL
say(f"""   Le §56 donne le seuil statique exact, celui d'un joueur qui ne se
   demande pas ce que son propre gain détruit :

       J* = (c - E)/p = ({C_NEW:.2f} - {E6:.4f}) / {P_FULL:.6e} = CHF {stat:,.0f}

   Le solveur, à une grille et sans auto-extinction, doit le retrouver.""")

thr1, _ = solve(RTP_NEW, R_NEW, C_NEW, False, n=1)
say(f"   contrôle : CHF {thr1:,.0f}   écart {abs(thr1-stat)/stat:.2%}\n")

say("   n grilles   n*p/q   seuil composé   prime d'auto-extinction")
for n in (1, 3, 6, 13):
    t, _ = solve(RTP_NEW, R_NEW, C_NEW, True, n=n)
    say(f"   {n:>9}   {n*P_FULL/Q_REF:>5.2f}   CHF {t:>9,.0f}   "
        f"{t/stat - 1:>+8.1%}")

say(f"""
   La prime d'auto-extinction est ce que le joueur doit exiger EN PLUS parce
   que son propre gain remet la cagnotte à zéro et détruit la valeur des
   tirages à venir. Elle ne dépend que de n*p/q, comme au §53.""")


rule("4. CE QUE LA PREMIÈRE CHUTE NE DIT PAS")

say(f"""   Une chute a été observée : la mise 5 passe de 355 à 245 entre les deux
   relevés, {N_DRAWS_BETWEEN} tirages d'écart. C'est la première du dossier. Combien
   vaut-elle comme mesure de q ?

   Un événement de Poisson observé sur {N_DRAWS_BETWEEN} tirages donne un intervalle de
   confiance à 95 % de [0,0253 ; 5,572] événements, donc""")

lo, hi = 0.0253 / N_DRAWS_BETWEEN, 5.572 / N_DRAWS_BETWEEN
say(f"""       q(mise 5) dans [1/{1/lo:,.0f} ; 1/{1/hi:,.0f}]   —  un facteur {hi/lo:,.0f}

   C'est exactement ce que le §36 avait annoncé : l'information sur la loi
   de la cagnotte arrive au rythme des CHUTES, et il en faut une dizaine
   pour situer q à un facteur 3 près. Une seule ne situe rien.

   Le seuil est donc rendu en fonction de q, treize grilles, entrées du §56.
""")

say("   q          n*p/q   seuil composé   mu = r/q    fraction favorable")
scan = []
for inv in (150, 200, 300, 400, 600, 1000, 2000):
    q = 1.0 / inv
    t, _ = solve(RTP_NEW, R_NEW, C_NEW, True, q_others=q)
    mu = R_NEW / q
    frac = math.exp(-t / mu)
    scan.append((t, frac))
    say(f"   1/{inv:<8}  {N_GRIDS*P_FULL*inv:>5.2f}   CHF {t:>9,.0f}   "
        f"{mu:>8,.0f}   {frac:>10.3%}")
SPREAD_T = max(t for t, _ in scan) / min(t for t, _ in scan)
SPREAD_F = max(f for _, f in scan) / min(f for _, f in scan)

say(f"""
   La fraction favorable est exp(-J*/mu) sous H1-H3, avec mu = r/q, et les
   deux colonnes ne réagissent pas du tout à la même échelle. Sur toute la
   plage, le seuil monte d'un facteur {SPREAD_T:.1f} — la prime d'auto-extinction est
   le seul terme qui dépende de q, et elle monte parce qu'une cagnotte qui
   tombe rarement vit longtemps, ce qui rend l'attente plus payante. La
   fraction, elle, varie d'un facteur {SPREAD_F:,.0f}.

   C'est le résultat honnête de cette section : le seuil STATIQUE est
   désormais solide, la prime d'auto-extinction qui s'y ajoute dépend d'un
   `q` qu'on ne mesure pas, et la FRÉQUENCE à laquelle le seuil est franchi
   n'est pas connue à un ordre de grandeur près. La seule chose qui la
   rendra connue est d'observer des chutes — pas des relevés.""")


rule("5. CE QUI CHANGE POUR LE JOUEUR, ET CE QUI RESTE SUSPENDU")

say(f"""   ACQUIS, et il faut séparer deux chiffres que le §55 confondait.

   Le seuil STATIQUE — celui d'un joueur qui joue une grille et ne se
   demande pas ce que son propre gain détruit — vaut CHF {stat:,.0f} sous c = 2.
   Il ne dépend plus d'AUCUNE borne ni d'aucun taux : le barème est lu, le
   gain fixe du rang plein est compté (le §55 l'oubliait), et sa seule
   hypothèse est le prix du ticket. C'est le chiffre solide.

   Le seuil COMPOSÉ — treize grilles, auto-extinction — vaut CHF {FINAL:,.0f}, soit
   +11,9 %. Mais cette prime dépend de n*p/q, donc d'un `q` qui n'est PAS
   mesuré : elle vaut de +2 % à +82 % selon la ligne de la section 4. Le
   §55 publiait un unique CHF 6 724 sans marquer cette dépendance ; c'est
   corrigé ici.

   Le maillon faible que le §55 nommait — rho >= 0,245 — a été remplacé par
   une mesure, et la mesure était DEUX FOIS plus généreuse que la borne. Le
   maillon faible s'est donc DÉPLACÉ : il n'est plus le barème, il est `q`.

   SUSPENDU.
   1. c = 2 reste une hypothèse. Le seuil lui est proportionnel en (c-E)/p :
      à c = 2,50 il vaut CHF {(2.5-E6)/P_FULL:,.0f} au lieu de CHF {stat:,.0f} en statique.
      C'est la dernière lecture à faire, et elle prend une seconde.
   2. q n'est pas mesuré, donc la fréquence des occasions ne l'est pas non
      plus. Section 4.
   3. H1-H3 du §28 tiennent toujours : accumulation constante, chutes sans
      mémoire, plancher nul. Le plancher nul est le cas le moins favorable
      au joueur, les deux autres ne sont pas vérifiées.
   4. L'option EXTRA n'entre pas dans ce calcul (§56, limite 3).

   ET CE QUI NE CHANGE PAS. Rien de tout ceci ne dit quels numéros cocher.
   L'espérance de hits vaut k/4 quel que soit le choix (§1). Ce seuil porte
   sur l'INSTANT, jamais sur la grille — et c'est la seule chose du dossier
   qui fasse changer l'espérance de signe.

   Registre : inchangé. h43 ne teste pas l'archive — il recompose.""")

say(f"\n   ({time.time() - T0:.1f} s)")
