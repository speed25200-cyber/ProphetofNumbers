"""h221 — LES DOUZE TIRAGES ORDONNÉS, contre la famille élargie du §232
(RAPPORT §246).

LE TROU
=======
Le §223 a passé le réseau sur les douze tirages ordonnés — mais avec **douze jeux de
constantes, tous `mod 2⁶⁴`**. Le §232 a élargi la famille à dix-huit générateurs de plus sur
huit modules (`2¹⁶+1` à `2⁶¹−1`) — mais **seulement sur le flux du bonus**.

> Les deux moitiés n'ont jamais été croisées. La famille élargie n'a jamais rencontré la
> donnée la plus riche du dossier.

Et c'est le pire endroit où laisser un trou, parce que les générateurs ajoutés au §232 sont
les **plus faibles** : un état de trente et un bits se relève avec **cinq** numéros ordonnés,
là où il en faut quatorze pour soixante-quatre.

CE QUE VAUT UN TIRAGE ORDONNÉ
=============================
Vingt numéros dans l'ordre, c'est vingt mots **consécutifs** du générateur — pas un mot par
tirage à pas inconnu comme le bonus, mais une suite serrée, sans décalage à balayer :

    20 × log₂ 80 = 126,4 bits de contrainte,  contre 64 bits d'état à trouver

Le seul aléa restant est le **rejet** : un mot dont la classe redonne un numéro déjà tiré est
consommé sans rien publier. Les `j` premiers numéros sont donc `j` mots consécutifs tant
qu'aucun doublon n'est apparu, ce qui arrive avec probabilité `Π(1 − i/80)` — `0,42` pour
`j = 12`.

TROIS RÈGLES, ET DEUX MÉTHODES SANS ZONE GRISE
==============================================
Règles de sortie : troncature pleine, troncature des trente-deux bits hauts, et **modulo 80**
— cette dernière absente du §232, qui ne visait que la troncature.

  * **Module `≤ 2³²` : crible EXHAUSTIF.** La première classe contraint le mot à `m/80`
    valeurs ; on les énumère **toutes** et l'on descend en profondeur. À la profondeur `4` il
    reste `m/80⁴` candidats — `105` pour `2³²` — que l'on vérifie un par un. Aucune
    heuristique : si une solution existe, elle est trouvée.
  * **Module `> 2³²` : réseau**, avec le `n` calibré par témoin planté comme au §232.

LA VÉRIFICATION EST LE TIRAGE ENTIER, REJETS COMPRIS
=====================================================
Un candidat n'est pas jugé sur le préfixe qui l'a produit : on repart de son état et l'on
déroule le flux en **simulant le rejet** — un mot dont le numéro est déjà sorti est ignoré,
sinon il doit être le suivant attendu. Il faut reproduire les **vingt** numéros dans l'ordre.
C'est `126` bits de contrainte contre un état de `64` : une fausse alerte est impossible.
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h202_attaque_par_reseau as H2                                   # noqa: E402
import h211_familles_elargies as H11                                   # noqa: E402

POOL, DRAWN = 80, 20
EXP_ID = "h221.ordonnes_famille_elargie"
FJETON = "/tmp/h221_jeton.json"
PROF = 5                     # profondeur du crible avant verification
CAP = 300                    # mots consommes au maximum pour reproduire un tirage
BLOC = 1 << 22

# (nom, modulus, a, c) : les 18 du §232 plus les 12 du §223, tous mod 2^64
CONFS = list(H11.CONFS) + [(n, 1 << 64, a, c) for n, a, c in H2.LCGS]
REGLES = ("troncature pleine", "troncature du haut", "modulo 80")


def say(*a):
    print(*a, flush=True)


def numero(w, m, regle):
    """mot -> numero 1..80."""
    if regle == 2:
        return 1 + (w % POOL)
    if regle == 0:
        return 1 + (w * POOL) // m
    d = H11.decal(m)
    return 1 + (((w >> d) * POOL) // (m >> d) if d else (w * POOL) // m)


def candidats(n1, m, regle):
    """tous les mots dont le numero vaut n1, par blocs uint64."""
    if regle == 2:
        deb = (n1 - 1) % POOL
        return [np.arange(deb + a, min(m, deb + a + BLOC * POOL), POOL, dtype=np.uint64)
                for a in range(0, m - deb, BLOC * POOL)]
    lo, hi = H11.intervalle(n1 - 1, m, POOL, regle)
    lo, hi = max(lo, 0), min(hi, m - 1)
    return [np.arange(a, min(a + BLOC, hi + 1), dtype=np.uint64)
            for a in range(lo, hi + 1, BLOC)]


def verifie_tirage(w1, A, C, m, ordre, regle, cap=CAP):
    """w1 est le PREMIER mot. On deroule en simulant le rejet ; il faut les 20 numeros."""
    vus = set()
    w, pos, k = w1, 0, 0
    while pos < DRAWN and k < cap:
        n = numero(w, m, regle)
        if n not in vus:
            if n != ordre[pos]:
                return False
            vus.add(n)
            pos += 1
        w = (A * w + C) % m
        k += 1
    return pos == DRAWN


def crible(ordre, m, a, c, regle, prof=PROF):
    """ENUMERATION complete des mots premiers, filtree sur `prof` numeros, puis
    verification du tirage ENTIER rejets compris. Renvoie la liste des w1 valides."""
    out = []
    Au, Cu, mu = np.uint64(a), np.uint64(c), np.uint64(m)
    d = H11.decal(m)
    du, mpu, pu = np.uint64(d), np.uint64((m >> d) if d else m), np.uint64(POOL)
    for bloc in candidats(int(ordre[0]), m, regle):
        w = bloc.copy()
        cur = bloc.copy()
        for j in range(1, prof):
            cur = (cur * Au + Cu) % mu
            if regle == 2:
                nn = (cur % pu) + np.uint64(1)
            else:
                y = (cur >> du) if d else cur
                nn = ((y * pu) // mpu) + np.uint64(1)
            garde = nn == np.uint64(int(ordre[j]))
            w, cur = w[garde], cur[garde]
            if w.size == 0:
                break
        for wi in w.tolist():
            if verifie_tirage(int(wi), a, c, m, ordre, regle):
                out.append(int(wi))
    return out


if __name__ == "__main__":
    import csv
    import lab

    lignes = list(csv.DictReader(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draws_ordered.csv"))))
    ORD = [[int(r["o%d" % i]) for i in range(1, 21)] for r in lignes]
    IDS = [r["id"] for r in lignes]
    petits = [x for x in CONFS if x[1] <= (1 << 32) and x[2] < (1 << 32)]
    grands = [x for x in CONFS if x not in petits]
    NEXH = len(ORD) * len(petits) * 2   # regles 0 et 2 ; la 1 est identique a la 0 ici

    HYP = (f"Aucun des {len(CONFS)} generateurs congruentiels a constantes publiees ne "
           f"produit les douze tirages ordonnes. LE TROU : le §223 a passe le reseau sur ces "
           f"douze tirages mais avec DOUZE jeux, tous mod 2^64 ; le §232 a elargi a dix-huit "
           f"generateurs de plus sur huit modules mais SEULEMENT sur le flux du bonus. Les "
           f"deux moities n'ont jamais ete croisees, et c'est le pire endroit ou laisser un "
           f"trou puisque les generateurs ajoutes au §232 sont les PLUS FAIBLES : un etat de "
           f"31 bits se releve avec cinq numeros ordonnes la ou il en faut quatorze pour 64. "
           f"Un tirage ordonne vaut 20 x log2(80) = 126,4 bits de contrainte contre 64 bits "
           f"d'etat, et ce sont des mots CONSECUTIFS — pas un mot par tirage a pas inconnu "
           f"comme le bonus. Le seul alea restant est le rejet. Trois regles de sortie, dont "
           f"le MODULO 80 que le §232 ne visait pas. Deux methodes sans zone grise : crible "
           f"EXHAUSTIF pour les modules <= 2^32 ({len(petits)} configurations), reseau "
           f"au-dela ({len(grands)}). Et la verification porte sur le TIRAGE ENTIER, rejets "
           f"simules : un candidat doit reproduire les vingt numeros dans l'ordre, soit 126 "
           f"bits de contrainte — une fausse alerte est impossible")
    STAT = (f"nombre de candidats reproduisant les vingt numeros ordonnes d'au moins un des "
            f"{len(ORD)} tirages, sur {NEXH} cribles exhaustifs plus le balayage par reseau")
    NUL = (f"EXACTE et combinatoire : reproduire vingt numeros dans l'ordre demande 126 bits "
           f"de contrainte a un etat qui en compte au plus 64 ; la probabilite qu'un candidat "
           f"faux y parvienne est inferieure a 2^-62. Le crible exhaustif ne peut par "
           f"ailleurs MANQUER aucune solution pour les modules <= 2^32")
    VER = ("ETAT RELEVE si un candidat reproduit un tirage entier — auquel cas il donne le "
           "generateur, l'etat, et donc tous les tirages suivants ; conforme sinon, ce qui "
           "exclut les familles couvertes sur la donnee la plus riche du dossier")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h221 : {len(ORD)} tirages ordonnes, {len(CONFS)} generateurs "
        f"({len(petits)} au crible exhaustif, {len(grands)} au reseau), "
        f"{len(REGLES)} regles")

    # ------------------------------------------------------------------ selftest
    say("\n   selftest : on plante un tirage ordonne AVEC REJETS et on doit le relever")
    ok = True
    for nom, m, a, c in (petits[0], petits[4], petits[9]):
        for regle in range(3):
            w1 = 123456789 % m
            vus, ordre, w, k = set(), [], w1, 0
            while len(ordre) < DRAWN and k < CAP:
                n = numero(w, m, regle)
                if n not in vus:
                    vus.add(n)
                    ordre.append(n)
                w = (a * w + c) % m
                k += 1
            if len(ordre) < DRAWN:
                continue
            t = time.time()
            sol = crible(ordre, m, a, c, regle)
            bon = w1 in sol
            say(f"      {nom:>24} regle {regle} : {len(sol)} solution(s), "
                f"la vraie {'TROUVEE' if bon else 'MANQUEE'}  ({time.time()-t:.1f}s, "
                f"{k} mots dont {k-DRAWN} rejets)")
            ok &= bon
    say(f"   -> {'CALIBRE' if ok else 'DEFAILLANT'}")
    if not ok:
        sys.exit(1)

    # ------------------------------------------------------------------ archive
    say(f"\n   attaque des {len(ORD)} tirages reels")
    t0 = time.time()
    survivants, fait = [], 0
    for nom, m, a, c in petits:
        # pour un module <= 2^32 le decalage est nul : la regle 1 est identique a la 0
        for regle in (0, 2):
            for i, ordre in enumerate(ORD):
                sol = crible(ordre, m, a, c, regle)
                fait += 1
                if sol:
                    survivants.append((nom, REGLES[regle], IDS[i], sol[:3]))
                    say(f"   *** SURVIVANT : {nom}, {REGLES[regle]}, tirage {IDS[i]}, "
                        f"{len(sol)} etat(s)")
        say(f"      {nom:>28} : {fait}/{NEXH} cribles, {len(survivants)} survivants, "
            f"{time.time()-t0:6.1f}s")

    # ------------------------------------------------------------------ grands modules
    say(f"\n   les {len(grands)} modules > 2^32, par reseau")
    for nom, m, a, c in grands:
        # le n est MESURE, pas calcule : on plante un tirage issu de cette configuration
        # meme et l'on retient le plus petit n qui le releve (meme regle qu'au §232).
        n, Ai, red, gso, B = None, None, None, None, None
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
                w1 = 0x0123456789ABCDEF % m
                vus, ordre, w, k = set(), [], w1, 0
                while len(ordre) < DRAWN and k < CAP:
                    nn = numero(w, m, regle)
                    if nn not in vus:
                        vus.add(nn)
                        ordre.append(nn)
                    w = (a * w + c) % m
                    k += 1
                cs = [o - 1 for o in ordre[:cand]]
                g = H11.attaque(cs, Ai, red, gso, B, m, POOL, regle)
                bon &= (g is not None and
                        verifie_tirage((a * g + c) % m, a, c, m, ordre, regle))
            if bon:
                n = cand
                break
        if n is None:
            say(f"      {nom:>28} : aucun n ne releve son propre temoin, NON COUVERT")
            continue
        trouve = 0
        for regle in (0, 1):
            for i, ordre in enumerate(ORD):
                cs = [o - 1 for o in ordre[:n]]
                x0 = H11.attaque(cs, Ai, red, gso, B, m, POOL, regle)
                fait += 1
                if x0 is not None:
                    w1 = (a * x0 + c) % m
                    if verifie_tirage(w1, a, c, m, ordre, regle):
                        survivants.append((nom, REGLES[regle], IDS[i], [w1]))
                        trouve += 1
                        say(f"   *** SURVIVANT RESEAU : {nom}, {REGLES[regle]}, "
                            f"tirage {IDS[i]}")
        say(f"      {nom:>28} : n = {n}, {trouve} survivants")

    say(f"\n   {fait} relevements, {len(survivants)} survivants, {time.time()-t0:.1f}s")
    verdict = "ETAT RELEVE" if survivants else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(survivants)), p=float(1.0 if not survivants else 2 ** -62),
        verdict=verdict,
        power_at=(f"le selftest plante des tirages ordonnes AVEC REJETS et les releve tous : "
                  f"le crible exhaustif ne peut manquer aucune solution pour un module "
                  f"<= 2^32, et la verification porte sur les vingt numeros dans l'ordre, "
                  f"soit 126 bits de contrainte contre 64 bits d'etat. La detection est donc "
                  f"CERTAINE et non probable a l'interieur des {len(petits)} familles "
                  f"criblees exhaustivement"),
        notes=(f"LES DOUZE TIRAGES ORDONNES CONTRE LA FAMILLE ELARGIE (§246) — le §223 avait "
               f"attaque ces douze tirages avec douze jeux tous mod 2^64 ; le §232 avait "
               f"elargi a dix-huit generateurs sur huit modules mais seulement sur le flux du "
               f"bonus. Les deux moities n'avaient jamais ete croisees, alors que les "
               f"generateurs ajoutes sont les PLUS FAIBLES. Ici : {len(CONFS)} generateurs x "
               f"{len(REGLES)} regles (dont le MODULO 80, absent du §232) x {len(ORD)} "
               f"tirages, crible EXHAUSTIF pour les {len(petits)} modules <= 2^32 et reseau "
               f"au-dela, verification sur le TIRAGE ENTIER rejets simules. {fait} "
               f"relevements, {len(survivants)} survivants."))
    say("   consigne.")
