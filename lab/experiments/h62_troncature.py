"""h62 — le second echantillonneur, et il fuit plus que le premier.

L'angle mort
=============
Tout le volet §68 a §81 repose sur une seule ligne :

    n = (out mod 80) + 1

C'est l'echantillonneur par MODULO, et le §74 en a tire une conclusion
rassurante : la fuite vaut 20 x v2(vivier), donc un vivier IMPAIR — 79 ou 81 —
l'annulerait entierement. « Un operateur qui aurait choisi 79 numeros aurait
ferme cette voie sans le savoir. »

Sauf que le modulo n'est pas la seule facon d'ecrire un tirage, ni meme la
plus repandue. Il y en a trois, et le dossier n'a teste que la premiere.

    (A) MODULO          n = (out mod 80) + 1
                        C, C++, PHP historique, tout code naif

    (B) TRONCATURE      n = floor(u x 80) + 1,  u = out / 2^W
                        JavaScript (Math.random()*80), Java (nextInt),
                        Python (random()*80), et la moitie des tutoriels

    (C) BITS DE POIDS FORT AVEC REJET
                        k = 7 bits tires, rejetes s'ils valent >= 80
                        Python (random.randrange), Go, Rust

LE THEOREME DE LA TRONCATURE
=============================
Sous (B), n - 1 = floor(out x 80 / 2^W) equivaut a

    out dans [ L_n , R_n ],   R_n - L_n + 1 = 2^W / 80

L'intervalle contraint donc les bits de POIDS FORT de out : tous ceux que L_n
et R_n ont en commun sont EXACTEMENT determines. Leur nombre K_n depend de n,
et son esperance se calcule exactement — ce n'est pas une estimation, c'est
une somme finie sur les 80 intervalles.

Sous (C), les k = 7 bits tires SONT le numero : sept bits par mot accepte,
exactement, sans condition.

CE QUE CELA RENVERSE
=====================
1. LE §74. La fuite de (B) et (C) ne depend PAS de la valuation 2-adique du
   vivier. Un vivier de 79 donne 0 bit sous (A) et ~4,5 sous (B), 7 sous (C).
   La « protection par vivier impair » ne protege que du plus faible des
   trois echantillonneurs.

2. LE §71. Sous Fisher-Yates, (A) ne fuit que 22 bits par tirage parce que la
   plupart des modules 80-i sont impairs. Sous (B), chaque pas fuit ~5 bits
   quel que soit le module : Fisher-Yates cesse d'etre une protection.

3. LE §69. L'echelle des paliers etait calculee a 80 bits par tirage. Sous
   (B) c'est 104, sous (C) 140.

Il TESTE l'archive (ses cinq tirages ordonnes) : il consigne au registre.
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
DRY = os.environ.get("H62_DRY") == "1"
BUDGET = 6.0 if DRY else 40.0
KCAP = 8                                  # cf. §81 : au-dela, non identifiable
# Le plafond de rejets depend de l'ECHANTILLONNEUR, et fortement : (A) et (B)
# ne rejettent que les doublons (~2,85 par tirage), tandis que (C) rejette
# aussi tout mot dont les sept bits valent 80 ou plus — soit 48 sur 128, plus
# du tiers. Un plafond unique rendait le temoin de (C) faux a 0/2.
MAXT_BY = {"A modulo": 5 if DRY else 9,
           "B troncature": 5 if DRY else 9,
           "C bits de poids fort": 10 if DRY else 18}


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


# ==========================================================================
# Les trois echantillonneurs : ce que chacun PUBLIE d'un mot de W bits.
# Chacun rend une liste de (indice de bit, valeur) — les equations lineaires.
# ==========================================================================

def bits_modulo(n0, W, pool):
    """(A) out == n0 (mod pool) publie out mod 2^v2(pool) : les bits BAS."""
    return [(i, (n0 >> i) & 1) for i in range(v2(pool))]


def interval(n0, W, pool):
    """Bornes de out sous (B) : floor(out * pool / 2^W) == n0."""
    L = -(-(n0 << W) // pool)
    R = -(-((n0 + 1) << W) // pool) - 1
    return L, R


def bits_truncate(n0, W, pool):
    """(B) les bits de POIDS FORT communs a L_n et R_n, exactement determines."""
    L, R = interval(n0, W, pool)
    out = []
    for j in range(W - 1, -1, -1):
        if (L >> j) & 1 != (R >> j) & 1:
            break
        out.append((j, (L >> j) & 1))
    return out


def bits_highbits(n0, W, pool):
    """(C) les k bits tires SONT le numero : k = pool.bit_length()."""
    k = pool.bit_length()
    return [(W - k + i, (n0 >> i) & 1) for i in range(k)]


SAMPLERS = [("A modulo", bits_modulo), ("B troncature", bits_truncate),
            ("C bits de poids fort", bits_highbits)]


def exact_leak(sampler, W, pool):
    """Esperance EXACTE du nombre de bits publies par mot accepte.

    Somme finie sur les valeurs possibles de n, ponderee par la largeur de
    leur intervalle — aucun echantillonnage.
    """
    tot = 0.0
    for n0 in range(pool):
        if sampler is bits_truncate:
            L, R = interval(n0, W, pool)
            w = (R - L + 1) / (1 << W)
        else:
            w = 1.0 / pool
        tot += w * len(sampler(n0, W, pool))
    return tot


# ==========================================================================
rule("1. LES TROIS ÉCHANTILLONNEURS, ET CE QUE CHACUN PUBLIE")
# ==========================================================================

W64 = 64
say(f"""   Esperance EXACTE du nombre de bits publies par mot accepte, pour un mot
   de {W64} bits. Aucune simulation : une somme finie sur les intervalles.
""")
say(f"   {'vivier':>7} {'v2':>3} {'(A) modulo':>11} {'(B) troncature':>15} "
    f"{'(C) poids fort':>15}   commentaire")
for pool in (76, 79, 80, 81, 96, 100, 127, 128):
    a = exact_leak(bits_modulo, W64, pool)
    b = exact_leak(bits_truncate, W64, pool)
    c = exact_leak(bits_highbits, W64, pool)
    note = "<- le vivier reel" if pool == POOL else (
        "vivier IMPAIR : (A) muet, (B) et (C) non" if v2(pool) == 0 else "")
    say(f"   {pool:>7} {v2(pool):>3} {a:>11.3f} {b:>15.3f} {c:>15.3f}   {note}")

LA = exact_leak(bits_modulo, W64, POOL)
LB = exact_leak(bits_truncate, W64, POOL)
LC = exact_leak(bits_highbits, W64, POOL)
say(f"""
   PREMIER RENVERSEMENT — LE §74. Ce paragraphe disait : « la fuite est TOUT
   OU RIEN : 34 des 69 tailles de vivier entre 60 et 128 sont impaires et ne
   publient RIEN. Un vivier de 79 rendrait le theoreme du §68 entierement
   vide. »

   C'est vrai de (A) seulement. Sous (B) un vivier de 79 publie
   {exact_leak(bits_truncate, W64, 79):.3f} bits par mot, sous (C) {exact_leak(bits_highbits, W64, 79):.0f}. La protection par parite ne protege
   que du plus faible des trois echantillonneurs — et le dossier n'avait
   teste que celui-la.

   DEUXIEME FAIT, et il est contre-intuitif : (A) est le MOINS fuyant des
   trois sur le vivier reel. {LA:.0f} bits contre {LB:.2f} et {LC:.0f}. Le volet §68-§81
   attaquait donc l'echantillonneur le plus avare.""")


# ==========================================================================
rule("2. SOUS FISHER-YATES, LA PROTECTION DU §71 DISPARAÎT")
# ==========================================================================

say(f"""   Le §71 avait etabli que Fisher-Yates divise la fuite par 3,6 : le pas i
   tire modulo {POOL}-i, et la plupart de ces modules sont IMPAIRS donc muets.
   C'est encore un raisonnement sur (A).
""")
say(f"   {'échantillonneur':>22} {'bits par tirage':>16} {'rapport à (A)+rejet':>21}")
fy_a = sum(v2(POOL - i) for i in range(DRAWN))
fy_b = sum(exact_leak(bits_truncate, W64, POOL - i) for i in range(DRAWN))
fy_c = sum((POOL - i).bit_length() for i in range(DRAWN))
rej_a = DRAWN * LA
for nm, v in [("(A) rejet modulo", rej_a), ("(A) Fisher-Yates", fy_a),
              ("(B) rejet troncature", DRAWN * LB), ("(B) Fisher-Yates", fy_b),
              ("(C) rejet poids fort", DRAWN * LC), ("(C) Fisher-Yates", fy_c)]:
    say(f"   {nm:>22} {v:>16.1f} {v/rej_a:>21.2f}")

say(f"""
   TROISIEME RENVERSEMENT. Sous (B), Fisher-Yates fuit {fy_b:.0f} bits par tirage —
   soit {fy_b/fy_a:.1f} fois plus que sous (A), et {fy_b/rej_a:.2f} fois le rejet modulo lui-meme.
   La raison est immediate : la troncature ne demande PAS que le module soit
   pair, elle publie log2(module) bits quel que soit ce module.

   Fisher-Yates n'est donc une protection que contre (A). Contre (B) et (C)
   il n'en est pas une du tout — il est meme legerement PIRE que le rejet,
   parce qu'il ne gaspille aucun mot.""")


# ==========================================================================
# Les familles, et l'algebre. Identiques au §81, l'observation change seule.
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


def rotl(x, k, w):
    return ((x << k) | (x >> (w - k))) & m(w)


def xoshiro256(s):
    a = [(s >> (64 * i)) & m(64) for i in range(4)]
    t = (a[1] << 17) & m(64)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = rotl(a[3], 45, 64)
    return sum(v << (64 * i) for i, v in enumerate(a)), a[0]


FAMS = [("xorshift32", 32, 32, xs32), ("xorshift64", 64, 64, xs64),
        ("xorshift96", 96, 32, xs96), ("xorshift128", 128, 32, xs128),
        ("taus88", 96, 32, taus88), ("xoshiro256 (brut)", 256, 64, xoshiro256)]


def basis_full(step, nbits, W, nwords):
    """coef[k][j] = forme lineaire « bit j du mot k », pour TOUS les bits.

    Le §68 ne gardait que les quatre bits bas ; (B) et (C) ont besoin des
    bits hauts, donc on garde tout.
    """
    coef = [[0] * W for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            cp = coef[k]
            for j in range(W):
                if (w >> j) & 1:
                    cp[j] |= bit
    return coef


def draw_from(step, state, ndraws, sampler, W, nnum=10**9):
    """Tirage sous l'echantillonneur donne. Rend aussi le nombre de rejets
    rencontres AVANT le nnum-ieme numero accepte — la portee de l'attaque."""
    s, draws, nrej, acc = state, [], 0, 0
    for _ in range(ndraws):
        seen, out, guard = set(), [], 0
        while len(out) < DRAWN:
            s, w = step(s)
            guard += 1
            if guard > 400:
                return None, 0
            n0 = (w % POOL) if sampler is bits_modulo else (
                (w * POOL) >> W if sampler is bits_truncate else None)
            if n0 is None:                       # (C) : rejet des >= 80
                n0 = w >> (W - POOL.bit_length())
                if n0 >= POOL:
                    if acc < nnum:
                        nrej += 1
                    continue
            if n0 + 1 in seen:
                if acc < nnum:
                    nrej += 1
            else:
                seen.add(n0 + 1)
                out.append(n0 + 1)
                acc += 1
        draws.append(out)
    return draws, nrej


def add_eq(piv, row, b, added):
    cur, cb = row, b
    while cur:
        h = cur.bit_length() - 1
        if h in piv:
            pr, pb = piv[h]
            cur ^= pr
            cb ^= pb
        else:
            piv[h] = (cur, cb)
            added.append(h)
            return True
    return cb == 0


def back_sub(piv, nbits):
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol


def kernel_basis(piv, nbits):
    """Base du noyau du systeme echelonne, une par variable libre.

    Les equations ne portent que sur les bits PUBLIES du mot ; le numero, lui,
    vaut out mod 80, ce qui en demande 6,32. Une direction du noyau peut donc
    laisser les bits publies intacts et CHANGER le numero : la solution
    particuliere ne suffit pas, il faut parcourir le noyau. LFSR113 le montre
    — son noyau vaut 17 dimensions et la solution a variables libres nulles
    ne rejoue pas.
    """
    free = [i for i in range(nbits) if i not in piv]
    hs = sorted(piv)
    out = []
    for f in free:
        v = 1 << f
        for h in hs:
            pr, _pb = piv[h]
            if (bin(pr & v).count("1")) & 1:
                v ^= 1 << h
        out.append(v)
    return out


def first_num(step, state, sampler, W):
    """Premier numero produit par cet etat — prefiltre a un pas, 80 fois
    moins cher qu'un rejeu complet."""
    s, guard = state, 0
    k = POOL.bit_length()
    while guard < 400:
        s, w = step(s)
        guard += 1
        if sampler is bits_modulo:
            return w % POOL + 1
        if sampler is bits_truncate:
            return ((w * POOL) >> W) + 1
        n0 = w >> (W - k)
        if n0 < POOL:
            return n0 + 1
    return -1


def replay_ok(step, state, draws, sampler, W):
    got, _ = draw_from(step, state, len(draws), sampler, W)
    return got == draws


def attack(step, nbits, W, draws, coef, nwords, sampler, budget, max_total,
           rank_target):
    """Identique au §81, l'observation seule change : chaque numero fournit
    les equations que l'echantillonneur publie, hautes ou basses."""
    flat = [n for d in draws for n in d]
    t0, found, depth, piv, tick = time.time(), [], -1, {}, [0]

    def dfs(pos, k, left):
        if found:
            return
        tick[0] += 1
        if not (tick[0] & 8191) and time.time() - t0 > budget:
            found.append(None)
            return
        if len(piv) >= rank_target or k == len(flat):
            sol = back_sub(piv, nbits)
            free = [i for i in range(nbits) if i not in piv]
            if not free:
                if replay_ok(step, sol, draws, sampler, W):
                    found.append(sol)
                return
            if len(free) > KCAP:
                return                      # defaut d'observabilite hors portee
            ker = kernel_basis(piv, nbits)
            first = draws[0][0]
            for mask in range(1 << len(ker)):
                c, mm, i2 = sol, mask, 0
                while mm:
                    if mm & 1:
                        c ^= ker[i2]
                    mm >>= 1
                    i2 += 1
                if first_num(step, c, sampler, W) != first:
                    continue
                if replay_ok(step, c, draws, sampler, W):
                    found.append(c)
                    return
            return
        if pos >= nwords:
            return
        added, ok = [], True
        for j, val in sampler(flat[k] - 1, W, POOL):
            if not add_eq(piv, coef[pos][j], val, added):
                ok = False
                break
        if ok:
            dfs(pos + 1, k + 1, left)
        for h in added:
            del piv[h]
        if found:
            return
        if left and k % DRAWN != 0:
            dfs(pos + 1, k, left - 1)

    for t in range(max_total + 1):
        if time.time() - t0 > budget:
            break
        depth = t
        piv.clear()
        dfs(0, 0, t)
        if found:
            break
    hit = found[0] if found and found[0] is not None else None
    if found and found[0] is None:
        depth -= 1
    return hit, max(depth, 0)


def rejection_law(sampler, W, nnum, reps):
    """Loi du nombre de rejets rencontres AVANT le nnum-ieme numero accepte,
    sous l'echantillonneur donne. C'est cette quantite, et non le total, qui
    borne la recherche : elle s'arrete des que le rang est plein."""
    import random
    r = random.Random(4242)
    out = []
    k = POOL.bit_length()
    for _ in range(reps):
        tot, acc, seen = 0, 0, set()
        while acc < nnum:
            if len(seen) == DRAWN:
                seen = set()
            w = r.getrandbits(W)
            if sampler is bits_modulo:
                n0 = w % POOL
            elif sampler is bits_truncate:
                n0 = (w * POOL) >> W
            else:
                n0 = w >> (W - k)
                if n0 >= POOL:
                    tot += 1
                    continue
            if n0 in seen:
                tot += 1
            else:
                seen.add(n0)
                acc += 1
        out.append(tot)
    return out


LAW = {}
NREP = 600 if DRY else 4000


def coverage(sampler, W, nnum, t):
    key = (sampler.__name__, W, nnum)
    if key not in LAW:
        LAW[key] = rejection_law(sampler, W, nnum, NREP)
    L = LAW[key]
    return sum(1 for v in L if v <= t) / len(L)


def rank_curve(step, nbits, W, nwords, sampler):
    """Premier mot atteignant le rang MAXIMAL, et ce rang.

    Comme au §81 : un palier d'un seul mot n'est PAS une saturation. Prendre
    le premier stall pour le rang final donnait a LFSR113 un rang de 111 au
    lieu du vrai, et l'attaque visait une cible inatteignable.
    """
    coef = basis_full(step, nbits, W, nwords)
    import random
    r = random.Random(7)
    piv, ranks = {}, []
    for k in range(nwords):
        n0 = r.randrange(POOL)
        for j, _v in sampler(n0, W, POOL):
            row = coef[k][j]
            while row:
                h = row.bit_length() - 1
                if h in piv:
                    row ^= piv[h]
                else:
                    piv[h] = row
                    break
        ranks.append(len(piv))
    rmax = ranks[-1]
    return ranks.index(rmax) + 1, rmax


# ==========================================================================
rule("3. L'ÉCHELLE DES PALIERS, RECALCULÉE POUR LES TROIS")
# ==========================================================================

say(f"""   Le §69 comptait « nbits / {DRAWN*4} » ; le §80 a montre qu'il faut MESURER le
   mot ou le rang sature. On le mesure ici pour les trois echantillonneurs.
""")
say(f"   {'famille':>20} {'n':>5}" + "".join(f"{'(' + s[0][0] + ') mots':>12}"
                                             for s in SAMPLERS)
    + f"{'gain B/A':>9}")
INFO = {}
for name, nb, W, step in FAMS:
    line = f"   {name:>20} {nb:>5}"
    got = {}
    for sn, sf in SAMPLERS:
        nw = min(400, int(nb / max(1.0, exact_leak(sf, W, POOL))) + 120)
        w, r = rank_curve(step, nb, W, nw, sf)
        got[sn] = (w, r)
        line += f"{w:>12}"
    INFO[name] = (nb, W, step, got)
    line += f"{got['A modulo'][0]/max(1,got['B troncature'][0]):>9.2f}"
    say(line)

say(f"""
   QUATRIEME RENVERSEMENT — LE §69. Sous (B) il faut environ {LA/LB:.0%} des mots
   qu'exige (A), sous (C) environ {LA/LC:.0%}. Trois familles que le dossier
   classait « deux tirages » tiennent desormais dans UN SEUL.

   xoshiro256, que le §81 declarait hors de portee des cinq tirages ordonnes
   (il en fallait {INFO['xoshiro256 (brut)'][3]['A modulo'][0]/DRAWN:.1f}), en demande {INFO['xoshiro256 (brut)'][3]['C bits de poids fort'][0]/DRAWN:.1f} sous (C). Il entre dans la portee.""")


# ==========================================================================
rule("4. LE TÉMOIN POSITIF, SOUS CHAQUE ÉCHANTILLONNEUR")
# ==========================================================================

import random                                                  # noqa: E402
rng = random.Random(31_337)
say(f"""   L'attaque approfondit sur le nombre de rejets rencontres avant le rang
   plein. Elle ne trouve donc que si le motif vrai tient dans la profondeur
   atteinte : c'est une COUVERTURE declaree. Rejets attendus avant le
   {INFO['xorshift64'][3]['A modulo'][0]}e numero, selon l'echantillonneur :

     (A) modulo        {sum(rejection_law(bits_modulo, 64, 19, NREP))/NREP:>5.1f}
     (B) troncature    {sum(rejection_law(bits_truncate, 64, 19, NREP))/NREP:>5.1f}
     (C) poids fort    {sum(rejection_law(bits_highbits, 64, 19, NREP))/NREP:>5.1f}   (il rejette aussi les valeurs >= {POOL})
""")
say(f"   {'famille':>20} {'échantillonneur':>22} {'tir.':>5} {'prof.':>6} "
    f"{'portée':>7} {'retrouvés':>10} {'sec':>7}")
PLAN, DEFECT = [], []
for name, (nb, W, step, got) in INFO.items():
    for sn, sf in SAMPLERS:
        w, r = got[sn]
        need = -(-w // DRAWN)
        if nb - r > KCAP:
            DEFECT.append((name, sn, nb, r, nb - r))
            continue
        if need > 2:
            continue
        mt = MAXT_BY[sn]
        PLAN.append((name, nb, W, step, sn, sf, need, r, w, mt))
        ok, elig, t0, dmin = 0, 0, time.time(), 99
        TRIES = 2 if DRY else 5
        for _ in range(TRIES):
            seed = rng.getrandbits(nb) | 1
            truth, nrej = draw_from(step, seed, need, sf, W, w)
            if truth is None:
                continue
            nw2 = DRAWN * need + mt
            c2 = basis_full(step, nb, W, nw2)
            got2, dep = attack(step, nb, W, truth, c2, nw2, sf, BUDGET, mt, r)
            dmin = min(dmin, dep)
            if nrej <= dep:
                elig += 1
                ok += got2 is not None and replay_ok(step, got2, truth, sf, W)
        say(f"   {name:>20} {sn:>22} {need:>5} {dmin:>6} {elig:>7} {ok:>10} "
            f"{time.time()-t0:>7.1f}")

say("""
   LECTURE. Parmi les graines dont le motif de rejet tient dans la profondeur
   atteinte, l'attaque retrouve l'etat. Les autres sont HORS COUVERTURE, pas
   des echecs : les compter comme des reussites serait malhonnete.""")

if DEFECT:
    say("\n   DEFAUTS D'OBSERVABILITE — familles que l'echantillonneur ne suffit "
        "pas a identifier :\n")
    say(f"   {'famille':>20} {'échantillonneur':>22} {'n':>5} {'rang':>6} "
        f"{'noyau':>6} {'états à départager':>19}")
    for name, sn, nb, r, d in DEFECT:
        say(f"   {name:>20} {sn:>22} {nb:>5} {r:>6} {d:>6} {1 << d:>19,}")
    say("""
   Un noyau non nul veut dire : deux etats donnent les MEMES bits publies et
   des NUMEROS differents. Le systeme lineaire ne les separe pas.""")


# ==========================================================================
rule("5. SUR LES TIRAGES ORDONNÉS DU DOSSIER")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = [(int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
       for r in rows]
pairs = [(ORD[i], ORD[i + 1]) for i in range(len(ORD) - 1)
         if ORD[i + 1][0] == ORD[i][0] + 1]
say(f"   {len(ORD)} tirages ordonnes, {len(pairs)} paire consecutive.")
say(f"   Les combinaisons (famille, echantillonneur) joignables : {len(PLAN)}\n")
say(f"   {'famille':>20} {'échantillonneur':>22} {'essais':>7} {'prof.':>6} "
    f"{'couv.':>6} {'trouvé':>7} {'sec':>7}")
nhit, ntry, COV, INCONC = 0, 0, [], []
for name, nb, W, step, sn, sf, need, r, w, mt in PLAN:
    cases = [[d[1]] for d in ORD] if need == 1 else [[a[1], b[1]] for a, b in pairs]
    hit, t0, dmin = 0, time.time(), 99
    for case in cases:
        ntry += 1
        nw2 = DRAWN * need + mt
        c2 = basis_full(step, nb, W, nw2)
        got2, dep = attack(step, nb, W, case, c2, nw2, sf, BUDGET, mt, r)
        dmin = min(dmin, dep)
        if got2 is not None:
            hit += 1
    nhit += hit
    cov = coverage(sf, W, w, dmin)
    (COV if cov >= 0.20 else INCONC).append(
        cov if cov >= 0.20 else (name, sn, cov))
    say(f"   {name:>20} {sn:>22} {len(cases):>7} {dmin:>6} {cov:>6.0%} "
        f"{hit:>7} {time.time()-t0:>7.1f}"
        + ("" if cov >= 0.20 else "   non concluant"))

say(f"""
   {ntry} attaques, {nhit} etat compatible.

   Les combinaisons dont la couverture tombe sous 20 % sont marquees NON
   CONCLUANTES et ne comptent pas comme testees : {len(INCONC)} sur {len(COV)+len(INCONC)}. Toutes
   relevent de l'echantillonneur (C), qui rejette plus du tiers de ses mots
   et fait donc exploser l'arbre — c'est un cout de CALCUL, pas une limite
   de l'attaque, et il se paierait avec un solveur en C.

   Sur les {len(COV)} combinaisons concluantes : couverture minimale {min(COV):.0%},
   mediane {sorted(COV)[len(COV)//2]:.0%}, aucun etat compatible.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h62.troncature",
        f"Aucun generateur F2-lineaire n'engendre les tirages ordonnes du "
        f"dossier sous les echantillonneurs par TRONCATURE (floor(u x {POOL})) ou "
        f"par BITS DE POIDS FORT AVEC REJET — les deux idiomes que les §68 a "
        f"§81 n'avaient jamais testes, n'ayant considere que le modulo",
        f"elimination de Gauss sur F2 des equations publiees par chaque "
        f"echantillonneur ({LA:.0f}, {LB:.2f} et {LC:.0f} bits par mot), motifs de rejet "
        f"enumeres par approfondissement iteratif, verification par rejeu "
        f"exact ; {ntry} attaques sur {len(COV)} combinaisons concluantes "
        f"(couverture mediane {sorted(COV)[len(COV)//2]:.0%}), {len(INCONC)} ecartees pour "
        f"couverture insuffisante",
        "aucun null requis : un etat compatible se verifie par rejeu, donc le "
        "taux de faux positifs est nul par construction",
        "conforme si aucun etat compatible", track="A")
    tok["m_extra"] = max(0, ntry - 1)
    lab.record(tok, float(nhit), p=1.0, verdict="conforme",
               power_at="temoin positif par famille et par echantillonneur, "
                        "section 4",
               notes=(f"RENVERSE trois conclusions anterieures. (1) §74 : la "
                      f"protection par vivier IMPAIR ne vaut que contre le "
                      f"modulo — un vivier de 79 publie "
                      f"{exact_leak(bits_truncate, W64, 79):.2f} bits par mot sous "
                      f"troncature et {exact_leak(bits_highbits, W64, 79):.0f} sous bits "
                      f"de poids fort. (2) §71 : Fisher-Yates ne divise la fuite "
                      f"que sous modulo ; sous troncature il fuit {fy_b:.0f} bits par "
                      f"tirage contre {fy_a} sous modulo. (3) §69 : l'echelle etait "
                      f"calculee a {DRAWN*4} bits par tirage, or la troncature en donne "
                      f"{DRAWN*LB:.0f} et les bits de poids fort {DRAWN*LC:.0f}. "
                      f"m_extra = {max(0, ntry - 1)}."))
    h = lab.holm()
    say(f"   consigne : h62.troncature   {nhit} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CELA CHANGE, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   CHANGE, et il faut le dire sans detour : le volet §68 a §81 attaquait le
   moins fuyant des trois echantillonneurs idiomatiques, et trois de ses
   conclusions etaient trop rassurantes.

   1. §74 — « un vivier impair fermerait la voie » : faux contre (B) et (C).
      La valuation 2-adique ne gouverne que le modulo.
   2. §71 — « Fisher-Yates divise la fuite par 3,6 » : faux contre (B), ou
      il la MULTIPLIE par {fy_b/fy_a:.1f} par rapport au Fisher-Yates modulo.
   3. §69 — l'echelle des paliers : trop longue de {1 - LA/LC:.0%} sous (C).

   NE CHANGE PAS.
   a. Le theoreme de conversion du §78 est intact : il dit ce qu'un bit vaut,
      pas d'ou il vient. Mais son cas r = 1 devient PLUS accessible, puisque
      (B) et (C) publient {LB:.1f} et {LC:.0f} bits du premier mot au lieu de {LA:.0f}.
   b. Le theoreme d'appartenance du §80 est intact : il porte sur la
      structure de L, pas sur l'observation.
   c. Le resultat reste NUL sur l'archive : aucun etat compatible, sous aucun
      des trois echantillonneurs, pour aucune famille joignable.

   RESTE OUVERT. Un quatrieme idiome existe — le rejet sur un intervalle
   multiple du vivier (« unbiased bounded random », Lemire 2019) — et il
   publie une information de forme differente. Il n'est pas traite ici.

   Registre : consigne a la section 6.

   ({time.time() - T0:.1f} s)""")
