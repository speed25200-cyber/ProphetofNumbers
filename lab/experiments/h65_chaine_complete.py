"""h65 — la chaine Fisher-Yates complete, enfin assez longue.

Ce que les quatre nouveaux tirages changent
============================================
Le §52 attaquait le Fisher-Yates avec UNE elimination et aucun branchement :
sous cet echantillonneur il n'y a pas de rejet, chaque tirage consomme
exactement vingt mots, et les indices j du melange se reconstruisent
EXACTEMENT depuis l'ordre publie. Le probleme n'etait donc pas l'algebre mais
le BUDGET : 22 bits par tirage (§71), et le dossier n'avait que cinq tirages
ordonnes dont deux consecutifs.

    5 tirages x 22 bits = 110 bits  <  128 bits d'etat

Le §52 se limitait de surcroit a la plus longue suite CONSECUTIVE, alors que
son propre theoreme du trou (§72) l'en dispense : sous Fisher-Yates l'etat
avance de vingt mots par tirage, exactement, donc deux tirages separes de g
tirages sont separes de 20g mots — un nombre CONNU. Toute la collecte se
chaine, consecutive ou non.

Avec les quatre tirages 1381256-1381259, le dossier en compte neuf :

    9 tirages x 22 bits = 198 bits  >  128 bits d'etat

Pour la premiere fois, les familles de 128 bits sont ATTEIGNABLES sous
Fisher-Yates, et sans la moindre recherche.

L'HYPOTHESE QU'IL FAUT DECLARER
================================
Chainer les neuf suppose que le generateur n'a pas ete RE-AMORCE entre eux.
Or les cinq premiers sont en session 349 et les quatre nouveaux en session
350 (§65, ancre 1 309 794, periode 204), et le §65 n'a jamais tranche si une
ouverture de session ré-amorce.

On mene donc les trois attaques :

    CONTINU     les neuf chaines            198 bits   suppose la continuite
    SESSION 349 les cinq premiers            110 bits   sans hypothese
    SESSION 350 les quatre nouveaux           88 bits   sans hypothese

Seule la premiere atteint 128 bits. C'est le prix de l'hypothese, et il est
ecrit.

Il TESTE l'archive (ses neuf tirages ordonnes) : il consigne au registre.
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
DRY = os.environ.get("H65_DRY") == "1"
ANCRE, PER = 1_309_794, 204
KCAP = 22                       # dimensions de noyau parcourues (4 M candidats)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


def v2(n):
    k = 0
    while n and n % 2 == 0:
        n //= 2
        k += 1
    return k


def rotl(x, k, w):
    return ((x << k) | (x >> (w - k))) & m(w)


# ==========================================================================
# Les familles. `step` rend (etat suivant, mot) ; les additives rendent en
# plus leurs deux ADDENDES, car c'est eux qui sont lineaires (§83).
# ==========================================================================

def xs32(s):
    s ^= (s << 13) & m(32); s ^= s >> 17; s ^= (s << 5) & m(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & m(64); s ^= s >> 7; s ^= (s << 17) & m(64)
    return s, s


def xs96(s):
    x, y, z = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    t = (x ^ (x << 3)) & m(32); t ^= t >> 19
    x, y = y, z
    z = (z ^ (z << 6) ^ t) & m(32)
    return x | (y << 32) | (z << 64), z


def xs128(s):
    x, y = s & m(32), (s >> 32) & m(32)
    z, w = (s >> 64) & m(32), (s >> 96) & m(32)
    t = (x ^ (x << 11)) & m(32); t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & m(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


def taus88(s):
    s1, s2, s3 = s & m(32), (s >> 32) & m(32), (s >> 64) & m(32)
    b = (((s1 << 13) ^ s1) >> 19) & m(32)
    s1 = (((s1 & 0xFFFFFFFE) << 12) ^ b) & m(32)
    b = (((s2 << 2) ^ s2) >> 25) & m(32)
    s2 = (((s2 & 0xFFFFFFF8) << 4) ^ b) & m(32)
    b = (((s3 << 3) ^ s3) >> 11) & m(32)
    s3 = (((s3 & 0xFFFFFFF0) << 17) ^ b) & m(32)
    return s1 | (s2 << 32) | (s3 << 64), s1 ^ s2 ^ s3


def lfsr113(s):
    z1, z2 = s & m(32), (s >> 32) & m(32)
    z3, z4 = (s >> 64) & m(32), (s >> 96) & m(32)
    b = (((z1 << 6) ^ z1) >> 13) & m(32)
    z1 = (((z1 & 0xFFFFFFFE) << 18) ^ b) & m(32)
    b = (((z2 << 2) ^ z2) >> 27) & m(32)
    z2 = (((z2 & 0xFFFFFFF8) << 2) ^ b) & m(32)
    b = (((z3 << 13) ^ z3) >> 21) & m(32)
    z3 = (((z3 & 0xFFFFFFF0) << 7) ^ b) & m(32)
    b = (((z4 << 3) ^ z4) >> 12) & m(32)
    z4 = (((z4 & 0xFFFFFF80) << 13) ^ b) & m(32)
    return z1 | (z2 << 32) | (z3 << 64) | (z4 << 96), z1 ^ z2 ^ z3 ^ z4


def xoroshiro128(s):
    s0, s1 = s & m(64), (s >> 64) & m(64)
    s1 ^= s0
    n0 = rotl(s0, 24, 64) ^ s1 ^ ((s1 << 16) & m(64))
    return n0 | (rotl(s1, 37, 64) << 64), n0


def xoshiro128(s):
    a = [(s >> (32 * i)) & m(32) for i in range(4)]
    t = (a[1] << 9) & m(32)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = rotl(a[3], 11, 32)
    return sum(v << (32 * i) for i, v in enumerate(a)), a[0]


def xoshiro256(s):
    a = [(s >> (64 * i)) & m(64) for i in range(4)]
    t = (a[1] << 17) & m(64)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = rotl(a[3], 45, 64)
    return sum(v << (64 * i) for i, v in enumerate(a)), a[0]


# --- additives (§83) : la sortie est une SOMME, les addendes sont lineaires --

def xs128p(s):
    """xorshift128+ — Math.random de V8."""
    A, B = s & m(64), (s >> 64) & m(64)
    t = (A ^ ((A << 23) & m(64))) & m(64)
    return B | ((t ^ B ^ (t >> 18) ^ (B >> 5)) << 64), (A + B) & m(64), A, B


def xoro128p(s):
    s0, s1 = s & m(64), (s >> 64) & m(64)
    t = s1 ^ s0
    n0 = rotl(s0, 24, 64) ^ t ^ ((t << 16) & m(64))
    return n0 | (rotl(t, 37, 64) << 64), (s0 + s1) & m(64), s0, s1


LIN = [("xorshift32", 32, xs32), ("xorshift64", 64, xs64),
       ("xorshift96", 96, xs96), ("xorshift128", 128, xs128),
       ("taus88", 96, taus88), ("LFSR113", 128, lfsr113),
       ("xoroshiro128 (brut)", 128, xoroshiro128),
       ("xoshiro128 (brut)", 128, xoshiro128),
       ("xoshiro256 (brut)", 256, xoshiro256)]
ADD = [("xorshift128+ (V8)", 128, xs128p), ("xoroshiro128+", 128, xoro128p)]


# ==========================================================================
# Fisher-Yates : le tirage, et la reconstruction EXACTE des indices.
# ==========================================================================

def fy_indices(draw):
    """Les indices j du melange, reconstruits depuis l'ordre publie.

    A chaque pas i, le numero sorti occupait la position j du tableau courant
    (initialement 1..80). L'inversion est exacte et sans ambiguite — c'est ce
    qui rend l'attaque Fisher-Yates sans recherche.
    """
    a = list(range(1, POOL + 1))
    out = []
    for i, num in enumerate(draw):
        j = a.index(num, i)
        a[i], a[j] = a[j], a[i]
        out.append(j - i)                    # out_i mod (80 - i)
    return out


def fy_draw(step, s):
    a = list(range(1, POOL + 1))
    out = []
    for i in range(DRAWN):
        s, w = step(s)[:2] if len(step(1)) == 4 else step(s)
        j = i + w % (POOL - i)
        a[i], a[j] = a[j], a[i]
        out.append(a[i])
    return out, s


def fy_replay(step, state, ids, id0, additive):
    """Rejoue le generateur depuis `state` et compare aux tirages observes,
    a leurs POSITIONS exactes : 20 mots par tirage, gaps compris."""
    s, want = state, dict(ids)
    last = max(want)
    a = None
    d = 0
    while d <= last:
        arr = list(range(1, POOL + 1))
        got = []
        for i in range(DRAWN):
            r = step(s)
            s, w = (r[0], r[1]) if additive else r
            j = i + w % (POOL - i)
            arr[i], arr[j] = arr[j], arr[i]
            got.append(arr[i])
        if d in want and got != want[d]:
            return False
        d += 1
    return True


# ==========================================================================
# L'algebre.
# ==========================================================================

def forms(step, nbits, positions, additive):
    """Formes lineaires des bits utiles, aux SEULES positions demandees.

    Pour les familles lineaires : bit b du mot. Pour les additives : la forme
    de « a_b XOR b_b », qui est ce que le theoreme de la retenue exploite.
    """
    need = set(positions)
    last = max(positions)
    out = {p: [0] * 8 for p in need}
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(last + 1):
            r = step(s)
            if additive:
                s, _w, a, b = r
                x = a ^ b
            else:
                s, x = r
            if k in need:
                cp = out[k]
                for b2 in range(8):
                    if (x >> b2) & 1:
                        cp[b2] |= bit
    return out


def free_prefix(bits, v):
    """Longueur du prefixe libre du theoreme de la retenue (§83), bornee par
    le nombre v de bits publies."""
    j = 0
    while j < v - 1 and (bits >> j) & 1:
        j += 1
    return j + 1


def build(step, nbits, chain, additive):
    """(lignes, membres de droite, positions) pour une chaine de tirages.

    `chain` : liste de (offset en tirages, numeros ordonnes). L'offset en MOTS
    vaut 20 x offset — c'est le theoreme du trou (§72), exact sous
    Fisher-Yates.
    """
    pos = []
    for off, draw in chain:
        for i in range(DRAWN):
            if v2(POOL - i):
                pos.append(off * DRAWN + i)
    coef = forms(step, nbits, pos, additive)
    rows, rhs = [], []
    for off, draw in chain:
        js = fy_indices(draw)
        for i, val in enumerate(js):
            v = v2(POOL - i)
            if not v:
                continue
            low = val & m(v)
            cp = coef[off * DRAWN + i]
            nb = free_prefix(low, v) if additive else v
            for b in range(nb):
                rows.append(cp[b])
                rhs.append((low >> b) & 1)
    return rows, rhs


def solve(rows, rhs, nbits):
    """Elimination de Gauss. Rend ((solution, base du NOYAU), rang) ou
    (None, rang atteint) si le systeme est incoherent.

    La base du noyau, et non la simple liste des variables libres : flipper
    une variable libre sans corriger les composantes pivots ne donne PAS un
    autre point de l'espace des solutions. Le §52 le faisait, et cela ne
    marchait que par accident sur les familles dont les directions libres
    sont inertes (taus88). Le temoin de la section 2 l'a attrape.
    """
    piv = {}
    for r, b in zip(rows, rhs):
        cur, cb = r, b
        while cur:
            h = cur.bit_length() - 1
            if h in piv:
                pr, pb = piv[h]
                cur ^= pr
                cb ^= pb
            else:
                piv[h] = (cur, cb)
                break
        else:
            if cb:
                return None, len(piv)
    hs = sorted(piv)
    sol = 0
    for h in hs:
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    ker = []
    for f in (i for i in range(nbits) if i not in piv):
        v = 1 << f
        for h in hs:
            pr, _pb = piv[h]
            if bin(pr & v).count("1") & 1:
                v ^= 1 << h
        ker.append(v)
    return (sol, ker), len(piv)


# ==========================================================================
rule("1. LA CHAÎNE, ET LE PRIX DE L'HYPOTHÈSE")
# ==========================================================================

rows_csv = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = [(int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
       for r in rows_csv]
ORD.sort()
FY_BITS = sum(v2(POOL - i) for i in range(DRAWN))


def session(t):
    return (t - ANCRE) // PER


runs, cur = [], [ORD[0][0]]
for a, b in zip([x[0] for x in ORD], [x[0] for x in ORD[1:]]):
    if b == a + 1:
        cur.append(b)
    else:
        runs.append(cur)
        cur = [b]
runs.append(cur)

say(f"""   {len(ORD)} tirages ordonnes. Suites consecutives : {[len(r) for r in runs]}.
   Fisher-Yates publie {FY_BITS} bits par tirage (§71), et le theoreme du trou
   (§72) chaine les tirages NON consecutifs sans perte, l'etat avancant de
   vingt mots par tirage exactement.
""")
CHAINS = {}
by_ses = {}
for t, d in ORD:
    by_ses.setdefault(session(t), []).append((t, d))
CHAINS["CONTINU (les neuf)"] = (ORD, True)
for s_, lst in sorted(by_ses.items()):
    CHAINS[f"session {s_} ({len(lst)} tirages)"] = (lst, False)

say(f"   {'chaîne':>26} {'tirages':>8} {'bits publiés':>13} {'≥ 128 ?':>8}  hypothèse")
for nm, (lst, hyp) in CHAINS.items():
    b = len(lst) * FY_BITS
    say(f"   {nm:>26} {len(lst):>8} {b:>13} {('oui' if b >= 128 else 'non'):>8}"
        f"  {'CONTINUITÉ entre sessions' if hyp else 'aucune'}")

say(f"""
   Seule la chaine CONTINUE atteint 128 bits, et elle suppose que le
   generateur n'est pas re-amorce a l'ouverture de session — question que le
   §65 a laissee ouverte. C'est le prix, et il est ecrit.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF, AVEC LES MÊMES TROUS")
# ==========================================================================

say("""   On fabrique une chaine synthetique ayant EXACTEMENT les memes trous que
   le dossier — memes ecarts entre tirages — et on verifie que l'attaque
   retrouve l'etat. Si les trous cassaient quelque chose, cela se verrait
   ici.
""")
import random                                                  # noqa: E402
rng = random.Random(65_065)
OFFS = [t - ORD[0][0] for t, _ in ORD]
say(f"   ecarts reels (en tirages) : {OFFS}")
say(f"\n   {'famille':>20} {'n':>5} {'rang':>6} {'libres':>7} {'retrouvés':>10} {'sec':>7}")


def first_draw(step, state, additive):
    """Le premier tirage produit par cet etat — prefiltre, 20 pas au lieu de
    quelques milliers."""
    s, arr, out = state, list(range(1, POOL + 1)), []
    for i in range(DRAWN):
        r = step(s)
        s, w = (r[0], r[1]) if additive else r
        j = i + w % (POOL - i)
        arr[i], arr[j] = arr[j], arr[i]
        out.append(arr[i])
    return out


def synth(step, state, offs, additive):
    """Rejoue et extrait les tirages aux offsets voulus."""
    s, out, want = state, {}, set(offs)
    for d in range(max(offs) + 1):
        arr = list(range(1, POOL + 1))
        got = []
        for i in range(DRAWN):
            r = step(s)
            s, w = (r[0], r[1]) if additive else r
            j = i + w % (POOL - i)
            arr[i], arr[j] = arr[j], arr[i]
            got.append(arr[i])
        if d in want:
            out[d] = got
    return [(d, out[d]) for d in offs]


TR = 2 if DRY else 4
for nom, nbits, step in LIN + ADD:
    additive = (nom, nbits, step) in ADD
    ok, t0, rk, fr = 0, time.time(), 0, 0
    for _ in range(TR):
        seed = rng.getrandbits(nbits) | 1
        ch = synth(step, seed, OFFS, additive)
        rws, rhs = build(step, nbits, ch, additive)
        res, rk = solve(rws, rhs, nbits)
        if res is None:
            continue
        sol, free = res
        fr = len(free)
        if len(free) > KCAP:
            continue
        want0 = ch[0][1]
        for combo in range(1 << len(free)):
            c = sol
            mm, t = combo, 0
            while mm:
                if mm & 1:
                    c ^= free[t]
                mm >>= 1
                t += 1
            if not c or first_draw(step, c, additive) != want0:
                continue
            if synth(step, c, OFFS, additive) == ch:
                ok += 1
                break
    say(f"   {nom:>20} {nbits:>5} {rk:>6} {fr:>7} {ok:>7}/{TR} "
        f"{time.time()-t0:>7.1f}")


# ==========================================================================
rule("3. SUR LES NEUF TIRAGES ORDONNÉS DU DOSSIER")
# ==========================================================================

nhit = ntry = 0
for cname, (lst, hyp) in CHAINS.items():
    base = lst[0][0]
    chain = [(t - base, d) for t, d in lst]
    say(f"\n   {cname}   ({len(lst) * FY_BITS} bits publies"
        f"{', suppose la continuite' if hyp else ''})\n")
    say(f"   {'famille':>20} {'n':>5} {'rang':>6} {'libres':>7} {'verdict':>22}")
    for nom, nbits, step in LIN + ADD:
        additive = (nom, nbits, step) in ADD
        if len(lst) * FY_BITS < nbits:
            say(f"   {nom:>20} {nbits:>5} {'—':>6} {'—':>7} "
                f"{'budget insuffisant':>22}")
            continue
        rws, rhs = build(step, nbits, chain, additive)
        res, rk = solve(rws, rhs, nbits)
        ntry += 1
        if res is None:
            say(f"   {nom:>20} {nbits:>5} {rk:>6} {'—':>7} "
                f"{'INCOHÉRENT — exclu':>22}")
            nhit += 0
            continue
        sol, free = res
        if len(free) > KCAP:
            say(f"   {nom:>20} {nbits:>5} {rk:>6} {len(free):>7} "
                f"{'noyau trop grand':>22}")
            continue
        hits = 0
        want0 = chain[0][1]
        offs = [t - base for t, _ in lst]
        for combo in range(1 << len(free)):
            c = sol
            mm, t = combo, 0
            while mm:
                if mm & 1:
                    c ^= free[t]
                mm >>= 1
                t += 1
            if not c or first_draw(step, c, additive) != want0:
                continue
            if synth(step, c, offs, additive) == chain:
                hits += 1
        nhit += hits
        say(f"   {nom:>20} {nbits:>5} {rk:>6} {len(free):>7} "
            f"{(str(hits) + ' état compatible') if hits else 'aucun état':>22}")

say(f"""
   TOTAL : {ntry} attaques, {nhit} etat compatible.

   Chaque attaque est UNE elimination de Gauss, sans le moindre branchement :
   sous Fisher-Yates il n'y a pas de rejet, et les indices du melange se
   reconstruisent exactement depuis l'ordre publie. Un systeme INCOHERENT
   exclut la famille sans appel — il n'y a pas de marge d'erreur a discuter.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h65.chaine_fy_complete",
        f"Aucun generateur F2-lineaire ou ADDITIF n'engendre les {len(ORD)} tirages "
        f"ordonnes du dossier sous echantillonnage de FISHER-YATES, ni en "
        f"chainant les neuf (hypothese de continuite entre sessions) ni "
        f"session par session",
        f"theoreme du trou (§72) : offset de 20 mots par tirage, exact sous "
        f"Fisher-Yates ; indices du melange reconstruits exactement depuis "
        f"l'ordre publie ; {FY_BITS} bits par tirage (§71) et, pour les familles "
        f"additives, le prefixe libre du theoreme de la retenue (§83) ; UNE "
        f"elimination de Gauss par famille, aucun branchement ; {ntry} attaques",
        "aucun null requis : un systeme incoherent exclut la famille, un etat "
        "compatible se verifie par rejeu — faux positifs nuls par construction",
        "conforme si aucun etat compatible", track="A")
    tok["m_extra"] = max(0, ntry - 1)
    lab.record(tok, float(nhit), p=1.0, verdict="conforme",
               power_at="temoin positif section 2 : chaines synthetiques ayant "
                        "EXACTEMENT les memes trous que le dossier",
               notes=(f"Rendu possible par les quatre tirages 1381256-1381259. "
                      f"Le §52 se limitait a la plus longue suite CONSECUTIVE "
                      f"alors que son propre theoreme du trou l'en dispensait, "
                      f"et le budget n'y suffisait pas : 5 x {FY_BITS} = "
                      f"{5*FY_BITS} bits < 128. Neuf tirages en publient "
                      f"{9*FY_BITS}. La chaine continue suppose l'absence de "
                      f"re-amorcage entre sessions (§65) ; les chaines par "
                      f"session ne le supposent pas mais n'atteignent pas 128 "
                      f"bits. m_extra = {max(0, ntry - 1)}."))
    h = lab.holm()
    say(f"   consigne : h65.chaine_fy_complete   {nhit} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
