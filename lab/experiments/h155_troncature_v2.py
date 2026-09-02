"""h155 — la troncature sous pas variable, DEUXIEME conception (THEORIE_ETAT §7.24 ; §172).

POURQUOI UNE DEUXIEME.
=====================
Le §172 (h152) a ete pre-enregistre avec un plafond de 60 mots par tirage et un modele de
cout « 2,5 x 20^L noeuds ». Le modele etait une MOYENNE, pas une borne, et la mesure l'a
dementi : le facteur de branchement vaut 0,50 en moyenne (sous-critique) mais un tirage qui
contient des classes CONSECUTIVES — 25, 26, 27, 28 par exemple — cree des poches
SURCRITIQUES, parce que les deux valeurs de delta y sont publiees a la fois. Un arbre
sous-critique en moyenne peut y grossir sans fin. Mesure : au degre 3, l'ancrage de la nuit
20 coute 2,4e9 noeuds contre 2e4 predits — dix mille fois le modele. La partie « par nuit »
de la grille du §172 est donc devenue infaisable, et deux configurations y ont ete COUPEES
au plafond de noeuds : elles n'excluent rien.

CE QUI CHANGE, ET C'EST TOUT.
=============================
(i) un elagage EXACT que la premiere version n'avait pas : il faut encore `20 - nacc` mots
    acceptants pour cloturer le tirage, donc tout chemin verifiant
    `wd + (20 - nacc) > NMAXD` est mort. Facteur 6 mesure ;
(ii) le plafond par tirage passe de 60 a 45 mots. P(N > 45) = 1,3e-11 par tirage, soit
    3,2e-7 sur les ~24 700 tirages que la grille parcourt — la perte de puissance est
    nommee, et elle est negligeable. Facteur 67 mesure.

Ensemble : l'ancrage pathologique passe de 2,4e9 a 5,6e6 noeuds au degre 3, et le degre 6
y coute 2,2e9 noeuds, soit sept secondes. La grille redevient faisable.

Rien d'autre ne change : meme outil, memes lemmes, memes temoins, meme grille de 52
configurations.
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
EXP_ID = "h155.troncature_v2"
JOURNAL = "/tmp/h155_journal.txt"
FJETON = "/tmp/h155_jeton.json"
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
        "alignement deduit et non branche. REPREND la grille du §172 (h152), dont la partie "
        "par nuit s'est revelee infaisable sous son plafond de 60 mots par tirage"
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
            "surcritiques), d'ou le plafond de noeuds et l'exigence de parcours complet")
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
                   "lourde. REMPLACE h152, dont la partie par nuit etait infaisable sous un "
                   "plafond de 60. NON COUVERT : le degre 8 (pas de trinome primitif), le degre "
                   "9 (§174, h154), le degre 10 et au-dela."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
            f"{sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
