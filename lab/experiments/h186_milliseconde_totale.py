"""h186 — LA MILLISECONDE, SUR TOUTE LA DURÉE DE L'ARCHIVE (RAPPORT §205).

CE QUE LE §200 LAISSAIT DE CÔTÉ
================================
Le §200 balaye la milliseconde, mais seulement dans une fenêtre de `±600 s` autour des
`346` débuts de nuit — soit `4,15·10⁸` millisecondes. L'archive s'étend sur `346` jours,
c'est-à-dire `2,99·10¹⁰` millisecondes. **Le §200 en couvrait donc `1,4 %`.**

Ce fichier couvre les `100 %`.

CE QUE CELA FERME
=================
    « Un tirage quelconque de l'archive est-il le PREMIER tirage produit par
      l'un des cinq générateurs modernes amorcé sur UNE MILLISECONDE QUELCONQUE
      des 346 jours que l'archive couvre ? »

C'est l'énoncé le plus large qu'un balayage de graine d'horloge puisse avoir sur ces
données : il ne suppose ni que l'amorçage a lieu près d'un tirage, ni près d'un début de
nuit, ni à un moment particulier. N'importe quelle milliseconde de la vie de l'archive.

L'outil est celui du §203 : il balaye une plage contiguë de graines et compare chacune à
l'archive **entière** par table de hachage. La plage est ici
`[ts_premier·1000 , (ts_dernier+1)·1000)`, soit `2,99·10¹⁰` graines, et le balayage vaut
`2,99·10¹¹` essais — environ trois heures et demie sur quatre cœurs.

Résultat binaire, comme aux §200 à §204 : coïncidence fausse à `2,0·10⁻¹⁴` par essai.
"""

import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN = 80, 20
EXP_ID = "h186.milliseconde_totale"
FJETON = "/tmp/h186_jeton.json"
OUTIL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools_bin", "graine_exhaustive")
CIBLES = "/tmp/h186_cibles.bin"
NBLOC = 4


def say(*a):
    print(*a, flush=True)


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

    DEB = int(TS[0]) * 1000
    FIN = (int(TS[-1]) + 1) * 1000
    span = FIN - DEB
    pas = span // NBLOC
    B = [(DEB + k * pas, DEB + (k + 1) * pas if k < NBLOC - 1 else FIN)
         for k in range(NBLOC)]
    essais = float(span) * 5 * 2
    faux = essais * N / 3.5353e18
    jours = span / 1000 / 86400

    HYP = ("Aucun tirage de l'archive n'est le PREMIER tirage produit par l'un des cinq "
           "generateurs modernes a un seul pas amorce sur UNE MILLISECONDE QUELCONQUE des "
           f"{jours:.0f} jours que l'archive couvre. Le §200 balayait la milliseconde mais "
           "seulement dans une fenetre de +-600 s autour des 346 debuts de nuit, soit "
           "4,15e8 millisecondes — 1,4 % de l'etendue. Celui-ci couvre les 100 %, sans "
           "supposer que l'amorcage ait lieu pres d'un tirage, pres d'un debut de nuit, ni "
           "a un moment particulier")
    STAT = (f"nombre d'appariements exacts sur les vingt numeros, en balayant les "
            f"{span} millisecondes de [{DEB}, {FIN}) x 5 generateurs x 2 echantillonneurs "
            f"= {essais:.4e} essais, chaque tirage engendre etant cherche dans une table de "
            f"hachage des {N} masques de l'archive")
    NUL = (f"Aucune : une coincidence fausse vaut {N}/C(80,20) = {N/3.5353e18:.2e} par "
           f"essai, donc {faux:.2e} sur l'ensemble. Resultat binaire")
    VER = ("conforme si zero appariement ; GRAINE TROUVEE sinon, auquel cas l'etat est "
           "connu et tout ce qui suit le tirage apparie est predit")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h186 : etendue {jours:.1f} jours = {span} ms ; {essais:.4e} essais")
    say(f"   faux attendus {faux:.3e} ; le §200 en couvrait "
        f"{100*4.15e8/span:.2f} %")

    if "--lancer" in sys.argv:
        for k, (a, b) in enumerate(B):
            jour = f"/tmp/h186_bloc{k}.txt"
            if os.path.exists(jour) and "TERMINE" in open(jour, encoding="utf-8").read():
                say(f"   bloc {k} deja termine")
                continue
            # reprise : on repart de la derniere graine annoncee
            depart = a
            if os.path.exists(jour):
                marques = [L for L in open(jour, encoding="utf-8").read().splitlines()
                           if L.startswith("  ... graine ")]
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
        jour = f"/tmp/h186_bloc{k}.txt"
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
        power_at=("le balayage est EXHAUSTIF sur la milliseconde pour toute l'etendue de "
                  "l'archive : il n'a pas de puissance a estimer, il a une couverture. "
                  "L'outil est celui du §203, dont le temoin retrouve trois graines de "
                  "32 bits plantees sur trois, chacune avec le bon generateur, le bon "
                  "echantillonneur et la bonne cible"),
        notes=(f"MILLISECONDE TOTALE (§205) : le §200 ne couvrait que 1,4 % de l'etendue "
               f"(fenetre de +-600 s autour des debuts de nuit) ; celui-ci couvre les "
               f"100 %. {span} millisecondes sur {jours:.0f} jours, cinq generateurs "
               f"modernes x deux echantillonneurs, {essais:.4e} essais compares a "
               f"l'archive entiere par table de hachage. {len(trouves)} appariement(s)."))
    say("   consigne.")
