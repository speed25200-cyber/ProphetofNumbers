# Prototype exact sur les tirages triés et MT19937

## Portée exacte

`sorted_mt_family_solver.py` teste une contrainte réellement disponible quand
l'ordre des boules est perdu : pour un Fisher-Yates avant, la première boule
générée appartient nécessairement à l'ensemble trié publié.

Le prototype utilise :

- la transition et la tempérisation de référence de MT19937 ;
- Fisher-Yates 20 parmi 80 ;
- le mapping exact `((uint64_t)u * borne) >> 32` ;
- uniquement les ensembles triés en entrée du solveur ;
- une intersection exacte de supports disjonctifs, sans relaxation par préfixe.

Pour que l'expérience soit calculable, l'état inconnu est limité à une tranche
affine dense de `B` dimensions dans l'image du twist MT. Les `2^B` états de cette
tranche sont tous évalués. Cette construction est utile pour valider le modèle et
mesurer la réduction du domaine ; elle ne réduit pas l'état général de MT19937 de
19 937 bits à `B` bits.

## Résultats synthétiques reproductibles

Commande exécutée dans l'environnement de développement :

```bash
python3 sorted_mt_family_solver.py --dimensions 12 16 20 22 24 \
  --train-draws 24 --holdout-draws 12
```

Les 36 tirages représentent 720 sorties, donc le replay traverse la frontière de
twist à 624 mots. Le candidat est sélectionné avec la seule contrainte de première
boule sur l'apprentissage. L'ensemble complet des 24 tirages d'apprentissage et
les 12 tirages de holdout sont ensuite rejoués sans erreur.

| `B` | États énumérés | Contraintes avant unicité | Temps solveur | Temps total | Holdout |
|---:|---:|---:|---:|---:|:---:|
| 12 | 4 096 | 6 | 0,0007 s | 0,0167 s | 12/12 |
| 16 | 65 536 | 9 | 0,0081 s | 0,0275 s | 12/12 |
| 20 | 1 048 576 | 11 | 0,1173 s | 0,1434 s | 12/12 |
| 22 | 4 194 304 | 11 | 0,4940 s | 0,5133 s | 12/12 |
| 24 | 16 777 216 | 12 | 2,3690 s | 2,3916 s | 12/12 |

Ces temps sont indicatifs et dépendent de la machine. Le résultat important est la
croissance exponentielle du domaine, pas la vitesse absolue. Dans ces expériences,
la disjonction exacte retire environ deux bits par tirage, comme attendu pour
« une boule parmi les 20 publiées sur 80 ». Cela confirme que l'ensemble trié
contient une contrainte utile, tout en montrant qu'une simple énumération ne peut
pas être extrapolée au domaine `2^19937`.

Un contrôle complémentaire avec 20 affectations vraies distinctes à `B=20` a
récupéré 20/20 états et rejoué 20/20 séries de holdout de 12 tirages. L'unicité
demandait entre 10 et 14 tirages (moyenne 10,95, médiane 10,5). Ce contrôle réduit le risque que le résultat
du tableau soit propre à une affectation favorable ; il ne change pas la limite
exponentielle.

## Vérifications

```bash
python3 -m unittest -v test_sorted_mt_family_solver.py
```

Les tests couvrent le vecteur officiel de sortie de MT19937, la linéarité GF(2) du
twist, l'équivalence entre formes affines et exécution concrète avant et après une
frontière de twist, l'exhaustivité du support disjonctif et le replay du holdout.

## Conclusion honnête

Le prototype démontre sur MT19937 — et non sur un petit LFSR de remplacement — que
la perte de permutation ne détruit pas toute l'information. Il ne démontre ni que
le générateur réel est MT19937, ni que le problème complet est calculable avec
cette méthode. La prochaine étape algorithmique doit conserver les XOR de façon
native et compresser les disjonctions (XOR-SAT, BDD ou élimination hybride), au lieu
d'énumérer l'état.
