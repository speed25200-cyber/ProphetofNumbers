"""c4_meta — méta-analyse du registre entier, et réplication des trois
signaux les plus forts jamais observés.

Question. Le registre compte ~3 250 tests dépensés, tous « conformes »
isolément, et `lab.holm()` rend 0 significatif. Mais Holm répond à « UN
de ces tests est-il significatif ? ». Une source légèrement défaillante
ne produirait pas un test franc : elle produirait un léger excès diffus,
réparti sur beaucoup de tests, dont aucun ne franchit son seuil. Sous H₀,
les p-values de tests indépendants sont uniformes sur [0,1] — prédiction
forte, testable sur l'ensemble du registre, et invisible par construction
à toute correction de multiplicité.

Le piège central, assumé partout ici : les p du registre ne sont NI
indépendantes NI toutes uniformes sous H₀ telles qu'enregistrées.
Combiner naïvement avec une table fabrique des découvertes. D'où :

  1. SÉLECTION d'un sous-ensemble défendable (règles ci-dessous, doublons
     et statistiques redondantes écartés, extrêmes de famille transformés
     en p familiales) ;
  2. NULL SIMULÉ en rejouant la structure du registre : marges fidèles
     (arrondis de l'audit, grilles discrètes de Davison-Hinkley aux
     null_reps consignés, transformations de famille), et DEUX bras de
     dépendance :
       - bras IND : indépendance totale — le null le plus étroit, donc le
         PLUS DÉFAVORABLE à un verdict « conforme » ; si même lui ne rend
         rien, la dépendance ne peut qu'affaiblir davantage le signal ;
       - bras DEP : joints exacts simulés là où c'est possible (triple a2,
         monobit+cusum par marche aléatoire, BM agrégé+fenêtres par
         multinomiales), bornes comonotones là où ça ne l'est pas — le
         null le plus large défendable.
     Un résultat n'est cru que s'il tient dans les deux bras.
  3. PUISSANCE mesurée : dérive diffuse Beta(β,1) injectée dans toutes
     les uniformes élémentaires, pipeline de discrétisation identique.

Sous-ensemble défendable — règles appliquées au registre à l'exécution
----------------------------------------------------------------------
  R1  seules les entrées portant un p entrent (dédupliquées par id,
      dernière consignation retenue) ;
  R2  exclu : b2.hits_pmf_qc — contrôle qualité du code du labo sur des
      tirages synthétiques, ne teste pas la source ;
  R3  doublons de la même statistique sur les mêmes données — un seul
      représentant :
        - audit.boost_memoire ≈ b2.boost_memoire (même taux de répétition
          lag-1) ⊂ b2.boost_transition (table 6×6, strictement plus fine) :
          on garde b2.boost_transition ;
        - a2.rang1_recouvrement_mutuel : même fluctuation que
          a2.rang1_chi2_champ (Σ recouvrements mutuels = Σₙ C(cₙ,2),
          fonction des mêmes comptes de colonnes — corrélation mesurée
          dans la banque jointe, imprimée plus bas) : on garde le χ² ;
        - a2.rangs1_10_chi2_max : son observé EST le χ² du rang 1
          (83,304, le même nombre au registre) ; idem
          a2.rangs1_10_recouv_prec_max ⊃ rang1_recouvrement_prec : écartés ;
        - b3.conf_real / b3.evalue_real / b3.conf_calibration : trois
          fonctionnelles de la même trajectoire de marche avant du même
          prédicteur sur la même archive : on garde conf_real ;
  R4  p extrêmes de famille : quatre entrées consignent le MIN d'une
      famille de F tests (F = m_extra + 1) comme si c'était un test
      unique — audit.paires (F=3160), audit.maurer (F=9),
      audit.fenetres_bm (F=8), audit.fenetres_maurer (F=8). Sous H₀ un
      min de famille n'est PAS uniforme ; on le transforme en p familiale
      1−(1−p)^F, exacte sous indépendance intra-famille (empiriquement
      soutenue pour les paires : z de moyenne 0,000 et σ=0,983 ; exacte
      pour les fenêtres, fichiers disjoints ; conservatrice pour Maurer,
      configurations L positivement corrélées). audit.chi2, audit.derive,
      audit.analogues portent un p de synthèse, pas un min : non
      transformés.

Dépendances résiduelles APRÈS sélection (bras DEP) :
  - {a2.rang1_chi2_champ, rang1_recouvrement_prec, rang1_recouvrement_max} :
    mêmes 345+345 tirages — joint EXACT simulé (banque SRS) ;
  - {nist.monobit, nist.cusum} : même flux, cusum ⊃ sommes partielles du
    monobit — joint simulé par marche aléatoire ;
  - {nist.bm, audit.fenetres_bm} : mêmes blocs partitionnés — joint
    simulé par multinomiales (classes NIST df=6) ;
  - {audit.maurer, audit.fenetres_maurer, nist.entropie} : trois
    estimateurs d'entropie du même flux — pas de joint simulable
    honnêtement : borne comonotone (une seule uniforme partagée) ;
  - familles PAR SUBSTRAT sur les mêmes 70 560 tirages — le registre a
    grossi de 25 entrées (c1, c3) pendant la conception de cette
    expérience ; les 23 tests c3 partagent EN PLUS une même banque de
    400 réplicats SRS pour leurs nulls, ce qui corrèle leurs p au-delà
    du partage de données. Bornes comonotones par substrat :
      champ (χ² des 80 fréquences)  : audit.chi2 + c3.*_champ + a3 ;
      recouvrement lag-1            : audit.derive + c1.overlap_real +
                                      c1.matrix_real + c3.*_ov1 +
                                      c3.spectre_fft_ov1 + b3.conf_real ;
      somme des 20 numéros          : c3.*_somme + c3.spectre_* ;
      séquence boost                : c3.*_boost + b2.boost_transition.
  Le reste est traité indépendant (recoupements négligeables, p. ex. la
  cohorte a2 = 0,5 % de l'archive de audit.bonus_position). Les bornes
  comonotones sont volontairement EXCESSIVES : le bras DEP est la borne
  large ; le bras IND la borne étroite ; la vérité est entre les deux.

Second volet — les trois signaux les plus forts jamais observés
---------------------------------------------------------------
  a2 χ² rang 1 (p=0,0145), Maurer L=14 (p=0,041), recouvrement
  conditionné au bonus (p=0,044). Chacun mesuré UNE fois. Piège assumé :
  l'archive ne contient pas de données neuves — un découpage en moitiés
  n'est pas une réplication au sens strict, car le signal a été observé
  sur l'union des deux moitiés ; conditionné à la valeur pleine observée,
  la somme des moitiés est FIXÉE et ne contient plus d'information. Donc :
  - a2 (statistique DIRECTIONNELLE, 80 dimensions) : le seul des trois où
    la moitié contre moitié a du contenu — la corrélation des vecteurs
    d'écart entre moitiés, calibrée CONDITIONNELLEMENT au χ² plein
    observé, teste si la même direction se répète au-delà de ce que la
    fluctuation déjà consignée implique mécaniquement ;
  - Maurer L=14 (statistique scalaire moyenne) : la moitié contre moitié
    est circulaire à total fixé ; l'attaque décisive est ailleurs — son
    p=0,041 est TABULÉ (gaussienne NIST) dans un régime où K est 450 fois
    sous la recommandation : on re-dérive p par null SIMULÉ du pipeline
    exact (règle n°1 du labo, jamais appliquée à ce chiffre), moitiés en
    descriptif avec test d'homogénéité ;
  - bonus (scalaire) : idem — p=0,044 vient d'un z gaussien sur paires
    indépendantes ; on re-dérive p par simulation de CHAÎNES complètes
    (structure de dépendance exacte : paires adjacentes partageant un
    tirage, effectif de matches aléatoire), moitiés en descriptif.
  a3 (p=0,066) n'est pas réplicable dans l'archive : son objet est une
  fenêtre localisée datée, pas une propriété persistante — les deux
  moitiés ne contiennent pas le même défaut supposé ; et son p est déjà
  le p correctement calibré du max de balayage.

Usage : python3 c4_meta.py [--fast] [--no-record]
  --fast      réplicats réduits, implique --no-record
  --no-record calcule tout, n'écrit rien au registre
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from math import comb

import numpy as np
from scipy.special import ndtri
from scipy.stats import chi2 as chi2_dist

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import lab

FAST = "--fast" in sys.argv
NO_RECORD = "--no-record" in sys.argv or FAST
T0 = time.time()
rng = np.random.default_rng(20260827)


def say(*a):
    print(*a, flush=True)


def dh_p_upper(samples: np.ndarray, obs: float) -> float:
    """p empirique unilatéral (queue haute), correction Davison-Hinkley."""
    return float((1 + np.sum(samples >= obs)) / (1 + len(samples)))


def dh_p_two(samples: np.ndarray, obs: float) -> float:
    """p empirique bilatéral autour de la moyenne du null (convention lab)."""
    m = samples.mean()
    return float((1 + np.sum(np.abs(samples - m) >= abs(obs - m))) / (1 + len(samples)))


# ==========================================================================
# 1. Inventaire du registre et sélection du sous-ensemble défendable
# ==========================================================================

say("=" * 76)
say("1. INVENTAIRE DU REGISTRE — sélection du sous-ensemble défendable")
say("=" * 76)

ledger_rows = lab.ledger()
last = {}
for r in ledger_rows:
    last[r["id"]] = r                      # déduplication : la dernière fait foi
m_total_ledger = len(last) + sum(int(r.get("m_extra", 0)) for r in last.values())
say(f"registre : {len(ledger_rows)} lignes, {len(last)} ids uniques, "
    f"m = {m_total_ledger} tests dépensés (m_extra compris)")

EXCLUDE = {
    "b2.hits_pmf_qc": "QC du code du labo sur tirages synthétiques — ne teste pas la source",
    "audit.boost_memoire": "même statistique que b2.boost_memoire ; ⊂ b2.boost_transition",
    "b2.boost_memoire": "répétition lag-1 ⊂ table de transition 6x6 (b2.boost_transition)",
    "a2.rang1_recouvrement_mutuel": "même fluctuation que rang1_chi2_champ (Σ C(cn,2))",
    "a2.rangs1_10_chi2_max": "son observé EST le chi2 du rang 1 (83,304) — même nombre",
    "a2.rangs1_10_recouv_prec_max": "contient rang1_recouvrement_prec (max sur r=1..10)",
    "b3.evalue_real": "même trajectoire de marche avant que b3.conf_real",
    "b3.conf_calibration": "même trajectoire de marche avant que b3.conf_real",
}
# p consigné = min d'une famille de F tests -> transformé en p familiale
FAMILY = {"audit.paires": 3160, "audit.maurer": 9,
          "audit.fenetres_bm": 8, "audit.fenetres_maurer": 8}


def t_family(p: float, F: int) -> float:
    """p familiale du min de F tests : 1-(1-p)^F, via expm1 pour la précision."""
    return float(-np.expm1(F * np.log1p(-p)))


kept = []          # [(id, p_utilisé, p_brut, note)]
for eid, r in sorted(last.items()):
    p = r.get("p")
    if p is None:
        continue
    if eid in EXCLUDE:
        say(f"  exclu  {eid:32s} p={p:.4g}  ({EXCLUDE[eid]})")
        continue
    if eid.startswith("c4."):
        say(f"  exclu  {eid:32s} (sortie de cette expérience — pas d'auto-combinaison)")
        continue
    if eid in FAMILY:
        pf = t_family(p, FAMILY[eid])
        kept.append((eid, pf, p, f"min de famille F={FAMILY[eid]} -> 1-(1-p)^F"))
    else:
        kept.append((eid, float(p), float(p), ""))

kept.sort(key=lambda t: t[0])
KEPT_IDS = [t[0] for t in kept]
P_OBS = np.array([t[1] for t in kept])
N_KEPT = len(kept)
say(f"\nretenues : {N_KEPT} p-values")
for eid, pu, pb, note in kept:
    star = f"   [{note}, brut {pb:.4g}]" if note else ""
    say(f"  {eid:32s} p = {pu:.4f}{star}")

subset_seal = hashlib.sha256(
    json.dumps([(e, round(p, 10)) for e, p, _, _ in kept]).encode()).hexdigest()[:12]
say(f"\nsceau du sous-ensemble : {subset_seal}")

# --- distribution observée --------------------------------------------------
say("\nDistribution des p retenues (10 classes de largeur 0,1 ; attendu "
    f"{N_KEPT / 10:.1f} par classe) :")
hist, _ = np.histogram(P_OBS, bins=np.linspace(0, 1, 11))
for i, h in enumerate(hist):
    say(f"  [{i / 10:.1f},{(i + 1) / 10:.1f})  {h:2d}  {'#' * h}")
say(f"  p < 0,05 : {np.sum(P_OBS < 0.05)} (attendu {N_KEPT * 0.05:.1f})   "
    f"min = {P_OBS.min():.4f}   médiane = {np.median(P_OBS):.3f}")

# ==========================================================================
# 2. Pré-enregistrement — AVANT tout calcul de null ou d'observé combiné
# ==========================================================================

NULL_DESC = ("null simulé en rejouant la structure du registre : marges fidèles "
             "(arrondis audit, grilles DH aux null_reps consignés, transformations "
             "de famille 1-(1-p)^F) ; bras IND = indépendance totale (le plus "
             "défavorable à 'conforme') ; bras DEP = joints exacts simulés "
             "(triple a2 par SRS, monobit+cusum par marche aléatoire, BM par "
             "multinomiales) + bornes comonotones (bloc Maurer/entropie, bloc "
             "archive chi2/derive/a3/b3) ; p consigné = bras IND")
DECISION = ("significatif si p (bras IND) <= seuil Holm du registre entier a "
            "l'execution ; conforme sinon ; un p nominal <0,05 dans un seul bras "
            "est un artefact de structure, pas une decouverte")

tokens = {}
tokens["fisher"] = lab.preregister(
    "c4.meta_fisher",
    f"Exces global de petites p sur les {N_KEPT} p defendables du registre "
    "(source legerement defaillante -> exces diffus qu'aucun test isole ne voit)",
    f"Fisher X = -2 sum ln p sur le sous-ensemble {subset_seal} (n={N_KEPT})",
    NULL_DESC + " ; p unilateral queue haute", DECISION, track="A")
tokens["stouffer"] = lab.preregister(
    "c4.meta_stouffer",
    "Decalage coherent de l'ensemble des p vers 0 (ou vers 1) — sensible a une "
    "derive commune que Fisher dilue",
    f"Stouffer S = sum Phi^-1(1-p) / sqrt(n) sur le sous-ensemble {subset_seal}",
    NULL_DESC + " ; p bilateral autour de la moyenne du null", DECISION, track="A")
tokens["ks"] = lab.preregister(
    "c4.meta_ks",
    "Non-uniformite de la distribution ENTIERE des p (exces diffus en un point "
    "quelconque de [0,1], invisible a Fisher et Stouffer)",
    f"Kolmogorov-Smirnov D = sup|F_n - U| sur le sous-ensemble {subset_seal}",
    NULL_DESC + " ; p unilateral queue haute de D", DECISION, track="A")
tokens["ad"] = lab.preregister(
    "c4.meta_ad",
    "Non-uniformite de la distribution entiere des p, queues sur-ponderees "
    "(Anderson-Darling voit un exces diffus pres de 0 ou 1 que KS manque)",
    f"Anderson-Darling A2 sur le sous-ensemble {subset_seal}",
    NULL_DESC + " ; p unilateral queue haute de A2", DECISION, track="A")
tokens["rep_a2"] = lab.preregister(
    "c4.rep_a2_chi2",
    "REPLICATION du signal a2.rang1_chi2_champ (p=0,0145) : si le champ du rang 1 "
    "est reellement deforme, la MEME direction de deformation apparait dans les "
    "deux moities temporelles disjointes des 345 reprises, au-dela de ce que la "
    "fluctuation pleine deja consignee implique mecaniquement",
    "corr Pearson des vecteurs d'ecart (c - E) sur 80 numeros entre reprises "
    "1..172 et 173..345, calibree CONDITIONNELLEMENT au chi2 plein dans "
    "[79.3, 87.3] (observe 83.304 +/- 4)",
    "SRS 345 tirages par replicat (lab.srs), rejet hors bande ; p unilateral "
    "P(corr >= obs | bande) ; secondaires : chi2 et z par moitie (m_extra=2)",
    "replique si p_cond <= 0,05 ET les deux moities devient dans le meme sens ; "
    "sinon fluctuation", track="A")
tokens["rep_maurer"] = lab.preregister(
    "c4.rep_maurer14",
    "RE-DERIVATION du signal audit.maurer L=14 (p=0,041, z=+2,045) : ce p est "
    "TABULE (gaussienne NIST) avec K=36030 soit 450x sous la recommandation "
    "K>=1000*2^L — regle n1 du labo jamais appliquee a ce chiffre ; moitie "
    "contre moitie en secondaire (circulaire a total fixe, homogeneite seule)",
    "f_n du pipeline exact de l'audit (rang colex < 2^61, 61 bits MSB, blocs "
    "L=14, Q=163840, K=36030) contre null SIMULE (blocs uniformes iid, meme "
    "pipeline) ; secondaires : z des moities K1=K2=18015 a init partagee et "
    "homogeneite |z1-z2| (m_extra=2)",
    "null simule, R>=500 replicats du pipeline complet ; p bilateral DH",
    "le signal tient si p simule <= 0,041 ; il se degonfle si p simule > 0,05",
    track="A")
tokens["rep_bonus"] = lab.preregister(
    "c4.rep_bonus_overlap",
    "RE-DERIVATION du signal audit.bonus_overlap (p=0,044, z=+2,01) : ce p vient "
    "d'un z gaussien calibre sur des PAIRES INDEPENDANTES ; l'archive est une "
    "CHAINE (paires adjacentes partageant un tirage, effectif de matches "
    "aleatoire) ; moities en secondaire (circulaire a total fixe)",
    "moyenne du recouvrement sur les paires adjacentes a bonus egal (observe "
    "5.6806, n=883) contre null simule par CHAINES SRS completes de 70560 "
    "tirages, bonus uniforme parmi les 20 ; secondaires : z des moities "
    "(35280 tirages chacune) et homogeneite (m_extra=2)",
    "chaines SRS completes simulees, R>=800 ; p bilateral DH",
    "le signal tient si p simule <= 0,044 ; il se degonfle si p simule > 0,05",
    track="A")

say("\n7 jetons scellés :",
    " ".join(f"{k}:{tokens[k]['seal']}" for k in tokens))

# ==========================================================================
# 3. Banques de joints exacts (utilisées par le bras DEP ; marges par les deux)
# ==========================================================================

say("\n" + "=" * 76)
say("3. BANQUES DE JOINTS EXACTS")
say("=" * 76)

# --- 3a. triple a2 : chi2 champ (345), recouvrement apparié (345 paires),
#         max mutuel (gram 345x345) — mêmes tirages
B_A2 = 800 if FAST else 3000
_iu = np.triu_indices(345, 1)
a2_stats = np.empty((B_A2, 4))
for b in range(B_A2):
    m = lab.srs(690, rng)
    ra, pv = m[:345], m[345:]
    c = ra.sum(0)
    a2_stats[b, 0] = (((c - 86.25) ** 2) / 86.25).sum()
    a2_stats[b, 1] = (ra & pv).sum(1).mean()
    g = ra.astype(np.int16) @ ra.T.astype(np.int16)
    a2_stats[b, 2] = g[_iu].max()
    a2_stats[b, 3] = g[_iu].mean()          # recouvrement mutuel — pour la note R3


def bank_p(stats: np.ndarray, two_sided_center: bool = True) -> np.ndarray:
    """p DH de chaque membre de la banque contre la banque elle-même (ties ok)."""
    m = stats.mean()
    d = np.abs(stats - m) if two_sided_center else stats
    ds = np.sort(d)
    cnt_ge = len(d) - np.searchsorted(ds, d, side="left")   # soi-même compris
    return cnt_ge / (len(d) + 1.0)


a2_bank = np.column_stack([bank_p(a2_stats[:, j]) for j in range(3)])
r_chi_mut = float(np.corrcoef(a2_stats[:, 0], a2_stats[:, 3])[0, 1])
say(f"3a. banque a2 : {B_A2} triples ; corr(chi2, recouv mutuel moyen) sous H0 "
    f"= {r_chi_mut:+.3f}  (justifie l'exclusion R3 du doublon)")
say(f"    corrélations résiduelles des p du triple retenu : "
    f"chi2-prec {np.corrcoef(a2_bank[:, 0], a2_bank[:, 1])[0, 1]:+.3f}, "
    f"chi2-max {np.corrcoef(a2_bank[:, 0], a2_bank[:, 2])[0, 1]:+.3f}")

# --- 3b. monobit + cusum : marche aléatoire ±1 (copule du couple (S_N, max|S|))
B_WALK = 8000 if FAST else 40000
NW = 8192
walk_p = np.empty((B_WALK, 2))
chunk = 4000
for lo in range(0, B_WALK, chunk):
    hi = min(lo + chunk, B_WALK)
    steps = rng.integers(0, 2, size=(hi - lo, NW), dtype=np.int8).astype(np.int32) * 2 - 1
    S = np.cumsum(steps, axis=1)
    zmono = S[:, -1] / math.sqrt(NW)
    cus = np.abs(S).max(axis=1) / math.sqrt(NW)
    walk_p[lo:hi, 0] = np.round([math.erfc(abs(z) / math.sqrt(2)) for z in zmono], 3)
    walk_p[lo:hi, 1] = cus
walk_p[:, 0] = np.maximum(walk_p[:, 0], 0.0005)
# p du cusum par ecdf de la banque (queue haute, ties ok)
walk_p[:, 1] = np.round(bank_p(walk_p[:, 1], two_sided_center=False), 3)
walk_p[:, 1] = np.maximum(walk_p[:, 1], 0.0005)
say(f"3b. banque marche aléatoire : {B_WALK} couples ; corr(p_mono, p_cusum) "
    f"sous H0 = {np.corrcoef(walk_p[:, 0], walk_p[:, 1])[0, 1]:+.3f}")

# --- 3c. BM agrégé + min des 8 fenêtres : multinomiales NIST (df=6)
B_BM = 10000 if FAST else 50000
PI_LC = np.array([0.010417, 0.03125, 0.125, 0.5, 0.25, 0.0625, 0.020833])
PI_LC = PI_LC / PI_LC.sum()
NBLK = [710] * 7 + [602]                       # ~355k bits / 500 par fichier
counts = np.stack([rng.multinomial(nb, PI_LC, size=B_BM) for nb in NBLK], axis=1)
exp_w = np.array(NBLK)[None, :, None] * PI_LC[None, None, :]
chi_w = (((counts - exp_w) ** 2) / exp_w).sum(axis=2)          # (B,8)
p_w = np.round(chi2_dist.sf(chi_w, 6), 4)
p_fam_bm = np.array([t_family(pm, 8) for pm in p_w.min(axis=1)])
agg = counts.sum(axis=1)
exp_a = sum(NBLK) * PI_LC
chi_a = (((agg - exp_a) ** 2) / exp_a).sum(axis=1)
p_agg_bm = np.round(chi2_dist.sf(chi_a, 6), 3)
bm_bank = np.column_stack([p_agg_bm, p_fam_bm])
say(f"3c. banque BM : {B_BM} couples ; corr(p_agrégé, p_famille fenêtres) "
    f"sous H0 = {np.corrcoef(bm_bank[:, 0], bm_bank[:, 1])[0, 1]:+.3f}")

# ==========================================================================
# 4. Null méta : assemblage des 27 p sous H0, deux bras — puis observé
# ==========================================================================

say("\n" + "=" * 76)
say("4. STATISTIQUES COMBINÉES — null simulé, deux bras de dépendance")
say("=" * 76)

R_META = 4000 if FAST else 20000

# précisions d'arrondi consignées au registre (répliquées dans le null)
ROUND2 = {"audit.chi2", "audit.antirejeu", "audit.derive", "audit.analogues"}
ROUND3 = {"audit.geometrie", "audit.bonus_position", "nist.blocs", "nist.runs",
          "nist.longest", "nist.dft", "nist.entropie", "audit.bonus_overlap"}
# grilles DH : lues sur le registre (null_reps de chaque entrée) — couvre
# aussi toute entrée future consignée par un autre volet du labo
DH_GRID = {eid: int(last[eid]["null_reps"]) for eid in KEPT_IDS
           if last[eid].get("null_reps") and eid not in FAMILY}
BANK_A2 = {"a2.rang1_chi2_champ": 0, "a2.rang1_recouvrement_prec": 1,
           "a2.rang1_recouvrement_max": 2}
BANK_WALK = {"nist.monobit": 0, "nist.cusum": 1}
BANK_BM = {"nist.bm": 0, "audit.fenetres_bm": 1}
for eid in list(DH_GRID):
    if eid in BANK_A2 or eid in BANK_WALK or eid in BANK_BM:
        del DH_GRID[eid]
# blocs comonotones du bras DEP (une uniforme partagée par bloc, par substrat)
COMONO = {"audit.maurer": "blkM", "audit.fenetres_maurer": "blkM",
          "nist.entropie": "blkM",
          "audit.chi2": "blkChamp", "a3.changepoint_scan": "blkChamp",
          "audit.derive": "blkOv", "b3.conf_real": "blkOv",
          "c1.overlap_real": "blkOv", "c1.matrix_real": "blkOv",
          "b2.boost_transition": "blkBoost"}
for cov in ("heure", "jsem", "minute", "jmois", "slot"):
    COMONO[f"c3.{cov}_champ"] = "blkChamp"
    COMONO[f"c3.{cov}_ov1"] = "blkOv"
    COMONO[f"c3.{cov}_somme"] = "blkSum"
    COMONO[f"c3.{cov}_boost"] = "blkBoost"
COMONO["c3.spectre_fft_ov1"] = "blkOv"
COMONO["c3.spectre_fft_somme"] = "blkSum"
COMONO["c3.spectre_cible_somme"] = "blkSum"

unclassified = [e for e in KEPT_IDS
                if e not in COMONO and e not in BANK_A2 and e not in BANK_WALK
                and e not in BANK_BM and e not in FAMILY and e not in ROUND2
                and e not in ROUND3 and e not in DH_GRID]
if unclassified:
    say(f"ATTENTION — entrées sans classement de dépendance/marge (traitées "
        f"indépendantes, arrondi 3 déc.) : {unclassified}")
say(f"grilles DH lues sur le registre : { {e: DH_GRID[e] for e in sorted(DH_GRID)} }")
say(f"blocs comonotones DEP effectifs : "
    f"{ {b: sum(1 for e in KEPT_IDS if COMONO.get(e) == b) for b in sorted(set(COMONO.values()))} }")

_sorted_banks = {"a2": np.sort(a2_bank, axis=0),
                 "walk": np.sort(walk_p, axis=0),
                 "bm": np.sort(bm_bank, axis=0)}


def marginal_from_u(eid: str, U: np.ndarray) -> np.ndarray:
    """p sous H0 pour une entrée hors banque, à partir d'uniformes U."""
    if eid in FAMILY:
        F = FAMILY[eid]
        M = -np.expm1(np.log1p(-U) / F)                 # min de F uniformes indép.
        d = 4 if eid in ("audit.paires", "audit.fenetres_bm") else 3
        M = np.maximum(np.round(M, d), 10.0 ** (-d) / 2)
        return -np.expm1(F * np.log1p(-M))
    if eid in DH_GRID:
        R = DH_GRID[eid]
        return np.ceil(U * (R + 1)) / (R + 1)
    if eid in ROUND2:
        return np.maximum(np.round(U, 2), 0.005)
    return np.maximum(np.round(U, 3), 0.0005)           # défaut : 3 décimales


def assemble(R: int, arm: str, rng: np.random.Generator,
             beta: float = 1.0) -> np.ndarray:
    """Matrice (R, n_kept) de p sous H0 (beta=1) ou sous dérive Beta(beta,1).

    beta<1 : chaque uniforme élémentaire U est remplacée par U^(1/beta),
    même pipeline de discrétisation/transformation. Les entrées en banque
    reçoivent le quantile de leur marge de banque au rang Beta(beta,1)."""
    P = np.empty((R, N_KEPT))
    blocks = {b: rng.random(R) ** (1.0 / beta)
              for b in ("blkM", "blkChamp", "blkOv", "blkSum", "blkBoost")}
    idx_a2 = rng.integers(0, B_A2, R)
    idx_walk = rng.integers(0, B_WALK, R)
    idx_bm = rng.integers(0, B_BM, R)
    for j, eid in enumerate(KEPT_IDS):
        if eid in BANK_A2:
            col = BANK_A2[eid]
            if beta != 1.0:                     # contamination : quantile de marge
                q = rng.random(R) ** (1.0 / beta)
                P[:, j] = _sorted_banks["a2"][(q * B_A2).astype(int), col]
            elif arm == "dep":
                P[:, j] = a2_bank[idx_a2, col]
            else:
                P[:, j] = a2_bank[rng.integers(0, B_A2, R), col]
        elif eid in BANK_WALK:
            col = BANK_WALK[eid]
            if beta != 1.0:
                q = rng.random(R) ** (1.0 / beta)
                P[:, j] = _sorted_banks["walk"][(q * B_WALK).astype(int), col]
            elif arm == "dep":
                P[:, j] = walk_p[idx_walk, col]
            else:
                P[:, j] = walk_p[rng.integers(0, B_WALK, R), col]
        elif eid in BANK_BM:
            col = BANK_BM[eid]
            if beta != 1.0:
                q = rng.random(R) ** (1.0 / beta)
                P[:, j] = _sorted_banks["bm"][(q * B_BM).astype(int), col]
            elif arm == "dep":
                P[:, j] = bm_bank[idx_bm, col]
            else:
                P[:, j] = bm_bank[rng.integers(0, B_BM, R), col]
        else:
            if arm == "dep" and eid in COMONO and beta == 1.0:
                U = blocks[COMONO[eid]]
            else:
                U = rng.random(R) ** (1.0 / beta)
            P[:, j] = marginal_from_u(eid, U)
    return P


def combos(P: np.ndarray) -> dict[str, np.ndarray]:
    """Fisher, Stouffer, KS, AD sur chaque ligne de P."""
    Pc = np.clip(P, 1e-15, 1 - 1e-15)
    fisher = -2.0 * np.log(Pc).sum(axis=1)
    stouf = ndtri(1.0 - Pc).sum(axis=1) / math.sqrt(P.shape[1])
    Ps = np.sort(Pc, axis=1)
    n = P.shape[1]
    i = np.arange(1, n + 1)
    ks = np.maximum((i / n - Ps).max(axis=1), (Ps - (i - 1) / n).max(axis=1))
    ad = -n - ((2 * i - 1) * (np.log(Ps) + np.log(1 - Ps[:, ::-1]))).sum(axis=1) / n
    return {"fisher": fisher, "stouffer": stouf, "ks": ks, "ad": ad}


rng_null = np.random.default_rng(11)
null_ind = combos(assemble(R_META, "ind", rng_null))
null_dep = combos(assemble(R_META, "dep", rng_null))
obs = combos(P_OBS[None, :])
obs = {k: float(v[0]) for k, v in obs.items()}

say(f"\nnull simulé : {R_META} réplicats par bras ; observé sur les {N_KEPT} p réelles\n")
say(f"{'stat':10s} {'observé':>9s} | {'IND moy±sd':>16s} {'z':>6s} {'p_IND':>8s} "
    f"| {'DEP moy±sd':>16s} {'z':>6s} {'p_DEP':>8s}")
meta_p = {}
for k in ("fisher", "stouffer", "ks", "ad"):
    two = (k == "stouffer")
    pi = dh_p_two(null_ind[k], obs[k]) if two else dh_p_upper(null_ind[k], obs[k])
    pd_ = dh_p_two(null_dep[k], obs[k]) if two else dh_p_upper(null_dep[k], obs[k])
    meta_p[k] = (pi, pd_)
    mi, si = null_ind[k].mean(), null_ind[k].std(ddof=1)
    md, sd_ = null_dep[k].mean(), null_dep[k].std(ddof=1)
    say(f"{k:10s} {obs[k]:9.3f} | {mi:8.3f}±{si:6.3f} {(obs[k]-mi)/si:+6.2f} {pi:8.4f} "
        f"| {md:8.3f}±{sd_:6.3f} {(obs[k]-md)/sd_:+6.2f} {pd_:8.4f}")
say("\n(référence tabulée qu'il ne faut PAS utiliser : Fisher ~ chi2 à "
    f"{2 * N_KEPT} ddl donnerait p = {chi2_dist.sf(obs['fisher'], 2 * N_KEPT):.4f} — "
    "faux car marges discrètes/arrondies et dépendances)")

# ==========================================================================
# 5. Puissance : dérive diffuse Beta(beta,1) sur toutes les uniformes
# ==========================================================================

say("\n" + "=" * 76)
say("5. PUISSANCE — quelle dérive diffuse aurait été vue ?")
say("=" * 76)

R_POW = 1000 if FAST else 4000
BETAS = (0.95, 0.9, 0.8, 0.7, 0.5)
thr = {}
for k in ("fisher", "stouffer", "ks", "ad"):
    thr[k] = {}
    for arm, nl in (("ind", null_ind), ("dep", null_dep)):
        if k == "stouffer":
            m = nl[k].mean()
            thr[k][arm] = {a: np.quantile(np.abs(nl[k] - m), 1 - a) for a in (0.05, 0.005)}
        else:
            thr[k][arm] = {a: np.quantile(nl[k], 1 - a) for a in (0.05, 0.005)}

say(f"\npuissance ({R_POW} réplicats contaminés/β ; structure IND)")
say("β : chaque p élémentaire ~ Beta(β,1) au lieu d'uniforme "
    "(E[p] = β/(1+β) ; β=0,9 -> E[p]=0,474)")
hdr = f"{'stat':10s}" + "".join(f"  β={b:<12g}" for b in BETAS)
say(hdr + "   (colonnes : α=0,05, seuil IND | seuil DEP — la vérité entre les deux)")
power_notes = {}
rng_pow = np.random.default_rng(13)
pow_tab = {}
for b in BETAS:
    pow_tab[b] = combos(assemble(R_POW, "ind", rng_pow, beta=b))
for k in ("fisher", "stouffer", "ks", "ad"):
    cells = []
    for b in BETAS:
        v = pow_tab[b][k]
        if k == "stouffer":
            mi, md = null_ind[k].mean(), null_dep[k].mean()
            p_i = np.mean(np.abs(v - mi) >= thr[k]["ind"][0.05])
            p_d = np.mean(np.abs(v - md) >= thr[k]["dep"][0.05])
        else:
            p_i = np.mean(v >= thr[k]["ind"][0.05])
            p_d = np.mean(v >= thr[k]["dep"][0.05])
        cells.append(f"{p_i:.2f}|{p_d:.2f}")
    say(f"{k:10s}" + "".join(f"  {c:>13s}" for c in cells))
    power_notes[k] = dict(zip(BETAS, cells))

# extrapolation au seuil Holm — approximation déclarée, pas une mesure
m_now = len([r for r in last.values() if r.get("p") is not None]) + \
    sum(int(r.get("m_extra", 0)) for r in last.values())
holm_thr = 0.05 / m_now
zH = -ndtri(holm_thr)
fisher_null_dep = null_dep["fisher"]
fisher_H = fisher_null_dep.mean() + zH * fisher_null_dep.std(ddof=1)
pow_H = {b: float(np.mean(pow_tab[b]["fisher"] >= fisher_H)) for b in BETAS}
say(f"\nau seuil Holm du registre (p<{holm_thr:.2e}) — seuil Fisher extrapolé "
    f"gaussien ({fisher_H:.0f}), approximation déclarée :")
say("  " + "  ".join(f"β={b}: {pow_H[b]:.2f}" for b in BETAS))

# ==========================================================================
# 6. Consignation des quatre entrées méta
# ==========================================================================

META_NOTE = (f"sous-ensemble {subset_seal} : {N_KEPT} p retenues sur "
             f"{len(last)} ids ({len(EXCLUDE)} exclusions doublons/QC, "
             f"4 transformations de famille) ; "
             "p_IND consigne (bras le plus defavorable a 'conforme') ; ")
if not NO_RECORD:
    for k in ("fisher", "stouffer", "ks", "ad"):
        pi, pd_ = meta_p[k]
        nl = null_ind[k]
        lab.record(
            tokens[k], observed=obs[k],
            p=pi,
            power_at=("derive diffuse Beta(b,1), a=0.05, seuil IND|DEP : "
                      + " ; ".join(f"b={b}: {power_notes[k][b]}" for b in BETAS)),
            verdict=("conforme" if pi > holm_thr else "SIGNIFICATIF au seuil Holm"),
            notes=(META_NOTE + f"null IND {nl.mean():.2f}±{nl.std(ddof=1):.2f} "
                   f"(R={R_META}), p_DEP={pd_:.4f} ; "
                   f"Fisher tabule (a NE PAS utiliser) p="
                   f"{chi2_dist.sf(obs['fisher'], 2 * N_KEPT):.4f}"))
    say("\n4 entrées méta consignées au registre.")

# ==========================================================================
# 7. Réplication 1/3 — a2 χ² du champ au rang 1 (directionnelle, conditionnelle)
# ==========================================================================

say("\n" + "=" * 76)
say("7. RÉPLICATION a2.rang1_chi2_champ — direction moitié contre moitié")
say("=" * 76)

a = lab.load()
d = np.diff(a.ts)
res = np.where(d > 600)[0] + 1
assert len(res) == 345
r1 = a.mask[res]
N1, N2 = 172, 173
E1, E2 = N1 * 0.25, N2 * 0.25


def chi2_field(mask):
    n = len(mask)
    e = n * 0.25
    c = mask.sum(0).astype(float)
    return float(((c - e) ** 2 / e).sum()), c


chi_full, c_full = chi2_field(r1)
chi_h1, c1 = chi2_field(r1[:N1])
chi_h2, c2 = chi2_field(r1[N1:])
dev1, dev2 = c1 - E1, c2 - E2
corr_obs = float(np.corrcoef(dev1, dev2)[0, 1])
say(f"observé : chi2 plein {chi_full:.3f} (registre 83.304) ; "
    f"chi2 moitiés {chi_h1:.2f} / {chi_h2:.2f} ; corr directions {corr_obs:+.4f}")

BAND = (79.3, 87.3)
R_A2 = 30000 if FAST else 150000
say(f"null : {R_A2} cohortes SRS 345 ; conditionnement chi2 ∈ [{BAND[0]}, {BAND[1]}]")
rng_a2 = np.random.default_rng(17)
sim = np.empty((R_A2, 4))
for b in range(R_A2):
    mm = lab.srs(345, rng_a2)
    ca = mm[:N1].sum(0).astype(float)
    cb = mm[N1:].sum(0).astype(float)
    da, db = ca - E1, cb - E2
    x1 = float((da * da).sum() / E1)
    x2 = float((db * db).sum() / E2)
    cf = float((((ca + cb) - 86.25) ** 2).sum() / 86.25)
    sim[b] = (cf, x1, x2, float(np.corrcoef(da, db)[0, 1]))

z_h1 = (chi_h1 - sim[:, 1].mean()) / sim[:, 1].std(ddof=1)
z_h2 = (chi_h2 - sim[:, 2].mean()) / sim[:, 2].std(ddof=1)
in_band = (sim[:, 0] >= BAND[0]) & (sim[:, 0] <= BAND[1])
corr_cond = sim[in_band, 3]
p_corr_cond = dh_p_upper(corr_cond, corr_obs)
p_corr_uncond = dh_p_upper(sim[:, 3], corr_obs)
say(f"z des moitiés (null simulé, E[chi2]={sim[:, 1].mean():.1f}) : "
    f"{z_h1:+.2f} / {z_h2:+.2f}")
say(f"corr null inconditionnel : {sim[:, 3].mean():+.4f} ± {sim[:, 3].std(ddof=1):.4f} "
    f"-> p = {p_corr_uncond:.4f}")
say(f"corr null CONDITIONNEL (bande, {in_band.sum()} réplicats retenus) : "
    f"{corr_cond.mean():+.4f} ± {corr_cond.std(ddof=1):.4f} -> p = {p_corr_cond:.4f}")

# puissance : témoin positif — 10 numéros à +d, d réglé pour E[chi2]~83
say("puissance du test conditionnel (témoin : 10 numéros biaisés, Gumbel top-20) :")


def biased_srs(n, w, rgen):
    g = rgen.gumbel(size=(n, 80))
    keys = np.log(w)[None, :] + g
    idx = np.argpartition(-keys, 20, axis=1)[:, :20]
    out = np.zeros((n, 80), bool)
    np.put_along_axis(out, idx, True, axis=1)
    return out


corr_cond_sorted = np.sort(corr_cond)
crit_corr = float(np.quantile(corr_cond, 0.95))
pow_lines = []
for dbias in (0.03, 0.04, 0.06):
    q = np.full(80, 0.25)
    q[:10] += dbias
    q[10:] -= 10 * dbias / 70
    w = q / (1 - q)
    R_W = 300 if FAST else 1200
    hit = tot = 0
    for _ in range(R_W):
        mm = biased_srs(345, w, rng_a2)
        ca = mm[:N1].sum(0).astype(float)
        cb = mm[N1:].sum(0).astype(float)
        cf = float((((ca + cb) - 86.25) ** 2).sum() / 86.25)
        if BAND[0] <= cf <= BAND[1]:
            tot += 1
            if float(np.corrcoef(ca - E1, cb - E2)[0, 1]) >= crit_corr:
                hit += 1
    pw = hit / max(tot, 1)
    pow_lines.append(f"d={dbias}: {pw:.2f} (dans bande {tot}/{R_W})")
    say(f"  {pow_lines[-1]}")

verdict_a2 = ("replique" if (p_corr_cond <= 0.05 and z_h1 > 0 and z_h2 > 0)
              else "non replique (et puissance conditionnelle faible a taille appariee)")
say(f"VERDICT a2 : {verdict_a2}")
if not NO_RECORD:
    row = lab.record(
        tokens["rep_a2"], observed=corr_obs, p=p_corr_cond,
        power_at="temoin 10 numeros biaises (corr cond. au seuil q95) : " + " ; ".join(pow_lines),
        verdict=verdict_a2,
        notes=(f"chi2 plein {chi_full:.3f} ; moities {chi_h1:.2f} (z {z_h1:+.2f}) / "
               f"{chi_h2:.2f} (z {z_h2:+.2f}) ; corr obs {corr_obs:+.4f} ; null cond "
               f"{corr_cond.mean():+.4f}±{corr_cond.std(ddof=1):.4f} "
               f"({in_band.sum()} rep. en bande / {R_A2}) ; p incond {p_corr_uncond:.4f} "
               "(quasi redondant avec le p original 0.0145 — meme information) ; "
               "le conditionnement retire ce que la fluctuation pleine consignee "
               "implique mecaniquement sur corr ; lecon de puissance : un biais "
               "reel REGLE pour produire le chi2 observe est presque indistinguable "
               "d'une fluctuation conditionnee par corr moitie-moitie — l'archive "
               "seule ne peut pas repliquer ce signal, seules des donnees neuves "
               "le peuvent"))
    # les 2 regards secondaires (chi2 des moitiés) comptent dans m
    rows_txt = open(lab.LEDGER).readlines()
    obj = json.loads(rows_txt[-1]); obj["m_extra"] = 2
    rows_txt[-1] = json.dumps(obj, ensure_ascii=False) + "\n"
    open(lab.LEDGER, "w").writelines(rows_txt)

# ==========================================================================
# 8. Réplication 2/3 — Maurer L=14 : re-dérivation par null simulé
# ==========================================================================

say("\n" + "=" * 76)
say("8. RÉPLICATION audit.maurer L=14 — p tabulé re-dérivé par simulation")
say("=" * 76)

CT = np.zeros((81, 21), dtype=object)
for v in range(81):
    for kk in range(21):
        CT[v, kk] = comb(v, kk)
LIM = 1 << 61
ranks_ok = []
for row in a.nums:
    rk = 0
    for i, v in enumerate(row):
        rk += CT[v - 1, i + 1]
    if rk < LIM:
        ranks_ok.append(rk)
arr = np.array(ranks_ok, dtype=np.uint64)
bits = np.unpackbits(arr.byteswap().view(np.uint8).reshape(-1, 8), axis=1)[:, 3:].ravel()
say(f"flux : {len(ranks_ok)} tirages acceptés, {bits.size} bits "
    "(audit : 45 872, 2 798 192)")
assert bits.size == 2798192

L, Q = 14, 10 * (1 << 14)
nb = bits.size // L
blocks_obs = bits[:nb * L].reshape(nb, L).astype(np.int64) @ \
    (1 << np.arange(L - 1, -1, -1, dtype=np.int64))
K = nb - Q
K1 = K // 2


def maurer_fn(v: np.ndarray) -> tuple[float, float, float]:
    """(fn plein, fn moitié 1, fn moitié 2), init Q partagée — pipeline audit."""
    T = v.size
    order = np.argsort(v, kind="stable")
    sv = v[order]
    prev = np.full(T, -1, np.int64)
    same = sv[1:] == sv[:-1]
    prev[order[1:]] = np.where(same, order[:-1], -1)
    prev[order[0]] = -1
    i = np.arange(T, dtype=np.int64)
    logs = np.log2(np.where(prev >= 0, i - prev, i + 1).astype(np.float64))
    return (float(logs[Q:Q + K].mean()),
            float(logs[Q:Q + K1].mean()), float(logs[Q + K1:Q + K].mean()))


fn_obs, fn1_obs, fn2_obs = maurer_fn(blocks_obs)
say(f"observé : fn = {fn_obs:.6f} (audit 13.181374) ; moitiés {fn1_obs:.6f} / {fn2_obs:.6f}")
assert abs(fn_obs - 13.181374) < 1e-5

R_MAU = 200 if FAST else 600
sim_m = np.empty((R_MAU, 3))
rng_m = np.random.default_rng(19)
for b in range(R_MAU):
    sim_m[b] = maurer_fn(rng_m.integers(0, 1 << L, size=nb))
p_fn = dh_p_two(sim_m[:, 0], fn_obs)
mu, sd = sim_m[:, 0].mean(), sim_m[:, 0].std(ddof=1)
z_sim = (fn_obs - mu) / sd
say(f"null simulé ({R_MAU} réplicats du pipeline complet) : "
    f"E[fn] = {mu:.6f} ± {sd:.6f}")
say(f"  attendu NIST tabulé : 13.167693 — écart de calibration "
    f"{(mu - 13.167693) / sd:+.2f} sd du null")
say(f"  z simulé = {z_sim:+.2f}   p simulé (bilatéral DH) = {p_fn:.4f}   "
    "(p tabulé audit : 0.041)")
z1 = (fn1_obs - sim_m[:, 1].mean()) / sim_m[:, 1].std(ddof=1)
z2 = (fn2_obs - sim_m[:, 2].mean()) / sim_m[:, 2].std(ddof=1)
dz_null = np.abs((sim_m[:, 1] - sim_m[:, 1].mean()) / sim_m[:, 1].std(ddof=1)
                 - (sim_m[:, 2] - sim_m[:, 2].mean()) / sim_m[:, 2].std(ddof=1))
p_hom = dh_p_upper(dz_null, abs(z1 - z2))
say(f"moitiés (init partagée) : z1 = {z1:+.2f}, z2 = {z2:+.2f} ; "
    f"homogénéité |z1-z2| = {abs(z1 - z2):.2f}, p = {p_hom:.3f} "
    "(à total fixé la moitié contre moitié ne porte que ceci)")

say("puissance (témoin : q motifs de 14 bits interdits — source compressible) :")
pow_m_lines = []
crit_lo = np.quantile(sim_m[:, 0], 0.025)
crit_hi = np.quantile(sim_m[:, 0], 0.975)
for q_out in (164, 328):
    R_W = 30 if FAST else 60
    hits = 0
    allowed = rng_m.permutation(1 << L)[:(1 << L) - q_out]
    for _ in range(R_W):
        v = allowed[rng_m.integers(0, allowed.size, size=nb)]
        f, _, _ = maurer_fn(v)
        if f < crit_lo or f > crit_hi:
            hits += 1
    pow_m_lines.append(f"{q_out}/16384 motifs interdits ({q_out / 163.84:.0f}%): {hits / R_W:.2f}")
    say(f"  {pow_m_lines[-1]}")

verdict_m = "signal degonfle (p simule > 0.05)" if p_fn > 0.05 else \
    ("tient au niveau nominal" if p_fn <= 0.041 else "affaibli")
say(f"VERDICT Maurer : {verdict_m}")
if not NO_RECORD:
    lab.record(
        tokens["rep_maurer"], observed=fn_obs, p=p_fn,
        power_at="temoin motifs interdits, alpha=0.05 bilateral : " + " ; ".join(pow_m_lines),
        verdict=verdict_m,
        notes=(f"null simule E[fn]={mu:.6f}±{sd:.6f} (R={R_MAU}) vs NIST tabule "
               f"13.167693 (biais de reference {(mu - 13.167693) / sd:+.2f} sd) ; "
               f"z simule {z_sim:+.2f} vs +2.045 tabule ; moities z1={z1:+.2f} "
               f"z2={z2:+.2f}, homogeneite p={p_hom:.3f} ; l'ecart etait dans le "
               "sens TROP aleatoire (fn haut = moins compressible), incompatible "
               "avec une source defaillante des le depart"))
    rows_txt = open(lab.LEDGER).readlines()
    obj = json.loads(rows_txt[-1]); obj["m_extra"] = 2
    rows_txt[-1] = json.dumps(obj, ensure_ascii=False) + "\n"
    open(lab.LEDGER, "w").writelines(rows_txt)

# ==========================================================================
# 9. Réplication 3/3 — recouvrement conditionné au bonus : chaînes complètes
# ==========================================================================

say("\n" + "=" * 76)
say("9. RÉPLICATION audit.bonus_overlap — null re-dérivé par chaînes complètes")
say("=" * 76)

N = len(a)
ovl = (a.mask[:-1] & a.mask[1:]).sum(1)
mtch = (a.bonus[:-1] == a.bonus[1:])
mean_obs = float(ovl[mtch].mean())
n_obs = int(mtch.sum())
H = N // 2
m1, m2 = mtch[:H - 1], mtch[H:]
o1, o2 = ovl[:H - 1], ovl[H:]
mean1, mean2 = float(o1[m1].mean()), float(o2[m2].mean())
say(f"observé : plein {mean_obs:.4f} (n={n_obs} ; audit 5.68/883) ; "
    f"moitiés {mean1:.4f} (n={m1.sum()}) / {mean2:.4f} (n={m2.sum()})")


def chain_stat(n_draws: int, rgen: np.random.Generator,
               reman_f: float = 0.0, reman_o: int = 6) -> float:
    keys = rgen.random((n_draws, 80))
    idx = np.argpartition(keys, 20, axis=1)[:, :20]
    m = np.zeros((n_draws, 80), bool)
    np.put_along_axis(m, idx, True, axis=1)
    if reman_f > 0:                       # témoin : rémanence du tirage précédent
        flagged = np.where(rgen.random(n_draws - 1) < reman_f)[0] + 1
        for i in flagged:
            copy = rgen.choice(np.where(m[i - 1])[0], reman_o, replace=False)
            rest = np.setdiff1d(np.where(m[i])[0], copy)
            need = 20 - reman_o
            if rest.size > need:
                rest = rgen.choice(rest, need, replace=False)
            elif rest.size < need:
                pool = np.setdiff1d(np.arange(80), np.concatenate([copy, rest]))
                rest = np.concatenate([rest, rgen.choice(pool, need - rest.size,
                                                         replace=False)])
            m[i] = False
            m[i, copy] = True
            m[i, rest] = True
        idx = np.argsort(~m, axis=1, kind="stable")[:, :20]
    ov = (m[:-1] & m[1:]).sum(1)
    bsel = idx[np.arange(n_draws), rgen.integers(0, 20, n_draws)]
    mt = bsel[:-1] == bsel[1:]
    return float(ov[mt].mean())


rng_b = np.random.default_rng(23)
R_FULL = 200 if FAST else 800
sim_full = np.array([chain_stat(N, rng_b) for _ in range(R_FULL)])
p_bonus = dh_p_two(sim_full, mean_obs)
mu_b, sd_b = sim_full.mean(), sim_full.std(ddof=1)
say(f"null chaînes complètes ({R_FULL} archives SRS de {N}) : "
    f"{mu_b:.4f} ± {sd_b:.4f}")
say(f"  z = {(mean_obs - mu_b) / sd_b:+.2f}   p simulé (bilatéral DH) = {p_bonus:.4f}"
    f"   (p tabulé audit : 0.044 ; E analytique 5.5698)")

R_HALF = 300 if FAST else 1000
sim_half = np.array([chain_stat(H, rng_b) for _ in range(R_HALF)])
mu_h, sd_h = sim_half.mean(), sim_half.std(ddof=1)
zb1, zb2 = (mean1 - mu_h) / sd_h, (mean2 - mu_h) / sd_h
z_all_b = (sim_half - mu_h) / sd_h
p_hom_b = dh_p_upper(np.abs(z_all_b[0::2] - z_all_b[1::2]), abs(zb1 - zb2))
say(f"moitiés : z1 = {zb1:+.2f}, z2 = {zb2:+.2f} (null moitié {mu_h:.4f}±{sd_h:.4f}) ; "
    f"homogénéité |z1-z2| = {abs(zb1 - zb2):.2f}, p ≈ {p_hom_b:.3f}")

say("puissance (témoin : rémanence — fraction f des tirages copient 6 numéros du précédent) :")
crit_lo_b = np.quantile(sim_full, 0.025)
crit_hi_b = np.quantile(sim_full, 0.975)
pow_b_lines = []
for f_rem in (0.05, 0.10):
    R_W = 15 if FAST else 40
    hits = sum(1 for _ in range(R_W)
               if not (crit_lo_b <= chain_stat(N, rng_b, reman_f=f_rem) <= crit_hi_b))
    pow_b_lines.append(f"f={f_rem}: {hits / R_W:.2f}")
    say(f"  {pow_b_lines[-1]}")

verdict_b = "signal degonfle (p simule > 0.05)" if p_bonus > 0.05 else \
    ("tient au niveau nominal" if p_bonus <= 0.044 else "affaibli")
say(f"VERDICT bonus : {verdict_b}")
if not NO_RECORD:
    lab.record(
        tokens["rep_bonus"], observed=mean_obs, p=p_bonus,
        power_at="temoin remanence o=6, alpha=0.05 bilateral : " + " ; ".join(pow_b_lines),
        verdict=verdict_b,
        notes=(f"null chaines {mu_b:.4f}±{sd_b:.4f} (R={R_FULL}, effectif de matches "
               f"aleatoire, paires adjacentes dependantes) vs z gaussien audit ; "
               f"moities {mean1:.4f} (z{zb1:+.2f}) / {mean2:.4f} (z{zb2:+.2f}), "
               f"homogeneite p~{p_hom_b:.3f} — a total fixe c'est tout ce que la "
               "moitie contre moitie peut dire pour un scalaire"))
    rows_txt = open(lab.LEDGER).readlines()
    obj = json.loads(rows_txt[-1]); obj["m_extra"] = 2
    rows_txt[-1] = json.dumps(obj, ensure_ascii=False) + "\n"
    open(lab.LEDGER, "w").writelines(rows_txt)

# ==========================================================================
# 10. Bilan Holm sur le registre entier
# ==========================================================================

say("\n" + "=" * 76)
say("10. BILAN")
say("=" * 76)
if not NO_RECORD:
    hh = lab.holm()
    if hh:
        sig = [r for r in hh if r["significant"]]
        say(f"holm() sur le registre entier : {len(sig)} significatif(s), "
            f"m_total = {hh[0]['m_total']}, "
            f"seuil le plus strict {0.05 / hh[0]['m_total']:.2e}")
        for r in hh[:5]:
            say(f"  {r['id']:32s} p={r['p']:.4g}  seuil={r['holm_threshold']:.2e}  "
                f"sig={r['significant']}")
say(f"\nterminé en {time.time() - T0:.0f} s"
    + (" (--fast/--no-record : rien n'est écrit au registre)" if NO_RECORD else ""))
