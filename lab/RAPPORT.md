# De combien peut-on améliorer les prédictions ?

Réponse courte, en quatre nombres :

| | |
|---|---|
| Amélioration possible par une meilleure **prédiction** | **0 %** — c'est un théorème, pas un résultat empirique |
| Plafond d'un biais **non détecté**, pour qui **connaîtrait** la règle | **+3,2 %** de rendement |
| Ce qu'un joueur pourrait **réellement** en tirer, devant l'identifier lui-même | **≈ +1,0 %** sur la famille mesurée |
| Avantage que l'app **affiche aujourd'hui** sur des données équitables | **+18 % à +34 %**, entièrement artefactuel |

Le seul gain substantiel disponible n'est donc pas dans la prédiction. Il est
dans le fait de cesser d'en annoncer une qui n'existe pas.

Protocole, API et règles : `lab/README.md`. Registre de tous les tests :
`lab/ledger.jsonl`. Chaque chiffre ci-dessous sort d'un script de
`lab/experiments/`, reproductible d'un bloc.

---

## 1. La prédiction est plafonnée à zéro, pas « difficile »

Sous H₀, les hits d'une grille de `k` numéros suivent une hypergéométrique
(80, 20, k), d'espérance `k/4` — **quel que soit le choix des numéros**.
L'espérance d'une hypergéométrique ne dépend pas de quels numéros on coche,
seulement de combien.

Ce n'est pas une observation qu'un meilleur modèle pourrait démentir : c'est
une identité. Chauds, froids, retards, essaim de 26 têtes, réseau de
neurones — tout donne exactement `k/4`. Vérifié en marche avant sur les
70 060 tirages évaluables (`a0_baselines.py`, écart-type de la moyenne
0,0049) :

```
les plus chauds       2,5074   z = +1,53        chauds sur 200   2,5050   z = +1,02
les plus froids       2,5051   z = +1,04        chauds sur 20    2,4988   z = −0,25
plus gros retard      2,5030   z = +0,61        fixe 1..10       2,4971   z = −0,60
retard le plus court  2,4976   z = −0,49                          H₀ = 2,5000
```

Les `log10(e)` valent tous entre −53 et −62 : l'e-process s'effondre parce
qu'il n'y a rien à parier. Les sept prédicteurs ont passé le contrôle de
fuite.

Toute la question « peut-on mieux prédire » se réduit donc à : **existe-t-il
un biais ?**

## 2. Il n'y en a pas — et on sait désormais à quelle sensibilité

`claude/AUDIT-CLAUDE.md` avait fermé quatorze voies. Le labo en ajoute quatre,
choisies pour leurs angles morts, et — c'est la différence — **mesure sa
propre puissance** à chaque fois.

**15ᵉ voie — démarrage à froid aux 345 reprises de session**
(`a2_cold_start.py`). Le §8 de l'audit n'attaquait ces reprises que par
reconstruction de graine, donc en postulant une famille d'algorithme. La
question statistique non paramétrique n'avait jamais été posée. Huit tests
pré-enregistrés, nulls simulés à la taille de cohorte (n = 345, pas 70 560).
Nul : ni champ déformé, ni rémanence d'état (recouvrement 4,870 avec le
dernier tirage d'avant la coupure — *sous* 5, pas au-dessus), ni collision de
graine (max 13/20). Les deux z de +2,5 observés sont la même fluctuation
comptée deux fois : la somme des recouvrements mutuels vaut `Σₙ C(cₙ,2)`,
fonction des mêmes comptes de colonnes que le χ². **Puissance** : une
rémanence portant le recouvrement à 5,5 aurait été vue à 99 %, un pool
partagé 76/80 à 100 %.

**16ᵉ voie — rupture à résolution libre** (`a3_changepoint.py`). Le §15 de
l'audit testait 8 fenêtres fixes de 9 000 tirages ; un défaut de trois
jours y serait dilué au dixième. Balayage à pas fin, 4 statistiques,
fenêtres de 200 à 9 000. Le max observé vaut **|z| = 5,24** — contre un seuil de test unique,
cela annoncerait une rupture à 5 σ. Calibré contre **la loi du max du même
balayage** sur 300 archives SRS complètes : **p = 0,066**. C'est l'artefact
que tout le protocole existe pour neutraliser, et il apparaît ici sur les
vraies données.

Sa courbe de détectabilité dit exactement ce qui aurait pu passer :

| fenêtre corrompue | +5 % | +10 % | +20 % | +40 % |
|---|---|---|---|---|
| 200 tirages (≈ 1 jour) | 0,00 | 0,00 | 0,00 | 0,58 |
| 500 tirages | 0,00 | 0,00 | 0,28 | 1,00 |
| 2 000 tirages (≈ 10 jours) | 0,00 | 0,10 | 1,00 | 1,00 |

**17ᵉ voie — covariables temporelles et périodicités** (`c3_temporel.py`).
`unix_utc` n'avait jamais servi de covariable : une charge serveur qui varie
selon l'heure, un cron à heure fixe ou un week-end différent ne produiraient
ni rupture (a3 aveugle) ni signature de reprise (a2 aveugle) — seulement une
modulation périodique, invisible en agrégat. Fait structurel établi d'abord :
l'horaire est ancré sur l'horloge **locale** Europe/Zurich (06:05 → 23:00,
204 tirages/jour ; les deux seuls gaps nocturnes anormaux sont exactement les
nuits de changement d'heure), donc le rang dans la session **est** la
position dans la journée locale. Cinq covariables (heure locale, jour de
semaine, minute dans l'heure — détecteur de cron —, position dans le mois,
créneau du jour = rang de session) × quatre statistiques (χ² d'homogénéité
des 80 fréquences, recouvrement lag-1, somme des 20 numéros, loi du boost),
plus trois périodogrammes dont le max est calibré contre **la loi du max du
même balayage** (35 280 ordonnées FFT sur la somme, 6 périodes physiques
6 h–168 h en temps réel, 35 107 ordonnées sur le recouvrement). 23 tests
pré-enregistrés, nulls simulés sur 400 archives SRS complètes partagées.
**Nul partout : 0 drapeau sur 23** (z du null simulé) :

| covariable (groupes) | χ² champ | ov1 | somme | boost |
|---|---|---|---|---|
| heure locale (18) | −0,82 | +1,15 | −0,43 | −0,18 |
| jour de semaine (7) | −0,44 | −0,37 | +0,07 | +0,09 |
| minute dans l'heure (12) | −0,45 | +0,82 | +0,56 | −2,04 |
| position dans le mois (3) | +0,41 | −0,97 | −1,02 | −0,02 |
| créneau du jour (204) | +1,20 | +1,36 | +1,12 | −0,33 |

Spectres : FFT somme z = −0,32, ciblé 6 périodes z = −0,39, FFT recouvrement
z = −0,72. Aucun pic à 204 tirages (un jour) ni à 1 428 (une semaine) : les
cinq plus fortes ordonnées tombent sur des périodes de 2,4 à 5,9 tirages, et
le maximum vaut 10,70 contre un null de 11,13 ± 1,35. Le seul p sous 0,05
(boost par minute, p = 0,040) est un χ² **inférieur** à son attente — moins
de variation que le hasard, pas plus, et la base rate à 23 tests suffit.
**Puissance**, par famille :

| défaut injecté (amplitude mesurée, pas supposée) | détecteur | puissance |
|---|---|---|
| modulation 24 h de la somme, crête 1,2 pt (0,013 σ) | périodogramme ciblé | 0,93 |
| modulation 24 h, crête 2,2 pts (0,024 σ) | ciblé / FFT / heure | 1,00 / 0,72 / 0,97 |
| modulation 24 h, crête 4,2 pts | les trois | 1,00 |
| modulation 168 h (hebdo), crête 2,2 pts | ciblé / jour de semaine | 0,97 / 0,97 |
| pool réduit à 78/80 pendant une heure de la journée | χ² champ \| heure | 1,00 |
| pool 76/80 sur un seul créneau de 5 min (n = 346) | χ² champ \| créneau | 1,00 |
| recouvrement lag-1 +0,25 pendant une heure | ov1 \| heure | 1,00 |
| P(répétition) modulée à 24 h, amplitude 0,10 ov | périodogramme ov1 | 1,00 |
| boost collé à 1 (ε = 0,05) sur un tiers du mois | boost \| position mois | 0,98 |

La modulation périodique devient donc invisible sous ≈ 1 point de somme en
crête — 0,01 écart-type par tirage, un ordre de grandeur sous le plafond du
§3. Réplicats de puissance réduits (30–40 par point) pour tenir le run en
8 min ; le seuil de détection |z| ≥ 3 est plus lâche que le Holm final, la
puissance au seuil Holm est donc ≤ à celle affichée (même convention que la
16ᵉ voie).

**18ᵉ voie — la structure de troisième ordre : les 82 160 triplets**
(`d1_triplets.py`). Le §2 de l'audit avait testé les 3 160 paires
(|z|max = 3,68, conforme) ; les C(80,3) = 82 160 triplets — un espace 26
fois plus grand, et le mode de défaillance classique des générateurs à
faible discrépance (les hyperplans de Marsaglia portent précisément sur la
dimension 3 et au-delà) — n'avaient jamais été comptés. Chaque triplet
apparaît ~979 fois (sd 31) sur les 70 560 tirages : largement testable.
Trois statistiques pré-enregistrées, une par régime de défaut : **max de
|z|** sur les 82 160 comptes (anomalie localisée), **somme des z²**
(structure diffuse), **max de |z| sur 5 agrégats structurés** — progressions
arithmétiques (1 560 triplets), même dizaine (960), même reste mod 2, 5, 10
(19 760, 2 800, 560) — le motif qu'un défaut de discrépance produirait.
Les comptes ne sont pas indépendants (leur somme vaut exactement 1 140·N,
et deux triplets partageant deux numéros sont corrélés) : l'écart-type
simulé de l'agrégat mod 2 vaut 12 749 contre 4 354 si les cases étaient
indépendantes, celui de la même-dizaine 1 768 contre 960 — une loi tabulée
mentirait ici dans les deux sens selon la famille. Les trois nulls sont
donc simulés sur 300 archives SRS complètes (mêmes réplicats partagés).

**Nul partout.** Le max observé vaut **|z| = 4,75** (triplet {10, 15, 38},
832 sorties au lieu de 979) — contre un seuil de test unique ce serait une
anomalie à 4,7 σ ; contre la loi simulée du max sur 82 160 cases
(4,48 ± 0,27), **p = 0,31**. C'est l'artefact de la 16ᵉ voie, réapparu à
l'identique et neutralisé par le même protocole. Somme des z² : z = −0,34,
p = 0,72. Motif : p = 1,00, le plus grand agrégat (mod 5) vaut z = −1,44.
Les 50 triplets les plus déviants ne dessinent rien : 0 progression
arithmétique, 0 même-dizaine, 0 consécutif (nulls simulés 1,0 / 0,6 /
0,04) ; le seul écart nominal — 18/50 de même parité contre 11,7 attendu,
P = 0,050 — est un diagnostic parmi six, et la base rate suffit.
**Puissance** :

| défaut injecté (amplitude connue par construction) | détecteur | puissance |
|---|---|---|
| 8 triplets sur-représentés de +18 % chacun (+174 occurrences/triplet) | max | 1,00 |
| idem, +13 % | max | 0,53 |
| idem, +9 % | max | 0,03 |
| famille AP entière gonflée de +0,37 % (un AP forcé dans 8 % des tirages) | motif | 0,83 (max : 0,00) |
| idem, +0,18 % | motif | 0,27 |
| pool groupé : 40 numéros à +0,68 % marginal, 9 880 cases à ≈ +0,6 σ | sumsq | 0,53 (max : 0,00) |

Une sur-représentation localisée devient donc invisible sous ≈ +15 % par
triplet (~130 sorties en excès sur 979), un motif AP diffus sous ≈ +0,3 %
d'excès agrégé — et les trois statistiques voient bien trois choses
différentes : le max ne voit pas le diffus, le motif ne voit pas le
localisé, sumsq seule voit le pool groupé (témoin qui serait de toute
façon attrapé d'abord par le χ² marginal, voie fermée). Réplicats : null
300, puissance 30/point au plancher empirique du null (p = 3,3 × 10⁻³) ;
le seuil Holm final est plus strict, la puissance y est ≤ à celle
affichée. Run complet ~12 min.

**19ᵉ voie — le couplage à tous les lags de 1 à 306** (`d2_lags.py`).
`c1_conditionnel.py` n'avait testé que le lag 1 et l'écrivait dans ses
limites. Un tampon circulaire, un cache de taille fixe ou une graine
réutilisée toutes les N sorties produiraient un couplage à un lag précis,
**invisible au lag 1**. Les deux statistiques de `c1` — recouvrement moyen
(T1) et norme de la matrice de couplage (T2) — ont donc été appliquées à
306 lags, en incluant explicitement les lags structurellement suspects :
k = 12 (une heure), k = 204 (une journée complète de tirages), k = 288,
k = 408, k = 1 428 (une semaine). Tous conformes, |z| ≤ 1,88. Et la loi du
**maximum sur les 306 lags** est calibrée comme telle sur 300 archives
complètes — sans quoi le balayage fabriquerait un signal à tous les coups :

```
T1  max |z| = 2,89  au lag 209   p = 0,482
T2  max |z| = 3,05  au lag 265   p = 0,784
```

Sa courbe de puissance confirme sur toute la plage la dichotomie que `c1`
avait trouvée au lag 1, et elle justifie après coup d'avoir porté les deux
statistiques : une rémanence diagonale est vue à 70 % par T1 et **jamais**
par T2 ; un dérangement en paires cachées à 83 % par T2 et **jamais** par T1.
Chacune est totalement aveugle à ce que l'autre voit. Le plafond conditionnel
passe de +3,21 % (lag 1 seul) à **+3,46 %** : balayer 306 lags coûte un peu
de puissance, comme attendu.

**20ᵉ voie — la dépendance non linéaire** (`d3_nonlineaire.py`), la seule
famille que le labo avait explicitement déclarée non bornée. Trois angles :
la **forme** de la loi du recouvrement et pas seulement sa moyenne (S1) ; la
corrélation et l'information mutuelle entre recouvrements successifs (S2,
S3) — l'information mutuelle capte une dépendance de forme quelconque là où
la corrélation ne voit que le linéaire ; et un **gradient boosting** en
marche avant, avec témoins positifs, contrôle de fuite passé et accord
bulk/causal exact.

```
S1  forme de la loi de O (13 cases)   z = +3,47   p = 0,010
S2  corrélation successive            z = −2,03   p = 0,037
S3  information mutuelle              z = +1,30   p = 0,216
modèle non linéaire, marche avant     2,4997 hits   z = −0,05
```

### Le plus grand écart du dossier, et pourquoi il ne tient pas

`S1` est la plus forte déviation qu'une statistique pré-enregistrée ait
produite dans tout ce labo, et le script se termine lui-même par « voir
chasse à l'artefact avant toute annonce ». `d3b_chasse.py` est cette chasse.
Trois vérifications indépendantes, chacune capable de tuer le signal :

- **La sur-dispersion ne le confirme pas.** La forme observée — excès à
  O = 2 (+2,53) et O = 8 (+3,13), déficit à O = 10 (−2,46) — se lit
  naturellement comme des épaules plus lourdes, et cette lecture tient en
  *une* statistique interprétable au lieu d'un χ² sur 13 cases : la variance
  du recouvrement. Elle vaut 2,86271 contre un null de 2,84828 ± 0,01516,
  soit **z = +0,95**. Le χ² capte un motif que le résumé naturel ne voit pas.
- **Il ne se réplique pas.** 1ʳᵉ moitié `z = +1,33`, 2ᵉ moitié `z = +2,80`.
- **Il est localisé.** Par huitième d'archive, sept sont dans le bruit
  (±1,1), le quatrième sort à +3,38 — exactement le régime que la 16ᵉ voie
  a déjà borné (`p = 0,066` sur son maximum).

Les coupures de session sont écartées : les 345 paires à cheval vont dans
l'*autre* sens et sont deux cents fois moins nombreuses.

**Verdict : fluctuation de base rate.** `p = 0,010` contre un seuil de
registre à 1,5 × 10⁻⁵ — trois ordres de grandeur — et rien ne l'en rapproche.

Ce que je ne classe pas pour autant : `c4_meta.py` a établi qu'un biais réel
*réglé pour produire exactement l'écart observé* serait presque
indistinguable d'une fluctuation à cette taille d'échantillon appariée.
L'absence de réplication interne est donc une **preuve faible**. C'est le
seul point du dossier qui mérite d'être re-testé sur des données **neuves**
plutôt que classé — et la seule source de données neuves est l'app.

**21ᵉ voie — la forme interne d'un tirage** (`d4_forme_interne.py`). Toutes
les voies précédentes examinent soit les relations *entre* tirages, soit les
marginales *à travers* les tirages. Une seule statistique touchait à
l'intérieur d'un tirage — le comptage d'adjacences du §2 de l'audit, et
seulement sa moyenne. Or un tirage est un objet géométrique, 20 points sur
[1, 80], et sa forme est précisément ce que rate un générateur à mauvaise
discrépance. Quatre profils sur leur distribution **complète** — écarts entre
numéros triés consécutifs, adjacences, somme, profil de dizaines — max |z| =
1,01 contre une loi du max à 1,44 ± 0,82, **p = 0,654**. Puissance : le test
voit une déformation dès qu'elle déplace la moyenne d'adjacences de 0,024 sur
4,7465, soit un demi-pourcent, sans qu'aucune fréquence marginale ne bouge.

**22ᵉ voie — le contenu conditionné au boost** (`d5_boost_contenu.py`). Le
boost avait été testé pour sa loi, sa mémoire, sa matrice de transition, son
lien au temps — toujours comme une série à part. Jamais dans l'autre sens :
le tirage est-il différent selon la valeur du boost qui l'accompagne ? C'est
pourtant le point de fuite naturel si boost et numéros sortent du même flux,
et il est invisible à tout ce qui précède puisqu'il ne touche ni la loi
marginale du boost ni celle des numéros. Le null par **permutation des
étiquettes** est exact et préserve les deux marginales par construction :
champ `z = −0,04`, somme `+0,27`, adjacences `−0,51`, recouvrement `+1,70` ;
max calibré **p = 0,254**. Puissance : un lien de 5 % serait vu à 72 %, de
10 % à 100 %.

**Une voie close par absence de donnée, et non par test.** L'horodatage
pourrait porter un canal — un générateur qui fait du rejet met plus longtemps
à produire certains tirages. Mais 70 548 tirages sur 70 560 tombent
*exactement* sur la grille des 300 secondes, et les douze écarts restants
valent 1 à 4 secondes. Il n'y a rien à mesurer. De même, l'ordre de sortie
des boules est absent des **huit** fichiers (0 tirage non trié sur 70 560).

**23ᵉ voie — la VALEUR du bonus** (`d7_bonus.py`). Le bonus est un numéro
publié à chaque tirage : 70 560 échantillons, et une **seconde sortie du
générateur**. L'audit avait testé son *rang* dans le tirage trié et le
recouvrement conditionné à une correspondance ; personne n'avait regardé sa
*valeur*. Cinq statistiques, null simulé sur 300 archives complètes **avec**
un bonus tiré uniformément parmi les 20 :

```
loi marginale sur les 80 numéros        z = +0,99   p = 0,349
bonus_t -> bonus_{t+1} (matrice 80x80)  z = +1,92   p = 0,057
bonus_t dans le tirage t+1              z = −2,58   p = 0,010
rang du bonus, re-dérivé                z = +1,35   p = 0,160
balayage 60 lags, max calibré           max |z| = 2,42 au lag 1, p = 0,638
```

**Et ici la table de l'audit était juste.** Son test de rang comparait
χ²(19) = 27,46 à un seuil **tabulé** de 30,14, sans null simulé — la règle
n° 1 du labo ne lui avait jamais été appliquée. Re-dérivé : le null simulé
vaut `19,06 ± 6,23` contre la théorie `19,00 ± 6,16`. Après cinq occasions
où une table a menti dans ce dossier, il faut dire quand elle ne ment pas.

### Le résidu le plus cohérent du dossier — et ce qu'il vaut

`V3` mérite un traitement à part (`d7b_chasse.py`). Contrairement à `S1`, il
survit à **toutes** les vérifications que l'archive permet :

- **Réplication** : même signe dans les deux moitiés (`z = −2,30` et
  `−1,13`) et dans 7 huitièmes sur 8. `S1` changeait de camp.
- **Spécificité de lag** : le lag 1 est singulier. Les lags 2 à 30 ont une
  moyenne de `z` de `+0,011` (H₀ : 0 ± 0,186) et 13 négatifs sur 29 — du
  bruit pur.
- **Placebo** : en remplaçant le bonus par un des 20 numéros tiré nous-mêmes,
  l'écart disparaît (cinq essais entre `−0,70` et `+1,45`). Il est spécifique
  au champ bonus réel, pas au calcul ni aux tirages.
- **Ce n'est pas une dérive du tirage** : le recouvrement global des mêmes
  paires va en sens *opposé* (`+0,30`).

Ce qu'il faudrait pour le trancher, s'il était réel et stable :

| seuil visé | N total | à collecter | jours |
|---|---|---|---|
| p = 0,05 (test unique) | 46 166 | déjà atteint | — |
| p = 0,001 | 130 037 | 59 477 | 292 |
| seuil Holm du registre | 222 133 | 151 573 | **743** |

**Mais la question qui décide n'est pas celle-là.** Les probabilités
d'inclusion somment à 20 : si le bonus précédent tombe à `0,246049`, les
79 autres montent à `0,250050`. Un joueur qui éviterait systématiquement le
bonus du tirage précédent gagnerait donc :

```
grille de 5  :  1,25025 hits au lieu de 1,25000
grille de 10 :  2,50050 hits au lieu de 2,50000        soit +0,02 %
```

**Une part sur cinq mille.** Même en supposant l'écart entièrement réel et
stable, l'exploiter ne rapporte rien — un déficit sur *un* numéro parmi 80 se
dilue sur les 79 autres, et une grille n'en coche que 5 à 10. À comparer au
plafond de la piste A (+3,46 %), à ce que l'app affiche à tort (+18 à +34 %),
et à l'avantage de la maison (−25 à −35 %).

C'est la conclusion la plus utile de toute la recherche de biais : le plus
beau résidu que 70 560 tirages puissent produire, à supposer qu'il soit réel,
vaut deux centièmes de pourcent.

### Le null lui-même, remis en question — et confirmé (`f1_permutation.py`)

Les 23 voies ci-dessus partagent une hypothèse jamais interrogée : tous les
nulls sont simulés par `lab.srs()`, un tirage SRS 20/80 supposé
**parfaitement uniforme**. C'est une hypothèse, pas une donnée — et si la loi
réelle s'écarte très légèrement de l'uniforme, trop peu pour que le χ²
marginal le voie, tout test calibré contre SRS hérite d'un null mal calibré.

Pour toute hypothèse **temporelle**, il existe un null strictement meilleur :
la **permutation**. Permuter l'ordre des 70 560 tirages réels détruit toute
structure temporelle en préservant EXACTEMENT la distribution empirique
jointe des tirages, quelle qu'elle soit — valide sous la seule hypothèse
d'échangeabilité, sans rien supposer de l'uniformité. `lab.calibrate_perm()`
l'implémente (même contrat que `lab.calibrate()`, `stat(archive)` reçoit une
Archive dont le contenu est permuté, `ts` restant fixe).

**Sanity check.** Sur une archive SRS *propre* (rien à détruire), les deux
nulls doivent coïncider : `calibrate()` 4,99988 ± 0,006818 contre
`calibrate_perm()` 4,99974 ± 0,006145 — ratio de sd 0,90, moyennes à
0,03 sd l'une de l'autre. Implémentation validée avant de la pointer sur les
vraies données.

**Le piège, démontré et pas seulement affirmé.** Une statistique purement
MARGINALE — la loi du bonus sur 80 numéros (V1 de d7) — est invariante par
permutation de l'ordre des lignes : sur 10 réplicats, le null vaut
92,340136 ± 1,5 × 10⁻¹⁴. Un sd numériquement nul : permuter les lignes ne
change *rien* à un compte marginal, le null est un point, pas une loi. La
permutation ne couvre donc que les hypothèses d'**ordre** ou de **covariable
temporelle** ; elle est structurellement aveugle aux marginales (§1 de
l'audit, V1/V5 de d7, c0), aux comptes de triplets (d1_triplets.py) et à
tout agrégat qui ne regarde pas le rang du tirage.

**Re-dérivation** des résultats temporels clés, SRS frais vs permutation
(archive réelle), 150 réplicats chacun :

| statistique | observé | null SRS | z SRS | null PERM | z PERM | sd(perm)/sd(srs) |
|---|---|---|---|---|---|---|
| T1 — recouvrement lag-1 (c1) | 5,0019 | 5,0006 ± 0,0065 | +0,21 | 4,9996 ± 0,0067 | +0,35 | 1,028 |
| **V3 — bonus_t dans t+1 (d7)** | **0,24605** | 0,25001 ± 0,00157 | **−2,52** | 0,25005 ± 0,00152 | **−2,63** | 0,969 |
| S1 — forme du recouvrement (d3) | 30,292 | 12,525 ± 5,23 | +3,40 | 11,372 ± 4,91 | +3,86 | 0,938 |
| c3 heure→somme | 115 440 | 135 010 ± 49 900 | −0,39 | 144 270 ± 46 900 | −0,61 | 0,940 |
| c3 slot→recouvrement | 665,33 | 579,32 ± 52,5 | +1,64 | 569,63 ± 53,5 | +1,79 | 1,019 |

Sur les cinq, le ratio des sd reste dans **[0,94 ; 1,03]** — le null SRS
n'était ni anti-conservateur ni conservateur de façon consistante, il était
juste **correct**, dans le bruit d'estimation à 150 réplicats. Aucun z ne
change de camp ; aucun verdict ne change. `lab.holm()` : 0 significatif,
m passe à 3 311 (+5), seuil quasi inchangé (1,51 × 10⁻⁵).

**Le verdict sur V3, puisque c'est la question qui décide.** z passe de
−2,52 (SRS, recalculé à 150 réplicats — cohérent avec le −2,58 original à
300) à **−2,63 sous permutation**. Le résidu **s'amplifie très légèrement** ;
il ne s'annule pas. p_perm = 0,0066 tombe sur le plancher de Davison-Hinkley
(0 des 150 permutations aussi extrêmes que l'observé, soit 1/151) : c'est une
limite de résolution à 150 réplicats, pas un saut de significativité — le z
est la comparaison qui fait foi, et il dit la même chose que sous SRS, à un
dixième près, à des ordres de grandeur du seuil Holm. **La conclusion de
`d7b_chasse.py` ne bouge pas** : le résidu est réel dans ses vérifications
internes, cohérent sous les deux nulls, et vaut +0,02 % s'il est réel — la
permutation ne le fait ni disparaître ni décoller.

**Puissance — les deux nulls détectent-ils pareil ?** Self-permutation par
réplicat contaminé (80 réplicats de null chacune) contre null SRS fixe,
N=20 000 (réduit — génération séquentielle, ~20-25 µs/tirage), 12 réplicats
par point, seuil |z| ≥ 4,33 :

| rémanence d (T1) | pw SRS | pw PERM | · | déficit bonus (V3) | pw SRS | pw PERM |
|---|---|---|---|---|---|---|
| 0,001 | 0 % | 0 % | | 0,02 | 0 % | 0 % |
| 0,002 | 8 % | 8 % | | 0,05 | 58 % | 58 % |
| 0,004 | 100 % | 100 % | | 0,10 | 100 % | 100 % |
| 0,008 | 100 % | 100 % | | 0,20 | 100 % | 100 % |

**Détection identique à chaque palier, pour les deux familles.** Passer au
null par permutation ne coûte ni ne gagne de puissance ici — cohérent avec
des sd déjà quasi identiques.

**Ce que la permutation couvre** : toute hypothèse d'ordre ou de covariable
temporelle — rémanence/répulsion lag-k (T1/T2 de c1), forme de la loi du
recouvrement (S1 de d3), dépendance sérielle du bonus (V2/V3/V4 de d7),
dépendance à une covariable dérivée de `ts` (c3 : heure, jour, créneau,
minute). **Ce qu'elle ne couvre pas** : toute hypothèse dont la statistique
est invariante par permutation de l'ordre des lignes — les lois marginales
(§1 de l'audit, V1/V5 de d7, c0), les comptes de triplets (d1), le boost non
conditionné à une covariable temporelle. Ce n'est pas une limite qu'on
pourrait lever en rééchantillonnant plus : c'est structurel, le null y est
un point.

**Un résultat utile précisément parce qu'il ne bouge rien** : les 23 voies
temporelles du dossier tenaient déjà sous l'hypothèse d'échangeabilité
seule, plus faible que l'uniformité SRS qu'on leur prêtait implicitement.
L'hypothèse cachée n'était pas fausse — elle était vérifiée, sans jamais
avoir été nommée.

**Registre entier : m = 3 311 tests dépensés, seuil Holm p < 1,51 × 10⁻⁵,
0 significatif.** Ce compte augmente à chaque expérience ; `lab.holm()` le
recalcule depuis `ledger.jsonl` et fait foi sur toute valeur citée ici.

## 3. Le plafond : ce que l'ignorance résiduelle peut au maximum valoir

« On n'a rien trouvé » et « il n'y a rien » sont deux affirmations
différentes, et seule la seconde répond à la question posée. D'où la question
exacte (`c0_plafond.py`) : **parmi tous les biais qui auraient échappé à
70 560 tirages, lequel donne le plus gros avantage à qui le connaîtrait ?**

L'adversaire optimal est constructible. Un biais poussant `m` numéros de `+d`
donne un avantage `min(m,10)·d` pour une grille de 10, et un χ² proportionnel
à `N·d²·m·80/(80−m)`. À détectabilité fixée, l'avantage est maximal en
**m = 10** : au-dessous on perd des numéros à cocher, au-dessus on dilue `d`
sans que la grille en profite. L'adversaire optimal biaise exactement autant
de numéros que la grille en coche — vérifié par balayage, pas supposé.

```
d = 0,0030   puissance 44 %    avantage +0,0332 hits sur 2,50   = +1,33 %
d = 0,0050   puissance 100 %   plus rien ne passe
```

**Le plafond de toute la piste « prédiction » est +1,33 % de rendement** — et
encore, pour un joueur qui connaîtrait ce biais, ce que personne ne peut
puisque par définition il n'a pas été détecté. À comparer à l'avantage de la
maison sur un Keno, de l'ordre de 25 à 35 %.

Deux limites déclarées : le seuil extrapole la queue du null par une
gaussienne (300 réplicats ne donnent pas un quantile à 1,5 × 10⁻⁵), ce qui
déplace le seuil sans déplacer l'ordre de grandeur puisque la puissance passe
de 1 % à 44 % entre d = 0,002 et 0,003 ; et la borne couvre les biais
**marginaux**.

Le cas **conditionnel** est traité au §3 quater, et il se scinde en deux
familles aux bornes opposées : +0,53 % pour une rémanence uniforme, +3,21 %
pour une structure en paires cachées. C'est cette dernière qui fixe le
plafond de toute la piste A.

## 3 bis. Détecter n'est pas identifier — le plafond réalisable est plus bas

Le +1,33 % du §3 est une borne d'**omniscience** : il suppose la règle connue.
Un vrai joueur ne l'a pas. Il doit deviner *quels* numéros sont biaisés, à
partir des mêmes données — et cette seconde étape est plus dure que la
détection. Le χ² met en commun l'écart des 80 numéros pour dire « quelque
chose cloche » ; il ne dit pas quoi.

Mesuré sur des archives à biais connu (`c2_apprentissage.py`), en comparant
un oracle qui joue les 10 numéros réellement biaisés au meilleur
identificateur possible pour cette famille — les 10 plus fréquents observés
jusqu'à `t`, qui est la statistique exhaustive d'un biais marginal :

| d | χ² | détecté ? | oracle | identifié | part captée |
|---|---|---|---|---|---|
| 0,002 | 58 | non | 2,5168 | 2,4967 | −20 % |
| **0,003** | **112** | **oui** | **2,5387** | **2,5248** | **64 %** |
| 0,005 | 166 | oui | 2,5545 | 2,5440 | 81 % |
| 0,008 | 397 | oui | 2,6000 | 2,5982 | 98 % |
| 0,020 | 1 916 | oui | 2,7399 | 2,7399 | 100 % |

À la frontière de détection — d = 0,003, le plus gros biais qui garde une
chance de passer inaperçu — l'identification n'en capte que **64 %**. Le
plafond réalisable tombe donc à **+0,99 %** (2,5248 contre 2,5000). En
dessous du seuil de détection, la part captée devient négative : le joueur
suit du bruit et perd le peu qu'il y avait.

## 3 ter. Ce qu'un modèle appris trouve, avec tous les champs

L'objection qui reste : les stratégies du §1 sont naïves. On a donc donné à
une régression logistique **tous** les champs — fréquences sur 4 fenêtres,
fréquence longue, retard, présence aux trois derniers tirages,
co-occurrence, heure locale cyclique, boost et bonus du tirage précédent —
réajustée en marche avant à trois points de contrôle, chacun sur le seul
passé disponible.

Deux voies de calcul indépendantes des mêmes traits (vectorisée pour
l'entraînement, causale depuis un `Past` borné) s'accordent à 3 × 10⁻⁸, et le
prédicteur appris passe `leak_check`.

**Sur les vraies données : 2,5023 hits, z = +0,41, log₁₀(e) = −44,2 sur
50 560 tirages.** Rien.

Les témoins positifs disent ce que ce modèle aurait vu. Sur un biais
**conditionnel** (rémanence des 20 numéros du tirage précédent), il le trouve
franchement dès d = 0,003 (z = +5,36) et l'exploite jusqu'à 2,73 hits à
d = 0,020. Sur un biais **marginal**, en revanche, il ne voit rien sous
d = 0,020 — alors que le χ² le détecte dès d = 0,005 et que le simple
classement par fréquence en capte 64 % dès d = 0,003.

Ce n'est pas un défaut du montage, et le mécanisme a été isolé plutôt que
supposé. À d = 0,003, le poids appris sur « fréquence longue » — le seul trait
qui porte le biais — vaut **+0,0014**, c'est-à-dire zéro : 18 000 tirages
d'entraînement n'y montrent qu'un signal à environ un écart-type. Pendant ce
temps un poids parasite de −0,53 sur la co-occurrence domine le classement.
Résultat : le modèle retient **0 des 10** numéros biaisés, là où le seul trait
informatif, pris brut, en retrouve **6 sur 10**. À d = 0,020 le poids se met
en place (+0,51) et le modèle retrouve les dix.

Le seuil n'est donc pas celui du signal : c'est celui de l'apprentissage du
poids. D'où la leçon la plus contre-intuitive du labo — **enrichir un modèle
le dégrade quand il n'y a rien de plus à trouver.** La fréquence longue est
la statistique exhaustive d'un biais marginal ; les treize autres traits
n'apportent que du bruit au classement des 80 numéros. Un modèle plus gros
n'est pas un modèle plus sensible.

## 3 quater. Le plafond dépend de la famille de biais — et j'avais tort deux fois

Le §3 borne les biais **marginaux**. J'avais d'abord affirmé qu'un biais
**conditionnel** aurait une borne plus haute, ayant plus de paramètres ; puis
je me suis corrigé en remarquant que le recouvrement moyen agrège 20 numéros
à chaque pas et serait donc très sensible. `c1_conditionnel.py` tranche : les
deux raisonnements étaient justes, mais sur des familles différentes.

| famille de biais | test qui la borne | avantage maximal non détecté |
|---|---|---|
| rémanence uniforme (conditionnel diagonal) | recouvrement moyen | **+0,53 %** |
| marginal (10 numéros poussés) | χ² sur 80 cases | **+1,33 %** |
| **paires cachées (conditionnel général)** | **‖Ĉ‖² sur 6 400 covariances** | **+3,21 %** |

Le mécanisme est net. Une rémanence **uniforme** — les 20 numéros du tirage
précédent tous favorisés — est écrasée par le recouvrement moyen, qui les
agrège tous : borne à +0,53 %, la plus basse des trois. Mais une structure en
**dérangement** — le numéro `i` appelle le numéro `j ≠ i` — laisse le
recouvrement moyen strictement aveugle (`z_T1 ≈ 0` sur toutes les
configurations testées). Il faut alors une statistique matricielle, qui
répartit sa puissance sur 6 400 directions au lieu d'une : borne 2,4 fois
plus haute que le cas marginal.

**Le plafond de la piste A est donc +3,21 %**, atteint par la configuration
la moins visible : 50 lignes modulées, invisibles au test qui borne les deux
autres familles.

Deux choses à porter avec ce chiffre. D'abord, c'est encore une borne
d'**omniscience** — et la pénalité d'identification du §3 bis y serait plus
lourde qu'ailleurs, puisqu'il faudrait estimer une matrice de couplage et non
dix numéros ; elle n'a pas été mesurée pour cette famille. Ensuite, la borne
couvre le **premier ordre linéaire au lag 1** ; étendre aux lags 1 à 100 ne
la monterait que d'environ 5 % (correction de multiplicité), mais une
dépendance **non linéaire** du tirage complet reste non bornée. C'est la
limite que cette expérience lègue à la suivante.

Détail de méthode qui n'en est pas un : l'écart-type du recouvrement moyen
sur 70 559 paires **consécutives** vaut `0,00678` en simulation, contre
`0,00635` si les paires étaient indépendantes — elles se chevauchent, et
l'ignorer sous-estime la variance de 6,7 %. Une formule aurait donc produit
un léger faux signal. C'est la quatrième fois dans ce dossier qu'un null
tabulé aurait menti, après les trois du §1 de l'audit.

Autre chose que le balayage a imposée contre l'intuition : l'adversaire
optimal module **30 à 50 lignes**, soit deux fois plus que ce que le
raisonnement naïf suggère. Son avantage sature à `min(chauds, 10)` — au-delà
de dix numéros favorisés parmi les vingt du tirage précédent, la grille n'en
profite plus, mais la détectabilité, elle, continue de se diluer.

Le test matriciel n'existait pas avant cette expérience — il a donc été
appliqué aux vraies données, pas seulement utilisé pour borner :

```
T1  recouvrement moyen      5,00191    z = +0,30   p = 0,807
T2  somme des carrés de Ĉ   3,164e-03  z = −0,30   p = 0,787
```

Rien. Recouvrement maximal observé sur 70 559 paires consécutives : 13.

## 3 quinquies. La question qu'aucun test individuel ne pose

Holm répond à « **un** de ces tests est-il significatif ? ». Ce n'est pas la
seule question. Une source légèrement défaillante ne produirait pas un test
franc — elle produirait un **léger excès diffus** réparti sur beaucoup de
tests, dont aucun ne franchirait son seuil. C'est précisément ce qu'une
correction de multiplicité, conçue pour être conservatrice, ne peut pas voir.

Sous H₀, les p-values de tests indépendants sont uniformes sur [0,1].
`c4_meta.py` teste cette prédiction sur les **52 p défendables** du registre
(69 identifiants, moins 8 doublons ou contrôles qualité, et 4 transformées
pour tenir compte de leur famille). Le point délicat est la dépendance : les
entrées ne sont pas indépendantes, et un Fisher tabulé sur des p corrélées
fabrique des découvertes. Le null est donc simulé en rejouant la structure du
registre, avec deux bras — indépendance totale, et joints exacts simulés plus
bornes comonotones.

| combinaison | ce qu'elle voit | observé | p (indép.) | p (dép.) |
|---|---|---|---|---|
| Fisher | les petites p | 114,53 | 0,184 | 0,308 |
| Stouffer | un décalage cohérent | +0,77 | 0,286 | 0,629 |
| Kolmogorov-Smirnov | la distribution entière | 0,117 | 0,448 | 0,996 |
| Anderson-Darling | les queues | 0,559 | 0,750 | 1,000 |

Conforme dans les deux bras. Le bras « indépendance » est le plus défavorable
au verdict de conformité — c'est donc lui qui fait foi, et la vérité est entre
les deux.

**Puissance mesurée**, sur une dérive diffuse Beta(b, 1), au niveau nominal :
`b = 0,5` détecté à 100 %, `b = 0,7` à 83 %, `b = 0,8` à 50 %, `b = 0,9` à
21 %. Une dérive faible resterait donc invisible. Et au seuil Holm du registre,
**aucune dérive diffuse plausible ne passerait** — ce qui est exactement
pourquoi cette méta-analyse existe : elle couvre l'angle mort que la
correction de multiplicité, conçue pour être conservatrice, ne peut pas voir.

### Une erreur de conception de mon registre, corrigée

Les quatre plus petites `p` du registre étaient des **extrêmes de famille
consignés sans leur correction** — `seed_ledger.py` gardait le `p` brut de
l'extrême et ne portait la taille de la famille que dans le compte `m_extra`.
Pour la correction de multiplicité c'est suffisant ; pour une méta-analyse
c'est un biais vers la significativité par construction. Transformées en `p`
familiales `1 − (1 − p)^F` :

```
audit.paires        0,0002 -> 0,469   (F = 3 160)
audit.maurer        0,041  -> 0,314
audit.fenetres_bm   0,0425 -> 0,294
audit.fenetres_maurer 0,051 -> 0,342
```

### Ce que la méta-analyse a montré avant d'être diluée

Nuance à ne pas taire : sur l'instantané au moment de sa conception — 27 `p`
défendables, avant que `c1` et `c3` n'entrent au registre — Fisher et KS
donnaient `p ≈ 0,016–0,03`, un excès diffus **nominal** porté par cinq petites
`p`. Les 25 tests neufs, tous conformes, l'ont dilué.

Ce n'est pas un tour de passe-passe : des tests neufs qui conforment sont des
preuves, et les diluer est le comportement correct d'une méta-analyse. Mais
cela veut dire que ce résultat dépend de la composition du registre, et il faut
le dire. Le volet réplication ci-dessous montre indépendamment que les moteurs
de cet excès se dégonflent un à un.

### Le seul signal résiduel de l'audit ne survit pas à la règle du labo

L'audit gardait un `p = 0,041` — le test de Maurer à `L = 14`, son plus petit
p. Ce chiffre était **tabulé** (gaussienne NIST) avec `K = 36 030`, soit 450
fois sous la recommandation `K ≥ 1000·2^L`. La règle n° 1 du labo ne lui avait
jamais été appliquée.

Re-dérivé avec un null **simulé** sur le pipeline complet : `E[fₙ] = 13,167328
± 0,007159` contre `13,167693` en table, et `z = +1,96` au lieu de `+2,045`.
Le p passe à 0,047 — et surtout, **l'écart était dans le sens « trop
aléatoire »** (fₙ haut = flux moins compressible), ce qui est incompatible
avec une source défaillante dès le départ. Verdict : affaibli, et de toute
façon orienté du mauvais côté pour signifier quoi que ce soit.

Le troisième signal de l'audit — le recouvrement conditionné au bonus,
`p = 0,044`, lui aussi tabulé — subit le même sort : null re-dérivé par
chaînes complètes (dépendance exacte, effectif de correspondances aléatoire),
`5,5705 ± 0,0550`, `p = 0,047`. Base rate, avec un témoin de rémanence détecté
à 97 %.

### Une limite que la réplication met à nu

Le χ² du champ au rang 1 (`a2`, `p = 0,0145`) a été soumis à un test de
réplication : un vrai signal se retrouve dans les deux moitiés temporelles
disjointes, une fluctuation non. Résultat : **non répliqué** (`p = 0,134`
conditionnellement au χ² plein).

Mais la leçon est dans la puissance, pas dans le verdict. Un biais réel
*réglé pour produire exactement le χ² observé* serait presque indistinguable
d'une fluctuation, à cette taille d'échantillon appariée. **L'archive seule ne
peut pas répliquer ce signal — seules des données nouvelles le pourraient.**
C'est une limite de la méthode, pas un résultat sur le générateur.

## 4. Le boost — le seul endroit où le signe de l'espérance pourrait changer

Le boost multiplie les gains, vaut {1, 2, 3, 4, 5, 10} d'espérance 2,0117, et
n'est **pas prédictible** depuis le passé (`b2_mises.py`) : répétition lag-1
0,3446 contre null permuté 0,3451 ± 0,0016 (p = 0,74), transition 6×6
χ² = 19,0 (p = 0,39). Puissance mesurée : un collage de ε = 0,01 aurait été
vu à 82 %, ε = 0,02 à 100 %. Le seuil d'exploitabilité exige ε ≈ 0,134, soit
une cinquantaine d'écarts-types au-delà.

Mais **s'il était publié avant la clôture des mises**, ne jouer que les
tirages à boost = 10 (7,2 par jour) vaudrait +150 % à +360 % par franc selon
le taux de retour. C'est le seul point du dossier où une réponse positive
changerait le *signe* de l'espérance. L'a priori est négatif — le boost est
tiré avec le tirage — mais cela mérite un instrument plutôt qu'une
supposition, et l'archive ne peut pas trancher : elle ne contient pas l'heure
de clôture.

## 5. Le choix de la mise n'est pas identifiable hors ligne

Loi des hits exacte et vérifiée : P(grille pleine) va de 1/1 551 (k = 5) à
1/8 911 711 (k = 10) ; P(zéro hit) de 0,227 à 0,046.

Mais **aucun barème réel n'existe dans le dépôt** — l'app le dit elle-même
(`HistoryView.swift:282`) : l'API publie les jackpots k/k, pas les rangs
intermédiaires. Testé sur trois barèmes paramétriques et 2 000 barèmes
aléatoires à taux de retour égalisé : la meilleure mise change d'un barème à
l'autre (k = 6, 10 ou 5 selon la variante), et aucune comparaison n'atteint
95 % de robustesse. La réponse solide est négative et utile : **l'écart entre
les mises est fixé par l'opérateur, pas par k**, et toutes sont à espérance
négative. Kelly conclut `f* = 0`.

## 5 bis. Le seul seuil qui fasse changer l'espérance de signe

C'est la chose la plus actionnable du dossier, et elle ressemble enfin à une
prédiction utile : non pas *quels numéros*, mais **quand jouer**.

Le blocage du §5 était que le barème des rangs intermédiaires n'est pas
publié, donc l'espérance totale n'est pas calculable — et l'app se contente
de l'affirmer négative (`GridsView.swift:148`). Mais on n'a pas besoin du
barème pour établir une condition **suffisante**. Le gain d'un ticket vaut

```
gain = jackpot·P(k/k) + Σ (rangs intermédiaires) ≥ jackpot·P(k/k)
```

puisque tous les rangs intermédiaires sont positifs ou nuls. Donc dès que
`jackpot ≥ mise / P(k/k)`, le pari est favorable — et **tout ce qu'on ignore
du barème ne peut que rendre l'inégalité meilleure, jamais pire**.

| mise | P(grille pleine) | jackpot suffisant, par franc misé |
|---|---|---|
| **5** | 1 / 1 551 | **CHF 1 551** |
| 6 | 1 / 7 753 | CHF 7 753 |
| 7 | 1 / 40 979 | CHF 40 979 |
| 8 | 1 / 230 115 | CHF 230 115 |
| 10 | 1 / 8 911 711 | CHF 8 911 711 |

Le seuil de la mise à 5 est le seul d'un ordre de grandeur qu'un jackpot
progressif puisse atteindre. L'app affiche déjà les montants k/k en direct
(`LoroClient.parseJackpots`) et calcule même le retour du jackpot par franc
misé ; il ne lui manquait que le seuil auquel le comparer.

**Et cela corrige une affirmation qu'elle fait sans condition.**
`GridsView.swift:148` et `docs/ESSAIM.md` §6 disent tous deux, sans réserve,
que « l'espérance totale reste négative ». Cette affirmation ne peut pas être
justifiée : elle porterait sur une somme dont un terme — le barème
intermédiaire — est inconnu. Et au-dessus du seuil, elle est *démontrablement
fausse*. Ce n'est pas un détail rhétorique : c'est le seul énoncé du produit
qui pourrait faire manquer à son utilisateur la seule occasion favorable que
ce jeu puisse offrir.

Ce que l'archive ne peut pas dire, en revanche, c'est **à quelle fréquence**
le seuil est franchi : elle ne contient aucun montant de jackpot, et le
réseau est fermé. La question se tranche sur l'appareil, en une ligne
d'affichage.

Trois choses que ce seuil **n'est pas**, à ne pas confondre :

- Il ne dit rien sur les numéros à cocher. L'espérance de hits reste `k/4`
  quel que soit le choix (§1) ; le seuil porte sur *l'instant*, pas sur la
  grille.
- C'est une condition **suffisante**, pas nécessaire. Le vrai seuil est plus
  bas — d'autant plus bas que les rangs intermédiaires sont généreux — mais
  il n'est pas calculable sans eux.
- Il ne rend pas le pari bon *en dessous*. En dessous, on ne sait rien de
  plus qu'avant : l'espérance reste négative d'un montant inconnu.

Contrôle de la loi exacte par simulation sur 2 millions de tirages, en cadre
de Poisson (les comptes attendus vont de 1 290 à 0,22 selon la mise, donc un
écart-type sur la fréquence n'aurait aucun sens aux grandes mises) : les cinq
conforment, `p` de 0,30 à 1,00.

## 6. La géométrie des grilles : réelle, mais pas là où on l'attend

L'invariance est ici plus forte qu'il n'y paraît, et il faut la poser avant
tout chiffre : le gain d'un paquet est une **somme de gains par grille**, et
la loi marginale de chaque grille est la même hypergéométrique quel que soit
son contenu. Donc **`E[gain total]` est invariant par géométrie sous
n'importe quelle table de gains par grille** — pas seulement `E[total hits]`.
Aucune géométrie ne peut créer du rendement, quel que soit le barème, connu
ou non.

Ce qui bouge, en revanche, c'est la **forme** de la loi jointe
(`b1_geometrie.py`, 4 millions de réplicats, recoupés par quatre voies
exactes indépendantes ; contrôle d'espérance passé partout à ±4 écarts-types) :

| | k = 5 | k = 10 |
|---|---|---|
| P(≥ 1 grille pleine), étalé / iid | **1,003** | **1,000** |
| Var(total), iid / étalé | **3,75×** | **5,25×** |
| P(zéro hit sur les 12) | 1,9 × 10⁻⁸ → ≈ 0 | 8,5 × 10⁻¹⁷ → **0** |

**Sur l'événement qui intéresse le joueur — décrocher le plein — la géométrie
ne change rien : ratio 1,00 à 1,05.** Ce qu'elle change, c'est la variance
(divisée par 3,75 à 5,25) et le risque de repartir bredouille. À k = 10, la
couverture équilibrée touche les 80 numéros, donc les 20 boules tirées sont
forcément couvertes : P(zéro hit) devient exactement nul.

La structure de l'app est **bonne dans son principe** — I, II et Anti sont
déjà disjointes au sein de chaque famille — et ses deux défauts sont des
**duplications** : Furtif reprend le même champ pénalisé par la popularité et
recouvre I de 3 à 4 numéros sur 5 ; et alpha, omega, nexus sont des mélanges
des mêmes 26 têtes, donc corrélés. Émulée entre les deux bornes de
corrélation inter-familles, `Var(app)/Var(disjoint)` vaut 5,02 (familles
décorrélées) à 14,98 (familles identiques), contre 3,75 pour iid ; sur
`P(max ≥ 4)` à k = 5, l'app fait 0,854 à 0,298 fois le disjoint. Verdict :
**entre indifférente et mauvaise, et mauvaise exactement dans la mesure où
ses grilles se dupliquent.**

Le correctif est local : dans `makeGrids`, bannir l'union de **toutes** les
grilles déjà émises — familles comprises, pas seulement au sein d'une famille
— et appliquer la pénalité de popularité *dans* le greedy plutôt que d'en
faire une quatrième grille qui duplique la première. Douze grilles deux à
deux disjointes sont alors possibles à k = 5 et k = 6 (60 et 72 ≤ 80) ; au-delà
(k = 7, 8, 10) la couverture équilibrée prend le relais.

## 7. Ce que l'app affiche — le seul vrai problème du dossier

`Swarm.makeGrids` (`Swarm.swift:1087`) calcule, et `GridsView.swift:261-262`
affiche côte à côte sur **chaque grille** :

```
ESPÉRANCE  3,35 hits          HASARD  2,50 hits
```

où `expectedHits` est la somme de `sources.inclusion[n]` sur les numéros
**sélectionnés**, et `sources.inclusion` le champ brut de la tête `bayes.b`
(`Swarm.swift:1061`), un posterior Beta escompté à mémoire 33.

Sous H₀ la vraie probabilité d'inclusion vaut 0,25 pour les 80 numéros. Mais
l'**estimateur** a un écart-type de `√(0,25·0,75/33) ≈ 0,075` — 30 % de la
valeur estimée. Or la grille prend les numéros qu'un score corrélé à cet
estimateur classe en tête. On affiche donc la moyenne d'un estimateur bruité
aux points où ce bruit est maximal. C'est la malédiction du vainqueur : elle
est positive à chaque tirage, sur chaque grille, et ne se compense pas.

Mesuré sous H₀ pur — données **équitables par construction**, donc tout écart
est nécessairement un artefact (`b4_expectedhits.py`, mise 10) :

| sélection | affiché | réel | surestimation |
|---|---|---|---|
| mélange z (émulation de `tagBlend`) | 3,354 | 2,500 | **+34 %** |
| mini-essaim 14 têtes (`b3`, indépendant) | 2,96 | 2,50 | **+18 %** |
| **aléatoire (témoin)** | **2,499** | 2,500 | **+0,0 %** |

Deux émulations indépendantes trouvent le même phénomène ; l'écart entre +18
et +34 % vient de la fidélité avec laquelle chacune reproduit la corrélation
entre le score de sélection et `bayes.b`. Le témoin aléatoire tombe pile sur
la base, ce qui établit que l'écart vient de la sélection et non d'un bug de
simulateur. Le plafond par dizaine de `greedyPick` n'y change rien
(nexus +31,2 % contre alpha +31,4 %) : huit dizaines à trois numéros laissent
24 places pour 10 choix, la contrainte ne mord presque jamais.

**L'app connaît déjà cette erreur — ailleurs.** `AnalyseView.swift:285`
avertit : « Choisir le vainqueur après coup surestime toujours — l'essaim,
lui, est jugé en marche avant. » C'est exactement le mécanisme du §7, énoncé
correctement pour la meilleure tête et commis sans avertissement sur les
douze grilles.

**La correction est vérifiée, pas seulement proposée.** Estimer sur une
fenêtre disjointe de celle qui sélectionne ramène l'affichage sur la base :

```
mise 5   naïf 1,787 (+43 %)  ->  fenêtre disjointe 1,247  (−0,3 %)   base 1,250
mise 10  naïf 3,396 (+36 %)  ->  fenêtre disjointe 2,501  (+0,0 %)   base 2,500
```

Ce qui est aussi la réponse de fond : sous H₀ il n'y a **aucun avantage à
afficher**, et une estimation honnête le dit toute seule. Le plus simple est
d'afficher `k/4`, exact et sans estimation.

*Nuance à ne pas exagérer* : `pAllHit`, calculé sur les mêmes probabilités
gonflées (facteur ×6 à k = 5, ×22 à k = 10), n'est **jamais lu** — c'est un
champ mort de `SuggestedGrid`. Ce qui s'affiche en « COTE MAX » est
`basePAllHit`, la valeur hypergéométrique honnête. Le ×22 est donc un bug
latent, pas un mensonge à l'écran.

## 8. La confiance affichée : centrée, mais mal nommée

Audit indépendant de la chaîne `hits → confiance` (`b3_calibration.py`,
`Swarm.swift:908-920`).

**Bonne nouvelle, et elle est établie.** Sous H₀ la confiance est **centrée** :
E = 49,855, médiane 50, sd 14,2, P(> 70) = 0,072. Le plancher
`max(0.2, btSD)` n'est jamais mordu (0 fois sur 10⁶, min btSD = 1,005 — il
faudrait 59 tirages identiques sur 60) et, étant un max au dénominateur, ne
pourrait que *réduire* |z|.

Le mode de fuite qu'on pouvait craindre — repondérer l'essaim sur le
backtest, puis juger le mélange sur ce même backtest — **n'existe pas, et
pour une raison structurelle** : `evaluate()` (`Swarm.swift:764-796`)
enregistre le recouvrement *avant* qu'AdaHedge ne voie les pertes du tirage,
et les têtes n'absorbent le tirage qu'ensuite (`L721`). L'évaluation est donc
préquentielle : chaque point du backtest est hors-échantillon pour le mélange
qui l'a produit. Vérifié plutôt que déduit — un mini-essaim fidèle de
14 têtes donne E = 49,77 contre 49,86 en i.i.d. (Δ = −0,08 ± 0,51).

Sur l'archive réelle : fraction > 70 de 0,0770 contre une bande H₀ de
[0,0585 ; 0,0867], p = 0,37. L'e-valeur reste à 1,259 au maximum sur toute
l'archive (seuil d'alerte : 20) et finit à 2,7 × 10⁻¹⁰⁷ — elle s'appauvrit,
ce qui est le comportement honnête sous H₀. **L'app ne s'imagine pas un
avantage.**

**Mais « confiance » n'est pas une probabilité.** Quand l'app affiche plus de
70, la probabilité que le tirage suivant dépasse l'espérance vaut **0,3741** —
contre 0,3744 sans condition, et 0,3740 quand l'app affiche 50. Strictement
plate. C'est un z rescalé, pas une probabilité calibrée ; l'UI dit bien
« 50 = hasard pur », mais le mot « confiance /100 » invite une lecture que le
chiffre ne supporte pas.

Corollaire à assumer : c'est un compteur de bruit. 7,2 % des consultations
afficheront plus de 70, et le 95 finira par être atteint — avec une
probabilité voisine de 1 sur un historique de cette longueur. Symétriquement,
le 5 aussi (la queue basse est même très légèrement plus lourde). Rien
d'anormal ; mais un utilisateur qui ouvre l'app un jour de 88 lira un signal
là où il n'y a qu'une fluctuation.

## 8 bis. Ce qui a été appliqué à l'app, et ce que ça vaut

L'audit s'est prolongé en correctifs. Chacun est mesuré, aucun ne repose sur
une hypothèse quant au barème inconnu.

### La géométrie du paquet perdait un quart de ses chances

`e1_audit_grilles.py` mesure la géométrie réellement produite, là où
`b1_geometrie.py` ne pouvait que la borner entre deux hypothèses de
corrélation inter-familles. Trois défauts structurels :

- **« Furtif » n'était pas une variante mais un doublon** de la variante I :
  même champ, seulement pénalisé par la popularité — **4,00 numéros communs
  sur 5** (Jaccard 0,69), 8,30 sur 10. Mesure robuste, sans rien supposer des
  têtes : les champs sont des z-scores et la pénalité est connue.
- **`alpha` et `omega` sont anti-corrélées à −0,70.** `alpha` agrège les
  têtes *momentum* (numéros chauds), `omega` les têtes *reversion* (numéros
  en retard) : la contre-épreuve d'une famille **était** la grille principale
  d'une autre. `b1` bornait cette corrélation entre 0 et +1 — il ne pouvait
  pas la voir.
- **Couverture effondrée** : 30 numéros sur 80 à la mise 5, pour 60
  emplacements.

Coût, en probabilité exacte par inclusion-exclusion sur 40 historiques :
**−24,8 %** de `P(au moins une grille pleine)` à la mise 5, −7,7 % à la mise
10. L'app faisait donc **moins bien que douze grilles tirées au hasard**.

Le correctif est une préférence de couverture — pas un bannissement, qui
devient impossible dès que 12k > 80. Il atteint l'optimum théorique à
**0,000 %** près à la mise 5.

### L'objectif choisi était-il le bon ? (`e2_tous_rangs.py`)

Maximiser `P(grille pleine)` n'allait pas de soi : une table de Keno paie
plusieurs rangs, et les deux régimes tirent en sens opposés — étaler
décorrèle les grilles, concentrer les corrèle. **L'étalement domine à tous
les rangs** :

| mise | t = 2 | t = 3 | t = 4 | t = 5 | t = 8 | t = 9 | t = 10 |
|---|---|---|---|---|---|---|---|
| 5 | ×1,024 | ×1,314 | ×1,415 | ×1,165 | — | — | — |
| 10 | — | — | — | — | ×1,085 | ×1,045 | ×1,017 |

Mon Monte-Carlo annonçait pourtant une *perte* aux rangs 9 et 10 de la mise
10 : il y comptait 216 événements contre 256, et quatre contre cinq. Refait
en exact — inclusion-exclusion avec la loi jointe de deux grilles partageant
`s` numéros, calculée par hypergéométrique multivariée — le signe s'inverse.

**Conséquence qui compte** : une dominance rang par rang vaut sous n'importe
quelle pondération positive. L'ignorance du barème devient donc *sans
conséquence* pour cette décision.

### L'affichage est passé de l'estimation aux combinatoires exactes

- **`ESPÉRANCE`** vaut désormais exactement `k/4`. Elle portait la somme du
  posterior de l'essaim sur les numéros sélectionnés par un score corrélé à
  ce même posterior : +18 à +34 % sur des données pourtant équitables.
- **`pAllHit` supprimé** — champ mort et faux d'un facteur 6 à 22.
- **Loi de survie exacte** affichée à la place de la paire redondante
  `ESPÉRANCE / HASARD` : `P(≥ k−1)` et `P(k/k)`, que l'app calculait sans
  jamais les montrer.
- **`P(au moins une des 12 grilles pleine)`**, exacte, qui n'existait pas :
  **1/129** à la mise 5 contre 1/1 551 pour une grille seule.
- **Le seuil de jackpot** : la carte calculait déjà le retour en centimes par
  franc ; le seuil est simplement **100 ct/CHF**. Au-delà, le jackpot seul
  rembourse la mise et le pari est favorable quel que soit le barème.
- **L'écran principal** affiche l'écart en σ au lieu d'un « n/100 » qui
  invitait une lecture probabiliste que le chiffre ne supporte pas.
- **La grille « Furtif »** met son argument au conditionnel : éviter la foule
  ne rapporte que si les gains se partagent, ce que rien n'établit.

## 9. Ce qu'il faudrait faire, par ordre de valeur réelle

1. **Corriger `ESPÉRANCE` sur les grilles** (`GridsView.swift:261`). C'est la
   seule affirmation fausse que voit l'utilisateur. Correction d'une ligne
   dans `Swarm.swift:1133` — `expectedHits: Double(stake) * Self.baseP` au
   lieu de `p.reduce(0, +)` — ou estimation par fenêtre disjointe : les deux
   donnent la même chose sous H₀, la première étant exacte et sans
   estimation.
2. **Renommer la confiance.** Elle est honnête mais son nom promet une
   probabilité qu'elle n'est pas. « Écart au hasard » plutôt que
   « confiance /100 ».
3. **Afficher le seuil de jackpot** à côté des montants k/k déjà affichés
   (§5 bis) : `CHF 1 551` par franc misé pour la mise à 5. C'est la seule
   information du dossier qui puisse dire à l'utilisateur qu'un pari est
   devenu favorable, et elle ne dépend d'aucune hypothèse sur le barème.
4. **Instrumenter la question du boost avant clôture.** L'autre point capable
   de changer le signe de l'espérance. A priori négatif, mais non tranché.
5. **Revoir la géométrie des 12 grilles** : bannir l'union de toutes les
   grilles déjà émises et intégrer la pénalité de popularité au greedy, au
   lieu d'en faire une grille qui duplique la première. À présenter pour ce
   que c'est — un lissage du risque (variance ÷ 3,75 à 5,25, P(zéro hit) → 0),
   jamais comme de la prédiction : `P(plein)` reste inchangée à 1 % près, et
   l'espérance de gain est invariante sous **tout** barème.
6. **Supprimer ou corriger `pAllHit`**, champ mort et faux d'un facteur 22.
7. **Mettre au conditionnel l'argument « Furtif »** : il suppose des gains
   partagés entre gagnants, ce que rien dans le dossier n'établit, et un
   modèle de popularité écrit à la main (`Swarm.swift:1122` : dates ≤ 31,
   multiples de 7 et 11) sans aucune mesure sur les joueurs de ce jeu.

## 10. Les instruments qui répondraient au reste

Spécification complète, code Swift et tests : `lab/experiments/a1_instruments.md`
(rien n'a été appliqué à `Prophet/` — c'est une proposition à valider).

**A — l'ordre de sortie n'est ni agrégé ni conservé.** `parseMatrix`
(`LoroClient.swift:367-380`) préserve déjà l'ordre du tableau `main`, et
`Draw.hasDrawOrder` (`Types.swift:24`) teste s'il diffère du tri. Mais ce
booléen n'est lu qu'à un seul endroit — `PRNGRecovery.swift:417` — consommé
au vol, jamais agrégé, jamais persisté, jamais affiché. **L'app calcule donc
la donnée la plus précieuse du dossier à chaque tirage, et jette la réponse.**
Compter la fraction de tirages où `order != order.sorted()` est un
changement minuscule qui tranche définitivement une question à 62 bits par
tirage.

**B — le boost sur les tirages OPEN n'est pas instrumenté du tout.**
`fetchOpen()` traite `boost` à l'identique quel que soit le statut, et
`LivePayload` ne porte même pas l'information du tirage à venir. C'est la
question du §4, la seule capable de changer le signe de l'espérance.

**C — l'instrument de latence censure une partie de ses échantillons.**
`recordPublicationLatency` (`ProphetStore.swift:300-305`) exige
`previous.nextDrawNumber == newLast.drawNumber` : tout enchaînement qui n'est
pas exactement le tirage annoncé comme suivant est écarté en silence.
L'instrument ne mesure donc que les séquences régulières — alors qu'un cache
mal invalidé ou une race condition se manifestent d'abord quand
l'ordonnancement dérape. Le correctif proposé mémorise la clôture de chaque
tirage dès qu'elle est connue, au lieu de ne regarder que le payload
immédiatement précédent.

Les critères de lecture proposés sont asymétriques, ce qui est correct ici :
une seule observation positive tranche A et B, tandis que conclure à
l'absence demande N = 20 pour A et B, et pour C une règle de trois — N = 300
exclut un taux de fuite ≥ 1 %, N = 3 000 exclut ≥ 0,1 %.

## 11. Ce que ce labo ne peut pas trancher

- **L'ordre de sortie des boules.** L'archive est triée : `n1..n20` est
  croissant sur les 70 560 lignes. Un tirage ordonné porterait ≈ 124 bits
  contre 61,6 pour l'ensemble trié — le plus gros gain d'information
  disponible, et il n'est pas dans les données dont on dispose.
- **Le flux live.** Le réseau vers `jeux.loro.ch` est fermé depuis cet
  environnement (403 au CONNECT). Les questions du boost avant clôture et de
  la latence de publication demandent l'app sur un téléphone.
- **Un défaut d'implémentation ou un accès privilégié.** Hors de portée de
  toute analyse de sorties publiques, quelle qu'en soit la profondeur — ce
  n'est pas une question de méthode mais d'accès (cf. §14 de l'audit).

## 12. Le renversement : tester le prédicteur, et non plus les tirages

Les vingt-trois voies qui précèdent testent toutes une propriété des
**tirages** : une fréquence, un écart, un recouvrement, un décalage. Chacune
doit nommer sa régularité d'avance, et chacune paie sa place au registre.

Cinq expériences ont changé de **méthode** plutôt que de question. Elles ne
demandent plus « telle régularité existe-t-elle ? » mais « qu'est-ce qui,
dans tout ce qu'on a construit, bat le hasard — et de combien, en quelle
unité ? ». Trois d'entre elles répondent sans avoir à nommer quoi que ce
soit d'avance.

### 12.1 L'essaim déployé bat-il le hasard ? (`f3_predicteur.py`)

Personne n'avait jamais testé le prédicteur lui-même. C'est pourtant la
seule question dont la réponse décide du produit.

Pour la poser il faut la **loi de l'essaim sous H₀**, donc pouvoir le rejouer
des centaines de fois sur des archives synthétiques. `lab/swarm_py.py`
transcrit les 26 têtes, leurs constantes, l'ordre des opérations (évaluation
avant absorption, à partir du 13ᵉ tirage), le z-score de population, le
top-20 et AdaHedge. Deux écarts sont assumés et tous deux **conservateurs** :
l'évolution est désactivée — elle ferait de « la tête h » une cible mouvante,
et une tête figée ne peut que sous-performer une tête qui s'adapte —, et les
égalités de tri sont départagées par indice croissant.

Le test est exact sans rien supposer du contenu des prédictions, grâce au
théorème qui borne déjà tout le dossier : pour **tout** ensemble de 20
numéros choisi sans voir le tirage, le recouvrement suit une
hypergéométrique(80, 20, 20), d'espérance 5 et d'écart-type 1,687632. Donc
`S_h = Σ_t (recouvrement_{h,t} − 5)` est une martingale de loi connue. Le
seul inconnu est la **dépendance entre têtes**, obtenue par simulation.

Sur les 70 560 tirages, en marche avant :

| tête | hits/tirage | z |
|---|---|---|
| `pression` (la meilleure) | 5,01195 | +1,88 |
| `acp.2` | 5,01079 | +1,70 |
| … | | |
| `mom.8x32` (la pire) | 4,98771 | −1,93 |
| **ensemble AdaHedge — ce que l'app utilise** | **4,99572** | **−0,67** |

Quatre statistiques pré-enregistrées, contre un null obtenu en rejouant
l'essaim entier sur 12 archives SRS complètes (et un null conditionnel
martingale sur 600 réplicats ; c'est le plus large des deux qui est retenu) :

| | observé | null | z | p |
|---|---|---|---|---|
| **F3-A** meilleure des 26 têtes | +1,881 | +1,914 ± 0,572 | −0,06 | 0,965 |
| **F3-B** ensemble AdaHedge | −0,674 | +0,439 ± 0,999 | −1,11 | 0,256 |
| **F3-C** transfert hors échantillon | −0,214 | −0,087 ± 0,378 | −0,34 | 0,846 |
| **F3-D** têtes effectives | 6,796 | 8,061 ± 2,606 | −0,49 | 0,846 |

F3-A est l'omnibus : la multiplicité du choix de tête est **dans la loi du
maximum**, pas corrigée après coup. F3-C est la seule version *exploitable*
de la question — la tête gagnante d'un pli, payée sur le pli suivant, sans
malédiction du vainqueur.

**Sensibilité.** Sur une contamination momentum à T = 20 000, le seuil à 3 σ
du null est +3,12, et l'essaim détecte 4 fois sur 4 dès **+0,043 hits par
tirage** (+0,85 %). Il ne détecte pas +0,019. Il n'y a rien à ce niveau.

**Conséquence produit.** L'app affiche `TÊTES EFFECTIVES 6,8` sur la carte
« L'ESSAIM », ce qui se lit comme un signe d'apprentissage. Sous le hasard
pur, cette statistique va de **3,2 à 14,1** selon le réplicat (f6 ci-dessous).
C'est un nombre aléatoire.

### 12.2 Combien de bits ? (`f4_codage.py`)

Toutes les voies du dossier réduisent un tirage à un nombre. C'est jeter 61
bits pour n'en garder que trois. f3 lui-même ne regarde que le top-20 de
chaque tête.

Ici on ne réduit rien. Sous H₀, le tirage est uniforme sur les
C(80, 20) = 3,54·10¹⁸ sous-ensembles : il coûte **61,6165 bits**, et pas un
de moins. Un modèle qui, avant de voir le tirage, propose une loi *Q* sur ces
mêmes sous-ensembles reçoit `e_t = Q(D_t)·C(80,20)`, et sous H₀

    E[e_t | passé] = Σ_S (1/C) · Q(S) · C = 1   exactement.

La loi *Q* est une **Bernoulli conditionnelle** : 80 poids w, et
`Q(S) = Π_{i∈S} w_i / e_20(w)`, où le polynôme symétrique élémentaire e₂₀ se
calcule par récurrence en 80 × 21 produits — vectorisée sur tous les modèles
et tous les tirages d'un bloc.

Trois conséquences que le dossier n'avait pas :

1. **Aucune correction de multiplicité.** La moyenne d'e-valeurs est une
   e-valeur : 174 paris se lisent tels quels, là où le registre impose un
   seuil de Holm à 1,51·10⁻⁵ à toute statistique classique.
2. **Valide à tout instant** (Ville) : la courbe s'inspecte en continu sans
   dépenser d'alpha.
3. **La réponse est en bits**, donc en argent — (1/T)·log₂ E est le taux de
   croissance de Kelly, et zéro bit signifie aucune information exploitable,
   quelle que soit la mise.

La construction a été vérifiée avant d'être appliquée : sur 200 000 tirages
uniformes et des poids arbitraires, la moyenne de `e_t` vaut 1 à +0,73 σ,
−0,33 σ et +1,44 σ pour θ = +0,05, +0,20 et −0,20. Un e-processus faux monte
tout seul et invente un signal ; celui-ci ne bouge pas.

Les modèles : les 26 têtes de l'app, leur mélange AdaHedge, l'appartenance au
tirage précédent et l'écho du bonus, chacun incliné par θ ∈ {±0,02 ; ±0,05 ;
±0,10}. Sur les 70 560 tirages :

| | valeur |
|---|---|
| sup_t E du mélange | **10^+0,066** (au pas 6 sur 70 547) |
| seuil de Ville à α = 0,05 | 10^+1,301 |
| **taux de Kelly** | **−3,33·10⁻³ bit/tirage** |
| coût d'un tirage sous H₀ | 61,6165 bits |

Les 174 paris réunis extraient une information **négative** sur le tirage
suivant. Détail cohérent : le meilleur des 174 est `bonus@−0,02` — l'écho du
bonus incliné exactement dans la direction que `d7` avait trouvée. C'est le
pari qui perd le moins (10^−68,4 contre 10^−84 pour les pires têtes). Il perd
quand même.

**Et f4 s'applique à lui-même ce qu'il reproche à l'app.** Écrit ainsi, c'est
un e-processus cumulé depuis le premier tirage — exactement la construction
que §12.5 démontre aveugle à un défaut tardif. Conclure « rien » avec cet
outil aurait porté la faiblesse que le même dossier reproche à l'ancien
e-processus de l'app. Les 174 paris sont donc tenus une seconde fois,
relancés à chaque tirage par la récurrence de Shiryaev-Roberts, et le mélange
des **348** se lit toujours sans correction :

| | valeur |
|---|---|
| **sup_t E des 348 — statistique pré-enregistrée** | **10^+0,962 = 9,16** (au pas 2 679) |
| p de Ville (≤ 1/sup) | **0,109** |
| seuil de Ville à α = 0,05 | 10^+1,301 = 20 |
| seuil du registre (Holm sur m = 3 310) | 1,51·10⁻⁵ |

Un chiffre descriptif, à ne pas lire comme un résultat : les paris relancés
*seuls* culminent à 10^+1,262 = 18,3, juste sous le seuil. Ce n'est pas la
statistique pré-enregistrée, et la choisir après l'avoir vue serait
précisément la malédiction du vainqueur que ce labo refuse. Le mélange des
348 est la seule lecture valide, et il donne 9,16.

**La correction se paie en puissance retrouvée, et c'est mesuré.** À
T = 20 000, sur la contamination momentum :

| ε | avance réelle | sup_t log₁₀ E (348) | E ≥ 20 ? |
|---|---|---|---|
| 0 | +0,024 hits | +0,374 | non |
| 0,02 | +0,017 hits | +0,568 | non |
| 0,05 | **+0,044 hits** | **+1,459** | **oui** |
| 0,10 | +0,120 hits | +19,464 | oui |

La version cumulée seule ne voyait rien à ε = 0,05 et ne se déclenchait qu'à
ε = 0,10. Le mélange de redémarrages descend le seuil de détection à
**+0,044 hits par tirage** — le même ordre de grandeur que f3 (+0,043), par
un chemin entièrement différent.

**Un plancher pris pour une mesure, et corrigé.** La première version de cette
section passait `bonus = None` aux archives simulées. Le champ du bonus
devient alors constant, son z-score vaut zéro, et les 6 modèles de cette
famille valent exactement 1 à chaque pas : le mélange ne peut plus descendre
sous 6/174, soit log₁₀ = −1,4622. Les trois « −1,462 » identiques que j'avais
lus comme trois mesures étaient ce plancher. Les archives simulées reçoivent
désormais un bonus uniforme.

### 12.3 Tous les décalages, toutes les fréquences, toutes les paires (`f5_paires.py`)

Le dossier avait testé les décalages 1 à 30 (`d2`), le recouvrement
conditionnel (`c1`), les triplets (`d1`) : quelques décalages, choisis à la
main. Or l'archive contient **2 489 344 020 paires** de tirages et le
processus a **35 280 fréquences**. Les regarder toutes n'était pas une
question de volonté mais d'algorithme.

Le recouvrement au décalage *d* s'écrit

    Σ_t |D_t ∩ D_{t+d}| = Σ_{n=1}^{80} Σ_t x_n[t] · x_n[t+d]

c'est-à-dire la somme des **autocorrélations** des 80 séries binaires
d'appartenance. Une FFT par numéro donne les 69 560 décalages en **3,5
secondes**, contre 2,5 milliards de comparaisons en force brute. Le null
aussi — ce qui rend possible une loi du maximum sur 300 archives complètes.

Le null lui-même a été vérifié avant usage : sous H₀ les paires (t, t+d) et
(t+d, t+2d) sont **non corrélées** — le tirage du milieu est intégré des deux
côtés à la même espérance 5 —, donc la variance de la moyenne vaut exactement
2,8481/(T−d), sans terme croisé. Mesuré sur 200 décalages : écart-type des z
= 1,0051.

| | observé | null | z | p |
|---|---|---|---|---|
| **f5-A** max sur 69 560 décalages | 4,157 | 4,473 ± 0,269 | −1,17 | 0,249 |
| **f5-B** max sur 35 280 fréquences | 1,513 | 1,534 ± 0,043 | −0,48 | 0,621 |
| **f5-C** max sur 2 489 344 020 paires | 16/20 | λ(≥16) = 1,691 | | 0,816 |

Les trois maxima sont **en dessous** de leur null. Et 168 décalages dépassent
3 σ là où H₀ en prédit 188 ; 3 dépassent 4 σ pour 4,4 attendus. Le décalage 1
— la voie `c1` — sort à z = +0,30 sans la moindre sélection.

f5-C est le test de réutilisation de graine (le bug Corriveau du Keno de
Pennsylvanie, 1994) mené à l'échelle de l'archive entière, au lieu des 480
derniers tirages que l'app surveille. L'histogramme complet suit
l'hypergéométrique classe par classe jusqu'à la queue rare : 2 paires
observées à 16 pour 1,664 attendues, 0 à 17 pour 0,027.

**Une limite mesurée plutôt que supposée.** f5-B est **faiblement puissant**
contre la contamination testée : une raie de période 512 tirages n'est pas
détectée à 0/3, même à amplitude 0,010. Le périodogramme couvre toutes les
fréquences, pas toutes les amplitudes. f5-A détecte +0,037 hits à un décalage
donné (2/2) mais pas +0,026.

### 12.4 Réel, permuté, simulé — le triangle qui isole la cause (`f6_permute.py`)

Le premier réplicat du null de f3 donnait 9,97 têtes effectives contre 6,80
observées, ce qui ressemblait à un écart. Un null seul ne peut pas dire d'où
viendrait un tel écart. Trois sommets le peuvent :

- **RÉEL** — l'archive telle quelle ;
- **PERMUTÉ** — les *mêmes* tirages, ordre rebattu : détruit le temps,
  préserve exactement le multi-ensemble ;
- **SIMULÉ** — des tirages SRS uniformes indépendants.

Réel ≠ permuté signifie structure temporelle ; permuté ≠ simulé signifie que
la loi des tirages s'écarte de l'uniforme ; les trois égaux signifient qu'il
n'y a rien.

| statistique | RÉEL | PERMUTÉ (8) | SIMULÉ (8) |
|---|---|---|---|
| têtes effectives | 6,80 | 7,43 ± 3,79 | 6,84 ± 3,32 |
| max_h z_h | +1,88 | +1,86 ± 0,64 | +2,11 ± 1,02 |
| dispersion des hits | 417,8 | 426,8 ± 88,6 | 444,0 ± 150,2 |
| z de l'ensemble | −0,67 | −0,10 ± 0,90 | +0,46 ± 1,55 |

Réel contre permuté : z = −0,17. Réel contre simulé : z = −0,01. Permuté
contre simulé : t = +0,33. Les trois sommets coïncident. Le 9,97 était du
bruit.

Mesure au passage : deux têtes différentes partagent **5,92 numéros sur 20**
dans leur top-20, à peine au-dessus des 5,00 que partagent deux ensembles
sans aucun rapport. L'essaim n'est pas 26 variantes d'une même idée.

### 12.5 Ce que l'anytime-validité coûte (`f2_eprocessus.py`)

Le résultat le plus utile de cette série est négatif, et il va contre sa
propre méthode.

Un portefeuille de quatre e-processus — recouvrement lag-1, écho du bonus,
somme marginale, dispersion du recouvrement — se lit sans correction de
multiplicité et à tout instant d'arrêt. Sur les vrais tirages : max_t E_t =
**4,99**, atteint au pas 234, puis retour à zéro ; p de Ville = 0,20. La
famille `overlap_shape`, celle de la voie `d3` qui sortait à z = +3,47 par
lots, culmine à 19,1 **au pas 234 sur 70 559** avant de s'effondrer. Un vrai
biais fait monter un e-processus de façon monotone.

Mais mesurée sur les contaminations transitoires de `a3` :

| fenêtre corrompue | biais | portefeuille | balayage par lots `a3` |
|---|---|---|---|
| 200 tirages | +40 % | 0,05 | **0,58** |
| 500 tirages | +20 % | 0,00 | **0,28** |
| 2 000 tirages | +20 % | 0,00 | **1,00** |

Le diagnostic décisif : le **même** défaut (L = 500, j = 7), placé tôt
(t ∈ [1, 5 000]) → puissance **1,00** ; placé tard (t ∈ [50 000, N−L]) →
**0,00**. La cause est arithmétique, pas un manque de sensibilité. Un pari
cumulé depuis le premier tirage vaut exp(Σ log f), et **une somme ne dépend
pas de l'ordre** : sa valeur finale ignore *quand* le défaut s'est produit.
Ce qui change est son maximum courant — le seul chiffre que Ville autorise à
lire —, et un défaut tardif arrive sur une richesse déjà effondrée par la
dérive négative.

L'anytime-validité et l'absence de correction se paient donc en puissance
contre les défauts transitoires. Le remède porte un nom : le **mélange sur
les instants de redémarrage**.

### 12.6 Ce que ces expériences ont changé dans l'app

Trois correctifs, tous démontrés plutôt qu'argumentés.

**1. L'écart affiché se mesure contre la loi exacte.** « ÉCART AU HASARD —
+x.xx σ » divisait par un écart-type **estimé sur 60 tirages**. Ce n'est pas
une quantité à estimer : c'est la constante 1,687632 de f3. L'estimer sur 60
points ajoutait σ/√(2·59) ≈ 9 % de bruit au dénominateur — le chiffre affiché
était un t de Student à 59 degrés présenté comme un σ. Le test recalcule
l'écart-type **à partir de la loi**, terme à terme, sans réutiliser la formule
fermée du code : les deux chemins tombent sur 1,687631851389.

**2. La surveillance cesse d'être aveugle à un biais apparu tard.** L'app
affichait une e-valeur avec la phrase « sous ce seuil, aucune anomalie ».
f2 a montré que c'était faux pour un défaut tardif. La récurrence de
Shiryaev-Roberts

    R_t = (1 + R_{t−1}) · f_t = Σ_{k≤t} Π_{s=k..t} f_s

est la somme des paris démarrés à chaque instant : `R_t/t` est la moyenne de
*t* e-processus, donc une e-valeur — en une ligne, O(1) de temps comme de
mémoire. L'e-valeur affichée devient la moyenne de **32 paris** : deux
familles dont la loi sous H₀ est exacte (recouvrement du top-20,
hypergéométrique ; écho du bonus, Bernoulli 0,25), huit tailles d'effet,
chacun tenu depuis le début **et** relancé à chaque tirage.

Le test rejoue le mécanisme, avec son témoin positif — sans lui il ne
distinguerait pas « aveugle à un défaut tardif » de « cassé » :

| | valeur |
|---|---|
| valeur finale du pari cumulé, tôt contre tard | 7,056·10⁻⁹⁰ = 7,056·10⁻⁹⁰ |
| défaut **tardif** : sup du pari cumulé | **7,748** — jamais 20 |
| défaut **tardif** : redémarrages | 3,256·10⁴⁶ |
| témoin, défaut **tôt** : sup du pari cumulé | 1,703·10⁵⁰ |
| témoin, défaut **tôt** : redémarrages | 1,129·10⁴⁸ |

**3. f4 s'applique à lui-même ce qu'il reproche à l'app** (§12.2) : les 174
paris sont désormais tenus deux fois, et le seuil de détection descend de
+0,120 à **+0,044 hits par tirage**. Le remède que f2 nomme est donc mesuré,
pas seulement recommandé — ce qui est la seule raison de le câbler dans l'app.

### 12.7 Où en est le registre

Ces expériences ajoutent 18 entrées. Le registre compte **110 tests
consignés**, m = 3 310 en comptant les familles dont seul l'extrême est
enregistré, seuil de Holm **1,511·10⁻⁵**. Le plus petit p du dossier entier
reste **2,0·10⁻⁴** (`audit.paires`) ; le plus petit p de cette série est
**0,109** (`f4.restart`).

**0 significatif.**

## 13. Trois thèses qui ferment le dossier par le haut (`g1_theses.py`)

Vingt-neuf voies ont cherché un écart. g1 pose la question inverse : que
peut-on **prouver** sur la meilleure prédiction possible ?

### 13.1 La distribution du prédicteur, pas sa moyenne

f3 a testé l'*espérance* des hits du prédicteur déployé. Mais un prédicteur
qui exploiterait une structure pourrait avoir la bonne moyenne et la
mauvaise **loi** — des épaules plus lourdes, une queue déplacée, plus de
très bons tirages compensés par plus de très mauvais. Personne n'avait
regardé l'histogramme complet.

Le test a un luxe qu'aucune autre voie n'a : son null est **exact**. Sous
H₀, conditionnellement au passé, le recouvrement du top-k est
hypergéométrique *quel que soit le contenu du top-k* — la suite des 70 547
recouvrements est donc exactement multinomiale(T, pmf), sans le moindre
rejeu d'archives.

| | χ² | ddl | null multinomial | p |
|---|---|---|---|---|
| top-20 de l'ensemble | 10,57 | 11 | 11,01 ± 4,74 | **0,921** |
| top-10 (la grille maximale) | 2,58 | 8 | 7,96 ± 3,95 | **0,141** |

L'histogramme suit l'hypergéométrique classe par classe (pire classe :
+2,41 σ sur 12, exactement ce que 12 classes donnent sous H₀). Puissance :
la contamination momentum est vue à ε = 0,10 (2/2) et à la frontière à
ε = 0,05 (1/2), sur T = 20 000.

Le top-10 à p = 0,141 mérite sa phrase : c'est un χ² *inférieur* à son
attente (2,58 pour 8 ddl) — l'histogramme colle *mieux* que la moyenne des
tirages multinomiaux, pas moins bien. La direction de l'écart est celle de
la conformité, pas du signal.

### 13.2 Ce que l'archive peut réfuter — et le prix d'aller plus loin

**Zéro tirage exactement répété sur 70 560** (attendu sous H₀ : 7·10⁻¹⁰).
Un générateur qui aurait cyclé dans l'archive aurait répété des tirages à
l'identique ; la période dépasse donc 70 559 pas, soit un état de plus de
16,1 bits par pas consommé. La borne est **faible, et c'est la thèse** :
l'archive ne peut réfuter que les générateurs à état minuscule. Tout état
modéré — 64 bits et plus — est hors de portée de *n'importe quelle* analyse
de 70 560 sorties, celles de ce labo comprises. Le budget total
d'information de l'archive est de 4,35 Mbit ; un état cryptographique n'y
laisse, par construction, rien d'exploitable.

Et le prix de la première découverte possible est chiffré : porter le
résidu V3 (z = −2,58, le plus cohérent du dossier) au seuil du registre
(1,51·10⁻⁵, z = 4,33) demanderait **198 491 tirages — 627 jours de tirages
nouveaux** à 204 par jour. En supposant l'effet réel *et stationnaire* ;
sinon ce temps n'achète rien.

### 13.3 Le théorème de l'assurance gratuite

Sous H₀, les 80 numéros sont échangeables : pour toute grille de k numéros
choisie sans voir le tirage — si adaptative soit-elle —, la **loi
complète** de ses hits est hypergéométrique(80, 20, k). Pas seulement
l'espérance : chaque probabilité de chaque rang de gain, donc la
distribution des gains sous n'importe quel barème à cotes fixes.

Conséquence jamais énoncée : suivre l'essaim ne coûte **rien** — en
distribution — par rapport à des numéros au hasard, et capterait un biais
des familles bornées par c0/c1 s'il en apparaissait un (f3 : détection à
+0,043 hit dès T = 20 000). La politique de l'app —

    essaim (biais éventuels) + paquet étalé (P(pleine) rang par rang)
    + seuil de jackpot (quand jouer) + surveillance relancée (alerte)

— est donc **minimax** : perte exactement nulle sous H₀, gain maximal
réalisable sous les alternatives bornées. « La meilleure prédiction
possible » n'est pas un choix de numéros ; c'est cette politique, et §13.1
vient d'en tester la prémisse sur les 70 547 pas du déployé.

### 13.4 Une boucle infinie de ma fabrication, et ce qu'elle enseigne

La première version de `hyper_pmf(k)` divisait par C(80, 20) quel que soit
k — juste pour k = 20, faux d'un facteur 2·10⁵ pour k = 10, et le
regroupement de classes cherchait alors sans fin un attendu ≥ 8 dans une
« loi » qui sommait à 4,7·10⁻⁶ : 43 minutes à 100 % de CPU. Ma vérification
indépendante d'avant lancement n'avait couvert que k = 20 — exactement
l'angle mort. Deux assertions transforment désormais ce genre d'erreur en
échec immédiat, et la formule est re-vérifiée aux trois tailles (somme 1,
espérance k/4).

### 13.5 Registre final

**113 tests consignés, m = 3 313, seuil de Holm 1,509·10⁻⁵. Zéro
significatif.** Le plus petit p du dossier reste 2,0·10⁻⁴ (`audit.paires`).

## 14. La théorie, développée puis vérifiée (`h1_theoremes.py`, `THEORIE.md`)

Quatre théorèmes, chacun vérifié par calcul exact ou simulation fidèle
avant d'être énoncé — le détail complet est dans `THEORIE.md` :

- **A (monotonie de la loi jointe).** P(deux grilles ≥ t) croît avec leurs
  numéros partagés — 0 violation sur tout le domaine de l'app, formule
  contre-vérifiée par Monte-Carlo brut. Corollaire : l'étalement maximise
  P(au moins une ≥ t) à tout rang.
- **B (e2 tranché).** Le « l'étalement ne domine pas aux rangs 9-10 » de e2
  était un artefact de comptage Monte-Carlo (~85 et ~5 événements). Bornes
  de Bonferroni exactes et inclusion-exclusion complète au rang plein :
  **dominance prouvée 12/12 aux trois rangs**, rapport 1,0269 au rang 10.
- **C (minimax quantifié).** La franchise de l'assurance gratuite est
  bornée par 2·√(T ln N)·20/T = 0,272 hit/tirage ; la franchise réelle
  mesurée par f3 est 0,016 — six pour cent de la borne.
- **D (la faille du moniteur — trouvée, mesurée, corrigée).** La relance
  R_t/t que f2 m'avait fait câbler est une e-valeur à chaque instant fixé
  mais PAS uniformément dans le temps : R_t est une sous-martingale, Ville
  ne couvre pas son supremum. Mesuré : **12 % de fausses alertes pour 5 %
  promis**. Correctif câblé : poids a priori w_k = 1/(k(k+1)) et trésorerie
  des paris à venir — N_t est une vraie martingale, fausses alertes
  mesurées **0,042 ± 0,013** sur 240 archives. Le prix, documenté : 2·ln k
  nats de budget en plus pour un défaut commençant au pas k.

La leçon de D vaut d'être dite : c'est la *contradiction* entre une
prédiction théorique et une simulation (0,77 mesuré là où la frontière
disait « invisible ») qui a mis la faille au jour. Une théorie qu'on ne
confronte pas à une simulation fidèle ne protège de rien.

**Registre : inchangé à 113 entrées — h1 ne teste pas l'archive, il prouve
et corrige.** Zéro significatif.
