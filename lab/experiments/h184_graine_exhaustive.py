"""h184 — LE BALAYAGE EXHAUSTIF DE L'ESPACE DE GRAINE 32 BITS (RAPPORT §203).

CE QUE LES §200 À §202 NE FERMENT PAS
=====================================
Les trois sections précédentes balayent `2,99·10¹⁰` graines **dérivées** du tirage :
l'heure, l'identifiant, la date, avec et sans échauffement. Elles supposent donc toutes que
la graine est **devinable à partir de ce que l'archive publie**.

Si la machine s'amorce sur autre chose — `srand(getpid())`, une constante de configuration,
un hachage quelconque, un compteur interne — aucun de ces balayages ne la trouve. Le trou
est réel et il est large.

Ce fichier ne suppose rien sur l'origine de la graine : **il les essaie toutes.**

L'ASTUCE QUI REND L'EXHAUSTIF FAISABLE
======================================
Naïvement il faudrait `2³² × 70 560` essais, ce qui est hors de portée. Mais la comparaison
se fait dans l'autre sens :

> pour chaque graine, on engendre **un** tirage et l'on demande « ce tirage est-il **dans**
> l'archive ? » Une table de hachage des `70 560` masques répond en temps constant.

Le balayage devient `2³² × 5 générateurs × 2 échantillonneurs = 4,295·10¹⁰` essais pour
couvrir l'archive **entière** — et non par tirage. Mesuré : `105` minutes sur un cœur,
donc une demi-heure sur les quatre.

CE QUE CELA FERME, EXACTEMENT
=============================
    « Un tirage quelconque de l'archive est-il le PREMIER tirage produit par
      l'un des cinq générateurs modernes amorcé avec une graine de 32 bits,
      quelle qu'en soit l'origine ? »

Une réponse positive donne la graine, donc l'état, donc tout ce qui suit ce tirage.

Une coïncidence fausse a une probabilité de `70 560/C(80,20) = 2,0·10⁻¹⁴` par essai ; sur
`4,3·10¹⁰` essais, l'espérance de faux vaut `8,6·10⁻⁴`. Le résultat reste binaire, et un
appariement resterait réel à mille contre un.

LE TÉMOIN
=========
Trois graines de 32 bits plantées — `3 141 592 653` sous `splitmix64`+troncature,
`2 718 281 828` sous `pcg32`+modulo, `1 234 567 890` sous `pcg64`+troncature — noyées dans
`5 000` tirages de bruit, sont retrouvées toutes les trois, chacune avec le bon générateur,
le bon échantillonneur et la bonne cible.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

POOL, DRAWN = 80, 20
EXP_ID = "h184.graine_exhaustive"
FJETON = "/tmp/h184_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_exhaustive")
CIBLES = "/tmp/h184_cibles.bin"
NBLOC = 4
TOT = 1 << 32


def say(*a):
    print(*a, flush=True)


def bornes():
    pas = TOT // NBLOC
    return [(k * pas, (k + 1) * pas if k < NBLOC - 1 else TOT) for k in range(NBLOC)]


if __name__ == "__main__":
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

    essais = float(TOT) * 5 * 2
    faux = essais * N / 3.5353e18

    HYP = ("Aucun tirage de l'archive n'est le PREMIER tirage produit par l'un des cinq "
           "generateurs modernes a un seul pas — splitmix64, xoshiro256++, xoshiro128**, "
           "pcg32, pcg64 — amorce avec une graine de 32 bits, quelle qu'en soit l'origine. "
           "Les §200 a §202 balayaient des graines DERIVEES du tirage (heure, identifiant, "
           "date) et supposaient donc la graine devinable a partir de ce que l'archive "
           "publie ; si la machine s'amorce sur autre chose — un identifiant de processus, "
           "une constante de configuration, un hachage — aucun ne la trouve. Celui-ci ne "
           "suppose rien : il essaie TOUTES les graines de 32 bits, et compare chacune a "
           "l'archive entiere par table de hachage")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros, en balayant les 2^32 "
            f"graines x 5 generateurs x 2 echantillonneurs = {essais:.4e} essais, chaque "
            f"tirage engendre etant cherche dans une table de hachage des {N} masques de "
            "l'archive")
    NUL = (f"Aucune : une coincidence fausse a une probabilite de {N}/C(80,20) = "
           f"{N/3.5353e18:.2e} par essai, donc {faux:.2e} sur l'ensemble du balayage. Le "
           "resultat est binaire et un appariement resterait reel a mille contre un")
    VER = ("conforme si zero appariement ; GRAINE TROUVEE sinon, auquel cas l'etat est "
           "connu et tout ce qui suit le tirage apparie est predit")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    B = bornes()
    say(f"h184 : {N} cibles ; 2^32 graines en {NBLOC} blocs ; {essais:.4e} essais")
    say(f"   faux attendus {faux:.3e}")

    if "--lancer" in sys.argv:
        for k, (a, b) in enumerate(B):
            jour = f"/tmp/h184_bloc{k}.txt"
            if os.path.exists(jour) and "TERMINE" in open(jour, encoding="utf-8").read():
                say(f"   bloc {k} deja termine")
                continue
            subprocess.Popen([OUTIL, CIBLES, str(a), str(b)],
                             stdout=open(jour, "w"), stderr=subprocess.STDOUT)
            say(f"   bloc {k} lance : graines [{a}, {b})")
        say("   les quatre blocs tournent ; relancer sans --lancer pour agreger")
        sys.exit(0)

    trouves, faits = [], 0
    for k, (a, b) in enumerate(B):
        jour = f"/tmp/h184_bloc{k}.txt"
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
        etat = "termine" if fini else "EN COURS"
        derniere = [L for L in txt.splitlines() if L.startswith("  ...")]
        say(f"   bloc {k} [{a}, {b}) : {etat}"
            + (f"   {derniere[-1].strip()}" if derniere and not fini else ""))

    if faits < NBLOC:
        say(f"\n   {faits}/{NBLOC} blocs termines — rien n'est consigne tant que le "
            "balayage n'est pas complet")
        sys.exit(0)

    say(f"\n   balayage COMPLET : {essais:.4e} essais, {len(trouves)} appariement(s)")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(trouves)), p=1.0 if not trouves else 0.0,
        verdict="GRAINE TROUVEE" if trouves else "conforme",
        power_at=("trois graines de 32 bits plantees — 3 141 592 653 sous splitmix64 et "
                  "troncature, 2 718 281 828 sous pcg32 et modulo, 1 234 567 890 sous "
                  "pcg64 et troncature — noyees dans 5 000 tirages de bruit, sont "
                  "retrouvees toutes les trois, chacune avec le bon generateur, le bon "
                  "echantillonneur et la bonne cible. Le balayage est EXHAUSTIF sur les "
                  "2^32 graines : il n'a pas de puissance a estimer, il a une couverture"),
        notes=(f"BALAYAGE EXHAUSTIF DE L'ESPACE DE GRAINE 32 BITS (§203). Les §200 a §202 "
               f"balayaient des graines DERIVEES et supposaient la graine devinable depuis "
               f"l'archive ; celui-ci les essaie TOUTES. L'exhaustif est rendu faisable en "
               f"inversant la comparaison : pour chaque graine on engendre un tirage et "
               f"l'on demande s'il est dans l'archive, via une table de hachage des {N} "
               f"masques. {essais:.4e} essais couvrant l'archive entiere, "
               f"{len(trouves)} appariement(s). Coincidence fausse : {N/3.5353e18:.2e} par "
               f"essai, {faux:.2e} au total."))
    say("   consigne.")
