"""A3 — Détection de rupture à résolution libre (scan multi-échelles).

Question. Le §15 de l'audit a testé 8 fenêtres FIXES de ~9 000 tirages :
un défaut d'implémentation de quelques jours (quelques centaines de
tirages) y serait dilué à 1/10 et invisible. Ici : balayage de fenêtres
glissantes de 4 tailles (200, 500, 2 000, 9 000) à pas fin, 4 statistiques
par fenêtre, et le MAXIMUM du balayage est calibré sous H0 par simulation
d'archives SRS complètes — jamais comparé à un seuil de test unique.

Statistiques par fenêtre (défauts visés distincts) :
  chi2 : somme (C_n - W/4)^2 sur les 80 numéros — uniformité du champ ;
  ov1  : recouvrement moyen lag-1 (E=5,0)      — dépendance sérielle ;
  adj  : paires adjacentes moyennes, grille 8x10 (E=8,538) — géométrie ;
  sum  : somme moyenne des 20 numéros (E=810)  — dérive directionnelle
         bas/haut qu'un chi2 omnibus (79 ddl) dilue.

Chaque stat de fenêtre est standardisée par des moments (mu, sd) estimés
sur M archives SRS simulées (jamais tabulés), et la statistique de
l'expérience est LE max global de |z| sur (4 stats x 4 tailles x toutes
positions) — ~42 600 scores par archive. Ce max est calibré par
lab.calibrate sur des archives SRS de 70 560 tirages : c'est le seul null
valide pour un max de balayage.

Puissance (lab.power) : fenêtre corrompue de longueur L injectée à
position aléatoire — biais de fréquence d'amplitude delta (8 numéros
favorisés, tirage pondéré Gumbel top-20, delta = biais marginal MESURÉ)
— plus un défaut secondaire de répétition (recouvrement lag-1 forcé).
Livrable : la courbe de détectabilité (L x delta -> puissance).

Usage : python3 a3_changepoint.py [--fast] [--no-record]
  --fast      réplicats réduits (fumée), n'écrit PAS au registre
  --no-record calcule tout, n'écrit pas au registre
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab

# --------------------------------------------------------------------------
# Configuration (pré-enregistrée : rien ici n'a été choisi après coup)
# --------------------------------------------------------------------------

N = 70560
SIZES = {200: 10, 500: 25, 2000: 100, 9000: 450}     # taille -> pas
STATS = ("chi2", "ov1", "adj", "sum")
FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST

M_MOMENTS = 10 if FAST else 40        # archives SRS pour les moments
R_NULL = 40 if FAST else 300          # réplicats du null du max global
R_POWER = 10 if FAST else 50          # réplicats par point de puissance
POWER_L = (200, 500, 2000)
POWER_DELTA = (0.05, 0.10, 0.20, 0.40)   # biais marginal cible des favoris
REPEAT_POINTS = ((500, 6), (500, 7))     # (L, overlap lag-1 forcé E=j)

EXP_ID = "a3.changepoint_scan"


# --------------------------------------------------------------------------
# Statistiques de fenêtre — vectorisées, O(1) par fenêtre via cumuls
# --------------------------------------------------------------------------

def per_draw_features(mask: np.ndarray):
    o = np.zeros(len(mask))
    o[1:] = np.sum(mask[1:] & mask[:-1], axis=1)     # o[0]=0 : identique
    g = mask.reshape(len(mask), 8, 10)               # null/observé, neutre
    adj = ((g[:, :, :-1] & g[:, :, 1:]).sum(axis=(1, 2))
           + (g[:, :-1, :] & g[:, 1:, :]).sum(axis=(1, 2)))
    s = (mask * np.arange(1, 81)).sum(axis=1)
    return o, adj.astype(np.float64), s.astype(np.float64)


def window_stats(mask: np.ndarray) -> dict:
    """(stat, W) -> vecteur des stats brutes, une par position de fenêtre."""
    cum = np.vstack([np.zeros((1, 80), np.int32),
                     np.cumsum(mask, axis=0, dtype=np.int32)])
    o, adj, s = per_draw_features(mask)
    co, ca, cs = (np.concatenate([[0.0], np.cumsum(v)]) for v in (o, adj, s))
    out = {}
    for W, step in SIZES.items():
        starts = np.arange(0, len(mask) - W + 1, step)
        C = (cum[starts + W] - cum[starts]).astype(np.float64)
        out[("chi2", W)] = ((C - W / 4.0) ** 2).sum(axis=1)
        out[("ov1", W)] = (co[starts + W] - co[starts]) / W
        out[("adj", W)] = (ca[starts + W] - ca[starts]) / W
        out[("sum", W)] = (cs[starts + W] - cs[starts]) / W
    return out


def estimate_moments(m_reps: int, seed: int = 12345) -> dict:
    """(mu, sd) de chaque stat de fenêtre, estimés sur des archives SRS.

    Simulés, jamais tabulés (règle 1) : aucune espérance à la main.
    """
    rng = np.random.default_rng(seed)
    pools: dict = {k: [] for k in window_stats(lab.srs(2 * max(SIZES), rng)).keys()}
    for _ in range(m_reps):
        for k, v in window_stats(lab.srs(N, rng)).items():
            pools[k].append(v)
    return {k: (float(np.mean(np.concatenate(v))), float(np.std(np.concatenate(v))))
            for k, v in pools.items()}


class Scan:
    """Max global de |z| ; collecte optionnelle des maxima par famille."""

    def __init__(self, moments: dict):
        self.moments = moments
        self.collect = False
        self.family_rows: list[dict] = []
        self.last_argmax = None

    def family_z(self, mask: np.ndarray) -> dict:
        return {k: np.abs((v - self.moments[k][0]) / self.moments[k][1])
                for k, v in window_stats(mask).items()}

    def __call__(self, mask: np.ndarray) -> float:
        fz = self.family_z(mask)
        fam_max = {k: float(v.max()) for k, v in fz.items()}
        if self.collect:
            self.family_rows.append(fam_max)
        key = max(fam_max, key=fam_max.get)
        self.last_argmax = (key, int(np.argmax(fz[key])) * SIZES[key[1]])
        return max(fam_max.values())


# --------------------------------------------------------------------------
# Contaminations — défauts d'amplitude connue, mesurée et non supposée
# --------------------------------------------------------------------------

def weighted_srs(n: int, log_w: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """n tirages 20/80 pondérés sans remise (Gumbel top-k)."""
    keys = log_w + rng.gumbel(size=(n, 80))
    out = np.zeros((n, 80), bool)
    idx = np.argpartition(-keys, 20, axis=1)[:, :20]
    np.put_along_axis(out, idx, True, axis=1)
    return out


def calibrate_gamma(delta: float, seed: int = 777) -> tuple[float, float]:
    """gamma (log-poids des 8 favoris) tel que P(inclusion) = 0,25(1+delta).

    Le biais marginal réellement obtenu est MESURÉ par simulation et
    renvoyé avec gamma — c'est lui qui figure dans la courbe.
    """
    rng = np.random.default_rng(seed)
    target = 0.25 * (1.0 + delta)

    def marginal(gamma: float, m: int = 60000) -> float:
        lw = np.zeros(80)
        lw[:8] = gamma
        return float(weighted_srs(m, lw, rng)[:, :8].mean())

    lo, hi = 0.0, 3.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if marginal(mid) < target:
            lo = mid
        else:
            hi = mid
    g = 0.5 * (lo + hi)
    return g, marginal(g, m=200000) / 0.25 - 1.0


def make_contaminate_freq(L: int, gamma: float):
    """Fenêtre [start, start+L) retirée avec 8 numéros favorisés (aléatoires)."""
    def contaminate(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        start = int(rng.integers(0, N - L + 1))
        fav = rng.choice(80, size=8, replace=False)
        lw = np.zeros(80)
        lw[fav] = gamma
        mask[start:start + L] = weighted_srs(L, lw, rng)
        return mask
    return contaminate


def make_contaminate_repeat(L: int, j: int):
    """Fenêtre où chaque tirage garde exactement j numéros du précédent
    (recouvrement lag-1 forcé à j au lieu de E=5)."""
    def contaminate(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        start = int(rng.integers(1, N - L + 1))
        for t in range(start, start + L):
            prev = np.flatnonzero(mask[t - 1])
            keep = rng.choice(prev, size=j, replace=False)
            other = np.setdiff1d(np.arange(80), prev, assume_unique=True)
            new = np.concatenate([keep, rng.choice(other, size=20 - j, replace=False)])
            mask[t] = False
            mask[t, new] = True
        return mask
    return contaminate


# --------------------------------------------------------------------------
# Expérience
# --------------------------------------------------------------------------

def main() -> None:
    t_start = time.time()
    a = lab.load()
    assert len(a) == N

    # -- 1. Pré-enregistrement : AVANT tout regard sur le résultat -------
    tok = lab.preregister(
        EXP_ID,
        hypothese := ("Une fenêtre temporelle localisée (>=200 tirages) dévie de SRS sur au "
                      "moins une de 4 stats (chi2 champ, overlap lag-1, adjacences 8x10, "
                      "somme moyenne), invisible aux 8 fenêtres fixes du §15"),
        statistic=("max global de |z| sur balayage : 4 stats x fenêtres "
                     f"{list(SIZES)} (pas {list(SIZES.values())}), moments par simulation "
                     f"SRS (M={M_MOMENTS}), ~42 600 scores par archive"),
        null_method=(f"lab.calibrate du max global sur archives SRS complètes de {N} "
                     f"tirages, R={R_NULL} réplicats — le max d'un balayage n'a pas la "
                     "loi d'un test unique, seul ce null est valide"),
        decision=(f"anomalie candidate si p empirique <= plancher 1/(R+1)={1/(R_NULL+1):.2e} "
                  "(alors re-calibration à plus de réplicats avant toute déclaration, seuil "
                  "final = Holm registre ~1,55e-05) ; sinon conforme"),
        track="A",
    )
    print(f"pré-enregistré  id={tok['id']}  seal={tok['seal']}")
    print(f"hypothèse : {hypothese}\n")

    # -- 2. Moments des stats de fenêtre (simulés) -----------------------
    t0 = time.time()
    moments = estimate_moments(M_MOMENTS)
    scan = Scan(moments)
    print(f"moments : M={M_MOMENTS} archives SRS, {time.time()-t0:.0f} s")
    for k, (mu, sd) in sorted(moments.items()):
        print(f"  {k[0]:>4} W={k[1]:>5} : mu={mu:10.3f}  sd={sd:8.4f}")

    # -- 3. Null du max global -------------------------------------------
    t0 = time.time()
    scan.collect = True
    null = lab.calibrate(scan, N, reps=R_NULL, seed=0)
    null_family_rows = scan.family_rows
    scan.collect, scan.family_rows = False, []
    q = np.quantile(null.samples, [0.5, 0.9, 0.99])
    floor_thr = float(null.samples.max())
    print(f"\nnull max global : R={R_NULL} ({time.time()-t0:.0f} s)  "
          f"mean={null.mean:.3f} sd={null.sd:.3f}  q50={q[0]:.3f} q90={q[1]:.3f} "
          f"q99={q[2]:.3f} max={floor_thr:.3f}")

    # -- 4. Observation ---------------------------------------------------
    obs = scan(a.mask)
    obs_key, obs_pos = scan.last_argmax
    obs_fz = scan.family_z(a.mask)
    p = null.p_two_sided(obs)
    ts0 = a.ts[obs_pos]
    date = time.strftime("%Y-%m-%d", time.gmtime(ts0))

    print(f"\nobservé : max global |z| = {obs:.3f}  (stat={obs_key[0]}, W={obs_key[1]}, "
          f"début tirage {obs_pos} ~ {date})")
    print(f"p empirique (Davison-Hinkley) = {p:.4f}   z vs null du max = {null.z(obs):+.2f}")

    print("\nDiagnostic par famille (max |z| de la famille vs son propre null simulé) :")
    print(f"  {'stat':>4} {'W':>5} | {'obs max':>7} | {'null q50':>8} {'null q99':>8} "
          f"{'null max':>8} | {'p_fam':>6}")
    for k in sorted(obs_fz.keys()):
        fam_obs = float(obs_fz[k].max())
        fam_null = np.array([row[k] for row in null_family_rows])
        p_fam = (1 + np.sum(fam_null >= fam_obs)) / (1 + len(fam_null))
        fq = np.quantile(fam_null, [0.5, 0.99])
        print(f"  {k[0]:>4} {k[1]:>5} | {fam_obs:7.3f} | {fq[0]:8.3f} {fq[1]:8.3f} "
              f"{fam_null.max():8.3f} | {p_fam:6.3f}")
    print("  (diagnostic seulement — la décision pré-enregistrée porte sur le max global)")

    # -- 5. Puissance : courbe de détectabilité ---------------------------
    # seuil de détection = plancher empirique (obs > tous les réplicats null)
    alpha_z_floor = null.z(floor_thr)
    print(f"\npuissance : seuil = max des {R_NULL} réplicats null "
          f"(|z|>={alpha_z_floor:.2f}, p plancher {1/(R_NULL+1):.1e}), "
          f"{R_POWER} réplicats contaminés/point")

    print("calibration gamma -> biais marginal mesuré :")
    gammas = {}
    for d in POWER_DELTA:
        g, d_meas = calibrate_gamma(d)
        gammas[d] = (g, d_meas)
        print(f"  delta cible {d:.2f} : gamma={g:.4f}, biais mesuré {d_meas*100:+.1f} %")

    print("\nCourbe de détectabilité — biais de fréquence (8 numéros favorisés) :")
    header = "  L \\ delta |" + "".join(f" {d*100:5.0f} % |" for d in POWER_DELTA)
    print(header)
    print("  " + "-" * (len(header) - 2))
    power_grid = {}
    for L in POWER_L:
        row = f"  {L:>9} |"
        for d in POWER_DELTA:
            pw = lab.power(scan, make_contaminate_freq(L, gammas[d][0]), N, null,
                           reps=R_POWER, seed=100 * L + int(d * 100),
                           alpha_z=alpha_z_floor)
            power_grid[(L, d)] = pw
            row += f"  {pw:5.2f} |"
        print(row, flush=True)

    print("\nDéfaut secondaire — répétition (overlap lag-1 forcé à j, E_H0=5) :")
    repeat_pw = {}
    for L, j in REPEAT_POINTS:
        pw = lab.power(scan, make_contaminate_repeat(L, j), N, null,
                       reps=R_POWER, seed=9000 + 10 * L + j, alpha_z=alpha_z_floor)
        repeat_pw[(L, j)] = pw
        print(f"  L={L}, overlap force j={j} (soit +{(j-5)/5*100:.0f} %) : puissance {pw:.2f}")

    # -- 6. Verdict et registre ------------------------------------------
    verdict = "conforme" if p > 1 / (R_NULL + 1) else "candidate — recalibrer"
    power_str = "; ".join(f"L={L},d={d:.2f}:{power_grid[(L,d)]:.2f}"
                          for L in POWER_L for d in POWER_DELTA)
    repeat_str = "; ".join(f"L={L},j={j}:{v:.2f}" for (L, j), v in repeat_pw.items())
    notes = (f"argmax: {obs_key[0]} W={obs_key[1]} @tirage {obs_pos} ({date}); "
             f"seuil puissance = plancher empirique p={1/(R_NULL+1):.1e} "
             f"(Holm 1,55e-05 est plus strict: puissance au seuil Holm <= mesurée); "
             f"repeat-defect: {repeat_str}; M_moments={M_MOMENTS}, R_power={R_POWER}")

    print(f"\nVERDICT : {verdict}  (max global {obs:.3f}, p={p:.4f}, "
          f"plancher {1/(R_NULL+1):.2e})")
    if NO_RECORD:
        print("(--fast/--no-record : rien n'est écrit au registre)")
    elif any(r.get("id") == EXP_ID for r in lab.ledger()):
        print(f"registre : entrée '{EXP_ID}' déjà présente — pas de doublon écrit")
    else:
        lab.record(tok, observed=obs, null=null,
                   power_at=power_str, verdict=verdict, notes=notes)
        print(f"registre : consigné sous '{EXP_ID}'")
    print(f"\ntotal : {time.time()-t_start:.0f} s")


if __name__ == "__main__":
    main()
