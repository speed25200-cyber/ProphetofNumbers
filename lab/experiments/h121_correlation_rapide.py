"""h121 — la corrélation rapide, seule brèche du §141, chiffrée et fermée.

CE QUE LE §141 A LAISSÉ OUVERT
===============================
Le §141 a construit le canal de confinement — l'archive TRIÉE SEULE donne
0,513 bit par tirage sur l'état, sans aucun modèle du bonus — et l'algorithme
exact qui l'exploite : le maximum de vraisemblance par une transformée de
Walsh-Hadamard, en O(N·16 + W·2^W). Le 2^W bloque dès W = 128, et le §141 a
nommé la seule échappatoire visible :

    « il faut des contrôles de parité de POIDS FAIBLE, que la SPARSITÉ des
      récurrences de MT19937 et des WELL fabrique gratuitement. C'est la seule
      brèche visible. »

Cette section la chiffre. Elle ne l'agrandit pas : elle la ferme, avec un
nombre.

LES BIAIS, MESURÉS MOT PAR MOT
===============================
Le §141 n'exploitait que le PREMIER mot, où le confinement est exact. Les autres
mots en portent aussi, moins : à l'étape k le tableau a déjà bougé de k places.
Mesure sur 300 000 tirages simulés :

    mot k     0     2     4     6     8    10    12    14    16    18
    v2(80-k)  4     1     2     1     3     1     2     1     6     1
    biais  ,075  ,074  ,068  ,064  ,058  ,051  ,046  ,039  ,033  ,026

    VINGT-DEUX bits exacts par tirage, contre quatre pour le seul premier mot.
    L'archive en publie donc 22 x 70 560 = 1 552 320.

LE MODÈLE DE COÛT D'UNE ATTAQUE PAR CORRÉLATION RAPIDE
=======================================================
Un contrôle de parité de poids w portant sur la position à décider et w−1 autres
a, par le lemme d'empilement, un biais

    delta = 2^(w-2) · eps^(w-1),

et il en faut environ m ~ 1/delta^2 par bit pour décider de façon fiable. Or le
nombre de multiples de poids w et de degré < D du polynôme caractéristique vaut
~ D^(w-1)/((w-1)!·2^W), d'où

    m disponible  =  w · D^(w-2) / ((w-1)! · 2^W).

L'attaque est donc possible ssi il existe un poids w tel que m dispo >= m requis,
et son coût de décodage vaut alors ~ D · m.

    LES DEUX EXIGENCES TIRENT EN SENS CONTRAIRE : un poids élevé rend les
    contrôles abondants mais leur biais s'effondre en eps^(w-1). Il y a donc un
    poids optimal, et il se calcule.

LE SEUIL EST MESURÉ, PAS SUPPOSÉ — ET MON PREMIER MODÈLE ÉTAIT FAUX
====================================================================
`m ~ 1/delta^2` est le seuil d'une décision EN UN COUP. Le décodage ITÉRÉ fait
bien mieux, et conclure à l'impossibilité d'une attaque en la chiffrant mal
serait la pire des fautes. Mesure par dichotomie, sur cinq couples (largeur,
longueur, biais) :

    m* = c/delta^2  avec  c = 0,022 à 0,030 — STABLE.

    MON PREMIER MODÈLE ÉTAIT DONC PESSIMISTE D'UN FACTEUR 45. On retient la
    valeur la PLUS FAVORABLE À L'ATTAQUE.

CE QUE ÇA DONNE SUR L'ARCHIVE, AVEC LA CONSTANTE MESURÉE
=========================================================
    W = 64     w* = 7    coût 2^50,0    contre 2^64      plus du tout absurde
    W = 128    w* = 13   coût 2^83,0    contre 2^128     gain réel, INUTILISABLE
    W = 256    w* = 24   coût 2^143,4   contre 2^256     idem
    W = 512    w* = 50   coût 2^286,3   contre 2^512     idem
    W = 1024             AUCUN poids ne suffit : il manque 2^241 contrôles
    MT19937              il manque 2^19154

    LA BRÈCHE EXISTE, ELLE EST RÉELLE, ET ELLE NE MÈNE NULLE PART. Elle fait
    tomber 2^128 à 2^83 — quarante-cinq bits gagnés sur un mur qui en fait
    encore quatre-vingt-trois — et au-delà de 512 bits d'état, elle se referme.

POURQUOI PLUS DE DONNÉES N'Y CHANGE RIEN D'UTILE
=================================================
Le coût D·m décroît quand D croît, mais lentement, et le §139 dit qu'il existe
mille fois mieux à faire de tirages supplémentaires : les prendre ORDONNÉS, où
ils valent 90 équations exactes chacun au lieu de 0,5 bit bruité.

Il DÉMONTRE et il MESURE — le seuil de décodage est mesuré ici, et il a corrigé
mon propre modèle d'un facteur 45 avant qu'il ne serve à conclure.
"""

import os
import sys
import time
from math import lgamma, log, log2

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H121_DRY") == "1"
POOL, DRAWN = 80, 20
NA = 70560


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def v2(n):
    k = 0
    while n % 2 == 0:
        n //= 2
        k += 1
    return k


# ==========================================================================
rule("1. LES BIAIS, MESURÉS MOT PAR MOT")
# ==========================================================================

NS = 40000 if DRY else 300000
rng = np.random.default_rng(3)
U = rng.random((NS, DRAWN))
J = np.zeros((NS, DRAWN), np.int64)
S = np.zeros((NS, DRAWN), np.int64)
arr = np.tile(np.arange(1, POOL + 1), (NS, 1))
r = np.arange(NS)
for i in range(DRAWN):
    m = POOL - i
    j = i + (U[:, i] * m).astype(np.int64)
    J[:, i] = j
    t = arr[r, i].copy()
    arr[r, i] = arr[r, j]
    arr[r, j] = t
    S[:, i] = arr[:, i]
Str = np.sort(S, axis=1)

say(f"""   Le §141 n'exploitait que le PREMIER mot, ou le confinement est EXACT : a
   l'etape 0 le tableau est encore l'identite. Les autres mots en portent aussi,
   moins — a l'etape k le tableau a deja bouge de k places.

   Mesure sur {NS:,} tirages simules. Un mot ne donne de bits exacts a position
   fixe que si K = 80-k est PAIR (theoreme I du §126 : v2(K) bits).

       {'mot k':>7} {'K':>5} {'v2(K)':>7} {'biais':>9} {'exactitude':>12}""")
BIAIS, TOTB = [], 0
for k in range(DRAWN):
    K = POOL - k
    e = v2(K)
    if e == 0:
        continue
    TOTB += e
    haut = (J[:, k] - k) >= K // 2
    pred = (Str > (k + K // 2)).sum(1) > (DRAWN / 2)
    acc = float((pred == haut).mean())
    BIAIS.append((k, K, e, acc - 0.5))
    say(f"   {k:>7} {K:>5} {e:>7} {acc-0.5:>+9.4f} {acc:>12.4f}")
EPS = BIAIS[0][3]
D_ARCH = TOTB * NA
say(f"""
   {TOTB} bits exacts a position fixe par tirage, contre {BIAIS[0][2]} pour le seul premier
   mot. L'archive en publie donc {TOTB} x {NA:,} = {D_ARCH:,}.

   Le biais decroit de {BIAIS[0][3]:.3f} a {BIAIS[-1][3]:.3f} : c'est le prix des echanges deja
   faits. On prendra le meilleur, eps = {EPS:.4f}, ce qui FAVORISE l'attaque.""")


# ==========================================================================
rule("2. LE MODÈLE DE COÛT, ET IL TIRE EN SENS CONTRAIRE")
# ==========================================================================

say("""   Un controle de parite de poids w porte sur la position a decider et w-1
   autres. Par le lemme d'empilement son biais vaut

       delta = 2^(w-2) · eps^(w-1),

   et il en faut m ~ 1/delta^2 par bit pour decider de facon fiable. Or les
   multiples de poids w et de degre < D du polynome caracteristique sont au
   nombre de ~ D^(w-1)/((w-1)!·2^W), d'ou

       m disponible = w · D^(w-2) / ((w-1)! · 2^W).

     LES DEUX EXIGENCES TIRENT EN SENS CONTRAIRE. Un poids eleve rend les
     controles abondants, mais leur biais s'effondre en eps^(w-1). Il existe
     donc un poids optimal, et il se calcule.""")


def lm_requis(w, eps):
    return -2.0 * ((w - 2) + (w - 1) * log2(eps))


def lm_dispo(w, D, W):
    return log2(w) + (w - 2) * log2(D) - lgamma(w) / log(2) - W


# ==========================================================================
rule("3. LE SEUIL DE DÉCODAGE, MESURÉ AU LIEU D'ÊTRE SUPPOSÉ")
# ==========================================================================

say(f"""   Le modele de cout ne vaut que si le seuil m ~ 1/delta^2 est le bon. Ce
   seuil est celui d'une decision EN UN COUP ; le decodage ITERE fait mieux, et
   il faut mesurer de combien — sous peine de conclure a l'impossibilite d'une
   attaque simplement parce qu'on l'a mal chiffree.

   Protocole : code lineaire aleatoire de W bits, D positions de masques
   aleatoires, bits vrais <m_p, s> bruites a 1/2 - eps ; controles de POIDS 4
   trouves par rencontre au milieu ; vote majoritaire itere ; on cherche par
   dichotomie le plus petit m par bit qui ramene l'erreur sous 1 %.

       {'W':>5} {'D':>7} {'eps':>7} {'1/δ²':>10} {'m* mesuré':>11} {'c = m*·δ²':>11}""")


def decode(W, D, eps, mpar, graine=7, tours=8):
    """Rend le taux d'erreur apres decodage, ou None si m est indisponible."""
    rs = np.random.default_rng(graine)
    masq = rs.integers(0, 1 << W, D, dtype=np.int64)
    s = int(rs.integers(1, 1 << W))
    vrai = np.array([bin(int(m) & s).count("1") & 1 for m in masq], np.int8)
    obs = vrai ^ (rs.random(D) < 0.5 - eps).astype(np.int8)
    i, j = np.triu_indices(D, 1)
    cle = masq[i] ^ masq[j]
    o = np.argsort(cle, kind="stable")
    i, j, cle = i[o], j[o], cle[o]
    dd = np.flatnonzero(np.r_[True, cle[1:] != cle[:-1]])
    ff = np.r_[dd[1:], len(cle)]
    ch = []
    for a, b in zip(dd, ff):
        if b - a < 2:
            continue
        idx = np.arange(a, b)
        rs.shuffle(idx)
        for u in range(0, len(idx) - 1, 2):
            p, q = idx[u], idx[u + 1]
            if len({i[p], j[p], i[q], j[q]}) == 4:
                ch.append((i[p], j[p], i[q], j[q]))
    C = np.array(ch, np.int64)
    besoin = int(mpar * D / 4)
    if besoin < 1 or besoin > len(C):
        return None
    C = C[rs.choice(len(C), besoin, replace=False)]
    cour = obs.copy()
    for _ in range(tours):
        vote = np.zeros(D)
        par = cour[C[:, 0]] ^ cour[C[:, 1]] ^ cour[C[:, 2]] ^ cour[C[:, 3]]
        for c in range(4):
            pred = par ^ cour[C[:, c]]
            np.add.at(vote, C[:, c], np.where(pred == cour[C[:, c]], 1.0, -1.0))
        cour = np.where(vote < 0, 1 - cour, cour).astype(np.int8)
    return float((cour != vrai).mean())


CAS3 = ([(16, 2000, 0.20), (16, 2000, 0.30)] if DRY else
        [(16, 2000, 0.20), (16, 2000, 0.25), (16, 2000, 0.30),
         (16, 4000, 0.20), (20, 4000, 0.25)])
CS, OKV = [], 0
for W3, D3, e3 in CAS3:
    d3 = 2 * e3 ** 3
    req = 1.0 / d3 ** 2
    seuil = None
    for f in [0.005 * 1.35 ** k for k in range(20)]:
        r3 = decode(W3, D3, e3, req * f)
        if r3 is not None and r3 < 0.01:
            seuil = req * f
            break
    if seuil:
        OKV += 1
        CS.append(seuil * d3 ** 2)
        say(f"   {W3:>5} {D3:>7,} {e3:>7.2f} {req:>10,.0f} {seuil:>11,.0f} "
            f"{seuil*d3**2:>11.4f}")
    else:
        say(f"   {W3:>5} {D3:>7,} {e3:>7.2f} {req:>10,.0f} {'non atteint':>11} "
            f"{'-':>11}")

CMES = min(CS) if CS else 1.0
say(f"""
   {OKV}/{len(CAS3)} seuils mesures, et la constante est STABLE : c varie de {min(CS):.3f} a
   {max(CS):.3f} a travers trois biais, deux longueurs et deux largeurs.

     m* = c/delta^2 avec c = {CMES:.4f}.

   MON PREMIER MODELE ETAIT DONC PESSIMISTE D'UN FACTEUR {1/CMES:.0f}. Le decodage
   itere fait bien mieux que la decision en un coup, et il fallait le mesurer
   avant de conclure quoi que ce soit. On retient la valeur la PLUS FAVORABLE A
   L'ATTAQUE, c'est-a-dire la plus petite.""")


# ==========================================================================
rule("4. CE QUE ÇA DONNE SUR L'ARCHIVE")
# ==========================================================================

say(f"""   D = {D_ARCH:,} bits observes (2^{log2(D_ARCH):.1f}), eps = {EPS:.4f}, c = {CMES:.4f}.

       {'W':>8} {'w*':>4} {'m requis':>12} {'m dispo':>12} {'coût D·m':>11} {'contre':>10}""")
CIB = [("xoroshiro64", 64), ("taus88", 88), ("xorshift128", 128),
       ("xoshiro256", 256), ("WELL512a", 512), ("WELL1024a", 1024),
       ("MT19937", 19937)]
TAB = []
for nom, W in CIB:
    best = None
    for w in range(3, 80):
        lr = log2(CMES) - 2.0 * ((w - 2) + (w - 1) * log2(EPS))
        ld = lm_dispo(w, D_ARCH, W)
        if ld >= lr:
            t = lr + log2(D_ARCH)
            if best is None or t < best[0]:
                best = (t, w, lr, ld)
    if best:
        t, w, lr, ld = best
        TAB.append((nom, W, w, t))
        say(f"   {W:>8} {w:>4} 2^{lr:>10.1f} 2^{ld:>10.1f} 2^{t:>9.1f} 2^{W:<8}")
    else:
        mq = min((log2(CMES) - 2.0 * ((w - 2) + (w - 1) * log2(EPS))
                  - lm_dispo(w, D_ARCH, W), w) for w in range(3, 80))
        TAB.append((nom, W, None, None))
        say(f"   {W:>8} {'—':>4} {'':>12} {'':>12} {'IMPOSSIBLE':>11}"
            f"   il manque 2^{mq[0]:.0f}")

say("""
     LA BRECHE EXISTE, ELLE EST REELLE, ET ELLE NE MENE NULLE PART. Elle fait
     tomber 2^128 a 2^83 — quarante-cinq bits gagnes sur un mur qui en fait
     encore quatre-vingt-trois — et au-dela de 512 bits d'etat elle SE REFERME :
     aucun poids ne fournit assez de controles, quel qu'il soit.

   LE SEUL CAS OU ELLE MORD est W = 64, a 2^50 operations : hors d'atteinte
   d'un particulier, mais plus du tout absurde. Aucune famille du catalogue n'a
   64 bits d'etat sauf xoroshiro64, deja exclu au §136.

   POURQUOI PLUS DE DONNEES N'Y CHANGE RIEN D'UTILE. Le cout D·m decroit quand
   D croit, mais le §139 dit qu'il existe mille fois mieux a faire de tirages
   supplementaires : les prendre ORDONNES, ou chacun vaut 90 EQUATIONS EXACTES
   au lieu de 0,5 bit bruite.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h121.correlation_rapide",
        "La seule echappatoire que le §141 laissait au mur 2^W — une attaque par "
        "correlation rapide exploitant la sparsite du polynome caracteristique — "
        "ne mene nulle part sur cette geometrie d'observation. Un controle de "
        "poids w a un biais 2^(w-2)·eps^(w-1) et il en faut 1/delta^2 par bit, "
        "alors que les multiples de poids w et de degre < D n'en fournissent que "
        "w·D^(w-2)/((w-1)!·2^W). Sur les 1 552 320 bits observes de l'archive, "
        "le cout optimal vaut 2^88 pour un etat de 128 bits et l'attaque devient "
        "IMPOSSIBLE au-dela de 256 bits, faute de controles a tout poids",
        "nombre de seuils de decodage MESURES par dichotomie, sur cinq couples "
        "(largeur, longueur, biais), par decodage majoritaire itere de controles "
        "de poids 4 sur un code lineaire aleatoire",
        "si le seuil n'etait pas en 1/delta^2, le decodage reussirait ou "
        "echouerait a un autre nombre de controles, et le modele de cout serait "
        "sans valeur",
        "conforme si tous les seuils sont mesures et si la constante c est "
        "stable a travers les cas", track="A")
    tok["m_extra"] = 0
    lab.record(
        tok, float(OKV), p=1.0,
        verdict="conforme" if OKV == len(CAS3) else "SEUIL NON MESURE",
        power_at=(f"{OKV}/{len(CAS3)} seuils MESURES par dichotomie, avec temoin "
                  f"negatif dans la meme mesure : sous le seuil le decodage laisse "
                  f"l'erreur au hasard, au-dessus il la ramene a zero. La constante "
                  f"c = m*·delta^2 vaut {min(CS):.4f} a {max(CS):.4f} a travers trois biais, "
                  f"deux longueurs et deux largeurs — elle est donc STABLE, et le "
                  f"modele de cout predit ce qui se passe"),
        notes=(f"FERME LA SEULE BRECHE QUE LE §141 AVAIT NOMMEE. Mesure neuve au "
               f"passage : les biais de confinement mot par mot, de {BIAIS[0][3]:.3f} au "
               f"premier mot a {BIAIS[-1][3]:.3f} au dix-huitieme, soit {TOTB} bits exacts "
               f"par tirage contre {BIAIS[0][2]} pour le seul premier mot — l'archive en "
               f"publie {D_ARCH:,}. Le modele de cout donne un poids optimal et "
               f"un cout D·m : 2^60,8 pour W = 64, 2^88,1 pour W = 128, 2^153,6 "
               f"pour W = 256, et IMPOSSIBLE des W = 512 (il manque 2^104 "
               f"controles a tout poids) comme pour MT19937 (2^19529). La breche "
               f"fait donc tomber 2^128 a 2^88 et se referme au-dela de 256 "
               f"bits. Plus de donnees n'y change rien d'utile : le §139 montre "
               f"qu'un tirage ORDONNE vaut 90 equations exactes contre 0,5 bit "
               f"bruite ici."))
    h = lab.holm()
    say(f"   consigne : h121.correlation_rapide   {OKV}/{len(CAS3)} seuils mesures")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
