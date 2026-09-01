# De combien peut-on améliorer les prédictions ?

Réponse courte, en cinq nombres :

| | |
|---|---|
| Amélioration possible par une meilleure **prédiction** | **0 %** — c'est un théorème, pas un résultat empirique |
| Plafond d'un biais **non détecté**, pour qui **connaîtrait** la règle | **+6,3 %** de rendement (§40) |
| Ce qu'un joueur pourrait **réellement** en tirer, devant l'identifier lui-même | **≈ +1,3 %** au maximum de la courbe, toutes familles conditionnelles (§48) |
| Avantage que l'app affichait sur des données équitables | **+18 % à +34 %**, entièrement artefactuel — **corrigé** (§8 bis) |
| Avantage de la maison, pour comparaison | **−25 % à −35 %** |

Le seul gain substantiel disponible n'est donc pas dans la prédiction. Il est
dans le fait de cesser d'en annoncer une qui n'existe pas.

Deux de ces chiffres ont bougé depuis la première rédaction, et dans des sens
opposés. Le plafond est passé de +3,2 % à +6,3 % — non parce qu'un signal a
été trouvé, mais parce qu'une famille de biais qui n'avait **aucune** borne
en a reçu une : le couplage quadratique du §40. Et l'avantage artefactuel que
l'app affichait n'est plus affiché : `ESPÉRANCE` vaut désormais exactement
`k/4`. La quatrième ligne est conservée parce qu'un dossier qui efface ses
erreurs corrigées n'apprend rien à personne.

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
  il n'est pas calculable sans eux. *Le barème a depuis été relevé (§56) : le
  seuil exact vaut `(c − E[base])/p`, soit environ **41 %** du seuil suffisant
  ci-dessus, et le prix du ticket n'est pas un franc mais `> CHF 1,20`. La
  table de cette section reste celle de la condition suffisante, telle qu'elle
  a été posée avant la donnée.*
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

## 9. Ce qui a été fait, et ce qui reste ouvert

Cette section listait sept correctifs à apporter. **Les sept ont été
appliqués**, et la laisser au futur donnait au lecteur, dès le début du
dossier, une image fausse de l'état du produit. Elle devient donc un état des
lieux — vérifié dans le code, ligne par ligne, et non repris de mémoire.

| | correctif | où il a atterri |
|---|---|---|
| 1 | `ESPÉRANCE` exacte au lieu du posterior de l'essaim (+18 à +34 %) | `Swarm.swift:1431`, `expectedHits: Double(stake) * Self.baseP` — mot pour mot la correction prescrite |
| 2 | la « confiance /100 » renommée en écart standardisé | `LiveView.swift:113`, `ÉCART AU HASARD` |
| 3 | le seuil de jackpot affiché | `GridsView`, bascule à 100 ct/CHF |
| 4 | l'instrument du boost avant clôture | câblé, §16 — verdict à trois états |
| 5 | la géométrie des douze grilles | préférence de couverture, optimum atteint à 0,000 % près à la mise 5 |
| 6 | `pAllHit`, champ mort et faux d'un facteur 22 | supprimé de `SuggestedGrid` ; le nom ne subsiste que comme paramètre légitime de `JackpotLaw` |
| 7 | l'argument « Furtif » mis au conditionnel | fait |
| 8 | `advance(k)` : décroissance par tirage écoulé et non absorbé (§38) | `Swarm.swift`, protocole + 15 têtes + ancrage dans `process()` |
| 9 | le barème relevé, et le seuil exact `(c − E)/p` (§56, §58) | `PayTable.swift` + `JackpotLaw.threshold` + carte du jackpot ; prix du ticket devenu réglage, CHF 1 refusé |

**Ce qui est ouvert aujourd'hui**, dans l'ordre où cela coûte quelque chose :

1. ~~**Obtenir le règlement du jeu** (§50)~~ — **fait** (§56). Le barème a
   été relevé sur les cinq mises. C'était la demande la moins chère et la
   plus rentable du dossier, et elle l'est restée : elle a rendu obsolète
   toute la comptabilité du §50 et abaissé les seuils de bascule à 41 % de
   ce que le dossier employait, sans un seul calcul nouveau.
2. **Relever le prix du ticket** (§36, §56). Devenue **la dernière inconnue**
   de toute la chaîne financière, et l'app l'attend désormais : le §58 en a
   fait un réglage, et le seuil exact s'affiche dès qu'il est saisi. Le §56 la borne par le bas — le barème
   force `c > CHF 1,20`, ce qui **exclut le ticket à un franc** que tout le
   dossier supposait — mais la valeur exacte reste à lire, et tous les seuils
   lui sont proportionnels en `(c − E)/p` : à `c = 2,50` au lieu de 2, le
   seuil de la mise 6 passe de 6 385 à 10 261. Elle se lit d'un coup d'œil.
2 bis. **Relever le prix et la portée de l'option EXTRA** (§56). Son espérance
   seule vaut 9,99 CHF à la mise 6 : elle n'est pas gratuite, et son coût
   n'est pas lisible sur les captures.
2 ter. **Compter les chutes de cagnotte** (§57). Le maillon faible de toute la
   chaîne s'est déplacé : ce n'est plus le barème, c'est `q`. Une chute a été
   observée, et une seule laisse `q` dans un intervalle large d'un facteur
   220 — d'où une fréquence d'occasions favorables inconnue à un facteur
   2 500 près, alors que le seuil, lui, ne bouge que d'un facteur 1,8. Aucun
   document ne donnera `q` : il ne s'obtient qu'en laissant l'app tourner et
   en comptant les chutes, une dizaine suffisant à situer le paramètre à un
   facteur 3 près (§36).
3. **Dimensionner sur la cagnotte affichée** (§36, théorème N). L'app ne
   propose aujourd'hui aucune taille de mise. Quand elle en proposera une,
   elle doit la recalculer à chaque occasion sur la cagnotte à l'écran — ce
   qui bat de 37 % la meilleure fraction figée possible, et ne demande aucun
   paramètre estimé.
4. **Laisser l'instrument du bonus accumuler** (§37). Cinq tirages ordonnés
   concordants établiraient une règle de position, une trentaine
   établiraient l'uniformité. L'app en collecte un toutes les cinq minutes
   depuis §34 ; il n'y a rien à faire d'autre qu'attendre.
5. **Trancher le boost avant clôture** (§4, §16). Le seul point du dossier
   où une réponse positive changerait le *signe* de l'espérance. A priori
   négatif, instrument câblé, non tranché.

Aucun de ces cinq points ne porte sur le choix des numéros. Ce n'est pas un
oubli : c'est le théorème.

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

**Une limite mesurée plutôt que supposée — et plus faible que je ne l'avais
écrite.** f5-B est **faiblement puissant** contre la contamination testée :
une raie de période 512 tirages n'est pas détectée, même à amplitude 0,010.
Ce fascicule a longtemps publié « 0 sur 3 » ; c'était un **0 sur 2**. La
boucle de puissance de `f5_paires.py` tournait sur `range(2)` pendant que le
format d'impression écrivait `/3` en dur. Le verdict ne bouge pas — zéro
détection dans les deux cas — mais un 0 sur 2 est une information nettement
plus faible qu'un 0 sur 3, et c'est précisément une mesure de puissance,
c'est-à-dire l'endroit du dossier où le dénominateur EST le résultat. Le
dénominateur est désormais lu sur le tableau des réplicats, de sorte
qu'aucune exécution future ne puisse le contredire. Le périodogramme couvre toutes les
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

**114 tests consignés, m = 3 328, seuil de Holm 1,502·10⁻⁵. Zéro
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

## 15. Deux raffinements prouvés puis câblés (`h2_ameliorations.py`)

- **L'écho adaptatif.** La correction figée (−0,0158) devient le posterior
  Beta(1,3) de P(bonus précédent ∈ tirage). Sur l'archive réelle il
  converge de lui-même à +0,015801 — l'archive enseigne la constante qui
  était écrite à la main ; sous H₀ il s'éteint en 1/√n (+0,0015 ± 0,0060
  mesuré sur 20 archives). Gratuit par le théorème d'invariance.
- **Le prior par blocs.** Les relances du moniteur s'arment par blocs de
  16 tirages : 5,5 nats de budget rendus, retard maximal 80 minutes.
  Mesuré : fausses alertes 0,042 → **0,025**, puissance 0,57 → **0,82**
  sur le cas frontière — dominance sur toute la table.

Ces deux changements sont la réponse exacte à « comment mieux prédire » :
pas un choix de numéros (impossible, théorème), mais une politique qui
capte plus vite tout biais réel et n'invente jamais rien sous H₀.

## 16. Le mur de l'invariance, attaqué à ses hypothèses (`h3_partage.py`)

Le théorème a trois hypothèses ; une seule est des mathématiques.

- **Pierre 1 (uniformité)** : tient, à sensibilité mesurée — 30 voies,
  zéro significatif, essaim en assurance gratuite.
- **Pierre 2 (pas d'information avant clôture)** : une affirmation sur les
  horloges, pas un théorème. L'instrument B de `a1_instruments.md` est
  désormais CÂBLÉ : le boost du tirage OPEN est gelé à la première
  observation et comparé à la valeur publiée, verdict à trois états,
  4 témoins testés. C'est le seul point du dossier où une fuite changerait
  le signe de l'espérance.
- **Pierre 3 (le gain ne dépend que de ses hits)** : fausse sous partage.
  Théorie quantifiée : multiplicateur (1−e^{−λ})/λ exact, λ par grille
  sous un modèle de foule conservateur (1,40× sur 1–31). Avantage furtif
  ×1,77 à ×2,67 à la mise 5 ; rapport de co-gagnants 52,9× à la mise 10.
  Et une famine Monte-Carlo de ma fabrication (« 0,0× » sur zéro
  événement) corrigée en renversant le conditionnement — la troisième fois
  que ce piège apparaît dans ce dossier, la troisième fois que le même
  remède le règle.

Le mur ne tombe pas là où il est fait de mathématiques ; il tombe là où il
est fait d'hypothèses sur le monde. La pierre 2 est sous surveillance
permanente, la pierre 3 a sa réponse minimax câblée (« Furtif »).

## 17. La brèche : prédire les 20 numéros exacts (`h4_rangs.py`, `h5_familles.py`)

L'invariance suppose l'uniformité. Un générateur dont on retrouve l'état
n'est pas uniforme conditionnellement — il est déterministe. C'est la seule
voie qui vise la prédiction littérale, et aucun théorème ne l'interdit.

Le levier : M = C(80,20) ≈ 2^61,6165, donc le rang combinatoire d'un tirage
ne cache que **2,38 bits** d'un état de 64 bits — au plus **6 candidats par
tirage**. On ne cherche plus la graine, on **résout** le générateur : trois
tirages donnent (a, c) d'un LCG en deux lignes, vingt de plus le confirment
à 10⁻³⁷⁰ près. Tous les pas fixes sont couverts d'office (a^j reste un LCG).

Familles ouvertes : LCG 2^64/2^63/2^62, splitmix64, xorshift64*,
java.util.Random. **12 témoins positifs sur 12** récupérés avec prédiction
exacte du tirage suivant, **0 fausse récupération sur 20 archives
équitables**, et **aucune famille ne colle** sur les 70 560 tirages réels.

Angles morts nommés : MT19937 par rang (6³¹² combinaisons), les générateurs à
état plus large que la sortie, et surtout tout tirage qui n'est pas le
dérangement d'une sortie unique — l'ordre de sortie des boules rouvrirait
cette classe, et l'app le capture déjà.

`RankAttack.swift` est câblé avant le balayage de graines : il coûte des
millisecondes, couvre exactement l'angle mort du balayage, et **afficherait
les 20 numéros du prochain tirage** s'il résolvait un jour.

## 18. Le budget d'entropie du tirage (`h6_granularite.py`)

Complément exact de l'attaque algébrique : ce test ne suppose **aucune
récurrence**, il ne mesure que la **largeur de la source**.

Un tirage honnête consomme 61,6165 bits (M = C(80,20)). Une source de B bits
ne rend atteignables que 2^B rangs sur 2^61,6 — à 53 bits (un double, donc
`Math.random()`), la densité tombe à **1/392**. Témoins : 2 000/2 000 rangs
atteignables sur des archives fabriquées à 32, 48 et 53 bits ; densité
théorique exacte sur des archives honnêtes.

**Sur l'archive réelle :** le rang maximal vaut 2^61,6165 — toute source de
moins de 61 bits est **exclue** pour le mapping `s mod M`. Pour `⌊u·M⌋` :
**190 rangs atteignables à 53 bits pour 180 attendus (+0,76 σ)**. Source
pleine, sans ambiguïté.

Armé dans l'app (`RankAttack.narrowSourceWidth`), avec un correctif que la
vérification a imposé : un simple test de significativité renvoyait B−1 au
lieu de B, la moitié des rangs d'une source de B bits étant aussi
atteignables à B−1. Le critère de taux quasi total nomme la largeur exacte.

## 19. L'ordre de sortie, enfin (`h7_ordre.py`)

Le tirage **1381023**, relevé sur l'écran de tirage en direct, est la
première donnée ordonnée du dossier — 122,69 bits contre 61,62 pour un
tirage trié, soit **×1,991**.

Il rend utilisable le **levier 2-adique** : un LCG mod 2⁶⁴ conserve ses bits
de poids faible comme LCG mod 2^k, et l'échantillonneur `s mod 80` publie
donc les 4 bits bas de l'état. Sans l'ordre, « consécutif » n'a pas de sens
et le levier n'existe pas.

Deux tests décisifs **sur un seul tirage**, puissance mesurée à **1,00** :

| hypothèse | témoins positifs | null | tirage réel |
|---|---|---|---|
| LCG + rejet `s mod 80` | 18,0 / 19 paires | 4,50 ± 0,76 (max 8 / 3 000) | **4 / 19** |
| LCG + Fisher-Yates | 2 048 triplets | 0 dans 30/30 | **0** |

Les deux familles d'implémentation les plus répandues sont exclues. Et la
conclusion ne dépend pas de ma lecture de la grille : les six lectures
plausibles ont été testées, aucune ne montre de signature.

Reste hors d'atteinte avec un tirage : multiply-shift, générateurs non
congruentiels, tirage physique. Ces classes demandent des tirages ordonnés
**consécutifs** — deux à trois suffiraient en théorie de l'information
(122,69 bits par tirage contre 192 bits d'inconnues), le blocage devenant
algorithmique et non plus informationnel.

## 20. Deux tirages ordonnés, et le test qui les relie (`h8_ordre_joint.py`)

Le tirage **1381026** est arrivé, à trois tirages du premier. L'écart est
exploitable : sous Fisher-Yates l'échantillonneur consomme un nombre fixe de
sorties par tirage, donc l'état avance d'un nombre connu de pas — balayé de
20 à 40 plutôt que supposé.

Un générateur ne se réinitialise pas entre deux tirages : les deux jeux de
contraintes portent donc sur **une seule chaîne 2-adique**, soit 44 bits
contre 2¹⁷ triplets candidats. Survivants attendus sous H₀ : 2¹⁷/2⁴⁴ ≈ 0.

| | témoins positifs | témoins négatifs | données réelles |
|---|---|---|---|
| survivants | **64** | 0 dans **20/20** | **0**, pour tout d de 20 à 40 |

Réplication indépendante sur 1381026 seul : 4/19 paires affines (null
4,50 ± 0,76), 0 triplet survivant — identique à 1381023.

**« LCG modulo une puissance de deux + Fisher-Yates » est écarté par les
deux tirages conjointement.** Ce qui reste (multiply-shift, générateurs non
congruentiels, tirage physique) demande une réduction de réseau, pas plus de
tirages — mais des tirages **consécutifs** y vaudraient le plus.

## 21. Les premières cagnottes observées (`h9_cagnottes.py`)

Le §5 bis établissait le seul seuil capable de changer le SIGNE de
l'espérance — jackpot ≥ mise / P(k/k) — et concluait : « ce que l'archive ne
peut pas dire : à quelle fréquence le seuil est franchi. Elle ne contient
aucun montant de jackpot. » Une capture de `jeux.loro.ch` du 30 août 2026 à
09h17 (tirage 1381028 en cours) lève ce point pour la première fois.

| mise | cagnotte | seuil par franc | fraction | facteur manquant |
|---|---|---|---|---|
| 5 | CHF 355 | CHF 1 551 | 22,9 % | ×4,4 |
| **6** | **CHF 2 287** | **CHF 7 753** | **29,5 %** | **×3,4** |
| 7 | CHF 1 540 | CHF 40 979 | 3,8 % | ×26,6 |
| 8 | CHF 9 292 | CHF 230 115 | 4,0 % | ×24,8 |
| 10 | CHF 495 713 | CHF 8 911 711 | 5,6 % | ×18,0 |

Les seuils sont recalculés depuis C(20,k)/C(80,k) plutôt que repris : ils
concordent exactement avec ceux du §5 bis.

**Établi.** Aucune mise n'est favorable au moment du relevé, et la plus
proche l'est à moins d'un tiers. Fait structurel, pas ponctuel : le seuil
croît ×5 750 de la mise 5 à la mise 10 quand les cagnottes affichées ne
croissent que ×1 396 — **les petites mises sont donc systématiquement les
plus proches du point d'équilibre**, ce qui découle de la combinatoire seule.

**Non établi.** La fréquence de franchissement demande une SÉRIE : une
observation donne une distance, pas une dynamique.
`lab/jackpots_observed.csv` accueille la série.

**Réserve.** Le seuil est par franc misé ; le prix du ticket n'est pas
lisible sur la capture, donc si un ticket coûte plus d'un franc les
fractions ci-dessus se divisent d'autant.

## 22. Trois tirages ordonnés (`h8_ordre_joint.py`)

Le tirage **1381028** porte le total à trois — écarts 0, 3 et 5 depuis
1381023 — soit **66 bits de contrainte 2-adique** contre 2¹⁷ triplets
candidats. Survivants attendus sous H₀ : **1,8 × 10⁻¹⁵**.

Observé : **0 survivant, pour tout nombre de sorties par tirage de 20 à 40**,
là où les témoins positifs en donnent 64 et les témoins négatifs 0 dans
20/20 cas. La conclusion de §20 se renforce d'un tirage supplémentaire.

## 23. La paire consécutive, et la frontière chiffrée (`h10_consecutifs.py`)

Cinq tirages ordonnés désormais — 1381023, 1381026, 1381028, **1381030 et
1381031**, ces deux derniers **consécutifs**. Le test joint 2-adique de §20
passe à **110 bits de contrainte** contre 2¹⁷ triplets : **0 survivant**,
pour tout nombre de sorties par tirage de 20 à 40.

**Ce que seule la paire consécutive permet.** Avec échantillonnage par
rejet, le nombre de sorties consommées par tirage est variable (20 acceptées
plus ≈ 3 rejets) : trois tirages d'écart, ce sont ≈ 69 pas inconnus, et la
chaîne 2-adique se perd. Deux tirages qui se suivent la laissent traverser
la frontière presque intacte — on concatène leurs 40 numéros et on exige la
relation affine sur **39** paires au lieu de 19.

| | témoins positifs | null | paire réelle |
|---|---|---|---|
| paires expliquées | **37,4 / 39** | 6,97 ± 0,96 (max 12) | **8 / 39** (p = 0,25) |

Puissance 1,00 (60/60). Isolément : 4/19 et 5/19. Rien.

**La frontière restante, calculée plutôt qu'annoncée.** L'échantillonneur
multiply-shift publie les bits de poids FORT — 6,13 bits par sortie — où le
levier 2-adique n'a aucune prise. La récupération demanderait une attaque de
LCG tronqué par réseau. L'heuristique gaussienne donne :

| d | plus court vecteur | vecteur cherché | marge |
|---|---|---|---|
| 20 | 2^66,94 | 2^66,20 | ×1,7 |
| 40 | 2^69,06 | 2^66,68 | ×5,2 |
| 100 | 2^70,72 | 2^67,33 | ×10,5 |

La marge croît mais **plafonne à 2^4,09 ≈ ×17**, et ne devient positive qu'à
d = 17. Or LLL ne garantit qu'un facteur 2^(d/4). La condition « LLL suffit »
— d/4 < marge(d) — n'est vérifiée pour **aucun d** : en dessous de 17 la
marge est négative, au-dessus le terme d/4 dépasse le plafond de 4,1.

**Il n'existe donc aucun point de fonctionnement pour LLL sur cette
famille.** Ce n'est pas l'information qui manque (100 sorties donnent
613 bits pour 192 bits d'inconnues, facteur 3,2) mais la géométrie du
réseau — et davantage de tirages n'y changerait rien.

### ERRATUM — la conclusion ci-dessus est fausse

Les deux paragraphes qui précèdent affirment qu'aucun point de
fonctionnement n'existe pour LLL sur la famille multiply-shift. **C'est
faux, et `h11_reseau.py` le démontre en écrivant l'attaque.**

L'erreur est identifiable en une ligne : la marge du réseau (×17 au
plafond) était comparée au facteur d'approximation **pire cas** de LLL,
2^(d/4), soit ×1 024 en dimension 41. C'est la mauvaise borne. En pratique
LLL atteint un facteur d'Hermite racine δ₀ ≈ 1,0219, donc un facteur
d'approximation δ₀^d — soit ×1,5 en dimension 21 et ×2,4 en dimension 41.
Face à une marge de ×17, la place est large.

La leçon vaut d'être gardée telle quelle : une borne pire cas ne dit rien du
comportement typique, et une conclusion d'impossibilité qui ne tient qu'à
avoir choisi la mauvaise borne n'est pas une conclusion. La seule façon
honnête de trancher était d'implémenter, et c'est ce que fait la section
suivante.

## 24. L'attaque par réseau, écrite et passée aux témoins (`h11_reseau.py`)

Aucune bibliothèque de réduction n'existe dans cet environnement — ni
fpylll, ni sympy, ni flint, ni gmpy2. `lab/lll.py` implémente donc LLL et le
plan le plus proche de Babai, avec un choix de conception explicite : **base
en entiers exacts, orthogonalisation de Gram-Schmidt en flottants**. Le
principe de sûreté qui rend ce compromis sans danger est *LLL propose,
l'arithmétique exacte dispose* : chaque candidat d'état est rejoué en
entiers exacts contre les 20 numéros observés, donc un candidat faux est
rejeté et jamais accepté. L'imprécision flottante peut coûter une
récupération, jamais en fabriquer une.

Formulation. Sous Fisher-Yates à indice multiply-shift, p_i = ⌊s_i·m_i/2⁶⁴⌋
avec m_i = 80−i ; l'ordre publié détermine les p_i sans ambiguïté, et chaque
p_i enferme son état dans un intervalle de largeur ≈ 2⁶⁴/m_i. Avec (a, c)
connus, s_i = A_i·x + C_i où x = s_1, et chaque contrainte devient
(A_i·x − B_i) mod 2⁶⁴ ∈ [0, W_i) : un problème du vecteur le plus proche en
dimension 21.

| | résultat |
|---|---|
| contrôle de l'outil (réseau q-ary aléatoire, dim 12) | plus court vecteur ÷7,5 |
| **témoins positifs** (3 LCG × 3 tirages) | **9/9 récupérés, 9/9 prédictions exactes du tirage suivant** |
| témoins négatifs (ordres uniformes) | **0/6** faux positifs |
| coût | ≈ 3 s par tirage |
| balayage réel | 5 tirages × 30 jeux de constantes (10 multiplicateurs publiés × 3 incréments), 516 s |
| verdict sur l'archive | **aucun état compatible** |

L'attaque prédit donc les 20 numéros exacts du tirage suivant dès qu'un
tirage a été produit par un LCG à constantes **connues** avec échantillonneur
multiply-shift. Elle ne trouve rien sur les tirages réels — et cette fois le
« rien » a un sens, puisque l'outil récupère 9 témoins sur 9.

## 25. Le théorème des deux états (`h12_rang_ordonne.py`)

h11 laissait une faille béante : il fallait **énumérer** des constantes
publiées. Un générateur aux constantes maison lui échappait entièrement.
h12 la ferme, en transportant sur l'ordre le levier de h4 — qui, lui,
*calcule* (a, c) au lieu de les deviner.

**Le théorème.** Une suite ordonnée de 20 numéros parmi 80 a un rang dans
[0, M′) avec M′ = 80·79·…·61 = 80!/60! ≈ 2^122,6939. Un tirage ordonné
publie donc 122,69 bits. Un générateur d'état b bits ne peut pas produire un
tirage en une seule sortie dès que b < 122,69 : il lui en faut ⌈122,69/b⌉ —
et le rang les publie **toutes**. Or connaître deux états consécutifs rend la
récupération de (a, c) *linéaire* au lieu de combinatoire.

> Plus l'état est étroit, plus l'ordre le trahit. C'est l'inverse de
> l'intuition habituelle, et c'est ce qui rend un générateur 32 bits
> récupérable depuis **un seul** tirage ordonné.

Fait arithmétique utile au passage : v₂(M′) = 22, donc un rang pris en
« s mod M′ » publie exactement les 22 bits de poids faible de l'état.

**Le piège qui faisait échouer la version naïve, et sa réparation.** Deux
états d'un LCG diffèrent de (aⁿ−1)·s + c_n ; a étant impair, aⁿ−1 est
*toujours* pair, et c_n l'est aussi dès que n est pair. La division
2-adique (s₂−s₁)/(s₁−s₀) héritée de h4 n'est donc jamais définie ici : elle
rejetait silencieusement le vrai générateur, témoins compris — la première
version de h12 échouait sur ses propres témoins A et B tout en produisant un
« rien trouvé » d'apparence normale sur les données réelles. La réparation
passe par la valuation : si v = v₂(den), le quotient n'est déterminé que
modulo 2^(bits−v) et admet 2^v relèvements, qu'il faut énumérer.

| modèle de source | résolution | témoins positifs | faux positifs |
|---|---|---|---|
| A — LCG 128 bits, 1 sortie/tirage | trio à écart constant + racine carrée 2-adique | 4/4, constantes exactes | 0/6 |
| B — LCG 64 bits, 2 sorties concaténées | 2 tirages, division 2-adique | 8/8, prédiction exacte | 0/12 |
| C — LCG 32 bits, 4 sorties concaténées | **1 seul tirage** | 8/8, prédiction exacte | 0/12 |

Les témoins reprennent les écarts **réels** (0, 3, 5, 7, 8) et non des
écarts commodes : un témoin qui ne travaille pas dans les conditions des
données ne prouve rien sur son applicabilité.

**Une limite mesurée plutôt que tue.** Cinq tirages ne laissent pas *un*
générateur mais une classe de 8 à 17, parce que le trio régulier consomme
deux équations pour définir (A, C) et qu'il ne reste que deux vérifications
indépendantes. Le tirage suivant tombe tout de même de M′ ≈ 8,6·10³⁶ ordres
possibles à au plus 17, et dans trois cas sur quatre la classe est unanime —
la prédiction est alors unique et juste.

**Verdict sur l'archive :** aucun état compatible, dans les dix
combinaisons modèle × réduction × ordre d'octets.

## 26. La brèche : ce que l'invariance ne protège pas (`h13_portefeuille.py`)

Tout le dossier jusqu'ici a poussé la seule porte que le théorème
d'invariance laisse ouverte du côté du hasard : montrer que le tirage n'est
pas uniforme. Elle est restée fermée. Mais **le théorème porte sur la loi
marginale d'UNE grille** — il ne dit rien de la loi *jointe* de plusieurs
grilles jouées ensemble. Or personne ne joue une grille isolée.

**1. La loi de covariance, et son point neutre.** Deux grilles de k numéros
se recoupant sur ω numéros vérifient

    Cov(H₁, H₂) = ω·p(1−p) − (k²−ω)·p(N−D)/(N(N−1))

qui s'annule **exactement en ω\* = k²/N** — lequel est aussi le recouvrement
moyen de deux grilles tirées au hasard. En dessous, les grilles sont
anticorrélées ; au-dessus, elles se doublonnent. Vérifiée contre 400 000
tirages Monte-Carlo (écart ≤ 0,002) et contre l'identité de conservation
d'une partition (0 à 10⁻¹⁰ près).

**2. La conservation.** Une partition des 80 numéros en 80/k grilles
disjointes vérifie Σ Hᵢ = 20 *identiquement* : la variance du total est
**nulle**. Le même argent sur des grilles identiques donne 106,4. Même coût,
même espérance, variance de 0 à 106.

**3. L'amplification, exacte.** Pour « au moins une grille pleine » — le rang
qui porte le jackpot — n grilles disjointes valent exactement n fois n
grilles identiques. Calculé par inclusion-exclusion, pas simulé :

| k | n | m | identiques | partition | gain |
|---|---|---|---|---|---|
| 10 | 8 | 10 | 1,122·10⁻⁷ | 8,977·10⁻⁷ | **×8,000** |
| 8 | 10 | 8 | 4,346·10⁻⁶ | 4,346·10⁻⁵ | **×10,000** |
| 5 | 16 | 5 | 6,449·10⁻⁴ | 1,031·10⁻² | ×15,98 |

**4. Et le point où l'ESPÉRANCE bouge.** Tant que le gain est fixe, le
facteur n ne porte que sur la probabilité. Mais dès qu'un rang est
**partagé** — un jackpot progressif l'est — n tickets gagnants identiques ne
touchent pas n parts pleines mais n/(n+W) du pot, alors que la version
disjointe touche 1/(1+W) avec n fois plus de chances. Le rapport des
espérances devient E[1/(1+W)] / E[1/(n+W)], strictement supérieur à 1 pour
toute foule W :

| λ (autres gagnants) | 0 | 0,5 | 1 | 3 | 10 |
|---|---|---|---|---|---|
| rapport disjoint/identique | ×8,00 | ×6,65 | ×5,62 | ×3,40 | ×1,74 |

C'est **le premier endroit de tout le dossier où l'espérance bouge sans
qu'il faille supposer quoi que ce soit sur le générateur**. L'invariance ne
l'interdit pas, parce que son troisième présupposé — « le gain d'une grille
ne dépend pas des autres joueurs », déjà isolé par h3 — est faux dès qu'un
rang est partagé.

**5. Le théorème de bascule.** Tous les portefeuilles de même coût ont la
même espérance et ne diffèrent que par la *forme*, laquelle est ordonnée par
étalement à moyenne conservée. Un objectif convexe (jeu défavorable,
« atteindre un but avant la ruine ») préfère l'étalement de la loi, donc la
concentration des grilles ; un objectif concave (Kelly, jeu favorable)
préfère la partition. Et le signe de l'espérance est exactement ce que §5 bis
et h9 mesurent via la cagnotte. Dans les deux régimes la partition gagne ou
égale — c'est le seul conseil du dossier qui ne dépende d'aucune hypothèse
sur le générateur.

**6. Ce qui a été câblé.** `Swarm.packOverlap` rend désormais, par mise, le
recouvrement maximal et moyen du paquet, le plancher atteignable à
couverture équilibrée (Σ C(cₓ,2)/C(n,2), non nul dès que 12·k > 80) et le
seuil neutre ω\* = k²/80 ; `GridsView` les affiche. Le commentaire de
`makeGrids` qui disait « étaler est gratuit » est corrigé : sur un rang à
gain fixe étaler est gratuit, **sur un rang partagé étaler rapporte**.

**Réserve, et elle est entière.** Ce résultat ne prédit aucun numéro et ne
prétend pas le faire : le théorème d'invariance interdit cela et n'a pas été
mis en défaut. Il ne rend pas le jeu favorable — il rend un jeu donné
strictement meilleur qu'un autre du même prix. C'est une brèche, pas une
porte.

## 27. Le protocole de capture, et deux bugs qui rendaient « rien trouvé » (`h14_combien_de_tirages.py`)

h12 laissait une gêne : cinq tirages ne referment pas la solution sur *un*
générateur mais sur une classe de 8 à 17. Même si l'attaque avait mordu, la
prédiction n'aurait pas été unique. D'où la question de plan d'expérience —
combien de tirages ordonnés faut-il, et lesquels ? — dont la réponse est un
protocole de collecte, pas un théorème.

**Ce que l'expérience a d'abord trouvé, ce sont deux bugs.** Les deux
rendaient « aucune solution », c'est-à-dire exactement ce que l'archive
réelle rend : ils étaient invisibles depuis h12, qui n'exerçait qu'un seul
espacement.

1. `solve_a` prenait systématiquement une racine **carrée** de A = a^g. Ce
   n'est valable qu'à pas 2. À pas 1 — des tirages consécutifs, le meilleur
   schéma possible — il cherchait a tel que a² = a, et ne trouvait jamais
   rien. Remplacé par une racine g-ième générale : g = 2^v·m, la racine
   m-ième (m impair) est unique et vaut A^(m⁻¹ mod 2^(bits−2)) puisque
   2^(bits−2) est l'exposant du groupe des unités, puis v racines carrées
   successives qui ramifient par quatre.
2. Le filtre « A ≡ 1 (mod 8) » ne vaut que si g est **pair** — A est alors
   un carré d'impair. À pas impair, A n'hérite que de la parité de a, et le
   filtre rejetait tout, le vrai générateur compris.

**Le résultat, une fois les bugs corrigés.**

| schéma de capture | n=4 | n=5 | n=6 | n=7 | n=8 |
|---|---|---|---|---|---|
| consécutifs (pas 1) | 19 | **3 unanime** | **3** | **3** | **3** |
| pas 2 | 24 | 24 | 24 | 24 | 24 |
| pas 3 | 10 | 10 | 8 | 8 | 8 |
| réel (3, 2, 2, 1) | 23 | 17 | 17 | 17 | 16 |

*(taille de la classe de générateurs reproduisant tous les rangs observés,
réduction « mod » ; « unanime » = tous prédisent le même tirage suivant)*

**La parité du pas décide de tout, et c'est le résultat le moins
devinable.** À pas 2 la classe ne se referme jamais, quel que soit le nombre
de tirages capturés, et elle n'est jamais unanime. La raison est
structurelle : trois tirages à écart 2 ne déterminent que a², et tous les
tirages suivants étant eux aussi à des décalages **pairs**, aucun n'apporte
la moindre information sur a lui-même. Capturer vingt tirages à pas régulier
pair n'apprendrait rien de plus que quatre.

**Quatre tirages au minimum.** À n = 3 il ne reste zéro vérification
indépendante — le trio dépense ses deux équations à définir (A, C) — et le
témoin négatif le confirme brutalement : sur des suites uniformes, la
réduction « floor » produit une fausse récupération **3 fois sur 3**. Dès
n = 4, le compte de faux positifs retombe à 0 et y reste jusqu'à n = 8.

**Les modèles B et C ne demandent presque rien** : deux tirages et un seul
tirage respectivement, solution unique d'emblée, quel que soit l'espacement.
Leur équation y = a·x + c vit à l'intérieur du tirage.

> **Consigne de terrain.** Capturer des tirages qui se **suivent**. C'est le
> pas impair le plus simple à viser, le plus convergent des schémas testés,
> et c'est aussi ce que h10 demandait pour le test 2-adique — une même
> consigne sert les deux. Cinq consécutifs suffisent aux trois modèles.

## 28. La loi de la cagnotte, et la fréquence de bascule (`h15_loi_cagnotte.py`)

h9 concluait : « la fréquence de franchissement demande une SÉRIE ; une
observation donne une distance, pas une dynamique ». C'est vrai d'une mesure
directe, pas d'une mesure modélisée — à condition de dire ce que le modèle
achète et ce qu'il laisse.

**Trois hypothèses, nommées.** H1 la cagnotte croît d'un montant fixe r par
tirage ; H2 elle est remportée avec une probabilité q par tirage, sans
mémoire ; H3 elle repart d'un plancher J₀. Sous H1–H3, l'âge de la cagnotte
à un instant quelconque est géométrique, donc

    P(J ≥ S) = exp(−(S − J₀)/μ)      avec μ = r/q

Vérifié par simulation — et l'écart admissible n'est pas fixé à la main : il
est calculé depuis le nombre de renouvellements de la simulation, et
rapporté en unités d'écart-type. Moyenne et queue tombent toutes deux à
moins de 3 σ.

**L'estimation ponctuelle**, avec J₀ = 0 (le cas le moins favorable) :

| mise | cagnotte | seuil | S/μ | fraction de tirages favorables |
|---|---|---|---|---|
| 5 | CHF 355 | CHF 1 551 | 4,37 | 1,27 % |
| **6** | **CHF 2 287** | **CHF 7 753** | **3,39** | **3,37 %** |
| 7 | CHF 1 540 | CHF 40 979 | 26,6 | 2,8·10⁻¹² |
| 8 | CHF 9 292 | CHF 230 115 | 24,8 | 1,8·10⁻¹¹ |
| 10 | CHF 495 713 | CHF 8 911 711 | 18,0 | 1,6·10⁻⁸ |

Un tirage toutes les cinq minutes : 3,4 % ferait dix tirages favorables par
jour à la mise 6, un toutes les deux heures et demie.

**Et l'incertitude EST le résultat.** Une exponentielle a un écart-type égal
à sa moyenne. Avec un seul relevé, l'intervalle exact à 95 % sur la fraction
favorable va de **0,00 % à 91,8 %** — autant dire qu'on ne sait rien.

| relevés | 1 | 3 | 10 | 30 | 100 |
|---|---|---|---|---|---|
| fraction favorable à 95 % | 0–91,8 % | 0,03–49,7 % | 0,31–19,7 % | 0,90–10,2 % | 1,68–6,34 % |

Il faut une trentaine de relevés pour situer la fraction à un facteur 10
près, une centaine pour un facteur 3. La demande de données du dossier
cesse d'être un souhait et devient un nombre.

**Le raccourci, et c'est lui qui compte.** r est simplement la *différence*
entre deux relevés successifs sans gain entre les deux ; q est le taux de
chutes observées. Avec r et q mesurés, μ n'est plus estimé à travers une
variable aléatoire — il est calculé, et l'intervalle s'effondre. Deux
relevés rapprochés valent donc bien davantage que deux relevés éloignés.

**Ce qui a été câblé.** L'app recevait déjà les cagnottes de l'API
(`extraJackpots`) sans en garder la moindre mémoire — chaque tirage passé
était une observation perdue pour toujours. Elle tient désormais un journal
persistant (`JackpotReading`, un relevé par tirage et par mise, sans
doublon) et `JackpotLaw` en tire l'accumulation par tirage (médiane, donc
robuste à une lecture d'écran erronée), le compte de chutes, et la fraction
de tirages favorables avec son intervalle de Poisson exact. Les bornes de
Garwood sont obtenues par bissection sur la fonction de répartition, faute
de fonction gamma en Swift, et vérifiées contre les quantiles exacts du
khi-deux.

**Les deux réserves structurelles vont dans le même sens, et c'est le bon.**
Un plancher J₀ > 0 rend le franchissement plus fréquent que calculé ; et le
seuil de h9 est *suffisant* et non nécessaire, puisqu'il ignore les rangs
intermédiaires qui ne peuvent qu'ajouter. La vraie fraction favorable est
donc plus haute que celle estimée ici. La réserve qui va dans l'autre sens
est le prix du ticket : tout est par franc misé, et ce prix reste la donnée
manquante la moins chère à obtenir de tout le dossier.

## 29. Le rendement conditionnel, et l'identité qui le rend calculable (`h16_rendement_conditionnel.py`)

h15 répondait à « combien d'occasions se présentent ». Il restait la
question qui décide s'il faut jouer : **quand une occasion se présente, elle
vaut combien ?** La réponse a une forme fermée dont la simplicité n'était pas
prévisible.

**L'identité.** Soit c le prix du ticket, p = P(k/k), et S = c/p le seuil de
h9. Sous l'absence de mémoire (h15), E[J | J ≥ S] = S + μ, donc le rendement
d'un franc misé en ne jouant qu'au-dessus du seuil vaut

    p·E[J | J ≥ S]/c = p(S + μ)/c = 1 + μ/S

Le gain conditionnel est donc **exactement μ/S** — le nombre que h9 affichait
comme « fraction du seuil » en croyant ne mesurer qu'une distance. Le même
rapport, lu dans l'autre sens, est le taux de profit du jour où le seuil est
franchi.

**Et ce rapport est une constante du jeu.** Si N grilles sont jouées par
tirage et que la cagnotte reçoit une fraction α de la mise collectée, alors
μ = r/q = αNc/(Np) = α·c/p = α·S, d'où **μ/S = α**. Le nombre de joueurs
disparaît : davantage de joueurs font monter la cagnotte plus vite *et* la
font tomber plus souvent, exactement dans la même proportion. Le gain
conditionnel est la part de la mise que l'opérateur verse dans la cagnotte,
et rien d'autre.

Vérifié sur le processus simulé, avec la correction exacte plutôt qu'une
approximation cachée : μ/S = α·κ où κ = N·p·(1−q)/q, et κ vaut 0,997 à
λ = 0,006, 0,968 à λ = 0,065, et ne s'effondre qu'à λ = 0,65 — un régime où
la cagnotte tombe deux tirages sur trois et n'accumule plus rien. L'écart
mesuré à α·κ est inférieur à 1 % partout.

**Le seuil de bascule est l'optimum, pas un pis-aller.** Le profit espéré
*par tirage* en visant un seuil S' = x·μ vaut e^(−x)·(α(x+1) − 1) ; sa
dérivée s'annule en x = 1/α, c'est-à-dire exactement en S' = S. Attendre une
cagnotte plus grosse augmente le gain par occasion mais raréfie les
occasions plus vite encore. Vérifié numériquement : maximum en x = 3,390,
prédit 1/α = 3,390.

**Les chiffres, sur le seul relevé disponible.**

| mise | cagnotte μ̂ | seuil S | α̂ = μ̂/S | gain conditionnel |
|---|---|---|---|---|
| 5 | CHF 355 | CHF 1 551 | 22,9 % | **+22,9 %** |
| **6** | **CHF 2 287** | **CHF 7 753** | **29,5 %** | **+29,5 %** |
| 7 | CHF 1 540 | CHF 40 979 | 3,8 % | +3,8 % |
| 8 | CHF 9 292 | CHF 230 115 | 4,0 % | +4,0 % |
| 10 | CHF 495 713 | CHF 8 911 711 | 5,6 % | +5,6 % |

Et cette fois **l'incertitude est bien mieux conditionnée** qu'en h15 : le
gain conditionnel est *linéaire* en μ là où la fréquence en dépendait
exponentiellement. Avec un seul relevé, à 95 % : de **+8,0 % à +1 165 %** —
et la borne basse est positive.

**L'objection du partage se dissout.** Avec W ~ Poisson(λ) autres gagnants,
le gain devient (1+α)·E[1/(1+W)] − 1, et la stratégie meurt si
E[1/(1+W)] < 1/(1+α), soit λ > 0,54 pour α = 0,295. Mais λ n'est pas un
paramètre libre : c'est aussi le taux auquel la cagnotte tombe. Une cagnotte
qui atteint des milliers de francs en s'incrémentant de quelques dizaines
par tirage tombe une fois toutes les dizaines ou centaines de tirages, soit
λ ≈ 0,01 — deux ordres de grandeur de marge. Le partage coûte 0,3 % de gain
à λ = 0,006 et 3 % à λ = 0,065. Il ne retourne le signe qu'à λ = 0,65, dans
le même régime dégénéré que κ : **les deux limites de la stratégie sont la
même limite**, et elle a un nom — une cagnotte qui tombe trop souvent pour
s'accumuler.

**La réserve qui devrait inquiéter.** Un α de 29,5 % est anormalement
généreux : une cagnotte progressive reçoit typiquement 1 à 5 % de la mise
collectée, pas trente. Trois explications, et le dossier ne peut pas
trancher : l'estimation de μ sur un relevé est très bruitée ; la cagnotte
affichée n'est peut-être pas purement progressive (une part fixe abondée par
l'opérateur gonflerait μ sans correspondre à un α de turnover) ; ou le
ticket ne coûte pas un franc, auquel cas le seuil se multiplie d'autant. Les
trois se lèvent avec les mêmes données : une série de relevés, et le prix du
ticket.

**Et rien ici ne prédit un numéro.** Le gain vient du *moment* choisi, pas du
choix des numéros — l'invariance reste intacte. À ce moment-là, c'est la
géométrie de h13 qui dit comment répartir les grilles : disjointes, pour
multiplier par n les chances de toucher le rang plein sans rien coûter en
espérance.

**Ce qui a été câblé.** `JackpotLawEstimate` porte désormais le gain
conditionnel et son intervalle, et `GridsView` l'affiche en tête — avant la
fréquence, parce qu'il ne demande qu'un relevé là où la fréquence en demande
cent. Le quantile du khi-deux nécessaire à l'intervalle est obtenu depuis la
même fonction de répartition de Poisson, via
P(χ²(2n) ≤ x) = P(Poisson(x/2) ≥ n), et vérifié contre scipy sur douze
points.

## 30. Combien miser, et ce que le gain rapporte vraiment (`h17_taille_de_mise.py`)

h16 donne une espérance. Ce n'est pas de l'argent. Entre les deux il y a la
variance, et elle est ici démesurée : on gagne une fois sur 7 753 et l'on
touche 10 000 fois la mise. Ne pas poser la question serait malhonnête.

**Une grille seule.** Le critère de Kelly donne une fraction optimale de
2,94·10⁻⁵ du capital par occasion, soit une croissance de 3,96·10⁻⁶ en
logarithme — **+1,4 % par an** en jouant les 3,37 % de tirages favorables,
à raison d'un tirage toutes les cinq minutes. L'espérance est de +29,5 %,
mais miser davantage détruit plus de capital dans les 99,987 % de pertes
qu'il n'en gagne dans le reste.

**Et c'est ici que la géométrie de h13 se paie en francs.** n grilles
disjointes gagnent n fois plus souvent, n fois moins gros : la moyenne est
intacte, la variance divisée par n, et la croissance de Kelly — au premier
ordre le carré de l'avantage divisé par la variance — multipliée par n.

| n grilles disjointes | fraction de Kelly | croissance/occasion | rapport | croissance/an |
|---|---|---|---|---|
| 1 | 2,94·10⁻⁵ | 3,96·10⁻⁶ | ×1,00 | +1,4 % |
| 4 | 1,18·10⁻⁴ | 1,59·10⁻⁵ | ×4,00 | +5,8 % |
| 8 | 2,35·10⁻⁴ | 3,17·10⁻⁵ | ×8,01 | +11,9 % |
| **13** | **3,83·10⁻⁴** | **5,16·10⁻⁵** | **×13,02** | **+20,0 %** |

Le facteur suit n à moins de 0,2 % près, et 13 = ⌊80/6⌋ est le maximum de
grilles disjointes à la mise 6. Vérifié par simulation sur 40 millions
d'occasions : croissance mesurée à 0,6 σ de la prédiction.

**La contrainte qui décide de tout.** La fraction de Kelly est un
pourcentage du capital ; le ticket, lui, a un prix plancher. Si le premier
tombe sous le second, on ne peut pas miser Kelly — on est forcé de
**surmiser**.

| prix du ticket | coût d'un tour de 13 grilles | capital minimal pour Kelly |
|---|---|---|
| CHF 0,50 | CHF 6,50 | CHF 16 995 |
| CHF 1,00 | CHF 13,00 | **CHF 33 991** |
| CHF 2,00 | CHF 26,00 | CHF 67 981 |
| CHF 5,00 | CHF 65,00 | CHF 169 953 |

Et la courbe de surmise est brutale : à ×2 Kelly la croissance annualisée
tombe de +20,0 % à +5,0 %, à ×3 elle vaut **−25,5 %**, à ×5 **−75,0 %**. Un
joueur disposant de CHF 1 000 et misant un tour à CHF 1 la grille miserait
**×34 Kelly** — très au-delà du point où l'espérance positive cesse de
produire de la croissance.

> **La conclusion pratique du dossier, et elle tempère §29 sans le
> contredire.** Le gain est réel et important en espérance, mais il ne se
> convertit en capital qu'à partir d'une réserve de l'ordre de plusieurs
> dizaines de milliers de francs. En dessous, le pari reste favorable en
> espérance et **perdant en croissance** — ce qui, pour quelqu'un qui joue
> plus d'une fois, est ce qui compte.

**Ce que le barème inconnu changerait, et dans le bon sens.** Les rangs
intermédiaires ajoutent deux fois : ils augmentent l'espérance, et ils
réduisent la dissymétrie — or c'est la dissymétrie qui écrase la fraction de
Kelly. Sur un modèle délibérément grossier (un seul rang intermédiaire
fictif rendant une fraction ρ de la mise), la croissance est multipliée par
3,2 à ρ = 20 %, par 7,6 à ρ = 40 %, par 15,5 à ρ = 60 %. Le barème ne
déplace donc pas seulement l'espérance : il déplace la **taille de mise
admissible**, et c'est elle qui décide si le gain devient de l'argent.

## 31. La valeur de voir — le théorème qui range tout le dossier (`h18_valeur_de_voir.py`)

Le dossier a exploré deux voies apparemment sans rapport : choisir les
numéros, fermée par l'invariance ; choisir le moment, ouverte par §29. Elles
sont deux cas d'un même énoncé, et le formuler explique d'un coup pourquoi
l'une est fermée et l'autre ouverte.

> **Théorème de la valeur de voir.** Soit X une quantité observable *avant*
> la mise et qui multiplie le gain, R₀ le retour par franc à X = 1. Le
> profit par tirage d'une politique A ⊂ valeurs de X vaut
> E[(R₀X − 1)·1{X ∈ A}], maximisé terme à terme par A = {x : R₀x > 1}. La
> politique optimale est donc **« miser si et seulement si le pari est
> favorable »**, quelle que soit la loi de X. Et la valeur de voir X plutôt
> que de miser à l'aveugle vaut
>
>     V = E[(R₀X − 1)⁺] − (R₀·E[X] − 1)⁺
>
> soit exactement l'écart de Jensen de la fonction convexe x ↦ (R₀x − 1)⁺.

Vérifié par balayage exhaustif de tous les seuils sur trois lois (uniforme,
géométrique, à deux points) × deux taux de retour : le seuil optimal
retrouve le seuil de bascule 1/R₀ dans les six cas, à 10⁻¹² près.

**Pourquoi cela referme l'invariance.** Le théorème d'invariance dit que la
loi du gain ne dépend pas de la grille. En langage de celui-ci : *choisir
des numéros ne produit aucun X*. La variable est dégénérée, l'écart de
Jensen est nul, il n'y a littéralement rien à voir. Aucune statistique sur
les numéros chauds, froids, les retards ou les paires ne peut créer un écart
de Jensen là où la loi ne varie pas — c'est pourquoi les 3 328 tests du
registre ne pouvaient **pas** trouver autre chose que zéro.

**Le boost, sa loi exacte, et ce que sa visibilité vaudrait.** Sur les 70 560
tirages archivés : P(1) = 0,512, P(2) = 0,238, P(3) = 0,151, P(4) = 0,050,
P(5) = 0,0247, P(10) = 0,0249, E = 2,0117.

| R₀ | à l'aveugle | en voyant le boost | valeur de voir | seuil de jeu |
|---|---|---|---|---|
| 0,40 | 0,000 | 0,159 | **+0,159** | boost ≥ 3 |
| 0,50 | 0,006 | 0,262 | **+0,256** | boost ≥ 3 |
| 0,60 | 0,207 | 0,412 | **+0,205** | boost ≥ 2 |
| 0,70 | 0,408 | 0,562 | +0,154 | boost ≥ 2 |
| 0,80 | 0,609 | 0,712 | +0,102 | boost ≥ 2 |

À 50 % de retour, voir le boost avant de miser vaut **26 centimes par franc
misé**. Ce n'est pas un raffinement : c'est un renversement du signe de
l'espérance, sans toucher aux numéros et sans rien supposer du générateur.

**La combinaison.** Cagnotte et boost multiplient tous deux le gain, donc le
pari est favorable dès que B·J·p ≥ 1, c'est-à-dire J ≥ S/B : **le boost
abaisse le seuil de la cagnotte d'un facteur B**. Et par absence de mémoire,
le gain conditionnel au-dessus de S/B vaut B·p·(S/B + μ) − 1 = **B·α**. Le
boost multiplie donc l'avantage *et* la fréquence des occasions.

| boost | seuil de cagnotte | fréquence | avantage | profit/tirage |
|---|---|---|---|---|
| 1 | CHF 7 753 | 3,4 % | +29,5 % | 0,0099 |
| 3 | CHF 2 584 | 32,3 % | +88,5 % | 0,2859 |
| 10 | CHF 775 | 71,3 % | +295,0 % | 2,1018 |

Profit par tirage en voyant le boost : 0,170 ; à l'aveugle : 0,110 ; rapport
**×1,54** sur la seule voie de la cagnotte — qui s'ajoute au renversement
ci-dessus, lequel porte sur les rangs à gain fixe.

**Et sur la taille de mise (§30).** Un avantage plus grand et un seuil plus
bas augmentent la fraction de Kelly, donc raccourcissent le temps de
doublement et abaissent le capital minimal : de CHF 33 991 à boost 1 à
CHF 10 377 à boost 10. La politique combinée double le capital en 44 jours
contre 1 385 jours pour la politique aveugle, soit ×31,6.

**Avertissement, et il est central.** Ces derniers nombres sont tous
proportionnels à α, estimé sur *un* relevé — l'intervalle de §29 va de +8 %
à +1 165 %, et la croissance de Kelly est quadratique en l'avantage. Ils
disent un ordre de grandeur et une comparaison entre politiques, pas un
rendement. Trois hypothèses non vérifiées les portent : que le boost
multiplie aussi la cagnotte progressive, qu'il soit visible avant la
clôture, et qu'on puisse miser une fraction arbitraire du capital. Ce qui
reste solide indépendamment de α, c'est le **rapport** entre les deux
politiques.

**La grille de lecture qui en découle**, et elle range trente voies d'un
coup :

- **Valeur nulle et démontrée telle** — le choix des numéros (écart de
  Jensen identiquement nul).
- **Valeur nulle par accident** — la récupération du générateur : elle
  créerait un X énorme, mais aucun générateur n'a été trouvé.
- **Valeur positive et mesurée** — la cagnotte : +29,5 % sur 3,4 % des
  tirages.
- **Valeur positive et non mesurée** — le boost, s'il est visible. C'est
  aujourd'hui la seule case à la fois grande et vide, et elle se remplit
  avec une observation faite sur l'appareil, pas avec du calcul.
- **Valeur nulle par construction** — tout ce qui n'est visible qu'*après*
  la clôture. Une variable qu'on ne peut pas voir avant de miser ne peut pas
  entrer dans A. C'est la réponse générale à « l'ordre de sortie
  aiderait-il ? » : il n'aide que s'il permet de *prédire*, jamais parce
  qu'il informe.

## 32. Le canal du bonus (`h19_canal_bonus.py`)

h12 a établi que l'ordre de sortie vaut deux fois le tirage trié. Mais
l'ordre n'existe que sur cinq tirages capturés à la main, quand l'archive en
compte 70 560 — triés, donc muets sur l'ordre. Sauf qu'il reste un champ.

**Le fait structurel, vérifié sur les 70 560 tirages.** Le `bonus` est
**toujours** l'un des vingt numéros tirés — 70 560 sur 70 560, là où
l'indépendance en prédirait 17 640. Ce n'est donc pas un tirage
supplémentaire mais une **désignation** parmi les vingt. Et si cette
désignation suit une règle de position — « la dernière boule sortie », la
convention la plus répandue — alors le bonus est une sortie *ordonnée* du
générateur, disponible sur toute l'archive.

d7 avait testé la *valeur* du bonus (loi marginale, mémoire sérielle,
appartenance au tirage suivant, rang dans le tirage trié). Tout cela regarde
le bonus comme un numéro. Ce fichier le regarde comme une **sortie**, ce qui
est une question différente et jamais posée.

**Le levier, et l'objection que les témoins ont démentie.** Si le bonus est
la valeur brute d'un échantillonneur « s mod 80 », alors (bonus − 1) mod 16
publie exactement les quatre bits de poids faible de l'état, et une relation
affine r_{t+1} = A·r_t + C mod 2^k doit tenir sur les 70 559 transitions.
L'objection évidente est que le rejet des doublons fait varier le nombre de
sorties consommées, donc A = a^g avec lui. **C'est ce que j'avais écrit, et
c'est faux** : modulo une puissance de deux, l'ordre multiplicatif de a
divise 2^(k−2), donc a^g ne prend que quelques valeurs quel que soit g. Un
unique couple (A, C) attrape la plus fréquente.

| témoin (20 000 tirages) | mod | expliqué | null (permutation) | z |
|---|---|---|---|---|
| bonus = s mod 80, avec rejet | 16 | 40,6 % | 6,69 % ± 0,08 | **+433** |
| bonus = s mod 80, avec rejet | 80 | 8,45 % | 1,53 % ± 0,02 | **+290** |
| bonus = ⌊s·80/2⁶⁴⌋, avec rejet | 16 | 6,79 % | 6,69 % ± 0,07 | +1,3 |
| bonus = élément de permutation | 16 | 6,85 % | 6,77 % ± 0,10 | +0,8 |
| uniforme | 16 | 6,57 % | 6,71 % ± 0,08 | −1,8 |

La portée du test est donc délimitée **par mesure et non par argument** : il
voit tout bonus qui est une valeur brute modulaire, avec ou sans rejet ; il
est aveugle à un bonus tiré des bits de poids fort, et à un bonus qui est un
contenu de tableau plutôt qu'une sortie.

**Sur l'archive : rien.** Cinq modules × trois décalages, null par
permutation à 200 réplicats par cellule. Le plus grand écart est +3,10 σ
(module 16, décalage 1), soit p = 9,6·10⁻⁴ pour la cellule et p = 0,014
après correction sur les quinze — très au-dessus du seuil de Holm du
registre entier. Consigné sous `h19.bonus_affine`, verdict conforme.

**Ce que la règle du bonus vaudrait, et la mesure qui la tranche.** Savoir
laquelle des vingt boules est sortie en dernier ajoute log₂ 20 = 4,32 bits
par tirage, soit 37 kilo-octets d'information d'ordre sur l'archive entière.
Ce n'est pas assez pour reconstituer l'ordre complet (65,94 bits contre
122,69) mais c'est assez pour **ancrer une sortie du générateur par tirage à
une position connue** — exactement ce qu'il faut aux attaques de §25 pour se
transporter sur 70 560 tirages au lieu de cinq.

> **La mesure tient en une ligne.** Pour chacun des cinq tirages ordonnés
> déjà capturés, relever le numéro bonus et regarder sa position dans
> l'ordre de sortie. Cinq fois la même position — la vingtième, ou la
> première — et la règle est établie. Des positions dispersées, et le bonus
> est un choix uniforme qui ne porte aucun ordre. L'archive locale s'arrête
> au tirage 1 380 173 et les tirages ordonnés commencent à 1 381 023 : le
> recoupement ne peut pas se faire hors ligne.

## 33. La prédiction elle-même (`predire.py`)

Tout ce qui précède sert à cadrer une seule chose : sortir vingt numéros, et
dire ce qu'ils valent. `lab/predire.py` le fait, avec l'appareil complet —
les 26 têtes de l'essaim, leurs poids AdaHedge appris en marche avant sur
70 565 tirages, et le champ qu'elles opposent au tirage qui n'a pas encore eu
lieu. La sortie est archivée dans `lab/prediction.txt`.

**Ce que l'essaim vaut, mesuré et non annoncé.** Rejeu en marche avant sur
les 20 000 derniers tirages, chaque prédiction notée sur le tirage qu'elle
n'a pas encore vu : recouvrement moyen **4,986** contre 5,0000 d'espérance
exacte, soit **−1,17 σ**. Meilleur tirage 12/20, pire 0/20. L'essaim fait jeu
égal avec le hasard, et il ne peut rien faire d'autre — ce chiffre n'est pas
un échec, c'est la mesure du théorème.

**Ce que la sélection vaut, exactement.** Espérance de bons numéros : 5,0000
sur 20 — et 5,0000 également pour n'importe quels vingt autres numéros.
P(au moins 10 bons) = 0,4743 %. P(les 20) = 1 sur 3,54·10¹⁸.

**Et le portefeuille, qui lui change quelque chose.** Treize grilles
disjointes de six numéros, construites par la couverture équilibrée de §26
avec le classement de l'essaim en simple départage : recouvrement maximal 0,
une grille pleine à 1 sur 7 753, **au moins une des treize à 1 sur 596** —
soit exactement le facteur 13 du théorème G. Ce facteur ne vient pas d'une
meilleure prédiction : il vient de ce que treize grilles disjointes offrent
treize occasions distinctes.

**Le fichier se termine par les deux seuls leviers réels** — le moment (§29,
ne pas jouer sous le seuil de bascule) et la taille de mise (§30, la fraction
de Kelly et le capital minimal) — avec la phrase qui résume trente-deux
voies : *les vingt numéros n'en sont pas un.*

## 34. Le ré-amorçage — la région que toutes les attaques précédentes manquaient (`tools/sweep_order.c`, `sweep_mt.c`, `sweep_java48.c`)

Toutes les attaques du dossier, de §17 à §33, supposent un générateur qui
**tourne en continu** : l'état à la fin d'un tirage est celui du début du
suivant. C'est ce qui permet de *résoudre* (a, c) sur plusieurs tirages au
lieu de les énumérer.

Une implémentation qui **ré-amorce à chaque tirage** les défait toutes d'un
coup. Et c'est le cas le plus courant en pratique — celui qu'on écrit quand
on tape `new Random(seed)` au début de la fonction de tirage. Contre lui, la
seule attaque possible est le balayage de l'espace des graines.

`tools/sweep48.c` faisait cela pour **une** famille, **un** échantillonneur,
et contre l'**ensemble** des vingt numéros. Trois outils neufs changent les
trois points.

**L'ordre change tout.** Travailler sur l'ordre de sortie plutôt que sur
l'ensemble fait passer le filtre de 1/4 à 1/80 par pas. La probabilité qu'une
graine fausse survive tombe de C(80,20)⁻¹ ≈ 3·10⁻¹⁹ à (80!/60!)⁻¹ ≈
**1·10⁻³⁷**. Sur 2³² graines et 48 combinaisons, le nombre attendu de faux
positifs vaut 2·10⁻²⁷ : **toute touche est réelle, et aucune confirmation
n'est nécessaire.**

**Une erreur de protocole, corrigée.** Les premiers balayages exigeaient
qu'une graine reproduise *aussi* un second tirage ordonné. C'était une faute
qui allait précisément contre le but : dans l'hypothèse du ré-amorçage,
chaque tirage a sa propre graine — c'est la définition même. Un générateur
réellement amorcé par le numéro de tirage aurait été trouvé sur le premier
tirage, puis **jeté** par la confirmation. Sans elle, le balayage devient
universel sur les schémas d'amorçage :

> balayer [0, 2³²) contre UN tirage ordonné écarte d'un coup tout schéma
> d'amorçage dont la graine tombe dans cette plage — numéro de tirage,
> numéro plus constante, seconde d'époque, compteur, petite graine fixe. Il
> n'est pas nécessaire de les énumérer.

**Ce qui a été balayé, et ce qui en est sorti.**

| outil | espace | combinaisons | résultat |
|---|---|---|---|
| `sweep_order` | graines [0, 2³²), **sur les cinq tirages** | 12 générateurs × 4 échantillonneurs | **0** |
| `sweep_order` | millisecondes d'époque ± 7 jours | idem | **0** |
| `sweep_order` | nanosecondes d'époque ± 1 s | idem | **0** |
| `sweep_linked` | décalages [0, 2³²), graine = **numéro de tirage + B** | idem, sur 10 tirages étalés sur des mois | **0** |
| `sweep_java48` | **les 2⁴⁸ états complets** | java.util.Random, Fisher-Yates | **0** |
| `sweep_mt` | graines [0, 2³²) | MT19937 × 2 amorçages × 5 échantillonneurs | **0** |

Les douze familles vont des LCG historiques (java.util.Random, MSVC, glibc)
aux familles modernes (xoshiro256\*\*, xoshiro128\*\*, xoroshiro128+, pcg32,
pcg64), en passant par xorshift et splitmix64. Autotest : **48/48**
combinaisons retrouvent leur témoin, avec exactement une graine compatible à
chaque fois.

**Les 2⁴⁸ états de java.util.Random, en secondes au lieu de 78 heures.**
`next(31)` rend `(int)(s >>> 17)`, et `nextInt(bound)` pour une borne qui
n'est pas une puissance de deux rend `next(31) % bound`. Donc pour une borne
**paire**, p_i mod 2^v publie **les bits 17 à 20 de l'état** — ni les bits de
poids faible où vit le levier 2-adique habituel, ni ceux de poids fort où
vivent les attaques par réseau : ceux du *milieu*, exploitables parce que le
LCG modulo 2⁴⁸ reste clos modulo 2²¹. D'où une attaque en deux temps :
énumérer s mod 2²¹ en exigeant ces bits (il reste une trentaine de
candidats), puis énumérer les 27 bits de poids fort. Le coût passe de
2,8·10¹⁴ à 4·10⁹ pas, soit un facteur 10⁴. Autotest : 3/3 états témoins
retrouvés, dont deux hors de portée d'un balayage 2³².

**Le piège de la borne 64**, qu'il fallait voir : `nextInt` traite les
puissances de deux à part, en prenant les bits de poids *fort*. Une seule
borne est concernée parmi 80, 79, …, 61 — 64, au dix-septième pas. La phase
2-adique doit la sauter et la phase de vérification la traiter comme le
reste ; l'oublier ferait rater le vrai état sans rien signaler.

**Et une transcription fausse, attrapée par la confrontation à CPython.**
`sweep_mt` reproduit `random.sample` et `random.shuffle` à la ligne près, et
la validation ne se fait pas contre un autotest interne mais contre CPython
lui-même : `random.seed(987654)` est exécuté en Python, et le balayage doit
retrouver 987654 depuis ses sorties. Il la retrouve — après correction d'une
erreur qu'aucun autotest interne n'aurait pu voir. Le `_randbelow` de CPython
demande `n.bit_length()` bits et non `(n-1).bit_length()` ; les deux
coïncident partout sauf quand n est une puissance de deux, et n parcourt ici
80, 79, …, 61. La divergence tombait pile sur n = 64, au **dix-septième**
numéro : seize numéros justes, puis une dérive silencieuse.

**L'amorçage lié au numéro de tirage**, que cinq tirages du même jour ne
peuvent pas tester. `sweep_linked` teste la *relation* graine(t) = id(t) + B
pour tout B de [0, 2³²), confirmée sur dix tirages étalés sur toute
l'archive — c'est la forme qu'on écrit quand on veut un tirage reproductible
et vérifiable, `new Random(drawId)`, et elle est invisible pour un balayage
qui exigerait la même graine à deux tirages différents. Dix tirages liés
portent la probabilité de faux positif sous 10⁻¹⁸⁰. Résultat : zéro décalage
compatible, sur les 48 combinaisons.

**Ce que la campagne a rendu à l'app.** Trois familles modernes — xoshiro256\*\*,
xoshiro128\*\*, xoroshiro128+ — n'étaient couvertes par aucune attaque du
dossier et sont désormais dans `PRNGRecovery` (l'app passe de 8 à 11
familles), leurs flux vérifiés contre une référence C compilée. Et surtout,
l'app **garde** maintenant l'ordre de sortie : elle le recevait à chaque
tirage puis le perdait à chaque relance, l'historique refetché revenant
trié. `OrderedDraw` est journalisé et persisté, et `runRecovery` réinjecte
l'ordre conservé avant d'attaquer. L'accumulation de tirages *consécutifs*
— la quantité que §27 désigne comme décisive — se fait ainsi toute seule, à
raison d'un toutes les cinq minutes, sans que personne ait à relever quoi
que ce soit.

**Un point de défaillance unique, repéré puis levé.** Le balayage 2³² n'avait
d'abord porté que sur UN tirage ordonné, transcrit à la main depuis une
capture d'écran — et le filtre agit dès le premier numéro. Si ce premier
numéro avait été mal lu, les 48 combinaisons seraient mortes au premier pas
et le « zéro » n'aurait rien voulu dire. Le recoupement est impossible :
l'archive s'arrête 850 tirages avant, elle ne contient aucun des cinq.

Le balayage a donc été refait sur les **quatre autres** tirages ordonnés.
Zéro partout. Ou bien aucun des cinq ne sort d'un générateur balayable, ou
bien les cinq transcriptions sont fausses — ce qui n'est pas crédible. Le
résultat est désormais robuste à une erreur de lecture sur n'importe lequel.

**Le Mersenne Twister, entièrement.** C'est le générateur le plus répandu du
logiciel ordinaire — `random` de Python, `mt_rand` de PHP, `RandomState` de
numpy, la bibliothèque standard de Ruby — et il s'amorce partout par un
entier de 32 bits, donc il est intégralement balayable. Les 4 294 967 296
graines, les deux amorçages (`init_genrand` canonique et le `random.seed(n)`
de CPython), les cinq échantillonneurs dont `random.sample` et
`random.shuffle` transcrits à la ligne près : **zéro graine compatible**, en
9 h 20 de temps processeur.

**Ce que cette campagne laisse ouvert, et il faut le nommer.** Les graines de
plus de 32 bits non dérivées d'une horloge (2⁶⁴ : hors de portée du calcul).
L'état complet de 19 937 bits d'un Mersenne Twister (hors de portée de
l'information : il faudrait 624 sorties consécutives entières, et cinq
tirages n'en donnent que 630 bits tronqués). Et surtout un générateur dont
l'état ne suit aucune récurrence affine — chiffrement par bloc, éponge,
source matérielle. C'est le cas le plus probable pour un opérateur certifié,
et **aucune analyse de sorties publiques ne peut le trancher, quelle qu'en
soit la profondeur.**

### Un dernier test, et il n'a aucune puissance — c'est le résultat

Le test d'anniversaire cherche une répétition exacte dans l'archive : si le
générateur avait un espace d'états assez petit, deux tirages finiraient par
coïncider entièrement, et cela se verrait **sans rien supposer de la
récurrence**. C'est le seul test model-free capable de borner l'espace
d'états.

Résultat : 70 560 tirages, 70 560 distincts, zéro répétition. Attendu sous
uniformité : 7,0·10⁻¹⁰.

Mais l'absence ne prouve rien, et le calcul de puissance le dit sans
ambiguïté :

| espace d'états supposé | collisions attendues sur 70 560 tirages |
|---|---|
| 2³⁰ | 2,32 |
| 2³² | 0,58 |
| 2³⁴ | 0,14 |
| 2⁴⁰ | 0,004 |

Observer zéro collision est **compatible avec un état de trente bits**.
L'archive est trop courte pour que ce test morde : il faudrait de l'ordre de
2^(b/2) tirages pour sonder un état de b bits, soit 65 536 tirages pour
32 bits — on y est tout juste — et 16 millions pour 48 bits.

C'est donc un résultat négatif sur la MÉTHODE, pas sur l'archive, et il est
consigné pour qu'on ne le refasse pas. Les espaces d'états que ce test aurait
pu atteindre sont de toute façon ceux que les balayages de §34 couvrent
exhaustivement — et bien mieux.

## 35. Les générateurs à sortie inversible (`h21_sortie_inversible.py`)

§25 testait trois modèles de source sous le rang ordonné, et les trois
supposent une récurrence **affine** de l'état — c'est ce qui permet d'y
résoudre (a, c). Un générateur à sortie *inversible* échappe entièrement à ce
cadre : splitmix64 avance son état par une simple addition s → s + γ, avec
γ = 0x9E3779B97F4A7C15 fixé et public, mais sa sortie est un mélange non
affine ; xorshift64\* avance par des décalages-xor. Le solveur de §25, qui
cherche une relation affine entre les valeurs publiées, ne peut rien en
faire. Or ce sont précisément les générateurs qu'on choisit aujourd'hui quand
on veut du rapide et du moderne sans dépendance.

**Le levier est brutal, et il n'y a rien à résoudre.** Un tirage ordonné
publie 122,69 bits, assez pour contenir deux sorties de 64 bits (théorème des
deux états). Si la sortie est inversible, chaque moitié se retourne en un
état exact. Le test tient alors en une identité **publique** :

    splitmix64    s₂ − s₁ doit valoir γ
    xorshift64*   s₂ doit valoir xorshift(s₁)

Aucune constante à deviner, aucune énumération, un seul tirage suffit. Sur
~40 candidats de rang, la probabilité qu'un faux passe vaut 40·2⁻⁶⁴ ≈ 2·10⁻¹⁸.

| | résultat |
|---|---|
| contrôle des inversions (16 000 + 8 000 allers-retours) | 0 échec |
| témoins positifs (2 générateurs × 2 réductions × 2 ordres) | **8/8 détectés** |
| témoins négatifs (ordres uniformes) | **0/120** |
| les cinq tirages ordonnés réels | **0 hypothèse compatible** |

**Une erreur attrapée par le contrôle d'aller-retour.** L'inverse de
y = x ^ (x >> s) accumule les décalages à pas CONSTANT —
x = y ^ (y>>s) ^ (y>>2s) ^ … — et non par doublement. La version à
doublement a l'air parfaitement plausible et elle est fausse partout ; elle
faisait échouer 16 000 allers-retours sur 16 000. Sans ce contrôle, le test
aurait rendu « rien trouvé » sur les données réelles avec l'assurance d'un
résultat, et c'est exactement la panne que les témoins existent pour
attraper.

## 36. La question d'avant : α sert à décider quoi ? (`h25_plan_releves.py`)

Le dossier réclame trois fois les mêmes données. §28 : « il faut une
trentaine de relevés pour situer la fraction à un facteur 10 près, une
centaine pour un facteur 3 ». §29 : « les trois se lèvent avec les mêmes
données : une série de relevés, et le prix du ticket ». §31 : « ces derniers
nombres sont tous proportionnels à α, estimé sur *un* relevé ».

Une demande de données ne se justifie que par une décision qu'elle change.
Personne n'avait posé la question d'avant : **α sert à décider quoi ?**

### L'inventaire, et il est court

L'app propose exactement quatre actions ; tout le reste est du rapport.

| | décision | α y entre-t-il ? | pourquoi |
|---|---|---|---|
| D1 | jouer ou non à ce tirage | **non** | la règle est `J ≥ S = c/p` ; `J` est affiché, `p` est une combinatoire exacte |
| D2 | combien miser | **non** — c'est le résultat de cette section | la cagnotte est affichée à l'instant de miser |
| D3 | comment disposer les grilles | non | dominance de l'étalement prouvée rang par rang (§26) |
| D4 | quels numéros cocher | non | théorème d'invariance (§1) |

D1, D3 et D4 étaient déjà acquis — §5 bis nommait même sa condition
« suffisante » précisément parce qu'elle ne suppose rien. Le seul cas
douteux était D2, où `h17` fait entrer α par la cagnotte moyenne
`J = S(1 + α)`. Mais au moment de miser, la cagnotte n'est pas une moyenne :
elle est à l'écran.

### Ce que coûte de dimensionner sur une moyenne dont on n'a pas besoin

**Le témoin d'abord**, sans quoi la comparaison ne prouverait rien : sur des
occasions **homogènes** — même cagnotte partout —, il n'y a plus
d'hétérogénéité à exploiter et les trois règles doivent coïncider. Elles
coïncident au zéro machine. Une machinerie de rejeu défaillante aurait donc
été attrapée là. (Précision qui évite de sur-lire l'accord : l'oracle tombe
exactement sur la fraction figée optimale parce que la grille géométrique
est centrée sur elle et la contient ; c'est une propriété de la grille, pas
une confirmation indépendante. Le témoin qui porte l'information est que
`R2` ne trouve rien de mieux qu'une fraction figée quand les occasions sont
identiques.)

Quatre règles rejouées sur le même processus (20 000 000 tirages,
α = 0,2950, 13 grilles disjointes à la mise 6, 654 827 occasions soit
3,27 % des tirages) :

| règle de dimensionnement | croissance totale | rapport à R2 |
|---|---|---|
| **R0** meilleure fraction figée, choisie par un oracle connaissant toute la trajectoire | 32,317 | ×0,728 |
| **R1** fraction figée à la cagnotte moyenne — ce que fait `h17` | 32,278 | ×0,727 |
| **R2** fraction recalculée sur la cagnotte **affichée** | **44,409** | ×1,000 |
| **R3** figée, α surestimé d'un facteur 3 | 2,212 | **×0,050** |
| R3′ figée, α sous-estimé d'un facteur 3 | 21,829 | ×0,492 |

Trois lectures, et c'est la deuxième qui décide.

**R2 gagne 38 %** de croissance sur la règle du dossier. **R2 bat aussi
R0**, la meilleure fraction figée qu'un oracle omniscient puisse choisir
(×1,374) : le compromis d'une fraction unique appliquée à des occasions
hétérogènes est donc perdant **par nature**, et non par mauvais réglage. La
question n'est pas de mieux estimer α pour mieux régler une fraction figée ;
c'est que la fraction ne doit pas être figée.

**Et le danger est asymétrique.** À la moyenne, un α surestimé d'un facteur
3 — soit à peu près la largeur de l'intervalle dont le dossier dispose, de
+8 % à +1 165 % — ne garde que **5 %** de la croissance, là où le
sous-estimer du même facteur en garde encore 49 %. Se tromper vers le haut
coûte dix fois plus que se tromper vers le bas : c'est la falaise de surmise
de §30, atteinte non par gourmandise mais par ignorance d'un paramètre. La
règle qui n'a besoin d'aucun α n'y est pas exposée.

**Le chiffre a été corrigé en cours de route, et il faut le dire.** Une
première version de cette section annonçait ici une croissance *négative*,
sur une trajectoire de 400 000 tirages. C'était un artefact d'effectif :
seuls les cycles qui atteignent le seuil portent de l'information, et il n'y
en avait qu'une trentaine — la trajectoire n'avait pas la précision que ses
six chiffres affichaient. Portée à 20 millions de tirages et recoupée par
intégration, la croissance reste positive. Le sens de l'asymétrie tenait ;
son amplitude était fausse.

R2 ne demande rien qui ne soit visible : la cagnotte est affichée, `p` est
exacte, `n` est un choix.

### La même quantité par une seconde voie

Une trajectoire simulée peut mentir sans le dire — c'est ce qui venait
d'arriver. L'écart est donc recalculé par un chemin qui ne partage rien avec
le premier : ni tirage aléatoire, ni rejeu. Par absence de mémoire, la
cagnotte au-dessus du seuil vérifie `J − S ~ Exp(μ)`, et les deux membres du
théorème N s'obtiennent par quadrature sur cette loi exacte.

| | par intégration | par simulation | écart |
|---|---|---|---|
| règle adaptative | 6,805460 × 10⁻⁵ | 6,781788 × 10⁻⁵ | 0,35 % |
| meilleure fraction figée | 4,949508 × 10⁻⁵ | 4,935174 × 10⁻⁵ | 0,29 % |
| **rapport** | **1,3750** | **1,3742** | 0,06 % |

Le rapport ne dépend donc ni du tirage aléatoire ni de la machinerie de
rejeu. Et c'est cette confrontation qui a établi que la version à 400 000
tirages était fausse : les rapports concordaient déjà (1,375 contre 1,412),
mais les *niveaux* divergeaient de 22 %, ce qu'aucune lecture du seul
rapport n'aurait révélé.

**Un troisième contrôle, et il a servi.** Passer la simulation de 400 000 à
20 000 000 de tirages a exigé de vectoriser le processus. La réécriture
avait un décalage d'un tirage sur l'âge de la cagnotte : une chute à
l'instant `s` remet la cagnotte à zéro *pour* l'instant `s+1`, dont l'âge
vaut donc 0 et non 1. Le contrôle contre la boucle littérale, sur la même
graine, a rendu un écart maximal de **5,718** — c'est-à-dire exactement `r`,
l'accumulation par tirage. Une erreur d'un cran se signe par la constante
qu'elle décale ; sans ce contrôle elle aurait produit des chiffres
plausibles et faux.

### Le plan de relevés, corrigé — l'information arrive au rythme des chutes

α sort des quatre décisions, mais il reste ce qui dit ce que la stratégie
**rapporte** par unité de temps. Ce plan-là garde donc un sens, et §28 en
donnait un raccourci — mesurer `r` (l'accumulation par tirage) et `q` (le
taux de chutes) — assorti d'une conclusion : « deux relevés rapprochés
valent bien davantage que deux relevés éloignés ».

La première moitié est juste, la seconde était incomplète. Indexé par le
nombre de **chutes** attendues plutôt que par une durée — `q` étant
lui-même inconnu, une durée n'aurait de sens qu'à un `q` particulier :

| chutes D | fenêtre | A : 95 % de α̂/α | B : 95 % de α̂/α | B défini |
|---|---|---|---|---|
| 1 | 400 | [0,20 ; 3,77] | [0,25 ; 1,00] | 62 % |
| 3 | 1 200 | [0,33 ; 2,84] | [0,43 ; 3,00] | 96 % |
| 10 | 4 000 | [0,50 ; 1,89] | [0,59 ; 2,00] | 100 % |
| 30 | 12 000 | [0,62 ; 1,67] | [0,71 ; 1,58] | 100 % |
| 100 | 40 000 | [0,78 ; 1,29] | [0,83 ; 1,25] | 100 % |
| 300 | 120 000 | [0,86 ; 1,18] | [0,90 ; 1,13] | 100 % |

**Ce qui indexe la précision est le nombre de chutes, pas le nombre de
relevés.** Entre deux chutes, l'app peut journaliser mille relevés : ils
décrivent tous le même cycle et n'apportent qu'une seule observation de
l'âge. L'app en collecte 204 par jour, mais elle n'apprend qu'au rythme où
la cagnotte tombe.

La loi d'échelle est **asymptotique et il faut le dire ainsi** : `écart
× √D` monte de 0,96 à 1,38 puis se stabilise vers **1,4** à partir de
D = 30. En dessous, la loi de l'estimateur est trop dissymétrique pour
qu'un écart-type la résume — c'est pourquoi le tableau donne un intervalle
et non un σ. Lu sur l'intervalle : le facteur d'incertitude sur α vaut
**18,9 à une chute, 3,8 à dix, 1,65 à cent**.

Enfin, le raccourci `B` de §28 est **moins bon** que la simple moyenne tant
que les chutes sont rares : `1/q̂` est une transformation convexe d'un
comptage, donc biaisée vers le haut et à queue lourde, et elle n'est même
pas définie dans 38 % des fenêtres à une chute attendue. Ce qu'il faut
garder de §28 : deux relevés **consécutifs** donnent `r` presque exactement,
l'accumulation étant déterministe entre deux chutes. Mais `r` saturé, la
précision ne dépend plus que de `q`, et `q` se paie en chutes.

### Le prix du ticket, qui n'est pas une donnée manquante parmi d'autres

§28 l'appelle « la donnée manquante la moins chère à obtenir » et §29 le
range à côté de la série de relevés. L'inventaire les sépare radicalement :
**c'est la seule donnée manquante dont une décision dépende.** Sans `c`, le
seuil `S = c/p` de D1 n'est pas calculable, et D1 est la règle qui décide
s'il faut jouer.

| prix du ticket | seuil D1 à la mise 6 | α implicite | capital minimal (13 grilles) |
|---|---|---|---|
| CHF 0,50 | CHF 3 876 | 59,0 % | CHF 10 436 |
| **CHF 1,00** | **CHF 7 753** | **29,5 %** | **CHF 33 991** |
| CHF 2,00 | CHF 15 506 | 14,7 % | CHF 120 457 |
| CHF 5,00 | CHF 38 764 | 5,9 % | CHF 694 709 |

La ligne à un franc retombe exactement sur le CHF 33 991 de §30 — contrôle
de cohérence entre les deux fichiers, calculé et non recopié.

Et **α est inversement proportionnel à `c`** : α = μ·p/c. Le « +29,5 % » de
§29 est un +29,5 % *à un franc* ; à cinq francs c'est +5,9 %. La réserve de
§29 — « un α de 29,5 % est anormalement généreux » — trouve donc parmi ses
trois explications candidates la moins chère à écarter, et c'est un coup
d'œil sur le prix d'un ticket.

### Deux faiblesses de ma première version

La première « vérifiait » que le taux d'arrivée sort de la décision en
balayant trois taux — mais la grille de fractions ne dépendait pas du taux,
si bien que les trois lignes réexécutaient la même arithmétique et
tombaient sur le même chiffre à 0,0e+00 près. Une simulation qui ne peut
pas échouer ne vérifie rien. L'additivité de la croissance logarithmique
est une identité et elle est désormais énoncée comme telle, la vérification
portant sur ce qui n'est pas trivial : le coût du compromis d'une fraction
figée.

La seconde donnait un tableau **non monotone** — 6,2 % d'erreur à un jour
contre 37,4 % à sept — parce que les fenêtres où l'estimateur est indéfini
étaient silencieusement écartées, et qu'à un jour il n'en survivait que les
plus favorables. C'est la sélection que tout le protocole existe pour
éviter, commise dans le fichier qui la dénonce. Le tableau rapporte
désormais la fraction de fenêtres où l'estimateur est défini.

### Ce que cette section déplace

Elle ne touche pas au théorème d'invariance et ne prédit aucun numéro. Elle
déplace une autre frontière : celle entre ce qu'il faut **mesurer** et ce
qu'il suffit de **lire**. Le dossier réclamait cent relevés pour une
décision qui n'en demande aucun, et laissait en réserve le prix d'un ticket
dont dépend la seule règle qui décide s'il faut jouer.

**Registre : inchangé.** Comme `h1`, `h14` et `h17`, `h25` ne teste pas
l'archive — il prouve et il corrige.

## 37. La règle du bonus : ce que l'archive ne peut pas dire (`h22_bonus_ordre.py`)

§32 a laissé une question ouverte et l'a formulée en une ligne : le bonus
étant une désignation de l'une des vingt boules, suit-il une règle de
POSITION dans l'ordre de sortie — « la dernière », convention la plus
répandue — ou est-ce un choix uniforme parmi les vingt ? La mesure directe
demande des tirages ordonnés ; `draws_ordered.csv` en a cinq, sans colonne
bonus, et l'archive de 70 560 tirages est triée sur ses 70 560 lignes. Elle
s'arrête à 1 380 173, les tirages ordonnés commencent à 1 381 023 : 850
tirages d'écart, aucun recoupement possible hors ligne.

Ce fichier ne force pas ce verrou. Il chiffre son épaisseur.

**Le théorème d'identifiabilité, et l'erreur de prémisse qu'il corrige.**
L'observable d'un tirage archivé est le couple (S, b) : l'ensemble trié et le
bonus qui lui appartient. Sa loi se factorise en P(S)·P(b en position j | S).
Si la loi de l'ordre est échangeable conditionnellement à l'ensemble — les
20! ordres équiprobables — ce second facteur vaut **1/20 exactement**, pour
toute position. Les deux hypothèses produisent alors la même loi sur (S, b)
et AUCUNE statistique ne peut les séparer sur des données triées. Ce n'est
pas un test faible, c'est une non-identifiabilité.

L'objection naturelle est que le tirage par REJET brise cette échangeabilité,
la probabilité de rejet dépendant des numéros déjà sortis. C'est l'objection
que j'avais moi-même posée en lançant ce travail, et **elle est fausse tant
que la loi de base est uniforme** : la probabilité de rejet ne dépend alors
que du NOMBRE de numéros déjà sortis, jamais de leur identité, et la suite
acceptée est une permutation uniforme. Rejet uniforme et Fisher-Yates sont la
même loi. Le fichier le vérifie plutôt que de l'affirmer, en comparant un
échantillonneur par rejet écrit littéralement à sa forme Plackett-Luce
vectorisée :

| loi de base | écart max entre les deux | corrélation |
|---|---|---|
| uniforme | 0,00173 | −0,07 |
| biaisée, rms 40 % | 0,00220 | +0,98 |

L'écart maximal ATTENDU entre deux estimations de la même loi vaut 0,00212 :
les deux échantillonneurs sont indiscernables. Et sous base uniforme, sur
400 000 tirages, P(bonus = n | n tiré) vaut 0,05000 de moyenne avec un
écart-type de 0,00073 contre 0,00069 de bruit de comptage pur.

**Ce qui rend la règle visible, et de combien.** Une loi de base NON uniforme
fait du rejet un échantillonnage successif à probabilités proportionnelles —
Plackett-Luce — et la dernière boule acceptée est celle de plus petit poids.
Sur 400 000 tirages à biais d'écart quadratique moyen 30 % :

```
P(n tiré)             = 0,25 · (1 + 0,878 · ε_n)
P(bonus = n | n tiré) = 0,05 · (1 + c_j  · ε_n)
```

avec c₁ = +0,128 pour la première boule, c₂₀ = −0,149 pour la dernière, de
signe opposé et de module comparable — les deux conventions candidates sont
aussi peu visibles l'une que l'autre — et Σc_j = 0,000, comme il se doit :
moyenner sur les positions redonne le choix uniforme. Le point qui décide :
0,88 contre 0,15. Un biais de base se voit **six fois mieux** dans les
fréquences marginales que dans la règle du bonus.

**Le test, et son null.** Contraste linéaire `T = Σ_t (w[bonus_t] − moyenne de
w sur le tirage t)`, `w` = fréquences marginales centrées, standardisé par la
variance conditionnelle : c'est le test localement le plus puissant contre
cette alternative. Null par randomisation conditionnelle — ensembles réels
conservés, bonus retiré uniformément parmi les vingt, 300 réplicats :
−0,034 ± 1,001, confirmé par un null SRS à 60 réplicats. `calibrate_perm` est
ici inutilisable, et pour la raison que sa propre documentation nomme :
permuter l'ordre des tirages laisse chaque couple (ensemble, bonus) intact,
donc `T` inchangé — le null serait vide, pas conservateur.

**La puissance, et c'est elle le résultat.** Sur les mêmes réplicats, à
N = 70 560, avec le χ² des 80 marginales pour comparaison (null simulé
60,2 ± 11,8, et non 79 ± 12,6 : la simulation retrouve d'elle-même le facteur
0,76 du §1 de l'audit) :

| ε rms | bonus, \|z\| | puissance | borne oracle | χ² marginal, z | puissance χ² |
|---|---|---|---|---|---|
| 0,000 | 0,81 | 0 % | 0,00 | −0,1 | 0 % |
| 0,005 | 0,83 | 0 % | 0,88 | 2,4 | 28 % |
| 0,010 | 0,88 | 0 % | 0,88 | 8,4 | 100 % |
| 0,050 | 2,13 | 15 % | 2,18 | 225,7 | 100 % |
| 0,100 | 4,07 | 85 % | 4,11 | 902,2 | 100 % |
| 0,400 | 15,00 | 100 % | 15,06 | 15 062,1 | 100 % |

Le témoin à ε = 0,40 est le contrôle positif : à biais massif le test se
déclenche, il n'est donc pas cassé. La colonne « borne oracle » est un test
qui CONNAÎTRAIT le biais — indisponible sur données réelles, et donc une
borne supérieure de tout test de cette famille.

**Sur l'archive : rien, et le rien est cette fois entièrement qualifié.**
`T = +1,42`, soit `z = +1,45` et `p = 0,153`. χ² marginal observé 53,6 contre
60,2 ± 11,8. Consigné sous `h22.bonus_ordre_contraste`, verdict conforme.

> Il faudrait un biais de base ε ≈ 0,077 pour que MÊME un test connaissant ce
> biais atteigne 3 σ sur la règle du bonus. À ce biais, le χ² des 80
> fréquences marginales — un test antérieur, plus sensible, et conforme —
> sortirait à **541 σ**. La fenêtre où la question serait décidable est
> fermée par une mesure déjà faite.

L'archive triée ne peut donc pas trancher la règle du bonus. Ce n'est pas une
intuition, c'est un calcul de puissance. La portée de cette borne est nommée :
elle couvre la famille Plackett-Luce, donc tout échantillonneur par rejet,
biaisé ou non, Fisher-Yates comme cas limite ; elle ne couvre pas une loi
d'ordre non échangeable construite pour laisser les marginales intactes.

**L'instrument, et son critère ASYMÉTRIQUE.** La mesure ne peut se faire que
là où l'ordre existe : dans l'app, qui le reçoit et le conserve depuis §34.
`BonusRule` rend un verdict à trois états, et les deux seuils sont calculés,
pas choisis.

*Côté règle* — une seule position discordante la réfute. Il faut donc que les
n positions coïncident toutes, et P(cela | uniforme) = 20^(1−n) passe sous le
seuil de Holm du registre (1,5·10⁻⁵) à **n = 5** : p = 6,25·10⁻⁶.

*Côté uniformité* — c'est une acceptation, elle exige une borne d'équivalence.
Une position discordante tue la règle DÉTERMINISTE en un coup, mais laisse
vivante une règle presque déterministe (« la vingtième dans 90 % des cas »),
qui vaudrait presque autant. Conclure à l'uniformité, c'est donc rejeter la
famille « ∃ j : P(position j) ≥ 1/2 » — le seuil où l'énoncé « le bonus est à
la position j » cesse d'être vrai plus souvent que faux, soit le plus faible
énoncé qui mérite encore le mot « règle ». Au plus une position peut le
vérifier : le maximum des comptages est une statistique suffisante et aucune
correction de multiplicité n'est due. Le plancher vaut **25** tirages
ordonnés (73 si l'on descend le seuil à 1/4, 557 à 1/10), et sous une
uniformité vraie le critère se déclenche à **32 tirages en médiane**, 35 au
80ᵉ centile, 38 au 95ᵉ. Témoin du critère : sous une règle « position 20 dans
90 % des cas », le verdict « uniforme » est prononcé à tort **0 fois sur
2 000**.

```
règle de position établie    n ≥ 5 et les n positions identiques
bonus uniforme parmi 20      positions non toutes identiques ET
                             P(Bin(n, 1/2) ≤ max des comptages) ≤ 1,5e-5
pas encore assez de tirages  sinon
```

L'asymétrie du critère est aussi une asymétrie de délai : cinq tirages font
vingt-cinq minutes, trente-cinq en font trois heures. La règle se prouverait
en une demi-heure, l'uniformité en une demi-journée — et ces durées ne
supposent rien du résultat, ce sont des délais de MESURE.

**Ce que l'app fait désormais.** Le bonus est conservé à côté de l'ordre pour
chaque tirage ordonné, avec rattrapage si le bonus arrive après l'ordre ; la
forensique lit le journal PERSISTÉ et non plus le seul historique en mémoire,
qui revient trié et remettait le compteur à zéro à chaque relance ; et la
carte Reconstruction affiche le verdict avec son compte. Une colonne `bonus`
vide a été ajoutée à `draws_ordered.csv` : la place est prête, aucune valeur
n'est inventée — 0 des 5 tirages ordonnés n'a son bonus.

Le neuvième test de la forensique reste le seul du dossier qui signale
l'inverse de l'habitude : ici une déviation par rapport à l'uniforme serait
une DÉCOUVERTE — 4,32 bits d'ordre par tirage sur toute l'archive — et non
une anomalie de source.

## 38. Le trou dans le flux, et la mémoire qui ne décroissait pas (`h23_trou_recence.py`)

`prediction.txt` s'ouvre sur un aveu : 849 tirages manquent entre l'archive
et les cinq relevés manuels, et la note qui le signale conclut aussitôt que
« ce trou n'invalide rien mais rend les cinq derniers tirages plus influents
qu'ils ne devraient l'être ». Aucun chiffre ne soutenait ni l'une ni l'autre
moitié de la phrase. Les deux ont été mesurées, et les deux sont fausses —
pas dans le même sens.

**La cause d'abord, parce qu'elle est simple.** Toutes les têtes pondérées
par récence décroissent par tirage ABSORBÉ, jamais par tirage écoulé : dans
`Swarm.swift` comme dans sa transcription `swarm_py.py`, un pas de
décroissance par appel d'`absorb`, et `process()` qui n'exploite jamais
l'écart des `drawNumber`. Un trou de 849 tirages est donc traité comme zéro
temps écoulé : l'état « récent » du prédicteur déployé était celui d'il y a
854 tirages — trois jours de jeu — rafraîchi de cinq.

Ce n'est pas resté une déduction. Pour une tête exponentielle de facteur `g`,
la corrélation de son champ avec l'état de fin d'archive doit valoir `g^j`
après `j` pas de décroissance, et l'état déployé la donne à `g⁵` :

| tête | corrélation mesurée | prédite à `g⁵` |
|---|---|---|
| `ewma.a` | 0,268 | 0,285 |
| `bayes.c` | 0,974 | 0,975 |
| `hawkes.a` | 0,214 | 0,222 |

là où l'état de vérité est à `g⁸⁵⁸ ≈ 0` (|corr| ≤ 0,023 partout). La
décroissance suit les absorptions. C'est le défaut.

**L'ampleur, ensuite.** La géométrie exacte du cas réel — un trou de 849,
puis cinq tirages aux écarts +849, +852, +854, +856, +857 — a été rejouée à
36 coupures dans l'archive, là où la vérité existe : le même essaim, cloné au
même état, ayant tout absorbé sans trou.

| métrique (déployé contre vérité) | médiane | [min ; max] |
|---|---|---|
| top-20 commun (identité 20, indépendance 5,0000 exacte) | **10/20** | [5 ; 14] |
| rho de Spearman sur les 80 numéros | **0,455** | [0,218 ; 0,711] |
| déplacement moyen de rang | 17,8 | [13,1 ; 22,0] |
| variation totale des poids AdaHedge | 0,082 | [0,016 ; 0,150] |

Les témoins situent ces chiffres. Un trou de zéro donne l'identité exacte —
20/20, rho = 1, TV = 0 sur les 36 coupures, assertion dans le code :
l'appareillage ne fabrique rien. Deux top-20 indépendants se recouvrent à
5,0000 par théorème. Et un trou de 849 suivi de 849 tirages RÉELS donne
18/20 et rho 0,961 : dès que les données reviennent, le gel devient presque
invisible. Le déployé, à 10/20, est à mi-chemin de la décorrélation totale.

« N'invalide rien » reste vrai au seul sens que l'invariance garantit de
toute façon — 5,0000 hits espérés pour ce top-20 comme pour tout autre. Mais
la note parlait de l'état des têtes, et là, la moitié de ce que l'app
affichait n'était pas ce que l'appareil informé aurait affiché.

**La seconde moitié de la note est fausse aussi, et c'est la partie
instructive.** Les cinq relevés ne sont PAS « plus influents qu'ils ne
devraient » : absorber cinq tirages déplace le top-20 de 8,0 numéros en
médiane dans l'état gelé, contre 8,0 dûs dans l'état de vérité — écart des
médianes **+0,0**. L'influence d'une absorption ne dépend pas de ce que
l'état croit du temps. Le poids excédentaire est ailleurs : ce sont les 849
derniers tirages d'archive, gelés à leur poids de récence plein, qui
impersonnent les 849 manquants. Le diagnostic de la note visait les cinq
vrais tirages ; le coupable était 849 faux.

L'erreur symétrique a été commise en cours de route et mérite d'être dite :
la première lecture du témoin « trou + 849 tirages réels » avait fait écrire
que le dégât venait « du trou, pas du petit nombre de relevés ». C'est la
conjonction des deux qui coûte, et la lecture a été récrite quand les 36
coupures l'ont montré.

**La correction, et ce qu'elle rend.** Chaque tête expose désormais
`advance(k)` — k tirages écoulés sans observation — et `run`/`predict_next`
acceptent les numéros de tirage : décroissance par tirage ÉCOULÉ, en forme
fermée pour les états linéaires (absorption de l'espérance du tirage non
observé), compteurs d'écart avancés du temps écoulé, état conditionné à
l'identité des derniers tirages déclaré perdu. Sans trou, les sorties sont
identiques au bit près — vérifié contre les hashes du champ, des poids et du
top-20 archivé dans `prediction.txt`.

Sur les mêmes 36 coupures : top-20 commun **12/20** [8 ; 16], soit **+2,0
numéros**, et rho **0,630**, soit **+0,174** ; le déplacement de rang retombe
de 17,8 à 14,85.

Ce que la correction ne rend pas, elle ne pouvait pas le rendre :
l'information des 849 tirages non vus — le résiduel de 12 à 20 —, et les
poids AdaHedge, qui manquent d'évaluations et non de décroissance (TV 0,083
contre 0,082, inchangée). L'état corrigé ne converge pas vers la vérité ; il
converge vers « la vérité moins ce qui n'a pas été vu », ce qui est le
maximum atteignable sans les données. Sur le cas réel, le top-20 corrigé du
tirage 1 381 032 ne garde que **11 des 20 numéros affichés** (rho 0,705).
Les deux valent exactement 5,0000 hits — la différence est que l'un sort d'un
essaim qui sait qu'il n'a pas vu trois jours de tirages.

**Et le correctif est désormais câblé côté Swift.** `SwarmHead` porte
`advance(_ elapsed: Int)`, les **quinze** classes de têtes l'implémentent, et
`SwarmEngine.process()` calcule `hole = drawNumber − lastDrawNumber − 1` en
tête de boucle, avant l'évaluation comme avant l'absorption. Chaque formule
est celle que `swarm_py` porte déjà et que les 36 coupures ont validée :
forme fermée pour Bayes, EWMA, Hawkes, ACP et les deux pressions ; `gap +=
elapsed` pour Weibull, Hazard et GapZ ; file de `SpectralHead` portée en
vecteurs pour qu'un tirage espéré fractionnaire y entre comme un tirage
observé ; et abstention déclarée pour Markov, Streak, Copair et Adjacency,
dont le conditionnement porte sur l'identité du tirage précédent, lequel
n'existe plus après un trou.

Vérifications passées : `verif_swift.py` rend **0 nœud de syntaxe invalide
introduit** ; `verif_logique.py` rend le verdict complet satisfait ; les
quinze conformités au protocole sont énumérées et aucune n'est sans
`advance`. Et la propriété qui rend le câblage sûr est celle que `h23` avait
établie en Python : **sans trou, la sortie est inchangée** — `hole` vaut 0
sur des tirages consécutifs, et le jeu d'essai des tests Swift est
précisément consécutif (`drawNumber: 10_000 + i`), donc leurs assertions
portent sur un comportement identique au bit près.

**Limites nommées.** La « vérité » de l'expérience est l'état informé, pas un
état optimal : le principe « absorber l'espérance » est un choix honnête
parmi d'autres, pas un théorème. Les compteurs d'écart corrigés mesurent
l'absence depuis la dernière sortie OBSERVÉE, bornée par ce qui est
connaissable. Markov et le voisinage s'abstiennent après un trou plutôt que
d'inventer un conditionnement. Et rien de tout ceci ne touche à l'espérance
de hits, dans un sens comme dans l'autre : c'est un dégât de fidélité de
l'appareil, pas de valeur de la grille — la valeur, elle, est plafonnée par
le théorème, trou ou pas.

**Au passage, un écart entre §31 et l'écran, constaté en lecture seule.**
§31 démontre que le boost abaisse le seuil de bascule d'un facteur B
(favorable dès `J ≥ S/B`, gain conditionnel `B·α`). L'app n'en tient compte
nulle part : `JackpotLaw.threshold` rend `1/p = S` sans paramètre boost, la
fraction favorable et le gain conditionnel (`edge = mean/seuil`) sont
calculés contre `S`, et `GridsView` affiche `J·p` en basculant à 100 ct/CHF.
Or `LivePayload.nextBoost` porte le boost du tirage ouvert quand l'API
l'expose, et l'instrument OpenBoost mesure justement cette exposition.

**Mais il faut dire dans quel sens l'écran se trompe, et ce n'est pas celui
qu'on croit.** Le boost vaut `B ≥ 1` et multiplie le gain, donc le gain réel
est supérieur ou égal à `B·J·p ≥ J·p`. La condition affichée reste donc une
condition SUFFISANTE valide, exactement comme au §5 bis : elle est
conservatrice, pas fausse. L'app manque des tirages favorables ; elle n'en
annonce jamais un qui ne le serait pas.

C'est la bonne asymétrie pour ce produit, et c'est pourquoi rien n'a été
câblé ici. Afficher `B·J·p` ferait basculer l'écran en « favorable » sur la
foi d'une hypothèse que §31 nomme comme non vérifiée — que le boost
multiplie aussi la cagnotte progressive. Le dossier entier existe pour
empêcher l'app d'affirmer ce qu'elle ne sait pas ; gagner quelques occasions
au prix d'une annonce non fondée serait précisément l'échange qu'il refuse.
Ce qui manque pour trancher n'est pas du code, c'est l'observation que
l'instrument OpenBoost est déjà là pour faire.

**Registre : 118 tests, zéro significatif.** `h23` consigne trois mesures
sans p-valeur — `h23.gel` (10,0/20), `h23.influence` (8,0 contre 8,0 dûs,
hypothèse de la note réfutée) et `h23.correction` (+2,0, adoptée). Comme
`h1`, `h14`, `h17` et `h25`, il ne teste pas l'archive : il mesure
l'appareil, et il corrige.

## 39. Les familles hors récurrence affine — l'instrument est fait, le balayage ne l'est pas (`tools/sweep_modern.c`)

§34 nomme lui-même sa limite : « un générateur dont l'état ne suit aucune
récurrence affine ». La formule est juste, mais elle range dans le même sac
deux choses qu'il faut séparer.

Il y a ce qui est **hors de portée du calcul** — une source matérielle, un
chiffrement à clé de 256 bits, un état de 19 937 bits. Aucune analyse de
sorties publiques ne le tranchera, et §34 a raison de le dire.

Et il y a ce qui n'est hors du cadre affine que par sa *récurrence*, tout en
restant **amorcé par un entier de 32 bits**. Un générateur à compteur, une
construction ARX, un mélangeur non linéaire : le balayage de graines ne
demande rien à la structure de l'état, seulement que l'espace des amorçages
soit énumérable. Le pas est plus cher — un bloc ChaCha20 coûte vingt tours là
où un LCG coûte une multiplication — et c'est tout. Ces familles-là n'avaient
jamais été incluses, non par choix mais par omission : `sweep_order` s'était
arrêté aux douze familles qu'on rencontre en lisant du code de loterie.

`sweep_modern` en ajoute quarante, contre les quatre échantillonneurs de
`sweep_order` repris sans modification, sur l'ordre de sortie et sans
confirmation : Philox4x32-10 et ThreeFry4x32-20 (clé = graine, compteur =
graine), ChaCha8/12/20 sous deux amorçages dont le `seed_from_u64` de
`rand_core` — celui de `StdRng` en Rust —, sfc64, jsf64, jsf32, wyrand,
romuTrio, romuDuoJr, xoshiro256+ et xoshiro256++, pcg32 et pcg64 à flux non
par défaut avec l'amorçage officiel `srandom`.

**Trois conventions de troncature, et c'est l'angle mort qui rendrait un zéro
faux.** `sweep_order` prend systématiquement les 32 bits de poids fort d'un
générateur 64 bits. C'est une convention, pas une loi. Or `rng() % 80`,
`(uint32_t)rng() % 80` et `(rng() >> 32) % 80` sont **trois générateurs
différents** du point de vue du balayage : une graine juste sous l'une meurt
au premier numéro sous les deux autres. Les neuf familles 64 bits sont donc
présentes trois fois — poids fort, poids faible, et mot natif.

**Le piège de la borne 64** que §34 documente pour `nextInt` ne se présente
pas ici : aucun des quatre échantillonneurs ne traite les puissances de deux
à part, `u % m` et `(u·m) >> w` s'appliquent uniformément, m = 64 au
dix-septième pas compris. Il est évité par construction et non par vigilance.

### Ce qui est acquis : l'instrument

La leçon la plus chère de §34 — la transcription fausse du `_randbelow` de
CPython, qui divergeait pile sur n = 64 au dix-septième numéro — dit qu'un
autotest interne ne prouve que la cohérence du programme avec lui-même.
Chaque flux est donc confronté à une référence **extérieure au programme**.

| | résultat |
|---|---|
| Philox4x32 (7 et 10 tours) contre le `kat_vectors` officiel de Random123 | 4 vecteurs, 0 écart |
| ThreeFry4x32 (13, 20 et 72 tours), même fichier | 5 vecteurs, 0 écart |
| ChaCha20 contre la RFC 8439 §2.3.2 | 3 vecteurs, 0 écart |
| splitmix64, xoshiro256+ et xoshiro256++ contre les valeurs de Vigna | 0 écart |
| romuDuoJr, wyrand, pcg32 contre le code des auteurs, compilé | 0 écart |
| **les quarante familles, graine 1234567**, contre `rand_chacha` 0.3 et `rand_xoshiro` 0.6 compilées, `randomgen` 2.3 et `pcg-c-basic` compilé | 0 écart |
| **total `--kat`** | **62/62** |
| `--selftest` : chaque combinaison retrouve son témoin | **160/160**, avec **exactement une** graine compatible |
| contrôle positif en ligne de commande, témoin en **haut** de plage (4 294 967 290) | **4/4** |

Le filtre d'ordre donne à ces chiffres leur sens : 1/80 par pas, soit une
probabilité qu'une graine fausse survive de (80!/60!)⁻¹ = 1,2·10⁻³⁷. Sur 2³²
graines et 160 combinaisons, le nombre attendu de faux positifs vaut
8·10⁻²⁶ — toute touche serait réelle, et aucune confirmation ne serait
nécessaire.

### Ce qui n'est pas acquis : le balayage

Il faut le dire sans détour, parce que c'est la moitié du travail et qu'elle
n'est pas faite. Le balayage a été **lancé** sur le tirage 1381023 pour les
familles 0-30 sur [0, 2³²). Il est **partiel**. Les familles 31-39 et les
quatre autres tirages ordonnés n'ont pas été balayés.

Le seul chiffre citable est donc daté et fractionnaire : au 30 août 2026 à
17 h 40 UTC, six des trente et une familles du tirage 1381023 étaient closes,
**zéro graine compatible** sur les vingt-quatre combinaisons correspondantes.

**Ce zéro ne conclut rien.** Six familles sur trente et une, un tirage sur
cinq : c'est une fraction d'un plan d'expérience, pas une réfutation. Un
« rien trouvé » n'a de portée que si l'on peut dire exactement sur quoi il a
porté. Le dimensionnement, lui, est mesuré : 2²⁴ graines × 31 familles en
7,55 s d'horloge sur quatre cœurs (3,8× de rendement parallèle), soit ≈ 40
min par tirage pour les quarante familles et ≈ 3 h 20 pour les cinq. Le
calcul se reprendra ailleurs ; l'espace se découpe en tranches `[lo, hi)`
sans communication, et chaque tirage se traite séparément — c'est le
protocole, pas une commodité.

### Deux erreurs, et pourquoi elles méritent d'être écrites

**La première a failli faire balayer le mauvais générateur.** Le premier
recoupement de Philox contre `randomgen` a échoué — mais de quatre mots
exactement : le flux du programme, décalé d'un bloc, redonnait celui de
`randomgen`. La raison est que numpy et `randomgen` **incrémentent le
compteur avant** de produire un bloc, si bien que leur premier bloc est celui
d'indice 1 au sens de Random123. Le fichier `kat_vectors`, qui fixe le bloc
0, a tranché : c'est le programme qui suit la convention de l'article. Sans
référence *publiée*, la correction évidente aurait été d'aligner le programme
sur `randomgen` — et le balayage aurait alors porté, en silence, sur un
générateur décalé d'un bloc. C'est exactement la panne du `_randbelow`, à un
autre endroit.

**La seconde était une non-concordance entre le code et sa documentation, et
c'est la plus instructive.** Les neuf familles en mode natif 64 bits ont été
écrites, compilées et validées — mais dans une copie de travail gardée hors
du dépôt pour ne pas remplacer le binaire sous un balayage déjà lancé. La
documentation, elle, a été rédigée d'après la copie de travail. Pendant un
moment, la source du dépôt rendait `--kat` 53/53, `--selftest` 124/124 et
trente et une familles, tandis que la page en annonçait 62, 160 et quarante.
Rien de faux n'avait été mesuré : les 62 et les 160 avaient bien été
observés, sur un binaire qui n'était pas celui du dépôt. C'est ce qui rend
l'écart dangereux — il ne se voit pas en relisant les chiffres, seulement en
recompilant, et c'est en recompilant qu'il a été vu. La correction a consisté
à installer la source complète, à remplacer le binaire par `mv` (une écriture
directe échoue avec `ETXTBSY` sur un exécutable en cours), puis à
revérifier : 62/62, 160/160, familles 0 à 39.

> La règle qu'on en tire vaut pour tout le dossier : **un « rien trouvé » ne
> vaut que si le binaire qui l'a produit est celui que la source
> reconstruit.** Chaque campagne doit donc dire quel binaire a couvert quoi.

### Ce que cette section laisse ouvert

Outre le balayage lui-même : les graines de plus de 32 bits non dérivées
d'une horloge (`ChaCha20Rng::from_entropy()` reste entier) ; les fenêtres
d'horloge en millisecondes et en nanosecondes, que §34 avait balayées pour
les douze familles de `sweep_order` mais qui ne le sont pas ici, faute
d'horodatage des cinq tirages dans le dossier — `draws_ordered.csv` ne porte
que l'identifiant et la source ; les échantillonneurs que ce programme ne
connaît pas, dont celui par flottant et celui à quatre-vingts clés ; les flux
autres que les trois testés pour pcg32 et pcg64, sur 2⁶³ et 2¹²⁷ possibles,
et ChaCha à nonce non nul. Et, inchangé depuis §34, un générateur dont l'état
est hors de portée du calcul. C'est le cas le plus probable pour un opérateur
certifié, et c'est la vraie borne du dossier.

Ce que cette section ajoute n'est donc pas un zéro de plus. C'est un
instrument dont chaque flux est vérifié contre l'extérieur, dont chaque
combinaison sait retrouver son propre témoin avec exactement une graine, et
dont le périmètre est écrit — y compris là où il est vide.

## 40. Le couplage quadratique, et le plafond qui manquait (`h24_couplage_quadratique.py`)

Le §3 quater lègue une phrase à laquelle personne n'avait répondu : « une
dépendance **non linéaire** du tirage complet reste non bornée ». Le §20 a
répondu par trois angles — la forme de la loi du recouvrement, l'information
mutuelle entre recouvrements successifs, un gradient boosting sur six traits
agrégés — et les trois réduisent le tirage à **un scalaire** avant de
regarder quoi que ce soit. Un nombre, là où le tirage en porte 61,6 bits. La
famille « non linéaire du tirage complet » était donc restée exactement aussi
ouverte qu'avant, et — c'est le point qui décide — **sans aucun test, elle
n'avait aucun plafond**. Ni `c0` (marginal), ni `c1` (linéaire au lag 1), ni
`d2` (le même, sur 306 décalages) ne la touchent.

Le premier terme non linéaire du développement est le seul qui reste
calculable sur 70 560 tirages :

```
P(n ∈ D_{t+1} | D_t) = 1/4 + Σ_{i<j} M2[n,(i,j)] · r_ij(D_t)
```

où `r_ij` est l'indicatrice « i ET j sortis en t », **débarrassée de sa part
linéaire**. 80 × 3 160 = **252 800 paramètres**, contre 6 400 pour `c1`. La
question n'est pas « une paire appelle-t-elle un numéro ? » — un tel biais
laisse une trace linéaire que `c1` verrait — mais : reste-t-il une dépendance
aux paires **une fois retirée toute la dépendance aux numéros** ? La
projection est refaite avec la covariance empirique de chaque archive à
laquelle on l'applique, réelle, simulée ou contaminée : aucune constante
tabulée n'entre dans la statistique.

Trois statistiques, une par régime de défaut : **Q1**, la somme des carrés
des 252 800 corrélations partielles (structure diffuse) ; **Q2**, leur
maximum, avec la multiplicité **dans** la loi du max et non corrigée après
coup (règle forte et isolée) ; **Q3**, la somme des carrés restreinte aux
6 320 cellules où le numéro appelé est l'un des deux membres de la paire — la
« rémanence quadratique », le cas physiquement naturel, et un sous-espace
40 fois plus petit donc 6,1 fois plus sensible (mesuré : 719 contre 118
d'écart-type).

**Un cadeau de l'arithmétique, qui change le statut du témoin.** La
contamination module le logit d'un numéro par `v(D_t)`, valant +1 si les deux
membres de la paire source sont sortis, −γ si un seul, +δ si aucun. En
résolvant `E[v] = 0` et `Cov(v, x_i) = 0` en rationnels — P₂ = 19/316,
P₁ = 120/316, P₀ = 177/316 — on trouve γ = 19/60 et δ = 19/177. Et il se
trouve que `Cov(v, x_k) = 0` **aussi pour les 78 autres numéros** :
[6840 − (19/60)·45600 + (19/177)·70800]/492960 = 0/492960, exactement. La
contamination n'a donc **aucune composante** dans la famille que `c1` et `d2`
bornent — pas « peu visible », strictement orthogonale. La disjonction des
familles est démontrée avant d'être mesurée, et mesurée ensuite : sur les
neuf points de contamination, `T1` reste dans [−0,63 ; +1,11], `T2` dans
[−0,55 ; +0,44], `S1` dans [−0,60 ; +0,55], pendant que Q1 monte à +4,5 et Q3
à +16,2.

**Sur l'archive réelle : rien.** Null simulé sur 400 archives SRS complètes.

| | observé | null simulé | z | p |
|---|---|---|---|---|
| Q1 Σ Z² (252 800 cellules) | 252 193,49 | 252 773,90 ± 719,03 | **−0,81** | 0,4165 |
| Q2 max \|Z\| | 4,6577 | 4,70093 ± 0,24286 | **−0,18** | 0,8703 |
| Q3 Σ Z² (6 320, n ∈ {i,j}) | 6 492,59 | 6 325,74 ± 118,50 | **+1,41** | 0,1372 |

Deux des trois maxima sont **sous** leur null. La cellule la plus déviante de
l'archive — le numéro 4 appelé par la paire (16, 44) — sort à Z = +4,658
contre une loi du max à 4,70 ± 0,24 : elle est *en dessous* de ce que 252 800
cellules produisent d'ordinaire. Et le décompte des queues suit : 19 cellules
au-delà de 4 σ pour 16,0 attendues, **681** au-delà de 3 σ pour 683.

La chasse à l'artefact — moitiés, huitièmes, placebo par permutation — n'a
pas été déclenchée : le plus grand |z| des trois vaut 1,41, sous le seuil de
3 déclaré au pré-enregistrement. Le bloc est écrit et validé sur une archive
délibérément contaminée (moitiés +2,61 et +2,21, `calibrate_perm` z = +5,34
contre +5,30 en SRS) ; il n'avait simplement pas lieu de tourner, et le dire
fait partie du protocole — une chasse lancée après coup sur un z ordinaire
fabrique des sous-groupes à volonté.

**Trois contre-épreuves que ce fichier se devait de passer.** `T1`, `T2` et
`S1` y sont recodés depuis zéro, et retombent exactement sur les valeurs
publiées : recouvrement lag-1 **5,00191** contre 5,00191 (`c1`), ‖Ĉ‖²_F
**3,160·10⁻³** contre 3,164·10⁻³ (`c1`), forme de la loi de O **30,29198**
contre 30,292 (`d3`, `f1`). Si l'un des trois avait bougé, c'est le montage
d'ici qu'il aurait fallu suspecter avant les résultats.

**Le plafond, enfin — et il déplace un chiffre du sommaire.** Même question
que `c0` et `c1`, même convention (le plus gros biais dont la puissance de
détection reste sous 50 % au seuil du registre), structure balayée et non
supposée : 2 familles × 3 tailles × 3 densités × 4 amplitudes, puis re-mesure
à l'enveloppe sur 12 archives.

| famille de biais | test qui la borne | plafond |
|---|---|---|
| rémanence uniforme | recouvrement moyen (`c1`) | +0,53 % |
| marginal | χ² sur 80 cases (`c0`) | +1,33 % |
| paires cachées (linéaire lag-1) | ‖Ĉ‖²_F sur 6 400 (`c1`) | +3,21 % |
| linéaire, lags 1 à 306 | le même, balayé (`d2`) | +3,46 % |
| **quadratique lag-1** | **Q1/Q2/Q3 sur 252 800 (`h24`)** | **+6,27 %** |

L'enveloppe est atteinte à 80 numéros modulés par 2 paires sources chacun,
θ = 0,080 : **+0,1567 ± 0,0008 hits sur 2,50**, puissance mesurée **17 %**.
Le §3 quater annonçait « le plafond de la piste A est donc +3,21 % » et le
§19 le portait à +3,46 % ; ces deux chiffres bornent les familles
**linéaires**, et il faut désormais lire le plafond de la piste A comme
**+6,27 %** — pas parce qu'un signal a été trouvé, mais parce qu'une famille
qui n'avait pas de borne en a une. La comparaison qui compte ne bouge pas :
l'avantage de la maison reste de −25 à −35 %.

**La courbe de sensibilité, par famille.**

| θ | avantage du joueur omniscient | Q1 | Q2 | Q3 | détection |
|---|---|---|---|---|---|
| tiers 0,05 | +3,96 % | +1,2 | +1,6 | −0,3 | 0 % |
| tiers 0,08 | +6,21 % | +2,2 | +5,8 | −1,0 | 0 % |
| tiers 0,10 | +7,81 % | +4,5 | +9,4 | −0,3 | **83 %** |
| membre 0,04 | +2,68 % | +0,8 | — | **+4,6** | **83 %** |
| membre 0,05 | +3,20 % | +1,7 | — | **+6,3** | **100 %** |

Et les trois statistiques voient bien trois choses différentes, ce qui est la
seule justification d'en dépenser trois au registre : à nombre de cellules
touchées décroissant et amplitude compensée, une règle **unique** sort à
|Z| = 17,5 — franche pour Q2 (+52,6 σ), invisible pour Q1 (+0,6 σ, parce que
306 de plus sur une somme d'écart-type 719 n'est rien) ; réciproquement
160 règles faibles allument Q1 et laissent Q2 dans sa loi du maximum ; et Q3
reste **exactement à zéro** sur la famille « tiers », par construction.

**Ce que j'ai eu tort d'écrire, et que la mesure a corrigé.** Trois fois.
D'abord, la première version n'avait qu'une famille de contamination, celle
où la paire appelle un numéro tiers — et Q3, dont c'est précisément le
sous-espace complémentaire, y mesurait **0 % de puissance à tous les
points**. Un test dont aucun témoin ne se déclenche est indistinguable d'un
test cassé : c'est la règle n° 4 du labo, enfreinte en croyant la respecter
parce que *les autres* statistiques, elles, se déclenchaient. La famille
« membre » a été ajoutée pour cela. Ensuite, sur 30 réplicats de mise au
point, l'écart-type simulé de Q1 valait 0,934 fois la valeur d'indépendance
et celui de Q3 1,206 fois, d'où une phrase sur une loi tabulée qui
« mentirait dans les deux sens » ; à 400 réplicats les ratios valent **1,011
et 1,054**, et la phrase était fausse. La voici dans le bon sens : **ici, la
table n'aurait presque pas menti** — retirer la part linéaire décorrèle
largement les cellules — là où `d1` mesurait 12 749 contre 4 354 sur son
agrégat mod 2. C'est une des rares fois de ce dossier où la règle n° 1
n'attrape rien, et cela se dit aussi : elle reste le seul moyen de l'avoir
**su**, et la loi du maximum de Q2 n'a de toute façon aucune forme tabulée
utilisable sur 252 800 cellules dépendantes. Enfin, le sous-bloc Q3 avait été
annoncé « 4 fois plus sensible » sur une racine mal prise : c'est √40 ≈ 6,
mesuré à 6,1. Les trois phrases sont désormais **calculées depuis le null**
dans le script, pour qu'aucune exécution future ne puisse les rendre fausses.

Détail d'exécution qui n'en est pas un : le noyau est fait de 160 petits
produits de Gram (80×80 en sortie). Mesuré, **0,45 s en mono-thread contre
1,0 à 9,0 s en multi-thread** — la synchronisation coûte plus que le calcul à
cette forme de matrice, et le pire cas est erratique. Le run complet tient en
17 minutes.

**Limites déclarées.** (1) Lag 1 seulement ; `d2` a montré que balayer
306 décalages coûte ~5 % sur la borne, et le coût serait le même ici, mais
306 nulls complets dépassent le budget. (2) Le seuil du registre extrapole la
queue du null : gaussienne pour Q1 et Q3, mais **Gumbel ajusté aux moments**
pour Q2, qui est un maximum — une extrapolation gaussienne l'aurait placé à
4,33 σ au lieu de 8,21 et aurait sur-estimé la puissance. (3) Le plafond est
une borne d'**omniscience**, comme `c0` et `c1` : la pénalité
d'identification du §3 bis s'y ajouterait, et elle serait plus lourde
qu'ailleurs puisqu'il faudrait estimer 252 800 coefficients au lieu de dix
numéros. Elle n'est pas mesurée — pas plus, du reste, qu'elle ne l'est pour
les paires cachées de `c1`. (4) Le grain du balayage (4 amplitudes) laisse le
plafond légèrement conservateur. (5) Le **troisième ordre** — un triplet
appelant un numéro — reste non borné à son tour ; c'est la limite que ce
fichier lègue, avec une raison de la croire moins urgente : la dilution en
√(nombre de cellules) coûte un facteur 2,8 de plus à chaque degré.

**Registre : 122 entrées, m = 3 318, seuil de Holm 1,507·10⁻⁵, 0
significatif.** Le plus petit p du dossier reste 2,0·10⁻⁴ (`audit.paires`).

## 41. La loi qui gouverne tous les plafonds (`h30_borne_unifiee.py`)

Le dossier a accumulé cinq plafonds — le plus gros avantage qu'un biais non
détecté pourrait donner, famille par famille — mesurés séparément, par des
tests différents, et empilés dans le sommaire sans rien qui les relie :

```
rémanence uniforme   recouvrement moyen        1 direction     +0,53 %
marginal             χ² sur 80 cases              80 cases     +1,33 %
paires cachées       ‖Ĉ‖² sur 6 400            6 400 cases     +3,21 %
lags 1 à 306         le même, balayé          ~2·10⁶ cases     +3,46 %
quadratique lag-1    Q1/Q2/Q3                252 800 cases     +6,27 %
```

Le plafond monte avec la taille de la famille. Personne n'avait dit
**pourquoi**, ni selon quelle loi, ni où cela s'arrête. Et la question n'est
pas décorative : si le plafond croît vite, il suffirait de monter en ordre
pour finir par dépasser l'avantage de la maison, et la piste A ne serait pas
fermée du tout.

### Le théorème

Le cadre commun, une fois dépouillé de ce qui distingue les cinq expériences.
Une famille de biais est un espace de déviations `ε` sur `m` cellules. Deux
quantités s'y opposent, et tout tient à ce qu'elles ne sont pas du même
degré :

- l'**avantage** que le biais donne au joueur est **linéaire** en `ε` —
  cocher un numéro poussé de `ε` rapporte proportionnellement à `ε`, donc
  `A(ε) = ⟨a, ε⟩` pour un vecteur `a` propre à la famille ;
- la **détectabilité** est **quadratique** — la non-centralité d'un χ² sur
  les `m` cellules vaut `λ = N‖ε‖²`.

Sous H₀ ce χ² a pour moyenne `m` et pour écart-type `√(2m)`. Le seuil vaut
donc `m + z√(2m)`, et la puissance atteint 50 % quand `λ = z√(2m)`. **Le
budget de déviation qu'un seuil laisse passer croît donc comme `√m`** — plus
la famille est grande, plus son null est dispersé, plus un biais peut s'y
cacher. C'est le seul endroit où la taille entre, et c'est tout le résultat.
Cauchy-Schwarz donne alors :

> **Théorème du plafond unifié.**  `plafond = ‖a‖ · (2m)^{1/4} · √(z/N)`
>
> avec égalité quand `ε` est colinéaire à `a` — l'adversaire optimal aligne
> sa déviation sur ce que la grille encaisse, et rien d'autre.

Trois conséquences. Le plafond croît en **m^{1/4}** : multiplier par 10 000
la taille d'une famille ne multiplie son plafond que par 10. Il décroît en
`1/√N`, ce qui est la seule façon de le faire baisser. Et le facteur `‖a‖`
ne dépend **pas** de `m` : c'est lui, non la taille, qui distingue une
famille utile au joueur d'une famille inutile.

### Vérifié sans réutiliser aucune de ses approximations

La démonstration enchaîne trois approximations — le χ² par ses deux premiers
moments, la puissance 50 % par l'égalité des moyennes, Cauchy-Schwarz
atteint. Le plafond est donc **remesuré directement**, par bissection sur
l'amplitude, dans un modèle multinomial où tout est connu et dont le null est
simulé :

| m | null χ² simulé | ε plafond | ε · m^{−1/4} |
|---|---|---|---|
| 16 | 15,3 ± 5,65 | 0,03479 | 0,017395 |
| 64 | 63,8 ± 11,28 | 0,05017 | 0,017738 |
| 256 | 255,5 ± 21,92 | 0,06873 | 0,017181 |
| 1 024 | 1 025,4 ± 41,50 | 0,09363 | 0,016551 |
| 4 096 | 4 092,9 ± 89,34 | 0,13562 | 0,016953 |

**Exposant mesuré : +0,2413** contre +0,2500 en théorie ; la colonne
normalisée est plate à 6 % près sur deux ordres et demi de grandeur.

L'exposant est cependant **légèrement sous** la théorie, et il ne faut pas
passer dessus. Deux causes, dans le même sens : le χ² est dissymétrique à `m`
modéré, donc un seuil pris à `z` écarts-types est plus strict que ne le dit
l'égalité des moyennes ; et surtout la contamination employée — moitié `+ε`,
moitié `−ε` — est **une direction particulière, non alignée sur `a`**.
Cauchy-Schwarz n'y est donc pas atteint, et cette section mesure un
**minorant** du plafond, pas le plafond. La loi d'échelle est vérifiée ; sa
constante ne l'est pas, et ce fichier n'en a pas besoin puisqu'il ne se sert
que des **rapports**.

### Les quatre plafonds du dossier, relus par la loi

Ces nombres ont été mesurés par trois fichiers différents, avant que la loi
n'existe et sans y penser. Ils constituent donc une vérification
**indépendante** : si la loi est juste, le `‖a‖` qu'on en extrait doit être
d'ordre 1 et varier peu.

| famille | m | plafond | (2m)^{1/4} | ‖a‖ relatif |
|---|---|---|---|---|
| rémanence uniforme (`c1`) | 1 | 0,53 % | 1,19 | 1,19 |
| marginal (`c0`) | 80 | 1,33 % | 3,56 | 1,00 |
| paires cachées (`c1`) | 6 400 | 3,21 % | 10,64 | 0,81 |
| quadratique lag-1 (`h24`) | 252 800 | 6,27 % | 26,67 | 0,63 |

Les `‖a‖` vont de 1,19 à 0,63 — un facteur **1,9** là où les plafonds bruts
varient d'un facteur **11,8** —, et la décroissance est **monotone**, ce que
la construction n'imposait pas. La taille de la famille explique donc
l'essentiel ; le reste est la conversion déviation → avantage.

La rémanence uniforme est l'exception instructive : `m = 1`, une seule
direction, et c'est pour cela que son plafond est le plus bas du dossier
malgré le `‖a‖` le plus élevé. Une famille à une seule direction n'a nulle
part où se cacher — exactement ce que le §3 quater constatait sans
l'expliquer.

*(Le cinquième plafond, +3,46 % pour les lags 1 à 306, est mis de côté : ce
n'est pas une famille mais l'union balayée de 306 familles, et son plafond
inclut une correction de multiplicité qui n'entre pas dans la loi.)*

### Une prédiction falsifiable, posée avant la mesure

L'ordre 3 — un **triplet** appelant un numéro — compte `80 × C(80,3) =
6 572 800` cellules contre 252 800 pour l'ordre 2, soit un rapport de tailles
de 26,0 et un rapport de plafonds de **2,26** à `‖a‖` égal.

> **Prédiction : le plafond de l'ordre 3 vaut entre 8,9 % et 14,2 %**, la
> fourchette venant de la décroissance mesurée de `‖a‖` d'un ordre au suivant.

`h27` mesure l'ordre 3 en ce moment, par une voie qui n'a rien à voir avec
celle-ci. Si son plafond tombe hors de la fourchette, **c'est la loi qui est
fausse**, et il faudra le dire.

### Ce qui ferme la piste A — et ce n'est pas ce qu'on croyait

| ordre d | cellules `80·C(80,d)` | (2m)^{1/4} | plafond à ‖a‖ constant |
|---|---|---|---|
| 1 | 6 400 | 10,6 | 4,0 % |
| 2 | 252 800 | 26,7 | 10,0 % |
| 3 | 6 572 800 | 60,2 | 22,5 % |
| 4 | 126 526 400 | 126,1 | **47,2 %** |
| 5 | 1 923 201 280 | 249,0 | 93,1 % |

À `‖a‖` constant, la hiérarchie **franchirait l'avantage de la maison vers
l'ordre 4**. Ce serait la conclusion alarmante — si `‖a‖` était constant. Il
ne l'est pas, et c'est ici que la loi cesse d'être rassurante toute seule.

Deux freins, dont un seul est chiffré ici. Le premier est `‖a‖`, qui décroît
d'un ordre au suivant : une déviation répartie sur des cellules de plus en
plus fines se convertit de moins en moins bien en avantage, une grille de dix
numéros ne pouvant encaisser qu'un nombre borné de directions.

Le second est le décisif : la **pénalité d'identification**. Tous ces
plafonds sont des bornes d'**omniscience** — elles supposent la règle connue.
Estimer 6,5 millions de coefficients sur 70 560 tirages est sans espoir, et
le §3 bis a mesuré que même dans le cas marginal, à 80 coefficients, le
joueur ne capte que 64 % à la frontière de détection. La borne réalisable
doit donc **retomber** quand `m` grandit.

D'où la contribution réelle de cette section, qui est une prédiction double :

- le plafond d'**omniscience** croît en `m^{1/4}`, sans limite ;
- le plafond **réalisable** croît puis décroît, et il existe donc un ordre
  optimal pour l'adversaire, au-delà duquel monter en complexité le dessert.

**La piste A n'est pas fermée par la petitesse des plafonds.** Elle est
fermée par le fait qu'on ne peut pas apprendre ce qu'on a le droit de cacher.
Ce n'est pas la même affirmation, et c'est la seconde qui tient.

> **ERRATUM — la seconde puce est fausse, et `h31` la corrige.** Elle
> annonçait un plafond réalisable qui « croît puis décroît », donc un ordre
> optimal pour l'adversaire. Mesuré au §42 : il croît encore, de façon
> monotone, sur toute la plage testée. C'était une intuition présentée comme
> une prédiction, et elle n'a pas tenu une heure.
>
> La conclusion qui la remplace est plus forte et procède d'un autre
> mécanisme : le plafond réalisable croît en `m^{0,06}` au lieu de
> `m^{0,25}` — la pénalité d'identification mange 75 % de l'exposant, mais
> ne le retourne pas. Passer de 80 cellules à 126 millions ne multiplie le
> plafond réalisable que par **2,7**. La dernière phrase du paragraphe
> ci-dessus reste donc vraie ; c'est le mécanisme qui était mal nommé.

**Registre : inchangé.** `h30` ne teste pas l'archive — il démontre.

## 42. La pénalité d'identification a sa propre loi d'échelle (`h31_identification_echelle.py`)

> **Portée restreinte au §59.** La loi `m^(−1/4)` établie ici est celle des
> déviations **denses** — `h31.make_eps` tire une déviation isotrope. Pour une
> déviation creuse l'exposant **change de signe**, et les familles que le §45
> mesure sont creuses. Le §59 le démontre, le mesure, et refait le +0,0616
> de cette section comme contrôle.

Le §41 démontre que le plafond d'**omniscience** croît en `m^{1/4}`, puis
affirme — sans le démontrer — que le plafond **réalisable** « croît puis
décroît, et qu'il existe donc un ordre optimal pour l'adversaire ». Cette
seconde moitié se dérive. Elle est fausse, et sa correction donne un
résultat plus fort.

### Une coïncidence d'exposants qui n'en est pas une

Le joueur doit estimer la déviation sur les mêmes données qui servent à la
tester. Deux quantités s'affrontent alors, et toutes deux dépendent de `m` :

```
SIGNAL   la déviation qu'un seuil laisse passer   ‖ε‖² = z√(2m)/N
BRUIT    l'erreur d'estimation sur m cellules     ‖η‖² ≈ m/N

         SNR² = ‖ε‖²/‖η‖² = z√2 / √m
```

**Le rapport signal sur bruit de l'identification décroît en `m^{−1/4}` —
exactement l'exposant par lequel le plafond d'omniscience croît.** Les deux
effets se compensent au premier ordre, et ce qui décide du sens final est la
façon dont la part captée dépend du SNR : proportionnelle au SNR, le plafond
réalisable serait constant en `m` ; proportionnelle à son carré, il
décroîtrait. **Un exposant sépare « la piste A reste ouverte à tous les
ordres » de « elle se referme d'elle-même ».**

### Mesuré

Même modèle abstrait qu'au §41 pour que les deux fichiers parlent de la même
chose, avec une différence nécessaire : la déviation est tirée **isotrope**
et non en créneau `±ε`. Avec un créneau à deux valeurs le classement des
cellules serait trivial, et la part captée mesurerait la chance de
distinguer deux paquets plutôt que la difficulté d'identifier une règle. Le
joueur coche `K/m = 1/8` des cellules, pour reproduire une grille de 10
numéros sur 80.

| m | ‖ε‖ plafond | ‖η‖ estimation | SNR | SNR·m^{1/4} |
|---|---|---|---|---|
| 64 | 0,05012 | 0,05576 | 0,8989 | 2,5424 |
| 256 | 0,07263 | 0,11290 | 0,6433 | 2,5733 |
| 1 024 | 0,10005 | 0,22512 | 0,4444 | 2,5140 |
| 4 096 | 0,13716 | 0,45280 | 0,3029 | 2,4233 |

**Exposant du SNR mesuré : −0,2621** contre −0,2500 en théorie. Le bruit se
contrôle à part : `√(m/N)` vaut 0,45255 pour `m = 4096`, contre 0,45280
mesuré.

| m | SNR | part captée | plafond omniscience | plafond réalisable |
|---|---|---|---|---|
| 64 | 0,8989 | 0,664 ± 0,011 | 3,36 | 2,23 |
| 256 | 0,6433 | 0,554 ± 0,006 | 4,76 | 2,63 |
| 1 024 | 0,4444 | 0,412 ± 0,004 | 6,73 | 2,77 |
| 4 096 | 0,3029 | 0,307 ± 0,002 | 9,51 | 2,92 |

Part captée ∝ `SNR^{0,721}`, d'où un plafond **réalisable en `m^{+0,0616}`**.

### L'erratum, et pourquoi le résultat corrigé est meilleur

Le plafond réalisable **croît encore**, de façon monotone sur toute la plage.
Le §41 annonçait un retournement et un ordre optimal pour l'adversaire : il
n'y en a pas. C'était une intuition présentée comme une prédiction, et elle
n'a pas tenu une heure.

Ce qui la remplace est plus fort, et procède d'un autre mécanisme. La
pénalité d'identification mange **75 % de l'exposant** — +0,25 devient
+0,06 — sans le retourner. Conséquence, transposée aux ordres réels :

| ordre | cellules | omniscience rel. | part captée rel. | **réalisable rel.** |
|---|---|---|---|---|
| 0 | 80 | 1,00 | 1,000 | **1,000** |
| 1 | 6 400 | 2,99 | 0,454 | **1,358** |
| 2 | 252 800 | 7,50 | 0,234 | **1,756** |
| 3 | 6 572 800 | 16,93 | 0,130 | **2,205** |
| 4 | 126 526 400 | 35,46 | 0,076 | **2,711** |

Passer de 80 cellules à 126 **millions** — un facteur 1,6 million en
complexité — ne multiplie le plafond réalisable que par **2,7**. Rapporté au
seul plafond réalisable que le dossier ait mesuré sur le vrai processus
(+0,99 % pour le cas marginal, §3 bis), l'ordre 4 vaudrait environ **2,7 %**.
L'avantage de la maison est de 25 à 35 %.

> Ce n'est donc ni la petitesse des plafonds d'omniscience — le §41 montre
> qu'ils franchissent l'avantage de la maison vers l'ordre 4 — ni un
> retournement de la courbe réalisable, qui n'a pas lieu, qui ferme la piste
> A. **C'est que les deux exposants se compensent presque exactement :**
> +0,25 pour ce qu'on gagne à se cacher dans une grande famille, −0,19 pour
> ce qu'on perd à devoir l'identifier. Il reste +0,06, et 0,06 ne mène nulle
> part.

### Limites, et la troisième pourrait renverser le signe

1. Le modèle est multinomial à cellules équiprobables, pas le vrai processus
   de tirage — c'est le prix d'un modèle où le plafond est calculable
   exactement, et c'est pourquoi tout est rapporté en **relatif**.
2. L'estimateur employé est la fréquence empirique, exhaustive pour un biais
   marginal. Les familles conditionnelles demanderaient la matrice de
   couplage ; `h26` mesure ce cas-là sur le vrai processus, et si son
   exposant diffère du mien c'est **le sien qui fait foi**.
3. Le joueur estime ici sur les **mêmes** observations que celles du test.
   Un joueur réel estimerait sur le passé et jouerait sur l'avenir, ce qui
   est strictement plus dur. La part captée mesurée est donc un **majorant**,
   l'exposant +0,06 aussi — et une mesure en marche avant pourrait le rendre
   négatif, ce qui redonnerait raison au §41 pour de mauvaises raisons.

> **C'est exactement ce qui s'est produit.** Le §45 mesure la part captée
> en marche avant, sur les vraies familles, et trouve le retournement :
> 0,53 → 0,99 → 1,30 puis **0,71** au tenseur. L'erratum ci-dessus a donc
> sur-corrigé le §41, dont l'intuition était juste. La limite n° 3 avait
> nommé la faille et la limite n° 2 avait désigné l'arbitre — « si
> l'exposant de `h26` diffère du mien, c'est le sien qui fait foi ». Il
> diffère, et il fait foi.

**Registre : inchangé.** `h31` ne teste pas l'archive — il démontre.

## 43. Le plafond d'un biais transitoire (`h32_plafond_transitoire.py`)

Les §41 et §42 établissent deux lois d'échelle en `m`, la taille de la
famille. Toutes deux, comme `c0`, `c1`, `d2` et `h24` avant elles, partagent
une hypothèse que **aucune ne dit** : le biais est **stationnaire**, présent
sur les 70 560 tirages.

Le dossier avait pourtant déjà mesuré, ailleurs, qu'un défaut bref est
presque invisible — la courbe de détectabilité de la 16ᵉ voie donne
puissance 0,58 pour une corruption de 200 tirages à +40 %, et 0,00 en
dessous. Trente fois le plafond stationnaire du §3, invisible une fois sur
deux. Il y a donc un régime entier que la hiérarchie ne couvre pas.

### La dérivation

Un biais d'amplitude `‖ε‖` présent sur une fenêtre de `L` tirages sur `N` :

- **le signal se concentre** — seuls les `L` tirages de la fenêtre le
  portent, donc `λ = L‖ε‖²` et non `N‖ε‖²` ;
- **le seuil monte** — un test qui ignore où est la fenêtre doit les
  balayer toutes, soit `N/L` fenêtres, ce qui ne coûte que
  `z_eff ≈ √(z² + 2 ln(N/L))` : la **racine d'un logarithme**.

Le budget d'amplitude passe donc de `z√(2m)/N` à `z_eff√(2m)/L`, soit `N/L`
fois plus grand à un facteur logarithmique près. D'où **deux** plafonds
qu'il faut distinguer :

```
plafond PENDANT la fenêtre   ≈ √(N/L) · plafond stationnaire
plafond MOYEN sur l'archive  ≈ √(L/N) · plafond stationnaire
```

Le premier explose quand `L` diminue, le second s'effondre — et ces deux
phrases décrivent le **même** défaut.

### Vérifié par balayage, avec le null du maximum

| L | fenêtres | null du max | ‖ε‖ plafond | × √(L/N) |
|---|---|---|---|---|
| 250 | 80 | 114,0 ± 8,52 | 0,57539 | 0,06433 |
| 500 | 40 | 109,7 ± 8,51 | 0,37480 | 0,05926 |
| 1 000 | 20 | 103,9 ± 8,99 | 0,25488 | 0,05699 |
| 2 000 | 10 | 99,9 ± 9,77 | 0,18447 | 0,05834 |
| 5 000 | 4 | 91,5 ± 8,56 | 0,09937 | 0,04968 |

**Exposant mesuré : −0,5735** contre −0,5000 en théorie. L'écart est le
facteur logarithmique du balayage, absent de la loi en puissance : il vaut
1,211 à `L = 250` contre 1,071 à `L = 5 000`, et il va dans le bon sens.

### Transposé à l'archive

| L | durée réelle | plafond PENDANT | plafond MOYEN |
|---|---|---|---|
| 200 | 17 h | **25,0 %** | 0,071 % |
| 500 | 42 h | 15,8 % | 0,112 % |
| 2 000 | 7 j | 7,9 % | 0,224 % |
| 10 000 | 35 j | 3,5 % | 0,501 % |
| 70 560 | 245 j | 1,3 % | 1,330 % |

Un défaut d'une journée pourrait porter un avantage de l'ordre de **25 %
pendant cette journée** — vingt fois le plafond stationnaire — sans que rien
ne le voie.

*Précaution sur le rapprochement avec la 16ᵉ voie, faute de quoi il ferait
croire à un accord numérique inexistant : les deux « +x % » ne sont **pas**
la même quantité — celui de `a3` est une amplitude de contamination injectée,
celui-ci un avantage de joueur. Ce qui concorde est le **régime**, entre deux
voies sans rien en commun.*

### Ce qui referme le trou : l'identification, cette fois dans le temps

Le plafond « pendant » n'est pas un avantage disponible. Pour l'encaisser, le
joueur doit savoir **quels** numéros sont biaisés (le problème du §42) *et*
**quand** la fenêtre a lieu. Or le seul moyen de savoir quand est de le
détecter — et un biais au plafond n'est détecté, par définition, qu'une fois
sur deux. Mesuré sur un détecteur **causal**, qui n'a que le passé :

| L | bascule à | jamais détecté | fenêtre restante | **encaissable** |
|---|---|---|---|---|
| 250 | 0,69 | 20 % | 32 % | **4,94 %** |
| 500 | 0,65 | 20 % | 30 % | 3,57 % |
| 1 000 | 0,76 | 47 % | 24 % | 1,37 % |
| 2 000 | 0,75 | 28 % | 31 % | 1,92 % |
| 5 000 | 0,75 | 14 % | 28 % | 0,19 % |

Le détecteur bascule aux trois quarts de la fenêtre, et souvent jamais. **Le
plafond réellement encaissable retombe à 5 % au plus**, contre 25 % pour le
plafond « pendant » — un facteur 4 à 8.

> Le trou était réel et grand ; il se referme par le même mécanisme que le
> §42 — l'impossibilité d'apprendre assez vite ce qu'on a le droit de
> cacher. Ici l'apprentissage porte sur le **temps** plutôt que sur les
> numéros, et c'est la troisième fois que ce dossier bute sur la même
> frontière par une voie différente.

### Limites

0. La colonne « jamais détecté » est bruitée — 60 réplicats — d'où sa
   non-monotonie apparente. Elle établit l'**ordre de grandeur** du facteur
   d'abattement, pas sa valeur à chaque `L` : ne pas lire ses variations.
1. Le facteur logarithmique du balayage est traité comme correction et non
   intégré à la loi en puissance ; à `L` très petit il finirait par dominer.
2. La section 4 raisonne **au plafond**, où la puissance vaut 50 % par
   définition. Un biais plus fort laisserait plus de fenêtre à jouer — mais
   serait détecté, donc corrigé par l'opérateur : régime hors du cadre.
3. Le modèle suppose **une** fenêtre. Un défaut récurrent — toutes les nuits,
   par exemple — serait bien plus détectable, la 17ᵉ voie l'ayant borné par
   périodogramme à 0,01 écart-type par tirage.

**Registre : inchangé.** `h32` ne teste pas l'archive — il démontre.

## 44. La foule inconnue : ce que l'anti-foule peut prouver (`h29_partage.py`)

Le §16 laissait la troisième pierre dans un état inconfortable. L'espérance
bouge sous partage — c'est un théorème, et c'est le seul endroit du dossier
où elle bouge sans rien supposer du générateur — mais l'ampleur annoncée
(×1,77 à ×2,67) reposait sur un modèle de popularité **écrit à la main**,
jamais mesuré sur ce jeu et non mesurable, la répartition des mises n'étant
pas publiée. `h29` sort de l'impasse par le haut : que reste-t-il quand on ne
suppose **rien** de la foule ?

### Le jeu, et son théorème

Le joueur choisit une loi sur les grilles, la nature choisit la répartition
de `N` tickets adverses, le rang partagé paie `J/(1+co-gagnants)`. Le groupe
des permutations des 80 numéros laisse le tirage invariant, la garantie est
concave, et la moyenne d'orbite de toute stratégie est l'uniforme :

> **La grille uniformément aléatoire est exactement minimax.**

La clef est un lemme d'une ligne : pour une grille uniforme, `P(g ⊆ d)` est
le même pour tout tirage `d`, donc conditionner au gain **ne déforme pas le
tirage**. Le mécanisme de `h3` — « mes numéros sont déjà dans D, une foule
qui les aime a une longueur d'avance » — disparaît en moyenne, et
`E[gain] = J·p·E[1/(1+W)]` avec `D` uniforme, `p` en facteur exact. La
famine Monte-Carlo qui a piégé ce dossier trois fois est ainsi évitée **par
construction**, pas par prudence.

### La valeur, encadrée puis atteinte

La nature minimise `E[1/(1+W)]` sous `E[W] = N·p = m` : la minorante convexe
interpolée aux entiers donne la borne universelle `L(m)` (= `1 − m/2` pour
`m ≤ 1`), la foule i.i.d. uniforme donne la majorante exacte, et l'écart est
`≤ m²/6`.

Dans un jeu réduit — 8 numéros, 3 tirés, grilles de 2, foule de 3 — les 4 060
foules énumérées donnent la valeur **exactement** à la prédiction
pré-enregistrée `p·L(3p) = 141/1568`, atteinte par les foules en triples
disjoints : *la nature optimale étale, elle aussi*.

*Recoupé indépendamment pour ce rapport, en arithmétique de fractions
exactes et par une énumération écrite à part : `p = 3/28`, garantie minimax
de l'uniforme `= 141/1568` au chiffre près, foule optimale `{01, 23, 45}`,
disjointe. Deux implémentations sans rien en commun tombent sur la même
fraction.*

Et une grille **déterministe**, furtive comprise, n'a pour garantie que
`J·p/(1+N)` : la nature pose ses `N` tickets dessus. **Le pire cas ne lit pas
les numéros ; il lit la prévisibilité.** « Éviter la foule » n'est pas
prouvable — « être imprévisible » l'est, et vaut un facteur `(1+N)·v(N)` de
garantie, soit ×88 681 à la mise 10 pour `N ≈ 9·10⁴`.

### Ce qui survit au pire cas, et ce qui n'y survit pas

Pour un portefeuille, la symétrisation laisse un degré de liberté : le
**motif de recouvrements**, tiré ensuite par permutation uniforme privée. Sur
les 4 060 foules du jeu réduit, `disjoint ≥ chevauchant ≥ doublon` **point
par point** (marges +0,014 et +0,070). La géométrie de `h13` traverse donc le
minimax mot pour mot ; le choix des numéros, non.

> **Corollaire produit, et il est sévère.** Une carte anti-foule **publiée**
> — la même grille furtive servie à tous les utilisateurs — fabrique le
> doublon massif qu'elle prétend fuir. Seule la rotation privée est immunisée.

Et parmi les foules i.i.d., la pire est la foule **uniforme** (par convexité) :
tout biais psychologique — dates, chiffre 7 — ne peut qu'**aider** le joueur
uniformisé, qui l'encaisse sans avoir à le modéliser.

### Ce que chaque connaissance achète

Pour le joueur uniformisé, la moyenne `m` seule encadre le multiplicateur de
partage dans `[L(m), ≈1)` ; la **fréquence de chute `q` seule** l'encadre
dans `(1−q, 1−q/2]`. Tout ce que la répartition de la foule peut encore
jouer pèse donc **moins de `q/2`** — au régime que le §29 estime (λ ≈ 0,01),
moins d'un demi pour cent.

Et le rang plein, le seul qui porte une grosse cagnotte, est précisément
celui où `q` est petit : **la promesse anti-foule s'effondre exactement là où
l'argent est.** Le reste — la place dans la fourchette, jusqu'au *signe* de
« furtive bat populaire » — exige la répartition. Sous le modèle de `h3`
(illustration étiquetée comme telle, recoupée à ses nombres publiés : λ 2,66
contre 2,7 ; ×1,81 contre ×1,77 ; ×2,78 contre ×2,67), la rotation capte
**73 %** de l'avantage modélisé, en logarithme, **sans le modèle**.

### L'observable, honnêtement

`q ≈ N·p` (§29) est le cas sans agglutination d'une identité générale :
`q ≤ N·p`, et l'écart `γ = N·p/q = E[gagnants | chute]` est le premier indice
de concentration de la foule qui soit **observable**. Comme `μ·p/c = α·γ`,
cela offre au `α̂ = 29,5 %` « anormalement généreux » du §29 une **quatrième
explication** qui ne contredit aucune des trois autres.

Mais l'unique relevé ne contraint rien : les cinq `μ̂·p` s'étalent de ×7,85,
**plus serré que la médiane du pur bruit** (cinq exponentielles i.i.d.
simulées : ×14,5 ; `p = 0,57`). Puissance mesurée : une agglutination ×8 est
invisible sur un relevé (9 %), vue à ~10 relevés (99,9 %) ; ×3 à une
trentaine. C'est la série que le §28 réclame déjà, avec un dividende de plus :
les chutes comptées donnent `q̂`, donc `N ≥ q̂/p` **sans aucune hypothèse de
répartition**.

### Ce qui a été consigné, et l'entorse

Quatre lignes au registre. Le test de cohérence est la seule à porter un `p`,
et sa statistique a été **prototypée avant le scellement du jeton** — entorse
à la règle n° 2, signalée dans les notes du registre, et de valeur
confirmatoire nulle de toute façon. Deux autres erreurs corrigées en route :
un témoin négatif qui ne pouvait pas sonner (une « fausse » borne qui était
vraie), et une dominance d'abord affirmée « aux co-gains près » quand la
preuve point par point était plus simple.

### Réserve, et la conclusion pour la carte « Furtif »

Rien ici ne prédit un numéro, et l'invariance sort **renforcée** : c'est le
lemme d'uniformité qui rend la garantie calculable. Le régime du barème et le
prix du ticket restent inconnus.

La carte devrait devenir une **rotation scellée** : garder la construction
de `h13`, lui appliquer une permutation uniforme des 80 numéros tirée en
privé, et reléguer le penchant anti-dates au rang de pari conditionnel qu'il
a toujours été. Le conditionnel du §9 n'était pas un pis-aller — c'était le
théorème qui manquait.

### La tension avec le théorème G, que cette recommandation ne peut pas trancher seule

Il faut cependant dire ce que `h29` ne dit pas, car sa conclusion heurte un
autre théorème du dossier. Une permutation uniforme des 80 numéros **détruit
le classement de l'essaim** : c'est le prix littéral de l'imprévisibilité.
Or le théorème G — l'assurance gratuite — établit que suivre l'essaim ne
coûte **rien** sous H₀ et capterait un biais des familles bornées s'il en
apparaissait un.

Les deux théorèmes sont justes et ils tirent en sens opposés :

| | ce qu'on gagne | ce qu'on perd |
|---|---|---|
| **rotation uniforme** | la garantie minimax sous partage | la capture d'un biais éventuel |
| **classement de l'essaim** | la capture d'un biais éventuel | la garantie minimax |

L'arbitrage dépend d'une quantité que le dossier n'a **pas** mesurée et ne
peut pas mesurer hors ligne : à quel point les grilles des utilisateurs de
l'app seraient corrélées à celles de la foule. Si l'app reste confidentielle,
le pire cas de `h29` — la foule entière posée sur la grille publiée — est une
fiction, et l'assurance gratuite l'emporte. Si l'app était massivement
suivie, elle **deviendrait** la foule, et la rotation l'emporterait.

Deux remarques pour cadrer la décision sans la prendre. D'une part la valeur
de l'assurance gratuite est bornée par le plafond réalisable du §42 — de
l'ordre du pour cent, et 39 voies n'ont rien trouvé qu'elle puisse capter.
D'autre part le gain minimax n'est un gain que dans un pire cas
adversarial, lequel suppose une foule qui *connaît* la grille publiée. Aucun
des deux termes n'est nul, aucun n'est mesuré.

**Rien n'a donc été câblé.** Modifier la carte reviendrait à trancher, par un
choix d'implémentation, un arbitrage que ce dossier n'a pas les données pour
trancher — exactement le genre de décision silencieuse que tout le reste du
protocole existe pour empêcher.

## 45. La pénalité d'identification, mesurée famille par famille (`h26_identification.py`)

> **Amendé au §59.** L'identificateur linéaire employé ici (`IdentLin`,
> variante `raw`) applique la matrice empirique **entière** à des familles dont
> 99 % des entrées sont du bruit pur. Un seuillage par entrée, calibré sans
> rien savoir de la règle, capte ×1,64 de plus — positif sur les cinq archives
> testées. Les parts captées de cette section sont donc celles d'un estimateur
> nommé, pas celles de la famille.

Le sommaire alignait cinq plafonds, et quatre portaient la même réserve en
toutes lettres : borne d'**omniscience**, pénalité d'identification non
mesurée (§3 quater, §40). Le §3 bis ne l'avait chiffrée que pour la famille
marginale — 64 % captés à la frontière, +1,33 % qui tombe à +0,99 %. Voici
les quatre autres.

Méthode de `c2_apprentissage.py` : des archives à biais **connu par
construction**, fabriquées par les générateurs mêmes des expériences
d'origine — `gen_conditional` de `c1`, `gen_lagged` de `d2`, `gen_quad` de
`h24`, ce dernier **extrait de sa source par l'AST** puisque le fichier
s'exécute à l'import et aurait écrit au registre. Les amplitudes de frontière
sont **relues des consignations**, jamais recalculées. Sur chaque archive,
trois joueurs en marche avant stricte (50 560 tirages, `leak_check` sur les
neuf prédicteurs) : la grille fixe à 2,50 par théorème ; l'**oracle** qui
joue la règle ; et l'**identificateur**, qui n'a que le passé et la
statistique exhaustive de sa famille — la matrice de couplage empirique
80×80 pour les familles linéaires, et non un classement par fréquence qui
n'est exhaustif que du cas marginal.

| amplitude (× frontière) | rémanence | paires cachées | lag connu | quadratique |
|---|---|---|---|---|
| ~0,5–0,6 | +137 % ± 121 % | +16 % ± 9 % | — | +6 % ± 2 % |
| **1 (frontière)** | **100 % ± 11 %** | **41 % ± 3 %** | **46 % ± 2 %** | **11 % ± 2 %** |
| ~2 | 100 % ± 5 % | 94 % ± 2 % | 99 % ± 4 % | 70 % ± 1 % |
| ~4 et plus | 100 % ± 1 % | 100 % ± 1 % | — | 100 % ± 1 % |

Les témoins encadrent la mesure : sur SRS pur les six joueurs rendent 2,50 à
l'erreur-type près (2,4881 à 2,5087) ; à grande amplitude toutes les parts
montent à 100 %, donc aucun identificateur n'est cassé. Et les archives de
frontière y sont bien : `T1` sort à z = +4,0, `T2` à +3,5, `Q1` à +3,4, juste
sous le seuil du registre. Les oracles retombent sur les plafonds publiés
(+0,0794 contre +0,0803 pour `c1`, +0,0851 contre +0,0865 pour `d2`, +0,1576
contre +0,1567 pour `h24`).

### La table qui remplace les majorants par des nombres atteignables

| famille | omniscience | part captée | **réalisable** |
|---|---|---|---|
| rémanence uniforme (`c1`) | +0,53 % | 100 % ± 11 % | +0,53 % |
| marginal (`c0`, §3 bis) | +1,33 % | 64 % | +0,99 % |
| paires cachées (`c1`) | +3,21 % | 41 % ± 3 % | **+1,30 %** |
| lags 1..306 (`d2`, lag connu) | +3,46 % | 46 % ± 2 % | **≤ +1,59 %** |
| **quadratique (`h24`)** | **+6,27 %** | **11 % ± 2 %** | **+0,71 %** |

**La hiérarchie publiée s'inverse par le haut.** La famille quadratique, qui
portait le plafond de la piste A à +6,27 % au §40, ne rend que **+0,71 %** à
un joueur qui doit l'identifier — *au-dessous du marginal*. Le mécanisme est
monotone en nombre de paramètres : 1 paramètre se devine toujours (100 %),
6 400 se devinent à moitié (41 %), 252 800 ne se devinent presque plus
(11 %). À la frontière, les cellules vraies du tenseur sont à |Z| ≈ 3 sous
une loi du max à ≈ 4,7 : **indiscernables du bruit de leur propre
estimateur**, et « non détecté » implique alors « non identifiable ».

L'étendue d'un facteur 12 entre plafonds d'omniscience (0,53 → 6,27 %) se
resserre en un facteur 3 entre plafonds réalisables (0,53 → 1,59 %). **Le
plafond réalisable de toute la piste A se lit désormais ≤ +1,59 %** — la
famille des lags, et c'est un majorant puisqu'il est mesuré à lag connu du
joueur. Un facteur 4 sous le chiffre d'omniscience du sommaire, et toujours
un ordre de grandeur sous l'avantage de la maison.

### Ce que cette mesure fait à mes §41 et §42 — et j'avais sur-corrigé

Le §41 affirmait que le plafond réalisable « croît puis décroît, et qu'il
existe donc un ordre optimal pour l'adversaire ». Le §42 a mesuré, dans un
modèle multinomial abstrait, une croissance monotone en `m^{+0,06}`, et a
porté un erratum retirant l'affirmation du §41.

**`h26` mesure sur les vraies familles, et le retournement existe** : 0,53 →
0,99 → 1,30 puis **0,71**. La courbe monte jusqu'aux paires cachées
(m = 6 400) et retombe au tenseur (m = 252 800). L'intuition du §41 était
juste ; c'est mon erratum du §42 qui a sur-corrigé.

Le §42 avait nommé la raison de sa propre faiblesse, et c'est celle-là :
sa limite n° 3 déclarait que le joueur y estimait sur les **mêmes**
observations que le test, ce qui est strictement plus facile que la marche
avant, donc que son exposant était un **majorant**. Il l'était. Sa limite
n° 2 déclarait aussi que si l'exposant de `h26` différait du sien, ce serait
celui de `h26` qui ferait foi, puisqu'il travaille sur les vraies familles.
Il diffère, et il fait foi.

> Ce qu'il faut retenir des trois sections ensemble : le plafond
> d'omniscience croît en `m^{1/4}` (§41, et cela tient), la pénalité
> d'identification le mange (§42, et cela tient), et elle le mange **plus
> vite que le modèle abstrait ne le prévoyait** — assez pour retourner la
> courbe entre 6 400 et 252 800 cellules (§45). Monter en complexité finit
> par desservir l'adversaire.

Une anticipation reste fausse dans l'autre sens, et il faut le dire : je
m'attendais à ce que l'inversion frappe dès les paires cachées. Elles
résistent (+1,30 % contre +0,99 %). C'est le tenseur qui s'effondre.

### Limites

1. « Meilleur identificateur » signifie le meilleur **disponible ici** —
   plug-in de la statistique exhaustive, meilleure de deux variantes par
   point. Le biais est légèrement optimiste, donc dans le sens qui
   **surestime** le réalisable : conservateur pour la conclusion
   d'effondrement.
2. La ligne `d2` est mesurée à **lag connu** : +1,59 % est un majorant,
   départager 306 lags étant strictement plus dur.
3. L'identificateur quadratique est réajusté aux trois points de contrôle de
   `c2` quand les linéaires apprennent en ligne. L'écart est chiffré par une
   variante de contrôle : +0,0038 hits, soit cinq points de part — pas les
   quatre-vingt-neuf qui manquent au tenseur.
4. Sous la frontière la part s'effondre vers zéro, mais son **signe** n'est
   pas résolu à ce budget de réplicats.

**Registre : quatre consignations sans `p`** — aucune statistique n'a été
calculée sur l'archive réelle, et le `m` de Holm ne bouge pas.

## 46. La franchise au second ordre, et l'égalité qui interdit de comparer sous H₀ (`h28_franchise.py`)

Le théorème C bornait la franchise de l'assurance gratuite par
`2·√(T ln N)·20/T = 0,2718` hit/tirage ; `f3` en mesurait **0,016**. Un
facteur 17 entre une borne et sa réalisation est un aveu : la borne ne décrit
pas le mécanisme. `2·√(T ln N)` est la garantie pire cas de Hedge, payée
contre un adversaire qui choisirait les pertes après avoir vu les poids. Ici
l'« adversaire » est un tirage hypergéométrique.

### Le piège, découvert en dérivant plutôt qu'en mesurant

Sous H₀ toutes les règles ont la même espérance de hits — invariance — donc
comparer des agrégateurs sur les hits ne peut rien montrer. On croit alors
que le **regret** les sépare. C'est encore faux :

> **Théorème d'égalité.** Pour tout agrégateur dont les poids et la grille
> sont prévisibles, `E[S_agg] = 0` par invariance, donc
> `E[franchise] = E[max_h S_h]/T` — **le même plancher pour tous.**

La franchise n'appartient pas à l'agrégateur : elle appartient au
**comparateur**, le maximum a posteriori de 26 marches corrélées. C'est la
malédiction du vainqueur, encore, à un endroit où personne ne l'attendait.
Vérifié : sur 32 archives SRS à T = 20 000, les différences appariées entre
cinq règles sont toutes compatibles avec zéro (max |z| = 1,20 ; une vraie
différence de 0,0056 hit/tirage aurait été vue à 3 σ).

**Sous H₀, la franchise ne se réduit pas : elle se paie, à l'identique, par
toute règle honnête.** Le plan initial de cette expérience — comparer les
franchises sous H₀ — était donc condamné avant d'être exécuté, et c'est la
dérivation qui l'a montré, pas la mesure.

### La borne C′

La famille de second ordre d'AdaHedge remplace `T` par `V_T`, la variance
cumulée des pertes sous les poids courants. Dérivée de bout en bout — gap
borné par l'étendue, Bernstein sur `δ_t`, télescopage par concavité, sortie
d'échauffement, récurrence sur `Δ²` — chaque fait revérifié numériquement à
chaque pas :

```
R_T ≤ 2,3971·√(V_T·ln N) + 2·ln N + 6 + 2Δ₀
```

**valide par réalisation** : `V_T` est mesuré sur la trajectoire même, sans
aucune hypothèse sur la loi des tirages.

| | valeur |
|---|---|
| regret fractionnaire réalisé, archive réelle | **0,01253** |
| borne C′ | **0,0255** (pur) / 0,0257 (déployé) |
| borne C (premier ordre) | 0,2718 |
| resserrement | **×10,7**, marge ×2,0 au lieu de ×21,7 |

Zéro violation sur l'archive réelle, 32 archives à T = 20 000 et 6 archives
complètes (marge minimale ×1,99) ; zéro violation des faits intermédiaires
sur 710 098 pas. **Témoin positif** : une borne sciemment fausse,
`0,5·√(V ln N)`, est violée **32/32** — le banc a des dents.

D'où vient le resserrement : `v̄` mesuré vaut 0,0046–0,0064 contre 1/4 au
pire cas. La combinatoire exacte le prédit depuis le partage de top-20 mesuré
entre têtes (5,916/20, recoupant le 5,92 de `f6`) : prédit 0,006428, mesuré
0,006439. **La corrélation des têtes ne compte que pour ~6 %** — l'essentiel
est que l'adversaire est un tirage, pas un adversaire.

### Une confusion du théorème C, corrigée au passage

La borne de Hedge porte sur l'agrégateur **fractionnaire** (`Σ w·pertes`) ;
l'app joue le **top-20 du mélange de champs**. Le théorème C écrivait la
borne de l'un en face de la franchise de l'autre. Mesurés séparément :
fractionnaire 0,0125, mélange 0,0162. Même espérance sous H₀ — les deux sont
prévisibles — mais objets distincts sous la borne, qui ne couvre que le
premier. La conformité du second est un **fait mesuré, pas démontré**, et de
même pour le mélange 2 % uniforme du code déployé.

### Cinq agrégateurs, un oracle, et le verdict

Moyenne uniforme, FTL, FTRL entropique, AdaHedge pur, AdaHedge déployé —
mêmes têtes, mêmes champs, `leak_check` propre sur les trois architectures.
Sur l'archive réelle : 0,0147 / 0,0179 / 0,0192 / 0,0164 / 0,0162. Le Hedge à
taux fixe optimisé **après coup** — un oracle, donc une borne inférieure et
non un concurrent — donne 0,0115. L'écart d'AdaHedge à l'oracle vaut
**0,001 hit/tirage**, loin sous le bruit (sd ≈ 0,006).

### La seule unité où la franchise compte : le seuil de détection

| avance (hit/tirage) | uniforme | FTL | FTRL | AH pur | déployé |
|---|---|---|---|---|---|
| +0,017 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| +0,046 | 0/4 | 0/4 | 3/4 | 2/4 | 2/4 |
| **+0,098** | 3/4 | **4/4** | **4/4** | **4/4** | **4/4** |
| +0,192 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

Les quatre règles qui suivent le leader détectent 4/4 dès +0,098 ; l'uniforme
seulement dès +0,192 — **deux fois pire**, alors que sa franchise réalisée
sous H₀ était plus *basse*. La réponse à « une franchise divisée par deux
abaisse-t-elle le seuil ? » est donc **non** : la franchise sous H₀ ne peut
pas différer (théorème d'égalité), et ce qui abaisse le seuil est la
franchise sous l'**alternative** — à +0,098, l'uniforme capte 61 %
(franchise 0,038) là où le déployé capte 95 % (0,005).

### Ce que C′ change au fond

Capter une avance `ε` est garanti dès que la borne par tirage passe sous `ε`.
Le théorème C exigeait `T ≳ 2 819 337` tirages pour `ε = 0,043` — et `f3`
**mesure** la détection à T = 20 000, un démenti par ×140. C′ exige
`T ≳ 17 348` : la garantie rejoint enfin la mesure.

> La théorie ne promettait pas moins que la pratique par lâcheté de
> l'algorithme, mais par lâcheté de la borne.

**Verdict : AdaHedge tel que déployé est déjà optimal ici, et il n'y a rien à
gagner à en changer.** C'est un résultat négatif, et il est mesuré.

### Deux erreurs de fabrication, et leur leçon

Un chiffre écrit à la main — « 0,2723 » — s'était glissé dans une note
destinée au registre : le run a été tué avant toute écriture et le chiffre
remplacé par sa valeur calculée, 0,2718. La règle « aucun nombre hors
exécution » a mordu sur son auteur. Et la répétition générale affichait des
« parts captées » à dix chiffres — division par une avance par réplicat
proche de zéro, remplacée par le rapport des moyennes.

**Registre : quatre consignations sans `p`** — des vérifications et des
mesures, pas des chasses au biais. Zéro significatif, inchangé.

## 47. L'ordre de sortie : un plafond infini en détection, nul en exploitation (`h37_ordre_et_avantage.py`)

L'archive est **triée** sur ses 70 560 lignes. Conséquence que personne
n'avait formulée : contre toute hypothèse portant sur l'**ordre** des boules,
elle n'a pas une puissance faible — elle a une puissance **exactement
nulle**, la statistique n'étant pas calculable. Par la loi du §41, une
famille invisible a un plafond **infini**, et l'espace ordonné compte
2^122,69 issues contre 2^61,62 pour l'espace trié. Sur ce critère, c'est un
trou bien plus grand que le troisième ordre.

### Le théorème qui le vide

> Le gain d'un ticket ne dépend du tirage que par le nombre de numéros cochés
> qui en font partie — donc par l'**ensemble** tiré, jamais par l'ordre de
> sortie. Toute déviation d'ordre pur laisse donc l'espérance de gain de
> toute grille **rigoureusement inchangée**.

La démonstration tient en une ligne : `E[gain] = Σ_S P(S)·gain(S)`, et une
déviation d'ordre pur ne touche aucun `P(S)`. Dans le langage du §41, le
vecteur d'avantage de cette famille est le vecteur **nul**, et le plafond
`‖a‖·(2m)^{1/4}·√(z/N)` vaut zéro quel que soit `m`, aussi grand soit-il.

**Vérifié plutôt que supposé.** Sur 200 000 tirages dont l'ordre est biaisé à
90 % — les petits numéros poussés vers le début — mais dont l'ensemble reste
uniforme par construction :

| statistique | observé | null simulé | z |
|---|---|---|---|
| loi de la **première boule** | 1 733 738 | 73 ± 12 | **+145 333** |
| χ² des 80 marginales d'**ensemble** | 57,2 | 59,8 ± 8,9 | **−0,30** |
| le même, ordre libre (témoin négatif) | 54,8 | 59,8 ± 8,9 | −0,56 |

Un générateur peut donc être massivement défaillant dans son ordre sans qu'un
joueur y gagne ou y perde un centime, et sans qu'aucune des 39 voies du
dossier ne puisse le voir.

*Le null est simulé et non tabulé : écrire « attendu 79 » aurait été l'erreur
même que le §1 de l'audit a commise une fois, les 80 comptes d'ensemble
sommant à 20N par construction. Il vaut 59,8 ± 8,9.*

### Par où l'ordre peut malgré tout payer

Le théorème ferme la voie directe et en laisse exactement deux :

- **L'ordre comme symptôme.** Un biais d'ordre n'est pas exploitable mais
  révèle que la source n'est pas ce qu'on croit — et une source défaillante
  dans son ordre l'est peut-être ailleurs. Instrument de diagnostic à haute
  sensibilité, deux fois plus d'information par tirage.
- **L'ordre comme levier algébrique.** C'est la voie des §17 à §35 : un
  tirage ordonné publie 122,69 bits, assez pour contenir deux sorties de
  64 bits, ce qui rend la récupération d'état linéaire au lieu de
  combinatoire. Un générateur récupéré rendrait le tirage suivant
  déterministe conditionnellement — **l'invariance ne s'appliquerait plus du
  tout**, faute d'uniformité. Ce n'est pas un avantage marginal, c'est la fin
  du théorème.

```
un biais d'ordre        ->  plafond d'exploitation NUL (théorème ci-dessus)
un générateur récupéré  ->  plafond illimité, invariance caduque
```

**L'ordre ne vaut rien par ce qu'il révèle, et tout par ce qu'il permettrait
de prédire.**

### Conséquence pour la collecte, et elle inverse une priorité

| tirages ordonnés | durée | plafond de détection relatif |
|---|---|---|
| 100 | 12 h | ×56,2 |
| 1 000 | 5 j | ×17,8 |
| 10 000 | 49 j | ×5,6 |
| 70 560 | 346 j | ×2,1 |

Il faudrait **315 553 tirages ordonnés — 4,2 ans** — pour que la loi de
position soit contrainte aussi finement que les marginales le sont
aujourd'hui. C'est un mauvais investissement : des années pour fermer une
famille dont le plafond d'exploitation est nul par théorème.

Les capturer pour la récupération d'état en est un excellent : le §27 a
établi que **cinq consécutifs suffisent** aux trois modèles de source, soit
vingt-cinq minutes, et l'app les accumule seule depuis le §34.

### Limites

1. Le théorème suppose que le gain ne dépend que du nombre de hits. Vrai d'un
   barème de keno, et déjà utilisé au §26 — mais c'est une hypothèse sur le
   **produit**, pas un théorème.
2. La voie du symptôme suppose qu'un défaut d'ordre soit corrélé à un défaut
   d'ensemble. Plausible, non démontré, et le dossier n'a aucun moyen de
   l'établir.
3. Le calendrier applique la loi d'échelle du §41, dont seule la structure en
   **rapports** est transportable.

**Registre : inchangé.** `h37` ne teste pas l'archive — il démontre.

## 48. Où la courbe se retourne, et le maximum de toute la piste A (`h38_maximum_realisable.py`)

> **Discuté au §59, puis CONFIRMÉ au §61.** Le §59 annonçait que ce maximum
> montait à +2,16 % avec un estimateur adapté à la parcimonie ; le §61 montre
> que le plafond d'omniscience du même point tombe de 44 % face aux détecteurs
> ajoutés au §60, et que le net vaut 1,20 %. Le §61 balaie de plus l'axe de la
> parcimonie, que cette section ne balayait pas, et y trouve le maximum **au
> bord, en s = m** — c'est-à-dire exactement ici. Le chiffre de cette section
> tient ; ce qu'elle ignorait, c'est pourquoi.

Le §45 établit que le plafond réalisable se retourne — 0,53 puis 0,99 puis
1,30 puis **0,71** — mais il ne le **localise** pas. Tant que le maximum
n'est pas situé, la phrase du sommaire (« ≤ +1,6 % ») n'est vraie que des
familles qu'on a pensé à tester. Cette section la rend vraie de toutes.

### Le critère du retournement, lisible sans ajustement

Le §42 a établi que le rapport signal sur bruit de l'identification vaut
`SNR ∝ m^{−1/4}`. C'est la variable naturelle. En la prenant comme abscisse,
les quatre parts captées de `h26` donnent des pentes locales :

| segment | d(log part) / d(log SNR) |
|---|---|
| rémanence → marginal | 0,407 |
| marginal → paires cachées | **0,406** |
| paires cachées → quadratique | **1,432** |

Les deux premières sont identiques **à trois décimales** ; la troisième
franchit 1. Or le plafond réalisable vaut `omniscience × part captée`, soit
`m^{1/4} × part(SNR)`, d'où en logarithmes

```
d(log réalisable)/d(log m) = 1/4 − (1/4)·pente
```

> **Le plafond réalisable croît tant que la pente est sous 1, décroît au-delà,
> et le maximum est exactement là où `d(log part)/d(log SNR) = 1`.**

Ce critère ne demande aucun ajustement paramétrique, et surtout il ne
s'appuie **que** sur la part captée — jamais sur les plafonds réalisables
eux-mêmes, qu'il prétend expliquer.

### Le maximum, localisé

| | valeur |
|---|---|
| m du maximum | **7 376 cellules** |
| intervalle à 95 % (bootstrap sur les incertitudes de `h26`) | [3 369 ; 23 520] |
| plafond réalisable au maximum | **1,28 %** |
| intervalle à 95 % | [1,06 % ; 1,46 %] |

**La famille des paires cachées est pratiquement au sommet de la courbe** —
6 400 cellules contre 7 376 pour le maximum. La famille quadratique, à
252 800, est déjà loin sur la pente descendante.

| m | omniscience | part captée | réalisable |
|---|---|---|---|
| 1 | 0,53 % | 1,000 | 0,53 % |
| 80 | 1,33 % | 0,640 | 0,85 % |
| 6 400 | 3,21 % | 0,410 | **1,32 %** |
| 7 376 | 3,29 % | 0,390 | **1,28 %  ← maximum** |
| 20 000 | 3,95 % | 0,273 | 1,08 % |
| 252 800 | 6,27 % | 0,110 | 0,69 % |

### Deux précisions, dont une incohérence héritée

Le critère de pente place le passage à 7 376 tandis que l'interpolation par
morceaux met le sommet du produit au nœud, à 6 400. Les deux disent la même
chose ; l'écart est un artefact de l'interpolation linéaire par morceaux.

Plus gênant : **la ligne marginale du dossier n'est pas cohérente avec
elle-même.** +1,33 % (plafond de `c0`) × 64 % (part captée de `c2`) fait
0,85 %, et non le +0,99 % publié depuis le §3 bis. La raison est que les deux
facteurs viennent de deux mesures différentes à amplitude nominalement
identique : `c0` mesure l'avantage de l'oracle à +1,33 % pour d = 0,0030,
`c2` le mesure à +1,55 % pour le même d. L'écart de 16 % est antérieur à ce
fichier, et `h26` l'a propagé sans le voir. La courbe ci-dessus emploie le
plafond de `c0` partout, par cohérence interne — d'où sa ligne marginale à
0,85 %.

### Une erreur de ma première version

J'interpolais l'omniscience par la loi `m^{1/4}` ancrée sur le seul point
marginal — alors que le §41 a lui-même **mesuré** que le facteur `‖a‖` varie
de 1,19 à 0,63. Cela surestimait de 24 % au voisinage du maximum : 1,61 %
annoncé contre 1,28 % réel. Appliquer une loi d'échelle là où l'on dispose
des mesures qu'elle est censée résumer est une faute d'autant plus facile
qu'on vient de démontrer la loi.

### Portée

**Ce que cela ferme.** Au-delà du maximum, monter en complexité **dessert**
l'adversaire : il n'existe donc pas de famille plus grande qui ferait mieux.
La piste A est bornée par le sommet de cette courbe, et non par la plus haute
famille qu'on a pensé à tester. L'énoncé cesse d'être un relevé de points
pour devenir une propriété de la courbe.

**Ce que cela ne ferme pas.** La courbe repose sur quatre points, et le
retournement n'est établi que par la dernière descente : un cinquième point
entre 6 400 et 252 800 cellules le confirmerait ou le déplacerait, et c'est
la mesure la plus utile que ce dossier puisse encore demander sur ce sujet.
L'interpolation log-log par morceaux est un choix, pas une loi — mais mieux
vaut interpoler des mesures qu'extrapoler un modèle que le §45 a réfuté. La
famille des lags (+1,59 %) n'entre pas dans la courbe, son `m` étant l'union
balayée de 306 familles. Et tout ceci porte sur les familles
**conditionnelles au tirage précédent** : le non stationnaire (§43) et
l'ordre (§47) ont leurs propres bornes, établies séparément.

> Le plafond réalisable de la piste A culmine autour de **1,3 %**, et
> l'avantage de la maison vaut 25 à 35 %. L'écart est d'un ordre de grandeur,
> et il **ne se referme pas en montant en complexité** — c'est précisément ce
> que signifie l'existence d'un maximum.

**Registre : inchangé.** `h38` n'interroge pas l'archive.

## 49. Avant la clôture : la deuxième pierre, épuisée (`h33_avant_cloture.py`)

Le §16 a démonté le mur de l'invariance en trois pierres, et le §31 a attaqué
la deuxième — « rien d'exploitable n'est visible avant la clôture » — avec
**une seule** variable, le boost, pour le plus gros chiffre du dossier. Une
variable examinée. Combien y en a-t-il ?

La réponse est le résultat principal de cette section : **l'inventaire est
fini, et il est court.**

### L'inventaire

Tout ce que le client peut lire pendant qu'un tirage est OPEN, champ par
champ : **six multiplicateurs** — les cinq cagnottes `extraJackpots`,
visibles sans condition, et le boost du slot OPEN, visible **sous
condition** (l'instrument B est câblé, zéro observation au dossier) — plus
deux constantes inconnues qui ne sont pas des variables aléatoires, le prix
du ticket et le barème. Et rien d'autre.

Le numéro de tirage est dégénéré (V = 0 par le cas d'égalité de Jensen).
L'heure, le jour, le rang de session et les boost passés ont leurs liens
vers le boost fermés au registre à puissance mesurée. L'historique n'informe
que par la prédiction, plafonnée aux §41–48. L'ordre de sortie et le bonus
sont post-clôture : valeur nulle par construction, corollaire du §31 — et le
§47 vient de montrer qu'ils vaudraient zéro même visibles.

Un fait de covariable clôt une cellule entière : **70 190 des 70 559 écarts
consécutifs de l'archive sont au pas exact de 300 s**, 24 seulement en
sortent (±1–5 s). La latence de publication n'a donc aucune trace
exploitable dans l'archive ; la question appartient aux instruments C et D,
pas au registre.

### Le corollaire qui traite tout le reste

Beaucoup d'entrées ne multiplient pas le gain, et forcer le théorème M
dessus serait une faute. Le bon énoncé, démontré puis vérifié par balayage
exhaustif des `2^|Z|` politiques :

> Pour `Z` observable avant la mise, tout se passe comme si l'on observait
> `X̂ = E[X | Z]`, et voir `Z` vaut l'écart de Jensen de `X̂`.

Deux conséquences. Un lien nul au registre devient une valeur **nulle
mesurée** — pas supposée. Et voir un indice ne vaut jamais plus que voir la
variable. C'est ce corollaire qui transforme trente lignes de « conforme »
du registre en trente zéros de la table des valeurs.

### La case vide, testée

Le produit cartésien (covariable pré-clôture × multiplicateur) n'avait
qu'une case à la fois testable et vide : le contenu du tirage `t−1` — publié
~4 min 30 avant la clôture de `t` — contre le boost de `t`. Deux
statistiques pré-enregistrées, null permuté simulé sur 2 000 réplicats :

| statistique | z | p |
|---|---|---|
| χ² d'homogénéité du champ | −1,21 | 0,233 |
| corrélation avec la somme | **−2,65** | **0,0085** |

Le second a la taille exacte de la base rate — l'audit en a produit trois par
hasard sur des données garanties équitables — et n'est pas significatif après
Holm (m = 3 321, seuil 1,5·10⁻⁵). Il est **marqué pour réplication** sur les
tirages postérieurs à l'archive. Puissance mesurée : 93–100 % dès ε = 0,02,
témoin négatif à 0 %. Et le seuil d'exploitabilité du boost reste ε ≈ 0,134
(§4) : ce qu'une fuite passée inaperçue ici pourrait valoir est borné très en
dessous de l'exploitable.

*Une entorse à la règle n° 2 est consignée au registre : les deux valeurs ont
été vues une fois au prototypage, avant le scellement des jetons — la même
faute que `h29.coherence_releve`, disclosée de la même façon.*

### La composition — deux mondes qu'il ne faut pas confondre

Le corollaire de composition du §31 dit que les multiplicateurs visibles
agissent par leur **produit** : la politique conjointe optimale est « miser la
mise k si et seulement si `b·j_k·p_k > 1` », quelle que soit la loi.

| politique | profit/tirage | rapport |
|---|---|---|
| monde 1 — J6 seule (§29) | 0,0099 | ×1,00 |
| monde 1 — **les cinq cagnottes** | **0,0128** | **×1,29 — inconditionnel** |
| monde 2 — J6 × B vu (§31) | 0,170 | — |
| monde 2 — cinq cagnottes × B vu | **0,276** | ×1,62 vs §31, ×27,8 vs J6 |

Le mécanisme du monde 2 : `B = 10` divise le seuil de la mise 5 à CHF 155 —
une cagnotte *moyenne* le franchit — et ressuscite les mises 7 à 10, mortes à
dix zéros du seuil en solo. La politique occupe alors 22,7 % des tirages.

Vérifié par simulation (2·10⁶ tirages × 5 mises, le pari du rang plein
intégré **exactement** — sans quoi 2·10⁶ × p₆ ≈ 9 événements, la famine
Monte-Carlo pour la quatrième fois) : accord sous 1 σ partout, et témoin
d'égalité de Jensen — `B ≡ 1` rejoué dans la même machinerie rend exactement
le monde 1, à 0,0 près.

> **Précision qui change l'attribution, et je l'ai vérifiée dans le code :
> le ×1,29 n'est pas un correctif à apporter à l'app — elle le fait déjà.**
> `GridsView` calcule `ret` pour les **cinq** mises et bascule dès que
> `rows.contains { $0.ret >= 100 }`. Ce que ce chiffre mesure, c'est l'écart
> entre ce que l'app fait et ce que le §29 *analysait* : le dossier avait
> raisonné sur la seule mise 6 alors que le produit surveillait déjà les
> cinq. Ici c'est l'analyse qui rattrape l'implémentation, et non l'inverse.

Recalibré sous l'hypothèse non rejetée du §44 (α·γ commun aux cinq mises), le
**niveau** bouge d'un facteur 30 — c'est l'intervalle du §29 qui parle — mais
la **structure** se renforce (×21 → ×439 pour la visibilité de B). Ce qui est
porté par les rapports tient ; ce qui est porté par le niveau ne tient qu'au
relevé unique.

### Six demandes de données, classées par rapport coût/décision

1. **Le prix du ticket** — une observation ; la seule donnée dont une
   décision dépende (§36).
2. **La règle du boost** — une lecture du règlement : est-il une option
   payante, étend-il la cagnotte ? C'est elle qui décide si le monde 2
   existe au-delà des rangs à gain fixe.
3. **Le verdict de l'instrument B** — ~20 tirages OPEN, soit 100 minutes ;
   l'enjeu est le facteur ×21 entre les deux mondes.
4. **La latence signée et la dérive de clôture** — instruments C et D ;
   l'archive est muette par construction.
5. **La série de cagnottes** — déjà journalisée ; la précision se paie en
   **chutes** et non en relevés (§36).
6. **Le barème** — il fixe `R₀` (§50 le reprend).

Ce qui n'est **pas** demandé : la répartition de la foule, non exposée par
l'API — la réponse minimax du §44 tient lieu de mesure.

### Ce qui est établi

La deuxième pierre n'est plus « une case grande et vide » : c'est une **liste
finie**. Six multiplicateurs, dont cinq visibles aujourd'hui et un suspendu à
une observation de cent minutes ; une politique conjointe dont la forme ne
dépend d'aucune loi ; une case d'archive close au registre ; et tout le reste
démontré **sans valeur** — par dégénérescence, par lien nul à puissance
mesurée, ou par le corollaire du post-clôture.

Le mur ne tombe toujours pas là où il est fait de mathématiques. Mais on sait
désormais exactement combien de portes il a, et laquelle n'a jamais été
poussée.

**Registre : +2** (`h33.champ_lag1_boost`, `h33.somme_lag1_boost`), les deux
conformes après Holm.

## 50. Le barème encerclé : non publié n'est pas inconnaissable (`h34_bareme.py`)

> **Dépassé par le §56.** Le barème a depuis été relevé. Cette section est
> conservée telle quelle : sa borne `ρ ≥ 0,245` s'est révélée **vraie** sur
> les cinq mises et lâche d'un facteur 2,1, et son théorème de collapse a été
> **mesuré**. On ne réécrit pas une borne qui a tenu — on montre ce qu'elle
> valait quand la donnée est arrivée.

Le §5 s'arrête sur un aveu : aucun barème réel dans le dépôt, l'API ne publie
que les jackpots k/k. Tout le volet financier contourne le trou par une
condition suffisante — « rangs intermédiaires ≥ 0 » — et le §30 chiffre le
prix de cette prudence : le barème déplace la **taille de mise admissible**,
c'est-à-dire ce qui décide si le gain devient de l'argent.

Personne n'avait posé la question d'avant : ce barème est-il libre, ou déjà
contraint par ce que le dossier sait ?

### La comptabilité, et l'inégalité qui la ferme

Un franc misé se décompose exactement : `1 = potcost + ρ + marge`, où
`potcost` est ce que l'opérateur versera aux gagnants du rang plein et `ρ`
l'espérance des rangs intermédiaires — **le** terme inconnu du §5. Le taux de
retour d'une licence vaut `R = potcost + ρ`.

Or `potcost` est borné par une quantité que les relevés mesurent **déjà**.
Avec `γ = E[gagnants | chute] ≥ 1` et un plancher `J₀ ≥ 0` :

```
potcost = α + q·J₀/(N·c)  ≤  θ = E[J]·p/c        car θ − potcost = (γ−1)·(…) ≥ 0
```

C'est une **inégalité de foule** : les co-gagnants font paraître la cagnotte
généreuse sans coûter davantage. Et `θ` est la « fraction du seuil » du §21,
le gain conditionnel du §29 — le même nombre, lu une troisième fois. Donc

> **ρ ≥ R − θ**, et la part des rangs intermédiaires est contrainte **par
> différence**.

**Une erreur commise et corrigée, qui aurait coûté un facteur de sécurité
injustifié.** La première dérivation bornait le *décaissement* de l'opérateur
et non les *versements* aux gagnants ; les deux diffèrent de `(1−q)` et la
« borne » se cassait au régime des chutes fréquentes. Le taux de retour compte
les versements, pour lesquels la borne tient sous les deux conventions
d'affichage. Vérifié sur 24 régimes simulés : versés/θ ≤ 1 partout à 4 σ, et
le témoin — le décaissement à λ = 0,65 — **viole** la borne à 1,92·θ. La
machinerie sait voir une violation.

### θ, et ce qu'un seul instantané contraint

Sous [Hθ] — `θ` commun aux cinq mises, dont le §44 a mesuré la cohérence avec
le relevé unique (p = 0,57) — les cinq `J_k·p_k` du 30 août sont cinq tirages
d'une même loi :

```
0,229   0,295   0,038   0,040   0,056        θ̂ = 0,1315,  θ ≤ 0,405 à 95 %
```

*Recoupé indépendamment pour ce rapport : les cinq valeurs et leur moyenne se
reproduisent au chiffre près depuis les combinaisons exactes.*

La couverture de cette borne n'est pas décrétée mais **mesurée** : 0,973 à
1,000 sur neuf régimes H1–H3, et elle s'effondre à 0,581 sur un témoin où H2
est violée (âges en mélange de deux régimes). La garantie est une propriété
de l'absence de mémoire — exactement la réserve du §28.

### La borne, hypothèses incluses dans la phrase

> **SI** `R ≥ 0,65` [HR — la valeur de travail que `b2` utilisait déjà ; aucun
> chiffre de licence n'est affirmé ici], **SI** le ticket coûte 1 franc [Hc],
> **sous** [Hθ] et H1–H3, **ALORS ρ ≥ 24,5 % à 95 %.**

| R | 0,50 | 0,60 | **0,65** | 0,70 | 0,75 |
|---|---|---|---|---|---|
| ρ_min | 9,5 % | 19,5 % | **24,5 %** | 29,5 % | 34,5 % |

**Sans le pooling [Hθ], la borne est VIDE** — `n = 1` par mise donne
θ_hi = 11,65 — et il faut le dire dans la même phrase que le résultat.

Variante qui se passe de H1–H3 : si la cagnotte affichée était un montant
**fixe** (réserve n° 2 du §29), alors `potcost = J·p/c` exactement et
`ρ ≥ 35,5 %`. La borne survit aux deux lectures de la cagnotte ; c'est la
stratégie du §29 qui ne survit qu'à la première — et **deux relevés
successifs les départagent**, un montant fixe ne bougeant pas.

### Le théorème de collapse : la forme du barème ne compte pas

Les contraintes — probabilités hypergéométriques exactes, monotonie, tout
rang payé rend au moins la mise, `Σπw = ρ` — réduisent la mise 6 de six
nombres libres à un **polytope de dimension 2** (aucun barème admissible ne
paie sous 3/6), et en gains entiers à un **catalogue fini de 72 tables**.
Elles n'identifient jamais le barème. Elles n'en ont pas besoin :

> Sur 4 081 barèmes admissibles, **chaque décision du dossier est fonction du
> seul scalaire `ρ`** — le seuil et le gain conditionnel par identité exacte,
> la fraction de Kelly et la croissance **à 0,45 % près**.

La raison est bornée, pas constatée : la variance des rangs intermédiaires
vaut au plus `ρ²/π₅ = 19,4` contre `p·J′² = 8 547` pour la cagnotte — un
demi-pour-cent du dénominateur de Kelly.

**Et le §5 se dissout au lieu de se réparer.** `b2` rejoué dans l'espace
admissible, `potcost` épinglé par les relevés et `R` commun : `E[brut] = R`
sur chaque barème à 3·10⁻¹⁶ près. Le « classement des mises par espérance »
de `b2` n'était pas *fragile* — il était **vide par identité comptable**. La
forme redevient partiellement robuste (7 paires ≥ 95 %, contre zéro pour
`b2`), toutes par l'écart-type que la cagnotte observée fixe.

*Seconde erreur corrigée : la première statistique de collapse comparait tous
les barèmes au `ρ` **nominal** et trouvait 15 % d'étendue — qui n'était que la
tolérance ±0,01 du catalogue, propagée. Elle mesurait un bouton de tolérance,
pas la forme. Corrigée en comparaison à `ρ(w)` égal.*

### Ce qui descend

| mise | seuil §5 bis | seuil abaissé | fraction avant | après | facteur |
|---|---|---|---|---|---|
| 5 | CHF 1 551 | CHF 1 171 | 1,27 % | 3,70 % | ×2,9 |
| **6** | **CHF 7 753** | **CHF 5 853** | **3,37 %** | **7,73 %** | **×2,3** |
| 7 | CHF 40 979 | CHF 30 940 | 2,8·10⁻¹² | 1,9·10⁻⁹ | ×678 |
| 8 | CHF 230 115 | CHF 173 738 | 1,8·10⁻¹¹ | 7,6·10⁻⁹ | ×431 |
| 10 | CHF 8 911 711 | CHF 6 728 394 | 1,6·10⁻⁸ | 1,3·10⁻⁶ | ×82 |

**Vingt-deux tirages favorables par jour à la mise 6 au lieu de dix.** Le
facteur est exactement `exp(ρ_min·S/μ̂)` — l'exponentielle du §28, cette fois
dans le bon sens. *(Recoupé ici : ×2,29 mesuré, ×2,29 prédit.)*

Le gain conditionnel au nouveau seuil reste exactement `μ̂/S = 29,5 %` :
**l'identité du §29 survit au barème**. Celui-ci ne change pas ce que vaut une
occasion — il change *où elle commence*, donc combien il y en a.

| scénario (hypothèse dans le nom) | f* | croissance/jour | capital minimal |
|---|---|---|---|
| §30, rangs ignorés — borne de tout barème | 2,94·10⁻⁵ | ×1,0 | CHF 34 031 |
| ρ_min = 0,245 [borne 95 %, hyp. ci-dessus] | 4,78·10⁻⁵ | **×3,6** | **CHF 20 922** |
| ρ̂₆ = 0,355 [estimation ponctuelle] | 6,20·10⁻⁵ | ×6,7 | CHF 16 129 |

Trois dividendes calculés au passage : la loi jointe exacte des 13 grilles
disjointes retrouve **×13,02 avec** rangs intermédiaires comme sans —
l'étalement des §26 et §30 y survit, et la croissance annualisée passe de
+20,0 % à +94,4 % ; le théorème « le seuil est l'optimum » du §29 s'étend mot
pour mot, l'optimum passant en `x = (1−ρ)/α` ; et en croissance l'optimum est
un peu au-delà (`x = 3,02`) mais jouer dès la bascule en garde 88 % — la règle
pratique ne bouge pas.

### La demande la moins chère du dossier

> **Le règlement du jeu.** La réponse à la question du titre est là : rien
> n'indique que le barème soit *inconnaissable*. Il n'est pas dans l'API, ce
> qui n'est pas la même chose. Un jeu sous licence publie normalement ses
> règles, barème compris. **Un document lèverait `w_h` exactement et rendrait
> toute cette section obsolète** : zéro relevé, zéro modèle.

Viennent ensuite `R` (un chiffre de licence, lecture directe), le prix du
ticket — qui joue dans les deux sens, `θ ∝ 1/c` faisant *monter* ρ_min à 0,447
pour un ticket à 2 francs, mais le seuil en francs montant aussi et la
fraction retombant à 2,4 % — et des relevés **après chute** : à θ̂ constant,
ρ_min passe de 0,245 (n = 5) à 0,455 (n = 30), et le seuil de la mise 6
descend vers CHF 3 967.

### Limites

Tout est conditionnel à [HR], balayé et jamais affirmé. [Hθ] porte la borne,
et un test de cohérence à p = 0,57 n'est pas une preuve. H1–H3 restent le
socle, et le témoin dit exactement comment la borne ment si la cagnotte a deux
régimes. Les fractions favorables restent des estimations ponctuelles sur μ̂,
dont le §28 a chiffré l'incertitude — seul le **facteur** `exp(ρ_min/α̂)` est
nouveau. Le catalogue montre la finitude, il ne compte pas juste.

**Registre : cinq entrées, aucune ne portant de `p`** — `h34` prouve, mesure
des couvertures et corrige ; il n'interroge pas l'archive.

> Le barème n'est pas identifié, mais **il n'a jamais été l'inconnue utile**.
> L'inconnue utile est le scalaire `ρ` ; il est borné par la comptabilité ; et
> la borne fait descendre le seul seuil qui fasse changer l'espérance de signe.

## 51. Trois résultats, trois fois la décision de ne rien câbler

Cette campagne a produit trois nombres qui rendraient l'affichage de l'app
plus favorable, et trois fois rien n'a été câblé. Ce n'est pas de la
timidité, et il vaut mieux dire une fois pourquoi que de le répéter en note
de bas de page.

| § | ce qui est démontré | ce que câbler donnerait | pourquoi rien n'est câblé |
|---|---|---|---|
| 38 | le boost abaisse le seuil d'un facteur `B` | bascule à `S/B` au lieu de `S` | suppose que le boost multiplie **aussi la cagnotte** — hypothèse nommée non vérifiée (§31) |
| 44 | la grille uniforme est minimax sous partage | rotation privée des 80 numéros | détruirait le classement de l'essaim — arbitrage à deux côtés, non tranchable ici |
| 50 | `ρ ≥ 24,5 %`, seuil à `(1−ρ)·S` | bascule à CHF 5 853 au lieu de 7 753 | suppose `R ≥ 0,65`, ticket à 1 franc, `θ` commun, H1–H3 |

**Deux de ces trois cas partagent une asymétrie, et c'est elle qui décide.**
Aux §38 et §50, la règle affichée aujourd'hui est une condition
**suffisante** : elle manque des tirages favorables, mais elle n'en annonce
jamais un qui ne le serait pas. Les deux corrections proposées vont dans le
même sens — rendre l'affichage plus agressif sur la foi d'hypothèses que le
dossier a explicitement nommées comme non vérifiées.

C'est exactement l'échange que ce dossier existe pour refuser. Tout le §7
raconte ce qu'il en coûte : l'app affichait autrefois un avantage de +18 à
+34 % qui était entièrement artefactuel, et le corriger a été le résultat le
plus utile de tout le travail. Gagner quelques occasions supplémentaires au
prix d'une annonce non fondée serait revenir en arrière par un autre chemin.

Le §44 est d'une autre nature : là, les deux options se valent en principe et
l'arbitrage dépend d'une quantité — la corrélation entre les grilles des
utilisateurs et celles de la foule — que rien ici ne mesure. Ne pas trancher
est alors la seule position tenable.

> **Le principe, énoncé une fois.** Un résultat théorique qui déplacerait un
> seuil affiché ne se câble que si la démonstration ne repose que sur des
> quantités observables. Le seuil actuel `J ≥ c/p` en est une : `J` est à
> l'écran, `p` est une combinatoire exacte, `c` se lit sur un ticket. Le
> seuil `(1−ρ)·c/p` n'en est pas une tant que `ρ` repose sur un taux de
> retour supposé.

Et cela donne à la liste du §9 sa hiérarchie réelle : **ce qui manque n'est
pas du code, c'est trois observations** — le prix du ticket, le règlement du
jeu, et cent minutes de boost avant clôture. Chacune transformerait une
hypothèse en donnée, et donc un chiffre non câblable en chiffre câblable.
Aucune ne demande une ligne de calcul supplémentaire.

> **Suite au §58.** L'une des trois est arrivée. Le barème a été relevé (§56),
> `ρ` n'est plus supposé mais lu, et la condition que ce principe nommait est
> levée : le quatrième cas **a été câblé**, pour la raison exacte pour
> laquelle les trois premiers ne l'ont pas été. La prédiction de ce paragraphe
> — qu'il manquait des observations et non du code — a tenu.

## 52. Le codeur qui n'a pas besoin qu'on lui dise quoi chercher (`h35_codage_universel.py`)

Toutes les voies de piste A partagent une servitude : nommer la régularité
d'avance, puis payer sa place au registre. Les §41 à §48 ont montré ce que
cette servitude coûte — le plafond d'un biais indétectable croît en `m^{1/4}`
avec la taille de la famille, et il existe une infinité de familles jamais
nommées.

Le **codage universel** échappe à cette structure : un compresseur converge
vers l'entropie de la source, quelle qu'elle soit dans la classe qu'il
mélange, sans qu'on lui dise quoi chercher. Et l'unité est déjà celle du
dossier — sous H₀ un tirage coûte 61,6165 bits, et tout bit économisé est un
taux de Kelly. `f4` avait fait un pas, mais ses 174 paris étaient des modèles
**nommés**, à inclinaison figée.

### La classe, et pourquoi les indicatrices

Le rang combinatoire est écarté : changer un numéro déplace le rang de
quantités énormes, et aucun contexte sur ses chiffres ne correspond à un
biais physique. Les indicatrices rendent de faible complexité exactement ce
que le monde sait produire.

**22 codeurs KT** — prior Beta(1/2, 3/2), de moyenne 1/4, la valeur H₀ — sur
des contextes structurels : profondeurs 0 à 12 de l'histoire propre,
partagées sur les 80 numéros (tous les ordres de Markov ≤ 12, cousin à regret
quasi identique de CTW) ; un bit isolé aux lags 2 à 12 ; fenêtres glissantes
512 et 4 096 pour les défauts transitoires ; par-numéro pour la marginale ; et
le canal du bonus, seul membre hérité d'une famille déjà nommée et déclaré
comme tel. **5 133 paramètres**, profondeur dictée par le budget de données
(1 378 événements par feuille), pas par les données.

Le couplage referme la contrainte des 20-parmi-80 : `Q(S) = Π_{i∈S} w_i /
e₂₀(w)`, la loi de maximum d'entropie à champ donné. Alors `E[e_t | passé] = 1`
**exactement, quel que soit l'état d'apprentissage** : la validité ne dépend
pas de la qualité du modèle, seulement du fait que `θ` est fonction du passé
strict.

> **Une conséquence structurelle qui a d'abord été un bug.** Le membre `sh-d0`
> a un `θ` constant sur les 80 numéros, et le couplage est invariant
> d'échelle : son facteur vaut 1 à chaque pas. **La classe contient donc le
> codeur H₀ lui-même**, comme tout vrai compresseur universel — et le mélange
> est planchonné à `1/22 = 10^{−1,342}`. Une division par zéro l'a révélé, et
> le plancher a été **déclaré avant** la lecture du réel : c'est la leçon du
> plancher de `f4` (§12.2), appliquée cette fois dans le bon ordre.

### Vérifié avant d'être appliqué, puis mordu par ses témoins

Sur 200 000 tirages uniformes à champs fixes, la moyenne de `e_t` vaut 1 à
+2,00 σ, −0,52 σ et +1,18 σ. Le codeur complet, apprentissage compris, sur
4 archives SRS de 70 560 : pire dérive 2,34 σ, sups à 10^{+0,86} au plus
contre un seuil de Ville à 10^{+1,30}, et une **redondance de
−6,24·10⁻⁵ bit/tirage** — le prix mesuré du droit de ne pas nommer la
famille. L'anti-fuite est décisif et non déclaratif : futur réécrit à partir
de `t₀`, les log-facteurs du passé sont **bit à bit identiques**.

| témoin positif (T = 20 000) | mord à | manque |
|---|---|---|
| marginale | Δp = +0,019 (2/2) | +0,009 |
| rémanence | ε = 0,05 (2/2) | ε = 0,02 |
| écho au lag 8 | ε = 0,05 (2/2) | — |
| transitoire L = 500 | Δp = +0,098, **tôt comme tard** | — |
| **modulation périodique pure en temps** | **jamais (0/2 à δ = 0,30)** | — |

Deux lignes méritent leur commentaire. Le transitoire mord **placé tard comme
placé tôt** : les redémarrages par blocs effacent la pénalité de position que
le §12.5 avait mesurée. Et le dernier est un **angle mort assumé puis
mesuré** : la classe ne contient aucun contexte exogène en `t`, donc une
modulation purement temporelle lui échappe. Un témoin qui doit échouer, et
qui échoue, borne une classe mieux qu'une phrase.

### Le chiffre

| | valeur |
|---|---|
| taux de Kelly sur les 70 560 tirages | **−6,18·10⁻⁵ bit/tirage** |
| bits extraits des 4,35 Mbit de l'archive | **−4,4** |
| valeur finale du mélange | 10^{−1,314} — *collée au plancher* |
| sup du mélange, sup des redémarrages | **10^{+0,000}, atteints au pas 0** |

La richesse ne repasse **jamais** au-dessus de sa valeur initiale. Zéro bit.
Le diagnostic par modèle raconte la même chose que la théorie : les finals
s'ordonnent presque exactement par le nombre de paramètres, la redondance de
Krichevsky-Trofimov et rien d'autre.

*Recoupé pour ce rapport : `log₁₀(1/22) = −1,342` contre 10^{−1,314} annoncé,
soit bien le plancher ; et −6,18·10⁻⁵ × 70 560 = −4,36 bits.*

### Trois lectures, dont une que personne n'avait chiffrée

**Le prix de l'universalité est négatif.** Le mélange **nommé** de `f4` perd
−3,33·10⁻³ bit/tirage ; l'universel **adaptatif** en perd **54 fois moins**.
Un codeur qui apprend qu'il n'y a rien cesse de payer ; une grille
d'inclinaisons figées paie jusqu'au bout. Et cette économie ne coûte rien en
puissance au même ordre de contamination. Sur cette source et à cet horizon,
ne pas avoir à deviner la famille est **gratuit, et même rentable**.

**Une borne empirique pour le §13.2, sans supposer de récurrence.** Une classe
de 5 133 paramètres couvrant marginale, Markov ≤ 12, lags isolés, transitoires
et canal du bonus extrait **0 bit** des 4,35 Mbit — exactement ce que « un
état de 64 bits et plus n'y laisse rien » prédit.

**Et la limite de la promesse.** « Universel » veut dire universel *dans sa
classe*. Pas de contexte exogène en temps — mesuré par l'angle mort de
période 2 ; pas d'interaction intra-tirage, donc le couplage quadratique du
§40 est hors classe ; pas de lag au-delà de 12, donc le couplage à lag 204 du
§19 non plus. La sémantique est par lot, et les courbes de puissance ont deux
réplicats par point : des ordres de grandeur, pas des fréquences.

### Une entorse, disclosée

Le spécialiste des transitoires a été ajouté après qu'un témoin simulé eut
montré la classe initiale aveugle — alors qu'une passe de mise au point avait
déjà vu 8 000 tirages réels, qui ne montraient rien. La motivation vient de la
simulation et le résultat réel est nul de toute façon, mais le jeton définitif
a été scellé **après** ce regard, et cela se dit. C'est la troisième entorse à
la règle n° 2 consignée dans cette campagne, avec celles du §44 et du §49 —
toutes disclosées, aucune découverte à la clé.

**Registre : 3 entrées, piste C, lisibles sans Holm. Zéro significatif — et
cette fois sans avoir eu à nommer ce qu'on cherchait.**

## 53. Le contrôle séquentiel : la cagnotte comme processus, le capital comme état (`h36_sequentiel.py`)

Tout ce que le dossier a construit au-dessus de l'invariance décide **un
tirage à la fois**. Or la cagnotte est un **processus** (§28) : elle monte de
`r` par tirage et tombe avec probabilité `q`. Le joueur choisit à chaque
tirage entre agir et attendre, et personne n'avait posé cela comme ce que
c'est — un problème de contrôle markovien.

### Ce que vaut « attendre » : exactement zéro, et c'est démontré

L'objection qui motivait la question — « ne pas jouer aujourd'hui pour jouer
demain avec un capital intact » — supposerait que jouer consomme l'occasion
de demain. Il ne la consomme pas : les profits sont additifs, et si l'action
ne touchait pas la transition de la cagnotte, l'optimum serait **myope**,
donc exactement le seuil de bascule. Le témoin qui coupe ce canal le confirme
**au tirage près**. Le théorème M gagne ainsi un étage.

**Mais l'action touche la transition par un canal unique que le calcul
statique ne peut pas voir : gagner éteint la cagnotte.** Jouer ajoute `n·p`
au taux de chute et détruit, avec cette probabilité, la valeur future du
processus. La condition de Bellman tient en une ligne :

```
jouer en t  ⟺  J_t > S + (1−q)·h(t+1)     avec h ≥ 0
```

> Le seuil séquentiel est donc **toujours au-dessus** du seuil statique,
> jamais en dessous, et l'écart est gouverné par `n·p/q` — **la part du taux
> de chute que le joueur s'inflige à lui-même.**

| joueur | `n·p/q` | seuil optimal | coût d'ignorer |
|---|---|---|---|
| une grille parmi la foule | 0,052 | ≈ S | **0,131 %** — le §29 tient |
| 13 grilles, 67 % du taux de chute | 0,67 | **CHF 8 651** (S + 0,39 μ) | **10,2 %** |

Deux lectures opposées, et les deux comptent. Pour un joueur isolé, c'est un
**renforcement** du §5 bis, désormais appuyé sur une raison nommée. Pour
quelqu'un qui jouerait les treize grilles en pesant lourd dans le taux de
chute, c'est une **correction** : s'en tenir au seuil statique laisse un
dixième du profit.

Et la règle corrigée est **sans α** : comparer `n·p` au taux de chutes
observé — le comptage que le §36 fait déjà tenir à l'app — et ne relever le
seuil que si ce rapport est visible.

### Le théorème du compteur d'essais

Second état : la réserve `W`, avec le prix plancher du ticket — on n'achète
pas une fraction de ticket. Objectif : atteindre le régime de Kelly avant la
ruine. La réduction qui résout tout est l'invariance elle-même : **chaque
ticket gagne avec probabilité `p` quel que soit le niveau de cagnotte où il
est tiré.**

> **Théorème du compteur d'essais.** Pour *toute* politique — niveaux visés,
> nombre de grilles, géométrie, ordre des mises —
> `P(atteindre G avant la ruine) ≤ 1 − (1−p)^{W₀/c}`, et la borne est
> **atteinte** par la politique audacieuse-en-cagnotte : ne tirer un ticket
> que lorsque la cagnotte affichée suffit à elle seule à boucler l'objectif.
>
> Le capital est un compteur d'essais. Une politique ne choisit pas leur
> nombre, seulement le **niveau de cagnotte** où chaque essai est dépensé.

La borne ne contient **pas α** : 12,1 % depuis CHF 1 000, 72,5 % depuis
CHF 10 000. *Recoupé pour ce rapport : 12,102 % et 72,471 %.*

Son prix est le temps — viser le plancher de Kelly n'arrive qu'à 3,5·10⁻⁷ des
tirages, une occasion tous les 38 ans. En facturant le temps, on obtient une
frontière plutôt qu'un chiffre : 12,2 % en 2 800 ans, 10,3 % en 14 mois,
8,2 % en 105 jours.

**La forme de la politique est le résultat actionnable, et elle renverse le
§30.** Plus le capital est loin du but, plus il faut être **audacieux en
cagnotte** — viser haut, tirer rarement, mise minimale — et redescendre vers
le seuil ordinaire en approchant. Sous le plancher de capital, la bonne
réponse n'est donc **pas** de miser plus gros à chaque occasion : c'est de
miser aussi petit que possible sur des occasions plus rares et plus hautes.

Le nombre de grilles ne change pas la probabilité — mêmes essais — il divise
seulement la durée par 13. Et le théorème classique refait surface là où on
l'attend : à fort prix du temps, la politique optimale tire **sous** le seuil
de faveur, des paris d'espérance négative achetés contre du temps.
L'audace de Dubins-Savage n'avait pas disparu du problème ; elle attendait
qu'on facture le temps.

### La géométrie ne dépend pas de l'état — et le prouver a exigé de reproduire d'abord la bascule

Le théorème de bascule du §26 est **reproduit** sur un rang à gain fixe :
sous-équitable, concentrer gagne partout ; sur-équitable, étaler gagne
×12,8. *Une intuition corrigée en route : la première version attendait
« étaler près du but, concentrer loin » par la seule courbure de l'objectif.
La table a répondu concentrer sur toute la colonne sous-équitable —
l'érosion du capital entre deux gains stérilise les volées tardives.*

Mais le rang qui compte est **partagé**, et le partage tue la bascule :
13 grilles disjointes touchent `J/(1+W)` avec probabilité `13p` ; 13 tickets
empilés touchent `13J/(13+W)` avec probabilité `p`. **Empiler ne grossit pas
le pot, il le partage avec soi-même.** Le disjoint domine dans tous les
états, à tous les `λ` jusqu'à 5 inclus.

> **Conclusion pour l'app, actionnable par sa négation : NON, les douze
> grilles ne doivent pas changer de géométrie selon la cagnotte. Disjointes
> partout.** La bascule est réelle — le témoin la reproduit — mais elle n'a,
> dans ce jeu, aucun état où s'exercer : le régime convexe ne concerne que
> des rangs à gain fixe non partagés, or le rang joué au-dessus du seuil est
> le pot progressif, et sous le seuil la politique optimale est de ne rien
> miser.

### Ce qui survit à l'incertitude sur α

**Sans α** : la règle d'admission (corrigée par `n·p/q` **observé**, un
comptage et non une estimation), la borne du compteur d'essais et la
politique qui l'atteint, le nombre de grilles optimal et sa frontière, et la
géométrie disjointe dans tous les états. **Avec α** : les rythmes seuls —
combien d'occasions, combien de temps.

> Le **point** de la frontière qu'on occupe dépend de α ; la **forme** de la
> politique n'en dépend pas.

### Limites, et une confession de méthode

Tout repose sur H1–H3 du §28 et hérite de leurs réserves. Les rangs
intermédiaires sont ignorés — ils ne peuvent qu'adoucir (§50). Le `q` de
référence est celui du §36, pas une mesure, et c'est pourquoi la règle est
rendue en `n·p/q`. Tout est par franc misé.

*La première rédaction annonçait l'écart séquentiel « presque gratuit, de
second ordre » **avant** de l'avoir mesuré — il vaut 10,2 % pour un joueur à
treize grilles. La même faute une ligne plus loin a été purgée en rendant le
texte dépendant des valeurs calculées. Deux rappels que pré-écrire une
conclusion est exactement ce que `lab.preregister` interdit aux tests, et que
la discipline vaut aussi pour la prose.*

**Registre : inchangé.** Comme `h1`, `h14`, `h17`, `h25` et `h38`, `h36` ne
teste pas l'archive — il prouve, et il corrige.

## 54. Le triplet — la dernière case du produit cartésien (`h40_triplet.py`)

Les trois champs publiés ont chacun leur dossier, mais toujours **deux à la
fois** : le contenu conditionné au boost (`d5`), le bonus seul et contre le
tirage (`d7`, `d7b`, `h19`, `h22`), le boost seul (`b2`), le boost contre le
passé et l'horloge (`c3`, §49).

Le registre a été relu **entrée par entrée** : la seule qui mentionne les deux
mots, `c2.apprentissage`, est une prédiction en marche avant, pas un test du
couple. **L'interaction à trois n'apparaissait nulle part** — et ce n'est pas
une case vide par hasard. Le §32 a établi que le bonus est toujours l'un des
vingt numéros tirés : une **désignation**, pas un tirage. Si le boost et cette
désignation sortent du même flux, le lien serait invisible à tout ce qui
précède, puisqu'il ne touche aucune loi marginale.

### La décomposition qui délimite le test

Toute statistique brute du couple (bonus, boost) se décompose en une part qui
passe par le **contenu** du tirage — le territoire de `d5`, déjà dépensé — et
une part qui passe par la **désignation** conditionnellement au tirage. Chaque
trait du bonus est donc centré par sa moyenne **exacte** sur les vingt numéros
qui le portent : un lien contenu↔boost, quel qu'il soit, laisse ces contrastes
à espérance rigoureusement nulle.

> La case se remplit **sans re-dépenser la précédente**. L'orthogonalité à
> `d5` est acquise par construction, pas par mesure.

### La forme, imposée par la puissance

Les strates de boost 5 et 10 comptent environ 1 750 tirages chacune : six
tests par strate auraient été le test d'anniversaire du §34 — élégant, sans
dents. Six contrastes **plein échantillon** à la place, null exact par
permutation des étiquettes de boost comme dans `d5`, 2 000 réplicats :

| statistique | z | p |
|---|---|---|
| rang de la désignation (linéaire) | +1,30 | 0,194 |
| valeur relative au tirage | +1,14 | 0,258 |
| parité | +1,15 | 0,253 |
| χ² rang × boost (20×6) | −0,73 | 0,463 |
| bonus dans le tirage suivant, modulé | −0,02 | 0,985 |
| résidus mod 8 | +0,39 | 0,680 |

**Max |z| = 1,30** contre une loi du max à 1,59 ± 0,58 : **p = 0,662**,
conforme.

### Et cette fois le rien a des dents

| contamination | ε = 2 % | ε = 5 % | 80 % de puissance |
|---|---|---|---|
| désignation extrême sur boost ≥ 5 | 37 % | **100 %** | **ε ≈ 0,041** |
| diffus | 35 % | 100 % | — |
| canal des bits | 22 % | 97 % | — |
| sériel | 13 % | 92 % | — |

Témoin négatif à 4,5 % de fausse alarme ; témoins pleine force entre +79 et
+3 490 σ, **chacun sur son canal et muet ailleurs**. Là où `d5`, avec les
mêmes 70 560 tirages, ne voyait un lien de 5 % qu'à 72 %, le contraste ciblé
sur la désignation atteint 100 % — c'est le bénéfice d'avoir retranché le
contenu.

### Ce qu'un lien aurait valu

Le bonus est **post-clôture** : sa valeur directe est nulle par construction
(§49). L'enjeu était **forensique** — une désignation corrélée au boost aurait
signé un flux partagé et transporté les attaques d'état du §25 sur l'archive
entière au lieu de cinq tirages. Le seul canal à valeur directe, le lien
sériel modulé, plafonnerait sous les +0,02 % que `d7b` a mesurés pour sa
version pleine archive. **Un lien indétectable ici est donc aussi
inexploitable**, et le seuil du boost reste `ε ≈ 0,134` (§4), sans commune
mesure.

### Une erreur attrapée à la répétition générale

Le protocole a exercé tout le chemin — branche « résidu » comprise — sur une
archive synthétique à lien planté, **avant** de toucher l'appariement réel. La
répétition a montré un verdict « conforme » imprimé pour un `p` au plancher de
simulation (5·10⁻⁴, au-dessus du seuil de Holm) : la règle « candidate à
recalibrer » était dans le jeton scellé, mais **pas dans le code**. Corrigée
avant le run réel — qui n'en a pas eu besoin.

*Une correction de design, avant tout scellement : la première version prenait
des statistiques brutes (bonus mod 8 × boost non centré), qui se confondent
avec le canal contenu×boost déjà dépensé par `d5`. Le centrage intra-tirage
l'a réparée.*

### Limites

Le null suppose l'échangeabilité de la série des boost — mesurée nulle par
`b2` (p = 0,74 et 0,39). Le contraste linéaire concentre ~60 % de sa variance
sur `boost = 10`, ce qui est voulu (l'exploitabilité vit là) mais rend un lien
confiné aux boosts faibles moins visible ; le χ² omnibus couvre le non
monotone. Le test est aveugle à un lien de désignation ne touchant ni rang, ni
valeur relative, ni parité, ni `mod 8`, ni le tirage suivant — portée
délimitée **par mesure**, via les quatre témoins.

**Registre : 145 entrées, m = 3 325, zéro significatif. Le produit cartésien
des trois champs publiés est clos** — marginales, paires, et désormais le
triplet.

## 55. La composition des deux seuils, et une convention qu'il a fallu retrouver (`h41_composition_seuils.py`)

> **Refait sur l'observé au §57.** Les trois entrées supposées de cette
> section — le ticket à un franc, la borne `ρ ≥ 0,245`, l'accumulation
> déduite — ont depuis été observées. Le §57 refait le calcul avec la même
> machine et une ablation entrée par entrée : le CHF 6 724 ci-dessous
> devient CHF 7 142, et il n'en était proche que parce que deux erreurs
> allaient en sens opposés.

Deux sections de cette campagne corrigent le seuil de bascule du §5 bis, **en
sens opposés** :

- le §50 le fait **descendre** — les rangs intermédiaires valent `ρ ≥ 24,5 %`,
  donc le pari devient favorable plus tôt : CHF 7 753 → 5 853 ;
- le §53 le fait **monter** — jouer ajoute `n·p` au taux de chute et détruit
  la valeur future du processus : CHF 8 651 pour treize grilles.

Chacune a été établie **en supposant l'autre absente**, et elles ne sont pas
indépendantes : abaisser le seuil fait jouer plus souvent, donc contribuer
davantage au taux de chute. Personne n'avait dit de combien la composition
s'écarte d'une addition, ni dans quel sens.

### Une convention non nommée, qui valait un tiers du résultat

Le §53 ne dit pas ce que désigne son `q`, et la réponse change son chiffre de
33 %. Deux lectures :

| convention | `q` désigne | auto-extinction seule |
|---|---|---|
| **B** — celle du §53 | le taux dû aux **autres**, notre joueur s'ajoute | **CHF 8 651** |
| A | le taux **total observé**, notre joueur inclus | CHF 11 532 |

Ce n'est l'erreur de personne : ce sont **deux joueurs différents**. B décrit
celui qui se demande s'il doit *se mettre* à jouer ; A celui dont l'activité
est déjà comprise dans le taux mesuré. La reconstitution en B retombe sur
CHF 8 651 **au franc près**, ce qui identifie la convention du §53 sans
ambiguïté — et une divergence de 33 % qu'on ne nommerait pas serait une
erreur en attente.

### Les contrôles avant le résultat

| | attendu | obtenu | écart |
|---|---|---|---|
| seuil nu | S = 7 753 | 7 753 | 0,00 % |
| rangs intermédiaires seuls | (1−ρ)S = 5 853 | 5 855 | 0,02 % |
| auto-extinction seule | §53 : 8 651 | 8 651 | 0,00 % |

Les trois tombent juste : le modèle est en accord avec les deux sections
qu'il compose, et ce qui suit est une prédiction, pas un réglage.

### La composition

```
addition naïve des deux corrections     CHF 6 752
composition exacte                      CHF 6 724
écart                                   CHF   −29   (−0,42 %)
```

L'addition naïve est donc une excellente approximation — moins d'un demi pour
cent — mais **le sens de l'écart est instructif, et il n'est pas celui qu'on
devine.**

On s'attend à ce qu'un seuil plus bas fasse jouer plus souvent — c'est vrai,
la fraction jouée passe de 3,37 % à 5,29 % — donc à ce que la pénalité
d'auto-extinction s'alourdisse et pousse le seuil **au-dessus** de la somme.
C'est l'effet inverse qui l'emporte : avec les rangs intermédiaires, chaque
tirage joué rapporte davantage **immédiatement**, si bien que la valeur future
détruite par un gain pèse relativement **moins**.

> Les rangs intermédiaires ne se contentent pas d'abaisser le seuil : ils
> rendent aussi l'auto-extinction moins coûteuse. La première correction
> **atténue** la seconde.

### Le chiffre pratique

| n grilles | n·p/q | seuil composé | vs (1−ρ)S | vs S nu |
|---|---|---|---|---|
| 1 | 0,05 | CHF 5 958 | ×1,018 | ×0,768 |
| 3 | 0,15 | CHF 6 141 | ×1,049 | ×0,792 |
| 6 | 0,31 | CHF 6 364 | ×1,087 | ×0,821 |
| **13** | **0,67** | **CHF 6 724** | ×1,149 | **×0,867** |

Pour un joueur à **une grille**, l'auto-extinction est négligeable et la
correction du barème s'applique telle quelle. Pour **treize grilles**, le
seuil composé vaut CHF 6 724 — soit **13 % sous le seuil nu**, et les
occasions favorables passent de 3,37 % à **5,29 %** des tirages.

> Les deux corrections ne s'annulent pas, et **celle qui compte le plus est
> celle qui abaisse le seuil.**

### Limites

Le modèle hérite de H1–H3 du §28 et de `ρ ≥ 0,245`, lui-même conditionnel aux
hypothèses nommées au §50 : rien ici n'est plus solide que le maillon le plus
faible de cette chaîne. Les collisions sont négligées à `O((n·p)²)`. Le `q` de
référence n'est pas une mesure, d'où la table en `n·p/q`. Et la convention B
suppose que le joueur **s'ajoute** au marché observé : s'il y est déjà compté,
c'est A qui vaut et le seuil monte.

**Registre : inchangé.** `h41` ne teste pas l'archive — il compose.

## 56. Le barème, lu (`h42_bareme_reel.py`)

> **Confirmé et corrigé au §62.** Le prix du ticket déduit ici — `c > CHF 1,20`,
> donc `c = 2` — est **confirmé par le règlement officiel** : la déduction était
> juste et `c = 2` cesse d'être une hypothèse. En revanche la limite n° 3
> ci-dessous est **fausse** : elle calcule l'espérance de l'option EXTRA en lui
> appliquant la loi hypergéométrique de la grille de base, ce qui donne 365 à
> 557 % de taux de retour selon la mise. La colonne EXTRA n'obéit pas à cette
> loi. Sa conclusion (« elle n'est pas gratuite ») est vraie, mais par accident.

Le §50 s'est achevé sur une phrase :

> « Un document lèverait `w_h` exactement et rendrait `h34` obsolète : zéro
> relevé, zéro modèle, la demande la moins chère du dossier. »

Le document est arrivé — cinq tableaux de gains relevés sur `jeux.loro.ch` le
30 août 2026 à 22:16, plus un second relevé de cagnottes treize heures après
le premier. `lab/bareme_observed.csv` et `lab/jackpots_observed.csv` les
portent. Cette section fait exactement ce que cette phrase annonçait, et rien
de plus : elle lit, vérifie, recalcule.

### Le contrôle qui valide la transcription — et qui est aussi le résultat

Le risque n'est pas statistique, il est **de lecture** : ces chiffres viennent
de captures d'écran lues à l'œil. Relire le tableau ne prouve rien. Mais les
cinq tableaux ont été lus séparément, et un opérateur égalise son taux de
retour entre les mises. Si les cinq espérances tombent ensemble, la
transcription est bonne **et** l'égalisation est démontrée. Si l'une décroche,
un chiffre est faux.

| mise | E[gain de base] | P(k/k) | 1/P |
|---|---|---|---|
| 5 | 1,1711 | 6,449 × 10⁻⁴ | 1 551 |
| 6 | 1,1765 | 1,290 × 10⁻⁴ | 7 753 |
| 7 | 1,1971 | 2,440 × 10⁻⁵ | 40 979 |
| 8 | 1,1668 | 4,346 × 10⁻⁶ | 230 115 |
| 10 | 1,1761 | 1,122 × 10⁻⁷ | 8 911 711 |

Étendue : **2,57 %**. Cinq tableaux mal lus ne se seraient pas rejoints.

Et c'est en même temps une mesure. Le §50 avait **démontré**, sur 4 081
barèmes admissibles, que chaque décision du dossier ne dépend que du scalaire
total et non de la forme du barème — donc que le « classement des mises par
espérance » de `b2` était vide par identité comptable. Le théorème de collapse
est ici **observé** sur le barème réel.

### Le prix du ticket : un franc est arithmétiquement exclu

Le taux de retour vaut `E/c` et ne peut pas dépasser 1. La mise 7 rend donc

> **`c > CHF 1,1971`**

Tout le dossier lisait « par franc misé » faute de mieux, et cette lecture par
défaut est **fausse** : à `c = 1` l'opérateur perdrait de l'argent sur chaque
mise avant même de servir la cagnotte. Ce n'est pas une hypothèse, c'est une
déduction à partir du barème.

| prix supposé | taux de retour de base |
|---|---|
| CHF 1,00 | 117,8 % — exclu |
| CHF 1,50 | 78,5 % |
| **CHF 2,00** | **58,9 %** |
| CHF 2,50 | 47,1 % |
| CHF 3,00 | 39,3 % |

La suite prend `c = 2`, seule valeur ronde compatible donnant un retour
plausible pour une loterie. C'est **la dernière hypothèse** de toute la chaîne
financière, et elle se lève d'un coup d'œil sur le prix affiché.

### Les rangs intermédiaires, exacts

Le §50 les bornait par comptabilité : `ρ ≥ 0,245` sous hypothèses nommées.

| mise | rang plein | rangs intermédiaires | ρ = interm/c | borne §50 |
|---|---|---|---|---|
| 5 | 0,2322 | 0,9389 | **0,469** | ≥ 0,245 ✔ |
| 6 | 0,1290 | 1,0475 | **0,524** | ≥ 0,245 ✔ |
| 7 | 0,0488 | 1,1483 | **0,574** | ≥ 0,245 ✔ |
| 8 | 0,0435 | 1,1234 | **0,562** | ≥ 0,245 ✔ |
| 10 | 0,0112 | 1,1649 | **0,582** | ≥ 0,245 ✔ |

La borne **tient sur les cinq mises**, et elle était conservatrice d'un
facteur **2,1** à la mise 6. C'est le comportement attendu d'une borne :
vraie, et lâche.

### Le seuil, sans plus aucune condition suffisante

Le pari est favorable quand `E[base] + p·J ≥ c`, soit

> **`J* = (c − E[base]) / p`**

Plus rien n'est jeté : ni les rangs intermédiaires, ni le gain fixe du rang
plein. Le §5 bis donnait une condition **suffisante** en ignorant tout cela ;
voici la condition **nécessaire et suffisante**.

| mise | seuil §5 bis (`c/p`) | seuil **exact** | rapport | cagnotte 30/08 22:16 | fraction |
|---|---|---|---|---|---|
| 5 | 3 101 | **1 285** | 0,414 | 245 | 19,1 % |
| 6 | 15 506 | **6 385** | 0,412 | 3 035 | **47,5 %** |
| 7 | 81 959 | **32 902** | 0,401 | 3 838 | 11,7 % |
| 8 | 460 229 | **191 727** | 0,417 | 13 051 | 6,8 % |
| 10 | 17 823 422 | **7 342 190** | 0,412 | 498 218 | 6,8 % |

Le seuil réel vaut environ **41 %** du seuil suffisant employé depuis le §5
bis. La mise 6 est à **48 %** de son point de bascule, contre les 29,5 %
qu'annonçait le §21 sur le premier relevé. Le §21 avait vu juste sur la
structure : les petites mises sont systématiquement les plus proches, et la
mise 6 domine.

### Deux relevés : l'accumulation mesurée, et la première chute

155 tirages séparent les deux relevés (09:17 → 22:16, un toutes les cinq
minutes).

| mise | 09:17 | 22:16 | variation | accumulation `r` |
|---|---|---|---|---|
| 5 | 355 | 245 | −110 | **chute observée** |
| 6 | 2 287 | 3 035 | +748 | 4,83 CHF/tirage |
| 7 | 1 540 | 3 838 | +2 298 | 14,83 CHF/tirage |
| 8 | 9 292 | 13 051 | +3 759 | 24,25 CHF/tirage |
| 10 | 495 713 | 498 218 | +2 505 | 16,16 CHF/tirage |

Deux acquis, et le second est le plus rare. **L'accumulation est mesurée** :
4,83 CHF par tirage à la mise 6, là où le §36 supposait 5,72 faute de mieux —
16 % d'écart. Et **une chute a été observée**, la première du dossier. Le §36
a montré que l'information sur la loi de la cagnotte arrive au rythme des
chutes et non des relevés : celle-ci est donc la première unité d'information
sur `q`, et il en faut une dizaine pour situer le paramètre à un facteur 3
près.

### Ce que cette section remplace, et ce qu'elle confirme

**Remplace.** Le §50 tout entier — sa comptabilité, sa borne `ρ ≥ 0,245`, son
espace admissible, son catalogue de 72 tables. Il existait pour contourner
l'absence du barème, il l'avait annoncé, et il a eu raison de le dire.

**Confirme.** Le théorème de collapse du §50, mesuré. La structure du §21. Et
la méthode : une borne honnête, posée sans le barème, n'a été ni fausse ni
inutile — elle a simplement été dépassée par une donnée, comme une borne doit
l'être.

### Limites

1. **Transcription à l'œil** depuis des captures. Le contrôle des cinq
   espérances la valide indirectement ; il ne la remplace pas.
2. **`c = 2` est une hypothèse**, et tous les seuils lui sont proportionnels
   en `(c − E)/p` — donc très sensibles : à `c = 2,50`, le seuil de la mise 6
   passe de 6 385 à **10 261**.
3. **L'option EXTRA n'est pas traitée** : son prix et sa portée ne sont pas
   lisibles sur les captures. Son espérance seule vaut 9,99 CHF à la mise 6,
   ce qui exclut qu'elle soit gratuite.
4. Le relevé est à **BOOST ×1** ; le boost multiplie les gains et déplacerait
   tout ce tableau (§31).
5. Le **numéro de tirage** du second relevé n'est pas lisible sur la capture :
   il est déduit (1 381 028 + 155) et marqué d'un « ? » dans le CSV pour cela.
   Rien ici n'en dépend au-delà du pas de temps.

**Registre : inchangé.** `h42` ne teste pas l'archive — il lit et recalcule.

> Le plus grand gain pratique de la session ne vient d'aucun théorème : il
> vient d'une capture d'écran. Le §50 l'avait écrit avant de l'obtenir.

## 57. Le seuil refait sur l'observé, et le maillon qui se déplace (`h43_seuil_observe.py`)

> **Limite n° 1 levée au §62.** `c = 2` n'est plus une hypothèse : le règlement
> officiel le donne. La sensibilité déclarée plus bas — « à `c = 2,50` le seuil
> passe à 10 261 » — est sans objet. Le seuil statique vaut **CHF 6 385**, et le
> maillon faible de la chaîne reste `q`, comme cette section le concluait.

Le §55 s'est achevé sur une phrase qui désignait sa propre faiblesse :

> « Le modèle hérite de H1–H3 du §28 et de `ρ ≥ 0,245`, lui-même conditionnel
> aux hypothèses nommées au §50 : rien ici n'est plus solide que le maillon
> le plus faible de cette chaîne. »

Le maillon nommé était une **borne**. Le §56 l'a remplacé par une **mesure**,
et a fait tomber deux autres entrées du même calcul au passage. Cette section
reprend la machine du §55 mot pour mot et substitue ses entrées **une à une**,
pour que chaque franc de déplacement soit attribuable à une observation et non
au modèle.

### Le contrôle, avant toute chose

Avec les entrées du §55 — `c = 1`, `ρ = 0,245`, `r = 5,7175` — le solveur doit
refaire ses quatre chiffres publiés.

| | publié §55 | obtenu | écart |
|---|---|---|---|
| nu (§5 bis) | CHF 7 753 | 7 753 | 0,00 % |
| rangs seuls (§50) | CHF 5 855 | 5 855 | 0,00 % |
| auto-extinction seule (§53) | CHF 8 651 | 8 651 | 0,00 % |
| **les deux (§55)** | CHF 6 724 | 6 724 | 0,00 % |

C'est la même machine. Ce qui suit ne dépend donc que des **entrées**.

### L'ablation

| entrée | §55 (supposé) | §56 (observé) |
|---|---|---|
| prix du ticket `c` | CHF 1,00 | **CHF 2,00** (déduit ; `c > 1,1971` prouvé) |
| retour de base | `ρ ≥ 0,245` | **`E/c = 0,5882`** (mesuré, exact) |
| accumulation `r` | 5,718 CHF/tirage | **4,826 CHF/tirage** (mesuré sur 155 tirages) |

Treize grilles, auto-extinction active :

| étape | seuil composé | déplacement |
|---|---|---|
| §55 tel que publié | CHF 6 724 | — |
| + prix du ticket réel | CHF 12 624 | **+5 900** (+87,8 %) |
| + retour de base exact | CHF 7 267 | **−5 357** (−42,4 %) |
| + accumulation mesurée | **CHF 7 142** | −125 (−1,7 %) |

> Les deux erreurs du §55 allaient en **sens opposés** et se sont largement
> compensées. Le chiffre publié était à +6,2 % du chiffre observé — **pour
> deux raisons qui se sont annulées.** C'est un accident, pas une méthode, et
> c'est exactement le genre de coïncidence qu'une ablation rend visible et
> qu'un recalcul global aurait masquée.

L'accumulation mesurée, elle, ne bouge le seuil que de −1,7 % : elle n'agit
que par `μ = r/q`, donc sur la valeur d'**attendre** — une cagnotte qui monte
moins vite rend l'attente moins payante. Son effet massif est ailleurs, sur la
fréquence, où elle entre en exponentielle.

### Deux chiffres que le §55 confondait

**Le seuil statique** — une grille, joueur qui ne se demande pas ce que son
propre gain détruit :

> `J* = (c − E)/p = (2,00 − 1,1765) / 1,2898·10⁻⁴ = ` **CHF 6 385**

Il ne dépend plus d'**aucune** borne ni d'aucun taux : le barème est lu, le
gain **fixe** du rang plein est compté — le §55 l'oubliait — et sa seule
hypothèse est le prix du ticket. C'est le chiffre solide. (Contrôle : le
solveur à `n = 1` sans auto-extinction le retrouve à 0,07 %.)

**Le seuil composé** — treize grilles, auto-extinction :

| n grilles | n·p/q | seuil composé | prime d'auto-extinction |
|---|---|---|---|
| 1 | 0,05 | CHF 6 476 | +1,4 % |
| 3 | 0,15 | CHF 6 635 | +3,9 % |
| 6 | 0,31 | CHF 6 829 | +6,9 % |
| **13** | **0,67** | **CHF 7 142** | **+11,9 %** |

Mais cette prime dépend de `n·p/q`, donc d'un `q` qui n'est **pas mesuré**.
Le §55 publiait un unique CHF 6 724 sans marquer cette dépendance.

### Ce que la première chute ne dit pas

Une chute a été observée (§56) : mise 5, de 355 à 245 sur 155 tirages. Un
événement de Poisson sur 155 tirages donne un intervalle à 95 % de
[0,0253 ; 5,572] événements, donc

> `q(mise 5) ∈ [1/6 126 ; 1/28]` — **un facteur 220.**

Le §36 l'avait annoncé : l'information sur la loi de la cagnotte arrive au
rythme des **chutes**, et il en faut une dizaine pour situer `q` à un facteur
3 près. **Une seule ne situe rien.** D'où la table en `q` :

| q | n·p/q | seuil composé | μ = r/q | fraction favorable |
|---|---|---|---|---|
| 1/150 | 0,25 | CHF 6 534 | 724 | 0,012 % |
| 1/200 | 0,34 | CHF 6 631 | 965 | 0,104 % |
| 1/300 | 0,50 | CHF 6 867 | 1 448 | 0,871 % |
| **1/400** | **0,67** | **CHF 7 142** | **1 930** | **2,472 %** |
| 1/600 | 1,01 | CHF 7 741 | 2 895 | 6,902 % |
| 1/1000 | 1,68 | CHF 8 937 | 4 826 | 15,692 % |
| 1/2000 | 3,35 | CHF 11 587 | 9 652 | 30,104 % |

Les deux colonnes ne réagissent pas à la même échelle : sur toute la plage le
seuil monte d'un facteur **1,8**, la fréquence d'un facteur **2 505**. Le
seuil monte parce qu'une cagnotte qui tombe rarement vit longtemps, ce qui
rend l'attente plus payante.

### Le maillon s'est déplacé

Le maillon faible que le §55 nommait — `ρ ≥ 0,245` — a été remplacé par une
mesure, et la mesure était **deux fois plus généreuse** que la borne. Le
maillon faible n'est donc plus le barème :

> **C'est `q`.** Et `q` ne s'observe qu'en comptant des **chutes**, pas des
> relevés — une donnée que ni l'archive ni un document ne peuvent fournir, et
> que seule l'app en fonctionnement accumulera.

### Limites

1. `c = 2` reste la dernière hypothèse. Le seuil statique lui est
   proportionnel en `(c − E)/p` : à `c = 2,50` il vaut CHF 10 261 au lieu de
   6 385.
2. `q` n'est pas mesuré ; la prime d'auto-extinction va de +2 % à +82 % sur
   la plage, et la fréquence des occasions n'est pas connue à un ordre de
   grandeur près.
3. H1–H3 du §28 tiennent toujours. Le plancher nul est le cas le moins
   favorable au joueur ; les deux autres ne sont pas vérifiées.
4. L'option EXTRA n'entre pas dans ce calcul (§56, limite 3).

**Et ce qui ne change pas.** Rien de tout ceci ne dit quels numéros cocher.
L'espérance de hits vaut `k/4` quel que soit le choix (§1). Ce seuil porte sur
l'**instant**, jamais sur la grille — et c'est la seule chose du dossier qui
fasse changer l'espérance de signe.

**Registre : inchangé.** `h43` ne teste pas l'archive — il recompose.

## 58. Le quatrième cas : cette fois, on câble (`PayTable.swift`)

Le §51 a énoncé le principe du dossier une fois pour toutes :

> « Un résultat théorique qui déplacerait un seuil affiché ne se câble que si
> la démonstration ne repose que sur des quantités **observables**. Le seuil
> actuel `J ≥ c/p` en est une : `J` est à l'écran, `p` est une combinatoire
> exacte, `c` se lit sur un ticket. Le seuil `(1−ρ)·c/p` n'en est pas une tant
> que `ρ` repose sur un taux de retour **supposé**. »

Trois fois cette règle a fait refuser un câblage. Le §56 a levé la condition
qu'elle nommait : `ρ` n'est plus supposé, il est **lu**. Le quatrième cas se
câble donc, et pour la raison exacte que les trois premiers ne se câblaient
pas.

### Ce que la carte du jackpot fait maintenant

| | avant | après |
|---|---|---|
| règle | `J·p ≥ 1` — condition **suffisante**, ticket supposé à 1 franc | `E[base] + J·p ≥ c` — condition **nécessaire et suffisante** |
| seuil affiché (mise 6) | 100 ct/CHF | **41,2 ct/CHF** à `c = 2` |
| rangs intermédiaires | jetés | comptés |
| gain **fixe** du rang plein | jeté | compté |
| prix du ticket | supposé | **réglage**, CHF 1 absent de la liste |

`Prophet/Models/PayTable.swift` porte le barème des cinq mises et calcule
`E[base]` par la loi hypergéométrique. `JackpotLaw.threshold` accepte un prix
et rend `(c − E)/p` quand il est renseigné.

### Ce qui se passe quand le prix n'est pas renseigné — et c'est le défaut

La carte retombe **exactement** sur son comportement précédent : `c = 1`,
`E = 0`, seuil 100 ct/CHF. Aucune régression, aucun chiffre nouveau affiché
sur la foi d'une hypothèse.

Mais elle dit désormais ce que ce comportement suppose, et cette réserve
n'était pas visible sans le barème :

> La règle des 100 ct/CHF n'est une condition suffisante que si le ticket
> coûte **au plus CHF 2,17** (= `1 + E[base]`, la mise 8 étant la plus
> contraignante). Au-delà, elle annoncerait « favorable » **à tort**.

C'est le genre exact d'énoncé que le §5 bis reprochait à l'app quand elle
affirmait « l'espérance totale reste négative » sans condition. La différence
est qu'il est maintenant écrit à l'écran plutôt que découvert plus tard.

Le réglage de prix ne propose pas CHF 1. Ce n'est pas un choix d'ergonomie :
`setTicketPrice` **refuse** tout prix sous CHF 1,1971, parce qu'au-dessous le
taux de retour de l'opérateur dépasserait 1 — une contradiction, pas une
improbabilité.

### Le piège que le nouveau seuil introduisait

Le gain conditionnel du §32 valait `μ/S` par absence de mémoire (h16). Cette
écriture n'était juste que **parce que** `S·p = c` avec le seuil suffisant.
Avec le seuil exact, `S·p = c − E`, et garder `μ/S` aurait surestimé le gain
d'un facteur `c/(c − E)` — **×2,43 à `c = 2`.**

La formule devient `μ·p/c`, qui redonne `μ/S` quand le prix est inconnu. Un
test nomme le piège et vérifie le facteur.

> C'est la forme la plus insidieuse d'erreur dans ce dossier : une identité
> vraie qui cesse de l'être parce qu'une **autre** quantité a été corrigée.
> Rien ne l'aurait signalée — le nombre serait resté plausible.

### Vérification

Aucune toolchain Swift n'est joignable depuis cet environnement (note datée du
§53). Les deux vérificateurs du dépôt passent :

- **`verif_swift.py`** — grammaire Swift réelle (`tree-sitter`) : **0 nœud de
  syntaxe invalide introduit** sur les six fichiers touchés.
- **`verif_logique.py`** — gagne une section 9 qui transcrit l'algorithme de
  `PayTable.swift` (somme de `log(i)` pour `log(n!)`, puis exponentielle de la
  différence) et le confronte au calcul **exact en Fractions**, ce que Swift ne
  peut pas faire : écart relatif maximal **5,7·10⁻¹⁴**, masse
  hypergéométrique à 5,6·10⁻¹⁴ de 1.

Quatre tests XCTest sont ajoutés. L'un d'eux prend la **transcription** pour
cible : les cinq espérances doivent tomber à 3 % près, ce qu'une seule ligne
mal saisie ferait échouer. Le test de non-régression est explicite —
`JackpotLaw.threshold(pAllHit:)` sans prix doit rendre exactement 7 753.

### Ce que cela laisse ouvert

Le prix du ticket est maintenant **saisissable** mais toujours pas **su**. Le
câblage ne l'invente pas : il rend l'app capable d'employer la réponse dès
qu'elle sera lue, et honnête sur ce qu'elle suppose en attendant. C'est la
seule chose qu'un dossier puisse faire d'une observation qu'il n'a pas encore.

## 59. Le mur de la piste A est un mur d'estimateur (`h44_parcimonie.py`)

> **CORRIGÉ AU §61, et sur sa conclusion même.** Le gain d'estimateur mesuré
> ici (×1,64, apparié, positif sur cinq archives) tient. La conclusion qu'on en
> tire — « le maximum de la piste A passe à au moins +2,16 % » — est **fausse** :
> elle multiplie une part captée améliorée par un plafond d'omniscience calculé
> contre le χ² seul, alors que le §60 venait d'ajouter deux détecteurs qui font
> tomber ce plafond de 44 % à `s = 50`. Le net vaut **1,20 %** contre 1,32 %
> publié : le mur n'a pas bougé. Les tableaux ci-dessous restent exacts ; c'est
> leur mise en produit qui ne l'était pas.

Trois sections ferment la piste A — prédire les numéros — par une paire de
lois d'échelle qui se compensent : le plafond d'omniscience croît en `m^(1/4)`
(§41), le SNR d'identification décroît en `m^(−1/4)` (§42), la courbe se
retourne et le maximum réalisable vaut **+1,28 %** (§48).

Le point aveugle tient en une ligne de `h31` :

```python
v = rng.normal(size=m); v -= v.mean(); v *= norm / rms(v)
```

**La déviation du §42 est isotrope.** Toutes les cellules portent du signal,
aucune n'est vide. C'est le cas **dense**, et c'est le pire pour
l'identification : il n'y a rien à éliminer.

Or les familles que le §45 mesure ne sont pas denses. Les paires cachées
portent **50 entrées non nulles sur 6 400**. Le tenseur quadratique, **80 sur
252 800**. Et l'identificateur que le §45 leur applique — `IdentLin`, variante
`raw`, `score = Ĉ @ xc` — emploie la matrice empirique **entière**, dont
6 350 entrées ne contiennent que du bruit. Sa variante `amax` n'en garde
qu'une par ligne. Les deux bouts, jamais le milieu.

### L'énoncé, en trois lignes

Une déviation reste sous le seuil du χ² tant que `‖C‖²/σ² ≤ z·√(2m)`. Portée
par `s` cellules d'amplitude `c`, cela donne le SNR **par cellule** :

> **`(c/σ)² = z·√(2m) / s`**

Deux régimes, et ils ne diffèrent que par ce qu'on met dans `s` :

| | `s` | `(c/σ)²` | exposant |
|---|---|---|---|
| dense | `m` | `z√2/√m` | **`m^(−1/4)`** — c'est le §42 |
| creux | fixé | `z√(2m)/s` | **`m^(+1/4)`** |

L'exposant **change de signe**. Le point neutre est `s = √m` (Théorème O).

| famille | m | s | SNR par cellule |
|---|---|---|---|
| dense (rémanence, marginal) | 80 | 80 | 0,83 |
| paires cachées | 6 400 | 50 | **3,13** |
| quadratique | 252 800 | 80 | **6,20** |

Une cellule active des familles réelles est à trois ou six écarts-types du
bruit. Elle est reconnaissable **une par une** — le fait que le cas dense
interdit, et que le §42 n'a pas eu l'occasion de voir.

### La machine du §42, une seule ligne changée

`h31.captured` est repris mot pour mot — même sélection des `K` meilleures
cellules, même `K/m = 1/8`, même estimateur de fréquence. Seule la loi de la
déviation change. `s = 32`, `N = 20 000`, `z = 4,33` d'un null simulé :

| m | part captée, dense | part captée, creuse |
|---|---|---|
| 64 | 0,681 | 0,624 |
| 256 | 0,520 | 0,696 |
| 1 024 | 0,389 | 0,811 |
| 4 096 | 0,314 | **0,920** |

Exposant **−0,189** (dense) contre **+0,095** (creux).

> **Le contrôle qui autorise à lire la seconde colonne.** L'exposant dense
> donne un plafond réalisable en `m^(+0,061)`. Le §42 publie **+0,0616**. La
> transcription refait donc le dossier à trois décimales, et ce qui suit n'est
> pas un réglage.

Aucun estimateur nouveau n'intervient ici : la **même** procédure, appliquée à
une déviation creuse plutôt qu'isotrope, ne se dégrade pas. Le §42 n'a pas
mesuré une loi de l'identification — il a mesuré **la loi de l'identification
des familles denses**.

### Là où l'estimateur commence vraiment à compter

Dans le modèle ci-dessus le joueur **classe** les cellules par leur
estimation : toute transformation croissante donne le même classement, donc
rétrécir ou seuiller n'y changerait rigoureusement rien.

Le §45 n'est pas dans ce cas. Sa matrice n'est pas classée, elle est
**appliquée** : `score = Ĉ @ xc`, et chacune des 6 400 entrées verse sa part
de bruit dans les 80 coordonnées du score. Une transformation par entrée n'est
alors plus inoffensive. L'alignement se lit sur le cosinus entre la matrice
employée et la vraie :

| famille | m | s | cos brut | cos seuillé | gain |
|---|---|---|---|---|---|
| paires cachées | 6 400 | 50 | 0,2666 | 0,6086 | **×2,28** (τ = 3) |
| quadratique | 252 800 | 80 | 0,1097 | **0,9397** | **×8,57** (τ = 4) |

Le gain **croît avec m**, exactement comme l'énoncé le prédit : le nombre
d'entrées à jeter croît, `s` ne bouge pas. À `m = 252 800`, un seuillage par
entrée récupère un alignement de **0,94** là où la matrice brute plafonne à
0,11.

### Sur une archive contaminée réelle, en marche avant

Famille « paires cachées » du §45, générateur `c1.gen_conditional` importé
sans réécriture, `d = 0,0071` (l'amplitude de frontière consignée par c1,
jamais recalculée), `K = 10`, cinq archives de 70 560 tirages, warmup 20 000,
marche avant stricte via `lab.walk_forward`. Le seuil n'est pas ajusté sur la
vérité : `σ̂` vient de l'écart médian absolu des entrées de la matrice — une
statistique de ce que le joueur a sous les yeux.

| identificateur | E[hits] | avantage | part captée |
|---|---|---|---|
| base (grille fixe) | 2,4959 | — | (théorème : 2,5000) |
| **oracle** | 2,5810 | +0,0851 | 1,000 |
| brut (le §45) | 2,5171 | +0,0213 | 0,247 ± 0,033 |
| seuillé τ = 2,5 | 2,5302 | +0,0343 | **0,404 ± 0,012** |

Les niveaux absolus varient beaucoup d'une archive à l'autre. La comparaison
qui porte le résultat est donc **appariée** — même archive, même oracle, deux
identificateurs :

> par archive : **+0,202  +0,255  +0,058  +0,162  +0,110**
> moyenne **+0,157 ± 0,034**, positif sur **les cinq**.

### Ce que le maximum du §48 devient

**Un contrôle échoue ici, et il décide de ce qu'on a le droit de conclure.** La
variante brute est censée être celle du §45, qui publie 0,41 ; on obtient
0,247, soit **40 % d'écart**, et la cause n'est pas établie. Les niveaux ne se
transportent donc pas — seul le **rapport** ×1,64 se transporte, appliqué au
0,41 publié :

| famille | m | plafond | captée §45 | réalisable §45 | **corrigé** |
|---|---|---|---|---|---|
| rémanence uniforme | 1 | 0,53 % | 1,00 | 0,53 % | — |
| marginal | 80 | 1,33 % | 0,64 | 0,85 % | — |
| **paires cachées** | 6 400 | 3,21 % | 0,41 | 1,32 % | **2,16 %** |
| quadratique | 252 800 | 6,27 % | 0,11 | 0,69 % | non mesuré |

> Ce seul point déplace le maximum de la piste A de **+1,28 %** à **au moins
> +2,16 %**, puisque le maximum est un maximum sur les points.

Et c'est le point quadratique, non mesuré ici, où le gain serait le plus grand
— la section précédente y mesure un gain d'alignement de ×8,57 contre ×2,28.
Le mesurer demande de refaire le protocole de h24 ; ce fichier le **désigne**
plutôt que de prétendre l'avoir fait.

### Ce que ceci ne fait pas

**Cela ne casse pas le théorème d'invariance.** `E[hits] = k/4` pour toute
grille sous un tirage échangeable. Tout ce qui précède se passe sur des
archives **contaminées par construction** ; sur l'archive réelle, les tests du
registre restent négatifs.

**Cela ne bat pas la marge.** Le maximum passe de +1,28 % à au moins +2,16 %,
contre une marge de l'opérateur de 41 % (§56). Il manque toujours un facteur
**vingt**, et aucune des deux quantités n'a bougé assez pour que les courbes
se croisent.

**Ce que cela fait.** Cela retire au dossier le droit de dire que le mur est
une propriété de la **nature** du problème. Le §48 écrivait un maximum ; ce
maximum était celui d'un couple **(famille, estimateur)**, et l'estimateur
n'était pas le bon pour les familles concernées.

### Limites

1. Un seul point est refait. Le quadratique, où le gain serait le plus grand,
   est désigné et non mesuré.
2. Le seuillage **dur** par entrée n'est pas optimal — le seuillage doux et la
   moyenne a posteriori sous un a priori de parcimonie feraient mieux. Ce qui
   est établi est une **borne inférieure** sur ce qu'un bon estimateur capte.
3. L'écart de 40 % entre la variante brute mesurée ici et celle du §45 n'est
   pas expliqué. Seul le rapport est transporté, ce qui est la lecture
   conservatrice, mais l'écart reste une dette.
4. La section sur la machine du §42 hérite de sa limite n° 3 : le joueur y
   estime sur les mêmes données que le test, ce qui la rend **majorante**. La
   mesure sur archive contaminée, elle, est en marche avant stricte.

**Registre : inchangé.** `h44` ne teste pas l'archive — il démontre et mesure
sur des contaminations connues.

## 60. Le détecteur qui manquait à la famille linéaire (`h45_detecteur_creux.py`)

Le §59 a une conséquence symétrique sur la **détection**, et elle se lit dans
le registre sans rien exécuter.

La famille quadratique de h24 a été testée **deux fois**, avec deux
statistiques qui ne visent pas la même chose : `h24.quad_diffus` (somme des
carrés des 252 800 cellules, optimale contre un biais **dense**) et
`h24.quad_max` (max |Z| sur les mêmes cellules, optimale contre un biais
**concentré**).

La famille linéaire, elle, n'a été testée **qu'une fois** : `c1.matrix_real`
(`‖Ĉ‖²_F`, p = 0,787) et `d2.t2_lagscan` (le même `T2` balayé sur 306 lags,
p = 0,784). Les deux sont des statistiques de **somme**. Leur note dit qu'elles
« couvrent toute matrice de couplage, dérangements compris » — vrai au sens de
la **consistance**, faux au sens de la **puissance**. Aucune statistique de
maximum n'existait pour la famille linéaire : une case vide du produit
(famille × forme du détecteur).

### Le croisement, en trois lignes

La somme détecte quand `s·(c/σ)² ≥ z√(2m)`, donc quand `c/σ ≥ √(z√(2m)/s)`. Le
maximum détecte quand une cellule dépasse le maximum du null, `≈ √(2 ln m)` —
**indépendant de `s`**. Les deux exigences se croisent en

> **`s* = z·√(2m) / (2 ln m) = 28`** cellules, pour `m = 6 400`, `z = 4,33`.

| s | la somme exige | le maximum exige | qui gagne |
|---|---|---|---|
| 1 | 22,13 σ | 4,19 σ | **maximum** |
| 5 | 9,90 | 4,19 | **maximum** |
| 10 | 7,00 | 4,19 | **maximum** |
| 20 | 4,95 | 4,19 | **maximum** |
| 28 | 4,18 | 4,19 | somme |
| 50 | 3,13 | 4,19 | somme |
| 6 400 | 0,28 | 4,19 | somme |

> **Et voici pourquoi le trou n'a jamais sauté aux yeux.** Les paires cachées
> de c1 ont `s = 50` : elles tombent du côté où le détecteur existant est le
> bon. La famille de contamination choisie pour mesurer la puissance était
> précisément dans le régime qui innocente la statistique employée.

Le trou porte donc sur les couplages **très** creux — une, deux, dix paires
(source → numéro) au lieu de cinquante. Rien dans le dossier ne les exclut, et
rien ne les avait cherchés avec le bon instrument.

### Les deux détecteurs manquants, exécutés

Deux tests pré-enregistrés, null par **permutation de l'ordre des tirages**
(300 réplicats) : les 70 560 tirages sont conservés tels quels, seul le
chaînage `t → t+1` est détruit. C'est le null exact de l'hypothèse visée, et
il est plus conservateur qu'un SRS puisqu'il préserve toute structure
intra-tirage.

| test | statistique | observé | null | p |
|---|---|---|---|---|
| `h45.matrix_max` | max \|C\|/sd(C) sur 6 400 cellules | 3,4545 | 3,9029 ± 0,2949 | **0,977** |
| `h45.matrix_hc` | Higher Criticism sur les mêmes | 1,4586 | 2,3611 ± 3,5953 | **0,781** |

Les deux sont **conformes**, et l'observé est en dessous du null dans les deux
cas. Le registre passe de m = 3 325 à **3 327** ; son plus petit `p` reste
2,0 × 10⁻⁴ pour un seuil de Holm de 1,5 × 10⁻⁵.

Deux notes de méthode. Les 6 400 cellules ne sont **pas** indépendantes —
chaque tirage porte exactement 20 numéros — donc les `p` gaussiens qui
alimentent HC sont mal calibrés cellule par cellule ; cela n'a aucune
conséquence, car HC n'est ici qu'un **nombre** dont la calibration vient
entièrement de la loi de permutation, qui subit les mêmes contraintes. Et le
null de HC est très dispersé (sd 3,60 pour une moyenne 2,36) : son `z` n'est
pas interprétable, seul le `p` empirique l'est.

### Une erreur de protocole, et sa réparation

Le galop d'essai de ce fichier **a consigné ses deux lignes au registre** — à
40 réplicats au lieu de 300. Le registre est append-only et partagé ; il n'est
pas réécrit à la main. La réparation est celle que le dossier a déjà employée
au §38 : `lab.dedupe()`, qui ne garde que la **dernière** consignation de
chaque `id` et a écrasé les deux lignes d'essai par les deux lignes à 300
réplicats. Le fichier porte désormais un garde-fou explicite — en mode essai,
il n'écrit rien et sort.

### Ce que cela ferme, et ce que cela n'atteint pas

**Fermé.** La famille linéaire est désormais couverte par une somme (c1, d2),
un maximum et un Higher Criticism — la même couverture que la famille
quadratique depuis h24.

**Ce que ce n'est pas.** Deux tests conformes n'établissent pas l'absence de
couplage : ils établissent qu'aucun couplage assez fort pour être vu **à cette
puissance** n'est présent. La puissance n'est pas mesurée ici, et c'est la
limite principale — le dossier exige d'ordinaire un témoin positif, et il
faudrait une contamination très creuse (`s` de 1 à 10) pour le fournir. Sans
lui, ces deux lignes valent comme **couverture de famille**, pas comme borne.

**Ce que cela ne change pas.** Le théorème d'invariance tient. Ce qui a bougé
est la **carte de ce qui a été cherché**, pas le résultat de la recherche.

## 61. L'axe manquant, balayé — et le §59 corrigé (`h46_axe_parcimonie.py`)

Les deux sections précédentes tirent en sens opposés sur la même quantité :

- **§59** — une déviation **creuse** est bien plus facile à identifier. *La
  parcimonie aide le joueur.*
- **§60** — la famille linéaire a gagné un maximum et un Higher Criticism, et
  la frontière d'Ingster–Donoho–Jin dit qu'ils mordent **exactement** dans le
  régime creux. *La parcimonie nuit à l'adversaire.*

Le net n'était pas calculé. Il l'est ici, et **il va contre la section qui l'a
motivé.**

### L'axe que le dossier ne balayait pas

Le §41 fait croître `m`. Le §42 fait croître `m`. Le §48 maximise sur `m`.
Aucun ne fait varier `s`, le nombre de cellules **actives** — il vaut toujours
implicitement `m`, puisque `h31.make_eps` tire une déviation isotrope. Or les
deux facteurs du produit du §48 dépendent de `s`, et en sens opposés.

`m = 6 400`, `N = 70 560`, plafond à 50 % de puissance, seuil `z = 4,33` d'un
null simulé pour chacun des trois détecteurs du registre :

| s | plafond χ² | plafond 3 dét. | détecteur liant | avantage oracle | part captée | **réalisable** |
|---|---|---|---|---|---|---|
| 2 | 0,1066 | 0,0305 | HC | 1,41 | 0,971 | 1,37 |
| 10 | 0,1120 | 0,0344 | HC | 3,64 | 0,831 | 3,02 |
| 40 | 0,0950 | 0,0516 | HC | 10,55 | 0,773 | 8,16 |
| **50** | 0,0972 | 0,0542 | HC | 12,13 | 0,754 | 9,15 |
| 80 | 0,0950 | 0,0617 | HC | 17,74 | 0,699 | 12,40 |
| 200 | 0,0818 | 0,0786 | HC | 35,35 | 0,636 | 22,47 |
| 800 | 0,0812 | 0,0800 | χ² | 71,97 | 0,370 | 26,61 |
| 2 400 | 0,0800 | 0,0800 | χ² | 113,78 | 0,242 | 27,57 |
| **6 400** | 0,0838 | 0,0829 | χ² | 109,24 | 0,274 | **29,90** |

> **Le résultat est négatif, et il faut le dire ainsi.** L'hypothèse qui a
> motivé ce fichier — que le maximum serait *intérieur*, la parcimonie ouvrant
> une porte que le §48 aurait manquée — est **fausse**. Le maximum est au
> bord, en `s = m`, exactement là où le §48 se tenait.

La raison se lit dans les deux colonnes du milieu. De `s = m` à `s = 2`, la
part captée monte de 0,27 à **0,97** — le §59 avait raison sur ce point — mais
l'avantage de l'oracle s'effondre de 109 à **1,4**, un facteur 78. Une
déviation creuse est bien plus facile à lire, **mais il y a bien moins à y
lire** : le seuil de détection borne l'amplitude **totale**, et la concentrer
sur peu de cellules n'en crée aucune.

Le §48 avait donc raison de se tenir où il se tenait. **Il ne le savait pas** :
il n'avait pas balayé cet axe, et rien dans son texte ne dit pourquoi `s = m`
serait le bon choix. La différence entre avoir raison et savoir pourquoi est
ce que cette section ajoute.

### Ce que les détecteurs du §60 coûtent à l'adversaire

| s | perte d'amplitude | détecteur liant |
|---|---|---|
| 2 | **71,4 %** | HC |
| 10 | 69,3 % | HC |
| 50 | **44,3 %** | HC |
| 200 | 4,0 % | HC |
| 800 et au-delà | ≈ 0 % | χ² |

Ils ne mordent que dans le régime creux — précisément ce que la frontière
d'Ingster–Donoho–Jin annonce, et précisément le seul régime que le χ² ne
couvrait pas. (Les valeurs autour de zéro, y compris un −0,0 %, sont le bruit
de bissection : les deux plafonds y coïncident.)

### Le net au point de fonctionnement réel — et le §59 est faux

Les paires cachées ont `s = 50` sur `m = 6 400`. C'est là que le §45 mesure
0,41 et le §41 un plafond de 3,21 %, d'où le 1,32 % du §48.

| lecture | plafond | captée | réalisable |
|---|---|---|---|
| §48, telle que publiée | 3,21 % | 0,41 | **1,32 %** |
| §59 seul (meilleur estimateur) | 3,21 % | 0,67 | 2,16 % |
| **§59 + §60 — le net** | **1,79 %** | 0,67 | **1,20 %** |

> **Le §59 annonçait « au moins +2,16 % » et concluait que le mur avait bougé
> de 69 %. C'était faux.** Il comparait un numérateur amélioré à un
> dénominateur périmé : le plafond de 3,21 % est calculé contre le χ² **seul**,
> et contre les trois détecteurs désormais au registre l'amplitude admissible à
> `s = 50` tombe de 44,3 %. Le même raisonnement qui rend une déviation creuse
> plus **lisible** la rend plus **détectable**.

**Le net vaut 1,20 % contre 1,32 % publié — soit −9 %. Le mur n'a pas bougé ;
il s'est très légèrement resserré.**

### Ce qui reste du §59, et ce qui tombe

**Reste.** Le gain d'estimateur mesuré en marche avant sur cinq archives
contaminées — ×1,64, apparié, positif sur les cinq. C'est une mesure, elle
tient, et elle vaut là où une matrice est **appliquée**. Le Théorème O tient
aussi : l'exposant de la loi d'identification change bien de signe avec la
parcimonie.

**Tombe.** La conclusion qu'on en tirait. Le plafond de la piste A ne passe pas
à +2,16 %. Le §59 a trouvé un vrai gain sur un facteur et l'a multiplié par un
autre facteur qui, entre-temps, avait cessé d'être valide — et c'est sa propre
section suivante qui l'avait invalidé.

### Ce que cela ne fait pas

**Le théorème d'invariance n'est pas touché, et il ne peut pas l'être.**
`E[hits] = Σ_{i∈G} P(i tiré) = k/4` dès que `P(i tiré) = 1/4` pour tout `i` :
c'est la linéarité de l'espérance, pas une conjecture. Tout ce fichier
travaille **sous l'hypothèse que cette uniformité est fausse** — la seule
manière d'attaquer l'énoncé, et ce que les 3 327 tests du registre font depuis
le début, sans succès à ce jour.

### Limites

1. `m` est fixé à 6 400. Le maximum **conjoint** sur `(m, s)` demanderait le
   même balayage à plusieurs `m` ; ce fichier établit que l'axe existe et
   qu'il ne recèle pas de maximum caché, pas la position du maximum conjoint.
2. La part captée est celle de la règle du §42 — classement **direct** des
   cellules, où seuiller ne change rien au classement. Le gain d'estimateur du
   §59 n'entre donc pas dans ce tableau : les deux résultats sont
   complémentaires, non cumulables tels quels.
3. Le joueur estime sur les mêmes données que le test (limite n° 3 du §42,
   héritée) : les chiffres sont **majorants**.
4. La frontière d'Ingster–Donoho–Jin est asymptotique. Elle sert ici à dire
   **où regarder**, jamais à fournir un nombre : tous les plafonds sont mesurés
   par bissection sur un null simulé.

**Registre : inchangé.** `h46` ne teste pas l'archive — il balaye un modèle.

## 62. Le prix du ticket, obtenu — et une erreur du §56

Le §56 avait déduit du barème que le taux de retour `E/c ≤ 1` force
**`c > CHF 1,1971`**, donc qu'un ticket à un franc est arithmétiquement exclu,
et avait pris `c = 2` comme « seule valeur ronde compatible donnant un retour
plausible ». Le §9 l'appelait depuis **la dernière inconnue de toute la chaîne
financière**.

### Ce que dit le règlement

Le règlement officiel de Loto Express (`loex-v13-1-fr.pdf`, Loterie Romande)
donne :

> **« L'enjeu unitaire LOTO EXPRESS est de CHF 2.- »**
>
> « L'enjeu unitaire EXTRA est de CHF 2.- et s'ajoute à l'enjeu unitaire LOTO
> EXPRESS en cas de participation à l'option EXTRA. »
>
> « L'enjeu unitaire BOOST est de CHF 2.- et s'ajoute à l'enjeu unitaire LOTO
> EXPRESS en cas de participation à l'option BOOST. »

**Sourçage, et il faut être précis.** Le PDF n'a pas pu être lu directement :
`jeux.loro.ch` est bloqué par le proxy de sortie de cet environnement, comme
il l'était déjà pour l'API (§11). Le chiffre provient de **deux recherches
indépendantes** dont les résultats citent ce document. C'est une source de
seconde main, plus solide qu'une déduction mais moins qu'une lecture directe :
la vérification à un coup d'œil sur l'application reste souhaitable.

### Ce que cela change

**La déduction du §56 était juste.** `c = 2` cesse d'être une hypothèse. Tout
ce qui en dépendait devient une mesure :

| quantité | statut au §56 | statut maintenant |
|---|---|---|
| taux de retour de base | 58,9 % *sous hypothèse* | **58,9 %, mesuré** |
| seuil exact, mise 6 | CHF 6 385 *sous hypothèse* | **CHF 6 385** |
| seuil statique (§57) | « seule hypothèse restante : `c` » | **plus aucune hypothèse** |
| marge de l'opérateur | 41 % *sous hypothèse* | **41 %** |

La sensibilité que le §57 déclarait en limite n° 1 — « à `c = 2,50` le seuil
passe à 10 261 » — devient sans objet. Le seuil statique de bascule à la mise 6
vaut **CHF 6 385**, sans conditionnel.

### Une erreur du §56, et elle est de méthode

Le §56 écrivait, en limite n° 3 :

> « Son espérance seule vaut 9,99 CHF à la mise 6, ce qui exclut qu'elle soit
> gratuite. »

**Ce calcul est invalide.** Il applique la loi hypergéométrique de la grille de
base à la colonne EXTRA. Passé sur les cinq mises, il donne :

| mise | E[extra] sous la loi de base | taux de retour implicite |
|---|---|---|
| 5 | 11,13 | 557 % |
| 6 | 9,99 | 500 % |
| 7 | 9,17 | 459 % |
| 8 | 8,24 | 412 % |
| 10 | 7,29 | 365 % |

Cinq taux de retour supérieurs à 100 % : aucun opérateur ne tient. **La colonne
EXTRA n'obéit donc pas à la loi de la grille de base** — l'option tire ses
propres numéros ou conditionne ses gains autrement, et lui appliquer la loi de
base est une faute, pas une approximation.

La conclusion du §56 (« elle n'est pas gratuite ») se trouve être **vraie** —
le règlement dit CHF 2 — mais elle l'était par accident. Un raisonnement faux
qui atteint la bonne réponse reste un raisonnement faux, et il aurait donné une
mauvaise réponse à la question suivante.

### Ce qui reste ouvert sur EXTRA

Son prix est connu (CHF 2, additionnels). Sa **loi** ne l'est pas : il faudrait
lire dans le règlement comment ses gains sont conditionnés avant de pouvoir
dire s'il est rentable de la prendre. Aucun chiffre du dossier n'en dépend
aujourd'hui.

**Sources :** [Règlement Loto Express — Loterie Romande](https://jeux.loro.ch/media/q5gbegrw/loex-v13-1-fr.pdf) · [Règlements des jeux | LoRo](https://jeux.loro.ch/reglements)

## 63. La graine que personne n'avait essayée : celle qu'on connaît (`h47_graine_connue.py`, `tools/sweep_time.c`)

Tous les balayages du dossier — `sweep48`, `sweep_java48`, `sweep_mt`,
`sweep_order`, `sweep_modern` — énumèrent un espace de graines **inconnues** :
2⁴⁸ états, **20,9 jours-cœur**, jamais mené à terme faute de GPU. Tous
supposent que la graine est un secret qu'il faut deviner.

Aucun n'a essayé le contraire, qui est le mode de défaillance le plus répandu
de tout le logiciel : **`srand(time(NULL))`**. Une graine dérivée de l'horloge
ou d'un compteur n'a pas à être devinée — elle est écrite dans l'archive :

- le numéro de tirage est **strictement consécutif**, 1 309 614 → 1 380 173 ;
- l'horodatage unix tombe sur une **grille exacte de 300 s** (70 548 / 70 560).

L'espace de recherche passe de 2⁴⁸ à **quarante-deux graines par tirage**. Ce
qui demandait trois semaines-cœur tient en deux minutes.

> Le §7 de l'audit notait déjà que l'horodatage ne porte aucun canal de rejet,
> *parce que* la grille est trop propre. Personne n'en avait tiré la
> conséquence inverse : une grille aussi propre rend la graine horaire
> parfaitement **prédictible**, donc parfaitement **testable**.

### La statistique, et pourquoi elle n'est pas binaire

On ne demande pas une reproduction exacte mais le **recouvrement** entre le
tirage engendré et le tirage réel. Une famille correcte avec une convention
légèrement fausse donnerait 16 ou 18 sur 20 ; l'exiger à 20 la manquerait.

Sous H₀ le recouvrement suit une **hypergéométrique(80, 20, 20) exacte** :
moyenne 5, écart-type 1,76. Le null de chaque essai est donc en forme close, et
la comparaison terme à terme de l'histogramme vaut calibration.

### Le témoin positif

Une archive de 400 tirages est fabriquée avec `java.util.Random(ts)` et un
Fisher-Yates partiel, par une réimplémentation **indépendante** de celle du C.

> **`max 20 — java.util.Random / fy_partiel / ts+0` — 400 sur 400 tirages.**

Le balayage retrouve le générateur planté sur *chaque* tirage et nomme
correctement la famille, l'échantillonneur et la convention. (Une première
version en trouvait 4 264 sur 400 : le remplissage de secours des
échantillonneurs à rejet répétait un numéro présent dans la cible, et le
recouvrement le comptait plusieurs fois. Corrigé en intersection
d'**ensembles** — c'est le témoin qui a révélé le défaut.)

### Le balayage

8 familles × 4 échantillonneurs × 6 conventions de graine × 7 décalages, sur
les 70 560 tirages : **91 869 120 essais.**

| | |
|---|---|
| familles | java.util.Random, glibc `random()`, MT19937, MSVC `rand()`, Numerical Recipes, minstd 16807, splitmix64, glibc LCG |
| échantillonneurs | Fisher-Yates partiel et complet, rejet modulo, rejet flottant |
| conventions | `ts+d`, `id+d`, `ts/300+d`, `(ts^id)+d`, `(ts+id)+d`, `ts*1000+d` |
| décalages | `d` de −3 à +3 |

| ov | observé | attendu | écart |
|---|---|---|---|
| 5 | 21 430 303 | 21 431 296 | −0,00 % |
| 10 | 361 255 | 361 974 | −0,20 % |
| 12 | 8 282 | 8 376 | −1,12 % |
| 13 | 800 | 778 | +2,83 % |
| 14 | 46 | 50,4 | −8,78 % |
| **15** | **4** | **2,26** | +82 % |

L'histogramme colle à la loi exacte à **moins de 0,3 %** dans tout le corps.
Maximum observé **15**, attendu 2,26 essais à ce niveau :

> **p = 1 − exp(−2,26) = 0,896.** Registre m = 3 328, seuil de Holm
> 1,55 × 10⁻⁵. **Conforme.**

Il aurait fallu `ov ≥ 17` pour `p = 10⁻³`, `ov ≥ 18` pour `p = 8,8 × 10⁻⁶`, et
un `ov = 20` — une reproduction exacte — vaudrait `p = 2,6 × 10⁻¹¹`.

### Ce que cela ferme, et ce que cela ne ferme pas

**Fermé.** La classe des implémentations qui ré-amorcent leur générateur sur
l'horloge ou sur un compteur — la plus courante en pratique, et celle
qu'aucun balayage du dossier n'atteignait — pour 8 familles, 4 échantillonneurs
et 6 conventions. Le témoin établit que le balayage voit ce genre de chose
quand il est là.

**Non fermé, et il faut être précis.**

1. La puissance vaut **1 dans** le produit balayé et **0 en dehors**. Une
   famille absente (AES-CTR, ChaCha, un matériel), un échantillonneur absent,
   une convention absente (millisecondes exactes, chaîne formatée, sel) ne sont
   pas testés.
2. Le décalage est borné à ±3 unités. Une graine prise à la seconde de
   *déclenchement* avec plus de trois secondes de dérive échapperait.
3. Un générateur qui **tourne en continu** n'est pas visé ici — c'est le
   domaine de h4 à h20 et de `sweep48`. Ce fichier ne couvre que le
   **ré-amorçage par quantité connue**.

**Ce que cela ne fait pas.** Le théorème d'invariance n'est pas touché. Un
générateur reproductible ne le ferait pas *tomber* : il rendrait le tirage
**prévisible**, ce qui est une autre chose — l'espérance resterait `k/4` pour
qui ne connaît pas la graine. C'était la seule voie ouverte vers une prédiction
réelle ; elle est ici fermée sur cette région, et l'archive n'y montre rien.

## 64. Le troisième ordre, et la prédiction qui a tenu (`h27_troisieme_ordre.py`)

La limite n° 5 du §40 était la dernière famille conditionnelle sans plafond :
« le troisième ordre — un triplet appelant un numéro — reste non borné ». Le
terme suivant du développement compte `80 × C(80,3) = 6 572 800` cellules,
**26 fois** l'espace du quadratique.

### La double projection se réduit à une seule, et c'est un théorème

Retirer la part linéaire puis la quadratique semble demander une régression
sur `80 + 3 160` colonnes. Mais chaque tirage contient exactement 20 numéros,
donc `Σ_{b≠a} x_a·x_b = 19·x_a` **identiquement**. Les 80 indicatrices sont
donc **dans** l'espace des 3 160 produits de paires : projeter sur les paires
seules retire les deux parts d'un coup, exactement (résidu mesuré
1,4 × 10⁻¹³), pour un huitième du coût.

### Le polynôme orthogonal de degré 3

La contamination témoin module le logit par `v(m)`, `m = |D_t ∩ S|`. En
résolvant `E[v] = E[v·m] = E[v·m²] = 0` en rationnels sous le poids
hypergéométrique :

    v = (−57/1711, +57/590, −3/10, +1),   Var(v) = 83 391 / 2 703 380

C'est le polynôme orthogonal de degré 3 de ce poids, et l'orthogonalité se
propage par les identités de somme : `Cov(v, x_a) = 0` pour les 80 numéros et
`Cov(v, w_ab) = 0` pour les 3 160 paires, **exactement**, les six cas vérifiés
en arithmétique de fractions. Mesuré **dans les deux sens** : sous les
contaminations cubiques (avantage jusqu'à +9,45 %, détecté à 100 %), les
statistiques de c1, d3 et h24 restent dans [−0,65 ; +1,47] ; réciproquement la
contamination quadratique de h24 allume Q1/Q2 à +4,4/+7,7 pendant que U1/U2/U3
ne voient rien. **Les familles sont disjointes, pas « peu couplées ».**

### Sur l'archive réelle : rien — la quarantième voie

| | observé | null simulé (40 SRS) | z | p |
|---|---|---|---|---|
| U1 `Σ Z²` (6 572 800) | 6 575 424,17 | 6 572 444,80 ± 3 327,98 | +0,90 | 0,390 |
| U2 `max \|Z\|` | 5,6178 | 5,29451 ± 0,17505 | +1,85 | 0,073 |
| U3 `Σ Z²` (n ∈ {i,j,k}) | 245 765,64 | 246 493,48 ± 642,63 | −1,13 | 0,244 |

La cellule la plus déviante — le numéro 47 appelé par le triplet (12, 26, 63) —
sort à |Z| = 5,618 contre une loi du max à 5,29 ± 0,18. Les queues suivent :
421 cellules au-delà de 4 σ pour 416 attendues.

### Le plafond, et la prédiction confrontée

Enveloppe : famille « tiers », m = 80, R = 8 triplets sources, θ = 0,120.
Avantage **+0,2453 ± 0,0019** hits sur 2,50, soit **+9,81 %**, puissance de
détection mesurée 12 %.

| famille | test qui la borne | plafond |
|---|---|---|
| marginal | χ² sur 80 (`c0`) | +1,33 % |
| linéaire lag-1 | ‖Ĉ‖²_F sur 6 400 (`c1`) | +3,21 % |
| lags 1..306 | le même, balayé (`d2`) | +3,46 % |
| quadratique | Q1/Q2/Q3 sur 252 800 (`h24`) | +6,27 % |
| **cubique** | **U1/U2/U3 sur 6 572 800 (`h27`)** | **+9,81 %** |

> **Le §41 avait publié, avant cette mesure et par une voie qui n'a rien de
> commun avec elle, une prédiction falsifiable : entre +8,9 % et +14,2 %.
> Mesuré : +9,81 %. La loi tient.**

Le rapport des plafonds 2→3 vaut 1,57 là où la loi à ‖a‖ constant donnerait
2,26 : ‖a‖ décroît d'un facteur 0,69 de l'ordre 2 à l'ordre 3, prolongeant la
décroissance monotone mesurée au §41.

### Ce que ce plafond n'est pas

C'est une borne d'**omniscience stricte** : elle suppose les 6 572 800
coefficients connus du joueur. La hiérarchie monte en degré — +3,21, +6,27,
+9,81 — mais elle monte **vers rien** : même omniscient, l'adversaire cubique
reste sous la marge de l'opérateur (41 %, §62), et l'adversaire réel doit
estimer sa règle sur les mêmes 70 560 tirages qui la cachent. C'est le §61 qui
donne l'état actuel de cette pénalité : elle n'est pas le simple m^(−1/4) du
§42, mais le produit reste maximal au bord dense et le net n'a pas bougé.

### Limites déclarées, et les erreurs corrigées en route

Lag 1 seulement. Le seuil de U2 extrapole la queue par un Gumbel ajusté aux
moments (une gaussienne aurait dit 4,33 au lieu de 8,21 et **surestimé** la
puissance). Null à 40 réplicats au lieu de 400 : ±11 % sur les écarts-types,
plancher du p empirique à 0,024. Balayage borné à R ≤ 8 : le plafond est
légèrement **conservateur**.

Cinq erreurs corrigées par la mesure et déclarées : la double projection
planifiée en régression jointe avant que le théorème ne la divise par huit ;
un comptage « optimisé » plus lent que le naïf ; la doctrine mono-thread de
h24 qui s'inverse sur d'autres formes de matrices (×3,7) ; un chrono isolé
qui mentait de 50 % sur le régime soutenu ; et des grilles d'amplitude
initiales plaçant la frontière à θ ≈ 0,4 quand le pilote l'a mesurée à 0,19 —
parce que c'est **U2** qui mord en premier, pas U1.

**Registre : 4 entrées, m = 3 331, seuil de Holm 1,501 × 10⁻⁵, 0 significatif.**
Le plus petit `p` du dossier reste 2,0 × 10⁻⁴ (`audit.paires`). Run officiel :
8 120 s.

## 65. Le troisième régime d'implémentation, et ce que le cas Tipton coûte ici (`h48_chaine_et_declencheur.py`)

Le dossier couvre **deux** architectures de générateur, et deux seulement :

| | régime | où il est traité |
|---|---|---|
| **A** | tourne en continu depuis toujours, graine inconnue | h4–h20 (algébrique), §34 : 12 familles sur [0, 2³²) **et les 2⁴⁸ complets** de `java.util.Random` |
| **B** | ré-amorcé **à chaque tirage** sur une quantité connue | §63, fermé |
| **C** | ré-amorcé **une fois**, puis court en continu | *personne* |

Le régime C est le plus naturel pour un système qui démarre le matin, et il
**échappe aux deux autres par construction** : le balayage aveugle (A) ne sait
pas où commencer, et le §63 (B) ré-amorce à chaque tirage — si le système ne se
ré-amorce qu'une fois par jour, le deuxième tirage de la journée ne sort pas
d'une graine horaire, et B ne teste rien.

### L'archive donne les points d'amorçage en clair

**345 sessions de 204 tirages exactement**, plus une de 180. Chaque session
commence à **04:05:00 UTC pile**, après une coupure de 25 500 s. Les points
d'amorçage sont donc connus à la seconde, et il y en a 346.

### La statistique, et les deux contrôles

Après **un seul** amorçage, on engendre `L = 3` tirages consécutifs en laissant
l'état **continuer**, et on somme les recouvrements. Sous H₀ la somme est la
convolution triple d'une hypergéométrique(80, 20, 20), calculée exactement en
rationnels : moyenne 15, et une reproduction exacte vaudrait 60.

> **Non-régression.** À `L = 1` l'outil doit refaire le §63 au chiffre près :
> 91 869 120 essais, max 15. **Obtenu.**
>
> **Témoin positif.** Une archive où chaque session sort d'un seul
> `java.util.Random` amorcé sur l'horodatage d'ouverture, l'état continuant
> d'un tirage au suivant, est retrouvée à **60/60**. *(Une version
> intermédiaire échouait : j'avais simplifié `nextInt` en perdant la branche
> « puissance de deux », et le Fisher-Yates passe par `n = 64` à la
> dix-septième itération. C'est le témoin qui l'a dit.)*

### Le résultat

| balayage | essais | max sur 60 | attendu à ce niveau | **p** |
|---|---|---|---|---|
| amorçage à n'importe quel tirage, `d = ±3` | 91 866 516 | 32 | 2,70 | **0,933** |
| amorçage aux 346 ouvertures, `d = ±600 s` | 77 291 556 | 33 | 0,35 | **0,298** |

L'histogramme colle à la convolution exacte sur toute son étendue. Il aurait
fallu une somme ≥ 38 pour `p = 7,5 × 10⁻⁶`. Registre **m = 3 333**, 0
significatif.

### Ce que le cas Tipton coûte à un initié, ici

Le seul générateur de loterie réellement cassé — Eddie Tipton, Multi-State
Lottery Association — **n'a pas été détecté par des statistiques** mais par une
caméra de station-service. Son rootkit ne s'activait que trois jours par an,
deux jours de semaine, après 20 h, et restreignait alors la sortie à un petit
ensemble de combinaisons. Un tel biais ne laisse **aucune** trace marginale.

Sa seule signature est la **collision**, et le registre porte déjà le test :
`audit.antirejeu`, recouvrement maximal 16/20 sur 2,489 milliards de paires —
donc aucune collision 20/20. Si `k` tirages sont déclenchés et tirent dans un
ensemble de `M` combinaisons, `P(aucune collision) ≈ exp(−k²/2M)` : n'en avoir
observé aucune exclut à 95 % tout `M < k²/(2 ln 20)`.

| scénario | k tirages | M minimal pour échapper |
|---|---|---|
| 1 heure par an | 12 | 24 |
| 1 jour par an | 193 | 6 217 |
| **3 jours par an (le cas Tipton)** | **579** | **55 953** |
| 1 jour par mois | 2 321 | 899 119 |

> **C'est un renversement.** Dans cette archive, « trois jours par an » ne vaut
> pas trois tirages mais **579**, parce que le jeu tire toutes les cinq minutes
> et non deux fois par semaine. L'ensemble de quelques centaines de
> combinaisons du cas Tipton aurait produit des collisions par milliers :
> `M = 1 000` donne `P(aucune) = 1,6 × 10⁻⁷³`, `M = 10 000` donne
> `5,3 × 10⁻⁸`.
>
> **La cadence, qui rend ce jeu attirant pour qui veut prédire, est
> précisément ce qui rend une attaque à la Tipton auto-destructrice.**

### Ce que cela ferme, et ce que cela ne ferme pas

Les trois régimes d'implémentation sont désormais couverts, et le seul cas
réel documenté d'insider est exclu par un test que le dossier avait déjà passé
— on ne le savait simplement pas.

**Non fermé.** La puissance vaut **1 dans** le produit balayé et **0 en
dehors** : une famille absente (AES-CTR, ChaCha, un matériel), un
échantillonneur absent, une convention de graine absente, ou une dérive de plus
de 600 s sur l'heure de démarrage échapperaient.

> **Erratum.** Une première rédaction affirmait ici que « le régime A reste
> ouvert par défaut de calcul : 2⁴⁸ n'a jamais été parcouru ». C'est **faux**,
> et la confusion portait sur deux outils différents. Le brute-force naïf de
> `sweep48.c` (20,9 jours-cœur) n'a effectivement jamais tourné — mais
> `sweep_java48.c` couvre le **même** espace par une attaque 2-adique qui
> ramène 2,8 × 10¹⁴ pas à 4 × 10⁹, et le §34 l'a exécutée : **0 touche sur les
> 2⁴⁸ états complets.** Ce qui reste hors de portée est un espace de graines
> de 2⁶⁴ ou plus **sans structure exploitable** — et là, aucune machine ne
> remplace un théorème.

**Sources :** [Hot Lotto fraud scandal](https://en.wikipedia.org/wiki/Hot_Lotto_fraud_scandal) · [The Register — lottery-hacking sysadmin](https://www.theregister.com/2017/08/23/florida_judge_gives_lottery_scammer_more_private_time/)

## 66. La classe jamais essayée : le modèle de séquence à représentation apprise (`h39_sequence.py`)

Les trois familles de modèles appris du dossier partagent une servitude que
personne n'avait nommée : **leur représentation est choisie, jamais apprise.**
La régression logistique du §3 ter et le gradient boosting de `d3` voient le
tirage à travers quatorze puis six traits agrégés ; le codeur universel du §52
mélange des contextes markoviens fixés d'avance, et ses angles morts sont
déclarés — pas d'interaction entre numéros, pas de lag au-delà de 12, pas de
contexte exogène en temps.

Un modèle de séquence à représentation apprise appartient à une **classe de
fonctions différente** : il peut apprendre un couplage entre le numéro `a` au
tirage `t−k` et le numéro `b` au tirage `t`, pour tout `k ≤ 127`, sans qu'on le
lui nomme. C'est l'angle mort que le §52 laisse ouvert, et personne ne l'avait
essayé.

### L'architecture, et pourquoi cette taille

Ni torch ni tensorflow ici — et c'est préférable : le réseau est en numpy,
rétropropagation comprise, **gradient vérifié par différences finies** (75
coordonnées, pire écart relatif 7,5 × 10⁻⁶) avant tout usage. TCN causal
dilaté : mélangeur 80 → 24 canaux, dilatations 1 à 64, champ réceptif **128**
(au-delà du plafond lag-12 de h35), résidus ; plus un bloc **depthwise** par
numéro (lags 1..12) et un noyau partagé sur les 80. **13 892 paramètres**, soit
406 événements binaires par paramètre — l'ordre du budget par feuille de h35.
Le §3 ter avait mesuré que 18 000 tirages n'apprennent pas *un* poids sur *un*
trait informatif : un modèle à 10⁶ paramètres n'apprendrait ici que du bruit.

### Sur les vraies données : rien, dans les deux unités

| | valeur |
|---|---|
| recouvrement moyen du top-20 (50 560 tirages, marche avant stricte) | **4,9979** (espérance exacte 5,0000) |
| z | **−0,28** |
| E final du mélange tempéré | 10⁻⁰·⁷⁷³ — *collé au plancher déclaré* 10⁻⁰·⁷⁷⁸ |
| taux de Kelly du mélange | **−5,08 × 10⁻⁵ bit/tirage** |
| sup mélange ; sup redémarrages | 10⁺⁰·⁹¹⁶ ; 10⁺⁰·⁸³⁷ (Ville : 10⁺¹·³⁰¹) |

`leak_check` propre (futur réécrit depuis chaque sonde, cumuls compris),
accord voie vectorisée / voie causale exact à 0,0.

> **Le recoupement qui ferme la lecture.** Le modèle brut paie −2,83 × 10⁻²
> bit/tirage sur le réel, contre **−2,79 × 10⁻²** sous H₀ (deux archives SRS,
> pipeline identique). **L'archive ne lui coûte rien de plus que du bruit.**

Et les bits **apparents** in-sample valent **+0,0393/tirage** : l'écart
train/éval *est* le sur-apprentissage, mesuré plutôt qu'invoqué.

### Le prix de la richesse, mesuré pour la première fois

| classe | Kelly sous H₀ (bit/tirage) |
|---|---|
| f4 — 174 paris nommés, figés (§12.2) | −3,33 × 10⁻³ |
| h35 — codeur universel, 5 133 paramètres (§52) | −6,2 × 10⁻⁵ |
| **h39 brut — monolithe appris, 13 892 paramètres** | **−2,79 × 10⁻²** |
| **h39 couvert — famille tempérée + membre cash** | **−5,0 × 10⁻⁵** |

Le monolithe brut paie **450 fois** le prix de l'universel, et même **8 fois**
celui des paris figés : une architecture riche est un **handicap mesurable**,
pas un outil, quand on la lit brute. Couverte par sa propre famille tempérée —
six lignes, déclarées d'avance — elle cesse de payer aussi vite que le codeur
universel. **Le sur-apprentissage n'est pas une fatalité de l'architecture,
c'est une fatalité de la lecture brute.**

### Où la classe compte — et c'est sur exactement une famille

| famille | c2 (§3 ter) | f3 (§12.1) | h35 (§52) | **h39** |
|---|---|---|---|---|
| marginale | aveugle sous Δp = 0,020 | — | Δp = +0,019 | **+0,019 — pareil** |
| rémanence lag-1 | mord à d = 0,003 | +0,043 hit | ≈ +0,044 hit | **+0,19 hit — 4× plus tard** |
| paires croisées lag 24 | hors traits | hors têtes | **hors classe**, vérifié ici | en classe, **non trouvé** (0/2) |
| transitoire tardif | hors classe | — | mord | **jamais** (0/2 à Δp = +0,18) |
| **période 2** | hors traits | — | **jamais** (0/2 à δ = 0,30) | **mord à δ = 0,30 (2/2)** |

> La classe de fonctions comptait donc, sur **une** famille : la modulation
> périodique pure en temps — l'angle mort **déclaré et mesuré** de h35. Aucun
> contexte exogène n'est nécessaire : la parité se lit dans le motif alterné
> des indicatrices, et le champ réceptif la décode. La détection *passive* de
> cette famille était couverte (c3, f5-B) ; **aucun prédicteur du dossier ne
> l'exploitait.**

Que h35 soit aveugle aux paires croisées est **vérifié** — son codeur relancé
sur la même contamination, aveugle 2/2 — et non affirmé.

### La leçon structurelle : le plancher de bruit du monolithe

Pourquoi quatre fois plus tard sur la rémanence ? Le mécanisme est **isolé**,
pas supposé. À ε = 0,05 le signal vaut 0,013 logit par numéro ; le noyau
partagé l'**apprend** (mise en commun des 80, SE ≈ 0,005) — et cela ne suffit
pas, parce que le classement porte les 80 logits **entiers**, bruit
d'estimation des 13 892 paramètres compris (≈ 0,1 logit). Tempérer n'y change
rien : `η` multiplie signal et bruit dans le même rapport. f3 et f4
**postulent** le poids (aucune estimation), h35 mélange des experts minuscules
dont chacun ne paie que sa propre redondance — le monolithe paie son plancher
de bruit sur **chaque** pari.

> C'est le §3 ter généralisé : « enrichir dégrade » n'était pas une anecdote de
> régression logistique, **c'est la structure de tout modèle monolithique
> appris** — et c'est pourquoi un mélange de contextes markoviens bat une
> architecture moderne sur cette source, sauf là où la représentation doit être
> **découverte**.

### Les erreurs, dont une que `leak_check` ne pouvait pas voir

Cinq itérations, toutes sur synthétique, toutes racontées dans le fichier. Une
mérite d'être ici : le bloc depthwise démarrait à `x[t−1]` alors que `S[t]`
prédit le tirage `t+1` — un décalage d'un cran **vers le passé**. Fuite il n'y
a pas, et `leak_check` **ne peut pas** l'attraper : un contrôle de fuite
protège du futur, pas d'un modèle qui regarde trop loin en arrière. Seul le
**témoin positif** l'a vu, en restant à `z ≈ 0` là où la détection était
certaine.

> Sans témoins, ce modèle aurait produit un « rien trouvé » parfaitement propre
> et parfaitement cassé — la leçon de c2, rejouée à l'identique dans une classe
> neuve.

### Limites nommées

Un couplage de paires **intra-tirage** à marginales neutres est invisible des
deux unités **par théorème** : `E[recouvrement] = Σ P(i ∈ D) = 5` et `E[log e_t]`
ne dépendent que des marginales — le réseau peut représenter l'interaction dans
ses couches, la loi de sortie produit-forme ne peut pas la facturer (le §40
reste la voie de détection de cette famille). Pas de canal bonus, pas de
covariable exogène, pas de lag au-delà de 127, pas d'adaptation entre points de
contrôle — d'où les transitoires manqués. Et les paires croisées au lag 24,
**en classe mais non apprises** à 250 comme à 600 époques : *la classe de
fonctions n'est pas la classe de ce que l'optimisation atteint*, et l'écart
entre les deux est ici mesuré.

**Registre : 3 entrées** (`h39.wf` z = −0,28 ; `h39.bits` et `h39.sup`, piste C,
p de Ville 1,0 et 0,145), **m = 3 335, zéro significatif.**

## 67. Les deux courbes, et l'ordre où elles se croisent (`h49_les_murs.py`)

Le dossier a mesuré **quatre** plafonds d'omniscience, un par ordre de
couplage. Ils **montent** avec l'ordre, et le §41 en donne la loi. La marge de
l'opérateur, elle, ne bouge pas : **41,1 %** (§62, prix du ticket confirmé).

Deux courbes, l'une qui monte et l'autre qui est plate : **elles se croisent.**
Personne n'avait calculé où — et c'est la seule façon de répondre à « quel mur
faut-il franchir », parce que la réponse n'est ni « le plafond est trop bas »
ni « la marge est trop haute ».

### Ce que les quatre points mesurés coûtent déjà

L'archive contient 70 560 tirages × 80 indicatrices = **5 644 800 événements
binaires**. C'est tout le budget d'information disponible, et il ne dépend pas
de l'ordre auquel on regarde.

| ordre | m cellules | plafond | **événements/cellule** | famille |
|---|---|---|---|---|
| 0 | 80 | 1,33 % | 70 560 | marginal (c0) |
| 1 | 6 400 | 3,21 % | 882 | linéaire lag-1 (c1) |
| 2 | 252 800 | 6,27 % | 22,3 | quadratique (§40) |
| 3 | 6 572 800 | 9,81 % | **0,86** | cubique (§64) |

> La dernière colonne est celle qu'on ne regarde jamais, et c'est elle qui
> décide. **Dès l'ordre 3, il y a moins d'un événement par cellule.**

### La loi, ajustée sur les quatre points

    plafond = 0,641 × m^0,178        (écart ≤ 7 % sur les quatre)

Le §41 prédit l'exposant ¼ à `‖a‖` constant ; l'écart jusqu'à 0,178 est
exactement la décroissance de `‖a‖` que le §41 mesurait et que le §64 a
prolongée.

### Le croisement

| ordre | m cellules | plafond | événements/cellule |
|---|---|---|---|
| 3 | 6 572 800 | 10,5 % | 0,86 |
| 4 | 126 526 400 | 17,8 % | 0,045 |
| 5 | 1 923 201 280 | 28,8 % | 0,0029 |
| **6** | **24 040 016 000** | **45,2 %** | **0,00023** |

> **Le croisement est à l'ordre 6.** Au moment *précis* où un adversaire
> omniscient rattraperait enfin la maison, il lui faudrait estimer **24
> milliards** de coefficients à partir de **5,6 millions** d'événements — soit
> **un événement pour 4 259 coefficients**.

Ce n'est pas difficile, c'est **sous-déterminé** : le système a 4 259 fois plus
d'inconnues que d'équations, et aucune méthode d'estimation ne fabrique de
l'information qui n'est pas là.

### Les deux façons de franchir, et ce qu'elles coûtent

**A — monter en ordre.** Il faudrait au minimum *une* observation par
coefficient : `24 040 016 000 / 80 = 300 500 200` tirages, soit **2 857 ans**
d'archive à 288 tirages/jour. Et une observation par coefficient n'apprend
rien — il en faudrait des dizaines. Multipliez par vingt.

**B — faire tomber la marge** jusqu'au plus haut plafond mesuré : il faudrait
un taux de retour de **90,2 %** au lieu des 58,9 % mesurés. Aucune loterie ne
rend 90 %.

**C.** Il n'y a pas de C.

### Ce que ce calcul établit

> Le mur de la piste A n'est pas « le plafond est trop bas » ni « la marge est
> trop haute ». C'est que les deux courbes se croisent **du mauvais côté de
> l'apprentissage** : là où le plafond devient suffisant, le nombre de
> paramètres dépasse le nombre d'observations d'un facteur 4 259.
>
> **Le plafond et l'apprenabilité ne sont pas deux obstacles indépendants —
> c'est un seul obstacle, vu deux fois.**

### Limites, et elles sont sérieuses

1. C'est une **extrapolation** de trois ordres au-delà du dernier point
   mesuré. La loi tient sur quatre points et le §64 a confirmé une prédiction
   faite d'avance, mais rien ne garantit qu'elle tienne jusqu'à l'ordre 6.
2. Les plafonds sont d'**omniscience stricte**. Le joueur réel en capte une
   fraction (§45, §59, §61) : le croisement réel serait donc encore **plus
   loin**, jamais plus proche. Le calcul est conservateur dans le bon sens.
3. La marge de 41,1 % repose sur le barème relevé (§56) et le prix de CHF 2
   (§62) — observés, mais la seconde source est de seconde main.
4. Le comptage « événements par coefficient » traite les 80 indicatrices d'un
   tirage comme indépendantes ; elles ne le sont pas (leur somme vaut 20
   exactement). Le budget réel est donc **plus petit**, ce qui ne fait
   qu'aggraver la conclusion.

**Registre : inchangé.** `h49` ne teste pas l'archive — il ajuste et extrapole.

## 68. Le théorème de la fuite modulaire (`h50_fuite_modulaire.py`)

Le §67 a nommé ce qui restait ouvert côté générateur : *« les espaces de
graines de 2⁶⁴ ou plus **sans structure exploitable** — là, aucune machine ne
remplace un théorème. »* Le §34 avait montré la voie sur `java.util.Random` :
une attaque 2-adique y a gagné un facteur **70 000** là où un A100 en aurait
gagné 1 282.

Cette section fait le même geste sur une autre classe. Elle n'a besoin
d'**aucune recherche de graine**.

### Le théorème

> **80 = 16 × 5.**
>
> Donc `n = (out mod 80) + 1` entraîne **`out ≡ n − 1 (mod 16)`**.
>
> Les **quatre bits de poids faible** du mot de sortie du générateur sont
> publiés en clair par chaque numéro tiré. Ce n'est pas une approximation :
> c'est une égalité.

**Corollaire (le cas F₂-linéaire).** Si le générateur est linéaire sur F₂ —
xorshift, LFSR, Tausworthe, et le tempérage de MT19937 — chaque bit de sortie
est une **forme linéaire** des bits d'état. Chaque numéro tiré fournit donc
**quatre équations linéaires sur F₂**, et un tirage ordonné de 20 numéros en
fournit **quatre-vingts**.

| état | équations disponibles | tirages nécessaires |
|---|---|---|
| 32 bits | 80 | **1** |
| 64 bits | 80 | **1** |
| 96 bits | 160 | 2 |
| 128 bits | 160 | 2 |

> L'état se retrouve par **élimination de Gauss**, en microsecondes, **quelle
> que soit la graine**. Que l'espace fasse 2⁶⁴ ou 2¹²⁸ ne change rien : on ne
> cherche plus la graine, on **résout** l'état.

### L'attaque, et le point délicat

L'échantillonnage par rejet consomme plus de 20 mots par tirage — espérance
**2,849 rejets**, loi exacte obtenue par convolution de 20 géométriques de
raison `i/80`. On ignore *où* sont les rejets.

Trois choses rendent la descente praticable là où l'énumération ne l'était
pas :

1. **Le pivot est partagé** le long du chemin : accepter un numéro coûte
   quatre réductions et non quatre-vingts. (Une première version recalculait
   les coefficients à chaque motif — dix mille fois le prix.)
2. **Un motif faux rend le système incohérent**, en général très tôt, et
   élague alors tout son sous-arbre.
3. **Dès que le rang est plein, on résout et on remonte** : la solution est
   unique et lui ajouter des équations ne peut plus la changer. Cela borne
   l'arbre à la profondeur où le rang se remplit.

Une contrainte gratuite s'ajoute : le **premier mot de chaque tirage est
toujours accepté**, aucun numéro n'y ayant encore été vu.

Et le plafond de rejets est compté **par tirage** et non globalement — un
budget global autorise à mettre tous les rejets dans le premier tirage, et
l'arbre passe de 177 000 à 141 millions de feuilles sans qu'aucun élagage ne
morde, puisque le système reste sous-déterminé tant que le rang n'est pas
atteint.

### Le témoin : cinq familles sur cinq

Chaque famille est amorcée sur un état **tiré au hasard dans tout son
espace**, et l'attaque doit le retrouver sans jamais énumérer de graine.

| famille | bits | tirages | retrouvé | temps |
|---|---|---|---|---|
| xorshift32 | 32 | 1 | **oui** | 0,00 s |
| xorshift64 | 64 | 1 | **oui** | 0,00 s |
| xorshift96 | 96 | 2 | **oui** | 3,9 s |
| **xorshift128** | **128** | 2 | **oui** | **12,5 s** |
| taus88 (L'Écuyer) | 96 | 2 | **oui** | 0,03 s |

> Un état de **128 bits**, tiré uniformément dans 2¹²⁸, retrouvé en **douze
> secondes** depuis deux tirages. Aucun balayage n'approchera jamais cet
> espace ; l'algèbre le traverse sans le voir.

### Sur les cinq tirages ordonnés de l'archive

Le dossier possède cinq tirages ordonnés (§20–22), dont **une seule paire
consécutive** (1381030, 1381031).

| famille | bits | chaînes | couverture | états compatibles |
|---|---|---|---|---|
| xorshift32 | 32 | 5 | 99,3 % | **0** |
| xorshift64 | 64 | 5 | 99,3 % | **0** |
| xorshift96 | 96 | 1 | 83,3 % | **0** |
| xorshift128 | 128 | 1 | 46,1 % | **0** |
| taus88 | 96 | 1 | 92,2 % | **0** |

La colonne **couverture** est la fraction des tirages dont le motif de rejet
tient sous le plafond atteint : c'est la **puissance** de l'attaque, déclarée
plutôt que supposée totale.

La vérification est **exacte et sans marge** — un état retenu doit reproduire
les 20 numéros *dans l'ordre*, ce qui élimine tout faux positif (probabilité
1/C(80,20) = 2,8 × 10⁻¹⁹ par état).

### Ce que cela ferme, et ce que cela ne ferme pas

**Fermé.** Les familles F₂-linéaires d'état ≤ 128 bits, **pour toute graine**.
C'est précisément la région que le §67 déclarait hors de portée. Le §34 avait
gagné un facteur 70 000 par une réduction algébrique ; celle-ci gagne un
facteur **illimité**, puisqu'elle ne dépend plus de la taille de l'espace.

**Non fermé, et les limites sont structurelles.**

1. **Il faut l'ordre de sortie.** L'archive triée est inutilisable ici : cinq
   tirages ordonnés sont tout ce dont on dispose, et c'est cette contrainte
   qui borne le résultat, pas l'algèbre. **C'est le levier le moins cher du
   dossier** — chaque tirage ordonné collecté vaut une famille testée.
2. **Les générateurs non linéaires sur F₂ échappent au théorème** : PCG
   (permutation de sortie), xoshiro `**` et `++` (multiplication, rotation),
   splitmix64, tout CSPRNG. La linéarité est l'hypothèse, et elle est forte.
3. **Les sorties additives** (xorshift128+, xoroshiro128+) ne sont linéaires
   que sur le **bit 0** : 20 équations par tirage au lieu de 80, donc sept
   tirages ordonnés consécutifs, que le dossier n'a pas.
4. **MT19937 est linéaire mais fait 19 937 bits** : il faudrait 250 tirages
   ordonnés consécutifs. C'est la seule famille linéaire courante qui
   résiste, et **elle résiste par la taille, pas par la structure.**

**Registre :** `h50.fuite_modulaire`, 0 état compatible, m = 3 335, zéro
significatif.

## 69. Le budget de fuite, et le calendrier qu'il impose (`h51_budget_de_fuite.py`)

> **CORRECTION (§80).** Le palier MT19937 de cette section — 250 tirages — est
> **faux de 37 %**. Il suppose les 80 équations d'un tirage indépendantes ;
> elles cessent de l'être au mot 2 493, exactement quatre blocs de 624. Le rang
> plein demande **6 853 mots, soit 343 tirages**, mesuré par élimination exacte
> au §80. Les autres paliers ne sont pas touchés : leurs états sont assez petits
> pour être résolus avant le quatrième bloc.

Les limites du §68 sont toutes de la même forme : *il faudrait plus de tirages
ordonnés consécutifs.* Ce n'est pas une limite théorique, c'est une
**commande**. Cette section la chiffre — et découvre en chemin que
l'échantillonneur décide de tout.

### Le budget dépend de l'implémentation, pas du jeu

Un modulo par `n` publie exactement `v₂(n)` bits de poids faible du mot. Le
§68 traitait `n = 80` ; écrit pour un `n` quelconque, le théorème donne des
budgets très différents selon l'échantillonneur.

**Rejet modulo 80** — tous les numéros passent par le même modulo :
`v₂(80) = 4`, donc **4 × 20 = 80 bits par tirage.**

**Fisher-Yates** — le pas `i` tire modulo `80 − i` :

| 80 | 79 | 78 | 77 | 76 | 75 | 74 | 73 | 72 | 71 |
|---|---|---|---|---|---|---|---|---|---|
| **4** | 0 | 1 | 0 | 2 | 0 | 1 | 0 | 3 | 0 |

| 70 | 69 | 68 | 67 | 66 | 65 | **64** | 63 | 62 | 61 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 2 | 0 | 1 | 0 | **6** | 0 | 1 | 0 |

Somme : **22 bits par tirage.**

> **Le rejet modulo 80 fuit 3,6 fois plus qu'un Fisher-Yates**, sur exactement
> le même jeu et les mêmes vingt numéros. La différence tient entièrement à ce
> que 80 = 16 × 5 est divisible par 16, alors que 79, 77, 75, 73, 71, 69, 67,
> 65, 63 et 61 sont impairs et **ne publient rien du tout**.

Et un seul pas rapporte plus que tous les autres réunis moins un : le
**dix-septième**, qui tire modulo 64 = 2⁶ et publie **six bits d'un coup**.
C'est exactement la borne dont le §34 signalait qu'elle est traitée à part par
`nextInt` — *là où java.util.Random change de chemin, la fuite est maximale.*

Le **multiply-shift** `(out × n) >> 32`, lui, ne fuit **aucun** bit linéaire :
il donne un encadrement, pas une congruence. C'est un problème de **réseau**,
hors du cadre de ce théorème.

### Ce qu'il manque, famille par famille

| famille | état | bits/tirage | **tirages ordonnés consécutifs requis** |
|---|---|---|---|
| xorshift32, xorshift64 | 32–64 | 80 | **1** |
| xorshift96, xorshift128, taus88 | 96–128 | 80 | **2** ← *le §68 s'arrête ici* |
| xoshiro256 (état seul) | 256 | 80 | 4 |
| **xorshift128+, xoroshiro128+** | 128 | **20** | **7** |
| **MT19937** | **19 937** | 80 | **250** |

Les familles **additives** ne sont linéaires que sur le **bit 0** — 20
équations par tirage au lieu de 80 — d'où le facteur 4 sur la collecte.

### Le calendrier

L'app collecte l'ordre à chaque tirage depuis le §38. Un tirage toutes les
cinq minutes :

| tirages | durée | ce qui devient testable |
|---|---|---|
| 2 | 10 min | *déjà fait* (§68) |
| 4 | 20 min | xoshiro256, si la sortie n'est pas brouillée |
| **7** | **35 min** | **les familles additives** |
| 13 | 65 min | toute famille additive jusqu'à 256 bits |
| **250** | **20,8 h** | **MT19937** |

### Et un mur que la collecte ne franchira pas

MT19937 — `random` de Python, `mt_rand` de PHP, la famille la plus répandue du
logiciel ordinaire — demande **250 tirages consécutifs**. Mais une session dure
**204 tirages** (§65), donc 250 consécutifs traversent **nécessairement** une
coupure nocturne.

> Si le générateur se ré-amorce à l'ouverture — le régime C du §65 — la chaîne
> casse, et il faudrait 250 consécutifs **dans** une session. Une session n'en
> compte que 204 : `204 × 80 = 16 320` bits contre **19 937** nécessaires.
> **Il manque un facteur 1,2.**

Le §65 a mesuré que le système se coupe **345 fois** dans l'archive. La
question « tourne-t-il en continu ou se ré-amorce-t-il ? » n'est donc pas
académique : **elle décide seule si la plus répandue des familles est
atteignable.** Et il s'en faut de 22 %.

### Ce que cela ne fait pas

Rien ici ne touche l'archive — c'est un calcul de budget, pas un test. Le
multiply-shift demande une attaque par réseau, non traitée. Et les générateurs
à sortie brouillée non linéairement (PCG, xoshiro `**` et `++`, splitmix64)
comme tout CSPRNG restent hors d'atteinte **quel que soit** le nombre de
tirages collectés : aucun calendrier ne les concerne.

**Registre : inchangé.** `h51` ne teste pas l'archive — il compte.

## 70. Le compteur devient une cible (`LeakBudget.swift`)

Le §51 a posé la règle : *un résultat théorique qui déplacerait un affichage
ne se câble que si sa démonstration ne repose que sur des quantités
observables.* Le théorème de la fuite modulaire y satisfait exactement — il
est **exact** (une congruence, pas une estimation) et son entrée, la plus
longue suite de tirages **ordonnés consécutifs**, est déjà collectée par l'app
depuis le §38.

### Ce que l'app faisait, et ce qui lui manquait

`ProphetStore.longestConsecutiveRun` existait et était affiché : *« il en faut
cinq consécutifs pour que la classe de solutions se referme »* — le critère de
h14, qui reste vrai. Mais le théorème du §68 dit bien davantage : **chaque
palier ferme une classe de générateurs de plus, pour toute graine.** Le
compteur cessait d'être un décompte pour devenir une **cible**, et l'app ne le
savait pas.

### Ce qui est câblé

`LeakBudget.swift` encode le théorème, et **calcule** l'échelle au lieu de la
recopier :

```swift
static var rejectionBitsPerDraw: Int { drawn * v2(pool) }          //  80
static var fisherYatesBitsPerDraw: Int {                            //  22
    (0..<drawn).reduce(0) { $0 + v2(pool - $1) }
}
```

d'où les six paliers `ceil(bits d'état / bits par tirage)` — **1, 2, 4, 7, 13,
250** — et la ligne affichée sous le journal : combien de classes la suite
courante a déjà résolues, quel est le palier suivant, et **en minutes de
collecte**.

Le mur du §69 y est aussi, sous forme exécutable :

```swift
static var mtReachableWithinOneSession: Bool {
    sessionLength * rejectionBitsPerDraw >= 19_937      // 16 320 >= 19 937 : faux
}
```

### Vérification

Aucune toolchain Swift ici (note datée du §53). Les deux vérificateurs passent :

- **`verif_swift.py`** — grammaire Swift réelle : **0 nœud invalide introduit**
  sur les trois fichiers touchés.
- **`verif_logique.py`** gagne une **section 10** qui transcrit la valuation
  2-adique et l'échelle, et les confronte aux paliers publiés : `v₂(80) = 4`,
  `v₂(64) = 6`, `v₂(79) = 0`, 80 contre 22 bits par tirage (rapport ×3,6),
  échelle `[1, 2, 4, 7, 13, 250]` croissante, et `204 × 80 = 16 320 < 19 937`
  au facteur 1,22. **Tout passe.**

Trois tests XCTest sont ajoutés, dont un qui vise la **dérivation** plutôt que
le résultat : l'échelle doit tomber sur les six paliers *en les calculant*, ce
qu'une table recopiée à la main ne garantirait pas.

### Ce que cela change pour l'utilisateur

Rien sur les numéros à cocher — le théorème ne prédit rien, il **résout** un
générateur s'il en existe un de la bonne famille. Ce qu'il change est que
l'app dit désormais **ce que sa propre collecte vaut**, et à quelle échéance :
*« palier suivant à 7 consécutifs — 35 min de collecte — il ouvrirait les
familles additives. »* Une instruction, pas un décompte.

## 71. Le théorème étendu au Fisher-Yates, et l'échange qu'il révèle (`h52_fuite_fisher_yates.py`)

Le §68 établit la fuite pour **un seul** échantillonneur : le rejet modulo 80.
Le §69 a calculé qu'un Fisher-Yates ne fuit que 22 bits par tirage, mais
personne n'avait écrit l'attaque correspondante — le dossier ne savait donc
pas si un Fisher-Yates lui échappe.

### Le théorème, écrit pour un module quelconque

> `j = out mod n` entraîne **`out ≡ j (mod 2^v₂(n))`**

Le §68 est le cas `n = 80`, `v₂ = 4`. Un Fisher-Yates tire modulo `80 − i` au
pas `i`, et **dix pas sur vingt ne publient rien du tout** — leurs modules sont
impairs. Le seul pas modulo 64 = 2⁶ en publie six, soit **27 % du total à lui
seul.**

### L'échange, et il n'est pas dans le sens attendu

Le rejet modulo 80 consomme un nombre **inconnu** de mots — d'où la descente
avec énumération des motifs de rejet du §68 et sa couverture partielle
déclarée. Le Fisher-Yates partiel en consomme **exactement vingt**, un par
pas : la correspondance mot ↔ numéro est **certaine**.

| | bits/tirage | couverture | méthode |
|---|---|---|---|
| rejet modulo 80 (§68) | **80** | 46–99 % | descente + élagage, 12,5 s |
| **Fisher-Yates** (ici) | 22 | **100 %** | **une seule élimination, 0,03 s** |

> Quatre fois moins de bits, mais une couverture **totale** et une attaque
> **quatre cents fois plus rapide**. Un implémenteur qui choisirait le
> Fisher-Yates pour « faire propre » diviserait la fuite par 3,6 — et rendrait
> l'attaque **exacte**.

### Le témoin

| famille | bits | tirages | équations | retrouvé | temps |
|---|---|---|---|---|---|
| xorshift32 | 32 | 2 | 44 | **oui** | 0,00 s |
| xorshift64 | 64 | 3 | 66 | **oui** | 0,01 s |
| xorshift96 | 96 | 5 | 110 | **oui** | 0,02 s |
| xorshift128 | 128 | 6 | 132 | **oui** | **0,03 s** |

Quatre sur quatre, depuis un état tiré au hasard dans tout son espace.

### Sur l'archive

La plus longue suite de tirages **ordonnés consécutifs** du dossier vaut
**2** (1381030, 1381031), soit 44 bits publiés.

| famille | requis | testable | états compatibles |
|---|---|---|---|
| xorshift32 | 2 | **oui** | **0** |
| xorshift64 | 3 | non | — |
| xorshift96 | 5 | non | — |
| xorshift128 | 6 | non | — |

> **La limite n'est pas mathématique, elle est de collecte.** Six tirages
> ordonnés consécutifs — **trente minutes** — rendraient xorshift128 testable
> sous Fisher-Yates. L'app en accumule un toutes les cinq minutes depuis le
> §38, et le §70 affiche désormais l'échéance.

### Ce que la paire (§68, §71) établit ensemble

Les deux échantillonneurs modulaires courants sont désormais couverts, pour
**toute graine**, sur les familles F₂-linéaires. Ce qui reste hors d'atteinte
n'a pas changé et ne changera pas par la collecte : le **multiply-shift** (zéro
bit linéaire — territoire du réseau, déjà traité au §24 pour les LCG), les
sorties **brouillées non linéairement** (PCG, xoshiro `**` et `++`,
splitmix64), et tout **CSPRNG**.

**Registre :** `h52.fuite_fisher_yates`, 0 état compatible, m = 3 335, zéro
significatif.

## 72. Le théorème du trou (`h53_theoreme_du_trou.py`)

Les §68 et §71 exigent des tirages ordonnés **consécutifs**, et le dossier n'en
a qu'une paire. Ses cinq tirages ordonnés en valaient donc deux :

```
1381023   1381026   1381028   1381030   1381031
        \__ 3 __/ \__ 2 __/ \__ 2 __/ \__ 1 __/
```

**Trois des cinq étaient jetés. C'était une erreur de raisonnement, pas une
limite.**

### L'énoncé

> Avancer un générateur F₂-linéaire de `k` pas est **encore une application
> linéaire** : `L^k` l'est dès que `L` l'est.

Un trou ne détruit donc aucune équation — il déplace l'indice du mot, rien de
plus. Il suffit de savoir **de combien de mots** le trou a avancé l'état :

| échantillonneur | consommation | coût du trou |
|---|---|---|
| **Fisher-Yates** | exactement 20 mots/tirage | **nul** — `20g` mots, connu |
| rejet modulo 80 | 20 + R, `E[R] = 2,849` | énumération bornée sur la somme des R |

### Ce que les cinq tirages valent maintenant

| | tirages utilisables | bits (Fisher-Yates) |
|---|---|---|
| avant — consécutifs seuls | 2 | 44 |
| **après — les trous traversés** | **5** | **110** |

| famille | bits | testable avant | testable après |
|---|---|---|---|
| xorshift32 | 32 | oui | oui |
| **xorshift64** | 64 | non | **oui** |
| **xorshift96** | 96 | non | **oui** |
| xorshift128 | 128 | non | non |

### Le témoin, avec les trous exacts de l'archive

Chaque famille est amorcée sur un état tiré au hasard ; on engendre neuf
tirages consécutifs, puis **on ne garde que les positions [0, 3, 5, 7, 8]** —
exactement les trous de l'archive.

| famille | bits | équations | retrouvé | temps |
|---|---|---|---|---|
| xorshift32 | 32 | 110 | **oui** | 0,01 s |
| xorshift64 | 64 | 110 | **oui** | 0,02 s |
| xorshift96 | 96 | 110 | **oui** | 0,03 s |

**Trois sur trois, malgré les trous.**

### Sur l'archive

**0 état compatible** sur les trois familles désormais testables.

> Le budget d'un jeu de tirages ordonnés ne dépend pas de leur **voisinage**
> mais de leur **nombre**. Les données étaient là ; c'est le raisonnement qui
> les jetait.

### Une cible annoncée qui ne tient pas

J'avais annoncé PCG comme prochaine porte, au motif que son brouillage
`XSH-RR` est F₂-linéaire à rotation fixée. **C'est vrai de la sortie et faux de
l'ensemble** : l'état de PCG avance par un LCG modulo 2⁶⁴, qui n'est pas
F₂-linéaire. Les équations de deux sorties successives ne se chaînent donc
pas, et le théorème ne s'applique pas.

PCG reste hors d'atteinte par cette voie — comme xoshiro `**` et `++`,
splitmix64 et tout CSPRNG. La linéarité de la **transition** est aussi
nécessaire que celle de la sortie, et je ne l'avais pas vérifiée avant de
l'annoncer.

### Limite

Sous rejet modulo 80, le trou coûte une énumération sur la somme des rejets
traversés — bornée, mais pas gratuite. Ce fichier ne traite que le cas
Fisher-Yates, où elle est nulle.

**Registre :** `h53.theoreme_du_trou`, 0 état compatible, m = 3 335, zéro
significatif.

## 73. La carte de couverture, et l'hypothèse silencieuse qui la porte (`h54_carte_et_hypothese.py`)

Cinq sections (§68 à §72) ont été ajoutées vite, chacune fermant une case. Il
faut dire exactement ce qui est couvert — et nommer une hypothèse qui porte
**tout** l'édifice et qu'aucune des cinq n'écrivait.

### L'hypothèse

Le théorème de la fuite exige l'**ordre de sortie** : il dit quel mot du
générateur a produit quel numéro. Les cinq tirages ordonnés viennent de
`parseMatrix`, qui préserve l'ordre du tableau `main` de l'API.

> **Rien n'établit que cet ordre soit celui du générateur.**

Il pourrait être l'ordre d'affichage d'une animation, un tri secondaire, ou un
ordre d'insertion. Ce qu'on peut vérifier ici est peu de chose : **0 des 5**
tirages ordonnés est déjà trié, ce qui exclut le cas le plus grossier — et
rien de plus.

### Ce qu'un ordre faux coûterait

Si l'ordre est faux, les équations associent le mauvais mot à chaque numéro,
le système devient incohérent, et l'attaque ne trouve rien — **exactement
comme si le générateur n'était pas de la famille**. Un « 0 état compatible » a
donc deux lectures :

1. le générateur n'appartient à aucune famille testée ;
2. l'ordre enregistré n'est pas celui du générateur.

**Elles sont indiscernables par les §68 à §72.** Ce que les cinq sections
établissent est donc exactement :

> **Si** l'ordre enregistré est celui du générateur, **alors** aucune des
> familles testées ne produit ces tirages, pour aucune graine.

Et rien de plus fort. Ce qui lèverait l'ambiguïté, par ordre de coût : **un
témoin d'ordre** (comparer un tirage à l'animation — coût nul, une
observation) ; la documentation technique ; ou une attaque qui aboutirait, ce
qui validerait l'ordre rétrospectivement.

### La carte

| famille | échantillonneur | § | condition |
|---|---|---|---|
| LCG mod 2⁴⁸ (`java.util.Random`) | **Fisher-Yates seulement** | §34 | 2-adique, **2⁴⁸ complets**, toute graine |
| LCG mod 2⁴⁸ (`java.util.Random`, `drand48`) | **rejet** | §97 | 2-adique, **2⁴⁸ complets**, couverture 1 − 9,4·10⁻¹² |
| LCG à constantes connues | multiply-shift | §24 | réseau LLL + Babai, 9/9 témoins |
| LCG à constantes **inconnues** | ordonné | §25 | théorème des deux états, (a,c) calculés |
| 12 familles | 4 échantillonneurs | §34 | graines [0, 2³²) **énumérées** |
| 8 familles | 4 échantillonneurs | §63 | graine = horloge ou compteur |
| 8 familles | 4 échantillonneurs | §65 | amorçage unique + course continue |
| **F₂-linéaires ≤ 128 bits** | rejet modulo 80 | §68 | **résolu**, toute graine, couverture 46–99 % |
| **F₂-linéaires ≤ 128 bits** | Fisher-Yates | §71 | **résolu**, toute graine, couverture 100 % |
| **F₂-linéaires ≤ 110 bits** | FY, tirages **non voisins** | §72 | **résolu**, trous gratuits |

**Ce qui reste — et aucune collecte n'y changera rien :**

| | pourquoi |
|---|---|
| PCG (XSH-RR) | l'état avance par LCG mod 2⁶⁴ : la **transition** n'est pas F₂-linéaire |
| xoshiro `**` et `++` | brouillage de sortie multiplicatif ou additif |
| splitmix64 | mixeur non linéaire à deux multiplications |
| MT19937 | F₂-linéaire, mais 19 937 bits (§69) |
| tout CSPRNG | casser la famille = casser la primitive |
| matériel (TRNG) | aucun état, donc rien à résoudre |

### Le budget, en une formule

> Pour `N` tirages ordonnés, **pas nécessairement voisins**, d'un générateur
> F₂-linéaire : `bits = N × Σᵢ v₂(module au pas i)`.

| N | rejet mod 80 | Fisher-Yates | ce que N ouvre (FY) |
|---|---|---|---|
| **5** *(le dossier)* | 400 | **110** | xorshift96 |
| 10 | 800 | 220 | xorshift128 |
| 20 | 1 600 | 440 | état 256 bits |
| **907** | 72 560 | **19 954** | **MT19937** |

MT19937 demanderait N = 907 sous Fisher-Yates ou N = 250 sous rejet — et sous
rejet les trous coûtent une énumération, donc il les faudrait **voisins**, ce
qu'une session de 204 tirages ne permet pas.

### Ce que cette section change

Elle ne ferme aucune case nouvelle. Elle empêche une case fermée **par
hypothèse** de passer pour fermée tout court — et elle transforme cinq
affirmations en une **implication** dont la prémisse est nommée, chiffrée, et
falsifiable pour un coût nul.

**Registre : inchangé.** `h54` ne teste pas l'archive — il cartographie.

## 74. L'arithmétique du vivier, et un résultat négatif qui valide le §69 (`h55_arithmetique_du_vivier.py`)

Deux questions, l'une négative et l'autre structurelle.

### Jetait-on de l'information ?

Le §69 compte 80 bits par tirage : 4 bits × 20 numéros **acceptés**. Il ignore
les ~2,85 mots **rejetés**. Un compte naïf suggérerait +11 bits.

Un mot est rejeté exactement quand `out mod 80 + 1` est **déjà vu**. À l'étape
`k`, cela contraint `out mod 16` à `min(k, 16)` valeurs sur 16 :

> information d'un rejet à l'étape `k` = `4 − log₂(min(k, 16))` bits,
> avec `k/(80 − k)` rejets attendus à cette étape.

| étape k | rejets attendus | candidats | bits gagnés | contribution |
|---|---|---|---|---|
| 1 | 0,013 | 1 | 4,00 | 0,051 |
| 5 | 0,067 | 5 | 1,68 | 0,112 |
| 10 | 0,143 | 10 | 0,68 | 0,097 |
| 15 | 0,231 | 15 | 0,09 | 0,022 |
| 19 | 0,312 | 16 | **0,00** | 0,000 |

> **Total : 1,26 bit par tirage, soit +1,6 %.** La réponse est **non**.

Les rejets arrivent **tard** — leur fréquence croît en `k/(80−k)` — et c'est
précisément quand ils sont fréquents que l'ambiguïté les vide : à 16 numéros
déjà vus, un rejet ne dit **plus rien du tout**, les 16 résidus étant tous
candidats. *L'ambiguïté croît exactement au rythme de la fréquence.*

Exploiter les rejets multiplierait l'arbre de recherche par une dizaine par
rejet, pour 1,26 bit. Mauvais échange — et le chiffrer était la seule façon de
le savoir. **Le §69 avait raison à 1,6 % près.**

### De quoi la fuite dépend-elle, exactement ?

Sous rejet, tous les numéros passent par le même module, donc

> **fuite = 20 × v₂(vivier)**

Elle ne dépend ni du jeu, ni du générateur, ni du joueur : de la **valuation
2-adique d'un seul entier**. Et `v₂` est brutalement discontinue.

| vivier | v₂ | rejet modulo | Fisher-Yates | |
|---|---|---|---|---|
| 78 | 1 | 20 | 20 | |
| **79** | **0** | **0** | 20 | *vivier impair : fuite nulle* |
| **80** | **4** | **80** | 22 | **← le vivier réel** |
| **81** | **0** | **0** | 22 | *vivier impair : fuite nulle* |
| 96 | 5 | 100 | 21 | pire que 80 |
| 128 | 7 | 140 | 23 | pire que 80 |

> **La fuite est tout ou rien.** 34 des 69 tailles de vivier entre 60 et 128
> sont **impaires et ne publient rien**. Un vivier de **79** rendrait le
> théorème du §68 entièrement vide.
>
> Le vivier réel vaut 80 = 2⁴ × 5 — presque le pire choix de sa plage : seul
> 128 fait mieux.

Sous Fisher-Yates la fuite ne s'annule **jamais** : les modules 80, 79, …, 61
balaient une plage où l'on rencontre toujours des puissances de deux (minimum
18 bits, maximum 23). Et le rapport entre les deux échantillonneurs
s'**inverse** : 80 contre 22 à vivier 80, **0 contre 20** à vivier impair.

### Ce que cela établit

**La vulnérabilité des §68 à §73 n'est pas une propriété des générateurs.**
C'est une rencontre entre trois choses :

1. un générateur **linéaire sur F₂**,
2. un échantillonneur **par modulo**,
3. un vivier **divisible par 16**.

Les trois sont nécessaires. **Retirer n'importe laquelle ferme la voie** — et
un opérateur qui aurait choisi 79 numéros au lieu de 80 l'aurait fermée sans
le savoir, sans changer une ligne de son code.

**Registre : inchangé.** `h55` ne teste pas l'archive — il dérive.

## 75. Le câblage du §70, corrigé par le §72

Le §70 a câblé le budget de fuite dans l'app en lui passant
`longestConsecutiveRun` — la plus longue suite de tirages ordonnés
**consécutifs**. Deux sections plus tard, le §72 a démontré que la
consécutivité **n'est pas nécessaire** : avancer un générateur F₂-linéaire de
`k` pas reste une application linéaire.

> **Mon propre théorème a invalidé mon propre câblage.** L'app affichait une
> cible inutilement pessimiste — elle jetait trois des cinq tirages ordonnés
> du dossier, exactement l'erreur que le §72 a corrigée côté labo.

### Ce qui est corrigé

`LeakBudget.status(run:)` devient `status(count:)` : le paramètre est un
**nombre** de tirages ordonnés, pas une suite.

### Mais le compte lui-même a deux lectures

Le théorème du trou exige de savoir **de combien de mots** le trou a avancé
l'état. Sous Fisher-Yates c'est exact — *à condition que le générateur n'ait
pas été ré-amorcé entre-temps.* Or le §65 n'a pas tranché cette question.

D'où deux budgets, et les afficher tous les deux est la seule position tenable :

| lecture | hypothèse | compte |
|---|---|---|
| `continuous` | le générateur traverse les coupures | **tous** les tirages ordonnés |
| `perSession` | il se ré-amorce chaque matin | le **maximum par session** |

Le découpage vient du §65, mesuré : **345 sessions de 204 tirages**, première
session complète à partir du tirage **1 309 794**. Les numéros de tirage étant
consécutifs à travers les coupures, la session ne se lit que par ce découpage.

L'app affiche désormais le compte **prudent** (`perSession`) comme cible, et
signale le compte optimiste entre parenthèses quand les deux diffèrent.

### Vérification

Les cinq tirages ordonnés du dossier tombent tous dans la **session 349** :
les deux lectures coïncident aujourd'hui (5 et 5), et la correction ne change
donc aucun chiffre affiché — elle change ce que l'affichage **signifie**, et
elle le rendra juste dès que la collecte franchira une coupure.

`verif_swift.py` : 0 nœud invalide sur les trois fichiers.
`verif_logique.py` : le découpage en sessions vérifié (les cinq tirages en
session 349 ; une coupure sépare bien deux sessions). Un test XCTest ajouté
pour les deux lectures.

### La leçon, et elle vaut d'être gardée

Le §70 obéissait au principe du §51 — ne câbler que ce qui repose sur des
quantités observables — et il l'a bien fait. Ce qu'il ne pouvait pas faire,
c'est anticiper qu'une section ultérieure élargirait le théorème sur lequel il
s'appuyait. **Un câblage correct peut devenir périmé sans jamais avoir été
faux**, et le seul remède est de le relire quand le théorème bouge.

## 76. L'ombre du théorème, testable sans l'ordre (`h56_classes_residuelles.py`)

Les §68 à §75 exigent l'**ordre de sortie**, et le dossier n'en a que cinq
tirages. L'archive triée — **70 560 tirages** — leur est inutile.

Or le théorème a une ombre qui, elle, ne demande pas l'ordre.

### L'ombre

Considérons un générateur **congruentiel modulo une puissance de deux** dont la
sortie est l'état brut :

    s_{i+1} = a·s_i + c  (mod 2^k)      puis   n = (s mod 80) + 1

Les bits de poids faible d'un LCG modulo 2^k sont **fermés** : `s mod 16` suit
lui-même un LCG modulo 16, de période exactement 16 pour les constantes
usuelles. Seize mots consécutifs visitent donc **les seize résidus**.

> Un tirage consomme ~23 mots et en retient 20. Ses vingt numéros se
> répartiraient donc **presque uniformément** entre les seize classes
> résiduelles — jamais zéro dans une classe, jamais quatre — là où le hasard
> laisse des trous. **Et cela se lit sur l'ensemble des numéros : l'ordre
> n'intervient pas.**

Aucun test du registre ne visait cette partition. Une telle structure se
diluerait dans les 3 160 paires d'`audit.paires` : les 160 paires intra-classe
seraient déprimées, mais un maximum sur 3 160 ne le verrait pas.

### Le témoin, et il confirme la théorie plus finement qu'attendu

Archive contaminée par un LCG modulo 2³² à sortie brute, χ² des comptes par
classe, rapporté au SRS :

| m | 2 | 4 | **5** | 8 | **10** | 16 | **20** | **40** |
|---|---|---|---|---|---|---|---|---|
| rapport | **0,078** | **0,083** | 1,19 | **0,150** | 1,07 | **0,210** | 1,01 | 1,00 |

> Le χ² **s'effondre** exactement aux diviseurs qui sont des **puissances de
> deux** (2, 4, 8, 16) et reste à 1 sur ceux qui portent le facteur 5. C'est
> précisément ce que la fermeture 2-adique prédit : les bits de poids faible
> se ferment modulo 2^j, **jamais modulo 5**. Le témoin ne se contente pas de
> détecter — il détecte *au bon endroit*.

### Sur l'archive réelle : rien

Null simulé, 400 archives, loi hypergéométrique multivariée exacte :

| m | observé | null | z | p |
|---|---|---|---|---|
| 2 | 53 441 | 53 585 ± 283 | −0,51 | 0,651 |
| 4 | 160 294 | 160 750 ± 489 | −0,93 | 0,372 |
| **5** | 213 718 | 214 313 ± 508 | **−1,17** | **0,267** |
| 8 | 374 506 | 375 119 ± 711 | −0,86 | 0,367 |
| 16 | 804 120 | 803 820 ± 947 | +0,32 | 0,783 |
| 40 | 2 090 068 | 2 090 006 ± 1 229 | +0,05 | 0,958 |

Le plus petit `p` vaut **0,267** sur 8 tests. Registre **m = 3 336**, zéro
significatif.

### Ce que cela ajoute

Le théorème de la fuite avait une ombre que personne n'avait cherchée : sa
conséquence sur l'**ensemble** des numéros, là où le théorème porte sur leur
ordre. Cette ombre se teste sur **70 560 tirages au lieu de cinq** — quatre
ordres de grandeur de données en plus.

### Ce que cela ne fait pas

1. Un générateur qui **décale avant de réduire** (`java.util.Random` rend
   `s >> 17`) n'a pas ses bits de poids faible en sortie : la fermeture ne
   s'applique pas. Le §34 le couvrait déjà.
2. Un générateur **F₂-linéaire** (xorshift) n'a pas de bits fermés non plus —
   c'est le §68 qui le vise, et lui exige l'ordre.
3. Le test **détecte sans résoudre**. Une détection renverrait vers les §68 à
   §72 pour l'exploitation.

**Registre :** `h56.classes_residuelles`, `p` = 0,267, `m_extra` = 7.

## 77. Le bonus, seule donnée ordonnée que l'archive triée contienne (`h57_bonus_ordonne.py`)

Le §11 conclut que l'archive triée a perdu l'ordre de sortie. **C'est vrai des
vingt numéros, et faux du bonus.**

### L'observation

Chaque tirage porte un bonus, présent sur les **70 560** lignes, et qui
appartient **toujours** aux vingt numéros tirés (70 560 / 70 560 vérifié). Le
bonus n'est donc pas un vingt-et-unième numéro : c'est un **pointeur** vers
l'un des vingt.

> Si ce pointeur désigne une **position fixe** de l'ordre de sortie, l'archive
> triée contient 70 560 données ordonnées que personne n'avait lues comme
> telles.

### La position qui se teste, et pourquoi c'est la seule

Sous Fisher-Yates, le numéro du pas `i` est l'ancien `a[j]` avec
`j = i + out_i mod (80−i)` : le retrouver demande **tout le préfixe**. Sauf au
pas 0, où le tableau est encore `1..80` :

    premier numéro tiré = (out₀ mod 80) + 1

Donc si le bonus est le **premier** numéro sorti, chaque tirage publie
`out₀ mod 16` — quatre bits — à un indice de mot **exactement connu** (20 mots
par tirage sous Fisher-Yates). Pour les positions `j > 0` le préfixe manque, et
le bonus ne dit rien d'exploitable.

### Le budget que cela ouvre

| source | tirages | bits |
|---|---|---|
| les cinq tirages ordonnés (§72) | 5 | 110 |
| **une session** | 204 | **816** |
| **l'archive entière** | 70 560 | **282 240** |

Trois ordres de grandeur, sur des données **déjà collectées**.

### Le témoin

Une archive fabriquée où le bonus est *posé* comme premier numéro :

| famille | bits | tirages | équations | retrouvé | temps |
|---|---|---|---|---|---|
| xorshift32 | 32 | 32 | 128 | **oui** | 0,02 s |
| xorshift64 | 64 | 64 | 256 | **oui** | 0,07 s |
| xorshift96 | 96 | 96 | 384 | **oui** | 0,23 s |
| xorshift128 | 128 | 128 | 512 | **oui** | 0,46 s |

**Quatre sur quatre, depuis les seuls bonus.** *(Une première version prenait
le strict minimum d'équations — `nbits/4` tirages — et échouait au-delà de 32
bits : les quatre équations d'un tirage ne sont pas indépendantes. Une session
en offre 816 ; il n'y avait aucune raison d'être avare.)*

### Sur l'archive

**346 sessions × 4 familles = 1 384 attaques, 0 état compatible.** Registre
`m = 3 336`, zéro significatif.

### Ce que cela n'est pas

Un échec a **deux lectures**, comme au §73 :

1. le générateur n'est d'aucune famille testée ;
2. **le bonus n'est pas le premier numéro sorti.**

Le test est donc **conjoint**, et il établit une implication : *si le bonus est
le premier numéro, alors aucune famille testée ne convient.*

### Ce qui lèverait l'ambiguïté

Le §37 a montré que l'archive triée ne peut **pas** trancher la règle du bonus
— non pas difficilement, mais par **non-identifiabilité**. Les tirages ordonnés
que l'app accumule depuis le §38 donnent la position du bonus *directement* :
une dizaine suffirait, et ils sont collectés un toutes les cinq minutes.

> C'est la deuxième fois que la même mesure — quelques tirages ordonnés —
> débloque deux choses à la fois : elle valide l'hypothèse d'ordre du §73 **et**
> la règle de position d'ici.

### Limite de calcul

MT19937 demanderait 4 985 tirages, soit 24 sessions chaînées — informationnellement
disponible, mais son élimination porte sur 19 937 inconnues, ce que Python ne
fait pas en temps raisonnable. **La limite est ici computationnelle, pas
informationnelle**, et c'est la première fois dans ce volet.

**Registre :** `h57.bonus_ordonne`, 0 état compatible.

---

## 78. Le taux de change : ce qu'un bit du générateur vaut en numéros (`h58_taux_de_change.py`)

Le dossier tenait deux théorèmes qui ne se parlaient pas.

| | énoncé | côté |
|---|---|---|
| **invariance** | `E[touches] = k/4` sous échangeabilité | table |
| **fuite (§68)** | `out ≡ n−1 (mod 16)` — quatre bits publiés par numéro | générateur |

Entre les deux, **rien**. Aucune section ne disait combien de touches achète un
bit de fuite — donc aucune ne disait *quelle partie* du générateur il faut
reproduire pour que le pari bascule. « Franchir le mur » n'avait pas de sens
quantitatif.

### Le théorème de conversion

Un générateur publie `b` bits par mot ; l'échantillonnage est un rejet modulo
80. Les numéros se partagent en `M = 2^b` classes de `s = 80/M` membres, la
classe de `n` étant `(n−1) mod M`. Si l'on connaît les résidus des `r` premiers
numéros tirés, de comptes `m_c`, alors pour `x` membre de la classe `c` :

> **P(x tiré | m) = [ m_c + (s − m_c)(20 − r)/(80 − r) ] / s**   (\*)

*Preuve.* Conditionnellement aux comptes, l'identité des `r` premiers est
uniforme dans chaque classe, donc `P(x parmi les r premiers) = m_c/s`. Sinon `x`
reste dans le vivier de `80 − r` numéros dont `20 − r` seront tirés. Somme. ∎

Trois lectures, et la troisième est le résultat.

1. **`r = 0` rend `P = 1/4` pour tout `x`.** Le théorème d'invariance devient un
   *cas particulier* du théorème de conversion — celui où l'on ne sait rien.
   Vérifié à 2·10⁻¹⁶ près.
2. **La somme de (\*) sur les 80 numéros vaut exactement 20**, pour tout `m` et
   tout `r`. L'invariance n'est donc jamais **violée** : elle est **contournée**.
   La masse totale reste 20 ; c'est sa *répartition* qui cesse d'être uniforme.
3. **`P` croît en `m_c`**, donc la grille optimale se lit sans recherche : trier
   les classes par compte décroissant et les remplir. Le problème de décision
   est résolu en fermeture, pas par optimisation.

### La loi exacte, parce que le Monte-Carlo ment ici

(\*) donne l'espérance ; le barème, lui, paie des **rangs**. Une première
version de ce fichier a estimé les taux de retour par simulation et **a produit
des chiffres faux** : à `k = 8`, `b = 4`, `r = 20`, le rang plein pèse **4,31 à
lui seul** dans le taux de retour pour une probabilité de 8,6·10⁻⁴. Sur 400 000
tirages le Monte-Carlo en voit 347 — 5 % d'erreur sur le poste dominant, et
bien pire aux petits échantillons.

La loi est donc calculée **exactement**, en trois étages : partitions des
comptes observés (les classes étant échangeables, seule la suite triée compte),
hypergéométrique multivariée pour les numéros restants, hypergéométrique simple
pour la classe entamée. Un Monte-Carlo *indépendant* de 400 000 tirages vérifie
les espérances — écart maximal **1,98 σ** sur neuf configurations.

### Le taux de change, en touches (les vingt résidus connus)

| k joués | b=0 | b=1 | b=2 | b=3 | b=4 | gain × |
|---|---|---|---|---|---|---|
| 5 | 1,250 | 1,441 | 1,760 | 2,270 | **3,090** | 2,47 |
| 8 | 2,000 | 2,305 | 2,815 | 3,632 | **4,599** | 2,30 |
| 10 | 2,500 | 2,881 | 3,519 | 4,540 | **5,604** | 2,24 |

Le premier bit rapporte 0,38 touche à `k = 10`, le quatrième **1,06** — 2,8 fois
plus. La raison est arithmétique : jouer « une classe » coûte `s = 80/2^b`
numéros, et `s = 5` est atteint exactement à `b = v₂(80) = 4`. **Le coude du
taux de change et la fuite du §68 sont gouvernés par le même entier** — celui
dont le §74 montrait qu'un vivier impair l'annulerait.

### Le résultat : trois bits d'un seul mot

Le mot qui produit le **premier** numéro est toujours accepté — aucun doublon
n'est encore possible — donc son résidu est connu *sans aucune hypothèse
d'alignement*. Supposons qu'on ne sache rien d'autre du générateur. Taux de
retour, barème du §56, ticket à CHF 2, **hors cagnotte** :

| b bits du mot 0 | k=5 | k=6 | k=7 | k=8 | k=10 |
|---|---|---|---|---|---|
| 0 | 0,586 | 0,588 | 0,599 | 0,583 | 0,588 |
| 1 | 0,664 | 0,666 | 0,676 | 0,687 | 0,670 |
| 2 | 0,822 | 0,821 | 0,831 | 0,895 | 0,833 |
| **3** | 1,136 | 1,130 | 1,140 | **1,309** | 1,160 |
| **4** | **1,765** | 1,543 | 1,405 | 1,517 | 1,160 |

> **TROIS BITS SUFFISENT.** Connaître les trois bits de poids faible du **seul**
> mot qui produira le premier numéro du prochain tirage, et jouer les dix
> numéros de sa classe résiduelle, porte le taux de retour de **0,583 à 1,309**.
> Quatre bits le portent à **1,765** en n'en jouant que cinq.

Et le corollaire négatif oriente autant que le résultat : connaître **un** bit
des **vingt** numéros — vingt fois plus d'observations — ne franchit pas le
seuil (0,964). **Ce n'est pas le volume d'information qui décide, c'est la
valuation 2-adique du vivier.**

### Ce que cela change au programme de recherche

| | avant (§77) | maintenant |
|---|---|---|
| objectif | résoudre l'état | prédire 3 formes linéaires |
| taille | 19 937 inconnues | 3 bits, soit 0,015 % de l'état |
| nature du mur | **rang** plein du système | **appartenance** à l'espace engendré |

Le §77 butait sur un mur de rang : 204 tirages par session donnent 16 320
équations pour 19 937 inconnues, et le système reste sous-déterminé. Mais
**prédire trois bits ne demande pas le rang plein** — seulement que ces trois
formes linéaires appartiennent à l'espace engendré par celles déjà observées.
Un système sous-déterminé prédit *quand même* tout ce qui tombe dans son image.

Les deux murs n'ont donc ni la même hauteur ni la même nature, et le dossier
attaquait le mauvais.

### Le régime A, de bout en bout

La chaîne complète — ordre → équations → état → prédiction → grille — sur
xorshift64, 80 graines de 64 bits tirées au hasard, **un seul** tirage ordonné
observé :

| | |
|---|---|
| états retrouvés | **80 / 80** |
| tirages suivants prédits | **80 / 80** (les vingt numéros, dans l'ordre) |
| touches en jouant 10 | **10,0 / 10** (contre 2,50 sous invariance) |

Ce n'est pas un résultat sur le jeu réel : c'est la preuve que la chaîne est
complète et sans trou dès que le générateur est F₂-linéaire. Le §68 donnait le
maillon algébrique ; le §78 le prolonge jusqu'au bulletin.

### Ce que cela ne fait pas

1. **Les colonnes `r > 1` supposent le rejet modulo le vivier.** Sous
   Fisher-Yates la fuite tombe à 22 bits (§71) et les résidus portent sur des
   *indices* dans un tableau déjà permuté, à partir du deuxième numéro.
   **Mais le cas `r = 1` survit aux deux échantillonneurs, et c'est celui du
   résultat** : au pas 0, Fisher-Yates lit le tableau intact `1..80` et tire
   modulo 80, donc `premier numéro = (out₀ mod 80) + 1` exactement, comme sous
   rejet (§77). Le mur — trois bits d'un seul mot — **ne dépend pas de
   l'échantillonneur**, et c'est le seul endroit du volet §68–§78 dont ce soit
   vrai.
2. **Rien ne dit que le tirage réel est vulnérable.** Les tests d'archive — §76
   sur les 70 560 tirages, §68 et §77 sur les cinq tirages ordonnés — n'ont rien
   trouvé. Ce fichier chiffre la **valeur** d'une porte ; il n'en ouvre aucune.
3. **La cagnotte BANGO n'entre pas dans ces taux.** Tous les chiffres ci-dessus
   sont des bornes inférieures.

**Registre : inchangé.** h58 dérive, vérifie sa dérivation par simulation
indépendante, et chiffre.

---

## 79. La fenêtre entre le détectable et le rentable, et le test qui la ferme (`h59_fenetre.py`)

Le §78 rend posable une question que le dossier n'avait jamais pu poser. Il a
produit 162 tests consignés et **zéro significatif** — mais « rien de
significatif » ne dit pas « rien d'exploitable » : un biais peut être trop petit
pour être vu et assez grand pour payer. C'est la **fenêtre**. Faute de savoir
convertir un biais en francs, personne ne pouvait la mesurer.

### Le modèle, et pourquoi c'est le seul possible

Un sous-ensemble `H` de `s` numéros « chauds », de cote `ω` contre 1. Le nombre
de chauds tirés suit alors **exactement** l'hypergéométrique non centrée de
Fisher, `P(n_H = j) ∝ C(s,j)·C(80−s, 20−j)·ω^j` — c'est la loi conditionnelle de
80 Bernoulli indépendantes *sachant que leur somme vaut 20*, donc le seul modèle
de biais compatible avec la contrainte « exactement vingt numéros par tirage ».
Le biais relatif par numéro chaud est `δ = E[n_H]/(20s/80) − 1`, et la loi des
touches se calcule exactement, par convolution de deux hypergéométriques.
Contrôle : à `ω = 1`, `δ = 0` et le taux de retour redonne le barème du §56.

### δ\* — le biais minimal rentable

| s chauds | ω\* | **δ\*** | k optimal | TRR |
|---|---|---|---|---|
| 5 | 1,258 | 0,1550 | 5 | 1,000 |
| **8** | **1,177** | **0,1189** | **8** | 1,000 |
| 20 | 1,171 | 0,1236 | 8 | 1,000 |
| 40 | 1,296 | 0,1443 | 10 | 1,000 |

> Pour qu'un biais de fréquence rende le pari favorable, il faut que huit
> numéros sortent **1,12 fois plus souvent** que les autres. Le barème prend
> 41 % de marge : il faut la combler.

### δ_min — le biais minimal détectable

Sous H₀, le compte d'un numéro sur `m` tirages suit **exactement** une
binomiale(`m`, 1/4) — l'indépendance d'un tirage à l'autre est acquise, seule la
dépendance *entre* numéros d'un même tirage existe, et elle joue dans le sens
conservateur. D'où `E[z] = δ·√(m/3)`, soit un facteur de conversion de **153,4**
sur les 70 560 tirages.

Au seuil de Holm du registre entier (m = 3 336, donc `p < 1,5·10⁻⁵`), le
détecteur **aveugle** — le max|z| sur les 80 numéros, celui que le dossier a
réellement appliqué — exige `t = 5,21`, plus 2,33 pour une puissance de 99 % :

> **δ_min = 0,0492**

### Le verdict, et il faut le dire avec sa marge

| | |
|---|---|
| δ\* (rentable) | 0,1189 |
| δ_min (détectable) | 0,0492 |
| **rapport** | **2,4** |

Un biais assez grand pour payer aurait produit un `z` de **18** sur chacun de ses
numéros chauds. L'archive mesure un maximum de **2,72**. Témoin mesuré :
contaminée à δ\*, l'archive déclenche **200/200** fois au seuil de Holm.

> **La fenêtre stationnaire est fermée** — mais le facteur est 2,4, pas mille.
> C'est une marge étroite, et elle tiendrait mal si le barème était plus
> généreux ou le ticket moins cher. Il faut le dire tel quel.

### Et une fenêtre bien plus grande était ouverte

Le verdict ci-dessus ne porte que sur les biais **stationnaires**. Un biais qui
rebat ses numéros chauds au fil du temps s'annule dans le compte global. Si le
biais bascule tous les `W` tirages, un balayage paie la multiplicité de
`80 × m/W` tests et le facteur de conversion tombe à `√(W/3)` :

| W | fenêtres | z requis | δ détectable | rentable ? |
|---|---|---|---|---|
| 100 | 705 | 8,65 | 1,498 | **OUI** |
| **204** (session, §65) | 345 | 8,54 | **1,035** | **OUI** |
| 2 000 | 35 | 8,17 | 0,316 | **OUI** |
| 70 560 | 1 | 7,54 | 0,049 | non |

> Un biais rebattu à chaque **session** — la coupure réelle du §65 — paie dès
> `δ = 0,12` et n'est détectable par balayage qu'à partir de `δ = 1,04`. La
> fenêtre non stationnaire n'était pas étroite : elle était **grande ouverte,
> d'un facteur 8**, et précisément là où le générateur coupe.

### Le test qui la ferme : sur-dispersion par session

**Le balayage est le mauvais test.** Chercher *où* est le biais coûte toute la
multiplicité ; ne chercher que *son existence* n'en coûte aucune. Un biais
rebattu à chaque session ne déplace aucune moyenne globale mais **gonfle la
variance** des comptes par session, et ce gonflement **s'additionne** au lieu de
s'annuler :

> `T = Σ_{session, numéro} (compte − 51)² / 38,25`, sur 344 sessions × 80 numéros

| | valeur |
|---|---|
| observé | 27 600 |
| null (200 archives SRS complètes) | 27 525 ± 239 |
| **z** | **+0,31** — p = 0,736, **conforme** |

**Témoin positif**, et c'est lui qui fait le travail : archive contaminée au
biais **minimal rentable** δ\* = 0,119, vivier chaud **rebattu à chaque
session** —

| détecteur | résultat |
|---|---|
| sur-dispersion (ce test) | z ≈ **12,3**, **40/40** détections |
| max\|z\| marginal (§79 §4) | 3,04 — **sous son seuil de 5,21, aveugle** |

Le témoin établit exactement ce qu'il fallait : le nouveau test voit ce que
l'ancien ne voit pas, au biais précis qui rendrait le jeu favorable.

**Registre : `h59.surdispersion_session`, p = 0,736, conforme. m = 3 337, zéro
significatif.**

### Ce que le §79 établit

1. **Le théorème de la fenêtre.** Le taux de change du §78 permet de comparer
   biais rentable et biais détectable. Stationnaire : fermée d'un facteur 2,4.
2. **La fenêtre non stationnaire était ouverte d'un facteur 8**, et le dossier
   l'ignorait — c'est le §78 qui l'a révélée en donnant enfin δ\*.
3. **Elle est fermée maintenant**, par un test qui ne coûte aucune multiplicité
   parce qu'il demande l'existence et non la position.
4. **Conséquence.** Les deux fenêtres statistiques de fréquence étant closes,
   il ne reste que la voie du générateur — où le §78 a montré que **trois bits
   suffisent**. Le dossier a, pour la première fois, une cible unique et
   chiffrée.

Reste ouvert, et nommé : les biais qui ne sont pas de *fréquence* (paires,
géométrie, ordre — couverts ailleurs, mais dont le taux de change n'est pas
calculé) ; les biais de période autre que la session ou l'archive ; et la
cagnotte BANGO, absente de tous ces taux, qui ne peut que les relever.

---

## 80. Le théorème d'appartenance, et le raccourci qu'il autorise (`h60_appartenance.py`)

Le §78 avait déplacé le mur : il ne faut pas **résoudre** l'état (19 937
inconnues) mais **prédire** trois formes linéaires. Et prédire une forme n'exige
pas le rang plein — `A·x = y` détermine `ψ·x` **si et seulement si** `ψ`
appartient à l'espace engendré par les lignes de `A` (l'ensemble des solutions
est `x₀ + ker A`, et `ψ·x` y est constant ssi `ψ ⊥ ker A`, c'est-à-dire
`ψ ∈ (ker A)^⊥ = ` espace des lignes). Le §78 concluait, prudemment, que « le
mur du §77 est un mur de **rang**, celui-ci un mur d'**appartenance** ».
Restait à savoir de combien.

### Le théorème

> **Théorème d'appartenance.** Soit `L` linéaire sur F₂, d'espace d'état de
> dimension `n`, de polynôme minimal `π`. On observe pour chaque mot `k` un jeu
> `J` de formes `φⱼ∘L^k` ; soit `V_W` l'espace engendré par les `W` premiers
> mots. **Si `π` est irréductible et si toutes les formes du mot suivant
> appartiennent à `V_W`, alors `V_W` est l'espace dual tout entier** — donc le
> rang est plein et l'état entièrement déterminé.

*Preuve.* La composition avec `L` agit sur le dual ; notons-la `T`. Par
définition `T(φⱼ∘L^k) = φⱼ∘L^{k+1}`, donc
`T(V_W) ⊆ V_W + ⟨φⱼ∘L^W⟩`. Si toutes les formes du mot `W` sont dans `V_W`, ce
second terme l'est aussi : `T(V_W) ⊆ V_W`. `V_W` est alors stable par `T`, donc
par tout polynôme en `T` — c'est un sous-module de F₂[T]. Or le dual a pour
polynôme minimal `π` irréductible de degré `n` : il est isomorphe au **corps**
F₂[T]/(π), dont les seuls sous-modules sont 0 et lui-même. Comme `V_W` contient
`φⱼ ≠ 0`, `V_W` est le dual entier. ∎

**Portée.** Tout générateur de période `2ⁿ − 1` a un polynôme caractéristique
primitif, donc irréductible : xorshift, xoshiro, et **MT19937** (dont la période
`2^19937 − 1` est un nombre de Mersenne premier). Pour eux, prédire le **quartet
complet** du prochain mot coûte exactement autant que résoudre l'état.

**Ce que le théorème ne couvre pas**, et la restriction est essentielle : il
exige *toutes* les formes. Un **sous-ensemble strict** — et le §78 n'en demande
que trois sur quatre — échappe à l'argument de stabilité.

### Le témoin : le théorème n'est pas vide

Un générateur construit exprès, 64 bits d'état dont 32 **muets** (ils avancent
mais n'entrent dans aucune sortie). Son polynôme se factorise, l'hypothèse
tombe, et le résultat suit : rang saturé à 32, mais **appartenance du quartet
complet dès le mot 9**. La machinerie sait donc voir le phénomène quand il est
là.

### Les familles du dossier

| famille | n | W(1 bit) | W(quartet) | W(rang) | rang final |
|---|---|---|---|---|---|
| xorshift32 | 32 | 8 | 9 | 9 | 32 |
| xorshift64 | 64 | **13** | 19 | 19 | 64 |
| xorshift96 | 96 | **17** | 28 | 28 | 96 |
| xorshift128 | 128 | **30** | 33 | 33 | 128 |
| taus88 | 96 | 22 | 22 | 22 | **88** |

`W(quartet) = W(rang)` partout : le théorème le prédisait, le calcul le
confirme. **Mais `W(1 bit)` ne coïncide pas** — 17 mots contre 28 sur
xorshift96, soit **39 % de collecte en moins**. Le raccourci du §78 est réel.

**taus88 est le cas à part**, et sa période le disait : `(2³¹−1)(2²⁹−1)(2²⁸−1)`
et non `2⁸⁸−1`. Son rang **sature à 88** au lieu de 96 — trois bits par LFSR
sont inertes. Ces 8 dimensions ne seront *jamais* déterminées, et toutes les
sorties futures le sont quand même. C'est la brèche du théorème en vraie
grandeur : **il faut qu'une partie de l'état soit muette**, la factorisation
seule ne suffit pas.

### MT19937 : le raccourci existe, et il ne suffit pas

Contrôle du modèle : le MT19937 reconstruit par formes contre celui de CPython,
**800/800 mots identiques**. Puis élimination exacte sur les 19 937 inconnues,
en construisant les formes par la récurrence plutôt que par propagation de base.

| bits prédits | mot | tirages (borne inf.) | rang alors |
|---|---|---|---|
| 1 | **4 363** | 218,2 | 15 578 / 19 937 |
| 2 | **6 232** | 311,6 | < 19 937 |
| 3 | *jamais* | — | — |
| 4 (= rang plein) | 6 853 | 342,6 | 19 937 |

**Vérification de bout en bout**, parce qu'une appartenance est une affirmation
forte : on refait l'élimination en gardant trace des combinaisons, on extrait le
vecteur `c` tel que `c·A = ψ`, et on l'applique aux bits **observés** d'un vrai
MT19937. Résultat : **8/8 états aléatoires**, la forme cible prédite depuis
17 448 bits observés — alors que **4 359 dimensions de l'état restent
indéterminées**.

> **En deux temps, et le second annule le premier.** Le raccourci existe : un
> bit devient prédictible **2 490 mots (36 %) avant le rang plein**. Mais le §78
> en demande **trois** — deux ne portent le taux de retour qu'à 0,895, sous le
> seuil — et trois n'arrivent **jamais** avant le rang plein. Le raccourci est
> réel et sans effet. C'est exactement le genre de résultat qu'on ne peut pas
> deviner.

### La correction au §69, et une mise en garde sur l'unité

Les 80 équations d'un tirage **cessent d'être indépendantes au mot 2 493** —
exactement `4,00` blocs de 624, quand les brassages commencent à se recouvrir.
Jusque-là le rang croît de 4 par mot, sans une seule équation redondante.

| | §69 | §80 (mesuré) |
|---|---|---|
| MT19937, rang plein | 19 937/80 = **250** tirages | 6 853 mots = **343** tirages |

Soit **+37 %**. `LeakBudget.swift` et `verif_logique.py` sont corrigés.

**Et « au mieux ».** Le calcul suppose les quatre bits de *chaque mot
consécutif* connus. Sous rejet modulo 80 un tirage consomme ~22,85 mots dont 20
seulement sont identifiés (§74) ; sous Fisher-Yates la fuite tombe à 22 bits
(§71). Tous les chiffres en tirages sont des **bornes inférieures**, jamais des
promesses.

### Conséquence opérationnelle

| | |
|---|---|
| session (204 tirages, §65) | 16 320 équations |
| MT19937 exige | 19 937 inconnues, rang plein à 343 tirages |

- **Si le générateur se ré-amorce à chaque session**, MT19937 est hors
  d'atteinte — et le raccourci à un bit ne rattrape rien, puisqu'il en faudrait
  trois.
- **S'il traverse les coupures** — la question ouverte du §65 — il faut **343
  tirages ordonnés, soit 29 heures** de collecte à un tirage toutes les cinq
  minutes. C'est faisable, et c'est la seule mesure qui tranche.

**Registre : inchangé.** h60 démontre et calcule.

---

## 81. Les familles que la carte n'avait jamais nommées (`h61_familles_etendues.py`)

Les §68 à §80 ont bâti une attaque complète sur les générateurs F₂-linéaires et
l'ont appliquée à **cinq** familles. Ce sont les cinq que le §68 avait écrites le
premier jour, et personne n'a demandé si la liste était la bonne. Elle ne l'est
pas : les générateurs F₂-linéaires réellement déployés aujourd'hui sont les
**xoshiro/xoroshiro** de Blackman et Vigna (2018), le **LFSR113** de L'Ecuyer
(1999) et les **WELL** de Panneton, L'Ecuyer et Matsumoto (2006). Aucun n'avait
été testé.

### Le seuil de rang, mesuré famille par famille

Le §69 comptait `nbits / 80` ; le §80 a montré que ce compte est faux dès que
l'état est grand. On mesure donc, comme au §80, le mot où le rang atteint son
maximum — et ce maximum, qui n'est pas toujours `nbits` :

| famille | nominal | W(rang) | **rang réel** | origine |
|---|---|---|---|---|
| xorshift32 | 32 | 9 | 32 | Marsaglia 2003 |
| xorshift64 | 64 | 19 | 64 | Marsaglia 2003 |
| xorshift96 | 96 | 28 | 96 | Marsaglia 2003 |
| xorshift128 | 128 | 33 | 128 | Marsaglia 2003 |
| taus88 | 96 | 22 | **88** | L'Ecuyer 1996 |
| xoroshiro128 (brut) | 128 | 33 | 128 | **Blackman-Vigna 2018** |
| xoshiro128 (brut) | 128 | 33 | 128 | **Blackman-Vigna 2018** |
| xoshiro256 (brut) | 256 | 64 | 256 | **Blackman-Vigna 2018** |
| LFSR113 | 128 | 29 | **111** | **L'Ecuyer 1999** |
| WELL512a | 512 | 128 | 512 | **Panneton et al. 2006** |

### LFSR113 n'est pas identifiable par les bits bas — et c'est un résultat

Les quatre bits publiés par mot n'engendrent qu'un espace de **rang 111 sur
128** : il reste un noyau de **17 dimensions invisible modulo 16 mais visible
modulo 80**. Deux états du noyau donnent les mêmes quartets et des **numéros
différents** — le système linéaire ne les sépare pas, et il faudrait départager
131 072 états à chaque feuille.

> Ce n'est pas une limite de calcul mais une propriété de la famille : sous
> l'échantillonneur par modulo, l'observation ne suffit pas à l'identifier. Le
> §82 montre que les deux autres échantillonneurs ferment ce défaut.

C'est le témoin positif qui a trouvé cette structure : la première version de
l'attaque visait le rang **nominal**, jamais atteint, et échouait à 0/6 sur
LFSR113 et taus88. Un résultat nul sans témoin l'aurait fait passer pour une
conformité.

### Deux erreurs d'algorithme, trouvées par le témoin

1. **Pas de plafond global de rejets.** La première version plafonnait les
   rejets *par tirage* : l'arbre valait C(19,7)² ≈ 2·10⁹ feuilles et le témoin
   échouait à 0/3. Remplacé par un **approfondissement itératif** sur le nombre
   de rejets rencontrés *avant que le rang ne soit plein* — la seule quantité
   qui compte, puisque la recherche s'arrête là. Compter le total surestimait le
   coût et sous-estimait la couverture d'un facteur deux.
2. **Copie du dictionnaire de pivots à chaque nœud**, O(rang) par nœud. Or
   `add_eq` n'écrase jamais un pivot : un journal d'annulation suffit, et le
   nœud redevient O(1) amorti.

### Sur les cinq tirages ordonnés

| famille | essais | profondeur | **couverture** | état trouvé |
|---|---|---|---|---|
| xorshift32 | 5 | 8 | 100 % | 0 |
| xorshift64 | 5 | 8 | 100 % | 0 |
| xorshift96 | 1 | 6 | 94 % | 0 |
| xorshift128 | 1 | 4 | 64 % | 0 |
| taus88 | 1 | 5 | 91 % | 0 |
| xoroshiro128 | 1 | 4 | 64 % | 0 |
| xoshiro128 | 1 | 4 | 64 % | 0 |

**15 attaques, 0 état compatible, couverture minimale 64 %.** La vérification
est un rejeu exact : pas de faux positif possible. Mais la couverture n'est pas
100 %, et l'écrire est la seule façon honnête de présenter un résultat nul.

### Ce qui reste hors de portée, nommément

| | tirages ordonnés requis |
|---|---|
| xoshiro256 | 3,2 — il en manque un consécutif |
| WELL512a | 6,4 |
| MT19937 | 343 (§80) |
| xoshiro\*\* et ++, PCG, splitmix64, CSPRNG | hors du champ du §68 |

**Registre : `h61.familles_etendues`, 0 état compatible, conforme.**

---

## 81 bis. Réparation du registre : le champ `m_extra` (`lab/reparation_m_extra.py`)

Le registre compte sa multiplicité comme `m = nombre de lignes + Σ m_extra`.
Les entrées h56, h57, h59 et h61 déclaraient leur `m_extra` **dans le texte des
notes** mais pas dans le **champ**, que `lab.record` n'expose pas. Le registre
sous-comptait donc sa propre multiplicité — c'est-à-dire que son seuil de Holm
était **trop permissif**, exactement le défaut que le protocole existe pour
empêcher. Aucune conclusion n'en dépend (toutes ces entrées sont conformes très
au-dessus du seuil), mais il fallait le corriger et le dire.

De plus, `h61` avait été consigné **deux fois** : la série complète a été lancée
deux fois et le registre est en ajout seul. Même incident qu'au §60, même
réparation.

Le fichier rejoue la dernière ligne de chaque entrée en y ajoutant le champ,
puis appelle `lab.dedupe()`. Rien n'est effacé à la main ; l'incident reste
lisible dans l'historique. Les fichiers d'expérience portent désormais
`tok["m_extra"] = …` avant `lab.record`.

> **m du registre : 3 339 → 3 359. Zéro significatif. Plus petit p : 2,0·10⁻⁴.**

---

## 82. Le second échantillonneur, et il fuit plus que le premier (`h62_troncature.py`)

Tout le volet §68–§81 repose sur une seule ligne : `n = (out mod 80) + 1`. Le
§74 en tirait une conclusion rassurante — la fuite vaut `20 × v₂(vivier)`, donc
un vivier **impair** l'annulerait : « un opérateur qui aurait choisi 79 numéros
aurait fermé cette voie sans le savoir ».

Sauf que le modulo n'est **pas** la seule façon d'écrire un tirage, ni la plus
répandue. Il y en a trois, et le dossier n'avait testé que la première.

| | forme | qui l'écrit |
|---|---|---|
| **(A)** | `out % 80` | C, C++, PHP historique, tout code naïf |
| **(B)** | `floor(u × 80)`, `u = out/2^W` | JavaScript, Java `nextInt`, Python `random()*80` |
| **(C)** | 7 bits tirés, rejetés si ≥ 80 | Python `randrange`, Go, Rust |

### Le théorème de la troncature

Sous (B), `n − 1 = floor(out × 80 / 2^W)` équivaut à
`out ∈ [L_n, R_n]` avec `R_n − L_n + 1 = 2^W/80`. L'intervalle contraint les
bits de **poids fort** : tous ceux que `L_n` et `R_n` partagent sont
exactement déterminés. Leur espérance est une **somme finie sur les 80
intervalles** — pas une estimation.

Sous (C), les `k = 7` bits tirés **sont** le numéro : sept bits par mot accepté,
sans condition.

| vivier | v₂ | **(A) modulo** | **(B) troncature** | **(C) poids fort** |
|---|---|---|---|---|
| **79** | 0 | **0,000** | **4,481** | **7,000** |
| **80** | 4 | 4,000 | **5,200** | **7,000** |
| **81** | 0 | **0,000** | **4,519** | **7,000** |
| 127 | 0 | 0,000 | 5,055 | 7,000 |
| 128 | 7 | 7,000 | 7,000 | 8,000 |

### Trois conclusions du dossier tombent

**1. Le §74.** « Un vivier impair rendrait le théorème du §68 entièrement vide. »
Vrai de (A) **seulement**. Un vivier de 79 publie 0 bit sous (A), **4,48 sous
(B) et 7 sous (C)**. La protection par parité ne protège que du plus faible des
trois échantillonneurs. Et — contre-intuitivement — **(A) est le moins fuyant
des trois** sur le vivier réel : 4 bits contre 5,20 et 7. *Le volet §68–§81
attaquait l'échantillonneur le plus avare.*

**2. Le §71.** « Fisher-Yates divise la fuite par 3,6. » Encore un raisonnement
sur (A) :

| | bits par tirage | rapport à (A)+rejet |
|---|---|---|
| (A) rejet modulo | 80,0 | 1,00 |
| (A) Fisher-Yates | 22,0 | 0,28 |
| (B) rejet troncature | 104,0 | 1,30 |
| **(B) Fisher-Yates** | **89,7** | **1,12** |
| (C) rejet poids fort | 140,0 | 1,75 |
| (C) Fisher-Yates | 137,0 | 1,71 |

Sous (B), Fisher-Yates fuit **4,1 fois plus** que sous (A) — et *plus* que le
rejet modulo lui-même, parce que la troncature ne demande pas que le module soit
pair : elle publie `log₂(module)` bits quel qu'il soit. **Fisher-Yates n'est une
protection que contre (A).**

**3. Le §69.** L'échelle des paliers, mesurée par la méthode du §80 pour les
trois :

| famille | n | (A) mots | (B) mots | (C) mots |
|---|---|---|---|---|
| xorshift32 | 32 | 9 | 7 | 6 |
| xorshift64 | 64 | 19 | 14 | 10 |
| xorshift96 | 96 | 28 | 19 | 16 |
| xorshift128 | 128 | 33 | 25 | 23 |
| taus88 | 96 | 22 | 18 | 14 |
| **xoshiro256** | 256 | 64 | 49 | **37** |

Sous (B) il faut ~77 % des mots qu'exige (A), sous (C) ~57 %. **xoshiro256, que
le §81 déclarait hors de portée (3,2 tirages), en demande 1,9 sous (C)** : il
entre dans la portée.

### Sur les cinq tirages ordonnés

**56 attaques, 0 état compatible.** Sur les **13 combinaisons concluantes** :
couverture minimale 38 %, médiane **96 %**. Trois combinaisons sont marquées
**non concluantes** (couverture < 20 %) et ne comptent pas comme testées —
toutes relèvent de (C), qui rejette plus du tiers de ses mots et fait exploser
l'arbre. C'est un coût de calcul, pas une limite de l'attaque.

**Registre : `h62.troncature`, 0 état compatible, conforme. m = 3 415, zéro
significatif.**

### Ce que cela ne change pas

- **Le théorème de conversion (§78) est intact** : il dit ce qu'un bit vaut, pas
  d'où il vient. Mais son cas `r = 1` devient *plus accessible* — (B) et (C)
  publient 5,2 et 7 bits du premier mot au lieu de 4.
- **Le théorème d'appartenance (§80) est intact** : il porte sur la structure de
  `L`, pas sur l'observation.
- **Le résultat reste nul sur l'archive**, sous aucun des trois
  échantillonneurs, pour aucune famille joignable.

Reste ouvert : un quatrième idiome existe — le rejet sur un intervalle multiple
du vivier (Lemire 2019) — et il publie une information de forme différente.

---

## 83. Le théorème de la retenue, et le mur qu'il nomme (`h63_retenue.py`)

Le §69 range les familles **additives** — xorshift128+, xoroshiro128+ — à part,
avec cette phrase : « seul le bit 0 d'une somme est exactement linéaire, d'où 20
bits par tirage ». C'est vrai, et c'est une **borne inférieure** que personne
n'avait cherché à relever.

Ces familles ne sont pas un cas d'école : **xorshift128+ est le générateur de
`Math.random` dans V8** — Chrome, Node, Edge — donc statistiquement le plus
probable derrière un affichage de loterie en ligne. Le dossier ne savait pas
l'attaquer.

### Le théorème

Soit `out = a + b (mod 2^W)`, `a` et `b` linéaires sur F₂ en l'état. Avec `c_i`
la retenue **entrante** au rang `i` et `c_0 = 0` :

`out_i = a_i ⊕ b_i ⊕ c_i` et `c_{i+1} = maj(a_i, b_i, c_i)`

> **Lemme.** Si `a_i ≠ b_i` alors `maj(a_i, b_i, c_i) = c_i`.
> *Preuve.* L'un vaut 0, l'autre 1 ; la majorité de `{0, 1, c_i}` est `c_i`. ∎

> **Corollaire — le préfixe libre.** Posons `d_i = out_i ⊕ c_i = a_i ⊕ b_i`. Si
> `d_i = 1` la retenue reste **connue**, donc l'équation du rang `i+1` reste
> **linéaire**. Comme `c_0 = 0`, les bits `0..j` de `out` donnent `j+1`
> équations linéaires libres, où `j` est le nombre de 1 en tête des bits
> observés.

Espérance sur quatre bits observés :
`1·½ + 2·¼ + 3·⅛ + 4·⅛ = **1,875**` équation linéaire par mot au lieu de 1 —
**sans aucune supposition et sans le moindre branchement**.

| longueur du préfixe | observé | théorie |
|---|---|---|
| 1 | 0,5090 | 0,5000 |
| 2 | 0,2360 | 0,2500 |
| 3 | 0,1320 | 0,1250 |
| 4 | 0,1230 | 0,1250 |

Moyenne mesurée **1,869** contre 1,875. **3 738 équations vérifiées, zéro
fausse** : c'est une identité, pas une approximation.

### Ce que cela change à l'échelle du §69

| famille | n | §69 | **mesuré (§80)** | tirages | gain |
|---|---|---|---|---|---|
| xorshift128+ (V8) | 128 | 128 mots | **77** | 3,85 | ×1,66 |
| xoroshiro128+ | 128 | 128 mots | **78** | 3,90 | ×1,64 |

Le palier tombe de **7 tirages à 4**. Le §69 n'avait pas tort — il comptait ce
qui était *certain* — mais il laissait **47 % de la fuite sur la table**, faute
d'avoir regardé la retenue.

### Le témoin : l'algèbre, séparée de la combinatoire

L'attaque complète doit énumérer les positions des rejets ; le théorème, lui,
porte sur l'algèbre. On sépare donc : ce témoin **donne** les positions et ne
fait qu'éliminer.

| famille | tirages | mots utilisés | états retrouvés |
|---|---|---|---|
| xorshift128+ (V8) | 4 | 96 | **10/10** |
| xoroshiro128+ | 4 | 100 | **10/10** |

L'état sort par **élimination seule**, sans une seule supposition.

### Ce que le dossier peut en faire aujourd'hui : rien, et pourquoi

| | |
|---|---|
| tirages ordonnés | 5 (1381023, 1381026, 1381028, 1381030, 1381031) |
| plus longue suite consécutive | **2** |
| nécessaire | **4** |
| manquants | 2 |

Sous rejet, le théorème du trou (§72) ne chaîne pas : le nombre de mots
consommés par les tirages intermédiaires est inconnu. Il faut donc 4 tirages
**consécutifs**. Avec 2, on a ~75 équations pour 128 inconnues — le système est
**sous-déterminé**, et tout état compatible admettrait ~9·10¹⁵ solutions.

> **Registre : inchangé.** Consigner un test sous-déterminé comme « conforme »
> serait exactement le faux négatif que le protocole interdit. Ce qu'il faut
> collecter : **4 tirages ordonnés consécutifs, soit 20 minutes.**

### Ce que la retenue n'ouvre pas — et c'est le mur, désormais en une ligne

Le lemme part de `c_0 = 0` : il démarre au bit de **poids faible**, donc il sert
l'échantillonneur (A) du §82 et lui seul. Sous (B), la troncature, on observe
les bits de poids **fort** de la somme, où la retenue entrante vaut
`c_i = 1 ⟺ (a mod 2^i) + (b mod 2^i) ≥ 2^i` — une inégalité sur des bits que
rien n'a publiés. Le lemme ne démarre pas, et chaque équation coûte une
supposition : 2⁶⁸ branches sans élagage possible avant le rang plein.

> **Or c'est la combinaison la plus plausible du monde réel.** xorshift128+ est
> `Math.random` de V8, et le JavaScript idiomatique écrit
> `Math.floor(Math.random() * 80)` — soit exactement (B).
>
> **Le mur, en une ligne : sortie ADDITIVE + échantillonneur par TRONCATURE.**
> Ni le §68 (linéaire, modulo), ni le §82 (linéaire, troncature), ni le §83
> (additif, modulo) ne l'atteignent. Il faudrait un solveur algébrique — SAT ou
> base de Gröbner — là où le dossier n'a que de l'élimination de Gauss.

C'est la première fois que le dossier peut écrire son mur en une ligne au lieu
d'une liste.

---

## 84. Le seuil de solvabilité SMT : le mur du §83, mesuré (`h64_seuil_smt.py`)

Le §83 a réduit ce que le dossier n'atteint pas à une ligne : **sortie additive
+ échantillonneur par troncature** — `Math.random` de V8 avec
`Math.floor(Math.random() * 80)`. Il concluait : « il faudrait un solveur
algébrique là où le dossier n'a que de l'élimination de Gauss. » Ce fichier
prend le solveur au mot.

Il ne demande pas *« est-ce que ça marche »* — question binaire et peu
informative — mais **où est la falaise**. C'est la seule façon de transformer un
mur en distance.

> **Dépendance assumée.** `h64` est le seul fichier du labo à demander
> `z3-solver`. En son absence il l'annonce et s'arrête : il ne fabrique aucun
> résultat de remplacement.

### L'encodage compte, et beaucoup

| mots | encodage | bits donnés | résultat | sec |
|---|---|---|---|---|
| 22 | intervalle `L ≤ out ≤ R` | 132 | unknown | 180,0 |
| 22 | bits exacts (§82) | 119 | unknown | 180,0 |
| 40 | intervalle | 240 | unknown | 180,1 |
| 40 | bits exacts | 215 | unknown | 180,1 |
| 100 | intervalle | 600 | unknown | 180,3 |
| 100 | bits exacts | 528 | unknown | 190,9 |

**Aucun des deux ne passe, et ajouter des mots n'y change rien.** À 100 mots on
donne 600 bits d'information pour 128 inconnues — cinq fois de quoi déterminer
l'état — et le solveur cale quand même. **Le problème n'est pas
informationnel.**

### La falaise

À redondance **fixée** (384 bits = 3 × l'état), on fait varier le nombre de bits
publiés par mot :

| K bits/mot | mots | bits | résultat | sec |
|---|---|---|---|---|
| 64 | 6 | 384 | **sat EXACT** | 0,6 |
| 32 | 12 | 384 | **sat EXACT** | 0,3 |
| **16** | 24 | 384 | **sat EXACT** | **15,9** |
| **12** | 32 | 384 | unknown | 180,0 |
| 10 | 39 | 390 | unknown | 180,1 |
| 8 | 48 | 384 | unknown | 180,1 |
| 6 | 64 | 384 | unknown | 185,2 |

> **La falaise est entre 16 et 12 bits par mot**, et elle est étroite — moins
> d'un facteur deux. Elle ne dépend pas du nombre de mots : ce qui bloque est la
> **largeur** de chaque contrainte, pas leur nombre. Chaque mot publie un
> fragment trop court pour propager.

### Où tombe le cas réel

| cas | bits/mot | position |
|---|---|---|
| `Math.random` brut (52 bits) | 52,00 | **au-dessus** |
| troncature vers 4 096 | 12,00 | sous |
| troncature vers 256 | 8,00 | sous |
| **troncature vers 80 — le cas réel** | **5,20** | **sous** |
| modulo 80 (§68, mais là c'est linéaire) | 4,00 | sous |

> **Le mur tient, et il est chiffré : facteur 3,08.** Le §83 nommait le mur ;
> le §84 en donne la distance. Ce n'est pas « on n'a pas trouvé », c'est une
> mesure.

### Ce qui le franchirait, précisément

1. **Un vivier plus grand.** La fuite par troncature vaut ~`log₂(vivier)` bits :
   il faudrait **65 536 numéros** pour atteindre le seuil. Loto Express en a 80,
   et aucune loterie n'en a autant.
2. **Un solveur dédié** plutôt que généraliste — les attaques publiées sur
   `Math.random` utilisent les 52 bits complets d'un double, pas 5,2.
3. **Un générateur non additif** : le §82 traite ce cas, et il cède.

### Ce que cela ne fait pas

Un `unknown` n'est **pas** un `unsat` : le solveur n'a pas prouvé qu'il n'y a
pas de solution, il a manqué de temps. Ce fichier ne conclut donc **rien** sur
l'archive et ne consigne rien.

**Registre : inchangé.** h64 mesure une capacité, il ne teste pas le tirage.

---

## 85. La carte de décision, après §78–§84

Sept sections, un seul but : savoir **ce qui améliorerait réellement la
prédiction**. Voici la carte, en ordre de coût croissant.

### Ce qu'il faut, exactement

Le §78 l'a chiffré une fois pour toutes : **trois bits de poids faible d'un seul
mot** — celui qui produira le premier numéro du prochain tirage — portent le
taux de retour de **0,583 à 1,309**. Quatre bits le portent à **1,765**. Il ne
faut donc *pas* reproduire le générateur : il faut trois formes linéaires.

Et le cas `r = 1` **survit aux deux échantillonneurs** (§78, correction) : au pas
0, Fisher-Yates lit le tableau intact et tire modulo 80 comme le rejet.

### Les deux voies, et leur état

| voie | état | référence |
|---|---|---|
| **Statistique — biais stationnaire** | **close** : rentable à δ = 0,119, détectable à 0,049 | §79 |
| **Statistique — biais par session** | **close** : nouveau test de sur-dispersion, témoin 40/40 | §79 |
| **Générateur — F₂-linéaire, état ≤ 128 bits** | **testé, nul** sous les trois échantillonneurs | §81, §82 |
| **Générateur — LFSR113 sous modulo** | **non identifiable** : noyau de 17 dimensions | §81 |
| **Générateur — xoshiro256** | atteignable sous (C) : 1,9 tirage | §82 |
| **Générateur — MT19937** | **343 tirages ordonnés**, pas 250 ; aucun raccourci | §80 |
| **Générateur — additif sous modulo** | 4 tirages **consécutifs** ; le dossier en a 2 | §83 |
| **Générateur — additif sous troncature** | **le mur**, distance mesurée ×3,08 | §83, §84 |

### La seule action qui déplace quelque chose

Toutes les lignes « générateur » du tableau butent sur la même chose, et ce
n'est ni une idée ni une machine : ce sont des **tirages ordonnés consécutifs**.

| cible | consécutifs requis | temps de collecte |
|---|---|---|
| xorshift 32/64/96/128, taus88, xoshiro/xoroshiro128 | 1 à 2 | **déjà fait — nul** |
| xoshiro256 sous (C) | 2 | 10 min |
| **additif (Math.random de V8) sous modulo** | **4** | **20 min** |
| WELL512a | 7 | 35 min |
| **MT19937** | **343** | **29 heures** |

Le dossier en a **cinq, dont deux consécutifs**. `LeakBudget.swift` porte le
compteur depuis le §70 ; il affiche désormais les bons paliers (§80, §82).

> **Ce qu'il faut faire pour améliorer la prédiction n'est plus une question
> mathématique. C'est une collecte de vingt minutes pour la cible la plus
> plausible, et de vingt-neuf heures pour la plus coûteuse.**

### Et si tout cela est nul aussi

Alors il reste exactement une chose, et le §84 en donne la mesure : la
combinaison **additive + troncature**, à un facteur 3,08 de ce qu'un solveur SMT
généraliste sait digérer. Ce n'est pas une porte fermée, c'est une porte dont on
connaît l'épaisseur.

---

## 86. La chaîne Fisher-Yates complète, enfin assez longue (`h65_chaine_complete.py`)

Quatre tirages ordonnés **consécutifs** — 1381256 à 1381259 — ont été relevés à
l'écran et versés au dossier. Contrôles de transcription : 20 numéros distincts
dans 1..80 chacun, identifiants consécutifs, **tous en session 350**. Le dossier
en compte désormais **neuf**, dont une suite de quatre.

### Ce que ces quatre-là débloquent, et ce n'est pas ce que j'attendais

J'avais annoncé qu'ils permettraient d'attaquer les familles **additives** sous
rejet — `Math.random` de V8. C'est vrai informationnellement (80 numéros ×
1,875 = 150 équations pour 128 inconnues) mais **faux en pratique** : sous
rejet, les positions des ~11 mots rejetés sont inconnues, et l'entropie de ce
motif vaut ~2⁴² — un mur du même genre que celui du §77.

Ce qu'ils débloquent réellement est ailleurs, et c'est mieux : la chaîne
**Fisher-Yates**, où il n'y a **aucune recherche du tout**.

| | |
|---|---|
| Fisher-Yates publie (§71) | **22 bits par tirage** |
| 5 tirages (avant) | 110 bits — **< 128** |
| **9 tirages (maintenant)** | **198 bits — > 128** |

Sous Fisher-Yates il n'y a pas de rejet, chaque tirage consomme exactement vingt
mots, et les indices `j` du mélange se reconstruisent **exactement** depuis
l'ordre publié. Une famille = **une élimination de Gauss**, sans le moindre
branchement.

### Une occasion manquée du §52, corrigée

Le §52 se limitait à la plus longue suite **consécutive** — alors que son propre
théorème du trou (§72) l'en dispensait : l'état avance de vingt mots par tirage,
donc deux tirages séparés de `g` tirages le sont de `20g` mots, un nombre
**connu**. Toute la collecte se chaîne, consécutive ou non. Les écarts réels du
dossier sont `[0, 3, 5, 7, 8, 233, 234, 235, 236]`, et ils ne coûtent rien.

### L'hypothèse, déclarée et facturée

Chaîner les neuf suppose que le générateur n'a pas été **ré-amorcé** entre eux.
Or les cinq premiers sont en session 349 et les quatre nouveaux en session 350,
et le §65 n'a jamais tranché. Les trois attaques sont donc menées :

| chaîne | tirages | bits | ≥ 128 ? | hypothèse |
|---|---|---|---|---|
| **continu (les neuf)** | 9 | **198** | **oui** | continuité entre sessions |
| session 349 | 5 | 110 | non | aucune |
| session 350 | 4 | 88 | non | aucune |

**Seule la chaîne continue atteint 128 bits.** C'est le prix, et il est écrit.

### Deux bugs que le témoin a attrapés

Le témoin rejoue des chaînes synthétiques ayant **exactement les mêmes trous**
que le dossier. Il a trouvé deux choses :

1. **L'énumération du noyau était fausse** — et le §52 avait le même défaut.
   Flipper une variable libre sans corriger les composantes pivots ne donne pas
   un autre point de l'espace des solutions. Cela ne marchait que par accident,
   sur les familles dont les directions libres sont inertes (taus88). Corrigé
   par une vraie base du noyau : LFSR113 (22 dimensions) et xorshift128+ (17)
   passent alors de 0/2 à 4/4.
2. **La vérification était trop lente** : rejouer 237 tirages par candidat.
   Remplacée par un préfiltre à un seul tirage — 20 pas au lieu de 4 740.

| famille | n | rang | noyau | retrouvés |
|---|---|---|---|---|
| xorshift32 / 64 / 96 / 128 | 32–128 | plein | 0 | **4/4** |
| taus88 | 96 | 88 | 8 | **4/4** |
| LFSR113 | 128 | 106 | 22 | **4/4** |
| xoroshiro128, xoshiro128 | 128 | 128 | 0 | **4/4** |
| **xorshift128+ (V8)** | 128 | 116 | 12 | **4/4** |
| xoroshiro128+ | 128 | 109 | 19 | **4/4** |
| xoshiro256 | 256 | 198 | 58 | 0/4 — *sous-déterminé, il faut 11,6 tirages* |

### Sur les neuf tirages du dossier

**Chaîne continue, 198 bits :**

| famille | rang atteint | verdict |
|---|---|---|
| xorshift32 | 32 | **INCOHÉRENT — exclu** |
| xorshift64 | 63 | **INCOHÉRENT — exclu** |
| xorshift96 | 94 | **INCOHÉRENT — exclu** |
| xorshift128 | 128 | **INCOHÉRENT — exclu** |
| taus88 | 88 | **INCOHÉRENT — exclu** |
| LFSR113 | 106 | **INCOHÉRENT — exclu** |
| xoroshiro128 (brut) | 125 | **INCOHÉRENT — exclu** |
| xoshiro128 (brut) | 127 | **INCOHÉRENT — exclu** |
| **xorshift128+ (V8)** | 118 | 1 024 candidats du noyau, **aucun état** |
| xoroshiro128+ | 118 | 1 024 candidats, **aucun état** |
| xoshiro256 | — | budget insuffisant |

Session 349 seule exclut xorshift32/64/96 et taus88 ; session 350 seule exclut
xorshift32/64. **Total : 16 attaques, 0 état compatible.**

> Un système **incohérent** exclut la famille sans appel : il n'y a pas de marge
> d'erreur à discuter, pas de seuil, pas de p-valeur. Et c'est la **première
> fois** que `Math.random` de V8 est écarté sous un échantillonneur quelconque.

### Ce que cela ne dit pas

1. **Tout ceci suppose Fisher-Yates.** La branche « rejet modulo » est traitée
   séparément (§81, §82) et n'a pas le même budget.
2. **Tout ceci suppose l'ordre de lecture** — l'hypothèse silencieuse du §73.
   La grille affichée est lue ligne par ligne ; si l'affichage ne suivait pas
   l'ordre d'émission, tous les systèmes seraient incohérents *trivialement*, et
   le résultat ne vaudrait rien. C'est la faiblesse principale de ce paragraphe,
   et elle ne se lève qu'en confrontant l'ordre affiché à une autre source.
3. **xoshiro256 reste ouvert** : 11,6 tirages ordonnés sous Fisher-Yates, il en
   manque trois.

**Registre : `h65.chaine_fy_complete`, 0 état compatible, conforme. m = 3 431,
zéro significatif.**

> **Correction au §85.** La carte de décision annonçait « additif sous modulo :
> 4 tirages consécutifs, 20 minutes ». Les tirages sont là, mais la ligne était
> optimiste : sous *rejet* le motif des mots rejetés coûte 2⁴², et c'est la
> branche *Fisher-Yates* — que la carte ne mentionnait pas — qui a livré le
> résultat. La collecte demandée était la bonne ; la raison ne l'était pas.

---

## 87. Le plafond exact de chaque échantillonneur — et une sous-estimation trouvée (`h66_plafond.py`)

Trois sections du dossier donnent un nombre de bits publiés par mot : le §71
(Fisher-Yates, 22 par tirage), le §82 (troncature, 5,20) et le §68 (modulo, 4).
**Les trois comptent des bits.** Or une équation sur F₂ n'est pas un bit : c'est
une **forme**, un XOR quelconque de bits. Rien n'interdisait qu'une combinaison
de bits hauts soit déterminée alors qu'aucun ne l'est individuellement — et dans
ce cas tous les paliers du dossier seraient faux, dans le sens indulgent.

Personne n'avait fait la vérification. La voici.

### Le théorème du plafond

Une observation restreint le mot de sortie à un ensemble `S`. Une forme `φ` est
**déterminée** ssi elle est constante sur `S`, c'est-à-dire orthogonale à
`D(S) = ⟨x ⊕ y : x, y ∈ S⟩`. Le contenu F₂-linéaire vaut donc exactement
`w − dim D(S)`. Calculé **exhaustivement** sur les 65 536 valeurs d'un mot
réduit à 16 bits — une énumération, pas un raisonnement.

| échantillonneur | annoncé | **réel** | verdict |
|---|---|---|---|
| (A) modulo 80 | 4 (= v₂(80)) | **4** | exact |
| (C) 7 bits + rejet | 7 | **7** | exact |
| Fisher-Yates | 22 / tirage | **22** | exact |
| **(B) troncature** | **5,20** | **5,60** | **le §82 sous-comptait** |

### Le supplément, et sa loi

Les 16 numéros qui publient plus que leur préfixe commun sont **exactement** ceux
vérifiant

> **`n ≡ 2 (mod 5)`**, où 5 est la **partie impaire** du vivier (80 = 2⁴ × 5)

et ils en publient **deux de plus** chacun — 16 sur 80, soit **0,40 bit** en
moyenne. La loi est vérifiée exhaustivement, et le profil est **indépendant de la
largeur du mot** : identique de 11 à 24 bits, donc valable à 32 et 64.

Le mécanisme se voit sur trois bits : l'intervalle `[3,4] = {011, 100}` n'a
**aucun** bit de poids fort commun, et pourtant `x₀ ⊕ x₁` y vaut 0 des deux
côtés. Une forme déterminée sans qu'aucun bit ne le soit. C'est exactement ce
qu'un compte par bits manque.

> **Corollaire, et il est joli.** `80 = 2⁴ × 5`. La partie **2-adique** gouverne
> la fuite du modulo (§68, `v₂ = 4`) ; la partie **impaire** gouverne le
> supplément de la troncature. **Les deux facteurs du vivier fuient, chacun par
> son propre mécanisme** — et le §74, qui concluait qu'un vivier impair fermerait
> la voie, se trompait deux fois.

### Ce que la correction change

| | §82 | **§87** |
|---|---|---|
| troncature, vivier 80 | 5,20 | **5,60** |
| troncature, vivier 79 | 4,48 | **5,39** |
| par tirage, (B) rejet | 104 | **112** |
| **Fisher-Yates sous (B)** | 89,7 | **105,2** |
| palier 128 bits sous (B) | 25 mots | **26 mots** |

L'erreur allait dans le sens **indulgent** : le dossier créditait la troncature
de moins de fuite qu'elle n'en a, donc ses paliers étaient trop longs et ses
attaques laissaient de l'information sur la table. **Aucun résultat nul n'en est
invalidé** — un état compatible se vérifie par rejeu, jamais par un seuil — mais
les couvertures déclarées au §82 sont **pessimistes**, et ses attaques peuvent
être renforcées de 7,7 %.

`LeakBudget.swift` et `verif_logique.py` sont corrigés ; le verdict reste vert.

### Le corollaire de bilan : aucun branchement n'aide

Supposer `v` bits de `out` multiplie l'arbre par `2^v` et rend **au plus** `v`
équations — le théorème du plafond l'interdit d'en rendre davantage. Le nombre de
feuilles à explorer est donc inchangé : `2^v` fois plus de branches, chacune
`2^v` fois plus contrainte.

> C'est pourquoi le théorème de la retenue (§83) est un **vrai** gain — il ne
> suppose rien, il *constate* que la retenue est connue quand `aᵢ ≠ bᵢ` — et
> pourquoi aucune variante « avec suppositions » ne l'a jamais battu.

### La carte de couverture

Chaque case dit ce qu'une expérience a **réellement** fait, jamais ce qu'une
formule laisse espérer :

| famille | (A) rejet | (B) troncature | (C) bits hauts | Fisher-Yates |
|---|---|---|---|---|
| xorshift32 | nul 100 % | nul 100 % | nul 100 % | **exclu** |
| xorshift64 | nul 100 % | nul 100 % | nul 96 % | **exclu** |
| xorshift96 | nul 94 % | nul 98 % | non concl. | **exclu** |
| xorshift128 | nul 64 % | nul 91 % | non concl. | **exclu** |
| taus88 | nul 91 % | nul 91 % | non concl. | **exclu** |
| LFSR113 | non identifiable | jamais | jamais | **exclu** |
| xoroshiro128, xoshiro128 | nul 64 % | jamais | jamais | **exclu** |
| xoshiro256 | 4 tirages | 3 tirages | non concl. | 12 tirages |
| WELL512a | 7 tirages | 5 tirages | 4 tirages | 24 tirages |
| **xorshift128+ (V8)**, xoroshiro128+ | 2⁴² motifs | jamais | jamais | **exclu** |
| MT19937 | 343 tirages | hors budget | hors budget | 907 tirages |

**24 cases sur 52 portent un résultat nul vérifié ; 10 n'ont jamais été
ouvertes.**

La colonne **Fisher-Yates est la seule pleine**, et ce n'est pas un hasard :
c'est la seule sans recherche. Les trois autres portent le même handicap — le
motif des mots rejetés — et leurs couvertures s'en ressentent.

Les quatre cases « jamais » qui comptent sont les deux familles **additives** sous
troncature et sous bits hauts. Ce n'est pas un oubli : le théorème de la retenue
démarre à la retenue nulle, donc aux bits **bas**, et ces deux échantillonneurs
publient les bits **hauts**. Le §84 a mesuré ce que coûte d'y aller quand même.

---

## 88. Reconstituer l'état interne depuis le bonus — MT19937 enfin testé (`h67_reconstitution.py`)

Toutes les attaques du dossier reconstituent l'état depuis l'**ordre** de
sortie, et le dossier n'a que neuf tirages ordonnés. L'archive en compte
70 560, mais triée : l'ordre y est perdu.

Sauf pour une chose. Le §77 a établi que le bonus est **toujours** l'un des vingt
numéros tirés — vérifié 70 560 fois sur 70 560. Ce n'est donc pas un tirage
supplémentaire mais un **pointeur**. Et s'il désigne le **premier** numéro sorti,
chaque ligne de l'archive publie `out(20t) ≡ bonus_t − 1 (mod 80)`, car sous
Fisher-Yates le pas 0 lit le tableau intact `1..80`.

> **70 560 tirages × 4 bits = 282 240 équations** — quatorze fois ce que
> MT19937 demande.

### Ce que le §77 n'avait pas pu faire

Le §77 menait cette attaque **session par session** (204 tirages, 816 bits) et
s'arrêtait là : *« MT19937 demanderait 4 985 tirages ; informationnellement
disponible, mais son élimination porte sur 19 937 inconnues, ce que Python ne
fait pas en temps raisonnable. La limite est ici computationnelle, pas
informationnelle. »*

Le §80 a levé cette limite en construisant les formes de MT19937 par la
**récurrence** plutôt que par propagation de base. Ce fichier applique cette
machinerie à l'archive entière.

### Deux bugs, encore attrapés par le témoin

1. **L'artefact du mot 0.** Le mot 0 est `x[0]`, dont les 31 bits de poids
   faible n'entrent pas dans l'état de MT19937 : trois de ses quatre formes
   basses sont identiquement nulles, et une équation `0 = 1` criait
   « incohérent » pour un simple défaut de paramétrage. Corrigé en démarrant au
   tirage 1. Le §80 avait déjà rencontré ce piège.
2. **S'arrêter au rang plein.** Un système de rang plein n'est pas un succès :
   c'est une solution *unique*, qu'il reste à confronter aux équations suivantes
   puis à rejouer. La première version s'arrêtait là — et déclarait
   « rang plein » pour xoshiro256, qui est en réalité incohérent 150 équations
   plus loin.

### Le témoin, puis l'archive

| | résultat | rang | tirages | temps |
|---|---|---|---|---|
| **MT19937 synthétique** | **cohérent, rang plein + 400 équations** | **19 937 / 19 937** | 5 386 | 40 s |
| **MT19937, archive réelle** | **INCOHÉRENT** | 19 936 / 19 937 | 4 985 | 35 s |

| famille | n | tirages | rang | verdict |
|---|---|---|---|---|
| xorshift32 | 32 | 84 | 31 | **INCOHÉRENT** |
| xorshift64 | 64 | 108 | 62 | **INCOHÉRENT** |
| xorshift128 | 128 | 156 | 125 | **INCOHÉRENT** |
| xoshiro256 | 256 | 252 | 256 | **INCOHÉRENT** |
| WELL512a | 512 | 444 | 512 | **INCOHÉRENT** |

**Six familles exclues, MT19937 compris** — celle que le §77 avait laissée
ouverte faute de machine.

### Le prix, et il est lourd

Le résultat est **conjoint sur quatre facteurs** :

1. le bonus est le **premier** numéro sorti (§37 : indécidable sur l'archive
   triée seule) ;
2. l'échantillonnage est de type **Fisher-Yates** — 20 mots par tirage
   exactement ;
3. le générateur n'est **pas ré-amorcé** sur toute l'archive (§65 : non
   tranché) ;
4. la famille.

Et il faut dire ce qui suit sans le maquiller : **avec 282 240 équations, une
règle de bonus fausse produirait elle aussi l'incohérence.** Le test exclut donc
le **paquet**, pas la famille isolément. Sa valeur est réelle — il ferme d'un
coup une région entière de l'espace d'hypothèses — mais elle n'est pas celle
d'une exclusion de MT19937 tout court.

### La mesure qui lèverait l'hypothèse 1, et elle est minuscule

Les tirages ordonnés collectés jusqu'ici (les neuf du §86) ne montrent **pas** le
bonus. Or il suffirait de relever **un seul tirage ordonné où le bonus est
visible** pour comparer directement le bonus au premier numéro sorti, et
trancher la règle que le §37 déclarait indécidable.

> Une capture. Le §37 tombe, l'hypothèse 1 disparaît, et les 282 240 équations
> de l'archive deviennent exploitables avec **une hypothèse de moins**.

**Registre : `h67.reconstitution_bonus`, conforme. m = 3 475, zéro
significatif.**

---

## 89. La complexité linéaire du bonus : le premier test qui ne nomme aucune famille (`h68_complexite_lineaire.py`)

Les §68 à §88 attaquent **famille par famille**. C'est une énumération, et une
énumération est toujours incomplète — le §81 a montré que la liste d'origine
oubliait les générateurs qu'on déploie aujourd'hui. Il existe un test qui les
couvre **tous d'un coup**, et le dossier ne l'avait jamais fait.

### L'idée

Si le bonus est le premier numéro sorti et si le générateur avance d'un nombre
**fixe** de mots par tirage, alors le bit `j` de `bonus_t − 1` vaut

> `b_j(t) = φ_j(Mᵗ · x)` avec `M = L²⁰`

Pour un générateur F₂-linéaire **quelconque**, cette suite satisfait donc une
récurrence linéaire d'ordre au plus `n`, la taille de l'état — quel que soit le
détail de la famille. Et **Berlekamp-Massey** rend exactement cet ordre minimal :
la *complexité linéaire*.

| | complexité attendue |
|---|---|
| générateur F₂-linéaire d'état `n` | **≤ n** |
| suite réellement aléatoire | **≈ N/2** |

Avec N = 70 560 bonus, le seuil est à **35 280 bits**.

> Et si la complexité était basse, on aurait un **prédicteur** : Berlekamp-Massey
> ne détecte pas seulement, il **restitue** le registre à décalage qui engendre
> la suite — donc le bit suivant. C'est la reconstitution la plus directe qui
> soit.

### Contrôle, puis témoin

| source | longueur | attendu | trouvé |
|---|---|---|---|
| LFSR de degré 17 | 68 | 17 | **17** |
| LFSR de degré 61 | 244 | 61 | **61** |
| suite aléatoire | 20 000 | 10 000 | **10 000** |

**Témoin** — une archive engendrée par MT19937, bonus posé égal au premier
numéro, 48 000 tirages :

| bit | complexité | N/2 | verdict |
|---|---|---|---|
| 0 | **19 937** | 24 000 | linéaire détecté |
| 1 | **19 937** | 24 000 | linéaire détecté |
| 2 | **19 937** | 24 000 | linéaire détecté |
| 3 | **19 937** | 24 000 | linéaire détecté |

La complexité tombe sur **la taille exacte de l'état de MT19937**, sans qu'on
ait eu besoin de le nommer. *(Le mode essai avec 12 000 échantillons ne le
voyait pas, et c'était juste : Berlekamp-Massey exige 2L échantillons pour voir
une complexité L. Le critère du témoin a été corrigé pour ne pas déclarer
« détecté » sur un échantillon trop court.)*

### Sur l'archive

| bit | longueur | complexité | N/2 | écart |
|---|---|---|---|---|
| 0 | 70 560 | 35 279 | 35 280 | −1 |
| 1 | 70 560 | 35 281 | 35 280 | +1 |
| 2 | 70 560 | 35 281 | 35 280 | +1 |
| 3 | 70 560 | 35 281 | 35 280 | +1 |

**Aucune structure linéaire.** Les quatre suites sont indiscernables d'une suite
aléatoire, à un bit près.

### Ce que cela exclut — et c'est bien plus que le §88

Le §88 excluait six familles **nommées**. Celui-ci exclut d'un seul coup

> **toute famille F₂-linéaire dont l'état tient sous 35 280 bits**

nommée ou non, connue ou non, présente ou absente de la littérature. C'est la
différence entre une énumération et un théorème : Berlekamp-Massey ne demande
pas *quelle* est la famille, il demande si la suite est **linéaire**.

Et 35 280 bits, c'est **1,8 fois** l'état de MT19937, 69 fois celui de WELL512a,
276 fois celui de `Math.random`. Aucun générateur déployé n'en a autant.

*(Pour mémoire : le §77 déclarait MT19937 « computationnellement hors de
portée ». Berlekamp-Massey le traite en **0,2 seconde**.)*

### Ce que cela n'exclut pas

1. **Les trois hypothèses du §88 restent** — bonus = premier numéro sorti,
   nombre fixe de mots par tirage, absence de ré-amorçage. Si l'une tombe, la
   suite observée n'est pas `φ(Mᵗx)` et le test ne porte sur rien.
2. **Les générateurs non F₂-linéaires** : LCG, PCG, xoshiro\*\* et ++,
   splitmix64, les familles additives, tout CSPRNG. La complexité linéaire ne
   les vise pas.
3. Un état de plus de 35 280 bits — mais MT19937 est déjà le plus gros de la
   littérature courante.

**Registre : `h68.complexite_lineaire`, complexité minimale 35 279, conforme.
m = 3 479, zéro significatif.**

---

## 90. Le boost : la seconde donnée publiée, et ce qu'elle corrige au §88 (`h69_boost.py`)

Question posée simplement : *l'archive contient-elle le bonus et l'extra ?*
La réponse est plus intéressante que oui ou non.

| | présent | ce que c'est |
|---|---|---|
| **bonus** | 70 560 / 70 560 | un numéro, 1..80 |
| **boost** | 70 560 / 70 560 | un multiplicateur, ∈ {1, 2, 3, 4, 5, 10} |
| **extra** | **absent** | et il ne peut pas y être : l'EXTRA est une **option de mise à CHF 2** (§63), pas un tirage. Il n'y a rien à consigner. |

> **Le dossier a toujours eu deux données publiées par tirage, et n'en a
> exploité qu'une.**

### La loi du boost

| boost | fréquence | cumul | pourcentage rond ? | z |
|---|---|---|---|---|
| 1 | 0,51193 | 0,51193 | *incertain* | — |
| 2 | 0,23797 | **0,74990** | 0,7500 | **−0,06** |
| 3 | 0,15060 | **0,90050** | 0,9000 | **+0,44** |
| 4 | 0,04996 | **0,95045** | 0,9500 | **+0,55** |
| 5 | 0,02465 | **0,97510** | 0,9750 | **+0,17** |
| 10 | 0,02490 | 1,00000 | 1 | — |

Les quatre seuils **75 %, 90 %, 95 %, 97,5 %** tombent à moins de **0,6 σ** sur
70 560 tirages : ce sont des pourcentages ronds, pas le fruit du hasard. Le
premier vaut 0,51193 — et **un tirage à pile ou face est écarté à 6,3 σ**.
Restent compatibles 0,51 ; 0,512 ; 0,5125 ; 0,515.

Entropie : **1,879 bit par tirage**.

### Ce que le boost publie, en formes linéaires

Le boost contraint `out` à un **intervalle** — exactement la situation du §87,
dont la machinerie rend les formes déterminées. Et les bornes des intervalles de
`boost ≥ 2` sont **rondes, donc certaines** ; celle du boost 1 dépend du premier
seuil, incertain, et on s'en passe.

| boost | intervalle | largeur | bits déterminés |
|---|---|---|---|
| 2 | [0,512 ; 0,750) | 0,238 | 2 |
| 3 | [0,750 ; 0,900) | 0,150 | 2 |
| 4 | [0,900 ; 0,950) | 0,050 | 3 |
| 5 | [0,950 ; 0,975) | 0,025 | 4 |
| 10 | [0,975 ; 1,000) | 0,025 | 5 |

**1,151 bit par tirage, soit 81 215 équations exactes** sur l'archive — à
comparer aux 282 240 du bonus. Le boost ajoute **29 %**.

### Ce que cela corrige au §88

Le §88 suppose que le générateur avance de **vingt** mots par tirage. Or si le
boost sort du même flux, il en consomme au moins un de plus. **Le §88 figeait
donc un paramètre inconnu sans le dire.** L'attaque est reprise pour six
longueurs :

| famille | W=20 | W=21 | W=22 | W=23 | W=24 | W=25 |
|---|---|---|---|---|---|---|
| xorshift32 | incohérent | incohérent | incohérent | incohérent | incohérent | incohérent |
| xorshift64 | incohérent | incohérent | incohérent | incohérent | incohérent | incohérent |
| xorshift128 | incohérent | incohérent | incohérent | incohérent | incohérent | incohérent |
| xoshiro256 | incohérent | incohérent | incohérent | incohérent | incohérent | incohérent |

Le paramètre figé n'était pas le point faible — **mais il fallait le montrer
plutôt que l'espérer.**

### Et ce que cela ne corrige pas au §89 : une hypothèse plus faible qu'annoncé

La suite du bonus vaut `φ(Mᵗx)` avec `M = Lᵂ`. **`M` est linéaire pour tout `W`
fixe** : Berlekamp-Massey voit donc la linéarité quelle que soit la longueur du
tirage. Vérifié sur un MT19937 synthétique :

| W | 20 | 21 | 23 | 25 |
|---|---|---|---|---|
| complexité | **19 937** | **19 937** | **19 937** | **19 937** |

> Le §89 ne suppose donc que **« un nombre fixe de mots par tirage »**, et non
> « vingt ». C'est une hypothèse nettement plus faible que celle que j'avais
> écrite — le résultat du §89 est plus fort qu'annoncé.

*(Un bug d'alignement de colonne affichait initialement des z de −146 : chaque
cumul était comparé au seuil du boost suivant. Corrigé.)*

**Registre : `h69.boost_seconde_donnee`, conforme. m = 3 527, zéro
significatif.**

---

## 91. La portée réelle du §89 : deux classes, pas une (`h70_portee.py`)

Le §89 concluait : *« toute famille F₂-linéaire dont l'état tient sous 35 280
bits est exclue »*. C'est vrai, et **c'est trop modeste**. Berlekamp-Massey ne
mesure pas la F₂-linéarité : il mesure la **complexité linéaire**. Or il existe
une seconde façon, entièrement différente, d'avoir une complexité basse.

### Le lemme

> Une suite **éventuellement périodique** de période `P` et de pré-période `t₀` a
> une complexité linéaire au plus `P + t₀`.
>
> *Preuve.* La suite vérifie `s(t+P) = s(t)` pour `t ≥ t₀`, donc le polynôme
> `(x^P − 1)·x^{t₀}` l'annule. Le polynôme minimal annulateur le divise. ∎

| période imposée | 7 | 64 | 500 | 3 000 |
|---|---|---|---|---|
| complexité mesurée | 7 | 63 | 500 | 2 998 |

### La classe que le §89 couvrait sans le dire

Un générateur **arithmétique** n'est pas F₂-linéaire. Mais si sa transition est
un **polynôme à coefficients entiers modulo 2^k**, elle descend modulo `2^j` :
les bits bas sont **fermés**, la suite observée est périodique, et le lemme la
rend visible.

Un tirage tous les 20 mots, sortie brute, 40 000 tirages :

| générateur | bit | période | complexité | N/2 | |
|---|---|---|---|---|---|
| LCG mod 2⁶⁴ | 0 / 3 | 1 / 4 | **1 / 3** | 20 000 | **vu** |
| LCG mod 2⁴⁸ (java brut) | 0 / 3 | 1 / 4 | **0 / 3** | 20 000 | **vu** |
| congruentiel quadratique | 0 / 3 | 1 / 1 | **1 / 0** | 20 000 | **vu** |
| **MWC 32 bits (Marsaglia)** | 0 / 3 | > 4 000 | **20 000** | 20 000 | *non vu* |

Berlekamp-Massey ne rate pas les congruentiels d'un cheveu : il les rate de
**quatre ordres de grandeur**.

> **MWC échappe, et c'est instructif.** Sa transition n'est pas un polynôme
> modulo 2^k : la retenue `c' = (a·x + c) div 2³²` est une quantité de la partie
> **haute**. La réduction modulo `2^j` n'est pas bien définie, les bits bas ne
> sont pas fermés. J'avais écrit « toute la famille arithmétique » — c'était trop
> large, et c'est le calcul qui l'a corrigé.

**Le §89 couvre donc deux classes :**

1. les générateurs **F₂-linéaires** d'état ≤ 35 280 bits ;
2. les générateurs à **transition polynomiale modulo 2^k et sortie brute** —
   congruentiels linéaires et quadratiques, c'est-à-dire *l'implémentation naïve
   par excellence*.

### Où la portée s'arrête, exactement

| générateur | complexité | N/2 | |
|---|---|---|---|
| `java.util.Random` (out = s ≫ 17) | 20 000 | 20 000 | **aveugle** |
| PCG32 (sortie brouillée) | 20 001 | 20 000 | **aveugle** |
| LCG brut + échantillonneur (B) | 20 000 | 20 000 | **aveugle** |

> **La frontière n'est pas celle de la famille, c'est celle de l'observation.**
> Un LCG est vu s'il sort brut, invisible s'il sort décalé — même générateur,
> même état. Ce qui compte est de savoir si `out mod 16` ne dépend que des bits
> fermés.

### Ce qui reste hors de portée, et pour deux raisons distinctes

**a) L'observation prend les bits hauts** — sorties décalées
(`java.util.Random`), sorties brouillées (PCG, xoshiro\*\*/++, splitmix64),
échantillonneur par troncature (§82). L'état peut être parfaitement fermé : on
n'en voit pas la partie fermée. *C'est exactement le mur nommé au §83 et mesuré
au §84.*

**b) La transition ne descend pas modulo 2^j** — les générateurs **à retenue**
(MWC, AWC, SWB de Marsaglia). Même à sortie brute, rien n'est fermé. *C'est une
case que le dossier n'avait jamais ouverte, et le §91 la nomme pour la première
fois.*

**Registre : inchangé.** h70 établit la portée d'un test déjà consigné.

## 92. La roue du boost : sept secteurs égaux, une loi qui ne l'est pas (`h71_roue.py`)

Deux enregistrements d'écran de `jeux.loro.ch`, tirage **1381278**, 2026-08-31
à 13:05 et 13:07. Le premier filme la **roue du boost**, le second l'affichage
du tirage puis la boule EXTRA.

| ce que la vidéo publie | |
|---|---|
| les 20 numéros | 4 7 8 12 15 17 22 25 28 36 45 47 52 54 56 60 62 69 74 75 — **affichés triés** |
| le boost | **×1,5** |
| le bonus | **45**, présent dans la grille (conforme au §77) |

Relevé dans `lab/observations_ecran.csv`. Ce fichier est **distinct** de
`draws_ordered.csv` : celui-là ne porte que des tirages dont l'ordre de sortie
est visible, et lui seul alimente les §68 à §86.

### La roue, mesurée

Le cercle est ajusté par moindres carrés sur les pixels colorés de la couronne
(résidu radial 2,0 px sur un rayon de 241) ; la teinte est échantillonnée tous
les 0,25° sur une bande radiale extérieure aux étiquettes ; une frontière est le
milieu d'une transition de teinte. L'aiguille est à 0°, le sens est horaire.

| début | fin | largeur | écart à 360/7 | multiplicateur | couleur |
|---|---|---|---|---|---|
| 320,62 | 12,38 | 51,75 | +0,32 | **×1,5** | jaune vif |
| 12,38 | 64,12 | 51,75 | +0,32 | ×3 | rouge |
| 64,12 | 116,12 | 52,00 | +0,57 | ×5 | jaune pâle |
| 116,12 | 167,62 | 51,50 | +0,07 | ×2 | orange |
| 167,62 | 219,12 | 51,50 | +0,07 | ×4 | rouge |
| 219,12 | 269,38 | 50,25 | −1,18 | ×1 | ambre |
| 269,38 | 320,62 | 51,25 | −0,18 | ×10 | vermillon |

Moyenne **51,4286°**, et 360/7 = **51,4286°**. Écart maximal 1,18°, soit **2,3 %**
d'une largeur de secteur. **Les sept secteurs sont égaux.** L'ordre angulaire,
dans le sens horaire, est

> **×1 ×10 ×1,5 ×3 ×5 ×2 ×4**

lu sur les étiquettes de deux images de rotations différentes (×1 en haut,
puis ×1,5 en haut), qui donnent le même ordre cyclique. L'aiguille tombe dans le
secteur ×1,5 — et l'écran affiche BOOST ×1,5 : la mesure et l'affichage se
recoupent.

### Le théorème de la roue

> **Théorème.** Soit une roue à *n* secteurs de même largeur et Θ l'angle où elle
> s'arrête. Si Θ est la variable aléatoire publiée et qu'elle est uniforme sur le
> cercle, le secteur désigné est uniforme sur les *n* secteurs.
>
> *Preuve.* Le secteur est `k = ⌊nΘ/2π⌋` ; l'image d'une uniforme par une
> partition en parts égales est uniforme. ∎

C'est la **réciproque** qui sert. L'archive ne connaît que six valeurs de boost —
`{1, 2, 3, 4, 5, 10}` — et le ×1,5 n'y est pas : il est donc fondu dans un seau,
soit **tronqué vers 1** (cas A), soit **arrondi vers 2** (cas B). On teste les deux.

| boost | observé | fréquence | uniforme, cas A | cas B |
|---|---|---|---|---|
| 1 | 36 122 | 0,51193 | 20 160 | 10 080 |
| 2 | 16 791 | 0,23797 | 10 080 | 20 160 |
| 3 | 10 626 | 0,15060 | 10 080 | 10 080 |
| 4 | 3 525 | 0,04996 | 10 080 | 10 080 |
| 5 | 1 739 | 0,02465 | 10 080 | 10 080 |
| 10 | 1 757 | 0,02490 | 10 080 | 10 080 |

**cas A : χ² = 35 173. cas B : χ² = 85 910.** Pour 5 degrés de liberté, dont la
moyenne vaut 5 et le seuil de 5 % 11,07.

> **L'angle d'arrêt n'est pas la variable publiée. Le résultat est tiré
> d'abord, d'une loi pondérée, et l'angle est calculé à partir de lui.**

Ce rejet **n'est pas consigné**, et délibérément : « la roue est uniforme » n'est
défendu par personne. Le consigner gonflerait *m* d'un homme de paille. C'est de
l'arithmétique, pas une découverte statistique.

**Ce que la pondération coûte.** La roue uniforme publierait log₂7 = 2,8074 bits
par tirage. Les six seaux en publient 1,8790 ; la vraie loi à sept valeurs, entre
1,8790 et 2,3909 (l'écart est la part du seau fondu, au plus un bit). **La
pondération coûte entre 0,42 et 0,93 bit par tirage** à qui veut reconstituer
l'état.

### Ce que le septième secteur corrige au §90

**Premier point — le seuil « incertain » est expliqué.** Le §90 relevait cinq
seuils cumulés : 0,51193 puis 0,74990, 0,90050, 0,95045, 0,97510. Les quatre
derniers sont ronds à moins de 0,6 σ ; le premier ne l'est pas, et ½ y est écarté
à 6,3 σ. La réponse n'était pas dans le générateur, elle était dans le **format** :
le premier seau de l'archive est **l'union de deux secteurs de la roue**, et une
somme de deux probabilités n'a aucune raison d'être ronde. *Le §90 cherchait une
structure là où il y avait un défaut de format.*

**Deuxième point — le §90 ne perd rien.** Sous l'hypothèse que l'échelle de
seuils suit l'ordre des multiplicateurs, le seau ×1,5 est adjacent au seau fondu
dans les deux cas, et le seau « 2 » reste l'intervalle [0,51193 ; 0,750) que le
§90 utilisait. **Sa table de formes linéaires — 1,151 bit par tirage, 81 215
équations — est intacte.**

**Troisième point — une hypothèse du §90 que la roue rend visible.** Cette table
suppose que chaque seau est *un seul* intervalle, donc que l'échelle suit l'ordre
des multiplicateurs. Or l'ordre **angulaire** mesuré plus haut ne le suit pas.
Rien n'oblige l'échelle à le suivre non plus. Si elle suivait l'ordre angulaire,
chaque seau resterait un intervalle sauf le seau fondu — justement celui dont le
§90 se passe. *La table tient dans les deux lectures ; mais l'hypothèse existait
sans être écrite, et elle l'est maintenant.*

**Quatrième point — cas A ou cas B ? La donnée ne tranche pas.** L'espérance du
multiplicateur, calculée sur les seaux, vaut **2,0117 ± 0,0062** : 2 est à
+1,90 σ. Si le jeu visait « le boost double en moyenne », le cas A la pousse
au-dessus de 2, tandis que le cas B la ramène à 2 pour P(×1,5) = 0,0234 ± 0,0123.
C'est compatible, ce n'est pas une preuve. L'API publique du jeu trancherait en
une requête ; le réseau de cet environnement la refuse (403 à l'établissement du
tunnel). *Limite de l'environnement, pas du raisonnement.*

### La loi du boost est-elle stationnaire ? (le test consigné)

L'archive s'arrête le 2026-08-25, la vidéo est du 2026-08-31. **Si le ×1,5 avait
été ajouté pendant la période couverte, la fréquence d'un seau aurait sauté à
cette date.** On balaie donc toutes les ruptures : χ² d'homogénéité à deux
échantillons entre préfixe et suffixe, **maximisé sur les 3 329 points de coupe**.
Le maximum absorbe le balayage ; le null le recalcule à l'identique sur des
permutations, donc la multiplicité est traitée exactement.

| | |
|---|---|
| observé | χ² = **15,74** à la coupe 34 320 (tirage 1343934) |
| null, 400 permutations | moyenne 13,02, écart-type 3,89 |
| seuil 5 % | 20,52 |
| **p** | **0,2095** |

**Témoin positif** — on fabrique la rupture cherchée : à mi-archive, une fraction
de la masse du seau 1 bascule vers le seau 2, exactement ce que ferait
l'apparition d'un septième secteur ré-encodé.

| bascule sur la 2ᵉ moitié | 0,20 pt | 0,40 pt | 0,60 pt | 1,00 pt |
|---|---|---|---|---|
| détections | 0/20 | **20/20** | **20/20** | **20/20** |

> **Le test voit 0,4 point de pourcentage à tous les coups. Il n'en voit aucun.**

Donc : ou bien le ×1,5 existait sur toute l'archive, et un seau est bien une
union — ou bien il a été ajouté dans les **six jours** entre la fin de l'archive
et la vidéo. La fenêtre est étroite, et elle est nommée.

### L'angle résiduel : la seule chose que cette section ouvre

La roue s'est arrêtée à **0,761** de la largeur de son secteur, pas au milieu —
soit 13,4° du centre, **onze fois** la plus grande erreur que la mesure des sept
largeurs ait laissée voir (1,18°). Deux lectures, et elles ne coûtent pas la même
chose :

| | |
|---|---|
| **décalage constant** | l'animation vise toujours le même point du secteur. La roue ne publie rien de plus que le boost. |
| **décalage tiré** | l'animation vise un point tiré au sort. La roue publie le boost **et** une variable continue. |

Un seul tirage filmé ne tranche pas. Mais il écarte déjà le cas le plus simple —
« la roue s'arrête au centre ».

**Et si le décalage est tiré, il est de la meilleure espèce.** Un décalage écrit
`random() × largeur` publie les bits de **poids fort** du mot brut : c'est
exactement l'échantillonneur du §87 dont le plafond exact vaut **7,00 bits par
mot** — le plus fuyant des trois, là où le modulo du §68 en publie 4,00 et la
troncature 5,60.

| précision de lecture | entropie angulaire | + le boost |
|---|---|---|
| 2° | 4,68 | 6,56 |
| 1° | 5,68 | 7,56 |
| 0,25° | 7,68 | 9,56 |
| 0,1° | 9,01 | **10,89** |

Le dossier n'est **pas** limité par l'archive : elle porte 70 560 tirages, le §88
les a tous consommés et n'a rien trouvé. Il est limité par ce qu'on peut
**filmer** — neuf tirages ordonnés au §86, et c'est tout. L'angle est une donnée
qui ne s'archive pas : elle se filme.

| ce qu'on filme | bits/tirage | nature | tirages | jours |
|---|---|---|---|---|
| le boost seul | 1,151 | formes exactes (§90) | 17 321 | 60,1 |
| le boost seul | 1,879 | entropie, majorant | 10 610 | 36,8 |
| le boost + angle lu à 1° | 7,564 | entropie, majorant | 2 636 | 9,2 |
| le boost + angle lu à 0,1° | 10,885 | entropie, majorant | 1 832 | 6,4 |

L'entropie **majore** le nombre de formes sans l'égaler — le §90 mesure le
rapport réel pour le boost : 1,151 forme pour 1,879 bit, soit 61 %. Les jours
sont donc un **plancher**, pas une promesse ; mais le **rapport** de 5,8 entre la
première ligne et la dernière ne dépend pas de ce taux de conversion.

> **Ce qu'il faut pour le savoir, et c'est petit : filmer vingt arrêts de roue et
> mesurer la fraction dans le secteur.** Si les vingt valeurs se serrent sur une
> constante, la roue ne publie rien de plus et la section se ferme. Si elles se
> répartissent sur [0, 1), la roue publie les bits de poids fort du générateur —
> et c'est la meilleure observation que le dossier ait jamais eue.

### Ce que cela ne fait pas

**Le §37 n'est pas tranché, et c'est la déception de ces vidéos.** Le bonus 45 est
bien visible, mais la grille du même tirage est **triée** : on ne peut donc pas
comparer le bonus au *premier numéro sorti*. Les neuf tirages ordonnés du §86
n'ont pas de bonus ; ce tirage-ci a un bonus et pas d'ordre. **Il manque toujours
la conjonction.**

> **Ce qu'il faut, exactement : un enregistrement d'un SEUL tirage montrant la
> grille se remplir boule après boule, puis la boule EXTRA du même tirage.** Pas
> deux tirages, pas deux écrans : un seul, continu.

**La roue ne prédit rien.** Elle publie un multiplicateur de gain, pas un numéro.
Son intérêt est entier dans l'angle résiduel — des **bits**, si le décalage est
tiré.

**Registre.** `h71_roue.py` porte la consignation de `h71.stationnarite_boost`
(voie A, `m_extra = 0`, le maximum absorbant le balayage). **Elle n'a pas encore
été exécutée dans cet environnement** : l'exécution de Python y a été bloquée
après l'écriture du fichier. Les valeurs ci-dessus proviennent d'un calcul
identique mené avant le blocage (400 permutations, graine 20260831). Le registre
reste donc à *m* = 3 488 (deux doublons de re-passe retirés par `lab.dedupe()`),
**zéro significatif**, plus petit p = 2,0 · 10⁻⁴.

## 93. Le théorème du convertisseur : ce qu'une fuite doit valoir, en francs (`h72_convertisseur.py`)

Le dossier a deux moitiés qui ne se parlent pas.

| | ce que ça produit |
|---|---|
| **§68 à §92** — reconstituer l'état | une loi a posteriori sur le **prochain tirage entier** : des tirages candidats, avec des poids |
| **§78 et toute l'app** — choisir une grille | une décision prise sur des **marginales** : une probabilité par numéro |

Personne n'a jamais démontré que la droite sait recevoir ce que la gauche
produit. **Elle ne sait pas.** Et le barème réel dit pourquoi, exactement.

### Théorème de linéarisation

> **Théorème.** Soit `D` le tirage (un 20-sous-ensemble aléatoire de [80]), `G` une
> grille de `k` numéros, `h = |G ∩ D|`, et `g` le barème. Posons
> `π(S) = P(S ⊆ D)`. Alors
>
> ```
> E[g(h)] = Σ_j  Δ^j g(0) · Σ_{S ⊆ G, |S| = j}  π(S)
> ```
>
> *Preuve.* Tout `g` sur `{0..k}` s'écrit de façon unique dans la base de Newton
> `g(h) = Σ_j Δ^j g(0)·C(h,j)` — interpolation exacte sur `k+1` points. Or
> `C(h,j)` **compte** les `j`-sous-ensembles de `G` contenus dans `D`, donc
> `C(h,j) = Σ_{S ⊆ G, |S|=j} 1[S ⊆ D]` ; l'espérance d'une indicatrice est `π(S)`,
> et la somme finie s'échange avec l'espérance. ∎

L'identité est **exacte** : aucune indépendance, aucune approximation, aucune
hypothèse sur la loi. Le gain espéré n'est pas une fonction quelconque de la
loi — c'est une **forme linéaire sur les probabilités d'inclusion**, et ses
coefficients se lisent dans le barème.

### Le barème réel ignore les marginales

Décomposition du relevé du 2026-08-30 (BOOST ×1, gain de base) — chaque ligne
vérifiée à la main par reconstruction `Σ_j c_j C(h,j) = g(h)` :

| mise | c₀ | c₁ | c₂ | c₃ | c₄ | c₅ | c₆ | c₇ | c₈ | c₉ | c₁₀ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 0 | 0 | 0 | **+6** | +12 | +240 | | | | | |
| 6 | 0 | 0 | 0 | **+4** | −4 | +40 | +740 | | | | |
| 7 | 0 | 0 | 0 | **+3** | −7 | +30 | +65 | +1 055 | | | |
| 8 | 0 | 0 | 0 | 0 | **+5** | −5 | +35 | +685 | +3 470 | | |
| 10 | +2 | −2 | +2 | −2 | +5 | −12 | +27 | +28 | −88 | +3 510 | **+61 972** |

> **Aux mises 5, 6 et 7, les coefficients d'ordre 0, 1 et 2 sont nuls ; à la
> mise 8, les ordres 0 à 3 le sont.**

Le gain espéré ne dépend donc **que** des inclusions d'ordre ≥ 3 (≥ 4 à la
mise 8). Ce n'est pas « les marginales comptent peu » : **elles n'apparaissent
pas dans la formule**. Un prédicteur qui publie une probabilité par numéro —
chauds, froids, retards, essaim, réseau de neurones — ne fournit pas les
arguments que `E[g]` prend. Ce n'est pas un prédicteur faible : c'est un
prédicteur dont la sortie n'est pas du bon type.

*Ce qui sauve le §78* : il travaille sur des **classes résiduelles**, et sa loi a
posteriori est échangeable dans chaque classe. Sous échangeabilité, `π(S)` ne
dépend que du profil de `S` par classe et le tri par comptes décroissants
redevient optimal. Le §78 est un **cas particulier correct** — pas une règle
générale.

### Théorème de domination

> **Théorème.** Il existe une loi a posteriori et deux grilles de **mêmes
> marginales** dont les gains espérés sont dans un rapport de 60.
>
> *Preuve par construction.* `D` uniforme sur deux tirages : `D₁ = {1..20}` et
> `D₂ = {21..40}`, chacun avec probabilité ½. Toutes les marginales valent ½
> sur 1..40. À la mise 5, prenons `G₁ = {1,2,3,4,5} ⊂ D₁` et
> `G₂ = {1,2,3,21,22}`, de même somme de marginales 2,5.
>
> `E[g(G₁)] = ½·g(5) + ½·g(0) = ½·360 = 180`
> `E[g(G₂)] = ½·g(3) + ½·g(2) = ½·6 = 3`
>
> Rapport **60**, à marginales identiques. ∎

Et ce n'est pas un contre-exemple artificiel : **une loi issue d'une
reconstitution d'état est exactement de cette forme** — quelques tirages
candidats entiers, avec des poids. Elle ne ressemble jamais à un nuage de
numéros indépendants légèrement penchés. *Le convertisseur de l'application est
conçu pour une entrée que la moitié gauche du dossier ne produit pas.*

**Contrôle.** Sous H₀, `π(S)` ne dépend que de `|S|`, donc le théorème de
linéarisation rend le même `E[g]` pour toutes les grilles de même taille : le
théorème d'invariance du §1 retombe comme corollaire. `h72` le vérifie en
arithmétique exacte (fractions), les deux voies devant coïncider au dernier
chiffre.

### Le convertisseur correct : le théorème de la min-entropie

Une reconstitution partielle produit `P = Σ_m w_m δ_{D_m}`. Posons
`H = −log₂(max_m w_m)`, la **min-entropie du prochain tirage**.

> **Théorème.** Soit `m*` le candidat le plus lourd et `G` n'importe quelle
> grille de `k` numéros **incluse dans `D_{m*}`**. Alors
>
> ```
> E[g(h)]  ≥  w_{m*}·g_k(k)  =  g_k(k)·2^(−H)
> ```
>
> et le pari à la mise `k` est favorable dès que
>
> ```
> H  <  log₂( g_k(k) / prix du ticket ).
> ```
>
> *Preuve.* `E[g(h)] = Σ_m w_m g(|G ∩ D_m|) ≥ w_{m*}·g(k)`, tous les termes étant
> ≥ 0 et le terme `m*` valant `g(k)` puisque `G ⊆ D_{m*}`. ∎

Deux remarques qui comptent. **(1) C'est suffisant, pas nécessaire** : on jette
tous les rangs intermédiaires et tous les autres candidats, donc le vrai seuil
est plus bas — même argument que le §29 sur le jackpot. **(2) La grille optimale
exacte** est `argmax_G Σ_m w_m g(|G ∩ D_m|)`, une couverture pondérée sur `M`
candidats : calculable exactement dès que `M` est énumérable — et `M` énumérable
est précisément le régime que le théorème vise.

### Le chiffre que le dossier cherchait depuis le §68

Un tirage complet pèse `log₂ C(80,20) = 61,62 bits`. Ticket à CHF 2 :

| mise | rang plein fixe | + cagnotte BANGO | **H max** | **bits à retirer** |
|---|---|---|---|---|
| 5 | 360 | 605 | 8,24 | 53,4 |
| 6 | 1 000 | 4 035 | 10,98 | 50,6 |
| 7 | 2 000 | 5 838 | 11,51 | 50,1 |
| 8 | 10 000 | 23 051 | 13,49 | 48,1 |
| **10** | 100 000 | **598 218** | **18,19** | **43,4** |

*(cagnottes du relevé 2026-08-30 22:16, supposées s'ajouter au rang plein fixe ;
si elles le remplacent, le seuil baisse de moins de 0,3 bit.)*

> **Le prochain tirage pèse 61,6 bits. Il faut le ramener sous 18,2. Il faut
> donc en retirer 43,4 — et pas un de plus.**

Ce n'est pas « casser le générateur ». C'est **réduire le prochain tirage à au
plus 2¹⁸ candidats énumérables**.

### Ce que cela change aux §80, §88 et §92

Si le système linéaire laisse un espace de solutions de dimension `d` sur F₂, le
prochain tirage a au plus `2^d` candidats, donc `H ≤ d`. La condition devient une
condition sur le **rang** :

```
rang ≥ n − 18        au lieu de        rang = n.
```

Pour MT19937 (`n = 19 937`), cela demande 19 919 au lieu de 19 937. **L'économie
est réelle mais petite, et il faut le dire** : le §80 montre que le rang sature
brutalement, donc les derniers bits ne coûtent presque rien.

**La vraie portée est ailleurs : le critère d'arrêt cesse d'être binaire.** Le
§88 s'arrêtait à « rang plein ou rien ». Il peut désormais s'arrêter à « 2¹⁸
candidats », les énumérer, et **jouer** — sans jamais identifier l'état. C'est un
critère opérationnel, pas algébrique. Et `H` peut être **plus petit** que `d` :
deux états distincts peuvent produire le même tirage, et les collisions ne
coûtent rien, elles rapportent.

Pour le **§92** : l'angle de la roue, s'il est tiré, publie 10,9 bits par tirage
filmé contre 1,9 pour le boost seul. Ce théorème dit à quoi ces bits servent —
à descendre de 61,6 sous 18,2.

### Ce que cela ne fait pas

1. **Cela ne produit aucune fuite.** Le théorème dit ce qu'une fuite doit valoir,
   pas qu'il en existe une. Les §68 à §92 n'en ont trouvé aucune, et ce bilan
   est inchangé.
2. **Cela ne teste rien.** Aucune statistique sur l'archive, donc **rien n'est
   consigné**. C'est la seule façon honnête de traiter un théorème.
3. **Le barème est un relevé d'écran** à BOOST ×1. Le fait structurel — les
   ordres bas sont nuls — tient tant que rien n'est payé en dessous de trois
   coïncidences, ce qui est le cas sur tout le relevé.
4. **La grille optimale exacte** reste un problème de couverture pondérée. Le
   théorème n'en donne qu'une minoration — celle qui suffit à décider de jouer.

**Registre : inchangé.** h72 démontre, il ne teste pas.

## 94. Le théorème du contenu : l'archive triée n'était pas muette (`h73_contenu.py`)

Trois sections répètent la même chose, et toutes les attaques algébriques en
dépendent :

| | |
|---|---|
| §11 | « l'archive est triée, l'ordre est perdu » |
| §47 | « contre toute hypothèse d'ordre, la puissance est **exactement nulle** » |
| §88 | « l'ordre y est perdu. **Sauf pour une chose** » — le bonus, 4 bits/tirage |

D'où les neuf tirages ordonnés du §86, les cinq du §61, et l'aveu répété que
l'archive de 70 560 lignes ne sert qu'au bonus.

**C'est faux.** Et l'erreur tient dans une identité que personne n'a écrite :

> **80 = 16 × 5**

Seize **divise** quatre-vingts. Donc, sous l'échantillonneur par modulo,
`(n−1) mod 16 = (out mod 80) mod 16 = out mod 16` : le **quartet de poids
faible du numéro est celui du mot de sortie**, c'est-à-dire quatre formes
F₂-linéaires exactes de l'état. Et le **multiensemble des vingt quartets est
invariant par permutation** — le tri ne le détruit pas.

### Le théorème

> **Théorème.** Soit `D` un 20-sous-ensemble uniforme de [80] et
> `m = (m_0,…,m_15)` le vecteur des comptes par classe résiduelle mod 16. Alors
>
> ```
> H(m) = log₂ C(80,20) − 16 · E[ log₂ C(5, m_v) ]
> ```
>
> *Preuve.* Le multiensemble des quartets équivaut à `m`. La chaîne
> `H(D) = H(m) + E[H(D|m)]` est exacte. Conditionnellement à `m`, `D` est
> **uniforme** sur les `Π_v C(5,m_v)` tirages réalisant ces comptes — chaque
> classe a exactement 5 membres et on en choisit `m_v`. Donc
> `H(D|m) = Σ_v log₂ C(5,m_v)`, et la **linéarité de l'espérance** conclut par
> échangeabilité des classes. Aucune indépendance n'est invoquée — les `m_v`
> sont fortement dépendants, et cela ne change rien. ∎

Loi marginale exacte (hypergéométrique, `N=80, K=5, n=20`), calculée à la main :

| m | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| P(m) | 0,22718 | 0,40569 | 0,27046 | 0,08393 | 0,01209 | 0,00064 |
| log₂C(5,m) | 0 | 2,3219 | 3,3219 | 3,3219 | 2,3219 | 0 |

`E[log₂C(5,m)] = 2,1473`, donc `16 × 2,1473 = 34,357`, et
`log₂ C(80,20) = 61,614`.

> **H(multiensemble) = 61,614 − 34,357 = 27,26 bits par tirage.**

`h73` refait le calcul par une **programmation dynamique sur les seize
classes** qui n'utilise pas la linéarité de l'espérance ; les deux voies
doivent coïncider, et la PD doit retrouver `C(80,20)` exactement.

### La décomposition exacte de 61,61

| | bits | |
|---|---|---|
| classe **mod 16** | **27,26** | F₂-**linéaire** pour un générateur à sortie brute → exploitable |
| « lequel des 5 » = part **mod 5** | 34,36 | non linéaire sur F₂ → muette |
| **total** | **61,61** | l'entropie d'un tirage |

Et ce que le dossier utilisait :

| source | bits/tirage | sur l'archive |
|---|---|---|
| le bonus seul (§88, §89) | 4,00 | 282 240 |
| **le multiensemble des quartets** | **27,26** | **1 923 000** |
| rapport | **×6,8** | |

> **Le dossier laissait dormir un facteur 6,8 sur chacune de ses 70 560
> lignes. Ce n'est pas une donnée à filmer : elle est dans le fichier depuis
> le premier jour.**

**Une précision qui borne ce facteur, et il faut la donner.** Les balayages de
graines — §63 et les campagnes `sweep_*` — comparaient déjà le tirage engendré
au tirage réel par **recouvrement**, donc sur l'**ensemble complet** : 61,6 bits
par tirage, pas 4. Le facteur 6,8 ne dormait que dans la branche **algébrique**.

| | ce qu'un tirage trié vaut |
|---|---|
| **vérifier** un candidat (balayage) | **61,62 bits** — utilisé depuis le §63 |
| **dériver** un candidat (résolution linéaire) | **27,26 bits** — et les §88/§89 n'en prenaient que 4 |

La distinction est nette : pour *vérifier*, l'archive triée a toujours valu un
tirage entier ; pour *dériver*, elle vaut la part mod 16 — et le dossier n'en
dérivait rien.

### Pourquoi personne ne l'a prise : le théorème de la parité

La tentation immédiate est de chercher une forme **linéaire** invariante par
permutation. Il n'y en a qu'une par position de bit : le XOR.
`P_b = ⊕_i bit_b(n_i − 1) = ⟨e_b, (Σ_{j∈J} L^j)x⟩`, où `J` est l'ensemble des
positions **acceptées**. C'est une forme linéaire — *dès qu'on connaît `J`*.

> **Théorème (négatif).** Sous l'échantillonneur par rejet, cette forme ne
> porte aucune information exploitable.
>
> *Preuve.* Soit `W` le nombre de mots consommés, `r = W − 20` le nombre de
> rejets. La somme sur le **préfixe complet**
> `Q_b = ⊕_{j≤W} bit_b(out_j) = ⟨e_b, (Σ_{j≤W}L^j)x⟩` ne dépend que de `W` —
> un seul entier inconnu. Or `Q_b = P_b ⊕ R_b`, où `R_b` est le XOR des
> quartets des mots **rejetés**. Un mot rejeté a par définition sa valeur mod
> 80 égale à une valeur déjà acceptée : son quartet est celui d'un des vingt
> numéros observés. `R` est donc le XOR d'un sous-multiensemble inconnu de
> taille `r` des vingt quartets connus, et parcourt le sous-espace qu'ils
> engendrent — qui est `F₂⁴` presque toujours. ∎

Et `r` vaut rarement zéro : `P(r=0) = Π_{i<20}(80−i)/80 = 7,46 %`, pour
`E[W] = 22,85` mots consommés. Les équations de parité forment donc une
instance de **parité bruitée** (LPN) à taux d'erreur **0,463** : une équation
sur treize est juste, et rien ne dit laquelle. À cette dimension, intraitable.

> **Voilà pourquoi l'information dormait.** Elle est là — 27,26 bits, le
> théorème le prouve — mais la seule voie **linéaire** qui y mène est fermée
> par le rejet. Ce n'est pas une limite de calcul, c'est une propriété de
> l'échantillonneur ; il fallait la démontrer avant de déclarer l'archive
> pauvre.

### Ce que coûte et ce que rapporte la contrainte de multiensemble

Elle n'est pas linéaire, mais elle est **exactement vérifiable** : pour un état
candidat et un motif de pas donné, on calcule les vingt quartets prédits et on
les compare au multiensemble observé. Coût `O(20)` ; une hypothèse fausse
survit avec probabilité `2⁻²⁷,²⁶`.

| par tirage | |
|---|---|
| inconnues ajoutées | le nombre de rejets `r`, **≤ 3 bits** |
| contraintes ajoutées | le multiensemble, **27,26 bits** |
| **gain net** | **24,26 bits/tirage** |

| famille | n | tirages requis | minutes de jeu |
|---|---|---|---|
| xorshift64 | 64 | 2,6 | 13 |
| xorshift128 | 128 | 5,3 | 26 |
| xoshiro256 | 256 | 10,6 | 53 |
| WELL512a | 512 | 21,1 | 106 |
| **MT19937** | **19 937** | **822** | 4 110 |

À comparer aux **neuf** tirages ordonnés du §86 : le §80 exigeait 343 tirages
*ordonnés* pour MT19937, le §61 en exigeait 6,4 pour WELL512a et n'en avait que
cinq. **Ici les tirages sont triés, et l'archive en contient 70 560 — soit 86
fois ce que MT19937 demande.**

**Ce qui reste à payer, et je ne vais pas l'enjoliver.** La contrainte étant un
multiensemble et non une équation, la résolution n'est pas une élimination de
Gauss : c'est une **recherche avec affectation**. L'attaque naïve fixe les
quartets position par position, branchement ≤ 16, et **aucun élagage avant la
saturation du rang** : le coût est `16^(n/4) = 2ⁿ`, c'est-à-dire exactement
l'énumération de l'état. **Aucun gain.** Une rencontre-au-milieu à `2^(n/2)`
n'est pas démontrée ici.

**Mais une part du contenu se lit sans aucune affectation, et c'est elle qui
est immédiatement utilisable.** Pour chaque position de bit `b`, le **compte**
`c_b = #{i : bit_b(n_i − 1) = 1}` est observable, et c'est le poids de Hamming
du vecteur des vingt formes `⟨e_b, L^j x⟩`. Le vérifier ne demande **aucune**
affectation : on calcule les vingt formes et on compte. Or
`c_b ~ hypergéométrique(80, 40, 20)`, de variance `20·¼·(60/79) = 3,797`, donc
`H(c_b) ≈ 3,01 bits` — et les quatre comptes valent jusqu'à **≈ 12 bits par
tirage, trois fois le bonus**, en `O(20)` par vérification.

> Le théorème donne le **contenu** (27,26 bits), la **part gratuite** (≈ 12 bits,
> sans affectation) — et laisse ouvert l'algorithme qui prendrait le reste.

### L'angle mort du §89, que ceci ouvre

Le §89 exclut tout générateur F₂-linéaire d'état ≤ 35 280 bits par
Berlekamp-Massey sur la suite des bonus. Le §90 a vérifié que sa portée ne
dépend pas de `W`. Mais il reste une condition **jamais nommée** :

> BM ne voit une suite linéaire récurrente que si le **pas entre bonus
> consécutifs est constant**.

Sous **Fisher-Yates**, le pas vaut exactement 20 : le §89 s'applique. Sous
**rejet**, le pas vaut `20 + r_t` avec `r_t` aléatoire, et une décimation à
positions irrégulières d'une suite linéaire **n'est pas** linéaire récurrente.

> **Le §89 ne dit rien de l'échantillonneur par rejet** — l'implémentation que
> le §76 appelle lui-même « la naïve par excellence », et qui n'a jamais été
> testée que sur neuf tirages ordonnés.

C'est exactement le trou que le théorème du contenu remplit : 27,26 bits par
tirage **trié**, sur 70 560 tirages, avec le motif de pas comme seule inconnue
supplémentaire — 3 bits contre 27,26.

### Ce que cela ne fait pas

1. **Cela ne reconstitue aucun état.** Ce fichier mesure une capacité, il
   n'exécute pas d'attaque. Rien ici ne contredit le bilan des §68 à §92 :
   zéro état compatible partout.
2. **Cela ne vaut que pour l'échantillonneur par modulo.** Sous troncature
   (§82) ou bits de poids fort (§87), le quartet du numéro n'est pas celui du
   mot et l'identité 80 = 16 × 5 ne mord pas.
3. **Cela ne vaut que pour une sortie brute.** PCG, xoshiro\*\*/++, splitmix64
   n'ont pas de quartet linéaire — le §91 le disait déjà.
4. **Le facteur 6,8 est un contenu, pas un algorithme.**

**Registre : inchangé.** h73 démontre et mesure, il ne teste pas.

## 95. L'angle mort du §89, démontré par un faux négatif (`h74_pas_variable.py`)

Le §94 a nommé une condition que le §89 portait sans l'écrire. Ce fichier ne la
discute pas : **il fabrique le contre-exemple.**

Le §89 conclut — c'est l'énoncé le plus large du dossier, il ne nomme aucune
famille : *« la suite des bonus n'est engendrée par aucun générateur F₂-linéaire
dont l'état tienne sous 35 280 bits »*. Le §90 a vérifié qu'il ne dépendait pas
de `W` et en a conclu qu'il était **plus fort** qu'annoncé.

Or la suite des bonus vaut `b_t = φ(L^{S_t}x)`, où `S_t` est la position du
premier mot du tirage `t`. **Si le pas est constant**, `b_t = φ((L^W)^t x)` est
linéaire récurrente, de complexité ≤ n, et BM la voit. **Si le pas varie**, c'est
une décimation à positions irrégulières — rien ne garantit la récurrence.

### Le faux négatif, sur MT19937 lui-même

Même générateur, même état initial, **même formule de bonus**. Une seule chose
change : l'échantillonneur, donc le pas. 45 000 tirages synthétiques (BM peut
donc constater jusqu'à 22 500, au-dessus de la cible 19 937).

| échantillonneur | pas moyen | pas min/max | complexité, les 4 bits |
|---|---|---|---|
| Fisher-Yates | 20,00 | 20 / 20 | **19 937 · 19 937 · 19 937 · 19 937** |
| rejet modulo 80 | 22,85 | 20 / 35 | 22 500 · 22 501 · 22 500 · 22 501 |

Sous Fisher-Yates, BM rend **exactement la taille d'état de MT19937**, sur les
quatre bits. Sous rejet, il rend **N/2** — la signature d'une suite aléatoire.

> **Le §89, appliqué à cette archive synthétique, aurait écrit exactement sa
> phrase. Et le générateur est MT19937, il est là, on connaît son état.**

### De combien le pas doit-il varier ?

xorshift64 (64 bits), pas `20 + Bernoulli(p)`, 900 tirages, 12 graines par point.
`p = 0` et `p = 1` sont tous deux des pas **constants** (20 et 21) — c'est le
contrôle interne du test.

| p | 0 | 0,002 | 0,005 | 0,01 | 0,05 | 0,50 | 1,0 |
|---|---|---|---|---|---|---|---|
| complexité moyenne | **64,0** | 385,7 | 436,9 | 450,2 | 450,0 | 450,2 | **64,0** |
| BM voit | **12/12** | 1/12 | 0/12 | 0/12 | 0/12 | 0/12 | **12/12** |

La falaise est brutale, et le plateau tombe sur `N/2 = 450` au bit près.
`p = 1` redonne 64 : **c'est l'irrégularité du pas qui aveugle BM, pas sa
valeur.** Il suffit qu'**un tirage sur 200** consomme un mot de plus. Le rejet,
lui, en fait varier **93 %** (§94 : `P(r=0) = 7,46 %`).

> **Le §89 n'est pas « presque » valide sous rejet. Il l'est zéro fois.**

### Ce que le §89 exclut vraiment

| | |
|---|---|
| énoncé consigné | « aucun générateur F₂-linéaire d'état sous 35 280 bits » |
| **énoncé correct** | « … **et qui consomme un nombre de mots constant par tirage** » |

**Reste couvert** : Fisher-Yates partiel — l'échantillonneur le plus courant en
bibliothèque — et tout schéma à budget de mots fixe. **Sort de la couverture** :
l'échantillonneur par **rejet**, sous toutes ses variantes, et tout schéma dont
la consommation dépend des valeurs tirées.

**Le résultat numérique du §89 ne bouge pas.** Les complexités mesurées sur
l'archive réelle — 35 279, 35 281, 35 281, 35 281 pour N/2 = 35 280 — restent
exactes. C'est leur **interprétation** qui rétrécit.

### Pourquoi rien n'est consigné, et c'est du protocole

Ce fichier ne teste pas l'archive : il fabrique deux archives **synthétiques** à
générateur connu. Pas d'hypothèse sur le tirage réel, donc pas de p.

Et il serait tentant de **re-consigner h68** avec l'hypothèse corrigée —
`lab.dedupe()` le permettrait techniquement, la dernière écriture d'un `id`
écrasant les précédentes. **Ce serait une faute** : réécrire une hypothèse
pré-enregistrée après avoir vu le résultat est exactement ce que le
pré-enregistrement interdit. L'entrée de h68 reste scellée telle quelle ; la
correction de portée vit ici, datée.

### Ce que cela rouvre

Une famille que le dossier croyait fermée ne l'est pas : **les générateurs
F₂-linéaires à échantillonneur par rejet**, jamais testés que sur neuf tirages
ordonnés (§86) et cinq (§61). Et le §94 dit où chercher : 27,26 bits par tirage
trié sur la classe mod 16, dont 12,04 vérifiables sans affectation, contre 3 bits
d'inconnue de pas. **Le budget est largement positif ; c'est l'algorithme qui
manque** — la contrainte est un multiensemble, pas une équation.

**Registre : inchangé, à dessein.**

## 96. L'attaque sur l'archive triée, et le coût du rejet (`h75_attaque_rejet.py`)

Le §95 a sorti l'échantillonneur par rejet de la couverture du §89. Il n'avait
jamais été attaqué que sur **neuf** tirages ordonnés (§86) et **cinq** (§61).
Ce fichier l'attaque sur les **70 560 tirages triés** — et c'est la première
fois que le dossier reconstitue un état sans jamais voir l'ordre de sortie.

### L'attaque

Sous l'hypothèse du §88 — le bonus est le premier numéro sorti — et pour un
générateur F₂-linéaire à sortie brute, `bonus_t − 1 = out(S_t) mod 80` donne
`out(S_t) mod 16`, soit **quatre formes linéaires exactes** de l'état à la
position `S_t`, avec `S_{t+1} = S_t + 20 + r_t`.

`r_t`, le nombre de mots rejetés, est **inconnu**. On cherche donc en
profondeur sur le motif `(r_0,…,r_{k−2})`, avec élimination de Gauss
incrémentale sur F₂ et journal d'annulation (technique du §61), puis
**énumération du noyau** quand le rang est déficient, puis rejeu exact comparé
aux ensembles triés — 61,62 bits par tirage.

**Deux bugs trouvés en route**, et le second est le plus instructif :

1. *Rang déficient au point vrai.* Supposer la solution unique faisait manquer
   une fenêtre pourtant dans la couverture. C'est l'erreur du §52, commise une
   seconde fois. Corrigée par l'énumération correcte du noyau.
2. *Métrique du témoin fausse.* Je comptais comme désaccord les fenêtres
   résolues **au-delà** de la couverture déclarée — alors que c'est de la
   puissance en plus.

### Le témoin, et pourquoi il a deux colonnes

L'état est planté, donc les vrais rejets sont connus et on peut confronter.

| famille | fenêtres | dans la couv. | retrouvés | **manqués** | prime |
|---|---|---|---|---|---|
| xorshift32 (13,17,5) | 12 | 2 | 3 | **0** | 1 |
| xorshift32 (1,3,10) | 12 | 1 | 2 | **0** | 1 |
| xorshift32 (5,17,13) | 12 | 4 | 4 | **0** | 0 |

> **Manqués = 0 partout** : aucune fenêtre dans la couverture n'échappe à
> l'attaque. **Prime > 0** : elle en résout même hors couverture, quand le rang
> déficient fait tomber l'énumération sur l'état vrai malgré un motif de pas
> faux. **La couverture déclarée est donc un minorant strict**, ce qui rend
> l'exclusion plus forte qu'annoncée, jamais plus faible.

### Ce que l'archive apporte : la couverture se compose

Le §61 avait cinq tirages ordonnés — une fenêtre, couverture 64 %, et rien
pour la relever. Ici **chaque bloc de `k` tirages consécutifs est une fenêtre**,
et l'archive en offre 8 820 (elle est une plage strictement consécutive :
70 559 écarts, tous égaux à 1). La couverture ne s'additionne pas, elle **se
compose** : `1 − (1−c)^m`.

| | par fenêtre | fenêtres attaquées | **cumulée** |
|---|---|---|---|
| xorshift32, T = 8 | 0,004172 | 5 200 | **1 − 3,6·10⁻¹⁰** |

**15 600 fenêtres attaquées, 0 état compatible.** L'exclusion n'est pas
conditionnelle : la fraction des motifs de rejet non explorés vaut 3,6·10⁻¹⁰.
Registre **m = 3 493, zéro significatif**.

### Le mur, chiffré

Le coût est le nombre de motifs de pas explorés, `2^(H(r)·(n/4 − 1))` avec
`H(r) = 2,85` bits **mesurés sur la loi exacte** (convolution de vingt
géométriques), soit `2^(0,712 n)` contre `2^n` en force brute.

| n | force brute | attaque | gain | faisable |
|---|---|---|---|---|
| 32 | 2³² | **2¹⁹·⁹** | 2¹²·¹ | **oui** |
| 48 | 2⁴⁸ | 2³¹·³ | 2¹⁶·⁷ | non |
| 64 | 2⁶⁴ | 2⁴²·⁷ | 2²¹·³ | non |
| 128 | 2¹²⁸ | 2⁸⁸·² | 2³⁹·⁸ | non |

> **Le gain est réel — 2^(0,29 n) — et il ne suffit pas.** À 64 bits la
> couverture par fenêtre tombe à 2,1·10⁻⁷, que même 4 410 fenêtres ne relèvent
> pas. xorshift64 est écrit **« hors portée »**, jamais « exclu ».

**Ce n'est donc pas « on n'a pas trouvé » : c'est une défense chiffrée.**
L'échantillonneur par rejet coûte 2,85 bits d'inconnue par tirage là où le
modulo n'en rend que 4. Le solde bascule vers **48 bits d'état**.

**Ce qui le franchirait**, précisément : le **boost** (§90 lui compte 1,151
forme par tirage à décalage fixe — passer de 4 à 5,151 formes ferait tomber le
coût de `2^0,712n` à `2^0,553n`, soit 2³⁵ au lieu de 2⁴³ à 64 bits) ; ou
**l'ordre de sortie**, qui rend le rejet lisible et fait disparaître l'inconnue
de pas — mais le dossier n'en a que neuf tirages.

**Registre : consigné.**

## 101. La carte vérifiée : lire les sources plutôt que la prose (`h82_carte_verifiee.py`)

La carte de couverture a menti **deux fois aujourd'hui** — §97 et §98 — et pour
la même raison : *une conclusion recopiée plus largement que sa source*. Une
carte tenue à la main dérive de sa base de code. Celle-ci **se recalcule**.

`h82` ne recopie rien : il lit les sources C et en extrait les tableaux de noms
que chaque programme utilise pour **s'annoncer lui-même** (`GEN_NAME`,
`FAM_NAME`, `SAMP_NAME`, ou à défaut ses fonctions d'échantillonnage).

### Ce que les neuf outils couvrent réellement

| outil | lignes | générateurs | échantillonneurs |
|---|---|---|---|
| `sweep_java48.c` | 276 | — | **1** (`java_fy` seul) |
| `sweep_keys.c` | 302 | 12 | — |
| `sweep_linked.c` | 348 | 12 | 4 |
| `sweep_modern.c` | 1124 | **40** | 4 |
| `sweep_mt.c` | 336 | — | 5 |
| `sweep_order.c` | 430 | 12 | 4 |
| `sweep_rand.c` | 554 | **20** | **6** |
| `sweep_time.c` | 339 | 8 | 4 |

**La couverture réelle est plus riche que la prose ne le disait.** `sweep_rand.c`
inclut les quatre types de `glibc random()` — **T1 (7,3), T2 (15,1), T3 (31,3),
T4 (63,1)**, c'est-à-dire les Fibonacci retardés — plus MINSTD, RANDU,
Borland/Delphi, et deux échantillonneurs `nextDouble` que la carte ne mentionne
nulle part. `sweep_modern.c` couvre quarante familles dont Philox, ThreeFry,
ChaCha8/12/20, sfc64, jsf64, wyrand, romuTrio, romuDuoJr.

> **Correction à mon propre §99 :** j'y écrivais que les Fibonacci retardés
> n'étaient pas couverts. C'est faux pour glibc — ses quatre types sont dans
> `sweep_rand.c`. Ce qui reste vrai, et vérifié mécaniquement ici, c'est
> l'absence de **`System.Random`** et de **`mt_rand`**.

### Le mensonge de `sweep_java48.c`, relu dans la source

```
sweep_java48.c annonce 1 échantillonneur(s) : java_fy
```

Un Fisher-Yates partiel, et rien d'autre. La carte annonçait « rejet / FY
modulaire ». C'est **exactement** ainsi que le défaut se voit : le fichier n'a
aucun tableau `SAMP_NAME`, donc on lit ses fonctions — et il n'y en a qu'une.

### Ce qui n'est dans aucune source

| famille | pourquoi elle compte |
|---|---|
| **`System.Random` (.NET)** | Fibonacci de Knuth, lags effectifs **55/34** mod 2³¹−1, sortie par troncature. La bibliothèque standard de tout back-end .NET. |
| **`mt_rand` (PHP < 7.1)** | le §72 le présente comme MT19937 — **faux** : son `twist` prend `loBit(u)` au lieu de `loBit(v)`. |
| **MWC / SWB** | générateurs à retenue, nommés au §91. Et une piste : ils sont **équivalents à un LCG multiplicatif modulo `a·2³²−1`**, ce qui est par où il faudrait les attaquer. |

Les deux premières sont désormais couvertes **autrement** — les §79 et §80
cherchent la récurrence plutôt que la graine, et une récurrence linéaire
d'ordre ≤ 2 mod 2^k y est exclue quelles que soient ses constantes. La
troisième reste ouverte.

### La règle qui en découle

> **Une ligne de carte ne doit jamais être plus large que la source qu'elle
> cite. Quand les deux divergent, c'est la source qui a raison.**

**Registre : inchangé.** h82 ne teste rien — il vérifie une prose contre du code.

## 100. Le théorème du bit zéro : le §89 est bien plus large qu'il ne le dit (`h81_bit_zero.py`)

Cette session a corrigé le §89 **deux fois, en sens contraire**, sur deux axes
indépendants. Le §95 l'a rétréci ; celui-ci l'élargit.

### Le théorème

> **Théorème.** Soit `s_i = Σ_j a_j·s_{i−j} + c (mod 2^k)`, coefficients
> **quelconques**. Alors la suite du **bit 0** vérifie la récurrence F₂-affine
> de coefficients `a_j mod 2`, **de même ordre**.
>
> *Preuve.* Modulo 2, l'addition et la multiplication de `Z/2^k` se réduisent à
> celles de F₂, et **aucune retenue ne remonte vers le bit 0** — il n'y a rien
> en dessous de lui. ∎

Le bit 0 est le **seul** dans ce cas. Dès le bit 1, la retenue issue du bit 0
entre dans le calcul et la forme F₂ est cassée. Vérifié sur des récurrences
tirées au hasard, ordres 1 à 8 :

| ordre | coefficients mod 2 | bit 0 suit ? | bit 2 suit ? |
|---|---|---|---|
| 3 | `[1, 1, 0]` | **OUI** | non |
| 1 | `[1]` | **OUI** | non |
| 5 | `[0, 1, 0, 0, 0]` | **OUI** | non |
| 8 | `[1,1,1,1,1,1,1,1]` | **OUI** | non |

### Ce que le §89 mesure vraiment

```
complexité linéaire du bit zéro : 35 279     pour N/2 = 35 280     écart : −1
```

Par le théorème, une récurrence linéaire sur `Z/2^k` d'ordre `r` produirait une
complexité d'au plus `r + 1`. Le bit zéro de l'archive est à **une unité** de
`N/2` : indiscernable du hasard.

> **Aucune récurrence linéaire modulo une puissance de deux, d'ordre au plus
> 35 280, à coefficients quelconques — connus ou non — n'engendre la suite des
> bonus.** Le §89 annonçait « F₂-linéaire ». Il excluait, sans le savoir, une
> classe bien plus vaste.

### Les deux corrections, ensemble

| axe | correction | sens |
|---|---|---|
| **le pas** | §95 : il faut un pas **constant**. Sous rejet, BM ne voit rien — faux négatif démontré sur MT19937. | **rétrécit** |
| **l'algèbre** | §100 : toute récurrence linéaire sur `Z/2^k`, pas seulement F₂. | **élargit** |

L'énoncé juste est donc : *« aucune récurrence linéaire modulo une puissance de
deux, d'ordre au plus 35 280, n'engendre la suite des bonus **d'un générateur
consommant un nombre fixe de mots par tirage** »*.

### Et ce que cela m'a évité

J'allais appliquer le balayage du §80 à la suite des bonus de l'archive. **Le
théorème le rend inutile** : le bit zéro couvre déjà toute la classe, et
jusqu'à l'ordre 35 280 au lieu de 2. C'est la seule raison pour laquelle ce
fichier existe.

Le §80 garde en revanche toute sa valeur **sur les tirages ordonnés** : donnée
différente (des mots consécutifs dans un tirage, pas un bonus par tirage),
hypothèse différente (l'alignement mot-numéro plutôt que le pas constant), et
il **nomme** ce qu'il trouve — `a, b, c, p, q` — là où Berlekamp-Massey ne rend
qu'un nombre.

**Registre : inchangé, à dessein.** h81 ne teste rien de neuf : il démontre et
ré-interprète. Re-consigner h68 avec un énoncé élargi serait la faute que le
§95 refusait de commettre dans l'autre sens.

## 99. Chercher la récurrence au lieu de la graine (`h78`, `h79`, `h80`)

Trois fichiers, une seule idée : **arrêter de demander « quelle famille ? »**.

### Le constat qui les déclenche

Les douze familles balayées au §34 sont, mot pour mot :

```
java.util.Random, LCG32 MSVC, LCG32 glibc, xorshift32, xorshift64*,
splitmix64, pcg32, LCG64 MMIX, xoshiro256**, xoshiro128**, xoroshiro128+, pcg64
```

Il y manque **`System.Random` de .NET** et **`mt_rand` de PHP** — les deux
bibliothèques standard les plus répandues du web, et exactement ce qu'un
opérateur régional utiliserait. Le §72 affirme même que `mt_rand` *est*
MT19937 : **c'est faux**, jusqu'à PHP 7.1 son `twist` prend `loBit(u)` au lieu
de `loBit(v)` — vingt ans de bug, et un générateur différent.

### §78 — les douze hoquets : chercher le ré-amorçage là où le serveur trébuche

L'horodatage est une grille de 300 s. Le §63 s'en sert pour la graine horaire
et note « 70 548 sur 70 560 » sans lire les exceptions. Elles se séparent en
trois :

| | | |
|---|---|---|
| 343 | 25 500 s (21:00 → 04:05 UTC) | la **fermeture nocturne** |
| 2 | 29 100 s et 21 900 s, le 26 oct. et le 29 mars | les **changements d'heure** |
| **12** | un tirage **en retard de 1 à 5 s**, aussitôt rattrapé | **le serveur a hoqueté** |

Le retard n'est jamais cumulatif : la cadence est **absolue**, et quelque chose
a bloqué le processus juste avant. Sur un service métronomique, c'est une pause
longue ou un **redémarrage** — donc, pour un générateur non cryptographique, un
**ré-amorçage**.

La conjonction testée n'avait jamais été faite : le §63 balaie la **seconde**
contre l'archive, le §34 la **milliseconde** mais contre les cinq tirages
ordonnés. Ici : la **milliseconde contre l'archive, aux instants de
redémarrage**. Et la cible est fixée **par le calendrier seul**, avant tout
regard sur les numéros — pas de pêche aux données.

> **1 148 046 390 graines testées, 0 compatible.** Six familles × trois formes
> de graine × (12 hoquets à fenêtre d'une heure + 343 ouvertures de session à
> une minute). Témoin **4/4 par famille** à l'échelle réelle. Espérance de faux
> positifs : 3,2·10⁻¹⁰.

### §79 et §80 — la signature d'une récurrence

Le levier est le **§94** : comme `16` divise à la fois `80` et `2^k`, une
relation linéaire sur l'état **descend exactement** sur les quartets des
numéros.

> `(n_i − 1) = a·(n_{i−p} − 1) + b·(n_{i−q} − 1) + c (mod 16)`
>
> avec `a, b, c` **inconnus** — trois entiers de quatre bits qu'on balaie, sauf
> `c` qu'on **ajuste par le mode** de la différence. Ni graine, ni état, ni
> constantes : seulement des numéros consécutifs.

Cela couvre d'un seul coup : `b = 0` → **tout LCG mod 2^k à constantes
inconnues** ; `a = b = 1` → les **Fibonacci retardés** (dont .NET) ; `a, b`
quelconques → **toute récurrence linéaire d'ordre deux**.

**Deux bugs attrapés par le témoin**, et ils valent d'être dits : les lags
effectifs de `System.Random` ne sont pas les 24/55 de la littérature mais
**55/34** — l'indexation circulaire les déplace — et la relation a **p > q**,
qu'un balayage `p < q` manquerait.

| témoin | p | q | a | b | c | succès | z |
|---|---|---|---|---|---|---|---|
| .NET `System.Random`, troncature | **55** | **34** | −1 | | | **25/25** | — |
| Fibonacci additif, modulo | **24** | **55** | +1 | | | **25/25** | — |
| LCG mod 2³², constantes inconnues | 1 | — | **13** | — | **9** | **79/79** | **+34,4** |
| récurrence `(3, 7, 13)` aux lags `(2,5)` | **2** | **5** | **3** | **7** | **13** | **75/75** | **+33,5** |
| bruit uniforme | | | | | | 16/73 | +5,5 |

`1103515245 mod 16 = 13`, `12345 mod 16 = 9` : **le test retrouve les
constantes elles-mêmes.**

### Et la leçon du null

| | z observé | null : moyenne | **p** |
|---|---|---|---|
| §79, signature additive | **+5,19** | **+5,33** | 0,4713 |
| §80, signature générale | **+5,78** | **+6,17** | 0,7512 |

> **Un z de +5,19 aurait l'air décisif isolément — et il tombe *sous* la
> moyenne du null.** Balayer 23 760 combinaisons produit un maximum de ~5,3 tout
> seul. C'est la raison d'être de l'étape par permutation, et c'est pourquoi
> aucun « signal » de ce dossier n'est annoncé sans elle.

**Registre : m = 3 504 puis 3 505, zéro significatif.**

### Ce que cela ferme, et ce que cela ne ferme pas

**Fermé** : toute récurrence linéaire d'ordre ≤ 2 modulo une puissance de deux,
à sortie brute, décalages jusqu'à 30, **constantes quelconques** — sans avoir
essayé une seule graine. Plus le ré-amorçage horaire aux douze redémarrages et
aux 343 ouvertures de session.

**Non fermé** : les sorties **non brutes** (un décalage, une troncature ou un
brouillage cassent la descente mod 16 — le §97 traite le premier cas) ; les
**ordres supérieurs à deux** (MT19937 est d'ordre 624) ; les générateurs **à
retenue**, dont le terme additif n'est pas une constante — l'échappatoire
nommée au §91 ; et **l'alignement**, puisque sous rejet les doublons sautent
des mots.

## 98. L'audit de la carte : trois défauts, et une famille débloquée (`h77_chaines_longues.py`)

Le §97 a trouvé une ligne **fausse** dans la carte de couverture. Si une ligne
est fausse, il faut lire les autres. Cet audit en trouve deux de plus, et la
cause des trois est dans le code, pas dans le raisonnement.

### Défaut 1 — une ligne contradictoire

```
| F₂-linéaires ≤ 128 bits | rejet modulo 80 | §68 | résolu, TOUTE GRAINE, couverture 46–99 % |
```

« Toute graine » et « 46 % » ne peuvent pas tenir ensemble.

### Défaut 2 — une garde périmée

`h61_familles_etendues.py`, ligne 559 :

```python
if need > 2:            # le dossier n'a qu'UNE paire consecutive
    continue
```

C'était vrai à cinq tirages ordonnés. Le dossier en a **neuf**, dont la plage
**1381256–1381259**, quatre à la suite. Les familles demandant trois ou quatre
tirages chaînés étaient écartées **faute de données qui existent**.

### Défaut 3 — un bug dans la loi de rejets

Le plus instructif, et il va dans le sens **inconfortable**. `h61` calcule sa
couverture avec la loi d'un tirage de `w` numéros **distincts d'affilée**. Or
une chaîne de deux tirages n'est pas un tirage de 33 numéros distincts : **au
vingt-et-unième, l'ensemble des déjà-vus est remis à zéro** et la probabilité
de rejet retombe à zéro.

| `w = 33` | rejets attendus |
|---|---|
| loi du §81 (33 d'affilée) | **6,60** |
| loi correcte (20 + reset + 13) | **3,82** |

Presque un facteur deux — et l'erreur **sous-estime** la couverture. Le dossier
s'annonçait moins avancé qu'il ne l'était. C'est le genre de faute qu'on ne
cherche jamais, parce qu'elle rend les conclusions plus prudentes.

### Et la composition

Chaque chaîne est un essai **indépendant** : il suffit qu'**une** ait son motif
de rejet dans la portée. Le §68 et le §81 rapportaient la couverture d'**une
seule**.

| famille | chaînes | §81 | corrigée | **composée** | états |
|---|---|---|---|---|---|
| xorshift32 | 9 | 100,0 % | 100,0 % | 100,0 % | **0** |
| xorshift64 | 9 | 99,6 % | 99,6 % | 100,0 % | **0** |
| xorshift96 | 4 | 58,1 % | 93,9 % | **100,0 %** | **0** |
| xorshift128 | 4 | **8,1 %** | 64,1 % | **98,3 %** | **0** |
| taus88 | 4 | 83,4 % | 91,2 % | 100,0 % | **0** |
| xoroshiro128 | 4 | 8,1 % | 64,1 % | 98,3 % | **0** |
| xoshiro128 | 4 | 8,1 % | 64,1 % | 98,3 % | **0** |
| **xoshiro256** | 1 | *écartée* | 3,9 % | **3,9 %** | **0** |

**39 attaques, 0 état compatible.** Registre **m = 3 501, zéro significatif**.

> **Et il faut lire ce tableau en deux temps, sous peine de se tromper.** Le
> fichier imprime « couverture minimale 3,9 % » — mais ce 3,9 %, c'est
> **xoshiro256**, la famille que le §81 n'atteignait **pas du tout**. Pour les
> sept familles que le §68 prétendait fermer, le chiffre corrigé est **98,3 à
> 100 %** : sa conclusion « fermé pour toute graine » devient enfin défendable,
> alors qu'elle ne l'était pas quand il l'a écrite.
>
> xoshiro256, elle, est **entamée, pas fermée** — une seule chaîne de quatre
> tirages, 3,9 % de couverture. L'écrire autrement serait refaire l'erreur
> qu'on vient de corriger.

### Méthode

`h77` ne réimplémente rien : il **exécute l'en-tête de `h61`** — toutes ses
fonctions sont définies avant sa première section — et ne change que trois
choses : le nombre de chaînes, la loi de rejets, la composition. Aucune
divergence possible entre l'attaque auditée et l'attaque d'origine.

**Registre : consigné.**

## 97. `java.util.Random` sous rejet, et le théorème du jumeau (`h76_java_rejet.py`)

### La case vide, et elle était la plus probable de toutes

Le §34 a mené deux campagnes qui **se croisent sans se recouvrir** :

| campagne | espace d'états | échantillonneur |
|---|---|---|
| `sweep_java48` | **les 2⁴⁸ complets** | Fisher-Yates **seulement** |
| `sweep_order` | graines **[0, 2³²) seulement** | 4 échantillonneurs |

**Et la carte de décision du §73 disait le contraire.** Elle portait la ligne
*« LCG mod 2⁴⁸ (`java.util.Random`) | **rejet / FY modulaire** | §34 | 2⁴⁸
complets »* — donc « rejet couvert ». Vérification faite dans la source :
`tools/sweep_java48.c` ne contient qu'**une seule** fonction
d'échantillonnage, `java_fy`, un Fisher-Yates partiel à `nextInt(80−i)`. Il
n'y a **aucun** échantillonneur par rejet dans ce fichier. La carte
surestimait la couverture du §34 ; elle est corrigée, et c'est exactement le
genre d'écart qui fait croire une case fermée alors qu'elle est ouverte.

Or `new Random()` en Java tire sa graine de `nanoTime` mêlée à un compteur :
l'état est un **48 bits arbitraire**, hors de portée d'un balayage 2³². Et
l'idiome par défaut pour vingt numéros distincts est

```java
Set<Integer> s = new HashSet<>();
while (s.size() < 20) s.add(rnd.nextInt(80) + 1);
```

c'est-à-dire un **échantillonneur par rejet** — celui que le §95 vient de
sortir de la couverture du §89. **Personne n'avait testé cette combinaison.**

### Le levier est au milieu de l'état

`next(31)` rend `(int)(s >>> 17)`, et `nextInt(80)` rend `next(31) % 80`.
Comme 16 divise 80 :

> `p mod 16 = (s >>> 17) mod 16 =` **les bits 17 à 20 de l'état**

Ni les bits de poids faible où vit le levier 2-adique habituel, ni ceux de
poids fort où vivent les attaques par réseau : **ceux du milieu**. Et le LCG
modulo 2⁴⁸ reste **clos modulo 2²¹** — ces bits ne dépendent donc que de
21 bits d'état, pas 48. D'où deux étages : `2²¹` puis `2²⁷`.

**Le lemme du préfixe propre** neutralise le rejet au départ : un rejet exige
un doublon, et au début il n'y a rien à doubler.

| rejets tolérés | probabilité | source |
|---|---|---|
| 0 | 0,6966 | `Π_{i<8}(1 − i/80)` |
| 1 | 0,2438 | `P(0) × Σ_{i<8} i/80` |
| **total** | **0,9405** par tirage | **1 − 9,4·10⁻¹²** sur les 9 tirages ordonnés |

Et **le piège de la borne 64** que le §34 devait traiter — `nextInt` prend les
bits de poids fort pour les puissances de deux, et Fisher-Yates croise 64 en
décroissant de 80 à 61 — **ne se présente pas ici** : sous rejet la borne vaut
toujours 80.

### Le résultat

L'attaque casse un état 48 bits **tiré au hasard** en 7 secondes, là où le
balayage brut demandait 2,8·10¹⁴ pas.

> **Zéro état compatible sur les neuf tirages ordonnés.** Registre m = 3 490,
> zéro significatif.

### Le théorème du jumeau

Trouvé en débuggant le témoin, et vérifié à la main :

```
état a : mots  46, 46, 75, 66, …   →  46 accepté, 46 REJETÉ, puis 75, 66, 0…
état b : mots  46, 75, 66,  0, …   →  46, 75, 66, 0…      la MÊME suite acceptée
```

> **Théorème.** Sous échantillonneur par rejet, l'application
> `état → tirage ordonné` **n'est pas injective**. Si le premier mot est
> immédiatement redoublé — probabilité 1/80 — l'état d'avant et celui d'après
> produisent le même tirage. Et les deux jumeaux **convergent dès le premier
> numéro accepté** : ils sont opérationnellement identiques.

**Ce que cela corrige.** Le dossier répète depuis le §34 que *« la vérification
est un rejeu exact, donc aucun faux positif possible »*.

| | |
|---|---|
| pour **exclure** | **vrai** — un zéro reste un zéro. Toutes les campagnes nulles du dossier tiennent, celle-ci comprise. |
| pour **identifier** | **trop fort** — l'état n'est déterminé qu'à un jumeau près. |
| pour **prédire** | sans conséquence — les jumeaux ont le même futur. |

Le témoin testait donc la mauvaise chose. Le critère correct n'est pas « on
retrouve l'état planté » mais « l'état trouvé **prédit les mêmes tirages
suivants** ». Avec lui : **2/2**, dont un par un jumeau.

### Ce que cela ferme, et ce qui reste

**Fermé** : `java.util.Random` à état 48 bits arbitraire sous échantillonneur
par rejet — et par la même occasion `drand48`/`lrand48`, qui partagent
exactement ces constantes et cette extraction. C'était la famille qui
échappait **à la fois** au §89 (rejet ⇒ pas constant, §95) et au §91
(`java.util.Random` déclaré aveugle à BM car sa sortie est décalée), et qui
n'était couverte qu'à 2³².

**Reste**, et la liste rétrécit :
1. les LCG modulo 2⁴⁸ à **autres constantes** — mais celles de `drand48` sont
   les seules standard ;
2. les sorties **brouillées** à état plein (PCG, xoshiro\*\*/++, splitmix64) —
   leurs scramblers font descendre les bits hauts, ce qui détruit précisément
   la clôture 2-adique exploitée ici ;
3. les générateurs **à retenue** (MWC), nommés au §91 ;
4. tout **CSPRNG**, et le matériel.

**Registre : consigné.**

## 102. MWC : la dernière case nommée, et pourquoi 64 bits n'en coûtent que 32 (`h83_mwc.py`)

Le §91 avait nommé les générateurs **à retenue** comme échappant à
Berlekamp-Massey. Le §101 a confirmé mécaniquement qu'aucune des neuf sources
de balayage n'en contenait. C'était la dernière case nommée de la carte.

### L'équivalence MWC ≡ LCG

Un MWC de base `b` et de multiplicateur `a` est **exactement** un LCG
multiplicatif modulo `p = ab − 1` :

> état `(x, c)` → `z = x + b·c`, et alors `z_{i+1} = a·z_i (mod p)`.
>
> **Preuve.** `ab ≡ 1 (mod p)`, donc `b = a⁻¹`. Alors
> `a·z = a·x + a·b·c = a·x + c`, qui est exactement `z_{i+1}`. ∎

Vérifié sur 2 000 pas : `a = 18030`, `b = 2¹⁶`, `p = 1 181 614 079`, les deux
formulations coïncident.

**Ce que cela confirme — et n'ouvre pas.** Il vient `x_{i+1} = a·x_i + c_{i+1}
(mod b)`, la retenue vivant dans `[0, a)`. Pour un `a` grand, `c mod 16` n'est
**pas** constant : ni la signature du §80 ni le théorème du bit zéro du §100
n'y mordent — tous deux exigent un terme additif constant. Le §91 avait raison.
La prise n'est pas algébrique.

### La dissymétrie de MWC1616

V8 — le moteur JavaScript de Chrome et de Node — a utilisé MWC1616 pour
`Math.random` **jusqu'en 2016** :

```
state0 = 18030 * (state0 & 0xFFFF) + (state0 >> 16)
state1 = 36969 * (state1 & 0xFFFF) + (state1 >> 16)
r = (state0 << 16) + (state1 & 0xFFFF)        puis  u = r / 2³²
```

Soixante-quatre bits d'état. Mais les seize bits de **poids fort** de `r`
viennent de `state0` **seul**, et un numéro tiré par troncature ne lit que
ceux-là. `state1` ne pèse que sur la fraction.

| mesure | valeur |
|---|---|
| divergence sur 50 000 états | 35, soit **0,070 %** |
| tirage de vingt numéros exact | **98,6 %** du temps |

> **Soixante-quatre bits d'état, trente-deux bits de recherche.**

C'est la même dissymétrie que le §97 sur `java.util.Random`, pour une raison
différente : là le LCG était clos modulo 2²¹ ; ici c'est **l'échantillonneur**
qui ne lit qu'une moitié de l'état.

### Le balayage, et une fausse exclusion évitée de justesse

| tirage | échantillonneur | états testés | compatibles | sec |
|---|---|---|---|---|
| 1381023 | rejet | 4 294 967 296 | 0 | 352 |
| 1381023 | fy | 4 294 967 296 | 0 | 637 |
| 1381026 | rejet | 4 294 967 296 | 0 | 349 |
| 1381026 | fy | 4 294 967 296 | 0 | 553 |
| 1381028 | rejet | 4 294 967 296 | 0 | 293 |
| 1381028 | fy | 4 294 967 296 | 0 | 873 |

**0 état compatible**, témoin **2/2** sous les deux échantillonneurs.

Deux défauts ont été attrapés, et le second est le pire genre de bogue.

1. **La boucle qui ne finit pas.** `state0 = 0` est un point fixe de MWC1616 :
   le générateur y rend toujours le même numéro, et « tant que moins de vingt
   distincts » ne se termine **jamais**. Un balayage exhaustif rencontre ces
   états par construction. D'où `PLAFOND_MOTS = 400`.

2. **La fausse exclusion silencieuse.** Le préfiltre vectorisé calculait le
   numéro émis par `floor(u·80)+1`. Sous troncature c'est la **valeur** émise ;
   sous Fisher-Yates c'est un **indice**. Le filtre éliminait donc l'état
   **vrai** et aurait rendu « 0 compatible » — le bon verdict pour la mauvaise
   raison, indétectable dans le résultat. Seul le témoin l'a vu (`fy 0/1`).
   Corrigé par un émetteur Fisher-Yates vectorisé qui rejoue les écritures
   sans matérialiser le tableau.

### Ce que cela ferme

MWC1616, l'unique générateur à retenue jamais déployé à grande échelle, à état
**complet**, sous deux échantillonneurs, couverture **98,6 %**.

**Reste** : les MWC à base 2³² (Marsaglia), dont l'état fait 64 bits **sans**
la dissymétrie — leur sortie est brute, les deux moitiés comptent, 2⁶⁴ hors de
portée ; les SWB et AWC, mêmes raisons ; et tout ce que le §91 nomme déjà.

**Et une remarque de méthode.** Ce fichier ne doit rien à une famille de plus
essayée au hasard : il vient du §101, qui a **lu** les sources et constaté
qu'aucune ne contenait de MWC. La carte vérifiée a produit sa première
expérience.

**Registre : consigné.**

---

## 103. Le théorème de la fenêtre : la moitié du monde que le §99 ne pouvait pas voir (`h84_fenetre.py`)

### L'angle mort

Le §99 cherchait une **signature** : `(n_t − 1) = a(n_{t−p} − 1) + g(n_{t−q} − 1) + c (mod 16)`.
Elle repose sur le théorème du contenu (§94) : `16 | 80`, donc sous un
échantillonneur **modulo**, `(n−1) mod 16 = état mod 16`. La réduction est un
morphisme et la récurrence descend.

Sous un échantillonneur par **troncature** — `n = floor(u·K) + 1` — elle ne
descend pas. Le numéro lit les bits de **poids fort** de l'état. Aucune
congruence ne survit, et le balayage du §99 ne pouvait **rien** voir, quel que
soit le générateur.

Or la troncature est l'échantillonneur **dominant** dans la nature :
`Random.Next(80)` en .NET, `Math.floor(Math.random()*80)` en JavaScript,
`mt_rand($a,$b)` en PHP. Le §99 et le §100 couvrent le monde **modulo** ; le
monde **troncature** était entièrement ouvert. C'est la moitié de la carte.

### Le théorème

> Soit `s_t ∈ [0, M)` vérifiant `s_t = a·s_{t−p} + g·s_{t−q} + b (mod M)`,
> coefficients entiers et constante **quelconques**. Soit un échantillonneur
> par troncature publiant `m_t = floor((s_t/M)·K_t)`, `K_t` connu.
>
> Posons `x_t = s_t/M ∈ [0,1)` et `θ = b/M`. Alors
> `x_t ∈ [m_t/K_t, (m_t+1)/K_t)`, et la récurrence divisée par `M` donne
>
>     x_t − a·x_{t−p} − g·x_{t−q} ≡ θ   (mod 1)
>
> donc **θ appartient à un arc calculable, le même pour tout t**, de largeur
> `w_t = (R_t − L_t) + |a|(R_{t−p} − L_{t−p}) + |g|(R_{t−q} − L_{t−q})`. ∎

**Trois propriétés font tout l'intérêt.**

1. **Le module disparaît.** `M` ne figure nulle part dans l'arc. Le test vaut
   pour 2³¹−1, 2³², 2⁴⁸ ou un premier inconnu — **sans le connaître**.
2. **La constante disparaît aussi.** `b` n'entre que par `θ`, la même inconnue
   pour tout `t`. On ne la cherche pas : on demande si les arcs ont un **point
   commun**. Une retenue d'AWC ou un emprunt de SWB ne décalent l'arc que d'une
   unité — absorbés.
3. **Ni graine ni état.** Rien n'est reconstruit. C'est la **structure** qui
   répond.

### L'indice de Fisher-Yates est exactement récupérable

Sous Fisher-Yates, ce que le générateur produit est un **indice**,
`j = i + floor(u·(80−i))`, et le numéro publié est `a[j]` après `i` échanges.
Mais le tableau est **déterminé** par les émissions précédentes : on le rejoue,
et la position de chaque numéro publié y est unique. L'indice est donc
récupérable **exactement**, et avec lui l'encadrement de `u`. C'est la même
distinction indice/valeur qui, au §102, avait failli produire une fausse
exclusion.

### Le témoin, et le piège de la statistique

| générateur planté | retrouvé | score | couverture |
|---|---|---|---|
| Fibonacci retardé .NET (55,34) mod 2³¹−1 | **oui** | 140,3 | 105/105 |
| glibc `random()` TYPE_3 (31,3) mod 2³² | **oui** | 173,0 | 129/129 |
| SWB de Marsaglia (43,22) mod 2³² | **oui** | 156,7 | 117/117 |

Lags **et** signes exacts, sans module, sans graine, sans constante.

**Le piège, et il a été mesuré.** La couverture brute ne se compare pas d'une
hypothèse à l'autre : un lag de 2 aligne 170 contraintes, un lag de 55 en
aligne 25. Une couverture de 19 est dérisoire sur 170 arcs et **impossible**
sur 25. Avec la couverture brute, le nul plafonnait à **21** — au-dessus de la
couverture *pleine* d'un témoin à 25 contraintes : un vrai signal à lag 55
aurait été invisible. D'où le score `−log₁₀` d'une borne d'union,

    P(couverture ≥ c) ≤ n · C(n−1, c−1) · w^(c−1)

qui ne sert qu'à **ordonner** les hypothèses ; la calibration vient du nul.

### Le verdict

| | |
|---|---|
| hypothèses balayées | **54 560** (lags ≤ 100, 4 signes, 3 strides, 2 conventions) |
| meilleur score observé | 4,37 (stride 79, p=96, q=2, 7 arcs sur 12) |
| nul — 200 archives d'un générateur **parfait**, même motif d'observation | médiane 3,90, **max 6,25** |
| **p** | **0,2935 — conforme** |

Le nul n'est pas une permutation : c'est le générateur parfait, et le balayage
**entier** est refait sur chacune des 200 archives. La loi est celle du
**maximum**, ce qui absorbe les 54 560 hypothèses sans correction
supplémentaire.

### Ce que cela ferme

Toute récurrence à trois termes à coefficients ±1, **à n'importe quel
module**, sous troncature : Fibonacci retardé (.NET, glibc, Mitchell-Moore),
add-with-carry et subtract-with-borrow de Marsaglia. Cela comprend
`System.Random` et `random()` — les deux bibliothèques standard les plus
probables pour une plateforme achetée sur étagère.

**Reste** : les coefficients **grands** (un LCG a `‖λ‖₁ = 1 + a`) — c'est le
§104 ; les sorties **brouillées** ; le pas **variable**, où l'alignement des
lags se perd (§95).

**Ce que cela change dans la carte.** La colonne « échantillonneur » du §101
avait une case vide que personne n'avait vue : **modulo** couvert par le §99 et
le §100, **troncature** couverte par rien. Elle ne l'est plus.

**Registre : consigné.**

---

## 104. La réduction de réseau : les LCG que la fenêtre ne pouvait pas atteindre (`h85_reseau.py`)

### Pourquoi la fenêtre s'arrête

Le §103 contraint `θ` à un arc de largeur `‖λ‖₁ / K`. Il a de la force tant que
`‖λ‖₁` est **petit devant 80**.

| récurrence | `‖λ‖₁` | vue par la fenêtre |
|---|---|---|
| Fibonacci retardé, AWC, SWB | 3 | **oui** |
| LCG `s_t = a·s_{t−1} + b` | `1 + a` (= 25 214 903 918 pour Java) | **non** |

**Et les relations plus longues n'y changent rien.** Le réseau
`{λ : Σ λ_j a^j ≡ 0 (mod M)}` a pour déterminant `M` ; son plus court vecteur
vaut `M^{1/(k+1)}`, d'où `‖λ‖₁ ≈ (k+1)·M^{1/(k+1)}`, minimisé en `k+1 = ln M` :

| module | ordre optimal | `‖λ‖₁` minimal |
|---|---|---|
| 2³¹−1 | 21 | 58 |
| 2³² | 22 | 60 |
| 2⁴⁸ | 33 | **90** |
| 2⁶⁴ | 44 | 120 |

Il faudrait `‖λ‖₁` **petit** devant 80, pas seulement inférieur. Aucune
relation n'y parvient : **la fenêtre ne peut pas atteindre les LCG, et ce n'est
pas une question d'effort — c'est une borne.**

### On renverse le problème

Paramètres **fixés**, état **cherché** :

    s_t = a^t·s_0 + c_t (mod M),   s_t ∈ [A_t, B_t) de largeur M/K_t

Une seule inconnue, `T` contraintes à `log₂ K ≈ 6,3` bits chacune : il en faut
`log₂(M)/6,3`, soit **8 mots pour 2⁴⁸ et 11 pour 2⁶⁴**. Un tirage en donne
vingt. **Un seul tirage suffit.**

Reste à résoudre — c'est un vecteur le plus proche dans
`Λ = {y : y_t ≡ a^t·y_0 (mod M)}`, traité par LLL puis plan le plus proche de
Babai.

### Trois bogues, et ce que le témoin a coûté à chacun

Le témoin est passé de **0/15** à **15/15** en trois corrections, et aucune
n'était visible dans le résultat.

1. **La famille liée.** Écrit naïvement avec `s_0` pour inconnue, on obtient
   `T+1` vecteurs — `(a, a², …, a^T)` et les `M·e_t` — dans un espace de
   dimension `T`. Ce n'est **pas une base** : Gram-Schmidt rend un vecteur nul
   et LLL travaille sur du sable. Reparamétrer par `y_0 = a·s_0`, libre dans
   `Z`, donne la base triangulaire `w_0 = (1, a, …, a^{T−1})`, `w_t = M·e_t` —
   `T` vecteurs, déterminant `M^{T−1}`.
2. **`np.eye(dtype=object)` stocke des flottants.** Les coefficients de la
   transformation unimodulaire passent 2⁵³ ; sans entiers exacts, le témoin
   reste à 0/15.
3. **La base en flottants.** Les opérations de ligne y sont **inexactes** : le
   réseau **dérive**, d'autant plus que le module est grand. Java (2⁴⁸)
   passait ; MMIX, musl et PCG (2⁶⁴) échouaient encore à `T = 20`,
   c'est-à-dire avec 123 bits de contrainte pour 64 bits d'inconnue. Ce n'était
   pas un manque d'information, c'était de l'arrondi.

**Et pas de mise à l'échelle.** Les rayons `r_t = M/(2K_t)` ne varient que de
`K = 61` à `K = 80`, soit un facteur 1,31 : la métrique euclidienne ordinaire
est déjà la bonne à ce facteur près. Diviser par `r_t` forcerait des entrées
fractionnaires — précisément ce qui faisait dériver le réseau.

### Le résultat

**Témoin : 45/45** — quinze jeux de paramètres × trois essais, états retrouvés
**exactement** à partir d'un seul tirage de vingt numéros, modules de 2¹⁷ à
2⁶⁴, sans aucun balayage.

**Archive : 0 état compatible sur 4 050 résolutions** — quinze jeux de
paramètres × trois strides × deux conventions de Fisher-Yates × neuf tirages ×
cinq alignements, chacune suivie d'un **rejeu exact** des vingt numéros dans
l'ordre.

Fermé : `java.util.Random` et `drand48` (2⁴⁸), la glibc, MSVC, Borland, Turbo
Pascal, VAX, Numerical Recipes, cc65 (2³¹–2³²), minstd et RANDU, MMIX, PCG et
musl (2⁶⁴) — **à état complet, sous troncature**.

**Reste** : un LCG à paramètres **inventés**. L'attaque de Stern retrouve `a`
et `M` eux-mêmes, mais elle demande des dizaines de mots **consécutifs** et
l'archive n'en offre que vingt par tirage.

**Registre : consigné.**

---

## 105. Le théorème du préfixe : les bits hauts, et le seul chiffre qui dit quoi filmer (`h86_prefixe.py`)

### La symétrie manquante

Le dossier a deux attaques F2-linéaires, et elles regardent le même mot par les
deux bouts opposés.

| | bits lus | échantillonneur supposé | bits par mot |
|---|---|---|---|
| **§68** (`h61`) | les quatre **bas** — `NB = 4`, soit `v₂(80)` | **modulo** (théorème du contenu, §94) | 4 |
| **§105**, ici | les **hauts** | **troncature** | **4,48** |

Sous troncature, aucune congruence ne survit : **le §68 était aveugle par
construction** à l'échantillonneur dominant dans la nature. C'est exactement la
dissymétrie que le §103 a corrigée pour les récurrences, transposée aux
générateurs F2-linéaires.

### Le théorème

> Soit un mot de `W` bits, `u = mot/2^W`, et l'observation `m = floor(u·K)`.
> Les `j` premiers bits de `u` sont déterminés **si et seulement si**
>
>     floor(m·2^j / K)  =  floor( ((m+1)·2^j − 1) / K )
>
> et la valeur commune **est** le préfixe. Les `j` bits de poids fort du mot
> sont alors connus exactement, soit `j` équations F2-linéaires. ∎
>
> L'intervalle `[m/K, (m+1)/K)` a pour largeur `1/K` ; il tient dans une
> cellule dyadique de niveau `j` avec probabilité `1 − 2^j/K`. L'espérance vaut
> `Σ_j max(0, 1 − 2^j/K)`.

| `K` | bits déterminés en moyenne |
|---|---|
| 80 | 5,200 |
| 70 | 4,371 |
| 61 | 4,066 |
| **moyenne sur les vingt pas de Fisher-Yates** | **4,483** |

Soit **89,7 équations par tirage** — davantage que les quatre bits du §68, et
de l'autre côté du mot.

### Le témoin, et le piège du rang

| famille | état | rang | noyau | retrouvé |
|---|---|---|---|---|
| xorshift32 | 32 | 32 | 0 | **oui** |
| xorshift64 | 64 | 64 | 0 | **oui** |
| xorshift96 | 96 | 96 | 0 | **oui** |
| xorshift128 | 128 | 128 | 0 | **oui** |
| taus88 | 96 | **88** | 8 | **oui** |
| xoroshiro128 (brut) | 128 | 128 | 0 | **oui** |
| xoshiro128 (brut) | 128 | 128 | 0 | **oui** |
| xoshiro256 (brut) | 256 | 256 | 0 | **oui** |
| LFSR113 | 128 | **109** | 19 | **oui** (106 s) |
| WELL512a | 512 | 352 | 160 | *hors de portée* |

**9/9 sur les familles à portée**, avec quatre tirages consécutifs.

**Le piège.** Le rang n'atteint pas toujours la taille **nominale** de l'état,
et pas toujours faute d'équations : taus88 loge 88 bits utiles dans 96,
LFSR113 en loge 113 dans 128. Les bits morts ne peuvent **pas** être
déterminés — le rang sature en dessous du nominal quel que soit le nombre de
mots. Confondre « rang < nominal » avec « hors de portée » déclarerait
inatteignable une famille parfaitement atteignable ; c'est l'erreur exacte que
le §68 documente pour LFSR113. On distingue donc par la **dimension du noyau** :
petite, on l'énumère en code de Gray avec abandon au premier numéro — un pas de
générateur élimine 79 candidats sur 80, ce qui rend 2²² tenable.

### L'archive, et trois issues qu'il faut séparer

| famille | essais | exclus | cherchés | non testés | compatibles |
|---|---|---|---|---|---|
| xorshift32 | 30 | **30** | 0 | 0 | 0 |
| xorshift64 | 30 | **30** | 0 | 0 | 0 |
| xorshift96 | 30 | 15 | 15 | 0 | 0 |
| xorshift128 | 30 | 12 | 0 | 18 | 0 |
| taus88 | 30 | 18 | 12 | 0 | 0 |
| xoroshiro128 (brut) | 30 | 12 | 0 | 18 | 0 |
| xoshiro128 (brut) | 30 | 12 | 0 | 18 | 0 |
| xoshiro256 (brut) | 30 | 6 | 0 | 24 | 0 |
| LFSR113 | 30 | 12 | 0 | 18 | 0 |
| WELL512a | 30 | 0 | 0 | 30 | 0 |

**0 état compatible sur 300 systèmes.**

- **exclus (147)** : le système est **incompatible** — les préfixes observés ne
  peuvent venir d'**aucun** état de cette famille. C'est l'exclusion la plus
  forte du dossier : ni rejeu, ni seuil, ni null.
- **cherchés (27)** : l'état est déterminé à un petit noyau près, noyau
  parcouru et rejoué.
- **non testés (126)** : le noyau dépasse 22 dimensions — l'archive ne porte
  pas assez de mots consécutifs. **Non testé, pas exclu.**

Confondre les deux dernières lignes serait exactement la faute que le §101 a
trouvée dans la carte : une conclusion recopiée plus largement que sa source.

### Le corollaire utile — ce qu'il faudrait filmer

`4,48` bits par mot × 20 mots = **90 équations par tirage**. Un état de `n`
bits demande `n` équations indépendantes, donc

    tirages ordonnés CONSÉCUTIFS nécessaires  =  n / 90

| générateur | état | tirages consécutifs | dans l'archive ? |
|---|---|---|---|
| xorshift32 | 32 | 1 | oui |
| xorshift64 | 64 | 1 | oui |
| taus88 | 88 | 1 | oui |
| xorshift128 / LFSR113 | 128 | 2 | oui |
| xoshiro256 (brut) | 256 | 3 | oui |
| WELL512a | 512 | 6 | **non** |
| WELL1024a | 1024 | 12 | **non** |
| **MT19937** | **19 937** | **225** | **non** |

L'archive offre au mieux **4** tirages consécutifs.

**MT19937 mérite sa ligne.** Son tempérage est **F2-linéaire** : ses bits de
poids fort sont bien des formes linéaires de l'état, et rien dans le générateur
ne s'oppose à l'attaque. Ce qui manque n'est pas une idée, c'est **225 tirages
ordonnés consécutifs** — à quatre minutes par tirage, environ **quinze heures**
d'écran filmé, sans interruption du flux.

C'est le seul chiffre de tout le dossier qui transforme « on n'a rien trouvé »
en « voici ce qu'il faut collecter ».

### Ce qui reste

- les états trop grands pour 4 tirages consécutifs — WELL, MT19937 — et c'est
  une question de **données**, chiffrée ci-dessus, pas de méthode ;
- les sorties **additives** : xorshift128+, xoroshiro128+, xoshiro256+ — le
  `Math.random` de V8 depuis 2016. La somme finale n'est pas F2-linéaire, et
  une campagne SMT antérieure du dossier rendait `unknown` dès que la sortie
  descendait sous **douze** bits par mot ; la troncature n'en donne que 6,3 ;
- les sorties **multipliées ou brouillées** : xoshiro\*\*, PCG, splitmix64 ;
- le pas **variable** (rejet), qui casse l'alignement des mots — §95.

**Registre : consigné.**

---

## 106. Le préfixe porté aux 70 560 tirages : la troncature sur l'archive entière (`h87_bonus_prefixe.py`)

### Ce que le §105 laissait sur la table

Le théorème du préfixe donne 4,48 équations F2 par mot — mais il exige
l'**ordre d'émission**, pour reconstruire l'indice de Fisher-Yates. Et l'ordre
n'existe que sur **neuf** tirages : quatre-vingts mots consécutifs au mieux,
d'où les 126 systèmes déclarés « non testés » du §105.

L'archive, elle, compte **70 560** tirages. Triée, donc muette sur l'ordre.
Sauf qu'il reste un champ.

### Le fait structurel, relu par l'autre bout

Le `bonus` est **toujours** l'un des vingt numéros tirés — 70 560 sur 70 560,
là où l'indépendance en prédirait 17 640. Ce n'est pas un tirage
supplémentaire : c'est une **désignation**.

Le dossier connaissait ce fait, mais ne l'avait lu qu'à travers
l'échantillonneur **modulo** : le §89 prend `(bonus − 1) mod 16`, les quatre
bits **bas**, et le §100 étend la portée de ce calcul.

Sous **troncature**, la même donnée dit autre chose. Une désignation par indice
s'écrit `bonus = tirés[floor(u·20)]`, et le **rang** du bonus parmi les vingt
numéros **triés** — le nombre de numéros tirés qui lui sont inférieurs, donc
calculable depuis l'archive — vaut alors `floor(u·20)`. C'est une observation
de troncature, **exacte**, disponible sur les 70 560 tirages.

| | §105 | §106 |
|---|---|---|
| `K` | 61 à 80 | **20** |
| bits F2 par observation | 4,48 | **3,20** |
| observations | 80 mots | **70 560** |
| ordre d'émission requis | oui | **non** |
| stride | 20 (supposé) | **21, fixe** |

Moins par observation, sept mille fois plus d'observations. Et le stride est
**fixe** — vingt mots pour le Fisher-Yates, un pour l'indice : c'est
exactement ce que le §95 reprochait au bonus lu comme sortie brute sous rejet,
où le nombre de mots consommés varie.

La loi du rang est uniforme (χ² = 27,5 sur 19 ddl), ce qui est attendu sous
**toute** désignation raisonnable et ne discrimine rien.

### Le témoin, et une colonne qui compte

| famille | état | tirages | rang | noyau | retrouvé | ×4 tirages |
|---|---|---|---|---|---|---|
| xorshift32 | 32 | 34 | 32 | 0 | **oui** | |
| xorshift64 | 64 | 64 | 64 | 0 | **oui** | |
| xorshift96 | 96 | 94 | 96 | 0 | **oui** | |
| xorshift128 | 128 | 124 | 128 | 0 | **oui** | |
| taus88 | 96 | 94 | 88 | 8 | **oui** | *structurel* |
| xoroshiro128 (brut) | 128 | 124 | 128 | 0 | **oui** | |
| xoshiro128 (brut) | 128 | 124 | 128 | 0 | **oui** | |
| xoshiro256 (brut) | 256 | 244 | 256 | 0 | **oui** | |
| LFSR113 | 128 | 124 | **98** | 30 | *hors de portée* | *structurel* |
| **WELL512a** | **512** | 484 | 512 | 0 | **oui** | |

**WELL512a mérite d'être signalé** : 512 bits d'état reconstruits depuis les
seuls rangs du bonus. Le §105, avec ses quatre tirages ordonnés, ne pouvait pas
l'atteindre — il lui fallait six.

**La colonne « ×4 tirages » est là pour une raison.** Quand le rang plafonne
sous la taille de l'état, il faut savoir si c'est faute de données ou par
**structure**. On remesure donc à quatre fois plus de tirages. Mesure : le rang
de LFSR113 reste à **98** de 124 à 2 000 tirages — les bits hauts d'un mot sur
vingt-et-un n'atteignent qu'un sous-espace, et **aucune collecte n'y changera
rien**. Promettre le contraire serait exactement la faute que le §101 a trouvée
dans la carte. (LFSR113 reste exclu par le §105, qui l'atteint par l'ordre.)

### Le verdict

| | |
|---|---|
| systèmes | **4 580** (10 familles × 10 strides × tous les décalages internes) |
| **exclus par incompatibilité** | **4 580** |
| cherchés | 0 |
| non testés | 0 |
| **états compatibles** | **0** |

Tous les systèmes sont **incompatibles** : les rangs observés ne peuvent venir
d'aucun état d'aucune de ces familles, sous aucun des strides essayés. Pas un
seul ne s'est même hissé jusqu'à l'étape du rejeu.

### La limite, énoncée franchement

Ce fichier teste le **couple** « générateur + désignation par indice dans le
tableau **trié** ». Si la plateforme indexe le tableau dans l'**ordre
d'émission**, le rang calculé est une permutation aléatoire du vrai indice et
l'exclusion porte sur le couple, pas sur le générateur seul. C'est une limite
de portée, consignée comme telle.

**Reste** également MT19937 et WELL19937 : le budget de 3,20 bits par tirage
les met à portée en **6 230 tirages**, largement disponibles dans l'archive.
Ce qui bloque n'est pas la donnée mais le **coût de calcul** des formes
linéaires. La différence avec le §105 est entière : là, il manquait des
tirages ; ici, il manque des heures.

**Registre : consigné.**

---

## 107. Le pari séquentiel : mesurer la prédiction au lieu de l'exclure (`h88_pari.py`)

### Le reproche, et il est juste

Les §102 à §106 ferment des classes entières de générateurs. Ce sont des
théorèmes d'**exclusion** : ils disent ce qui ne produit *pas* les tirages,
jamais ce qui les produit. Un dossier de 58 068 hypothèses enregistrées, toutes
conformes, ne répond toujours pas à la seule question posée : **peut-on
gagner ?**

Ce fichier change d'instrument. Il ne teste pas une hypothèse : **il parie.**

### Ce que le §93 imposait, et que personne n'avait exploité

Le théorème de linéarisation donne, exactement et sans hypothèse,
`E[g] = Σ_j Δ^j g(0) · Σ_{|S|=j} π(S)`, et le barème réel annule `c₀`, `c₁` et
`c₂` aux grilles de 5, 6 et 7 numéros.

> **Le gain espéré ne dépend que des inclusions d'ordre ≥ 3.**

Les marginales — chauds, froids, retards, réseaux de neurones — n'apparaissent
pas dans la formule. Le §93 l'avait démontré ; **aucune expérience du dossier
n'avait ensuite cherché la structure du bon type.** C'est le trou que ce fichier
comble.

### Le théorème du pari

Tester 82 160 triplets dans un registre corrigé par Holm à `m = 58 068` serait
sans espoir : il faudrait `p < 10⁻⁶` par triplet. Alors on ne teste pas.

> **Théorème.** Soit `π₀ = P(S ⊆ D)` sous le tirage uniforme et
> `X_t(S) = 1[S ⊆ D_t]`. Pour `λ ∈ [0,1[`, la richesse
>
>     W_S(λ) = Π_t ( 1 + λ ( X_t(S)/π₀ − 1 ) )
>
> est une martingale positive d'espérance 1 sous le nul, et **tout mélange
> convexe à poids fixés d'avance en est une**. Par l'inégalité de Ville,
> `P( sup_t W_t ≥ 1/α ) ≤ α`. ∎

Une richesse de 20 vaut `p ≤ 0,05` — **quel que soit le nombre de
sous-ensembles pariés**, sans aucune correction de multiplicité : le mélange
est *une seule* martingale. C'est exactement l'instrument qu'il fallait après
58 068 tests corrigés.

**Forme close.** À `λ` fixé, `W_S = (1+λ(1/π₀−1))^k (1−λ)^{N−k}` ne dépend du
sous-ensemble que par son nombre de touches `k`. On tabule sur `k`, on intègre
sur `λ`, et le million et demi de quadruplets passe en vingt secondes.

**Et le prior sur `λ` n'est pas un détail.** Pour un excès relatif `ε` sur un
événement de probabilité `π₀`, la mise de Kelly optimale vaut `λ* ≈ ε·π₀`, soit
un millième ici. Un prior **uniforme** sur `[0,1]` n'y met qu'un millième de sa
masse : mesure faite, le seuil de détection passait de 20 % à 80 % d'excès.
Le prior **log-uniforme** donne un poids égal à chaque ordre de grandeur.

### Le résultat

| ordre | sous-ensembles | log₂ richesse | p (Ville) | meilleur seul |
|---|---|---|---|---|
| 2 | 3 160 | −1,025 | 1,000 | 3,33 |
| **3** | **82 160** | **−1,175** | **1,000** | 8,03 |
| 4 | 1 581 580 | −0,847 | 1,000 | 17,95 |

> Un parieur qui aurait misé sur les 82 160 triplets pendant 70 560 tirages
> aurait multiplié sa mise par **2⁻¹·¹⁸**.

La colonne « meilleur seul » montre l'écart avec le mélange : c'est exactement
ce que la correction de multiplicité aurait dû payer, et que le pari paie tout
seul.

### La puissance, et ce que « rien » veut dire

Une borne sans puissance ne vaut rien. On plante donc une anomalie sur un
triplet et on regarde à partir de quelle taille le **mélange** la voit.

| excès ε | touches | log₂ richesse | vu à 5 % |
|---|---|---|---|
| 0,10 | 1 077 | −1,07 | non |
| 0,15 | 1 126 | −1,02 | non |
| **0,20** | **1 175** | **+5,96** | **oui** |
| 0,25 | 1 224 | +20,22 | oui |
| 0,50 | 1 469 | +133,36 | oui |
| 1,20 | 2 154 | +746,41 | oui |

**Seuil mesuré : 20 % d'excès sur un seul triplet.** L'archive n'en montre
aucun.

### Les deux bornes se rejoignent

Grille de 5 numéros, barème du §93 (`c₃ = +6`, `c₄ = +12`, `c₅ = +240`) :

    E[g] = 6·C(5,3)·π₃ + 12·C(5,4)·π₄ + 240·π₅
         = 0,832522 + 0,183804 + 0,154782  =  1,171107

La part des **triplets** y pèse **71,1 %**. Un excès relatif `ε` sur les dix
triplets d'une grille monte donc le gain espéré de `0,711·ε`.

| | |
|---|---|
| excès **détectable** | **20 %** → +14,2 % de gain espéré |
| excès **nécessaire** pour revenir à l'équilibre (TRJ 50–65 %) | **76 % à 141 %** |

> **L'anomalie qu'il faudrait pour gagner est quatre à sept fois plus grosse
> que celle que nous saurions détecter — et nous n'en voyons aucune.**

*Le taux de retour au joueur n'a pas été mesuré dans ce dossier* ; la fourchette
50–65 % est l'ordre de grandeur usuel, et le chiffre en dépend. Il est donné
comme tel.

### Hors échantillon : le vrai test de prédiction

Le mélange est honnête mais aveugle — il ne **choisit** pas. Un parieur, lui,
choisirait. On coupe donc l'archive en deux, on retient les triplets les plus
favorisés sur la première moitié, et on parie dessus sur la seconde. La
sélection ne dépend que du passé : la richesse reste une martingale.

| top | touches 1ʳᵉ moitié | attendu | touches 2ᵈᵉ moitié | attendu | log₂ rich. |
|---|---|---|---|---|---|
| 10 | 577,10 | 489,52 | **479,70** | 489,52 | −1,328 |
| 100 | 563,76 | 489,52 | **491,40** | 489,52 | −1,200 |
| 1 000 | 547,57 | 489,52 | **490,17** | 489,52 | −1,174 |
| 10 000 | 526,27 | 489,52 | **489,51** | 489,52 | −1,115 |

Les triplets les plus chauds de la première moitié reviennent **exactement** à
l'attendu sur la seconde — les dix meilleurs passent même en dessous. C'est la
définition opérationnelle de « pas de structure » : la sélection ne survit pas
au passage à l'échantillon suivant.

### Ce que ce fichier apporte, et ce qu'il n'apporte pas

**Il apporte** une borne sur la **prédictibilité**, dans les unités que le
barème paie, et sans multiplicité à payer. Les §102 à §106 disent « telle
famille ne produit pas ces tirages ». Celui-ci répond à la question posée, pas
à une question voisine.

**Il n'apporte pas** de prédiction. La richesse ne monte pas, la sélection hors
échantillon ne survit pas, et les deux bornes — détectable, nécessaire — se
rejoignent dans le mauvais sens. C'est la forme la plus forte de réponse
négative qu'on puisse donner **sans** reconstituer l'état.

**Et le levier reste où il était** : dans l'**ordre d'émission** (§105 — 225
tirages consécutifs filmés mettent MT19937 à portée) et dans l'**angle
résiduel** de la roue (§92).

**Registre : consigné.**

---

## 108. Prédire le boost : la seule cible où une marginale vaut de l'argent (`h89_boost_predictif.py`)

### Pourquoi cette cible, et pourquoi elle avait été manquée

Le §93 a tué la prédiction numéro par numéro : le barème annule `c₀`, `c₁` et
`c₂`, donc une probabilité par numéro **n'entre pas** dans `E[g]`. Le §107 en a
tiré la conséquence et est allé chercher les triplets.

**Mais le boost n'est pas un numéro.** C'est un **multiplicateur** :

    gain = boost × g(h)      donc     E[gain] = E[boost] × E[g]

Il entre **linéairement**. Une marginale sur le boost est donc exactement du bon
type, et un edge de δ % vaut δ % de taux de retour en plus — sans passer par le
barème, sans hypothèse sur les inclusions.

> **C'est le seul endroit de tout le dossier où un prédicteur scalaire vaut de
> l'argent.**

Le §90 a mesuré la loi du boost. Le §92 a démontré que la roue est cosmétique.
Ni l'un ni l'autre n'a essayé de le **prédire**.

| boost | effectif | probabilité |
|---|---|---|
| 1 | 36 122 | 0,5119 |
| 2 | 16 791 | 0,2380 |
| 3 | 10 626 | 0,1506 |
| 4 | 3 525 | 0,0500 |
| 5 | 1 739 | 0,0246 |
| 10 | 1 757 | 0,0249 |

`E[boost] = 2,0117` sur 70 560 tirages.

**Et la question est actionnable** : le joueur décide **avant** le tirage. On ne
prédit donc le boost du tirage `t` qu'à partir des tirages `1..t−1`,
strictement — aucun regard sur le présent, aucun ajustement rétrospectif.

### L'instrument

> **Théorème.** Soient `P₀` et `P₁` deux assignations de probabilité
> **séquentielles** — deux prédicteurs qui, à chaque `t`, rendent une loi sur
> `x_t` au vu du seul passé. Alors
>
>     W_N = Π_t  P₁(x_t | passé) / P₀(x_t | passé)
>
> vérifie `E_{P₀}[W_N] = Σ_x P₁(x_{1:N}) = 1` : c'est une martingale positive
> sous `P₀`, et Ville s'applique. ∎

Un **mélange** de prédicteurs à poids fixés d'avance est encore une assignation
séquentielle, donc encore une martingale : **douze modèles d'un coup, et la
barre ne bouge pas.** `P₀` est la marginale estimée en ligne (Dirichlet 0,5),
optimale sous le nul « le boost est i.i.d. de loi inconnue ».

### Les douze modèles

| modèle | contextes | bits/tirage | log₂ richesse |
|---|---|---|---|
| marginale (référence) | 1 | 0 | 0 |
| boost précédent | 6 | −0,001732 | −122 |
| deux boosts précédents | 36 | −0,008179 | −577 |
| heure du jour | 24 | −0,005596 | −395 |
| jour de la semaine | 7 | −0,002182 | −154 |
| jour × heure | 168 | −0,029453 | −2 078 |
| rang dans la journée | 288 | −0,043517 | −3 071 |
| écart depuis boost ≥ 5 | 16 | −0,004701 | −332 |
| boosts élevés sur 20 | 6 | −0,001533 | −108 |
| somme du tirage précédent | 12 | −0,001783 | −126 |
| rang du bonus précédent | 20 | −0,006262 | −442 |
| boost préc. × heure | 144 | −0,022592 | −1 594 |

**Mélange : log₂ richesse = −3,585.** Pas un seul modèle ne bat la marginale ;
tous perdent exactement ce que coûte l'estimation de leurs contextes.

### La puissance

On fabrique une archive où le boost dépend **vraiment** de l'heure — une masse
`ε` déplacée de la valeur 1 vers la valeur 10, six heures par jour.

| ε | E[boost] creux | E[boost] pointe | log₂ richesse | vu à 5 % |
|---|---|---|---|---|
| 0,02 | 2,0117 | 2,1917 | −299 | non |
| **0,05** | 2,0117 | **2,4617** | **+121** | **oui** |
| 0,10 | 2,0117 | 2,9117 | +1 163 | oui |

> **Toute promotion administrative valant plus de ~+22 % sur `E[boost]` pendant
> six heures par jour aurait été vue. Il n'y en a aucune.**

### La stratégie, testée hors échantillon

Un rapport de vraisemblance ne se dépense pas. La question du joueur est
autre : *existe-t-il un sous-ensemble de tirages, reconnaissable à l'avance, où
`E[boost]` soit plus élevé ?* On apprend sur la première moitié, on sélectionne
les contextes favorables, on mesure le boost **réalisé** sur la seconde.

| modèle | joués | E[b] appris | **E[b] réalisé** | edge | z |
|---|---|---|---|---|---|
| boost précédent | 28 237 | 2,0347 | 2,0044 | −0,37 % | −0,76 |
| deux boosts précédents | 21 514 | 2,0864 | 2,0148 | +0,15 % | +0,27 |
| heure du jour | 20 334 | 2,0357 | 1,9960 | −0,78 % | −1,37 |
| jour × heure | 17 714 | 2,0845 | 2,0091 | −0,13 % | −0,21 |
| rang dans la journée | 16 949 | **2,1125** | 2,0145 | +0,14 % | +0,22 |
| boosts élevés sur 20 | 15 171 | **2,1185** | 1,9978 | −0,69 % | −1,05 |
| somme du tirage précédent | 15 485 | 2,0232 | **2,0304** | **+0,93 %** | **+1,42** |
| boost préc. × heure | 18 970 | **2,1108** | 2,0024 | −0,46 % | −0,79 |

Regarder la colonne « appris » suffit à voir le piège : plusieurs modèles
montent à 2,11 — soit +5 % — en apprentissage, et **retombent tous à 2,00 en
test**. Meilleur edge réalisé : **+0,93 %, z = +1,42**.

L'écart-type du boost vaut 1,636 ; sur quelques milliers de tirages joués,
l'erreur type sur `E[boost]` est de 0,030, soit **1,49 %** de la moyenne. Un
edge inférieur à cela n'est pas un edge : c'est du bruit — et tous les modèles
y restent.

### Ce que cela vaut

C'est, avec le §107, la seconde expérience du dossier qui **prédit** au lieu
d'exclure — et la seule qui vise une quantité dont l'edge se convertit
**directement** en taux de retour, sans passer par le barème.

Le verdict est net : sur 70 560 tirages, douze modèles, aucune multiplicité à
payer, **le boost n'est pas prédictible à partir du passé**, et la puissance dit
que toute structure administrative valant plus de +22 % aurait été vue.

**Registre : consigné.** `m = 58 070`, zéro significatif.

---

## 109. Le prédicteur : de l'état reconstitué au tirage annoncé (`h90_prediction.py`)

### Ce qui manquait, et c'est gênant

Le dossier comptait huit attaques qui reconstituent un **état**. Aucune n'avait
jamais **prédit un tirage**. Tous les témoins s'arrêtaient à « l'état planté est
retrouvé » — jamais à « voici les vingt numéros du tirage suivant, dans
l'ordre », puis vérification.

La différence n'est pas rhétorique. *Retrouver l'état* est une propriété de
l'attaque ; *annoncer le tirage d'après et avoir raison* est la chose qu'on
demandait depuis le début.

### Le théorème de prédiction

> **Théorème.** Soit un générateur **déterministe** de transition connue, dont
> l'état est identifié à l'instant `t`. Alors tous les tirages futurs sont
> calculables exactement : la prédiction n'est pas probabiliste, c'est une
> **évaluation**.
>
> **Corollaire.** « Peut-on prédire ? » se réduit **entièrement** à « peut-on
> identifier ? », et le nombre de tirages ordonnés nécessaires se lit dans le
> budget d'information : `n/89,7` pour un état F2-linéaire de `n` bits (§105),
> `log₂(M)/126` pour un LCG de module `M` (§104). Il n'y a pas de troisième
> quantité. ∎

**Et voici ce qui sépare radicalement cette voie des §107–108 :** une fois
l'état connu, **l'horizon est infini**. Le pari sur les triplets et la
prédiction du boost mesuraient des edges qui s'évanouissent dans le bruit ; ici
il n'y a pas d'edge — il y a une **certitude**, ou rien du tout.

### La démonstration

On plante un état, on montre au prédicteur `d` tirages consécutifs, on lui
demande **le suivant**, et on compare les vingt numéros dans l'ordre.

| générateur | d minimal | tirage +1 | horizon 10 |
|---|---|---|---|
| LCG java.util.Random / drand48 | **1** | **exact** | 10/10 |
| LCG glibc TYPE_0 | **1** | **exact** | 10/10 |
| LCG ANSI C / MSVC | **1** | **exact** | 10/10 |
| LCG Borland / Delphi | **1** | **exact** | 10/10 |
| LCG Turbo Pascal | **1** | **exact** | 10/10 |
| LCG VAX MTH$RANDOM | **1** | **exact** | 10/10 |
| xorshift32 | **1** | **exact** | 10/10 |
| xorshift64 | **1** | **exact** | 10/10 |
| xorshift96 | **1** | **exact** | 10/10 |
| xorshift128 | 2 | **exact** | 10/10 |
| taus88 | **1** | **exact** | 10/10 |
| xoroshiro128 (brut) | 2 | **exact** | 10/10 |
| xoshiro128 (brut) | 2 | **exact** | 10/10 |
| xoshiro256 (brut) | 3 | **exact** | 10/10 |
| LFSR113 | 2 | **exact** | 10/10 |

> **15/15 générateurs dont le tirage suivant est annoncé exactement — vingt
> numéros, dans l'ordre — et 15/15 dont les dix tirages suivants le sont
> aussi.**

C'est la première fois du dossier qu'un tirage est **prédit** et vérifié. Et le
prix en données est dérisoire : **un seul tirage ordonné** suffit pour tout LCG
publié et pour les F2-linéaires jusqu'à 96 bits ; deux à trois au-delà.

### Sur l'archive réelle

| bloc | tirages | générateur identifié |
|---|---|---|
| 1381023 | 1 | aucun |
| 1381026 | 1 | aucun |
| 1381028 | 1 | aucun |
| 1381030–1381031 | 2 | aucun |
| 1381256–1381259 | 4 | aucun |

**0 générateur identifié.** Le prédicteur qui annonce 15 loteries plantées sur
15 n'annonce rien ici. Ce n'est pas un échec de méthode : c'est que le
générateur de cette loterie n'est pas dans la classe couverte, et le §105
chiffre exactement ce qu'il faudrait pour l'élargir.

### L'outil

    python3 lab/experiments/h90_prediction.py mes_tirages.csv

Colonnes `id, o1..o20` dans l'**ordre d'émission**. Il rend soit « aucun », soit
le générateur, l'état, et **les vingt numéros du tirage suivant**.

| état à identifier | tirages ordonnés consécutifs |
|---|---|
| 32 bits | 1 |
| 128 bits | 2 |
| 256 bits | 3 |
| 512 bits | 6 |
| MT19937 (19 937 bits) | 225 |

**Registre : inchangé.** Ce fichier ne teste rien de neuf sur l'archive — il
rejoue les exclusions déjà consignées aux §103–§106. Les consigner une seconde
fois gonflerait `m` sans rien mesurer de plus.

---

## 110. Le flux unique, et le théorème du confinement (`h91_flux_unique.py`)

Deux apports, et **le premier est une correction de mon propre travail**.

### I. Le flux unique — une erreur de découpage, pas une limite de données

Le §105 a construit un système linéaire **par bloc** de tirages consécutifs.
L'archive ordonnée compte cinq blocs — 1, 1, 1, 2 et 4 tirages — donc au mieux
`4 × 89,7 = 359` équations, et une portée de 359 bits d'état. D'où ses **126
systèmes « non testés »**.

C'était une erreur de **découpage**. Sous l'hypothèse d'un flux continu à stride
constant, le mot qui engendre le pas `k` du tirage d'identifiant `i` occupe la
position

    (i − i₀) · stride + k

**parfaitement connue**. Les tirages absents laissent des cases vides ; ils ne
rompent pas l'alignement. Les neuf tirages contraignent donc **un seul état** :

> **portée : 359 bits → 807 bits, sans une seule donnée de plus.**

L'étendue du flux vaut 237 tirages, soit 4 740 mots au stride 20, dont 180
observés.

**Le témoin devait vérifier que l'alignement traverse vraiment les trous** — si
non, j'aurais conclu « exclu » sur une erreur de ma part. On plante donc un
état, on engendre le flux entier, on n'en garde que les tirages aux
identifiants **réels** de l'archive, trous compris.

| famille | état | équations | rang | noyau | retrouvé |
|---|---|---|---|---|---|
| xorshift32 | 32 | 806 | 32 | 0 | **oui** |
| xorshift64 | 64 | 796 | 64 | 0 | **oui** |
| xorshift96 | 96 | 833 | 96 | 0 | **oui** |
| xorshift128 | 128 | 786 | 128 | 0 | **oui** |
| taus88 | 96 | 806 | 88 | 8 | **oui** |
| xoroshiro128 (brut) | 128 | 820 | 128 | 0 | **oui** |
| xoshiro128 (brut) | 128 | 782 | 128 | 0 | **oui** |
| xoshiro256 (brut) | 256 | 837 | 256 | 0 | **oui** |
| LFSR113 | 128 | 819 | 109 | 19 | **oui** |
| **WELL512a** | **512** | 788 | 512 | 0 | **oui** |

**10/10 états retrouvés à travers les trous.** Un identifiant manquant est un
décalage connu, pas une rupture.

### Le résultat sur l'archive

| | §105 (par bloc) | §110 (flux unique) |
|---|---|---|
| systèmes | 300 | **120** |
| exclus par incompatibilité | 147 | **120** |
| **non testés** | **126** | **0** |
| états compatibles | 0 | **0** |

**Le trou est comblé.** Tout le catalogue F2-linéaire, WELL512a compris, est
désormais exclu — à six strides et deux conventions — sans qu'aucun système ne
reste hors de portée.

### II. Le théorème du confinement

Les neuf tirages ordonnés sont une goutte ; l'archive en compte 70 560, triée.
Que peut-on en tirer **sans l'ordre** ?

> **Théorème du confinement.** Sous Fisher-Yates, au pas `k`, la valeur émise
> vaut `a[j_k]`, où `a` ne diffère de l'identité qu'aux `k` positions déjà
> échangées. Donc `valeur = j_k + 1` sauf si `j_k` a déjà été touché, ce qui
> arrive avec probabilité au plus `k/80`. Si `S` désigne l'**ensemble** non
> ordonné des vingt numéros,
>
>     P( j_k + 1 ∈ S ) ≥ 1 − k/80
>
> et au pas 0 l'inclusion est **exacte** — le tableau est encore l'identité. ∎

Chaque mot est donc confiné à vingt intervalles sur quatre-vingts, soit **2 bits
sans connaître l'ordre**. Sur 70 560 tirages et vingt mots : **2,8 millions de
bits disponibles**, pour un état qui en fait 128.

**L'information est là. Elle est pourtant hors d'atteinte** — et voici la
démonstration.

> **Corollaire de branchement.** Le confinement ne détermine **aucun** bit du
> mot : une réunion de vingt intervalles sur quatre-vingts n'est jamais
> contenue dans une moitié dyadique — il faudrait que les vingt numéros soient
> tous sous 41 ou tous au-dessus, ce qui arrive avec probabilité
> `2·C(40,20)/C(80,20) = 7,8·10⁻⁸`, soit jamais.
>
> Pour obtenir des équations il faut donc **brancher** sur la valeur — vingt
> choix, `log₂20 = 4,32` bits — et chaque valeur supposée rend 4,48 équations
> (§105). Le bilan par mot vaut **+0,16 bit**.
>
> Mais **aucun branchement ne peut être élagué tant que le système est
> sous-déterminé** : l'incompatibilité n'apparaît qu'au-delà de `n` équations.
> L'arbre atteint donc `20^(n/4,48)` nœuds **avant** de commencer à se
> contracter. ∎

| état `n` | mots requis | nœuds d'arbre |
|---|---|---|
| 32 | 7,1 | 2³¹ |
| 64 | 14,3 | 2⁶² |
| **128** | 28,6 | **2¹²³** |
| 256 | 57,1 | 2²⁴⁷ |

C'est la démonstration **quantitative** de ce que tout le dossier constatait
sans le dire : l'archive triée contient largement assez d'information — 2,8
millions de bits pour 128 — et elle reste hors d'atteinte par manque de
**levier**, pas par manque de bits.

> **Le levier, c'est l'ordre.** Il change 4,32 bits de branchement en 4,48 bits
> d'équations **gratuites**. Et c'est là la valeur exacte d'un tirage ordonné :
> il ne vaut pas 89,7 bits de plus qu'un tirage trié — il vaut la différence
> entre **2¹²³ nœuds et un pivot de Gauss**.

### La règle générale qui en sort

Ce qui compte n'est **pas** le nombre de tirages **consécutifs** mais le nombre
de tirages **ordonnés**, quelle que soit leur dispersion. Le §105 demandait 225
tirages consécutifs pour MT19937 ; il en faut 225 **ordonnés**, et ils peuvent
être pris n'importe où — c'est une contrainte de collecte entièrement
différente, et bien plus facile.

**Registre : consigné.** `m = 58 071`, zéro significatif.

---

## 111. Rejet et troncature : la case vide de la carte (`h92_rejet_troncature.py`)

### La case que personne n'avait vue

La carte du dossier a deux axes : l'**échantillonneur** et le **pas**.

| | pas **fixe** (Fisher-Yates) | pas **variable** (rejet) |
|---|---|---|
| **modulo** (`s mod 80`) | §68, §89, §99, §100 | §96 |
| **troncature** (`u·80`) | §103, §104, §105, §110 | *— vide —* |

Or la cellule vide est celle de l'implémentation **la plus naïve qui soit** :

    do { n = Math.floor(Math.random()*80) + 1 } while (déjà_vu(n));

Trois lignes de JavaScript, ce qu'écrit quiconque n'a jamais entendu parler de
Fisher-Yates — et aucune attaque du dossier ne la couvrait.

### Le rejet donne plus, et coûte l'alignement

Sous rejet, le numéro émis vaut **exactement** `floor(u·80)+1` : le
dénominateur reste 80 pour les vingt numéros, là où Fisher-Yates le fait
descendre de 80 à 61.

| échantillonneur | bits/numéro | équations/tirage |
|---|---|---|
| Fisher-Yates (K = 80…61) | 4,48 | 89,7 |
| **rejet (K = 80)** | **5,20** | **104,0** |

Un seul tirage détermine donc tout état de **104 bits ou moins** — *si l'on
sait où sont les rejets*. Or le nombre de mots consommés vaut `20 + r`, `r`
inconnu. C'est la leçon du §95.

### Le théorème de l'arbre de rejet

> **Théorème.** L'ordre étant **connu**, on ne branche que sur les **rejets** :
> il y a `C(20+r, r)` motifs à `r` rejets, et l'incompatibilité n'apparaît
> qu'après `n/5,20` numéros. L'arbre à explorer avant tout élagage compte donc
>
>     C( n/5,20 + r , r )  nœuds
>
> et non `20^(n/4,48)` comme dans le cas **trié** du §110. ∎

| état `n` | numéros requis | nœuds (r ≤ 10) |
|---|---|---|
| 32 | 6,2 | 3 003 |
| 64 | 12,3 | 646 646 |
| 96 | 18,5 | 13 123 110 |
| 128 | 24,6 | 183 579 396 |

> **Le rejet coûte un facteur combinatoire ; le tri coûte un facteur
> exponentiel.** C'est la valeur exacte de l'ordre, chiffrée.

### Le témoin, et les nœuds mesurés

| famille | état | rejets réels | nœuds | retrouvé |
|---|---|---|---|---|
| xorshift32 | 32 | [1] | 10 105 | **oui** |
| xorshift64 | 64 | [1] | 423 482 | **oui** |
| xorshift96 | 96 | [0] | > 4 000 000 | non (plafond) |
| taus88 | 96 (88 utiles) | [5] | 3 165 538 | **oui** |

**3/4**, motif de rejets inconnu du solveur. Les comptes de nœuds suivent la
prédiction du théorème à un petit facteur près.

### L'archive

| famille | essais | exclus | débordés | compatibles |
|---|---|---|---|---|
| xorshift32 | 9 | **9** | 0 | 0 |
| xorshift64 | 9 | **9** | 0 | 0 |
| xorshift96 | 9 | 0 | 9 | 0 |
| taus88 | 9 | 3 | 6 | 0 |

**0 état compatible sur 36 systèmes** — 21 exclus par incompatibilité, 15
débordés au plafond de 4 millions de nœuds.

### Une erreur que le rejeu a rattrapée, et il faut la raconter

La première version de ce fichier a consigné **15 104 « états compatibles »**
pour taus88. Ce n'était pas une découverte : c'était un **défaut de code**.

`explore` ajoutait chaque élément du noyau à la liste des solutions **sans
jamais rejouer le tirage**. Or les équations ne portent que sur les bits de
**préfixe** ; une direction du noyau peut les laisser intactes et changer le
numéro émis — c'est exactement ce dont la docstring de `kernel_basis` du §68
met en garde. taus88 loge 88 bits utiles dans 96 : son noyau fait 8
dimensions, soit 256 candidats par feuille, dont **aucun** ne reproduit le
tirage.

Correction : vérification par **rejeu complet** de chaque candidat. Résultat :
**0**. La ligne fautive a été retirée du registre par `lab.dedupe()`, qui ne
garde que la dernière consignation de chaque identifiant.

> Le rejeu est la seule chose qui distingue une solution d'une coïncidence
> algébrique. C'est la troisième fois de la session qu'un témoin ou un rejeu
> attrape une erreur invisible dans le résultat (§102, §104, §111) — et la
> seule fois où elle avait déjà atteint le registre.

### Ce que cela ferme

La carte n'a plus de case vide sur ces deux axes. Et le théorème qui reste
vaut au-delà de ce dossier :

| régime | coût |
|---|---|
| ordre connu, pas connu | **pivot de Gauss** |
| ordre connu, pas inconnu | arbre **combinatoire**, `C(n/5,2 + r, r)` |
| ordre inconnu | arbre **exponentiel**, `20^(n/4,48)` |

Trois régimes, trois coûts, et la frontière entre le deuxième et le troisième
est ce qui sépare une attaque possible d'une attaque impossible.

**Registre : consigné.** `m = 58 072`, zéro significatif.

---

## 112. Le `Math.random` de V8 : la case que j'avais déclarée sans espoir (`h93_v8.py`)

### Ce que j'ai affirmé, et qui était faux

J'ai écrit dans ce dossier — plusieurs fois, et jusque dans une réponse où je
chiffrais mes chances de succès — que `Math.random` de V8 depuis 2016 était
**`xorshift128+`**, donc à sortie **additive**, donc hors d'atteinte des §103 à
§111. Je l'ai classé dans la case « aucune quantité de données n'y change
rien ».

**C'est faux.** V8 a laissé tomber le « + » :

```cpp
void XorShift128(uint64_t* state0, uint64_t* state1) {
  uint64_t s1 = *state0;  uint64_t s0 = *state1;
  *state0 = s0;
  s1 ^= s1 << 23;  s1 ^= s1 >> 17;  s1 ^= s0;  s1 ^= s0 >> 26;
  *state1 = s1;
}
double ToDouble(uint64_t state0) {
  return bit_cast<double>((state0 >> 12) | 0x3FF0000000000000) - 1;
}
```

La sortie est `ToDouble(state0)` — **l'état lui-même**, pas une somme. C'est un
xorshift128 à deux mots de 64 bits, décalages 23/17/26, **purement
F2-linéaire**. Et ce n'est **pas** le xorshift128 de Marsaglia du catalogue du
§68 (quatre mots de 32 bits, décalages 11/8/19). Personne ne l'avait testé.

> Et c'est le générateur le plus probable pour une plateforme web.

### La validation : contre V8, pas contre ma mémoire

Le fichier ne me croit pas sur parole — il lance `node` :

| | |
|---|---|
| valeurs de `Math.random()` lues depuis node v22.22.2 | 192 |
| état reconstitué à partir de | **4** d'entre elles |
| `state0` | `0xa9ab4a81b6394e10` |
| `state1` | `0x3b709ca7e1457b7c` |
| **sorties reproduites** | **192/192 — modèle confirmé** |

Un détail qui a failli me tromper : les 12 bits bas de `x₂` **n'influencent pas
du tout** les 52 bits hauts de `x₃`. Un test à trois termes laisse donc 4 096
candidats équivalents et j'en avais retenu un mauvais. Il faut un **quatrième**
terme pour les fixer.

### Le théorème du cache

V8 ne génère pas un nombre à la fois : il remplit un cache de 64 **en avant**
et le consomme **en arrière** (`return cache[--index]`).

> **Théorème du cache.** L'application qui envoie l'indice applicatif `j` sur
> l'indice générateur
>
>     g(j) = 64·(j // 64) + 63 − (j mod 64)
>
> est une **involution**, connue, et **indépendante de l'état**. Les équations
> de préfixe (§105) se transportent donc telles quelles : seule l'indexation
> change. ∎

**Un renversement de cache ne protège rien — mais il fait échouer
silencieusement toute attaque qui suppose un flux en avant.** C'est peut-être
pour cela que tout revenait vide.

### Le résultat

**Témoin : 3/3** — états de V8 reconstitués sur le motif d'identifiants réel de
l'archive, trous **et** renversement de cache compris, ~810 équations pour 128
bits d'état. Deux tirages ordonnés auraient suffi ; j'en ai neuf.

| stride | essais | **exclus** | poussés au rejeu | compatibles |
|---|---|---|---|---|
| 20, 21, 22, 79, 80, 81 × 2 conventions × 64 phases | **768** | **768** | 0 | **0** |

**0 état compatible sur 768 systèmes**, tous exclus par incompatibilité du
système linéaire — la forme d'exclusion la plus forte du dossier.

### Ce que cela change

**C'est une correction de ma part, et la leçon est celle du §101.** J'ai passé
la session à classer les « sorties additives » hors d'atteinte, en y mettant le
générateur le plus déployé de la planète. Il n'y était pas.

> Une famille qu'on croit connaître mérite d'être **lue dans le code**. Le §101
> l'avait établi pour la carte de couverture ; je viens de commettre exactement
> la même faute sur une bibliothèque — et il a fallu `node` pour me le prouver.

**Reste vraiment additif**, cette fois vérifié :

- **SpiderMonkey** (Firefox) et **JavaScriptCore** (Safari), qui utilisent bien
  `xorshift128+` avec la somme ;
- les **CSPRNG** : `crypto.getRandomValues`, `random_int` de PHP, `/dev/urandom` ;
- les sorties **multipliées** : PCG, splitmix64, xoshiro\*\*.

**Registre : consigné.** `m = 58 073`, zéro significatif.

---

## 113. Deux mots par numéro : l'hypothèse que toutes mes attaques faisaient sans le dire (`h94_mots_par_numero.py`)

### L'hypothèse cachée

Les §103 à §112 supposent tous, **sans jamais l'écrire**, qu'un numéro coûte
**un** mot de générateur. Le stride vaut 20, 21, 79 ou 80, et le mot du pas `k`
du tirage `d` occupe la position `(d − d₀)·stride + k`.

Ce n'est pas vrai en général, et la vérification tient en trois lignes de Java,
exécutées sur cette machine :

```
new Random(424242L).nextDouble()        →  0.35987869081344237
deux next() consécutifs                 →  1545667241, 508083266
(((w1>>>6) << 27) + (w2>>>5)) · 2⁻⁵³    →  IDENTIQUE
```

`nextDouble()` consomme **deux** mots de 32 bits — et il en va de même de toute
implémentation qui fabrique un double 53 bits depuis un générateur 32 bits.

> **Un tirage de vingt numéros coûte alors quarante mots, pas vingt.**

Et une attaque à stride faux n'échoue pas bruyamment : elle rend
« incompatible », et je consigne « exclu ». C'est le piège du renversement de
cache du §112 sous une autre forme.

### Le théorème du premier mot

> Si `u = (a·2²⁷ + b)·2⁻⁵³` avec `a = next(26)` et `b = next(27)`, alors
> `|u − a/2²⁶| < 2⁻²⁶`, tandis que l'intervalle de troncature a pour largeur
> `1/K ≥ 1/80`. Donc `floor(u·K)` ne dépend que de `a`, sauf à moins de
> `K·2⁻²⁶ < 1,2·10⁻⁶` près.
>
> Les équations de préfixe portent donc sur le **premier** mot de la paire ; le
> second n'est **jamais** observé. ∎

**Le budget d'information est inchangé** — 89,7 équations par tirage, portée 807
bits. Seule l'**indexation** change : `position = (d − d₀)·stride + k·m`.

### Le témoin

| famille | m = 1 | m = 2 |
|---|---|---|
| xorshift32, xorshift64, xorshift96, xorshift128 | oui | **oui** |
| taus88, xoroshiro128, xoshiro128, xoshiro256 | oui | **oui** |
| LFSR113, WELL512a, **V8 Math.random** | oui | **oui** |

**21/21 états retrouvés.** L'indexation à deux mots par numéro tient.

### L'archive

| | |
|---|---|
| systèmes (11 familles × 12 strides × 2 conventions) | **264** |
| **exclus par incompatibilité** | **264** |
| non testés | 0 |
| **états compatibles** | **0** |

### Ce que cela change

**Trois pièges silencieux, trois sections.** Le §112 a montré qu'un cache
renversé fait échouer une attaque sans bruit ; celle-ci montre qu'un nombre de
mots par numéro mal deviné fait exactement pareil. Dans les deux cas l'attaque
rend « incompatible » et le registre enregistre « exclu ».

> **Une exclusion ne vaut que pour le modèle de consommation testé, et ce modèle
> doit être énuméré explicitement — pas supposé.**

Le dossier compte désormais quatre axes de modèle :

| axe | valeurs | où |
|---|---|---|
| échantillonneur | modulo / troncature | §94, §105 |
| pas | fixe / variable | §95, §111 |
| **consommation** | **un / deux mots par numéro** | **§113** |
| ordre de service | direct / cache renversé | §112 |

Rien ne garantit qu'il n'y en ait pas un cinquième.

**Registre : consigné.** `m = 58 074`, zéro significatif.

---

## 114. MT19937 à état complet : la cible que seul le calcul bloquait (`h95_mt19937.py`, `tools/f2solve.c`)

### Ce que le §106 avait laissé

Le §106 avait montré que le **rang du bonus** parmi les vingt numéros triés est
une observation de troncature **exacte**, disponible sur toute l'archive, à
stride **fixe**, et **sans jamais avoir besoin de l'ordre d'émission**. Il rend
3,20 équations F2 par tirage. Sa conclusion, mot pour mot :

> « MT19937 et WELL19937. Le budget de 3,20 bits par tirage les met à portée en
> 6 230 tirages, largement disponibles — c'est le **coût de calcul** des formes
> linéaires qui bloque, pas la donnée. »

Ce fichier fournit les heures. Et l'enjeu est le plus gros du dossier :

> **MT19937 est le générateur de PHP (`mt_rand`), de Python (`random`), de Ruby
> (`Random`) et de C++ (`std::mt19937`).**

### Où était vraiment le mur

**Pas dans les formes linéaires.** Les 19 937 formes se propagent par la
récurrence du twist en **dix secondes** de Python : chaque mot ne coûte qu'une
centaine de XOR d'entiers longs, sur une fenêtre glissante de 624 mots.

C'est **l'élimination** qui ne passait pas. Réduire 25 908 équations de 19 937
bits demande ~2·10⁸ XOR de lignes — des jours avec les entiers longs de Python,
**57 secondes** avec `tools/f2solve.c`, écrit pour l'occasion et autotesté sur
le rang, l'incohérence et la reconstruction exacte de la solution.

### La paramétrisation, et pourquoi elle n'est pas cosmétique

> L'état de MT19937 fait 624 mots de 32 bits, mais seulement **19 937 bits
> utiles** : le twist ne lit de `mt[0]` que son bit de poids fort, et les 31
> bits bas n'influencent jamais aucune sortie.
>
>     bit 0       = mt[0] bit 31
>     bits 1..32  = mt[1]        …        1 + 623×32 = 19 937

C'est exactement le logarithme de la période. Une paramétrisation à 19 968 bits
laisserait **31 dimensions de noyau parasites** et ferait croire à un système
sous-déterminé là où il est plein.

### Le témoin

| | |
|---|---|
| tirages utilisés | 8 099 |
| équations | 25 908 |
| **rang obtenu** | **19 937 — plein** |
| **état retrouvé** | **exactement** |
| temps d'élimination | 57 s |

**Les 19 937 bits d'état de MT19937 reconstitués depuis les seuls rangs du
bonus** — sans aucun ordre d'émission, sans aucun tirage consécutif.

*Un premier passage avait rendu un rang de 13 554 et un témoin en échec. Non
reproductible : réexécuté isolément puis en entier, le rang est 19 937 dans les
deux cas et le fichier système intact. Contention de ressources avec un autre
calcul en arrière-plan. Consigné ici parce qu'une exclusion dont le témoin
échoue ne vaut rien, et que la ligne fautive a été retirée par `lab.dedupe()`.*

### L'archive

| stride | décalage | équations | rang | incohérent | compatible |
|---|---|---|---|---|---|
| 21 | 20 | 25 897 | **19 937** | **oui** | 0 |
| 21 | 0 | 25 897 | **19 937** | **oui** | 0 |
| 22 | 20 | 25 897 | **19 937** | **oui** | 0 |
| 22 | 21 | 25 897 | **19 937** | **oui** | 0 |
| 41 | 40 | 25 897 | **19 937** | **oui** | 0 |
| 42 | 40 | 25 897 | **19 937** | **oui** | 0 |

**0 état compatible sur 6 hypothèses de consommation, 6 systèmes
incohérents.** Le rang atteint 19 937 dans tous les cas — le système est donc
pleinement déterminé, puis **contredit**. C'est la forme d'exclusion la plus
forte possible.

### Ce que cela ferme

**MT19937 à état complet.** C'était la plus grosse cible restante et la plus
probable après celles déjà exclues.

Et la méthode vaut au-delà : **toute famille F2-linéaire dont l'état tient sous
~225 000 bits** est désormais atteignable par la même voie — rangs du bonus,
formes propagées, élimination en C — **sans ordre d'émission et sans tirages
consécutifs**. WELL19937 en fait partie.

**Registre : consigné.** `m = 58 075`, zéro significatif.

---

## 115. Le cinquième axe : où commencent les vingt mots dans le bloc (`h96_decalage.py`)

### Le §113 avait prédit un cinquième axe. Il existe.

Le §113 concluait : *« rien ne garantit qu'il n'y ait pas un cinquième [axe de
modèle] »*. Il y en a un, et c'est le plus bête de tous : le **décalage**.

Les §105 à §114 placent tous le mot du pas `k` à la position
`(i − i₀)·stride + k·m` — donc ils supposent que les vingt mots du tirage
commencent **au début** du bloc de stride. Rien ne le justifie :

| consommation | décalage |
|---|---|
| `[boost][n₁..n₂₀][bonus]` | **1** |
| `[n₁..n₂₀][bonus][boost]` | 0 — *le seul testé* |
| `[bonus][boost][n₁..n₂₀]` | **2** |

Les trois consomment vingt-deux mots et sont **indistinguables du point de vue
du stride**. Et l'échec est silencieux, comme les deux précédents : un décalage
faux rend le système incompatible et le registre note « exclu ».

### Le témoin, qui est la démonstration du problème

On plante un état avec un décalage de **3**, et on demande à l'attaque de le
retrouver — d'abord en balayant les décalages, puis au décalage 0 seul.

| | trouvé par balayage | trouvé à 0 seul |
|---|---|---|
| **9 / 10** familles | **oui** | **0 / 10** |

> **Sans balayer les décalages, l'attaque aurait déclaré « exclu » un générateur
> qu'elle vient de reconstituer** — dix fois sur dix.

*(LFSR113 est la dixième : son rang sature à 109 sur 128, donc son noyau fait 19
dimensions à chaque décalage et le parcours coûterait 2¹⁹ par système. Plafonné
à 12, il est déclaré **non testé** sur cet axe pour le témoin — et non exclu. La
distinction est celle du §105.)*

### L'archive

| | |
|---|---|
| strides balayés | 8 (20 à 24, 40 à 42) |
| décalages | **tous**, de 0 à `stride−1` |
| conventions de Fisher-Yates | 2 |
| **systèmes** | **5 126** |
| **exclus par incompatibilité** | **5 126** |
| non testés | 0 |
| **états compatibles** | **0** |

Sur l'archive, tous les systèmes sont incompatibles **avant même** d'atteindre
l'étape du noyau — y compris LFSR113. L'exclusion y est donc complète, malgré
le plafond posé pour le témoin.

### Ce que cela coûte, et pourquoi cela ne coûte rien

Le budget d'information est **inchangé** : on observe toujours vingt mots par
tirage, donc 89,7 équations. Le coût est en **nombre d'hypothèses** — il faut
balayer `stride` décalages par stride.

> **Et c'est là la vertu des exclusions par incohérence : elles ne se paient
> d'aucune correction de multiplicité.** Balayer cinq mille hypothèses de
> consommation ne coûte que du temps machine, là où cinq mille tests
> *statistiques* auraient exigé un seuil cinq mille fois plus dur. Le registre
> compte `m = 58 076` hypothèses corrigées par Holm ; les 5 126 systèmes de ce
> fichier n'y ajoutent **qu'une ligne**, parce qu'un système linéaire
> incohérent n'est pas un test.

### Le modèle de consommation, énuméré au complet

| axe | valeurs | où |
|---|---|---|
| échantillonneur | modulo / troncature | §94, §105 |
| pas | fixe / variable | §95, §111 |
| consommation | un / deux mots par numéro | §113 |
| ordre de service | direct / cache renversé | §112 |
| **décalage** | **0 à stride−1** | **§115** |

**Trois de ces cinq axes ont été trouvés après coup**, et chacun faisait échouer
les attaques **sans bruit**. C'est le vrai enseignement de ces trois sections,
et il vaut au-delà de ce dossier :

> Une attaque algébrique qui rend « incompatible » ne dit pas *« ce n'est pas ce
> générateur »*. Elle dit *« ce n'est pas ce générateur **sous ce modèle de
> consommation** »*. Le modèle doit être **énuméré, pas supposé**.

**Registre : consigné.** `m = 58 076`, zéro significatif.

---

## 116. Prédire depuis l'archive triée : boucler la chaîne (`h97_prediction_triee.py`)

### Le trou

Le §109 a construit un prédicteur : quinze générateurs sur quinze, horizon dix.
Mais il part des tirages **ordonnés** — et le dossier n'en compte que **neuf**.

Le §114 reconstitue MT19937 à état complet depuis les rangs du bonus des
**70 560 tirages triés** — la donnée dont on dispose en masse. Mais il s'arrête
à l'état : il n'a **jamais prédit**.

> D'un côté un prédicteur sans données, de l'autre des données sans prédiction.

### Le théorème de prédiction depuis une donnée partielle

> Le rang du bonus ne publie que **3,20 bits** par tirage — moins d'un vingtième
> des 61,6 bits que contient l'ensemble tiré. On pourrait croire qu'un
> prédicteur bâti dessus ne rendra qu'une prédiction partielle.
>
> **C'est faux.** Une fois l'état identifié, la sortie est *entièrement*
> déterminée : les vingt numéros, leur **ordre d'émission** — jamais observé —,
> le rang du bonus, et tous les tirages suivants.
>
>     observation : 3,20 bits par tirage
>     prédiction  : 61,6 bits par tirage, PLUS l'ordre, à horizon INFINI
>
> La quantité d'information de l'**observation** ne borne pas celle de la
> **prédiction** ; elle ne borne que le **nombre de tirages à observer**. ∎

C'est la différence de nature avec les §107 et §108, où l'edge s'évanouit dans
le bruit : ici il n'y a pas d'edge, il n'y a plus rien d'aléatoire.

### La démonstration : observer des ensembles, annoncer un ordre

On plante un état, on fabrique des tirages, on ne garde que **les rangs du
bonus** — pas les numéros, pas l'ordre — on reconstitue, puis on **annonce** le
tirage suivant.

| famille | état | tirages triés | tirage +1 | bonus +1 | horizon 10 |
|---|---|---|---|---|---|
| xorshift32 | 32 | 18 | **exact** | exact | 10/10 |
| xorshift64 | 64 | 28 | **exact** | exact | 10/10 |
| xorshift96 | 96 | 38 | **exact** | exact | 10/10 |
| xorshift128 | 128 | 48 | **exact** | exact | 10/10 |
| taus88 | 96 | 38 | **exact** | exact | 10/10 |
| xoroshiro128 (brut) | 128 | 48 | **exact** | exact | 10/10 |
| xoshiro128 (brut) | 128 | 48 | **exact** | exact | 10/10 |
| xoshiro256 (brut) | 256 | 88 | **exact** | exact | 10/10 |
| LFSR113 | 128 | 48 | non | non | — |
| WELL512a | 512 | 168 | **exact** | exact | 10/10 |
| V8 `Math.random` | 128 | 48 | **exact** | exact | 10/10 |
| **MT19937** | **19 937** | **6 430** | **exact** | **exact** | **10/10** |

> **11/12 tirages suivants annoncés exactement — vingt numéros dans l'ordre
> d'émission, un ordre que l'observation ne contenait à aucun moment.**

*(LFSR113 est l'exception : son rang sature structurellement — le §106 l'avait
mesuré, stable de 124 à 2 000 tirages — donc les rangs du bonus ne déterminent
pas la totalité de son état. C'est une limite de l'observable, pas de la
méthode.)*

**Une correction au solveur en passant.** `tools/f2solve.c` n'émettait de
solution qu'au rang plein. Or plusieurs générateurs logent moins de bits utiles
que leur état nominal — taus88 en met 88 dans 96, LFSR113 en met 113 dans 128 —
et ces bits morts ne peuvent être déterminés par **aucune** observation,
puisqu'ils n'influencent aucune sortie. Exiger le rang plein déclarait en échec
des familles que l'attaque résout parfaitement : taus88 est passé de « non » à
**exact**.

### Ce qu'il faudrait observer

| état | tirages triés requis | l'archive suffit ? |
|---|---|---|
| 128 | 41 | oui |
| 512 | 161 | oui |
| 1 024 | 321 | oui |
| **19 937** | **6 231** | **oui** |
| 200 000 | 62 501 | oui |

**La donnée n'est pas le facteur limitant jusqu'à ~225 000 bits d'état.**

### Sur l'archive

Appliqué aux vrais rangs, ce prédicteur ne rend **rien** : les §106 et §114 ont
montré que tous les systèmes sont incohérents. Il n'y a pas de prédiction à
annoncer, et il serait malhonnête d'en fabriquer une.

Ce que ce fichier établit est autre chose :

> **La chaîne est complète et vérifiée de bout en bout** : ensembles triés →
> rangs du bonus → équations F2 → état → **ordre d'émission et tirages
> futurs**. Chaque maillon est mesuré, et le dernier — celui qui manquait —
> rend 11 tirages exacts sur 12.

Si un jour un générateur rend un système **cohérent** sur l'archive, il n'y
aura rien de plus à inventer : la prédiction sortira du même code, à horizon
infini.

**Registre : inchangé** — ce fichier rejoue les exclusions des §106 et §114.

---

## 117. Le bit zéro des sorties additives : rouvrir la case que j'avais fermée (`h98_bit_zero_additif.py`)

### Ce que le dossier affirmait, et moi avec

Le §68 écarte explicitement les sorties additives du champ des attaques
F2-linéaires : *« les sorties additives (xorshift128+, xoroshiro128+) ne sont
pas linéaires »*. Je l'ai repris à mon compte toute cette session — jusqu'à
bâtir dessus mon estimation de nos chances, en classant `xorshift128+`, le
`Math.random` de **Firefox et de Safari**, dans la case « aucune quantité de
données n'y change rien ».

**C'est faux pour un bit, et un bit suffit.**

### Le théorème du bit zéro additif

> Soient `A` et `B` deux fonctions **F2-linéaires** de l'état. Alors
>
>     bit₀(A + B) = bit₀(A) ⊕ bit₀(B)
>
> **Preuve.** L'addition propage des retenues du bit `k` vers le bit `k+1`.
> Aucune retenue n'entre dans le bit 0 : il n'y a rien en dessous de lui. ∎

C'est le pendant exact du §100 — qui traitait d'une **constante** additive —
pour un **terme** additif variable.

| sur `xorshift128+` | prédit par une forme linéaire |
|---|---|
| **bit 0** | **8 000 / 8 000** |
| bit 1 | 4 065 / 8 000 — le hasard |

> Toute famille « + » a un bit zéro **exactement F2-linéaire** en son état, et
> se laisse donc attaquer par élimination de Gauss comme n'importe quelle
> famille à sortie brute.

**La superposition sur vecteurs unitaires est légitime pour le bit 0 — et pour
lui seul.** La transition d'état est linéaire ; la sortie ne l'est pas, mais son
bit 0 l'est par le théorème.

### Ce qui le publie

Sous échantillonneur **modulo**, la désignation du bonus par indice donne
`rang = sortie mod 20`, donc `rang mod 2 = sortie mod 2` puisque **2 divise
20**. Chacun des 70 560 tirages publie **une équation F2 exacte** — et il n'en
faut que 128 pour `xorshift128+`, 256 pour `xoshiro256+`.

C'est un modèle d'observation **différent** du §106 et du §114, qui supposaient
un indice **tronqué**. Les deux sont plausibles ; aucun n'était testé sur les
familles additives.

### Le témoin

| famille | état | tirages | rang | tirage +1 | horizon 10 |
|---|---|---|---|---|---|
| **xorshift128+** (Firefox, Safari) | 128 | 384 | 128 | **exact** | 10/10 |
| xoroshiro128+ | 128 | 384 | 128 | **exact** | 10/10 |
| xoshiro256+ | 256 | 768 | 256 | **exact** | 10/10 |
| xoshiro128+ (32 bits) | 128 | 384 | 128 | **exact** | 10/10 |

> **4/4 états de familles additives reconstitués et prédits — depuis un seul bit
> par tirage.**

### L'archive

| | |
|---|---|
| hypothèses (4 familles × 7 modèles de consommation) | **28** |
| **systèmes incohérents** | **28** |
| **états compatibles** | **0** |

### Ce que cela change à la carte

**J'ai eu tort deux fois sur les sorties additives.** Au §112, en croyant que le
`Math.random` de V8 en était une — il n'en est pas, il est brut. Ici, en croyant
que celles qui en sont vraiment résistent à tout — leur bit zéro ne résiste à
rien.

**Ce qui reste vraiment hors d'atteinte**, et la liste a encore maigri :

- les sorties **multipliées avec rotation** : `xoshiro256**`, `xoroshiro128**`,
  dont la sortie est `rotl(s·5, 7)·9`. La multiplication par un impair
  **préserve** le bit 0 — `bit₀(5x) = bit₀(x)` — mais la **rotation le
  déplace** : le bit 0 de la sortie devient un bit intermédiaire du produit, où
  les retenues sont entrées ;
- **PCG**, dont la rotation est de surcroît dépendante des données ;
- **splitmix64** et les chaînes de mélange à décalages multipliés ;
- tout **CSPRNG**, et le matériel.

> **La règle qui en sort : pour casser le bit zéro, il faut une rotation ou un
> décalage à droite appliqué APRÈS une addition. Une addition seule ne suffit
> pas, une multiplication par un impair non plus.**

**Registre : consigné.** Zéro significatif.

---

## 118. Le système total : tout ce que l'archive publie, dans une seule matrice (`h99_systeme_total.py`)

### Ce qui n'avait jamais été joint

L'archive publie **trois** choses par tirage, et le dossier ne s'est jamais
servi que d'une à la fois :

| observable | information | statut |
|---|---|---|
| l'ensemble trié des vingt numéros | 61,6 bits | **inutilisable** — corollaire de branchement (§110) |
| le rang du bonus | 3,20 bits F2 exacts | utilisé (§106, §114) |
| **le boost** | 1,879 bit d'entropie | **jamais mis dans un système linéaire** |

Le §90 avait mesuré le boost et s'était arrêté là.

### Le théorème de l'intervalle cumulé

> Soit une loi discrète de bornes cumulées `F(0)=0 < F(1) < … < F(k)=1`,
> échantillonnée par comparaison : on tire `u`, on rend `i` tel que
> `u ∈ [F(i−1), F(i))`.
>
> Observer `i` **encadre `u` exactement comme le fait une troncature**, et le
> théorème du préfixe (§105) s'applique tel quel. ∎

**La différence avec la troncature, et elle est délicate** : les bornes ne sont
pas connues d'avance, on les **estime** sur l'archive. Une borne mal estimée
donnerait des bits **faux** et une exclusion imméritée. On élargit donc chaque
intervalle de **quatre écarts-types** — ce qui coûte des bits et ne peut pas en
inventer.

| boost | part | intervalle élargi | bits exacts |
|---|---|---|---|
| 1 | 0,5119 | [0,00000 ; 0,51946) | 0 |
| 2 | 0,2380 | [0,50441 ; 0,75642) | 1 |
| 3 | 0,1506 | [0,74338 ; 0,90500) | 1 |
| 4 | 0,0500 | [0,89599 ; 0,95372) | **3** |
| 5 | 0,0246 | [0,94719 ; 0,97745) | **4** |
| 10 | 0,0249 | [0,97275 ; 1,00000) | **5** |

> **0,762 bit F2 exact par tirage — 53 733 équations que le dossier n'avait
> jamais utilisées.**

### Ce que le système joint ajoute vraiment

`3,20 + 0,762 = 3,96` équations par tirage au lieu de 3,20 — un gain de 24 %,
qui n'est **pas** l'essentiel. L'essentiel :

> Le système joint contraint aussi la **position relative** des deux mots dans
> le bloc. `[20 numéros][boost][bonus]` et `[boost][20 numéros][bonus]` sont
> deux modèles distincts qu'un observable **seul** ne peut pas séparer.

C'est le cinquième axe du §115, mais **mesuré** au lieu d'être balayé à
l'aveugle.

### Le témoin

| famille | état | tirages | équations | tirage +1 | horizon 10 |
|---|---|---|---|---|---|
| xorshift32 … xoshiro256 (brut) | 32–256 | 20–76 | 71–303 | **exact** | 10/10 |
| **WELL512a** | 512 | 141 | 562 | **exact** | 10/10 |
| V8 `Math.random` | 128 | 44 | 175 | **exact** | 10/10 |
| LFSR113 | 128 | 44 | 179 | non (rang 103) | — |

**10/11 états reconstitués depuis le rang et le boost réunis**, puis tirage
suivant annoncé exactement.

### L'archive

| | |
|---|---|
| modèles de consommation (11 familles × 7) | **77** |
| **systèmes incohérents** | **77** |
| **états compatibles** | **0** |

### Ce que l'archive peut encore donner — et c'est fini

    ensemble trié des 20 numéros   61,6 bits/tirage   INUTILISABLE (§110)
    rang du bonus                   3,20 bits/tirage   utilisé
    boost                           0,762 bit/tirage   utilisé ici
    ------------------------------------------------------------------
    total                           3,96 équations F2 exactes par tirage
                                    279 000 sur l'archive entière

> **Et c'est tout. Il n'y a pas de quatrième champ.**

Ce qui reste inexploité — les 61,6 bits de l'ensemble trié — l'est pour une
raison **démontrée**, pas par manque d'effort : le corollaire de branchement du
§110 chiffre son arbre à **2¹²³ nœuds** pour 128 bits d'état. La seule façon
d'en extraire davantage serait d'obtenir l'**ordre**, qui change 4,32 bits de
branchement en 4,48 bits d'équations gratuites.

**Registre : consigné.** `m = 58 078`, zéro significatif.

---

## 119. Le sous-espace de linéarité : mesurer la frontière au lieu de l'affirmer (`h100_sous_espace.py`)

> **⚠ Correction apportée par le §123.** Le modèle de PCG32 employé ici oubliait
> le cast en `uint32_t` de la référence (`uint32_t xorshifted = ((old >> 18u) ^
> old) >> 27u;`) et faisait tourner **37 bits au lieu de 32**. La rotation
> cessait alors d'être une permutation du mot, et la mesure rendait
> `dim L = 0` pour PCG32 là où la valeur juste est **`dim L = 1`** — la
> **parité du mot**, qu'aucune rotation ne peut brouiller. `h100_sous_espace.py`
> est corrigé et le tableau ci-dessous relu ; la conclusion pratique tient, mais
> son énoncé change : voir le §123.


### Ce que tout le dossier faisait sans le mesurer

Depuis le §68, chaque section range les générateurs en deux tas —
« attaquable par algèbre linéaire » et « non linéaire, hors d'atteinte » — sur
la foi d'un raisonnement au cas par cas. **Ce raisonnement s'est trompé deux
fois dans cette seule session :**

- **§112** — j'ai cru que le `Math.random` de V8 était `xorshift128+`, donc
  additif, donc hors d'atteinte. Il est **brut**, donc entièrement linéaire.
- **§117** — j'ai cru que les vraies familles additives résistaient à tout.
  Leur **bit zéro** est exactement linéaire, et un bit a suffi.

Deux erreurs, même cause : une frontière **affirmée** au lieu d'être
**mesurée**.

### Le théorème du défaut de linéarité

> Soit `Ψ : F₂ⁿ → F₂^W` l'application « état → sortie ». Posons le **défaut**
>
>     D(x, y) = Ψ(x ⊕ y) ⊕ Ψ(x) ⊕ Ψ(y) ⊕ Ψ(0)
>
> Alors `c` est une forme **F2-linéaire** de l'état **si et seulement si**
> `c·D(x,y) = 0` pour tous `x, y`. Donc
>
>     L = vect{ D(x,y) }^⊥        et       dim L = W − rang(D)   ∎

**On ne cherche plus une forme linéaire au jugé : on calcule la dimension de
l'espace de toutes celles qui existent.** Zéro veut dire qu'il n'y en a
**aucune** — pas qu'on n'en a pas trouvé.

### La mesure

Sortie concaténée sur **4 pas** — ce qui attrape aussi les relations linéaires
*entre* mots successifs, qu'un test mot par mot manquerait. 2 500 couples
`(x, y)` par famille.

| famille | sortie | bits | rang du défaut | **dim L** |
|---|---|---|---|---|
| xorshift128 (Marsaglia) | brute | 128 | 0 | **128** |
| xoshiro256 (brut) | brute | 256 | 0 | **256** |
| V8 `Math.random` (§112) | brute | 208 | 0 | **208** |
| **xorshift128+** (Firefox/Safari) | additive | 256 | 252 | **4** |
| xoroshiro128+ | additive | 256 | 252 | **4** |
| xoshiro256+ | additive | 256 | 252 | **4** |
| xoshiro256++ | addition + **rotation** | 256 | 256 | **0** |
| xoshiro256\*\* | multiplication + **rotation** | 256 | 256 | **0** |
| xoroshiro128\*\* | multiplication + **rotation** | 256 | 256 | **0** |
| PCG32 | rotation **variable** | 128 | 127 | **1** ⚠ *corrigé au §123 — la parité du mot* |
| splitmix64 | chaîne de mélange | 256 | 256 | **0** |

### La vérification indépendante du §117

`xorshift128+` rend **dim L = 4** sur quatre mots concaténés — soit **un par
mot** — et la base calculée vit exactement sur les bits `0, 64, 128, 192` :

> **le bit 0 de chaque mot, et lui seul.**

C'est le théorème du §117, retrouvé par une voie entièrement différente : non
pas en raisonnant sur les retenues, mais en calculant l'orthogonal d'un défaut
mesuré.

### La frontière, enfin mesurée

| forme de la sortie | dim L | ce qui protège |
|---|---|---|
| brute | tous les bits | rien |
| **additive** | **1 par mot** | rien — le bit 0 passe |
| addition + **rotation** | **0** | la rotation |
| multiplication + rotation | **0** | la rotation |
| rotation **variable** (PCG) | **1 par mot** ⚠ | rien — la **parité** passe, une rotation étant une permutation des bits (§123) |
| chaîne de mélange | **0** | les décalages à droite |

> Le §117 avait **deviné** cette règle à partir d'un cas ; elle est ici
> **mesurée** sur onze familles. **Ce qui protège n'est jamais l'addition, ni
> la multiplication par un impair — c'est toujours un décalage à droite ou une
> rotation appliqués APRÈS elles.**

Et c'est aussi le verdict sur ce qui reste : les **quatre** familles à
`dim L = 0` — `xoshiro256++`, `xoshiro256**`, `xoroshiro128**`, `splitmix64` —
sont hors d'atteinte de toute attaque par algèbre linéaire, **et ce n'est plus
une conjecture — c'est une dimension calculée**. Le §123 étend d'ailleurs cette
mesure aux **degrés 2 et 3**, où elle rend encore zéro pour ces quatre-là.

> **PCG32 n'en fait plus partie** : sa dimension vaut 1, et c'est la parité du
> mot. Elle ne sert pourtant à rien ici — l'archive ne publie que deux bits du
> mot, et la transition de PCG32 est un LCG, qui ne se chaîne pas sur F₂. La
> conclusion pratique tient, **son énoncé change** (§123).

**Registre : inchangé** — ce fichier ne teste rien sur l'archive ; il mesure
une propriété des générateurs eux-mêmes, et fixe la frontière que tout le reste
du dossier supposait.

---

## 120. La graine des familles brouillées : la dernière voie vers un positif (`h101_graine_brouillee.py`, `tools/sweep_brouille.c`)

### Ce que le §119 a fermé, et ce qu'il n'a pas fermé

Le §119 mesure que `xoshiro256**`, `xoshiro256++`, `xoroshiro128**`, `PCG32` et
`splitmix64` ont un sous-espace de linéarité de dimension **exactement zéro**.
Aucune élimination de Gauss ne mordra jamais sur eux — dimension **calculée**,
pas conjecture.

**Mais cela ne dit rien de leur graine.**

> Un état de 256 bits est hors de portée. **Une graine de 32 bits ne l'est pas.**

Et une loterie régulée doit pouvoir **rejouer** ses tirages pour l'audit — ce
qui pousse à amorcer sur le numéro de tirage ou sur l'horodatage, **tous deux
publiés dans l'archive**.

C'était la dernière voie par laquelle un résultat **positif** pouvait encore
sortir du dossier. Les §105 à §119 ferment l'**état** ; celle-ci ferme la
**graine**.

### Une seule plage couvre les trois hypothèses

On balaie `[0 ; 2³²)`, soit `[0 ; 4 294 967 296)`. Cet intervalle contient :

| | plage |
|---|---|
| petites graines | 0 à quelques millions |
| **numéro de tirage** | 1 309 614 – 1 380 173 |
| **horodatage unix** | 1 757 829 900 – 1 787 691 600 |

Une seule plage, trois hypothèses d'amorçage. Pas besoin d'en balayer trois.

> **Correction, §121** : cette phrase est trop large. Elle vaut pour
> l'horodatage en **secondes** et non pour celui en **millisecondes**, qui vaut
> 1 757 829 900 000 — soit 409 fois la borne du balayage. La lacune est comblée
> au §121.

### Le filtre, et son coût réel

La cible est l'**ensemble trié** des vingt numéros ; un numéro tiré sur quatre y
appartient, donc l'abandon survient après **1,33 pas** en moyenne. Mesure :
2²⁴ graines en 0,3 s, donc 2³² en 75 s.

> Probabilité de faux positif : `1/C(80,20) = 2,8·10⁻¹⁹` par graine. **Un seul
> succès aurait été décisif.**

**Autotest : 28/28** — pour chacune des sept familles et des quatre
échantillonneurs, une graine plantée est retrouvée.

### Le résultat

| | |
|---|---|
| familles × échantillonneurs | 7 × 4 = **28 balayages** |
| graines testées | **120 259 084 288** |
| espérance de faux positifs | 3,4·10⁻⁸ |
| **graines compatibles** | **0** |

### Ce que cela veut dire

L'**état** était fermé par le §119 — une dimension calculée. La **graine** l'est
ici — 120 milliards de graines, espérance de faux positifs 3,4·10⁻⁸.

**Ce qui subsiste après les deux :**

- une graine de **plus de 32 bits**, ou tirée d'un CSPRNG — c'est le cas d'un
  générateur correctement amorcé, et c'est aussi ce qu'un auditeur exigerait ;
- un **état brouillé jamais réamorcé**, hors d'atteinte par le §119 ;
- le **matériel**.

> **Le dossier a atteint sa borne.** Il ne reste que des hypothèses dont on peut
> *démontrer* qu'aucune donnée publiée ne les distinguera — et non des
> hypothèses qu'il resterait à essayer.

**Registre : consigné.** `m = 58 079`, zéro significatif.

---

## 121. La graine en millisecondes : la lacune du §120 (`h102_graine_milliseconde.py`)

### Une affirmation de portée, pas un résultat

Le §120 balaie `[0 ; 2³²)` et affirme que cette plage couvre « les trois
hypothèses d'amorçage ». **C'est vrai pour l'horodatage en secondes, et faux
pour celui en millisecondes :**

|  |  |
|---|---|
| `2³²` | 4 294 967 296 |
| horodatage **secondes** | 1 757 829 900 — dans la plage |
| horodatage **millisecondes** | **1 757 829 900 000 — hors de la plage, ×409** |

Or `Date.now()` en JavaScript, `System.currentTimeMillis()` en Java et
`microtime()` en PHP rendent **tous** des millisecondes ou mieux. Une plateforme
qui amorce sur l'horloge sort donc, le plus souvent, de la plage que le §120 a
balayée.

### Ce qui rattrape la lacune sans coûter cher

L'archive publie l'horodatage **à la seconde** : la partie milliseconde est
inconnue sur trois chiffres seulement, et l'incertitude sur l'instant réel du
tirage se compte en minutes.

    graine = ts × 1000 + m,   m dans ±600 s

soit 1 200 000 graines par tirage — contre 2³² au §120 — dans une plage que le
§120 ne pouvait pas voir.

**Et sur dix tirages.** C'est le point : sous l'hypothèse du ré-amorçage
horaire, **chaque tirage a sa propre graine**. Dix tirages sont dix chances
**indépendantes**, pas une confirmation.

### Le résultat

| | |
|---|---|
| autotest du balayeur | **28/28** |
| tirages balayés | 10 |
| graines testées | **336 000 000** |
| **graines compatibles** | **0** |

### Ce que cela corrige

Le §120 ne s'est **pas trompé dans ses mesures** : ses 120 milliards de graines
sont bien testées et bien nulles. Il s'est trompé dans la **phrase qui les
résume** — « une seule plage couvre les trois hypothèses » — parce que
l'horodatage a deux écritures et qu'une seule tient dans 2³².

> C'est exactement la faute que le §101 avait trouvée dans la carte de
> couverture : **une conclusion recopiée plus largement que sa source.** Elle se
> reproduit volontiers — c'est pourquoi le dossier la traque.

**Registre : consigné.** `m = 58 080`, zéro significatif.

## 122. Le théorème de la complexité linéaire universelle : cesser d'énumérer (`h103_complexite_lineaire.py`, `tools/bmf2.c`)

### Le défaut de méthode que ce paragraphe corrige

Du §105 au §121, la méthode est toujours la même : **nommer** une famille,
écrire ses formes F2-linéaires, résoudre, exclure. Onze mille systèmes, cinq
axes de modèle de consommation. Et **trois de ces cinq axes** — l'ordre de
service du cache (§112), les mots par numéro (§113), le décalage (§115) — n'ont
été trouvés qu'**après coup**. Chacun faisait échouer toutes les attaques
**en silence**.

> Une exclusion par énumération ne vaut que pour ce qui a été énuméré. Et
> l'histoire du dossier montre qu'on n'énumère jamais assez.

Ce paragraphe change de méthode : il calcule un **invariant**.

### Le théorème

Soit un générateur dont l'état vit dans `F2^W`, évolue par `s ↦ A·s` pour une
matrice `A` **quelconque** sur F2, et dont le mot rendu est `w = Λ·s` pour une
application F2-linéaire `Λ` quelconque. Soit `β` une forme F2-linéaire du mot.
Si la plateforme consomme ses mots aux positions d'une **progression
arithmétique** `n_i = c + σ·i`, alors la suite observée

    b_i  =  β( Λ · A^(c + σi) · s )

vérifie la récurrence linéaire dont le polynôme caractéristique est le polynôme
minimal de `A^σ`. Celui-ci divise le polynôme caractéristique de `A^σ`, de
degré `W`. Donc :

> **L(b) ≤ W**, où `L` est la complexité linéaire — et Berlekamp-Massey rend
> **exactement** `L` pour la suite finie observée.

**Le membre de droite ne contient ni `A`, ni `Λ`, ni `β`, ni `σ`, ni `c`.** Un
seul nombre teste donc simultanément :

| ce qui disparaît de l'énoncé | ce que cela remplace |
|---|---|
| la matrice `A` | **toute** famille F2-linéaire, y compris non publiée |
| le pas `σ` | l'axe 2 du §121 — le §115 y avait passé 5 126 systèmes |
| le décalage `c` | l'axe 5 |
| les mots par numéro | l'axe 3 (§113) : absorbé dans `σ` |
| la sortie `Λ`, la forme `β` | la position du bit lu dans le mot |

### Le corollaire qui compte : prédire sans identifier

Si `L` est petit, Berlekamp-Massey rend **la récurrence elle-même**, et tout bit
suivant se calcule à partir des `L` derniers — sans jamais savoir de quelle
famille il s'agit, ni quel est le pas, ni quel est l'échantillonneur.
**L'identification de la famille n'est pas nécessaire à la prédiction.** C'est
la seule voie du dossier qui prédise sans reconstituer.

### Le ppcm : doubler la portée sans un bit de plus

Le rang du bonus donne **deux** bits exacts par tirage. Les polynômes minimaux
`f` et `f'` des deux suites divisent tous deux le polynôme caractéristique de
`A^σ`, donc leur ppcm le divise aussi :

    W  ≥  deg ppcm(f, f')  =  L + L' − deg pgcd(f, f').

Sur un vrai générateur à polynôme caractéristique **irréductible** — MT19937 —
`f = f'`, le pgcd vaut tout, et la borne rend exactement `W`. Sur du hasard les
deux polynômes sont **premiers entre eux** et la borne vaut `~N` au lieu de
`~N/2` : **la portée double**.

### Deux bits exacts, toujours, et pourquoi

Le §106 mesurait 3,20 bits en moyenne par rang de bonus — un nombre **variable**
selon le rang. Ici il faut un bit à **position fixe**, sinon la suite n'est plus
la trace d'une seule forme linéaire. Or **4 divise 20** :

- **troncature** : `m = ⌊20u⌋` met `4u` dans `[m/5, (m+1)/5)`, intervalle de
  longueur 1/5 qui ne contient un entier que si `m/5` en est un. Donc
  `⌊4u⌋ = ⌊m/5⌋` **sans exception** : les deux bits de poids fort du mot sont
  exacts sur les 70 560 tirages, et pas seulement sur une partie ;
- **modulo** : `4 | 20 | 2^W` donne `w mod 4 = m mod 4` — les deux bits de poids
  **faible**. C'est le théorème du contenu du §94 réduit à `K = 20`.

### Les témoins : retrouver la largeur d'état sans nommer la famille

On fabrique le rang du bonus sous le modèle « 20 mots de Fisher-Yates + 1 mot
d'indice » — puis **on l'oublie**. Berlekamp-Massey ne reçoit que la suite de
bits.

| famille | état | tirages | L(f) | L(f') | ppcm | |
|---|---|---|---|---|---|---|
| xorshift32 | 32 | 600 | 32 | 32 | **32** | ✓ |
| xorshift64 | 64 | 600 | 64 | 64 | **64** | ✓ |
| xorshift96 | 96 | 600 | 92 | 92 | **92** | ✓ |
| xorshift128 | 128 | 600 | 128 | 128 | **128** | ✓ |
| taus88 | 96 | 600 | 84 | 83 | **84** | ✓ |
| xoroshiro128 (brut) | 128 | 600 | 128 | 128 | **128** | ✓ |
| xoshiro128 (brut) | 128 | 600 | 128 | 128 | **128** | ✓ |
| xoshiro256 (brut) | 256 | 1 024 | 256 | 256 | **256** | ✓ |
| LFSR113 | 128 | 600 | 79 | 83 | **83** | ✓ |
| WELL512a | 512 | 2 048 | 512 | 512 | **512** | ✓ |
| **MT19937** | **19 937** | 45 000 | 19 937 | 19 937 | **19 937** | ✓ |
| *(générateur parfait)* | — | 70 560 | 35 280 | 35 278 | **70 553** | ~N |

**MT19937 est retrouvé à 19 937 exactement**, depuis les seuls rangs du bonus,
sans qu'aucune famille n'ait été nommée au solveur. Le §114 avait dû écrire
19 937 formes linéaires et un solveur en C pour la même cible ; ici c'est un
nombre qui tombe.

### L'invariance mesurée, et non affirmée

Le §115 a coûté 5 126 systèmes pour balayer le seul décalage. Sur WELL512a
(512 bits) :

| pas σ | décalage c | mots/numéro | ppcm |
|---|---|---|---|
| 21 | 20 | 1 | 512 |
| 21 | 0 | 1 | 512 |
| 22 | 7 | 1 | 512 |
| 37 | 3 | 1 | 512 |
| 41 | 40 | 2 | 512 |
| 43 | 11 | 1 | 512 |

**Six modèles de consommation, une seule borne.** Les axes 2, 3 et 5 du §121
sont neutralisés par construction, pas par balayage.

### L'archive

| hypothèse | bits lus | L(f) | L(f') | pgcd | **W ≥ ppcm** |
|---|---|---|---|---|---|
| troncature | bits 1 et 2 hauts | 35 280 | 35 280 | 0 | **70 560** |
| modulo | bits 1 et 0 bas | 35 282 | 35 280 | 0 | **70 562** |

> **W ≥ 70 560.** Aucun générateur F2-linéaire dont l'état tient en moins de
> 70 560 bits, consommé à pas constant, n'engendre les rangs du bonus de
> l'archive.

Ce que cela couvre n'est pas une liste de familles, c'est une **inégalité** :

| | largeur | |
|---|---|---|
| xorshift 32/64/96/128 | 32-128 | couvert |
| taus88, LFSR113 | 88-113 | couvert |
| xoshiro / xoroshiro bruts | 128-256 | couvert |
| WELL512a, WELL1024a | 512-1 024 | couvert |
| MT19937, WELL19937 | 19 937 | couvert |
| **WELL44497b** — le plus grand état publié | **44 497** | **couvert** |
| tout le reste | < 70 560 | couvert, **nommé ou non** |

### Le corollaire arithmétique : les récurrences entières mod 2^e

Le théorème est écrit sur F2, et le §104 a dû bâtir une réduction de réseau pour
les générateurs **entiers**. Une partie d'entre eux retombe dans le même test,
et gratuitement. Soit

    x_t  =  a₁x_{t−1} + … + a_r x_{t−r} + b   (mod 2^e).

Réduite modulo 2, c'est une récurrence **affine** d'ordre `r` sur F2 ; une
récurrence affine se rend homogène en multipliant son polynôme par `(1+x)` :

> **L(bit 0) ≤ r + 1**, et la décimation par `σ` ne change pas ce degré — elle
> élève les racines à la puissance `σ`.

Or le bit 0 est justement ce que l'échantillonneur **modulo** publie, puisque
4 divise 20.

| témoin (mot = état entier) | ordre | L(bit 0) mesuré | borne |
|---|---|---|---|
| LCG mod 2³² (ANSI C, MMIX, Borland) | 1 | **2** | ≤ 2 |
| Fibonacci additif mod 2³² (`r[i−3]+r[i−31]`) | 31 | **31** | ≤ 31 |

**Mesure sur l'archive : `L(bit 0) = 35 280`.** Toute récurrence entière de
module `2^e` et d'ordre inférieur à 35 280 termes est donc exclue.

*Ce que le corollaire ne prend pas, et il faut le dire* : les modules **premiers**
(Lehmer 2³¹−1 ; MWC, dont le module `a·b−1` est impair au §102) — la réduction
modulo 2 n'a plus de sens ; et les implantations qui ne rendent que les bits
**hauts** — Java `next(bits)`, PCG, et `random()` de la glibc qui décale d'un bit
et jette justement le bit 0. Le bit 0 du **mot** n'est alors plus le bit 0 de
l'**état**, et la retenue de l'addition brise la linéarité dès le bit 1. Pour ces
deux cas, la réduction de réseau du §104 reste l'outil.

### L'axe du cache : le seul qui casse la progression arithmétique

Le §112 a montré que V8 remplit son cache par 64 en avant et le consomme **à
rebours** : `g(j) = 64·(j//64) + 63 − (j mod 64)`. Les positions consommées ne
sont alors plus arithmétiques. **Mais le théorème s'applique à chaque classe
modulo 64** : `j_{i+64} = j_i + 64σ` laisse `(j mod 64)` inchangé et augmente
`j//64` de `σ`, donc `g(j_{i+64}) = g(j_i) + 64σ`.

| hypothèse | ppcm minimal sur les 64 classes | max | moyenne |
|---|---|---|---|
| troncature | **1 098** | 1 106 | 1 102 |
| modulo | **1 096** | 1 107 | 1 103 |

**W ≥ 1 096 sous ordre de service renversé** — ce qui couvre les 128 bits du
`Math.random` de V8, le cas même qui a motivé le §112, ainsi que WELL512a.
Le prix est de 1 102 bits par classe au lieu de 70 560.

### Le résultat

| | |
|---|---|
| autotest de `tools/bmf2.c` | **10/10** |
| témoins F2-linéaires | **11/11**, MT19937 à 19 937 exactement |
| témoins du corollaire arithmétique | **2/2** |
| null | 200 archives d'un générateur parfait |
| null : moyenne / min / max | 70 559 / 70 552 / 70 562 |
| **observé** | **70 560** — `p = 0,826` |

**Registre : consigné.** `m = 58 146`, zéro significatif.

### Ce que cela change, et ce qu'il faudrait pour aller plus loin

Les §105 à §121 excluaient des familles **nommées**, une par une, et chaque axe
de modèle oublié rouvrait tout. Ici l'exclusion porte sur une **inégalité** :
`W ≥ 70 560`. Elle ne s'écrit pas plus longtemps si l'on ajoute une famille, et
aucun axe de consommation à pas constant ne la remet en cause.

> **C'est la première borne du dossier qui ne se périme pas.**

Ce qu'elle ne couvre pas, et c'est écrit dans le jeton :

- le **rejet**, où le pas varie (§111) ;
- les **sorties brouillées**, où aucun bit n'est F2-linéaire — le §119 les ferme
  autrement, par `dim L = 0`. Les deux paragraphes se partagent l'espace sans
  laisser d'interstice : §122 prend tout ce qui est linéaire, §119 démontre que
  le reste n'a aucun bit à donner ;
- l'indexation dans l'**ordre d'émission** plutôt que dans le tableau trié —
  réserve héritée du §106, et qu'aucune donnée triée ne peut lever.

**La pente.** La portée est de `~N` bits d'état pour `N` tirages, soit 70 560
aujourd'hui. Un état plus large demande plus de tirages, **dans un rapport de un
pour un**, et rien d'autre. Aucune autre borne du dossier n'a une pente aussi
simple.

## 123. Le degré algébrique : le §119 n'avait mesuré qu'au degré un (`h104_degre_algebrique.py`)

### La limite non dite du §119

Le §119 a remplacé une frontière **affirmée** par une frontière **mesurée**, et
c'était juste. Mais son défaut

    D(x, y) = Ψ(x⊕y) ⊕ Ψ(x) ⊕ Ψ(y) ⊕ Ψ(0)

est la **dérivée seconde** : il ne teste que le **degré 1**. Un bit de sortie de
degré algébrique 2 y compte pour zéro — alors qu'il donne une équation
parfaitement exploitable, **par linéarisation** : on remplace chaque produit
`x_i·x_j` par une inconnue neuve et le système redevient linéaire. Le prix est
le nombre d'inconnues, et **l'archive peut le payer** :

| état `W` | degré 1 | degré 2 | degré 3 | l'archive (70 560) suffit ? |
|---|---|---|---|---|
| 64 | 65 | 2 081 | 43 745 | **degré 2 et degré 3** |
| 128 | 129 | 8 257 | 349 633 | **degré 2** |
| 256 | 257 | 32 897 | 2 796 161 | **degré 2** |
| 512 | 513 | 131 073 | 22 238 721 | non |

> Le degré 2 est payable jusqu'à `W = 375`, le degré 3 jusqu'à `W = 74`. **Si
> l'une des familles que le §119 a fermées avait un seul bit de degré 2, elle
> tombait.** Personne dans le dossier ne l'avait demandé.

### Le théorème du défaut, porté au degré `d`

> Soit `Ψ : F₂ⁿ → F₂ᵐ`. Pour des directions `a₁, …, a_{d+1}` et un point `x`,
> la **dérivée (d+1)-ième** vaut
>
>     T(x; a₁..a_{d+1}) = ⊕_{S ⊆ {1..d+1}} Ψ( x ⊕ ⊕_{i∈S} a_i ).
>
> Alors `deg(c·Ψ) ≤ d` **si et seulement si** `c·T = 0` partout.
>
> **Preuve.** `deg(Δ_a f) ≤ deg(f) − 1`, donc un degré ≤ `d` annule toute dérivée
> (d+1)-ième. Réciproquement, si `deg f = e > d`, la dérivée (d+1)-ième garde la
> partie de degré `e−d−1`, non identiquement nulle. ∎
>
> **Conséquence.** `L_d = vect{T}^⊥`, `dim L_d = m − rang(T)`. Le §119 est le
> cas `d = 1`, où `T` a quatre termes.

### La calibration : ce que l'arithmétique de la retenue impose

Le §117 donne la prédiction, et elle est **arithmétique**, pas empirique. Pour
`A + B` : bit 0 → aucune retenue entrante, degré 1 ; bit 1 → retenue
`bit0(A)·bit0(B)`, degré 2 ; bit 2 → retenue de la retenue, degré 3. Sur quatre
mots concaténés, une famille additive **doit** rendre `4 / 8 / 12`.

### Ce que la mesure a trouvé en chemin : une faute dans le §119

En portant le calcul au degré 2, **PCG32 a rendu une dimension non nulle** là où
le §119 avait écrit zéro. Avant de crier victoire, on vérifie le **modèle** — et
c'est le modèle qui était faux. La référence écrit

    uint32_t xorshifted = ((old >> 18u) ^ old) >> 27u;

Le cast **tronque à 32 bits avant la rotation**. Le §119 l'avait omis et faisait
tourner 37 bits : ce n'est alors plus une permutation du mot.

| sortie | référence C | §119 | §119 corrigé |
|---|---|---|---|
| 0 | 355 248 013 | 356 296 589 ✗ | 355 248 013 |
| 1 | 1 055 580 183 | 1 055 580 183 | 1 055 580 183 |
| 2 | 3 222 338 950 | 3 222 338 950 | 3 222 338 950 |
| 3 | 2 908 720 768 | 3 982 462 592 ✗ | 2 908 720 768 |
| 4 | 1 758 754 096 | 1 758 754 736 ✗ | 1 758 754 096 |
| 5 | 2 682 436 660 | 2 682 437 492 ✗ | 2 682 436 660 |

**Quatre sorties sur six diffèrent**, et la mesure change avec le modèle :

| modèle | dim L₁ | dim L₂ |
|---|---|---|
| §119 tel quel | 0 | 1 |
| **référence** | **1** | **3** |

**La raison tient en une ligne.** Une rotation est une **permutation** des 32
bits du mot : elle en conserve la **parité**. Or

    x = (uint32)( ((s >> 18) ^ s) >> 27 )

est **F₂-linéaire** en l'état — ce ne sont que des décalages et des XOR. Donc

> **parité(sortie) = parité(x) = une forme F₂-linéaire de l'état**, quel que soit
> l'angle de rotation — alors que c'est précisément la rotation variable qui
> devait brouiller PCG32.

La fonctionnelle mesurée vaut `0xFFFFFFFF` sur le premier mot et zéro sur les
suivants : **exactement cette parité, et rien d'autre.**

### La mesure, degré par degré

| famille | état | sortie | dim L₁ | dim L₂ | dim L₃ | prédit | |
|---|---|---|---|---|---|---|---|
| xorshift128 (Marsaglia) | 128 | 32 | 128 | 128 | 128 | tout | **calibré** |
| xoshiro256 (brut) | 256 | 64 | 256 | 256 | 256 | tout | **calibré** |
| V8 `Math.random` (§112) | 128 | 52 | 208 | 208 | 208 | tout | **calibré** |
| xorshift128+ | 128 | 64 | 4 | 8 | 12 | 4/8/12 | **calibré** |
| xoroshiro128+ | 128 | 64 | 4 | 8 | 12 | 4/8/12 | **calibré** |
| xoshiro256+ | 256 | 64 | 4 | 8 | 12 | 4/8/12 | **calibré** |
| xoshiro256++ | 256 | 64 | **0** | **0** | **0** | — | fermé |
| xoshiro256\*\* | 256 | 64 | **0** | **0** | **0** | — | fermé |
| xoroshiro128\*\* | 128 | 64 | **0** | **0** | **0** | — | fermé |
| **PCG32** | 64 | 32 | **1** | **3** | **7** | — | ⚠ |
| splitmix64 | 64 | 64 | **0** | **0** | **0** | — | fermé |

**6/6 témoins calibrés.** Les familles additives rendent exactement `4 / 8 / 12`
— les bits 0, 1 et 2 de chaque mot, ni plus ni moins, comme l'arithmétique de la
retenue l'exige. La mesure est donc lisible.

### Ce que la mesure décide

Une dimension non nulle **ne suffit pas**. Il faut deux conditions de plus, et
elles doivent figurer dans le **même tableau** que la dimension, sinon on relit
un chiffre pour une conclusion :

- **observable** — la forme doit se lire dans ce que l'archive publie : deux
  bits du mot (§122), et non le mot entier ;
- **chaînable** — la transition doit être F₂-linéaire, sinon la forme vaut pour
  l'état courant et ne se propage pas d'un tirage au suivant.

| famille brouillée | état | dim L₁ | dim L₂ | dim L₃ | monômes | observable | chaînable | **exploitable** |
|---|---|---|---|---|---|---|---|---|
| xoshiro256++ | 256 | 0 | 0 | 0 | — | — | — | **non : aucun bit** |
| xoshiro256\*\* | 256 | 0 | 0 | 0 | — | — | — | **non : aucun bit** |
| xoroshiro128\*\* | 128 | 0 | 0 | 0 | — | — | — | **non : aucun bit** |
| PCG32 | 64 | 1 | 3 | 7 | 65 | **non** | **non (LCG)** | **non** |
| splitmix64 | 64 | 0 | 0 | 0 | — | — | — | **non : aucun bit** |

> **Zéro famille exploitable.** La frontière du §119 tient — et elle est
> désormais mesurée à **trois degrés au lieu d'un**, sur un modèle **vérifié
> contre la référence**.

Pour les quatre familles à zéro, la conclusion est même **plus forte** que celle
du §119 : il ne s'agit pas seulement de l'absence d'un bit *linéaire*, c'est
qu'aucune combinaison de bits n'atteint même le **degré 3**. La linéarisation,
qui aurait rattrapé le degré 2 à 32 897 inconnues pour un état de 256 bits, n'a
**rien à linéariser**.

### Ce que cela ajoute au dossier

Le §119 écrivait « `dim L = 0`, donc aucune élimination de Gauss ». C'était vrai
de l'élimination **directe** et faux comme borne générale : la linéarisation
ramène le degré 2 à une élimination de Gauss, simplement plus large.

> **La phrase du §119 valait plus large que sa mesure.** C'est la troisième fois
> dans ce dossier — §101, §121, et ici — qu'une conclusion se révèle recopiée
> plus largement que sa source. Elle se reproduit, et c'est pourquoi le dossier
> la traque.

Ce qui reste hors d'atteinte, et pourquoi ce n'est pas un aveu : au-delà du degré
3 le nombre de monômes dépasse le nombre de tirages, et **aucune donnée publiée
ne comblera l'écart** — `C(256,4)` vaut déjà 174 792 640. Ce n'est pas une
hypothèse qu'il resterait à essayer, c'est une borne.

**Registre : inchangé** — ce fichier ne teste rien sur l'archive ; il mesure une
propriété des générateurs eux-mêmes.
