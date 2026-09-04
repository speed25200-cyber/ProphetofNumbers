"""h229 — MT19937 SOUS LA TRONCATURE : le trou que le §106 avait nommé lui-même
(RAPPORT §254).

LE TROU, ET IL EST ÉCRIT NOIR SUR BLANC
=======================================
Le §106 lit le bonus par la **désignation par indice** : `bonus = triés[⌊u·20⌋]`, donc le
**rang** du bonus parmi les vingt numéros triés vaut `⌊u·20⌋` — une observation de troncature
exacte, disponible sur les `70 560` tirages, sans jamais avoir besoin de l'ordre d'émission.
Il passe `10` familles `F₂`-linéaires à cette moulinette et les exclut toutes.

Et il nomme ce qu'il ne fait pas :

> *« RESTE : MT19937 et WELL19937. Le budget de `3,20` bits par tirage les met à portée en
>   `6 230` tirages, largement disponibles — c'est le **coût de calcul** des formes linéaires
>   qui bloque, pas la donnée. »*

Or ce coût-là, le §80 l'a déjà levé, et le §88 s'en est déjà servi : on construit les formes
de `MT19937` **par la récurrence** au lieu de propager `19 937` vecteurs de base.

LE §88 A BIEN TESTÉ MT19937 — MAIS PAS SOUS CETTE LECTURE
=========================================================
Le §88 conclut « MT19937 INCOHÉRENT ». Sa première hypothèse est :

> *« le bonus est le **premier** numéro sorti »*, et il lit `(bonus − 1) mod 16`, les quatre
> bits **bas**, au mot `20t`.

C'est l'échantillonneur **modulo**, au pas fixe `20`, sous une désignation que le §106 a
justement remplacée. Les deux paragraphes testent donc deux modèles **différents** :

    §88    bonus = premier numero sorti, bits BAS, pas 20     -> INCOHERENT
    §106   bonus = tries[floor(u*20)], bits HAUTS, 10 pas     -> 10 familles, MT19937 ABSENT
    ici    bonus = tries[floor(u*20)], bits HAUTS, pas balaye -> MT19937 et WELL19937

> Aucun des deux ne couvre l'autre. Le §88 a le bon générateur et la mauvaise lecture ; le
> §106 a la bonne lecture et pas ce générateur-là.

ET LE §124 NE LES FERME PAS NON PLUS
====================================
On pourrait croire la question réglée par la complexité linéaire conjointe : `W ≥ 47 040`
fermerait `MT19937` (`19 937` bits). La précision ajoutée au §124 dit pourquoi c'est faux —
ce théorème exige que les suites observées soient des fonctionnelles **linéaires** de l'état,
et `⌊u·20⌋` est un **seuil**, pas une forme linéaire. Une sortie filtrée non linéairement peut
avoir une complexité linéaire bien supérieure à la largeur de son état.

**MT19937 sous la carte de rang n'est donc fermé nulle part.** C'est ce fichier qui le fait.

LE DÉCALAGE INTERNE S'ABSORBE
=============================
Le §106 balayait « tous les décalages internes ». Ce n'est pas nécessaire, et le §230 avait
déjà fait la remarque pour les congruentiels : si l'on lit les mots aux positions
`décalage + t·pas`, il suffit de prendre pour inconnue l'état **au mot `décalage`** —
`x[décalage .. décalage+623]` est un état MT19937 parfaitement légitime — et les positions
lues redeviennent `0, pas, 2·pas, …`. **Le décalage disparaît dans l'état inconnu**, et il ne
reste que le pas à balayer.
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
EXP_ID = "h229.mt19937_sous_troncature"
FJETON = "/tmp/h229_jeton.json"
STRIDES = tuple(range(20, 42))
EXTRA = 300                    # equations empilees APRES le rang plein
JMAX = 6


def say(*a):
    print(*a, flush=True)


# --- on reprend, par le texte, la machinerie deja ecrite et deja verifiee :
#     le theoreme du prefixe (§105, h86) et les formes de MT19937 par la
#     recurrence (§80, h67). La recopier serait la faire diverger.
_H86 = open(os.path.join(ICI, "h86_prefixe.py"), encoding="utf-8").read()
exec(compile(_H86[_H86.index("def prefixe("):_H86.index("def indices_fy(")],
             "h86prefixe", "exec"), globals())

_H67 = open(os.path.join(ICI, "h67_reconstitution.py"), encoding="utf-8").read()
exec(compile(_H67[_H67.index("N, M_, MAG = "):_H67.index("def temper_low(")],
             "h67mt", "exec"), globals())
exec(compile(_H67[_H67.index("def mt_outputs("):_H67.index("# =====", _H67.index("def mt_outputs("))],
             "h67out", "exec"), globals())
exec(compile(_H67[_H67.index("class Ech:"):_H67.index("# =====", _H67.index("class Ech:"))],
             "h67ech", "exec"), globals())


def temper_formes(x):
    """les 32 formes F2 du mot TEMPERE, dans l'ordre des poids croissants.

    Le §88 n'avait besoin que des bits bas ; la lecture du §106 lit les bits HAUTS,
    puisque le rang vaut floor(u*20) — un prefixe, pas un residu.
    """
    y1 = [x[i] ^ (x[i + 11] if i + 11 < 32 else 0) for i in range(32)]
    y2 = [y1[i] ^ ((y1[i - 7] if i >= 7 else 0)
                   if (0x9D2C5680 >> i) & 1 else 0) for i in range(32)]
    y3 = [y2[i] ^ ((y2[i - 15] if i >= 15 else 0)
                   if (0xEFC60000 >> i) & 1 else 0) for i in range(32)]
    return [y3[i] ^ (y3[i + 18] if i + 18 < 32 else 0) for i in range(32)]


def attaque(rangs, stride, budget, extra=EXTRA):
    """Empile les equations de prefixe du rang, au mot t*stride, et elimine.

    ON DEMARRE AU TIRAGE 1. Le mot 0 est x[0], dont les 31 bits de poids faible
    n'entrent PAS dans l'etat : ses formes seraient fausses, et l'incoherence qui en
    sortirait serait un artefact de parametrage, pas un fait sur l'archive. C'est le
    piege que le §80 puis le §88 ont rencontre.

    ET ON NE S'ARRETE PAS AU RANG PLEIN : un systeme de rang plein n'est pas une
    reussite, c'est une solution UNIQUE qu'il reste a confronter aux equations
    suivantes. On empile donc `extra` tirages de plus.
    """
    mots = mt_state_forms()
    E = Ech()
    t0 = time.time()
    kw, plein = 0, None
    for t in range(1, len(rangs)):
        besoin = t * stride
        while kw <= besoin:
            if kw >= N:
                mots.append(mt_next(mots[kw - N], mots[kw - N + 1], mots[kw - N + M_]))
                mots[kw - N] = None
            kw += 1
        hautes = temper_formes(mots[besoin])
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

    BUDGET = float(os.environ.get("H229_BUDGET", "600"))
    ARCH = lab.load()
    BON = np.asarray(ARCH.bonus)
    NUM = np.asarray(ARCH.nums)
    RANG = (NUM < BON[:, None]).sum(1).astype(np.int64)
    MOY = sum(prefixe(m, KB, 32)[0] for m in range(KB)) / KB
    besoin = int(NUNK / MOY) + 1

    HYP = (f"MT19937 ne produit pas les rangs du bonus, sous la lecture du §106 — "
           f"bonus = tries[floor(u*20)], donc le rang parmi les vingt numeros tries vaut "
           f"floor(u*20) — et sous aucun des {len(STRIDES)} pas de bloc balayes. LE TROU EST "
           f"NOMME PAR LE §106 LUI-MEME : « RESTE : MT19937 et WELL19937. Le budget de 3,20 "
           f"bits par tirage les met a portee en 6 230 tirages, largement disponibles — c'est "
           f"le COUT DE CALCUL des formes lineaires qui bloque, pas la donnee. » Or ce cout, "
           f"le §80 l'a leve en construisant les formes par la RECURRENCE au lieu de propager "
           f"{NUNK} vecteurs de base, et le §88 s'en est deja servi. Mais le §88 teste un "
           f"AUTRE modele : sa premiere hypothese est « le bonus est le PREMIER numero sorti » "
           f"et il lit (bonus - 1) mod 16, les quatre bits BAS, au mot 20t — l'echantillonneur "
           f"modulo, au pas fixe 20, sous une designation que le §106 a justement remplacee. "
           f"Aucun des deux paragraphes ne couvre l'autre : le §88 a le bon generateur et la "
           f"mauvaise lecture, le §106 a la bonne lecture et pas ce generateur-la. Et le §124 "
           f"ne les ferme pas non plus : sa borne W >= 47 040 exige que les suites observees "
           f"soient des fonctionnelles LINEAIRES de l'etat, alors que floor(u*20) est un "
           f"seuil — une sortie filtree non lineairement peut avoir une complexite lineaire "
           f"bien superieure a la largeur de son etat. MT19937 sous la carte de rang n'est "
           f"donc ferme nulle part. Le decalage interne n'a pas a etre balaye : lire les mots "
           f"aux positions decalage + t*pas revient a prendre pour inconnue l'etat AU MOT "
           f"decalage, qui est un etat MT19937 legitime, de sorte que le decalage disparait "
           f"dans l'inconnue et qu'il ne reste que le pas")
    STAT = (f"verdict de compatibilite du systeme lineaire F2 a {NUNK} inconnues, par pas de "
            f"bloc, sur les {len(BON)} rangs de l'archive")
    NUL = (f"EXACTE et algebrique : ce n'est pas un test statistique mais une DECISION de "
           f"compatibilite. Le systeme a {NUNK} inconnues recoit {MOY:.2f} equations exactes "
           f"par tirage, donc il sature vers {besoin} tirages ; on en empile {EXTRA} de plus "
           f"apres le rang plein, ce qui laisse 2^-{EXTRA*3} de chance a un faux positif. Un "
           f"systeme incompatible EXCLUT le generateur, il ne le rend pas improbable")
    VER = ("ETAT RELEVE si un pas rend un systeme compatible a rang plein ; MT19937 EXCLU si "
           "tous les pas rendent une incompatibilite ; INCOMPLET si le budget de temps est "
           "atteint avant la saturation, auquel cas rien n'est conclu pour ce pas")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h229 : MT19937, {NUNK} inconnues, {MOY:.2f} bits par tirage -> saturation vers "
        f"{besoin} tirages ; {len(STRIDES)} pas balayes (le decalage s'absorbe)")

    # --- LE TEMOIN. Sans lui, « incoherent » ne dit rien : il faut d'abord montrer
    #     que la machine reconnait un MT19937 qu'on y a mis, SOUS CETTE LECTURE-LA.
    say("\n   temoin : un MT19937 plante, lu par la carte de rang du §106")
    import random
    rng = random.Random(229_229)
    for pas_t in (21, 23):
        st = [rng.getrandbits(32) for _ in range(N)]
        st[0] |= 0x80000000
        nt = besoin + EXTRA + 20
        outs = mt_outputs(st, nt * pas_t + 8)
        rg = [(outs[t * pas_t] * KB) >> 32 for t in range(nt)]
        v, rang, tt, dt = attaque(rg, pas_t, BUDGET * 3)
        say(f"      pas {pas_t} : {v}, rang {rang:,}/{NUNK:,}, {tt} tirages, {dt:.0f}s")
        if not v.startswith("COHERENT"):
            raise SystemExit("le temoin plante n'est pas reconnu : on n'exclut rien avec ca")
    # temoin NEGATIF : des rangs au hasard doivent etre declares incoherents
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
               ("MT19937 EXCLU" if not incomplets else "INCOMPLET"))
    say(f"\n   {len(res)} pas balayes, {len(compat)} compatible(s), "
        f"{len(incomplets)} incomplet(s)")
    if incomplets:
        say(f"   NON CONCLUS, et il faut le dire : pas "
            + ", ".join(str(p) for p in incomplets))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(compat)), p=float(1.0 if not compat else 2.0 ** -900),
        verdict=verdict,
        power_at=(f"la decision est ALGEBRIQUE et non statistique : un systeme incompatible "
                  f"EXCLUT le generateur. La puissance est etablie par le temoin, pas "
                  f"supposee — un MT19937 plante et lu par la carte de rang du §106 est "
                  f"reconnu COHERENT a rang plein sur deux pas differents, et une suite de "
                  f"rangs au hasard est declaree incoherente. Le decalage interne n'est pas "
                  f"balaye parce qu'il s'absorbe dans l'etat inconnu, non parce qu'il est "
                  f"neglige. Ce qui n'est PAS couvert et se dit : la designation par indice "
                  f"dans l'ordre D'EMISSION plutot que dans le tableau trie, indistinguable "
                  f"ici comme au §106 ; et les pas hors de {STRIDES[0]}..{STRIDES[-1]}"),
        notes=(f"MT19937 SOUS LA TRONCATURE (§254) — le §106 nommait lui-meme ce trou : "
               f"« RESTE : MT19937 et WELL19937 [...] c'est le COUT DE CALCUL des formes "
               f"lineaires qui bloque, pas la donnee », cout que le §80 avait deja leve par "
               f"la recurrence. Le §88 avait bien teste MT19937, mais sous « le bonus est le "
               f"premier numero sorti », bits BAS, pas 20 — un autre modele que la designation "
               f"par indice du §106. Et le §124 ne le ferme pas non plus, sa borne exigeant "
               f"des fonctionnelles lineaires de l'etat alors que floor(u*20) est un seuil. "
               f"{len(res)} pas balayes sur {NUNK} inconnues, {len(compat)} compatibles, "
               f"{len(incomplets)} incomplets. {verdict}."))
    say("   consigne.")
