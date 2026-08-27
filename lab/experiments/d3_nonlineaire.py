"""La dernière famille non bornée : dépendance NON LINÉAIRE entre tirages.

`c1_conditionnel.py` a borné le premier ordre LINÉAIRE au lag 1 (matrice M sur
les covariances croisées) et légué explicitement sa limite : « une dépendance
non linéaire du tirage complet reste non bornée ». `c2_apprentissage.py` a
montré qu'un modèle LINÉAIRE dans ses traits ne trouve rien — et surtout que
sans témoin positif, un modèle qui ne trouve rien est indistinguable d'un
modèle cassé. Ce script ferme la famille non linéaire, par trois angles du
plus interprétable au plus général.

Angle 1 — la FORME de la loi du recouvrement, pas seulement sa moyenne.
    T1 de c1 teste E[O(t,t+1)] = 5. Une dépendance non linéaire peut laisser
    cette moyenne intacte et déformer la distribution. S1 = χ² de
    l'histogramme complet de O (cases fusionnées à attendu >= 5, queue >= 12
    regroupée) contre les effectifs hypergéométriques exacts. Le χ² n'est
    qu'une DISTANCE : sa distribution sous H0 est simulée, jamais tabulée
    (les paires consécutives partagent un tirage — un χ²(df) tabulé mentirait,
    null simulé s1 ≈ 10,8 contre 12 tabulé).
    Témoin : mélange attract/repel — avec probabilité eps/2 le tirage garde
    8 des 20 précédents, avec eps/2 il n'en garde que 2 ; E[O] = 5 EXACTEMENT
    (8/2 et 2/2 compensés) et la covariance linéaire diagonale reste nulle
    (P(n|n) = ½·8/20 + ½·2/20 = 0,25) : invisible de T1 ET de T2, donc
    strictement hors de la famille bornée par c1.

Angle 2 — second ordre temporel : O(t-1,t) prédit-il O(t,t+1) ?
    S2 = corrélation de Pearson des recouvrements successifs (linéaire).
    S3 = information mutuelle plug-in entre recouvrements successifs,
    7 classes {<=2,3,4,5,6,7,>=8} (chacune >= 6 % de masse). L'IM empirique
    est BIAISÉE VERS LE HAUT : E[IM|H0] ≈ (K-1)²/(2N ln2) ≈ 3,7e-4 bit, pas
    0 — le null simulé À LA MÊME TAILLE d'échantillon la recentre ; comparer
    l'observé à 0 fabriquerait un z de l'ordre de +4 à partir de rien (le
    piège exact du §14 de l'audit, version information).
    Témoin IM : si |O(t-1,t) - 5| >= 3, le tirage t+1 est modulé de ±delta
    sur les 20 numéros de t, signe TIRÉ AU HASARD : moyenne conservée,
    corrélation nulle par construction — seule une statistique de forme
    (IM, χ² d'histogramme) peut le voir. C'est la démonstration que S2 ne
    suffit pas.

Angle 3 — un modèle non linéaire, protocole c2 (témoins obligatoires).
    Gradient boosting (arbres : interactions et seuils natifs) sur 6 traits
    causaux à VALEURS ENTIÈRES (présence aux lags 1-3, O(t-2,t-1), O(t-3,t-2),
    sorties sur 10 tirages) — l'accord voie vectorisée / voie causale est
    alors EXACT, aucun risque de bascule d'égalité au contrôle de fuite.
    Six traits seulement : c2 a montré qu'enrichir dégrade.
    Témoin positif imposé par l'énoncé : si O(t-2,t-1) > 7, les numéros du
    tirage t-1 ont p = 1/4 + d au tirage t (froids compensés à 1/4 - d/3).
    Le déclencheur touche ~7 % des tirages (plus les cascades qu'il crée).
    Témoin négatif : le même pipeline sur une archive SRS doit rendre 2,50.
    Oracle : le joueur qui CONNAÎT la règle — borne haute de ce que le
    modèle peut capter, et rappel que détecter n'est pas exploiter.

Limites déclarées
------------------
 1. Comme c0/c1 : le seuil registre (z ≈ 4,33) extrapole la queue du null en
    gaussienne ; 300 réplicats ne donnent pas un quantile à 1,5e-05, et le
    plancher du p empirique est 1/301. Un |z| > 3 déclenche d'abord une
    chasse à l'artefact, pas une annonce.
 2. REPS_POWER = 30 (contre 60 dans c1), dit plutôt que caché : la machine
    est partagée avec le run de d2_lags pendant toute l'exécution ; à 50 %
    de puissance l'incertitude est ±9 points, sans effet sur l'ordre de
    grandeur des enveloppes (mêmes conventions que la 17e voie).
 3. Les témoins couvrent trois formes non linéaires (mélange de régimes,
    hétéroscédasticité conditionnelle, seuil sur le recouvrement), pas
    toutes les formes possibles — aucune famille de témoins n'est
    exhaustive. S1 et S3 restent des statistiques de FORME générales :
    toute dépendance qui déforme la loi de O ou la loi jointe des O
    successifs tombe dans leur champ, quelle que soit sa paramétrisation.
 4. Le modèle de l'angle 3 ne voit que 3 lags et 2 recouvrements : une
    non-linéarité d'ordre supérieur à ces traits lui échapperait — mais
    elle n'échapperait pas à S1/S3 si elle touche la loi du recouvrement.

Usage : python d3_nonlineaire.py [--dry]   (--dry : réplicats réduits,
n'écrit PAS au registre — mise au point uniquement)
"""
import os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "2")   # machine partagée (d2_lags)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab
from sklearn.ensemble import HistGradientBoostingClassifier

POOL, DRAWN, K = lab.POOL, lab.DRAWN, 10
N = 70_560
DRY = "--dry" in sys.argv
REPS_NULL = 40 if DRY else 300
REPS_POWER = 6 if DRY else 30
GRID_MIX = (0.004, 0.016) if DRY else (0.002, 0.004, 0.008, 0.016)
GRID_VC = (0.03, 0.08) if DRY else (0.02, 0.03, 0.05, 0.08)
GRID_RULE = (0.007, 0.02) if DRY else (0.004, 0.007, 0.012, 0.02)
GRID_MODEL = (0.08,) if DRY else (0.02, 0.04, 0.08, 0.15)
WARM3 = 2_000
CPS_REAL = (20_000,) if DRY else (20_000, 45_000)
CPS_CTRL = (20_000,)
STOP3 = 32_000 if DRY else None


# --------------------------------------------------------------------------
# Statistiques (angles 1 et 2) — sur un masque (n,80), scalaires
# --------------------------------------------------------------------------

def overlaps(mask):
    return (mask[1:] & mask[:-1]).sum(1)


_PMF = lab.overlap_pmf()
_EXP = _PMF * (N - 1)
_LAST = int(np.max(np.flatnonzero(_EXP >= 5)))        # = 12 : au-delà, attendu < 5
_BINID = np.minimum(np.arange(DRAWN + 1), _LAST)
_EXPB = np.bincount(_BINID, weights=_EXP)


def s1_hist(mask):
    """χ² de l'histogramme complet de O contre les effectifs hypergéométriques.

    Cases 0..11 + {>=12} (règle : attendu >= 5, fixée par la pmf exacte AVANT
    tout regard sur les données). La référence est analytique mais la
    DISTRIBUTION du χ² est simulée : les 70 559 paires se chevauchent.
    """
    obs = np.bincount(_BINID[overlaps(mask)], minlength=_LAST + 1).astype(float)
    return float(((obs - _EXPB) ** 2 / _EXPB).sum())


def s2_corr(mask):
    """Corrélation de Pearson entre recouvrements successifs (le linéaire)."""
    ov = overlaps(mask)
    return float(np.corrcoef(ov[:-1], ov[1:])[0, 1])


def s3_mi(mask):
    """Information mutuelle plug-in (bits) entre recouvrements successifs.

    7 classes {<=2,3,4,5,6,7,>=8}. Le plug-in est biaisé vers le haut sur
    données finies (≈ (K-1)²/(2N ln2) ≈ 3,7e-4 bit ici) : seul le null
    simulé à la même taille rend ce chiffre interprétable.
    """
    ov = overlaps(mask)
    b = np.clip(ov, 2, 8) - 2
    C = np.bincount(b[:-1] * 7 + b[1:], minlength=49).reshape(7, 7).astype(float)
    p = C / C.sum()
    pi_, pj = p.sum(1), p.sum(0)
    nz = p > 0
    return float((p[nz] * np.log2(p[nz] / np.outer(pi_, pj)[nz])).sum())


def t1_overlap(mask):
    """T1 de c1 (recouvrement moyen) — gardé pour montrer ce qu'il NE voit pas."""
    return float(overlaps(mask).sum() / (len(mask) - 1))


def t2_lagcov(mask):
    """T2 de c1 (‖Ĉ‖² lag-1) — le test qui borne le premier ordre linéaire."""
    x = mask.astype(np.float32)
    x -= x.mean(0)
    c = x[1:].T @ x[:-1] / np.float32(len(x) - 1)
    return float((c * c).sum(dtype=np.float64))


STATS = (("S1 hist", s1_hist), ("S2 corr", s2_corr), ("S3 IM", s3_mi),
         ("T1 moy", t1_overlap), ("T2 ‖Ĉ‖²", t2_lagcov))


def calibrate_shared(reps, seed):
    """Nulls simulés PARTAGÉS : mêmes archives SRS pour les 5 statistiques."""
    rng = np.random.default_rng(seed)
    vals = {name: np.empty(reps) for name, _ in STATS}
    for r in range(reps):
        m = lab.srs(N, rng)
        for name, fn in STATS:
            vals[name][r] = fn(m)
        if (r + 1) % max(1, reps // 6) == 0:
            print(f"  null {r + 1}/{reps}", flush=True)
    return {name: lab.Null(float(v.mean()), float(v.std(ddof=1)), reps, v)
            for name, v in vals.items()}


# --------------------------------------------------------------------------
# Les alternatives non linéaires (générateurs séquentiels — chaque tirage
# dépend du précédent ; les régimes sont rares, seul le régime est réécrit)
# --------------------------------------------------------------------------

def _regime_row(prev_row, k, rng):
    """Un tirage qui garde exactement k des 20 numéros de prev_row."""
    prev = np.flatnonzero(prev_row)
    comp = np.flatnonzero(~prev_row)
    g = rng.random(POOL)
    row = np.zeros(POOL, bool)
    row[prev[np.argpartition(-g[prev], k - 1)[:k]]] = True
    row[comp[np.argpartition(-g[comp], DRAWN - k - 1)[:DRAWN - k]]] = True
    return row


def gen_mix(n, eps, rng, kh=8, kl=2):
    """Mélange de régimes : avec prob eps/2 garder 8 des 20 précédents, avec
    eps/2 n'en garder que 2. E[O] = 5 exact, P(n|n) = 0,25 exact : hors de
    portée de T1 ET T2 — seule la FORME de la loi de O bouge (angle 1)."""
    m = lab.srs(n, rng)
    u = rng.random(n)
    reg = np.where(u < eps / 2, 1, np.where(u < eps, -1, 0))
    reg[0] = 0
    for t in np.flatnonzero(reg):
        m[t] = _regime_row(m[t - 1], kh if reg[t] == 1 else kl, rng)
    return m


def gen_var_cond(n, delta, rng, thr=3):
    """Hétéroscédasticité conditionnelle : si |O(t-1,t) - 5| >= 3, le tirage
    t+1 est modulé de ±delta sur les 20 numéros de t, SIGNE AU HASARD.
    Moyenne conservée, corrélation nulle par construction : dépendance de
    forme quelconque que S2 ne peut pas voir (angle 2, témoin IM)."""
    m = lab.srs(n, rng)
    sgn = rng.random(n) < 0.5
    lo_p = np.log((0.25 + delta) / (0.75 - delta)) - np.log((0.25 - delta / 3) / (0.75 + delta / 3))
    lo_m = np.log((0.25 - delta) / (0.75 + delta)) - np.log((0.25 + delta / 3) / (0.75 - delta / 3))
    for t in range(1, n - 1):
        if abs(int(np.count_nonzero(m[t - 1] & m[t])) - 5) >= thr:
            keys = rng.gumbel(size=POOL)
            keys[m[t]] += lo_p if sgn[t] else lo_m
            idx = np.argpartition(-keys, DRAWN)[:DRAWN]
            row = np.zeros(POOL, bool)
            row[idx] = True
            m[t + 1] = row
    return m


def gen_ov_rule(n, d, rng, thr=7):
    """Le témoin imposé par l'énoncé : si O(t-2,t-1) > 7, les numéros du
    tirage t-1 ont p = 1/4 + d au tirage t (froids à 1/4 - d/3). Non linéaire
    par le SEUIL ; les cascades (tirages favorisés -> recouvrements plus
    hauts -> re-déclenchement) font partie de l'alternative."""
    m = lab.srs(n, rng)
    delta = np.log((0.25 + d) / (0.75 - d)) - np.log((0.25 - d / 3) / (0.75 + d / 3))
    for t in range(2, n):
        if int(np.count_nonzero(m[t - 2] & m[t - 1])) > thr:
            keys = rng.gumbel(size=POOL)
            keys[m[t - 1]] += delta
            idx = np.argpartition(-keys, DRAWN)[:DRAWN]
            row = np.zeros(POOL, bool)
            row[idx] = True
            m[t] = row
    return m


def power_multi(gen, nulls, reps, seed, alpha_z):
    """Puissance de TOUTES les statistiques sur les MÊMES archives contaminées.

    Trois fois moins de génération qu'un lab.power par statistique, et les
    z croisés (quelle statistique voit quoi) sortent gratuitement.
    """
    rng = np.random.default_rng(seed)
    zs = {name: np.empty(reps) for name, _ in STATS}
    for r in range(reps):
        m = gen(rng)
        for name, fn in STATS:
            zs[name][r] = nulls[name].z(fn(m))
    return {name: (float(np.mean(np.abs(v) >= alpha_z)), float(v.mean()))
            for name, v in zs.items()}


# --------------------------------------------------------------------------
# Angle 3 : le modèle non linéaire — traits causaux ENTIERS, double voie
# --------------------------------------------------------------------------

N_FEAT = 6


def feats_bulk(arch):
    """(n,80,6) float32 à valeurs ENTIÈRES. La ligne t n'utilise que < t.

    Traits : présence aux lags 1,2,3 ; O(t-2,t-1) ; O(t-3,t-2) ; sorties sur
    les 10 derniers tirages. Valeurs entières exactement représentables :
    l'accord bulk/causal est exact, aucune égalité ne peut basculer sous
    leak_check par un arrondi.
    """
    arch.build_index()
    n = len(arch)
    mk = arch.mask
    f = np.zeros((n, POOL, N_FEAT), np.float32)
    for i, lag in enumerate((1, 2, 3)):
        f[lag:, :, i] = mk[:-lag]
    ovl = np.zeros(n, np.float32)
    ovl[1:] = (mk[1:] & mk[:-1]).sum(1)               # ovl[t] = O(t-1,t)
    f[2:, :, 3] = ovl[1:-1, None]                     # O(t-2,t-1)
    f[3:, :, 4] = ovl[1:-2, None]                     # O(t-3,t-2)
    hi = np.vstack([np.zeros((1, POOL), np.int32), arch.cum[:-1]])
    lo = np.vstack([np.zeros((11, POOL), np.int32), arch.cum[:-11]])
    f[:, :, 5] = (hi - lo)
    return f


def feats_at(past):
    """(80,6) pour le seul instant t, depuis un `Past` borné à [0,t)."""
    m1, m2, m3 = past.mask[-1], past.mask[-2], past.mask[-3]
    X = np.empty((POOL, N_FEAT), np.float32)
    X[:, 0] = m1
    X[:, 1] = m2
    X[:, 2] = m3
    X[:, 3] = float(np.count_nonzero(m1 & m2))
    X[:, 4] = float(np.count_nonzero(m2 & m3))
    X[:, 5] = past.counts_window(10)
    return X


class GBLearner:
    """Gradient boosting sur l'inclusion, réajusté en marche avant.

    Même discipline que c2 : à chaque point de contrôle le modèle est ajusté
    sur TOUT le passé disponible et rien d'autre ; entre deux points il
    prédit sans apprendre. Les scores sont précalculés en bloc depuis les
    traits vectorisés ; `predict_causal` refait le calcul depuis un `Past`
    borné, pour le contrôle de fuite.
    """

    def __init__(self, arch, cps):
        self.arch, self.cps = arch, cps
        self.feats = feats_bulk(arch)
        self.models = {}
        self.scores = None

    def _cp(self, t):
        prior = [c for c in self.cps if c <= t]
        return prior[-1] if prior else 0

    def model(self, cp):
        if cp not in self.models:
            X = self.feats[WARM3:cp].reshape(-1, N_FEAT)
            y = self.arch.mask[WARM3:cp].reshape(-1)
            gb = HistGradientBoostingClassifier(
                max_iter=100, learning_rate=0.1, max_leaf_nodes=31,
                early_stopping=False, random_state=0)
            gb.fit(X, y)
            self.models[cp] = gb
        return self.models[cp]

    def fit_all(self, stop=None):
        n = len(self.arch) if stop is None else stop
        self.scores = np.zeros((n, POOL), np.float32)
        bounds = list(self.cps) + [n]
        for cp, nxt in zip(bounds[:-1], bounds[1:]):
            gb = self.model(cp)
            self.scores[cp:nxt] = gb.decision_function(
                self.feats[cp:nxt].reshape(-1, N_FEAT)).reshape(-1, POOL)

    def predict(self, past, t):
        return np.argsort(-self.scores[t], kind="stable")[:K] + 1

    def predict_causal(self, past, t):
        z = self.models[self._cp(t)].decision_function(feats_at(past))
        return np.argsort(-z.astype(np.float32), kind="stable")[:K] + 1


def eval_model(arch, cps, stop=None):
    """Ajuste, évalue en marche avant. (hits, z, log10 e, n, learner)."""
    lr = GBLearner(arch, cps)
    lr.fit_all(stop)
    hits = lab.walk_forward(arch, lr.predict, k=K, warmup=cps[0], stop=stop)
    pmf = lab.hits_pmf(K)
    var = float((pmf * np.arange(K + 1) ** 2).sum()) - (K / 4) ** 2
    z = (hits.mean() - K / 4) / np.sqrt(var / len(hits))
    _, log_e = lab.evalue(hits, K)
    return float(hits.mean()), float(z), float(log_e), len(hits), lr


def eval_oracle(mask, warmup, stop=None, thr=7):
    """Le joueur qui CONNAÎT la règle du témoin : borne haute du captable."""
    n = len(mask) if stop is None else stop
    ovl = (mask[1:] & mask[:-1]).sum(1)               # ovl[i] = O(i,i+1)
    trig = np.zeros(n, bool)
    trig[2:] = ovl[:n - 2] > thr                      # O(t-2,t-1) > thr
    prev20 = np.argsort(~mask[warmup - 1:n - 1], axis=1, kind="stable")[:, :DRAWN]
    picks = np.where(trig[warmup:, None], prev20[:, :K], np.arange(K)[None, :])
    hits = np.take_along_axis(mask[warmup:n], picks, axis=1).sum(1)
    p_hot = float(ovl[warmup - 1:n - 1][trig[warmup:]].mean() / DRAWN) if trig[warmup:].any() else float("nan")
    return float(hits.mean()), float(trig[warmup:].mean()), p_hot


def as_archive(mask, base):
    nums = np.sort(np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1,
                   axis=1).astype(np.int8)
    arch = lab.Archive(base.ids.copy(), base.ts.copy(), nums,
                       base.boost.copy(), base.bonus.copy(), mask)
    arch.build_index()
    return arch


# --------------------------------------------------------------------------

def main():
    t00 = time.time()
    print("=" * 78)
    print("DÉPENDANCE NON LINÉAIRE — la famille que c1 a déclarée ouverte")
    print("=" * 78)
    if DRY:
        print("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

    # -- 0. seuil du registre entier ---------------------------------------
    rows = lab.ledger()
    m_tests = len(rows) + sum(int(r.get("m_extra", 0)) for r in rows)
    from scipy.stats import norm
    z_crit = float(norm.isf(0.05 / m_tests / 2))
    print(f"\nregistre : m = {m_tests} tests déjà dépensés -> seuil z = {z_crit:.2f} "
          f"(p < {0.05 / m_tests:.2e})")

    # -- 1. nulls simulés partagés (jamais tabulés) ------------------------
    t0 = time.time()
    print(f"\nnulls simulés : {REPS_NULL} archives SRS complètes partagées "
          f"par les 5 statistiques", flush=True)
    nulls = calibrate_shared(REPS_NULL, seed=501)
    print(f"({time.time() - t0:.0f}s)")
    n1, n2, n3 = nulls["S1 hist"], nulls["S2 corr"], nulls["S3 IM"]
    print(f"  S1 χ² histogramme : {n1.mean:8.3f} +- {n1.sd:.3f}   "
          f"(χ²({_LAST}) tabulé dirait {_LAST},0 — les paires se chevauchent)")
    print(f"  S2 corr ov succ.  : {n2.mean:+8.5f} +- {n2.sd:.5f}   "
          f"(1/sqrt(n) dirait {1 / np.sqrt(N - 2):.5f})")
    bias_th = 36 / (2 * (N - 2) * np.log(2))
    print(f"  S3 IM plug-in     : {n3.mean:.3e} +- {n3.sd:.1e} bit")
    print(f"     le biais plug-in est LÀ et il est mesuré : E[IM|H0] = {n3.mean:.2e}, "
          f"théorie (K-1)²/(2N ln2) = {bias_th:.2e} ;")
    print(f"     lu contre 0, l'observé nul moyen vaudrait déjà z = "
          f"+{n3.mean / n3.sd:.1f} — le null simulé à même taille recentre.")

    # -- 2. pré-enregistrement AVANT tout regard sur les vraies données ----
    tok1 = lab.preregister(
        "d3.hist_overlap",
        "La LOI complète du recouvrement lag-1 (pas seulement sa moyenne, T1 de c1) "
        "est compatible SRS : pas de déformation de forme (régimes, queues, variance)",
        "χ² de l'histogramme de O(t,t+1) sur 70 559 paires, cases 0..11 + {>=12} "
        "(fusion à attendu >= 5), effectifs de référence hypergéométriques exacts",
        f"simulation : {REPS_NULL} archives SRS complètes de {N} tirages, "
        "statistique identique (les paires se chevauchent : χ² tabulé refusé)",
        f"conforme si p empirique > seuil Holm registre ({0.05 / m_tests:.2e}) ; "
        "|z|>3 déclenche d'abord une chasse à l'artefact (leçon du §14)",
        track="A")
    tok2 = lab.preregister(
        "d3.ov2_corr",
        "Pas de second ordre temporel LINÉAIRE : corr(O(t-1,t), O(t,t+1)) = 0 — "
        "la suite des recouvrements est sans mémoire au premier ordre",
        "corrélation de Pearson des 70 558 paires de recouvrements successifs",
        f"simulation : {REPS_NULL} archives SRS complètes, statistique identique",
        f"conforme si p empirique > seuil Holm registre ({0.05 / m_tests:.2e}) ; "
        "|z|>3 déclenche d'abord une chasse à l'artefact",
        track="A")
    tok3 = lab.preregister(
        "d3.ov2_mi",
        "Pas de second ordre temporel de FORME QUELCONQUE : information mutuelle "
        "nulle entre recouvrements successifs (couvre ce que la corrélation ne "
        "voit pas : hétéroscédasticité conditionnelle, régimes, seuils)",
        "IM plug-in (bits), 7 classes {<=2,3,4,5,6,7,>=8}, 70 558 paires successives",
        f"simulation : {REPS_NULL} archives SRS complètes, même statistique à MÊME "
        "taille (le plug-in est biaisé vers le haut ~3,7e-4 bit : lu contre 0 le "
        "null moyen vaudrait déjà z~+4 — le null simulé recentre)",
        f"conforme si p empirique > seuil Holm registre ({0.05 / m_tests:.2e}) ; "
        "|z|>3 déclenche d'abord une chasse à l'artefact",
        track="A")
    tok4 = lab.preregister(
        "d3.model_nonlin",
        "Un modèle NON LINÉAIRE (gradient boosting : interactions et seuils) sur "
        "traits causaux bat-il le hasard en marche avant sur l'archive réelle ?",
        "hits moyens d'une grille de 10 classée par gradient boosting réajusté en "
        f"marche avant (points de contrôle {CPS_REAL}), contre la base 2,50",
        "témoins : positif = règle à seuil imposée (O(t-2,t-1)>7 -> rémanence d) "
        "sur archives contaminées, amplitude minimale détectée mesurée ; "
        "négatif = même pipeline sur archive SRS, attendu 2,50",
        "avantage établi si z > seuil registre ET témoin positif reproduit ; "
        "sans témoin positif franchi, un nul est ininterprétable (leçon de c2)",
        track="A")

    # -- 3. puissance mesurée : trois formes non linéaires -----------------
    print(f"\n{'-' * 78}\n1. Puissance (angle 1) — mélange de régimes 8/2, E[O]=5 exact, "
          f"cov diagonale nulle\n   ({REPS_POWER} réplicats/point, seuil |z| >= {z_crit:.2f})")
    print(f"{'eps':>8} | {'S1 hist':>16} | {'S3 IM':>16} | {'T1 moy':>16} | {'T2 ‖Ĉ‖²':>16}")
    env_mix = None
    for i, eps in enumerate(GRID_MIX):
        r = power_multi(lambda rg, e=eps: gen_mix(N, e, rg), nulls,
                        REPS_POWER, seed=600 + i, alpha_z=z_crit)
        print(f"{eps:>8.3f} | " + " | ".join(
            f"{r[k][0]:>6.0%} (z {r[k][1]:+6.1f})" for k in
            ("S1 hist", "S3 IM", "T1 moy", "T2 ‖Ĉ‖²")), flush=True)
        if r["S1 hist"][0] < 0.5:
            env_mix = eps
    print(f"  -> T1 et T2 (les tests de c1) restent à z ≈ 0 : cette famille est bien "
          f"HORS de la borne\n     conditionnelle linéaire ; S1 la voit. "
          f"Enveloppe 50 % : eps entre {env_mix} et le cran supérieur.")

    print(f"\n{'-' * 78}\n2. Puissance (angle 2) — hétéroscédasticité conditionnelle "
          f"(signe aléatoire :\n   corrélation nulle PAR CONSTRUCTION — seule une "
          f"statistique de forme peut voir)")
    print(f"{'delta':>8} | {'S3 IM':>16} | {'S2 corr':>16} | {'S1 hist':>16} | {'T1 moy':>16}")
    env_vc = None
    for i, dl in enumerate(GRID_VC):
        r = power_multi(lambda rg, d=dl: gen_var_cond(N, d, rg), nulls,
                        REPS_POWER, seed=700 + i, alpha_z=z_crit)
        print(f"{dl:>8.3f} | " + " | ".join(
            f"{r[k][0]:>6.0%} (z {r[k][1]:+6.1f})" for k in
            ("S3 IM", "S2 corr", "S1 hist", "T1 moy")), flush=True)
        if r["S3 IM"][0] < 0.5:
            env_vc = dl
    print(f"  -> S2 (corrélation) reste aveugle à tous les niveaux : l'IM est "
          f"NÉCESSAIRE, pas décorative.\n     Enveloppe 50 % IM : delta entre "
          f"{env_vc} et le cran supérieur.")

    print(f"\n{'-' * 78}\n3. Puissance (angle 2/3) — règle à seuil de l'énoncé "
          f"(O(t-2,t-1)>7 -> rémanence d)")
    print(f"{'d':>8} | {'S3 IM':>16} | {'S2 corr':>16} | {'S1 hist':>16} | {'T1 moy':>16}")
    env_rule = None
    for i, d in enumerate(GRID_RULE):
        r = power_multi(lambda rg, dd=d: gen_ov_rule(N, dd, rg), nulls,
                        REPS_POWER, seed=800 + i, alpha_z=z_crit)
        print(f"{d:>8.3f} | " + " | ".join(
            f"{r[k][0]:>6.0%} (z {r[k][1]:+6.1f})" for k in
            ("S3 IM", "S2 corr", "S1 hist", "T1 moy")), flush=True)
        if r["S3 IM"][0] < 0.5:
            env_rule = d
    print(f"  -> l'IM domine partout (la corr et T1 suivent, plus tard). "
          f"Enveloppe 50 % IM : d entre {env_rule} et le cran supérieur.")

    # -- 4. les VRAIES données (angles 1 et 2) -----------------------------
    print(f"\n{'-' * 78}\n4. Les vraies données ({N} tirages)")
    a = lab.load()
    assert len(a) == N
    obs = {name: fn(a.mask) for name, fn in STATS}
    res = {}
    for name in ("S1 hist", "S2 corr", "S3 IM"):
        z = nulls[name].z(obs[name])
        p = nulls[name].p_two_sided(obs[name])
        res[name] = (z, p)
        print(f"  {name:<10} observé {obs[name]:.6g}   z = {z:+.2f}   p = {p:.3f}")
    ovr = overlaps(a.mask)
    cnt = np.bincount(_BINID[ovr], minlength=_LAST + 1)
    worst = int(np.argmax((cnt - _EXPB) ** 2 / _EXPB))
    print(f"  détail S1 : case la plus déviante O={'>=12' if worst == _LAST else worst} "
          f"({cnt[worst]} contre {_EXPB[worst]:.0f} attendus, "
          f"{(cnt[worst] - _EXPB[worst]) / np.sqrt(_EXPB[worst]):+.1f} sd)")
    print(f"  (T1 {obs['T1 moy']:.5f}, T2 {obs['T2 ‖Ĉ‖²']:.4e} — recoupent c1)")

    verdicts = {name: ("conforme H0" if res[name][1] > 0.05 / m_tests
                       else "A EXAMINER (artefact d'abord)") for name in res}

    # -- 5. angle 3 : le modèle non linéaire -------------------------------
    print(f"\n{'-' * 78}\n5. Modèle non linéaire (gradient boosting, 6 traits "
          f"causaux entiers)")
    t0 = time.time()
    a.build_index()
    lr = GBLearner(a, CPS_REAL)
    gap = 0.0
    for t in (2500, 25_000, 50_000, 70_000):
        if STOP3 is not None and t >= STOP3:
            continue
        gap = max(gap, float(np.abs(lr.feats[t] - feats_at(lab.Past(a, t))).max()))
    print(f"  accord bulk/causal : écart max {gap:.1e} (traits entiers : doit être 0)",
          flush=True)
    lr.fit_all(STOP3)
    hits_wf = lab.walk_forward(a, lr.predict, k=K, warmup=CPS_REAL[0], stop=STOP3)
    pmf_h = lab.hits_pmf(K)
    var_h = float((pmf_h * np.arange(K + 1) ** 2).sum()) - (K / 4) ** 2
    hits_r, n_r = float(hits_wf.mean()), len(hits_wf)
    z_r = (hits_r - K / 4) / np.sqrt(var_h / n_r)
    _, loge_r = lab.evalue(hits_wf, K)
    same = all(np.array_equal(lr.predict(lab.Past(a, t), t),
                              lr.predict_causal(lab.Past(a, t), t))
               for t in (25_000, 30_000) if STOP3 is None or t < STOP3)
    print(f"  cohérence predict / predict_causal aux sondes : {'oui' if same else 'NON'}")
    clean, spots = lab.leak_check(a, lr.predict_causal, k=K,
                                  warmup=CPS_REAL[0], probes=6, repeats=4)
    print(f"  contrôle de fuite : {'propre' if clean else f'FUITE en {spots}'}")
    if not clean or not same or gap != 0.0:
        print("  -> résultat invalide, on s'arrête là.")
        return
    print(f"\n  RÉEL : {hits_r:.4f} hits sur {n_r} tirages   z = {z_r:+.2f}   "
          f"log10(e) = {loge_r:.1f}   ({time.time() - t0:.0f}s)")

    print(f"\n  Témoins (1 archive par point, pipeline identique, "
          f"point de contrôle {CPS_CTRL[0]}) :")
    print(f"  {'archive':<16}{'déclch.':>8}{'oracle':>9}{'modèle':>9}{'z_mod':>8}"
          f"{'part captée':>13}")
    rng = np.random.default_rng(20260827)
    neg = as_archive(lab.srs(N, rng), a)
    h_neg, z_neg, _, n_neg, _ = eval_model(neg, CPS_CTRL, stop=STOP3)
    o_neg, f_neg, _ = eval_oracle(neg.mask, CPS_CTRL[0], stop=STOP3)
    print(f"  {'SRS (négatif)':<16}{f_neg:>8.3f}{o_neg:>9.4f}{h_neg:>9.4f}"
          f"{z_neg:>+8.2f}{'—':>13}")
    d_detect = None
    ctrl_rows = []
    for d in GRID_MODEL:
        arch_c = as_archive(gen_ov_rule(N, d, rng), a)
        h_c, z_c, _, _, _ = eval_model(arch_c, CPS_CTRL, stop=STOP3)
        o_c, f_c, ph_c = eval_oracle(arch_c.mask, CPS_CTRL[0], stop=STOP3)
        part = (h_c - K / 4) / (o_c - K / 4) if o_c > K / 4 + 5e-4 else float("nan")
        ctrl_rows.append((d, f_c, o_c, h_c, z_c, part, ph_c))
        print(f"  {'d = %.3f' % d:<16}{f_c:>8.3f}{o_c:>9.4f}{h_c:>9.4f}"
              f"{z_c:>+8.2f}{part:>12.0%}" if part == part else
              f"  {'d = %.3f' % d:<16}{f_c:>8.3f}{o_c:>9.4f}{h_c:>9.4f}"
              f"{z_c:>+8.2f}{'nan':>13}", flush=True)
        if d_detect is None and z_c >= 3:
            d_detect = d
        del arch_c
    print(f"\n  p_chaud réalisée au plus gros d : {ctrl_rows[-1][6]:.3f} "
          f"(cible 0,25 + d = {0.25 + GRID_MODEL[-1]:.3f})")
    print(f"  le modèle détecte (z >= 3) à partir de d ≈ {d_detect} ; "
          f"S3 (IM) détectait dès d ≈ {env_rule} au seuil registre —")
    print(f"  la statistique dédiée bat le modèle appris d'un ordre de grandeur, "
          f"et l'oracle lui-même\n  n'atteint z = 3 qu'où 10·d·P(déclenché) > "
          f"3·sd : détecter n'est pas exploiter (§3 bis).")

    # -- 6. registre --------------------------------------------------------
    if not DRY:
        lab.record(tok1, observed=obs["S1 hist"], null=n1,
                   power_at=f"mélange de régimes 8/2 (E[O]=5 exact, invisible de T1 et T2) : "
                            f"50 % entre eps={env_mix} et le cran supérieur "
                            f"({REPS_POWER} réplicats, grille {GRID_MIX})",
                   verdict=verdicts["S1 hist"],
                   notes=f"cases 0..11 + >=12 (attendu>=5) ; case la plus déviante "
                         f"O={'>=12' if worst == _LAST else worst} à "
                         f"{(cnt[worst] - _EXPB[worst]) / np.sqrt(_EXPB[worst]):+.1f} sd ; "
                         f"null {n1.mean:.2f}±{n1.sd:.2f} contre χ²({_LAST})=12 tabulé — "
                         f"les paires se chevauchent, le simulé fait foi.")
        lab.record(tok2, observed=obs["S2 corr"], null=n2,
                   power_at=f"règle à seuil O>7->rémanence d : 50 % entre d={env_rule} et "
                            f"le cran supérieur pour S3 ; S2 suit plus tard (grille {GRID_RULE}) ; "
                            f"S2 AVEUGLE par construction à l'hétéroscédasticité conditionnelle "
                            f"(z≈0 sur toute la grille {GRID_VC})",
                   verdict=verdicts["S2 corr"],
                   notes=f"70 558 paires de recouvrements successifs ; null sd {n2.sd:.5f} "
                         f"contre 1/sqrt(n)={1 / np.sqrt(N - 2):.5f}.")
        lab.record(tok3, observed=obs["S3 IM"], null=n3,
                   power_at=f"hétéroscédasticité conditionnelle (corr nulle par construction) : "
                            f"50 % entre delta={env_vc} et le cran supérieur ; règle à seuil : "
                            f"50 % entre d={env_rule} et le cran supérieur "
                            f"({REPS_POWER} réplicats)",
                   verdict=verdicts["S3 IM"],
                   notes=f"IM plug-in 7 classes ; biais plug-in MESURÉ : null "
                         f"{n3.mean:.2e}±{n3.sd:.1e} bit contre 0 théorique naïf "
                         f"(théorie (K-1)²/(2Nln2)={bias_th:.2e}) — lu contre 0 le null "
                         f"vaudrait déjà z=+{n3.mean / n3.sd:.1f} : le null simulé à même "
                         f"taille est ce qui évite le faux signal.")
        lab.record(tok4, observed=hits_r - K / 4, null=None, p=None,
                   power_at=f"témoin positif (règle à seuil) : modèle z>=3 dès d≈{d_detect} "
                            f"(oracle {ctrl_rows[-1][2]:.3f} hits à d={GRID_MODEL[-1]}, part captée "
                            f"{ctrl_rows[-1][5]:.0%}) ; témoin négatif SRS : {h_neg:.4f} hits (z={z_neg:+.2f})",
                   verdict="aucun avantage" if abs(z_r) < 3 else "à réexaminer",
                   notes=f"hits {hits_r:.4f} contre 2,5000, z = {z_r:+.2f}, "
                         f"log10(e) = {loge_r:.1f} sur {n_r} tirages ; gradient boosting "
                         f"6 traits entiers (lags 1-3, O lag1, O lag2, fenêtre 10), "
                         f"points de contrôle {CPS_REAL} ; leak_check propre ; accord "
                         f"bulk/causal exact (0.0).")

    # -- 7. synthèse --------------------------------------------------------
    print(f"\n{'=' * 78}\nSYNTHÈSE — la famille non linéaire, angle par angle")
    print(f"  {'angle':<44}{'observé':>12}{'z':>8}{'p':>8}")
    print(f"  {'1. forme de la loi de O (S1, 13 cases)':<44}"
          f"{obs['S1 hist']:>12.3f}{res['S1 hist'][0]:>+8.2f}{res['S1 hist'][1]:>8.3f}")
    print(f"  {'2a. corr recouvrements successifs (S2)':<44}"
          f"{obs['S2 corr']:>12.5f}{res['S2 corr'][0]:>+8.2f}{res['S2 corr'][1]:>8.3f}")
    print(f"  {'2b. IM recouvrements successifs (S3)':<44}"
          f"{obs['S3 IM']:>12.2e}{res['S3 IM'][0]:>+8.2f}{res['S3 IM'][1]:>8.3f}")
    print(f"  {'3. gradient boosting, marche avant':<44}"
          f"{hits_r:>12.4f}{z_r:>+8.2f}{'—':>8}")
    allz = [abs(res[k][0]) for k in res] + [abs(z_r)]
    msg = ("rien à signaler — la famille non linéaire est fermée aux sensibilités mesurées"
           if max(allz) < 3 else "VOIR CHASSE À L ARTEFACT AVANT TOUTE ANNONCE")
    print(f"\n{msg}.")
    print(f"{'(dry run : rien consigné)' if DRY else 'consigné au registre (4 entrées).'} "
          f"total {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
