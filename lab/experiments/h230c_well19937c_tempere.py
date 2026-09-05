"""h230c — WELL19937c, LA VARIANTE TEMPÉRÉE, sous la troncature (RAPPORT §255 addendum 2).

Le §255 nomme la variante `c` parmi ce qu'il ne couvre pas. Elle ne diffère de `WELL19937a`
que par un **tempérage** de la sortie — deux masques, deux décalages, `F₂`-linéaires comme
tout le reste — que le code de référence active par `#define TEMPERING` :

    y  = v ^ ((v << 7)  & 0xe46e1700)
    y ^=     ((y << 15) & 0x9b868000)

L'état, la récurrence, les `19 937` inconnues et la lecture par la carte de rang sont ceux du
§255 ; seules les formes de **sortie** changent. La réserve de fidélité du §255 tient, et
s'étend aux deux constantes de tempérage.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICI = os.path.dirname(os.path.abspath(__file__))
_H230 = open(os.path.join(ICI, "h230_well19937_sous_troncature.py"), encoding="utf-8").read()
exec(compile(_H230[:_H230.index('if __name__ == "__main__":')], "h230defs", "exec"), globals())

EXP_ID = "h230c.well19937c_tempere"
FJETON = "/tmp/h230c_jeton.json"
STRIDES = tuple(range(20, 129))
TEMPERB, TEMPERC = 0xE46E1700, 0x9B868000


def temper_int(v):
    y = (v ^ ((v << 7) & TEMPERB)) & 0xFFFFFFFF
    return (y ^ ((y << 15) & TEMPERC)) & 0xFFFFFFFF


def temper_formes(v):
    y1 = [v[b] ^ (v[b - 7] if b >= 7 and (TEMPERB >> b) & 1 else 0) for b in range(32)]
    return [y1[b] ^ (y1[b - 15] if b >= 15 and (TEMPERC >> b) & 1 else 0) for b in range(32)]


def controle_formes_c(pas_test=1500, graine=2303):
    import random
    rng = random.Random(graine)
    S_int = [rng.getrandbits(32) for _ in range(R)]
    x = etat_vers_bits(S_int)
    S_f = formes_initiales()
    i_int = i_f = 0
    for k in range(pas_test):
        i_int, w = well_int(S_int, i_int)
        i_f, wf = well_formes(S_f, i_f)
        tf = temper_formes(wf)
        v = sum(evalue(tf[b], x) << b for b in range(32))
        if v != temper_int(w):
            return False, k
    return True, pas_test


def sorties_int_c(S_int, count):
    return [temper_int(w) for w in sorties_int(S_int, count)]


def attaque_c(rangs, stride, budget, extra=EXTRA):
    S = formes_initiales()
    i = 0
    E = Ech()
    t0 = time.time()
    kw, plein = 0, None
    mot = None
    for t in range(1, len(rangs)):
        besoin = t * stride
        while kw < besoin:
            i, mot = well_formes(S, i)
            kw += 1
        hautes = temper_formes(mot)
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

    HYP = (f"WELL19937c — la variante temperee de WELL19937a, y = v ^ ((v << 7) & 0xe46e1700) "
           f"puis y ^= (y << 15) & 0x9b868000 — ne produit pas les rangs du bonus sous la "
           f"lecture du §106, pour aucun des pas de bloc {STRIDES[0]} a {STRIDES[-1]}. Le "
           f"§255 la nomme parmi ce qu'il ne couvre pas. Etat, recurrence, {NUNK} inconnues "
           f"et lecture sont ceux du §255 ; seules les formes de SORTIE recoivent le "
           f"temperage, F2-lineaire comme tout le reste. Memes controles — les formes "
           f"temperees evaluees a un etat au hasard contre la version entiere temperee, un "
           f"WELL19937c plante reconnu COHERENT a rang plein, un temoin negatif rejete — et "
           f"meme reserve : rien ne prouve la fidelite de la transcription, ni des deux "
           f"constantes de temperage, au WELL19937c.c publie")
    STAT = (f"verdict de compatibilite du systeme F2 a {NUNK} inconnues, par pas de bloc de "
            f"{STRIDES[0]} a {STRIDES[-1]}, sur les {len(BON)} rangs")
    NUL = (f"EXACTE et algebrique. {EXTRA} tirages apres le rang plein laissent "
           f"2^-{EXTRA*3} de chance a un faux positif")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible ; WELL19937c EXCLU (sous la "
           "reserve dite) si tous rendent une incompatibilite ; INCOMPLET si un pas atteint "
           "le budget")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h230c : WELL19937c (tempere), pas {STRIDES[0]}..{STRIDES[-1]}, {NUNK} inconnues")
    say("\n   controle 1 : les formes temperees contre la version entiere temperee, 1 500 pas")
    ok, k = controle_formes_c()
    say(f"      {'JUSTE sur ' + str(k) + ' pas' if ok else 'FAUX au pas ' + str(k)}")
    if not ok:
        raise SystemExit("la propagation des formes temperees ne suit pas la transcription")

    say("\n   controle 2 : un WELL19937c plante, lu par la carte de rang")
    import random
    rng = random.Random(230_230_3)
    for pas_t in (21, 97):
        st = [rng.getrandbits(32) for _ in range(R)]
        nt = besoin + EXTRA + 400
        outs = sorties_int_c(st, nt * pas_t + 8)
        rg = [(outs[t * pas_t - 1] * KB) >> 32 if t else 0 for t in range(nt)]
        v, rang, tt, dt = attaque_c(rg, pas_t, BUDGET * 3)
        say(f"      pas {pas_t} : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
        if not v.startswith("COHERENT"):
            raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")
    rg = [rng.randrange(KB) for _ in range(besoin + EXTRA + 400)]
    v, rang, tt, dt = attaque_c(rg, 21, BUDGET * 3)
    say(f"      temoin NEGATIF (rangs au hasard) : {v}, rang {rang:,}, {tt} tirages, {dt:.0f}s")
    if v.startswith("COHERENT"):
        raise SystemExit("le temoin negatif passe : la machine ne discrimine rien")

    say(f"\n   l'archive : {len(RANG)} rangs")
    res, compat, incomplets = [], [], []
    t_all = time.time()
    for pas in STRIDES:
        v, rang, tt, dt = attaque_c(RANG, pas, BUDGET)
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
               ("WELL19937c EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes en {time.time()-t_all:.0f}s, {len(compat)} "
        f"compatible(s), {len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique ; les formes temperees suivent la version entiere "
                  f"sur {k} pas, et un WELL19937c plante est reconnu COHERENT a rang plein "
                  f"aux pas 21 et 97. Reserve de fidelite : identique au §255, etendue aux "
                  f"constantes de temperage"),
        notes=(f"WELL19937c TEMPERE (§255 addendum 2) — {len(res)} pas de "
               f"{STRIDES[0]} a {STRIDES[-1]}, {len(compat)} compatibles, "
               f"{len(incomplets)} incomplets. {verdict}."))
    say("   consigne.")
