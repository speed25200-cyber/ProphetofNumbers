"""La question posee, mesuree : « predire meme cinq, dix ou moins de numeros ».

Tout le reste du dossier repond « quel generateur ? ». Ceci repond a la question telle
qu'elle a ete posee : sur les 70 560 tirages reels, en jouant k numeros choisis par une
strategie qui ne voit QUE le passe, combien en touche-t-on ?

Le nul est exact : k numeros joues sur un tirage 20/80 equitable donnent k/4 bons numeros
en esperance, de variance hypergeometrique k*(20/80)*(60/80)*(80-k)/79. Sur T tirages hors
echantillon l'ecart-type de la moyenne vaut sqrt(Var/T) : avec T ~ 69 500 il suffit de
~0,01 numero d'avantage pour sortir du bruit. C'est la sensibilite reelle du test, et elle
est enorme — un avantage exploitable serait des dizaines de fois plus grand.

CONTROLE OBLIGATOIRE : une archive synthetique BIAISEE ou « numeros chauds » DOIT gagner.
Sans lui, un resultat nul ne prouverait que l'impuissance des strategies a lire un biais,
pas l'absence de biais.

Le comptage est ROULANT (ajout du nouveau tirage, retrait du plus ancien) et le classement
calcule une seule fois par tirage, partage par les trois tailles k. La premiere version
recalculait tout par (strategie, k) : O(N*W) par strategie, elle ne finissait pas.
"""
import numpy as np, math
from load import load

NAMES = ["chauds", "froids", "retard", "repeter", "paires", "markov", "fixe", "hasard"]
KS = (5, 10, 20)


def run(nums, label, W=500, warm=1000):
    N = nums.shape[0]
    rng = np.random.default_rng(31337)
    cnt = np.zeros(81, dtype=np.int64)
    last = np.full(81, -10**9, dtype=np.int64)
    trans = np.zeros((81, 81), dtype=np.int64)
    for i in range(warm):
        cnt[nums[i]] += 1
        last[nums[i]] = i
        if i:
            for a in nums[i-1]:
                trans[a, nums[i]] += 1
    for i in range(max(0, warm - W)):
        cnt[nums[i]] -= 1

    tot = {(n, k): 0 for n in NAMES for k in KS}
    T = 0
    order_fixe = np.arange(1, 81)
    for t in range(warm, N):
        prev = nums[t - 1]
        rank = {}
        rank["chauds"] = 1 + np.argsort(-cnt[1:81], kind="stable")
        rank["froids"] = 1 + np.argsort(cnt[1:81], kind="stable")
        rank["retard"] = 1 + np.argsort(last[1:81], kind="stable")
        pset = set(prev.tolist())
        rank["repeter"] = np.array(list(prev) + [v for v in rank["chauds"] if v not in pset])
        sc = trans[prev, :].sum(axis=0)[1:81].astype(float)
        rank["paires"] = 1 + np.argsort(-sc, kind="stable")
        sc2 = sc.copy()
        mask = np.ones(80, dtype=bool); mask[prev - 1] = False
        sc2[mask] -= 1e9
        rank["markov"] = 1 + np.argsort(-sc2, kind="stable")
        rank["fixe"] = order_fixe
        rank["hasard"] = rng.permutation(np.arange(1, 81))

        cur = np.zeros(81, dtype=bool); cur[nums[t]] = True
        for n in NAMES:
            r = rank[n]
            for k in KS:
                tot[(n, k)] += int(cur[r[:k]].sum())
        T += 1

        cnt[nums[t]] += 1
        last[nums[t]] = t
        for a in prev:
            trans[a, nums[t]] += 1
        old = t - W
        if old >= 0:
            cnt[nums[old]] -= 1

    print("\n  %s   (%d tirages hors echantillon, fenetre %d)" % (label, T, W))
    print("   %-9s %5s %8s %10s %11s %8s" % ("strategie", "k", "nul", "observe", "ecart", "z"))
    out = {}
    for k in KS:
        var = k * 0.25 * 0.75 * (80 - k) / 79.0
        se = math.sqrt(var / T)
        for n in NAMES:
            m = tot[(n, k)] / T; mu = k / 4.0
            z = (m - mu) / se
            out[(n, k)] = z
            print("   %-9s %5d %8.3f %10.4f %+11.4f %8.2f%s"
                  % (n, k, mu, m, m - mu, z, "  <<<" if abs(z) > 4 else ""))
    return out


ids, ts, nums, boost, bonus = load()
nums = nums.astype(np.int64)
N = nums.shape[0]
rng = np.random.default_rng(99)

print("=" * 78)
print("CONTROLE POSITIF -- archive BIAISEE : la strategie 'chauds' doit gagner")
print("=" * 78)
w = np.ones(80); w[:8] *= 1.35
p = w / w.sum()
bias = np.empty((N, 20), dtype=np.int64)
for i in range(N):
    bias[i] = np.sort(rng.choice(np.arange(1, 81), size=20, replace=False, p=p))
zc = run(bias, "archive synthetique biaisee (8 numeros a poids 1,35)")
print("\n  -> %s (z 'chauds' k=10 = %+.1f, exige > +8)"
      % ("CONTROLE PASSE" if zc[("chauds", 10)] > 8 else "*** CONTROLE ECHOUE ***", zc[("chauds", 10)]))

print("\n" + "=" * 78)
print("CONTROLE NEGATIF -- archive SRS equitable : rien ne doit gagner")
print("=" * 78)
fair = np.empty((N, 20), dtype=np.int64)
for i in range(N):
    fair[i] = np.sort(rng.choice(np.arange(1, 81), size=20, replace=False))
zf = run(fair, "archive synthetique equitable")
mxf = max(abs(v) for v in zf.values())
print("\n  -> %s (plus grand |z| = %.2f)"
      % ("CONTROLE PASSE" if mxf < 4.5 else "*** faux positif ***", mxf))

print("\n" + "=" * 78)
print("ARCHIVE REELLE")
print("=" * 78)
zr = run(nums, "70 560 tirages reels")
mx = max(abs(v) for v in zr.values())
best = max(zr.items(), key=lambda kv: kv[1])
bk = best[0][1]
adv = best[1] * math.sqrt(bk * 0.25 * 0.75 * (80 - bk) / 79.0 / (N - 1000))
print("\n  plus grand |z| sur l'archive : %.2f" % mx)
print("  meilleure strategie : %s a k=%d, z = %+.2f  (avantage %+.4f numero sur %.2f)"
      % (best[0][0], bk, best[1], adv, bk / 4.0))
print("\n  %s" % ("*** UN AVANTAGE MESURABLE EXISTE ***" if mx > 4.5 else
      "aucune strategie ne bat le nul ; l'avantage est nul a ~0,01 numero pres"))
