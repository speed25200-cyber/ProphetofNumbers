#!/usr/bin/env python3
"""ENVELOPPE DE PUISSANCE de l'attaque par analogues.

Un résultat nul n'a de valeur que si l'on sait ce que le test AURAIT vu.
Aucune des neuf attaques précédentes n'a mesuré sa propre puissance.

Modèle générique d'un générateur inconnu de n bits d'état :
    s <- H(s) mod 2^n      (H = SHA-256 tronqué : fonction aléatoire)
    sortie = s mod 80, avec rejet des doublons
C'est le modèle sans hypothèse : toute application déterministe de n bits
vers n bits se comporte, en distribution, comme une fonction aléatoire.
Mesurer la puissance là-dessus, c'est la mesurer pour TOUTE famille
d'algorithme à n bits d'état — y compris celles que personne n'a écrites.

Prédiction théorique : un flux continu consomme ~23 sorties brutes par
tirage, soit R = 23m sorties. Une fonction aléatoire sur 2^n états entre
en cycle après ~sqrt(pi/2 * 2^n) pas. Le test voit le générateur dès que
R depasse ce seuil, donc dès que
    n <= 2 log2(R) - 0.65
Pour m = 20 000 (R = 4,6e5) : n <= 36,8 bits.
Pour m = 70 560 (R = 1,6e6) : n <= 40,4 bits.
C'est AU-DELÀ des 2^32 du balayage exhaustif, et sans nommer d'algorithme.

Témoins négatifs : splitmix64 (64 bits, avalanche complète) et SHA-256 en
compteur — le test doit rendre 5,000 sur les deux, sinon il ment.
"""
import hashlib, math, sys, time
import numpy as np

POOL, K = 80, 20


def draws_from_stepper(step, s0, m):
    """m tirages 20/80 par rejet sur un flux d'entiers."""
    X = np.zeros((m, POOL), dtype=np.float32)
    s = s0
    raw = 0
    for i in range(m):
        seen = set()
        while len(seen) < K:
            s, v = step(s)
            raw += 1
            seen.add(v % POOL)
        for v in seen:
            X[i, v] = 1.0
    return X, raw


def random_map(n):
    """Fonction aléatoire sur n bits : le générateur générique de n bits."""
    mask = (1 << n) - 1
    nb = (n + 7) // 8

    def step(s):
        h = hashlib.sha256(s.to_bytes(8, 'little')).digest()
        t = int.from_bytes(h[:nb], 'little') & mask
        return t, t
    return step


def splitmix64(s):
    s = (s + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = s
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return s, (z ^ (z >> 31))


def sha_ctr(s):
    h = hashlib.sha256(s.to_bytes(16, 'little')).digest()
    return s + 1, int.from_bytes(h[:8], 'little')


def lcg48(s):
    s = (s * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
    return s, s >> 16


def analogue_score(X, warm=None):
    """Prédicteur par analogue, contexte 1, k=1. Sous H0 : 5,000."""
    m = X.shape[0]
    warm = warm or max(500, m // 20)
    XT = np.ascontiguousarray(X.T)
    sc = []
    block = 256
    t = warm
    while t < m:
        b = min(block, m - t)
        S = X[t - 1:t + b - 1] @ XT
        for r in range(b):
            tt = t + r
            row = S[r, :tt - 1]
            if row.size < 10:
                continue
            j = int(np.argmax(row))
            sc.append(float(X[j + 1] @ X[tt]))
        t += b
    s = np.array(sc)
    n = len(s)
    mu, sd = s.mean(), s.std(ddof=1)
    z = (mu - 5.0) / (sd / math.sqrt(n))
    return mu, z, n


M = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
print(f"\nEnveloppe de puissance — {M:,} tirages par condition")
print(f"{'source':<34} {'brut':>10} {'score analogue':>15} {'z':>9}  verdict")
print("-" * 84)

rows = []
for n in (20, 24, 28, 32, 36, 40, 44):
    t0 = time.time()
    X, raw = draws_from_stepper(random_map(n), 12345, M)
    mu, z, _ = analogue_score(X)
    det = "DÉTECTÉ" if z > 6 else ("marginal" if z > 3 else "invisible")
    print(f"{'fonction aléatoire ' + str(n) + ' bits':<34} {raw:>10,} "
          f"{mu:>15.4f} {z:>+9.1f}  {det}   ({time.time()-t0:.0f} s)", flush=True)
    rows.append((n, mu, z))

for name, step, s0 in (("LCG 48 bits (bits hauts)", lcg48, 987654321),
                       ("splitmix64 (avalanche pleine)", splitmix64, 42),
                       ("SHA-256 en compteur", sha_ctr, 7)):
    t0 = time.time()
    X, raw = draws_from_stepper(step, s0, M)
    mu, z, _ = analogue_score(X)
    det = "DÉTECTÉ" if z > 6 else ("marginal" if z > 3 else "invisible")
    print(f"{name:<34} {raw:>10,} {mu:>15.4f} {z:>+9.1f}  {det}   "
          f"({time.time()-t0:.0f} s)", flush=True)

rng = np.random.default_rng(9)
X = np.zeros((M, POOL), dtype=np.float32)
for i in range(M):
    X[i, rng.choice(POOL, K, replace=False)] = 1.0
mu, z, _ = analogue_score(X)
print(f"{'SRS idéal (témoin nul)':<34} {'—':>10} {mu:>15.4f} {z:>+9.1f}  "
      f"{'invisible' if z < 3 else 'FAUX POSITIF'}")

R = 23 * M
print(f"\nSeuil théorique pour m={M:,} : R≈{R:,} sorties brutes,")
print(f"n_max = 2·log2(R) − 0,65 = {2*math.log2(R)-0.65:.1f} bits")
