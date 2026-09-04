"""h226 — LE FLUX DU BONUS PAR ÉNUMÉRATION COMPLÈTE : le §232 sans son heuristique
(RAPPORT §250).

CE QUE LE §232 A FERMÉ, ET COMMENT
==================================
Le §232 rend `0` sur `368 640` relèvements du flux du bonus, sur dix-huit générateurs et huit
modules. C'est le zéro le plus large du dossier. Mais il est obtenu par **réseau + Babai**, et
Babai est une **heuristique** : le vecteur rendu par le plan le plus proche n'est pas toujours
le plus proche. Le §232 le savait et s'en est protégé de deux façons — un témoin planté par
configuration, et *« en doublon, le crible exhaustif sur **deux** configurations, tous les pas,
deux fenêtres »*, soit `1 024` cribles.

    368 640 relevements par reseau      0 survivant   <- heuristique, calibree
      1 024 cribles exhaustifs          0 solution    <- certain, mais sur 2 configurations

> Deux configurations sur dix-huit, c'est un **contrôle**, pas une couverture. Le zéro large
> reste suspendu à une heuristique.

CE QUE FAIT CELUI-CI
====================
Le même balayage, mais **par énumération complète**, pour tous les modules `m ≤ 2³²` — donc
sans Babai nulle part. La première classe contraint l'état à `m/POOL` valeurs ; on les parcourt
**toutes**.

Et il n'y a **pas de rejet** ici, contrairement au §248 : le bonus est publié une fois par
tirage, quoi qu'il arrive. La chaîne est donc exacte et sans arbitrage — `A = a^P mod m`,
`C = c·(A−1)/(a−1)` sous le §225, et chaque pas doit rendre la classe suivante.

LE PLAFOND DU §249 DÉCIDE DE LA FENÊTRE
=======================================
Le §249 montre qu'aucune plage à pas constant ne dépasse `204` tirages. On crible donc **sur
une plage entière** — `204` valeurs consécutives — et l'on vérifie sur une **seconde** plage,
qui n'a jamais servi à choisir. C'est exactement la contrainte que le §230 s'imposait déjà en
gardant ses fenêtres « entièrement à l'intérieur d'une nuit », mais ici la fenêtre est maximale
au lieu d'être arbitraire.

`204` valeurs de bonus valent `204 × 6,32 = 1 289` bits de contrainte sur un état qui en compte
au plus `32`. Il n'y a pas de zone grise.
"""

import csv
import glob
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RACINE, "claude", "research"))

import lcg_family_solver as S                                            # noqa: E402

POOL, DRAWN, PAS = 80, 20, 300
EXP_ID = "h226.bonus_crible_complet"
FJETON = "/tmp/h226_jeton.json"
PROF = 6                       # classes filtrees en numpy avant la verification exacte
STRIDES = tuple(range(20, 129))
CANAUX = (("numero du bonus", POOL), ("rang du bonus parmi les 20 tries", DRAWN))
BLOC = 1 << 22


def say(*a):
    print(*a, flush=True)


def constantes(m: int, a: int, c: int, P: int):
    """le pas de bloc du §225 : P mots par tirage, donc la chaine du bonus est elle-meme
    un LCG de constantes (a^P, c*(a^P - 1)/(a - 1)) — la somme geometrique, calculee
    terme a terme pour rester exacte quand a - 1 n'est pas inversible modulo m."""
    A, C = 1, 0
    for _ in range(P):
        A, C = (A * a) % m, (C * a + c) % m
    return A, C


def candidats(cl: int, m: int, mapping: int, pool: int):
    """tous les mots dont la classe vaut cl (0-indexe), par blocs uint64. COMPLET.

    Meme decoupage que `lcg_family_solver.candidats`, mais avec un vivier libre : le canal
    du rang a vingt classes, pas quatre-vingts.

    Le decoupage est un GENERATEUR, pas une liste : sur le canal du rang un module de 2^32
    donne 2^32/20 = 215 millions de candidats, soit 1,7 Go si on les materialise d'un coup —
    et il y a un processus par coeur. On n'en garde qu'un bloc a la fois.
    """
    d = S.haut32(m)
    if d:
        raise ValueError("enumeration exhaustive reservee a d = 0")
    if mapping == 1:
        for x in range(cl, m, BLOC * pool):
            yield np.arange(x, min(x + BLOC * pool, m), pool, dtype=np.uint64)
        return
    if mapping == 2:
        hmax = (m - 1) >> 16
        hauts = np.arange(cl, hmax + 1, pool, dtype=np.uint64)
        bas = np.arange(1 << 16, dtype=np.uint64)
        for i in range(0, len(hauts), 64):
            h = hauts[i:i + 64]
            b = ((h[:, None] << np.uint64(16)) + bas[None, :]).ravel()
            yield b[b < np.uint64(m)]
        return
    lo = -(-(cl * m) // pool)
    hi = -(-((cl + 1) * m) // pool) - 1
    for x in range(lo, hi + 1, BLOC):
        yield np.arange(x, min(x + BLOC, hi + 1), dtype=np.uint64)


def classe_np(w, m, mapping, pool, lg=None):
    """lg = log2(m) quand m est une puissance de deux : le decalage remplace la division
    entiere, qui coute plus cher que tout le reste de la boucle reunie."""
    pu = np.uint64(pool)
    if mapping == 0:
        if lg is not None:
            return (w * pu) >> np.uint64(lg)
        return (w * pu) // np.uint64(m)
    if mapping == 1:
        return w % pu
    return (w >> np.uint64(16)) % pu


def classe(w: int, m: int, mapping: int, pool: int) -> int:
    if mapping == 0:
        return (w * pool) // m
    if mapping == 1:
        return w % pool
    return (w >> 16) % pool


def verifie(w0: int, A: int, C: int, m: int, cls, mapping: int, pool: int) -> bool:
    """en entiers exacts, sur TOUTE la plage — pas seulement sur les classes criblees."""
    w = w0
    for k in cls:
        if classe(w, m, mapping, pool) != k:
            return False
        w = (A * w + C) % m
    return True


def crible(cls, m: int, A: int, C: int, mapping: int, pool: int, prof=PROF):
    """enumeration complete des w0 tels que la chaine (A, C) rende les classes `cls`."""
    out = []
    Au, Cu, mu = np.uint64(A), np.uint64(C), np.uint64(m)
    puiss = (m & (m - 1)) == 0                    # module puissance de deux : & au lieu de %
    lg = m.bit_length() - 1 if puiss else None
    msk = np.uint64(m - 1) if puiss else None
    for bloc in candidats(int(cls[0]), m, mapping, pool):
        w0, cur = bloc, bloc.copy()
        for j in range(1, min(prof, len(cls))):
            if w0.size == 0:
                break
            cur = (cur * Au + Cu)
            cur = (cur & msk) if puiss else (cur % mu)
            g = classe_np(cur, m, mapping, pool, lg) == np.uint64(int(cls[j]))
            w0, cur = w0[g], cur[g]
        for wi in w0.tolist():
            if verifie(int(wi), A, C, m, cls, mapping, pool):
                out.append(int(wi))
    return out


def _travail(arg):
    """LE CONTROLE DOIT FRANCHIR LA NUIT, PAS REUTILISER w0.

    La plage de controle commence `saut` creneaux apres la fin de la plage de crible. Sous
    le §225 chaque creneau consomme P mots, donc la chaine du bonus avance d'un pas par
    creneau — y compris pendant la nuit, SI le service tire sans publier. On avance donc
    l'etat de (n1 - 1) + saut pas. Si au contraire le service ne consomme rien la nuit, le
    bon saut est zero : les deux hypotheses sont essayees, et laquelle passe est en soi le
    renseignement que le §249 reclamait.
    """
    (nom, m, a, c), P, mapping, icanal, cls, ctrl, saut = arg
    pool = CANAUX[icanal][1]
    A, C = constantes(m, a, c, P)
    survivants = []
    for w0 in crible(cls, m, A, C, mapping, pool):
        conf = []
        for nuit, ecart in (("nuit consommee", len(cls) - 1 + saut),
                            ("nuit muette", len(cls) - 1)):
            w = w0
            for _ in range(ecart):
                w = (A * w + C) % m
            if verifie(w, A, C, m, ctrl, mapping, pool):
                conf.append(nuit)
        survivants.append((nom, P, S.MAPPINGS[mapping], CANAUX[icanal][0], w0,
                           ", ".join(conf) if conf else ""))
    return nom, P, mapping, icanal, survivants


def plages(T):
    out, deb = [], 0
    for i in range(len(T) - 1):
        if not (T[i + 1][1] - T[i][1] == PAS and T[i + 1][0] - T[i][0] == 1):
            out.append((deb, i + 1))
            deb = i + 1
    out.append((deb, len(T)))
    return out


if __name__ == "__main__":
    import multiprocessing as mp

    import lab

    T = []
    for f in sorted(glob.glob(os.path.join(RACINE, "claude", "draws", "draws-*.csv"))):
        for r in csv.DictReader(open(f)):
            T.append((int(r["id"]), int(r["unix_utc"]), int(r["bonus"]),
                      [int(r["n%d" % i]) for i in range(1, 21)]))
    T.sort()
    PL = plages(T)
    # la plage de crible est la plus longue ; la plage de CONTROLE est celle qui la suit
    # immediatement, sans quoi le « saut » a franchir n'aurait pas de sens.
    i1 = max(range(len(PL)), key=lambda i: PL[i][1] - PL[i][0])
    if i1 + 1 >= len(PL):
        i1 -= 1
    (a1, b1), (a2, b2) = PL[i1], PL[i1 + 1]
    saut = (T[a2][1] - T[b1 - 1][1]) // PAS
    petits = [k for k in S.CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]

    def canal(i, deb, fin):
        if i == 0:
            return [T[j][2] - 1 for j in range(deb, fin)]
        return [T[j][3].index(T[j][2]) for j in range(deb, fin)]

    n1, n2 = b1 - a1, b2 - a2
    total = len(petits) * len(STRIDES) * len(S.MAPPINGS) * len(CANAUX)

    HYP = (f"Aucun des {len(petits)} generateurs congruentiels de module <= 2^32 ne produit le "
           f"flux du bonus, sur aucun des {len(STRIDES)} pas de bloc, aucun des "
           f"{len(S.MAPPINGS)} mappings et aucun des {len(CANAUX)} canaux — et cette fois SANS "
           f"AUCUNE HEURISTIQUE. Le §232 rend zero sur 368 640 relevements, ce qui est le zero "
           f"le plus large du dossier, mais il l'obtient par reseau + Babai, et Babai est une "
           f"heuristique : le vecteur rendu par le plan le plus proche n'est pas toujours le "
           f"plus proche. Le §232 s'en protegeait par un temoin plante par configuration et "
           f"par 1024 cribles exhaustifs en doublon — mais sur DEUX configurations sur "
           f"dix-huit seulement. Deux sur dix-huit, c'est un controle, pas une couverture, et "
           f"le zero large reste suspendu a une heuristique. Ici on refait le meme balayage "
           f"par ENUMERATION COMPLETE pour tous les modules <= 2^32 : la premiere classe "
           f"contraint l'etat a m/pool valeurs et on les parcourt toutes. Il n'y a pas de "
           f"rejet, contrairement au §248 : le bonus est publie une fois par tirage quoi qu'il "
           f"arrive, donc la chaine est exacte — A = a^P mod m et C = c(a^P - 1)/(a - 1) sous "
           f"le §225. Le §249 decide de la fenetre : aucune plage a pas constant ne depasse "
           f"204 tirages, donc on crible sur une plage ENTIERE de {n1} valeurs consecutives et "
           f"l'on confirme sur une SECONDE plage de {n2} valeurs qui n'a jamais servi a "
           f"choisir. {n1} valeurs de bonus valent {n1*6.32:.0f} bits de contrainte sur un "
           f"etat qui en compte au plus 32 : il n'y a pas de zone grise")
    STAT = (f"nombre d'etats initiaux reproduisant la plage entiere de {n1} valeurs, sur les "
            f"{total} cribles complets ({len(petits)} generateurs x {len(STRIDES)} pas x "
            f"{len(S.MAPPINGS)} mappings x {len(CANAUX)} canaux)")
    NUL = (f"EXACTE et combinatoire : reproduire {n1} classes consecutives demande "
           f"{n1*6.32:.0f} bits (canal du numero) ou {n1*4.32:.0f} bits (canal du rang) a un "
           f"etat qui en compte au plus 32. La probabilite qu'un etat faux y parvienne est "
           f"inferieure a 2^-1250, donc l'esperance du nombre de faux positifs sur les {total} "
           f"cribles est nulle a toute precision utile. Ce n'est pas une loi, c'est un COMPTE")
    VER = (f"ETAT RELEVE si un candidat reproduit la plage entiere ET la plage de controle ; "
           f"conforme sinon, et l'absence est alors CERTAINE — non plus heuristique — sur "
           f"toute la famille de module <= 2^32")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h226 : {len(petits)} generateurs, {len(STRIDES)} pas de bloc, "
        f"{len(S.MAPPINGS)} mappings, {len(CANAUX)} canaux -> {total} cribles COMPLETS")
    say(f"   plage de crible  : {n1} tirages (ids {T[a1][0]}..{T[b1-1][0]})")
    say(f"   plage de controle: {n2} tirages (ids {T[a2][0]}..{T[b2-1][0]}), "
        f"elle ne sert jamais a choisir")
    say(f"   saut a franchir  : {saut} creneaux de {PAS} s "
        f"({(T[a2][1]-T[b1-1][1])/3600:.2f} h) — les deux hypotheses de nuit sont essayees")

    # --- autotest : on plante un flux de bonus dans CHAQUE couple et l'on exige que le
    #     crible releve l'etat exact. Sans cela, un zero ne veut rien dire. Un couple qu'on
    #     ne peut pas planter n'est PAS saute en silence : ou bien son image compte moins de
    #     `pool` classes — et c'est alors une conclusion exhaustive —, ou bien l'autotest
    #     echoue.
    say("\n   autotest : un flux plante par couple (configuration, mapping, canal)")
    manques, degeneres, plantes = [], [], 0
    for nom, m, a, c in petits:
        for mapping in range(len(S.MAPPINGS)):
            for icanal, (cnom, pool) in enumerate(CANAUX):
                img = min(pool, ((m - 1) >> 16) + 1) if mapping == 2 else min(pool, m)
                if img < pool:
                    degeneres.append((nom, S.MAPPINGS[mapping], cnom, img))
                    continue
                A, C = constantes(m, a, c, 23)
                w0 = 123456789 % m
                w, cls = w0, []
                for _ in range(40):
                    cls.append(classe(w, m, mapping, pool))
                    w = (A * w + C) % m
                plantes += 1
                if w0 not in crible(cls, m, A, C, mapping, pool):
                    manques.append((nom, S.MAPPINGS[mapping], cnom))
    if manques:
        for x in manques:
            say(f"      MANQUE : {x}")
        raise SystemExit("crible NON CALIBRE : on n'attaque rien avec ca")
    say(f"      {plantes} flux plantes, tous releves exactement")
    for nom, g, cnom, img in degeneres:
        say(f"      {nom} / {g} / {cnom} : DEGENERE, image = {img} classes — "
            f"aucun flux ne peut en sortir, c'est une conclusion et non un trou")

    taches = [(k, P, mp_i, ic, canal(ic, a1, b1), canal(ic, a2, b2), saut)
              for k in petits for P in STRIDES
              for mp_i in range(len(S.MAPPINGS)) for ic in range(len(CANAUX))]
    t0 = time.time()
    survivants, faits = [], 0
    with mp.Pool(max(1, os.cpu_count() or 1)) as pool:
        for nom, Pp, mapping, ic, surv in pool.imap_unordered(_travail, taches, chunksize=4):
            faits += 1
            survivants.extend(surv)
            for s in surv:
                say(f"   *** SURVIVANT : {s[0]}, pas {s[1]}, {s[2]}, {s[3]}, etat {s[4]}, "
                    f"controle : {s[5] or 'ECHEC sous les deux hypotheses de nuit'}")
    dt = time.time() - t0
    say(f"\n   {faits} cribles COMPLETS en {dt:.0f}s, {len(survivants)} survivants")

    confirmes = [s for s in survivants if s[5]]
    verdict = "ETAT RELEVE" if confirmes else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(confirmes)), p=float(1.0 if not confirmes else 2.0 ** -1250),
        verdict=verdict,
        power_at=(f"la detection est CERTAINE et non probable, et c'est tout l'objet : "
                  f"l'enumeration est complete sur les {len(petits)} generateurs de module "
                  f"<= 2^32, et l'autotest plante un flux de bonus dans CHACUN des "
                  f"{len(petits)*len(S.MAPPINGS)*len(CANAUX)} couples "
                  f"(configuration, mapping, canal) et exige l'etat exact avant que le "
                  f"balayage ne commence. La ou le §232 confirmait son reseau par 1024 cribles "
                  f"sur deux configurations, celui-ci en fait {total} sur les quinze : le zero "
                  f"ne repose plus sur Babai. La limite reste nette : au-dela de 2^32 "
                  f"l'enumeration est hors de portee et le §232 garde son heuristique"),
        notes=(f"LE FLUX DU BONUS PAR ENUMERATION COMPLETE (§250) — le §232 rend zero sur "
               f"368 640 relevements par reseau + Babai, heuristique, avec 1024 cribles "
               f"exhaustifs en doublon sur DEUX configurations sur dix-huit. Deux sur dix-huit "
               f"est un controle, pas une couverture. Ici : {faits} cribles COMPLETS "
               f"({len(petits)} generateurs x {len(STRIDES)} pas x {len(S.MAPPINGS)} mappings "
               f"x {len(CANAUX)} canaux) sur la plage maximale de {n1} tirages fixee par le "
               f"§249, confirmes sur une seconde plage de {n2} qui n'a jamais servi a choisir. "
               f"{len(survivants)} survivants, {len(confirmes)} confirmes. {verdict}."))
    say("   consigne.")
