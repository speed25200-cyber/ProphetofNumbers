# Loto Express — recherche de faille exploitable

Audit offensif de l'archive complète : 70 560 tirages (ids 1309614–1380173,
2025-09-14 → 2026-08-25, 0 trou). Objectif : prédire tout ou partie des 20 numéros.

Tout le code est dans [`research/`](research/) et rejouable hors ligne.

> **Mise à jour du 4 septembre 2026 :** l'audit de reprise et le protocole
> opérationnel corrigé sont dans [`REPRISE_ETAT.md`](REPRISE_ETAT.md). En
> particulier, le REST est maintenant confirmé trié, le seuil de 300 tirages n'est
> pas robuste et `keno_break` ne couvre pas encore rejet/Java. Les formulations
> historiques trop générales ci-dessous ne doivent pas être lues comme des preuves
> au-delà des configurations explicitement testées.

---

## 1. Résumé

| Ligne d'attaque | Verdict |
|---|---|
| Structure statistique de l'historique publié | **Aucune.** 250 prédicteurs, 2,49 G de paires, 82 160 triplets, 60 000 lags, batterie NIST : rien au-delà du bruit |
| Initialisations 32 bits (234 variantes algorithmiques) | Configurations balayées rejetées ; pas les états arbitraires plus larges |
| Dérivation par hash de données publiques (« provably fair ») | 390 schémas testés sans correspondance |
| Reconstruction d'état à partir des tirages **triés** | **Barrière combinatoire** : 20! ≈ 2,4·10¹⁸ ordres par tirage |
| Générateurs F2-linéaires via canaux `bonus`/`boost` | Configurations implémentées rejetées sous leurs hypothèses de canal et de stride ; pas une exclusion de toute la famille |
| Générateur congruentiel à sortie en bits faibles | **Exclu** — récurrences modulaires d'ordre 1 et 2 mod 2…16 |
| LCG 2⁶⁴ à sortie de poids fort | 2 880 réductions LLL sans correspondance ; résultat heuristique sans reconstruction/replay |
| Reconstruction d'état à partir des tirages **ordonnés** | Cassage complet démontré sur données synthétiques ; aucune capture LoRo ordonnée validée à ce jour |

**Conclusion opérationnelle :** les tests versionnés n'ont détecté aucune structure
prédictive hors échantillon dans l'historique publié. Cela borne les signaux et les
modèles effectivement testés ; ce n'est pas une preuve universelle d'absence
d'information.
La voie prioritaire est l'**ordre de sortie des boules**. Les endpoints REST sont
confirmés triés en amont ; le candidat réel est `meta[lang].balls` dans le flux
d'animation SignalR, désormais capturable par `research/capture_order.py`.

---

## 2. Correction d'une erreur du rapport précédent

`REPORT.md` annonce χ²/df = 0,68 et en conclut une sous-dispersion.
C'est un artefact de normalisation : le dénominateur utilisé est l'espérance
`E = N·p = 17 640` au lieu de la variance `Var = N·p(1−p) = 13 230`.
Le facteur est exactement 0,75 — d'où les 12 mois sur 12 « sous 1 ».

Valeur correcte : **Σz² = 71,46** pour E = 80, sd = 12,73 → **z = −0,67**.
Uniformité parfaite. Aucune sous-dispersion, donc aucun mécanisme d'équilibrage
(« deck », rappel de boules) — ce que confirme le test de rapport de variance
sur 15 fenêtres (W = 2 … 4000) : tous les ratios à 1,000 ± 0,006.

---

## 3. Ce qui a été testé (et n'a rien donné)

| # | Test | Résultat | Attendu |
|---|---|---|---|
| E8 | Uniformité marginale corrigée | Σz² = 71,46, max\|z\| = 2,72 | 80 ± 12,7 |
| E9 | Rapport de variance, 15 fenêtres | ratios 0,995–1,007 | 1 |
| E10 | Statistiques d'ordre des 20 positions | max\|z\| = 1,60 | — |
| E11 | Somme mod 2…81, XOR des 20 | rien (max z = +2,38 sur 16 tests) | — |
| E4 | Rang GF(2) de la matrice 70560×80 | 79/80 (seule la parité, poids 20 pair) | 79 |
| **pairs** | **Overlap des 2 489 321 520 paires** | **accord hypergéométrique exact, max overlap 16** | 16 |
| E15 | 82 160 triplets de numéros | Σz² = 81 436, z = −1,79 | 82 160 |
| E12 | Périodogramme, 35 280 fréquences × 80 séries | max z = +4,59 | ~4,5 |
| **E19** | **Overlap moyen à CHAQUE lag 1…60 000 (FFT)** | **max \|z\| = 4,16** | ~4,69 |
| E14 | Autocorrélation lags 1–40 | max \|z\| = 1,99 | — |
| E17 | 216 créneaux horaires × 80 numéros | Σz² = 17 176 / 17 280 | — |
| E18 | 346 premiers tirages du jour (démarrage à froid) | Σz² = 110 / 80 | — |
| E20 | Canal boost : marginal, paires, triplets, runs, vs numéros | tout à 0 | — |
| E21 | Canal bonus : rang, paires de rangs, vs boost | tout à 0 | — |
| **score** | **250 prédicteurs (lags 1–200, fenêtres 2–30 000, gaps, co-occurrence, créneaux, bonus)** | **0 test au-delà de \|z\| = 3**, Σz² = 239,2/250 | 250 ± 22 |
| **NIST** | Flux uniforme 2 798 192 bits extrait des rangs colex : monobit, blocs, runs, rang matriciel 32×32, DFT, serial m=8/12/16, cusum, **complexité linéaire** | tout conforme (L = 2500,22 vs 2500,17) | — |
| — | Compression zlib / bzip2 / lzma | **incompressible** (+0,02 %) | — |
| E22 | Histogramme d'overlap lag-1 vs hypergéométrique exact | χ²=30,1 df=12 → **ne se réplique pas** (E29) | 12 |
| E23 | Overlap triple \|Aₜ ∩ Aₜ₊₁ ∩ Aₜ₊₂\| | χ²=5,66 df=6, moyenne 1,2484 vs 1,25 | 6 |
| E24/E28 | Composition en 21 gaps, paires de gaps consécutifs | χ²=2759 — **sous les 4 contrôles SRS** (2848–2968) : artefact du modèle nul | — |
| E26 | #impairs, #bas, somme vs hypergéométrique exact | z = +1,82 / +0,72 / +1,29 | — |
| **hash** | 390 schémas « provably fair » (6 hashs × 13 entrées publiques × 5 dérivations) | chance pure (max 11/20) | ~10/20 |
| **seed** | Balayage 2³² **complet et terminé**, 224 combinaisons × 4,29·10⁹ graines = **9,62·10¹¹ essais**, plus 10 générateurs de plateforme, plus MT/glibc avec 64 décalages sur la plage des timestamps unix, plus les graines en millisecondes (16 familles PRNG × 4 mappings × 4 échantillonneurs, + .NET, V8, Python `random.sample`, PHP `mt_rand`) | meilleur **15/20**, exactement le modèle nul | voir ci-dessous |

### Le balayage 2³² colle au modèle nul, ce qui prouve qu'il cherchait bien

Une graine fausse survit à l'étape *i* de Fisher-Yates avec probabilité (20−i)/(80−i),
pas 1/4 : le vivier rétrécit en même temps que le nombre de cibles restantes. La loi
du « plus long préfixe correct » est donc entièrement prévisible.

| k | P(≥ k) | graines attendues / combo | combos attendus avec max ≥ k | observés |
|---|---|---|---|---|
| 12 | 2,09·10⁻⁹ | 8,98 | 224 | 189 |
| 13 | 2,46·10⁻¹⁰ | 1,06 | 146 | 108 |
| 14 | 2,57·10⁻¹¹ | 0,11 | 23,4 | 17 |
| 15 | 2,34·10⁻¹² | 0,01 | **2,2** | **3** |
| 16 | 1,80·10⁻¹³ | 0,00 | 0,2 | 0 |

`P(20/20) = 2,83·10⁻¹⁹ = 1/C(80,20)` ; sur 9,62·10¹¹ essais cela fait **0,0000**
attendu. Le maximum observé sur tout le balayage est 15/20, et les 3 combos qui
l'atteignent sont exactement les 2,2 prévus. Le balayage n'a rien trouvé — et la
correspondance avec le nul montre qu'il cherchait correctement.

### Discipline sur les faux positifs

Deux écarts apparents ont été poursuivis jusqu'à réfutation, pas écartés à la main :

- **χ² du lag-1 = 30,1 (z = +3,69).** Profil sur les lags 1…60 : moyenne 12,46 pour
  E = 12, et lag-1 n'est que le maximum de 60 tirages de χ²₁₂ (p ≈ 0,15).
  Réplication moitié/moitié : **5/12 cellules de même signe** (p = 0,77), la cellule
  k=8 passe de +1,05 à +3,50, et la corrélation inter-moitiés du taux de répétition
  par numéro vaut **−0,133** (elle devrait être positive). Fluctuation.
- **χ² des paires de gaps = 2759 (z = +274).** Mon modèle nul était faux : les 21 gaps
  somment à 60, donc ils sont dépendants par construction. Quatre archives SRS
  synthétiques donnent 2848, 2954, 2848, 2968 — la valeur réelle est **inférieure**
  à toutes. Aucun effet.

**Test non paramétrique par analogues** (`analog.c`) — le test de score et le modèle
logistique sont linéaires en leurs features ; celui-ci ne l'est pas. Pour chaque tirage
retenu, on cherche les contextes historiques (1 à 3 tirages précédents) les plus
ressemblants, on met en commun ce qui les a effectivement suivis, et on joue les
numéros les plus fréquents. Toute structure locale — biais conditionnel, attracteur,
motif répétitif que les tests linéaires moyennent — apparaîtrait ici.

| voisins | numéros joués | contexte | z (choix) | z (anti-choix) |
|---|---|---|---|---|
| 400 | 10 | 2 tirages | **−0,07** | +0,58 |
| 100 | 5 | 1 tirage | +1,17 | +1,46 |
| 2000 | 20 | 3 tirages | −0,89 | +1,23 |

Une vraie structure séparerait les deux colonnes ; ici elles bougent ensemble.

Modèle prédictif hors-échantillon (13 460 tirages retenus, 13 features, pas de Newton exact) :
gain de log-loss **−8,9·10⁻⁶ bit**, et le tirage des k meilleurs numéros est
indistinguable du tirage des k pires (k = 5 : z = +1,19 ; k = 10 : z = −0,09).

---

## 4. Bornes rigoureuses sur tout biais exploitable

Test de score exact, pondérations centrées dans chaque tirage
(facteur de variance `p(1−p) − (p₂−p²) = 0,1898734`).
« Limite » = décalage de probabilité minimal détectable à 3σ :

| Prédicteur | Biais détectable à 3σ |
|---|---|
| « était dans le tirage précédent » | \|ΔP\| ≤ 0,00127 |
| log-écart depuis la dernière sortie | \|ΔP\| ≤ 0,00093 / unité |
| fréquence sur 20 tirages | \|ΔP\| ≤ 0,0057 / unité |
| taux marginal d'un numéro | \|ΔP\| ≤ 0,00489 (observé max 0,00444) |

La marge maison d'un keno se situe entre 30 % et 50 %. Il faudrait donc un biais
de l'ordre de ΔP ≈ 0,05–0,10. Le plafond mesuré est ~10⁻³.
**Rapport requis/disponible : 75× à 125×.** Ce n'est pas une hypothèse, c'est une mesure.

---

## 5. Le résultat central : les tests statistiques sont le mauvais outil

Calibration décisive (`calib.py`). Trois archives synthétiques de 70 560 tirages,
générées avec le **même** échantillonneur Fisher-Yates :

| Source | χ² z | lag-1 z | max z sur 50 000 lags | Cassable ? |
|---|---|---|---|---|
| xorshift32 (2³² états) | +0,24 | +0,78 | 4,65 | **oui, en secondes** |
| MINSTD (2³¹ états) | +0,61 | +0,61 | 4,32 | **oui, en secondes** |
| PCG64 (fort) | +0,57 | −0,10 | 4,37 | non |
| **Loto Express réel** | −0,67 | +0,29 | 4,16 | ? |

Un générateur **totalement cassable** est statistiquement indistinguable d'un
générateur fort à N = 70 560. Donc : *« l'archive est uniforme »* ne dit **rien**
sur la prédictibilité. Seule la **reconstruction d'état** tranche.

C'est pourquoi l'effort est passé du statistique à l'algébrique.

---

## 6. Cassage complet démontré — `mtbreak.c`

MT19937 (le générateur logiciel le plus répandu, 19 937 bits d'état) est
**F2-linéaire** : chaque bit de sortie est une forme linéaire connue des bits d'état.

Avec l'**ordre de tirage**, chaque indice Fisher-Yates `j_i = (u·k)>>32` fixe
l'intervalle de la sortie 32 bits `u`, donc ses bits de tête :
**4,5 bits certains par sortie × 20 sorties = 90 bits par tirage.**

L'attaque : propager symboliquement l'état (624 mots × 32 bits, chacun un vecteur
de 19 968 bits), en extraire les formes linéaires des bits connus, résoudre par
élimination de Gauss sur GF(2), remonter l'état, rejouer le générateur.

```
$ ./mtbreak 400 0xC0FFEE42 0
  linear equations used: 35842 (4.48 known bits per output)  rank=19937/19968  [5.2s]
  RESULT: observed draws reproduced 400/400 ; FUTURE draws predicted 50/50
  *** FULL BREAK: every future draw predicted exactly ***
```

Le rang atteint **19 937/19 968** — exactement la dimension réelle de MT19937
(les 31 bits bas de `mt[0]` sont sans effet). Ce n'est pas un ajustement :
les 50 tirages suivants, jamais montrés au solveur, sont prédits **exactement**,
les 20 numéros à chaque fois.

Le seuil dépend de la graine et du rang des contraintes. À 300 tirages, la graine
de démonstration ne donne que 19 935/19 937 dimensions observables : le résultat est
**inconclusif**, même si une complétion arbitraire passe un court holdout. La cible
prudente vérifiée est **400 tirages** pour `mulhi` ; voir `REPRISE_ETAT.md`.

| tirages | rang | tirages observés rejoués | tirages futurs prédits |
|---|---|---|---|
| 230 | 19 633 | 2/230 | 0/50 |
| 250 | 19 894 | 55/250 | 0/50 |
| 270 | 19 928 | 183/270 | 26/50 |
| **300** | **19 935 sur la graine publiée** | **300/300 pour une complétion** | **inconclusif** |
| **400** | **19 937** | **400/400** | **50/50** |

La phase absolue peut être absorbée par une représentation canonique de l'état. En
revanche, le nombre de mots consommés par tirage doit être modélisé : `keno_break`
balaie maintenant un stride fixe `W`, et distingue rejet, rang insuffisant et
récupération validée sur holdout.

### Généralisation — tirages ordonnés nécessaires par famille

90 bits utiles par tirage, marge ×1,35 mesurée :

| Générateur | bits d'état | tirages ordonnés | observation |
|---|---|---|---|
| xorshift32, MINSTD | 31–32 | 1 (ou force brute 2³²) | 5 min |
| `java.util.Random` | 48 | 1 | 5 min |
| LCG64, PCG32, splitmix64 | 64 | 1–2 | 10 min |
| xorshift128, xoshiro128 | 128 | 2 | 10 min |
| xoshiro256, xorshift1024 | 256–1024 | 4–16 | 20 min – 1 h 20 |
| **MT19937 / MT19937-64 / WELL19937** | **19 937** | **300** | **25 h** |
| ChaCha20, AES-CTR-DRBG, RNG matériel | secret non linéaire | **impossible** | — |

Familles F2-linéaires : `mtbreak.c` s'applique tel quel (changer la récurrence).
Familles congruentielles : même compte d'information, réduction de réseau (LLL).

### `keno_break.c` — l'outil déployable

`mtbreak.c` est la démonstration ; `keno_break.c` est l'outil qu'on braque sur une
vraie capture. Il lit un fichier de tirages ordonnés (20 numéros par ligne, dans
l'ordre de sortie) et balaye **3 échantillonneurs × 3 mappings** :

| mapping | bits F2-linéaires extraits | tirages nécessaires |
|---|---|---|
| `mulhi` `(u·k)>>32` | préfixe commun de l'intervalle, ~4,5 bits/sortie | **300** |
| `u % k` | `u mod 2^v2(k)` — 22 bits/tirage (k=64 en donne 6 à lui seul) | **1400** |
| `(u>>16) % k` | mêmes bits, décalés en position 16 | **1400** |

Vérifié de bout en bout sur des captures synthétiques (graine cachée, préchauffage
inconnu de 41 sorties) :

```
$ ./keno_break scanfile ordered_demo.txt
  already-sorted lines: 0/420  (0.0%; a real draw order gives ~0%)
  rank of the first drawn ball inside the sorted set: 24 18 22 24 19 21 29 20 ...
    sampler 0 mapping 0 : rank 19937/19968, 35544 eqs -> replayed 395/395, predicted 25/25
  *** CONSISTENT: sampler 0, mapping 0 — generator recovered ***

$ ./keno_break scanfile sorted_demo.txt
  already-sorted lines: 420/420  (100.0%)
  -> the feed publishes sorted numbers; the order attack cannot run.
```

Le second cas est **l'état actuel de l'archive** : l'outil détecte tout seul que
l'ordre a été perdu et refuse de tourner. C'est le verrou à lever.

Les échantillonneurs et mappings faux ne coûtent rien : le système devient
**incohérent** (35 000 équations pour 19 968 inconnues), l'outil abandonne en 0,2 s
et passe à l'hypothèse suivante.

---

## 6 bis. Attaque par canaux auxiliaires — sur les VRAIS tirages, sans ordre

Le flux publie deux sorties supplémentaires du **même** générateur. Elles suffisent,
sans jamais avoir besoin de l'ordre des boules :

| canal | hypothèse | bits F2-linéaires certains | tirages pour 19 937 bits |
|---|---|---|---|
| `bonus` = **première boule tirée** | Fisher-Yates part du tableau identité, donc `bonus−1` **est** `j₀=(u·80)>>32` | **5,20 / tirage** | 4 239 (14,7 j de flux) |
| `bonus` = `trié[(u·20)>>32]` | tirage supplémentaire parmi les 20 | 3,21 / tirage | 6 180 (21,5 j) |
| `boost` | seuils sur `u/2³²` : 0,512 / 0,75 / 0,90 / 0,95 / 0,975 | 1,15 / tirage | 17 336 (60 j) |

**L'archive en contient 70 560 — soit 11× le nécessaire.** Aucun ordre requis.
`channel_break.c` monte le système et l'élimine sur GF(2).

### Un point subtil : l'alignement n'est pas identifiable

Premier réflexe : balayer les 624 positions possibles du tampon. Le contrôle négatif
l'a réfuté — *tous* les alignements passaient. La raison est structurelle : la
récurrence `x_{n+624} = f(x_n, x_{n+1}, x_{n+397})` est invariante par décalage et
s'inverse vers l'arrière, donc n'importe quel flux MT valide se lit depuis n'importe
quelle phase en prolongeant le tampon en arrière. L'alignement est libre — 624× moins
de travail — et le vrai discriminant est le **modèle** (W et la sémantique du canal).

Contrôles sur une archive synthétique MT19937 (graine et préchauffage cachés) :

| test | équations | rang | contradictions | verdict |
|---|---|---|---|---|
| modèle correct (W=22, bonus=1ʳᵉ boule) | 28 717 | 19 937 | **0** | consistant ✓ |
| **mauvais** W (21) | 19 944 | 19 937 | **4** | rejeté ✓ |
| **mauvaise** sémantique (rang du bonus) | 17 690 | 17 690 | 0 | rang insuffisant |

### Résultat sur l'archive réelle

| mode | W | équations | rang | contradictions | verdict |
|---|---|---|---|---|---|
| bonus = 1ʳᵉ boule | 20 | 19 944 | 19 937 | 4 | **rejeté** |
| bonus = 1ʳᵉ boule | 21 | 19 944 | 19 937 | 4 | **rejeté** |
| bonus = 1ʳᵉ boule | 22 | 19 944 | 19 937 | 5 | **rejeté** |
| bonus = 1ʳᵉ boule | 23 | 19 944 | 19 937 | 5 | **rejeté** |
| bonus = 1ʳᵉ boule | 24 | 19 949 | 19 937 | 3 | **rejeté** |
| bonus = rang trié | 22 | 19 941 | 19 937 | 3 | **rejeté** |
| **boost seul** (24 000 tirages) | 21 | 19 949 | 19 937 | 3 | **rejeté** |
| **boost seul** (24 000 tirages) | 22 | — | 19 937 | ≥3 | **rejeté** |
| bonus = 1ʳᵉ boule via `u % 80` | 20 / 21 / 22 | 19 940–19 944 | 19 936–19 937 | 3–4 | **rejeté** |
| bonus = 1ʳᵉ boule, Floyd (k=61) | 21 / 22 | 19 949 | 19 937 | 4–5 | **rejeté** |

Les variantes `% ` couvrent le style de code `j = i + u %% (80-i)` : 80 = 16·5, donc
`u %% 80` fixe `u mod 16`, soit 4 bits **de poids faible**. Validé sur une archive
synthétique générée avec ce mapping — mode 6 consistant, mode 0 (mulhi) rejeté,
mauvais W rejeté.

Le test `boost seul` est le plus léger en hypothèses : il ne suppose rien sur le
bonus — seulement MT19937, W mots par tirage, et un boost issu de seuils sur `u/2³²`.

Chaque configuration sature le rang à 19 937 — la dimension exacte de MT19937 — puis
se contredit immédiatement. Le générateur de Loto Express **n'est pas MT19937** avec
ces dispositions, et cela est établi **depuis l'archive triée seule**, ce que ni le
balayage 2³² ni aucun test statistique ne pouvait faire.

### `lin_break.c` — les générateurs F2-linéaires de 33 à 1024 bits

Le balayage 2³² couvre tout état ≤ 32 bits ; `channel_break` couvre les 19 937 de
MT19937. `lin_break` ferme l'intervalle : mêmes canaux auxiliaires, mais 64 à 512
inconnues au lieu de 19 968, donc chaque essai prend quelques millisecondes.

Validé d'abord sur une archive synthétique xorshift64 : bon générateur → consistant
(rang 64/64, 0 contradiction) ; mauvaise moitié de sortie, mauvais générateur, mauvais
W → tous rejetés.

Sur l'archive **réelle**, balayage large — 8 générateurs (xorshift64 hi/lo,
xorshift128 de Marsaglia, xorshift96, LFSR de Galois 64/128/256/512) × 7 canaux ×
**W de 1 à 64** = **3 584 essais, 3 424 rejetés, 0 consistant**. Les 160 restants sont
dégénérés (canal boost placé en r=20 avec W ≤ 20 : ce mot n'existe pas, zéro équation ;
le mode 8 couvre ces W correctement).

Balayer W jusqu'à 64 couvre aussi les **flux entrelacés** : si deux serveurs alternent
les tirages, chaque flux ne voit qu'un tirage sur deux — ce qui revient exactement à
doubler W. Et W ∈ {1…4} couvre l'hypothèse où le boost et le bonus proviennent d'une
**instance de générateur distincte** de celle qui tire les numéros (192 essais
supplémentaires, tous rejetés).

### Générateurs congruentiels — `modlcg.py`

Les bits de poids faible d'un LCG modulo 2^k forment eux-mêmes un LCG modulo 2^t,
**quel que soit le multiplicateur**. Donc si l'échantillonneur écrit `j = u %% 80` et
que `u` est constitué des bits faibles de l'état, alors `(bonus−1) mod 16 = u mod 16`
et la suite doit vérifier `x_{d+1} = A·x_d + C (mod 16)` — 256 couples à essayer, sans
jamais deviner le multiplicateur. Étendu aux ordres 1 et 2, modulo 2 à 16, sur six
suites observables (bonus−1, rang du bonus, indice du boost, plus petit et plus grand
numéro, somme du tirage). **La plus longue plage de correspondance est au niveau du
hasard partout** (une famille congruentielle produirait un accord sur l'archive entière).

### LCG 64 bits à sortie de poids fort — attaque par réseau

Une famille classique échappe à tout ce qui précède : le **LCG modulo 2⁶⁴ à sortie de
poids fort** (`out = s >> 32`) avec un état 64 bits arbitraire. Le balayage 2³² couvre
tout LCG modulo 2³² et tout LCG 64 bits atteignable depuis une graine 32 bits ;
l'algèbre F2 ne s'applique pas à une mise à jour congruentielle ; `modlcg` ne voit
qu'une sortie en bits **faibles**. Reste ce cas.

Montage : le canal bonus fixe chaque état à un intervalle de 2⁵⁷·⁷ sur 2⁶⁴ (6,32 bits),
la différence `D_d = s_{d+1} − s_d` élimine l'incrément inconnu puisque
`D_{d+1} = A·D_d`, et en centrant on obtient `e_d = A^d·e_0 + b_d (mod 2⁶⁴)` avec tous
les `|e_d| ≤ 2⁵⁸·⁷` — un *Hidden Number Problem* que LLL résout. Le multiplicateur est
pris dans la liste standard, W est balayé.

**Correction d'une prédiction erronée de ma part.** Mon estimation analytique disait
que ça ne pouvait pas marcher : la marge entre la norme du vecteur cible et
l'heuristique gaussienne plafonne à 2³·⁷ alors que le facteur d'approximation de LLL
vaut ~2^(n/4), soit 2⁵ dès la dimension 21. Le test empirique dit l'inverse — **LLL
récupère l'état** à K = 12, 16, 20 et 24. En pratique LLL fait très largement mieux que
sa borne pire-cas sur ce type de réseau. La leçon vaut d'être notée : la borne
analytique ne remplace pas le contrôle positif.

Contrôles (LCG64 synthétique, multiplicateur et W cachés) :

| K | bon (a, W) | mauvais W | mauvais a | données aléatoires |
|---|---|---|---|---|
| 12 | **récupéré** | faux positif | rejeté | rejeté |
| 16 | **récupéré** | rejeté | rejeté | rejeté |
| 20 | **récupéré** | rejeté | rejeté | rejeté |
| 24 | **récupéré** | rejeté | rejeté | rejeté |

À partir de K = 16 l'attaque discrimine proprement ; K = 12 produit des faux positifs
et n'est pas utilisable. Les résultats sur l'archive réelle sont donc lancés à K = 20.

L'implémentation Python (fractions exactes) sert de référence ; `lcg_lll.c` refait le
même calcul avec la base en `__int128` et le Gram-Schmidt en `long double`, soit
quelques microsecondes par réduction au lieu de plusieurs minutes.

**Résultat sur l'archive réelle** — 12 multiplicateurs standards × W de 1 à 48 ×
5 fenêtres de départ = **2 880 réductions de réseau, 0 correspondance** :

```
  MMIX / PCG   L'Ecuyer a/b/c   ranqd1-64   Lehmer64   drand48
  glibc LCG    MSVC             Numerical Recipes      PCG-XSL-RR   Knuth 64
  -> no fit at any W ; total hits: 0
```

La dernière famille classique est donc exclue elle aussi. Réserve honnête : l'attaque
exige de **deviner le multiplicateur**. Un multiplicateur maison lui échappe — mais
c'est aussi le seul degré de liberté qui reste, et l'ordre de tirage le referme.


---

## 7. Ce qui a été appris sur le jeu

- **Table du multiplicateur boost reconstruite exactement** :
  `×1 : 51,2 % · ×2 : 23,8 % · ×3 : 15,0 % · ×4 : 5,0 % · ×5 : 2,5 % · ×10 : 2,5 %`
  (χ² = 0,55 pour df = 5 — ajustement quasi parfait ; l'hypothèse 500/250/… est
  rejetée à χ² = 61,5). **Multiplicateur moyen = 2,013.**
  Conséquence : si le boost était publié **avant** la clôture des mises,
  ne jouer que les tirages à boost ≥ 4 multiplierait le retour par
  5,75 / 2,013 = **2,86×** — un levier structurel qui ne demande aucune prédiction.
  À vérifier sur le flux live (champ `secondarySelection` d'un tirage `OPEN`).
- Le **bonus** est un tirage uniforme parmi les 20 boules (rang : χ² = 27,5 / df 19),
  indépendant du boost et du tirage suivant. Aucune information d'ordre.
- La cadence est une grille stricte de 300 s ; **24 décrochages** en 70 559 pas,
  toujours par paires compensées exactes (300+δ puis 300−δ, δ ≤ 5 s) : un tirage
  isolé publié en retard, la grille se recale au suivant. Les timestamps sont donc
  mesurés, pas planifiés.
- **Cotes exactes** (`odds.py`, hypergéométrique 20/80) — l'entrée de tout calcul
  d'espérance, sans aucune prédiction :

  | numéros joués | espérance de bons numéros | probabilité de tout toucher | soit 1 sur |
  |---|---|---|---|
  | 5 | 1,25 | 6,449·10⁻⁴ | 1 551 |
  | 6 | 1,50 | 1,290·10⁻⁴ | 7 753 |
  | 7 | 1,75 | 2,440·10⁻⁵ | 40 979 |
  | 8 | 2,00 | 4,346·10⁻⁶ | 230 115 |
  | 9 | 2,25 | 7,243·10⁻⁷ | 1 380 688 |
  | 10 | 2,50 | 1,122·10⁻⁷ | 8 911 711 |

- **Provenance de l'archive.** Deux marqueurs indiquent une capture réelle plutôt
  qu'une fabrication : les 24 décrochages d'horloge en paires exactement compensées
  (un artefact d'ordonnanceur que personne ne fabriquerait), et la table du boost qui
  tombe sur des probabilités *conçues* (512/238/150/50/25/25 pour mille, χ² = 0,55).
  Un archive fabriquée avec une bibliothèque standard aurait par ailleurs été
  identifiée par le balayage de graines ou l'attaque par canaux — elle ne l'a pas été.
- Aucun biais de fréquence sur 70 560 tirages ⇒ ce **n'est pas une machine à boules**
  (un tirage physique montrerait un biais de billes à cette taille d'échantillon).
  C'est un RNG logiciel, correctement implémenté (aucun biais de modulo, aucun
  mélange naïf : les deux laisseraient une signature marginale visible).

---

## 8. Étape suivante — capter l'ordre

`primarySelection` et `drawResult.matrix1.main` sont confirmés triés par le serveur
REST : ils ne contiennent aucun ordre. La source candidate est le flux d'animation
SignalR `SendCurrentState`, champ `meta[lang].balls`, que le frontend anime selon la
position du tableau avant de le trier dans `ReorderScene`.

Protocole corrigé :

1. Lancer `capture_order.py` pendant un tirage actif et conserver le JSON brut.
2. Exiger 20 valeurs uniques non triées et vérifier que leur tri égale le REST du
   même identifiant. Sinon, la piste est réfutée.
3. Collecter 500 tirages pour `mulhi`, ou 1 600–2 000 pour inclure les mappings à
   faible fuite, avec 50 tirages réservés au holdout. L'arrêt nocturne porte 400
   tirages à environ 47 h murales.
4. Balayer les 3 samplers et 3 mappings actuellement implémentés ainsi que le stride
   fixe `W`. Rejet et vrai `javaNextInt` restent à implémenter et ne sont pas couverts.
5. Ne conclure à une récupération que pour un rang 19 937, un replay intégral et un
   holdout exact. Un rang insuffisant est `INCONCLUSIVE`, pas un rejet.

Voir [`REPRISE_ETAT.md`](REPRISE_ETAT.md) pour les commandes et les limites exactes.

---

## 9. Où en est exactement la prédiction

**Réponse directe : aucun des modèles versionnés n'a prédit un numéro au-dessus du
taux de base de 25 % sur le holdout. Cela rejette ces modèles, pas toute méthode
possible ni tout générateur non testé.**

Ce qui est **rejeté dans les configurations explicitement testées** :

- les 250 prédicteurs, analyses de paires/triplets/lags et tests de flux exécutés ;
- les 234 initialisations 32 bits balayées, ainsi que les initialisations MT19937
  et glibc 32 bits avec les 64 décalages essayés ;
- les récurrences F2-linéaires, sémantiques de canal et strides effectivement
  énumérés par `channel_break`/`lin_break` — sans généralisation à toute la famille ;
- les récurrences congruentielles d'ordre 1/2 et modules 2…16 testés ;
- 390 schémas de dérivation par hash de données publiques.

Ce qui **reste ouvert** :

- tout générateur **non-F2-linéaire d'état ≥ 64 bits** dont la sortie n'est pas une
  troncature simple de l'état — PCG (permutation dépendante de l'état), xoshiro\*\*
  (multiplication en sortie), splitmix64 (mélange bijectif) : le canal donne bien
  6,32 bits par tirage, mais pas sous la forme « bits de tête de l'état » dont le
  réseau a besoin. Pour le LCG 2⁶⁴ à troncature simple, l'échec LLL actuel reste
  heuristique tant qu'aucun état/incrément n'est reconstruit puis rejoué (§6 bis) ;
- un LCG 2⁶⁴ à **multiplicateur non standard** : l'attaque par réseau doit le deviner ;
- un boost dérivé autrement que par des seuils sur `u/2³²` — par exemple
  `u % 1000 < 512` — ne livre aucun bit linéaire et échappe à l'attaque par canaux ;
- un échantillonneur à **consommation variable** (rejet avec redraw) : le nombre de
  mots par tirage n'est alors plus constant, et l'attaque par canaux suppose un W fixe.
  L'hypothèse « boost/bonus sur une instance séparée » (W ∈ 1…4) contourne ce cas et a
  été testée ;
- un CSPRNG (ChaCha20, AES-CTR-DRBG) ou un RNG matériel : dans ce cas la partie est
  close mathématiquement, quelle que soit la quantité de données.

**Le verrou est l'ordre des boules, et il est chiffrable :** l'ensemble trié porte
61,617 bits d'entropie, l'ordre complet 122,694 bits. Sous `mulhi`, le solveur
extrait environ 89,66 bits linéaires certains par tirage. Cette information rend la
récupération synthétique praticable, sans garantir qu'une famille non linéaire soit
calculatoirement cassable.

### Ce qu'il faut faire, dans l'ordre

1. **Capter puis valider l'ordre.** `capture_order.py` conserve séparément le flux
   SignalR ; le client REST Swift ne fabrique plus de `drawOrder`. Seul un
   `DrawScene` non trié dont l'ensemble, le boost et le bonus correspondent au REST
   du même ID devient `VERIFIED_ORDER`.
2. **Vérifier la fenêtre de mise.** Le flux expose `wagerEndDate` et `phase` par
   tirage. Si un résultat existe dans l'API avant la clôture des mises, même d'une
   seconde, c'est une faille de pipeline — et elle ne demande aucune cryptanalyse.
   Le client de ce dépôt court déjà après la publication ; il suffit de mesurer l'écart.
3. **Vérifier le boost.** Sa distribution historique est mesurée (§7), mais aucune
   apparition avant clôture n'est établie. Toute observation éventuelle doit être
   horodatée avec une marge supérieure à l'incertitude réseau/horloge.
4. **Si l'ordre est disponible**, lancer `keno_break` avec un holdout intact : cible
   prudente de 400–500 tirages pour MT/`mulhi`, 1 600–2 000 pour les mappings à
   faible fuite. Une prédiction n'est déclarée qu'après rang complet, holdout exact
   et modèle unique. L'option `--state-out` de `keno_break file/scanfile`
   matérialise alors l'état après le dernier tirage consommé ; `keno_break predict`
   produit les tirages suivants sans modifier ce checkpoint.

---

## 9 bis. Erreurs et impasses, consignées

Une note d'audit n'a de valeur que si les échecs y figurent aussi.

- Le χ²/df = 0,68 du rapport précédent était une **erreur de normalisation** (§2).
- Le χ² des paires de gaps (z = +274) venait de **mon propre modèle nul erroné** ;
  quatre contrôles SRS le placent au-dessus de la valeur réelle (§3).
- Le χ² du lag-1 (z = +3,69) ne **se réplique pas** en moitié/moitié (§3).
- Le balayage des 624 alignements de tampon était **inutile** : la récurrence MT
  s'inverse en arrière, tout alignement est consistant (§6 bis). Le contrôle négatif
  l'a révélé avant que le résultat ne soit publié.
- J'ai prédit analytiquement que l'attaque par réseau sur LCG64 **ne pouvait pas
  marcher** (marge 2³·⁷ contre un facteur LLL de 2⁵). Le contrôle positif dit le
  contraire : LLL récupère l'état à K = 12…24. La borne pire-cas ne remplace pas
  l'expérience.
- Les tests statistiques n'ont **aucun pouvoir** contre un PRNG à petit état : un
  xorshift32 cassable en secondes est indiscernable d'un PCG64 (§5). C'est la raison
  pour laquelle tout l'effort a basculé vers l'algèbre.

---

## 10. Reproduire

```bash
cd claude/research
python3 load.py           # charge et vérifie les 70 560 tirages
python3 exp01.py          # bonus, boost, rang GF(2)
python3 exp02.py          # rang colex, LCG, matrice de transition, timestamps
python3 exp03.py          # uniformité corrigée, rapport de variance, ordre, modulaire
python3 exp04.py          # spectral, autocorrélation
python3 exp05.py          # triplets, fuites, créneaux, démarrage à froid
python3 exp06.py          # scan de TOUS les lags, canaux boost et bonus
python3 score_test.py     # 250 prédicteurs, test de score exact
python3 bounds.py         # modèle de Newton + bornes 3σ
python3 bitstream.py      # batterie NIST sur le flux extrait
python3 hashhunt.py       # 390 schémas provably-fair
python3 calib.py          # calibration : faible vs fort vs réel
python3 exp07.py          # histogramme lag-1, overlap triple, gaps, impairs/bas
python3 exp08.py          # réfutation des deux faux positifs par contrôles SRS
python3 exp09.py          # réplication moitié/moitié du lag-1
python3 segments.py       # audit en 14 blocs (effet localisé)
python3 modlcg.py         # récurrences modulaires (familles congruentielles)
python3 lcg_lll.py margins # pourquoi le réseau ne passe pas sur LCG64
gcc -O3 -o pairs pairs.c -lpthread -lm && ./pairs             # 2,49 G de paires
gcc -O3 -o seedhunt seedhunt.c -lpthread && ./seedhunt 0 0 4294967296 4
gcc -O3 -o seedhunt2 seedhunt2.c -lpthread && ./seedhunt2 0 0 100000000
gcc -O3 -o mtbreak mtbreak.c && ./mtbreak 400 0xC0FFEE42 0    # cassage complet
gcc -O3 -o keno_break keno_break.c && ./keno_break scanfile ordered.txt 20 64
python3 capture_order.py capture capture.jsonl --duration 900 --max-draws 1 \
  --expected-draw-id ID_DU_TIRAGE                              # SignalR brut
python3 capture_order.py inspect capture.jsonl
python3 capture_order.py validate capture.jsonl --draw-id ID_DU_TIRAGE
python3 capture_order.py export capture.jsonl ordered.txt \
  --validation capture.jsonl.validation.json
gcc -O3 -o channel_break channel_break.c -lpthread && ./channel_break 0 22 5500 1 0 0 1
gcc -O3 -o lin_break lin_break.c && sh run_lin_wide.sh          # 3584 essais
```

`seedhunt` s'auto-valide : `./seedhunt 0 0 3000000 4 -1 "0,1,0,1234567"`
plante une graine connue et la retrouve.
