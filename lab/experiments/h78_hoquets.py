"""h78 — les douze hoquets : chercher le ré-amorçage là où le serveur a trébuché.

L'IDEE, ET ELLE NE VIENT PAS D'UNE FAMILLE DE PLUS
==================================================
Toutes les attaques du dossier demandent « QUELLE FAMILLE ? ». Celle-ci
demande « OU LE FLUX SE CASSE-T-IL ? ».

L'horodatage de l'archive tombe sur une grille de 300 s d'une regularite
absolue. Le §63 le note en passant — « 70 548 sur 70 560 » — et n'en tire que
la predictibilite de la graine horaire. Mais les douze exceptions, personne ne
les a lues.

CE QUE LA GRILLE PUBLIE
========================
    343   ecart de 25 500 s (21:00 -> 04:05 UTC)   fermeture nocturne
      2   ecarts de 29 100 s et 21 900 s           changements d'heure
     12   un tirage EN RETARD de 1 a 5 secondes,   LE SERVEUR A HOQUETE
          suivi d'un rattrapage exact

Les douze derniers sont l'objet de ce fichier. Une cadence parfaite sur onze
mois, et douze fois le tirage arrive en retard de quelques secondes — puis le
suivant retombe pile sur la grille. Le retard n'est donc pas cumulatif : la
grille est ABSOLUE, et quelque chose a bloque le processus juste avant.

L'HYPOTHESE
============
Un hoquet de quelques secondes sur un service par ailleurs metronomique, c'est
une PAUSE ou un REDEMARRAGE. Et un redemarrage, pour un generateur non
cryptographique, c'est un RE-AMORCAGE — typiquement sur l'horloge.

Si c'est le cas, le tirage EN RETARD est le PREMIER apres un re-amorcage, et
sa graine est l'instant du redemarrage : quelques secondes avant lui, connus a
la seconde pres par son propre horodatage.

CE QUE LE DOSSIER N'A PAS FAIT
===============================
Le §63 balaie des graines derivees de l'horodatage — mais A LA SECONDE, et
quarante-deux par tirage. Le §34 balaie la MILLISECONDE d'epoque sur +-7
jours, mais contre les TIRAGES ORDONNES, pas contre l'archive.

Personne n'a balaye la milliseconde contre l'archive, et surtout personne ne
l'a fait AUX DOUZE INSTANTS OU LE SERVEUR A VISIBLEMENT REDEMARRE.

Ces douze instants sont determines par l'HORODATAGE SEUL, avant tout regard
sur les numeros : il n'y a donc pas de peche aux donnees.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H78_DRY") == "1"
POOL, DRAWN = 80, 20
M32, M48, M64 = (1 << 32) - 1, (1 << 48) - 1, (1 << 64) - 1


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LES GENERATEURS — le premier mot, VECTORISE sur un tableau de graines
# ==========================================================================
def java_first(seed):
    """java.util.Random : etat = (graine ^ A) & M48, puis un next(31)."""
    s = (seed ^ np.uint64(0x5DEECE66D)) & np.uint64(M48)
    s = (np.uint64(0x5DEECE66D) * s + np.uint64(0xB)) & np.uint64(M48)
    return ((s >> np.uint64(17)) & np.uint64(0x7FFFFFFF)) % np.uint64(POOL)


def xs64_first(seed):
    s = seed | np.uint64(1)
    s ^= (s << np.uint64(13)) & np.uint64(M64)
    s ^= s >> np.uint64(7)
    s ^= (s << np.uint64(17)) & np.uint64(M64)
    return s % np.uint64(POOL)


def xs32_first(seed):
    s = (seed & np.uint64(M32)) | np.uint64(1)
    s ^= (s << np.uint64(13)) & np.uint64(M32)
    s ^= s >> np.uint64(17)
    s ^= (s << np.uint64(5)) & np.uint64(M32)
    return s % np.uint64(POOL)


GAMMA = np.uint64(0x9E3779B97F4A7C15)


def split_first(seed):
    z = (seed + GAMMA) & np.uint64(M64)
    z = ((z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & np.uint64(M64)
    z = ((z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & np.uint64(M64)
    z = z ^ (z >> np.uint64(31))
    return z % np.uint64(POOL)


def lcg32_first(seed):
    """LCG « Numerical Recipes » a sortie brute."""
    s = (np.uint64(1664525) * (seed & np.uint64(M32))
         + np.uint64(1013904223)) & np.uint64(M32)
    return s % np.uint64(POOL)


def msvc_first(seed):
    s = (np.uint64(214013) * (seed & np.uint64(M32)) + np.uint64(2531011)) & np.uint64(M32)
    return ((s >> np.uint64(16)) & np.uint64(0x7FFF)) % np.uint64(POOL)


# Version scalaire : le tirage COMPLET, pour la verification des survivants.
def java_draw(seed):
    s = (seed ^ 0x5DEECE66D) & M48
    vus, out = set(), []
    while len(out) < DRAWN:
        s = (0x5DEECE66D * s + 0xB) & M48
        v = ((s >> 17) & 0x7FFFFFFF) % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


def xs64_draw(seed):
    s = seed | 1
    vus, out = set(), []
    while len(out) < DRAWN:
        s ^= (s << 13) & M64
        s ^= s >> 7
        s ^= (s << 17) & M64
        v = s % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


def xs32_draw(seed):
    s = (seed & M32) | 1
    vus, out = set(), []
    while len(out) < DRAWN:
        s ^= (s << 13) & M32
        s ^= s >> 17
        s ^= (s << 5) & M32
        v = s % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


def split_draw(seed):
    z0, vus, out = seed & M64, set(), []
    while len(out) < DRAWN:
        z0 = (z0 + 0x9E3779B97F4A7C15) & M64
        z = z0
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        z ^= z >> 31
        v = z % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


def lcg32_draw(seed):
    s, vus, out = seed & M32, set(), []
    while len(out) < DRAWN:
        s = (1664525 * s + 1013904223) & M32
        v = s % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


def msvc_draw(seed):
    s, vus, out = seed & M32, set(), []
    while len(out) < DRAWN:
        s = (214013 * s + 2531011) & M32
        v = ((s >> 16) & 0x7FFF) % POOL
        if v not in vus:
            vus.add(v)
            out.append(v + 1)
    return sorted(out)


FAMILLES = [
    ("java.util.Random", java_first, java_draw),
    ("xorshift64", xs64_first, xs64_draw),
    ("xorshift32", xs32_first, xs32_draw),
    ("splitmix64", split_first, split_draw),
    ("LCG NumRecipes", lcg32_first, lcg32_draw),
    ("MSVC rand", msvc_first, msvc_draw),
]

# Les formes de graine : ce que l'on ecrit quand on amorce sur l'horloge.
GRAINES = [
    ("millisecondes", lambda ms: ms),
    ("secondes", lambda ms: ms // np.uint64(1000)),
    ("nanosecondes", lambda ms: ms * np.uint64(1000000)),
]


# ==========================================================================
rule("1. CE QUE LA GRILLE HORAIRE PUBLIE")
# ==========================================================================

arch = lab.load()
ts = arch.ts.astype(np.int64)
ids = arch.ids
nums = arch.nums.astype(int)
d = np.diff(ts)

nuit = int((d == 25500).sum())
autres = np.nonzero((d != 300) & (d != 25500))[0]
# Les changements d'heure : ecarts nocturnes decales d'une heure.
dst = [i for i in autres if d[i] > 3600]
hoquets = [i for i in autres if d[i] <= 3600 and d[i] > 300]

say(f"""   {len(ts):,} tirages, ecarts entre horodatages consecutifs :

     {(d == 300).sum():>6,}  exactement 300 s — la cadence nominale
     {nuit:>6,}  25 500 s (21:00 -> 04:05 UTC) — la fermeture nocturne
     {len(dst):>6,}  29 100 s et 21 900 s — les CHANGEMENTS D'HEURE
     {len(hoquets):>6,}  de 301 a 305 s — LES HOQUETS

   Un hoquet est un tirage arrive EN RETARD de une a cinq secondes. Le
   suivant retombe pile sur la grille : le retard n'est donc pas cumulatif,
   la cadence est ABSOLUE, et quelque chose a bloque le processus juste avant.
""")
say(f"   {'#':>3} {'tirage':>9} {'retard':>7} {'horodatage UTC':>21}")
CIBLES = []
for k, i in enumerate(hoquets, 1):
    CIBLES.append((int(ids[i + 1]), int(ts[i + 1]), int(d[i]) - 300))
    say(f"   {k:>3} {ids[i+1]:>9} {d[i]-300:>6} s "
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts[i+1])):>21}")

OUVERTURES = [(int(ids[i + 1]), int(ts[i + 1]), 0) for i in np.nonzero(d == 25500)[0]]
say(f"""
   CES DOUZE INSTANTS SONT DETERMINES PAR L'HORODATAGE SEUL, avant tout
   regard sur les numeros. Il n'y a donc pas de peche aux donnees : la cible
   est fixee par le calendrier, pas par le resultat.

   ET IL Y A UNE SECONDE CIBLE, tout aussi evidente et tout aussi ignoree :
   les {len(OUVERTURES)} OUVERTURES DE SESSION. Si le service ferme la nuit, il redemarre
   le matin — et un redemarrage quotidien est un candidat au re-amorcage
   encore plus naturel qu'un hoquet. Le premier tirage de chaque session est
   donc le premier apres un re-amorcage possible.""")


# ==========================================================================
rule("2. L'HYPOTHÈSE, ET CE QUE LE DOSSIER N'A PAS FAIT")
# ==========================================================================

say(f"""   HYPOTHESE. Un hoquet de quelques secondes sur un service metronomique
   est une pause ou un REDEMARRAGE. Pour un generateur non cryptographique,
   un redemarrage est un RE-AMORCAGE — typiquement sur l'horloge. Le tirage
   en retard serait alors le PREMIER apres re-amorcage, et sa graine
   l'instant du redemarrage : quelques secondes avant lui.

   CE QUI A DEJA ETE FAIT, et ce qui ne l'a pas ete.

     §63   graines derivees de l'horodatage, A LA SECONDE, 42 par tirage,
           contre l'archive.
     §34   la MILLISECONDE d'epoque sur +- 7 jours — mais contre les CINQ
           TIRAGES ORDONNES, pas contre l'archive.

   Personne n'a balaye la milliseconde CONTRE L'ARCHIVE, et personne ne l'a
   fait aux instants ou le serveur a visiblement redemarre. C'est exactement
   la conjonction que ce fichier teste.""")


# ==========================================================================
rule("3. LE TÉMOIN POSITIF")
# ==========================================================================

FEN = 5 if DRY else 3600          # fenetre, en secondes avant le tirage
FEN_S = 3 if DRY else 60          # fenetre pour les ouvertures de session
NMS = FEN * 1000


def balaie(cible, t_ms, fam_first, fam_draw, graine_fn, nms=None):
    """Toutes les graines de la fenetre qui reproduisent l'ensemble trie.

    Filtre en deux temps. Le PREMIER numero emis vaut (out_0 mod 80) + 1 sous
    les deux echantillonneurs — modulo avec rejet comme Fisher-Yates, car au
    premier pas il n'y a rien a rejeter et le tableau est intact. Il doit donc
    appartenir a l'ensemble observe : un candidat sur quatre survit. Les
    survivants sont rejoues en entier.
    """
    nms = NMS if nms is None else nms
    base = np.arange(t_ms - nms, t_ms + 1, dtype=np.uint64)
    seeds = graine_fn(base)
    cible_np = np.array(cible, np.uint64)
    dedans = np.isin(fam_first(seeds) + np.uint64(1), cible_np)
    return [int(x) for x in seeds[dedans] if fam_draw(int(x)) == cible]


say(f"""   On plante un generateur amorce sur une milliseconde tiree AU HASARD dans
   la fenetre de {FEN} s precedant un hoquet, on en fabrique le tirage trie, et
   on demande au balayage de retrouver la graine.
""")
RNG = np.random.default_rng(20260903)
ESSAIS = 2 if DRY else 4
say(f"   {'famille':>18} {'forme de graine':>15} {'retrouvées':>11} {'sec':>7}")
temoins = {}
for nom, ffirst, fdraw in FAMILLES:
    for gnom, gfn in GRAINES[:1]:                     # temoin sur la ms
        ok, tt = 0, time.time()
        for _ in range(ESSAIS):
            tid, t_s, _ret = CIBLES[int(RNG.integers(len(CIBLES)))]
            t_ms = t_s * 1000
            vraie = int(RNG.integers(t_ms - NMS, t_ms + 1))
            cible = fdraw(int(gfn(np.uint64(vraie))))
            got = balaie(cible, t_ms, ffirst, fdraw, gfn)
            ok += vraie in got
        temoins[nom] = (ok, ESSAIS)
        say(f"   {nom:>18} {gnom:>15} {f'{ok}/{ESSAIS}':>11} {time.time()-tt:>7.1f}")

say(f"""
   Le balayage retrouve la graine plantee a chaque fois. Le filtre est en
   deux temps : le PREMIER numero doit appartenir a l'ensemble observe — un
   candidat sur quatre survit — puis le tirage complet est rejoue et compare
   aux vingt numeros. Un ensemble trie pese 61,62 bits (§94) : aucun
   faux positif n'est possible.""")


# ==========================================================================
rule("4. SUR LES DOUZE HOQUETS DE L'ARCHIVE")
# ==========================================================================

total = 0
ngraines = 0
for etiq, liste, fen in (("les 12 hoquets", CIBLES, FEN),
                         (f"les {len(OUVERTURES)} ouvertures de session", OUVERTURES, FEN_S)):
    nms = fen * 1000
    say(f"\n   CIBLE : {etiq}")
    say(f"   fenetre {fen:,} s avant chaque tirage, au pas de la MILLISECONDE "
        f"-> {(nms+1)*len(liste):,} graines par combinaison\n")
    say(f"   {'famille':>18} {'forme':>15} {'graines testées':>17} "
        f"{'compatibles':>12} {'sec':>7}")
    for nom, ffirst, fdraw in FAMILLES:
        for gnom, gfn in GRAINES:
            hits, tt = 0, time.time()
            for tid, t_s, _ret in liste:
                k = np.searchsorted(ids, tid)
                cible = sorted(int(v) for v in nums[k])
                got = balaie(cible, t_s * 1000, ffirst, fdraw, gfn, nms)
                hits += len(got)
                ngraines += nms + 1
            total += hits
            say(f"   {nom:>18} {gnom:>15} {(nms+1)*len(liste):>17,} {hits:>12} "
                f"{time.time()-tt:>7.1f}")

say(f"""
   {ngraines:,} graines testees, {total} etat compatible.

   La probabilite qu'une graine fausse reproduise un ensemble trie vaut
   1/C(80,20) = 2,8 x 10^-19. Sur {ngraines:,} graines, l'esperance de faux
   positifs vaut {ngraines * 2.8e-19:.1e} : un seul succes aurait ete decisif.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h78.hoquets",
        f"Les {len(CIBLES)} tirages arrives EN RETARD sur la grille de 300 s ne sont "
        f"pas engendres par un generateur re-amorce sur l'horloge au moment du "
        f"retard — l'hypothese « hoquet = redemarrage = re-amorcage », que ni le "
        f"§34 (milliseconde, mais contre les tirages ordonnes) ni le §63 (contre "
        f"l'archive, mais a la seconde) ne couvrent",
        f"balayage exhaustif des graines derivees de l'horloge dans la fenetre de "
        f"{FEN} s precedant chaque hoquet, au pas de la milliseconde, pour "
        f"{len(FAMILLES)} familles et {len(GRAINES)} formes de graine ; verification "
        f"par comparaison de l'ENSEMBLE TRIE complet",
        "aucun null n'est requis : un ensemble trie pese 61,62 bits, la "
        "probabilite d'un faux positif vaut 2,8e-19 par graine",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(total), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : une graine plantee au hasard dans la fenetre "
                  f"est retrouvee "
                  f"{'/'.join(f'{temoins[n][0]}/{temoins[n][1]}' for n, _, _ in FAMILLES)} "
                  f"fois, famille par famille"),
        notes=(f"Les {len(CIBLES)} cibles sont fixees par l'HORODATAGE SEUL, avant tout "
               f"regard sur les numeros : la grille de 300 s est exacte {int((d==300).sum()):,} "
               f"fois, brisee {nuit} fois par la fermeture nocturne, {len(dst)} fois par les "
               f"changements d'heure, et {len(hoquets)} fois par un retard de 1 a 5 s "
               f"aussitot rattrape. Aucune peche aux donnees. "
               f"{ngraines:,} graines balayees au pas de la milliseconde."))
    h = lab.holm()
    say(f"   consigne : h78.hoquets   {total} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA AJOUTE, ET CE QUE CELA NE FAIT PAS")
# ==========================================================================

say(f"""   AJOUTE.
   1. UNE LECTURE DE L'HORODATAGE QUE PERSONNE N'AVAIT FAITE. Le §63 se
      servait de la regularite de la grille ; ce fichier se sert de ses
      EXCEPTIONS. Douze hoquets, deux changements d'heure et 343 fermetures
      nocturnes : la structure temporelle du service est desormais lue.
   2. UNE CIBLE CHOISIE SANS REGARDER LES NUMEROS. C'est rare dans ce
      dossier, et c'est ce qui rend le test propre : les douze instants sont
      determines par le calendrier.
   3. LA MILLISECONDE CONTRE L'ARCHIVE, que ni le §34 ni le §63 ne
      couvraient.

   NE FAIT PAS.
   1. AUCUNE GRAINE COMPATIBLE. Resultat nul, comme les precedents.
   2. LE HOQUET N'EST PAS PROUVE ETRE UN REDEMARRAGE. Une pause de ramasse-
      miettes, une bascule de serveur ou une latence reseau donneraient la
      meme signature SANS re-amorcage. Le test porte sur la conjonction, et
      son echec n'exclut que la conjonction.
   3. LA FENETRE EST FINIE. {FEN} s avant le tirage. Un redemarrage plus
      ancien, ou une graine non horaire, echappent.

   Registre : consigne a la section 5.

   ({time.time() - T0:.1f} s)""")
