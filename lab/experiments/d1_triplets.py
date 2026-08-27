"""D1 — Structure de troisième ordre : les 82 160 triplets de numéros.

Question. L'audit §2 a testé les 3 160 PAIRES (|z|max = 3,68, rien au seuil
de Bonferroni). Le troisième ordre n'a jamais été regardé : C(80,3) = 82 160
triplets, un espace 26 fois plus grand. Un générateur peut avoir des
marginales et des paires parfaites avec une structure de triplets — c'est le
mode de défaillance des générateurs à faible discrépance (les hyperplans de
Marsaglia portent précisément sur la dimension 3 et au-delà). Sous H0 chaque
triplet apparaît ~979 fois sur 70 560 tirages : largement testable.

Comptage. Chaque tirage contient C(20,3) = 1 140 triplets ; 80,4 millions
d'incréments au total, vectorisés par encodage plat a*6400+b*80+c (a<b<c)
et np.bincount par blocs (~1,2 s par archive).

Trois statistiques, trois régimes de défaut :
  max    : max de |z| sur les 82 160 comptes — anomalie LOCALISÉE (quelques
           triplets déviants). C'est un max de balayage : sa loi n'est PAS
           celle d'un z unique (leçon a3 : un max de 5,24 y valait p=0,066).
  sumsq  : somme des z^2 sur les 82 160 cases — structure DIFFUSE (beaucoup
           de cases légèrement déplacées). Les comptes ne sont PAS
           indépendants (deux triplets partageant deux numéros sont
           corrélés, et la somme des 82 160 comptes vaut EXACTEMENT
           1140*N) : un chi2 tabulé à 82 160 ddl serait faux. Null simulé.
  motif  : max de |z| sur 5 agrégats structurés — progressions
           arithmétiques (1 560 triplets), même dizaine (960), même parité
           (19 760), même reste mod 5 (2 800), mod 10 (560). Un défaut de
           discrépance produit un MOTIF, pas un bruit isolé ; agréger la
           famille est bien plus puissant que le max cellule à cellule.
           Le pilote mesure sd(AP) = ~900 contre 1 227 si les cases étaient
           indépendantes : la corrélation négative est forte, seule la
           simulation donne la bonne loi.

Standardisation : moments par cellule et par famille estimés sur M archives
SRS (jamais tabulés) ; les mêmes moments servent à l'observé et au null,
donc leur erreur d'estimation est neutralisée par construction. Les trois
nulls sortent d'UNE même passe de calibration sur R archives SRS complètes
(mêmes réplicats, trois statistiques collectées).

Puissance (obligatoire) : injection d'une sur-représentation d'amplitude
CONNUE — (a) 8 triplets disjoints forcés dans une fraction f des tirages
(excès par triplet = N*f*(1-p1)/8, connu exactement) ; (b) motif diffus :
un triplet AP aléatoire forcé dans une fraction f des tirages (excès agrégé
N*f réparti sur 1 560 cases, invisible au max) ; (c) un point témoin
« pool groupé » (40 numéros légèrement favorisés : 9 880 cases déplacées
d'une fraction de sigma chacune) pour montrer le régime où sumsq voit ce
que le max manque — témoin détectable d'abord par le chi2 marginal (voie
fermée), donné à titre de démonstration.

Usage : python3 d1_triplets.py [--fast] [--no-record]
  --fast      réplicats réduits (fumée), n'écrit PAS au registre
  --no-record calcule tout, n'écrit pas au registre
"""

from __future__ import annotations

import itertools
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
T = 82160                                  # C(80,3)
FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST

M_MOMENTS = 8 if FAST else 40              # archives SRS pour les moments
R_NULL = 30 if FAST else 300               # réplicats du null (3 stats, même passe)
R_POWER = 4 if FAST else 30                # réplicats par point de puissance

K_LOC = 8                                  # triplets disjoints sur-représentés
F_LOC = (0.005, 0.01, 0.015, 0.02, 0.04)   # fraction de tirages contaminés
F_AP = (0.01, 0.02, 0.04, 0.08)            # idem, motif AP diffus
FAV_DEMO = 40                              # numéros favorisés du témoin diffus
GAMMA_DEMO = 0.012                         # log-poids : 9 880 cases à ~+0,6 sigma

EXP_MAX = "d1.triplets_max"
EXP_SS = "d1.triplets_sumsq"
EXP_MOTIF = "d1.triplets_motif"

# --------------------------------------------------------------------------
# Comptage vectorisé des 82 160 triplets
# --------------------------------------------------------------------------

_COMBOS = np.array(list(itertools.combinations(range(20), 3)), np.int64)
_CI, _CJ, _CK = _COMBOS[:, 0], _COMBOS[:, 1], _COMBOS[:, 2]

_a, _b, _c = np.meshgrid(*(np.arange(80),) * 3, indexing="ij")
VALID = np.flatnonzero((_a < _b) & (_b < _c))            # (82160,) index plat
TA, TB, TC = VALID // 6400, (VALID // 80) % 80, VALID % 80   # décodage 0..79

FAMILIES = {
    "AP": (TB - TA) == (TC - TB),
    "dizaine": (TA // 10 == TB // 10) & (TB // 10 == TC // 10),
    "mod2": (TA % 2 == TB % 2) & (TB % 2 == TC % 2),
    "mod5": (TA % 5 == TB % 5) & (TB % 5 == TC % 5),
    "mod10": (TA % 10 == TB % 10) & (TB % 10 == TC % 10),
}
PATTERNS = dict(FAMILIES, consec=((TC - TA) == 2))       # diagnostic top-50


def triplet_counts(mask: np.ndarray, chunk: int = 4096) -> np.ndarray:
    """(82160,) comptes des triplets a<b<c sur l'archive. ~1,2 s."""
    n = len(mask)
    cols = np.nonzero(mask)[1].reshape(n, 20).astype(np.int32)  # triés par ligne
    counts = np.zeros(80 * 80 * 80, np.int64)
    for s in range(0, n, chunk):
        sl = cols[s:s + chunk]
        flat = (sl[:, _CI] * 6400 + sl[:, _CJ] * 80 + sl[:, _CK]).ravel()
        counts += np.bincount(flat, minlength=512000)
    return counts[VALID].astype(np.float64)


def trip_name(t: int) -> str:
    return f"{{{TA[t]+1},{TB[t]+1},{TC[t]+1}}}"


# --------------------------------------------------------------------------
# Moments simulés (règle 1 : rien de tabulé)
# --------------------------------------------------------------------------

def estimate_moments(m_reps: int, seed: int = 12345) -> dict:
    """mu/sd par cellule (mis en commun : les 82 160 cellules sont
    échangeables sous SRS) et mu/sd par famille structurée."""
    rng = np.random.default_rng(seed)
    sq_sum, mu_sum = 0.0, 0.0
    fam_sums = {k: [] for k in FAMILIES}
    for _ in range(m_reps):
        cnt = triplet_counts(lab.srs(N, rng))
        mu_sum += cnt.mean()
        sq_sum += ((cnt - cnt.mean()) ** 2).mean()
        for k, sel in FAMILIES.items():
            fam_sums[k].append(cnt[sel].sum())
    mu = mu_sum / m_reps                      # = 1140*N/82160, déterministe
    sd = float(np.sqrt(sq_sum / m_reps))
    fams = {k: (float(np.mean(v)), float(np.std(v, ddof=1)))
            for k, v in fam_sums.items()}
    return {"mu": float(mu), "sd": sd, "fams": fams}


class TripStat:
    """Les trois statistiques en une passe ; collecte pour la calibration.

    __call__ renvoie la primaire (max |z|) pour lab.calibrate ; en mode
    collect, sumsq, motif et le diagnostic top-50 de chaque réplicat sont
    gardés — les trois nulls sortent des MÊMES archives simulées.
    """

    def __init__(self, moments: dict):
        self.mo = moments
        self.collect = False
        self.rows: list[dict] = []
        self.last: dict | None = None

    def all(self, mask: np.ndarray) -> dict:
        cnt = triplet_counts(mask)
        z = (cnt - self.mo["mu"]) / self.mo["sd"]
        fam_z = {k: (cnt[FAMILIES[k]].sum() - self.mo["fams"][k][0])
                 / self.mo["fams"][k][1] for k in FAMILIES}
        top = np.argpartition(-np.abs(z), 50)[:50]
        vals = {
            "max": float(np.abs(z).max()),
            "sumsq": float((z ** 2).sum()),
            "motif": float(max(abs(v) for v in fam_z.values())),
            "fam_z": fam_z,
            "argmax": int(np.argmax(np.abs(z))),
            "z": z,
            "top50": {k: int(sel[top].sum()) for k, sel in PATTERNS.items()},
            "top50_pos": int((z[top] > 0).sum()),
        }
        return vals

    def __call__(self, mask: np.ndarray) -> float:
        v = self.all(mask)
        self.last = {k: v[k] for k in
                     ("max", "sumsq", "motif", "fam_z", "argmax", "top50", "top50_pos")}
        if self.collect:
            self.rows.append(self.last)
        return v["max"]


# --------------------------------------------------------------------------
# Contaminations — amplitude connue par construction
# --------------------------------------------------------------------------

def _force(mask: np.ndarray, rows: np.ndarray, trips: np.ndarray,
           rng: np.random.Generator) -> None:
    """Force trips[r] (3 numéros 0..79) dans mask[rows[r]], à 20 tirés."""
    for r, tr in zip(rows, trips):
        row = mask[r]
        missing = tr[~row[tr]]
        if missing.size == 0:
            continue
        removable = np.setdiff1d(np.flatnonzero(row), tr, assume_unique=True)
        row[rng.choice(removable, size=missing.size, replace=False)] = False
        row[missing] = True


def make_contaminate_loc(f: float):
    """K_LOC triplets disjoints (24 numéros), chacun forcé dans f/K_LOC des
    tirages : excès par triplet = N*f*(1-p1)/K_LOC, connu exactement."""
    def contaminate(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        trips = rng.choice(80, size=3 * K_LOC, replace=False).reshape(K_LOC, 3)
        rows = rng.choice(len(mask), size=int(round(f * len(mask))), replace=False)
        _force(mask, rows, trips[rng.integers(0, K_LOC, size=len(rows))], rng)
        return mask
    return contaminate


AP_TRIPS = np.stack([TA[FAMILIES["AP"]], TB[FAMILIES["AP"]],
                     TC[FAMILIES["AP"]]], axis=1)


def make_contaminate_ap(f: float):
    """Un triplet AP aléatoire (parmi 1 560) forcé dans f des tirages :
    excès agrégé ~N*f sur la famille AP, ~N*f/1560 par case — le max de
    cellule est aveugle par construction, le motif ne l'est pas."""
    def contaminate(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        rows = rng.choice(len(mask), size=int(round(f * len(mask))), replace=False)
        _force(mask, rows, AP_TRIPS[rng.integers(0, len(AP_TRIPS), size=len(rows))], rng)
        return mask
    return contaminate


def contaminate_pool(mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Témoin « pool groupé » : FAV_DEMO numéros au log-poids GAMMA_DEMO
    (Gumbel top-20). Excès diffus sur les C(FAV_DEMO,3) = 9 880 triplets du
    groupe, chacun déplacé d'une fraction de sigma — le max de cellule est
    aveugle par construction, sumsq agrège. Biais marginal MESURÉ, pas
    supposé."""
    fav = rng.choice(80, size=FAV_DEMO, replace=False)
    lw = np.zeros(80)
    lw[fav] = GAMMA_DEMO
    keys = lw + rng.gumbel(size=(len(mask), 80))
    idx = np.argpartition(-keys, 20, axis=1)[:, :20]
    out = np.zeros_like(mask)
    np.put_along_axis(out, idx, True, axis=1)
    return out


# --------------------------------------------------------------------------
# Expérience
# --------------------------------------------------------------------------

def main() -> None:
    t_start = time.time()
    a = lab.load()
    assert len(a) == N
    p1 = 20 * 19 * 18 / (80 * 79 * 78)     # P(triplet donné dans un tirage)

    # -- 1. Pré-enregistrement : AVANT tout regard sur le résultat -------
    common_null = (f"lab.calibrate sur archives SRS complètes de {N} tirages, "
                   f"R={R_NULL} réplicats partagés entre les trois stats ; moments "
                   f"par cellule/famille simulés sur M={M_MOMENTS} archives — les "
                   "82 160 comptes sont dépendants (somme exactement 1140*N, "
                   "triplets partageant 2 numéros corrélés), aucune loi tabulée "
                   "n'est valide")
    common_dec = (f"anomalie candidate si p empirique <= plancher 1/(R+1)="
                  f"{1/(R_NULL+1):.2e} (alors re-calibration à plus de réplicats "
                  "avant toute déclaration, seuil final = Holm registre ~1,5e-05) ; "
                  "sinon conforme")
    tok_max = lab.preregister(
        EXP_MAX,
        "Un petit nombre de triplets de numéros est sur/sous-représenté sur les "
        "70 560 tirages (anomalie localisée du 3e ordre, invisible aux marginales "
        "et aux 3 160 paires du §2)",
        statistic=("max de |z| sur les 82 160 comptes de triplets, z standardisé "
                   "par moments simulés mis en commun (cellules échangeables)"),
        null_method=common_null, decision=common_dec, track="A")
    tok_ss = lab.preregister(
        EXP_SS,
        "La distribution des 82 160 comptes de triplets est globalement "
        "sur-dispersée (structure diffuse du 3e ordre : beaucoup de triplets "
        "légèrement déplacés, aucun ne dépassant seul le seuil du max)",
        statistic="somme des z^2 sur les 82 160 comptes (chi2 de triplets, "
                  "loi simulée — jamais 82 160 ddl tabulés)",
        null_method=common_null, decision=common_dec, track="A")
    tok_motif = lab.preregister(
        EXP_MOTIF,
        "Les triplets déviants forment un MOTIF arithmétique (progression "
        "arithmétique, même dizaine, même reste mod 2/5/10) — signature d'un "
        "défaut de discrépance type hyperplans de Marsaglia",
        statistic=("max de |z| sur 5 agrégats de familles structurées : AP (1 560 "
                   "triplets), dizaine (960), mod2 (19 760), mod5 (2 800), "
                   "mod10 (560), moments simulés par famille"),
        null_method=common_null, decision=common_dec, track="A")
    for tok in (tok_max, tok_ss, tok_motif):
        print(f"pré-enregistré  id={tok['id']}  seal={tok['seal']}")
    print()

    # -- 2. Moments simulés ----------------------------------------------
    t0 = time.time()
    mo = estimate_moments(M_MOMENTS)
    stat = TripStat(mo)
    print(f"moments : M={M_MOMENTS} archives SRS, {time.time()-t0:.0f} s")
    print(f"  cellule : mu={mo['mu']:.3f}  sd={mo['sd']:.3f}  "
          f"(binomiale théorique {np.sqrt(N*p1*(1-p1)):.3f} — à titre indicatif)")
    for k, (fmu, fsd) in mo["fams"].items():
        n_indep = int(FAMILIES[k].sum())
        print(f"  famille {k:8s}: mu={fmu:12.0f}  sd={fsd:8.0f}  "
              f"(si indépendantes : {np.sqrt(n_indep)*mo['sd']:.0f})")

    # -- 3. Null des trois statistiques, une seule passe -----------------
    t0 = time.time()
    stat.collect = True
    null_max = lab.calibrate(stat, N, reps=R_NULL, seed=0)
    rows = stat.rows
    stat.collect, stat.rows = False, []
    ss_samples = np.array([r["sumsq"] for r in rows])
    mo_samples = np.array([r["motif"] for r in rows])
    null_ss = lab.Null(float(ss_samples.mean()), float(ss_samples.std(ddof=1)),
                       R_NULL, ss_samples)
    null_motif = lab.Null(float(mo_samples.mean()), float(mo_samples.std(ddof=1)),
                          R_NULL, mo_samples)
    print(f"\nnull ({R_NULL} archives SRS, {time.time()-t0:.0f} s) :")
    for name, nl in (("max", null_max), ("sumsq", null_ss), ("motif", null_motif)):
        q = np.quantile(nl.samples, [0.5, 0.9, 0.99])
        print(f"  {name:5s}: mean={nl.mean:12.3f} sd={nl.sd:10.3f}  "
              f"q50={q[0]:12.3f} q90={q[1]:12.3f} q99={q[2]:12.3f} "
              f"max={nl.samples.max():12.3f}")
    naive = 2.0 * T
    print(f"  (naïf : Var d'un chi2 à 82 160 ddl donnerait sd={np.sqrt(naive):.0f} "
          f"en unités z^2 ; le null simulé fait foi)")

    # -- 4. Observation ---------------------------------------------------
    obs = stat.all(a.mask)
    z_real = obs.pop("z")
    p_max = null_max.p_two_sided(obs["max"])
    p_ss = null_ss.p_two_sided(obs["sumsq"])
    p_motif = null_motif.p_two_sided(obs["motif"])

    print(f"\nobservé :")
    print(f"  max   |z| = {obs['max']:.3f}  (triplet {trip_name(obs['argmax'])}, "
          f"compte {z_real[obs['argmax']]*mo['sd']+mo['mu']:.0f})   "
          f"z_null={null_max.z(obs['max']):+.2f}  p={p_max:.4f}")
    print(f"  sumsq     = {obs['sumsq']:.1f}   "
          f"z_null={null_ss.z(obs['sumsq']):+.2f}  p={p_ss:.4f}")
    print(f"  motif |z| = {obs['motif']:.3f}   "
          f"z_null={null_motif.z(obs['motif']):+.2f}  p={p_motif:.4f}")
    print("  agrégats par famille (z vs moments simulés) :")
    for k, v in obs["fam_z"].items():
        print(f"    {k:8s}: z = {v:+.2f}")

    order = np.argsort(-np.abs(z_real))[:10]
    print("\n  top 10 des triplets par |z| :")
    for t in order:
        pat = [k for k, sel in PATTERNS.items() if sel[t]]
        print(f"    {trip_name(t):>12s}  compte {z_real[t]*mo['sd']+mo['mu']:5.0f}  "
              f"z = {z_real[t]:+.2f}  {'/'.join(pat) if pat else '-'}")

    # -- 5. Géométrie des extrêmes : motif ou bruit ? ---------------------
    print("\n  composition des 50 triplets les plus déviants (obs vs null simulé) :")
    for k in PATTERNS:
        nullv = np.array([r["top50"][k] for r in rows])
        pgeo = (1 + np.sum(nullv >= obs["top50"][k])) / (1 + len(nullv))
        print(f"    {k:8s}: obs {obs['top50'][k]:2d}/50   null {nullv.mean():5.2f} "
              f"(q95 {np.quantile(nullv, 0.95):4.0f})   P(>=obs)={pgeo:.3f}")
    nullpos = np.array([r["top50_pos"] for r in rows])
    print(f"    sur-rep. : obs {obs['top50_pos']:2d}/50   null {nullpos.mean():5.2f} "
          f"(diagnostic seulement — la décision porte sur les 3 stats pré-enregistrées)")

    # -- 6. Puissance : courbe de détectabilité ---------------------------
    floors = {"max": float(null_max.samples.max()),
              "sumsq": float(null_ss.samples.max()),
              "motif": float(null_motif.samples.max())}
    nulls = {"max": null_max, "sumsq": null_ss, "motif": null_motif}
    az = {k: abs(nulls[k].z(v)) for k, v in floors.items()}
    print(f"\npuissance : seuil = plancher empirique du null (p={1/(R_NULL+1):.1e} ; "
          f"|z| max/sumsq/motif >= {az['max']:.2f}/{az['sumsq']:.2f}/{az['motif']:.2f}), "
          f"{R_POWER} réplicats/point — Holm est plus strict, la puissance au seuil "
          "Holm est <= à celle affichée")

    def measured_power(contaminate, seed: int) -> dict:
        # même sémantique que lab.power, mais les 3 stats sur les MÊMES
        # archives contaminées (une passe au lieu de trois)
        rng = np.random.default_rng(seed)
        hit = {k: 0 for k in floors}
        for _ in range(R_POWER):
            v = stat.all(contaminate(lab.srs(N, rng), rng))
            for k in floors:
                if abs(nulls[k].z(v[k])) >= az[k]:
                    hit[k] += 1
        return {k: h / R_POWER for k, h in hit.items()}

    print(f"\n(a) {K_LOC} triplets disjoints forcés dans f des tirages "
          f"(excès/triplet = N*f*(1-p1)/{K_LOC}) :")
    print("    f      excès  (rel.)  | puiss. max  sumsq  motif")
    pw_loc = {}
    for f in F_LOC:
        pw = measured_power(make_contaminate_loc(f), seed=int(f * 1e5))
        pw_loc[f] = pw
        exc = N * f * (1 - p1) / K_LOC
        print(f"    {f:.3f}  {exc:5.0f}  ({exc/mo['mu']*100:+3.0f} %) |"
              f"      {pw['max']:.2f}   {pw['sumsq']:.2f}   {pw['motif']:.2f}",
              flush=True)

    print(f"\n(b) motif AP diffus : un triplet AP aléatoire forcé dans f des tirages "
          f"(excès agrégé ~N*f sur 1 560 cases) :")
    print("    f      excès/case      | puiss. max  sumsq  motif")
    pw_ap = {}
    for f in F_AP:
        pw = measured_power(make_contaminate_ap(f), seed=90000 + int(f * 1e5))
        pw_ap[f] = pw
        exc = N * f / len(AP_TRIPS)
        print(f"    {f:.3f}  {exc:5.1f}  ({exc/mo['mu']*100:+.2f} %) |"
              f"      {pw['max']:.2f}   {pw['sumsq']:.2f}   {pw['motif']:.2f}",
              flush=True)

    # témoin pool groupé : biais marginal mesuré, une seule amplitude
    rngd = np.random.default_rng(4242)
    n_meas = 40000
    fav_test = np.arange(FAV_DEMO)
    lw = np.zeros(80)
    lw[fav_test] = GAMMA_DEMO
    keys = lw + rngd.gumbel(size=(n_meas, 80))
    idx = np.argpartition(-keys, 20, axis=1)[:, :20]
    frac = np.isin(idx, fav_test).sum() / (n_meas * 20)
    d_meas = float(frac / (FAV_DEMO / 80) - 1)
    pw_pool = measured_power(contaminate_pool, seed=777)
    print(f"\n(c) témoin pool groupé (gamma={GAMMA_DEMO}, biais marginal mesuré "
          f"{d_meas*100:+.2f} % sur {FAV_DEMO} numéros, 9 880 cases déplacées — "
          f"détectable d'abord par le chi2 marginal, voie fermée ; démonstration "
          f"du régime diffus) :")
    print(f"    puiss. max {pw_pool['max']:.2f}  sumsq {pw_pool['sumsq']:.2f}  "
          f"motif {pw_pool['motif']:.2f}")

    # -- 7. Verdicts et registre -----------------------------------------
    floor_p = 1 / (R_NULL + 1)
    v_max = "conforme" if p_max > floor_p else "candidate — recalibrer"
    v_ss = "conforme" if p_ss > floor_p else "candidate — recalibrer"
    v_motif = "conforme" if p_motif > floor_p else "candidate — recalibrer"
    pw_loc_str = "; ".join(
        f"f={f}(exc{N*f*(1-p1)/K_LOC/mo['mu']*100:+.0f}%):max {pw_loc[f]['max']:.2f}"
        for f in F_LOC)
    pw_ap_str = "; ".join(f"f={f}:motif {pw_ap[f]['motif']:.2f}" for f in F_AP)
    fam_str = "; ".join(f"{k} z={v:+.2f}" for k, v in obs["fam_z"].items())

    print(f"\nVERDICTS : max {v_max} (p={p_max:.4f})  sumsq {v_ss} (p={p_ss:.4f})  "
          f"motif {v_motif} (p={p_motif:.4f})")
    if NO_RECORD:
        print("(--fast/--no-record : rien n'est écrit au registre)")
    else:
        existing = {r.get("id") for r in lab.ledger()}
        for tok, o, nl, v, pa, notes in (
            (tok_max, obs["max"], null_max, v_max, pw_loc_str,
             f"argmax {trip_name(obs['argmax'])} ; le p est déjà familial "
             f"(loi du max simulée sur les 82 160 cellules) ; puissance sumsq/motif "
             f"sur (a) : nulle aux mêmes f (voir rapport) ; R_power={R_POWER}"),
            (tok_ss, obs["sumsq"], null_ss, v_ss,
             f"pool groupé d_marg={d_meas*100:+.1f}%: sumsq {pw_pool['sumsq']:.2f} "
             f"(max {pw_pool['max']:.2f})",
             "aveugle par construction aux excès de <10 cases ; sensible au régime "
             "diffus multiplicatif (témoin c) ; somme des comptes exactement 1140*N "
             "-> chi2 tabulé invalide"),
            (tok_motif, obs["motif"], null_motif, v_motif, pw_ap_str,
             f"agrégats : {fam_str} ; p familial (loi du max sur 5 familles "
             f"simulée) ; sd(AP)={mo['fams']['AP'][1]:.0f} contre "
             f"{np.sqrt(1560)*mo['sd']:.0f} si cases indépendantes"),
        ):
            if tok["id"] in existing:
                print(f"registre : entrée '{tok['id']}' déjà présente — pas de doublon")
            else:
                lab.record(tok, observed=o, null=nl, power_at=pa, verdict=v, notes=notes)
                print(f"registre : consigné sous '{tok['id']}'")
    print(f"\ntotal : {time.time()-t_start:.0f} s")


if __name__ == "__main__":
    main()
