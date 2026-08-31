"""Reparation du registre : le champ `m_extra` manquait sur quatre entrees.

CE QUI S'EST PASSE, et il faut l'ecrire.
========================================
Le registre compte sa multiplicite ainsi (`lab.holm`) :

    m = nombre de lignes + somme des `m_extra`

`m_extra` est le nombre de tests SUPPLEMENTAIRES qu'une entree represente : un
balayage sur huit diviseurs est une entree mais huit tests, donc m_extra = 7.

Les entrees h56, h57, h59 et h61 declaraient leur m_extra dans le TEXTE des
notes — « m_extra = 7. » — mais pas dans le CHAMP, que `lab.record` n'expose
pas. Le registre sous-comptait donc sa propre multiplicite, ce qui rend le
seuil de Holm TROP PERMISSIF. Aucune conclusion n'en depend (toutes les
entrees concernees sont conformes avec p tres au-dessus du seuil), mais un
seuil trop permissif est exactement le defaut que le protocole du labo
existe pour empecher.

De plus, h61 a ete consigne DEUX FOIS : la serie complete a ete lancee deux
fois, et le registre etant en ajout seul, les deux lignes y sont. C'est le
meme incident qu'au §60, et il se repare de la meme facon.

CE QUE FAIT CE FICHIER
======================
1. Il rejoue la derniere ligne de chacune des quatre entrees en y AJOUTANT le
   champ `m_extra`, avec la valeur que les notes declaraient — h57 n'en
   declarait aucune, donc 0.
2. Il appelle `lab.dedupe()`, qui ne garde que la derniere ligne de chaque
   identifiant : la ligne corrigee remplace l'ancienne, et le doublon h61
   disparait.

Rien n'est efface a la main. Le registre reste en ajout seul, et l'incident
reste lisible dans son historique.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lab                                                    # noqa: E402

DECLARED = {"h56.classes_residuelles": 7,
            "h57.bonus_ordonne": 0,
            "h59.surdispersion_session": 0,
            "h61.familles_etendues": 14}


def main():
    rows = lab.ledger()
    before = lab.holm()[0]["m_total"]
    last = {}
    for r in rows:
        last[r["id"]] = r
    n = 0
    with open(lab.LEDGER, "a") as fh:
        for eid, extra in DECLARED.items():
            if eid not in last:
                print(f"   {eid} : absent du registre, ignore")
                continue
            row = dict(last[eid])
            if row.get("m_extra") == extra:
                continue
            row["m_extra"] = extra
            row["notes"] = (row.get("notes", "") +
                            " [REPARATION : champ m_extra ajoute, valeur "
                            f"declaree dans les notes d'origine ; "
                            f"cf. lab/reparation_m_extra.py]")
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            print(f"   {eid} : m_extra = {extra} porte au champ")
    removed = lab.dedupe()
    after = lab.holm()
    print(f"\n   lignes rejouees   {n}")
    print(f"   doublons retires  {removed}")
    print(f"   m du registre     {before:,} -> {after[0]['m_total']:,}")
    print(f"   significatifs     {sum(1 for r in after if r['significant'])}")
    print(f"   plus petit p      {min(r['p'] for r in after if r.get('p') is not None):.2e}")


if __name__ == "__main__":
    main()
