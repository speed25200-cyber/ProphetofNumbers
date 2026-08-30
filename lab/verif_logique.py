"""Vérification par exécution de la logique ajoutée à Swarm.swift.

`verif_swift.py` établit que la syntaxe est valide. Il ne dit rien de ce que
le code CALCULE. Ce fichier transcrit fidèlement les fonctions ajoutées —
même formule, même ordre d'opérations — et vérifie que chaque assertion des
tests Swift serait satisfaite.

Ce n'est pas une compilation : un désaccord de types resterait invisible.
Mais l'ordre des arguments des initialiseurs par membre, qui est ici le
risque de typage le plus probable, est contrôlé séparément, et la syntaxe
l'est par une grammaire Swift réelle. Ce qui restait non vérifié était la
justesse numérique — c'est l'objet de ce fichier.
"""
import math
import os
from math import comb as exact_comb


def comb(n, k):
    """Transcription littérale de `SwarmEngine.comb` (produit incrémental)."""
    if k < 0 or k > n:
        return 0.0
    if k == 0 or k == n:
        return 1.0
    kk = min(k, n - k)
    r = 1.0
    for i in range(1, kk + 1):
        r *= (n - kk + i) / i
    return r


POOL, DRAWN = 80, 20


def hypergeometric_p_all(k):
    return comb(DRAWN, k) / comb(POOL, k)


def hypergeometric_tail(k, t):
    if t > k:
        return 0.0
    acc = 0.0
    for h in range(max(0, t), k + 1):
        acc += comb(DRAWN, h) * comb(POOL - DRAWN, k - h)
    return acc / comb(POOL, k)


def pack_p_all_hit(grids, stake):
    if not grids:
        return 0.0
    acc = len(grids) * hypergeometric_p_all(stake)
    for i in range(len(grids)):
        a = set(grids[i])
        for j in range(i + 1, len(grids)):
            acc -= hypergeometric_p_all(len(a | set(grids[j])))
    return max(0.0, acc)


def greedy_pick(score, k, cap, banned=frozenset()):
    """`greedyPick` réduit au plafond par dizaine et au bannissement."""
    picked, dec = [], [0] * 8
    order = sorted(range(POOL), key=lambda n: -score[n])
    for n in order:
        if n in banned or n in picked:
            continue
        d = n // 10
        if dec[d] >= cap:
            continue
        picked.append(n); dec[d] += 1
        if len(picked) == k:
            break
    if len(picked) < k:                      # branche de repli, plafond ignoré
        for n in order:
            if n in banned or n in picked:
                continue
            picked.append(n)
            if len(picked) == k:
                break
    return sorted(picked)


def make_grids(fields, stake, spread_penalty=1e6):
    """`makeGrids` : préférence de couverture sur les 3 familles x 4 variantes."""
    cover = [0.0] * POOL
    grids = []
    pop = [0.0] * POOL
    for n in range(1, POOL + 1):
        s = 0.0
        if n <= 31: s += 1.0
        if n <= 12: s += 0.4
        if n % 10 == 7: s += 0.5
        if n % 11 == 0: s += 0.4
        if n % 10 == 0: s += 0.2
        pop[n - 1] = s
    for name in ("alpha", "omega", "nexus"):
        src = fields[name]
        cap = max(2, -(-stake // 5) + 1) if name == "nexus" else stake
        base = [src[i] - spread_penalty * cover[i] for i in range(POOL)]
        first = greedy_pick(base, stake, cap)
        for n in first: cover[n] += 1
        base = [src[i] - spread_penalty * cover[i] for i in range(POOL)]
        second = greedy_pick(base, stake, cap, banned=frozenset(first))
        for n in second: cover[n] += 1
        base = [-src[i] - spread_penalty * cover[i] for i in range(POOL)]
        anti = greedy_pick(base, stake, cap)
        for n in anti: cover[n] += 1
        base = [src[i] - 0.4 * pop[i] - spread_penalty * cover[i] for i in range(POOL)]
        stealth = greedy_pick(base, stake, cap)
        for n in stealth: cover[n] += 1
        grids += [first, second, anti, stealth]
    return grids, cover


def main():
    import random
    rng = random.Random(20260827)
    ok = True

    print("=" * 74)
    print("VÉRIFICATION PAR EXÉCUTION — chaque assertion des tests Swift")
    print("=" * 74)

    # 1. comb : la formule incrémentale du code contre la valeur exacte.
    worst = max(abs(comb(n, k) - exact_comb(n, k)) / max(exact_comb(n, k), 1)
                for n in (60, 80) for k in range(0, 21))
    print(f"\n1. comb() incrémental contre exact : écart relatif max {worst:.2e}"
          f"  {'ok' if worst < 1e-12 else 'ÉCHEC'}")
    ok &= worst < 1e-12

    # 1 bis. overlapSD : la formule fermée du code contre la loi terme à terme.
    # C'est testDisplayedSigmaUsesTheExactLawNotAnEstimate.
    tot = exact_comb(80, 20)
    mean = sum(o * exact_comb(20, o) * exact_comb(60, 20 - o) / tot for o in range(21))
    square = sum(o * o * exact_comb(20, o) * exact_comb(60, 20 - o) / tot for o in range(21))
    sd_loi = (square - mean * mean) ** 0.5
    sd_code = (20 * 0.25 * (1 - 0.25) * (80 - 20) / (80 - 1)) ** 0.5
    a = abs(mean - 5.0) < 1e-9
    b = abs(sd_loi - sd_code) < 1e-9
    c = abs(sd_code - 1.6876317) < 1e-6
    print(f"\n1 bis. overlapSD : espérance {mean:.12f} (attendu 5)  "
          f"{'ok' if a else 'ÉCHEC'}")
    print(f"       loi terme à terme {sd_loi:.12f} contre formule fermée "
          f"{sd_code:.12f}  {'ok' if b else 'ÉCHEC'}")
    print(f"       valeur affichée dans le test 1,6876317  {'ok' if c else 'ÉCHEC'}")
    ok &= a and b and c

    # 1 quater. packOverlap : transcription de Swarm.packOverlap, contrôlée
    # contre une référence indépendante. Les trois façons dont ce code peut
    # être faux en silence sont testées : le plancher Σ C(cₓ,2)/C(n,2) quand
    # la couverture n'est pas entière, le seuil neutre ω* = k²/80, et le fait
    # que le plancher soit réellement une BORNE INFÉRIEURE du recouvrement
    # moyen (une erreur d'un cran le rendrait inatteignable ou dépassable).
    def pack_overlap(grids):
        n = len(grids)
        if n < 2 or not grids[0]:
            return 0, 0.0, 0.0, 0.0
        k = len(grids[0])
        sets = [set(g) for g in grids]
        worst, total = 0, 0
        for i in range(n):
            for j in range(i + 1, n):
                o = len(sets[i] & sets[j])
                worst = max(worst, o)
                total += o
        pairs = n * (n - 1) // 2
        base, rem = divmod(n * k, POOL)
        floor_sum = (rem * (base + 1) * base // 2
                     + (POOL - rem) * base * (base - 1) // 2)
        return worst, total / pairs, floor_sum / pairs, k * k / POOL

    a = True
    for k, n in ((10, 8), (10, 12), (5, 12), (8, 10), (4, 12)):
        # Référence : le plancher doit égaler Σ C(cₓ,2)/C(n,2) recalculé
        # à partir d'une couverture équilibrée construite explicitement.
        cov = [0] * POOL
        for i in range(n * k):
            cov[i % POOL] += 1
        ref = sum(c * (c - 1) // 2 for c in cov) / (n * (n - 1) // 2)
        # Un portefeuille équilibré réel : découpage tournant.
        grids = [[(i * k + t) % POOL + 1 for t in range(k)] for i in range(n)]
        # Le découpage tournant ne l'est que si n·k ≤ 80 ; sinon on prend un
        # plan glouton équivalent à celui du labo (h13).
        if n * k > POOL:
            cover, grids = {x: 0 for x in range(1, POOL + 1)}, []
            for _ in range(n):
                g = set()
                for _ in range(k):
                    best = min((x for x in range(1, POOL + 1) if x not in g),
                               key=lambda x: (cover[x],
                                              max((len(gg & (g | {x})) for gg in grids),
                                                  default=0), x))
                    g.add(best)
                for x in g:
                    cover[x] += 1
                grids.append(g)
            grids = [sorted(g) for g in grids]
        worst, mean_o, floor_o, neutral = pack_overlap(grids)
        okk = (abs(floor_o - ref) < 1e-12
               and abs(neutral - k * k / POOL) < 1e-12
               and mean_o >= floor_o - 1e-12
               and worst < k)
        a &= okk
        print(f"\n1 quater. packOverlap k={k} n={n} : max {worst}, moyen "
              f"{mean_o:.3f}, plancher {floor_o:.3f} (réf {ref:.3f}), "
              f"ω* {neutral:.2f}  {'ok' if okk else 'ÉCHEC'}")
    ok &= a

    # 1 quinquies. JackpotLaw : transcription de Prophet/Services/JackpotLaw.swift.
    # L'intervalle de Poisson y est obtenu par bissection sur la fonction de
    # répartition, faute de fonction gamma en Swift — donc la vérification
    # est de le confronter aux quantiles exacts du khi-deux (Garwood).
    import math as _m

    def poisson_cdf(k, lam):
        if k < 0:
            return 0.0
        if lam <= 0:
            return 1.0
        log_term = -lam
        total = _m.exp(log_term)
        for i in range(1, k + 1):
            log_term += _m.log(lam) - _m.log(i)
            total += _m.exp(log_term)
        return min(1.0, total)

    def _solve(target, k):
        lo, hi = 0.0, float(k) + 10
        while poisson_cdf(k, hi) > target and hi < 1e9:
            hi *= 2
        for _ in range(200):
            mid = (lo + hi) / 2
            if poisson_cdf(k, mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def poisson_rate_interval(count, exposure, alpha=0.05):
        if exposure <= 0:
            return 0.0, float("inf")
        lo = 0.0 if count == 0 else _solve(1 - alpha / 2, count - 1)
        hi = _solve(alpha / 2, count)
        return lo / exposure, hi / exposure

    from scipy import stats as _st
    a = True
    print()
    for count in (0, 1, 2, 5, 17):
        lo, hi = poisson_rate_interval(count, 1.0)
        ref_lo = 0.0 if count == 0 else _st.chi2.ppf(0.025, 2 * count) / 2
        ref_hi = _st.chi2.ppf(0.975, 2 * count + 2) / 2
        okk = abs(lo - ref_lo) < 1e-6 and abs(hi - ref_hi) < 1e-6
        a &= okk
        print(f"1 quinquies. Poisson exact, {count:>2} chute(s) : "
              f"[{lo:.6f}, {hi:.6f}] contre Garwood [{ref_lo:.6f}, {ref_hi:.6f}]"
              f"  {'ok' if okk else 'ÉCHEC'}")

    # Le quantile du khi-deux, obtenu en Swift depuis la MÊME fonction de
    # répartition de Poisson via P(χ²(2n) ≤ x) = P(Poisson(x/2) ≥ n). C'est
    # ce qui donne l'intervalle du gain conditionnel (h16) sans fonction gamma.
    def chi2_quantile(p, n):
        return 2 * _solve(1 - p, n - 1)

    for n in (1, 2, 5, 10, 30, 100):
        for pq in (0.025, 0.975):
            got, ref = chi2_quantile(pq, n), _st.chi2.ppf(pq, 2 * n)
            okk = abs(got - ref) < 1e-6 * max(1.0, ref)
            a &= okk
            if not okk:
                print(f"1 quinquies. χ²({2 * n}) au quantile {pq} : "
                      f"{got:.6f} contre {ref:.6f}  ÉCHEC")
    print(f"1 quinquies. quantiles du khi-deux depuis la loi de Poisson, "
          f"12 points : {'ok' if a else 'ÉCHEC'}")

    # Et le gain conditionnel lui-même : sur UN relevé il vaut exactement le
    # rapport cagnotte/seuil, et son intervalle doit l'encadrer.
    seuil6, j6 = 7753.0, 2287.0
    edge = j6 / seuil6
    e_lo = 2 * 1 * j6 / chi2_quantile(0.975, 1) / seuil6
    e_hi = 2 * 1 * j6 / chi2_quantile(0.025, 1) / seuil6
    d = e_lo < edge < e_hi and e_lo > 0
    a &= d
    print(f"1 quinquies. gain conditionnel sur 1 relevé : {edge:+.1%} "
          f"dans [{e_lo:+.1%}, {e_hi:+.1%}]  {'ok' if d else 'ÉCHEC'}")

    # La chaîne complète : un journal fabriqué à r et q connus doit rendre
    # une fraction favorable qui encadre la vraie.
    def estimate(rows, seuil):
        rows = sorted(rows)
        rates, drops = [], 0
        for i in range(1, len(rows)):
            step = rows[i][0] - rows[i - 1][0]
            if step <= 0:
                continue
            delta = rows[i][1] - rows[i - 1][1]
            if delta < 0:
                drops += 1
            else:
                rates.append(delta / step)
        pos = sorted(x for x in rates if x > 0)
        r = None if not pos else (pos[len(pos) // 2] if len(pos) % 2
                                  else (pos[len(pos) // 2 - 1] + pos[len(pos) // 2]) / 2)
        span = rows[-1][0] - rows[0][0] if len(rows) >= 2 else 0
        if r is None or r <= 0 or span <= 0:
            return r, drops, None, None, None
        lo_rate, hi_rate = poisson_rate_interval(drops, span)
        q = drops / span
        fav = _m.exp(-seuil * q / r) if q > 0 else None
        return (r, drops, fav,
                _m.exp(-seuil * hi_rate / r) if hi_rate > 0 else 0.0,
                _m.exp(-seuil * lo_rate / r) if lo_rate > 0 else 1.0)

    r_true, q_true, seuil = 40.0, 0.004, 7753.0
    rng2 = random.Random(31337)
    rows, amount = [], 0.0
    for d in range(4000):
        amount = 0.0 if rng2.random() < q_true else amount + r_true
        rows.append((d, amount))
    r_hat, drops, fav, lo, hi = estimate(rows, seuil)
    truth = _m.exp(-seuil * q_true / r_true)
    b = abs(r_hat - r_true) < 1e-9
    c = lo <= truth <= hi
    print(f"1 quinquies. journal simulé (r={r_true:.0f}, q={q_true}) : "
          f"r estimé {r_hat:.1f}, {drops} chutes")
    print(f"             fraction favorable {fav:.4%}, vraie {truth:.4%}, "
          f"intervalle [{lo:.4%}, {hi:.4%}]  "
          f"{'ok' if b and c else 'ÉCHEC'}")
    ok &= a and b and c

    # 1 sexies. Forensics.bonusPosition : la queue binomiale de la cellule
    # dominante, qui remplace un χ² à vingt classes mal calibré. Trois façons
    # de se tromper en silence : la récurrence du coefficient binomial, la
    # sommation en échelle logarithmique, et l'union sur les vingt positions.
    def binomial_tail(k, n, pr):
        if k <= 0:
            return 1.0
        if k > n:
            return 0.0
        logC = sum(_m.log(n - i) - _m.log(i + 1) for i in range(k))
        tot, lc = 0.0, logC
        for i in range(k, n + 1):
            tot += _m.exp(lc + i * _m.log(pr) + (n - i) * _m.log1p(-pr))
            if i < n:
                lc += _m.log(n - i) - _m.log(i + 1)
        return min(1.0, tot)

    a = True
    for nn in (12, 40, 200):
        for kk in (1, 2, 5, nn // 2, nn):
            got = binomial_tail(kk, nn, 1 / 20)
            ref = _st.binom.sf(kk - 1, nn, 1 / 20)
            a &= abs(got - ref) < 1e-12 * max(1.0, ref)
    print(f"\n1 sexies. queue binomiale contre scipy, 15 points : "
          f"{'ok' if a else 'ÉCHEC'}")

    # Calibration : uniforme -> p grand, position fixe -> p écrasant dès 12.
    rngb = random.Random(7)
    cnt = [0] * 20
    for _ in range(200):
        cnt[rngb.randrange(20)] += 1
    p_unif = min(1.0, 20 * binomial_tail(max(cnt), 200, 1 / 20))
    p_fix = min(1.0, 20 * binomial_tail(12, 12, 1 / 20))
    b = p_unif > 0.05 and p_fix < 1e-10
    a &= b
    print(f"1 sexies. positions uniformes p = {p_unif:.3f} ; position fixe sur "
          f"12 tirages p = {p_fix:.2e}  {'ok' if b else 'ÉCHEC'}")
    ok &= a

    # 1 septies. Les trois familles modernes ajoutées à PRNGRecovery.swift,
    # transcrites depuis le Swift et confrontées aux valeurs de référence
    # produites par `tools/sweep_order.c` (compilé et exécuté). Une constante
    # de rotation fausse — 7 au lieu de 45, 9 au lieu de 11 — donnerait un
    # générateur d'apparence saine mais incapable de retrouver quoi que ce
    # soit : exactement le genre d'erreur qui ne se voit pas sans référence.
    M64 = (1 << 64) - 1
    M32 = (1 << 32) - 1

    def _smnext(st):
        st = (st + 0x9E3779B97F4A7C15) & M64
        z = st
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return st, z ^ (z >> 31)

    def _rl64(x, k):
        return ((x << k) | (x >> (64 - k))) & M64

    def _rl32(x, k):
        return ((x << k) | (x >> (32 - k))) & M32

    seed = 0x0123456789ABCDEF
    st = seed
    vv = []
    for _ in range(4):
        st, v = _smnext(st)
        vv.append(v)
    A, B, C, D = vv
    o256 = []
    for _ in range(5):
        r = (_rl64((B * 5) & M64, 7) * 9) & M64
        t = (B << 17) & M64
        C ^= A; D ^= B; B ^= C; A ^= D; C ^= t; D = _rl64(D, 45)
        o256.append(r >> 32)

    st = seed
    st, u = _smnext(st)
    st, v = _smnext(st)
    A, B, C, D = u & M32, (u >> 32) & M32, v & M32, (v >> 32) & M32
    o128 = []
    for _ in range(5):
        r = (_rl32((B * 5) & M32, 7) * 9) & M32
        t = (B << 9) & M32
        C ^= A; D ^= B; B ^= C; A ^= D; C ^= t; D = _rl32(D, 11)
        o128.append(r)

    st = seed
    st, A = _smnext(st)
    st, B = _smnext(st)
    oxo = []
    for _ in range(5):
        s0, s1 = A, B
        r = (s0 + s1) & M64
        s1 ^= s0
        A = _rl64(s0, 24) ^ s1 ^ ((s1 << 16) & M64)
        B = _rl64(s1, 37)
        oxo.append(r >> 32)

    REF = {
        "xoshiro256**": [2730664992, 100410832, 1650359295, 463789510, 3741983874],
        "xoshiro128**": [1038917469, 3889024309, 3818883509, 328341858, 2220985983],
        "xoroshiro128+": [3941436066, 3003168496, 1196682349, 924613345, 3111143280],
    }
    got = {"xoshiro256**": o256, "xoshiro128**": o128, "xoroshiro128+": oxo}
    a = all(got[k] == REF[k] for k in REF)
    print()
    for k in REF:
        print(f"1 septies. {k:<15} contre la référence C : "
              f"{'ok' if got[k] == REF[k] else 'ÉCHEC ' + str(got[k])}")
    ok &= a

    # 1 ter. testRestartMixtureSeesALateDefectThatACumulativeBetCannot :
    # même arithmétique, même graine, même LCG que le test Swift — forme
    # martingale par BLOCS (h2) : au 1er pas du bloc j, S += w_j = 1/(j(j+1)),
    # puis S *= f ; N = S + 1/(bloc_courant + 2).
    import math as _m

    def _lae(a, b):
        if a == -_m.inf:
            return b
        if b == -_m.inf:
            return a
        hi = max(a, b)
        return hi + _m.log1p(_m.exp(min(a, b) - hi))

    def _traj(defect_first):
        seed = 20260827
        m64 = (1 << 64) - 1

        def bern(q):
            nonlocal seed
            seed = (seed * 6364136223846793005 + 1442695040888963407) & m64
            return 1.0 if (seed >> 33) / 2147483648.0 < q else 0.0

        theta, pb = 0.40, 0.25
        log_m = _m.log(pb * _m.exp(theta) + (1 - pb))
        quiet, loud, block = 20000, 400, 16
        cum, sr, mc, mn, n = 0.0, -_m.inf, 0.0, 0.0, 0.0
        for t in range(quiet + loud):
            biased = t < loud if defect_first else t >= quiet
            x = 1.0 if biased else bern(pb)
            lf = theta * x - log_m
            cum += lf
            if t % block == 0:
                j = t // block + 1
                sr = _lae(sr, -_m.log(j * (j + 1)))
            sr = min(700, sr + lf)
            mc = max(mc, cum)
            n = _m.exp(min(700, sr)) + 1.0 / (t // block + 2)
            mn = max(mn, n)
        return _m.exp(cum), _m.exp(mc), n, mn

    lc_f, lc_s, ln_f, _ = _traj(False)
    ec_f, ec_s, en_f, en_s = _traj(True)
    checks = [
        ("valeur finale du pari cumule identique tot/tard",
         abs(lc_f - ec_f) <= 1e-12 * max(1.0, ec_f), f"{lc_f:.3e} contre {ec_f:.3e}"),
        ("defaut TARDIF : sup du pari cumule sous 20", lc_s < 20, f"{lc_s:.3f}"),
        ("defaut TARDIF : martingale par blocs au-dessus de 1e40", ln_f > 1e40, f"{ln_f:.3e}"),
        ("temoin, defaut TOT : sup du pari cumule au-dessus de 20", ec_s > 20, f"{ec_s:.3e}"),
        ("temoin, defaut TOT : sup de la martingale au-dessus de 1e45", en_s > 1e45, f"{en_s:.3e}"),
        ("defaut TOT : richesse relancee depensee en fin de course", en_f < 1, f"{en_f:.3e}"),
    ]
    print("\n1 ter. melange de relances par blocs, forme martingale (h2) :")
    for label, good, val in checks:
        print(f"       {label:<56} {val:>12}   {'ok' if good else 'ÉCHEC'}")
        ok &= good

    for stake in (5, 6, 7, 8, 10):
        tail = [hypergeometric_tail(stake, t) for t in range(stake + 1)]
        p_all = hypergeometric_p_all(stake)

        # 2. testTailLawIsExactHypergeometric
        ref = []
        for t in range(stake + 1):
            e = sum(exact_comb(20, h) * exact_comb(60, stake - h) for h in range(t, stake + 1))
            ref.append(e / exact_comb(80, stake))
        a = abs(tail[0] - 1.0) < 1e-12
        b = all(abs(tail[t] - ref[t]) < 1e-9 for t in range(stake + 1))
        c = all(tail[t] <= tail[t - 1] for t in range(1, stake + 1))
        d = abs(tail[stake] - p_all) < 1e-12
        ok &= a and b and c and d

        # 3. testGridPackIsSpread + testGridPackHasNoNearDuplicatePair
        fields = {n: [rng.gauss(0, 1) for _ in range(POOL)] for n in ("alpha", "omega", "nexus")}
        grids, cover = make_grids(fields, stake)
        distinct = len({n for g in grids for n in g})
        want = min(12 * stake, 80)
        max_cover = int(max(cover))
        ceiling_cov = (12 * stake + 79) // 80
        pairs_max = max(len(set(grids[i]) & set(grids[j]))
                        for i in range(12) for j in range(i + 1, 12))
        e = distinct == want
        f = max_cover <= ceiling_cov
        g = pairs_max <= stake // 2
        ok &= e and f and g

        # 4. testPackProbabilityIsExactAndNearItsCeiling
        pack = pack_p_all_hit(grids, stake)
        ceiling = 12 * p_all
        h = p_all < pack <= ceiling and pack > 0.98 * ceiling
        ok &= h

        print(f"\n  mise {stake}")
        print(f"    loi de survie exacte, décroissante, tail[k]=P(pleine)   "
              f"{'ok' if a and b and c and d else 'ÉCHEC'}")
        print(f"    couverture {distinct}/{want} attendus, max {max_cover}<={ceiling_cov}   "
              f"{'ok' if e and f else 'ÉCHEC'}")
        print(f"    recouvrement max entre 2 grilles {pairs_max} <= {stake // 2}   "
              f"{'ok' if g else 'ÉCHEC'}")
        print(f"    paquet 1/{1/pack:,.0f} contre 1/{1/p_all:,.0f} seule, "
              f"{pack / ceiling:.5f} du plafond   {'ok' if h else 'ÉCHEC'}")

    # 9. Le barème relevé (§56) et les quatre tests de PayTable.
    #    L'algorithme testé ici est celui de Prophet/Models/PayTable.swift,
    #    transcrit : somme de log(i) pour log(n!), puis exp de la différence.
    #    Il est comparé au calcul exact en Fractions, ce que Swift ne peut
    #    pas faire — c'est donc le contrôle que la version Swift ne peut pas
    #    s'offrir elle-même.
    import csv as _csv
    from fractions import Fraction as _F

    bareme = {}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "bareme_observed.csv")) as fh:
        for row in _csv.DictReader(l for l in fh if not l.startswith("#")):
            bareme.setdefault(int(row["mise"]), {})[int(row["hits"])] = float(row["gain_base"])

    def _logfact(n):
        return sum(math.log(i) for i in range(2, n + 1))

    def _logC(n, k):
        return -math.inf if (k < 0 or k > n) else _logfact(n) - _logfact(k) - _logfact(n - k)

    def _prob(k, h):
        l = _logC(k, h) + _logC(80 - k, 20 - h) - _logC(80, 20)
        return math.exp(l) if math.isfinite(l) else 0.0

    def _exact_E(k):
        g = bareme[k]
        return float(sum(_F(int(v)) * _F(exact_comb(k, h) * exact_comb(80 - k, 20 - h),
                                         exact_comb(80, 20)) for h, v in g.items()))

    E_swift = {k: sum(v * _prob(k, h) for h, v in g.items()) for k, g in bareme.items()}
    E_exact = {k: _exact_E(k) for k in bareme}
    worst_E = max(abs(E_swift[k] - E_exact[k]) / E_exact[k] for k in bareme)
    mass_worst = max(abs(sum(_prob(k, h) for h in range(k + 1)) - 1) for k in bareme)
    lo_E, hi_E = min(E_exact.values()), max(E_exact.values())
    spread = (hi_E - lo_E) / (sum(E_exact.values()) / len(E_exact))
    price_lo, legacy_up = hi_E, 1 + lo_E
    p6 = 1 / 7753.0
    exact_thr = (2 - E_swift[6]) / p6
    ratio = exact_thr / (2 / p6)
    edge = 2287 * p6 / 2
    naive_over_true = (2287 / exact_thr) / edge

    a = worst_E < 1e-10                       # testPayTableExpectationsCollapse...
    b = mass_worst < 1e-12
    c = spread < 0.03
    d = abs(E_swift[6] - 1.1764564549) < 1e-8
    e = abs(price_lo - 1.1971176275) < 1e-8 and price_lo > 1
    f = abs(legacy_up - 2.1668190816) < 1e-8
    g = all(x > price_lo for x in (1.5, 2, 2.5, 3)) and 1 not in (1.5, 2, 2.5, 3)
    h = abs(exact_thr - 6384.9331) < 1e-3 and abs(ratio - 0.41177) < 1e-4
    i = abs(edge - 0.1474913) < 1e-6
    j = abs(naive_over_true - 2 / (2 - 1.1764564549)) < 1e-4
    ok &= a and b and c and d and e and f and g and h and i and j

    print(f"\n9. Barème relevé (§56) — PayTable.swift")
    print(f"    log-somme contre Fractions exactes : écart relatif max {worst_E:.2e}   "
          f"{'ok' if a else 'ÉCHEC'}")
    print(f"    masse hypergéométrique à 1 près de {mass_worst:.2e}   "
          f"{'ok' if b else 'ÉCHEC'}")
    print(f"    collapse : cinq espérances à {spread:.2%}, E[6] = {E_swift[6]:.10f}   "
          f"{'ok' if c and d else 'ÉCHEC'}")
    print(f"    ticket : c > {price_lo:.4f} (CHF 1 exclu), règle 100 ct/CHF "
          f"valide jusqu'à {legacy_up:.4f}   {'ok' if e and f and g else 'ÉCHEC'}")
    print(f"    seuil exact à c=2 : CHF {exact_thr:,.0f} = {ratio:.1%} du suffisant   "
          f"{'ok' if h else 'ÉCHEC'}")
    print(f"    gain conditionnel mu*p/c = {edge:.7f}, le naïf mu/S le "
          f"surestimerait de x{naive_over_true:.2f}   {'ok' if i and j else 'ÉCHEC'}")

    print(f"\n{'=' * 74}")
    print("VERDICT :", "toutes les assertions des tests Swift sont satisfaites"
          if ok else "AU MOINS UNE ASSERTION ÉCHOUERAIT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
