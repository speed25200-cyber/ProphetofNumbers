"""la portee du detecteur d'energie additive : cinq echantillonneurs x trois degres.
Synthetique — aucune donnee reelle. Sert de temoin de PUISSANCE aux §177 a §181."""
import numpy as np, random, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'experiments'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h164_energie_signee as S
POOL, DRAWN, M32 = 80, 20, 1 << 32
def gen(n, graine, mode, K, L):
    rng = random.Random(graine); r = [rng.randrange(M32) for _ in range(max(80, L + 1))]
    i = len(r)
    def mot():
        nonlocal i
        r.append((r[i - K] + r[i - L]) % M32); i += 1; return r[i - 1]
    m = np.zeros((n, POOL), bool)
    for j in range(n):
        if mode in ('rejet', 'muets'):
            vus = set()
            while len(vus) < DRAWN: vus.add((mot() * POOL) >> 32)
            if mode == 'muets':
                for _ in range(10): mot()
            m[j, list(vus)] = True
        elif mode == 'mod_masque':
            vus = set()
            while len(vus) < DRAWN:
                v = mot() % 128
                if v < POOL: vus.add(v)
            m[j, list(vus)] = True
        elif mode == 'fy':
            urne = list(range(POOL))
            for k in range(DRAWN):
                p = k + ((mot() * (POOL - k)) >> 32); urne[k], urne[p] = urne[p], urne[k]
            m[j, urne[:DRAWN]] = True
        elif mode == 'fy_fin':
            urne = list(range(POOL)); pris = []
            for k in range(DRAWN):
                nn = POOL - k; p = (mot() * nn) >> 32
                pris.append(urne[p]); urne[p] = urne[nn - 1]
            m[j, pris] = True
    return m
if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--nb") + 1]) if "--nb" in sys.argv else 3000
    rng = np.random.default_rng(43); mn = S.srs(n, rng)
    NUL = {}
    for g in S.COUPLES:
        t = S.energie(mn, *g); NUL[g] = (t.mean(), t.std(ddof=1) / np.sqrt(len(t)))
    print(f"portee du detecteur — {n} tirages plantes, z ramene aux 70 560 de l'archive")
    print(f"{'echantillonneur':>26} | " + " | ".join(f"{x:>16}" for x in ('(3,7)', '(1,15)', '(3,31)')))
    for mode, nom in (('rejet', 'rejet + troncature'), ('mod_masque', 'modulo masque 128'),
                      ('fy', 'Fisher-Yates'), ('fy_fin', 'echange avec le dernier'),
                      ('muets', 'rejet + 10 mots muets')):
        out = []
        for K, L in ((3, 7), (1, 15), (3, 31)):
            m = gen(n, 8888 + K + L, mode, K, L); best, bz = None, 0.0
            for g in S.COUPLES:
                mu, sd = NUL[g]; z = (S.energie(m, *g).mean() - mu) / sd
                if abs(z) > abs(bz): best, bz = g, z
            out.append(f"{str(best):>8} {bz*np.sqrt(70560/n):+7.0f}")
        print(f"{nom:>26} | " + " | ".join(out), flush=True)
