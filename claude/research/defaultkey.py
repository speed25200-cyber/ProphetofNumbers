"""Counter-mode ciphers under a default or trivially guessable key.

A certified deployment would use AES-CTR-DRBG or ChaCha20 with a real key, and no
amount of output reveals it. A *misconfigured* one might not: an all-zero key, an
all-0xFF key, a key that is the product name, a key derived from the draw date. That
is the classic default-credential failure, and it costs nothing to rule out.

The counter is taken from public data — the draw id, the draw index, the timestamp —
because that is what a counter-mode DRBG would actually be stepping through. Every
(cipher, key, counter, derivation) combination is checked against real draws.
"""
import struct, hashlib, datetime
import numpy as np
from math import comb
from Crypto.Cipher import AES, ChaCha20
from load import load

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
        if p+4 > len(d): return frozenset(out)
        u = int.from_bytes(d[p:p+4], 'big'); p += 4
        j = i + (((u*k) >> 32) if mulhi else (u % k))
        a[i], a[j] = a[j], a[i]; out.append(a[i])
    return frozenset(out)

def rej_bytes(d):
    s = []; p = 0
    while len(s) < 20 and p < len(d):
        b = d[p]; p += 1
        if b >= 240: continue
        v = b % 80 + 1
        if v not in s: s.append(v)
    return frozenset(s)

DERIV = [("fy_mulhi", lambda d: fy_words(d, True)),
         ("fy_mod",   lambda d: fy_words(d, False)),
         ("rejection", rej_bytes),
         ("colex",    lambda d: unrank_colex(int.from_bytes(d, 'big') % C8020))]

def keys32():
    ks = {"zero": b"\x00"*32, "ff": b"\xff"*32,
          "0123": bytes(range(32)),
          "lotoexpress": (b"lotoexpress" + b"\x00"*32)[:32],
          "loro": (b"loro" + b"\x00"*32)[:32],
          "LoterieRomande": (b"LoterieRomande" + b"\x00"*32)[:32],
          "sha256(lotoexpress)": hashlib.sha256(b"lotoexpress").digest(),
          "sha256(loro)": hashlib.sha256(b"loro").digest(),
          "sha256()": hashlib.sha256(b"").digest()}
    return ks

def counters(i, ids, ts):
    I, T = int(ids[i]), int(ts[i])
    dtu = datetime.datetime.utcfromtimestamp(T)
    yield "id_be16",   struct.pack(">Q", 0) + struct.pack(">Q", I)
    yield "idx_be16",  struct.pack(">Q", 0) + struct.pack(">Q", I-1309614)
    yield "ts_be16",   struct.pack(">Q", 0) + struct.pack(">Q", T)
    yield "id_le16",   struct.pack("<Q", I) + b"\x00"*8
    yield "date_id",   (dtu.strftime("%Y%m%d").encode() + struct.pack(">Q", I) + b"\x00"*16)[:16]

if __name__ == "__main__":
    ids, ts, nums, boost, bonus = load()
    TEST = [0, 1, 5, 900, 30000, 70559]
    TRUE = {i: frozenset(nums[i].tolist()) for i in TEST}
    KS = keys32()
    n = 0; best = (0, None)
    for kn, key in KS.items():
        for cn, _ in counters(0, ids, ts):
            for dn, df in DERIV:
                for algo in ("aes-ctr", "chacha20"):
                    m = 0
                    for i in TEST:
                        ctr = dict(counters(i, ids, ts))[cn]
                        try:
                            if algo == "aes-ctr":
                                c = AES.new(key[:16], AES.MODE_ECB)
                                blocks = b"".join(
                                    c.encrypt(ctr[:15] + bytes([b])) for b in range(6))
                            else:
                                c = ChaCha20.new(key=key, nonce=ctr[:8])
                                blocks = c.encrypt(b"\x00"*96)
                            cand = df(blocks)
                        except Exception:
                            cand = frozenset()
                        m = max(m, len(cand & TRUE[i]))
                    n += 1
                    if m > best[0]: best = (m, (algo, kn, cn, dn))
                    if m >= 15:
                        print("  !! STRONG %s key=%s ctr=%s %s -> %d/20" % (algo, kn, cn, dn, m))
    print("Counter-mode ciphers under default / guessable keys")
    print("  %d combinations (2 ciphers x %d keys x %d counters x %d derivations),"
          % (n, len(KS), 5, len(DERIV)))
    print("  each checked against %d real draws. Chance overlap is about 5/20.\n" % len(TEST))
    print("  best overlap: %d/20 at %s" % best)
    print("\n  %s" % ("NOTHING: no default-key counter mode reproduces the archive"
                      if best[0] < 15 else "INVESTIGATE"))
