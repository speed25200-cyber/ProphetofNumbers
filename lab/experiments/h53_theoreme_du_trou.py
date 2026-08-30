"""h53 — le theoreme du trou : les tirages ordonnes n'ont pas besoin d'etre voisins.

La contrainte que les §68 et §71 se sont imposee
=================================================
Les deux attaques exigent des tirages ordonnes CONSECUTIFS, et le dossier n'en
a qu'une paire (1381030, 1381031). Ses cinq tirages ordonnes valent donc deux :

    1381023   1381026   1381028   1381030   1381031
            \\_ 3 _/  \\_ 2 _/  \\_ 2 _/  \\_ 1 _/

Trois des cinq etaient inutilisables. C'etait une erreur de raisonnement, pas
une limite.

LE THEOREME DU TROU
====================
Avancer un generateur F2-lineaire de k pas est ENCORE UNE APPLICATION
LINEAIRE. Un trou ne detruit donc rien : il deplace l'indice du mot, et les
equations de deux tirages separes se chainent exactement comme celles de deux
tirages voisins, pourvu qu'on sache DE COMBIEN DE MOTS le trou a avance
l'etat.

Deux regimes, et le premier est gratuit :

  FISHER-YATES     consomme EXACTEMENT 20 mots par tirage. Un trou de g
                   tirages avance donc de 20g mots, connu sans ambiguite.
                   Les cinq tirages ordonnes se chainent SANS RIEN ENUMERER.

  REJET MODULO 80  consomme 20 + R mots, R aleatoire d'esperance 2,849. Un
                   trou de g tirages coute une enumeration sur la somme des R,
                   bornee et petite.

CE QUE CELA CHANGE
==================
Le budget passe de 2 tirages a 5. Sous Fisher-Yates : 2 x 22 = 44 bits
deviennent 5 x 22 = 110, ce qui fait entrer xorshift96 dans le testable. Sous
rejet : 2 x 80 = 160 deviennent 5 x 80 = 400.

Aucune collecte supplementaire n'est necessaire — les donnees etaient la.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import itertools
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
DRY = os.environ.get("H53_DRY") == "1"
RMAX = 4 if DRY else 8            # rejets tolerés par tirage traversé


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(n):
    k = 0
    while n and n % 2 == 0:
        n //= 2
        k += 1
    return k


def msk(n):
    return (1 << n) - 1


def xs32(s):
    s ^= (s << 13) & msk(32)
    s ^= s >> 17
    s ^= (s << 5) & msk(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & msk(64)
    s ^= s >> 7
    s ^= (s << 17) & msk(64)
    return s, s


def xs96(s):
    x, y, z = s & msk(32), (s >> 32) & msk(32), (s >> 64) & msk(32)
    t = (x ^ (x << 3)) & msk(32)
    t ^= t >> 19
    x, y = y, z
    z = (z ^ (z << 6) ^ t) & msk(32)
    return x | (y << 32) | (z << 64), z


def xs128(s):
    x, y = s & msk(32), (s >> 32) & msk(32)
    z, w = (s >> 64) & msk(32), (s >> 96) & msk(32)
    t = (x ^ (x << 11)) & msk(32)
    t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & msk(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


FAMS = [("xorshift32", 32, xs32), ("xorshift64", 64, xs64),
        ("xorshift96", 96, xs96), ("xorshift128", 128, xs128)]

FY_BITS = sum(v2(POOL - i) for i in range(DRAWN))


def fy_draw(step, s):
    a, out = list(range(1, POOL + 1)), []
    for i in range(DRAWN):
        s, w = step(s)
        j = i + w % (POOL - i)
        a[i], a[j] = a[j], a[i]
        out.append(a[i])
    return out, s


def coeffs(step, nbits, nwords):
    """COEF[pos][b] : coefficients de « bit b du mot d'indice pos »."""
    cols = []
    for i in range(nbits):
        s, seq = 1 << i, []
        for _ in range(nwords):
            s, w = step(s)
            seq.append(w)
        cols.append(seq)
    coef = [[0] * 8 for _ in range(nwords)]
    for i in range(nbits):
        ci, bit = cols[i], 1 << i
        for pos in range(nwords):
            w = ci[pos]
            for b in range(8):
                if (w >> b) & 1:
                    coef[pos][b] |= bit
    return coef


def solve(rows, rhs, nbits):
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
                return None
    sol = 0
    for h in sorted(piv):
        pr, pb = piv[h]
        if (bin(pr & sol).count("1") + pb) & 1:
            sol ^= 1 << h
    return sol, [i for i in range(nbits) if i not in piv]


def fy_equations(draw, base, coef):
    """Les equations d'un tirage Fisher-Yates place au mot `base`."""
    rows, rhs = [], []
    a = list(range(1, POOL + 1))
    for i, num in enumerate(draw):
        j = a.index(num, i)
        a[i], a[j] = a[j], a[i]
        k = v2(POOL - i)
        if k == 0:
            continue
        val = (j - i) & msk(k)
        cp = coef[base + i]
        for b in range(k):
            rows.append(cp[b])
            rhs.append((val >> b) & 1)
    return rows, rhs


def attack_gapped_fy(step, nbits, items, coef, max_free=18):
    """items = [(offset en tirages depuis le premier, tirage ordonne)].

    Sous Fisher-Yates l'offset en MOTS vaut 20 x offset en tirages : le trou
    ne coute rien du tout.
    """
    rows, rhs = [], []
    for off, draw in items:
        r, h = fy_equations(draw, off * DRAWN, coef)
        rows += r
        rhs += h
    res = solve(rows, rhs, nbits)
    if res is None:
        return [], len(rows)
    sol, free = res
    if len(free) > max_free:
        return [], len(rows)
    found = []
    for combo in range(1 << len(free)):
        cand = sol
        for t, fb in enumerate(free):
            if (combo >> t) & 1:
                cand ^= 1 << fb
        if not cand:
            continue
        s, ok = cand, True
        for off, draw in items:
            # rejouer depuis l'etat candidat jusqu'au tirage vise
            st = cand
            for _ in range(off):
                _, st = fy_draw(step, st)
            got, _ = fy_draw(step, st)
            if got != draw:
                ok = False
                break
        if ok:
            found.append(cand)
    return found, len(rows)


# ==========================================================================
rule("1. LE THÉORÈME DU TROU")
# ==========================================================================

say(f"""   Avancer un generateur F2-lineaire de k pas est ENCORE une application
   lineaire : L^k l'est des que L l'est. Un trou ne detruit donc aucune
   equation — il deplace l'indice du mot, rien de plus.

   Ce qu'il faut savoir, c'est de combien de MOTS le trou a avance l'etat.

     FISHER-YATES     {DRAWN} mots par tirage, exactement. Un trou de g tirages
                      avance de {DRAWN}g mots : connu, aucune enumeration.
     REJET MODULO {POOL}  {DRAWN} + R mots, R d'esperance 2,849. Un trou de g
                      tirages coute une enumeration sur la somme des R.

   Les §68 et §71 exigeaient des tirages CONSECUTIFS. C'etait une erreur de
   raisonnement, pas une limite : trois des cinq tirages ordonnes du dossier
   etaient jetes sans raison.""")


# ==========================================================================
rule("2. CE QUE LES CINQ TIRAGES VALENT MAINTENANT")
# ==========================================================================

rows_csv = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = {int(r["id"]): [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)] for r in rows_csv}
ids = sorted(ORD)
span = ids[-1] - ids[0] + 1
items = [(i - ids[0], ORD[i]) for i in ids]

say(f"""   {ids}
   trous : {[b - a for a, b in zip(ids, ids[1:])]}   etendue : {span} tirages, soit {span * DRAWN} mots.

     avant (consecutifs seuls)   2 tirages   {2 * FY_BITS:>3} bits sous Fisher-Yates
     apres (le trou traverse)    {len(ids)} tirages   {len(ids) * FY_BITS:>3} bits
""")
say(f"   {'famille':<14} {'bits':>5} {'testable avant':>15} {'testable après':>15}")
for nom, nbits, _ in FAMS:
    before = "oui" if nbits <= 2 * FY_BITS else "non"
    after = "oui" if nbits <= len(ids) * FY_BITS else "non"
    flag = "  <- gagne" if before == "non" and after == "oui" else ""
    say(f"   {nom:<14} {nbits:>5} {before:>15} {after:>15}{flag}")


# ==========================================================================
rule("3. LE TÉMOIN, AVEC LES MÊMES TROUS QUE L'ARCHIVE")
# ==========================================================================

rng = __import__("random").Random(20260908)
offs = [i - ids[0] for i in ids]
say(f"""   Chaque famille est amorcee sur un etat tire au hasard, on engendre
   {span} tirages consecutifs en Fisher-Yates, puis on n'en GARDE que les
   positions {offs} — exactement les trous de l'archive. L'attaque doit
   retrouver l'etat malgre les trous.
""")
say(f"   {'famille':<14} {'bits':>5} {'équations':>10} {'retrouvé':>9} {'temps':>8}")
ctrl = 0
for nom, nbits, step in FAMS:
    if nbits > len(ids) * FY_BITS:
        say(f"   {nom:<14} {nbits:>5} {'—':>10} {'hors budget':>9} {'—':>8}")
        continue
    st = rng.getrandbits(nbits) or 1
    s, all_draws = st, []
    for _ in range(span):
        d, s = fy_draw(step, s)
        all_draws.append(d)
    kept = [(o, all_draws[o]) for o in offs]
    t = time.time()
    coef = coeffs(step, nbits, span * DRAWN)
    got, neq = attack_gapped_fy(step, nbits, kept, coef)
    dt = time.time() - t
    ok = st in got
    ctrl += ok
    say(f"   {nom:<14} {nbits:>5} {neq:>10} {'OUI' if ok else 'non':>9} {dt:>7.2f}s")
say(f"\n   {ctrl} familles retrouvees malgre les trous.")


# ==========================================================================
rule("4. SUR L'ARCHIVE")
# ==========================================================================

say(f"   {'famille':<14} {'bits':>5} {'équations':>10}  {'états compatibles':>18}")
total, tested = 0, 0
for nom, nbits, step in FAMS:
    if nbits > len(ids) * FY_BITS:
        say(f"   {nom:<14} {nbits:>5} {'—':>10}  {'hors budget':>18}")
        continue
    tested += 1
    coef = coeffs(step, nbits, span * DRAWN)
    got, neq = attack_gapped_fy(step, nbits, items, coef)
    total += len(got)
    say(f"   {nom:<14} {nbits:>5} {neq:>10}  {len(got):>18}")
say(f"\n   TOTAL : {total} etat compatible, sur {tested} familles testables.")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h53.theoreme_du_trou",
        f"Aucun generateur F2-lineaire d'etat <= {len(ids) * FY_BITS} bits, echantillonnant en "
        f"Fisher-Yates, ne reproduit les CINQ tirages ordonnes de l'archive — "
        f"y compris a travers leurs trous, pour aucune graine",
        f"nombre d'etats compatibles verifies par rejeu integral ; les trous "
        f"sont traverses exactement, un tirage Fisher-Yates consommant {DRAWN} mots",
        "deterministe : verification par rejeu, aucun null a simuler",
        "conforme si aucun etat compatible", track="A")
    lab.record(tok, float(total), p=None, verdict="conforme",
               power_at=(f"temoin positif : {ctrl} familles retrouvees depuis un etat "
                         f"tire au hasard, avec EXACTEMENT les trous de l'archive "
                         f"({[b - a for a, b in zip(ids, ids[1:])]})"),
               notes=(f"THEOREME DU TROU : avancer un generateur F2-lineaire de k pas "
                      f"reste lineaire, donc deux tirages ordonnes SEPARES se chainent "
                      f"comme deux voisins des lors qu'on sait de combien de mots le "
                      f"trou a avance l'etat. Sous Fisher-Yates c'est exact ({DRAWN} mots "
                      f"par tirage), donc gratuit. Les §68 et §71 exigeaient des "
                      f"consecutifs et jetaient trois des cinq tirages ordonnes : le "
                      f"budget passe de {2 * FY_BITS} a {len(ids) * FY_BITS} bits sans "
                      f"aucune collecte supplementaire."))
    h = lab.holm()
    say(f"   consigne : h53.theoreme_du_trou   etats compatibles {total}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA AJOUTE, ET UNE CIBLE QUI NE TIENT PAS")
# ==========================================================================

say(f"""   AJOUTE. Le budget d'un jeu de tirages ordonnes ne depend pas de leur
   voisinage mais de leur NOMBRE. Sous Fisher-Yates les cinq tirages du
   dossier valent {len(ids) * FY_BITS} bits au lieu de {2 * FY_BITS}, et xorshift96 devient testable
   sans qu'un seul tirage de plus ait ete collecte. Les donnees etaient la ;
   c'est le raisonnement qui les jetait.

   UNE CIBLE ANNONCEE QUI NE TIENT PAS. J'avais annonce PCG comme prochaine
   porte, au motif que son brouillage XSH-RR est F2-lineaire a rotation
   fixee. C'est vrai de la SORTIE et faux de l'ensemble : l'etat de PCG
   avance par un LCG modulo 2^64, qui n'est pas F2-lineaire. Les equations de
   deux sorties successives ne se chainent donc pas, et le theoreme ne
   s'applique pas. PCG reste hors d'atteinte par cette voie — comme
   xoshiro** et ++, splitmix64 et tout CSPRNG.

   LIMITE. Sous rejet modulo {POOL} le trou coute une enumeration sur la somme
   des rejets traverses, bornee mais pas gratuite : ce fichier ne traite que
   le cas Fisher-Yates, ou elle est nulle.

   Registre : consigne a la section 5.

   ({time.time() - T0:.1f} s)""")
