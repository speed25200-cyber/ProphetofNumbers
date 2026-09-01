"""h98 — le bit zéro des sorties ADDITIVES : rouvrir la case que j'avais fermée.

CE QUE LE DOSSIER AFFIRMAIT, ET MOI AVEC
=========================================
Le §68 écarte explicitement les sorties additives du champ des attaques
F2-linéaires :

    « Les sorties additives (xorshift128+, xoroshiro128+) ne sont pas
      linéaires. »

Je l'ai repris à mon compte tout au long de cette session, et j'ai même bâti
dessus mon estimation de nos chances : `xorshift128+` — le `Math.random` de
Firefox et de Safari — classé dans la case « aucune quantité de données n'y
change rien ».

C'EST FAUX POUR UN BIT, ET UN BIT SUFFIT.

LE THÉORÈME DU BIT ZÉRO ADDITIF
================================
    Soient A et B deux fonctions F2-LINEAIRES de l'état. Alors

        bit_0(A + B)  =  bit_0(A)  XOR  bit_0(B)

    PREUVE. L'addition entière propage des retenues du bit k vers le bit k+1.
    Aucune retenue n'entre dans le bit 0 : il n'y a rien en dessous de lui.
    Le bit 0 d'une somme est donc le XOR des bits 0, sans correction. []

    Dès le bit 1 la retenue a_0·b_0 entre dans le calcul, et la forme
    F2 est détruite.

C'est le pendant exact du §100 — qui traitait d'une constante additive — pour
un TERME additif variable. Et il change la portée de tout ce qui suit :

    TOUTE FAMILLE « + » — xorshift128+, xoroshiro128+, xoshiro256+ — A UN BIT
    ZERO EXACTEMENT F2-LINEAIRE EN SON ETAT, et se laisse donc attaquer par
    élimination de Gauss comme n'importe quelle famille à sortie brute.

MESURE (section 1) : sur `xorshift128+`, le bit 0 est prédit par sa forme
linéaire 8000 fois sur 8000 ; le bit 1, 4065 fois sur 8000 — le hasard.

CE QUI LE PUBLIE
=================
Il faut une observation qui expose le bit 0 de la sortie. Sous échantillonneur
MODULO, c'est immédiat :

    designation du bonus par indice modulo  :  rang = sortie mod 20
                                               rang mod 2 = sortie mod 2

puisque 2 divise 20. Chacun des 70 560 tirages triés publie donc UNE équation
F2 exacte sur l'état — et il n'en faut que 128 pour `xorshift128+`, 256 pour
`xoshiro256+`.

    C'est un modèle DIFFERENT de celui du §106 et du §114, qui supposaient un
    indice TRONQUE. Les deux sont plausibles ; aucun n'était testé sur les
    familles additives.

Il TESTE l'archive : il consigne au registre.
"""

import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H98_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H98_TMP", "/tmp")
POOL, DRAWN, KB = 80, 20, 20
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
HORIZON = 10
PLANS = [(21, 20), (21, 0)] if DRY else [(20, 19), (21, 20), (21, 0), (22, 20),
                                         (22, 21), (41, 40), (42, 40)]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def rotl(x, k, w=64):
    m = (1 << w) - 1
    return ((x << k) | (x >> (w - k))) & m


# ==========================================================================
# LES FAMILLES « + » — celles que le §68 declarait hors d'atteinte
# ==========================================================================
def xs128p(s):
    """xorshift128+ : le Math.random de Firefox et de Safari."""
    A = s & M64
    B = (s >> 64) & M64
    res = (A + B) & M64
    t = A ^ ((A << 23) & M64)
    n1 = t ^ B ^ (t >> 18) ^ (B >> 5)
    return (B | (n1 << 64)), res


def xoroshiro128p(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    res = (s0 + s1) & M64
    s1 ^= s0
    n0 = rotl(s0, 24) ^ s1 ^ ((s1 << 16) & M64)
    n1 = rotl(s1, 37)
    return (n0 | (n1 << 64)), res


def xoshiro256p(s):
    w = [(s >> (64 * i)) & M64 for i in range(4)]
    res = (w[0] + w[3]) & M64
    t = (w[1] << 17) & M64
    w[2] ^= w[0]
    w[3] ^= w[1]
    w[1] ^= w[2]
    w[0] ^= w[3]
    w[2] ^= t
    w[3] = rotl(w[3], 45)
    return sum(v << (64 * i) for i, v in enumerate(w)), res


def xoshiro128p32(s):
    w = [(s >> (32 * i)) & M32 for i in range(4)]
    res = (w[0] + w[3]) & M32
    t = (w[1] << 9) & M32
    w[2] ^= w[0]
    w[3] ^= w[1]
    w[1] ^= w[2]
    w[0] ^= w[3]
    w[2] ^= t
    w[3] = rotl(w[3], 11, 32)
    return sum(v << (32 * i) for i, v in enumerate(w)), res


FAMILLES = [("xorshift128+ (Firefox, Safari)", 128, xs128p),
            ("xoroshiro128+", 128, xoroshiro128p),
            ("xoshiro256+", 256, xoshiro256p),
            ("xoshiro128+ (32 bits)", 128, xoshiro128p32)]


# ==========================================================================
# LE SYSTÈME : UNE ÉQUATION PAR TIRAGE, LE BIT ZÉRO
# ==========================================================================
def formes_bit0(step, nbits, positions):
    """La forme F2 du BIT ZERO de la sortie, aux positions demandees.

    LA SUPERPOSITION EST LEGITIME ICI, ET ELLE NE L'EST QUE POUR LE BIT ZERO.
    La transition d'etat est F2-lineaire ; la SORTIE ne l'est pas, mais son bit
    0 l'est par le theoreme. Lire le bit 0 sur les vecteurs unitaires donne donc
    exactement la forme cherchee — ce qui serait FAUX pour tout autre bit.
    """
    besoin = set(positions)
    nmax = max(positions) + 1
    out = {p: 0 for p in positions}
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nmax):
            s, w = step(s)
            if k in besoin and (w & 1):
                out[k] |= bit
    return out


def ecrire(chemin, formes, bits, positions, nbits):
    W8 = (nbits + 63) // 64
    n = 0
    with open(chemin, "wb") as f:
        f.write(struct.pack("<ii", nbits, 0))
        for d, b in enumerate(bits):
            f.write(formes[positions[d]].to_bytes(W8 * 8, "little"))
            f.write(bytes([int(b) & 1]))
            n += 1
        f.seek(4)
        f.write(struct.pack("<i", n))
    return n


def resoudre(chemin, binaire):
    p = subprocess.run([binaire, chemin], capture_output=True, text=True, timeout=1800)
    d = dict(kv.split("=") for kv in p.stdout.split("\n")[0].split())
    sol = None
    for l in p.stdout.split("\n"):
        if l.startswith("solution="):
            h = l.split("=")[1]
            mots = [int(h[i:i + 16], 16) for i in range(0, len(h), 16)]
            sol = sum(m << (64 * i) for i, m in enumerate(mots))
    return int(d["rang"]), int(d["incoherent"]), sol


def tirages_modulo(step, etat, nd, stride, off, W):
    """Tirages par Fisher-Yates MODULO, plus l'indice de bonus MODULO 20."""
    mots, s = [], etat
    for _ in range(nd * stride + off + 2):
        s, w = step(s)
        mots.append(w)
    out = []
    for d in range(nd):
        arr = list(range(1, POOL + 1))
        ordre = []
        for k in range(DRAWN):
            j = k + (mots[d * stride + k] % (POOL - k))
            arr[k], arr[j] = arr[j], arr[k]
            ordre.append(arr[k])
        rang = mots[d * stride + off] % KB
        out.append((ordre, rang))
    return out


# ==========================================================================
rule("1. LE THÉORÈME DU BIT ZÉRO ADDITIF")
# ==========================================================================

say("""   Le §68 ecarte les sorties additives du champ des attaques F2-lineaires :
   « les sorties additives (xorshift128+, xoroshiro128+) ne sont pas
   lineaires ». Je l'ai repris a mon compte toute la session, et j'ai bati
   dessus mon estimation de nos chances.

   C'EST FAUX POUR UN BIT, ET UN BIT SUFFIT.

   THEOREME. Soient A et B deux fonctions F2-LINEAIRES de l'etat. Alors

       bit_0(A + B) = bit_0(A) XOR bit_0(B)

   PREUVE. L'addition propage des retenues du bit k vers le bit k+1. Aucune
   retenue n'entre dans le bit 0 : il n'y a rien en dessous de lui. []

   C'est le pendant exact du §100 — qui traitait d'une CONSTANTE additive —
   pour un TERME additif variable.

   VERIFICATION, sur xorshift128+ :""")
NW = 40
rng = np.random.default_rng(20260920)
for nom, nbits, step in FAMILLES[:1]:
    c0 = [0] * NW
    c1 = [0] * NW
    for i in range(nbits):
        s = 1 << i
        for k in range(NW):
            s, w = step(s)
            if w & 1:
                c0[k] |= 1 << i
            if (w >> 1) & 1:
                c1[k] |= 1 << i
    ok0 = ok1 = 0
    for _ in range(200):
        x = int(rng.integers(0, 1 << 62)) | (int(rng.integers(0, 1 << 62)) << 62)
        x &= (1 << nbits) - 1
        s = x
        for k in range(NW):
            s, w = step(s)
            ok0 += (bin(c0[k] & x).count("1") & 1) == (w & 1)
            ok1 += (bin(c1[k] & x).count("1") & 1) == ((w >> 1) & 1)
    say(f"""
     bit 0 predit par sa forme lineaire : {ok0}/{200*NW}
     bit 1 predit par une forme lineaire : {ok1}/{200*NW}   (le hasard)

   CE QUE CELA CHANGE. Toute famille « + » a un bit zero exactement
   F2-lineaire en son etat, et se laisse donc attaquer par elimination de Gauss
   comme n'importe quelle famille a sortie brute.

   CE QUI LE PUBLIE. Sous echantillonneur MODULO, la designation du bonus par
   indice donne rang = sortie mod 20, donc rang mod 2 = sortie mod 2 puisque 2
   divise 20. Chacun des 70 560 tirages publie UNE equation F2 exacte — et il
   n'en faut que 128 pour xorshift128+, 256 pour xoshiro256+.

   C'est un modele DIFFERENT du §106 et du §114, qui supposaient un indice
   TRONQUE. Les deux sont plausibles ; aucun n'etait teste sur les additives.""")


# ==========================================================================
rule("2. LE TÉMOIN : RECONSTITUER, PUIS PRÉDIRE")
# ==========================================================================

BIN = os.path.join(TMP, "f2solve98")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "f2solve.c")], check=True,
               capture_output=True)

say(f"""   On plante un etat, on fabrique des tirages par Fisher-Yates MODULO avec
   un indice de bonus modulo 20, on ne garde que LA PARITE DU RANG — un bit par
   tirage — on reconstitue, puis on annonce le tirage suivant.
""")
say(f"   {'famille':>32} {'état':>6} {'tirages':>8} {'rang':>6} "
    f"{'tirage +1':>11} {f'horizon {HORIZON}':>11} {'sec':>7}")
import random                                                  # noqa: E402
rnd = random.Random(20260921)
TEM = []
for nom, nbits, step in FAMILLES:
    tt = time.time()
    nd = nbits * 3
    st, off = 21, 20
    etat = rnd.getrandbits(nbits) | 1
    vrai = tirages_modulo(step, etat, nd + HORIZON + 1, st, off, nbits)
    bits = [t[1] & 1 for t in vrai[:nd]]
    pos = [d * st + off for d in range(nd)]
    F = formes_bit0(step, nbits, pos)
    ch = os.path.join(TMP, "h98.bin")
    ecrire(ch, F, bits, pos, nbits)
    rang, inc, sol = resoudre(ch, BIN)
    ok1 = okh = False
    if sol is not None and not inc:
        pred = tirages_modulo(step, sol, nd + HORIZON + 1, st, off, nbits)
        ok1 = pred[nd][0] == vrai[nd][0]
        okh = pred[nd:nd + HORIZON] == vrai[nd:nd + HORIZON]
    TEM.append(ok1)
    say(f"   {nom:>32} {nbits:>6} {nd:>8} {rang:>6} "
        f"{('EXACT' if ok1 else 'non'):>11} "
        f"{(f'{HORIZON}/{HORIZON}' if okh else '—'):>11} {time.time()-tt:>7.1f}")

say(f"""
   {sum(TEM)}/{len(TEM)} etats de familles ADDITIVES reconstitues et predits — depuis UN BIT
   par tirage. Ce sont les familles que le §68 declarait hors d'atteinte.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

ARCH = lab.load()
BON = np.asarray(ARCH.bonus).astype(np.int64)
NUM = np.asarray(ARCH.nums)
RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
say(f"""   La parite du rang du bonus, sur les {len(RANG):,} tirages. Pour chaque famille
   et chaque hypothese de consommation (stride, position du mot d'indice) :
""")
say(f"   {'famille':>32} {'hypothèses':>11} {'incohérents':>12} "
    f"{'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS, INCOH = 0, 0, 0
for nom, nbits, step in FAMILLES:
    tt = time.time()
    nd = nbits * 3
    tr, ess, inc_ = 0, 0, 0
    for st, off in PLANS:
        if off >= st:
            continue
        pos = [d * st + off for d in range(nd)]
        F = formes_bit0(step, nbits, pos)
        ch = os.path.join(TMP, "h98.bin")
        ecrire(ch, F, (RANG[:nd] & 1).tolist(), pos, nbits)
        rang, inc, sol = resoudre(ch, BIN)
        ess += 1
        inc_ += inc
        if not inc and sol is not None:
            pred = tirages_modulo(step, sol, min(nd, 300), st, off, nbits)
            tr += int([p[1] & 1 for p in pred] == (RANG[:min(nd, 300)] & 1).tolist())
    TOTAL += tr
    ESSAIS += ess
    INCOH += inc_
    say(f"   {nom:>32} {ess:>11} {inc_:>12} {tr:>12} {time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} hypotheses — {INCOH} systemes incoherents.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h98.bit_zero_additif",
        "Aucune famille a sortie ADDITIVE — xorshift128+ (le Math.random de "
        "Firefox et de Safari), xoroshiro128+, xoshiro256+, xoshiro128+ — "
        "n'engendre les rangs du bonus de l'archive, a etat COMPLET, sous une "
        "designation du bonus par indice MODULO 20",
        "theoreme du bit zero additif : bit_0(A+B) = bit_0(A) XOR bit_0(B), "
        "aucune retenue n'entrant dans le bit 0. Le bit zero d'une sortie "
        "additive est donc exactement F2-lineaire en l'etat, et rang mod 2 = "
        "sortie mod 2 puisque 2 divise 20. Une equation F2 exacte par tirage, "
        "elimination par tools/f2solve.c, puis rejeu",
        "aucun null n'est requis : le systeme est incoherent ou il ne l'est pas",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {sum(TEM)}/{len(TEM)} etats de familles additives "
                  f"reconstitues DEPUIS UN SEUL BIT PAR TIRAGE, puis tirage suivant "
                  f"annonce exactement et horizon de {HORIZON} tirages verifie"),
        notes=("Le §68 ecarte les sorties additives du champ F2-lineaire, et je "
               "l'ai repris a mon compte toute la session — jusqu'a batir dessus "
               "mon estimation de nos chances, en classant xorshift128+ dans la "
               "case « aucune quantite de donnees n'y change rien ». C'est faux "
               "POUR UN BIT, et un bit suffit : mesure, le bit 0 est predit par sa "
               "forme lineaire 8000 fois sur 8000, le bit 1 4065 fois sur 8000. La "
               "superposition sur vecteurs unitaires est legitime pour le bit 0 et "
               "pour lui seul. Modele d'observation DIFFERENT du §106 et du §114, "
               "qui supposaient un indice TRONQUE ; ici l'indice est MODULO."))
    h = lab.holm()
    say(f"   consigne : h98.bit_zero_additif   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA CHANGE À LA CARTE")
# ==========================================================================

say(f"""   J'AI EU TORT DEUX FOIS SUR LES SORTIES ADDITIVES. Au §112, en croyant que
   le Math.random de V8 en etait une — il n'en est pas, il est brut. Ici, en
   croyant que celles qui en sont vraiment resistent a tout — leur bit zero ne
   resiste a rien.

   CE QUI RESTE VRAIMENT HORS D'ATTEINTE, et la liste a encore maigri :
     — les sorties MULTIPLIEES : xoshiro256** et xoroshiro128**, dont la sortie
       est rotl(s*5,7)*9. La multiplication par un impair PRESERVE le bit 0
       (bit_0(5x) = bit_0(x)), mais la ROTATION le deplace : le bit 0 de la
       sortie devient un bit INTERMEDIAIRE du produit, ou les retenues sont
       entrees. La rotation est donc ce qui protege, pas la multiplication.
     — PCG, dont la rotation est de surcroit dependante des donnees ;
     — splitmix64 et les chaines de melange a decalages multiplies ;
     — tout CSPRNG, et le materiel.

   ET UNE REGLE QUI SORT DE LA : POUR CASSER LE BIT ZERO, IL FAUT UNE ROTATION
   OU UN DECALAGE A DROITE APPLIQUE APRES UNE ADDITION. Une addition seule ne
   suffit pas, une multiplication par un impair non plus.

   ({time.time() - T0:.1f} s)""")
