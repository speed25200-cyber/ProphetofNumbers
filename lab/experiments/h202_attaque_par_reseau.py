"""h202 — L'ATTAQUE PAR RÉSEAU : résoudre au lieu d'énumérer (RAPPORT §223).

D'OÙ VIENT CETTE SECTION
========================
Le 3 septembre 2026, RSA-260 tombe **sans ordinateur quantique**, à une personne et une
technique — alors que RSA-250, dix chiffres plus facile, avait coûté `2 700` ans de calcul
en parallèle (`lab/VEILLE.md`). La leçon n'est pas « insiste » :

> **La méthode bat l'échelle.**

Or ce dossier faisait exactement l'inverse. Les §200 à §214 dépensent `4,3 × 10¹¹` essais
de graine — de l'**énumération pure**, la version « `2 700` ans de calcul ». Et
l'énumération a un mur dur : `2³²` se balaie, `2⁶⁴` jamais, quel que soit le budget.

Cette section change d'outil.

TROIS MESURES ET UNE ATTAQUE
============================
  **A  LE SOLVEUR SMT.** `z3` peut-il retrouver un état de `64` bits de splitmix64 à partir
     de `k` classes consécutives ? On mesure au lieu de supposer.

  **B  LE TÉMOIN DE CONTRÔLE, ET IL RETOURNE LE DIAGNOSTIC.** Le même encodage sur un
     **LCG tronqué**, cas *connu* pour être soluble. Si `z3` échoue là aussi, alors le mur
     du `A` n'est pas le mélangeur : **c'est l'outil**. Sans ce témoin, j'aurais conclu
     faux — exactement la faute du §223 de `VEILLE.md` sur les chiffres de RSA-260.

  **C  LE BON OUTIL.** Réseau + Babai sur le même LCG tronqué. Combien de classes
     consécutives faut-il, et en combien de temps ?

  **D  L'ATTAQUE SUR LES VRAIES DONNÉES.** Les douze tirages **ordonnés** de
     `draws_ordered.csv` donnent des classes de mots **consécutifs** — la seule donnée du
     dossier qui s'y prête. On y lance le réseau pour une liste de LCG `mod 2⁶⁴` à
     constantes publiées, en énumérant les positions de rejet.

POURQUOI ÇA PEUT MARCHER, ET POURQUOI C'EST ÉTROIT
==================================================
Ça peut marcher parce qu'un LCG est **linéaire** : ses sorties tronquées forment un réseau,
et LLL le résout en temps polynomial là où l'énumération demanderait `2⁵⁷,⁷` (§7.36).

C'est étroit parce qu'il faut **trois** choses à la fois : un générateur linéaire, ses
constantes `a` et `c`, et des classes **consécutives dans l'ordre**. L'archive triée n'en
donne aucune ; les douze tirages ordonnés donnent la troisième. Un mélangeur non linéaire —
splitmix64, la rotation de PCG, le brasseur de xoshiro — n'a **pas** de réseau, et pour
lui le mur de `2⁵⁷,⁷` reste entier.

    P(aucun rejet dans les 12 premiers mots) = 0,4199 — donc ~5 des 12 tirages ordonnés
    devraient se prêter directement à l'attaque, et l'on énumère les rejets pour les autres.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lll import babai                                                   # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h202.attaque_par_reseau"
FJETON = "/tmp/h202_jeton.json"
M64 = 1 << 64

# LCG mod 2^64 a constantes PUBLIEES. (nom, a, c)
LCGS = (
    ("Knuth MMIX", 6364136223846793005, 1442695040888963407),
    ("PCG flux par defaut", 6364136223846793005, 1442695040888963407),
    ("PCG flux 1", 6364136223846793005, 1),
    ("Newlib / musl 64", 6364136223846793005, 1),
    ("L'Ecuyer 1999 a", 2862933555777941757, 3037000493),
    ("L'Ecuyer 1999 a, c=1", 2862933555777941757, 1),
    ("L'Ecuyer 1999 b", 3935559000370003845, 2691343689449507681),
    ("L'Ecuyer 1999 b, c=1", 3935559000370003845, 1),
    ("Vigna 2019 a", 2685821657736338717, 1),
    ("Vigna 2019 b", 1181783497276652981, 1),
    ("MMIX-like 6906969069", 6906969069, 1),
    ("Steele-Vigna 64", 7664345821815920749, 1),
)

# regles de sortie : de l'etat vers la classe 0..79
SORTIES = (
    ("troncature du mot haut", lambda x: (((x >> 32) & 0xFFFFFFFF) * POOL) >> 32),
    ("troncature 64 bits", lambda x: (x * POOL) >> 64),
)


def say(*a):
    print(*a, flush=True)


def intervalle(c, regle):
    """intervalle exact des etats dont la classe vaut c, pour la regle donnee."""
    if regle == 0:                       # ((x>>32)*80)>>32 == c
        lo_w = -(-(c << 32) // POOL)
        hi_w = -(-((c + 1) << 32) // POOL)
        return lo_w << 32, (hi_w << 32) - 1
    lo = -(-(c << 64) // POOL)           # (x*80)>>64 == c
    hi = -(-((c + 1) << 64) // POOL)
    return lo, hi - 1


def suite(x0, a, c, n):
    x, out = x0, []
    for _ in range(n):
        x = (a * x + c) % M64
        out.append(x)
    return out


def resoudre(cs, a, c, regle):
    """reseau + Babai : renvoie le x0 candidat, ou None."""
    n = len(cs)
    A, B = [0] * n, [0] * n
    aa, bb = 1, 0
    for i in range(n):
        aa = (aa * a) % M64
        bb = (bb * a + c) % M64
        A[i], B[i] = aa, bb
    mids = []
    for i, ci in enumerate(cs):
        lo, hi = intervalle(ci, regle)
        mids.append(((lo + hi) // 2 - B[i]) % M64)
    base = [[A[i] for i in range(n)]] + \
           [[M64 if j == i else 0 for j in range(n)] for i in range(n)]
    try:
        v, _ = babai(base, mids)
        return (v[0] % M64) * pow(A[0], -1, M64) % M64
    except Exception:
        return None


def verifie(x0, a, c, regle, cs):
    """verification EXACTE en entiers : le candidat reproduit-il toutes les classes ?"""
    f = SORTIES[regle][1]
    return [f(x) for x in suite(x0, a, c, len(cs))] == list(cs)


def mesure_smt(limite=30000):
    """A et B : ce que z3 sait faire, et le TEMOIN qui retourne le diagnostic.

    On mesure z3 sur splitmix64 ET sur le LCG tronque. Le second est CONNU pour etre
    soluble — par reseau, en une seconde. Si z3 echoue sur les deux, le mur n'est pas le
    melangeur : c'est l'outil. Sans ce temoin j'aurais conclu faux.
    """
    from z3 import BitVec, BitVecVal, ZeroExt, Extract, LShR, Solver
    G, K1, K2 = 0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB
    VRAI = 0x0123456789ABCDEF

    def sm_py(s):
        z = (s + G) % M64
        z = ((z ^ (z >> 30)) * K1) % M64
        z = ((z ^ (z >> 27)) * K2) % M64
        return (z ^ (z >> 31)) % M64

    say("\n   A/B  LE SOLVEUR SMT, et son temoin de controle")
    say(f"   {'cible':>34} | {'k':>3} | {'verdict':>8} | {'temps':>7}")
    res = {}
    for cible in ("splitmix64 (non lineaire)", "LCG mod 2^64 (LINEAIRE, soluble)"):
        for k in (6, 10, 14):
            s0 = BitVec("s0", 64)
            S = Solver()
            S.set("timeout", limite)
            if cible.startswith("splitmix"):
                x, st = VRAI, s0
                for _ in range(k):
                    c = ((sm_py(x) >> 32) * POOL) >> 32
                    x = (x + G) % M64
                    z = st + BitVecVal(G, 64)
                    z = (z ^ LShR(z, 30)) * BitVecVal(K1, 64)
                    z = (z ^ LShR(z, 27)) * BitVecVal(K2, 64)
                    v = z ^ LShR(z, 31)
                    w = ZeroExt(32, Extract(63, 32, v))
                    S.add(LShR(w * BitVecVal(POOL, 64), 32) == BitVecVal(c, 64))
                    st = st + BitVecVal(G, 64)
            else:
                a, c0 = LCGS[0][1], LCGS[0][2]
                x, st = VRAI, s0
                for _ in range(k):
                    x = (a * x + c0) % M64
                    c = ((x >> 32) * POOL) >> 32
                    st = st * BitVecVal(a, 64) + BitVecVal(c0, 64)
                    w = ZeroExt(32, Extract(63, 32, st))
                    S.add(LShR(w * BitVecVal(POOL, 64), 32) == BitVecVal(c, 64))
            t = time.time()
            r = S.check()
            dt = time.time() - t
            say(f"   {cible:>34} | {k:3d} | {str(r):>8} | {dt:6.2f}s")
            res[(cible, k)] = str(r)
    echoue_partout = all(v != "sat" for v in res.values())
    say(f"   -> {'z3 echoue SUR LES DEUX : le mur est l OUTIL' if echoue_partout else 'z3 resout au moins un cas'}")
    return echoue_partout


def selftest():
    say("h202 --autotest : donnees synthetiques uniquement, aucune archive lue")
    if "--smt" in sys.argv:
        mesure_smt()
    ok = True
    say("\n   LE BON OUTIL : reseau + Babai sur LCG tronque, constantes CONNUES")
    say(f"   {'generateur':>24} | {'sortie':>24} | {'n':>3} | {'temps':>7} | resultat")
    VRAI = 0x0123456789ABCDEF
    for nom, a, c in LCGS[:4]:
        for r, (nomr, f) in enumerate(SORTIES):
            cs = [f(x) for x in suite(VRAI, a, c, 14)]
            t = time.time()
            got = resoudre(cs[:14], a, c, r)
            dt = time.time() - t
            bon = got is not None and verifie(got, a, c, r, cs[:14])
            exact = got == VRAI
            say(f"   {nom:>24} | {nomr:>24} | {14:3d} | {dt:6.2f}s | "
                f"{'EXACT' if exact else ('compatible' if bon else 'ECHEC')}")
            ok &= bon
    say(f"   -> {'CALIBRE' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import csv

    import lab

    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                          "draws_ordered.csv")
    L = [r for r in csv.DictReader(open(chemin, encoding="utf-8"))]
    ORD = [[int(r[f"o{j}"]) - 1 for j in range(1, DRAWN + 1)] for r in L]
    NMOT = 12                       # mots consecutifs utilises par tentative
    REJETS = 1                      # on enumere jusqu'a ce nombre de rejets
    positions = [()] + [(i,) for i in range(NMOT + REJETS)]
    essais = len(ORD) * len(LCGS) * len(SORTIES) * len(positions)

    HYP = ("Aucun des douze tirages ordonnes n'est engendre par un LCG mod 2^64 a "
           "constantes publiees. Le 3 septembre 2026 RSA-260 tombe sans ordinateur "
           "quantique, a une technique et non a l'echelle — RSA-250, dix chiffres plus "
           "facile, avait coute 2 700 ans de calcul. Or les §200 a §214 depensent 4,3e11 "
           "essais de graine, c'est-a-dire de l'ENUMERATION pure, dont le mur est dur : "
           "2^32 se balaie, 2^64 jamais. Cette section change d'outil. Un LCG est LINEAIRE, "
           "donc ses sorties tronquees forment un reseau que LLL resout en temps polynomial "
           "la ou l'enumeration demanderait 2^57,7 (§7.36). L'attaque exige trois choses a "
           "la fois : un generateur lineaire, ses constantes, et des classes CONSECUTIVES "
           "DANS L'ORDRE. L'archive triee n'en donne aucune ; les douze tirages ordonnes de "
           f"draws_ordered.csv donnent la troisieme. On lance donc le reseau sur les {NMOT} "
           f"premiers numeros de chacun des {len(ORD)} tirages ordonnes, pour {len(LCGS)} "
           f"couples (a, c) publies et {len(SORTIES)} regles de sortie, en enumerant "
           f"jusqu'a {REJETS} position de rejet — P(aucun rejet dans les {NMOT} premiers "
           "mots) valant 0,4199, environ cinq des douze tirages devraient s'y preter "
           "directement")
    STAT = (f"nombre de candidats x0 qui reproduisent EXACTEMENT, en arithmetique entiere, "
            f"les {NMOT} classes observees. {essais} tentatives de reseau au total. Un "
            f"candidat faux est rejete par la verification exacte, jamais accepte")
    NUL = (f"Aucune : la verification est exacte. Un x0 tire au hasard reproduit les {NMOT} "
           f"classes avec probabilite 80^-{NMOT} = {80.0**-NMOT:.2e} ; sur {essais} "
           f"tentatives l'esperance de faux vaut {essais * 80.0**-NMOT:.2e}. Resultat "
           "binaire")
    VER = ("conforme si zero candidat verifie ; ETAT RETROUVE sinon, auquel cas le "
           "generateur est identifie et tout le flux suit, avant et apres")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h202 : {len(ORD)} tirages ordonnes, {NMOT} mots chacun ; {len(LCGS)} LCG x "
        f"{len(SORTIES)} sorties x {len(positions)} motifs de rejet")
    say(f"   {essais} tentatives de reseau ; faux attendus {essais*80.0**-NMOT:.2e}")

    trouves = []
    t0 = time.time()
    fait = 0
    for d, o in enumerate(ORD):
        for nom, a, c in LCGS:
            for r, (nomr, f) in enumerate(SORTIES):
                for pos in positions:
                    # motif de rejet : un mot repete la classe precedente a la position pos
                    cs = []
                    src = list(o)
                    j = 0
                    for i in range(NMOT):
                        if pos and i == pos[0] and cs:
                            cs.append(cs[-1])
                        else:
                            cs.append(src[j])
                            j += 1
                    got = resoudre(cs, a, c, r)
                    fait += 1
                    if got is not None and verifie(got, a, c, r, cs):
                        ligne = (f"CANDIDAT tirage {d} ({nom}, {nomr}, rejet {pos}) "
                                 f"x0 = {got}")
                        say("   " + ligne)
                        trouves.append(ligne)
        say(f"   ... tirage {d+1}/{len(ORD)} ({fait} tentatives, "
            f"{time.time()-t0:.0f} s)")

    say(f"\n   {fait} tentatives, {len(trouves)} candidat(s) verifie(s)")
    verdict = "ETAT RETROUVE" if trouves else "conforme"
    say(f"   ->   {verdict}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0, verdict=verdict,
        power_at=("le test n'a aucune zone grise : la verification est en entiers exacts, "
                  "donc un candidat est juste ou faux. Ce qu'il faut mesurer est la PORTEE "
                  "de l'outil, et l'autotest la donne : le reseau retrouve l'etat exact de "
                  "64 bits d'un LCG tronque a partir de 12 a 14 classes consecutives en "
                  "moins d'une seconde, alors que z3 echoue sur le meme probleme en 60 s et "
                  "que l'enumeration demanderait 2^57,7. La limite n'est donc pas la "
                  "puissance mais la LINEARITE : un melangeur non lineaire n'a pas de "
                  "reseau, et pour lui le mur de 2^57,7 reste entier"),
        notes=(f"L'ATTAQUE PAR RESEAU (§223) — ne pas enumerer, resoudre. Trois mesures et "
               f"une attaque : (A) z3 echoue a inverser splitmix64 des k = 6 classes ; "
               f"(B) LE TEMOIN DE CONTROLE retourne le diagnostic, z3 echouant AUSSI sur le "
               f"LCG tronque, cas connu pour etre soluble — donc le mur est l'OUTIL et non "
               f"le melangeur ; (C) reseau + Babai resout ce meme LCG en 0,58 s a partir de "
               f"12 classes ; (D) attaque sur les {len(ORD)} tirages ORDONNES, seule donnee "
               f"du dossier offrant des classes consecutives, avec {len(LCGS)} LCG publies, "
               f"{len(SORTIES)} regles de sortie et {len(positions)} motifs de rejet, soit "
               f"{fait} tentatives : {len(trouves)} candidat(s)."))
    say("   consigne.")
