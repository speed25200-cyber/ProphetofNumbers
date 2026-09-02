"""h145 — la SYNCHRONISATION sous le REJET (pas variable) : le trou explicite des §155-§160
(THEORIE_ETAT §7.17).

LE TROU
=======
Tous les cribles du flux continu (§157, §158 : 868 cribles, 0 survivant) et le decodage mou
(§160) lisent le generateur A PAS CONSTANT : le tirage t consomme S mots (S = 20..24, 79, 80).
L'echantillonneur le plus naif de tous, celui du programmeur presse,

    tant que |A| < 20 : x = suivant() ; v = 1 + (x mod 80) ; si v n'est pas dans A, A += v

consomme un nombre VARIABLE de mots (20 acceptes + les rejets : E[N] = 22,85, P(N > 40) =
8e-9), et l'alignement mot-tirage se perd : aucun crible a pas fixe ne le lit. Il etait
"explicitement hors des cribles" a chaque section. Le voici lu.

L'IDEE : LA POSITION ABSOLUE DANS LA m-SEQUENCE
===============================================
Le plan 0 d'un Fibonacci retarde additif de trinome primitif est une m-sequence de periode
P = 2^L - 1 : l'inconnue n'est pas un etat de L bits mais une POSITION q dans Z/P — et cette
position, augmentee du nombre de mots consommes, suit le generateur a travers les rejets.
Le tirage t consomme n_t mots aux positions q_t, ..., q_t + n_t - 1 ; le bit 0 du mot x
(x = r >> shift) est (v - 1) mod 2 : un mot de bit b est un numero UNIFORME parmi les 40
de la classe b (pair/impair de v - 1). L'ensemble tire A se scinde en A_0, A_1 (a_0 + a_1
= 20). La vraisemblance EXACTE d'une fenetre de n mots dont w_1 ont le bit 1 et w_0 = n - w_1
le bit 0, de dernier bit b (le vingtieme accepte) :

    P(A, n | fenetre) = F(w_{1-b}, a_{1-b}) . G(w_b, a_b)
    F(w, a) = a! S(w, a) / 40^w          (w mots couvrent exactement les a numeros : surjections)
    G(w, a) = a! S(w-1, a-1) / 40^w      (idem, le dernier mot est la premiere occurrence de
                                          l'un des a numeros)
S = nombres de Stirling de seconde espece. Verifie : sum_A sum_n sum_bits 2^-n P = 1 exactement
(a 6e-17), egal terme a terme a P_0(N = n) = 20! S(n-1, 19) / 80^n . C(80, 20).
Elle ne depend de A que par a_0 : la statistique suffisante du canal est le NOMBRE DE
NUMEROS IMPAIRS de chaque tirage (21 valeurs, entropie 3,01 bits sous H0).

LA PROGRAMMATION DYNAMIQUE DE SYNCHRONISATION
=============================================
Chaine cachee sur Z/P (ou sur (orbite, position) pour le plan 1 : 2^(L-1) orbites de periode
2P du Fibonacci mod 4), pas variable n in [20, 40] :

    alpha_t[(q + n) mod P] += alpha_{t-1}[q] . P(A_t, n | bits q..q+n-1),   alpha_0 = 1/P
    (avec une "evasion" epsilon = 1e-3 par tirage : alpha <- (1-eps) alpha + eps/P, resynchro)

Sum_q alpha_t = P_mel(A_1..A_t) ; facteur de Bayes BF_t = P_mel / P_0 = Sum alpha_t . C(80,20)^t.
Sous H0 (tirages uniformes) BF_t est une MARTINGALE de moyenne 1 (rapport de vraisemblance
d'un melange) : Ville, P_0(sup_t BF_t >= 10^7) <= 10^-7, sans aucune hypothese de
distribution, en tout temps t. Seuil : log2 BF >= 23,25. Sous H1 a position connue, le gain
moyen est 1,31 bit par tirage (Monte-Carlo, ecart-type 1,33) contre -5,0 bits par tirage pour
une position fausse : un bloc de 204 tirages rend ~266 - log2 P bits, le flux des milliers.
Variante "bloc" : alpha remis a 1/P au debut de chaque nuit (generateur reamorce chaque jour),
meme martingale.

CE QUE C'EST / CE QUE CE N'EST PAS
==================================
Couvre : shift 0 (sortie brute), les 31 trinomes primitifs L <= 17 ; shift 1 (glibc
random(), sortie r >> 1 : TYPE_1 compris), les trinomes L <= 10 ; la sequence alternee
(tout congruentiel lineaire mod 2^k a increment impair, sortie = etat) ; sous le flux continu
ET nuit par nuit. Ne couvre pas : TYPE_3, TYPE_4 (P = 2^31 - 1, 2^63 - 1) ; la troncature
(x . 80) >> 32 ; les echantillonneurs a pas fixe (deja cribles ailleurs).

TEMOINS
=======
--selftest : generateurs plantes (Fibonacci 32 bits, rejet exact) sous le flux et par bloc,
posterieur pique sur la vraie position, log2 BF >> 23,25 ; tirages aleatoires : log2 BF < 0.
Il TESTE l'archive (--archive) : pre-enregistrement AVANT toute lecture, jeton scelle.
"""

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POOL, DRAWN, HALF = 80, 20, 40
NMIN, NMAX = 20, 40                       # P(N > 40) = 8e-9 : 6e-4 tirage attendu sur l'archive
EPS = 1e-3                                # evasion (resynchronisation) par tirage
SEUIL_LOG2 = math.log2(1e7)               # Ville : P0(sup BF >= 1e7) <= 1e-7
LOG2_C8020 = math.log2(math.comb(POOL, DRAWN))
EXP_ID = "h145.sync_rejet"


def say(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------
# la vraisemblance exacte d'une fenetre : Stirling, F, G, tables par a0
# --------------------------------------------------------------------------

_S = [[0] * (DRAWN + 1) for _ in range(NMAX + 1)]
_S[0][0] = 1
for _w in range(1, NMAX + 1):
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


def P_fenetre(w1, n, a0, a1, b):
    w0 = n - w1
    if b == 1:
        return F(w0, a0) * G(w1, a1)
    return F(w1, a1) * G(w0, a0)


_TAB = {}


def table(a0):
    """T[n] aplati sur (b, w1) : T[n][b * (NMAX + 1) + w1] = P(A, n | w1, dernier bit b)."""
    if a0 not in _TAB:
        a1 = DRAWN - a0
        t = np.zeros((NMAX + 1, 2 * (NMAX + 1)))
        for n in range(NMIN, NMAX + 1):
            for w1 in range(n + 1):
                t[n, w1] = P_fenetre(w1, n, a0, a1, 0)
                t[n, NMAX + 1 + w1] = P_fenetre(w1, n, a0, a1, 1)
        _TAB[a0] = t
    return _TAB[a0]


# --------------------------------------------------------------------------
# trinomes primitifs, m-sequences (plan 0), orbites du Fibonacci mod 4 (plan 1)
# --------------------------------------------------------------------------

def _mulmod(a, b, p, L):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if (a >> L) & 1:
            a ^= p
    return r


def _powmod(a, e, p, L):
    r = 1
    while e:
        if e & 1:
            r = _mulmod(r, a, p, L)
        a = _mulmod(a, a, p, L)
        e >>= 1
    return r


def _facteurs(n):
    f, d = set(), 2
    while d * d <= n:
        while n % d == 0:
            f.add(d)
            n //= d
        d += 1
    if n > 1:
        f.add(n)
    return f


def primitif(K, L):
    p = (1 << L) | (1 << K) | 1
    n = (1 << L) - 1
    if _powmod(2, n, p, L) != 1:
        return False
    return all(_powmod(2, n // q, p, L) != 1 for q in _facteurs(n))


LMAX = 17
NOMS = {(3, 7): "TYPE_1", (1, 15): "TYPE_2", (3, 31): "TYPE_3"}
TRINOMES = [(K, L) for L in range(2, LMAX + 1) for K in range(1, L) if primitif(K, L)]
assert len(TRINOMES) == 31 and (3, 7) in TRINOMES and (1, 15) in TRINOMES


def m_sequence(K, L):
    """plan 0 : b_i = b_{i-K} xor b_{i-L}, periode P = 2^L - 1 (verifiee) ; rend (1, P) bits."""
    P = (1 << L) - 1
    b = np.zeros(P + L, dtype=np.uint8)
    b[0] = 1
    for i in range(L, P + L):
        b[i] = b[i - K] ^ b[i - L]
    assert np.array_equal(b[P:P + L], b[:L]), "periode"
    return b[:P].reshape(1, P)


def orbites_mod4(K, L):
    """plan 1 du Fibonacci mod 4, r_i = r_{i-K} + r_{i-L} mod 4, plan 0 non nul : 2^(L-1) orbites
    de periode 2P ; rend (2^(L-1), 2P) bits (bit 1 de r)."""
    P = (1 << L) - 1
    Pi = 2 * P
    vu = np.zeros(1 << (2 * L), dtype=bool)       # etats (r_0..r_{L-1}) codes sur 2L bits
    orbs = []
    for rep in range(1 << (2 * L)):
        if vu[rep]:
            continue
        r0 = [(rep >> (2 * i)) & 3 for i in range(L)]
        if all(v % 2 == 0 for v in r0):
            vu[rep] = True                          # plan 0 nul : le plan 1 est une m-sequence pure
            continue
        r = np.zeros(Pi + L, dtype=np.int64)
        r[:L] = r0
        for i in range(L, Pi + L):
            r[i] = (r[i - K] + r[i - L]) & 3
        assert np.array_equal(r[Pi:Pi + L], r[:L]), "periode 2P"
        code = np.zeros(Pi, dtype=np.int64)
        for i in range(L):
            code |= r[i:i + Pi] << (2 * i)
        assert not vu[code].any(), "orbites disjointes"
        assert len(np.unique(code)) == Pi, "periode minimale 2P"
        vu[code] = True
        orbs.append(((r[:Pi] >> 1) & 1).astype(np.uint8))
    assert len(orbs) == 1 << (L - 1), len(orbs)
    return np.stack(orbs)


def sequence_alternee():
    return np.array([[0, 1]], dtype=np.uint8)


# --------------------------------------------------------------------------
# la programmation dynamique de synchronisation
# --------------------------------------------------------------------------

class Synchro:
    """sequences (nseq, Pi) de bits periodiques ; alpha (nseq, Pi) ; un pas par tirage."""

    def __init__(self, seqs, eps=EPS):
        seqs = np.asarray(seqs, dtype=np.uint8)
        self.nseq, self.Pi = seqs.shape
        self.eps = eps
        ext = np.concatenate([seqs, seqs[:, :NMAX]], axis=1) if self.Pi >= NMAX else \
            np.concatenate([seqs] * (NMAX // self.Pi + 2), axis=1)[:, :self.Pi + NMAX]
        C = np.concatenate([np.zeros((self.nseq, 1), np.int64), np.cumsum(ext, axis=1)], axis=1)
        # index (b_dernier, w1) pour chaque n : int16 (nseq, Pi)
        self.idx = {}
        for n in range(NMIN, NMAX + 1):
            w1 = C[:, n:n + self.Pi] - C[:, :self.Pi]
            bl = ext[:, n - 1:n - 1 + self.Pi].astype(np.int64)
            self.idx[n] = (w1 + bl * (NMAX + 1)).astype(np.int16)
        self.reset()

    def reset(self):
        self.alpha = np.full((self.nseq, self.Pi), 1.0 / (self.nseq * self.Pi))
        self.log2bf = 0.0
        self.max_log2bf = 0.0
        self.t = 0
        self.t_max = 0

    def pas(self, a0, evasion=True):
        """un tirage de a0 numeros impairs ; rend log2 BF cumule."""
        T = table(a0)
        al = self.alpha
        if evasion and self.eps > 0:
            al = (1.0 - self.eps) * al + self.eps / (self.nseq * self.Pi)
        acc = np.zeros_like(al)
        for n in range(NMIN, NMAX + 1):
            acc += np.roll(al * T[n][self.idx[n]], n, axis=1)
        s = float(acc.sum())
        if s <= 0.0:
            # aucun chemin : masse nulle, BF = 0 ; on repart de l'uniforme (evasion totale)
            self.log2bf = -math.inf
            self.alpha = np.full_like(al, 1.0 / (self.nseq * self.Pi))
        else:
            self.alpha = acc / s
            self.log2bf += math.log2(s) + LOG2_C8020
        self.t += 1
        if self.log2bf > self.max_log2bf:
            self.max_log2bf = self.log2bf
            self.t_max = self.t
        return self.log2bf

    def pic(self):
        """(sequence, position, masse) du maximum a posteriori."""
        i = int(np.argmax(self.alpha))
        return i // self.Pi, i % self.Pi, float(self.alpha.flat[i])


# --------------------------------------------------------------------------
# generateurs plantes (32 bits) et echantillonneur a rejet exact
# --------------------------------------------------------------------------

class LFG32:
    def __init__(self, K, L, rng, shift):
        self.K, self.L, self.shift = K, L, shift
        self.r = [int(v) for v in rng.integers(0, 1 << 32, size=L, dtype=np.uint64)]
        if all(v % 2 == 0 for v in self.r):
            self.r[0] |= 1
        self.i = 0
        self.trace = []                                   # bits 0 des sorties (verification)

    def suivant(self):
        L, K = self.L, self.K
        v = (self.r[-K] + self.r[-L]) & 0xFFFFFFFF
        self.r.append(v)
        del self.r[0]
        x = v >> self.shift
        self.trace.append(x & 1)
        return x


class Alterne:
    def __init__(self, rng):
        self.x = int(rng.integers(0, 1 << 32))
        self.trace = []

    def suivant(self):
        self.x = (self.x * 1103515245 + 12345) & 0xFFFFFFFF
        self.trace.append(self.x & 1)
        return self.x


def tirage_rejet(gen):
    A = []
    n = 0
    while len(A) < DRAWN:
        v = 1 + gen.suivant() % POOL
        n += 1
        if v not in A:
            A.append(v)
    return sorted(A), n


def a0_de(A):
    """nombre de numeros v de (v - 1) pair, i.e. de bit 0 nul : les numeros impairs."""
    return sum(1 for v in A if (v - 1) % 2 == 0)


def positions_dans(seqs, bits):
    """toutes les positions (seq, q) ou la fenetre de bits apparait dans les sequences periodiques."""
    nseq, Pi = seqs.shape
    w = np.asarray(bits, dtype=np.uint8)
    m = len(w)
    ext = np.concatenate([seqs] * (m // Pi + 2), axis=1)[:, :Pi + m]
    ok = np.ones((nseq, Pi), dtype=bool)
    for j in range(m):
        ok &= ext[:, j:j + Pi] == w[j]
    return [(int(s), int(q)) for s, q in zip(*np.nonzero(ok))]


# --------------------------------------------------------------------------
# temoins
# --------------------------------------------------------------------------

def selftest(K, L, shift, T, graine, bloc=0, verbeux=True):
    """plante un LFG (K, L) a shift donne, T tirages sous le rejet (un generateur neuf par bloc
    si bloc > 0, la DP remise a l'uniforme au debut de chaque bloc) ; puis T tirages aleatoires."""
    rng = np.random.default_rng(graine)
    seqs = m_sequence(K, L) if shift == 0 else orbites_mod4(K, L)
    t0 = time.time()
    sy = Synchro(seqs)
    t_init = time.time() - t0
    tirages, ns, gen = [], [], None
    for t in range(T):
        if gen is None or (bloc and t % bloc == 0):
            gen = LFG32(K, L, rng, shift)
            ns = []
        A, n = tirage_rejet(gen)
        tirages.append(A)
        ns.append(n)
    # vraie position du dernier generateur au depart, puis apres ses tirages
    pos = positions_dans(seqs, gen.trace[:min(len(gen.trace), 4 * L + 8)])
    assert pos, "la trace n'est pas dans les sequences"
    attendu = {(s_, (q_ + sum(ns)) % sy.Pi) for s_, q_ in pos}
    t0 = time.time()
    lb = []
    for t, A in enumerate(tirages):
        if bloc and t % bloc == 0:
            sy.alpha[:] = 1.0 / sy.alpha.size
        lb.append(sy.pas(a0_de(A)))
    dt = time.time() - t0
    s_pic, q_pic, masse = sy.pic()
    # la position apres le dernier tirage reste floue a n_T pres (ses rejets ne sont pas
    # observes ; la DP filtre, elle ne lisse pas) : le pic doit etre sur la bonne orbite a moins
    # de n_T <= 40 mots de la vraie position, qui doit porter >= 0,03 de masse
    m_vrai = max(float(sy.alpha[s_, q_]) for s_, q_ in attendu)
    ok = any(s_pic == s_ and min((q_pic - q_) % sy.Pi, (q_ - q_pic) % sy.Pi) <= ns[-1] for s_, q_ in attendu) \
        and m_vrai >= 0.03
    sy.reset()
    lb0 = []
    for t in range(T):
        if bloc and t % bloc == 0:
            sy.alpha[:] = 1.0 / sy.alpha.size
        A = sorted(int(v) + 1 for v in rng.choice(POOL, DRAWN, replace=False))
        lb0.append(sy.pas(a0_de(A)))
    d = dict(K=K, L=L, shift=shift, T=T, bloc=bloc, nseq=sy.nseq, Pi=sy.Pi, log2bf=lb[-1], max_log2bf=max(lb),
             t_seuil=next((t + 1 for t, v in enumerate(lb) if v >= SEUIL_LOG2), None),
             pic_ok=ok, n_pos=len(pos), masse_pic=masse, masse_vrai=m_vrai, log2bf_nul=lb0[-1],
             max_log2bf_nul=max(lb0),
             n_max=max(ns), ms_par_tirage=1000 * dt / T, s_init=t_init)
    if verbeux:
        say(f"   K={K} L={L} shift={shift} bloc={bloc} {sy.nseq}x{sy.Pi} : plante log2 BF = {lb[-1]:.1f} "
            f"(max {max(lb):.1f}, seuil au tirage {d['t_seuil']}) pic {'OK' if ok else 'FAUX'} "
            f"masse {masse:.3f}, vraie {m_vrai:.3f} ({len(pos)} pos.) ; nul log2 BF = {lb0[-1]:.1f} (max {max(lb0):.2f}) ; "
            f"{d['ms_par_tirage']:.2f} ms/tirage, init {t_init:.1f} s, n max {max(ns)}")
    return d


if __name__ == "__main__" and "--selftest" in sys.argv:
    say("h145 selftest")
    res = []
    for K, L, shift, T, bloc in [(1, 3, 0, 60, 0), (3, 7, 0, 100, 0), (3, 7, 1, 120, 0), (1, 15, 0, 150, 0),
                                 (3, 17, 0, 150, 0), (4, 9, 1, 150, 0), (3, 7, 1, 204 * 3, 204),
                                 (1, 15, 0, 204 * 3, 204)]:
        res.append(selftest(K, L, shift, T, graine=100 + L + shift, bloc=bloc))
    assert all(r["pic_ok"] and r["log2bf"] > SEUIL_LOG2 and r["max_log2bf_nul"] < SEUIL_LOG2 for r in res)
    # la sequence alternee
    sy = Synchro(sequence_alternee())
    rng = np.random.default_rng(7)
    g = Alterne(rng)
    lb = [sy.pas(a0_de(tirage_rejet(g)[0])) for _ in range(60)]
    say(f"   alternee (LCG) : log2 BF = {lb[-1]:.1f} apres 60 tirages")
    assert lb[-1] > SEUIL_LOG2
    say("selftest OK")


# ==========================================================================
# L'ARCHIVE : l'outil C tools/lfg_sync_rejet.c (les deux chaines, flux et bloc, en un passage),
# croise avec la DP numpy ci-dessus a 5e-5 pres sur des donnees plantees et nulles
# ==========================================================================

LMAX1 = 11                                    # shift 1 : 2^(2L-1) etats, L <= 11 (2^21)
OUTIL = os.environ.get("H145_OUTIL", "/tmp/lfg_sync_rejet_h145")
TMP = "/tmp"
JOURNAL = os.path.join(TMP, "h145_journal.txt")
FJETON = os.path.join(TMP, "h145_jeton.json")


def grille():
    g = [(K, L, 0) for K, L in TRINOMES]
    g.append((0, 0, "alt"))
    g += [(K, L, 1) for K, L in TRINOMES if L <= LMAX1]
    return g


def cle(K, L, shift):
    return f"{K},{L},{shift}"


def lire_journal():
    d = {}
    if os.path.exists(JOURNAL):
        for l in open(JOURNAL, encoding="utf-8"):
            t = l.split()
            if len(t) >= 18 and t[0] != "#":
                d[t[0]] = dict(nseq=int(t[1]), Pi=int(t[2]), nt=int(t[3]), lf=float(t[4]), mf=float(t[5]),
                               tmf=int(t[6]), lb=float(t[7]), mb=float(t[8]), tmb=int(t[9]), maxbloc=float(t[10]),
                               bmax=int(t[11]), pic_seq=int(t[12]), pic_q=int(t[13]), pic_masse=float(t[14]),
                               sec=float(t[15]), nimpf=int(t[16]), nimpb=int(t[17]))
    return d


def lancer(K, L, shift, f_a0, f_blocs, nice=10, pasj=10000):
    """execute l'outil C ; rend le dict FIN et la liste des log2 BF par bloc."""
    import subprocess
    cmd = ["nice", "-n", str(nice), OUTIL, str(K), str(L), str(shift), f_a0, f_blocs, repr(EPS), str(pasj)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
    blocs, fin = [], None
    for l in p.stdout:
        t = l.split()
        if t[0] == "T":
            say(f"      {cle(K, L, shift):>8}  t={int(t[1]):6d}  flux {float(t[2]):10.1f} (max {float(t[3]):6.2f} @ {t[4]:>5})"
                f"  bloc {float(t[5]):10.1f} (max {float(t[6]):6.2f} @ {t[7]:>5})")
        elif t[0] == "BLOC":
            blocs.append((int(t[1]), int(t[2]), int(t[3]), float(t[4])))
        elif t[0] == "FIN":
            fin = dict(nseq=int(t[1]), Pi=int(t[2]), nt=int(t[3]), lf=float(t[4]), mf=float(t[5]), tmf=int(t[6]),
                       lb=float(t[7]), mb=float(t[8]), tmb=int(t[9]), maxbloc=float(t[10]), bmax=int(t[11]),
                       pic_seq=int(t[12]), pic_q=int(t[13]), pic_masse=float(t[14]), sec=float(t[15]),
                       nimpf=int(t[16]), nimpb=int(t[17]))
    rc = p.wait()
    if rc != 0 or fin is None:
        raise RuntimeError(f"outil C : code {rc}, FIN {fin}")
    return fin, blocs


if __name__ == "__main__" and "--archive" in sys.argv:
    import lab
    DRY = "--dry" in sys.argv
    T0 = time.time()
    say(f"h145 --archive  ({'MODE ESSAI' if DRY else 'jeton'})  outil {OUTIL}")
    assert os.path.exists(OUTIL), "compiler : cc -O3 -march=native -o /tmp/lfg_sync_rejet_h145 tools/lfg_sync_rejet.c -lm"

    # 1. l'archive -> a0 par tirage (numeros impairs) et debuts de bloc
    ARCH = lab.load()
    TS = np.asarray(ARCH.ts).astype(np.int64)
    NUM = np.sort(np.asarray(ARCH.nums).astype(np.int64), axis=1)
    NTOT = len(TS)
    coupe = np.flatnonzero(np.diff(TS) != 300)
    DEB = np.r_[0, coupe + 1]
    NBLOCS = len(DEB)
    if DRY:
        # l'essai ne lit PAS l'archive : a0 tires sous H0 (structure de blocs conservee)
        rng = np.random.default_rng(145)
        A0 = np.array([int(((rng.choice(POOL, DRAWN, replace=False)) % 2 == 0).sum()) for _ in range(NTOT)])
        F_A0, F_BLOCS = os.path.join(TMP, "h145_dry_a0.txt"), os.path.join(TMP, "h145_dry_blocs.txt")
    else:
        A0 = ((NUM - 1) % 2 == 0).sum(axis=1)
        F_A0, F_BLOCS = os.path.join(TMP, "h145_a0.txt"), os.path.join(TMP, "h145_blocs.txt")
    assert NUM.shape == (NTOT, DRAWN) and A0.min() >= 0 and A0.max() <= DRAWN
    open(F_A0, "w").write("\n".join(str(int(a)) for a in A0) + "\n")
    open(F_BLOCS, "w").write("\n".join(str(int(d)) for d in DEB) + "\n")
    h_a0 = -sum(c / NTOT * math.log2(c / NTOT) for c in np.bincount(A0, minlength=DRAWN + 1) if c)
    say(f"   {NTOT} tirages, {NBLOCS} blocs ; a0 (numeros impairs) : moyenne {A0.mean():.3f} "
        f"(H0 : 10), entropie {h_a0:.3f} bits (H0 : 3,010)")

    # 2. la grille et le pre-enregistrement, AVANT toute lecture
    G = grille()
    NCONF = len(G)
    N_CHAINES = 2 * NCONF                      # flux + bloc cumulee
    P_UNION = N_CHAINES * 1e-7 + NCONF * 1e-7  # + max par bloc (union sur les 370 blocs incluse)
    HYPOTHESE = (
        "Ni le flux continu de l'archive triee (70 560 tirages, un seul etat) ni ses 370 blocs de "
        "nuit (generateur reamorce chaque nuit) ne sont engendres par un Fibonacci retarde additif "
        "r_i = r_(i-K) + r_(i-L) mod 2^32 lu par l'echantillonneur A REJET (v = 1 + (x mod 80), "
        "refuse si deja tire ; pas variable n in [20, 40] mots par tirage) : plan 0 (sortie x = r, "
        f"shift 0) des {len(TRINOMES)} trinomes primitifs L <= 17 (TYPE_1, TYPE_2 compris), plans 0-1 "
        f"(x = r >> 1, glibc random()) des trinomes L <= {LMAX1} ; ni par un congruentiel lineaire "
        "mod 2^k a increment impair de sortie x = etat (bit 0 alterne). Synchronisation (§7.17) : "
        "chaine cachee sur la position absolue dans la m-sequence (shift 0 : Z/(2^L-1) ; shift 1 : "
        "2^(L-1) orbites de periode 2(2^L-1) du Fibonacci mod 4), vraisemblance exacte de fenetre "
        "F(w,a) G(w,a) (nombres de Stirling), evasion 1e-3 par tirage, statistique suffisante a0 "
        "= nombre de numeros impairs du tirage. Design, seuils et temoins fixes AVANT cette "
        "consignation sur des generateurs plantes, jamais sur l'archive"
    )
    STATISTIQUE = (
        f"D = nombre de chaines DETECTEES parmi {N_CHAINES} (flux et bloc-cumulee, {NCONF} "
        "configurations) : maximum courant de log2 BF_t >= log2(1e7) = 23,25 ; plus le nombre de "
        f"configurations dont un bloc de nuit atteint log2 BF >= 23,25 + log2({NBLOCS}) = "
        f"{SEUIL_LOG2 + math.log2(NBLOCS):.2f}. BF_t = P_melange(A_1..A_t) / P_0 (C(80,20)^t Sum alpha_t)"
    )
    NULL = (
        "inegalite de Ville : sous H0 (tirages uniformes sans remise) BF_t est une (sur)martingale "
        "de moyenne <= 1 (rapport de vraisemblance d'un modele de melange propre, tronque a n <= 40), "
        "donc P_0(sup_t BF_t >= 1e7) <= 1e-7 par chaine, en tout temps, sans hypothese de "
        f"distribution ; borne d'union sur les chaines et les blocs : E[D] <= {P_UNION:.1e}"
    )
    VERDICT = (
        "conforme si D = 0 ; ETAT TROUVE si une chaine depasse 23,25 et son pic a posteriori se "
        "confirme (position stable, log2 BF croissant de ~1,3 bit par tirage ensuite) ; DETECTION "
        "NON CONFIRMEE sinon (anomalie a examiner, non conforme)"
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
        G = G[:3]

    # 3. la grille, avec reprise par le journal
    say(f"   grille : {NCONF} configurations ({len(TRINOMES)} shift 0, 1 alternee, "
        f"{sum(1 for K, L, s in G if s == 1)} shift 1 L <= {LMAX1}) ; journal {JOURNAL}")
    FAIT = lire_journal() if not DRY else {}
    for K, L, shift in G:
        k = cle(K, L, shift)
        if k in FAIT:
            continue
        say(f"   >> {k}  ({time.strftime('%H:%M:%SZ', time.gmtime())})")
        fin, blocs = lancer(K, L, shift, F_A0, F_BLOCS)
        assert fin["nt"] == NTOT and len(blocs) == NBLOCS, (fin, len(blocs))
        vals = np.array([b[3] for b in blocs])
        say(f"      FIN {k} : {fin['nseq']}x{fin['Pi']}  flux log2 BF {fin['lf']:.1f} (max {fin['mf']:.2f} @ {fin['tmf']}) ; "
            f"bloc cumulee {fin['lb']:.1f} (max {fin['mb']:.2f} @ {fin['tmb']}) ; par bloc max {fin['maxbloc']:.2f} "
            f"(bloc {fin['bmax']}), moyenne {vals.mean():.1f} +- {vals.std():.1f} ; impossibles {fin['nimpf']}/{fin['nimpb']} ; "
            f"{fin['sec']:.1f} s"
            + ("   !! DETECTION" if fin['mf'] >= SEUIL_LOG2 or fin['mb'] >= SEUIL_LOG2
               or fin['maxbloc'] >= SEUIL_LOG2 + math.log2(NBLOCS) else ""))
        if not DRY:
            with open(os.path.join(TMP, f"h145_blocs_{K}_{L}_{shift}.txt"), "w") as f:
                f.write("".join(f"{b} {t0} {n} {v:.6f}\n" for b, t0, n, v in blocs))
            with open(JOURNAL, "a", encoding="utf-8") as f:
                f.write(f"{k} {fin['nseq']} {fin['Pi']} {fin['nt']} {fin['lf']:.4f} {fin['mf']:.4f} {fin['tmf']} "
                        f"{fin['lb']:.4f} {fin['mb']:.4f} {fin['tmb']} {fin['maxbloc']:.4f} {fin['bmax']} "
                        f"{fin['pic_seq']} {fin['pic_q']} {fin['pic_masse']:.6f} {fin['sec']:.1f} "
                        f"{fin['nimpf']} {fin['nimpb']}\n")
        FAIT[k] = fin

    # 4. le bilan et la consignation
    LIG = [(k, FAIT[k]) for k in (cle(*c) for c in G) if k in FAIT]
    SEUIL_BLOC = SEUIL_LOG2 + math.log2(NBLOCS)
    D_FLUX = sum(1 for k, f in LIG if f["mf"] >= SEUIL_LOG2)
    D_BLOC = sum(1 for k, f in LIG if f["mb"] >= SEUIL_LOG2)
    D_NUIT = sum(1 for k, f in LIG if f["maxbloc"] >= SEUIL_BLOC)
    D = D_FLUX + D_BLOC + D_NUIT
    MF = max(LIG, key=lambda kf: kf[1]["mf"])
    MB = max(LIG, key=lambda kf: kf[1]["mb"])
    MN = max(LIG, key=lambda kf: kf[1]["maxbloc"])
    SEC = sum(f["sec"] for k, f in LIG)
    N_IMP = sum(1 for k, f in LIG if f["nimpf"] > 0)
    say(f"\n   {len(LIG)} configurations : D = {D} ({D_FLUX} flux, {D_BLOC} bloc cumulee, {D_NUIT} nuit) ; "
        f"{N_IMP} configurations a tirage impossible (exclues exactement) ; "
        f"max flux {MF[1]['mf']:.2f} ({MF[0]} @ {MF[1]['tmf']}) ; max bloc cumulee {MB[1]['mb']:.2f} "
        f"({MB[0]} @ {MB[1]['tmb']}) ; max par nuit {MN[1]['maxbloc']:.2f} ({MN[0]}, bloc {MN[1]['bmax']}) "
        f"contre {SEUIL_LOG2:.2f} et {SEUIL_BLOC:.2f} ; {SEC/3600:.2f} h de DP")
    if DRY or len(LIG) < NCONF:
        say("   grille incomplete ou essai : rien n'est consigne.")
    else:
        TOK["m_extra"] = 0
        verdict = "conforme" if D == 0 else "DETECTION NON CONFIRMEE"
        lab.record(
            TOK, float(D), p=1.0 if D == 0 else min(1.0, P_UNION), verdict=verdict,
            power_at=("temoins plantes (Fibonacci 32 bits, rejet exact, meme DP, meme evasion) : flux L=3 s0 "
                      "log2 BF 30,2 en 60 tirages (seuil au tirage 33), L=7 s0 94,6/100 (32), TYPE_1 s1 "
                      "87,4/120 (40), TYPE_2 s0 116,1/150 (39), L=17 s0 seuil avant 150 ; par bloc de 204 "
                      "(generateur neuf chaque bloc) TYPE_1 s1 508 bits en 3 blocs, TYPE_2 s0 543, "
                      "max par bloc 186-193 ; alternee 327/300. Tirages nuls : max log2 BF <= 1,4 sur tous "
                      "les temoins, -5 bits par tirage a position fausse. Outil C = DP numpy a 5e-5 pres"),
            notes=(f"LA SYNCHRONISATION SOUS LE REJET : {len(LIG)} configurations ({len(TRINOMES)} trinomes "
                   f"shift 0, alternee, {sum(1 for K, L, s in G if s == 1)} shift 1 L <= {LMAX1}), "
                   f"{N_CHAINES} chaines + {NBLOCS} blocs par configuration. D = {D}. max log2 BF flux "
                   f"{MF[1]['mf']:.2f} ({MF[0]}), bloc cumulee {MB[1]['mb']:.2f} ({MB[0]}), par nuit "
                   f"{MN[1]['maxbloc']:.2f} ({MN[0]} bloc {MN[1]['bmax']}) ; seuils {SEUIL_LOG2:.2f} / "
                   f"{SEUIL_BLOC:.2f}. {N_IMP} configurations tuees par un tirage impossible (F(w,a) = 0). "
                   f"a0 : entropie archive {h_a0:.3f} bits. {SEC/3600:.2f} h de DP. "
                   "NON COUVERT : TYPE_3, TYPE_4, shift 1 L >= 15, troncature (x*80)>>32, shifts >= 2."))
        h = lab.holm()
        say(f"   consigne : {EXP_ID}   verdict {verdict}")
        say(f"   m du registre : {h[0]['m_total']:,}   significatifs : {sum(1 for r in h if r['significant'])}")
    say(f"\n   duree totale {(time.time() - T0)/60:.1f} min")
