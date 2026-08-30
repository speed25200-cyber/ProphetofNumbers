"""h39 — la classe jamais essayée : un modèle de SÉQUENCE à représentation apprise.

Ce que le dossier a, et ce qui manque
--------------------------------------
Trois familles de modèles appris ont été poussées, chacune avec ses limites
déclarées : la régression logistique de c2 (§3 ter) et le gradient boosting
de d3 travaillent sur des TRAITS agrégés choisis à la main — le tirage y est
réduit à une poignée de scalaires ; le codeur universel de h35 (§52) mélange
des contextes markoviens, mais ses angles morts sont nommés : pas
d'interaction entre numéros, pas de lag au-delà de 12, pas de contexte
exogène en temps. Aucune des trois n'apprend sa propre représentation.

Ce fichier ajoute la classe manquante : un réseau de CONVOLUTIONS CAUSALES
DILATÉES (TCN) sur les 80 indicatrices, entraîné à prédire le tirage t+1
depuis l'historique, rétropropagation écrite en numpy (ni torch ni
tensorflow ici — et c'est préférable : chaque opération est contrôlée).

L'architecture, et pourquoi cette taille
-----------------------------------------
Entrée : x[t] ∈ {0,1}^80 centrée (−0,25). Deux blocs, la décomposition
standard des convolutions séparables :

  - un bloc MÉLANGEUR : conv causale noyau 2, dilatation 1, 80 → 24 canaux,
    ReLU ; puis 6 couches 24 → 24, noyau 2, dilatations 2, 4, 8, 16, 32, 64,
    ReLU + connexion résiduelle ; tête linéaire 24 → 80 logits. Champ
    réceptif 1 + Σ dilatations = 128 tirages — chaque lag de 1 à 127 est
    atteignable (sommes de sous-ensembles des dilatations = toute valeur en
    binaire), bien AU-DELÀ du plafond 12 de h35. Le mélange de canaux donne
    au modèle ce qu'aucun des trois prédécesseurs n'a : un couplage appris
    ENTRE numéros à travers le temps (numéro a au t−k → numéro b au t) ;
  - un bloc DEPTHWISE : un noyau causal PAR NUMÉRO sur ses propres lags
    1..12 (80 × 12 poids appris, ajoutés aux logits). Motif : une
    application diagonale 80 → 80 (chaque numéro sur sa propre histoire —
    la rémanence) est de rang 80, et un mélangeur à 24 canaux ne peut pas
    la porter ; le premier jet, sans ce bloc, manquait la rémanence
    synthétique même à ε = 0,10 (voir « mise au point » plus bas).

13 880 paramètres, et pas des millions : l'archive contient 70 560 × 80 =
5,6 M d'événements binaires, soit ~407 événements par paramètre — le même
ordre que le budget par feuille de h35 (1 378). Le §3 ter a mesuré que
18 000 tirages ne suffisent pas à apprendre UN poids sur UN trait informatif
à d = 0,003 ; un modèle à 10⁶ paramètres sur cette source n'apprendrait que
du bruit, et son sur-apprentissage rendrait les deux unités illisibles.
Petit et honnête plutôt que gros et invérifiable.

Entraînement : Adam plein lot, 250 époques, lr 2·10⁻³, weight decay 10⁻⁴
sur les matrices (pas les biais), init de la tête à ZÉRO (le modèle démarre
exactement au codeur H₀ : logit(1/4) partout), graine fixe — l'ajustement
est une fonction DÉTERMINISTE des données d'entraînement, condition du
contrôle de fuite. Réajusté en marche avant aux points de contrôle
(20 000, 45 000) comme c2/d3 : chaque ajustement ne voit que [0, cp).
La rétropropagation est vérifiée par différences finies avant tout usage.

Les deux unités du dossier
---------------------------
1. RECOUVREMENT : top-20 du modèle contre le tirage réel, en marche avant
   stricte (`lab.walk_forward`, k = 20). Sous H₀, espérance 5 exactement et
   écart-type 1,687632 par tirage, QUEL QUE soit le choix (théorème du §12.1).
2. BITS : l'e-processus du §12.2. Les 80 logits sont les log-cotes d'un
   champ ; Q(S) = Π_{i∈S} w_i / e₂₀(w) (Bernoulli conditionnelle, la loi de
   maximum d'entropie à champ donné), e_t = Q(D_t)·C(80,20), et
   E[e_t | passé] = 1 exactement dès que les logits sont fonction du passé
   strict — la validité ne dépend pas de la qualité du modèle. Famille
   TEMPÉRÉE déclarée d'avance : η ∈ {0, 1/16, 1/8, 1/4, 1/2, 1} multiplie
   les logits centrés ; η = 0 est le membre « cash » (facteur 1 exactement,
   la leçon du plancher de f4/h35 appliquée dans le bon ordre : plancher du
   mélange = 1/6, déclaré ici avant toute lecture). Le mélange cumulé est
   doublé du mélange à REDÉMARRAGES par blocs de 16 (prior 1/(j(j+1)) +
   trésorerie — la construction corrigée du §14-D), sup lisible par Ville.

Limite structurelle assumée (et démontrable en deux lignes) : les DEUX
unités sont limitées au champ. Un couplage de paires INTRA-tirage à
marginales neutres est invisible par théorème — E[recouvrement de tout
20-parmi-80 mesurable du passé] = Σ_i P(i ∈ D) = 5 ne dépend que des
marginales, et E[log e_t] n'en dépend aussi que par Σ_i P_t(i)·log w_i. Le
réseau peut REPRÉSENTER une interaction intra-tirage dans ses couches, mais
la loi de sortie produit-forme ne peut pas la FACTURER : la vraie cible
intra-tirage de cette classe est le couplage entre numéros À TRAVERS les
tirages (croisé en temps), qui, lui, est dans les deux unités. Le couplage
quadratique du §40 reste la voie de détection de l'intra-tirage pur.
Autres limites : pas de canal bonus (territoire déclaré de d7/f4/h35), pas
de covariable exogène en temps (mais une modulation PÉRIODIQUE est visible
depuis les indicatrices seules, par le champ réceptif — mesuré ci-dessous),
pas de lag au-delà de 127, pas d'adaptation entre points de contrôle.

Témoins positifs (T = 20 000, ajustement à 10 000, évaluation sur 10 000) :
marginale, rémanence lag-1, couplage de paires CROISÉ au lag 24 (hors classe
pour h35 : ses contextes ne lisent que l'histoire PROPRE d'un numéro — c'est
vérifié ici en faisant tourner le codeur de h35 sur la même contamination ;
la détection passive de cette famille appartient à c1/d2, qui l'ont bornée,
mais aucun PRÉDICTEUR appris du dossier ne l'avait en classe), transitoire
tardif L = 500, et modulation périodique de période 2 — l'angle mort mesuré
de h35 (0/2 à δ = 0,30, §52). Amplitudes RÉALISÉES mesurées, pas supposées.
2 réplicats par point : des ordres de grandeur, pas des fréquences (même
convention déclarée que h35).

La question qui décide (d) : le PRIX du sur-apprentissage sous H₀ — le taux
de Kelly du modèle brut (η = 1) sur des archives SRS complètes, pipeline
identique au réel. h35 a mesuré que l'universalité coûte −6,2·10⁻⁵
bit/tirage ; f4 (paris figés) −3,3·10⁻³ ; personne n'a mesuré ce que coûte
une architecture riche entraînée sur cette source.

Mise au point : ce fichier a été développé et débogué en mode --fast sur
données SYNTHÉTIQUES uniquement (aucun appel à lab.load()) ; l'archive
réelle n'est lue que par l'exécution finale, jetons scellés au lancement.

Usage : python3 h39_sequence.py [--fast] [--no-record]
"""

import itertools
import math
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")   # machine partagée (h27, h40)

import numpy as np

EXPDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EXPDIR))
sys.path.insert(0, EXPDIR)
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
LOG_C = float(sum(math.log(POOL - i) - math.log(i + 1) for i in range(DRAWN)))
BITS_H0 = LOG_C / math.log(2)
LN10 = math.log(10)
LOG10_VILLE = math.log10(20.0)
LOGW_MIN = math.log(1e-8)

FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST
T0 = time.time()

# --------------------------------------------------------------------------
# L'architecture — fixée ICI, avant toute exécution sur l'archive
# --------------------------------------------------------------------------

CWID = 24                                # canaux
DIL = (1, 2, 4, 8, 16, 32, 64)           # dilatations (couche 0 = 1)
DW_LAGS = 12                             # bloc depthwise : noyaux par numéro, lags 1..12
RF = 1 + sum(DIL)                        # champ réceptif : 128 tirages
K = 20                                   # l'unité recouvrement du dossier
ETAS = np.array([0.0, 0.0625, 0.125, 0.25, 0.5, 1.0])   # famille tempérée
NMIX = len(ETAS)
EPOCHS = 60 if FAST else 250
LR = 2e-3
WD = 1e-4
SEED_FIT = 20260830
BLOCK = 16                               # redémarrages par blocs (§14-D/§15)
CPS_REAL = (4_000, 8_000) if FAST else (20_000, 45_000)
T_CTRL = 6_000 if FAST else 20_000
CP_CTRL = 3_000 if FAST else 10_000
REPS = 1 if FAST else 2

_PMF20 = lab.hits_pmf(K)
_H20 = np.arange(K + 1)
SD20 = math.sqrt(float((_PMF20 * _H20 * _H20).sum()) - 25.0)   # 1,687632 recalculé


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def n_params():
    n = 2 * POOL * CWID + CWID                       # couche 0
    n += (len(DIL) - 1) * (2 * CWID * CWID + CWID)   # couches dilatées
    n += CWID * POOL + POOL                          # tête
    n += DW_LAGS * POOL                              # bloc depthwise
    return n


# --------------------------------------------------------------------------
# Le réseau : avant, arrière, Adam — tout en numpy
# --------------------------------------------------------------------------

def shift(m, d):
    out = np.zeros_like(m)
    out[d:] = m[:-d]
    return out


def unshift(m, d):
    out = np.zeros_like(m)
    out[:-d] = m[d:]
    return out


def init_params(rng):
    p = {}
    s0 = 1.0 / math.sqrt(2 * POOL)
    p["W0a"] = rng.standard_normal((POOL, CWID)) * s0
    p["W0b"] = rng.standard_normal((POOL, CWID)) * s0
    p["b0"] = np.zeros(CWID)
    sl = 1.0 / math.sqrt(2 * CWID)
    for l in range(len(DIL) - 1):
        p[f"Wa{l}"] = rng.standard_normal((CWID, CWID)) * sl
        p[f"Wb{l}"] = rng.standard_normal((CWID, CWID)) * sl
        p[f"bd{l}"] = np.zeros(CWID)
    p["Wo"] = rng.standard_normal((CWID, POOL)) * 0.01   # petit mais non nul :
    # une tête exactement nulle coupe tout gradient vers les couches conv au
    # départ (dH = dS @ Wo.T = 0) — mesuré sur témoins synthétiques.
    p["bo"] = np.full(POOL, math.log(0.25 / 0.75))
    p["Vdw"] = np.zeros((DW_LAGS, POOL))             # noyaux par numéro, lags 1..12
    return p


def forward(p, X, want_cache=False):
    """S[t] = logits prédisant le tirage t+1, fonction de X[max(0,t-127)..t]."""
    Z0 = X @ p["W0a"] + shift(X, 1) @ p["W0b"] + p["b0"]
    H = np.maximum(Z0, 0.0)
    zs, hins = [Z0], []
    for l, d in enumerate(DIL[1:]):
        hins.append(H)
        Z = H @ p[f"Wa{l}"] + shift(H, d) @ p[f"Wb{l}"] + p[f"bd{l}"]
        H = np.maximum(Z, 0.0) + H
        zs.append(Z)
    S = H @ p["Wo"] + p["bo"]
    for k in range(1, DW_LAGS + 1):                  # bloc depthwise (diagonal)
        S += shift(X, k) * p["Vdw"][k - 1]
    if want_cache:
        return S, (X, zs, hins, H)
    return S


def backward(p, cache, dS):
    X, zs, hins, Hlast = cache
    g = {"Wo": Hlast.T @ dS, "bo": dS.sum(0)}
    g["Vdw"] = np.stack([(shift(X, k) * dS).sum(0) for k in range(1, DW_LAGS + 1)])
    dH = dS @ p["Wo"].T
    for l in reversed(range(len(DIL) - 1)):
        d = DIL[1:][l]
        dZ = dH * (zs[l + 1] > 0)
        g[f"Wa{l}"] = hins[l].T @ dZ
        g[f"Wb{l}"] = shift(hins[l], d).T @ dZ
        g[f"bd{l}"] = dZ.sum(0)
        dH = dZ @ p[f"Wa{l}"].T + unshift(dZ @ p[f"Wb{l}"].T, d) + dH
    dZ0 = dH * (zs[0] > 0)
    g["W0a"] = X.T @ dZ0
    g["W0b"] = shift(X, 1).T @ dZ0
    g["b0"] = dZ0.sum(0)
    return g


def bce_loss(S, Y, V):
    """BCE moyenne (nats) sur les lignes valides, formulation stable."""
    s, y = S[V], Y[V]
    return float(np.mean(np.maximum(s, 0) - s * y + np.log1p(np.exp(-np.abs(s)))))


def fit_net(mask_train, epochs=None, seed=SEED_FIT, tag="", say_progress=False):
    """Ajuste sur mask_train ([0, cp)) : S[t] cible mask[t+1], t ∈ [RF, cp-2].

    Déterministe : graine fixe, plein lot — mêmes données, mêmes poids.
    """
    epochs = EPOCHS if epochs is None else epochs
    Tn = len(mask_train)
    X = mask_train.astype(np.float64) - 0.25
    Y = np.zeros((Tn, POOL))
    Y[:-1] = mask_train[1:]
    V = np.zeros(Tn, bool)
    V[RF:Tn - 1] = True
    nV = int(V.sum())
    p = init_params(np.random.default_rng(seed))
    mom = {k: np.zeros_like(v) for k, v in p.items()}
    vel = {k: np.zeros_like(v) for k, v in p.items()}
    b1, b2, eps = 0.9, 0.999, 1e-8
    loss0 = loss = None
    for ep in range(1, epochs + 1):
        S, cache = forward(p, X, want_cache=True)
        if ep == 1:
            loss0 = bce_loss(S, Y, V)
        Pr = np.where(S >= 0, 1.0 / (1.0 + np.exp(-np.abs(S))),
                      np.exp(-np.abs(S)) / (1.0 + np.exp(-np.abs(S))))
        G = (Pr - Y)
        G[~V] = 0.0
        G /= (nV * POOL)
        grads = backward(p, cache, G)
        for k in p:
            if k[0] == "W":
                grads[k] = grads[k] + WD * p[k]
            mom[k] = b1 * mom[k] + (1 - b1) * grads[k]
            vel[k] = b2 * vel[k] + (1 - b2) * grads[k] ** 2
            mh = mom[k] / (1 - b1 ** ep)
            vh = vel[k] / (1 - b2 ** ep)
            p[k] = p[k] - LR * mh / (np.sqrt(vh) + eps)
        if say_progress and ep % 50 == 0:
            say(f"     fit {tag} époque {ep}/{epochs}  ({time.time() - T0:.0f}s)")
    S = forward(p, X)
    loss = bce_loss(S, Y, V)
    return p, loss0, loss


# --------------------------------------------------------------------------
# Le couplage vers une loi sur les 20-parmi-80 (f4/h35) et les e-processus
# --------------------------------------------------------------------------

def _log_factors_logw(LOGW, HIT):
    """(B, M, 80) log-cotes et (B, 80) tirages -> (B, M) log e-facteurs.

    Même construction que h35 : normalisation au max (invariance d'échelle),
    plancher 1e-8 (Q reste une vraie loi), e20 par récurrence.
    """
    logw = LOGW - LOGW.max(axis=2, keepdims=True)
    np.maximum(logw, LOGW_MIN, out=logw)
    W = np.exp(logw)
    B, Mm, _ = W.shape
    E = np.zeros((B, Mm, DRAWN + 1))
    E[:, :, 0] = 1.0
    for i in range(POOL):
        E[:, :, 1:] += W[:, :, i:i + 1] * E[:, :, :-1]
    logZ = np.log(E[:, :, DRAWN])
    lognum = np.where(HIT[:, None, :], logw, 0.0).sum(axis=2)
    return LOG_C + lognum - logZ


def efactors(scores, hits):
    """(n, 80) logits + (n, 80) tirages -> (n, NMIX) log e-facteurs tempérés.

    Le membre η = 0 est posé à 0 EXACTEMENT (codeur H0, membre cash) : le
    plancher du mélange vaut 1/6 par construction, pas par arrondi.
    """
    n = len(scores)
    out = np.empty((n, NMIX))
    for a in range(0, n, 2048):
        b = min(a + 2048, n)
        LOGW = ETAS[None, :, None] * scores[a:b, None, :]
        out[a:b] = _log_factors_logw(LOGW, hits[a:b])
    out[:, 0] = 0.0
    return out


def mixture_log(LOGF):
    cum = np.cumsum(LOGF, axis=0)
    mx = cum.max(axis=1, keepdims=True)
    return mx[:, 0] + np.log(np.exp(cum - mx).mean(axis=1)), cum


def restart_mean_log10(LOGF, block=BLOCK):
    """Mélange §14-D : redémarrages par blocs, prior 1/(j(j+1)) + trésorerie.

    Vraie martingale uniformément dans le temps — le sup se lit par Ville.
    Identique à la construction de h35 (qui a effacé la pénalité de position
    mesurée au §12.5).
    """
    T, Mm = LOGF.shape
    logA = np.full(Mm, -np.inf)
    logtail = 0.0
    out = np.empty(T)
    for t in range(T):
        if t % block == 0:
            j = t // block + 1
            logA = np.logaddexp(logA, math.log(1.0 / (j * (j + 1))))
            logtail = math.log(1.0 / (j + 1))
        logA = np.minimum(logA + LOGF[t], 700.0)
        logN = np.logaddexp(logA, logtail)
        mx = logN.max()
        out[t] = (mx + math.log(np.exp(logN - mx).mean())) / LN10
    return out


# --------------------------------------------------------------------------
# Le pipeline complet — identique pour le réel, H0 et les témoins
# --------------------------------------------------------------------------

def pscore_from(models, mask, cps):
    """PS[t] = logits utilisés pour prédire le tirage t (modèle du dernier cp <= t,
    scores de la ligne t-1 : fonction du passé strict [t-128, t))."""
    T = len(mask)
    Xc = mask.astype(np.float64) - 0.25
    fulls = {cp: forward(models[cp], Xc) for cp in cps}
    PS = np.zeros((T, POOL))
    bounds = list(cps) + [T]
    for cp, nxt in zip(bounds[:-1], bounds[1:]):
        PS[cp:nxt] = fulls[cp][cp - 1:nxt - 1]
    return PS, fulls


def run_pipeline(mask, cps, tag="", say_progress=False):
    """Ajuste aux points de contrôle, évalue sur [cps[0], T) dans les 2 unités."""
    T = len(mask)
    models, losses = {}, {}
    for cp in cps:
        models[cp], l0, l1 = fit_net(mask[:cp], tag=f"{tag}@{cp}",
                                     say_progress=say_progress)
        losses[cp] = (l0, l1)
    PS, fulls = pscore_from(models, mask, cps)
    e0 = cps[0]
    idx = np.argsort(-PS[e0:], axis=1, kind="stable")[:, :K]
    ov = np.take_along_axis(mask[e0:], idx, axis=1).sum(1)
    n_ev = T - e0
    z = (float(ov.mean()) - 5.0) / (SD20 / math.sqrt(n_ev))
    LOGF = efactors(PS[e0:], mask[e0:])
    log_mix, cum = mixture_log(LOGF)
    l10_rst = restart_mean_log10(LOGF)
    # diagnostic train (η = 1, modèle du 1er cp sur sa PROPRE zone d'ajustement)
    tr_s = fulls[cps[0]][RF:cps[0] - 1]
    tr_h = mask[RF + 1:cps[0]]
    tr_lf = efactors(tr_s, tr_h)[:, -1]
    return dict(
        models=models, PS=PS, losses=losses, ov=ov, ov_mean=float(ov.mean()),
        z=z, n_ev=n_ev, LOGF=LOGF,
        l10_final=float(log_mix[-1] / LN10),
        kelly_mix=float(log_mix[-1] / math.log(2) / n_ev),
        kelly_raw=float(cum[-1, -1] / math.log(2) / n_ev),
        sup_mix=float(log_mix.max() / LN10),
        sup_rst=float(l10_rst.max()),
        argmax_rst=int(np.argmax(l10_rst)),
        per_eta=cum[-1] / LN10,
        bits_train_raw=float(tr_lf.mean() / math.log(2)),
    )


# --------------------------------------------------------------------------
# Pré-enregistrement — architecture et décisions figées avant toute donnée
# --------------------------------------------------------------------------

TOK_WF = lab.preregister(
    "h39.wf",
    "un modele de sequence a representation apprise (convolutions causales "
    f"dilatees, {n_params()} parametres, champ receptif {RF}, retropropagation "
    "numpy) bat le hasard en marche avant stricte sur l'archive reelle",
    f"recouvrement moyen du top-{K} sur les tirages [{CPS_REAL[0]}, 70560), "
    "moins l'esperance exacte 5 ; z contre l'ecart-type hypergeometrique "
    "1,687632 recalcule de la pmf",
    "loi exacte du recouvrement (theoreme d'invariance, 12.1), recoupee par "
    "le meme pipeline sur archives SRS completes ; temoins positifs sur 5 "
    "familles contaminees (marginale, remanence, paires croisees lag 24, "
    "transitoire tardif, periode 2)",
    "|z| >= 3 declenche d'abord une chasse a l'artefact ; sans temoin positif "
    "mordant, un nul est ininterpretable (lecon de c2) ; leak_check decisif "
    "obligatoire avant lecture",
    track="A")

TOK_BITS = lab.preregister(
    "h39.bits",
    "les logits du meme modele, couples en loi sur les 20-parmi-80 "
    "(Bernoulli conditionnelle de f4/h35), extraient des bits de l'archive",
    f"log10 de la valeur FINALE du melange a poids egaux des {NMIX} e-processus "
    "temperes (eta dans {0, 1/16, 1/8, 1/4, 1/2, 1} sur les logits ; "
    "e_t = Q(D_t)*C(80,20)) ; taux de Kelly = log2(E_final)/T",
    "aucune calibration : E[e_t|passe] = 1 par construction (theta fonction du "
    "passe strict) ; verifie avant application (e20 exact enumere, champs "
    "fixes sur tirages uniformes, pipeline complet sur archives SRS) ; "
    "plancher du melange 1/6 DECLARE (membre cash eta=0)",
    "significatif si E >= 20 (Ville, alpha = 0,05, valide a tout instant), "
    "sans correction de multiplicite (moyenne d'e-valeurs = e-valeur) ; le "
    "livrable est le taux en bits signe compris, plus le PRIX du "
    "sur-apprentissage sous H0 (Kelly du membre brut eta=1 sur SRS)",
    track="C")

TOK_SUP = lab.preregister(
    "h39.sup",
    "avec les redemarrages par blocs (la construction corrigee du 14-D), le "
    "modele de sequence detecte aussi un ecart apparu tard dans l'archive",
    f"max_t log10 du melange a redemarrages par blocs de {BLOCK} tirages "
    f"(prior 1/(j(j+1)) + tresorerie) des {NMIX} e-processus temperes",
    "vraie martingale uniformement dans le temps ; Ville s'applique au sup ; "
    "meme verification que h39.bits",
    "significatif si sup >= 20",
    track="C")


# --------------------------------------------------------------------------
# Vérifications AVANT toute donnée réelle — sur du synthétique uniquement
# --------------------------------------------------------------------------

def verify_gradients():
    """La rétropropagation contre les différences finies. Sans cela, tout le
    reste est une croyance. X continu (les coudes ReLU sont de mesure nulle)."""
    rng = np.random.default_rng(3)
    Tn = 320
    X = rng.standard_normal((Tn, POOL)) * 0.4
    Y = (rng.random((Tn, POOL)) < 0.25).astype(np.float64)
    V = np.zeros(Tn, bool)
    V[RF:Tn - 1] = True
    p = init_params(rng)
    p["Wo"] = rng.standard_normal((CWID, POOL)) * 0.05   # tête non nulle : le
    for l in range(len(DIL) - 1):                        # gradient doit circuler
        p[f"bd{l}"] = rng.standard_normal(CWID) * 0.01
    nV = int(V.sum())

    def loss_of(pp):
        return bce_loss(forward(pp, X), Y, V)

    S, cache = forward(p, X, want_cache=True)
    Pr = 1.0 / (1.0 + np.exp(-S))
    G = (Pr - Y)
    G[~V] = 0.0
    G /= (nV * POOL)
    g = backward(p, cache, G)
    worst = 0.0
    h = 1e-6
    for k in sorted(p):
        flat = p[k].ravel()
        for j in rng.choice(flat.size, size=min(3, flat.size), replace=False):
            keep = flat[j]
            flat[j] = keep + h
            lp = loss_of(p)
            flat[j] = keep - h
            lm = loss_of(p)
            flat[j] = keep
            num = (lp - lm) / (2 * h)
            ana = g[k].ravel()[j]
            rel = abs(num - ana) / max(abs(num), abs(ana), 1e-9)
            worst = max(worst, rel)
    assert worst < 1e-4, f"retropropagation fausse : erreur relative {worst:.2e}"
    say(f"   gradients : {3 * len(p)} coordonnées contre différences finies, "
        f"pire écart relatif {worst:.1e}")


def verify_e20_exact():
    """e20 par récurrence contre l'énumération brute (leçon du §13.4 : couvrir
    aussi les petits cas) ; et le chemin de production à champ nul -> facteur 1."""
    rng = np.random.default_rng(7)
    for rep in range(5):
        w = np.exp(rng.standard_normal(6))
        e3_brute = sum(w[a] * w[b] * w[c]
                       for a, b, c in itertools.combinations(range(6), 3))
        E = np.zeros(4)
        E[0] = 1.0
        for i in range(6):
            E[1:] += w[i] * E[:-1]
        assert abs(E[3] - e3_brute) / e3_brute < 1e-12
    LOGW = np.zeros((4, 1, POOL))
    HIT = np.zeros((4, POOL), bool)
    HIT[:, :DRAWN] = True
    lf = _log_factors_logw(LOGW, HIT)
    assert np.abs(lf).max() < 1e-9, lf
    say("   e20 : récurrence == énumération brute (pool 6, k 3, 5 champs) ;")
    say("   champ uniforme -> facteur 1 à 1e-9 près (et le membre cash est posé")
    say("   à 0 exactement dans efactors : plancher 1/6 par construction).")


def verify_fixed_fields():
    """E[e_t] = 1 sur des tirages uniformes, champs fixes arbitraires, par le
    chemin de production exact (efactors). Un e-processus faux monte tout seul."""
    rng = np.random.default_rng(11)
    n = 20_000 if FAST else 200_000
    sc = rng.standard_normal(POOL) * 0.6              # un « logit » arbitraire
    acc = np.zeros(NMIX)
    acc2 = np.zeros(NMIX)
    for a in range(0, n, 4096):
        b = min(a + 4096, n)
        m = lab.srs(b - a, rng)
        e = np.exp(efactors(np.broadcast_to(sc, (b - a, POOL)), m))
        acc += e.sum(0)
        acc2 += (e * e).sum(0)
    worst = 0.0
    for j in range(1, NMIX):
        mean = acc[j] / n
        se = math.sqrt(max(acc2[j] / n - mean * mean, 1e-30) / n)
        zz = (mean - 1.0) / se
        worst = max(worst, abs(zz))
        say(f"   eta = {ETAS[j]:.4f}   moyenne e_t = {mean:.5f} ± {se:.5f}"
            f"   (écart à 1 : {zz:+.2f} sigma)")
    assert worst < 4.0, "E[e_t] s'écarte de 1 : la construction est fausse, ARRÊT"


def verify_determinism():
    """Deux ajustements sur les mêmes données -> poids identiques bit à bit.
    Sans cela, leak_check ne peut rien conclure (le choix en t doit être une
    fonction du passé, pas d'un aléa d'entraînement)."""
    rng = np.random.default_rng(17)
    m = lab.srs(RF + 900, rng)
    pA, _, _ = fit_net(m, epochs=25)
    pB, _, _ = fit_net(m, epochs=25)
    for k in pA:
        assert np.array_equal(pA[k], pB[k]), f"ajustement non déterministe ({k})"
    say("   deux ajustements identiques bit à bit : l'entraînement est une")
    say("   fonction déterministe des données.")


def verify_no_leak_forward():
    """Deux archives identiques jusqu'à t0, différentes après : les scores des
    lignes < t0 doivent être bit à bit identiques (attrape un décalage d'indice
    dans les décalages de la convolution — la fuite accidentelle la plus
    probable ici). leak_check tranchera de bout en bout sur le réel."""
    rng = np.random.default_rng(23)
    Tn, t0 = 2_000, 1_000
    mA = lab.srs(Tn, rng)
    mB = mA.copy()
    mB[t0:] = lab.srs(Tn - t0, rng)
    p = init_params(np.random.default_rng(5))
    p["Wo"] = np.random.default_rng(6).standard_normal((CWID, POOL)) * 0.05
    SA = forward(p, mA.astype(np.float64) - 0.25)
    SB = forward(p, mB.astype(np.float64) - 0.25)
    assert np.array_equal(SA[:t0], SB[:t0]), "FUITE : le passé dépend du futur"
    assert not np.array_equal(SA[t0:], SB[t0:]), "témoin cassé : rien ne diffère"
    say(f"   futur réécrit à partir de t0={t0} : les {t0} lignes de scores du")
    say("   passé sont bit à bit identiques ; celles du futur diffèrent (témoin).")


def verify_walkforward_equiv():
    """L'évaluation vectorisée des témoins == lab.walk_forward, sur une même
    archive synthétique. Une divergence ici invaliderait toute comparaison."""
    rng = np.random.default_rng(29)
    Tn, cp = RF + 2_200, RF + 1_200
    m = lab.srs(Tn, rng)
    pmod, _, _ = fit_net(m[:cp], epochs=25)
    PS, _ = pscore_from({cp: pmod}, m, (cp,))
    idx = np.argsort(-PS[cp:], axis=1, kind="stable")[:, :K]
    ov_vec = np.take_along_axis(m[cp:], idx, axis=1).sum(1)
    nums = np.sort(np.argsort(~m, axis=1, kind="stable")[:, :DRAWN] + 1,
                   axis=1).astype(np.int8)
    arch = lab.Archive(np.arange(Tn), np.zeros(Tn, np.int64), nums,
                       np.full(Tn, -1, np.int8), np.full(Tn, -1, np.int8), m)
    hits = lab.walk_forward(
        arch, lambda past, t: np.argsort(-PS[t], kind="stable")[:K] + 1,
        k=K, warmup=cp)
    assert np.array_equal(ov_vec, hits), "évaluation vectorisée != walk_forward"
    say(f"   évaluation vectorisée == lab.walk_forward sur {len(hits)} tirages.")


# --------------------------------------------------------------------------
# Témoins positifs — générateurs (conventions de c1/c2/h35, amplitudes mesurées)
# --------------------------------------------------------------------------

def srs_weighted(T, w, rng):
    """Tirage sans remise à probabilités proportionnelles (Gumbel top-k)."""
    g = np.log(w)[None, :] + rng.gumbel(size=(T, POOL))
    idx = np.argsort(-g, axis=1)[:, :DRAWN]
    m = np.zeros((T, POOL), bool)
    m[np.arange(T)[:, None], idx] = True
    return m


def contaminate_echo(m, rng, eps, lag):
    """Réinjection : avec proba eps, un numéro du tirage t-lag remplace un
    numéro frais du tirage t (la contamination momentum de f3/f4/h35)."""
    m = m.copy()
    for t in range(lag, len(m)):
        if rng.random() >= eps:
            continue
        prev = np.flatnonzero(m[t - lag] & ~m[t])
        cur = np.flatnonzero(m[t] & ~m[t - lag])
        if len(prev) and len(cur):
            m[t, rng.choice(prev)] = True
            m[t, rng.choice(cur)] = False
    return m


PAIR_SRC = np.arange(8)                  # sources : numéros 1..8 (index 0..7)
PAIR_TGT = np.arange(40, 48)             # cibles  : numéros 41..48


def gen_crosspair(T, d, rng, lag=24):
    """Couplage de paires CROISÉ en temps : si la source a_j est sortie au
    tirage t-24, la cible b_j a p = 0,25 + d au tirage t ; sinon 0,25 - d/3
    (marginale figée à 1/4 : P(source sortie) = 1/4). Les sources ne sont
    JAMAIS modifiées : le déclencheur reste exogène à la contamination.
    Réalisé par ajout/retrait avec proba 4d/3 (calcul : 0,25 + 0,75*(4d/3) =
    0,25 + d ; 0,25*(1 - 4d/3) = 0,25 - d/3), échange avec un numéro tampon
    (ni source ni cible). Hors classe pour h35 (contextes = histoire PROPRE
    d'un numéro) ; hors traits de c2 (lags 1-3 + co-occurrence lag 1) et de
    d3 (lags 1-3) ; la DÉTECTION passive de la famille appartient à c1/d2."""
    m = lab.srs(T, rng)
    q = 4.0 * d / 3.0
    protected = np.zeros(POOL, bool)
    protected[PAIR_SRC] = True
    protected[PAIR_TGT] = True
    for t in range(lag, T):
        trig = m[t - lag, PAIR_SRC]
        for j in range(len(PAIR_SRC)):
            b = PAIR_TGT[j]
            if trig[j]:
                if not m[t, b] and rng.random() < q:
                    filler = np.flatnonzero(m[t] & ~protected)
                    if len(filler):
                        m[t, rng.choice(filler)] = False
                        m[t, b] = True
            else:
                if m[t, b] and rng.random() < q:
                    filler = np.flatnonzero(~m[t] & ~protected)
                    if len(filler):
                        m[t, rng.choice(filler)] = True
                        m[t, b] = False
    return m


def crosspair_dp(m, lag=24):
    """Amplitude réalisée : P(cible | source au t-lag) - 0,25, moyenne des paires."""
    trig = m[:-lag][:, PAIR_SRC]
    tgt = m[lag:][:, PAIR_TGT]
    return float(tgt[trig].mean() - 0.25)


FAV8 = np.arange(8)


def gen_marginal(T, delta, rng):
    w = np.ones(POOL)
    w[FAV8] = 1.0 + delta
    return srs_weighted(T, w, rng)


def gen_transient(T, delta, t_on, L, rng):
    m = lab.srs(T, rng)
    w = np.ones(POOL)
    w[FAV8] = 1.0 + delta
    m[t_on:t_on + L] = srs_weighted(L, w, rng)
    return m


def gen_period2(T, delta, rng):
    """L'angle mort mesuré de h35 (§52, 0/2 à delta = 0,30) : poids (1+delta)
    aux tirages pairs, 1/(1+delta) aux impairs, sur 8 numéros. Aucun contexte
    exogène nécessaire pour un modèle de séquence : la parité se lit dans le
    champ réceptif (motif alterné des indicatrices elles-mêmes)."""
    wA = np.ones(POOL)
    wA[FAV8] = 1.0 + delta
    wB = np.ones(POOL)
    wB[FAV8] = 1.0 / (1.0 + delta)
    mA = srs_weighted(T, wA, rng)
    mB = srs_weighted(T, wB, rng)
    m = mA.copy()
    m[1::2] = mB[1::2]
    return m


def power_tables():
    """Cinq familles, amplitudes réalisées mesurées ; détection selon les deux
    unités : sup redémarrages >= 20 (Ville — critère de h35, comparable) et
    z du recouvrement >= 3 (échelle de f3). REPS réplicats par point : ordres
    de grandeur, pas des fréquences (convention h35, déclarée)."""
    results = {}

    import zlib

    def run_points(name, grid, make, eff, eff_label):
        say(f"\n   -- {name} --")
        for lvl in grid:
            # graine stable inter-exécutions (hash() de str est randomisé)
            rng = np.random.default_rng(
                1_000_000 + zlib.crc32(f"{name}|{lvl:.4f}".encode()) % 100_000)
            det_v = det_z = 0
            sups, zs, effs = [], [], []
            for r in range(REPS):
                m = make(lvl, rng)
                res = run_pipeline(m, (CP_CTRL,), tag=f"{name}@{lvl}")
                det_v += res["sup_rst"] >= LOG10_VILLE
                det_z += res["z"] >= 3.0
                sups.append(res["sup_rst"])
                zs.append(res["z"])
                effs.append(eff(m))
            say(f"      {lvl:>5.2f}  {eff_label}={np.mean(effs):+.4f}  "
                f"recouvr. z={np.mean(zs):+6.2f} ({det_z}/{REPS})  "
                f"sup 10^{np.mean(sups):+.2f} ({det_v}/{REPS})")
            results[(name, lvl)] = (det_v, det_z, REPS, float(np.mean(sups)),
                                    float(np.mean(zs)), float(np.mean(effs)))

    say("\n   -- référence H0 (aucun biais) --")
    rng0 = np.random.default_rng(909)
    for r in range(REPS):
        res = run_pipeline(lab.srs(T_CTRL, rng0), (CP_CTRL,), tag="H0ctrl")
        say(f"      H0 : recouvr. z={res['z']:+.2f}  sup 10^{res['sup_rst']:+.3f}  "
            f"Kelly brut {res['kelly_raw']:+.3e} bit/t")
        results[("H0", r)] = (0, 0, 1, res["sup_rst"], res["z"], 0.0)

    run_points("marginale (8 numéros à poids 1+delta)",
               (0.05, 0.10, 0.20, 0.40),
               lambda d, rg: gen_marginal(T_CTRL, d, rg),
               lambda m: m[:, FAV8].mean() - 0.25, "Dp")
    run_points("rémanence lag-1 (momentum de f3/f4/h35)",
               (0.02, 0.05, 0.10, 0.20),
               lambda e, rg: contaminate_echo(lab.srs(T_CTRL, rg), rg, e, 1),
               lambda m: (m[1:] & m[:-1]).sum(1).mean() - 5.0, "+hits")
    run_points("paires croisées lag 24 (hors classe h35)",
               (0.02, 0.05, 0.10),
               lambda d, rg: gen_crosspair(T_CTRL, d, rg),
               crosspair_dp, "Dp|src")
    t_on = 3 * T_CTRL // 4
    run_points(f"transitoire tardif (L=500 à t0={t_on})",
               (0.60, 1.20),
               lambda d, rg: gen_transient(T_CTRL, d, t_on, 500, rg),
               lambda m: m[t_on:t_on + 500][:, FAV8].mean() - 0.25, "Dp fen")
    run_points("période 2 (l'angle mort mesuré de h35)",
               (0.10, 0.30),
               lambda d, rg: gen_period2(T_CTRL, d, rg),
               lambda m: m[0::2][:, FAV8].mean() - 0.25, "Dp pair")
    return results


def h35_crosscheck():
    """Le codeur de h35, tel quel, sur la contamination paires-croisées-24 :
    la cécité structurelle annoncée est VÉRIFIÉE, pas affirmée."""
    import h35_codage_universel as h35mod
    say("   (codeur h35 importé : mêmes 22 modèles KT, mêmes redémarrages)")
    out = []
    rng = np.random.default_rng(4242)
    for d in (0.10,):
        for r in range(REPS):
            m = gen_crosspair(T_CTRL, d, rng)
            bo = h35mod.gen_bonus(m, rng)
            lf = h35mod.run_coder(m, bo)
            s = float(h35mod.restart_mean_log10(lf).max())
            dp = crosspair_dp(m)
            say(f"      d={d:.2f}  Dp|src={dp:+.4f}  sup h35 10^{s:+.3f}  "
                f"({'DÉTECTÉ' if s >= LOG10_VILLE else 'aveugle'})")
            out.append((d, dp, s))
    return out


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def main():
    rule("h39 — MODÈLE DE SÉQUENCE À REPRÉSENTATION APPRISE"
         + (" (mode FAST : synthétique seulement, rien au registre)" if FAST else ""))
    say(f"   TCN causal : canaux {CWID}, dilatations {DIL}, champ réceptif {RF},")
    say(f"   {n_params()} paramètres ({70560 * POOL / n_params():.0f} événements "
        f"binaires par paramètre sur l'archive) ;")
    say("   famille tempérée eta = (" + ", ".join(f"{e:g}" for e in ETAS)
        + f") -> plancher du mélange 1/{NMIX}")
    say(f"   (log10 = {-math.log10(NMIX):.3f}) ; un tirage coûte {BITS_H0:.4f} bits sous H0.")

    rule("1. VÉRIFIER AVANT D'APPLIQUER")
    verify_gradients()
    verify_e20_exact()
    verify_fixed_fields()
    verify_determinism()
    verify_no_leak_forward()
    verify_walkforward_equiv()

    rule("2. LE PRIX DU SUR-APPRENTISSAGE SOUS H0 — la question (d)")
    say("   Pipeline complet (ajustements aux mêmes points de contrôle que le")
    say("   réel) sur des archives SRS entières. Le chiffre qui compte : le")
    say("   Kelly du membre BRUT eta=1 — ce que la richesse de l'architecture")
    say("   coûte quand il n'y a rien à apprendre. Le mélange, planchonné à 1/6,")
    say("   dit ce que la couverture tempérée rachète.")
    rngH = np.random.default_rng(31)
    R_H0 = 1 if FAST else 2
    TsimH = 12_000 if FAST else 70_560
    h0_rows = []
    for rrep in range(R_H0):
        m = lab.srs(TsimH, rngH)
        res = run_pipeline(m, CPS_REAL, tag=f"H0full{rrep}", say_progress=True)
        h0_rows.append(res)
        say(f"   archive H0 n°{rrep + 1} (T={TsimH}) :")
        say(f"      recouvrement {res['ov_mean']:.4f} (z={res['z']:+.2f}) ; "
            f"Kelly brut eta=1 : {res['kelly_raw']:+.3e} bit/tirage ;")
        say(f"      Kelly mélange {res['kelly_mix']:+.3e} ; sup mélange "
            f"10^{res['sup_mix']:+.3f} ; sup redémarrages 10^{res['sup_rst']:+.3f}")
        say(f"      bits/tirage APPARENTS sur la zone d'entraînement (eta=1, "
            f"in-sample) : {res['bits_train_raw']:+.4f}")
    h0_raw = float(np.mean([r["kelly_raw"] for r in h0_rows]))
    h0_mix = float(np.mean([r["kelly_mix"] for r in h0_rows]))
    say(f"\n   PRIX MESURÉ sous H0 : brut {h0_raw:+.3e} bit/tirage ; "
        f"mélange {h0_mix:+.3e} ;")
    say("   repères : h35 (universel) -6,2e-05 ; f4 (paris figés) -3,3e-03.")

    rule("3. LES 70 560 TIRAGES RÉELS" if not FAST else
         "3. (FAST) ARCHIVE SYNTHÉTIQUE TENANT LIEU DE RÉEL")
    if FAST:
        rngF = np.random.default_rng(99)
        mask_real = lab.srs(12_000, rngF)
        nums = np.sort(np.argsort(~mask_real, axis=1, kind="stable")[:, :DRAWN] + 1,
                       axis=1).astype(np.int8)
        Tn = len(mask_real)
        a = lab.Archive(np.arange(Tn), np.zeros(Tn, np.int64), nums,
                        np.full(Tn, -1, np.int8), np.full(Tn, -1, np.int8), mask_real)
    else:
        a = lab.load()
    a.build_index()
    Treal = len(a)
    t0 = time.time()
    res_real = run_pipeline(a.mask, CPS_REAL, tag="réel", say_progress=True)
    say(f"   ajustements + passes : {time.time() - t0:.0f}s ; pertes BCE (nats) : "
        + " ; ".join(f"cp {cp} : {l0:.5f} -> {l1:.5f}"
                     for cp, (l0, l1) in res_real["losses"].items()))

    models, PS = res_real["models"], res_real["PS"]

    def cp_of(t):
        prior = [c for c in CPS_REAL if c <= t]
        return prior[-1]

    def predict(past, t):
        return np.argsort(-PS[t], kind="stable")[:K] + 1

    def predict_causal(past, t):
        win = past.mask[t - RF:t].astype(np.float64) - 0.25
        s = forward(models[cp_of(t)], win)[-1]
        return np.argsort(-s, kind="stable")[:K] + 1

    # accord voie vectorisée / voie causale, puis contrôle de fuite décisif
    gap = 0.0
    for t in (CPS_REAL[0] + 137, (CPS_REAL[0] + CPS_REAL[1]) // 2,
              CPS_REAL[1] + 211, Treal - 3):
        win = a.mask[t - RF:t].astype(np.float64) - 0.25
        s = forward(models[cp_of(t)], win)[-1]
        gap = max(gap, float(np.abs(s - PS[t]).max()))
        assert np.array_equal(predict(None, t), predict_causal(lab.Past(a, t), t))
    say(f"   accord scores bulk / causal aux sondes : écart max {gap:.1e} "
        f"(ordre de sommation BLAS), picks identiques")
    clean, spots = lab.leak_check(a, predict_causal, k=K,
                                  warmup=CPS_REAL[0], probes=6, repeats=4)
    say(f"   contrôle de fuite (décisif, futur réécrit cumuls compris) : "
        f"{'propre' if clean else f'FUITE en {spots}'}")
    if not clean:
        say("   -> résultat invalide, on s'arrête là.")
        return

    hits = lab.walk_forward(a, predict, k=K, warmup=CPS_REAL[0])
    assert np.array_equal(hits, res_real["ov"].astype(hits.dtype)), \
        "walk_forward != évaluation vectorisée"
    n_ev = len(hits)
    ov_mean = float(hits.mean())
    z_real = (ov_mean - 5.0) / (SD20 / math.sqrt(n_ev))

    say(f"\n   UNITÉ 1 — RECOUVREMENT (marche avant stricte, {n_ev} tirages) :")
    say(f"      moyenne du top-20 : {ov_mean:.4f}   (espérance exacte 5,0000)")
    say(f"      z = {z_real:+.2f}   (écart-type par tirage {SD20:.6f})")
    say(f"\n   UNITÉ 2 — BITS (e-processus du §12.2, {NMIX} tempéreurs) :")
    say(f"      E final du mélange     : 10^{res_real['l10_final']:+.3f}   "
        f"(plancher déclaré 10^{-math.log10(NMIX):.3f})")
    say(f"      taux de Kelly mélange  : {res_real['kelly_mix']:+.3e} bit/tirage")
    say(f"      taux de Kelly brut η=1 : {res_real['kelly_raw']:+.3e} bit/tirage "
        f"(le prix payé par la richesse sur le réel)")
    say(f"      sup mélange 10^{res_real['sup_mix']:+.3f} ; sup redémarrages "
        f"10^{res_real['sup_rst']:+.3f} (au pas {res_real['argmax_rst']}/{n_ev}) ; "
        f"Ville 10^{LOG10_VILLE:+.3f}")
    say(f"      bits APPARENTS in-sample (η=1) : {res_real['bits_train_raw']:+.4f} "
        f"/tirage — l'écart train/éval EST le sur-apprentissage")
    say("      par tempéreur, log10 E final : "
        + "  ".join(f"η={e:g}:{v:+.1f}" for e, v in
                    zip(ETAS, res_real["per_eta"])))

    rule("4. TÉMOINS POSITIFS — cinq familles, amplitudes réalisées mesurées")
    say(f"   T = {T_CTRL}, ajustement à {CP_CTRL}, évaluation sur "
        f"{T_CTRL - CP_CTRL} tirages ; {REPS} réplicat(s)/point.")
    say(f"   Détection : z >= 3 (recouvrement) et sup redémarrages >= 20 (Ville).")
    pw = power_tables()

    rule("5. LE CODEUR DE h35 SUR LES PAIRES CROISÉES — cécité vérifiée")
    xchk = h35_crosscheck()

    rule("6. LA COURBE DE DÉTECTION, CLASSE PAR CLASSE (publié / mesuré ici)")
    say("   famille          | c2 §3ter        | f3 §12.1     | h35 §52        | h39 (ici)")
    say("   marginale        | aveugle < Dp=0,020 | —          | Dp=+0,019      | voir table 4")
    say("   rémanence lag-1  | mord dès d=0,003*  | +0,043 hits| eps=0,05       | voir table 4")
    say("   paires croisées  | hors traits     | hors têtes   | HORS CLASSE (vérifié §5) | voir table 4")
    say("   transitoire tard | hors classe     | —            | Dp=+0,098      | voir table 4")
    say("   période 2        | hors traits     | —            | 0/2 à δ=0,30   | voir table 4")
    say("   (* c2 : biais conditionnel évalué sur 50 560 tirages, non 10 000 —")
    say("    échelles rappelées telles que publiées, pas converties)")

    rule("7. REGISTRE")
    if NO_RECORD:
        say("   --fast/--no-record : rien n'est écrit au registre")
        return
    existing = {r.get("id") for r in lab.ledger()}
    if {"h39.wf", "h39.bits", "h39.sup"} & existing:
        say("   entrées h39.* déjà présentes — AUCUN doublon écrit")
        return
    pw_items = [(k, v) for k, v in pw.items() if k[0] != "H0"]
    pw_str = "; ".join(
        f"{k[0].split(' ')[0]}@{k[1]}:ville {v[0]}/{v[2]},z3 {v[1]}/{v[2]}"
        for k, v in pw_items)
    xchk_str = "; ".join(f"h35 sur paires d={d}: sup 10^{s:+.2f}" for d, dp, s in xchk)
    lab.record(TOK_WF, observed=ov_mean - 5.0, p=None,
               power_at=pw_str,
               verdict="aucun avantage" if abs(z_real) < 3 else "a reexaminer",
               notes=f"recouvrement {ov_mean:.4f} contre 5,0000, z = {z_real:+.2f} "
                     f"sur {n_ev} tirages ; TCN {n_params()} params, RF {RF}, "
                     f"cps {CPS_REAL} ; leak_check propre ; accord bulk/causal "
                     f"{gap:.1e} ; walk_forward == vectorise ; {xchk_str}")
    lab.record(TOK_BITS, observed=res_real["l10_final"],
               p=float(min(1.0, 10 ** (-res_real["l10_final"]))),
               power_at=pw_str,
               verdict="",
               notes=f"Kelly melange {res_real['kelly_mix']:+.3e} bit/tirage ; "
                     f"Kelly brut eta=1 {res_real['kelly_raw']:+.3e} (reel) ; "
                     f"PRIX H0 mesure : brut {h0_raw:+.3e}, melange {h0_mix:+.3e} "
                     f"(sur {R_H0} archives SRS completes, pipeline identique) ; "
                     f"reperes h35 -6,2e-05, f4 -3,3e-03 ; in-sample eta=1 "
                     f"{res_real['bits_train_raw']:+.4f} bit/t")
    lab.record(TOK_SUP, observed=res_real["sup_rst"],
               p=float(min(1.0, 10 ** (-res_real["sup_rst"]))),
               power_at=pw_str,
               verdict="",
               notes=f"sup au pas {res_real['argmax_rst']}/{n_ev} ; blocs de "
                     f"{BLOCK}, prior 1/(j(j+1)) + tresorerie (14-D corrige) ; "
                     f"sup melange cumule 10^{res_real['sup_mix']:+.3f}")
    say("   consigné : h39.wf, h39.bits, h39.sup")


if __name__ == "__main__":
    main()
    rule(f"terminé — {time.time() - T0:.0f}s")
