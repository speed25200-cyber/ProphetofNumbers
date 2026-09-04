# Loto Express — recherche de faille exploitable

Audit offensif de l'archive complète : 70 560 tirages (ids 1309614–1380173,
2025-09-14 → 2026-08-25, 0 trou). Objectif : prédire tout ou partie des 20 numéros.

Tout le code est dans [`research/`](research/) et rejouable hors ligne.

---

## 1. Résumé

| Ligne d'attaque | Verdict |
|---|---|
| Structure statistique de l'historique publié | **Aucune.** 250 prédicteurs, 2,49 G de paires, 82 160 triplets, 60 000 lags, batterie NIST : rien au-delà du bruit |
| Générateur à état ≤ 32 bits (234 variantes algorithmiques) | **Exclu** par balayage exhaustif 2³² |
| Dérivation par hash de données publiques (« provably fair ») | **Exclu**, 390 schémas testés |
| Reconstruction d'état à partir des tirages **triés** | **Barrière combinatoire** : 20! ≈ 2,4·10¹⁸ ordres par tirage |
| Générateur F2-linéaire (64 → 19 937 bits) via canaux `bonus`/`boost` | **Exclu** — 3 900+ configurations testées sur les vrais tirages, 0 consistante |
| Sortie additive (xorshift128+ de V8, xoshiro256+) | **Exclu** — bit 0 exactement linéaire, 128 essais, 0 consistant |
| Générateur congruentiel à sortie en bits faibles | **Exclu** — récurrences modulaires d'ordre 1 et 2 mod 2…16 |
| LCG 2⁶⁴ à sortie de poids fort | **Exclu** — 2 880 réductions de réseau (12 multiplicateurs standards × 48 W × 5 fenêtres), 0 correspondance |
| `java.util.Random`, état 48 bits quelconque | **Exclu** — même réseau, module paramétré, 0 correspondance |
| Congruentiel `u = s >> shift` puis `j = u % 80` | **Exclu** — effondrement en bits faibles, 2⁶⁴ ramené à 2²⁰–2³⁶, **0 survivant** |
| Idem avec l'**incrément également inconnu** | **Exclu** — réserve levée, contrôle corrigé et validé, 0 survivant (§7 ter) |
| Hachage à **rondes réduites** (la fonction de delta-chain) | **Exclu**, 1 920 schémas |
| Mode compteur à clé par défaut (AES-CTR, ChaCha20) | **Exclu**, 360 combinaisons |
| splitmix64 / PCG / xoshiro\*\* par SAT, canal 4 bits | **Hors d'atteinte, mesuré** — la barrière des retenues tient |
| **Le tirage trié vu comme un rang combinatoire** (61,6 bits/tirage au lieu de 4) | **Piste neuve — le tri ne perd rien si le tirage n'a jamais eu d'ordre.** Voir §6 quater |
| LCG **quelconque** (multiplicateur, incrément et W tous inconnus) sur le rang | **Exclu** — forme close sur 3 rangs, 3 conventions × 5 mappages × 70 557 départs, 0 |
| splitmix64 et 5 autres finaliseurs bijectifs sur le rang | **Exclu** — la sortie complète rend l'état par inversion ; chaque ligne exactement sur son nul |
| **Toute** la classe F2-linéaire d'état < 35 280 bits, sans énumérer | **Exclu** — complexité linéaire mesurée à 35 278–35 282 pour n/2 = 35 280 |
| `xoshiro256**`, `xoroshiro128**` (brouilleur non linéaire) sur le rang | **Exclu** — le brouilleur se décolle par inversion, 0 fenêtre sur 1 536, tous les W |
| Fibonacci retardé (le `random()` de la glibc, Boost, add-with-carry) | **Exclu** — 2 016 couples de lags × 3 opérations, meilleur 0/3 000 |
| Rang concaténé à partir de **deux mots** 32 ou 31 bits | **Exclu** — a et c en forme close, 0/20 000 positions, 4 dispositions |
| Réensemencement sur l'horloge aux 24 décrochages | **Exclu** — 2,46·10¹⁰ graines, maximum 13/20 exactement à l'espérance du hasard |
| Reconstruction d'état à partir des tirages **ordonnés** | **CASSAGE COMPLET démontré** — voir §6 |

**Conclusion opérationnelle :** l'historique publié ne contient aucune information
exploitable, et ce n'est pas une limite de méthode — c'est mesuré et borné (§4).
La seule voie ouverte est l'**ordre de sortie des boules**, que le client jetait
(`Array(Set(out)).sorted()`). Le patch de ce dépôt le conserve désormais.

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
| **seed** | Balayage 2³² **complet et terminé**, 224 combinaisons × 4,29·10⁹ graines = **9,62·10¹¹ essais**, plus 10 générateurs de plateforme, plus MT/glibc avec 64 décalages sur la plage des timestamps unix, plus les graines en **millisecondes** et en **nanosecondes** (fenêtre de ±0,5 s autour de la seconde du tirage, 10⁹ candidates × 224 combos = 2,24·10¹¹ essais supplémentaires) (16 familles PRNG × 4 mappings × 4 échantillonneurs, + .NET, V8, Python `random.sample`, PHP `mt_rand`) | meilleur **15/20**, exactement le modèle nul | voir ci-dessous |

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

Le balayage **nanoseconde** — ce qu'aurait réellement un système qui s'ensemence sur
une horloge à la nanoseconde, hors de portée de 2³² — donne la même chose : 224 combos
× 10⁹ graines, meilleur **15/20**, 2 combos l'atteignant.

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

Minimum mesuré : **300 tirages ordonnés = 25 h d'observation**, résolution en 2,4 s.

| tirages | rang | tirages observés rejoués | tirages futurs prédits |
|---|---|---|---|
| 230 | 19 633 | 2/230 | 0/50 |
| 250 | 19 894 | 55/250 | 0/50 |
| 270 | 19 928 | 183/270 | 26/50 |
| **300** | **19 937** | **300/300** | **50/50** |

L'alignement du tampon (624 possibilités) et le nombre de mots consommés par
tirage n'ont pas besoin d'être connus : une hypothèse fausse rend le système
**incohérent** (35 842 équations pour 19 968 inconnues ⇒ détection certaine),
ce que l'outil exploite pour balayer les hypothèses automatiquement (`SCAN=1`).

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
| bonus = 1ʳᵉ boule, **`nextDouble()`** (2 mots/indice) | 40 / 41 / 42 / 44 | 19 944–19 949 | 19 937 | 4–6 | **rejeté** |

La variante W ≈ 40 couvre l'échantillonneur qui tire un flottant :
`j = (int)(nextDouble() * k)` consomme **deux** mots 32 bits par indice, donc une
quarantaine par tirage. Les bits de tête du premier mot restent épinglés, l'attaque
s'applique telle quelle.

Les variantes `%` couvrent le style de code `j = i + u % (80-i)` : 80 = 16·5, donc
`u % 80` fixe `u mod 16`, soit 4 bits **de poids faible**. Validé sur une archive
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

### Sortie additive — xorshift128+ (V8) et xoshiro256+

Ces deux-là ont une mise à jour d'état **F2-linéaire** mais une sortie **additive**
(`s0 + s1`, `s0 + s3` modulo 2⁶⁴), ce qui casse la linéarité… sauf en **bit 0** : une
addition n'a pas de retenue entrante, donc `(a+b)₀ = a₀ ⊕ b₀` **exactement**.

Avec le mapping `u % 80`, `(bonus−1) mod 2` livre donc **une équation linéaire exacte
par tirage**. Il faut 128 tirages pour xorshift128+ et 256 pour xoshiro256+ — l'archive
en a 70 560. C'est la famille des générateurs modernes rapides, dont `Math.random` de
V8 : elle méritait d'être fermée.

Validation, et une erreur trouvée au passage : mon premier pas symbolique de xoshiro256+
était faux (`t = s1 << 17` doit capturer `s1` **avant** la chaîne de XOR). Le contrôle
positif l'a signalé — il rejetait ses propres données. Après correction :

| test | résultat |
|---|---|
| xorshift128+ sur ses propres données | rang 128/128, 0 contradiction → **consistant** |
| xoshiro256+ sur ses propres données | rang 256/256, 0 contradiction → **consistant** |
| xoshiro256+ sur les données de xorshift128+ | rejeté |
| xorshift128+ sur les données de xoshiro256+ | rejeté |
| xorshift128+ avec un mauvais W | rejeté |

Sur l'archive **réelle** : 2 générateurs × W de 1 à 64 = **128 essais, 128 rejetés,
0 consistant**.

### Ce que delta-chain apporte réellement, et où il s'arrête

Le dépôt `delta-chain-sha256` casse SHA-256 à rondes réduites en exploitant la
structure de la fonction de tour, et il documente une **transition de phase de
résolution des retenues** : en dessous d'un certain nombre de rondes le système est
SAT-résoluble, au-dessus il ne l'est plus. Deux choses en découlent ici.

**1. Hachages à rondes réduites** (`redhash.py`). `hashhunt` n'avait testé que des
hachages complets. La fonction de compression réduite est reprise **verbatim** de
`delta-chain-sha256/src/sha256_attack_toolkit.py`, et vérifiée : à R = 64 elle
reproduit `hashlib` bit à bit. Rondes 1 à 64 × 6 entrées publiques × 5 dérivations =
**1 920 schémas**, meilleur recouvrement **11/20** — le hasard. Rien.

**2. Inversion par SAT** (`satmix.py`). L'élimination sur GF(2) atteint les générateurs
F2-linéaires, le réseau atteint un LCG à sortie tronquée. Ni l'un ni l'autre n'atteint
un générateur dont la sortie est un **mélange bijectif** — splitmix64 avance son état
d'une constante puis le pousse à travers deux multiplications 64 bits, ce qui *est* la
barrière des retenues de delta-chain. L'outil approprié est donc SAT, et c'est ce que
fait `satmix.py` : une seule inconnue (les 64 bits de s₀, l'état étant un compteur),
les intervalles du canal bonus comme contraintes, aucun tableau Fisher-Yates à encoder.

Premier encodage — 31 additions à propagation de retenue en chaîne par multiplication —
**budget épuisé sans verdict** en 153 s sur une instance pourtant *sous*-déterminée
(31 bits connus pour 64 inconnues, 74 050 variables, 343 285 clauses). Second encodage
avec l'**arbre de compression 3:2** (`wcsa`, exactement la primitive du toolkit
delta-chain) : une seule chaîne de retenue au lieu de trente. **Toujours aucun verdict**
à 600 s.

C'est un résultat, pas un échec : **la barrière des retenues tient**, exactement comme
la transition de phase que documente delta-chain. Deux multiplications 64 bits placent
splitmix64 hors de portée de CaDiCaL à cette taille — et donc, par le même argument,
PCG (rotation dépendante de l'état) et xoshiro\*\* (multiplication en sortie).

**3. Effondrement en bits faibles** (`lowlcg.c`) — et là, l'algèbre gagne. Pour un LCG
modulo 2^M, les **L bits de poids faible de l'état forment eux-mêmes un LCG modulo 2^L**,
quoi que fassent les bits hauts. Or 80 = 16·5, donc `u % 80` fixe `u mod 16`, c'est-à-dire
les bits `shift..shift+3` de l'état — qui vivent dans `s mod 2^(shift+4)`. L'inconnue
s'effondre de M bits à shift+4 :

| famille | modulo | décalage | candidats | coût |
|---|---|---|---|---|
| `java.util.Random` | 2⁴⁸ | 16 | **2²⁰** | instantané |
| MSVC | 2³² | 16 | 2²⁰ | instantané |
| PCG (cœur LCG) | 2⁶⁴ | 27 | 2³¹ | secondes |
| MMIX, L'Ecuyer, Lehmer | 2⁶⁴ | 32 | **2³⁶** | ~une minute |

Une recherche 2⁶⁴ ramenée à 2²⁰–2³⁶ par pure algèbre modulaire. Chaque tirage vérifie
4 bits, donc un mauvais candidat survit avec probabilité 1/16 et seize tirages ne
laissent rien. Contrôle positif : **9 familles sur 9, exactement 1 survivant chacune**.

Cela comble le trou entre `modlcg` (sortie en bits faibles) et `lcg_lll` (sortie
tronquée de poids fort + mapping `mulhi`) : le cas intermédiaire, `u = s >> shift`
puis `j = u % 80`, où le bonus épingle des bits faibles de `u` — ni un intervalle
(pas de réseau), ni linéaire sur F2 (pas d'élimination).

**Résultat sur l'archive réelle** — 9 familles × W jusqu'à 32 × jusqu'à 4 fenêtres,
16 quartets vérifiés par candidat (un mauvais candidat survit avec probabilité 2⁻⁶⁴) :

```
  java.util.Random    java (nextInt bits)   MMIX 64    L'Ecuyer 64   Lehmer64
  PCG (cœur LCG)      glibc TYPE_0          MSVC       Numerical Recipes
  -> best survivors 0 partout ; total : 0
```

**Zéro survivant.** Aucun générateur congruentiel de cette forme ne reproduit l'archive.

`lowlcg2` élargit la même attaque sur deux axes. La **position du quartet** devient un
paramètre : `j = (u >> 16) % 80` — le style `shr16mod` que le balayage de graines teste
déjà — décale les bits observés de 16, soit les bits 32…35 pour java (L = 36, toujours
dans le budget). Et le **canal** aussi : si le bonus n'est pas la première boule mais
`trié[u % 20]`, alors 20 = 4·5 ne fixe que `u mod 4`, deux bits par tirage contre
quatre, mais face à une inconnue d'autant plus étroite. Contrôles : **11 familles sur
11 récupérées**, un survivant chacune. Sur l'archive réelle, canal « première boule » :
**11 familles, 0 survivant, total 0**.

### Une réserve levée : l'incrément inconnu

`lowlcg` fixe l'incrément au constant standard de chaque famille. Un opérateur qui
garderait un multiplicateur connu mais choisirait son propre incrément y échappe.
`lowlcg3` lève ça : les deux premiers tirages épinglent déjà quatre bits de `x₀` et
quatre de `x₁`, donc l'espace des paires tombe de 2²ᴸ à 2^(2L−8) = 2³², et chaque paire
**détermine** l'incrément `C = x₁ − A·x₀`.

Le contrôle positif a d'abord semblé échouer : 11 477 survivants (java) au lieu d'un.
J'ai poursuivi l'hypothèse « il manque des tirages » — elle est fausse, et c'est le
critère d'acceptation qui l'était. Avec `u = A − 1` et

```
x_k = A^k x₀ + C (A^k − 1) / u
```

substituer `x₀ → x₀ + d` et `C → C − u·d` donne

```
A^k (x₀+d) + (C − u d)(A^k − 1)/u = x_k + A^k d − d(A^k − 1) = x_k + d
```

exactement, à chaque pas et pour toujours. **La paire (état, incrément) n'est pas
identifiable** : toute translation de l'orbite entière est réalisable par un changement
d'incrément, et l'observable ne voit qu'un quartet de chaque `x_k`, donc tout `d` qui ne
pousse aucun `x_k` par-dessus une frontière de quartet est indiscernable de `d = 0`.
Vérifié numériquement : pour java à L = 20 la famille de translation compte 9 515
membres — et le total des survivants vaut 9 515 lui aussi. La recherche trouve la
famille, et **rien d'autre**.

Ce n'est pas un défaut, c'est ce que porte l'observable. Une orbite translatée émet les
mêmes quartets dans le futur aussi, ce qui est exactement ce qu'une prédiction demande.
Le contrôle a donc été réécrit pour demander ce qui compte : (1) la paire plantée doit
figurer parmi les survivants, (2) tout survivant doit appartenir à la famille de
translation, (3) les survivants doivent **prédire** des quartets futurs jamais montrés à
la recherche. Et j'ai relevé l'exigence de preuve plutôt que d'abaisser la barre : la
famille rétrécit à mesure que les quartets s'accumulent — 11 477 à 20 tirages, 9 515 à
30, 1 026 à 40 — et à 48 le vote majoritaire est exact. Les quartets supplémentaires sont
quasi gratuits : une mauvaise paire meurt au troisième.

Contrôles à 48 quartets observés, 20 tenus en réserve (`./lowlcg3 selftest`) :

| famille | survivants | plantée gardée | intrus | futur prédit | W faux | quartets aléatoires |
|---|---|---|---|---|---|---|
| java | 1 026 | oui | 0 | 20/20 | 0 | 0 |
| MSVC | 2 804 | oui | 0 | 20/20 | 0 | 0 |
| glibc | 240 | oui | 0 | 20/20 | 0 | 0 |
| Borland | 1 103 | oui | 0 | 20/20 | 0 | 0 |

Le hasard donnerait 1,25 quartet correct sur 20. « Intrus » compte les survivants
extérieurs à la famille de translation : zéro partout, sur des millions de paires
visitées. L'outil est donc probant dans les deux sens, et son résultat sur l'archive
compte :

```
$ ./lowlcg3 real 24
  java multiplier      L=20  best survivors 0   (no state/increment pair fits at any W)
  MSVC multiplier      L=20  best survivors 0
  glibc LCG multiplier L=16  best survivors 0
  Borland multiplier   L=20  best survivors 0
  total survivors: 0  ->  no custom-increment LCG of this shape fits the archive
```

**La réserve est levée** : un opérateur qui garderait un multiplicateur connu en
choisissant son propre incrément n'échappe plus à l'exclusion.

### Clés par défaut en mode compteur — `defaultkey.py`

Un déploiement certifié utilise AES-CTR-DRBG ou ChaCha20 avec une vraie clé, et aucune
quantité de sortie ne la révèle. Un déploiement **mal configuré**, si. C'est la panne
classique des identifiants par défaut, et elle ne coûte rien à écarter : 2 chiffrements
× 9 clés (tout à zéro, tout à 0xFF, 0…31, le nom du produit, le nom de l'opérateur, le
SHA-256 de chacun, le SHA-256 du vide) × 5 compteurs publics × 4 dérivations =
**360 combinaisons**, meilleur recouvrement **11/20** — le hasard.

### Générateurs congruentiels — `modlcg.py`

Les bits de poids faible d'un LCG modulo 2^k forment eux-mêmes un LCG modulo 2^t,
**quel que soit le multiplicateur**. Donc si l'échantillonneur écrit `j = u % 80` et
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

**Et `java.util.Random` avec un état 48 bits arbitraire.** Le balayage de graines ne
couvrait java que pour `new Random(int)`, soit 2³² graines — pas un état quelconque.
Or java est un LCG modulo 2⁴⁸ à sortie tronquée de poids fort : exactement le cadre du
réseau, à condition de paramétrer le module. Contrôles sur données synthétiques :
**récupéré à K = 12, 16, 20 et 24**, les trois contrôles négatifs rejetant à chaque
fois — plus net encore que le cas 64 bits, où K = 12 produit un faux positif. Sur
l'archive réelle : **0 correspondance**, 12 multiplicateurs × 48 W × 5 fenêtres.

Les dernières familles classiques sont donc exclues elles aussi. Réserve honnête :
l'attaque exige de **deviner le multiplicateur**. Un multiplicateur maison lui échappe
— mais c'est aussi le seul degré de liberté qui reste, et l'ordre de tirage le referme.


---

## 6 quater. Le tri ne détruit rien — si le tirage n'a jamais eu d'ordre

Toutes les attaques ci-dessus butent sur le même fait : l'archive publie 20 numéros
**triés**, donc les 89,6 bits d'ordre sont perdus et il ne reste que 4 à 6 bits de canal
auxiliaire par tirage. C'est la « barrière combinatoire » du tableau de synthèse.

Mais cette barrière suppose que le générateur ait **produit** un ordre. Une classe
entière d'implémentations réelles ne mélange rien : elle tire **un** entier dans
`[0, C(80,20))` et le **dérange** (unranking) en combinaison. C'est la façon canonique
d'obtenir un sous-ensemble uniforme sans mélange, et c'est ce qu'on écrit quand on veut
qu'un tirage soit auditable à partir d'un seul nombre publié.

Sous cette architecture, le tirage trié **est** la sortie du générateur, en entier :

```
C(80,20) = 3 535 316 142 212 174 320 = 2^61,617 bits par tirage
```

Pas 4 bits. **61,6 bits**, et le tri n'en perd aucun, puisqu'il n'y avait pas d'ordre à
perdre. C'est un facteur 15 sur le débit d'information, et il change la nature des
attaques possibles.

`rank.py` calcule ce rang sous trois conventions (colex/lex, numéros 0- ou 1-basés). Les
deux formules sont vérifiées par **énumération exhaustive** à (n,k) = (5,2), (7,3), (9,4),
(12,5), puis recalculées en grands entiers exacts sur six vrais tirages. Le flux de rangs
est uniforme sur `[0, C)` comme le veut le modèle nul : moyenne/C = 0,5011, écart-type/C
= 0,28897 contre 1/√12 = 0,28868, χ² = 45,9 sur 64 cases (df 63, z = −1,52).

### `lcgrank.c` — un LCG quelconque, sans deviner le multiplicateur

Avec 61,6 bits par tirage l'attaque n'a plus rien à deviner. En écrivant
`u_{d+1} = A·u_d + B (mod 2^64)`, trois sorties consécutives donnent

```
A = (u₂ − u₁) / (u₁ − u₀)        B = u₁ − A·u₀
```

en forme close. Et comme `A = a^W` et `B = c(a^{W−1}+…+1)` pour un générateur avancé de
W pas par tirage, résoudre pour `(A,B)` **quelconque** couvre d'un seul coup *tous* les
multiplicateurs, *tous* les incréments et *tous* les W — sans balayage. C'est
strictement plus fort que les 2 880 réductions de réseau du §6 ter, qui devaient, elles,
énumérer 12 multiplicateurs standards.

Le rang ne donne `u` que modulo C, mais `2^64/C = 5,22`, donc `u = r + kC` avec k ∈ 0..5 :
216 combinaisons par triplet. Chaque candidat est ensuite vérifié sur 6 tirages de plus,
où un faux survit avec probabilité 2⁻³⁶⁹.

Contrôles : les 5 mappages plantés sont récupérés, et **deux flux mélangés
non-affines** sont rejetés. Le contrôle négatif évident — « des rangs aléatoires » — a
d'abord été écrit comme un LCG réduit mod C : c'est-à-dire *exactement* le mode 0, donc
un second positif déguisé en contrôle. Corrigé.

Sur l'archive, **3 conventions de rang × 5 mappages × 70 557 positions de départ : 0**.

### `rankmix.c` — splitmix64, que le §6 bis classait « hors d'atteinte »

Le tableau de synthèse porte `splitmix64 / PCG / xoshiro**` en **hors d'atteinte,
mesuré** : à 4 bits par tirage il faut un solveur SAT qui traverse la chaîne de retenues,
et la barrière tient. Cette barrière existait parce que l'observable faisait 4 bits.

À 61,6 bits elle s'évapore — non pas parce que le solveur s'améliore, mais parce que le
problème **cesse d'être une recherche**. splitmix64 est `state += γ`, `sortie = fmix(state)`,
et `fmix` est une **bijection**. Une sortie complète rend donc l'état par simple inversion :

```
s_d = fmix⁻¹(u_d)        s_{d+1} − s_d = W·γ = la même constante, pour toujours
```

Ni γ ni W n'ont besoin d'être connus : W ne fait que multiplier la constante. Le test est
donc « une différence se répète-t-elle ? ». Sur 70 559 paires × 36 candidats, soit 2,5 M
de valeurs dans un espace de 2⁶⁴, même trois collisions seraient hors du hasard.

Six finaliseurs testés (splitmix64, murmur3 fmix64, moremur, rrmxmx, identité,
xor-shift seul). Contrôles : bijectivité vérifiée sur 40 000 valeurs, γ planté retrouvé
avec une récurrence de 399/399, flux témoin à 1. Le seuil n'est pas supposé mais
**calibré** pour chaque finaliseur sur un flux non-additif de la **même longueur** —
nécessaire, car l'identité (l'additionneur pur) est dégénérée et a un niveau de hasard
plus élevé.

| finaliseur | archive | hasard, même longueur |
|---|---|---|
| splitmix64 fmix | 1 | 1 |
| murmur3 fmix64 | 1 | 1 |
| moremur | 1 | 1 |
| rrmxmx | 1 | 1 |
| identité (additionneur pur) | 6 | 6 |
| xor-shift seul | 1 | 1 |

Chaque ligne est **exactement** sur son niveau de hasard, pour les trois conventions de
rang. splitmix64 passe de « hors d'atteinte » à **écarté**.

### `bm.c` — Berlekamp-Massey : la classe F2-linéaire entière, sans énumérer

Tout ce qui précède teste des générateurs **nommés**, un par un : choisir MT19937, un
canal, un W, monter le système GF(2), résoudre. Des milliers de configurations, chacune
une hypothèse séparée. Une telle démarche ne peut écarter que ce qu'on a pensé à
énumérer.

Berlekamp-Massey n'énumère rien. Si le bit observé est **une** fonctionnelle F2-linéaire
de l'état de **n'importe quel** générateur F2-linéaire — MT19937, MT19937-64, WELL,
xorshift, le cœur linéaire de xoshiro, un LFSR de taps quelconques, quelque chose que
personne n'a publié — alors la suite observée est linéaire récurrente et sa **complexité
linéaire** vaut au plus la taille de l'état. Et cela reste vrai quand le générateur est
avancé de W pas par tirage : échantillonner une application linéaire tous les W pas
redonne une application linéaire, donc **W ne peut rien changer**. Un seul nombre tranche
pour toute la classe.

Contrôles : xorshift64 → 64, LFSR de 521 bits → 521, xorshift128+ échantillonné tous les
7 pas → 128 (W est bien sans effet), splitmix64 (non linéaire) → n/2.

Sur l'archive, 30 flux de bits observables (les 4 plans de bits k-libres du rang pour
chaque convention, les 7 de `bonus`, les 5 du rang du bonus dans le tirage, les 3 de
`boost`, et le bit de poids faible de trois positions triées), n = 70 560 :

```
complexité linéaire mesurée : 35 278 à 35 282     (n/2 = 35 280)
six flux aléatoires, même longueur : 35 280 à 35 282
```

Les deux distributions sont indiscernables. Donc, en une phrase :

> **Aucun générateur F2-linéaire d'état inférieur à 35 280 bits, quels que soient ses
> taps et quel que soit W, ne produit un seul de ces flux.**

MT19937 (19 937 bits), MT19937-64, WELL19937, xorshift1024\*, et toute la famille
xoshiro/xoroshiro en font partie — y compris les variantes à sortie additive, dont le
bit 0 est exactement linéaire. Cette seule mesure subsume les 3 900 configurations du
§6 bis, et va bien au-delà : elle couvre les générateurs qu'on n'a pas nommés.

Les 4 plans de bits du rang sont les plus rigoureux du lot : `v₂(C(80,20)) = 4`, donc
`u mod C` conserve **exactement** les 4 bits de poids faible de `u`, quel que soit le k
inconnu. Les plans de `bonus` et `boost` sont plus faibles — si `bonus−1 = u % 80`, ses
bits bas ne sont pas des fonctionnelles linéaires de u — et sont rapportés comme tels.

### `rankxo.c` — les brouilleurs `**`, que ni l'un ni l'autre n'atteint

Restent les générateurs « brouillés » modernes : `xoshiro256**` et `xoroshiro128**`
posent une application **non linéaire** sur un cœur linéaire,

```
sortie = rotl(s1 × 5, 7) × 9
```

de sorte qu'aucun bit de sortie n'est une fonctionnelle linéaire : Berlekamp-Massey ne
dit rien à leur sujet, et rankmix non plus (l'état n'est pas additif).

Mais ce brouilleur est une **bijection** — ×5, rotation, ×9, tout est inversible mod
2⁶⁴. Avec une sortie complète, la non-linéarité se **décolle** :

```
s1 = rotr(sortie × 9⁻¹, 7) × 5⁻¹
```

et ce qui reste dessous est linéaire. L'état tombe alors en **une** résolution linéaire :
plus de recherche dans la chaîne de retenues, plus de SAT.

L'application linéaire est construite en **faisant tourner** le générateur sur des états
de base plutôt que par algèbre symbolique : la colonne i de la matrice est ce que fait
l'observable quand l'état vaut le vecteur unité e_i. Ce n'est licite que si la mise à
jour est purement F2-linéaire, ce que le contrôle vérifie directement
(`step(a⊕b) = step(a)⊕step(b)` sur 500 paires).

Une mesure a corrigé une supposition : les D mots échantillonnés **n'engendrent pas**
l'état — rang 253/256 et 125/128, il manque exactement 3 bits. Un tirage de plus, et une
base indépendante choisie parmi les lignes, réparent cela.

Contrôles : linéarité vérifiée, bijectivité vérifiée sur 200 000 valeurs, générateur
planté récupéré, flux mélangé rejeté.

Un premier passage laissait 3 valeurs de W (et 5 pour xoroshiro128\*\*) **non testées**
faute de matrice inversible. Plutôt que de les déclarer, l'outil prend des tirages
supplémentaires jusqu'à ce que la base se ferme — au prix d'un facteur 6 en affectations
de k par tirage ajouté. Résultat : **0 W encore singulier**, jusqu'à 6 tirages utilisés.

```
xoshiro256**     0 fenêtres résolues sur 1536   (0 W encore singulier, jusqu'à 6 tirages)
xoroshiro128**   0 fenêtres résolues sur 1536   (0 W encore singulier, jusqu'à 4 tirages)
```

`xoshiro512**` demande 6⁹ affectations de k par fenêtre et **reste hors budget** —
c'est une lacune, elle est déclarée comme telle.

### `ranklfg.c` — Fibonacci retardé, la famille que personne n'avait testée

Tout ce qui précède est soit congruentiel (une valeur précédente), soit F2-linéaire (une
matrice sur un état de bits). Une troisième famille manquait, et elle n'a rien d'exotique :
le `random()` de la glibc **est** un Fibonacci additif retardé, `r[i] = r[i-3] + r[i-31]`.
Boost, le `ran_array` de Knuth, l'add-with-carry et le subtract-with-borrow de Marsaglia
ont tous cette forme. Un balayage congruentiel ne peut pas les voir : ils n'ont pas de
multiplicateur. Berlekamp-Massey ne voit que les variantes XOR, puisque l'addition
retient.

À 61,6 bits par tirage ils sont triviaux à tester, la relation de définition étant une
seule équation entre trois sorties :

```
u_d = u_{d−l}  OP  u_{d−s}   (mod 2⁶⁴),   OP ∈ { +, −, ^ },  retenue tolérée
```

Contrôles : quatre générateurs plantés (lags 3/31 de la glibc, 5/17 de Boost, 10/24
subtract-with-borrow, 7/33 XOR). Chacun tient à **toutes** les positions, aucun autre
couple de lags ne tient **une seule fois**, et un flux non-LFG non plus. La séparation
est totale.

Sur l'archive : 2 016 couples de lags × 3 opérations × 3 conventions × 3 000 positions,
**meilleur couple : 0/3 000**. Aucune relation de Fibonacci retardé.

### `rankw32.c` — le rang assemblé à partir de DEUX mots

`lcgrank` résout `u_{d+1} = A·u_d + B` sur le rang lui-même. C'est exact si l'opérateur
tire une valeur de 64 bits. Mais un générateur 32 bits **ne peut pas** produire 61,6 bits
en un appel : il doit concaténer deux sorties. Et alors le rang n'est plus une fonction
affine d'un état unique — `(w_{2d}, w_{2d+1})` sont deux points différents de l'orbite —
donc la forme close de `lcgrank` ne s'applique pas et la famille lui échappe.

Elle n'échappe pas longtemps. Rendre à `u` ses deux mots redonne deux sorties
consécutives, et un seul tirage donne déjà `w₁ = a·w₀ + c`. Un second tirage donne une
deuxième instance, et le couple se résout en forme close : `a = (w₃−w₁)/(w₂−w₀)`,
`c = w₁ − a·w₀`, toujours **sans supposer le multiplicateur**. Le nombre de pas W entre
tirages se lit ensuite en cherchant quelle puissance de a mène `w₀` à `w₂`.

Contrôles : quatre dispositions (2×32 et 2×31 bits, mot fort ou mot faible en tête),
générateur planté récupéré avec `(a,c)` **exacts** dans les quatre, flux mélangé rejeté.

Sur l'archive : **0 / 20 000 positions** pour chaque disposition et chaque convention.

### `rankseed.c` — le balayage 2³² refait pour cette architecture

`seedhunt` balaie toutes les graines 32 bits et mesure la longueur du préfixe
Fisher-Yates qui coïncide. C'est le bon test pour un générateur qui **produit un ordre**.
Il ne dit rien de l'architecture par dérangement : il n'y a pas de mélange à mesurer.

Le balayage n'avait donc jamais été fait pour ce modèle. Il l'est ici : pour chaque
graine et chaque générateur, prendre la ou les premières sorties, les envoyer dans
`[0, C(80,20))`, et comparer au rang publié. Une coïncidence vaut 61,6 bits d'un coup —
sur 2³² graines une fausse arrive avec probabilité 2⁻²⁹·⁶, donc un seul succès trancherait.

Contrôles : les 16 générateurs plantés sont tous retrouvés ; 3·10⁶ graines × 16
générateurs × 3 décalages contre un rang n'appartenant à aucun générateur donnent **0**.

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

- **Les 24 décrochages d'horloge ne cachent aucun réensemencement.** Si un service
  redémarre, la graine plausible est l'horloge murale à cet instant précis.
  `jitter_seeds.py` vise donc chaque tirage suivant un décrochage — 24 cibles — sur
  trois fenêtres (secondes ±30, millisecondes ±2 s, nanosecondes ±2 ms), soit
  **2,46·10¹⁰ essais de graine**. Meilleur préfixe obtenu : **13/20**. Or à ce nombre
  d'essais le hasard seul en attend 6,05 à 13 et 0,63 à 14 : le maximum observé tombe
  **exactement** sur l'espérance, comme le passage de calibration à 1,02·10⁹ essais
  (maximum attendu 12,0 — observé 12). Le seuil d'alarme de l'outil, fixé à 14, est
  donc bien placé, et le verdict est net : **aucun réensemencement sur l'horloge**,
  à aucune granularité.
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

Le flux LoRo renvoie `primarySelection`; le client faisait
`Array(Set(out)).sorted()` (`LoroClient.swift:355`) et détruisait l'ordre.

Ce dépôt ajoute `Draw.drawOrder` et `parseOrderedNumbers`, qui conserve la séquence
du flux et reconstruit l'ordre à partir d'un champ de position s'il existe
(`position`, `order`, `drawOrder`, `index`, `rank`, `sequence`).

Protocole, dans l'ordre :

1. Collecter 400 tirages consécutifs avec `drawOrder` (~33 h).
2. Vérifier que l'ordre est réel et non un tri : la distribution du rang du premier
   élément dans l'ensemble trié doit être **uniforme sur 1…20**. Si elle est
   dégénérée (toujours le plus petit), le flux publie déjà trié et cette voie est morte.
3. Lancer `mtbreak` sur les indices Fisher-Yates reconstruits, en balayant
   l'échantillonneur (Fisher-Yates avant/arrière, rejet, Floyd) et le mapping
   (`mod`, `mulhi`, `shr16`, java) — 16 combinaisons, quelques minutes chacune.
4. Système cohérent ⇒ tous les tirages suivants sont prédits exactement.
   Système incohérent sur les 16 combinaisons × 625 alignements ⇒ le générateur
   n'est pas de classe F2-linéaire : c'est un CSPRNG ou du matériel, et la partie
   est mathématiquement close.

---

## 9. Où en est exactement la prédiction

**Réponse directe : depuis l'archive publiée, prédire ne serait-ce qu'un numéro
au-dessus de 25 % n'est pas atteignable — et c'est mesuré, pas supposé.**

Ce qui est **exclu** :

- toute structure statistique exploitable (250 prédicteurs, 2,49 G de paires,
  82 160 triplets, 60 000 lags, batterie NIST, 14 blocs séparés) ;
- tout générateur d'état ≤ 32 bits, 234 variantes algorithmiques, balayage 2³²
  complet — plus MT19937 et glibc initialisés par une graine 32 bits avec 64
  décalages de consommation ;
- tout générateur **F2-linéaire** de 64 à 19 937 bits (MT19937, xorshift64/96/128,
  LFSR 64/128/256/512), sous 7 sémantiques de canal × W de 1 à 64, soit plus de
  3 900 configurations — **sans jamais utiliser l'ordre de tirage** ;
- tout générateur congruentiel à sortie en bits faibles ;
- 390 schémas de dérivation par hash de données publiques.

Ce qui **reste ouvert** :

- les générateurs dont la sortie n'est ni une troncature de l'état, ni une somme :
  **PCG** (rotation dépendante de l'état), **xoshiro\*\*** (multiplication en sortie),
  **splitmix64** (mélange bijectif). Le canal donne bien ses 6,32 bits, mais sous une
  forme que ni le réseau ni GF(2) n'exploitent. Le LCG 2⁶⁴ à troncature simple est
  **exclu** (réseau), et les sorties **additives** — xorshift128+, xoshiro256+ — le
  sont aussi (bit 0 exactement linéaire) ;
- un LCG 2⁶⁴ à **multiplicateur non standard** : l'attaque par réseau doit le deviner ;
- un boost dérivé autrement que par des seuils sur `u/2³²` — par exemple
  `u % 1000 < 512` — ne livre aucun bit linéaire et échappe à l'attaque par canaux ;
- un échantillonneur à **consommation variable** (rejet avec redraw) : le nombre de
  mots par tirage n'est alors plus constant, et l'attaque par canaux suppose un W fixe.
  L'hypothèse « boost/bonus sur une instance séparée » (W ∈ 1…4) contourne ce cas et a
  été testée ;
- un CSPRNG (ChaCha20, AES-CTR-DRBG) ou un RNG matériel : dans ce cas la partie est
  close mathématiquement, quelle que soit la quantité de données.

**Le verrou est l'ordre des boules, et il est chiffrable :** 6,32 bits par tirage
aujourd'hui contre **126 bits** avec l'ordre. C'est un facteur 20, et il fait basculer
chaque famille ci-dessus du côté cassable — `mtbreak` le démontre de bout en bout,
`keno_break` est l'outil prêt à l'emploi.

### Ce qu'il faut faire, dans l'ordre

1. **Capter l'ordre.** Le patch de ce dépôt (`Draw.drawOrder`) le conserve. Une seule
   requête suffit à trancher : si `primarySelection` arrive trié, cette voie est morte
   et il faut le savoir tout de suite. `keno_break scanfile` le détecte seul.
2. **Vérifier la fenêtre de mise — c'est maintenant automatique.** `LeakProbe.swift`
   enregistre, pour chaque tirage, le premier instant où l'app voit ses 20 numéros et
   le compare au `wagerEndDate` du même tirage. Une marge **négative** est le cas
   normal (le résultat paraît après la clôture). Une marge **positive**, sur un seul
   tirage, c'est la faille — et elle ne demande aucune cryptanalyse. L'app affiche la
   marge maximale observée sous le dernier tirage ; il suffit de la laisser tourner.
   La sonde note aussi si un tirage a exposé son **boost alors qu'il était encore
   `OPEN`**, ce qui déclencherait le levier du point 3.
3. **Vérifier le boost** — même sonde. Sa table est connue exactement (§7). S'il est
   publié **avant** la clôture, ne jouer que les tirages à boost ≥ 4 multiplie le
   retour par 2,86 — sans prédire un seul numéro.
4. **Si l'ordre est disponible**, lancer `keno_break` : 300 tirages (25 h) pour un
   générateur de classe MT, 2 pour un xorshift128, et tout tirage suivant est prédit
   exactement.

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
- Le contrôle de `lowlcg3` échouait, et j'ai d'abord accusé un **manque de tirages** :
  une mesure partielle montrait 1 500 survivants à 18 quartets et 0 à 26, ce qui allait
  dans ce sens. En vérifiant trois survivants un par un, ils se sont révélés **réels**.
  L'outil n'était pas en cause, mon critère l'était : l'observable ne détermine la paire
  (état, incrément) qu'à une translation d'orbite près, et la translation est une
  identité algébrique exacte (§7 ter). J'ai réécrit le critère, pas l'outil — et relevé
  l'exigence de preuve de 30 à 48 quartets plutôt qu'abaisser la barre à un « presque ».

---

## 10. Reproduire

Chaque résultat négatif ne vaut que ce que vaut le contrôle positif de l'outil qui l'a
produit. `verify_all.sh` les rejoue tous d'un coup — graine plantée retrouvée,
prédiction des tirages retenus, refus d'un flux trié, bon modèle accepté et mauvais W
rejeté, bon générateur accepté et trois mauvais rejetés, LCG64 récupéré et trois
contrôles négatifs rejetés :

```bash
sh verify_all.sh
```

Et une vérification du risque le plus dangereux — un `draws.bin` désaligné ferait
rejeter **toutes** les hypothèses pour une raison qui n'a rien à voir avec le
générateur, donc un faux négatif systématique. `dumpbin.c` imprime ce que les outils C
lisent réellement, à comparer au CSV source :

```
$ ./dumpbin draws.bin 0 2
id=1309614 ts=1757829900 nums=3,4,7,11,16,... boost=3 bonus=70 mask=3,4,7,11,16,... (popcount=20)
$ head -2 ../draws/draws-01.csv | tail -1
1309614,1757829900,3,4,7,11,16,...,80,3,70
```

Identique aux indices 0, 1 et 9000, masque compris.


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
gcc -O3 -o keno_break keno_break.c && ./keno_break scanfile ordered.txt
gcc -O3 -o channel_break channel_break.c -lpthread && ./channel_break 0 22 5500 1 0 0 1
gcc -O3 -o lin_break lin_break.c && sh run_lin_wide.sh          # 3584 essais
```

`seedhunt` s'auto-valide : `./seedhunt 0 0 3000000 4 -1 "0,1,0,1234567"`
plante une graine connue et la retrouve.
