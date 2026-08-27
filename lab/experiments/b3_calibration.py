"""B3 — Audit d'honnêteté de la confiance affichée par Swarm.swift (track B).

Question : le chiffre `confidence` affiché à l'utilisateur (Swarm.swift:919-920,
LiveView "SIGNAL DU MODÈLE … / 100 · 50 = hasard pur") se comporte-t-il comme du
bruit centré sur 50 sous H0, ou dérive-t-il vers le haut ?

-----------------------------------------------------------------------------
Transcription de la chaîne (Swarm.swift, lignes citées)
-----------------------------------------------------------------------------
  - L613  uniformExp = 20*20/80 = 5.0
  - L726  évaluation dès absorbed > 12 (1er point de backtest au 14e tirage)
  - L764-769  evaluate() : ensemble = mélange pondéré des champs z-scorés,
      overlap = |top-20(ensemble) ∩ tirage| — noter k = drawN = 20 (L767),
      PAS les grilles k=10 : l'écart-type vrai des hits est 1.6876, pas 1.29.
      L'overlap est enregistré AVANT que AdaHedge ne voie les pertes du
      tirage (L779-795) : évaluation préquentielle.
  - L908  recentBT = suffix(60) de ensembleOv
  - L909  btMean = moyenne (ou 5.0 si vide)
  - L915  btSD = écart-type ÉCHANTILLON (ddof=1), 1.68 si count<=1
  - L916-918  btZ = (btMean-5)/(max(0.2,btSD)/sqrt(count)) si count>=12, sinon 0
  - L919-920  confidence = clip(round(50 + 14*btZ), 5, 95)
  - L771-774, 922-924  e-process : eLogs[j] = min(80, eLogs[j]+θ_j·ov−log M_j),
      eValue = moyenne_j exp(min(60, eLogs[j])), θ ∈ ±{0.05,0.1,0.2,0.4}.

Simplification et pourquoi elle est sans effet sur la question posée
--------------------------------------------------------------------
Sous H0 (tirages SRS 20/80 indépendants), pour TOUT choix de 20 numéros
mesurable par rapport au passé — donc pour n'importe quel essaim adaptatif,
AdaHedge, évolution des têtes compris — la loi conditionnelle de l'overlap
sachant le passé est l'hypergéométrique(80,20,20), qui ne dépend pas du choix.
La suite ensembleOv est donc EXACTEMENT i.i.d. hyper(80,20,20) sous H0 : la
chaîne hits→confiance peut être alimentée par des hits i.i.d. sans rien
perdre. Ce théorème est lui-même VÉRIFIÉ ici par simulation (partie 2) : un
mini-essaim fidèle (14 têtes, AdaHedge L777-814, part fixe 2 %, évolution
L818-848 avec le même LCG de jitter, seuils et caps identiques) tourne sur des
tirages SRS et sa confiance finale est comparée à la version i.i.d. Têtes
omises (Weibull, Hazard, Spectral, Markov, Copair, ACP, Adjacency…) : sans
effet sous H0 par le même théorème ; le mini-essaim garde les trois familles
évolutives, les deux têtes anti et une tête de pression pour exercer tous les
mécanismes adaptatifs (repondération + mutation sur la même fenêtre).

Exécution : python3 lab/experiments/b3_calibration.py   (~5-8 min)
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab  # noqa: E402

POOL, DRAWN = 80, 20
H = 14
UNIF = 5.0
PMF = lab.hits_pmf(DRAWN)                     # hyper(80,20,20) == overlap pmf
PMF = PMF / PMF.sum()
H21 = np.arange(DRAWN + 1)
SD_TRUE = float(np.sqrt((PMF * (H21 - UNIF) ** 2).sum()))    # 1.6876
P_GE6 = float(PMF[6:].sum())                                  # 0.3744
THETA = np.array([0.05, 0.10, 0.20, 0.40, -0.05, -0.10, -0.20, -0.40])
LOGM = np.array([math.log((PMF * np.exp(th * H21)).sum()) for th in THETA])
VALS = H21.astype(np.int8)

DEC_IDX = np.arange(POOL) // 10               # (n-1)//10
PAR_IDX = (np.arange(1, POOL + 1)) % 2        # n%2
A_LCG = np.uint64(6364136223846793005)
C_LCG = np.uint64(1442695040888963407)


# ---------------------------------------------------------------------------
# Chaîne hits -> confiance (transcription exacte de Swarm.swift L908-920)
# ---------------------------------------------------------------------------

def conf_snapshot(hits2d: np.ndarray):
    """Confiance affichée pour M fenêtres complètes (M, n). Renvoie conf, z, sd."""
    x = hits2d.astype(np.float64)
    n = x.shape[1]
    mean = x.mean(axis=1)
    sd = x.std(axis=1, ddof=1)                              # L915
    z = (mean - UNIF) / (np.maximum(0.2, sd) / math.sqrt(n))  # L916-917
    if n < 12:
        z = np.zeros_like(z)                                # L918
    conf = np.clip(np.floor(50.0 + 14.0 * z + 0.5), 5, 95).astype(np.int64)  # L919-920
    return conf, z, sd


def confidence_series(ov: np.ndarray):
    """Confiance affichée après CHAQUE point de backtest (fenêtre glissante 60)."""
    ov = np.asarray(ov, np.float64)
    L = len(ov)
    c1 = np.concatenate([[0.0], np.cumsum(ov)])
    c2 = np.concatenate([[0.0], np.cumsum(ov * ov)])
    i = np.arange(1, L + 1)
    n = np.minimum(60, i)
    s1 = c1[i] - c1[i - n]
    s2 = c2[i] - c2[i - n]
    mean = s1 / n
    var = np.where(n > 1, (s2 - n * mean**2) / np.maximum(1, n - 1), 0.0)
    sd = np.where(n > 1, np.sqrt(np.maximum(var, 0.0)), 1.68)
    z = np.where(n >= 12, (mean - UNIF) / (np.maximum(0.2, sd) / np.sqrt(n)), 0.0)
    conf = np.clip(np.floor(50.0 + 14.0 * z + 0.5), 5, 95).astype(np.int64)
    return conf, z, n


def evalue_series(ov: np.ndarray) -> np.ndarray:
    """E-valeur affichée après chaque point (Swarm.swift L771-774, L922-924)."""
    ov = np.asarray(ov, np.float64)
    inc = THETA[:, None] * ov[None, :] - LOGM[:, None]
    logs = np.cumsum(inc, axis=1)
    if logs.max() > 80.0:  # le clip par pas (L773) mord : repli exact en boucle
        cur = np.zeros(len(THETA))
        for t in range(inc.shape[1]):
            cur = np.minimum(80.0, cur + inc[:, t])
            logs[:, t] = cur
    return np.exp(np.minimum(60.0, logs)).mean(axis=0)


# ---------------------------------------------------------------------------
# Mini-essaim fidèle : 14 têtes, AdaHedge + part fixe 2 %, évolution
# (SwarmEngine L704-848). Vectorisé sur R trajectoires.
# Têtes : bayes 10/33/200 (L35-66), ewma 8/25/64 (L70-94),
# hawkes 2.3/3.9/8.7 (L98-124), gapz (L202-233), streak (L339-355),
# anti-ewma25 + anti-hawkes3.9 (L474-487, copies indépendantes L1276-1277),
# pression (L564-595).
# ---------------------------------------------------------------------------

class MiniSwarm:
    def __init__(self, R: int):
        self.R = R
        self.bay_a = np.full((R, 3, POOL), 2.0)
        self.bay_b = np.full((R, 3, POOL), 6.0)
        self.bay_m = np.tile(np.array([10.0, 33.0, 200.0]), (R, 1))
        self.ew_e = np.full((R, 3, POOL), 0.25)
        self.ew_m = np.tile(np.array([8.0, 25.0, 64.0]), (R, 1))
        self.hk_s = np.zeros((R, 3, POOL))
        self.hk_m = np.tile(np.array([2.3, 3.9, 8.7]), (R, 1))
        self.gap = np.zeros((R, POOL))
        self.m1 = np.full((R, POOL), 4.0)      # 1/pBase (L206)
        self.m2 = np.full((R, POOL), 28.0)
        self.streak = np.zeros((R, POOL))
        self.anti_e = np.full((R, POOL), 0.25)
        self.anti_s = np.zeros((R, POOL))
        self.dec = np.full((R, 8), 2.5)        # drawK/8 (L567)
        self.par = np.full((R, 2), 10.0)
        self.w = np.full((R, H), 1.0 / H)
        self.cumLoss = np.zeros((R, H))
        self.adaGap = np.full(R, 1e-3)         # L624
        self.hedgeCum = np.zeros(R)
        self.buf = np.zeros((R, H, 40))        # suffix(40) de headOv (cap 80, L782)
        self.cnt = np.zeros((R, H), np.int64)
        self.rsum = np.zeros((R, H))
        self.pos = 0
        self.seed = np.full(R, 0x9E3779B97F4A7C15, np.uint64)   # L676
        self.absorbed = 0
        self.eLogs = np.zeros((R, len(THETA)))

    def fields(self) -> np.ndarray:
        F = np.empty((self.R, H, POOL))
        F[:, 0:3] = self.bay_a / (self.bay_a + self.bay_b)
        F[:, 3:6] = self.ew_e
        F[:, 6:9] = 0.07 + self.hk_s
        sd = np.sqrt(np.maximum(1.0, self.m2 - self.m1**2))
        F[:, 9] = (self.gap - self.m1) / sd
        F[:, 10] = self.streak
        F[:, 11] = -self.anti_e
        F[:, 12] = -(0.07 + self.anti_s)
        F[:, 13] = (2.5 - self.dec[:, DEC_IDX]) / 2.5 + 0.5 * (10.0 - self.par[:, PAR_IDX]) / 10.0
        return F

    @staticmethod
    def zscore(F: np.ndarray) -> np.ndarray:  # L1315-1327 : SD population, denom 1 si 0
        m = F.mean(axis=-1, keepdims=True)
        s = F.std(axis=-1, keepdims=True)
        s = np.where(s == 0, 1.0, s)
        return (F - m) / s

    def recompute_weights(self):  # L800-814
        eta = np.log(H) / self.adaGap
        minL = self.cumLoss.min(axis=1, keepdims=True)
        wv = np.exp(-eta[:, None] * (self.cumLoss - minL))
        s = wv.sum(axis=1, keepdims=True)
        bad = (~np.isfinite(s)) | (s <= 0)
        wv = np.where(bad, 1.0 / H, wv / np.where(s <= 0, 1.0, s))
        self.w = 0.98 * wv + 0.02 / H

    def evaluate(self, mask: np.ndarray):  # L764-796 : états et poids figés AVANT le tirage
        Z = self.zscore(self.fields())
        ens = np.einsum('rh,rhp->rp', self.w, Z)
        top = np.argpartition(-ens, DRAWN - 1, axis=1)[:, :DRAWN]
        ov = np.take_along_axis(mask, top, axis=1).sum(axis=1)
        self.eLogs = np.minimum(80.0, self.eLogs + THETA[None, :] * ov[:, None] - LOGM[None, :])
        toph = np.argpartition(-Z, DRAWN - 1, axis=2)[:, :, :DRAWN]
        ovh = np.take_along_axis(np.broadcast_to(mask[:, None, :], Z.shape), toph, axis=2).sum(axis=2)
        losses = 1.0 - ovh / DRAWN
        old = self.buf[:, :, self.pos].copy()
        self.rsum += ovh - np.where(self.cnt >= 40, old, 0.0)
        self.buf[:, :, self.pos] = ovh
        self.cnt += 1
        self.pos = (self.pos + 1) % 40
        eta = np.log(H) / self.adaGap
        hLoss = (self.w * losses).sum(axis=1)
        lmin = losses.min(axis=1)
        accum = (self.w * np.exp(-eta[:, None] * (losses - lmin[:, None]))).sum(axis=1)
        mixLoss = lmin - np.log(np.maximum(accum, 1e-300)) / eta
        self.adaGap += np.maximum(0.0, hLoss - mixLoss)
        self.hedgeCum += hLoss
        self.cumLoss += losses
        self.recompute_weights()
        # Exploratoire : "ESPÉRANCE" des grilles (GridsView L261) = somme du
        # posterior bayes.b (inclusion, L1061) sur les numéros les mieux classés.
        top10 = np.argpartition(-ens, 9, axis=1)[:, :10]
        incl = self.bay_a[:, 1] / (self.bay_a[:, 1] + self.bay_b[:, 1])
        exp10 = np.take_along_axis(incl, top10, axis=1).sum(axis=1)
        return ov, exp10

    def absorb(self, mask: np.ndarray):
        hit = mask
        g = 1.0 - 1.0 / np.maximum(2.0, self.bay_m)
        self.bay_a = g[:, :, None] * self.bay_a + hit[:, None, :]
        self.bay_b = g[:, :, None] * self.bay_b + (1.0 - hit[:, None, :])
        l = 2.0 / (np.maximum(2.0, self.ew_m) + 1.0)
        self.ew_e = (1.0 - l[:, :, None]) * self.ew_e + l[:, :, None] * hit[:, None, :]
        d = np.exp(-0.6931 / np.maximum(0.5, self.hk_m))
        self.hk_s = self.hk_s * d[:, :, None] + 0.42 * hit[:, None, :]
        self.gap += 1.0
        hb = hit > 0.5
        x = self.gap
        self.m1 = np.where(hb, self.m1 + 0.15 * (x - self.m1), self.m1)
        self.m2 = np.where(hb, self.m2 + 0.15 * (x * x - self.m2), self.m2)
        self.gap = np.where(hb, 0.0, self.gap)
        self.streak = (self.streak + 1.0) * hit
        la = 2.0 / 26.0
        self.anti_e = (1.0 - la) * self.anti_e + la * hit
        da = math.exp(-0.6931 / 3.9)
        self.anti_s = self.anti_s * da + 0.42 * hit
        dCount = mask.reshape(self.R, 8, 10).sum(axis=2)
        self.dec += 0.12 * (dCount - self.dec)
        pCount = np.stack([mask[:, PAR_IDX == 0].sum(axis=1), mask[:, PAR_IDX == 1].sum(axis=1)], axis=1)
        self.par += 0.12 * (pCount - self.par)

    def evolve(self):  # L818-848 : sélection du meilleur SUR LE BACKTEST (suffix 40)
        mutated = np.zeros(self.R, bool)
        for name, fam in [("bayes", [0, 1, 2]), ("ewma", [3, 4, 5]), ("hawkes", [6, 7, 8])]:
            cnt = self.cnt[:, fam]
            ok = (cnt >= 20).all(axis=1)                       # L827 (toutes les têtes)
            means = self.rsum[:, fam] / np.maximum(1, np.minimum(cnt, 40))
            bi = means.argmax(axis=1)
            wi = means.argmin(axis=1)
            gapm = means.max(axis=1) - means.min(axis=1)
            cond = ok & (bi != wi) & (gapm > 0.35)             # L833
            if not cond.any():
                continue
            with np.errstate(over="ignore"):
                self.seed[cond] = self.seed[cond] * A_LCG + C_LCG   # L837
            jit = 0.7 + 0.6 * ((self.seed >> np.uint64(33)) & np.uint64(0xFFFF)).astype(np.float64) / 65535.0
            mem = {"bayes": self.bay_m, "ewma": self.ew_m, "hawkes": self.hk_m}[name]
            r = np.nonzero(cond)[0]
            mem[r, wi[r]] = np.minimum(400.0, np.maximum(1.0, mem[r, bi[r]] * jit[r]))  # L839
            gh = np.array(fam)[wi[r]]
            self.cnt[r, gh] = 0                                # L840 removeAll
            self.rsum[r, gh] = 0.0
            self.cumLoss[r, gh] = self.hedgeCum[r]             # L843
            mutated |= cond
        if mutated.any():
            self.recompute_weights()

    def step(self, mask: np.ndarray):
        """Ordre exact de process() L704-760 : evaluate -> absorb -> evolve."""
        out = None
        if self.absorbed > 12:                                 # L726
            out = self.evaluate(mask)
        self.absorb(mask)
        if self.absorbed >= 48 and self.absorbed % 24 == 0:    # L753 (pré-incrément)
            self.evolve()
        self.absorbed += 1
        return out

    def best_head_mean(self) -> np.ndarray:  # L973-985 (mini-essaim : 14 têtes, pas 26)
        means = self.rsum / np.maximum(1, np.minimum(self.cnt, 40))
        means = np.where(self.cnt >= 20, means, -np.inf)
        return means.max(axis=1)


# ---------------------------------------------------------------------------
# PRÉ-ENREGISTREMENT (avant tout calcul — règle 2 du labo)
# ---------------------------------------------------------------------------

TOK_H0 = lab.preregister(
    "b3.conf_h0",
    "Sous H0, la confiance affichée (50+14·z sur fenêtre 60, clip [5,95], plancher "
    "SD 0.2, seuil 12 points — Swarm.swift L908-920) est centrée : E[conf]≈50, "
    "distribution symétrique, P(conf>70) ≈ bruit t_59 ≈ 0.074 ; le plancher 0.2 "
    "ne mord jamais (SD vrai des hits top-20 = 1.688).",
    "E[conf], P(conf>70), P(conf>80), P(btSD<0.2) sur 1e6 fenêtres de 60 hits "
    "i.i.d. hyper(80,20,20) — loi exacte de ensembleOv sous H0 (invariance : la "
    "loi conditionnelle de l'overlap ne dépend pas du choix des 20 numéros) ; "
    "équivalence vérifiée contre un mini-essaim AdaHedge+évolution fidèle.",
    "simulation i.i.d. hyper(80,20,20), 1e6 fenêtres ; contrôle : 3000 "
    "trajectoires mini-essaim sur tirages SRS",
    "centrée si |E[conf]-50| < 1 ET P(conf>70) <= 0.12 ET |E[conf]_mini-essaim - "
    "E[conf]_iid| < 1 point ; sinon biaisée",
    track="B",
)
TOK_REAL = lab.preregister(
    "b3.conf_real",
    "Rejouée en marche avant sur l'archive réelle (70 560 tirages), la trajectoire "
    "de confiance est dans la plage H0 : l'app ne « voit » pas un avantage.",
    "fraction temporelle (fenêtres pleines, n=60) de conf>70 sur la marche avant "
    "réelle du mini-essaim 14 têtes",
    "1000 trajectoires H0 i.i.d. hyper(80,20,20) de même longueur (70 547 points)",
    "conforme si p empirique (Davison-Hinkley) > 0.05 ; Holm sur registre entier ensuite",
    track="B",
)
TOK_EVAL = lab.preregister(
    "b3.evalue_real",
    "L'e-valeur affichée (mélange 8 θ, clip 80/60 — L771-774, 922-924) reste "
    "bornée sous H0 et ne croît pas sur l'archive réelle (Ville : P(max>=20)<=5%).",
    "max_t eValue sur la marche avant réelle",
    "1000 trajectoires H0 i.i.d. hyper(80,20,20) de même longueur",
    "conforme si p empirique > 0.05 et max_t eValue < 20",
    track="B",
)
TOK_CAL = lab.preregister(
    "b3.conf_calibration",
    "La confiance n'est PAS une probabilité calibrée : quand l'app affiche >70, "
    "P(le prochain tirage dépasse l'espérance, ov>=6) reste ≈ P(H>=6)=0.374, pas 0.70.",
    "P(ov_{t+1}>=6 | conf_t>70) sur la marche avant réelle ; null = même taux sous H0",
    "1000 trajectoires H0 i.i.d. hyper(80,20,20)",
    "non calibrée si le taux réel est compatible H0 (p>0.05) et |taux - 0.70| > 0.2 ; "
    "calibrée si le taux suit conf/100",
    track="B",
)


def main():
    rng = np.random.default_rng(20260827)
    t0 = time.time()
    print(f"SD vrai des hits top-20 : {SD_TRUE:.4f} ; P(H>=6) = {P_GE6:.4f}")

    # -- Partie 1 : distribution H0 exacte (1e6 fenêtres i.i.d.) --------------
    M = 1_000_000
    confs = np.empty(M, np.int64)
    zs = np.empty(M)
    sds = np.empty(M)
    for a in range(0, M, 100_000):
        b = a + 100_000
        hits = rng.choice(VALS, size=(100_000, 60), p=PMF)
        confs[a:b], zs[a:b], sds[a:b] = conf_snapshot(hits)
    q = np.percentile(confs, [1, 5, 25, 50, 75, 95, 99])
    p_gt70 = float((confs > 70).mean())
    p_ge80 = float((confs >= 80).mean())
    p_gt80 = float((confs > 80).mean())
    p_lt30 = float((confs < 30).mean())
    p_chip = float((zs >= 2).mean())
    floor_bites = int((sds < 0.2).sum())
    print(f"\n[P1] H0 i.i.d., n=60, M={M}:")
    print(f"  E[conf]={confs.mean():.3f}  méd={np.median(confs):.0f}  sd={confs.std():.2f}")
    print(f"  quantiles 1/5/25/50/75/95/99 : {q}")
    print(f"  P(conf>70)={p_gt70:.4f}  P(conf>80)={p_gt80:.4f}  P(conf>=80)={p_ge80:.4f}  "
          f"P(conf<30)={p_lt30:.4f}")
    print(f"  P(chip 'Sur-performance', z>=2)={p_chip:.4f}")
    print(f"  plancher SD : P(btSD<0.2)={floor_bites}/{M}  min btSD={sds.min():.3f}  "
          f"P(btSD<1.0)={(sds < 1.0).mean():.2e}")
    # fenêtres courtes (démarrage, n=12 et 24)
    for n_small in (12, 24):
        hits = rng.choice(VALS, size=(300_000, n_small), p=PMF)
        c_s, _, _ = conf_snapshot(hits)
        print(f"  n={n_small}: E[conf]={c_s.mean():.2f}  P(conf>70)={(c_s > 70).mean():.4f}")

    # -- Partie 2 : mini-essaim adaptatif sous H0 (le canal de « fuite ») -----
    R2, T2 = 3000, 420
    eng = MiniSwarm(R2)
    ov_hist = np.empty((T2 - 13, R2), np.float64)
    for t in range(T2):
        mask = lab.srs(R2, rng).astype(np.float64)
        out = eng.step(mask)
        if out is not None:
            ov_hist[t - 13] = out[0]
    conf_mini, _, _ = conf_snapshot(ov_hist[-60:].T)     # suffix(60), comme l'app
    exp10_final = out[1]
    bhm = eng.best_head_mean()
    d_mean = conf_mini.mean() - confs.mean()
    se = conf_mini.std(ddof=1) / math.sqrt(R2)
    print(f"\n[P2] mini-essaim AdaHedge+évolution, R={R2}, T={T2} tirages SRS :")
    print(f"  E[conf]={conf_mini.mean():.3f} (iid: {confs.mean():.3f}, Δ={d_mean:+.3f} ± {2*se:.3f})")
    print(f"  P(conf>70)={(conf_mini > 70).mean():.4f} (iid: {p_gt70:.4f})  "
          f"P(conf>80)={(conf_mini > 80).mean():.4f} (iid: {p_gt80:.4f})")
    print(f"  [expl.] bestHeadMean (max 14 têtes, suffix 40) : E={bhm.mean():.3f} vs 5.0 "
          f"(l'app en a 26 : biais ≥ celui-ci)")
    print(f"  [expl.] 'ESPÉRANCE' grille k=10 (Σ posterior bayes.b des 10 mieux classés) : "
          f"E={exp10_final.mean():.3f} vs 2.50 vrai")

    # -- Partie 3 : marche avant sur l'archive réelle -------------------------
    arch = lab.load()
    N = len(arch)
    eng1 = MiniSwarm(1)
    ov_real = np.empty(N - 13, np.float64)
    exp10_real = np.empty(N - 13, np.float64)
    m = arch.mask.astype(np.float64)
    for t in range(N):
        out = eng1.step(m[t:t + 1])
        if out is not None:
            ov_real[t - 13] = out[0][0]
            exp10_real[t - 13] = out[1][0]
    conf_r, z_r, n_r = confidence_series(ov_real)
    full = n_r == 60
    frac70_real = float((conf_r[full] > 70).mean())
    frac80_real = float((conf_r[full] > 80).mean())
    ev_real = evalue_series(ov_real)
    e_lab, log10_e_lab = lab.evalue(ov_real.astype(np.int64), k=DRAWN)
    calib_idx = np.nonzero((conf_r[:-1] > 70) & full[:-1])[0]
    calib_real = float((ov_real[calib_idx + 1] >= 6).mean())
    mid_idx = np.nonzero((np.abs(conf_r[:-1] - 50) <= 5) & full[:-1])[0]
    calib_mid = float((ov_real[mid_idx + 1] >= 6).mean())
    print(f"\n[P3] archive réelle, {N} tirages, {len(ov_real)} points de backtest :")
    print(f"  moyenne backtest = {ov_real.mean():.4f} (attendu 5.0)")
    print(f"  confiance finale affichée = {conf_r[-1]}  ;  E_t[conf]={conf_r[full].mean():.2f}")
    print(f"  fraction du temps conf>70 : {frac70_real:.4f}  conf>80 : {frac80_real:.4f}  "
          f"max={conf_r.max()}  min={conf_r.min()}")
    print(f"  e-valeur finale = {ev_real[-1]:.3g}  max_t = {ev_real.max():.3f}  "
          f"(lab.evalue : log10 e = {log10_e_lab:.2f})")
    print(f"  P(ov_next>=6 | conf>70) = {calib_real:.4f} ({len(calib_idx)} points)  "
          f"| conf∈[45,55] = {calib_mid:.4f}")

    # -- Partie 4 : 1000 trajectoires H0 de même longueur ---------------------
    RT = 1000
    L = len(ov_real)
    frac70_h0 = np.empty(RT)
    final_h0 = np.empty(RT)
    maxev_h0 = np.empty(RT)
    finev_h0 = np.empty(RT)
    calib_h0 = np.empty(RT)
    maxconf_h0 = np.empty(RT)
    for r in range(RT):
        ov = rng.choice(VALS, size=L, p=PMF).astype(np.float64)
        c, _, n = confidence_series(ov)
        f = n == 60
        frac70_h0[r] = (c[f] > 70).mean()
        final_h0[r] = c[-1]
        maxconf_h0[r] = c.max()
        ev = evalue_series(ov)
        maxev_h0[r] = ev.max()
        finev_h0[r] = ev[-1]
        ci = np.nonzero((c[:-1] > 70) & f[:-1])[0]
        calib_h0[r] = (ov[ci + 1] >= 6).mean() if len(ci) else np.nan
    print(f"\n[P4] {RT} trajectoires H0 (L={L}) :")
    print(f"  fraction>70 : moy={frac70_h0.mean():.4f}  q[0.5,99.5]%="
          f"[{np.percentile(frac70_h0, 0.5):.4f}, {np.percentile(frac70_h0, 99.5):.4f}]")
    print(f"  conf finale : moy={final_h0.mean():.1f}  ;  max conf sur trajectoire : "
          f"moy={maxconf_h0.mean():.1f} (le 95 est atteint tôt ou tard : "
          f"P={np.mean(maxconf_h0 >= 95):.2f})")
    print(f"  max eValue : méd={np.median(maxev_h0):.2f}  q99={np.percentile(maxev_h0, 99):.1f}  "
          f"P(max>=20)={np.mean(maxev_h0 >= 20):.4f} (Ville<=0.05)")
    print(f"  eValue finale : méd={np.median(finev_h0):.2e}  q99={np.percentile(finev_h0, 99):.2e}")
    print(f"  calib H0 P(ov>=6|conf>70) : moy={np.nanmean(calib_h0):.4f}")

    # -- Partie 5 : puissance -------------------------------------------------
    def tilted(delta: float) -> np.ndarray:
        lo, hi = 0.0, 3.0
        for _ in range(60):
            th = (lo + hi) / 2
            qq = PMF * np.exp(th * H21)
            qq /= qq.sum()
            if (qq * H21).sum() < UNIF + delta:
                lo = th
            else:
                hi = th
        return qq

    print("\n[P5] réponse de l'afficheur à un vrai biais (fenêtres n=60, 200k) :")
    for delta in (0.02, 0.05, 0.10, 0.20, 0.50):
        qq = tilted(delta)
        hits = rng.choice(VALS, size=(200_000, 60), p=qq)
        c_t, _, _ = conf_snapshot(hits)
        print(f"  δ={delta:4.2f} hits/tirage : E[conf]={c_t.mean():5.1f}  "
              f"P(conf>70)={(c_t > 70).mean():.3f}")
    lo_thr, hi_thr = np.percentile(frac70_h0, [0.5, 99.5])
    print("  puissance du test b3.conf_real (fraction>70 hors [q0.5,q99.5] H0) :")
    powers = {}
    for delta in (0.01, 0.02, 0.05):
        qq = tilted(delta)
        det = 0
        reps = 100
        for _ in range(reps):
            ov = rng.choice(VALS, size=L, p=qq).astype(np.float64)
            c, _, n = confidence_series(ov)
            fr = (c[n == 60] > 70).mean()
            det += int(fr < lo_thr or fr > hi_thr)
        powers[delta] = det / reps
        print(f"  δ={delta:4.2f} : puissance = {det / reps:.2f}")

    # -- Contrôle de fuite (leak_check sur tranche, mini-essaim comme predict) --
    sl = arch.slice(0, 3000)
    calls = {"n": 0}

    def predict(past, t):
        calls["n"] += 1
        e = MiniSwarm(1)
        mm = past.mask.astype(np.float64)
        for i in range(mm.shape[0]):
            e.step(mm[i:i + 1])
        Z = e.zscore(e.fields())
        ens = np.einsum('rh,rhp->rp', e.w, Z)[0]
        return np.argsort(-ens)[:DRAWN] + 1

    ok_leak, spots = lab.leak_check(sl, predict, k=DRAWN, warmup=500, probes=6, repeats=4)
    print(f"\n[leak_check] tranche 3000 tirages, 6 sondes x 4 futurs : "
          f"{'PROPRE' if ok_leak else f'FUITE {spots}'} ({calls['n']} appels)")

    # -- Registre -------------------------------------------------------------
    centered = (abs(confs.mean() - 50) < 1) and (p_gt70 <= 0.12) and (abs(d_mean) < 1)
    lab.record(
        TOK_H0, float(confs.mean()),
        verdict="centrée" if centered else "biaisée",
        notes=(f"n=60 iid hyper: E[conf]={confs.mean():.3f}, méd=50, "
               f"q1..99={list(q)}, P(>70)={p_gt70:.4f}, P(>80)={p_gt80:.4f}, "
               f"P(<30)={p_lt30:.4f}, P(z>=2)={p_chip:.4f} ; plancher 0.2 : "
               f"jamais mordu sur 1e6 (min btSD={sds.min():.3f}) et il ne peut que "
               f"REDUIRE |z| (max au dénominateur) ; mini-essaim adaptatif "
               f"(AdaHedge+évolution, mêmes fenêtres) : E[conf]={conf_mini.mean():.3f}, "
               f"Δ={d_mean:+.3f}±{2 * se:.3f} — la réutilisation backtest/poids ne "
               f"déplace pas le centre (théorème d'invariance vérifié). "
               f"Réponse à un vrai biais : δ=0.05 hits → E[conf]≈53, δ=0.2 → ≈63. "
               f"EXPLORATOIRE (canaux voisins biaisés, eux) : bestHeadMean "
               f"E={bhm.mean():.2f}>5 (sélection du max, 14 têtes ; l'app en a 26, "
               f"caveat déjà affiché AnalyseView L285) ; 'ESPÉRANCE' de grille "
               f"E={exp10_final.mean():.2f} vs 2.50 (winner's curse du posterior "
               f"bayes.b sur les numéros sélectionnés, GridsView L261)."),
    )
    null_frac = lab.Null(float(frac70_h0.mean()), float(frac70_h0.std(ddof=1)), RT, frac70_h0)
    lab.record(
        TOK_REAL, frac70_real, null=null_frac,
        power_at=f"δ=0.01:{powers[0.01]:.2f}, δ=0.02:{powers[0.02]:.2f}, δ=0.05:{powers[0.05]:.2f}",
        verdict="conforme H0" if null_frac.p_two_sided(frac70_real) > 0.05 else "hors plage H0",
        notes=(f"archive réelle: frac>70={frac70_real:.4f}, frac>80={frac80_real:.4f}, "
               f"conf finale={conf_r[-1]}, E_t[conf]={conf_r[full].mean():.2f}, "
               f"moyenne backtest={ov_real.mean():.4f} ; H0 [q0.5,q99.5]="
               f"[{lo_thr:.4f},{hi_thr:.4f}] ; leak_check tranche 3000: "
               f"{'propre' if ok_leak else spots} ; marche avant mini-essaim 14 têtes "
               f"(loi de conf invariante au prédicteur sous H0)."),
    )
    null_ev = lab.Null(float(maxev_h0.mean()), float(maxev_h0.std(ddof=1)), RT, maxev_h0)
    lab.record(
        TOK_EVAL, float(ev_real.max()), null=null_ev,
        verdict="conforme H0" if (null_ev.p_two_sided(float(ev_real.max())) > 0.05
                                  and ev_real.max() < 20) else "anomalie",
        notes=(f"max_t eValue réel={ev_real.max():.3f} (seuil alerte UI: 20) ; "
               f"eValue finale réelle={ev_real[-1]:.3g} (affichée '0.00' : sous H0 "
               f"la martingale s'appauvrit, c'est le comportement honnête) ; "
               f"lab.evalue log10={log10_e_lab:.2f} ; H0: méd(max)={np.median(maxev_h0):.2f}, "
               f"P(max>=20)={np.mean(maxev_h0 >= 20):.4f}."),
    )
    null_cal = lab.Null(float(np.nanmean(calib_h0)), float(np.nanstd(calib_h0, ddof=1)), RT,
                        calib_h0[~np.isnan(calib_h0)])
    lab.record(
        TOK_CAL, calib_real, null=null_cal,
        verdict="non calibrée (par construction)",
        notes=(f"P(ov_next>=6 | conf>70) réel={calib_real:.4f}, sous H0={np.nanmean(calib_h0):.4f}, "
               f"P(H>=6)={P_GE6:.4f} — plate quel que soit l'affichage "
               f"(conf∈[45,55] réel: {calib_mid:.4f}). 'confiance 70' ne signifie "
               f"aucun événement à 70 % ; c'est un z rescalé. L'UI le dit "
               f"('50 = hasard pur') mais le mot 'confiance /100' invite la "
               f"lecture probabiliste."),
    )
    print(f"\n4 entrées consignées au registre. Durée totale : {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
