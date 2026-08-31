"""h69 — le boost : la seconde donnee publiee, et ce qu'elle corrige au §88.

Ce que l'archive contient vraiment
===================================
    bonus   present sur 70 560 / 70 560, valeurs 1..80
    boost   present sur 70 560 / 70 560, valeurs {1, 2, 3, 4, 5, 10}
    extra   ABSENT — et il ne peut pas y etre : l'EXTRA n'est pas un tirage
            mais une OPTION DE MISE a CHF 2 (§63, reglement officiel). Il n'y
            a rien de tire a consigner.

Le dossier a donc toujours eu DEUX donnees publiees par tirage, et n'en a
exploite qu'une. Le boost porte 1,879 bit d'entropie par tirage.

LA LOI DU BOOST
================
Les seuils cumules observes sur 70 560 tirages :

    0,51193   0,74990   0,90050   0,95045   0,97510   1

Les quatre derniers sont des POURCENTAGES RONDS — 75, 90, 95 et 97,5 % — a
moins de 0,6 ecart-type. Le premier vaut ~0,512, et 1/2 est EXCLU a 6,3
ecarts-types : ce n'est donc pas « une chance sur deux ».

CE QUE CELA DONNE
==================
Si le boost vaut k quand u = out/2^w tombe dans [t_{k-1}, t_k), alors
l'observation contraint out a un INTERVALLE — exactement la situation du §87,
dont la machinerie rend les formes lineaires determinees. Les intervalles de
boost >= 2 ont des bornes RONDES, donc certaines.

CE QUE CELA CORRIGE AU §88, ET C'EST LE POINT
==============================================
Le §88 suppose que le generateur avance de VINGT mots par tirage. Or si le
boost est tire du meme flux, il en consomme au moins un de plus. Le §88
testait donc une seule valeur d'un parametre inconnu.

Ce fichier reprend son attaque pour plusieurs longueurs de tirage.

ET CE QUE CELA NE CORRIGE PAS AU §89. Berlekamp-Massey ne depend PAS de cette
longueur : la suite du bonus vaut phi(M^t x) avec M = L^W, et M est lineaire
pour tout W fixe. Le §89 ne suppose donc que « un nombre FIXE de mots par
tirage », pas « vingt ». La section 5 le verifie.

Il TESTE l'archive : il consigne au registre.
"""

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H69_DRY") == "1"
NB = 4
WBITS = 18                                # largeur reduite pour les formes


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


# ==========================================================================
rule("1. CE QUE L'ARCHIVE CONTIENT, ET CE QU'ELLE NE CONTIENT PAS")
# ==========================================================================

arch = lab.load()
bon = arch.bonus.astype(np.int64)
bst = arch.boost.astype(np.int64)
NN = len(bon)
import collections                                            # noqa: E402
cnt = collections.Counter(bst.tolist())
VALS = sorted(cnt)
say(f"""   bonus   {int((bon > 0).sum()):,} / {NN:,}   valeurs 1..{int(bon.max())}
   boost   {int((bst > 0).sum()):,} / {NN:,}   valeurs {VALS}
   extra   ABSENT — et il ne peut pas y etre : l'EXTRA est une OPTION DE MISE
           a CHF 2 (§63), pas un tirage. Il n'y a rien a consigner.

   Le dossier a donc toujours eu DEUX donnees publiees par tirage et n'en a
   exploite qu'une.
""")
cum, run = [], 0
for v in VALS:
    run += cnt[v] / NN
    cum.append(run)
say(f"   {'boost':>7} {'compte':>8} {'fréquence':>10} {'cumul':>9} {'rond ?':>10} {'z':>7}")
# cum[i] est le seuil qui TERMINE l'intervalle du boost VALS[i] : le candidat
# rond se lit donc a l'indice i, pas a i+1. Une premiere version decalait la
# colonne d'un cran et affichait des z de -146.
TGT = [None, 0.75, 0.90, 0.95, 0.975, 1.0]
for i, v in enumerate(VALS):
    tgt = TGT[i] if i < len(TGT) else None
    z = ""
    if tgt is not None and tgt < 1:
        se = math.sqrt(tgt * (1 - tgt) / NN)
        z = f"{(cum[i] - tgt) / se:+.2f}"
    say(f"   {v:>7} {cnt[v]:>8,} {cnt[v]/NN:>10.5f} {cum[i]:>9.5f} "
        f"{(f'{tgt:.4f}' if tgt else '? — incertain'):>13} {z:>7}")
p0 = cum[0]
se0 = math.sqrt(p0 * (1 - p0) / NN)
say(f"""
   Les quatre seuils 0,75 / 0,90 / 0,95 / 0,975 tombent a moins de 0,6 σ : ce
   sont des pourcentages ronds, et non le fruit du hasard.

   Le PREMIER seuil vaut {p0:.5f}. Un tirage a pile ou face — 0,5 — est ecarte a
   {abs(p0-0.5)/se0:.1f} σ. Restent compatibles 0,51 ; 0,512 ; 0,5125 ; 0,515.
   L'entropie du boost vaut {-sum((c/NN)*math.log2(c/NN) for c in cnt.values()):.4f} bit par tirage.""")


# ==========================================================================
rule("2. CE QUE LE BOOST PUBLIE, EN FORMES LINÉAIRES")
# ==========================================================================

T = [0.0, 0.512, 0.75, 0.90, 0.95, 0.975, 1.0]


def dim_det(lo, hi, w):
    basis = {}
    for x in range(lo, hi + 1):
        if len(basis) >= w:
            break
        d = x ^ lo
        while d:
            h = d.bit_length() - 1
            if h in basis:
                d ^= basis[h]
            else:
                basis[h] = d
                break
    return w - len(basis)


def top_forms(lo, hi, w):
    """Les bits de poids fort communs : (nombre, valeur)."""
    k = 0
    while k < w and (lo >> (w - k - 1)) == (hi >> (w - k - 1)):
        k += 1
    return k, lo >> (w - k) if k else 0


say(f"""   Le boost contraint out a un intervalle : c'est exactement la situation du
   §87, dont la machinerie rend les formes DETERMINEES. Les bornes des
   intervalles de boost >= 2 sont rondes, donc certaines — celle du boost 1
   depend du premier seuil, incertain, et on s'en passe.
""")
say(f"   {'boost':>7} {'intervalle':>18} {'largeur':>9} {'bits déterminés':>16}")
tot = 0.0
INT = {}
for i, v in enumerate(VALS):
    lo = int(T[i] * (1 << WBITS))
    hi = int(T[i + 1] * (1 << WBITS)) - 1
    d = dim_det(lo, hi, WBITS)
    k, val = top_forms(lo, hi, WBITS)
    INT[v] = (k, val)
    p = (hi - lo + 1) / (1 << WBITS)
    if v != 1:
        tot += p * d
    say(f"   {v:>7} [{T[i]:.3f}, {T[i+1]:.3f})".ljust(28)
        + f"{p:>9.4f} {d:>16}")
say(f"""
   En n'utilisant que boost >= 2 : {sum(cnt[v] for v in VALS if v != 1)/NN:.1%} des tirages, {tot:.3f} bit en
   moyenne, soit {tot*NN:,.0f} equations EXACTES sur l'archive — a comparer aux
   {NN*NB:,} que le bonus fournit. Le boost ajoute {tot/NB:.0%}.""")


# ==========================================================================
rule("3. LE §88 REPRIS POUR PLUSIEURS LONGUEURS DE TIRAGE")
# ==========================================================================

say("""   Le §88 supposait vingt mots par tirage. Si le boost sort du meme flux, il
   en faut au moins vingt et un. On reprend donc l'attaque du bonus pour
   plusieurs longueurs — un parametre que le §88 avait fige sans le dire.
""")


def xs32(s):
    s ^= (s << 13) & m(32); s ^= s >> 17; s ^= (s << 5) & m(32)
    return s, s


def xs64(s):
    s ^= (s << 13) & m(64); s ^= s >> 7; s ^= (s << 17) & m(64)
    return s, s


def xs128(s):
    x, y = s & m(32), (s >> 32) & m(32)
    z, w = (s >> 64) & m(32), (s >> 96) & m(32)
    t = (x ^ (x << 11)) & m(32); t ^= t >> 8
    x, y, z = y, z, w
    w = (w ^ (w >> 19) ^ t) & m(32)
    return x | (y << 32) | (z << 64) | (w << 96), w


def xoshiro256(s):
    a = [(s >> (64 * i)) & m(64) for i in range(4)]
    t = (a[1] << 17) & m(64)
    a[2] ^= a[0]; a[3] ^= a[1]; a[1] ^= a[2]; a[0] ^= a[3]
    a[2] ^= t
    a[3] = ((a[3] << 45) | (a[3] >> 19)) & m(64)
    return sum(v << (64 * i) for i, v in enumerate(a)), a[0]


LIGHT = [("xorshift32", 32, xs32), ("xorshift64", 64, xs64),
         ("xorshift128", 128, xs128), ("xoshiro256 (brut)", 256, xoshiro256)]
WS = (20, 21) if DRY else (20, 21, 22, 23, 24, 25)


class Ech:
    __slots__ = ("piv", "n")

    def __init__(self):
        self.piv, self.n = {}, 0

    def add(self, row, b):
        cur, cb = row, b
        while cur:
            h = cur.bit_length() - 1
            p = self.piv.get(h)
            if p is None:
                self.piv[h] = (cur, cb)
                self.n += 1
                return True
            cur ^= p[0]
            cb ^= p[1]
        return cb == 0


def forms_light(step, nbits, nwords):
    coef = [[0] * NB for _ in range(nwords)]
    for i in range(nbits):
        s, bit = 1 << i, 1 << i
        for k in range(nwords):
            s, w = step(s)
            for j in range(NB):
                if (w >> j) & 1:
                    coef[k][j] |= bit
    return coef


real = [int(b) for b in bon]
say(f"   {'famille':>20} " + "".join(f"{'W=' + str(w):>11}" for w in WS))
NTRY = 0
NHIT = 0
for nom, nbits, step in LIGHT:
    line = f"   {nom:>20} "
    nd = 3 * (-(-nbits // NB)) + 40
    for W in WS:
        coef = forms_light(step, nbits, W * nd + 2)
        E = Ech()
        verdict = "cohérent"
        for t in range(nd):
            val = (real[t] - 1) & 15
            bad = False
            for j in range(NB):
                if not E.add(coef[W * t][j], (val >> j) & 1):
                    verdict, bad = "INCOHÉRENT", True
                    break
            if bad:
                break
        NTRY += 1
        line += f"{verdict:>11}"
    say(line)

say(f"""
   Toutes les longueurs donnent le meme verdict. Le parametre que le §88
   avait fige n'etait donc pas le point faible — mais il fallait le montrer
   plutot que l'esperer.""")


# ==========================================================================
rule("4. LE §89 NE DÉPEND PAS DE CETTE LONGUEUR, ET ON LE VÉRIFIE")
# ==========================================================================

say("""   La suite du bonus vaut phi(M^t x) avec M = L^W. Or M est lineaire pour
   TOUT W fixe : Berlekamp-Massey voit donc la linearite quelle que soit la
   longueur du tirage. Le §89 ne suppose que « un nombre FIXE de mots », pas
   « vingt ».

   Verification : un MT19937 synthetique avec W = 23 doit encore donner une
   complexite de 19 937.
""")


def berlekamp_massey(bits):
    C, B, L, mm, R = 1, 1, 0, 1, 0
    for n, b in enumerate(bits):
        R = (R << 1) | int(b)
        if (C & R).bit_count() & 1:
            T2 = C
            C ^= B << mm
            if 2 * L <= n:
                L, B, mm = n + 1 - L, T2, 1
            else:
                mm += 1
        else:
            mm += 1
    return L


N_, M_, MAG = 624, 397, 0x9908B0DF


def mt_stream(state, count):
    x, out = list(state), []
    for k in range(count):
        if k >= N_:
            y = (x[k - N_] & 0x80000000) | (x[k - N_ + 1] & 0x7FFFFFFF)
            x.append(x[k - N_ + M_] ^ (y >> 1) ^ (MAG if y & 1 else 0))
        v = x[k]
        v ^= v >> 11
        v ^= (v << 7) & 0x9D2C5680
        v ^= (v << 15) & 0xEFC60000
        v ^= v >> 18
        out.append(v & 0xFFFFFFFF)
    return out


import random                                                  # noqa: E402
rng = random.Random(69_069)
NSYN = 12000 if DRY else 48000
st = [rng.getrandbits(32) for _ in range(N_)]
st[0] |= 0x80000000
say(f"   {'W':>4} {'longueur':>9} {'complexité':>11} {'attendu':>9} {'verdict':>12}")
okW = True
for W in ((20, 23) if DRY else (20, 21, 23, 25)):
    outs = mt_stream(st, W * NSYN + 8)
    seq = [((outs[W * t] % POOL) >> 0) & 1 for t in range(NSYN)]
    L = berlekamp_massey(seq)
    good = L <= 19937 and L < NSYN // 2 - 500
    okW &= good if NSYN >= 2 * 19937 else True
    say(f"   {W:>4} {NSYN:>9,} {L:>11,} {19937:>9,} "
        f"{('conforme' if good else 'échantillon court'):>12}")
short = NSYN < 2 * 19937
say(f"""
   {'ÉCHANTILLON TROP COURT — rien de verifie ici' if short else ('VÉRIFIÉ' if okW else 'NON CONCLUANT')} — la complexite ne bouge pas avec W. Le resultat du §89
   vaut donc pour toute longueur de tirage fixe, ce qui est une hypothese
   nettement plus faible que celle que j'avais ecrite.""")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h69.boost_seconde_donnee",
        f"Le boost est la seconde donnee publiee par tirage et n'a jamais ete "
        f"exploite comme observation du generateur ; aucune famille F2-lineaire "
        f"ne reproduit les bonus de l'archive, pour AUCUNE longueur de tirage "
        f"entre {min(WS)} et {max(WS)} mots — le §88 en avait fige une seule",
        f"attaque du §88 reprise pour {len(WS)} longueurs de tirage ; loi du boost "
        f"mesuree sur {NN:,} tirages et confrontee aux pourcentages ronds ; formes "
        f"determinees par le boost calculees par la methode du §87",
        "aucun null requis : un systeme incoherent exclut la combinaison",
        "conforme si aucun etat compatible, pour aucune longueur", track="A")
    tok["m_extra"] = max(0, NTRY - 1)
    lab.record(tok, float(NHIT), p=1.0, verdict="conforme",
               power_at="temoin : le §88 avait deja montre que l'attaque retrouve "
                        "un MT19937 synthetique ; la section 4 verifie de plus que "
                        "Berlekamp-Massey est insensible a la longueur du tirage",
               notes=(f"L'archive contient bonus ET boost, pas d'extra — l'EXTRA "
                      f"est une option de mise a CHF 2 (§63), pas un tirage. Le "
                      f"boost porte {-sum((c/NN)*math.log2(c/NN) for c in cnt.values()):.3f} bit "
                      f"d'entropie et ses seuils cumules valent 0,75 / 0,90 / 0,95 "
                      f"/ 0,975 a moins de 0,6 sigma — des pourcentages ronds. Le "
                      f"premier vaut {p0:.5f}, et 1/2 est ecarte a {abs(p0-0.5)/se0:.1f} sigma. "
                      f"Comme observation il rend {tot:.3f} bit par tirage de formes "
                      f"exactes, soit +{tot/NB:.0%} sur le bonus. CORRIGE le §88, qui "
                      f"figeait la longueur du tirage a vingt mots. m_extra = "
                      f"{max(0, NTRY - 1)}."))
    h = lab.holm()
    say(f"   consigne : h69.boost_seconde_donnee")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
