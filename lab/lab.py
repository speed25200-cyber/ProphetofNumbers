"""Noyau du labo — socle commun à toutes les expériences.

Trois règles, tirées des erreurs réelles de `claude/AUDIT-CLAUDE.md` :

  1. Le null est SIMULÉ, jamais tabulé. L'audit s'est trompé trois fois
     en prenant une formule asymptotique pour l'espérance exacte :
     χ²/df attendu à 1,00 au lieu de 0,76 (§1), plus longue série à 13,12
     au lieu de 12,64 (§5), recouvrement conditionné au bonus à 5,00 au
     lieu de 5,57 (§14). Les trois donnaient un « signal » qui n'existait
     pas. `calibrate()` refuse donc une espérance fournie à la main.

  2. Toute expérience est PRÉ-ENREGISTRÉE : statistique, null et seuil
     déclarés avant de regarder le résultat. `preregister()` renvoie un
     jeton qu'il faut rendre à `record()`.

  3. La multiplicité se compte sur le REGISTRE ENTIER, pas par expérience.
     Le registre est pré-chargé avec les tests déjà consommés par l'audit :
     une découverte doit franchir le seuil corrigé de tout ce qui a été
     tenté avant elle, sinon c'est la base rate qui parle.

Un résultat nul dont on ignore la sensibilité n'est pas un résultat.
`power()` est donc obligatoire pour toute expérience de détection.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field

import numpy as np

POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(ROOT, "ledger.jsonl")
CACHE = os.path.join(ROOT, "cache", "draws.npz")


# --------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------

@dataclass
class Archive:
    ids: np.ndarray        # (N,)   numéro de tirage, croissant
    ts: np.ndarray         # (N,)   unix utc, secondes
    nums: np.ndarray       # (N,20) numéros triés, 1..80
    boost: np.ndarray      # (N,)   multiplicateur, -1 si absent
    bonus: np.ndarray      # (N,)   numéro bonus, -1 si absent
    mask: np.ndarray       # (N,80) bool : mask[i,n-1] == n tiré au tirage i

    def __len__(self) -> int:
        return len(self.ids)

    cum: np.ndarray = field(default=None, repr=False)    # (N,80) sorties cumulées
    last: np.ndarray = field(default=None, repr=False)   # (N,80) index de dernière sortie

    def build_index(self) -> None:
        """Cumuls pour la marche avant. ~45 Mo, construits une fois."""
        if self.cum is not None:
            return
        self.cum = np.cumsum(self.mask, axis=0, dtype=np.int32)
        n = len(self.ids)
        idx = np.where(self.mask, np.arange(n, dtype=np.int32)[:, None], np.int32(-1))
        self.last = np.maximum.accumulate(idx, axis=0)

    def slice(self, a: int, b: int) -> "Archive":
        return Archive(self.ids[a:b], self.ts[a:b], self.nums[a:b],
                       self.boost[a:b], self.bonus[a:b], self.mask[a:b])


def load(refresh: bool = False) -> Archive:
    """Charge les 70 560 tirages. Cache .npz : ~40 ms au lieu de ~6 s."""
    if os.path.exists(CACHE) and not refresh:
        z = np.load(CACHE)
        return Archive(z["ids"], z["ts"], z["nums"], z["boost"], z["bonus"], z["mask"])

    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "..", "claude", "draws", "*.csv"))):
        with open(path) as fh:
            for r in csv.DictReader(fh):
                rows.append(r)
    rows.sort(key=lambda r: int(r["id"]))

    n = len(rows)
    ids = np.empty(n, np.int64)
    ts = np.empty(n, np.int64)
    nums = np.empty((n, DRAWN), np.int8)
    boost = np.full(n, -1, np.int8)
    bonus = np.full(n, -1, np.int8)
    for i, r in enumerate(rows):
        ids[i] = int(r["id"])
        ts[i] = int(r["unix_utc"])
        nums[i] = [int(r[f"n{j}"]) for j in range(1, DRAWN + 1)]
        if r.get("boost"):
            boost[i] = int(r["boost"])
        if r.get("bonus"):
            bonus[i] = int(r["bonus"])

    mask = np.zeros((n, POOL), bool)
    mask[np.arange(n)[:, None], nums.astype(np.int64) - 1] = True

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, ids=ids, ts=ts, nums=nums, boost=boost, bonus=bonus, mask=mask)
    return Archive(ids, ts, nums, boost, bonus, mask)


def srs(n: int, rng: np.random.Generator) -> np.ndarray:
    """n tirages SRS 20/80 indépendants -> masque booléen (n,80).

    C'est LE null de référence : ce que le générateur ferait s'il était
    parfait. Toute statistique doit être calibrée contre lui, jamais
    contre une formule.
    """
    out = np.zeros((n, POOL), bool)
    idx = np.argsort(rng.random((n, POOL)), axis=1)[:, :DRAWN]
    np.put_along_axis(out, idx, True, axis=1)
    return out


# --------------------------------------------------------------------------
# Lois exactes utiles (pour l'espérance ANALYTIQUE, à confronter au null simulé)
# --------------------------------------------------------------------------

def overlap_pmf() -> np.ndarray:
    """Loi du recouvrement entre deux tirages : hypergéométrique(80,20,20)."""
    from math import comb
    tot = comb(POOL, DRAWN)
    return np.array([comb(DRAWN, o) * comb(POOL - DRAWN, DRAWN - o) / tot
                     for o in range(DRAWN + 1)])


def hits_pmf(k: int) -> np.ndarray:
    """Loi des hits d'une grille de k numéros : hypergéométrique(80,20,k).

    E[hits] = k/4 pour tout k, et pour TOUT choix de numéros. C'est le
    théorème qui borne la track A : sous H0 aucune sélection ne bouge
    cette espérance. Seule la forme de la loi, donc le gain sous une
    table non linéaire, est manipulable (track B).
    """
    from math import comb
    tot = comb(POOL, k)
    return np.array([comb(DRAWN, h) * comb(POOL - DRAWN, k - h) / tot
                     for h in range(k + 1)])


# --------------------------------------------------------------------------
# Calibration du null — par simulation, sans exception
# --------------------------------------------------------------------------

@dataclass
class Null:
    mean: float
    sd: float
    reps: int
    samples: np.ndarray = field(repr=False, default=None)

    def z(self, observed: float) -> float:
        return float("nan") if self.sd == 0 else (observed - self.mean) / self.sd

    def p_two_sided(self, observed: float) -> float:
        """p empirique, jamais gaussien : la queue simulée fait foi.

        Le +1 au numérateur et au dénominateur est la correction de
        Davison-Hinkley — sans elle un p simulé peut valoir 0, ce qui
        n'est jamais vrai.
        """
        d = np.abs(self.samples - self.mean)
        return float((1 + np.sum(d >= abs(observed - self.mean))) / (1 + len(d)))


def calibrate(stat, n_draws: int, reps: int = 400, seed: int = 0, progress: bool = False) -> Null:
    """Distribution de `stat` sous H0, par simulation de tirages SRS.

    `stat(mask)` reçoit un masque (n_draws, 80) et renvoie un scalaire.
    Aucune espérance théorique n'est acceptée en argument : c'est
    précisément l'erreur que ce labo refuse de reproduire.
    """
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for r in range(reps):
        vals[r] = stat(srs(n_draws, rng))
        if progress and (r + 1) % max(1, reps // 10) == 0:
            print(f"  null {r + 1}/{reps}", flush=True)
    return Null(float(vals.mean()), float(vals.std(ddof=1)), reps, vals)


def power(stat, contaminate, n_draws: int, null: Null, reps: int = 100,
          seed: int = 1, alpha_z: float = 3.0) -> float:
    """Puissance : fraction des réplicats CONTAMINÉS que le test détecte.

    `contaminate(mask, rng)` injecte le défaut qu'on prétend savoir voir.
    Sans cette mesure, un test qui ne se déclenche jamais est
    indistinguable d'un test cassé — c'est la leçon du §11 de l'audit.
    """
    rng = np.random.default_rng(seed)
    hit = 0
    for _ in range(reps):
        m = contaminate(srs(n_draws, rng), rng)
        if abs(null.z(stat(m))) >= alpha_z:
            hit += 1
    return hit / reps


# --------------------------------------------------------------------------
# Protocole marche avant
# --------------------------------------------------------------------------

class Past:
    """Vue sur le passé strict d'un tirage. Le futur est inatteignable.

    `counts` et `gaps` sont servis depuis des cumuls précalculés : O(1)
    par pas au lieu de re-sommer l'historique, ce qui fait passer une
    marche avant complète de ~10 min à ~10 s. L'objet n'expose aucun
    index >= t, donc un prédicteur ne peut pas tricher même par erreur.
    """

    __slots__ = ("_arch", "t")

    def __init__(self, arch: "Archive", t: int):
        self._arch, self.t = arch, t

    @property
    def mask(self) -> np.ndarray:
        return self._arch.mask[:self.t]

    @property
    def nums(self) -> np.ndarray:
        return self._arch.nums[:self.t]

    @property
    def counts(self) -> np.ndarray:
        """(80,) nombre de sorties de chaque numéro sur [0, t)."""
        return self._arch.cum[self.t - 1]

    @property
    def gaps(self) -> np.ndarray:
        """(80,) tirages écoulés depuis la dernière sortie de chaque numéro."""
        return self.t - 1 - self._arch.last[self.t - 1]


def walk_forward(archive: Archive, predict, k: int = 10, warmup: int = 200,
                 stop: int | None = None) -> np.ndarray:
    """Rejoue l'histoire en marche avant. Renvoie les hits par tirage.

    `predict(past, t)` reçoit un `Past` borné à [0, t). Cela empêche la
    fuite ACCIDENTELLE — l'erreur d'indice à `t` au lieu de `t-1` — mais
    pas un prédicteur qui capturerait l'archive par fermeture. Pour
    cela, et seulement pour cela, il y a `leak_check()`, qui tranche
    par l'expérience plutôt que par la discipline. Tout prédicteur du
    registre doit l'avoir passé : un backtest qui fuit produit des
    résultats spectaculaires et faux.
    """
    archive.build_index()
    n = len(archive) if stop is None else stop
    hits = np.empty(n - warmup, np.int16)
    past = Past(archive, warmup)
    for t in range(warmup, n):
        past.t = t
        pick = np.asarray(predict(past, t), np.int64)
        if pick.size != k:
            raise ValueError(f"predict a renvoyé {pick.size} numéros, attendu {k}")
        if np.unique(pick).size != k:
            raise ValueError("predict a renvoyé des doublons")
        if pick.min() < 1 or pick.max() > POOL:
            raise ValueError("predict est sorti de 1..80")
        hits[t - warmup] = int(archive.mask[t][pick - 1].sum())
    return hits


def leak_check(archive: Archive, predict, k: int = 10, warmup: int = 500,
               probes: int = 10, repeats: int = 8, seed: int = 0) -> tuple[bool, list[int]]:
    """Le prédicteur lit-il le futur ? Tranché par l'expérience, pas par la discipline.

    Principe : à l'instant `t`, un prédicteur honnête ne connaît que
    [0, t). Donc si l'on réécrit tout l'historique à partir de `t`
    INCLUS — le tirage courant et tous les suivants — son choix en `t`
    doit être rigoureusement identique. S'il change, il avait lu au
    moins un tirage qu'il n'était pas censé voir.

    On mute l'archive EN PLACE : un prédicteur qui capture l'archive par
    fermeture lit donc la version mutée, ce qu'une copie ne permettrait
    pas de détecter. Les cumuls `cum[t-1]` et `last[t-1]` sont des
    préfixes, que réécrire la queue laisse intacts — rien à reconstruire.

    Les CUMULS sont réécrits en même temps que les tirages. C'est le
    point qui décide : sans cela, un prédicteur lisant `cum[t]` au lieu
    de `cum[t-1]` — le décalage d'indice, la fuite accidentelle la plus
    probable — passerait le test, puisque le cache serait resté celui de
    l'archive d'origine.

    Renvoie `(propre, positions_fuyantes)`.
    """
    archive.build_index()
    rng = np.random.default_rng(seed)
    n = len(archive)
    spots = np.linspace(warmup + 1, n - 1, probes, dtype=int)
    saved = (archive.mask.copy(), archive.nums.copy(),
             archive.cum.copy(), archive.last.copy())
    leaks: list[int] = []

    def restore():
        archive.mask[:], archive.nums[:], archive.cum[:], archive.last[:] = saved

    try:
        for t0 in spots:
            t0 = int(t0)
            before = np.sort(np.asarray(predict(Past(archive, t0), t0), np.int64))
            # `repeats` futurs différents : une fuite dont l'effet est ténu
            # — lire `cum[t]` au lieu de `cum[t-1]` ne déplace le classement
            # que de temps en temps — ne bascule pas à la première mutation.
            for _ in range(repeats):
                fresh = srs(n - t0, rng)
                archive.mask[t0:] = fresh
                archive.nums[t0:] = np.sort(
                    np.argsort(~fresh, axis=1, kind="stable")[:, :DRAWN] + 1, axis=1).astype(np.int8)
                archive.cum[t0:] = archive.cum[t0 - 1] + np.cumsum(fresh, axis=0, dtype=np.int32)
                idx = np.where(fresh, np.arange(t0, n, dtype=np.int32)[:, None], np.int32(-1))
                archive.last[t0:] = np.maximum.accumulate(
                    np.concatenate([archive.last[t0 - 1][None], idx]), axis=0)[1:]
                after = np.sort(np.asarray(predict(Past(archive, t0), t0), np.int64))
                restore()
                if not np.array_equal(before, after):
                    leaks.append(t0)
                    break
    finally:
        restore()
    return (len(leaks) == 0), leaks


def evalue(hits: np.ndarray, k: int,
           thetas=(0.05, 0.1, 0.2, 0.4, -0.05, -0.1, -0.2, -0.4)) -> tuple[float, float]:
    """E-valeur par mélange de martingales — mesure honnête d'un avantage.

    Une e-valeur de v autorise à rejeter H0 au niveau 1/v, et reste
    valide quel que soit l'instant d'arrêt : contrairement à un p, on
    peut la regarder à chaque tirage sans gonfler le taux d'erreur.
    Grille signée, comme l'e-process de `Swarm.swift` : un déficit de
    hits est une anomalie au même titre qu'un excès.

    Renvoie `(e, log10_e)`. Sur des dizaines de milliers de tirages sans
    signal, `e` sous-déborde à 0,000 — ce qui est le bon résultat mais
    illisible ; `log10_e` reste interprétable (≈ −0 sous H0, très négatif
    quand H0 est massivement confirmée, positif s'il y a un avantage).
    """
    pmf = hits_pmf(k)
    h_grid = np.arange(k + 1)
    logs = []
    for th in thetas:
        m = float((pmf * np.exp(th * h_grid)).sum())
        logs.append(float(np.sum(th * hits - np.log(m))))
    logs = np.asarray(logs)
    mx = float(logs.max())
    log_e = (mx + np.log(np.mean(np.exp(logs - mx)))) / np.log(10)
    return float(np.mean(np.exp(np.clip(logs, -700, 700)))), float(log_e)


# --------------------------------------------------------------------------
# Registre : pré-enregistrement et multiplicité
# --------------------------------------------------------------------------

def preregister(exp_id: str, hypothesis: str, statistic: str, null_method: str,
                decision: str, track: str = "A") -> dict:
    """Déclare l'expérience AVANT de la faire tourner. Renvoie le jeton."""
    tok = {
        "id": exp_id,
        "track": track,
        "hypothesis": hypothesis,
        "statistic": statistic,
        "null_method": null_method,
        "decision": decision,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    tok["seal"] = hashlib.sha256(
        json.dumps(tok, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    return tok


def record(token: dict, observed: float, null: Null | None = None, p: float | None = None,
           power_at: str | None = None, verdict: str = "", notes: str = "") -> dict:
    """Consigne le résultat. Le jeton scelle ce qui avait été annoncé."""
    row = dict(token)
    row["observed"] = float(observed)
    if null is not None:
        row.update(null_mean=null.mean, null_sd=null.sd, null_reps=null.reps,
                   z=null.z(observed), p=null.p_two_sided(observed) if p is None else p)
    elif p is not None:
        row["p"] = float(p)
    row["power_at"] = power_at
    row["verdict"] = verdict
    row["notes"] = notes
    row["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def ledger() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def dedupe() -> int:
    """Ne garde que la dernière consignation de chaque `id`.

    Relancer une expérience pendant sa mise au point ne doit pas gonfler
    `m` : c'est le même test, pas deux. L'effet d'un doublon est
    conservateur (il durcit le seuil), donc il ne fabrique pas de fausse
    découverte — mais il fausse le compte, et le compte est précisément
    ce sur quoi repose la correction.
    """
    rows = ledger()
    keep = {r["id"]: r for r in rows}          # la dernière écrase les précédentes
    order = []
    seen = set()
    for r in reversed(rows):
        if r["id"] not in seen:
            seen.add(r["id"])
            order.append(keep[r["id"]])
    order.reverse()
    removed = len(rows) - len(order)
    if removed:
        with open(LEDGER, "w") as fh:
            for r in order:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return removed


def holm(alpha: float = 0.05) -> list[dict]:
    """Holm-Bonferroni sur le REGISTRE ENTIER, voies de l'audit comprises.

    Holm plutôt que Bonferroni : même garantie de taux d'erreur familial,
    strictement plus puissant. Le point qui compte n'est pas lequel des
    deux, c'est que `m` soit le nombre total de tests réellement tentés
    — sinon la correction ment dans le sens confortable.
    """
    rows = [r for r in ledger() if r.get("p") is not None]
    rows.sort(key=lambda r: r["p"])
    # m compte AUSSI les tests d'une famille dont seul l'extrême est
    # consigné (les 3 160 paires du §2, par exemple). Sans `m_extra`, la
    # correction mentirait dans le sens confortable.
    m = len(rows) + sum(int(r.get("m_extra", 0)) for r in ledger())
    out, still = [], True
    for i, r in enumerate(rows):
        thr = alpha / (m - i)
        sig = still and r["p"] <= thr
        still = sig
        out.append({**r, "holm_threshold": thr, "significant": bool(sig), "m_total": m})
    return out
