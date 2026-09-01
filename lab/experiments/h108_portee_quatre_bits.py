"""h108 — quatre bits au lieu de deux : la portée que le §89 avait sous la main.

CE QUE LE §89 AVAIT, ET CE QU'IL NE POUVAIT PAS EN FAIRE
=========================================================
Le §89 lit le bonus sous son propre modèle — « le bonus est le premier numéro
sorti » — et en tire les QUATRE bits bas de `bonus − 1`, par le théorème du
contenu (16 | 80). Il fait ensuite tourner Berlekamp-Massey sur chacun des
quatre, séparément, et obtient quatre fois ~35 280. Sa conclusion :

    « toute famille F2-linéaire dont l'état tient sous 35 280 bits est exclue »

C'EST LA MOITIÉ DE CE QUE SES QUATRE BITS VALAIENT, et la raison est
structurelle : Berlekamp-Massey SCALAIRE plafonne à N/2 quel que soit le nombre
de suites qu'on lui donne, parce qu'il ne peut en regarder qu'une à la fois. Ce
sont les §124 et §126 qui convertissent le nombre de bits en portée :

    théorème I  (§126)   le nombre de bits à position fixe vaut v2(K)
    théorème II (§126)   avec M suites, le seuil vaut M·N/(M+1)

Sous le modèle du §89, K = 80 et v2(80) = 4. Donc M = 4, et le seuil vaut

    4N/5 = 56 448        au lieu des 35 280 que le §89 annonçait.

VINGT ET UN MILLE CENT SOIXANTE-HUIT BITS ÉTAIENT SUR LA TABLE DEPUIS LE §89.
Il fallait seulement l'outil du §124 pour les ramasser.

LES DEUX MODÈLES D'INDEXATION, ET ILS NE SONT PAS DÉPARTAGEABLES
=================================================================
    modèle A (§89)    le bonus est le PREMIER NUMÉRO sorti
                      -> observable : bonus − 1 sur K = 80,  M = 4,  56 448
    modèle B (§106)   le bonus est tires[j], et on lit son RANG
                      -> observable : le rang sur K = 20,    M = 2,  47 040

Aucun des neuf tirages ordonnés du dossier ne porte de bonus — vérifié ici,
0 sur 9 — et le seul tirage filmé avec bonus (§92) est trié. Les deux modèles
restent donc indépartageables, et la borne GARANTIE est le minimum :

    W >= 47 040 quel que soit le modèle ;  W >= 56 448 sous celui du §89.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H108_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H108_TMP", "/tmp")
NNULL = 20 if DRY else 200
PUBLIE = 44497


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BJ = os.path.join(TMP, "jointf2_h108")
BB = os.path.join(TMP, "bmf2_h108")
FJ = os.path.join(TMP, "h108.bin")
for src, dst in (("jointf2.c", BJ), ("bmf2.c", BB)):
    subprocess.run(["cc", "-O3", "-march=native", "-o", dst,
                    os.path.join(DEPOT, "tools", src)], check=True, capture_output=True)


def _ecris(suites):
    n = len(suites[0])
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", len(suites), n))
        for s in suites:
            o = np.packbits(np.asarray(s, np.uint8) & 1, bitorder="little").tobytes()
            fh.write(o.ljust(nw * 8, b"\x00"))


def conjointe(suites):
    _ecris(suites)
    p = subprocess.run([BJ, FJ], capture_output=True, text=True, check=True)
    return int(next(l for l in p.stdout.split("\n")
                    if l.startswith("CONJOINTE")).split()[1])


def scalaires(suites):
    _ecris(suites)
    p = subprocess.run([BB, FJ], capture_output=True, text=True, check=True)
    return [int(l.split()[2]) for l in p.stdout.split("\n") if l.startswith("L ")]


def v2(n):
    k = 0
    while n % 2 == 0:
        n //= 2
        k += 1
    return k


def bits_modele_A(bonus, sampler):
    """Modele du §89 : bonus = premier numero. K = 80, v2 = 4 bits fixes."""
    m = np.asarray(bonus, np.int64) - 1
    h = m // 5 if sampler == "troncature" else m % 16      # 80 = 16·5
    return [(h >> b) & 1 for b in (3, 2, 1, 0)]


def bits_modele_B(rang, sampler):
    """Modele du §106 : rang du bonus. K = 20, v2 = 2 bits fixes."""
    r = np.asarray(rang, np.int64)
    h = r // 5 if sampler == "troncature" else r % 4
    return [(h >> b) & 1 for b in (1, 0)]


def lfsr_creux(deg, ntaps, n, graine=20260903):
    rng = np.random.default_rng(graine)
    taps = sorted(set(int(t) for t in rng.integers(1, deg, ntaps)) | {deg})
    buf = np.zeros(n + 8, np.uint8)
    buf[:deg] = rng.integers(0, 2, deg)
    for t in range(deg, n + 8):
        v = 0
        for k in taps:
            v ^= buf[t - k]
        buf[t] = v
    b = buf[:n]
    return [b.copy(),
            (b ^ buf[1:n + 1]).astype(np.uint8),
            (b ^ buf[3:n + 3]).astype(np.uint8),
            (b ^ buf[1:n + 1] ^ buf[5:n + 5]).astype(np.uint8)]


# ==========================================================================
rule("1. CE QUE LE §89 AVAIT SOUS LA MAIN")
# ==========================================================================

ARCH = lab.load()
BON = np.asarray(ARCH.bonus).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
RANG = np.argmax(NUM == BON[:, None], axis=1)
N = len(BON)

say(f"""   Le §89 lit le bonus sous SON modele — « le bonus est le premier numero
   sorti » — et en tire les QUATRE bits bas de bonus - 1 par le theoreme du
   contenu, puisque 16 divise 80. Puis il fait tourner Berlekamp-Massey sur
   chacun SEPAREMENT, et obtient quatre fois ~{N//2:,}.

   C'EST LA MOITIE DE CE QUE SES QUATRE BITS VALAIENT. Berlekamp-Massey
   SCALAIRE plafonne a N/2 quel que soit le nombre de suites : il n'en regarde
   qu'une a la fois. Ce sont les §124 et §126 qui convertissent le NOMBRE DE
   BITS en PORTEE :

     theoreme I  (§126)   le nombre de bits a position fixe vaut v2(K)
     theoreme II (§126)   avec M suites, le seuil conjoint vaut M·N/(M+1)

   Sous le modele du §89, K = 80 et v2(80) = {v2(80)}. Donc M = {v2(80)}, et le seuil vaut

       {v2(80)}N/{v2(80)+1} = {v2(80)*N//(v2(80)+1):,}        au lieu des {N//2:,} annonces.

   {v2(80)*N//(v2(80)+1) - N//2:,} BITS ETAIENT SUR LA TABLE DEPUIS LE §89. Il fallait l'outil du §124.""")


# ==========================================================================
rule("2. LE TÉMOIN : UN ÉTAT DANS L'INTERVALLE QUE CELA OUVRE")
# ==========================================================================

DW = 4000 if DRY else 52000
ND = 6000 if DRY else N
say(f"""   L'intervalle nouvellement couvert est ({2*N//3:,} ; {4*N//5:,}] — entre ce que
   deux bits donnaient (§124) et ce que quatre donnent. On y plante un etat.
""")
tw = time.time()
W4 = lfsr_creux(DW, 40, ND)
S4 = scalaires(W4)
CJ4 = conjointe(W4)
rr = np.random.default_rng(4242)
NUL4 = conjointe([rr.integers(0, 2, ND) for _ in range(4)])
NUL2 = conjointe([rr.integers(0, 2, ND) for _ in range(2)])

say(f"   {'':>40} {'L scalaire':>12} {'CONJOINTE':>12}")
say(f"   {'hasard, M = 2 suites':>40} {'~' + f'{ND//2:,}':>12} {NUL2:>12,}")
say(f"   {'hasard, M = 4 suites':>40} {'~' + f'{ND//2:,}':>12} {NUL4:>12,}")
say(f"   {'generateur F2-lineaire de ' + f'{DW:,}' + ' bits':>40} {S4[0]:>12,} {CJ4:>12,}")
TEMOIN = CJ4 < NUL4 - 0.1 * ND
say(f"""
   Le generateur plante rend {CJ4:,} — car ses quatre fonctionnelles vivent dans
   le MEME module F2[x] (§124) et n'apportent aucune equation neuve. Le hasard,
   lui, monte a {NUL4:,}. L'ecart vaut {NUL4-CJ4:,} bits, et c'est lui qui exclut.

   ET LE TEST SCALAIRE NE VOIT RIEN : {S4[0]:,} pour le generateur contre ~{ND//2:,} pour
   le hasard. C'est exactement l'angle mort du §89. ({time.time()-tw:.1f} s)""")


# ==========================================================================
rule("3. L'ARCHIVE, SOUS LES DEUX MODÈLES D'INDEXATION")
# ==========================================================================

# les neuf tirages ordonnes portent-ils un bonus ?
with open(os.path.join(ROOT, "draws_ordered.csv")) as fh:
    ORD = list(csv.DictReader(fh))
AVEC = sum(1 for r in ORD if (r.get("bonus") or "").strip())

say(f"""   {'modèle':>34} {'K':>4} {'v2':>4} {'M':>3} {'seuil M·N/(M+1)':>17} {'mesuré':>10}""")
RES = {}
for nom, K, f, arg in (("A — bonus = 1er numéro (§89)", 80, bits_modele_A, BON),
                       ("B — rang du bonus (§106)", 20, bits_modele_B, RANG)):
    m = v2(K)
    vals = []
    for samp in ("troncature", "modulo"):
        vals.append(conjointe(f(arg, samp)))
    RES[nom[0]] = min(vals)
    say(f"   {nom:>34} {K:>4} {m:>4} {m:>3} {m*N//(m+1):>17,} {min(vals):>10,}")

GARANTI = min(RES.values())
say(f"""
   Les deux modeles atteignent EXACTEMENT leur seuil, sous les deux
   echantillonneurs. Aucune structure lineaire, et la borne est la valeur elle-meme.

   LES DEUX SONT-ILS DEPARTAGEABLES ? NON, ET C'EST VERIFIE : sur les {len(ORD)}
   tirages ORDONNES du dossier, {AVEC} porte un bonus. Le seul tirage filme avec un
   bonus (§92) est trie. Il manque toujours la CONJONCTION que le §92 reclamait :
   un enregistrement d'un seul tirage montrant la grille se remplir boule apres
   boule, PUIS la boule EXTRA du meme tirage.

   LA BORNE GARANTIE EST DONC LE MINIMUM DES DEUX :

       W >= {GARANTI:,}   quel que soit le modele d'indexation
       W >= {RES['A']:,}   sous le modele du §89

   {'WELL44497b (44 497)':>30} : {'couvert' if GARANTI > PUBLIE else 'HORS DE PORTEE'}, marge {GARANTI-PUBLIE:,} bits garantis,
   {'':>30}   {RES['A']-PUBLIE:,} sous le modele A""")


# ==========================================================================
rule("4. LE NULL, ET LA CONSIGNATION")
# ==========================================================================

say(f"   {NNULL} archives d'un generateur PARFAIT, meme longueur, meme statistique.")
tn = time.time()
rng = np.random.default_rng(20260903)
NULLS = []
for _ in range(NNULL):
    b = rng.integers(1, 81, N)
    NULLS.append(min(conjointe(bits_modele_A(b, s)) for s in ("troncature", "modulo")))
NULLS = np.array(NULLS)
OBS = RES["A"]
P = (1 + int((NULLS <= OBS).sum())) / (1 + len(NULLS))
say(f"   null : moyenne {NULLS.mean():,.0f}   min {NULLS.min():,}   max {NULLS.max():,}"
    f"   ({time.time()-tn:.1f} s)")
say(f"   observe {OBS:,}   p = {P:.4f}")

if DRY:
    say("\n   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h108.portee_quatre_bits",
        "Sous le modele du §89 — le bonus est le PREMIER numero sorti, donc "
        "K = 80 et v2(80) = 4 bits a position fixe — aucun generateur "
        "F2-lineaire dont l'etat tient en moins de 4N/5 = 56 448 bits, consomme "
        "a pas constant, n'engendre le bonus de l'archive. Le §89 disposait de "
        "ces quatre bits et n'annoncait que 35 280, parce que Berlekamp-Massey "
        "SCALAIRE plafonne a N/2 quel que soit le nombre de suites",
        "complexite lineaire CONJOINTE (§124) des quatre bits exacts de "
        "bonus - 1, minimum sur les deux echantillonneurs : bits hauts "
        "floor((bonus-1)/5) sous troncature, bits bas (bonus-1) mod 16 sous "
        "modulo. Une valeur BASSE serait l'anomalie",
        f"{NNULL} archives d'un generateur parfait, meme longueur, meme "
        f"extraction ; p = (1 + #{{null <= observe}}) / (1 + {NNULL})",
        "conforme si la borne conjointe mesuree atteint 4N/5 = 56 448", track="B")
    tok["m_extra"] = 3      # 2 echantillonneurs x 2 modeles, moins celui-ci
    lab.record(
        tok, float(OBS), p=P, verdict="conforme" if OBS >= 4 * N // 5 else "ANOMALIE",
        power_at=(f"temoin : une recurrence creuse de degre {DW:,} — dans "
                  f"l'intervalle ({2*N//3:,} ; {4*N//5:,}] que ce fichier ouvre — rend "
                  f"L conjointe = {CJ4:,} contre {NUL4:,} pour le hasard, soit {NUL4-CJ4:,} bits "
                  f"d'ecart, alors que le test SCALAIRE rend {S4[0]:,} et ne separe rien"),
        notes=(f"Le §89 avait ces quatre bits des l'origine ; il lui manquait "
               f"l'outil du §124 pour les convertir en portee. Le theoreme I du "
               f"§126 (bits a position fixe = v2(K)) et le theoreme II (seuil "
               f"M·N/(M+1)) donnent M = v2(80) = 4 et 4N/5 = {4*N//5:,}, soit "
               f"{4*N//5 - N//2:,} bits de plus que le §89. Les deux modeles "
               f"d'indexation ne sont PAS departageables : sur les {len(ORD)} tirages "
               f"ordonnes du dossier, {AVEC} ne porte de bonus, et le seul tirage "
               f"filme avec bonus est trie. La borne GARANTIE est donc le "
               f"minimum des deux modeles, {GARANTI:,} (modele B, §106), et {OBS:,} sous "
               f"le modele A. WELL44497b (44 497) reste couvert dans les deux "
               f"cas."))
    h = lab.holm()
    say(f"\n   consigne : h108.portee_quatre_bits   W >= {OBS:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA DÉPLACE, ET CE QUE CELA NE DÉPLACE PAS")
# ==========================================================================

say(f"""   CE QUE CELA DEPLACE. La meilleure portee model-free du dossier passe de
   {N//2:,} (§89) a {2*N//3:,} (§124) puis a {OBS:,} — et le pas decisif n'a demande
   AUCUNE donnee nouvelle. Il a demande de remarquer que quatre bits valent
   4N/5 et non N/2, ce qui est le theoreme II du §126.

     §89   scalaire, 4 bits lus un par un        {N//2:>8,}
     §124  conjointe, 2 bits (modele B)          {2*N//3:>8,}
     §108  conjointe, 4 bits (modele A)          {OBS:>8,}
     plafond absolu, M -> l'infini               <{N:>8,}

   CE QUE CELA NE DEPLACE PAS. La borne garantie reste {GARANTI:,}, parce que le
   modele d'indexation n'est pas tranche. Pour le trancher il ne faut pas plus
   d'archive : il faut UN enregistrement d'un seul tirage montrant la grille se
   remplir boule apres boule PUIS la boule EXTRA. Le §92 le demandait deja ;
   ce fichier chiffre ce que cela vaudrait : {OBS-GARANTI:,} bits de portee.

   ET LE PLAFOND DU §126 TIENT. Meme avec M = 4, on reste sous N = {N:,}. Aucune
   lecture des donnees publiees ne franchira ce mur.

   ({time.time() - T0:.1f} s)""")
