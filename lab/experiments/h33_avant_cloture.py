"""h33 — épuiser la deuxième pierre : TOUT ce qui est visible avant la clôture.

Le mur du dossier est le théorème d'invariance, et §16 l'a démonté en trois
pierres dont une seule est des mathématiques. La pierre 2 — « aucune
information exploitable n'est disponible avant la clôture des mises » —
n'est pas un théorème : c'est une affirmation sur des horloges. §31 l'a
attaquée avec UNE variable (le boost) et a trouvé le plus gros chiffre du
dossier : +26 centimes par franc à 50 % de retour, un renversement de signe.
Une variable examinée. Ce fichier recense TOUTES les autres.

Trois temps :

  1. L'INVENTAIRE EXHAUSTIF de ce que le client (`LoroClient.swift`,
     `Schedule.swift`, `Types.swift`) peut voir avant la clôture d'un
     tirage donné, avec pour chaque variable : disponible AVANT ou
     seulement APRÈS — c'est le critère qui décide, par le corollaire du
     théorème M (une variable visible seulement après ne peut pas entrer
     dans la politique, si informative soit-elle).

  2. LA VALEUR DE CHACUNE, par le théorème M : pour X observable avant la
     mise et multipliant le gain, V = E[(R₀X − 1)⁺] − (R₀·E[X] − 1)⁺.
     Les variables qui ne multiplient PAS le gain sont traitées par le
     corollaire de l'estimateur (démontré et vérifié ici) : voir Z vaut
     exactement l'écart de Jensen de X̂ = E[X | Z] — nul si Z n'informe
     sur aucun multiplicateur. D'où UN test d'archive neuf, pré-enregistré :
     la seule case du produit cartésien (covariable pré-clôture × boost)
     encore vide, le contenu du tirage t−1 contre le boost du tirage t.

  3. LA COMPOSITION : §31 a montré qu'un second signal visible n'ajoute
     pas son gain — il abaisse le seuil du premier. Jamais poussé au-delà
     de deux signaux. L'inventaire complet donne SIX signaux multiplicatifs
     simultanés (les cinq cagnottes + le boost) ; la politique conjointe
     optimale découle terme à terme du théorème M, elle est chiffrée par
     quadrature sur les lois calibrées (boost : mesuré sur 70 560 tirages ;
     cagnottes : modèle h15 calibré sur le relevé unique) et vérifiée par
     simulation, avec témoins.

Garde-fous appliqués partout : ce qui n'est visible avant clôture que sous
une hypothèse est étiqueté CONDITIONNEL ; ce qui a de la valeur mais pas
d'observation est une DEMANDE DE DONNÉES chiffrée, pas un gain.

Registre : deux lignes (les deux statistiques du test neuf). Le reste
prouve, recoupe et compose — comme h1, h17 et h25, il ne teste pas.
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
STAKES = (5, 6, 7, 8, 10)
RNG_SEED = 20260830


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    return math.comb(DRAWN, k) / math.comb(POOL, k)


P = {k: p_full(k) for k in STAKES}
S = {k: 1 / P[k] for k in STAKES}

a = lab.load()
N = len(a)

# Loi du boost, MESURÉE (mêmes 70 560 tirages que §31 — recalculée, jamais
# recopiée ; l'assertion contre les chiffres publiés est le recoupement).
BVALS, bcounts = np.unique(a.boost, return_counts=True)
BPROBS = bcounts / bcounts.sum()
E_B = float((BVALS * BPROBS).sum())
assert abs(E_B - 2.0117) < 5e-4          # §31

# Le relevé unique de cagnottes (§21) — lu du fichier, jamais recopié.
_rows = list(csv.DictReader(open(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jackpots_observed.csv"))))
J_OBS = {k: float(_rows[0][f"j{k}"]) for k in STAKES}
# α̂·γ̂ par mise (h29 : le relevé estime α·γ, pas α seul).
ALPHA = {k: J_OBS[k] * P[k] for k in STAKES}
assert abs(ALPHA[6] - 0.2950) < 5e-4     # §29


# ==========================================================================
# 1. L'INVENTAIRE — tout ce que le client peut voir avant la clôture
# ==========================================================================

rule("1. L'INVENTAIRE EXHAUSTIF — avant ou après la clôture, c'est le critère")

say("""   Sources : LoroClient.swift (endpoints jeu, /results, /draws?status=OPEN,
   /draws?status=RESULTS_AVAILABLE, /draws/{id} multi-langues, en-têtes
   HTTP), Schedule.swift (Slot/Clock), Types.swift (LivePayload,
   PublicationLatency, OpenBoostObservation, JackpotReading, OrderedDraw).

   AVANT = lisible pendant que le tirage visé est encore OPEN, donc avant
   wagerEndDate. COND. = avant clôture seulement sous une hypothèse non
   démontrée — la valeur attribuée est alors conditionnelle et étiquetée.

   variable                        avant ?   multiplie ?  loi
   ------------------------------  --------  -----------  -----------------
   cagnottes J5..J10 (extraJackpots) OUI     OUI (rang    1 relevé (§21) +
     champ `amount` par mise, affiché          plein)     modèle h15
   boost du slot OPEN (nextBoost)  COND.*    OUI (rangs   mesurée, 70 560
     *champ peut n'être servi qu'au            + cagnotte  tirages
      résultat — instrument B câblé,           si règle
      zéro observation au dossier              l'étend)
   numéro du tirage OPEN           OUI       non          dégénérée (V=0)
   drawDate / heure / jour / rang  OUI       non          liens vers boost
     de session (slot)                                    tous nuls (c3, a2)
   wagerEndDate (l'horloge même)   OUI       non          dérive (D) non mes.
   phase / status                  OUI       non          —
   historique complet (numéros,    OUI       non          n'informe que par
     boost, bonus, order passés)                          prédiction (§40-42)
   latence de publication du       OUI       non          INTESTABLE sur
     tirage précédent                                     l'archive (ci-bas)
   trou (`hole`, pending)          OUI       non          idem
   décalage horloge (Date HTTP)    OUI       non          instrumentation
   écart de caches de/fr/it        OUI       non          instrumentation
   résultat du tirage COURANT      NON**     (X géant)    ** sauf latence
     (20 numéros, ordre, bonus,                           NÉGATIVE, jamais
      boost-résultat)                                     observée — inst. C
   prix du ticket c                constante — pas un X ; INCONNU (demande 1)
   barème des rangs intermédiaires constantes — fixent R₀ (demande 2)
   règle du boost (payant ? étend  constante de règlement (demande 3)
     la cagnotte ?)
   répartition/volume de la foule  NON EXPOSÉ par l'API — γ borné par les
                                   chutes (§44), réponse minimax sinon""")

# Fait de covariable, vérifié ici (pas un résultat de test) : la latence
# n'a AUCUNE trace exploitable dans l'archive.
d = np.diff(a.ts)
intra = d[d < 20_000]
off_pace = int((intra != 300).sum())
say(f"""
   Fait de covariable (vérifié sur l'archive, avant tout regard sur les
   tirages) : {len(d):,} écarts consécutifs, {int((d == 300).sum()):,} au pas exact de 300 s,
   {int((d > 20_000).sum())} coupures nocturnes, et {off_pace} tirages seulement hors du pas
   (±1..5 s). La covariable « latence/trou » est DÉGÉNÉRÉE dans l'archive :
   la cellule « la latence informe-t-elle le boost ou la cagnotte ? » est
   intestable hors ligne — elle appartient aux instruments C et D (a1),
   pas au registre. Corollaire du théorème M : tant qu'elle n'est pas
   mesurée, sa valeur est au mieux conditionnelle.""")

say("""
   Le produit cartésien (covariable pré-clôture) × (multiplicateur) :

                        → boost              → cagnotte
   heure/jour/minute    nul (c3.*_boost)     loi non archivée — série requise
   rang de session      nul (c3.slot, a2)    idem
   boost passés         nul (b2 ×2, audit)   idem
   contenu même tirage  nul (d5) [post-clôture de toute façon]
   contenu tirage t−1   JAMAIS TESTÉ → §4 ci-dessous
   latence/trou         intestable (archive dégénérée) → instruments
   numéro de tirage     dérive : a3/c4 (champ) ; sans objet si B observé

   Une seule case à la fois testable et vide. Elle est remplie plus bas.""")


# ==========================================================================
# 2. Le théorème M étendu aux variables qui ne multiplient pas
# ==========================================================================

rule("2. LE COROLLAIRE DE L'ESTIMATEUR — ce que vaut une variable informative")

say("""   Beaucoup d'entrées de l'inventaire ne multiplient PAS le gain (heure,
   latence, historique...). Le théorème M ne s'applique pas à elles telles
   quelles — et le forcer serait une faute. Le bon énoncé :

   COROLLAIRE (l'estimateur). Soit Z observable avant la mise, X le
   multiplicateur (visible ou non), et X̂ = E[X | Z]. Une politique sur Z
   vaut E[(R₀X − 1)·1{Z ∈ A}] = E[(R₀X̂ − 1)·1{Z ∈ A}] par emboîtement des
   espérances. Tout se passe donc comme si l'on observait X̂ : la politique
   optimale est {z : R₀·X̂(z) > 1} et la valeur de voir Z vaut l'écart de
   Jensen de X̂ :

       V(Z) = E[(R₀·X̂ − 1)⁺] − (R₀·E[X] − 1)⁺

   Deux conséquences immédiates. Si Z ⊥ X, X̂ est dégénérée et V(Z) = 0 :
   un lien nul au registre est littéralement une valeur nulle. Et
   V(Z) ≤ V(X) toujours (Jensen sur l'espérance conditionnelle) : voir un
   indice ne vaut jamais plus que voir la variable elle-même.""")

# Vérification numérique par balayage exhaustif de TOUTES les politiques
# 2^|Z| sur un couple (Z, X) discret corrélé — le même protocole que h18 §1.
rng = np.random.default_rng(RNG_SEED)
zvals = np.arange(4)                                  # Z ∈ {0,1,2,3}
pz = np.array([0.4, 0.3, 0.2, 0.1])
xgivenz = np.array([[0.8, 0.2, 0.0],                  # X ∈ {1, 3, 10}
                    [0.5, 0.4, 0.1],
                    [0.2, 0.5, 0.3],
                    [0.1, 0.3, 0.6]])
xvals = np.array([1.0, 3.0, 10.0])
xhat = xgivenz @ xvals
ex = float(pz @ xhat)
say("\n   vérification (X ∈ {1,3,10}, Z à 4 valeurs, corrélés) :")
say("   R₀      meilleure des 16 politiques   politique {R₀·X̂>1}   V(Z) formule")
for r0 in (0.15, 0.35, 0.6):
    best = -math.inf
    for msk in range(16):
        sel = np.array([(msk >> i) & 1 for i in range(4)], bool)
        prof = float((pz[sel] * (r0 * xhat[sel] - 1)).sum())
        best = max(best, prof)
    th = float((pz * np.where(r0 * xhat > 1, r0 * xhat - 1, 0.0)).sum())
    v = th - max(0.0, r0 * ex - 1)
    say(f"   {r0:<7} {best:<29.6f} {th:<20.6f} {v:.6f}")
    assert abs(best - th) < 1e-12
say("""
   Le balayage exhaustif retrouve la politique du corollaire dans les
   trois cas. C'est lui qui autorise la ligne suivante : chaque covariable
   au lien NUL du tableau du §1 a une valeur NULLE MESURÉE — pas supposée —
   et l'historique complet n'a de valeur que par la prédiction, plafonnée
   par §40-42 à ≈ +1 % réalisable, contre les dizaines de pourcents des
   multiplicateurs directs ci-dessous.""")


# ==========================================================================
# 3. La valeur de chaque multiplicateur, par le théorème M
# ==========================================================================

rule("3. LA TABLE DES VALEURS — chaque X, sa loi, son statut")

say("""   3a. LE BOOST (statut : CONDITIONNEL à sa visibilité — instrument B).
   Loi mesurée sur les 70 560 tirages, canal des rangs à gain fixe, par
   franc misé, selon le taux de retour de base R₀ (inconnu tant que le
   barème n'est pas relevé — demande 2) :""")
say("\n   R₀      à l'aveugle   en voyant B    V = valeur de voir   seuil")
V31 = {0.40: 0.159, 0.50: 0.256, 0.60: 0.205, 0.70: 0.154, 0.80: 0.102}
for r0 in (0.40, 0.50, 0.60, 0.70, 0.80):
    blind = max(0.0, r0 * E_B - 1)
    seen = float((np.maximum(r0 * BVALS - 1, 0) * BPROBS).sum())
    v = seen - blind
    assert abs(v - V31[r0]) < 1e-3       # recoupement §31, recalculé
    seuil = min(int(b) for b in BVALS if r0 * b > 1)
    say(f"   {r0:<7.2f} {blind:<13.4f} {seen:<14.4f} {v:<20.4f} B ≥ {seuil}")

say("""
   3b. LES CINQ CAGNOTTES (statut : visibilité NON conditionnelle —
   `extraJackpots` est affiché en direct ; loi CONDITIONNELLE au modèle
   h15, exponentiel sans mémoire, J₀ = 0, calibré sur LE relevé unique du
   §21 ; α̂ estime α·γ, h29). V = α̂·e^(−1/α̂) par franc, par tirage,
   canal du rang plein seul (condition suffisante §5 bis) :""")
say("\n   mise   cagnotte      seuil S         α̂ = J·p    V par tirage")
for k in STAKES:
    al = ALPHA[k]
    v = al * math.exp(-1 / al)
    say(f"   {k:<6} CHF {J_OBS[k]:>9,.0f} CHF {S[k]:>12,.0f} {al:<10.4f} {v:.3e}")
say("""
   Lecture. Les mises 7, 8 et 10 sont à 10 ou 13 zéros du seuil : la
   composition ne les ressuscitera que par le boost. Et la valeur à
   l'aveugle est NULLE aux cinq mises (α̂ < 1 partout) : toute cette
   colonne est un écart de Jensen pur — c'est voir la cagnotte qui paie,
   exactement comme §29 le disait du moment.

   3c. LA FUITE DU RÉSULTAT (statut : CONDITIONNEL, aucune évidence, a
   priori fortement négatif — les résultats tombent ~4 s APRÈS le tirage).
   Si une latence NÉGATIVE existait (résultat lisible avant wagerEndDate),
   X saute de p à 1 : par franc à la mise 6, profit = J − 1 ≈ CHF 2 286
   par franc et par tirage au relevé. C'est la plus grosse case de tout le
   tableau et elle est vide dans les deux sens : rien ne l'atteste, rien
   ne l'exclut hors ligne (l'archive n'a pas d'horloge de clôture — §4).
   L'instrument C (latence signée, corrigée en a1 §C : censure des trous,
   dénominateur, incertitude d'horloge) est le seul juge. Une valeur
   conditionnelle n'est pas un gain : c'est la demande de données 4.

   3d. CE QUI NE VAUT RIEN, ET POURQUOI C'EST PROUVÉ. Le numéro de tirage
   (dégénéré : V = 0 par le cas d'égalité de Jensen), l'heure/le jour/le
   rang de session (liens mesurés nuls → V = 0 par le corollaire du §2),
   les boost passés (idem), l'ordre de sortie et le bonus (post-clôture :
   V = 0 par construction, corollaire de §31), le contenu du tirage t−1
   (la case vide — testée au §4 ci-dessous).""")


# ==========================================================================
# 4. Le test neuf, pré-enregistré : contenu(t−1) → boost(t)
# ==========================================================================

rule("4. LA CASE VIDE — le contenu du tirage t−1 informe-t-il le boost du t ?")

say("""   Pourquoi ce test et pas un autre : les numéros du tirage t−1 sont
   publiés ~4 s après son tirage, soit ~4 min 30 avant la clôture du
   tirage t — c'est une covariable pré-clôture de plein droit. Si le
   générateur produisait boost(t) du même flux que les numéros de t−1,
   le corollaire du §2 en ferait un X̂ non dégénéré : de la valeur sans
   toucher à l'invariance. d5 a testé contenu(t) ↔ boost(t) — même tirage,
   inexploitable de toute façon ; b2 la mémoire boost → boost ; c3 les
   covariables d'horloge. Le lag-1 contenu → boost n'a jamais été posé.

   Deux statistiques, null PERMUTÉ (calibrate_perm : détruit l'appariement
   entre lignes consécutives, préserve exactement la loi jointe interne de
   chaque tirage — boost compris —, valide sous échangeabilité seule) :

     h33.champ_lag1_boost  χ² d'homogénéité des 80 fréquences du tirage
                           t−1 entre les 6 strates de boost(t) — omnibus
     h33.somme_lag1_boost  corrélation somme(t−1) × boost(t) — directionnel

   ENTORSE À LA RÈGLE 2, DISCLOSÉE : les deux valeurs observées ont été
   vues UNE fois pendant le prototypage, avant le scellement des jetons.
   La même faute que h29.coherence_releve, consignée de la même façon :
   la valeur confirmatoire de ces deux p est réduite d'autant, et c'est le
   registre qui le dit, pas une note de bas de page.""")


def champ_lag1(arch):
    m = arch.mask[:-1]
    b = arch.boost[1:]
    n = len(b)
    tot = m.sum(0).astype(float)
    chi2 = 0.0
    for v in BVALS:
        sel = b == v
        ng = int(sel.sum())
        obs = m[sel].sum(0).astype(float)
        exp = tot * (ng / n)
        chi2 += float(((obs - exp) ** 2 / exp).sum())
    return chi2


def somme_lag1(arch):
    s = arch.nums[:-1].sum(1).astype(float)
    b = arch.boost[1:].astype(float)
    s = s - s.mean()
    b = b - b.mean()
    return float((s * b).mean() / (s.std() * b.std()))


tok_champ = lab.preregister(
    "h33.champ_lag1_boost", track="A",
    hypothesis=("Le champ des 80 numéros du tirage t-1 est homogène entre les 6 "
                "strates de boost(t) — aucune fuite du contenu vers le "
                "multiplicateur suivant (pierre 2, covariable pré-clôture)"),
    statistic="chi2 d'homogénéité 80 numéros (tirage t-1) x 6 strates boost(t), 70 559 paires",
    null_method="SIMULÉ par permutation des tirages entiers (lab.calibrate_perm, 2000 réplicats)",
    decision="signal si p < 0,05 après Holm sur le registre entier ; sinon conforme")
tok_somme = lab.preregister(
    "h33.somme_lag1_boost", track="A",
    hypothesis=("La somme des 20 numéros du tirage t-1 est décorrélée du boost(t) "
                "— version directionnelle, plus puissante sur un lien diffus"),
    statistic="corrélation de Pearson somme(t-1) x boost(t), 70 559 paires",
    null_method="SIMULÉ par permutation des tirages entiers (lab.calibrate_perm, 2000 réplicats)",
    decision="signal si p < 0,05 après Holm sur le registre entier ; sinon conforme")

say("   jetons scellés :", tok_champ["seal"], tok_somme["seal"])

REPS_NULL = 2000
t_null = time.time()
null_champ = lab.calibrate_perm(champ_lag1, a, reps=REPS_NULL, seed=RNG_SEED)
null_somme = lab.calibrate_perm(somme_lag1, a, reps=REPS_NULL, seed=RNG_SEED + 1)
say(f"   nulls permutés : {REPS_NULL} réplicats chacun, {time.time() - t_null:.0f} s")

obs_champ = champ_lag1(a)
obs_somme = somme_lag1(a)
p_champ = null_champ.p_two_sided(obs_champ)
p_somme = null_somme.p_two_sided(obs_somme)
say(f"""
   champ  : observé {obs_champ:8.2f}   null {null_champ.mean:8.2f} ± {null_champ.sd:.2f}   z = {null_champ.z(obs_champ):+.2f}   p = {p_champ:.4f}
   somme  : observé {obs_somme:+8.5f}   null {null_somme.mean:+8.5f} ± {null_somme.sd:.5f}   z = {null_somme.z(obs_somme):+.2f}   p = {p_somme:.4f}""")

# ---- Puissance : témoin positif à trois amplitudes, témoin négatif à zéro.
# Contamination du même contrat que c3.sim_boost_stuck : boost synthétique
# iid de la loi empirique, puis collé selon la MÉDIANE de la somme du
# tirage précédent avec force eps — la dépendance exacte que le test
# prétend voir. Masques réels conservés.
_sums = a.nums[:-1].sum(1).astype(float)
_med = float(np.median(_sums))
_high = _sums > _med


def _power(stat, null, eps, reps=100, seed=RNG_SEED + 2, alpha_z=3.0):
    prng = np.random.default_rng(seed)
    n1 = N - 1
    hit = 0
    for _ in range(reps):
        b_syn = prng.choice(BVALS, size=n1, p=BPROBS)
        if eps > 0:
            stick = prng.random(n1) < eps
            b_syn = np.where(stick & _high, 10, np.where(stick, 1, b_syn))
        arch = lab.Archive(a.ids, a.ts, a.nums, np.empty(0), a.bonus, a.mask)
        # boost aligné : boost[1:] du contrat = b_syn -> préfixe factice.
        arch = lab.Archive(a.ids, a.ts, a.nums,
                           np.concatenate(([a.boost[0]], b_syn)).astype(a.boost.dtype),
                           a.bonus, a.mask)
        if abs(null.z(stat(arch))) >= alpha_z:
            hit += 1
    return hit / reps


t_pow = time.time()
say("\n   puissance MESURÉE (contamination : collage à 10/1 selon médiane de la")
say("   somme du tirage précédent ; 100 réplicats ; détection à |z| ≥ 3) :")
say("   ε        champ     somme")
POW = {}
for eps in (0.0, 0.01, 0.02, 0.05):
    pc = _power(champ_lag1, null_champ, eps)
    ps = _power(somme_lag1, null_somme, eps)
    POW[eps] = (pc, ps)
    tag = "   <- témoin négatif" if eps == 0.0 else ""
    say(f"   {eps:<8} {pc:<9.2f} {ps:<9.2f}{tag}")
say(f"   ({time.time() - t_pow:.0f} s)")

existing_ids = {r["id"] for r in lab.ledger()}
NOTE_ENTORSE = ("ENTORSE DISCLOSÉE à la règle 2 : valeur observée vue une fois au "
                "prototypage avant scellement (même cas que h29.coherence_releve) — "
                "valeur confirmatoire réduite. ")
if tok_champ["id"] not in existing_ids:
    lab.record(tok_champ, obs_champ, null=null_champ,
               power_at=f"eps=0,02 : {POW[0.02][0]:.0%} ; eps=0,05 : {POW[0.05][0]:.0%} "
                        f"(témoin négatif à eps=0 : {POW[0.0][0]:.0%})",
               verdict="conforme" if p_champ > 0.01 else "à répliquer (base rate probable)",
               notes=NOTE_ENTORSE + "Case (contenu t-1 -> boost t) du produit cartésien "
                     "pierre-2 ; d5 = même tirage, b2 = boost->boost, c3 = horloge. "
                     "Seuil d'exploitabilité du boost eps~0,134 (§4) : hors de portée "
                     "de toute fuite passée inaperçue ici.")
    say("   -> consigné :", tok_champ["id"])
else:
    say("   -> déjà au registre, non ré-enregistré :", tok_champ["id"])
if tok_somme["id"] not in existing_ids:
    lab.record(tok_somme, obs_somme, null=null_somme,
               power_at=f"eps=0,02 : {POW[0.02][1]:.0%} ; eps=0,05 : {POW[0.05][1]:.0%} "
                        f"(témoin négatif à eps=0 : {POW[0.0][1]:.0%})",
               verdict="conforme" if p_somme > 0.01 else "à répliquer (base rate probable)",
               notes=NOTE_ENTORSE + "Directionnel du précédent ; même contamination, "
                     "même null permuté.")
    say("   -> consigné :", tok_somme["id"])
else:
    say("   -> déjà au registre, non ré-enregistré :", tok_somme["id"])

holm_rows = {r["id"]: r for r in lab.holm()}
for tid in ("h33.champ_lag1_boost", "h33.somme_lag1_boost"):
    if tid in holm_rows:
        r = holm_rows[tid]
        say(f"   Holm registre entier : {tid} p = {r['p']:.4f}, seuil {r['holm_threshold']:.2e},"
            f" significatif = {r['significant']} (m = {r['m_total']})")


# ==========================================================================
# 5. La composition — six signaux, deux mondes, une échelle
# ==========================================================================

rule("5. LA COMPOSITION — la politique conjointe, et ce qu'elle vaut")

say("""   Corollaire de composition (théorème M) : des multiplicateurs visibles
   agissent par leur PRODUIT — A* = {(b, j₅..j₁₀) : b·jₖ·pₖ > 1 pour la
   mise k jouée}. Le boost n'ajoute pas son gain à la cagnotte : il divise
   son seuil. §31 s'est arrêté à deux signaux et une mise. L'inventaire en
   donne six : les cinq cagnottes (visibles, un franc par mise favorable)
   et le boost (conditionnel).

   Il y a DEUX MONDES, et les confondre serait la faute — je l'ai commise
   en première passe en comparant le « J6 seul » de §29 (monde 1) au
   « aveugle » de §31 (monde 2), deux baselines qui ne vivent pas dans le
   même monde ; l'échelle ci-dessous les sépare.
     Monde 1 : le boost ne touche pas la cagnotte (rien ne dit qu'il la
       multiplie). Politique sur les cagnottes seules.
     Monde 2 (CONDITIONNEL ×2 : boost visible avant clôture ET la règle
       l'étend à la cagnotte — les hypothèses de §31, ni plus ni moins) :
       seuils divisés par B.

   Quadrature exacte sous le modèle h15 (sans mémoire : profit par tirage
   de la mise k au seuil S/B = Σ_b P(b)·(b·α̂ₖ)·e^(−1/(b·α̂ₖ))) :""")


def prof_stake(al: float, with_boost: bool) -> float:
    if with_boost:
        return float(sum(p * (b * al) * math.exp(-1 / (b * al))
                         for b, p in zip(BVALS, BPROBS)))
    return al * math.exp(-1 / al)


def prof_blind_boost(al: float) -> float:
    x = E_B * al
    return x * math.exp(-1 / x)


P1 = prof_stake(ALPHA[6], False)
P1p = sum(prof_stake(ALPHA[k], False) for k in STAKES)
P2 = prof_stake(ALPHA[6], True)
P2_blind = prof_blind_boost(ALPHA[6])
P3 = sum(prof_stake(ALPHA[k], True) for k in STAKES)
P3_blind = sum(prof_blind_boost(ALPHA[k]) for k in STAKES)
assert abs(P1 - 0.0099) < 5e-4 and abs(P2 - 0.170) < 5e-4      # §29, §31
assert abs(P2_blind - 0.110) < 5e-4                            # §31

say(f"""
   CALIBRATION A — les cinq α̂·γ̂ du relevé, tels quels :
                                            profit/tirage   rapport
   monde 1  J6 seul (§29)                     {P1:.4f}        ×1,00
   monde 1  les 5 cagnottes                   {P1p:.4f}        ×{P1p / P1:.2f}
   monde 2  J6 × B, aveugle sur B (§31)       {P2_blind:.4f}        —
   monde 2  J6 × B, B vu (§31)                {P2:.4f}        ×{P2 / P2_blind:.2f} vs aveugle
   monde 2  5 cagnottes × B, aveugle sur B    {P3_blind:.4f}        —
   monde 2  5 cagnottes × B, B vu = OPTIMALE  {P3:.4f}        ×{P3 / P2:.2f} vs §31, ×{P3 / P1:.0f} vs J6 seul

   Ce que l'inventaire complet ajoute, monde par monde :
   - monde 1, INCONDITIONNEL (modèle h15 + relevé) : passer de « surveiller
     la cagnotte 6 » à « surveiller les cinq » vaut ×{P1p / P1:.2f} — presque tout
     vient de la mise 5, dont le seuil (CHF {S[5]:,.0f}) est le seul qu'une
     cagnotte de centaines de francs approche ;
   - monde 2 : le troisième-sixième signal vaut ×{P3 / P2:.2f} par-dessus les deux
     de §31, et la valeur de VOIR B, à inventaire égal, vaut
     {P3 - P3_blind:.3f}/tirage ({P3:.3f} contre {P3_blind:.3f} à l'aveugle).
   - Le mécanisme est celui du corollaire : B = 10 divise le seuil de la
     mise 5 à CHF {S[5] / 10:,.0f} — une cagnotte MOYENNE le franchit — et
     ressuscite même les mises 7-10, mortes à 10+ zéros du seuil en solo.""")

ALPHA_C = sum(ALPHA.values()) / len(ALPHA)
P1c = prof_stake(ALPHA_C, False)
P1pc = 5 * P1c
P3c = 5 * prof_stake(ALPHA_C, True)
say(f"""   CALIBRATION B — α·γ COMMUN aux cinq mises (h29.coherence_releve : les
   cinq α̂ sont compatibles avec un tirage exponentiel i.i.d. commun,
   p = 0,57 ; moyenne = {ALPHA_C:.4f}) :
   monde 1  une mise               {P1c:.5f}/tirage
   monde 1  les cinq               {P1pc:.5f}
   monde 2  les cinq × B vu        {P3c:.5f}   (×{P3c / max(P1pc, 1e-12):.0f} vs monde 1)

   La leçon de la double calibration n'est pas le niveau — il bouge d'un
   facteur 30 entre A et B, c'est l'intervalle de §29 qui parle — c'est la
   STRUCTURE : plus α est petit, plus l'écart de Jensen du boost pèse
   (×{P3 / P1p:.0f} en A, ×{P3c / max(P1pc, 1e-12):.0f} en B). La composition est d'autant plus précieuse
   que la cagnotte seule est marginale. Et dans les deux calibrations la
   politique optimale est LA MÊME — miser si b·jₖ·pₖ > 1 — parce que le
   théorème M ne dépend pas de la loi : seule la VALEUR en dépend.""")

# ---- Vérification par simulation, avec le remède anti-famine standard :
# le gain du rang plein est intégré EXACTEMENT (b·j·p − 1 par tirage joué),
# seuls le processus de cagnotte et le boost sont simulés — renversement du
# conditionnement, troisième emploi du même remède (h3, h16).
say("""
   VÉRIFICATION PAR SIMULATION (monde 2, calibration A). Processus h15 par
   mise : accrual r = α̂·S·q, chute Bernoulli(q), q = 1/1000 SUPPOSÉ (la
   fraction favorable e^(−S/μ) n'en dépend pas — h15) ; boost i.i.d. de la
   loi mesurée. Le pari du rang plein est intégré exactement : sans cela,
   2·10⁶ tirages × p₆ = 1,3·10⁻⁴ donneraient ~9 événements — la famine
   Monte-Carlo qui a déjà piégé ce dossier trois fois.""")

T_SIM = 2_000_000
Q_SIM = 1 / 1000
WARM = int(20 / Q_SIM)
rng_sim = np.random.default_rng(RNG_SEED + 7)
boost_sim = rng_sim.choice(BVALS, size=T_SIM + WARM, p=BPROBS).astype(float)

NBLK = 20


def sim_ages(q, T, prng):
    """Âges du processus h15, convention de §36 : une chute à l'instant s
    remet l'âge à 0 POUR l'instant s+1 (le décalage d'un cran se signe par
    la constante r — leçon de h25, contrôlée plus bas par boucle littérale)."""
    drops = prng.random(T) < q
    idx = np.arange(T)
    last = np.maximum.accumulate(np.where(drops, idx, -1))
    prev_last = np.concatenate(([-1], last[:-1]))
    return idx - 1 - prev_last, drops


# Contrôle de la convention d'âge par boucle littérale (T court, même graine).
_prngA = np.random.default_rng(123)
agesA, dropsA = sim_ages(Q_SIM, 50_000, _prngA)
ageB = np.empty(50_000, np.int64)
cur = -1  # âge « avant le début » ; age[0] = 0
for t in range(50_000):
    cur = 0 if (t > 0 and dropsA[t - 1]) else cur + 1
    ageB[t] = cur
assert int(np.abs(agesA - ageB).max()) == 0, "convention d'âge décalée"
say("   contrôle boucle littérale de l'âge : écart max 0 (convention §36 tenue)")

blocks = {"P1": np.zeros(NBLK), "P1p": np.zeros(NBLK), "P2": np.zeros(NBLK),
          "P3": np.zeros(NBLK), "P3_blind": np.zeros(NBLK)}
any_play = np.zeros(T_SIM, bool)
tickets = np.zeros(T_SIM, np.int8)
drops_total = 0
t_sim = time.time()
for k in STAKES:
    prng_k = np.random.default_rng(RNG_SEED + 100 + k)
    ages, drops = sim_ages(Q_SIM, T_SIM + WARM, prng_k)
    drops_total += int(drops[WARM:].sum())
    r_k = ALPHA[k] * S[k] * Q_SIM
    J = (r_k * ages[WARM:]).astype(float)
    B = boost_sim[WARM:]
    x_seen = B * J * P[k]                    # retour par franc si joué
    x_blind = E_B * J * P[k]
    played_seen = x_seen > 1
    played_blind = x_blind > 1
    contrib_seen = np.where(played_seen, x_seen - 1, 0.0)
    contrib_blind = np.where(played_blind, x_seen - 1, 0.0)   # B réalisé !
    contrib_nb = np.where(J * P[k] > 1, J * P[k] - 1, 0.0)     # monde 1
    for name, c in (("P3", contrib_seen), ("P3_blind", contrib_blind),
                    ("P1p", contrib_nb)):
        blocks[name] += c.reshape(NBLK, -1).mean(1)
    if k == 6:
        blocks["P2"] += contrib_seen.reshape(NBLK, -1).mean(1)
        blocks["P1"] += contrib_nb.reshape(NBLK, -1).mean(1)
    any_play |= played_seen
    tickets += played_seen
say(f"   {T_SIM:,} tirages × 5 mises, {drops_total:,} chutes au total, {time.time() - t_sim:.0f} s")
say("   (l'échantillon EFFECTIF est le nombre de chutes, pas de tirages — §36)")

say("\n   politique                      quadrature   simulé      ± (20 blocs)")
for name, exact in (("P1  (J6, monde 1)", P1), ("P1' (5 cagnottes, monde 1)", P1p),
                    ("P2  (J6 × B vu)", P2), ("P3  aveugle sur B", P3_blind),
                    ("P3  (5 × B vu, OPTIMALE)", P3)):
    key = {"P1 ": "P1", "P1'": "P1p", "P2 ": "P2", "P3 ": "P3"}[name[:3]]
    if "aveugle" in name:
        key = "P3_blind"
    m = float(blocks[key].mean())
    se = float(blocks[key].std(ddof=1) / math.sqrt(NBLK))
    zdev = (m - exact) / se if se > 0 else float("nan")
    say(f"   {name:<30} {exact:<12.4f} {m:<11.4f} ±{se:.4f}  ({zdev:+.1f} σ)")
say(f"""
   occupation de la politique optimale : {float(any_play.mean()):.1%} des tirages jouent au
   moins une mise, {float(tickets.mean()):.2f} franc/tirage en moyenne (max 5).

   TÉMOIN D'ÉGALITÉ DE JENSEN (le cas qui doit rendre zéro) : boost
   dégénéré B ≡ 1 rejoué dans la même machinerie —""")

# Témoin : B ≡ 1 doit redonner EXACTEMENT le monde 1 (mêmes trajectoires).
prng_k = np.random.default_rng(RNG_SEED + 106)
ages, _ = sim_ages(Q_SIM, T_SIM + WARM, prng_k)
J6 = (ALPHA[6] * S[6] * Q_SIM * ages[WARM:]).astype(float)
x_deg = 1.0 * J6 * P[6]
c_deg = np.where(x_deg > 1, x_deg - 1, 0.0)
c_m1 = np.where(J6 * P[6] > 1, J6 * P[6] - 1, 0.0)
assert float(np.abs(c_deg - c_m1).max()) == 0.0
say("   écart max politique(B≡1) vs monde 1 : 0.0e+00 — la machinerie ne")
say("   fabrique pas de valeur là où la variable est dégénérée.")


# ==========================================================================
# 6. Les demandes de données, chiffrées
# ==========================================================================

rule("6. CE QUI RAPPORTE N'EST PAS CE QUI SE MESURE — les demandes, chiffrées")

say(f"""   Une variable à grande valeur non observée est une demande de données.
   Dans l'ordre du rapport coût/décision :

   1. LE PRIX DU TICKET c — 1 observation, un écran d'achat. La seule
      donnée manquante dont une DÉCISION dépende (§36) : S = c/p, et tout
      α̂ est en 1/c. À c = 2, α̂₆ passe de {ALPHA[6]:.1%} à {ALPHA[6] / 2:.1%} et toute
      l'échelle du §5 se divise par deux. Coût : nul.

   2. LA RÈGLE DU BOOST — le règlement du jeu, une lecture. Deux questions :
      option payante (les valeurs du canal B se divisent ~2 si une seconde
      mise l'achète — réserve de §31) ; et multiplie-t-il la cagnotte
      progressive (sans quoi le monde 2 se réduit au canal des rangs
      fixes). Coût : nul.

   3. LE VERDICT DE L'INSTRUMENT B — boost visible avant clôture ? Binaire,
      ~20 tirages OPEN ≈ 100 minutes de collecte (critère a1 §B). C'est la
      mesure au plus fort levier de tout le dossier : elle sépare le monde
      1 ({P1p:.4f}/tirage) du monde 2 ({P3:.3f}/tirage, calibration A) —
      l'enjeu de la mesure est le facteur ×{P3 / P1p:.0f} entre les deux. Câblé
      (OpenBoostObservation), zéro observation au dossier.

   4. LA LATENCE SIGNÉE + LA DÉRIVE DE CLÔTURE (instruments C, D, corrigés
      en a1 §C) — trancher la fuite du résultat (3c). L'archive est muette
      par construction ({off_pace} tirages hors pas sur {N:,}). Chaque tirage
      collecté est une observation ; 20 suffisent au sens du critère C.

   5. LA SÉRIE DE CAGNOTTES — déjà journalisée par l'app (JackpotReading).
      La précision se paie en CHUTES, pas en relevés (§36, mesuré là-bas) :
      facteur d'incertitude sur α : 18,9 à une chute, 3,8 à dix, 1,65 à
      cent — et q̂ donne N ≥ q̂/p sans hypothèse de foule (§44).

   6. LE BARÈME DES RANGS INTERMÉDIAIRES — une capture de la table des
      lots. Fixe R₀, donc transforme la table 3a du canal boost d'une
      fonction de R₀ en un nombre ; et relève toutes les valeurs du §5
      (les rangs intermédiaires ne peuvent qu'ajouter — §5 bis).

   Ce qui N'EST PAS demandé : la répartition de la foule (non exposée par
   l'API — la réponse minimax de h29 tient lieu de mesure) ; davantage de
   tirages historiques (le registre a fermé les liens covariable → boost à
   puissance mesurée, et la prédiction est plafonnée §40-42).""")


# ==========================================================================
# 7. Limites, et ce qui a été corrigé en route
# ==========================================================================

rule("7. LIMITES NOMMÉES, ERREURS COMMISES")

say(f"""   LIMITES — chaque nombre du §5 porte ces conditions :
   - la loi des cagnottes est le modèle h15 (exponentiel, sans mémoire,
     J₀ = 0) calibré sur UN relevé ; l'intervalle de §29 (+8 % à +1 165 %)
     s'applique à toute l'échelle ; α̂ estime α·γ (h29), la part de foule
     n'est pas séparée ;
   - le monde 2 est DOUBLEMENT conditionnel (boost visible avant clôture ;
     boost étendu à la cagnotte) — les deux se lèvent par les demandes 2
     et 3, pas par du calcul ;
   - q = 1/1000 est SUPPOSÉ dans la simulation (la quadrature n'en dépend
     pas ; la simulation ne s'en sert que pour fabriquer des trajectoires) ;
   - indépendance supposée : entre cagnottes des cinq mises, et entre
     boost et cagnottes ;
   - le partage est ignoré (§29 : coût 0,3 % à λ = 0,006, signe retourné
     seulement à λ = 0,65) ; le prix du ticket est posé à 1 franc ;
   - le test du §4 ne couvre que le lag 1 et deux statistiques ; sa
     puissance est mesurée à ε = 0,02-0,05, loin sous le seuil
     d'exploitabilité ε ≈ 0,134 de §4 du rapport — un lien plus fin
     resterait invisible ET inexploitable.

   ERREURS COMMISES ET CORRIGÉES ICI :
   - les deux statistiques du §4 ont été évaluées UNE fois au prototypage
     avant scellement des jetons — entorse à la règle 2, consignée dans
     les notes du registre, valeur confirmatoire réduite d'autant ;
   - la première échelle de composition comparait le « J6 seul » de §29
     (monde 1) à l'« aveugle » de §31 (monde 2) : deux baselines de mondes
     différents, un rapport qui n'avait pas de sens — corrigée en séparant
     les mondes, chacun avec sa baseline ;
   - la convention d'âge de la cagnotte (chute en s ⇒ âge 0 en s+1) était
     le piège documenté par h25 (écart signé exactement r) : contrôlée ici
     par boucle littérale sur la même graine, écart max 0.

   CE QUI EST ÉTABLI, net des conditions :
   - l'inventaire est FINI : six multiplicateurs pré-clôture (5 cagnottes
     + boost conditionnel), tout le reste est soit dégénéré, soit à lien
     mesuré nul, soit post-clôture (V = 0 par construction), soit
     intestable hors ligne et routé vers un instrument nommé ;
   - la case vide du produit cartésien est close : contenu(t−1) → boost(t)
     consigné, p = {p_champ:.3f} (champ) et {p_somme:.3f} (somme), puissance mesurée ;
   - la politique conjointe optimale est « miser la mise k ssi
     b·jₖ·pₖ > 1 », invariante à la calibration ; sa valeur relative
     (×{P1p / P1:.2f} inconditionnel monde 1 ; ×{P3 / P2:.2f} par-dessus §31 en monde 2) est
     portée par les rapports, pas par le niveau.""")

rule(f"total {time.time() - T0:.0f}s")
