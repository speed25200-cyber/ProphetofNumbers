"""Le bonus et le boost : les deux seuls observables de l'archive que le tri n'a pas ecrases.

Tout le reste du dossier se bat contre le tri : 20 numeros publies dans l'ordre croissant,
donc 4 bits d'information la ou le tirage en consomme 61,6. Mais deux champs annexes
echappent au tri.

  * bonus  — c'est TOUJOURS l'un des 20 (verifie : 70560/70560). Sa POSITION parmi les 20
             tries est donc une fonction de l'ordre cache : 20 valeurs, log2(20) = 4,32
             bits par tirage, que le tri n'a pas detruits.
  * boost  — six valeurs (1,2,3,4,5,10) de frequences tres inegales : ~1,9 bit par tirage,
             et surtout un observable de type SEUIL, donc une contrainte d'intervalle sur
             une sortie brute du generateur si l'operateur le tire par comparaison.

Ensemble : ~6,2 bits par tirage, 70560 tirages, sans tri. C'est la matiere qui manquait.

Ce fichier ne fait que la caracterisation. Si un de ces flux montre la moindre structure,
c'est la porte d'entree ; s'ils sont propres, ils restent la meilleure cible pour une
recherche de graine, parce qu'un appariement sur 16 tirages vaut 20^16 = 2^69.
"""
import numpy as np, math
from load import load

ids, ts, nums, boost, bonus = load()
N = nums.shape[0]
srt = np.sort(nums, axis=1)
pos = np.array([int(np.searchsorted(srt[i], bonus[i])) for i in range(N)])

def chi2(cnt, exp, label):
    c = np.asarray(cnt, dtype=float); e = np.asarray(exp, dtype=float)
    x = (((c - e) ** 2) / e).sum(); df = len(c) - 1
    print("    %-46s chi2 = %8.2f / %4d ddl   z = %+6.2f" % (label, x, df, (x - df) / math.sqrt(2 * df)))
    return x

print("=" * 78)
print("1. LE FLUX DES POSITIONS DU BONUS  (0..19)")
print("=" * 78)
chi2(np.bincount(pos, minlength=20), np.full(20, N / 20), "uniformite marginale")

print("\n  dependance serielle -- paires (pos[t], pos[t+d]) sur 400 cases :")
for d in (1, 2, 3, 5, 7, 11, 20, 100, 358):
    a, b = pos[:-d], pos[d:]
    tab = np.bincount(a * 20 + b, minlength=400)
    chi2(tab, np.full(400, len(a) / 400.0), "lag %-4d" % d)

print("\n  triplets (pos[t],pos[t+1],pos[t+2]) sur 8000 cases :")
t3 = np.bincount(pos[:-2] * 400 + pos[1:-1] * 20 + pos[2:], minlength=8000)
chi2(t3, np.full(8000, (N - 2) / 8000.0), "lag 1,2")

print("\n  repetitions immediates : %d observees, %.1f attendues  (z = %+.2f)"
      % ((pos[1:] == pos[:-1]).sum(), (N - 1) / 20.0,
         ((pos[1:] == pos[:-1]).sum() - (N - 1) / 20.0) / math.sqrt((N - 1) * (1 / 20.) * (19 / 20.))))

print("\n" + "=" * 78)
print("2. LE FLUX DU BOOST")
print("=" * 78)
vals, cnt = np.unique(boost, return_counts=True)
print("  valeur   compte   frequence   -log2(p)")
H = 0.0
for v, c in zip(vals, cnt):
    p = c / N; H -= p * math.log2(p)
    print("     %2d   %6d   %.6f    %.3f" % (v, c, p, -math.log2(p)))
print("  entropie du boost : %.3f bits/tirage" % H)
print("  entropie de la position du bonus : %.3f bits/tirage" % math.log2(20))
print("  TOTAL non trie : %.3f bits/tirage, soit %.0f bits sur l'archive" % (H + math.log2(20), (H + math.log2(20)) * N))

idx = {int(v): i for i, v in enumerate(vals)}
bi = np.array([idx[int(v)] for v in boost])
K = len(vals)
print("\n  dependance serielle du boost :")
for d in (1, 2, 3, 358):
    a, b = bi[:-d], bi[d:]
    e = np.outer(np.bincount(a, minlength=K), np.bincount(b, minlength=K)) / float(len(a))
    chi2(np.bincount(a * K + b, minlength=K * K), e.ravel(), "lag %-4d (independance)" % d)

print("\n" + "=" * 78)
print("3. BOOST x POSITION DU BONUS -- tires par le meme appel ?")
print("=" * 78)
e = np.outer(np.bincount(bi, minlength=K), np.bincount(pos, minlength=20)) / float(N)
chi2(np.bincount(bi * 20 + pos, minlength=K * 20), e.ravel(), "independance boost / position")
mi = 0.0
tab = np.bincount(bi * 20 + pos, minlength=K * 20).reshape(K, 20).astype(float)
for i in range(K):
    for j in range(20):
        if tab[i, j] > 0:
            mi += (tab[i, j] / N) * math.log2((tab[i, j] / N) / ((cnt[i] / N) * (1 / 20.)))
print("    information mutuelle : %.6f bit  (0 si independants ; 4.32 si le boost dictait la position)" % mi)

print("\n" + "=" * 78)
print("4. LE BOOST COMME SEUIL -- les frequences sortent-elles d'une table ronde ?")
print("=" * 78)
cum = 0.0
print("  si boost = premier v tel que u < seuil_v, les seuils cumules valent :")
for v, c in zip(vals, cnt):
    cum += c / N
    print("     %2d : cumul %.6f   (x 2^64 = %.4e)   1/x = %.3f" % (v, cum, cum * 2**64, 1 / cum if cum else 0))

np.save("bonuspos.npy", pos.astype(np.int64))
np.save("boostidx.npy", bi.astype(np.int64))
print("\n-> bonuspos.npy, boostidx.npy ecrits")
