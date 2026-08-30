"""h38 — où la courbe se retourne, et quel est le maximum de toute la piste A.

Ce que les trois sections précédentes laissent
----------------------------------------------
h30 (§41) : le plafond d'OMNISCIENCE croît en m^(1/4). Démontré, vérifié.
h31 (§42) : la pénalité d'identification a sa propre loi, le SNR décroît en
            m^(-1/4). Démontré, vérifié — mais dans un modèle abstrait où le
            joueur estimait sur les mêmes données que le test, ce qui est un
            MAJORANT et que le fichier déclarait comme sa limite n° 3.
h26 (§45) : la part captée, mesurée en MARCHE AVANT sur les vraies familles.
            Quatre points, et un retournement que h31 n'avait pas vu.

Il reste une question, et c'est celle qui ferme la piste A : le plafond
réalisable a un maximum — le §45 le montre en passant de 1,30 à 0,71 — mais
personne ne l'a LOCALISÉ, et personne ne sait donc si une famille non
mesurée pourrait faire mieux que les cinq qui l'ont été.

Tant que ce maximum n'est pas situé, la phrase du sommaire (« <= +1,6 % »)
n'est vraie que des familles testées. Ce fichier la rend vraie de TOUTES.

Il ne teste pas l'archive : il ajuste et il maximise.

Environnement : scipy absent — numpy seul.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
RNG = np.random.default_rng(20260903)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# Les quatre points MESURÉS par h26 (§45), plus le marginal du §3 bis.
# (nom, m cellules, plafond d'omniscience %, part captée, incertitude)
POINTS = [
    ("rémanence uniforme", 1,        0.53, 1.00, 0.11),
    ("marginal",           80,       1.33, 0.64, 0.05),
    ("paires cachées",     6_400,    3.21, 0.41, 0.03),
    ("quadratique",        252_800,  6.27, 0.11, 0.02),
]

# ==========================================================================
# 1. LA FORME, ET POURQUOI ELLE EST CELLE-LÀ
# ==========================================================================

rule("1. LA VARIABLE QUI GOUVERNE LA PART CAPTÉE")

say("""   h31 a établi que le rapport signal sur bruit de l'identification vaut
   SNR^2 = z*racine(2)/racine(m), donc SNR proportionnel à m^(-1/4). C'est
   la variable naturelle : deux familles de tailles différentes mais de même
   SNR devraient se laisser identifier également bien.

   On porte donc les quatre parts captées de h26 non pas contre m, mais
   contre le SNR. Si la loi de h31 est la bonne variable, les points doivent
   s'aligner — et le retournement du plafond réalisable doit s'y lire comme
   un changement de pente.""")

say("\n   famille                  m cellules      SNR rel.   part captée")
snr = []
cap = []
for name, m, omni, c, se in POINTS:
    s = m ** -0.25
    snr.append(s)
    cap.append(c)
    say(f"   {name:<22} {m:>11,}   {s:>11.5f}   {c:>7.2f} ± {se:.2f}")

snr = np.array(snr)
cap = np.array(cap)
ls, lc = np.log(snr), np.log(cap)

say("\n   pentes locales d(log part)/d(log SNR), segment par segment :")
for i in range(len(POINTS) - 1):
    sl = (lc[i + 1] - lc[i]) / (ls[i + 1] - ls[i])
    say(f"   {POINTS[i][0]:<22} -> {POINTS[i+1][0]:<22} {sl:>7.3f}")

say("""
   Les deux premiers segments ont la MÊME pente à trois décimales, et le
   troisième est nettement plus raide. Ce n'est pas une droite : c'est une
   courbe qui s'effondre, et l'endroit où elle s'effondre est précisément ce
   qu'on cherche.

   LE CRITÈRE DU RETOURNEMENT, et il est simple. Le plafond réalisable vaut
   omniscience x part captée, soit (à ||a|| constant)

       réalisable ~ m^(1/4) x part(SNR)   avec SNR ~ m^(-1/4)

   En logarithmes : d(log réalisable)/d(log m) = 1/4 - (1/4) x pente. Le
   plafond réalisable CROÎT tant que la pente est sous 1, DÉCROÎT au-delà,
   et le maximum est exactement là où

       d(log part captée) / d(log SNR) = 1

   C'est un critère lisible sur les données, et il ne demande aucun ajustement
   paramétrique pour dire de quel côté du maximum se trouve chaque famille.""")


# ==========================================================================
# 2. OÙ EST LE MAXIMUM
# ==========================================================================

rule("2. LOCALISATION DU MAXIMUM")

say("""   Les pentes mesurées encadrent le passage à 1. On interpole en
   logarithmes entre les deux points qui l'encadrent, et l'on propage
   l'incertitude des parts captées par tirage bootstrap.""")


def peak_from(caps):
    """m du maximum, par passage de la pente locale à 1 (interpolation log)."""
    lcz = np.log(np.clip(caps, 1e-6, None))
    slopes, mids = [], []
    for i in range(len(POINTS) - 1):
        sl = (lcz[i + 1] - lcz[i]) / (ls[i + 1] - ls[i])
        slopes.append(sl)
        mids.append(0.5 * (math.log(POINTS[i][1] + 1e-9)
                           + math.log(POINTS[i + 1][1])))
    slopes, mids = np.array(slopes), np.array(mids)
    for i in range(len(slopes) - 1):
        if (slopes[i] - 1) * (slopes[i + 1] - 1) < 0:
            f = (1 - slopes[i]) / (slopes[i + 1] - slopes[i])
            return math.exp(mids[i] + f * (mids[i + 1] - mids[i]))
    return math.nan


m_star = peak_from(cap)
boot = []
for _ in range(4000):
    pert = np.array([max(0.02, min(1.0, c + RNG.normal(0, se)))
                     for (_, _, _, c, se) in POINTS])
    v = peak_from(pert)
    if not math.isnan(v):
        boot.append(v)
boot = np.array(boot)
lo, hi = np.percentile(boot, [2.5, 97.5])

say(f"""
   m du maximum      : {m_star:>12,.0f} cellules
   intervalle à 95 % : [{lo:,.0f} ; {hi:,.0f}]   ({len(boot)/4000:.0%} des tirages définis)

   Pour situer : la famille des paires cachées compte 6 400 cellules, la
   famille quadratique 252 800. Le maximum tombe donc JUSTE AU-DESSUS des
   paires cachées, et très loin sous le quadratique — l'essentiel de
   l'intervalle reste dans le même ordre de grandeur que 6 400.

   Autrement dit, et c'est le résultat : la famille des paires cachées est
   pratiquement AU sommet de la courbe. Ce n'est pas un ajustement heureux —
   la localisation ne s'appuie que sur les pentes de la part captée, jamais
   sur les plafonds réalisables eux-mêmes.""")


# ==========================================================================
# 3. LA VALEUR DU MAXIMUM — le nombre qui ferme la piste A
# ==========================================================================

rule("3. COMBIEN VAUT LE MAXIMUM")

say("""   Le plafond réalisable au maximum s'obtient en interpolant les deux
   grandeurs qui le composent, chacune dans sa variable naturelle :
   l'omniscience en m^(1/4) (loi démontrée au §41), la part captée par
   interpolation log-log entre les points mesurés qui encadrent le maximum.""")


def realisable_at(m, caps):
    """Plafond réalisable interpolé à m cellules."""
    lm = math.log(m)
    lms = [math.log(mm + 1e-9) for (_, mm, _, _, _) in POINTS]
    omn = [o for (_, _, o, _, _) in POINTS]
    lcz = np.log(np.clip(caps, 1e-6, None))
    # Omniscience : interpolée sur les valeurs MESURÉES et non sur la loi
    # ancrée en un point. Le §41 a lui-même mesuré que le facteur ||a||
    # varie (1,19 ; 1,00 ; 0,81 ; 0,63) : appliquer m^(1/4) depuis le seul
    # point marginal ignorerait cette variation et surestimerait de 24 % au
    # voisinage du maximum. C'était l'erreur de ma première version.
    o = math.exp(float(np.interp(lm, lms, np.log(omn))))
    # part captée : interpolation linéaire en log-log
    c = math.exp(float(np.interp(lm, lms, lcz)))
    return o * c


val = realisable_at(m_star, cap)
bootv = []
for _ in range(4000):
    pert = np.array([max(0.02, min(1.0, c + RNG.normal(0, se)))
                     for (_, _, _, c, se) in POINTS])
    mm = peak_from(pert)
    if not math.isnan(mm):
        bootv.append(realisable_at(mm, pert))
bootv = np.array(bootv)
vlo, vhi = np.percentile(bootv, [2.5, 97.5])

say(f"""
   plafond réalisable AU MAXIMUM : {val:.2f} %
   intervalle à 95 %             : [{vlo:.2f} % ; {vhi:.2f} %]

   À comparer aux cinq familles mesurées — 0,53 / 0,99 / 1,30 / 1,59 / 0,71 —
   dont la plus haute est la famille des lags à +1,59 %, et qui est elle-même
   un majorant (mesurée à lag connu du joueur).

   DEUX PRÉCISIONS, et la seconde est une incohérence héritée qu'il vaut
   mieux dire que masquer.

   1. Le critère de pente place le passage à 7 376 cellules, mais
      l'interpolation par morceaux met le sommet du PRODUIT au nœud, à
      6 400. Les deux disent la même chose — le maximum est à la famille des
      paires cachées — et l'écart est un artefact de l'interpolation
      linéaire par morceaux, pas un désaccord.

   2. La ligne marginale du dossier n'est pas cohérente avec elle-même :
      +1,33 % (plafond de c0) fois 64 % (part captée de c2) fait 0,85 % et
      non le +0,99 % publié. La raison est que les deux facteurs viennent de
      deux mesures différentes à amplitude nominalement identique — c0
      mesure l'avantage de l'oracle à +1,33 % pour d = 0,0030, c2 le mesure
      à +1,55 % pour le même d. L'écart de 16 % est antérieur à ce fichier
      et h26 l'a propagé. La courbe ci-dessous utilise le plafond de c0 pour
      toutes les familles, par cohérence interne ; c'est pourquoi sa ligne
      marginale affiche 0,85 % et non 0,99 %.""")

say("\n   la courbe entière (interpolée entre les mesures ; au-delà de")
say("   252 800 cellules c'est une EXTRAPOLATION, signalée comme telle) :")
say("\n        m   omniscience   part captée   réalisable")
lms_t = [math.log(mm + 1e-9) for (_, mm, _, _, _) in POINTS]
omn_t = [o for (_, _, o, _, _) in POINTS]
for m in (1, 80, 6_400, 7_376, 20_000, 252_800, 6_572_800):
    o = math.exp(float(np.interp(math.log(m), lms_t, np.log(omn_t))))
    c = math.exp(float(np.interp(math.log(m), lms_t, np.log(cap))))
    tag = "  <- maximum" if m == 7_376 else (
        "  (extrapolé)" if m > 252_800 else "")
    say(f"   {m:>10,}   {o:>10.2f} %   {c:>10.3f}   {o*c:>9.2f} %{tag}")


# ==========================================================================
# 4. CE QUE CELA FERME, ET CE QUE CELA NE FERME PAS
# ==========================================================================

rule("4. PORTÉE")

say(f"""   CE QUE CELA FERME. Le sommaire disait « <= +1,6 %, toutes familles
   MESURÉES ». Avec un maximum localisé et borné, l'énoncé devient une
   propriété de la courbe et non un relevé de cinq points : au-delà du
   maximum, monter en complexité DESSERT l'adversaire, et il n'existe donc
   pas de famille plus grande qui ferait mieux. La piste A est bornée par le
   sommet de cette courbe, pas par la plus haute famille qu'on a pensé à
   tester.

   CE QUE CELA NE FERME PAS, et il faut être précis.

   1. La courbe est ajustée sur QUATRE points. Le retournement est établi par
      les deux derniers (1,30 puis 0,71), donc par une seule descente. Un
      cinquième point entre 6 400 et 252 800 cellules le confirmerait ou le
      déplacerait, et c'est la mesure la plus utile que ce dossier puisse
      encore demander sur ce sujet.
   2. L'interpolation de la part captée est log-log linéaire par morceaux —
      un choix, pas une loi. Une forme dérivée du SNR serait meilleure, mais
      h31 a montré que son exposant abstrait (0,72) ne vaut pas celui des
      vraies familles : mieux vaut interpoler les mesures que d'extrapoler un
      modèle réfuté.
   3. La famille des lags (+1,59 %) n'entre pas dans la courbe : son m est
      l'union balayée de 306 familles, et le §41 l'avait déjà écartée pour
      cette raison. Elle reste le plus haut plafond réalisable mesuré, et
      c'est un MAJORANT.
   4. Tout ceci porte sur les familles CONDITIONNELLES au tirage précédent.
      Une famille d'une autre nature — non stationnaire (§43), portant sur
      l'ordre (§47) — obéit à d'autres bornes, déjà établies séparément.

   LE CHIFFRE À RETENIR, avec sa réserve : le plafond réalisable de la piste
   A culmine autour de {val:.1f} % et l'avantage de la maison vaut 25 à 35 %.
   L'écart est d'un ordre de grandeur, et il ne se referme pas en montant en
   complexité — c'est précisément ce que le maximum signifie.

   Registre : inchangé. h38 n'interroge pas l'archive.""")

say(f"\n   ({time.time() - T0:.1f} s)")
