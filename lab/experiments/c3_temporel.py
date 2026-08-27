"""c3_temporel — covariables temporelles et périodicités : la 17e voie.

Question. `unix_utc` n'a jamais servi de COVARIABLE. Le §8 de l'audit a
regardé la structure des coupures, a2 les 10 premiers tirages après reprise,
a3 des ruptures franches dans l'ordre chronologique. Aucun ne voit une
MODULATION PÉRIODIQUE (charge serveur selon l'heure, cron à heure fixe,
week-end différent) : pas de rupture (a3 aveugle), pas de signature de
démarrage (a2 aveugle), invisible en agrégat (audit aveugle).

Structure temporelle (vérifiée par le script avant tout regard sur les
tirages ; ce sont des faits de covariable, pas des résultats) :
  - 70 560 tirages, pas de 300 s (12 tirages en retard de 1..5 s) ;
  - 346 sessions : 345 de 204 tirages, 06:05 -> 23:00 HEURE LOCALE
    Europe/Zurich ; la première (180 tirages) commence à 08:05 ;
  - les 2 gaps nocturnes != 25 500 s sont exactement les nuits de
    changement d'heure (2025-10-26 : 29 100 s ; 2026-03-29 : 21 900 s).
    L'horaire est donc ancré sur l'horloge LOCALE, pas sur UTC.
  Convention : Python `zoneinfo("Europe/Zurich")` sur les secondes unix —
  même base IANA que `enum Zurich` (Calendar grégorien, tz Europe/Zurich)
  dans Prophet/Models/Types.swift. Les deux transitions DST tombent juste.
  COROLLAIRE : le rang dans la session EST la position dans la journée
  locale (rang r <=> créneau r-1 après 06:05, sauf la 1re session, décalée
  de 24 créneaux). La covariable `slot` (204 créneaux) couvre donc à la
  fois « rang de session » et « position fine dans la journée ».

Covariables (groupes fixes, dérivés de ts seulement — sous H0 le contenu
des tirages est SRS indépendant de l'horodatage) :
  heure   heure locale, 18 groupes (6..23 ; 23 = le seul tirage de 23:00)
  jsem    jour de semaine local, 7 groupes (lundi=0)
  minute  minute dans l'heure (:00..:55), 12 groupes — détecteur de cron
  jmois   position dans le mois, 3 groupes (1-10, 11-20, 21-31)
  slot    créneau du jour = rang de session, 204 groupes

Statistiques conditionnées (4 par covariable, 20 tests) :
  champ   chi2 d'homogénéité des 80 fréquences entre groupes
          (attendu par cellule = n_g * total_n / N)
  ov1     B = somme_g n_g (m_g - m.)^2 du recouvrement lag-1, paires
          intra-session seulement (les 345 paires trans-coupure exclues)
  somme   même B sur la somme des 20 numéros — contraste directionnel,
          plus puissant qu'un chi2 dilué sur 79 ddl
  boost   chi2 d'homogénéité boost (6 catégories) x groupes ; null =
          boost iid loi empirique globale (RNG dérivé du masque, cf. a2)

Périodicité pure (3 tests, chaque max calibré contre LA LOI DU MAX du
même balayage — jamais contre un seuil de test unique, leçon de a3) :
  spectre_fft_somme    max des 35 280 ordonnées du périodogramme FFT
                       (domaine indice) de la somme centrée / variance
  spectre_cible_somme  max sur 6 périodes {6, 8, 12, 24, 84, 168 h} du
                       périodogramme temps-réel exp(-2i.pi.ts/P)
  spectre_fft_ov1      idem FFT sur le recouvrement lag-1 intra-session
                       (70 214 points concaténés)

Nulls : simulés (SRS 20/80, archives complètes de 70 560 tirages). Les 23
statistiques sont évaluées sur les MÊMES archives simulées
(`calibrate_many`, même contrat que lab.calibrate : chaque null marginal a
exactement la loi que lab.calibrate produirait ; le partage évite 23 x 400
générations d'archives). Aucune espérance à la main ; les contrôles
analytiques imprimés ne servent qu'à vérifier que le null simulé tombe
dessus.

Puissance : mesurée pour CHAQUE test (lab.power ou boucle même contrat) ;
livrable central = la courbe amplitude -> détection d'une modulation
sinusoïdale de la somme (période 24 h et 168 h), amplitude MESURÉE en
points de somme (sd de la somme sous H0 ~ 90).

Multiplicité : 23 tests consignés individuellement ; les balayages
internes (35 280 ordonnées, 6 périodes, 204 groupes) sont absorbés par la
calibration de leur max — la statistique préenregistrée EST le max, donc
pas de m_extra (précédent a3). Seuil final : Holm registre entier.

Usage :
    python3 c3_temporel.py --dry     # machinerie sur données synthétiques,
                                     # réplicats réduits, AUCUNE écriture
    python3 c3_temporel.py --fast    # réplicats réduits, pas d'écriture
    python3 c3_temporel.py           # run réel : pré-enregistre, calibre,
                                     # mesure la puissance, observe, consigne
"""

from __future__ import annotations

import datetime
import hashlib
import os
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab

DRY = "--dry" in sys.argv
FAST = "--fast" in sys.argv
NO_RECORD = DRY or FAST
POOL, DRAWN = lab.POOL, lab.DRAWN
ALPHA_Z = 3.0
R_NULL = 60 if (DRY or FAST) else 400
R_POWER = 6 if (DRY or FAST) else 40
R_POWER_SLOW = 4 if (DRY or FAST) else 30
R_POWER_BOOST = 50 if (DRY or FAST) else 400

TZ = ZoneInfo("Europe/Zurich")
W_SUM = np.arange(1, POOL + 1, dtype=np.float64)
PERIODS_H = (6.0, 8.0, 12.0, 24.0, 84.0, 168.0)          # heures
PERIODS_S = tuple(3600.0 * h for h in PERIODS_H)

t_script = time.time()

# --------------------------------------------------------------------------
# 1. Structure temporelle et covariables — dérivées de ts uniquement
# --------------------------------------------------------------------------

a = lab.load()
N = len(a)
d = np.diff(a.ts)
res = np.where(d > 600)[0] + 1
assert N == 70560 and len(res) == 345

_loc = [datetime.datetime.fromtimestamp(int(t), TZ) for t in a.ts]
loc_sec = np.array([dt.hour * 3600 + dt.minute * 60 + dt.second for dt in _loc])
g_heure = np.array([dt.hour for dt in _loc]) - 6                  # 0..17
g_jsem = np.array([dt.weekday() for dt in _loc])                  # 0..6
g_minute = (loc_sec % 3600) // 300                                # 0..11
g_jmois = np.minimum((np.array([dt.day for dt in _loc]) - 1) // 10, 2)
g_slot = (loc_sec - (6 * 3600 + 300)) // 300                      # 0..203

# rang dans la session (détection a2 : gap > 600 s)
sess_start = np.zeros(N, np.int64)
sess_start[res] = 1
sess_id = np.cumsum(sess_start)
rank = np.arange(N) - np.concatenate([[0], res])[sess_id]         # 0-based

assert g_heure.min() == 0 and g_heure.max() == 17
assert g_slot.min() == 0 and g_slot.max() == 203
# rang == slot pour toutes les sessions sauf la première (décalée de 24)
same = (rank == g_slot)
assert same[res[0]:].all() and (g_slot[:res[0]] - rank[:res[0]] == 24).all()

GROUPINGS = {
    "heure":  (g_heure, 18),
    "jsem":   (g_jsem, 7),
    "minute": (g_minute, 12),
    "jmois":  (g_jmois, 3),
    "slot":   (g_slot, 204),
}

valid_pair = d <= 600                       # (N-1,) paire (t, t+1) intra-session
N_PAIRS = int(valid_pair.sum())             # 70 214

BOOST_CATS = np.array(sorted(np.unique(a.boost)))                 # [1,2,3,4,5,10]
NCAT = len(BOOST_CATS)
P_BOOST = np.array([(a.boost == c).mean() for c in BOOST_CATS])
real_bcat = np.searchsorted(BOOST_CATS, a.boost)

print("=" * 76)
print("STRUCTURE TEMPORELLE (covariables seulement — aucun contenu de tirage lu)")
print("=" * 76)
print(f"tirages {N}   sessions {len(res)+1}   paires intra-session {N_PAIRS}")
odd = np.where((d > 600) & (d != 25500))[0]
for i in odd:
    print(f"  gap != 25500 s : {d[i]} s, nuit du "
          f"{_loc[i].date()} -> {_loc[i+1].date()} (changement d'heure)")
print("comptes par groupe :")
for name, (g, G) in GROUPINGS.items():
    c = np.bincount(g, minlength=G)
    print(f"  {name:7s} G={G:3d}  n_g min/med/max = {c.min()}/{int(np.median(c))}/{c.max()}")
print(f"loi empirique du boost {BOOST_CATS.tolist()} : {np.round(P_BOOST, 4).tolist()}")

# --------------------------------------------------------------------------
# 2. Statistiques — prep(mask) partagé, stat(mask) individuel (contrat lab)
# --------------------------------------------------------------------------

def _mask_rng(mask: np.ndarray) -> np.random.Generator:
    seed = int.from_bytes(hashlib.sha256(mask.tobytes()).digest()[:8], "little")
    return np.random.default_rng(seed)


_ORD = {name: np.argsort(g, kind="stable") for name, (g, _) in GROUPINGS.items()}
_BND = {name: np.searchsorted(GROUPINGS[name][0][_ORD[name]], np.arange(GROUPINGS[name][1]))
        for name in GROUPINGS}
_CNT = {name: np.bincount(g, minlength=G) for name, (g, G) in GROUPINGS.items()}

_E_TARG = np.exp(-2j * np.pi * a.ts[None, :] / np.array(PERIODS_S)[:, None])


def prep(mask: np.ndarray) -> dict:
    """Primitives partagées par les 23 statistiques. `bcat` est le boost
    SIMULÉ sous H0 (iid loi empirique, RNG dérivé du masque) — l'observé
    le remplace par le boost réel."""
    mi = mask.astype(np.int32)
    sums = mi @ W_SUM
    ov = (mask[1:] & mask[:-1]).sum(1).astype(np.float64)
    bcat = _mask_rng(mask).choice(NCAT, size=len(mask), p=P_BOOST)
    return {"mask": mask, "mi": mi, "sums": sums, "ov": ov, "bcat": bcat}


def champ_from_prep(name):
    order, bnd, cnt = _ORD[name], _BND[name], _CNT[name]
    def f(p):
        C = np.add.reduceat(p["mi"][order], bnd, axis=0).astype(np.float64)
        e = cnt[:, None] * (C.sum(0)[None, :] / N)
        return float(((C - e) ** 2 / e).sum())
    return f


def _between_ss(vals, g, G):
    cnt = np.bincount(g, minlength=G).astype(np.float64)
    s = np.bincount(g, weights=vals, minlength=G)
    m = vals.mean()
    nz = cnt > 0
    return float((cnt[nz] * (s[nz] / cnt[nz] - m) ** 2).sum())


def somme_from_prep(name):
    g, G = GROUPINGS[name]
    def f(p):
        return _between_ss(p["sums"], g, G)
    return f


def ov1_from_prep(name):
    g, G = GROUPINGS[name]
    gp = g[1:][valid_pair]                  # groupe du tirage aval de la paire
    def f(p):
        return _between_ss(p["ov"][valid_pair], gp, G)
    return f


def _boost_chi2(bcat, g, G):
    K = np.bincount(g * NCAT + bcat, minlength=G * NCAT).reshape(G, NCAT).astype(float)
    e = K.sum(1)[:, None] * (K.sum(0)[None, :] / len(bcat))
    nz = e > 0
    return float(((K - e)[nz] ** 2 / e[nz]).sum())


def boost_from_prep(name):
    g, G = GROUPINGS[name]
    def f(p):
        return _boost_chi2(p["bcat"], g, G)
    return f


def fft_max_from_prep(key):
    def f(p):
        x = p[key][valid_pair] if key == "ov" else p[key]
        x = x - x.mean()
        I = np.abs(np.fft.rfft(x)[1:]) ** 2 / len(x)
        return float(I.max() / x.var())
    return f


def cible_from_prep(p):
    x = p["sums"] - p["sums"].mean()
    T = np.abs(_E_TARG @ x) ** 2 / (N * x.var())
    return float(T.max())


FNS: dict[str, callable] = {}
for _name in GROUPINGS:
    FNS[f"c3.{_name}_champ"] = champ_from_prep(_name)
    FNS[f"c3.{_name}_ov1"] = ov1_from_prep(_name)
    FNS[f"c3.{_name}_somme"] = somme_from_prep(_name)
    FNS[f"c3.{_name}_boost"] = boost_from_prep(_name)
FNS["c3.spectre_fft_somme"] = fft_max_from_prep("sums")
FNS["c3.spectre_cible_somme"] = cible_from_prep
FNS["c3.spectre_fft_ov1"] = fft_max_from_prep("ov")


def make_stat(tid):
    """stat(mask) -> scalaire, contrat lab.calibrate / lab.power."""
    fn = FNS[tid]
    return lambda mask: fn(prep(mask))


# --------------------------------------------------------------------------
# 3. Contaminations — défauts d'amplitude connue et MESURÉE
# --------------------------------------------------------------------------

RAMP = (np.arange(1, POOL + 1) - 40.5) / 39.5            # [-1, 1], favorise le haut


def weighted_rows(lw: np.ndarray, rng) -> np.ndarray:
    """Tirages 20/80 pondérés sans remise (Gumbel top-20), lw (n,80)."""
    keys = lw + rng.gumbel(size=lw.shape)
    out = np.zeros(lw.shape, bool)
    idx = np.argpartition(-keys, DRAWN, axis=1)[:, :DRAWN]
    np.put_along_axis(out, idx, True, axis=1)
    return out


def measure_shift(gamma: float, m: int = 40000, seed: int = 4242) -> float:
    """Décalage de E[somme] induit par lw = gamma*RAMP — mesuré, pas supposé."""
    rng = np.random.default_rng(seed)
    lw = np.broadcast_to(gamma * RAMP, (m, POOL)).copy()
    return float((weighted_rows(lw, rng) @ W_SUM).mean()
                 - (lab.srs(m, np.random.default_rng(seed + 1)) @ W_SUM).mean())


def gamma_for_shift(target: float) -> tuple[float, float]:
    lo, hi = 0.0, 1.5
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if measure_shift(mid) < target:
            lo = mid
        else:
            hi = mid
    g = 0.5 * (lo + hi)
    return g, measure_shift(g, m=120000)


def contaminate_sin(gamma: float, period_s: float):
    """Modulation sinusoïdale de la somme : lw(t,n) = gamma*sin(2pi ts/P)*RAMP.
    Amplitude crête en points de somme = measure_shift(gamma)."""
    s = np.sin(2 * np.pi * a.ts / period_s)
    def f(mask, rng):
        mask[:] = weighted_rows(gamma * s[:, None] * RAMP[None, :], rng)
        return mask
    return f


def contaminate_shift_group(gamma: float, name: str, choices):
    """Décalage constant de la somme dans UN groupe (choisi au hasard)."""
    g, _ = GROUPINGS[name]
    def f(mask, rng):
        rows = np.flatnonzero(g == rng.choice(choices))
        lw = np.broadcast_to(gamma * RAMP, (len(rows), POOL)).copy()
        mask[rows] = weighted_rows(lw, rng)
        return mask
    return f


def contaminate_pool_group(pool_size: int, name: str, choices):
    """Les tirages d'UN groupe (au hasard) puisent dans un pool réduit."""
    g, _ = GROUPINGS[name]
    def f(mask, rng):
        rows = np.flatnonzero(g == rng.choice(choices))
        pool_idx = rng.choice(POOL, pool_size, replace=False)
        keys = rng.random((len(rows), pool_size))
        idx = np.argpartition(-keys, DRAWN, axis=1)[:, :DRAWN]
        sub = np.zeros((len(rows), POOL), bool)
        for r in range(len(rows)):          # n_rows petit ou moyen ; simple
            sub[r, pool_idx[idx[r]]] = True
        mask[rows] = sub
        return mask
    return f


def _force_row(mask, t, j, rng):
    prev = np.flatnonzero(mask[t - 1])
    keep = rng.choice(prev, j, replace=False)
    other = np.setdiff1d(np.arange(POOL), prev, assume_unique=True)
    mask[t] = False
    mask[t, keep] = True
    mask[t, rng.choice(other, DRAWN - j, replace=False)] = True


def contaminate_ov_group(j: int, frac: float, name: str, choices):
    """Recouvrement lag-1 forcé à j sur une fraction frac des paires d'UN
    groupe : m_g passe de 5 à 5 + frac*(j-5)."""
    g, _ = GROUPINGS[name]
    ok = np.concatenate([[False], valid_pair])
    def f(mask, rng):
        for t in np.flatnonzero((g == rng.choice(choices)) & ok):
            if rng.random() < frac:
                _force_row(mask, int(t), j, rng)
        return mask
    return f


def contaminate_ov_sin(beta: float, period_s: float, j: int = 6):
    """P(paire forcée à j) = beta*(1+sin(2pi ts/P))/2 : le recouvrement
    moyen oscille avec une amplitude beta/2*(j-5)."""
    pt = beta * (1 + np.sin(2 * np.pi * a.ts / period_s)) / 2
    ok = np.concatenate([[False], valid_pair])
    def f(mask, rng):
        for t in np.flatnonzero(ok & (rng.random(N) < pt)):
            _force_row(mask, int(t), j, rng)
        return mask
    return f


def sim_boost_stuck(eps: float, name: str, choices):
    """simulate(rng) -> stat contaminée (contrat custom_power de a2) :
    boost iid global, mais collé à 1 avec prob eps dans UN groupe."""
    g, G = GROUPINGS[name]
    def f(rng):
        bcat = rng.choice(NCAT, size=N, p=P_BOOST)
        rows = (g == rng.choice(choices)) & (rng.random(N) < eps)
        bcat[rows] = 0
        return _boost_chi2(bcat, g, G)
    return f


# --------------------------------------------------------------------------
# 4. Pré-enregistrement — AVANT tout calcul d'observé
# --------------------------------------------------------------------------

DECISION = ("z du null simulé ; drapeau si |z| >= 3 ; candidate si p <= plancher "
            f"1/(R+1)={1/(R_NULL+1):.2e} (recalibrer avant toute déclaration) ; "
            "significatif seulement si p <= seuil Holm du registre entier (~1,54e-05)")
NM_SHARED = (f"calibrate_many : SRS 20/80, archives complètes N={N}, R={R_NULL} "
             "réplicats partagés entre les 23 stats (même loi marginale que "
             "lab.calibrate ; aucune espérance à la main)")

COV_DESC = {
    "heure":  "l'heure locale Europe/Zurich (18 groupes, 6..23)",
    "jsem":   "le jour de semaine local (7 groupes)",
    "minute": "la minute dans l'heure :00..:55 (12 groupes — tâche cron)",
    "jmois":  "la position dans le mois (3 groupes 1-10/11-20/21-31)",
    "slot":   "le créneau du jour = rang de session (204 groupes de ~346)",
}
STAT_DESC = {
    "champ": ("chi2 d'homogénéité des 80 fréquences entre groupes",
              "la loi des 80 numéros dépend de"),
    "ov1":   ("B = somme_g n_g (m_g - m.)^2 du recouvrement lag-1 "
              "(paires intra-session)", "la dépendance sérielle dépend de"),
    "somme": ("B = somme_g n_g (m_g - m.)^2 de la somme des 20 numéros",
              "la somme moyenne (contraste bas/haut) dépend de"),
    "boost": ("chi2 d'homogénéité boost (6 cat.) x groupes ; null = boost iid "
              "loi empirique (RNG dérivé du masque)", "la loi du boost dépend de"),
}

TESTS = []
for _name in GROUPINGS:
    for _st, (_sdesc, _hverb) in STAT_DESC.items():
        TESTS.append((f"c3.{_name}_{_st}",
                      f"{_hverb} {COV_DESC[_name]}",
                      _sdesc + f" ; covariable {_name}",
                      NM_SHARED))
TESTS += [
    ("c3.spectre_fft_somme",
     "Une périodicité de la somme des 20 numéros à une période quelconque "
     "(domaine indice : 204 = journée locale, 1428 = semaine, etc.)",
     "max des 35 280 ordonnées du périodogramme FFT de la somme centrée, "
     "normalisé par la variance", NM_SHARED + " ; null = loi du MAX du balayage"),
    ("c3.spectre_cible_somme",
     "Une périodicité de la somme aux périodes physiques {6, 8, 12, 24, 84, "
     "168 h} en temps réel (charge serveur, cycles quotidien/hebdomadaire)",
     "max sur 6 périodes de |somme_t x_t exp(-2i.pi.ts_t/P)|^2/(N var), "
     "horodatages réels", NM_SHARED + " ; null = loi du MAX des 6 ordonnées"),
    ("c3.spectre_fft_ov1",
     "Une périodicité du recouvrement lag-1 (rémanence d'état modulée)",
     "max des 35 107 ordonnées du périodogramme FFT du recouvrement lag-1 "
     "intra-session centré (70 214 points)", NM_SHARED + " ; null = loi du MAX"),
]

print()
print("=" * 76)
print("PRE-ENREGISTREMENT" + ("  [DRY/FAST : jetons calculés, rien ne sera consigné]"
                              if NO_RECORD else ""))
print("=" * 76)
tokens = {}
for tid, hyp, statd, nulld in TESTS:
    tok = lab.preregister(tid, hyp, statd, nulld, DECISION, track="A")
    tokens[tid] = tok
    print(f"  {tid:26s} seal={tok['seal']}")

# --------------------------------------------------------------------------
# 5. Nulls simulés — réplicats partagés, contrôles analytiques imprimés
# --------------------------------------------------------------------------

def calibrate_many(reps: int, seed: int = 2026) -> dict[str, lab.Null]:
    """Même contrat que lab.calibrate (SRS via lab.srs, Null identique),
    mais les 23 stats sont évaluées sur les MÊMES archives simulées."""
    rng = np.random.default_rng(seed)
    vals = {tid: np.empty(reps) for tid in FNS}
    for r in range(reps):
        p = prep(lab.srs(N, rng))
        for tid, fn in FNS.items():
            vals[tid][r] = fn(p)
        if (r + 1) % max(1, reps // 8) == 0:
            print(f"  null {r + 1}/{reps}  ({time.time()-t_script:.0f} s)", flush=True)
    return {tid: lab.Null(float(v.mean()), float(v.std(ddof=1)), reps, v)
            for tid, v in vals.items()}


# contrôles analytiques (JAMAIS utilisés comme null — vérification seulement)
VAR_SUM = 20 * ((POOL ** 2 - 1) / 12) * (POOL - DRAWN) / (POOL - 1)     # 8100
VAR_OV = DRAWN * (DRAWN / POOL) * (1 - DRAWN / POOL) * (POOL - DRAWN) / (POOL - 1)
ANALYTIC = {}
for _name, (_g, _G) in GROUPINGS.items():
    ANALYTIC[f"c3.{_name}_somme"] = (_G - 1) * VAR_SUM
    ANALYTIC[f"c3.{_name}_ov1"] = (_G - 1) * VAR_OV

print()
print("=" * 76)
print(f"CALIBRATION DES NULLS ({R_NULL} archives SRS complètes, partagées)")
print("=" * 76)
t0 = time.time()
nulls = calibrate_many(R_NULL)
print(f"  ({time.time()-t0:.0f} s)")
for tid in FNS:
    nl = nulls[tid]
    ctrl = f"  [contrôle analytique ~{ANALYTIC[tid]:.0f}]" if tid in ANALYTIC else ""
    print(f"  {tid:26s} null = {nl.mean:12.2f} +/- {nl.sd:10.2f}{ctrl}")

# --------------------------------------------------------------------------
# 6. Puissance mesurée — chaque test a la sienne
# --------------------------------------------------------------------------

print()
print("=" * 76)
print(f"PUISSANCE (fraction des réplicats contaminés détectés, |z|>={ALPHA_Z:.0f} ; "
      f"reps={R_POWER}/{R_POWER_SLOW} — réduits pour tenir en ~10 min, dit ici)")
print("=" * 76)

print("calibration gamma -> décalage de somme mesuré :")
SHIFTS = {}
for A in (1.0, 2.0, 4.0, 8.0, 40.0):
    g_, meas = gamma_for_shift(A)
    SHIFTS[A] = (g_, meas)
    print(f"  cible {A:5.1f} pts : gamma={g_:.4f}, mesuré {meas:+.2f} pts "
          f"({meas/np.sqrt(VAR_SUM)*100:+.2f} % sd)")


def power_many(tids: list[str], contaminate, reps: int, seed: int) -> dict[str, float]:
    """Même contrat que lab.power, détecteurs multiples sur les mêmes
    réplicats contaminés."""
    rng = np.random.default_rng(seed)
    hits = {t: 0 for t in tids}
    for _ in range(reps):
        p = prep(contaminate(lab.srs(N, rng), rng))
        for t in tids:
            if abs(nulls[t].z(FNS[t](p))) >= ALPHA_Z:
                hits[t] += 1
    return {t: h / reps for t, h in hits.items()}


def custom_power(simulate, null, reps: int, seed: int = 1) -> float:
    rng = np.random.default_rng(seed)
    return sum(abs(null.z(simulate(rng))) >= ALPHA_Z for _ in range(reps)) / reps


power_notes: dict[str, list[str]] = {tid: [] for tid in FNS}

# --- 6a. LIVRABLE CENTRAL : modulation sinusoïdale, courbe amplitude->détection
SIN_DETECT = ["c3.spectre_cible_somme", "c3.spectre_fft_somme", "c3.heure_somme"]
print("\nModulation sinusoïdale 24 h de la somme (amplitude crête, pts de somme) :")
print("  A (pts) |  " + "  ".join(f"{t.split('.')[1]:>18s}" for t in SIN_DETECT))
curve_24 = {}
for A in (1.0, 2.0, 4.0, 8.0):
    pw = power_many(SIN_DETECT, contaminate_sin(SHIFTS[A][0], 86400.0),
                    R_POWER, seed=int(1000 + A * 10))
    curve_24[A] = pw
    for t in SIN_DETECT:
        power_notes[t].append(f"sin24h A={SHIFTS[A][1]:.1f}pts: {pw[t]:.2f}")
    print(f"  {SHIFTS[A][1]:7.1f} |  " + "  ".join(f"{pw[t]:18.2f}" for t in SIN_DETECT),
          flush=True)

SIN_W_DETECT = ["c3.spectre_cible_somme", "c3.jsem_somme"]
print("\nModulation sinusoïdale 168 h (hebdomadaire) de la somme :")
curve_168 = {}
for A in (1.0, 2.0, 4.0):
    pw = power_many(SIN_W_DETECT, contaminate_sin(SHIFTS[A][0], 604800.0),
                    R_POWER, seed=int(2000 + A * 10))
    curve_168[A] = pw
    for t in SIN_W_DETECT:
        power_notes[t].append(f"sin168h A={SHIFTS[A][1]:.1f}pts: {pw[t]:.2f}")
    print("  A=" + f"{SHIFTS[A][1]:5.1f} pts : " +
          "  ".join(f"{t.split('.')[1]}={pw[t]:.2f}" for t in SIN_W_DETECT), flush=True)

# --- 6b. champ conditionné : pool réduit dans UN groupe
POOL_PLAN = [("heure", (78, 76, 72), tuple(range(1, 17))),
             ("minute", (76, 72), tuple(range(12))),
             ("jmois", (76,), (0, 1, 2)),
             ("slot", (72, 60), tuple(range(24, 204))),
             ("jsem", (78, 76), tuple(range(7)))]
print("\nChamp conditionné — pool réduit dans un groupe (au hasard) :")
for name, pools, choices in POOL_PLAN:
    tid = f"c3.{name}_champ"
    for ps in pools:
        pw = lab.power(make_stat(tid), contaminate_pool_group(ps, name, choices),
                       N, nulls[tid], reps=R_POWER, seed=300 + ps, alpha_z=ALPHA_Z)
        power_notes[tid].append(f"pool {ps}/80 dans 1 groupe: {pw:.2f}")
        print(f"  {tid:22s} pool {ps}/80 : {pw:.2f}", flush=True)

# --- 6c. ov1 conditionné : recouvrement forcé dans UN groupe
OV_PLAN = [("heure", ((6, 0.25), (6, 0.5))), ("jsem", ((6, 0.25),)),
           ("minute", ((6, 0.25),)), ("jmois", ((6, 0.10),)), ("slot", ((8, 1.0),))]
print("\nOv1 conditionné — recouvrement forcé dans un groupe :")
for name, pts in OV_PLAN:
    tid = f"c3.{name}_ov1"
    choices = tuple(range(1, 17)) if name == "heure" else (
        tuple(range(24, 204)) if name == "slot" else tuple(range(GROUPINGS[name][1])))
    for j, frac in pts:
        pw = lab.power(make_stat(tid), contaminate_ov_group(j, frac, name, choices),
                       N, nulls[tid], reps=R_POWER_SLOW,
                       seed=int(500 + 10 * j + frac * 100), alpha_z=ALPHA_Z)
        power_notes[tid].append(f"ov force j={j} frac={frac} (dm={frac*(j-5):+.2f}): {pw:.2f}")
        print(f"  {tid:22s} j={j} frac={frac} (delta m_g={frac*(j-5):+.2f}) : {pw:.2f}",
              flush=True)

# --- 6d. somme conditionnée : décalage constant dans UN groupe
SHIFT_PLAN = [("heure", (4.0, 8.0)), ("jsem", (4.0, 8.0)), ("minute", (4.0, 8.0)),
              ("jmois", (2.0, 4.0)), ("slot", (8.0, 40.0))]
print("\nSomme conditionnée — décalage constant dans un groupe :")
for name, amps in SHIFT_PLAN:
    tid = f"c3.{name}_somme"
    choices = tuple(range(1, 17)) if name == "heure" else (
        tuple(range(24, 204)) if name == "slot" else tuple(range(GROUPINGS[name][1])))
    for A in amps:
        pw = lab.power(make_stat(tid), contaminate_shift_group(SHIFTS[A][0], name, choices),
                       N, nulls[tid], reps=R_POWER, seed=int(700 + A), alpha_z=ALPHA_Z)
        power_notes[tid].append(f"shift {SHIFTS[A][1]:+.1f}pts dans 1 groupe: {pw:.2f}")
        print(f"  {tid:22s} decalage {SHIFTS[A][1]:+.1f} pts : {pw:.2f}", flush=True)

# --- 6e. boost conditionné : collage à 1 dans UN groupe (contrat a2)
print("\nBoost conditionné — collé à 1 avec prob eps dans un groupe :")
for name in GROUPINGS:
    tid = f"c3.{name}_boost"
    choices = tuple(range(GROUPINGS[name][1]))
    for eps in (0.02, 0.05) if name in ("jsem", "jmois") else (0.05, 0.10):
        pw = custom_power(sim_boost_stuck(eps, name, choices), nulls[tid],
                          reps=R_POWER_BOOST, seed=int(900 + eps * 100))
        power_notes[tid].append(f"boost->1 eps={eps} dans 1 groupe: {pw:.2f}")
        print(f"  {tid:22s} eps={eps} : {pw:.2f}", flush=True)

# --- 6f. périodicité du recouvrement
print("\nSpectre ov1 — probabilité de répétition modulée à 24 h :")
for beta in (0.2, 0.4):
    tid = "c3.spectre_fft_ov1"
    pw = lab.power(make_stat(tid), contaminate_ov_sin(beta, 86400.0), N, nulls[tid],
                   reps=R_POWER_SLOW, seed=int(1100 + beta * 10), alpha_z=ALPHA_Z)
    power_notes[tid].append(f"P(repet) module 24h beta={beta} (ampl {beta/2:.2f} ov): {pw:.2f}")
    print(f"  {tid:22s} beta={beta} (amplitude {beta/2:.2f} pt d'overlap) : {pw:.2f}",
          flush=True)

# --------------------------------------------------------------------------
# 7. Observés — construits SEULEMENT maintenant
# --------------------------------------------------------------------------

print()
print("=" * 76)
print("OBSERVES" + ("  [DRY : archive remplacée par du SRS synthétique]" if DRY else ""))
print("=" * 76)

if DRY:
    _rng = np.random.default_rng(31337)
    obs_prep = prep(lab.srs(N, _rng))
    obs_prep["bcat"] = _rng.choice(NCAT, size=N, p=P_BOOST)
else:
    obs_prep = prep(a.mask)
    obs_prep["bcat"] = real_bcat            # boost REEL pour les tests boost

observed = {tid: fn(obs_prep) for tid, fn in FNS.items()}

# tables descriptives (contexte du rapport, non consignées)
print("\n  contexte par heure locale (somme moy., ov1 moy., E[boost]) :")
sums_o, ov_o = obs_prep["sums"], obs_prep["ov"]
gp_h = g_heure[1:][valid_pair]
for h in range(18):
    sel = g_heure == h
    ovm = ov_o[valid_pair][gp_h == h].mean() if (gp_h == h).any() else float("nan")
    print(f"    {h+6:02d}h  n={sel.sum():5d}  somme={sums_o[sel].mean():7.2f}"
          f"  ov1={ovm:6.3f}  boost={BOOST_CATS[obs_prep['bcat'][sel]].mean():6.3f}")
print("\n  contexte par jour de semaine :")
for j, nom in enumerate(["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]):
    sel = g_jsem == j
    print(f"    {nom}  n={sel.sum():5d}  somme={sums_o[sel].mean():7.2f}"
          f"  boost={BOOST_CATS[obs_prep['bcat'][sel]].mean():6.3f}")
x_ = sums_o - sums_o.mean()
I_ = np.abs(np.fft.rfft(x_)[1:]) ** 2 / N / x_.var()
top = np.argsort(I_)[-5:][::-1] + 1
print("\n  top-5 ordonnées FFT de la somme (période en tirages ; 204 = 1 jour) :")
for k in top:
    print(f"    k={k:5d}  période={N/k:9.1f} tirages  I/var={I_[k-1]:6.2f}")

# --------------------------------------------------------------------------
# 8. Verdicts + registre
# --------------------------------------------------------------------------

print()
print("=" * 76)
print("RESULTATS")
print("=" * 76)
print(f"  {'test':26s} {'observé':>12s} {'null':>22s} {'z':>7s} {'p':>9s}")
already = {r["id"] for r in lab.ledger()}
n_flags = 0
for tid, _, _, _ in TESTS:
    nl, obs = nulls[tid], observed[tid]
    z, p = nl.z(obs), nl.p_two_sided(obs)
    flag = ""
    if abs(z) >= ALPHA_Z:
        n_flags += 1
        flag = "  <-- |z|>=3 : chercher d'abord l'artefact"
    print(f"  {tid:26s} {obs:>12.2f} {nl.mean:>12.2f}+/-{nl.sd:<9.2f} {z:>+7.2f} "
          f"{p:>9.2e}{flag}")
    if not NO_RECORD:
        if tid in already:
            print(f"    (registre : '{tid}' déjà présent — pas de doublon)")
            continue
        verdict = "conforme" if abs(z) < ALPHA_Z else "drapeau |z|>=3 — voir notes"
        lab.record(tokens[tid], obs, null=nl,
                   power_at=" | ".join(power_notes[tid]),
                   verdict=verdict,
                   notes=("covariables Europe/Zurich (zoneinfo, = enum Zurich de "
                          "Types.swift) ; horaire ancré heure LOCALE 06:05-23:00, "
                          "204 tirages/j ; slot == rang de session (1re session "
                          "décalée de 24) ; nulls partagés calibrate_many ; "
                          "balayages internes absorbés par la loi du max"))

if NO_RECORD:
    print("\n[DRY/FAST] Rien n'a été consigné au registre.")
else:
    sig = [r for r in lab.holm() if r["significant"]]
    m_tot = lab.holm()[0]["m_total"] if lab.holm() else 0
    print(f"\nHolm sur registre entier : {len(sig)} significatif(s), m_total={m_tot}.")
print(f"drapeaux |z|>=3 : {n_flags}/23")
print(f"\ntotal : {time.time()-t_script:.0f} s")
