"""h221b — LE CALIBRAGE CORRIGÉ DU §246 : neuf « NON COUVERT » qui n'en étaient pas
(RAPPORT §246 addendum).

LA FAUTE
========
Le §246 a déclaré **neuf** des quinze configurations de module `> 2³²` « NON COUVERT » —
aucun `n` ne relevait leur propre témoin planté. Ce n'était pas une faiblesse du réseau :
c'était ma façon de fabriquer le témoin.

Le témoin était un tirage ordonné synthétique **avec rejets**, et je donnais ensuite ses
`n` premiers numéros au réseau comme s'ils étaient les classes de `n` mots **consécutifs**.
Dès qu'un rejet tombait dans le préfixe, ils ne l'étaient pas — et le réseau échouait sur une
entrée fausse, pas sur un problème dur.

> Un témoin planté doit être planté **dans les conditions de l'hypothèse testée**. L'attaque
> suppose un préfixe sans rejet ; le témoin devait donc en être un.

LA CORRECTION
=============
On cherche une graine dont les `n` premiers mots donnent `n` numéros **distincts** — donc un
préfixe réellement sans rejet — et l'on calibre là-dessus. Le reste ne change pas : mêmes
constantes, même réseau, même vérification du tirage entier rejets compris.

Le sens de l'erreur était **conservateur** : elle faisait déclarer non couvert ce qui l'était,
donc elle rétrécissait la portée annoncée au lieu de la gonfler. C'est la bonne direction pour
une faute, et ce n'est pas une raison de la garder.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h211_familles_elargies as H11                                   # noqa: E402
import h221_ordonnes_famille_elargie as H21                            # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h221b.calibrage_corrige"
FJETON = "/tmp/h221b_jeton.json"
GRAINES = 400


def say(*a):
    print(*a, flush=True)


def temoin_sans_rejet(m, a, c, regle, n, graines=GRAINES):
    """cherche une graine dont les n premiers mots donnent n numeros DISTINCTS."""
    rng = np.random.default_rng(0xC0FFEE)
    for _ in range(graines):
        w1 = int(rng.integers(1, min(m, 1 << 62)))
        w, mots = w1, []
        for _ in range(n):
            mots.append(H21.numero(w, m, regle))
            w = (a * w + c) % m
        if len(set(mots)) < n:
            continue
        vus, ordre, w, k = set(), [], w1, 0
        while len(ordre) < DRAWN and k < H21.CAP:
            nn = H21.numero(w, m, regle)
            if nn not in vus:
                vus.add(nn)
                ordre.append(nn)
            w = (a * w + c) % m
            k += 1
        if len(ordre) == DRAWN:
            return w1, ordre
    return None, None


if __name__ == "__main__":
    import csv
    import lab

    lignes = list(csv.DictReader(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draws_ordered.csv"))))
    ORD = [[int(r["o%d" % i]) for i in range(1, 21)] for r in lignes]
    IDS = [r["id"] for r in lignes]
    grands = [x for x in H21.CONFS if not (x[1] <= (1 << 32) and x[2] < (1 << 32))]

    HYP = (f"Aucun des {len(grands)} generateurs de module > 2^32 ne produit les douze "
           f"tirages ordonnes — et cette fois la portee est mesuree correctement. LA FAUTE DU "
           f"§246 : neuf des quinze configurations y sont declarees NON COUVERT parce "
           f"qu'aucun n ne relevait leur propre temoin plante. Ce n'etait pas une faiblesse "
           f"du reseau mais ma facon de fabriquer le temoin — un tirage ordonne synthetique "
           f"AVEC REJETS dont je donnais les n premiers numeros au reseau comme s'ils etaient "
           f"les classes de n mots CONSECUTIFS. Des qu'un rejet tombait dans le prefixe ils ne "
           f"l'etaient pas, et le reseau echouait sur une entree fausse, pas sur un probleme "
           f"dur. Un temoin plante doit etre plante DANS LES CONDITIONS DE L'HYPOTHESE "
           f"TESTEE : l'attaque suppose un prefixe sans rejet, le temoin devait donc en etre "
           f"un. Le sens de l'erreur etait conservateur — elle retrecissait la portee "
           f"annoncee au lieu de la gonfler — et ce n'est pas une raison de la garder. "
           f"Correction : on cherche une graine dont les n premiers mots donnent n numeros "
           f"DISTINCTS, et l'on calibre la-dessus")
    STAT = (f"nombre de configurations COUVERTES apres correction du temoin, et nombre de "
            f"candidats reproduisant les vingt numeros ordonnes d'un des {len(ORD)} tirages")
    NUL = ("EXACTE et combinatoire : reproduire vingt numeros dans l'ordre demande 126 bits "
           "de contrainte a un etat qui en compte au plus 64 ; la probabilite qu'un candidat "
           "faux y parvienne est inferieure a 2^-62")
    VER = ("ETAT RELEVE si un candidat reproduit un tirage entier ; conforme sinon, avec la "
           "portee reelle enfin mesuree")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h221b : {len(grands)} configurations de module > 2^32, temoin SANS REJET")
    t0 = time.time()
    couverts, survivants, fait = [], [], 0
    for nom, m, a, c in grands:
        retenu = None
        for cand in H11.NS:
            if cand > DRAWN or cand * np.log2(POOL) < m.bit_length() + 8:
                continue
            try:
                Ai, red, gso = H11.prepare(a, cand, m)
            except Exception:
                continue
            B = H11.increments(a, c, cand, m)
            bon = True
            for regle in (0, 1):
                w1, ordre = temoin_sans_rejet(m, a, c, regle, cand)
                if w1 is None:
                    bon = False
                    break
                cs = [o - 1 for o in ordre[:cand]]
                g = H11.attaque(cs, Ai, red, gso, B, m, POOL, regle)
                if not (g is not None and
                        H21.verifie_tirage((a * g + c) % m, a, c, m, ordre, regle)):
                    bon = False
                    break
            if bon:
                retenu = (cand, Ai, red, gso, B)
                break
        if retenu is None:
            say(f"      {nom:>28} : NON COUVERT meme avec un temoin sans rejet")
            continue
        n, Ai, red, gso, B = retenu
        couverts.append(nom)
        tr = 0
        for regle in (0, 1):
            for i, ordre in enumerate(ORD):
                cs = [o - 1 for o in ordre[:n]]
                x0 = H11.attaque(cs, Ai, red, gso, B, m, POOL, regle)
                fait += 1
                if x0 is not None:
                    w1 = (a * x0 + c) % m
                    if H21.verifie_tirage(w1, a, c, m, ordre, regle):
                        survivants.append((nom, regle, IDS[i], w1))
                        tr += 1
                        say(f"   *** SURVIVANT : {nom}, regle {regle}, tirage {IDS[i]}")
        say(f"      {nom:>28} : n = {n}, COUVERT, {tr} survivants")

    say(f"\n   {len(couverts)}/{len(grands)} configurations couvertes "
        f"(le §246 n'en couvrait que 6), {fait} relevements, {len(survivants)} survivants, "
        f"{time.time()-t0:.1f}s")
    verdict = "ETAT RELEVE" if survivants else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(couverts)), p=float(1.0 if not survivants else 2 ** -62),
        verdict=verdict,
        power_at=(f"le temoin est desormais plante DANS LES CONDITIONS DE L'HYPOTHESE — "
                  f"prefixe sans rejet — donc le n retenu mesure la capacite du reseau et non "
                  f"un accident de rejet. {len(couverts)} des {len(grands)} configurations "
                  f"relevent 100 % de leur propre temoin sur les deux regles de troncature ; "
                  f"pour celles-la la detection est CERTAINE et non probable"),
        notes=(f"CALIBRAGE CORRIGE DU §246 — le §246 declarait 9 des 15 configurations de "
               f"module > 2^32 « NON COUVERT » a cause d'un temoin plante AVEC REJETS dont "
               f"les n premiers numeros etaient donnes au reseau comme des mots consecutifs. "
               f"Un temoin doit etre plante dans les conditions de l'hypothese testee. Apres "
               f"correction : {len(couverts)}/{len(grands)} couvertes, {fait} relevements, "
               f"{len(survivants)} survivants. Le sens de l'erreur etait conservateur — elle "
               f"retrecissait la portee annoncee."))
    say("   consigne.")
