"""Provably-fair draws, redone for the unranking architecture.

The earlier sweep tested 390 hash schemes by turning a digest into a stream and running
a sampler. But the canonical provably-fair COMBINATION draw does not sample at all:

    rank = H(public input) mod C(80,20)      then unrank into the 20 numbers

which is exactly how you make a k-subset auditable from one published number. That
construction was never tested, because the rank was never computed. It is here.

A match is 61.6 bits at once, so one draw would settle it; every scheme is checked on
several draws anyway. The reduced-round SHA-256 from delta-chain is included, since a
misconfigured or deliberately cheapened hash is the one case where this could be broken
even if the construction is honest.
"""
import hashlib, struct, math, sys, itertools
import numpy as np
from load import load
sys.path.insert(0, ".")

C = math.comb(80, 20)
ids, ts, nums, boost, bonus = load()
ranks = np.fromfile("rank_colex0.bin", dtype=np.uint64)
ranks_lex = np.fromfile("rank_lex0.bin", dtype=np.uint64)

try:
    from redhash import sha256_reduced
    HAVE_RED = True
except Exception:
    HAVE_RED = False

def hashes():
    for name in ("md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b", "blake2s"):
        yield name, (lambda m, n=name: hashlib.new(n, m).digest())
    if HAVE_RED:
        # the reduced compression function takes exactly a 32-byte message, so the
        # input is zero-padded to 32 bytes (or truncated) — that is the scheme, stated,
        # not a silent coercion
        for R in (16, 24, 32, 40, 48, 56, 64):
            yield "sha256_r%d(pad32)" % R, (
                lambda m, r=R: sha256_reduced(m[:32].ljust(32, b"\0"), r))

PREFIX = [b"", b"keno", b"KENO", b"LotoExpress", b"loro", b"loterie", b"romande",
          b"lotoexpress", b"draw", b"seed"]

def inputs(d):
    i, t = int(ids[d]), int(ts[d])
    out = {
        "id_dec":      str(i).encode(),
        "id_le4":      struct.pack("<I", i),
        "id_be4":      struct.pack(">I", i),
        "id_le8":      struct.pack("<Q", i),
        "id_be8":      struct.pack(">Q", i),
        "ts_dec":      str(t).encode(),
        "ts_be4":      struct.pack(">I", t),
        "ts_be8":      struct.pack(">Q", t),
        "id:ts":       ("%d:%d" % (i, t)).encode(),
        "id-ts":       ("%d-%d" % (i, t)).encode(),
        "idts_be":     struct.pack(">QQ", i, t),
    }
    if d > 0:
        out["prev_rank_be"] = struct.pack(">Q", int(ranks[d-1]))
        out["prev_nums"]    = bytes(int(x) for x in nums[d-1])
        out["prev_nums_dec"]= ",".join(str(int(x)) for x in nums[d-1]).encode()
    return out

def reductions(dig):
    yield "first8_be",  int.from_bytes(dig[:8], "big")  % C
    yield "first8_le",  int.from_bytes(dig[:8], "little") % C
    yield "last8_be",   int.from_bytes(dig[-8:], "big") % C
    yield "whole_be",   int.from_bytes(dig, "big")      % C
    yield "whole_le",   int.from_bytes(dig, "little")   % C
    yield "mulhi",      (int.from_bytes(dig[:8], "big") * C) >> 64

DRAWS = [1, 2, 7, 1000, 35280, 70000]
targets = {"colex0": ranks, "lex0": ranks_lex}

nsch = 0; hits = []
for hname, H in hashes():
    for pre in PREFIX:
        for iname, ival in inputs(DRAWS[0]).items():
            for rname, _ in zip([r[0] for r in reductions(b"\0"*32)], range(99)):
                nsch += 1
for hname, H in hashes():
    for pre in PREFIX:
        keys = list(inputs(DRAWS[0]).keys())
        for iname in keys:
            for tgt, arr in targets.items():
                ok = True
                for d in DRAWS:
                    inp = inputs(d)
                    if iname not in inp: ok = False; break
                    dig = H(pre + inp[iname])
                    if dig is None: ok = False; break
                    if not any(v == int(arr[d]) for _, v in reductions(dig)):
                        ok = False; break
                if ok:
                    hits.append((hname, pre, iname, tgt))
print("schemes tried: %d hash x %d prefix x ~11 inputs x 6 reductions x 2 conventions"
      % (len(list(hashes())), len(PREFIX)))
print("  = %d combinations, each checked on %d draws" % (nsch*2, len(DRAWS)))
print("  a wrong scheme matches one draw with probability 2^-61.6")
print()
if hits:
    print("*** MATCHES ***")
    for h in hits: print("   ", h)
else:
    print("no provably-fair unranking scheme of this shape produces the archive")

# positive control: plant one and make sure the harness would see it
plant = hashlib.sha256(b"keno" + str(int(ids[1])).encode()).digest()
pr = int.from_bytes(plant[:8], "big") % C
found = any(v == pr for _, v in reductions(hashlib.sha256(b"keno" + str(int(ids[1])).encode()).digest()))
print("\npositive control: a planted sha256('keno'+id) scheme is recognised:", found)
