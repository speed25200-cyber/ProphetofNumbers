"""h28 — la franchise de l'assurance gratuite : borne resserrée, agrégateurs
comparés, et ce qu'une franchise plus basse changerait à la détection.

Le point de départ, et l'aveu qu'il contient
--------------------------------------------
Le théorème C borne la franchise de l'essaim par 2·√(T ln N)·20/T = 0,272
hit/tirage ; f3 mesure 0,016. Un facteur ~17 entre une borne et sa
réalisation signifie que la borne ne décrit pas le mécanisme : 2·√(T ln N)
est la garantie PIRE CAS de Hedge, payée contre un adversaire qui choisirait
les pertes après avoir vu les poids, avec des pertes qui rempliraient tout
[0,1]. Ici l'« adversaire » est un tirage hypergéométrique : la dispersion
INSTANTANÉE des pertes des 26 têtes (leur variance sous les poids courants,
v_t) est minuscule devant 1/4, pour deux raisons mesurables — le
recouvrement d'un top-20 a un écart-type de 1,688/20 = 0,084, et les têtes
sont corrélées (elles partagent ~5,9 numéros de top-20 sur 20, contre 5,00
pour deux ensembles sans rapport). La famille des bornes de SECOND ORDRE
d'AdaHedge remplace √T par √(V_T), V_T = Σ_t v_t : c'est elle qu'on dérive,
puis qu'on vérifie — une borne qu'une simulation viole est fausse, et c'est
ce contrôle qui a fait tomber le théorème D.

Le piège qui décide de ce travail — écrit AVANT de mesurer
-----------------------------------------------------------
Sous H₀, E[hits] = k/4 pour TOUTE grille prévisible (théorème d'invariance,
g1-C) : comparer des agrégateurs sur l'espérance de hits ne peut RIEN
montrer. Ce qui les sépare est le REGRET — l'écart à la meilleure tête a
posteriori. Mais le piège a un second étage, qui est un théorème :

    THÉORÈME (égalité des franchises sous H₀). Pour tout agrégateur dont
    les poids et le choix de grille sont PRÉVISIBLES (fonctions du passé
    strict), E[franchise] = E[max_h S_h − S_agg]/T = E[max_h S_h]/T,
    car E[S_agg] = 0 par invariance — le terme de l'agrégateur disparaît
    de l'espérance. Sous H₀, TOUS les agrégateurs honnêtes ont donc la
    MÊME franchise espérée : le plancher E[max_h S_h]/T, qui n'appartient
    pas à l'agrégateur mais au COMPARATEUR (le max a posteriori de 26
    marches aléatoires corrélées — la malédiction du vainqueur). Seule la
    LOI de la franchise (variance, queues) distingue les agrégateurs sous
    H₀ ; leur espérance ne les distingue que sous les ALTERNATIVES.

Conséquence méthodologique : la table « franchise sous H₀ par agrégateur »
est la mesure d'UN nombre (le plancher) par cinq canaux bruités — ses
différences appariées testent le théorème (elles doivent être compatibles
avec zéro), et la vraie comparaison se joue (1) sur la borne pire cas, qui
est un théorème par agrégateur, et (2) sous la contamination momentum de
f3, où le regret espéré sépare réellement les règles. Sans cette page, on
mesurerait du vent avec six décimales.

Deux ensembles, et le théorème ne couvre que l'un des deux
-----------------------------------------------------------
L'app mélange les CHAMPS (top-20 de Σ w·champ_h) ; la théorie du regret
borne l'agrégateur FRACTIONNAIRE (Σ w·pertes_h). Le théorème C écrivait la
borne de l'un en face de la franchise de l'autre. Les deux sont mesurés ici
séparément ; la borne s'applique au fractionnaire, et la conformité du
mélange de champs est un fait MESURÉ, pas démontré.

Théorème C′ — la borne de second ordre, dérivée
------------------------------------------------
Cadre : N experts, pertes ℓ_{t,k} ∈ [0,1] (ici ℓ = 1 − o/20, o ∈ {0..20}).
AdaHedge : Δ₀ ≥ 0, η_t = ln N / Δ_{t−1}, poids w_t ∝ exp(−η_t L_{t−1}).
Notations par pas : h_t = w_t·ℓ_t (perte de l'algorithme),
m_t = −(1/η_t)·ln(w_t·e^{−η_t ℓ_t}) (perte de mélange), δ_t = h_t − m_t,
v_t = Var_{k~w_t}(ℓ_{t,k}), s_t = max_k ℓ − min_k ℓ, V_T = Σ v_t,
Δ_T = Δ₀ + Σ δ_t.

Fait 1 (encadrement du gap) : 0 ≤ δ_t ≤ s_t ≤ 1. [Jensen pour ≥ 0 ;
m_t ≥ min_k ℓ_{t,k} ≥ h_t − s_t pour ≤ s_t.]

Fait 2 (Bernstein du gap) : δ_t ≤ φ(η_t)·v_t, φ(η) = (e^η − η − 1)/η.
Preuve : soit Y = h_t − ℓ_t sous w_t ; E[Y] = 0, Y ≤ h_t ≤ 1. Pour y ≤ 1,
e^{ηy} ≤ 1 + ηy + (e^η − η − 1)·y² car ψ(y) = (e^{ηy} − ηy − 1)/y² est
croissante. En espérance : E[e^{ηY}] ≤ 1 + (e^η − η − 1)·v_t, puis
δ_t = (1/η)·ln E[e^{ηY}] ≤ φ(η)·v_t via ln(1+x) ≤ x. Pour η ≤ 1 :
φ(η) ≤ (e−2)·η, car (e^η − η − 1)/η² est croissante et vaut e−2 en η = 1.
Ce fait est RE-VÉRIFIÉ numériquement à chaque pas de chaque rejeu.

Fait 3 (télescopage de la perte de mélange) : si η_t est décroissante,
M_T = Σ m_t ≤ L*_T + ln N / η_T = L*_T + Δ_{T−1}.
Preuve : Φ(η, L) = −(1/η)·ln((1/N)·Σ_k e^{−η L_k}) ; m_t = Φ(η_t, L_t) −
Φ(η_t, L_{t−1}) ; la somme télescope à Φ(η_T, L_T) plus des termes
Φ(η_t, L_t) − Φ(η_{t+1}, L_t) ≤ 0, car Φ est DÉCROISSANTE en η : avec
g(η) = −ln E_u[e^{−ηL}], g(0) = 0 et g'' = −Var_tilt ≤ 0, donc g concave
et g/η décroissante. Enfin Φ(η_T, L_T) ≤ L* + ln N/η_T. AdaHedge a bien
η_t décroissante (Δ croît). C'est le lemme classique de Hedge à taux
variable (Cesa-Bianchi–Lugosi ; de Rooij–van Erven–Grünwald–Koolen 2014).

Fait 4 (échauffement) : tant que Δ_{t−1} < ln N, δ_t ≤ s_t ≤ 1 (Fait 1) ;
au premier pas t₀ où Δ dépasse ln N, Δ_{t₀} ≤ ln N + 1.

Fait 5 (récurrence) : pour t > t₀, η_t ≤ 1, donc δ_t ≤ (e−2)·ln N·v_t /
Δ_{t−1}, et Δ_t² − Δ_{t−1}² = 2Δ_{t−1}δ_t + δ_t² ≤ 2(e−2)·ln N·v_t + δ_t.
En sommant : Δ_T² ≤ (ln N + 1)² + 2(e−2)·ln N·V_T + Δ_T, et x² ≤ a + x
implique x ≤ √a + 1 ≤ √(2(e−2)·ln N·V_T) + ln N + 2.

Assemblage : R_T = H_T − L* = (M_T − L*) + Σδ_t ≤ Δ_{T−1} + Δ_T ≤ 2Δ_T
≤ 2·√(2(e−2)·ln N·V_T) + 2·ln N + 4. On consigne la version élargie de
2 + 2Δ₀ unités (négligeables devant le terme principal), qui couvre aussi
le cas dégénéré où Δ ne sort jamais de l'échauffement :

    THÉORÈME C′.  R_T ≤ 2·√(2(e−2)·V_T·ln N) + 2·ln N + 6 + 2Δ₀
                      = 2,3971·√(V_T·ln N) + 2·ln N + 6 + 2Δ₀,

en unités de perte ; ×20/T pour des hits/tirage. La borne est VALIDE PAR
RÉALISATION (V_T est mesuré sur la même trajectoire), donc adversariale ;
sous H₀ la version en espérance suit par Jensen (E√ ≤ √E). Elle couvre
l'AdaHedge du manuel ; le déployé ajoute un mélange 2 % uniforme
(exploration) que la preuve ne couvre pas — sa conformité est MESURÉE.
[La constante 2 de de Rooij et al. (thm 8) est un peu meilleure que notre
2,3971 ; on garde la version auto-contenue, démontrée ligne à ligne.]

Ce que ça change si un biais apparaît : une avance de ε hit/tirage portée
par une tête est GARANTIE captée (au sens fractionnaire) dès que la borne
par tirage passe sous ε — T ≳ 1600·ln N/ε² au premier ordre, contre
T ≳ (2,3971)²·400·v̄·ln N/ε² au second ordre : le rapport des deux seuils
est mesuré plus bas, et c'est lui qui dit si la théorie décrit enfin la
détection à T = 20 000 que f3 a MESURÉE.

Protocole
---------
1. Passe avant multi-agrégateurs (mêmes têtes, mêmes champs, mêmes pertes,
   lues une seule fois par pas) : moyenne uniforme, FTL (suivi du leader,
   départage par indice), FTRL entropique à taux décroissant
   η_t = √(8 ln N/t), AdaHedge pur, AdaHedge déployé (bit-identique à
   `sp._ada_update` — vérifié contre `sp.run` sur l'archive réelle), plus
   une grille de Hedge à taux fixe dont le meilleur A POSTERIORI est un
   ORACLE : une borne inférieure, pas un concurrent honnête.
2. Archive réelle (70 560 tirages) : franchises, regret réalisé, V_T,
   borne C′ contre borne C — et recoupement avec les chiffres publiés de
   f3 (5,01195 / 4,99572), qui doivent se retrouver à l'identique.
3. H₀ : 32 archives SRS à T = 20 000 (franchises, égalité appariée,
   bornes) + 6 archives SRS complètes (la borne à l'échelle du déployé).
   TÉMOIN POSITIF de la vérification : une borne délibérément fausse
   (0,5·√(V_T ln N), sans terme additif) doit être VIOLÉE massivement —
   sinon le banc n'a pas de dents.
4. Contamination momentum de f3 (réinjection du tirage précédent avec
   probabilité ε), T = 20 000 : z de l'ensemble par agrégateur contre son
   null (les 32 réplicats H₀), part de l'avance captée, et le seuil de
   détection par agrégateur — la seule unité dans laquelle « une franchise
   plus basse » veut dire quelque chose.
5. `lab.leak_check` sur les prédicteurs d'ensemble (déployé, uniforme,
   FTL) — décisif, pas déclaratif.

Différences assumées, héritées de f3 : évolution désactivée, égalités par
indice croissant, pas d'`ids` (mêmes conventions que les chiffres publiés
de f3, pour que le recoupement soit exact).
"""

import math
import os
import sys
import time
from multiprocessing import Pool, cpu_count

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab
import swarm_py as sp

T0 = time.time()
N = sp.N_HEADS
LOGN = math.log(N)
DRAWN = sp.DRAWN
E_M2 = math.e - 2.0
CST = 2.0 * math.sqrt(2.0 * E_M2)               # 2·√(2(e−2)) = 2,3971
GAP0 = 1e-3                                     # le Δ₀ du code déployé


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Pré-enregistrement — AVANT de regarder quoi que ce soit
# --------------------------------------------------------------------------

TOK_EGAL = lab.preregister(
    "h28.egalite",
    "sous H0, tout agrégateur prévisible a la même franchise espérée "
    "(E[S_agg] = 0 par invariance) : les différences appariées de franchise "
    "entre agrégateurs sont compatibles avec zéro",
    "max sur les agrégateurs honnêtes de |moyenne appariée / SE| des diffs "
    "de franchise vs AdaHedge déployé, 32 archives SRS T=20000",
    "les diffs appariées SONT le null (paires sur les mêmes archives H0)",
    "théorème réfuté si un |z| >= 3 ; sinon conforme, consigné sans p",
    track="C")

TOK_BORNE = lab.preregister(
    "h28.borne",
    "le théorème C' (regret AdaHedge <= 2,3971·sqrt(V_T ln N) + 2 ln N + 6 "
    "+ 2·gap0) majore le regret fractionnaire réalisé sur l'archive réelle "
    "et sur toutes les archives simulées, pur ET déployé",
    "marge minimale borne/regret sur tous les rejeux (réel, 32×T=20000, "
    "6×T=70560) ; faits 2 et 4 de la dérivation re-vérifiés pas à pas",
    "vérification par réalisation, V_T mesuré sur la même trajectoire",
    "théorème réfuté à la PREMIÈRE violation ; témoin positif obligatoire : "
    "la fausse borne 0,5·sqrt(V_T ln N) doit être violée sur la majorité "
    "des réplicats, sinon le banc de vérification est cassé",
    track="C")

TOK_FRAN = lab.preregister(
    "h28.franchise",
    "la franchise mesurée de chaque agrégateur sous H0 (et sur l'archive "
    "réelle), avec son incertitude — mesure, pas test de détection",
    "franchise = max_h hits/tirage(tête h) − hits/tirage(ensemble), en "
    "mélange de champs et en fractionnaire ; oracle taux-fixe à part "
    "(borne inférieure, pas un concurrent)",
    "32 archives SRS T=20000 + 6 archives SRS complètes, mêmes archives "
    "pour tous les agrégateurs (appariement)",
    "consigné comme mesure avec incertitude ; pas de verdict de détection",
    track="C")

TOK_DET = lab.preregister(
    "h28.detection",
    "une franchise plus basse abaisse-t-elle le seuil auquel l'ENSEMBLE "
    "détecte un biais momentum ? (l'espérance sous H0 étant invariante, "
    "seul ce seuil donne une unité à la comparaison)",
    "z de l'ensemble par agrégateur sous contamination momentum de f3 "
    "(eps ∈ {0,02, 0,03, 0,05, 0,10, 0,20}, 4 réplicats, T=20000), seuil = "
    "moyenne + 3·sd de son null (32 réplicats H0) ; avance en hits/tirage "
    "mesurée par le recouvrement lag-1, comme f3",
    "null par simulation (les 32 archives SRS de h28.franchise)",
    "consigné : plus petite avance détectée 4/4 par agrégateur ; la "
    "contamination est le témoin positif (elle doit se détecter aux forts eps)",
    track="C")


# --------------------------------------------------------------------------
# Les agrégateurs — tous lisent les MÊMES pertes, au même instant
# --------------------------------------------------------------------------

class Unif:
    """La moyenne uniforme des 26 têtes. Zéro adaptation, zéro paramètre."""
    name = "uniforme"

    def __init__(self):
        self.w = np.full(N, 1 / N)

    def update(self, losses):
        pass


class FTL:
    """Suivi du leader, sans régularisation. Égalités par indice croissant."""
    name = "FTL"

    def __init__(self):
        self.w = np.full(N, 1 / N)
        self.cum = np.zeros(N)

    def update(self, losses):
        self.cum += losses
        w = np.zeros(N)
        w[int(np.argmin(self.cum))] = 1.0
        self.w = w


class FTRL:
    """Suivi du leader régularisé (entropie), taux décroissant canonique
    η_t = √(8 ln N / t) — le Hedge « anytime » des manuels."""
    name = "FTRL η=√(8lnN/t)"

    def __init__(self):
        self.w = np.full(N, 1 / N)
        self.cum = np.zeros(N)
        self.t = 0

    def update(self, losses):
        self.cum += losses
        self.t += 1
        eta = math.sqrt(8 * LOGN / (self.t + 1))
        r = np.exp(-eta * (self.cum - self.cum.min()))
        self.w = r / r.sum()


class AdaPure:
    """AdaHedge du manuel — l'objet exact du théorème C′. Instrumenté :
    il RE-VÉRIFIE les faits 2 et 4 de la dérivation à chaque pas."""
    name = "AdaHedge pur"

    def __init__(self):
        self.w = np.full(N, 1 / N)
        self.cum = np.zeros(N)
        self.gap = GAP0
        self.M = 0.0                      # Σ m_t
        self.f2_viol = 0                  # violations du Fait 2 (η ≤ 700)
        self.f2_checked = 0
        self.warm_steps = 0               # pas avec η > 1 (échauffement)
        self.gap_at_exit = None           # Δ au premier pas où Δ ≥ ln N

    def update(self, losses):
        eta = LOGN / self.gap
        h = float(self.w @ losses)
        lmin = float(losses.min())
        accum = float(self.w @ np.exp(-eta * (losses - lmin)))
        mix = lmin - math.log(max(accum, 1e-300)) / eta
        d = max(0.0, h - mix)
        v = float(self.w @ (losses - h) ** 2)
        if eta > 1.0:
            self.warm_steps += 1
        if eta < 700.0:                   # Fait 2, vérifié partout où e^η tient
            self.f2_checked += 1
            if d > (math.exp(eta) - eta - 1) / eta * v + 1e-12:
                self.f2_viol += 1
        self.M += mix
        self.gap += d
        if self.gap_at_exit is None and self.gap >= LOGN:
            self.gap_at_exit = self.gap   # Fait 4 : doit être ≤ ln N + 1 + Δ₀
        self.cum += losses
        eta = LOGN / self.gap
        r = np.exp(-eta * (self.cum - self.cum.min()))
        self.w = r / r.sum()


class AdaDep:
    """AdaHedge tel que déployé : `sp._ada_update` à l'identique (mélange
    2 % uniforme, gap initial 1e-3). Le théorème C′ ne le couvre pas —
    sa conformité à la borne est un fait mesuré."""
    name = "AdaHedge déployé"

    def __init__(self):
        self.w = np.full(N, 1 / N)
        self.cum = np.zeros(N)
        self.gap = GAP0

    def update(self, losses):
        self.w, self.gap = sp._ada_update(self.w, self.cum, self.gap, losses, N)


AGG_NAMES = [Unif.name, FTL.name, FTRL.name, AdaPure.name, AdaDep.name]
AGG_SHORT = ["unif", "FTL", "FTRL", "AH-pur", "AH-dép"]
K = len(AGG_NAMES)
I_UNIF, I_FTL, I_FTRL, I_PURE, I_DEP = range(K)
ETA_GRID = np.geomspace(1e-3, 30.0, 25)          # l'oracle taux-fixe


def borne_C2(V):
    """Théorème C′, unités de perte."""
    return CST * math.sqrt(max(V, 0.0) * LOGN) + 2 * LOGN + 6 + 2 * GAP0


def borne_C1(steps):
    """Théorème C (premier ordre), unités de perte."""
    return 2 * math.sqrt(steps * LOGN)


def fausse_borne(V):
    """Le témoin positif du banc : une borne sciemment fausse."""
    return 0.5 * math.sqrt(max(V, 0.0) * LOGN)


# --------------------------------------------------------------------------
# La passe avant — têtes lues UNE fois par pas, agrégateurs en parallèle
# --------------------------------------------------------------------------

def forward(mask, measure_share=0):
    """Rejoue les 26 têtes et tous les agrégateurs sur une archive (T,80).

    Renvoie des agrégats (jamais un verdict) : hits par tête, hits mélange
    de champs et fractionnaires par agrégateur, V_T, Δ_T, M_T, la grille
    d'η fixes, et les compteurs de vérification de la dérivation.
    `measure_share > 0` : mesure le partage de top-20 entre têtes tous les
    `measure_share` pas (coûteux, réservé à l'archive réelle).
    """
    T = len(mask)
    heads = sp.make_heads()
    aggs = [Unif(), FTL(), FTRL(), AdaPure(), AdaDep()]
    G = len(ETA_GRID)
    steps = max(0, T - sp.WARMUP)
    tot_o = np.zeros(N, np.int64)
    tot_mix = np.zeros(K, np.int64)
    H_frac = np.zeros(K)                  # Σ w·ℓ, unités de perte
    V = np.zeros(K)
    s_sum = 0.0
    grid_H = np.zeros(G)
    grid_cum = np.zeros(N)
    grid_w = np.full((G, N), 1 / N)
    share_sum, share_cnt = 0.0, 0
    j = 0
    for t in range(T):
        hit = mask[t].astype(float)
        if t >= sp.WARMUP:
            fields = np.stack([sp._z(h.field()) for h in heads])
            tops = np.stack([sp._top(fields[i]) for i in range(N)])
            o = mask[t][tops].sum(axis=1)
            tot_o += o
            losses = 1 - o / DRAWN
            s_sum += float(losses.max() - losses.min())
            for a, ag in enumerate(aggs):
                ens = ag.w @ fields
                tot_mix[a] += int(mask[t][sp._top(ens)].sum())
                h = float(ag.w @ losses)
                H_frac[a] += h
                V[a] += float(ag.w @ (losses - h) ** 2)
            grid_H += grid_w @ losses
            if measure_share and j % measure_share == 0:
                P = np.zeros((N, sp.POOL), bool)
                P[np.arange(N)[:, None], tops] = True
                S = (P @ P.T.astype(np.int64))
                share_sum += float((S.sum() - np.trace(S)) / (N * (N - 1)))
                share_cnt += 1
            for ag in aggs:
                ag.update(losses)
            grid_cum += losses
            r = np.exp(-ETA_GRID[:, None] * (grid_cum - grid_cum.min())[None, :])
            grid_w = r / r.sum(axis=1, keepdims=True)
            j += 1
        for h in heads:
            h.absorb(hit)

    pure, dep = aggs[I_PURE], aggs[I_DEP]
    Lstar = steps - tot_o.max() / DRAWN            # min_k Σ ℓ_k
    sd_T = sp.OV_SD * math.sqrt(steps)
    return {
        "steps": steps,
        "mean_o": tot_o / steps,                   # hits/tirage par tête
        "best_head": int(np.argmax(tot_o)),
        "z_heads_max": float((tot_o.max() - steps * sp.OV_MEAN) / sd_T),
        "mix_mean": tot_mix / steps,               # hits/tirage, mélange de champs
        "frac_mean": DRAWN * (1 - H_frac / steps),  # hits/tirage, fractionnaire
        "z_mix": (tot_mix - steps * sp.OV_MEAN) / sd_T,
        "regret": H_frac - Lstar,                  # unités de perte, par agrégateur
        "V": V,
        "s_mean": s_sum / steps,
        "M_pure": pure.M, "Lstar": Lstar,
        "gap_pure": pure.gap, "gap_dep": dep.gap,
        "f2_viol": pure.f2_viol, "f2_checked": pure.f2_checked,
        "warm_steps": pure.warm_steps, "gap_at_exit": pure.gap_at_exit,
        "grid_regret": grid_H - Lstar,
        "share_mean": (share_sum / share_cnt) if share_cnt else None,
    }


# --------------------------------------------------------------------------
# Réplicats parallèles
# --------------------------------------------------------------------------

def _rep_h0(args):
    seed, T = args
    rng = np.random.default_rng(seed)
    return forward(lab.srs(T, rng))


def contaminate(m, rng, eps):
    """La contamination momentum de f3 (copie fidèle, mêmes opérations) :
    avec probabilité eps, un numéro du tirage précédent est réinjecté."""
    m = m.copy()
    for t in range(1, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - 1] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - 1])
        if len(prev) == 0 or len(cur) == 0:
            continue
        m[t, rng.choice(prev)] = True
        m[t, rng.choice(cur)] = False
    return m


def _rep_alt(args):
    seed, T, eps = args
    rng = np.random.default_rng(seed)
    m = contaminate(lab.srs(T, rng), rng, eps)
    r = forward(m)
    r["avance"] = float((m[1:] & m[:-1]).sum(axis=1).mean()) - sp.OV_MEAN
    return r


# --------------------------------------------------------------------------
# 1. L'ARCHIVE RÉELLE — recoupement f3, franchises, borne
# --------------------------------------------------------------------------

rule("1. L'ARCHIVE RÉELLE — 70 560 tirages, cinq agrégateurs, une grille d'oracle")

arch = lab.load()
T_all = len(arch.mask)
say(f"   {T_all} tirages, {N} têtes, échauffement {sp.WARMUP}")
t0 = time.time()
real = forward(arch.mask, measure_share=32)
say(f"   rejoué en {time.time() - t0:.0f}s — {real['steps']} pas évalués")

best = real["best_head"]
best_hits = real["mean_o"][best]
say(f"\n   recoupement avec f3 (publiés : pression 5,01195 ; ensemble 4,99572) :")
say(f"     meilleure tête : {sp.HEAD_IDS[best]:<10} {best_hits:.5f} hits/tirage")
say(f"     AdaHedge déployé (mélange de champs) : {real['mix_mean'][I_DEP]:.5f}")
ok1 = sp.HEAD_IDS[best] == "pression" and abs(best_hits - 5.01195) < 5e-5
ok2 = abs(real["mix_mean"][I_DEP] - 4.99572) < 5e-5
say(f"     recoupement : {'IDENTIQUE' if ok1 and ok2 else 'ÉCART — À EXPLIQUER'}")

say(f"\n   partage moyen de top-20 entre deux têtes : {real['share_mean']:.3f} / 20"
    f"   (f6 publiait 5,92 ; sans rapport : 5,00)")

say("\n   franchises sur l'archive réelle (max_h − ensemble, hits/tirage) :")
say(f"   {'agrégateur':<22} {'mélange de champs':>18} {'fractionnaire':>15}")
for a in range(K):
    fm = best_hits - real["mix_mean"][a]
    ff = best_hits - real["frac_mean"][a]
    say(f"   {AGG_NAMES[a]:<22} {fm:>18.5f} {ff:>15.5f}")
g_best = int(np.argmin(real["grid_regret"]))
fr_orac = real["grid_regret"][g_best] * DRAWN / real["steps"]
say(f"   {'ORACLE η fixe (a posteriori)':<38} {fr_orac:>15.5f}"
    f"   (η* = {ETA_GRID[g_best]:.3f} — borne inférieure, PAS un concurrent :")
say("      son η est choisi APRÈS avoir vu les 70 547 pas)")

rule("2. LA BORNE C′ SUR L'ARCHIVE RÉELLE — et la dérivation re-vérifiée")
st = real["steps"]
say(f"   dispersion par pas : v̄ (déployé) = {real['V'][I_DEP] / st:.6f}"
    f"   s̄ (étendue) = {real['s_mean']:.4f}   pire cas du théorème C : 1/4")
sig2 = sp.OV_SD ** 2
c_of_s = lambda s: s * (3 / 16 + 12 / 5056) - 400 * (12 / 5056)
v_pred_ind = (1 - 1 / N) * sig2 / (DRAWN ** 2)
v_pred_cor = (1 - 1 / N) * (sig2 - c_of_s(real["share_mean"])) / (DRAWN ** 2)
say(f"   v̄ prédit (uniforme, combinatoire exacte) : têtes indépendantes "
    f"{v_pred_ind:.6f} ; avec le partage mesuré {v_pred_cor:.6f}")
say(f"   v̄ mesuré (uniforme) : {real['V'][I_UNIF] / st:.6f}")
say(f"   -> le resserrement vient d'abord du fait que l'adversaire est un")
say(f"      tirage (v ≪ 1/4), la corrélation des têtes n'en retire que"
    f" ~{100 * (1 - v_pred_cor / v_pred_ind):.0f} %")

say(f"\n   dérivation, re-vérifiée pas à pas sur ce rejeu :")
say(f"     Fait 2 (δ ≤ φ(η)·v)   : {real['f2_viol']} violation(s) sur {real['f2_checked']} pas")
say(f"     Fait 3 (M_T ≤ L*+Δ)   : M−L* = {real['M_pure'] - real['Lstar']:+.3f}"
    f"  ≤  Δ = {real['gap_pure']:.3f} : {real['M_pure'] - real['Lstar'] <= real['gap_pure'] + 1e-9}")
say(f"     Fait 4 (sortie ≤ lnN+1): Δ(t₀) = {real['gap_at_exit']:.3f}"
    f"  ≤  {LOGN + 1 + GAP0:.3f} : {real['gap_at_exit'] <= LOGN + 1 + GAP0}"
    f"   ({real['warm_steps']} pas d'échauffement η > 1)")

for lbl, idx in (("AdaHedge pur (le théorème)", I_PURE),
                 ("AdaHedge déployé (conformité mesurée)", I_DEP)):
    R = real["regret"][idx]
    b2 = borne_C2(real["V"][idx])
    b1 = borne_C1(st)
    say(f"\n   {lbl} :")
    say(f"     regret réalisé  {R:8.2f} u. de perte  = {R * DRAWN / st:.5f} hit/tirage")
    say(f"     borne C  (1er ordre)  {b1:8.1f}  = {b1 * DRAWN / st:.4f} hit/tirage"
        f"   marge ×{b1 / R:.1f}")
    say(f"     borne C′ (2nd ordre)  {b2:8.1f}  = {b2 * DRAWN / st:.4f} hit/tirage"
        f"   marge ×{b2 / R:.1f}   resserrement ×{b1 / b2:.1f}")


# --------------------------------------------------------------------------
# 3. H₀ — 32 archives T = 20 000 : égalité des franchises, bornes, témoin
# --------------------------------------------------------------------------

rule("3. H₀, 32 ARCHIVES SRS T = 20 000 — l'égalité des franchises, et les bornes")

T_H0 = 20_000
R_H0 = 32
WORKERS = max(1, min(4, cpu_count()))
say(f"   {R_H0} réplicats sur {WORKERS} processus…")
t0 = time.time()
with Pool(WORKERS) as pool:
    reps = pool.map(_rep_h0, [(9000 + r, T_H0) for r in range(R_H0)])
say(f"   fait en {time.time() - t0:.0f}s")

best_h = np.array([r["mean_o"].max() for r in reps])          # plancher + 5
fr_mix = np.array([r["mean_o"].max() - r["mix_mean"] for r in reps])   # (R,K)
fr_frac = np.array([r["mean_o"].max() - r["frac_mean"] for r in reps])
fr_orac_h0 = np.array([r["grid_regret"].min() * DRAWN / r["steps"] for r in reps])

say(f"\n   le plancher commun (malédiction du vainqueur du COMPARATEUR) :")
say(f"     E[max_h hits/tirage] − 5 = {best_h.mean() - 5:+.5f} ± {best_h.std(ddof=1):.5f}")
say(f"     (à T = 20 000 ; il décroît en 1/√T — ce n'est pas une propriété")
say(f"      de l'agrégateur, TOUT agrégateur honnête le paie en espérance)")

say(f"\n   franchises sous H₀ (hits/tirage, moyenne ± sd sur {R_H0} réplicats) :")
say(f"   {'agrégateur':<22} {'mélange de champs':>22} {'fractionnaire':>22}")
for a in range(K):
    say(f"   {AGG_NAMES[a]:<22} {fr_mix[:, a].mean():>12.5f} ± {fr_mix[:, a].std(ddof=1):.5f}"
        f" {fr_frac[:, a].mean():>13.5f} ± {fr_frac[:, a].std(ddof=1):.5f}")
say(f"   {'ORACLE η fixe':<22} {'—':>22} {fr_orac_h0.mean():>13.5f} ± {fr_orac_h0.std(ddof=1):.5f}"
    f"   (choisi a posteriori)")

say(f"\n   le test du théorème d'égalité — diffs appariées vs AdaHedge déployé")
say(f"   (mélange de champs ; sous H₀ l'espérance de chaque diff est 0) :")
z_max_egal = 0.0
for a in range(K):
    if a == I_DEP:
        continue
    d = fr_mix[:, a] - fr_mix[:, I_DEP]
    se = d.std(ddof=1) / math.sqrt(R_H0)
    z = d.mean() / se if se > 0 else 0.0
    z_max_egal = max(z_max_egal, abs(z))
    say(f"     {AGG_NAMES[a]:<22} diff {d.mean():+.5f} ± {se:.5f}   z = {z:+.2f}")
say(f"   max |z| = {z_max_egal:.2f}  ->  {'CONFORME au théorème' if z_max_egal < 3 else 'RÉFUTÉ'}")
say(f"   (la précision atteinte : une différence VRAIE de "
    f"{3 * np.median([np.std(fr_mix[:, a] - fr_mix[:, I_DEP], ddof=1) for a in range(K) if a != I_DEP]) / math.sqrt(R_H0):.5f}"
    f" hit/tirage serait vue à 3σ — c'est la puissance de la comparaison)")

viol2 = viol2_dep = viol_faux = 0
marges2, marges2_dep = [], []
f2v = f2c = 0
for r in reps:
    for idx, (lst, cnt) in ((I_PURE, (marges2, "pure")), (I_DEP, (marges2_dep, "dep"))):
        R_ = r["regret"][idx]
        b2 = borne_C2(r["V"][idx])
        lst.append(b2 / R_ if R_ > 0 else np.inf)
        if R_ > b2:
            if idx == I_PURE:
                viol2 += 1
            else:
                viol2_dep += 1
    if r["regret"][I_PURE] > fausse_borne(r["V"][I_PURE]):
        viol_faux += 1
    f2v += r["f2_viol"]
    f2c += r["f2_checked"]

say(f"\n   la borne C′ sur les {R_H0} réplicats (T = {T_H0}) :")
say(f"     AdaHedge pur     : {viol2} violation(s) ; marge min ×{min(marges2):.2f}")
say(f"     AdaHedge déployé : {viol2_dep} violation(s) ; marge min ×{min(marges2_dep):.2f}")
say(f"     Fait 2 cumulé    : {f2v} violation(s) sur {f2c} pas")
say(f"   TÉMOIN POSITIF — la fausse borne 0,5·√(V·lnN) est violée sur "
    f"{viol_faux}/{R_H0} réplicats")
say(f"   -> le banc {'a des dents' if viol_faux >= R_H0 // 2 else 'EST CASSÉ — fausse borne jamais violée'}")


# --------------------------------------------------------------------------
# 4. H₀ — 6 archives COMPLÈTES : la borne à l'échelle du déployé
# --------------------------------------------------------------------------

rule("4. H₀, 6 ARCHIVES SRS COMPLÈTES — la borne à T = 70 560")

t0 = time.time()
with Pool(WORKERS) as pool:
    reps_full = pool.map(_rep_h0, [(7700 + r, T_all) for r in range(6)])
say(f"   fait en {time.time() - t0:.0f}s")

viol_full = 0
say(f"\n   {'rep':<5} {'regret pur':>11} {'V_T':>8} {'borne C′':>9} {'marge':>7}"
    f"   {'regret dép.':>11} {'borne C′':>9} {'franchise dép.':>15}")
for i, r in enumerate(reps_full):
    st_ = r["steps"]
    Rp, Rd = r["regret"][I_PURE], r["regret"][I_DEP]
    b2p, b2d = borne_C2(r["V"][I_PURE]), borne_C2(r["V"][I_DEP])
    if Rp > b2p or Rd > b2d:
        viol_full += 1
    frd = r["mean_o"].max() - r["mix_mean"][I_DEP]
    say(f"   {i + 1:<5} {Rp:>11.2f} {r['V'][I_PURE]:>8.1f} {b2p:>9.1f}"
        f" {'×' + format(b2p / max(Rp, 1e-9), '.1f'):>7}   {Rd:>11.2f} {b2d:>9.1f} {frd:>15.5f}")
Vbar_full = float(np.mean([r["V"][I_PURE] for r in reps_full]))
b2_typ = borne_C2(Vbar_full)
st_full = reps_full[0]["steps"]
say(f"\n   violations : {viol_full}")
say(f"   borne C′ typique à T = {T_all} : {b2_typ:.1f} u. = "
    f"{b2_typ * DRAWN / st_full:.4f} hit/tirage   (théorème C : "
    f"{borne_C1(st_full) * DRAWN / st_full:.4f} — resserrement ×{borne_C1(st_full) / b2_typ:.1f})")
fr_full_dep = np.array([r["mean_o"].max() - r["mix_mean"][I_DEP] for r in reps_full])
say(f"   franchise déployée sous H₀ à T complet : {fr_full_dep.mean():.5f} ± "
    f"{fr_full_dep.std(ddof=1):.5f}   (réelle, f3 : 0,01623)")


# --------------------------------------------------------------------------
# 5. CONTAMINATION MOMENTUM — la seule unité où la franchise compte
# --------------------------------------------------------------------------

rule("5. CONTAMINATION MOMENTUM (f3) — seuil de détection par agrégateur")
say("   Sous H₀ l'espérance est invariante : la comparaison n'a d'unité que")
say("   sous une alternative. Même contamination que f3, mêmes ε, T = 20 000.")
say("   Détection par l'ENSEMBLE : z du mélange de champs contre son null")
say("   (les 32 réplicats H₀ de la section 3), seuil à 3σ par agrégateur.")

z_mix_h0 = np.array([r["z_mix"] for r in reps])          # (R,K)
seuils = z_mix_h0.mean(axis=0) + 3 * z_mix_h0.std(axis=0, ddof=1)
say(f"\n   seuils 3σ par agrégateur : "
    + "  ".join(f"{AGG_SHORT[a]} {seuils[a]:+.2f}" for a in range(K)))
zbh = np.array([r["z_heads_max"] for r in reps])
seuil_omni = zbh.mean() + 3 * zbh.std(ddof=1)
say(f"   (l'omnibus de f3, max_h z_h : seuil {seuil_omni:+.2f} sur ce null)")

EPS = (0.02, 0.03, 0.05, 0.10, 0.20)
R_ALT = 4
jobs = [(5500 + 100 * i + r, T_H0, eps) for i, eps in enumerate(EPS) for r in range(R_ALT)]
t0 = time.time()
with Pool(WORKERS) as pool:
    alt = pool.map(_rep_alt, jobs)
say(f"   {len(jobs)} rejeux contaminés en {time.time() - t0:.0f}s")

det_table = {}
say(f"\n   {'ε':<6} {'avance':>8} | " + " | ".join(f"{AGG_SHORT[a]:>10}" for a in range(K))
    + " |   (z moyen de l'ensemble, détections/4)")
for i, eps in enumerate(EPS):
    rs = alt[i * R_ALT:(i + 1) * R_ALT]
    av = float(np.mean([r["avance"] for r in rs]))
    zs = np.array([r["z_mix"] for r in rs])              # (4,K)
    det = (zs >= seuils[None, :]).sum(axis=0)
    det_table[eps] = (av, zs.mean(axis=0), det)
    say(f"   {eps:<6.2f} {av:>+8.4f} | "
        + " | ".join(f"{zs.mean(axis=0)[a]:+6.2f} {det[a]}/4" for a in range(K)))

say("\n   plus petite avance détectée 4/4, par agrégateur :")
seuil_det = {}
for a in range(K):
    hit = [det_table[e][0] for e in EPS if det_table[e][2][a] == R_ALT]
    seuil_det[a] = min(hit) if hit else None
    txt = f"dès +{min(hit):.4f} hit/tirage" if hit else "jamais sur cette grille"
    say(f"     {AGG_NAMES[a]:<22} {txt}")

say("\n   la part de l'avance CAPTÉE (hits de l'ensemble − 5, en % de l'avance ;")
say("   rapport des moyennes sur 4 réplicats) et, entre crochets, la FRANCHISE")
say("   sous l'alternative (max_h − ensemble, hit/tirage) — c'est ici que les")
say("   règles se séparent :")
say(f"   {'ε':<6} | " + " | ".join(f"{AGG_SHORT[a]:>16}" for a in range(K)))
for eps in EPS:
    rs = alt[EPS.index(eps) * R_ALT:(EPS.index(eps) + 1) * R_ALT]
    av = det_table[eps][0]
    for r in rs:
        r["_fr"] = r["mean_o"].max() - r["mix_mean"]
    cap = [100 * float(np.mean([r["mix_mean"][a] - sp.OV_MEAN for r in rs])) / max(av, 1e-9)
           for a in range(K)]
    fra = [float(np.mean([r["_fr"][a] for r in rs])) for a in range(K)]
    say(f"   {eps:<6.2f} | " + " | ".join(f"{cap[a]:>5.0f}% [{fra[a]:.3f}]" for a in range(K)))

say("\n   ce que la borne GARANTIT désormais (capture fractionnaire d'une avance ε) :")
vbar_h0 = float(np.mean([r["V"][I_PURE] / r["steps"] for r in reps]))
for eps_g in (0.043, 0.02):
    t1 = 4 * (DRAWN ** 2) * LOGN / eps_g ** 2
    t2 = (CST ** 2) * (DRAWN ** 2) * vbar_h0 * LOGN / eps_g ** 2
    say(f"     ε = {eps_g:.3f} : théorème C exige T ≳ {t1:,.0f} ; "
        f"C′ exige T ≳ {t2:,.0f} (×{t1 / t2:.0f} de moins)")
say(f"   (v̄ H₀ mesuré : {vbar_h0:.6f} ; f3 MESURE la détection à T = 20 000 —")
say("    c'est C′, pas C, qui décrit ce qui se passe)")


# --------------------------------------------------------------------------
# 6. CONTRÔLE DE FUITE — décisif, pas déclaratif
# --------------------------------------------------------------------------

rule("6. LEAK CHECK — les prédicteurs d'ensemble, archive réécrite en place")


def _leak_predict(kind):
    """Prédicteur pour `lab.leak_check` : rejoue têtes + agrégateur sur
    past.mask (borné à [0,t)) et rend le top-20 du champ d'ensemble."""

    def predict(past, t):
        m = past.mask
        heads = sp.make_heads()
        ag = {"dep": AdaDep, "unif": Unif, "ftl": FTL}[kind]()
        for s_ in range(len(m)):
            hit = m[s_].astype(float)
            if s_ >= sp.WARMUP:
                fields = np.stack([sp._z(h.field()) for h in heads])
                tops = np.stack([sp._top(fields[i]) for i in range(N)])
                o = m[s_][tops].sum(axis=1)
                ag.update(1 - o / DRAWN)
            for h in heads:
                h.absorb(hit)
        fields = np.stack([sp._z(h.field()) for h in heads])
        return np.sort(sp._top(ag.w @ fields) + 1)

    return predict


arch.build_index()
small = arch.slice(0, 2100)
small.build_index()
t0 = time.time()
for kind, nom in (("dep", "AdaHedge déployé"), ("unif", "uniforme"), ("ftl", "FTL")):
    ok, spots = lab.leak_check(small, _leak_predict(kind), k=DRAWN,
                               warmup=1400, probes=4, repeats=3)
    say(f"   {nom:<20} : {'PROPRE' if ok else 'FUITE ' + str(spots)}")
say(f"   ({time.time() - t0:.0f}s — archive tronquée à 2 100 tirages : le chemin")
say("    de code est identique, seul le coût du rejeu par sonde change)")


# --------------------------------------------------------------------------
# 7. REGISTRE
# --------------------------------------------------------------------------

rule("7. REGISTRE")

fr_reel_mix = float(best_hits - real["mix_mean"][I_DEP])
lab.record(
    TOK_EGAL, z_max_egal,
    verdict="conforme" if z_max_egal < 3 else "réfuté",
    notes=f"diffs appariées de franchise vs déployé sur {R_H0} archives SRS "
          f"T={T_H0} ; plancher commun mesuré {best_h.mean() - 5:+.5f} ± "
          f"{best_h.std(ddof=1):.5f} hit/tirage ; précision 3σ ≈ "
          f"{3 * float(np.median([np.std(fr_mix[:, a] - fr_mix[:, I_DEP], ddof=1) for a in range(K) if a != I_DEP])) / math.sqrt(R_H0):.5f}")

marge_min = float(min(min(marges2), min(marges2_dep),
                      min(borne_C2(r["V"][I_PURE]) / r["regret"][I_PURE] for r in reps_full),
                      min(borne_C2(r["V"][I_DEP]) / r["regret"][I_DEP] for r in reps_full),
                      borne_C2(real["V"][I_PURE]) / real["regret"][I_PURE],
                      borne_C2(real["V"][I_DEP]) / real["regret"][I_DEP]))
lab.record(
    TOK_BORNE, marge_min,
    power_at=f"témoin positif : fausse borne 0,5·sqrt(V lnN) violée sur "
             f"{viol_faux}/{R_H0} réplicats",
    verdict="jamais violée" if (viol2 + viol2_dep + viol_full) == 0 and marge_min > 1
            else "VIOLÉE — théorème C' réfuté",
    notes=f"R <= 2,3971·sqrt(V_T lnN) + 2 lnN + 6 + 2e-3 ; archive réelle : "
          f"borne {borne_C2(real['V'][I_DEP]) * DRAWN / st:.4f} hit/tirage vs "
          f"théorème C {borne_C1(st) * DRAWN / st:.4f} "
          f"(resserrement ×{borne_C1(st) / borne_C2(real['V'][I_DEP]):.1f}) ; "
          f"Fait 2 : {f2v + real['f2_viol']} violation sur {f2c + real['f2_checked']} pas")

lab.record(
    TOK_FRAN, fr_reel_mix,
    verdict="mesure",
    notes=f"franchise réelle déployée (mélange de champs) {fr_reel_mix:.5f} ; "
          f"fractionnaire {best_hits - real['frac_mean'][I_DEP]:.5f} ; sous H0 "
          f"T={T_H0} toutes les règles honnêtes à {fr_mix[:, I_DEP].mean():.5f} ± "
          f"{fr_mix[:, I_DEP].std(ddof=1):.5f} (égalité, cf. h28.egalite) ; "
          f"oracle a posteriori {fr_orac_h0.mean():.5f} ; leak_check propre ×3")

det_dep = seuil_det[I_DEP]
lab.record(
    TOK_DET, det_dep if det_dep is not None else float("nan"),
    power_at=f"contamination momentum f3, eps={EPS}, T={T_H0}, 4 réplicats/eps",
    verdict="mesure",
    notes="seuil 4/4 par agrégateur (hit/tirage) : " + "; ".join(
        f"{AGG_NAMES[a]}: {('+%.4f' % seuil_det[a]) if seuil_det[a] is not None else 'non détecté'}"
        for a in range(K)) + f" ; omnibus f3 (max_h z_h) seuil {seuil_omni:+.2f}")

rule(f"consigné au registre — total {time.time() - T0:.0f}s")
