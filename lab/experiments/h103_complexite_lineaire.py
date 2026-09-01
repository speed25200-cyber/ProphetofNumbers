"""h103 — le théorème de la complexité linéaire universelle.

CE QUE TOUT LE DOSSIER FAIT DEPUIS LE §105, ET SA FAIBLESSE
============================================================
Du §105 au §121, la méthode est toujours la même : NOMMER une famille, écrire
ses formes F2-linéaires, résoudre, exclure. Onze mille systèmes, cinq axes de
modèle. Et trois de ces cinq axes — l'ordre de service du cache (§112), les
mots par numéro (§113), le décalage (§115) — n'ont été trouvés qu'APRÈS COUP.
Chacun faisait échouer toutes les attaques EN SILENCE.

    Une exclusion par énumération ne vaut que pour ce qui a été énuméré. Et
    l'histoire du dossier montre qu'on n'énumère jamais assez.

CE FICHIER CHANGE DE MÉTHODE : IL CALCULE UN INVARIANT.

LE THÉORÈME
============
Soit un générateur dont l'état vit dans F2^W, évolue par s -> A·s pour une
matrice A QUELCONQUE sur F2, et dont le mot rendu est w = Λ·s pour une
application F2-linéaire Λ quelconque. Soit β une forme F2-linéaire du mot.
Si la plateforme consomme ses mots aux positions d'une PROGRESSION
ARITHMÉTIQUE n_i = c + σ·i, alors la suite observée

    b_i = β(Λ · A^{c + σ i} · s)

vérifie la récurrence linéaire dont le polynôme caractéristique est le
polynôme minimal de A^σ. Ce polynôme divise le polynôme caractéristique de
A^σ, de degré W. DONC :

    L(b) <= W,

où L est la complexité linéaire — et Berlekamp-Massey rend EXACTEMENT L pour
la suite finie observée.

CE QUE CETTE SEULE INÉGALITÉ REMPLACE
======================================
Le membre de droite ne contient ni A, ni Λ, ni β, ni σ, ni c. Un seul nombre
teste donc, simultanément :

    — toute matrice de transition, donc TOUTE famille F2-linéaire, y compris
      celles que personne n'a publiées et celles que je n'ai pas su nommer ;
    — tout pas σ constant : le §115 a passé 5 126 systèmes à balayer un
      décalage, ici c'est gratuit ;
    — tout décalage c, tout nombre de mots par numéro (§113), toute position
      du mot d'indice dans le bloc ;
    — les deux échantillonneurs, en lisant les bits HAUTS (troncature) ou les
      bits BAS (modulo) du même rang.

COROLLAIRE : PRÉDIRE SANS IDENTIFIER
=====================================
Si L est petit, Berlekamp-Massey rend la récurrence elle-même, et tout bit
suivant se calcule à partir des L derniers — sans jamais savoir de quelle
famille il s'agit, ni quel est le pas, ni quel est l'échantillonneur.
L'IDENTIFICATION DE LA FAMILLE N'EST PAS NÉCESSAIRE À LA PRÉDICTION. C'est la
seule voie du dossier qui prédise sans reconstituer.

LE PPCM : DOUBLER LA PORTÉE SANS UN BIT DE PLUS
================================================
Le rang du bonus donne DEUX bits exacts par tirage, pas un (voir plus bas).
Les polynômes minimaux f et f' des deux suites divisent tous deux le polynôme
caractéristique de A^σ. Donc leur ppcm le divise aussi :

    W >= deg ppcm(f, f') = L + L' - deg pgcd(f, f').

Sur un vrai générateur à polynôme caractéristique irréductible — MT19937 —
f = f' et la borne rend exactement W. Sur du hasard, f et f' sont premiers
entre eux et la borne vaut ~N au lieu de ~N/2 : LA PORTÉE DOUBLE.

DEUX BITS EXACTS, TOUJOURS, ET POURQUOI
========================================
Le §106 mesurait 3,20 bits en moyenne par rang de bonus, un nombre variable
selon le rang. Ici il faut un bit à POSITION FIXE, sinon la suite n'est plus
la trace d'une seule forme linéaire. Or :

    4 divise 20.

Sous TRONCATURE, m = floor(20u) donne 4u dans [m/5, (m+1)/5), intervalle de
longueur 1/5 qui ne contient un entier que si m/5 en est un. Donc floor(4u) =
floor(m/5) SANS EXCEPTION : les deux bits de poids fort du mot sont exacts sur
les 70 560 tirages, pas seulement sur une partie.

Sous MODULO, m = w mod 20, et 4 | 20 | 2^W donne w mod 4 = m mod 4 : les deux
bits de poids FAIBLE, exacts eux aussi. C'est le théorème du contenu du §94
réduit à K = 20.

LA LIMITE, ÉNONCÉE FRANCHEMENT
===============================
1. Le théorème exige un pas CONSTANT. Sous rejet le nombre de mots consommés
   varie et n_i cesse d'être arithmétique — c'est exactement ce que le §111
   disait déjà.
2. Il exige que le bit observé soit une forme F2-LINÉAIRE. Les familles à
   sortie brouillée — xoshiro**, PCG32, splitmix64 — ont dim L = 0 au §119 :
   aucun bit ne l'est. Le §119 les ferme, celui-ci ferme les autres.
3. Il hérite de la réserve du §106 : le rang est calculé dans le tableau TRIÉ.
   Si la plateforme indexe le tableau dans l'ORDRE D'ÉMISSION, le rang observé
   est une permutation aléatoire du vrai indice, et un L de ~N/2 exclut le
   COUPLE, pas le générateur seul.

Il TESTE l'archive : il consigne au registre.
"""

import os
import random
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H103_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H103_TMP", "/tmp")
NNULL = 20 if DRY else 200
KB = 20                                   # le rang du bonus vit dans 0..19
CACHE = 64                                # le bloc de V8, §112
PUBLIE = 44497                            # WELL44497b : le plus grand état publié


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "bmf2_h103")
FICH = os.path.join(TMP, "bmf2_h103.bin")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "bmf2.c")],
               check=True, capture_output=True)


def bm(suites):
    """Berlekamp-Massey sur chaque suite, puis le ppcm de chaque paire."""
    n = len(suites[0])
    nw = (n + 63) // 64
    with open(FICH, "wb") as fh:
        fh.write(struct.pack("<ii", len(suites), n))
        for s in suites:
            octets = np.packbits(np.asarray(s, np.uint8) & 1,
                                 bitorder="little").tobytes()
            fh.write(octets.ljust(nw * 8, b"\x00"))
    p = subprocess.run([BIN, FICH], capture_output=True, text=True, check=True)
    L, PP = {}, {}
    for ligne in p.stdout.split("\n"):
        t = ligne.split()
        if t[:1] == ["L"]:
            L[int(t[1])] = int(t[2])
        elif t[:1] == ["PPCM"]:
            PP[(int(t[1]), int(t[2]))] = int(t[4].split("=")[1])
    return L, PP


def bits_de(rangs, sampler):
    """Les DEUX bits exacts du mot, à position fixe, pour les deux samplers.

    Rendus du plus fort au plus faible :
      troncature : [bit 1 du mot, bit 2 du mot]   — floor(4u) = floor(m/5)
      modulo     : [bit 1 du mot, bit 0 du mot]   — w mod 4 = m mod 4
    """
    r = np.asarray(rangs, np.int64)
    if sampler == "troncature":
        h = r // 5                        # = floor(4u), les deux bits HAUTS
        return [(h >> 1) & 1, h & 1]
    q = r & 3                             # = w mod 4, les deux bits BAS
    return [(q >> 1) & 1, q & 1]


# ==========================================================================
rule("1. LE THÉORÈME, ET CE QU'IL REMPLACE")
# ==========================================================================

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Si l'etat evolue par s -> A·s sur F2^W et que le mot est une fonction
   F2-LINEAIRE de l'etat, alors tout bit lu aux positions c + σi verifie une
   recurrence lineaire de degre <= W :

       L(b)  <=  W       pour TOUT A, TOUT Λ, TOUT β, TOUT σ, TOUT c.

   Le membre de droite ne contient plus le modele. Un seul nombre teste donc
   toute famille F2-lineaire, tout pas, tout decalage, tout nombre de mots par
   numero — et les deux echantillonneurs, en lisant les bits HAUTS ou BAS.

   DEUX BITS EXACTS PAR TIRAGE, ET NON 3,20 EN MOYENNE. Le §106 comptait un
   nombre de bits qui DEPEND du rang ; il faut ici une position FIXE. Comme
   4 divise 20 :
     troncature : floor(4u) = floor(m/5), les deux bits de poids FORT, exacts
                  sur les 70 560 tirages sans exception ;
     modulo     : w mod 4 = m mod 4, les deux bits de poids FAIBLE.

   LE PPCM. Les polynomes minimaux des deux suites divisent tous deux le
   polynome caracteristique de A^σ, donc W >= deg ppcm(f, f'). Sur un vrai
   generateur irreductible f = f' et la borne rend W exactement ; sur du
   hasard les deux sont premiers entre eux et la borne vaut ~N. La portee
   DOUBLE sans un bit de plus.

   `tools/bmf2.c` autotest : {AUTO}""")
for l in st.stdout.strip().split("\n")[:-1]:
    say("     " + l.strip())


# ==========================================================================
rule("2. LES TÉMOINS : RETROUVER LA LARGEUR D'ÉTAT SANS NOMMER LA FAMILLE")
# ==========================================================================

# Le catalogue du §68 et du §86, repris SANS ETRE RECOPIE : c'est la tete de
# h61 qui definit les `step`, et h86 qui fixe la largeur du MOT rendu.
_SRC = open(os.path.join(ICI, "h61_familles_etendues.py"), encoding="utf-8").read()
_G = {"__name__": "h61tete", "__file__": os.path.join(ICI, "h61_familles_etendues.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LES FAMILLES')], "h61tete", "exec"), _G)
FAMILLES = _G["OLD"] + _G["NEW"]
LARGEUR = {"xorshift32": 32, "xorshift64": 64, "xorshift96": 32,
           "xorshift128": 32, "taus88": 32, "xoroshiro128 (brut)": 64,
           "xoshiro128 (brut)": 32, "xoshiro256 (brut)": 64,
           "LFSR113": 32, "WELL512a": 32}


def rangs_famille(step, etat, W, nd, stride, off, sampler):
    """Le rang du bonus, tirage apres tirage, sous le modele « stride mots par
    tirage, le mot d'indice au decalage off »."""
    out = []
    s = etat
    for i in range(nd):
        for k in range(stride):
            s, w = step(s)
            if k == off:
                out.append((w * KB) >> W if sampler == "troncature" else w % KB)
    return out


def rangs_mt(graine, nd, stride, off, sampler):
    r = random.Random(graine)
    out = []
    for i in range(nd):
        for k in range(stride):
            w = r.getrandbits(32)
            if k == off:
                out.append((w * KB) >> 32 if sampler == "troncature" else w % KB)
    return out


say(f"""   Pour chaque famille on fabrique le rang du bonus sous le modele « 20 mots
   de Fisher-Yates + 1 mot d'indice », soit un pas de 21 et un decalage de 20 —
   PUIS ON L'OUBLIE. Berlekamp-Massey ne recoit que la suite de bits. Il doit
   rendre une borne <= la largeur de l'etat.

   {'famille':>22} {'état':>7} {'tirages':>8} {'L(b1)':>7} {'L(b2)':>7} {'ppcm':>7} {'verdict':>9}""")

TEM = []
for nom, nbits, step, _ref in FAMILLES:
    W = LARGEUR[nom]
    nd = max(600, 4 * nbits)
    etat = 0
    g = random.Random(20260901 + nbits)
    while etat == 0:
        etat = g.getrandbits(nbits)
    rg = rangs_famille(step, etat, W, nd, 21, 20, "troncature")
    L, PP = bm(bits_de(rg, "troncature"))
    pp = PP[(0, 1)]
    ok = pp <= nbits
    TEM.append(ok)
    say(f"   {nom:>22} {nbits:>7} {nd:>8} {L[0]:>7} {L[1]:>7} {pp:>7} "
        f"{'OK' if ok else 'ECHEC':>9}")

# MT19937 : 19 937 bits, la plus grosse cible du dossier (§114)
ND_MT = 3000 if DRY else 45000
rg = rangs_mt(20260901, ND_MT, 21, 20, "troncature")
L, PP = bm(bits_de(rg, "troncature"))
PP_MT = PP[(0, 1)]
# Le polynome caracteristique de MT19937 est PRIMITIF, donc irreductible : les
# deux suites ont le MEME polynome minimal, le pgcd vaut tout, et le ppcm rend
# exactement 19 937. Il y faut 2 x 19 937 tirages : le mode d'essai n'en a pas
# assez, et il rend alors N/2 comme du hasard — ce qui est correct aussi.
ok_mt = (PP_MT == 19937) if not DRY else (PP_MT <= 19937)
TEM.append(ok_mt)
say(f"   {'MT19937':>22} {19937:>7} {ND_MT:>8} {L[0]:>7} {L[1]:>7} {PP_MT:>7} "
    f"{'OK' if ok_mt else 'ECHEC':>9}")

# le null : un generateur parfait
rgn = np.random.default_rng(7).integers(0, KB, 70560)
Ln, PPn = bm(bits_de(rgn, "troncature"))
say(f"   {'(générateur parfait)':>22} {'—':>7} {70560:>8} {Ln[0]:>7} {Ln[1]:>7} "
    f"{PPn[(0,1)]:>7} {'~N':>9}")

say(f"""
   {sum(TEM)}/{len(TEM)} familles rendent une borne inferieure a leur etat, MT19937 compris —
   et le generateur parfait rend {PPn[(0,1)]:,}, soit ~N. Le test SEPARE.""")


# ==========================================================================
rule("3. L'INVARIANCE MESURÉE, ET NON AFFIRMÉE")
# ==========================================================================

say("""   Le theoreme dit que le pas et le decalage n'entrent pas dans la borne. Le
   §115 a coute 5 126 systemes pour balayer le seul decalage : on verifie donc
   que c'est bien gratuit ici, plutot que de le croire.
""")
NOMI = "WELL512a" if "WELL512a" in LARGEUR else FAMILLES[0][0]
fam = [f for f in FAMILLES if f[0] == NOMI][0]
say(f"   {NOMI} — etat {fam[1]} bits\n")
say(f"   {'pas σ':>7} {'décalage c':>11} {'mots/numéro':>12} {'ppcm':>7}")
INV = []
for stride, off, mpn in [(21, 20, 1), (21, 0, 1), (22, 7, 1), (37, 3, 1),
                         (41, 40, 2), (43, 11, 1)]:
    rg = rangs_famille(fam[2], 0x1234567 | (1 << (fam[1] - 1)), LARGEUR[NOMI],
                       max(600, 4 * fam[1]), stride, off, "troncature")
    _L, _PP = bm(bits_de(rg, "troncature"))
    INV.append(_PP[(0, 1)])
    say(f"   {stride:>7} {off:>11} {mpn:>12} {_PP[(0,1)]:>7}")
say(f"""
   Six modeles de consommation, une seule borne : {max(INV)} au plus, pour un etat
   de {fam[1]}. Les axes 2, 3 et 5 du §121 sont neutralises par construction.""")


# ==========================================================================
rule("4. L'ARCHIVE : 70 560 TIRAGES, DEUX HYPOTHÈSES D'ÉCHANTILLONNEUR")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1)
N = len(RANG)
assert (NUM == BON[:, None]).any(1).all(), "bonus hors des vingt tires"

say(f"""   Le bonus est l'un des vingt numeros tires dans les {N:,} cas. Son rang dans
   le tableau TRIE vaut donc floor(20u) sous troncature, et w mod 20 sous
   modulo. On en tire les deux bits exacts, et on les donne a Berlekamp-Massey
   sans rien lui dire d'autre.

   {'hypothèse':>14} {'bits lus':>16} {'L(f)':>9} {"L(f')":>9} {'pgcd':>6} {'W >= ppcm':>11}""")
REEL, LREEL = {}, {}
for samp, quels in (("troncature", "bits 1 et 2 hauts"), ("modulo", "bits 1 et 0 bas")):
    L, PP = bm(bits_de(RANG, samp))
    pp = PP[(0, 1)]
    REEL[samp] = pp
    LREEL[samp] = (L[0], L[1])
    say(f"   {samp:>14} {quels:>16} {L[0]:>9,} {L[1]:>9,} {L[0]+L[1]-pp:>6} {pp:>11,}")

BORNE = min(REEL.values())
say(f"""
   BORNE MESUREE : W >= {BORNE:,}.

   Aucun generateur F2-lineaire d'etat inferieur a {BORNE:,} bits, consomme a pas
   constant, n'engendre les rangs du bonus de l'archive. La liste de ce que
   cela couvre n'est pas une liste de familles — c'est une INEGALITE :

     xorshift 32/64/96/128    32-128     couvert
     taus88, LFSR113          88-113     couvert
     xoshiro/xoroshiro bruts  128-256    couvert
     WELL512a, WELL1024a      512-1024   couvert
     MT19937, WELL19937       19 937     couvert
     WELL44497b               44 497     {'couvert' if BORNE >= PUBLIE else 'HORS DE PORTEE'}
     tout le reste < {BORNE:,}      couvert, nomme ou non""")


# ==========================================================================
rule("4 bis. LE COROLLAIRE ARITHMÉTIQUE : LES RÉCURRENCES ENTIÈRES MOD 2^e")
# ==========================================================================

L0 = LREEL["modulo"][1]                   # le bit 0 du mot, sous modulo
say(f"""   Le theoreme est ecrit sur F2, et le §104 a du batir une reduction de reseau
   pour les generateurs ENTIERS. Or une partie d'entre eux retombe dans le
   meme test, et gratuitement.

   Soit une recurrence entiere a r termes et a module une PUISSANCE DE DEUX :

       x_t  =  a_1 x_{{t-1}} + ... + a_r x_{{t-r}} + b   (mod 2^e).

   Reduite modulo 2, elle devient une recurrence AFFINE d'ordre r sur F2. Une
   recurrence affine se rend homogene en multipliant son polynome par (1 + x) :

       L(bit 0)  <=  r + 1.

   Et la decimation par un pas σ ne change pas cette borne : les racines du
   polynome caracteristique sont elevees a la puissance σ, son degre ne bouge
   pas. Le bit 0 est justement ce que l'echantillonneur MODULO publie, puisque
   4 divise 20.

     LCG mod 2^e (ANSI C, MMIX, Borland)      r = 1    ->  L <= 2
     Fibonacci additif retarde mod 2^e        r = 31   ->  L <= 31
     (la recurrence de `random()` de la glibc : r[i-3] + r[i-31])
""")


def rangs_lcg(nd, stride, off):
    x, out = 20260901, []
    for i in range(nd):
        for k in range(stride):
            x = (1103515245 * x + 12345) & 0xFFFFFFFF
            if k == off:
                out.append(x % KB)
    return out


def rangs_lfg(nd, stride, off):
    g = random.Random(20260901)
    r = [g.getrandbits(32) for _ in range(31)]
    out, i = [], 0
    for d in range(nd):
        for k in range(stride):
            v = (r[(i - 3) % 31] + r[(i - 31) % 31]) & 0xFFFFFFFF
            r[i % 31] = v
            i += 1
            if k == off:
                out.append(v % KB)
    return out


say(f"   {'témoin (mot = état entier)':>30} {'ordre r':>9} {'L(bit 0)':>10} {'attendu':>10}")
TA = []
for nom, rg, borne in (("LCG mod 2^32", rangs_lcg(2000, 21, 20), 2),
                       ("Fibonacci additif mod 2^32", rangs_lfg(2000, 21, 20), 31)):
    Lb = bm([np.asarray(rg, np.int64) & 1])[0][0]
    TA.append(Lb <= borne)
    say(f"   {nom:>30} {borne if borne > 2 else 1:>9} {Lb:>10} {'<= ' + str(borne):>10}")

say(f"""
   MESURE SUR L'ARCHIVE : L(bit 0) = {L0:,}.

   Toute recurrence entiere de module 2^e et d'ordre inferieur a {L0:,} termes est
   donc exclue, pourvu que le mot publie porte le bit 0 de l'etat.

   CE QUE LE COROLLAIRE NE PREND PAS, ET IL FAUT LE DIRE :
     — les modules PREMIERS (Lehmer 2^31-1, MWC dont le module vaut a·b-1,
       impair au §102) : la reduction modulo 2 n'a plus de sens ;
     — les implantations qui ne rendent que les bits HAUTS — Java `next(bits)`,
       PCG, et `random()` de la glibc qui decale d'un bit et jette justement le
       bit 0. Le bit 0 du MOT n'est alors plus le bit 0 de l'ETAT, et la
       retenue de l'addition brise la linearite des le bit 1.
   Pour ces deux cas c'est la reduction de reseau du §104 qui reste l'outil.""")


# ==========================================================================
rule("5. L'AXE DU CACHE : LE SEUL QUI CASSE LA PROGRESSION ARITHMÉTIQUE")
# ==========================================================================

say(f"""   Le §112 a montre que V8 remplit son cache par 64 en avant et le consomme a
   REBOURS : g(j) = 64·(j//64) + 63 - (j mod 64). Les positions consommees ne
   sont alors plus arithmetiques, et le theoreme ne s'applique plus tel quel.

   IL S'APPLIQUE A CHAQUE CLASSE MODULO 64. Car j_{{i+64}} = j_i + 64σ laisse
   (j mod 64) INCHANGE et augmente j//64 de σ : donc g(j_{{i+64}}) = g(j_i) + 64σ.
   La sous-suite prise un tirage sur 64 est de nouveau arithmetique.

   Prix a payer : {N // CACHE:,} bits par classe au lieu de {N:,}, donc une portee de
   ~{N // CACHE:,} bits d'etat au lieu de ~{N:,}.
""")
DEC = []
for samp in ("troncature", "modulo"):
    b1, b2 = bits_de(RANG, samp)
    pires = []
    for r in range(CACHE):
        L, PP = bm([b1[r::CACHE], b2[r::CACHE]])
        pires.append(PP[(0, 1)])
    DEC.append((samp, min(pires), max(pires), float(np.mean(pires))))
    say(f"   {samp:>14} : ppcm minimal sur les 64 classes = {min(pires):,}  "
        f"(max {max(pires):,}, moyenne {np.mean(pires):.0f})")
BORNE_C = min(d[1] for d in DEC)
say(f"""
   BORNE SOUS CACHE RENVERSE : W >= {BORNE_C:,}. Cela couvre xorshift128 — donc le
   `Math.random` de V8 lui-meme, {128} bits, le cas qui a motive le §112 — ainsi
   que WELL512a. Au-dela il faudrait plus de tirages.""")


# ==========================================================================
rule("6. LE NULL, ET LA CONSIGNATION")
# ==========================================================================

say(f"""   {NNULL} archives d'un generateur PARFAIT, meme longueur, meme extraction, et
   la MEME statistique : le minimum du ppcm sur les deux echantillonneurs.""")
tn = time.time()
rng = np.random.default_rng(20260901)
NULLS = []
for k in range(NNULL):
    rg = rng.integers(0, KB, N)
    NULLS.append(min(bm(bits_de(rg, s))[1][(0, 1)] for s in ("troncature", "modulo")))
NULLS = np.array(NULLS)
P = (1 + int((NULLS <= BORNE).sum())) / (1 + len(NULLS))
say(f"   null : moyenne {NULLS.mean():,.0f}   min {NULLS.min():,}   max {NULLS.max():,}"
    f"   ({time.time()-tn:.1f} s)")
say(f"   observe {BORNE:,}   p = {P:.4f}")

if DRY:
    say("\n   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h103.complexite_lineaire",
        "Aucun generateur F2-lineaire dont l'etat tient en moins de 44 497 bits "
        "— la plus grande largeur publiee, celle de WELL44497b — n'engendre les "
        "rangs du bonus de l'archive, sous aucun pas constant, aucun decalage, "
        "aucun nombre de mots par numero et aucun des deux echantillonneurs",
        "borne inferieure sur la largeur d'etat W = min sur les deux "
        "echantillonneurs de deg ppcm(f, f'), ou f et f' sont les polynomes "
        "minimaux rendus par Berlekamp-Massey sur les DEUX bits exacts du rang "
        "du bonus (bits hauts sous troncature, bits bas sous modulo) des "
        "70 560 tirages. Une valeur BASSE serait l'anomalie",
        f"{NNULL} archives d'un generateur parfait, meme longueur, meme "
        f"extraction ; p = (1 + #{{null <= observe}}) / (1 + {NNULL})",
        "conforme si la borne mesuree depasse 44 497", track="B")
    tok["m_extra"] = 65          # 2 ppcm pleins + 64 classes de cache, moins celui-ci
    lab.record(
        tok, float(BORNE), p=P, verdict="conforme" if BORNE >= PUBLIE else "ANOMALIE",
        power_at=(f"temoins : {sum(TEM)}/{len(TEM)} familles F2-lineaires rendent "
                  f"une borne inferieure ou egale a leur largeur d'etat, MT19937 "
                  f"retrouve a 19 937 EXACTEMENT depuis 45 000 rangs de bonus, "
                  f"sans qu'aucune famille soit nommee au solveur ; "
                  f"{sum(TA)}/{len(TA)} temoins du corollaire arithmetique ; "
                  f"autotest de l'outil : {AUTO}"),
        notes=(f"Le dossier procedait par ENUMERATION depuis le §105, et trois "
               f"des cinq axes du modele de consommation n'ont ete trouves "
               f"qu'apres coup, chacun faisant echouer les attaques en silence. "
               f"Ce test calcule un INVARIANT : L(b) <= W pour toute matrice de "
               f"transition, toute sortie lineaire, tout pas constant et tout "
               f"decalage. Il ne nomme aucune famille et les couvre toutes. "
               f"Bornes mesurees : troncature {REEL['troncature']:,}, modulo "
               f"{REEL['modulo']:,}. Sous l'ordre de service renverse du cache "
               f"V8 (§112) le theoreme ne vaut que par classe modulo 64 et la "
               f"portee tombe a {BORNE_C:,} bits — ce qui couvre encore les 128 "
               f"bits du Math.random de V8. Reserves : le pas doit etre "
               f"CONSTANT, donc le rejet echappe (§111) ; le bit doit etre une "
               f"forme F2-lineaire, donc les sorties brouillees echappent — "
               f"mais le §119 les ferme par dim L = 0 ; et le rang est lu dans "
               f"le tableau TRIE (reserve du §106)."))
    h = lab.holm()
    say(f"\n   consigne : h103.complexite_lineaire   W >= {BORNE:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("7. CE QUE CELA CHANGE, ET CE QU'IL FAUDRAIT POUR ALLER PLUS LOIN")
# ==========================================================================

say(f"""   CE QUE CELA CHANGE. Les §105 a §121 excluaient des familles NOMMEES, une
   par une, et chaque axe de modele oublie rouvrait tout. Ici l'exclusion
   porte sur une INEGALITE : W >= {BORNE:,}. Elle ne s'ecrit pas plus longtemps si
   l'on ajoute une famille, et aucun axe de consommation a pas constant ne la
   remet en cause. C'est la premiere borne du dossier qui ne se perime pas.

   CE QU'ELLE NE COUVRE PAS, ET C'EST DIT DANS LE JETON :
     — le rejet, ou le pas varie (§111) ;
     — les sorties brouillees, ou aucun bit n'est lineaire — le §119 les ferme
       autrement, par dim L = 0 ;
     — l'indexation dans l'ORDRE D'EMISSION plutot que dans le tableau trie,
       reserve heritee du §106.

   CE QU'IL FAUDRAIT POUR ALLER PLUS LOIN. La portee est de ~N bits d'etat pour
   N tirages, soit {BORNE:,} aujourd'hui. Un etat plus large que cela demande plus
   de tirages, dans un rapport de un pour un — et rien d'autre. Aucune autre
   borne du dossier n'a une pente aussi simple.

   ET LE COROLLAIRE QUI COMPTE. Si un jour la borne s'effondre — L petit — la
   recurrence rendue par Berlekamp-Massey predit tous les bits suivants sans
   qu'on ait identifie quoi que ce soit. Ce fichier est donc a la fois le test
   le plus general du dossier et son seul predicteur sans reconstitution.

   ({time.time() - T0:.1f} s)""")
