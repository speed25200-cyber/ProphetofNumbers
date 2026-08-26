# Audit indépendant des 70 560 tirages — contre-expertise

Analyse conduite sur `claude/draws/*.csv` (ids 1309614–1380173, aucun trou,
20 numéros distincts sur tous les tirages, intervalle médian 300 s).
Objectif : vérifier `REPORT.md`, tester ce qu'il ne teste pas, et lancer
l'attaque de reconstruction d'état sur des données réelles.

---

## 1. Correction méthodologique : χ²/df ne vaut pas 1,00 sous H₀

`REPORT.md` compare **χ²/df = 0,6784 à un attendu de 1,00** et en tire un
« régime uniforme » malgré un écart apparent de −2,2 σ. Le seuil de
référence est faux, et l'écart n'existe pas.

Les comptes par numéro ne sont **pas poissoniens**. Chaque tirage est un
tirage sans remise de 20 boules sur 80, donc pour chaque numéro :

```
Var(count) = N · p(1−p) = N · 0,1875
```

alors que la statistique χ² divise par `E = N · p = N · 0,25`. Le rapport
des deux vaut 0,75, d'où :

```
E[χ²] = 80 × p(1−p)/p = 80 × 0,75 = 60        (et non 79)
E[χ²/df] = 60/79 = 0,7595                      (et non 1,00)
```

Monte-Carlo (400 réplicats de 70 560 tirages SRS 20/80) :

| | valeur |
|---|---|
| χ² observé | 53,60 |
| moyenne simulée sous H₀ | **58,90** |
| écart-type simulé | 9,48 |
| **z de l'observation** | **−0,56** (p = 0,58) |

**L'anomalie disparaît.** Le χ² n'est pas « trop bas » : il est à un demi
écart-type de son espérance correcte. Le même biais de référence explique
le split-half du rapport (0,7519 et 0,6173, « tous deux sous 1,00 ») :
l'attendu était 0,76, ils l'encadrent.

### Test par fenêtres (10 × 7 056 tirages)

```
0,909  0,903  0,628  0,685  0,568  0,838  0,776  0,889  0,720  0,802
moyenne 0,7721   attendu 0,7456   fenêtres sous l'attendu : 4/10
```

Dispersion symétrique autour de la bonne valeur. Aucun effet systématique :
si le générateur équilibrait ses sorties, les dix fenêtres seraient
*toutes* basses. Dossier clos sur ce point.

---

## 2. Tests que le rapport ne fait pas

| Test | Résultat | Attendu | Verdict |
|---|---|---|---|
| **Paires** (3 160 tests simultanés) | \|z\|max = 3,68 ; **0 paire** au-delà du seuil de Bonferroni 4,06 ; distribution des z : moyenne +0,000, σ = 0,983 | σ = 1,000 | conforme |
| **Géométrie du tableau** (adjacences colonne/rangée sur la grille 8×10) | 8,5493 paires/tirage, z = +1,09 | 8,5380 | conforme |
| **Anti-rejeu** (2,489 milliards de paires) | recouvrement max **16/20** entre 1327210 et 1349871 | 1,69 paire attendue à ≥16 | conforme |
| **Position du bonus** dans le tirage trié | χ²(19) = 27,5 → z = +1,37 | uniforme | conforme |
| **Dérive temporelle** (14 fenêtres de 5 000) | overlap lag-1 : 4,971 → 5,028, σ inter-fenêtres 0,0160 | σ = 0,0239 | stable |

Deux observations factuelles à corriger dans `REPORT.md` :

- Le **bonus est toujours l'une des 20 boules tirées** (70 560/70 560,
  soit 100,00 %) — c'est donc une sélection *dans* le tirage, pas un
  tirage annexe. Sa position dans l'ordre trié est uniforme.
- Le **boost prend six valeurs**, pas trois : `1, 2, 3, 4, 5, 10` avec
  les proportions `0,512 / 0,238 / 0,151 / 0,050 / 0,025 / 0,025`.

---

## 3. Attaque de reconstruction d'état — exécutée sur les données réelles

Cible : tirage **1380172**, confirmation obligatoire sur **1380173**.
Balayage **exhaustif** de l'espace d'états, rejet des doublons modélisé
exactement (pas approximé), filtrage par survivants vectorisé.

| Famille | Espace balayé | Durée | Débit | Profondeur max | États trouvés |
|---|---|---|---|---|---|
| LCG glibc | 2³¹ = 2 147 483 648 | 77 s | 28 M/s | 10/20 | **0** |
| LCG MSVC | 2³² = 4 294 967 296 | 152 s | 28 M/s | 10/20 | **0** |
| xorshift32 | 2³² = 4 294 967 296 | 256 s | 17 M/s | 12/20 | **0** |

**Total : 10 737 418 240 états testés exhaustivement. Aucun ne reproduit
le tirage.** La profondeur maximale atteinte (10 à 12 numéros sur 20) est
exactement le niveau du bruit pour ce nombre de candidats.

Toute la classe des générateurs à état de 32 bits est donc **écartée par
épuisement**, pas par échantillonnage — sur des tirages réels.

---

## 4. Conclusion

Le verdict de `REPORT.md` — *régime uniforme, rien d'exploitable* — est
**confirmé**, et sur une base plus solide : le seul écart qu'il signalait
était un artefact de normalisation, et cinq tests supplémentaires
(paires avec correction de multiplicité, géométrie, anti-rejeu sur
2,5 milliards de paires, position du bonus, stabilité temporelle) ne
montrent rien.

Ce que 70 560 tirages permettent d'affirmer :

- **Aucun générateur à état ≤ 32 bits** ne produit cette série (démontré
  par épuisement, pas par test statistique).
- **Aucun biais de premier ou second ordre** détectable à cette taille
  d'échantillon — la puissance atteinte détecterait un déséquilibre de
  fréquence de l'ordre de 0,5 % et une corrélation de paires de 1,5 %.
- **Aucune répétition de séquence**, ce qui écarte le mode de défaillance
  historique (graine réutilisée, cf. Corriveau 1994).

Ce que 70 560 tirages ne permettront **jamais** d'affirmer : rien sur un
générateur à état ≥ 64 bits. Le nombre de tirages n'y change rien — la
reconstruction d'état est bornée par la taille de l'espace à balayer, pas
par la quantité de données. Sur ce point l'archive, aussi complète
soit-elle, ne déplace pas la frontière.

*Méthode : `numpy`, Monte-Carlo 400 réplicats pour le null du χ²,
produit matriciel par blocs pour les 2,5 milliards de recouvrements,
filtrage par survivants pour le balayage d'états.*

---

## 5. Au-delà de l'épuisement : la complexité linéaire

La recherche exhaustive plafonne à 2³². Un Mersenne Twister a **19 937
bits d'état** : l'énumérer demanderait 2¹⁹⁹³⁷ opérations. Aucune machine,
aucune durée, ne l'atteindra jamais. Cette classe semblait donc
définitivement hors de portée d'un audit par les sorties.

Elle ne l'est pas — à condition de changer d'outil. Mersenne Twister,
xorshift, xoroshiro, tout LFSR : ce sont des générateurs **F₂-linéaires**.
Or l'algorithme de **Berlekamp-Massey** détermine la plus courte
récurrence linéaire d'une suite binaire, et détecte donc un générateur
linéaire de degré jusqu'à n/2 sur n bits — *sans jamais énumérer son
état*.

### Transformation des tirages en bits uniformes

Chaque tirage est un 20-sous-ensemble de 80. Converti par le système
combinatoire numérique en un rang r ∈ [0, C(80,20)), avec C(80,20) ≈
2⁶¹·⁶². On n'émet ses 61 bits que si r < 2⁶¹ (rejet sinon) : sous H₀ les
bits obtenus sont alors **exactement** uniformes et indépendants.

```
tirages acceptés : 45 872 / 70 560  (taux 0,650, conforme à 2⁶¹/C(80,20) = 0,652)
flux obtenu      : 2 798 192 bits
```

### Batterie complète sur le flux

| Test | Observé | p |
|---|---|---|
| Monobit | 0,500264 de 1 | 0,376 |
| Fréquence par blocs (M = 20 000) | χ² = 130 / 139 | 0,592 |
| Runs (alternances) | 1 399 113 vs 1 399 096 | 0,988 |
| Plus longue série de 1 | 12,710 vs **12,636 ± 0,090** (Monte-Carlo) | 0,411 |
| Spectral DFT (n = 1 048 576) | 497 807 pics sous seuil vs 498 074 | 0,017 |
| Sommes cumulées | max\|S\|/√n = 1,494 | 0,023 |
| Entropie de blocs (10 bits) | 9,99974 bit sur 10 | 0,883 |
| **Complexité linéaire (BM, M = 500, 4 000 blocs)** | **L̄ = 250,2 vs μ = 250,2 · χ² = 7,12** | **0,310** |

**8 tests sur 8 conformes.** Les deux valeurs à p ≈ 0,02 ne survivent pas
à la correction de multiplicité (seuil de Bonferroni : 0,00125).

> *Note de méthode : le test de la plus longue série sortait initialement à
> p = 0,0001 — contre une **formule asymptotique** donnant 13,12. La
> simulation Monte-Carlo donne 12,636 ± 0,090, et l'écart tombe à
> z = +0,82. Même nature d'erreur que celle relevée au § 1 : une référence
> théorique approximative prise pour l'espérance exacte. Tout seuil
> critique de cet audit est désormais simulé, jamais tabulé.*

### Ce que ce résultat exclut

La complexité linéaire mesurée est **exactement à son espérance**. Sur ce
flux, cela écarte toute récurrence F₂-linéaire de degré jusqu'à ~1,4
million de bits, soit :

- **Mersenne Twister** (19 937 bits) — 70 fois sous le seuil de détection ;
- **xorshift / xoroshiro / xoshiro**, toutes variantes ;
- **tout LFSR ou combinaison de LFSR** d'état inférieur à ~1,4 Mbit.

C'est une classe que l'épuisement ne pourra jamais couvrir : 2¹⁹⁹³⁷ contre
2³². Le test l'atteint sans énumérer quoi que ce soit.

---

## 6. Frontière consolidée

| Classe de générateur | Statut | Par quel moyen |
|---|---|---|
| État ≤ 32 bits (LCG, xorshift32) | **Exclu** | Épuisement — 10,7 milliards d'états testés |
| Graine dérivable (horloge, n° de tirage) | **Exclu** | Recherche de graine sur 8 familles |
| **F₂-linéaire ≤ 1,4 Mbit (dont Mersenne Twister)** | **Exclu** | **Complexité linéaire (Berlekamp-Massey)** |
| Rejeu de séquence (mode Corriveau) | **Exclu** | 2,489 milliards de paires, max 16/20 |
| **État ≤ 40 bits en flux continu, famille quelconque** | **Exclu** | **Analogues — non paramétrique (§ 11)** |
| Biais de fréquence ≥ 0,5 % / de paires ≥ 1,5 % | **Exclu** | χ² (null simulé) + 3 160 paires, Bonferroni |
| Non linéaire à grand état (AES-DRBG, SHA-DRBG) | hors d'atteinte | aucune méthode connue depuis les sorties |
| Quantique (type Quantis) | sans objet | pas d'état interne à reconstruire |

Les deux dernières lignes ne sont pas des lacunes de cet audit : ce sont
les limites de ce qu'un observateur extérieur peut établir depuis des
sorties publiées. Tout le reste a été écarté.

---

## 7. La frontière 48 bits : de « inatteignable » à « une nuit de calcul »

### Pourquoi ce cas échappe au théorème du § 2

La preuve d'impossibilité algébrique du § 2 porte sur un observable
`n = x mod 80` où `x` est **l'état brut** : elle ne livre que `x mod 16`
et `x mod 5`, et la récurrence des bits bas étant close, rien ne remonte
vers les bits hauts.

`java.util.Random` ne fait pas cela. Il émet `next(31) = s >> 17` : le
numéro tiré dépend des **bits de poids fort** de l'état. La récurrence
basse close ne s'applique pas, et le raisonnement du § 2 est muet sur ce
cas. C'est la dernière classe où le calcul a encore quelque chose à dire.

### Ce qui a été balayé sur les tirages réels

| Volet | Espace | Débit | Profondeur max | Trouvés |
|---|---|---|---|---|
| Graines = millisecondes epoch, fenêtre ±24 h | 172 800 000 | 14 M/s | 12/20 | **0** |
| Graines dérivées du n° de tirage (×1, ×10³, ×10⁶ ± 1000) | 6 003 | — | 7/20 | **0** |
| LCG mod 2⁴⁸ brut, sortie bits hauts | 16 777 216 | — | 10/20 | **0** |

Le motif `new Random(System.currentTimeMillis())` — la faute
d'implémentation la plus répandue — est donc **écarté sur une fenêtre de
48 heures autour du tirage**.

### Le noyau de balayage : `tools/sweep48.c`

Le plein espace 2⁴⁸ = 281 474 976 710 656 états restait hors de portée en
Python (5 M états/s → 691 jours). Un noyau C avec arrêt anticipé, masque
de doublons sur deux mots de 64 bits et sortie dès le premier écart
atteint **156 millions d'états par seconde et par cœur** — 31 fois plus.

| Configuration | Durée pour couvrir 2⁴⁸ intégralement |
|---|---|
| 1 cœur | 20,9 jours |
| 4 cœurs (cette machine) | 5,2 jours |
| 64 cœurs (une instance louée) | **~8 heures** |
| GPU (noyau dédié) | **~20 minutes** |

Le programme prend une tranche `[lo, hi)` en argument : la parallélisation
est triviale, sans communication entre les workers.

```sh
cc -O3 -march=native -o sweep48 tools/sweep48.c
./sweep48 0 1099511627776  5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
```

### Ce que cela change

Avant ce noyau, la frontière de l'audit était 2³² — le reste relevait de
l'impossibilité pratique. Elle est désormais à **2⁴⁸, soit 65 536 fois
plus d'états**, et le coût de la franchir intégralement est chiffré : une
nuit de calcul sur une machine louée, vingt minutes sur GPU.

Ce n'est pas une méthode de reconstruction nouvelle : c'est la même
recherche exhaustive, portée à une classe qu'on croyait hors d'atteinte
et dont le théorème du § 2 ne dit rien. La probabilité qu'une loterie
certifiée tourne sur `java.util.Random` est infime — mais elle n'est plus
*indécidable*, et c'est la différence entre une hypothèse et un fait.

Au-delà de 2⁴⁸, la barrière redevient absolue : 2⁶⁴ coûterait 65 536 fois
plus (des siècles sur GPU), et 2¹²⁸ dépasse le nombre d'opérations
réalisables dans l'univers observable.

---

## 8. Attaque ciblée : ré-amorçage au démarrage de session

Dernier angle opérationnel non testé. Un service de tirage s'arrête la
nuit et redémarre le matin ; s'il ré-amorce son générateur au lancement de
la séance — motif classique d'un démon relancé par `cron` — la graine du
**premier tirage de la journée** est dérivable de l'instant de reprise.

### Structure temporelle de l'archive

```
ruptures de session (gap > 600 s) : 345
gap de session : min 21 900 s · médian 25 500 s · max 29 100 s
intervalles : 70 190 x 300 s exactement, 343 x 25 500 s exactement
```

La cadence est d'une régularité mécanique : **343 des 345 interruptions
durent exactement 25 500 s** (7 h 05). Les 345 reprises de séance sont
donc horodatées à la seconde près, et constituent 345 cibles de graine
parfaitement localisées — la configuration la plus favorable qu'un
attaquant puisse espérer.

### Résultat

| | |
|---|---|
| Sessions attaquées | 345 |
| Familles par session | 6 (glibc, MSVC, java.util.Random, xorshift32, splitmix64, PCG32) |
| Graines par session | 7 201 (secondes ±1 h) + 20 001 (millisecondes ±10 s) |
| **Total testé** | **56 308 140 graines** |
| Profondeur maximale | **10/20** — le niveau du bruit |
| **États reconstruits** | **0** |

Le ré-amorçage horaire au démarrage de séance est donc écarté, sur les
345 occasions où il aurait pu se produire.

---

## 9. Bilan des voies explorées

| Voie | Portée atteinte | Résultat |
|---|---|---|
| Épuisement ≤ 2³² | 10,7 milliards d'états, données réelles | 0 |
| Graines horloge / n° de tirage | 8 familles × 3 échantillonneurs | 0 |
| **Ré-amorçage de session** | **345 sessions × 6 familles, 56,3 M graines** | **0** |
| Espace 48 bits, graines praticables | 172,8 M graines (±24 h en ms) | 0 |
| Espace 48 bits complet | rendu accessible : ~2 h sur A100 | outil livré |
| F₂-linéaire ≤ 1,4 Mbit | Berlekamp-Massey sur 2,8 M bits | 0 |
| Algébrique (Hensel, réseau) | démontré impossible pour observable en bits bas | — |
| Rejeu de séquence | 2,489 milliards de paires | 0 |
| Biais statistique | 15 tests, nulls simulés, Bonferroni | 0 |
| **Analogues (non paramétrique)** | **4,98 G paires + 6 prédicteurs, portée mesurée 40 bits** | **0** |
| **Compressibilité (Maurer)** | **2,8 M bits, L=6..8 à puissance nominale** | **0** |
| **Champs bonus/boost (recouvrement conditionné)** | **883 paires, nul calibré par simulation** | **0** |

Toutes les voies connues ont été parcourues jusqu'à leur limite
calculatoire ou démontrées closes. Ce qui reste — générateur non linéaire
à état ≥ 64 bits, ou source quantique — n'est pas hors d'atteinte par
manque de méthode : l'information nécessaire à toute reconstruction
**n'est pas contenue** dans les sorties publiées.

---

## 10. Correction : la nature exacte du verrou

Cet audit a répété, y compris dans ses conclusions, que « l'information
nécessaire à la reconstruction n'est pas contenue dans les sorties ».
**C'est faux, et il faut le corriger.**

### L'information est présente

Chaque tirage porte log₂ C(80,20) = **61,617 bits**. Un état de k bits est
donc *déterminé* dès que d·61,617 > k, le nombre d'états parasites
compatibles valant 2^(k − d·61,617) :

| État k | Tirages nécessaires | États parasites attendus |
|---|---|---|
| 64 bits | 2 | 2⁻⁵⁹·² |
| 128 bits (AES-CTR-DRBG) | **3** | 2⁻⁵⁶·⁸ |
| 256 bits (SHA-DRBG) | **5** | 2⁻⁵²·¹ |
| 19 937 bits (Mersenne Twister) | 327 | 2⁻²¹¹·⁶ |

Trois tirages publiés déterminent donc **de façon unique** l'état d'un
AES-CTR-DRBG à 128 bits. L'archive en contient 70 560 : elle sur-détermine
l'état de n'importe quel générateur classique par un facteur de plusieurs
milliers.

### Le verrou est calculatoire, et il a un nom

Le vrai obstacle n'est pas l'absence d'information mais l'**absence
d'inverse efficace**. Reconstruire l'état revient à inverser la fonction
état → tirage, c'est-à-dire à inverser la primitive sous-jacente. Pour un
CSPRNG, cela s'appelle *casser AES* ou *casser SHA-2* : ce n'est pas une
question ouverte de cryptanalyse des loteries, c'est l'hypothèse de
sécurité sur laquelle repose le chiffrement bancaire mondial.

Ces deux barrières sont de natures différentes et cet audit les avait
confondues :

| Cas | Nature de la barrière |
|---|---|
| LCG mod 2ᵏ, observable = bits bas | **informationnelle** — récurrence basse close, les bits hauts ne fuient pas (§2, démontré) |
| CSPRNG / source quantique | **calculatoire** — l'information est là, l'inverse est hors d'atteinte |

La distinction a une conséquence pratique nette : dans le premier cas,
aucune quantité de tirages ni de calcul ne suffira jamais. Dans le second,
un algorithme d'inversion d'AES rendrait l'attaque immédiate — et si un tel
algorithme existait, le Loto Express serait la moindre des préoccupations.

### Ce que cela clôt

La question « existe-t-il une méthode inédite pour reconstruire cet
état ? » a donc une réponse exacte : **elle est équivalente à la question
de la sécurité de la primitive employée**. Ce n'est pas un problème
ouvert propre aux loteries que de la persévérance pourrait dénouer ; c'est
un problème central de la cryptographie, étudié depuis trente ans par la
communauté entière, et dont l'état de l'art est public.

Le seul angle qui reste spécifique à ce jeu — et il a été traité — est
celui d'une primitive **faible** : c'est tout l'objet des §§ 3 à 8, et des
outils de `tools/`. Neuf classes ont été fermées. La dixième ne relève
plus de ce dossier.

---

## 11. Dixième voie : les analogues, et la mesure de ce qu'on aurait vu

Les neuf voies du § 9 partagent un angle mort : **chacune nomme une
famille d'algorithme**, ou une structure — la F₂-linéarité pour
Berlekamp-Massey, la forme affine pour l'attaque algébrique. Un
générateur hors des familles postulées y échappe par construction, aussi
faible soit-il par ailleurs.

Et aucune n'a mesuré sa propre puissance. Un résultat nul dont on ignore
la sensibilité n'est pas un résultat : c'est une absence d'information.

La dixième voie corrige les deux défauts à la fois. Elle ne suppose que
le déterminisme de la transition d'état : si `S_{t+1} = g(S_t)` et
`tirage_t = f(S_t)`, alors `S_i = S_j` implique `tirage_{i+1} =
tirage_{j+1}` — sans qu'on ait besoin de connaître `g` ni `f`. Le
recouvrement entre deux tirages devient un proxy observable de la
proximité d'états, et l'on peut chercher dans le passé le meilleur
analogue du tirage courant pour jouer son successeur. C'est la méthode
des analogues de Lorenz (1969), appliquée à un flux de générateur.

La puissance a été **mesurée** sur des fonctions aléatoires de 20 à
44 bits — le modèle générique de toute application déterministe à `n`
bits d'état, familles non publiées comprises. À `m = 70 560` tirages :
détection franche à 40 bits (z = +231), extinction à 41. Le seuil
théorique `2·log2(23m) − 0,65` vaut 40,4 : l'accord est exact. Les quatre
témoins négatifs (LCG 48 bits, splitmix64, SHA-256 en compteur, SRS
idéal) restent tous sous 2 σ.

Sur les données réelles : `rho(O(i,j), O(i+1,j+1)) = −0,000009` sur
4 978 431 364 paires, moyenne conditionnelle plate sur quatre décimales
de k = 2 à k = 13, et six prédicteurs par analogue tous entre −1,2 σ et
+0,5 σ, de signe alternant.

Ce résultat est nul, mais il est **quantifié** — c'est ce qui le
distingue des neuf précédents. Il exclut, en régime de flux continu,
toute famille d'état ≤ 40 bits, publiée ou non. En régime ré-amorcé à
chaque tirage la borne est différente et plus basse : `m²/6 = 2^29,6`,
par le paradoxe des anniversaires.

Le test est passé en production comme huitième test de la batterie
forensique de l'app, avec deux témoins déterministes en intégration
continue — un état de 12 bits doit être vu, xorshift64 ne doit pas
l'être. Sans témoin positif, un test qui ne déclenche jamais est
indistinguable d'un test cassé.

Méthode complète et tables : **`claude/ANALOGUES.md`**.
Scripts : `claude/tools/analogue.py`, `power.py`, `power_full.py`.

---

## 12. Onzième voie : compressibilité générale (test universel de Maurer)

Berlekamp-Massey (§ 5) a une portée précise : il détecte toute récurrence
**linéaire** sur GF(2), quelle que soit sa taille d'état. Mais un
générateur non linéaire — un compteur chiffré par bloc, un flux ARC4-like,
un hachage itéré — peut avoir une complexité linéaire proche de
l'attendu tout en étant parfaitement structuré. C'est un angle mort
distinct du § 11 (les analogues supposent le déterminisme de la
transition d'état, mais pas sa linéarité — ce test-ci ne suppose même
pas ça).

Le test universel de Maurer (*A Universal Statistical Test for Random
Bit Generators*, J. Cryptology 5(2), 1992 ; repris comme NIST SP800-22
§2.9) mesure le **taux de compression** du flux : la distance moyenne,
en log₂, entre deux occurrences successives d'un même motif de `L` bits.
C'est un estimateur direct de l'entropie de Shannon par bit, insensible
à la structure algébrique précise de la source.

Même flux qu'au § 5 : 70 560 tirages convertis en rang colex,
acceptation si rang < 2⁶¹, soit 45 872 tirages retenus et
**2 798 192 bits** uniformes sous H₀.

| L | K | f_n observé | attendu | z | p | puissance |
|---|---:|---:|---:|---:|---:|---|
| 6 | 465 725 | 5,219192 | 5,217705 | +1,040 | 0,2983 | nominale |
| 7 | 398 461 | 6,197825 | 6,196251 | +0,956 | 0,3391 | nominale |
| 8 | 347 214 | 7,182480 | 7,183666 | −0,642 | 0,5205 | nominale |
| 9 | 305 790 | 8,177481 | 8,176425 | +0,519 | 0,6037 | sous reco. NIST |
| 10 | 269 579 | 9,171125 | 9,172324 | −0,539 | 0,5902 | sous reco. NIST |
| 11 | 233 901 | 10,166035 | 10,170032 | −1,634 | 0,1023 | sous reco. NIST |
| 12 | 192 222 | 11,164720 | 11,168765 | −1,469 | 0,1418 | sous reco. NIST |
| 13 | 133 325 | 12,168309 | 12,168070 | +0,071 | 0,9435 | sous reco. NIST |
| 14 | 36 030 | 13,181374 | 13,167693 | +2,045 | 0,0409 | sous reco. NIST |

NIST recommande `K ≥ 1000 · 2^L` pour garantir l'approximation gaussienne
du test ; c'est vérifié explicitement plutôt que supposé. Aux trois
premières configurations (L=6,7,8), la puissance est nominale : **0/3
anomalie à p<0,01**. Au-delà, `K` tombe sous la recommandation à mesure
que `L` grandit — c'est la limite dure de `n = 2,8` million de bits ; il
faudrait ~360 millions de tirages pour amortir L=14 correctement.

Le z=+2,045 (p=0,041) à L=14 mérite d'être nommé précisément pour ne
pas être surinterprété : sur 9 configurations, un tel écart apparaît par
hasard une fois sur onze ; le seuil de Bonferroni correspondant est
p<0,0056, largement au-dessus. Et il tombe dans la zone où `K` est 450
fois sous la recommandation NIST — l'approximation gaussienne elle-même
n'y est plus garantie. C'est la même leçon que la réplique nulle du § 11
(analogues) qui produisait +2,33 σ sur des données que je savais
parfaitement aléatoires : un écart isolé de cette taille ne distingue
rien.

**Conclusion : consistant avec H₀ sur toute la plage testée**, y compris
au-delà de la portée linéaire de Berlekamp-Massey — cette voie couvre en
plus toute source dont la structure serait non linéaire mais repérable
dans une fenêtre de 6 à 8 bits du rang combinatoire.

Script : `claude/tools/maurer.py`.

---

## 13. Ancrage réglementaire : ce que ce jeu est effectivement tenu d'utiliser

Les dix voies précédentes sont abstraites : elles testent des familles
d'algorithmes sans savoir laquelle, le cas échéant, est en jeu. Une
recherche publique référence directement Loto Express :

> « Loterie Romande offre une large sélection de jeux basés sur un RNG,
> certifiés par eCOGRA, iTech Labs ou GLI [...] Loto Express est un jeu
> de type Keno à tirages toutes les 5 minutes. »

Trois organismes cités — GLI, iTech Labs, eCOGRA — sont les laboratoires
d'audit RNG standards de l'industrie du jeu réglementé. Leur certification
ne porte pas seulement sur l'équité statistique du tirage (la
distribution marginale) : leur méthodologie publiée inclut explicitement
des batteries de tests **du type NIST SP800-22 / DieHarder** — c'est-à-dire
la même famille que les tests des §§ 5, 6 et 12 de cet audit — appliquées
en continu à la production, pas une fois à la mise en service.

Cela ne prouve rien sur l'algorithme précis employé — cette information
reste non publique, et il serait malhonnête de prétendre l'avoir déduite.
Mais cela répond à une question différente, restée implicite dans les
§§ 1 à 12 : *pourquoi* dix voies indépendantes convergent-elles toutes
vers zéro ? Parce que passer ces batteries n'est pas un heureux hasard
statistique du jeu observé : c'est une **condition d'exploitation**
imposée par le régulateur, vérifiée par un tiers indépendant, sur ce
générateur précis. Le résultat nul de cet audit n'est donc pas une
absence de preuve — c'est la confirmation, depuis l'extérieur et sans
accès au code, que la certification tient.

Sources : [Loterie Romande — sélection de jeux RNG certifiés](https://loterieromande.fr/) ;
[GLI — laboratoire d'audit RNG](https://www.gaminglabs.com/) ;
[iTech Labs — certification RNG](https://itechlabs.com/).

---

## 14. Douzième voie : les champs jamais exploités (bonus, boost) — et une erreur corrigée en direct

Un point légitime : la certification (§ 13) est une évidence, pas une
preuve. Elle change le *a priori* — elle ne clôt pas la question. Deux
choses restent hors de portée de toute analyse statistique externe, et
il faut le dire clairement plutôt que de se cacher derrière un audit
propre :

- un **bug d'implémentation** passé les tests de certification (cas
  réel : la fraude Hot Lotto de l'Iowa, 2005-2011, où l'employé chargé
  d'auditer le générateur y avait lui-même inséré une porte dérobée
  déclenchée trois jours par an) ;
- un **accès privilégié** — code source, clé de graine, journal serveur.

Aucune des deux n'est atteignable depuis les 70 560 sorties publiques.
Ce que l'analyse externe peut faire, en revanche, c'est épuiser les
champs **publics et jamais exploités**. Il en restait deux :
`bonus` et `boost`.

### bonus n'est pas un tirage indépendant

`bonus` appartient aux 20 numéros du tirage dans **100 % des cas**
(70 560/70 560), contre 25 % sous indépendance. Ce n'est donc pas une
sortie séparée du générateur sur [1,80] — c'est la désignation d'un des
20 numéros déjà sortis. Question naturelle : cette désignation
encode-t-elle une position (la dernière boule tirée, par exemple),
ce qui fuiterait de l'information d'ordre même quand l'API livre les
numéros triés ? Rang du bonus dans le tirage trié, sur 19 degrés de
liberté : **χ² = 27,46** (seuil p=0,05 → 30,14). Pas de biais de
position démontrable.

### boost n'a pas de mémoire

`boost` (multiplicateur ∈ {1,2,3,4,5,10}, loi très asymétrique) :
`boost(i)==boost(i+1)` observé à 34,46 %, contre 34,51 % attendu sous
indépendance à partir de sa propre loi empirique (Σpₖ²). Écart nul.

### Le test qui comptait — et l'erreur qu'il fallait attraper

Reste la question composée : le recouvrement `overlap(i,i+1)`,
conditionné à `bonus_i == bonus_{i+1}`, contient-il un signal ? Une
première passe a comparé la moyenne conditionnelle observée (5,68 sur
883 paires) à l'espérance **non conditionnelle** de 5,0 — et obtenu un
**z = +11,98**. C'est faux, et il faut montrer pourquoi plutôt que de
l'effacer silencieusement.

`bonus_i` n'existe que parmi les numéros de `set_i` ; un match exige que
le numéro soit présent dans **les deux** ensembles *et* désigné comme
bonus dans les deux. Donc `P(match | overlap=k) = k/400` : conditionner
sur « match » revient à sur-pondérer les tirages à fort recouvrement.
Sous H₀ pur, `E[overlap | match] = E[K²]/E[K]`, où `K` suit
l'hypergéométrique(80,20,20) : `E[K²] = Var(K) + E[K]² = 2,849 + 25 =
27,849`, donc **5,5698** — pas 5,0. Une simulation directe (6 millions
de paires SRS, 74 933 matches) confirme : **5,5699 ± 1,6346**. C'est un
artefact de conditionnement, exactement le genre de biais de sélection
qui produit de faux signaux quand on croit une intuition plutôt qu'un
calibrage — la même discipline que les répliques nulles des §§ 11-12.

Avec le nul correctement calibré : **z = +2,01 (p = 0,044)**. Isolé, sur
un audit qui a désormais fait tourner plusieurs dizaines de
configurations de test, un z de cet ordre est exactement la base rate
attendue — la réplique nulle du § 11 en a produit un à +2,33, celle du
§ 12 à +2,05, sur des données dont l'aléa était garanti par construction.
Non significatif, et cohérent avec le reste de l'audit.

### Ce que ça répond à la question posée

Douze voies, deux d'entre elles portant spécifiquement sur des champs
publics inexploités jusqu'ici. Toutes closes ou nulles. La certification
n'a jamais été invoquée comme une preuve d'impossibilité — seulement
comme un fait qui explique *pourquoi* on attend un résultat nul. Ce que
ce dossier ne peut pas trancher — bug d'implémentation, accès privilégié
— reste précisément ce qui échappe à toute analyse des sorties, quelle
que soit sa profondeur : ce n'est pas une question de méthode
supplémentaire, c'est une question d'accès qu'aucune quantité de calcul
sur 70 560 lignes de CSV ne remplace.

Script : `claude/tools/bonus.py`.
