"""h149 — le canal MOD 4 : deux bits par mot, et le JUMEAU entrelacé (THEORIE_ETAT §7.21).

LE TROU QUE CELA FERME
======================
Le §7.20 s'arrête sur une limite exacte : la synchronisation ne dérive vers le haut que si
l'entropie de l'excédent par tirage est inférieure au débit du canal, `1,09` bit. Un générateur
PARTAGÉ — servant un autre tirage du même jeu entre deux des nôtres — coûte `H(N) = 2,85` bits
(loi exacte du §7.17) : illisible par la parité, quelle que soit la longueur du flux.

Le canal mod 4 lève cela. Le numéro publié donne `v − 1 = x mod 80`, donc `x mod 4` : DEUX bits
du mot (80 = 4 × 20). L'état caché est le couple (plan 0, plan 1) — les orbites du Fibonacci
mod 4 déjà construites au §7.17 —, soit `N = (2^L − 1) 2^L` ; pour la sortie décalée de la glibc
(`x = r >> 1`), le triplet mod 8, `N = (2^L − 1) 2^{2L}`.

    P(A, n | fenêtre) = [Π_{c ≠ c*} F₂₀(w_c, a_c)] · G₂₀(w_{c*}, a_{c*})
    F₂₀(w, a) = a! S(w, a) / 20^w,  G₂₀(w, a) = a! S(w−1, a−1) / 20^w

Débit mesuré : `5,37` bits par tirage (contre `1,31`). Avec un jumeau entrelacé, le noyau est
une convolution par `P₀(n')` et le net vaut `+2,53` bit par tirage au lieu de `−1,54`.

TEMOINS (--selftest)
====================
planté sans jumeau, lu sans jumeau : détecté ; lu AVEC jumeau : rien.
planté AVEC jumeau, lu sans : rien ; lu avec : détecté.  Tirages nuls : rien.
"""

import json
import math
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h145_sync_rejet as H                                             # noqa: E402

POOL, DRAWN = H.POOL, H.DRAWN
SEUIL_LOG2 = H.SEUIL_LOG2
RMAX = 64
EXP_ID = "h149.canal_mod4"
OUTIL = os.environ.get("H149_OUTIL", "/tmp/lfg_beam_mod4_h149")
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h149_journal.txt")
FJETON = os.path.join(TMP, "h149_jeton.json")
M, B1, M2, B2 = 16, 65536, 20, 1024          # le canal est 4 fois plus riche : m = 16 suffit
SEUIL_FLUX = SEUIL_LOG2 + math.log2(RMAX)    # 29,25
LMAX0, LMAX1 = 15, 10                        # mod 4 : N = 2^{2L} ; mod 8 : N = 2^{3L-...}


def say(*a):
    print(*a, flush=True)


TRIN = [(K, L) for L in range(2, 32) for K in range(1, L) if H.primitif(K, L)]
TRIN0 = [(K, L) for K, L in TRIN if L <= LMAX0]
TRIN1 = [(K, L) for K, L in TRIN if L <= LMAX1]


def grille():
    g = [(K, L, 0, j) for j in (0, 1) for K, L in TRIN0]
    g += [(K, L, 1, j) for j in (0, 1) for K, L in TRIN1]
    return g


def cle(K, L, shift, jumeau):
    return f"{K},{L},{shift},{jumeau}"


def ac_de(A):
    """les quatre comptes de classes mod 4 du tirage (a_c = #{v : (v-1) mod 4 = c})."""
    c = [0, 0, 0, 0]
    for v in A:
        c[(v - 1) % 4] += 1
    return c


def ecrire(fichier, L, blocs=(0,)):
    open(fichier, "w").write("\n".join(" ".join(map(str, c)) for c in L) + "\n")
    open(fichier + ".b", "w").write("\n".join(map(str, blocs)) + "\n")


def lancer(K, L, shift, jumeau, f_ac, f_blocs, m=M, b1=B1, m2=M2, b2=B2, mode="flux", saut=1,
           nice=10, pasj=0, fils=None, verbeux=False):
    env = dict(os.environ)
    if fils:
        env["OMP_NUM_THREADS"] = str(fils)
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), str(jumeau), f_ac, f_blocs,
           mode, str(m), str(b1), str(m2), str(b2), str(pasj), str(saut)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
    fin, pic = None, None
    for l in p.stdout:
        t = l.split()
        if not t:
            continue
        if t[0] == "PIC":
            pic = (int(t[1]), int(t[2]), float(t[3]))
        elif t[0] == "T" and verbeux:
            say(f"      {cle(K, L, shift, jumeau):>12}  t={int(t[1]):6d}  log2 BF {float(t[2]):12.1f} "
                f"(max {float(t[3]):6.2f} @ {t[4]})")
        elif t[0] == "FIN":
            fin = dict(nseq=int(t[1]), Pi=int(t[2]), N=int(float(t[3])), nt=int(t[4]), lb=float(t[5]),
                       gmax=float(t[6]), tmax=int(t[7]), bmax=int(t[8]), ncum=int(t[9]),
                       gcummax=float(t[10]), nmort=int(t[11]), nred=int(t[12]), sec=float(t[13]))
    if p.wait() != 0 or fin is None:
        raise RuntimeError(f"outil C : FIN {fin}")
    return fin, pic


def planter(K, L, shift, T, graine, jumeau_vrai):
    """LFG 32 bits lu au rejet ; si jumeau_vrai, un tirage du meme jeu est intercale."""
    rng = np.random.default_rng(graine)
    gen = H.LFG32(K, L, rng, shift)
    out = []
    for _ in range(T):
        A, _ = H.tirage_rejet(gen)
        out.append(ac_de(A))
        if jumeau_vrai:
            H.tirage_rejet(gen)
    return out


if __name__ == "__main__" and "--selftest" in sys.argv:
    say("h149 selftest (données synthétiques)")
    assert os.path.exists(OUTIL)
    T = int(sys.argv[sys.argv.index("--T") + 1]) if "--T" in sys.argv else 150
    K, L = (1, 15) if "--gros" in sys.argv else (2, 11)
    res = {}
    for jv in (0, 1):
        ecrire("/tmp/h149_self.txt", planter(K, L, 0, T, 1490 + jv, jv))
        for jl in (0, 1):
            fin, pic = lancer(K, L, 0, jl, "/tmp/h149_self.txt", "/tmp/h149_self.txt.b", nice=5,
                              fils=2)
            res[(jv, jl)] = fin["gmax"]
            say(f"   planté jumeau={jv}, lu jumeau={jl} : max log2 BF = {fin['gmax']:9.2f} @ "
                f"{fin['tmax']} ; pic {pic[0]},{pic[1]} masse {pic[2]:.3f} ; {fin['sec']:.0f} s")
    rng = np.random.default_rng(77)
    ecrire("/tmp/h149_self.txt", [ac_de(sorted(int(v) + 1 for v in rng.choice(POOL, DRAWN, replace=False)))
                                  for _ in range(T)])
    for jl in (0, 1):
        fin, _ = lancer(K, L, 0, jl, "/tmp/h149_self.txt", "/tmp/h149_self.txt.b", nice=5, fils=2)
        res[("nul", jl)] = fin["gmax"]
        say(f"   tirages nuls, lu jumeau={jl} : max log2 BF = {fin['gmax']:.2f}")
    assert res[(0, 0)] > SEUIL_FLUX and res[(1, 1)] > SEUIL_FLUX, res
    assert res[(0, 1)] < SEUIL_FLUX and res[(1, 0)] < SEUIL_FLUX, res
    assert res[("nul", 0)] < SEUIL_FLUX and res[("nul", 1)] < SEUIL_FLUX, res
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
    say(f"h149 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL)
    G = grille()
    NCONF = len(G)
    HYPOTHESE = (
        "Le flux continu de l'archive triee (70 560 tirages) n'est engendre par aucun Fibonacci "
        "retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur a rejet "
        "(v = 1 + (x mod 80)) au CANAL MOD 4 — c'est-a-dire en lisant les DEUX bits bas de chaque "
        f"mot que le numero publie revele —, pour les {len(TRIN0)} trinomes primitifs de degre "
        f"<= {LMAX0} a la sortie brute (etat : orbites du Fibonacci mod 4, N = (2^L-1)2^L) et les "
        f"{len(TRIN1)} de degre <= {LMAX1} a la sortie decalee x = r >> 1 (orbites mod 8), NI "
        "SEUL NI AVEC UN JUMEAU ENTRELACE (le meme generateur servant un autre tirage du meme jeu "
        "entre deux des notres : noyau convole par P0(n'), §7.21). Vraisemblance exacte de fenetre "
        "prod_c F20(w_c, a_c) G20 (normalisation verifiee a 1e-9) ; DP en flot puis faisceau (§7.18)"
    )
    STATISTIQUE = (
        f"D = nombre de chaines DETECTEES parmi {NCONF} (chaque configuration en deux versions, "
        f"sans et avec jumeau) : maximum courant de log2 BF_t >= {SEUIL_FLUX:.2f} = log2(1e7) + "
        f"log2({RMAX})"
    )
    NULL = ("Ville : surmartingale positive de moyenne <= 1 (melange propre, elagage, redemarrages "
            f"melanges, denormaux) ; borne d'union E[D] <= {NCONF * 1e-7:.1e}")
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
        G = G[:2]

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    AC = np.stack([((NUM - 1) % 4 == c).sum(axis=1) for c in range(4)], axis=1)
    assert AC.shape == (NTOT, 4) and (AC.sum(axis=1) == DRAWN).all()
    F_AC = os.path.join(TMP, "h149_ac.txt")
    F_BLOCS = os.path.join(TMP, "h149_blocs.txt")
    open(F_AC, "w").write("\n".join(" ".join(map(str, r)) for r in AC.tolist()) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages ; a_c moyens {AC.mean(axis=0).round(3).tolist()} (H0 : 5) ; "
        f"grille : {NCONF} chaînes ; seuil {SEUIL_FLUX:.2f}")

    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, jumeau in G:
        k = cle(K, L, shift, jumeau)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, pic = lancer(K, L, shift, jumeau, F_AC, F_BLOCS, nice=10, pasj=20000, fils=4,
                          verbeux=True)
        assert fin["nt"] == NTOT, fin
        det = fin["gmax"] >= SEUIL_FLUX
        say(f"      FIN {k} : {fin['nseq']}x{fin['Pi']} = {fin['N']:,}  max log2 BF {fin['gmax']:.2f} "
            f"@ {fin['tmax']} (seuil {SEUIL_FLUX:.2f}) ; {fin['nred']} redémarrages ; "
            f"{fin['nmort']} morts ; pic {pic[0]},{pic[1]} masse {pic[2]:.3f} ; {fin['sec']:.0f} s"
            + ("   !! DETECTION" if det else ""))
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
            TOK, float(D), p=1.0 if D == 0 else min(1.0, NCONF * 1e-7), verdict=verdict,
            power_at=("normalisation de la vraisemblance mod 4 verifiee a 1e-9 ; debit mesure 5,37 "
                      "bits par tirage (contre 1,31 pour la parite) ; plante sans jumeau detecte "
                      "(561 bits en 150 tirages a N = 1,07e9) et rejete par le modele a jumeau ; "
                      "plante AVEC jumeau invisible sans le modele (1,4 bit) et detecte avec (527) ; meme tableau croise a la sortie decalee (etat mod 8, L = 5, 7, 9 : 756/742/627 sans jumeau, 707/530/590 avec, <= 3,4 aux modeles croises) ; "
                      "tirages nuls sous le seuil"),
            notes=(f"CANAL MOD 4 (§7.21) : {len(LIG)} chaines = ({len(TRIN0)} trinomes L <= {LMAX0} "
                   f"sortie brute + {len(TRIN1)} L <= {LMAX1} sortie decalee) x (sans, avec jumeau "
                   f"entrelace). D = {D}, max {MF[1]['gmax']:.2f} ({MF[0]}) contre {SEUIL_FLUX:.2f}. "
                   f"{SEC/3600:.2f} h. NON COUVERT : L > 15 (etat 2^{{2L}}), TYPE_3, deux jumeaux ou "
                   "plus (entropie 5,7 bits > 5,37)."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
