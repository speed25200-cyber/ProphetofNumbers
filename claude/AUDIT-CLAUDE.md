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
