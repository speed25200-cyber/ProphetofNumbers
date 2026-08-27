"""F2 — Portefeuille d'e-processus : la batterie par lots remplacée par un pari séquentiel.

Les 23 voies du dossier sont des tests PAR LOTS : on prend les 70 560
tirages, on calcule une statistique, on la compare à un null. Deux failles :
un défaut transitoire (a3 : une fenêtre de 200 tirages à moins de 30 % de
biais passe inaperçue) est dilué sur l'ensemble, et chaque nouveau regard
oblige à recorriger la multiplicité (le registre en est à m = 3 306, seuil
Holm 1,5e-05).

Les e-processus (Shafer 2021, Ramdas-Grünwald-Vovk-Shafer 2023) répondent
aux deux à la fois : une e-valeur est une martingale de pari sous H0
(espérance 1 À CHAQUE PAS), donc valide à tout instant d'arrêt (Ville :
P(sup_t E_t >= 1/alpha) <= alpha, sans aucune correction) — et la MOYENNE
d'e-valeurs est une e-valeur, donc un portefeuille de paris sur des
hypothèses différentes se combine sans multiplicité. L'app en a déjà un
(`SwarmEngine.eLogs` dans `Swarm.swift`, exposé ici via `lab.evalue`) : un
mélange de martingales à inclinaison exponentielle sur le recouvrement du
top-20 de l'essaim, theta in +-{0.05,0.10,0.20,0.40}. C'est un portefeuille
d'UN SEUL pari. Ce fichier en construit quatre, un par famille déjà testée
par lots ailleurs dans le labo :

  lag1_overlap   recouvrement lag-1 (rémanence)          -- c1 (T1), d2
  bonus_echo     bonus_t dans le tirage t+1 (V3)          -- d7_bonus, d7b_chasse
  sum_marginal   somme des 20 numéros (dérive directionnelle
                 de la fréquence marginale, cf. le "sum" de a3)
  overlap_shape  forme/dispersion du recouvrement lag-1    -- d3_nonlineaire (S1),
                 analogue séquentiel EXACT du diagnostic "variance" que
                 d3b_chasse a utilisé pour débusquer S1 (z=+0.95, RAPPORT §2)

Chacun utilise EXACTEMENT la même construction que `lab.evalue` /
`Swarm.eLogs` : un mélange de martingales à inclinaison exponentielle,
mais avec m(theta) = E_H0[exp(theta*U)] calculé sur la loi EXACTE (jamais
simulée, jamais approximée) de la statistique standardisée U — garantissant
espérance 1 par construction. La partie qui décide de tout : ce n'est pas
une preuve. `main_martingale_check()` le vérifie empiriquement par
simulation (E[e_t] ~= 1 à plusieurs t, sous H0), AVANT toute lecture des
vraies données -- l'erreur classique est un "e-processus" dont l'espérance
dérive, et ce fichier la débusquerait comme telle si elle existait.

Puissance : les MÊMES contaminations que a3 (`weighted_srs`,
`calibrate_gamma`, `make_contaminate_freq`, `make_contaminate_repeat`,
importées directement de `a3_changepoint.py`) sont rejouées ici, pour une
comparaison loyale, apples-to-apples, contre le tableau déjà publié
(RAPPORT §2, 16e voie).

Usage : python3 f2_eprocessus.py [--fast] [--no-record]
  --fast      réplicats réduits (fumée), n'écrit PAS au registre
  --no-record calcule tout, n'écrit pas au registre
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

EXPDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EXPDIR))
sys.path.insert(0, EXPDIR)
import lab
import a3_changepoint as a3   # réutilise SES contaminations, pour une comparaison loyale

POOL, DRAWN = lab.POOL, lab.DRAWN
N = 70560
FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST

R_NULL = 30 if FAST else 100          # archives complètes : vérif martingale + seuil du max
R_POWER = 6 if FAST else 20           # réplicats par point de puissance (fenêtres a3)
THETAS = np.array([0.05, 0.10, 0.20, 0.40, -0.05, -0.10, -0.20, -0.40])   # comme Swarm.eLogs
# Checkpoints PETITS (t explicite, peu de pas cumulés : la moyenne d'échantillon
# de e_t y est encore un estimateur bien posé) + GRANDS (fraction de T, où un
# martingale non-négatif d'espérance 1 devient intrinsèquement à queue lourde
# -- cf. note dans report_martingale_check). Les deux régimes sont nécessaires :
# le premier détecte un bug (signe, m(theta) faux), le second est hors de
# portée d'une vérification de moyenne, quel que soit R.
CHECKPOINTS_SMALL = (1, 5, 20, 100, 1000)
CHECKPOINTS_FRAC = (0.10, 0.25, 0.50, 0.75, 1.0)

EXP_ID = "f2.eprocessus_portefeuille"


# --------------------------------------------------------------------------
# 1. Lois EXACTES sous H0 (jamais tabulées à la main : combinatoire ou DP exact)
# --------------------------------------------------------------------------

def sum_pmf() -> np.ndarray:
    """Loi exacte de la somme des 20 numéros tirés parmi 1..80.

    DP de dénombrement de sous-ensembles (le "sac à dos" 0/1 exact) :
    dp[k,s] = nombre de k-sous-ensembles de {1..n} sommant à s, construit en
    incrémentant n de 1 à 80. Comme `lab.overlap_pmf`/`lab.hits_pmf`, c'est
    une loi EXACTE (pas une formule asymptotique prise pour l'espérance —
    la faute que la règle n°1 du labo interdit), auto-vérifiée ci-dessous.
    """
    max_s = sum(range(POOL - DRAWN + 1, POOL + 1))     # 61+...+80 = 1410
    dp = np.zeros((DRAWN + 1, max_s + 1), dtype=np.int64)
    dp[0, 0] = 1
    for n in range(1, POOL + 1):
        for k in range(min(DRAWN, n), 0, -1):
            dp[k, n:] += dp[k - 1, :max_s + 1 - n]
    from math import comb
    total = int(dp[DRAWN].sum())
    assert total == comb(POOL, DRAWN), "DP somme : total incorrect"
    return dp[DRAWN].astype(np.float64) / total


OVERLAP_PMF = lab.overlap_pmf()                # support 0..20, hypergéométrique(80,20,20)
SUM_PMF = sum_pmf()                            # support 0..1410 (masse sur 210..1410)
BONUS_SUPPORT = np.array([0.0, 1.0])
BONUS_PMF = np.array([0.75, 0.25])             # bonus_t (fixé) dans un tirage frais : 20/80


def _self_check_sum_pmf() -> None:
    s = np.arange(len(SUM_PMF))
    mu = float((s * SUM_PMF).sum())
    sd = float(np.sqrt((s * s * SUM_PMF).sum() - mu * mu))
    rng = np.random.default_rng(4242)
    sim = (lab.srs(200_000, rng) * np.arange(1, 81)).sum(1)
    assert abs(mu - 810.0) < 1e-9, mu
    assert abs(mu - sim.mean()) < 5 * sim.std() / np.sqrt(len(sim)), "DP vs simulation : écart"
    assert abs(sd - sim.std()) / sd < 0.01, "DP vs simulation : écart-type"
    print(f"  sum_pmf() auto-vérifié : mu={mu:.4f} (exact 810) sd={sd:.4f} "
          f"vs simulation mu={sim.mean():.4f} sd={sim.std():.4f} (200k tirages)")


# --------------------------------------------------------------------------
# 2. Moteur générique de martingale à mélange (même construction que
#    lab.evalue / Swarm.eLogs, généralisée à toute statistique bornée dont
#    la loi EXACTE sous H0 est connue).
# --------------------------------------------------------------------------

class Family:
    """Un pari séquentiel. X_t -> g(X_t), standardisé par (mu,sd) EXACTS
    tirés de la loi H0 de g(X), mélangé sur THETAS. m(theta) est intégré
    sur la loi exacte (jamais simulé) : E_H0[facteur_t | F_{t-1}] = 1 à
    CHAQUE pas, par construction algébrique -- c'est ce que la vérification
    par simulation, plus bas, contrôle empiriquement plutôt que de le
    supposer.
    """

    def __init__(self, label: str, support: np.ndarray, pmf: np.ndarray,
                 g=lambda x: x, thetas: np.ndarray = THETAS):
        self.label, self.g, self.thetas = label, g, thetas
        self.support, self.pmf = support.astype(np.float64), pmf
        gv = g(support.astype(np.float64))
        mu = float(np.sum(pmf * gv))
        var = float(np.sum(pmf * (gv - mu) ** 2))
        assert var > 0, f"{label} : variance nulle sous H0"
        self.mu, self.sd = mu, float(np.sqrt(var))
        u = (gv - mu) / self.sd
        self.u_support = u
        ms = np.array([np.sum(pmf * np.exp(th * u)) for th in thetas])
        assert np.all(np.isfinite(ms)) and np.all(ms > 0), f"{label} : m(theta) invalide"
        self.log_m = np.log(ms)

    def exact_step_expectation(self) -> np.ndarray:
        """E_H0[facteur_t | F_{t-1}] par theta, intégré EXACTEMENT sur la loi
        connue (pas simulé) : doit valoir 1.0 à la précision flottante près.
        C'est la vérification de premier ordre -- un bug de signe ou de
        m(theta) se voit ICI, pas en attendant une simulation."""
        return np.array([np.sum(self.pmf * np.exp(th * self.u_support - lm))
                         for th, lm in zip(self.thetas, self.log_m)])

    def log_factors(self, X: np.ndarray) -> np.ndarray:
        """(T, n_theta) : theta*u_t - log m(theta), PAS encore cumulé dans le temps."""
        u = (self.g(np.asarray(X, np.float64)) - self.mu) / self.sd
        return self.thetas[None, :] * u[:, None] - self.log_m[None, :]

    def trajectory(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(e_t, log10_e_t) du mélange sur theta, cumulé dans le temps. e_t
        est la moyenne sur theta de exp(somme cumulée des facteurs) --
        c'est elle-même une e-valeur (moyenne d'e-valeurs)."""
        logs = np.cumsum(self.log_factors(X), axis=0)                  # (T, n_theta)
        mx = logs.max(axis=1)
        log_e = mx + np.log(np.mean(np.exp(logs - mx[:, None]), axis=1))
        return np.exp(np.clip(log_e, -700, 700)), log_e / np.log(10)


FAMILIES: dict[str, Family] = {
    "lag1_overlap":  Family("recouvrement lag-1 (rémanence)", np.arange(21), OVERLAP_PMF),
    "bonus_echo":    Family("bonus_t dans le tirage t+1 (V3)", BONUS_SUPPORT, BONUS_PMF),
    "sum_marginal":  Family("somme des 20 numéros (dérive marginale directionnelle)",
                             np.arange(len(SUM_PMF)), SUM_PMF),
    "overlap_shape": Family("forme/dispersion du recouvrement lag-1",
                             np.arange(21), OVERLAP_PMF, g=lambda x: (x - 5.0) ** 2),
}


def extract_X(mask: np.ndarray, bonus: np.ndarray) -> dict[str, np.ndarray]:
    """(T,) par famille, T = len(mask)-1, indexées sur "tirage t" (t=1..N-1) :
    l'info de chaque famille est disponible exactement quand le tirage t
    est révélé (mask[t-1] et bonus[t-1] sont connus avant)."""
    ov = (mask[1:] & mask[:-1]).sum(1).astype(np.float64)
    s = (mask[1:].astype(np.int64) * np.arange(1, POOL + 1)).sum(1).astype(np.float64)
    idx = bonus[:-1].astype(np.int64) - 1
    be = mask[1:][np.arange(len(mask) - 1), idx].astype(np.float64)
    return {"lag1_overlap": ov, "overlap_shape": ov, "sum_marginal": s, "bonus_echo": be}


def portfolio_trajectory(X: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """E_t du portefeuille = moyenne (LINÉAIRE, pas log) des 4 e-processus de
    famille. Une combinaison linéaire à poids fixes de martingales
    d'espérance 1 est une martingale d'espérance 1 -- aucune correction."""
    fam_e = {name: fam.trajectory(X[name])[0] for name, fam in FAMILIES.items()}
    port_e = np.mean(np.vstack(list(fam_e.values())), axis=0)
    return port_e, fam_e


# --------------------------------------------------------------------------
# 3. Génération H0 : archive SRS complète + bonus (comme d7_bonus.synth)
# --------------------------------------------------------------------------

def srs_with_bonus(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Mask SRS + bonus tiré uniformément parmi les 20 DU MÊME tirage --
    le null exact de `d7_bonus.py` (P(bonus_t in tirage t+1) = 20/80 = 1/4
    exactement, puisque bonus_t est fixé avant que le tirage t+1, frais et
    indépendant sous H0, ne soit révélé)."""
    mask = lab.srs(n, rng)
    nums = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
    pick = rng.integers(0, DRAWN, size=n)
    bonus = nums[np.arange(n), pick]
    return mask, bonus


# --------------------------------------------------------------------------
# 4. Vérification de la martingale — AVANT toute lecture des vraies données
# --------------------------------------------------------------------------

def martingale_check(r_null: int, n_draws: int = N, seed: int = 0) -> dict:
    """E[e_t] ~= 1 à plusieurs t, par famille et pour le portefeuille, sous
    H0. C'est le point qui décide de tout : un e-processus dont l'espérance
    dérive n'en est pas un. Renvoie aussi les échantillons du max (pour la
    calibration du seuil de puissance, §6) et les événements Ville."""
    rng = np.random.default_rng(seed)
    T = n_draws - 1
    checkpoints = sorted(set(list(CHECKPOINTS_SMALL) +
                            [int(round(f * (T - 1))) for f in CHECKPOINTS_FRAC]))
    names = list(FAMILIES) + ["PORTEFEUILLE"]
    vals_at_cp = {nm: {cp: [] for cp in checkpoints} for nm in names}
    max_samples = {nm: np.empty(r_null) for nm in names}

    t0 = time.time()
    for r in range(r_null):
        mask, bonus = srs_with_bonus(n_draws, rng)
        X = extract_X(mask, bonus)
        port_e, fam_e = portfolio_trajectory(X)
        for nm, traj in list(fam_e.items()) + [("PORTEFEUILLE", port_e)]:
            for cp in checkpoints:
                vals_at_cp[nm][cp].append(traj[cp])
            max_samples[nm][r] = traj.max()
        if (r + 1) % max(1, r_null // 5) == 0:
            print(f"  martingale check {r + 1}/{r_null}  ({time.time() - t0:.0f}s)", flush=True)

    return dict(checkpoints=checkpoints, vals_at_cp=vals_at_cp, max_samples=max_samples, T=T)


def report_exact_unit_check() -> None:
    """Vérification de PREMIER ORDRE : E_H0[facteur_t]=1, intégré EXACTEMENT
    sur la loi connue, theta par theta, famille par famille. Aucune
    simulation ici -- un bug de signe ou de m(theta) mal calculé se voit
    directement, à la précision flottante près."""
    print("\nVérification EXACTE (intégration sur la loi H0 connue, pas de simulation) :")
    print(f"  {'famille':<16}{'max |E[facteur_t]-1| sur theta':>34}")
    worst = 0.0
    for name, fam in FAMILIES.items():
        dev = np.max(np.abs(fam.exact_step_expectation() - 1.0))
        worst = max(worst, dev)
        print(f"  {name:<16}{dev:>34.2e}")
    ok = worst < 1e-9
    print(f"  -> {'OK' if ok else 'ÉCHEC'} : chaque facteur multiplicatif a une espérance "
          f"EXACTEMENT 1 sous H0 (écart max {worst:.2e}, précision flottante). C'est la "
          "propriété qui rend chaque famille une vraie martingale à CHAQUE pas.")
    assert ok, "un facteur n'a pas espérance 1 -- ARRÊT avant toute lecture des vraies données"


def report_martingale_check(chk: dict) -> None:
    checkpoints, vals, T = chk["checkpoints"], chk["vals_at_cp"], chk["T"]
    names = list(FAMILIES) + ["PORTEFEUILLE"]
    small = [cp for cp in checkpoints if cp in CHECKPOINTS_SMALL]
    large = [cp for cp in checkpoints if cp not in CHECKPOINTS_SMALL]

    print("\nE[e_t] sous H0 PAR SIMULATION, à PETIT t (l'estimateur y est encore bien posé --")
    print("doit valoir 1 dans le bruit d'échantillonnage ; sinon la martingale dérive, et")
    print("c'est un bug, pas une curiosité statistique) :")
    header = f"  {'famille':<16}" + "".join(f"{'t=' + str(cp):>14}" for cp in small)
    print(header)
    for nm in names:
        row = f"  {nm:<16}"
        for cp in small:
            v = np.asarray(vals[nm][cp])
            m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
            row += f"{m:>8.3f}±{se:<4.3f}"
        print(row)

    print(f"\nE[e_t] par simulation, à GRAND t (R={len(vals['PORTEFEUILLE'][large[0]])}) --")
    print("PAS un test de validité : un martingale non-négatif d'espérance EXACTEMENT 1 (déjà")
    print("prouvé ci-dessus) est nécessairement à queue lourde (Jensen : E[log e_t] < 0 si e_t")
    print("n'est pas p.s. constant, donc e_t -> 0 p.s. tandis que E[e_t] reste figé à 1 -- la")
    print("masse qui tient la moyenne à 1 vit dans des excursions rares que R réplicats ne")
    print("croisent presque jamais). Une moyenne d'échantillon proche de 0 ici est ATTENDUE,")
    print("pas un signe de dérive :")
    header = f"  {'famille':<16}" + "".join(f"{'t=' + str(cp):>14}" for cp in large)
    print(header)
    for nm in names:
        row = f"  {nm:<16}"
        for cp in large:
            v = np.asarray(vals[nm][cp])
            m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
            row += f"{m:>8.3f}±{se:<4.3f}"
        print(row)

    print("\nInégalité de Ville, vérifiée empiriquement (P(max_t e_t >= 1/alpha) <= alpha) --")
    print("LE test qui importe à grand T : une proportion s'estime bien même quand la")
    print("moyenne ne s'estime plus :")
    print(f"  {'famille':<16}{'seuil 1/a=20':>14}{'1/a=100':>10}{'1/a=1000':>11}")
    r_null = len(chk["max_samples"]["PORTEFEUILLE"])
    for nm in names:
        mx = chk["max_samples"][nm]
        f20 = (mx >= 20).mean()
        f100 = (mx >= 100).mean()
        f1000 = (mx >= 1000).mean()
        print(f"  {nm:<16}{f20:>10.3f} (a=.05){f100:>10.3f}{f1000:>11.3f}   (R={r_null})")


# --------------------------------------------------------------------------
# 5. Portefeuille sur les vraies données
# --------------------------------------------------------------------------

def run_real(a: "lab.Archive") -> dict:
    X = extract_X(a.mask, a.bonus)
    port_e, fam_e = portfolio_trajectory(X)
    argmax = int(np.argmax(port_e))
    ts0 = a.ts[argmax + 1]
    date = time.strftime("%Y-%m-%d", time.gmtime(ts0))
    return dict(X=X, port_e=port_e, fam_e=fam_e, max_e=float(port_e.max()),
                argmax=argmax, date_argmax=date, final_e=float(port_e[-1]))


# --------------------------------------------------------------------------
# 6. Puissance — MÊMES contaminations que a3 (importées), comparaison loyale
# --------------------------------------------------------------------------

def portfolio_max_with_bonus(mask: np.ndarray, rng: np.random.Generator) -> float:
    """bonus généré APRÈS contamination du mask (uniforme parmi les 20 de
    CHAQUE tirage, contaminé ou non — cohérent avec le null de d7_bonus)."""
    nums = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
    pick = rng.integers(0, DRAWN, size=len(mask))
    bonus = nums[np.arange(len(mask)), pick]
    port_e, _ = portfolio_trajectory(extract_X(mask, bonus))
    return float(port_e.max())


def make_contaminate_bonus_echo(L: int, target_p: float):
    """Fenêtre où P(bonus_t dans tirage t+1) est forcée à `target_p` par
    construction directe (pas de rejet) : bonus_{t-1} est inséré/retiré du
    tirage t selon un tirage à pile ou face de paramètre target_p. Teste
    spécifiquement `bonus_echo`, l'analogue transitoire de V3."""
    def contaminate(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        nums0 = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
        pick0 = rng.integers(0, DRAWN, size=len(mask))
        bonus0 = nums0[np.arange(len(mask)), pick0]
        start = int(rng.integers(1, len(mask) - L))
        for t in range(start, start + L):
            b = int(bonus0[t - 1]) - 1
            row = mask[t]
            present = bool(row[b])
            want = rng.random() < target_p
            if want and not present:
                present_idx = np.flatnonzero(row)
                drop = rng.choice(present_idx)
                row[drop] = False
                row[b] = True
            elif not want and present:
                absent_idx = np.flatnonzero(~row)
                add = rng.choice(absent_idx)
                row[b] = False
                row[add] = True
        return mask
    return contaminate


def power_grid_freq(threshold: float, r_power: int) -> dict:
    """Table de détectabilité, biais de fréquence — EXACTEMENT la
    contamination de a3 (`weighted_srs` + `calibrate_gamma`), pour être
    comparable case par case à la 16e voie (RAPPORT §2)."""
    gammas = {d: a3.calibrate_gamma(d) for d in a3.POWER_DELTA}
    out = {}
    for L in a3.POWER_L:
        for d in a3.POWER_DELTA:
            contaminate = a3.make_contaminate_freq(L, gammas[d][0])
            rng = np.random.default_rng(500_000 + 100 * L + int(d * 100))
            hit = 0
            for _ in range(r_power):
                mask = lab.srs(N, rng)
                mask = contaminate(mask, rng)
                if portfolio_max_with_bonus(mask, rng) >= threshold:
                    hit += 1
            out[(L, d)] = hit / r_power
    return out, gammas


def power_repeat(threshold: float, r_power: int) -> dict:
    """Défaut secondaire de a3 : recouvrement lag-1 forcé à j (E_H0=5).
    Cible directement `lag1_overlap`."""
    out = {}
    for L, j in a3.REPEAT_POINTS:
        contaminate = a3.make_contaminate_repeat(L, j)
        rng = np.random.default_rng(600_000 + 10 * L + j)
        hit = 0
        for _ in range(r_power):
            mask = lab.srs(N, rng)
            mask = contaminate(mask, rng)
            if portfolio_max_with_bonus(mask, rng) >= threshold:
                hit += 1
        out[(L, j)] = hit / r_power
    return out


def power_bonus_echo(threshold: float, r_power: int) -> dict:
    """Point illustratif : `bonus_echo` seul, cible directe de V3 rendu
    transitoire. target_p sous 0,25 (déficit, comme V3 observé)."""
    out = {}
    for L in (500, 2000):
        for target_p in (0.20, 0.10):
            contaminate = make_contaminate_bonus_echo(L, target_p)
            rng = np.random.default_rng(700_000 + 10 * L + int(target_p * 100))
            hit = 0
            for _ in range(r_power):
                mask = lab.srs(N, rng)
                mask = contaminate(mask, rng)
                if portfolio_max_with_bonus(mask, rng) >= threshold:
                    hit += 1
            out[(L, target_p)] = hit / r_power
    return out


def power_repeat_by_position(threshold: float, r_power: int) -> dict:
    """DIAGNOSTIC DÉCISIF : le même défaut (L=500, overlap forcé j=7) placé
    TÔT vs TARD dans l'archive. Un portefeuille SANS RESET est une
    martingale non-négative unique, cumulée depuis le pas 1 : sous H0 elle
    décroit p.s. vers 0 (cf. §1). Si le défaut tombe tard, le pari doit
    d'abord "remonter" depuis une richesse déjà proche de 0 avant même de
    commencer à accumuler la preuve locale -- un désavantage qu'un balayage
    par fenêtres (a3), qui réévalue une statistique FRAÎCHE à chaque
    position, n'a pas. C'est la réponse à "voit-il ce que les lots
    diluent, et réciproquement" : la dilution existe, mais côté portefeuille,
    et elle dépend de LA POSITION, pas seulement de l'amplitude."""
    out = {}
    L, j = 500, 7
    contaminate_early = a3.make_contaminate_repeat(L, j)
    windows = {"tôt (t in [1,5000])": (1, 5000),
              "tard (t in [50000,N-L])": (50000, N - L)}
    for label, (lo, hi) in windows.items():
        def contaminate(mask, rng, lo=lo, hi=hi):
            start = int(rng.integers(lo, hi))
            for t in range(start, start + L):
                prev = np.flatnonzero(mask[t - 1])
                keep = rng.choice(prev, size=j, replace=False)
                other = np.setdiff1d(np.arange(POOL), prev, assume_unique=True)
                new = np.concatenate([keep, rng.choice(other, size=DRAWN - j, replace=False)])
                mask[t] = False
                mask[t, new] = True
            return mask
        rng = np.random.default_rng(800_000 + hash(label) % 10_000)
        hit = 0
        for _ in range(r_power):
            mask = lab.srs(N, rng)
            mask = contaminate(mask, rng)
            if portfolio_max_with_bonus(mask, rng) >= threshold:
                hit += 1
        out[label] = hit / r_power
    return out


# --------------------------------------------------------------------------
# 7. Orchestration
# --------------------------------------------------------------------------

def main() -> None:
    t_start = time.time()
    print("=" * 78)
    print("F2 — PORTEFEUILLE D'E-PROCESSUS (mode:", "FAST" if FAST else "complet", ")")
    print("=" * 78)

    print("\n0. Auto-vérification de la loi exacte de la somme (sum_pmf)")
    _self_check_sum_pmf()
    for name, fam in FAMILIES.items():
        print(f"  {name:<16} mu={fam.mu:9.3f}  sd={fam.sd:7.3f}  "
              f"log_m finis: {np.all(np.isfinite(fam.log_m))}")

    # -- 1. Pré-enregistrement : AVANT tout regard sur le résultat ---------
    tok = lab.preregister(
        EXP_ID,
        hypothese := ("Un portefeuille de 4 e-processus (mélange de martingales à inclinaison "
                      "exponentielle theta in +-{.05,.10,.20,.40}, un par famille : recouvrement "
                      "lag-1, bonus_t dans tirage t+1 (V3), somme des 20 numéros, forme/dispersion "
                      "du recouvrement) atteint un maximum anormal sur la marche avant des 70 559 "
                      "pas de l'archive réelle"),
        statistic="max_t E_t du portefeuille (moyenne linéaire des 4 e-processus de famille)",
        null_method=(f"loi du max simulée sur R={R_NULL} archives SRS complètes "
                     "(mask + bonus uniforme parmi les 20 du même tirage, cf. d7_bonus.synth), "
                     "jamais tabulée ; la validité de la martingale (E[e_t]=1) est vérifiée "
                     "empiriquement par la même simulation AVANT toute lecture des vraies données"),
        decision=(f"anomalie candidate si p empirique (Davison-Hinkley) du max <= plancher "
                  f"1/(R_NULL+1)={1/(R_NULL+1):.2e} ; sinon conforme. Diagnostic par famille "
                  "rapporté mais PAS la décision enregistrée (comme a3) ; seuil final = Holm "
                  "registre ~1,5e-05"),
        track="A",
    )
    print(f"\npré-enregistré  id={tok['id']}  seal={tok['seal']}")

    # -- 2. Vérification de la martingale -----------------------------------
    print(f"\n{'-'*78}\n1. VÉRIFICATION DE LA MARTINGALE (AVANT toute donnée réelle)")
    report_exact_unit_check()
    print(f"\nSimulation (R={R_NULL} archives H0 complètes) :")
    chk = martingale_check(R_NULL, N, seed=0)
    report_martingale_check(chk)
    port_max_null = chk["max_samples"]["PORTEFEUILLE"]
    floor_thr = float(port_max_null.max())
    p_floor = 1 / (R_NULL + 1)
    print(f"\nplancher empirique du max (portefeuille, R={R_NULL}) : {floor_thr:.2f}  "
          f"(p plancher {p_floor:.2e})")

    # -- 3. Portefeuille sur les vraies données ------------------------------
    print(f"\n{'-'*78}\n2. LE PORTEFEUILLE SUR LES 70 560 VRAIS TIRAGES")
    a = lab.load()
    assert len(a) == N
    real = run_real(a)
    print(f"trajectoire : T={len(real['port_e'])} pas")
    print(f"max_t E_t du portefeuille = {real['max_e']:.4f}  "
          f"(atteint au pas {real['argmax']}, ~{real['date_argmax']})")
    print(f"E_t final (fin d'archive) = {real['final_e']:.6f}")
    print("\npar famille (max sur la trajectoire, diagnostic — pas la décision enregistrée) :")
    for name, fam in FAMILIES.items():
        e = real["fam_e"][name]
        print(f"  {name:<16} max={e.max():10.4f}  final={e[-1]:.6f}  "
              f"argmax_t={int(np.argmax(e)):>6}")

    # null empirique -> p, z (comme lab.Null, construit à la main car le stat
    # dépend aussi du bonus, que lab.calibrate() ne fournit pas à `stat(mask)`)
    null_obj = lab.Null(mean=float(port_max_null.mean()), sd=float(port_max_null.std(ddof=1)),
                        reps=R_NULL, samples=port_max_null)
    p_emp = null_obj.p_two_sided(real["max_e"])
    z_vs_null = null_obj.z(real["max_e"])
    p_ville = min(1.0, 1.0 / real["max_e"])
    print(f"\np empirique (Davison-Hinkley, vs loi simulée du max) = {p_emp:.4f}   "
          f"z = {z_vs_null:+.2f}")
    print(f"p de Ville (min(1, 1/max E_t), valide à tout instant d'arrêt, sans simulation) "
          f"= {p_ville:.4f}")
    verdict = "conforme" if p_emp > p_floor else "candidate — recalibrer"
    print(f"VERDICT : {verdict}")

    # -- 4. Comparaison qualitative aux résultats par lots -------------------
    print(f"\n{'-'*78}\n3. COMPARAISON AUX RÉSULTATS PAR LOTS (RAPPORT.md §2)")
    print("  lag1_overlap   (bat.) c1 T1 réel = 5,00191  z=+0,30      -- attendu : null ici aussi")
    print("  bonus_echo     (bat.) d7  V3 réel z=-2,58  p=0,010 (non signif. Holm)")
    print("  sum_marginal   (bat.) a3 'sum' fait partie du balayage multi-échelle, max|z|=5,24 p=0,066")
    print("  overlap_shape  (bat.) d3  S1 z=+3,47 p=0,010, PAS répliqué "
          "(variance seule : z=+0,95, RAPPORT l.240)")
    print(f"  portefeuille F2 : max E_t={real['max_e']:.2f}  p_emp={p_emp:.4f}  p_Ville={p_ville:.4f}")

    # Réciproque : le portefeuille voit-il quelque chose LÀ où a3 a placé
    # son propre maximum (chi2 W=200 @tirage 58340, RAPPORT §2, p=0,066) ?
    a3_hot_lo = 58340 - 1
    a3_hot_hi = a3_hot_lo + 200
    if a3_hot_hi <= len(real["port_e"]):
        e_there = real["port_e"][a3_hot_lo:a3_hot_hi].max()
        print(f"  au hotspot de a3 (tirage 58340, chi2 W=200, non-signif. p=0,066) : "
              f"max E_t portefeuille sur cette fenêtre = {e_there:.3e} -- portefeuille aveugle "
              "ici (chi2 champ omnidirectionnel n'est pas un des 4 paris, ET la richesse y est "
              "déjà quasi nulle, cf. §5)")

    # -- 5. Puissance ----------------------------------------------------
    print(f"\n{'-'*78}\n4. PUISSANCE — mêmes contaminations que a3 (R_power={R_POWER}/point), "
          f"seuil = plancher empirique {floor_thr:.2f} (p={p_floor:.2e})")
    t0 = time.time()
    freq_pw, gammas = power_grid_freq(floor_thr, R_POWER)
    print(f"  biais fréquence (8 numéros favorisés) : {time.time()-t0:.0f}s")
    header = "  L \\ delta |" + "".join(f" {d*100:5.0f} % |" for d in a3.POWER_DELTA)
    print(header)
    for L in a3.POWER_L:
        row = f"  {L:>9} |"
        for d in a3.POWER_DELTA:
            row += f"  {freq_pw[(L, d)]:5.2f} |"
        print(row)
    print("  (a3, même grille, RAPPORT §2 / README) :")
    print("    200  | 0.00 | 0.00 | 0.00 | 0.58 |")
    print("    500  | 0.00 | 0.00 | 0.28 | 1.00 |")
    print("    2000 | 0.00 | 0.10 | 1.00 | 1.00 |")

    t0 = time.time()
    rep_pw = power_repeat(floor_thr, R_POWER)
    print(f"\n  défaut secondaire (recouvrement lag-1 forcé, cible directe de lag1_overlap) : "
          f"{time.time()-t0:.0f}s")
    for (L, j), pw in rep_pw.items():
        print(f"  L={L}, overlap forcé j={j} (+{(j-5)/5*100:.0f} %) : puissance F2 = {pw:.2f}")

    t0 = time.time()
    be_pw = power_bonus_echo(floor_thr, R_POWER)
    print(f"\n  bonus_echo transitoire (illustratif, cible directe de V3) : {time.time()-t0:.0f}s")
    for (L, tp), pw in be_pw.items():
        print(f"  L={L}, P(bonus_t in t+1) forcée à {tp:.2f} (H0=0,25) : puissance F2 = {pw:.2f}")

    # -- 5 bis. LE mécanisme : la position du défaut, pas seulement son amplitude
    print(f"\n{'-'*78}\n5. POURQUOI L'ÉCART DE PUISSANCE — même défaut, position tôt vs tard")
    print("  a3 (RAPPORT §2, registre) : L=500, j=6 -> puissance 1,00 ; j=7 -> puissance 1,00")
    print(f"  F2 ci-dessus (position ALÉATOIRE, comme a3) : j=6 -> {rep_pw[(500,6)]:.2f} ; "
          f"j=7 -> {rep_pw[(500,7)]:.2f}")
    t0 = time.time()
    pos_pw = power_repeat_by_position(floor_thr, R_POWER)
    print(f"  MÊME défaut (L=500, j=7), position contrôlée ({time.time()-t0:.0f}s) :")
    for label, pw in pos_pw.items():
        print(f"    {label:<28} puissance F2 = {pw:.2f}")
    print("  -> le portefeuille est une SEULE martingale cumulée depuis le pas 1 : sous H0 elle")
    print("     décroît p.s. vers 0 (§1). Un défaut TARD doit d'abord regagner cette richesse")
    print("     perdue avant d'accumuler la preuve locale ; un défaut TÔT n'a rien à regagner.")
    print("     a3 réévalue une statistique FRAÎCHE à chaque position de fenêtre : aucun passif.")

    # -- 6. Verdict et registre -------------------------------------------
    notes = (f"max_e={real['max_e']:.4f} @pas {real['argmax']} ({real['date_argmax']}); "
             f"p_Ville={p_ville:.4f}; floor={floor_thr:.2f} (R_NULL={R_NULL}); "
             f"freq_power={freq_pw}; repeat_power={rep_pw}; bonus_echo_power={be_pw}; "
             f"position_mechanism(L=500,j=7)={pos_pw}; "
             f"a3_hotspot_e={e_there if a3_hot_hi <= len(real['port_e']) else None}; "
             f"R_power={R_POWER}")
    print(f"\n{'-'*78}\nVERDICT FINAL : {verdict}  (max E_t={real['max_e']:.2f}, "
          f"p_emp={p_emp:.4f}, plancher {p_floor:.2e})")
    if NO_RECORD:
        print("(--fast/--no-record : rien n'est écrit au registre)")
    elif any(r.get("id") == EXP_ID for r in lab.ledger()):
        print(f"registre : entrée '{EXP_ID}' déjà présente — pas de doublon écrit")
    else:
        lab.record(tok, observed=real["max_e"], null=null_obj, power_at=str(freq_pw),
                   verdict=verdict, notes=notes)
        print(f"registre : consigné sous '{EXP_ID}'")

    print(f"\ntotal : {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
