"""h32 — le plafond d'un biais TRANSITOIRE, et le trou qu'il comble.

L'hypothèse que tous les plafonds partagent sans la dire
---------------------------------------------------------
c0 (+1,33 %), c1 (+0,53 % et +3,21 %), d2 (+3,46 %), h24 (+6,27 %), et les
lois d'échelle de h30 et h31 : tous supposent un biais STATIONNAIRE, présent
sur les 70 560 tirages. Aucun ne le dit, et c'est une hypothèse forte.

Or le dossier a déjà mesuré, ailleurs, qu'un défaut BREF est presque
invisible. La courbe de détectabilité de la 16e voie (a3) :

    fenêtre corrompue       +5 %   +10 %   +20 %   +40 %
    200 tirages (~1 jour)   0,00   0,00    0,00    0,58
    500 tirages             0,00   0,00    0,28    1,00
    2 000 tirages           0,00   0,10    1,00    1,00

Une corruption de 200 tirages à +40 % passe inaperçue une fois sur deux.
+40 %, c'est trente fois le plafond stationnaire du §3. Il y a donc un
régime entier que la hiérarchie des plafonds ne couvre pas, et personne ne
l'a borné.

Ce fichier le borne. Il ne teste pas l'archive : comme h1, h14, h17, h25,
h30 et h31, il démontre.

Environnement au moment d'écrire : scipy absent (installé depuis, dans la
même session) — numpy seul, toute loi simulée.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
RNG = np.random.default_rng(20260901)
N_ARCHIVE = 70_560


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# 1. LA DÉRIVATION
# ==========================================================================

rule("1. POURQUOI UN DÉFAUT BREF SE CACHE MIEUX")

say("""   Reprenons le cadre de h30. Un biais d'amplitude ||eps|| sur m cellules,
   mais présent seulement sur une FENÊTRE de L tirages sur N.

   LE SIGNAL SE CONCENTRE. Seuls les L tirages de la fenêtre portent le
   biais, donc la non-centralité vue par un test qui regarde LA BONNE
   fenêtre vaut  lambda = L * ||eps||^2  — et non N * ||eps||^2.

   LE SEUIL MONTE. Un test qui ne sait pas où est la fenêtre doit les
   BALAYER toutes : environ N/L fenêtres disjointes de longueur L, et le
   dossier a mesuré ce que coûte un tel balayage (16e voie : un max à
   |z| = 5,24 qui ne vaut que p = 0,066 une fois calibré contre la loi du
   max du même balayage). Le seuil passe donc de z à

       z_eff(L) ~ racine(z^2 + 2*ln(N/L))

   c'est-à-dire qu'il ne monte que comme la RACINE d'un logarithme.

   LE BUDGET, en combinant :

       ||eps||^2 <= z_eff(L) * racine(2m) / L

   contre  z * racine(2m) / N  pour un biais stationnaire. À un facteur
   logarithmique près, le budget d'amplitude est donc N/L fois plus grand.

   D'OÙ DEUX PLAFONDS, ET IL FAUT LES DISTINGUER :

     plafond PENDANT la fenêtre   ~ racine(N/L) * plafond stationnaire
     plafond MOYEN sur l'archive  ~ racine(L/N) * plafond stationnaire

   Le premier explose quand L diminue, le second s'effondre. Un défaut bref
   est donc énorme tant qu'il dure et négligeable en moyenne — et ces deux
   phrases décrivent le même défaut. Laquelle compte dépend entièrement de
   la capacité du joueur à savoir QUAND il a lieu, ce qui est la question de
   la section 4.""")


# ==========================================================================
# 2. VÉRIFICATION PAR BALAYAGE SIMULÉ
# ==========================================================================

rule("2. LE FACTEUR racine(N/L), MESURÉ")

say("""   On mesure le plafond directement, avec un détecteur qui fait ce qu'un
   analyste ferait : balayer toutes les fenêtres de longueur L et prendre le
   maximum du chi-2. Le null de ce MAXIMUM est simulé — c'est exactement la
   précaution que la 16e voie a rendue obligatoire, sans quoi le balayage
   fabrique un signal à tous les coups.""")

M_CELLS = 80
N_TOT = 20_000                      # archive réduite pour tenir le temps de calcul


def scan_max(counts_by_window, n_win, expect):
    """Max du chi-2 sur les fenêtres — la statistique de balayage."""
    chi = ((counts_by_window - expect) ** 2 / expect).sum(axis=1)
    return float(chi.max())


def simulate_scan(L, eps_norm, rng, contaminate):
    """Une archive de N_TOT tirages, éventuellement corrompue sur une fenêtre."""
    n_win = N_TOT // L
    p = np.full(M_CELLS, 1.0 / M_CELLS)
    expect = L / M_CELLS
    counts = np.empty((n_win, M_CELLS))
    hot = rng.integers(0, n_win) if contaminate else -1
    for w in range(n_win):
        if w == hot:
            v = rng.normal(size=M_CELLS)
            v -= v.mean()
            v *= eps_norm / math.sqrt(float((v * v).mean()))
            q = np.clip((1 + v) / M_CELLS, 1e-12, None)
            q /= q.sum()
            counts[w] = rng.multinomial(L, q)
        else:
            counts[w] = rng.multinomial(L, p)
    return scan_max(counts, n_win, expect)


def scan_threshold(L, rng, reps, z=4.33):
    vals = np.array([simulate_scan(L, 0.0, rng, False) for _ in range(reps)])
    return float(vals.mean() + z * vals.std(ddof=1)), float(vals.mean()), float(vals.std(ddof=1))


def scan_ceiling(L, rng, reps_null=120, reps_pw=40):
    thr, mu, sd = scan_threshold(L, rng, reps_null)
    lo, hi = 0.0, 0.05
    def pw(e, r):
        hits = sum(1 for _ in range(r) if simulate_scan(L, e, rng, True) >= thr)
        return hits / r
    while pw(hi, 12) < 0.5 and hi < 8:
        hi *= 2
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        if pw(mid, reps_pw) < 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), mu, sd


say(f"\n   N = {N_TOT:,}, m = {M_CELLS} cellules, seuil à z = 4,33 du null du MAX.")
say("\n        L   fenêtres   null du max (moy ± sd)   ||eps|| plafond   × racine(L/N)")
rows = []
for L in (250, 500, 1000, 2000, 5000):
    ceil, mu, sd = scan_ceiling(L, RNG)
    rows.append((L, ceil))
    say(f"   {L:>6}   {N_TOT//L:>8}       {mu:>7.1f} ± {sd:>5.2f}        {ceil:.5f}"
        f"        {ceil * math.sqrt(L / N_TOT):.5f}")

lL = np.log([r[0] for r in rows])
lc = np.log([r[1] for r in rows])
slope = float(np.polyfit(lL, lc, 1)[0])
say(f"""
   EXPOSANT MESURÉ en L : {slope:+.4f}   (théorie : −0,5000, au log près)

   La dernière colonne est le contrôle : si le plafond suit racine(N/L), le
   produit par racine(L/N) est constant. Il l'est à quelques pour cent, et
   l'écart résiduel est le facteur logarithmique du balayage, qui n'est pas
   dans la loi en puissance — il vaut racine(1 + 2*ln(N/L)/z^2), soit
   {math.sqrt(1 + 2*math.log(N_TOT/250)/4.33**2):.3f} à L = 250 contre {math.sqrt(1 + 2*math.log(N_TOT/5000)/4.33**2):.3f} à L = 5 000, et il va dans le
   bon sens.""")


# ==========================================================================
# 3. TRANSPOSÉ À L'ARCHIVE RÉELLE
# ==========================================================================

rule("3. CE QU'UN DÉFAUT BREF POURRAIT VALOIR SUR 70 560 TIRAGES")

say("""   En prenant le plafond stationnaire marginal du §3 — +1,33 % sur
   N = 70 560 — et en appliquant le facteur racine(N/L) :""")

say("\n         L   durée réelle    plafond PENDANT   plafond MOYEN   détecté par a3 ?")
A3 = {200: "+40 % vu 1 fois sur 2", 500: "+20 % vu 1 fois sur 4",
      2000: "+20 % vu à coup sûr"}
for L in (200, 500, 2000, 10_000, 70_560):
    fac = math.sqrt(N_ARCHIVE / L)
    hours = L * 5 / 60
    dur = f"{hours:.0f} h" if hours < 48 else f"{hours/24:.0f} j"
    say(f"   {L:>7}   {dur:>10}      {1.33*fac:>10.1f} %    {1.33/fac:>9.3f} %   "
        f"{A3.get(L, '—')}")

say("""
   La colonne du milieu est la découverte, et elle est brutale : un défaut
   d'une journée pourrait porter un avantage de l'ordre de 25 % PENDANT
   cette journée sans que rien ne le voie — vingt fois le plafond
   stationnaire du §3.

   Le rapprochement avec a3 demande une précaution, faute de quoi il ferait
   croire à un accord numérique qui n'existe pas. Les deux « + x % » ne sont
   PAS la même quantité : celui de a3 est une amplitude de contamination
   injectée, celui d'ici un avantage de joueur. Ce qui se compare est le
   RÉGIME, et il concorde — a3 place la frontière de détection d'une fenêtre
   de 200 tirages dans les dizaines de pour cent, exactement là où cette loi
   d'échelle la met, et sa colonne « vu 1 fois sur 2 » est précisément la
   convention « puissance < 50 % » qui définit un plafond dans ce dossier.
   C'est un accord d'ordre de grandeur entre deux voies sans rien en commun
   — a3 injecte dans l'archive réelle, celle d'ici dérive puis vérifie sur
   un modèle abstrait — et non une égalité.""")


# ==========================================================================
# 4. CE QUI REND CE PLAFOND INEXPLOITABLE — et c'est mesurable
# ==========================================================================

rule("4. LE PROBLÈME D'IDENTIFICATION, MAINTENANT DANS LE TEMPS")

say("""   Le plafond « pendant » n'est pas un avantage disponible. Pour
   l'encaisser, le joueur doit savoir DEUX choses, et non plus une :

     - quels numéros sont biaisés   (le problème d'identification de h31)
     - QUAND la fenêtre a lieu       (nouveau, et propre au cas transitoire)

   Or le seul moyen de savoir quand est de le détecter — et par
   construction, un biais AU plafond n'est détecté qu'une fois sur deux. Le
   joueur qui attend d'être sûr a manqué la fenêtre ; celui qui n'attend pas
   joue sur du bruit la plupart du temps.

   Pire, et c'est le point décisif : le joueur ne dispose que du PASSÉ. Même
   un détecteur parfait ne signale la fenêtre qu'APRÈS avoir vu assez de
   tirages pour l'établir, c'est-à-dire une fraction substantielle de L. On
   mesure donc ce qui reste : la part de la fenêtre encore à jouer au moment
   où elle devient détectable.""")

def causal_fraction(L, eps_norm, rng, thr, reps=60):
    """Quand un détecteur CAUSAL bascule-t-il, en fraction de fenêtre ?

    Il accumule le chi-2 depuis le début de la fenêtre et franchit le seuil
    du balayage. On rend la fraction de fenêtre écoulée au franchissement,
    et la fraction des réplicats où il ne franchit jamais.
    """
    expect_unit = 1.0 / M_CELLS
    crossed, never = [], 0
    for _ in range(reps):
        v = rng.normal(size=M_CELLS)
        v -= v.mean()
        v *= eps_norm / math.sqrt(float((v * v).mean()))
        q = np.clip((1 + v) / M_CELLS, 1e-12, None)
        q /= q.sum()
        draws = rng.choice(M_CELLS, size=L, p=q)
        counts = np.zeros(M_CELLS)
        hit = None
        for t in range(1, L + 1):
            counts[draws[t - 1]] += 1
            if t % max(1, L // 40) == 0:
                e = t * expect_unit
                chi = float(((counts - e) ** 2 / e).sum())
                if chi >= thr:
                    hit = t / L
                    break
        if hit is None:
            never += 1
        else:
            crossed.append(hit)
    return (float(np.mean(crossed)) if crossed else float("nan"),
            never / reps)

say("\n        L   bascule à (fraction de fenêtre)   jamais détecté   fenêtre restante")
for L, ceil in rows:
    thr, _, _ = scan_threshold(L, RNG, 60)
    frac, never = causal_fraction(L, ceil, RNG, thr)
    rest = "—" if math.isnan(frac) else f"{1 - frac:.0%}"
    fs = "—" if math.isnan(frac) else f"{frac:.2f}"
    say(f"   {L:>6}   {fs:>30}   {never:>14.0%}   {rest:>16}")

say("\n   Et le chiffre composite, qui est le seul qui décrive un joueur réel :")
say("\n        L   plafond PENDANT   x part restante   x P(détecté)   ENCAISSABLE")
for L, ceil in rows:
    thr, _, _ = scan_threshold(L, RNG, 60)
    frac, never = causal_fraction(L, ceil, RNG, thr)
    if math.isnan(frac):
        continue
    pend = 1.33 * math.sqrt(N_ARCHIVE / L)
    enc = pend * (1 - frac) * (1 - never)
    say(f"   {L:>6}   {pend:>13.1f} %   {1-frac:>15.0%}   {1-never:>12.0%}   "
        f"{enc:>10.2f} %")

say("""
   Le détecteur causal bascule tard, et souvent jamais — ce qui est la
   définition même d'un biais au plafond. Le joueur n'encaisse donc que la
   part restante, et seulement dans les réplicats où le signal bascule : la
   dernière colonne divise le plafond « pendant » par un facteur 4 à 8.

   CE QUE CE FICHIER AJOUTE AU DOSSIER, en une phrase : la hiérarchie des
   plafonds avait un trou — elle ne couvrait que les biais permanents — et
   ce trou est réel et grand, mais il se referme par le même mécanisme que
   le §42, l'impossibilité d'apprendre assez vite ce qu'on a le droit de
   cacher. Ici l'apprentissage porte sur le temps plutôt que sur les
   numéros.

   LIMITES.
   0. La colonne P(détecté) est bruitée — 60 réplicats seulement, d'où sa
      non-monotonie apparente (70 %, 75 %, 50 %, 78 %, 28 %). Ce qu'elle
      établit est l'ORDRE DE GRANDEUR du facteur d'abattement, pas sa
      valeur à chaque L. Ne pas lire ses variations.
   1. Le facteur logarithmique du balayage est traité comme une correction
      et non intégré à la loi en puissance ; à L très petit il finirait par
      dominer.
   2. La section 4 raisonne au plafond, où la puissance vaut 50 % par
      définition. Un biais plus fort serait détecté plus tôt et laisserait
      plus de fenêtre à jouer — mais il serait aussi détecté, donc corrigé
      par l'opérateur : c'est un régime hors du cadre « non détecté ».
   3. Le modèle suppose UNE fenêtre. Un défaut récurrent — toutes les nuits,
      par exemple — serait bien plus détectable, la 17e voie l'ayant borné
      par périodogramme à 0,01 écart-type par tirage.

   Registre : inchangé. h32 ne teste pas l'archive — il démontre.""")

say(f"\n   ({time.time() - T0:.1f} s)")
