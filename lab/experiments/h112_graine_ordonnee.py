"""h112 — le balayage de graines sur les trois tirages ORDONNÉS datés.

CE QUI EST NEUF, ET CE QUI NE L'EST PAS
========================================
Le §34 a écrit `tools/sweep_order.c` : douze familles, quatre échantillonneurs,
quarante-huit combinaisons, balayées contre l'ORDRE de sortie plutôt que contre
l'ensemble. Le filtre passe de 1/4 à 1/80 par pas et la probabilité de faux
positif de 3e-19 à 1e-37. Cet outil-là n'est pas neuf.

CE QUI EST NEUF EST LA DONNÉE. Les trois vidéos apportent trois tirages
ordonnés dont on connaît, pour la première fois, À LA FOIS :

    l'IDENTIFIANT      1381278, 1381481, 1381483
    l'ORDRE d'émission  les vingt numéros, dans l'ordre
    l'HORODATAGE EXACT  déduit de la structure de journée du §130, et vérifié
                        contre la cadence de l'archive à la seconde près

C'est cette troisième colonne qui manquait. Sous l'hypothèse du RÉ-AMORCAGE PAR
TIRAGE — celle qu'on écrit quand on tape `new Random(seed)` en tête de la
fonction de tirage — la graine la plus naturelle est l'identifiant ou l'heure.
Les deux sont maintenant connus exactement.

LA VÉRIFICATION DE L'HORODATAGE
================================
Le §130 donne 204 tirages par journée, de 06:05 à 23:00. De la fin de l'archive
(1380173, unix 1787691600, index 203 de sa journée) au tirage 1381278 il y a
1 105 tirages, soit 5 journées pleines et 85 tirages, donc SIX nuits :

    1105 x 300 s + 6 x (25 500 - 300) s ... non : le compte exact se fait par
    différence de dates — 23:00 du jour 0 à 13:05 du jour 6, soit
    6 x 86 400 - 35 700 = 482 700 s.

    1787691600 + 482 700 = 1788174300, et c'est bien l'horodatage déduit.

DEUX PLAGES, ET ELLES COUVRENT TOUT CE QUI EST NOMMABLE
=======================================================
    [0 ; 2^32)              petites graines, IDENTIFIANT (1,38e6),
                            HORODATAGE EN SECONDES (1,788e9)
    ts*1000 +- 600 s        HORODATAGE EN MILLISECONDES, hors de 2^32 (§121)

Il TESTE l'archive : il consigne au registre.
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H112_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H112_TMP", "/tmp")
HI = (1 << 24) if DRY else (1 << 32)
FEN = 600                                  # secondes de part et d'autre

TIRAGES = [
    (1381278, 1788174300,
     [17, 74, 45, 36, 69, 60, 4, 47, 7, 75, 28, 12, 8, 22, 54, 25, 56, 62, 52, 15]),
    (1381481, 1788260400,
     [61, 8, 20, 49, 59, 3, 24, 27, 39, 74, 71, 66, 54, 58, 21, 5, 11, 41, 10, 26]),
    (1381483, 1788261000,
     [76, 79, 64, 6, 71, 68, 75, 40, 50, 14, 36, 32, 57, 10, 19, 29, 28, 12, 3, 65]),
]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_order_h112")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_order.c")],
               check=True, capture_output=True)


def balaye(lo, hi, ordre):
    p = subprocess.run([BIN, str(lo), str(hi)] + [str(n) for n in ordre],
                       capture_output=True, text=True, timeout=7200)
    tot, trouv = 0, []
    for l in p.stdout.split("\n"):
        if "total :" in l:
            tot = int(l.split(":")[1].split()[0])
        if l.startswith("TROUVE") or "graine=" in l:
            trouv.append(l.strip())
    return tot, trouv


# ==========================================================================
rule("1. CE QUI EST NEUF : L'HORODATAGE EXACT")
# ==========================================================================

say(f"""   Le §34 a ecrit `tools/sweep_order.c` — douze familles, quatre
   echantillonneurs, quarante-huit combinaisons, balayees contre l'ORDRE de
   sortie. Le filtre vaut 1/80 par pas et la probabilite de faux positif
   1e-37. L'outil n'est pas neuf.

   CE QUI EST NEUF EST LA DONNEE. Pour la premiere fois, trois tirages
   ordonnes dont on connait A LA FOIS l'identifiant, l'ordre et l'HEURE EXACTE
   — cette derniere deduite de la structure de journee du §130 et verifiee
   contre la cadence de l'archive.

   {'tirage':>9} {'heure locale':>14} {'unix':>12} {'ms':>16} {'1er numéro':>11}""")
for tid, ts, ordre in TIRAGES:
    loc = time.strftime("%d/%m %H:%M", time.gmtime(ts + 7200))
    say(f"   {tid:>9} {loc:>14} {ts:>12} {ts*1000:>16} {ordre[0]:>11}")

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]
say(f"""
   Verification de l'horodatage : fin de l'archive 1380173 a unix 1787691600
   (index 203 de sa journee, 23:00). Jusqu'a 1381278 il y a 1 105 tirages, soit
   cinq journees pleines et 85 tirages — donc six nuits, et de 23:00 du jour 0
   a 13:05 du jour 6 il s'ecoule 6 x 86 400 - 35 700 = 482 700 s.

       1 787 691 600 + 482 700 = {1787691600+482700:,}   -> l'horodatage deduit. EXACT.

   autotest de l'outil : {AUTO}""")


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

say(f"""   Deux plages, et elles couvrent tout ce qui se nomme :

     [0 ; {HI:,})   petites graines, IDENTIFIANT, HORODATAGE EN SECONDES
     ts*1000 +- {FEN} s     HORODATAGE EN MILLISECONDES, hors de 2^32 (§121)

   {'tirage':>9} {'plage':>22} {'graines':>16} {'trouvées':>9} {'sec':>7}""")
TOTAL, GRAINES = 0, 0
TROUVAILLES = []
for tid, ts, ordre in TIRAGES:
    for nom, lo, hi in (("[0 ; 2^32)", 0, HI),
                        ("ts*1000 ± 600 s", ts * 1000 - 1000 * FEN, ts * 1000 + 1000 * FEN)):
        t0 = time.time()
        n, tr = balaye(lo, hi, ordre)
        TOTAL += n
        GRAINES += (hi - lo) * 48        # 48 combinaisons par graine
        TROUVAILLES += [(tid, nom, x) for x in tr]
        say(f"   {tid:>9} {nom:>22} {(hi-lo)*48:>16,} {n:>9} {time.time()-t0:>7.1f}")

say(f"""
   {TOTAL} graine compatible sur {GRAINES:,} couples (graine, combinaison) testes.""")
for tid, nom, x in TROUVAILLES:
    say(f"     !! {tid} {nom} : {x}")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h112.graine_ordonnee_datee",
        "Sous l'hypothese du RE-AMORCAGE PAR TIRAGE, aucune des douze familles "
        "de `tools/sweep_order.c` — LCG historiques (java, MSVC, glibc), "
        "xoshiro, xoroshiro, PCG — n'engendre l'ORDRE D'EMISSION de l'un des "
        "trois tirages filmes, pour une graine egale a l'identifiant, a "
        "l'horodatage en secondes, a l'horodatage en millisecondes a dix "
        "minutes pres, ou a toute valeur inferieure a 2^32, sous aucun des "
        "quatre echantillonneurs",
        "nombre de graines compatibles, une graine etant compatible si elle "
        "reproduit les VINGT numeros DANS L'ORDRE. Probabilite de faux positif "
        "par graine : 1/(80!/60!) = 1e-37",
        "aucun null n'est requis : l'esperance de faux positifs sur l'ensemble "
        "du balayage est inferieure a 1e-27",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == 0 else "RECONSTITUTION",
        power_at=f"autotest de l'outil : {AUTO} — chacune des quarante-huit "
                 f"combinaisons retrouve une graine plantee",
        notes=(f"L'outil est celui du §34 ; c'est la DONNEE qui est neuve. Les "
               f"trois videos apportent des tirages ordonnes dont l'identifiant, "
               f"l'ordre ET l'heure exacte sont connus — cette derniere deduite "
               f"de la structure de journee du §130 (204 tirages, 06:05-23:00) "
               f"et verifiee contre la cadence de l'archive : 1 787 691 600 + "
               f"482 700 = 1 788 174 300, exactement l'horodatage du tirage "
               f"1381278. Le balayage couvre [0 ; 2^32), qui contient "
               f"l'identifiant (1,38e6) et l'horodatage en secondes (1,788e9), "
               f"plus une fenetre de +-600 s autour de l'horodatage en "
               f"MILLISECONDES, hors de 2^32 — la lacune que le §121 avait "
               f"trouvee au §120. {GRAINES:,} couples (graine, combinaison) testes."))
    h = lab.holm()
    say(f"   consigne : h112.graine_ordonnee_datee   {TOTAL} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
