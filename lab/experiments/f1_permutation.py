"""f1 — le null par PERMUTATION : un changement de méthode, pas une 24e voie de plus.

Question. Les 23 voies temporelles du dossier (c1, c3, d2, d3, d7...) partagent
toutes une hypothèse jamais interrogée : leur null est simulé par `lab.srs()`,
c'est-à-dire un tirage SRS 20/80 supposé **parfaitement uniforme**. C'est une
hypothèse, pas une donnée. Si la loi réelle des 70 560 tirages s'écarte très
légèrement de l'uniforme — trop peu pour que le χ² marginal le voie — tout
test calibré contre le SRS hérite d'un null mal calibré.

Pour une hypothèse TEMPORELLE (l'ordre des tirages porte l'information), il
existe un null strictement meilleur : la PERMUTATION. Permuter l'ordre des
70 560 tirages réels détruit toute structure temporelle tout en préservant
EXACTEMENT la distribution empirique jointe des tirages, quelle qu'elle
soit. Un test calibré par permutation est valide sous la seule hypothèse
d'ÉCHANGEABILITÉ des tirages dans le temps — sans rien supposer de
l'uniformité. `lab.calibrate_perm()` (ajouté à lab.py) l'implémente : même
contrat que `lab.calibrate()`, mais `stat(archive)` reçoit une Archive dont
le contenu (mask/nums/bonus/boost) est permuté et dont `ts`/`ids` restent
fixes — ce qui permet aussi de tester une covariable dérivée de `ts`.

Ce que ce fichier fait, dans l'ordre :
  0. Sanity check — calibrate() vs calibrate_perm() sur une archive SRS
     PROPRE : les deux nulls doivent coïncider (aucune structure réelle à
     détruire). Valide l'implémentation avant de la pointer sur les vraies
     données.
  1. Le PIÈGE, démontré et pas seulement affirmé — une statistique purement
     MARGINALE (la loi du bonus sur 80 numéros, V1 de d7) est invariante par
     permutation de l'ordre des lignes : le null a un sd numériquement nul,
     le test est VIDE. La permutation ne couvre que les hypothèses d'ORDRE
     ou de covariable temporelle (rémanence, périodicité, dépendance
     sérielle du bonus) ; elle ne peut rien dire des marginales (§1 de
     l'audit, V1/V5 de d7), des triplets (d1), ou de toute statistique qui
     agrège les tirages sans égard à leur rang.
  2. RE-DÉRIVATION sous permutation des résultats temporels clés déjà établis
     sous SRS — même statistique, même archive réelle, null différent :
       T1   c1  recouvrement moyen lag-1                    (SRS z=+0,30)
       V3   d7  bonus_t dans le tirage t+1 — LE résidu       (SRS z=−2,58)
       S1   d3  forme de la loi du recouvrement (histogramme) (SRS z=+3,47)
       c3.heure_somme   somme conditionnée à l'heure locale  (SRS z proche de 0)
       c3.slot_ov1      recouvrement lag-1 conditionné au créneau du jour
     Pour chacune : les deux nulls coïncident-ils ? Si le sd sous permutation
     diffère de celui sous SRS, l'hypothèse d'uniformité biaisait le z du
     dossier — dans quel sens et de combien.
  3. PUISSANCE des deux nulls sur données contaminées, pour les deux familles
     les plus directement testées ici (rémanence diagonale pour T1, déficit
     de rémanence du bonus pour V3) : self-permutation par réplicat contre
     null SRS fixe, même seuil |z|>=3.

Usage : python3 f1_permutation.py [--dry]   (--dry : réplicats réduits,
n'écrit PAS au registre — mise au point uniquement)
"""
import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

DRY = "--dry" in sys.argv
POOL, DRAWN = lab.POOL, lab.DRAWN
ALPHA_Z = 3.0
R_SANITY = 60 if DRY else 150
R_MAIN = 60 if DRY else 150          # reps par null (SRS et perm), les 5 stats — réduit
                                     # de 200 à 150 pour tenir en quelques minutes, dit ici.
R_POWER = 5 if DRY else 12
R_POWER_NULL = 30 if DRY else 80     # reps de la self-permutation, PAR réplicat — réduit
                                     # de 100 à 80 pour la même raison.
R_POWER_SRS = 60 if DRY else 150     # null SRS fixe pour la puissance
N_POWER = 6_000 if DRY else 20_000   # réduit : la rémanence/bonus sont générés
                                     # SÉQUENTIELLEMENT (~20 us/tirage) — dit ici.

t_script = time.time()

# --------------------------------------------------------------------------
# 0. Chargement, covariables temporelles (identiques à c3_temporel.py)
# --------------------------------------------------------------------------

a = lab.load()
N = len(a)
assert N == 70_560

TZ = ZoneInfo("Europe/Zurich")
_loc = [datetime.datetime.fromtimestamp(int(t), TZ) for t in a.ts]
g_heure = np.array([dt.hour for dt in _loc]) - 6                 # 0..17
loc_sec = np.array([dt.hour * 3600 + dt.minute * 60 + dt.second for dt in _loc])
g_slot = (loc_sec - (6 * 3600 + 300)) // 300                     # 0..203
d_ts = np.diff(a.ts)
valid_pair = d_ts <= 600                                         # paire intra-session
gp_slot = g_slot[1:][valid_pair]                                 # groupe du tirage aval
W_SUM = np.arange(1, POOL + 1, dtype=np.float64)


def _between_ss(vals, g, G):
    cnt = np.bincount(g, minlength=G).astype(np.float64)
    s = np.bincount(g, weights=vals, minlength=G)
    m = vals.mean()
    nz = cnt > 0
    return float((cnt[nz] * (s[nz] / cnt[nz] - m) ** 2).sum())


# --------------------------------------------------------------------------
# 1. Les 5 statistiques — deux formes : stat_mask(mask) pour calibrate(),
#    stat_arch(archive) pour calibrate_perm() (même calcul, juste le contenant)
# --------------------------------------------------------------------------

def t1_mask(mask):
    """c1 — recouvrement moyen des paires consécutives."""
    return float((mask[1:] & mask[:-1]).sum() / (len(mask) - 1))


_PMF = lab.overlap_pmf()
_EXP_REAL = _PMF * (N - 1)
_LAST = int(np.max(np.flatnonzero(_EXP_REAL >= 5)))
_BINID = np.minimum(np.arange(DRAWN + 1), _LAST)
_EXPB_REAL = np.bincount(_BINID, weights=_EXP_REAL)


def s1_mask(mask):
    """d3 — χ² de l'histogramme complet du recouvrement lag-1 (forme, pas
    seulement la moyenne). Cases 0..11 + {>=12}, effectifs hypergéométriques
    exacts ; SEULE la distribution du χ² est simulée (les paires se
    chevauchent)."""
    ov = (mask[1:] & mask[:-1]).sum(1)
    n_pairs = len(mask) - 1
    exp = _EXPB_REAL * (n_pairs / (N - 1)) if n_pairs != N - 1 else _EXPB_REAL
    obs = np.bincount(_BINID[ov], minlength=_LAST + 1).astype(float)
    return float(((obs - exp) ** 2 / exp).sum())


def heure_somme_mask(mask):
    """c3 — somme des 20 numéros conditionnée à l'heure locale (18 groupes)."""
    sums = mask.astype(np.int32) @ W_SUM
    return _between_ss(sums, g_heure, 18)


def slot_ov1_mask(mask):
    """c3 — recouvrement lag-1 conditionné au créneau du jour (204 groupes),
    paires intra-session seulement."""
    ov = (mask[1:] & mask[:-1]).sum(1).astype(np.float64)
    return _between_ss(ov[valid_pair], gp_slot, 204)


def v3_bonus(mask, bonus):
    """d7 — bonus_t appartient-il au tirage t+1 ? (le résidu, z=-2,58 sous SRS)."""
    n = len(bonus)
    return float(mask[1:][np.arange(n - 1), bonus[:-1] - 1].mean())


def v1_bonus_marginal(bonus):
    """d7 — loi marginale du bonus sur 80 numéros : le PIÈGE, purement
    marginale, invariante par permutation de l'ordre des lignes."""
    c = np.bincount(bonus.astype(np.int64) - 1, minlength=POOL).astype(float)
    e = len(bonus) / POOL
    return float((((c - e) ** 2) / e).sum())


# Enveloppes pour calibrate_perm() : `stat(archive)` -> scalaire
STATS_ARCH = {
    "f1.c1_t1_perm": lambda arch: t1_mask(arch.mask),
    "f1.d3_s1_perm": lambda arch: s1_mask(arch.mask),
    "f1.c3_heure_somme_perm": lambda arch: heure_somme_mask(arch.mask),
    "f1.c3_slot_ov1_perm": lambda arch: slot_ov1_mask(arch.mask),
    "f1.d7_v3_perm": lambda arch: v3_bonus(arch.mask, arch.bonus.astype(np.int64)),
}
STATS_MASK = {
    "f1.c1_t1_perm": t1_mask,
    "f1.d3_s1_perm": s1_mask,
    "f1.c3_heure_somme_perm": heure_somme_mask,
    "f1.c3_slot_ov1_perm": slot_ov1_mask,
}   # f1.d7_v3_perm a besoin du bonus : null SRS géré à part (synth), cf. §3


def as_archive(mask, bonus=None, ids=None, ts=None):
    """Emballe un masque (n,80) [+ bonus] en Archive minimale, pour
    calibrate_perm() sur des données SYNTHÉTIQUES (sanity check, puissance)."""
    n = len(mask)
    nums = np.sort(np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1,
                   axis=1).astype(np.int8)
    return lab.Archive(
        ids if ids is not None else np.arange(n, dtype=np.int64),
        ts if ts is not None else np.arange(n, dtype=np.int64),
        nums, np.full(n, -1, np.int8),
        bonus.astype(np.int8) if bonus is not None else np.full(n, -1, np.int8),
        mask)


print("=" * 78)
print("F1 — NULL PAR PERMUTATION : les 23 voies temporelles tenaient-elles sous")
print("     une hypothèse plus faible que l'uniformité SRS ?")
print("=" * 78)
if DRY:
    print("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

rows0 = lab.ledger()
m_tests = len(rows0) + sum(int(r.get("m_extra", 0)) for r in rows0)
from scipy.stats import norm
z_crit = float(norm.isf(0.05 / m_tests / 2))
print(f"\nregistre : m = {m_tests} tests déjà dépensés -> seuil Holm p < "
      f"{0.05 / m_tests:.2e} (z >= {z_crit:.2f})")

# --------------------------------------------------------------------------
# 2. Sanity check — calibrate() vs calibrate_perm() sur une archive SRS PROPRE
#    (aucune structure temporelle à détruire : les deux nulls DOIVENT coïncider)
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n0. SANITY CHECK — les deux nulls coïncident-ils sur une archive SANS "
      f"structure ?\n   ({R_SANITY} réplicats)")
rng_s = np.random.default_rng(7)
clean_mask = lab.srs(N, rng_s)
clean_arch = as_archive(clean_mask)
t0 = time.time()
null_srs_clean = lab.calibrate(t1_mask, N, reps=R_SANITY, seed=70)
null_perm_clean = lab.calibrate_perm(lambda arc: t1_mask(arc.mask), clean_arch,
                                     reps=R_SANITY, seed=71)
print(f"  T1 sur archive SRS propre :")
print(f"    calibrate()      {null_srs_clean.mean:.6f} +/- {null_srs_clean.sd:.6f}")
print(f"    calibrate_perm() {null_perm_clean.mean:.6f} +/- {null_perm_clean.sd:.6f}"
      f"   ratio sd = {null_perm_clean.sd / null_srs_clean.sd:.3f}")
print(f"  -> implémentation validée : les deux nulls coïncident dans le bruit "
      f"d'estimation ({time.time() - t0:.0f}s).")
assert abs(null_perm_clean.mean - null_srs_clean.mean) < 5 * max(null_srs_clean.sd, 1e-9)

# --------------------------------------------------------------------------
# 3. Le PIÈGE, démontré — une statistique MARGINALE est invariante par
#    permutation de l'ordre : null dégénéré, test vide.
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n1. LE PIÈGE — une statistique marginale sous permutation (10 réplicats "
      f"suffisent)")
obs_v1 = v1_bonus_marginal(a.bonus.astype(np.int64))
null_v1_perm = lab.calibrate_perm(lambda arc: v1_bonus_marginal(arc.bonus.astype(np.int64)),
                                  a, reps=10, seed=12)
print(f"  V1 (loi marginale du bonus, d7) observé = {obs_v1:.6f}")
print(f"  null PAR PERMUTATION : {null_v1_perm.mean:.6f} +/- {null_v1_perm.sd:.2e} "
      f"(sur 10 réplicats)")
print(f"  -> sd numériquement NUL : la statistique ne dépend QUE du multi-ensemble des "
      f"tirages, pas de leur ordre.\n     Permuter les lignes ne change RIEN à un compte "
      f"marginal : le null est un point, pas une loi. z n'est pas interprétable.")
print(f"  Même chose, par construction, pour V5 (rang du bonus), pour d1_triplets.py "
      f"(comptes de triplets sur\n  l'archive entière) et pour tout χ² marginal du §1 de "
      f"l'audit : la permutation les préserve EXACTEMENT.")

# --------------------------------------------------------------------------
# 4. Pré-enregistrement — AVANT de regarder le résultat sous permutation
#    (le résultat SOUS SRS, lui, est déjà public : cf. RAPPORT.md §2)
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n2. PRÉ-ENREGISTREMENT (track A)")
DECISION = ("z et p du null PAR PERMUTATION (archive réelle, ordre des tirages "
            "shuffle) ; comparé au null SRS déjà consigné ; significatif si "
            "p_perm <= seuil Holm du registre entier ; le sd des deux nulls est "
            "comparé explicitement — un ratio != 1 quantifie le biais que "
            "l'hypothèse d'uniformité SRS introduisait dans le z déjà publié")
TESTS = [
    ("f1.c1_t1_perm",
     "Le recouvrement moyen lag-1 (c1, z=+0,30 sous SRS) est-il compatible avec "
     "l'échangeabilité SEULE (permutation), sans supposer l'uniformité SRS ?",
     "recouvrement moyen des 70 559 paires consécutives (T1 de c1, inchangée)",
     "permutation : calibrate_perm sur l'archive réelle, 70 560 tirages"),
    ("f1.d7_v3_perm",
     "LE résidu le plus cohérent du dossier — bonus_t dans le tirage t+1 "
     "(d7, z=-2,58 sous SRS) — survit-il, s'amplifie-t-il ou s'annule-t-il "
     "sous un null par permutation (échangeabilité seule) ?",
     "P(bonus_t dans mask_t+1) sur 70 559 paires (V3 de d7, inchangée)",
     "permutation : calibrate_perm sur l'archive réelle (mask ET bonus permutés "
     "ensemble, chaque tirage garde son propre bonus)"),
    ("f1.d3_s1_perm",
     "La forme de la loi du recouvrement (d3, S1, z=+3,47 sous SRS — le plus "
     "grand écart brut du dossier, classé fluctuation par d3b_chasse) "
     "change-t-elle de verdict sous un null par permutation ?",
     "χ² de l'histogramme complet de O(t,t+1), 13 cases (S1 de d3, inchangée)",
     "permutation : calibrate_perm sur l'archive réelle, 70 560 tirages"),
    ("f1.c3_heure_somme_perm",
     "La somme des 20 numéros conditionnée à l'heure locale (c3, 18 groupes) "
     "est-elle compatible avec l'échangeabilité seule ?",
     "B = somme_g n_g (moy_g - moy.)^2 de la somme, groupée par heure locale",
     "permutation : calibrate_perm sur l'archive réelle ; ts FIXE, contenu permuté "
     "— teste l'exchangeabilité des tirages à travers les créneaux horaires"),
    ("f1.c3_slot_ov1_perm",
     "Le recouvrement lag-1 conditionné au créneau du jour (c3, 204 groupes) "
     "est-il compatible avec l'échangeabilité seule ?",
     "B = somme_g n_g (moy_g - moy.)^2 du recouvrement lag-1 intra-session, "
     "groupé par créneau du jour",
     "permutation : calibrate_perm sur l'archive réelle ; ts FIXE, contenu permuté"),
]
tokens = {}
for tid, hyp, statd, nulld in TESTS:
    tok = lab.preregister(tid, hyp, statd, nulld, DECISION, track="A")
    tokens[tid] = tok
    print(f"  {tid:26s} seal={tok['seal']}")

# --------------------------------------------------------------------------
# 5. Re-dérivation — SRS (frais) vs PERMUTATION (archive réelle), les 5 stats
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n3. RE-DÉRIVATION — SRS frais vs PERMUTATION (archive réelle), "
      f"{R_MAIN} réplicats chacun")

# -- null SRS pour v3 (bonus) : reproduit exactement le null_method de d7 --
def synth_bonus(n, rng):
    mask = lab.srs(n, rng)
    nums = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
    pick = rng.integers(0, DRAWN, size=n)
    bonus = nums[np.arange(n), pick]
    return mask, bonus


def calibrate_v3_srs(n, reps, seed):
    """`n` DOIT correspondre à la taille des données testées : la re-dérivation
    §3 l'appelle à N=70560 (archive réelle), la puissance §4 à N_POWER — un
    null bâti à la mauvaise taille fausserait le sd et donc la comparaison."""
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for r in range(reps):
        mask, bonus = synth_bonus(n, rng)
        vals[r] = v3_bonus(mask, bonus)
    return lab.Null(float(vals.mean()), float(vals.std(ddof=1)), reps, vals)


obs = {
    "f1.c1_t1_perm": t1_mask(a.mask),
    "f1.d3_s1_perm": s1_mask(a.mask),
    "f1.c3_heure_somme_perm": heure_somme_mask(a.mask),
    "f1.c3_slot_ov1_perm": slot_ov1_mask(a.mask),
    "f1.d7_v3_perm": v3_bonus(a.mask, a.bonus.astype(np.int64)),
}

results = {}
row_fmt = "  {:<24}{:>13}{:>24}{:>24}{:>9}"
print(row_fmt.format("stat", "observé", "null SRS", "null PERM", "sd ratio"))
for tid, _, _, _ in TESTS:
    t0 = time.time()
    if tid == "f1.d7_v3_perm":
        null_srs = calibrate_v3_srs(N, R_MAIN, seed=900)
    else:
        null_srs = lab.calibrate(STATS_MASK[tid], N, reps=R_MAIN, seed=hash(tid) % 9973)
    null_perm = lab.calibrate_perm(STATS_ARCH[tid], a, reps=R_MAIN, seed=(hash(tid) + 1) % 9973)
    z_srs, p_srs = null_srs.z(obs[tid]), null_srs.p_two_sided(obs[tid])
    z_perm, p_perm = null_perm.z(obs[tid]), null_perm.p_two_sided(obs[tid])
    ratio = null_perm.sd / null_srs.sd
    results[tid] = dict(obs=obs[tid], null_srs=null_srs, null_perm=null_perm,
                        z_srs=z_srs, p_srs=p_srs, z_perm=z_perm, p_perm=p_perm, ratio=ratio)
    print(row_fmt.format(tid.replace("f1.", "").replace("_perm", ""),
                         f"{obs[tid]:.5g}",
                         f"{null_srs.mean:.5g}+/-{null_srs.sd:.3g}",
                         f"{null_perm.mean:.5g}+/-{null_perm.sd:.3g}",
                         f"{ratio:.3f}"))
    print(f"    z_SRS={z_srs:+.3f} (p={p_srs:.3g})   z_PERM={z_perm:+.3f} "
          f"(p={p_perm:.3g})   ({time.time() - t0:.0f}s)")

# --------------------------------------------------------------------------
# 6. Puissance — SRS null fixe vs PERMUTATION (self, par réplicat contaminé)
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n4. PUISSANCE — les deux nulls détectent-ils pareil ? "
      f"(N={N_POWER}, {R_POWER} réplicats/point,\n   self-permutation "
      f"{R_POWER_NULL} reps/réplicat, seuil |z|>={z_crit:.2f})")
print(f"   N réduit à {N_POWER} (contre 70 560) : la rémanence et le déficit de bonus "
      f"sont générés\n   SÉQUENTIELLEMENT (~20-25 us/tirage, pas vectorisable — dépendance "
      f"au tirage précédent).\n   Dit ici plutôt que caché : à N_POWER, les puissances "
      f"absolues ne sont pas directement\n   comparables à celles de c1/d7 (N=70 560, "
      f"sd plus petit) ; seule la comparaison SRS/PERM,\n   MÊME N, MÊME réplicats, "
      f"MÊME contamination, est visée ici.")


def gen_remanence(n, d, rng):
    """T1 : P(n au t) = 1/4+d si n était au t-1, 1/4-d/3 sinon (marginale
    figée à 1/4 exactement). Même famille que c1.gen_conditional(diag)."""
    lo = np.log(0.25 / 0.75)
    lo_hot = np.log((0.25 + d) / (0.75 - d)) - lo
    lo_cold = np.log((0.25 - d / 3) / (0.75 + d / 3)) - lo
    g = rng.gumbel(size=(n, POOL))
    out = np.zeros((n, POOL), bool)
    idx = np.argpartition(-g[0], DRAWN)[:DRAWN]
    out[0, idx] = True
    for t in range(1, n):
        keys = g[t].copy()
        keys[out[t - 1]] += lo_hot
        keys[~out[t - 1]] += lo_cold
        idx = np.argpartition(-keys, DRAWN)[:DRAWN]
        out[t, idx] = True
    return out


def gen_bonus_deficit(n, frac, rng):
    """V3 : force bonus_t hors de mask_t+1 sur une fraction `frac` des paires
    où il y aurait été présent — P(bonus_t in mask_t+1) : 0,25 -> 0,25*(1-frac)."""
    mask, bonus = synth_bonus(n, rng)
    hit = mask[1:][np.arange(n - 1), bonus[:-1] - 1]
    victims = np.flatnonzero(hit & (rng.random(n - 1) < frac))
    for t in victims:
        row = mask[t + 1]
        row[bonus[t] - 1] = False
        outs = np.flatnonzero(~row)
        row[rng.choice(outs)] = True
    return mask, bonus


def power_family(name, gen, grid, stat_mask_or_bonus, needs_bonus, seed0):
    """SRS null FIXE (calibrate, une fois) vs self-permutation PAR RÉPLICAT
    (calibrate_perm sur le réplicat contaminé lui-même — le vrai test de
    permutation : on shuffle exactement les données qu'on observe)."""
    rng_null = np.random.default_rng(seed0)
    if needs_bonus:
        null_fixed = calibrate_v3_srs(N_POWER, R_POWER_SRS, seed=seed0 + 1)
    else:
        null_fixed = lab.calibrate(stat_mask_or_bonus, N_POWER, reps=R_POWER_SRS, seed=seed0 + 1)
    print(f"\n  {name} : null SRS fixe = {null_fixed.mean:.5g} +/- {null_fixed.sd:.3g} "
          f"({R_POWER_SRS} reps)")
    print(f"  {'param':>8}{'pw SRS':>10}{'pw PERM':>10}{'z SRS moy':>12}{'z PERM moy':>12}")
    for i, p in enumerate(grid):
        rng = np.random.default_rng(seed0 + 100 + i)
        hit_srs = hit_perm = 0
        zs_srs, zs_perm = [], []
        for _ in range(R_POWER):
            if needs_bonus:
                mask, bonus = gen(N_POWER, p, rng)
                obs_v = stat_mask_or_bonus(mask, bonus)
                arch = as_archive(mask, bonus)
                null_perm_r = lab.calibrate_perm(
                    lambda arc: v3_bonus(arc.mask, arc.bonus.astype(np.int64)),
                    arch, reps=R_POWER_NULL, seed=int(rng.integers(1 << 31)))
            else:
                mask = gen(N_POWER, p, rng)
                obs_v = stat_mask_or_bonus(mask)
                arch = as_archive(mask)
                null_perm_r = lab.calibrate_perm(
                    lambda arc, f=stat_mask_or_bonus: f(arc.mask),
                    arch, reps=R_POWER_NULL, seed=int(rng.integers(1 << 31)))
            z_s, z_p = null_fixed.z(obs_v), null_perm_r.z(obs_v)
            zs_srs.append(z_s); zs_perm.append(z_p)
            hit_srs += abs(z_s) >= z_crit
            hit_perm += abs(z_p) >= z_crit
        print(f"  {p:>8.4g}{hit_srs / R_POWER:>10.0%}{hit_perm / R_POWER:>10.0%}"
              f"{np.mean(zs_srs):>+12.2f}{np.mean(zs_perm):>+12.2f}", flush=True)


t0 = time.time()
power_family("T1 rémanence diagonale (famille c1)", gen_remanence,
            (0.001, 0.002, 0.004, 0.008), t1_mask, False, seed0=2000)
power_family("V3 déficit de rémanence du bonus (famille d7)", gen_bonus_deficit,
            (0.02, 0.05, 0.1, 0.2), v3_bonus, True, seed0=3000)
print(f"\n  (puissance : {time.time() - t0:.0f}s)")

# --------------------------------------------------------------------------
# 7. Verdicts + registre
# --------------------------------------------------------------------------
print(f"\n{'-' * 78}\n5. VERDICTS")


def verdict_for(tid):
    r = results[tid]
    same_conclusion = (r["p_srs"] > 0.05 / m_tests) == (r["p_perm"] > 0.05 / m_tests)
    ratio_note = ("sd quasi identique" if 0.9 <= r["ratio"] <= 1.1 else
                 ("PERM plus dispersé (SRS anti-conservateur)" if r["ratio"] > 1.1 else
                  "PERM moins dispersé (SRS conservateur)"))
    return ("conforme sous les deux nulls" if same_conclusion else "DIVERGENCE — voir notes"), ratio_note


power_notes = {
    "f1.c1_t1_perm": "rémanence diagonale d in {0.001,0.002,0.004,0.008}, N=20000 : "
                    "cf. tableau puissance SRS vs self-permutation (§4 du script)",
    "f1.d7_v3_perm": "déficit bonus frac in {0.02,0.05,0.1,0.2}, N=20000 : "
                     "cf. tableau puissance SRS vs self-permutation (§4 du script)",
}

if not DRY:
    for tid, _, _, _ in TESTS:
        r = results[tid]
        verd, ratio_note = verdict_for(tid)
        lab.record(tokens[tid], observed=r["obs"], null=r["null_perm"],
                   power_at=power_notes.get(tid, "puissance déjà mesurée sous SRS "
                                                  "par c1/d3/c3 ; non re-mesurée sous "
                                                  "permutation ici (portée du script)"),
                   verdict=verd,
                   notes=(f"null SRS (frais, {R_MAIN} reps) {r['null_srs'].mean:.5g}+/-"
                          f"{r['null_srs'].sd:.3g} (z={r['z_srs']:+.3f}, p={r['p_srs']:.3g}) "
                          f"vs null PERMUTATION (archive réelle, {R_MAIN} reps) "
                          f"{r['null_perm'].mean:.5g}+/-{r['null_perm'].sd:.3g} "
                          f"(z={r['z_perm']:+.3f}, p={r['p_perm']:.3g}) ; "
                          f"ratio sd(perm)/sd(srs) = {r['ratio']:.3f} -> {ratio_note}."))
    print("\nconsigné au registre (5 entrées).")
else:
    print("\n[DRY] rien consigné.")

# --------------------------------------------------------------------------
# 8. Synthèse
# --------------------------------------------------------------------------
print(f"\n{'=' * 78}\nSYNTHÈSE")
print(f"  {'stat':<18}{'z SRS':>9}{'z PERM':>9}{'sd ratio':>10}   verdict")
for tid, _, _, _ in TESTS:
    r = results[tid]
    verd, _ = verdict_for(tid)
    print(f"  {tid.replace('f1.', '').replace('_perm', ''):<18}{r['z_srs']:>+9.2f}"
          f"{r['z_perm']:>+9.2f}{r['ratio']:>10.3f}   {verd}")
r3 = results["f1.d7_v3_perm"]
print(f"\nV3 (le résidu) : z_SRS = {r3['z_srs']:+.2f}  ->  z_PERM = {r3['z_perm']:+.2f} "
      f"(ratio sd = {r3['ratio']:.3f})")
print("\nCe que la permutation couvre : toute hypothèse d'ORDRE ou de covariable "
      "temporelle — rémanence/répulsion\nlag-k (T1/T2 de c1), forme de la loi du "
      "recouvrement (S1 de d3), dépendance sérielle du bonus (V2/V3/V4\nde d7), "
      "dépendance à une covariable dérivée de ts (c3 : heure, jour, créneau, minute).")
print("Ce qu'elle NE couvre PAS : toute hypothèse dont la statistique est invariante "
      "par permutation de l'ordre des\nlignes — les lois marginales (§1 de l'audit, "
      "V1/V5 de d7, c0), les comptes de triplets (d1), le boost non\nconditionné, "
      "et plus généralement tout agrégat qui ne regarde pas le RANG du tirage : "
      "démontré §1 (sd nul).")
print(f"\ntotal : {time.time() - t_script:.0f}s")
