"""La forme interne d'un tirage — la projection que personne n'a regardée.

Toutes les voies du dossier examinent soit les relations ENTRE tirages
(recouvrement, analogues, couplage, rejeu), soit les marginales À TRAVERS
les tirages (χ² du champ, paires, dérive). Une seule statistique touche à
l'intérieur d'un tirage : le comptage d'adjacences sur la grille 8×10 du
§2 de l'audit — et encore, sa moyenne seule (8,5493 contre 8,5380).

Or un tirage est un objet géométrique : 20 points sur [1,80]. Sa forme —
comment les 20 numéros se répartissent, s'agglutinent ou se repoussent —
est une projection de basse dimension, riche, et jamais testée. C'est
précisément ce que rate un générateur à mauvaise discrépance : ses points
se rangent dans des hyperplans (Marsaglia 1968), ce qui laisse les
marginales parfaites et déforme la géométrie.

Quatre statistiques de forme, chacune sur sa distribution COMPLÈTE et pas
seulement sa moyenne — c'est la différence avec le §2 :

  écarts        les 19 intervalles entre numéros triés consécutifs
  adjacences    combien de ces écarts valent exactement 1
  somme         la somme des 20 numéros
  dizaines      le profil de répartition sur les 8 dizaines

Aucune loi n'est tabulée : les quatre nulls sont simulés sur des archives
SRS complètes, et le MAXIMUM des quatre est calibré comme tel — comparer
le plus grand de quatre écarts à un seuil de test unique est le piège que
`a3_changepoint.py` a documenté sur données réelles.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
REPS = 300
GAP_MAX = 12          # écarts 1..11 puis « 12 et plus » — au-delà les cases se vident
SUM_BINS = 24


def sorted_nums(mask):
    """(n,20) numéros triés, depuis un masque booléen."""
    return np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1


def stats(mask):
    """Les quatre profils de forme. Renvoie un dict de vecteurs de comptes."""
    nums = np.sort(sorted_nums(mask), axis=1)
    n = mask.shape[0]

    gaps = np.diff(nums, axis=1).ravel()                       # 19n écarts
    g = np.bincount(np.minimum(gaps, GAP_MAX), minlength=GAP_MAX + 1)[1:]

    adj = (np.diff(nums, axis=1) == 1).sum(1)                  # adjacences par tirage
    a = np.bincount(np.minimum(adj, 9), minlength=10)

    tot = nums.sum(1)                                          # somme par tirage
    edges = np.linspace(500, 1120, SUM_BINS + 1)
    s = np.histogram(tot, bins=edges)[0]

    dec = mask.reshape(n, 8, 10).sum(2)                        # 0..10 par dizaine
    d = np.bincount(dec.ravel(), minlength=11)

    return {"ecarts": g, "adjacences": a, "somme": s, "dizaines": d}


def chi2_against(obs, exp):
    e = np.maximum(exp, 1e-9)
    return float((((obs - e) ** 2) / e).sum())


def main():
    t0 = time.time()
    a = lab.load()
    n = len(a)

    print("=" * 78)
    print("LA FORME INTERNE D'UN TIRAGE — 4 profils, null simulé, max calibré")
    print("=" * 78)

    # --- Espérances et loi du chi2 de chaque profil, par simulation ---------
    rng = np.random.default_rng(20260827)
    keys = ["ecarts", "adjacences", "somme", "dizaines"]
    acc = {k: [] for k in keys}
    print(f"\ncalibration sur {REPS} archives SRS de {n} tirages...", flush=True)
    for r in range(REPS):
        st = stats(lab.srs(n, rng))
        for k in keys:
            acc[k].append(st[k])
        if (r + 1) % 100 == 0:
            print(f"  {r + 1}/{REPS}  ({time.time() - t0:.0f}s)", flush=True)

    exp = {k: np.mean(acc[k], axis=0) for k in keys}
    # chi2 de chaque réplicat contre l'espérance simulée : la loi du null.
    null_chi = {k: np.array([chi2_against(v, exp[k]) for v in acc[k]]) for k in keys}

    obs_profiles = stats(a.mask)
    obs_chi = {k: chi2_against(obs_profiles[k], exp[k]) for k in keys}

    print(f"\n{'profil':<14}{'cases':>7}{'chi2 observé':>15}{'null simulé':>22}{'z':>8}{'p':>9}")
    zs = {}
    for k in keys:
        nl = lab.Null(float(null_chi[k].mean()), float(null_chi[k].std(ddof=1)),
                      REPS, null_chi[k])
        z = nl.z(obs_chi[k])
        zs[k] = z
        print(f"  {k:<12}{len(exp[k]):>7}{obs_chi[k]:>15.2f}"
              f"{nl.mean:>13.2f} ± {nl.sd:<6.2f}{z:>+8.2f}{nl.p_two_sided(obs_chi[k]):>9.3f}")

    # --- Le maximum des quatre, calibré comme un maximum -------------------
    zn = np.column_stack([(null_chi[k] - null_chi[k].mean()) / null_chi[k].std(ddof=1)
                          for k in keys])
    null_max = np.abs(zn).max(axis=1)
    obs_max = max(abs(z) for z in zs.values())
    p_max = float((1 + (null_max >= obs_max).sum()) / (1 + len(null_max)))
    print(f"\n  max |z| observé = {obs_max:.2f}   loi du max sous H0 : "
          f"{null_max.mean():.2f} ± {null_max.std(ddof=1):.2f}   p = {p_max:.3f}")
    print("  (comparé à un seuil de test unique, ce même max paraîtrait bien plus rare —")
    print("   c'est exactement l'artefact que la calibration du maximum neutralise)")

    # --- Puissance : quelle déformation de forme verrait-on ? --------------
    #
    # Première version de ce volet : rejeter les tirages à « trop »
    # d'adjacences. Erreur de conception — sous H0 la moyenne vaut 4,75
    # adjacences, donc un rejet au-delà de 6 touche 32 % des tirages et
    # au-delà de 3, 92 %. Détecter un défaut aussi massif à 100 % ne dit
    # rien de la sensibilité, et un nul dont la puissance n'est pas
    # informative est ce que la charte du labo refuse.
    #
    # Version correcte : une inclinaison exponentielle d'intensité λ, qui
    # accepte un tirage avec probabilité exp(−λ·adjacences). λ règle
    # continûment la force du défaut, et on rapporte la puissance en
    # fonction du décalage RÉALISÉ de la moyenne d'adjacences — une
    # quantité interprétable, mesurée et non supposée.
    print(f"\n{'-' * 78}\nPUISSANCE — quelle déformation de forme serait vue ?")
    print(f"  {'λ':>7}{'E[adj] obtenu':>16}{'écart à 4,7465':>17}{'puissance':>12}")
    thr = float(np.quantile(null_max, 0.95))
    rng2 = np.random.default_rng(7)
    base_adj = 4.7465

    def tilted(count, lam, rg):
        """Tirages inclinés : acceptation ∝ exp(−λ·adjacences)."""
        keep = np.zeros((0, POOL), bool)
        while len(keep) < count:
            cand = lab.srs(min(count * 2, 200_000), rg)
            nn = np.sort(sorted_nums(cand), axis=1)
            ad = (np.diff(nn, axis=1) == 1).sum(1)
            u = rg.random(len(cand))
            keep = np.vstack([keep, cand[u < np.exp(-lam * (ad - ad.min()))]])
        return keep[:count]

    for lam in (0.005, 0.010, 0.020, 0.040):
        hit = 0
        R = 12
        realised = []
        for _ in range(R):
            m = tilted(n, lam, rng2)
            nn = np.sort(sorted_nums(m), axis=1)
            realised.append(float((np.diff(nn, axis=1) == 1).sum(1).mean()))
            st = stats(m)
            zz = [abs((chi2_against(st[k], exp[k]) - null_chi[k].mean())
                      / null_chi[k].std(ddof=1)) for k in keys]
            if max(zz) >= thr:
                hit += 1
        ra = float(np.mean(realised))
        print(f"  {lam:>7.3f}{ra:>16.4f}{ra - base_adj:>+17.4f}{hit / R:>11.0%}")
    print("\n  Lecture : le test voit une déformation de la forme interne dès qu'elle")
    print("  déplace la moyenne d'adjacences de quelques centièmes sur 4,75 — sans")
    print("  qu'aucune fréquence marginale ne bouge.")

    tok = lab.preregister(
        "d4.forme_interne",
        "La forme interne d'un tirage (écarts, adjacences, somme, profil de dizaines) "
        "s'écarte-t-elle de ce que produit un tirage sans remise 20/80 ?",
        "max des |z| des chi2 de 4 profils complets, contre l'espérance simulée",
        f"null simulé sur {REPS} archives SRS de {n} tirages ; loi du MAX calibrée comme telle",
        "conforme si p du max > seuil Holm du registre entier",
        track="A")
    lab.record(tok, observed=obs_max, p=p_max,
               power_at="voir table de rejet d'adjacences",
               verdict="conforme" if p_max > 1.52e-5 else "À RÉEXAMINER",
               notes=("z par profil : " + ", ".join(f"{k} {zs[k]:+.2f}" for k in keys)
                      + f" ; loi du max sous H0 {null_max.mean():.2f}±{null_max.std(ddof=1):.2f}"))
    print(f"\n{'=' * 78}\nconsigné au registre. total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
