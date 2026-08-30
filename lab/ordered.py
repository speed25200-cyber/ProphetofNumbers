"""Primitives du rang ORDONNÉ — partagées entre expériences.

Extrait de `h12_rang_ordonne.py` pour la même raison que `ranks.py` l'avait
été de `h4_rangs.py` : un fichier d'expérience est un SCRIPT, et l'importer
rejoue toute l'expérience. Ce module ne contient que des définitions.

Le théorème qui les gouverne (h12) : une suite ordonnée de 20 numéros parmi
80 a un rang dans [0, M') avec M' = 80!/60! ≈ 2^122,6939. Un générateur
d'état b bits ne peut donc pas produire un tirage ordonné en une seule
sortie dès que b < 122,69 — il lui en faut ⌈122,69/b⌉, et le rang les
publie toutes.

Trois modèles de source, trois solveurs :
  A  LCG 128 bits, une sortie par tirage   -> `solve_a`  (3 tirages à écart
                                              constant, plus racine 2-adique)
  B  LCG 64 bits, deux sorties concaténées -> `solve_b`  (2 tirages)
  C  LCG 32 bits, quatre sorties           -> `solve_c`  (1 seul tirage)
"""

POOL, DRAWN = 80, 20
N128 = 1 << 128
N64 = 1 << 64
N32 = 1 << 32

RADIX = [POOL - i for i in range(DRAWN)]          # 80, 79, …, 61
MP = 1
for r in RADIX:
    MP *= r                                        # M' = 80!/60!
WEIGHT = []
acc = 1
for r in reversed(RADIX):
    WEIGHT.append(acc)
    acc *= r
WEIGHT.reverse()                                   # poids du chiffre i


def fy_indices(order):
    """Chiffres de la représentation : p_i ∈ [0, 80−i)."""
    arr = list(range(1, POOL + 1))
    out = []
    for i, n in enumerate(order):
        j = arr.index(n, i)
        out.append(j - i)
        arr[i], arr[j] = arr[j], arr[i]
    return out


def order_rank(order) -> int:
    return sum(p * w for p, w in zip(fy_indices(order), WEIGHT))


def order_unrank(r: int) -> list:
    arr = list(range(1, POOL + 1))
    out = []
    for i in range(DRAWN):
        p, r = r // WEIGHT[i], r % WEIGHT[i]
        j = i + p
        arr[i], arr[j] = arr[j], arr[i]
        out.append(arr[i])
    return out


def rank_of(s: int, mapping: str) -> int:
    return s % MP if mapping == "mod" else (s * MP) >> 128


def candidates(r: int, mapping: str) -> list:
    """Valeurs 128 bits compatibles avec un rang ordonné observé."""
    if mapping == "mod":
        out, s = [], r
        while s < N128:
            out.append(s)
            s += MP
        return out
    lo = (r * N128 + MP - 1) // MP
    hi = ((r + 1) * N128 + MP - 1) // MP
    return list(range(lo, min(hi, N128)))


# --------------------------------------------------------------------------
# Outils 2-adiques
# --------------------------------------------------------------------------

def inv_pow2(x: int, bits: int = 128):
    """Inverse modulo 2^bits, ou None si x est pair."""
    if x % 2 == 0:
        return None
    inv, mod = 1, 1 << bits
    for _ in range(8):
        inv = inv * (2 - x * inv) % mod
    return inv


def sqrt_mod_2k(A: int, bits: int = 128) -> list:
    """Les quatre racines carrées impaires de A modulo 2^bits (Hensel)."""
    if A % 8 != 1:
        return []
    x = 1
    for k in range(3, bits):
        if (x * x - A) % (1 << (k + 1)):
            x += 1 << (k - 1)
    mod = 1 << bits
    x %= mod
    if (x * x - A) % mod:
        return []
    h = 1 << (bits - 1)
    return sorted({x, (-x) % mod, (x + h) % mod, (-x + h) % mod})


def roots_pow(A: int, g: int, bits: int = 128) -> list:
    """Toutes les racines g-ièmes impaires de A modulo 2^bits.

    Nécessaire parce que le pas entre tirages capturés n'est pas
    nécessairement 2. Écrire `sqrt_mod_2k(A)` revient à supposer g = 2 : à
    g = 1 — des tirages CONSÉCUTIFS, le cas le plus favorable — la racine
    carrée cherche a tel que a² = a, et ne trouve rien. Le solveur rendait
    donc « aucune solution » sur le meilleur schéma de capture possible.

    Décomposition g = 2^v·m avec m impair. Le groupe des unités modulo 2^bits
    a pour exposant 2^(bits−2), donc l'élévation à une puissance IMPAIRE y
    est bijective : la racine m-ième est unique et vaut A^(m⁻¹ mod 2^(bits−2)).
    Restent v racines carrées successives, qui elles ramifient par quatre.
    """
    mod = 1 << bits
    A %= mod
    if A % 2 == 0 or bits < 3:
        return []
    v, m = 0, g
    while m % 2 == 0:
        m //= 2
        v += 1
    lam = 1 << (bits - 2)
    B = pow(A, pow(m % lam, -1, lam), mod)
    roots = [B]
    for _ in range(v):
        nxt = set()
        for r in roots:
            nxt.update(sqrt_mod_2k(r, bits))
        if not nxt:
            return []
        roots = sorted(nxt)
    return roots


def v2(x: int) -> int:
    return (x & -x).bit_length() - 1 if x else 10 ** 9


def ratio_base(num: int, den: int, bits: int, vmax: int = 8):
    """Résout q·den ≡ num (mod 2^bits) — y compris quand den est PAIR.

    C'est le point qui fait tomber la version naïve de cette attaque. Deux
    états d'un LCG diffèrent de (a^n − 1)·s + c_n ; a est impair, donc
    a^n − 1 est TOUJOURS pair, et c_n l'est aussi dès que n est pair. La
    division « (s₂−s₁)/(s₁−s₀) » de h4 n'est donc jamais définie ici : elle
    rejetait silencieusement le vrai générateur, témoins compris.

    La réparation est la valuation 2-adique. Si v = v₂(den), q n'est
    déterminé que modulo 2^(bits−v) et admet 2^v relèvements. Rend
    (base, pas, nombre) — la base suffit à filtrer sur les bits de poids
    faible, qui sont invariants sous relèvement.
    """
    mod = 1 << bits
    num %= mod
    den %= mod
    if den == 0:
        return None
    v = v2(den)
    if v > vmax or v >= bits or num % (1 << v):
        return None
    inv = inv_pow2(den >> v, bits - v)
    if inv is None:
        return None
    step = 1 << (bits - v)
    return (num >> v) * inv % step, step, 1 << v


def step_fwd(a, c, s, n, mod):
    for _ in range(n):
        s = (a * s + c) % mod
    return s


def step_back(ainv, c, s, n, mod):
    for _ in range(n):
        s = (s - c) * ainv % mod
    return s


# --------------------------------------------------------------------------
# MODÈLE A — LCG 128 bits, une sortie par tirage
# --------------------------------------------------------------------------

def solve_a(draws, mapping, vmax=8, collect=False, cap=64, runs_limit=None):
    """draws : [(offset en tirages, rang ordonné)], trié par offset.

    collect=True rend la LISTE de toutes les solutions (plafonnée à `cap`)
    au lieu de la première. C'est ce qui permet de mesurer la classe
    d'équivalence : avec la réduction « floor », le rang ne lit que les
    122,69 bits de poids fort de l'état, donc un décalage de quelques unités
    sur (a, c, s₀) laisse TOUS les rangs observés inchangés. La solution
    n'est alors pas unique, et c'est une limite à mesurer, pas à cacher.
    """
    found = []
    gaps = [draws[i + 1][0] - draws[i][0] for i in range(len(draws) - 1)]
    runs = [(i, gaps[i]) for i in range(len(gaps) - 1) if gaps[i] == gaps[i + 1]]
    if runs_limit is not None:
        runs = runs[:runs_limit]
    for start, g in runs:
        trio = draws[start:start + 3]
        cands = [candidates(r, mapping) for _, r in trio]
        for s0 in cands[0]:
            for s1 in cands[1]:
                D1 = (s1 - s0) % N128
                for s2 in cands[2]:
                    rb = ratio_base((s2 - s1) % N128, D1, 128, vmax)
                    if rb is None:
                        continue
                    baseA, stepA, nA = rb
                    # A = a^g avec a impair. Si g est PAIR, A est un carré
                    # d'impair donc A ≡ 1 (mod 8) ; si g est impair, A hérite
                    # seulement de la parité de a. Le résidu de poids faible
                    # est invariant sous relèvement, donc on filtre avant
                    # d'énumérer — mais avec le bon résidu : exiger 1 mod 8 à
                    # pas impair rejetait tout, y compris le vrai générateur,
                    # sur le meilleur schéma de capture (tirages consécutifs).
                    if (baseA % 8 != 1) if g % 2 == 0 else (baseA % 2 == 0):
                        continue
                    for tA in range(nA):
                        A = (baseA + tA * stepA) % N128
                        C = (s1 - A * s0) % N128
                        for a in roots_pow(A, g):
                            S, p = 0, 1             # 1 + a + … + a^(g−1)
                            for _ in range(g):
                                S = (S + p) % N128
                                p = p * a % N128
                            rc = ratio_base(C, S, 128, 12)
                            if rc is None:
                                continue
                            baseC, stepC, nC = rc
                            for tC in range(nC):
                                c = (baseC + tC * stepC) % N128
                                got = verify_a(a, c, s0, start, draws, mapping)
                                if got:
                                    sol = {"a": a, "c": c, "mapping": mapping,
                                           "last": got[1], "checked": got[0]}
                                    if not collect:
                                        return sol
                                    found.append(sol)
                                    if len(found) >= cap:
                                        return found
    return found if collect else None


def verify_a(a, c, s_at, idx, draws, mapping):
    """Rejoue le LCG dans les deux sens depuis le tirage idx. Rend (n, état final)."""
    ainv = inv_pow2(a)
    if ainv is None:
        return None
    checked = 0
    s = s_at
    for k in range(idx + 1, len(draws)):
        s = step_fwd(a, c, s, draws[k][0] - draws[k - 1][0], N128)
        if rank_of(s, mapping) != draws[k][1]:
            return None
        checked += 1
    last = s
    s = s_at
    for k in range(idx - 1, -1, -1):
        s = step_back(ainv, c, s, draws[k + 1][0] - draws[k][0], N128)
        if rank_of(s, mapping) != draws[k][1]:
            return None
        checked += 1
    return checked, last


# --------------------------------------------------------------------------
# MODÈLES B et C — un tirage = w sortie(s) de b bits, concaténées
# --------------------------------------------------------------------------

def split_words(R, w, bits, big_endian):
    out = [(R >> (bits * (w - 1 - i))) & ((1 << bits) - 1) for i in range(w)]
    return out if big_endian else out[::-1]


def join_words(words, bits, big_endian):
    seq = words if big_endian else words[::-1]
    R = 0
    for x in seq:
        R = (R << bits) | x
    return R


def verify_words(a, c, x0, idx, draws, mapping, w, bits, big_endian):
    """x0 = premier état du tirage idx. Rejoue tous les tirages."""
    mod = 1 << bits
    ainv = inv_pow2(a, bits)
    if ainv is None:
        return None
    # état au premier mot du premier tirage
    s = step_back(ainv, c, x0, w * (draws[idx][0] - draws[0][0]), mod)
    checked = 0
    last = None
    for k in range(len(draws)):
        if k:
            s = step_fwd(a, c, s, w * (draws[k][0] - draws[k - 1][0]), mod)
        words, t = [], s
        for _ in range(w):
            words.append(t)
            t = (a * t + c) % mod
        R = join_words(words, bits, big_endian)
        if R >= N128 or rank_of(R, mapping) != draws[k][1]:
            return None
        checked += 1
        last = s
    return checked, last


def solve_b(draws, mapping, big_endian, bits=64, collect=False, cap=64):
    """Deux sorties par tirage : y = a·x + c donne a par deux tirages."""
    found = []
    mod = 1 << bits
    cands = [[split_words(R, 2, bits, big_endian) for R in candidates(r, mapping)]
             for _, r in draws]
    for i in range(len(draws)):
        for j in range(i + 1, len(draws)):
            for xi, yi in cands[i]:
                for xj, yj in cands[j]:
                    rb = ratio_base((yi - yj) % mod, (xi - xj) % mod, bits)
                    if rb is None:
                        continue
                    base, step, n = rb
                    if base % 2 == 0:               # a doit être impair
                        continue
                    for t in range(n):
                        a = (base + t * step) % mod
                        c = (yi - a * xi) % mod
                        got = verify_words(a, c, xi, i, draws, mapping, 2,
                                           bits, big_endian)
                        if got:
                            sol = {"a": a, "c": c, "mapping": mapping,
                                   "big_endian": big_endian, "bits": bits,
                                   "last": got[1], "checked": got[0]}
                            if not collect:
                                return sol
                            if not any(x["a"] == a and x["c"] == c
                                       for x in found):
                                found.append(sol)
                            if len(found) >= cap:
                                return found
    return found if collect else None


def solve_c(draws, mapping, big_endian, bits=32, collect=False, cap=64):
    """Quatre sorties par tirage : un seul tirage résout ET vérifie."""
    found = []
    mod = 1 << bits
    for i, (_, r) in enumerate(draws):
        for R in candidates(r, mapping):
            w0, w1, w2, w3 = split_words(R, 4, bits, big_endian)
            rb = ratio_base((w2 - w1) % mod, (w1 - w0) % mod, bits)
            if rb is None:
                continue
            base, step, n = rb
            if base % 2 == 0:                       # a doit être impair
                continue
            for t in range(n):
                a = (base + t * step) % mod
                c = (w1 - a * w0) % mod
                if (a * w2 + c) % mod != w3:
                    continue
                got = verify_words(a, c, w0, i, draws, mapping, 4, bits,
                                   big_endian)
                if got:
                    sol = {"a": a, "c": c, "mapping": mapping,
                           "big_endian": big_endian, "bits": bits,
                           "last": got[1], "checked": got[0]}
                    if not collect:
                        return sol
                    if not any(x["a"] == a and x["c"] == c for x in found):
                        found.append(sol)
                    if len(found) >= cap:
                        return found
    return found if collect else None


# --------------------------------------------------------------------------
# Fabrication de tirages témoins
# --------------------------------------------------------------------------

def make_draws(a, c, s, offsets, mapping, w, bits, big_endian):
    """Rend ([(offset, rang)], état juste après le dernier tirage)."""
    mod = 1 << bits
    out = []
    cur = 0
    for off in offsets:
        while cur < off:
            s = step_fwd(a, c, s, w, mod)
            cur += 1
        words, t = [], s
        for _ in range(w):
            words.append(t)
            t = (a * t + c) % mod
        R = join_words(words, bits, big_endian) if w > 1 else words[0]
        out.append((off, rank_of(R % N128, mapping)))
    return out, s


def next_order(a, c, s_first_of_last, mapping, w, bits, big_endian):
    """L'ordre du tirage qui suit celui commençant à s_first_of_last."""
    mod = 1 << bits
    s = step_fwd(a, c, s_first_of_last, w, mod)
    words, t = [], s
    for _ in range(w):
        words.append(t)
        t = (a * t + c) % mod
    R = join_words(words, bits, big_endian) if w > 1 else words[0]
    return order_unrank(rank_of(R % N128, mapping))
