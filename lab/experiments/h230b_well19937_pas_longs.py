"""h230b — WELL19937a SOUS LA TRONCATURE, pas de bloc 42 à 128 (RAPPORT §255 addendum).

Le §255 exclut WELL19937a sous la carte de rang du §106 pour les pas `20` à `41`. Comme le
§254 pour MT19937, on prolonge jusqu'à `128` — l'intervalle que le dossier a toujours balayé
pour les congruentiels — à la même machine, sous la même lecture, avec le même témoin planté
à un pas de **cet** intervalle.

Ce fichier ne redéfinit rien : il reprend, par le texte, les définitions de `h230` et ne
change que l'intervalle balayé et le jeton scellé, qui doit nommer ces pas-là.
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

EXP_ID = "h230b.well19937_pas_longs"
FJETON = "/tmp/h230b_jeton.json"
STRIDES = tuple(range(42, 129))


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
           f"bonus = tries[floor(u*20)] — pour aucun des pas de bloc {STRIDES[0]} a "
           f"{STRIDES[-1]}. Le §255 l'a exclu pour les pas 20 a 41 ; comme le §254 pour "
           f"MT19937, on prolonge jusqu'a 128, l'intervalle que le dossier balaie pour les "
           f"congruentiels. Meme machine — formes de WELL19937a par la recurrence, transcrite "
           f"en miroir du code de reference, sur {NUNK} inconnues ; lecture par le theoreme "
           f"du prefixe ; {MOY:.2f} equations exactes par tirage, saturation vers {besoin} "
           f"tirages, {EXTRA} tirages empiles apres le rang plein — meme temoin, plante a un "
           f"pas de cet intervalle. La reserve du §255 tient a l'identique : rien ici ne "
           f"prouve la fidelite de la transcription au WELL19937a.c publie")
    STAT = (f"verdict de compatibilite du systeme lineaire F2 a {NUNK} inconnues, par pas de "
            f"bloc de {STRIDES[0]} a {STRIDES[-1]}, sur les {len(BON)} rangs de l'archive")
    NUL = (f"EXACTE et algebrique : une decision de compatibilite. {EXTRA} tirages apres le "
           f"rang plein laissent 2^-{EXTRA*3} de chance a un faux positif")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible a rang plein ; WELL19937a EXCLU "
           "(sous la reserve dite) si tous les pas rendent une incompatibilite ; INCOMPLET si "
           "un pas atteint le budget")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h230b : WELL19937a, pas {STRIDES[0]}..{STRIDES[-1]} ({len(STRIDES)} pas), "
        f"{NUNK} inconnues")

    say("\n   temoin : un WELL19937a plante, lu par la carte de rang, au pas 97")
    import random
    rng = random.Random(230_230_2)
    st = [rng.getrandbits(32) for _ in range(R)]
    nt = besoin + EXTRA + 400
    outs = sorties_int(st, nt * 97 + 8)
    rg = [(outs[t * 97 - 1] * KB) >> 32 if t else 0 for t in range(nt)]
    v, rang, tt, dt = attaque(rg, 97, BUDGET * 3)
    say(f"      pas 97 : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
    if not v.startswith("COHERENT"):
        raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")

    say(f"\n   l'archive : {len(RANG)} rangs")
    res, compat, incomplets = [], [], []
    t_all = time.time()
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
    say(f"\n   {len(res)} pas balayes en {time.time()-t_all:.0f}s, {len(compat)} "
        f"compatible(s), {len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique ; un WELL19937a plante au pas 97 — un pas de CET "
                  f"intervalle — est reconnu COHERENT a rang plein. Avec le §255, les pas 20 "
                  f"a 128 sont couverts sans trou. La reserve sur la fidelite de la "
                  f"transcription tient a l'identique"),
        notes=(f"WELL19937a SOUS LA TRONCATURE, PAS 42 A 128 (§255 addendum) — {len(res)} "
               f"pas, {len(compat)} compatibles, {len(incomplets)} incomplets. {verdict}."))
    say("   consigne.")
