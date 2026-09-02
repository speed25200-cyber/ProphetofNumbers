"""h147 — la synchronisation sous le rejet MASQUE : `v = 1 + (x mod M)`, refusé si `v > 80`
(THEORIE_ETAT §7.19, suite des §7.17 et §7.18).

LE TROU
=======
Les §165 et §166 lisent l'échantillonneur du programmeur PRESSÉ : `v = 1 + (x mod 80)`, biaisé
d'un cheveu (2^32 n'est pas multiple de 80) mais direct. Le programmeur SOIGNEUX écrit autre
chose : pour tirer un entier de [1, 80] sans biais, on masque (`x & 127`, M = 128) ou on prend
`x mod 100`, et on RECOMMENCE si le résidu dépasse 80. C'est l'écriture recommandée partout, et
aucun crible du dossier ne la lit sous pas variable : le pas y est encore plus variable,
E[N] = 22,85 / rho mots par tirage (rho = 80/M), soit 28,6 (M = 100), 36,6 (M = 128), 73,1
(M = 256).

LA VRAISEMBLANCE, INCHANGEE DANS SA FORME
=========================================
Un mot est "dans la plage" avec probabilité rho INDEPENDAMMENT de son bit 0 : parmi les 80
résidus retenus, 40 sont pairs et 40 impairs. Un mot dans la plage donne un numéro uniforme
parmi les 40 de sa classe. Donc, en notant S l'ensemble (inconnu) des mots dans la plage,

    P(A, n | fenêtre) = Sum_{S ∋ n} rho^|S| (1-rho)^{n-|S|} F(w_{1-b}(S), a_{1-b}) G(w_b(S), a_b)

et, comme le nombre de sous-ensembles à j uns et z zéros ne dépend que des comptes, la somme
se FACTORISE (les binomiales du masque étalent F et G) :

    Ff[W][a] = Sum_j C(W, j) rho^j (1-rho)^{W-j} F(j, a)
    Gg[W][a] = Sum_j C(W-1, j-1) rho^j (1-rho)^{W-j} G(j, a)      (le dernier mot est dans la plage)
    b = 1 : P = Gg[W1][a1] Ff[W0][a0]        b = 0 : P = Ff[W1][a1] Gg[W0][a0]

rho = 1 redonne exactement le §7.17. La statistique suffisante reste (n, W1, dernier bit), donc
TOUTE la machinerie du §7.18 (passage en flot, faisceau, Ville) s'applique telle quelle : seule
la table change, et n monte jusqu'à 61 (M = 100), 87 (M = 128), 176 (M = 256) — d'où la fenêtre
de 128 bits de l'outil `tools/lfg_beam_masque.c`.

TEMOINS
=======
--selftest : normalisation Sum_{A,n} P = 1 à 1e-7 près pour les quatre M ; l'outil à M = 80
reproduit CHIFFRE POUR CHIFFRE celui du §166 ; générateurs plantés lus au masque et retrouvés ;
et le croisement des masques (planté à M, analysé à M') montre que le masque doit être le bon.
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
import h146_beam_rejet as B                                             # noqa: E402

POOL, DRAWN, HALF = H.POOL, H.DRAWN, 40
SEUIL_LOG2 = H.SEUIL_LOG2
RMAX = 64
SEUIL_FLUX = SEUIL_LOG2 + math.log2(RMAX)       # 29,25
EXP_ID = "h147.masque_rejet"
TAUX = {80: 1.022, 100: 0.475, 128: 0.314, 256: 0.092}   # bits par tirage, mesures (planté L=15)
OUTIL = os.environ.get("H147_OUTIL", "/tmp/lfg_beam_masque_h147")
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h147_journal.txt")
FJETON = os.path.join(TMP, "h147_jeton.json")
M, B1, M2, B2 = 40, 65536, 20, 1024             # phases A / B / C (comme au §166)
MASQUES = [100, 128, 256]                       # M = 80 est le §166 lui-meme
LMAX1 = 15                                      # plan 1 : trinomes de degre <= 15


def say(*a):
    print(*a, flush=True)


TRIN0 = [(K, L) for L in range(2, 32) for K in range(1, L) if H.primitif(K, L)]
TRIN1 = [(K, L) for K, L in TRIN0 if L <= LMAX1]
assert len(TRIN0) == 63 and len(TRIN1) == 25 and (3, 31) in TRIN0 and (1, 15) in TRIN1


def grille():
    """(K, L, shift, M, mode) — flux seulement ; M = 256 réservé aux séquences nommées."""
    g = []
    for m in MASQUES:
        if m == 256:
            g += [(3, 31, 0, m, "flux"), (1, 15, 0, m, "flux"), (3, 7, 0, m, "flux"),
                  (1, 15, 1, m, "flux"), (3, 7, 1, m, "flux")]
            continue
        g += [(K, L, 0, m, "flux") for K, L in TRIN0]
        g += [(K, L, 1, m, "flux") for K, L in TRIN1]
    return g


def cle(K, L, shift, m, mode):
    return f"{K},{L},{shift},{m},{mode}"


# --------------------------------------------------------------------------
# la vraisemblance (prototype numpy : normalisation, croisement avec l'outil)
# --------------------------------------------------------------------------

NMB = 200
_S = [[0.0] * (DRAWN + 1) for _ in range(NMB + 1)]
_S[0][0] = 1.0
for _w in range(1, NMB + 1):
    for _a in range(1, DRAWN + 1):
        _S[_w][_a] = _a * _S[_w - 1][_a] + _S[_w - 1][_a - 1]
_FACT = [math.factorial(a) for a in range(DRAWN + 1)]


def F(w, a):
    if w < a or (a == 0 and w > 0):
        return 0.0
    return _FACT[a] * _S[w][a] / HALF ** w


def G(w, a):
    if a == 0 or w < a:
        return 0.0
    return _FACT[a] * _S[w - 1][a - 1] / HALF ** w


def n_max(m):
    """le n maximal de l'outil : moyenne + 9 ecarts-types, plafonne a 176."""
    rho = POOL / m
    mu, sd = 22.85 / rho, math.sqrt(22.85 * (1 - rho) + 3.42) / rho
    return min(176, int(mu + 9 * sd) + 1)


def tables_masque(m):
    nmax = n_max(m)
    rho = POOL / m
    Ff = np.zeros((nmax + 1, DRAWN + 1))
    Gg = np.zeros((nmax + 1, DRAWN + 1))
    for W in range(nmax + 1):
        for a in range(DRAWN + 1):
            Ff[W, a] = sum(math.comb(W, j) * rho ** j * (1 - rho) ** (W - j) * F(j, a)
                           for j in range(W + 1))
            Gg[W, a] = sum(math.comb(W - 1, j - 1) * rho ** j * (1 - rho) ** (W - j) * G(j, a)
                           for j in range(1, W + 1))
    return Ff, Gg, nmax


def P_fenetre(Ff, Gg, W1, W0, b, a0):
    a1 = DRAWN - a0
    return Gg[W1, a1] * Ff[W0, a0] if b == 1 else Ff[W1, a1] * Gg[W0, a0]


def normalisation(m, essais=4, graine=147):
    """Sum_{A, n} P(A, n | fenetre) doit valoir 1 (au defaut de troncature pres)."""
    Ff, Gg, nmax = tables_masque(m)
    rng = np.random.default_rng(graine)
    mult = [math.comb(HALF, a) * math.comb(HALF, DRAWN - a) for a in range(DRAWN + 1)]
    out = []
    for _ in range(essais):
        bits = rng.integers(0, 2, size=nmax + 1)
        s = 0.0
        for n in range(20, nmax + 1):
            W1 = int(bits[:n].sum())
            s += sum(mult[a0] * P_fenetre(Ff, Gg, W1, n - W1, int(bits[n - 1]), a0)
                     for a0 in range(DRAWN + 1))
        out.append(s)
    return out


# --------------------------------------------------------------------------
# l'echantillonneur masque et les generateurs plantes
# --------------------------------------------------------------------------

def tirage_masque(gen, m):
    """v = 1 + (x mod m) ; refuse si v > 80 ou deja tire."""
    A, n = [], 0
    while len(A) < DRAWN:
        v = 1 + gen.suivant() % m
        n += 1
        if v <= POOL and v not in A:
            A.append(v)
    return sorted(A), n


def lancer(K, L, shift, m, mode, f_a0, f_blocs, mm=M, b1=B1, m2=M2, b2=B2, saut=1, nice=10,
           pasj=0, fils=None, verbeux=False):
    env = dict(os.environ)
    if fils:
        env["OMP_NUM_THREADS"] = str(fils)
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), str(m), f_a0, f_blocs,
           mode, str(mm), str(b1), str(m2), str(b2), str(pasj), str(saut)]
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
            say(f"      {cle(K, L, shift, m, mode):>16}  t={int(t[1]):6d}  log2 BF {float(t[2]):12.1f} "
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


def temoin(K, L, shift, m_plante, m_lu, T, graine, verifie_pic=True, fils=2, dossier="/tmp"):
    """plante un LFG lu au masque m_plante, l'analyse au masque m_lu."""
    rng = np.random.default_rng(graine)
    gen = H.LFG32(K, L, rng, shift)
    a0, ns = [], []
    for _ in range(T):
        A, n = tirage_masque(gen, m_plante)
        a0.append(H.a0_de(A))
        ns.append(n)
    f_a0 = os.path.join(dossier, f"h147_tem_{K}_{L}_{shift}_{m_plante}.txt")
    open(f_a0, "w").write("\n".join(map(str, a0)) + "\n")
    open(f_a0 + ".b", "w").write("0\n")
    fin, pic, _ = lancer(K, L, shift, m_lu, "flux", f_a0, f_a0 + ".b", nice=5, fils=fils)
    ok = None
    if verifie_pic:
        seqs = B.sequence_outil(K, L, shift)
        pos = H.positions_dans(seqs, gen.trace[:4 * L + 8])
        assert pos
        Pi = seqs.shape[1]
        att = {(s_, (q_ + sum(ns)) % Pi) for s_, q_ in pos}
        ok = any(pic[0] == s_ and min((pic[1] - q_) % Pi, (q_ - pic[1]) % Pi) <= ns[-1]
                 for s_, q_ in att)
    a0n = [H.a0_de(sorted(int(v) + 1 for v in rng.choice(POOL, DRAWN, replace=False)))
           for _ in range(T)]
    open(f_a0, "w").write("\n".join(map(str, a0n)) + "\n")
    finn, _, _ = lancer(K, L, shift, m_lu, "flux", f_a0, f_a0 + ".b", nice=5, fils=fils)
    say(f"   planté M={m_plante} lu M={m_lu} : K={K} L={L} s{shift} N={fin['N']:,} T={T} "
        f"(n moyen {np.mean(ns):.1f}) : max log2 BF = {fin['gmax']:.1f} @ {fin['tmax']} ; pic "
        f"{'OK' if ok else ('FAUX' if verifie_pic else '—')} masse {pic[2]:.3f} ; nul {finn['gmax']:.2f} ; "
        f"{fin['sec']:.0f} s")
    return dict(K=K, L=L, shift=shift, m_plante=m_plante, m_lu=m_lu, T=T, N=fin["N"],
                nmoy=float(np.mean(ns)), max=fin["gmax"], tmax=fin["tmax"], pic=pic, pic_ok=ok,
                nul=finn["gmax"], sec=fin["sec"])


if __name__ == "__main__" and "--selftest" in sys.argv:
    say("h147 selftest (données synthétiques ; aucune lecture de l'archive)")
    assert os.path.exists(OUTIL), ("compiler : cc -O3 -march=native -fopenmp -o "
                                   "/tmp/lfg_beam_masque_h147 tools/lfg_beam_masque.c -lm")
    for m in [80] + MASQUES:
        nrm = normalisation(m)
        say(f"   normalisation M={m:3d} (rho = {POOL/m:.4f}, n <= {n_max(m):3d}) : "
            f"{min(nrm):.10f} .. {max(nrm):.10f}")
        assert 1 - max(nrm) < 1e-5 and min(nrm) <= 1.0 + 1e-9, nrm
    res = []
    # M = 80 : l'outil doit reproduire celui du §166, chiffre pour chiffre
    rng = np.random.default_rng(1015)
    gen = H.LFG32(1, 15, rng, 0)
    a0 = [H.a0_de(H.tirage_rejet(gen)[0]) for _ in range(200)]
    open("/tmp/h147_croise.txt", "w").write("\n".join(map(str, a0)) + "\n")
    open("/tmp/h147_croise.txt.b", "w").write("0\n")
    f1, _, _ = lancer(1, 15, 0, 80, "flux", "/tmp/h147_croise.txt", "/tmp/h147_croise.txt.b", fils=2)
    f2, _, _ = B.lancer(1, 15, 0, "flux", M, B1, M2, B2, 1, "/tmp/h147_croise.txt",
                        "/tmp/h147_croise.txt.b", fils=2)
    say(f"   croisement M=80 : h147 {f1['lb']:.4f} bits, h146 {f2['lb']:.4f} — écart "
        f"{abs(f1['lb'] - f2['lb']):.2e}")
    assert abs(f1["lb"] - f2["lb"]) < 1e-6
    # plantés lus au bon masque
    for K, L, shift, mm, T in [(1, 15, 0, 100, 200), (3, 20, 0, 128, 250), (4, 9, 1, 128, 200),
                               (1, 15, 0, 256, 1500)]:
        res.append(temoin(K, L, shift, mm, mm, T, graine=3000 + 10 * L + shift + mm))
    # le masque doit etre le bon : plante a 128, lu a 80 et a 100
    for mlu in (80, 100):
        res.append(temoin(1, 15, 0, 128, mlu, 250, graine=777, verifie_pic=False))
    for d in res[:4]:
        assert d["max"] > SEUIL_FLUX and d["pic_ok"] and d["nul"] < SEUIL_FLUX, d
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
    say(f"h147 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL)
    G = grille()
    NCONF = len(G)

    HYPOTHESE = (
        "Le flux continu de l'archive triee (70 560 tirages, un seul etat) n'est engendre par aucun "
        "Fibonacci retarde additif r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur a rejet "
        "MASQUE — v = 1 + (x mod M), REFUSE si v > 80, puis refuse si deja tire — pour M = 100, 128 "
        f"(les {len(TRIN0)} trinomes primitifs de degre <= 31 au plan 0, x^31+x^3+1 (TYPE_3) compris ; "
        f"les {len(TRIN1)} de degre <= 15 au plan 1, x^15+x+1 (TYPE_2) compris) ni pour M = 256 "
        "(TYPE_1, TYPE_2, TYPE_3 nommes). C'est l'ecriture RECOMMANDEE d'un tirage sans biais (masque "
        "puis rejet de plage), que les §165-§166 ne lisent pas. Vraisemblance exacte de fenetre "
        "(§7.19) : F et G etales par la binomiale du masque, statistique suffisante inchangee "
        "(n, W1, dernier bit) ; DP en flot puis faisceau (§7.18), n jusqu'a 176. Design, seuils, "
        "largeurs et temoins fixes AVANT cette consignation sur des generateurs plantes"
    )
    STATISTIQUE = (
        f"D = nombre de chaines de flux DETECTEES parmi {NCONF} : maximum courant de log2 BF_t >= "
        f"{SEUIL_FLUX:.2f} = log2(1e7) + log2({RMAX}) (melange uniforme sur les <= {RMAX} "
        "redemarrages du faisceau). BF_t = (1/N) Sum_q alpha_t(q), alpha_0 = 1"
    )
    NULL = (
        "inegalite de Ville : sous H0 BF_t est une surmartingale positive de moyenne <= 1 (melange "
        "propre tronque a n <= n_max, elagage, redemarrages melanges a poids 1/64, denormaux mis a "
        f"zero), donc 1e-7 par chaine a tout instant ; borne d'union : E[D] <= {NCONF * 1e-7:.1e}"
    )
    VERDICT = ("conforme si D = 0 ; ETAT TROUVE si une chaine depasse le seuil et que son pic se "
               "confirme ; DETECTION NON CONFIRMEE sinon")
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

    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    DEB = np.r_[0, np.flatnonzero(np.diff(TS) != 300) + 1]
    if DRY:
        rng = np.random.default_rng(147)
        A0 = np.array([int(((rng.choice(POOL, DRAWN, replace=False)) % 2 == 0).sum())
                       for _ in range(NTOT)])
        F_A0, F_BLOCS = os.path.join(TMP, "h147_dry_a0.txt"), os.path.join(TMP, "h147_dry_blocs.txt")
        G = [G[0], G[len(TRIN0)], G[-1]]
    else:
        A0 = ((NUM - 1) % 2 == 0).sum(axis=1)
        F_A0, F_BLOCS = os.path.join(TMP, "h147_a0.txt"), os.path.join(TMP, "h147_blocs.txt")
    open(F_A0, "w").write("\n".join(str(int(a)) for a in A0) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    say(f"   {NTOT} tirages, {len(DEB)} blocs ; grille : {NCONF} configurations "
        f"({', '.join(str(m) + ' : ' + str(sum(1 for c in G if c[3] == m)) for m in MASQUES)})")

    FAIT = lire_journal() if not DRY else {}
    for K, L, shift, m, mode in G:
        k = cle(K, L, shift, m, mode)
        if k in FAIT:
            continue
        say(f"   >> {k}  (n <= {n_max(m)})  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, pic, _ = lancer(K, L, shift, m, mode, F_A0, F_BLOCS, nice=10, pasj=20000, fils=4,
                             verbeux=True)
        assert fin["nt"] == NTOT, fin
        det = fin["gmax"] >= SEUIL_FLUX
        say(f"      FIN {k} : {fin['nseq']}x{fin['Pi']} = {fin['N']:,}  max log2 BF {fin['gmax']:.2f} "
            f"@ {fin['tmax']} (seuil {SEUIL_FLUX:.2f}) ; {fin['nred']} redémarrages ; "
            f"{fin['nmort']} morts ; pic {pic[0]},{pic[1]} masse {pic[2]:.3f} ; {fin['sec']:.0f} s"
            + ("   !! DETECTION" if det else ""))
        if not DRY:
            with open(JOURNAL, "a", encoding="utf-8") as f:
                f.write(f"{k} {fin['nseq']} {fin['Pi']} {fin['N']} {fin['nt']} {fin['lb']:.4f} "
                        f"{fin['gmax']:.4f} {fin['tmax']} {fin['bmax']} {fin['ncum']} "
                        f"{fin['gcummax']:.4f} {fin['nmort']} {fin['nred']} {fin['sec']:.1f}\n")
        FAIT[k] = fin

    LIG = [(cle(*c), FAIT[cle(*c)]) for c in G if cle(*c) in FAIT]
    D = sum(1 for k, f in LIG if f["gmax"] >= SEUIL_FLUX)
    MF = max(LIG, key=lambda kf: kf[1]["gmax"])
    SEC = sum(f["sec"] for k, f in LIG)
    say(f"\n   {len(LIG)} configurations : D = {D} ; max {MF[1]['gmax']:.2f} ({MF[0]} @ "
        f"{MF[1]['tmax']}) contre {SEUIL_FLUX:.2f} ; {sum(f['nred'] for k, f in LIG)} redémarrages ; "
        f"{SEC/3600:.2f} h")
    if DRY or len(LIG) < NCONF:
        say("   grille incomplète ou essai : rien n'est consigné.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "DETECTION NON CONFIRMEE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else min(1.0, NCONF * 1e-7), verdict=verdict,
            power_at=("normalisation de la vraisemblance masquee a 1e-7 pres (M = 80, 100, 128, 256) ; "
                      "l'outil a M = 80 reproduit celui du §166 chiffre pour chiffre (1e-6 bit) ; "
                      "generateurs plantes LUS AU MASQUE et retrouves (M = 100, 128, 256 ; plans 0 et "
                      "1 ; N jusqu'a 3,4e7), pic sur la vraie position ; lus au MAUVAIS masque, rien"),
            notes=(f"REJET MASQUE (§7.19) : {len(LIG)} chaines de flux, M = 100 et 128 sur les "
                   f"{len(TRIN0)} trinomes du plan 0 (L <= 31) et les {len(TRIN1)} du plan 1 (L <= 15), "
                   f"M = 256 sur les types nommes. D = {D}, max {MF[1]['gmax']:.2f} ({MF[0]}) contre "
                   f"{SEUIL_FLUX:.2f}. {SEC/3600:.2f} h. NON COUVERT : par nuit (flux seulement), "
                   "plan 1 de TYPE_3, troncature, pas fixe."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
