"""h230 — WELL19937a SOUS LA TRONCATURE : le second nom de la phrase du §106
(RAPPORT §255).

LA PHRASE, ENCORE
=================
> *« RESTE : MT19937 **et WELL19937**. Le budget de 3,20 bits par tirage les met à portée en
>   6 230 tirages, largement disponibles — c'est le coût de calcul des formes linéaires qui
>   bloque, pas la donnée. »*

Le §254 a pris le premier. Voici le second, à la même machine, sous la même lecture — le rang
du bonus vaut `⌊u·20⌋` — et avec le même témoin.

LES FORMES PAR LA RÉCURRENCE, COMME AU §80
==========================================
WELL19937a est `F₂`-linéaire : chaque mot nouveau est une somme de décalages et de masques de
mots plus anciens. On fait donc tourner la récurrence **sur des formes** — un mot est une liste
de trente-deux entiers de `19 937` bits, un par position — exactement comme le §80 pour
MT19937. Aucune propagation de base ; le coût est celui de la récurrence elle-même.

Le générateur est transcrit **en miroir** du code de référence (Panneton, L'Ecuyer,
Matsumoto 2006, `WELL19937a.c`) : `R = 624`, `P = 31`, `M1 = 70`, `M2 = 179`, `M3 = 449`,

    z0    = (V[i-1] & 0x80000000) | (V[i-2] & 0x7fffffff)
    z1    = M0neg(25, V[i])  ^ M0pos(27, V[i+M1])
    z2    = M3pos(9, V[i+M2]) ^ M0pos(1, V[i+M3])
    V[i]  = z1 ^ z2                                        (newV1)
    V[i-1]= z0 ^ M0neg(9, z1) ^ M0neg(21, z2) ^ M0pos(21, V[i])   (newV0, la sortie)

avec `M0pos(t,v) = v ^ (v >> t)`, `M0neg(t,v) = v ^ (v << t)`, `M3pos(t,v) = v >> t`, et
l'indice qui **décroît** d'un cran par appel. Pas de tempérage pour la variante `a`.

CE QUE LE TÉMOIN PROUVE, ET CE QU'IL NE PROUVE PAS
=================================================
Deux contrôles, de portée différente, et il faut les distinguer :

  **formes contre entiers** — la version entière et la version en formes sont deux
     transcriptions du même algorithme ; on les fait tourner côte à côte sur un état tiré au
     hasard et l'on exige que les formes, évaluées à cet état, rendent exactement les mots
     entiers. Cela prouve que la propagation des formes est **juste par rapport à la
     transcription**.
  **le générateur planté** — un WELL19937a synthétique lu par la carte de rang doit être
     reconnu `COHÉRENT` à rang plein. Cela prouve que l'attaque **reconnaît ce qu'elle
     cherche**.

Ce que **rien** ici ne prouve : que ma transcription soit fidèle au `WELL19937a.c` publié.
Il n'y a pas d'implémentation de référence sur cette machine pour la confronter. Les
constantes sont celles que je tiens du code de référence, et une erreur de décalage ferait
tester un générateur que personne n'utilise. C'est dit ici plutôt que laissé à deviner.

LES 31 BITS QUI NE COMPTENT PAS
===============================
À chaque pas, `z0` ne lit que le bit `31` de `V[i−1]` — mot aussitôt écrasé par `newV0`. Ses
trente-et-un bits bas, à l'état initial, ne sont donc **jamais lus** : `624 × 32 − 31 = 19 937`
inconnues, exactement comme le bit `31` seul de `x[0]` compte pour MT19937.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICI = os.path.dirname(os.path.abspath(__file__))
POOL, DRAWN = 80, 20
KB = DRAWN
EXP_ID = "h230.well19937_sous_troncature"
FJETON = "/tmp/h230_jeton.json"
STRIDES = tuple(range(20, 42))
EXTRA = 300
R, M1, M2, M3 = 624, 70, 179, 449
MASKU, MASKL = 0x7FFFFFFF, 0x80000000
NUNK = R * 32 - 31


def say(*a):
    print(*a, flush=True)


_H86 = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
exec(compile(_H86[_H86.index("def prefixe("):_H86.index("def indices_fy(")],
             "h86prefixe", "exec"), globals())
_H67 = open(os.path.join(ICI, "h67_reconstitution.py"), encoding="utf-8").read()
exec(compile(_H67[_H67.index("class Ech:"):_H67.index("# =====", _H67.index("class Ech:"))],
             "h67ech", "exec"), globals())


# --------------------------------------------------------------- version ENTIERE
def m0pos(t, v):
    return (v ^ (v >> t)) & 0xFFFFFFFF


def m0neg(t, v):
    return (v ^ (v << t)) & 0xFFFFFFFF


def m3pos(t, v):
    return (v >> t) & 0xFFFFFFFF


def well_int(S, i):
    """un pas de WELL19937a sur des entiers ; rend (i suivant, mot de sortie)."""
    V0, VM1, VM2, VM3 = S[i], S[(i + M1) % R], S[(i + M2) % R], S[(i + M3) % R]
    VRm1, VRm2 = S[(i - 1) % R], S[(i - 2) % R]
    z0 = (VRm1 & MASKL) | (VRm2 & MASKU)
    z1 = m0neg(25, V0) ^ m0pos(27, VM1)
    z2 = m3pos(9, VM2) ^ m0pos(1, VM3)
    nv1 = z1 ^ z2
    nv0 = z0 ^ m0neg(9, z1) ^ m0neg(21, z2) ^ m0pos(21, nv1)
    S[i] = nv1
    S[(i - 1) % R] = nv0
    return (i - 1) % R, nv0


# --------------------------------------------------------------- version en FORMES
# un mot = liste de 32 formes, formes[b] = entier de NUNK bits, bit b du mot (b = 0 : LSB)
def f_m0pos(t, v):
    return [v[b] ^ (v[b + t] if b + t < 32 else 0) for b in range(32)]


def f_m0neg(t, v):
    return [v[b] ^ (v[b - t] if b - t >= 0 else 0) for b in range(32)]


def f_m3pos(t, v):
    return [(v[b + t] if b + t < 32 else 0) for b in range(32)]


def f_xor(*ws):
    return [sum_xor(b, ws) for b in range(32)]


def sum_xor(b, ws):
    x = 0
    for w in ws:
        x ^= w[b]
    return x


def well_formes(S, i):
    V0, VM1, VM2, VM3 = S[i], S[(i + M1) % R], S[(i + M2) % R], S[(i + M3) % R]
    VRm1, VRm2 = S[(i - 1) % R], S[(i - 2) % R]
    z0 = [VRm2[b] for b in range(31)] + [VRm1[31]]
    z1 = f_xor(f_m0neg(25, V0), f_m0pos(27, VM1))
    z2 = f_xor(f_m3pos(9, VM2), f_m0pos(1, VM3))
    nv1 = f_xor(z1, z2)
    nv0 = f_xor(z0, f_m0neg(9, z1), f_m0neg(21, z2), f_m0pos(21, nv1))
    S[i] = nv1
    S[(i - 1) % R] = nv0
    return (i - 1) % R, nv0


def formes_initiales():
    """toutes les positions sont des inconnues, sauf les 31 bits bas du mot R-1 — jamais
    lus, donc absents de l'etat effectif."""
    S, idx = [], 0
    for k in range(R):
        w = []
        for b in range(32):
            if k == R - 1 and b < 31:
                w.append(0)
            else:
                w.append(1 << idx)
                idx += 1
        S.append(w)
    assert idx == NUNK
    return S


def evalue(forme, etat_bits):
    """valeur d'une forme a un etat donne (etat_bits : entier de NUNK bits)."""
    return bin(forme & etat_bits).count("1") & 1


def etat_vers_bits(S_int):
    """l'etat entier -> le vecteur d'inconnues, dans l'ordre de formes_initiales."""
    x, idx = 0, 0
    for k in range(R):
        for b in range(32):
            if k == R - 1 and b < 31:
                continue
            if (S_int[k] >> b) & 1:
                x |= 1 << idx
            idx += 1
    return x


def controle_formes(pas_test=1500, graine=230):
    """les formes, evaluees a un etat tire au hasard, doivent rendre les mots entiers."""
    import random
    rng = random.Random(graine)
    S_int = [rng.getrandbits(32) for _ in range(R)]
    x = etat_vers_bits(S_int)
    S_f = formes_initiales()
    i_int = i_f = 0
    for k in range(pas_test):
        i_int, w = well_int(S_int, i_int)
        i_f, wf = well_formes(S_f, i_f)
        v = sum(evalue(wf[b], x) << b for b in range(32))
        if v != w:
            return False, k
    return True, pas_test


def sorties_int(S_int, count):
    S, i, out = list(S_int), 0, []
    for _ in range(count):
        i, w = well_int(S, i)
        out.append(w)
    return out


def attaque(rangs, stride, budget, extra=EXTRA):
    """equations de prefixe du rang au mot t*stride (t >= 1), elimination F2."""
    S = formes_initiales()
    i = 0
    E = Ech()
    t0 = time.time()
    kw, plein = 0, None
    mot_courant = None
    for t in range(1, len(rangs)):
        besoin = t * stride
        while kw < besoin:
            i, mot_courant = well_formes(S, i)
            kw += 1
        hautes = mot_courant
        j, val = prefixe(int(rangs[t]), KB, 32)
        for r in range(j):
            if not E.add(hautes[31 - r], (val >> (j - 1 - r)) & 1):
                return "INCOHERENT", E.n, t, time.time() - t0
        if E.n >= NUNK and plein is None:
            plein = t
        if plein is not None and t >= plein + extra:
            return "COHERENT — rang plein", E.n, t, time.time() - t0
        if time.time() - t0 > budget:
            return f"budget (rang {E.n:,})", E.n, t, time.time() - t0
    return "epuise", E.n, len(rangs), time.time() - t0


if __name__ == "__main__":
    import lab

    BUDGET = float(os.environ.get("H230_BUDGET", "900"))
    ARCH = lab.load()
    BON = np.asarray(ARCH.bonus)
    NUM = np.asarray(ARCH.nums)
    RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
    MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
    besoin = int(NUNK / MOY) + 1

    HYP = (f"WELL19937a ne produit pas les rangs du bonus, sous la lecture du §106 — "
           f"bonus = tries[floor(u*20)] — pour aucun des {len(STRIDES)} pas de bloc balayes. "
           f"C'est le second nom de la phrase du §106 : « RESTE : MT19937 et WELL19937 [...] "
           f"c'est le cout de calcul des formes lineaires qui bloque, pas la donnee. » Le §254 "
           f"a pris le premier ; voici le second, a la meme machine — formes construites par "
           f"la RECURRENCE du generateur sur des entiers de {NUNK} bits, une par position de "
           f"mot, sans propagation de base — sous la meme lecture et avec le meme temoin. Le "
           f"generateur est transcrit en miroir du code de reference (R = 624, P = 31, "
           f"M1 = 70, M2 = 179, M3 = 449, decalages 25, 27, 9, 1, 9, 21, 21, sans temperage "
           f"pour la variante a). Deux controles de portee differente : les formes evaluees a "
           f"un etat tire au hasard doivent rendre exactement les mots de la version entiere "
           f"(la propagation est juste PAR RAPPORT A LA TRANSCRIPTION), et un WELL19937a "
           f"plante lu par la carte de rang doit etre reconnu COHERENT a rang plein "
           f"(l'attaque reconnait ce qu'elle cherche). Ce que rien ici ne prouve, et qui est "
           f"dit : la fidelite de la transcription au WELL19937a.c publie — il n'y a pas "
           f"d'implementation de reference sur cette machine. Les 31 bits bas du mot R-1 ne "
           f"sont jamais lus et ne sont pas des inconnues : {NUNK} inconnues, comme MT19937")
    STAT = (f"verdict de compatibilite du systeme lineaire F2 a {NUNK} inconnues, par pas de "
            f"bloc, sur les {len(BON)} rangs de l'archive")
    NUL = (f"EXACTE et algebrique : une decision de compatibilite. {MOY:.2f} equations "
           f"exactes par tirage, saturation vers {besoin} tirages, {EXTRA} tirages empiles "
           f"apres le rang plein")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible a rang plein ; WELL19937a EXCLU "
           "(sous reserve de la fidelite de la transcription, dite ci-dessus) si tous les pas "
           "rendent une incompatibilite ; INCOMPLET si un pas atteint le budget")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h230 : WELL19937a, {NUNK} inconnues, {MOY:.2f} bits par tirage -> saturation vers "
        f"{besoin} tirages ; {len(STRIDES)} pas")

    say("\n   controle 1 : les formes contre la version entiere, 1 500 pas")
    ok, k = controle_formes()
    say(f"      {'JUSTE sur ' + str(k) + ' pas' if ok else 'FAUX au pas ' + str(k)}")
    if not ok:
        raise SystemExit("la propagation des formes ne suit pas la transcription entiere")

    say("\n   controle 2 : un WELL19937a plante, lu par la carte de rang")
    import random
    rng = random.Random(230_230)
    for pas_t in (21, 23):
        st = [rng.getrandbits(32) for _ in range(R)]
        nt = besoin + EXTRA + 20
        outs = sorties_int(st, nt * pas_t + 8)
        # la sortie k est le mot produit au (k+1)-ieme pas ; l'attaque lit le mot t*stride
        # comme le t*stride-ieme mot produit, d'ou l'indice t*stride - 1
        rg = [(outs[t * pas_t - 1] * KB) >> 32 if t else 0 for t in range(nt)]
        v, rang, tt, dt = attaque(rg, pas_t, BUDGET * 3)
        say(f"      pas {pas_t} : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
        if not v.startswith("COHERENT"):
            raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")
    rg = [rng.randrange(KB) for _ in range(besoin + EXTRA + 20)]
    v, rang, tt, dt = attaque(rg, 21, BUDGET * 3)
    say(f"      temoin NEGATIF (rangs au hasard) : {v}, rang {rang:,}, {tt} tirages, {dt:.0f}s")
    if v.startswith("COHERENT"):
        raise SystemExit("le temoin negatif passe : la machine ne discrimine rien")

    say(f"\n   l'archive : {len(RANG)} rangs")
    res, compat, incomplets = [], [], []
    for pas in STRIDES:
        v, rang, tt, dt = attaque(RANG, pas, BUDGET)
        res.append((pas, v, rang, tt, dt))
        marque = ""
        if v.startswith("COHERENT"):
            compat.append(pas)
            marque = "   *** COMPATIBLE"
        elif v.startswith("budget") or v == "epuise":
            incomplets.append(pas)
            marque = "   (rien conclu pour ce pas)"
        say(f"      pas {pas:>3} : {v:<24} rang {rang:>6,}/{NUNK:,}, {tt:>5} tirages, "
            f"{dt:>5.0f}s{marque}")

    verdict = ("ETAT RELEVE" if compat else
               ("WELL19937a EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes, {len(compat)} compatible(s), "
        f"{len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique ; puissance etablie par deux temoins de portee "
                  f"distincte — les formes evaluees a un etat au hasard rendent exactement "
                  f"les {k} mots de la version entiere, et un WELL19937a plante lu par la "
                  f"carte de rang est reconnu COHERENT a rang plein sur deux pas. Ce que "
                  f"rien ne prouve et qui est dit : la fidelite de la transcription au "
                  f"WELL19937a.c publie, faute d'implementation de reference sur la machine. "
                  f"Non couvert : l'ordre d'emission comme designation, les pas hors de "
                  f"{STRIDES[0]}..{STRIDES[-1]}, la variante c (temperee) et WELL44497b"),
        notes=(f"WELL19937a SOUS LA TRONCATURE (§255) — le second nom de la phrase du §106. "
               f"Formes par la recurrence sur {NUNK} inconnues, lecture par la carte de rang, "
               f"{len(res)} pas, {len(compat)} compatibles, {len(incomplets)} incomplets. "
               f"{verdict}."))
    say("   consigne.")
