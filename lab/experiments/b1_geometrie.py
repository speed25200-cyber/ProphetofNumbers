"""B1 — Géométrie du paquet de 12 grilles (track B, biais nul).

Question. L'app propose 12 grilles par mise (ProphetConst.stakes = [5,6,7,8,10],
OracleTests.testGridsHaveCorrectCardinality). Sous H0, CHAQUE grille de k
numéros a la même loi de hits, Hypergéométrique(80,20,k), quel que soit le
choix des numéros — donc E[hits]=k/4 par grille et E[total]=3k par paquet,
pour TOUTE géométrie. Mieux : le gain d'un paquet étant la SOMME de gains
par grille, et la loi marginale par grille étant identique partout,
E[gain total] est invariant par géométrie sous n'importe quelle table de
gains par grille. La géométrie ne peut déplacer que la FORME de la loi
jointe : variance du total, P(au moins une grille à >= t hits), P(zéro hit
partout). C'est exactement le périmètre de la track B : aucune prédiction,
aucun biais, aucun rendement moyen — seulement le profil de risque.

Géométries comparées, à k et budget identiques (12 grilles) :
  - disjoint     12 grilles deux à deux disjointes (possible ssi 12k <= 80,
                 donc k=5 ou 6 ; pour k=5 c'est AUSSI l'optimum « équilibré » :
                 couverture 0/1, zéro paire répétée) ;
  - balanced     couverture équilibrée quand disjoint est impossible
                 (k=10 : 120 > 80 ; chaque numéro couvert 1 ou 2 fois,
                 paires co-occurrentes répétées minimisées, glouton) ;
  - iid          12 grilles uniformes indépendantes (référence « aléatoire ») ;
  - app_indep    émulation structurelle de Swarm.makeGrids : 3 kinds x
                 {I, II, Anti, Furtif}, I/II/Anti disjoints par kind, Furtif =
                 top-k du champ pénalisé par la popularité (recouvre I),
                 champs des 3 kinds INDÉPENDANTS (borne basse de corrélation) ;
  - app_corr     idem, champs des 3 kinds PARFAITEMENT corrélés : le paquet
                 dégénère en 4 grilles distinctes x3 (borne haute) ;
                 l'app réelle est entre app_indep et app_corr ;
  - conc         concentré : 12 grilles dans un support réduit (k=5 : 15
                 numéros couverts 4x ; k=10 : 20 numéros couverts 6x) —
                 l'anti-stratégie, pour borner l'écart ;
  - identical    12 copies de la même grille (concentration maximale).

Méthode. Monte-Carlo SRS 20/80 via lab.srs (règle 1 du labo : le null est
simulé), avec recoupements exacts indépendants là où ils existent :
  - variance exacte du total pour tout design fixe : total = sum_n c_n I_n,
    Cov(I_n,I_m) = -19/79/16^... constante => Var ne dépend QUE du profil de
    couverture sum c_n^2 (formule fermée, vérifiée par MC) ;
  - loi exacte du max pour les grilles disjointes (PGF par produit) ;
  - énumération exacte sur le support (2^s états) pour conc et identical ;
  - forme fermée pour iid (hits indépendants conditionnellement au tirage,
    qui est de taille fixe => indépendance inconditionnelle) ;
  - inclusion-exclusion d'ordre 2 (bornes de Bonferroni) pour les queues que
    le MC ne peut pas atteindre (k=10, t=9,10).

Contrôle dur : E[total hits] identique (= 3k) pour toutes les géométries,
à 4 erreurs types MC près. S'il échoue, le code est faux.

Reproductible : python3 lab/experiments/b1_geometrie.py [--quick]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from functools import lru_cache
from math import comb, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN          # 80, 20
NG = 12                                    # grilles par mise (OracleTests)
TOT = comb(POOL, DRAWN)
SEED = 20260827


# --------------------------------------------------------------------------
# Lois exactes élémentaires
# --------------------------------------------------------------------------

def sf(k: int, t: int) -> float:
    """P(H >= t), H ~ Hypergéom(80,20,k)."""
    return float(lab.hits_pmf(k)[t:].sum())


@lru_cache(maxsize=None)
def p2_pair(k: int, m: int, t: int) -> float:
    """P(H_g >= t ET H_h >= t) pour deux grilles de taille k partageant m numéros.

    Trivariée hypergéométrique sur (partagé, propre à g, propre à h, reste).
    """
    rest = POOL - 2 * k + m
    s = 0
    for a in range(min(m, DRAWN) + 1):
        for b1 in range(k - m + 1):
            if a + b1 < t:
                continue
            for b2 in range(k - m + 1):
                if a + b2 < t:
                    continue
                r = DRAWN - a - b1 - b2
                if r < 0 or r > rest:
                    continue
                s += comb(m, a) * comb(k - m, b1) * comb(k - m, b2) * comb(rest, r)
    return s / TOT


def ie2_union(overlaps: list[int], k: int, t: int, n_grids: int) -> tuple[float, float]:
    """Bornes Bonferroni ordre 2 : S1-S2 <= P(au moins une grille >= t) <= S1.

    `overlaps` : les recouvrements des paires de grilles DISTINCTES.
    Renvoie (borne basse S1-S2, borne haute S1). Pour des événements rares et
    des recouvrements faibles, S1-S2 est quasi exact (S3 négligeable).
    """
    s1 = n_grids * sf(k, t)
    s2 = sum(p2_pair(k, m, t) for m in overlaps)
    return s1 - s2, s1


def var_total_exact(coverage: np.ndarray) -> float:
    """Variance exacte du total de hits d'un design fixe.

    total = sum_n c_n I_n avec I_n = 1[n tiré].
    Var(I_n) = p(1-p), Cov(I_n,I_m) = 20*19/(80*79) - p^2 (constante) :
    la variance du total ne dépend QUE du profil de couverture sum c_n^2.
    """
    p = DRAWN / POOL
    v_diag = p * (1 - p)
    cov_off = DRAWN * (DRAWN - 1) / (POOL * (POOL - 1)) - p * p
    s1 = float(coverage.sum())
    s2 = float((coverage.astype(np.float64) ** 2).sum())
    return v_diag * s2 + cov_off * (s1 * s1 - s2)


def exact_iid(k: int) -> dict:
    """Forme fermée pour 12 grilles iid : conditionnellement au tirage (taille
    fixe 20), les 12 hits sont iid Hypergéom(80,20,k) — donc inconditionnellement
    aussi. Max et total en découlent exactement."""
    pmf = lab.hits_pmf(k)
    cdf = np.cumsum(pmf)
    p_max_ge = {t: 1.0 - float(cdf[t - 1]) ** NG for t in range(1, k + 1)}
    tot = np.array([1.0])
    for _ in range(NG):
        tot = np.convolve(tot, pmf)
    mean = float(np.arange(len(tot)) @ tot)
    var = float(((np.arange(len(tot)) - mean) ** 2) @ tot)
    e_max = sum(p_max_ge.values())
    return {"mean": mean, "var": var, "p_tot0": float(tot[0]),
            "p_max_ge": p_max_ge, "e_max": e_max}


def exact_support(design: np.ndarray) -> dict | None:
    """Métriques exactes par énumération des 2^s intersections tirage-support.

    Possible quand le support (union des numéros couverts) a s <= 20 numéros.
    Poids d'un sous-ensemble x de taille d : C(80-s, 20-d)/C(80,20).
    """
    support = np.where(design.any(axis=0))[0]
    s = len(support)
    if s > 20:
        return None
    k = int(design.sum(axis=1)[0])
    masks = np.array([sum(1 << j for j, n in enumerate(support) if design[g, n])
                      for g in range(design.shape[0])], dtype=np.uint32)
    xs = np.arange(1 << s, dtype=np.uint32)
    d = np.bitwise_count(xs).astype(np.int64)
    w_by_d = np.array([comb(POOL - s, DRAWN - dd) / TOT if 0 <= DRAWN - dd <= POOL - s
                       else 0.0 for dd in range(s + 1)])
    w = w_by_d[d]
    hits = np.bitwise_count(xs[:, None] & masks[None, :]).astype(np.int16)
    tot = hits.sum(axis=1)
    mx = hits.max(axis=1)
    mean = float(tot @ w)
    var = float(((tot - mean) ** 2) @ w)
    p_max_ge = {t: float(w[mx >= t].sum()) for t in range(1, k + 1)}
    return {"mean": mean, "var": var, "p_tot0": float(w[tot == 0].sum()),
            "p_max_ge": p_max_ge, "e_max": sum(p_max_ge.values())}


def exact_max_disjoint(k: int) -> dict:
    """Loi exacte du max pour 12 grilles disjointes (12k <= 80).

    P(max <= c) = sum_j [ (sum_{h<=c} C(k,h) x^h)^12 ]_j * C(80-12k, 20-j) / C(80,20).
    Entiers exacts, aucune approximation.
    """
    leftover = POOL - NG * k
    out = {}
    for c in range(k + 1):
        base = [comb(k, h) for h in range(min(c, k) + 1)]
        poly = [1]
        for _ in range(NG):
            new = [0] * (len(poly) + len(base) - 1)
            for i, a in enumerate(poly):
                for j, b in enumerate(base):
                    new[i + j] += a * b
            poly = new[:DRAWN + 1]
        ways = sum(poly[j] * comb(leftover, DRAWN - j)
                   for j in range(min(DRAWN, len(poly) - 1) + 1)
                   if DRAWN - j <= leftover)
        out[c] = ways / TOT
    p_max_ge = {t: 1.0 - out[t - 1] for t in range(1, k + 1)}
    return {"p_max_ge": p_max_ge, "e_max": sum(p_max_ge.values())}


# --------------------------------------------------------------------------
# Constructions des designs (12 x 80 booléens)
# --------------------------------------------------------------------------

def design_disjoint(k: int) -> np.ndarray:
    assert NG * k <= POOL, f"12 grilles disjointes de {k} impossibles : {NG * k} > {POOL}"
    d = np.zeros((NG, POOL), bool)
    for g in range(NG):
        d[g, g * k:(g + 1) * k] = True
    return d


def design_balanced(k: int, seed: int = SEED) -> np.ndarray:
    """Couverture équilibrée gloutonne : couvrir d'abord les numéros les moins
    couverts, en minimisant les paires déjà co-occurrentes. Pour k=10 :
    couverture {1,2} (40 numéros 2x, 40 numéros 1x), paires répétées ~minimales
    (borne inférieure 8 quand les 8 premières grilles partitionnent 1..80)."""
    rng = np.random.default_rng(seed)
    cov = np.zeros(POOL, np.int64)
    pair = np.zeros((POOL, POOL), np.int64)
    d = np.zeros((NG, POOL), bool)
    for g in range(NG):
        chosen: list[int] = []
        for _ in range(k):
            cand = np.setdiff1d(np.arange(POOL), np.array(chosen, int))
            pen = pair[np.ix_(cand, np.array(chosen, int))].sum(axis=1) if chosen \
                else np.zeros(len(cand))
            key = cov[cand] * 10_000 + pen * 10 + rng.random(len(cand))
            chosen.append(int(cand[np.argmin(key)]))
        for a in chosen:
            cov[a] += 1
            for b in chosen:
                if a < b:
                    pair[a, b] += 1
        d[g, chosen] = True
    return d


def design_concentrated(k: int, seed: int = SEED) -> np.ndarray:
    """Anti-stratégie : 12 grilles dans un support réduit, via des partitions
    répétées du support (résolvable : couverture uniforme dans le support).
    k=5 : support 15, 4 partitions en 3 grilles (couverture 4).
    k=10 : support 20, 6 partitions en 2 grilles (couverture 6)."""
    if k == 5:
        s, rounds, per = 15, 4, 3
    elif k == 10:
        s, rounds, per = 20, 6, 2
    else:
        raise ValueError(k)
    rng = np.random.default_rng(seed)
    d = np.zeros((NG, POOL), bool)
    g = 0
    for _ in range(rounds):
        perm = rng.permutation(s)
        for j in range(per):
            d[g, perm[j * k:(j + 1) * k]] = True
            g += 1
    return d


def design_identical(k: int) -> np.ndarray:
    d = np.zeros((NG, POOL), bool)
    d[:, :k] = True
    return d


# Popularité humaine, copiée de Swarm.swift (grilles Furtif).
POPULARITY = np.zeros(POOL)
for n in range(1, POOL + 1):
    s_ = 0.0
    if n <= 31:
        s_ += 1.0
    if n <= 12:
        s_ += 0.4
    if n % 10 == 7:
        s_ += 0.5
    if n % 11 == 0:
        s_ += 0.4
    if n % 10 == 0:
        s_ += 0.2
    POPULARITY[n - 1] = s_


def app_pack_hits(mask: np.ndarray, k: int, rng: np.random.Generator,
                  corr: bool) -> np.ndarray:
    """Hits (B,12) d'un paquet émulant Swarm.makeGrids sous H0.

    Sous H0 les champs de score sont du bruit ; seule la géométrie
    inter-grilles compte (la loi marginale d'une grille fixe est la même
    hypergéométrique quel que soit son contenu). Par kind : I = top-k du
    champ, II = k suivants (disjoint de I), Anti = k derniers, Furtif =
    top-k de (champ - 0.4*popularité), qui recouvre I. `corr=True` : les 3
    kinds partagent le même champ (les 12 grilles dégénèrent en 4 x3).
    """
    b = mask.shape[0]
    n_fields = 1 if corr else 3
    fields = rng.standard_normal((b, n_fields, POOL))
    cols = []
    for j in range(3):
        f = fields[:, 0 if corr else j, :]
        order = np.argsort(-f, axis=1)
        m_ord = np.take_along_axis(mask, order, axis=1)
        h_i = m_ord[:, :k].sum(axis=1)
        h_ii = m_ord[:, k:2 * k].sum(axis=1)
        h_anti = m_ord[:, POOL - k:].sum(axis=1)
        order_s = np.argsort(-(f - 0.4 * POPULARITY), axis=1)[:, :k]
        h_st = np.take_along_axis(mask, order_s, axis=1).sum(axis=1)
        cols += [h_i, h_ii, h_anti, h_st]
        if corr:
            break
    hits = np.stack(cols, axis=1).astype(np.int16)
    if corr:
        hits = np.tile(hits, (1, 3))
    return hits


def app_overlap_profile(k: int, corr: bool, n_packs: int = 400,
                        seed: int = SEED + 7) -> tuple[list[list[int]], int]:
    """Recouvrements de paires de grilles DISTINCTES des paquets émulés
    (pour l'inclusion-exclusion sur les queues rares). Renvoie (profils,
    nombre de grilles distinctes par paquet)."""
    rng = np.random.default_rng(seed)
    profiles = []
    n_distinct = 4 if corr else 12
    for _ in range(n_packs):
        f = rng.standard_normal((3, POOL)) if not corr else \
            np.tile(rng.standard_normal((1, POOL)), (3, 1))
        grids = []
        for j in range(3):
            order = np.argsort(-f[j])
            grids += [set(order[:k]), set(order[k:2 * k]), set(order[POOL - k:]),
                      set(np.argsort(-(f[j] - 0.4 * POPULARITY))[:k])]
            if corr:
                break
        prof = [len(grids[a] & grids[b]) for a in range(len(grids))
                for b in range(a + 1, len(grids))]
        profiles.append(prof)
    return profiles, n_distinct


# --------------------------------------------------------------------------
# Monte-Carlo
# --------------------------------------------------------------------------

class Acc:
    def __init__(self, k: int):
        self.k, self.n = k, 0
        self.hist_tot = np.zeros(NG * k + 1, np.int64)
        self.hist_max = np.zeros(k + 1, np.int64)

    def add(self, hits: np.ndarray):
        self.n += hits.shape[0]
        self.hist_tot += np.bincount(hits.sum(axis=1), minlength=len(self.hist_tot))
        self.hist_max += np.bincount(hits.max(axis=1), minlength=len(self.hist_max))

    def stats(self) -> dict:
        pt = self.hist_tot / self.n
        xs = np.arange(len(pt))
        mean = float(xs @ pt)
        var = float(((xs - mean) ** 2) @ pt) * self.n / (self.n - 1)
        pm = self.hist_max / self.n
        p_max_ge = {t: float(pm[t:].sum()) for t in range(1, self.k + 1)}
        return {"n": self.n, "mean": mean, "var": var,
                "se_mean": sqrt(var / self.n), "p_tot0": float(pt[0]),
                "p_max_ge": p_max_ge,
                "e_max": float(np.arange(len(pm)) @ pm)}


def run_mc(k: int, designs: dict[str, np.ndarray], reps: int, reps_app: int,
           seed: int = SEED) -> dict[str, dict]:
    """Un seul flux de tirages lab.srs partagé par tous les designs fixes
    (comparaisons appariées) ; iid par hypergéométrique exacte conditionnelle
    (grilles indépendantes du tirage de taille fixe) ; app par champs simulés."""
    rng = np.random.default_rng(seed)
    accs = {name: Acc(k) for name in designs}
    accs["iid"] = Acc(k)
    accs["app_indep"] = Acc(k)
    accs["app_corr"] = Acc(k)
    dmats = {name: d.T.astype(np.int16) for name, d in designs.items()}
    batch = 200_000
    done = 0
    t0 = time.time()
    while done < reps:
        b = min(batch, reps - done)
        mask = lab.srs(b, rng)
        m16 = mask.astype(np.int16)
        for name, dt in dmats.items():
            accs[name].add(m16 @ dt)
        accs["iid"].add(rng.hypergeometric(DRAWN, POOL - DRAWN, k,
                                           size=(b, NG)).astype(np.int16))
        if done < reps_app:
            accs["app_indep"].add(app_pack_hits(mask, k, rng, corr=False))
            accs["app_corr"].add(app_pack_hits(mask, k, rng, corr=True))
        done += b
        print(f"  k={k}: {done:,}/{reps:,} réplicats  ({time.time() - t0:.0f}s)",
              flush=True)
    return {name: acc.stats() for name, acc in accs.items()}


# --------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------

def fmt_p(p: float | None) -> str:
    if p is None:
        return "      —    "
    if p == 0:
        return "      0    "
    if p >= 0.01:
        return f"{p:11.5f}"
    return f"{p:11.3e}"


def se_p(p: float, n: int) -> float:
    return sqrt(max(p, 1e-300) * (1 - p) / n)


def report_k(k: int, mc: dict, exact: dict, order: list[str], labels: dict):
    ts = [k - 2, k - 1, k]
    print(f"\n=== k = {k} (mise à {k} numéros, 12 grilles, E[total] théorique = {3 * k}) ===")
    print(f"\n{'géométrie':<12} {'réplicats':>11} {'E[tot] MC':>10} {'E exact':>8} "
          f"{'Var MC':>8} {'Var exacte':>10} {'P(tot=0)':>11} {'E[max]':>7}")
    for name in order:
        s = mc[name]
        ex = exact.get(name, {})
        p0 = ex.get("p_tot0", s["p_tot0"])
        print(f"{labels.get(name, name):<12} {s['n']:>11,} {s['mean']:>10.4f} "
              f"{ex.get('mean', 3 * k):>8.3f} {s['var']:>8.3f} "
              f"{ex.get('var', float('nan')):>10.3f} {fmt_p(p0)} "
              f"{ex.get('e_max', s['e_max']):>7.4f}")

    print(f"\nP(au moins une grille >= t hits) — MC (± se) et exact/IE2 quand disponible :")
    head = f"{'géométrie':<12}"
    for t in ts:
        head += f" {'t=' + str(t) + ' (MC)':>13} {'exact/IE2':>11}"
    print(head)
    for name in order:
        s = mc[name]
        row = f"{labels.get(name, name):<12}"
        for t in ts:
            p = s["p_max_ge"].get(t, 0.0)
            ex = exact.get(name, {}).get("p_max_ge", {}).get(t)
            row += f" {fmt_p(p)} {fmt_p(ex)}"
        print(row)
    print("   (se MC sur P : ~sqrt(p(1-p)/n) ; ex. p=1e-2, n=4e6 -> ±5e-5)")


def ratio(a: float, b: float) -> float:
    return a / b if b > 0 else float("inf")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="MC réduit (dev)")
    ap.add_argument("--reps", type=int, default=None)
    args = ap.parse_args()
    reps = args.reps or (200_000 if args.quick else 4_000_000)
    reps_app = min(reps, 2_000_000)

    # ---- Pré-enregistrement AVANT tout calcul (règle 2) --------------------
    already = {r["id"] for r in lab.ledger()}
    toks = {}
    toks["k5"] = lab.preregister(
        "b1.geo.k5",
        "À espérance figée (E[total]=15), la géométrie du paquet de 12 grilles k=5 "
        "change la loi jointe : disjoint domine iid sur Var(total) et P(tot=0) sans "
        "dégrader P(max>=t) ; le concentré est dominé sur P(max>=t).",
        "ratio P_disjoint(max>=4)/P_iid(max>=4) ; MC SRS lab.srs "
        f"{reps:,} réplicats + exact (PGF disjoint, forme fermée iid, énumération support)",
        "MC SRS + recoupements exacts indépendants ; contrôle E[total]=3k à ±4 se",
        "mesure track B (pas de test H0) : recommander la géométrie dominante si "
        "l'ordre est hors bruit MC (>3 se) ; sinon 'indifférent'",
        track="B")
    toks["k10"] = lab.preregister(
        "b1.geo.k10",
        "Pour k=10, 12 grilles disjointes sont impossibles (120>80) ; la couverture "
        "équilibrée (1-2x par numéro) domine iid sur Var(total) et P(tot=0), "
        "l'écart sur P(max>=t) restant faible.",
        "ratio P_balanced(max>=8)/P_iid(max>=8) ; MC SRS lab.srs "
        f"{reps:,} réplicats + IE2 (Bonferroni ordre 2) pour t=9,10",
        "MC SRS + variance exacte par profil de couverture + IE2 ; contrôle E[total]=30 à ±4 se",
        "mesure track B : recommander la géométrie dominante si l'ordre est hors "
        "bruit MC (>3 se) ; sinon 'indifférent'",
        track="B")
    toks["app"] = lab.preregister(
        "b1.geo.app",
        "La géométrie actuelle de Swarm.makeGrids (3 kinds x I/II/Anti/Furtif), "
        "émulée sous H0 entre deux bornes de corrélation inter-kinds, est proche "
        "d'iid/disjoint si les kinds sont décorrélés, et dégénère vers 4 grilles x3 "
        "(variance ~x3, P(max>=t) d'un paquet de 4) si les kinds sont corrélés.",
        "ratios app_indep/disjoint et app_corr/disjoint sur Var(total) et "
        "P(max>=k-1), k=5 ; émulation structurelle (pas d'exécution Swift possible ici)",
        "MC SRS, mêmes tirages que les designs fixes",
        "mesure track B : qualifier la géométrie de l'app (bonne/mauvaise/indifférente) "
        "métrique par métrique",
        track="B")

    print(f"B1 — géométrie du paquet de 12 grilles ; {reps:,} réplicats SRS "
          f"(app : {reps_app:,}), seed {SEED}\n")

    results = {}
    for k in (5, 10):
        designs: dict[str, np.ndarray] = {}
        exact: dict[str, dict] = {}

        if NG * k <= POOL:
            designs["disjoint"] = design_disjoint(k)
            print(f"k={k} : 12 grilles disjointes possibles (12x{k}={NG * k} <= 80) ; "
                  "c'est aussi l'optimum 'équilibré' (couverture 0/1, zéro paire répétée).")
        else:
            print(f"k={k} : 12 grilles disjointes IMPOSSIBLES (12x{k}={NG * k} > 80) "
                  "-> design équilibré glouton (couverture 1-2, paires répétées minimisées).")
            bal = design_balanced(k)
            designs["balanced"] = bal
            cov = bal.sum(axis=0)
            co = (bal.astype(int).T @ bal.astype(int))
            np.fill_diagonal(co, 0)
            rep_pairs = int((co[np.triu_indices(POOL, 1)] >= 2).sum())
            print(f"   couverture: min={cov.min()} max={cov.max()} "
                  f"(x1: {(cov == 1).sum()}, x2: {(cov == 2).sum()}) ; "
                  f"paires co-occurrentes répétées: {rep_pairs}")

        designs["conc"] = design_concentrated(k)
        designs["identical"] = design_identical(k)

        for name, d in designs.items():
            assert (d.sum(axis=1) == k).all()
            exact[name] = {"mean": 3.0 * k, "var": var_total_exact(d.sum(axis=0))}
        if "disjoint" in designs:
            exact["disjoint"].update(exact_max_disjoint(k))
            pmf60 = np.array([comb(NG * k, j) * comb(POOL - NG * k, DRAWN - j) / TOT
                              if DRAWN - j <= POOL - NG * k else 0.0
                              for j in range(DRAWN + 1)])
            exact["disjoint"]["p_tot0"] = float(pmf60[0])
        for name in ("conc", "identical"):
            es = exact_support(designs[name])
            if es:
                exact[name].update(es)
        exact["iid"] = exact_iid(k)
        exact["iid"]["mean"] = 3.0 * k

        # IE2 pour les queues hors de portée du MC (et recoupement à t=k-1,k)
        spread = "disjoint" if "disjoint" in designs else "balanced"
        d = designs[spread]
        ov = [int((d[a] & d[b]).sum()) for a in range(NG) for b in range(a + 1, NG)]
        exact[spread].setdefault("p_max_ge", {})
        for t in (k - 1, k):
            lo, hi = ie2_union(ov, k, t, NG)
            exact[spread]["p_max_ge"].setdefault(t, lo)
        for mode, corr in (("app_indep", False), ("app_corr", True)):
            profs, nd = app_overlap_profile(k, corr)
            exact[mode] = {"mean": 3.0 * k, "p_max_ge": {}}
            for t in (k - 1, k):
                los = [ie2_union(p, k, t, nd)[0] for p in profs]
                exact[mode]["p_max_ge"][t] = float(np.mean(los))

        mc = run_mc(k, designs, reps, reps_app)

        # ---- Contrôle dur : espérance identique partout --------------------
        print(f"\nContrôle E[total] = {3 * k} (théorème ; toute géométrie) :")
        ok_all = True
        for name, s in mc.items():
            zdev = (s["mean"] - 3 * k) / s["se_mean"]
            ok = abs(zdev) <= 4
            ok_all &= ok
            print(f"  {name:<12} E_MC = {s['mean']:.4f}  (écart {zdev:+.2f} se) "
                  f"{'OK' if ok else '== ÉCHEC =='}")
        if not ok_all:
            print("ÉCHEC DU CONTRÔLE : bug dans la simulation, résultats invalides.")
            sys.exit(1)

        order = ([spread, "iid", "app_indep", "app_corr", "conc", "identical"])
        labels = {"disjoint": "disjoint", "balanced": "équilibré", "iid": "iid",
                  "app_indep": "app (ρ=0)", "app_corr": "app (ρ=1)",
                  "conc": "concentré", "identical": "identiques"}
        report_k(k, mc, exact, order, labels)
        results[k] = {"mc": mc, "exact": exact, "spread": spread}

    # ---- Ratios ------------------------------------------------------------
    print("\n=== Ratios (meilleure géométrie étalée vs les autres) ===")
    for k in (5, 10):
        r = results[k]
        sp = r["spread"]
        mc, ex = r["mc"], r["exact"]
        t_hi = k
        # à t=k : exact/IE2 (le MC ne voit pas t=10 pour k=10)
        p_sp = ex[sp]["p_max_ge"][t_hi]
        p_iid = ex["iid"]["p_max_ge"][t_hi]
        p_conc = ex["conc"]["p_max_ge"].get(t_hi, 0.0)
        p_id = ex["identical"]["p_max_ge"][t_hi]
        print(f"\nk={k} :")
        print(f"  P(>=1 grille à {t_hi}/{t_hi})   {sp}/iid = {ratio(p_sp, p_iid):.4f}   "
              f"{sp}/concentré = {ratio(p_sp, p_conc):.2f}   "
              f"{sp}/identiques = {ratio(p_sp, p_id):.2f}")
        t_md = k - 1
        p_sp_m = ex[sp]["p_max_ge"].get(t_md, mc[sp]["p_max_ge"][t_md])
        p_iid_m = ex["iid"]["p_max_ge"][t_md]
        print(f"  P(>=1 grille à >={t_md}) exact/IE2   {sp}/iid = {ratio(p_sp_m, p_iid_m):.4f}")
        t_lo = k - 2
        print(f"  P(>=1 grille à >={t_lo}) MC   {sp}/iid = "
              f"{ratio(mc[sp]['p_max_ge'][t_lo], mc['iid']['p_max_ge'][t_lo]):.4f}")
        print(f"  Var(total hits) exacte    iid/{sp} = "
              f"{ex['iid']['var'] / ex[sp]['var']:.2f}   "
              f"concentré/{sp} = {ex['conc']['var'] / ex[sp]['var']:.2f}   "
              f"identiques/{sp} = {ex['identical']['var'] / ex[sp]['var']:.2f}")
        print(f"  P(zéro hit sur les 12)    {sp}: {fmt_p(ex[sp].get('p_tot0', mc[sp]['p_tot0'])).strip()}"
              f"   iid: {fmt_p(ex['iid']['p_tot0']).strip()}"
              f"   concentré: {fmt_p(ex['conc'].get('p_tot0')).strip()}"
              f"   identiques: {fmt_p(ex['identical'].get('p_tot0')).strip()}")

    print("\nMises intermédiaires : k=6 -> disjoint possible (72<=80) ; "
          "k=7,8 -> disjoint impossible (84,96>80), design équilibré comme k=10.")

    print("\nCe que la géométrie NE change PAS (théorème, et contrôle ci-dessus) : "
          "E[total hits]=3k, et E[gain total] sous toute table de gains par grille. "
          "Rien ici n'est de la prédiction ; seule la forme de la loi bouge.")

    # ---- Registre ----------------------------------------------------------
    def rec(key, observed, verdict, notes):
        if args.quick:
            print(f"[registre] mode --quick : {toks[key]['id']} NON consigné (dev).")
            return
        if toks[key]["id"] in already:
            print(f"[registre] {toks[key]['id']} déjà consigné, on ne double pas.")
            return
        lab.record(toks[key], observed, verdict=verdict, notes=notes)
        print(f"[registre] {toks[key]['id']} consigné.")

    r5, r10 = results[5], results[10]
    obs5 = r5["mc"]["disjoint"]["p_max_ge"][4] / r5["mc"]["iid"]["p_max_ge"][4]
    rec("k5", obs5,
        "disjoint domine iid sur Var(total) et P(tot=0), à P(max>=t) quasi égale ; "
        "concentré/identiques dominés sur P(max>=t)",
        f"Var iid/disjoint = {r5['exact']['iid']['var'] / r5['exact']['disjoint']['var']:.2f} ; "
        f"P(max>=5) disjoint/iid = "
        f"{r5['exact']['disjoint']['p_max_ge'][5] / r5['exact']['iid']['p_max_ge'][5]:.4f} (exact/IE2) ; "
        f"P(tot=0) iid {r5['exact']['iid']['p_tot0']:.2e} vs disjoint ~0 ; "
        f"E[total]=15 vérifié partout (contrôle ±4se). L'espérance de gain est "
        f"invariante par géométrie : aucun rendement moyen n'est créé.")
    obs10 = r10["mc"]["balanced"]["p_max_ge"][8] / r10["mc"]["iid"]["p_max_ge"][8]
    rec("k10", obs10,
        "équilibré domine iid sur Var(total) et P(tot=0)=0 (couverture 80/80), "
        "P(max>=t) quasi égale ; disjoint impossible (120>80)",
        f"Var iid/équilibré = {r10['exact']['iid']['var'] / r10['exact']['balanced']['var']:.2f} ; "
        f"P(max>=10) équilibré/iid = "
        f"{r10['exact']['balanced']['p_max_ge'][10] / r10['exact']['iid']['p_max_ge'][10]:.4f} (IE2) ; "
        f"E[total]=30 vérifié partout. Aucun rendement moyen créé.")
    v5 = r5["exact"]
    obs_app = r5["mc"]["app_indep"]["var"] / v5["disjoint"]["var"]
    rec("app", obs_app,
        "géométrie app correcte sans être optimale si kinds décorrélés ; la "
        "duplication (Furtif~I, corrélation inter-kinds) est le vrai défaut",
        f"k=5 : Var app_indep/disjoint = {r5['mc']['app_indep']['var'] / v5['disjoint']['var']:.2f}, "
        f"app_corr/disjoint = {r5['mc']['app_corr']['var'] / v5['disjoint']['var']:.2f} ; "
        f"P(max>=4) app_indep/disjoint = "
        f"{r5['mc']['app_indep']['p_max_ge'][4] / r5['mc']['disjoint']['p_max_ge'][4]:.4f}, "
        f"app_corr/disjoint = "
        f"{r5['mc']['app_corr']['p_max_ge'][4] / r5['mc']['disjoint']['p_max_ge'][4]:.4f} ; "
        f"émulation structurelle sous H0 (Swift non exécutable ici), bornes "
        f"ρ=0 et ρ=1 sur la corrélation inter-kinds.")


if __name__ == "__main__":
    main()
