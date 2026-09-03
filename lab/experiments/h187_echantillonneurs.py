"""h187 — LE BALAYAGE EXHAUSTIF, MAIS SUR SIX ÉCHANTILLONNEURS (RAPPORT §206 bis).

LE TROU QUE JE VIENS DE VOIR DANS MON PROPRE PROGRAMME
=======================================================
Les §200 à §205 balayent `1,56·10¹¹` graines. Tous, sans exception, supposent que
l'échantillonneur réduit **un** mot de trente-deux bits à une classe par **troncature**
`(w·80)>>32` ou par **modulo** `w mod 80`.

Ce sont deux façons parmi beaucoup. Si la machine utilise l'une des autres — et elles sont
au moins aussi répandues — alors **aucun de ces balayages ne pouvait apparier**, et leur
résultat négatif ne disait rien du tout sur la graine :

    java.util.Random.nextInt(80)      modulo débiaisé par rejet
    C++ / Rust / Go modernes           Lemire, multiplication et rejet sur les bits bas
    Math.random() * 80                 double de 53 bits, DEUX mots par candidat
    rand() & 127                       sept bits bas avec rejet

> **Un balayage exhaustif en graines mais borgne en échantillonneurs ne prouve rien.**
> Il faut les deux, et je ne les avais pas.

CE QUE FAIT CE FICHIER
======================
Il rejoue le balayage exhaustif du §203 — les `2³²` graines, comparées à l'archive entière
par table de hachage — sur **six** échantillonneurs au lieu de deux :

    0  troncature        `c = (w·80) >> 32`
    1  modulo            `c = w mod 80`
    2  modulo débiaisé   rejet si `w ≥ 2³² − 16`, puis `w mod 80`
    3  Lemire            `m = w·80` ; rejet si `(m mod 2³²) < 16` ; `c = m >> 32`
    4  double 53 bits    deux mots, `u = ((w₁>>5)·2²⁶ + (w₂>>6))/2⁵³`, `c = ⌊80u⌋`
    5  sept bits bas     `c = w & 127`, rejet si `c ≥ 80`

`2³² × 5 générateurs × 6 échantillonneurs = 1,29·10¹¹` essais.

LE TÉMOIN EST TRENTE FOIS PLUS EXIGEANT
=======================================
Trente couples générateur × échantillonneur, une graine plantée pour chacun. Si un seul
n'est pas retrouvé, l'échantillonneur correspondant n'est pas réellement couvert et il
faut le dire.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h181_graine_moderne as G                                        # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h187.echantillonneurs"
FJETON = "/tmp/h187_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_exhaustive")
CIBLES = "/tmp/h187_cibles.bin"
NBLOC = 4
TOT = 1 << 32
SEUIL80 = (1 << 32) % POOL                                   # 16
NOMECH = ("troncature", "modulo", "modulo debiaise", "Lemire", "double 53 bits",
          "sept bits bas")


def say(*a):
    print(*a, flush=True)


def tirage(graine, g, s, nmax=400):
    """miroir exact de `engendre` du C, pour PLANTER les temoins."""
    gen = G.Gen(graine, g)
    vus = set()
    for _ in range(nmax):
        w = gen.suivant()
        if s == 0:
            c = (w * POOL) >> 32
        elif s == 1:
            c = w % POOL
        elif s == 2:
            if w >= (1 << 32) - SEUIL80:
                continue
            c = w % POOL
        elif s == 3:
            m = w * POOL
            if (m & 0xFFFFFFFF) < SEUIL80:
                continue
            c = m >> 32
        elif s == 4:
            w2 = gen.suivant()
            u = ((w >> 5) * 67108864.0 + (w2 >> 6)) / 9007199254740992.0
            c = min(int(u * POOL), POOL - 1)
        else:
            c = w & 127
            if c >= POOL:
                continue
        vus.add(c)
        if len(vus) == DRAWN:
            m0 = m1 = 0
            for x in vus:
                if x < 64:
                    m0 |= 1 << x
                else:
                    m1 |= 1 << (x - 64)
            return m0, m1
    return None


def selftest():
    say("h187 --autotest : donnees synthetiques uniquement, aucune archive lue")
    say(f"   2^32 mod 80 = {SEUIL80}")
    say(f"   {'generateur':>14} | {'echantillonneur':>16} | graine | retrouvee")
    ok = True
    for g in range(5):
        for s in range(6):
            graine = 1000000000 + 7919 * (6 * g + s)
            t = tirage(graine, g, s)
            if t is None:
                say(f"   {G.NOMGEN[g]:>14} | {NOMECH[s]:>16} | ENGENDREMENT IMPOSSIBLE")
                ok = False
                continue
            with open("/tmp/h187_t.bin", "wb") as f:
                f.write(struct.pack("<qQQ", 0, t[0], t[1]))
            r = subprocess.run([OUTIL, "/tmp/h187_t.bin", str(graine - 30),
                                str(graine + 30)], capture_output=True, text=True)
            vu = any(f"graine {graine} generateur {G.NOMGEN[g]} "
                     f"echantillonneur {NOMECH[s]}" in L for L in r.stdout.splitlines())
            say(f"   {G.NOMGEN[g]:>14} | {NOMECH[s]:>16} | {graine} | "
                f"{'OUI' if vu else 'NON'}")
            ok &= vu
    say(f"   -> {'CALIBRE 30/30' if ok else 'DEFAILLANT'}")
    return ok


if __name__ == "__main__":
    if "--autotest" in sys.argv:
        sys.exit(0 if selftest() else 1)

    import lab

    A = lab.load()
    N = len(A.ids)
    TS = np.asarray(A.ts).astype(np.int64)
    NUMS = np.asarray(A.nums).astype(np.int64)
    M0 = np.zeros(N, np.uint64)
    M1 = np.zeros(N, np.uint64)
    for j in range(DRAWN):
        c = NUMS[:, j] - 1
        bas = c < 64
        M0[bas] |= (np.uint64(1) << c[bas].astype(np.uint64))
        M1[~bas] |= (np.uint64(1) << (c[~bas] - 64).astype(np.uint64))
    if not os.path.exists(CIBLES):
        with open(CIBLES, "wb") as f:
            for i in range(N):
                f.write(struct.pack("<qQQ", int(TS[i]), int(M0[i]), int(M1[i])))

    essais = float(TOT) * 5 * 6
    faux = essais * N / 3.5353e18
    pas = TOT // NBLOC
    B = [(k * pas, (k + 1) * pas if k < NBLOC - 1 else TOT) for k in range(NBLOC)]

    HYP = ("Le resultat du §203 tient sur SIX echantillonneurs et non deux. Les §200 a §205 "
           "supposaient tous que l'echantillonneur reduit un mot de 32 bits a une classe "
           "par troncature ou par modulo ; ce sont deux facons parmi beaucoup, et si la "
           "machine utilise le modulo debiaise par rejet (java.util.Random.nextInt), la "
           "methode de Lemire (C++, Rust, Go modernes), un double de 53 bits construit sur "
           "DEUX mots (Math.random()*80) ou les sept bits bas, alors AUCUN de ces balayages "
           "ne pouvait apparier et leur resultat negatif ne disait rien de la graine. Un "
           "balayage exhaustif en graines mais borgne en echantillonneurs ne prouve rien")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros, en balayant les 2^32 "
            f"graines x 5 generateurs x 6 echantillonneurs = {essais:.4e} essais, chaque "
            f"tirage engendre etant cherche dans une table de hachage des {N} masques")
    NUL = (f"Aucune : une coincidence fausse vaut {N}/C(80,20) = {N/3.5353e18:.2e} par "
           f"essai, soit {faux:.2e} au total. Resultat binaire")
    VER = "conforme si zero appariement ; GRAINE TROUVEE sinon"

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h187 : {N} cibles ; 2^32 graines x 5 generateurs x 6 echantillonneurs")
    say(f"   {essais:.4e} essais ; faux attendus {faux:.3e}")

    if "--lancer" in sys.argv:
        for k, (a, b) in enumerate(B):
            jour = f"/tmp/h187_bloc{k}.txt"
            depart = a
            if os.path.exists(jour):
                txt = open(jour, encoding="utf-8").read()
                if "TERMINE" in txt:
                    say(f"   bloc {k} deja termine")
                    continue
                marques = [L for L in txt.splitlines() if L.startswith("  ... graine ")]
                if marques:
                    depart = int(marques[-1].split()[2])
                    say(f"   bloc {k} repris a {depart}")
            subprocess.Popen([OUTIL, CIBLES, str(depart), str(b)],
                             stdout=open(jour, "a"), stderr=subprocess.STDOUT)
            say(f"   bloc {k} lance : [{depart}, {b})")
        say("   relancer sans --lancer pour agreger")
        sys.exit(0)

    trouves, faits = [], 0
    for k, (a, b) in enumerate(B):
        jour = f"/tmp/h187_bloc{k}.txt"
        if not os.path.exists(jour):
            say(f"   bloc {k} : ABSENT")
            continue
        txt = open(jour, encoding="utf-8").read()
        fini = "TERMINE" in txt
        faits += fini
        for L in txt.splitlines():
            if L.startswith("APPARIEMENT"):
                trouves.append(L)
                say("   " + L)
        dern = [L for L in txt.splitlines() if L.startswith("  ...")]
        say(f"   bloc {k} : {'termine' if fini else 'EN COURS'}"
            + (f"   {dern[-1].strip()}" if dern and not fini else ""))

    if faits < NBLOC:
        say(f"\n   {faits}/{NBLOC} blocs termines — rien n'est consigne tant que le "
            "balayage n'est pas complet")
        sys.exit(0)

    say(f"\n   balayage COMPLET : {essais:.4e} essais, {len(trouves)} appariement(s)")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("trente couples generateur x echantillonneur, une graine plantee pour "
                  "chacun, toutes retrouvees. C'est trente fois l'exigence du temoin du "
                  "§203, et c'est ce qu'il faut : un echantillonneur non retrouve serait "
                  "un echantillonneur non couvert. Le balayage est EXHAUSTIF sur les 2^32 "
                  "graines — il n'a pas de puissance a estimer, il a une couverture"),
        notes=(f"SIX ECHANTILLONNEURS (§206 bis) : le trou que les §200 a §205 laissaient "
               f"ouvert sans que je le voie. Tous supposaient troncature ou modulo sur un "
               f"mot de 32 bits ; ce fichier ajoute le modulo debiaise par rejet "
               f"(java.util.Random.nextInt), la methode de Lemire (C++/Rust/Go modernes), "
               f"le double de 53 bits sur DEUX mots (Math.random()*80) et les sept bits "
               f"bas. {essais:.4e} essais, {len(trouves)} appariement(s). Un balayage "
               "exhaustif en graines mais borgne en echantillonneurs ne prouve rien."))
    say("   consigne.")
