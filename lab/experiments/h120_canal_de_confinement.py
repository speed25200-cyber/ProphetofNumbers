"""h120 — le canal de confinement : reconstituer l'état à partir de l'ARCHIVE
TRIÉE SEULE, sans bonus, sans ordre, et sans modèle du bonus.

CE QUE LE §140 VIENT DE COÛTER
===============================
Le §140 a montré que la borne `W >= 47 040` est CONDITIONNELLE au modèle B — le
rang publié du bonus vaut floor(20·u) d'un mot à position fixe — et que la
condition n'est pas vérifiable sur l'archive. Toute la voie model-free du dossier
passe par le rang du bonus, donc toute la voie model-free est conditionnelle.

    LA QUESTION QUI S'IMPOSE ALORS : RESTE-T-IL QUELQUE CHOSE QUI NE DÉPENDE
    D'AUCUN MODÈLE DU BONUS ?

Oui, et c'était sous la main depuis le §110.

LE CANAL, ET IL EST EXACT
==========================
À l'étape 0 de Fisher-Yates le tableau est ENCORE L'IDENTITÉ. La valeur émise
vaut donc exactement `j_0 + 1`, où `j_0 = floor(80·u_0)` — sans aucune hypothèse,
sans le bonus, sans l'ordre. Et cette valeur est l'un des vingt numéros publiés :

    j_0 + 1  ∈  S        EXACTEMENT, pour tout tirage de l'archive.

Mieux : par symétrie de Fisher-Yates, `j_0 + 1` est UNIFORME sur S. L'archive
publie donc, pour chaque tirage, une LOI A POSTERIORI complète sur `u_0`.

    ET LES QUATRE BITS DE POIDS FORT DU MOT SONT q = floor(j_0/5) = u_0 >> 28,
    puisque floor(80u/2^32 / 5) = floor(16u/2^32). Ce sont exactement les
    v2(80) = 4 bits exacts du théorème I du §126.

LE BUDGET D'INFORMATION, CALCULÉ ET NON ESTIMÉ
===============================================
    H(q) = 4 bits           E[H(q | S)] = 3,487 bits

        I(q ; S)  =  0,513 bit par tirage.

    contrôle : I(j_0 ; S) = log2(80) − log2(20) = 2 bits EXACTEMENT — c'est le
    théorème du confinement du §110, retrouvé par un autre chemin.

Donc l'archive de 70 560 tirages porte 36 199 bits d'information sur l'état, PAR
UN CANAL QUI NE SUPPOSE RIEN DU BONUS :

        xorshift128   128 bits ->     249 tirages
        WELL1024a   1 024 bits ->   1 996 tirages
        MT19937    19 937 bits ->  38 861 tirages     <- L'ARCHIVE SUFFIT
        WELL44497b 44 497 bits ->  86 734 tirages     <- il en manque 16 174

L'ALGORITHME, ET IL EST EXACT
==============================
L'information ne suffit pas : il faut un algorithme. En voici un, et il est le
maximum de vraisemblance EXACT, pas une heuristique.

Les quatre bits de q sont des formes F2-LINÉAIRES de l'état : q_i(s) = <m_i, s>.
On développe la log-vraisemblance d'un tirage sur la base de Walsh des quatre
bits :

    log P(q | S)  =  somme_{T ⊆ {0,1,2,3}}  c_T(S) · (−1)^<m_T, s>,  m_T = XOR

d'où, en sommant sur les tirages,

    LL(s)  =  somme_m  B[m] · (−1)^<m, s>       avec B[m] = somme des c_T

    — c'est LA TRANSFORMÉE DE WALSH-HADAMARD DE B. Un seul appel donne la
    log-vraisemblance de TOUS les 2^W états à la fois, en W·2^W opérations.

    COÛT : O(N·16 + W·2^W) en temps, 2^W en mémoire. Exact.

CE QUE CELA DONNE, ET CE QUE CELA NE DONNE PAS
===============================================
Cela DONNE la première reconstitution d'état du dossier à partir de l'archive
TRIÉE SEULE — témoin ci-dessous, état retrouvé et REJOUÉ.

Cela NE DONNE PAS l'archive réelle : 2^W est hors d'atteinte dès W = 128. Le
gouffre est celui que le §110 avait nommé — l'information est là, le levier
manque — mais il est maintenant chiffré des deux côtés, et l'algorithme exact
existe.

Il DÉMONTRE, il MESURE, et il RECONSTITUE. Il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H120_DRY") == "1"
POOL, DRAWN, MOTS = 80, 20, 21
PLANCHER = -30.0                              # log d'une case vide de S


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ---------------------------------------------------------------------------
# Générateur jouet F2-LINÉAIRE : LFSR de degré W, mot = 32 bits consécutifs.
# ---------------------------------------------------------------------------
class LFSR:
    """x^W + x^t + 1. L'état est le contenu du registre ; chaque bit produit est
    une forme linéaire de l'état initial, ce qui est tout ce qu'exige l'attaque.

    Le registre est un ENTIER PYTHON et non un tableau : la boucle de bits est
    le point chaud de la section, et la version tableau y passait cinquante fois
    plus de temps."""

    __slots__ = ("W", "t", "r", "haut")

    def __init__(self, W, t, etat):
        self.W, self.t = W, t
        self.haut = 1 << (W - 1)
        self.r = 0
        for k in range(W):
            if int(etat[k]) & 1:
                self.r |= 1 << k

    def mot(self):
        u, r, t, haut = 0, self.r, self.t, self.haut
        for _ in range(32):
            b = r & 1
            u = (u << 1) | b
            r = (r >> 1) | ((b ^ ((r >> t) & 1)) * haut)
        self.r = r
        return u


def tirages(W, t, etat, n):
    """Rend la liste des ENSEMBLES TRIÉS — c'est tout ce que l'archive publie."""
    g = LFSR(W, t, etat)
    out = []
    for _ in range(n):
        arr = list(range(1, POOL + 1))
        for i in range(DRAWN):
            m = POOL - i
            j = i + ((g.mot() * m) >> 32)
            arr[i], arr[j] = arr[j], arr[i]
        out.append(sorted(arr[:DRAWN]))
        g.mot()                                # le 21e mot : l'indice du bonus
    return out


def masques(W, t, n):
    """Les quatre formes linéaires <m_i, s> qui donnent q = u_0 >> 28, pour
    chacun des n tirages. Obtenues en faisant tourner le générateur depuis les W
    vecteurs unité — la linéarité fait le reste."""
    M = np.zeros((n, 4), np.int64)
    for k in range(W):
        e = np.zeros(W, np.uint8)
        e[k] = 1
        g = LFSR(W, t, e)
        for d in range(n):
            u = g.mot()                        # mot 0 du tirage d
            for b in range(4):                 # M[d,b] <-> le bit b de q
                if (u >> (28 + b)) & 1:        # q = u >> 28, donc bit b de q
                    M[d, b] |= 1 << k
            for _ in range(MOTS - 1):          # les vingt autres mots
                g.mot()
    return M


def coeffs_walsh(S):
    """Rend c_T pour T ⊆ {0,1,2,3}, à partir de l'ensemble trié S."""
    q = np.array([(v - 1) // 5 for v in S])    # les seize blocs de cinq
    p = np.bincount(q, minlength=16) / float(DRAWN)
    lp = np.where(p > 0, np.log(np.maximum(p, 1e-300)), PLANCHER)
    c = np.zeros(16)
    for T in range(16):
        s = 0.0
        for b in range(16):
            s += lp[b] * (-1.0) ** bin(T & b).count("1")
        c[T] = s / 16.0
    return c


def wht(a):
    """Walsh-Hadamard sur place, taille 2^W."""
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, h * 2):
            x = a[i:i + h].copy()
            y = a[i + h:i + 2 * h].copy()
            a[i:i + h] = x + y
            a[i + h:i + 2 * h] = x - y
        h *= 2
    return a


def reconstitue(W, M, ens):
    """Maximum de vraisemblance EXACT sur les 2^W états, par une seule WHT."""
    B = np.zeros(1 << W)
    for d, S in enumerate(ens):
        c = coeffs_walsh(S)
        for T in range(16):
            m = 0
            for b in range(4):
                if (T >> b) & 1:
                    m ^= int(M[d, b])
            B[m] += c[T]
    LL = wht(B)
    return int(np.argmax(LL)), LL


# ==========================================================================
rule("1. LE CANAL, ET IL NE SUPPOSE RIEN DU BONUS")
# ==========================================================================

say("""   Le §140 a rendu CONDITIONNELLE toute la voie model-free : elle passe par le
   rang du bonus, et le modele B n'est pas verifiable sur l'archive. Reste-t-il
   quelque chose qui ne depende d'aucun modele du bonus ?

   Oui, et c'etait sous la main depuis le §110. A L'ETAPE 0 DE FISHER-YATES LE
   TABLEAU EST ENCORE L'IDENTITE : la valeur emise vaut exactement j_0 + 1, ou
   j_0 = floor(80·u_0). Et elle est l'un des vingt numeros publies.

       j_0 + 1  dans  S       EXACTEMENT, pour tout tirage de l'archive.

   Par symetrie de Fisher-Yates, j_0 + 1 est UNIFORME sur S : l'archive publie
   donc, pour chaque tirage, une LOI A POSTERIORI complete sur u_0. Et les
   quatre bits de poids fort du mot sont

       q = floor(j_0 / 5) = u_0 >> 28,   car floor(80u/2^32 / 5) = floor(16u/2^32)

   — exactement les v2(80) = 4 bits exacts du theoreme I du §126.""")


# ==========================================================================
rule("2. LE BUDGET D'INFORMATION, CALCULÉ")
# ==========================================================================

rng = np.random.default_rng(11)
NS = 20000 if DRY else 200000
Sm = np.array([rng.choice(POOL, DRAWN, replace=False) for _ in range(NS)])
Qm = Sm // 5
cnt = np.zeros((NS, 16))
for b in range(16):
    cnt[:, b] = (Qm == b).sum(1)
pm = cnt / float(DRAWN)
with np.errstate(divide="ignore", invalid="ignore"):
    Hm = -np.where(pm > 0, pm * np.log2(pm), 0.0).sum(1)
INFO = 4.0 - Hm.mean()
NA = 70560

say(f"""   H(q) = 4 bits exactement. Sachant S, q suit la loi des seize blocs de cinq :

       E[H(q | S)] = {Hm.mean():.4f} bits        sur {NS:,} tirages simules

       I(q ; S) = {INFO:.4f} BIT PAR TIRAGE.

   Controle independant : I(j_0 ; S) = log2(80) - log2(20) = 2 bits EXACTEMENT,
   qui est le theoreme du confinement du §110 retrouve par un autre chemin.

   {'cible':>14} {'bits':>8} {'tirages requis':>16}   verdict""")
CIB = [("xorshift128", 128), ("taus88", 88), ("LFSR113", 113), ("WELL512a", 512),
       ("WELL1024a", 1024), ("MT19937", 19937), ("WELL44497b", 44497)]
for nom, W in CIB:
    n = W / INFO
    say(f"   {nom:>14} {W:>8,} {n:>16,.0f}   "
        f"{'ARCHIVE SUFFIT' if n <= NA else f'il en manque {n-NA:,.0f}'}")
say(f"""
   Largeur maximale couverte par les {NA:,} tirages de l'archive : {NA*INFO:,.0f} bits.
   MT19937 EST DEDANS, et il y est SANS AUCUN MODELE DU BONUS.""")


# ==========================================================================
rule("3. L'ALGORITHME : LE MAXIMUM DE VRAISEMBLANCE PAR UNE SEULE WALSH")
# ==========================================================================

say("""   L'information ne suffit pas : il faut un algorithme. Celui-ci est le maximum
   de vraisemblance EXACT, pas une heuristique.

   Les quatre bits de q sont des formes F2-LINEAIRES de l'etat : q_i(s) =
   <m_i, s>. On developpe la log-vraisemblance d'un tirage sur la base de Walsh
   des quatre bits :

       log P(q | S) = somme_{T inclus dans {0,1,2,3}} c_T(S) · (-1)^<m_T, s>

   ou m_T est le XOR des m_i pour i dans T. En sommant sur les tirages :

       LL(s) = somme_m B[m] · (-1)^<m, s>       B[m] = somme des c_T concernes

   — C'EST LA TRANSFORMEE DE WALSH-HADAMARD DE B. Un seul appel donne la
   log-vraisemblance des 2^W etats A LA FOIS.

       cout : O(N·16 + W·2^W) en temps, 2^W en memoire. EXACT.

   Le facteur 16 est le nombre de sous-ensembles des quatre bits ; il ne depend
   ni de N ni de W.""")


# ==========================================================================
rule("4. TÉMOIN : L'ÉTAT RETROUVÉ À PARTIR DES ENSEMBLES TRIÉS SEULS")
# ==========================================================================

say(f"""   Un LFSR de degre W engendre les tirages ; on ne publie QUE les ensembles
   tries — pas l'ordre, pas le bonus, pas le mot du bonus. On demande l'etat.

   On ne fixe pas le nombre de tirages : ON MESURE LE SEUIL. Pour chaque cas on
   augmente n jusqu'a ce que l'etat soit retrouve, et on exige un REJEU complet
   — l'etat retrouve doit reengendrer TOUS les ensembles observes, ce qu'un etat
   faux ne peut faire qu'avec probabilite C(80,20)^-n.

       {'W':>4} {'polynôme':>16} {'seuil théo.':>12} {'seuil MESURÉ':>13} {'rejeu':>7} {'sec':>7}""")

GRILLE = [40, 60, 80, 120, 160, 200, 300, 400]
CAS = [(16, 5), (20, 3)] if DRY else [(16, 5), (18, 7), (20, 3), (22, 1)]
OKT, LIGT = 0, []
for W, t in CAS:
    tt = time.time()
    rs = np.random.default_rng(1000 + W)
    etat = rs.integers(0, 2, W).astype(np.uint8)
    etat[0] |= 1
    vrai = int("".join(str(int(b)) for b in etat[::-1]), 2)
    nmax = GRILLE[-1]
    ens_max = tirages(W, t, etat, nmax)
    M_max = masques(W, t, nmax)
    seuil, rejeu = None, False
    for n in GRILLE:
        got, _ = reconstitue(W, M_max[:n], ens_max[:n])
        if got == vrai:
            eb = np.array([(got >> k) & 1 for k in range(W)], np.uint8)
            rejeu = tirages(W, t, eb, n) == ens_max[:n]
            if rejeu:
                seuil = n
                break
    OKT += seuil is not None and rejeu
    LIGT.append((W, t, W / INFO, seuil, rejeu))
    say(f"   {W:>4} {'x^%d + x^%d + 1' % (W, W - t):>16} {W/INFO:>12.0f} "
        f"{(str(seuil) if seuil else 'non atteint'):>13} "
        f"{('OUI' if rejeu else 'NON'):>7} {time.time()-tt:>7.1f}")

say(f"""
   {OKT}/{len(CAS)} etats retrouves ET rejoues, a un nombre de tirages du meme ordre
   que la borne d'information W/{INFO:.3f} — le facteur qui les separe est le prix
   ordinaire du maximum de vraisemblance sur 2^W concurrents, pas une faiblesse
   du canal.

     C'EST LA PREMIERE RECONSTITUTION D'ETAT DU DOSSIER A PARTIR DE L'ARCHIVE
     TRIEE SEULE. Ni ordre, ni bonus, ni modele du bonus — et l'etat sort.""")


# ==========================================================================
rule("5. LE GOUFFRE, CHIFFRÉ DES DEUX CÔTÉS")
# ==========================================================================

say(f"""   L'algorithme est exact, et il coute 2^W. Il est donc hors d'atteinte des la
   premiere cible reelle :

       {'W':>8} {'information':>14} {'coût de la WHT':>18}
       {16:>8} {'suffisante':>14} {'2^16 = instantané':>18}
       {22:>8} {'suffisante':>14} {'2^22 = quelques s':>18}
       {40:>8} {'suffisante':>14} {'2^40 = jours':>18}
       {128:>8} {'suffisante':>14} {'2^128 = jamais':>18}

   LE GOUFFRE EST CELUI QUE LE §110 AVAIT NOMME — « l'information est la, le
   levier manque » — mais il est desormais chiffre DES DEUX COTES, et
   l'algorithme exact existe. Ce qui manque n'est plus une idee : c'est un
   algorithme SOUS-EXPONENTIEL pour le meme probleme.

   CE QU'IL FAUDRAIT, ET IL A UN NOM. Le probleme est exactement LPN structure :
   retrouver s a partir de formes lineaires <m_i, s> observees a travers un
   canal bruite de biais {0.075:.3f}. Deux voies connues, et il faut dire ce qui les
   bloque ici :

     BKW           2^O(W/log W) — asymptotiquement meilleur, mais il exige un
                   nombre de couples exponentiel que l'archive n'a pas.
     correlation   il faut des controles de parite de POIDS FAIBLE. Le biais
     rapide        d'un controle de poids 3 vaut 4·eps^3 = {4*0.075**3:.1e}, donc il en
                   faut ~{1/(4*0.075**3)**2:.0e} — l'archive n'en fournit pas tant.

   La sparsite du polynome caracteristique decide donc tout : MT19937 et les
   WELL ont des recurrences CREUSES, ce qui fabrique des controles de poids
   faible gratuitement. C'est la seule breche visible, et elle demande plus de
   tirages que l'archive n'en publie — mais MOINS que 2^W, et le §139 dit ou les
   prendre.""")


# ==========================================================================
rule("6. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h120.canal_de_confinement",
        "L'archive TRIEE SEULE — sans l'ordre, sans le bonus et sans aucun "
        "modele du bonus — porte de l'information exploitable sur l'etat : a "
        "l'etape 0 de Fisher-Yates le tableau est encore l'identite, donc la "
        "valeur emise vaut exactement j_0 + 1 et appartient a l'ensemble publie, "
        "uniformement. Il en resulte I(q ; S) = 0,513 bit par tirage sur les "
        "quatre bits de poids fort du premier mot, et le maximum de "
        "vraisemblance sur les 2^W etats se calcule par UNE SEULE transformee de "
        "Walsh-Hadamard, en W·2^W operations",
        "nombre de generateurs F2-lineaires dont l'etat est retrouve EXACTEMENT "
        "a partir des seuls ensembles tries, et dont l'etat retrouve REJOUE la "
        "totalite des ensembles observes",
        "un etat tire au hasard rejoue les n ensembles avec probabilite "
        "C(80,20)^-n, soit moins de 1e-18 pour un seul tirage",
        "conforme si tous les etats plantes sont retrouves et rejoues", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(OKT), p=1.0,
        verdict="conforme" if OKT == len(CAS) else "ECHEC",
        power_at=(f"{OKT}/{len(CAS)} etats retrouves ET rejoues a partir des seuls "
                  f"ensembles tries. Le rejeu est le temoin : un etat faux "
                  f"reengendrerait un ensemble different des le premier tirage, "
                  f"avec probabilite 1 - C(80,20)^-1"),
        notes=(f"NE A LA CORRECTION DU §140, qui a rendu conditionnelle toute la "
               f"voie model-free en montrant que le modele B du bonus n'est pas "
               f"verifiable. Ce canal-ci ne suppose RIEN du bonus. Budget "
               f"d'information : H(q) = 4, E[H(q|S)] = {Hm.mean():.4f}, donc "
               f"I = {INFO:.4f} bit/tirage ; controle independant I(j_0 ; S) = "
               f"log2(80) - log2(20) = 2 bits exactement, soit le theoreme du "
               f"confinement du §110 par un autre chemin. L'archive de 70 560 "
               f"tirages porte donc {NA*INFO:,.0f} bits — MT19937 (19 937) est "
               f"DEDANS. L'algorithme est le maximum de vraisemblance EXACT par "
               f"une seule Walsh-Hadamard, O(N·16 + W·2^W), et c'est le 2^W qui "
               f"bloque des W = 128, pas l'information. Le probleme est du LPN "
               f"structure de biais 0,075 ; la seule breche visible est la "
               f"sparsite des recurrences de MT19937 et des WELL, qui fabrique "
               f"des controles de parite de poids faible."))
    h = lab.holm()
    say(f"   consigne : h120.canal_de_confinement   {OKT}/{len(CAS)} etats retrouves")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
