"""Le bonus comme signal à part entière — 70 560 échantillons jamais regardés.

Le `bonus` est un numéro publié à chaque tirage. C'est une **seconde sortie
du générateur** : si celui-ci a une structure, le bonus en est une fenêtre
indépendante de celle des 20 numéros.

Ce qui a été fait sur lui, et qui ne couvre pas ce fichier :
  audit §14   son RANG dans le tirage trié (χ²(19) = 27,46) ;
  audit §14   le recouvrement conditionné à `bonus_i == bonus_{i+1}` ;
  c4          re-dérivation de ce dernier avec null simulé ;
  b2 / c3     la loi et la mémoire du BOOST, qui est un autre champ.

Ce qui n'a jamais été testé — sa **valeur** :
  V1  la loi marginale du bonus sur les 80 numéros (H0 : uniforme, 882 par
      numéro ; le bonus étant un choix parmi les 20 tirés, chacun eux-mêmes
      à 1/4, la marginale vaut exactement 1/80) ;
  V2  sa structure sérielle : `bonus_t` prédit-il `bonus_{t+1}` ? Matrice
      80×80, testée par la norme de ses covariances croisées, comme `c1` ;
  V3  `bonus_t` appartient-il au tirage `t+1` plus souvent que 1/4 ?
  V4  le même, balayé sur les lags 1 à 60, avec la loi du max calibrée ;
  V5  le RANG, re-dérivé contre un null simulé. L'audit l'avait comparé à un
      seuil χ² **tabulé** (30,14 à p = 0,05) — or ce dossier compte déjà cinq
      occasions où une table a menti, et la règle n° 1 du labo ne lui avait
      jamais été appliquée.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import lab

POOL, DRAWN = lab.POOL, lab.DRAWN
REPS = 300
LAGS = range(1, 61)


def synth(n, rng):
    """Archive SRS + bonus tiré uniformément parmi les 20 — le null exact."""
    mask = lab.srs(n, rng)
    nums = np.argsort(~mask, axis=1, kind="stable")[:, :DRAWN] + 1
    pick = rng.integers(0, DRAWN, size=n)
    bonus = nums[np.arange(n), pick]
    return mask, np.sort(nums, axis=1), bonus


def stats(mask, nums_sorted, bonus):
    out = {}
    n = len(bonus)

    # V1 — loi marginale du bonus sur les 80 numéros
    c = np.bincount(bonus - 1, minlength=POOL).astype(float)
    e = n / POOL
    out["V1_marginale"] = float((((c - e) ** 2) / e).sum())

    # V2 — structure sérielle : norme des covariances croisées de la
    # matrice 80x80 des transitions bonus_t -> bonus_{t+1}
    a = np.zeros((n - 1, POOL), np.float32)
    b = np.zeros((n - 1, POOL), np.float32)
    a[np.arange(n - 1), bonus[:-1] - 1] = 1.0
    b[np.arange(n - 1), bonus[1:] - 1] = 1.0
    a -= a.mean(0); b -= b.mean(0)
    C = (a.T @ b) / (n - 1)
    out["V2_serie"] = float((C ** 2).sum())

    # V3 — bonus_t est-il dans le tirage t+1 ?
    out["V3_dans_suivant"] = float(mask[1:][np.arange(n - 1), bonus[:-1] - 1].mean())

    # V5 — rang du bonus dans le tirage trié
    rk = (nums_sorted == bonus[:, None]).argmax(1)
    cr = np.bincount(rk, minlength=DRAWN).astype(float)
    er = n / DRAWN
    out["V5_rang"] = float((((cr - er) ** 2) / er).sum())
    return out


def main():
    t0 = time.time()
    a = lab.load()
    n = len(a)
    nums = np.sort(a.nums.astype(np.int64), axis=1)
    bonus = a.bonus.astype(np.int64)

    print("=" * 78)
    print("LE BONUS COMME SIGNAL — sa VALEUR, jamais testée")
    print("=" * 78)
    print(f"\n{n} bonus, tous dans leur tirage (vérifié) ; "
          f"{len(set(bonus.tolist()))} valeurs distinctes sur 80")

    obs = stats(a.mask, nums, bonus)

    rng = np.random.default_rng(20260827)
    keys = list(obs)
    null = {k: np.empty(REPS) for k in keys}
    print(f"\ncalibration : {REPS} archives SRS complètes avec bonus uniforme...", flush=True)
    for r in range(REPS):
        st = stats(*synth(n, rng))
        for k in keys:
            null[k][r] = st[k]
        if (r + 1) % 100 == 0:
            print(f"  {r + 1}/{REPS}  ({time.time() - t0:.0f}s)", flush=True)

    label = {"V1_marginale": "loi du bonus sur 80 numéros",
             "V2_serie": "bonus_t -> bonus_{t+1} (80x80)",
             "V3_dans_suivant": "bonus_t dans le tirage t+1",
             "V5_rang": "rang du bonus (re-dérivé)"}
    print(f"\n{'statistique':<34}{'observé':>14}{'null simulé':>24}{'z':>8}{'p':>9}")
    zs = {}
    for k in keys:
        nl = lab.Null(float(null[k].mean()), float(null[k].std(ddof=1)), REPS, null[k])
        zs[k] = nl.z(obs[k])
        print(f"  {label[k]:<32}{obs[k]:>14.5f}{nl.mean:>15.5f} ± {nl.sd:<7.5f}"
              f"{zs[k]:>+8.2f}{nl.p_two_sided(obs[k]):>9.4f}")

    print(f"\n  V5 — l'audit comparait χ²(19) = 27,46 à un seuil TABULÉ de 30,14.")
    print(f"       Null simulé : {null['V5_rang'].mean():.2f} ± {null['V5_rang'].std(ddof=1):.2f}"
          f"  (χ²(19) théorique : moyenne 19,00, sd 6,16)")

    # V4 — balayage de lags sur « bonus_t dans le tirage t+k », max calibré.
    print(f"\n{'-' * 78}\nV4 — bonus_t appartient-il au tirage t+k ? (lags 1 à 60, max calibré)")

    def lagscan(mask, bo):
        z = []
        for k in LAGS:
            v = mask[k:][np.arange(len(bo) - k), bo[:-k] - 1].mean()
            se = np.sqrt(0.25 * 0.75 / (len(bo) - k))
            z.append((v - 0.25) / se)
        return np.array(z)

    obs_scan = lagscan(a.mask, bonus)
    null_max = np.empty(REPS)
    rng2 = np.random.default_rng(99)
    for r in range(REPS):
        m2, _, b2 = synth(n, rng2)
        null_max[r] = np.abs(lagscan(m2, b2)).max()
    om = float(np.abs(obs_scan).max())
    kmax = list(LAGS)[int(np.abs(obs_scan).argmax())]
    p_scan = float((1 + (null_max >= om).sum()) / (1 + REPS))
    print(f"  max |z| = {om:.2f} au lag {kmax}   loi du max sous H0 : "
          f"{null_max.mean():.2f} ± {null_max.std(ddof=1):.2f}   p = {p_scan:.4f}")

    for k, z in zip(LAGS, obs_scan):
        if abs(z) >= 2.5:
            print(f"    lag {k:>3} : z = {z:+.2f}")

    tok = lab.preregister(
        "d7.bonus_valeur",
        "La VALEUR du bonus (loi marginale, structure sérielle, appartenance au tirage "
        "suivant, rang re-dérivé) s'écarte-t-elle de ce que produit un choix uniforme "
        "parmi les 20 numéros tirés ?",
        "max des |z| de 4 statistiques, plus le max d'un balayage de 60 lags",
        f"null simulé sur {REPS} archives SRS complètes avec bonus uniforme ; "
        "lois des MAXIMA calibrées comme telles",
        "conforme si les p dépassent le seuil Holm du registre entier",
        track="A")
    mx = max(abs(z) for z in zs.values())
    lab.record(tok, observed=mx, p=min(p_scan, 1.0),
               power_at="balayage de 60 lags, max calibré sur 300 archives",
               verdict="conforme" if p_scan > 1.5e-5 and mx < 4 else "À RÉEXAMINER",
               notes=("z : " + ", ".join(f"{label[k]} {zs[k]:+.2f}" for k in keys)
                      + f" ; balayage max |z| = {om:.2f} au lag {kmax}, p = {p_scan:.4f}"
                      + f" ; V5 null simulé {null['V5_rang'].mean():.2f}"
                        f"±{null['V5_rang'].std(ddof=1):.2f} contre le seuil tabulé 30,14 de l'audit"))
    print(f"\n{'=' * 78}\nconsigné au registre. total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
