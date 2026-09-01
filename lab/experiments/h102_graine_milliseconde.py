"""h102 — la graine en millisecondes : la lacune du §120.

LA LACUNE
==========
Le §120 balaie [0 ; 2^32), et affirme que cette plage couvre « les trois
hypotheses d'amorçage » — petites graines, numero de tirage, horodatage unix.

C'EST VRAI POUR L'HORODATAGE EN SECONDES, ET FAUX POUR CELUI EN MILLISECONDES.

    2^32                 = 4 294 967 296
    horodatage secondes  = 1 757 829 900       dans la plage
    horodatage MS        = 1 757 829 900 000   HORS de la plage, x409

Or `Date.now()` en JavaScript, `System.currentTimeMillis()` en Java et
`microtime()` en PHP rendent tous des millisecondes ou mieux. Une plateforme
qui amorce sur l'horloge le fait donc, le plus souvent, en dehors de la plage
que le §120 a balayee.

CE QUI RATTRAPE LA LACUNE SANS COUTER CHER
===========================================
L'archive publie l'horodatage A LA SECONDE. La partie milliseconde est donc
inconnue sur trois chiffres seulement, et l'incertitude sur l'instant reel du
tirage se compte en minutes, pas en annees :

    graine = ts * 1000 + m,     m dans une fenetre de +- FENETRE secondes

Le balayage ne porte donc que sur 2 000 * FENETRE graines par tirage — contre
2^32 au §120 — et il atteint une plage que le §120 ne pouvait pas voir.

ON LE FAIT SUR PLUSIEURS TIRAGES, et c'est le point : sous l'hypothese du
re-amorcage horaire, CHAQUE tirage a sa propre graine. Un balayage sur dix
tirages est donc dix chances independantes, pas une confirmation.
"""

import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H102_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H102_TMP", "/tmp")
FENETRE = 60 if DRY else 600           # secondes de part et d'autre
NTIR = 3 if DRY else 10                # tirages balayes
NFAM, NSAMP = 7, 4
FAM = ["xoshiro256**", "xoshiro256++", "xoroshiro128**", "PCG32",
       "splitmix64", "xorshift128+", "xoshiro256 (brut)"]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_brouille102")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_brouille.c")],
               check=True, capture_output=True)

ARCH = lab.load()
TS = np.asarray(ARCH.ts).astype(np.int64)
NUM = np.asarray(ARCH.nums)

# ==========================================================================
rule("1. LA LACUNE DU §120")
# ==========================================================================

say(f"""   Le §120 balaie [0 ; 2^32) et affirme couvrir « les trois hypotheses
   d'amorcage ». C'est vrai pour l'horodatage en SECONDES et faux pour celui en
   MILLISECONDES :

     2^32                 = {1 << 32:,}
     horodatage secondes  = {TS[0]:,}        dans la plage
     horodatage MS        = {TS[0]*1000:,}    HORS de la plage, x{TS[0]*1000/(1<<32):.0f}

   Or `Date.now()` en JavaScript, `System.currentTimeMillis()` en Java et
   `microtime()` en PHP rendent tous des millisecondes ou mieux. Une plateforme
   qui amorce sur l'horloge sort donc, le plus souvent, de la plage du §120.

   CE QUI RATTRAPE LA LACUNE SANS COUTER CHER. L'archive publie l'horodatage A
   LA SECONDE : la partie milliseconde est inconnue sur trois chiffres, et
   l'incertitude sur l'instant reel se compte en minutes.

       graine = ts * 1000 + m,   m dans +- {FENETRE} s

   soit {2000*FENETRE:,} graines par tirage — contre 2^32 au §120 — dans une plage que
   le §120 ne pouvait pas voir.

   ET ON LE FAIT SUR {NTIR} TIRAGES : sous l'hypothese du re-amorcage horaire,
   CHAQUE tirage a sa propre graine. Dix tirages sont dix chances
   INDEPENDANTES, pas une confirmation.""")

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]
say(f"\n   autotest du balayeur : {AUTO}")


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

say(f"   {'tirage':>8} {'horodatage':>14} {'graines':>14} {'trouvées':>9} {'sec':>7}")
TOTAL, GRAINES = 0, 0
for d in range(NTIR):
    tt = time.time()
    cible = sorted(int(x) for x in NUM[d])
    lo = TS[d] * 1000 - 1000 * FENETRE
    hi = TS[d] * 1000 + 1000 * FENETRE
    nt = 0
    for f in range(NFAM):
        for sa in range(NSAMP):
            args = [BIN, str(f), str(sa), "2", "0", str(lo), str(hi)] + \
                   [str(n) for n in cible]
            p = subprocess.run(args, capture_output=True, text=True, timeout=3600)
            tete = p.stdout.strip().split("\n")[-1]
            dd = dict(kv.split("=", 1) for kv in tete.split() if "=" in kv)
            nt += int(dd.get("trouves", 0))
            GRAINES += hi - lo
            for l in p.stdout.split("\n"):
                if l.startswith("TROUVE"):
                    say(f"     !! {FAM[f]} / echantillonneur {sa} : {l}")
    TOTAL += nt
    say(f"   {d:>8} {TS[d]:>14,} {(hi-lo)*NFAM*NSAMP:>14,} {nt:>9} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} graine compatible sur {GRAINES:,} testees.""")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h102.graine_milliseconde",
        "Aucune des sept familles du §120 n'engendre l'un des dix premiers "
        "tirages de l'archive pour une graine egale a l'horodatage EN "
        "MILLISECONDES, a dix minutes pres — la plage que le balayage [0 ; 2^32) "
        "du §120 ne pouvait pas atteindre",
        f"graine = ts*1000 + m avec m dans +-{FENETRE} s, soit {2000*FENETRE:,} graines par "
        f"tirage et par combinaison. {NFAM} familles x {NSAMP} echantillonneurs x "
        f"{NTIR} tirages. Sous l'hypothese du re-amorcage horaire chaque tirage a sa "
        f"propre graine : les {NTIR} tirages sont des chances INDEPENDANTES",
        "aucun null n'est requis : la probabilite qu'une graine fausse reproduise "
        "l'ensemble trie vaut 1/C(80,20) = 2,8e-19",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme" if TOTAL == 0 else "ANOMALIE",
        power_at=f"autotest du balayeur : {AUTO}",
        notes=(f"Le §120 affirmait que [0 ; 2^32) couvrait « les trois hypotheses "
               f"d'amorcage ». C'etait vrai pour l'horodatage en SECONDES et faux "
               f"pour celui en MILLISECONDES, qui vaut {TS[0]*1000:,} — soit 409 fois "
               f"la borne du balayage. Or Date.now(), currentTimeMillis() et "
               f"microtime() rendent tous des millisecondes. La lacune se rattrape "
               f"a bas cout parce que l'archive publie l'horodatage A LA SECONDE : "
               f"trois chiffres inconnus, et une incertitude qui se compte en "
               f"minutes. {GRAINES:,} graines testees."))
    h = lab.holm()
    say(f"   consigne : h102.graine_milliseconde   {TOTAL} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("4. CE QUE CELA CORRIGE")
# ==========================================================================

say(f"""   UNE AFFIRMATION DE PORTEE, PAS UN RESULTAT. Le §120 ne s'est pas trompe
   dans ses mesures : ses 120 milliards de graines sont bien testees et bien
   nulles. Il s'est trompe dans la PHRASE qui les resume — « une seule plage
   couvre les trois hypotheses » — parce que l'horodatage a deux ecritures et
   qu'une seule tient dans 2^32.

   C'est la meme faute que le §101 avait trouvee dans la carte de couverture :
   une conclusion RECOPIEE plus largement que sa source. Elle se reproduit
   volontiers, et c'est pourquoi le dossier la traque.

   ({time.time() - T0:.1f} s)""")
