"""h231b — WELL44497b SOUS LA TRONCATURE, pas de bloc 42 à 128 (RAPPORT §256 addendum).

Le §256 exclut WELL44497b sous la carte de rang du §106 pour les pas `20` à `41`. Comme les
§254 et §255 pour MT19937 et WELL19937, on prolonge jusqu'à `128` — l'intervalle que le
dossier a toujours balayé pour les congruentiels — à la même machine, sous la même lecture,
avec le même témoin planté à un pas de **cet** intervalle.

Ce fichier ne redéfinit rien : il reprend, par le texte, les définitions de `h231` et ne
change que l'intervalle balayé et le jeton scellé, qui doit nommer ces pas-là. Le découpage
entre processus (`H231_PAS`, `H231_CACHE`, `H231_SEULEMENT_CACHE`) est repris tel quel : un
pas coûte dix minutes, et il y en a quatre-vingt-sept.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ICI = os.path.dirname(os.path.abspath(__file__))
_H231 = open(os.path.join(ICI, "h231_well44497b_sous_troncature.py"), encoding="utf-8").read()
exec(compile(_H231[:_H231.index('if __name__ == "__main__":')], "h231defs", "exec"), globals())

EXP_ID = "h231b.well44497b_pas_longs"
FJETON = "/tmp/h231b_jeton.json"
CACHE = os.environ.get("H231_CACHE", "/tmp/h231b_faits.json")
STRIDES = (tuple(int(x) for x in os.environ["H231_PAS"].split(","))
           if os.environ.get("H231_PAS") else tuple(range(42, 129)))
TEMOIN_PAS = 97


if __name__ == "__main__":
    import lab

    BUDGET = float(os.environ.get("H231_BUDGET", "3600"))
    ARCH = lab.load()
    BON = np.asarray(ARCH.bonus)
    NUM = np.asarray(ARCH.nums)
    RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
    MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
    besoin = int(NUNK / MOY) + 1

    HYP = (f"WELL44497b ne produit pas les rangs du bonus, sous la lecture du §106 — "
           f"bonus = tries[floor(u*20)] — pour aucun des pas de bloc 42 a 128. Le §256 l'a "
           f"exclu pour les pas 20 a 41 ; comme les §254 et §255 pour MT19937 et WELL19937, "
           f"on prolonge jusqu'a 128, l'intervalle que le dossier balaie pour les "
           f"congruentiels. Meme machine — formes de WELL44497b par la recurrence, transcrite "
           f"en miroir du code de reference, M5 affine en un bit, temperage 0x93dd1400 / "
           f"0xfa118000, sur {NUNK} inconnues ; lecture par le theoreme du prefixe ; "
           f"{MOY:.2f} equations exactes par tirage, saturation vers {besoin} tirages, {EXTRA} "
           f"tirages empiles apres le rang plein — meme temoin, plante au pas {TEMOIN_PAS}, un "
           f"pas de cet intervalle. La reserve du §256 tient a l'identique, et elle est la "
           f"plus forte du dossier : rien ici ne prouve la fidelite de la transcription au "
           f"WELL44497b.c publie, et les constantes de M5 et du temperage sont celles dont je "
           f"suis le moins sur. Le balayage est decoupe entre processus, un cache par "
           f"processus, et consigne en une passe sur le cache fusionne")
    STAT = (f"verdict de compatibilite du systeme lineaire F2 a {NUNK} inconnues, par pas de "
            f"bloc de 42 a 128, sur les {len(BON)} rangs de l'archive")
    NUL = (f"EXACTE et algebrique : une decision de compatibilite. {EXTRA} tirages apres le "
           f"rang plein laissent 2^-{EXTRA*3} de chance a un faux positif")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible a rang plein ; WELL44497b EXCLU "
           "(sous la reserve dite) si tous les pas rendent une incompatibilite ; INCOMPLET si "
           "un pas atteint le budget")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h231b : WELL44497b, pas {STRIDES[0]}..{STRIDES[-1]} ({len(STRIDES)} pas), "
        f"{NUNK} inconnues, cache {CACHE}")

    deja = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}

    def consigne_cache():
        json.dump(deja, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    say(f"\n   temoin : un WELL44497b plante, lu par la carte de rang, au pas {TEMOIN_PAS}")
    if deja.get("temoin") == "ok":
        say("      temoin deja passe (graine deterministe) — repris du cache")
    else:
        import random
        rng = random.Random(231_231_2)
        st = [rng.getrandbits(32) for _ in range(R)]
        nt = besoin + EXTRA + 600
        outs = sorties_int(st, nt * TEMOIN_PAS + 8)
        rg = [(outs[t * TEMOIN_PAS - 1] * KB) >> 32 if t else 0 for t in range(nt)]
        v, rang, tt, dt = attaque(rg, TEMOIN_PAS, BUDGET * 3)
        say(f"      pas {TEMOIN_PAS} : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
        if not v.startswith("COHERENT"):
            raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")
        deja["temoin"] = "ok"
        consigne_cache()

    say(f"\n   l'archive : {len(RANG)} rangs")
    res, compat, incomplets = [], [], []
    t_all = time.time()
    for pas in STRIDES:
        if str(pas) in deja:
            v, rang, tt, dt = deja[str(pas)]
            say(f"      pas {pas:>3} : {v:<24} rang {rang:>6,}/{NUNK:,}, {tt:>5} tirages, "
                f"{dt:>5.0f}s   (repris du cache)")
        else:
            v, rang, tt, dt = attaque(RANG, pas, BUDGET)
            deja[str(pas)] = [v, rang, tt, dt]
            consigne_cache()
            say(f"      pas {pas:>3} : {v:<24} rang {rang:>6,}/{NUNK:,}, {tt:>5} tirages, "
                f"{dt:>5.0f}s")
        res.append((pas, v, rang, tt, dt))
        if v.startswith("COHERENT"):
            compat.append(pas)
            say("         *** COMPATIBLE")
        elif v.startswith("budget") or v == "epuise":
            incomplets.append(pas)
            say("         (rien conclu pour ce pas)")

    if os.environ.get("H231_SEULEMENT_CACHE"):
        say(f"\n   cache seul ({CACHE}) : {len(res)} pas ecrits, pas de consignation")
        raise SystemExit(0)

    verdict = ("ETAT RELEVE" if compat else
               ("WELL44497b EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes ({time.time()-t_all:.0f}s dans cette passe, "
        f"{sum(r[4] for r in res):.0f}s de calcul en tout), {len(compat)} compatible(s), "
        f"{len(incomplets)} incomplet(s)")
    if incomplets:
        say("   NON CONCLUS, et il faut le dire : pas " + ", ".join(map(str, incomplets)))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"decision algebrique ; un WELL44497b plante au pas {TEMOIN_PAS} — un pas de "
                  f"CET intervalle — est reconnu COHERENT a rang plein. Avec le §256, les pas "
                  f"20 a 128 sont couverts sans trou. La reserve sur la fidelite de la "
                  f"transcription tient a l'identique"),
        notes=(f"WELL44497b SOUS LA TRONCATURE, PAS 42 A 128 (§256 addendum) — {len(res)} "
               f"pas, {len(compat)} compatibles, {len(incomplets)} incomplets, "
               f"{sum(r[4] for r in res):.0f}s de calcul. {verdict}."))
    say("   consigne.")
