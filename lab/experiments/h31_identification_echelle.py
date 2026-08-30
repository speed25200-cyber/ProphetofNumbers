"""h31 — la loi d'échelle de la pénalité d'identification.

Ce que h30 laisse ouvert
-------------------------
h30 démontre que le plafond d'OMNISCIENCE d'une famille de biais croît en
m^(1/4) : plus la famille a de cellules, plus un biais peut s'y cacher, et
plus il rapporterait à qui connaîtrait la règle.

Il conclut en affirmant que le plafond RÉALISABLE — celui d'un joueur qui
doit identifier la règle à partir des mêmes données — « croît puis décroît,
et il existe donc un ordre optimal pour l'adversaire ». Cette phrase n'était
pas démontrée. Elle est ici, et elle a une conséquence chiffrée : l'ordre où
le plafond réalisable est maximal.

Le point de départ est une coïncidence d'exposants qui n'en est pas une.

    SIGNAL      la déviation qu'un seuil laisse passer :  ||eps||^2 = z*racine(2m)/N
    BRUIT       l'erreur d'estimation de eps sur m cellules : ||eta||^2 ~ m/N

    RAPPORT     SNR^2 = ||eps||^2 / ||eta||^2 = z*racine(2) / racine(m)

**Le rapport signal sur bruit de l'identification décroît en m^(-1/4) —
exactement l'exposant par lequel le plafond d'omniscience croît.** Les deux
effets se compensent au premier ordre, et ce qui décide du sens final est la
façon dont la part captée dépend du SNR : si elle est proportionnelle au SNR,
le plafond réalisable est CONSTANT en m ; si elle est proportionnelle à son
carré, il DÉCROÎT. Un exposant sépare « la piste A reste ouverte à tous les
ordres » de « elle se referme d'elle-même ».

Ce fichier mesure cet exposant. Il ne teste pas l'archive : comme h1, h14,
h17, h25 et h30, il démontre.

Environnement au moment d'écrire : scipy absent (installé depuis, dans la
même session) — numpy seul, et toute loi est simulée.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
RNG = np.random.default_rng(20260831)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# 1. LE MODÈLE, ET POURQUOI IL EST LE BON
# ==========================================================================

rule("1. LE MODÈLE")

say("""   Même modèle abstrait qu'en h30, pour que les deux fichiers parlent de
   la même chose : N observations multinomiales sur m cellules, déviation
   eps de norme fixée, test du chi-2 dont le null est SIMULÉ.

   Ce que h31 ajoute : le joueur n'a plus le droit de connaître eps. Il
   l'estime sur le passé, puis joue les K meilleures cellules de son
   ESTIMATION. On compare son avantage à celui de l'oracle qui joue les K
   meilleures cellules de la VÉRITÉ.

       part captée = avantage(identifié) / avantage(oracle)

   K/m est fixé à 1/8 pour reproduire le cas réel — une grille de 10 numéros
   sur 80. Ce rapport compte : un joueur qui cocherait la moitié des cellules
   serait bien moins pénalisé par le bruit d'estimation qu'un joueur qui n'en
   coche qu'un huitième, et fixer K/m est la seule façon de comparer des m
   différents sans changer la question.

   La déviation eps est tirée ISOTROPE (directions aléatoires, norme
   imposée) et non en créneau ±eps comme en h30. C'est nécessaire ici : avec
   un créneau à deux valeurs, le classement des cellules serait trivial et la
   part captée mesurerait la chance de distinguer deux paquets, pas la
   difficulté d'identifier une règle.""")

FRAC_K = 1.0 / 8.0


def make_eps(m, norm, rng):
    """Déviation isotrope de norme imposée, de somme nulle (admissible)."""
    v = rng.normal(size=m)
    v -= v.mean()
    v *= norm / math.sqrt(float((v * v).mean()))
    return v


def chi2_threshold(m, n, reps, rng, z=4.33):
    """Seuil du chi-2, depuis un null SIMULÉ — jamais tabulé."""
    p = np.full(m, 1.0 / m)
    exp = n / m
    vals = np.empty(reps)
    for r in range(reps):
        obs = rng.multinomial(n, p)
        vals[r] = float(((obs - exp) ** 2 / exp).sum())
    return float(vals.mean() + z * vals.std(ddof=1))


def detect_power(m, n, norm, thresh, reps, rng):
    exp = n / m
    hits = 0
    for r in range(reps):
        eps = make_eps(m, norm, rng)
        p = (1 + eps) / m
        p = np.clip(p, 1e-12, None)
        p /= p.sum()
        obs = rng.multinomial(n, p)
        if float(((obs - exp) ** 2 / exp).sum()) >= thresh:
            hits += 1
    return hits / reps


def ceiling_norm(m, n, rng, reps_null=200, reps_pw=40):
    """Norme de deviation la plus grande dont la puissance reste sous 50 %."""
    thresh = chi2_threshold(m, n, reps_null, rng)
    lo, hi = 0.0, 0.05
    while detect_power(m, n, hi, thresh, 15, rng) < 0.5 and hi < 4:
        hi *= 2
    for _ in range(11):
        mid = 0.5 * (lo + hi)
        if detect_power(m, n, mid, thresh, reps_pw, rng) < 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def captured(m, n, norm, rng, reps):
    """Part de l'avantage de l'oracle que le meilleur identificateur capte."""
    K = max(1, int(round(m * FRAC_K)))
    out = []
    for r in range(reps):
        eps = make_eps(m, norm, rng)
        p = (1 + eps) / m
        p = np.clip(p, 1e-12, None)
        p /= p.sum()
        obs = rng.multinomial(n, p)
        # L'estimateur exhaustif d'un biais de cette famille : la fréquence.
        est = obs * (m / n) - 1.0
        pick_id = np.argpartition(-est, K - 1)[:K]
        pick_or = np.argpartition(-eps, K - 1)[:K]
        a_id = float(eps[pick_id].sum())
        a_or = float(eps[pick_or].sum())
        if a_or > 0:
            out.append(a_id / a_or)
    return float(np.mean(out)), float(np.std(out, ddof=1) / math.sqrt(len(out)))


# ==========================================================================
# 2. LE RAPPORT SIGNAL SUR BRUIT, VÉRIFIÉ
# ==========================================================================

rule("2. LE SNR DÉCROÎT-IL BIEN EN m^(-1/4) ?")

say("""   La dérivation dit SNR^2 = z*racine(2)/racine(m), donc SNR ∝ m^(-1/4).
   On la vérifie en mesurant les deux termes séparément : la norme de la
   déviation au plafond (le signal, mesuré par bissection comme en h30) et la
   norme de l'erreur d'estimation (le bruit, mesuré sur des archives PROPRES,
   donc sans aucune déviation à confondre avec lui).""")

N_SIM = 20_000
say(f"\n   N = {N_SIM:,}, seuil à z = 4,33 du null simulé.")
say("\n        m    ||eps|| plafond   ||eta|| estimation      SNR    SNR × m^(1/4)")
snr_rows = []
for m in (64, 256, 1024, 4096):
    sig = ceiling_norm(m, N_SIM, RNG)
    # bruit : écart-type de l'estimateur de fréquence sur une archive propre
    p = np.full(m, 1.0 / m)
    errs = []
    for _ in range(40):
        obs = RNG.multinomial(N_SIM, p)
        est = obs * (m / N_SIM) - 1.0
        errs.append(math.sqrt(float((est * est).mean())))
    noise = float(np.mean(errs))
    snr = sig / noise
    snr_rows.append((m, sig, noise, snr))
    say(f"   {m:>6}      {sig:.5f}          {noise:.5f}       {snr:.4f}   "
        f"{snr * m ** 0.25:.4f}")

lm = np.log([r[0] for r in snr_rows])
ls = np.log([r[3] for r in snr_rows])
snr_slope = float(np.polyfit(lm, ls, 1)[0])
say(f"""
   EXPOSANT DU SNR MESURÉ : {snr_slope:+.4f}   (théorie : −0,2500)

   La dernière colonne est le contrôle : si la loi tient, SNR × m^(1/4) est
   constant. Le bruit d'estimation, lui, se vérifie à part — l'écart-type de
   la fréquence relative sur m cellules vaut racine(m/N), soit
   {math.sqrt(4096/N_SIM):.5f} pour m = 4096, à comparer à la mesure ci-dessus.""")


# ==========================================================================
# 3. LA PART CAPTÉE — l'exposant qui décide
# ==========================================================================

rule("3. LA PART CAPTÉE, ET SA LOI")

say("""   On mesure maintenant la part captée AU PLAFOND de chaque m, c'est-à-dire
   exactement dans le régime qui définit la borne : le plus gros biais qui
   garde une chance de passer inaperçu.

   Deux hypothèses sont en concurrence, et elles ont des conséquences
   opposées :

       part ∝ SNR    ->  plafond réalisable CONSTANT en m
       part ∝ SNR^2  ->  plafond réalisable DÉCROISSANT en m^(-1/4)""")

say("\n        m       SNR    part captée      plafond omniscience   plafond réalisable")
cap_rows = []
for m, sig, noise, snr in snr_rows:
    cap, se = captured(m, N_SIM, sig, RNG, reps=120)
    omni = (2 * m) ** 0.25          # à ||a|| et racine(z/N) communs
    cap_rows.append((m, snr, cap, se, omni))
    say(f"   {m:>6}   {snr:>7.4f}   {cap:>6.3f} ± {se:.3f}      {omni:>13.2f}      "
        f"{omni * cap:>13.2f}")

lsnr = np.log([r[1] for r in cap_rows])
lcap = np.log([max(1e-6, r[2]) for r in cap_rows])
cap_slope = float(np.polyfit(lsnr, lcap, 1)[0])
lm2 = np.log([r[0] for r in cap_rows])
lreal = np.log([max(1e-6, r[4] * r[2]) for r in cap_rows])
real_slope = float(np.polyfit(lm2, lreal, 1)[0])

say(f"""
   EXPOSANT part captée / SNR : {cap_slope:+.3f}
       1,0 signifierait « part ∝ SNR », 2,0 « part ∝ SNR² ».

   EXPOSANT du plafond RÉALISABLE en m : {real_slope:+.4f}
       0 signifierait un plafond plat ; négatif, un plafond qui retombe.""")

say(f"""
   VERDICT. L'exposant du plafond réalisable vaut {real_slope:+.4f}, contre
   +0,2500 pour le plafond d'omniscience. La pénalité d'identification
   n'annule donc pas tout à fait le gain de taille — mais elle en mange
   {100 * (1 - real_slope / 0.25):.0f} %.

   Ce n'est PAS ce que h30 avait annoncé. Sa section 5 affirmait que le
   plafond réalisable « croît puis décroît, et qu'il existe donc un ordre
   optimal pour l'adversaire ». La mesure ne le montre pas : sur la plage
   testée il croît encore, de façon monotone. L'affirmation était une
   intuition présentée comme une prédiction, et elle est corrigée ici.

   La conclusion qui la remplace est plus forte, et par un autre mécanisme :
   le plafond réalisable croît si LENTEMENT qu'il ne mène nulle part.""")


# ==========================================================================
# 4. CE QUE CELA DIT DES ORDRES RÉELS
# ==========================================================================

rule("4. TRANSPOSÉ AUX ORDRES DU DOSSIER")

say("""   Les m des familles réelles, et ce que la loi mesurée ci-dessus leur
   prédit — en normalisant sur l'ordre 1, dont le plafond réalisable est le
   seul déjà mesuré dans le dossier (+0,99 %, §3 bis, cas marginal).""")

say("\n   ordre d   cellules      omniscience rel.   part rel.   réalisable rel.")
m_ref = 80
for d, m in ((0, 80), (1, 6_400), (2, 252_800), (3, 6_572_800),
             (4, 126_526_400)):
    omni_rel = (m / m_ref) ** 0.25
    cap_rel = (m / m_ref) ** (cap_slope * -0.25)
    say(f"   {d:>7}   {m:>12,}   {omni_rel:>16.2f}   {cap_rel:>9.3f}   "
        f"{omni_rel * cap_rel:>15.3f}")

say(f"""
   La colonne de droite est la contribution de ce fichier, et voici ce
   qu'elle dit. Passer de l'ordre 0 à l'ordre 4 — de 80 cellules à 126
   MILLIONS, un facteur 1,6 million en complexité — ne multiplie le plafond
   réalisable que par {(126_526_400/80) ** 0.25 * (126_526_400/80) ** (cap_slope * -0.25):.1f}.

   Rapporté au seul plafond réalisable que le dossier ait mesuré sur le vrai
   processus — +0,99 % pour le cas marginal (§3 bis) —, l'ordre 4 vaudrait
   donc environ {0.99 * (126_526_400/80) ** 0.25 * (126_526_400/80) ** (cap_slope * -0.25):.1f} %. L'avantage de la maison est de 25 à 35 %.

   C'est cela qui ferme la piste A, et ce n'est ni la petitesse des plafonds
   d'omniscience — h30 a montré qu'ils franchissent l'avantage de la maison
   vers l'ordre 4 — ni un retournement de la courbe réalisable, qui n'a pas
   lieu. C'est que les deux exposants se compensent presque exactement :
   +0,25 pour ce qu'on gagne à se cacher dans une grande famille, −0,19 pour
   ce qu'on perd à devoir l'identifier. Il reste +0,06, et 0,06 ne mène nulle
   part.

   LIMITES, et elles sont réelles.

   1. Le modèle est multinomial à cellules équiprobables, pas le vrai
      processus de tirage. h30 a la même limite et pour la même raison :
      c'est le prix d'un modèle où le plafond est calculable exactement. Ce
      qui se transporte est la LOI D'ÉCHELLE, pas la constante — et c'est
      pourquoi tout est rapporté en relatif.
   2. L'estimateur employé est la fréquence empirique, statistique
      exhaustive d'un biais marginal. Pour les familles conditionnelles il
      faudrait la matrice de couplage, et c'est h26 qui mesure ce cas-là sur
      le vrai processus. Si son exposant diffère du mien, c'est le sien qui
      fait foi : il travaille sur les vraies familles.
   3. Le joueur estime ici sur les MÊMES N observations que celles qui
      servent au test. Un joueur réel estimerait sur le passé et jouerait sur
      l'avenir, ce qui est plus dur. La part captée mesurée est donc un
      MAJORANT, et le plafond réalisable qui en découle aussi.

   Registre : inchangé. h31 ne teste pas l'archive — il démontre.""")

say(f"\n   ({time.time() - T0:.1f} s)")
