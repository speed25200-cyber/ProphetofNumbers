#!/usr/bin/env python3
"""Treizième voie : localisation temporelle.

Les §§5 et 12 (Berlekamp-Massey, Maurer) n'ont jamais tourné qu'en
AGRÉGÉ sur les 70 560 tirages. Seule la fréquence brute (§1) a été
testée fenêtre par fenêtre. Or un défaut d'implémentation corrigé en
cours de route (mise à jour serveur, patch de sécurité) est exactement
le genre de structure qu'une moyenne sur 70 560 tirages DILUE jusqu'à
la faire disparaître, alors qu'elle serait franche sur le sous-ensemble
concerné. On refait tourner BM et Maurer fichier par fichier
(draws-01..08, découpage déjà存在 dans l'archive, ~8-9k tirages
chacun) plutôt qu'en agrégat, pour voir si un signal apparaît
localement puis s'annule en moyenne.
"""
import csv, glob, math, time
from math import comb

C8020 = comb(80, 20)
BITS = 61
LIM = 1 << BITS

EXPECTED_M = {6: 5.2177052}
VARIANCE_M = {6: 2.954}


def rank(nums):
    r = 0
    for i, v in enumerate(sorted(nums)):
        r += comb(v - 1, i + 1)
    return r


def bits_for(rows):
    bits = []
    for d in rows:
        v = [int(d[f'n{j}']) for j in range(1, 21)]
        r = rank(v)
        if r >= LIM:
            continue
        for b in range(BITS - 1, -1, -1):
            bits.append((r >> b) & 1)
    return bits


def berlekamp_massey(seq_int, M):
    b = 1; c = 1; L = 0; m = -1
    for N in range(M):
        d = 0; cc = c; i = 0
        while cc:
            if cc & 1:
                d ^= (seq_int >> (N - i)) & 1 if N - i >= 0 else 0
            cc >>= 1; i += 1
        if d:
            t = c
            c ^= b << (N - m)
            if L <= N // 2:
                L = N + 1 - L; m = N; b = t
    return L


def bm_test(bits, Mlc=500):
    n = len(bits)
    nblk = n // Mlc
    if nblk < 50:
        return None
    mu = Mlc / 2 + (9 + (-1) ** (Mlc + 1)) / 36 - (Mlc / 3 + 2 / 9) / (2 ** Mlc)
    Ls = []
    for i in range(nblk):
        blk = bits[i * Mlc:(i + 1) * Mlc]
        v = 0
        for j, bit in enumerate(blk):
            if bit: v |= (1 << j)
        Ls.append(berlekamp_massey(v, Mlc))
    Ls = [(-1) ** Mlc * (L - mu) + 2 / 9 for L in Ls]
    edges = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]
    probs = [0.010417, 0.031250, 0.125000, 0.500000, 0.250000, 0.062500, 0.020833]
    obs = [0] * 7
    for t in Ls:
        idx = 0
        for e in edges:
            if t <= e: break
            idx += 1
        obs[idx] += 1
    expc = [p * nblk for p in probs]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(obs, expc))
    return dict(nblk=nblk, chi2=chi2)


def chi2_sf(x, k):
    if x <= 0: return 1.0
    k2, x2 = k / 2, x / 2
    term = math.exp(-x2 + k2 * math.log(x2) - math.lgamma(k2 + 1))
    s = term; j = 1
    while j < 500:
        term *= x2 / (k2 + j)
        s += term
        if term < 1e-15: break
        j += 1
    return max(0.0, min(1.0, 1 - s))


def maurer_test(bits, L=6):
    n = len(bits)
    Q = 10 * (1 << L)
    K = n // L - Q
    if K <= 0:
        return None
    T = [0] * (1 << L)
    for i in range(Q):
        pat = 0
        for b in bits[i * L:(i + 1) * L]:
            pat = (pat << 1) | b
        T[pat] = i + 1
    s = 0.0
    for i in range(Q, Q + K):
        pat = 0
        for b in bits[i * L:(i + 1) * L]:
            pat = (pat << 1) | b
        s += math.log2(i + 1 - T[pat])
        T[pat] = i + 1
    fn = s / K
    expected = EXPECTED_M[L]; var = VARIANCE_M[L]
    c = 0.7 - 0.8 / L + (4 + 32 / L) * (K ** (-3 / L)) / 15
    sigma = c * math.sqrt(var / K)
    z = (fn - expected) / sigma
    reco = 1000 * (1 << L)
    return dict(K=K, fn=fn, z=z, powered=K >= reco, reco=reco)


files = sorted(glob.glob('/home/user/ProphetofNumbers/claude/draws/draws-*.csv'))
print(f"{'fichier':<16} {'n_tirages':>9} {'n_bits':>9} | {'BM chi2':>8} {'BM p':>7} | "
      f"{'Maurer z (L=6)':>15} {'puissance':>10}")
print("-" * 90)
for f in files:
    with open(f) as fh:
        rows = list(csv.DictReader(fh))
    bits = bits_for(rows)
    bm = bm_test(bits)
    mr = maurer_test(bits, L=6)
    bm_p = chi2_sf(bm['chi2'], 6) if bm else float('nan')
    name = f.split('/')[-1]
    print(f"{name:<16} {len(rows):>9,} {len(bits):>9,} | "
          f"{bm['chi2'] if bm else float('nan'):>8.2f} {bm_p:>7.4f} | "
          f"{mr['z'] if mr else float('nan'):>15.3f} "
          f"{'nominale' if mr and mr['powered'] else 'réduite':>10}")
