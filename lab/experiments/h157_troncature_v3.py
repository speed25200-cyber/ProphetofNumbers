"""h157 — la troncature sous pas variable, TROISIEME et derniere conception (§7.24 ; §172).

TROIS CONCEPTIONS, ET POURQUOI.
===============================
h152 (plafond de 60 mots par tirage, pas d'elagage de cloturabilite) : la partie par nuit
s'est revelee infaisable — le cout est a queue lourde — et deux configurations ont ete
COUPEES au plafond de noeuds. NON CONSIGNE.

h155 (45 mots, elagage de cloturabilite) : une configuration coupee malgre tout, au decalage
1, la ou delta avait TROIS valeurs et ne laissait que 0,415 bit de decroissance par mot au
lieu de 1. NON CONSIGNE.

h157 ajoute les deux dernieres pieces, toutes deux tirees du lemme du contraste de
collectionneur (§7.24 (v)) — le vrai chemin consomme 22,85 mots par tirage, un faux 71,96 :

  (iii) un BUDGET GLOBAL de mots, 22,85 x ntir a huit ecarts-types pres. EXACT (P < 1e-15) ;
  (iv)  delta reduit a DEUX valeurs au decalage 1. La troisieme — le bit perdu ajoute une
        unite — n'arrive que si la partie fractionnaire tombe a 80/2^31 = 3,7e-8 pres d'un
        entier : sur les ~571 mots d'un ancrage, la probabilite de perdre le vrai chemin
        vaut 2,1e-5, et elle est NOMMEE. La garder coutait un facteur 1 500 (mesure :
        (1,3) shift 1, 3,0e7 -> 2,0e4 noeuds).

Autotest apres chaque changement : 12 cas sur 12 (flux et nuit, deux decalages), etat vrai
retenu, 0 survivant sous H0.
"""


import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h152_troncature as C                                            # noqa: E402

POOL, DRAWN = C.POOL, C.DRAWN
EXP_ID = "h157.troncature_v3"
JOURNAL = "/tmp/h157_journal.txt"
FJETON = "/tmp/h157_jeton.json"
NMAXD = 45
NTIR = C.NTIR
say = C.say
grille = C.grille
cle = C.cle


def lancer(K, L, shift, mode, saut, f_cls, f_blocs, fils=4):
    import subprocess
    env = dict(os.environ, OMP_NUM_THREADS=str(fils))
    cmd = ["nice", "-n", "15", C.OUTIL, str(K), str(L), str(shift), mode, f_cls, f_blocs,
           str(NTIR), str(saut), str(NMAXD), str(C.plafond(L))]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"{cle(K,L,shift,mode,saut)} : {p.returncode}\n{p.stderr[:400]}")
    fin = {"sec": time.time() - t0, "surv": 0, "noeuds": 0, "pic": 0, "coupes": 0, "sols": []}
    for ligne in p.stdout.splitlines():
        t = ligne.split()
        if t and t[0] == "noeuds":
            fin["noeuds"] = int(t[1]); fin["pic"] = int(t[3])
            fin["surv"] = int(t[5]); fin["coupes"] = int(t[7])
        elif t and t[0] == "surv" and len(fin["sols"]) < 8:
            fin["sols"].append(" ".join(t[1:]))
    return fin


def lire_journal():
    d = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 6 and t[0] != "#":
                d[t[0]] = dict(noeuds=int(t[1]), pic=int(t[2]), surv=int(t[3]),
                               coupes=int(t[4]), sec=float(t[5]))
    return d


if __name__ == "__main__" and "--archive" in sys.argv:
    import lab
    T0 = time.time()
    C.compiler()
    G = grille()
    NCONF = len(G)
    say(f"h155 --archive  outil {C.OUTIL} ; {NCONF} configurations ; NMAXD = {NMAXD}")
    HYPOTHESE = (
        "L'archive triee (70 560 tirages, 370 blocs de nuit) n'est engendree par aucun "
        "Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur "
        "a TRONCATURE v = 1 + ((x * 80) >> 32) avec rejet des doublons, pour x = r (shift 0) "
        "comme x = r >> 1 (shift 1), sur les 13 trinomes primitifs de degre <= 7 en flux "
        "continu, les 9 de degre <= 6 par nuit (1 nuit sur 10) et les 4 de degre 7 par nuit "
        "(1 nuit sur 37) — 52 configurations. Crible de classes (§7.24) : automate non "
        "deterministe sur (Z/80)^L, 1 bit de branchement par mot contre 2 bits d'elagage, "
        "alignement deduit et non branche, elagage de cloturabilite, plafond de 45 mots par "
        "tirage, budget global de mots a 8 sigma, et delta reduit a deux valeurs au decalage 1. "
        "REPREND les grilles de h152 et h155, toutes deux abandonnees pour cause de "
        "configurations coupees au plafond de noeuds"
    )
    STATISTIQUE = (f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant "
                   f"(un L-uplet de classes dont l'automate cloture {NTIR} tirages consecutifs), "
                   "ET dont le parcours est COMPLET : une configuration coupee au plafond de "
                   "noeuds n'exclut rien et interdit la consignation")
    NULL = (f"Crible DUR, pas de martingale : zero survivant EXCLUT la configuration a la "
            f"probabilite pres que le vrai generateur consomme plus de {NMAXD} mots pour un "
            f"tirage, P(N > {NMAXD}) = 1,3e-11, soit 3,2e-7 sur les ~24 700 tirages parcourus "
            "par la grille. Sous H0 le front decroit d'un bit par mot en moyenne — mais le "
            "cout est a QUEUE LOURDE (les tirages a classes consecutives creent des poches "
            "surcritiques), d'ou le plafond de noeuds et l'exigence de parcours complet. "
            "Au decalage 1, delta est reduit a deux valeurs : perte de puissance 2,1e-5 par "
            "ancrage, nommee")
    VERDICT = "conforme si D = 0 et aucune coupe ; ETAT TROUVE si un survivant se releve (§173)"
    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    F_CLS, F_BLOCS = "/tmp/h155_classes.txt", "/tmp/h155_blocs.txt"
    open(F_CLS, "w").write("\n".join(" ".join(str(int(v)) for v in l) for l in (NUM - 1)) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {len(TS)} tirages, {len(DEB)} blocs")

    FAIT = lire_journal()
    for K, L, shift, mode, saut in G:
        k = cle(K, L, shift, mode, saut)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin = lancer(K, L, shift, mode, saut, F_CLS, F_BLOCS)
        say(f"      FIN {k} : {fin['noeuds']:,} noeuds, pic {fin['pic']:,}, "
            f"{fin['surv']} survivants, {fin['coupes']} coupes, {fin['sec']:.0f} s"
            + ("   !! SURVIVANT" if fin["surv"] else ""))
        for s in fin["sols"]:
            say(f"         sol {s}")
        with open(JOURNAL, "a", encoding="utf-8") as fj:
            fj.write(f"{k} {fin['noeuds']} {fin['pic']} {fin['surv']} {fin['coupes']} "
                     f"{fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    INC = [k for k, f in LIG if f["coupes"] > 0]
    D = sum(1 for k, f in LIG if f["surv"] > 0)
    NOE = sum(f["noeuds"] for k, f in LIG)
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; {NOE:,} noeuds, "
        f"{len(INC)} non concluantes, {SEC/3600:.2f} h")
    if len(LIG) < NCONF:
        say("   grille incomplete : rien n'est consigne.")
    elif INC:
        say(f"   {len(INC)} configurations coupees : elles n'excluent RIEN. Rien n'est consigne.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "SURVIVANT NON RELEVE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else 0.0, verdict=verdict,
            power_at=("temoins plantes : suite (K,L) lue par troncature avec rejet puis TRIEE, "
                      "etat vrai retenu a tous les coups en flux comme par nuit (12 cas sur 12, "
                      "deux decalages), 0 survivant sous H0"),
            notes=(f"TRONCATURE SOUS PAS VARIABLE, 2e conception (§172) : {len(LIG)} "
                   f"configurations, {NOE:,} noeuds, {SEC/3600:.2f} h, parcours complet. D = {D}. "
                   f"Plafond de {NMAXD} mots par tirage (P = 1,3e-11 par tirage, 3,2e-7 sur la "
                   "grille) et elagage exact de cloturabilite : sans eux le cout est a queue "
                   "lourde. REMPLACE h152 et h155, tous deux abandonnes pour configurations "
                   "coupees. NON COUVERT : le degre 8 (pas de trinome primitif), le degre 9 "
                   "(h154), le degre 10 et au-dela."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
            f"{sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
