# De combien peut-on améliorer les prédictions ?

Réponse courte, en cinq nombres :

| | |
|---|---|
| Amélioration possible par une meilleure **prédiction** | **0 %** — c'est un théorème, pas un résultat empirique |
| Plafond d'un biais **non détecté**, pour qui **connaîtrait** la règle | **+6,3 %** de rendement (§40) |
| Ce qu'un joueur pourrait **réellement** en tirer, devant l'identifier lui-même | **≈ +1,0 %** sur la famille mesurée |
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

**Ce qui est ouvert aujourd'hui**, dans l'ordre où cela coûte quelque chose :

1. **Relever le prix du ticket** (§36). C'est la seule donnée manquante dont
   une décision dépende : le seuil de bascule vaut `c/p`, et sans `c` la
   règle qui décide s'il faut jouer n'est pas calculable. Tout le dossier est
   « par franc misé » faute de ce nombre, qui se lit d'un coup d'œil.
2. **Dimensionner sur la cagnotte affichée** (§36, théorème N). L'app ne
   propose aujourd'hui aucune taille de mise. Quand elle en proposera une,
   elle doit la recalculer à chaque occasion sur la cagnotte à l'écran — ce
   qui bat de 37 % la meilleure fraction figée possible, et ne demande aucun
   paramètre estimé.
3. **Laisser l'instrument du bonus accumuler** (§37). Cinq tirages ordonnés
   concordants établiraient une règle de position, une trentaine
   établiraient l'uniformité. L'app en collecte un toutes les cinq minutes
   depuis §34 ; il n'y a rien à faire d'autre qu'attendre.
4. **Trancher le boost avant clôture** (§4, §16). Le seul point du dossier
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

**Registre : inchangé.** `h31` ne teste pas l'archive — il démontre.
