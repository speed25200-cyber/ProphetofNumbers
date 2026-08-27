"""La borne CONDITIONNELLE : le dernier endroit où un avantage pourrait se cacher.

`c0_plafond.py` a borné les biais marginaux : +1,33 % de rendement au maximum
pour un biais qui aurait échappé aux 70 560 tirages. Sa limite n°2 déclarait
ouvert le cas conditionnel — une loi du tirage t+1 qui dépend du tirage t.

Ce que le registre couvre déjà, et ce qu'il ne couvre pas
---------------------------------------------------------
Le test des analogues (§11 de l'audit) couvre la structure conditionnelle
DÉTERMINISTE : si S_{t+1}=g(S_t) avec ≤ 40 bits d'état, une collision d'état
force des tirages suivants identiques — et il rend zéro. Ce qu'il ne voit
pas : une dépendance STATISTIQUE de premier ordre, où chaque numéro voit sa
probabilité modulée par le tirage précédent sans qu'aucun état ne se répète.
À d = 0,01 l'information mutuelle par pas est de l'ordre de 10⁻³ bit : aucune
collision, aucun analogue. Le χ² marginal (§1, c0) y est aveugle par
construction : la famille ci-dessous laisse les 80 marginales à 1/4 exactement.

Famille formalisée — premier ordre linéaire
--------------------------------------------
    P(n ∈ tirage t+1 | tirage t) = 1/4 + Σ_j M[n,j] · (x_j(t) − 1/4)

80×80 = 6 400 paramètres, contre 80 pour le cas marginal. Sous-cas :

  - M = d·I : RÉMANENCE (d>0) / répulsion (d<0). Le cas physiquement
    naturel (usure, mélange insuffisant, fuite d'état du générateur).
  - M = d·P, P permutation SANS POINT FIXE (« paires cachées ») : le cas
    adverse — même avantage pour qui connaît P, mais invisible du
    recouvrement, qui ne regarde que la diagonale.
  - parcimonie : seulement m lignes non nulles (m paires modulées).

Un seul terme par ligne est adversairement optimal : répartir la masse d'une
ligne sur r sources divise l'écart-type de la modulation par √r sans réduire
la masse détectable dans Ĉ — l'adversaire concentre. Le nombre de lignes m,
lui, est balayé plus bas, pas supposé.

Concrètement : chaque numéro modulé n a une « source » s(n) ; si s(n) est
sorti au tirage t, P(n au t+1) = 1/4 + d, sinon 1/4 − d/3 (compensation qui
fige la marginale à 1/4 : P(source sortie) = 1/4).

Les deux tests, et pourquoi ceux-là
-----------------------------------
  T1 = recouvrement moyen O(t,t+1) sur les 70 559 paires consécutives.
       C'est le test du SCORE de la famille diagonale (la dérivée de la
       log-vraisemblance en d=0 est ∝ Σ_t O_t) : localement le plus
       puissant possible contre rémanence/répulsion uniforme. E[T1|H0]=5,
       mais moyenne ET écart-type sont simulés, jamais tabulés — les
       paires consécutives partagent un tirage sur deux.
  T2 = ‖Ĉ‖²_F : somme des carrés des 6 400 covariances croisées lag-1
       (colonnes centrées). Invariante par permutation des numéros : elle
       couvre TOUTE matrice M, paires cachées comprises. Contre la
       structure optimale de l'adversaire (~40 entrées non nulles), la
       somme des carrés bat la statistique du max : le max exige ~5,9
       écarts-types sur UNE entrée (quantile registre du max de 6 400),
       la somme des carrés se contente de ~2,5 par entrée répartis sur 40.

L'avantage du joueur conditionnel
----------------------------------
Il voit le tirage t, calcule les numéros « chauds » (ceux dont la source est
sortie — en moyenne m/4, exactement 20 si m=80), coche les min(chauds,10)
plus favorisés et complète par des numéros neutres. Avantage attendu
≈ E[min(|chauds|,10)]·d_eff — mais il est MESURÉ en jouant la stratégie sur
les archives contaminées, pas déduit. d<0 (répulsion) donne 3× moins
d'avantage à |d| égal (les froids ne gagnent que |d|/3) : l'adversaire
joue d>0.

Limites déclarées
------------------
 1. Comme c0 : le seuil registre (z≈4,3) extrapole la queue du null en
    gaussienne ; 300 réplicats ne donnent pas un quantile à 1,5e-05.
 2. La famille est de premier ordre LINÉAIRE en lag 1. Le lag seul n'est
    pas une échappatoire : couvrir les lags 1..100 par Bonferroni ne
    monte le seuil que de z=4,32 à ≈4,75, soit ~5 % sur d. Une dépendance
    NON LINÉAIRE du tirage complet (fonction de combinaisons), elle,
    n'est pas bornée ici — c'est la limite ouverte que ce script lègue.
 3. REPS_POWER = 60 (contre 200 dans c0), dit plutôt que caché : la
    génération conditionnelle est séquentielle (~1 s par archive de
    70 560 tirages), le balayage complet dépasserait l'heure. À 50 % de
    puissance l'incertitude est ±6,5 points — sans effet sur l'ordre de
    grandeur de la borne (la puissance passe de ~10 % à ~90 % sur un
    facteur ~1,6 en d, cf. tableaux).

Usage : python c1_conditionnel.py [--dry]   (--dry : réplicats réduits,
n'écrit PAS au registre — mise au point uniquement)
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

N = 70_560
K = 10
DRY = "--dry" in sys.argv
REPS_NULL = 40 if DRY else 300
REPS_POWER = 8 if DRY else 60
R_SWEEP = 2 if DRY else 3          # archives par point du balayage de structure
R_EDGE = 3 if DRY else 12          # archives pour mesurer l'avantage à l'enveloppe


# --------------------------------------------------------------------------
# Statistiques
# --------------------------------------------------------------------------

def t1_overlap(mask):
    """Recouvrement moyen des paires consécutives. E[.|H0] = 5 — simulé quand même."""
    return float((mask[1:] & mask[:-1]).sum() / (len(mask) - 1))


def t2_lagcov(mask):
    """‖Ĉ‖²_F : somme des carrés des 6 400 covariances croisées lag-1."""
    x = mask.astype(np.float32)
    x -= x.mean(0)
    c = x[1:].T @ x[:-1] / np.float32(len(x) - 1)
    return float((c * c).sum(dtype=np.float64))


# --------------------------------------------------------------------------
# L'alternative : génération séquentielle (chaque tirage dépend du précédent)
# --------------------------------------------------------------------------

def pairing(m, rng):
    """m numéros modulés + leurs sources, sur un 80-cycle aléatoire.

    Un cycle unique garantit une permutation SANS point fixe (dérangement) :
    aucune composante diagonale, donc rien pour T1 — c'est le choix de
    l'adversaire, vérifié plus bas (z_T1 mesuré ≈ 0 sous contamination).
    """
    perm = rng.permutation(lab.POOL)
    src_of = np.empty(lab.POOL, np.int64)
    src_of[perm] = perm[np.roll(np.arange(lab.POOL), -1)]
    mod = perm[:m]
    return mod, src_of[mod]


def gen_conditional(n, mod, msrc, d, rng):
    """n tirages où P(n° modulé) = 1/4+d si sa source est sortie en t-1, 1/4-d/3 sinon.

    Gumbel top-20 par pas (échantillonnage sans remise), donc SÉQUENTIEL :
    ~1 s par archive. Les probabilités réalisées sont mesurées, pas supposées.
    """
    lo = np.log(0.25 / 0.75)
    lo_hot = np.log((0.25 + d) / (0.75 - d)) - lo
    lo_cold = np.log((0.25 - d / 3) / (0.75 + d / 3)) - lo
    g = rng.gumbel(size=(n, lab.POOL))
    out = np.zeros((n, lab.POOL), bool)
    idx = np.argpartition(-g[0], lab.DRAWN)[:lab.DRAWN]
    out[0, idx] = True
    prev = out[0]
    for t in range(1, n):
        keys = g[t].copy()
        keys[mod] += np.where(prev[msrc], lo_hot, lo_cold)
        idx = np.argpartition(-keys, lab.DRAWN)[:lab.DRAWN]
        out[t, idx] = True
        prev = out[t]
    return out


def informed_play(cm, mod, msrc, rng):
    """Joue la stratégie du joueur qui CONNAÎT la règle, mesure tout.

    Priorité chauds (2) > neutres (1) > froids modulés (0), départage
    aléatoire ; grille de K numéros choisie sur le tirage précédent.
    Renvoie (E[hits], p_chaud réalisé, p_froid réalisé, E[min(chauds,K)]).
    """
    n = len(cm)
    hot = cm[:-1][:, msrc]                                   # (n-1, m)
    prio = np.ones((n - 1, lab.POOL), np.float32)
    prio[:, mod] = np.where(hot, np.float32(2.0), np.float32(0.0))
    prio += rng.random((n - 1, lab.POOL), dtype=np.float32) * np.float32(0.5)
    idx = np.argpartition(-prio, K, axis=1)[:, :K]
    hits = np.take_along_axis(cm[1:], idx, axis=1).sum(1)
    nxt = cm[1:][:, mod]
    return (float(hits.mean()), float(nxt[hot].mean()), float(nxt[~hot].mean()),
            float(np.minimum(hot.sum(1), K).mean()))


def measure(m, d, reps, rng, null1, null2, diag=False):
    """R archives contaminées : avantage joué, z des deux tests, p réalisées."""
    adv, z1, z2, ph, pc, mh = [], [], [], [], [], []
    for _ in range(reps):
        if diag:
            mod = msrc = np.arange(lab.POOL)
        else:
            mod, msrc = pairing(m, rng)
        cm = gen_conditional(N, mod, msrc, d, rng)
        h, p_hot, p_cold, min_hot = informed_play(cm, mod, msrc, rng)
        adv.append(h - K / 4)
        z1.append(null1.z(t1_overlap(cm)))
        z2.append(null2.z(t2_lagcov(cm)))
        ph.append(p_hot); pc.append(p_cold); mh.append(min_hot)
    f = lambda v: float(np.mean(v))
    return dict(adv=f(adv), z1=f(z1), z2=f(z2), p_hot=f(ph), p_cold=f(pc),
                min_hot=f(mh), se_adv=float(np.std(adv, ddof=1) / np.sqrt(reps)) if reps > 1 else float("nan"))


def main():
    t00 = time.time()
    print("=" * 78)
    print("BORNE CONDITIONNELLE — le meilleur biais de premier ordre qui aurait échappé")
    print("=" * 78)
    if DRY:
        print("*** DRY RUN : réplicats réduits, AUCUNE écriture au registre ***")

    # -- 0. seuil du registre entier ---------------------------------------
    rows = lab.ledger()
    m_tests = len(rows) + sum(int(r.get("m_extra", 0)) for r in rows)
    from scipy.stats import norm
    z_crit = float(norm.isf(0.05 / m_tests / 2))
    print(f"\nregistre : m = {m_tests} tests déjà dépensés -> seuil z = {z_crit:.2f} "
          f"(p < {0.05 / m_tests:.2e})")

    # -- 1. nulls simulés (jamais tabulés) ---------------------------------
    t0 = time.time()
    null1 = lab.calibrate(t1_overlap, N, reps=REPS_NULL, seed=101)
    null2 = lab.calibrate(t2_lagcov, N, reps=REPS_NULL, seed=102)
    print(f"\nnulls simulés ({REPS_NULL} archives SRS complètes, {time.time()-t0:.0f}s) :")
    print(f"  T1 recouvrement moyen : {null1.mean:.5f} +- {null1.sd:.5f}")
    sd_naif = float(np.sqrt(20 * 0.25 * 0.75 * 60 / 79 / (N - 1)))
    print(f"     attendu analytique 5,0 ; sd si paires non corrélées {sd_naif:.5f} "
          f"(écart {abs(null1.sd - sd_naif) / sd_naif:+.1%} — le simulé fait foi)")
    print(f"  T2 somme des carrés Ĉ : {null2.mean:.6e} +- {null2.sd:.2e}")

    # -- 2. pré-enregistrement AVANT tout regard sur les vraies données ----
    tok1 = lab.preregister(
        "c1.overlap_real",
        "Pas de rémanence/répulsion lag-1 : E[overlap(t,t+1)] sur les 70 559 paires "
        "consécutives est compatible SRS",
        "recouvrement moyen des paires consécutives (T1, test du score de la famille diagonale)",
        f"simulation : {REPS_NULL} archives SRS complètes de 70 560 tirages, statistique identique",
        f"conforme si p empirique > seuil Holm registre ({0.05 / m_tests:.2e}) ; "
        "|z|>3 déclenche d'abord une chasse à l'artefact (leçon du §14)",
        track="A")
    tok2 = lab.preregister(
        "c1.matrix_real",
        "Pas de dépendance linéaire de premier ordre t->t+1 : la somme des carrés des "
        "6 400 covariances croisées lag-1 est compatible SRS",
        "‖Ĉ‖²_F lag-1, colonnes centrées (T2, couvre toute matrice M, paires cachées comprises)",
        f"simulation : {REPS_NULL} archives SRS complètes de 70 560 tirages, statistique identique",
        f"conforme si p empirique > seuil Holm registre ({0.05 / m_tests:.2e}) ; "
        "|z|>3 déclenche d'abord une chasse à l'artefact (leçon du §14)",
        track="A")
    tok3 = lab.preregister(
        "c1.plafond_cond",
        "Borne supérieure sur l'avantage d'un biais CONDITIONNEL de premier ordre "
        "(linéaire, lag 1) ayant échappé à 70 560 tirages face aux tests T1+T2",
        "avantage E[hits]-2,5 du joueur qui adapte sa grille au tirage précédent, "
        "au plus gros d gardant puissance < 50 % au seuil du registre",
        f"simulation : nulls T1/T2 sur {REPS_NULL} archives SRS ; puissance sur "
        f"{REPS_POWER} archives contaminées générées séquentiellement",
        "borne, pas un test : aucune hypothèse nulle n'est rejetée ici",
        track="A")

    # -- 3. structure de l'adversaire : combien de paires moduler ? --------
    print(f"\n{'-' * 78}\n1. Structure de l'adversaire (paires cachées) : combien de lignes m ?")
    print("   d ajusté pour amener E[T2] au seuil (mesuré, échelle ΔS ∝ m·d²) ; "
          "avantage JOUÉ.\n")
    rng = np.random.default_rng(20260827)
    target = z_crit * null2.sd
    print(f"{'m':>4} {'d@seuil':>9} {'p_chaud':>8} {'E[min(H,10)]':>12} "
          f"{'avantage':>9} {'rendement':>9} {'z_T2':>6} {'z_T1':>6}")
    best = None
    for m in (10, 20, 30, 40, 50, 60, 80):
        d0 = min(0.010 * np.sqrt(40 / m), 0.02)
        ds0 = np.mean([t2_lagcov(gen_conditional(N, *pairing(m, rng), d0, rng))
                       for _ in range(R_SWEEP)]) - null2.mean
        d_m = float(d0 * np.sqrt(target / max(ds0, 1e-12)))
        r = measure(m, d_m, R_SWEEP, rng, null1, null2)
        print(f"{m:>4} {d_m:>9.4f} {r['p_hot']:>8.4f} {r['min_hot']:>12.2f} "
              f"{r['adv']:>+9.4f} {r['adv'] / (K / 4):>+8.2%} {r['z2']:>6.1f} {r['z1']:>6.1f}")
        if best is None or r["adv"] > best[2]:
            best = (m, d_m, r["adv"])
    m_star = best[0]
    print(f"\n  -> optimum empirique : m = {m_star} lignes modulées "
          f"(z_T1 ≈ 0 partout : le dérangement rend T1 aveugle, comme prévu)")

    # -- 4. puissance mesurée, famille diagonale (rémanence) vs T1 ---------
    print(f"\n{'-' * 78}\n2. Rémanence uniforme (M = d·I) contre T1 — "
          f"puissance sur {REPS_POWER} archives contaminées")
    print(f"{'d':>9} {'puissance T1':>13}")
    env_diag = None
    diag_id = np.arange(lab.POOL)
    for i, d in enumerate((0.0009, 0.0011, 0.0013, 0.0016, 0.0020)):
        pw = lab.power(t1_overlap,
                       lambda mask, rg, d=d: gen_conditional(len(mask), diag_id, diag_id, d, rg),
                       N, null1, reps=REPS_POWER, seed=300 + i, alpha_z=z_crit)
        print(f"{d:>9.4f} {pw:>13.0%}")
        if pw < 0.5:
            env_diag = d
    r_diag = measure(80, env_diag, R_EDGE, rng, null1, null2, diag=True)
    adv_diag = r_diag["adv"]
    print(f"\n  enveloppe : d = {env_diag:.4f} -> avantage joué (10 chauds sur les 20 "
          f"du tirage précédent)\n  = {adv_diag:+.4f} +- {r_diag['se_adv']:.4f} hits sur 2,5 "
          f"({adv_diag / (K / 4):+.2%}) ; p_chaud réalisée {r_diag['p_hot']:.4f}")
    print(f"  contre-vérification : à cette enveloppe z_T2 = {r_diag['z2']:+.1f} "
          f"(T2 ne le rattrape pas)")

    # -- 5. puissance mesurée, paires cachées à m* vs T2 -------------------
    print(f"\n{'-' * 78}\n3. Paires cachées (m = {m_star}) contre T2 — "
          f"puissance sur {REPS_POWER} archives contaminées")
    print(f"{'d':>9} {'puissance T2':>13}")
    d_ref = best[1]
    env_pair = None
    for i, f in enumerate((0.65, 0.8, 0.9, 1.0, 1.15)):
        d = round(f * d_ref, 4)

        def contaminate(mask, rg, d=d):
            return gen_conditional(len(mask), *pairing(m_star, rg), d, rg)

        pw = lab.power(t2_lagcov, contaminate, N, null2,
                       reps=REPS_POWER, seed=400 + i, alpha_z=z_crit)
        print(f"{d:>9.4f} {pw:>13.0%}")
        if pw < 0.5:
            env_pair = d
    r_pair = measure(m_star, env_pair, R_EDGE, rng, null1, null2)
    adv_pair = r_pair["adv"]
    print(f"\n  enveloppe : d = {env_pair:.4f} -> avantage joué "
          f"= {adv_pair:+.4f} +- {r_pair['se_adv']:.4f} hits sur 2,5 ({adv_pair / (K / 4):+.2%})")
    print(f"  p_chaud réalisée {r_pair['p_hot']:.4f}, p_froid {r_pair['p_cold']:.4f}, "
          f"E[min(chauds,10)] = {r_pair['min_hot']:.2f}")
    print(f"  contre-vérification : z_T1 = {r_pair['z1']:+.1f} (aveugle), "
          f"z_T2 = {r_pair['z2']:+.1f} (au bord du seuil {z_crit:.2f}, comme il se doit)")

    # -- 6. les VRAIES données ---------------------------------------------
    print(f"\n{'-' * 78}\n4. Les vraies données (70 560 tirages)")
    a = lab.load()
    assert len(a) == N
    obs1 = t1_overlap(a.mask)
    obs2 = t2_lagcov(a.mask)
    z1, p1 = null1.z(obs1), null1.p_two_sided(obs1)
    z2, p2 = null2.z(obs2), null2.p_two_sided(obs2)
    ov = (a.mask[1:] & a.mask[:-1]).sum(1)
    print(f"  T1 recouvrement moyen : {obs1:.5f}   z = {z1:+.2f}   p = {p1:.3f}")
    print(f"  T2 somme carrés Ĉ    : {obs2:.6e}   z = {z2:+.2f}   p = {p2:.3f}")
    print(f"  diagnostic : recouvrement max observé {ov.max()} "
          f"(P(O>=15|H0) par paire ≈ {float(lab.overlap_pmf()[15:].sum()):.1e}), "
          f"#paires O>=12 : {int((ov >= 12).sum())}")
    verdict1 = "conforme H0" if p1 > 0.05 / m_tests else "A EXAMINER (artefact d'abord)"
    verdict2 = "conforme H0" if p2 > 0.05 / m_tests else "A EXAMINER (artefact d'abord)"

    # -- 7. registre --------------------------------------------------------
    if not DRY:
        lab.record(tok1, observed=obs1, null=null1,
                   power_at=f"rémanence uniforme : 50 % entre d={env_diag:.4f} et le cran supérieur "
                            f"(grille de puissance mesurée, {REPS_POWER} réplicats)",
                   verdict=verdict1,
                   notes=f"70 559 paires consécutives ; null sd {null1.sd:.5f} vs "
                         f"{sd_naif:.5f} si paires indépendantes ; O max {ov.max()}.")
        lab.record(tok2, observed=obs2, null=null2,
                   power_at=f"paires cachées m={m_star} : 50 % entre d={env_pair:.4f} et le cran "
                            f"supérieur ({REPS_POWER} réplicats)",
                   verdict=verdict2,
                   notes="somme des carrés des 6 400 covariances croisées lag-1, colonnes centrées ; "
                         "couvre toute matrice de premier ordre, dérangements compris.")
        lab.record(tok3, observed=adv_pair, null=None, p=None,
                   power_at=f"50 % à d={env_pair:.4f} (paires cachées, m={m_star}) ; "
                            f"rémanence uniforme bornée plus bas : {adv_diag:+.4f} hits à d={env_diag:.4f}",
                   verdict="borne établie",
                   notes=(f"Avantage conditionnel max non détecté = {adv_pair:+.4f} hits sur 2,5 "
                          f"({adv_pair / (K / 4):+.2%}), contre +1,33 % marginal (c0) et "
                          f"{adv_diag / (K / 4):+.2%} pour la rémanence uniforme. "
                          f"Seuil registre m={m_tests}, z={z_crit:.2f}. Famille : premier ordre "
                          f"linéaire lag 1 ; non-linéaire non borné (limite déclarée)."))

    # -- 8. synthèse --------------------------------------------------------
    print(f"\n{'=' * 78}\nSYNTHÈSE — plafonds de la piste A, par famille de biais")
    print(f"{'famille':<42} {'test qui borne':<16} {'avantage max':>12} {'rendement':>9}")
    print(f"{'marginal (c0, m=10 numéros poussés)':<42} {'chi2 80 cases':<16} "
          f"{'+0.0332':>12} {'+1.33%':>9}")
    print(f"{'conditionnel diagonal (rémanence uniforme)':<42} {'T1 recouvrement':<16} "
          f"{adv_diag:>+12.4f} {adv_diag / (K / 4):>+8.2%}")
    print(f"{'conditionnel général (paires cachées, m=' + str(m_star) + ')':<42} "
          f"{'T2 ‖Ĉ‖²':<16} {adv_pair:>+12.4f} {adv_pair / (K / 4):>+8.2%}")
    print(f"\nLa borne conditionnelle est {adv_pair / 0.0332:.1f}× la borne marginale : "
          f"plus de paramètres, moins de puissance par direction, borne plus haute —")
    print(f"mais la rémanence NATURELLE est bornée plus bas que le marginal : "
          f"le recouvrement agrège les 20 numéros à chaque pas.")
    print(f"\nVraies données : T1 z={z1:+.2f} (p={p1:.3f}), T2 z={z2:+.2f} (p={p2:.3f}) — "
          f"{'rien à signaler' if max(abs(z1), abs(z2)) < 3 else 'VOIR CHASSE A L ARTEFACT'}.")
    print(f"{'(dry run : rien consigné)' if DRY else 'consigné au registre (3 entrées).'} "
          f"total {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
