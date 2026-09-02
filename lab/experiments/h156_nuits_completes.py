"""h156 — la troncature par nuit, sur les 370 NUITS, sans sous-echantillonnage (§172).

CE QUE LE §172 LAISSE COMME RESERVE.
====================================
La grille du §172 lit le mode « par nuit » sur UNE NUIT SUR DIX (37 ancrages) au degre <= 6
et une sur trente-sept (10 ancrages) au degre 7 : c'etait le seul budget disponible sous la
premiere conception. Les deux corrections du §172 — l'elagage de cloturabilite et le plafond
de 45 mots par tirage — ont divise le cout par 400 sur les ancrages pathologiques. La reserve
tombe donc au degre <= 6 : les 370 nuits y tiennent en une demi-heure.

Le degre 7 reste hors budget en nuits completes (370 ancrages x 23 s = 2,4 h par
configuration, 19 h pour les huit) et n'est pas repris ici : il reste couvert a une nuit sur
trente-sept par le §172, et c'est dit.

L'hypothese est celle du generateur REAMORCE chaque soir — chaque nuit est un ancrage
independant, donc ce mode couvre AUSSI le flux continu a fortiori.
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
import h155_troncature_v2 as V                                         # noqa: E402

EXP_ID = "h156.nuits_completes"
JOURNAL = "/tmp/h156_journal.txt"
FJETON = "/tmp/h156_jeton.json"
say = C.say


def grille():
    t6 = [(K, L) for K, L in Q.TRIN0 if L <= 6]
    return [(K, L, s, "nuit", 1) for s in (0, 1) for K, L in t6]


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
    T6 = [(K, L) for K, L in Q.TRIN0 if L <= 6]
    say(f"h156 --archive ; {NCONF} configurations x 370 nuits ; NMAXD = {V.NMAXD}")
    HYPOTHESE = (
        "Aucun des 370 BLOCS DE NUIT de l'archive triee (generateur reamorce chaque soir) "
        "n'est engendre par un Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu "
        "par l'echantillonneur a TRONCATURE v = 1 + ((x * 80) >> 32) avec rejet des doublons, "
        f"pour x = r (shift 0) comme x = r >> 1 (shift 1), sur les {len(T6)} trinomes "
        "primitifs de degre <= 6 : 18 configurations, TOUTES LES NUITS (sans sous-echantillon). "
        "Leve la reserve « une nuit sur dix » du §172 pour ces degres. Meme outil, memes "
        "lemmes, memes temoins que le §172"
    )
    STATISTIQUE = (f"D = nombre de configurations parmi {NCONF} laissant AU MOINS UN survivant "
                   f"sur l'une des 370 nuits (un L-uplet de classes dont l'automate cloture "
                   f"{V.NTIR} tirages consecutifs), ET dont le parcours est COMPLET")
    NULL = (f"Crible DUR : zero survivant EXCLUT a la probabilite pres que le vrai generateur "
            f"consomme plus de {V.NMAXD} mots pour un tirage, P = 1,3e-11 par tirage, soit "
            "2,4e-6 sur les ~185 000 tirages parcourus (18 x 370 x 25). Cout a queue lourde : "
            "d'ou le plafond de noeuds et l'exigence de parcours complet")
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
        fin = V.lancer(K, L, shift, mode, saut, F_CLS, F_BLOCS)
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
        say(f"   {len(INC)} configurations coupees : elles n'excluent RIEN. Rien n'est consigne.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "SURVIVANT NON RELEVE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else 0.0, verdict=verdict,
            power_at=("temoins du §172 en mode nuit : trois nuits plantees, generateur reamorce "
                      "a chaque bloc, etat vrai retenu 3 fois sur 3 aux deux decalages, et "
                      "0 survivant sur des nuits tirees sous H0"),
            notes=(f"TRONCATURE PAR NUIT, 370 NUITS COMPLETES (§172) : {len(LIG)} "
                   f"configurations x 370 ancrages, {NOE:,} noeuds, {SEC/3600:.2f} h, parcours "
                   f"complet. D = {D}. Leve la reserve « une nuit sur dix » du §172 au degre "
                   "<= 6. NON COUVERT : le degre 7 en nuits completes (19 h), qui reste a une "
                   "nuit sur trente-sept."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
            f"{sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
