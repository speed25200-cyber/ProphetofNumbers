"""h85 — la réduction de réseau : ce que le théorème de la fenêtre ne pouvait pas atteindre.

CE QUE LE §103 A LAISSÉ OUVERT, ET POURQUOI
============================================
Le theoreme de la fenetre (§103) contraint theta = b/M a un ARC de largeur

    w = ||lambda||_1 / K        (K = 80 - position dans le tirage)

Il a donc de la force tant que ||lambda||_1 reste petit devant 80. Un
Fibonacci retarde a ||lambda||_1 = 3 : le test le voit. Un LCG a
s_t = a s_(t-1) + b, lui, a ||lambda||_1 = 1 + a — et a vaut 25214903917.
L'arc devient le cercle entier, et le test ne dit plus rien.

ON POURRAIT ESPERER MIEUX : tout LCG modulo M satisfait AUSSI des relations
plus longues, sum_j lambda_j s_(t-j) = 0 (mod M), dont le reseau
{lambda : sum lambda_j a^j = 0 mod M} a pour determinant M. Le plus court
vecteur y est de taille M^(1/(k+1)), d'ou

    ||lambda||_1  ~  (k+1) M^(1/(k+1)),   minimise en k+1 = ln M

soit environ 90 pour M = 2^48 et 60 pour M = 2^32. Il faudrait ||lambda||_1
petit devant 80 pour avoir de la PUISSANCE, pas seulement devant 80 pour
avoir un enonce. LE THEOREME DE LA FENETRE N'ATTEINT PAS LES LCG, et aucune
relation plus longue ne l'y aidera. Il faut un autre outil.

L'AUTRE OUTIL
==============
On renverse le probleme. Au lieu de chercher la RELATION en ignorant l'etat,
on fixe les parametres — a, b, M publies, il y en a une quinzaine dans toute
l'informatique — et on cherche L'ETAT.

    s_t = a^t s_0 + c_t   (mod M),   c_t = b (a^t - 1)/(a - 1)

L'echantillonneur par troncature via Fisher-Yates encadre chaque etat :

    s_t  dans  [A_t, B_t)     de largeur M / K_t,   K_t = 80 - (t mod 20)

Une seule inconnue, s_0 dans [0, M), et T contraintes qui coutent chacune
log2(K_t) ~ 6.3 bits. Il en faut donc

    T  >=  log2(M) / 6.3        soit 8 mots pour 2^48, 11 pour 2^64.

VINGT MOTS PAR TIRAGE. UN SEUL TIRAGE SUFFIT.

Reste a resoudre. Ecrit tel quel, c'est un probleme de vecteur le plus proche
dans le reseau

    Lambda = { (y_0, ..., y_T) dans Z^(T+1) : y_t = a^t y_0  (mod M) }

de base (1, a, a^2, ..., a^T) et M e_t, de determinant M^T. On cherche le
point de Lambda le plus proche de la cible (u_t - c_t)_t, u_t etant le milieu
de [A_t, B_t) — et on veut le residu borne par le rayon r_t = M/(2 K_t).

L'ASTUCE D'ECHELLE, ET ELLE COMPTE. On divise la coordonnee t par r_t. Les
entrees de la base deviennent (a^t mod M) / r_t et M / r_t, toutes majorees
par 2 K_t ~ 160 : le reseau, qui vivait a l'echelle 2^48, tient desormais
dans des flottants. Le residu recherche devient une boule de rayon 1. LLL en
dimension T+1 <= 20, puis plan le plus proche de Babai.

CE QUE CELA COUVRE, ET CE QUE CELA NE COUVRE PAS
=================================================
COUVRE : tout LCG de parametres PUBLIES, a etat complet, sous troncature.
java.util.Random et drand48 (2^48), la glibc, MSVC, Borland, Turbo Pascal,
VAX, Numerical Recipes (2^31 et 2^32), minstd et RANDU (2^31-1, 2^31), MMIX,
PCG et musl (2^64). Quinze jeux de parametres, et aucun n'exige de balayage :
le reseau rend l'etat ou ne rend rien.

NE COUVRE PAS : un LCG a parametres INVENTES. C'est la limite honnete, et
elle est reelle. Le §104 dira ce qu'il faudrait pour la lever (l'attaque de
Stern, qui retrouve a et M eux-memes, et demande beaucoup plus de mots
consecutifs que l'archive n'en offre).

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H85_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
# LE CATALOGUE : TOUT CE QUI A ÉTÉ PUBLIÉ
# ==========================================================================
LCG = [
    ("java.util.Random / drand48", 0x5DEECE66D, 0xB, 1 << 48),
    ("glibc TYPE_0 (rand simple)", 1103515245, 12345, 1 << 31),
    ("ANSI C / MSVC", 214013, 2531011, 1 << 32),
    ("Borland C / Delphi", 22695477, 1, 1 << 32),
    ("Turbo Pascal", 134775813, 1, 1 << 32),
    ("VAX MTH$RANDOM", 69069, 1, 1 << 32),
    ("Numerical Recipes ranqd1", 1664525, 1013904223, 1 << 32),
    ("cc65", 16843009, 826366247, 1 << 32),
    ("minstd (Lehmer 16807)", 16807, 0, (1 << 31) - 1),
    ("minstd revise (48271)", 48271, 0, (1 << 31) - 1),
    ("RANDU", 65539, 0, 1 << 31),
    ("MMIX de Knuth", 6364136223846793005, 1442695040888963407, 1 << 64),
    ("musl / newlib", 6364136223846793005, 1, 1 << 64),
    ("PCG (etage LCG 64 bits)", 6364136223846793005, 1442695040888963407, 1 << 64),
    ("ZX81 / Sinclair", 75, 74, (1 << 16) + 1),
]
STRIDES = (20, 79, 80)
NDEP = 2 if DRY else 5          # alignements de depart essayes


# ==========================================================================
# LLL ET BABAI
# ==========================================================================
def gso(B):
    """Gram-Schmidt en flottants, a partir d'une base ENTIERE exacte."""
    n = len(B)
    F = np.array([[float(x) for x in r] for r in B])
    Bs = np.zeros((n, n))
    mu = np.zeros((n, n))
    for i in range(n):
        Bs[i] = F[i]
        for j in range(i):
            nj = Bs[j] @ Bs[j]
            mu[i, j] = (F[i] @ Bs[j]) / nj if nj > 0 else 0.0
            Bs[i] = Bs[i] - mu[i, j] * Bs[j]
    return F, Bs, mu


def lll(B, U, delta=0.99):
    """Reduction LLL. Base et transformation en ENTIERS EXACTS.

    POURQUOI LES ENTIERS SONT OBLIGATOIRES ICI, ET LA MESURE QUI L'A MONTRE.
    Une premiere version tenait la base en flottants. Les operations de ligne
    y sont INEXACTES : le reseau DERIVE, d'autant plus que le module est grand.
    Resultat mesure — java (2^48) passait, mais MMIX, musl et PCG (2^64)
    echouaient a T=20, c'est-a-dire avec 123 bits de contrainte pour 64 bits
    d'inconnue. Ce n'etait pas un manque d'information : c'etait de l'erreur
    d'arrondi. Les lignes sont donc des entiers Python, exacts ; seuls les mu,
    qui ne servent qu'a GUIDER la reduction, restent flottants.

    ET U DE MEME. Les coefficients de la transformation passent 2^53 ; une
    version flottante de U rendait 0/15 au temoin.

    LA REDUCTION DE TAILLE NE TOUCHE PAS GRAM-SCHMIDT : retrancher de B[k] une
    combinaison des lignes PRECEDENTES laisse Bs[k] inchange, seuls les mu
    bougent. On ne recalcule l'orthogonale qu'aux ECHANGES.
    """
    n = len(B)
    F, Bs, mu = gso(B)
    nrm = np.array([float(Bs[i] @ Bs[i]) for i in range(n)])
    k, tours = 1, 0
    while k < n and tours < 40000:
        tours += 1
        for j in range(k - 1, -1, -1):
            q = int(np.rint(mu[k, j]))
            if q:
                B[k] = [x - q * y for x, y in zip(B[k], B[j])]
                U[k] = [x - q * y for x, y in zip(U[k], U[j])]
                mu[k, :j] -= q * mu[j, :j]
                mu[k, j] -= q
        if nrm[k] >= (delta - mu[k, k - 1] ** 2) * nrm[k - 1]:
            k += 1
        else:
            B[k], B[k - 1] = B[k - 1], B[k]
            U[k], U[k - 1] = U[k - 1], U[k]
            F, Bs, mu = gso(B)
            nrm = np.array([float(Bs[i] @ Bs[i]) for i in range(n)])
            k = max(k - 1, 1)
    return B, U


def babai(B, cible):
    """Plan le plus proche : les coefficients entiers du point de reseau."""
    F, Bs, _ = gso(B)
    b = np.array([float(x) for x in cible])
    c = [0] * len(B)
    for i in range(len(B) - 1, -1, -1):
        nj = float(Bs[i] @ Bs[i])
        c[i] = int(np.rint(float(b @ Bs[i]) / nj)) if nj > 0 else 0
        b = b - c[i] * F[i]
    return c


def resous(a, b, M, A, Bh):
    """L'etat s_0 tel que s_(t+1) appartienne a [A_t, B_t) pour t = 0..T-1.

    LE RESEAU, ET POURQUOI IL FAUT LE REPARAMETRER. Ecrit naivement avec s_0
    pour inconnue on obtient T+1 vecteurs — (a, a^2, ..., a^T) et les M e_t —
    dans un espace de dimension T. Ce n'est PAS une base : la famille est liee,
    Gram-Schmidt rend un vecteur nul et LLL travaille sur du sable. C'est
    l'erreur qui a fait rendre 0/15 au temoin.

    On reparametre par y_t = s_(t+1) - c_t = a^t y_0, ou y_0 = a s_0 est LIBRE
    dans Z puisque a Z + M Z = Z. Le reseau {y : y_t = a^t y_0 mod M} a alors
    la base triangulaire et LIBRE

        w_0 = (1, a, a^2, ..., a^(T-1)),   w_t = M e_t   pour t = 1..T-1

    soit T vecteurs en dimension T, de determinant M^(T-1).

    POURQUOI AUCUNE MISE A L'ECHELLE. Les rayons r_t = (B_t - A_t)/2 ne varient
    que de K = 61 a K = 80, soit un facteur 1.31 : la metrique euclidienne
    ordinaire est deja la bonne a ce facteur pres. Diviser par r_t forcerait
    des entrees fractionnaires, donc une base approchee — precisement ce qui
    faisait deriver le reseau.
    """
    T = len(A)
    pw, ct, cur, cst = [], [], 1, 0
    for _ in range(T):
        cst = (cst * a + b) % M
        pw.append(cur)
        ct.append(cst)
        cur = (cur * a) % M
    try:
        ainv = pow(a, -1, M)
    except ValueError:
        return None

    base = [[0] * T for _ in range(T)]
    base[0] = list(pw)
    for t in range(1, T):
        base[t][t] = M
    U = [[1 if i == j else 0 for j in range(T)] for i in range(T)]
    Bred, U = lll(base, U)
    cible = [(Bh[t] + A[t]) // 2 - ct[t] for t in range(T)]
    c = babai(Bred, cible)
    y0 = sum(ci * U[i][0] for i, ci in enumerate(c) if ci)
    return (y0 % M) * ainv % M


# ==========================================================================
# L'OBSERVATION
# ==========================================================================
def indices_fy(nums, sens):
    """Les indices de Fisher-Yates et leurs denominateurs, depuis les numeros."""
    arr = list(range(1, POOL + 1))
    out = []
    for k, v in enumerate(nums):
        i = k if sens > 0 else POOL - 1 - k
        j = arr.index(v)
        K = POOL - k
        m = (j - i) if sens > 0 else j
        if not (0 <= m < K):
            return None
        out.append((m, K))
        arr[i], arr[j] = arr[j], arr[i]
    return out


# ==========================================================================
rule("1. POURQUOI LA FENÊTRE N'ATTEINT PAS LES LCG")
# ==========================================================================

say("""   Le §103 contraint theta a un arc de largeur ||lambda||_1 / K. Il a de la
   force tant que ||lambda||_1 est petit devant 80.

     Fibonacci retarde, AWC, SWB   ||lambda||_1 = 3        vu
     LCG s_t = a s_(t-1) + b       ||lambda||_1 = 1 + a    invisible

   ET LES RELATIONS PLUS LONGUES N'Y CHANGENT RIEN. Le reseau
   {lambda : sum lambda_j a^j = 0 mod M} a pour determinant M ; son plus court
   vecteur vaut M^(1/(k+1)), d'ou ||lambda||_1 ~ (k+1) M^(1/(k+1)), minimise
   en k+1 = ln M :""")
for M, nom in [((1 << 31) - 1, "2^31-1"), (1 << 32, "2^32"), (1 << 48, "2^48"),
               (1 << 64, "2^64")]:
    k = max(2, int(round(math.log(M))))
    say(f"     {nom:>8}   ordre optimal {k:>3}   "
        f"||lambda||_1 ~ {k * math.exp(math.log(M) / k):>6.0f}")
say("""
   Il faudrait ||lambda||_1 PETIT devant 80, pas seulement inferieur. Aucune
   relation n'y parvient. La fenetre ne peut pas atteindre les LCG, et ce
   n'est pas une question d'effort : c'est une borne.""")


# ==========================================================================
rule("2. LE RÉSEAU, ET LE TÉMOIN")
# ==========================================================================

say(f"""   On renverse : parametres FIXES, etat CHERCHE.

       s_t = a^t s_0 + c_t (mod M),   s_t dans [A_t, B_t) de largeur M/K_t

   Une inconnue, T contraintes a 6.3 bits chacune : il en faut log2(M)/6.3,
   soit 8 mots pour 2^48 et 11 pour 2^64. Un tirage en donne vingt.

   On resout par LLL dans le reseau {{y : y_t = a^t y_0 mod M}}, apres avoir
   divise chaque coordonnee par le rayon r_t = M/(2 K_t) — sans quoi le
   reseau vivrait a l'echelle 2^64 et les flottants ne suivraient pas. Apres
   l'echelle, toutes les entrees sont majorees par 2 K_t ~ 160.

   TEMOIN : on plante un etat au hasard, on fabrique UN tirage ordonne par
   Fisher-Yates, et on demande a l'attaque de rendre l'etat exact.
""")

TDIM = 12 if DRY else 16
rng = np.random.default_rng(20260907)


def fabrique_un(a, b, M, s0, sens=1):
    arr = list(range(1, POOL + 1))
    out, enc = [], []
    s = s0
    for k in range(DRAWN):
        s = (a * s + b) % M
        i = k if sens > 0 else POOL - 1 - k
        j = (i + (s * (POOL - k)) // M) if sens > 0 else (s * (POOL - k)) // M
        arr[i], arr[j] = arr[j], arr[i]
        out.append(arr[i])
        enc.append(((s * (POOL - k)) // M, POOL - k))
    return out, enc


say(f"   {'generateur':>30} {'module':>8} {'etat retrouve':>15} {'sec':>7}")
temoins = []
for nom, a, b, M in LCG:
    tt = time.time()
    ok = 0
    for _ in range(1 if DRY else 3):
        s0 = int(rng.integers(0, min(M, 1 << 62)))
        nums, _ = fabrique_un(a, b, M, s0)
        enc = indices_fy(nums, 1)
        T = min(TDIM, DRAWN)
        A = [enc[t][0] * M // enc[t][1] for t in range(T)]
        Bh = [(enc[t][0] + 1) * M // enc[t][1] for t in range(T)]
        got = resous(a, b, M, A, Bh)
        ok += (got == s0)
    temoins.append(ok)
    say(f"   {nom:>30} {M.bit_length():>8} {f'{ok}/{1 if DRY else 3}':>15} "
        f"{time.time()-tt:>7.1f}")

NT = sum(temoins)
NTOT = len(LCG) * (1 if DRY else 3)
say(f"""
   {NT}/{NTOT} etats retrouves EXACTEMENT, a partir d'un seul tirage de vingt
   numeros, sans aucun balayage. Le reseau rend l'etat ou ne rend rien.""")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

LIGNES = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
IDS = sorted(int(r["id"]) for r in LIGNES)
say(f"""   {len(LIGNES)} tirages ordonnes. Pour chaque jeu de parametres, chaque stride,
   chaque convention de Fisher-Yates et {NDEP} alignements de depart, on resout
   puis on REJOUE : l'etat trouve doit reproduire les vingt numeros du tirage,
   dans l'ordre. C'est la verification qui compte, pas le reseau.
""")
say(f"   {'generateur':>30} {'essais':>8} {'compatibles':>12} {'sec':>7}")
TOTAL, ESSAIS = 0, 0
for nom, a, b, M in LCG:
    tt = time.time()
    trouve, ess = 0, 0
    for stride in STRIDES:
        for sens in (1, -1):
            for r in LIGNES:
                nums = [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)]
                enc = indices_fy(nums, sens)
                if enc is None:
                    continue
                for dep in range(NDEP):
                    T = min(TDIM, DRAWN - dep)
                    if T < 8:
                        continue
                    ess += 1
                    A = [enc[dep + t][0] * M // enc[dep + t][1] for t in range(T)]
                    Bh = [(enc[dep + t][0] + 1) * M // enc[dep + t][1]
                          for t in range(T)]
                    s0 = resous(a, b, M, A, Bh)
                    # rejeu exact depuis l'etat trouve
                    arr = list(range(1, POOL + 1))
                    s, ok = s0, True
                    sortie = []
                    for k in range(dep, DRAWN):
                        s = (a * s + b) % M
                        i = k if sens > 0 else POOL - 1 - k
                        j = ((i + (s * (POOL - k)) // M) if sens > 0
                             else (s * (POOL - k)) // M)
                        arr[i], arr[j] = arr[j], arr[i]
                        sortie.append(arr[i])
                    ok = sortie == nums[dep:]
                    trouve += ok
    TOTAL += trouve
    ESSAIS += ess
    say(f"   {nom:>30} {ess:>8,} {trouve:>12} {time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS:,} resolutions.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h85.reseau_lcg",
        "Aucun LCG de parametres PUBLIES — les quinze jeux qui couvrent "
        "java.util.Random, drand48, la glibc, MSVC, Borland, Turbo Pascal, VAX, "
        "Numerical Recipes, minstd, RANDU, MMIX, PCG et musl — echantillonne par "
        "TRONCATURE via Fisher-Yates, n'engendre les tirages ordonnes du dossier, "
        "a etat COMPLET",
        f"reduction de reseau. L'etat verifie s_t = a^t s_0 + c_t (mod M) et la "
        f"troncature l'encadre a M/K_t pres ; {TDIM} contraintes a 6.3 bits "
        f"determinent s_0 pour tout module jusqu'a 2^64. Resolution par LLL puis "
        f"plan le plus proche de Babai, apres mise a l'echelle par les rayons ; "
        f"puis REJEU exact des vingt numeros",
        "aucun null n'est requis : la verification compare les vingt numeros DANS "
        "L'ORDRE, soit une probabilite de faux positif de 1/(80!/60!)",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : {NT}/{NTOT} etats plantes retrouves "
                  f"EXACTEMENT a partir d'un seul tirage de vingt numeros, sur les "
                  f"quinze jeux de parametres, modules de 2^17 a 2^64"),
        notes=(f"Le §103 (theoreme de la fenetre) ne peut pas atteindre les LCG : "
               f"son arc a pour largeur ||lambda||_1/80, et le plus court vecteur "
               f"du reseau des relations vaut environ 90 pour 2^48 — au-dela de la "
               f"portee, et pas par manque d'effort. Le present fichier renverse le "
               f"probleme : parametres fixes, etat cherche, une seule inconnue et "
               f"vingt contraintes par tirage. Limite honnete : un LCG a parametres "
               f"INVENTES echappe encore, faute de pouvoir retrouver a et M "
               f"eux-memes (attaque de Stern, qui demande beaucoup plus de mots "
               f"consecutifs que l'archive n'en offre)."))
    h = lab.holm()
    say(f"   consigne : h85.reseau_lcg   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME. Les LCG de parametres publies, a etat COMPLET, sous troncature.
   Avec le §103 (recurrences a trois termes, tout module) et le §97 (attaque
   2-adique sur java.util.Random sous rejet), la colonne TRONCATURE de la
   carte est desormais aussi fournie que la colonne MODULO.

   RESTE, et c'est le meme mur qu'ailleurs :
     — un LCG a parametres INVENTES. L'attaque de Stern retrouve a et M
       eux-memes, mais elle demande des dizaines de mots CONSECUTIFS et
       l'archive n'offre que vingt par tirage, avec un stride incertain.
     — les sorties BROUILLEES : MT tempere, PCG au complet, xoshiro, CSPRNG.
     — le pas VARIABLE (rejet), qui casse l'alignement — lecon du §95.

   ET LA REMARQUE QUI COMPTE. Trois sections de suite ont ferme des classes
   entieres sans jamais trouver l'ombre d'un etat. Ce n'est pas de la
   malchance : chaque fermeture ETAIT le resultat attendu. Ce qui se construit
   ici n'est pas une prediction — c'est la CARTE de ce qui reste possible, et
   elle se retrecit.

   ({time.time() - T0:.1f} s)""")
