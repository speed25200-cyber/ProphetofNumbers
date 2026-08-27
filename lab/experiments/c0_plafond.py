"""Le plafond : quel avantage pourrait encore exister sans avoir été vu ?

Quatorze voies d'audit ont rendu zéro. Mais « on n'a rien trouvé » et
« il n'y a rien » sont deux affirmations différentes, et seule la seconde
intéresse quelqu'un qui veut savoir de combien il peut améliorer ses
prédictions. La question exacte est :

    Parmi tous les biais qui auraient ÉCHAPPÉ à 70 560 tirages, quel est
    celui qui donne le plus gros avantage à un joueur qui le connaîtrait ?

C'est une borne supérieure sur toute la piste A. Elle ne suppose aucun
biais — elle chiffre ce que l'ignorance résiduelle peut au maximum valoir.

Construction de l'adversaire le plus efficace
---------------------------------------------
Un biais marginal qui pousse `m` numéros de `+d` chacun (et retire le
complément sur les 80-m autres) donne, pour une grille de k=10 numéros :

    avantage  = min(m, 10) · d
    chi2      ∝ N · d² · m · 80/(80-m)

À chi2 fixé — donc à détectabilité fixée — l'avantage est maximal en
**m = 10** : au-dessous, on perd des numéros à cocher ; au-dessus, on
dilue `d` sans que la grille en profite. L'adversaire optimal biaise donc
exactement autant de numéros que la grille en coche. Vérifié par balayage
plus bas plutôt que supposé.

On ne suppose pas non plus que les probabilités d'inclusion valent les
poids : le tirage biaisé est simulé (Gumbel top-20, c.-à-d. échantillonnage
successif sans remise), et les probabilités d'inclusion réalisées sont
MESURÉES. C'est la règle du labo — le null et l'alternative sont simulés,
jamais tabulés.

Deux limites, à porter avec le résultat
---------------------------------------
1. Le seuil de détection extrapole la queue du null par une gaussienne
   (z = 4,32 pour m = 3 228 tests). 300 réplicats ne permettent pas de
   lire empiriquement un quantile à 1,5e-05 ; le χ² à 80 cellules est
   proche de la normalité, donc l'extrapolation est raisonnable, mais
   c'est une approximation et non une mesure. Elle déplace le seuil, pas
   l'ordre de grandeur : la courbe de puissance passe de 1 % à 44 % entre
   d = 0,002 et d = 0,003, donc la frontière est franche et un seuil
   légèrement différent ne déplace guère la borne.

2. La borne couvre les biais MARGINAUX — une déformation des fréquences
   des 80 numéros. Le cas CONDITIONNEL (la loi du tirage dépendant du
   précédent) n'est pas couvert. On serait tenté de dire qu'il a plus de
   paramètres, donc se détecte moins bien, donc que sa borne est plus
   haute — mais c'est un raisonnement qui ne tient pas : sur la famille
   la plus simple, le recouvrement moyen agrège 20 numéros à chaque pas
   et devient très sensible, ce qui pourrait rendre la borne plus BASSE.
   La question est traitée dans `c1_conditionnel.py` par le calcul, pas
   ici par l'intuition. Indépendamment, le test des analogues (§11 de
   l'audit) couvre déjà la structure conditionnelle issue d'un état
   déterministe jusqu'à 40 bits, et rend zéro.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

N = 70_560
K = 10
REPS_NULL = 300
REPS_POWER = 200


def biased(n, w, rng):
    """n tirages 20/80 avec poids `w` — Gumbel top-k (échantillonnage successif)."""
    g = rng.gumbel(size=(n, lab.POOL))
    keys = np.log(w)[None, :] + g
    idx = np.argpartition(-keys, lab.DRAWN, axis=1)[:, :lab.DRAWN]
    out = np.zeros((n, lab.POOL), bool)
    np.put_along_axis(out, idx, True, axis=1)
    return out


def weights(m, d):
    """m numéros à p = 0,25 + d ; le reste compense pour garder 20 boules."""
    q = np.full(lab.POOL, 0.25)
    q[:m] += d
    q[m:] -= m * d / (lab.POOL - m)
    return q / (1 - q)          # odds : ce que Gumbel top-k consomme


def chi2(mask):
    c = mask.sum(0).astype(float)
    E = mask.shape[0] * lab.DRAWN / lab.POOL
    return float(((c - E) ** 2 / E).sum())


def realised_p(m, d, rng, n=400_000):
    """Probabilités d'inclusion RÉELLES sous ce biais — mesurées, pas supposées."""
    return biased(n, weights(m, d), rng).mean(0)


def main():
    rng = np.random.default_rng(20260827)

    print("=" * 76)
    print("PLAFOND DE LA PISTE A — le meilleur biais qui aurait échappé à 70 560 tirages")
    print("=" * 76)

    t0 = time.time()
    null = lab.calibrate(chi2, N, reps=REPS_NULL, seed=11)
    # Seuil de détection : Bonferroni sur le registre entier (m = 3 228 tests
    # déjà dépensés par l'audit), pas 0,05. C'est le seuil que le labo
    # s'impose, donc c'est lui qui définit ce qui « aurait échappé ».
    rows = lab.ledger()
    m_tests = len(rows) + sum(int(r.get("m_extra", 0)) for r in rows)
    from scipy.stats import norm
    z_crit = float(norm.isf(0.05 / m_tests / 2))
    thr = null.mean + z_crit * null.sd
    print(f"\nnull chi2 simulé : {null.mean:.2f} +- {null.sd:.2f} ({REPS_NULL} réplicats, {time.time()-t0:.0f}s)")
    print(f"  attendu analytique 80*0,75 = 60,00 — concordance : {'oui' if abs(null.mean-60)<3*null.sd/np.sqrt(REPS_NULL) else 'NON'}")
    print(f"registre : m = {m_tests} tests dépensés -> seuil z = {z_crit:.2f}, chi2 > {thr:.1f}")

    # -- 1. m=10 est-il bien la configuration optimale de l'adversaire ? ------
    print(f"\n{'-'*76}\n1. Configuration de l'adversaire : combien de numéros biaiser ?")
    print(f"{'m':>4} {'d pour chi2 = seuil':>20} {'avantage E[hits]':>18} {'gain relatif':>14}")
    best = None
    for m in (2, 5, 10, 20, 40, 80 - 1):
        # d qui amène le chi2 attendu pile au seuil : chi2(d) - chi2(0) ~ N*d^2*m*80/(80-m)/0.25
        d = float(np.sqrt(max(thr - null.mean, 0) / (4 * N * m * lab.POOL / (lab.POOL - m))))
        p = realised_p(m, d, rng)
        edge = float(np.sort(p)[-K:].sum() - K * 0.25)
        rel = edge / (K * 0.25)
        print(f"{m:>4} {d:>20.6f} {edge:>+18.5f} {rel:>13.3%}")
        if best is None or edge > best[2]:
            best = (m, d, edge)
    print(f"  -> optimum empirique : m = {best[0]} (avantage {best[2]:+.5f} hits)")

    # -- 2. Puissance réelle : jusqu'où le biais passe-t-il inaperçu ? --------
    m = best[0]
    print(f"\n{'-'*76}\n2. Puissance mesurée à m = {m} : à partir de quel biais le test le voit-il ?")
    print(f"{'d':>9} {'p du n° biaisé':>15} {'E[hits] k=10':>13} {'gain':>8} {'puissance':>10}")
    envelope = None
    for d in (0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.012):
        w = weights(m, d)
        det = 0
        for _ in range(REPS_POWER):
            if chi2(biased(N, w, rng)) > thr:
                det += 1
        pw = det / REPS_POWER
        p = realised_p(m, d, rng)
        edge = float(np.sort(p)[-K:].sum() - K * 0.25)
        print(f"{d:>9.4f} {p[:m].mean():>15.5f} {K*0.25+edge:>13.5f} {edge/(K*0.25):>7.2%} {pw:>10.0%}")
        if pw < 0.5:
            envelope = (d, edge, pw)
    print(f"\n  Le plus gros biais qui garde une chance sur deux de passer inaperçu :")
    print(f"    d = {envelope[0]:.4f}  ->  avantage maximal = {envelope[1]:+.5f} hits sur 2,5")
    print(f"    soit {envelope[1]/(K*0.25):+.2%} de rendement, pour un joueur qui CONNAÎTRAIT ce biais")

    tok = lab.preregister(
        "c0.plafond",
        "Borne supérieure sur l'avantage d'un biais marginal ayant échappé à 70 560 tirages",
        "avantage E[hits] du meilleur biais dont la puissance de détection reste < 50 % au seuil du registre",
        f"simulation : null chi2 sur {REPS_NULL} archives SRS, puissance sur {REPS_POWER} archives biaisées",
        "borne, pas un test : aucune hypothèse nulle n'est rejetée ici",
        track="A")
    lab.record(tok, observed=envelope[1], null=None, p=None,
               power_at=f"50 % à d = {envelope[0]:.4f} (m = {m} numéros biaisés)",
               verdict="borne établie",
               notes=(f"Avantage max non détecté = {envelope[1]:+.5f} hits sur 2,5 "
                      f"({envelope[1]/(K*0.25):+.2%}). Seuil registre m={m_tests}, z={z_crit:.2f}."))
    print(f"\n{'='*76}\nconsigné au registre. total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
