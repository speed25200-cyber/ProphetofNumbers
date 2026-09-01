"""h130 — l'espace d'état de 32 bits contre l'archive, sous les TROIS AUTRES
façons de tirer vingt numéros.

CE QUE LE §150 LAISSAIT
========================
Le h127 énumère les 2^32 états de chacun des 972 designs xorshift à période
pleine et demande à chacun s'il produit EXACTEMENT l'ensemble des vingt numéros
d'un tirage de l'archive. Mais il le demande sous UN SEUL échantillonneur — la
troncature `(x·(80−k)) >> 32` de Lemire — et un seul schéma, Fisher-Yates
partiel. Or le code qui tire vingt numéros s'écrit bien plus souvent avec un
MODULO, et souvent sans Fisher-Yates du tout.

LES TROIS MODES
================
    MODULO    Fisher-Yates partiel, j = k + x mod (80−k)
    REJET     v = x mod 80 + 1, tiré jusqu'à vingt DISTINCTS
    SHUFFLE   Collections.shuffle : pour i = 79..1, swap(i, x mod (i+1)) ;
              le tirage = les vingt DERNIÈRES cases, fixées par les vingt
              premiers mots

Les trois partagent leur premier mot — sa valeur est `x mod 80 + 1` dans les
trois cas et doit appartenir à l'ensemble publié — donc trois états sur quatre
meurent avant qu'aucun tableau ne soit construit, et balayer les trois modes
coûte moins que le seul mode du h127.

CE QU'ON NE BALAIE PAS, ET POURQUOI
====================================
Les vingt PREMIÈRES cases d'un shuffle complet dépendent des 79 mots : pas de
rejet précoce, soixante fois plus cher. Il est dit, pas fait.

TÉMOIN
=======
`tools/sweep_archive3.c --selftest` : un état planté sous chacun des trois
modes est retrouvé, lui seul, dans SON mode seulement ; un ensemble aléatoire
ne rend rien.

Il TESTE l'archive : il consigne au registre.
"""

import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402
import designs32                                              # noqa: E402

T0 = time.time()
DRY = os.environ.get("H130_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H130_TMP", "/tmp")
MODES = ("modulo", "rejet", "shuffle")


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_archive3_h130")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_archive3.c")],
               check=True, capture_output=True)
ENV = dict(os.environ, SWEEP_THREADS=os.environ.get("SWEEP_THREADS", "4"))


# ==========================================================================
rule("1. LA CIBLE — le même tirage que le §150, et les trois modes")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
coupe = np.flatnonzero(np.diff(TS) != 300)
deb = np.r_[0, coupe + 1]
fin = np.r_[coupe + 1, len(TS)]
k = int(np.argmax(fin - deb))
CIBLE = NUM[deb[k]].tolist()
ID_CIBLE = int(IDS[deb[k]])

from math import comb                                            # noqa: E402
FILTRE = 1.0 / comb(80, 20)

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True, env=ENV)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Le §150 balaie les 2^32 etats de 972 designs xorshift contre l'ensemble du
   tirage {ID_CIBLE} — sous la troncature de Lemire et Fisher-Yates partiel. Ici,
   meme design, meme tirage, meme filtre 1/C(80,20) = {FILTRE:.2e}, et les
   trois autres facons d'ecrire un tirage :

       MODULO    j = k + x mod (80-k)         (Fisher-Yates partiel)
       REJET     v = x mod 80 + 1, jusqu'a vingt distincts
       SHUFFLE   Collections.shuffle, les vingt DERNIERES cases

   Le premier mot est commun aux trois — x mod 80 + 1 — et tue trois etats sur
   quatre avant tout tableau.

       ensemble vise     {CIBLE}
       faux positifs     {2**32 * FILTRE:.1e} par design et par mode

   temoin de l'outil : {AUTO}""")
assert AUTO.endswith("4/4"), AUTO


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

BONS = designs32.designs_pleins()
NDES = 4 if DRY else int(os.environ.get("H130_NDES", str(len(BONS))))
say(f"""   {NDES} designs a periode pleine (la liste du §150, {len(BONS)} designs) x
   4 294 967 296 etats x 3 modes.

       {'#':>5} {'design':>20} {'modulo':>7} {'rejet':>6} {'shuffle':>8} {'sec':>7} {'reste':>9}""")

JOURNAL = os.path.join(TMP, "h130_journal.txt")
DEJA = {}
if os.path.exists(JOURNAL):
    for l in open(JOURNAL, encoding="utf-8"):
        t = l.split()
        if len(t) >= 4:
            DEJA[t[0]] = tuple(int(x) for x in t[1:4])
    say(f"   reprise : {len(DEJA)} designs deja faits, ecrits dans {JOURNAL}")

TROUV, FAIT = [], 0
TOT = [0, 0, 0]
t0 = time.time()
jr = open(JOURNAL, "a", encoding="utf-8")
for i, (a, b, c, o) in enumerate(BONS[:NDES]):
    cle = f"{a},{b},{c},{o}"
    if cle in DEJA:
        ns = DEJA[cle]
        FAIT += 1
        for m in range(3):
            TOT[m] += ns[m]
        continue
    p = subprocess.run([BIN, str(a), str(b), str(c), str(o)]
                       + [str(v) for v in CIBLE],
                       capture_output=True, text=True, timeout=3600, env=ENV)
    ns = (0, 0, 0)
    for l in p.stdout.split("\n"):
        if l.startswith("TROUVE"):
            TROUV.append(l.strip())
        if l.startswith("designs="):
            d = dict(kv.split("=", 1) for kv in l.split() if "=" in kv)
            ns = (int(d["modulo"]), int(d["rejet"]), int(d["shuffle"]))
    for m in range(3):
        TOT[m] += ns[m]
    jr.write(f"{cle} {ns[0]} {ns[1]} {ns[2]}\n")
    jr.flush()
    FAIT += 1
    if i < 3 or any(ns) or (i + 1) % 10 == 0 or i + 1 == NDES:
        ec = time.time() - t0
        nf = FAIT - len(DEJA)
        say(f"   {i+1:>5} {f'({a},{b},{c},or={o})':>20} {ns[0]:>7} {ns[1]:>6} "
            f"{ns[2]:>8} {ec/max(nf,1):>7.1f} {(ec/max(nf,1)*(NDES-FAIT))/3600:>8.1f} h")

say(f"""
   {sum(TOT)} etat compatible sur {FAIT} designs x 2^32 x 3 modes =
   {FAIT*4294967296*3:,} (etat, mode) — modulo {TOT[0]}, rejet {TOT[1]}, shuffle {TOT[2]}.""")
for l in TROUV:
    say(f"     !! {l}")
if not TROUV:
    say(f"""     AUCUN. Avec le §150, tout xorshift de 32 bits a periode pleine est
     donc exclu sur l'archive sous les QUATRE facons usuelles de tirer vingt
     numeros — troncature, modulo, rejet des doublons, shuffle complet (vingt
     dernieres cases) — quel que soit son etat initial.

   CE QUI RESTE OUVERT, ET IL FAUT LE DIRE : les vingt PREMIERES cases d'un
   shuffle complet (79 mots par tirage, sans rejet precoce) ; et tout
   generateur dont l'etat depasse 32 bits, que l'enumeration ne touche pas.""")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h130.archive_trois_echantillonneurs",
        f"Aucun des {FAIT} designs xorshift de 32 bits a PERIODE PLEINE (la liste "
        f"du h127), pour AUCUN de ses 4 294 967 296 etats initiaux, n'engendre "
        f"EXACTEMENT l'ensemble des vingt numeros du tirage {ID_CIBLE} de "
        f"l'archive sous AUCUN des trois modes : Fisher-Yates partiel par modulo "
        f"(j = k + x mod (80-k)), tirage par rejet des doublons (v = x mod 80 + 1 "
        f"jusqu'a vingt distincts), Collections.shuffle (swap(i, x mod (i+1)) "
        f"pour i = 79..1, tirage = les vingt dernieres cases). Complete le §150, "
        f"qui ne couvrait que la troncature de Lemire",
        "nombre de couples (etat, mode) compatibles, un etat etant compatible "
        "dans un mode s'il produit l'ensemble des vingt numeros du tirage vise. "
        f"Probabilite de faux positif : 1/C(80,20) = {FILTRE:.2e} par etat et "
        "par mode",
        f"aucun null n'est requis : l'esperance de faux positifs vaut "
        f"{3 * 2**32 * FILTRE:.1e} par design",
        "conforme si aucun couple (etat, mode) n'est compatible", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(sum(TOT)), p=1.0,
        verdict="conforme" if not TROUV else "ETAT TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} — un etat de 32 bits plante sous "
                  f"chacun des trois modes est retrouve LUI SEUL et dans SON mode "
                  f"seulement, et un ensemble aleatoire ne rend aucun survivant"),
        notes=(f"COMPLETE LE §150 (troncature seule) PAR LES TROIS AUTRES FACONS "
               f"D'ECRIRE UN TIRAGE. Le premier mot est commun aux trois modes "
               f"(x mod 80 + 1) et rejette 3/4 des etats avant tout tableau. "
               f"Cible : l'ensemble trie du tirage {ID_CIBLE}, un seul tirage "
               f"suffit (filtre {FILTRE:.1e}), donc ni pas ni alignement "
               f"supposes. NON COUVERT : les vingt premieres cases d'un shuffle "
               f"complet (79 mots par tirage, sans rejet precoce). {FAIT} designs "
               f"x 2^32 x 3 = {FAIT*4294967296*3:,} couples, {sum(TOT)} compatible."))
    h = lab.holm()
    say(f"   consigne : h130.archive_trois_echantillonneurs   {sum(TOT)} couple sur "
        f"{FAIT*4294967296*3:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
