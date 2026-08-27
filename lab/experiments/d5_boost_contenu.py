"""Le contenu du tirage dépend-il de la valeur du boost ?

Le `boost` a été passablement testé — sa loi (audit §14), sa mémoire au
lag 1 (§14 et `b2`), sa matrice de transition (`b2`), sa dépendance aux
covariables temporelles (`c3`). Toutes ces voies traitent le boost comme
une série à part.

Aucune n'a posé la question inverse, qui est pourtant la plus naturelle
s'il sort du MÊME flux que les numéros : **le tirage est-il différent
selon la valeur du boost qui l'accompagne ?**

C'est un point de fuite plausible et bon marché à tester. Si le
générateur produit d'abord les 20 numéros puis le multiplicateur à partir
du même état, une structure résiduelle apparaîtrait comme une dépendance
entre la valeur du boost et une propriété du tirage — sans jamais toucher
ni la loi marginale du boost, ni celle des numéros, ce qui la rend
invisible à tout ce qui a été fait jusqu'ici.

Quatre propriétés du tirage, stratifiées par les 6 valeurs de boost :

  champ       les 80 fréquences, par strate (χ² d'homogénéité)
  somme       la somme des 20 numéros
  adjacences  la forme interne (cf. d4)
  recouvr.    le recouvrement avec le tirage précédent

Null simulé en permutant les étiquettes de boost — c'est le null exact
de l'hypothèse « le boost est indépendant du contenu », et il préserve
automatiquement les deux lois marginales, donc il ne teste QUE le lien.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
REPS = 2000
BOOSTS = (1, 2, 3, 4, 5, 10)


def stratified_stats(mask, boost, sums, adj, ov):
    """Les quatre statistiques d'hétérogénéité entre strates de boost."""
    out = {}

    # 1. champ : chi2 d'homogénéité des 80 fréquences entre les 6 strates
    tot = 0.0
    n_all = mask.shape[0]
    col = mask.sum(0).astype(float)          # total par numéro
    for b in BOOSTS:
        sel = boost == b
        nb = int(sel.sum())
        if nb == 0:
            continue
        obs = mask[sel].sum(0).astype(float)
        exp = col * nb / n_all
        tot += (((obs - exp) ** 2) / np.maximum(exp, 1e-9)).sum()
    out["champ"] = tot

    # 2-4. contrastes scalaires : dispersion des moyennes par strate,
    # pondérée par l'effectif — c'est un F d'analyse de variance non normalisé.
    for name, v in (("somme", sums), ("adjacences", adj), ("recouvrement", ov)):
        gm = v.mean()
        s = 0.0
        for b in BOOSTS:
            sel = boost == b
            nb = int(sel.sum())
            if nb == 0:
                continue
            s += nb * (v[sel].mean() - gm) ** 2
        out[name] = s
    return out


def main():
    t0 = time.time()
    a = lab.load()
    n = len(a)
    nums = np.sort(a.nums.astype(np.int64), axis=1)

    sums = nums.sum(1).astype(float)
    adj = (np.diff(nums, axis=1) == 1).sum(1).astype(float)
    ov = np.empty(n, float)
    ov[0] = np.nan
    ov[1:] = (a.mask[1:] & a.mask[:-1]).sum(1)
    ov[0] = ov[1:].mean()

    boost = a.boost.astype(np.int64)
    print("=" * 78)
    print("LE CONTENU DU TIRAGE DÉPEND-IL DE LA VALEUR DU BOOST ?")
    print("=" * 78)
    print(f"\neffectifs par strate : "
          + "  ".join(f"boost {b}: {int((boost == b).sum())}" for b in BOOSTS))

    print(f"\n{'boost':>6}{'n':>8}{'somme moy.':>13}{'adjacences':>13}{'recouvrement':>15}")
    for b in BOOSTS:
        sel = boost == b
        print(f"{b:>6}{int(sel.sum()):>8}{sums[sel].mean():>13.3f}"
              f"{adj[sel].mean():>13.4f}{ov[sel].mean():>15.4f}")
    print(f"{'tous':>6}{n:>8}{sums.mean():>13.3f}{adj.mean():>13.4f}{ov.mean():>15.4f}")

    obs = stratified_stats(a.mask, boost, sums, adj, ov)

    # Null EXACT : permuter les étiquettes de boost. Sous l'hypothèse
    # d'indépendance, toute assignation est équiprobable — et les deux lois
    # marginales sont préservées par construction, donc le test ne mesure
    # que le lien, jamais un artefact de marge.
    rng = np.random.default_rng(20260827)
    keys = ["champ", "somme", "adjacences", "recouvrement"]
    null = {k: np.empty(REPS) for k in keys}
    print(f"\ncalibration : {REPS} permutations des étiquettes de boost...", flush=True)
    for r in range(REPS):
        perm = rng.permutation(boost)
        st = stratified_stats(a.mask, perm, sums, adj, ov)
        for k in keys:
            null[k][r] = st[k]
        if (r + 1) % 500 == 0:
            print(f"  {r + 1}/{REPS}  ({time.time() - t0:.0f}s)", flush=True)

    print(f"\n{'statistique':<16}{'observé':>14}{'null (permuté)':>24}{'z':>8}{'p':>9}")
    zs = {}
    for k in keys:
        nl = lab.Null(float(null[k].mean()), float(null[k].std(ddof=1)), REPS, null[k])
        zs[k] = nl.z(obs[k])
        print(f"  {k:<14}{obs[k]:>14.3f}{nl.mean:>15.3f} ± {nl.sd:<7.3f}"
              f"{zs[k]:>+8.2f}{nl.p_two_sided(obs[k]):>9.4f}")

    zn = np.column_stack([(null[k] - null[k].mean()) / null[k].std(ddof=1) for k in keys])
    null_max = np.abs(zn).max(axis=1)
    obs_max = max(abs(z) for z in zs.values())
    p_max = float((1 + (null_max >= obs_max).sum()) / (1 + len(null_max)))
    print(f"\n  max |z| = {obs_max:.2f}   loi du max sous H0 : "
          f"{null_max.mean():.2f} ± {null_max.std(ddof=1):.2f}   p = {p_max:.4f}")

    # Puissance : injecter un lien connu entre boost et contenu.
    print(f"\n{'-' * 78}\nPUISSANCE — quel lien boost/contenu serait vu ?")
    print(f"  {'lien injecté':<46}{'puissance':>12}")
    thr = float(np.quantile(null_max, 0.95))
    for eps, label in ((0.02, "boost 10 legèrement plus fréquent si somme haute (2 %)"),
                       (0.05, "idem, 5 %"),
                       (0.10, "idem, 10 %"),
                       (0.20, "idem, 20 %")):
        hit = 0
        R = 40
        for _ in range(R):
            b2 = rng.permutation(boost)
            # on déplace une fraction eps des boost=10 vers les sommes hautes
            hi = np.argsort(-sums)[: int(n * 0.1)]
            k10 = np.where(b2 == 10)[0]
            move = rng.choice(k10, size=int(len(k10) * eps), replace=False)
            targets = rng.choice(hi, size=len(move), replace=False)
            b2[move], b2[targets] = b2[targets], b2[move]
            st = stratified_stats(a.mask, b2, sums, adj, ov)
            zz = [abs((st[k] - null[k].mean()) / null[k].std(ddof=1)) for k in keys]
            if max(zz) >= thr:
                hit += 1
        print(f"  {label:<46}{hit / R:>11.0%}")

    tok = lab.preregister(
        "d5.boost_contenu",
        "Le contenu du tirage (champ, somme, adjacences, recouvrement) dépend-il "
        "de la valeur du boost qui l'accompagne ?",
        "max des |z| de 4 statistiques d'hétérogénéité entre les 6 strates de boost",
        f"null EXACT par permutation des étiquettes de boost ({REPS} réplicats) — "
        "préserve les deux lois marginales, ne teste que le lien ; loi du MAX calibrée",
        "conforme si p du max > seuil Holm du registre entier",
        track="A")
    lab.record(tok, observed=obs_max, p=p_max,
               power_at="voir table de lien injecté",
               verdict="conforme" if p_max > 1.52e-5 else "À RÉEXAMINER",
               notes=("z par statistique : " + ", ".join(f"{k} {zs[k]:+.2f}" for k in keys)))
    print(f"\n{'=' * 78}\nconsigné au registre. total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
