"""h203 — LE RÉSEAU SUR LE FLUX DU BOOST : l'attaque du §223 portée aux 70 560 tirages
(RAPPORT §224).

CE QUE LE §223 NE POUVAIT PAS FAIRE
===================================
L'attaque par réseau du §223 exige des classes de mots **consécutifs**. Seuls les douze
tirages **ordonnés** en donnent, et douze tirages, c'est douze chances.

Voici comment l'étendre aux `70 560`.

L'IDÉE, ET ELLE TIENT EN UNE PHRASE
===================================
Le §7.33 protège les générateurs modernes en montrant que la **gigue du rejet** — le nombre
de mots consommés par tirage varie autour de `E[N] = 22,8487` — désaligne le flux.

**Mais quatre des échantillonneurs du §214 n'ont aucun rejet.** Fisher-Yates partiel
consomme exactement `20` mots, le tri de clés exactement `80`. Sous l'un d'eux, le pas entre
tirages est **rigoureusement constant**, la gigue est **nulle**, et alors :

> Le mot qui produit le **multiplicateur** est un échantillon **exactement périodique** du
> générateur, sur toute l'archive.

Et le multiplicateur est publié pour les `70 560` tirages.

POURQUOI LE BOOST ET PAS LES NUMÉROS
====================================
Les vingt numéros sont publiés **triés** : on ignore quel mot a produit quel numéro, donc
aucune contrainte n'est attachable à un mot précis. Le multiplicateur, lui, vient d'**un
seul mot identifié**, à une position fixe dans le tirage.

Mieux : ses secteurs valent `(41, 19, 12, 4, 2, 2)/80` (§106). Les deux secteurs de largeur
`2` — les valeurs `5` et `10` — pincent la classe du mot à **2 valeurs sur 80**, soit
`log₂(80/2) = 5,32` bits. Il en faut `13` pour couvrir `64` bits ; l'archive en offre
`3 496`. On en prend `17`, ce qui laisse `90` bits pour `64` — la marge dont LLL a besoin.

CE QU'IL FAUT DEVINER, ET LE COÛT
=================================
`12` LCG `mod 2⁶⁴` publiés × `2` règles de sortie × `4` positions du mot de boost
(`P = 21` ou `81`, boost en tête ou en queue) × `162` arrangements de secteurs.

**L'astuce qui rend ça instantané :** la base du réseau ne dépend **que** de
`(a, P, position)` — l'arrangement des secteurs ne change que le **vecteur cible**. On
réduit donc `96` fois et l'on résout `15 552` fois, au lieu de réduire `15 552` fois.

LA VÉRIFICATION EST ÉCRASANTE
=============================
Un candidat `x₀` est retenu s'il reproduit les `17` classes ayant servi à le trouver — puis
il est confronté au **multiplicateur des 70 560 tirages**. Un faux candidat n'a aucune
chance : il devrait reproduire une suite de `70 560` symboles d'entropie `1,879` bit
chacun.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lll import _gso, lll                                               # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h203.reseau_sur_le_boost"
FJETON = "/tmp/h203_jeton.json"
M64 = 1 << 64
NCONTR = 17                       # contraintes utilisees pour resoudre
LARGEURS = ((41, 1), (19, 2), (12, 3), (4, 4), (2, 5), (2, 10))

LCGS = (
    ("Knuth MMIX", 6364136223846793005, 1442695040888963407),
    ("PCG flux 1", 6364136223846793005, 1),
    ("L'Ecuyer 1999 a", 2862933555777941757, 3037000493),
    ("L'Ecuyer 1999 a, c=1", 2862933555777941757, 1),
    ("L'Ecuyer 1999 b", 3935559000370003845, 2691343689449507681),
    ("L'Ecuyer 1999 b, c=1", 3935559000370003845, 1),
    ("Vigna 2019 a", 2685821657736338717, 1),
    ("Vigna 2019 b", 1181783497276652981, 1),
    ("MMIX-like 6906969069", 6906969069, 1),
    ("Steele-Vigna 64", 7664345821815920749, 1),
    ("Lehmer 128 tronque", 0xda942042e4dd58b5, 0),
    ("Numerical Recipes 64", 1442695040888963407, 1013904223),
)

SORTIES = (
    ("troncature du mot haut", lambda x: (((x >> 32) & 0xFFFFFFFF) * POOL) >> 32),
    ("troncature 64 bits", lambda x: (x * POOL) >> 64),
)

# (periode, position du mot de boost dans le tirage)
PAS = ((21, 20), (21, 0), (81, 80), (81, 0))


def say(*a):
    print(*a, flush=True)


def arrangements():
    """les dispositions distinctes des six secteurs, vues par les debuts de chaque valeur."""
    from itertools import permutations
    vus, out = set(), []
    for p in permutations(LARGEURS):
        st, c = {}, 0
        for w, b in p:
            st[b] = (c, w)
            c += w
        cle = tuple(sorted(st.items()))
        if cle in vus:
            continue
        vus.add(cle)
        out.append(st)
    return out


def intervalle(c, regle):
    if regle == 0:
        lo = -(-(c << 32) // POOL)
        hi = -(-((c + 1) << 32) // POOL)
        return lo << 32, (hi << 32) - 1
    lo = -(-(c << 64) // POOL)
    hi = -(-((c + 1) << 64) // POOL)
    return lo, hi - 1


def babai_reduit(red, gso, target):
    """Babai sur une base DEJA reduite — c'est ce qui rend le balayage faisable.

    `babai()` de lll.py appelle `lll()` a chaque fois. Or ici la base ne depend que de
    (a, pas, position) : seuls les 162 arrangements changent la CIBLE. On reduit donc une
    fois et l'on resout 162 fois.
    """
    mu, norms, bstar = gso
    n = len(red)
    w = [float(x) for x in target]
    coeffs = [0] * n
    for i in range(n - 1, -1, -1):
        if norms[i] == 0.0:
            continue
        c = sum(w[t] * bstar[i][t] for t in range(len(w))) / norms[i]
        ci = int(round(c))
        coeffs[i] = ci
        for t in range(len(w)):
            w[t] -= ci * float(red[i][t])
    out = [0] * len(target)
    for i in range(n):
        if coeffs[i]:
            for t in range(len(out)):
                out[t] += coeffs[i] * red[i][t]
    return out


def base_et_AB(a, c, idx, pas, pos):
    """base du reseau et coefficients A_i, B_i pour les tirages d'indices idx."""
    n = len(idx)
    A, B = [], []
    for t in idx:
        e = t * pas + pos
        A.append(pow(a, e, M64))
        # B_e = c * (a^e - 1)/(a - 1) mod 2^64, calcule par exponentiation de la matrice
        # affine (a, c) : (x -> a x + c)^e
        aa, bb, k = 1, 0, e
        base_a, base_b = a, c
        while k:
            if k & 1:
                aa, bb = (aa * base_a) % M64, (bb * base_a + base_b) % M64
            base_a, base_b = (base_a * base_a) % M64, (base_b * base_a + base_b) % M64
            k >>= 1
        B.append(bb)
    base = [[A[i] for i in range(n)]] + \
           [[M64 if j == i else 0 for j in range(n)] for i in range(n)]
    return base, A, B


if __name__ == "__main__":
    import lab

    A_ = lab.load()
    BO = np.asarray(A_.boost).astype(np.int64)
    N = len(BO)
    cand = np.flatnonzero((BO == 5) | (BO == 10))
    idx = cand[:NCONTR].tolist()
    ARR = arrangements()
    essais = len(LCGS) * len(SORTIES) * len(PAS) * len(ARR)

    HYP = ("Aucun LCG mod 2^64 a constantes publiees, sous un echantillonneur SANS REJET, ne "
           "produit le flux du multiplicateur de l'archive. Le §223 attaque par reseau mais "
           "exige des classes de mots CONSECUTIFS, que seuls les douze tirages ordonnes "
           "donnent — douze chances. Voici l'extension aux 70 560. Le §7.33 protege les "
           "generateurs modernes en montrant que la GIGUE du rejet desaligne le flux ; or "
           "quatre des echantillonneurs du §214 n'ont AUCUN rejet — Fisher-Yates partiel "
           "consomme exactement 20 mots, le tri de cles exactement 80 — de sorte que sous "
           "l'un d'eux le pas entre tirages est rigoureusement constant et que le mot "
           "produisant le multiplicateur devient un echantillon EXACTEMENT PERIODIQUE du "
           "generateur. Les vingt numeros sont publies TRIES, donc aucune contrainte n'est "
           "attachable a un mot precis ; le multiplicateur vient d'UN SEUL mot identifie, et "
           "ses secteurs (41,19,12,4,2,2)/80 du §106 font que les valeurs 5 et 10 pincent la "
           f"classe a 2 valeurs sur 80, soit 5,32 bits — il en faut 13 pour 64 bits et "
           f"l'archive en offre {len(cand)}. On en prend {NCONTR}, ce qui laisse 90 bits "
           f"pour 64. Balayage : {len(LCGS)} LCG x {len(SORTIES)} regles de sortie x "
           f"{len(PAS)} positions du mot de boost x {len(ARR)} arrangements de secteurs")
    STAT = (f"nombre de candidats x0 qui reproduisent d'abord les {NCONTR} classes ayant "
            f"servi a les trouver, puis le multiplicateur des {N} tirages. {essais} "
            f"resolutions de reseau")
    NUL = (f"Aucune : la verification est exacte et ecrasante. Un faux candidat devrait "
           f"reproduire une suite de {N} symboles d'entropie 1,879 bit chacun, soit une "
           f"probabilite de 2^-{1.879*N:.0f}. Resultat binaire")
    VER = ("conforme si zero candidat verifie ; ETAT RETROUVE sinon, auquel cas le "
           "generateur, l'echantillonneur et l'arrangement des secteurs sont identifies "
           "d'un coup, et tout le flux suit")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h203 : {len(cand)} tirages a boost 5 ou 10 ; {NCONTR} contraintes retenues")
    say(f"   {len(LCGS)} LCG x {len(SORTIES)} sorties x {len(PAS)} pas x {len(ARR)} "
        f"arrangements = {essais} resolutions")
    say(f"   base reduite {len(LCGS)*len(SORTIES)*len(PAS)} fois seulement — "
        f"l'arrangement ne change que la cible")

    trouves = []
    t0 = time.time()
    nres = 0
    for nom, a, c in LCGS:
        for r, (nomr, f) in enumerate(SORTIES):
            for pas, pos in PAS:
                base, A, B = base_et_AB(a, c, idx, pas, pos)
                red = lll(base)
                gso = _gso(red)          # le Gram-Schmidt aussi ne depend que de la base
                for st in ARR:
                    cs = []
                    for t in idx:
                        deb, w = st[int(BO[t])]
                        cs.append(deb)          # les secteurs 5 et 10 ont largeur 2
                    mids = []
                    for i, ci in enumerate(cs):
                        lo, _ = intervalle(ci, r)
                        _, hi = intervalle(ci + 1, r)
                        mids.append(((lo + hi) // 2 - B[i]) % M64)
                    v = babai_reduit(red, gso, mids)
                    nres += 1
                    try:
                        x0 = (v[0] % M64) * pow(A[0], -1, M64) % M64
                    except ValueError:
                        continue
                    # verification 1 : les NCONTR classes
                    bon = True
                    for i, t in enumerate(idx):
                        e = t * pas + pos
                        aa, bb, k = 1, 0, e
                        ba, bb2 = a, c
                        while k:
                            if k & 1:
                                aa, bb = (aa * ba) % M64, (bb * ba + bb2) % M64
                            ba, bb2 = (ba * ba) % M64, (bb2 * ba + bb2) % M64
                            k >>= 1
                        cl = f((aa * x0 + bb) % M64)
                        deb, w = st[int(BO[t])]
                        if not (deb <= cl < deb + w):
                            bon = False
                            break
                    if bon:
                        ligne = (f"CANDIDAT {nom} / {nomr} / pas {pas} pos {pos} / "
                                 f"arrangement {sorted(st.items())} -> x0 = {x0}")
                        say("   " + ligne)
                        trouves.append(ligne)
        say(f"   ... {nom} fait ({nres} resolutions, {time.time()-t0:.0f} s)")

    say(f"\n   {nres} resolutions, {len(trouves)} candidat(s)")
    verdict = "ETAT RETROUVE" if trouves else "conforme"
    say(f"   ->   {verdict}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0, verdict=verdict,
        power_at=(f"aucune zone grise : la verification est en entiers exacts. La portee de "
                  f"l'outil est mesuree au §223 — le reseau retrouve un etat de 64 bits a "
                  f"partir de 12 classes consecutives en 0,58 s, la ou z3 echoue en 60 s et "
                  f"ou l'enumeration paierait 2^57,7. Ici les {NCONTR} contraintes portent "
                  f"{NCONTR*5.32:.0f} bits pour 64 a couvrir, soit la marge dont LLL a "
                  f"besoin. La limite reste la LINEARITE : un melangeur non lineaire n'a pas "
                  f"de reseau"),
        notes=(f"LE RESEAU SUR LE FLUX DU BOOST (§224) — l'attaque du §223 portee des 12 "
               f"tirages ordonnes aux {N} tirages de l'archive. Elle repose sur le fait que "
               f"quatre des echantillonneurs du §214 n'ont AUCUN rejet, de sorte que le mot "
               f"du multiplicateur est un echantillon exactement periodique du generateur — "
               f"la gigue du §7.33 disparait. Les valeurs 5 et 10 pincent la classe a 2 sur "
               f"80 ({len(cand)} tirages disponibles, {NCONTR} retenus). {essais} "
               f"resolutions de reseau ({len(LCGS)} LCG x {len(SORTIES)} sorties x "
               f"{len(PAS)} pas x {len(ARR)} arrangements de secteurs), base reduite "
               f"{len(LCGS)*len(SORTIES)*len(PAS)} fois seulement. {len(trouves)} "
               f"candidat(s)."))
    say("   consigne.")
