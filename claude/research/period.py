"""La periode — un test universel qui ne suppose AUCUNE famille de generateur.

Tout le reste du dossier demande « quel generateur ? ». Celui-ci ne le demande pas. Si le
generateur de l'operateur boucle — periode courte, etat qui se repete, reamorcage
periodique sur une horloge, compteur qui deborde — alors la suite des tirages se repete
EXACTEMENT a ce decalage, quel que soit le generateur, quelle que soit l'architecture,
quelle que soit la convention de rang. Rien a deviner.

Trois observables, du plus fin au plus grossier :
  * le tirage entier (61,6 bits)  — une seule repetition vaut 2^-61,6
  * la position du bonus (4,32 bits)
  * le boost (1,88 bit)

Le nul : deux tirages independants coincident avec probabilite 1/C(80,20) = 2,8e-19, donc
sur les 2,5e9 paires de l'archive on en attend 7e-10. UNE seule repetition serait donc
concluante. Pour la position du bonus le nul est 1/20 par paire, et le test devient un
balayage de tous les decalages : une periode reelle donnerait 100 % a ce decalage.

Ce test attrape aussi ce qu'aucun autre n'attrape : un reamorcage periodique (le service
redemarre chaque jour sur la meme graine), un compteur 32 bits qui reboucle, un etat qui
retombe sur un cycle court — des defauts d'EXPLOITATION, pas de generateur.
"""
import numpy as np, math
from load import load

ids, ts, nums, boost, bonus = load()
N = nums.shape[0]
srt = np.sort(nums, axis=1)
pos = np.array([int(np.searchsorted(srt[i], bonus[i])) for i in range(N)])
C = math.comb(80, 20)

print("=" * 78)
print("1. LE TIRAGE ENTIER SE REPETE-T-IL ?  (une seule fois suffirait)")
print("=" * 78)
key = [srt[i].tobytes() for i in range(N)]
seen = {}
dups = []
for i, k in enumerate(key):
    if k in seen:
        dups.append((seen[k], i))
    else:
        seen[k] = i
print("  tirages distincts : %d / %d" % (len(seen), N))
print("  repetitions exactes : %d   (le hasard en attend %.2e)" % (len(dups), N * (N - 1) / 2 / C))
if dups:
    for a, b in dups[:5]:
        print("     *** tirages %d et %d identiques, ecart %d ***" % (a, b, b - a))
print("  -> %s" % ("*** PERIODE DETECTEE ***" if dups else "aucune repetition : pas de cycle <= 70 560 tirages"))

print("\n" + "=" * 78)
print("2. BALAYAGE DE TOUS LES DECALAGES SUR LA POSITION DU BONUS")
print("=" * 78)
print("  une periode d de la suite donnerait pos[t] == pos[t+d] pour TOUS les t")
def scan(arr, e, label, ntest_note=""):
    """Le maximum du z sur TOUS les decalages — pas le z du decalage au taux maximal.
       Les decalages courts ont plus d'echantillons, donc les deux ne tombent pas au meme
       endroit, et c'est le maximum du z qu'il faut comparer au seuil. Une premiere version
       imprimait l'autre, ce qui aurait pu faire passer un decalage sous le radar."""
    n2 = N // 2 - 1
    zs = np.empty(n2); ds = np.arange(1, N // 2)
    for i, d in enumerate(ds):
        n = N - d
        m = int((arr[:-d] == arr[d:]).sum())
        zs[i] = (m - n * e) / math.sqrt(n * e * (1 - e))
    from math import erfc, sqrt
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if n2 * erfc(mid / sqrt(2)) > 0.05: lo = mid
        else: hi = mid
    k, kn = int(np.argmax(zs)), int(np.argmin(zs))
    print("  taux attendu sous l'independance : %.5f ; %d decalages testes" % (e, n2))
    print("     z max  %+6.2f au decalage %6d" % (zs[k], ds[k]))
    print("     z min  %+6.2f au decalage %6d" % (zs[kn], ds[kn]))
    print("     seuil de Bonferroni bilateral a 5 %% : |z| > %.2f" % hi)
    ok = max(zs[k], -zs[kn]) <= hi
    print("  -> %s" % ("aucun decalage ne sort du bruit" if ok else "*** A INSTRUIRE ***"))
    return ok

scan(pos, 1 / 20., "position du bonus")

print("\n" + "=" * 78)
print("3. LE MEME BALAYAGE SUR LE BOOST")
print("=" * 78)
VAL = [1, 2, 3, 4, 5, 10]
p = np.array([(boost == v).sum() for v in VAL], dtype=float) / N
scan(boost.astype(np.int16), float((p * p).sum()), "boost")

print("\n" + "=" * 78)
print("4. REPETITION PARTIELLE : deux tirages partagent-ils trop de numeros ?")
print("=" * 78)
print("  un generateur dont l'etat se rapproche sans coincider donnerait des paires a")
print("  fort recouvrement. Sous le nul, le recouvrement est hypergeometrique 20/80 :")
M = np.zeros((N, 80), dtype=np.uint8)
M[np.repeat(np.arange(N), 20), srt.reshape(-1) - 1] = 1
mx = 0; arg = None
CH = 4000
for i0 in range(0, N, CH):
    blk = M[i0:i0 + CH].astype(np.int16)
    ov = blk @ M.T.astype(np.int16)
    for r in range(blk.shape[0]):
        ov[r, i0 + r] = -1
    v = int(ov.max())
    if v > mx:
        mx = v
        j = np.unravel_index(int(ov.argmax()), ov.shape)
        arg = (i0 + int(j[0]), int(j[1]))
from math import comb
pairs = N * (N - 1) / 2
print("  recouvrement maximal observe : %d numeros communs (tirages %s)" % (mx, arg))
for k in range(mx - 1, 21):
    pk = comb(20, k) * comb(60, 20 - k) / comb(80, 20)
    print("     P(recouvrement = %2d) = %.3e   -> attendu sur %.3g paires : %.3f" % (k, pk, pairs, pairs * pk))
