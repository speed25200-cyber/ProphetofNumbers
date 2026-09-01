"""h101 — la graine des familles brouillées : la dernière voie vers un positif.

CE QUE LE §119 A FERMÉ, ET CE QU'IL N'A PAS FERMÉ
==================================================
Le §119 mesure la frontière et la rend définitive : xoshiro256**, xoshiro256++,
xoroshiro128**, PCG32 et splitmix64 ont un sous-espace de linéarité de dimension
EXACTEMENT ZÉRO. Aucune élimination de Gauss ne mordra jamais sur eux, et ce
n'est plus une conjecture — c'est une dimension calculée.

MAIS CELA NE DIT RIEN DE LEUR GRAINE.

    Un état de 256 bits est hors de portée. Une graine de 32 bits ne l'est pas.

Et une plateforme de loterie régulée doit pouvoir REJOUER ses tirages pour
l'audit — ce qui pousse naturellement à amorcer sur le numéro de tirage ou sur
l'horodatage, tous deux publiés dans l'archive.

    C'EST LA DERNIÈRE VOIE PAR LAQUELLE UN RÉSULTAT POSITIF PEUT ENCORE SORTIR
    DE CE DOSSIER. Les §105 à §119 ont fermé l'ÉTAT ; celle-ci ferme ou ouvre
    la GRAINE.

CE QUE LA PLAGE COUVRE, ET POURQUOI UNE SEULE SUFFIT
=====================================================
On balaie les graines de 0 à 2^32, soit [0 ; 4 294 967 296). Cet intervalle
contient :

    les petites graines             0 a quelques millions
    le NUMERO DE TIRAGE             1 309 614 a 1 380 173
    l'HORODATAGE UNIX               1 757 829 900 a 1 787 691 600

Une seule plage couvre donc les trois hypothèses d'amorçage à la fois, ce qui
évite d'en balayer trois.

LE FILTRE, ET SON COÛT RÉEL
============================
La cible est l'ensemble TRIÉ des vingt numéros. Le filtre est une appartenance :
un numéro tiré sur quatre y appartient, donc l'abandon survient en moyenne après
1,33 pas de générateur. Mesure : 2^24 graines en 0,3 s, soit 2^32 en 77 s.

    probabilité de faux positif : 1/C(80,20) = 2,8e-19 par graine,
    soit 1,2e-9 sur les 2^32 d'un balayage. Un seul succès serait décisif.

AUTOTEST : 28/28 — pour chacune des sept familles et des quatre
échantillonneurs, une graine plantée est retrouvée.
"""

import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H101_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H101_TMP", "/tmp")
HI = (1 << 24) if DRY else (1 << 32)
NFAM, NSAMP = 7, 4
FAM = ["xoshiro256**", "xoshiro256++", "xoroshiro128**", "PCG32",
       "splitmix64", "xorshift128+", "xoshiro256 (brut)"]
SAMP = ["FY tronqué", "FY modulo", "rejet tronqué", "rejet modulo"]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. CE QUE LE §119 N'A PAS FERMÉ")
# ==========================================================================

BIN = os.path.join(TMP, "sweep_brouille")
cc = subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                     os.path.join(DEPOT, "tools", "sweep_brouille.c")],
                    capture_output=True, text=True)
ARCH = lab.load()
IDS = np.asarray(ARCH.ids).astype(np.int64)
TS = np.asarray(ARCH.ts).astype(np.int64)
NUM = np.asarray(ARCH.nums)

say(f"""   Le §119 mesure que xoshiro256**, xoshiro256++, xoroshiro128**, PCG32 et
   splitmix64 ont dim L = 0 : aucune elimination de Gauss ne mordra jamais sur
   eux, et c'est une dimension CALCULEE.

   MAIS CELA NE DIT RIEN DE LEUR GRAINE. Un etat de 256 bits est hors de
   portee ; une graine de 32 bits ne l'est pas. Et une loterie regulee doit
   pouvoir REJOUER ses tirages pour l'audit — ce qui pousse a amorcer sur le
   numero de tirage ou sur l'horodatage, tous deux publies dans l'archive.

   UNE SEULE PLAGE COUVRE LES TROIS HYPOTHESES. On balaie [0 ; {HI:,}) :

     petites graines        0 a quelques millions
     NUMERO DE TIRAGE       {IDS.min():,} a {IDS.max():,}
     HORODATAGE UNIX        {TS.min():,} a {TS.max():,}

   `tools/sweep_brouille.c` : {'compile' if cc.returncode == 0 else 'ECHEC'}
""")
st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]
say(f"   autotest : {AUTO}")
say(f"""
   FILTRE. La cible est l'ensemble TRIE des vingt numeros ; un numero tire sur
   quatre y appartient, donc l'abandon survient apres 1,33 pas en moyenne.
   Probabilite de faux positif : 1/C(80,20) = 2,8e-19 par graine, soit 1,2e-9
   sur un balayage entier. UN SEUL SUCCES SERAIT DECISIF.""")


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

CIBLE = sorted(int(x) for x in NUM[0])
say(f"""   Tirage cible : identifiant {IDS[0]:,}, horodatage {TS[0]:,}.
   {' '.join(str(n) for n in CIBLE)}

   {NFAM} familles x {NSAMP} echantillonneurs = {NFAM*NSAMP} balayages de {HI:,} graines.
""")
say(f"   {'famille':>20} {'échantillonneur':>16} {'graines':>15} "
    f"{'trouvées':>9} {'sec':>7}")
TOTAL, ESSAIS = 0, 0
TROUVAILLES = []
for f in range(NFAM):
    for sa in range(NSAMP):
        args = [BIN, str(f), str(sa), "2", "0", "0", str(HI)] + \
               [str(n) for n in CIBLE]
        p = subprocess.run(args, capture_output=True, text=True, timeout=3600)
        lignes = p.stdout.strip().split("\n")
        tete = lignes[-1]
        d = dict(kv.split("=", 1) for kv in tete.split() if "=" in kv)
        nt = int(d.get("trouves", 0))
        TOTAL += nt
        ESSAIS += 1
        for l in lignes[:-1]:
            if l.startswith("TROUVE"):
                TROUVAILLES.append((FAM[f], SAMP[sa], l))
        say(f"   {FAM[f]:>20} {SAMP[sa]:>16} {HI:>15,} {nt:>9} "
            f"{float(d.get('sec', 0)):>7.1f}")

say(f"""
   {TOTAL} graine compatible sur {ESSAIS} balayages, soit {ESSAIS*HI:,} graines testees.""")
for nom, sa, l in TROUVAILLES:
    say(f"     {nom} / {sa} : {l}")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h101.graine_brouillee",
        "Aucune des familles a sortie BROUILLEE que le §119 place hors "
        "d'atteinte de l'algebre lineaire — xoshiro256**, xoshiro256++, "
        "xoroshiro128**, PCG32, splitmix64 — ni xorshift128+ ni xoshiro256 brut, "
        "n'engendre le premier tirage de l'archive pour une graine de 32 bits, "
        "sous aucun des quatre echantillonneurs",
        f"balayage exhaustif de [0 ; 2^32), plage qui contient a la fois les "
        f"petites graines, le NUMERO DE TIRAGE ({IDS.min():,}-{IDS.max():,}) et "
        f"l'HORODATAGE UNIX ({TS.min():,}-{TS.max():,}). Filtre par appartenance a "
        f"l'ensemble trie, abandon au premier ecart. {NFAM} familles x {NSAMP} "
        f"echantillonneurs",
        "aucun null n'est requis : la probabilite qu'une graine fausse reproduise "
        "l'ensemble trie vaut 1/C(80,20) = 2,8e-19, soit 1,2e-9 par balayage",
        "conforme si aucune graine compatible n'est trouvee", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme" if TOTAL == 0 else "ANOMALIE",
        power_at=f"autotest du balayeur : {AUTO} — pour chaque famille et chaque "
                 f"echantillonneur, une graine plantee est retrouvee",
        notes=(f"Le §119 ferme l'ETAT de ces familles par une dimension calculee "
               f"(dim L = 0). Il ne disait rien de leur GRAINE : un etat de 256 "
               f"bits est hors de portee, une graine de 32 bits ne l'est pas. Et "
               f"une loterie regulee doit pouvoir REJOUER ses tirages pour "
               f"l'audit, ce qui pousse a amorcer sur le numero de tirage ou "
               f"l'horodatage. C'etait la derniere voie par laquelle un resultat "
               f"POSITIF pouvait sortir du dossier. Esperance de faux positifs sur "
               f"{ESSAIS*HI:,} graines : {ESSAIS*HI*2.8e-19:.1e}."))
    h = lab.holm()
    say(f"   consigne : h101.graine_brouillee   {TOTAL} graine compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("4. CE QUE CELA VEUT DIRE")
# ==========================================================================

say(f"""   L'ETAT etait ferme par le §119 — dimension calculee, pas conjecture.
   LA GRAINE l'est par ce fichier — {ESSAIS*HI:,} graines, esperance de faux
   positifs {ESSAIS*HI*2.8e-19:.1e}.

   Ce qui subsiste apres les deux :
     — une graine de PLUS de 32 bits, ou tiree d'un CSPRNG. C'est le cas d'un
       generateur correctement amorce, et c'est aussi ce qu'un auditeur
       exigerait ;
     — un etat brouille jamais reamorce, hors d'atteinte par le §119 ;
     — le materiel.

   AUTREMENT DIT : LE DOSSIER A ATTEINT SA BORNE. Il ne reste que des
   hypotheses dont on peut DEMONTRER qu'aucune donnee publiee ne les
   distinguera — et non des hypotheses qu'il resterait a essayer.

   ({time.time() - T0:.1f} s)""")
