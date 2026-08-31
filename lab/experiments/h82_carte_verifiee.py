"""h82 — la carte vérifiée : lire les sources plutôt que la prose.

POURQUOI CE FICHIER EXISTE
===========================
La carte de couverture du §73 a menti DEUX FOIS aujourd'hui.

  §97   « LCG mod 2^48 | rejet / FY modulaire | §34 | 2^48 complets ».
        Or `tools/sweep_java48.c` ne contient qu'UNE fonction
        d'echantillonnage, `java_fy`. Aucun rejet. La case la plus probable
        de tout l'espace etait crue fermee ; elle ne l'etait pas.

  §98   « F2-lineaires <= 128 bits | rejet | §68 | resolu TOUTE GRAINE,
        couverture 46-99 % ». Les deux moities de la phrase se
        contredisent, et la garde de h61 portait un commentaire perime.

Deux erreurs, meme cause : une conclusion RECOPIEE plus largement que sa
source. Une carte tenue a la main derive de sa base de code.

CE QUE CE FICHIER FAIT
=======================
Il ne recopie rien. Il LIT les sources C des balayages et en extrait, par
analyse du texte, les tableaux de noms que le programme lui-meme utilise
pour s'annoncer :

    #define NGEN 12
    static const char *GEN_NAME[NGEN] = { "java.util.Random", ... };
    static const char *SAMP_NAME[NSAMP] = { "modulo + rejet", ... };

La carte qui en sort est donc VRAIE PAR CONSTRUCTION : si le code change,
elle change. Si elle ment, c'est que le programme mentait deja sur lui-meme.

Il ne teste rien : il ne consigne RIEN.
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

T0 = time.time()
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TOOLS = os.path.join(DEPOT, "tools")


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# L'ANALYSEUR
# ==========================================================================
def defines(src):
    """Les #define entiers du fichier."""
    return {m.group(1): int(m.group(2))
            for m in re.finditer(r"#define\s+(\w+)\s+(\d+)", src)}


def tableau_noms(src, motif):
    """Les chaines d'un tableau `static const char *MOTIF[...] = { ... };`."""
    m = re.search(motif + r"\s*\[[^\]]*\]\s*=\s*\{(.*?)\};", src, re.S)
    if not m:
        return []
    return re.findall(r'"([^"]*)"', m.group(1))


def familles_struct(src):
    """Les noms d'un tableau de structures `static const ... FAM[] = {...};`."""
    m = re.search(r"FAM\s*\[\]\s*=\s*\{(.*?)\n\};", src, re.S)
    if not m:
        return []
    return re.findall(r'\{\s*"([^"]+)"', m.group(1))


def fonctions_echantillon(src):
    """Les fonctions dont le nom denonce un echantillonneur."""
    return sorted(set(re.findall(r"static\s+\w+\s+(samp_\w+|\w*_fy\w*|\w*reject\w*)\s*\(",
                                 src)))


def lire(chemin):
    src = open(chemin, encoding="utf-8", errors="replace").read()
    d = defines(src)
    gens = (tableau_noms(src, r"GEN_NAME") or tableau_noms(src, r"FAM_NAME")
            or familles_struct(src))
    samps = tableau_noms(src, r"SAMP_NAME") or fonctions_echantillon(src)
    return {
        "lignes": src.count("\n") + 1,
        "NGEN": d.get("NGEN") or d.get("NFAM") or (len(gens) or None),
        "NSAMP": d.get("NSAMP") or (len(samps) or None),
        "generateurs": gens,
        "echantillonneurs": samps,
    }


# ==========================================================================
rule("1. CE QUE CHAQUE OUTIL COUVRE VRAIMENT")
# ==========================================================================

fichiers = sorted(f for f in os.listdir(TOOLS) if f.endswith(".c"))
say(f"   {len(fichiers)} sources de balayage dans `tools/`.\n")
say(f"   {'outil':>22} {'lignes':>7} {'générateurs':>12} {'échantillonneurs':>17}")
INV = {}
for f in fichiers:
    info = lire(os.path.join(TOOLS, f))
    INV[f] = info
    say(f"   {f:>22} {info['lignes']:>7} "
        f"{(info['NGEN'] if info['NGEN'] else '—'):>12} "
        f"{(info['NSAMP'] if info['NSAMP'] else '—'):>17}")

say("\n   Le detail, tel que chaque programme se decrit lui-meme :\n")
for f, info in INV.items():
    if not info["generateurs"] and not info["echantillonneurs"]:
        continue
    say(f"   {f}")
    if info["generateurs"]:
        say(f"     générateurs      : {', '.join(info['generateurs'])}")
    if info["echantillonneurs"]:
        say(f"     échantillonneurs : {', '.join(info['echantillonneurs'])}")
    say("")


# ==========================================================================
rule("2. LES DEUX MENSONGES DE LA CARTE, RELUS DANS LA SOURCE")
# ==========================================================================

j48 = INV.get("sweep_java48.c", {})
say(f"""   PREMIER. La carte portait :

     | LCG mod 2^48 (java.util.Random) | rejet / FY modulaire | §34 | 2^48 |

   `sweep_java48.c` annonce {len(j48.get('echantillonneurs', [])) or 0} echantillonneur(s) :
     {', '.join(j48.get('echantillonneurs', [])) or '(aucun tableau de noms)'}

   Un Fisher-Yates partiel, et rien d'autre. Le rejet n'y est pas. Corrige au
   §97, qui l'a ferme pour de bon par l'attaque 2-adique.
""")

ordre = INV.get("sweep_order.c", {})
say(f"""   SECOND. Le §68 conclut « resolu pour TOUTE GRAINE » avec une couverture
   annoncee de 46 %. Ce n'est pas une question de source mais d'arithmetique :
   les deux enonces se contredisent. Le §98 a trouve la cause — une garde
   perimee et une loi de rejets fausse — et rendu le chiffre corrige.

   Ce que `sweep_order.c` couvre reellement : {ordre.get('NGEN')} generateurs
   x {ordre.get('NSAMP')} echantillonneurs, sur les graines annoncees dans son
   usage, pas sur les etats complets.""")


# ==========================================================================
rule("3. CE QUI N'EST DANS AUCUNE SOURCE")
# ==========================================================================

tous = set()
for info in INV.values():
    tous |= {g.lower() for g in info["generateurs"]}

MANQUANTS = [
    ("System.Random (.NET)",
     "Fibonacci retarde de Knuth, lags effectifs 55/34 mod 2^31-1, sortie par "
     "troncature. La bibliotheque standard de tout back-end .NET."),
    ("mt_rand (PHP < 7.1)",
     "le §72 le presente comme MT19937 : FAUX. Son twist prend loBit(u) au "
     "lieu de loBit(v) — vingt ans de bogue, un generateur different."),
    ("MWC / SWB (Marsaglia)",
     "generateurs a retenue. Le §91 les nomme comme non vus ; ils sont "
     "EQUIVALENTS a un LCG multiplicatif modulo a*2^32 - 1, ce qui est la "
     "piste a suivre si on veut les attaquer."),
]
say("   Familles absentes de TOUTES les sources de balayage :\n")
say(f"   {'famille':>24}   pourquoi elle compte")
for nom, pourquoi in MANQUANTS:
    present = any(nom.split()[0].lower() in t for t in tous)
    say(f"   {nom:>24}   {'PRESENTE ?!' if present else pourquoi.split('.')[0]}")

say(f"""
   Les deux premieres sont couvertes AUTREMENT depuis cette session : le §79
   et le §80 cherchent la RECURRENCE plutot que la graine, et une recurrence
   lineaire d'ordre <= 2 modulo 2^k y est exclue quelles que soient ses
   constantes. .NET tombe dans cette classe pour la partie additive ; son
   echantillonneur par troncature est couvert par la signature (B) du §79.

   La troisieme reste ouverte, et le §91 avait raison de la nommer.""")


# ==========================================================================
rule("4. LA CARTE, TELLE QU'ELLE DEVRAIT S'ÉCRIRE")
# ==========================================================================

say(f"""   Une carte tenue a la main derive. Celle-ci se recalcule :

     - la colonne « echantillonneurs » vient du tableau SAMP_NAME du
       programme, pas d'un souvenir ;
     - la colonne « generateurs » vient de GEN_NAME, FAM_NAME ou du tableau
       de structures FAM ;
     - quand un fichier n'a AUCUN tableau de noms, on lit ses fonctions —
       c'est ainsi que le mensonge de `sweep_java48.c` se voit.

   REGLE QUI EN DECOULE, et elle vaut pour la suite du dossier : une ligne de
   carte ne doit jamais etre plus large que la source qu'elle cite. Quand les
   deux divergent, c'est la source qui a raison.

   Registre : INCHANGE. h82 ne teste rien — il verifie une prose contre du
   code.

   ({time.time() - T0:.1f} s)""")
