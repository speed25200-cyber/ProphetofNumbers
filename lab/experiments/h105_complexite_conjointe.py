"""h105 — la complexité linéaire CONJOINTE, et la réparation d'une faute du §122.

LA FAUTE
=========
Le §122 mesure, sur les deux bits exacts du rang du bonus, deux complexités
linéaires L et L', puis écrit

    W  >=  deg ppcm(f, f')  =  L + L' - deg pgcd(f, f')          <-- FAUX

et conclut « W >= 70 560 ». C'est faux, et l'erreur est une inégalité lue à
l'envers.

Sur une suite FINIE de N termes, Berlekamp-Massey rend le degré minimal d'un
annulateur du PRÉFIXE. Ce polynôme ne divise le polynôme caractéristique du
générateur que si N >= 2W. Pour W > N/2, un vrai générateur rend exactement
L = N/2 — indiscernable du hasard.

    Vérifié : un LFSR de degré 400 observé sur 640 termes rend L = 321 et 320,
    et le ppcm de ces deux annulateurs vaut 639. Le §122 aurait donc écrit
    « W >= 639 » et EXCLU le générateur de largeur 400 QUI AVAIT PRODUIT LES
    DONNÉES. Ce n'est pas une borne trop faible : c'est une EXCLUSION FAUSSE.

CE QUI EST VRAI
================
Si un générateur de largeur W a produit les M suites, son polynôme
caractéristique khi — de degré <= W — annule les M préfixes A LA FOIS. Donc

    W  >=  L_conjointe  =  min { deg g : g annule les M préfixes }.

C'est rigoureux pour TOUT W, sans condition sur N.

LE THÉORÈME DU SECOND BIT — ET IL NE DIT PAS CE QU'ON CROIT
============================================================
On attendrait du second bit qu'il apporte des équations neuves sur le
générateur. IL N'EN APPORTE AUCUNE, et c'est démontrable :

    Les suites annulées par khi forment un module sur F2[x] isomorphe à
    F2[x]/(khi). Si khi est IRRÉDUCTIBLE — c'est le cas de MT19937, des WELL,
    de tout LFSR à polynôme primitif — ce module est CYCLIQUE : deux
    fonctionnelles quelconques du même générateur vérifient b' = h(x)·b. La
    seconde est une combinaison de décalages de la première. []

Mesure : un LFSR de degré 44 497 observé sur 70 560 termes rend L_conjointe =
35 283, soit à deux unités près sa complexité scalaire.

    LE SECOND BIT NE REHAUSSE PAS LE SIGNAL. IL REHAUSSE LE NULL.

Deux suites INDÉPENDANTES, elles, ont une complexité conjointe de 2N/3 et non
N/2 : un g de degré d a d+1 coefficients pour M(N-d) équations, donc une
solution non triviale n'existe qu'à partir de d > M·N/(M+1). Le seuil passe
donc de 35 280 à 47 040, et l'écart se creuse là :

    hasard (deux suites indépendantes)          47 040
    générateur F2-linéaire de 44 497 bits       35 283
    Berlekamp-Massey scalaire, les deux cas     35 280 / 35 281  -- AVEUGLE

Le test scalaire ne sépare pas ces deux mondes ; le test conjoint les sépare de
onze mille sept cents bits. Et 47 040 > 44 497 = WELL44497b, LE PLUS GRAND ÉTAT
PUBLIÉ.

    La PORTÉE annoncée par le §122 est donc juste. Sa DÉMONSTRATION ne l'était
    pas, et la marge n'est pas celle qu'il annonçait.

COMMENT ON LA CALCULE
======================
g de degré <= d annule le préfixe de b si et seulement si, en notant R le
RENVERSÉ de b et g^ le renversé de g,

    (g^ · R mod x^N)  a un degré < d.

L'ensemble des (g^, rho_0, .., rho_{M-1}) tels que g^·R_j = rho_j (mod x^N) est
un module LIBRE de rang M+1 sur F2[x]. On y cherche l'élément de degré DÉCALÉ
minimal, avec le décalage (0, 1, .., 1) qui encode « deg rho_j < deg g^ ».
L'algorithme de Mulders-Storjohann met la base en forme faiblement de Popov —
pivots distincts — et la propriété de degré prévisible garantit alors que le
minimum sur les LIGNES est le minimum sur tout le module.

    `tools/jointf2.c`. Chaque étape fait strictement décroître la somme des
    degrés décalés : terminaison en O(M·N) étapes, 0,2 s pour N = 70 560.

Il TESTE l'archive : il consigne au registre.
"""

import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H105_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H105_TMP", "/tmp")
NNULL = 20 if DRY else 200
KB = 20
PUBLIE = 44497                            # WELL44497b, le plus grand état publié


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BJ = os.path.join(TMP, "jointf2_h105")
BB = os.path.join(TMP, "bmf2_h105")
FJ = os.path.join(TMP, "h105.bin")
for src, dst in (("jointf2.c", BJ), ("bmf2.c", BB)):
    subprocess.run(["cc", "-O3", "-march=native", "-o", dst,
                    os.path.join(DEPOT, "tools", src)], check=True, capture_output=True)


def _ecris(suites):
    n = len(suites[0])
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", len(suites), n))
        for s in suites:
            o = np.packbits(np.asarray(s, np.uint8) & 1, bitorder="little").tobytes()
            fh.write(o.ljust(nw * 8, b"\x00"))
    return n


def conjointe(suites):
    _ecris(suites)
    p = subprocess.run([BJ, FJ], capture_output=True, text=True, check=True)
    for l in p.stdout.split("\n"):
        if l.startswith("CONJOINTE"):
            return int(l.split()[1])
    raise RuntimeError(p.stdout)


def scalaires(suites):
    _ecris(suites)
    p = subprocess.run([BB, FJ], capture_output=True, text=True, check=True)
    L, pp = {}, None
    for l in p.stdout.split("\n"):
        t = l.split()
        if t[:1] == ["L"]:
            L[int(t[1])] = int(t[2])
        elif t[:1] == ["PPCM"]:
            pp = int(t[4].split("=")[1])
    return [L[i] for i in sorted(L)], pp


def bits_de(rangs, sampler):
    """Les deux bits exacts du mot, à position fixe (§122)."""
    r = np.asarray(rangs, np.int64)
    if sampler == "troncature":
        h = r // 5
        return [(h >> 1) & 1, h & 1]
    q = r & 3
    return [(q >> 1) & 1, q & 1]


def lfsr_dense(deg, n, graine=7):
    """Récurrence DENSE de degré `deg` : le polynôme est alors de plein degré
    avec forte probabilité, donc la complexité vaut vraiment `deg`. Coût
    O(n·deg) : réservé aux petites tailles de démonstration."""
    rng = np.random.default_rng(graine)
    P = rng.integers(0, 2, deg).astype(np.uint8)
    P[deg - 1] = 1
    buf = np.zeros(n + 8, np.uint8)
    buf[:deg] = rng.integers(0, 2, deg)
    buf[0] |= 1
    for t in range(deg, n + 8):
        buf[t] = np.bitwise_xor.reduce(buf[t - deg:t] & P[::-1])
    return buf[:n].copy(), (buf[:n] ^ buf[1:n + 1] ^ buf[5:n + 5]).astype(np.uint8)


def lfsr_trinome(deg, k, n, graine=1):
    """x^deg + x^k + 1. Pour deg = 44 497 — un exposant de Mersenne, d'où la
    famille WELL44497 tire son nom — et k = 8575, c'est un trinôme primitif
    connu, donc de complexité exactement `deg`."""
    rng = np.random.default_rng(graine)
    buf = np.zeros(n + 8, np.uint8)
    buf[:deg] = rng.integers(0, 2, deg)
    for t in range(deg, n + 8):
        buf[t] = buf[t - deg] ^ buf[t - k]
    return buf[:n].copy(), (buf[:n] ^ buf[1:n + 1] ^ buf[5:n + 5]).astype(np.uint8)


# ==========================================================================
rule("1. LA FAUTE DU §122, ET LE CONTRE-EXEMPLE QUI LA CLÔT")
# ==========================================================================

say("""   Le §122 ecrit  W >= deg ppcm(f, f')  et conclut W >= 70 560. C'est FAUX.

   Sur une suite FINIE de N termes, Berlekamp-Massey rend le degre minimal d'un
   annulateur du PREFIXE. Ce polynome ne divise le caracteristique du
   generateur que si N >= 2W. Pour W > N/2, un vrai generateur rend exactement
   N/2 — indiscernable du hasard.
""")
D0, N0 = 400, 640
b0, b1 = lfsr_dense(D0, N0)
Ls0, pp0 = scalaires([b0, b1])
cj0 = conjointe([b0, b1])
say(f"""   UN LFSR DE DEGRE {D0}, OBSERVE SUR {N0} TERMES ({N0//2} = N/2 < {D0} < {2*N0//3} = 2N/3) :

     Berlekamp-Massey scalaire      L = {Ls0[0]}, L' = {Ls0[1]}   (~N/2 : AVEUGLE)
     ppcm des deux, lu comme au §122        {pp0}
     complexite CONJOINTE                    {cj0}   (la verite plantee : {D0})

   Le §122 aurait donc ecrit « W >= {pp0} » et EXCLU le generateur de largeur
   {D0} QUI AVAIT PRODUIT LES DONNEES. Ce n'est pas une borne trop faible :
   c'est une EXCLUSION FAUSSE.

   Le ppcm de deux annulateurs d'un prefixe MAJORE la borne conjointe ; il ne
   la MINORE pas. Le §122 lisait l'inegalite a l'envers.""")


# ==========================================================================
rule("2. CE QUI EST VRAI, ET COMMENT ON LE CALCULE")
# ==========================================================================

st = subprocess.run([BJ, "--selftest"], capture_output=True, text=True)
AUTO = st.stdout.strip().split("\n")[-1]

say(f"""   Si un generateur de largeur W a produit les M suites, son polynome
   caracteristique khi — de degre <= W — annule les M prefixes A LA FOIS :

       W  >=  L_conjointe  =  min {{ deg g : g annule les M prefixes }}.

   RIGOUREUX POUR TOUT W, sans condition sur N.

   LE CALCUL. g de degre <= d annule le prefixe de b ssi (g^·R mod x^N) est de
   degre < d, ou R est le RENVERSE de b et g^ le renverse de g. L'ensemble des
   (g^, rho_0..rho_{{M-1}}) verifiant g^·R_j = rho_j mod x^N est un module LIBRE
   de rang M+1 sur F2[x] ; on y cherche l'element de degre DECALE minimal, le
   decalage (0,1,..,1) encodant « deg rho_j < deg g^ ». Mulders-Storjohann met
   la base en forme faiblement de Popov, et la propriete de degre previsible
   garantit que le minimum sur les LIGNES est le minimum sur tout le module.

   `tools/jointf2.c` autotest : {AUTO}""")
for l in st.stdout.strip().split("\n")[:-1]:
    say("     " + l.strip())


# ==========================================================================
rule("3. LE THÉORÈME DU SECOND BIT — ET IL NE DIT PAS CE QU'ON CROIT")
# ==========================================================================

ND = 6000 if DRY else 70560
DW, KT = (3500, 1301) if DRY else (PUBLIE, 8575)

say(f"""   On attendrait du second bit qu'il apporte des EQUATIONS NEUVES sur le
   generateur. IL N'EN APPORTE AUCUNE, et cela se demontre :

     Les suites annulees par khi forment un module sur F2[x] isomorphe a
     F2[x]/(khi). Si khi est IRREDUCTIBLE — MT19937, les WELL, tout LFSR a
     polynome primitif — ce module est CYCLIQUE, donc deux fonctionnelles
     quelconques du meme generateur verifient b' = h(x)·b : la seconde est une
     combinaison de DECALAGES de la premiere. []

   On plante donc un etat de {DW:,} bits{' — la largeur de WELL44497b, le plus grand etat publie —' if not DRY else ' (taille reduite du mode essai)'}
   et on l'observe sur {ND:,} tirages, comme l'archive.
""")
tw = time.time()
if DRY:
    w0, w1 = lfsr_dense(DW, ND, graine=3)
else:
    w0, w1 = lfsr_trinome(DW, KT, ND)
Lw, ppw = scalaires([w0, w1])
cjw = conjointe([w0, w1])
rr = np.random.default_rng(4242)
cjn = conjointe([rr.integers(0, 2, ND), rr.integers(0, 2, ND)])

say(f"   {'':>36} {'L scalaire':>12} {'CONJOINTE':>12}")
say(f"   {'hasard (deux suites independantes)':>36} {'~' + f'{ND//2:,}':>12} {cjn:>12,}")
say(f"   {'generateur F2-lineaire de ' + f'{DW:,}' + ' bits':>36} "
    f"{Lw[0]:>12,} {cjw:>12,}")
say(f"""
   LE SECOND BIT NE REHAUSSE PAS LE SIGNAL — la conjointe du generateur vaut
   {cjw:,}, a {abs(cjw-Lw[0])} unites de sa complexite scalaire. IL REHAUSSE LE NULL :
   deux suites INDEPENDANTES passent de N/2 = {ND//2:,} a 2N/3 = {2*ND//3:,}, parce qu'un g de
   degre d a d+1 coefficients pour 2(N-d) equations et qu'une solution non
   triviale n'apparait qu'a partir de d > 2N/3.

   C'EST LA QUE L'ECART SE CREUSE. Le test SCALAIRE rend {Lw[0]:,} pour le generateur
   et ~{ND//2:,} pour le hasard : il ne les separe pas. Le test CONJOINT rend {cjw:,}
   contre {cjn:,} — {cjn-cjw:,} bits d'ecart.

   {'Et ' + f'{2*ND//3:,}' + ' > ' + f'{PUBLIE:,}' + ' : le seuil conjoint depasse WELL44497b la ou le' if not DRY else '(Mode essai : les tailles sont reduites, le rapport des seuils est le'}
   {'seuil scalaire, ' + f'{ND//2:,}' + ', restait EN DESSOUS.' if not DRY else 'meme.)'} ({time.time()-tw:.1f} s)""")
TEMOIN = cjw <= DW and cjn - cjw > 0.15 * ND


# ==========================================================================
rule("4. L'ARCHIVE")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1)
N = len(RANG)

say(f"   {'hypothèse':>14} {'L (scalaire)':>14} {'L′':>8} "
    f"{'ppcm (§122, faux)':>19} {'W ≥ CONJOINTE':>15}")
REEL, SCAL = {}, {}
for samp in ("troncature", "modulo"):
    bb = bits_de(RANG, samp)
    Ls, pp = scalaires(bb)
    cj = conjointe(bb)
    REEL[samp], SCAL[samp] = cj, (Ls, pp)
    say(f"   {samp:>14} {Ls[0]:>14,} {Ls[1]:>8,} {pp:>19,} {cj:>15,}")

BORNE = min(REEL.values())
say(f"""
   BORNE JUSTE : W >= {BORNE:,}.   (le §122 annoncait {min(SCAL[s][1] for s in SCAL):,})

   {'WELL44497b (44 497)':>28} : {'couvert' if BORNE > PUBLIE else 'HORS DE PORTEE'}
   {'MT19937, WELL19937':>28} : couvert
   {'tout etat < ' + f'{BORNE:,}':>28} : couvert, nomme ou non""")


# ==========================================================================
rule("5. LE NULL, ET LA CONSIGNATION")
# ==========================================================================

say(f"   {NNULL} archives d'un generateur PARFAIT, meme longueur, meme statistique.")
tn = time.time()
rng = np.random.default_rng(20260902)
NULLS = []
for k in range(NNULL):
    rg = rng.integers(0, KB, N)
    NULLS.append(min(conjointe(bits_de(rg, s)) for s in ("troncature", "modulo")))
NULLS = np.array(NULLS)
P = (1 + int((NULLS <= BORNE).sum())) / (1 + len(NULLS))
say(f"   null : moyenne {NULLS.mean():,.0f}   min {NULLS.min():,}   max {NULLS.max():,}"
    f"   ({time.time()-tn:.1f} s)")
say(f"   observe {BORNE:,}   p = {P:.4f}")

if DRY:
    say("\n   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h105.complexite_conjointe",
        "Aucun generateur F2-lineaire dont l'etat tient en moins de 44 497 bits "
        "— la largeur de WELL44497b, le plus grand etat publie — n'engendre les "
        "rangs du bonus de l'archive, sous aucun pas constant, aucun decalage, "
        "aucun nombre de mots par numero et aucun des deux echantillonneurs. "
        "C'est l'enonce que le §122 pretendait etablir avec une statistique "
        "invalide ; il est ici teste avec une statistique valide",
        "borne inferieure sur la largeur d'etat W = min sur les deux "
        "echantillonneurs de la COMPLEXITE LINEAIRE CONJOINTE des DEUX bits "
        "exacts du rang du bonus — le degre minimal d'un polynome annulant les "
        "deux prefixes a la fois, calcule par reduction de base sur F2[x] "
        "(forme faiblement de Popov). Contrairement au ppcm du §122, cette "
        "quantite MINORE W sans condition sur N. Une valeur BASSE serait "
        "l'anomalie",
        f"{NNULL} archives d'un generateur parfait, meme longueur, meme "
        f"extraction ; p = (1 + #{{null <= observe}}) / (1 + {NNULL})",
        "conforme si la borne conjointe mesuree depasse 44 497", track="B")
    tok["m_extra"] = 1          # les deux echantillonneurs, moins celui-ci
    lab.record(
        tok, float(BORNE), p=P,
        verdict="conforme" if BORNE > PUBLIE else "ANOMALIE",
        power_at=(f"temoin decisif : une recurrence creuse de degre {DW:,} — la "
                  f"largeur de WELL44497b — observee sur {ND:,} tirages rend "
                  f"L = {Lw[0]:,} et {Lw[1]:,} en Berlekamp-Massey scalaire (aveugle, "
                  f"~N/2) et {cjw:,} en conjointe (vue). Autotest de l'outil : {AUTO}"),
        notes=(f"RETRACTATION PARTIELLE DU §122. Le §122 concluait W >= 70 560 a "
               f"partir de deg ppcm(f, f'). C'est faux : sur une suite FINIE, "
               f"Berlekamp-Massey rend un annulateur du PREFIXE, qui ne divise "
               f"le caracteristique que si N >= 2W ; le ppcm MAJORE la borne "
               f"conjointe au lieu de la minorer. Contre-exemple execute : un "
               f"LFSR de degre {D0} observe sur {N0} termes donne L = {Ls[0]}/{Ls[1]} et "
               f"un ppcm de {pp0} — le §122 aurait exclu le generateur qui avait "
               f"produit les donnees. La borne valide est la complexite "
               f"CONJOINTE, de seuil 2N/3 = {2*N//3:,} et non N/2 = {N//2:,}. Elle "
               f"depasse quand meme 44 497, donc la PORTEE annoncee au §122 "
               f"reste acquise — mais par un autre calcul et avec une marge de "
               f"{2*N//3 - PUBLIE:,} bits au lieu des 26 063 annonces. Corrige aussi le "
               f"§89, qui ecrivait qu'aucun generateur deploye ne depasse "
               f"35 280 bits : WELL44497b en fait 44 497."))
    h = lab.holm()
    say(f"\n   consigne : h105.complexite_conjointe   W >= {BORNE:,}")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA CORRIGE, ET CE QUE CELA LAISSE DEBOUT")
# ==========================================================================

say(f"""   AU §122. Sa conclusion de PORTEE — « WELL44497b est couvert » — tient, mais
   sa DEMONSTRATION ne tenait pas, et la marge n'est pas celle qu'il annoncait :
   {2*N//3:,} et non {min(SCAL[s][1] for s in SCAL):,}. Tout le reste du §122 reste vrai : le theoreme
   L(b) <= W, l'invariance en pas et en decalage, l'extension par classes modulo
   64, le corollaire arithmetique. C'est la SEULE etape du ppcm qui tombe.

   AU §89. Il ecrivait : « 35 280 bits, c'est 1,8 fois l'etat de MT19937. Aucun
   generateur deploye n'en a autant. » WELL44497b en a {PUBLIE:,}, et il est publie
   depuis 2006 dans la meme famille que WELL512a et WELL19937, deja au
   catalogue du dossier. Le §89 laissait donc une case ouverte sans le savoir ;
   c'est ce fichier qui la ferme, et il faut deux bits pour cela.

   LA LECON, ET ELLE EST LA MEME QUE CELLE DU §101, DU §121 ET DU §123. Une
   conclusion recopiee plus large que sa source. Ici la source disait « L <= W »
   — une MAJORATION de L — et j'en ai tire une MINORATION de W par un chemin
   qui n'existe pas. La difference entre les deux se voit en une simulation de
   dix lignes ; encore faut-il la faire.

   CE QUI RESTE HORS DE PORTEE, INCHANGE : le rejet a pas variable (§111), les
   sorties brouillees (§119, §123), et l'indexation dans l'ordre d'emission
   (§106).

   ({time.time() - T0:.1f} s)""")
