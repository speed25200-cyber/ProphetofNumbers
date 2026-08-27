"""a2_cold_start — signature de démarrage à froid aux 345 reprises de session.

Question. 345 ruptures de session (gap > 600 s ; 343 durent exactement
25 500 s, fenêtre de maintenance nocturne). L'audit §8 a attaqué ces
reprises par reconstruction de graine (56,3 M graines, 0 trouvée) — une
approche paramétrique. Ici : la question NON paramétrique. Un générateur
ré-amorcé au démarrage peut avoir une signature statistique de démarrage
à froid (état sous-mélangé, biais transitoire, graines d'horloge à faible
granularité) sans qu'aucune graine ne soit devinable. §15 testait des
fenêtres de 9 000 tirages — bien trop grossier pour voir 345 premiers
tirages noyés dedans.

Cohortes. rang r = le r-ième tirage après chaque reprise (r = 1..10),
n = 345 par rang. « prev » = le dernier tirage d'avant la coupure.

Huit tests pré-enregistrés, chacun avec null simulé (lab.calibrate, à la
taille de cohorte — jamais une espérance tabulée) et puissance mesurée :

  T1 rang1_chi2_champ           χ² d'uniformité des 80 numéros, rang 1
  T2 rang1_recouvrement_prec    recouvrement moyen (rang 1, prev)
  T3 rang1_recouvrement_mutuel  recouvrement moyen des 345 rang-1 entre eux
  T4 rang1_recouvrement_max     recouvrement MAX entre les 345 rang-1
                                (mode Corriveau : collision de graines)
  T5 rang1_bonus_rang           χ² du rang du bonus (20 cases), rang 1
  T6 rang1_boost_loi            χ² de la loi du boost vs loi empirique globale
  T7 rangs1_10_chi2_max         max sur r=1..10 du χ² de champ
                                (multiplicité interne au null simulé)
  T8 rangs1_10_recouv_prec_max  max sur r=1..10 de |recouv moyen(r, prev) − 5|

Contrôles analytiques (jamais utilisés comme null, seulement pour vérifier
que le null simulé tombe dessus) : E[χ²_champ] = 60 exactement (pas 79 —
la somme de ligne est fixée à 20, cf. §1 de l'audit), E[recouvrement] = 5,
E[χ²_bonus] = 19, E[χ²_boost] = 5.

Usage :
    python3 a2_cold_start.py --dry    # machinerie sur données synthétiques,
                                      # AUCUNE écriture au registre, aucune
                                      # statistique observée sur l'archive
    python3 a2_cold_start.py          # run réel : pré-enregistre, calibre,
                                      # mesure la puissance, observe, consigne
"""

from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab

DRY = "--dry" in sys.argv
POOL, DRAWN = lab.POOL, lab.DRAWN
N_RANKS = 10
ALPHA_Z = 3.0

# --------------------------------------------------------------------------
# 1. Structure : identifier les reprises, vérifier avant de conclure
# --------------------------------------------------------------------------

a = lab.load()
d = np.diff(a.ts)
res = np.where(d > 600)[0] + 1          # index du 1er tirage après reprise
gaps = d[res - 1]

print("=" * 72)
print("STRUCTURE DES REPRISES")
print("=" * 72)
print(f"tirages: {len(a)}   reprises (gap>600s): {len(res)}")
print(f"gaps: min {gaps.min()}  médian {int(np.median(gaps))}  max {gaps.max()}"
      f"   (== 25500 s : {(gaps == 25500).sum()})")
sess_len = np.diff(np.concatenate([[0], res, [len(a)]]))
print(f"sessions: {len(sess_len)}  longueur min/med/max: "
      f"{sess_len.min()}/{int(np.median(sess_len))}/{sess_len.max()}")
assert len(res) == 345, f"attendu 345 reprises, trouvé {len(res)}"
assert (gaps == 25500).sum() == 343
for j in range(1, N_RANKS):
    assert (d[res - 1 + j] <= 600).all(), f"rang {j+1} croise une coupure"
assert res.max() + N_RANKS - 1 <= len(a) - 1
assert (a.bonus >= 1).all() and (a.boost >= 1).all()
NS = len(res)                            # 345
print(f"rangs 1..{N_RANKS} : aucun ne croise de coupure ; cohortes n={NS}")

BOOST_CATS = np.array(sorted(np.unique(a.boost)))          # [1,2,3,4,5,10]
P_BOOST = np.array([(a.boost == c).mean() for c in BOOST_CATS])
print(f"loi empirique globale du boost {BOOST_CATS.tolist()}: "
      f"{np.round(P_BOOST, 4).tolist()}")

# --------------------------------------------------------------------------
# 2. Statistiques — stat(mask) -> scalaire, calibrables par lab.calibrate
# --------------------------------------------------------------------------

def chi2_field(mask: np.ndarray) -> float:
    """χ² d'uniformité des 80 numéros (E ≠ 79 : somme de ligne fixée)."""
    n = len(mask)
    exp = n * DRAWN / POOL
    c = mask.sum(0)
    return float(((c - exp) ** 2 / exp).sum())


def mean_overlap_pairs(mask: np.ndarray) -> float:
    """Lignes en paires (2i, 2i+1) : recouvrement moyen des paires."""
    return float((mask[0::2] & mask[1::2]).sum(1).mean())


def _gram(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.int16)
    return m @ m.T


def mutual_mean(mask: np.ndarray) -> float:
    g = _gram(mask)
    iu = np.triu_indices(len(mask), k=1)
    return float(g[iu].mean())


def mutual_max(mask: np.ndarray) -> float:
    g = _gram(mask)
    np.fill_diagonal(g, -1)
    return float(g.max())


def _mask_rng(mask: np.ndarray) -> np.random.Generator:
    """RNG déterministe dérivé du masque : rend stat(mask) reproductible."""
    seed = int.from_bytes(hashlib.sha256(mask.tobytes()).digest()[:8], "little")
    return np.random.default_rng(seed)


def chi2_of_ranks(ranks: np.ndarray) -> float:
    n = len(ranks)
    c = np.bincount(ranks, minlength=DRAWN)
    exp = n / DRAWN
    return float(((c - exp) ** 2 / exp).sum())


def bonus_rank_chi2(mask: np.ndarray) -> float:
    """H0 : le bonus désigne uniformément l'un des 20 numéros tirés (§14).
    Le masque ne porte pas le bonus : le null tire le rang uniformément,
    via un RNG dérivé du masque (déterministe, indépendant du contenu)."""
    rng = _mask_rng(mask)
    return chi2_of_ranks(rng.integers(0, DRAWN, len(mask)))


def chi2_of_boost(vals: np.ndarray, n: int) -> float:
    c = np.array([(vals == k).sum() for k in BOOST_CATS])
    exp = n * P_BOOST
    return float(((c - exp) ** 2 / exp).sum())


def boost_chi2(mask: np.ndarray) -> float:
    """H0 : boost iid selon sa loi empirique globale, indépendant des reprises."""
    rng = _mask_rng(mask)
    n = len(mask)
    vals = rng.choice(BOOST_CATS, size=n, p=P_BOOST)
    return chi2_of_boost(vals, n)


def ranks_chi2_max(mask: np.ndarray) -> float:
    """Lignes rang-majeur : bloc r = lignes [r*NS, (r+1)*NS). Max des χ²."""
    return max(chi2_field(mask[r * NS:(r + 1) * NS]) for r in range(N_RANKS))


def ranks_ovl_prev_maxdev(mask: np.ndarray) -> float:
    """Lignes session-majeur, 11 par session : [prev, rang1..rang10].
    Max sur r de |recouvrement moyen(rang r, prev) − 5|. Le 5 centre la
    statistique ; le null reste entièrement simulé."""
    v = mask.reshape(NS, N_RANKS + 1, POOL)
    prev = v[:, 0]
    devs = [abs(float((prev & v[:, r]).sum(1).mean()) - 5.0)
            for r in range(1, N_RANKS + 1)]
    return max(devs)


# --------------------------------------------------------------------------
# 3. Contaminations — le défaut de démarrage à froid qu'on prétend voir
# --------------------------------------------------------------------------

def redraw_from_pool(n: int, pool_idx: np.ndarray, rng) -> np.ndarray:
    out = np.zeros((n, POOL), bool)
    for i in range(n):
        out[i, rng.choice(pool_idx, DRAWN, replace=False)] = True
    return out


def contaminate_pool(pool_size: int, rows=slice(None)):
    """Les lignes visées tirent leurs 20 numéros dans un pool réduit."""
    def f(mask, rng):
        pool_idx = rng.choice(POOL, pool_size, replace=False)
        sub = mask[rows]
        mask[rows] = redraw_from_pool(len(sub), pool_idx, rng)
        return mask
    return f


def force_overlap_pairs(o: int, frac: float, stride: int = 2, off: int = 1):
    """Paires (i*stride, i*stride+off) : la 2e ligne partage exactement o
    numéros avec la 1re, sur une fraction frac des paires. ΔE = frac*(o-5)."""
    def f(mask, rng):
        npairs = len(mask) // stride
        for i in range(npairs):
            if rng.random() >= frac:
                continue
            first = mask[i * stride]
            inb = np.where(first)[0]
            outb = np.where(~first)[0]
            row = np.zeros(POOL, bool)
            row[rng.choice(inb, o, replace=False)] = True
            row[rng.choice(outb, DRAWN - o, replace=False)] = True
            mask[i * stride + off] = row
        return mask
    return f


def collide_two(share: int):
    """Deux sessions partagent `share` numéros au rang 1 (collision de
    graine : share=20 -> tirages identiques)."""
    def f(mask, rng):
        i, j = rng.choice(len(mask), 2, replace=False)
        src = mask[i]
        inb = np.where(src)[0]
        outb = np.where(~src)[0]
        row = np.zeros(POOL, bool)
        row[rng.choice(inb, share, replace=False)] = True
        row[rng.choice(outb, DRAWN - share, replace=False)] = True
        mask[j] = row
        return mask
    return f


def force_overlap_rank1_in_sessions(o: int, frac: float):
    """Layout session-majeur (11 lignes/session) : force le recouvrement
    du rang 1 avec prev, comme force_overlap_pairs."""
    return force_overlap_pairs(o, frac, stride=N_RANKS + 1, off=1)


def custom_power(simulate, null: lab.Null, reps: int = 200, seed: int = 1,
                 alpha_z: float = ALPHA_Z) -> float:
    """Même contrat que lab.power, pour les stats dont la contamination ne
    passe pas par le masque (bonus, boost) : simulate(rng) -> valeur
    contaminée de la statistique."""
    rng = np.random.default_rng(seed)
    return sum(abs(null.z(simulate(rng))) >= alpha_z for _ in range(reps)) / reps


def sim_bonus_biased(eps: float):
    """Défaut : à la reprise, le bonus désigne la plus petite boule (rang 0)
    avec probabilité eps, uniforme sinon."""
    def f(rng):
        ranks = rng.integers(0, DRAWN, NS)
        ranks[rng.random(NS) < eps] = 0
        return chi2_of_ranks(ranks)
    return f


def sim_boost_stuck(eps: float):
    """Défaut : à la reprise, le boost retombe à 1 avec probabilité eps."""
    def f(rng):
        vals = rng.choice(BOOST_CATS, size=NS, p=P_BOOST)
        vals[rng.random(NS) < eps] = 1
        return chi2_of_boost(vals, NS)
    return f


# --------------------------------------------------------------------------
# 4. Pré-enregistrement — AVANT tout calcul d'observé
# --------------------------------------------------------------------------

DECISION = ("z du null simulé ; drapeau si |z| >= 3 ; significatif seulement "
            "si p <= seuil Holm du registre entier (~1.55e-05)")
NM_CAL = "lab.calibrate, SRS 20/80, a la taille de cohorte"

TESTS = [
    ("a2.rang1_chi2_champ",
     "Le 1er tirage apres reprise a un champ non uniforme (etat sous-melange)",
     "chi2 des 80 numeros sur la cohorte rang 1, n=345",
     f"{NM_CAL} (n_draws=345)"),
    ("a2.rang1_recouvrement_prec",
     "Etat non reinitialise a la reprise : recouvrement (rang 1, dernier "
     "tirage avant coupure) au-dessus de 5",
     "recouvrement moyen sur 345 paires (prev, rang 1)",
     f"{NM_CAL} (n_draws=690, paires SRS independantes)"),
    ("a2.rang1_recouvrement_mutuel",
     "Amorcage sur horloge a faible granularite : les 345 premiers tirages "
     "se ressemblent entre eux (mode Corriveau)",
     "recouvrement moyen des 59340 paires parmi les 345 tirages rang 1",
     f"{NM_CAL} (n_draws=345)"),
    ("a2.rang1_recouvrement_max",
     "Collision de graines entre deux reprises : une paire de premiers "
     "tirages quasi identiques",
     "recouvrement maximal parmi les 59340 paires des 345 tirages rang 1",
     f"{NM_CAL} (n_draws=345)"),
    ("a2.rang1_bonus_rang",
     "Le rang du bonus au 1er tirage apres reprise n'est pas uniforme sur "
     "les 20 numeros tires",
     "chi2 a 20 cases du rang du bonus, cohorte rang 1, n=345",
     "lab.calibrate ; null: rang uniforme 0..19 simule (RNG derive du masque)"),
    ("a2.rang1_boost_loi",
     "La loi du boost au 1er tirage apres reprise differe de la loi "
     "empirique globale",
     "chi2 a 6 categories du boost, cohorte rang 1, n=345, vs loi globale",
     "lab.calibrate ; null: boost iid loi empirique simule (RNG derive du masque)"),
    ("a2.rangs1_10_chi2_max",
     "Un defaut de champ transitoire sur l'un des 10 premiers tirages "
     "apres reprise",
     "max sur r=1..10 du chi2 des 80 numeros par cohorte de rang, n=3450",
     f"{NM_CAL} (n_draws=3450, max simule => multiplicite interne)"),
    ("a2.rangs1_10_recouv_prec_max",
     "Une remanence transitoire de l'etat d'avant coupure sur l'un des 10 "
     "premiers tirages",
     "max sur r=1..10 de |recouvrement moyen(rang r, prev) - 5|, n=3795",
     f"{NM_CAL} (n_draws=3795, max simule => multiplicite interne)"),
]

print()
print("=" * 72)
print("PRE-ENREGISTREMENT" + ("  [DRY: jetons calcules, rien ne sera consigne]" if DRY else ""))
print("=" * 72)
tokens = {}
for tid, hyp, statd, nulld in TESTS:
    tok = lab.preregister(tid, hyp, statd, nulld, DECISION, track="A")
    tokens[tid] = tok
    print(f"  {tid:34s} seal={tok['seal']}")

# --------------------------------------------------------------------------
# 5. Nulls simulés + contrôles analytiques
# --------------------------------------------------------------------------

print()
print("=" * 72)
print("CALIBRATION DES NULLS (simulation SRS)")
print("=" * 72)

REPS_SMALL, REPS_BIG = 4000, 2000
SPEC = {
    "a2.rang1_chi2_champ":          (chi2_field,            NS,               REPS_SMALL, 60.0),
    "a2.rang1_recouvrement_prec":   (mean_overlap_pairs,    2 * NS,           REPS_SMALL, 5.0),
    "a2.rang1_recouvrement_mutuel": (mutual_mean,           NS,               REPS_SMALL, 5.0),
    "a2.rang1_recouvrement_max":    (mutual_max,            NS,               REPS_SMALL, None),
    "a2.rang1_bonus_rang":          (bonus_rank_chi2,       NS,               REPS_SMALL, 19.0),
    "a2.rang1_boost_loi":           (boost_chi2,            NS,               REPS_SMALL, 5.0),
    "a2.rangs1_10_chi2_max":        (ranks_chi2_max,        N_RANKS * NS,     REPS_BIG,   None),
    "a2.rangs1_10_recouv_prec_max": (ranks_ovl_prev_maxdev, (N_RANKS + 1) * NS, REPS_BIG, None),
}

nulls = {}
for tid, (stat, nd, reps, analytic) in SPEC.items():
    nulls[tid] = lab.calibrate(stat, nd, reps=reps, seed=hash(tid) % 2**31)
    nl = nulls[tid]
    ctrl = f"  [controle analytique E={analytic:.2f}]" if analytic is not None else ""
    print(f"  {tid:34s} null = {nl.mean:8.4f} +/- {nl.sd:7.4f}  (reps={reps}){ctrl}")

# --------------------------------------------------------------------------
# 6. Puissance mesurée
# --------------------------------------------------------------------------

print()
print("=" * 72)
print("PUISSANCE (fraction des replicats contamines detectes, |z|>=3)")
print("=" * 72)

POWER_PLAN = {
    "a2.rang1_chi2_champ": [
        ("pool 70/80", contaminate_pool(70), 200),
        ("pool 60/80", contaminate_pool(60), 200),
        ("pool 40/80", contaminate_pool(40), 200),
    ],
    "a2.rang1_recouvrement_prec": [
        ("E[ovl]=5.25 (o=6, f=.25)", force_overlap_pairs(6, 0.25), 200),
        ("E[ovl]=5.50 (o=6, f=.50)", force_overlap_pairs(6, 0.50), 200),
        ("E[ovl]=6.00 (o=6, f=1)",   force_overlap_pairs(6, 1.0),  200),
        ("E[ovl]=8.00 (o=8, f=1)",   force_overlap_pairs(8, 1.0),  200),
    ],
    "a2.rang1_recouvrement_mutuel": [
        ("pool commun 76 (E=5.26)", contaminate_pool(76), 200),
        ("pool commun 72 (E=5.56)", contaminate_pool(72), 200),
        ("pool commun 60 (E=6.67)", contaminate_pool(60), 200),
        ("pool commun 40 (E=10.0)", contaminate_pool(40), 100),
    ],
    "a2.rang1_recouvrement_max": [
        ("1 paire partage 15/20", collide_two(15), 200),
        ("1 collision totale (20/20)", collide_two(20), 200),
    ],
    "a2.rangs1_10_chi2_max": [
        ("rang 1 seul: pool 60", contaminate_pool(60, rows=slice(0, NS)), 100),
        ("rang 1 seul: pool 40", contaminate_pool(40, rows=slice(0, NS)), 100),
    ],
    "a2.rangs1_10_recouv_prec_max": [
        ("rang 1 seul: E[ovl]=5.5", force_overlap_rank1_in_sessions(6, 0.5), 100),
        ("rang 1 seul: E[ovl]=6.0", force_overlap_rank1_in_sessions(6, 1.0), 100),
    ],
}

power_notes = {}
for tid, plan in POWER_PLAN.items():
    stat, nd, _, _ = SPEC[tid]
    parts = []
    for label, cont, reps in plan:
        pw = lab.power(stat, cont, nd, nulls[tid], reps=reps, alpha_z=ALPHA_Z)
        parts.append(f"{label}: {pw:.2f}")
        print(f"  {tid:34s} {label:28s} puissance = {pw:.2f}")
    power_notes[tid] = " | ".join(parts)

for tid, plan in {
    "a2.rang1_bonus_rang": [("bonus->rang min, eps=.05", sim_bonus_biased(0.05), 400),
                            ("bonus->rang min, eps=.10", sim_bonus_biased(0.10), 400)],
    "a2.rang1_boost_loi":  [("boost->1, eps=.10", sim_boost_stuck(0.10), 400),
                            ("boost->1, eps=.20", sim_boost_stuck(0.20), 400)],
}.items():
    parts = []
    for label, sim, reps in plan:
        pw = custom_power(sim, nulls[tid], reps=reps)
        parts.append(f"{label}: {pw:.2f}")
        print(f"  {tid:34s} {label:28s} puissance = {pw:.2f}")
    power_notes[tid] = " | ".join(parts) + " (boucle maison, meme contrat que lab.power)"

# --------------------------------------------------------------------------
# 7. Observés — construits SEULEMENT maintenant
# --------------------------------------------------------------------------

print()
print("=" * 72)
print("OBSERVES" + ("  [DRY : cohortes remplacees par du SRS synthetique]" if DRY else ""))
print("=" * 72)

if DRY:
    _rng = np.random.default_rng(987654321)
    rank_masks = [lab.srs(NS, _rng) for _ in range(N_RANKS)]
    prev_mask = lab.srs(NS, _rng)
    obs_bonus_ranks = _rng.integers(0, DRAWN, NS)
    obs_boost = _rng.choice(BOOST_CATS, size=NS, p=P_BOOST)
else:
    rank_masks = [a.mask[res + r] for r in range(N_RANKS)]
    prev_mask = a.mask[res - 1]
    obs_bonus_ranks = (a.nums[res] == a.bonus[res, None]).argmax(1)
    obs_boost = a.boost[res]
    assert ((a.nums[res] == a.bonus[res, None]).sum(1) == 1).all()

paired = np.empty((2 * NS, POOL), bool)          # layout de T2
paired[0::2], paired[1::2] = prev_mask, rank_masks[0]
sess_major = np.empty((NS, N_RANKS + 1, POOL), bool)   # layout de T8
sess_major[:, 0] = prev_mask
for r in range(N_RANKS):
    sess_major[:, r + 1] = rank_masks[r]

observed = {
    "a2.rang1_chi2_champ":          chi2_field(rank_masks[0]),
    "a2.rang1_recouvrement_prec":   mean_overlap_pairs(paired),
    "a2.rang1_recouvrement_mutuel": mutual_mean(rank_masks[0]),
    "a2.rang1_recouvrement_max":    mutual_max(rank_masks[0]),
    "a2.rang1_bonus_rang":          chi2_of_ranks(obs_bonus_ranks),
    "a2.rang1_boost_loi":           chi2_of_boost(obs_boost, NS),
    "a2.rangs1_10_chi2_max":        ranks_chi2_max(np.concatenate(rank_masks)),
    "a2.rangs1_10_recouv_prec_max": ranks_ovl_prev_maxdev(
        sess_major.reshape(-1, POOL)),
}

# Table descriptive par rang (non enregistree : contexte du rapport)
print()
print(f"  {'rang':>4s} {'chi2(80)':>10s} {'ovl(prev)':>10s} {'ovl mutuel':>10s}")
for r in range(N_RANKS):
    ovl_prev = float((prev_mask & rank_masks[r]).sum(1).mean())
    print(f"  {r+1:>4d} {chi2_field(rank_masks[r]):>10.2f} "
          f"{ovl_prev:>10.4f} {mutual_mean(rank_masks[r]):>10.4f}")

# --------------------------------------------------------------------------
# 8. Verdicts + registre
# --------------------------------------------------------------------------

print()
print("=" * 72)
print("RESULTATS")
print("=" * 72)
print(f"  {'test':34s} {'observe':>10s} {'null':>18s} {'z':>7s} {'p':>9s}")
rows = []
for tid, _, _, _ in TESTS:
    nl = nulls[tid]
    obs = observed[tid]
    z, p = nl.z(obs), nl.p_two_sided(obs)
    flag = "  <-- |z|>=3 : chercher d'abord l'artefact" if abs(z) >= ALPHA_Z else ""
    print(f"  {tid:34s} {obs:>10.4f} {nl.mean:>9.4f}+/-{nl.sd:<7.4f} "
          f"{z:>+7.2f} {p:>9.2e}{flag}")
    rows.append((tid, obs, z, p))
    if not DRY:
        verdict = "conforme" if abs(z) < ALPHA_Z else "drapeau |z|>=3 — voir notes"
        lab.record(tokens[tid], obs, null=nl,
                   power_at=power_notes.get(tid, ""),
                   verdict=verdict,
                   notes=("cohortes: 345 reprises (gap>600s), rangs 1..10; "
                          "controles analytiques imprimes par le script"))

if DRY:
    print("\n[DRY] Rien n'a ete consigne au registre.")
else:
    sig = [r for r in lab.holm() if r["significant"]]
    print(f"\nHolm sur registre entier: {len(sig)} test(s) significatif(s)"
          f" (m_total={lab.holm()[0]['m_total'] if lab.holm() else 0}).")
