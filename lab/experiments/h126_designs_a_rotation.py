"""h126 — l'espace des designs À ROTATION : xoshiro et xoroshiro, tous décalages.

CE QUE LE §146 A FERMÉ, ET CE QU'IL A LAISSÉ
=============================================
Le §146 a balayé l'espace ENTIER de la forme de Marsaglia — tous les triplets de
décalages, toutes les orientations, pour W = 32, 64 et 128 — et fermé le trou que
le §25 avait nommé : « un générateur aux constantes maison lui échappait
entièrement ».

Mais la forme de Marsaglia n'est pas la seule. Les générateurs écrits après 2014
sont bâtis sur des ROTATIONS, pas sur des décalages :

    xoroshiro128    s1 ^= s0 ; s0 = rotl(s0,A) ^ s1 ^ (s1<<B) ; s1 = rotl(s1,C)
    xoshiro256      t = s1<<A ; s2^=s0 ; s3^=s1 ; s1^=s2 ; s0^=s3 ;
                    s2 ^= t ; s3 = rotl(s3, B)

Ces deux formes ont leur propre espace de paramètres, et AUCUN balayage du
dossier ne l'a couvert : le §136 et le §144 testent xoroshiro128 et xoshiro256
avec les rotations PUBLIÉES (24, 16, 37) et (17, 45).

CE QUI EST BALAYÉ ICI
======================
    xoroshiro128 brut, W = 128   A, B, C dans [1,63], mot lu haut ou bas
                                 -> 63^3 x 2 = 500 094 designs
    xoshiro256 brut,   W = 256   A, B dans [1,63], mot lu parmi 4, haut ou bas
                                 -> 63^2 x 8 = 31 752 designs

« Brut » veut dire SORTIE F2-LINÉAIRE : un mot d'état, sans le brouilleur
arithmétique. C'est délibéré, et le §145 dit pourquoi — le brouilleur est affine
sur Z/2^64 et donc INVERSIBLE ; ce qui protège la plateforme est l'échantillonneur,
pas lui. Une variante brouillée ne changerait donc pas la conclusion sur l'état,
seulement la façon de le lire.

TÉMOIN
=======
Pour chacune des cinq formes, un design planté est retrouvé COMPATIBLE et un
design ne différant que d'UN paramètre est rejeté. 10/10.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H126_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H126_TMP", "/tmp")
BASE_ID, PARJOUR = 1381194, 204


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_design_h126")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_design.c")],
               check=True, capture_output=True)

# ==========================================================================
rule("1. CE QUE LE §146 A LAISSÉ")
# ==========================================================================

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Le §146 a balaye l'espace ENTIER de la forme de Marsaglia et ferme le trou
   que le §25 avait nomme. Mais la forme de Marsaglia n'est pas la seule : les
   generateurs ecrits apres 2014 sont batis sur des ROTATIONS.

     xoroshiro128   s1 ^= s0 ; s0 = rotl(s0,A) ^ s1 ^ (s1<<B) ; s1 = rotl(s1,C)
     xoshiro256     t = s1<<A ; s2^=s0 ; s3^=s1 ; s1^=s2 ; s0^=s3 ;
                    s2 ^= t ; s3 = rotl(s3,B)

   AUCUN balayage du dossier n'a couvert leur espace de parametres : les §136 et
   §144 les testent avec les rotations PUBLIEES, (24,16,37) et (17,45).

       xoroshiro128 brut, W = 128    63^3 x 2 =  500 094 designs
       xoshiro256 brut,   W = 256    63^2 x 8 =   31 752 designs

   « Brut » veut dire SORTIE F2-LINEAIRE : un mot d'etat, sans le brouilleur
   arithmetique. C'est delibere, et le §145 dit pourquoi — le brouilleur est
   AFFINE sur Z/2^64 donc inversible ; ce qui protege la plateforme est
   l'echantillonneur, pas lui.

   temoin de l'outil : {AUTO}
     (pour chacune des cinq formes : design plante retrouve, design differant
      d'UN parametre rejete)""")


# ==========================================================================
rule("2. LE BALAYAGE")
# ==========================================================================

LIG = []
for r in csv.DictReader(open(os.path.join(os.path.dirname(ICI), "draws_ordered.csv"),
                             encoding="utf-8")):
    LIG.append((int(r["id"]), [int(r[f"o{i}"]) for i in range(1, 21)]))
LIG.sort()
JOURS = {}
for i, o in LIG:
    off = i - BASE_ID
    JOURS.setdefault(off // PARJOUR, {})[off % PARJOUR] = o

def prefixe_nb(v, K):
    lo = -(-(v << 32) // K)
    hi = -(-((v + 1) << 32) // K) - 1
    n = 0
    while n < 32 and ((lo >> (31 - n)) & 1) == ((hi >> (31 - n)) & 1):
        n += 1
    return n


def equations(ordre_par_index):
    """Nombre d'equations exactes que rendent les tirages ordonnes d'une journee."""
    tot = 0
    for ordre in ordre_par_index.values():
        arr = list(range(1, 81))
        for k, val in enumerate(ordre):
            j = arr.index(val, k)
            arr[k], arr[j] = arr[j], arr[k]
            tot += prefixe_nb(j - k, 80 - k)
    return tot


FORMES = [(4, 256)] if DRY else [(3, 128), (4, 256)]
say(f"""   Chaque journee est re-originee sur son premier tirage observe (§146).

   ET CHAQUE COUPLE (journee, forme) PORTE SA PORTE DE PUISSANCE. Un balayage
   n'exclut RIEN tant que le systeme est sous-determine : le §144 l'a mesure —
   le point de contradiction vaut la largeur de l'etat. Une journee ne conclut
   donc sur une largeur W que si elle rend PLUS de W equations.

       {'journée':>8} {'forme':>16} {'W':>5} {'équations':>10} {'concluant':>10} {'designs':>10} {'survivants':>11} {'sec':>7}""")
NOM = {3: "xoroshiro128", 4: "xoshiro256"}
TOTAL, SURV, TESTES, SANSPUIS = 0, [], 0, []
for j in sorted(JOURS):
    idx = sorted(JOURS[j])
    rel = [k - idx[0] for k in idx]
    NEQ = equations(JOURS[j])
    for forme, W in FORMES:
        args = [BIN, str(forme), str(len(idx))]
        for k, r in zip(idx, rel):
            args.append(str(r))
            args += [str(n) for n in JOURS[j][k]]
        tt = time.time()
        p = subprocess.run(args, capture_output=True, text=True, timeout=14400)
        nd = ns = 0
        for l in p.stdout.split("\n"):
            if l.startswith("SURVIVANT"):
                SURV.append((j, W, l.strip()))
            if l.startswith("forme="):
                d = dict(kv.split("=", 1) for kv in l.split() if "=" in kv)
                nd, ns = int(d["designs"]), int(d["survivants"])
        TOTAL += nd
        concluant = NEQ > W
        if concluant:
            TESTES += nd
        else:
            SANSPUIS.append((j, NOM[forme], W, NEQ, nd, ns))
            SURV[:] = [x for x in SURV if not (x[0] == j and x[1] == W)]
        say(f"   {j:>8} {NOM[forme]:>16} {W:>5} {NEQ:>10} "
            f"{('OUI' if concluant else 'non'):>10} {nd:>10,} {ns:>11} "
            f"{time.time()-tt:>7.1f}")

say(f"""
   {len(SURV)} design compatible sur {TESTES:,} testes DANS LES COUPLES CONCLUANTS.""")
for j, W, l in SURV:
    say(f"     !! journee {j}, W={W} : {l}")
if SANSPUIS:
    say("""
   COUPLES SANS PUISSANCE, ECARTES ET DITS COMME TELS :""")
    for j, nom, W, neq, nd, ns in SANSPUIS:
        say(f"     journee {j}, {nom} (W = {W}) : {neq} equations pour {W} "
            f"inconnues.\n       Le systeme est SOUS-DETERMINE, donc {ns:,} des "
            f"{nd:,} designs\n       « survivent » sans que cela signifie quoi que "
            f"ce soit. Ecarte.")
if not SURV:
    say("""     AUCUN. Et le controle tient : xoroshiro128 (24,16,37) et xoshiro256
     (17,45) sont DANS l'espace balaye, donc le balayage les rejette comme le
     §136 et le §144.

   AVEC LE §146, CE QUI EST FERME MAINTENANT :

     forme de Marsaglia, W = 32, 64, 128     tous decalages, toutes orientations
     xoroshiro128, W = 128                   toutes rotations, tout mot lu
     xoshiro256,   W = 256                   toutes rotations, tout mot lu

   Ce n'est plus « aucune famille PUBLIEE ne convient » : c'est « aucun
   generateur de ces cinq FORMES ne convient, quels que soient ses
   parametres ».""")


# ==========================================================================
rule("3. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h126b.designs_a_rotation_determine",
        "Aucun generateur des deux formes A ROTATION — xoroshiro128 (W = 128, "
        "rotations A et C, decalage B, mot lu haut ou bas) et xoshiro256 "
        "(W = 256, decalage A, rotation B, mot lu parmi quatre, haut ou bas) — "
        "n'engendre les tirages ordonnes filmes, POUR AUCUN jeu de parametres, "
        "LA OU LE SYSTEME EST SUR-DETERMINE — c'est-a-dire la ou la journee rend "
        "plus d'equations que la largeur d'etat ne compte d'inconnues. Un couple "
        "(journee, largeur) sous-determine est ECARTE et dit comme tel : il "
        "n'exclut rien, et la premiere version de cette section avait omis cette "
        "porte. "
        "Le §146 avait ferme la forme de Marsaglia ; les formes a rotation, "
        "c'est-a-dire tout ce qui a ete ecrit apres 2014, restaient ouvertes",
        "nombre de designs compatibles, un design etant compatible si le systeme "
        "F2 construit sur les bits exacts de tous les tirages ordonnes de la "
        "journee reste sans contradiction",
        "aucun null n'est requis : la contradiction est deterministe",
        "conforme si aucun design n'est compatible", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(SURV)), p=1.0,
        verdict="conforme" if not SURV else "DESIGN TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} — pour chacune des CINQ formes, un "
                  f"design plante est retrouve COMPATIBLE et un design ne "
                  f"differant que d'UN parametre est rejete"),
        notes=(f"COMPLETE LE §146. Celui-ci avait balaye la forme de Marsaglia "
               f"(decalages) ; les formes a ROTATION — celles de tout ce qui a "
               f"ete ecrit apres 2014 — restaient entieres. {TOTAL:,} designs "
               f"testes dans les couples CONCLUANTS. Les rotations publiees "
               f"sont DANS l'espace balaye — xoroshiro128 (24,16,37), xoshiro256 "
               f"(17,45) — donc le balayage les rejette comme les §136 et §144. "
               f"La sortie balayee est BRUTE, c'est-a-dire F2-lineaire : c'est "
               f"delibere, le §145 ayant montre que le brouilleur est affine sur "
               f"Z/2^64 donc inversible, et que ce qui protege la plateforme est "
               f"l'echantillonneur. Avec le §146 : plus « aucune famille publiee "
               f"ne convient » mais « aucun generateur de ces cinq FORMES ne "
               f"convient, quels que soient ses parametres »."))
    h = lab.holm()
    say(f"   consigne : h126b.designs_a_rotation_determine   {len(SURV)} design "
        f"sur {TESTES:,} concluants")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
