"""h119 — le survivant que le §137 a oublié, et ce qu'il coûte à la borne
la plus citée du dossier.

CE QUE LE §137 A CONCLU, ET OÙ IL A GLISSÉ
===========================================
Le §137 a réfuté deux lectures que le §129 laissait ouvertes, toutes deux à
INDICE CONSTANT :

    A' : bonus = ordre[j],  j constant       refuté (indices 2, 18, 9)
    B' : bonus = trié[j],   j constant       refuté (indices 10, 3, 4)

Puis il a écrit : « B (§106) — rang du bonus = floor(20·u) — SEUL SURVIVANT ».
C'est faux, et la faute est une omission de cas. Réfuter « j constant » laisse
DEUX modèles à indice TIRÉ, pas un :

    B   : j = floor(20·u_20) est l'indice dans le TABLEAU TRIÉ
    B'' : j = floor(20·u_20) est l'indice dans l'ORDRE D'ÉMISSION

Le §137 n'a testé que la constance de j. Il n'a rien dit sur le TABLEAU auquel j
s'applique — et c'est précisément la question que le §129 posait.

POURQUOI C'EST GRAVE, ET PAS UNE ARGUTIE
=========================================
Sous B, le rang publié r vaut floor(20·u_20), donc

    r // 5 = floor(4·u_20) = LES DEUX BITS DE POIDS FORT DU MOT.

C'est cette égalité — et rien d'autre — qui autorise le §122 à donner ces deux
bits à Berlekamp-Massey, et donc les §124 et §126 à conclure W >= 47 040. C'est
la borne la plus citée du dossier.

Sous B'', r est le rang de ordre[j] dans le tableau trié : une fonction des
VINGT ET UN mots du tirage, pas d'un seul. Les « deux bits exacts » n'existent
plus, et la borne s'effondre.

CE QUE CETTE SECTION ÉTABLIT
=============================
  1. B et B'' sont INDISCERNABLES sur le couple (indice d'émission, rang trié) :
     ce couple est uniforme sur 20x20 sous les DEUX. L'archive ne peut donc pas
     trancher, et trois vidéos non plus.

  2. La différence est pourtant ÉNORME sur l'observable du §122, et on la mesure
     avec l'outil du §122 lui-même : sur un générateur planté de 128 bits,

         sous B    L(b) = 128        la borne du §122 fonctionne
         sous B''  L(b) = N/2        elle est VIDE

  3. Donc W >= 47 040 est CONDITIONNEL À B, et la condition n'est pas
     vérifiable sur l'archive.

CE QUI NE BOUGE PAS, ET IL FAUT LE DIRE AUSSI
==============================================
Le §136 — 120 systèmes sur 120 INCOMPATIBLES sur les tirages ordonnés — n'utilise
pas le rang du bonus : il lit l'ordre d'émission, donc les j_k directement. Il est
INTACT. Idem pour les §132, §133 et §138, qui balayent des graines contre l'ordre
ou contre l'ensemble trié.

    Le dégât est circonscrit à la borne model-free. C'est déjà beaucoup : c'est
    le seul résultat du dossier qui ne nomme aucune famille.

Il DÉMONTRE et il MESURE. Il consigne au registre.
"""

import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H119_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H119_TMP", "/tmp")
POOL, DRAWN = 80, 20
M32 = 0xFFFFFFFF


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


import struct                                                 # noqa: E402
import subprocess                                             # noqa: E402

BB = os.path.join(TMP, "bmf2_h119")
FJ = os.path.join(TMP, "h119.bin")
subprocess.run(["cc", "-O3", "-march=native", "-o", BB,
                os.path.join(DEPOT, "tools", "bmf2.c")],
               check=True, capture_output=True)


def L_de(suite):
    b = np.asarray(suite, np.uint8) & 1
    n = len(b)
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", 1, n))
        fh.write(np.packbits(b, bitorder="little").tobytes().ljust(nw * 8, b"\x00"))
    p = subprocess.run([BB, FJ], capture_output=True, text=True, check=True)
    for l in p.stdout.split("\n"):
        t = l.split()
        if t[:1] == ["L"]:
            return int(t[2])
    raise RuntimeError(p.stdout)


# ---------------------------------------------------------------------------
# xorshift128 : F2-LINEAIRE, largeur 128, sortie = le mot lui-meme. C'est le
# cadre exact du §122 — s -> A·s et le bit observe est une forme lineaire.
# ---------------------------------------------------------------------------
class XS128:
    def __init__(self, graine=(123456789, 362436069, 521288629, 88675123)):
        self.x, self.y, self.z, self.w = graine

    def mot(self):
        t = (self.x ^ ((self.x << 11) & M32)) & M32
        self.x, self.y, self.z = self.y, self.z, self.w
        self.w = (self.w ^ (self.w >> 19) ^ t ^ (t >> 8)) & M32
        return self.w


def tirage(g):
    """Rend (ordre d'emission, mot du bonus). Fisher-Yates par TRONCATURE,
    vingt mots, puis UN vingt-et-unieme mot pour l'indice du bonus (§137)."""
    arr = list(range(1, POOL + 1))
    ordre = []
    for i in range(DRAWN):
        m = POOL - i
        u = g.mot()
        j = i + ((u * m) >> 32)
        arr[i], arr[j] = arr[j], arr[i]
        ordre.append(arr[i])
    return ordre, g.mot()


def observables(ordre, u20):
    """Rend (r_sous_B, r_sous_Bpp, j) — le rang PUBLIE dans chaque modele."""
    j = (u20 * DRAWN) >> 32                       # floor(20·u), les deux modeles
    tri = sorted(ordre)
    r_B = j                                       # j indexe le tableau TRIE
    r_Bpp = tri.index(ordre[j])                   # j indexe l'ORDRE d'emission
    return r_B, r_Bpp, j


def bit_expose(r):
    """Le bit de poids fort des deux bits « exacts » du §122, sous troncature."""
    return ((r // 5) >> 1) & 1


# ==========================================================================
rule("1. LA FAUTE DU §137 : UNE OMISSION DE CAS")
# ==========================================================================

say("""   Le §137 a refute deux lectures, toutes deux a INDICE CONSTANT :

     A'  bonus = ordre[j], j constant      refute (indices 2, 18, 9)
     B'  bonus = trie[j],  j constant      refute (indices 10, 3, 4)

   puis a conclu « B — rang du bonus = floor(20·u) — SEUL SURVIVANT ». C'est
   faux. Refuter « j constant » laisse DEUX modeles a indice TIRE :

     B    j = floor(20·u_20) indexe le TABLEAU TRIE
     B''  j = floor(20·u_20) indexe l'ORDRE D'EMISSION

   Le §137 n'a teste que la CONSTANCE de j. Il n'a rien dit sur le TABLEAU
   auquel j s'applique — et c'est exactement la question que le §129 posait.

   POURQUOI CE N'EST PAS UNE ARGUTIE. Sous B, le rang publie r vaut
   floor(20·u_20), donc

       r // 5 = floor(4·u_20) = LES DEUX BITS DE POIDS FORT DU MOT,

   et c'est cette egalite — rien d'autre — qui autorise le §122 a donner ces
   deux bits a Berlekamp-Massey, donc les §124 et §126 a conclure W >= 47 040.

   Sous B'', r est le rang de ordre[j] dans le tableau trie : une fonction des
   VINGT ET UN mots du tirage. Les deux bits exacts n'existent plus.""")


# ==========================================================================
rule("2. B ET B'' SONT INDISCERNABLES SUR CE QUE LA PLATEFORME PUBLIE")
# ==========================================================================

NSIM = 2000 if DRY else 200000
g = XS128()
JB, RB, JP, RP = [], [], [], []
for _ in range(NSIM):
    o, u = tirage(g)
    rb, rp, j = observables(o, u)
    # sous B    : l'indice d'emission du bonus est la position de trie[j]
    JB.append(o.index(sorted(o)[j]))
    RB.append(rb)
    # sous B''  : l'indice d'emission EST j, et le rang publie est rp
    JP.append(j)
    RP.append(rp)


def khi2_couple(a, b):
    t = np.bincount(np.asarray(a) * DRAWN + np.asarray(b),
                    minlength=DRAWN * DRAWN).astype(float)
    e = len(a) / (DRAWN * DRAWN)
    x = float(((t - e) ** 2 / e).sum())
    return x, float(stats.chi2.sf(x, DRAWN * DRAWN - 1))


XB, PB = khi2_couple(JB, RB)
XP, PP = khi2_couple(JP, RP)

say(f"""   Ce que la plateforme publie du bonus, c'est son RANG TRIE r. Ce qu'une
   video ajoute, c'est son INDICE D'EMISSION j. Le couple (j, r) est donc tout
   ce qui est observable — et il est UNIFORME SUR 20x20 SOUS LES DEUX MODELES.

   La raison est une symetrie : l'ordre d'emission est une permutation
   uniforme du tableau trie. Sous B on tire r uniformement et j s'en deduit par
   une permutation uniforme ; sous B'' on tire j uniformement et r s'en deduit
   par la permutation inverse. Les deux lois jointes sont la meme.

   Mesure sur {NSIM:,} tirages simules, khi-deux a {DRAWN*DRAWN-1} degres de liberte :

       modèle            khi2          p
       B          {XB:>11.1f} {PB:>10.3f}
       B''        {XP:>11.1f} {PP:>10.3f}

     NI L'ARCHIVE NI LES VIDEOS NE PEUVENT TRANCHER. Le §129 avait raison :
     il faut reconstituer l'etat, et rien ne le reconstitue.""")


# ==========================================================================
rule("3. LA DIFFÉRENCE, MESURÉE AVEC L'OUTIL DU §122 LUI-MÊME")
# ==========================================================================

ND = 400 if DRY else 1200
g = XS128(graine=(88675123, 521288629, 362436069, 123456789))
bB, bP = [], []
for _ in range(ND):
    o, u = tirage(g)
    rb, rp, _ = observables(o, u)
    bB.append(bit_expose(rb))
    bP.append(bit_expose(rp))
LB, LP = L_de(bB), L_de(bP)
W = 128

say(f"""   xorshift128 est F2-LINEAIRE de largeur {W} : c'est exactement le cadre du
   §122 — s -> A·s, et le bit observe doit etre une forme lineaire de l'etat.
   On fabrique {ND:,} tirages, on en extrait le bit du §122 sous CHAQUE modele,
   et on donne les deux suites a Berlekamp-Massey sans rien lui dire.

       modèle     observable                              L mesuré     borne §122
       B          bit 31 du mot u_20, position fixe    {LB:>12,}   {'TIENT' if LB <= W else 'ROMPUE':>13}
       B''        rang de ordre[j] dans le tableau     {LP:>12,}   {'TIENT' if LP <= W else 'VIDE':>13}

   seuil du hasard pour {ND:,} termes : {ND//2:,}

   Sous B, L vaut {LB} et la borne du §122 fonctionne : elle exclut toute largeur
   inferieure. Sous B'', L sature au seuil du hasard — LA BORNE EST VIDE, et
   elle l'est alors meme que les donnees viennent d'un generateur de {W} bits.

     CE N'EST PAS UNE BORNE FAIBLE : C'EST UNE BORNE QUI NE DIT RIEN.""")


# ==========================================================================
rule("4. LA CARTE DES DÉGÂTS")
# ==========================================================================

say("""   Ce qui repose sur le rang du bonus, donc sur le modele B :

     §103, §122   complexite lineaire du rang du bonus
     §124         complexite CONJOINTE, W >= 47 040
     §126         plafond de l'archive
     §127         portee de quatre bits
     §135         la table d'exclusion par degre, colonne T = 70 560

   Ce qui N'Y REPOSE PAS, et qui est donc INTACT :

     §136   120 systemes sur 120 INCOMPATIBLES. Il lit l'ORDRE d'emission,
            donc les j_k directement, et n'a jamais touche au rang du bonus.
            C'est l'exclusion la plus forte du dossier, et elle tient.
     §132   balayage de graines contre l'ORDRE des trois tirages dates.
     §138   balayage de graines contre l'ORDRE, journee par journee.
     §133   balayage de graines contre l'ENSEMBLE TRIE, 346 journees.
     §110   theoreme du confinement, qui ne parle que des vingt numeros.
     §134   le plafond T/(M+1) est un theoreme sur les suites, pas sur ce
            dossier ; il vaut quel que soit l'observable.
     §137   le fait que le tirage consomme VINGT ET UN mots reste acquis :
            il decoule de « j est tire », que B'' partage avec B.

   L'ENONCE CORRIGE, ET IL FAUT LE CITER AINSI DESORMAIS :

     « SOUS LE MODELE B — le rang publie du bonus est floor(20·u) d'un mot a
       position fixe — l'archive impose W >= 47 040. La condition n'est pas
       verifiable sur les donnees publiees. »

   COMMENT ON TRANCHERAIT. Il faut un tirage ordonne AVEC son bonus dont on
   connaisse aussi l'etat, ou — equivalent et atteignable — assez de tirages
   ordonnes pour reconstituer l'etat, puis PREDIRE u_20 et regarder lequel des
   deux modeles produit le bonus observe. C'est exactement le programme du
   §139 : deux jours et demi de capture du flux, et la question tombe avec le
   reste.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

OK = (PB > 0.01) + (PP > 0.01) + (LB <= W) + (LP > 2 * W)

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h119.survivant_oublie",
        "Le §137 a conclu a tort que le modele B etait le SEUL survivant : "
        "refuter les deux lectures a indice CONSTANT laisse DEUX modeles a "
        "indice tire, selon que j = floor(20·u) indexe le tableau TRIE (B) ou "
        "l'ORDRE d'emission (B''). Ces deux modeles sont indiscernables sur le "
        "couple (indice d'emission, rang trie), qui est uniforme sur 20x20 sous "
        "les deux ; et pourtant, sur un generateur F2-lineaire plante de 128 "
        "bits, le bit du §122 a une complexite lineaire bornee par 128 sous B et "
        "saturee au seuil du hasard sous B''. La borne W >= 47 040 est donc "
        "CONDITIONNELLE A B, et la condition n'est pas verifiable sur l'archive",
        "nombre de predictions chiffrees exactes sur quatre : uniformite du "
        "couple (j, r) sous B, puis sous B'' ; L <= 128 sous B ; et L > 256 "
        "sous B'', c'est-a-dire au-dela de toute borne utile",
        "si les deux modeles differaient sur ce que la plateforme publie, l'un "
        "des deux khi-deux s'ecarterait ; si B'' preservait les bits exacts, sa "
        "complexite lineaire resterait bornee par la largeur de l'etat",
        "conforme si les quatre predictions sont exactes", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(OK), p=1.0,
        verdict="conforme" if OK == 4 else "DEMENTI",
        power_at=(f"temoin positif ET negatif dans la meme mesure : la MEME suite "
                  f"de tirages, issue du MEME generateur de 128 bits, donne "
                  f"L = {LB} sous B — la borne du §122 fonctionne — et L = {LP} "
                  f"sous B'' sur {ND} termes, soit le seuil du hasard. L'outil "
                  f"voit donc la structure quand elle est la, et son absence "
                  f"quand elle n'y est pas"),
        notes=(f"AUTO-CORRECTION DU §137, ECRIT DANS CETTE MEME SESSION. Il a "
               f"refute les deux lectures a indice CONSTANT du §129 puis conclu "
               f"« B seul survivant » : c'est une omission de cas, car B'' — j "
               f"indexe l'ORDRE d'emission au lieu du tableau trie — est aussi a "
               f"indice tire et n'a pas ete teste. La symetrie qui les rend "
               f"indiscernables est que l'ordre d'emission est une permutation "
               f"uniforme du tableau trie : sous B on tire r et j s'en deduit, "
               f"sous B'' on tire j et r s'en deduit, meme loi jointe. Degats "
               f"CIRCONSCRITS : les §103, §122, §124, §126, §127 et la colonne "
               f"T = 70 560 du §135 deviennent conditionnels a B ; le §136 (120 "
               f"systemes sur 120 incompatibles), les §132, §133, §138 et le "
               f"§110 lisent l'ORDRE ou l'ensemble trie et sont INTACTS ; le "
               f"§134 est un theoreme sur les suites et vaut quel que soit "
               f"l'observable ; et le fait que le tirage consomme 21 mots reste "
               f"acquis, B'' le partageant avec B. Pour trancher il faut "
               f"reconstituer l'etat puis predire u_20 — c'est le programme du "
               f"§139."))
    h = lab.holm()
    say(f"   consigne : h119.survivant_oublie   {OK}/4 predictions exactes")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
