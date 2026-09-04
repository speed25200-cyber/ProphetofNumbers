"""h225 — LE PLAFOND DE LA NUIT : pourquoi `D >= 450` est hors d'atteinte
(RAPPORT §249).

CE QUE CE TEST VISE, ET CE N'EST PAS L'ARCHIVE
==============================================
Ce n'est pas une hypothèse sur le générateur. C'est une contrainte sur le **plan de
capture** — et elle se lit dans les horodatages que le dossier possède déjà.

La branche `codex/state-reconstruction-continuation` fixe le seuil de son solveur :

    keno_break, mapping mulhi   : D >= 450   (400 d'apprentissage + 50 de validation)
    keno_break, mapping modulo  : D ~ 1400   + holdout

et pose, à juste titre, une règle de sécurité :

> « Les entrées solveur dérivées sont séparées dès qu'un ID manque **ou** que l'intervalle
>   entre `drawDate` sort de `300 ± 5` secondes. Deux IDs consécutifs séparés par la nuit ne
>   sont donc jamais présentés à tort comme un flux fixed-stride continu. L'ancien
>   contournement `--allow-gaps` a été supprimé : concaténer deux segments ferait croire à
>   tort au solveur qu'ils sont contigus. »

La règle est bonne. Mais elle a une conséquence que personne n'a chiffrée : **elle plafonne
`D`.** Et le plafond, lui, est déjà mesurable — les `70 560` horodatages de l'archive le
donnent exactement, sans capturer quoi que ce soit.

LA QUESTION, ET ELLE A UNE RÉPONSE EXACTE
=========================================
> Combien de tirages consécutifs peut contenir, au maximum, une plage sans coupure de nuit ?

On compte les plages maximales où l'identifiant s'incrémente de `1` **et** l'horodatage de
`300` secondes exactement — la définition même que le solveur exige.

Si la réponse est `>= 450`, le plan tient. Si elle est en dessous, `D >= 450` n'est pas
« difficile » : il est **inaccessible sur un segment**, et le seuil doit changer ou la
méthode doit changer.

CE QUE ÇA NE DIT PAS
====================
Que la nuit plafonne le segment **observable** ne prouve pas qu'elle interrompe le
**générateur**. Si le service tire sans publier, ou si un démon garde son état, la nuit est
un décalage *connu* — `85` créneaux — et donc franchissable. Ce test ne tranche pas cela ;
il chiffre le plafond **sous la règle que le plan s'est lui-même donnée**, et dit ce qu'il
faudrait établir pour le lever.
"""

import csv
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAS = 300
EXP_ID = "h225.plafond_de_la_nuit"
FJETON = "/tmp/h225_jeton.json"
SEUILS = (204, 300, 400, 450, 1400)


def say(*a):
    print(*a, flush=True)


def plages(T):
    """longueurs des plages maximales a id consecutif ET pas de 300 s exactement."""
    out, cur = [], 1
    for i in range(len(T) - 1):
        if T[i + 1][1] - T[i][1] == PAS and T[i + 1][0] - T[i][0] == 1:
            cur += 1
        else:
            out.append(cur)
            cur = 1
    out.append(cur)
    return out


if __name__ == "__main__":
    import lab

    T = []
    for f in sorted(glob.glob(os.path.join(RACINE, "claude", "draws", "draws-*.csv"))):
        for r in csv.DictReader(open(f)):
            T.append((int(r["id"]), int(r["unix_utc"])))
    T.sort()
    n = len(T)
    P = sorted(plages(T), reverse=True)
    jours = (T[-1][1] - T[0][1]) / 86400.0

    HYP = (f"Le plan de capture de la branche codex fixe D >= 450 tirages CONSECUTIFS a pas "
           f"fixe (400 d'apprentissage + 50 de validation) pour le mapping mulhi, et environ "
           f"1400 pour les mappings modulo. Il pose en meme temps une regle de securite juste "
           f"— les entrees solveur sont separees des qu'un ID manque ou que l'intervalle sort "
           f"de 300 +/- 5 s, et le contournement --allow-gaps a ete supprime parce que "
           f"concatener deux segments ferait croire a tort au solveur qu'ils sont contigus. "
           f"Cette regle a une consequence que personne n'a chiffree : ELLE PLAFONNE D. Et le "
           f"plafond est deja mesurable sans capturer quoi que ce soit, dans les {n} "
           f"horodatages de l'archive. L'hypothese testee est celle du plan : il existe des "
           f"plages de 450 tirages consecutifs a pas de 300 s exactement, sans coupure de "
           f"nuit. Si le maximum mesure est en dessous, D >= 450 n'est pas difficile mais "
           f"INACCESSIBLE SUR UN SEGMENT, et c'est le seuil ou la methode qui doit changer. "
           f"Ce test ne prouve pas que la nuit interrompe le GENERATEUR : si le service tire "
           f"sans publier ou si un demon garde son etat, la nuit est un decalage connu et donc "
           f"franchissable. Il chiffre le plafond SOUS LA REGLE QUE LE PLAN S'EST DONNEE")
    STAT = (f"longueur de la plus longue plage maximale a identifiant consecutif ET intervalle "
            f"de {PAS} s exactement, sur les {n} tirages de l'archive")
    NUL = (f"EXACTE et deterministe : ce n'est pas une loi mais un COMPTE sur les {n} "
           f"horodatages publies. Sous l'hypothese du plan — un flux continu a pas de {PAS} s "
           f"— la plage maximale serait de l'ordre de {n} et depasserait 450 des le premier "
           f"jour. Il n'y a pas d'echantillonnage, donc pas de p a estimer")
    VER = (f"PLAN TENABLE si la plus longue plage atteint 450 tirages ; PLAFOND sinon, et le "
           f"plafond mesure devient la borne dure de tout segment fixed-stride")

    if os.path.exists(FJETON):
        TOK = json.load(open(FJETON, encoding="utf-8"))
        say(f"   jeton repris : scelle {TOK['seal']}")
    else:
        TOK = lab.preregister(EXP_ID, HYP, STAT, NUL, VER, track="B")
        json.dump(TOK, open(FJETON, "w", encoding="utf-8"), ensure_ascii=False)
        say(f"   jeton scelle {TOK['seal']}")

    say(f"h225 : {n} tirages, {jours:.0f} jours, ids {T[0][0]} -> {T[-1][0]}")

    ecarts = {}
    for i in range(n - 1):
        d = T[i + 1][1] - T[i][1]
        ecarts[d] = ecarts.get(d, 0) + 1
    say("\n   les intervalles, par frequence")
    for d, k in sorted(ecarts.items(), key=lambda x: -x[1])[:4]:
        say(f"      {d:7d} s ({d/3600:6.2f} h) : {k:6d}"
            + ("   <- la nuit" if d > 3600 else ""))
    # la nuit TYPIQUE, pas la plus longue : c'est la modale qui decrit la coupure
    grandes = {d: k for d, k in ecarts.items() if d > 3600}
    nuit = max(grandes, key=lambda d: grandes[d]) if grandes else 0
    if nuit:
        say(f"   la coupure de nuit type vaut {nuit} s = {nuit // PAS} creneaux de {PAS} s "
            f"exactement (reste {nuit % PAS}), vue {grandes[nuit]} fois sur "
            f"{sum(grandes.values())} coupures")
        exacts = sum(k for d, k in grandes.items() if d % PAS == 0)
        say(f"   coupures multiples exacts de {PAS} s : {exacts}/{sum(grandes.values())} "
            f"-> la nuit est un nombre ENTIER de creneaux, donc un decalage connu")

    say(f"\n   {len(P)} plages continues ; la plus longue : {P[0]} tirages "
        f"({P[0]*PAS/3600:.1f} h)")
    say(f"   mediane {statistics.median(P):.0f}, moyenne {sum(P)/len(P):.1f}, "
        f"les dix plus longues : {P[:10]}")
    say("")
    for s in SEUILS:
        k = sum(1 for r in P if r >= s)
        say(f"      plages de >= {s:5d} tirages : {k:4d}"
            + ("   <- le seuil mulhi du plan" if s == 450 else
               "   <- le seuil modulo du plan" if s == 1400 else ""))

    tenable = P[0] >= 450
    verdict = "PLAN TENABLE" if tenable else "PLAFOND"
    say(f"\n   {verdict}")
    if not tenable:
        say(f"   -> 450 demande {450/P[0]:.2f} fois le plus long segment possible ; "
            f"1400 en demande {1400/P[0]:.2f} fois.")
        say(f"      Un etat congruentiel de 32 bits, lui, est sur-determine par UN SEUL "
            f"tirage ordonne (126 bits).")

    TOK["m_extra"] = 0
    lab.record(
        TOK, float(P[0]), p=1.0, verdict=verdict,
        power_at=(f"le compte est EXACT et non statistique : il porte sur les {n} "
                  f"horodatages publies, tous, et la definition de plage est exactement celle "
                  f"que le solveur exige (id consecutif et intervalle de {PAS} s). Un seul "
                  f"segment de 450 tirages suffirait a rendre le verdict inverse ; il y en a "
                  f"{sum(1 for r in P if r >= 450)} sur {len(P)} plages et {jours:.0f} jours"),
        notes=(f"LE PLAFOND DE LA NUIT (§249) — le plan de la branche codex demande D >= 450 "
               f"tirages consecutifs a pas fixe (1400 pour les mappings modulo) et interdit a "
               f"raison de concatener deux segments separes par la nuit. Mesure sur "
               f"l'archive : la plus longue plage a id consecutif et pas de {PAS} s exactement "
               f"vaut {P[0]} tirages ({P[0]*PAS/3600:.1f} h), sur {len(P)} plages en "
               f"{jours:.0f} jours ; "
               f"{sum(1 for r in P if r >= 300)} plages atteignent 300, "
               f"{sum(1 for r in P if r >= 450)} atteignent 450. La coupure de nuit vaut "
               f"{nuit} s = {nuit // PAS} creneaux exactement, donc franchissable SI le pas "
               f"est fixe et le processus unique — deux hypotheses a etablir, non etablies. "
               f"{verdict}."))
    say("   consigne.")
