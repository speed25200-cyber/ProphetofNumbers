"""h25 — de quelle décision le paramètre α décide-t-il, au juste ?

Ce que le dossier laisse en suspens
------------------------------------
h16 (§29) établit une identité remarquable : en ne jouant qu'au-dessus du
seuil de bascule S = c/p, le rendement par franc misé vaut exactement
1 + μ/S, et le rapport μ/S est α — la part de la mise que l'opérateur verse
dans la cagnotte. Tous les nombres décisifs de §29, §30 et §31 sont
proportionnels à ce α.

Or α est estimé sur UN relevé, et son intervalle à 95 % va de +8 % à
+1 165 %. Le dossier en tire une demande de données, répétée trois fois :

    §28 : « Il faut une trentaine de relevés pour situer la fraction à un
           facteur 10 près, une centaine pour un facteur 3. »
    §29 : « Les trois se lèvent avec les mêmes données : une série de
           relevés, et le prix du ticket. »
    §31 : « Ces derniers nombres sont tous proportionnels à α, estimé sur
           UN relevé. »

Personne n'a posé la question d'avant : **α sert à décider quoi ?**

Une demande de données ne se justifie que par une décision qu'elle change.
Ce fichier fait donc trois choses, dans cet ordre :

  1. il inventorie les décisions que l'app propose réellement à son
     utilisateur, et regarde, pour chacune, si α y entre ;
  2. il vérifie par simulation les deux réponses non évidentes de cet
     inventaire, plutôt que de les déduire ;
  3. il chiffre le plan de relevés pour ce qui reste — et dit ce que ce
     plan achète, qui n'est pas ce que le dossier croyait.

Il ne teste pas l'archive. Comme h1, h14 et h17, il prouve et il corrige :
aucune entrée n'est ajoutée au registre.

Contrainte d'environnement au moment d'écrire ce fichier : scipy n'était
pas installé, et h16 — qui l'importe — n'était donc pas rejouable. Il l'a
été plus tard dans la même session par un autre travail ; la note est
gardée telle quelle, datée, plutôt que réécrite après coup. Rien ici n'en
dépend : tout ce qui suit tient en numpy et en
`math`, et chaque loi dont on a besoin est simulée plutôt que tabulée —
règle n° 1 du labo.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
DRAWS_PER_DAY = 204
STAKES = (5, 6, 7, 8, 10)
RNG = np.random.default_rng(20260830)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    """P(les k numéros de la grille sont tous tirés) — hypergéométrique."""
    return math.comb(DRAWN, k) / math.comb(POOL, k)


def threshold_per_franc(k: int) -> float:
    """Seuil de bascule de §5 bis, par franc misé : S = 1/p."""
    return 1.0 / p_full(k)


def kelly(q: float, b: float):
    """Fraction optimale et croissance logarithmique pour un pari (q, cote b).

    Transcrite à l'identique de h17 pour que les deux fichiers ne puissent
    pas diverger en silence.
    """
    f = q - (1 - q) / b
    if f <= 0:
        return 0.0, 0.0
    g = q * math.log1p(f * b) + (1 - q) * math.log1p(-f)
    return f, g


def growth(f: float, q: float, b: float) -> float:
    if f <= 0 or f >= 1:
        return -math.inf
    return q * math.log1p(f * b) + (1 - q) * math.log1p(-f)


# Le seul relevé du dossier (lab/jackpots_observed.csv, 30 août 2026).
OBSERVED = {5: 355.0, 6: 2287.0, 7: 1540.0, 8: 9292.0, 10: 495713.0}
K = 6                                    # la mise que h16/h17 prennent en exemple
S = threshold_per_franc(K)
ALPHA_HAT = OBSERVED[K] / S              # α estimé sur un relevé — h16


# ==========================================================================
# 1. L'INVENTAIRE — quelles décisions l'app propose-t-elle, et α y entre-t-il ?
# ==========================================================================

rule("1. L'INVENTAIRE DES DÉCISIONS")

say(f"""   Le dossier propose à son utilisateur exactement quatre actions, et
   c'est la liste complète — tout le reste est du rapport, pas de la
   décision.

   D1  JOUER OU NON à ce tirage.        §5 bis / §21 : jouer ssi J >= S = c/p
   D2  COMBIEN MISER.                    §30 : la fraction de Kelly
   D3  COMMENT DISPOSER LES GRILLES.     §26 / §33 : disjointes
   D4  QUELS NUMÉROS COCHER.             §1 : indifférent (théorème)

   Pour chacune, la question est : le paramètre α y entre-t-il ?

   D4 — non, et c'est un théorème. L'espérance de hits vaut k/4 pour toute
        grille. Rien n'y entre, α pas plus que le reste.

   D3 — non. La dominance de l'étalement est prouvée rang par rang (§26,
        théorème A et B), donc sous toute pondération positive des rangs.
        Elle ne dépend d'aucun paramètre estimé.

   D1 — la règle est J >= S. J est AFFICHÉ par l'opérateur au moment de
        décider ; S = c/p où p est une combinatoire exacte et c le prix du
        ticket. α n'y figure pas. C'est le point que §5 bis avait déjà
        établi en le nommant « condition suffisante » : elle est suffisante
        précisément parce qu'elle ne suppose rien.

   D2 — c'est le seul cas douteux, et c'est là que ce fichier travaille.
        h17 calcule la fraction de Kelly à partir de J = S(1 + α), c'est-à-
        dire à partir de la cagnotte MOYENNE au-dessus du seuil. α y entre
        donc explicitement. Mais au moment de miser, la cagnotte n'est pas
        une moyenne : elle est affichée. D'où deux questions qu'il faut
        trancher par le calcul et non par l'intuition :

          Q1  le taux d'ARRIVÉE des occasions (donc α, via §28) change-t-il
              la fraction optimale par occasion ?
          Q2  dimensionner sur la cagnotte OBSERVÉE plutôt que sur sa
              moyenne conditionnelle — qu'est-ce que cela change ?""")

say(f"""
   Paramètres repris du dossier, pour que les chiffres soient comparables :
   mise k = {K}, p = 1/{S:,.0f}, α estimé sur le relevé unique = {ALPHA_HAT:.4f}.""")


# ==========================================================================
# 2. Q1 — le taux d'arrivée entre-t-il dans la fraction optimale ?
# ==========================================================================

rule("2. Q1 — LE TAUX D'ARRIVÉE SORT DE LA DÉCISION, ET POURQUOI C'EST TRIVIAL")

n_grids = POOL // K                      # 13 grilles disjointes à la mise 6
p_win = n_grids * p_full(K)
J_mean = S * (1 + ALPHA_HAT)
b_mean = J_mean / n_grids - 1
f_star_mean, g_star_mean = kelly(p_win, b_mean)

say(f"""   La croissance logarithmique est ADDITIVE sur des paris indépendants.
   Le total vaut donc la somme des croissances par occasion, et le taux
   d'arrivée ne fait que compter les termes : il multiplie le total sans
   déplacer l'argmax d'aucun terme. C'est une identité, pas un résultat, et
   il serait malhonnête de la présenter comme une vérification — une
   simulation qui « confirmerait » cela ne ferait que réexécuter la même
   arithmétique.

   Ce qui n'est PAS trivial, et que la section 3 tranche, est autre chose :
   une fraction FIGÉE appliquée à des occasions HÉTÉROGÈNES n'est optimale
   pour aucune d'elles. C'est un compromis, et la question est de savoir ce
   que ce compromis coûte.

   Cadre commun aux deux sections : {n_grids} grilles disjointes à la mise {K} (le
   maximum, 13x6 = 78 <= 80), probabilité qu'une grille soit pleine
   {p_win:.3e}, cagnotte moyenne au-dessus du seuil {J_mean:,.0f} fois la mise,
   cote nette correspondante {b_mean:,.0f}.

   Fraction de h17 à cette cagnotte moyenne : {f_star_mean:.4e}.""")


# ==========================================================================
# 3. Q2 — dimensionner sur la cagnotte affichée plutôt que sur sa moyenne
# ==========================================================================

rule("3. Q2 — LA CAGNOTTE EST AFFICHÉE : FAUT-IL ENCORE L'ESTIMER ?")

say("""   h17 dimensionne à J = S(1 + α), la cagnotte MOYENNE au-dessus du
   seuil. C'est le bon chiffre pour annoncer un rendement. Ce n'est pas le
   chiffre dont on dispose au moment de miser : à cet instant la cagnotte
   est affichée à l'écran, et elle vaut ce qu'elle vaut.

   Trois règles de dimensionnement sont donc en concurrence, et la
   comparaison se fait en rejouant le même processus :

     R0  la MEILLEURE fraction figée possible, cherchée numériquement en
         connaissant toute la trajectoire — un oracle, donc une borne
         supérieure sur ce que toute règle à fraction figée peut atteindre
     R1  fraction figée, calculée une fois à la cagnotte moyenne (h17)
     R2  fraction recalculée à chaque occasion sur la cagnotte AFFICHÉE
     R3  figée, mais avec un α faux d'un facteur 3 — pour mesurer ce que
         l'ignorance de α coûte quand on dimensionne à la moyenne

   R0 est le juge de la question : si R2 bat même l'oracle des fractions
   figées, alors le compromis est perdant par nature et non par mauvais
   réglage.""")


def simulate_process_loop(alpha: float, n_draws: int, rng, j0: float = 0.0):
    """Version de référence, écrite en boucle — lente mais littérale."""
    mu = alpha * S
    q = 1.0 / 400.0
    r = mu * q
    fall = rng.random(n_draws) < q
    out = np.empty(n_draws)
    a0 = int(rng.geometric(q))
    j = j0 + r * a0
    for t in range(n_draws):
        out[t] = j
        j = j0 if fall[t] else j + r
    return out, r, q


def simulate_process(alpha: float, n_draws: int, rng, j0: float = 0.0):
    """Processus de cagnotte de h15, par franc misé — version vectorisée.

    H1 la cagnotte croît de r par tirage ; H2 elle tombe avec probabilité q
    par tirage, sans mémoire ; H3 elle repart de j0. Les deux paramètres ne
    sont pas libres : h16 établit mu = r/q = alpha*S. On fixe q et l'on en
    déduit r, de sorte que le processus porte exactement l'alpha demandé.

    La cagnotte au tirage t ne reflète que les chutes STRICTEMENT avant t,
    d'où le décalage d'un cran sur le cumul — c'est le point où une version
    vectorisée diverge silencieusement de sa boucle, et c'est pourquoi la
    section 0 les confronte.
    """
    mu = alpha * S
    q = 1.0 / 400.0
    r = mu * q
    fall = rng.random(n_draws) < q
    a0 = int(rng.geometric(q))
    idx = np.arange(n_draws)
    marked = np.where(fall, idx, -1)
    shifted = np.concatenate(([-1], marked[:-1]))
    last = np.maximum.accumulate(shifted)      # dernière chute avant t
    # Une chute à l'indice s remet la cagnotte à j0 POUR le tirage s+1, dont
    # l'âge vaut donc 0 et non 1 : d'où le « - 1 ». C'est précisément
    # l'erreur que le contrôle ci-dessous a attrapée dans la première
    # version, avec un écart maximal valant exactement r.
    age = np.where(last >= 0, idx - last - 1, a0 + idx)
    return j0 + r * age, r, q


def occasions_of(jackpots):
    """Les cagnottes qui franchissent le seuil — la règle D1, sans paramètre."""
    return jackpots[jackpots >= S]


def growth_of(occ, f, n=n_grids, k=K):
    """Croissance logarithmique cumulée, vectorisée sur les occasions.

    `f` est soit un scalaire (fraction figée), soit un vecteur de la taille
    de `occ` (fraction recalculée par occasion). Espérance de log plutôt
    qu'un tirage de Bernoulli : à p ~ 1e-3 il faudrait des milliards de
    tirages pour que la moyenne empirique converge, et l'espérance de log
    EST la quantité que Kelly maximise.
    """
    q_win = n * p_full(k)
    b = occ / n - 1
    f = np.broadcast_to(np.asarray(f, dtype=float), b.shape)
    ok = (f > 0) & (f < 1) & (b > 0)
    g = np.zeros_like(b)
    g[ok] = (q_win * np.log1p(f[ok] * b[ok])
             + (1 - q_win) * np.log1p(-f[ok]))
    return float(g.sum())


def replay(jackpots, sizing, n=n_grids, k=K):
    """Compatibilité avec la forme `sizing(J)` — rend (croissance, occasions)."""
    occ = occasions_of(jackpots)
    f = np.array([sizing(J) for J in occ]) if len(occ) else np.zeros(0)
    return growth_of(occ, f, n, k), len(occ)


# ---- SECTION 0 : la vectorisation contre sa boucle de référence ----
_chk = np.random.default_rng(7)
_a, _, _ = simulate_process(ALPHA_HAT, 5_000, np.random.default_rng(11))
_b, _, _ = simulate_process_loop(ALPHA_HAT, 5_000, np.random.default_rng(11))
_maxdiff = float(np.abs(_a - _b).max())
say(f"""
   CONTRÔLE — le processus vectorisé contre sa boucle littérale, même
   graine, 5 000 tirages : écart maximal {_maxdiff:.3e}. Le décalage d'un
   cran sur les chutes est le piège de cette réécriture, et c'est
   exactement ce que ce contrôle attrape.""")

# Assez long pour que le nombre de CYCLES atteignant le seuil soit grand :
# c'est lui, et non le nombre de tirages, qui fixe la précision (cf. §4).
N_DRAWS = 20_000_000
jack, r_true, q_true = simulate_process(ALPHA_HAT, N_DRAWS, RNG)
say(f"""
   Processus simulé : {N_DRAWS:,} tirages, alpha = {ALPHA_HAT:.4f}, chute toutes les
   {1/q_true:.0f} tirages en moyenne, accumulation r = {r_true:.4f} par tirage et par
   franc. Occasions (J >= S) : {int((jack >= S).sum()):,} soit {(jack >= S).mean():.2%} des tirages.""")


occ = occasions_of(jack)


def f_observed(o):
    """Fraction de Kelly par occasion, sur la cagnotte affichée — vectorisée."""
    return np.clip(p_win - (1 - p_win) / (o / n_grids - 1), 0.0, None)


def f_at_alpha(factor=1.0):
    """Fraction figée dimensionnée sur la cagnotte moyenne d'un alpha donné."""
    Jw = S * (1 + ALPHA_HAT * factor)
    f, _ = kelly(p_win, Jw / n_grids - 1)
    return f


# ---- TÉMOIN : sur des occasions HOMOGÈNES, les trois règles coïncident ----
# Sans ce contrôle, une machinerie de rejeu cassée pourrait faire gagner R2
# pour une raison qui n'aurait rien à voir avec l'hétérogénéité. Si toutes
# les occasions portent la MÊME cagnotte, « recalculer sur l'affichage » et
# « fraction figée bien réglée » sont la même chose, et l'écart doit être nul.
J_flat = J_mean
flat = np.full(20_000, J_flat)
f_flat_star, _ = kelly(p_win, J_flat / n_grids - 1)
g_flat_obs = growth_of(flat, f_observed(flat))
g_flat_fix = growth_of(flat, f_flat_star)
grid_w = np.geomspace(f_flat_star * 1e-2, min(0.5, f_flat_star * 1e2), 601)
g_flat_orc = max(growth_of(flat, f) for f in grid_w)
say(f"""
   TÉMOIN — occasions homogènes (même cagnotte partout, {len(flat):,} occasions).
   Les trois règles doivent alors coïncider : il n'y a plus d'hétérogénéité
   à exploiter.

     R2 sur l'affichage        {g_flat_obs:.9e}
     fraction figée optimale   {g_flat_fix:.9e}   écart relatif {abs(g_flat_fix/g_flat_obs - 1):.2e}
     oracle sur grille         {g_flat_orc:.9e}   écart relatif {abs(g_flat_orc/g_flat_obs - 1):.2e}

   Les trois coïncident exactement. Une précision qui évite de lire cet
   accord pour plus qu'il ne vaut : l'oracle tombe au zéro machine et non à
   un pas de grille près parce que la grille géométrique est CENTRÉE sur la
   fraction figée optimale et la contient donc exactement. Son accord avec
   elle est une propriété de la grille, pas une confirmation indépendante.
   Le témoin qui porte l'information est l'autre : R2, qui recalcule à
   chaque occasion, ne trouve rien de mieux qu'une fraction figée quand les
   occasions sont identiques. La machinerie ne fabrique donc pas d'avantage
   à R2 là où il n'y en a pas, et tout écart mesuré ci-dessous vient bien de
   l'hétérogénéité des cagnottes.""")

# R0 — l'oracle des fractions figées, cherché sur la trajectoire entière.
grid = np.geomspace(f_star_mean * 1e-2, min(0.5, f_star_mean * 1e2), 601)
g_grid = np.array([growth_of(occ, f) for f in grid])
f_oracle = float(grid[int(np.argmax(g_grid))])
g_oracle = float(g_grid.max())
if int(np.argmax(g_grid)) in (0, len(grid) - 1):
    say("   ATTENTION : l'optimum de R0 est au bord de la grille — élargir.")

rows = [
    ("R0  meilleure fraction figée (oracle)", f_oracle),
    ("R1  fraction figée à la cagnotte moyenne", f_star_mean),
    ("R2  fraction sur la cagnotte affichée", f_observed(occ)),
    ("R3  figée, alpha faux x3", f_at_alpha(3.0)),
    ("R3' figée, alpha faux /3", f_at_alpha(1 / 3)),
]
say(f"\n   fraction de l'oracle R0 : {f_oracle:.4e}  "
    f"(h17 dimensionne à {f_star_mean:.4e})")
say("\n   règle de dimensionnement                    croissance totale   rapport à R2")
results = {}
for name, f in rows:
    results[name] = growth_of(occ, f)
base = results["R2  fraction sur la cagnotte affichée"]
for name, _ in rows:
    lg = results[name]
    say(f"   {name:<43} {lg:<19.6e} x{lg / base:.4f}")

say(f"""
   Lecture. R2 domine, et surtout R2 ne demande AUCUN alpha : elle lit la
   cagnotte affichée, la probabilité p est une combinatoire exacte, et n
   est un choix. Les deux variantes fausses de R3 montrent ce que coûte une
   erreur d'un facteur 3 sur alpha — c'est-à-dire à peu près la largeur de
   l'intervalle dont dispose le dossier — quand on dimensionne à la moyenne
   plutôt qu'à l'affichage.

   C'est le résultat de ce fichier, et il retire une dépendance plutôt
   qu'il n'en ajoute une : **la fraction de Kelly se calcule intégralement
   avec ce qui est visible à l'instant de miser.** alpha n'entre dans D2
   que si l'on choisit de dimensionner sur une moyenne dont on n'a pas
   besoin.""")


# ==========================================================================
# 3 bis. La même quantité par une seconde voie, entièrement indépendante
# ==========================================================================

rule("3 bis. SECONDE VOIE — intégration sur la loi, sans trajectoire")

say("""   La section 3 mesure l'écart sur UNE trajectoire simulée. Si le
   simulateur n'était pas en régime stationnaire, ou si `replay` comptait
   mal les occasions, le chiffre serait faux sans que rien ne le signale.

   La même quantité se calcule par un chemin qui ne partage rien avec le
   premier — ni tirage aléatoire, ni boucle de rejeu. Par absence de
   mémoire, la cagnotte au-dessus du seuil vérifie J - S ~ Exp(mu), donc

     règle adaptative   E[ max_f g(f, b(J)) ]      integrale sur la loi
     meilleure figée    max_f E[ g(f, b(J)) ]      integrale, puis maximum

   Les deux intégrales sont évaluées par quadrature sur la loi exacte.""")

mu = ALPHA_HAT * S
# Quadrature sur J - S ~ Exp(mu) : noeuds par quantiles réguliers, ce qui
# évite d'avoir à tronquer la queue à la main.
u = (np.arange(1, 200_001) - 0.5) / 200_000
J_q = S - mu * np.log1p(-u)              # quantiles de S + Exp(mu)
b_q = J_q / n_grids - 1

# Voie adaptative : optimum atteint occasion par occasion.
f_q = p_win - (1 - p_win) / b_q
f_q = np.clip(f_q, 0.0, None)
g_adapt = float(np.mean(
    p_win * np.log1p(f_q * b_q) + (1 - p_win) * np.log1p(-f_q)))

# Voie figée : une seule fraction, la meilleure en espérance.
fs = np.geomspace(f_star_mean * 1e-2, min(0.5, f_star_mean * 1e2), 4001)
g_fixed_all = np.array([
    float(np.mean(p_win * np.log1p(f * b_q) + (1 - p_win) * math.log1p(-f)))
    for f in fs])
g_fixed = float(g_fixed_all.max())
f_fixed = float(fs[int(np.argmax(g_fixed_all))])

n_occ = len(occ)
sim_adapt = results["R2  fraction sur la cagnotte affichée"] / n_occ
sim_oracle = results["R0  meilleure fraction figée (oracle)"] / n_occ

say(f"""
                              par intégration      par simulation      écart
   règle adaptative           {g_adapt:.6e}        {sim_adapt:.6e}       {abs(g_adapt/sim_adapt - 1):.2%}
   meilleure fraction figée   {g_fixed:.6e}        {sim_oracle:.6e}       {abs(g_fixed/sim_oracle - 1):.2%}
   rapport adaptative/figée   {g_adapt/g_fixed:.4f}               {sim_adapt/sim_oracle:.4f}

   fraction figée optimale : {f_fixed:.4e} par intégration, {f_oracle:.4e} par simulation.""")

say(f"""
   Les deux voies s'accordent. Le rapport — l'écart de Jensen du théorème N
   — vaut {g_adapt/g_fixed:.3f} par intégration contre {sim_adapt/sim_oracle:.3f} par simulation, et il ne dépend
   donc ni du tirage aléatoire ni de la machinerie de rejeu.""")


# ==========================================================================
# 4. Ce que le plan de relevés achète RÉELLEMENT
# ==========================================================================

rule("4. LE PLAN DE RELEVÉS — ce qu'il achète, et ce qu'il n'achète pas")

say("""   alpha sort donc des quatre décisions. Il reste utile à une chose, et
   elle n'est pas rien : savoir ce que la stratégie RAPPORTE par unité de
   temps, donc si elle vaut la peine d'être suivie. C'est du rapport, pas
   de l'action — mais un joueur a le droit de le savoir avant de commencer.

   La question de plan d'expérience est alors : qu'est-ce qui porte
   l'information sur alpha ?

   §28 nomme le raccourci — mesurer r (l'accumulation par tirage) et q (le
   taux de chutes) plutôt que d'estimer mu à travers une variable
   aléatoire — et conclut : « deux relevés rapprochés valent bien davantage
   que deux relevés éloignés ». La première moitié est juste, la seconde
   demande une précision que le dossier n'a pas apportée.""")

say("""
   Deux estimateurs sont en concurrence sur une même fenêtre contiguë :

     A  moyenne de la cagnotte sur TOUS les relevés, alpha_hat = moy(J)/S
        — l'estimateur de h15/h16 poussé à son maximum, sans mémoire donc
        sans biais
     B  r par différences consécutives, q par comptage de chutes,
        alpha_hat = r/(q*S)                              (le raccourci §28)

   L'app journalise désormais un relevé par tirage (§28), soit 204 par
   jour : la fenêtre d'observation est contiguë et gratuite.""")


def estimate_A(j):
    """Moyenne de la cagnotte sur TOUS les relevés de la fenêtre.

    C'est l'estimateur naturel de h15/h16 poussé à son maximum : en
    régime stationnaire l'âge de la cagnotte est sans mémoire, donc
    E[J] = r/q = mu, et la moyenne empirique est sans biais. Toujours
    défini, ce qui évite la sélection sur les fenêtres.
    """
    return float(np.mean(j)) / S


def estimate_B(j):
    """Le raccourci de §28 : r par différences consécutives, q par comptage.

    Rend NaN quand la fenêtre ne contient aucune chute — q n'y est alors
    pas estimable, et compter cette fenêtre comme un succès reviendrait à
    la sélection que la première version de ce fichier commettait.
    """
    d = np.diff(j)
    pos = d[d > 0]
    n_falls = int((d < 0).sum())
    if len(pos) == 0 or n_falls == 0:
        return math.nan
    r_hat = float(np.median(pos))
    q_hat = n_falls / len(d)
    return (r_hat / q_hat) / S


say("""
   Le tableau est indexé par le nombre de CHUTES attendues et non par une
   durée, parce que le taux de chute q est lui-même inconnu : une durée
   n'aurait de sens qu'au q particulier de la simulation. La traduction en
   jours est donnée à part, pour deux valeurs de q qui encadrent le
   plausible.

   L'écart est rapporté par l'intervalle empirique à 95 % de alpha_hat/alpha
   — et non par un écart-type, ces estimateurs étant des rapports à queue
   lourde pour lesquels un écart-type dit peu de chose.""")

REPS = 600
say("\n   D attendu   fenêtre     A : 95 % de a/a      B : 95 % de a/a      B défini")
scaling = []
for D_target in (1, 3, 10, 30, 100, 300):
    q = 1.0 / 400.0
    n = int(D_target / q)
    ea, eb = [], []
    for _ in range(REPS):
        j, r, q_used = simulate_process(ALPHA_HAT, n, RNG)
        ea.append(estimate_A(j) / ALPHA_HAT)
        b = estimate_B(j)
        if not math.isnan(b):
            eb.append(b / ALPHA_HAT)
    ea = np.array(ea)
    eb = np.array(eb)
    la, ha = np.percentile(ea, [2.5, 97.5])
    if len(eb) > 20:
        lb, hb = np.percentile(eb, [2.5, 97.5])
        btxt = f"[{lb:.2f} ; {hb:.2f}]"
    else:
        lb = hb = math.nan
        btxt = "indéfini"
    scaling.append((D_target, float(np.std(ea))))
    say(f"   {D_target:>9}   {n:>7,}     [{la:.2f} ; {ha:.2f}]{'':<8} "
        f"{btxt:<20} {len(eb)/REPS:>6.0%}")

say("\n   Vérification de la loi d'échelle — l'écart doit suivre 1/racine(D) :")
say("\n   D          écart-type de a/a    x racine(D)")
for D_target, sd in scaling:
    say(f"   {D_target:>6}     {sd:>16.4f}     {sd * math.sqrt(D_target):>10.4f}")

say("""
   La colonne ne devient plate qu'à partir de D = 30, où elle se stabilise
   autour de 1,4 ; en dessous elle monte de 0,96 à 1,38. Il faut le dire
   ainsi plutôt que d'annoncer une loi exacte : à petit D la loi de
   l'estimateur est trop dissymétrique pour qu'un écart-type la résume, et
   c'est précisément pourquoi le tableau du dessus donne un intervalle et
   non un sigma. La loi d'échelle est donc ASYMPTOTIQUE, de constante
   mesurée 1,4, et atteinte vers une trentaine de chutes.

   Ce qui est net, en revanche, c'est ce qui indexe l'échelle : le nombre
   de CHUTES observées, et non le nombre de relevés. C'est le point que §28
   n'avait pas isolé — entre deux chutes, l'app peut journaliser mille
   relevés, ils décrivent tous le même cycle et n'apportent qu'une seule
   observation de l'âge.

   Lu sur l'intervalle à 95 %, cela donne la règle pratique : le facteur
   d'incertitude sur alpha vaut 18,9 à une chute, 3,8 à dix, 1,65 à cent.

   Et B, le raccourci de §28, est MOINS bon que A tant que les chutes sont
   rares — 1/q_hat est une transformation convexe d'un comptage, donc
   biaisée vers le haut et à queue lourde, et il n'est même pas défini dans
   38 % des fenêtres à une chute attendue. Ce que §28 avait raison de dire,
   et qu'il faut garder : deux relevés CONSÉCUTIFS donnent r presque
   exactement, l'accumulation étant déterministe entre deux chutes. Mais r
   saturé, la précision sur alpha ne dépend plus que de q, et q se paie en
   chutes observées — pas en relevés.""")

say("\n   Traduction en temps, aux deux extrémités du plausible :")
say("\n   chute toutes les…   D = 10 (facteur 3)   D = 100 (facteur 10)")
for period in (200, 400, 2000):
    say(f"   {period:>4} tirages         "
        f"{10 * period / DRAWS_PER_DAY:>10.0f} jours       "
        f"{100 * period / DRAWS_PER_DAY:>10.0f} jours")


# ==========================================================================
# 5. Le prix du ticket — la seule donnée manquante dont une décision dépende
# ==========================================================================

rule("5. LE PRIX DU TICKET")

say("""   Le dossier appelle le prix du ticket « la donnée manquante la moins
   chère à obtenir » (§28) et la range à côté de la série de relevés (§29).
   L'inventaire du §1 les sépare radicalement.

   Le seuil de bascule vaut S = c/p. Sans c, la règle D1 — la seule qui
   décide s'il faut jouer — n'est pas calculable. Toutes les tables du
   dossier sont « par franc misé » précisément pour contourner cette
   ignorance, et §21 le dit en réserve : « si un ticket coûte plus d'un
   franc les fractions ci-dessus se divisent d'autant ».""")

say("\n   prix du ticket   seuil D1 à la mise 6   cagnotte relevée   franchi ?")
for c in (0.50, 1.00, 2.00, 3.00, 5.00):
    s_abs = c * S
    ok = "OUI" if OBSERVED[K] >= s_abs else f"non ({OBSERVED[K]/s_abs:.1%})"
    say(f"   CHF {c:<12.2f} CHF {s_abs:>16,.0f}   CHF {OBSERVED[K]:>13,.0f}   {ok}")

say(f"""
   Le relevé unique du dossier est à {OBSERVED[K]/(1.0*S):.1%} du seuil pour un ticket à un
   franc, et à {OBSERVED[K]/(5.0*S):.1%} pour un ticket à cinq. L'ordre de grandeur de la
   distance au point de bascule dépend donc entièrement d'un nombre que
   personne n'a relevé.

   Et alpha en dépend aussi : alpha = mu/S = mu*p/c, donc alpha est
   INVERSEMENT proportionnel au prix du ticket. Le +29,5 % de §29 est un
   +29,5 % à un franc ; à cinq francs c'est +5,9 %. La réserve de §29 sur
   un alpha « anormalement généreux » a donc une explication banale parmi
   les trois qu'elle propose, et c'est la moins chère à écarter.""")

say("\n   prix du ticket   alpha implicite   gain conditionnel   capital minimal (x13 grilles)")
for c in (0.50, 1.00, 2.00, 5.00):
    a_c = OBSERVED[K] / (c * S)
    Jc = c * S * (1 + a_c)
    f_c, g_c = kelly(p_win, Jc / (c * n_grids) - 1) if a_c > 0 else (0.0, 0.0)
    tour = c * n_grids
    cap = tour / f_c if f_c > 0 else float("inf")
    say(f"   CHF {c:<12.2f} {a_c:<17.1%} {a_c:<19.1%} CHF {cap:>12,.0f}")


# ==========================================================================
# 6. Conclusion
# ==========================================================================

rule("6. CE QUE CE FICHIER CHANGE")

say(f"""   1. alpha n'entre dans AUCUNE des quatre décisions de l'app. D4 est
      fermée par un théorème, D3 par une dominance rang par rang, D1 par
      une condition suffisante qui ne suppose rien, et D2 — le seul cas
      douteux — se calcule intégralement sur la cagnotte AFFICHÉE, ce que
      la section 3 vérifie plutôt que de le déduire.

   2. La demande de données du dossier était donc mal orientée. « Une
      trentaine de relevés, une centaine » (§28) achète un RAPPORT plus
      précis, pas une meilleure action. L'app peut agir correctement dès
      aujourd'hui, sans le moindre historique de cagnottes.

   3. Ce que l'historique achète, il l'achète au rythme des CHUTES de la
      cagnotte et non des relevés : écart relatif ~ 1,4/racine(D) au-delà
      d'une trentaine de chutes. C'est une correction à §28, dont le
      raccourci « r et q » est juste pour r et incomplet pour q — et dont
      l'estimateur B est en pratique moins bon que la simple moyenne tant
      que les chutes sont rares.

   4. La seule donnée manquante dont une DÉCISION dépende est le prix du
      ticket, et elle se relève d'un coup d'oeil. Elle fixe le seuil D1,
      elle divise alpha d'autant, et elle multiplie le capital minimal de
      §30 dans la même proportion.

   5. Correction proposée à h17/§30 : dimensionner sur la cagnotte affichée
      (R2) plutôt que sur la cagnotte moyenne conditionnelle (R1). R2 bat
      même R0, la MEILLEURE fraction figée possible choisie par un oracle
      qui connaîtrait toute la trajectoire — le compromis d'une fraction
      unique sur des occasions hétérogènes est donc perdant par nature, pas
      par mauvais réglage.

   6. Et le danger est ASYMÉTRIQUE, ce qui est l'argument le plus fort de
      tous : dimensionner à la moyenne avec un alpha surestimé d'un facteur
      3 — soit à peu près la largeur de l'intervalle dont le dossier
      dispose — ne garde que 5 % de la croissance, quand le sous-estimer du
      même facteur en garde encore 49 %. Se tromper vers le haut coûte dix
      fois plus que se tromper vers le bas, ce qui est la falaise de surmise
      de §30. La règle qui n'a besoin d'aucun alpha n'y est pas exposée.

      Une version antérieure de ce fichier annonçait ici une croissance
      NÉGATIVE. C'était un artefact d'échantillon : à 400 000 tirages, seuls
      une trentaine de cycles atteignent le seuil, et la trajectoire n'avait
      donc pas l'effectif que ses six chiffres laissaient croire. À 20
      millions de tirages, et confirmée par l'intégration de la section
      3 bis, la croissance reste positive. Le sens de l'asymétrie tient ;
      son amplitude était fausse.

   Réserve, et elle est entière. Rien de tout cela ne prédit un numéro, et
   rien n'y prétend. Le théorème d'invariance reste intact : ce fichier ne
   déplace pas la frontière entre ce qui est prévisible et ce qui ne l'est
   pas, il déplace la frontière entre ce qu'il faut MESURER et ce qu'il
   suffit de LIRE.

   Registre : inchangé. h25 ne teste pas l'archive.""")

say(f"\n   ({time.time() - T0:.1f} s)")
