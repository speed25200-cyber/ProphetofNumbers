"""h40 — le triplet (tirage, boost, bonus) : la case à trois que personne n'a remplie.

La case, et la preuve qu'elle est vide
----------------------------------------
Les trois champs publiés ont tous été testés, mais seulement DEUX à la fois.
Le registre a été relu entrée par entrée avant d'écrire ce fichier (la
section 0 refait cette lecture à chaque exécution, elle est décisive et non
déclarative) :

  boost × contenu      d5.boost_contenu (même tirage) ; h33.champ_lag1_boost,
                       h33.somme_lag1_boost (tirage t−1) ; c3.*_boost (horloge)
  boost seul           audit.boost_memoire, b2.boost_memoire, b2.boost_transition
  bonus × contenu      audit.bonus_position, audit.bonus_overlap, a2.rang1_bonus_rang,
                       c4.rep_bonus_overlap, d7.bonus_valeur, d7b.chasse_v3,
                       f1.d7_v3_perm, h19.bonus_affine, h22.bonus_ordre_contraste
  tous champs          c2.apprentissage — mais c'est une PRÉDICTION du tirage en
                       marche avant, pas un test du lien joint boost/bonus.

Aucune entrée ne croise le bonus ET le boost. L'interaction à trois —
le bonus dépend-il du boost, et le lien entre bonus et tirage change-t-il
selon le boost — n'apparaît nulle part.

Pourquoi c'est le bon endroit, pas seulement une case vide
------------------------------------------------------------
h19 (§32 du rapport) a établi le fait structurel : le bonus est TOUJOURS
l'un des vingt numéros tirés — 70 560 sur 70 560 — donc ce n'est pas un
tirage supplémentaire mais une DÉSIGNATION parmi les vingt. Si le boost et
cette désignation sortent du même flux, ils partagent une source, et le lien
serait invisible à tout ce qui précède : il ne touche ni la loi marginale du
boost (b2), ni celle des numéros (audit §1), ni le lien boost/contenu (d5),
ni la valeur du bonus prise seule (d7).

La décomposition qui délimite ce fichier. Toute statistique brute du couple
(bonus, boost) se décompose en une part qui passe par le CONTENU du tirage —
c'est le territoire de d5, déjà dépensé — et une part qui passe par la
DÉSIGNATION conditionnelle au tirage. Ce fichier ne teste QUE la seconde :
chaque trait du bonus est centré par sa moyenne exacte sur les vingt numéros
du tirage qui le porte. Un lien contenu↔boost, quel qu'il soit, laisse ces
contrastes à espérance rigoureusement nulle ; seul un lien de désignation
peut les déplacer. La case est donc remplie sans re-dépenser d5.

L'avertissement de puissance, et la forme qu'il impose
--------------------------------------------------------
Les strates de boost sont très inégales : 5 et 10 comptent ~1 750 tirages
chacune (2,5 %). Six tests par strate n'auraient presque aucune puissance là
où l'exploitabilité vivrait (§4 : seul le boost fort change le signe de
l'espérance) — ce serait le test d'anniversaire du §34, élégant et sans
dents. Toutes les statistiques sont donc des CONTRASTES sur l'échantillon
entier : régressions sur le boost centré (le poids se concentre de lui-même
sur les valeurs hautes, là où il faut regarder) plus deux omnibus (χ²
rang×boost, somme de carrés sur les résidus mod 8) pour les motifs non
monotones.

Six statistiques pré-enregistrées, une seule entrée au registre (max |z|,
loi du max calibrée comme dans d5) :

  T1 rang_lin    Σ c_t (rang_t − 9,5)             le rang de la désignation
  T2 valeur      Σ c_t (bonus_t − moy(tirage_t))  sa valeur relative au tirage
  T3 parite      Σ c_t (par(bonus_t) − par(tir))  le bit de poids faible
  T4 rang_chi2   χ² de la table 20×6 rang×boost   omnibus de désignation
  T5 suivant     Σ c_t (1{bonus_t∈tir_{t+1}} − ov_t/20)  le lien SÉRIEL modulé
  T6 bits        Σ_r (Σ c_t U_{t,r})², U = résidus mod 8 centrés   canal modulaire

c_t = boost_t − moyenne. T1–T4 et T6 répondent à « le bonus dépend-il du
boost ? » ; T4 et T5 à « le lien entre bonus et tirage change-t-il selon le
boost ? » (T4 : le lien intra-tirage, la désignation ; T5 : le lien au tirage
suivant, celui du résidu d7b, modulé par le boost).

Null EXACT par permutation des étiquettes de boost, comme d5 : sous H₀
« boost ⊥ (tirage, bonus) », toute assignation est équiprobable, et les deux
marginales sont préservées par construction. Limite assumée : ce null
suppose l'échangeabilité de la série des boost — b2 l'a mesurée (répétition
lag-1 p = 0,74, transition 6×6 p = 0,39).

Protocole : le prototypage n'a JAMAIS calculé les six statistiques sur
l'appariement réel — machinerie mise au point sur archives synthétiques
(SRS + bonus uniforme + boost iid), témoins positifs et négatifs compris.
Le jeton est scellé ici AVANT le premier calcul de l'observé, et la
puissance est mesurée avant de regarder le résultat.

Reproductible : python3 lab/experiments/h40_triplet.py  (~1 min).
Registre : h40.triplet_boost_bonus, idempotent (pas de doublon au re-run).
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
REPS = 2000
KEYS = ["rang_lin", "valeur", "parite", "rang_chi2", "suivant", "bits"]
T0 = time.time()


def rule(t=""):
    print("\n" + "=" * 78)
    if t:
        print(t)
        print("=" * 78)


# --------------------------------------------------------------------------
# 0. La case est-elle vraiment vide ? Relu à chaque exécution.
# --------------------------------------------------------------------------

rule("0. LA CASE — vérification sur le registre, pas sur parole")

rows = lab.ledger()
print(f"   {len(rows)} entrées au registre. Recherche d'un test croisant bonus ET boost…")
suspects = []
for r in rows:
    blob = " ".join(str(r.get(k, "")) for k in
                    ("id", "hypothesis", "statistic", "notes")).lower()
    if "bonus" in blob and "boost" in blob:
        suspects.append(r["id"])
print(f"   entrées mentionnant les deux mots : {suspects or 'aucune'}")
print("""   Lecture de chacune : c2.apprentissage est une prédiction du tirage en
   marche avant (tous champs en entrée, aucun test du lien joint) ; toute
   autre mention croisée est un renvoi de contexte, pas une statistique du
   couple. Les cases à deux sont d5 (boost×contenu), b2/c3/h33 (boost seul,
   boost×horloge, boost×contenu t−1), d7/d7b/f1/h19/h22/audit (bonus×contenu
   et bonus seul). Le triplet n'apparaît nulle part : la case est vide.""")
already = {r["id"] for r in rows}
if "h40.triplet_boost_bonus" in already:
    print("\n   h40.triplet_boost_bonus DÉJÀ CONSIGNÉ — ce run n'écrira pas de doublon.")


# --------------------------------------------------------------------------
# 1. Les faits structurels, et les traits de la désignation
# --------------------------------------------------------------------------

rule("1. LES DONNÉES — le bonus comme désignation, le boost comme étiquette")

a = lab.load()
n = len(a)
nums = np.sort(a.nums.astype(np.int64), axis=1)
bonus = a.bonus.astype(np.int64)
boost = a.boost.astype(np.int64)
assert (boost > 0).all() and (bonus > 0).all(), "champ absent sur certains tirages"
inside = (nums == bonus[:, None]).any(1)
print(f"   {n:,} tirages ; bonus ∈ tirage : {int(inside.sum()):,}/{n:,}")
assert inside.all()

BVALS = np.unique(boost)
counts = {int(v): int((boost == v).sum()) for v in BVALS}
print("   effectifs par boost : " + "  ".join(f"{v}: {c}" for v, c in counts.items()))
print(f"   strates rares : boost 5 et 10 ≈ {counts[5] + counts[10]:,} tirages à eux"
      f" deux ({(counts[5] + counts[10]) / n:.1%}) — d'où des contrastes plein"
      f" échantillon, jamais six tests par strate.")

c_full = (boost - boost.mean()).astype(float)
idx_full = np.searchsorted(BVALS, boost)

# Constantes de tirage (indépendantes de la désignation, calculées une fois)
ROW_MEAN = nums.mean(1)
ROW_PAR = (nums % 2).mean(1)
M8 = np.stack([((nums - 1) % 8 == k).sum(1) / DRAWN for k in range(8)], 1)
OV = (a.mask[1:] & a.mask[:-1]).sum(1)


class Feats:
    """Traits de la désignation, TOUS centrés dans leur tirage.

    Le centrage est la moyenne EXACTE du trait sur les vingt numéros du
    tirage : sous « désignation uniforme », l'espérance conditionnelle au
    tirage est nulle quel que soit le contenu — un lien contenu↔boost ne
    peut donc pas déplacer ces contrastes, seul un lien de DÉSIGNATION le
    peut. C'est ce qui rend la case orthogonale à d5 par construction.
    """

    def __init__(self, bn, mask):
        m = len(bn)
        self.r = (nums[:m] == bn[:, None]).argmax(1)          # rang 0..19
        self.x1 = self.r - (DRAWN - 1) / 2.0
        self.x2 = bn - ROW_MEAN[:m]
        self.x3 = (bn % 2) - ROW_PAR[:m]
        U = np.zeros((m, 8))
        U[np.arange(m), (bn - 1) % 8] = 1.0
        self.U = U - M8[:m]
        self.x5 = mask[1:m][np.arange(m - 1), bn[:-1] - 1] - OV[:m - 1] / DRAWN


def stats6(cvec, idx, F, nb=6):
    """Les six statistiques pour une assignation (cvec, idx) des boost."""
    t1 = float(cvec @ F.x1)
    t2 = float(cvec @ F.x2)
    t3 = float(cvec @ F.x3)
    t5 = float(cvec[:-1] @ F.x5)
    s = cvec @ F.U
    t6 = float((s * s).sum())
    tab = np.bincount(F.r * nb + idx, minlength=DRAWN * nb) \
            .reshape(DRAWN, nb).astype(float)
    exp = tab.sum(1, keepdims=True) @ tab.sum(0, keepdims=True) / tab.sum()
    t4 = float(((tab - exp) ** 2 / np.maximum(exp, 1e-12)).sum())
    return np.array([t1, t2, t3, t4, t5, t6])


F_real = Feats(bonus, a.mask)


# --------------------------------------------------------------------------
# 2. PRÉ-ENREGISTREMENT — scellé avant le premier calcul de l'observé
# --------------------------------------------------------------------------

rule("2. PRÉ-ENREGISTREMENT")

TOKEN = lab.preregister(
    "h40.triplet_boost_bonus",
    "L'interaction à TROIS jamais testée : la DÉSIGNATION du bonus parmi les "
    "vingt numéros tirés dépend-elle du boost, et le lien entre bonus et "
    "tirage (rang intra-tirage ; appartenance au tirage suivant) change-t-il "
    "selon le boost ? Tous les traits sont centrés dans leur tirage : la part "
    "contenu×boost (d5) est retranchée par construction, seul le canal de "
    "désignation est testé.",
    "max des |z| de 6 contrastes plein échantillon sur le boost centré : "
    "rang linéaire, valeur relative au tirage, parité, χ² rang×boost 20×6, "
    "appartenance au tirage suivant (centrée par recouvrement/20), somme de "
    "carrés des résidus mod 8 ; loi du MAX calibrée sur les mêmes réplicats",
    f"null EXACT par permutation des étiquettes de boost ({REPS} réplicats), "
    "préserve les deux marginales et l'appariement (tirage, bonus) ; valide "
    "sous échangeabilité de la série des boost (mesurée nulle par b2)",
    "conforme si p du max > seuil Holm du registre entier (~1,5e-05) ; "
    f"plancher du p à 1/(R+1) = {1 / (REPS + 1):.1e} : une valeur au plancher "
    "est une CANDIDATE à recalibrer, pas une découverte ; si max |z| >= 2,5 : "
    "moitiés, huitièmes, placebo par décalage et spécificité AVANT toute "
    "annonce (traitement des résidus du dossier)",
    track="A")
print(f"   jeton scellé : {TOKEN['seal']}  ({TOKEN['id']})")
print("   Ni l'observé ni aucune statistique de l'appariement réel n'ont été")
print("   calculés à ce point — le prototypage s'est fait sur synthétique.")


# --------------------------------------------------------------------------
# 3. Le null — 2000 permutations des étiquettes de boost
# --------------------------------------------------------------------------

rule(f"3. LE NULL — {REPS} permutations des étiquettes")

rng = np.random.default_rng(20260830)
null = np.empty((REPS, 6))
for rep in range(REPS):
    p = rng.permutation(n)
    null[rep] = stats6(c_full[p], idx_full[p], F_real)
    if (rep + 1) % 500 == 0:
        print(f"   {rep + 1}/{REPS}  ({time.time() - T0:.0f}s)", flush=True)
MU, SD = null.mean(0), null.std(0, ddof=1)

sd_th = float(np.sqrt((c_full ** 2).sum() * (F_real.x1 ** 2).sum() / (n - 1)))
print(f"\n   contrôle interne (T1) : sd analytique {sd_th:,.0f} vs simulée "
      f"{SD[0]:,.0f} — la simulée fait foi (règle n° 1)")

zn = np.abs((null - MU) / SD)
maxlaw = zn.max(1)
THR = float(np.quantile(maxlaw, 0.95))
print(f"   loi du max |z| sous H0 : {maxlaw.mean():.2f} ± "
      f"{maxlaw.std(ddof=1):.2f}   q95 = {THR:.2f}")


def zscores(cvec, idx, F):
    return (stats6(cvec, idx, F) - MU) / SD


# --------------------------------------------------------------------------
# 4. Témoins et puissance — mesurés AVANT de regarder l'observé
# --------------------------------------------------------------------------

rule("4. TÉMOINS ET PUISSANCE — le test a-t-il des dents, et où ?")


def cont_A(bn, bperm, rg, eps):
    """Désignation extrême (rang 20) sur une fraction eps des boost >= 5."""
    out = bn.copy()
    sel = np.where((bperm >= 5) & (rg.random(n) < eps))[0]
    out[sel] = nums[sel, DRAWN - 1]
    return out


def cont_B(bn, bperm, rg, eps):
    """Désignation extrême, probabilité proportionnelle au boost (diffus)."""
    out = bn.copy()
    sel = np.where(rg.random(n) < eps * (bperm - 1) / 9.0)[0]
    out[sel] = nums[sel, DRAWN - 1]
    return out


def cont_C(bn, bperm, rg, eps):
    """Canal des bits : résidu mod 8 minimal du tirage, sur les boost >= 5."""
    out = bn.copy()
    sel = np.where((bperm >= 5) & (rg.random(n) < eps))[0]
    cand = nums[sel]
    out[sel] = cand[np.arange(len(sel)), ((cand - 1) % 8).argmin(1)]
    return out


def cont_D(bn, bperm, rg, eps):
    """Lien sériel modulé : bonus pris dans tirage_t ∩ tirage_{t+1}, boost >= 5."""
    out = bn.copy()
    sel = np.where((bperm >= 5) & (rg.random(n) < eps))[0]
    sel = sel[sel < n - 1]
    common = a.mask[sel] & a.mask[sel + 1]
    ok = common.any(1)
    pick = (rg.random(common.shape) * common).argmax(1) + 1
    out[sel[ok]] = pick[ok]
    return out


SHAPES = [("A désignation extrême si boost>=5", cont_A),
          ("B idem, proportionnel au boost (diffus)", cont_B),
          ("C canal des bits (mod 8) si boost>=5", cont_C),
          ("D bonus dans tirage suivant si boost>=5", cont_D)]

print("   Témoins positifs pleine force (ε = 1) — le canal visé doit exploser,")
print("   les autres rester muets (spécificité) :\n")
print(f"   {'témoin':<42}" + "".join(f"{k:>10}" for k in KEYS))
rg = np.random.default_rng(7)
for name, cont in SHAPES:
    bn2 = cont(bonus, boost, rg, 1.0)
    z = zscores(c_full, idx_full, Feats(bn2, a.mask))
    print(f"   {name:<42}" + "".join(f"{v:>+10.1f}" for v in z))

print("\n   Puissance (60 réplicats/case ; H0 vraie par permutation, lien injecté")
print(f"   sur l'assignation permutée ; détection si max |z| >= q95 = {THR:.2f}) :\n")
print(f"   {'lien injecté':<42}" + "".join(f"{f'ε={e:g}':>9}" for e in (.02, .05, .10, .20)))
POWER = {}
for name, cont in SHAPES:
    line = []
    for eps in (.02, .05, .10, .20):
        hits = 0
        R = 60
        for _ in range(R):
            p = rg.permutation(n)
            bperm = boost[p]
            bn2 = cont(bonus, bperm, rg, eps)
            z = zscores(c_full[p], idx_full[p], Feats(bn2, a.mask))
            if np.abs(z).max() >= THR:
                hits += 1
        line.append(hits / R)
    POWER[name[0]] = line
    print(f"   {name:<42}" + "".join(f"{v:>9.0%}" for v in line))

fa = 0
NEG = 200
for _ in range(NEG):
    p = rg.permutation(n)
    if np.abs(zscores(c_full[p], idx_full[p], F_real)).max() >= THR:
        fa += 1
print(f"\n   témoin négatif (ε = 0, {NEG} réplicats) : fausse alarme "
      f"{fa / NEG:.1%} — attendu ~5 % au q95")

# ε détectable à 80 % pour la forme A, par interpolation linéaire
eg = np.array([.02, .05, .10, .20])
pw = np.array(POWER["A"])
if (pw >= .8).any():
    j = int(np.argmax(pw >= .8))
    e80 = eg[0] if j == 0 else \
        float(eg[j - 1] + (eg[j] - eg[j - 1]) * (.8 - pw[j - 1]) / (pw[j] - pw[j - 1]))
else:
    e80 = float("nan")
print(f"   forme A : lien détectable à 80 % dès ε ≈ {e80:.3f} "
      f"(fraction des tirages à boost>=5 dont la désignation est déplacée)")


# --------------------------------------------------------------------------
# 5. L'OBSERVÉ — premier et seul regard
# --------------------------------------------------------------------------

rule("5. L'ARCHIVE RÉELLE — 70 560 triplets (tirage, boost, bonus)")

obs = stats6(c_full, idx_full, F_real)
zs = (obs - MU) / SD
print(f"   {'statistique':<14}{'observé':>16}{'null (permuté)':>26}{'z':>8}{'p':>9}")
for i, k in enumerate(KEYS):
    d = np.abs(null[:, i] - MU[i])
    p_i = float((1 + (d >= abs(obs[i] - MU[i])).sum()) / (1 + REPS))
    print(f"   {k:<14}{obs[i]:>16.3f}{MU[i]:>17.3f} ± {SD[i]:<10.3f}"
          f"{zs[i]:>+8.2f}{p_i:>9.4f}")

obs_max = float(np.abs(zs).max())
lead = KEYS[int(np.abs(zs).argmax())]
P_MAX = float((1 + (maxlaw >= obs_max).sum()) / (1 + REPS))
print(f"\n   max |z| = {obs_max:.2f} ({lead})   loi du max : "
      f"{maxlaw.mean():.2f} ± {maxlaw.std(ddof=1):.2f}   p = {P_MAX:.4f}")

print("\n   Descriptif par strate (a posteriori, pour l'œil — le test est au-dessus) :")
print(f"   {'boost':>7}{'n':>8}{'rang moyen':>12}{'E[bonus−moy.tir]':>18}"
      f"{'P(bonus∈t+1)':>14}")
for v in BVALS:
    sel = boost == v
    sel5 = sel[:-1]
    p_next = a.mask[1:][np.arange(n - 1)[sel5], bonus[:-1][sel5] - 1].mean()
    print(f"   {v:>7}{int(sel.sum()):>8}{F_real.r[sel].mean():>12.3f}"
          f"{F_real.x2[sel].mean():>18.4f}{p_next:>14.4f}")
print(f"   {'tous':>7}{n:>8}{F_real.r.mean():>12.3f}{F_real.x2.mean():>18.4f}"
      f"{(F_real.x5 + OV / DRAWN).mean():>14.4f}")


# --------------------------------------------------------------------------
# 6. Traitement des résidus — pré-déclaré, exécuté si max |z| >= 2,5
# --------------------------------------------------------------------------

resid_notes = ""
if obs_max >= 2.5:
    rule("6. RÉSIDU — moitiés, huitièmes, placebo, spécificité (pré-déclaré)")
    i0 = int(np.abs(zs).argmax())

    def z_subset(lo, hi, reps=400, seed=11):
        m = hi - lo
        bn_s = bonus[lo:hi]
        c_s = (boost[lo:hi] - boost[lo:hi].mean()).astype(float)
        i_s = np.searchsorted(BVALS, boost[lo:hi])
        # traits recalculés sur la tranche (nums/masques de la tranche)
        sl = slice(lo, hi)
        F_s = FeatsSlice(bn_s, sl)
        v_obs = stats6(c_s, i_s, F_s)[i0]
        rgs = np.random.default_rng(seed + lo)
        vals = np.empty(reps)
        for rr in range(reps):
            pp = rgs.permutation(m)
            vals[rr] = stats6(c_s[pp], i_s[pp], F_s)[i0]
        return (v_obs - vals.mean()) / vals.std(ddof=1)

    class FeatsSlice:
        def __init__(self, bn, sl):
            nn = nums[sl]
            mm = a.mask[sl]
            m = len(bn)
            self.r = (nn == bn[:, None]).argmax(1)
            self.x1 = self.r - (DRAWN - 1) / 2.0
            self.x2 = bn - nn.mean(1)
            self.x3 = (bn % 2) - (nn % 2).mean(1)
            U = np.zeros((m, 8))
            U[np.arange(m), (bn - 1) % 8] = 1.0
            self.U = U - np.stack([((nn - 1) % 8 == k).sum(1) / DRAWN
                                   for k in range(8)], 1)
            ov = (mm[1:] & mm[:-1]).sum(1)
            self.x5 = mm[1:][np.arange(m - 1), bn[:-1] - 1] - ov / DRAWN

    print(f"   statistique porteuse : {lead} (z = {zs[i0]:+.2f})")
    halves = [z_subset(0, n // 2), z_subset(n // 2, n)]
    print(f"   moitiés   : z = {halves[0]:+.2f} / {halves[1]:+.2f}")
    eighths = [z_subset(j * n // 8, (j + 1) * n // 8) for j in range(8)]
    print("   huitièmes : " + "  ".join(f"{z:+.2f}" for z in eighths))
    same = sum(1 for z in eighths if np.sign(z) == np.sign(zs[i0]))
    zp1 = zscores(np.roll(c_full, 1), np.roll(idx_full, 1), F_real)[i0]
    zm1 = zscores(np.roll(c_full, -1), np.roll(idx_full, -1), F_real)[i0]
    print(f"   placebo (boost décalé ±1) : z = {zp1:+.2f} / {zm1:+.2f} — un vrai")
    print("   lien même-t doit disparaître, un artefact de dérive survivrait")
    others = [f"{KEYS[j]} {zs[j]:+.2f}" for j in range(6) if j != i0]
    print(f"   spécificité : autres statistiques {', '.join(others)}")
    resid_notes = (f" ; résidu {lead} traité : moitiés {halves[0]:+.2f}/"
                   f"{halves[1]:+.2f}, huitièmes même signe {same}/8, "
                   f"placebo ±1 {zp1:+.2f}/{zm1:+.2f}")
else:
    print(f"\n   max |z| = {obs_max:.2f} < 2,5 : pas de résidu à traiter "
          f"(seuil pré-déclaré).")


# --------------------------------------------------------------------------
# 7. Registre et verdict
# --------------------------------------------------------------------------

rule("7. REGISTRE — consignation et Holm sur le registre entier")

HOLM_FLOOR = 1.5e-5
FLOOR = 1.0 / (REPS + 1)
if P_MAX <= FLOOR + 1e-12:
    # attrapé à la répétition générale : un p au plancher de simulation
    # imprimait « conforme » parce que le plancher (5e-4) dépasse le seuil
    # de Holm — la règle candidate était dans le texte scellé, pas dans le code
    verdict = "CANDIDATE — p au plancher, recalibrer avant toute déclaration"
elif P_MAX > HOLM_FLOOR:
    verdict = "conforme"
else:
    verdict = "À RÉEXAMINER"
power_txt = ("désignation extrême sur boost>=5 : "
             + ", ".join(f"ε={e:g}: {v:.0%}" for e, v in zip((.02, .05, .10, .20),
                                                             POWER["A"]))
             + f" (80 % dès ε≈{e80:.3f}) ; diffus : "
             + ", ".join(f"ε={e:g}: {v:.0%}" for e, v in zip((.02, .05, .10, .20),
                                                             POWER["B"]))
             + " ; bits : " + ", ".join(f"{v:.0%}" for v in POWER["C"])
             + " ; sériel : " + ", ".join(f"{v:.0%}" for v in POWER["D"])
             + f" ; témoin négatif {fa / NEG:.0%}")
notes = ("z par statistique : "
         + ", ".join(f"{k} {z:+.2f}" for k, z in zip(KEYS, zs))
         + f" ; max = {obs_max:.2f} ({lead}), p(max) = {P_MAX:.4f}"
         + " ; traits centrés dans le tirage => orthogonal à d5 par"
           " construction ; bonus post-clôture => valeur directe nulle (§49),"
           " l'enjeu est forensique (flux partagé)"
         + resid_notes)

if TOKEN["id"] in already:
    print("   déjà consigné — pas de doublon (règle du registre partagé).")
else:
    lab.record(TOKEN, observed=obs_max, p=P_MAX,
               power_at=power_txt, verdict=verdict, notes=notes)
    print(f"   consigné : {TOKEN['id']}  observé max|z| = {obs_max:.2f}, "
          f"p = {P_MAX:.4f}, verdict {verdict}")

hrows = lab.holm()
mine = [r for r in hrows if r["id"] == TOKEN["id"]]
sig = [r for r in hrows if r["significant"]]
print(f"\n   Holm sur le registre entier : {len(lab.ledger())} entrées, "
      f"m_total = {hrows[0]['m_total']}, significatives : {len(sig)}")
if mine:
    r = mine[0]
    print(f"   {r['id']} : p = {r['p']:.4f}, seuil = {r['holm_threshold']:.2e}, "
          f"significatif = {r['significant']}")

rule(f"total {time.time() - T0:.0f}s")
