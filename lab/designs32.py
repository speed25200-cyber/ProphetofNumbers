"""designs32 — les designs xorshift de 32 bits a PERIODE PLEINE, calcules.

Extrait du h127 (§150) pour que le h130 balaie exactement la meme liste : pour
chacun des 31^3 x 8 = 238 328 designs de la forme de Marsaglia, le polynome
caracteristique est extrait par Berlekamp-Massey sur le bit 0, et sa
primitivite testee — x^(2^32) = x modulo f, puis ordre 2^32-1 via les facteurs
premiers 3, 5, 17, 257, 65537.
"""

import json
import os

M32 = 0xFFFFFFFF


def pas32(x, a, b, c, o):
    x ^= ((x << a) & M32) if o & 1 else (x >> a)
    x ^= ((x << b) & M32) if o & 2 else (x >> b)
    x ^= ((x << c) & M32) if o & 4 else (x >> c)
    return x & M32


def polmul(p, q):
    r = 0
    while q:
        if q & 1:
            r ^= p
        p <<= 1
        q >>= 1
    return r


def polmod(r, f, d):
    while r.bit_length() - 1 >= d:
        r ^= f << (r.bit_length() - 1 - d)
    return r


def bm(s):
    n = len(s)
    C = B = 1
    L, m = 0, 1
    for i in range(n):
        dd = s[i]
        for j in range(1, L + 1):
            if (C >> j) & 1:
                dd ^= s[i - j]
        if dd:
            T = C
            C ^= B << m
            if 2 * L <= i:
                L, B, m = i + 1 - L, T, 1
            else:
                m += 1
        else:
            m += 1
    return L, C


PRIMES = [3, 5, 17, 257, 65537]
NORD = (1 << 32) - 1


def primitif(f, d=32):
    r = 2
    for _ in range(32):
        r = polmod(polmul(r, r), f, d)
    if r != 2:
        return False
    for p in PRIMES:
        e, r, base = NORD // p, 1, 2
        while e:
            if e & 1:
                r = polmod(polmul(r, base), f, d)
            base = polmod(polmul(base, base), f, d)
            e >>= 1
        if r == 1:
            return False
    return True


def designs_pleins():
    cache = os.path.join(os.environ.get("H127_TMP", "/tmp"), "h127_primitifs.json")
    if os.path.exists(cache):
        return [tuple(x) for x in json.load(open(cache))]
    out = []
    for a in range(1, 32):
        for b in range(1, 32):
            for c in range(1, 32):
                for o in range(8):
                    x, s = 1, []
                    for _ in range(64):
                        s.append(x & 1)
                        x = pas32(x, a, b, c, o)
                    L, C = bm(s)
                    if L == 32 and primitif(C):
                        out.append((a, b, c, o))
    json.dump(out, open(cache, "w"))
    return out
