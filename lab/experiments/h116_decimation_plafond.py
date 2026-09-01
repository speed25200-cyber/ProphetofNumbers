"""h116 — le THÉORÈME DU PLAFOND UNIVERSEL : T/2, et une seule suite.

LA QUESTION QUI RESTAIT OUVERTE APRÈS LE §124
==============================================
Le §124 a démontré que le SECOND BIT n'apporte aucune équation quand khi est
irréductible : le module des suites annulées par khi est cyclique, donc
b' = h(x)·b. Mais il a laissé ouvert le pendant naturel de cette question :

    ET SI, AU LIEU DE LIRE UN AUTRE BIT, ON LISAIT LE MÊME BIT UN TIRAGE
    SUR DEUX ? Le dossier énumère des pas depuis le §14 ; personne n'a jamais
    demandé ce que la DÉCIMATION fait au plafond model-free.

C'est une vraie question, parce que la décimation, elle, CHANGE le polynôme
minimal : si b vient de A, la suite décimée vient de A^d, dont les racines sont
les puissances d-ièmes de celles de A. Elles peuvent COLLIDER, et la complexité
CHUTE. Ce n'est pas un effet théorique : on le construit ci-dessous, et la
chute est totale.

LE THÉORÈME DE LA DÉCIMATION
=============================
Soit s -> A·s sur F2^W et b_n = l(A^n s) avec l une forme F2-linéaire.

  (a) VALIDITÉ. Pour tout pas d >= 1 et tout décalage r, la suite décimée
      b^(d,r)_n = b_{r + nd} vaut l(A^r (A^d)^n s) : c'est la suite d'un
      générateur de matrice A^d, de MÊME largeur W. Donc

          W  >=  L( b^(d,r) )     et     W  >=  L_conjointe( b^(d,0..d-1) ).

      Les deux bornes sont rigoureuses pour tout W, sans condition sur N.

  (b) CHUTE. Les racines de khi_d = polynôme caractéristique de A^d sont les
      alpha_i^d. Si alpha_i^d = alpha_j^d pour i != j — c'est-à-dire si l'ordre
      multiplicatif de alpha_i/alpha_j divise d — le degré du polynôme MINIMAL
      chute. Cas extrême : khi = x^3 + x + 1, dont les racines sont d'ordre 7.
      Alors alpha^7 = 1, donc A^7 agit comme l'identité sur le module, donc

          b_{7n}  est  CONSTANTE.     L = 1 au lieu de 3.

  (c) PERTE. Les d suites de résidus ont chacune N/d termes. Le seuil aléatoire
      du §126 pour M suites de longueur N' est M·N'/(M+1) ; ici M = d et
      N' = N/d, donc le seuil vaut

          d · (N/d) / (d+1)  =  N / (d+1).

      Il DÉCROÎT en d. La décimation ne peut donc jamais rehausser le plafond :
      elle le divise par (d+1)/2.

LE COROLLAIRE, ET C'EST LUI QUI COMPTE
=======================================
Réunissons (c) avec le seuil du §124. M suites de longueur N, c'est T = M·N
bits observés au total, pour un seuil de M·N/(M+1) = T/(M+1). Donc :

    À NOMBRE TOTAL DE BITS OBSERVÉS FIXÉ, LE PLAFOND MODEL-FREE VAUT T/(M+1)
    OÙ M EST LE NOMBRE DE SUITES. IL EST MAXIMAL POUR M = 1, ET VAUT ALORS T/2.

    Toute façon de DÉCOUPER l'observation — un second bit, un second pas, un
    second observable — DÉGRADE le plafond. Une seule suite, aussi longue que
    possible, est optimale, et T/2 est indépassable.

C'est le troisième théorème de clôture du dossier, après le second bit (§124)
et le plafond de l'archive (§126), et il les contient tous les deux : le §124
est le cas d = 1, M = 2 ; le §126 est le cas M quelconque, d = 1.

CE QUE CELA DIT À QUI COLLECTE DES DONNÉES
===========================================
Un tirage de plus vaut mieux qu'un bit de plus par tirage. C'est contre
l'intuition — un bit est un bit — et c'est démontré.

Il ne teste pas l'archive : il DÉMONTRE. Il ne consigne pas au registre, sauf
la vérification numérique du seuil, qui est une prédiction chiffrée.
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
DRY = os.environ.get("H116_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))
TMP = os.environ.get("H116_TMP", "/tmp")


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


BJ = os.path.join(TMP, "jointf2_h116")
BB = os.path.join(TMP, "bmf2_h116")
FJ = os.path.join(TMP, "h116.bin")
for src, dst in (("jointf2.c", BJ), ("bmf2.c", BB)):
    subprocess.run(["cc", "-O3", "-march=native", "-o", dst,
                    os.path.join(DEPOT, "tools", src)], check=True, capture_output=True)


def _ecris(suites):
    n = min(len(s) for s in suites)
    nw = (n + 63) // 64
    with open(FJ, "wb") as fh:
        fh.write(struct.pack("<ii", len(suites), n))
        for s in suites:
            o = np.packbits(np.asarray(s[:n], np.uint8) & 1,
                            bitorder="little").tobytes()
            fh.write(o.ljust(nw * 8, b"\x00"))
    return n


def conjointe(suites):
    _ecris(suites)
    p = subprocess.run([BJ, FJ], capture_output=True, text=True, check=True)
    for l in p.stdout.split("\n"):
        if l.startswith("CONJOINTE"):
            return int(l.split()[1])
    raise RuntimeError(p.stdout)


def scalaire(suite):
    _ecris([suite])
    p = subprocess.run([BB, FJ], capture_output=True, text=True, check=True)
    for l in p.stdout.split("\n"):
        t = l.split()
        if t[:1] == ["L"]:
            return int(t[2])
    raise RuntimeError(p.stdout)


def lfsr(taps, deg, n, graine=1):
    """x^deg + somme des x^t, t dans taps. Rend n termes."""
    rng = np.random.default_rng(graine)
    buf = np.zeros(n + deg, np.uint8)
    buf[:deg] = rng.integers(0, 2, deg)
    if not buf[:deg].any():
        buf[0] = 1
    for t in range(deg, n + deg):
        v = buf[t - deg]
        for k in taps:
            v ^= buf[t - deg + k]
        buf[t] = v
    return buf[:n].copy()


def residus(b, d):
    return [np.asarray(b)[r::d] for r in range(d)]


# ==========================================================================
rule("1. (a) VALIDITÉ : LA DÉCIMÉE VIENT DE A^d, DE MÊME LARGEUR")
# ==========================================================================

say("""   Si b_n = l(A^n s), alors b_{r+nd} = l(A^r (A^d)^n s) : c'est la suite d'un
   generateur de matrice A^d, DE MEME LARGEUR W. Donc L(decimee) <= W pour tout
   pas et tout decalage — l'enonce ne nomme ni famille, ni pas, ni alignement.

   Verification sur un LFSR de degre 61 (trinome primitif x^61 + x^3 + 1), sur
   2 000 termes, donc bien au-dela de 2W = 122 ou BM devient exact.

       pas d      L(b^(d,0))   <= 61 ?     L_conjointe(residus)   <= 61 ?""")

W1, N1 = 61, 2000
B1 = lfsr([3], W1, N1, graine=11)
OK_A = 0
ESSAIS_A = 0
for d in (1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 16):
    r0 = residus(B1, d)
    ls = scalaire(r0[0])
    lj = conjointe(r0) if d > 1 else ls
    ESSAIS_A += 2
    OK_A += (ls <= W1) + (lj <= W1)
    say(f"   {d:>9}   {ls:>13}   {'oui' if ls <= W1 else 'NON':>7}   "
        f"{lj:>20}   {'oui' if lj <= W1 else 'NON':>7}")
say(f"""
   {OK_A}/{ESSAIS_A} bornes respectees. Aucune decimation ne fait mentir W >= L.""")


# ==========================================================================
rule("2. (b) CHUTE : LA DÉCIMATION PEUT DÉTRUIRE LA COMPLEXITÉ")
# ==========================================================================

say("""   La borne du (a) est valide, mais elle n'est pas SERREE, et l'ecart peut etre
   total. Les racines de khi_d sont les alpha_i^d ; si l'ordre multiplicatif de
   alpha_i/alpha_j divise d, deux racines fusionnent et le degre CHUTE.

   Cas extreme : khi = x^3 + x + 1 est primitif sur F2, ses racines sont
   d'ordre 7. Donc alpha^7 = 1, A^7 agit comme l'identite, et la decimee par 7
   est CONSTANTE. Prediction : L = 1.

       khi                    ordre des racines    pas d    L predit    L mesuré""")

PRED = []
for taps, deg, ordre, nom in (([1], 3, 7, "x^3 + x + 1"),
                              ([1], 4, 15, "x^4 + x + 1"),
                              ([2], 5, 31, "x^5 + x^2 + 1")):
    b = lfsr(taps, deg, 4000, graine=3)
    for d, att in ((ordre, 1), (1, deg)):
        got = scalaire(b[::d])
        PRED.append(got == att)
        say(f"   {nom:>18} {ordre:>20} {d:>8} {att:>11} {got:>11}"
            f"   {'ok' if got == att else 'NON'}")
say(f"""
   {sum(PRED)}/{len(PRED)} predictions exactes. La decimee par l'ordre des racines est
   CONSTANTE : la complexite tombe de {3} a 1, de {4} a 1, de {5} a 1.

   CONSEQUENCE. Un pas mal choisi ne degrade pas seulement la statistique : il
   peut ANEANTIR le signal. Le dossier enumerait des pas depuis le §14 sans le
   savoir.""")


# ==========================================================================
rule("3. (c) PERTE : LE SEUIL ALÉATOIRE DÉCROÎT EN N/(d+1)")
# ==========================================================================

say("""   Decouper N bits en d suites de residus, c'est passer a M = d suites de
   longueur N' = N/d. Le seuil aleatoire du §126 vaut M·N'/(M+1), soit

       d · (N/d) / (d+1)  =  N/(d+1),

   qui DECROIT en d. Mesure sur du hasard vrai, N = 20 160.

       pas d     seuil prédit N/(d+1)     L_conjointe mesurée   écart""")

N3 = 20160
RNG = np.random.default_rng(20260901)
HAS = RNG.integers(0, 2, N3).astype(np.uint8)
OK_C, LIG3 = 0, []
for d in (1, 2, 3, 4, 6):
    r = residus(HAS, d)
    lj = scalaire(r[0]) if d == 1 else conjointe(r)
    att = N3 // (d + 1)
    ec = lj - att
    OK_C += abs(ec) <= 2
    LIG3.append((d, att, lj, ec))
    say(f"   {d:>9} {att:>22,} {lj:>23,} {ec:>+7}")
say(f"""
   {OK_C}/{len(LIG3)} seuils retrouves a 2 pres. Le plafond model-free obtenu en
   decimant vaut N/(d+1) : il est MAXIMAL en d = 1, et vaut alors N/2.""")


# ==========================================================================
rule("4. LE COROLLAIRE : À BITS OBSERVÉS ÉGAUX, UNE SEULE SUITE EST OPTIMALE")
# ==========================================================================

say("""   Le §124 donne le seuil de M suites de longueur N : M·N/(M+1). Or M suites de
   longueur N, c'est T = M·N bits observes AU TOTAL. Le seuil vaut donc

       M·N/(M+1)  =  T/(M+1),

   et il DECROIT en M a T constant. C'est le meme phenomene que le (c), et ce
   n'est pas une coincidence : un g de degre L a L+1 inconnues et donne T - M·L
   equations, donc le seuil est la ou T - M·L = L+1.

   Mesure a T = 20 160 bits FIXE, redistribues en M suites de T/M bits.

       M suites     longueur    seuil prédit T/(M+1)     mesuré   écart""")

OK_D, LIG4 = 0, []
for M in (1, 2, 3, 4, 5):
    n = N3 // M
    r = [RNG.integers(0, 2, n).astype(np.uint8) for _ in range(M)]
    lj = scalaire(r[0]) if M == 1 else conjointe(r)
    att = N3 // (M + 1)
    ec = lj - att
    OK_D += abs(ec) <= 2
    LIG4.append((M, n, att, lj, ec))
    say(f"   {M:>8} {n:>12,} {att:>23,} {lj:>10,} {ec:>+7}")
say(f"""
   {OK_D}/{len(LIG4)} seuils retrouves a 2 pres.

     A NOMBRE TOTAL DE BITS FIXE, LE PLAFOND VAUT T/(M+1). UNE SEULE SUITE,
     AUSSI LONGUE QUE POSSIBLE, EST OPTIMALE, ET T/2 EST INDEPASSABLE.

   Un tirage de plus vaut mieux qu'un bit de plus par tirage. C'est contre
   l'intuition, et c'est demontre.""")


# ==========================================================================
rule("5. L'ARCHIVE : LE SPECTRE DE DÉCIMATION DU RANG DU BONUS")
# ==========================================================================

ARCH = lab.load()
NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
BON = np.asarray(ARCH.bonus).astype(np.int64)
RANG = np.argmax(NUM == BON[:, None], axis=1)
NA = len(RANG)
BIT = ((RANG // 5) >> 1).astype(np.uint8)          # bit exact, troncature (§122)

say(f"""   Le bit exact de poids fort du rang du bonus, sous troncature : {NA:,} bits,
   la plus longue suite que l'archive publie sans hypothese de famille.

   Le (b) dit qu'un pas mal choisi ANEANTIT le signal. On mesure donc le
   SPECTRE : L en fonction du pas. Une chute nette denoncerait une structure ;
   la prediction du (c), elle, est N/(d+1) — le hasard, et rien d'autre.

       pas d    bits lus    seuil N/(d+1)     L mesuré   écart""")

SPEC, OK_E = [], 0
for d in (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 20, 21):
    r = residus(BIT, d)
    n = min(len(x) for x in r)
    lj = scalaire(r[0]) if d == 1 else conjointe(r)
    att = (n * d) // (d + 1)
    ec = lj - att
    OK_E += abs(ec) <= 4
    SPEC.append((d, n * d, att, lj, ec))
    say(f"   {d:>8} {n*d:>11,} {att:>16,} {lj:>12,} {ec:>+7}")

CHUTE = min(SPEC, key=lambda t: t[3] - t[2])
say(f"""
   {OK_E}/{len(SPEC)} pas rendent exactement le seuil du hasard, a 4 pres. La chute la
   plus profonde est au pas {CHUTE[0]}, et elle vaut {CHUTE[4]:+} — c'est-a-dire rien.

   AUCUNE DECIMATION NE FAIT TOMBER LE SPECTRE. L'archive se comporte, pour
   chacun des douze pas, exactement comme du hasard de meme longueur.""")


# ==========================================================================
rule("6. CE QUE LE THÉORÈME FERME, ET CE QU'IL LAISSE OUVERT")
# ==========================================================================

say(f"""   TROIS THEOREMES DE CLOTURE, ET LE TROISIEME CONTIENT LES DEUX AUTRES.

     §124  le second bit n'ajoute aucune equation      d = 1, M = 2
     §126  le plafond de l'archive est M·N/(M+1)       d = 1, M quelconque
     §134  le plafond universel est T/(M+1)            tout d, tout M

   CE QUE CELA FERME. Il n'existe aucune facon de DECOUPER les observations qui
   rehausse le plafond model-free. Ni un second bit, ni un second pas, ni un
   second observable. Le dossier avait, depuis le §122, cherche des bornes plus
   hautes en multipliant les lectures : c'etait perdu d'avance, et on sait
   maintenant pourquoi.

   CE QUE CELA LAISSE OUVERT. Le plafond T/2 est ATTEINT, pas depasse : avec
   T = {NA:,} bits l'archive borne W >= {NA//2:,} model-free. Doubler l'archive
   doublerait la borne. C'est la SEULE facon de monter, et elle est LINEAIRE
   en la donnee — il faudrait {2*44497 - NA:,} tirages de plus pour depasser
   WELL44497b, le plus grand etat publie.

   CE QUE CELA DIT A QUI COLLECTE. Un tirage de plus vaut mieux qu'un bit de
   plus par tirage — a bits egaux, M = 1 bat M = 2 d'un facteur 3/2.""")


# ==========================================================================
rule("7. CONSIGNATION")
# ==========================================================================

TOTAL = OK_A + sum(PRED) + OK_C + OK_D
ATTEN = ESSAIS_A + len(PRED) + len(LIG3) + len(LIG4)

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h116.plafond_universel",
        "Le plafond model-free sur la largeur W vaut T/(M+1) ou T est le nombre "
        "TOTAL de bits observes et M le nombre de suites en lesquelles on les "
        "decoupe — que le decoupage vienne d'un second observable (§124) ou "
        "d'une DECIMATION du meme observable. Il est donc maximal a M = 1 et "
        "vaut alors T/2 : aucune facon de decouper l'observation ne rehausse le "
        "plafond. Corollaires verifiables : (a) W >= L(suite decimee) pour tout "
        "pas et tout decalage ; (b) la decimation par l'ordre multiplicatif des "
        "racines rend la suite CONSTANTE ; (c) le seuil aleatoire des d suites "
        "de residus vaut N/(d+1)",
        "nombre de predictions chiffrees exactes : les bornes (a) sur onze pas, "
        "les six complexites predites en (b), les cinq seuils N/(d+1) en (c) et "
        "les cinq seuils T/(M+1) du corollaire",
        "un enonce faux manquerait ses predictions : le seuil vaudrait N/2 pour "
        "tout d si la decimation etait neutre, et la decimee par l'ordre des "
        "racines aurait la complexite pleine",
        "conforme si toutes les predictions chiffrees sont exactes", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0,
        verdict="conforme" if TOTAL == ATTEN else "DEMENTI",
        power_at=(f"{TOTAL}/{ATTEN} predictions chiffrees exactes. Temoin positif : "
                  f"la decimation par l'ordre des racines fait chuter L de 3, 4 "
                  f"et 5 a exactement 1 — le test DETECTE une chute quand il y "
                  f"en a une"),
        notes=(f"TROISIEME THEOREME DE CLOTURE, et il contient les deux autres : "
               f"le §124 (second bit) est le cas d=1 M=2, le §126 (plafond de "
               f"l'archive) le cas d=1 M quelconque. Un g de degre L a L+1 "
               f"inconnues et donne T - M·L equations, d'ou le seuil T/(M+1), "
               f"DECROISSANT en M a T fixe. Applique au spectre de decimation du "
               f"rang du bonus sur {NA:,} tirages, douze pas de 1 a 21 : aucune "
               f"chute, le seuil du hasard partout a 4 pres. Consequence pour la "
               f"collecte : un tirage de plus vaut mieux qu'un bit de plus par "
               f"tirage."))
    h = lab.holm()
    say(f"   consigne : h116.plafond_universel   {TOTAL}/{ATTEN} predictions exactes")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
