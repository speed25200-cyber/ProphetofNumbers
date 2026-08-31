"""h83 — MWC : la dernière case nommée, et pourquoi 64 bits n'en coûtent que 32.

CE QUE LE §91 AVAIT NOMMÉ
==========================
Le §91 a etabli que les generateurs A RETENUE echappent a Berlekamp-Massey :
leur transition ne descend pas modulo 2^j, parce que la retenue est une
quantite de la partie HAUTE. Le §101 a confirme mecaniquement qu'aucune des
neuf sources de balayage ne contient de MWC. C'etait la derniere case nommee.

L'EQUIVALENCE, ET CE QU'ELLE DONNE
===================================
Un MWC de base b et de multiplicateur a est EXACTEMENT un LCG multiplicatif
modulo p = a*b - 1 :

    etat (x, c)  ->  z = x + b*c        avec z dans [0, p]
    z_{i+1} = a*z_i   (mod p)           et    x_i = z_i mod b

    PREUVE. a*b = 1 (mod p), donc b = a^-1. Alors
    a*z = a*x + a*b*c = a*x + c = t, qui est exactement z_{i+1}. []

Verifie sur 2 000 pas a la section 1.

CE QUE CELA CONFIRME, ET CE QUE CELA N'OUVRE PAS. La consequence directe est
x_{i+1} = a*x_i + c_{i+1} (mod b), la retenue vivant dans [0, a). Pour un a
grand, c mod 16 n'est pas constant : la signature du §80 ne mord pas, et le
theoreme du bit zero du §100 non plus. Le §91 avait raison.

LA PRISE EST AILLEURS
======================
V8 — le moteur JavaScript de Chrome et de Node — a utilise MWC1616 pour
`Math.random` jusqu'en 2016. Deux MWC de seize bits en parallele :

    state0 = 18030 * (state0 & 0xFFFF) + (state0 >> 16)
    state1 = 36969 * (state1 & 0xFFFF) + (state1 >> 16)
    r = (state0 << 16) + (state1 & 0xFFFF)      puis  u = r / 2^32

Soixante-quatre bits d'etat. Mais les seize bits de POIDS FORT de r viennent
de state0 SEUL, et un numero tire par troncature ne lit que ceux-la :

    floor(u * 80) = floor((state0 & 0xFFFF) * 80 / 2^16)  dans 99,955 % des cas

state1 ne pese que sur la fraction, et ne fait basculer le numero que lorsque
celle-ci frole une frontiere. MESURE : 9 divergences sur 20 000, soit un
tirage de vingt numeros EXACT 99,1 % du temps.

    SOIXANTE-QUATRE BITS D'ETAT, TRENTE-DEUX BITS DE RECHERCHE.

C'est le meme genre de dissymetrie que le §97 exploitait sur java.util.Random,
mais pour une raison differente : la, le LCG etait clos modulo 2^21 ; ici,
c'est l'echantillonneur qui ne lit qu'une moitie de l'etat.

Il TESTE les tirages ordonnes : il consigne au registre.
"""

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H83_DRY") == "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL, DRAWN = 80, 20
M32 = (1 << 32) - 1
A0, A1 = 18030, 36969


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ==========================================================================
rule("1. L'ÉQUIVALENCE MWC = LCG, VÉRIFIÉE")
# ==========================================================================

say(f"""   THEOREME. Un MWC de base b et de multiplicateur a est un LCG
   multiplicatif modulo p = a*b - 1, via z = x + b*c :

       z_(i+1) = a * z_i   (mod p)        et       x_i = z_i mod b

   PREUVE. a*b = 1 (mod p), donc b = a^-1 modulo p. Alors
   a*z = a*x + a*b*c = a*x + c = t, qui est exactement z_(i+1). []
""")
a, b = A0, 1 << 16
p = a * b - 1
x, c = 12345, 678
z = x + b * c
coincide = True
for _ in range(2000):
    t = a * x + c
    x, c = t % b, t // b
    z = (a * z) % p
    if z != x + b * c:
        coincide = False
        break
say(f"   a = {a}, b = 2^16, p = a*b - 1 = {p:,}")
say(f"   les deux formulations coincident sur 2 000 pas : {coincide}")
say(f"""
   CONSEQUENCE, et elle confirme le §91. Il vient x_(i+1) = a*x_i + c_(i+1)
   modulo b, la retenue vivant dans [0, {a}). Pour un a grand, c mod 16 n'est
   PAS constant : la signature du §80 ne mord pas, et le theoreme du bit zero
   du §100 non plus, puisqu'il exige un terme additif CONSTANT.

   La prise n'est donc pas algebrique. Elle est dans l'echantillonneur.""")


# ==========================================================================
rule("2. LA DISSYMÉTRIE DE MWC1616 (V8 AVANT 2016)")
# ==========================================================================


def pas0(s):
    return (np.uint64(A0) * (s & np.uint64(0xFFFF)) + (s >> np.uint64(16))) & np.uint64(M32)


def pas1(s):
    return (np.uint64(A1) * (s & np.uint64(0xFFFF)) + (s >> np.uint64(16))) & np.uint64(M32)


def numero_de(s0):
    """floor(u*80) + 1 en n'utilisant QUE state0."""
    return (((s0 & np.uint64(0xFFFF)) * np.uint64(POOL)) >> np.uint64(16)) + np.uint64(1)


RNG = np.random.default_rng(20260907)
NECH = 5_000 if DRY else 50_000
s0 = RNG.integers(0, 1 << 32, NECH, dtype=np.uint64)
s1 = RNG.integers(0, 1 << 32, NECH, dtype=np.uint64)
s0, s1 = pas0(s0), pas1(s1)
r = ((s0 << np.uint64(16)) + (s1 & np.uint64(0xFFFF))) & np.uint64(M32)
vrai = ((r * np.uint64(POOL)) >> np.uint64(32)) + np.uint64(1)
approx = numero_de(s0)
div = int((vrai != approx).sum())
say(f"""   V8 combinait deux MWC de seize bits :

       state0 = {A0} * (state0 & 0xFFFF) + (state0 >> 16)
       state1 = {A1} * (state1 & 0xFFFF) + (state1 >> 16)
       r = (state0 << 16) + (state1 & 0xFFFF)      puis   u = r / 2^32

   Les seize bits de POIDS FORT de r viennent de state0 SEUL. Un numero tire
   par troncature ne lit que ceux-la ; state1 ne pese que sur la fraction.
""")
say(f"   divergence mesuree sur {NECH:,} etats : {div} — soit {100*div/NECH:.3f} %")
say(f"   un tirage de {DRAWN} numeros est donc exact {100*(1-div/NECH)**DRAWN:.2f} % du temps")
COUV = (1 - div / NECH) ** DRAWN
say(f"""
   SOIXANTE-QUATRE BITS D'ETAT, TRENTE-DEUX BITS DE RECHERCHE. C'est la meme
   dissymetrie que le §97 sur java.util.Random, mais pour une autre raison :
   la, le LCG etait clos modulo 2^21 ; ici, c'est l'ECHANTILLONNEUR qui ne
   lit qu'une moitie de l'etat.""")


# ==========================================================================
# LE BALAYAGE
# ==========================================================================
MPREF = 6                     # numeros filtres en vectoriel (rejet)
MPREF_FY = 4                  # idem sous Fisher-Yates, ou chaque pas coute plus
CHUNK = 1 << 20 if DRY else 1 << 24


PLAFOND_MOTS = 400        # au-dela, l'etat est degenere : on abandonne


def tirage_mwc(s0, mode):
    """Le tirage complet depuis state0 seul. `mode` : 'rejet' ou 'fy'.

    LE PLAFOND N'EST PAS COSMETIQUE. MWC1616 a des points fixes — state0 = 0
    se reproduit indefiniment — et le generateur y rend toujours le meme
    numero. Une boucle « tant que moins de vingt distincts » ne se termine
    alors JAMAIS. Le balayage exhaustif rencontre ces etats par construction ;
    sans plafond, il se bloque au premier.
    """
    s = int(s0)
    if mode == "rejet":
        vus, out, mots = set(), [], 0
        while len(out) < DRAWN:
            if mots >= PLAFOND_MOTS:
                return None
            s = (A0 * (s & 0xFFFF) + (s >> 16)) & M32
            mots += 1
            v = ((s & 0xFFFF) * POOL) >> 16
            if v not in vus:
                vus.add(v)
                out.append(v + 1)
        return out
    arr = list(range(1, POOL + 1))
    out = []
    for i in range(DRAWN):
        s = (A0 * (s & 0xFFFF) + (s >> 16)) & M32
        j = i + (((s & 0xFFFF) * (POOL - i)) >> 16)
        arr[i], arr[j] = arr[j], arr[i]
        out.append(arr[i])
    return out


def valeur_en(m, P, V, W, i):
    """La valeur du tableau en position `m` apres `i` echanges.

    On ne materialise jamais le tableau : apres i echanges il ne differe de
    l'identite qu'aux positions deja touchees, dont on garde la liste. La
    valeur courante en m s'obtient en rejouant les ecritures.
    """
    cur = m + np.uint64(1)
    for k in range(i):
        cur = np.where(m == P[k], W[k], cur)
        cur = np.where(m == np.uint64(k), V[k], cur)
    return cur.astype(np.uint64)


def prefiltre_fy(dep, cible_np, nsteps):
    """Les etats dont les `nsteps` premiers numeros EMIS sont tous dans la cible.

    POURQUOI PAS `numero_de`. Sous troncature, le numero emis vaut
    floor(u*80)+1 : `numero_de` suffit. Sous FISHER-YATES cette quantite est un
    INDICE, pas une valeur — le numero emis est a[j] apres i echanges. Utiliser
    `numero_de` comme filtre eliminerait l'etat VRAI et rendrait « 0
    compatible » : une FAUSSE EXCLUSION SILENCIEUSE. Le temoin l'a attrapee, et
    c'est le pire genre de bogue.

    POURQUOI INCREMENTAL, ET CE QUE LA PREMIERE VERSION A COUTE. Elle rejouait
    les i+1 premiers pas DEPUIS LE DEBUT a chaque i, sur le chunk entier : du
    travail quadratique, et surtout une douzaine de tableaux de 2^24 mots
    vivants en meme temps. Le balayage s'est fait tuer au deuxieme des six.
    Ici on filtre A CHAQUE PAS et on retaille les colonnes deja calculees : un
    quart des candidats survit au premier pas, un seizieme au second — la
    memoire DECROIT au lieu de croitre, et le travail avec elle.
    """
    s = dep
    P, V, W = [], [], []
    for i in range(nsteps):
        s = pas0(s)
        j = np.uint64(i) + (((s & np.uint64(0xFFFF)) * np.uint64(POOL - i))
                            >> np.uint64(16))
        a_i = valeur_en(np.full(len(s), i, np.uint64), P, V, W, i)
        a_j = valeur_en(j, P, V, W, i)          # le numero emis au pas i
        garde = np.isin(a_j, cible_np)
        if not garde.any():
            return dep[:0]
        s, dep = s[garde], dep[garde]
        P = [c[garde] for c in P]
        V = [c[garde] for c in V]
        W = [c[garde] for c in W]
        P.append(j[garde])
        V.append(a_j[garde])
        W.append(a_i[garde])   # ce qui atterrit en j apres l'echange
    return dep


def balaie(cible, mode, lo=0, hi=1 << 32):
    """Tous les state0 dont le tirage reproduit `cible` (liste ORDONNEE)."""
    cible_np = np.array(sorted(set(cible)), np.uint64)
    trouves = []
    for base in range(lo, hi, CHUNK):
        s = np.arange(base, min(base + CHUNK, hi), dtype=np.uint64)
        dep = s.copy()
        if mode == "rejet":
            for _ in range(MPREF):
                s = pas0(s)
                garde = np.isin(numero_de(s), cible_np)
                s, dep = s[garde], dep[garde]
                if len(dep) == 0:
                    break
        else:
            dep = prefiltre_fy(dep, cible_np, MPREF_FY)
        for d in dep.tolist():
            if tirage_mwc(d, mode) == cible:
                trouves.append(int(d))
    return trouves


# ==========================================================================
rule("3. LE TÉMOIN POSITIF")
# ==========================================================================

say(f"""   On plante un etat 64 bits au hasard, on en fabrique un tirage, et on
   demande au balayage de retrouver state0 — en n'explorant QUE ses 2^32
   valeurs, sans jamais toucher a state1.
""")
ESSAIS = 1 if DRY else 2
say(f"   {'échantillonneur':>16} {'retrouvés':>11} {'sec':>8}")
temoins = {}
for mode in ("rejet", "fy"):
    ok, tt = 0, time.time()
    for _ in range(ESSAIS):
        v0 = int(RNG.integers(0, 1 << 32))
        cible = tirage_mwc(v0, mode)
        # fenetre etroite autour de la verite : le temoin valide l'attaque,
        # pas la force brute, dont la section 4 fait le compte exact.
        lo = max(0, v0 - (CHUNK // 2))
        got = balaie(cible, mode, lo, lo + CHUNK)
        ok += v0 in got
    temoins[mode] = (ok, ESSAIS)
    say(f"   {mode:>16} {f'{ok}/{ESSAIS}':>11} {time.time()-tt:>8.1f}")

say(f"""
   L'attaque retrouve l'etat plante. Le filtre est en deux temps : les {MPREF}
   premiers numeros doivent appartenir a l'ensemble observe — un candidat sur
   {4**MPREF:,} survit — puis le tirage complet est rejoue et compare.""")


# ==========================================================================
rule("4. SUR LES TIRAGES ORDONNÉS")
# ==========================================================================

rows = list(csv.DictReader(open(os.path.join(ROOT, "draws_ordered.csv"))))
ORD = sorted((int(r["id"]), [int(r[f"o{i}"]) for i in range(1, DRAWN + 1)])
             for r in rows)
CIBLES = ORD[:2] if DRY else ORD[:3]
HI = (1 << 22) if DRY else (1 << 32)
say(f"""   Un seul tirage suffit a l'exclusion : balayer les 2^32 valeurs de
   state0 couvre l'etat du generateur A N'IMPORTE QUEL tirage. On en fait
   {len(CIBLES)} par securite.

   espace : {HI:,} etats par tirage et par echantillonneur
""")

def une_passe(tache):
    """Un (tirage, echantillonneur). Rendue ISOLABLE pour tourner en parallele :
    les six balayages sont independants, la machine a quatre coeurs, et numpy
    ne parallelise pas ces boucles lui-meme."""
    tid, ordre, mode = tache
    tt = time.time()
    got = balaie(ordre, mode, 0, HI)
    return tid, mode, got, time.time() - tt


TACHES = [(tid, ordre, mode) for tid, ordre in CIBLES for mode in ("rejet", "fy")]
NPROC = 1 if DRY else 3        # trois : on laisse un coeur, la memoire suit
if NPROC == 1:
    RES = [une_passe(t) for t in TACHES]
else:
    import multiprocessing as mp
    with mp.get_context("fork").Pool(NPROC) as pool:
        RES = pool.map(une_passe, TACHES)

say(f"   {'tirage':>9} {'échantillonneur':>16} {'états testés':>14} {'compatibles':>12} {'sec':>8}")
total = 0
for tid, mode, got, sec in RES:
    total += len(got)
    say(f"   {tid:>9} {mode:>16} {HI:>14,} {len(got):>12} {sec:>8.1f}")

say(f"""
   {total} etat compatible.

   COUVERTURE. Le balayage ignore state1, dont la contribution ne fait
   basculer un numero que {100*div/NECH:.3f} % du temps. Un tirage entier est donc
   reproduit exactement {100*COUV:.1f} % du temps : c'est la couverture declaree, et
   les {100*(1-COUV):.1f} % restants ne sont pas testes.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h83.mwc1616",
        "Aucun etat de MWC1616 — le Math.random de V8 jusqu'en 2016, seul "
        "generateur A RETENUE que le §91 nommait et que le §101 a confirme "
        "absent des neuf sources de balayage — n'engendre les tirages ordonnes "
        "du dossier, ni sous rejet ni sous Fisher-Yates",
        f"balayage EXHAUSTIF des 2^32 valeurs de state0. L'echantillonneur par "
        f"troncature ne lit que les seize bits de poids fort de la sortie, qui "
        f"viennent de state0 seul : soixante-quatre bits d'etat, trente-deux "
        f"bits de recherche. Filtre sur les {MPREF} premiers numeros puis rejeu "
        f"complet",
        "aucun null n'est requis : la verification compare les vingt numeros "
        "DANS L'ORDRE, soit une probabilite de faux positif de 1/(80!/60!)",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(total), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : l'etat plante est retrouve "
                  f"{'/'.join(f'{temoins[m][0]}/{temoins[m][1]}' for m in ('rejet', 'fy'))} "
                  f"fois, sous rejet et sous Fisher-Yates"),
        notes=(f"Le §91 nommait les generateurs a retenue comme non vus par "
               f"Berlekamp-Massey, et la section 1 confirme pourquoi : un MWC est "
               f"un LCG multiplicatif modulo a*b-1, d'ou x_(i+1) = a*x_i + c_(i+1) "
               f"mod b avec une retenue NON CONSTANTE — ni la signature du §80 ni "
               f"le bit zero du §100 n'y mordent. La prise est dans "
               f"l'echantillonneur : mesure sur {NECH:,} etats, le numero ne depend "
               f"que de state0 dans {100-100*div/NECH:.3f} % des cas, soit un tirage entier exact "
               f"{100*COUV:.1f} % du temps. Couverture declaree en consequence."))
    h = lab.holm()
    say(f"   consigne : h83.mwc1616   {total} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("6. CE QUE CELA FERME, ET CE QUI RESTE")
# ==========================================================================

say(f"""   FERME. MWC1616, l'unique generateur a retenue jamais deploye a grande
   echelle — il a servi a `Math.random` dans Chrome et Node jusqu'en 2016 —
   a etat COMPLET, sous deux echantillonneurs, couverture {100*COUV:.1f} %.

   RESTE, et la liste est courte :
     — les MWC a base 2^32 (Marsaglia), dont l'etat fait 64 bits SANS la
       dissymetrie de MWC1616 : leur sortie est brute, donc les deux moities
       comptent. 2^64, hors de portee.
     — les SWB et AWC, memes raisons.
     — tout ce que le §91 nomme deja : sorties brouillees, CSPRNG, materiel.

   ET UNE REMARQUE DE METHODE. Ce fichier ne doit rien a une famille de plus
   essayee au hasard : il vient du §101, qui a LU les sources et constate
   qu'aucune ne contenait de MWC. La carte verifiee a produit sa premiere
   experience.

   Registre : consigne a la section 5.

   ({time.time() - T0:.1f} s)""")
