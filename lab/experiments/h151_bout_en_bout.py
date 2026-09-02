"""h151 — le témoin de BOUT EN BOUT : détecter, relever l'état complet, prédire.
(THEORIE_ETAT §7.23. Synthétique : générateur planté, aucune donnée réelle, aucun
pré-enregistrement requis — c'est un témoin, pas un test.)

LA CHAÎNE
=========
Le §7.23 chiffre la jonction entre la DP de synchronisation (§7.17-§7.21) et le relèvement
(§7.7-§7.12) mais ne la programme pas. La voici, sur un TYPE_1 planté (`x⁷ + x³ + 1`, sortie
`r >> 1`, `224` bits d'état), en quatre temps :

  1. DÉTECTION.  La DP sur les orbites du Fibonacci mod 4 (plan 1 observé) trouve l'orbite et
     la position ; le lissage avant-arrière donne la position de CHAQUE tirage à quelques mots
     près. On en tire les plans 0 et 1 de tous les mots consommés.
  2. CRIBLE.  Les plans 2, 3, 4 restent inconnus : `3 L = 21` bits. Pour chaque candidat, la
     suite basse `r mod 32` est déterminée, donc la classe `(v−1) mod 16 = x mod 16` de chaque
     mot ; on parcourt les tirages en branchant sur ACCEPTÉ / PERDU et on élague dès qu'une
     classe manque au tirage. C'est le crible du §7.6, restreint par la détection.
  3. RELÈVEMENT.  Les survivants (état bas complet, `5 L` bits) passent au réseau LLL exact du
     §7.8 (`lab/lfg_releve.py`) qui rend l'état 32 bits.
  4. PRÉDICTION.  L'état régénère la suite : on prédit le tirage suivant, et on vérifie.

Ce que ce témoin établit : la détection SUFFIT — le reste est mécanique, et coûte des minutes.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h145_sync_rejet as H                                             # noqa: E402
import lfg_releve as R                                                  # noqa: E402

POOL, DRAWN = H.POOL, H.DRAWN


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------
# les orbites mod 4 avec LEURS DEUX PLANS (plan 0 canonique, comme tools/lfg_beam_mod4.c)
# --------------------------------------------------------------------------

def orbites_deux_plans(K, L):
    """rend (b, c) : deux tableaux (2^(L-1), 2P) de bits — plan 0 et plan 1."""
    P = (1 << L) - 1
    Pi = 2 * P
    msk = (1 << L) - 1
    vu = np.zeros(1 << L, dtype=bool)
    B, C = [], []
    for c0 in range(1 << L):
        if vu[c0]:
            continue
        vu[c0] = True
        R0, R1 = 1, c0
        b = np.zeros(Pi, dtype=np.uint8)
        c = np.zeros(Pi, dtype=np.uint8)
        for i in range(Pi):
            x0, y0 = (R0 >> (K - 1)) & 1, (R0 >> (L - 1)) & 1
            x1, y1 = (R1 >> (K - 1)) & 1, (R1 >> (L - 1)) & 1
            bb, cc = x0 ^ y0, x1 ^ y1 ^ (x0 & y0)
            b[i], c[i] = bb, cc
            R0 = (R0 << 1) | bb
            R1 = (R1 << 1) | cc
            if i + 1 == P:
                vu[R1 & msk] = True
        assert (R1 & msk) == c0 and (R0 & msk) == 1
        B.append(b)
        C.append(c)
    assert len(B) == 1 << (L - 1)
    return np.stack(B), np.stack(C)


# --------------------------------------------------------------------------
# 1. la détection et le lissage
# --------------------------------------------------------------------------

def avant_arriere(seqs, a0s):
    sy = H.Synchro(seqs, eps=0.0)
    nseq, Pi = sy.nseq, sy.Pi
    A = [np.full((nseq, Pi), 1.0 / (nseq * Pi))]
    lbf = 0.0
    for a0 in a0s:
        T = H.table(a0)
        acc = np.zeros((nseq, Pi))
        for n in range(H.NMIN, H.NMAX + 1):
            acc += np.roll(A[-1] * T[n][sy.idx[n]], n, axis=1)
        s = acc.sum()
        lbf += np.log2(max(s, 1e-300)) + H.LOG2_C8020
        A.append(acc / s if s > 0 else acc)
    Bk = [np.ones((nseq, Pi))]
    for a0 in a0s[::-1]:
        T = H.table(a0)
        acc = np.zeros((nseq, Pi))
        for n in range(H.NMIN, H.NMAX + 1):
            acc += T[n][sy.idx[n]] * np.roll(Bk[-1], -n, axis=1)
        m = acc.max()
        Bk.append(acc / m if m > 0 else acc)
    Bk = Bk[::-1]
    G = [(A[t] * Bk[t]) for t in range(len(a0s) + 1)]
    return [g / max(g.sum(), 1e-300) for g in G], A, lbf


# --------------------------------------------------------------------------
# 2. le crible des plans 2-4, alignement compris
# --------------------------------------------------------------------------

def crible(b, c, q0, tirages, bornes, K, L, marge=8):
    """Les plans 0 et 1 de la séquence sont connus (détection) ; on énumère les 2^(3L) plans 2-4
    des L premiers mots et on propage `r mod 32` (anneau, mémoire O(2^(3L) L)).

    Contrainte (§7.7) : sous rejet, un mot est soit ACCEPTÉ (numéro neuf), soit PERDU (doublon
    d'un numéro déjà tiré) — dans les DEUX cas sa classe `x mod 16` appartient aux classes du
    tirage. Un mot dont la classe manque au tirage tue donc le candidat. Comme les frontières
    entre tirages ne sont connues qu'à quelques mots près (le lissage de la DP), on n'applique
    la contrainte qu'à l'INTÉRIEUR sûr de chaque tirage : `[q̂_t + marge, q̂_{t+1} − marge]`.
    C'est nécessaire, jamais faux, et cela suffit : ~17 mots par tirage à `0,7` de survie."""
    NB = 1 << (3 * L)
    Pi = len(b)
    nmots = bornes[-1] - bornes[0] + 2 * marge + L + 4
    idx = (q0 + np.arange(nmots)) % Pi
    b0 = b[idx].astype(np.int8)
    c1 = c[idx].astype(np.int8)
    buf = np.zeros((NB, L), dtype=np.int8)
    hauts = np.arange(NB, dtype=np.int64)
    for j in range(L):
        buf[:, j] = b0[j] | (c1[j] << 1) | (((hauts >> (3 * j)) & 7) << 2)
    NC = np.zeros((len(tirages), 16), dtype=bool)
    for t, S in enumerate(tirages):
        for v in S:
            NC[t, (v - 1) % 16] = True
    # a quel tirage appartient (surement) le mot i ?  -1 = zone de frontiere, non contrainte
    tmot = np.full(nmots, -1, dtype=np.int16)
    for t in range(len(tirages)):
        d = bornes[t] - bornes[0] + marge
        f = bornes[t + 1] - bornes[0] - marge
        if f > d:
            tmot[max(0, d):min(nmots, f)] = t
    vivant = np.ones(NB, dtype=bool)
    etat0 = buf.copy()
    for i in range(nmots):
        mot = buf[:, i] if i < L else (buf[:, (i - K) % L] + buf[:, (i - L) % L]) & 31
        if i >= L:
            buf[:, i % L] = mot
        if tmot[i] >= 0:
            vivant &= NC[tmot[i], (mot >> 1) & 15]
            if not vivant.any():
                return [], 0
    n = int(vivant.sum())
    return [[int(x) for x in etat0[i]] for i in np.nonzero(vivant)[0][:64]], n


# --------------------------------------------------------------------------
# le témoin
# --------------------------------------------------------------------------

def temoin(K=3, L=7, ND=25, graine=151, verbeux=True):
    rng = np.random.default_rng(graine)
    etat = [int(v) for v in rng.integers(0, 1 << 32, size=L, dtype=np.uint64)]
    if all(v % 2 == 0 for v in etat):
        etat[0] |= 1
    NW = 60 * ND + L + 200
    r = R.regenere(etat, K, L, NW)
    draws = R.tirages_de(r, ND)
    tirages = [S for (_, _, S) in draws]
    ns = [f - d for (d, f, S) in draws]
    a0s = [H.a0_de(S) for S in tirages]
    say(f"h151 — témoin de bout en bout : x^{L} + x^{K} + 1, sortie r >> 1, {ND} tirages "
        f"({sum(ns)} mots), état planté {etat}")

    # 1. détection
    t0 = time.time()
    b, c = orbites_deux_plans(K, L)
    G, A, lg = avant_arriere(c, a0s)
    i = int(np.argmax(G[0]))
    s0, q0 = i // c.shape[1], i % c.shape[1]
    # la vraie orbite et la vraie position de départ
    vrai = None
    for s in range(c.shape[0]):
        for q in range(c.shape[1]):
            if all(int(c[s][(q + j) % c.shape[1]]) == ((r[j] >> 1) & 1) for j in range(4 * L)):
                vrai = (s, q)
                break
        if vrai:
            break
    say(f"   1. détection : orbite/position lissée ({s0}, {q0}), vraie {vrai}, "
        f"masse {float(G[0].flat[i]):.3f} ; {time.time() - t0:.1f} s")

    # 2. crible des plans 2-4, frontières prises du lissage
    t1 = time.time()
    NDC = min(8, ND)                                   # tirages utilisés par le crible
    Pi = c.shape[1]
    # frontières : argmax du lissage CONTRAINT par le pas (20..40), ce qui empêche la dérive
    g0 = G[0].sum(axis=0) if G[0].ndim > 1 else G[0]
    q_start = int(np.argmax(G[0])) % Pi
    abs_b = [q_start]
    for t in range(1, NDC + 1):
        gt = G[t][s0]
        cands = [abs_b[-1] + n for n in range(H.NMIN, H.NMAX + 1)]
        abs_b.append(max(cands, key=lambda p: gt[p % Pi]))
    bornes = [p % Pi for p in abs_b]
    ecart = [abs_b[t] - abs_b[0] - (sum(ns[:t])) for t in range(NDC + 1)]
    say(f"   2. frontières lissées : écart à la vérité {ecart}")
    vrai_bas = [x & 31 for x in etat]
    bas, nsurv = [], 0
    for dq in (0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6):
        q = (abs_b[0] + dq) % Pi
        out, nn = crible(b[s0], c[s0], q, tirages[:NDC], [x + dq for x in abs_b], K, L)
        if out:
            bas += [o for o in out if o not in bas]
            nsurv += nn
            say(f"      crible dq={dq:+d} : {nn} survivant(s) sur 2^{3*L}"
                + ("   (dont le VRAI état bas)" if vrai_bas in out else ""))
    say(f"   2. crible : {nsurv} état(s) bas au total, vrai retenu {vrai_bas in bas} "
        f"({time.time() - t1:.1f} s)")
    if not bas:
        say("   2. crible : aucun survivant — témoin ÉCHOUÉ")
        return False

    # 3. relèvement
    t2 = time.time()
    etats = []
    for lo in bas[:20]:
        tr, _ = R.releve_etat(lo, tirages, K, L)
        etats += [e for e in tr if e not in etats]
    say(f"   3. relèvement : {len(etats)} état(s) 32 bits ; état vrai retrouvé "
        f"{etat in etats} ; {time.time() - t2:.1f} s")
    if etat not in etats:
        return False

    # 4. prédiction du tirage suivant
    seq = R.regenere(etats[0], K, L, NW + 200)
    suite = R.tirages_de(seq, ND + 3)
    vrai_suivant = R.tirages_de(r, ND + 3)[ND][2]
    pred = suite[ND][2]
    say(f"   4. prédiction du tirage {ND + 1} : {pred}")
    say(f"      tirage réel                   : {vrai_suivant}")
    say(f"      exact : {pred == vrai_suivant} ; log2 BF de la détection {lg:.1f} bits")
    return pred == vrai_suivant


if __name__ == "__main__":
    ND = int(sys.argv[sys.argv.index("--nd") + 1]) if "--nd" in sys.argv else 25
    ok = True
    for g in (151, 152, 153):
        ok &= temoin(ND=ND, graine=g)
        say("")
    say("témoin de bout en bout : " + ("OK" if ok else "ÉCHOUÉ"))
