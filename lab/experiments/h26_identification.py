"""h26 — la pénalité d'identification, mesurée famille par famille.

Ce que le registre affiche, et ce qu'il tait
============================================
Le sommaire publie une hiérarchie de plafonds d'exploitabilité : marginal
+1,33 % (c0), rémanence uniforme +0,53 % et paires cachées +3,21 % (c1),
lags 1..306 +3,46 % (d2), quadratique +6,27 % (h24). **Toutes sont des
bornes d'OMNISCIENCE** : elles supposent que le joueur connaît la règle
biaisée. Le §3 bis a mesuré, pour la SEULE famille marginale, ce qu'un
joueur qui doit deviner la règle depuis les mêmes données en capte
réellement : 64 % à la frontière de détection, d'où un plafond réalisable
de +0,99 % au lieu de +1,33 %. Les §3 quater et §40 disent en toutes
lettres que cette pénalité n'est mesurée pour AUCUNE autre famille.

Ce fichier la mesure, en calquant la méthode de `c2_apprentissage.py`
(`identification()`), pour les quatre familles restantes :

  rémanence uniforme (c1)   M = d·I, d = 0,0013 à la frontière
  paires cachées (c1)       M = d·P dérangement, m = 50, d = 0,0071
  couplage à lag 204 (d2)   même famille, k0 = 204, m = 40, d = 0,008
  quadratique (h24)         tiers, m = 80, R = 2, θ = 0,080

Les amplitudes de frontière sont REPRISES des consignations c1/d2/h24 du
registre (power_at), jamais recalculées : relancer ces expériences pour
« vérifier » écrirait des doublons dans un registre partagé (règle n° 6,
erreur déjà commise dans ce dépôt et corrigée par `lab.dedupe()`).

Le protocole, par archive contaminée à biais CONNU par construction
===================================================================
Trois joueurs, tous en marche avant stricte (`lab.walk_forward`, warmup
20 000, soit 50 560 tirages évalués), contrôle de fuite `lab.leak_check`
sur chacun :

  BASE        grille fixe 1..10 — E[hits] = 2,5 par théorème (les quatre
              contaminations figent les marginales à 1/4) ;
  ORACLE      joue la règle réellement biaisée (les priorités de
              `informed_play` de c1/d2/h24, refaites en prédicteur pas à
              pas) — c'est la définition des plafonds d'omniscience ;
  IDENTIFICATEUR  estime la règle sur le SEUL passé, par la statistique
              exhaustive de la famille :
                - familles linéaires : la matrice de couplage empirique
                  Ĉ[n,j] = Cov^(y_n(t), x_j(t−k0)), mise à jour en ligne
                  (un produit extérieur par pas), score = Ĉ·(x−x̄) —
                  et non un classement par fréquence, qui n'est exhaustif
                  que du cas marginal ;
                - variante « amax » (structure connue : une source par
                  numéro) : ĵ(n) = argmax_j Ĉ[n,j], score = Ĉ[n,ĵ]·xc[ĵ] ;
                - rémanence : l'identificateur exhaustif de la famille
                  M = d·I est le SIGNE du recouvrement moyen passé
                  (1 paramètre) ; la matrice pleine est mesurée à côté
                  pour chiffrer le prix de l'ignorance de la forme ;
                - quadratique : le tenseur des corrélations partielles de
                  h24 (part linéaire retirée par projection empirique sur
                  le passé), réajusté aux trois points de contrôle de c2
                  (20 000, 35 000, 50 000), en brut et en seuillé à
                  |Z| > 4,5 (le max de 252 800 cellules N(0,1) est ≈ 4,7 :
                  en deçà du seuil, une cellule est indiscernable du bruit
                  de son propre tenseur).

  PART CAPTÉE = (identifié − 2,5) / (oracle − 2,5), par amplitude, dont
  l'amplitude de frontière — c'est elle qui fixe le plafond réalisable
  (réalisable = part captée × plafond d'omniscience publié).

Réutilisation, pas réécriture
=============================
Les générateurs de contamination sont ceux des expériences d'origine :
`gen_conditional` et `pairing` importés de `c1_conditionnel`,
`gen_lagged` importé de `d2_lags` (imports sans effet de bord, les deux
fichiers sont gardés par `if __name__`). `h24_couplage_quadratique`
s'exécute à l'import (il écrirait au registre) : ses fonctions
`make_rules`, `gen_quad`, `pair_z`, `_tri_tensor`, `informed_play` et ses
constantes (GAMMA, DELTA, IU, PAIR_ID, …) sont donc EXTRAITES de sa
source par l'AST et exécutées telles quelles — zéro ligne recopiée à la
main. L'extracteur capture aussi les affectations par indice
(`PAIR_ID[...] = ...`) : une première version ne le faisait pas,
PAIR_ID restait à −1, et toutes les sondes de mise au point lisaient la
dernière colonne du tenseur — l'assert sur les cellules hors diagonale de
PAIR_ID, plus bas, est le test de non-régression de cette erreur-là (la
diagonale, elle, reste légitimement à −1 : il n'y a pas de paire (i,i)).

Témoins et contrôles (règle n° 4)
=================================
 - témoin négatif : archives SRS pures, tous les joueurs doivent rendre
   ≈ 2,50 (un identificateur au-dessus de 2,5 sous H0 serait une fuite) ;
 - témoin positif : à grande amplitude, la part captée doit approcher
   100 % — un identificateur qui ne capte jamais rien est indistinguable
   d'un identificateur cassé ;
 - contre-épreuve des oracles : les moyennes en marche avant sont
   confrontées aux `informed_play` vectorisés de c1 et h24 sur les mêmes
   archives, et aux plafonds publiés (+0,0803, +0,1567…) ;
 - accord bulk/causal du prédicteur quadratique (précédent c2) : les
   scores pré-calculés par blocs et la voie causale pas à pas doivent
   coïncider ;
 - `lab.leak_check` sur chaque type de prédicteur, à la frontière.

Limites déclarées
=================
 1. Le « meilleur identificateur » est le meilleur DISPONIBLE ici : la
    statistique exhaustive de la famille en plug-in (+ 2 variantes, la
    meilleure des deux est retenue par point — léger biais optimiste,
    donc dans le sens qui SURESTIME le plafond réalisable, jamais
    l'inverse). Un estimateur plus fin (appariement global du
    dérangement, rétrécissement) relèverait un peu la part.
 2. Pour d2, la part est mesurée à LAG CONNU du joueur : identifier le
    lag parmi 306 est strictement plus dur, la part mesurée est un
    MAJORANT de la part réalisable de cette famille.
 3. L'identificateur quadratique est réajusté aux 3 points de contrôle de
    c2, les identificateurs linéaires en ligne à chaque pas ; l'écart de
    calendrier est chiffré par une variante contrôle (matrice linéaire
    aux mêmes 3 points) à la frontière des paires cachées.
 4. Part captée = ratio de deux moyennes bruitées : sous la frontière,
    le dénominateur est petit et le ratio instable — les erreurs-types
    sont propagées et affichées, et une part négative est un résultat
    (le joueur suit du bruit), pas un échec.
 5. Aucune statistique n'est calculée sur l'archive réelle : rien de
    neuf n'entre dans m de Holm (consignations sans p, comme c0.plafond).

Usage : python3 h26_identification.py [--dry]
        (--dry : archives raccourcies, réplicats réduits, AUCUNE écriture
        au registre — mise au point uniquement)
"""

import ast
import math
import os
import sys
import time

# Leçon de h24 : à ces formes de matrices, le multi-thread coûte plus que
# le calcul. Mono-thread, mesuré plus rapide et plus stable.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

import numpy as np
import lab
from c1_conditionnel import gen_conditional, pairing, informed_play as c1_informed_play, \
    t1_overlap, t2_lagcov
from d2_lags import gen_lagged

POOL, DRAWN, K = lab.POOL, lab.DRAWN, 10
DRY = "--dry" in sys.argv

N = 20_000 if DRY else 70_560
WARMUP = 6_000 if DRY else 20_000
CPS = (6_000, 11_000, 16_000) if DRY else (20_000, 35_000, 50_000)   # points de contrôle de c2 (§3 ter)
BLOCK = 2_500                       # les CPS tombent sur des frontières de bloc
assert all((c - WARMUP) % BLOCK == 0 for c in CPS), "CPS non alignés sur les blocs"
TAU_QUAD = 4.5                      # seuil de la variante seuillée (max de 252 800 N(0,1) ~ 4,7)
BASE_GRID = np.arange(1, K + 1)

T0 = time.time()


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------
# Réutilisation des générateurs de h24 (qui s'exécute à l'import)
# --------------------------------------------------------------------------

def borrow_h24():
    """Extrait de la source de h24 les définitions nécessaires, telles quelles.

    h24 n'est pas importable (son expérience tourne au niveau module et
    écrirait au registre). On prend donc les nœuds AST voulus — fonctions ET
    affectations, y compris par indice (`PAIR_ID[IU[0], IU[1]] = ...`) — et
    on les exécute dans un espace de noms dédié. Une première version ne
    capturait pas les affectations par indice : PAIR_ID restait à −1 et
    toute sonde qui s'en servait lisait la dernière colonne du tenseur.
    L'assert final est le test de non-régression de cette erreur.
    """
    path = os.path.join(_HERE, "h24_couplage_quadratique.py")
    want_fn = {"v_values", "make_rules", "gen_quad", "informed_play",
               "_tri_tensor", "pair_z", "q_stats"}
    want_as = {"IU", "NPAIR", "PAIR_ID", "_n", "INPAIR", "GAMMA", "DELTA"}
    src = open(path).read()

    def base_names(t):
        if isinstance(t, ast.Name):
            return {t.id}
        if isinstance(t, ast.Subscript):
            return base_names(t.value)
        if isinstance(t, ast.Tuple):
            out = set()
            for e in t.elts:
                out |= base_names(e)
            return out
        return set()

    segs, got = [], set()
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in want_fn:
            segs.append(ast.get_source_segment(src, node))
            got.add(node.name)
        elif isinstance(node, ast.Assign):
            names = set()
            for t in node.targets:
                names |= base_names(t)
            if names & want_as:
                segs.append(ast.get_source_segment(src, node))
                got |= names & want_as
    missing = (want_fn | want_as) - got
    assert not missing, f"définitions absentes de h24 : {missing}"
    ns = {"np": np, "math": math, "lab": lab, "POOL": POOL, "DRAWN": DRAWN, "K": K}
    exec("\n\n".join(segs), ns)
    _iu = ns["IU"]
    assert ns["PAIR_ID"][_iu[0], _iu[1]].min() >= 0 and ns["PAIR_ID"][_iu[1], _iu[0]].min() >= 0, \
        "PAIR_ID incomplet : affectations par indice non extraites"
    assert ns["v_values"]() == (1.0, -ns["GAMMA"], ns["DELTA"])
    return ns


H24 = borrow_h24()
IU, PAIR_ID = H24["IU"], H24["PAIR_ID"]
GAMMA, DELTA = H24["GAMMA"], H24["DELTA"]
make_rules, gen_quad = H24["make_rules"], H24["gen_quad"]
h24_informed_play, h24_q_stats = H24["informed_play"], H24["q_stats"]
_tri_tensor, pair_z = H24["_tri_tensor"], H24["pair_z"]


# --------------------------------------------------------------------------
# Outils communs
# --------------------------------------------------------------------------

def as_archive(mask):
    """Enrobe un masque contaminé dans une Archive jouable en marche avant."""
    n = len(mask)
    nums = np.sort(np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1,
                   axis=1).astype(np.int8)
    return lab.Archive(np.arange(n), np.zeros(n, np.int64), nums,
                       np.full(n, -1, np.int8), np.full(n, -1, np.int8), mask.copy())


def tiebreak(t, scale):
    """Bruit de départage DÉTERMINISTE en t : leak_check exige que deux appels
    au même t rendent le même choix. Utilisé seulement quand les scores sont
    discrets (oracles) — les scores continus n'ont pas d'ex æquo."""
    return np.random.default_rng(900_000_000 + t).random(POOL, dtype=np.float32) * np.float32(scale)


def topk(score):
    return np.argpartition(-score, K)[:K] + 1


def walk_mean(arch, fn):
    return float(lab.walk_forward(arch, fn, k=K, warmup=WARMUP).mean())


def base_predict(past, t):
    return BASE_GRID


# --------------------------------------------------------------------------
# Oracles — la règle connue, en prédicteur pas à pas
# --------------------------------------------------------------------------

class OracleLin:
    """Priorités de informed_play (c1/d2) : chaud 2 > neutre 1 > froid 0."""

    def __init__(self, mod, msrc, k0=1):
        self.mod, self.msrc, self.k0 = mod, msrc, k0

    def __call__(self, past, t):
        prev = past.mask[t - self.k0]
        prio = np.ones(POOL, np.float32)
        prio[self.mod] = np.where(prev[self.msrc], np.float32(2.0), np.float32(0.0))
        return topk(prio + tiebreak(t, 0.5))


class OracleQuad:
    """Le score exact de la règle de h24 : v = both − γ·one + δ·none."""

    def __init__(self, mod, SI, SJ):
        self.mod, self.SI, self.SJ = mod, SI, SJ
        self.R = SI.shape[1]

    def __call__(self, past, t):
        prev = past.mask[t - 1]
        pi, pj = prev[self.SI], prev[self.SJ]
        both = (pi & pj).sum(1)
        one = (pi ^ pj).sum(1)
        score = np.zeros(POOL, np.float32)
        score[self.mod] = both - GAMMA * one + DELTA * (self.R - both - one)
        return topk(score + tiebreak(t, 1e-3))


# --------------------------------------------------------------------------
# Identificateurs linéaires — matrice de couplage empirique, en ligne
# --------------------------------------------------------------------------

class IdentLin:
    """Ĉ[n,j] = Cov^(y_n(s), x_j(s−k0)) sur les paires du passé, en ligne.

    variant = 'raw'      score(n) = Σ_j Ĉ[n,j]·(x_j(t−k0) − x̄_j)
              'amax'     ĵ(n) = argmax_j Ĉ[n,j], score(n) = Ĉ[n,ĵ]·xc[ĵ]
                         (structure connue : une source par numéro)
              'raw_cps'  comme raw mais matrice GELÉE aux points de
                         contrôle CPS — contrôle du calendrier de
                         réajustement pour la comparaison avec le
                         quadratique (limite n° 3 du bandeau).
    L'état n'avance qu'avec des lignes STRICTEMENT antérieures à t ; un
    appel en arrière lève une erreur (garde anti-réutilisation)."""

    def __init__(self, arch, k0=1, variant="raw"):
        self.arch, self.k0, self.variant = arch, k0, variant
        self.ts = k0                       # prochain s à absorber (paires (s−k0, s))
        self.T = 0
        self.S = np.zeros((POOL, POOL))
        self.sx = np.zeros(POOL)
        self.sy = np.zeros(POOL)
        self.snap = {}                     # cp -> (C, mx) gelés (variant raw_cps)

    def _absorb(self, upto):
        if upto > self.ts:
            X = self.arch.mask[self.ts - self.k0: upto - self.k0].astype(np.float32)
            Y = self.arch.mask[self.ts: upto].astype(np.float32)
            self.S += (Y.T @ X).astype(np.float64)
            self.sx += X.sum(0, dtype=np.float64)
            self.sy += Y.sum(0, dtype=np.float64)
            self.T += len(Y)
            self.ts = upto

    def _advance(self, t):
        if t < self.ts:
            raise RuntimeError("IdentLin réutilisé en arrière — état non causal")
        for cp in CPS:
            if self.ts < cp <= t:
                self._absorb(cp)
                self.snap[cp] = self._matrix()
        self._absorb(t)

    def _matrix(self):
        mx = self.sx / self.T
        my = self.sy / self.T
        return self.S / self.T - np.outer(my, mx), mx

    def __call__(self, past, t):
        self._advance(t)
        if self.variant == "raw_cps":
            cp = max((c for c in CPS if c <= t), default=None)
            C, mx = self.snap[cp]
        else:
            C, mx = self._matrix()
        x = past.mask[t - self.k0]
        xc = x.astype(np.float64) - mx
        if self.variant == "amax":
            jhat = C.argmax(1)
            score = C[np.arange(POOL), jhat] * xc[jhat]
        else:
            score = C @ xc
        return topk(score.astype(np.float32))


class IdentScalarDiag:
    """L'identificateur exhaustif de la famille M = d·I : le signe du
    recouvrement moyen passé (1 paramètre). Recouvrement > 5 (l'espérance
    exacte E[O] = 20·20/80, théorème) -> jouer 10 des 20 du tirage
    précédent ; sinon les éviter."""

    def __init__(self, arch):
        self.arch = arch
        self.ts = 1
        self.osum = 0.0
        self.T = 0

    def _advance(self, t):
        if t < self.ts:
            raise RuntimeError("IdentScalarDiag réutilisé en arrière")
        if t > self.ts:
            m = self.arch.mask
            self.osum += float((m[self.ts:t] & m[self.ts - 1:t - 1]).sum())
            self.T += t - self.ts
            self.ts = t

    def __call__(self, past, t):
        self._advance(t)
        prev = past.mask[t - 1].astype(np.float32)
        score = prev if self.osum / self.T > 5.0 else np.float32(1.0) - prev
        return topk(score + tiebreak(t, 0.5))


# --------------------------------------------------------------------------
# Identificateur quadratique — le tenseur de h24, estimé sur le passé
# --------------------------------------------------------------------------

def quad_fit(win):
    """Même algèbre que pair_z (h24), mais rend les COMPOSANTES du modèle :
    projection linéaire B, poids plug-in Wraw = C/varR, tenseur standardisé
    Z (pour le seuillage). Vérifié plus bas contre pair_z cellule à cellule."""
    xb, yb = win[:-1], win[1:]
    x = xb.astype(np.float32)
    T = x.shape[0]
    Gx = _tri_tensor(xb, x).astype(np.float64)
    Gy = _tri_tensor(yb, x).astype(np.float64)
    Sxx = (x.T @ x).astype(np.float64)
    Syx = (yb.astype(np.float32).T @ x).astype(np.float64)
    mx, my = xb.mean(0), yb.mean(0)
    mw = Sxx / T
    Cxw = Gx / T - mx[:, None, None] * mw[None, :, :]
    Cyw = Gy / T - my[:, None, None] * mw[None, :, :]
    Cxx = Sxx / T - np.outer(mx, mx)
    Cyx = Syx / T - np.outer(my, mx)
    P = np.linalg.pinv(Cxx, rcond=1e-8)
    B3 = np.tensordot(P, Cxw, axes=(1, 0))
    C = Cyw - np.tensordot(Cyx, B3, axes=(1, 0))
    varR = mw * (1.0 - mw) - (Cxw * B3).sum(0)
    vary = my * (1.0 - my)
    i0, j0 = IU
    Cmat = C[:, i0, j0]
    varRv = varR[i0, j0]
    Z = Cmat * math.sqrt(T) / np.sqrt(vary[:, None] * varRv[None, :])
    return dict(mx=mx.astype(np.float32), mwv=mw[i0, j0].astype(np.float32),
                B=B3[:, i0, j0].astype(np.float32),
                Wraw=(Cmat / varRv).astype(np.float32),
                Wthr=(Cmat / varRv * (np.abs(Z) > TAU_QUAD)).astype(np.float32),
                Z=Z, T=T)


class IdentQuad:
    """Score(n | D_{t−1}) = Σ_p Ŵ[n,p]·r_p(D_{t−1}), Ŵ estimé sur [0, cp).

    Deux voies, précédent c2 : `bulk` pré-calcule les scores par blocs de
    {BLOCK} tirages (GEMM), `causal` refait la même ligne depuis `past` —
    c'est elle que leak_check éprouve, et l'accord des deux est vérifié.
    Les fits (un par point de contrôle) sont partagés par les variantes."""

    def __init__(self, arch):
        self.arch = arch
        self.fits = {}
        self.blocks = {}

    def _fit(self, cp):
        if cp not in self.fits:
            self.fits[cp] = quad_fit(self.arch.mask[:cp])
        return self.fits[cp]

    @staticmethod
    def _cp(t):
        return max(c for c in CPS if c <= t)

    def _row(self, f, x):
        """Résidu quadratique d'UN tirage x (float32, 80) sous le fit f."""
        wv = x[IU[0]] * x[IU[1]]
        return (wv - f["mwv"]) - (x - f["mx"]) @ f["B"]

    def _block(self, bi):
        if bi not in self.blocks:
            t0 = WARMUP + bi * BLOCK
            t1 = min(N, t0 + BLOCK)
            f = self._fit(self._cp(t0))
            X = self.arch.mask[t0 - 1:t1 - 1].astype(np.float32)
            R = (X[:, IU[0]] * X[:, IU[1]] - f["mwv"]) - (X - f["mx"]) @ f["B"]
            self.blocks[bi] = {"raw": R @ f["Wraw"].T, "thr": R @ f["Wthr"].T}
        return self.blocks[bi]

    def predictor(self, variant):
        def fn(past, t):
            bi = (t - WARMUP) // BLOCK
            return topk(self._block(bi)[variant][t - WARMUP - bi * BLOCK])
        return fn

    def causal(self, variant):
        def fn(past, t):
            f = self._fit(self._cp(t))
            r = self._row(f, past.mask[t - 1].astype(np.float32))
            w = f["Wraw"] if variant == "raw" else f["Wthr"]
            return topk(w @ r)
        return fn

    def accord(self, variant, spots):
        """Écart max bulk/causal sur quelques t — même contrat que
        c2.assert_same : si les deux voies divergent, tout le reste est faux."""
        worst = 0.0
        for t in spots:
            bi = (t - WARMUP) // BLOCK
            f = self._fit(self._cp(t))
            r = self._row(f, self.arch.mask[t - 1].astype(np.float32))
            w = f["Wraw"] if variant == "raw" else f["Wthr"]
            a = self._block(bi)[variant][t - WARMUP - bi * BLOCK]
            b = w @ r
            scale = max(float(np.abs(a).max()), 1e-9)
            worst = max(worst, float(np.abs(a - b).max()) / scale)
        return worst


# --------------------------------------------------------------------------
# 0. Registre : provenance des frontières, nulls des détecteurs (repris)
# --------------------------------------------------------------------------

say("=" * 78)
say("h26 — DÉTECTER N'EST PAS IDENTIFIER, POUR CHAQUE FAMILLE DE BIAIS")
say("=" * 78)
if DRY:
    say("*** DRY RUN : N=%d, réplicats réduits, AUCUNE écriture au registre ***" % N)

LED = {r["id"]: r for r in lab.ledger()}
for need in ("c1.plafond_cond", "c1.overlap_real", "c1.matrix_real",
             "d2.plafond_lags", "h24.plafond_quad", "h24.quad_diffus",
             "h24.quad_remanence"):
    assert need in LED, f"entrée de registre absente : {need}"

# Frontières et plafonds d'omniscience, repris des consignations (power_at/notes)
FRONT = {
    "diag": dict(d=0.0013, plafond=0.53, src="c1.overlap_real / c1.plafond_cond"),
    "pair": dict(d=0.0071, m=50, plafond=3.21, src="c1.matrix_real / c1.plafond_cond"),
    "lag": dict(d=0.0080, m=40, k0=204, plafond=3.46, src="d2.plafond_lags"),
    "quad": dict(th=0.080, m=80, R=2, plafond=6.27, src="h24.plafond_quad"),
}
say("\nfrontières de détection reprises du registre (jamais recalculées, règle n° 6) :")
for k, f in FRONT.items():
    amp = f.get("d", f.get("th"))
    say(f"  {k:<5} amplitude {amp}   plafond d'omniscience {f['plafond']:+.2f} %   [{f['src']}]")

# Nulls des détecteurs : SIMULÉS par c1/h24, relus du registre (pas retabulés)
DET = {
    "T1": (LED["c1.overlap_real"]["null_mean"], LED["c1.overlap_real"]["null_sd"]),
    "T2": (LED["c1.matrix_real"]["null_mean"], LED["c1.matrix_real"]["null_sd"]),
    "Q1": (LED["h24.quad_diffus"]["null_mean"], LED["h24.quad_diffus"]["null_sd"]),
    "Q3": (LED["h24.quad_remanence"]["null_mean"], LED["h24.quad_remanence"]["null_sd"]),
}
say("\nnulls des détecteurs relus du registre (simulés par c1/h24 sur N=70 560) :")
say("  T1 %.5f±%.5f   T2 %.4e±%.2e   Q1 %.0f±%.0f   Q3 %.0f±%.0f"
    % (DET["T1"] + DET["T2"] + DET["Q1"] + DET["Q3"]))
if DRY:
    say("  (dry : N réduit, la colonne détecteur n'est pas comparable — omise)")


def det_z(stat, key):
    mu, sd = DET[key]
    return (stat - mu) / sd


# --------------------------------------------------------------------------
# 1. Pré-enregistrement — avant toute mesure
# --------------------------------------------------------------------------

say("\n" + "-" * 78 + "\n1. PRÉ-ENREGISTREMENT")

DEC = ("mesure d'un ratio (part captée), pas un test : aucune hypothèse n'est "
       "rejetée, aucune statistique n'est calculée sur l'archive réelle, "
       "consigné sans p (n'entre pas dans le m de Holm, précédent c0.plafond)")
NULLDOC = ("archives contaminées à biais connu par construction (générateurs de "
           "c1/d2/h24 réutilisés), oracle et identificateur évalués en marche "
           "avant lab.walk_forward (warmup 20 000), leak_check sur chaque "
           "prédicteur ; base = 2,5 exacte (marginales figées à 1/4, "
           "contrôlée sur SRS et sur grille fixe)")

TOKS = {
    "diag": lab.preregister(
        "h26.ident_remanence",
        "Quelle part de l'avantage d'omniscience de la rémanence uniforme "
        "(c1, +0,53 % à d=0,0013) un joueur qui doit IDENTIFIER la règle depuis "
        "les mêmes données capte-t-il à la frontière de détection ?",
        "part captée = (identifié−2,5)/(oracle−2,5) à d=0,0013 ; identificateur "
        "exhaustif de la famille M=d·I : signe du recouvrement moyen passé, en "
        "ligne ; matrice de couplage pleine mesurée à côté (prix de l'ignorance "
        "de la forme)", NULLDOC, DEC, track="A"),
    "pair": lab.preregister(
        "h26.ident_paires",
        "Même question pour les paires cachées (c1, +3,21 % à d=0,0071, m=50) : "
        "la pénalité d'identification, non mesurée par §3 quater, y est-elle "
        "plus lourde que pour le marginal (64 % au §3 bis) ?",
        "part captée à d=0,0071 ; identificateur = matrice de couplage empirique "
        "Ĉ (80×80, statistique exhaustive de la famille), en ligne, variantes "
        "raw et argmax-source, la meilleure retenue", NULLDOC, DEC, track="A"),
    "lag": lab.preregister(
        "h26.ident_lags",
        "Même question pour le couplage à lag 204 (d2, +3,46 % à d=0,008, m=40), "
        "à LAG CONNU du joueur — la part mesurée est un MAJORANT de la part à "
        "lag inconnu (306 lags à départager)",
        "part captée à d=0,008, k0=204 connu ; identificateur = matrice de "
        "couplage empirique au lag 204, en ligne, variantes raw et argmax-source",
        NULLDOC, DEC, track="A"),
    "quad": lab.preregister(
        "h26.ident_quad",
        "Même question pour le couplage quadratique (h24, +6,27 % à θ=0,080, "
        "tiers m=80 R=2) : 252 800 coefficients à estimer — la pénalité "
        "annoncée « plus lourde qu'ailleurs » par §40, chiffrée",
        "part captée à θ=0,080 ; identificateur = tenseur des corrélations "
        "partielles de h24 estimé sur le passé, réajusté aux points de contrôle "
        "de c2 (20k/35k/50k), variantes brute et seuillée |Z|>4,5, la meilleure "
        "retenue", NULLDOC, DEC, track="A"),
}
for k, tk in TOKS.items():
    say(f"  {tk['id']:<22} scellé {tk['seal']}  à {tk['registered_at']}")


# --------------------------------------------------------------------------
# 2. Contrôles de construction — avant les mesures
# --------------------------------------------------------------------------

say("\n" + "-" * 78 + "\n2. CONTRÔLES DE CONSTRUCTION")

rngC = np.random.default_rng(26_000)

say("\n2a. quad_fit reproduit-il pair_z (h24) cellule à cellule ?")
_win = lab.srs(4_000, rngC)
_f = quad_fit(_win)
_gap = float(np.abs(_f["Z"] - pair_z(_win)).max())
say(f"    écart max sur 252 800 cellules : {_gap:.2e}")
assert _gap < 1e-9, "quad_fit ne reproduit pas pair_z"

say("\n2b. témoin négatif : archives SRS pures — tout le monde doit rendre ~2,50")
say(f"    {'joueur':<26}{'hits':>9}   (erreur-type ~ {1.36 / math.sqrt(N - WARMUP):.4f})")
for rep in range(1 if DRY else 2):
    srs_mask = lab.srs(N, rngC)
    arch = as_archive(srs_mask)
    mod_p, msrc_p = pairing(50, rngC)
    mod_q, SI_q, SJ_q = make_rules(80, 2, rngC, "tiers")
    iq = IdentQuad(arch)
    for lbl, fn in (("base (grille fixe)", base_predict),
                    ("oracle lin (règle fictive)", OracleLin(mod_p, msrc_p)),
                    ("ident matrice lin", IdentLin(arch)),
                    ("ident scalaire diag", IdentScalarDiag(arch)),
                    ("ident quad brut", iq.predictor("raw")),
                    ("ident quad seuillé", iq.predictor("thr"))):
        say(f"    {lbl:<26}{walk_mean(arch, fn):>9.4f}")

say("\n2c. contrôle de fuite (leak_check) sur chaque type de prédicteur,")
say("    archives contaminées à la frontière — décisif, pas déclaratif")
_pr = (4, 2) if DRY else (6, 4)     # (probes, repeats), comme c2

rngL = np.random.default_rng(26_001)
mod_d = msrc_d = np.arange(POOL)
cm = gen_conditional(N, mod_d, msrc_d, FRONT["diag"]["d"], rngL)
arch_d = as_archive(cm)
mod_p, msrc_p = pairing(FRONT["pair"]["m"], rngL)
cm = gen_conditional(N, mod_p, msrc_p, FRONT["pair"]["d"], rngL)
arch_p = as_archive(cm)
mod_l, msrc_l = pairing(FRONT["lag"]["m"], rngL)
cm = gen_lagged(N, FRONT["lag"]["k0"], mod_l, msrc_l, FRONT["lag"]["d"], rngL)
arch_l = as_archive(cm)
mod_q, SI_q, SJ_q = make_rules(FRONT["quad"]["m"], FRONT["quad"]["R"], rngL, "tiers")
cm = gen_quad(N, mod_q, SI_q, SJ_q, FRONT["quad"]["th"], rngL)
arch_q = as_archive(cm)

iq_leak = IdentQuad(arch_q)
_checks = (
    ("oracle linéaire (paires)", arch_p, OracleLin(mod_p, msrc_p)),
    ("oracle lag 204", arch_l, OracleLin(mod_l, msrc_l, k0=FRONT["lag"]["k0"])),
    ("oracle quadratique", arch_q, OracleQuad(mod_q, SI_q, SJ_q)),
    ("ident matrice (paires)", arch_p, IdentLin(arch_p)),
    ("ident amax (paires)", arch_p, IdentLin(arch_p, variant="amax")),
    ("ident matrice lag 204", arch_l, IdentLin(arch_l, k0=FRONT["lag"]["k0"])),
    ("ident scalaire (diag)", arch_d, IdentScalarDiag(arch_d)),
    ("ident quad causal brut", arch_q, iq_leak.causal("raw")),
    ("ident quad causal seuillé", arch_q, iq_leak.causal("thr")),
)
_all_clean = True
for lbl, arch, fn in _checks:
    ok, spots = lab.leak_check(arch, fn, k=K, warmup=WARMUP,
                               probes=_pr[0], repeats=_pr[1])
    _all_clean &= ok
    say(f"    {lbl:<28}{'propre' if ok else 'FUITE en ' + str(spots)}")
if not _all_clean:
    say("    -> FUITE DÉTECTÉE : résultats invalides, on s'arrête là.")
    sys.exit(1)

say("\n2d. accord bulk/causal du prédicteur quadratique (précédent c2)")
_spots = [WARMUP + 3, WARMUP + BLOCK + 7, min(N - 2, CPS[-1] + 11)]
for v in ("raw", "thr"):
    g = iq_leak.accord(v, _spots)
    say(f"    variante {v:<5} écart relatif max {g:.1e}")
    assert g < 1e-3, "les deux voies divergent"

say("\n2e. contre-épreuve des oracles : marche avant vs informed_play vectorisé")
rngX = np.random.default_rng(26_002)
_wf = walk_mean(arch_p, OracleLin(mod_p, msrc_p))
_vec = c1_informed_play(arch_p.mask, mod_p, msrc_p, rngX)[0]
say(f"    paires cachées d={FRONT['pair']['d']}: marche avant {_wf:.4f}  "
    f"informed_play (c1) {_vec:.4f}  plafond publié 2,5{'+0.0803' if not DRY else ' (dry)'}")
_wfq = walk_mean(arch_q, OracleQuad(mod_q, SI_q, SJ_q))
_vecq = h24_informed_play(arch_q.mask, mod_q, SI_q, SJ_q, rngX)[0]
say(f"    quadratique θ={FRONT['quad']['th']}: marche avant {_wfq:.4f}  "
    f"informed_play (h24) {_vecq:.4f}  plafond publié 2,5{'+0.1567' if not DRY else ' (dry)'}")


# --------------------------------------------------------------------------
# 3. La mesure — part captée par famille et par amplitude
# --------------------------------------------------------------------------

def agg(vals):
    v = np.asarray(vals, float)
    return float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else float("nan")


def part_se(iv, ise, ov, ose):
    """Erreur-type du ratio (identifié−2,5)/(oracle−2,5), méthode delta."""
    if abs(ov) < 1e-12:
        return float("nan")
    p = iv / ov
    return math.sqrt(ise ** 2 + p * p * ose ** 2) / abs(ov)


def run_family(seed, grid, reps_grid, gen_one, idents, det_key=None, det_stat=None):
    """Balaye les amplitudes. gen_one(amp, rng) -> (arch, oracle_fn, extras).
    idents : liste de (label, factory(arch, extras)). Renvoie les lignes agrégées."""
    rng = np.random.default_rng(seed)
    rows = []
    for amp, reps in zip(grid, reps_grid):
        acc = {lbl: [] for lbl, _ in idents}
        acc.update(base=[], oracle=[], det=[])
        for rep in range(reps):
            arch, oracle_fn, extras = gen_one(amp, rng)
            acc["base"].append(walk_mean(arch, base_predict))
            acc["oracle"].append(walk_mean(arch, oracle_fn))
            for lbl, factory in idents:
                acc[lbl].append(walk_mean(arch, factory(arch, extras)))
            if det_stat is not None and not DRY:
                acc["det"].append(det_z(det_stat(arch.mask), det_key))
        row = {"amp": amp, "reps": reps,
               "base": agg(acc["base"]), "oracle": agg(acc["oracle"]),
               "det": agg(acc["det"])[0] if acc["det"] else float("nan")}
        for lbl, _ in idents:
            row[lbl] = agg(acc[lbl])
        rows.append(row)
    return rows


def show_family(title, rows, ident_lbls, det_name):
    say(f"\n{title}")
    hdr = f"  {'amp':>8}{'z(' + det_name + ')':>9}{'base':>9}{'oracle':>17}"
    for l in ident_lbls:
        hdr += f"{l:>17}"
    hdr += f"{'part captée*':>15}"
    say(hdr)
    for r in rows:
        ov, ose = r["oracle"]
        best = max(ident_lbls, key=lambda l: r[l][0])
        iv, ise = r[best]
        adv_o, adv_i = ov - 2.5, iv - 2.5
        p = adv_i / adv_o if abs(adv_o) > 1e-9 else float("nan")
        pse = part_se(adv_i, ise, adv_o, ose)
        line = f"  {r['amp']:>8.4f}{r['det']:>+9.1f}{r['base'][0]:>9.4f}" \
               f"{ov:>10.4f}±{ose:.4f}"
        for l in ident_lbls:
            line += f"{r[l][0]:>10.4f}±{r[l][1]:.4f}"
        line += f"{p:>+9.0%}±{pse:.0%}"
        say(line)
    say("  (* part de la MEILLEURE variante ; base jouée en contrôle, part calculée sur 2,5 exact)")


def part_at(rows, amp, ident_lbls):
    r = next(x for x in rows if abs(x["amp"] - amp) < 1e-9)
    best = max(ident_lbls, key=lambda l: r[l][0])
    adv_o = r["oracle"][0] - 2.5
    adv_i = r[best][0] - 2.5
    return {"part": adv_i / adv_o, "se": part_se(adv_i, r[best][1], adv_o, r["oracle"][1]),
            "adv_o": adv_o, "adv_i": adv_i, "se_i": r[best][1], "se_o": r["oracle"][1],
            "best": best, "reps": r["reps"]}


say("\n" + "-" * 78 + "\n3. LA MESURE — part captée par famille")
say(f"\nMarche avant : warmup {WARMUP}, {N - WARMUP} tirages évalués par archive.")
say("Chaque réplicat tire une RÈGLE neuve (pairing/make_rules) puis une archive")
say("contaminée neuve ; l'oracle joue la règle, l'identificateur ne voit que le passé.")

# --- 3a. rémanence uniforme --------------------------------------------------
GRID_DIAG = ((0.0013, 0.0060), (2, 2)) if DRY else \
            ((0.0007, 0.0013, 0.0026, 0.0060), (4, 10, 4, 3))


def gen_diag(amp, rng):
    cm = gen_conditional(N, np.arange(POOL), np.arange(POOL), amp, rng)
    arch = as_archive(cm)
    return arch, OracleLin(np.arange(POOL), np.arange(POOL)), None


IDENTS_DIAG = [("scalaire", lambda a, x: IdentScalarDiag(a)),
               ("matrice", lambda a, x: IdentLin(a))]
t0 = time.time()
rows_diag = run_family(26_101, GRID_DIAG[0], GRID_DIAG[1], gen_diag, IDENTS_DIAG,
                       det_key="T1", det_stat=t1_overlap)
show_family(f"3a. RÉMANENCE UNIFORME (M = d·I) — frontière d = {FRONT['diag']['d']} "
            f"[{time.time() - t0:.0f}s]", rows_diag, ["scalaire", "matrice"], "T1")
say("  L'identificateur exhaustif de cette famille tient en 1 paramètre (le signe")
say("  du recouvrement) : la part devrait être haute dès la frontière. La matrice")
say("  pleine (6 400 paramètres pour une famille qui en a 1) chiffre le prix de")
say("  l'ignorance de la forme.")

# --- 3b. paires cachées ------------------------------------------------------
GRID_PAIR = ((0.0071, 0.0300), (2, 2)) if DRY else \
            ((0.0040, 0.0071, 0.0140, 0.0300), (4, 8, 4, 3))


def gen_pair(amp, rng):
    mod, msrc = pairing(FRONT["pair"]["m"], rng)
    cm = gen_conditional(N, mod, msrc, amp, rng)
    return as_archive(cm), OracleLin(mod, msrc), (mod, msrc)


IDENTS_PAIR = [("matrice", lambda a, x: IdentLin(a)),
               ("amax", lambda a, x: IdentLin(a, variant="amax"))]
t0 = time.time()
rows_pair = run_family(26_102, GRID_PAIR[0], GRID_PAIR[1], gen_pair, IDENTS_PAIR,
                       det_key="T2", det_stat=t2_lagcov)
show_family(f"3b. PAIRES CACHÉES (m = {FRONT['pair']['m']}) — frontière d = "
            f"{FRONT['pair']['d']} [{time.time() - t0:.0f}s]",
            rows_pair, ["matrice", "amax"], "T2")

# contrôle du calendrier : matrice gelée aux 3 points de contrôle de c2
say("\n  contrôle du calendrier (limite n° 3) : matrice linéaire GELÉE aux points")
say("  de contrôle de c2 (comme l'identificateur quadratique), à la frontière :")
rngS = np.random.default_rng(26_500)
_cps_vals = []
for rep in range(2 if DRY else 4):
    mod, msrc = pairing(FRONT["pair"]["m"], rngS)
    cm = gen_conditional(N, mod, msrc, FRONT["pair"]["d"], rngS)
    arch = as_archive(cm)
    on = walk_mean(arch, IdentLin(arch))
    cps = walk_mean(arch, IdentLin(arch, variant="raw_cps"))
    _cps_vals.append((on, cps))
_on, _one = agg([v[0] for v in _cps_vals])
_cp, _cpe = agg([v[1] for v in _cps_vals])
say(f"    en ligne {_on:.4f}±{_one:.4f}   gelée aux cps {_cp:.4f}±{_cpe:.4f}   "
    f"écart {(_on - _cp):+.4f}")

# --- 3c. couplage à lag 204 (lag CONNU) -------------------------------------
GRID_LAG = ((0.0080,), (2,)) if DRY else ((0.0080, 0.0200), (6, 3))


def gen_lag(amp, rng):
    mod, msrc = pairing(FRONT["lag"]["m"], rng)
    k0 = FRONT["lag"]["k0"]
    cm = gen_lagged(N, k0, mod, msrc, amp, rng)
    return as_archive(cm), OracleLin(mod, msrc, k0=k0), (mod, msrc)


IDENTS_LAG = [("matrice", lambda a, x: IdentLin(a, k0=FRONT["lag"]["k0"])),
              ("amax", lambda a, x: IdentLin(a, k0=FRONT["lag"]["k0"], variant="amax"))]
t0 = time.time()
rows_lag = run_family(26_103, GRID_LAG[0], GRID_LAG[1], gen_lag, IDENTS_LAG)
show_family(f"3c. COUPLAGE À LAG {FRONT['lag']['k0']} (m = {FRONT['lag']['m']}, lag "
            f"CONNU du joueur) — frontière d = {FRONT['lag']['d']} [{time.time() - t0:.0f}s]",
            rows_lag, ["matrice", "amax"], "—")
say("  Lag connu : la part mesurée MAJORE la part réalisable de la famille d2")
say("  (identifier le lag parmi 306 est strictement plus dur).")

# --- 3d. quadratique ---------------------------------------------------------
GRID_QUAD = ((0.080, 0.400), (2, 2)) if DRY else \
            ((0.050, 0.080, 0.160, 0.300, 0.600), (3, 8, 3, 3, 2))


def gen_quad_arch(amp, rng):
    mod, SI, SJ = make_rules(FRONT["quad"]["m"], FRONT["quad"]["R"], rng, "tiers")
    cm = gen_quad(N, mod, SI, SJ, amp, rng)
    arch = as_archive(cm)
    # un IdentQuad par archive, passé par extras : les deux variantes partagent
    # ses fits et ses blocs, et tout est libéré à la fin du réplicat
    return arch, OracleQuad(mod, SI, SJ), (mod, SI, SJ, IdentQuad(arch))


IDENTS_QUAD = [("brut", lambda a, x: x[3].predictor("raw")),
               ("seuillé", lambda a, x: x[3].predictor("thr"))]


def quad_det(mask):
    q1, _, q3 = h24_q_stats(mask)
    return q1                     # z(Q1) affiché ; Q3 ~ 0 sur la famille tiers


t0 = time.time()
rows_quad = run_family(26_104, GRID_QUAD[0], GRID_QUAD[1], gen_quad_arch,
                       IDENTS_QUAD, det_key="Q1", det_stat=quad_det)
show_family(f"3d. QUADRATIQUE (tiers, m = {FRONT['quad']['m']}, R = {FRONT['quad']['R']}) "
            f"— frontière θ = {FRONT['quad']['th']} [{time.time() - t0:.0f}s]",
            rows_quad, ["brut", "seuillé"], "Q1")
say("  252 800 coefficients à estimer : à la frontière les cellules vraies sont à")
say("  |Z| ≈ 2-3 sous un plancher de bruit à ≈ 4,7 — indiscernables du bruit de")
say("  leur propre tenseur. La variante seuillée est le témoin du haut : à grande")
say("  amplitude elle doit retrouver la règle.")


# --------------------------------------------------------------------------
# 4. La table — plafonds réalisables
# --------------------------------------------------------------------------

say("\n" + "=" * 78 + "\n4. LA TABLE — ce que les plafonds d'omniscience valent pour un vrai joueur")

# diag : l'identificateur PRÉ-ENREGISTRÉ est le scalaire (statistique
# exhaustive de M = d·I) ; la matrice pleine est chiffrée à côté.
P_DIAG = part_at(rows_diag, FRONT["diag"]["d"], ["scalaire"])
P_DIAG_MAT = part_at(rows_diag, FRONT["diag"]["d"], ["matrice"])
P_PAIR = part_at(rows_pair, FRONT["pair"]["d"], ["matrice", "amax"])
P_LAG = part_at(rows_lag, FRONT["lag"]["d"], ["matrice", "amax"])
P_QUAD = part_at(rows_quad, FRONT["quad"]["th"], ["brut", "seuillé"])

say(f"\n{'famille':<34}{'omniscience':>12}{'part captée':>16}{'réalisable':>12}")
say(f"{'marginal (c0 ; part : §3 bis/c2)':<34}{'+1,33 %':>12}{'64 % (repris)':>16}{'+0,99 %':>12}")
for lbl, P, key in (("rémanence uniforme (c1)", P_DIAG, "diag"),
                    ("paires cachées (c1)", P_PAIR, "pair"),
                    ("lags, lag connu (d2, majorant)", P_LAG, "lag"),
                    ("quadratique (h24)", P_QUAD, "quad")):
    pl = FRONT[key]["plafond"]
    say(f"{lbl:<34}{pl:>+11.2f} %{P['part']:>+9.0%} ±{P['se']:>4.0%}"
        f"{pl * P['part']:>+11.2f} %")
say("\n(réalisable = part captée à la frontière × plafond d'omniscience publié ;")
say(" identificateur retenu par famille : "
    f"diag « {P_DIAG['best']} » (pré-enregistré), paires « {P_PAIR['best']} », "
    f"lag « {P_LAG['best']} », quad « {P_QUAD['best']} »)")
say(f"\n prix de l'ignorance de la forme, famille rémanence : la matrice pleine")
say(f" (6 400 paramètres pour une famille qui en a 1) ne capte que "
    f"{P_DIAG_MAT['part']:+.0%} ± {P_DIAG_MAT['se']:.0%},")
say(f" contre {P_DIAG['part']:+.0%} ± {P_DIAG['se']:.0%} pour le signe du recouvrement seul.")


# --------------------------------------------------------------------------
# 5. Registre
# --------------------------------------------------------------------------

say("\n" + "-" * 78 + "\n5. REGISTRE")

if DRY:
    say("*** DRY RUN : rien n'est écrit au registre ***")
else:
    done = {r["id"] for r in lab.ledger()}
    if {t["id"] for t in TOKS.values()} & done:
        say("entrées h26 déjà présentes — pas de doublon écrit (règle n° 6)")
    else:
        def ramp(rows, lbls):
            out = []
            for r in rows:
                best = max(lbls, key=lambda l: r[l][0])
                adv_o, adv_i = r["oracle"][0] - 2.5, r[best][0] - 2.5
                p = adv_i / adv_o if abs(adv_o) > 1e-9 else float("nan")
                out.append(f"amp={r['amp']}: oracle {adv_o:+.4f}, ident {adv_i:+.4f} "
                           f"({best}), part {p:+.0%}")
            return " ; ".join(out)

        extra_note = {
            "diag": (f" ; matrice pleine à la même frontière : "
                     f"{P_DIAG_MAT['part']:+.0%}±{P_DIAG_MAT['se']:.0%} "
                     f"(prix de l'ignorance de la forme)"),
            "pair": "", "lag": "", "quad": "",
        }
        for key, P, rows, lbls in (("diag", P_DIAG, rows_diag, ["scalaire", "matrice"]),
                                   ("pair", P_PAIR, rows_pair, ["matrice", "amax"]),
                                   ("lag", P_LAG, rows_lag, ["matrice", "amax"]),
                                   ("quad", P_QUAD, rows_quad, ["brut", "seuillé"])):
            pl = FRONT[key]["plafond"]
            lab.record(
                TOKS[key], observed=P["part"], null=None, p=None,
                power_at=f"rampe mesurée ({N - WARMUP} tirages évalués/archive) : "
                         + ramp(rows, lbls),
                verdict=f"part captée {P['part']:+.0%} ± {P['se']:.0%} à la frontière "
                        f"-> plafond réalisable {pl * P['part']:+.2f} % "
                        f"(omniscience {pl:+.2f} %)",
                notes=(f"identificateur retenu : {P['best']} ; oracle à la frontière "
                       f"{P['adv_o']:+.4f}±{P['se_o']:.4f} hits (publié : voir "
                       f"{FRONT[key]['src']}), identifié {P['adv_i']:+.4f}±{P['se_i']:.4f} "
                       f"sur {P['reps']} archives ; leak_check propre sur tous les "
                       f"prédicteurs ; base 2,5 exacte contrôlée (SRS + grille fixe) ; "
                       f"limites : meilleure de 2 variantes par point (léger biais "
                       f"optimiste, sens conservateur pour la conclusion), "
                       + ("lag connu -> majorant ; " if key == "lag" else "")
                       + "générateurs de c1/d2/h24 réutilisés" + extra_note[key]))
            say(f"  consigné {TOKS[key]['id']:<22} part {P['part']:+.0%} "
                f"-> réalisable {pl * P['part']:+.2f} %")

say(f"\n{'=' * 78}\ntotal {time.time() - T0:.0f}s")
