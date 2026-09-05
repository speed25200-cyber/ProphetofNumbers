"""Reduced-round SHA-256 as the draw derivation — the gap hashhunt.py left open.

hashhunt tested full-round MD5/SHA1/SHA256/SHA512/SHA3/BLAKE2 over public inputs. A
system built on a *reduced* compression function is a different hypothesis: it is what
the delta-chain work in the sibling repo actually attacks, and at R <= 16 that function
is invertible in O(1), so a draw feed built on one would be predictable outright.

The reduced compression function is taken verbatim from
delta-chain-sha256/src/sha256_attack_toolkit.py so the two repos agree bit for bit.
Every round count from 1 to 64 is tried against the same public inputs and the same
five derivations hashhunt used.
"""
import struct, numpy as np
from math import comb
from load import load

MASK = 0xFFFFFFFF
H0 = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
K_SHA = [
 0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
 0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
 0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
 0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
 0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
 0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]

def rotr(x, n): return ((x >> n) | (x << (32 - n))) & MASK

def sha256_reduced(msg32, nr):
    """Verbatim from the delta-chain toolkit: 32-byte message, nr rounds."""
    padded = msg32 + b'\x80' + b'\x00'*23 + struct.pack('>Q', 256)
    W = list(struct.unpack('>16I', padded))
    for t in range(16, max(nr, 16)):
        s0 = rotr(W[t-15], 7) ^ rotr(W[t-15], 18) ^ (W[t-15] >> 3)
        s1 = rotr(W[t-2], 17) ^ rotr(W[t-2], 19) ^ (W[t-2] >> 10)
        W.append((s1 + W[t-7] + s0 + W[t-16]) & MASK)
    a, b, c, d, e, f, g, h = H0
    for t in range(nr):
        S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
        ch = (e & f) ^ ((~e & MASK) & g)
        T1 = (h + S1 + ch + K_SHA[t] + W[t]) & MASK
        S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        T2 = (S0 + maj) & MASK
        h = g; g = f; f = e; e = (d + T1) & MASK
        d = c; c = b; b = a; a = (T1 + T2) & MASK
    out = [(H0[i] + v) & MASK for i, v in enumerate([a, b, c, d, e, f, g, h])]
    return b"".join(struct.pack(">I", w) for w in out)

C8020 = comb(80, 20)
CT = [[comb(n, k) if n >= k else 0 for k in range(21)] for n in range(81)]

def unrank_colex(r):
    out = []
    for k in range(20, 0, -1):
        n = k-1
        while n+1 <= 80 and CT[n+1][k] <= r: n += 1
        out.append(n+1); r -= CT[n][k]
    return frozenset(out)

def fy_words(d, mulhi=True):
    a = list(range(1, 81)); out = []; p = 0
    for i in range(20):
        k = 80-i
        u = int.from_bytes(d[p:p+4], 'big'); p += 4
        j = i + (((u*k) >> 32) if mulhi else (u % k))
        a[i], a[j] = a[j], a[i]; out.append(a[i])
    return frozenset(out)

def fy_bytes(d):
    a = list(range(1, 81)); out = []; p = 0
    for i in range(20):
        v = (d[p] << 8) | d[p+1]; p += 2
        j = i + (v % (80-i)); a[i], a[j] = a[j], a[i]; out.append(a[i])
    return frozenset(out)

def rej_bytes(d):
    s = []; p = 0
    while len(s) < 20 and p < len(d):
        b = d[p]; p += 1
        if b >= 240: continue
        v = b % 80 + 1
        if v not in s: s.append(v)
    return frozenset(s)

DERIV = [("fy_words_mulhi", lambda d: fy_words(d, True)),
         ("fy_words_mod",   lambda d: fy_words(d, False)),
         ("fy_bytes",       fy_bytes),
         ("rej_bytes",      rej_bytes),
         ("bigint_colex",   lambda d: unrank_colex(int.from_bytes(d, 'big') % C8020))]

def msg(i, ids, ts, kind):
    I, T = int(ids[i]), int(ts[i])
    if kind == "id_be":   return struct.pack(">I", I) + b"\x00"*28
    if kind == "idx_be":  return struct.pack(">I", I-1309614) + b"\x00"*28
    if kind == "ts_be":   return struct.pack(">I", T) + b"\x00"*28
    if kind == "id_ts":   return struct.pack(">II", I, T) + b"\x00"*24
    if kind == "id_ascii":return (str(I).encode() + b"\x00"*32)[:32]
    if kind == "ts_ascii":return (str(T).encode() + b"\x00"*32)[:32]
    return b"\x00"*32

if __name__ == "__main__":
    ids, ts, nums, boost, bonus = load()
    TEST = [0, 1, 2, 7, 100, 5000, 40000, 70559]
    TRUE = {i: frozenset(nums[i].tolist()) for i in TEST}
    KINDS = ["id_be", "idx_be", "ts_be", "id_ts", "id_ascii", "ts_ascii"]
    print("Reduced-round SHA-256 derivations (the delta-chain compression function)")
    print("  rounds 1..64 x %d public inputs x %d derivations = %d schemes,"
          % (len(KINDS), len(DERIV), 64*len(KINDS)*len(DERIV)))
    print("  each checked against %d real draws. Chance overlap is about 5/20.\n" % len(TEST))
    best = (0, None)
    hist = {}
    for nr in range(1, 65):
        for kind in KINDS:
            for dn, df in DERIV:
                m = 0
                for i in TEST:
                    try: cand = df(sha256_reduced(msg(i, ids, ts, kind), nr))
                    except Exception: cand = frozenset()
                    m = max(m, len(cand & TRUE[i]))
                hist[m] = hist.get(m, 0) + 1
                if m > best[0]: best = (m, (nr, kind, dn))
                if m >= 15:
                    print("  !! STRONG  R=%d %s %s -> %d/20" % (nr, kind, dn, m))
    print("  best overlap over all schemes: %d/20  at %s" % best)
    print("  distribution:", dict(sorted(hist.items())))
    print("\n  %s" % ("NOTHING: no reduced-round derivation reproduces the archive"
                      if best[0] < 15 else "INVESTIGATE"))
