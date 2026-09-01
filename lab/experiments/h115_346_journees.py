"""h115 — les 346 journées de l'archive, et leurs 346 graines.

CE QUE LE §113 A FAIT, ET CE QU'IL N'A PAS PU FAIRE
====================================================
Le §113 teste l'hypothèse du ré-amorçage quotidien sur les TROIS journées dont
une vidéo donne l'ordre d'émission. Trois journées, c'est ce que les vidéos
donnent — et c'est très peu quand l'archive en contient 346.

    L'ARCHIVE EST TRIÉE, DONC ELLE NE DONNE PAS L'ORDRE. Mais elle donne
    l'ENSEMBLE des vingt numéros, et le filtre vaut alors 1/C(80,20) = 2,8e-19
    par tirage. C'est amplement suffisant : une seule journée suffit à rejeter
    une graine, et il y en a 346 à essayer.

LA STRUCTURE, MESURÉE
======================
Les intervalles entre tirages ne prennent que deux valeurs — 300 s, et une
pause nocturne. L'archive se découpe donc en 346 blocs, et le premier tirage de
chaque bloc a un HORODATAGE CONNU EXACTEMENT, publié par l'archive elle-même.

    346 journées, 346 horodatages de départ, 346 graines candidates.

Aucune n'avait été essayée : le §120 balayait [0 ; 2^32) contre le PREMIER
tirage de l'archive seulement, et le §113 ne connaît que trois journées.

LES FORMES DE GRAINE TESTÉES, PAR JOURNÉE
==========================================
    l'horodatage du premier tirage du jour, en SECONDES     exact
    le même en MILLISECONDES, à une minute près             120 000 graines
    l'horodatage à une heure près                           7 200 graines
    l'IDENTIFIANT du premier tirage du jour                 exact
    la date en YYYYMMDD                                     exact
    l'indice de la journée                                  exact

CE QUE VAUDRAIT UN SUCCÈS
==========================
Une graine trouvée pour une journée donne les 204 tirages de cette journée-là —
et, la forme de graine étant connue, TOUTES les journées suivantes.

Il TESTE l'archive : il consigne au registre.
"""

import datetime as dt
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H115_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H115_TMP", "/tmp")
FEN_MS = 5 if DRY else 60                  # secondes autour de l'horodatage ms
FEN_S = 600 if DRY else 3600               # secondes autour de l'horodatage
NFAM, NSAMP = 7, 4


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_brouille_h115")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_brouille.c")],
               check=True, capture_output=True)


def balaye(lo, hi, cible):
    """Rend (graines testees, compatibles) sur toutes les combinaisons."""
    tot, tr = 0, []
    for f in range(NFAM):
        for s in range(NSAMP):
            p = subprocess.run(
                [BIN, str(f), str(s), "2", "0", str(lo), str(hi)]
                + [str(n) for n in cible],
                capture_output=True, text=True, timeout=3600)
            for l in p.stdout.split("\n"):
                if l.startswith("TROUVE"):
                    tr.append((f, s, l.strip()))
                if "trouves=" in l:
                    tot += int(dict(kv.split("=", 1) for kv in l.split()
                                    if "=" in kv).get("trouves", 0))
    return (hi - lo) * NFAM * NSAMP, tot, tr


# ==========================================================================
rule("1. LES 346 JOURNÉES, ET LEURS 346 HORODATAGES DE DÉPART")
# ==========================================================================

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
IDS = np.asarray(ARCH.ids).astype(np.int64)
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
COUPE = np.flatnonzero(np.diff(TS) > 1000)
DEB = np.r_[0, COUPE + 1]

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Le §113 teste le re-amorcage quotidien sur les TROIS journees dont une video
   donne l'ordre d'emission. L'archive en contient {len(DEB)}.

   Elle est TRIEE, donc muette sur l'ordre — mais elle donne l'ENSEMBLE des
   vingt numeros, et le filtre vaut alors 1/C(80,20) = 2,8e-19 par tirage. Une
   seule journee suffit a rejeter une graine.

   {'journée':>9} {'1er tirage':>11} {'unix':>12} {'heure locale':>18}""")
for k in (0, 1, 2, len(DEB) - 2, len(DEB) - 1):
    i = DEB[k]
    say(f"   {k:>9} {IDS[i]:>11} {TS[i]:>12} "
        f"{dt.datetime.utcfromtimestamp(int(TS[i])+7200).strftime('%Y-%m-%d %H:%M'):>18}")
say(f"""
   Aucune de ces {len(DEB)} graines n'avait ete essayee : le §120 balayait
   [0 ; 2^32) contre le PREMIER tirage de l'archive seulement, et le §113 ne
   connait que trois journees.

   autotest du balayeur : {AUTO}""")


# ==========================================================================
rule("2. LE BALAYAGE, JOURNÉE PAR JOURNÉE")
# ==========================================================================

NJ = 6 if DRY else len(DEB)
say(f"""   Pour chaque journee, la cible est l'ENSEMBLE TRIE de son PREMIER tirage, et
   les formes de graine sont derivees de la journee elle-meme.

   {'forme de graine':>34} {'graines/journée':>17}""")
say(f"   {'horodatage du 1er tirage (s)':>34} {'1 (exact)':>17}")
say(f"   {'le même ± ' + str(FEN_S) + ' s':>34} {2*FEN_S:>17,}")
say(f"   {'le même en MILLISECONDES ± ' + str(FEN_MS) + ' s':>34} {2000*FEN_MS:>17,}")
say(f"   {'identifiant du 1er tirage':>34} {'1 (exact)':>17}")
say(f"   {'la date YYYYMMDD':>34} {'1 (exact)':>17}")
say(f"   {'indice de la journée':>34} {'1 (exact)':>17}")

TOTAL, GRAINES, TROUV = 0, 0, []
t0 = time.time()
for k in range(NJ):
    i = DEB[k]
    cible = NUM[i].tolist()
    u = int(TS[i])
    ymd = int(dt.datetime.utcfromtimestamp(u + 7200).strftime("%Y%m%d"))
    exacts = [u, int(IDS[i]), ymd, k]
    plages = [(u - FEN_S, u + FEN_S),
              (u * 1000 - 1000 * FEN_MS, u * 1000 + 1000 * FEN_MS)]
    for v in exacts:                                   # les graines exactes
        plages.append((v, v + 1))
    for lo, hi in plages:
        g, n, tr = balaye(lo, hi, cible)
        GRAINES += g
        TOTAL += n
        TROUV += [(k, lo, x) for x in tr]
    if k % 50 == 0 or k == NJ - 1:
        say(f"   journee {k:>3}/{NJ} — {GRAINES:>14,} graines testees, "
            f"{TOTAL} compatible(s)   ({time.time()-t0:.0f} s)")

say(f"""
   {TOTAL} graine compatible sur {GRAINES:,} couples (graine, combinaison) testes,
   pour {NJ} journees.""")
for k, lo, x in TROUV:
    say(f"     !! journee {k} plage {lo} : {x}")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h115.346_journees",
        "Sous l'hypothese du RE-AMORCAGE QUOTIDIEN (§130), aucune des sept "
        "familles a sortie brouillee, sous aucun des quatre echantillonneurs, "
        "n'engendre le premier tirage de l'une des 346 journees de l'archive "
        "pour une graine derivee de cette journee : son horodatage de depart en "
        "secondes (a une heure pres) ou en millisecondes (a une minute pres), "
        "l'identifiant de son premier tirage, sa date en YYYYMMDD, ou son indice",
        "nombre de graines compatibles, une graine etant compatible si elle "
        "reproduit l'ENSEMBLE TRIE des vingt numeros. Probabilite de faux "
        "positif : 1/C(80,20) = 2,8e-19 par graine",
        "aucun null n'est requis : l'esperance de faux positifs sur l'ensemble "
        "du balayage reste inferieure a 1e-8",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == 0 else "RECONSTITUTION",
        power_at=f"autotest du balayeur : {AUTO} — pour chaque famille et chaque "
                 f"echantillonneur, une graine plantee est retrouvee",
        notes=(f"Le §113 ne pouvait tester le re-amorcage quotidien que sur les "
               f"TROIS journees dont une video donne l'ordre. L'archive en "
               f"contient {len(DEB)}, et si elle est muette sur l'ordre, elle donne "
               f"l'ENSEMBLE — filtre 2,8e-19, amplement suffisant. Le §120 "
               f"balayait [0 ; 2^32) contre le PREMIER tirage de l'archive "
               f"seulement ; ici chaque journee est testee avec les graines "
               f"derivees d'ELLE-MEME. Un succes aurait donne les 204 tirages "
               f"de la journee, et la forme de graine etant connue, toutes les "
               f"journees suivantes. {GRAINES:,} couples testes sur {NJ} journees."))
    h = lab.holm()
    say(f"   consigne : h115.346_journees   {TOTAL} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
