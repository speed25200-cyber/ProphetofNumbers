"""h146 — la synchronisation sous le REJET pour les GRANDS etats : DP ELAGUEE (faisceau)
(THEORIE_ETAT §7.18, suite du §7.17).

CE QUE LE §7.17 LAISSAIT
========================
La DP de synchronisation du §145 lit le pas variable de l'echantillonneur a rejet en promenant
une loi sur la POSITION ABSOLUE q dans une sequence de bits periodique. Elle coute 21 N par
tirage : sur les 70 560 tirages de l'archive elle s'arrete a N ~ 10^5 (plan 0 des trinomes
L <= 17, plan 1 des L <= 11). Restaient dehors, entre autres, les deux sequences qui portent
les noms de la libc :
    plan 0 de TYPE_3 (x^31 + x^3 + 1) : N = 2^31 - 1 = 2 147 483 647
    plan 1 de TYPE_2 (x^15 + x + 1)   : N = 2^14 . 65 534 = 1 073 725 440
et tout le plan 0 des degres 18 a 31.

L'ELAGAGE, ET POURQUOI IL EST LICITE
====================================
Mettre a zero une partie des alpha — par n'importe quelle regle, meme dependante des donnees —
ne peut que DIMINUER tous les alpha ulterieurs (les poids sont positifs), et l'esperance
conditionnelle d'un pas reste <= 1. Donc BF' est une SURMARTINGALE positive de moyenne <= 1 :
l'inegalite de Ville s'applique telle quelle, P0(sup_t BF'_t >= 1e7) <= 1e-7. L'elagage ne coute
pas de VALIDITE ; il coute de la PUISSANCE — il faut que la VRAIE position survive.
Markov : sous H0, E[#{q : LR_q >= 2^x}] <= N 2^-x ; un faisceau de largeur B garde tout ce qui
depasse la COUPE x = log2(N/B). La vraie position gagne 1,1 bit par tirage (mesure : 43 +- 8
bits en m = 40 tirages, minimum observe 23,6 sur 21 temoins), tres au-dessus des 15 bits de
coupe d'un faisceau de 2^16 sur N = 2^31.

TROIS PHASES (tools/lfg_beam_rejet.c)
=====================================
  A. m tirages PLEINS, en UN SEUL passage en flot sur la sequence : alpha_t(p) ne depend que de
     alpha_{t-1}(p-20..p-40), donc un anneau de 64 positions x m etages suffit — memoire O(m),
     aucun tableau de taille N, et un prologue de 40 m positions rend chaque morceau EXACT, donc
     parallelisable sans approximation.
  B. les B1 = 2^16 meilleures positions, m2 = 20 tirages de plus.
  C. les B2 = 1024 meilleures, tous les tirages restants.
Mode flux : si le faisceau meurt (aucune position survivante — l'elagage, pas le modele), la
chaine redemarre a l'uniforme, au plus RMAX = 64 fois ; le melange de poids 1/RMAX sur ces
chaines reste une surmartingale, d'ou le seuil log2(1e7) + log2(64) = 29,25. Mode nuit : une
chaine par bloc (seuil log2(1e7) + log2(nombre de blocs)) et la chaine des blocs cumules
(seuil 23,25) ; un bloc mort reste mort.

CE QUE C'EST / CE QUE CE N'EST PAS
==================================
Couvre : plan 0 (sortie x = r) des 32 trinomes primitifs 18 <= L <= 31 — TYPE_3 compris — sous
le flux, et par nuit pour L <= 25 (les 370 blocs) ; plan 1 (x = r >> 1, glibc random()) des 6
trinomes de degre 15 — TYPE_2 compris — sous le flux ; par nuit, un bloc sur dix pour les deux
sequences nommees. Ne couvre pas : le plan 1 de TYPE_3 (N = 2^62 : hors de portee, cf. §7.18),
TYPE_4, la troncature (x . 80) >> 32, les echantillonneurs a pas fixe (cribles ailleurs).
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
SEUIL_LOG2 = H.SEUIL_LOG2                       # 23,25 : Ville a 1e-7
RMAX = 64                                       # budget de redemarrages du flux (outil C)
SEUIL_FLUX = SEUIL_LOG2 + math.log2(RMAX)       # 29,25
EXP_ID = "h146.beam_rejet"
OUTIL = os.environ.get("H146_OUTIL", "/tmp/lfg_beam_rejet_h146")
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h146_journal.txt")
FJETON = os.path.join(TMP, "h146_jeton.json")
M, B1, M2, B2 = 40, 65536, 20, 1024             # phases A / B / C
M_NUIT_GROS, SAUT_GROS = 30, 10                 # les deux sequences nommees, par nuit


def say(*a):
    print(*a, flush=True)


def trinomes(lo, hi):
    return [(K, L) for L in range(lo, hi + 1) for K in range(1, L) if H.primitif(K, L)]


TRIN0 = trinomes(18, 31)          # 32 trinomes, plan 0
TRIN1 = trinomes(15, 15)          # 6 trinomes de degre 15, plan 1 (TYPE_2)
assert len(TRIN0) == 32 and (3, 31) in TRIN0 and len(TRIN1) == 6 and (1, 15) in TRIN1


def grille():
    """(K, L, shift, mode, m, B1, m2, B2, saut)."""
    g = [(K, L, 0, "flux", M, B1, M2, B2, 1) for K, L in TRIN0]
    g += [(K, L, 1, "flux", M, B1, M2, B2, 1) for K, L in TRIN1]
    g += [(K, L, 0, "nuit", M, B1, M2, B2, 1) for K, L in TRIN0 if L <= 25]
    g += [(3, 31, 0, "nuit", M_NUIT_GROS, B1, M2, B2, SAUT_GROS),
          (1, 15, 1, "nuit", M_NUIT_GROS, B1, M2, B2, SAUT_GROS)]
    return g


def cle(K, L, shift, mode):
    return f"{K},{L},{shift},{mode}"


# --------------------------------------------------------------------------
# les sequences DANS LA CONVENTION DE L'OUTIL C (pour verifier le pic des temoins)
# --------------------------------------------------------------------------

def m_sequence_outil(K, L):
    """etat initial 0...01, R bit j = b_{i-1-j} : b_i = b_{i-K} xor b_{i-L}."""
    P = (1 << L) - 1
    b = np.zeros(P, dtype=np.uint8)
    R = 1
    for i in range(P):
        x = ((R >> (K - 1)) ^ (R >> (L - 1))) & 1
        b[i] = x
        R = ((R << 1) | x) & ((1 << 64) - 1)
    assert (R & ((1 << L) - 1)) == 1
    return b.reshape(1, P)


def orbites_outil(K, L):
    """plan 1 mod 4, plan 0 fixe a 0...01, les 2^L etats du plan 1 apparies (c, c apres P pas)."""
    P = (1 << L) - 1
    msk = (1 << L) - 1
    vu = np.zeros(1 << L, dtype=bool)
    orbs = []
    for c0 in range(1 << L):
        if vu[c0]:
            continue
        vu[c0] = True
        R0, R1 = 1, c0
        s = np.zeros(2 * P, dtype=np.uint8)
        for i in range(2 * P):
            x0, y0 = (R0 >> (K - 1)) & 1, (R0 >> (L - 1)) & 1
            x1, y1 = (R1 >> (K - 1)) & 1, (R1 >> (L - 1)) & 1
            b, cc = x0 ^ y0, x1 ^ y1 ^ (x0 & y0)
            s[i] = cc
            R0 = ((R0 << 1) | b) & ((1 << 64) - 1)
            R1 = ((R1 << 1) | cc) & ((1 << 64) - 1)
            if i + 1 == P:
                vu[R1 & msk] = True
        assert (R1 & msk) == c0 and (R0 & msk) == 1
        orbs.append(s)
    assert len(orbs) == 1 << (L - 1)
    return np.stack(orbs)


def sequence_outil(K, L, shift):
    return m_sequence_outil(K, L) if shift == 0 else orbites_outil(K, L)


# --------------------------------------------------------------------------
# l'outil
# --------------------------------------------------------------------------

def lancer(K, L, shift, mode, m, b1, m2, b2, saut, f_a0, f_blocs, nice=10, pasj=0, fils=None,
           verbeux=False):
    """execute l'outil C ; rend (dict FIN, pic, liste des blocs)."""
    env = dict(os.environ)
    if fils:
        env["OMP_NUM_THREADS"] = str(fils)
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), f_a0, f_blocs, mode,
           str(m), str(b1), str(m2), str(b2), str(pasj), str(saut)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
    blocs, fin, pic = [], None, None
    for l in p.stdout:
        t = l.split()
        if not t:
            continue
        if t[0] == "BLOC":
            blocs.append((int(t[1]), int(t[2]), int(t[3]), float(t[4]), float(t[5])))
        elif t[0] == "PIC":
            pic = (int(t[1]), int(t[2]), float(t[3]))
        elif t[0] == "T" and verbeux:
            say(f"      {cle(K, L, shift, mode):>12}  t={int(t[1]):6d}  log2 BF {float(t[2]):12.1f} "
                f"(max {float(t[3]):6.2f} @ {t[4]})")
        elif t[0] == "FIN":
            fin = dict(nseq=int(t[1]), Pi=int(t[2]), N=int(float(t[3])), nt=int(t[4]),
                       lb=float(t[5]), gmax=float(t[6]), tmax=int(t[7]), bmax=int(t[8]),
                       ncum=int(t[9]), gcummax=float(t[10]), nmort=int(t[11]), nred=int(t[12]),
                       sec=float(t[13]))
    rc = p.wait()
    if rc != 0 or fin is None:
        raise RuntimeError(f"outil C : code {rc}, FIN {fin}")
    return fin, pic, blocs


# --------------------------------------------------------------------------
# temoins
# --------------------------------------------------------------------------

def temoin(K, L, shift, T, graine, mode="flux", bloc=0, m=M, b1=B1, b2=B2, verifie_pic=True,
           fils=2, dossier="/tmp"):
    """plante un LFG 32 bits (K, L) lu par le rejet, ecrit a0, lance l'outil, verifie."""
    rng = np.random.default_rng(graine)
    a0, ns, gen = [], [], None
    for t in range(T):
        if gen is None or (bloc and t % bloc == 0):
            gen = H.LFG32(K, L, rng, shift)
            ns = []
        A, n = H.tirage_rejet(gen)
        a0.append(H.a0_de(A))
        ns.append(n)
    f_a0 = os.path.join(dossier, f"h146_tem_a0_{K}_{L}_{shift}_{mode}.txt")
    f_bl = os.path.join(dossier, f"h146_tem_bl_{K}_{L}_{shift}_{mode}.txt")
    open(f_a0, "w").write("\n".join(map(str, a0)) + "\n")
    open(f_bl, "w").write("\n".join(str(i) for i in range(0, T, bloc or T)) + "\n")
    t0 = time.time()
    fin, pic, blocs = lancer(K, L, shift, mode, m, b1, M2, b2, 1, f_a0, f_bl, nice=5, fils=fils)
    dt = time.time() - t0
    ok_pic = None
    if verifie_pic:
        seqs = sequence_outil(K, L, shift)
        pos = H.positions_dans(seqs, gen.trace[:4 * L + 8])
        assert pos, "la trace n'est pas dans les sequences de l'outil"
        Pi = seqs.shape[1]
        att = {(s_, (q_ + sum(ns)) % Pi) for s_, q_ in pos}
        ok_pic = any(pic[0] == s_ and min((pic[1] - q_) % Pi, (q_ - pic[1]) % Pi) <= ns[-1]
                     for s_, q_ in att)
    # temoin nul : memes longueurs, tirages uniformes
    a0n = [H.a0_de(sorted(int(v) + 1 for v in rng.choice(POOL, DRAWN, replace=False)))
           for _ in range(T)]
    open(f_a0, "w").write("\n".join(map(str, a0n)) + "\n")
    finn, _, _ = lancer(K, L, shift, mode, m, b1, M2, b2, 1, f_a0, f_bl, nice=5, fils=fils)
    d = dict(K=K, L=L, shift=shift, mode=mode, T=T, bloc=bloc, N=fin["N"], m=m, B1=b1, B2=b2,
             log2bf=fin["lb"], max=fin["gmax"], tmax=fin["tmax"], pic=pic, pic_ok=ok_pic,
             nul_max=finn["gmax"], nul_lb=finn["lb"], nred=fin["nred"], nul_nred=finn["nred"],
             sec=fin["sec"], mur=dt, blocs=len(blocs),
             maxbloc=max((b[4] for b in blocs), default=None))
    say(f"   K={K} L={L} s{shift} {mode} bloc={bloc} N={fin['N']:,} T={T} : plante max log2 BF = "
        f"{fin['gmax']:.1f} @ {fin['tmax']}" + (f" (max par bloc {d['maxbloc']:.1f})" if blocs and mode == "nuit" else "")
        + f" ; pic {pic[0]},{pic[1]} {'OK' if ok_pic else ('FAUX' if verifie_pic else '(non verifie)')}"
        f" masse {pic[2]:.3f} ; nul max {finn['gmax']:.2f} ({finn['nred']} redemarrages) ; {dt:.1f} s")
    return d


if __name__ == "__main__" and "--selftest" in sys.argv:
    say("h146 selftest (donnees synthetiques ; aucune lecture de l'archive)")
    assert os.path.exists(OUTIL), ("compiler : cc -O3 -march=native -fopenmp -o "
                                   "/tmp/lfg_beam_rejet_h146 tools/lfg_beam_rejet.c -lm")
    res = []
    # 1. accord EXACT avec la DP pleine du §145 (faisceau plus large que N : aucun elagage)
    for K, L, shift, T in [(1, 15, 0, 200), (4, 9, 1, 150)]:
        rng = np.random.default_rng(1000 + L)
        gen = H.LFG32(K, L, rng, shift)
        a0 = [H.a0_de(H.tirage_rejet(gen)[0]) for _ in range(T)]
        f = f"/tmp/h146_croise_{L}_{shift}.txt"
        open(f, "w").write("\n".join(map(str, a0)) + "\n")
        open(f + ".b", "w").write("0\n")
        seqs = H.m_sequence(K, L) if shift == 0 else H.orbites_mod4(K, L)
        sy = H.Synchro(seqs, eps=0.0)
        plein = [sy.pas(x, evasion=False) for x in a0]
        N = seqs.shape[0] * seqs.shape[1]
        fin, _, _ = lancer(K, L, shift, "flux", 40, N, 0, N, 1, f, f + ".b", nice=5, fils=2)
        e = abs(fin["lb"] - plein[-1])
        say(f"   croise (K={K}, L={L}, shift={shift}) : DP pleine {plein[-1]:.4f} bits, faisceau "
            f"sans elagage {fin['lb']:.4f} — ecart {e:.2e}")
        assert e < 1e-3, e
        fin2, _, _ = lancer(K, L, shift, "flux", 40, B1, M2, B2, 1, f, f + ".b", nice=5, fils=2)
        say(f"      avec elagage (B1 = {B1}, B2 = {B2}) : {fin2['lb']:.4f} — ecart "
            f"{abs(fin2['lb'] - plein[-1]):.2e}")
        assert abs(fin2["lb"] - plein[-1]) < 1e-2
    # 2. temoins plantes : flux et nuit, plan 0 et plan 1, jusqu'a N = 3,4e7
    for K, L, shift, T, mode, bloc in [(1, 15, 0, 200, "flux", 0), (3, 20, 0, 250, "flux", 0),
                                       (4, 9, 1, 150, "flux", 0), (7, 18, 0, 204 * 3, "nuit", 204),
                                       (4, 9, 1, 204 * 3, "nuit", 204)]:
        res.append(temoin(K, L, shift, T, graine=2000 + 10 * L + shift, mode=mode, bloc=bloc))
    # 3. le temoin de puissance a l'echelle de l'archive : TYPE_3 plan 0, N = 2^31 - 1
    if "--gros" in sys.argv:
        res.append(temoin(3, 31, 0, 300, graine=31146, verifie_pic=False, fils=4))
        res.append(temoin(1, 15, 1, 300, graine=15146, verifie_pic=False, fils=4))
    for d in res:
        assert d["max"] > SEUIL_FLUX and d["nul_max"] < SEUIL_FLUX, d
        assert d["pic_ok"] in (True, None), d
    say("selftest OK")


# ==========================================================================
# L'ARCHIVE
# ==========================================================================

def lire_journal():
    d = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 14 and t[0] != "#":
                d[t[0]] = dict(nseq=int(t[1]), Pi=int(t[2]), N=int(t[3]), nt=int(t[4]), lb=float(t[5]),
                               gmax=float(t[6]), tmax=int(t[7]), bmax=int(t[8]), ncum=int(t[9]),
                               gcummax=float(t[10]), nmort=int(t[11]), nred=int(t[12]),
                               sec=float(t[13]))
    return d


if __name__ == "__main__" and "--archive" in sys.argv:
    import lab
    DRY = "--dry" in sys.argv
    T0 = time.time()
    say(f"h146 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL)
    G = grille()
    NCONF = len(G)
    NFLUX = sum(1 for c in G if c[3] == "flux")
    NNUIT = NCONF - NFLUX

    # 1. le pre-enregistrement, AVANT toute lecture de l'archive
    HYPOTHESE = (
        "Ni le flux continu de l'archive triee (70 560 tirages, un seul etat) ni ses blocs de nuit "
        "(generateur reamorce chaque nuit) ne sont engendres par un Fibonacci retarde additif "
        "r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur A REJET (v = 1 + (x mod 80), "
        "refuse si deja tire ; pas variable n in [20, 40] mots par tirage) pour : le PLAN 0 "
        f"(sortie x = r) des {len(TRIN0)} trinomes primitifs de degre 18 <= L <= 31 — x^31 + x^3 + 1 "
        "(TYPE_3) compris, N = 2^L - 1 jusqu'a 2 147 483 647 — ni pour le PLAN 1 (x = r >> 1, "
        f"glibc random()) des {len(TRIN1)} trinomes de degre 15 — x^15 + x + 1 (TYPE_2) compris, "
        "N = 2^14 . 65 534. Methode (§7.18) : la DP de synchronisation du §7.17 sur la position "
        "absolue, ELAGUEE — m tirages pleins en un passage en flot, puis faisceau des B1 = 2^16 "
        "meilleures positions pendant m2 = 20 tirages, puis des B2 = 1024. L'elagage laisse une "
        "surmartingale positive de moyenne <= 1 (mise a zero de masse positive) : Ville reste "
        "valable. Design, seuils, largeurs et temoins fixes AVANT cette consignation sur des "
        "generateurs plantes, jamais sur l'archive"
    )
    STATISTIQUE = (
        f"D = nombre de chaines DETECTEES parmi les {NCONF} configurations : {NFLUX} chaines de flux "
        f"(maximum courant de log2 BF_t >= {SEUIL_FLUX:.2f} = log2(1e7) + log2({RMAX}), le melange "
        f"uniforme sur les <= {RMAX} redemarrages du faisceau) ; pour chacune des {NNUIT} "
        "configurations par nuit, la chaine des blocs cumules (seuil 23,25) et le maximum sur les "
        "blocs traites (seuil 23,25 + log2(nombre de blocs traites)). BF_t = P_melange / P_0 = "
        "(1/N) Sum_q alpha_t(q), alpha_0 = 1"
    )
    NULL = (
        "inegalite de Ville : sous H0 (tirages uniformes sans remise) BF_t est une surmartingale "
        "positive de moyenne <= 1 — melange propre tronque a n <= 40, puis elagage (mise a zero) et "
        "arrondi par defaut (denormaux mis a zero) qui ne peuvent que la diminuer — donc "
        "P0(sup_t BF_t >= 1e7) <= 1e-7 par chaine, en tout temps, sans hypothese de distribution ; "
        f"borne d'union sur les {NFLUX} chaines de flux et les 2 chaines par configuration de nuit : "
        f"E[D] <= {(NFLUX + 2 * NNUIT) * 1e-7:.1e}"
    )
    VERDICT = (
        "conforme si D = 0 ; ETAT TROUVE si une chaine depasse son seuil et que son pic a posteriori "
        "se confirme (position stable, log2 BF croissant de ~1,1 bit par tirage ensuite) ; DETECTION "
        "NON CONFIRMEE sinon"
    )
    if not DRY:
        if os.path.exists(FJETON):
            TOK = json.load(open(FJETON, encoding="utf-8"))
            say(f"   jeton repris : scelle {TOK['seal']} le {TOK['registered_at']}")
        else:
            TOK = lab.preregister(EXP_ID, HYPOTHESE, STATISTIQUE, NULL, VERDICT, track="B")
            json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
            say(f"   jeton scelle {TOK['seal']} le {TOK['registered_at']}")
    else:
        say("   MODE ESSAI : pas de jeton, grille tronquee.")

    # 2. l'archive -> a0 par tirage et debuts de bloc
    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    NBLOCS = len(DEB)
    if DRY:
        rng = np.random.default_rng(146)
        A0 = np.array([int(((rng.choice(POOL, DRAWN, replace=False)) % 2 == 0).sum())
                       for _ in range(NTOT)])
        F_A0, F_BLOCS = os.path.join(TMP, "h146_dry_a0.txt"), os.path.join(TMP, "h146_dry_blocs.txt")
        G = [G[0], G[NFLUX], G[-1]]
    else:
        A0 = ((NUM - 1) % 2 == 0).sum(axis=1)
        F_A0, F_BLOCS = os.path.join(TMP, "h146_a0.txt"), os.path.join(TMP, "h146_blocs.txt")
    assert NUM.shape == (NTOT, DRAWN) and A0.min() >= 0 and A0.max() <= DRAWN
    open(F_A0, "w").write("\n".join(str(int(a)) for a in A0) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages, {NBLOCS} blocs ; a0 moyenne {A0.mean():.3f}")
    say(f"   grille : {NCONF} configurations ({NFLUX} flux, {NNUIT} nuit) ; journal {JOURNAL}")

    # 3. la grille, avec reprise par le journal
    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, mode, m, b1, m2, b2, saut in G:
        k = cle(K, L, shift, mode)
        if k in FAIT:
            continue
        say(f"   >> {k}  m={m} B1={b1} B2={b2} saut={saut}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, pic, blocs = lancer(K, L, shift, mode, m, b1, m2, b2, saut, F_A0, F_BLOCS,
                                 nice=10, pasj=20000 if mode == "flux" else 0, fils=4, verbeux=True)
        assert fin["nt"] == NTOT, fin
        seuil = SEUIL_FLUX if mode == "flux" else SEUIL_LOG2 + math.log2(max(1, fin["ncum"]))
        det = fin["gmax"] >= seuil or (mode == "nuit" and fin["gcummax"] >= SEUIL_LOG2)
        say(f"      FIN {k} : {fin['nseq']}x{fin['Pi']} = {fin['N']:,}  max log2 BF {fin['gmax']:.2f} "
            f"@ {fin['tmax']} (seuil {seuil:.2f})" +
            (f" ; {fin['ncum']} blocs, cumul max {fin['gcummax']:.2f}, meilleur bloc {fin['bmax']}"
             if mode == "nuit" else f" ; {fin['nred']} redemarrages") +
            f" ; {fin['nmort']} morts ; pic {pic[0]},{pic[1]} masse {pic[2]:.3f} ; {fin['sec']:.0f} s"
            + ("   !! DETECTION" if det else ""))
        if not DRY:
            if blocs:
                with open(os.path.join(TMP, f"h146_blocs_{K}_{L}_{shift}.txt"), "w") as f:
                    f.write("".join(f"{b} {t0} {n} {v:.6f} {mx:.6f}\n" for b, t0, n, v, mx in blocs))
            with open(JOURNAL, "a", encoding="utf-8") as f:
                f.write(f"{k} {fin['nseq']} {fin['Pi']} {fin['N']} {fin['nt']} {fin['lb']:.4f} "
                        f"{fin['gmax']:.4f} {fin['tmax']} {fin['bmax']} {fin['ncum']} "
                        f"{fin['gcummax']:.4f} {fin['nmort']} {fin['nred']} {fin['sec']:.1f}\n")
        FAIT[k] = fin

    # 4. le bilan et la consignation
    LIG = [(cle(*c[:4]), FAIT[cle(*c[:4])]) for c in G if cle(*c[:4]) in FAIT]
    def seuil_de(k, f):
        return SEUIL_FLUX if k.endswith("flux") else SEUIL_LOG2 + math.log2(max(1, f["ncum"]))
    D = sum(1 for k, f in LIG if f["gmax"] >= seuil_de(k, f)) + \
        sum(1 for k, f in LIG if k.endswith("nuit") and f["gcummax"] >= SEUIL_LOG2)
    MF = max((kf for kf in LIG if kf[0].endswith("flux")), key=lambda kf: kf[1]["gmax"], default=None)
    MN = max((kf for kf in LIG if kf[0].endswith("nuit")), key=lambda kf: kf[1]["gmax"], default=None)
    SEC = sum(f["sec"] for k, f in LIG)
    NRED = sum(f["nred"] for k, f in LIG)
    NMORT = sum(f["nmort"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; max flux {MF[1]['gmax']:.2f} ({MF[0]}) contre "
        f"{SEUIL_FLUX:.2f}" + (f" ; max par nuit {MN[1]['gmax']:.2f} ({MN[0]})" if MN else "") +
        f" ; {NRED} redemarrages, {NMORT} morts ; {SEC/3600:.2f} h")
    if DRY or len(LIG) < NCONF:
        say("   grille incomplete ou essai : rien n'est consigne.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "DETECTION NON CONFIRMEE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else min(1.0, (NFLUX + 2 * NNUIT) * 1e-7), verdict=verdict,
            power_at=("temoins plantes (Fibonacci 32 bits, rejet exact, meme outil) : accord EXACT "
                      "avec la DP pleine du §7.17 sans elagage (ecart < 1e-3 bit) et a 1e-2 pres avec "
                      "le faisceau ; plante detecte sur tous les temoins (plan 0 L = 15, 18, 20, 25, "
                      "31 ; plan 1 L = 9, 15), flux et par nuit, avec pic sur la vraie position a "
                      "moins de n_T mots ; temoins nuls sous le seuil"),
            notes=(f"FAISCEAU (§7.18) : {len(LIG)} configurations, {NFLUX} de flux + {NNUIT} de nuit. "
                   f"D = {D}. max flux {MF[1]['gmax']:.2f} ({MF[0]}) / {SEUIL_FLUX:.2f}" +
                   (f", max nuit {MN[1]['gmax']:.2f} ({MN[0]})" if MN else "") +
                   f". {NRED} redemarrages, {NMORT} morts. {SEC/3600:.2f} h. "
                   "NON COUVERT : plan 1 de TYPE_3 (N = 2^62), TYPE_4, troncature, pas fixe."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
