"""h127 — l'espace d'état ENTIER contre L'ARCHIVE, pas contre les vidéos.

CE QUE LE DOSSIER FAISAIT, ET CE QUI MANQUAIT
==============================================
Les §144, §146 et §147 attaquent les DOUZE tirages ordonnés des vidéos. C'est ce
qu'il y a de plus riche, mais c'est douze tirages. L'archive, elle, en publie
70 560 — et c'est elle qui compte, parce qu'elle est publique et permanente.

Et le §120 balayait bien l'archive, mais des GRAINES : 2^32 valeurs passées à un
amorçage NOMMÉ. Un état amorcé par une source d'entropie lui échappait.

    CE FICHIER BALAIE L'ESPACE D'ÉTAT ENTIER — les 4 294 967 296 états d'un
    générateur de 32 bits, amorcés n'importe comment — CONTRE L'ARCHIVE.

LE FILTRE, ET IL NE SUPPOSE RIEN
=================================
Le §141 l'a établi : à l'étape 0 de Fisher-Yates le tableau est ENCORE
L'IDENTITÉ, donc la valeur émise vaut exactement j_0 + 1 avec
j_0 = floor(80·u/2^32), et elle appartient à l'ensemble publié.

    j_0 + 1 ∈ S        EXACTEMENT, pour chaque tirage de l'archive.

C'est un filtre de 20/80 = 1/4 par tirage — sans l'ordre, sans le bonus, sans
aucun modèle du bonus. La fenêtre utilisée fait QUARANTE tirages consécutifs
d'une même journée, soit un filtre de 4^-40 = 10^-24 : un état faux ne survit
pas, et l'espérance de faux positifs sur les 2^32 états vaut 4·10^-15.

LE REJET PRÉCOCE FAIT LE TRAVAIL
=================================
Un état survit à k tirages avec probabilité 4^-k, donc trois états sur quatre
meurent au PREMIER mot. Le coût mesuré vaut 5,7·10^9 pas de générateur par
design, soit 23 s sur quatre fils — pour 2^32 états.

QUELS DESIGNS
==============
Tous ceux à PÉRIODE PLEINE. On ne les prend pas dans un article : on les
CALCULE. Pour chacun des 31^3 x 8 = 238 328 designs de la forme de Marsaglia, on
extrait le polynôme caractéristique par Berlekamp-Massey et on teste sa
primitivité (irréductibilité, puis ordre 2^32-1 via les facteurs premiers
3, 5, 17, 257, 65537).

    972 designs sont à période pleine, et le canonique (13,17,5) en fait
    partie — c'est le contrôle.

TÉMOIN
=======
`--selftest` plante un état de 32 bits, fabrique la fenêtre d'ensembles TRIÉS
qu'il produirait, et vérifie que le balayage le retrouve — LUI ET LUI SEUL. Puis
il refait le balayage sur des masques ALÉATOIRES et exige zéro survivant. 2/2.

Il TESTE l'archive : il consigne au registre.
"""

import json
import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H127_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H127_TMP", "/tmp")
NW = 40                                        # tirages de la fenetre
M32 = 0xFFFFFFFF


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_archive_h127")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_archive.c")],
               check=True, capture_output=True)
ENV = dict(os.environ, SWEEP_THREADS=os.environ.get("SWEEP_THREADS", "4"))


# ---------------------------------------------------------------------------
# Les designs a PERIODE PLEINE, calcules et non recopies.
# ---------------------------------------------------------------------------
def pas32(x, a, b, c, o):
    x ^= ((x << a) & M32) if o & 1 else (x >> a)
    x ^= ((x << b) & M32) if o & 2 else (x >> b)
    x ^= ((x << c) & M32) if o & 4 else (x >> c)
    return x & M32


def polmul(p, q):
    r = 0
    while q:
        if q & 1:
            r ^= p
        p <<= 1
        q >>= 1
    return r


def polmod(r, f, d):
    while r.bit_length() - 1 >= d:
        r ^= f << (r.bit_length() - 1 - d)
    return r


def bm(s):
    n = len(s)
    C = B = 1
    L, m = 0, 1
    for i in range(n):
        dd = s[i]
        for j in range(1, L + 1):
            if (C >> j) & 1:
                dd ^= s[i - j]
        if dd:
            T = C
            C ^= B << m
            if 2 * L <= i:
                L, B, m = i + 1 - L, T, 1
            else:
                m += 1
        else:
            m += 1
    return L, C


PRIMES = [3, 5, 17, 257, 65537]
NORD = (1 << 32) - 1


def primitif(f, d=32):
    r = 2
    for _ in range(32):
        r = polmod(polmul(r, r), f, d)
    if r != 2:
        return False
    for p in PRIMES:
        e, r, base = NORD // p, 1, 2
        while e:
            if e & 1:
                r = polmod(polmul(r, base), f, d)
            base = polmod(polmul(base, base), f, d)
            e >>= 1
        if r == 1:
            return False
    return True


def designs_pleins():
    cache = os.path.join(TMP, "h127_primitifs.json")
    if os.path.exists(cache):
        return [tuple(x) for x in json.load(open(cache))]
    out = []
    for a in range(1, 32):
        for b in range(1, 32):
            for c in range(1, 32):
                for o in range(8):
                    x, s = 1, []
                    for _ in range(64):
                        s.append(x & 1)
                        x = pas32(x, a, b, c, o)
                    L, C = bm(s)
                    if L == 32 and primitif(C):
                        out.append((a, b, c, o))
    json.dump(out, open(cache, "w"))
    return out


# ==========================================================================
rule("1. LA FENÊTRE DE L'ARCHIVE, ET LE FILTRE QU'ELLE DONNE")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
coupe = np.flatnonzero(np.diff(TS) != 300)
deb = np.r_[0, coupe + 1]
fin = np.r_[coupe + 1, len(TS)]
k = int(np.argmax(fin - deb))
SEG = NUM[deb[k]:deb[k] + NW]
assert np.all(np.diff(IDS[deb[k]:deb[k] + NW]) == 1)

FMASQ = os.path.join(TMP, "h127_masques.bin")
with open(FMASQ, "wb") as fh:
    for row in SEG:
        lo = hi = 0
        for v in row:
            j = int(v) - 1
            if j < 64:
                lo |= 1 << j
            else:
                hi |= 1 << (j - 64)
        fh.write(struct.pack("<QQ", lo, hi))

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True, env=ENV)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Les §144, §146 et §147 attaquent les DOUZE tirages ordonnes des videos.
   L'archive en publie {len(NUM):,}, et c'est elle qui compte. Le §120 la balayait
   bien, mais des GRAINES : 2^32 valeurs passees a un amorcage NOMME. Un etat
   amorce par une source d'entropie lui echappait.

     ICI ON BALAIE L'ESPACE D'ETAT ENTIER — les 4 294 967 296 etats d'un
     generateur de 32 bits, amorces N'IMPORTE COMMENT — CONTRE L'ARCHIVE.

   LE FILTRE NE SUPPOSE RIEN (§141). A l'etape 0 de Fisher-Yates le tableau est
   encore l'identite, donc la valeur emise vaut exactement j_0 + 1 avec
   j_0 = floor(80·u/2^32), et elle appartient a l'ensemble publie :

       j_0 + 1 dans S    EXACTEMENT, pour chaque tirage — soit 20/80 = 1/4.

   Sans l'ordre, sans le bonus, sans aucun modele du bonus.

       fenetre           {NW} tirages CONSECUTIFS d'une meme journee
       identifiants      {IDS[deb[k]]} a {IDS[deb[k]+NW-1]}
       journee           {fin[k]-deb[k]} tirages a 300 s, sans coupure
       filtre            4^-{NW} = 1e-{NW*0.602:.0f}
       faux positifs     esperance {2**32 * 4.0**-NW:.1e} sur les 2^32 etats

   temoin de l'outil : {AUTO}""")


# ==========================================================================
rule("2. LES DESIGNS À PÉRIODE PLEINE, CALCULÉS ET NON RECOPIÉS")
# ==========================================================================

t0 = time.time()
BONS = designs_pleins()
say(f"""   On ne prend pas les triplets dans un article : on les CALCULE. Pour chacun
   des 31^3 x 8 = 238 328 designs de la forme de Marsaglia, le polynome
   caracteristique est extrait par Berlekamp-Massey et sa PRIMITIVITE testee —
   irreductibilite, puis ordre 2^32-1 via les facteurs premiers de 2^32-1,
   c'est-a-dire 3, 5, 17, 257 et 65537.

       designs a periode pleine : {len(BONS)} sur 238 328   ({time.time()-t0:.0f} s)
       le canonique (13,17,5,or=5) en fait partie : {'OUI' if (13,17,5,5) in BONS else 'NON'}

   C'est le controle : xorshift32 tel que Marsaglia le publie doit etre dans la
   liste, et il y est.""")


# ==========================================================================
rule("3. LE BALAYAGE")
# ==========================================================================

NDES = 6 if DRY else int(os.environ.get("H127_NDES", str(len(BONS))))
say(f"""   {NDES} designs x 4 294 967 296 etats. Le rejet precoce fait le travail : trois
   etats sur quatre meurent au PREMIER mot, et le cout mesure vaut 5,7e9 pas de
   generateur par design.

       {'#':>5} {'design':>20} {'survivants':>11} {'sec':>7} {'reste':>9}""")

# POINT DE CONTROLE : un balayage de plusieurs heures doit survivre a une
# interruption. Chaque design termine est ecrit ; au demarrage on saute ceux
# qui le sont deja.
JOURNAL = os.path.join(TMP, "h127_journal.txt")
DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 3:
            DEJA[t[0]] = (int(t[1]), float(t[2]))
    say(f"   reprise : {len(DEJA)} designs deja faits, ecrits dans {JOURNAL}")

TROUV, FAIT, PAS = [], 0, 0.0
t0 = time.time()
jr = open(JOURNAL, "a", encoding="utf-8")
for i, (a, b, c, o) in enumerate(BONS[:NDES]):
    cle = f"{a},{b},{c},{o}"
    if cle in DEJA:
        ns, pp = DEJA[cle]
        FAIT += 1
        PAS += pp
        continue
    p = subprocess.run([BIN, FMASQ, str(NW), str(a), str(b), str(c), str(o)],
                       capture_output=True, text=True, timeout=3600, env=ENV)
    ns = 0
    pp = 0.0
    for l in p.stdout.split("\n"):
        if l.startswith("TROUVE"):
            TROUV.append(l.strip())
        if l.startswith("designs="):
            d = dict(kv.split("=", 1) for kv in l.split() if "=" in kv)
            ns = int(d["survivants"])
            pp = float(d["pas"])
            PAS += pp
    jr.write(f"{cle} {ns} {pp:.6e}\n")
    jr.flush()
    FAIT += 1
    if i < 3 or ns or (i + 1) % 10 == 0 or i + 1 == NDES:
        ec = time.time() - t0
        say(f"   {i+1:>5} {f'({a},{b},{c},or={o})':>20} {ns:>11} {ec/FAIT:>7.1f} "
            f"{(ec/FAIT*(NDES-FAIT))/3600:>8.1f} h")

say(f"""
   {len(TROUV)} etat compatible sur {FAIT} designs x 2^32 = {FAIT*4294967296:,} etats,
   soit {PAS:.3e} pas de generateur.""")
for l in TROUV:
    say(f"     !! {l}")
if not TROUV:
    say(f"""     AUCUN. Et c'est une exclusion, pas une absence de resultat : le filtre
     vaut 1e-{NW*0.602:.0f} par etat, et le temoin retrouve un etat plante.

   CE QUE CELA FERME SUR L'ARCHIVE. Tout generateur xorshift de 32 bits a
   PERIODE PLEINE, quel que soit son triplet de decalages, son orientation, ET
   SON ETAT INITIAL — y compris amorce par une source d'entropie, ce que le
   §120 ne couvrait pas.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h127.archive_espace_etat",
        f"Aucun des {FAIT} designs xorshift de 32 bits a PERIODE PLEINE balayes, "
        f"pour AUCUN de ses 4 294 967 296 etats initiaux, n'engendre la fenetre "
        f"de {NW} tirages consecutifs de l'archive. Le filtre est le confinement "
        f"du §141 — a l'etape 0 de Fisher-Yates la valeur emise vaut exactement "
        f"j_0 + 1 et appartient a l'ensemble publie — donc il ne suppose ni "
        f"l'ordre, ni le bonus, ni aucun modele du bonus. C'est strictement plus "
        f"fort que le §120, qui balayait 2^32 GRAINES sous des amorcages nommes",
        "nombre d'etats compatibles, un etat etant compatible s'il satisfait le "
        f"confinement sur les {NW} tirages de la fenetre. Probabilite de faux "
        f"positif : 4^-{NW} = 1e-{NW*0.602:.0f} par etat",
        f"aucun null n'est requis : l'esperance de faux positifs vaut "
        f"{2**32 * 4.0**-NW:.1e} par design",
        "conforme si aucun etat n'est compatible", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(TROUV)), p=1.0,
        verdict="conforme" if not TROUV else "ETAT TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} — un etat de 32 bits plante est "
                  f"retrouve LUI ET LUI SEUL a partir des seuls ensembles TRIES, "
                  f"et des masques aleatoires ne rendent aucun survivant"),
        notes=(f"PREMIER BALAYAGE D'ESPACE D'ETAT SUR L'ARCHIVE. Le §120 balayait "
               f"2^32 GRAINES sous amorcage nomme ; ici l'etat est LIBRE, amorce "
               f"n'importe comment, y compris par une source d'entropie. Les "
               f"designs ne sont pas recopies d'un article mais CALCULES : "
               f"polynome caracteristique par Berlekamp-Massey puis test de "
               f"primitivite (irreductibilite, puis ordre 2^32-1 via 3, 5, 17, "
               f"257, 65537), ce qui donne {len(BONS)} designs a periode pleine sur "
               f"238 328, le canonique (13,17,5) inclus. Fenetre de {NW} tirages "
               f"CONSECUTIFS d'une meme journee (ids {IDS[deb[k]]}-{IDS[deb[k]+NW-1]}), "
               f"filtre 4^-{NW}. {FAIT} designs x 2^32 = {FAIT*4294967296:,} etats, "
               f"{PAS:.3e} pas de generateur, {len(TROUV)} compatible."))
    h = lab.holm()
    say(f"   consigne : h127.archive_espace_etat   {len(TROUV)} etat sur "
        f"{FAIT*4294967296:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
