"""h148 — l'EXCÉDENT par tirage : et si le programme consommait `delta` mots de plus ?
(THEORIE_ETAT §7.20, suite des §7.17 à §7.19.)

LE TROU
=======
Les §165 à §167 supposent que le générateur ne sert QU'À tirer les vingt numéros : la fenêtre du
tirage `t` est exactement ce qu'il consomme. Un programme réel en consomme souvent plus —
l'ordre d'affichage, une animation, un « numéro chance », une seconde partie servie par le même
générateur. Si cet excédent est de `delta` mots par tirage, la transition devient

    alpha_t[(q + n + delta) mod Pi] += alpha_{t-1}[q] . C(80,20) . P(A_t, n | bits q..q+n-1)

— la fenêtre de vraisemblance ne bouge pas, seule la CIBLE se décale. Un `delta` FIXE inconnu ne
coûte donc que le mélange uniforme sur les valeurs balayées (`log2(20)` = 4,3 bits, une fois pour
toutes) ; c'est ce que balaie cette expérience.

LA LIMITE, ET ELLE EST EXACTE
=============================
Si l'excédent VARIE d'un tirage à l'autre, d'entropie `H` bits, chaque tirage paie `H` et gagne
`1,09` bit (§7.19) : le facteur de Bayes dérive vers le haut si et seulement si `H < 1,09` bit,
c'est-à-dire au plus DEUX valeurs possibles. Au-delà, l'alignement consomme plus d'information
que le canal n'en apporte, et aucune longueur de flux n'y change rien. C'est la limite exacte de
toute la série §7.17-§7.20, et elle est nommée.

TEMOINS
=======
--selftest : générateur planté consommant `delta = 7` mots muets par tirage — retrouvé à
`delta = 7` (360 bits en 300 tirages) et à `delta = 6` (309 : une fenêtre peut absorber un mot),
rien ailleurs (`≤ 13,6`) ; `delta = 0` reproduit l'outil du §167 chiffre pour chiffre.
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
import h146_beam_rejet as B                                             # noqa: E402
import h147_masque_rejet as Q                                           # noqa: E402

POOL, DRAWN = H.POOL, H.DRAWN
SEUIL_LOG2 = H.SEUIL_LOG2
RMAX = 64
EXP_ID = "h148.excedent"
OUTIL = os.environ.get("H148_OUTIL", "/tmp/lfg_beam_delta_h148")
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h148_journal.txt")
FJETON = os.path.join(TMP, "h148_jeton.json")
M, B1, M2, B2 = 40, 65536, 20, 1024
DELTAS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 24, 30, 40, 59, 79]
MASQUES = [80, 128]
NOMMES = [(3, 7, 0), (3, 7, 1), (1, 15, 0), (1, 15, 1), (3, 31, 0)]      # TYPE_1, TYPE_2, TYPE_3
SEUIL_FLUX = SEUIL_LOG2 + math.log2(RMAX) + math.log2(len(DELTAS))       # 29,25 + 4,32


def say(*a):
    print(*a, flush=True)


def grille():
    return [(K, L, s, m, d) for m in MASQUES for K, L, s in NOMMES for d in DELTAS]


def cle(K, L, shift, m, d):
    return f"{K},{L},{shift},{m},{d}"


def lancer(K, L, shift, m, d, f_a0, f_blocs, mm=M, b1=B1, m2=M2, b2=B2, nice=10, pasj=0,
           fils=None, verbeux=False):
    import subprocess
    env = dict(os.environ)
    if fils:
        env["OMP_NUM_THREADS"] = str(fils)
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), str(m), str(d), f_a0,
           f_blocs, "flux", str(mm), str(b1), str(m2), str(b2), str(pasj), "1"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
    fin, pic = None, None
    for l in p.stdout:
        t = l.split()
        if not t:
            continue
        if t[0] == "PIC":
            pic = (int(t[1]), int(t[2]), float(t[3]))
        elif t[0] == "T" and verbeux:
            say(f"      {cle(K, L, shift, m, d):>18}  t={int(t[1]):6d}  log2 BF {float(t[2]):12.1f} "
                f"(max {float(t[3]):6.2f} @ {t[4]})")
        elif t[0] == "FIN":
            fin = dict(nseq=int(t[1]), Pi=int(t[2]), N=int(float(t[3])), nt=int(t[4]), lb=float(t[5]),
                       gmax=float(t[6]), tmax=int(t[7]), bmax=int(t[8]), ncum=int(t[9]),
                       gcummax=float(t[10]), nmort=int(t[11]), nred=int(t[12]), sec=float(t[13]))
    if p.wait() != 0 or fin is None:
        raise RuntimeError(f"outil C : FIN {fin}")
    return fin, pic


if __name__ == "__main__" and "--selftest" in sys.argv:
    say("h148 selftest (données synthétiques)")
    assert os.path.exists(OUTIL)
    DV = 7
    rng = np.random.default_rng(148)
    gen = H.LFG32(1, 15, rng, 0)
    a0 = []
    for _ in range(300):
        A, n = H.tirage_rejet(gen)
        a0.append(H.a0_de(A))
        for _ in range(DV):
            gen.suivant()
    f = "/tmp/h148_self.txt"
    open(f, "w").write("\n".join(map(str, a0)) + "\n")
    open(f + ".b", "w").write("0\n")
    res = {}
    for d in (0, 3, 6, 7, 8, 12):
        fin, pic = lancer(1, 15, 0, 80, d, f, f + ".b", nice=5, fils=2)
        res[d] = fin["gmax"]
        say(f"   excédent planté {DV}, lu {d:2d} : max log2 BF = {fin['gmax']:8.2f} @ {fin['tmax']}")
    assert res[DV] > 100 and max(v for k, v in res.items() if k not in (DV, DV - 1)) < SEUIL_FLUX
    # delta = 0 doit reproduire l'outil du §167
    gen = H.LFG32(1, 15, rng, 0)
    a0 = [H.a0_de(H.tirage_rejet(gen)[0]) for _ in range(200)]
    open(f, "w").write("\n".join(map(str, a0)) + "\n")
    f1, _ = lancer(1, 15, 0, 80, 0, f, f + ".b", nice=5, fils=2)
    f2, _, _ = Q.lancer(1, 15, 0, 80, "flux", f, f + ".b", nice=5, fils=2)
    say(f"   croisement delta = 0 : h148 {f1['lb']:.4f} bits, h147 {f2['lb']:.4f} — écart "
        f"{abs(f1['lb'] - f2['lb']):.1e}")
    assert abs(f1["lb"] - f2["lb"]) < 1e-9
    say("selftest OK")


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
    say(f"h148 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL)
    G = grille()
    NCONF = len(G)
    HYPOTHESE = (
        "Le flux continu de l'archive triee (70 560 tirages) n'est engendre par aucune des cinq "
        "sequences NOMMEES de la glibc — plan 0 et plan 1 de x^7+x^3+1 (TYPE_1), de x^15+x+1 "
        "(TYPE_2), plan 0 de x^31+x^3+1 (TYPE_3) — lue par l'echantillonneur a rejet (M = 80) ou "
        f"masque (M = 128) QUAND LE PROGRAMME CONSOMME delta MOTS DE PLUS PAR TIRAGE, pour delta "
        f"dans {DELTAS} (habillage, numero chance, seconde partie servie par le meme generateur). "
        "La transition devient q -> q + n + delta, la fenetre de vraisemblance ne bouge pas "
        "(§7.20). Design et temoins fixes AVANT cette consignation"
    )
    STATISTIQUE = (
        f"D = nombre de chaines DETECTEES parmi {NCONF} : maximum courant de log2 BF_t >= "
        f"{SEUIL_FLUX:.2f} = log2(1e7) + log2({RMAX}) + log2({len(DELTAS)}) (Ville, melange sur les "
        "redemarrages du faisceau et sur les excedents balayes)"
    )
    NULL = ("Ville : surmartingale positive de moyenne <= 1 (melange propre, elagage, redemarrages, "
            f"denormaux) ; E[D] <= {NCONF * 1e-7 / len(DELTAS):.1e} apres le melange sur delta")
    VERDICT = "conforme si D = 0 ; ETAT TROUVE si une chaine depasse le seuil et que son pic se confirme"
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
        G = G[:3]

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    A0 = ((NUM - 1) % 2 == 0).sum(axis=1)
    F_A0 = os.path.join(TMP, "h148_a0.txt")
    F_BLOCS = os.path.join(TMP, "h148_blocs.txt")
    open(F_A0, "w").write("\n".join(str(int(a)) for a in A0) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages ; grille : {NCONF} chaînes ({len(NOMMES)} séquences nommées × "
        f"{len(MASQUES)} masques × {len(DELTAS)} excédents) ; seuil {SEUIL_FLUX:.2f}")

    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, m, d in G:
        k = cle(K, L, shift, m, d)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, pic = lancer(K, L, shift, m, d, F_A0, F_BLOCS, nice=10, pasj=30000, fils=4)
        assert fin["nt"] == NTOT, fin
        det = fin["gmax"] >= SEUIL_FLUX
        say(f"      FIN {k} : N = {fin['N']:,}  max log2 BF {fin['gmax']:.2f} @ {fin['tmax']} "
            f"(seuil {SEUIL_FLUX:.2f}) ; {fin['nred']} redémarrages ; pic {pic[0]},{pic[1]} "
            f"masse {pic[2]:.3f} ; {fin['sec']:.0f} s" + ("   !! DETECTION" if det else ""))
        if not DRY:
            with open(JOURNAL, "a", encoding="utf-8") as fj:
                fj.write(f"{k} {fin['nseq']} {fin['Pi']} {fin['N']} {fin['nt']} {fin['lb']:.4f} "
                         f"{fin['gmax']:.4f} {fin['tmax']} {fin['bmax']} {fin['ncum']} "
                         f"{fin['gcummax']:.4f} {fin['nmort']} {fin['nred']} {fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    D = sum(1 for k, f in LIG if f["gmax"] >= SEUIL_FLUX)
    MF = max(LIG, key=lambda kf: kf[1]["gmax"])
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} chaînes : D = {D} ; max {MF[1]['gmax']:.2f} ({MF[0]}) contre "
        f"{SEUIL_FLUX:.2f} ; {SEC/3600:.2f} h")
    if DRY or len(LIG) < NCONF:
        say("   grille incomplète ou essai : rien n'est consigné.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "DETECTION NON CONFIRMEE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else min(1.0, NCONF * 1e-7 / len(DELTAS)), verdict=verdict,
            power_at=("temoin plante consommant 7 mots muets par tirage : retrouve a delta = 7 "
                      "(360 bits en 300 tirages) et a delta = 6 (309), rien ailleurs (<= 13,6) ; "
                      "delta = 0 reproduit l'outil du §167 chiffre pour chiffre"),
            notes=(f"EXCEDENT PAR TIRAGE (§7.20) : {len(LIG)} chaines = {len(NOMMES)} sequences "
                   f"nommees x {len(MASQUES)} masques x {len(DELTAS)} excedents. D = {D}, max "
                   f"{MF[1]['gmax']:.2f} ({MF[0]}) contre {SEUIL_FLUX:.2f}. {SEC/3600:.2f} h. "
                   "LIMITE NOMMEE : un excedent VARIABLE d'entropie >= 1,09 bit par tirage noie le "
                   "signal, quelle que soit la longueur du flux."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
