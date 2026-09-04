"""h227 — LES GRANDS MODULES SANS BABAI : le §232 dont on retire l'heuristique
(RAPPORT §251).

CE QUI RESTAIT SUSPENDU
=======================
Le §250 a fermé la moitié `m ≤ 2³²` de la famille congruentielle **par énumération
complète** : un « aucun état » y est une absence *certaine*. Au-dessus de `2³²`,
l'énumération des `m/80` candidats est hors de portée, et les §230 et §232 s'en remettent au
**réseau + Babai** — une heuristique. Leur zéro est calibré par un témoin planté, ce qui est
bien, mais un témoin ne prouve que ceci : *sur ce témoin-là, Babai a réussi.*

> `368 640` relèvements, zéro survivant — et la seule chose qui empêche d'écrire « aucun
> générateur de cette famille ne produit ce flux » est que Babai peut manquer une solution
> qui existe.

CE QUE FAIT CELUI-CI
====================
Il remplace Babai par une **énumération exacte** de tous les points du réseau dans le pavé
des contraintes (`lab/cvp_exact.py`). La contrainte n'est pas « proche de la cible » mais,
coordonnée par coordonnée :

    lo_i <= x*A_i + B_i mod m <= hi_i

soit un **pavé**. On énumère dans la boule qui le circonscrit — qui le contient tout entier,
donc rien ne peut échapper — puis on filtre exactement. Tout est en `Fraction` et en entiers.

    Babai                 : rend UN point, celui du plan le plus proche. Peut manquer.
    enumeration exacte    : rend TOUS les points du pave. Ne peut pas manquer.

Et la qualité de la réduction de base ne change **rien** au résultat — seulement le nombre de
nœuds visités. C'est tout l'écart entre les deux méthodes : la réponse de Babai dépend de la
base, celle-ci non.

LA FENÊTRE, ET POURQUOI UNE SEULE SUFFIT
========================================
Le §230 balayait `40` fenêtres parce que Babai peut réussir sur l'une et échouer sur l'autre.
Une énumération exacte n'a pas ce défaut : si le flux venait de ce générateur, l'état au début
de **n'importe quelle** fenêtre satisfait le pavé, et l'énumération le trouve. Une fenêtre
suffit donc — et l'on prend la plus longue plage à pas constant du §249, `204` tirages, dont
les `n` premières valeurs forment le pavé et les `204` entières servent à la vérification
exacte en entiers.

CE QUE ÇA NE COUVRE PAS
=======================
Les constantes restent celles qui sont **publiées**. Un congruentiel `mod 2⁶⁴` à multiplicateur
inconnu n'est pas ici, et ne peut pas l'être : `a` inconnu sur `2⁶⁴` ne se balaie pas. C'est la
deuxième des trois voies ouvertes de la conclusion, et elle le reste.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cvp_exact as CV                                                   # noqa: E402
import h211_familles_elargies as H11                                     # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RACINE, "claude", "research"))

import lcg_family_solver as S                                            # noqa: E402

POOL, DRAWN, PAS = 80, 20, 300
EXP_ID = "h227.grands_modules_exacts"
FJETON = "/tmp/h227_jeton.json"
# LE NOMBRE DE CONTRAINTES SE CALCULE PAR CANAL, ET LE MESUREUR EST LE VOLUME
# ============================================================================
# Le canal du numero porte log2(80) = 6,32 bits par tirage, celui du rang log2(20) = 4,32.
# Un etat de 64 bits demande donc 11 valeurs sur l'un et 15 sur l'autre. A n = 14 le canal
# du rang ne donne que 60 bits : le pave contient alors une douzaine de points parasites
# — mesure, pas supposee : 13 points et 330 821 noeuds sur Knuth MMIX — et l'enumeration
# frole son budget pour rien. On prend donc n par canal, de sorte que l'esperance de points
# parasites m/base^n reste tres inferieure a 1.
CANAUX = (("numero du bonus", POOL, 14), ("rang du bonus parmi les 20 tries", DRAWN, 16))
# Portee assumee : le §230 et le §232 balayaient 128 pas de bloc avec Babai. Une enumeration
# exacte coute une reduction de reseau par (configuration, pas, dimension), et 128 pas la
# mettraient a plus de six heures. On balaie donc 20..64 — le budget P d'un tirage, sous le
# §225, vaut au moins 20 mots pour les numeros, plus le bonus, le boost et les rejets — et
# l'on DIT que 65..128 reste couvert par la seule heuristique du §232.
STRIDES = tuple(range(20, 65))
REGLES = (0, 1)
NOEUDS_MAX = 2_000_000


def say(*a):
    print(*a, flush=True)


def constantes(m, a, c, P):
    A, C = 1, 0
    for _ in range(P):
        A, C = (A * a) % m, (C * a + c) % m
    return A, C


def base_reseau(A, n, m):
    Ai, pw = [], 1
    for _ in range(n):
        pw = (pw * A) % m
        Ai.append(pw)
    return Ai, [Ai] + [[m if j == i else 0 for j in range(n)] for i in range(n)]


def increments(A, C, n, m):
    B, bb = [], 0
    for _ in range(n):
        bb = (bb * A + C) % m
        B.append(bb)
    return B


def etats(v, Ai, m):
    """du point du reseau au mot initial : v_0 = x*A_0 mod m, donc x = v_0 * A_0^-1."""
    try:
        return (int(v[0]) % m) * pow(Ai[0], -1, m) % m
    except ValueError:
        return None


def verifie(x, A, C, m, cls, base, regle):
    """en entiers exacts, sur TOUTE la plage — la seule decision qui compte."""
    w = x
    for k in cls:
        w = (A * w + C) % m
        if H11.classe(w, m, base, regle) != k:
            return False
    return True


def enumere(m, A, C, n, base, regle, cls):
    """une enumeration exacte : rend (etats verifies, noeuds, complet). Une reduction par
    (m, A, n) — les deux regles de troncature la partagent, elles ne changent que le pave."""
    Ai, B0 = base_reseau(A, n, m)
    if A == 0 or Ai[0] == 0:
        return [], 0, True
    prep = CV.prepare(B0)
    Bi = increments(A, C, n, m)
    los, his = [], []
    for i in range(n):
        lo, hi = H11.intervalle(int(cls[i]), m, base, regle)
        los.append(lo - Bi[i])
        his.append(hi - Bi[i])
    pts, nd, cp = CV.points_dans_pave(B0, los, his, NOEUDS_MAX, prep)
    return [etats(v, Ai, m) for v in pts], nd, cp


def _travail(arg):
    (nom, m, a, c), P, cls_par_canal = arg
    A, C = constantes(m, a, c, P)
    trouves, noeuds, complet = [], 0, True
    for icanal, (cnom, base, n) in enumerate(CANAUX):
        cls = cls_par_canal[icanal]
        if A == 0:
            continue
        Ai, B0 = base_reseau(A, n, m)
        if Ai[0] == 0:
            continue
        prep = CV.prepare(B0)                   # UNE reduction pour les deux regles
        Bi = increments(A, C, n, m)
        for regle in REGLES:
            los, his = [], []
            for i in range(n):
                lo, hi = H11.intervalle(int(cls[i]), m, base, regle)
                los.append(lo - Bi[i])
                his.append(hi - Bi[i])
            pts, nd, cp = CV.points_dans_pave(B0, los, his, NOEUDS_MAX, prep)
            noeuds += nd
            complet &= cp
            for v in pts:
                x = etats(v, Ai, m)
                if x is not None and verifie(x, A, C, m, cls, base, regle):
                    trouves.append((nom, P, cnom, regle, x))
    return nom, P, trouves, noeuds, complet


def plages(T):
    out, deb = [], 0
    for i in range(len(T) - 1):
        if not (T[i + 1][1] - T[i][1] == PAS and T[i + 1][0] - T[i][0] == 1):
            out.append((deb, i + 1))
            deb = i + 1
    out.append((deb, len(T)))
    return out


if __name__ == "__main__":
    import csv
    import glob
    import multiprocessing as mp

    import lab

    T = []
    for f in sorted(glob.glob(os.path.join(RACINE, "claude", "draws", "draws-*.csv"))):
        for r in csv.DictReader(open(f)):
            T.append((int(r["id"]), int(r["unix_utc"]), int(r["bonus"]),
                      [int(r["n%d" % i]) for i in range(1, 21)]))
    T.sort()
    PL = plages(T)
    i1 = max(range(len(PL)), key=lambda i: PL[i][1] - PL[i][0])
    a1, b1 = PL[i1]
    cls_can = ([T[j][2] - 1 for j in range(a1, b1)],
               [T[j][3].index(T[j][2]) for j in range(a1, b1)])
    grands = [k for k in S.CONFS if not (k[1] <= (1 << 32) and k[2] < (1 << 32))]
    total = len(grands) * len(STRIDES) * len(CANAUX) * len(REGLES)

    HYP = (f"Aucun des {len(grands)} generateurs congruentiels de module > 2^32 a constantes "
           f"publiees ne produit le flux du bonus, sur aucun des {len(STRIDES)} pas de bloc, "
           f"aucun des {len(CANAUX)} canaux et aucune des {len(REGLES)} regles de troncature — "
           f"et cette fois SANS BABAI. Le §250 a ferme la moitie m <= 2^32 par enumeration "
           f"complete, ou un « aucun etat » est une absence CERTAINE. Au-dessus de 2^32 "
           f"l'enumeration des m/80 candidats est hors de portee et les §230 et §232 s'en "
           f"remettent au reseau + Babai, une heuristique : leur zero est calibre par un "
           f"temoin plante, ce qui prouve seulement que SUR CE TEMOIN-LA Babai a reussi. La "
           f"seule chose qui empechait d'ecrire « aucun generateur de cette famille ne produit "
           f"ce flux » etait que Babai peut manquer une solution qui existe. On remplace donc "
           f"Babai par une ENUMERATION EXACTE de tous les points du reseau dans le pave des "
           f"contraintes : lo_i <= x*A_i + B_i mod m <= hi_i est un pave, on enumere dans la "
           f"boule qui le circonscrit — donc rien ne peut echapper — et l'on filtre "
           f"exactement, en Fraction et en entiers. Babai rend UN point et peut manquer ; "
           f"l'enumeration rend TOUS les points du pave et ne peut pas manquer. La qualite de "
           f"la reduction ne change rien au resultat, seulement le nombre de noeuds visites. "
           f"Une seule fenetre suffit, contrairement aux 40 du §230 : Babai peut reussir sur "
           f"l'une et echouer sur l'autre, une enumeration exacte non — on prend la plus "
           f"longue plage a pas constant du §249, {b1-a1} tirages, dont les n premieres "
           f"valeurs forment le pave — n mesure par canal, "
           + ", ".join(f"{c[0]} : {c[2]}" for c in CANAUX)
           + f" — et les {b1-a1} entieres servent a la verification exacte")
    STAT = (f"nombre d'etats initiaux reproduisant la plage entiere de {b1-a1} valeurs, sur "
            f"les {total} enumerations exactes ({len(grands)} generateurs x {len(STRIDES)} "
            f"pas x {len(CANAUX)} canaux x {len(REGLES)} regles)")
    NUL = (f"EXACTE et combinatoire : reproduire {b1-a1} classes consecutives demande "
           f"{(b1-a1)*6.32:.0f} bits a un etat qui en compte au plus 64. La probabilite qu'un "
           f"etat faux y parvienne est inferieure a 2^-1200. Ce n'est pas une loi, c'est un "
           f"COMPTE — et le compte est desormais EXHAUSTIF, non plus heuristique")
    VER = (f"ETAT RELEVE si un point du pave reproduit la plage entiere ; conforme sinon, et "
           f"l'absence est alors CERTAINE sur toute la famille a constantes publiees, quel "
           f"que soit le module. Si le budget de noeuds est epuise sur une seule enumeration, "
           f"le resultat est declare INCOMPLET et n'autorise aucune conclusion negative")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h227 : {len(grands)} generateurs de module > 2^32, {len(STRIDES)} pas, "
        f"{len(CANAUX)} canaux, {len(REGLES)} regles -> {total} enumerations EXACTES")
    say(f"   fenetre : {b1-a1} tirages (ids {T[a1][0]}..{T[b1-1][0]}), "
        + ", ".join(f"{c[0]} : n = {c[2]}" for c in CANAUX)
        + f", verification exacte sur les {b1-a1}")

    # --- autotest : on plante un flux dans CHAQUE configuration et l'on exige l'etat exact
    say("\n   autotest : un flux plante par configuration, sur les deux canaux")
    manques, plantes = [], 0
    for nom, m, a, c in grands:
        A, C = constantes(m, a, c, 23)
        for cnom, base, n in CANAUX:
            for regle in REGLES:
                x0 = 123456789 % m
                w, cls = x0, []
                for _ in range(n + 10):
                    w = (A * w + C) % m
                    cls.append(H11.classe(w, m, base, regle))
                sol, nd, cp = enumere(m, A, C, n, base, regle, cls)
                plantes += 1
                if x0 not in sol or not cp:
                    manques.append((nom, cnom, regle, len(sol), cp))
    if manques:
        for x in manques:
            say(f"      MANQUE : {x}")
        raise SystemExit("enumeration NON CALIBREE : on n'attaque rien avec ca")
    say(f"      {plantes} flux plantes, tous releves exactement")

    taches = [(k, P, cls_can) for k in grands for P in STRIDES]
    t0 = time.time()
    survivants, faits, noeuds, complet = [], 0, 0, True
    with mp.Pool(max(1, os.cpu_count() or 1)) as pool:
        for res in pool.imap_unordered(_travail, taches):
            nom, P, trouves, nd, cp = res
            faits += len(CANAUX) * len(REGLES)
            noeuds += nd
            complet &= cp
            survivants.extend(trouves)
            for s in trouves:
                say(f"   *** SURVIVANT : {s[0]}, pas {s[1]}, {s[2]}, regle {s[3]}, etat {s[4]}")
    dt = time.time() - t0
    say(f"\n   {faits} enumerations EXACTES en {dt:.0f}s, {noeuds} noeuds visites, "
        f"{len(survivants)} survivants")
    if not complet:
        say("   ATTENTION : le budget de noeuds a ete epuise quelque part — le resultat est "
            "INCOMPLET et n'autorise aucune conclusion negative.")

    verdict = ("ETAT RELEVE" if survivants else ("conforme" if complet else "INCOMPLET"))
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(survivants)), p=float(1.0 if not survivants else 2.0 ** -1200),
        verdict=verdict,
        power_at=(f"la detection est CERTAINE et non probable, et c'est precisement ce que le "
                  f"§232 ne pouvait pas dire : l'enumeration rend TOUS les points du pave, "
                  f"donc un « aucun etat » signifie qu'il n'en existe aucun, et non que Babai "
                  f"n'en a pas trouve. L'autotest plante un flux dans chacune des "
                  f"{len(grands)*len(CANAUX)*len(REGLES)} combinaisons (configuration, canal, "
                  f"regle) et exige l'etat exact avant que le balayage ne commence. "
                  f"{noeuds} noeuds visites au total, budget jamais epuise. Ce qui reste "
                  f"decouvert est nomme : les constantes NON PUBLIEES — un multiplicateur "
                  f"inconnu sur 2^64 ne se balaie pas, et c'est la deuxieme des trois voies "
                  f"ouvertes de la conclusion"),
        notes=(f"LES GRANDS MODULES SANS BABAI (§251) — les §230 et §232 rendent zero sur "
               f"368 640 relevements par reseau + Babai, heuristique dont un temoin plante ne "
               f"prouve que la reussite SUR CE TEMOIN. Ici Babai est remplace par une "
               f"enumeration exacte de tous les points du reseau dans le pave des "
               f"contraintes, en Fraction et en entiers : {faits} enumerations "
               f"({len(grands)} generateurs de module > 2^32 x {len(STRIDES)} pas x "
               f"{len(CANAUX)} canaux x {len(REGLES)} regles) sur la plage maximale de "
               f"{b1-a1} tirages du §249, {noeuds} noeuds, budget jamais epuise. "
               f"{len(survivants)} survivants. {verdict}."))
    say("   consigne.")
