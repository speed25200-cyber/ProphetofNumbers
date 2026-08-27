"""L'avantage affiché sur chaque grille est-il réel, ou un artefact de sélection ?

`Swarm.makeGrids` (Prophet/Services/Swarm.swift:1087) affiche pour chaque
grille :

    expectedHits = somme de sources.inclusion[n] sur les n SÉLECTIONNÉS
    baseExpected = stake * 0,25

et `sources.inclusion` est le champ brut de la tête `bayes.b`
(Swarm.swift:1061), c'est-à-dire le posterior Beta escompté a/(a+b) à
mémoire 33 (Swarm.swift:35-65).

Sous H0 la probabilité d'inclusion vaut exactement 0,25 pour les 80
numéros. Mais l'ESTIMATEUR fluctue : à mémoire 33, son écart-type vaut
√(0,25·0,75/33) ≈ 0,075, soit 30 % de la valeur estimée. Or la grille ne
prend pas 10 numéros au hasard : elle prend ceux qu'un score CORRÉLÉ à cet
estimateur classe en tête. On affiche donc la moyenne d'un estimateur
bruité sur les points où ce même bruit est maximal.

C'est la malédiction du vainqueur, et elle ne s'annule pas en moyenne :
elle est positive à chaque tirage, sur chaque grille. Si l'effet est
sensible, l'app annonce un avantage fabriqué à son utilisateur en
permanence — sans qu'aucun biais du générateur soit nécessaire.

On mesure ici l'ampleur sous H0 pur : toute valeur > 0 est entièrement
artefactuelle, puisque les données sont équitables par construction.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN


def run_heads(mask, mem_bayes=33.0, mem_ewma=25.0, mem_hawkes=3.9):
    """Rejoue les trois familles de têtes de l'essaim. Renvoie leurs champs finaux."""
    a = np.full(POOL, 2.0); b = np.full(POOL, 6.0)
    gb = 1 - 1 / max(2.0, mem_bayes)
    e = np.full(POOL, 0.25); ge = 1 - 1 / max(2.0, mem_ewma)
    h = np.zeros(POOL); gh = np.exp(-1 / mem_hawkes)
    for row in mask:
        hit = row.astype(float)
        a = gb * a + hit
        b = gb * b + (1 - hit)
        e = ge * e + (1 - ge) * hit
        h = gh * h + hit
    return a / (a + b), e, h


def zscore(v):
    s = v.std()
    return (v - v.mean()) / s if s > 0 else v * 0


def main():
    rng = np.random.default_rng(20260827)
    print("=" * 74)
    print("expectedHits AFFICHÉ PAR L'APP — mesuré sous H0 (données équitables)")
    print("=" * 74)
    print("Toute valeur au-dessus de la base est un artefact : il n'y a aucun biais\n"
          "dans les données simulées ici, par construction.\n")

    TRIALS, HIST = 3000, 400
    for stake in (5, 10):
        base = stake * 0.25
        acc = {"bayes (pire cas)": [], "ewma (cas réel)": [], "hawkes": [],
               "mélange z": [], "aléatoire (témoin)": []}
        for _ in range(TRIALS):
            mask = lab.srs(HIST, rng)
            incl, ew, hw = run_heads(mask)
            blend = (zscore(incl) + zscore(ew) + zscore(hw)) / 3
            picks = {
                "bayes (pire cas)": np.argsort(-incl)[:stake],
                "ewma (cas réel)": np.argsort(-ew)[:stake],
                "hawkes": np.argsort(-hw)[:stake],
                "mélange z": np.argsort(-blend)[:stake],
                "aléatoire (témoin)": rng.choice(POOL, stake, replace=False),
            }
            for name, p in picks.items():
                acc[name].append(incl[p].sum())

        print(f"mise = {stake} numéros — base honnête = {base:.3f} hits")
        print(f"  {'sélection par':<22}{'expectedHits affiché':>22}{'écart':>10}{'surestimation':>15}")
        for name, vals in acc.items():
            v = np.array(vals)
            print(f"  {name:<22}{v.mean():>16.3f} ± {v.std():.3f}"
                  f"{v.mean()-base:>+10.3f}{(v.mean()-base)/base:>14.1%}")
        print()

    # Le témoin qui tranche : une sélection INDÉPENDANTE de l'estimateur
    # doit tomber pile sur la base. Si c'est le cas, l'écart des autres
    # lignes vient bien de la sélection et non d'un biais de l'estimateur.
    tok = lab.preregister(
        "b4.expected_hits",
        "L'expectedHits affiché par makeGrids surestime-t-il l'espérance réelle sous H0 ?",
        "moyenne de sum(inclusion[selection]) sous H0, contre la base k/4",
        f"simulation : {TRIALS} trajectoires SRS de {HIST} tirages, têtes rejouées à l'identique",
        "artefact confirmé si la sélection corrélée dépasse la base alors que le témoin aléatoire l'atteint",
        track="B")
    v = np.array(acc["mélange z"]); base = 10 * 0.25
    lab.record(tok, observed=float(v.mean()) - base, p=None,
               power_at="témoin aléatoire = base par construction",
               verdict="artefact de sélection confirmé" if v.mean() - base > 0.05 else "effet négligeable",
               notes=f"mise 10, sélection par mélange z : {v.mean():.3f} affiché contre {base:.3f} réel")
    print("consigné au registre.")


def correction():
    """La correction : estimer sur une fenêtre DISJOINTE de celle qui sélectionne.

    L'artefact vient de ce qu'un seul échantillon sert à la fois à choisir
    les numéros et à leur attribuer une probabilité. Le découplage
    (« cross-fitting ») le supprime : on sélectionne sur la fenêtre A, on
    estime sur la fenêtre B. Sous H0 le résultat doit revenir exactement à
    k/4 — et c'est bien le point : sous H0, il N'Y A PAS d'avantage à
    afficher, et une estimation honnête le dit.

    On mesure aussi ce que l'artefact fait à `pAllHit`, la probabilité
    affichée de toucher les k numéros, qui est calculée sur les mêmes
    probabilités gonflées.
    """
    import numpy as np, lab
    rng = np.random.default_rng(4242)
    TRIALS, HIST = 2000, 400
    print("\n" + "=" * 74)
    print("LA CORRECTION — estimer sur une fenêtre disjointe de celle qui sélectionne")
    print("=" * 74)
    for stake in (5, 10):
        base = stake * 0.25
        naive, cross, p_naive, p_cross = [], [], [], []
        for _ in range(TRIALS):
            m1 = lab.srs(HIST, rng)          # fenêtre A : sélectionne
            m2 = lab.srs(HIST, rng)          # fenêtre B : estime (disjointe)
            incl_a, ew_a, hw_a = run_heads(m1)
            incl_b, _, _ = run_heads(m2)
            pick = np.argsort(-ew_a)[:stake]
            naive.append(incl_a[pick].sum())
            cross.append(incl_b[pick].sum())
            # pAllHit ~ produit des p sous contrainte de 20 boules ; l'ordre
            # de grandeur suffit à montrer l'effet de l'inflation.
            p_naive.append(np.prod(incl_a[pick] * (POOL / DRAWN) * 0.25))
            p_cross.append(np.prod(incl_b[pick] * (POOL / DRAWN) * 0.25))
        n, c = np.array(naive), np.array(cross)
        pn, pc = np.array(p_naive), np.array(p_cross)
        print(f"\nmise = {stake} — base honnête = {base:.3f}")
        print(f"  expectedHits, estimation naïve (code actuel) : {n.mean():.3f}  ({(n.mean()-base)/base:+.1%})")
        print(f"  expectedHits, fenêtre disjointe (corrigé)    : {c.mean():.3f}  ({(c.mean()-base)/base:+.1%})")
        print(f"  pAllHit affiché / pAllHit corrigé            : x{pn.mean()/pc.mean():.2f}")
    print("\nLa fenêtre disjointe ramène l'affichage sur la base, à la précision")
    print("de la simulation. C'est la preuve que l'écart était bien un artefact")
    print("de sélection, et non une propriété des données.")


if __name__ == "__main__":
    main()
    correction()
