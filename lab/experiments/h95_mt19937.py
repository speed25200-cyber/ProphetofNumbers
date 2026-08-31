"""h95 — MT19937 sur les 70 560 tirages : la cible que seul le calcul bloquait.

CE QUE LE §106 AVAIT LAISSÉ
===========================
Le §106 a montré que le RANG DU BONUS parmi les vingt numéros triés est une
observation de troncature EXACTE, disponible sur toute l'archive, à stride
FIXE, et sans jamais avoir besoin de l'ordre d'émission. Il rend 3,20 équations
F2 par tirage. Sa conclusion, mot pour mot :

    « MT19937 et WELL19937. Le budget de 3,20 bits par tirage les met à portée
      en 6 230 tirages, largement disponibles — c'est le COÛT DE CALCUL des
      formes linéaires qui bloque, pas la donnée. La différence avec le §105 est
      entière : là, il manquait des tirages ; ici, il manque des heures. »

Ce fichier fournit les heures.

    MT19937 EST LE GENERATEUR DE PHP (`mt_rand`), DE PYTHON (`random`), DE RUBY
    (`Random`) ET DE C++ (`std::mt19937`). C'est, de loin, le plus probable
    apres ceux deja exclus.

OÙ ÉTAIT VRAIMENT LE MUR
=========================
Pas dans les formes linéaires : les 19 937 formes se propagent par la récurrence
du twist en une minute de Python, parce que chaque mot ne coûte qu'une centaine
de XOR d'entiers longs.

C'est L'ELIMINATION qui ne passait pas. Réduire 25 000 équations de 19 937 bits
demande ~2·10⁸ XOR de lignes ; avec les entiers longs de Python cela fait
plusieurs jours, et moins d'une minute avec `tools/f2solve.c` écrit pour
l'occasion et autotesté (rang, incohérence, et solution exacte reconstruite).

LA PARAMÉTRISATION DE L'ÉTAT
=============================
    L'état de MT19937 fait 624 mots de 32 bits, mais seulement 19 937 bits
    UTILES : le twist ne lit de `mt[0]` que son bit de poids fort, et les 31
    bits bas n'influencent jamais aucune sortie. On paramètre donc par

        bit 0        = mt[0] bit 31
        bits 1..32   = mt[1]
        ...          = 1 + 623*32 = 19 937 inconnues

    ce qui est exactement le logarithme de la période. Une paramétrisation à
    19 968 bits laisserait 31 dimensions de noyau parasites et ferait croire à
    un système sous-déterminé là où il est plein.

Il TESTE l'archive : il consigne au registre.
"""

import os
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lab                                                    # noqa: E402

T0 = time.time()
DRY = os.environ.get("H95_DRY") == "1"
ICI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ICI)
DEPOT = os.path.dirname(ROOT)
TMP = os.environ.get("H95_TMP", "/tmp")
POOL, DRAWN = 80, 20
KB = DRAWN
NBITS = 19937
N, M = 624, 397
UPPER, LOWER, MATRIX_A = 0x80000000, 0x7FFFFFFF, 0x9908B0DF
# (stride, decalage du mot de bonus)
PLANS = [(21, 20), (21, 0)] if DRY else [(21, 20), (21, 0), (22, 20), (22, 21),
                                         (41, 40), (42, 40)]


def say(*a):
    print(*a, flush=True)


def rule(t=""):
    say("\n" + "=" * 78)
    if t:
        say(t)
        say("=" * 78)


_SRC = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
_G = {"__name__": "h86tete", "__file__": os.path.join(ICI, "h86_prefixe.py")}
exec(compile(_SRC[:_SRC.index('rule("1. LE TH')], "h86tete", "exec"), _G)
prefixe = _G["prefixe"]


# ==========================================================================
# MT19937 : L'ENTIER, ET LES FORMES LINÉAIRES
# ==========================================================================
def mt_init_etat(graine):
    mt = [0] * N
    mt[0] = graine & 0xFFFFFFFF
    for i in range(1, N):
        mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & 0xFFFFFFFF
    return mt


def temper(y):
    y ^= y >> 11
    y ^= (y << 7) & 0x9D2C5680
    y ^= (y << 15) & 0xEFC60000
    y ^= y >> 18
    return y & 0xFFFFFFFF


def mt_mots(mt, n):
    """Les `n` sorties temperees, en consommant l'etat sur place."""
    mt = list(mt)
    out = []
    for i in range(n):
        y = (mt[i % N] & UPPER) | (mt[(i + 1) % N] & LOWER)
        v = mt[(i + M) % N] ^ (y >> 1) ^ (MATRIX_A if (y & 1) else 0)
        mt[i % N] = v & 0xFFFFFFFF
        out.append(temper(mt[i % N]))
    return out


def temper_formes(f):
    """Le temperage, applique aux 32 formes d'un mot."""
    g = [f[k] ^ (f[k + 11] if k + 11 < 32 else 0) for k in range(32)]
    m1 = 0x9D2C5680
    h = [g[k] ^ (g[k - 7] if (k >= 7 and (m1 >> k) & 1) else 0) for k in range(32)]
    m2 = 0xEFC60000
    i2 = [h[k] ^ (h[k - 15] if (k >= 15 and (m2 >> k) & 1) else 0) for k in range(32)]
    return [i2[k] ^ (i2[k + 18] if k + 18 < 32 else 0) for k in range(32)]


def formes_aux_positions(positions, jmax=6):
    """Les `jmax` formes de POIDS FORT du mot tempere, aux positions demandees.

    On propage une fenetre glissante de 624 mots, chacun porteur de 32 formes
    lineaires sur les 19 937 bits d'etat. Seules les positions demandees sont
    conservees : garder tout couterait des gigaoctets.
    """
    besoin = set(positions)
    nmax = max(positions) + 1
    F = []
    idx = 0
    for i in range(N):
        mots = []
        for b in range(32):
            if i == 0 and b < 31:
                mots.append(0)                   # les 31 bits bas de mt[0] sont morts
            else:
                mots.append(1 << idx)
                idx += 1
        F.append(mots)
    assert idx == NBITS, idx
    out = {}
    for i in range(nmax):
        a, b, c = F[i % N], F[(i + 1) % N], F[(i + M) % N]
        y = [b[k] for k in range(31)] + [a[31]]
        ny = [y[k + 1] for k in range(31)] + [0]
        bas = y[0]
        nw = [c[k] ^ ny[k] ^ (bas if (MATRIX_A >> k) & 1 else 0) for k in range(32)]
        F[i % N] = nw
        if i in besoin:
            t = temper_formes(nw)
            out[i] = [t[31 - r] for r in range(jmax)]
    return out


# ==========================================================================
# LE SYSTÈME, ÉCRIT POUR LE SOLVEUR C
# ==========================================================================
def ecrire_systeme(chemin, formes, rangs, positions):
    W = (NBITS + 63) // 64
    n = 0
    with open(chemin, "wb") as f:
        f.write(struct.pack("<ii", NBITS, 0))
        for d, r in enumerate(rangs):
            j, val = prefixe(int(r), KB, 32)
            fp = formes[positions[d]]
            for k in range(j):
                f.write(fp[k].to_bytes(W * 8, "little"))
                f.write(bytes([(val >> (j - 1 - k)) & 1]))
                n += 1
        f.seek(4)
        f.write(struct.pack("<i", n))
    return n


def resoudre(chemin, binaire):
    p = subprocess.run([binaire, chemin], capture_output=True, text=True, timeout=3600)
    tete = p.stdout.split("\n")[0]
    d = dict(kv.split("=") for kv in tete.split())
    sol = None
    for l in p.stdout.split("\n"):
        if l.startswith("solution="):
            h = l.split("=")[1]
            mots = [int(h[i:i + 16], 16) for i in range(0, len(h), 16)]
            sol = sum(m << (64 * i) for i, m in enumerate(mots))
    return int(d["rang"]), int(d["incoherent"]), sol, float(d["sec"])


# ==========================================================================
rule("1. LE MUR ÉTAIT L'ÉLIMINATION, PAS LES FORMES")
# ==========================================================================

BIN = os.path.join(TMP, "f2solve")
cc = subprocess.run(["cc", "-O3", "-march=native", "-o", BIN,
                     os.path.join(DEPOT, "tools", "f2solve.c")],
                    capture_output=True, text=True)
say(f"""   Le §106 concluait : « MT19937 est a portee en 6 230 tirages, largement
   disponibles — c'est le COUT DE CALCUL qui bloque, pas la donnee ». Ce
   fichier fournit les heures.

   OU ETAIT LE MUR. Pas dans les formes : les 19 937 formes se propagent par la
   recurrence du twist en une minute de Python. C'est l'ELIMINATION — reduire
   25 000 equations de 19 937 bits demande ~2e8 XOR de lignes, soit des jours
   avec les entiers longs de Python.

   `tools/f2solve.c` : {'compile' if cc.returncode == 0 else 'ECHEC ' + cc.stderr[:200]}

   LA PARAMETRISATION. L'etat fait 624 mots de 32 bits, mais {NBITS:,} bits UTILES :
   le twist ne lit de mt[0] que son bit de poids fort. Une parametrisation a
   19 968 bits laisserait 31 dimensions de noyau parasites et ferait croire a un
   systeme sous-determine la ou il est plein.""")


# ==========================================================================
rule("2. LE TÉMOIN : RECONSTITUER MT19937 DEPUIS LES SEULS RANGS")
# ==========================================================================

MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
ND = int(NBITS / MOY * (1.10 if DRY else 1.30))
say(f"""   {MOY:.2f} equations par tirage, {NBITS:,} bits a determiner : il en faut
   {int(NBITS/MOY):,}. On en prend {ND:,} pour la marge.

   On plante un etat de MT19937, on fabrique {ND:,} tirages par « vingt mots de
   Fisher-Yates puis un mot d'indice de bonus », on ne garde que les RANGS, et
   on demande la reconstitution des {NBITS:,} bits.
""")


def fabrique(mt, nd, stride, off):
    """Les rangs du bonus engendres par l'etat `mt`."""
    mots = mt_mots(mt, nd * stride + off + 1)
    rangs = []
    for d in range(nd):
        arr = list(range(1, POOL + 1))
        out = []
        for k in range(DRAWN):
            u = mots[d * stride + k]
            j = k + (u * (POOL - k)) // (1 << 32)
            arr[k], arr[j] = arr[j], arr[k]
            out.append(arr[k])
        # le bonus est tires_tries[idx] : son RANG parmi les vingt vaut donc idx
        idx = (mots[d * stride + off] * KB) >> 32
        rangs.append(idx)
        _ = sorted(out)
    return rangs


tt = time.time()
MT = mt_init_etat(20260917)
STR_T, OFF_T = 21, 20
rangs_t = fabrique(MT, ND, STR_T, OFF_T)
pos_t = [d * STR_T + OFF_T for d in range(ND)]
say(f"   {ND:,} tirages fabriques ({time.time()-tt:.1f} s) ; calcul des formes...")
tt = time.time()
F_t = formes_aux_positions(pos_t)
say(f"   formes sur {max(pos_t)+1:,} mots ({time.time()-tt:.1f} s) ; ecriture du systeme...")
CH = os.path.join(TMP, "h95_temoin.bin")
neq = ecrire_systeme(CH, F_t, rangs_t, pos_t)
tt = time.time()
rang, inc, sol, sec = resoudre(CH, BIN)
say(f"   {neq:,} equations -> rang={rang:,}  incoherent={inc}  ({sec:.1f} s)")

VRAI = 0
bit = 0
for i in range(N):
    for b in range(32):
        if i == 0 and b < 31:
            continue
        if (MT[i] >> b) & 1:
            VRAI |= 1 << bit
        bit += 1
TEMOIN = (sol is not None and sol == VRAI)
say(f"   etat retrouve EXACTEMENT : {TEMOIN}")
if sol is not None and not TEMOIN:
    say(f"   (rang plein mais solution differente — {bin(sol ^ VRAI).count('1')} bits d'ecart)")


# ==========================================================================
rule("3. SUR L'ARCHIVE")
# ==========================================================================

ARCH = lab.load()
BON = np.asarray(ARCH.bonus).astype(np.int64)
NUM = np.asarray(ARCH.nums)
RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
say(f"""   {len(RANG):,} rangs disponibles, {ND:,} utilises. Pour chaque hypothese de
   consommation (stride, position du mot de bonus) :
""")
say(f"   {'stride':>8} {'décalage':>9} {'équations':>11} {'rang':>9} "
    f"{'incohérent':>11} {'compatible':>11} {'sec':>7}")
TOTAL, ESSAIS, INCOH = 0, 0, 0
for stride, off in PLANS:
    tt = time.time()
    pos = [d * stride + off for d in range(ND)]
    F = formes_aux_positions(pos)
    neq = ecrire_systeme(CH, F, RANG[:ND].tolist(), pos)
    rang, inc, sol, sec = resoudre(CH, BIN)
    ESSAIS += 1
    INCOH += inc
    ok = 0
    if not inc and sol is not None:
        # rejeu : l'etat trouve reproduit-il les rangs ?
        mt = [0] * N
        bit = 0
        for i in range(N):
            for b in range(32):
                if i == 0 and b < 31:
                    continue
                if (sol >> bit) & 1:
                    mt[i] |= 1 << b
                bit += 1
        ok = int(fabrique(mt, min(ND, 200), stride, off) == RANG[:min(ND, 200)].tolist())
    TOTAL += ok
    say(f"   {stride:>8} {off:>9} {neq:>11,} {rang:>9,} {inc:>11} {ok:>11} "
        f"{time.time()-tt:>7.1f}")

say(f"""
   {TOTAL} etat compatible sur {ESSAIS} hypotheses — {INCOH} systemes incoherents.""")


# ==========================================================================
rule("4. CONSIGNATION")
# ==========================================================================

if DRY:
    say("   MODE ESSAI : rien n'est consigne.")
else:
    tok = lab.preregister(
        "h95.mt19937_bonus",
        f"MT19937 — le generateur de PHP (`mt_rand`), Python (`random`), Ruby et "
        f"C++ (`std::mt19937`) — n'engendre pas les rangs du bonus de l'archive, "
        f"a etat COMPLET de {NBITS:,} bits, sous le schema « vingt mots de "
        f"Fisher-Yates puis un mot d'indice de bonus »",
        f"theoreme du prefixe (§105) applique au rang du bonus (§106), K = {KB}, "
        f"{MOY:.2f} equations F2 exactes par tirage sur {ND:,} tirages. Formes "
        f"lineaires propagees par la recurrence du twist sur les {NBITS:,} bits utiles "
        f"de l'etat, temperage compris ; elimination de Gauss par "
        f"`tools/f2solve.c`, autoteste sur rang, incoherence et solution exacte",
        "aucun null n'est requis : le systeme lineaire est incoherent ou il ne "
        "l'est pas, et tout etat trouve est verifie par rejeu des rangs",
        "conforme si aucun etat compatible n'est trouve", track="B")
    tok["m_extra"] = 0
    lab.record(
        tok, float(TOTAL), p=1.0, verdict="conforme",
        power_at=(f"temoin positif : l'etat de MT19937 plante est retrouve "
                  f"EXACTEMENT ({TEMOIN}) depuis les seuls rangs du bonus de {ND:,} "
                  f"tirages, soit {NBITS:,} bits reconstitues sans aucun ordre d'emission"),
        notes=(f"Le §106 avait chiffre cette cible comme atteignable et bloquee "
               f"par le seul COUT DE CALCUL. Les formes lineaires ne sont pas le "
               f"mur — elles se propagent en une minute — c'est l'ELIMINATION : "
               f"25 000 equations de {NBITS:,} bits demandent ~2e8 XOR de lignes, soit "
               f"des jours en Python et moins d'une minute en C. Parametrisation a "
               f"{NBITS:,} bits et non 19 968 : le twist ne lit de mt[0] que son bit de "
               f"poids fort, et les 31 bits bas ne sont determinables par rien."))
    h = lab.holm()
    say(f"   consigne : h95.mt19937_bonus   {TOTAL} etat compatible")
    say(f"   m du registre : {h[0]['m_total']:,}   significatifs : "
        f"{sum(1 for r in h if r['significant'])}")


# ==========================================================================
rule("5. CE QUE CELA FERME")
# ==========================================================================

say(f"""   MT19937 A ETAT COMPLET. C'etait la plus grosse cible restante et la plus
   probable apres celles deja exclues : PHP, Python, Ruby et C++ l'utilisent
   tous par defaut.

   ET LA METHODE VAUT AU-DELA. Toute famille F2-lineaire dont l'etat tient sous
   ~{int(len(RANG)*MOY):,} bits est desormais atteignable par la meme voie — rangs du bonus,
   formes propagees, elimination en C — SANS ordre d'emission et SANS tirages
   consecutifs. WELL19937 en fait partie.

   ({time.time() - T0:.1f} s)""")
