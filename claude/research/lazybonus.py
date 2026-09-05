"""Les raccourcis d'implementation : l'indice du bonus est-il DEJA quelque part ?

Un developpeur presse ne tire pas toujours une nouvelle valeur. Il reutilise ce qu'il a
sous la main : le rang, l'identifiant du tirage, l'horodatage, le boost. Chacune de ces
paresses est catastrophique et se teste en une seconde. Aucune ne demande de deviner un
generateur, donc aucune ne peut etre bloquee par ce qui a bloque tout le reste du dossier.

Le nul : l'indice observe coincide avec le candidat 1 fois sur 20. Sur 70560 tirages,
3528 +- 57,9 coincidences. Un vrai raccourci donnerait 70560.
"""
import numpy as np, math
from load import load

ids, ts, nums, boost, bonus = load()
N = nums.shape[0]
srt = np.sort(nums, axis=1)
pos = np.array([int(np.searchsorted(srt[i], bonus[i])) for i in range(N)])
C = math.comb(80, 20)

rk = {}
for name in ("colex0", "lex0", "colex1", "comp0", "revcolex0"):
    try:
        rk[name] = np.fromfile("rank_%s.bin" % name, dtype=np.uint64)
    except FileNotFoundError:
        pass

cands = {}
cands["id mod 20"]                = ids.astype(np.int64) % 20
cands["(id-1) mod 20"]            = (ids.astype(np.int64) - 1) % 20
cands["unix mod 20"]              = ts.astype(np.int64) % 20
cands["(unix/300) mod 20"]        = (ts.astype(np.int64) // 300) % 20
cands["indice du tirage mod 20"]  = np.arange(N) % 20
cands["boost mod 20"]             = boost.astype(np.int64) % 20
cands["bonus mod 20"]             = bonus.astype(np.int64) % 20
cands["(bonus-1) mod 20"]         = (bonus.astype(np.int64) - 1) % 20
cands["(bonus-1)*20//80"]         = (bonus.astype(np.int64) - 1) * 20 // 80
cands["somme des 20 mod 20"]      = srt.sum(axis=1).astype(np.int64) % 20
cands["xor des 20 mod 20"]        = np.bitwise_xor.reduce(srt.astype(np.int64), axis=1) % 20
cands["n1 mod 20"]                = srt[:, 0].astype(np.int64) % 20
cands["n20 mod 20"]               = srt[:, 19].astype(np.int64) % 20
for name, a in rk.items():
    r = a.astype(object)
    cands["rang %s mod 20" % name] = np.array([int(x) % 20 for x in r])
    cands["rang %s mulhi 20" % name] = np.array([(int(x) * 20) // C for x in r])
    cands["rang %s >>59 mod 20" % name] = np.array([(int(x) >> 59) % 20 for x in r])

exp = N / 20.0
sd = math.sqrt(N * (1 / 20.) * (19 / 20.))
print("coincidences avec l'indice observe du bonus (nul : %.0f +- %.1f, tout : %d)\n" % (exp, sd, N))
rows = []
for name, c in cands.items():
    c = np.asarray(c) % 20
    hit = int((c == pos).sum())
    rows.append((abs((hit - exp) / sd), hit, name))
for z, hit, name in sorted(rows, reverse=True):
    flag = "  <<< A INSTRUIRE" if z > 5 else ""
    print("  %-30s %6d   z = %+6.2f%s" % (name, hit, (hit - exp) / sd, flag))

# meme chose pour le boost : le boost est-il une fonction paresseuse de ce qui precede ?
print("\ncoincidences avec le boost observe (6 valeurs, nul selon la table de seuils)")
TH = [0.512, 0.75, 0.90, 0.95, 0.975, 1.0]
VAL = np.array([1, 2, 3, 4, 5, 10])
def to_boost(frac):
    out = np.full(len(frac), 10, dtype=np.int64)
    for v, t in zip(VAL[::-1], TH[::-1]):
        out[frac < t] = v
    return out
p_agree = sum(p * p for p in np.diff([0.0] + TH))   # taux de coincidence sous independance
exp_b = N * p_agree; sd_b = math.sqrt(N * p_agree * (1 - p_agree))
bcands = {}
bcands["id / 2^k"]      = (ids.astype(np.float64) % 1000) / 1000.0
bcands["unix mod 300"]  = (ts.astype(np.float64) % 300) / 300.0
bcands["pos/20"]        = pos / 20.0
for name, a in rk.items():
    bcands["rang %s / C" % name] = np.array([int(x) / C for x in a.astype(object)])
for name, fr in bcands.items():
    b = to_boost(np.asarray(fr))
    hit = int((b == boost).sum())
    print("  %-30s %6d   attendu %.0f +- %.1f   z = %+6.2f"
          % (name, hit, exp_b, sd_b, (hit - exp_b) / sd_b))
