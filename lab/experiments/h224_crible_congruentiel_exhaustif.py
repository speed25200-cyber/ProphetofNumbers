"""h224 — LE CRIBLE EXHAUSTIF SOUS LE REJET : ce que le §246 ne testait pas
(RAPPORT §248).

L'ANGLE MORT DU §246, ET IL EST DANS MON PROPRE OUTIL
=====================================================
Le §246 a passé les douze tirages ordonnés au réseau, sur la famille élargie. Le §246b
(h221b) a corrigé le **témoin** : il était planté avec des rejets dans le préfixe alors
que l'attaque suppose un préfixe sans rejet, ce qui faisait déclarer « NON COUVERT » des
configurations qui l'étaient.

Mais la correction s'arrêtait au témoin. **L'attaque, elle, garde l'hypothèse.** Elle lit
`ordre[:n]` comme les classes de `n` mots **consécutifs** ; dès qu'un rejet tombe dans ce
préfixe — un numéro déjà sorti, consommé sans rien publier — les classes ne sont pas
celles-là, et le réseau travaille sur une entrée fausse. Il ne rend alors pas « pas de
solution » : il rend « pas de solution **à un problème que personne ne posait** ».

> Corriger le témoin sans corriger l'attaque, c'est mesurer correctement la portée d'un
> instrument qui reste borgne.

Sur un tirage réel, la probabilité qu'aucun rejet ne tombe dans les `n` premiers mots vaut
exactement `prod_{j<n} (1 - j/80)`. Et le §246 n'utilise pas un seul `n` : le §232 le
mesure configuration par configuration, de `6` à `18`.

    n     6      8     10     12     14     18     20
    p  0,825  0,697  0,556  0,420  0,299  0,126  0,075

    part des tirages sur lesquels l'attaque du §246 travaille sur une entree JUSTE :
        de 83 % (module 2^16+1, n = 6) a 13 % (module 2^61-1, n = 18)

> **CORRECTION du texte pré-enregistré.** Le jeton scellé de cette expérience dit
> « `p = 0,0746` » — exact, c'est la valeur pour `n = 20` — puis en tire « **deux tirages
> sur trois** échappaient ». Les deux ne vont pas ensemble : « deux sur trois » est la
> valeur de `n = 14`, et `p = 0,0746` en donnerait **treize sur quatorze**. Le chiffre
> juste n'est ni l'un ni l'autre mais un **intervalle**, celui du tableau ci-dessus,
> puisque `n` dépend de la configuration. La phrase scellée est donc **conservatrice** —
> elle sous-estime le trou sur les grands modules et le surestime sur les petits — et je
> la laisse telle quelle plutôt que de la réécrire après coup.

CE QUE FAIT CELUI-CI
====================
`claude/research/lcg_family_solver.py` n'a pas cette hypothèse. Pour `m <= 2^32` il
**énumère** les mots compatibles avec le premier numéro et déroule le flux en simulant le
rejet **dès le filtre** :

    PREM[n] == pos   le numéro attendu       -> on publie, pos avance
    PREM[n] <  pos   un numéro déjà sorti    -> REJET, le mot est consommé
    PREM[n] >  pos   contradiction           -> le candidat meurt

Trois cas, aucun arbitrage, aucune heuristique : **si une solution existe, elle est
trouvée.** Un « aucun état » rendu par cet outil est une absence *certaine*, pas
l'échec d'une recherche.

LA FORCE, ET SA LIMITE
======================
La force : `15` générateurs × `3` mappings × `12` tirages = `540` cribles **complets**,
là où le §246 en faisait autant de partiels.

La limite, et elle est nette : `m <= 2^32`. Au-delà, l'énumération est hors de portée et
seul le réseau reste — avec son hypothèse. C'est dit ici plutôt que laissé à deviner.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOLVEUR = os.path.join(RACINE, "claude", "research", "lcg_family_solver.py")
POOL, DRAWN = 80, 20
EXP_ID = "h224.crible_congruentiel_exhaustif"
FJETON = "/tmp/h224_jeton.json"


def say(*a):
    print(*a, flush=True)


def sans_rejet(n: int) -> float:
    """probabilite qu'aucun rejet ne tombe dans les n premiers mots d'un tirage."""
    p = 1.0
    for j in range(n):
        p *= (POOL - j) / POOL
    return p


if __name__ == "__main__":
    import csv
    import lab

    sys.path.insert(0, os.path.join(RACINE, "claude", "research"))
    import lcg_family_solver as S                                       # noqa: E402

    lignes = list(csv.DictReader(open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draws_ordered.csv"))))
    ORD = [[int(r["o%d" % i]) for i in range(1, 21)] for r in lignes]
    IDS = [r["id"] for r in lignes]
    n = len(ORD)
    petits = [k for k in S.CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]
    essais = len(petits) * len(S.MAPPINGS) * n
    p20, p5 = sans_rejet(DRAWN), sans_rejet(S.PROF)

    HYP = (f"Aucun des {len(petits)} generateurs congruentiels de module <= 2^32 ne produit "
           f"l'un des {n} tirages ordonnes, sous aucun des {len(S.MAPPINGS)} mappings, depuis "
           f"AUCUN etat — et cette fois l'enonce est exhaustif au sens propre. L'ANGLE MORT DU "
           f"§246 : le §246b a corrige le TEMOIN — il etait plante avec des rejets dans le "
           f"prefixe alors que l'attaque suppose un prefixe sans rejet — mais la correction "
           f"s'arretait au temoin. L'ATTAQUE, ELLE, GARDE L'HYPOTHESE : elle lit ordre[:n] "
           f"comme les classes de n mots CONSECUTIFS, et des qu'un rejet tombe dans ce prefixe "
           f"les classes ne sont pas celles-la. Le reseau ne rend alors pas « pas de solution » "
           f"mais « pas de solution a un probleme que personne ne posait ». La probabilite "
           f"qu'aucun rejet ne tombe dans les vingt premiers mots vaut prod (1 - j/80) = "
           f"{p20:.4f} : DEUX TIRAGES SUR TROIS echappaient donc en silence a l'attaque du "
           f"§246. Corriger le temoin sans corriger l'attaque, c'est mesurer correctement la "
           f"portee d'un instrument qui reste borgne. Le crible exhaustif n'a pas cette "
           f"hypothese : il enumere les mots compatibles avec le premier numero et deroule le "
           f"flux en simulant le rejet DES LE FILTRE, par la regle a trois cas PREM[n] == pos "
           f"(on publie), PREM[n] < pos (rejet, mot consomme), PREM[n] > pos (le candidat "
           f"meurt). Aucun arbitrage, aucune heuristique : si une solution existe elle est "
           f"trouvee, et une absence est CERTAINE et non l'echec d'une recherche")
    STAT = (f"nombre d'etats initiaux reproduisant les vingt numeros ordonnes d'un tirage, "
            f"rejets compris, sur les {essais} cribles complets "
            f"({len(petits)} generateurs x {len(S.MAPPINGS)} mappings x {n} tirages)")
    NUL = (f"EXACTE et combinatoire : reproduire vingt numeros DANS L'ORDRE demande "
           f"log2(80!/60!) = 126,0 bits de contrainte a un etat qui en compte au plus 32. La "
           f"probabilite qu'un etat faux y parvienne est inferieure a 2^-94, donc l'esperance "
           f"du nombre de faux positifs sur les {essais} cribles reste sous 2^-70. Un seul "
           f"survivant serait donc reel")
    VER = ("ETAT RELEVE si au moins un etat reproduit un tirage entier ; conforme sinon, et "
           "l'absence est alors CERTAINE sur toute la famille de module <= 2^32, sans "
           "hypothese de prefixe sans rejet")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h224 : {len(petits)} generateurs de module <= 2^32, {len(S.MAPPINGS)} mappings, "
        f"{n} tirages ordonnes -> {essais} cribles EXHAUSTIFS")
    say(f"   part des tirages a prefixe sans rejet : {p20:.4f} sur vingt mots, "
        f"{p5:.4f} sur cinq")
    say("   le §246 n'utilise pas un seul n — le §232 le mesure de 6 a 18 selon la "
        "configuration :")
    say("      " + "  ".join(f"n={k}:{sans_rejet(k):.3f}" for k in (6, 8, 10, 12, 14, 18, 20)))
    say(f"   -> l'attaque du §246 travaille sur une entree JUSTE dans "
        f"{100*sans_rejet(18):.0f} a {100*sans_rejet(6):.0f} % des cas selon le module ; "
        f"le reste lui echappe en silence")

    # --- l'autotest de l'outil fait foi : on ne crible pas avec un outil non calibre
    say("\n   autotest du solveur (temoins plantes AVEC rejets dans la fenetre du filtre)")
    r = subprocess.run([sys.executable, SOLVEUR, "selftest"],
                       capture_output=True, text=True)
    for ligne in r.stdout.rstrip().splitlines():
        say("   " + ligne)
    if r.returncode != 0:
        raise SystemExit("solveur NON CALIBRE : on n'attaque rien avec ca")

    t0 = time.time()
    touches, faits, nconf = S.crible_independant(ORD, verbeux=False)
    dt = time.time() - t0
    # le compte annonce et le compte fait doivent se rejoindre A LA LIGNE PRES
    impossibles = [(nom, S.MAPPINGS[mp]) for nom, m, a, c in petits
                   for mp in range(len(S.MAPPINGS)) if S.image(m, mp) < DRAWN]
    say(f"\n   {faits} cribles complets en {dt:.1f}s, {len(touches)} etats trouves")
    if impossibles:
        say(f"   {essais - faits} des {essais} cribles annonces sont IMPOSSIBLES PAR "
            f"CONSTRUCTION et non « non faits » : "
            + ", ".join(f"{n}/{g}" for n, g in impossibles))
        say(f"   (leur image compte moins de {DRAWN} numeros, donc aucun tirage de "
            f"{DRAWN} numeros distincts ne peut en sortir — c'est une conclusion, pas un trou)")
    for nom, mapping, i, w1 in touches:
        say(f"   *** {nom}, {mapping}, tirage {IDS[i]}, etat {w1}")

    verdict = "ETAT RELEVE" if touches else "conforme"
    say(f"\n   {verdict}")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(touches)), p=float(1.0 if not touches else 2.0 ** -70),
        verdict=verdict,
        power_at=(f"la detection est CERTAINE et non probable : l'enumeration est complete "
                  f"sur les {len(petits)} generateurs de module <= 2^32, et l'autotest "
                  f"replante une graine dans CHACUN des {len(petits)} x {len(S.MAPPINGS)} "
                  f"couples qu'il pretend couvrir — pas dans un echantillon — dont neuf ont "
                  f"un rejet DANS LA FENETRE MEME DU FILTRE, la voie que le §246 n'exercait "
                  f"pas. Un seul couple est declare IMPOSSIBLE PAR CONSTRUCTION et il est "
                  f"affiche comme tel : le ZX81 sous shr16, dont l'image ne compte que deux "
                  f"numeros et qui ne peut donc produire aucun tirage de vingt numeros "
                  f"distincts. C'est l'autotest echantillonne qui avait laisse passer une "
                  f"enumeration shr16 incomplete — elle s'arretait au haut borne >> 16 au "
                  f"lieu de (borne - 1) >> 16, ce qui ne se voit QUE sur un module non "
                  f"puissance de deux, et les cinq configurations tirees etaient toutes des "
                  f"puissances de deux. La limite est nette et se dit : au-dela de 2^32 "
                  f"l'enumeration est hors de portee et seul le reseau reste, avec son "
                  f"hypothese de prefixe sans rejet"),
        notes=(f"CRIBLE EXHAUSTIF SOUS LE REJET (§248) — le §246b avait corrige le TEMOIN du "
               f"§246 mais pas l'ATTAQUE, qui lit toujours ordre[:n] comme n mots consecutifs "
               f"et travaille donc sur une entree fausse des qu'un rejet tombe dans le "
               f"prefixe. CORRECTION DU TEXTE PRE-ENREGISTRE : le jeton dit « p = "
               f"{p20:.4f} » (exact, c'est n = 20) puis en tire « deux tirages sur trois », "
               f"ce qui est la valeur de n = 14 ; les deux ne vont pas ensemble et le chiffre "
               f"juste est un INTERVALLE, car le §232 mesure n de 6 a 18 selon la "
               f"configuration — l'attaque travaille sur une entree juste dans "
               f"{100*sans_rejet(18):.0f} a {100*sans_rejet(6):.0f} % des cas. La phrase "
               f"scellee est conservatrice et je la laisse telle quelle. Ce crible-ci simule "
               f"le rejet des le filtre par une regle a trois cas et n'a aucune heuristique. "
               f"{faits} cribles complets, {len(touches)} etats. {verdict}."))
    say("   consigne.")
