"""h24 — le couplage QUADRATIQUE conditionnel, la famille que rien ne borne.

Ce que le registre ferme déjà, et ce qu'il laisse ouvert
========================================================
`c1_conditionnel.py` borne la dépendance conditionnelle de PREMIER ORDRE
LINÉAIRE au lag 1 :

    P(n ∈ D_{t+1} | D_t) = 1/4 + Σ_j M[n,j]·(x_j(t) − 1/4)

`T2 = ‖Ĉ‖²_F` sur les 6 400 covariances croisées couvre TOUTE matrice M —
rémanence, répulsion, paires cachées — et c'est de là que sort le plafond de
+3,21 % annoncé comme « le plafond de toute la piste A ». `d2_lags.py` étend
le même couple de statistiques à 306 décalages (+3,46 %). Mais c1 écrit
lui-même, en toutes lettres, ce qu'il ne couvre pas :

    « Une dépendance NON LINÉAIRE du tirage complet (fonction de
      combinaisons), elle, n'est pas bornée ici — c'est la limite ouverte
      que ce script lègue. »

`d3_nonlineaire.py` a répondu à cet appel par trois angles, et les trois
réduisent le tirage à un SCALAIRE avant de regarder quoi que ce soit : la
forme de la loi du recouvrement O(t,t+1) (S1), la corrélation et
l'information mutuelle entre recouvrements successifs (S2, S3), un gradient
boosting sur six traits agrégés. Un scalaire par tirage, là où le tirage en
porte 61,6 bits. La famille « non linéaire du tirage COMPLET » reste donc
exactement aussi ouverte qu'avant d3 — et, n'ayant aucun test, elle n'a
aucun plafond d'exploitabilité : ni c0 (marginal) ni c1 (linéaire lag-1) ne
la touchent.

L'objet de ce fichier
=====================
Le premier terme non linéaire du développement, et le seul qui reste
calculable sur 70 560 tirages : le couplage QUADRATIQUE

    P(n ∈ D_{t+1} | D_t) = 1/4 + Σ_{i<j} M2[n,(i,j)]·r_{ij}(D_t)

où r_{ij} est l'indicatrice « i ET j sortis en t », débarrassée de sa part
linéaire. 80 × 3 160 = 252 800 paramètres, contre 6 400 pour c1. La question
n'est pas « une paire appelle-t-elle un numéro ? » en général — un tel biais
laisse une trace linéaire que c1 verrait — mais : reste-t-il une dépendance
aux PAIRES une fois retirée toute la dépendance aux numéros ?

La règle du dérangement de c1 (« le numéro i appelle le numéro j ») est
invisible du recouvrement mais visible de Ĉ. Ici la règle est « la paire
(i, j) appelle le numéro n », et une fois orthogonalisée elle est invisible
de Ĉ **par construction algébrique**, pas par chance : c'est démontré plus
bas en arithmétique exacte, puis mesuré.

Les trois statistiques, une par régime de défaut
================================================
  Q1  Σ Z² sur les 252 800 cellules       — structure DIFFUSE (beaucoup de
                                            règles faibles). C'est la
                                            généralisation directe du T2 de
                                            c1, un cran plus haut en degré.
  Q2  max |Z| sur les mêmes cellules      — une règle FORTE et isolée. Le
                                            max ne voit pas le diffus, la
                                            somme des carrés ne voit pas
                                            l'isolé : la dichotomie que d1
                                            a mesurée sur les triplets.
  Q3  Σ Z² sur les 6 320 cellules n ∈ {i,j} — la « rémanence quadratique » :
                                            une paire qui rappelle l'un de
                                            ses propres membres. Sous-espace
                                            80 fois plus petit, donc 4 fois
                                            plus sensible sur cette
                                            sous-famille (√ du nombre de
                                            cellules).

Z[n,(i,j)] est la corrélation, standardisée à √T, entre l'appartenance de n
au tirage t+1 et la PART DE LA PAIRE (i,j) NON EXPLIQUÉE PAR LES NUMÉROS
PRIS UN À UN au tirage t. La projection est faite avec la covariance
EMPIRIQUE de l'archive à laquelle on l'applique — réelle, simulée ou
contaminée — donc aucune constante tabulée n'entre dans la statistique.

Pourquoi la matrice Σ_xx est singulière, et pourquoi ça ne gêne pas
-------------------------------------------------------------------
Σ_n x_n(t) = 20 identiquement : les 80 indicatrices sont liées, Σ_xx est de
rang 79 et son vecteur nul est 1. On projette donc par pseudo-inverse, ce
qui revient à retirer la part linéaire dans le seul sous-espace où elle est
définie. Et Σ_{j≠i} x_i x_j = 19·x_i identiquement : après projection, les
lignes de la matrice résiduelle somment exactement à zéro. Ces deux
dégénérescences abaissent la moyenne du null sous 252 800 — raison de plus
pour la simuler, jamais la tabuler.

Le null
=======
Simulé, sur des archives SRS complètes de 70 560 tirages (règle n° 1). Les
252 800 cellules ne sont ni indépendantes ni identiquement distribuées (deux
paires partageant un numéro sont corrélées, et les 6 320 cellules n ∈ {i,j}
n'ont pas les mêmes moments que les autres) : une loi du χ² tabulée à
252 800 degrés mentirait, et la loi du max encore davantage.

La permutation de `lab.calibrate_perm` serait un null valide ici — Q1/Q2/Q3
dépendent de l'ORDRE — mais elle coûte le même prix et f1 a établi que les
deux nulls coïncident à [0,94 ; 1,03] près sur les cinq statistiques
temporelles du dossier. Le SRS est gardé, et le point est déclaré, pas caché.

Limites déclarées
=================
 1. Lag 1 seulement. d2 a montré que balayer 306 lags coûte ~5 % sur la
    borne ; ici le coût serait le même, mais 306 × 1,6 s de null par lag
    dépasse le budget. Déclaré, pas dissimulé.
 2. Comme c0/c1/d3 : le seuil du registre (z ≈ 4,33) extrapole la queue du
    null. Pour Q1 et Q3 (sommes de carrés, quasi gaussiennes) l'extrapolation
    est gaussienne ; pour Q2 (un MAXIMUM, donc à queue de Gumbel) une
    extrapolation gaussienne SUR-ESTIMERAIT la puissance — le seuil de Q2 est
    donc extrapolé par un Gumbel ajusté aux moments du null, ce qui le place
    à ≈ 8,2 écarts-types au lieu de 4,33.
 3. Le plafond mesuré est un plafond d'OMNISCIENCE, comme c0 et c1 : il
    suppose la règle connue du joueur. La pénalité d'identification du §3 bis
    s'y ajouterait, et elle serait plus lourde qu'ailleurs (il faut estimer
    252 800 coefficients, pas dix numéros). Non mesurée.
 4. Le troisième ordre (triplets appelant un numéro) reste non borné à son
    tour. C'est la limite que ce fichier lègue — avec une raison de penser
    qu'elle est moins urgente : la dilution en √(nombre de cellules) fait
    perdre un facteur 2,8 de plus à chaque degré.

Usage : python3 h24_couplage_quadratique.py [--dry]
        (--dry : réplicats réduits, N'ÉCRIT PAS au registre)
"""

import os
import sys
import math
import time

# Le noyau est fait de 160 petits produits de Gram (80x80 en sortie). Mesuré :
# 0,45 s en mono-thread contre 1,0 à 9,0 s en multi-thread — la synchronisation
# des threads coûte plus que le calcul à cette forme de matrice, et le pire cas
# est erratique. Un thread, donc, et le run est aussi plus poli pour la machine.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import lab

POOL, DRAWN, K = lab.POOL, lab.DRAWN, 10
N = 70_560
DRY = "--dry" in sys.argv

REPS_NULL = 30 if DRY else 400
REPS_POWER = 2 if DRY else 6
REPS_SWEEP = 2 if DRY else 3
REPS_EDGE = 3 if DRY else 12
ALPHA_REG = 0.05

T0 = time.time()

# indexation des 3 160 paires i<j
IU = np.triu_indices(POOL, 1)
NPAIR = len(IU[0])
PAIR_ID = np.full((POOL, POOL), -1, np.int64)
PAIR_ID[IU[0], IU[1]] = np.arange(NPAIR)
PAIR_ID[IU[1], IU[0]] = np.arange(NPAIR)
_n = np.arange(POOL)[:, None]
INPAIR = (_n == IU[0][None, :]) | (_n == IU[1][None, :])       # (80, 3160)

# coefficients EXACTS de la règle pure-paire (dérivés plus bas en rationnels)
GAMMA = 19.0 / 60.0
DELTA = 19.0 / 177.0


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def zcrit(p_two_sided):
    """Quantile normal bilatéral, sans scipy : bissection sur erfc."""
    lo, hi = 0.0, 40.0
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if math.erfc(mid / math.sqrt(2.0)) > p_two_sided:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------
# La statistique
# --------------------------------------------------------------------------

def _tri_tensor(sel, x):
    """G[k,i,j] = Σ_t sel_k(t)·x_i(t)·x_j(t), pour k = 0..79.

    Écrit comme 80 produits Gram sur les lignes sélectionnées : ~9·10⁹ MAC,
    servis par BLAS en ~0,4 s. Les sommes sont des ENTIERS < 2²⁴, donc
    exactes en float32 — vérifié contre une voie float64 dans les contrôles.
    """
    G = np.empty((POOL, POOL, POOL), np.float32)
    for k in range(POOL):
        sub = x[sel[:, k]]
        G[k] = sub.T @ sub
    return G


def pair_z(mask):
    """Z[n,(i,j)] : couplage quadratique lag-1, part linéaire retirée.

    Renvoie (80, 3160). Sous H0 chaque cellule est ≈ N(0,1) — mais les
    cellules sont corrélées, et c'est la simulation qui donne la loi de
    toute fonction d'elles.
    """
    xb, yb = mask[:-1], mask[1:]
    x = xb.astype(np.float32)
    T = x.shape[0]

    Gx = _tri_tensor(xb, x).astype(np.float64)          # Σ_t x_k x_i x_j
    Gy = _tri_tensor(yb, x).astype(np.float64)          # Σ_t y_k x_i x_j
    Sxx = (x.T @ x).astype(np.float64)                  # Σ_t x_i x_j
    Syx = (yb.astype(np.float32).T @ x).astype(np.float64)

    mx, my = xb.mean(0), yb.mean(0)
    mw = Sxx / T                                        # E[x_i x_j]

    Cxw = Gx / T - mx[:, None, None] * mw[None, :, :]   # Cov(x_k, w_ij)
    Cyw = Gy / T - my[:, None, None] * mw[None, :, :]   # Cov(y_n, w_ij)
    Cxx = Sxx / T - np.outer(mx, mx)
    Cyx = Syx / T - np.outer(my, mx)

    P = np.linalg.pinv(Cxx, rcond=1e-8)                 # rang 79 : Σ_n x_n ≡ 20
    B = np.tensordot(P, Cxw, axes=(1, 0))               # coefficients de projection
    C = Cyw - np.tensordot(Cyx, B, axes=(1, 0))         # covariance résiduelle
    varR = mw * (1.0 - mw) - (Cxw * B).sum(0)           # Var(w) − part linéaire
    vary = my * (1.0 - my)

    c = C[:, IU[0], IU[1]]
    vr = varR[IU[0], IU[1]]
    return c * math.sqrt(T) / np.sqrt(vary[:, None] * vr[None, :])


def q_stats(mask):
    Z = pair_z(mask)
    zz = Z * Z
    return (float(zz.sum()), float(np.abs(Z).max()), float(zz[INPAIR].sum()))


# --------------------------------------------------------------------------
# Les statistiques déjà au registre, pour la démonstration de spécificité
# --------------------------------------------------------------------------

def t1_overlap(mask):
    """c1 / T1 : recouvrement moyen des paires consécutives."""
    return float((mask[1:] & mask[:-1]).sum() / (len(mask) - 1))


def t2_lagcov(mask):
    """c1 / T2 : ‖Ĉ‖²_F, les 6 400 covariances croisées LINÉAIRES lag-1."""
    x = mask.astype(np.float32)
    x -= x.mean(0)
    c = x[1:].T @ x[:-1] / np.float32(len(x) - 1)
    return float((c * c).sum(dtype=np.float64))


_PMF = lab.overlap_pmf()
_EXP = _PMF * (N - 1)
_LAST = int(np.max(np.flatnonzero(_EXP >= 5)))
_BINID = np.minimum(np.arange(DRAWN + 1), _LAST)
_EXPB = np.bincount(_BINID, weights=_EXP)


def s1_hist(mask):
    """d3 / S1 : χ² de l'histogramme complet du recouvrement lag-1."""
    ov = (mask[1:] & mask[:-1]).sum(1)
    obs = np.bincount(_BINID[ov], minlength=_LAST + 1).astype(float)
    return float(((obs - _EXPB) ** 2 / _EXPB).sum())


# --------------------------------------------------------------------------
# L'alternative : une règle purement quadratique, orthogonale par construction
# --------------------------------------------------------------------------

def v_values():
    """v(les deux) = +1, v(un seul) = −γ, v(aucun) = +δ.

    γ et δ sont les DEUX solutions exactes du système
        E[v] = 0        et        Cov(v, x_i) = 0
    sous SRS 20/80, en arithmétique rationnelle :
        P₂ = 19/316, P₁ = 120/316, P₀ = 177/316
        Cov(v, x_i) = 19/316 − (60/316)·γ = 0  →  γ = 19/60
        E[v] = 19/316 − (120/316)(19/60) + (177/316)·δ = 0  →  δ = 19/177
    Et il se trouve — ce n'est pas imposé, c'est un cadeau de la symétrie —
    que Cov(v, x_k) = 0 aussi pour k ∉ {i, j} :
        [6840 − (19/60)·45600 + (19/177)·70800] / 492960 = 0 / 492960
    La règle est donc EXACTEMENT orthogonale aux 80 indicatrices, donc
    strictement hors de la famille bornée par c1, et pas seulement « peu
    visible ». Vérifié numériquement dans les contrôles.
    """
    return 1.0, -GAMMA, DELTA


def make_rules(m_mod, R, rng, family="tiers"):
    """m_mod numéros modulés, chacun par R paires sources.

    family = "tiers"    : la paire source ne contient PAS le numéro appelé.
                          Les cellules touchées sont hors du bloc n ∈ {i,j} :
                          c'est le témoin de Q1 et Q2, et Q3 doit y rester
                          aveugle — un témoin qui allume tout ne prouve rien.
    family = "membre"   : la paire source est (n, j), donc le numéro appelé
                          est l'un de ses deux membres — « rémanence
                          quadratique », le cas physiquement naturel (une
                          paire qui rallume l'un des siens). Cellules dans le
                          bloc n ∈ {i,j} : c'est le témoin de Q3.
    Dans les deux cas la fonction v reste EXACTEMENT orthogonale aux 80
    indicatrices : l'orthogonalité ne dépend que de v, pas de qui est appelé.
    """
    mod = rng.permutation(POOL)[:m_mod]
    SI = np.empty((m_mod, R), np.int64)
    SJ = np.empty((m_mod, R), np.int64)
    for a, n in enumerate(mod):
        pool = np.delete(np.arange(POOL), n)
        if family == "membre":
            js = rng.choice(pool, size=R, replace=False)
            for r in range(R):
                SI[a, r], SJ[a, r] = min(int(n), int(js[r])), max(int(n), int(js[r]))
        else:
            for r in range(R):
                pr = rng.choice(pool, size=2, replace=False)
                SI[a, r], SJ[a, r] = int(pr.min()), int(pr.max())
    return mod, SI, SJ


def gen_quad(n, mod, SI, SJ, theta, rng):
    """Archive où le logit de n est décalé de θ·Σ_r v(paire source r au tirage t−1).

    Gumbel top-20 par pas — échantillonnage sans remise exact, donc
    SÉQUENTIEL (~1,7 s par archive de 70 560). θ = 0 redonne du SRS pur :
    c'est le témoin négatif du montage lui-même.
    """
    R = SI.shape[1]
    g = rng.gumbel(size=(n, POOL))
    out = np.zeros((n, POOL), bool)
    out[0, np.argpartition(-g[0], DRAWN)[:DRAWN]] = True
    prev = out[0]
    for t in range(1, n):
        pi, pj = prev[SI], prev[SJ]
        both = (pi & pj).sum(1)
        one = (pi ^ pj).sum(1)
        keys = g[t].copy()
        keys[mod] += theta * (both - GAMMA * one + DELTA * (R - both - one))
        out[t, np.argpartition(-keys, DRAWN)[:DRAWN]] = True
        prev = out[t]
    return out


def informed_play(cm, mod, SI, SJ, rng):
    """Le joueur qui CONNAÎT la règle : il coche les K numéros au plus fort tilt.

    Renvoie (E[hits], nombre moyen de numéros « chauds » — au moins une
    paire source complète au tirage précédent).
    """
    R = SI.shape[1]
    prev = cm[:-1]
    pi, pj = prev[:, SI], prev[:, SJ]
    both = (pi & pj).sum(2)
    one = (pi ^ pj).sum(2)
    score = np.zeros((len(prev), POOL), np.float32)
    score[:, mod] = both - GAMMA * one + DELTA * (R - both - one)
    score += rng.random(score.shape, dtype=np.float32) * np.float32(1e-3)
    idx = np.argpartition(-score, K, axis=1)[:, :K]
    hits = np.take_along_axis(cm[1:], idx, axis=1).sum(1)
    return float(hits.mean()), float((both > 0).sum(1).mean())


# --------------------------------------------------------------------------
# 0. Le seuil du registre
# --------------------------------------------------------------------------

rule("h24 — LE COUPLAGE QUADRATIQUE CONDITIONNEL")
if DRY:
    say("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

_rows = lab.ledger()
M_TESTS = len([r for r in _rows if r.get("p") is not None]) \
    + sum(int(r.get("m_extra", 0)) for r in _rows) + 3
P_REG = ALPHA_REG / M_TESTS
Z_REG = zcrit(P_REG)
say(f"\nregistre : {len(_rows)} entrées, m = {M_TESTS} tests dépensés (les 3 d'ici compris)")
say(f"seuil de Holm : p < {P_REG:.3e}   soit |z| > {Z_REG:.3f} en extrapolation gaussienne")


# --------------------------------------------------------------------------
# 1. Contrôles de construction — AVANT tout regard sur l'archive
# --------------------------------------------------------------------------

rule("1. CONTRÔLES DE CONSTRUCTION")

say("\n1a. la règle pure-paire est-elle orthogonale aux 80 indicatrices ?")
_rng = np.random.default_rng(20260830)
_m = lab.srs(400_000 if not DRY else 60_000, _rng)
_i, _j = 3, 41
_both = _m[:, _i] & _m[:, _j]
_one = _m[:, _i] ^ _m[:, _j]
_none = ~(_m[:, _i] | _m[:, _j])
_v = _both * 1.0 - GAMMA * _one + DELTA * _none
_cov = (_m.astype(float) * _v[:, None]).mean(0) - _v.mean() * _m.mean(0)
_se = _v.std() * _m.astype(float).std(0).mean() / math.sqrt(len(_v))
say(f"    E[v] = {_v.mean():+.6f}   (bruit à cette taille : ±{_v.std()/math.sqrt(len(_v)):.6f})")
say(f"    max_k |Cov(v, x_k)| = {np.abs(_cov).max():.6f}   soit "
    f"{np.abs(_cov).max()/_se:.2f} erreur-type — loi du max de 80 : ≈ 2,5 à 3")
say(f"    Var(v) = {_v.var():.6f}   contre l'exact 19/316 + (120/316)(19/60)² "
    f"+ (177/316)(19/177)² = {19/316 + (120/316)*(19/60)**2 + (177/316)*(19/177)**2:.6f}")

say("\n1b. le tenseur reproduit-il la définition, cellule par cellule ?")
_ms = lab.srs(4_000, _rng)
_Z = pair_z(_ms)
_x = _ms[:-1].astype(np.float64)
_y = _ms[1:].astype(np.float64)
_T = len(_x)
_xc = _x - _x.mean(0)
_P = np.linalg.pinv(_xc.T @ _xc / _T, rcond=1e-8)
_worst = 0.0
for (n0, i0, j0) in ((5, 11, 40), (11, 11, 40), (0, 1, 2), (79, 12, 79)):
    _w = _x[:, i0] * _x[:, j0]
    _wc = _w - _w.mean()
    _b = _P @ (_xc.T @ _wc / _T)
    _r = _wc - _xc @ _b
    _yc = _y[:, n0] - _y[:, n0].mean()
    _z = (_yc * _r).mean() * math.sqrt(_T) / math.sqrt(_yc.var() * _r.var())
    _got = _Z[n0, PAIR_ID[i0, j0]]
    _worst = max(_worst, abs(_z - _got))
    say(f"    n={n0:2d} paire ({i0:2d},{j0:2d})  voie directe {_z:+.8f}   "
        f"tenseur {_got:+.8f}   écart {abs(_z-_got):.2e}")
say(f"    écart maximal : {_worst:.2e}")
assert _worst < 1e-6, "le tenseur ne reproduit pas la définition"

say("\n1c. le montage de contamination rend-il du SRS pur à θ = 0 ?")
_mod, _SI, _SJ = make_rules(80, 2, _rng)
_c0 = gen_quad(20_000, _mod, _SI, _SJ, 0.0, _rng)
say(f"    θ = 0 : recouvrement lag-1 = {t1_overlap(_c0):.5f}  (H₀ : 5)   "
    f"fréquences min/max = {_c0.mean(0).min():.4f}/{_c0.mean(0).max():.4f}  (H₀ : 0,25)")


# --------------------------------------------------------------------------
# 2. Les nulls — simulés, jamais tabulés
# --------------------------------------------------------------------------

rule("2. NULLS SIMULÉS")
say(f"\n{REPS_NULL} archives SRS complètes de {N} tirages, partagées par les six")
say("statistiques : Q1, Q2, Q3 (neuves) et T1, T2, S1 (déjà au registre —")
say("elles servent à la démonstration de spécificité, pas à un nouveau test).")

rngN = np.random.default_rng(240830)
vals = {k: np.empty(REPS_NULL) for k in ("Q1", "Q2", "Q3", "T1", "T2", "S1")}
t0 = time.time()
for r in range(REPS_NULL):
    m = lab.srs(N, rngN)
    q1, q2, q3 = q_stats(m)
    vals["Q1"][r], vals["Q2"][r], vals["Q3"][r] = q1, q2, q3
    vals["T1"][r], vals["T2"][r], vals["S1"][r] = t1_overlap(m), t2_lagcov(m), s1_hist(m)
    if (r + 1) % max(1, REPS_NULL // 10) == 0:
        el = time.time() - t0
        say(f"    {r+1}/{REPS_NULL}  ({el:.0f}s, reste ≈ {el/(r+1)*(REPS_NULL-r-1):.0f}s)")

NULL = {k: lab.Null(float(v.mean()), float(v.std(ddof=1)), REPS_NULL, v)
        for k, v in vals.items()}

say(f"\n  {'statistique':<34}{'moyenne':>16}{'écart-type':>14}")
for k, lbl in (("Q1", "Q1  Σ Z² (252 800 cellules)"),
               ("Q2", "Q2  max |Z|"),
               ("Q3", "Q3  Σ Z² (6 320, n ∈ {i,j})"),
               ("T1", "T1  recouvrement lag-1 (c1)"),
               ("T2", "T2  ‖Ĉ‖²_F linéaire (c1)"),
               ("S1", "S1  forme de la loi de O (d3)")):
    say(f"  {lbl:<34}{NULL[k].mean:>16.5f}{NULL[k].sd:>14.5f}")

say(f"\n  Q1 : moyenne simulée {NULL['Q1'].mean:.0f} pour 252 800 cellules, "
    f"écart-type {NULL['Q1'].sd:.0f}")
say(f"       si les cellules étaient indépendantes : 252 800 ± "
    f"{math.sqrt(2*252800):.0f} — ratio des sd {NULL['Q1'].sd/math.sqrt(2*252800):.3f}")
say(f"  Q3 : {NULL['Q3'].mean:.0f} ± {NULL['Q3'].sd:.0f} pour 6 320 cellules ; "
    f"indépendance : 6 320 ± {math.sqrt(2*6320):.0f} — ratio {NULL['Q3'].sd/math.sqrt(2*6320):.3f}")
say("       une loi tabulée aurait donc menti sur les deux, et pas du même facteur —")
say("       ni même dans le même SENS : la somme des carrés est sous-dispersée sur")
say("       l'ensemble et SUR-dispersée sur le sous-bloc.")

say("\n  contre-épreuve du montage de null : T1, T2 et S1 sont recalculés ici depuis")
say("  zéro, et leurs nulls doivent retomber sur ceux que c1 et d3 ont publiés.")
say(f"    T1  {NULL['T1'].mean:.5f} ± {NULL['T1'].sd:.5f}    c1 : 5,0006 ± 0,0065")
say(f"    T2  {NULL['T2'].mean:.6e} ± {NULL['T2'].sd:.2e}    c1 : observé 3,164e-03 à z = −0,30")
say(f"    S1  {NULL['S1'].mean:.3f} ± {NULL['S1'].sd:.3f}       d3 : 12,525 ± 5,23 (150 rép.)")
say("  Si l'un des trois s'écartait, ce serait le montage d'ici qu'il faudrait")
say("  suspecter avant les résultats — pas l'inverse.")

# seuils de détection au niveau du registre
beta_g = NULL["Q2"].sd * math.sqrt(6.0) / math.pi
mu_g = NULL["Q2"].mean - 0.5772156649 * beta_g
THR = {
    "Q1": NULL["Q1"].mean + Z_REG * NULL["Q1"].sd,
    "Q3": NULL["Q3"].mean + Z_REG * NULL["Q3"].sd,
    "Q2": mu_g - beta_g * math.log(-math.log(1.0 - P_REG)),
}
say(f"\n  seuils de détection au niveau du registre (p = {P_REG:.2e}) :")
say(f"    Q1 > {THR['Q1']:.0f}      (gaussienne, {Z_REG:.2f} sd)")
say(f"    Q3 > {THR['Q3']:.0f}        (gaussienne, {Z_REG:.2f} sd)")
say(f"    Q2 > {THR['Q2']:.3f}     (Gumbel ajusté aux moments : "
    f"{(THR['Q2']-NULL['Q2'].mean)/NULL['Q2'].sd:.2f} sd — une gaussienne aurait dit "
    f"{Z_REG:.2f} sd et sur-estimé la puissance)")


# --------------------------------------------------------------------------
# 3. Pré-enregistrement — AVANT de calculer quoi que ce soit sur l'archive
# --------------------------------------------------------------------------

rule("3. PRÉ-ENREGISTREMENT")

DEC = f"conforme si p empirique > seuil de Holm du registre entier ({P_REG:.2e}) ; " \
      "un |z| > 3 déclenche d'abord une chasse à l'artefact (moitiés, huitièmes, " \
      "placebo, spécificité), jamais une annonce"
NULLDOC = (f"simulation : {REPS_NULL} archives SRS complètes de {N} tirages, "
           "statistique identique ; la projection linéaire est ré-estimée sur "
           "CHAQUE archive, donc aucune constante tabulée n'entre dans la statistique")

TOK1 = lab.preregister(
    "h24.quad_diffus",
    "Après retrait de toute la dépendance LINÉAIRE au tirage précédent (la famille "
    "bornée par c1/d2), il ne reste aucun couplage entre les 3 160 paires du tirage t "
    "et les 80 numéros du tirage t+1",
    "Q1 = somme des carrés des 252 800 corrélations partielles standardisées "
    "Z[n,(i,j)] (structure quadratique diffuse)",
    NULLDOC, DEC, track="A")
TOK2 = lab.preregister(
    "h24.quad_max",
    "Aucune paire du tirage t n'appelle ni ne repousse un numéro du tirage t+1 de "
    "façon isolée et forte, une fois la part linéaire retirée",
    "Q2 = max |Z[n,(i,j)]| sur les 252 800 cellules ; la multiplicité est DANS la "
    "loi du maximum, pas corrigée après coup",
    NULLDOC, DEC, track="A")
TOK3 = lab.preregister(
    "h24.quad_remanence",
    "Une paire (i, j) sortie au tirage t ne rappelle pas l'un de ses propres membres "
    "au tirage t+1 au-delà de ce que la rémanence linéaire de c1 explique déjà",
    "Q3 = somme des carrés des Z[n,(i,j)] sur les 6 320 cellules où n ∈ {i, j}",
    NULLDOC, DEC, track="A")
for tk in (TOK1, TOK2, TOK3):
    say(f"  {tk['id']:<22} scellé {tk['seal']}  à {tk['registered_at']}")


# --------------------------------------------------------------------------
# 4. L'archive réelle
# --------------------------------------------------------------------------

rule("4. L'ARCHIVE RÉELLE")
a = lab.load()
if DRY:
    # En mise au point on ne REGARDE PAS l'archive : un dry run qui montre la
    # réponse avant le run officiel viderait le pré-enregistrement de son sens.
    # On lui substitue une archive SRS de même taille, annoncée comme telle.
    REAL = lab.srs(N, np.random.default_rng(999))
    say("\n  *** DRY : PLACEBO SRS à la place de l'archive — rien n'est regardé ***")
else:
    REAL = a.mask
say(f"\n  {len(a)} tirages, {len(a)-1} paires consécutives (coupures de session comprises,")
say("  comme c1 et d3 — les 345 reprises sont trop peu nombreuses pour peser)")

t0 = time.time()
Z_REAL = pair_z(REAL)
o1 = float((Z_REAL * Z_REAL).sum())
o2 = float(np.abs(Z_REAL).max())
o3 = float((Z_REAL * Z_REAL)[INPAIR].sum())
say(f"  statistique calculée en {time.time()-t0:.1f}s")

say(f"\n  {'':<26}{'observé':>14}{'null simulé':>26}{'z':>9}{'p':>10}")
RES = {}
for key, obs, lbl in (("Q1", o1, "Q1  Σ Z² (252 800)"),
                      ("Q2", o2, "Q2  max |Z|"),
                      ("Q3", o3, "Q3  Σ Z² (n ∈ {i,j})")):
    nl = NULL[key]
    z, p = nl.z(obs), nl.p_two_sided(obs)
    RES[key] = (obs, z, p)
    say(f"  {lbl:<26}{obs:>14.4f}{nl.mean:>15.4f} ± {nl.sd:<8.4f}{z:>+9.2f}{p:>10.4f}")

imax = int(np.argmax(np.abs(Z_REAL)))
n_max, p_max = divmod(imax, NPAIR)
say(f"\n  cellule la plus déviante : numéro {n_max+1} au tirage t+1, "
    f"paire ({IU[0][p_max]+1}, {IU[1][p_max]+1}) au tirage t   Z = {Z_REAL[n_max, p_max]:+.3f}")
say(f"  cellules |Z| > 4 : {int((np.abs(Z_REAL) > 4).sum())}   "
    f"(attendu sous H₀ pour 252 800 cellules ≈ "
    f"{252800*math.erfc(4/math.sqrt(2)):.1f})")
say(f"  cellules |Z| > 3 : {int((np.abs(Z_REAL) > 3).sum())}   attendu ≈ "
    f"{252800*math.erfc(3/math.sqrt(2)):.0f}")

say(f"\n  rappel, sur la même archive et le même null (déjà au registre, non recomptés) :")
for key, fn, lbl in (("T1", t1_overlap, "T1 recouvrement lag-1 (c1)"),
                     ("T2", t2_lagcov, "T2 ‖Ĉ‖²_F linéaire (c1)"),
                     ("S1", s1_hist, "S1 forme de la loi de O (d3)")):
    v = fn(REAL)
    say(f"    {lbl:<30}{v:>14.5f}   z = {NULL[key].z(v):+.2f}")


# --------------------------------------------------------------------------
# 4 bis. Chasse à l'artefact — déclenchée par la règle pré-enregistrée
# --------------------------------------------------------------------------

rule("4 bis. CHASSE À L'ARTEFACT")

Z_MAX_OBS = max(abs(RES[k][1]) for k in ("Q1", "Q2", "Q3"))
KEY_MAX = max(("Q1", "Q2", "Q3"), key=lambda k: abs(RES[k][1]))


def q_of(mask, key):
    Z = pair_z(mask)
    zz = Z * Z
    return {"Q1": float(zz.sum()), "Q2": float(np.abs(Z).max()),
            "Q3": float(zz[INPAIR].sum())}[key]


if Z_MAX_OBS <= 3.0:
    say(f"\n  Non déclenchée : le plus grand |z| des trois vaut {Z_MAX_OBS:.2f} "
        f"({KEY_MAX}), sous le seuil de 3")
    say("  déclaré au pré-enregistrement. Le traitement réservé à S1 (§20) et V3")
    say("  (§23) — moitiés, huitièmes, placebo par permutation — n'a pas lieu")
    say("  d'être, et le dire est la moitié du protocole : une chasse lancée")
    say("  après coup sur un z ordinaire fabrique des sous-groupes à volonté.")
else:
    say(f"\n  DÉCLENCHÉE : {KEY_MAX} sort à z = {RES[KEY_MAX][1]:+.2f}. Traitement")
    say("  de §20 (S1) et §23 (V3) : réplication sur les moitiés puis les")
    say("  huitièmes, et placebo par PERMUTATION de l'ordre des tirages réels.")

    REPS_CH = 20 if DRY else 80
    for nparts, lbl in ((2, "moitiés"), (8, "huitièmes")):
        L = len(REAL) // nparts
        nl = lab.calibrate(lambda m, k=KEY_MAX: q_of(m, k), L, reps=REPS_CH, seed=555 + nparts)
        say(f"\n  {lbl} (n = {L}) — null simulé à CETTE taille : "
            f"{nl.mean:.4f} ± {nl.sd:.4f}")
        zs = []
        for i in range(nparts):
            v = q_of(REAL[i * L:(i + 1) * L], KEY_MAX)
            zs.append(nl.z(v))
            say(f"    part {i+1}/{nparts} : {v:.4f}   z = {nl.z(v):+.2f}")
        say(f"    même signe que l'observé sur "
            f"{sum(1 for z in zs if z * RES[KEY_MAX][1] > 0)}/{nparts} parts")

    say(f"\n  placebo par permutation (null de f1 : détruit l'ORDRE, conserve")
    say(f"  EXACTEMENT la loi jointe des tirages), {REPS_CH} réplicats :")
    _arch = lab.Archive(a.ids, a.ts, a.nums, a.boost, a.bonus, REAL)
    nlp = lab.calibrate_perm(lambda arch, k=KEY_MAX: q_of(arch.mask, k), _arch,
                             reps=REPS_CH, seed=777)
    say(f"    null permuté {nlp.mean:.4f} ± {nlp.sd:.4f}   contre SRS "
        f"{NULL[KEY_MAX].mean:.4f} ± {NULL[KEY_MAX].sd:.4f}")
    say(f"    z sous permutation : {nlp.z(RES[KEY_MAX][0]):+.2f}   "
        f"(SRS : {RES[KEY_MAX][1]:+.2f})   ratio des sd "
        f"{nlp.sd / NULL[KEY_MAX].sd:.3f}")


# --------------------------------------------------------------------------
# 5. Puissance — contaminations d'amplitude connue par construction
# --------------------------------------------------------------------------

rngP = np.random.default_rng(770830)


def measure(m_mod, R, theta, reps, family="tiers", full=False):
    """`reps` archives contaminees : detection par statistique, avantage joue.

    `full` ajoute T1, T2, S1 — les statistiques DEJA au registre — pour la
    demonstration de specificite. Elles ne sont jamais re-consignees.
    """
    keys = ("Q1", "Q2", "Q3") + (("T1", "T2", "S1") if full else ())
    zs = {k: [] for k in keys}
    det = {k: 0 for k in ("Q1", "Q2", "Q3")}
    det_any = 0
    advs, hots = [], []
    for _ in range(reps):
        mod, SI, SJ = make_rules(m_mod, R, rngP, family)
        cm = gen_quad(N, mod, SI, SJ, theta, rngP)
        q1, q2, q3 = q_stats(cm)
        raw = {"Q1": q1, "Q2": q2, "Q3": q3}
        if full:
            raw.update(T1=t1_overlap(cm), T2=t2_lagcov(cm), S1=s1_hist(cm))
        for k in keys:
            zs[k].append(NULL[k].z(raw[k]))
        hit = False
        for k in ("Q1", "Q2", "Q3"):
            if raw[k] >= THR[k]:
                det[k] += 1
                hit = True
        det_any += int(hit)
        h, ho = informed_play(cm, mod, SI, SJ, rngP)
        advs.append(h - K / 4.0)
        hots.append(ho)
    return dict(m=m_mod, R=R, theta=theta, family=family, reps=reps,
                adv=float(np.mean(advs)), hot=float(np.mean(hots)),
                se=float(np.std(advs, ddof=1) / math.sqrt(reps)) if reps > 1 else float("nan"),
                z={k: float(np.mean(v)) for k, v in zs.items()},
                pw={k: det[k] / reps for k in det}, pw_any=det_any / reps)


rule("5. PUISSANCE MESUREE")
say("\nContamination : m numeros modules, chacun par R paires sources, tilt de logit")
say("theta*v ou v est la fonction pure-paire EXACTEMENT orthogonale aux 80")
say("indicatrices (section 1a). Detection = la statistique depasse son seuil de")
say("registre (section 2). L'avantage est celui d'un joueur qui CONNAIT la regle,")
say("sur une grille de 10 — mesure en jouant la strategie, jamais deduit.")

HDR = (f"  {'theta':>6}{'chauds':>8}{'avantage':>11}{'%':>8}"
       f"{'z(Q1)':>9}{'z(Q2)':>9}{'z(Q3)':>9}{'pwQ1':>7}{'pwQ2':>7}{'pwQ3':>7}{'pw v':>7}")


def show(row):
    say(f"  {row['theta']:>6.2f}{row['hot']:>8.2f}{row['adv']:>+11.4f}{row['adv']/2.5:>+8.2%}"
        f"{row['z']['Q1']:>+9.1f}{row['z']['Q2']:>+9.1f}{row['z']['Q3']:>+9.1f}"
        f"{row['pw']['Q1']:>7.0%}{row['pw']['Q2']:>7.0%}{row['pw']['Q3']:>7.0%}"
        f"{row['pw_any']:>7.0%}")


GRID_A = (0.06, 0.09) if DRY else (0.05, 0.06, 0.07, 0.08, 0.10)
GRID_B = (0.06, 0.09) if DRY else (0.04, 0.05, 0.06, 0.08)

say("\n5a. FAMILLE « TIERS » — la paire (i,j) appelle un numero n hors de la paire")
say(f"    m = 80 numeros modules, R = 2 paires sources chacun (160 cellules / 252 800)")
say("\n" + HDR)
TAB_A = []
for th in GRID_A:
    r = measure(80, 2, th, REPS_POWER, "tiers", full=True)
    TAB_A.append(r)
    show(r)
say("    Q3 doit rester a zero ici : aucune cellule n in {i,j} n'est touchee.")
say("    Un temoin qui allumerait les trois statistiques ne prouverait rien sur")
say("    ce que chacune voit — c'est la dichotomie que d1 avait mesuree sur les")
say("    triplets, refaite ici.")

say("\n5b. FAMILLE « MEMBRE » — remanence QUADRATIQUE : la paire (n,j) rallume n")
say(f"    m = 80, R = 2 (160 cellules dans le bloc n in {{i,j}} de 6 320)")
say("\n" + HDR)
TAB_B = []
for th in GRID_B:
    r = measure(80, 2, th, REPS_POWER, "membre", full=True)
    TAB_B.append(r)
    show(r)
say("    Q3 mord ici a plus basse amplitude que Q1 : 6 320 cellules au lieu de")
say("    252 800, donc un seuil 4 fois plus bas en somme de carres. C'est la")
say("    raison d'etre du sous-bloc, et elle est mesuree, pas argumentee.")

say("\n5c. DIFFUS CONTRE ISOLE — pourquoi Q1 et Q2 ne sont pas redondantes")
say("    a nombre de cellules touchees decroissant, amplitude compensee :")
say(f"\n  {'regles':<12}{'cellules':>9}{'theta':>7}{'avantage':>11}"
    f"{'z(Q1)':>9}{'z(Q2)':>9}{'pwQ1':>7}{'pwQ2':>7}")
TAB_C = []
for (mm, rr, th) in (((80, 2, 0.08), (8, 1, 0.20)) if DRY else
                     ((80, 2, 0.08), (20, 1, 0.14), (4, 1, 0.25), (1, 1, 0.40))):
    r = measure(mm, rr, th, max(3, REPS_POWER // 2), "tiers")
    r["label"] = f"m={mm} R={rr}"
    TAB_C.append(r)
    say(f"  {r['label']:<12}{mm*rr:>9}{r['theta']:>7.2f}{r['adv']:>+11.4f}"
        f"{r['z']['Q1']:>+9.1f}{r['z']['Q2']:>+9.1f}"
        f"{r['pw']['Q1']:>7.0%}{r['pw']['Q2']:>7.0%}")
say("    Une regle unique et forte est invisible de Q1 — un exces de 40 sur une")
say("    somme dont l'ecart-type vaut ~660 — et franche pour Q2. Reciproquement")
say("    160 regles faibles allument Q1 et laissent Q2 dans sa loi du maximum.")

say("\n5d. SPECIFICITE — ce que les tests DEJA au registre voient de la meme chose")
say(f"\n  {'famille':>10}{'theta':>7}{'z(T1) c1':>11}{'z(T2) c1':>11}{'z(S1) d3':>11}"
    f"{'  |':>3}{'z(Q1)':>9}{'z(Q3)':>9}{'pw v':>7}")
for lbl, tab in (("tiers", TAB_A), ("membre", TAB_B)):
    for row in tab:
        say(f"  {lbl:>10}{row['theta']:>7.2f}{row['z']['T1']:>+11.2f}"
            f"{row['z']['T2']:>+11.2f}{row['z']['S1']:>+11.2f}{'  |':>3}"
            f"{row['z']['Q1']:>+9.1f}{row['z']['Q3']:>+9.1f}{row['pw_any']:>7.0%}")
say("\n    T1, T2 et S1 restent dans le bruit la ou Q1 ou Q3 sortent franchement.")
say("    Ce n'est pas une chance : Cov(v, x_k) = 0 EXACTEMENT pour les 80 numeros")
say("    (section 1a), donc la contamination n'a aucune composante dans la famille")
say("    lineaire que c1 et d2 bornent. La famille testee ici leur est disjointe.")


# --------------------------------------------------------------------------
# 6. L'enveloppe de l'adversaire — le plafond d'exploitabilite
# --------------------------------------------------------------------------

rule("6. LE PLAFOND : LE MEILLEUR BIAIS QUADRATIQUE QUI AURAIT ECHAPPE")
say("\nMeme question que c0 et c1, sur la famille neuve : parmi les couplages")
say("quadratiques que 70 560 tirages n'auraient PAS vus, lequel donne le plus gros")
say("avantage a qui le connaitrait ? La structure (famille, m, R) est BALAYEE.")

CONFIGS = ((("tiers", 40, 2), ("tiers", 80, 2)) if DRY else
           (("tiers", 20, 1), ("tiers", 40, 1), ("tiers", 80, 1),
            ("tiers", 20, 2), ("tiers", 40, 2), ("tiers", 80, 2),
            ("tiers", 80, 4), ("membre", 40, 2), ("membre", 80, 2)))
GRID_BY_FAM = ({"tiers": (0.06, 0.09), "membre": (0.03, 0.06)} if DRY else
               {"tiers": (0.050, 0.065, 0.080, 0.095),
                "membre": (0.020, 0.030, 0.040, 0.055)})
GRID_SWEEP = GRID_BY_FAM["tiers"]        # pour la trace du pre-enregistrement

say(f"\n  {'famille':>8}{'m':>4}{'R':>3}{'theta':>7}{'chauds':>8}{'avantage':>11}{'%':>8}"
    f"{'pwQ1':>7}{'pwQ2':>7}{'pwQ3':>7}{'pw v':>7}")
BEST, SWEEP = None, []
for (fam, mm, rr) in CONFIGS:
    for th in GRID_BY_FAM[fam]:
        r = measure(mm, rr, th, REPS_SWEEP, fam)
        SWEEP.append(r)
        say(f"  {fam:>8}{mm:>4}{rr:>3}{th:>7.3f}{r['hot']:>8.2f}{r['adv']:>+11.4f}"
            f"{r['adv']/2.5:>+8.2%}{r['pw']['Q1']:>7.0%}{r['pw']['Q2']:>7.0%}"
            f"{r['pw']['Q3']:>7.0%}{r['pw_any']:>7.0%}")
        if r["pw_any"] < 0.5 and (BEST is None or r["adv"] > BEST["adv"]):
            BEST = r

if BEST is None:
    BEST = min(SWEEP, key=lambda s: s["pw_any"])
    say("\n  ATTENTION : aucune configuration sous 50 % de puissance dans la grille ;")
    say("  la borne ci-dessous est SUR-ESTIMEE (le plafond reel est plus bas).")

say(f"\n  Enveloppe retenue : famille {BEST['family']}, m = {BEST['m']}, R = {BEST['R']},")
say(f"  theta = {BEST['theta']:.3f} — puissance {BEST['pw_any']:.0%} sur {BEST['reps']} archives.")
say(f"\n  Re-mesure a l'enveloppe sur {REPS_EDGE} archives (le balayage a {REPS_SWEEP}")
say("  ne separe pas 33 % de 50 %) :")
EDGE = measure(BEST["m"], BEST["R"], BEST["theta"], REPS_EDGE, BEST["family"], full=True)
if EDGE["pw_any"] >= 0.5:
    lower = [t for t in GRID_BY_FAM[BEST["family"]] if t < BEST["theta"]]
    say(f"    la re-mesure donne {EDGE['pw_any']:.0%} : l'enveloppe du balayage etait")
    say(f"    trop haute (3 archives ne separent pas 33 % de 50 %). On redescend d'un")
    say(f"    cran, et c'est le report honnete du bruit d'estimation, pas un choix.")
    if lower:
        EDGE = measure(BEST["m"], BEST["R"], max(lower), REPS_EDGE,
                       BEST["family"], full=True)
    else:
        say("    ATTENTION : plus bas point de la grille deja detecte — le plafond")
        say("    ci-dessous est SUR-ESTIME.")
say(f"    theta retenu {EDGE['theta']:.3f}")
say(f"    avantage {EDGE['adv']:+.4f} +- {EDGE['se']:.4f} hits, soit {EDGE['adv']/2.5:+.2%}")
say(f"    puissance mesuree {EDGE['pw_any']:.0%}   "
    f"(Q1 {EDGE['pw']['Q1']:.0%}, Q2 {EDGE['pw']['Q2']:.0%}, Q3 {EDGE['pw']['Q3']:.0%})")
say(f"    z moyens : Q1 {EDGE['z']['Q1']:+.1f}  Q2 {EDGE['z']['Q2']:+.1f}  "
    f"Q3 {EDGE['z']['Q3']:+.1f}  |  T1 {EDGE['z']['T1']:+.2f}  T2 {EDGE['z']['T2']:+.2f}  "
    f"S1 {EDGE['z']['S1']:+.2f}")

CEIL = EDGE["adv"] / (K / 4.0)
say(f"\n  PLAFOND D'EXPLOITABILITE DE LA FAMILLE QUADRATIQUE :")
say(f"    {EDGE['adv']:+.4f} hits sur 2,50, soit {CEIL:+.2%} de rendement")
say(f"\n  a comparer : marginal (c0) +1,33 %  |  lineaire lag-1 (c1) +3,21 %")
say(f"              lags 1..306 (d2) +3,46 %  |  avantage de la maison -25 a -35 %")


# --------------------------------------------------------------------------
# 7. Registre
# --------------------------------------------------------------------------

rule("7. REGISTRE")

pw_ref = None
for row in TAB_A:
    if row["pw_any"] >= 0.5:
        pw_ref = row
        break
pw_txt = (f"famille tiers m=80 R=2 : theta={pw_ref['theta']:.2f} "
          f"(avantage {pw_ref['adv']/2.5:+.1%}) detecte a {pw_ref['pw_any']:.0%} ; "
          f"plafond de la famille {CEIL:+.2%}" if pw_ref else
          f"voir table de la section 5 ; plafond de la famille {CEIL:+.2%}")

if DRY:
    say("\n*** DRY RUN : rien n'est écrit au registre ***")
    for k in ("Q1", "Q2", "Q3"):
        say(f"  {k}: observé {RES[k][0]:.4f}  z = {RES[k][1]:+.2f}  p = {RES[k][2]:.4f}")
else:
    NOTE = (f"famille NEUVE : couplage quadratique (paire du tirage t -> numero du "
            f"tirage t+1), part lineaire retiree par projection empirique, donc "
            f"disjointe des familles bornees par c0/c1/d2. Plafond d'exploitabilite "
            f"mesure : {CEIL:+.2%} (enveloppe {BEST['family']} m={BEST['m']} "
            f"R={BEST['R']} theta={BEST['theta']:.3f}, puissance {EDGE['pw_any']:.0%} "
            f"sur {REPS_EDGE} archives). Sous contamination detectee, T1/T2 (c1) et "
            f"S1 (d3) restent dans le bruit.")
    for tok, key, extra in (
            (TOK1, "Q1", f"cellules |Z|>4 : {int((np.abs(Z_REAL) > 4).sum())} pour "
                         f"{252800*math.erfc(4/math.sqrt(2)):.1f} attendues"),
            (TOK2, "Q2", f"cellule extreme : numero {n_max+1} | paire "
                         f"({IU[0][p_max]+1},{IU[1][p_max]+1})"),
            (TOK3, "Q3", "sous-bloc n dans la paire, 6 320 cellules ; temoin propre "
                         "(famille membre), aveugle a la famille tiers comme attendu")):
        obs, z, p = RES[key]
        lab.record(tok, observed=obs, null=NULL[key], power_at=pw_txt,
                   verdict="conforme" if p > P_REG else "À RÉEXAMINER",
                   notes=NOTE + " | " + extra)
        say(f"  consigné {tok['id']:<22} observé {obs:.4f}  z = {z:+.2f}  p = {p:.4f}")

    tok4 = lab.preregister(
        "h24.plafond_quad",
        "Parmi les couplages QUADRATIQUES (paire -> numero, lag 1) que 70 560 tirages "
        "n'auraient pas detectes, quel est le plus gros avantage pour qui le connaitrait ?",
        "avantage E[hits]-2,5 d'une grille de 10 jouee par un joueur omniscient, a "
        "l'enveloppe (famille, m, R et amplitude theta balayees, puissance < 50 %)",
        f"balayage de {len(CONFIGS)} structures x {len(GRID_SWEEP)} amplitudes, "
        f"{REPS_SWEEP} archives contaminees par point, seuils de registre de la "
        f"section 2 ; re-mesure a l'enveloppe sur {REPS_EDGE} archives",
        "borne rapportee, pas de p — c'est une mesure d'ignorance residuelle, pas un test",
        track="A")
    lab.record(tok4, observed=EDGE["adv"],
               power_at=f"puissance {EDGE['pw_any']:.0%} a l'enveloppe "
                        f"({REPS_EDGE} archives)",
               verdict=f"plafond {CEIL:+.2%} de rendement",
               notes=(f"enveloppe famille={BEST['family']} m={BEST['m']} R={BEST['R']} "
                      f"theta={BEST['theta']:.3f} ; borne d'OMNISCIENCE, la penalite "
                      f"d'identification du §3 bis s'y ajouterait et serait plus lourde "
                      f"qu'ailleurs (252 800 coefficients a estimer) ; lag 1 seulement ; "
                      f"a comparer : c0 marginal +1,33 %, c1 lineaire lag-1 +3,21 %, "
                      f"d2 lags 1..306 +3,46 %"))
    say(f"  consigné {tok4['id']:<22} plafond {CEIL:+.2%}")

    h = lab.holm()
    nsig = sum(1 for r in h if r["significant"])
    say(f"\n  lab.holm() : m = {h[0]['m_total']}, seuil {h[0]['holm_threshold']:.3e}, "
        f"{nsig} significatif(s)")
    say(f"  plus petit p du registre : {h[0]['id']} à p = {h[0]['p']:.2e}")
    say(f"  rang des trois entrées de h24 :")
    for i, r in enumerate(h):
        if r["id"].startswith("h24."):
            say(f"    {r['id']:<22} p = {r['p']:.4f}   rang {i+1}/{len(h)}   "
                f"significatif : {r['significant']}")

say(f"\n{'=' * 78}\ntotal {time.time() - T0:.0f}s")
