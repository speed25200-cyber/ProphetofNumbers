"""h229b — MT19937 SOUS LA TRONCATURE, pas de bloc 42 à 128 (RAPPORT §254 addendum).

Le §254 exclut MT19937 sous la carte de rang du §106 pour les pas `20` à `41`, et nomme
lui-même ce qu'il laisse : *« les pas hors de 20–41. Chacun coûte ≈ 50 s ; l'intervalle a été
choisi parce que le budget d'un tirage vaut au moins vingt mots, plus le bonus, le boost et
les rejets. »*

Les §230 et §232 balayaient `128` pas de bloc pour les congruentiels. Rien ne justifie que le
générateur `F₂`-linéaire soit balayé moins loin que les congruentiels : on prolonge donc
jusqu'à `128`, à la même machine, sous la même lecture, avec le même témoin.

Ce fichier ne redéfinit rien : il reprend, par le texte, les définitions de `h229` — formes
par la récurrence, lecture par le prefixe, élimination — et ne change que l'intervalle balayé
et le jeton scellé, qui doit nommer ces pas-là et non les précédents.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICI = os.path.dirname(os.path.abspath(__file__))
_H229 = open(os.path.join(ICI, "h229_mt19937_sous_troncature.py"), encoding="utf-8").read()
exec(compile(_H229[:_H229.index('if __name__ == "__main__":')], "h229defs", "exec"), globals())

EXP_ID = "h229b.mt19937_pas_longs"
FJETON = "/tmp/h229b_jeton.json"
STRIDES = tuple(range(42, 129))


if __name__ == "__main__":
    import lab

    BUDGET = float(os.environ.get("H229_BUDGET", "900"))
    ARCH = lab.load()
    BON = np.asarray(ARCH.bonus)
    NUM = np.asarray(ARCH.nums)
    RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
    MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
    besoin = int(NUNK / MOY) + 1

    HYP = (f"MT19937 ne produit pas les rangs du bonus, sous la lecture du §106 — "
           f"bonus = tries[floor(u*20)] — pour aucun des pas de bloc {STRIDES[0]} a "
           f"{STRIDES[-1]}. Le §254 a exclu MT19937 sous cette lecture pour les pas 20 a 41 "
           f"et nomme lui-meme ce qu'il laisse : les pas au-dela. Les §230 et §232 balayaient "
           f"128 pas de bloc pour les congruentiels ; rien ne justifie que le generateur "
           f"F2-lineaire soit balaye moins loin. Meme machine que le §254 — formes de MT19937 "
           f"par la recurrence (§80), lecture par le theoreme du prefixe (§105), elimination "
           f"F2 sur {NUNK} inconnues, {MOY:.2f} equations exactes par tirage donc saturation "
           f"vers {besoin} tirages, {EXTRA} tirages empiles apres le rang plein — meme temoin, "
           f"meme absorption du decalage interne dans l'etat inconnu. Seul l'intervalle des "
           f"pas change, et le jeton le nomme")
    STAT = (f"verdict de compatibilite du systeme lineaire F2 a {NUNK} inconnues, par pas de "
            f"bloc de {STRIDES[0]} a {STRIDES[-1]}, sur les {len(BON)} rangs de l'archive")
    NUL = (f"EXACTE et algebrique : une DECISION de compatibilite, non un test statistique. "
           f"Un systeme incompatible EXCLUT le generateur. {EXTRA} tirages apres le rang plein "
           f"laissent 2^-{EXTRA*3} de chance a un faux positif")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible a rang plein ; MT19937 EXCLU si "
           "tous les pas rendent une incompatibilite ; INCOMPLET si un pas atteint le budget "
           "avant saturation, auquel cas rien n'est conclu pour lui")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h229b : MT19937, pas {STRIDES[0]}..{STRIDES[-1]} ({len(STRIDES)} pas), "
        f"{NUNK} inconnues, saturation vers {besoin} tirages")

    # --- le temoin, a un pas de CET intervalle : la machine doit le reconnaitre ici aussi
    say("\n   temoin : un MT19937 plante, lu par la carte de rang, au pas 97")
    import random
    rng = random.Random(229_229_2)
    st = [rng.getrandbits(32) for _ in range(N)]
    st[0] |= 0x80000000
    nt = besoin + EXTRA + 20
    outs = mt_outputs(st, nt * 97 + 8)
    rg = [(outs[t * 97] * KB) >> 32 for t in range(nt)]
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
               ("MT19937 EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes en {time.time()-t_all:.0f}s, {len(compat)} "
        f"compatible(s), {len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique, puissance etablie par le temoin : un MT19937 plante "
                  f"et lu par la carte de rang au pas 97 — un pas de CET intervalle — est "
                  f"reconnu COHERENT a rang plein. Avec le §254, les pas 20 a 128 sont "
                  f"couverts sans trou, soit l'intervalle que les §230 et §232 balayaient pour "
                  f"les congruentiels. Non couvert et dit : la designation par indice dans "
                  f"l'ordre d'emission, et WELL19937 / WELL44497b"),
        notes=(f"MT19937 SOUS LA TRONCATURE, PAS 42 A 128 (§254 addendum) — le §254 nommait "
               f"les pas au-dela de 41 comme non couverts ; les §230 et §232 en balayaient 128 "
               f"pour les congruentiels. {len(res)} pas, {len(compat)} compatibles, "
               f"{len(incomplets)} incomplets. {verdict}."))
    say("   consigne.")
