"""Le théorème, vérifié : aucune sélection ne déplace l'espérance.

Sous H0, les hits d'une grille de k numéros suivent une hypergéométrique
(80, 20, k), d'espérance k/4 — quel que soit le choix des numéros.
L'espérance d'une hypergéométrique ne dépend pas de QUELS numéros on
coche, seulement de combien.

Ce n'est donc pas une affirmation qu'un meilleur modèle pourrait
démentir : c'est une identité. Ce fichier la vérifie sur les 70 060
tirages évaluables de l'archive réelle, en marche avant, avec les
stratégies que tout le monde essaie en premier — et il sert de témoin de
non-régression pour le noyau du labo.

Chaque prédicteur passe `leak_check` avant d'être évalué : un backtest
qui fuit produit des résultats spectaculaires et faux, et c'est
exactement là que ce genre de fichier se trompe d'habitude.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

K = 10
WARMUP = 500

STRATEGIES = {
    "les plus chauds":      lambda past, t: np.argsort(-past.counts)[:K] + 1,
    "les plus froids":      lambda past, t: np.argsort(past.counts)[:K] + 1,
    "plus gros retard":     lambda past, t: np.argsort(-past.gaps)[:K] + 1,
    "retard le plus court": lambda past, t: np.argsort(past.gaps)[:K] + 1,
    "chauds sur 200":       lambda past, t: np.argsort(-past.mask[-200:].sum(0))[:K] + 1,
    "chauds sur 20":        lambda past, t: np.argsort(-past.mask[-20:].sum(0))[:K] + 1,
    "fixe 1..10 (témoin)":  lambda past, t: np.arange(1, K + 1),
}


def main():
    a = lab.load()
    a.build_index()
    base = K * lab.DRAWN / lab.POOL

    # Écart-type de la moyenne sous H0, pour lire les écarts à la bonne échelle.
    pmf = lab.hits_pmf(K)
    h = np.arange(K + 1)
    var = float((pmf * h * h).sum() - base ** 2)
    n_eval = len(a) - WARMUP
    se = np.sqrt(var / n_eval)

    print("=" * 78)
    print(f"AUCUNE SÉLECTION NE DÉPLACE L'ESPÉRANCE — {n_eval} tirages, marche avant")
    print("=" * 78)
    print(f"base H0 = {base:.4f} hits   écart-type de la moyenne = {se:.4f}\n")
    print(f"  {'stratégie':<24}{'hits/tirage':>12}{'z':>8}{'log10(e)':>11}  fuite")

    t0 = time.time()
    for name, fn in STRATEGIES.items():
        clean, spots = lab.leak_check(a, fn, k=K, warmup=WARMUP, probes=6, repeats=4)
        hits = lab.walk_forward(a, fn, k=K, warmup=WARMUP)
        z = (hits.mean() - base) / se
        _, log_e = lab.evalue(hits, K)
        flag = "propre" if clean else f"FUITE {len(spots)}"
        print(f"  {name:<24}{hits.mean():>12.4f}{z:>+8.2f}{log_e:>11.1f}  {flag}")

    print(f"\n  {time.time() - t0:.0f}s. Tous les écarts sont dans le bruit, et les")
    print("  log10(e) très négatifs disent la même chose de façon séquentielle :")
    print("  l'e-process s'effondre parce qu'il n'y a rien à parier.")


if __name__ == "__main__":
    main()
