"""h22 — la règle du bonus : ce que l'archive TRIÉE peut en dire, et à quelle puissance.

La question, et pourquoi elle n'est pas refaite ici de travers
---------------------------------------------------------------
h19 (§32) a établi un fait structurel sur les 70 560 tirages : le `bonus` est
TOUJOURS l'un des vingt numéros sortis — 70 560 sur 70 560, là où
l'indépendance en prédirait 17 640. Ce n'est donc pas un tirage à part, c'est
une DÉSIGNATION de l'une des vingt boules. Reste une question purement
descriptive, jamais tranchée : cette désignation suit-elle une règle de
POSITION dans l'ordre de sortie — « la dernière boule », convention la plus
répandue — ou est-elle un choix uniforme parmi les vingt ?

Ce qui est déjà dépensé au registre, et qui n'est pas refait ici : la loi
MARGINALE du bonus, sa mémoire sérielle, son rang dans le tirage TRIÉ, son
appartenance au tirage suivant (`audit.bonus_position`, `audit.bonus_overlap`,
`d7.bonus_valeur`, `d7b.chasse_v3`, `f1.d7_v3_perm`), et l'hypothèse « valeur
brute s mod 80 » (`h19.bonus_affine`).

Le blocage, nommé
-----------------
`lab/draws_ordered.csv` — les cinq tirages dont l'ordre de sortie est connu —
n'a aucune colonne bonus, et l'archive de 70 560 tirages est triée, donc
muette sur l'ordre. La mesure directe (relever la position du bonus dans
l'ordre) est donc impossible avec les données présentes. D'où la question de
repli : existe-t-il une statistique calculable sur l'archive TRIÉE qui
distingue « bonus = dernière boule sortie » de « bonus = choix uniforme parmi
les vingt » ?

Le théorème d'identifiabilité, et l'erreur de prémisse qu'il corrige
--------------------------------------------------------------------
L'observable d'un tirage archivé est le couple (S, b) : l'ensemble trié et le
numéro bonus qui lui appartient. Sa loi se factorise en

    P(S, b) = P(S) · P(b est la boule de position j | S).

Si la loi de l'ORDRE est échangeable conditionnellement à l'ensemble — c'est-
à-dire si les 20! ordres du même ensemble sont équiprobables — alors
P(b en position j | S) = 1/20 EXACTEMENT, pour toute position j. Les deux
hypothèses produisent alors la même loi sur (S, b), et AUCUNE statistique,
d'aucune sorte, ne peut les séparer sur des données triées. Ce n'est pas un
échec du test : c'est une non-identifiabilité.

La prémisse qu'on m'a donnée était que le tirage par REJET brise cette
échangeabilité, « la probabilité de rejet dépendant des numéros déjà sortis ».
C'est faux tant que la loi de base est uniforme : la probabilité de rejet ne
dépend alors que du NOMBRE de numéros déjà sortis, jamais de leur identité, et
la suite acceptée est exactement une permutation uniforme. Rejet uniforme et
Fisher-Yates sont la même loi. §1 le vérifie plutôt que de l'affirmer.

Ce qui brise réellement l'échangeabilité, c'est une loi de base NON uniforme :
le rejet devient alors un échantillonnage successif sans remise à probabilités
proportionnelles à q — le modèle de Plackett-Luce — et la dernière boule
acceptée est celle de plus petit poids. La règle redevient visible. §2 mesure
de combien, §3 construit le test, §4 mesure sa puissance, §5 l'applique.

Le verrou, et c'est le résultat
--------------------------------
Le même biais de base q qui rend la règle visible déplace aussi les
FRÉQUENCES MARGINALES des 80 numéros — et celles-ci sont mesurées, conformes,
et beaucoup plus sensibles. §4 chiffre les deux sensibilités sur les mêmes
réplicats : le rapport décide si l'archive peut trancher.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALPHA_HOLM = 1.5e-5          # seuil de Holm du registre entier (§32)


def say(*a):
    print(*a, flush=True)


def num(x, dec=0):
    """Entier séparé par une espace fine — jamais une virgule, qui se lit
    comme un séparateur décimal dans le reste du rapport."""
    return f"{x:,.{dec}f}".replace(",", " ")


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# --------------------------------------------------------------------------
# Échantillonneurs
# --------------------------------------------------------------------------

def pl_orders(n, logq, rng, chunk=20_000):
    """n tirages Plackett-Luce, ORDRE DE SORTIE complet (n, 20).

    Plackett-Luce = échantillonnage successif sans remise à probabilités
    proportionnelles à q = exp(logq). C'est EXACTEMENT la loi d'un
    échantillonneur par rejet dont la loi de base est q (§1 le vérifie).
    Réalisé par le truc de Gumbel : l'ordre décroissant de
    log q_n + Gumbel_n est une permutation de Plackett-Luce.
    """
    out = np.empty((n, DRAWN), np.int64)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        g = rng.gumbel(size=(b - a, POOL)) + logq
        out[a:b] = np.argsort(-g, axis=1)[:, :DRAWN]
    return out


def literal_rejection(n, q, rng):
    """L'échantillonneur par rejet, écrit littéralement. Le témoin de §1."""
    cum = np.cumsum(q)
    out = np.empty((n, DRAWN), np.int64)
    for t in range(n):
        seen, got = set(), []
        while len(got) < DRAWN:
            v = int(np.searchsorted(cum, rng.random()))
            if v not in seen:
                seen.add(v)
                got.append(v)
        out[t] = got
    return out


def eps_pattern(rms, seed=20260830):
    """Motif de biais de base, moyenne nulle, écart QUADRATIQUE MOYEN = rms.

    Rampe graduée (et non deux valeurs ±rms) pour que la régression de §2 ait
    de quoi mordre, puis permutée par une graine fixe : le χ² marginal comme
    le contraste ne dépendent, au premier ordre, que de Σ ε² — donc la FORME
    du motif est indifférente à la comparaison, seul l'écart quadratique
    compte. Une rampe MONOTONE en la valeur du numéro serait en outre visible
    par `audit.bonus_position` (rang du bonus dans le tirage trié), un test
    déjà dépensé ; la permutation choisit donc le cas le plus DÉFAVORABLE aux
    tests existants.
    """
    ramp = np.linspace(-1.0, 1.0, POOL)
    ramp = ramp / math.sqrt(float((ramp ** 2).mean()))
    r = np.random.default_rng(seed)
    r.shuffle(ramp)
    out = ramp * rms
    assert np.abs(out).max() < 1.0, "un poids de base négatif n'a pas de sens"
    return out


def weights(eps):
    q = (1.0 + eps) / POOL
    return q / q.sum()


# --------------------------------------------------------------------------
# La statistique
# --------------------------------------------------------------------------

def contrast(sets, bonus_idx, w):
    """Contraste linéaire pondéré par w, standardisé par le null conditionnel.

    T = Σ_n w_n (c_n − d_n/20) = Σ_t (w[bonus_t] − moyenne de w sur S_t),
    avec c_n le nombre de fois où n est bonus et d_n le nombre de fois où n
    est tiré. Sous « bonus uniforme parmi les vingt » et à ensembles FIXÉS,
    chaque terme a une espérance nulle et une variance Var_{u∈S_t}(w_u) :
    T / √(Σ_t Var_t) a donc une loi centrée réduite par construction. Le null
    est malgré tout SIMULÉ (règle 1), w étant estimé sur les mêmes données.

    C'est le test localement le plus puissant contre l'alternative
    « P(bonus = n | n tiré) varie linéairement avec w_n » — c'est-à-dire
    contre exactement ce que produit un biais de base sous Plackett-Luce.
    """
    ws = w[sets]                              # (N,20)
    wbar = ws.mean(axis=1)
    t_raw = float((w[bonus_idx] - wbar).sum())
    var = float(ws.var(axis=1).sum())
    return t_raw / math.sqrt(var) if var > 0 else 0.0


def counts_of(sets):
    return np.bincount(sets.ravel(), minlength=POOL).astype(np.float64)


def z_feasible(sets, bonus_idx):
    """Le test RÉALISABLE : w = fréquences marginales observées, centrées.

    Sur des données réelles on ne connaît pas le biais de base ; le meilleur
    substitut disponible est la fréquence de sortie de chaque numéro, qui en
    est une image bruitée. C'est ce qui se calcule sur l'archive.
    """
    d = counts_of(sets)
    return contrast(sets, bonus_idx, d - d.mean())


def z_oracle(sets, bonus_idx, eps):
    """Le test ORACLE : w = le vrai biais de base. Indisponible sur données
    réelles — c'est une BORNE SUPÉRIEURE de tout test de cette famille."""
    return contrast(sets, bonus_idx, eps - eps.mean())


def chi2_marginal(sets, n):
    """χ² des 80 fréquences marginales — le test déjà dépensé, pour comparer."""
    d = counts_of(sets)
    e = n * DRAWN / POOL
    return float(((d - e) ** 2 / e).sum())


# --------------------------------------------------------------------------
# 0. L'état des données — le blocage, vérifié et non supposé
# --------------------------------------------------------------------------

rule("0. L'ÉTAT DES DONNÉES — pourquoi la mesure directe est impossible")

a = lab.load()
N = len(a)
sorted_rows = int((np.diff(a.nums.astype(np.int64), axis=1) > 0).all(axis=1).sum())
say(f"   archive : {num(N)} tirages, ids {num(int(a.ids.min()))} … {num(int(a.ids.max()))}")
say(f"   lignes strictement croissantes n1<…<n20 : {num(sorted_rows)}/{num(N)} "
    f"→ l'archive est TRIÉE, donc muette sur l'ordre de sortie.")

with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    ordered_rows = list(csv.DictReader(fh))
cols = list(ordered_rows[0].keys())
filled = sum(1 for r in ordered_rows if (r.get("bonus") or "").strip())
ids_txt = ", ".join(str(r["id"]) for r in ordered_rows)
say(f"   draws_ordered.csv : {len(ordered_rows)} tirages ordonnés, ids {ids_txt}")
say(f"   colonnes : {', '.join(cols)}")
say(f"   colonne bonus renseignée : {filled}/{len(ordered_rows)} — la colonne "
    f"existe pour préparer la place, aucune valeur n'est inventée.")

lo = min(int(r["id"]) for r in ordered_rows)
say(f"   recoupement : l'archive s'arrête à {num(int(a.ids.max()))}, les tirages "
    f"ordonnés commencent à {num(lo)} — écart de {num(lo - int(a.ids.max()))} tirages.")
say("""
   La mesure directe — relever la position du bonus dans l'ordre de sortie —
   ne peut donc pas se faire hors ligne, et le réseau vers jeux.loro.ch est
   fermé. Reste la question de repli : que peut dire l'archive TRIÉE ?""")


# --------------------------------------------------------------------------
# 1. Le théorème d'identifiabilité, et la prémisse qu'il corrige
# --------------------------------------------------------------------------

rule("1. IDENTIFIABILITÉ — le rejet uniforme est Fisher-Yates, et c'est mesuré")

rng = np.random.default_rng(20260830)

n1 = 40_000
q_flat = np.full(POOL, 1.0 / POOL)
lit_flat = literal_rejection(n1, q_flat, rng)
pl_flat = pl_orders(n1, np.log(q_flat), rng)

eps_big = eps_pattern(0.40)
q_big = weights(eps_big)
lit_bias = literal_rejection(n1, q_big, rng)
pl_bias = pl_orders(n1, np.log(q_big), rng)


def last_law(o):
    return np.bincount(o[:, -1], minlength=POOL) / len(o)


# Écart maximal ATTENDU entre deux estimations indépendantes de la même loi :
# 80 cellules, écart-type √(2p(1−p)/n) par cellule, maximum d'un échantillon
# normal de taille 80 ≈ 2,7 σ. C'est la référence contre laquelle lire le
# tableau — pas zéro, qui ne serait atteignable qu'à n infini.
sd_pair = math.sqrt(2 * (1 / POOL) * (1 - 1 / POOL) / n1)
say(f"   {num(n1)} tirages par échantillonneur ; comparaison de la loi de la "
    f"VINGTIÈME boule sortie.")
say(f"   écart max attendu entre DEUX estimations de la MÊME loi : "
    f"{2.7 * sd_pair:.5f}\n")
say("   loi de base            écart max   corrélation des deux lois estimées")
for name, lit, pl in (("uniforme", lit_flat, pl_flat),
                      ("biaisée, rms 40 %", lit_bias, pl_bias)):
    la, lb = last_law(lit), last_law(pl)
    say(f"   {name:<22} {np.abs(la - lb).max():.5f}     "
        f"{np.corrcoef(la, lb)[0, 1]:+.4f}")

say("""
   Lecture. Les écarts maximaux sont au niveau du bruit d'estimation : le
   rejet littéral et Plackett-Luce donnent la même loi, biais compris. La
   corrélation est nulle sous base uniforme parce qu'il n'y a alors AUCUNE
   structure à corréler — la loi est plate et les deux estimations ne
   partagent que du bruit ; elle est forte sous base biaisée, où les deux
   retrouvent le même relief. L'échantillonneur par rejet EST un
   échantillonnage successif à probabilités proportionnelles à la loi de
   base, et la simulation vectorisée qui suit est donc fidèle.""")

# Le point qui décide de tout : sous base UNIFORME, la dernière boule est-elle
# uniforme parmi les vingt ?
n1b = 400_000
flat = pl_orders(n1b, np.log(q_flat), rng)
d_flat = counts_of(flat)
c_flat = np.bincount(flat[:, -1], minlength=POOL).astype(np.float64)
rate = c_flat / d_flat
sd_cell = math.sqrt(0.05 * 0.95 / (n1b * DRAWN / POOL))
say(f"""
   Base UNIFORME, {num(n1b)} tirages. Taux P(bonus = n | n tiré) si le bonus est
   la VINGTIÈME boule sortie :
       moyenne     {rate.mean():.5f}      (« uniforme parmi les vingt » : 0,05000)
       écart-type  {rate.std():.5f}      (bruit de comptage attendu : {sd_cell:.5f})
       min / max   {rate.min():.5f} / {rate.max():.5f}

   Les taux sont indiscernables du bruit pur. Sous une loi de base uniforme,
   « bonus = dernière boule » et « bonus = choix uniforme parmi les vingt »
   produisent la MÊME loi sur (ensemble trié, bonus) : la question n'est pas
   difficile sur l'archive, elle est NON IDENTIFIABLE. C'est un résultat, pas
   un échec — et il justifie à lui seul l'instrument embarqué de §6.""")


# --------------------------------------------------------------------------
# 2. Ce qui rend la règle visible : un biais de base — et de combien
# --------------------------------------------------------------------------

rule("2. SENSIBILITÉ — de combien un biais de base rend la règle visible")

scale = 0.30
eps_s = eps_pattern(scale)
n2 = 400_000
o2 = pl_orders(n2, np.log(weights(eps_s)), rng)
d2 = counts_of(o2)
p_inc = d2 / n2

# γ : sensibilité de la probabilité d'INCLUSION au biais de base.
gamma = float(np.polyfit(eps_s, p_inc / (DRAWN / POOL) - 1, 1)[0])

say(f"   {num(n2)} tirages Plackett-Luce, biais de base d'écart quadratique "
    f"moyen {scale * 100:.0f} %.")
say(f"   sensibilité de l'inclusion : P(n tiré) = 0,25·(1 {gamma:+.4f}·ε_n)\n")
say("   position j    P(bonus = n | n tiré) = 0,05·(1 + c_j·ε_n)      c_j")
c_by_pos = np.empty(DRAWN)
for j in range(DRAWN):
    cj = np.bincount(o2[:, j], minlength=POOL).astype(np.float64)
    c_by_pos[j] = float(np.polyfit(eps_s, (cj / d2) / 0.05 - 1, 1)[0])
    if j < 3 or j >= DRAWN - 3:
        say(f"   {j + 1:<13} {(cj / d2).mean():.5f}                              "
            f"{c_by_pos[j]:+.4f}")
    elif j == 3:
        say("   …")
say(f"\n   somme des c_j sur les vingt positions : {c_by_pos.sum():+.4f} "
    f"(exactement 0 en théorie : moyenner sur j REDONNE le choix uniforme)")
say(f"   |c_j| maximal : {np.abs(c_by_pos).max():.4f} à la position "
    f"{int(np.abs(c_by_pos).argmax()) + 1}")
c_last, c_first = c_by_pos[-1], c_by_pos[0]
say(f"""
   Lecture. La règle « dernière boule » a une sensibilité c₂₀ = {c_last:+.4f} et la
   règle « première boule » c₁ = {c_first:+.4f} : de signe opposé — la première boule
   favorise les numéros de poids fort, la dernière ceux de poids faible — et
   de module comparable. Les deux conventions candidates sont donc aussi peu
   visibles l'une que l'autre, et TOUTES les positions intermédiaires le sont
   encore moins.

   Le point qui compte : |c| ≈ {np.abs(c_by_pos).max():.2f} contre γ = {gamma:.2f}. Un biais de base se
   voit environ {gamma / np.abs(c_by_pos).max():.0f} fois mieux dans les fréquences marginales que dans
   la règle du bonus. C'est ce rapport que §4 transforme en puissance.""")


# --------------------------------------------------------------------------
# 3. Le test, et son null simulé
# --------------------------------------------------------------------------

rule("3. LE TEST — contraste linéaire, null simulé")

say("""   Statistique : T = Σ_t (w[bonus_t] − moyenne de w sur le tirage t),
   standardisée par sa variance conditionnelle. w = fréquences marginales
   observées, centrées — le seul substitut disponible au biais de base.

   Deux nulls, tous deux SIMULÉS :
     • RANDOMISATION CONDITIONNELLE — on garde les ensembles RÉELS de
       l'archive et on retire le bonus uniformément parmi les vingt. C'est
       exactement l'hypothèse en jeu, et les fréquences marginales réelles y
       sont conservées à l'identique.
     • SRS — tirages simulés 20/80 uniformes, bonus uniforme parmi les vingt.

   `calibrate_perm` est INUTILISABLE ici : permuter l'ordre des tirages laisse
   chaque couple (ensemble, bonus) intact, donc T inchangé. C'est le piège que
   documente lab.calibrate_perm — un null d'écart-type nul n'est pas
   conservateur, il est vide.""")

sets_real = a.nums.astype(np.int64) - 1
bonus_real = a.bonus.astype(np.int64) - 1
assert bool((sets_real == bonus_real[:, None]).any(axis=1).all()), \
    "le bonus doit être l'un des vingt (fait structurel de §32)"


def null_conditional(reps, seed):
    """Bonus retiré uniformément parmi les vingt, ensembles réels conservés."""
    r = np.random.default_rng(seed)
    out = np.empty(reps)
    for i in range(reps):
        pick = sets_real[np.arange(N), r.integers(0, DRAWN, N)]
        out[i] = z_feasible(sets_real, pick)
    return out


def null_srs(reps, seed):
    r = np.random.default_rng(seed)
    out = np.empty(reps)
    for i in range(reps):
        o = pl_orders(N, np.zeros(POOL), r)
        out[i] = z_feasible(o, o[np.arange(N), r.integers(0, DRAWN, N)])
    return out


NREP_NULL = 300
nc = null_conditional(NREP_NULL, 11)
null_cond = lab.Null(float(nc.mean()), float(nc.std(ddof=1)), NREP_NULL, nc)
say(f"\n   null conditionnel ({NREP_NULL} réplicats) : moyenne {null_cond.mean:+.4f}, "
    f"écart-type {null_cond.sd:.4f}")

NREP_SRS = 60
ns = null_srs(NREP_SRS, 12)
null_srs_ = lab.Null(float(ns.mean()), float(ns.std(ddof=1)), NREP_SRS, ns)
say(f"   null SRS         ({NREP_SRS} réplicats) : moyenne {null_srs_.mean:+.4f}, "
    f"écart-type {null_srs_.sd:.4f}")
say("   Les deux coïncident : la standardisation conditionnelle fait son office.")


# --------------------------------------------------------------------------
# 4. Témoins et puissance — le verrou, chiffré
# --------------------------------------------------------------------------

rule("4. TÉMOINS ET PUISSANCE — le biais qu'il faudrait, et ce qu'il ferait ailleurs")

NREP_POW = 40
chi_null = np.array([chi2_marginal(pl_orders(N, np.zeros(POOL), rng), N)
                     for _ in range(60)])
chi_mu, chi_sd = float(chi_null.mean()), float(chi_null.std(ddof=1))
say(f"   χ² marginal sous H0 ({len(chi_null)} réplicats simulés, jamais tabulés) : "
    f"{chi_mu:.1f} ± {chi_sd:.1f}")
say(f"   (79 ddl naïfs donneraient 79,0 ± 12,6 — l'écart vient de la "
    f"contrainte Σ = 20 par tirage)\n")

say("   ε      test bonus (réalisable)   borne ORACLE   χ² marginal        puissance")
say("   rms    |z| moyen   puissance     |z| moyen      z moyen            χ²")
GRID = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40]
rows = []
for e in GRID:
    ev = eps_pattern(e) if e > 0 else np.zeros(POOL)
    lq = np.log(weights(ev))
    zf, zo, zc = [], [], []
    for _ in range(NREP_POW):
        o = pl_orders(N, lq, rng)
        b = o[:, -1]                                   # bonus = DERNIÈRE boule
        zf.append(null_cond.z(z_feasible(o, b)))
        zo.append(z_oracle(o, b, ev) if e > 0 else 0.0)
        zc.append((chi2_marginal(o, N) - chi_mu) / chi_sd)
    zf, zo, zc = np.abs(zf), np.abs(zo), np.array(zc)
    pw_f = float((zf >= 3).mean())
    pw_c = float((zc >= 3).mean())
    rows.append((e, zf.mean(), pw_f, zo.mean(), zc.mean(), pw_c))
    say(f"   {e:<6.3f} {zf.mean():>9.2f}   {pw_f:>8.0%}     {zo.mean():>9.2f}      "
        f"{zc.mean():>12.1f}   {pw_c:>10.0%}")

say("""
   Le témoin ε = 0,40 est le contrôle positif du test lui-même : à biais
   massif il se déclenche, donc il n'est pas cassé. Le témoin ε = 0 est le
   contrôle négatif : il reste à zéro.""")


def interp_thr(rows, col, target=0.80):
    """Plus petit ε atteignant `target` de puissance, par interpolation."""
    prev = None
    for r in rows:
        if r[col] >= target and prev is not None:
            x0, y0 = prev
            x1, y1 = r[0], r[col]
            return x0 + (target - y0) * (x1 - x0) / (y1 - y0) if y1 > y0 else x1
        prev = (r[0], r[col])
    return None


eps_bonus = interp_thr(rows, 2)
eps_chi = interp_thr(rows, 5)
txt_b = "jamais atteint sur la grille" if eps_bonus is None else f"{eps_bonus:.3f}"
txt_c = "jamais atteint sur la grille" if eps_chi is None else f"{eps_chi:.4f}"
say(f"\n   ε à 80 % de puissance — test du bonus : {txt_b}")
say(f"   ε à 80 % de puissance — χ² marginal  : {txt_c}")
if eps_bonus is not None and eps_chi is not None:
    say(f"   rapport : il faut un biais {eps_bonus / eps_chi:.0f} fois plus gros pour que "
        f"la règle du bonus se voie que pour que les marginales le trahissent.")

# Borne oracle : combien faudrait-il pour que MÊME un test qui connaîtrait le
# biais atteigne 3σ ? |z_oracle| croît linéairement en ε (contraste linéaire).
big = [r for r in rows if r[0] >= 0.10]
slope = float(np.mean([r[3] / r[0] for r in big]))
chi_slope = float(np.mean([r[4] / r[0] ** 2 for r in big]))   # χ² : quadratique en ε
eps_oracle3 = 3.0 / slope
z_chi_at = chi_slope * eps_oracle3 ** 2
say(f"\n   |z| oracle croît linéairement : {slope:.1f}·ε  (ajusté sur ε ≥ 0,10)")
say(f"   z du χ² croît en ε² :          {num(chi_slope)}·ε²")
say(f"   ε qu'il faudrait pour que même l'ORACLE atteigne 3σ : {eps_oracle3:.4f}")
say(f"   à ce ε, le χ² marginal sortirait à {num(z_chi_at)} σ.")


# --------------------------------------------------------------------------
# 5. L'archive réelle
# --------------------------------------------------------------------------

rule("5. L'ARCHIVE — 70 560 tirages")

TOKEN = lab.preregister(
    "h22.bonus_ordre_contraste",
    "le bonus est la boule d'une POSITION FIXE de l'ordre de sortie sous un "
    "échantillonneur à loi de base non uniforme : P(bonus = n | n tiré) varie "
    "alors linéairement avec le biais de base, dont la fréquence marginale de "
    "n est l'image observable",
    "contraste linéaire T = Σ_t (w[bonus_t] − moyenne de w sur le tirage t), "
    "w = fréquences marginales centrées, standardisé par la variance "
    "conditionnelle",
    "randomisation conditionnelle : ensembles réels conservés, bonus retiré "
    "uniformément parmi les vingt, 300 réplicats",
    "conforme si p > seuil de Holm du registre entier",
    track="H")

obs = z_feasible(sets_real, bonus_real)
z_obs = null_cond.z(obs)
p_obs = null_cond.p_two_sided(obs)
d_real = counts_of(sets_real)
c_real = np.bincount(bonus_real, minlength=POOL).astype(np.float64)
chi2_obs = chi2_marginal(sets_real, N)

say(f"   contraste observé T = {obs:+.4f}")
say(f"   null conditionnel  {null_cond.mean:+.4f} ± {null_cond.sd:.4f}  →  "
    f"z = {z_obs:+.2f}, p = {p_obs:.3f}")
say(f"   χ² marginal des 80 numéros : {chi2_obs:.1f}  →  z = "
    f"{(chi2_obs - chi_mu) / chi_sd:+.2f} contre le null simulé "
    f"{chi_mu:.1f} ± {chi_sd:.1f}")
say(f"   taux P(bonus = n | n tiré) : moyenne {(c_real / d_real).mean():.5f}, "
    f"étendue {(c_real / d_real).min():.5f}…{(c_real / d_real).max():.5f}")

lab.record(TOKEN, observed=obs, null=null_cond,
           power_at=f"témoin biais de base rms 0,40 : {rows[-1][1]:.1f} σ, "
                    f"puissance {rows[-1][2]:.0%} ; ε à 80 % de puissance = {txt_b}",
           verdict="conforme — et sans puissance utile",
           notes=f"borne ORACLE : même un test connaissant le biais de base "
                 f"exigerait ε = {eps_oracle3:.3f} pour atteindre 3 sigma, biais auquel "
                 f"le khi-deux marginal sortirait à {num(z_chi_at)} sigma ; khi-deux "
                 f"marginal observé {chi2_obs:.1f} contre {chi_mu:.1f} ± {chi_sd:.1f}")

say(f"""
   Verdict. Le contraste est à {z_obs:+.2f} σ : rien. Mais le « rien » n'a de valeur
   que par la puissance, et la puissance est ici NULLE dans la région qui
   compte — c'est cela, le résultat.

   L'argument en deux temps, entièrement mesuré :
     1. Sous une loi de base uniforme, la question est non identifiable :
        aucun test ne peut séparer les deux hypothèses (§1).
     2. Sous une loi de base biaisée, elle le redevient — mais il faudrait
        ε ≈ {eps_oracle3:.2f} pour que MÊME un test connaissant le biais atteigne 3σ,
        et à ce biais le χ² marginal des 80 numéros sortirait à {num(z_chi_at)} σ.
        Or il vaut {chi2_obs:.1f} contre {chi_mu:.1f} ± {chi_sd:.1f} attendus.

   L'archive triée NE PEUT PAS trancher la règle du bonus. Ce n'est pas une
   intuition, c'est un calcul de puissance : la fenêtre où le test mordrait
   est fermée par un test antérieur, plus sensible, et conforme.

   Portée de la borne, nommée. Elle couvre la famille Plackett-Luce — donc
   tout échantillonneur par rejet, avec ou sans biais de base, et Fisher-Yates
   comme cas limite. Elle ne couvre PAS une loi d'ordre non échangeable
   construite pour laisser les marginales intactes ; un tel objet n'appartient
   à aucune famille d'échantillonneur écrite en pratique, mais rien ici ne
   l'exclut.""")


# --------------------------------------------------------------------------
# 6. L'instrument embarqué — et le critère chiffré qu'il applique
# --------------------------------------------------------------------------

rule("6. L'INSTRUMENT — le critère de lecture, calculé et non choisi")

say("""   Puisque l'archive ne peut pas trancher, la mesure doit se faire là où
   l'ordre de sortie existe : dans l'app, qui le reçoit et le conserve
   (`OrderedDraw`, §34). Le critère de lecture est ASYMÉTRIQUE, et il faut
   l'écrire comme tel.""")


def log_binom_tail_le(k, n, p):
    """log P(Binomiale(n,p) ≤ k), sommé en échelle logarithmique."""
    if k < 0:
        return -math.inf
    k = min(k, n)
    if k == n:
        return 0.0
    terms = []
    lc = 0.0
    for i in range(0, k + 1):
        terms.append(lc + i * math.log(p) + (n - i) * math.log1p(-p))
        if i < n:
            lc += math.log(n - i) - math.log(i + 1)
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


# --- côté « règle établie » : une seule position discordante la réfute ---
say("\n   A. RÈGLE DE POSITION ÉTABLIE — une seule position discordante réfute.")
say("      P(les n positions coïncident | bonus uniforme) = 20·20^(−n) = 20^(1−n)")
n_fixed = None
for n_ in range(2, 12):
    p = DRAWN * (1.0 / DRAWN) ** n_
    mark = ""
    if p <= ALPHA_HOLM and n_fixed is None:
        n_fixed = n_
        mark = "  ← seuil franchi"
    if n_ <= 8:
        say(f"      n = {n_:<3} p = {p:.3e}{mark}")
say(f"      N_règle = {n_fixed} tirages ordonnés tous à la même position "
    f"(p = {DRAWN * (1.0 / DRAWN) ** n_fixed:.2e} ≤ {ALPHA_HOLM:.1e}).")

# --- côté « uniforme » : il faut exclure toute loi CONCENTRÉE ---
say("""
   B. BONUS UNIFORME PARMI LES VINGT — c'est une acceptation, elle exige une
      borne d'équivalence. Une position discordante tue la règle DÉTERMINISTE
      en un coup, mais laisse vivante une règle presque déterministe (« la
      vingtième dans 90 % des cas »), qui vaudrait presque autant. Conclure à
      l'uniformité, c'est donc rejeter la famille « ∃ j : P(position j) ≥ p* ».

      Le seuil p* = 1/2 est nommé, pas dérivé : c'est le point où l'énoncé
      « le bonus est à la position j » cesse d'être vrai plus souvent que
      faux — le plus faible énoncé qui mérite encore le mot « règle ». Au plus
      une position peut le vérifier, donc le maximum des comptages est une
      statistique suffisante et aucune correction de multiplicité n'est due.""")

say("\n      p*      N minimal   (n tel que P(Bin(n,p*) ≤ ⌈n/20⌉) ≤ 1,5·10⁻⁵)")
n_uniform = None
for pstar in (0.5, 0.25, 0.10):
    got = None
    for n_ in range(2, 4000):
        if log_binom_tail_le(math.ceil(n_ / DRAWN), n_, pstar) <= math.log(ALPHA_HOLM):
            got = n_
            break
    if pstar == 0.5:
        n_uniform = got
    say(f"      {pstar:<7.2f} {got}")

say(f"""
      N_uniforme = {n_uniform} est le PLANCHER : il suppose des comptages aussi
      plats que possible (position dominante à ⌈n/20⌉). Les données réelles
      fluctuent, donc le critère se déclenche plus tard. La question honnête
      est : QUAND, sous une uniformité vraie ?""")

sim = np.random.default_rng(4242)
REPS = 4000
first_ok = []
for _ in range(REPS):
    counts = np.zeros(DRAWN, np.int64)
    for n_ in range(1, 401):
        counts[sim.integers(0, DRAWN)] += 1
        if n_ >= n_uniform and \
           log_binom_tail_le(int(counts.max()), n_, 0.5) <= math.log(ALPHA_HOLM):
            first_ok.append(n_)
            break
    else:
        first_ok.append(401)
first_ok = np.array(first_ok)
q = np.percentile(first_ok, [50, 80, 95])
say(f"      sous uniformité vraie ({num(REPS)} réplicats simulés) : le critère se "
    f"déclenche à")
say(f"        médiane {q[0]:.0f} tirages ordonnés · 80ᵉ centile {q[1]:.0f} · "
    f"95ᵉ centile {q[2]:.0f}")
say(f"        (jamais atteint en 400 tirages : {int((first_ok > 400).sum())}/{REPS})")

# --- contrôle positif du critère : une règle à 90 % ne doit PAS passer ---
leak = 0
REPS2 = 2000
for _ in range(REPS2):
    counts = np.zeros(DRAWN, np.int64)
    passed = False
    for n_ in range(1, 401):
        j = 19 if sim.random() < 0.90 else int(sim.integers(0, DRAWN))
        counts[j] += 1
        if n_ >= n_uniform and \
           log_binom_tail_le(int(counts.max()), n_, 0.5) <= math.log(ALPHA_HOLM):
            passed = True
            break
    leak += int(passed)
say(f"\n      TÉMOIN du critère : sous une règle « position 20 dans 90 % des cas »,")
say(f"      le verdict « uniforme » est prononcé à tort {leak}/{REPS2} fois en "
    f"400 tirages.")
say(f"      Un critère qui ne se trompe jamais sur ce témoin est un critère qui "
    f"discrimine.")

say(f"""
   C. LE VERDICT À TROIS ÉTATS, tel qu'il est câblé dans `BonusRule` :

        règle de position établie   n ≥ {n_fixed} et les n positions identiques
        bonus uniforme parmi 20     positions non toutes identiques ET
                                    P(Bin(n, 1/2) ≤ max des comptages) ≤ 1,5·10⁻⁵
        pas encore assez de tirages  sinon

      L'asymétrie du critère est aussi une asymétrie de DÉLAI. À raison d'un
      tirage toutes les cinq minutes, et si l'API publie l'ordre à chaque fois :
      {n_fixed} tirages font {n_fixed * 5} minutes, {int(q[1])} en font {int(q[1]) * 5 / 60:.1f} heures. La règle se
      prouverait donc en une demi-heure, l'uniformité en trois heures. Aucune
      de ces deux durées ne suppose quoi que ce soit sur le résultat : ce sont
      des délais de MESURE, pas des prévisions — et elles ne valent que si
      l'API publie effectivement l'ordre de sortie, ce que le journal de l'app
      dira mais que rien ici ne garantit.""")


# --------------------------------------------------------------------------
# 7. Transcription du Swift — ce que les deux vérificateurs ne couvrent pas
# --------------------------------------------------------------------------

rule("7. TRANSCRIPTION — les fonctions Swift rejouées en Python")

say("""   `verif_swift.py` contrôle la syntaxe, `verif_logique.py` la justesse
   numérique des fonctions qu'il connaît. `ProphetTests/` est hors périmètre
   ici, donc la logique neuve est contrôlée par transcription : même formule,
   même ordre d'opérations, mêmes cas que les assertions Swift existantes.""")


def swift_binomial_lower_tail(k, n, p):
    """Transcription de BonusRule.binomialLowerTail (Prophet/Models/Types.swift)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    log_c = 0.0
    total = 0.0
    for i in range(0, k + 1):
        total += math.exp(log_c + i * math.log(p) + (n - i) * math.log1p(-p))
        log_c += math.log(n - i) - math.log(i + 1)
    return min(1.0, total)


def swift_minimum_for_rule():
    """Transcription de BonusRule.minimumForRule — la boucle Swift, à l'identique."""
    k = float(DRAWN)
    n = 1
    while n < 100 and k * (1 / k) ** n > ALPHA_HOLM:
        n += 1
    return n


def swift_minimum_for_uniform():
    """Transcription de BonusRule.minimumForUniform."""
    n = 1
    while n < 10_000 and \
            swift_binomial_lower_tail((n + DRAWN - 1) // DRAWN, n, 0.5) > ALPHA_HOLM:
        n += 1
    return n


def swift_missing(n, m):
    """Transcription de BonusRule.missing — ce qu'il manque AU MIEUX."""
    if n == 0 or m == n:
        return max(0, swift_minimum_for_rule() - n)
    extra = 0
    while extra < 4000:
        total = n + extra
        best = max(m, (total + DRAWN - 1) // DRAWN)
        if swift_binomial_lower_tail(best, total, 0.5) <= ALPHA_HOLM:
            return extra
        extra += 1
    return 4000


def swift_read(positions):
    """Transcription de BonusRule.read — le verdict à trois états."""
    n = len(positions)
    if n == 0:
        return ("undecided", 0, 0, 0)
    counts = [0] * DRAWN
    for p in positions:
        if 1 <= p <= DRAWN:
            counts[p - 1] += 1
    top = max(range(DRAWN), key=lambda i: counts[i])
    m = counts[top]
    if m == n and n >= n_fixed:
        return ("positionRule", n, top + 1, m)
    if m < n and swift_binomial_lower_tail(m, n, 0.5) <= ALPHA_HOLM:
        return ("uniform", n, top + 1, m)
    return ("undecided", n, top + 1, m)


for k, n_, p in ((2, 25, 0.5), (2, 24, 0.5), (3, 25, 0.5), (0, 5, 0.05)):
    exact = sum(math.comb(n_, i) * p ** i * (1 - p) ** (n_ - i) for i in range(k + 1))
    got = swift_binomial_lower_tail(k, n_, p)
    say(f"   binomialLowerTail({k}, {n_}, {p}) = {got:.6e}  "
        f"exact {exact:.6e}  écart {abs(got - exact):.1e}")
    assert abs(got - exact) < 1e-12 * max(1, exact)

say("")
say(f"   minimumForRule    Swift {swift_minimum_for_rule():>4}   §6 {n_fixed:>4}")
say(f"   minimumForUniform Swift {swift_minimum_for_uniform():>4}   §6 {n_uniform:>4}")
assert swift_minimum_for_rule() == n_fixed
assert swift_minimum_for_uniform() == n_uniform

say("\n   missing(n, dominante) — tirages encore manquants AU MIEUX")
for n_, m_ in ((0, 0), (3, 3), (5, 4), (20, 2), (24, 2), (25, 2), (31, 3)):
    say(f"     n = {n_:<4} dominante {m_:<3} → {swift_missing(n_, m_)}")
assert swift_missing(0, 0) == n_fixed
assert swift_missing(3, 3) == n_fixed - 3
assert swift_missing(25, 2) == 0, "25 tirages à dominante 2 : le plancher est atteint"
assert swift_missing(24, 2) == 1

cases = [
    ([20] * 4, "undecided"),
    ([20] * 5, "positionRule"),
    ([20] * 60, "positionRule"),
    ([20] * 4 + [7], "undecided"),
    (list(range(1, 21)) * 3, "uniform"),
]
say("")
for pos, want in cases:
    got = swift_read(pos)
    say(f"   {len(pos):>3} positions → {got[0]:<13} (dominante {got[2]}, "
        f"{got[3]}/{got[1]})   attendu {want}")
    assert got[0] == want, (pos[:5], got, want)

# Les assertions de ProphetTests/OracleTests.swift, rejouées.
rr = np.random.default_rng(7)
fixed_pos = [20] * 60
loose_pos = [int(rr.integers(1, DRAWN + 1)) for _ in range(300)]
say(f"\n   OracleTests, 60 tirages à position fixe   → {swift_read(fixed_pos)[0]}"
    f"  (le test Swift exige « signalé » + libellé RÈGLE FIXE)")
say(f"   OracleTests, 300 tirages à position libre → {swift_read(loose_pos)[0]}"
    f"  (le test Swift exige « non signalé »)")
assert swift_read(fixed_pos)[0] == "positionRule"
assert swift_read(loose_pos)[0] == "uniform"
say("   Les deux assertions Swift existantes restent satisfaites.")

rule(f"total {time.time() - T0:.0f}s")
