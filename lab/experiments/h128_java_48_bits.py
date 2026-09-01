"""h128 — les 281 474 976 710 656 états de `java.util.Random`, balayés en 2^21.

CE QUE LES BALAYAGES NE COUVRAIENT PAS
=======================================
Le §120 balaie 2^32 GRAINES et le §121 les millisecondes. Cela couvre
`new Random(k)` pour k petit — un identifiant, un horodatage. Cela NE COUVRE PAS
`new Random()` SANS ARGUMENT, qui amorce l'état sur `nanoTime ^ 0x5DEECE66D` :
l'état est alors un entier LIBRE de 48 bits, et 2^48 = 2,8·10^14 est hors de
portée d'une énumération.

    C'est pourtant la façon dont on écrit `new Random()` neuf fois sur dix.

LA STRUCTURE QUI REND LE BALAYAGE POSSIBLE
===========================================
`java.util.Random` est un LCG de module 2^48 :

    s <- (0x5DEECE66D · s + 0xB) mod 2^48,     next(31) = s >>> 17

et `nextInt(80)`, le module 80 n'étant pas une puissance de deux, rend
`next(31) mod 80`. Or

    80 = 16 · 5,   donc   (v − 1) mod 16 = (s >>> 17) mod 16 = LES BITS 17 À 20.

Ces quatre bits ne dépendent que de `s mod 2^21`. Et — c'est là tout — le LCG
mod 2^21 est AUTONOME : `s mod 2^21` évolue sans jamais consulter les bits
hauts.

    ON PEUT DONC CRIBLER LES 2^21 BITS BAS SANS RIEN SAVOIR DES 27 AUTRES.

CE QUE L'ARCHIVE DONNE À CE CRIBLE
===================================
À l'étape 0 de Fisher-Yates le tableau est encore l'identité, donc la valeur
émise vaut j_0 + 1 et elle appartient à l'ensemble publié (§141). Pour chaque
tirage on exige donc

    (s >>> 17) mod 16  ∈  { (v − 1) mod 16 : v ∈ S }

Ce résidu couvre en moyenne 12,8 des 16 classes, soit un filtre de 0,8 par
tirage — faible, mais l'archive en publie 70 560 : cent tirages suffisent à
ramener 2 097 152 candidats à zéro.

    UN CRIBLE DE 2^21 EXCLUT DONC UN ESPACE D'ÉTAT DE 2^48.

TÉMOIN
=======
Un état de 48 bits planté est cherché par le même crible. Il doit SURVIVRE, et
être le seul ou presque ; puis on relève les 27 bits hauts et on exige que
l'état complet REJOUE le tirage.

Il TESTE l'archive : il consigne au registre.
"""

import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H128_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
A, C = 0x5DEECE66D, 0xB
M48, M21 = (1 << 48) - 1, (1 << 21) - 1
POOL, DRAWN = 80, 20
STRIDES = (20, 21, 22) if DRY else (20, 21, 22, 23, 24)


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def tirage_java(s, stride):
    """Un tirage a la java : Fisher-Yates partiel avec nextInt(80-k)."""
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        s = (A * s + C) & M48
        j = k + ((s >> 17) % (POOL - k))
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    for _ in range(stride - DRAWN):
        s = (A * s + C) & M48
    return s, sorted(out)


def crible(ensembles, stride, nmax=None):
    """Rend les valeurs de `s mod 2^21` compatibles avec les ensembles.

    Le LCG mod 2^21 etant AUTONOME, on fait evoluer une copie de chaque
    candidat et on garde l'indice d'origine."""
    orig = np.arange(1 << 21, dtype=np.uint64)
    cour = orig.copy()
    aa, cc, mm = np.uint64(A & M21), np.uint64(C), np.uint64(M21)
    hist = []
    for i, S in enumerate(ensembles if nmax is None else ensembles[:nmax]):
        cour = (aa * cour + cc) & mm                 # le mot 0 du tirage
        b = (cour >> np.uint64(17)) & np.uint64(15)
        ok = np.zeros(16, bool)
        for v in S:
            ok[(v - 1) % 16] = True
        garde = ok[b]
        orig, cour = orig[garde], cour[garde]
        for _ in range(stride - 1):                  # les autres mots
            cour = (aa * cour + cc) & mm
        hist.append(len(orig))
        if len(orig) == 0:
            break
    return orig, hist


BINL = os.path.join(os.environ.get("H128_TMP", "/tmp"), "java_lift_h128")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BINL,
                os.path.join(DEPOT, "tools", "java_lift.c")],
               check=True, capture_output=True)
ENVL = dict(os.environ, SWEEP_THREADS=os.environ.get("SWEEP_THREADS", "4"))


def releve(bas, ensembles, stride):
    """Releve les 27 bits hauts par `tools/java_lift.c` : pour chaque candidat
    bas, les 134 217 728 hauts sont essayes et l'etat complet doit produire
    l'ENSEMBLE des vingt numeros. Filtre 1/C(80,20), donc l'esperance de faux
    positifs sur 2^27 vaut 3,8e-11."""
    trouves = []
    for b in bas:
        p = subprocess.run([BINL, str(int(b)), str(stride)]
                           + [str(n) for n in ensembles[0]],
                           capture_output=True, text=True, timeout=1800, env=ENVL)
        for l in p.stdout.split("\n"):
            if l.startswith("TROUVE"):
                trouves.append(int(l.split("=")[1]))
    return trouves


# ==========================================================================
rule("1. CE QUE LES BALAYAGES NE COUVRAIENT PAS")
# ==========================================================================

say("""   Le §120 balaie 2^32 GRAINES, le §121 les millisecondes. Cela couvre
   `new Random(k)` pour k petit — un identifiant, un horodatage. Cela NE COUVRE
   PAS `new Random()` SANS ARGUMENT, qui amorce l'etat sur nanoTime ^ 0x5DEECE66D :
   l'etat est alors un entier LIBRE de 48 bits.

     2^48 = 281 474 976 710 656 — hors de portee d'une enumeration. Et c'est
     pourtant ainsi qu'on ecrit `new Random()` neuf fois sur dix.

   LA STRUCTURE QUI REND LE BALAYAGE POSSIBLE. java.util.Random est un LCG de
   module 2^48, avec next(31) = s >>> 17, et nextInt(80) rend next(31) mod 80.
   Or 80 = 16 x 5, donc

       (v - 1) mod 16 = (s >>> 17) mod 16 = LES BITS 17 A 20 DE L'ETAT,

   qui ne dependent que de s mod 2^21. Et le LCG mod 2^21 est AUTONOME : les
   bits bas evoluent sans jamais consulter les 27 bits hauts.

     ON CRIBLE DONC 2^21 SANS RIEN SAVOIR DES 27 AUTRES BITS.""")


# ==========================================================================
rule("2. TÉMOIN : UN ÉTAT DE 48 BITS PLANTÉ, RETROUVÉ PAR LE CRIBLE")
# ==========================================================================

rng = np.random.default_rng(20260901)
OKT, LIGT = 0, []
NT = 2 if DRY else 3
for essai in range(NT):
    vrai = int(rng.integers(0, 1 << 48))
    st = 21
    s, ens = vrai, []
    for _ in range(140):
        s, d = tirage_java(s, st)
        ens.append(d)
    bas, hist = crible(ens, st)
    present = (vrai & M21) in set(int(x) for x in bas)
    rel = releve(bas, ens, st) if len(bas) <= 4 else []
    exact = vrai in rel
    OKT += present and exact
    LIGT.append((vrai, len(bas), present, exact, hist))
    say(f"   essai {essai+1} : crible {2**21:,} -> {len(bas)} candidat(s) bas, "
        f"vrai present {'OUI' if present else 'NON'}, "
        f"etat complet releve {'OUI' if exact else 'non'}")
    say(f"     decroissance : {hist[:10]} ...")

say(f"""
   {OKT}/{NT} etats de 48 bits retrouves — cribles sur 2^21 puis releves sur 2^27.

     LE CRIBLE FAIT DONC CE QU'IL PROMET : il ramene 2 097 152 candidats a une
     poignee, et le relevement rend l'etat COMPLET.""")


# ==========================================================================
rule("3. L'ARCHIVE")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
coupe = np.flatnonzero(np.diff(TS) != 300)
deb = np.r_[0, coupe + 1]
fin = np.r_[coupe + 1, len(TS)]
k = int(np.argmax(fin - deb))
NJ = min(150, int(fin[k] - deb[k]))
ENS = [NUM[deb[k] + i].tolist() for i in range(NJ)]

say(f"""   {NJ} tirages CONSECUTIFS d'une meme journee, identifiants {IDS[deb[k]]} a
   {IDS[deb[k]+NJ-1]}. Le residu (v-1) mod 16 couvre en moyenne 12,8 des 16
   classes, soit un filtre de 0,8 par tirage — faible, mais cent tirages
   ramenent 2 097 152 candidats a zero.

   Le pas est balaye, puisqu'on ne le suppose pas.

       {'pas':>5} {'candidats bas restants':>24} {'décroissance':>34}""")

TOT, LIGA = 0, []
for st in STRIDES:
    bas, hist = crible(ENS, st)
    TOT += len(bas)
    LIGA.append((st, len(bas), hist))
    say(f"   {st:>5} {len(bas):>24,} {str(hist[:6])[:34]:>34}")

REL = []
for st, nb, _ in LIGA:
    if nb and nb <= 64:
        bas, _ = crible(ENS, st)
        REL += [(st, s) for s in releve(bas, ENS, st)]

say(f"""
   {TOT} candidat bas survivant, {len(REL)} etat complet apres relevement.""")
for st, s in REL:
    say(f"     !! pas {st} : etat = {s}")
if not REL:
    say(f"""     AUCUN. Les 281 474 976 710 656 etats de java.util.Random sont donc
     exclus sur l'archive, POUR CHACUN des pas {list(STRIDES)} — et sans que
     l'amorcage soit suppose, puisque l'etat est libre.

   CE QUE CELA AJOUTE AUX §120 ET §121. Eux couvraient `new Random(k)` pour k
   inferieur a 2^32, c'est-a-dire une graine NOMMEE. Celui-ci couvre
   `new Random()` tout court — l'amorcage par l'horloge, qui est le cas normal.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h128.java_48_bits",
        "Aucun des 281 474 976 710 656 etats de java.util.Random n'engendre les "
        "tirages de l'archive, pour aucun des pas 20 a 24. L'attaque n'enumere "
        "pas 2^48 : elle crible les 2^21 bits BAS, ce que rend possible le fait "
        "que 80 = 16 x 5 — donc (v-1) mod 16 vaut les bits 17 a 20 de l'etat — "
        "et que le LCG de module 2^48 soit AUTONOME modulo 2^21. C'est le cas "
        "que les §120 et §121 ne couvraient pas : `new Random()` sans argument, "
        "amorce sur l'horloge, dont l'etat est un entier LIBRE de 48 bits",
        "nombre d'etats complets de 48 bits compatibles, obtenus en criblant les "
        "bits bas puis en relevant les 27 bits hauts, l'etat complet devant "
        "reproduire l'ENSEMBLE des vingt numeros",
        "aucun null n'est requis : le crible garde un candidat bas avec "
        "probabilite 0,8 par tirage, donc 0,8^150 x 2^21 = 4e-9 par pas",
        "conforme si aucun etat complet n'est compatible", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(REL)), p=1.0,
        verdict="conforme" if not REL else "ETAT TROUVE",
        power_at=(f"{OKT}/{NT} etats de 48 bits PLANTES retrouves par le meme "
                  f"crible puis releves en entier — le crible ramene 2 097 152 "
                  f"candidats a une poignee et le relevement rend l'etat complet"),
        notes=(f"COUVRE LE CAS QUE LES §120 ET §121 LAISSAIENT : `new Random()` "
               f"SANS ARGUMENT, amorce sur nanoTime ^ 0x5DEECE66D, dont l'etat "
               f"est un entier LIBRE de 48 bits — l'ecriture normale en Java. Les "
               f"balayages precedents ne couvraient que `new Random(k)` pour k < "
               f"2^32, c'est-a-dire une graine NOMMEE. L'attaque ne peut pas "
               f"enumerer 2^48 et n'en a pas besoin : 80 = 16 x 5, donc "
               f"(v-1) mod 16 = (s>>>17) mod 16 = les bits 17 a 20 de l'etat, qui "
               f"ne dependent que de s mod 2^21 ; et le LCG mod 2^48 est AUTONOME "
               f"modulo 2^21. Un crible de 2^21 exclut donc 2^48. Filtre 0,8 par "
               f"tirage, {NJ} tirages consecutifs, pas 20 a 24 tous balayes."))
    h = lab.holm()
    say(f"   consigne : h128.java_48_bits   {len(REL)} etat sur 2^48 x "
        f"{len(STRIDES)} pas")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
