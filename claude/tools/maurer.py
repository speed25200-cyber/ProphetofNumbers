#!/usr/bin/env python3
"""Test universel de Maurer (NIST SP800-22 §2.9) sur le flux binaire des
tirages réels.

Pourquoi ce test et pas un autre : Berlekamp-Massey (déjà fait) détecte
une récurrence LINÉAIRE sur GF(2), quelle que soit sa taille. Mais un
générateur non-linéaire (ARC4-like, un compteur chiffré par bloc, un
hachage itéré) peut avoir une complexité linéaire proche de l'attendu
tout en étant parfaitement prévisible. Le test de Maurer mesure autre
chose : le TAUX DE COMPRESSION du flux, via la distance moyenne entre
occurrences successives d'un même motif de L bits. C'est un estimateur
de l'entropie par bit au sens de Shannon, insensible à la structure
algébrique précise de la source — il détecte toute source dont le débit
d'entropie réel est < 1 bit/bit, qu'elle soit linéaire ou non.

Référence : U. Maurer, "A Universal Statistical Test for Random Bit
Generators", J. Cryptology 5(2), 1992. Table des (L, expected, variance)
reprise de NIST SP800-22 Rev.1a, Table 2-2 / 2-3 (K >= 1000, seuil L=6..16).
"""
import csv, glob, math, time
from math import comb

C8020 = comb(80, 20)
BITS = 61
LIM = 1 << BITS

rows = []
for f in sorted(glob.glob('/home/user/ProphetofNumbers/claude/draws/draws-*.csv')):
    with open(f) as fh:
        rows.extend(list(csv.DictReader(fh)))
print(f"tirages source : {len(rows):,}")


def rank(nums):
    r = 0
    for i, v in enumerate(sorted(nums)):
        r += comb(v - 1, i + 1)
    return r


t0 = time.time()
bits = []
accepted = 0
for d in rows:
    v = [int(d[f'n{j}']) for j in range(1, 21)]
    r = rank(v)
    if r >= LIM:
        continue
    accepted += 1
    for b in range(BITS - 1, -1, -1):
        bits.append((r >> b) & 1)
n = len(bits)
print(f"tirages acceptés : {accepted:,}/{len(rows):,}  ->  {n:,} bits  (extraction en {time.time()-t0:.0f} s)")

# --- Table NIST SP800-22 pour le test de Maurer (expected value, variance c*sqrt(var/K))
# clé = L ; valeur = (expected value en bits, variance théorique par bloc)
EXPECTED = {
    6: 5.2177052, 7: 6.1962507, 8: 7.1836656, 9: 8.1764248, 10: 9.1723243,
    11: 10.170032, 12: 11.168765, 13: 12.168070, 14: 13.167693, 15: 14.167488,
    16: 15.167379,
}
VARIANCE = {
    6: 2.954, 7: 3.125, 8: 3.238, 9: 3.311, 10: 3.356,
    11: 3.384, 12: 3.401, 13: 3.410, 14: 3.416, 15: 3.419, 16: 3.421,
}


def maurer(bits, L, Q):
    n = len(bits)
    K = n // L - Q
    if K <= 0:
        return None
    # table d'initialisation : dernière position vue pour chaque motif de L bits
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
    expected = EXPECTED[L]
    var = VARIANCE[L]
    c = 0.7 - 0.8 / L + (4 + 32 / L) * (K ** (-3 / L)) / 15
    sigma = c * math.sqrt(var / K)
    z = (fn - expected) / sigma
    p = math.erfc(abs(z) / math.sqrt(2))
    return dict(L=L, Q=Q, K=K, fn=fn, expected=expected, sigma=sigma, z=z, p=p)


# NIST recommande K >= 1000 * 2^L pour que l'approximation normale du
# test soit fiable (au-delà, la variance finie-échantillon s'écarte de la
# table). On le vérifie explicitement plutôt que de le supposer : les
# grands L ici sont exploratoires, pas garantis.
print()
print(f"{'L':>3} {'Q':>7} {'K':>9} {'f_n observé':>14} {'attendu':>10} {'z':>8} {'p':>8}  {'puissance'}")
print("-" * 78)
results = []
for L in (6, 7, 8, 9, 10, 11, 12, 13, 14):
    Q = 10 * (1 << L)
    r = maurer(bits, L, Q)
    if r is None:
        print(f"{L:>3}  (n insuffisant pour Q={Q:,})")
        continue
    results.append(r)
    reco = 1000 * (1 << L)
    powered = "nominal (K >= reco. NIST)" if r['K'] >= reco else f"sous reco. NIST ({reco:,})"
    flag = "  <-- ANOMALIE (p<0,01)" if r['p'] < 0.01 else ""
    print(f"{r['L']:>3} {r['Q']:>7,} {r['K']:>9,} {r['fn']:>14.6f} {r['expected']:>10.6f} "
          f"{r['z']:>8.3f} {r['p']:>8.4f}  {powered}{flag}")

nominal = [r for r in results if r['K'] >= 1000 * (1 << r['L'])]
print()
print(f"Configurations à puissance nominale (L=6..{nominal[-1]['L'] if nominal else '?'}) : "
      f"{sum(1 for r in nominal if r['p'] < 0.01)}/{len(nominal)} anomalie(s) à p<0,01.")
print("Au-delà (K sous la recommandation NIST), les z restent lisibles mais")
print("l'approximation gaussienne n'est plus garantie : à traiter comme")
print("exploratoire, pas comme un résultat calibré.")
