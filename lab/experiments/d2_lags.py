"""d2_lags — le balayage que c1 a déclaré manquant : T1 et T2 aux lags k > 1.

Question. `c1_conditionnel.py` a fermé le couplage de premier ordre au LAG 1
(T1 recouvrement, T2 = ‖Ĉ‖² sur les 6 400 covariances croisées) et sa note de
limites le dit : « famille : premier ordre linéaire lag 1 ». Un générateur à
mémoire, un tampon circulaire, un cache de taille fixe, une graine ré-utilisée
toutes les N sorties produiraient un couplage à UN lag précis et invisible au
lag 1. Le §11 de l'audit (analogues) ne couvre que l'état déterministe
≤ 40 bits ; un couplage statistique n'en relève pas. Cette plage n'a jamais
été balayée.

Balayage. k ∈ {1..300} ∪ {408, 612, 816, 1020, 1224, 1428} — 306 lags, dont
les lags structurellement suspects : 12 (une heure), 204 (une journée de
tirages, cf. c3), 288, et les multiples de jour jusqu'à 1 428 (une semaine).
Deux statistiques par lag, celles de c1 transposées :
  T1(k) = recouvrement moyen des paires (t, t+k)      — rémanence diagonale ;
  T2(k) = ‖Ĉ_k‖² somme des carrés des 6 400 covariances croisées à lag k
          (colonnes centrées globalement, même convention que c1) — couvre
          toute matrice de couplage, dérangements compris.

La statistique de CHAQUE test est le MAX sur les 306 lags de |z|, et ce max
est calibré contre la loi du max du même balayage sur des archives SRS
complètes — jamais contre un seuil de test unique. C'est la leçon d'a3
(max |z| = 5,24 sur les vraies données, calibré p = 0,066) : balayer 300 lags
et comparer le plus grand à un seuil individuel fabriquerait un signal à tous
les coups. Les moments (mu_k, sd_k) par lag sont eux-mêmes simulés (M archives
SRS distinctes de celles du null du max) ; leur bruit d'estimation est absorbé
par la calibration du max, qui utilise les mêmes moments.

Décision sur les coupures nocturnes — trans-coupures, et pourquoi
-----------------------------------------------------------------
Les paires sont appariées en INDEX de tirage, à travers les 345 coupures :
 1. les mécanismes visés (tampon, graine recyclée toutes les N sorties,
    mémoire d'état) comptent en SORTIES du générateur ; l'index d'archive est
    ce compteur, la nuit n'y existe pas ;
 2. les sessions font exactement 204 tirages (c3) : à k >= 204 il n'existe
    AUCUNE paire intra-session — les lags suspects 204..1428 ne sont testables
    QUE trans-coupures ; et déjà à k = 100, ~49 % des paires croisent une
    nuit : un balayage « intra-session seulement » changerait d'effectif à
    chaque k et mourrait à 204 ;
 3. le null simulé apparie les MÊMES index : la structure d'appariement est
    dans le null, pas seulement dans l'observé.
Coût déclaré : un défaut vivant en temps-machine et suspendu la nuit serait
dilué par la fraction trans-coupure — cette famille-là (modulation selon
l'horloge) est le territoire de c3, qui l'a fermée. Et un pic à un multiple
de 204 pourrait naître d'une périodicité JOURNALIÈRE des marginales sans
aucun couplage (artefact de structure d'échantillonnage) : la décision
pré-enregistrée impose de confronter d'abord un tel pic aux bornes de c3.

Puissance (obligation du labo). Couplage injecté à k0 = 204 — un générateur
dont l'état se recycle chaque jour — d'amplitude d connue, par la MÊME loi
que gen_conditional de c1 (Gumbel top-20, marginales figées à 1/4) ; le
processus à lag k0 factorise l'archive en k0 chaînes indépendantes, générées
vectorisées sur les chaînes (~0,3 s au lieu de ~1 s). Deux familles :
rémanence diagonale (cible T1) et paires cachées en dérangement m = 40
(cible T2, aveugle pour T1). Amplitudes réalisées MESURÉES (p_hot), pas
supposées. Contrôle à k0 = 37 : le balayage ne privilégie aucun lag.
Seuil de détection = max des R réplicats null (p plancher 1/(R+1), comme a3) ;
le seuil Holm final est plus strict, la puissance au seuil Holm est donc <= à
celle affichée — même convention qu'a3/c3, déclarée.

Nulls : boucle au même contrat que lab.calibrate (archives SRS complètes
indépendantes, statistique identique), T1 et T2 évalués sur les MÊMES archives
(précédent c3.calibrate_many) et réplicats parallélisés sur 4 processus, une
graine par réplicat. BLAS mono-thread par processus : les GEMM (80,N)x(N,80)
y font 98 GFLOPS contre 49 en multi-thread (mesuré) — le parallélisme est au
niveau des archives.

Limites déclarées
------------------
 1. Le plancher de p atteignable est 1/(R_NULL+1) ~ 3e-3, pas le seuil Holm
    (1,52e-05) : comme a3, une observation sous le plancher déclencherait une
    recalibration à plus de réplicats, pas une déclaration.
 2. La famille reste PREMIER ORDRE LINÉAIRE, à un lag unique : un couplage
    réparti sur plusieurs lags simultanés, ou non linéaire dans le tirage
    complet, n'est pas borné ici (limite héritée de c1, toujours ouverte).
 3. L'enveloppe de la borne est mesurée au seuil plancher ; l'extrapolation
    au seuil Holm (queue gaussienne du max, comme c0/c1) est donnée à part.

Usage : python3 d2_lags.py [--dry]   (--dry : réplicats réduits, AUCUNE
écriture au registre — mise au point uniquement)
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
import time
import multiprocessing as mp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

N = 70_560
K = 10
LAGS = np.r_[np.arange(1, 301), 204 * np.arange(2, 8)]      # 306 lags
NL = len(LAGS)
SUSPECTS = (12, 204, 288, 408, 1428)
K0 = 204                       # lag d'injection : l'état recyclé chaque jour
K0_CTRL = 37                   # contrôle : lag sans aucune structure
M_PAIR = 40                    # lignes modulées du dérangement (m* de c1)

DRY = "--dry" in sys.argv
M_MOMENTS = 8 if DRY else 150
R_NULL = 24 if DRY else 300
R_POWER = 5 if DRY else 30
R_CTRL = 0 if DRY else 15
R_EDGE = 3 if DRY else 8
GRID_DIAG = (0.5, 1.0, 1.8) if DRY else (0.5, 0.75, 1.0, 1.35, 1.8)
GRID_PAIR = (0.6, 1.0, 1.7) if DRY else (0.6, 0.8, 1.0, 1.3, 1.7)
NPROC = min(4, os.cpu_count() or 1)


# --------------------------------------------------------------------------
# Statistiques par lag — un GEMM float32 par lag, T1 exact par correction
# --------------------------------------------------------------------------

def lag_stats(mask):
    """(T1(k), T2(k)) pour les 306 lags.

    x est centré par les moyennes de colonnes GLOBALES (convention c1).
    T2(k) = somme des carrés de x[k:].T @ x[:-k] / (N-k). T1(k) est reconstruit
    exactement depuis la diagonale du même GEMM + sommes préfixes (vérifié
    contre le calcul booléen direct à 1e-7 près, cf. autotest ci-dessous).
    """
    x = mask.astype(np.float32)
    mu = x.mean(0, dtype=np.float64)
    x -= mu.astype(np.float32)
    cs = np.vstack([np.zeros((1, lab.POOL)), np.cumsum(x, 0, dtype=np.float64)])
    n = len(mask)
    t1 = np.empty(NL)
    t2 = np.empty(NL)
    musq = float((mu * mu).sum())
    for i, k in enumerate(LAGS):
        S = (x[:-k].T @ x[k:]).astype(np.float64)
        w = n - k
        t2[i] = float(((S / w) ** 2).sum())
        s1 = cs[n - k] - cs[0]                 # sommes colonnes de x[:-k]
        s2 = cs[n] - cs[k]                     # sommes colonnes de x[k:]
        t1[i] = float((np.trace(S) + (mu * (s1 + s2)).sum()) / w + musq)
    return t1, t2


def _selftest_t1():
    """T1 par GEMM+correction == T1 booléen direct (une archive, 3 lags)."""
    rng = np.random.default_rng(99)
    m = lab.srs(N, rng)
    t1, _ = lag_stats(m)
    worst = 0.0
    for k in (1, 204, 1428):
        direct = float((m[k:] & m[:-k]).sum() / (N - k))
        worst = max(worst, abs(t1[list(LAGS).index(k)] - direct))
    assert worst < 1e-5, worst
    return worst


# --------------------------------------------------------------------------
# Alternative : couplage de premier ordre à lag k0 — chaînes vectorisées
# --------------------------------------------------------------------------

def pairing(m, rng):
    """m numéros modulés + sources sur un 80-cycle (dérangement) — comme c1."""
    perm = rng.permutation(lab.POOL)
    src_of = np.empty(lab.POOL, np.int64)
    src_of[perm] = perm[np.roll(np.arange(lab.POOL), -1)]
    mod = perm[:m]
    return mod, src_of[mod]


def gen_lagged(n, k0, mod, msrc, d, rng):
    """n tirages où P(n° modulé au tirage t) dépend du tirage t-k0.

    Même loi que gen_conditional de c1 (Gumbel top-20, chaud 1/4+d, froid
    1/4-d/3), mais le tirage t ne dépendant que de t-k0, l'archive se
    factorise en k0 chaînes indépendantes -> vectorisé sur les chaînes.
    """
    lo = np.log(0.25 / 0.75)
    lo_hot = np.log((0.25 + d) / (0.75 - d)) - lo
    lo_cold = np.log((0.25 - d / 3) / (0.75 + d / 3)) - lo
    steps = -(-n // k0)
    g = rng.gumbel(size=(steps, k0, lab.POOL))
    out = np.zeros((steps, k0, lab.POOL), bool)
    idx = np.argpartition(-g[0], lab.DRAWN, axis=1)[:, :lab.DRAWN]
    np.put_along_axis(out[0], idx, True, axis=1)
    bump = np.array([lo_cold, lo_hot])
    for s in range(1, steps):
        keys = g[s].copy()
        keys[:, mod] += bump[out[s - 1][:, msrc].astype(np.intp)]
        idx = np.argpartition(-keys, lab.DRAWN, axis=1)[:, :lab.DRAWN]
        np.put_along_axis(out[s], idx, True, axis=1)
    return out.reshape(steps * k0, lab.POOL)[:n]


def realized_p_hot(cm, k0, mod, msrc):
    """P(n° modulé sorti | sa source sortie k0 tirages avant) — mesurée."""
    hot = cm[:-k0][:, msrc]
    return float(cm[k0:][:, mod][hot].mean())


def informed_play(cm, k0, mod, msrc, rng):
    """Avantage joué par qui CONNAÎT la règle (grille K sur le tirage t-k0)."""
    n = len(cm)
    hot = cm[:-k0][:, msrc]
    prio = np.ones((n - k0, lab.POOL), np.float32)
    prio[:, mod] = np.where(hot, np.float32(2.0), np.float32(0.0))
    prio += rng.random((n - k0, lab.POOL), dtype=np.float32) * np.float32(0.5)
    idx = np.argpartition(-prio, K, axis=1)[:, :K]
    hits = np.take_along_axis(cm[k0:], idx, axis=1).sum(1)
    return float(hits.mean()) - K / 4


# --------------------------------------------------------------------------
# Workers (parallélisme au niveau des archives, BLAS mono-thread)
# --------------------------------------------------------------------------

def _worker(task):
    """('srs', seed) | ('diag'|'pair', seed, k0, d, play) -> (t1, t2, p_hot, adv)."""
    kind, seed = task[0], task[1]
    rng = np.random.default_rng(seed)
    p_hot = adv = float("nan")
    if kind == "srs":
        cm = lab.srs(N, rng)
    else:
        _, _, k0, d, play = task
        if kind == "diag":
            mod = msrc = np.arange(lab.POOL)
        else:
            mod, msrc = pairing(M_PAIR, rng)
        cm = gen_lagged(N, k0, mod, msrc, d, rng)
        p_hot = realized_p_hot(cm, k0, mod, msrc)
        if play:
            adv = informed_play(cm, k0, mod, msrc, rng)
    t1, t2 = lag_stats(cm)
    return t1, t2, p_hot, adv


def run_pool(pool, tasks):
    out = pool.map(_worker, tasks, chunksize=1)
    return (np.array([o[0] for o in out]), np.array([o[1] for o in out]),
            np.array([o[2] for o in out]), np.array([o[3] for o in out]))


# --------------------------------------------------------------------------
# Expérience
# --------------------------------------------------------------------------

def main():
    t00 = time.time()
    print("=" * 78)
    print("D2 — BALAYAGE DE LAGS : T1 et T2 aux 306 lags k ∈ {1..300} ∪ multiples de 204")
    print("=" * 78)
    if DRY:
        print("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

    rows = lab.ledger()
    m_tests = len(rows) + sum(int(r.get("m_extra", 0)) for r in rows)
    p_floor = 1 / (R_NULL + 1)
    print(f"\nregistre : m = {m_tests} tests dépensés, seuil Holm p < {0.05 / m_tests:.2e} ; "
          f"plancher de ce run p = {p_floor:.2e}")
    print(f"lags : {NL} (1..300 + jours 2..7) ; suspects contrôlés : {SUSPECTS}")

    # -- 0. pré-enregistrement AVANT tout regard sur les vraies données ----
    convention = ("paires en INDEX de tirage, TRANS-coupures nocturnes : les mécanismes "
                  "visés comptent en sorties du générateur ; k>=204 n'a aucune paire "
                  "intra-session (sessions de 204, cf. c3) ; le null apparie les mêmes index")
    tok1 = lab.preregister(
        "d2.t1_lagscan",
        "Aucune rémanence/répulsion diagonale à aucun lag k∈{1..300}∪{408..1428} : "
        "max_k |z(T1_k)| (recouvrement moyen des paires (t,t+k)) compatible SRS",
        f"max sur {NL} lags de |z| du recouvrement moyen ; {convention} ; moments par lag "
        f"simulés (M={M_MOMENTS} archives SRS), max calibré contre la loi du max du même "
        "balayage (leçon a3 : jamais contre un seuil de test unique)",
        f"boucle même contrat que lab.calibrate (précédent c3.calibrate_many), parallélisée : "
        f"{R_NULL} archives SRS complètes de {N} tirages, statistique identique",
        f"conforme si p empirique > plancher {p_floor:.2e} ; sinon candidate -> recalibration "
        f"à plus de réplicats avant toute déclaration (seuil final Holm ~{0.05 / m_tests:.2e}) ; "
        "un pic à un multiple de 204 est confronté D'ABORD aux bornes de périodicité de c3 "
        "(artefact de structure d'échantillonnage) avant toute lecture de couplage",
        track="A")
    tok2 = lab.preregister(
        "d2.t2_lagscan",
        "Aucune matrice de couplage de premier ordre à aucun lag k∈{1..300}∪{408..1428}, "
        "dérangements compris : max_k |z(T2_k)|, T2_k=‖Ĉ_k‖² (6 400 covariances croisées "
        "à lag k), compatible SRS",
        f"max sur {NL} lags de |z| de la somme des carrés des covariances croisées lag-k, "
        f"colonnes centrées (convention c1) ; {convention} ; moments simulés "
        f"(M={M_MOMENTS}), max calibré contre la loi du max du même balayage",
        f"boucle même contrat que lab.calibrate (précédent c3.calibrate_many), parallélisée : "
        f"{R_NULL} archives SRS complètes de {N} tirages, statistique identique",
        f"conforme si p empirique > plancher {p_floor:.2e} ; sinon candidate -> recalibration "
        f"avant toute déclaration (seuil final Holm ~{0.05 / m_tests:.2e}) ; pic à un multiple "
        "de 204 : confronter d'abord aux bornes c3",
        track="A")
    tok3 = lab.preregister(
        "d2.plafond_lags",
        "Extension de la borne c1 (lag 1) à toute la plage k<=1428 : avantage maximal d'un "
        "couplage de premier ordre à lag unique restant sous 50 % de puissance face au "
        "balayage T1/T2",
        "avantage joué E[hits]-2,5 du joueur qui connaît la règle, à l'enveloppe (plus grand "
        "d de la grille gardant puissance < 50 % au seuil plancher du balayage), injection "
        f"k0={K0} ; contrôle d'uniformité à k0={K0_CTRL}",
        f"puissance : {R_POWER} archives contaminées par point (chaînes vectorisées, même "
        "loi que gen_conditional de c1, amplitudes réalisées mesurées) contre le null du max",
        "borne, pas un test : aucune hypothèse nulle n'est rejetée ici",
        track="A")

    qc = _selftest_t1()
    print(f"autotest T1 (GEMM+correction vs booléen direct) : écart max {qc:.1e}  OK")

    ctx = mp.get_context("fork")
    with ctx.Pool(NPROC) as pool:

        # -- 1. moments par lag (simulés, archives dédiées) ----------------
        t0 = time.time()
        t1s, t2s, _, _ = run_pool(pool, [("srs", 10_000 + r) for r in range(M_MOMENTS)])
        mu1, sd1 = t1s.mean(0), t1s.std(0, ddof=1)
        mu2, sd2 = t2s.mean(0), t2s.std(0, ddof=1)
        sd_naif = float(np.sqrt(20 * 0.25 * 0.75 * 60 / 79 / (N - 1)))
        print(f"\nmoments par lag : M={M_MOMENTS} archives SRS ({time.time() - t0:.0f}s)")
        print(f"  T1 : mu ∈ [{mu1.min():.5f}, {mu1.max():.5f}]  "
              f"sd ∈ [{sd1.min():.5f}, {sd1.max():.5f}]  "
              f"(médiane {np.median(sd1):.5f} ; {sd_naif:.5f} si paires indépendantes — "
              "les chaînes (t,t±k) partagent un tirage à TOUT lag)")
        print(f"  T2 : mu ~ {mu2.mean():.4e}  sd médiane {np.median(sd2):.2e}")

        # -- 2. null du max (archives dédiées, mêmes moments) --------------
        t0 = time.time()
        n1, n2, _, _ = run_pool(pool, [("srs", 20_000 + r) for r in range(R_NULL)])
        max1 = np.abs((n1 - mu1) / sd1).max(1)
        max2 = np.abs((n2 - mu2) / sd2).max(1)
        null1 = lab.Null(float(max1.mean()), float(max1.std(ddof=1)), R_NULL, max1)
        null2 = lab.Null(float(max2.mean()), float(max2.std(ddof=1)), R_NULL, max2)
        floor1, floor2 = float(max1.max()), float(max2.max())
        q = lambda v: np.quantile(v, [0.5, 0.9, 0.99])
        print(f"\nnull du max ({R_NULL} archives SRS complètes, {time.time() - t0:.0f}s) :")
        print(f"  max|z1| : q50={q(max1)[0]:.2f} q90={q(max1)[1]:.2f} "
              f"q99={q(max1)[2]:.2f} max={floor1:.2f}")
        print(f"  max|z2| : q50={q(max2)[0]:.2f} q90={q(max2)[1]:.2f} "
              f"q99={q(max2)[2]:.2f} max={floor2:.2f}")

        # -- 3. les VRAIES données -----------------------------------------
        a = lab.load()
        assert len(a) == N
        t1o, t2o = lag_stats(a.mask)
        z1, z2 = (t1o - mu1) / sd1, (t2o - mu2) / sd2
        obs1, obs2 = float(np.abs(z1).max()), float(np.abs(z2).max())
        k1, k2 = int(LAGS[np.abs(z1).argmax()]), int(LAGS[np.abs(z2).argmax()])
        p1, p2 = null1.p_two_sided(obs1), null2.p_two_sided(obs2)
        print(f"\n{'-' * 78}\nVRAIES DONNÉES — {N} tirages, {NL} lags")
        print(f"  ancrage c1 (lag 1) : T1={t1o[0]:.5f}  T2={t2o[0]:.4e}")
        print(f"  max|z1| = {obs1:.2f} @ lag {k1}   p (loi du max) = {p1:.3f}")
        print(f"  max|z2| = {obs2:.2f} @ lag {k2}   p (loi du max) = {p2:.3f}")
        top = lambda z: ", ".join(f"k={int(LAGS[i])}:{z[i]:+.2f}"
                                  for i in np.argsort(-np.abs(z))[:5])
        print(f"  top-5 |z1| : {top(z1)}")
        print(f"  top-5 |z2| : {top(z2)}")
        idx = {int(k): i for i, k in enumerate(LAGS)}
        print("  lags suspects : " + "  ".join(
            f"k={k}: z1={z1[idx[k]]:+.2f} z2={z2[idx[k]]:+.2f}" for k in SUSPECTS))
        verdict1 = "conforme H0" if p1 > p_floor else "candidate — recalibrer (artefact d'abord)"
        verdict2 = "conforme H0" if p2 > p_floor else "candidate — recalibrer (artefact d'abord)"

        # -- 4. puissance : rémanence diagonale à k0=204 vs balayage T1 ----
        # grille centrée par l'analytique E[T1(k0)] = 5+20d (centrage seulement :
        # la puissance et p_hot sont MESURÉES) ; détection = stat >= max null.
        sd1_k0 = float(sd1[idx[K0]])
        d_diag = [round(float(f * floor1 * sd1_k0 / 20), 5) for f in GRID_DIAG]
        print(f"\n{'-' * 78}\nPUISSANCE — couplage injecté à k0={K0} "
              f"(état recyclé chaque jour), {R_POWER} archives/point")
        print(f"seuil = max des {R_NULL} réplicats null (p plancher {p_floor:.1e} ; "
              "Holm plus strict -> puissance au seuil Holm <= affichée)")
        print(f"\n1. rémanence diagonale (cible T1)   [z1 attendu ~ 20d/{sd1_k0:.5f}]")
        print(f"{'d':>9} {'p_hot réalisée':>14} {'z1@204 moy':>10} "
              f"{'pw balayage T1':>14} {'pw balayage T2':>14}")
        pw_diag = {}
        for j, d in enumerate(d_diag):
            tasks = [("diag", 30_000 + 100 * j + r, K0, d, False) for r in range(R_POWER)]
            c1s, c2s, ph, _ = run_pool(pool, tasks)
            s1 = np.abs((c1s - mu1) / sd1).max(1)
            s2 = np.abs((c2s - mu2) / sd2).max(1)
            z1k = float(((c1s[:, idx[K0]] - mu1[idx[K0]]) / sd1_k0).mean())
            pw_diag[d] = (float((s1 >= floor1).mean()), float((s2 >= floor2).mean()))
            print(f"{d:>9.5f} {np.nanmean(ph):>14.4f} {z1k:>+10.1f} "
                  f"{pw_diag[d][0]:>14.2f} {pw_diag[d][1]:>14.2f}", flush=True)

        # -- 5. puissance : paires cachées (m=40) à k0=204 vs balayage T2 --
        sd2_k0 = float(sd2[idx[K0]])
        d_mid = 4 * np.sqrt(floor2 * sd2_k0 / M_PAIR)     # centrage : ΔT2 ~ m(d/4)²
        d_pair = [round(float(f * d_mid), 5) for f in GRID_PAIR]
        print(f"\n2. paires cachées, dérangement m={M_PAIR} (cible T2, T1 aveugle)")
        print(f"{'d':>9} {'p_hot réalisée':>14} {'z2@204 moy':>10} "
              f"{'pw balayage T2':>14} {'pw balayage T1':>14}")
        pw_pair = {}
        for j, d in enumerate(d_pair):
            tasks = [("pair", 31_000 + 100 * j + r, K0, d, False) for r in range(R_POWER)]
            c1s, c2s, ph, _ = run_pool(pool, tasks)
            s1 = np.abs((c1s - mu1) / sd1).max(1)
            s2 = np.abs((c2s - mu2) / sd2).max(1)
            z2k = float(((c2s[:, idx[K0]] - mu2[idx[K0]]) / sd2_k0).mean())
            pw_pair[d] = (float((s2 >= floor2).mean()), float((s1 >= floor1).mean()))
            print(f"{d:>9.5f} {np.nanmean(ph):>14.4f} {z2k:>+10.1f} "
                  f"{pw_pair[d][0]:>14.2f} {pw_pair[d][1]:>14.2f}", flush=True)

        # -- 6. contrôle d'uniformité : même injection à k0=37 -------------
        ctrl_note = "non couru (dry)"
        if R_CTRL:
            dd = min((d for d in d_diag if pw_diag[d][0] >= 0.5), default=d_diag[-1])
            dp = min((d for d in d_pair if pw_pair[d][0] >= 0.5), default=d_pair[-1])
            c1s, _, _, _ = run_pool(pool, [("diag", 40_000 + r, K0_CTRL, dd, False)
                                           for r in range(R_CTRL)])
            _, c2s, _, _ = run_pool(pool, [("pair", 41_000 + r, K0_CTRL, dp, False)
                                           for r in range(R_CTRL)])
            pw_cd = float((np.abs((c1s - mu1) / sd1).max(1) >= floor1).mean())
            pw_cp = float((np.abs((c2s - mu2) / sd2).max(1) >= floor2).mean())
            ctrl_note = (f"k0={K0_CTRL} : diag d={dd:.5f} pw={pw_cd:.2f} "
                         f"(vs {pw_diag[dd][0]:.2f} à 204) ; pair d={dp:.5f} pw={pw_cp:.2f} "
                         f"(vs {pw_pair[dp][0]:.2f} à 204)")
            print(f"\n3. contrôle d'uniformité — {ctrl_note}")

        # -- 7. enveloppe et avantage joué ---------------------------------
        env_diag = max((d for d in d_diag if pw_diag[d][0] < 0.5), default=d_diag[0])
        env_pair = max((d for d in d_pair if pw_pair[d][0] < 0.5), default=d_pair[0])
        _, _, _, adv_d = run_pool(pool, [("diag", 50_000 + r, K0, env_diag, True)
                                         for r in range(R_EDGE)])
        _, _, _, adv_p = run_pool(pool, [("pair", 51_000 + r, K0, env_pair, True)
                                         for r in range(R_EDGE)])

    adv_diag, se_d = float(np.mean(adv_d)), float(np.std(adv_d, ddof=1) / np.sqrt(R_EDGE))
    adv_pair, se_p = float(np.mean(adv_p)), float(np.std(adv_p, ddof=1) / np.sqrt(R_EDGE))
    adv_max = max(adv_diag, adv_pair)
    fam = "paires cachées" if adv_pair >= adv_diag else "rémanence diagonale"
    print(f"\n{'-' * 78}\nENVELOPPE (puissance < 50 % au seuil plancher, grille ci-dessus) :")
    print(f"  rémanence diagonale : d = {env_diag:.5f} -> avantage joué "
          f"{adv_diag:+.4f} ± {se_d:.4f} hits ({adv_diag / (K / 4):+.2%})")
    print(f"  paires cachées m={M_PAIR} : d = {env_pair:.5f} -> avantage joué "
          f"{adv_pair:+.4f} ± {se_p:.4f} hits ({adv_pair / (K / 4):+.2%})")
    print(f"  la borne lag-balayée (seuil plancher) est portée par : {fam}")
    print("  NB : au seuil Holm (plus haut que le plancher), l'enveloppe d — donc la borne — "
          "serait un peu PLUS haute ;\n  l'ordre de grandeur reste celui de c1 "
          "(z2 ∝ d² : +10-15 % sur d entre un test unique lag-1 et ce max sur 306 lags).")

    # -- 8. registre --------------------------------------------------------
    pw_str_d = "; ".join(f"d={d:.5f}:T1 {v[0]:.2f}/T2 {v[1]:.2f}" for d, v in pw_diag.items())
    pw_str_p = "; ".join(f"d={d:.5f}:T2 {v[0]:.2f}/T1 {v[1]:.2f}" for d, v in pw_pair.items())
    suspect_str = " ".join(f"k{k}:z1{z1[idx[k]]:+.2f}/z2{z2[idx[k]]:+.2f}" for k in SUSPECTS)
    if DRY:
        print("\n(dry run : rien consigné)")
    else:
        done = {r["id"] for r in lab.ledger()}
        if {"d2.t1_lagscan", "d2.t2_lagscan", "d2.plafond_lags"} & done:
            print("\nregistre : entrées d2 déjà présentes — pas de doublon écrit")
        else:
            lab.record(tok1, observed=obs1, null=null1,
                       power_at=f"rémanence diagonale k0={K0}, seuil plancher {p_floor:.1e} : "
                                f"{pw_str_d} ({R_POWER} rép./point) ; contrôle {ctrl_note}",
                       verdict=verdict1,
                       notes=f"max|z1|={obs1:.2f} @ lag {k1} sur {NL} lags trans-coupures ; "
                             f"suspects {suspect_str} ; sd(T1) médiane {float(np.median(sd1)):.5f} "
                             f"vs {sd_naif:.5f} paires indép. ; moments M={M_MOMENTS} ; "
                             f"balayage interne absorbé par la calibration du max (précédent a3).")
            lab.record(tok2, observed=obs2, null=null2,
                       power_at=f"paires cachées m={M_PAIR} k0={K0}, seuil plancher {p_floor:.1e} : "
                                f"{pw_str_p} ({R_POWER} rép./point)",
                       verdict=verdict2,
                       notes=f"max|z2|={obs2:.2f} @ lag {k2} ; T2 couvre toute matrice de couplage "
                             f"à chaque lag, dérangements compris ; T1 mesuré aveugle aux paires "
                             f"cachées (cf. power_at) ; même convention trans-coupures que T1.")
            lab.record(tok3, observed=adv_max, null=None, p=None,
                       power_at=f"50 % franchi entre {env_diag:.5f} et le cran supérieur (diag) ; "
                                f"entre {env_pair:.5f} et le cran supérieur (paires, m={M_PAIR})",
                       verdict="borne établie",
                       notes=f"Avantage max non détecté par le balayage 306 lags (seuil plancher "
                             f"{p_floor:.1e}) = {adv_max:+.4f} hits ({adv_max / (K / 4):+.2%}), "
                             f"famille {fam} ; diag {adv_diag:+.4f}±{se_d:.4f}, paires "
                             f"{adv_pair:+.4f}±{se_p:.4f} ; au seuil Holm l'enveloppe serait plus "
                             f"haute (limite déclarée, comme c0/c1) ; couplage multi-lag ou non "
                             f"linéaire non borné (limite héritée de c1).")
            print("\nconsigné au registre (3 entrées).")

    # -- 9. synthèse --------------------------------------------------------
    print(f"\n{'=' * 78}\nSYNTHÈSE")
    print(f"  balayage : {NL} lags, trans-coupures ; nulls du max sur {R_NULL} archives SRS")
    print(f"  T1 : max|z|={obs1:.2f} @ k={k1}, p={p1:.3f} -> {verdict1}")
    print(f"  T2 : max|z|={obs2:.2f} @ k={k2}, p={p2:.3f} -> {verdict2}")
    print(f"  détectabilité (50 %) : rémanence d ≈ {env_diag:.5f}..{d_diag[-1]:.5f}, "
          f"paires d ≈ {env_pair:.5f}..{d_pair[-1]:.5f}")
    print(f"  total {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
