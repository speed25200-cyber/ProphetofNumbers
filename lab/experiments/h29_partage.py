"""h29 — l'anti-foule sans modèle de foule : le jeu minimax, sa valeur, et
ce que « Furtif » a le droit de promettre.

La question, et pourquoi elle se pose
--------------------------------------
h3 a montré que la pierre 3 du théorème d'invariance — « le gain d'une
grille ne dépend que de SES hits » — tombe dès qu'un rang est partagé, et a
chiffré un avantage « anti-foule » de ×1,77 à ×2,67. Mais ce chiffre repose
sur un modèle de popularité ÉCRIT À LA MAIN (dates ≤ 31, chiffre 7,
multiples de 11), jamais mesuré sur les joueurs de ce jeu — la répartition
des mises n'est pas publiée, elle ne peut pas l'être. Le §9 et la carte
« Furtif » de l'app le reconnaissent : l'argument est au conditionnel.

Ce fichier sort de l'impasse PAR LE HAUT : que peut-on PROUVER sur une
stratégie anti-foule sans rien savoir de la foule ? Trois questions.

(a) LE JEU MINIMAX. Le joueur choisit une grille (ou un portefeuille, ou
    une loi sur les grilles) ; la nature choisit la répartition w de N
    grilles adverses ; le gain du rang partagé est J/(1 + co-gagnants).

    THÉORÈME (symétrisation, style Hunt-Stein). Le groupe S_80 des
    permutations des 80 numéros laisse le tirage invariant, donc la
    garantie G(x) = inf_w U(x, w) vérifie G(σx) = G(x). G est un inf de
    formes linéaires en x, donc concave ; la moyenne de σx sur le groupe
    vaut la loi uniforme (une seule orbite de grilles). D'où

        G(uniforme) ≥ G(x)   pour TOUTE stratégie x.

    La grille UNIFORMÉMENT ALÉATOIRE est exactement minimax. « Éviter la
    foule » n'est pas prouvable ; « être imprévisible » l'est. Une grille
    déterministe — furtive comprise — a pour garantie J·p/(1+N) : la
    nature pose ses N tickets dessus. La randomisation uniforme vaut donc
    un facteur (1+N)·v(N) de garantie, où v(N) est la valeur du jeu.

    LEMME D'UNIFORMITÉ (la clef de tout le fichier). Pour une grille
    uniforme g, P(g ⊆ d) = C(20,k)/C(80,k) est la MÊME pour tout tirage d,
    donc conditionner au gain ne déforme pas le tirage : D | « g gagne »
    reste uniforme, et le mécanisme de h3 — « mes numéros sont déjà dans
    D, une foule qui les aime a une longueur d'avance » — disparaît en
    moyenne. Il en découle, EXACTEMENT :

        E[gain] = J·p·E_D[1/(1+W(D))]   avec D uniforme.

    VALEUR. La nature minimise E_D[1/(1+W)] sous E[W] = m = N·p. La
    minorante convexe de 1/(1+w) interpolée aux entiers donne la borne
    universelle L(m) (= 1 − m/2 pour m ≤ 1) ; la foule i.i.d. uniforme
    donne la majorante exacte (1−(1−p)^{N+1})/((N+1)p). Dans le jeu
    réduit (8 numéros, 3 tirés, grilles de 2, foule de 3), la valeur
    exacte — énumérée ici sur les 4 060 foules — doit être p·L(3p) =
    141/1568, atteinte par les foules en triples DISJOINTS : la nature
    optimale, elle aussi, étale. En 20/80 les deux bornes se pincent à
    m²/6 près (m ≤ 1) : la valeur est déterminée sans résoudre le design.

    PORTEFEUILLES. La symétrisation vaut aussi pour n grilles : l'optimal
    est une ORBITE — un motif de recouvrements — tirée par permutation
    uniforme. Entre motifs, 1/(j+W) ≤ 1/(1+W) donne, pour toute foule,
    doublons ≺ recouvrements ≺ disjoint : la géométrie de h13 survit au
    minimax mot pour mot, le choix des numéros non. Vérifié point par
    point sur les 4 060 foules du jeu réduit.

(b) CE QUE CHAQUE CONNAISSANCE ACHÈTE. Pour le joueur uniformisé :
      - la MOYENNE m = N·p seule encadre le multiplicateur de partage
        dans [L(m), ≈1) — bornes atteignables des deux côtés ;
      - la FRÉQUENCE DE CHUTE q = P(au moins un gagnant) seule l'encadre
        dans (1−q, 1−q/2] : TOUT ce que la répartition de la foule peut
        encore jouer pèse moins de q/2 — au régime observé du §29
        (λ ≈ 0,01), moins d'un demi pour cent ;
      - le reste — la place dans la fourchette, et jusqu'au SIGNE de
        « furtive bat populaire » — exige la répartition, qui n'est pas
        publiée. C'est la frontière exacte de ce que « Furtif » peut
        légitimement promettre.
    Et un théorème de consolation : parmi les foules i.i.d., la foule
    UNIFORME est la pire pour le joueur uniformisé (convexité de
    π ↦ ∫(1−π(1−t))^N dt + E_D[π(D)] = p pour tout biais). Tout biais
    psychologique — dates, chiffre 7 — ne peut que l'aider. Il n'a pas
    besoin de connaître la foule : il encaisse son biais sans le modéliser.

(c) L'OBSERVABLE. q = γ·N·p exigerait γ = 1 (l'identité q ≈ N·p du §29
    suppose une foule non agglutinée) ; en général q ≤ N·p et l'écart
    γ = N·p/q = E[W | W ≥ 1] est le nombre moyen de gagnants par chute —
    le premier indice de CONCENTRATION de la foule qui soit observable.
    L'unique relevé donne μ̂·p = α·γ par mise ; les rapports entre mises
    élimineraient α et le prix du ticket — mais UN relevé exponentiel par
    mise ne contraint rien : le test de cohérence ci-dessous (null simulé,
    5 exponentielles i.i.d.) le quantifie, et la puissance mesurée dit
    combien de relevés il faudrait. Rien n'est fabriqué : q n'a jamais été
    observé, et le fichier le dit.

Les garde-fous du dossier, appliqués d'emblée
----------------------------------------------
La famine Monte-Carlo (« ×0 sur zéro événement », trois fois dans ce
dossier) est évitée PARTOUT par construction : le lemme d'uniformité sort
p en facteur EXACT et il ne reste à estimer que E_D[1/(1+W)], qui n'a
aucun événement rare ; les lois conditionnelles D ⊇ g sont échantillonnées
exactement (g ∪ 15 uniformes parmi les 75 autres) ; le jeu réduit est
énuméré, pas simulé. La §1 montre la famine en direct — 1 événement 10/10
sur 2 millions de tirages simulés, là où il en faudrait des milliers pour
un rapport — pour mémoire, pas pour mesure.

Erreurs commises pendant l'écriture, et corrigées
--------------------------------------------------
1. Le prototypage du test (c) a calculé la statistique observée AVANT que
   le jeton de pré-enregistrement ne soit scellé — une entorse à la règle 2,
   consignée dans les notes du registre. Elle ne change pas le verdict (le
   test ne rejette rien, p ≈ 0,6) mais elle en réduit la valeur
   confirmatoire à zéro ; le test vaut comme consignation, pas découverte.
2. Première idée de témoin négatif : une « fausse borne » 1 − 0,6·m — qui
   est en réalité une borne VRAIE (plus lâche que 1 − m/2, donc jamais
   violée) : un témoin qui ne peut pas sonner. Remplacée par 1 − m/3, plus
   HAUTE que le vrai minimum, que le témoin viole comme il doit.
3. La dominance des motifs a d'abord été affirmée « à l'ordre des co-gains
   près » ; la preuve propre est plus simple et pointwise (1/(j+W) est
   décroissante en j sachant le gain), et l'énumération la confirme avec
   une marge strictement positive sur TOUTES les foules du jeu réduit.

Ce que ce fichier ne prétend pas
---------------------------------
Aucun numéro n'est prédit et le théorème d'invariance n'est pas mis en
défaut : E[hits], P(gain) et tous les m_j = N·P_j sont invariants par
linéarité, quelle que soit la foule. Seule la répartition d'une mise à
espérance de hits identique est en cause. Le régime réel du barème
(quels rangs partagent) reste une propriété du règlement, non établie ici.
"""

import csv
import itertools
import math
import os
import sys
import time
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lab

T0 = time.time()
POOL, DRAWN = 80, 20
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.environ.get("H29_RECORD") == "1"
rng = np.random.default_rng(20260830)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def p_full(k: int) -> float:
    """P(k/k) — rang plein d'une grille de k numéros."""
    return comb(POOL - k, DRAWN - k) / comb(POOL, DRAWN)


def L(m: float) -> float:
    """Minorante universelle de E[1/(1+W)] sous E[W] = m, W entier ≥ 0.

    C'est l'interpolée linéaire de w ↦ 1/(1+w) aux entiers (la minorante
    convexe exacte sur ℕ), atteinte par la loi à deux points {⌊m⌋, ⌈m⌉}.
    Pour m ≤ 1 : L(m) = 1 − m/2.
    """
    f = math.floor(m)
    th = m - f
    return (1 - th) / (1 + f) + th / (2 + f)


def e_inv_binom(N: int, pi: float) -> float:
    """E[1/(1+W)] EXACT pour W ~ Binomiale(N, π) : (1−(1−π)^{N+1})/((N+1)π)."""
    if pi <= 0:
        return 1.0
    return -math.expm1((N + 1) * math.log1p(-pi)) / ((N + 1) * pi)


# --------------------------------------------------------------------------
# 0. Pré-enregistrement — les quatre jetons, scellés avant les calculs
# --------------------------------------------------------------------------

tok_jeu = lab.preregister(
    "h29.jeu_reduit", hypothesis=(
        "La valeur exacte du jeu minimax de partage réduit (8 numéros, 3 tirés, "
        "grilles de 2, foule de 3 tickets) vaut p·L(3p) = 141/1568, atteinte par "
        "les foules en triples disjoints ; la stratégie uniforme est minimax "
        "(théorème de symétrisation) et la garantie déterministe vaut p/(1+3)"),
    statistic="min sur les 4060 foules de U(uniforme, foule), énumération exacte",
    null_method="aucun (identité combinatoire) ; décision par écart numérique",
    decision="conforme si |observé − 141/1568| ≤ 1e-12 ET argmin ⊆ triples disjoints",
    track="B")

tok_dom = lab.preregister(
    "h29.dominance_motifs", hypothesis=(
        "Sous rotation uniforme, pour TOUTE foule : motif disjoint ≥ motif "
        "chevauchant ≥ motif doublon (préuve : 1/(j+W) décroissante en j sachant "
        "le gain) — la géométrie de h13 survit au pire cas, le choix des numéros non"),
    statistic="min sur les 4060 foules du jeu réduit des deux écarts de motifs (n=2)",
    null_method="aucun (dominance pointwise) ; décision par écart numérique",
    decision="conforme si les deux minima ≥ −1e-12",
    track="B")

tok_bin = lab.preregister(
    "h29.binomiale_qc", hypothesis=(
        "E[1/(1+W)] pour W ~ Bin(N,π) vaut (1−(1−π)^{N+1})/((N+1)π) — la brique "
        "exacte qui remplace le Monte-Carlo affamé partout dans h29"),
    statistic="max |z| entre formule et Monte-Carlo (2e6 tirages de W) sur 3 régimes",
    null_method="erreur-type empirique du Monte-Carlo",
    decision="conforme si max |z| < 4",
    track="B")

tok_coh = lab.preregister(
    "h29.coherence_releve", hypothesis=(
        "Sous (α·γ) identique aux cinq mises et relevés exponentiels indépendants "
        "(h15, J0=0), les cinq α̂ = J·p du relevé unique sont 5 tirages i.i.d. "
        "d'une exponentielle commune ; l'écart max/min observé n'est pas anormal"),
    statistic="log(max/min) des α̂_k = J_k·p_k, k ∈ {5,6,7,8,10}, relevé du 2026-08-30",
    null_method="SIMULÉ : 200 000 réplicats de 5 exponentielles i.i.d. (statistique "
                "pivotale, l'échelle commune s'élimine)",
    decision="hétérogénéité (foule ou α) si p < 0,05 après Holm sur le registre "
             "entier ; sinon : un relevé ne contraint pas la foule, il faut la série du §28",
    track="B")


# --------------------------------------------------------------------------
# 1. Le lemme d'uniformité, et la famine qu'il évite
# --------------------------------------------------------------------------

rule("1. LE LEMME D'UNIFORMITÉ — et la famine Monte-Carlo, montrée puis contournée")

say("   P(g ⊆ d) pour g uniforme est la même pour TOUT tirage d :")
for k in (2, 5, 10):
    lhs = comb(DRAWN, k) / comb(POOL, k)
    say(f"     k={k:<3} C(20,{k})/C(80,{k}) = {lhs:.6e} = p = {p_full(k):.6e}"
        f"   écart {abs(lhs - p_full(k)):.1e}")
    assert abs(lhs - p_full(k)) < 1e-18
say("""   Donc D | « g gagne » reste uniforme, E[gain] = J·p·E_D[1/(1+W)], et p
   sort en facteur EXACT : il ne reste à estimer que E_D[1/(1+W)], qui n'a
   aucun événement rare. C'est le renversement de conditionnement du
   dossier, appliqué avant de simuler quoi que ce soit.""")

h10 = rng.hypergeometric(DRAWN, POOL - DRAWN, 10, size=2_000_000)
say(f"\n   La famine, pour mémoire : rang 10/10 par Monte-Carlo naïf,")
say(f"   {int((h10 == 10).sum())} événement(s) sur 2 000 000 de tirages simulés "
    f"(attendu {2e6 * p_full(10):.2f}).")
say("   Tout « rapport de gains » construit là-dessus serait la quatrième")
say("   famine du dossier ; aucune quantité de h29 n'en dépend.")


# --------------------------------------------------------------------------
# 2. Le jeu réduit, énuméré — la valeur, exacte, et qui l'atteint
# --------------------------------------------------------------------------

rule("2. LE JEU RÉDUIT (8 numéros, 3 tirés, k=2, foule de 3) — ÉNUMÉRÉ")

grids2 = list(itertools.combinations(range(8), 2))          # 28 grilles
draws3 = list(itertools.combinations(range(8), 3))          # 56 tirages
WinM = np.array([[set(g) <= set(d) for d in draws3] for g in grids2])
p_r = WinM[0].sum() / len(draws3)                           # 3/28
assert abs(p_r - 3 / 28) < 1e-15

foules = list(itertools.combinations_with_replacement(range(28), 3))
Wr = np.zeros((len(foules), 56))
for i, (a, b, c) in enumerate(foules):
    Wr[i] = WinM[a].astype(int) + WinM[b] + WinM[c]
inv1 = 1.0 / (1.0 + Wr)
U_unif = p_r * inv1.mean(axis=1)                            # garantie par foule
v_obs = float(U_unif.min())
v_pred = (3 / 28) * (47 / 56)                               # p·L(3p) = 141/1568

say(f"   grilles {len(grids2)}, tirages {len(draws3)}, foules {len(foules)} — exact, zéro simulation")
say(f"   valeur observée   min_w U(uniforme, w) = {v_obs:.15f}")
say(f"   valeur prédite    p·L(3p) = 141/1568   = {v_pred:.15f}")
say(f"   écart {abs(v_obs - v_pred):.1e}")

am = np.where(U_unif < v_obs + 1e-12)[0]
am_disjoints = all(
    all(len(set(grids2[a]) & set(grids2[b])) == 0
        for a, b in itertools.combinations(foules[i], 2)) for i in am)
say(f"   argmin : {len(am)} foules, toutes en triples DISJOINTS : {am_disjoints}")
say("   -> la nature optimale étale elle aussi : trois tickets disjoints ne")
say("      co-gagnent jamais (union 4 > 3), W ∈ {0,1}, la borne L est atteinte.")

# Certificat de selle : la foule optimale symétrisée rend U(g, w̄) constant en g
# (identité d'orbite U(g, σw) = U(σ⁻¹g, w), moyenne uniforme sur l'orbite),
# donc max_x min_w = min_w max_x = 141/1568 — la VALEUR du jeu, pas une borne.
Ug_argmin = (WinM * inv1[am[0]]).mean(axis=1)               # U(g, w*) pour les 28 g
say(f"   certificat : moyenne_g U(g, w*) = {float(Ug_argmin.mean()):.15f} = valeur "
    f"(écart {abs(float(Ug_argmin.mean()) - v_obs):.1e})")

U_det = float((WinM[0] * inv1).mean(axis=1).min())          # garantie d'une grille fixe
say(f"\n   garantie d'une grille DÉTERMINISTE : {U_det:.15f} = p/(1+3) = {p_r / 4:.15f}")
say(f"   la randomisation uniforme vaut ×{v_obs / U_det:.3f} de garantie — et une")
say("   grille furtive déterministe n'a PAS mieux : le pire cas ne distingue pas")
say("   les numéros, seulement le fait d'être prévisible.")

# Témoin : une stratégie mixte NON uniforme (anti-« dates » sur {0,1,2,3}) doit
# faire strictement moins bien — le vérificateur sait distinguer.
tilt = np.array([math.exp(-1.0 * sum(x < 4 for x in g)) for g in grids2])
tilt /= tilt.sum()
Ug_all = (inv1 @ WinM.T.astype(float)) / 56          # (4060, 28) : U(g, foule)
G_tilt = float((Ug_all @ tilt).min())
say(f"\n   témoin (mixte anti-dates, non uniforme) : garantie {G_tilt:.6f} "
    f"< uniforme {v_obs:.6f} : {G_tilt < v_obs - 1e-9}")

# Témoin : la « valeur » que prédirait une foule Poisson n'est PAS la valeur
# du jeu — l'énumération a le pouvoir de le voir.
m_r = 3 * p_r
v_poisson = p_r * (1 - math.exp(-m_r)) / m_r
say(f"   témoin (formule Poisson, fausse ici) : {v_poisson:.6f} ≠ {v_obs:.6f} "
    f"(écart relatif {abs(v_poisson - v_obs) / v_obs:.1%} — détectable)")

# Recoupement Monte-Carlo (règle 4) : la colonne argmin, simulée côté tirage.
R = 400_000
idx = np.argsort(rng.random((R, 8)), axis=1)[:, :3]
inD = np.zeros((R, 8), bool)
np.put_along_axis(inD, idx, True, axis=1)
Wmc = np.zeros(R)
for gi in foules[am[0]]:
    Wmc += inD[:, grids2[gi]].all(axis=1)
mult_mc = (1.0 / (1.0 + Wmc)).mean()
se_mc = (1.0 / (1.0 + Wmc)).std() / math.sqrt(R)
mult_ex = float(inv1[am[0]].mean())
z_jeu = (mult_mc - mult_ex) / se_mc
say(f"\n   recoupement MC (400k tirages, foule argmin) : {mult_mc:.6f} "
    f"vs exact {mult_ex:.6f}   z = {z_jeu:+.2f}")

verdict_jeu = "conforme" if (abs(v_obs - v_pred) <= 1e-12 and am_disjoints) else "ÉCART"
say(f"\n   VERDICT h29.jeu_reduit : {verdict_jeu}")


# --------------------------------------------------------------------------
# 3. Les motifs de portefeuille — la dominance, pour toute foule
# --------------------------------------------------------------------------

rule("3. LES MOTIFS (n=2) — disjoint ≥ chevauchant ≥ doublon, TOUTE foule")

say("""   Sous rotation uniforme, E[gain] = Σᵢ p·E[1/(j+W) | grille i gagne] où j
   compte MES tickets gagnants. Sachant un gain, j ≥ 1, et tout recouvrement
   ne peut qu'ajouter des co-gains propres : 1/(j+W) ≤ 1/(1+W) point par
   point. La preuve est une ligne ; l'énumération vérifie qu'aucune foule ne
   la contourne, avec quelle marge.""")

inv2 = 1.0 / (2.0 + Wr)
E_pat = {}
for om in (0, 1, 2):
    if om == 2:
        inst = [(i, i) for i in range(28)]
    else:
        inst = [(i, j) for i in range(28) for j in range(i + 1, 28)
                if len(set(grids2[i]) & set(grids2[j])) == om]
    n1 = np.zeros(56)
    n2 = np.zeros(56)
    for (i, j) in inst:
        jj = WinM[i].astype(int) + WinM[j]
        n1 += (jj == 1)
        n2 += (jj == 2)
    E_pat[om] = (inv1 @ n1 + 2 * (inv2 @ n2)) / (56 * len(inst))
d01 = float((E_pat[0] - E_pat[1]).min())
d12 = float((E_pat[1] - E_pat[2]).min())
say(f"   min sur les 4060 foules :  E[disjoint] − E[chevauchant] = {d01:+.6f}")
say(f"                              E[chevauchant] − E[doublon]  = {d12:+.6f}")
say("   -> marges strictement positives : la dominance est pointwise, pas en")
say("      moyenne. En 20/80 la partition de h13 (×8,000 au rang plein, déjà")
say("      au rapport) se transporte donc telle quelle sous rotation uniforme.")

say(f"\n   Et en 20/80, l'écart entre motifs sans doublon est infime au rang")
say(f"   plein : co-gain d'une paire k=10 disjointe = 1/C(80,20) = "
    f"{1 / comb(80, 20):.2e},")
say(f"   au pire (ω=9) {p_full(10) * 10 / 70:.2e} — contre p = {p_full(10):.2e} par grille.")
say("   Le premier ordre est la marginale (invariante) ; le motif joue sur les")
say("   co-gains et la forme (h13). Les DOUBLONS, eux, coûtent au premier ordre")
say("   (théorème H) — et c'est ce que ferait une carte « Furtif » déployée en")
say("   masse : publier la même grille anti-foule à tous ses utilisateurs")
say("   FABRIQUE la foule qu'elle prétend fuir. La rotation privée est immunisée.")

verdict_dom = "conforme" if min(d01, d12) >= -1e-12 else "ÉCART"
say(f"\n   VERDICT h29.dominance_motifs : {verdict_dom} (observé min = {min(d01, d12):+.2e})")


# --------------------------------------------------------------------------
# 4. Les bornes universelles — la brique exacte, recoupée par MC
# --------------------------------------------------------------------------

rule("4. LES BORNES — L(m) atteinte, l'identité binomiale recoupée, les témoins")

say("   a) L(m) est ATTEINTE par la loi à deux points {⌊m⌋,⌈m⌉} :")
for m in (0.3, 0.9, 2.5):
    f_ = math.floor(m)
    th = m - f_
    two = (1 - th) / (1 + f_) + th / (2 + f_)
    say(f"      m={m:<5} L(m)={L(m):.6f}   deux-points={two:.6f}   écart {abs(L(m) - two):.1e}")

say("\n   b) témoin : la fausse borne « E ≥ 1 − m/3 » doit être violée —")
for m in (0.3, 0.9):
    say(f"      m={m} : deux-points {1 - m / 2:.4f} < 1 − m/3 = {1 - m / 3:.4f} : "
        f"{1 - m / 2 < 1 - m / 3}   (le vérificateur sonne)")

say("\n   c) et vers le haut, la foule agglutinée pousse E[1/(1+W)] vers 1 :")
for M in (10, 100, 10_000):
    m = 0.3
    e = 1 - m / M + (m / M) / (1 + M)
    say(f"      clump de taille {M:<7} E = {e:.6f}")
say("      -> de la moyenne seule : multiplicateur ∈ [L(m), ≈1). Large.")

say("\n   d) l'identité binomiale (la brique de tout h29), formule vs MC :")
zmax_bin = 0.0
for (N_, pi_) in ((1_000, 3e-3), (50, 0.2), (89_126, 1.1221e-7)):
    Wb = rng.binomial(N_, pi_, size=2_000_000)
    v = 1.0 / (1.0 + Wb)
    z = (v.mean() - e_inv_binom(N_, pi_)) / (v.std() / math.sqrt(len(Wb)))
    zmax_bin = max(zmax_bin, abs(z))
    say(f"      N={N_:<7} π={pi_:<10.2e} formule {e_inv_binom(N_, pi_):.6f}   "
        f"MC {v.mean():.6f}   z = {z:+.2f}")
verdict_bin = "conforme" if zmax_bin < 4 else "ÉCART"
say(f"   VERDICT h29.binomiale_qc : {verdict_bin} (max |z| = {zmax_bin:.2f})")

say("\n   e) la fourchette par la fréquence de chute q SEULE — pour le joueur")
say("      uniformisé : multiplicateur ∈ (1−q, 1−q/2], largeur q/2 :")
say("      q         plancher 1−q   plafond 1−q/2   enjeu max de la répartition")
for q in (0.006, 0.065, 0.65):
    say(f"      {q:<9} {1 - q:<14.4f} {1 - q / 2:<15.4f} {q / 2:.1%}")
say("""      (les q illustratifs sont les λ du §29 ; q n'a pas été mesuré.)
      Au régime que le §29 estime (λ ≈ 0,01), TOUT ce que la connaissance
      parfaite de la foule pourrait ajouter au joueur uniformisé pèse moins
      d'un demi pour cent. Le rang plein — le seul qui porte une grosse
      cagnotte — est précisément celui où q est petit : la promesse
      anti-foule s'effondre exactement là où l'argent est.""")


# --------------------------------------------------------------------------
# 5. Le jeu 20/80 — la valeur encadrée, et le prix du déterminisme
# --------------------------------------------------------------------------

rule("5. LE JEU 20/80 — valeur v(N) pincée, garanties comparées (unités de J·p)")

say("   k   N          m=N·p     borne basse    borne haute    haute−basse   dét. 1/(1+N)  ratio unif/dét")
for (k, N_) in ((10, 89_126), (10, 891_260), (10, 8_912_600),
                (5, 2_000), (5, 20_000)):
    p = p_full(k)
    m = N_ * p
    lo = L(m)
    hi = e_inv_binom(N_, p)
    det = 1.0 / (1 + N_)
    say(f"   {k:<3} {N_:<10,} {m:<9.4f} {lo:<14.6f} {hi:<14.6f} {hi - lo:<13.2e} "
        f"{det:<13.2e} ×{lo / det:,.0f}")
say("""
   Lecture. La borne basse est universelle (L, atteinte dans le jeu réduit
   par le design disjoint) ; la borne haute est la foule i.i.d. uniforme,
   EXACTE par l'identité binomiale. À m ≤ 1 l'écart est ≤ m²/6 : la valeur
   du jeu est déterminée sans résoudre le problème de design — et aucune
   décision ne tient dans l'écart. La dernière colonne est le prix du
   déterminisme : ce que perd, en garantie, une grille fixe — populaire,
   furtive, peu importe — face à une rotation uniforme scellée. La nature
   qui réalise ce pire cas n'est pas exotique : c'est une foule qui aime
   exactement vos numéros, et le modèle de h3 dit précisément que les
   foules aiment des numéros particuliers.""")


# --------------------------------------------------------------------------
# 6. Sous le modèle de h3 — où se place la rotation (illustration, pas preuve)
# --------------------------------------------------------------------------

rule("6. SOUS LE MODÈLE DE h3 (illustration étiquetée) — rotation vs furtive vs populaire")

say("""   Le modèle de foule de h3 (dates ≤ 31, chiffre 7, multiples de 11,
   β = 0,55) reste ce qu'il est : écrit à la main. On ne s'en sert pas pour
   prouver — on s'en sert pour situer la rotation uniforme DANS le monde où
   « Furtif » a été chiffré, et pour recouper h29 contre les nombres publiés
   de h3/§16 sans relancer h3 (règle 6).""")

pop = np.zeros(POOL)
for n in range(1, POOL + 1):
    s = 0.0
    if n <= 31: s += 1.0
    if n <= 12: s += 0.4
    if n % 10 == 7: s += 0.5
    if n % 11 == 0: s += 0.4
    if n % 10 == 0: s += 0.2
    pop[n - 1] = s
BETA = 0.55
w_crowd = np.exp(BETA * pop)
p_crowd = w_crowd / w_crowd.sum()
logw = np.log(p_crowd)

K5 = 5
order = np.argsort(-pop)
g_pop = order[:K5]
g_fur = order[-K5:]
say(f"   grille populaire {sorted(int(x) + 1 for x in g_pop)}   "
    f"furtive {sorted(int(x) + 1 for x in g_fur)}")

# Validation de l'échantillonneur (Gumbel top-k == tirage séquentiel pondéré,
# la loi de rng.choice(replace=False, p=...) utilisée par h3) sur un petit cas.
wv = np.array([5., 1., 1., 1., .5, .5, .3, .2])
pv = wv / wv.sum()
Rv = 200_000
c_ref = np.zeros((8, 8))
for _ in range(Rv // 10):
    g = rng.choice(8, size=2, replace=False, p=pv)
    c_ref[min(g), max(g)] += 1
c_ref /= (Rv // 10)
keys = np.log(pv)[None, :] + rng.gumbel(size=(Rv, 8))
top = np.argpartition(-keys, 2, axis=1)[:, :2]
c_g = np.zeros((8, 8))
np.add.at(c_g, (top.min(axis=1), top.max(axis=1)), 1.0)
c_g /= Rv
zs = []
for i in range(8):
    for j in range(i + 1, 8):
        se = math.sqrt(c_ref[i, j] * (1 - c_ref[i, j]) / (Rv // 10)
                       + c_g[i, j] * (1 - c_g[i, j]) / Rv)
        if se > 0:
            zs.append(abs(c_ref[i, j] - c_g[i, j]) / se)
say(f"   échantillonneur Gumbel top-k vs rng.choice : max |z| = {max(zs):.2f} "
    f"sur 28 cases (seuil 4) : {'ok' if max(zs) < 4 else 'ÉCART'}")

others_pop = np.setdiff1d(np.arange(POOL), g_pop)
others_fur = np.setdiff1d(np.arange(POOL), g_fur)
NBIG, NSMALL, T = 20_000, 2_000, 1_200
acc = {("rot", NBIG): [], ("pop", NBIG): [], ("fur", NBIG): [],
       ("rot", NSMALL): [], ("pop", NSMALL): [], ("fur", NSMALL): []}
wsum = {"pop": 0.0, "fur": 0.0, "rot": 0.0}
wrot = []
for t in range(T):
    keys = logw[None, :] + rng.gumbel(size=(NBIG, POOL))
    crowd = np.argpartition(-keys, K5, axis=1)[:, :K5]
    for nom, D in (("rot", rng.choice(POOL, DRAWN, replace=False)),
                   ("pop", np.concatenate([g_pop, rng.choice(others_pop, DRAWN - K5, replace=False)])),
                   ("fur", np.concatenate([g_fur, rng.choice(others_fur, DRAWN - K5, replace=False)]))):
        inD = np.zeros(POOL, bool)
        inD[D] = True
        wins = inD[crowd].all(axis=1)
        Wb, Ws = int(wins.sum()), int(wins[:NSMALL].sum())
        acc[(nom, NBIG)].append(1.0 / (1.0 + Wb))
        acc[(nom, NSMALL)].append(1.0 / (1.0 + Ws))
        wsum[nom] += Wb
        if nom == "rot":
            wrot.append(Wb)

mult = {key: float(np.mean(v)) for key, v in acc.items()}
se = {key: float(np.std(v) / math.sqrt(T)) for key, v in acc.items()}
lam_ratio = wsum["pop"] / wsum["fur"]
p5 = p_full(5)

say(f"\n   mise 5, {T} tours de foule complète, multiplicateur E[1/(1+W)] :")
say("   joueurs    populaire        rotation         furtive        fur/pop")
for N_ in (NSMALL, NBIG):
    say(f"   {N_:<10,} {mult[('pop', N_)]:.4f} ±{se[('pop', N_)]:.4f} "
        f"  {mult[('rot', N_)]:.4f} ±{se[('rot', N_)]:.4f} "
        f"  {mult[('fur', N_)]:.4f} ±{se[('fur', N_)]:.4f}"
        f"   ×{mult[('fur', N_)] / mult[('pop', N_)]:.2f}")
say(f"\n   recoupements contre les nombres PUBLIÉS de h3/§16 (voie indépendante :")
say(f"   ici la foule est simulée entière et W compté, là-bas λ exact par joueur")
say(f"   puis formule Poisson) :")
say(f"     rapport λ populaire/furtive : {lam_ratio:.2f}   (§16 : 2,7×)")
say(f"     avantage furtif à 2 000 j.  : ×{mult[('fur', NSMALL)] / mult[('pop', NSMALL)]:.2f}   (§16 : ×1,77)")
say(f"     avantage furtif à 20 000 j. : ×{mult[('fur', NBIG)] / mult[('pop', NBIG)]:.2f}   (§16 : ×2,67)")

floor_iid = e_inv_binom(NBIG, p5)
z_floor = (mult[("rot", NBIG)] - floor_iid) / se[("rot", NBIG)]
say(f"\n   le théorème « la foule i.i.d. uniforme est la PIRE » en direct :")
say(f"     plancher exact (foule uniforme, 20 000 j.) : {floor_iid:.4f}")
say(f"     rotation sous la foule BIAISÉE de h3       : {mult[('rot', NBIG)]:.4f} "
    f"(z = {z_floor:+.1f} au-dessus)")
say(f"   le biais psychologique aide le joueur uniformisé sans qu'il le modélise.")

# Invariance en direct : E[W | D uniforme] = N·p pour TOUTE foule.
mW_rot = float(np.mean(wrot))
se_Wr = float(np.std(wrot) / math.sqrt(len(wrot)))
say(f"\n   et l'invariance tient : E[W | D uniforme] = {mW_rot:.2f} ±{se_Wr:.2f} "
    f"vs N·p = {NBIG * p5:.2f} (z = {(mW_rot - NBIG * p5) / se_Wr:+.1f}) —")
say("   par linéarité, quel que soit le biais : la moyenne de W est le seul")
say("   trait de la foule que l'invariance fixe ; tout le reste est libre.")

r_fp = mult[("fur", NBIG)] / mult[("pop", NBIG)]
r_rp = mult[("rot", NBIG)] / mult[("pop", NBIG)]
say(f"""
   Lecture. SOUS le modèle de h3 — et seulement sous lui — la rotation
   uniforme réalise ×{r_rp:.2f} contre la grille populaire, là où la furtive
   atteint ×{r_fp:.2f} : en logarithme, la rotation capte
   {math.log(r_rp) / math.log(r_fp):.0%} de l'avantage modélisé, SANS le modèle,
   avec la garantie minimax en prime. Le reliquat ({math.exp(math.log(r_fp) - math.log(r_rp)):.2f}×)
   est exactement la part qui exige de croire le modèle.""")


# --------------------------------------------------------------------------
# 7. L'observable — ce que le relevé contraint, et ce qu'il faudrait
# --------------------------------------------------------------------------

rule("7. LES DONNÉES RÉELLES — γ = N·p/q, le test de cohérence, la puissance")

say("""   L'identité du §29, q ≈ N·p, est le cas γ = 1 d'une identité générale :
   q = P(W ≥ 1) ≤ E[W] = N·p (Markov), avec

       γ = N·p/q = E[W | W ≥ 1] ≥ 1   — gagnants moyens par chute,

   le premier indice de CONCENTRATION de la foule qui soit observable. Une
   foule agglutinée fait tomber la cagnotte moins souvent (q < N·p), donc
   monter plus haut : μ = r/q donne μ·p/c = α·γ. Le α̂ « anormalement
   généreux » du §29 admet ainsi une QUATRIÈME explication, qui ne contredit
   ni le relevé ni le règlement : γ > 1. Et les RAPPORTS entre mises
   élimineraient α et c :  γ_k/γ_j = (μ_k·p_k)/(μ_j·p_j).""")

stakes = (5, 6, 7, 8, 10)
with open(os.path.join(ROOT, "jackpots_observed.csv")) as fh:
    row = list(csv.DictReader(fh))[0]
say(f"   relevé unique {row['horodatage']} (tirage {row['tirage']}) — c = 1 CHF faute de prix connu :")
say("   mise   cagnotte μ̂    p exact        seuil S=1/p     α̂·γ̂ = μ̂·p")
alpha_hat = {}
for k in stakes:
    J = float(row[f"j{k}"])
    p = p_full(k)
    alpha_hat[k] = J * p
    say(f"   {k:<6} {J:<13,.0f} {p:<14.6e} {1 / p:<15,.0f} {J * p:.4f}")
say("   (seuils identiques au §28 — les trois voies p exact / hits_pmf / MC")
pmf_ok = all(abs(p_full(k) - lab.hits_pmf(k)[k]) < 1e-15 for k in stakes)
h5mc = rng.hypergeometric(DRAWN, POOL - DRAWN, 5, size=2_000_000)
n5 = int((h5mc == 5).sum())
z5 = (n5 - 2e6 * p_full(5)) / math.sqrt(2e6 * p_full(5))
say(f"    concordent : hits_pmf {pmf_ok}, MC 5/5 {n5} vs {2e6 * p_full(5):.0f} attendus, "
    f"z = {z5:+.2f}.)")

vals = np.array([alpha_hat[k] for k in stakes])
obs_coh = math.log(vals.max() / vals.min())
say(f"\n   Les cinq μ̂·p s'étalent de {vals.min():.3f} à {vals.max():.3f} — max/min "
    f"= {vals.max() / vals.min():.2f}.")
say("   Si γ et α étaient communs, ces cinq nombres seraient 5 exponentielles")
say("   i.i.d. (un relevé d'âge exponentiel par mise, h15). Test, null SIMULÉ :")

sim = rng.standard_exponential((200_000, 5))
st = np.log(sim.max(axis=1) / sim.min(axis=1))
p_ge = (1 + int((st >= obs_coh).sum())) / (1 + len(st))
p_le = (1 + int((st <= obs_coh).sum())) / (1 + len(st))
p_coh = min(1.0, 2 * min(p_ge, p_le))
say(f"     stat log(max/min) = {obs_coh:.3f}   médiane null = {np.median(st):.3f} "
    f"(ratio typique ×{math.exp(float(np.median(st))):.1f} !)")
say(f"     p empirique bilatéral = {p_coh:.3f}")
say("   -> UN relevé ne contraint pas la foule : l'écart ×7,8 observé est plus")
say("      SERRÉ que la médiane du pur bruit. Le γ 6× plus fort aux petites")
say("      mises reste une lecture possible du relevé, pas une mesure.")

say("\n   Puissance mesurée (obligation du labo) : probabilité de détecter une")
say("   hétérogénéité γ ×8 (resp. ×3) sur deux mises, selon le nombre de")
say("   relevés indépendants par mise — moyennes de n âges exponentiels :")
say("   n relevés   seuil 5% (null)    puissance ×8    puissance ×3")
for n_r in (1, 3, 10, 30, 100):
    null_n = rng.gamma(n_r, size=(60_000, 5)) / n_r
    stn = np.log(null_n.max(axis=1) / null_n.min(axis=1))
    lo, hi = np.quantile(stn, [0.025, 0.975])
    pow_ = {}
    for fac in (8.0, 3.0):
        alt = rng.gamma(n_r, size=(60_000, 5)) / n_r
        alt[:, :2] *= fac
        sta = np.log(alt.max(axis=1) / alt.min(axis=1))
        pow_[fac] = float(((sta < lo) | (sta > hi)).mean())
    say(f"   {n_r:<11} [{lo:.2f}, {hi:.2f}]       {pow_[8.0]:<15.1%} {pow_[3.0]:.1%}")
say("""   -> même une foule ×8 plus agglutinée à deux mises est invisible sur un
      relevé (puissance ≈ 5 %, le niveau du test). Une trentaine de relevés
      la verrait ; une centaine verrait ×3. C'est la MÊME série que le §28
      réclame déjà — les chutes comptées donneraient q̂ directement, et
      alors :  N ≥ q̂/p (sans AUCUNE hypothèse de répartition), γ̂ par
      rapports de mises sans connaître ni α ni le prix du ticket.""")

verdict_coh = ("hétérogénéité (α ou foule)" if p_coh < 0.05
               else "un relevé ne contraint pas la foule — série du §28 requise")
say(f"   VERDICT h29.coherence_releve : {verdict_coh} (p = {p_coh:.3f})")


# --------------------------------------------------------------------------
# 8. Consignation, et la lecture qui reste
# --------------------------------------------------------------------------

rule("8. REGISTRE")

if RECORD:
    lab.record(tok_jeu, observed=v_obs, verdict=verdict_jeu,
               notes=f"prédit 141/1568={v_pred:.12e} ; argmin {len(am)} foules toutes "
                     f"disjointes={am_disjoints} ; certificat de selle écart "
                     f"{abs(float(Ug_argmin.mean()) - v_obs):.1e} ; garantie déterministe "
                     f"p/(1+3) exacte ; recoupé MC z={z_jeu:+.2f} ; témoin Poisson "
                     f"écarté ({abs(v_poisson - v_obs) / v_obs:.1%}).")
    lab.record(tok_dom, observed=min(d01, d12), verdict=verdict_dom,
               notes=f"marges min sur 4060 foules : disjoint−chevauchant {d01:+.4f}, "
                     f"chevauchant−doublon {d12:+.4f} ; dominance pointwise prouvée "
                     f"(1/(j+W) décroissante en j sachant le gain).")
    lab.record(tok_bin, observed=zmax_bin, verdict=verdict_bin,
               notes="régimes (1000,3e-3), (50,0.2), (89126,1.12e-7) ; la brique exacte "
                     "qui évite toute famine MC dans h29.")
    lab.record(tok_coh, observed=obs_coh, p=p_coh, verdict=verdict_coh,
               notes="ENTORSE DISCLOSÉE à la règle 2 : la statistique a été prototypée "
                     "avant le scellement du jeton (les relevés étaient de toute façon "
                     "publiés au §29) — valeur confirmatoire nulle, consigné pour le "
                     "registre. Puissance sur 1 relevé ≈ 5 % contre γ ×8 ; ~30 relevés "
                     "pour ×8, ~100 pour ×3. α̂γ̂ par mise : "
                     + ", ".join(f"{k}:{alpha_hat[k]:.3f}" for k in stakes) + ".")
    say("   4 lignes ajoutées au registre (ajout seul).")
    hh = [r for r in lab.holm() if r["id"] == "h29.coherence_releve"]
    if hh:
        say(f"   Holm, registre entier (m={hh[0]['m_total']}) : "
            f"p={hh[0]['p']:.3f} vs seuil {hh[0]['holm_threshold']:.2e} — "
            f"significatif : {hh[0]['significant']}")
else:
    say("   MODE SEC (H29_RECORD≠1) : rien n'est écrit au registre — les mises au")
    say("   point ne polluent pas le compte de multiplicité du labo.")

rule("9. CE QUI EST PROUVÉ, CE QUI NE L'EST PAS")
say("""   PROUVÉ, sans rien savoir de la foule :
     1. La grille uniformément aléatoire est EXACTEMENT minimax
        (symétrisation) ; valeur v(N) ∈ [L(N·p), borne binomiale], pincée à
        m²/6 près, atteinte à 141/1568 exactement dans le jeu réduit.
     2. Une grille déterministe — furtive comprise — n'a pour garantie que
        J·p/(1+N) : le pire cas ne lit pas les numéros, il lit la
        prévisibilité. « Éviter la foule » n'est pas prouvable ; « être
        imprévisible » l'est, et vaut un facteur (1+N)·v(N).
     3. Pour les portefeuilles : rotation uniforme d'un motif à
        recouvrement minimal — la géométrie de h13 survit au pire cas,
        dominance pointwise ; les doublons restent le seul coût du premier
        ordre, et une carte anti-foule PUBLIÉE en serait un à l'échelle.
     4. Face à toute foule i.i.d., la foule uniforme est la pire : le
        joueur uniformisé encaisse tout biais psychologique sans le
        modéliser.
     5. La fréquence de chute q borne à q/2 tout ce que la répartition de
        la foule peut encore jouer pour lui — et q est petit précisément
        là où la cagnotte est grosse.

   PAS PROUVABLE sans modèle de foule : le SIGNE même de « furtive bat
   populaire », donc les ×1,77–×2,67 de h3. Sous le modèle de h3, la
   rotation en capte l'essentiel ; le reliquat est la part de foi.

   POUR L'APP : la carte « Furtif » doit devenir « rotation scellée » —
   garder la construction de h13 (recouvrements minimaux), lui appliquer
   une permutation uniforme des 80 numéros tirée en privé, et reléguer le
   penchant anti-dates au rang de pari conditionnel qu'il a toujours été.
   Rien ici ne prédit un numéro ; l'invariance sort intacte — renforcée :
   c'est elle (le lemme d'uniformité) qui rend la garantie calculable.""")

rule(f"total {time.time() - T0:.0f}s")
