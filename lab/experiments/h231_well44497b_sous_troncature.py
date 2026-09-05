"""h231 — WELL44497b SOUS LA TRONCATURE : le dernier nom (RAPPORT §256).

LE DERNIER NOM DE LA PHRASE DU §106
===================================
Le §124 citait `WELL44497b` comme la plus large famille `F₂`-linéaire déployée — `44 497`
bits — et croyait l'avoir couverte par la complexité linéaire conjointe. La précision ajoutée
au §124 dit pourquoi ce n'était pas le cas sous une carte de rang non linéaire. Le §255 a pris
`WELL19937a` et `c` ; voici `WELL44497b`, à la même machine, sous la même lecture.

LE GÉNÉRATEUR, TRANSCRIT EN MIROIR
==================================
`WELL44497b` (Panneton, L'Ecuyer, Matsumoto 2006) : `R = 1391`, `P = 15`, `M1 = 23`,
`M2 = 481`, `M3 = 229`, `MASKU = 0x7fff`, `MASKL = 0xffff8000`, et à chaque pas, l'indice
décroissant d'un cran,

    z0     = (V[i-1] & MASKL) | (V[i-2] & MASKU)
    z1     = M0neg(24, V[i])     ^ M0pos(30, V[i+M1])
    z2     = M0neg(10, V[i+M2])  ^ M3neg(26, V[i+M3])
    V[i]   = z1 ^ z2
    V[i-1] = z0 ^ M0pos(20, z1) ^ M5(9, 0xb729fcec, 0xfbffffff, 0x00020000, z2) ^ V[i]

avec `M3neg(t,v) = v << t` et `M5(r, a, ds, dt, v) = (rot_r(v) & ds) ^ (a si bit dt de v)`.
Ce `M5` est **affine en un bit** — on ajoute la constante `a` si le bit `17` de `v` vaut un —
donc `F₂`-linéaire : chaque bit de `a` est multiplié par le seul bit `v[17]`. La variante `b`
tempère la sortie :

    y  = v ^ ((v << 7)  & 0x93dd1400)
    y ^=     ((y << 15) & 0xfa118000)

LES 15 BITS QUI NE COMPTENT PAS
===============================
`z0` ne lit que les `17` bits hauts de `V[i−1]`, mot aussitôt écrasé. Ses quinze bits bas, à
l'état initial, ne sont jamais lus : `1391 × 32 − 15 = 44 497` inconnues.

LA RÉSERVE, LA MÊME
===================
Rien ici ne prouve la fidélité de la transcription au `WELL44497b.c` publié — pas de
référence sur cette machine —, et les constantes de `M5` et du tempérage sont celles dont je
suis le moins sûr. Les deux contrôles du §255 valent à l'identique : formes contre entiers,
puis générateur planté reconnu. Le premier prouve la propagation **par rapport à la
transcription**, le second que l'attaque reconnaît ce qu'elle cherche.
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
EXP_ID = "h231.well44497b_sous_troncature"
FJETON = "/tmp/h231_jeton.json"
CACHE = os.environ.get("H231_CACHE", "/tmp/h231_faits.json")   # un pas coute dix minutes
# Le balayage peut etre DECOUPE entre plusieurs processus : H231_PAS="25,26,27" restreint
# les pas, H231_CACHE isole le cache, H231_SEULEMENT_CACHE=1 ecrit le cache sans
# consigner. La consignation finale se fait en UNE passe, sur le cache fusionne, avec les
# 22 pas du jeton scelle.
STRIDES = (tuple(int(x) for x in os.environ["H231_PAS"].split(","))
           if os.environ.get("H231_PAS") else tuple(range(20, 42)))
EXTRA = 300
R, P, M1, M2, M3 = 1391, 15, 23, 481, 229
MASKU = (0xFFFFFFFF >> (32 - P)) & 0xFFFFFFFF
MASKL = (~MASKU) & 0xFFFFFFFF
M5R, M5A, M5DS, M5DT = 9, 0xB729FCEC, 0xFBFFFFFF, 0x00020000
TEMPERB, TEMPERC = 0x93DD1400, 0xFA118000
NUNK = R * 32 - P


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


def m3neg(t, v):
    return (v << t) & 0xFFFFFFFF


def m5(v):
    rot = ((v << M5R) | (v >> (32 - M5R))) & 0xFFFFFFFF
    t = rot & M5DS
    return (t ^ M5A) if (v & M5DT) else t


def temper(v):
    y = (v ^ ((v << 7) & TEMPERB)) & 0xFFFFFFFF
    return (y ^ ((y << 15) & TEMPERC)) & 0xFFFFFFFF


def well_int(S, i):
    V0, VM1, VM2, VM3 = S[i], S[(i + M1) % R], S[(i + M2) % R], S[(i + M3) % R]
    VRm1, VRm2 = S[(i - 1) % R], S[(i - 2) % R]
    z0 = (VRm1 & MASKL) | (VRm2 & MASKU)
    z1 = m0neg(24, V0) ^ m0pos(30, VM1)
    z2 = m0neg(10, VM2) ^ m3neg(26, VM3)
    nv1 = z1 ^ z2
    nv0 = z0 ^ m0pos(20, z1) ^ m5(z2) ^ nv1
    S[i] = nv1
    S[(i - 1) % R] = nv0
    return (i - 1) % R, nv0


# --------------------------------------------------------------- version en FORMES
def f_m0pos(t, v):
    return [v[b] ^ (v[b + t] if b + t < 32 else 0) for b in range(32)]


def f_m0neg(t, v):
    return [v[b] ^ (v[b - t] if b - t >= 0 else 0) for b in range(32)]


def f_m3neg(t, v):
    return [(v[b - t] if b - t >= 0 else 0) for b in range(32)]


def f_m5(v):
    # rot_9 : le bit b de la sortie est le bit (b - 9) mod 32 de l'entree ; puis le masque
    # ds ; puis la constante a, ajoutee si le bit 17 (dt) vaut un — affine en UN bit, donc
    # F2-lineaire : chaque bit de a est multiplie par la seule forme v[17].
    return [((v[(b - M5R) % 32] if (M5DS >> b) & 1 else 0)
             ^ (v[17] if (M5A >> b) & 1 else 0)) for b in range(32)]


def f_temper(v):
    y1 = [v[b] ^ (v[b - 7] if b >= 7 and (TEMPERB >> b) & 1 else 0) for b in range(32)]
    return [y1[b] ^ (y1[b - 15] if b >= 15 and (TEMPERC >> b) & 1 else 0) for b in range(32)]


def f_xor(*ws):
    out = []
    for b in range(32):
        x = 0
        for w in ws:
            x ^= w[b]
        out.append(x)
    return out


def well_formes(S, i):
    V0, VM1, VM2, VM3 = S[i], S[(i + M1) % R], S[(i + M2) % R], S[(i + M3) % R]
    VRm1, VRm2 = S[(i - 1) % R], S[(i - 2) % R]
    z0 = [VRm2[b] for b in range(P)] + [VRm1[b] for b in range(P, 32)]
    z1 = f_xor(f_m0neg(24, V0), f_m0pos(30, VM1))
    z2 = f_xor(f_m0neg(10, VM2), f_m3neg(26, VM3))
    nv1 = f_xor(z1, z2)
    nv0 = f_xor(z0, f_m0pos(20, z1), f_m5(z2), nv1)
    S[i] = nv1
    S[(i - 1) % R] = nv0
    return (i - 1) % R, nv0


def formes_initiales():
    S, idx = [], 0
    for k in range(R):
        w = []
        for b in range(32):
            if k == R - 1 and b < P:
                w.append(0)
            else:
                w.append(1 << idx)
                idx += 1
        S.append(w)
    assert idx == NUNK
    return S


def evalue(forme, x):
    return bin(forme & x).count("1") & 1


def etat_vers_bits(S_int):
    x, idx = 0, 0
    for k in range(R):
        for b in range(32):
            if k == R - 1 and b < P:
                continue
            if (S_int[k] >> b) & 1:
                x |= 1 << idx
            idx += 1
    return x


def controle_formes(pas_test=1500, graine=231):
    import random
    rng = random.Random(graine)
    S_int = [rng.getrandbits(32) for _ in range(R)]
    x = etat_vers_bits(S_int)
    S_f = formes_initiales()
    i_int = i_f = 0
    for k in range(pas_test):
        i_int, w = well_int(S_int, i_int)
        i_f, wf = well_formes(S_f, i_f)
        v = sum(evalue(f, x) << b for b, f in enumerate(f_temper(wf)))
        if v != temper(w):
            return False, k
    return True, pas_test


def sorties_int(S_int, count):
    S, i, out = list(S_int), 0, []
    for _ in range(count):
        i, w = well_int(S, i)
        out.append(temper(w))
    return out


def attaque(rangs, stride, budget, extra=EXTRA):
    S = formes_initiales()
    i, E, t0, kw, plein, mot = 0, Ech(), time.time(), 0, None, None
    for t in range(1, len(rangs)):
        besoin = t * stride
        while kw < besoin:
            i, mot = well_formes(S, i)
            kw += 1
        hautes = f_temper(mot)
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

    BUDGET = float(os.environ.get("H231_BUDGET", "3600"))
    ARCH = lab.load()
    BON = np.asarray(ARCH.bonus)
    NUM = np.asarray(ARCH.nums)
    RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
    MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
    besoin = int(NUNK / MOY) + 1

    HYP = (f"WELL44497b ne produit pas les rangs du bonus sous la lecture du §106 — "
           f"bonus = tries[floor(u*20)] — pour aucun des {len(STRIDES)} pas de bloc balayes. "
           f"C'est le dernier nom de la phrase du §106 et la plus large famille F2-lineaire "
           f"deployee, que le §124 croyait couverte par la complexite lineaire conjointe — la "
           f"precision du §124 dit pourquoi ce n'etait pas le cas sous une carte de rang non "
           f"lineaire. Meme machine que les §254 et §255 : formes par la RECURRENCE du "
           f"generateur, transcrit en miroir du code de reference (R = 1391, P = 15, M1 = 23, "
           f"M2 = 481, M3 = 229, decalages 24, 30, 10, 26, 20, M5 de rotation 9 et masques "
           f"0xb729fcec / 0xfbffffff / 0x00020000, temperage 0x93dd1400 / 0xfa118000), sur "
           f"{NUNK} inconnues — les 15 bits bas du mot R-1 ne sont jamais lus. M5 est affine "
           f"en un bit, donc F2-lineaire. {MOY:.2f} equations exactes par tirage, saturation "
           f"vers {besoin} tirages, {EXTRA} empiles apres le rang plein. Deux controles : "
           f"formes temperees contre entiers temperes sur 1 500 pas, et un WELL44497b plante "
           f"reconnu COHERENT a rang plein. Reserve : rien ne prouve la fidelite de la "
           f"transcription au WELL44497b.c publie, et les constantes de M5 et du temperage "
           f"sont celles dont je suis le moins sur")
    STAT = (f"verdict de compatibilite du systeme F2 a {NUNK} inconnues, par pas de bloc, sur "
            f"les {len(BON)} rangs")
    NUL = (f"EXACTE et algebrique : une decision de compatibilite. {EXTRA} tirages apres le "
           f"rang plein laissent 2^-{EXTRA*3} de chance a un faux positif")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible ; WELL44497b EXCLU (sous la "
           "reserve dite) si tous rendent une incompatibilite ; INCOMPLET si un pas atteint "
           "le budget, auquel cas rien n'est conclu pour lui")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h231 : WELL44497b, {NUNK} inconnues, {MOY:.2f} bits par tirage -> saturation vers "
        f"{besoin} tirages ; {len(STRIDES)} pas")

    say("\n   controle 1 : les formes contre la version entiere, 1 500 pas")
    ok, k = controle_formes()
    say(f"      {'JUSTE sur ' + str(k) + ' pas' if ok else 'FAUX au pas ' + str(k)}")
    if not ok:
        raise SystemExit("la propagation des formes ne suit pas la transcription entiere")

    # UN CACHE PAR PAS. Chaque systeme coute une dizaine de minutes sur 44 497 inconnues,
    # et le conteneur a deja ete redemarre deux fois en cours de balayage. Chaque pas
    # termine — et le temoin, deterministe par sa graine — est ecrit dans CACHE ; une
    # relance ne refait que ce qui manque, et la ligne de registre couvre tout.
    deja = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    def consigne_cache():
        json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    say("\n   controle 2 : un WELL44497b plante, lu par la carte de rang")
    import random
    rng = random.Random(231_231)
    st = [rng.getrandbits(32) for _ in range(R)]
    nt = besoin + EXTRA + 600
    if deja.get("temoin") == "ok":
        say("      temoins deja passes (graine deterministe) — repris du cache")
    else:
        outs = sorties_int(st, nt * 21 + 8)
        rg = [(outs[t * 21 - 1] * KB) >> 32 if t else 0 for t in range(nt)]
        v, rang, tt, dt = attaque(rg, 21, BUDGET * 3)
        say(f"      pas 21 : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
        if not v.startswith("COHERENT"):
            raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")
        rg = [rng.randrange(KB) for _ in range(besoin + EXTRA + 600)]
        v, rang, tt, dt = attaque(rg, 21, BUDGET * 3)
        say(f"      temoin NEGATIF (rangs au hasard) : {v}, rang {rang:,}, {tt} tirages, {dt:.0f}s")
        if v.startswith("COHERENT"):
            raise SystemExit("le temoin negatif passe : la machine ne discrimine rien")
        deja["temoin"] = "ok"
        consigne_cache()

    say(f"\n   l'archive : {len(RANG)} rangs")
    res, compat, incomplets = [], [], []
    for pas in STRIDES:
        if str(pas) in deja:
            v, rang, tt, dt = deja[str(pas)]
            say(f"      pas {pas:>3} : {v:<24} rang {rang:>6,}/{NUNK:,}, {tt:>5} tirages, "
                f"{dt:>5.0f}s   (repris du cache)")
            res.append((pas, v, rang, tt, dt))
            if v.startswith("COHERENT"):
                compat.append(pas)
            elif v.startswith("budget") or v == "epuise":
                incomplets.append(pas)
            continue
        v, rang, tt, dt = attaque(RANG, pas, BUDGET)
        deja[str(pas)] = [v, rang, tt, dt]
        consigne_cache()
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

    if os.environ.get("H231_SEULEMENT_CACHE"):
        say(f"\n   cache seul ({CACHE}) : {len(res)} pas ecrits, pas de consignation")
        raise SystemExit(0)

    verdict = ("ETAT RELEVE" if compat else
               ("WELL44497b EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes, {len(compat)} compatible(s), "
        f"{len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique ; les formes suivent la version entiere sur {k} pas "
                  f"et un WELL44497b plante est reconnu COHERENT a rang plein. Reserve de "
                  f"fidelite : la plus forte du dossier, sur les constantes de M5 et du "
                  f"temperage. Non couvert : la variante a, l'ordre d'emission, les pas hors "
                  f"de {STRIDES[0]}..{STRIDES[-1]}"),
        notes=(f"WELL44497b SOUS LA TRONCATURE (§256) — le dernier nom de la phrase du §106, "
               f"{NUNK} inconnues, {len(res)} pas, {len(compat)} compatibles, "
               f"{len(incomplets)} incomplets. {verdict}."))
    say("   consigne.")
