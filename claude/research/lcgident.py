"""L'identite qui teste TOUT LCG mod 2^64 d'un coup — sans deviner le multiplicateur.

Sous l'architecture par derangement avec reduction u mod C, la sortie brute se retrouve a
six candidats pres : u = rang + k*C, et 2^64 / C = 5,2159 donc k dans 0..5. Sous mulhi,
u vit dans un intervalle de ~5,2 entiers : meme structure, meme nombre de candidats.

Si le generateur est un LCG de module 2^64 — multiplicateur, increment et PAS quelconques,
puisque s appels par tirage donnent simplement A' = A^s — alors les differences
d_t = u_{t+1} - u_t verifient d_{t+1} = A' d_t. D'ou, en eliminant A' :

        d_1^2  ==  d_0 * d_2   (mod 2^64)

Aucune inconnue. Pas de multiplicateur a deviner, pas de graine a balayer, pas de pas a
supposer. C'est une identite exacte que tout LCG mod 2^64 satisfait et qu'un flux
quelconque ne satisfait qu'avec probabilite 2^-64.

Cout : 1296 combinaisons de (k0,k1,k2,k3) par quadruplet, 70 557 quadruplets, soit 9,1e7
verifications — et le hasard en attend 1296 * 70557 * 2^-64 = 5e-12. Une seule touche
serait donc un resultat, pas une coincidence.

Limite, dite d'emblee : ceci couvre les LCG dont la SORTIE EST L'ETAT. Un PCG, un xoshiro
ou tout generateur a fonction de sortie brouillee ne la satisfait pas — ils sont traites
ailleurs (rankxo, rankmix).
"""
import numpy as np, math, sys

C = math.comb(80, 20)
M = 1 << 64
KMAX = 6            # k dans 0..5 ; le rejet honnete donnerait 0..4, on garde une marge


def test_stream(u_cand, label, kmax=KMAX, report=True):
    """u_cand[j][t] = le j-eme candidat pour la sortie brute du tirage t (uint64)."""
    n = u_cand.shape[1]
    hits = []
    for k0 in range(kmax):
        for k1 in range(kmax):
            d0 = (u_cand[k1, 1:n-2] - u_cand[k0, 0:n-3]).astype(np.uint64)
            for k2 in range(kmax):
                d1 = (u_cand[k2, 2:n-1] - u_cand[k1, 1:n-2]).astype(np.uint64)
                lhs = (d1 * d1).astype(np.uint64)
                for k3 in range(kmax):
                    d2 = (u_cand[k3, 3:n] - u_cand[k2, 2:n-1]).astype(np.uint64)
                    ok = (lhs == (d0 * d2).astype(np.uint64))
                    c = int(ok.sum())
                    if c:
                        hits.append((k0, k1, k2, k3, c, np.flatnonzero(ok)[:5].tolist()))
    tot = sum(h[4] for h in hits)
    exp = (n - 3) * kmax**4 / 2.0**64
    if report:
        print("  %-42s quadruplets %6d   touches %8d   hasard %.3e"
              % (label, n - 3, tot, exp))
        for h in hits[:6]:
            print("       k=(%d,%d,%d,%d)  %d fois  ex. aux tirages %s" % h)
    return tot


def build_modC(ranks, kmax=KMAX):
    r = ranks.astype(object)
    out = np.zeros((kmax, len(r)), dtype=np.uint64)
    for k in range(kmax):
        v = [(int(x) + k * C) for x in r]
        out[k] = np.array([x & (M - 1) for x in v], dtype=np.uint64)
    return out


def build_mulhi(ranks, kmax=KMAX):
    """rang = (u*C)>>64  =>  u dans [ceil(r*2^64/C), ceil((r+1)*2^64/C))."""
    r = ranks.astype(object)
    base = [-((-int(x) * M) // C) for x in r]
    out = np.zeros((kmax, len(r)), dtype=np.uint64)
    for k in range(kmax):
        out[k] = np.array([(b + k) & (M - 1) for b in base], dtype=np.uint64)
    return out


print("=" * 78)
print("CONTROLE POSITIF -- un LCG64 plante doit etre vu, a n'importe quel pas")
print("=" * 78)
rng = np.random.default_rng(7)
for A, B, stride, nm in ((6364136223846793005, 1442695040888963407, 1, "MMIX, pas 1"),
                         (2862933555777941757, 3037000493, 3, "L'Ecuyer a, pas 3"),
                         (6364136223846793005, 0, 7, "increment nul, pas 7")):
    n = 3000
    s = 0xC0FFEE1234567890
    ranks = []
    for t in range(n):
        while True:                      # rejet honnete : u < 5C
            u = s; s = (A * s + B) % M
            for _ in range(stride - 1): s = (A * s + B) % M
            if u < 5 * C: break
        ranks.append(u % C)
    rk = np.array(ranks, dtype=np.uint64)
    got = test_stream(build_modC(rk), "LCG plante %s" % nm)
    print("       -> %s\n" % ("RECOVERED" if got > 0 else "*** FAIL : identite non vue ***"))

print("=" * 78)
print("CONTROLE NEGATIF -- un flux vraiment aleatoire ne doit rien donner")
print("=" * 78)
rk = np.array([int(x) for x in rng.integers(0, C, size=3000, dtype=np.uint64)], dtype=np.uint64)
got = test_stream(build_modC(rk), "rangs uniformes")
print("       -> %s\n" % ("PASS" if got == 0 else "*** FAIL : faux positif ***"))

print("=" * 78)
print("ARCHIVE REELLE")
print("=" * 78)
for conv in ("colex0", "lex0", "colex1", "comp0", "revcolex0"):
    try:
        a = np.fromfile("rank_%s.bin" % conv, dtype=np.uint64)
    except FileNotFoundError:
        continue
    test_stream(build_modC(a), "%s / reduction u mod C" % conv)
    test_stream(build_mulhi(a), "%s / reduction mulhi" % conv)
