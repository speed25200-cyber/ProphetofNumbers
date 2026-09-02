"""h150 — le rejet MASQUÉ, par NUIT : l'hypothèse du générateur réamorcé chaque soir, sous
l'échantillonneur recommandé (THEORIE_ETAT §7.19 ; le §167 ne lit que le flux continu).

LE TROU
=======
Le §165 lit les 370 nuits sous le rejet `mod 80` ; le §167 lit le flux continu sous le rejet
MASQUÉ (`v = 1 + (x mod M)`, refusé si `v > 80`). Manque le croisement des deux : un générateur
réamorcé chaque soir ET lu au masque. C'est l'objet de ce §170. Une phase pleine par nuit coûte
`N` par bloc : la grille se limite donc aux suites que 370 phases pleines laissent accessibles —
plan 0 des trinômes de degré `≤ 18` (`N ≤ 262 143`) et plan 1 de ceux de degré `≤ 11`
(`N ≤ 4 192 254`), sous `M = 100` et `M = 128`.

Chaque nuit est une chaîne indépendante (loi a priori uniforme au début du bloc) : seuil
`log₂(10⁷) + log₂(nombre de blocs traités)`, plus la chaîne des blocs cumulés au seuil `23,25`.
Aucun redémarrage n'y intervient (un bloc mort reste mort), donc pas de mélange à payer.
"""

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h145_sync_rejet as H                                             # noqa: E402
import h147_masque_rejet as Q                                           # noqa: E402

POOL, DRAWN = H.POOL, H.DRAWN
SEUIL_LOG2 = H.SEUIL_LOG2
EXP_ID = "h150.masque_nuit"
OUTIL = Q.OUTIL
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h150_journal.txt")
FJETON = os.path.join(TMP, "h150_jeton.json")
M, B1, M2, B2 = 40, 65536, 20, 1024
MASQUES = [100, 128]
LMAX0, LMAX1 = 18, 11


def say(*a):
    print(*a, flush=True)


TRIN0 = [(K, L) for K, L in Q.TRIN0 if L <= LMAX0]
TRIN1 = [(K, L) for K, L in Q.TRIN0 if L <= LMAX1]


def grille():
    g = []
    for m in MASQUES:
        g += [(K, L, 0, m) for K, L in TRIN0]
        g += [(K, L, 1, m) for K, L in TRIN1]
    return g


def cle(K, L, shift, m):
    return f"{K},{L},{shift},{m},nuit"


def lire_journal():
    d = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 14 and t[0] != "#":
                d[t[0]] = dict(nseq=int(t[1]), Pi=int(t[2]), N=int(t[3]), nt=int(t[4]), lb=float(t[5]),
                               gmax=float(t[6]), tmax=int(t[7]), bmax=int(t[8]), ncum=int(t[9]),
                               gcummax=float(t[10]), nmort=int(t[11]), nred=int(t[12]), sec=float(t[13]))
    return d


if __name__ == "__main__" and "--archive" in sys.argv:
    import lab
    DRY = "--dry" in sys.argv
    T0 = time.time()
    say(f"h150 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL)
    G = grille()
    NCONF = len(G)
    HYPOTHESE = (
        "Aucun des 370 BLOCS DE NUIT de l'archive triee (generateur reamorce chaque soir) n'est "
        "engendre par un Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu par "
        "l'echantillonneur a rejet MASQUE (v = 1 + (x mod M), refuse si v > 80, puis refuse si deja "
        f"tire) pour M = 100 et M = 128 : plan 0 des {len(TRIN0)} trinomes primitifs de degre <= "
        f"{LMAX0}, plan 1 des {len(TRIN1)} de degre <= {LMAX1}. C'est le croisement des §165 (nuits, "
        "rejet simple) et §167 (flux, rejet masque), que ni l'un ni l'autre ne couvre. Methode : DP "
        "de synchronisation en flot puis faisceau (§7.18), une chaine par bloc"
    )
    STATISTIQUE = (
        f"D = nombre de configurations DETECTEES parmi {NCONF} : maximum sur les blocs de log2 BF "
        "(seuil log2(1e7) + log2(nombre de blocs)), ou chaine des blocs cumules (seuil 23,25)"
    )
    NULL = ("Ville : chaque bloc est une surmartingale positive de moyenne <= 1 partant de 1 "
            f"(melange propre, elagage, denormaux) ; borne d'union E[D] <= {2 * NCONF * 1e-7:.1e}")
    VERDICT = "conforme si D = 0 ; ETAT TROUVE si une chaine depasse son seuil et que son pic se confirme"
    if not DRY:
        if os.path.exists(FJETON):
            TOK = json.load(open(FJETON, encoding="utf-8"))
            say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
        else:
            TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
            json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
            say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        say("   MODE ESSAI : pas de jeton.")
        G = G[:2]

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    if DRY:                       # l'essai ne lit PAS l'archive : a0 tires sous H0
        rng = np.random.default_rng(150)
        A0 = np.array([int(((rng.choice(POOL, DRAWN, replace=False)) % 2 == 0).sum())
                       for _ in range(NTOT)])
        F_A0 = os.path.join(TMP, "h150_dry_a0.txt")
    else:
        A0 = ((NUM - 1) % 2 == 0).sum(axis=1)
        F_A0 = os.path.join(TMP, "h150_a0.txt")
    F_BLOCS = os.path.join(TMP, "h150_blocs.txt")
    open(F_A0, "w").write("\n".join(str(int(a)) for a in A0) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages, {len(DEB)} blocs ; grille : {NCONF} configurations "
        f"({len(TRIN0)} plan 0 + {len(TRIN1)} plan 1, × {len(MASQUES)} masques)")

    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, m in G:
        k = cle(K, L, shift, m)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, pic, blocs = Q.lancer(K, L, shift, m, "nuit", F_A0, F_BLOCS, mm=M, b1=B1, m2=M2, b2=B2,
                                   saut=1, nice=10, pasj=0, fils=4)
        assert fin["nt"] == NTOT, fin
        seuil = SEUIL_LOG2 + math.log2(max(1, fin["ncum"]))
        det = int(fin["gmax"] >= seuil) + int(fin["gcummax"] >= SEUIL_LOG2)
        say(f"      FIN {k} : {fin['nseq']}x{fin['Pi']} = {fin['N']:,}  max par nuit "
            f"{fin['gmax']:.2f} (bloc {fin['bmax']}, seuil {seuil:.2f}) ; {fin['ncum']} blocs, "
            f"cumul max {fin['gcummax']:.2f} ; {fin['nmort']} morts ; {fin['sec']:.0f} s"
            + ("   !! DETECTION" if det else ""))
        if not DRY:
            with open(JOURNAL, "a", encoding="utf-8") as fj:
                fj.write(f"{k} {fin['nseq']} {fin['Pi']} {fin['N']} {fin['nt']} {fin['lb']:.4f} "
                         f"{fin['gmax']:.4f} {fin['tmax']} {fin['bmax']} {fin['ncum']} "
                         f"{fin['gcummax']:.4f} {fin['nmort']} {fin['nred']} {fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    def seuil_de(f):
        return SEUIL_LOG2 + math.log2(max(1, f["ncum"]))
    D = sum(1 for k, f in LIG if f["gmax"] >= seuil_de(f)) + \
        sum(1 for k, f in LIG if f["gcummax"] >= SEUIL_LOG2)
    MN = max(LIG, key=lambda kf: kf[1]["gmax"])
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; max par nuit {MN[1]['gmax']:.2f} ({MN[0]}, "
        f"bloc {MN[1]['bmax']}) contre {seuil_de(MN[1]):.2f} ; {SEC/3600:.2f} h")
    if DRY or len(LIG) < NCONF:
        say("   grille incomplète ou essai : rien n'est consigné.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "DETECTION NON CONFIRMEE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else min(1.0, 2 * NCONF * 1e-7), verdict=verdict,
            power_at=("les temoins du §167 (meme outil, meme vraisemblance masquee) : plantes lus au "
                      "bon masque detectes en 200 a 250 tirages, au mauvais masque rien ; et ceux du "
                      "§165 pour le mode par nuit (planté par blocs de 204, retrouvé bloc par bloc)"),
            notes=(f"REJET MASQUE PAR NUIT (§170) : {len(LIG)} configurations ({len(TRIN0)} plan 0 "
                   f"L <= {LMAX0}, {len(TRIN1)} plan 1 L <= {LMAX1}, M = 100 et 128), 370 blocs "
                   f"chacune. D = {D}. max par nuit {MN[1]['gmax']:.2f} ({MN[0]}). {SEC/3600:.2f} h. "
                   "NON COUVERT : les degres superieurs (une phase pleine par nuit), M = 256."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
