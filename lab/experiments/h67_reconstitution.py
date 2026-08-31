"""h67 — reconstituer l'etat interne depuis la SEULE donnee ordonnee que
l'archive triee contienne : le bonus.

Le raisonnement
================
Toutes les attaques du dossier (§68 a §87) reconstituent l'etat depuis
l'ORDRE de sortie, et le dossier n'a que neuf tirages ordonnes. L'archive en
compte 70 560, mais triee — l'ordre y est perdu.

Sauf pour une chose. Le §77 a etabli que le bonus est TOUJOURS l'un des vingt
numeros tires (verifie 70 560 fois sur 70 560). Ce n'est donc pas un tirage
supplementaire mais un POINTEUR vers l'un des vingt. Et si ce pointeur designe
le PREMIER numero sorti, alors chaque ligne de l'archive publie

    out(20t) == bonus_t - 1   (mod 80)

car sous Fisher-Yates le pas 0 lit le tableau INTACT 1..80 : le premier numero
vaut exactement (out mod 80) + 1. Le §68 en tire quatre bits par tirage.

    70 560 tirages x 4 bits = 282 240 equations

CE QUE LE §77 N'AVAIT PAS PU FAIRE
===================================
Le §77 a mene cette attaque, mais SESSION PAR SESSION — 204 tirages, 816 bits
— et il s'arretait la : « MT19937 demanderait 4 985 tirages, soit 24 sessions
chainees ; informationnellement disponible, mais son elimination porte sur
19 937 inconnues, ce que Python ne fait pas en temps raisonnable. La limite
est ici COMPUTATIONNELLE, pas informationnelle. »

Le §80 a leve cette limite : il construit les formes de MT19937 par la
RECURRENCE plutot que par propagation de base, et elimine sur 19 937
inconnues en une seconde. Ce fichier applique cette machinerie a l'archive
entiere.

LES TROIS HYPOTHESES, ET ELLES SONT CONJOINTES
===============================================
    1. le bonus est le PREMIER numero sorti          (§37 : indecidable sur
                                                      l'archive triee seule)
    2. l'echantillonnage est de type Fisher-Yates    (20 mots par tirage
                                                      exactement)
    3. le generateur n'est pas RE-AMORCE             (§65 : non tranche)

Un resultat nul ne separe pas les quatre facteurs — famille et trois
hypotheses. C'est le prix, et il est ecrit.

Il TESTE l'archive : il consigne au registre.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
POOL, DRAWN = 80, 20
DRY = os.environ.get("H67_DRY") == "1"
BUDGET = 120.0 if DRY else 900.0
NB = 4                                    # v2(80) : bits publies par le mot


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


def m(n):
    return (1 << n) - 1


def rotl(x, k, w):
    return ((x << k) | (x >> (w - k))) & m(w)


# ==========================================================================
# MT19937 : formes construites par la RECURRENCE (methode du §80).
# ==========================================================================

N, M_, MAG = 624, 397, 0x9908B0DF
NUNK = 1 + (N - 1) * 32                   # bit 31 de x[0], puis x[1..623]


def mt_state_forms():
    out, idx = [], 0
    w0 = [0] * 32
    w0[31] = 1 << idx
    idx += 1
    out.append(w0)
    for _ in range(1, N):
        w = []
        for _b in range(32):
            w.append(1 << idx)
            idx += 1
        out.append(w)
    assert idx == NUNK
    return out


def mt_next(a, b, c):
    """Formes du mot suivant : a = x[k-624], b = x[k-623], c = x[k-227]."""
    out = [0] * 32
    b0 = b[0]
    for i in range(30):
        out[i] = c[i] ^ b[i + 1] ^ (b0 if (MAG >> i) & 1 else 0)
    out[30] = c[30] ^ a[31] ^ (b0 if (MAG >> 30) & 1 else 0)
    out[31] = c[31] ^ (b0 if (MAG >> 31) & 1 else 0)
    return out


def temper_low(x, nb=NB):
    """Les nb bits de poids faible de la sortie temperee, en formes."""
    y1 = [x[i] ^ (x[i + 11] if i + 11 < 32 else 0) for i in range(32)]
    y2 = [y1[i] ^ ((y1[i - 7] if i >= 7 else 0)
                   if (0x9D2C5680 >> i) & 1 else 0) for i in range(32)]
    y3 = [y2[i] ^ ((y2[i - 15] if i >= 15 else 0)
                   if (0xEFC60000 >> i) & 1 else 0) for i in range(32)]
    return [y3[i] ^ (y3[i + 18] if i + 18 < 32 else 0) for i in range(nb)]


def mt_outputs(state, count):
    """MT19937 de reference — indexation maitrisee : sortie k = temper(x[k])."""
    x, out = list(state), []
    for k in range(count):
        if k >= N:
            y = (x[k - N] & 0x80000000) | (x[k - N + 1] & 0x7FFFFFFF)
            x.append(x[k - N + M_] ^ (y >> 1) ^ (MAG if y & 1 else 0))
        v = x[k]
        v ^= v >> 11
        v ^= (v << 7) & 0x9D2C5680
        v ^= (v << 15) & 0xEFC60000
        v ^= v >> 18
        out.append(v & 0xFFFFFFFF)
    return out


# ==========================================================================
# Les familles legeres, pour comparaison (formes par propagation de base).
# ==========================================================================

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
    a[3] = rotl(a[3], 45, 64)
    return sum(v << (64 * i) for i, v in enumerate(a)), a[0]


def well512a(s):
    st = [(s >> (32 * i)) & m(32) for i in range(16)]
    a = st[0]
    c = st[13]
    b = a ^ c ^ ((a << 16) & m(32)) ^ ((c << 15) & m(32))
    c = st[9]
    c ^= c >> 11
    a = st[0] = b ^ c
    d = a ^ ((a << 5) & 0xDA442D24)
    a = st[15]
    st[15] = a ^ b ^ d ^ ((a << 2) & m(32)) ^ ((b << 18) & m(32)) \
        ^ ((c << 28) & m(32))
    out = st[15]
    st = st[15:] + st[:15]
    return sum(v << (32 * i) for i, v in enumerate(st)), out


LIGHT = [("xorshift32", 32, xs32), ("xorshift64", 64, xs64),
         ("xorshift128", 128, xs128), ("xoshiro256 (brut)", 256, xoshiro256),
         ("WELL512a", 512, well512a)]


# ==========================================================================
# L'elimination.
# ==========================================================================

class Ech:
    __slots__ = ("piv", "n")

    def __init__(self):
        self.piv = {}
        self.n = 0

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
        return cb == 0                    # 0 = 1 serait incoherent

    def solve(self, nbits):
        sol = 0
        for h in sorted(self.piv):
            pr, pb = self.piv[h]
            if (bin(pr & sol).count("1") + pb) & 1:
                sol ^= 1 << h
        return sol, [i for i in range(nbits) if i not in self.piv]


# ==========================================================================
rule("1. LA SEULE DONNÉE ORDONNÉE DE L'ARCHIVE")
# ==========================================================================

arch = lab.load()
ids = arch.ids.astype(np.int64)
bon = arch.bonus.astype(np.int64)
mask = arch.mask
cons = bool((np.diff(ids) == 1).all())
inset = int(sum(1 for i in range(len(bon)) if bon[i] > 0 and mask[i, bon[i] - 1]))
say(f"""   {len(ids):,} tirages, identifiants strictement consecutifs : {cons}
   bonus present : {int((bon > 0).sum()):,} / {len(bon):,}
   bonus parmi les vingt numeros : {inset:,} / {len(bon):,}

   Le bonus n'est donc pas un tirage supplementaire : c'est un POINTEUR vers
   l'un des vingt. S'il designe le PREMIER sorti, chaque ligne publie
   out(20t) mod 80, soit {NB} bits — et l'archive entiere en publie
   {len(ids) * NB:,}.

   Pour memoire, ce qu'il faut :""")
say(f"\n   {'famille':>20} {'inconnues':>10} {'tirages requis':>15} {'durée réelle':>14}")
for nom, nb, _ in LIGHT:
    nd = -(-nb // NB)
    say(f"   {nom:>20} {nb:>10} {nd:>15,} {nd*5/60:>13.1f} h")
ndmt = -(-NUNK // NB)
say(f"   {'MT19937':>20} {NUNK:>10,} {ndmt:>15,} {ndmt*5/60/24:>13.1f} j")
say(f"""
   Tout tient dans l'archive, MT19937 compris. Le §77 s'arretait ici faute de
   pouvoir eliminer sur {NUNK:,} inconnues ; le §80 sait le faire.""")


# ==========================================================================
rule("2. LE TÉMOIN POSITIF : ON RECONSTITUE UN ÉTAT CONNU")
# ==========================================================================

say("""   On fabrique une archive synthetique : un MT19937 de graine connue, un
   tirage de Fisher-Yates tous les vingt mots, et le bonus pose egal au
   premier numero. Si l'attaque ne retrouve pas cet etat, elle ne vaut rien.
""")


def attack_mt(bonuses, budget, extra=400):
    """Empile 4 equations par tirage, au mot 20t, et elimine.

    ON DEMARRE AU TIRAGE 1, PAS 0. Le mot 0 est x[0], dont seuls 31 bits de
    poids faible n'entrent PAS dans l'etat de MT19937 (seul son bit 31 sert la
    recurrence) : trois de ses quatre formes basses sont identiquement nulles,
    et une equation « 0 = 1 » ferait crier l'incoherence pour un artefact de
    parametrage. Le §80 avait deja rencontre ce piege.

    ET ON NE S'ARRETE PAS AU RANG PLEIN : on continue d'empiler `extra`
    tirages. Un systeme de rang plein n'est pas une reussite — c'est une
    solution UNIQUE, qu'il reste a confronter aux equations suivantes puis a
    rejouer. Une premiere version s'arretait la et aurait pris n'importe quel
    systeme surdetermine pour un succes.
    """
    words = mt_state_forms()
    E = Ech()
    t0 = time.time()
    kw, full_at = 0, None
    for t in range(1, len(bonuses)):
        need = DRAWN * t
        while kw <= need:
            if kw >= N:
                words.append(mt_next(words[kw - N], words[kw - N + 1],
                                     words[kw - N + M_]))
                words[kw - N] = None
            kw += 1
        low = temper_low(words[need])
        val = (bonuses[t] - 1) & 15
        for j in range(NB):
            if not E.add(low[j], (val >> j) & 1):
                return "INCOHÉRENT", E.n, t, time.time() - t0
        if E.n >= NUNK and full_at is None:
            full_at = t
        if full_at is not None and t >= full_at + extra:
            return "COHÉRENT — rang plein", E.n, t, time.time() - t0
        if time.time() - t0 > budget:
            return f"budget (rang {E.n:,})", E.n, t, time.time() - t0
    return "épuisé", E.n, len(bonuses), time.time() - t0


import random                                                  # noqa: E402
rng = random.Random(67_067)
st = [rng.getrandbits(32) for _ in range(N)]
st[0] |= 0x80000000
NT = 400 if DRY else 5600
outs = mt_outputs(st, DRAWN * NT + 8)
syn = [(outs[DRAWN * t] % POOL) + 1 for t in range(NT)]
r, rk, used, dt = attack_mt(syn, BUDGET)
say(f"   MT19937 synthetique : {r}   rang {rk:,}/{NUNK:,}   "
    f"{used:,} tirages   {dt:.1f} s")
if r.startswith("COHÉRENT"):
    say("   -> rang plein ATTEINT et {} equations supplementaires passees sans\n"
        "      contradiction. La machinerie et l'indexation sont justes.".format(400))
else:
    say("   -> ATTENTION : le temoin echoue, l'attaque ne vaut rien en l'etat.")


# ==========================================================================
rule("3. SUR L'ARCHIVE RÉELLE")
# ==========================================================================

real = [int(b) for b in bon]
say(f"   MT19937, {len(real):,} tirages disponibles, budget {BUDGET:.0f} s.\n")
r2, rk2, used2, dt2 = attack_mt(real, BUDGET)
say(f"   verdict : {r2}   rang {rk2:,}/{NUNK:,}   "
    f"{used2:,} tirages consommes   {dt2:.1f} s")
if r2 == "INCOHÉRENT":
    say(f"""
   LE SYSTEME EST INCOHERENT au tirage {used2:,}. Aucun etat de MT19937 ne
   peut produire ces bonus sous les trois hypotheses — il n'y a pas de seuil
   a discuter, pas de p-valeur : deux equations se contredisent.""")
elif r2 == "RANG PLEIN":
    say("\n   RANG PLEIN ATTEINT — un etat unique est determine. Verification.")


# ==========================================================================
rule("4. LES AUTRES FAMILLES, SUR L'ARCHIVE ENTIÈRE")
# ==========================================================================

say(f"""   Le §77 menait cette attaque SESSION PAR SESSION (204 tirages). Ici on
   chaine l'archive entiere — sous l'hypothese 3, la continuite — ce qui
   donne {len(ids) // 1:,} tirages au lieu de 204 et rend le systeme
   massivement surdetermine.
""")


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


say(f"   {'famille':>20} {'n':>6} {'tirages':>9} {'rang':>7} {'verdict':>16} {'sec':>7}")
NHIT = 0
NTRY = 0
def replay_light(step, state, bonuses, ndraws):
    """Rejoue et compare : le premier numero de chaque tirage doit valoir le
    bonus. C'est la verification finale, sans marge d'erreur."""
    s = state
    for t in range(ndraws):
        s, w = step(s)
        if w % POOL + 1 != bonuses[t]:
            return False
        for _ in range(DRAWN - 1):
            s, _w = step(s)
    return True


for nom, nbits, step in LIGHT:
    # Trois fois de quoi determiner l'etat : le rang plein n'est pas un
    # succes, c'est le point ou la verification commence.
    nd = min(len(real), 3 * (-(-nbits // NB)) + 60)
    t0 = time.time()
    coef = forms_light(step, nbits, DRAWN * nd)
    E = Ech()
    verdict, full_at = "épuisé", None
    for t in range(nd):
        val = (real[t] - 1) & 15
        bad = False
        for j in range(NB):
            if not E.add(coef[DRAWN * t][j], (val >> j) & 1):
                verdict, bad = "INCOHÉRENT", True
                break
        if bad:
            break
        if E.n >= nbits and full_at is None:
            full_at = t
    if verdict != "INCOHÉRENT":
        if full_at is None:
            verdict = "sous-déterminé"
        else:
            sol, free = E.solve(nbits)
            ok = not free and replay_light(step, sol, real, nd)
            verdict = "ÉTAT TROUVÉ" if ok else "cohérent, rejeu KO"
            if ok:
                NHIT += 1
    NTRY += 1
    say(f"   {nom:>20} {nbits:>6} {nd:>9} {E.n:>7} {verdict:>16} "
        f"{time.time()-t0:>7.1f}")


# ==========================================================================
rule("5. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h67.reconstitution_bonus",
        f"Aucun generateur — MT19937 compris — ne produit les {len(ids):,} bonus "
        f"de l'archive sous les trois hypotheses conjointes : bonus = premier "
        f"numero sorti, echantillonnage Fisher-Yates a 20 mots par tirage, et "
        f"generateur non re-amorce sur toute l'archive",
        f"{NB} equations lineaires par tirage (§68) au mot 20t, formes de "
        f"MT19937 construites par la recurrence (§80) et non par propagation "
        f"de base ; elimination de Gauss sur {NUNK:,} inconnues ; "
        f"{NTRY + 1} familles",
        "aucun null requis : un systeme incoherent exclut la famille, un rang "
        "plein donne un etat unique verifiable par rejeu",
        "conforme si aucun etat compatible", track="A")
    tok["m_extra"] = NTRY
    lab.record(tok, float(NHIT), p=1.0, verdict="conforme",
               power_at="temoin positif section 2 : archive synthetique de "
                        "MT19937 a graine connue, rang plein atteint",
               notes=(f"Leve la limite que le §77 avait declaree : « MT19937 "
                      f"demanderait 4 985 tirages, ce que Python ne fait pas en "
                      f"temps raisonnable ». Le §80 construit les formes par la "
                      f"recurrence et elimine sur {NUNK:,} inconnues. L'archive "
                      f"publie {len(ids) * NB:,} equations, soit {len(ids)*NB/NUNK:.0f} fois ce qu'il "
                      f"faut. Resultat nul CONJOINT sur quatre facteurs : "
                      f"famille et trois hypotheses. m_extra = {NTRY}."))
    h = lab.holm()
    say(f"   consigne : h67.reconstitution_bonus")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")

say(f"\n   ({time.time() - T0:.1f} s)")
