"""h211 — LA FAMILLE ÉLARGIE : le même réseau, sur dix-huit générateurs de plus
(RAPPORT §232).

CE QUE LE §230 A FERMÉ, ET CE QU'IL A LAISSÉ OUVERT
==================================================
Le §230 passe le réseau sur le flux du bonus — le canal ordonné le plus riche de l'archive,
`6,32` bits par tirage — et rend zéro. Mais sa portée est **exactement** celle de sa liste :
douze jeux de constantes, tous `mod 2⁶⁴`.

Un exploitant qui utilise `java.util.Random` (`mod 2⁴⁸`), `minstd` (`mod 2³¹−1`), la
`rand()` de Borland (`mod 2³²`) ou celle de Visual Basic (`mod 2²⁴`) **n'est pas dans cette
liste**. Or ces générateurs-là sont plus faibles, pas plus forts : un état de trente et un
bits se relève avec **cinq** valeurs de bonus au lieu de quatorze.

> Une attaque décisive à l'intérieur de sa famille ne vaut que ce que vaut sa famille.
> Élargir la famille est donc le seul travail qui convertisse une nullité en couverture.

DIX-HUIT CONFIGURATIONS, SIX MODULES
====================================
`2¹⁶+1`, `2²³`, `2²⁴`, `2³¹−1`, `2³¹`, `2³²`, `2⁴⁸` — les constantes publiées de RANDU, de
`minstd`, d'ANSI C, de Borland, de Turbo Pascal, de Visual C++, des *Numerical Recipes*, de
`cc65`, de Visual Basic 6, de `drand48`, de VMS, du ZX81.

LE `n` N'EST PAS CALCULÉ, IL EST MESURÉ
======================================
Le nombre de contraintes nécessaires *semble* se calculer : `log₂(m)/log₂(80)`. Le §230 a
montré que c'est faux dans le détail — sur le canal du rang `mod 2⁶⁴`, `n = 18` relève
`18` flux plantés sur `18`, et `n = 20` n'en relève que `14`. La qualité de Babai se dégrade
avec la dimension plus vite que le système ne se contraint.

Donc pour **chaque** configuration et **chaque** canal, on essaie plusieurs `n` sur des flux
**plantés issus de cette configuration même**, et l'on retient le plus petit qui relève
`100 %`. Si aucun ne le fait, la configuration est déclarée **NON COUVERTE** et comptée
comme telle — jamais présentée comme testée.

LE CONTRÔLE EXHAUSTIF
=====================
Babai est une heuristique : un échec ne prouve rien. Pour les modules `≤ 2³²`, on peut faire
mieux qu'espérer — **énumérer**. La première classe contraint l'état à un intervalle de
`m/80` valeurs ; on les parcourt toutes et l'on garde celles qui reproduisent la suite.
Pour `m = 2³²` cela fait `5,4·10⁷` candidats, quelques secondes en `numpy`, et le verdict
est **exhaustif, sans heuristique**.

On l'exécute sur deux configurations, sur **tous** les pas balayés par le réseau et sur
deux fenêtres. Si
le crible exhaustif et le réseau rendent tous deux zéro, le zéro du réseau est **validé par
une méthode qui ne peut pas manquer de solution**.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lll import _gso, lll                                              # noqa: E402
import h203_reseau_sur_le_boost as H3                                  # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h211.familles_elargies"
FJETON = "/tmp/h211_jeton.json"

# (nom, modulus, multiplicateur, increment)
CONFS = (
    ("RANDU",                       1 << 31,      65539,          0),
    ("minstd 16807 (Lehmer)",       (1 << 31) - 1, 16807,         0),
    ("minstd 48271 (C++)",          (1 << 31) - 1, 48271,         0),
    ("ANSI C / glibc TYPE_0",       1 << 31,      1103515245,     12345),
    ("Borland C/C++",               1 << 32,      22695477,       1),
    ("Turbo Pascal",                1 << 32,      134775813,      1),
    ("Microsoft Visual C++",        1 << 32,      214013,         2531011),
    ("Numerical Recipes",           1 << 32,      1664525,        1013904223),
    ("VMS MTH$RANDOM",              1 << 32,      69069,          1),
    ("Commodore / cc65",            1 << 23,      16843009,       826366247),
    ("Visual Basic 6",              1 << 24,      1140671485,     12820163),
    ("java.util.Random / drand48",  1 << 48,      25214903917,    11),
    ("drand48 sans increment",      1 << 48,      25214903917,    0),
    ("Native API Windows",          1 << 31,      2147483629,     2147483587),
    ("Sinclair ZX81",               (1 << 16) + 1, 75,            74),
    ("glibc TYPE_1 mod 2^32",       1 << 32,      1103515245,     12345),
    ("LCG mod 2^61-1",              (1 << 61) - 1, 2307085864,    0),
    ("ANSI C sans increment",       1 << 32,      1103515245,     0),
)

PAS = tuple(range(1, 129))
NFEN = 40
SUP = 10
NS = (6, 8, 10, 12, 14, 16, 18)        # candidats pour le nombre de contraintes
CANAUX = (("numero du bonus", 80), ("rang du bonus parmi les 20 tries", 20))
REGLES = ("troncature pleine", "troncature du haut")
EXHAUSTIF = ("Numerical Recipes", "ANSI C / glibc TYPE_0")   # modules <= 2^32


def say(*a):
    print(*a, flush=True)


def _arg(nom, defaut):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else defaut


def affine(a, c, e, m):
    aa, bb, k = 1, 0, e
    ba, bc = a, c
    while k:
        if k & 1:
            aa, bb = (aa * ba) % m, (bb * ba + bc) % m
        ba, bc = (ba * ba) % m, (bc * ba + bc) % m
        k >>= 1
    return aa, bb


def decal(m):
    """bits bas jetes par la regle 'troncature du haut' : on ne lit que 32 bits."""
    return max(0, m.bit_length() - 32)


def classe(x, m, base, regle):
    if regle == 0:
        return (x * base) // m
    d = decal(m)
    return ((x >> d) * base) // (m >> d) if d else (x * base) // m


def intervalle(c, m, base, regle):
    if regle == 0:
        lo = -(-(c * m) // base)
        hi = -(-((c + 1) * m) // base)
        return lo, hi - 1
    d = decal(m)
    if not d:
        lo = -(-(c * m) // base)
        hi = -(-((c + 1) * m) // base)
        return lo, hi - 1
    mp = m >> d
    lo = -(-(c * mp) // base)
    hi = -(-((c + 1) * mp) // base)
    return lo << d, ((hi) << d) - 1


def prepare(A, n, m):
    Ai, pw = [], 1
    for _ in range(n):
        pw = (pw * A) % m
        Ai.append(pw)
    red = lll([Ai] + [[m if j == i else 0 for j in range(n)] for i in range(n)])
    return Ai, red, _gso(red)


def increments(A, C, n, m):
    B, bb = [], 0
    for _ in range(n):
        bb = (bb * A + C) % m
        B.append(bb)
    return B


def attaque(cs, Ai, red, gso, B, m, base, regle):
    cible = []
    for i, ci in enumerate(cs):
        lo, hi = intervalle(int(ci), m, base, regle)
        cible.append(((lo + hi) // 2 - B[i]) % m)
    try:
        v = H3.babai_reduit(red, gso, cible)
    except Exception:
        return None
    try:
        return (int(v[0]) % m) * pow(Ai[0], -1, m) % m
    except ValueError:
        return None


def verifie(x0, A, C, m, cs, base, regle):
    x = x0
    for ci in cs:
        x = (A * x + C) % m
        if classe(x, m, base, regle) != int(ci):
            return False
    return True


def crible_exhaustif(cs, A, C, m, base, regle, bloc=1 << 22):
    """ENUMERATION complete : tous les x1 de la bonne classe, filtres par la suite.

    Sans heuristique : si une solution existe, elle est trouvee. Renvoie la liste des x0.
    """
    assert m <= (1 << 32) and A < (1 << 32), "le crible exhaustif exige un module <= 2^32"
    lo, hi = intervalle(int(cs[0]), m, base, regle)
    lo, hi = max(lo, 0), min(hi, m - 1)
    out = []
    ia = pow(A, -1, m)
    d = decal(m)
    mp = (m >> d) if d else m
    Au, Cu, mu = np.uint64(A), np.uint64(C), np.uint64(m)
    du, bu, mpu = np.uint64(d), np.uint64(base), np.uint64(mp)
    deb = lo
    while deb <= hi:
        fin = min(deb + bloc, hi + 1)
        orig = np.arange(deb, fin, dtype=np.uint64)
        cur = orig.copy()
        for ci in cs[1:]:
            # cur < 2^32 et A < 2^32 : le produit tient dans uint64, tout est EXACT
            cur = (cur * Au + Cu) % mu
            y = (cur >> du) if d else cur
            garde = ((y * bu) // mpu) == np.uint64(int(ci))
            orig, cur = orig[garde], cur[garde]
            if orig.size == 0:
                break
        for xi in orig.tolist():
            # orig porte x1 = A*x0 + C : l'inverse est AFFINE, pas lineaire. Oublier le
            # -C fait manquer la solution des que l'increment est non nul — le temoin
            # plante l'a montre sur les douze configurations a increment.
            x0 = ((int(xi) - C) * ia) % m
            if verifie(x0, A, C, m, cs, base, regle):
                out.append(x0)
        deb = fin
    return out


def calibre(nom, m, a, c, base):
    """choisit le plus petit n qui releve 100 % de flux plantes issus de CETTE config."""
    for n in NS:
        if n * np.log2(base) < m.bit_length() + 8:
            continue
        bon = True
        for pas in (1, 23):
            A, C = affine(a, c, pas, m)
            if A % 2 == 0 and m & (m - 1) == 0:
                continue
            for regle in (0, 1):
                for graine in (0x0123456789ABCDEF % m, 0x9E3779B97F4A7C15 % m):
                    x, cs = graine, []
                    for _ in range(n + SUP):
                        x = (A * x + C) % m
                        cs.append(classe(x, m, base, regle))
                    try:
                        Ai, red, gso = prepare(A, n, m)
                    except Exception:
                        bon = False
                        break
                    B = increments(A, C, n, m)
                    g = attaque(cs[:n], Ai, red, gso, B, m, base, regle)
                    if not (g is not None and verifie(g, A, C, m, cs, base, regle)):
                        bon = False
                        break
                if not bon:
                    break
            if not bon:
                break
        if bon:
            return n
    return None


if __name__ == "__main__":
    import lab

    A_ = lab.load()
    bonus = np.asarray(A_.bonus).astype(np.int64)
    nums = np.asarray(A_.nums).astype(np.int64)
    TS = np.asarray(A_.ts).astype(np.int64)
    N = len(bonus)
    BOR = np.r_[0, np.flatnonzero(np.diff(TS) > 1000) + 1, N]
    SUITES = {"numero du bonus": bonus - 1,
              "rang du bonus parmi les 20 tries": (nums < bonus[:, None]).sum(axis=1)}

    say(f"h211 : calibrage — on choisit n par TEMOIN PLANTE, config par config")
    say(f"   {'generateur':>28} | {'module':>10} | {'canal':>6} | {'n retenu':>9}")
    FCAL = "/tmp/h211_calibrage.json"
    if os.path.exists(FCAL):
        brut = json.load(open(FCAL, encoding="utf-8"))
        NRET = {(k.split("||")[0], k.split("||")[1]): v for k, v in brut.items()}
        say(f"   calibrage repris de {FCAL}")
    else:
        NRET = {}
        for nom, m, a, c in CONFS:
            for canal, base in CANAUX:
                n = calibre(nom, m, a, c, base)
                NRET[(nom, canal)] = n
                say(f"   {nom:>28} | 2^{m.bit_length()-1:<8} | {base:6d} | "
                    f"{(str(n) if n else 'NON COUVERT'):>9}")
        json.dump({f"{k[0]}||{k[1]}": v for k, v in NRET.items()},
                  open(FCAL, "w", encoding="utf-8"), ensure_ascii=False)
    couverts = sum(1 for v in NRET.values() if v)
    say(f"\n   {couverts}/{len(NRET)} couples (generateur, canal) couverts")

    besoin = max([v for v in NRET.values() if v] + [1]) + SUP
    nuits = [(BOR[i], BOR[i + 1]) for i in range(len(BOR) - 1)
             if BOR[i + 1] - BOR[i] >= besoin + 4]
    depart = [nuits[i][0] + 1 for i in range(0, len(nuits), max(1, len(nuits) // NFEN))]
    depart = depart[:NFEN]
    NTEST = couverts * len(PAS) * len(REGLES) * len(depart)
    say(f"   {len(depart)} fenetres de nuit -> {NTEST} relevements annonces")

    HYP = (f"Aucun des {len(CONFS)} generateurs congruentiels a constantes publiees, sur les "
           f"six modules 2^16+1, 2^23, 2^24, 2^31-1, 2^31, 2^32, 2^48 et 2^61-1, a pas de "
           f"bloc fixe <= {max(PAS)}, ne produit le flux du bonus de l'archive. Le §230 a "
           f"passe le reseau sur ce flux mais sa portee est EXACTEMENT celle de sa liste : "
           f"douze jeux de constantes, tous mod 2^64. Un exploitant qui utilise "
           f"java.util.Random (2^48), minstd (2^31-1), la rand() de Borland (2^32) ou celle "
           f"de Visual Basic (2^24) n'y est pas — et ces generateurs sont PLUS FAIBLES, un "
           f"etat de 31 bits se relevant avec cinq valeurs de bonus au lieu de quatorze. "
           f"Une attaque decisive a l'interieur de sa famille ne vaut que ce que vaut sa "
           f"famille ; elargir la famille est le seul travail qui convertisse une nullite "
           f"en couverture. Le nombre de contraintes n n'est pas calcule mais MESURE : pour "
           f"chaque configuration et chaque canal on retient le plus petit n qui releve "
           f"100 % de flux plantes issus de cette configuration meme, et une configuration "
           f"pour laquelle aucun n ne le fait est declaree NON COUVERTE, jamais presentee "
           f"comme testee. Enfin Babai est une heuristique : pour deux configurations de "
           f"module <= 2^32 on double le reseau d'un CRIBLE EXHAUSTIF qui enumere les m/80 "
           f"etats compatibles avec la premiere classe, et qui ne peut donc pas manquer une "
           f"solution")
    STAT = (f"nombre de relevements dont l'etat candidat reproduit EXACTEMENT en entiers les "
            f"{SUP} classes suivantes non utilisees, sur {NTEST} tentatives ; plus le nombre "
            f"de solutions du crible exhaustif sur {len(EXHAUSTIF)} configurations")
    NUL = (f"EXACTE et combinatoire : un candidat faux reproduit {SUP} classes de plus avec "
           f"probabilite base^-{SUP}, soit au plus 20^-{SUP} = 1e-13 ; sur {NTEST} "
           f"tentatives l'esperance de faux positifs est inferieure a 1e-7")
    VER = ("ETAT RELEVE si au moins un candidat passe la verification exacte ; conforme "
           "sinon, ce qui exclut les familles couvertes — et le crible exhaustif dit si le "
           "zero du reseau est un vrai zero ou une limite de l'heuristique")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")
    if "--jeton" in sys.argv:
        sys.exit(0)

    NPARTS = int(_arg("--nparts", 1))
    PART = int(_arg("--part", 0))
    FPART = "/tmp/h211_part%d.json"

    if "--agrege" in sys.argv:
        survivants, fait, nexh, t0 = [], 0, 0, time.time()
        for k in range(NPARTS):
            d = json.load(open(FPART % k, encoding="utf-8"))
            fait += d["fait"]
            nexh += d["nexh"]
            survivants += [tuple(s) for s in d["survivants"]]
            say(f"   part {k} : {d['fait']} relevements, {len(d['survivants'])} survivants, "
                f"{d['nexh']} solutions exhaustives")
    else:
        t0 = time.time()
        survivants, fait, nexh = [], 0, 0
        for ic, (nom, m, a, c) in enumerate(CONFS):
            if ic % NPARTS != PART:
                continue
            for pas in PAS:
                A, C = affine(a, c, pas, m)
                for canal, base in CANAUX:
                    n = NRET[(nom, canal)]
                    if not n:
                        continue
                    s = SUITES[canal]
                    try:
                        Ai, red, gso = prepare(A, n, m)
                    except Exception:
                        continue
                    B = increments(A, C, n, m)
                    for regle in (0, 1):
                        for d0 in depart:
                            cs = s[d0:d0 + n + SUP]
                            x0 = attaque(cs[:n], Ai, red, gso, B, m, base, regle)
                            fait += 1
                            if x0 is not None and verifie(x0, A, C, m, cs, base, regle):
                                survivants.append((nom, pas, canal, regle, int(d0), int(x0)))
                                say(f"   *** SURVIVANT : {nom}, pas {pas}, {canal}, "
                                    f"regle {regle}, depart {d0}, x0 = {x0}")
                    if nom in EXHAUSTIF and canal == "numero du bonus":
                        for regle in (0, 1):
                            for d0 in depart[:2]:
                                cs = s[d0:d0 + n + SUP]
                                sol = crible_exhaustif(cs, A, C, m, base, regle)
                                nexh += len(sol)
                                if sol:
                                    say(f"   *** EXHAUSTIF : {nom}, pas {pas}, regle "
                                        f"{regle}, depart {d0}, {len(sol)} solutions")
            say(f"   part {PART} {nom:>28} : {fait} relevements, {len(survivants)} "
                f"survivants, {nexh} exhaustifs, {time.time()-t0:7.1f}s")

        if NPARTS > 1:
            json.dump({"fait": fait, "nexh": nexh, "survivants": survivants},
                      open(FPART % PART, "w", encoding="utf-8"))
            say(f"   part {PART} ecrite")
            sys.exit(0)

    say(f"\n   {fait} relevements, {len(survivants)} survivants, "
        f"{nexh} solutions du crible exhaustif, {time.time()-t0:.1f}s")
    verdict = "ETAT RELEVE" if survivants else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(survivants)), p=float(1.0 if not survivants else 1e-13),
        verdict=verdict,
        power_at=(f"le n de chaque couple (generateur, canal) a ete choisi par temoin "
                  f"plante issu de cette configuration meme : {couverts} couples sur "
                  f"{len(NRET)} relevent 100 % des flux synthetiques et sont donc COUVERTS ; "
                  f"les autres sont declares non couverts et exclus du compte. Le crible "
                  f"exhaustif sur {len(EXHAUSTIF)} configurations de module <= 2^32 enumere "
                  f"tous les etats compatibles avec la premiere classe et ne peut manquer "
                  f"aucune solution : il valide le zero du reseau au lieu de le supposer"),
        notes=(f"LA FAMILLE ELARGIE (§232) — le reseau du §230, mais sur {len(CONFS)} "
               f"generateurs congruentiels a constantes publiees repartis sur huit modules "
               f"(2^16+1 a 2^61-1), la ou le §230 ne couvrait que douze jeux mod 2^64. "
               f"{couverts}/{len(NRET)} couples couverts par temoin plante, {fait} "
               f"relevements, {len(survivants)} survivants. Crible EXHAUSTIF (sans "
               f"heuristique) sur {len(EXHAUSTIF)} configurations : {nexh} solutions."))
    say("   consigne.")
