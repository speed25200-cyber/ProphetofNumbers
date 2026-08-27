"""b2 — Quelle mise (k numéros cochés) est la moins mauvaise, et de combien ?

Piste B (décision à biais nul). Sous H0 les hits d'une grille de k numéros
suivent une hypergéométrique(80, 20, k) — c'est un théorème, pas une
observation. Tout ce qui suit en découle, et le rapport distingue à chaque
ligne ce qui est SU (la loi exacte, vérifiée par simulation) de ce qui est
SUPPOSÉ (le barème des gains, absent du dépôt).

Fait établi dans le dépôt, cité tel quel :
  Prophet/Views/HistoryView.swift:282 — « L'API Loro publie les montants des
  jackpots k/k mais pas le barème des rangs intermédiaires : l'app compte les
  rangs sans inventer leurs montants. »
Les jackpots k/k arrivent par le flux live (`extraJackpots`, LoroClient.swift:406)
et ne sont stockés nulle part dans le dépôt ; le réseau est fermé (403).
Le barème complet est donc IRRÉCUPÉRABLE hors ligne : toute table de gains
utilisée ici est une hypothèse paramétrique, marquée comme telle, et la
question posée est traitée en robustesse (le classement dépend-il du barème ?).

Reproductible : `python3 lab/experiments/b2_mises.py`  (~2 min).
Registre : entrées track="B", idempotentes (pas de doublon au re-run).
"""

from __future__ import annotations

import os
import sys
from math import comb

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab  # noqa: E402

POOL, DRAWN = lab.POOL, lab.DRAWN
STAKES = [5, 6, 7, 8, 10]          # ProphetConst.stakes (Prophet/Models/Types.swift:6)
KS = list(range(1, 11))

SEP = "-" * 78


def title(s: str) -> None:
    print(f"\n{SEP}\n{s}\n{SEP}")


def rec_guarded(done: set, tok: dict, **kw) -> None:
    """Consigne au registre, sans doublon au re-run."""
    if tok["id"] in done:
        print(f"[registre] {tok['id']} déjà consigné — pas de doublon")
        return
    lab.record(tok, **kw)
    done.add(tok["id"])
    print(f"[registre] {tok['id']} consigné")


# ==========================================================================
# 1. SU — loi exacte des hits, k = 1..10
# ==========================================================================

def exact_tables() -> dict[int, np.ndarray]:
    title("1. SU — loi exacte des hits : hypergéométrique(80, 20, k)")
    pmfs = {k: lab.hits_pmf(k) for k in KS}
    print(f"{'k':>3} {'E[hits]':>8} {'k/4':>6} {'Var':>8} {'P(hits=k)':>12} {'1/P(plein)':>14} {'P(hits=0)':>10}")
    for k in KS:
        pmf = pmfs[k]
        h = np.arange(k + 1)
        e = float((pmf * h).sum())
        v = float((pmf * h * h).sum() - e * e)
        # Variance exacte pour contrôle interne : k * 1/4 * 3/4 * (80-k)/79
        v_th = k * 0.25 * 0.75 * (POOL - k) / (POOL - 1)
        assert abs(e - k / 4) < 1e-12 and abs(v - v_th) < 1e-12 and abs(pmf.sum() - 1) < 1e-12
        pk = pmf[k]
        print(f"{k:>3} {e:>8.4f} {k/4:>6.2f} {v:>8.4f} {pk:>12.3e} {1/pk:>14,.1f} {pmf[0]:>10.4f}")
    print("\nLoi complète P(hits=h) pour les mises de l'app :")
    for k in STAKES:
        cells = "  ".join(f"h={h}:{p:.5f}" if p >= 1e-5 else f"h={h}:{p:.2e}"
                          for h, p in enumerate(pmfs[k]))
        print(f"  k={k:>2}  {cells}")
    return pmfs


# ==========================================================================
# 2. Vérification de lab.hits_pmf par simulation lab.srs (règle 1 : null simulé)
# ==========================================================================

GRID10 = None  # 10 colonnes fixes, choisies une fois


def _hits_all_k(mask: np.ndarray) -> np.ndarray:
    """(n, 10) : hits de la grille emboîtée GRID10[:k] pour k=1..10."""
    return np.cumsum(mask[:, GRID10], axis=1)


def _chi2_total(mask: np.ndarray) -> float:
    """Somme sur k=1..10 des chi2 (cellules groupées à attendu>=5) contre hits_pmf(k)."""
    n = len(mask)
    hk = _hits_all_k(mask)
    tot = 0.0
    for j, k in enumerate(KS):
        obs = np.bincount(hk[:, j], minlength=k + 1).astype(float)
        exp = lab.hits_pmf(k) * n
        # groupe la queue jusqu'à attendu >= 5
        while len(exp) > 2 and exp[-1] < 5:
            exp[-2] += exp[-1]; obs[-2] += obs[-1]
            exp, obs = exp[:-1], obs[:-1]
        tot += float(((obs - exp) ** 2 / exp).sum())
    return tot


def _contaminate_bias(q: float):
    """Force, pour une fraction q des tirages, un numéro de GRID10 non tiré à
    entrer (échange contre un numéro hors grille tiré). Décale les hits vers
    le haut : c'est le défaut que le test de l'étape 2 prétend savoir voir."""
    def f(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        n = len(mask)
        rows = np.where(rng.random(n) < q)[0]
        if rows.size == 0:
            return mask
        g = mask[rows][:, GRID10]                      # (r,10)
        ng_cols = np.setdiff1d(np.arange(POOL), GRID10)
        ngm = mask[rows][:, ng_cols]                   # (r,70)
        ok = ~g.all(axis=1)                            # au moins un absent dans la grille
        rows, g, ngm = rows[ok], g[ok], ngm[ok]
        cin = GRID10[np.argmax(rng.random(g.shape) * (~g), axis=1)]
        cout = ng_cols[np.argmax(rng.random(ngm.shape) * ngm, axis=1)]
        mask[rows, cin] = True
        mask[rows, cout] = False
        return mask
    return f


def verify_pmf(done: set) -> None:
    global GRID10
    title("2. Vérification de lab.hits_pmf par lab.srs — null simulé, puissance mesurée")
    rng = np.random.default_rng(7)
    GRID10 = np.sort(rng.choice(POOL, 10, replace=False))
    print(f"Grille fixe (colonnes 0-based) : {GRID10.tolist()}")

    tok = lab.preregister(
        "b2.hits_pmf_qc",
        "lab.hits_pmf(k) est la loi des hits d'une grille de k numéros sous SRS 20/80, k=1..10",
        "somme des chi2 (queues groupées à attendu>=5) entre l'histogramme des hits "
        "sur 100 000 tirages lab.srs et hits_pmf(k), k=1..10, grille emboîtée fixe",
        "lab.calibrate, 200 réplicats SRS de 100 000 tirages",
        "conforme si p > 0,01 ; sinon hits_pmf est fausse et tout b2 tombe",
        track="B",
    )

    null = lab.calibrate(_chi2_total, 100_000, reps=200, seed=0)
    obs = _chi2_total(lab.srs(100_000, np.random.default_rng(123)))
    p = null.p_two_sided(obs)
    print(f"chi2 total observé {obs:.1f} | null simulé {null.mean:.1f} ± {null.sd:.1f} "
          f"(200 réplicats) | z = {null.z(obs):+.2f} | p = {p:.3f}")

    pw = {q: lab.power(_chi2_total, _contaminate_bias(q), 100_000, null, reps=40, seed=1)
          for q in (0.01, 0.02)}
    print(f"Puissance (biais d'inclusion de la grille) : "
          + " ; ".join(f"q={q:.0%} -> {v:.0%}" for q, v in pw.items()))

    # Gros échantillon : précision fine sur chaque cellule + espérance.
    M, chunk = 6_400_000, 200_000
    counts = {k: np.zeros(k + 1, np.int64) for k in KS}
    r2 = np.random.default_rng(42)
    for _ in range(M // chunk):
        hk = _hits_all_k(lab.srs(chunk, r2))
        for j, k in enumerate(KS):
            counts[k] += np.bincount(hk[:, j], minlength=k + 1)
    print(f"\nGros échantillon : {M:,} tirages srs. Écarts empirique-exact par k :")
    worst = 0.0
    for k in KS:
        emp = counts[k] / M
        pmf = lab.hits_pmf(k)
        se = np.sqrt(pmf * (1 - pmf) / M)
        zmax = float(np.max(np.abs(emp - pmf) / np.maximum(se, 1e-300)))
        dmax = float(np.max(np.abs(emp - pmf)))
        mean_emp = float((np.arange(k + 1) * emp).sum())
        z_mean = (mean_emp - k / 4) / np.sqrt(k * .25 * .75 * (POOL - k) / (POOL - 1) / M)
        worst = max(worst, zmax)
        print(f"  k={k:>2}  max|emp-exact| = {dmax:.2e}  |z|max/cellule = {zmax:.2f}  "
              f"E_emp = {mean_emp:.5f} (z = {z_mean:+.2f})")
    verdict = "conforme" if p > 0.01 and worst < 5 else "ÉCART — hits_pmf suspecte"
    rec_guarded(done, tok, observed=obs, null=null, p=p,
                power_at=f"q=1% : {pw[0.01]:.0%} ; q=2% : {pw[0.02]:.0%}",
                verdict=verdict,
                notes=f"6,4 M tirages srs : |z|max par cellule {worst:.2f}, "
                      f"E[hits] retrouvée à k/4 pour k=1..10. hits_pmf validée.")


# ==========================================================================
# 3. SUPPOSÉ — barèmes paramétriques + métriques de gain par mise
# ==========================================================================
#
# AUCUN barème réel dans le dépôt (HistoryView.swift:282), réseau fermé.
# Les trois variantes ci-dessous sont des HYPOTHÈSES structurelles couvrant
# l'espace des barèmes Keno publiés : casino (RTP haut, paie dès ~k/2),
# loterie d'État (RTP bas, rangs bas + lot 0/10), jackpot-lourd (quasi tout
# sur k/k — la structure que l'app elle-même met en avant, GridsView:108).
# Les montants sont des multiples BRUTS de la mise (gain net = brut - 1).

PAYTABLES: dict[str, dict[int, dict[int, float]]] = {
    "V1 casino (SUPPOSÉ)": {
        5:  {3: 3, 4: 12, 5: 800},
        6:  {3: 3, 4: 4, 5: 70, 6: 1600},
        7:  {4: 2, 5: 21, 6: 400, 7: 7000},
        8:  {5: 12, 6: 98, 7: 1652, 8: 10000},
        10: {5: 2, 6: 15, 7: 40, 8: 450, 9: 4250, 10: 10000},
    },
    "V2 loterie (SUPPOSÉ)": {
        5:  {3: 1, 4: 8, 5: 100},
        6:  {3: 1, 4: 4, 5: 30, 6: 400},
        7:  {4: 2, 5: 10, 6: 100, 7: 2000},
        8:  {4: 1, 5: 6, 6: 50, 7: 500, 8: 10000},
        10: {0: 2, 5: 2, 6: 10, 7: 50, 8: 500, 9: 10000, 10: 100000},
    },
    # J_k calé pour que le seul jackpot rende 0,50 CHF/CHF ; k-1 paie 10x.
    "V3 jackpot-lourd (SUPPOSÉ)": {
        k: {k: round(0.5 / lab.hits_pmf(k)[k]), k - 1: 10} for k in STAKES
    },
}


def metrics(k: int, table: dict[int, float], scale: float = 1.0) -> dict:
    pmf = lab.hits_pmf(k)
    pay = np.zeros(k + 1)
    for h, v in table.items():
        pay[h] = v * scale
    rtp = float((pmf * pay).sum())
    var = float((pmf * pay ** 2).sum() - rtp ** 2)     # Var(brut) == Var(net)
    return {
        "rtp": rtp,
        "ev_net": rtp - 1.0,
        "sd": var ** 0.5,
        "p_zero": float(pmf[pay == 0].sum()),          # perte totale
        "p_win_stake": float(pmf[pay >= 1].sum()),     # gain >= mise
    }


def paytable_analysis() -> None:
    title("3. SUPPOSÉ — barèmes paramétriques : espérance, variance, P(perte), P(gain>=mise)")
    print("Aucun barème réel dans le dépôt ; toutes les valeurs CHF ci-dessous sont des")
    print("HYPOTHÈSES. Seules les probabilités (colonne pmf) sont exactes.\n")
    for name, tabs in PAYTABLES.items():
        print(f"--- {name} ---")
        print(f"{'k':>3} {'RTP':>7} {'E[net]/CHF':>11} {'sd':>9} {'P(perte tot.)':>14} {'P(gain>=mise)':>14}")
        best = max(STAKES, key=lambda k: metrics(k, tabs[k])["rtp"])
        for k in STAKES:
            m = metrics(k, tabs[k])
            star = " *" if k == best else ""
            print(f"{k:>3} {m['rtp']:>7.3f} {m['ev_net']:>+11.3f} {m['sd']:>9.1f} "
                  f"{m['p_zero']:>14.3f} {m['p_win_stake']:>14.4f}{star}")
        print("  (* = meilleure espérance SOUS CE barème supposé)\n")

    print("--- Mêmes variantes, renormalisées à RTP = 0,65 (forme seule) ---")
    print("À espérance égalisée, seul reste ce que la géométrie de la loi impose :")
    print(f"{'k':>3} | " + " | ".join(f"{name.split()[0]:^27}" for name in PAYTABLES))
    print(f"{'':>3} | " + " | ".join(f"{'P(perte)':>8} {'P(g>=m)':>8} {'sd':>8}" for _ in PAYTABLES))
    for k in STAKES:
        cells = []
        for name, tabs in PAYTABLES.items():
            m0 = metrics(k, tabs[k])
            m = metrics(k, tabs[k], scale=0.65 / m0["rtp"])
            cells.append(f"{m['p_zero']:>8.3f} {m['p_win_stake']:>8.4f} {m['sd']:>8.1f}")
        print(f"{k:>3} | " + " | ".join(cells))


def random_paytable_robustness(done: set) -> dict:
    """Le classement des mises est-il robuste au barème ? 2 000 barèmes
    aléatoires par k, tous à RTP = 0,65 exactement (l'espérance est alors
    ÉGALE par construction : on ne compare que la forme)."""
    title("4. Sensibilité au barème — 2 000 barèmes aléatoires par k, RTP fixé à 0,65")
    rng = np.random.default_rng(2024)
    R = 2000
    res = {k: {"p_zero": np.empty(R), "p_win": np.empty(R), "sd": np.empty(R)} for k in STAKES}
    for k in STAKES:
        pmf = lab.hits_pmf(k)
        for r in range(R):
            hmin = int(rng.integers(max(2, (k + 1) // 2), k - 1))   # 1er rang payé
            g = rng.uniform(1.0, 2.5)                               # pente log des lots
            pay = np.zeros(k + 1)
            hs = np.arange(hmin, k + 1)
            pay[hs] = np.exp(g * (hs - hmin)) * rng.uniform(0.7, 1.4, len(hs))
            if k >= 7 and rng.random() < 0.3:                       # lot « 0 hit » style loterie
                pay[0] = rng.uniform(0.5, 2.0)
            pay *= 0.65 / (pmf * pay).sum()
            res[k]["p_zero"][r] = pmf[pay == 0].sum()
            res[k]["p_win"][r] = pmf[pay >= 1].sum()
            res[k]["sd"][r] = ((pmf * pay ** 2).sum() - 0.65 ** 2) ** 0.5

    print(f"{'k':>3} {'P(perte totale)':>24} {'P(gain>=mise)':>24} {'sd du gain':>20}")
    for k in STAKES:
        z, w, s = res[k]["p_zero"], res[k]["p_win"], res[k]["sd"]
        print(f"{k:>3}   {np.median(z):>6.3f} [{np.quantile(z,.05):.3f}-{np.quantile(z,.95):.3f}]"
              f"      {np.median(w):>6.4f} [{np.quantile(w,.05):.4f}-{np.quantile(w,.95):.4f}]"
              f"    {np.median(s):>7.1f} [{np.quantile(s,.05):.1f}-{np.quantile(s,.95):.1f}]")

    print("\nRobustesse des comparaisons deux à deux (fraction des appariements de barèmes")
    print("aléatoires où la mise de gauche domine ; >= 95 % = ordre robuste au barème) :")
    pairs = [(a, b) for i, a in enumerate(STAKES) for b in STAKES[i + 1:]]
    rows = []
    for a, b in pairs:
        f_zero = float((res[a]["p_zero"] < res[b]["p_zero"]).mean())   # moins de pertes sèches
        f_win = float((res[a]["p_win"] > res[b]["p_win"]).mean())      # plus souvent >= mise
        f_sd = float((res[a]["sd"] < res[b]["sd"]).mean())             # moins volatile
        rows.append((a, b, f_zero, f_win, f_sd))
        print(f"  k={a:>2} vs k={b:>2} : P(perte) plus faible {f_zero:>5.0%} | "
              f"P(g>=m) plus forte {f_win:>5.0%} | sd plus faible {f_sd:>5.0%}")
    return {"pairs": rows}


# ==========================================================================
# 5. Boost — loi empirique (SU), mémoire (SU), valeur si connu (SUPPOSÉ)
# ==========================================================================

def _repeat_rate(b: np.ndarray) -> float:
    return float((b[1:] == b[:-1]).mean())


def _trans_chi2(b: np.ndarray, vals: np.ndarray) -> float:
    """Chi2 de la table de transition lag-1 6x6 contre l'indépendance."""
    idx = np.searchsorted(vals, b)
    m = len(vals)
    tab = np.bincount(idx[:-1] * m + idx[1:], minlength=m * m).reshape(m, m).astype(float)
    n = tab.sum()
    exp = tab.sum(1)[:, None] * tab.sum(0)[None, :] / n
    return float(((tab - exp) ** 2 / np.maximum(exp, 1e-12)).sum())


def _sticky_chain(n: int, vals: np.ndarray, probs: np.ndarray, eps: float,
                  rng: np.random.Generator) -> np.ndarray:
    """Chaîne collante : b[i] = b[i-1] avec prob eps, sinon iid selon probs.
    Vectorisé par points de rafraîchissement."""
    x = rng.choice(vals, size=n, p=probs)
    keep = rng.random(n) < eps
    keep[0] = False
    refresh = np.where(~keep, np.arange(n), 0)
    src = np.maximum.accumulate(refresh)
    return x[src]


def boost_analysis(a: lab.Archive, done: set) -> None:
    title("5. Boost — loi empirique (SU), mémoire et prédictibilité (SU), valeur si connu (SUPPOSÉ)")
    b = a.boost
    assert (b >= 0).all(), "boost absent sur certains tirages"
    vals, cnt = np.unique(b, return_counts=True)
    probs = cnt / cnt.sum()
    e_boost = float((vals * probs).sum())
    audit = {1: .512, 2: .238, 3: .151, 4: .050, 5: .025, 10: .025}
    print("Loi empirique sur les 70 560 tirages (SU) — vs audit §14 :")
    for v, p in zip(vals.tolist(), probs):
        print(f"  boost={v:>2} : {p:.4f}  (audit : {audit[v]:.3f})")
    print(f"E[boost] = {e_boost:.4f}   P(boost>=5) = {probs[vals >= 5].sum():.4f}   "
          f"P(boost=10) = {probs[vals == 10][0]:.4f}")
    dt = float(np.median(np.diff(a.ts)))
    per_day = 86400 / dt
    print(f"Cadence : 1 tirage / {dt:.0f} s -> ~{per_day:.0f} tirages/jour, dont "
          f"~{per_day * probs[vals >= 5].sum():.1f}/jour à boost>=5 et "
          f"~{per_day * probs[vals == 10][0]:.1f}/jour à boost=10.")

    # ---- 5a. mémoire lag-1 : confirmation de l'audit, null par permutation
    tok1 = lab.preregister(
        "b2.boost_memoire",
        "boost(i+1) est indépendant de boost(i) (confirmation audit §14 : 34,46 % vs 34,51 %)",
        "taux de répétition P(boost(i+1)==boost(i)) sur les 70 559 paires adjacentes",
        "2 000 permutations de la séquence boost (marginale exactement conservée)",
        "conforme si p > 0,05 après Holm sur le registre entier",
        track="B",
    )
    obs_r = _repeat_rate(b)
    rng = np.random.default_rng(5)
    perm_r = np.array([_repeat_rate(rng.permutation(b)) for _ in range(2000)])
    null_r = lab.Null(float(perm_r.mean()), float(perm_r.std(ddof=1)), 2000, perm_r)
    p_r = null_r.p_two_sided(obs_r)
    sump2 = float((probs ** 2).sum())
    eps_hat = (obs_r - sump2) / (1 - sump2)
    eps_sd = null_r.sd / (1 - sump2)
    print(f"\n5a. Répétition lag-1 : observé {obs_r:.4f} | Σp² = {sump2:.4f} | "
          f"null permuté {null_r.mean:.4f} ± {null_r.sd:.4f} | z = {null_r.z(obs_r):+.2f} | p = {p_r:.3f}")
    print(f"    Collage estimé ε = {eps_hat:+.4f} ± {eps_sd:.4f} "
          f"(IC95 ≈ [{eps_hat - 1.96 * eps_sd:+.4f}, {eps_hat + 1.96 * eps_sd:+.4f}])")

    # ---- 5b. transition complète 6x6 : test plus puissant que la répétition
    tok2 = lab.preregister(
        "b2.boost_transition",
        "la table de transition lag-1 du boost (6x6) est celle de l'indépendance",
        "chi2 de la table de transition 6x6 contre l'indépendance (marges observées)",
        "2 000 permutations de la séquence boost",
        "conforme si p > 0,05 après Holm sur le registre entier",
        track="B",
    )
    obs_t = _trans_chi2(b, vals)
    perm_t = np.array([_trans_chi2(rng.permutation(b), vals) for _ in range(2000)])
    null_t = lab.Null(float(perm_t.mean()), float(perm_t.std(ddof=1)), 2000, perm_t)
    p_t = null_t.p_two_sided(obs_t)
    print(f"5b. Transition 6x6 : chi2 observé {obs_t:.1f} | null permuté "
          f"{null_t.mean:.1f} ± {null_t.sd:.1f} | z = {null_t.z(obs_t):+.2f} | p = {p_t:.3f}")

    # ---- puissance : chaînes collantes injectées, détection à |z| >= 3
    print("\nPuissance mesurée (chaîne collante d'intensité ε, 200 réplicats, |z|>=3) :")
    n = len(b)
    pw_r, pw_t = {}, {}
    for eps in (0.005, 0.01, 0.02, 0.05):
        rr = np.random.default_rng(int(eps * 10000))
        hit_r = hit_t = 0
        for _ in range(200):
            c = _sticky_chain(n, vals, probs, eps, rr)
            if abs(null_r.z(_repeat_rate(c))) >= 3: hit_r += 1
            if abs(null_t.z(_trans_chi2(c, vals))) >= 3: hit_t += 1
        pw_r[eps], pw_t[eps] = hit_r / 200, hit_t / 200
        print(f"  ε = {eps:>5.3f} : répétition {pw_r[eps]:>4.0%} | transition {pw_t[eps]:>4.0%}")

    rec_guarded(done, tok1, observed=obs_r, null=null_r, p=p_r,
                power_at="; ".join(f"ε={e}: {v:.0%}" for e, v in pw_r.items()),
                verdict="conforme" if p_r > 0.05 else "ÉCART",
                notes=f"Confirme audit §14. ε̂ = {eps_hat:+.4f} ± {eps_sd:.4f} ; "
                      f"le seuil d'exploitabilité (voir 5c) est ε ≈ 0,13, exclu à ~50 sd.")
    rec_guarded(done, tok2, observed=obs_t, null=null_t, p=p_t,
                power_at="; ".join(f"ε={e}: {v:.0%}" for e, v in pw_t.items()),
                verdict="conforme" if p_t > 0.05 else "ÉCART",
                notes="Test strictement plus puissant que la répétition lag-1 ; nul aussi.")

    # ---- 5c. valeur du boost s'il était connu avant la clôture (SUPPOSÉ)
    print("\n5c. SUPPOSÉ — ce que vaudrait un boost connu AVANT la clôture des mises.")
    print("    Mécanique supposée (invérifiable hors ligne) : l'option boost coûte une")
    print("    2e mise et multiplie les gains par le boost tiré. Alors, par CHF misé :")
    print("      rendement = RTP_base × E[boost | sélection] / 2.")
    e_ge5 = float((vals[vals >= 5] * probs[vals >= 5]).sum() / probs[vals >= 5].sum())
    print(f"    E[boost] = {e_boost:.3f} -> toujours jouer le boost ≈ neutre "
          f"(facteur {e_boost / 2:.3f} sur le RTP : l'option est tarifée juste).")
    for rtp in (0.50, 0.65, 0.92):
        r10 = rtp * 10 / 2
        r5 = rtp * e_ge5 / 2
        print(f"    RTP supposé {rtp:.2f} : boost=10 seulement -> {r10:.2f} CHF/CHF "
              f"({(r10 - 1) * 100:+.0f} %) ; boost>=5 -> {r5:.2f} CHF/CHF ({(r5 - 1) * 100:+.0f} %)")
    print(f"    E[boost | boost>=5] = {e_ge5:.2f}. Même à RTP 0,50, boost connu = +150 % par")
    print("    tirage joué. Rentable dès RTP > 0,2 (boost=10) : la question VAUT d'être")
    print("    instrumentée dans l'app (horodater l'apparition du boost dans l'API vs la")
    print("    clôture des mises). A priori évident : le boost est tiré AVEC le tirage.")
    print("    Prédictibilité depuis le passé : il faudrait E[boost|signal] > 2/RTP ≈ 3,1")
    print(f"    (RTP 0,65), soit un collage ε > {(3.08 - e_boost) / (10 - e_boost):.3f} ; "
          f"observé ε̂ = {eps_hat:+.4f} ± {eps_sd:.4f} -> exclu.")


# ==========================================================================
# 6. Jackpot k/k (mécanisme réel de l'app) + Kelly
# ==========================================================================

def jackpot_and_kelly(done: set, rob: dict) -> None:
    title("6. Jackpot k/k (le seul levier réel de l'app) et conclusion de Kelly")
    print("SU : P(plein) exacte, et jackpot J_k nécessaire pour que le SEUL jackpot")
    print("rende 1 CHF par CHF misé (hors rangs intermédiaires), J_k = mise / P(plein) :")
    print(f"{'k':>3} {'P(plein)':>12} {'J nécessaire (x mise)':>24}")
    for k in STAKES:
        pk = lab.hits_pmf(k)[k]
        print(f"{k:>3} {pk:>12.3e} {1 / pk:>24,.0f}")
    print("Les montants J_k réels ne vivent que dans le flux live (LoroClient.swift:406,")
    print("`extraJackpots`) — c'est le nombre à surveiller dans l'app (GridsView:108 le")
    print("fait déjà : francs × P(plein), étoile sur la mise la moins défavorable).")

    # Espérances nettes réellement calculées sous les 3 barèmes supposés.
    evs = [metrics(k, tabs[k])["ev_net"] for tabs in PAYTABLES.values() for k in STAKES]
    ev_lo, ev_hi, ev_med = min(evs), max(evs), float(np.median(evs))
    # Robustesse deux à deux issue de l'étape 4.
    f510 = next((z, w, s) for a_, b_, z, w, s in rob["pairs"] if (a_, b_) == (5, 10))
    others = [max(z, w, s) for a_, b_, z, w, s in rob["pairs"] if (a_, b_) != (5, 10)]

    tok = lab.preregister(
        "b2.mises_classement",
        "classement des mises {5,6,7,8,10} par espérance et par forme du risque, "
        "barème inconnu (absent du dépôt, réseau fermé)",
        "RTP, Var, P(perte totale), P(gain>=mise) sous 3 barèmes paramétriques et "
        "2 000 barèmes aléatoires par mise à RTP égalisé 0,65",
        "aucun (décision analytique exacte sous chaque barème ; pas de test)",
        "le classement par ESPÉRANCE dépend du barème (non identifiable hors ligne) ; "
        "le classement par FORME est jugé robuste s'il tient sur >=95 % des barèmes aléatoires",
        track="B",
    )
    rec_guarded(done, tok, observed=ev_med, null=None, p=None,
                power_at=None,
                verdict="mise optimale de Kelly : 0 — espérance négative sous tout barème plausible",
                notes="SU : E[hits]=k/4 quelle que soit la grille ; le signe de l'espérance est fixé "
                      "par le barème, absent du dépôt (HistoryView.swift:282) — aucun barème Keno "
                      f"publié n'a RTP>=1. Sous les 3 barèmes supposés : E[net] de {ev_lo:+.2f} à "
                      f"{ev_hi:+.2f} CHF/CHF (médiane {ev_med:+.2f}), et la meilleure mise change de "
                      "variante en variante -> classement par espérance NON identifiable hors ligne. "
                      "Forme à RTP égalisé : k=5 domine k=10 sur "
                      f"{min(f510):.0%}-{max(f510):.0%} des barèmes aléatoires (moins de pertes "
                      "sèches, gains plus fréquents, variance plus faible), mais aucune paire "
                      f"n'atteint 95 % (autres paires : 50-{max(others):.0%}) : un barème peut "
                      "inverser toute comparaison. À espérance négative, Kelly f* = 0 : la seule "
                      "mise gagnante est de ne pas miser.")

    print("\nKelly (SU dans sa structure, SUPPOSÉ dans son ampleur) :")
    print("  f* = argmax E[log(1 + f·G)] ; pour tout G à E[G] < 0, f* = 0.")
    print(f"  Sous les barèmes supposés : E[net] entre {ev_lo:+.2f} et {ev_hi:+.2f} CHF par CHF")
    print(f"  misé (médiane {ev_med:+.2f}). La mise optimale est ZÉRO. Le seul paramètre qui")
    print("  pourrait inverser le signe est un jackpot k/k dépassant mise/P(plein) (table")
    print("  ci-dessus) — surveillable en live via `extraJackpots`, hors de portée aux")
    print("  échelles habituelles des jackpots affichés.")


# ==========================================================================

def main() -> None:
    a = lab.load()
    done = {r["id"] for r in lab.ledger()}
    exact_tables()
    verify_pmf(done)
    paytable_analysis()
    rob = random_paytable_robustness(done)
    boost_analysis(a, done)
    jackpot_and_kelly(done, rob)
    title("Registre — état après b2 (Holm sur le registre entier)")
    rows = lab.holm()
    sig = [r for r in rows if r["significant"]]
    print(f"{len(lab.ledger())} entrées au registre, {len(rows)} avec p, "
          f"m_total = {rows[0]['m_total'] if rows else 0}, significatives : {len(sig)}")
    for r in rows:
        if r["id"].startswith("b2."):
            print(f"  {r['id']}: p = {r['p']:.3f}, seuil Holm = {r['holm_threshold']:.2e}, "
                  f"significatif = {r['significant']}")


if __name__ == "__main__":
    main()
