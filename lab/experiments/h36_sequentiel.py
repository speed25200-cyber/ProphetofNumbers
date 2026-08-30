"""h36 — sortir du cadre « un tirage à la fois » : la cagnotte comme processus,
le capital comme état, la géométrie comme fonction de l'état.

Ce que le dossier n'a jamais formulé
-------------------------------------
Le théorème d'invariance est un énoncé sur UN tirage et UNE grille. Tout ce
qui a été construit par-dessus reste dans ce cadre : le seuil du §5 bis
décide tirage par tirage, la fraction de Kelly du §30 se calcule occasion
par occasion, et le théorème N (§36) dit de la recalculer sur la cagnotte
affichée. Or la cagnotte est un PROCESSUS (§28, théorème J) : elle monte de
r par tirage et tombe avec probabilité q. L'état du jeu à l'instant t est
son niveau J_t, et le joueur fait face à un problème de CONTRÔLE MARKOVIEN
que personne n'a posé comme tel. Ce fichier le pose, le résout, et compare.

La formulation, en trois problèmes emboîtés
--------------------------------------------
(a) ADMISSION SÉQUENTIELLE. État : l'âge t de la cagnotte (J_t = r·t, sous
    H1–H3 de h15). Action : jouer n grilles disjointes ou s'abstenir.
    Récompense : n·(p·J_t − c) si l'on joue. Transition : la cagnotte tombe
    avec probabilité q (la foule) — ET, si l'on joue, avec probabilité
    supplémentaire n·p (se la faire tomber soi-même). Critère : le profit
    moyen par tirage (récompense moyenne à long terme). C'est un MDP
    unichaîne sur une chaîne de naissance-et-remise-à-zéro ; on le résout
    par itération sur les politiques avec certificat de Bellman, et l'on
    recoupe par la formule de renouvellement exacte et par un Monte-Carlo
    par cycles qui échantillonne les gains au lieu d'en réécrire
    l'espérance.

    Deux forces que le calcul statique du §29 ignore s'annulent ou non :
      - « attendre pour jouer demain avec un capital intact » : NULLE en
        espérance, car jouer aujourd'hui n'empêche pas de jouer demain —
        les récompenses sont additives et la transition de la cagnotte ne
        dépend pas de l'action... sauf par un canal :
      - l'AUTO-EXTINCTION : gagner fait tomber la cagnotte, donc jouer
        détruit avec probabilité n·p la valeur future du processus. C'est
        le seul canal par lequel le séquentiel peut dévier du statique, et
        il ne pousse que dans UN sens : jouer PLUS TARD que le seuil.

(b) CAPITAL. Second état : la réserve W, avec le prix plancher c du ticket
    (on ne mise pas une fraction, on achète des tickets entiers). Objectif :
    atteindre le régime de Kelly (W ≥ G = n·c/f*, le CHF 33 991 du §30)
    avant la ruine. La clef de voûte est une réduction : le capital est un
    COMPTEUR D'ESSAIS. Chaque ticket est une Bernoulli(p) quel que soit le
    niveau de cagnotte auquel on le tire — c'est l'invariance elle-même —
    donc une politique ne choisit qu'une chose : le niveau de cagnotte
    auquel chaque essai est dépensé. D'où un théorème (borne + politique
    qui l'atteint), puis la version au temps facturé (programmation
    dynamique sur le stock de tickets), puis la variante « croissance avec
    intégralité du ticket » qui étend R2 (§36) sous le plancher de capital.

(c) GÉOMÉTRIE. Le théorème de bascule (§26) dit : objectif convexe →
    concentrer, objectif concave → étaler. En séquentiel le joueur traverse
    les deux régimes selon J. MAIS le rang qui porte tout ici est PARTAGÉ :
    empiler ses n tickets sur une même grille, c'est partager le pot avec
    soi-même — le pot est une tarte, pas une cote. On vérifie donc (témoin)
    que la machinerie détecte bien la bascule sur un rang à gain FIXE, puis
    on montre qu'elle ne trouve AUCUN état où la concentration gagne sur le
    rang partagé.

Garde-fous
----------
Rien ici ne prédit un numéro : E[hits] = k/4 dans tous les états (l'unique
raison pour laquelle p est incompressible est aussi ce qui rend le théorème
du compteur d'essais vrai). Toutes les politiques rendues sont paramétrées
par ce qui est VISIBLE (J affiché, W, c, p) ; α n'entre que dans les
RYTHMES (fréquences, durées), jamais dans les règles — et c'est vérifié en
balayant α sur l'intervalle du §29.

Comme h1, h14, h17 et h25 : ce fichier prouve et corrige, il ne teste pas
l'archive. Registre inchangé. numpy et math seulement (pas de scipy).
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
POOL, DRAWN = 80, 20
K = 6
C = 1.0                                   # prix du ticket, par franc (réserve : §36)
N_GRIDS = POOL // K                       # 13 grilles disjointes au maximum
DRAWS_PER_DAY = 204
RNG = np.random.default_rng(20260830)

P = math.comb(DRAWN, K) / math.comb(POOL, K)
S = C / P                                 # seuil de bascule du §5 bis
ALPHA_HAT = 2287.0 / S                    # le relevé unique du dossier (§29)
Q_BASE = 1.0 / 400.0                      # chute toutes les 400 tirages (h25)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def kelly(q, b):
    """Transcrite à l'identique de h17/h25."""
    f = q - (1 - q) / b
    if f <= 0:
        return 0.0, 0.0
    return f, q * math.log1p(f * b) + (1 - q) * math.log1p(-f)


# Garde-fou n°1 : l'espérance de hits est k/4, indépendante de tout état.
assert abs(K * DRAWN / POOL - K / 4) < 1e-15
# Cohérences avec le dossier, calculées et non recopiées.
J_REF = S * (1 + ALPHA_HAT)
F13, G13 = kelly(N_GRIDS * P, J_REF / N_GRIDS - 1)
G_KELLY = N_GRIDS * C / F13               # doit retomber sur le CHF 33 991 du §30
assert abs(G_KELLY - 33991) < 1.0, G_KELLY
F1, _ = kelly(P, J_REF - 1)
assert abs(F1 - 2.94e-5) < 1e-7           # §30, une grille seule
X_STAR = 1 / ALPHA_HAT
assert abs(math.exp(-X_STAR) * (ALPHA_HAT * (X_STAR + 1) - 1) - 0.0099) < 1e-4  # §31


# ==========================================================================
# A. L'ADMISSION SÉQUENTIELLE — le seuil du §29 survit-il au temps ?
# ==========================================================================

rule("A. LE SEUIL, EN SÉQUENTIEL — programmation dynamique sur le niveau de cagnotte")

say("""   Le §29 prouve l'optimalité du seuil dans un problème STATIQUE : le
   profit par tirage d'une politique de seuil, dérivé, s'annule en S. Un
   joueur séquentiel a deux objections possibles. La première — « ne pas
   jouer aujourd'hui pour jouer demain » — est nulle : jouer n'empêche pas
   de rejouer, les profits sont additifs, et si l'action ne changeait pas
   la transition, l'optimum d'un MDP à transitions indépendantes de
   l'action serait myope, donc exactement le seuil statique. La seconde
   est réelle : GAGNER FAIT TOMBER LA CAGNOTTE. Jouer ajoute n·p au taux de
   chute, et détruit donc, avec cette probabilité, la valeur future du
   processus. Le prix de cette auto-extinction est ce que le programme
   dynamique mesure.

   La condition d'amélioration de Bellman se réduit à une ligne :

       jouer en t  ⟺  J_t > S + (1−q)·h(t+1)

   où h est la fonction de biais (valeur relative) de la politique. h ≥ 0 :
   le seuil séquentiel est TOUJOURS au-dessus du seuil statique, jamais en
   dessous — et il s'y recolle quand n·p/q → 0, c'est-à-dire quand le
   joueur est négligeable dans la foule.""")


def eval_threshold_renewal(m, alpha, q, n, phantom=False):
    """Profit moyen par tirage d'une politique de seuil d'âge m — forme fermée.

    Renouvellement : poids stationnaires (1−q)^t sous m, puis
    (1−q)^m (1−q1)^{t−m} au-dessus, q1 = 1−(1−q)(1−n·p) (auto-extinction),
    sommes géométriques exactes. `phantom` coupe l'auto-extinction (témoin).
    """
    mu = alpha * S
    r = mu * q
    q1 = q if phantom else 1 - (1 - q) * (1 - n * P)
    below = (1 - (1 - q) ** m) / q                    # somme des poids t < m
    wm = (1 - q) ** m
    above = wm / q1                                   # somme des poids t >= m
    sum_wt = wm * (m / q1 + (1 - q1) / q1 ** 2)       # somme w(t)·t, t >= m
    reward = n * P * r * sum_wt - n * C * above
    return reward / (below + above)


def solve_dp_admission(alpha, q, n, phantom=False, xmax=34.0):
    """Itération sur les politiques, évaluation exacte, certificat de Bellman.

    État : âge t (J = r·t), t = 0..T avec (1−q)^T < e^{−xmax}. Rend le
    seuil optimal (en âge), le profit moyen, et le fait que la politique
    optimale est bien de forme seuil (vérifié, pas supposé).
    """
    mu = alpha * S
    r = mu * q
    T = int(math.ceil(xmax / q))
    J = r * np.arange(T + 2)
    q1 = q if phantom else 1 - (1 - q) * (1 - n * P)
    play = J[: T + 1] >= S                            # départ : politique statique
    rho = math.nan
    h = None
    for _ in range(60):
        haz = np.where(play, q1, q)
        w = np.empty(T + 1)
        w[0] = 1.0
        np.cumprod(1 - haz[:-1], out=w[1:])
        rew = np.where(play, n * P * J[: T + 1] - n * C, 0.0)
        rho = float(w @ rew) / float(w.sum())
        # biais : h(t) = E[somme (R−rho) jusqu'à la prochaine chute | t], h(chute)=0
        h = np.zeros(T + 2)
        for t in range(T, -1, -1):
            h[t] = rew[t] - rho + (1 - haz[t]) * h[t + 1]
        if phantom:
            margin = n * P * J[: T + 1] - n * C
        else:
            margin = n * P * J[: T + 1] - n * C - (1 - q) * n * P * h[1: T + 2]
        new = margin > 0
        if bool(np.all(new == play)):
            break
        play = new
    # certificats
    assert abs(h[0]) < 1e-6 * max(1.0, abs(rho) / max(q, 1e-9)), h[0]
    idx = np.flatnonzero(play)
    is_threshold = len(idx) > 0 and bool(np.all(np.diff(idx) == 1)) \
        and idx[-1] == len(play) - 1
    return int(idx[0]) if len(idx) else None, rho, is_threshold, r


def mc_cycles_admission(m, alpha, q, n, n_cycles, rng, phantom=False):
    """Monte-Carlo par cycles : échantillonne les GAINS, pas leur espérance.

    Un cycle : la cagnotte survit sous q jusqu'à l'âge m (ou tombe avant),
    puis sous q1 ; si la chute au-dessus de m est le fait du joueur
    (probabilité (1−q)·n·p / q1), il empoche J à cet âge. Coût n·c par
    tirage joué. Rend rho estimé et son erreur-type (TCL de renouvellement).
    """
    mu = alpha * S
    r = mu * q
    q1 = q if phantom else 1 - (1 - q) * (1 - n * P)
    g1 = rng.geometric(q, n_cycles)                   # essais jusqu'à chute sous q
    early = g1 - 1 < m                                # chute avant d'atteindre m
    length = np.where(early, g1, 0).astype(float)
    reward = np.zeros(n_cycles)
    k_up = int((~early).sum())
    if k_up:
        g2 = rng.geometric(q1, k_up)                  # durée au-dessus de m
        fall_age = m + g2 - 1
        own = rng.random(k_up) < ((1 - q) * n * P / q1 if not phantom else 0.0)
        length[~early] = m + g2
        reward[~early] = -n * C * g2 + np.where(own, r * fall_age, 0.0)
    rho_hat = reward.sum() / length.sum()
    resid = reward - rho_hat * length
    se = float(np.std(resid)) / (float(np.mean(length)) * math.sqrt(n_cycles))
    return rho_hat, se


say("\n   A1. TÉMOIN — auto-extinction coupée : le DP doit rendre EXACTEMENT")
say("       le seuil statique (transitions indépendantes de l'action ⇒ myopie).")
m_stat = math.ceil(S / (ALPHA_HAT * S * Q_BASE))
m_ph, rho_ph, thr_ph, r_base = solve_dp_admission(ALPHA_HAT, Q_BASE, N_GRIDS,
                                                  phantom=True)
say(f"       seuil statique m_S = {m_stat} (âge), DP fantôme m* = {m_ph}, "
    f"forme seuil : {thr_ph}")
assert m_ph == m_stat and thr_ph

rho_ph_renew = eval_threshold_renewal(m_ph, ALPHA_HAT, Q_BASE, N_GRIDS, phantom=True)
say(f"       rho fantôme : DP {rho_ph:.6e} vs renouvellement {rho_ph_renew:.6e} "
    f"(écart {abs(rho_ph / rho_ph_renew - 1):.1e})")
assert abs(rho_ph / rho_ph_renew - 1) < 1e-8

# recoupement avec la formule continue du §29 (n = 1) : f(x) = e^{-x}(α(x+1)−1)
rho_cont = math.exp(-1 / ALPHA_HAT) * (ALPHA_HAT * (1 / ALPHA_HAT + 1) - 1)
rho_disc1 = eval_threshold_renewal(m_stat, ALPHA_HAT, Q_BASE, 1, phantom=True)
say(f"       recoupement §29 (n=1, par franc) : continu {rho_cont:.5e}, "
    f"discret {rho_disc1:.5e} (écart {abs(rho_disc1 / rho_cont - 1):.2%}, "
    "discret vs exponentiel)")
assert abs(rho_disc1 / rho_cont - 1) < 0.02

say("\n   A2. LE VRAI PROBLÈME — auto-extinction comptée. Trois voies.")
m_opt, rho_opt, thr_ok, _ = solve_dp_admission(ALPHA_HAT, Q_BASE, N_GRIDS)
assert thr_ok
# balayage de renouvellement : la même réponse par une arithmétique disjointe
ms = np.arange(max(1, m_stat - 60), m_opt + 800)
rhos = np.array([eval_threshold_renewal(int(m), ALPHA_HAT, Q_BASE, N_GRIDS)
                 for m in ms])
m_renew = int(ms[int(np.argmax(rhos))])
rho_renew = float(rhos.max())
rho_static_true = eval_threshold_renewal(m_stat, ALPHA_HAT, Q_BASE, N_GRIDS)
say(f"""
       seuil optimal (DP, certificat de Bellman)   m* = {m_opt}  soit J* = {m_opt * r_base:,.0f}
       seuil optimal (balayage renouvellement)     m* = {m_renew}  soit J* = {m_renew * r_base:,.0f}
       seuil statique du §29                       m_S = {m_stat}  soit S  = {S:,.0f}
       décalage Δ = J* − S = {m_opt * r_base - S:,.0f} francs = {(m_opt * r_base - S) / (ALPHA_HAT * S):.3f}·μ = {(m_opt * r_base / S - 1):+.2%} de S""")
assert m_renew == m_opt

rho_mc, se_mc = mc_cycles_admission(m_opt, ALPHA_HAT, Q_BASE, N_GRIDS,
                                    2_000_000, RNG)
z_mc = (rho_mc - rho_opt) / se_mc
say(f"""
       profit/tirage : DP {rho_opt:.6e} = renouvellement {rho_renew:.6e}
       Monte-Carlo par cycles (2·10⁶ cycles, gains échantillonnés) :
       {rho_mc:.6e} ± {se_mc:.1e}, z = {z_mc:+.2f} σ""")
assert abs(rho_opt / rho_renew - 1) < 1e-9 and abs(z_mc) < 4

loss_static = 1 - rho_static_true / rho_opt
say(f"""
       Et le prix de l'ignorer : jouer au seuil statique dans la vraie
       dynamique coûte {loss_static:.2%} de profit par tirage à ces paramètres.
       Une confession de méthode : la première rédaction de ce paragraphe
       annonçait ce coût « presque gratuit, de second ordre » AVANT de
       l'avoir mesuré. Le calcul a corrigé le texte : de second ordre, il
       ne l'est que si n·p/q est petit — or aux paramètres de référence de
       h25 (q = 1/400), les 13 grilles d'un seul joueur représentent 67 %
       du taux de chute, et le coût est de dix pour cent. Le tableau
       suivant dit où l'approximation statique est bonne, au lieu de le
       présumer.""")

say("""
   A3. LA RÈGLE, SOUS L'INCERTITUDE SUR α — et sur la part du joueur dans
       la foule. Le décalage est gouverné par n·p/q (la part du taux de
       chute que le joueur s'inflige) ; α ne fait qu'en fixer l'échelle en
       francs. Balayage croisé, borne à borne de l'intervalle du §29 :""")
say("\n   α        q        n·p/q    Δ/μ      Δ (francs)   perte du seuil statique")
for alpha_v in (0.08, 0.295, 1.0, 3.0, 11.65):
    for q_v in (1 / 50, 1 / 400, 1 / 2000):
        m_s_v = math.ceil(1 / (alpha_v * q_v))
        m_o_v, rho_o_v, ok_v, r_v = solve_dp_admission(alpha_v, q_v, N_GRIDS)
        assert ok_v
        rho_s_v = eval_threshold_renewal(m_s_v, alpha_v, q_v, N_GRIDS)
        d_fr = m_o_v * r_v - S
        say(f"   {alpha_v:<8.3g} {q_v:<8.4f} {N_GRIDS * P / q_v:<8.3f} "
        f"{d_fr / (alpha_v * S):<8.4f} {d_fr:>10,.0f}   {1 - rho_s_v / rho_o_v:>10.3%}")

say(f"""
   Et la ligne qui décrit un utilisateur de l'app — UNE grille parmi la
   foule (n = 1, q = 1/400, soit n·p/q = {P / Q_BASE:.3f}) :""")
say("\n   α        Δ/μ      Δ (francs)   perte du seuil statique")
one_grid = {}
for alpha_v in (0.08, 0.295, 1.0, 3.0):
    m_s_v = math.ceil(1 / (alpha_v * Q_BASE))
    m_o_v, rho_o_v, ok_v, r_v = solve_dp_admission(alpha_v, Q_BASE, 1)
    assert ok_v
    rho_s_v = eval_threshold_renewal(m_s_v, alpha_v, Q_BASE, 1)
    d_fr = m_o_v * r_v - S
    one_grid[alpha_v] = (d_fr / (alpha_v * S), 1 - rho_s_v / rho_o_v)
    say(f"   {alpha_v:<8.3g} {d_fr / (alpha_v * S):<8.4f} {d_fr:>10,.0f}   "
        f"{1 - rho_s_v / rho_o_v:>10.3%}")

worst1 = max(v[1] for v in one_grid.values())
say(f"""
   Lecture, en trois temps.

   1. La politique optimale du contrôle markovien EST une politique de
      seuil (vérifié par certificat de Bellman, pas supposé). L'intuition
      qui motivait la question — « ne pas jouer aujourd'hui pour jouer
      demain avec un capital intact » — est nulle en espérance, et le
      calcul dit pourquoi : jouer n'empêche pas de rejouer. Si l'action ne
      touchait pas la transition, le seuil du §29 serait EXACTEMENT optimal
      en séquentiel (témoin A1, égalité au tirage près).

   2. Mais l'action touche la transition par UN canal : gagner éteint la
      cagnotte. Le seuil séquentiel vaut S plus la valeur future détruite
      en cas de gain, TOUJOURS au-dessus de S, jamais en dessous. Pour le
      joueur à une grille, ignorer ce supplément coûte au pire {worst1:.2%} du
      profit sur tout le balayage de α : le §29 tient, et c'est un
      renforcement. Pour un joueur dont les grilles sont une part VISIBLE
      du taux de chute (n·p/q ≳ 0,5), le supplément monte à des dixièmes
      de μ et le seuil statique laisse jusqu'à moitié du profit sur la
      table. La règle, sans α : comparer n·p au taux de chutes observé
      (celui que §36 fait déjà compter à l'app) ; tant que le rapport est
      petit, jouer au seuil du §5 bis ; sinon relever le seuil de la
      fraction de μ donnée par la colonne Δ/μ.

   3. Attendre PLUS que ce seuil corrigé est une erreur, exactement comme
      au §29 : la seule valeur d'attente qui existe en séquentiel est celle
      de ne pas s'auto-éteindre, et elle est entièrement contenue dans Δ.""")


# ==========================================================================
# B. LE CAPITAL COMME SECOND ÉTAT — atteindre Kelly sans se ruiner
# ==========================================================================

rule("B. LE CAPITAL — le théorème du compteur d'essais, puis le temps facturé")

M_GOAL = int(math.ceil(G_KELLY))          # 33 991 tickets à 1 franc
say(f"""   Objectif : W ≥ G = {G_KELLY:,.0f} francs (le capital minimal de §30,
   recalculé ici — pas recopié), en partant de W₀ < G, sans ruine (ruine =
   plus de quoi acheter un ticket). Le prix plancher du ticket interdit les
   fractions : l'état est le STOCK DE TICKETS M = W/c.

   B1. LE THÉORÈME. Chaque ticket gagne avec probabilité p, quel que soit
   le niveau de cagnotte auquel il est tiré — c'est l'invariance (E[hits] =
   k/4 dans tous les états). Le capital ne croît QUE par un gain. Donc pour
   TOUTE politique (niveaux visés, nombre de grilles, géométrie, ordre) :

       P(atteindre G avant la ruine) ≤ 1 − (1−p)^{{M₀}}

   par récurrence sur le stock — la branche gagnante d'un essai vaut au
   mieux 1. Et la borne est ATTEINTE par la politique audacieuse-en-
   cagnotte : ne tirer un ticket que lorsque la cagnotte affichée suffit à
   elle seule à boucler l'objectif (J ≥ G − W + c), car alors chaque gain
   est une victoire. Le capital est un compteur d'essais ; une politique ne
   choisit pas leur nombre, seulement le niveau de cagnotte où les dépenser.""")

MU_HAT = ALPHA_HAT * S


def solve_goal_dp(theta, alpha, m_goal, xs, nq=32, max_sweeps=200, tol=1e-12):
    """V(M) = P(but avant ruine) − θ·E[tirages consommés], stock M en tickets.

    Bellman : V(M) = max(0, max_x [ −θ·w(x) + p·WinE_x(M) ] + (1−p)·V(M−1))
    où w(x) = e^x / 13 tirages par ticket (13 grilles disjointes par tirage
    favorable, fraction e^{−x} des tirages, théorème J), et WinE_x moyenne
    V au stock M−1+J/c, J ~ x·μ + Exp(μ), succès si ≥ m_goal. Itération en
    « une victoire de plus par balayage » ; les pertes sont résolues en
    Gauss-Seidel ascendant à chaque balayage.
    """
    mu = alpha * S
    u = (np.arange(1, nq + 1) - 0.5) / nq
    V = np.zeros(m_goal)                  # V[M], M = 0..m_goal−1 ; but = 1
    offs = []
    for x in xs:
        J_q = mu * (x - np.log1p(-u))     # quantiles de x·μ + Exp(μ)
        offs.append(np.maximum(np.floor(J_q).astype(np.int64) - 1, 0))
    w_cost = np.array([theta * math.exp(x) / N_GRIDS for x in xs])
    best_arg = np.zeros(m_goal, dtype=np.int64)
    for sweep in range(max_sweeps):
        Bbest = np.full(m_goal, -np.inf)
        barg = np.zeros(m_goal, dtype=np.int64)
        for xi in range(len(xs)):
            acc = np.zeros(m_goal)
            for off in offs[xi]:
                if off >= m_goal:
                    acc += 1.0
                else:
                    acc[: m_goal - off] += V[off:]
                    acc[m_goal - off:] += 1.0
            Bx = P * (acc / nq) - w_cost[xi]
            better = Bx > Bbest
            Bbest[better] = Bx[better]
            barg[better] = xi
        Vn = np.zeros(m_goal)
        prev = 0.0
        for M in range(1, m_goal):
            v = Bbest[M] + (1 - P) * prev
            prev = v if v > 0.0 else 0.0
            Vn[M] = prev
        delta = float(np.abs(Vn - V).max())
        V = Vn
        best_arg = barg
        if delta < tol:
            break
    return V, best_arg, sweep + 1


def mc_goal(policy_x, m0, m_goal, alpha, n_rep, rng):
    """Rejoue une politique x(M) en « temps de victoires » — voie indépendante.

    Le nombre de tickets jusqu'à la prochaine victoire est Geom(p) QUEL QUE
    SOIT le niveau visé (l'invariance encore) ; seuls le temps d'attente et
    le saut en dépendent. Rend P(but), son erreur-type, E[tirages], et
    l'erreur-type du temps.
    """
    mu = alpha * S
    w_of = np.exp(policy_x) / N_GRIDS                 # tirages par ticket, par stock
    cumw = np.concatenate(([0.0], np.cumsum(w_of[1:])))  # cumw[M] = somme w(1..M)
    M = np.full(n_rep, m0, dtype=np.int64)
    t_used = np.zeros(n_rep)
    alive = np.ones(n_rep, dtype=bool)
    success = np.zeros(n_rep, dtype=bool)
    for _ in range(400):
        if not alive.any():
            break
        idx = np.flatnonzero(alive)
        bw = rng.geometric(P, idx.size)               # tickets jusqu'à victoire
        Mi = M[idx]
        spent = np.minimum(bw, Mi)
        t_used[idx] += cumw[Mi] - cumw[Mi - spent]
        ruined = bw > Mi
        M[idx[ruined]] = 0
        alive[idx[ruined]] = False
        winners = idx[~ruined]
        if winners.size:
            m_after = M[winners] - bw[~ruined]        # stock au moment du tir gagnant −1
            x_at = policy_x[np.minimum(m_after + 1, len(policy_x) - 1)]
            J = mu * (x_at + rng.exponential(1.0, winners.size))
            M_new = m_after + np.floor(J).astype(np.int64)
            done = M_new >= m_goal
            success[winners[done]] = True
            alive[winners[done]] = False
            M[winners] = np.minimum(M_new, m_goal - 1)
    p_hat = float(success.mean())
    se = math.sqrt(max(p_hat * (1 - p_hat), 1e-12) / n_rep)
    return p_hat, se, float(t_used.mean()), float(np.std(t_used)) / math.sqrt(n_rep)


X_GRID = np.concatenate([np.linspace(0.4, 6.0, 29),
                         np.linspace(6.5, 15.2, 19)])

say("\n   B2. TÉMOIN — au temps gratuit (θ=0), le DP doit rendre exactement")
say("       1 − (1−p)^M, la borne du théorème, atteinte par l'audace-en-cagnotte.")
V0, arg0, sw0 = solve_goal_dp(0.0, ALPHA_HAT, M_GOAL, X_GRID)
Ms_check = np.array([500, 1000, 5000, 20000, 33990])
closed = 1 - (1 - P) ** Ms_check
err0 = float(np.abs(V0[Ms_check] - closed).max())
say(f"       écart max au théorème sur 5 stocks : {err0:.1e} "
    f"({sw0} balayages)")
assert err0 < 1e-9
say(f"       P(atteindre G) depuis CHF 1 000 : {V0[1000]:.4f} — et depuis "
    f"CHF 10 000 : {V0[10000]:.4f}")
say(f"""       La borne est SANS α : 1 − (1−p)^(W₀/c). Mais son prix est le
       temps : viser J ≥ {G_KELLY:,.0f} n'arrive qu'à {math.exp(-G_KELLY / MU_HAT):.1e} des tirages
       (à α̂), soit une occasion tous les {1 / math.exp(-G_KELLY / MU_HAT) / DRAWS_PER_DAY / 365:,.0f} ans. Le théorème est
       vrai et inutilisable tel quel — d'où le temps facturé.""")

say("""
   B3. LE TEMPS FACTURÉ — V = P(but) − θ·E[tirages], balayé en θ. Chaque θ
       est un prix du tirage d'attente ; la frontière (durée, probabilité)
       et la politique J*(W) qui la réalise :""")
say("\n   θ            P(but) MC     E[durée] MC      politique J*(W) en francs (W = 1k / 5k / 20k)")
frontier = []
for theta in (0.0, 1e-8, 1e-7, 1e-6, 1e-5):
    if theta == 0.0:
        Vt, argt = V0, arg0
    else:
        Vt, argt, _ = solve_goal_dp(theta, ALPHA_HAT, M_GOAL, X_GRID)
    pol_x = X_GRID[argt]
    p_mc, se_p, t_mc, se_t = mc_goal(pol_x, 1000, M_GOAL, ALPHA_HAT, 60_000, RNG)
    frontier.append((theta, p_mc, t_mc, pol_x, Vt))
    v_pred = Vt[1000]
    v_mc = p_mc - theta * t_mc

    def _jstr(M):
        # dans la région d'abandon (V = 0), l'argmax n'est pas une politique
        return f"{pol_x[M] * MU_HAT:>9,.0f}" if Vt[M] > 0 else "  abandon"

    say(f"   {theta:<12.0e} {p_mc:.4f}±{se_p:.4f} {t_mc:>12,.0f}   "
        f"J* = {_jstr(1000)} / {_jstr(5000)} / "
        f"{_jstr(20000)}   [V: DP {v_pred:.4f} vs MC {v_mc:.4f}]")
    if v_pred > 0:
        assert abs(v_mc - v_pred) < 6 * (se_p + theta * se_t) + 1e-6

say("""
       Les deux voies se recoupent à chaque ligne (le DP par quadrature et
       balayages de victoires ; le Monte-Carlo par temps de victoires, qui
       ne partage ni la récursion ni la loi discrétisée). La structure de
       la politique est monotone et lisible : PLUS LE CAPITAL EST LOIN DU
       BUT, PLUS ON EST AUDACIEUX EN CAGNOTTE — viser haut, tirer rarement ;
       plus il en est proche, plus on redescend vers le seuil du §5 bis.
       C'est le renversement exact de la surmise du §30 : sous le plancher
       de capital, la bonne réponse n'est pas de miser plus gros à chaque
       occasion, c'est de miser AUSSI PETIT que possible sur des occasions
       PLUS RARES ET PLUS HAUTES.""")

# Le classique ressuscité : sous forte pression de temps, le DP tire-t-il
# SOUS le seuil de faveur ? (l'audace de Dubins-Savage, achetée au prix du temps)
Vt5, pol5 = frontier[-1][4], frontier[-1][3]
sub = np.flatnonzero((Vt5 > 0) & (pol5 < 1 / ALPHA_HAT))
if sub.size:
    say(f"""
       Et le théorème classique refait surface là où on l'attend : à
       θ = 10⁻⁵, sur {sub.size:,} niveaux de capital (de {sub.min():,} à {sub.max():,} francs),
       la politique optimale tire SOUS le seuil de faveur (J* < S) — des
       paris d'espérance négative, achetés parce que l'occasion favorable
       coûte plus de temps que le prix qu'on lui donne. « Sous jeu
       défavorable, audacieux » : la solution de Dubins-Savage n'avait pas
       disparu du problème, elle attendait qu'on facture le temps.""")
else:
    say("""
       À noter : même à θ = 10⁻⁵, aucun état ne fait tirer sous le seuil
       de faveur — l'audace sous-équitable de Dubins-Savage ne réapparaît
       pas dans la plage explorée.""")

say("""
   B4. LE NOMBRE DE GRILLES NE CHANGE PAS LA PROBABILITÉ — que le temps.
       13 grilles par tirage favorable ou 1 seule : mêmes essais, même
       P(but) ; seule la durée est divisée par 13. Vérifié par MC sur la
       politique θ=10⁻⁶ :""")
pol_ref = frontier[3][3]
p_a, se_a, t_a, _ = mc_goal(pol_ref, 1000, M_GOAL, ALPHA_HAT, 60_000, RNG)
say(f"       13/tirage : P = {p_a:.4f} ± {se_a:.4f}, durée {t_a:,.0f} tirages ;"
    f" 1/tirage : même P (mêmes essais), durée ×13 = {13 * t_a:,.0f} par construction.")

say("""
   B5. ET LA CROISSANCE, PRISE AU SÉRIEUX SOUS LE PLANCHER — l'extension de
       R2 (§36) à l'intégralité du ticket. Le rang progressif est un POT :
       empiler un second ticket sur la même grille ne fait que partager
       avec soi-même. La mise n'est donc pas une fraction continue mais un
       nombre de grilles disjointes n ∈ {0..13}, et le n optimal se calcule
       sur l'écran, sans α :

           n*(W, J) = argmax_n g_n,
           g_n = n·p·ln((W − n·c + J)/W) + (1 − n·p)·ln((W − n·c)/W)""")


def n_star(W, J):
    best = (0, 0.0)
    for n in range(1, N_GRIDS + 1):
        if n * C >= W:
            break
        g = n * P * math.log((W - n * C + J) / W) \
            + (1 - n * P) * math.log((W - n * C) / W)
        if g > best[1]:
            best = (n, g)
    return best


say("\n   n*(W, J) — grilles disjointes à jouer (0 = s'abstenir), croissance/occasion :")
say("   W \\ J        S        1,3·S      2·S        3·S        6·S")
J_cols = [1.0, 1.3, 2.0, 3.0, 6.0]
for W in (1_000, 3_000, 8_000, 17_000, 34_000, 100_000, 1_000_000):
    cells = []
    for jm in J_cols:
        n, g = n_star(W, jm * S)
        cells.append(f"{n:>2}" if n else " 0")
    say(f"   {W:>9,}   " + "        ".join(cells))

# la carte est-elle bang-bang ? balayage fin de la frontière
inter = set()
for W in np.geomspace(800, 120_000, 160):
    for jm in np.geomspace(1.0, 8.0, 160):
        n, _ = n_star(float(W), jm * S)
        if 0 < n < N_GRIDS:
            inter.add(n)
say(f"""
       Trois lignes de lecture. (1) Au capital de §30 et au-delà, n* = 13
       dès que J dépasse un seuil proche de S : on retrouve R2. (2) La
       carte est presque BANG-BANG — un balayage fin de 160×160 états ne
       trouve {"que les n intermédiaires " + str(sorted(inter)) + " sur une bande étroite"
              if inter else "AUCUN n intermédiaire"} : la contribution de
       chaque grille disjointe au log-rendement a le même signe, donc la
       décision est « toutes les treize ou rien », et l'information utile
       est la frontière J₀(W) ci-dessous. (3) Tout est lisible à l'écran :
       W, J, p, c — α absent, comme pour R2. La politique de but (B3) et la
       politique de croissance, deux objectifs étrangers, convergent vers
       la même forme : seuil de cagnotte croissant quand le capital baisse.""")

# seuil J en dessous duquel même 1 grille détruit la croissance, par W
say("   Seuil de cagnotte J₀(W) au-delà duquel une grille au moins devient")
say("   jouable en croissance (bissection exacte, sans α) :")
say("\n   W (francs)      J₀(W)/S    et à W → ∞ : doit tendre vers 1 (témoin §29)")
for W in (2_000, 5_000, 17_000, 34_000, 10_000_000):
    lo, hi = S, 60 * S
    if n_star(W, hi)[0] == 0:
        say(f"   {W:>12,}   injouable")
        continue
    for _ in range(80):
        mid = (lo + hi) / 2
        if n_star(W, mid)[0] > 0:
            hi = mid
        else:
            lo = mid
    say(f"   {W:>12,}   {hi / S:>7.3f}")


# ==========================================================================
# C. LA GÉOMÉTRIE, REMISE DANS LE TEMPS — la bascule a-t-elle un état où mordre ?
# ==========================================================================

rule("C. LA GÉOMÉTRIE SELON L'ÉTAT — le témoin d'abord, le rang partagé ensuite")

say("""   Le théorème de bascule (§26) : un objectif convexe préfère concentrer
   les grilles, un concave les étaler, et le SIGNE de l'espérance décide
   lequel s'applique. En séquentiel, l'état — cagnotte et capital — fixe à
   la fois le signe du jeu et la distance au but : la géométrie devrait
   donc dépendre de l'état. Elle en dépend, sur un rang à gain FIXE (C1) ;
   elle n'en dépend PAS sur le rang partagé (C2), parce qu'empiler y
   revient à partager le pot avec soi-même.

   Une intuition corrigée en route, et il faut la raconter : la première
   version de ce témoin attendait « étaler près du but, concentrer loin »,
   par la seule courbure de U. La table a répondu CONCENTRER sur toute la
   colonne : dans un jeu sous-équitable, l'érosion du capital entre deux
   gains stérilise les volées tardives dès que le saut étalé ne reboucle
   pas l'objectif — c'est l'audace de Dubins-Savage, et elle vaut même tout
   près du but. Le critère n'est pas la distance seule : c'est « LE SAUT
   ÉTALÉ SUFFIT-IL, d'où l'on tirera encore ? » — une fonction jointe du
   signe du jeu et de l'état. Le témoin ci-dessous le montre dans les deux
   sens.

   C1. TÉMOIN — rang à gain fixe g par ticket (non partagé), volée de 13
   tickets, stock 300 francs, objectif +Δ avant ruine. Empilés : prob p,
   saut +13g ; disjoints : prob 13p, saut +g. Même coût, même espérance.""")


def u_fixed_rank(m0, gap, g_prize, stacked):
    """P(atteindre +gap avant la ruine) en jouant CE rang en boucle — petit
    DP exact par balayages de victoires (mêmes principes qu'en B)."""
    jump = int(13 * g_prize) if stacked else int(g_prize)
    p_win = P if stacked else N_GRIDS * P
    cost = 13
    goal = m0 + int(gap)
    V = np.zeros(goal)
    for _ in range(400):
        Vn = np.zeros(goal)
        for M in range(cost, goal):
            tgt = M - cost + jump
            win_val = 1.0 if tgt >= goal else V[tgt]
            Vn[M] = p_win * win_val + (1 - p_win) * Vn[M - cost]
        if float(np.abs(Vn - V).max()) < 1e-13:
            V = Vn
            break
        V = Vn
    return V[m0]


N_VOLLEYS = (300 - 13) // 13 + 1                      # volées finançables : 23
closed_st = 1 - (1 - P) ** N_VOLLEYS                  # « toutes volées vivantes »
closed_dj = 1 - (1 - N_GRIDS * P) ** N_VOLLEYS
say("\n   g (rang)    RTP      Δ (objectif)   empilées      disjointes    préférée")
cases = [(30, 15), (30, 200), (12000, 5000), (12000, 12500)]
prefs = []
for g_prize, gap in cases:
    u_st = u_fixed_rank(300, gap, g_prize, True)
    u_dj = u_fixed_rank(300, gap, g_prize, False)
    prefs.append(u_st > u_dj)
    rtp = g_prize * P
    say(f"   {g_prize:<11,} {rtp:<8.2%} {gap:<14,} {u_st:<13.5f} {u_dj:<13.5f} "
        + ("CONCENTRER" if u_st > u_dj else "ÉTALER"))
# formes fermées (seconde voie) là où chaque victoire boucle l'objectif :
u_st_check = u_fixed_rank(300, 15, 30, True)          # saut 390 ≥ Δ+13k partout
assert abs(u_st_check - closed_st) < 1e-12
u_st_sup = u_fixed_rank(300, 5000, 12000, True)
u_dj_sup = u_fixed_rank(300, 5000, 12000, False)
assert abs(u_st_sup - closed_st) < 1e-12 and abs(u_dj_sup - closed_dj) < 1e-12
say(f"""
   Recoupement par forme fermée (là où toute victoire boucle l'objectif,
   P = 1 − (1−p_gain)^23) : empilées {closed_st:.5f}, disjointes {closed_dj:.5f} —
   le DP les retrouve au zéro machine.

   La bascule du §26 est donc REPRODUITE, et son axe est bien celui que le
   théorème nommait : le SIGNE du jeu. Sous-équitable (g = 30), la
   concentration gagne — y compris tout près du but, l'érosion aidant :
   c'est la branche audacieuse. Sur-équitable (g = 12 000), l'étalement
   gagne — à Δ = 5 000 par la probabilité ×13, et même à Δ = 12 500, où le
   saut étalé ne boucle plus d'un coup, parce que chaque gain ré-arme un
   stock assez gros pour regagner : la timidité est robuste en régime
   favorable. Or dans CE jeu, le signe est indexé par l'état : sous le
   seuil de cagnotte le pari est défavorable, au-dessus favorable. Sur un
   rang à gain fixe, la géométrie optimale DÉPENDRAIT donc de l'état,
   exactement comme la mission le conjecturait. Maintenant, le rang qui
   compte :""")
assert prefs == [True, True, False, False], prefs

say("""   C2. LE RANG PARTAGÉ. À une occasion de cagnotte J, avec W autres
   gagnants ~ Poisson(λ) : 13 grilles DISJOINTES touchent J/(1+W) avec
   probabilité 13p ; 13 tickets EMPILÉS touchent 13J/(13+W) avec
   probabilité p. Empiler n'a de valeur que si la foule est là (prendre
   une part plus grosse d'un pot disputé) ; sans foule, le pot est le même
   et seule la probabilité diffère — d'un facteur 13. Différence d'utilité
   sous U(M) = 1 − (1−p)^M (l'objectif de but, exact au temps gratuit),
   balayée sur stock × cagnotte × foule :""")


def geometry_gap_shared(M, J, lam, wmax=80):
    """EU(disjoint) − EU(empilé) sous U(M)=1−(1−p)^M ; Poisson tronquée."""
    def U(m):
        m = max(m, 0.0)
        if m >= M_GOAL:
            return 1.0
        return 1 - (1 - P) ** m
    logw = -lam
    eu_d = eu_s = 0.0
    for wcnt in range(wmax):
        pw = math.exp(logw)
        eu_d += pw * (13 * P * U(M - 13 + J / (1 + wcnt))
                      + (1 - 13 * P) * U(M - 13))
        eu_s += pw * (P * U(M - 13 + 13 * J / (13 + wcnt))
                      + (1 - P) * U(M - 13))
        logw += math.log(max(lam, 1e-300)) - math.log(wcnt + 1)
    return eu_d - eu_s


say("\n   λ (foule)   pire écart disjoint−empilé sur 42 états (M × J)  signe")
states_M = [500, 1000, 3000, 8000, 17000, 25000, 33000]
states_J = [1.0, 1.3, 2.0, 3.0, 4.4, 6.0]
for lam in (0.0, 0.006, 0.065, 0.3, 0.65, 2.0, 5.0):
    worst = min(geometry_gap_shared(M, jm * S, lam)
                for M in states_M for jm in states_J)
    say(f"   {lam:<11.3f} {worst:>+12.3e}"
        + ("   disjoint partout" if worst >= 0 else "   EMPILER quelque part"))

say(f"""
   Le disjoint domine dans TOUS les états, et c'est PLUS fort que ce que
   la prudence annonçait : même à λ = 5 — cinq gagnants par tirage, un
   régime où une cagnotte progressive ne peut plus exister (§29 : κ s'y
   effondre et le partage y tue la stratégie entière bien avant) — l'écart
   se resserre sans jamais changer de signe. La raison est structurelle :
   quand les deux sauts bouclent l'objectif, seule la probabilité compte,
   et elle vaut 13 contre 1 ; quand ils ne le bouclent pas, la part d'un
   empilement (13J/(13+W)) ne dépasse assez celle d'une grille disjointe
   (J/(1+W)) que pour une foule nombreuse — où le théorème H a déjà réduit
   l'écart d'espérance sans le renverser.

   Conclusion pour l'app, et elle est actionnable par sa négation : NON,
   les douze grilles ne doivent PAS changer de géométrie selon la cagnotte.
   Disjointes partout. La bascule du §26 est réelle (témoin C1) mais elle
   n'a, dans ce jeu, aucun état où s'exercer : le régime convexe qui
   préférerait la concentration ne concerne que des rangs à gain fixe, or
   (i) le rang joué au-dessus du seuil est le rang progressif, partagé —
   empiler y revient à partager avec soi-même ; (ii) sous le seuil, la
   politique optimale de A et de B est de ne pas jouer, et une géométrie de
   mises qu'on ne pose pas n'a pas à être optimisée.""")


# ==========================================================================
# D. Ce qui dépend de α, et ce qui n'en dépend pas
# ==========================================================================

rule("D. L'INVENTAIRE DE ROBUSTESSE — règles sans α, rythmes avec")

say("""   Balayage final : les REGLES aux bornes de l'intervalle du §29
   (α de 0,08 à 11,65), à politique de but θ·E[t] facturé (θ = 10⁻⁶) :""")
say("\n   α        J*(W=1k)/gap   J*(W=20k)/gap   P(but) depuis 1k (borne 1−(1−p)^M : {:.4f})"
    .format(1 - (1 - P) ** 1000))
band = []
for alpha_v in (0.08, 0.295, 1.0, 3.0):
    Vt, argt, _ = solve_goal_dp(1e-6, alpha_v, M_GOAL, X_GRID)
    pol = X_GRID[argt]
    mu_v = alpha_v * S
    gap1 = G_KELLY - 1000
    gap2 = G_KELLY - 20000
    if Vt[1000] <= 0:
        say(f"   {alpha_v:<8.3g} abandon — à ce prix du temps, la stratégie ne "
            "vaut plus d'être tentée depuis CHF 1 000")
        continue
    p_mc, se_p, t_mc, _ = mc_goal(pol, 1000, M_GOAL, alpha_v, 120_000, RNG)
    band.append(pol[1000] * mu_v / gap1)
    say(f"   {alpha_v:<8.3g} {pol[1000] * mu_v / gap1:<14.3f} "
        f"{pol[20000] * mu_v / gap2:<15.3f} {p_mc:.4f} ± {se_p:.4f}   "
        f"(durée {t_mc / DRAWS_PER_DAY:,.0f} jours)")

say(f"""
   Ce tableau est le verdict de robustesse, et il reprend la partition du
   §36 en l'étendant au séquentiel :

   SANS α (lisible à l'écran, robuste à tout l'intervalle du §29) :
     - la règle d'admission « jouer ssi J ≥ S » (A, exacte quand n·p/q → 0,
       et corrigée par n·p/q OBSERVÉ sinon — pas par α) ;
     - la borne P(atteindre Kelly) = 1 − (1−p)^(W₀/c) et la politique
       audacieuse-en-cagnotte qui l'atteint : « viser J ≥ ce qui manque » —
       le seuil se lit sur l'écart au but, pas sur un paramètre estimé ;
     - le nombre de grilles n*(W, J) et le seuil J₀(W) de B5 ;
     - la géométrie : disjointes, dans tous les états (C).

   AVEC α (les rythmes — combien d'occasions, combien de temps) :
     - la fréquence des occasions à chaque niveau (théorème J), donc les
       DURÉES de la frontière de B3 — d'un ordre de grandeur à l'autre
       selon α — et le niveau fin J*(W) quand on facture le temps : sur ce
       balayage, J*(1k)/gap court de {min(band):.2f} à {max(band):.2f}. Le POINT de la
       frontière qu'on occupe dépend de α ; la FORME de la politique
       (seuil croissant quand le capital baisse, mise minimale) n'en
       dépend pas.

   Et rien de tout ceci ne prédit un numéro : chaque essai reste une
   Bernoulli(p), E[hits] = k/4 dans tous les états — c'est même la raison
   pour laquelle le théorème de B1 est vrai.""")

say(f"\n   Registre : inchangé. h36 ne teste pas l'archive — il prouve, il")
say(f"   corrige, et il ferme une question que le dossier n'avait pas posée.")

rule(f"total {time.time() - T0:.0f}s")
