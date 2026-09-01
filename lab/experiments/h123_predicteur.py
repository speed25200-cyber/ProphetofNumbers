"""h123 — LE PRÉDICTEUR : de l'ordre observé aux vingt numéros du tirage suivant.

CE QUI MANQUAIT AU DOSSIER
===========================
Les §140 à §143 ont chiffré la DIFFICULTÉ — bornes conditionnelles, coût du
maximum de vraisemblance, corrélation rapide, arbre de branchement. Aucun d'eux
ne PRÉDIT. Le dossier savait dire pourquoi c'est dur ; il ne savait pas dire, en
un seul fichier exécutable :

    « voici des tirages ordonnés, voici les VINGT NUMÉROS du prochain. »

Cette section livre cette chaîne-là, de bout en bout, avec son témoin.

LA THÉORIE, EN TROIS ÉNONCÉS
=============================

(1) L'ÉQUATION D'OBSERVATION. Sous Fisher-Yates par troncature, connaître le
    numéro émis au pas k d'un tirage ordonné donne j_k, donc

        floor(K·u / 2^32) = j_k − k     avec K = 80 − k,

    ce qui confine u à un intervalle [lo, hi). Les bits de POIDS FORT sur
    lesquels lo et hi−1 s'accordent sont EXACTS : ce sont des formes
    F2-linéaires de l'état, connues. Un tirage ordonné en rend ~90.

(2) LE CRITÈRE DE PRÉDICTIBILITÉ, ET C'EST LUI QUI EST NEUF. Le dossier a
    toujours demandé « l'état est-il déterminé ? ». Ce n'est PAS la bonne
    question pour prédire. Un bit cible b = <lambda, s> est prédictible ssi

        lambda appartient a l'ESPACE DES LIGNES du système observé,

    ce qui est STRICTEMENT PLUS FAIBLE que « le système est de rang plein ».
    Autrement dit :

        LA PRÉDICTION PEUT RÉUSSIR SUR UN SYSTÈME SOUS-DÉTERMINÉ.

    Concrètement : si le noyau est de dimension d, on l'énumère, on garde les
    2^d états candidats qui REJOUENT les tirages observés, et si tous
    s'accordent sur le tirage suivant, LA PRÉDICTION EST CERTAINE MÊME SI
    L'ÉTAT NE L'EST PAS.

(3) LA CARTE DE PRÉDICTION. Une fois l'état connu (ou la classe suffisante),
    le tirage d+Delta occupe les mots 21(d+Delta)..21(d+Delta)+20 — le pas 21
    étant MESURÉ au §137 — et les vingt numéros s'obtiennent par Fisher-Yates.
    Il n'y a plus de statistique : c'est du calcul.

CE QUE LE TÉMOIN MONTRE
========================
Générateur planté, n tirages ordonnés donnés au prédicteur, VINGT NUMÉROS du
tirage suivant exigés DANS L'ORDRE — probabilité de réussite au hasard 1e-37.
Cinq familles sur cinq, et surtout :

    LFSR113, rang 108 sur 128 : VINGT DIMENSIONS DE NOYAU, 32 768 états
    distincts rejouent tous les tirages observés — l'état n'est PAS
    déterminé — ET ILS S'ACCORDENT TOUS SUR LE TIRAGE SUIVANT.

C'est l'énoncé (2) en acte. Le dossier testait « l'état est-il déterminé ? »
alors que la bonne question est « LA CIBLE est-elle déterminée ? ».

APPLIQUÉ AUX DOUZE TIRAGES ORDONNÉS RÉELS
==========================================
Le §136 a exclu 120 systèmes sur 120 par incompatibilité. Le prédicteur y ajoute
un DIAGNOSTIC que le §136 ne donnait pas : à quelle équation, exactement, chaque
famille se contredit. Et si l'une survivait, il émettrait les vingt numéros.

Il TESTE l'archive : il consigne au registre.
"""

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H123_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
POOL, DRAWN, STRIDE = 80, 20, 21
M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF
KCAP = 20                                     # dimension de noyau enumerable


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


# ---------------------------------------------------------------------------
# Les familles F2-LINÉAIRES : l'état est un vecteur de bits, le mot une forme
# linéaire de l'état. C'est tout ce que le prédicteur exige.
# ---------------------------------------------------------------------------
def _bits(x, n):
    return [(x >> i) & 1 for i in range(n)]


def _ent(b):
    v = 0
    for i, x in enumerate(b):
        if x:
            v |= 1 << i
    return v


class Fam:
    def __init__(self, nom, W, pas, sortie):
        self.nom, self.W, self.pas, self.sortie = nom, W, pas, sortie

    def flux(self, etat_bits, n):
        """Rend n mots de 32 bits."""
        e = self.depuis(etat_bits)
        out = []
        for _ in range(n):
            e = self.pas(e)
            out.append(self.sortie(e) & M32)
        return out

    def depuis(self, b):
        raise NotImplementedError


class FamMots(Fam):
    """État = k mots de `taille` bits."""

    def __init__(self, nom, k, taille, pas, sortie):
        super().__init__(nom, k * taille, pas, sortie)
        self.k, self.taille = k, taille

    def depuis(self, b):
        return [_ent(b[i * self.taille:(i + 1) * self.taille])
                for i in range(self.k)]


def _xorshift32(e):
    x = e[0]
    x ^= (x << 13) & M32
    x ^= x >> 17
    x ^= (x << 5) & M32
    return [x & M32]


def _xorshift64(e):
    x = (e[1] << 32) | e[0]
    x ^= (x << 13) & M64
    x ^= x >> 7
    x ^= (x << 17) & M64
    return [x & M32, (x >> 32) & M32]


def _xorshift128(e):
    x, y, z, w = e
    t = (x ^ ((x << 11) & M32)) & M32
    return [y, z, w, (w ^ (w >> 19) ^ t ^ (t >> 8)) & M32]


def _taus88(e):
    s1, s2, s3 = e
    b = ((s1 << 13) ^ s1) >> 19
    s1 = (((s1 & 0xFFFFFFFE) << 12) ^ b) & M32
    b = ((s2 << 2) ^ s2) >> 25
    s2 = (((s2 & 0xFFFFFFF8) << 4) ^ b) & M32
    b = ((s3 << 3) ^ s3) >> 11
    s3 = (((s3 & 0xFFFFFFF0) << 17) ^ b) & M32
    return [s1, s2, s3]


def _lfsr113(e):
    s1, s2, s3, s4 = e
    b = ((s1 << 6) ^ s1) >> 13
    s1 = (((s1 & 0xFFFFFFFE) << 18) ^ b) & M32
    b = ((s2 << 2) ^ s2) >> 27
    s2 = (((s2 & 0xFFFFFFF8) << 2) ^ b) & M32
    b = ((s3 << 13) ^ s3) >> 21
    s3 = (((s3 & 0xFFFFFFF0) << 7) ^ b) & M32
    b = ((s4 << 3) ^ s4) >> 12
    s4 = (((s4 & 0xFFFFFF80) << 13) ^ b) & M32
    return [s1, s2, s3, s4]


FAMILLES = [
    FamMots("xorshift32", 1, 32, _xorshift32, lambda e: e[0]),
    FamMots("xorshift64", 2, 32, _xorshift64, lambda e: e[0]),
    FamMots("xorshift128", 4, 32, _xorshift128, lambda e: e[3]),
    FamMots("taus88", 3, 32, _taus88, lambda e: e[0] ^ e[1] ^ e[2]),
    FamMots("LFSR113", 4, 32, _lfsr113, lambda e: e[0] ^ e[1] ^ e[2] ^ e[3]),
]


# ---------------------------------------------------------------------------
# (1) L'équation d'observation.
# ---------------------------------------------------------------------------
def prefixe(v, K):
    """u tel que floor(K·u/2^32) = v : rend (nbits, valeur du prefixe)."""
    lo = -(-(v << 32) // K)
    hi = -(-((v + 1) << 32) // K) - 1
    n = 0
    while n < 32 and ((lo >> (31 - n)) & 1) == ((hi >> (31 - n)) & 1):
        n += 1
    return n, (lo >> (32 - n)) if n else 0


def indices_fy(ordre):
    """De l'ordre d'emission aux j_k. Rend None si l'ordre est impossible."""
    arr = list(range(1, POOL + 1))
    out = []
    for k, val in enumerate(ordre):
        try:
            j = arr.index(val, k)
        except ValueError:
            return None
        out.append(j)
        arr[k], arr[j] = arr[j], arr[k]
    return out


def masques(fam, nmots):
    """M[t][b] = masque de la forme lineaire donnant le bit b (poids fort
    d'abord) du mot t. Obtenus depuis les W vecteurs unite : la linearite fait
    tout le travail, et aucune algebre par famille n'est necessaire."""
    W = fam.W
    M = [[0] * 32 for _ in range(nmots)]
    for c in range(W):
        b = [0] * W
        b[c] = 1
        for t, u in enumerate(fam.flux(b, nmots)):
            for j in range(32):
                if (u >> (31 - j)) & 1:
                    M[t][j] |= 1 << c
    return M


def systeme(fam, M, obs):
    """obs = {indice_de_tirage: [20 numeros dans l'ordre]}. Rend (piv, neq) ou
    (None, indice de l'equation qui contredit)."""
    piv, neq = {}, 0
    for d in sorted(obs):
        idx = indices_fy(obs[d])
        if idx is None:
            return None, neq
        for k in range(DRAWN):
            nb, pref = prefixe(idx[k] - k, POOL - k)
            t = d * STRIDE + k
            for b in range(nb):
                m, v = M[t][b], (pref >> (nb - 1 - b)) & 1
                while m:
                    h = m.bit_length() - 1
                    if h in piv:
                        pm, pv = piv[h]
                        m ^= pm
                        v ^= pv
                    else:
                        piv[h] = (m, v)
                        m = 0
                        break
                else:
                    if v:
                        return None, neq
                neq += 1
    return piv, neq


def solution(piv, W):
    """Une solution particuliere du systeme echelonne."""
    s = 0
    for h in sorted(piv):
        m, v = piv[h]
        x = v
        mm = m & ~(1 << h)
        while mm:
            c = mm.bit_length() - 1
            x ^= (s >> c) & 1
            mm &= ~(1 << c)
        if x:
            s |= 1 << h
    return s


def noyau(piv, W):
    """Base du noyau : une direction par colonne libre."""
    libres = [c for c in range(W) if c not in piv]
    base = []
    for f in libres:
        v = 1 << f
        for h in sorted(piv):
            m, _ = piv[h]
            x = 0
            mm = m & ~(1 << h)
            while mm:
                c = mm.bit_length() - 1
                x ^= (v >> c) & 1
                mm &= ~(1 << c)
            if x:
                v |= 1 << h
        base.append(v)
    return base


# ---------------------------------------------------------------------------
# (3) La carte de prédiction : de l'état aux vingt numéros.
# ---------------------------------------------------------------------------
def tirage_de(fam, etat_bits, d):
    """Les vingt numeros DANS L'ORDRE du tirage d'indice d."""
    flux = fam.flux(etat_bits, (d + 1) * STRIDE)
    arr = list(range(1, POOL + 1))
    out = []
    for k in range(DRAWN):
        u = flux[d * STRIDE + k]
        j = k + ((u * (POOL - k)) >> 32)
        arr[k], arr[j] = arr[j], arr[k]
        out.append(arr[k])
    return out


def bits_de(s, W):
    return [(s >> c) & 1 for c in range(W)]


def predit(fam, obs, cible, kcap=KCAP):
    """LE PRÉDICTEUR. Rend (prediction ou None, diagnostic)."""
    nmax = (max(list(obs) + [cible]) + 1) * STRIDE
    M = masques(fam, nmax)
    piv, neq = systeme(fam, M, obs)
    if piv is None:
        return None, f"INCOMPATIBLE apres {neq} equations"
    d = fam.W - len(piv)
    if d > kcap:
        return None, f"rang {len(piv)}/{fam.W}, noyau {d} > {kcap}"
    s0 = solution(piv, fam.W)
    base = noyau(piv, fam.W)
    vus, preds = 0, set()
    for masque in range(1 << d):
        s = s0
        for i in range(d):
            if (masque >> i) & 1:
                s ^= base[i]
        b = bits_de(s, fam.W)
        if all(tirage_de(fam, b, dd) == obs[dd] for dd in obs):
            vus += 1
            preds.add(tuple(tirage_de(fam, b, cible)))
    if vus == 0:
        return None, f"rang {len(piv)}/{fam.W}, aucun etat ne rejoue"
    if len(preds) == 1:
        return list(next(iter(preds))), \
            f"rang {len(piv)}/{fam.W}, {vus} etat(s) rejouent, PREDICTION UNIQUE"
    return None, f"rang {len(piv)}/{fam.W}, {vus} etats rejouent, {len(preds)} predictions"


# ==========================================================================
rule("1. LA THÉORIE, ET CE QUI EST NEUF DEDANS")
# ==========================================================================

say("""   Les §140 a §143 ont chiffre la DIFFICULTE. Aucun ne PREDIT. Voici la
   chaine qui manquait, en trois enonces.

   (1) L'EQUATION D'OBSERVATION. Connaitre le numero emis au pas k donne j_k,
       donc floor(K·u/2^32) = j_k - k avec K = 80 - k, ce qui confine u a un
       intervalle. Les bits de poids fort sur lesquels ses deux bornes
       s'accordent sont EXACTS — des formes F2-lineaires de l'etat, connues.

   (2) LE CRITERE DE PREDICTIBILITE, ET C'EST LUI QUI EST NEUF. Le dossier a
       toujours demande « l'etat est-il determine ? ». Ce n'est pas la bonne
       question. Un bit cible <lambda, s> est predictible SSI lambda appartient
       a l'ESPACE DES LIGNES du systeme — condition STRICTEMENT PLUS FAIBLE que
       le rang plein.

         LA PREDICTION PEUT REUSSIR SUR UN SYSTEME SOUS-DETERMINE.

       En pratique : noyau de dimension d, on enumere ses 2^d etats, on garde
       ceux qui REJOUENT les tirages observes, et s'ils s'accordent tous sur le
       tirage suivant, LA PREDICTION EST CERTAINE MEME SI L'ETAT NE L'EST PAS.

   (3) LA CARTE DE PREDICTION. L'etat connu, le tirage d occupe les mots
       21d..21d+20 — le pas 21 etant MESURE au §137 — et Fisher-Yates rend les
       vingt numeros. Il n'y a plus de statistique : c'est du calcul.""")


# ==========================================================================
rule("2. CONTRÔLE : LES FAMILLES SONT BIEN F2-LINÉAIRES")
# ==========================================================================

say(f"""   Le predicteur n'exige qu'une chose des familles : que le mot soit une forme
   F2-LINEAIRE de l'etat. On le VERIFIE avant de s'en servir, sur des etats
   tires au hasard — f(a XOR b) doit valoir f(a) XOR f(b).

       {'famille':>14} {'W':>5} {'linéarité':>12}""")
OKL = 0
rs = np.random.default_rng(1)
for fam in FAMILLES:
    ok = True
    for _ in range(6):
        a = rs.integers(0, 2, fam.W).tolist()
        b = rs.integers(0, 2, fam.W).tolist()
        c = [x ^ y for x, y in zip(a, b)]
        fa, fb, fc = (fam.flux(a, 8), fam.flux(b, 8), fam.flux(c, 8))
        if any((x ^ y) != z for x, y, z in zip(fa, fb, fc)):
            ok = False
            break
    OKL += ok
    say(f"   {fam.nom:>14} {fam.W:>5} {('OUI' if ok else 'NON'):>12}")
say(f"\n   {OKL}/{len(FAMILLES)} familles verifiees F2-lineaires.")


# ==========================================================================
rule("3. TÉMOIN : LES VINGT NUMÉROS DU TIRAGE SUIVANT, EXIGÉS EXACTS")
# ==========================================================================

say(f"""   Generateur plante, n tirages ordonnes donnes au predicteur, VINGT NUMEROS du
   tirage n exiges DANS L'ORDRE. Probabilite qu'un hasard y parvienne :
   1/(80!/60!) = 1e-37.

   On rapporte aussi le RANG au moment de la prediction, et le nombre d'etats
   qui rejouent les tirages observes — c'est la que le critere (2) se voit.

       {'famille':>14} {'W':>5} {'n':>3} {'rang':>8} {'noyau':>6} {'états rejouant':>15} {'20/20':>7} {'sec':>7}""")

OK3, LIG3, GAIN = 0, [], 0
for fam in FAMILLES:
    tt = time.time()
    rs = np.random.default_rng(4000 + fam.W)
    etat = rs.integers(0, 2, fam.W).tolist()
    etat[0] = 1
    nmax = 4
    vrai = {d: tirage_de(fam, etat, d) for d in range(nmax + 1)}
    trouve = None
    for n in range(1, nmax + 1):
        obs = {d: vrai[d] for d in range(n)}
        M = masques(fam, (n + 1) * STRIDE)
        piv, _ = systeme(fam, M, obs)
        rang = len(piv) if piv else -1
        p, diag = predit(fam, obs, n)
        if p == vrai[n]:
            nrej = int(diag.split()[2]) if "rejouent" in diag else 1
            trouve = (n, rang, fam.W - rang, nrej)
            break
    ok = trouve is not None
    OK3 += ok
    if ok:
        n, rang, noy, nrej = trouve
        # le critere (2) a mordu si l'etat n'etait PAS unique
        if noy > 0:
            GAIN += 1
        LIG3.append((fam.nom, fam.W, n, rang, noy, nrej))
        say(f"   {fam.nom:>14} {fam.W:>5} {n:>3} {rang:>8} {noy:>6} {nrej:>15,} "
            f"{'OUI':>7} {time.time()-tt:>7.1f}")
    else:
        LIG3.append((fam.nom, fam.W, None, None, None, None))
        say(f"   {fam.nom:>14} {fam.W:>5} {'—':>3} {'—':>8} {'—':>6} {'—':>15} "
            f"{'NON':>7} {time.time()-tt:>7.1f}")

say(f"""
   {OK3}/{len(FAMILLES)} tirages suivants predits EXACTEMENT, les vingt numeros dans
   l'ordre.

     ET LE CRITERE (2) MORD DANS {GAIN} CAS SUR {OK3}. Regardez la derniere ligne :
     rang {LIG3[-1][3]} sur {LIG3[-1][1]}, donc {LIG3[-1][4]} DIMENSIONS DE NOYAU, et {LIG3[-1][5]:,} etats
     distincts rejouent tous les tirages observes — l'etat n'est PAS determine.
     Et pourtant ils s'accordent TOUS sur les vingt numeros du tirage suivant.

     LA PREDICTION EST CERTAINE LA OU LA RECONSTITUTION NE L'EST PAS. C'est
     exactement ce que l'enonce (2) annonce, et c'est ce que le dossier
     cherchait sans le formuler : il testait « l'etat est-il determine ? »,
     alors que la bonne question est « la CIBLE est-elle determinee ? ».""")


# ==========================================================================
rule("4. LES DOUZE TIRAGES ORDONNÉS RÉELS")
# ==========================================================================

BASE_ID, PARJOUR = 1381194, 204
LIG = []
for r in csv.DictReader(open(os.path.join(os.path.dirname(ICI), "draws_ordered.csv"),
                             encoding="utf-8")):
    LIG.append((int(r["id"]), [int(r[f"o{i}"]) for i in range(1, 21)]))
LIG.sort()
JOURS = {}
for i, o in LIG:
    off = i - BASE_ID
    JOURS.setdefault(off // PARJOUR, {})[off % PARJOUR] = o

say(f"""   Le §136 a exclu 120 systemes sur 120 par INCOMPATIBILITE. Le predicteur y
   ajoute un DIAGNOSTIC que le §136 ne donnait pas : a quelle equation,
   exactement, chaque famille se contredit. Et si l'une survivait, il emettrait
   les vingt numeros du tirage suivant.

   {len(LIG)} tirages ordonnes, repartis sur {len(JOURS)} journees (§130) :
""")
for j in sorted(JOURS):
    say(f"     journee {j:>3} : index {sorted(JOURS[j])}")

say(f"""
       {'journée':>8} {'famille':>14} {'diagnostic':>44}""")
COMPAT, ESSAIS = [], 0
for j in sorted(JOURS):
    obs = JOURS[j]
    cible = max(obs) + 1
    for fam in FAMILLES:
        ESSAIS += 1
        p, diag = predit(fam, obs, cible)
        if p is not None:
            COMPAT.append((j, fam.nom, cible, p))
        say(f"   {j:>8} {fam.nom:>14} {diag:>44}")

say(f"""
   {len(COMPAT)} prediction(s) sur {ESSAIS} systemes.""")
for j, nom, cible, p in COMPAT:
    say(f"     !! journee {j}, {nom}, tirage d'index {cible} : {p}")
if not COMPAT:
    say("""     AUCUNE. Chaque famille se contredit avant d'avoir absorbe ses
     equations — le diagnostic dit exactement ou. Le predicteur ne rend donc
     aucun numero, et c'est le seul resultat honnete : une prediction ne se
     publie que si un etat la porte.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h123.predicteur",
        "La chaine complete « tirages ordonnes -> equations F2 -> etat -> VINGT "
        "NUMEROS DU TIRAGE SUIVANT » fonctionne et se verifie sur generateur "
        "plante ; appliquee aux douze tirages ordonnes reels, sous les cinq "
        "familles F2-lineaires du catalogue et le pas 21 mesure au §137, elle "
        "n'engendre aucune prediction, chaque systeme se contredisant avant "
        "d'avoir absorbe ses equations",
        "nombre de systemes reels rendant une prediction. Un systeme rend une "
        "prediction si un etat au moins REJOUE tous les tirages observes et si "
        "tous les etats qui les rejouent s'accordent sur le tirage suivant",
        "aucun null n'est requis : une prediction fausse serait detectee par le "
        "rejeu, dont la probabilite de faux positif vaut (80!/60!)^-k = 1e-37 "
        "par tirage observe",
        "conforme si aucune prediction n'est emise sur les donnees reelles",
        track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(len(COMPAT)), p=1.0,
        verdict="conforme" if not COMPAT else "PREDICTION",
        power_at=(f"{OK3}/{len(FAMILLES)} tirages suivants predits EXACTEMENT sur "
                  f"generateur plante — les vingt numeros dans l'ordre, "
                  f"probabilite de reussite au hasard 1e-37. Le predicteur "
                  f"reussit donc quand il doit reussir"),
        notes=(f"CE QUI MANQUAIT AU DOSSIER : les §140 a §143 chiffrent la "
               f"DIFFICULTE, aucun ne PREDIT. Trois enonces : (1) l'equation "
               f"d'observation, qui transforme un numero emis en bits exacts du "
               f"mot ; (2) LE CRITERE DE PREDICTIBILITE, neuf — un bit cible est "
               f"predictible ssi sa forme lineaire est dans l'espace des lignes "
               f"du systeme, condition STRICTEMENT PLUS FAIBLE que le rang "
               f"plein, donc LA PREDICTION PEUT REUSSIR SUR UN SYSTEME "
               f"SOUS-DETERMINE ; (3) la carte de prediction, pas 21 mesure au "
               f"§137. LE CRITERE (2) MORD DANS {GAIN} CAS SUR {OK3} : LFSR113 est predit "
               f"exactement alors que {LIG3[-1][5]:,} etats distincts rejouent les tirages "
               f"observes — rang {LIG3[-1][3]} sur {LIG3[-1][1]}. Sur les douze tirages ordonnes "
               f"reels, {ESSAIS} systemes testes, {len(COMPAT)} prediction — le "
               f"diagnostic dit pour chacun a quelle equation il se contredit, "
               f"ce que le §136 ne donnait pas."))
    h = lab.holm()
    say(f"   consigne : h123.predicteur   {len(COMPAT)} prediction sur {ESSAIS} systemes")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
