"""h125 — balayer l'ESPACE DES DESIGNS, et non le catalogue publié.

LE TROU QUE LE §25 A NOMMÉ LUI-MÊME
====================================
Le §25 écrit, à propos de l'attaque par réseau du §24 :

    « h11 laissait une faille béante : il fallait ÉNUMÉRER des constantes
      publiées. Un générateur aux constantes maison lui échappait
      entièrement. »

Le §25 a fermé ce trou POUR LES LCG, en calculant (a, c) au lieu de les deviner.
Pour les générateurs F2-LINÉAIRES, IL EST RESTÉ OUVERT. Tous les balayages du
dossier — §34, §110, §136, §144 — testent xorshift32/64/128, taus88, LFSR113,
WELL512a : c'est-à-dire des DÉCALAGES PUBLIÉS.

    Un xorshift maison dont les décalages (13, 17, 5) seraient remplacés par
    (11, 19, 3) leur échappe À TOUS. Et il n'y a aucune raison qu'une
    plateforme utilise les constantes de l'article.

CE QUE CETTE SECTION BALAIE
============================
`tools/sweep_design.c` énumère l'espace ENTIER de la forme de Marsaglia :

    W =  32   x ^= x <<|>> a ; x ^= x <<|>> b ; x ^= x <<|>> c
    W =  64   idem, décalages jusqu'à 63
    W = 128   t = x ^ (x<<|>>a) ; x=y;y=z;z=w ;
              w = w ^ (w<<|>>b) ^ t ^ (t<<|>>c)

soit, pour chaque largeur, tous les triplets de décalages ET les huit
orientations. Les familles publiées sont DEDANS — c'est le contrôle : le
balayage doit les rejeter comme le §136 les a rejetées.

L'ATTAQUE, ET LE RÉ-ORIGINAGE QUI LA REND POSSIBLE
===================================================
Un tirage ordonné donne j_k, donc floor(K·u/2^32) = j_k − k avec K = 80 − k :
les bits de poids fort sur lesquels les deux bornes de l'intervalle s'accordent
sont EXACTS, et ce sont des formes F2-linéaires de l'état.

    L'état au DÉBUT DU PREMIER TIRAGE OBSERVÉ est aussi inconnu que celui du
    début de la journée. On ré-origine donc sur lui, et la profondeur de flux
    tombe de 42 x 21 = 882 mots à 9 x 21 = 189. Facteur cinq sur le coût.

TÉMOIN
=======
`--selftest` plante un design de chaque largeur, fabrique ses tirages ordonnés,
et vérifie DEUX choses : que le design planté est retrouvé COMPATIBLE, et qu'un
design ne différant que d'UN décalage est rejeté. 6/6.

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
DRY = os.environ.get("H125_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H125_TMP", "/tmp")
BASE_ID, PARJOUR = 1381194, 204


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BIN = os.path.join(TMP, "sweep_design_h125")
subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                os.path.join(DEPOT, "tools", "sweep_design.c")],
               check=True, capture_output=True)

# ==========================================================================
rule("1. LE TROU QUE LE §25 A NOMMÉ LUI-MÊME")
# ==========================================================================

st = subprocess.run([BIN, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Le §25 ecrit, a propos de l'attaque par reseau du §24 :

     « h11 laissait une faille beante : il fallait ENUMERER des constantes
       publiees. Un generateur aux constantes maison lui echappait
       entierement. »

   Le §25 a ferme ce trou POUR LES LCG, en calculant (a, c) au lieu de les
   deviner. POUR LES GENERATEURS F2-LINEAIRES, IL EST RESTE OUVERT : les §34,
   §110, §136 et §144 testent tous des DECALAGES PUBLIES.

     Un xorshift maison dont les decalages (13, 17, 5) seraient remplaces par
     (11, 19, 3) leur echappe A TOUS. Et rien n'oblige une plateforme a
     reprendre les constantes de l'article.

   `tools/sweep_design.c` enumere l'espace ENTIER de la forme de Marsaglia :
   tous les triplets de decalages et les huit orientations, pour trois
   largeurs. Les familles publiees sont DEDANS — c'est le controle.

   temoin de l'outil : {AUTO}
     (design plante retrouve COMPATIBLE, design differant d'UN decalage rejete)""")


# ==========================================================================
rule("2. LES DOUZE TIRAGES ORDONNÉS, RÉ-ORIGINÉS PAR JOURNÉE")
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

say(f"""   L'etat au DEBUT DU PREMIER TIRAGE OBSERVE est aussi inconnu que celui du
   debut de la journee : on re-origine donc sur lui, et la profondeur de flux
   s'effondre.

       {'journée':>8} {'index bruts':>26} {'ré-originés':>20} {'mots':>6}""")
BOULOT = []
for j in sorted(JOURS):
    idx = sorted(JOURS[j])
    rel = [k - idx[0] for k in idx]
    nm = (rel[-1] + 1) * 21
    BOULOT.append((j, idx, rel, nm))
    say(f"   {j:>8} {str(idx):>26} {str(rel):>20} {nm:>6}")


# ==========================================================================
rule("3. LE BALAYAGE")
# ==========================================================================

FORMES = [(0, 32, 31), (2, 128, 31)] if DRY else [(0, 32, 31), (1, 64, 63), (2, 128, 31)]
say(f"""   Pour chaque journee et chaque largeur, tous les designs de la forme.

       {'journée':>8} {'W':>5} {'designs':>12} {'survivants':>11} {'sec':>8}""")

TOTAL, SURV, LIGB = 0, [], []
for j, idx, rel, nm in BOULOT:
    for forme, W, smax in FORMES:
        args = [BIN, str(forme), str(len(idx))]
        for k, r in zip(idx, rel):
            args.append(str(r))
            args += [str(n) for n in JOURS[j][k]]
        tt = time.time()
        p = subprocess.run(args, capture_output=True, text=True, timeout=7200)
        nd = ns = 0
        for l in p.stdout.split("\n"):
            if l.startswith("SURVIVANT"):
                SURV.append((j, W, l.strip()))
            if l.startswith("forme="):
                d = dict(kv.split("=", 1) for kv in l.split() if "=" in kv)
                nd, ns = int(d["designs"]), int(d["survivants"])
        TOTAL += nd
        LIGB.append((j, W, nd, ns))
        say(f"   {j:>8} {W:>5} {nd:>12,} {ns:>11} {time.time()-tt:>8.1f}")

say(f"""
   {len(SURV)} design compatible sur {TOTAL:,} testes.""")
for j, W, l in SURV:
    say(f"     !! journee {j}, W={W} : {l}")
if not SURV:
    say("""     AUCUN. Et le controle tient : les familles publiees sont DANS
     l'espace balaye — xorshift32 (13,17,5), xorshift64 (13,7,17),
     xorshift128 (11,19,8) — donc le balayage les a rejetees comme le §136.

   CE QUE CELA FERME. Ce n'est plus « aucune famille PUBLIEE ne convient »,
   c'est « aucun xorshift de la forme de Marsaglia ne convient, quels que
   soient ses decalages ». Le trou que le §25 avait nomme est ferme pour les
   trois largeurs balayees.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h125.espace_des_designs",
        "Aucun generateur de la forme de Marsaglia — x ^= x<<|>>a ; x ^= "
        "x<<|>>b ; x ^= x<<|>>c pour W = 32 et 64, et la forme a quatre mots "
        "pour W = 128 — n'engendre les tirages ordonnes filmes, POUR AUCUN "
        "triplet de decalages ni aucune des huit orientations. C'est le trou "
        "que le §25 avait nomme et laisse ouvert pour les generateurs "
        "F2-lineaires : les §34, §110, §136 et §144 ne testent que des "
        "decalages PUBLIES",
        "nombre de designs compatibles, un design etant compatible si le "
        "systeme F2 construit sur les bits exacts de tous les tirages ordonnes "
        "de la journee reste sans contradiction",
        "aucun null n'est requis : la contradiction est deterministe. Un design "
        "faux est rejete des que ses equations se contredisent",
        "conforme si aucun design n'est compatible", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(SURV)), p=1.0,
        verdict="conforme" if not SURV else "DESIGN TROUVE",
        power_at=(f"temoin de l'outil : {AUTO} — pour chacune des trois largeurs, "
                  f"un design plante est retrouve COMPATIBLE et un design ne "
                  f"differant que d'UN decalage est rejete"),
        notes=(f"FERME LE TROU QUE LE §25 AVAIT NOMME. « h11 laissait une faille "
               f"beante : il fallait ENUMERER des constantes publiees ; un "
               f"generateur aux constantes maison lui echappait entierement. » "
               f"Le §25 l'a ferme pour les LCG en calculant (a,c) ; pour les "
               f"F2-lineaires il restait ouvert. {TOTAL:,} designs testes sur les "
               f"trois journees filmees, toutes orientations et tous decalages. "
               f"Le re-originage sur le premier tirage observe divise la "
               f"profondeur de flux par cinq et rend le balayage possible. Les "
               f"familles publiees sont DANS l'espace balaye — xorshift32 "
               f"(13,17,5), xorshift64 (13,7,17), xorshift128 (11,19,8) — donc "
               f"le balayage les rejette comme le §136. Ce n'est plus « aucune "
               f"famille publiee ne convient » mais « aucun xorshift de la forme "
               f"de Marsaglia ne convient, quels que soient ses decalages »."))
    h = lab.holm()
    say(f"   consigne : h125.espace_des_designs   {len(SURV)} design sur {TOTAL:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
