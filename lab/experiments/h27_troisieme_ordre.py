"""h27 — le TROISIÈME ORDRE conditionnel : un triplet appelle un numéro.

Ce que le registre ferme déjà, et la limite exacte que h24 lègue
================================================================
Le développement conditionnel du tirage t+1 sur le tirage t s'écrit

    P(n ∈ D_{t+1} | D_t) = 1/4 + Σ_i M1[n,i]·x_i + Σ_{i<j} M2[n,(i,j)]·r_ij
                               + Σ_{i<j<k} M3[n,(i,j,k)]·s_ijk + …

`c1` borne l'ordre 1 (6 400 cellules, plafond +3,21 %), `d2` l'étend aux lags
1..306 (+3,46 %), `h24` vient de borner l'ordre 2 (252 800 cellules, +6,27 %)
et écrit en toutes lettres sa limite n° 4 :

    « Le troisième ordre (triplets appelant un numéro) reste non borné à son
      tour. C'est la limite que ce fichier lègue — avec une raison de penser
      qu'elle est moins urgente : la dilution en √(nombre de cellules) fait
      perdre un facteur 2,8 de plus à chaque degré. »

C'est l'objet d'ici : le terme s_ijk, l'indicatrice « i ET j ET k sortis
en t », débarrassée de sa part linéaire ET de sa part quadratique.
80 × C(80,3) = 6 572 800 cellules, 26 fois l'espace de h24. La question n'est
pas « un triplet appelle-t-il un numéro ? » — un tel biais laisse des traces
d'ordres 1 et 2 que c1 et h24 verraient — mais : reste-t-il une dépendance
aux TRIPLETS une fois retirée toute la dépendance aux numéros et aux paires ?

La double projection se réduit à une seule, et c'est un théorème
================================================================
Retirer la part linéaire PUIS la part quadratique semble demander une
régression sur 80 + 3 160 colonnes. Mais chaque tirage contient exactement
20 numéros, donc Σ_{b≠a} x_a·x_b = x_a·(20−1) = 19·x_a IDENTIQUEMENT — sur
l'archive réelle, simulée ou contaminée, ligne par ligne. Les 80 indicatrices
sont DANS l'espace engendré par les 3 160 produits de paires : projeter sur
les paires seules retire aussi, exactement, toute la part linéaire. Vérifié
numériquement dans les contrôles (résidu des 80 indicatrices après projection
sur les paires : ~10⁻¹³, section 1b). Une seule matrice 3 160 × 3 160 à
inverser par archive au lieu de 3 240 × 3 240 — et surtout aucune cascade de
projections dont les erreurs se composeraient.

La projection est refaite avec la covariance EMPIRIQUE de chaque archive à
laquelle on l'applique — réelle, simulée ou contaminée : aucune constante
tabulée n'entre dans la statistique. Son noyau de calcul : les moments joints
d'ordre 2 à 5 des indicatrices (M2 aux paires jusqu'à M5 aux quintuplets,
C(80,5) = 24 040 016 comptes) sont comptés par bincount sur les
C(20,5) = 15 504 quintuplets de chaque tirage, puis Cov(w_ab, u_ijk) est
assemblée par une table d'index d'union précalculée (3 160 × 82 160, 1,0 Go)
— jamais par le produit dense (T × 3 160)ᵀ(T × 82 160), qui coûterait
1,8·10¹³ MAC par archive et rendait le plan infaisable de front.

Les trois statistiques, une par régime de défaut
================================================
  U1  Σ Z² sur les 6 572 800 cellules     — structure DIFFUSE. La
                                            généralisation directe du Q1 de
                                            h24, un degré plus haut.
  U2  max |Z| sur les mêmes cellules      — une règle FORTE et isolée ; la
                                            multiplicité est DANS la loi du
                                            max (queue Gumbel ajustée aux
                                            moments du null, comme h24).
  U3  Σ Z² sur les 246 480 cellules n ∈ {i,j,k} — la « rémanence cubique » :
                                            un triplet qui rappelle l'un de
                                            ses propres membres. Sous-espace
                                            26,7 fois plus petit, donc
                                            ~√26,7 ≈ 5 fois plus sensible sur
                                            cette sous-famille (mesuré au
                                            null, section 2).

Z[n,(i,j,k)] est la corrélation, standardisée à √T, entre l'appartenance de
n au tirage t+1 et la part du triplet (i,j,k) NON EXPLIQUÉE par les numéros
ni par les paires du tirage t.

Le cadeau de l'arithmétique, au degré 3
=======================================
La contamination module le logit d'un numéro par v(m), où m = |D_t ∩ S| est
le nombre de membres du triplet source S sortis en t. En résolvant en
RATIONNELS le système E[v] = 0, E[v·m] = 0, E[v·m²] = 0 (v₃ = 1) sous le
poids hypergéométrique p_m = C(3,m)·C(77,20−m)/C(80,20) :

    v = (−57/1711, +57/590, −3/10, +1),  Var(v) = 83 391/2 703 380

v est le polynôme orthogonal de DEGRÉ 3 du poids p_m. Et l'orthogonalité aux
moments internes du triplet se propage à TOUT le reste par les identités de
somme (Σ_a x_a ≡ 20, Σ_b w_ab ≡ 19·x_a) : Cov(v, x_a) = 0 pour les 80
numéros et Cov(v, w_ab) = 0 pour les 3 160 paires, EXACTEMENT, les six cas
vérifiés en arithmétique de fractions dans la section 1a. La contamination
n'a donc AUCUNE composante dans les familles bornées par c1/d2 (linéaire) ni
par h24 (quadratique) — pas « peu visible » : strictement orthogonale. La
disjonction est démontrée avant d'être mesurée, puis mesurée (section 5d),
et dans les DEUX sens : la contamination quadratique de h24 vit dans l'espace
que la projection d'ici retire, donc U1/U2/U3 doivent y être aveugles
(section 5e).

Le null
=======
Simulé, sur des archives SRS complètes de 70 560 tirages (règle n° 1). Les
6 572 800 cellules ne sont ni indépendantes ni identiquement distribuées :
deux triplets partageant une paire sont corrélés, Σ_{k∉{i,j}} u_ijk = 18·w_ij
identiquement (les résidus somment à zéro par blocs), et les 246 480 cellules
n ∈ {i,j,k} n'ont pas les mêmes moments que les autres. h24 a mesuré que
retirer la part linéaire décorrèle largement ses cellules (ratios 1,011 et
1,054) ; de combien la double soustraction d'ici s'écarte de l'indépendance
ne peut pas être connu d'avance — la mesure est dans la section 2.

Le coût, et les réductions déclarées
====================================
Mesuré sur cette machine (4 cœurs, OpenBLAS ; le multi-thread gagne ici —
3,7 s contre 14 s sur le produit (3 160×3 160)(3 160×82 160) — contrairement
aux petits Gram de h24 où il perdait : la forme des matrices décide, pas la
doctrine) : UNE archive complète coûte 65 s de statistique en chrono isolé
(dont ~29 s de comptage M4/M5, ~25 s de projection par tranches, ~8 s de
moments croisés y), et ~100 s en régime soutenu sur plusieurs heures — le
chiffre de PLANIFICATION est le second, mesuré sur un pilote de 10 nulls,
pas le premier. 400 nulls comme h24 coûteraient ~11 h pour le null seul ;
le budget d'exécution réellement disponible pour ce run était d'environ
3 h, et le plan y tient par trois réductions DÉCLARÉES :

  1. REPS_NULL = 40 au lieu de 400 — l'écart-type du null est estimé à
     ±11 % au lieu de ±3,5 %, le plancher du p empirique passe de 1/401 à
     1/41 = 0,024. C'est la réduction la plus lourde du dossier, et elle
     est déclarée : les seuils de détection (donc la puissance, donc le
     plafond) portent cette incertitude d'échelle ; la re-mesure à
     l'enveloppe sur REPS_EDGE archives en absorbe une partie.
  2. Des grilles de puissance resserrées autour de la frontière de détection
     repérée par pilote (10 nulls + 4 archives contaminées, hors registre),
     figées AVANT le run officiel.
  3. La table d'index d'union (1,0 Go) est reconstruite à chaque run (~60 s)
     plutôt que mise en cache sur disque.

Ce run confronte aussi une PRÉDICTION posée avant lui : le §41 (h30) dérive
plafond = ‖a‖·(2m)^{1/4}·√(z/N) et en tire « le plafond de l'ordre 3 vaut
entre 8,9 % et 14,2 % ». La mesure d'ici passe par une voie indépendante
(contamination et détection réelles, pas la loi d'échelle) : si elle tombe
hors de la fourchette, c'est la loi qui est fausse.

Limites déclarées
=================
 1. Lag 1 seulement, comme h24 — 306 nulls complets par lag sont hors budget.
 2. Le seuil du registre extrapole la queue du null : gaussienne pour U1/U3,
    Gumbel ajusté aux moments pour U2 (un max sur 6,6 millions de cellules ;
    une extrapolation gaussienne sur-estimerait la puissance).
 3. Le plafond est une borne d'OMNISCIENCE : la règle est supposée connue
    du joueur. h26 a depuis MESURÉ la pénalité d'identification famille par
    famille : la part captée tombe à 11 % déjà pour l'ordre 2 (252 800
    cellules, plafond réalisable +0,71 %) ; à 6 572 800 cellules elle serait
    plus basse encore. Le chiffre d'ici est donc un plafond d'omniscience
    STRICT — le réalisable est une petite fraction de lui, non mesurée pour
    cette famille.
 4. REPS_NULL = 40 (point 1 ci-dessus) : les z de puissance portent ±11 %
    d'incertitude d'échelle ; la re-mesure à l'enveloppe (REPS_EDGE archives)
    en absorbe une partie sur le chiffre finalement rapporté.
 5. Le QUATRIÈME ordre et au-delà restent non bornés — mais la courbe des
    plafonds par degré (section 6) dit désormais par MESURE, et non plus par
    extrapolation, si la famille suivante peut encore porter un avantage
    au-dessus de ce que 70 560 tirages détecteraient.

Usage : python3 h27_troisieme_ordre.py [--dry]
        (--dry : réplicats réduits, placebo à la place de l'archive,
         N'ÉCRIT PAS au registre)
"""

import os
import sys
import math
import time
import itertools
from fractions import Fraction

# Contrairement à h24 (petits Gram 80×80, mono-thread gagnant), le noyau
# d'ici est dominé par un produit (3 160×3 160)(3 160×82 160) où 4 threads
# vont 3,7 fois plus vite (mesuré : 0,37 s contre 1,4 s par tranche de 8 192).
# On NE force donc PAS le mono-thread ; les sections à petits Gram sont
# indifférentes aux threads sur cette machine (mesuré : 0,38 s contre 0,39 s).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import lab

POOL, DRAWN, K = lab.POOL, lab.DRAWN, 10
N = 70_560
DRY = "--dry" in sys.argv

REPS_NULL = 6 if DRY else 40
REPS_POWER = 2 if DRY else 3
REPS_SWEEP = 1 if DRY else 2
REPS_EDGE = 2 if DRY else 8
ALPHA_REG = 0.05

T0 = time.time()


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def zcrit(p_two_sided):
    """Quantile normal bilatéral, sans scipy : bissection sur erfc (h24)."""
    lo, hi = 0.0, 40.0
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if math.erfc(mid / math.sqrt(2.0)) > p_two_sided:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------
# Indexation : paires, triplets, rangs combinatoires, tables d'union
# --------------------------------------------------------------------------

IU = np.triu_indices(POOL, 1)
NPAIR = len(IU[0])                                   # 3 160
_aa, _bb, _cc = np.meshgrid(*(np.arange(POOL),) * 3, indexing="ij")
VALID = np.flatnonzero((_aa < _bb) & (_bb < _cc))
TA, TB, TC = VALID // 6400, (VALID // 80) % 80, VALID % 80
NTRI = len(VALID)                                    # 82 160
del _aa, _bb, _cc
N4, N5 = math.comb(POOL, 4), math.comb(POOL, 5)      # 1 581 580 ; 24 040 016
NCELL = POOL * NTRI                                  # 6 572 800
OFF2, OFF3 = 0, NPAIR
OFF4, OFF5 = OFF3 + NTRI, OFF3 + NTRI + N4
MOMLEN = OFF5 + N5

# CT[j][v] = C(v, j+1) — rang colexicographique d'un k-uplet trié :
# rank(a<b<c<…) = C(a,1)+C(b,2)+C(c,3)+…  La sentinelle 127 (cases 80..127)
# absorbe les doublons marqués lors du calcul d'union, jamais sélectionnés.
CT = [np.array([math.comb(v, j + 1) for v in range(128)], np.int64)
      for j in range(5)]
EX2 = CT[0][IU[0]] + CT[1][IU[1]]
EX3 = CT[0][TA] + CT[1][TB] + CT[2][TC]

# cellules n ∈ {i,j,k} : le bloc « rémanence cubique » de U3
INBLOCK = (np.arange(POOL)[:, None] == TA[None, :]) | \
          (np.arange(POOL)[:, None] == TB[None, :]) | \
          (np.arange(POOL)[:, None] == TC[None, :])
NBLOCK = int(INBLOCK.sum())                          # 246 480


def build_union_idx(tupA, tupB, chunk=2048):
    """(nA, nB) int32 : index MOM du moment joint de l'union des deux uplets.

    Concatène, trie, marque les doublons à 127, retrie : les éléments
    distincts arrivent en tête, triés. Le rang colex est alors lu au bon
    degré (2 à 5 distincts) avec l'offset du bloc de moments correspondant.
    Table indépendante de l'archive : construite UNE fois, vérifiée contre
    le produit dense dans les contrôles (section 1b).
    """
    nA, kA = tupA.shape
    nB, kB = tupB.shape
    Kk = kA + kB
    out = np.empty((nA, nB), np.int32)
    A8, B8 = tupA.astype(np.int8), tupB.astype(np.int8)
    for s in range(0, nB, chunk):
        e = min(nB, s + chunk)
        arr = np.empty((nA, e - s, Kk), np.int8)
        arr[:, :, :kA] = A8[:, None, :]
        arr[:, :, kA:] = B8[None, s:e, :]
        arr.sort(axis=2)
        dup = arr[:, :, 1:] == arr[:, :, :-1]
        ndup = dup.sum(axis=2, dtype=np.int8)
        arr[:, :, 1:][dup] = 127
        arr.sort(axis=2)
        v = arr.astype(np.intp)
        r = CT[0][v[:, :, 0]] + CT[1][v[:, :, 1]]
        idx = np.where(ndup == Kk - 2, OFF2 + r, 0)
        r = r + CT[2][v[:, :, 2]]
        idx = np.where(ndup == Kk - 3, OFF3 + r, idx)
        if Kk >= 4:
            r = r + CT[3][v[:, :, 3]]
            idx = np.where(ndup == Kk - 4, OFF4 + r, idx)
        if Kk >= 5:
            r = r + CT[4][v[:, :, 4]]
            idx = np.where(ndup == Kk - 5, OFF5 + r, idx)
        out[:, s:e] = idx.astype(np.int32)
    return out


say("construction des tables d'union (une fois, ~60 s)…")
_t = time.time()
PAIRS = np.stack([IU[0], IU[1]], 1)
TRIPS = np.stack([TA, TB, TC], 1)
IDX_G = build_union_idx(PAIRS, PAIRS)                # (3 160, 3 160)
IDX_WU = build_union_idx(PAIRS, TRIPS)               # (3 160, 82 160), 1,0 Go
say(f"  fait en {time.time()-_t:.0f}s ({(IDX_G.nbytes+IDX_WU.nbytes)/1e9:.2f} Go)")

# comptage M4/M5 : rang(5-uplet) = R3(3 premiers) + S2(2 derniers), les
# C(20,5) combinaisons énumérées par paires (préfixe, suffixe) compatibles —
# 3 passes mémoire au lieu de 9 (une variante int32 « optimisée » a été
# mesurée PLUS LENTE : np.bincount recopie tout int32 en int64 ; l'int64
# direct évite la copie)
_T3c = np.array(list(itertools.combinations(range(DRAWN), 3)), np.int64)
_P2c = np.array(list(itertools.combinations(range(DRAWN), 2)), np.int64)
_pr5, _po5, _pr4, _po4 = [], [], [], []
for _i, _mx in enumerate(_T3c[:, 2]):
    _ok = np.flatnonzero(_P2c[:, 0] > _mx)
    _pr5.append(np.full(len(_ok), _i)); _po5.append(_ok)
for _i, _mx in enumerate(_P2c[:, 1]):
    _ok = np.flatnonzero(_P2c[:, 0] > _mx)
    _pr4.append(np.full(len(_ok), _i)); _po4.append(_ok)
PRE5, POST5 = np.concatenate(_pr5), np.concatenate(_po5)
PRE4, POST4 = np.concatenate(_pr4), np.concatenate(_po4)
assert len(PRE5) == math.comb(DRAWN, 5) and len(PRE4) == math.comb(DRAWN, 4)


def count45(mask, chunk=2048):
    """Comptes exacts des C(80,4) quadruplets et C(80,5) quintuplets."""
    n = len(mask)
    cols = np.nonzero(mask)[1].reshape(n, DRAWN).astype(np.intp)
    m4 = np.zeros(N4, np.int64)
    m5 = np.zeros(N5, np.int64)
    for s in range(0, n, chunk):
        sl = cols[s:s + chunk]
        W = [CT[j][sl] for j in range(5)]
        R3 = W[0][:, _T3c[:, 0]] + W[1][:, _T3c[:, 1]] + W[2][:, _T3c[:, 2]]
        S2 = W[3][:, _P2c[:, 0]] + W[4][:, _P2c[:, 1]]
        r5 = np.take(R3, PRE5, axis=1)
        r5 += np.take(S2, POST5, axis=1)
        m5 += np.bincount(r5.ravel(), minlength=N5)
        R2 = W[0][:, _P2c[:, 0]] + W[1][:, _P2c[:, 1]]
        S2b = W[2][:, _P2c[:, 0]] + W[3][:, _P2c[:, 1]]
        r4 = np.take(R2, PRE4, axis=1)
        r4 += np.take(S2b, POST4, axis=1)
        m4 += np.bincount(r4.ravel(), minlength=N4)
    assert m4.sum() == n * math.comb(DRAWN, 4)
    assert m5.sum() == n * math.comb(DRAWN, 5)
    return m4, m5


# --------------------------------------------------------------------------
# La statistique
# --------------------------------------------------------------------------

def _tri_tensor(sel, x):
    """G[k,i,j] = Σ_t sel_k(t)·x_i(t)·x_j(t) — le noyau de h24, repris tel
    quel. Sommes entières < 2²⁴, exactes en float32."""
    G = np.empty((POOL, POOL, POOL), np.float32)
    for k in range(POOL):
        sub = x[sel[:, k]]
        G[k] = sub.T @ sub
    return G


def cube_z(mask, chunk=8192, want_z=False):
    """U1, U2, U3 du couplage cubique lag-1, parts linéaire ET quadratique
    retirées par projection empirique sur les 3 160 produits de paires.

    Renvoie aussi les comptes de queue et la cellule extrême. Sous H0 chaque
    cellule est ≈ N(0,1) mais corrélée à ses voisines : la loi de U1/U2/U3
    ne sort que de la simulation.
    """
    xb, yb = mask[:-1], mask[1:]
    x = xb.astype(np.float32)
    T = len(xb)

    Sxx = (x.T @ x).astype(np.float64)               # M2
    T3 = _tri_tensor(xb, x).astype(np.float64)       # M3
    Gy = _tri_tensor(yb, x).astype(np.float64)       # Σ y_n x_a x_b
    m4, m5 = count45(xb)                             # M4, M5

    MOM = np.empty(MOMLEN)
    MOM[OFF2 + EX2] = Sxx[IU]
    MOM[OFF3 + EX3] = T3[TA, TB, TC]
    MOM[OFF4:OFF4 + N4] = m4
    MOM[OFF5:] = m5
    MOM /= T

    my = yb.mean(0)
    mw = Sxx[IU] / T                                 # E[w_ab]
    mu = MOM[OFF3 + EX3].copy()                      # E[u_ijk]

    # G = Cov(w, w), rang 3 159 : le vecteur nul est EXACTEMENT 1
    # (Σ w_ab ≡ C(20,2) = 190). On régularise dans cette seule direction ;
    # tous les seconds membres lui sont orthogonaux par la même identité,
    # donc G⁻¹_reg agit comme la pseudo-inverse (vérifié section 1b).
    G = MOM[IDX_G] - np.outer(mw, mw)
    kappa = float(np.trace(G)) / NPAIR
    G += kappa / NPAIR
    Gi = np.linalg.inv(G)

    Cyw = Gy[:, IU[0], IU[1]] / T - np.outer(my, mw)
    D = Cyw @ Gi                                     # (80, 3 160)

    # moments croisés y × triplet : troisième moment sous sélection y_n
    M3y = np.empty((POOL, NTRI))
    for nn in range(POOL):
        sel = yb[:, nn]
        G3 = _tri_tensor(xb[sel], x[sel])
        M3y[nn] = G3[TA, TB, TC]
    Cyu = M3y / T - np.outer(my, mu)

    vary = my * (1.0 - my)
    sqT = math.sqrt(T)
    U1 = U3 = 0.0
    nz4 = nz3 = 0
    zmax = -1.0
    cell = (-1, -1)
    Zfull = np.empty((POOL, NTRI), np.float32) if want_z else None
    for s in range(0, NTRI, chunk):
        e = min(NTRI, s + chunk)
        c = MOM[IDX_WU[:, s:e]] - mw[:, None] * mu[None, s:e]
        H = Gi @ c
        den = mu[s:e] * (1.0 - mu[s:e]) - (c * H).sum(0)
        num = Cyu[:, s:e] - D @ c
        Z = num * sqT / np.sqrt(vary[:, None] * den[None, :])
        zz = Z * Z
        U1 += float(zz.sum())
        U3 += float(zz[INBLOCK[:, s:e]].sum())
        nz4 += int((np.abs(Z) > 4).sum())
        nz3 += int((np.abs(Z) > 3).sum())
        am = int(np.argmax(np.abs(Z)))
        if abs(Z.ravel()[am]) > zmax:
            zmax = abs(Z.ravel()[am])
            cell = (am // (e - s), s + am % (e - s))
        if want_z:
            Zfull[:, s:e] = Z
    return dict(U1=U1, U2=zmax, U3=U3, nz4=nz4, nz3=nz3, cell=cell, Z=Zfull)


def u_stats(mask):
    st = cube_z(mask)
    return st["U1"], st["U2"], st["U3"]


# --------------------------------------------------------------------------
# Les statistiques déjà au registre, recodées pour la démonstration de
# spécificité — c1 (T1, T2), d3 (S1) et h24 (Q1, Q2, Q3). Même montage que
# h24 recodant celles de c1/d3 : si l'une d'elles ne retombe pas sur sa
# valeur publiée, c'est le montage d'ici qu'il faut suspecter d'abord.
# --------------------------------------------------------------------------

def t1_overlap(mask):
    return float((mask[1:] & mask[:-1]).sum() / (len(mask) - 1))


def t2_lagcov(mask):
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
    ov = (mask[1:] & mask[:-1]).sum(1)
    obs = np.bincount(_BINID[ov], minlength=_LAST + 1).astype(float)
    return float(((obs - _EXPB) ** 2 / _EXPB).sum())


GAMMA24, DELTA24 = 19.0 / 60.0, 19.0 / 177.0
INPAIR24 = (np.arange(POOL)[:, None] == IU[0][None, :]) | \
           (np.arange(POOL)[:, None] == IU[1][None, :])


def pair_z(mask):
    """h24, repris tel quel : couplage quadratique lag-1, part linéaire
    retirée."""
    xb, yb = mask[:-1], mask[1:]
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
    B = np.tensordot(P, Cxw, axes=(1, 0))
    C = Cyw - np.tensordot(Cyx, B, axes=(1, 0))
    varR = mw * (1.0 - mw) - (Cxw * B).sum(0)
    vary = my * (1.0 - my)
    c = C[:, IU[0], IU[1]]
    vr = varR[IU[0], IU[1]]
    return c * math.sqrt(T) / np.sqrt(vary[:, None] * vr[None, :])


def q_stats24(mask):
    Z = pair_z(mask)
    zz = Z * Z
    return (float(zz.sum()), float(np.abs(Z).max()), float(zz[INPAIR24].sum()))


# --------------------------------------------------------------------------
# L'alternative : une règle purement cubique, doublement orthogonale
# --------------------------------------------------------------------------

def v_exact():
    """Dérive v(m) en rationnels et DÉMONTRE l'orthogonalité complète.

    Système : Σ p_m v_m mʲ = 0 pour j = 0, 1, 2, avec v₃ = 1 — v est le
    polynôme orthogonal de degré 3 du poids hypergéométrique p_m. Puis les
    six covariances (x_a pour a ∈ S et a ∉ S ; w_ab pour |{a,b}∩S| = 2, 1,
    0) sont calculées par dénombrement exact et ASSERT à zéro : ce que h24 a
    trouvé « par cadeau de la symétrie » au degré 2 est ici démontré au
    degré 3 — l'orthogonalité aux moments INTERNES du triplet se propage à
    tout le reste par Σ_a x_a ≡ 20 et Σ_b w_ab ≡ 19·x_a.
    """
    C = math.comb
    M = C(80, 20)
    p = [Fraction(C(3, m) * C(77, 20 - m), M) for m in range(4)]
    assert sum(p) == 1
    # élimination de Gauss exacte sur le 3×3
    mat = [[p[m] * m ** j for m in range(3)] + [-p[3] * 3 ** j]
           for j in range(3)]
    for col in range(3):
        piv = next(r for r in range(col, 3) if mat[r][col] != 0)
        mat[col], mat[piv] = mat[piv], mat[col]
        pv = mat[col][col]
        mat[col] = [q / pv for q in mat[col]]
        for r in range(3):
            if r != col and mat[r][col] != 0:
                f = mat[r][col]
                mat[r] = [q - f * y for q, y in zip(mat[r], mat[col])]
    v = [mat[r][3] for r in range(3)] + [Fraction(1)]
    ev = sum(p[m] * v[m] for m in range(4))
    assert ev == 0
    quart, eww = Fraction(1, 4), Fraction(20 * 19, 80 * 79)
    cov = {
        "x, a∈S": sum(v[m] * Fraction(C(2, m - 1) * C(77, 20 - m), M)
                      for m in range(1, 4)) - ev * quart,
        "x, a∉S": sum(v[m] * Fraction(C(3, m) * C(76, 19 - m), M)
                      for m in range(4)) - ev * quart,
        "w, |∩|=2": sum(v[m] * Fraction(C(1, m - 2) * C(77, 20 - m), M)
                        for m in range(2, 4)) - ev * eww,
        "w, |∩|=1": sum(v[m] * Fraction(C(2, m - 1) * C(76, 19 - m), M)
                        for m in range(1, 4)) - ev * eww,
        "w, |∩|=0": sum(v[m] * Fraction(C(3, m) * C(75, 18 - m), M)
                        for m in range(4)) - ev * eww,
    }
    for k, val in cov.items():
        assert val == 0, f"Cov(v, {k}) = {val} ≠ 0"
    var = sum(p[m] * v[m] ** 2 for m in range(4))
    return v, var, cov


V_FRAC, V_VAR_FRAC, _ = v_exact()
VARR = np.array([float(q) for q in V_FRAC])          # (v0, v1, v2, v3)
V_VAR = float(V_VAR_FRAC)


def make_rules(m_mod, R, rng, family="tiers"):
    """m_mod numéros modulés, chacun par R triplets sources.

    family = "tiers"  : le triplet source ne contient PAS le numéro appelé —
                        cellules hors du bloc n ∈ {i,j,k} ; témoin de U1/U2,
                        U3 doit y rester aveugle.
    family = "membre" : le triplet source CONTIENT le numéro appelé —
                        « rémanence cubique », le cas physiquement naturel ;
                        cellules dans le bloc de U3.
    Dans les deux cas v reste EXACTEMENT orthogonal aux 80 indicatrices et
    aux 3 160 paires : l'orthogonalité ne dépend que de v, pas de qui est
    appelé.
    """
    mod = rng.permutation(POOL)[:m_mod]
    S = np.empty((m_mod, R, 3), np.int64)
    for a, n in enumerate(mod):
        pool = np.delete(np.arange(POOL), n)
        for r in range(R):
            if family == "membre":
                two = rng.choice(pool, size=2, replace=False)
                S[a, r] = sorted([int(n), int(two[0]), int(two[1])])
            else:
                three = rng.choice(pool, size=3, replace=False)
                S[a, r] = sorted(int(z) for z in three)
    return mod, S[:, :, 0], S[:, :, 1], S[:, :, 2]


def gen_cube(n, mod, S1, S2, S3, theta, rng):
    """Archive où le logit de n est décalé de θ·Σ_r v(|D_{t−1} ∩ S_r|).

    Gumbel top-20 par pas, séquentiel (~2 s par archive), comme gen_quad de
    h24. θ = 0 redonne du SRS pur : témoin négatif du montage (section 1c).
    """
    g = rng.gumbel(size=(n, POOL))
    out = np.zeros((n, POOL), bool)
    out[0, np.argpartition(-g[0], DRAWN)[:DRAWN]] = True
    prev = out[0]
    for t in range(1, n):
        cnt = prev[S1].astype(np.int8) + prev[S2] + prev[S3]
        keys = g[t].copy()
        keys[mod] += theta * VARR[cnt].sum(1)
        out[t, np.argpartition(-keys, DRAWN)[:DRAWN]] = True
        prev = out[t]
    return out


def informed_play(cm, mod, S1, S2, S3, rng):
    """Le joueur qui CONNAÎT la règle coche les K numéros au plus fort tilt.

    Renvoie (E[hits], nombre moyen de numéros « chauds » — au moins un
    triplet source COMPLET au tirage précédent).
    """
    prev = cm[:-1]
    cnt = prev[:, S1].astype(np.int8) + prev[:, S2] + prev[:, S3]
    score = np.zeros((len(prev), POOL), np.float32)
    score[:, mod] = VARR[cnt].sum(2)
    score += rng.random(score.shape, dtype=np.float32) * np.float32(1e-3)
    idx = np.argpartition(-score, K, axis=1)[:, :K]
    hits = np.take_along_axis(cm[1:], idx, axis=1).sum(1)
    return float(hits.mean()), float((cnt == 3).any(2).sum(1).mean())


# la contamination de h24, reprise telle quelle, pour la réciproque (5e)
def make_rules24(m_mod, R, rng):
    mod = rng.permutation(POOL)[:m_mod]
    SI = np.empty((m_mod, R), np.int64)
    SJ = np.empty((m_mod, R), np.int64)
    for a, n in enumerate(mod):
        pool = np.delete(np.arange(POOL), n)
        for r in range(R):
            pr = rng.choice(pool, size=2, replace=False)
            SI[a, r], SJ[a, r] = int(pr.min()), int(pr.max())
    return mod, SI, SJ


def gen_quad24(n, mod, SI, SJ, theta, rng):
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
        keys[mod] += theta * (both - GAMMA24 * one + DELTA24 * (R - both - one))
        out[t, np.argpartition(-keys, DRAWN)[:DRAWN]] = True
        prev = out[t]
    return out


# --------------------------------------------------------------------------
# 0. Le seuil du registre
# --------------------------------------------------------------------------

rule("h27 — LE TROISIÈME ORDRE CONDITIONNEL")
if DRY:
    say("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

_rows = lab.ledger()
M_TESTS = len([r for r in _rows if r.get("p") is not None]) \
    + sum(int(r.get("m_extra", 0)) for r in _rows) + 3
P_REG = ALPHA_REG / M_TESTS
Z_REG = zcrit(P_REG)
say(f"\nregistre : {len(_rows)} entrées, m = {M_TESTS} tests dépensés "
    f"(les 3 d'ici compris)")
say(f"seuil de Holm : p < {P_REG:.3e}   soit |z| > {Z_REG:.3f} en "
    f"extrapolation gaussienne")


# --------------------------------------------------------------------------
# 1. Contrôles de construction — AVANT tout regard sur l'archive
# --------------------------------------------------------------------------

rule("1. CONTRÔLES DE CONSTRUCTION")

say("\n1a. la règle pure-triplet est-elle orthogonale aux 80 indicatrices ET")
say("    aux 3 160 paires ?")
say(f"    v = ({V_FRAC[0]}, {V_FRAC[1]}, {V_FRAC[2]}, {V_FRAC[3]})   "
    f"Var(v) = {V_VAR_FRAC} = {V_VAR:.6f}")
say("    les SIX covariances (x_a, a ∈ S et a ∉ S ; w_ab aux trois cas")
say("    d'intersection) sont ASSERT à 0 en arithmétique de fractions — pas")
say("    d'à-peu-près numérique. Contre-vérification Monte-Carlo :")
_rng = np.random.default_rng(20260830)
_m = lab.srs(60_000 if DRY else 400_000, _rng)
_S = (3, 41, 63)
_cnt = _m[:, _S[0]].astype(np.int8) + _m[:, _S[1]] + _m[:, _S[2]]
_v = VARR[_cnt]
_cov_x = (_m.astype(float) * _v[:, None]).mean(0) - _v.mean() * _m.mean(0)
_w_sample = _m[:, IU[0][::13]] & _m[:, IU[1][::13]]     # 244 paires témoins
_cov_w = (_w_sample.astype(float) * _v[:, None]).mean(0) \
    - _v.mean() * _w_sample.mean(0)
_se = _v.std() / math.sqrt(len(_v))
say(f"    E[v] = {_v.mean():+.6f}  (bruit ±{_se:.6f})   "
    f"Var(v) = {_v.var():.6f}  (exact {V_VAR:.6f})")
say(f"    max_a |Cov(v, x_a)| = {np.abs(_cov_x).max():.6f}   "
    f"max sur 244 paires |Cov(v, w_ab)| = {np.abs(_cov_w).max():.6f}")

say("\n1b. le pipeline (moments + table d'union + inverse régularisée)")
say("    reproduit-il la définition, cellule par cellule ?")
_ms = lab.srs(4_001, _rng)
_res = cube_z(_ms, want_z=True)
_x64 = _ms[:-1].astype(np.float64)
_T = len(_x64)
_W = _x64[:, IU[0]] * _x64[:, IU[1]]
_Wc = _W - _W.mean(0)
_Cww_direct = _Wc.T @ _Wc / _T
_Gp = np.linalg.pinv(_Cww_direct, rcond=1e-10)
_y64 = _ms[1:].astype(np.float64)
_yc = _y64 - _y64.mean(0)
_worst = 0.0
_rr = np.random.default_rng(8)
_cells = [(5, 11, 40, 63), (11, 11, 40, 63), (0, 1, 2, 3), (79, 12, 33, 79)]
_cells += [(int(_rr.integers(80)),) + tuple(int(q) for q in
           np.sort(_rr.choice(80, 3, replace=False))) for _ in range(4)]
for (n0, i0, j0, k0) in _cells:
    _u = _x64[:, i0] * _x64[:, j0] * _x64[:, k0]
    _uc = _u - _u.mean()
    _r = _uc - _Wc @ (_Gp @ (_Wc.T @ _uc / _T))
    _ycn = _yc[:, n0]
    _zd = (_ycn * _r).mean() * math.sqrt(_T) / math.sqrt(_ycn.var() * _r.var())
    _ti = int(np.flatnonzero((TA == i0) & (TB == j0) & (TC == k0))[0])
    _zg = float(_res["Z"][n0, _ti])
    _worst = max(_worst, abs(_zd - _zg))
    say(f"    n={n0:2d} triplet ({i0:2d},{j0:2d},{k0:2d})  "
        f"directe {_zd:+.8f}   pipeline {_zg:+.8f}   écart {abs(_zd-_zg):.2e}")
say(f"    écart maximal : {_worst:.2e}  (borné par le stockage float32 de Z)")
assert _worst < 1e-6, "le pipeline ne reproduit pas la définition"
_xc = _x64 - _x64.mean(0)
_resid_x = _xc - _Wc @ (_Gp @ (_Wc.T @ _xc / _T))
say(f"    résidu max des 80 indicatrices après projection sur les paires :")
say(f"    {np.abs(_resid_x).max():.2e} — la part linéaire est DANS l'espace")
say("    des paires (Σ_b w_ab ≡ 19·x_a) : une projection les retire toutes")
say("    les deux, exactement. C'est le théorème qui divise le coût par 8.")
assert np.abs(_resid_x).max() < 1e-9

say("\n1c. le montage de contamination rend-il du SRS pur à θ = 0 ?")
_mod, _S1, _S2, _S3 = make_rules(80, 2, _rng)
_c0 = gen_cube(20_000, _mod, _S1, _S2, _S3, 0.0, _rng)
say(f"    θ = 0 : recouvrement lag-1 = {t1_overlap(_c0):.5f}  (H₀ : 5)   "
    f"fréquences min/max = {_c0.mean(0).min():.4f}/{_c0.mean(0).max():.4f}  "
    f"(H₀ : 0,25)")


# --------------------------------------------------------------------------
# 2. Les nulls — simulés, jamais tabulés
# --------------------------------------------------------------------------

rule("2. NULLS SIMULÉS")
say(f"\n{REPS_NULL} archives SRS complètes de {N} tirages, partagées par les")
say("neuf statistiques : U1, U2, U3 (neuves), Q1, Q2, Q3 (h24), T1, T2 (c1)")
say("et S1 (d3) — les six anciennes servent à la démonstration de")
say(f"spécificité, pas à un nouveau test. {REPS_NULL} réplicats au lieu des "
    f"400 de")
say("h24 : réduction de budget déclarée en tête de fichier, ±11 % sur les")
say("écarts-types au lieu de ±3,5 %.")

rngN = np.random.default_rng(270830)
KEYS = ("U1", "U2", "U3", "Q1", "Q2", "Q3", "T1", "T2", "S1")
vals = {k: np.empty(REPS_NULL) for k in KEYS}
t0 = time.time()
for r in range(REPS_NULL):
    m = lab.srs(N, rngN)
    u1, u2, u3 = u_stats(m)
    q1, q2, q3 = q_stats24(m)
    vals["U1"][r], vals["U2"][r], vals["U3"][r] = u1, u2, u3
    vals["Q1"][r], vals["Q2"][r], vals["Q3"][r] = q1, q2, q3
    vals["T1"][r], vals["T2"][r], vals["S1"][r] = \
        t1_overlap(m), t2_lagcov(m), s1_hist(m)
    if (r + 1) % max(1, REPS_NULL // 20) == 0:
        el = time.time() - t0
        say(f"    {r+1}/{REPS_NULL}  ({el:.0f}s, reste ≈ "
            f"{el/(r+1)*(REPS_NULL-r-1):.0f}s)")

NULL = {k: lab.Null(float(v.mean()), float(v.std(ddof=1)), REPS_NULL, v)
        for k, v in vals.items()}

say(f"\n  {'statistique':<38}{'moyenne':>16}{'écart-type':>14}")
for k, lbl in (("U1", "U1  Σ Z² (6 572 800 cellules)"),
               ("U2", "U2  max |Z|"),
               ("U3", "U3  Σ Z² (246 480, n ∈ {i,j,k})"),
               ("Q1", "Q1  Σ Z² quadratique (h24)"),
               ("Q2", "Q2  max |Z| quadratique (h24)"),
               ("Q3", "Q3  Σ Z² n ∈ {i,j} (h24)"),
               ("T1", "T1  recouvrement lag-1 (c1)"),
               ("T2", "T2  ‖Ĉ‖²_F linéaire (c1)"),
               ("S1", "S1  forme de la loi de O (d3)")):
    say(f"  {lbl:<38}{NULL[k].mean:>16.5f}{NULL[k].sd:>14.5f}")

_r1 = NULL["U1"].sd / math.sqrt(2 * NCELL)
_r3 = NULL["U3"].sd / math.sqrt(2 * NBLOCK)
say(f"\n  U1 : moyenne simulée {NULL['U1'].mean:.0f} pour {NCELL} cellules ;")
say(f"       indépendance : {NCELL} ± {math.sqrt(2*NCELL):.0f} — ratio des "
    f"sd {_r1:.3f}")
say(f"  U3 : {NULL['U3'].mean:.0f} ± {NULL['U3'].sd:.0f} pour {NBLOCK} "
    f"cellules ; indépendance : {NBLOCK} ± {math.sqrt(2*NBLOCK):.0f} — "
    f"ratio {_r3:.3f}")
say(f"  gain de sensibilité du sous-bloc U3 : {NULL['U1'].sd/NULL['U3'].sd:.1f} "
    f"(√26,7 ≈ 5,2 si les cellules étaient indépendantes)")

say("\n  contre-épreuve du montage : les six statistiques déjà publiées,")
say("  recodées ici depuis zéro, doivent retomber sur leurs nulls publiés.")
say(f"    Q1  {NULL['Q1'].mean:.1f} ± {NULL['Q1'].sd:.1f}     "
    f"h24 : 252 773,90 ± 719,03")
say(f"    Q2  {NULL['Q2'].mean:.4f} ± {NULL['Q2'].sd:.4f}     "
    f"h24 : 4,70093 ± 0,24286")
say(f"    Q3  {NULL['Q3'].mean:.1f} ± {NULL['Q3'].sd:.1f}       "
    f"h24 : 6 325,74 ± 118,50")
say(f"    T1  {NULL['T1'].mean:.5f} ± {NULL['T1'].sd:.5f}    c1 : 5,0006 ± 0,0065")
say(f"    T2  {NULL['T2'].mean:.6e} ± {NULL['T2'].sd:.2e}    "
    f"c1 : observé 3,164e-03 à z = −0,30")
say(f"    S1  {NULL['S1'].mean:.3f} ± {NULL['S1'].sd:.3f}       "
    f"d3 : 12,525 ± 5,23 (150 rép.)")
say("  Si l'une des six s'écartait, ce serait le montage d'ici qu'il")
say("  faudrait suspecter avant les résultats — pas l'inverse.")

beta_g = NULL["U2"].sd * math.sqrt(6.0) / math.pi
mu_g = NULL["U2"].mean - 0.5772156649 * beta_g
THR = {
    "U1": NULL["U1"].mean + Z_REG * NULL["U1"].sd,
    "U3": NULL["U3"].mean + Z_REG * NULL["U3"].sd,
    "U2": mu_g - beta_g * math.log(-math.log(1.0 - P_REG)),
}
say(f"\n  seuils de détection au niveau du registre (p = {P_REG:.2e}) :")
say(f"    U1 > {THR['U1']:.0f}      (gaussienne, {Z_REG:.2f} sd)")
say(f"    U3 > {THR['U3']:.0f}        (gaussienne, {Z_REG:.2f} sd)")
say(f"    U2 > {THR['U2']:.3f}     (Gumbel ajusté aux moments : "
    f"{(THR['U2']-NULL['U2'].mean)/NULL['U2'].sd:.2f} sd — une gaussienne "
    f"aurait dit {Z_REG:.2f} sd et sur-estimé la puissance)")


# --------------------------------------------------------------------------
# 3. Pré-enregistrement — AVANT de calculer quoi que ce soit sur l'archive
# --------------------------------------------------------------------------

rule("3. PRÉ-ENREGISTREMENT")

DEC = f"conforme si p empirique > seuil de Holm du registre entier " \
      f"({P_REG:.2e}) ; un |z| > 3 déclenche d'abord une chasse à " \
      "l'artefact (moitiés, huitièmes, placebo, spécificité), jamais une " \
      "annonce"
NULLDOC = (f"simulation : {REPS_NULL} archives SRS complètes de {N} tirages, "
           "statistique identique ; la projection sur les 3 160 produits de "
           "paires (qui contiennent exactement les 80 indicatrices) est "
           "ré-estimée sur CHAQUE archive, donc aucune constante tabulée "
           "n'entre dans la statistique")

TOK1 = lab.preregister(
    "h27.cube_diffus",
    "Après retrait de toute la dépendance LINÉAIRE et QUADRATIQUE au tirage "
    "précédent (les familles bornées par c1/d2/h24), il ne reste aucun "
    "couplage entre les 82 160 triplets du tirage t et les 80 numéros du "
    "tirage t+1",
    "U1 = somme des carrés des 6 572 800 corrélations partielles "
    "standardisées Z[n,(i,j,k)] (structure cubique diffuse)",
    NULLDOC, DEC, track="A")
TOK2 = lab.preregister(
    "h27.cube_max",
    "Aucun triplet du tirage t n'appelle ni ne repousse un numéro du tirage "
    "t+1 de façon isolée et forte, une fois les parts linéaire et "
    "quadratique retirées",
    "U2 = max |Z[n,(i,j,k)]| sur les 6 572 800 cellules ; la multiplicité "
    "est DANS la loi du maximum, pas corrigée après coup",
    NULLDOC, DEC, track="A")
TOK3 = lab.preregister(
    "h27.cube_remanence",
    "Un triplet sorti au tirage t ne rappelle pas l'un de ses propres "
    "membres au tirage t+1 au-delà de ce que la rémanence linéaire (c1) et "
    "quadratique (h24) expliquent déjà",
    "U3 = somme des carrés des Z[n,(i,j,k)] sur les 246 480 cellules où "
    "n ∈ {i,j,k}",
    NULLDOC, DEC, track="A")
for tk in (TOK1, TOK2, TOK3):
    say(f"  {tk['id']:<22} scellé {tk['seal']}  à {tk['registered_at']}")


# --------------------------------------------------------------------------
# 4. L'archive réelle
# --------------------------------------------------------------------------

rule("4. L'ARCHIVE RÉELLE")
a = lab.load()
if DRY:
    # En mise au point on ne REGARDE PAS l'archive : un dry run qui montre
    # la réponse avant le run officiel viderait le pré-enregistrement de son
    # sens. Placebo SRS de même taille, annoncé comme tel (montage h24).
    REAL = lab.srs(N, np.random.default_rng(999))
    say("\n  *** DRY : PLACEBO SRS à la place de l'archive — rien n'est "
        "regardé ***")
else:
    REAL = a.mask
say(f"\n  {len(a)} tirages, {len(a)-1} paires consécutives (coupures de "
    f"session comprises,")
say("  comme c1, d3 et h24 — les 345 reprises sont trop peu nombreuses pour "
    "peser)")

t0 = time.time()
ST_REAL = cube_z(REAL)
o1, o2, o3 = ST_REAL["U1"], ST_REAL["U2"], ST_REAL["U3"]
say(f"  statistique calculée en {time.time()-t0:.0f}s")

say(f"\n  {'':<28}{'observé':>16}{'null simulé':>26}{'z':>9}{'p':>10}")
RES = {}
for key, obs, lbl in (("U1", o1, "U1  Σ Z² (6 572 800)"),
                      ("U2", o2, "U2  max |Z|"),
                      ("U3", o3, "U3  Σ Z² (n ∈ {i,j,k})")):
    nl = NULL[key]
    z, p = nl.z(obs), nl.p_two_sided(obs)
    RES[key] = (obs, z, p)
    say(f"  {lbl:<28}{obs:>16.4f}{nl.mean:>15.4f} ± {nl.sd:<9.4f}"
        f"{z:>+9.2f}{p:>10.4f}")

n_max, t_max = ST_REAL["cell"]
say(f"\n  cellule la plus déviante : numéro {n_max+1} au tirage t+1, "
    f"triplet ({TA[t_max]+1}, {TB[t_max]+1}, {TC[t_max]+1}) au tirage t   "
    f"|Z| = {ST_REAL['U2']:.3f}")
say(f"  cellules |Z| > 4 : {ST_REAL['nz4']}   (attendu sous H₀ pour "
    f"{NCELL} cellules ≈ {NCELL*math.erfc(4/math.sqrt(2)):.0f})")
say(f"  cellules |Z| > 3 : {ST_REAL['nz3']}   attendu ≈ "
    f"{NCELL*math.erfc(3/math.sqrt(2)):.0f}")

say("\n  rappel, sur la même archive (déjà au registre, non recompté) :")
_q1r, _q2r, _q3r = q_stats24(REAL)
for key, vv, lbl, pub in (
        ("Q1", _q1r, "Q1 Σ Z² quadratique (h24)", "252 193,49  z = −0,81"),
        ("Q2", _q2r, "Q2 max |Z| quadratique (h24)", "4,6577  z = −0,18"),
        ("Q3", _q3r, "Q3 Σ Z² n ∈ {i,j} (h24)", "6 492,59  z = +1,41"),
        ("T1", t1_overlap(REAL), "T1 recouvrement lag-1 (c1)", "5,00191  z = +0,30"),
        ("T2", t2_lagcov(REAL), "T2 ‖Ĉ‖²_F linéaire (c1)", "3,164e-03  z = −0,30"),
        ("S1", s1_hist(REAL), "S1 forme de la loi de O (d3)", "30,292")):
    say(f"    {lbl:<32}{vv:>14.5f}   z = {NULL[key].z(vv):+.2f}   "
        f"(publié : {pub})")


# --------------------------------------------------------------------------
# 4 bis. Chasse à l'artefact — déclenchée par la règle pré-enregistrée
# --------------------------------------------------------------------------

rule("4 bis. CHASSE À L'ARTEFACT")

Z_MAX_OBS = max(abs(RES[k][1]) for k in ("U1", "U2", "U3"))
KEY_MAX = max(("U1", "U2", "U3"), key=lambda k: abs(RES[k][1]))


def u_of(mask, key):
    st = cube_z(mask)
    return st[key]


if Z_MAX_OBS <= 3.0:
    say(f"\n  Non déclenchée : le plus grand |z| des trois vaut "
        f"{Z_MAX_OBS:.2f} ({KEY_MAX}), sous le seuil de 3")
    say("  déclaré au pré-enregistrement. Le traitement de §20 (S1), §23 "
        "(V3) et h24")
    say("  — moitiés, huitièmes, placebo par permutation — n'a pas lieu "
        "d'être, et le")
    say("  dire est la moitié du protocole : une chasse lancée après coup "
        "sur un z")
    say("  ordinaire fabrique des sous-groupes à volonté.")
else:
    say(f"\n  DÉCLENCHÉE : {KEY_MAX} sort à z = {RES[KEY_MAX][1]:+.2f}. "
        f"Traitement de §20/§23/h24.")
    REPS_CH = 10 if DRY else 40
    for nparts, lbl in ((2, "moitiés"), (8, "huitièmes")):
        L = len(REAL) // nparts
        nl = lab.calibrate(lambda m, k=KEY_MAX: u_of(m, k), L,
                           reps=REPS_CH, seed=555 + nparts)
        say(f"\n  {lbl} (n = {L}) — null simulé à CETTE taille : "
            f"{nl.mean:.4f} ± {nl.sd:.4f}")
        zs = []
        for i in range(nparts):
            v = u_of(REAL[i * L:(i + 1) * L], KEY_MAX)
            zs.append(nl.z(v))
            say(f"    part {i+1}/{nparts} : {v:.4f}   z = {nl.z(v):+.2f}")
        say(f"    même signe que l'observé sur "
            f"{sum(1 for z in zs if z * RES[KEY_MAX][1] > 0)}/{nparts} parts")
    say(f"\n  placebo par permutation (null de f1), {REPS_CH} réplicats :")
    _arch = lab.Archive(a.ids, a.ts, a.nums, a.boost, a.bonus, REAL)
    nlp = lab.calibrate_perm(lambda arch, k=KEY_MAX: u_of(arch.mask, k),
                             _arch, reps=REPS_CH, seed=777)
    say(f"    null permuté {nlp.mean:.4f} ± {nlp.sd:.4f}   contre SRS "
        f"{NULL[KEY_MAX].mean:.4f} ± {NULL[KEY_MAX].sd:.4f}")
    say(f"    z sous permutation : {nlp.z(RES[KEY_MAX][0]):+.2f}   "
        f"(SRS : {RES[KEY_MAX][1]:+.2f})")


# --------------------------------------------------------------------------
# 5. Puissance — contaminations d'amplitude connue par construction
# --------------------------------------------------------------------------

rngP = np.random.default_rng(770830)


def measure(m_mod, R, theta, reps, family="tiers", full=False):
    """`reps` archives contaminées : détection par statistique, avantage
    joué. `full` ajoute Q1/Q2/Q3 (h24), T1/T2 (c1) et S1 (d3) — jamais
    re-consignées."""
    keys = ("U1", "U2", "U3") + \
        (("Q1", "Q2", "Q3", "T1", "T2", "S1") if full else ())
    zs = {k: [] for k in keys}
    det = {k: 0 for k in ("U1", "U2", "U3")}
    det_any = 0
    advs, hots = [], []
    for _ in range(reps):
        mod, S1, S2, S3 = make_rules(m_mod, R, rngP, family)
        cm = gen_cube(N, mod, S1, S2, S3, theta, rngP)
        u1, u2, u3 = u_stats(cm)
        raw = {"U1": u1, "U2": u2, "U3": u3}
        if full:
            q1, q2, q3 = q_stats24(cm)
            raw.update(Q1=q1, Q2=q2, Q3=q3, T1=t1_overlap(cm),
                       T2=t2_lagcov(cm), S1=s1_hist(cm))
        for k in keys:
            zs[k].append(NULL[k].z(raw[k]))
        hit = False
        for k in ("U1", "U2", "U3"):
            if raw[k] >= THR[k]:
                det[k] += 1
                hit = True
        det_any += int(hit)
        h, ho = informed_play(cm, mod, S1, S2, S3, rngP)
        advs.append(h - K / 4.0)
        hots.append(ho)
    return dict(m=m_mod, R=R, theta=theta, family=family, reps=reps,
                adv=float(np.mean(advs)), hot=float(np.mean(hots)),
                se=float(np.std(advs, ddof=1) / math.sqrt(reps))
                if reps > 1 else float("nan"),
                z={k: float(np.mean(v)) for k, v in zs.items()},
                pw={k: det[k] / reps for k in det}, pw_any=det_any / reps)


rule("5. PUISSANCE MESURÉE")
say("\nContamination : m numéros modulés, chacun par R triplets sources, "
    "tilt de")
say("logit θ·v où v est la fonction pure-triplet EXACTEMENT orthogonale aux "
    "80")
say("indicatrices et aux 3 160 paires (section 1a). Détection = la "
    "statistique")
say("dépasse son seuil de registre (section 2). L'avantage est celui d'un "
    "joueur")
say("qui CONNAÎT la règle, sur une grille de 10 — mesuré en jouant la "
    "stratégie.")

HDR = (f"  {'theta':>6}{'chauds':>8}{'avantage':>11}{'%':>8}"
       f"{'z(U1)':>9}{'z(U2)':>9}{'z(U3)':>9}{'pwU1':>7}{'pwU2':>7}"
       f"{'pwU3':>7}{'pw v':>7}")


def show(row):
    say(f"  {row['theta']:>6.2f}{row['hot']:>8.2f}{row['adv']:>+11.4f}"
        f"{row['adv']/2.5:>+8.2%}"
        f"{row['z']['U1']:>+9.1f}{row['z']['U2']:>+9.1f}{row['z']['U3']:>+9.1f}"
        f"{row['pw']['U1']:>7.0%}{row['pw']['U2']:>7.0%}{row['pw']['U3']:>7.0%}"
        f"{row['pw_any']:>7.0%}")


# grilles figées d'après un pilote de 10 nulls + 4 archives contaminées
# (frontière de détection ~θ=0,19 pour « tiers » via U2, ~θ=0,16 pour
# « membre » via U2/U3) — figées AVANT le run officiel
GRID_A = (0.18, 0.35) if DRY else (0.14, 0.20, 0.28)
GRID_B = (0.12, 0.25) if DRY else (0.10, 0.15, 0.22)

say("\n5a. FAMILLE « TIERS » — le triplet (i,j,k) appelle un numéro n hors "
    "du triplet")
say(f"    m = 80 numéros modulés, R = 2 triplets sources chacun "
    f"(160 cellules / {NCELL})")
say("\n" + HDR)
TAB_A = []
for th in GRID_A:
    r = measure(80, 2, th, REPS_POWER, "tiers", full=True)
    TAB_A.append(r)
    show(r)
say("    U3 doit rester à zéro ici : aucune cellule n ∈ {i,j,k} n'est "
    "touchée.")

say("\n5b. FAMILLE « MEMBRE » — rémanence CUBIQUE : le triplet (n,j,k) "
    "rallume n")
say(f"    m = 80, R = 2 (160 cellules dans le bloc n ∈ {{i,j,k}} de "
    f"{NBLOCK})")
say("\n" + HDR)
TAB_B = []
for th in GRID_B:
    r = measure(80, 2, th, REPS_POWER, "membre", full=True)
    TAB_B.append(r)
    show(r)
say(f"    U3 mord ici à plus basse amplitude que U1 : {NBLOCK} cellules au "
    f"lieu de")
say(f"    {NCELL}, donc un excès à franchir de "
    f"{Z_REG*NULL['U3'].sd:.0f} au lieu de {Z_REG*NULL['U1'].sd:.0f} — un "
    f"facteur {NULL['U1'].sd/NULL['U3'].sd:.1f}.")

say("\n5c. DIFFUS CONTRE ISOLÉ — pourquoi U1 et U2 ne sont pas redondantes")
say(f"\n  {'règles':<12}{'cellules':>9}{'theta':>7}{'avantage':>11}"
    f"{'z(U1)':>9}{'z(U2)':>9}{'pwU1':>7}{'pwU2':>7}")
TAB_C = []
for (mm, rr, th) in (((1, 1, 0.35), (80, 8, 0.15)) if DRY else
                     ((1, 1, 0.35), (4, 1, 0.35), (80, 2, 0.30),
                      (80, 8, 0.15))):
    r = measure(mm, rr, th, max(2, REPS_POWER // 2), "tiers")
    r["label"] = f"m={mm} R={rr}"
    TAB_C.append(r)
    say(f"  {r['label']:<12}{mm*rr:>9}{r['theta']:>7.2f}{r['adv']:>+11.4f}"
        f"{r['z']['U1']:>+9.1f}{r['z']['U2']:>+9.1f}"
        f"{r['pw']['U1']:>7.0%}{r['pw']['U2']:>7.0%}")

say("\n5d. SPÉCIFICITÉ — ce que les tests DÉJÀ au registre voient de la "
    "même chose")
say(f"\n  {'famille':>8}{'theta':>7}{'z(T1)':>8}{'z(T2)':>8}{'z(S1)':>8}"
    f"{'z(Q1)':>8}{'z(Q2)':>8}{'z(Q3)':>8}{'  |':>3}{'z(U1)':>8}"
    f"{'z(U3)':>8}{'pw v':>7}")
for lbl, tab in (("tiers", TAB_A), ("membre", TAB_B)):
    for row in tab:
        say(f"  {lbl:>8}{row['theta']:>7.2f}{row['z']['T1']:>+8.2f}"
            f"{row['z']['T2']:>+8.2f}{row['z']['S1']:>+8.2f}"
            f"{row['z']['Q1']:>+8.2f}{row['z']['Q2']:>+8.2f}"
            f"{row['z']['Q3']:>+8.2f}{'  |':>3}{row['z']['U1']:>+8.1f}"
            f"{row['z']['U3']:>+8.1f}{row['pw_any']:>7.0%}")
say("\n    T1, T2, S1 ET Q1, Q2, Q3 restent dans le bruit là où U1 ou U3")
say("    sortent : Cov(v, x_a) = 0 et Cov(v, w_ab) = 0 EXACTEMENT")
say("    (section 1a) — la famille testée ici est disjointe de TOUTES les")
say("    familles conditionnelles déjà bornées, y compris h24.")

say("\n5e. LA RÉCIPROQUE — la contamination QUADRATIQUE de h24, vue d'ici")
say("    (le tilt de h24 vit dans l'espace des paires, que la projection")
say("    d'ici retire : U1/U2/U3 doivent y être aveugles)")
_tabE = []
for th24 in ((0.10,) if DRY else (0.08, 0.10)):
    _mq, _si, _sj = make_rules24(80, 2, rngP)
    _cq = gen_quad24(N, _mq, _si, _sj, th24, rngP)
    _u1, _u2, _u3 = u_stats(_cq)
    _q1, _q2, _q3 = q_stats24(_cq)
    say(f"    θ24 = {th24:.2f} :  z(Q1) = {NULL['Q1'].z(_q1):+.1f}  "
        f"z(Q2) = {NULL['Q2'].z(_q2):+.1f}  "
        f"z(Q3) = {NULL['Q3'].z(_q3):+.1f}   |   "
        f"z(U1) = {NULL['U1'].z(_u1):+.2f}  z(U2) = {NULL['U2'].z(_u2):+.2f}  "
        f"z(U3) = {NULL['U3'].z(_u3):+.2f}")
say("    La disjonction des familles est donc mesurée dans les DEUX sens.")


# --------------------------------------------------------------------------
# 6. L'enveloppe de l'adversaire — le plafond d'exploitabilité
# --------------------------------------------------------------------------

rule("6. LE PLAFOND : LE MEILLEUR BIAIS CUBIQUE QUI AURAIT ÉCHAPPÉ")
say("\nMême question que c0, c1 et h24, sur la famille neuve : parmi les")
say("couplages cubiques que 70 560 tirages n'auraient PAS vus, lequel donne")
say("le plus gros avantage à qui le connaîtrait ? Structure BALAYÉE.")

# le pilote montre que U2 borne le PAR-CELLULE (δ ∝ θ, indépendant de m et
# R) pendant que U1 ne voit que m·R·δ² : l'adversaire optimal ÉTALE donc ses
# règles sous la frontière de U2. Le balayage doit couvrir R grand.
CONFIGS = ((("tiers", 80, 2), ("membre", 80, 2)) if DRY else
           (("tiers", 80, 2), ("tiers", 80, 4), ("tiers", 80, 8),
            ("membre", 80, 2)))
GRID_BY_FAM = ({"tiers": (0.18, 0.35), "membre": (0.12, 0.25)} if DRY else
               {"tiers": (0.12, 0.18, 0.26),
                "membre": (0.10, 0.15, 0.22)})
GRID_SWEEP = GRID_BY_FAM["tiers"]

say(f"\n  {'famille':>8}{'m':>4}{'R':>3}{'theta':>7}{'chauds':>8}"
    f"{'avantage':>11}{'%':>8}{'pwU1':>7}{'pwU2':>7}{'pwU3':>7}{'pw v':>7}")
BEST, SWEEP = None, []
for (fam, mm, rr) in CONFIGS:
    for th in GRID_BY_FAM[fam]:
        r = measure(mm, rr, th, REPS_SWEEP, fam)
        SWEEP.append(r)
        say(f"  {fam:>8}{mm:>4}{rr:>3}{th:>7.3f}{r['hot']:>8.2f}"
            f"{r['adv']:>+11.4f}{r['adv']/2.5:>+8.2%}{r['pw']['U1']:>7.0%}"
            f"{r['pw']['U2']:>7.0%}{r['pw']['U3']:>7.0%}{r['pw_any']:>7.0%}")
        if r["pw_any"] < 0.5 and (BEST is None or r["adv"] > BEST["adv"]):
            BEST = r

if BEST is None:
    BEST = min(SWEEP, key=lambda s: s["pw_any"])
    say("\n  ATTENTION : aucune configuration sous 50 % de puissance dans "
        "la grille ;")
    say("  la borne ci-dessous est SUR-ESTIMÉE (le plafond réel est plus "
        "bas).")

say(f"\n  Enveloppe retenue : famille {BEST['family']}, m = {BEST['m']}, "
    f"R = {BEST['R']},")
say(f"  θ = {BEST['theta']:.3f} — puissance {BEST['pw_any']:.0%} sur "
    f"{BEST['reps']} archives.")
say(f"\n  Re-mesure à l'enveloppe sur {REPS_EDGE} archives (le balayage à "
    f"{REPS_SWEEP} ne")
say("  sépare pas 0 % de 50 %) :")
EDGE = measure(BEST["m"], BEST["R"], BEST["theta"], REPS_EDGE,
               BEST["family"], full=True)
if EDGE["pw_any"] >= 0.5:
    lower = [t for t in GRID_BY_FAM[BEST["family"]] if t < BEST["theta"]]
    say(f"    la re-mesure donne {EDGE['pw_any']:.0%} : l'enveloppe du "
        f"balayage était trop")
    say("    haute. On redescend d'un cran — report honnête du bruit "
        "d'estimation.")
    if lower:
        EDGE = measure(BEST["m"], BEST["R"], max(lower), REPS_EDGE,
                       BEST["family"], full=True)
    else:
        say("    ATTENTION : plus bas point de la grille déjà détecté — le "
            "plafond")
        say("    ci-dessous est SUR-ESTIMÉ.")
say(f"    θ retenu {EDGE['theta']:.3f}")
say(f"    avantage {EDGE['adv']:+.4f} ± {EDGE['se']:.4f} hits, soit "
    f"{EDGE['adv']/2.5:+.2%}")
say(f"    puissance mesurée {EDGE['pw_any']:.0%}   "
    f"(U1 {EDGE['pw']['U1']:.0%}, U2 {EDGE['pw']['U2']:.0%}, "
    f"U3 {EDGE['pw']['U3']:.0%})")
say(f"    z moyens : U1 {EDGE['z']['U1']:+.1f}  U2 {EDGE['z']['U2']:+.1f}  "
    f"U3 {EDGE['z']['U3']:+.1f}  |  Q1 {EDGE['z']['Q1']:+.2f}  "
    f"Q3 {EDGE['z']['Q3']:+.2f}  T1 {EDGE['z']['T1']:+.2f}  "
    f"T2 {EDGE['z']['T2']:+.2f}  S1 {EDGE['z']['S1']:+.2f}")

CEIL = EDGE["adv"] / (K / 4.0)
say(f"\n  PLAFOND D'EXPLOITABILITÉ DE LA FAMILLE CUBIQUE :")
say(f"    {EDGE['adv']:+.4f} hits sur 2,50, soit {CEIL:+.2%} de rendement")
say(f"\n  à comparer : marginal (c0) +1,33 %  |  linéaire lag-1 (c1) "
    f"+3,21 %")
say(f"              lags 1..306 (d2) +3,46 %  |  quadratique lag-1 (h24) "
    f"+6,27 %")
say(f"              avantage de la maison −25 à −35 %")

# confrontation avec la prédiction du §41 (h30), posée AVANT cette mesure
say(f"\n  CONFRONTATION : le §41 (h30, loi plafond = ‖a‖·(2m)^(1/4)·√(z/N),")
say(f"  voie indépendante de celle-ci) prédit pour l'ordre 3 un plafond")
say(f"  entre +8,9 % et +14,2 %. Mesuré ici : {CEIL:+.2%} — " +
    ("DANS la fourchette : la loi tient."
     if 0.089 <= CEIL <= 0.142 else
     "HORS de la fourchette : c'est la loi du §41 qui est fausse, et il "
     "faut le dire."))
say(f"  (rapport mesuré des plafonds 3/2 : {CEIL*100/6.27:.2f} ; la loi à "
    f"‖a‖ égal donne 2,26)")


# --------------------------------------------------------------------------
# 7. Registre
# --------------------------------------------------------------------------

rule("7. REGISTRE")

pw_ref = None
for row in TAB_A + TAB_B:
    if row["pw_any"] >= 0.5:
        pw_ref = row
        break
pw_txt = (f"famille {pw_ref['family']} m=80 R=2 : theta={pw_ref['theta']:.2f} "
          f"(avantage {pw_ref['adv']/2.5:+.1%}) detecte a "
          f"{pw_ref['pw_any']:.0%} ; plafond de la famille {CEIL:+.2%}"
          if pw_ref else
          f"voir tables de la section 5 ; plafond de la famille {CEIL:+.2%}")

if DRY:
    say("\n*** DRY RUN : rien n'est écrit au registre ***")
    for k in ("U1", "U2", "U3"):
        say(f"  {k}: observé {RES[k][0]:.4f}  z = {RES[k][1]:+.2f}  "
            f"p = {RES[k][2]:.4f}")
else:
    NOTE = (f"famille NEUVE : couplage cubique (triplet du tirage t -> "
            f"numero du tirage t+1), parts lineaire ET quadratique retirees "
            f"par projection empirique sur les 3160 produits de paires (qui "
            f"contiennent exactement les 80 indicatrices), donc disjointe "
            f"des familles bornees par c0/c1/d2/h24 — demontre en rationnels "
            f"et mesure dans les deux sens. Plafond d'exploitabilite : "
            f"{CEIL:+.2%} (enveloppe {BEST['family']} m={BEST['m']} "
            f"R={BEST['R']} theta={EDGE['theta']:.3f}, puissance "
            f"{EDGE['pw_any']:.0%} sur {REPS_EDGE} archives). Sous "
            f"contamination detectee, T1/T2 (c1), S1 (d3) et Q1/Q2/Q3 (h24) "
            f"restent dans le bruit.")
    for tok, key, extra in (
            (TOK1, "U1", f"cellules |Z|>4 : {ST_REAL['nz4']} pour "
                         f"{NCELL*math.erfc(4/math.sqrt(2)):.0f} attendues"),
            (TOK2, "U2", f"cellule extreme : numero {n_max+1} | triplet "
                         f"({TA[t_max]+1},{TB[t_max]+1},{TC[t_max]+1})"),
            (TOK3, "U3", "sous-bloc n dans le triplet, 246 480 cellules ; "
                         "temoin propre (famille membre), aveugle a la "
                         "famille tiers comme attendu")):
        obs, z, p = RES[key]
        lab.record(tok, observed=obs, null=NULL[key], power_at=pw_txt,
                   verdict="conforme" if p > P_REG else "À RÉEXAMINER",
                   notes=NOTE + " | " + extra)
        say(f"  consigné {tok['id']:<22} observé {obs:.4f}  z = {z:+.2f}  "
            f"p = {p:.4f}")

    tok4 = lab.preregister(
        "h27.plafond_cube",
        "Parmi les couplages CUBIQUES (triplet -> numero, lag 1) que 70 560 "
        "tirages n'auraient pas detectes, quel est le plus gros avantage "
        "pour qui le connaitrait ?",
        "avantage E[hits]-2,5 d'une grille de 10 jouee par un joueur "
        "omniscient, a l'enveloppe (famille, m, R et amplitude theta "
        "balayees, puissance < 50 %)",
        f"balayage de {len(CONFIGS)} structures x "
        f"{len(GRID_SWEEP)} amplitudes, {REPS_SWEEP} archives contaminees "
        f"par point, seuils de registre de la section 2 ; re-mesure a "
        f"l'enveloppe sur {REPS_EDGE} archives",
        "borne rapportee, pas de p — c'est une mesure d'ignorance "
        "residuelle, pas un test",
        track="A")
    lab.record(tok4, observed=EDGE["adv"],
               power_at=f"puissance {EDGE['pw_any']:.0%} a l'enveloppe "
                        f"({REPS_EDGE} archives)",
               verdict=f"plafond {CEIL:+.2%} de rendement",
               notes=(f"enveloppe famille={BEST['family']} m={BEST['m']} "
                      f"R={BEST['R']} theta={EDGE['theta']:.3f} ; borne "
                      f"d'OMNISCIENCE STRICTE : h26 mesure une part captee "
                      f"de 11 % deja a l'ordre 2 (252 800 cellules, "
                      f"realisable +0,71 %), a 6 572 800 cellules le "
                      f"realisable serait une fraction plus petite encore ; "
                      f"lag 1 seulement ; null a {REPS_NULL} replicats "
                      f"(reduction declaree) ; confronte a la prediction du "
                      f"paragraphe 41 (h30) : fourchette +8,9 % a +14,2 % ; "
                      f"a comparer : c0 +1,33 %, c1 +3,21 %, d2 +3,46 %, "
                      f"h24 +6,27 %"))
    say(f"  consigné {tok4['id']:<22} plafond {CEIL:+.2%}")

    h = lab.holm()
    nsig = sum(1 for r in h if r["significant"])
    say(f"\n  lab.holm() : m = {h[0]['m_total']}, seuil "
        f"{h[0]['holm_threshold']:.3e}, {nsig} significatif(s)")
    say(f"  plus petit p du registre : {h[0]['id']} à p = {h[0]['p']:.2e}")
    say("  rang des trois entrées de h27 :")
    for i, r in enumerate(h):
        if r["id"].startswith("h27."):
            say(f"    {r['id']:<22} p = {r['p']:.4f}   rang {i+1}/{len(h)}   "
                f"significatif : {r['significant']}")

say(f"\n{'=' * 78}\ntotal {time.time() - T0:.0f}s")
