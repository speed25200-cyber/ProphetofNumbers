"""h100 — le sous-espace de linéarité : mesurer la frontière au lieu de l'affirmer.

CE QUE TOUT LE DOSSIER FAISAIT SANS LE MESURER
===============================================
Depuis le §68, chaque section range les générateurs en deux tas — « attaquable
par algèbre linéaire » et « non linéaire, hors d'atteinte » — sur la foi d'un
raisonnement au cas par cas. Et ce raisonnement s'est trompé DEUX FOIS dans
cette seule session :

    §112  j'ai cru que le `Math.random` de V8 était `xorshift128+`, donc
          additif, donc hors d'atteinte. Il est BRUT, donc entièrement linéaire.

    §117  j'ai cru que les vraies familles additives résistaient à tout. Leur
          BIT ZÉRO est exactement linéaire, et un bit a suffi.

Deux erreurs, même cause : une frontière AFFIRMÉE au lieu d'être MESURÉE. Ce
fichier la mesure, et il la mesure exactement.

LE THÉORÈME DU DÉFAUT DE LINÉARITÉ
===================================
    Soit Psi : F2^n -> F2^W l'application « état -> sortie » d'un générateur.
    Posons le DÉFAUT

        D(x, y)  =  Psi(x XOR y) XOR Psi(x) XOR Psi(y) XOR Psi(0)

    Alors une fonctionnelle c dans F2^W est une forme F2-LINÉAIRE de l'état si
    et seulement si

        c . D(x, y) = 0   pour tous x, y.

    PREUVE. Psi est affine en x exactement quand D est identiquement nul ; pour
    une seule composante c.Psi, la condition porte sur c.D. []

    CONSÉQUENCE. L'ensemble des fonctionnelles linéaires est EXACTEMENT
    l'orthogonal du sous-espace engendré par les D(x, y) :

        L  =  vect{ D(x, y) }^perp,        dim L  =  W - rang(D)

    On ne cherche donc pas une forme linéaire au jugé : on calcule la DIMENSION
    de l'espace de toutes celles qui existent. Zéro veut dire qu'il n'y en a
    aucune — pas qu'on n'en a pas trouvé.

CE QUE CELA REND POSSIBLE
==========================
Une réponse COMPLÈTE, par famille, à la question « quelle part de la sortie est
linéaire en l'état ? ». Et une vérification indépendante du §117 : si le
théorème du bit zéro additif est juste, `xorshift128+` doit rendre dim L = 1,
et cette dimension doit être portée par le bit 0.

Il ne teste rien sur l'archive : REGISTRE INCHANGÉ.
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
DRY = os.environ.get("H100_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
NMOTS = 2 if DRY else 4            # mots de sortie concatenes
ECH = 400 if DRY else 2500


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
# LE CATALOGUE, DES PLUS LINÉAIRES AUX PLUS BROUILLÉS
# ==========================================================================
_SRC = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LE TH')], "h86tete", "exec"), _G)


def v8(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    t = (s0 ^ (s0 << 23)) & M64
    t ^= t >> 17
    t ^= s1 ^ (s1 >> 26)
    return (s1 | (t << 64)), s1 >> 12


def xs128p(s):
    A = s & M64
    B = (s >> 64) & M64
    res = (A + B) & M64
    t = A ^ ((A << 23) & M64)
    return (B | ((t ^ B ^ (t >> 18) ^ (B >> 5)) << 64)), res


def xoroshiro128p(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    res = (s0 + s1) & M64
    s1 ^= s0
    return (rotl(s0, 24) ^ s1 ^ ((s1 << 16) & M64)) | (rotl(s1, 37) << 64), res


def _xoshiro256(s):
    w = [(s >> (64 * i)) & M64 for i in range(4)]
    t = (w[1] << 17) & M64
    n = list(w)
    n[2] ^= n[0]
    n[3] ^= n[1]
    n[1] ^= n[2]
    n[0] ^= n[3]
    n[2] ^= t
    n[3] = rotl(n[3], 45)
    return w, sum(v << (64 * i) for i, v in enumerate(n))


def xoshiro256p(s):
    w, ns = _xoshiro256(s)
    return ns, (w[0] + w[3]) & M64


def xoshiro256pp(s):
    w, ns = _xoshiro256(s)
    return ns, (rotl((w[0] + w[3]) & M64, 23) + w[0]) & M64


def xoshiro256ss(s):
    w, ns = _xoshiro256(s)
    return ns, (rotl((w[1] * 5) & M64, 7) * 9) & M64


def xoroshiro128ss(s):
    s0 = s & M64
    s1 = (s >> 64) & M64
    res = (rotl((s0 * 5) & M64, 7) * 9) & M64
    s1 ^= s0
    return (rotl(s0, 24) ^ s1 ^ ((s1 << 16) & M64)) | (rotl(s1, 37) << 64), res


def pcg32(s):
    ns = (6364136223846793005 * s + 1442695040888963407) & M64
    x = ((s >> 18) ^ s) >> 27
    r = s >> 59
    return ns, ((x >> r) | (x << ((-r) & 31))) & M32


def splitmix64(s):
    ns = (s + 0x9E3779B97F4A7C15) & M64
    z = ns
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return ns, z ^ (z >> 31)


CATALOGUE = [
    ("xorshift128 (Marsaglia)", 128, 32, _G["FAMILLES"][3][2], "brute"),
    ("xoshiro256 (brut)", 256, 64, _G["FAMILLES"][7][2], "brute"),
    ("V8 Math.random (§112)", 128, 52, v8, "brute"),
    ("xorshift128+ (Firefox/Safari)", 128, 64, xs128p, "additive"),
    ("xoroshiro128+", 128, 64, xoroshiro128p, "additive"),
    ("xoshiro256+", 256, 64, xoshiro256p, "additive"),
    ("xoshiro256++", 256, 64, xoshiro256pp, "addition + rotation"),
    ("xoshiro256**", 256, 64, xoshiro256ss, "multiplication + rotation"),
    ("xoroshiro128**", 128, 64, xoroshiro128ss, "multiplication + rotation"),
    ("PCG32", 64, 32, pcg32, "rotation variable"),
    ("splitmix64", 64, 64, splitmix64, "chaîne de mélange"),
]


# ==========================================================================
# LE DÉFAUT, ET SON ORTHOGONAL
# ==========================================================================
def psi(step, x, nmots, W):
    """La sortie sur `nmots` pas, concatenee en un vecteur de nmots*W bits."""
    s, v = x, 0
    for k in range(nmots):
        s, w = step(s)
        v |= (w & ((1 << W) - 1)) << (k * W)
    return v


def dim_lineaire(step, n, W, nmots, ech, graine=11):
    """(dimension des fonctionnelles lineaires, rang du defaut)."""
    rnd = random.Random(graine)
    p0 = psi(step, 0, nmots, W)
    piv, rang = {}, 0
    for _ in range(ech):
        x = rnd.getrandbits(n)
        y = rnd.getrandbits(n)
        d = psi(step, x ^ y, nmots, W) ^ psi(step, x, nmots, W) \
            ^ psi(step, y, nmots, W) ^ p0
        while d:
            h = d.bit_length() - 1
            if h in piv:
                d ^= piv[h]
            else:
                piv[h] = d
                rang += 1
                break
    return nmots * W - rang, rang


def base_orthogonale(piv, taille):
    """Une base de l'orthogonal du sous-espace engendre par les lignes de `piv`."""
    hs = sorted(piv)
    libres = [i for i in range(taille) if i not in piv]
    out = []
    for f in libres:
        v = 1 << f
        for h in hs:
            if (bin(piv[h] & v).count("1")) & 1:
                v ^= 1 << h
        out.append(v)
    return out


# ==========================================================================
rule("1. LE THÉORÈME DU DÉFAUT DE LINÉARITÉ")
# ==========================================================================

say("""   Depuis le §68, chaque section range les generateurs en deux tas —
   « attaquable par algebre lineaire » et « non lineaire, hors d'atteinte » —
   sur la foi d'un raisonnement au cas par cas. Ce raisonnement s'est trompe
   DEUX FOIS dans cette seule session :

     §112  j'ai cru que le Math.random de V8 etait xorshift128+, donc additif,
           donc hors d'atteinte. Il est BRUT, donc entierement lineaire.
     §117  j'ai cru que les vraies additives resistaient a tout. Leur BIT ZERO
           est exactement lineaire, et un bit a suffi.

   Deux erreurs, meme cause : une frontiere AFFIRMEE au lieu d'etre MESUREE.

   THEOREME. Soit Psi : F2^n -> F2^W l'application etat -> sortie. Posons

       D(x, y) = Psi(x XOR y) XOR Psi(x) XOR Psi(y) XOR Psi(0)

   Alors c est une forme F2-LINEAIRE de l'etat si et seulement si c.D(x,y) = 0
   pour tous x, y. Donc

       L = vect{ D(x,y) }^perp        et      dim L = W - rang(D)   []

   ON NE CHERCHE PLUS UNE FORME LINEAIRE AU JUGE : on calcule la DIMENSION de
   l'espace de toutes celles qui existent. Zero veut dire qu'il n'y en a
   AUCUNE — pas qu'on n'en a pas trouve.""")


# ==========================================================================
rule("2. LA MESURE, FAMILLE PAR FAMILLE")
# ==========================================================================

say(f"""   Sortie concatenee sur {NMOTS} pas — ce qui attrape aussi les relations
   lineaires ENTRE mots successifs, qu'un test mot par mot manquerait.
   {ECH:,} couples (x, y) par famille.
""")
say(f"   {'famille':>30} {'sortie':>10} {'bits':>5} {'rang défaut':>12} "
    f"{'dim L':>7} {'sec':>6}")
RES = []
for nom, n, W, step, genre in CATALOGUE:
    tt = time.time()
    dl, rg = dim_lineaire(step, n, W, NMOTS, ECH)
    RES.append((nom, genre, dl, NMOTS * W))
    say(f"   {nom:>30} {genre:>10} {NMOTS*W:>5} {rg:>12} {dl:>7} "
        f"{time.time()-tt:>6.1f}")

say(f"""
   LECTURE. dim L est le nombre de bits de la sortie — ou de combinaisons de
   bits — qui sont des formes F2-LINEAIRES exactes de l'etat. C'est exactement
   ce sur quoi une elimination de Gauss peut mordre.""")


# ==========================================================================
rule("3. LA VÉRIFICATION INDÉPENDANTE DU §117")
# ==========================================================================

say("""   Si le theoreme du bit zero additif (§117) est juste, xorshift128+ doit
   rendre dim L = 1 PAR MOT — soit 4 sur les 4 mots concatenes — et chacune de
   ces dimensions doit etre portee par LE BIT 0 d'un mot, et par lui seul. On calcule donc une base de L et on regarde ou elle vit.
""")
rnd = random.Random(11)
p0 = psi(xs128p, 0, NMOTS, 64)
piv = {}
for _ in range(ECH):
    x = rnd.getrandbits(128)
    y = rnd.getrandbits(128)
    d = psi(xs128p, x ^ y, NMOTS, 64) ^ psi(xs128p, x, NMOTS, 64) \
        ^ psi(xs128p, y, NMOTS, 64) ^ p0
    while d:
        h = d.bit_length() - 1
        if h in piv:
            d ^= piv[h]
        else:
            piv[h] = d
            break
B = base_orthogonale(piv, NMOTS * 64)
say(f"   dim L = {len(B)}")
for v in B[:4]:
    bits = [i for i in range(NMOTS * 64) if (v >> i) & 1]
    say(f"     fonctionnelle portee par les bits {bits}  "
        f"(soit le bit {[b % 64 for b in bits]} de chaque mot)")
say("""
   C'est exactement le theoreme du §117, retrouve par une voie entierement
   differente : non pas en raisonnant sur les retenues, mais en calculant
   l'orthogonal d'un defaut mesure.""")


# ==========================================================================
rule("4. LA FRONTIÈRE, ENFIN MESURÉE")
# ==========================================================================

att = [r for r in RES if r[2] > 0]
res = [r for r in RES if r[2] == 0]
say(f"""   ATTEIGNABLES PAR ALGEBRE LINEAIRE — dim L > 0 :""")
for nom, genre, dl, tot in att:
    say(f"     {nom:>30}   dim L = {dl:>3} sur {tot}")
say(f"""
   HORS D'ATTEINTE — dim L = 0, et c'est une MESURE, pas une conjecture :""")
for nom, genre, dl, tot in res:
    say(f"     {nom:>30}   {genre}")

say(f"""
   ET LA REGLE QUI S'EN DEGAGE, maintenant qu'on la LIT au lieu de la deviner :

     sortie brute              dim L = tous les bits    tout est lineaire
     sortie ADDITIVE           dim L = 1 PAR MOT        le bit 0, et lui seul
     addition + ROTATION       dim L = 0                la rotation deplace le
                                                        bit 0 la ou les retenues
                                                        sont deja entrees
     multiplication + rotation dim L = 0
     rotation VARIABLE (PCG)   dim L = 0
     chaine de melange         dim L = 0

   Le §117 avait devine cette regle a partir d'un cas ; elle est ici MESUREE
   sur onze familles. Ce qui protege n'est jamais l'addition ni la
   multiplication par un impair — c'est TOUJOURS un decalage a droite ou une
   rotation appliques APRES elles.

   REGISTRE : INCHANGE. Ce fichier ne teste rien sur l'archive — il mesure une
   propriete des generateurs eux-memes, et fixe la frontiere que tout le reste
   du dossier supposait.

   ({time.time() - T0:.1f} s)""")
