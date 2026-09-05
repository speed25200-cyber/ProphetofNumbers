"""h232 — LE TREIZIÈME TIRAGE ORDONNÉ : celui que le dépôt portait déjà, et le seul
qui soit le PREMIER DE SA JOURNÉE (RAPPORT §258).

OÙ IL ÉTAIT
===========
Pas dans une vidéo, pas dans l'API, pas dans un fichier de capture — ceux-là sont
exclus du dépôt par le `.gitignore` de la branche `codex` (`capture*.jsonl`,
`ordered*.txt`, `captures/`). Il était dans un fichier de PROSE :
`claude/REPRISE_ETAT.md` de la branche `codex/state-reconstruction-continuation`
(PR #3), commit `6f26f34` du 4 septembre 2026, blob `b73b0fd9`. Le texte rapporte
une capture ACTIVE du flux d'animation `SignalR` :

    tirage 1382010, wagerEndDate = 2026-09-04T04:05:00Z (06:05 Europe/Zurich)
    DrawScene  a +30,107 s : 22 24 30 41 6 76 73 9 45 36 37 54 39 21 72 15 10 38 64 79
    ExtraScene a +146,1 s  : bonus 37 (boost 2 deja present dans le DrawScene)
    verdict du collecteur  : VERIFIED_ORDER, order_scope = ANIMATION_SEQUENCE_ONLY

Le fouillage qui l'a trouvé a couvert TOUT le dépôt distant : les huit branches
(arbres complets), tous les objets git (`cat-file --batch-all-objects`, y compris les
blobs inatteignables), les trois releases (les vidéos, déjà exploitées aux §129 et §130),
les trois PR, les issues (aucune), les Actions (aucune). C'est la SEULE donnée
ordonnée du dépôt que `draws_ordered.csv` ne portait pas encore.

CE QU'IL A DE PLUS QUE LES DOUZE AUTRES
=======================================
La journée compte 204 créneaux et la numérotation les franchit sans exception (§249) :
depuis le dernier identifiant de l'archive, `1380173` du 25 août à 21:00Z,

    1382010 - 1380173 = 1837 = 9 x 204 + 1

Il est donc le PREMIER tirage du 4 septembre — créneau 0 —, ce que confirme son heure
(04:05Z est l'heure du premier tirage sur 191 des 345 journées d'été de l'archive).
Les douze autres relevés sont aux créneaux 33 à 85. Si un générateur est réamorcé
chaque matin, ces vingt numéros ordonnés sont ses PREMIERS MOTS.

CE QUE CELA PERMET, ET NE PERMET PAS — DIT AVANT DE CALCULER
============================================================
  * Les balayages de graine (§133, §161, §200 à §204, §212, §214) travaillaient déjà
    sur les 346 PREMIERS tirages TRIÉS de l'archive, et un ensemble trié est un filtre
    à 61,6 bits : par graine, une coïncidence fausse a une probabilité de 1/C(80,20).
    L'ordre n'y ajoute donc AUCUN pouvoir de détection ; ces zéros-là restent ce qu'ils
    sont, et on ne les refait pas ici.
  * Les cribles des plans bas (§154, §159) ne sont décisifs qu'avec plusieurs tirages
    d'une même journée : un tirage seul livre 22 bits bas exacts contre des plans de
    L ≤ 17 bits chacun — marge insuffisante, cellule non décisive. On ne les refait pas
    non plus, et on le dit plutôt que de faire tourner un instrument aveugle.
  * Ce qui GAGNE un tirage ordonné de plus, c'est l'instrument qui lit CHAQUE tirage
    seul et sans hypothèse : le crible exhaustif du §248, qui énumère tous les états
    d'un générateur congruentiel de module ≤ 2^32, rejet simulé dès le filtre. Il est
    relancé sur les TREIZE tirages — les douze déjà criblés servent de contrôle de
    régression, le treizième est la question.

La nulle est un compte, pas une loi : reproduire vingt numéros DANS L'ORDRE demande
126 bits de contrainte à un état qui en compte au plus 32 ; l'espérance des faux
positifs sur la grille entière reste sous 2^-70. Un survivant serait réel.
"""

import csv
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOLVEUR = os.path.join(RACINE, "claude", "research", "lcg_family_solver.py")
CSV = os.path.join(RACINE, "lab", "draws_ordered.csv")
ARCHIVE_FIN = os.path.join(RACINE, "claude", "draws", "draws-08.csv")
POOL, DRAWN = 80, 20
CRENEAUX = 204
EXP_ID = "h232.treizieme_tirage_premier_du_jour"
FJETON = "/tmp/h232_jeton.json"

NOUVEAU = 1382010
SOURCE = "signalr-codex-REPRISE_ETAT"
BLOB = "b73b0fd93d4b0ed6259a8e6be78db828f7f5f9bb"          # claude/REPRISE_ETAT.md @ 6f26f34
ATTENDU = [22, 24, 30, 41, 6, 76, 73, 9, 45, 36, 37, 54, 39, 21, 72, 15, 10, 38, 64, 79]


def say(*a):
    print(*a, flush=True)


def provenance():
    """le CSV doit porter EXACTEMENT ce que le blob git porte ; sinon on ne crible rien."""
    lignes = list(csv.DictReader(open(CSV, encoding="utf-8")))
    ligne = [r for r in lignes if int(r["id"]) == NOUVEAU]
    if len(ligne) != 1:
        raise SystemExit(f"le tirage {NOUVEAU} doit figurer une fois dans {CSV}")
    ordre = [int(ligne[0]["o%d" % i]) for i in range(1, DRAWN + 1)]
    if ordre != ATTENDU or ligne[0]["source"] != SOURCE or ligne[0]["bonus"] != "37":
        raise SystemExit("la ligne du CSV ne correspond pas a la transcription attendue")
    try:
        texte = subprocess.run(["git", "-C", RACINE, "cat-file", "-p", BLOB],
                               capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        say(f"   (blob {BLOB[:8]} absent du clone local : la branche codex n'est pas "
            f"rapatriee ; la transcription est verifiee contre la constante du script)")
        return lignes, ordre, False
    suite = " ".join(str(v) for v in ATTENDU)
    if suite not in texte or f"**{NOUVEAU}**" not in texte:
        raise SystemExit("le blob git ne porte pas la suite attendue : transcription fausse")
    say(f"   blob {BLOB[:8]} relu : la suite et l'identifiant y sont, mot pour mot")
    return lignes, ordre, True


def creneau(ident: int, dernier_id: int) -> int:
    """position dans la journee de 204 creneaux, comptee depuis le lendemain de l'archive."""
    return (ident - (dernier_id + 1)) % CRENEAUX


if __name__ == "__main__":
    import lab

    sys.path.insert(0, os.path.join(RACINE, "claude", "research"))
    import lcg_family_solver as S                                       # noqa: E402

    say(f"h232 : le treizieme tirage ordonne, {NOUVEAU}, et d'ou il vient")
    lignes, ordre, blob_vu = provenance()
    ORD = [[int(r["o%d" % i]) for i in range(1, DRAWN + 1)] for r in lignes]
    IDS = [int(r["id"]) for r in lignes]
    n = len(ORD)

    with open(ARCHIVE_FIN, encoding="utf-8") as fh:
        dernier = int(list(csv.DictReader(fh))[-1]["id"])
    cren = {i: creneau(i, dernier) for i in IDS}
    say(f"   archive close a {dernier} ; creneaux des {n} tirages ordonnes :")
    say("      " + "  ".join(f"{i}:{cren[i]}" for i in IDS))
    premiers = [i for i in IDS if cren[i] == 0]
    say(f"   premiers de leur journee : {premiers}  "
        f"({NOUVEAU} - {dernier} = {NOUVEAU - dernier} = "
        f"{(NOUVEAU - dernier - 1) // CRENEAUX} x {CRENEAUX} + 1)")
    if premiers != [NOUVEAU]:
        raise SystemExit("l'enonce du script est faux : verifier les creneaux avant de crible")

    petits = [k for k in S.CONFS if k[1] <= (1 << 32) and k[2] < (1 << 32)]
    essais = len(petits) * len(S.MAPPINGS) * n

    HYP = (f"Le depot portait un treizieme tirage ORDONNE que draws_ordered.csv n'avait pas : "
           f"{NOUVEAU}, capture active du flux SignalR rapportee dans claude/REPRISE_ETAT.md "
           f"de la branche codex (PR #3, commit 6f26f34, blob {BLOB[:8]}), DrawScene a "
           f"+30,107 s de wagerEndDate = 2026-09-04T04:05:00Z, bonus 37 en ExtraScene a "
           f"+146,1 s, boost 2. Il est le PREMIER tirage de sa journee (creneau 0 : "
           f"{NOUVEAU} - {dernier} = 9 x 204 + 1, et 04:05Z est l'heure du premier tirage "
           f"sur 191 journees d'ete de l'archive) — les douze autres sont aux creneaux 33 a "
           f"85. Hypothese testee : aucun des {len(petits)} generateurs congruentiels de "
           f"module <= 2^32, sous aucun des {len(S.MAPPINGS)} mappings, ne produit ce tirage "
           f"depuis AUCUN etat, rejet simule des le filtre par la regle a trois cas du §248 "
           f"(PREM == pos publie, PREM < pos rejette, PREM > pos tue). Les douze tirages deja "
           f"cribles au §248 sont recribles comme controle de regression et doivent rendre "
           f"zero comme alors. DIT AVANT DE CALCULER : les balayages de graine du dossier "
           f"travaillaient deja sur les premiers tirages TRIES, filtre a 61,6 bits par graine, "
           f"l'ordre n'y ajoute aucun pouvoir et ils ne sont pas refaits ; les cribles des "
           f"plans bas ne sont pas decisifs sur un tirage seul (22 bits contre L <= 17 par "
           f"plan) et ne sont pas refaits non plus")
    STAT = (f"nombre d'etats initiaux reproduisant les vingt numeros ordonnes d'un tirage, "
            f"rejets compris, sur les {essais} cribles complets ({len(petits)} generateurs x "
            f"{len(S.MAPPINGS)} mappings x {n} tirages), le treizieme tirage compte a part")
    NUL = ("EXACTE et combinatoire : 126 bits de contrainte contre un etat d'au plus 32 ; "
           "probabilite d'un faux etat < 2^-94 par crible, esperance des faux positifs sur la "
           "grille < 2^-70. Un seul survivant serait reel")
    VER = ("ETAT RELEVE si au moins un etat reproduit un tirage entier ; conforme sinon, et "
           "l'absence est alors CERTAINE pour le treizieme tirage sur toute la famille de "
           "module <= 2^32, sans hypothese de prefixe sans rejet")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"\n   autotest du solveur (temoins plantes AVEC rejets dans la fenetre du filtre)")
    r = subprocess.run([sys.executable, SOLVEUR, "selftest"], capture_output=True, text=True)
    for ligne in r.stdout.rstrip().splitlines()[-6:]:
        say("   " + ligne)
    if r.returncode != 0:
        raise SystemExit("solveur NON CALIBRE : on n'attaque rien avec ca")

    say(f"\n   {len(petits)} generateurs x {len(S.MAPPINGS)} mappings x {n} tirages "
        f"-> {essais} cribles exhaustifs")
    t0 = time.time()
    touches, faits, nconf = S.crible_independant(ORD, verbeux=False)
    dt = time.time() - t0
    impossibles = [(nom, S.MAPPINGS[mp]) for nom, m, a, c in petits
                   for mp in range(len(S.MAPPINGS)) if S.image(m, mp) < DRAWN]
    say(f"   {faits} cribles complets en {dt:.0f} s, {len(touches)} etat(s) trouve(s)")
    if impossibles:
        say(f"   {essais - faits} des {essais} cribles annonces sont IMPOSSIBLES PAR "
            f"CONSTRUCTION (image < {DRAWN} numeros) : "
            + ", ".join(f"{a}/{b}" for a, b in impossibles))
    for nom, mapping, i, w1 in touches:
        say(f"   *** {nom}, {mapping}, tirage {IDS[i]}, etat {w1}")
    nouveaux = [t for t in touches if IDS[t[2]] == NOUVEAU]
    anciens = [t for t in touches if IDS[t[2]] != NOUVEAU]
    say(f"   treizieme tirage : {len(nouveaux)} etat(s) ; les douze du §248 : {len(anciens)} "
        f"(attendu 0, controle de regression)")

    verdict = "ETAT RELEVE" if touches else "conforme"
    say(f"\n   {verdict}")
    TOK["m_extra"] = 0
    lab.record(
        TOK, float(len(touches)), p=float(1.0 if not touches else 2.0 ** -70),
        verdict=verdict,
        power_at=(f"detection CERTAINE et non probable : l'enumeration est complete sur les "
                  f"{len(petits)} generateurs de module <= 2^32, et l'autotest du solveur "
                  f"replante une graine dans chacun des {len(petits)} x {len(S.MAPPINGS)} "
                  f"couples, neuf d'entre elles avec un rejet DANS la fenetre du filtre. "
                  f"Les douze tirages du §248 recribles rendent {len(anciens)} etat(s), comme "
                  f"alors. La limite est la meme qu'au §248 : au-dela de 2^32 l'enumeration "
                  f"est hors de portee"),
        notes=(f"LE TREIZIEME TIRAGE ORDONNE (§258) — {NOUVEAU}, premier de sa journee "
               f"(creneau 0), transcrit de claude/REPRISE_ETAT.md (branche codex, PR #3, "
               f"commit 6f26f34, blob {BLOB[:8]}{', relu ici' if blob_vu else ''}) ; "
               f"capture SignalR active du 2026-09-04, DrawScene +30,107 s, bonus 37 en "
               f"ExtraScene +146,1 s, boost 2. {faits} cribles complets en {dt:.0f} s, "
               f"{len(nouveaux)} etat(s) sur le treizieme, {len(anciens)} sur les douze. "
               f"{verdict}."))
    say("   consigne.")
