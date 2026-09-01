"""h113 — la graine de la JOURNÉE : ce que le sixième axe rend testable.

D'OÙ VIENT CETTE HYPOTHÈSE
===========================
Le §130 a trouvé le sixième axe du modèle de consommation : la plateforme
s'arrête 7 h 05 chaque nuit et reprend à 06:05, par blocs de 204 tirages. La
structure est mesurée sur 70 560 tirages et vérifiée TROIS FOIS hors
échantillon — les horodatages 13:05, 13:00, 13:10 des trois vidéos, et
l'identifiant 1381483 lui-même.

    SI LA PLATEFORME S'ARRÊTE SEPT HEURES PAR NUIT, LE PROCESSUS QUI TIRE
    S'ARRÊTE AUSSI. Et quand il repart, il repart de quelque part.

Une plateforme régulée doit pouvoir REJOUER ses tirages pour l'audit. Amorcer
une fois par jour sur une valeur dérivée de la date est la façon la plus
naturelle d'y arriver — et c'est une hypothèse que rien dans le dossier n'avait
testée, parce que le sixième axe n'existait pas avant hier.

CE QUI LA REND TESTABLE MAINTENANT
===================================
Il fallait trois choses, et les trois viennent d'arriver :

  1. l'ORDRE d'émission de plusieurs tirages — les trois vidéos ;
  2. leur INDEX DANS LA JOURNÉE — le §130 ;
  3. l'HEURE EXACTE du premier tirage de chaque journée — le §130 encore.

    contrôle : début du 31/08 = 1 788 149 100, et 1 788 149 100 + 84 x 300
    = 1 788 174 300, exactement l'horodatage du tirage 1381278. EXACT.

L'ATTAQUE
==========
Sous ré-amorçage quotidien, le tirage d'index m occupe les mots m*stride. Pour
chaque graine candidate on avance le générateur de m*stride mots, puis on exige
les VINGT numéros DANS L'ORDRE — et cela pour TOUS les tirages observés de la
journée à la fois. Le filtre est écrasant : (80!/60!)^k pour k tirages.

`tools/sweep_order.c --jour`, douze familles x deux échantillonneurs de
Fisher-Yates. Les échantillonneurs à rejet sont exclus du mode, et c'est
délibéré : sous rejet le nombre de mots consommés VARIE et « m*stride »
n'existe pas.

    TÉMOIN : 24/24 combinaisons retrouvent une graine plantée à partir de deux
    tirages d'index 33 et 41.

Il TESTE l'archive : il consigne au registre.
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H113_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H113_TMP", "/tmp")
PETIT = (1 << 18) if DRY else (1 << 24)
FEN_MS = 10 if DRY else 60                 # secondes autour de l'horodatage ms

# La structure de journee du §130 : 204 tirages, de 06:05 a 23:00 locale.
PARJOUR = 204
BASE_ID, BASE_TS = 1381194, 1788149100      # premier tirage du 31/08, verifie


def journees():
    """Lit draws_ordered.csv et range les tirages par JOURNEE, avec leur index
    dans la journee et l'horodatage du premier tirage du jour (§130)."""
    import csv as _csv
    import datetime as _dt
    out = {}
    chemin = os.path.join(os.path.dirname(ICI), "draws_ordered.csv")
    for r in _csv.DictReader(open(chemin, encoding="utf-8")):
        i = int(r["id"])
        off = i - BASE_ID
        j, k = off // PARJOUR, off % PARJOUR
        date = (_dt.datetime(2026, 8, 31) + _dt.timedelta(days=j)).strftime("%d/%m")
        first = BASE_ID + j * PARJOUR
        ts = BASE_TS + j * 86400
        d = out.setdefault(date, {"first": first, "ts": ts, "tirages": {}})
        d["tirages"][k] = [int(r[f"o{n}"]) for n in range(1, 21)]
    return [(d, v["first"], v["ts"], v["tirages"]) for d, v in sorted(out.items())]


STRIDES = [20] if DRY else [20, 21, 22]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_order_h113")
subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_order.c")],
               check=True, capture_output=True)
ENV = dict(os.environ, SWEEP_THREADS="8")


def balaye_jour(lo, hi, stride, tirages):
    args = [BIN, "--jour", str(lo), str(hi), str(stride), str(len(tirages))]
    for m in sorted(tirages):
        args.append(str(m))
        args += [str(n) for n in tirages[m]]
    p = subprocess.run(args, capture_output=True, text=True, timeout=7200, env=ENV)
    tot, tr = 0, []
    for l in p.stdout.split("\n"):
        if "total :" in l:
            tot = int(l.split(":")[1].split()[0])
        if "PREMIÈRE" in l:
            tr.append(l.strip())
    return tot, tr


# ==========================================================================
JOURS = journees()
rule("1. L'HYPOTHÈSE, ET D'OÙ ELLE VIENT")
# ==========================================================================

st = subprocess.run([BIN, "--jour-selftest"], capture_output=True, text=True, env=ENV)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Le §130 a trouve le sixieme axe : la plateforme s'arrete 7 h 05 chaque nuit
   et reprend a 06:05, par blocs de 204 tirages. La structure est mesuree sur
   70 560 tirages et verifiee TROIS FOIS hors echantillon.

     SI LA PLATEFORME S'ARRETE SEPT HEURES PAR NUIT, LE PROCESSUS QUI TIRE
     S'ARRETE AUSSI. Et quand il repart, il repart de quelque part.

   Une loterie regulee doit pouvoir REJOUER ses tirages pour l'audit ; amorcer
   une fois par jour sur une valeur derivee de la date est la facon la plus
   naturelle d'y arriver. Rien dans le dossier ne l'avait teste, parce que le
   sixieme axe n'existait pas avant hier.

   CE QU'IL FALLAIT, ET QUI VIENT D'ARRIVER :
     1. l'ORDRE d'emission de plusieurs tirages   les trois videos
     2. leur INDEX DANS LA JOURNEE                le §130
     3. l'HEURE du premier tirage de la journee   le §130

   {'journée':>9} {'1er tirage':>11} {'unix du 1er':>13} {'index observés':>22}""")
for date, first, u, tir in JOURS:
    say(f"   {date:>9} {first:>11} {u:>13} {str(sorted(tir)):>22}")
say(f"""
   CONTROLE : debut du 31/08 = 1 788 149 100, et + 84 x 300 = 1 788 174 300 —
   exactement l'horodatage du tirage 1381278.

   temoin du mode journee : {AUTO}""")


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

say(f"""   Sous re-amorcage quotidien, le tirage d'index m occupe les mots m*stride.
   Pour chaque graine on avance de m*stride mots puis on exige les VINGT
   numeros DANS L'ORDRE, pour TOUS les tirages observes de la journee a la
   fois. Filtre : (80!/60!)^k, soit 1e-37 par tirage.

   {'journée':>9} {'plage':>26} {'pas':>4} {'graines':>13} {'trouvées':>9} {'sec':>7}""")
TOTAL, GRAINES = 0, 0
TROUVAILLES = []
for date, first, u, tir in JOURS:
    plages = [
        ("[0 ; 2^24)", 0, PETIT),
        ("unix du jour ± 3600 s", u - 3600, u + 3600),
        ("ms du jour ± %d s" % FEN_MS, u * 1000 - 1000 * FEN_MS, u * 1000 + 1000 * FEN_MS),
        ("1er identifiant ± 10 000", first - 10000, first + 10000),
    ]
    for nom, lo, hi in plages:
        for stride in STRIDES:
            t0 = time.time()
            n, tr = balaye_jour(lo, hi, stride, tir)
            TOTAL += n
            GRAINES += (hi - lo) * 24        # 12 familles x 2 echantillonneurs FY
            TROUVAILLES += [(date, nom, stride, x) for x in tr]
            say(f"   {date:>9} {nom:>26} {stride:>4} {(hi-lo)*24:>13,} {n:>9} "
                f"{time.time()-t0:>7.1f}")

say(f"""
   {TOTAL} graine compatible sur {GRAINES:,} couples (graine, combinaison) testes.""")
for date, nom, stride, x in TROUVAILLES:
    say(f"     !! {date} {nom} pas {stride} : {x}")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h113.graine_de_journee",
        "Sous l'hypothese du RE-AMORCAGE QUOTIDIEN — le sixieme axe du §130 — "
        "aucune des douze familles de `tools/sweep_order.c`, sous aucun des deux "
        "echantillonneurs de Fisher-Yates ni aucun pas de 20 a 22, n'engendre "
        "les tirages ordonnes d'une journee pour une graine egale a "
        "l'horodatage du premier tirage du jour (en secondes ou en "
        "millisecondes), a son identifiant, ou a toute valeur inferieure a 2^24",
        "nombre de graines compatibles, une graine etant compatible si elle "
        "reproduit les VINGT numeros DANS L'ORDRE de TOUS les tirages observes "
        "de la journee, chacun a son index m via un saut de m*stride mots. "
        "Probabilite de faux positif : (80!/60!)^-k = 1e-37 par tirage",
        "aucun null n'est requis : l'esperance de faux positifs sur l'ensemble "
        "du balayage est inferieure a 1e-25",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == 0 else "RECONSTITUTION",
        power_at=(f"temoin du mode journee : {AUTO} — chacune retrouve une "
                  f"graine plantee a partir de deux tirages d'index 33 et 41, "
                  f"donc a travers un saut de 660 mots"),
        notes=(f"HYPOTHESE NEE DU SIXIEME AXE. Le §130 a montre que la "
               f"plateforme s'arrete 7 h 05 par nuit et reprend a 06:05 par "
               f"blocs de 204 tirages ; si le processus s'arrete, il repart de "
               f"quelque part, et une loterie regulee doit pouvoir REJOUER ses "
               f"tirages. Trois choses etaient necessaires pour tester cela et "
               f"les trois viennent d'arriver : l'ORDRE d'emission (les videos), "
               f"l'INDEX dans la journee et l'HEURE du premier tirage du jour "
               f"(le §130). Controle : debut du 31/08 = 1 788 149 100, plus "
               f"84 x 300 = 1 788 174 300, exactement l'horodatage du tirage "
               f"1381278. Le mode --jour a ete ajoute a tools/sweep_order.c avec "
               f"son propre temoin. {GRAINES:,} couples testes."))
    h = lab.holm()
    say(f"   consigne : h113.graine_de_journee   {TOTAL} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
