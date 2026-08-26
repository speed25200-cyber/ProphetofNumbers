#!/usr/bin/env python3
"""Douzième voie : les champs bonus/boost, jamais exploités par les
§§1-13 (qui ne portent que sur les 20 numéros triés).

Deux contrôles structurels d'abord :
  - bonus appartient aux 20 numéros dans 100 % des tirages (70 560/70 560)
    -> ce n'est pas un tirage RNG séparé sur [1,80], c'est la désignation
       d'un des 20 numéros déjà sortis.
  - son RANG dans le tirage trié est-il uniforme (pas de "dernière boule
    tirée" qui fuiterait de l'ordre même quand l'API trie) ? khi2 sur 19
    ddl : voir sortie.
  - boost (multiplicateur, valeurs {1,2,3,4,5,10}) a-t-il une mémoire
    d'un tirage à l'autre ? Comparé à sa propre loi empirique sous IID.

Puis le test qui compte : le recouvrement overlap(i,i+1) conditionné à
bonus_i == bonus_{i+1} contient-il un signal ?

ATTENTION MÉTHODOLOGIQUE (erreur commise puis corrigée dans cette
même séance) : P(bonus_i == bonus_{i+1}) n'est PAS 1/20 sous
indépendance totale. bonus_i n'existe que si le numéro est dans set_i ;
matcher exige que le numéro soit dans les DEUX ensembles ET choisi comme
bonus dans les deux, donc P(match | overlap=k) = k/400, et conditionner
sur "match" revient à sur-pondérer les gros recouvrements. Sous H0 pur :
E[overlap | match] = E[K²]/E[K] = 27.849/5 = 5.5698 (hypergéométrique),
PAS 5.0. Une première version de ce script comparait à tort à 5.0 et
trouvait un z=+11.98 — un artefact de conditionnement, pas un signal.
Le calibrage correct se fait par simulation directe (pas par formule à
la main, cf. les répliques nulles des §§11-12) : voir null_via_sim().
"""
import csv, glob, math
import numpy as np

rows = []
for f in sorted(glob.glob('/home/user/ProphetofNumbers/claude/draws/draws-*.csv')):
    with open(f) as fh:
        rows.extend(list(csv.DictReader(fh)))
rows.sort(key=lambda r: int(r['id']))
m = len(rows)
print(f"tirages : {m:,}")

sets = np.zeros((m, 81), dtype=bool)
bonus = np.zeros(m, dtype=np.int32)
boost = np.zeros(m, dtype=np.int32)
sorted_nums = []
for i, r in enumerate(rows):
    nums = sorted(int(r[f'n{j}']) for j in range(1, 21))
    sorted_nums.append(nums)
    for v in nums:
        sets[i, v] = True
    bonus[i] = int(r['bonus'])
    boost[i] = int(r['boost'])

# --- bonus appartient-il toujours aux 20 numéros ?
in_set = sum(1 for i in range(m) if sets[i, bonus[i]])
print(f"\nbonus dans les 20 numéros : {in_set}/{m} ({in_set/m:.4f})  (indépendance -> 0.2500)")

# --- rang du bonus dans le tirage trié : uniforme ?
rank_counts = np.zeros(21, dtype=np.int64)
for i in range(m):
    rank_counts[sorted_nums[i].index(bonus[i]) + 1] += 1
exp = m / 20
chi2 = float(((rank_counts[1:] - exp) ** 2 / exp).sum())
print(f"khi2 du rang (df=19) = {chi2:.2f}  (seuil p=0.05 -> 30.14 ; p=0.01 -> 36.19)")

# --- boost : mémoire d'un tirage à l'autre ?
p_boost = np.bincount(boost) / m
p2 = float((p_boost.astype(np.float64) ** 2).sum())
boost_match = (boost[:-1] == boost[1:])
print(f"\nboost(i)==boost(i+1) observé : {boost_match.mean():.4f}  "
      f"attendu sous IID (Σp²) : {p2:.4f}")

# --- overlap conditionné à bonus_i == bonus_{i+1}
overlap = (sets[:-1].astype(np.int32) * sets[1:].astype(np.int32)).sum(axis=1)
bonus_match = (bonus[:-1] == bonus[1:])
ov_m = overlap[bonus_match]
print(f"\npaires avec bonus_i==bonus_{{i+1}} : {bonus_match.sum():,} "
      f"({bonus_match.mean():.4f})")
print(f"overlap moyen sur ce sous-échantillon (réel) : {ov_m.mean():.4f}  n={len(ov_m):,}")


def null_via_sim(n_sim=6_000_000, seed=11, batch=300_000):
    """Loi nulle de overlap | bonus_i==bonus_{i+1} sous SRS pur, par
    simulation directe plutôt que par formule à la main."""
    rng = np.random.default_rng(seed)
    POOL, K = 80, 20
    done, chunks = 0, []
    while done < n_sim:
        b = min(batch, n_sim - done)
        A = np.array([rng.permutation(POOL)[:K] for _ in range(b)]) + 1
        B = np.array([rng.permutation(POOL)[:K] for _ in range(b)]) + 1
        bonusA = A[np.arange(b), rng.integers(0, K, b)]
        bonusB = B[np.arange(b), rng.integers(0, K, b)]
        setA = np.zeros((b, POOL + 1), dtype=bool)
        setB = np.zeros((b, POOL + 1), dtype=bool)
        for i in range(b):
            setA[i, A[i]] = True
            setB[i, B[i]] = True
        ov = (setA & setB).sum(axis=1)
        mtch = bonusA == bonusB
        chunks.append(ov[mtch])
        done += b
    return np.concatenate(chunks)


null = null_via_sim()
print(f"\nnul calibré par simulation ({len(null):,} paires matchées / SRS pur) :")
print(f"  moyenne = {null.mean():.4f}  sd = {null.std():.4f}")
se = null.std() / math.sqrt(len(ov_m))
z = (ov_m.mean() - null.mean()) / se
p = math.erfc(abs(z) / math.sqrt(2))
print(f"\nz (réel vs nul calibré, n={len(ov_m):,}) = {z:+.2f}   p = {p:.4f}")
print("(pour référence, une formule naïve E[overlap]=5.0 aurait donné un "
      "z artefactuel autour de +12 — l'erreur de conditionnement ci-dessus.)")
