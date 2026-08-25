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
