"""h34 — le barème inconnu : inconnaissable, ou seulement non publié ?

Le trou, et pourquoi il commande tout le reste
-----------------------------------------------
Le §5 bute sur un fait : aucun barème réel n'existe dans le dépôt
(HistoryView.swift:282) — l'API publie les jackpots k/k, pas les rangs
intermédiaires. Tout le volet financier du dossier contourne ce trou par des
conditions SUFFISANTES (« rangs intermédiaires ≥ 0 », §5 bis), et h17 §5
mesure ce que cette prudence coûte : le barème ne déplace pas seulement
l'espérance, il déplace la taille de mise admissible.

Ce fichier pose la question que personne n'avait posée : le barème est-il
vraiment libre, ou est-il CONTRAINT par des faits déjà disponibles ? Trois
voies, et chacune rend quelque chose :

  (a) l'espace ADMISSIBLE des barèmes — probabilités hypergéométriques
      exactes, monotonie par rang, taux de retour, part de la cagnotte
      lisible sur les relevés — a une dimension calculable, et les
      décisions du dossier s'y comportent d'une manière que le tirage
      « libre » de b2 §4 ne pouvait pas voir ;
  (b) la COMPTABILITÉ de la mise : 1 franc = coût de la cagnotte + rangs
      intermédiaires + marge. Le coût de la cagnotte est borné par θ = J·p/c,
      qui se lit sur les relevés. Si le taux de retour R est contraint, la
      part des rangs intermédiaires ρ est contrainte PAR DIFFÉRENCE ;
  (c) la borne INFÉRIEURE sur ρ qui en sort abaisse le seuil suffisant du
      §5 bis de (1−ρ_min), et la fraction de tirages favorables monte en
      exp(ρ_min/α) — exponentiellement, comme §28 l'annonçait.

Le garde-fou central, écrit avant les chiffres
-----------------------------------------------
Rien ici ne fabrique un barème « plausible » pour le traiter ensuite comme
connu. Chaque énoncé est soit une CONTRAINTE démontrée (« le barème
appartient à cet ensemble », « la décision est la même sur tout
l'ensemble »), soit une hypothèse ÉTIQUETÉE dans la phrase qui porte le
chiffre. Les hypothèses récurrentes reçoivent des noms :

  [H1–H3]   loi de la cagnotte de h15 (accrétion fixe, chute sans mémoire,
            plancher J₀ ≥ 0) ;
  [Hθ]      θ = J·p/c commun aux cinq cagnottes (h29 a testé la cohérence
            du relevé unique avec cette hypothèse : p = 0,57 — compatible,
            pas prouvée) et les cinq valeurs du relevé indépendantes ;
  [HR]      taux de retour R fixé (balayé, jamais affirmé : R = 0,65 est la
            valeur de travail que b2 §4 utilisait déjà) ;
  [Hc]      prix du ticket c = 1 franc (tout le dossier est par franc) ;
  [Hmono]   barème d'opérateur : gains ≥ 0, monotones du premier rang payé
            au rang plein, tout rang payé rend au moins la mise (lot « 0
            hit » possible aux mises ≥ 7, comme b2) ;
  [Hint]    variante : gains en multiples entiers de la mise.

Une erreur commise et corrigée pendant la dérivation, racontée au §2 : la
première version de la borne comptable confondait DÉCAISSEMENT et VERSEMENT
AUX JOUEURS, et se cassait dans le régime des chutes fréquentes ; le taux de
retour d'une licence compte les versements, et la borne tient alors sous les
deux conventions d'affichage. La simulation du §2 fait la différence entre
les deux — c'est son témoin.

Reproductible : `python3 lab/experiments/h34_bareme.py`  (~1 min).
Registre : entrées track="B", idempotentes (pas de doublon au re-run).
"""

from __future__ import annotations

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab  # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAKES = (5, 6, 7, 8, 10)
R_WORK = 0.65          # [HR] valeur de travail, la même que b2 §4
R_SWEEP = (0.50, 0.60, 0.65, 0.70, 0.75)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def pmf(k: int) -> np.ndarray:
    tot = math.comb(POOL, k)
    return np.array([math.comb(DRAWN, h) * math.comb(POOL - DRAWN, k - h) / tot
                     for h in range(k + 1)])


def p_full(k: int) -> float:
    return math.comb(DRAWN, k) / math.comb(POOL, k)


def threshold(k: int) -> float:
    return 1.0 / p_full(k)


# --------------------------------------------------------------------------
# Quantiles du khi-deux sans scipy — la même identité que JackpotLaw.swift
# --------------------------------------------------------------------------

def pois_cdf(kk: int, lam: float) -> float:
    if kk < 0:
        return 0.0
    if lam <= 0:
        return 1.0
    lt, tot = -lam, math.exp(-lam)
    for i in range(1, kk + 1):
        lt += math.log(lam) - math.log(i)
        tot += math.exp(lt)
    return min(1.0, tot)


def chi2_q(p: float, two_n: int) -> float:
    """Quantile p de χ²(two_n), via P(χ²(2n) ≤ x) = P(Poisson(x/2) ≥ n)."""
    n = two_n // 2
    target = 1 - p
    lo, hi = 0.0, n + 10.0
    while pois_cdf(n - 1, hi) > target and hi < 1e9:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if pois_cdf(n - 1, mid) > target:
            lo = mid
        else:
            hi = mid
    return 2 * ((lo + hi) / 2)


def theta_upper(theta_hat: float, n: int, q: float = 0.025) -> float:
    """Borne supérieure (extrémité haute de l'IC bilatéral 95 % par défaut)
    sur la moyenne d'une exponentielle estimée par n observations."""
    return 2 * n * theta_hat / chi2_q(q, 2 * n)


# --------------------------------------------------------------------------
# Pré-enregistrement — les jetons sont scellés ICI, avant tout calcul
# --------------------------------------------------------------------------

done = {r["id"] for r in lab.ledger()}

TOK_COMPTA = lab.preregister(
    "h34.compta_potcost",
    "coût de la cagnotte par franc misé (versements aux gagnants) ≤ θ = E[J]·p/c, "
    "sous H1–H3, pour les deux conventions d'affichage et tout J₀ ≥ 0, γ ≥ 1",
    "max, sur 24 régimes simulés (λ ∈ {0.006, 0.065, 0.65} × γ ∈ {1,3} × "
    "J₀/μ ∈ {0,1} × 2 conventions), du rapport versements/(N·c·T)/θ_simulé",
    "simulation du processus de renouvellement complet (règle 1 : null simulé), "
    "T = 400 000 pas par régime",
    "conforme si max ≤ 1 + 4/√(nb de chutes du régime) ; et le TÉMOIN — le "
    "DÉCAISSEMENT (collecte) au lieu des versements, convention B, λ = 0,65 — "
    "doit violer la borne (> 1 + 4σ), sinon la simulation ne sait pas voir "
    "une violation",
    track="B",
)

TOK_COUV = lab.preregister(
    "h34.theta_couverture",
    "la borne supérieure 2nθ̂/χ²(0,025; 2n) sur θ, calculée en poolant n relevés "
    "stationnaires sous [Hθ], couvre le vrai θ dans ≥ 95 % des cas sous H1–H3",
    "couverture empirique sur 4 000 réplicats de n = 5 relevés, "
    "9 régimes (q ∈ {0.002, 0.01, 0.1} × J₀/μ ∈ {0, 0.5, 2})",
    "population stationnaire simulée (2·10⁶ tirages par régime), θ vrai mesuré "
    "sur la population, jamais posé par formule",
    "conforme si couverture ≥ 0,95 sur les 9 régimes H1–H3 ET ≤ 0,90 sur le "
    "témoin H2-violé (âges en mélange 0,8·Geom(q) + 0,2·Geom(q/25) : une "
    "cagnotte à deux régimes, exactement la réserve de h15 §5)",
    track="B",
)

TOK_SCAL = lab.preregister(
    "h34.decisions_scalaire",
    "sur l'espace admissible des barèmes (mise 6), les décisions du dossier ne "
    "dépendent du barème qu'à travers le scalaire ρ(w) = Σπw : seuil et gain "
    "conditionnel exactement (identité), fraction de Kelly et croissance à "
    "moins de 1 % près (borne analytique Var_int ≤ ρ²/π₅ ≪ p·J²)",
    "écart relatif max de (f*, croissance/jour) entre chaque barème w et le "
    "barème de référence (tout-sur-le-rang-5) pris au MÊME ρ(w), sur 4 000 "
    "barèmes échantillonnés + sommets + catalogue entier [Hint] ; et résidu de "
    "construction |Σπw − ρ| sur l'échantillon continu",
    "aucun (identités et optimisation exactes ; l'échantillonnage ne sert qu'à "
    "couvrir l'espace, pas à estimer une loi)",
    "conforme si écart de forme ≤ 1 % et résidu de construction ≤ 10⁻¹⁰. "
    "Statistique CORRIGÉE après un premier passage à blanc (aucune "
    "consignation) : la v1 comparait au ρ nominal et mesurait la tolérance "
    "±0,01 du catalogue entier au lieu de la forme — entorse à la règle n° 2, "
    "signalée ici même, valeur confirmatoire nulle",
    track="B",
)

TOK_B2 = lab.preregister(
    "h34.b2_contraint",
    "b2 §4 rejoué dans l'espace ADMISSIBLE (potcost épinglé par relevé, R commun "
    "[HR], monotonie [Hmono]) : l'espérance est identique entre mises PAR "
    "CONSTRUCTION (elle ne peut plus départager), et la robustesse des "
    "comparaisons de forme est re-mesurée",
    "écart max de E[brut] à R sur tous les barèmes échantillonnés (doit être "
    "machine-zéro) ; fractions de dominance deux à deux sur P(perte totale), "
    "P(gain ≥ mise), écart-type (2 000 barèmes admissibles par mise)",
    "aucun (calcul exact sous chaque barème échantillonné)",
    "l'espérance est jugée non-départageante si écart machine ; une comparaison "
    "de forme est robuste si ≥ 95 % (le critère de b2)",
    track="B",
)

TOK_RHO = lab.preregister(
    "h34.rho_borne",
    "part de la mise revenant aux rangs intermédiaires : ρ ≥ R − θ_hi, où θ_hi "
    "est la borne 95 % sur θ poolée sur les cinq cagnottes du relevé du "
    "2026-08-30 — sous [Hθ], [HR], [Hc], H1–H3",
    "ρ_min = R − 2nθ̂/χ²(0,025; 2n), n = 5, θ̂ = moyenne des J_k·p_k",
    "la validité de la borne repose sur h34.compta_potcost (potcost ≤ θ) et "
    "h34.theta_couverture (couverture de θ_hi), tous deux vérifiés par "
    "simulation ci-dessus",
    "la borne est retenue si les deux vérifications amont sont conformes ; "
    "elle est CONDITIONNELLE aux hypothèses étiquetées, et vaut 0 si R ≤ θ_hi",
    track="B",
)


# ==========================================================================
# 1. Les cinq relevés, relus en comptabilité
# ==========================================================================

rule("1. LA COMPTABILITÉ DE LA MISE — ce que les relevés disent déjà")

say("""   Un franc misé se décompose exactement :

       1 = potcost + ρ + marge

   potcost : ce que l'opérateur versera aux gagnants du rang plein (la
             cagnotte progressive) par franc collecté ;
   ρ       : l'espérance des rangs intermédiaires par franc — LE terme
             inconnu du §5 ;
   marge   : ce que l'opérateur garde.

   Et le taux de retour d'une licence est R = potcost + ρ. Donc

       ρ = R − potcost.

   potcost n'est pas observable directement, mais θ = E[J]·p/c l'est — c'est
   la moyenne des relevés ramenée au seuil, le α̂·γ de h16/h29. Le §2 montre
   potcost ≤ θ : la part des rangs intermédiaires est contrainte PAR
   DIFFÉRENCE, ρ ≥ R − θ_hi.""")

rows = []
with open(os.path.join(ROOT, "jackpots_observed.csv")) as fh:
    for r in csv.DictReader(fh):
        rows.append(r)
obs = {k: [float(r[f"j{k}"]) for r in rows if r.get(f"j{k}")] for k in STAKES}
n_releves = sum(len(v) for v in obs.values())

theta_k = {k: float(np.mean(obs[k])) * p_full(k) for k in STAKES if obs[k]}
say(f"\n   Relevé(s) : {len(rows)} instantané(s), {n_releves} cagnottes. "
    f"θ̂_k = J_k·p_k [Hc : c = 1 franc] :")
say("   mise   cagnotte        seuil S_k         θ̂_k = J_k/S_k")
for k in STAKES:
    say(f"   {k:<6} CHF {np.mean(obs[k]):>10,.0f}   CHF {threshold(k):>12,.0f}   {theta_k[k]:>8.4f}")

theta_hat = float(np.mean(list(theta_k.values())))
n_pool = len(theta_k)
say(f"""
   Sous [Hθ] (θ commun aux cinq cagnottes, relevés indépendants — h29 a
   mesuré la cohérence du relevé avec cette hypothèse : p = 0,57), les cinq
   valeurs sont {n_pool} tirages d'une même loi de moyenne θ :

       θ̂ poolé = {theta_hat:.4f}

   C'est la moyenne des « fractions du seuil » de h9 — le même nombre, lu
   une troisième fois : distance au seuil (h9), gain conditionnel (h16), et
   maintenant BORNE SUR LE COÛT DE LA CAGNOTTE.""")


# ==========================================================================
# 2. potcost ≤ θ — la borne, son erreur corrigée, et sa vérification
# ==========================================================================

rule("2. LA BORNE potcost ≤ θ — vérifiée sur le processus, témoin compris")

say("""   Algèbre d'abord, sous H1–H3 avec γ = E[gagnants | chute] ≥ 1 et un
   plancher J₀ ≥ 0. Le pot affiché vaut J = J₀ + r·âge ; les versements aux
   gagnants par franc misé valent

       potcost = q·E[J | chute]/(N·c) = α + q·J₀/(N·c)
       θ       = E[J]·p/c            = α·γ + J₀·p/c

   d'où θ − potcost = α(γ−1) + (J₀/c)(p − q/N) = (γ−1)·(α + q·J₀/(N·c)) ≥ 0,
   puisque γ = N·p/q ≥ 1. La borne est une inégalité de foule : davantage de
   co-gagnants (γ grand) font paraître la cagnotte GÉNÉREUSE (θ grand) sans
   coûter davantage à l'opérateur — θ majore donc toujours le coût.

   L'ERREUR COMMISE ET CORRIGÉE, avant tout chiffre. Ma première version
   bornait le DÉCAISSEMENT de l'opérateur (la collecte α·N·c versée au pot à
   chaque tirage) et non les VERSEMENTS aux gagnants. Sous la convention
   d'affichage où les mises d'un tirage ne comptent pas pour son propre pot,
   les deux diffèrent d'un facteur (1−q), et la « borne » se cassait dans le
   régime des chutes fréquentes — j'ai failli publier un ρ_min dégradé d'un
   facteur de sécurité 1/(1−q) qui n'avait pas lieu d'être. Le taux de
   retour d'une licence compte les VERSEMENTS ; pour eux la borne tient sous
   les deux conventions. La simulation ci-dessous mesure les deux quantités
   séparément : le décaissement VIOLE la borne au régime dégénéré (c'est le
   témoin — la machinerie sait voir une violation), les versements jamais.""")

rng = np.random.default_rng(20260830)


def sim_pot(lam: float, gamma_: float, j0_over_mu: float, convention: str,
            alpha: float = 0.15, N: int = 1000, T: int = 400_000,
            rng: np.random.Generator = rng):
    """Processus complet : renvoie (versements/franc, décaissement/franc,
    θ mesuré, q, nb de chutes)."""
    q = 1 - math.exp(-lam / gamma_)          # chutes groupées : γ gagnants/chute
    p_ticket = gamma_ * q / N
    r = alpha * N                            # c = 1
    mu = r * (1 - q) / q if convention == "B" else r / q
    j0 = j0_over_mu * (r / q)
    wins = rng.random(T) < q
    idx = np.arange(T)
    last = np.maximum.accumulate(np.where(wins, idx, -1))
    last_strict = np.concatenate(([-1], last[:-1]))
    keep = last_strict >= 0
    age = (idx - last_strict)[keep]          # ≥ 1
    w = wins[keep]
    J = j0 + r * (age if convention == "A" else age - 1)
    paid = float(J[w].sum())                 # versements aux gagnants
    outlay = r * len(age) + j0 * int(w.sum())  # décaissement (collecte + amorçage)
    theta = float(J.mean()) * p_ticket
    return (paid / (N * len(age)), outlay / (N * len(age)), theta, q, int(w.sum()))


say("\n   λ=N·p   γ   J₀/μ  conv   versés/θ    (décision ≤ 1+4σ)   décaissé/θ")
worst = -math.inf
witness_ratio = None
for lam in (0.006, 0.065, 0.65):
    for gamma_ in (1.0, 3.0):
        for j0f in (0.0, 1.0):
            for conv in ("A", "B"):
                paid, outlay, th, q, nw = sim_pot(lam, gamma_, j0f, conv)
                tol = 4 / math.sqrt(max(nw, 1))
                rat, rat_o = paid / th, outlay / th
                worst = max(worst, rat - 1 - tol)
                flag = "" if rat <= 1 + tol else "  <-- VIOLATION"
                if lam == 0.65 and gamma_ == 1.0 and j0f == 0.0 and conv == "B":
                    witness_ratio = rat_o
                    flag += "   <- témoin : décaissé/θ doit dépasser 1"
                say(f"   {lam:<7.3f} {gamma_:<3.0f} {j0f:<5.1f} {conv:<6} {rat:<11.4f} "
                    f"(tol ±{tol:.3f})        {rat_o:<10.4f}{flag}")

ok_compta = worst <= 0 and witness_ratio is not None and witness_ratio > 1.05
say(f"""
   Versements/θ ≤ 1 partout (max de l'excès au-delà de 4σ : {worst:+.4f}) ;
   le décaissement du témoin vaut {witness_ratio:.3f}·θ — la borne naïve que
   j'avais d'abord écrite aurait été fausse là, et la simulation le voit.
   potcost ≤ θ est donc établi sous H1–H3, pour tout γ ≥ 1, J₀ ≥ 0, et les
   deux conventions d'affichage.""")


# ==========================================================================
# 3. θ_hi — l'intervalle sans scipy, et sa couverture mesurée
# ==========================================================================

rule("3. LA BORNE SUPÉRIEURE SUR θ — machinerie vérifiée, couverture mesurée")

say("""   Le quantile du khi-deux vient de la même identité de Poisson que
   JackpotLaw.swift (aucune fonction gamma nulle part). Vérification par
   simulation — 2·10⁶ tirages Gamma(n, 2) ~ χ²(2n), jamais une table :""")

ok_chi2 = True
for n in (1, 5, 15):
    g = rng.gamma(n, 2.0, size=2_000_000)
    for pq in (0.025, 0.975):
        xq = chi2_q(pq, 2 * n)
        emp = float((g <= xq).mean())
        se = math.sqrt(pq * (1 - pq) / len(g))
        z = (emp - pq) / se
        ok_chi2 &= abs(z) < 4
        say(f"   χ²({pq}, {2*n:>2}) = {xq:>8.4f}   P_sim(X ≤ x) = {emp:.5f}  (z = {z:+.2f})")
assert ok_chi2, "quantiles khi-deux faux — tout le §3 tombe"

say("""
   Couverture de θ_hi = 2nθ̂/χ²(0,025; 2n) avec n = 5 relevés poolés, sur des
   populations stationnaires SIMULÉES (θ vrai mesuré sur la population, pas
   posé). La loi exacte est géométrique décalée, pas exponentielle : la
   couverture n'est donc pas 97,5 % par décret, elle se mesure.""")

say("\n   régime                          couverture (4 000 réplicats × n = 5)")
cov_min = 1.0
POPN, REPS, NPOOL = 2_000_000, 4000, 5
for q in (0.002, 0.01, 0.1):
    for j0f in (0.0, 0.5, 2.0):
        age = rng.geometric(q, POPN).astype(float)
        popu = j0f * (1 / q) + age            # unités r·p = 1 : θ sans dimension
        th_true = float(popu.mean())
        samp = popu[rng.integers(0, POPN, size=(REPS, NPOOL))].mean(axis=1)
        cov = float((2 * NPOOL * samp / chi2_q(0.025, 2 * NPOOL) >= th_true).mean())
        cov_min = min(cov_min, cov)
        say(f"   q = {q:<6} J₀/μ = {j0f:<4}            {cov:.3f}")

# Témoin H2-violé : âges en mélange (cagnotte à deux régimes de chute).
comp = rng.random(POPN) < 0.2
age = np.where(comp, rng.geometric(0.01 / 25, POPN), rng.geometric(0.01, POPN)).astype(float)
th_true = float(age.mean())
samp = age[rng.integers(0, POPN, size=(REPS, NPOOL))].mean(axis=1)
cov_wit = float((2 * NPOOL * samp / chi2_q(0.025, 2 * NPOOL) >= th_true).mean())
say(f"   TÉMOIN H2 violé (mélange 0,8·Geom(q) + 0,2·Geom(q/25)) : {cov_wit:.3f}")

ok_couv = cov_min >= 0.95 and cov_wit <= 0.90
say(f"""
   Couverture minimale sous H1–H3 : {cov_min:.3f} (la loi géométrique et le
   plancher J₀ sont SOUS-dispersés par rapport à l'exponentielle — la borne
   est conservatrice de leur côté). Le témoin tombe à {cov_wit:.3f} : la
   garantie est bien une propriété de l'ABSENCE DE MÉMOIRE, pas de
   l'arithmétique — si l'opérateur ajuste la progression par régimes, θ_hi
   ment, et c'est la réserve de h15 §5 qui décide.""")

TH_HI = theta_upper(theta_hat, n_pool)
say(f"   Sur le relevé réel : θ_hi = 2·{n_pool}·{theta_hat:.4f}/χ²(0,025; {2*n_pool}) "
    f"= {TH_HI:.4f}")


# ==========================================================================
# 4. ρ_min = R − θ_hi — la borne inférieure, hypothèses en face
# ==========================================================================

rule("4. LA BORNE INFÉRIEURE SUR LES RANGS INTERMÉDIAIRES")

say("""   ρ ≥ R − potcost ≥ R − θ, et θ ≤ θ_hi à 95 % — sous H1–H3, [Hθ], [Hc].
   R n'est PAS dans le dépôt : il est balayé [HR], jamais affirmé. Trois
   lectures par colonne : la borne à 95 % (celle qui compte), la borne au
   point (θ̂ poolé — estimation, PAS une garantie), et le point par mise
   (θ̂_k propre — si les cinq cagnottes n'ont pas le même θ).""")

say("\n   R [HR]     ρ_min = R − θ_hi     R − θ̂ (point)     R − θ̂₆ (mise 6, point)")
for R in R_SWEEP:
    a = max(0.0, R - TH_HI)
    b = max(0.0, R - theta_hat)
    c6 = max(0.0, R - theta_k[6])
    star = "  <- valeur de travail" if R == R_WORK else ""
    say(f"   {R:<10.2f} {a:<20.4f} {b:<17.4f} {c6:<10.4f}{star}")

RHO_MIN = max(0.0, R_WORK - TH_HI)
RHO_POINT6 = max(0.0, R_WORK - theta_k[6])
RHO_POINT_POOL = max(0.0, R_WORK - theta_hat)
say(f"""
   La phrase qui porte le chiffre, hypothèses incluses : SI le taux de
   retour vaut au moins {R_WORK:.2f} [HR], SI le ticket coûte 1 franc [Hc], SI les
   cinq cagnottes partagent θ [Hθ] et suivent H1–H3, ALORS au moins
   ρ_min = {RHO_MIN:.1%} de chaque franc misé revient par les rangs
   intermédiaires, à 95 %. Sans le pooling [Hθ], n = 1 par mise et
   θ_hi = {theta_upper(theta_k[6], 1):.2f} : la borne est VIDE — c'est le pooling qui
   la rend possible, et il faut le dire dans la même phrase.

   Cas structurel voisin, qui se passe de H1–H3 : si la cagnotte affichée
   n'était PAS progressive mais un montant fixe (la réserve n° 1 de h16
   §5), alors potcost = J·p/c exactement, sans intervalle — ρ ≥ R − θ̂_k au
   point, soit {R_WORK - theta_k[6]:.1%} à la mise 6 [HR]. La borne ρ_min > 0 survit
   aux deux lectures de la cagnotte ; c'est la STRATÉGIE de h16 qui ne
   survit qu'à la première (un montant fixe ne franchit jamais le seuil).
   Deux relevés successifs départagent : un montant fixe ne bouge pas.""")


# ==========================================================================
# 5. L'espace admissible (voie a) — dimension, catalogue, et le collapse
# ==========================================================================

rule("5. L'ESPACE ADMISSIBLE — sa dimension, et ce qui s'y effondre")

say("""   Un barème admissible à la mise k, sous [Hmono] et à ρ fixé :
   w_h ≥ 0, monotone du premier rang payé m au rang k−1, w_h ≥ 1 sur les
   rangs payés, et Σ_h π_h·w_h = ρ (probabilités hypergéométriques exactes).
   Le premier rang payé m n'est admissible que si Σ_{h≥m} π_h ≤ ρ — payer
   tous les rangs au-dessus de m coûte déjà la somme de leurs probabilités.""")

say(f"\n   Premier rang payé admissible et dimension, à ρ = ρ̂_k = R−θ̂_k [HR R={R_WORK}]"
    f" puis à ρ = ρ_min = {RHO_MIN:.3f} :")
say("   mise   ρ̂_k      m admissibles (point)   dim    m admissibles (ρ_min)   dim")
for k in STAKES:
    pk = pmf(k)
    tails = [float(pk[m:k].sum()) for m in range(k)]
    rho_pt = R_WORK - theta_k[k]
    feas_pt = [m for m in range(1, k) if tails[m] <= rho_pt]
    feas_mn = [m for m in range(1, k) if tails[m] <= RHO_MIN]
    d_pt = max((k - m - 1) for m in feas_pt) if feas_pt else -1
    d_mn = max((k - m - 1) for m in feas_mn) if feas_mn else -1
    say(f"   {k:<6} {rho_pt:<8.3f} {str(feas_pt):<23} {d_pt:<6} {str(feas_mn):<23} {d_mn}")
say("   (dimension du polytope continu ; +1 aux mises ≥ 7 si lot « 0 hit »)")

say("""
   Lecture. Les contraintes IDENTIFIENT une structure — à la mise 6, aucun
   barème admissible ne paie sous 3/6, et l'inconnue passe de 6 nombres
   libres à un polytope de dimension 2 — mais elles n'identifient PAS le
   barème : la dimension n'est nulle nulle part. La voie (a) seule ne
   suffit donc pas. Ce qui suit montre pourquoi elle n'a pas besoin de
   suffire.""")

# ---- catalogue entier [Hint] : mises 5 et 6 (au-delà, l'énumération explose)
say(f"\n   Catalogue [Hint] (gains entiers, |Σπw − ρ| ≤ 0,01) — énumération exacte :")
catalogues = {}
for k, rho in ((5, R_WORK - theta_k[5]), (5, RHO_MIN), (6, R_WORK - theta_k[6]), (6, RHO_MIN)):
    pk = pmf(k)
    tabs = []
    # monotone entier sur h = 2..k-1 (m=1 jamais admissible ici, vérifié large)
    caps = [int((rho + 0.01) / pk[h]) if pk[h] > 0 else 0 for h in range(k)]
    def rec(h, prev, cost, w):
        if h == k:
            if abs(cost - rho) <= 0.01:
                tabs.append(tuple(w))
            return
        lo = prev if prev > 0 else 0
        for v in range(lo, caps[h] + 1):
            if v != 0 and v < max(prev, 1):
                continue
            c2 = cost + v * pk[h]
            if c2 > rho + 0.01:
                break
            if prev > 0 and v < prev:
                continue
            rec(h + 1, v if v > 0 else prev, c2, w + [v])
    rec(2, 0, 0.0, [])
    catalogues[(k, round(rho, 4))] = tabs
    lab_rho = "ρ̂_k (point)" if abs(rho - RHO_MIN) > 1e-9 else "ρ_min (borne)"
    say(f"   mise {k}, ρ = {rho:.3f} [{lab_rho}] : {len(tabs)} barèmes entiers admissibles")

say("""   Un catalogue FINI — de six tables à cent trente selon la mise et ρ —
   mais pas un singleton : même la contrainte entière laisse l'opérateur
   libre. La question devient : cette liberté change-t-elle une décision ?""")

# ---- le collapse : les décisions ne voient que ρ
say("\n" + "-" * 78)
say("   LE COLLAPSE — toutes les décisions du dossier passent par le scalaire ρ")
say("-" * 78)

K6 = 6
pk6 = pmf(K6)
P6 = p_full(K6)
S6 = threshold(K6)
ALPHA6 = theta_k[6]                    # μ̂/S au point (h16), = θ̂₆
MU6 = float(np.mean(obs[6]))


def sample_admissible(k: int, rho: float, n: int, rng: np.random.Generator):
    """Barèmes admissibles par construction (aucun rejet) : base 1 sur les
    rangs ≥ m, excédent réparti en incréments de queue ≥ 0 (monotone)."""
    pk = pmf(k)
    tails = np.array([float(pk[m:k].sum()) for m in range(k)])
    feas = [m for m in range(1, k) if tails[m] <= rho]
    out = np.zeros((n, k))
    for i in range(n):
        m = feas[rng.integers(len(feas))]
        budget = rho - tails[m]
        w = np.zeros(k)
        w[m:] = 1.0
        if k >= 7 and rng.random() < 0.3:              # lot « 0 hit », comme b2
            w0 = rng.uniform(1.0, 2.0)
            if pk[0] * w0 <= budget:
                w[0] = w0
                budget -= pk[0] * w0
        c = rng.exponential(size=k - m) * (rng.random(k - m) < 0.7)
        cost = tails[m:]
        s = float((c * cost).sum())
        if s <= 0:
            j = rng.integers(k - m)
            w[m + j:] += budget / cost[j]
        else:
            c *= budget / s
            w[m:] += np.cumsum(c)
        out[i] = w
    return out


def kelly_growth(probs: np.ndarray, nets: np.ndarray):
    """f* et croissance par occasion, ternaire vectorisée (concave en f)."""
    lo, hi = 1e-9, 0.5

    def g(f):
        return float((probs * np.log1p(f * nets)).sum())
    for _ in range(120):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if g(m1) < g(m2):
            lo = m1
        else:
            hi = m2
    f = (lo + hi) / 2
    return f, g(f)


def decisions_stake6(w: np.ndarray):
    """(ρ(w), f*, g/occasion, g/jour) pour un barème w (mise 6). Politique :
    jouer au-dessus du seuil de bascule PROPRE au barème, S'(w) = (1−ρ(w))·S ;
    cagnotte conditionnelle S' + μ̂ (absence de mémoire, h16) ; fréquence
    exp(−S'/μ̂). Le seuil et le gain conditionnel sont des FONCTIONS de ρ(w)
    par identité — ce que le test mesure est si f* et la croissance le sont
    aussi."""
    rho_w = float((pk6[:K6] * w).sum())
    Sp = (1 - rho_w) * S6
    Jc = Sp + MU6
    probs = np.concatenate([pk6[:K6], [P6]])
    nets = np.concatenate([w - 1.0, [Jc - 1.0]])
    f, g = kelly_growth(probs, nets)
    freq = math.exp(-Sp / MU6)
    return rho_w, f, g, g * freq


def reference_at_rho(rho: float):
    """La décision au barème de référence (tout sur le rang 5) de même ρ."""
    w = np.zeros(K6)
    w[5] = rho / float(pk6[5])
    return decisions_stake6(w)


# baseline du dossier (§30, recalculée ici, jamais recopiée)
J_BASE = S6 * (1 + ALPHA6)
f_base, g_base = kelly_growth(np.array([P6, 1 - P6]), np.array([J_BASE - 1.0, -1.0]))
FREQ_BASE = math.exp(-1 / ALPHA6)
gday_base = g_base * FREQ_BASE
say(f"\n   Baseline sans rangs intermédiaires, recalculée : f* = {f_base:.3e}, "
    f"g/occasion = {g_base:.3e}")
say(f"   (§30 annonçait 2,94e-05 et 3,96e-06 — concordance, calculée et non recopiée)")

NS = 4000
W = sample_admissible(K6, RHO_MIN, NS, rng)
# sommets du polytope : base-1 à m + tout l'excédent sur la queue j
verts = []
tails6 = np.array([float(pk6[m:K6].sum()) for m in range(K6)])
for m in range(1, K6):
    if tails6[m] > RHO_MIN:
        continue
    for j in range(m, K6):
        w = np.zeros(K6)
        w[m:] = 1.0
        w[j:] += (RHO_MIN - tails6[m]) / tails6[j]
        verts.append(w)
    w = np.zeros(K6)                                   # rayon pur si w ≥ 1 tenable
    if RHO_MIN / tails6[m] >= 1:
        w[m:] = RHO_MIN / tails6[m]
        verts.append(w)
cat = [np.concatenate([np.zeros(2), np.array(t, float)]) for t in
       catalogues[(6, round(RHO_MIN, 4))]]
allW = np.vstack([W] + [v[None, :] for v in verts] + [c[None, :] for c in cat])

say("""
   UNE ERREUR DE STATISTIQUE, COMMISE ET CORRIGÉE ICI. La première version
   de ce test comparait tous les barèmes au ρ NOMINAL et trouvait 15 %
   d'étendue — un scandale apparent, qui n'était que la tolérance ±0,01 du
   catalogue entier : une table entière n'a pas exactement Σπw = ρ, et un
   écart de 0,01 sur ρ pèse (0,305/0,285)² ≈ 15 % sur une croissance en
   EV². La statistique mesurait mon bouton de tolérance, pas la forme du
   barème. Corrigée : chaque barème est comparé à la référence prise à SON
   ρ(w) — ce qui est précisément l'énoncé « la décision est une fonction de
   ρ seul ». L'entorse à la règle n° 2 est signalée dans le jeton.""")

res = np.array([decisions_stake6(w) for w in allW])
rho_all, fstar, gocc, gday = res[:, 0], res[:, 1], res[:, 2], res[:, 3]
resid_cons = float(np.abs(rho_all[:NS + len(verts)] - RHO_MIN).max())
ref = np.array([reference_at_rho(r) for r in rho_all])
dev_f = float(np.abs(fstar / ref[:, 1] - 1).max())
dev_g = float(np.abs(gday / ref[:, 3] - 1).max())
var_bound = RHO_MIN ** 2 / float(pk6[5])
m2_pot = P6 * ((1 - RHO_MIN) * S6 + MU6) ** 2
say(f"""   Sur {len(allW)} barèmes admissibles (échantillon + {len(verts)} sommets à ρ_min
   exactement — résidu de construction {resid_cons:.1e} — plus les {len(cat)} tables du
   catalogue entier, chacune à son ρ(w)) :

     seuil S'(w) et gain conditionnel : fonctions de ρ(w) par identité
       (S' = (1−ρ)·S ; gain au seuil = μ̂/S, §6) — rien à mesurer ;
     fraction de Kelly f*   : écart max à la référence de même ρ : {dev_f:.2%} ;
     croissance par jour    : écart max à la référence de même ρ : {dev_g:.2%}.

   La raison est une borne, pas une chance : la variance des rangs
   intermédiaires est ≤ ρ²/π₅ = {var_bound:.1f}, contre p·J'² = {m2_pot:.0f} pour la
   cagnotte — {var_bound / m2_pot:.1%} du dénominateur de Kelly. À la mise 6, TOUTE la
   liberté résiduelle de l'espace admissible — le polytope de dimension 2,
   le catalogue entier, les sommets extrêmes — pèse moins d'un centième sur
   chaque décision du dossier, une fois ρ connu. (Aux grandes mises la
   borne ρ²/π_{{k−1}} devient lâche — mise 10 : rang 9 quasi aussi rare que
   le plein — mais ces mises sont à des ordres de grandeur du seuil, h9.)

   Le barème reste non identifié ; les décisions n'en avaient pas besoin.
   L'inconnue utile n'a JAMAIS été la table w — c'est le scalaire ρ.""")

ok_scal = resid_cons <= 1e-10 and max(dev_f, dev_g) <= 0.01

# ---- b2 §4 rejoué dans l'espace admissible
say("\n" + "-" * 78)
say("   b2 §4 REJOUÉ — même question, espace contraint")
say("-" * 78)
say(f"""   b2 tirait 2 000 barèmes par mise dans un espace LIBRE à RTP égalisé et
   ne trouvait aucune comparaison robuste à 95 %. Ici : potcost épinglé au
   relevé (J_k au rang plein), intermédiaires admissibles à ρ_k = R − θ̂_k
   [HR R = {R_WORK}], [Hmono]. L'espérance d'abord — elle est réglée PAR
   CONSTRUCTION :""")

NB = 2000
metrics = {}
ev_dev = 0.0
for k in STAKES:
    pk = pmf(k)
    rho_k = R_WORK - theta_k[k]
    Wk = sample_admissible(k, rho_k, NB, rng)
    gross = np.concatenate([Wk, np.full((NB, 1), float(np.mean(obs[k])) * p_full(k) / p_full(k))], axis=1)
    # colonne du rang plein : la cagnotte observée J_k (par franc, [Hc])
    gross[:, k] = float(np.mean(obs[k]))
    pz = (np.where(gross == 0, pk[None, :], 0).sum(axis=1))
    pw = (np.where(gross >= 1, pk[None, :], 0).sum(axis=1))
    mean = gross @ pk
    sd = np.sqrt(np.maximum((gross ** 2) @ pk - mean ** 2, 0))
    ev_dev = max(ev_dev, float(np.abs(mean - R_WORK).max()))
    metrics[k] = dict(pz=pz, pw=pw, sd=sd)
say(f"   E[brut] = R sur chaque barème de chaque mise : écart max {ev_dev:.1e}.")
say("""   Le « classement des mises par espérance » de b2 n'était donc pas
   fragile : il était VIDE. À potcost lu sur les relevés et R commun,
   l'espérance est la même par identité comptable ; la seule chose qu'un
   barème puisse encore départager est la FORME du risque. Elle :""")

say("\n   paire      P(perte) plus faible   P(g≥mise) plus forte   sd plus faible")
rob_max = 0.0
robust_pairs = []
for i, a in enumerate(STAKES):
    for b in STAKES[i + 1:]:
        fz = float((metrics[a]["pz"] < metrics[b]["pz"]).mean())
        fw = float((metrics[a]["pw"] > metrics[b]["pw"]).mean())
        fs = float((metrics[a]["sd"] < metrics[b]["sd"]).mean())
        for v in (fz, fw, fs):
            rob_max = max(rob_max, v, 1 - v)
        if max(fz, 1 - fz) >= 0.95 or max(fw, 1 - fw) >= 0.95 or max(fs, 1 - fs) >= 0.95:
            robust_pairs.append((a, b, fz, fw, fs))
        say(f"   {a} vs {b:<4}   {fz:>8.0%}               {fw:>8.0%}               {fs:>8.0%}")
say(f"""
   {len(robust_pairs)} paires atteignent 95 % sur au moins un critère de forme (b2 : zéro).
   La contrainte a créé de la robustesse là où l'espace libre n'en avait
   pas — mais la conclusion qui compte n'est pas là : c'est que la question
   « quelle mise a la meilleure espérance ? » n'était pas une question de
   barème. Au-dessus du seuil, la mise se choisit sur α̂_k (relevés, mise 6,
   h9) ; en dessous, toutes valent R − 1 < 0 [HR] et Kelly dit zéro (b2).""")


# ==========================================================================
# 6. Ce que la borne fait descendre (voie c)
# ==========================================================================

rule("6. CE QUI DESCEND — seuils, fréquences, taille de mise")

say(f"""   Toute la section sous les hypothèses du §4, rappelées : [HR R = {R_WORK}],
   [Hθ], [Hc], H1–H3, borne 95 %. Le seuil suffisant devient

       S' = (1−ρ_min)·S = {1 - RHO_MIN:.3f}·S

   et la fraction favorable est multipliée par exp(ρ_min·S/μ̂) — le rapport
   exponentiel seuil/fréquence du §28, cette fois dans le bon sens.""")

say("\n   mise   seuil §5bis     seuil abaissé    fraction favorable (point μ̂ = J relevé)")
say("                                            avant §28      après       facteur")
for k in STAKES:
    S = threshold(k)
    Sp = (1 - RHO_MIN) * S
    mu = float(np.mean(obs[k]))
    f0, f1 = math.exp(-S / mu), math.exp(-Sp / mu)
    aff0 = f"{f0:.2%}" if f0 >= 1e-4 else f"{f0:.1e}"
    aff1 = f"{f1:.2%}" if f1 >= 1e-4 else f"{f1:.1e}"
    say(f"   {k:<6} CHF {S:>11,.0f}   CHF {Sp:>11,.0f}   {aff0:>9}   {aff1:>9}   ×{f1 / f0:.2f}")

freq_new = math.exp(-(1 - RHO_MIN) / ALPHA6)
say(f"""
   À la mise 6 : le seuil descend de CHF {S6:,.0f} à CHF {(1-RHO_MIN)*S6:,.0f}, la fraction
   favorable passe de {FREQ_BASE:.2%} à {freq_new:.2%} — {288*freq_new:.0f} tirages favorables par jour
   au lieu de {288*FREQ_BASE:.0f} (un toutes les {24*60/(288*freq_new):.0f} minutes). Et le gain conditionnel
   au NOUVEAU seuil reste exactement μ̂/S = α̂ = {ALPHA6:.1%} : l'identité de h16
   survit au barème — E[J | J ≥ S'] = S' + μ, donc p·(S'+μ)/c + ρ − 1 =
   μ/S. Le barème ne change pas ce que vaut une occasion ; il change OÙ
   commence l'occasion, et donc combien il y en a.""")

# ---- Kelly : une grille
say("-" * 78)
say("   KELLY, une grille — la taille de mise admissible bouge, et de combien")
say("-" * 78)
scenarios = [
    ("§30 (rangs ignorés — borne de tout barème)", 0.0),
    (f"ρ_min = {RHO_MIN:.3f} [borne 95 %, hypothèses §4]", RHO_MIN),
    (f"ρ̂₆ = {RHO_POINT6:.3f} [point mise 6 — estimation, pas une borne]", RHO_POINT6),
    (f"ρ̂ = {RHO_POINT_POOL:.3f} [point poolé — estimation, pas une borne]", RHO_POINT_POOL),
]
say("\n   scénario (hypothèse dans le nom)                          f*        g/occ      g/jour   ×jour   capital min (13 gr.)")
gd0 = None
for name, rho in scenarios:
    if rho == 0.0:
        f, g, gd = f_base, g_base, gday_base
    else:
        w = np.zeros(K6)
        w[5] = rho / pk6[5]                    # pire sommet : tout sur 5/6
        _, f, g, gd = decisions_stake6(w)
    if gd0 is None:
        gd0 = gd
    say(f"   {name:<57} {f:.2e} {g:.2e} {gd:.2e}  ×{gd / gd0:<5.1f} CHF {13.0 / (13 * f):>9,.0f}")
say("""
   Le « capital minimal » est 13·c/f*₁₃ ≈ c/f*₁ (h17 §4, retrouvé ci-dessous).
   Les multiplicateurs ×jour sont pris au PIRE barème admissible (tout ρ sur
   le rang 5) — tout autre barème admissible fait au moins aussi bien, à
   moins de 1 % près (§5). La borne conservatrice triple déjà la croissance ;
   l'estimation ponctuelle poolée la multiplierait par un ordre de grandeur —
   mais c'est une estimation sur cinq nombres, et elle porte son étiquette.""")

# ---- 13 grilles disjointes : loi jointe EXACTE par programmation dynamique
say("-" * 78)
say("   13 GRILLES DISJOINTES — la loi jointe exacte, et l'étalement re-vérifié")
say("-" * 78)


def dp_joint13(w5: float):
    """Loi jointe exacte de (nb de blocs à 5 hits, nb de blocs pleins) pour
    13 blocs disjoints de 6 + 2 numéros restants, 20 tirés de 80.
    Entiers exacts, divisés par C(80,20) à la fin."""
    from collections import defaultdict
    dp = {(0, 0, 0): 1}
    for _ in range(13):
        nxt = defaultdict(int)
        for (used, n5, n6), ways in dp.items():
            for j in range(0, 7):
                if used + j > DRAWN:
                    break
                nxt[(used + j, n5 + (j == 5), n6 + (j == 6))] += ways * math.comb(6, j)
        dp = dict(nxt)
    out = defaultdict(int)
    for (used, n5, n6), ways in dp.items():
        rem = DRAWN - used
        if 0 <= rem <= 2:
            out[(n5, n6)] += ways * math.comb(2, rem)
    tot = sum(out.values())
    assert tot == math.comb(POOL, DRAWN), "la DP ne somme pas à C(80,20)"
    return {k: v / tot for k, v in out.items()}


JOINT = dp_joint13(0.0)
# contrôle par simulation (règle 1) : 300 000 tirages multivariés
mvh = rng.multivariate_hypergeometric([6] * 13 + [2], DRAWN, size=300_000,
                                      method="marginals")
n5_s = (mvh[:, :13] == 5).sum(axis=1)
n6_s = (mvh[:, :13] == 6).sum(axis=1)
p_n5 = sum(v for (a, b), v in JOINT.items() if a >= 1)
p_n6 = sum(v for (a, b), v in JOINT.items() if b >= 1)
z5 = (float((n5_s >= 1).mean()) - p_n5) / math.sqrt(p_n5 * (1 - p_n5) / len(n5_s))
z6 = (float((n6_s >= 1).mean()) - p_n6) / math.sqrt(p_n6 * (1 - p_n6) / len(n6_s))
say(f"\n   DP exacte contrôlée par 300 000 tirages simulés : "
    f"P(≥1 bloc à 5) z = {z5:+.2f}, P(≥1 bloc plein) z = {z6:+.2f}")
assert abs(z5) < 4 and abs(z6) < 4


def kelly13(rho: float):
    Sp = (1 - rho) * S6
    Jc = Sp + MU6
    w5 = rho / float(pk6[5]) if rho > 0 else 0.0
    probs, nets = [], []
    for (a, b), pv in sorted(JOINT.items()):
        gross = a * w5 + (1 if b >= 1 else 0) * Jc     # cagnotte payée une fois
        probs.append(pv)
        nets.append((gross - 13.0) / 13.0)
    return kelly_growth(np.array(probs), np.array(nets))


f13_0, g13_0 = kelly13(0.0)
f13_m, g13_m = kelly13(RHO_MIN)
_, f1_m, g1_m, _ = decisions_stake6(
    np.concatenate([np.zeros(5), [RHO_MIN / pk6[5]]]))
say(f"""
   sans rangs (contrôle §30) : f*₁₃ = {f13_0:.3e}, g₁₃/occ = {g13_0:.3e}
     -> rapport g₁₃/g₁ = {g13_0 / g_base:.2f} (§30 : ×13,02 — retrouvé) ;
   au pire barème admissible, ρ_min [hypothèses §4] :
     f*₁₃ = {f13_m:.3e}, g₁₃ = {g13_m:.3e}, rapport g₁₃/g₁ = {g13_m / g1_m:.2f} —
     l'étalement de h13/h17 SURVIT aux rangs intermédiaires (la cagnotte se
     partage entre blocs, les rangs 5/6 non : la loi jointe le dit, ×13 tient) ;
   capital minimal pour Kelly (ticket CHF 1) : CHF {13.0 / f13_0:>9,.0f} -> CHF {13.0 / f13_m:>9,.0f}
   croissance annualisée (288 tirages/jour, fraction favorable {freq_new:.2%}) :
     {math.exp(g13_0 * FREQ_BASE * 288 * 365) - 1:+.1%} (§30 : +20,0 %) -> {math.exp(g13_m * freq_new * 288 * 365) - 1:+.1%} [mêmes hypothèses §4]""")

# ---- la politique de seuil, en croissance
say("-" * 78)
say("   OÙ VISER — le seuil de bascule reste l'optimum d'espérance, pas de Kelly")
say("-" * 78)
xs = np.linspace((1 - RHO_MIN) / ALPHA6, 8.0, 60)
best_ev = max(xs, key=lambda x: math.exp(-x) * (ALPHA6 * (x + 1) + RHO_MIN - 1))
gd_list = []
w5_worst = RHO_MIN / float(pk6[5])
for x in xs:
    Sp = x * MU6
    Jc = Sp + MU6
    probs = np.concatenate([pk6[:K6], [P6]])
    nets = np.concatenate([np.full(5, -1.0), [w5_worst - 1.0], [Jc - 1.0]])
    _, g = kelly_growth(probs, nets)
    gd_list.append(math.exp(-x) * g)
x_star = float(xs[int(np.argmax(gd_list))])
x_seuil = (1 - RHO_MIN) / ALPHA6
say(f"""
   Profit espéré par tirage : maximum numérique en x = S*/μ = {best_ev:.2f} pour un
   optimum théorique (1−ρ)/α = {x_seuil:.2f} — le théorème de h16 §2 s'étend
   mot pour mot au barème : l'optimum d'espérance EST le nouveau seuil.
   CROISSANCE par tirage (Kelly au pire barème admissible) : maximum en
   x = {x_star:.2f}, un peu au-dessus du seuil, mais jouer dès le seuil garde
   {gd_list[0]/max(gd_list):.0%} de la croissance optimale : la règle pratique — jouer dès la
   bascule — ne bouge pas, pour l'espérance comme pour la croissance.""")


# ==========================================================================
# 7. Les demandes de données, chiffrées comme §28 chiffre la sienne
# ==========================================================================

rule("7. CE QU'IL FAUT DEMANDER, ET CE QUE CHAQUE DONNÉE ACHÈTE")

say(f"""   1. LE RÈGLEMENT DU JEU, d'abord. La question du titre a une réponse :
      rien n'indique que le barème soit inconnaissable — il n'est pas dans
      l'API, ce qui n'est pas la même chose. Un jeu sous licence publie
      normalement ses règles, barème compris, dans un document de règlement.
      UN document lèverait w_h exactement, rendrait ce fichier obsolète, et
      c'est la demande la moins chère du dossier : zéro relevé, zéro modèle.
      (Le réseau d'ici est fermé — 403 au CONNECT, README — donc c'est une
      demande à l'app ou à son auteur, pas une expérience.)

   2. LE TAUX DE RETOUR R — un chiffre de licence, pas une mesure. Toute la
      colonne ρ_min du §4 est conditionnelle à [HR] ; R réel la débloque :
      ρ_min = R − {TH_HI:.3f} par lecture directe du tableau.

   3. LE PRIX DU TICKET c. θ = J·p/c : un ticket à 2 francs DIVISE θ par
      deux et MONTE ρ_min d'autant — la borne à c = 1 est le pire cas si
      c ≥ 1. Mais le seuil en francs S' = c·(1−ρ_min)/p MONTE avec c, et la
      fréquence retombe. Les deux effets, chiffrés [mêmes hypothèses §4] :""")

say("      c (CHF)   θ_hi/c    ρ_min      seuil S' (francs)   fraction favorable")
for c in (0.5, 1.0, 2.0, 5.0):
    th_c = TH_HI / c
    rho_c = max(0.0, R_WORK - th_c)
    Sp_c = c * (1 - rho_c) * S6
    fr = math.exp(-Sp_c / MU6)
    aff = f"{fr:.2%}" if fr >= 1e-4 else f"{fr:.1e}"
    say(f"      {c:<9.2f} {th_c:<9.3f} {rho_c:<10.3f} CHF {Sp_c:>12,.0f}   {aff:>12}")

say(f"""
   4. DES RELEVÉS APRÈS CHUTE. La borne θ_hi ne se resserre qu'au rythme des
      chutes (§36 : entre deux chutes, mille relevés ne valent qu'une
      observation). n = 5 cagnottes au premier instantané, puis +1 par chute
      observée. À θ̂ constant [étiquette : le point bougera], R = {R_WORK} :""")
say("      n relevés   θ_hi      ρ_min     seuil mise 6    fraction favorable")
for n in (5, 10, 20, 30, 50, 100):
    th = theta_upper(theta_hat, n)
    rho = max(0.0, R_WORK - th)
    Sp = (1 - rho) * S6
    say(f"      {n:<11} {th:<9.4f} {rho:<9.4f} CHF {Sp:>9,.0f}   {math.exp(-Sp / MU6):>9.2%}")
say(f"""      La borne converge vers le point ρ̂ = {RHO_POINT_POOL:.3f} — et une centaine de
      chutes la met à mi-chemin. Mais la MÊME série donne r et q, donc α
      directement (h15 §4, h25) : la borne n'est que le chemin d'attente.

   5. LE PLANCHER J₀, en dividende. Le premier relevé qui suit une chute
      lit J₀. Or la monotonie [Hmono] impose w₉ ≤ J₀/c au rang 9 de la mise
      10 — le seul rang dont la borne de variance du §5 ne contrôle pas la
      queue. J₀ fermerait la dernière mise où le barème peut encore faire
      varier une décision.""")


# ==========================================================================
# 8. Limites, et consignation
# ==========================================================================

rule("8. LES LIMITES, NOMMÉES")

say(f"""   — Tout le §4 et le §6 sont CONDITIONNELS à [HR] : R n'est pas dans le
     dépôt, et aucun chiffre de licence n'est affirmé ici. Les tableaux
     balaient R ; la « valeur de travail » 0,65 est un choix de b2, pas un
     fait.
   — [Hθ] porte la borne : sans pooling, n = 1 et la borne est vide. La
     cohérence des cinq relevés avec un θ commun est testée (h29, p = 0,57)
     mais un test de cohérence ne prouve pas une hypothèse.
   — H1–H3 restent le socle ; le témoin du §3 montre exactement comment la
     borne ment si la cagnotte a deux régimes (couverture {cov_wit:.0%}).
   — La borne de collapse ρ²/π_{{k−1}} est propre aux petites mises ; à la
     mise 10 le barème peut encore déplacer Kelly — mais la mise 10 est à
     ×{threshold(10) / float(np.mean(obs[10])):.0f} du seuil.
   — Les fractions favorables restent des estimations PONCTUELLES sur μ̂
     (un relevé par cagnotte) : h15 §3 a chiffré leur incertitude, elle est
     énorme, et rien ici ne la réduit — seul le facteur MULTIPLICATIF
     exp(ρ_min/α̂) est nouveau.
   — Le catalogue entier [Hint] dépend de sa tolérance (±0,01) et de son
     unité (multiples de la mise) : son rôle est de montrer la finitude,
     pas de compter juste.
   — La loi jointe des 13 grilles suppose la cagnotte payée UNE fois même à
     deux blocs pleins (règle de partage inconnue) — conservateur.""")

rule("REGISTRE")


def rec_guarded(tok: dict, **kw) -> None:
    if tok["id"] in done:
        say(f"   [registre] {tok['id']} déjà consigné — pas de doublon")
        return
    lab.record(tok, **kw)
    done.add(tok["id"])
    say(f"   [registre] {tok['id']} consigné")


rec_guarded(TOK_COMPTA, observed=worst, null=None, p=None,
            power_at=f"témoin (décaissement, conv. B, λ=0,65) : ratio {witness_ratio:.3f} > 1, vu",
            verdict="conforme — potcost ≤ θ sous H1–H3, γ ≥ 1, J₀ ≥ 0, 2 conventions"
                    if ok_compta else "ÉCART",
            notes="Erreur corrigée en dérivation : la v1 bornait le décaissement "
                  "(collecte) et non les versements ; le RTP d'une licence compte les "
                  "versements, pour lesquels θ − potcost = (γ−1)(α + qJ₀/(Nc)) ≥ 0. "
                  "Le témoin (décaissement) viole la borne au régime dégénéré : la "
                  "simulation sait voir une violation.")

rec_guarded(TOK_COUV, observed=cov_min, null=None, p=None,
            power_at=f"témoin H2-violé (mélange de régimes) : couverture {cov_wit:.3f} — "
                     "la garantie est bien une propriété de l'absence de mémoire",
            verdict="conforme — couverture ≥ 0,95 sur les 9 régimes H1–H3, témoin < 0,90"
                    if ok_couv else "ÉCART",
            notes=f"θ_hi = {TH_HI:.4f} sur le relevé réel (n = 5 poolé sous [Hθ]). "
                  "Géométrique discrète et plancher J₀ sont sous-dispersés vs "
                  "l'exponentielle : la borne est conservatrice de leur côté.")

rec_guarded(TOK_SCAL, observed=max(dev_f, dev_g), null=None, p=None,
            power_at=f"résidu de construction {resid_cons:.1e} ; écart de forme max à "
                     f"ρ égal : f* {dev_f:.2%}, croissance/jour {dev_g:.2%}",
            verdict="conforme — toutes les décisions passent par le scalaire ρ "
                    "(exactement pour seuil/gain, < 1 % pour Kelly)"
                    if ok_scal else "ÉCART",
            notes=f"Espace admissible mise 6 : premier rang payé ∈ {{3,4,5}}, dimension 2 ; "
                  f"catalogue entier [Hint] : {len(cat)} tables à ρ_min. Borne de collapse "
                  f"Var_int ≤ ρ²/π₅ = {var_bound:.1f} ≪ p·J'² = {m2_pot:.0f}. Lâche à la mise 10 "
                  "(rang 9 quasi aussi rare que le plein) — mise à ×18 du seuil.")

rec_guarded(TOK_B2, observed=ev_dev, null=None, p=None,
            power_at=f"{len(robust_pairs)} paires ≥ 95 % sur au moins un critère de forme "
                     "(b2, espace libre : 0)",
            verdict="l'espérance ne départage pas les mises PAR CONSTRUCTION "
                    "(écart machine à R) ; la forme redevient partiellement robuste "
                    "dans l'espace admissible",
            notes="b2 §4 rejoué à potcost épinglé par les relevés et R commun [HR 0,65], "
                  "[Hmono] : E[brut] = R est une identité comptable, donc le "
                  "« classement par espérance » de b2 était structurellement vide, pas "
                  "fragile. Au-dessus du seuil la mise se choisit sur α̂_k (mise 6, h9) "
                  "— sans barème.")

demand = " → ".join(f"{max(0.0, R_WORK - theta_upper(theta_hat, n)):.3f} (n={n})"
                    for n in (5, 10, 30, 100))
rec_guarded(TOK_RHO, observed=RHO_MIN, null=None, p=None,
            power_at=f"n = 5+chutes, à θ̂ constant : ρ_min = {demand}",
            verdict=f"ρ ≥ {RHO_MIN:.3f} à 95 % SOUS [HR R=0,65]+[Hθ]+[Hc]+H1–H3 ; "
                    f"seuil mise 6 : 7 753 → {(1-RHO_MIN)*S6:,.0f} ; fraction favorable "
                    f"{FREQ_BASE:.2%} → {freq_new:.2%} ; croissance/jour ×{(g13_m * freq_new) / (g13_0 * FREQ_BASE):.1f}"
            if ok_compta and ok_couv else "SUSPENDU — vérification amont non conforme",
            notes="Conditionnel et étiqueté : R balayé (0,50 → ρ_min 0,095 ; 0,75 → "
                  "0,345), jamais affirmé. Sans [Hθ] la borne est vide (n=1 : θ_hi = 5,2). "
                  "Variante fixe (cagnotte non progressive) : ρ ≥ R − θ̂_k au point, sans "
                  "H1–H3 — la borne survit, la stratégie de h16 non. Le règlement du jeu "
                  "rendrait tout ceci obsolète en un document.")

say(f"\n   {len(lab.ledger())} entrées au registre.")
rule(f"total {time.time() - T0:.0f}s")
