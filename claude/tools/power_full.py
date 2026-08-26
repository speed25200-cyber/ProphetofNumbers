#!/usr/bin/env python3
"""Seuil d'exclusion à l'échelle réelle : m = 70 560 tirages.

Même protocole que power.py, mais avec exactement le nombre de tirages
dont on dispose réellement. Le seuil obtenu ici est celui qui s'applique
au résultat nul sur les données de la Loterie Romande.
"""
import hashlib, math, time
import numpy as np
from power import draws_from_stepper, random_map, analogue_score, splitmix64, sha_ctr, lcg48

M = 70560
print(f"\nSeuil d'exclusion à l'échelle réelle — m = {M:,} tirages")
print(f"{'source':<34} {'brut':>11} {'score':>10} {'z':>9}  verdict", flush=True)
print("-" * 78)
for n in (36, 38, 40, 41, 42, 44):
    t0 = time.time()
    X, raw = draws_from_stepper(random_map(n), 12345, M)
    mu, z, _ = analogue_score(X)
    det = "DÉTECTÉ" if z > 6 else ("marginal" if z > 3 else "invisible")
    print(f"{'fonction aléatoire ' + str(n) + ' bits':<34} {raw:>11,} {mu:>10.4f} "
          f"{z:>+9.1f}  {det}  ({time.time()-t0:.0f} s)", flush=True)
for name, step, s0 in (("LCG 48 bits", lcg48, 987654321),
                       ("splitmix64", splitmix64, 42),
                       ("SHA-256 compteur", sha_ctr, 7)):
    t0 = time.time()
    X, raw = draws_from_stepper(step, s0, M)
    mu, z, _ = analogue_score(X)
    det = "DÉTECTÉ" if z > 6 else ("marginal" if z > 3 else "invisible")
    print(f"{name:<34} {raw:>11,} {mu:>10.4f} {z:>+9.1f}  {det}  "
          f"({time.time()-t0:.0f} s)", flush=True)
R = 23 * M
print(f"\nR ≈ {R:,} sorties brutes  ->  n_max = 2·log2(R) − 0,65 = {2*math.log2(R)-0.65:.1f} bits")
