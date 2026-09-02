"""h154 — la troncature au degre 9 : ce que le §172 laisse juste au-dessus de sa portee.

Le §172 lit les 13 trinomes primitifs de degre <= 7 (front 20^L, soit 2^30,3 au degre 7).
Le degre 8 n'a pas de trinome primitif ; le degre 9 en a deux, (4,9) et (5,9), au front
20^9 = 2^38,9 — environ 1,3e12 noeuds, deux a trois heures par configuration. C'est la
derniere marche que l'ordre de flux permet de monter sans outil nouveau, et elle est
franchie ici. Le degre 10 (2^43,2, une quarantaine d'heures par configuration) ne l'est
pas, et c'est dit.

Tout le reste — outil, lemmes, temoins, plafond par tirage — est celui du §172.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h147_masque_rejet as Q                                           # noqa: E402
import h152_troncature as C                                            # noqa: E402

POOL, DRAWN = C.POOL, C.DRAWN
EXP_ID = "h154.troncature_9"
JOURNAL = "/tmp/h154_journal.txt"
FJETON = "/tmp/h154_jeton.json"
say = C.say


def grille():
    t9 = [(K, L) for K, L in Q.TRIN0 if L == 9]
    return [(K, L, s, "flux", 1) for s in (0, 1) for K, L in t9]


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
    T9 = [(K, L) for K, L in Q.TRIN0 if L == 9]
    say(f"h154 --archive  outil {C.OUTIL} ; {NCONF} configurations")
    HYPOTHESE = (
        "L'archive triee (70 560 tirages) n'est engendree, en flux continu, par aucun "
        "Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 de degre 9 lu par "
        "l'echantillonneur a TRONCATURE v = 1 + ((x * 80) >> 32) avec rejet des doublons, "
        f"pour x = r (shift 0) comme x = r >> 1 (shift 1) : les {len(T9)} trinomes primitifs "
        "de degre 9, soit 4 configurations. Meme outil, memes lemmes et memes temoins que le "
        "§172 (crible de classes, automate non deterministe sur (Z/80)^L)"
    )
    STATISTIQUE = (f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant, "
                   f"c'est-a-dire un 9-uplet de classes dont l'automate cloture {C.NTIR} "
                   "tirages consecutifs, ET dont le parcours est COMPLET (aucune coupe)")
    NULL = ("Crible DUR : zero survivant EXCLUT la configuration a 1,3e-15 pres (plafond de "
            f"{C.NMAXD} mots par tirage, P(N > {C.NMAXD}) = 1,8e-20 par tirage). Ce n'est pas "
            "une martingale et il n'y a pas de seuil : le verdict est exact ou il n'est pas")
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
    F_CLS, F_BLOCS = "/tmp/h152_classes.txt", "/tmp/h152_blocs.txt"
    if not os.path.exists(F_CLS):
        open(F_CLS, "w").write("\n".join(" ".join(str(int(v)) for v in l) for l in (NUM - 1)) + "\n")
        open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {len(TS)} tirages, {len(DEB)} blocs")

    FAIT = lire_journal()
    for K, L, shift, mode, saut in G:
        k = C.cle(K, L, shift, mode, saut)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin = C.lancer(K, L, shift, mode, saut, F_CLS, F_BLOCS, nice=15, fils=4)
        say(f"      FIN {k} : {fin['noeuds']:,} noeuds, pic {fin['pic']:,}, "
            f"{fin['surv']} survivants, {fin['coupes']} coupes, {fin['sec']:.0f} s"
            + ("   !! SURVIVANT" if fin["surv"] else ""))
        with open(JOURNAL, "a", encoding="utf-8") as fj:
            fj.write(f"{k} {fin['noeuds']} {fin['pic']} {fin['surv']} {fin['coupes']} "
                     f"{fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(C.cle(*c), FAIT[C.cle(*c)]) for c in G if C.cle(*c) in FAIT]
    INC = [k for k, f in LIG if f["coupes"] > 0]
    D = sum(1 for k, f in LIG if f["surv"] > 0)
    NOE = sum(f["noeuds"] for k, f in LIG)
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; {NOE:,} noeuds, "
        f"{len(INC)} non concluantes, {SEC/3600:.2f} h")
    if len(LIG) < NCONF:
        say("   grille incomplete : rien n'est consigne.")
    elif INC:
        say(f"   {len(INC)} configurations coupees au plafond : elles n'excluent RIEN. "
            "Rien n'est consigne.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "SURVIVANT NON RELEVE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else 0.0, verdict=verdict,
            power_at=("les memes temoins que le §172 : suite plantee lue par troncature avec "
                      "rejet puis TRIEE, etat vrai retenu a tous les coups, 0 survivant sous H0, "
                      "cout conforme a 2,5 x 20^L au chiffre pres"),
            notes=(f"TRONCATURE, DEGRE 9 (§174) : {len(LIG)} configurations, {NOE:,} noeuds, "
                   f"{SEC/3600:.2f} h, parcours complet. D = {D}. NON COUVERT : le degre 10 "
                   "(2^43,2 par configuration) et au-dela ; le degre 8 n'a pas de trinome "
                   "primitif."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
            f"{sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
