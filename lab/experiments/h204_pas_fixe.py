"""h204 — LE PAS FIXE : la faille dans mon propre §224 (RAPPORT §225).

LA FAUTE QUE JE VIENS DE TROUVER DANS LE §224
=============================================
Le §224 attaque le flux du multiplicateur par réseau, et il pose comme condition que
l'échantillonneur n'ait **aucun rejet** — Fisher-Yates partiel ou tri de clés — pour que le
pas entre tirages soit constant. C'est ce qui fait tomber la gigue du §7.33.

**Cette condition est trop forte, et je l'ai prise pour nécessaire alors qu'elle est
seulement suffisante.**

Si la machine consomme un **bloc de mots de taille fixe** par tirage — un tampon de `32`,
`48`, `64` mots, avec le rejet **à l'intérieur** du bloc — alors le pas est constant
**malgré le rejet**. C'est une implémentation parfaitement banale : on demande `N` mots à la
source, on s'en sert, on jette le reste. La gigue du §7.33 disparaît exactement de la même
façon, et l'attaque redevient possible pour **tous** les échantillonneurs, y compris ceux à
rejet.

Le §224 n'a donc pas testé un cas particulier de plus : **il a testé le mauvais espace.**

ET UNE SECONDE FAUTE, DE PARESSE CELLE-LÀ
=========================================
Le §224 énumère quatre positions du mot de boost dans le tirage. C'était inutile :

    L^(t·P + pos)(x₀) = L^(t·P)( L^pos(x₀) )

les puissances d'une même application affine commutant. **La position s'absorbe dans
l'inconnue** : résoudre avec `pos = 0` couvre *tous* les décalages. Quatre fois trop de
travail, pour rien.

CE QUE CE FICHIER BALAIE
========================
  * **le pas `P`** — une liste de tailles de bloc plausibles, de `20` à `256`, au lieu des
    deux seules valeurs `21` et `81` du §224 ;
  * **le module** — `2⁶⁴`, mais aussi `2⁴⁸` (c'est `java.util.Random`, le générateur non
    cryptographique le plus déployé au monde, et son espace de graine de `2⁴⁸` est **hors de
    portée** des balayages `2³²` des §200 à §214), `2³²`, `2³¹` ;
  * **la règle de sortie** — quels bits de l'état deviennent la classe ;
  * **les 720 arrangements** des secteurs du multiplicateur.

La base du réseau ne dépendant que de `(module, a, c, P, règle)`, on réduit une fois par
configuration et l'on résout `720` fois. La position, elle, ne coûte plus rien.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lll import _gso, lll                                               # noqa: E402
import h203_reseau_sur_le_boost as H3                                   # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h204.pas_fixe"
FJETON = "/tmp/h204_jeton.json"
NCONTR = 17

# (nom, module, a, c, decalage, largeur) : classe = ((x >> decalage) mod 2^largeur * 80)
#                                                    >> largeur
CFG = (
    ("Knuth MMIX 2^64 haut", 1 << 64, 6364136223846793005, 1442695040888963407, 32, 32),
    ("Knuth MMIX 2^64 plein", 1 << 64, 6364136223846793005, 1442695040888963407, 0, 64),
    ("PCG flux 1 2^64 haut", 1 << 64, 6364136223846793005, 1, 32, 32),
    ("L'Ecuyer a 2^64 haut", 1 << 64, 2862933555777941757, 3037000493, 32, 32),
    ("L'Ecuyer a 2^64 plein", 1 << 64, 2862933555777941757, 3037000493, 0, 64),
    ("L'Ecuyer b 2^64 haut", 1 << 64, 3935559000370003845, 2691343689449507681, 32, 32),
    ("Vigna a 2^64 haut", 1 << 64, 2685821657736338717, 1, 32, 32),
    ("Vigna b 2^64 haut", 1 << 64, 1181783497276652981, 1, 32, 32),
    ("Steele-Vigna 2^64 haut", 1 << 64, 7664345821815920749, 1, 32, 32),
    ("Numerical Recipes 2^64", 1 << 64, 1442695040888963407, 1013904223, 32, 32),
    # java.util.Random : 2^48, hors de portee de tout balayage 2^32
    ("java.util.Random nextInt", 1 << 48, 0x5DEECE66D, 0xB, 17, 31),
    ("java.util.Random haut 24", 1 << 48, 0x5DEECE66D, 0xB, 24, 24),
    ("java.util.Random plein", 1 << 48, 0x5DEECE66D, 0xB, 0, 48),
    # 2^32 : deja couvert en graine par enumeration, mais pas par reseau
    ("glibc / ANSI C 2^32", 1 << 32, 1103515245, 12345, 0, 32),
    ("MSVC 2^32", 1 << 32, 214013, 2531011, 16, 15),
    ("Borland 2^32", 1 << 32, 22695477, 1, 0, 32),
    ("Numerical Recipes 2^32", 1 << 32, 1664525, 1013904223, 0, 32),
    ("minstd 2^31-1", (1 << 31) - 1, 16807, 0, 0, 31),
    ("minstd nouveau", (1 << 31) - 1, 48271, 0, 0, 31),
)

# tailles de bloc plausibles : les rondes, les puissances de deux, et le voisinage
# de E[N] = 22,8487 mots reellement consommes par tirage
PAS = (20, 21, 22, 23, 24, 25, 26, 28, 30, 32, 33, 36, 40, 42, 44, 48, 50, 56,
       60, 64, 65, 72, 80, 81, 96, 100, 104, 128, 160, 200, 204, 256)


def say(*a):
    print(*a, flush=True)


def intervalle(c, dec, lar):
    """intervalle exact des etats dont la classe vaut c."""
    lo = -(-(c << lar) // POOL)
    hi = -(-((c + 1) << lar) // POOL)
    return lo << dec, (hi << dec) - 1


def classe(x, dec, lar):
    return (((x >> dec) & ((1 << lar) - 1)) * POOL) >> lar


def affine(a, c, e, m):
    """(x -> a x + c)^e mod m, par exponentiation rapide."""
    aa, bb, k = 1, 0, e
    ba, bc = a, c
    while k:
        if k & 1:
            aa, bb = (aa * ba) % m, (bb * ba + bc) % m
        ba, bc = (ba * ba) % m, (bc * ba + bc) % m
        k >>= 1
    return aa, bb


def base_AB(m, a, c, idx, pas):
    n = len(idx)
    A, B = [], []
    for t in idx:
        aa, bb = affine(a, c, t * pas, m)
        A.append(aa)
        B.append(bb)
    base = [[A[i] for i in range(n)]] + \
           [[m if j == i else 0 for j in range(n)] for i in range(n)]
    return base, A, B


if __name__ == "__main__":
    import lab

    A_ = lab.load()
    BO = np.asarray(A_.boost).astype(np.int64)
    N = len(BO)
    cand = np.flatnonzero((BO == 5) | (BO == 10))
    idx = cand[:NCONTR].tolist()
    ARR = H3.arrangements()
    nred = len(CFG) * len(PAS)
    essais = nred * len(ARR)

    HYP = ("Aucun generateur congruentiel a constantes publiees, sous un PAS FIXE quelconque, "
           "ne produit le flux du multiplicateur de l'archive. Le §224 attaque ce flux par "
           "reseau mais pose que le pas n'est constant que si l'echantillonneur n'a AUCUN "
           "rejet ; cette condition est suffisante et non necessaire, et je l'ai prise pour "
           "necessaire. Si la machine consomme un BLOC DE TAILLE FIXE par tirage — un tampon "
           "de 32, 48 ou 64 mots avec le rejet A L'INTERIEUR — le pas est constant MALGRE le "
           "rejet, la gigue du §7.33 disparait de la meme facon, et l'attaque redevient "
           "possible pour TOUS les echantillonneurs. Le §224 n'a donc pas teste un cas de "
           "plus : il a teste le mauvais espace. Seconde correction : le §224 enumerait "
           "quatre positions du mot de boost, ce qui est inutile puisque L^(tP+pos)(x0) = "
           "L^(tP)(L^pos(x0)), les puissances d'une meme application affine commutant — la "
           f"position S'ABSORBE dans l'inconnue. On balaie donc {len(PAS)} tailles de bloc de "
           f"20 a 256, {len(CFG)} configurations de generateur incluant java.util.Random dont "
           f"l'espace de graine de 2^48 est HORS DE PORTEE des balayages 2^32 des §200 a "
           f"§214, et les {len(ARR)} arrangements de secteurs du multiplicateur")
    STAT = (f"nombre de candidats x0 reproduisant d'abord les {NCONTR} classes ayant servi a "
            f"les trouver, puis le multiplicateur des {N} tirages. {essais} resolutions de "
            f"reseau, {nred} reductions")
    NUL = (f"Aucune : verification exacte et ecrasante. Un faux candidat devrait reproduire "
           f"{N} symboles d'entropie 1,879 bit. Resultat binaire")
    VER = "conforme si zero candidat ; ETAT RETROUVE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h204 : {len(CFG)} configurations x {len(PAS)} pas x {len(ARR)} arrangements = "
        f"{essais} resolutions ({nred} reductions)")
    say(f"   la position du mot de boost s'absorbe dans l'inconnue : plus rien a enumerer")

    trouves = []
    t0 = time.time()
    nres = 0
    for nom, m, a, c, dec, lar in CFG:
        for pas in PAS:
            base, A, B = base_AB(m, a, c, idx, pas)
            red = lll(base)
            gso = _gso(red)
            try:
                inv = pow(A[0], -1, m)
            except ValueError:
                continue
            for st in ARR:
                mids = []
                for i, t in enumerate(idx):
                    deb, _ = st[int(BO[t])]
                    lo, _ = intervalle(deb, dec, lar)
                    _, hi = intervalle(deb + 1, dec, lar)
                    mids.append(((lo + hi) // 2 - B[i]) % m)
                v = H3.babai_reduit(red, gso, mids)
                nres += 1
                x0 = (v[0] % m) * inv % m
                bon = True
                for i, t in enumerate(idx):
                    aa, bb = affine(a, c, t * pas, m)
                    cl = classe((aa * x0 + bb) % m, dec, lar)
                    deb, w = st[int(BO[t])]
                    if not (deb <= cl < deb + w):
                        bon = False
                        break
                if bon:
                    ligne = f"CANDIDAT {nom} pas {pas} arrangement {sorted(st.items())} x0={x0}"
                    say("   " + ligne)
                    trouves.append(ligne)
        say(f"   ... {nom} fait ({nres} resolutions, {time.time()-t0:.0f} s)")

    say(f"\n   {nres} resolutions, {len(trouves)} candidat(s)")
    verdict = "ETAT RETROUVE" if trouves else "conforme"
    say(f"   ->   {verdict}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0, verdict=verdict,
        power_at=(f"aucune zone grise : verification en entiers exacts. La portee de l'outil "
                  f"est mesuree au §223 — le reseau retrouve un etat de 64 bits a partir de "
                  f"12 classes en 0,58 s. Ici {NCONTR} contraintes portent "
                  f"{NCONTR*5.32:.0f} bits, ce qui couvre largement les modules de 31 a 64 "
                  f"bits balayes. La nouveaute est la couverture : java.util.Random a un "
                  f"espace de graine de 2^48 que les balayages 2^32 des §200 a §214 ne "
                  f"pouvaient pas atteindre, et que le reseau traverse sans enumerer"),
        notes=(f"LE PAS FIXE (§225) — correction d'une faille de mon propre §224, qui posait "
               f"que le pas n'est constant que sans rejet. C'est suffisant, pas necessaire : "
               f"un BLOC DE TAILLE FIXE par tirage, rejet a l'interieur, donne le meme "
               f"resultat et vaut pour TOUS les echantillonneurs. Le §224 testait donc le "
               f"mauvais espace. Seconde correction : la position du mot de boost s'absorbe "
               f"dans l'inconnue puisque L^(tP+pos) = L^(tP) o L^pos, donc les quatre "
               f"positions enumerees etaient du travail pour rien. {len(CFG)} configurations "
               f"x {len(PAS)} pas x {len(ARR)} arrangements = {essais} resolutions, dont "
               f"java.util.Random mod 2^48, hors de portee des balayages 2^32. "
               f"{len(trouves)} candidat(s)."))
    say("   consigne.")
