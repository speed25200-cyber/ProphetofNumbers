#!/usr/bin/env python3
"""RECONSTRUCTION D'ÉTAT PAR ANALOGUES — attaque non paramétrique.

Les neuf attaques précédentes sont toutes PARAMÉTRIQUES : chacune postule
une famille (LCG, xorshift, MT, Java) ou une structure (F2-linéarité pour
Berlekamp-Massey). Un générateur hors des familles postulées y échappe par
construction.

IDÉE NOUVELLE. Soit S_t l'état interne, g la transition, f la sortie :
    S_{t+1} = g(S_t),   tirage_t = f(S_t).
On n'a jamais besoin de CONNAÎTRE g ni f. Il suffit que g soit
déterministe. Alors :

    S_i = S_j   =>   tirage_{i+k} = tirage_{j+k}  pour tout k.

Et pour tout générateur dont l'avalanche est imparfaite (tous les LCG,
tous les compteurs faiblement mixés, tout PRNG non cryptographique) la
version continue tient aussi :

    S_i ~ S_j   =>   tirage_{i+1} ~ tirage_{j+1}.

D'où le test : le recouvrement O(i,j) entre deux tirages est un PROXY
observable de la proximité d'états. Si le proxy porte de l'information,
alors O(i,j) élevé doit prédire O(i+1,j+1) élevé. Sous H0 (tirages
indépendants), les deux sont indépendants : E[O(i+1,j+1) | O(i,j)] = 5
quel que soit le conditionnement.

C'est la méthode des ANALOGUES de Lorenz (1969), conçue pour prédire un
système dynamique déterministe sans en connaître les équations — jamais
appliquée, à ma connaissance, à un flux de générateur.

Deux volets :
  T1  histogramme conjoint de (O(i,j), O(i+1,j+1)) sur les 2,49 milliards
      de paires — la pente porte toute l'information de propagation
  T2  prédicteur par analogue en avant glissant : pour chaque tirage t,
      chercher dans le passé le meilleur analogue du contexte, et jouer
      son successeur. Score = recouvrement réel. Sous H0 : 5,000.

Calibration : la même chaîne sur un flux SRS synthétique, qui reproduit
exactement la structure de dépendance (chaque tirage apparaît dans 70 559
paires — les paires ne sont pas indépendantes, un test analytique serait
faux).
"""
import csv, glob, math, sys, time
import numpy as np

POOL = 80
K = 20


def load_real():
    rows = []
    for f in sorted(glob.glob('/home/user/ProphetofNumbers/claude/draws/draws-*.csv')):
        with open(f) as fh:
            rows.extend(list(csv.DictReader(fh)))
    rows.sort(key=lambda r: int(r['id']))
    m = len(rows)
    X = np.zeros((m, POOL), dtype=np.float32)
    for i, r in enumerate(rows):
        for j in range(1, K + 1):
            X[i, int(r[f'n{j}']) - 1] = 1.0
    return X, [int(r['id']) for r in rows]


def make_null(m, seed):
    """Flux SRS 20/80 indépendant — même taille, même structure de paires."""
    rng = np.random.default_rng(seed)
    X = np.zeros((m, POOL), dtype=np.float32)
    for i in range(m):
        X[i, rng.choice(POOL, K, replace=False)] = 1.0
    return X


# ---------------------------------------------------------------- T1
def joint_hist(X, block=512, lag=1):
    """H[k, l] = #{(i,j) : O(i,j)=k, O(i+lag, j+lag)=l}, j != i, j != i-lag."""
    m = X.shape[0]
    H = np.zeros((K + 1) * (K + 1), dtype=np.int64)
    XT = np.ascontiguousarray(X.T)
    a = 0
    t0 = time.time()
    while a + lag < m - 1:
        b = min(block, m - lag - 1 - a)
        if b <= 0:
            break
        Oa = (X[a:a + b] @ XT[:, :m - lag]).astype(np.int8)        # (b, m-lag)
        Ob = (X[a + lag:a + lag + b] @ XT[:, lag:]).astype(np.int8)  # (b, m-lag)
        idx = Oa.astype(np.int32) * (K + 1) + Ob.astype(np.int32)
        # retirer la diagonale j == i (recouvrement trivial 20/20)
        for r in range(b):
            i = a + r
            if i < m - lag:
                idx[r, i] = -1
        good = idx >= 0
        H += np.bincount(idx[good].ravel(), minlength=(K + 1) * (K + 1))
        a += b
        if a % (block * 20) == 0:
            el = time.time() - t0
            print(f"      T1 {a/m*100:5.1f} %  ({el:.0f} s)", flush=True)
    return H.reshape(K + 1, K + 1)


def t1_stats(H):
    k = np.arange(K + 1)
    n = H.sum()
    pk = H.sum(1)
    cond = np.where(pk > 0, (H * k[None, :]).sum(1) / np.maximum(pk, 1), np.nan)
    mk = (pk * k).sum() / n
    ml = (H.sum(0) * k).sum() / n
    ekl = (H * k[:, None] * k[None, :]).sum() / n
    vk = (pk * (k - mk) ** 2).sum() / n
    vl = (H.sum(0) * (k - ml) ** 2).sum() / n
    rho = (ekl - mk * ml) / math.sqrt(vk * vl)
    slope = (ekl - mk * ml) / vk
    return dict(n=int(n), rho=float(rho), slope=float(slope), cond=cond, pk=pk)


# ---------------------------------------------------------------- T2
def analogue_forecast(X, ctx=1, kbest=1, warm=2000):
    """Prédiction par analogue en avant glissant.

    Pour chaque t >= warm : on cherche dans j < t-1 l'indice dont le
    contexte (les `ctx` tirages finissant en j) ressemble le plus au
    contexte courant (finissant en t-1), puis on joue tirage_{j+1}.
    Score = |prediction ∩ tirage_t|.  Sous H0 : 5,000.
    """
    m = X.shape[0]
    scores = []
    # clé de contexte : concaténation de ctx tirages (proximité d'état plus fine)
    if ctx == 1:
        Kx = X
    else:
        Kx = np.concatenate([X[i:m - ctx + 1 + i] for i in range(ctx)], axis=1)
        # Kx[j] = contexte finissant au tirage j+ctx-1
    off = ctx - 1
    KT = np.ascontiguousarray(Kx.T)
    block = 256
    t = warm
    t0 = time.time()
    while t < m:
        b = min(block, m - t)
        # requêtes : contextes finissant en t-1 .. t+b-2
        qi = np.arange(t - 1 - off, t + b - 1 - off)
        Q = Kx[qi]                                  # (b, ctx*80)
        S = Q @ KT                                  # (b, ncand)
        for r in range(b):
            tt = t + r
            lim = tt - 1 - off                      # analogues j strictement antérieurs
            row = S[r, :lim]
            if row.size < 10:
                scores.append(np.nan)
                continue
            if kbest == 1:
                jj = int(np.argmax(row))
                pred = X[jj + off + 1]
            else:
                top = np.argpartition(row, -kbest)[-kbest:]
                agg = X[top + off + 1].sum(0)
                pred = np.zeros(POOL, dtype=np.float32)
                pred[np.argpartition(agg, -K)[-K:]] = 1.0
            scores.append(float(pred @ X[tt]))
        t += b
        if (t - warm) % (block * 40) == 0:
            print(f"      T2 ctx={ctx} k={kbest} {(t-warm)/(m-warm)*100:5.1f} % "
                  f"({time.time()-t0:.0f} s)", flush=True)
    s = np.array(scores, dtype=np.float64)
    s = s[~np.isnan(s)]
    return s


def report_t2(label, s):
    n = len(s)
    mu, sd = s.mean(), s.std(ddof=1)
    z = (mu - 5.0) / (sd / math.sqrt(n))
    p = math.erfc(abs(z) / math.sqrt(2))
    print(f"   {label:<34} n={n:6,}  moyenne={mu:.4f}  (H0=5,000)  "
          f"z={z:+6.2f}  p={p:.4f}")
    return mu, z, p


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'real'
    if which == 'real':
        X, ids = load_real()
        tag = f"RÉEL ({len(ids):,} tirages, ids {ids[0]}–{ids[-1]})"
    else:
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        X = make_null(70560, seed)
        tag = f"NUL SRS synthétique (graine {seed})"
    print(f"\n===== {tag} =====")
    print(f"matrice {X.shape}, densité {X.mean():.4f} (attendu {K/POOL:.4f})")

    print("\n-- T1 : propagation de proximité sur toutes les paires --")
    t0 = time.time()
    H = joint_hist(X)
    st = t1_stats(H)
    print(f"   {st['n']:,} paires en {time.time()-t0:.0f} s")
    print(f"   corrélation  rho(O(i,j), O(i+1,j+1)) = {st['rho']:+.6f}")
    print(f"   pente        dE[O(i+1,j+1)]/dO(i,j)  = {st['slope']:+.6f}")
    print("   moyenne conditionnelle E[O(i+1,j+1) | O(i,j)=k] :")
    for k in range(K + 1):
        if st['pk'][k] >= 30:
            print(f"      k={k:2d}  n={st['pk'][k]:13,}  E={st['cond'][k]:.4f}")
    tail = st['pk'][12:].sum()
    if tail:
        num = (H[12:] * np.arange(K + 1)[None, :]).sum()
        print(f"   queue O>=12 : n={tail:,}  E[succ]={num/tail:.4f}")

    print("\n-- T2 : prédicteur par analogue (avant glissant) --")
    out = {}
    for ctx in (1, 2, 3):
        for kb in (1, 20):
            s = analogue_forecast(X, ctx=ctx, kbest=kb)
            out[(ctx, kb)] = report_t2(f"contexte {ctx} tirage(s), k={kb}", s)
    print()
