"""Le seuil de jackpot au-delà duquel le pari devient favorable — sans connaître le barème.

C'est le seul endroit du dossier où l'espérance peut réellement changer de
signe, et la seule chose qui ressemble à une prédiction utile : non pas
« quels numéros », mais **quand jouer**.

Le blocage, jusqu'ici, était que le barème des rangs intermédiaires n'est
pas publié (`HistoryView.swift:282`) — donc l'espérance totale n'est pas
calculable, et l'app se contente de l'affirmer négative
(`GridsView.swift:148`). `b2_mises.py` a confirmé que le classement des
mises n'est pas identifiable hors ligne pour cette raison.

Mais on n'a pas besoin du barème pour établir une condition SUFFISANTE.
Le gain total d'un ticket vaut :

    gain = jackpot·P(k/k)  +  Σ (rangs intermédiaires)  ≥  jackpot·P(k/k)

puisque tous les rangs intermédiaires sont positifs ou nuls. Donc :

    jackpot ≥ mise / P(k/k)   ⇒   espérance ≥ mise   ⇒   pari favorable

et tout ce qu'on ignore — la totalité du barème intermédiaire — ne peut
que rendre l'inégalité plus favorable, jamais moins. C'est une borne
inférieure sur l'espérance, valable quel que soit le barème réel.

La condition est vérifiable en direct : l'app affiche déjà le montant des
jackpots k/k (`LoroClient.parseJackpots`). Il ne manque que le seuil.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

STAKES = (5, 6, 7, 8, 10)


def main():
    print("=" * 76)
    print("SEUIL DE JACKPOT — au-delà duquel le pari est favorable, barème inconnu compris")
    print("=" * 76)

    # Contrôle : la loi exacte, vérifiée par simulation avant d'en tirer un seuil.
    rng = np.random.default_rng(20260827)
    N = 2_000_000
    m = lab.srs(N, rng)
    # Contrôle en COMPTES, pas en fréquences. Aux grandes mises, l'événement
    # est si rare que la fréquence observée vaut souvent zéro : un écart-type
    # calculé dessus n'a aucun sens (première version de ce contrôle : elle
    # annonçait −158,7 σ pour k=10 alors qu'on attend 0,22 succès, et qu'en
    # observer zéro arrive quatre fois sur cinq). Le bon cadre est Poisson.
    from scipy.stats import poisson
    print(f"\ncontrôle de la loi exacte sur {N:,} tirages simulés (cadre de Poisson) :")
    print(f"  {'mise':>5}{'P(k/k) exacte':>18}{'1 sur':>14}{'attendus':>11}{'observés':>10}{'p':>9}")
    exact = {}
    for k in STAKES:
        p = float(lab.hits_pmf(k)[k])
        exact[k] = p
        grid = np.arange(k)                      # une grille quelconque : P ne dépend pas du choix
        obs = int((m[:, grid].sum(1) == k).sum())
        lam = N * p
        # p bilatéral de Poisson : masse des comptes au moins aussi improbables.
        pmf_obs = poisson.pmf(obs, lam)
        support = np.arange(0, int(lam + 10 * np.sqrt(lam) + 20))
        pv = float(poisson.pmf(support, lam)[poisson.pmf(support, lam) <= pmf_obs * 1.000001].sum())
        print(f"  {k:>5}{p:>18.3e}{1/p:>14,.0f}{lam:>11.2f}{obs:>10}{min(pv,1.0):>9.3f}")

    print(f"\n{'-'*76}")
    print("Le seuil. Tous les rangs intermédiaires étant positifs, le jackpot seul")
    print("suffit à rendre le pari favorable dès qu'il dépasse mise / P(k/k).")
    print("Ce que l'on ignore du barème ne peut que rendre l'inégalité meilleure.\n")
    print(f"  {'mise':>5}{'jackpot suffisant, par franc misé':>38}")
    for k in STAKES:
        thr = 1 / exact[k]
        print(f"  {k:>5}{'CHF ' + format(thr, ',.0f').replace(',', ' '):>38}")

    print(f"\n{'-'*76}")
    print("Lecture. Le seuil de la mise à 5 numéros est le seul d'un ordre de")
    print("grandeur qu'un jackpot progressif peut atteindre ; celui de la mise à 10")
    print("demanderait près de neuf millions de francs par franc misé.")
    print("\nAttention à ce que ce seuil N'EST PAS : il ne dit rien sur les numéros à")
    print("cocher — l'espérance de hits reste k/4 quel que soit le choix (§1). Il ne")
    print("dit pas non plus que le pari devient bon en dessous du seuil ; il dit")
    print("seulement qu'AU-DESSUS il est favorable, et cela sans rien supposer du")
    print("barème. C'est une condition suffisante, pas une condition nécessaire :")
    print("le vrai seuil est plus bas, d'autant plus bas que les rangs")
    print("intermédiaires sont généreux — mais il n'est pas calculable sans eux.")

    tok = lab.preregister(
        "d6.seuil_jackpot",
        "Existe-t-il un seuil de jackpot, calculable sans connaître le barème des rangs "
        "intermédiaires, au-delà duquel l'espérance du pari est positive ?",
        "mise / P(k/k), borne inférieure de l'espérance par positivité des rangs intermédiaires",
        f"P(k/k) exacte (hypergéométrique) contrôlée par simulation sur {N:,} tirages",
        "résultat analytique, pas un test d'hypothèse : aucune H0 n'est rejetée ici",
        track="B")
    lab.record(tok, observed=1 / exact[5], p=None,
               power_at="sans objet (résultat exact)",
               verdict="seuil établi",
               notes=("jackpot suffisant par franc misé : "
                      + ", ".join(f"k={k}: {1/exact[k]:,.0f}" for k in STAKES)
                      + " ; condition SUFFISANTE et non nécessaire — le vrai seuil est plus "
                        "bas, d'autant que les rangs intermédiaires sont généreux, mais il "
                        "n'est pas calculable sans eux"))
    print(f"\n{'='*76}\nconsigné au registre.")


if __name__ == "__main__":
    main()
