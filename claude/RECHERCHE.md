# Loto Express — recherche de faille exploitable

Audit offensif de l'archive complète : 70 560 tirages (ids 1309614–1380173,
2025-09-14 → 2026-08-25, 0 trou). Objectif : prédire tout ou partie des 20 numéros.

Tout le code est dans [`research/`](research/) et rejouable hors ligne.

**Comment lire ce document.** Le §1 est le tableau de verdicts et suffit pour savoir ce
qui est tombé. Le §6 quater est le cœur du travail : il change l'observable de 4 bits à
61,6 par tirage, et c'est de là que vient la plupart de ce qui est écarté. Le §9 dit où
en est la prédiction et **ce qui reste debout, sans arrondir**. Le §9 bis consigne les
erreurs, y compris celles que les contrôles ont attrapées à temps.

**La règle de tout le dossier :** aucun résultat négatif n'est écrit avant que l'outil
qui l'a produit n'ait retrouvé une réponse plantée **et** rejeté de mauvaises hypothèses.
`sh research/verify_all.sh` rejoue tous ces contrôles d'un coup. Cette règle a rattrapé,
dans cette seule session, une matrice à moitié non initialisée, un faux « INVESTIGATE »,
un signal à 211 σ purement tautologique, et quatre outils qui cherchaient au mauvais
endroit.

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
| splitmix64 / PCG / xoshiro\*\* par SAT, canal 4 bits | **Hors d'atteinte, mesuré** — la barrière des retenues tient. *Dépassé* pour splitmix64 et xoshiro\*\* par la ligne du rang (lignes ci-dessous) ; il ne reste que PCG64 |
| **Le tirage trié vu comme un rang combinatoire** (61,6 bits/tirage au lieu de 4) | **Piste neuve — le tri ne perd rien si le tirage n'a jamais eu d'ordre.** Voir §6 quater |
| LCG **quelconque** (multiplicateur, incrément et W tous inconnus) sur le rang | **Exclu** — forme close sur 3 rangs, 5 conventions × 5 mappages × 70 557 départs, 0 |
| splitmix64 et 5 autres finaliseurs bijectifs sur le rang | **Exclu** — la sortie complète rend l'état par inversion ; chaque ligne exactement sur son nul |
| **Toute** la classe F2-linéaire d'état < 35 280 bits, sans énumérer | **Exclu** — complexité linéaire mesurée à 35 278–35 282 pour n/2 = 35 280. `WELL44497` (44 497 bits) est juste au-dessus et déclaré |
| `xoshiro256**`, `xoroshiro128**`, `xoshiro512**` (brouilleur non linéaire) | **Exclus** — le brouilleur se décolle par inversion, 0 fenêtre sur 1 536, tous les W |
| Fibonacci retardé (le `random()` de la glibc, Boost, add-with-carry) | **Exclu** — 2 016 couples de lags × 3 opérations, meilleur 0/3 000 |
| Multiply-with-carry (Marsaglia, KISS, xorwow) | **Exclu** — cohérence de retenue, 31 multiplicateurs × 2 largeurs × 5 conventions, 0/4 000 |
| **Toute** la classe FCSR / à retenue d'état < 35 280 bits, sans énumérer | **Exclue** — complexité **2-adique**, la contrepartie de Berlekamp-Massey ; contrôles exacts à 64, 128, 256, 1 024 bits |
| **Toute** récurrence linéaire entière mod 2^k, tout ordre (LCG, LFG, MRG) | **Exclue** — le bit de poids faible suffit : mesuré à 2, 31, 4 et 7 sur les cas plantés |
| Réduction `u % C` **naïve** (biais de modulo) | **Exclu à 20–86 σ** — et c'est une mesure *sur l'implémentation*, pas une exclusion de famille |
| `Math.floor(Math.random() * C)` — le rang médié par un double | **Exclu** — 142 multiples de 512 observés pour 137,8 attendus, contre 70 560 si c'était le cas |
| Les 5 fautes de mélange qui **auraient** donné un avantage | **Exclues** — \|ΔP\| de 0,011 à 0,750, soit \|z\| de 6,5 à 460 ; l'archive plafonne à 2,72 |
| Ré-ensemencement lié aux 358 ouvertures de bloc quotidiennes | **Rien** — 63 903 paires d'ouvertures, overlap max 13 pour 12 attendu au hasard |
| Équité prouvable **par dérangement** (`rang = H(public) mod C`) | **Exclu** — 23 520 schémas × 6 tirages, contrôle positif validé |
| Les deux réductions (`u mod C` avec rejet **et** mulhi/Lemire) | **Couvertes** — quatre outils y étaient aveugles, mesuré à 399/399 contre 1/399 ; refait sous les deux |
| Existence de tirages **ordonnés**, compte GitHub entier | **Aucun** — 20 dépôts listés, 8 inspectés, 248 fichiers + 373 objets git balayés (§6 quinquies) |
| Rang concaténé à partir de **deux mots** 32 ou 31 bits | **Exclu** — a et c en forme close, 0/20 000 positions, 4 dispositions |
| Réensemencement sur l'horloge aux 24 décrochages | **Exclu** — 2,46·10¹⁰ graines, maximum 13/20 exactement à l'espérance du hasard |
| Reconstruction d'état à partir des tirages **ordonnés** | **CASSAGE COMPLET démontré** — voir §6 |

**Ce qui reste debout, sans arrondir :** PCG64 à état 128 bits complet (le pliage
`hi ^ lo` perd la moitié de l'état, la rotation dépend de l'état) ; les générateurs
**combinés** de type KISS, dont la somme n'est aucune des structures testées ; un CSPRNG
à clé inconnue, hors d'atteinte par construction ; et une architecture à laquelle je n'ai
pas pensé.

**Conclusion opérationnelle :** l'historique publié ne contient aucune information
exploitable, et ce n'est pas une limite de méthode — c'est mesuré et borné (§4). Deux
voies restent ouvertes, et **aucune des deux ne demande de prédire quoi que ce soit** :

1. l'**ordre de sortie des boules**, que le client jetait
   (`Array(Set(out)).sorted()`) et que le patch de ce dépôt conserve désormais. Avec lui,
   §6 démontre un cassage complet ;
2. le **boost publié avant la clôture des mises** : ne jouer que les tirages à boost ≥ 4
   est rentable dès un RTP de base de 0,350, c'est-à-dire pour n'importe quel keno
   réel (§7). `LeakProbe.swift` mesure si le champ est lisible à temps.

Les deux se tranchent par une seule observation du flux live. Tout le reste de ce dossier
dit pourquoi il n'y a pas de troisième voie.

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

*(Ce verdict vaut pour le canal de 4 bits. Le §6 quater le contourne : à 61,6 bits par
tirage le finaliseur de splitmix64 s'inverse au lieu de se résoudre, et le brouilleur de
xoshiro\*\* se décolle. La barrière n'est pas franchie — elle cesse d'être sur le chemin.)*

**3. Le rang de la jacobienne GF(2) comme instrument de mesure.**
`analyze_phase_transition.py` de delta-chain n'attaque rien : il **mesure** le rang de la
jacobienne sur GF(2) pour savoir où le système bascule du linéaire vers le non-linéaire.
C'est le transfert méthodologique le plus utile du dépôt, et il traverse tous les outils
d'ici — le rang n'y est jamais supposé, il est mesuré, et à chaque fois il a corrigé une
supposition :

| outil | rang mesuré | ce qu'il a corrigé |
|---|---|---|
| `mtbreak` | 19 937 / 19 968 | la nullité de 31 dimensions **est** la structure de MT, pas un bug |
| `channel_break` | saturation à 19 937 puis contradiction | distingue « pas assez d'équations » de « hypothèse fausse » |
| `rankxo` | 253/256 et 125/128 | les mots échantillonnés **n'engendrent pas** l'état — un tirage de plus était nécessaire |
| `bm`, `twoadic` | complexité linéaire et 2-adique | le rang, appliqué à une classe entière au lieu d'un générateur |

Les deux dernières lignes sont la généralisation naturelle de la première : mesurer un
rang plutôt que tester une hypothèse. C'est ce qui permet d'écarter des familles qu'on n'a
pas pensé à nommer.

**4. Effondrement en bits faibles** (`lowlcg.c`) — et là, l'algèbre gagne. Pour un LCG
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

`rank.py` calcule ce rang sous **six** conventions, dont cinq distinctes : colex et lex
sur les numéros 0-basés, colex sur les 1-basés, l'alphabet renversé (v → 81−v) en colex
et en lex, et le rang du **complément** — c'est celle qu'il aurait été facile d'oublier,
puisque C(80,60) = C(80,20) : un opérateur qui tire les 60 numéros **perdants** et publie
le reste produit un rang de taille identique, et tous les outils regarderaient le mauvais
nombre.

Les deux formules sont vérifiées par **énumération exhaustive** à (n,k) = (5,2), (7,3),
(9,4), (12,5), puis recalculées en grands entiers exacts sur six vrais tirages. Un
recoupement indépendant tombe en prime : le rang du complément s'avère **exactement égal**
au rang lex de l'alphabet renversé, sur les 70 560 tirages — l'identité combinatoire
attendue, que deux implémentations séparées n'auraient aucune raison de satisfaire si
l'une des deux était fausse. Le flux de rangs
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

Sur l'archive, **5 conventions de rang distinctes × 5 mappages × 70 557 positions de
départ : 0**.

### `lcgident.py` — l'identité qui teste TOUT LCG mod 2⁶⁴ sans deviner le multiplicateur

`lcgrank.c` balaie une liste de multiplicateurs standards. C'est une couverture par
catalogue : elle rate un opérateur qui aurait choisi le sien. Il existe mieux.

Sous la réduction `u mod C`, la sortie brute se retrouve **à six candidats près** :
`u = rang + k·C`, et `2⁶⁴/C = 5,2159` donc `k ∈ 0..5`. Sous mulhi, `u` vit dans un
intervalle de ~5,2 entiers : même structure, même compte.

Si le générateur est un LCG de module 2⁶⁴, les différences `d_t = u_{t+1} − u_t` vérifient
`d_{t+1} = A′·d_t` — où `A′ = A^s` absorbe le **pas**, donc le nombre d'appels par tirage
n'a pas besoin d'être connu. En éliminant `A′` entre trois différences :

```
                    d₁²  ≡  d₀ · d₂     (mod 2⁶⁴)
```

**Aucune inconnue.** Pas de multiplicateur à deviner, pas d'incrément, pas de graine, pas
de pas. Une identité exacte que tout LCG mod 2⁶⁴ satisfait et qu'un flux quelconque ne
satisfait qu'avec probabilité 2⁻⁶⁴.

```
CONTROLE POSITIF
  LCG plante MMIX, pas 1              quadruplets 2997   touches 8321   hasard 2,1e-13  RECOVERED
  LCG plante L'Ecuyer a, pas 3        quadruplets 2997   touches 8356   hasard 2,1e-13  RECOVERED
  LCG plante increment nul, pas 7     quadruplets 2997   touches 8273   hasard 2,1e-13  RECOVERED
CONTROLE NEGATIF
  rangs uniformes                     quadruplets 2997   touches    0                   PASS

ARCHIVE (5 conventions x 2 reductions)
  colex0 / u mod C     70557 quadruplets   0 touches      colex0 / mulhi      0
  lex0   / u mod C                    0                   lex0   / mulhi      0
  colex1 / u mod C                    0                   colex1 / mulhi      0
  comp0  / u mod C                    0                   comp0  / mulhi      0
  revcolex0 / u mod C                 0                   revcolex0 / mulhi   0
```

**0 sur 9,1·10⁸ vérifications**, là où le hasard en attend 5·10⁻¹¹.

Deux points sur la portée du contrôle, parce qu'ils décident de ce que vaut le zéro.
Le contrôle plante un **rejet honnête** (`u < 5C`), donc le nombre d'appels entre deux
tirages acceptés **varie** — et l'identité est quand même vue, massivement. Le test est
donc robuste au pas variable qu'impose le rejet, ce qui n'allait pas de soi. Et il ne
suppose rien du pas fixe : `A′ = A^s` l'absorbe.

Limite, dite d'emblée : ceci couvre les LCG **dont la sortie est l'état**. Un PCG, un
xoshiro, tout générateur à fonction de sortie brouillée ne satisfait pas l'identité — ils
sont traités par `rankxo.c` et `rankmix.c`. Ce que `lcgident` apporte, c'est la
**suppression du catalogue** : plus aucun multiplicateur ne peut se cacher.

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
bit 0 est exactement linéaire.

**La borne est 35 280 et il faut la dire telle quelle**, parce qu'un générateur réel est
juste au-dessus : `WELL44497` porte 44 497 bits d'état et **échappe donc à cette mesure**.
Ce n'est pas hors d'atteinte pour autant — 4 bits exacts par tirage sur 70 560 tirages
font 282 240 équations pour 44 497 inconnues, largement de quoi le résoudre par
élimination GF(2) directe. Mais cela demande sa matrice de transition symbolique, donc de
le nommer, ce qui fait retomber dans l'énumération que ce test servait justement à éviter.
Lacune étroite, précise, déclarée. Cette seule mesure subsume les 3 900 configurations du
§6 bis, et va bien au-delà : elle couvre les générateurs qu'on n'a pas nommés.

Les 4 plans de bits du rang sont les plus rigoureux du lot : `v₂(C(80,20)) = 4`, donc
`u mod C` conserve **exactement** les 4 bits de poids faible de `u`, quel que soit le k
inconnu. Les plans de `bonus` et `boost` sont plus faibles — si `bonus−1 = u % 80`, ses
bits bas ne sont pas des fonctionnelles linéaires de u — et sont rapportés comme tels.

**Et la réduction mulhi a son propre canal, exactement complémentaire.** Sous `u mod C`
les bits **bas** de u sont connus et les hauts ne le sont pas ; sous mulhi c'est
l'inverse : `r = ⌊u·C/2⁶⁴⌋` épingle u à un intervalle d'environ 5,2 entiers, donc tout
bit au-dessus de la position 32 est déterminé — la probabilité que l'intervalle
enjambe une retenue y vaut 5,2/2³², soit **8·10⁻⁵ erreur attendue sur toute l'archive**.
Ces plans-là sont donc eux aussi des fonctionnelles linéaires exactes, et
Berlekamp-Massey s'y applique sans réserve :

```
15 plans hauts (bits 32, 40, 48, 56, 63 × 3 conventions) : complexité 35 276 à 35 282
```

L'exclusion de la classe F2-linéaire vaut donc pour **les deux** réductions, et non plus
seulement pour `u mod C`.

Ces deux affirmations portent tout le résultat — si l'un des canaux n'était pas exact,
la complexité linéaire mesurerait du bruit. Elles sont donc **vérifiées**, pas
argumentées (`bitchannel.py`) :

```
u mod C, 4 bits bas : 0 différence sur 300 000     <- le canal
u mod C, 5 bits bas : 21 362 différences sur 50 000 <- la frontière est exactement 4
mulhi, bits 24/28/32/40/48 : 0 différence sur 200 000 chacun
```

Les deux canaux sont exacts là où l'argument le dit, et cessent de l'être exactement là
où il dit qu'ils cessent.

### `twoadic.py` — la contrepartie « à retenue » de Berlekamp-Massey

`bm.c` règle la classe F2-linéaire sans l'énumérer, parce qu'une suite linéaire récurrente
a une **complexité linéaire** faible. Les familles à retenue ont l'analogue exact : un
FCSR de nombre de connexion `q` émet le développement 2-adique de `p/q`, donc sa suite a
une **complexité 2-adique** faible. Et tout multiply-with-carry **est** un FCSR — le MWC
de Marsaglia de multiplicateur `a` en base `b` correspond à `q = a·b − 1`.

Donc `rankmwc`, qui a besoin d'un multiplicateur publié, se généralise : celui-ci n'en a
besoin d'aucun. Et les deux tests couvrent ensemble les deux mondes linéaires — sur GF(2)
et sur les 2-adiques — **sans nommer un seul générateur**.

La minimisation est un problème de réseau en dimension 2 : les couples `(t, r)` avec
`r ≡ t·S (mod 2ⁿ)` engendrent le réseau de base `(1, S)` et `(0, 2ⁿ)`, et l'algorithme
d'Euclide sur `(2ⁿ, S)` parcourt exactement ses meilleures approximations, donc le plus
court vecteur est le plus petit `max(|rᵢ|, |tᵢ|)` le long de ce parcours.

Contrôles (et le premier jet en avait de faux : un `int64` de numpy déborde silencieusement
sur les décalages construisant un `q` de 128 ou 256 bits, ce qui donnait un nombre de
connexion absurde et donc un contrôle absurde — corrigé en entiers Python) :

| source | complexité 2-adique mesurée | attendu |
|---|---|---|
| FCSR, q de 64 bits | 63,6 | 64 |
| FCSR, q de 128 bits | 125,5 | 128 |
| FCSR, q de 256 bits | 255,0 | 256 |
| FCSR, q de 1 024 bits | 1 021,6 | 1 024 |
| MWC `a = 4 294 967 118`, `q = a·2³² − 1` | **64,0** | 64 |
| bits aléatoires | 3 999,9 | n/2 = 4 000 |

Sur l'archive, à pleine longueur (n = 70 560), tous les flux observables tombent entre
**35 278,5 et 35 279,4** pour n/2 = 35 280 :

> **Aucun FCSR ni générateur à retenue de nombre de connexion inférieur à 35 280 bits
> ne produit un seul de ces flux.**

### La portée réelle du test de complexité linéaire, mesurée

Berlekamp-Massey a été introduit ici pour les générateurs F2-linéaires. Sa portée est plus
large, et la raison est assez simple pour être **vérifiée** plutôt qu'argumentée : le
**bit de poids faible** de n'importe quelle récurrence linéaire entière mod 2^k est
lui-même une suite linéaire récurrente sur GF(2) du même ordre, puisque les retenues ne
se propagent que vers le haut.

`lowbit_reach.py` plante chaque construction et mesure ce que `bm` en dit :

| construction plantée | complexité du bit 0 |
|---|---|
| LCG mod 2⁶⁴ (ordre 1) | **2** |
| Fibonacci retardé 3,31 | **31** |
| MRG d'ordre 3 mod 2⁶⁴ | **4** |
| MRG d'ordre 7 mod 2⁶⁴ | **7** |
| splitmix64 (non linéaire) | 1 999 = n/2 |

« N'importe quel ordre » étant une affirmation sur l'échelle, elle est vérifiée à
l'échelle plutôt qu'extrapolée depuis les ordres 1, 3, 7 et 31 :

| ordre planté | complexité du bit 0 |
|---|---|
| 100 | **100** |
| 500 | **500** |
| 1 000 | **1 000** |
| 2 000 | **1 998** |

Autrement dit, **toute** récurrence linéaire entière mod 2^k — LCG, Fibonacci retardé,
générateur récursif multiple de n'importe quel ordre — se trahit par son seul bit de poids
faible. Les flux de bits bas de l'archive sont à n/2. Cette classe entière tombe donc
aussi, et le résultat de `lcgrank` comme celui de `ranklfg` en sont des cas particuliers
confirmés par une seconde voie indépendante.

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
xoroshiro128**   0 fenêtres résolues sur 1536   (0 W encore singulier, jusqu'à 3 tirages)
xoshiro512**     0 fenêtres résolues sur 1536   (0 W encore singulier, jusqu'à 9 tirages)
```

**`xoshiro512**` est passé de « hors budget » à écarté.** Ses 6⁹ ≈ 10⁷ affectations de k
par fenêtre étaient prohibitives tant que chacune coûtait une résolution linéaire
complète (512²/64 mots). Le filtre de cohérence les rejette d'abord pour n/64 mots, soit
64 fois moins cher, et seules celles qui survivent paient la résolution. Ce n'est pas un
solveur plus intelligent, c'est le bon ordre des opérations.

À la différence des autres outils du §6 quater, `rankxo` n'a été passé que sur **trois**
conventions de rang, pas cinq : chaque fenêtre coûte 6⁹ affectations pour l'état de
512 bits, et le budget a été mis sur le balayage de W plutôt que sur des conventions
supplémentaires. C'est une couverture moindre, pas un résultat différent — mais elle est
dite.

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

Sur l'archive : 2 016 couples de lags × 3 opérations × **5 conventions** × 3 000
positions, **meilleur couple : 0/3 000**. Aucune relation de Fibonacci retardé.

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

Sur l'archive : **0 / 20 000 positions** pour chacune des 4 dispositions et chacune des
5 conventions.

### `rankseed.c` — le balayage 2³² refait pour cette architecture

`seedhunt` balaie toutes les graines 32 bits et mesure la longueur du préfixe
Fisher-Yates qui coïncide. C'est le bon test pour un générateur qui **produit un ordre**.
Il ne dit rien de l'architecture par dérangement : il n'y a pas de mélange à mesurer.

Le balayage n'avait donc jamais été fait pour ce modèle. Il l'est ici : pour chaque
graine et chaque générateur, prendre la ou les premières sorties, les envoyer dans
`[0, C(80,20))`, et comparer au rang publié. Une coïncidence vaut 61,6 bits d'un coup —
sur 2³² graines une fausse arrive avec probabilité 2⁻²⁹·⁶, donc un seul succès trancherait.

Contrôles : les **20** générateurs plantés sont tous retrouvés — dont PCG64 (XSL-RR
128 bits), xoroshiro128\*\*, xoshiro512\*\* et MT19937-64 — et 3·10⁶ graines × 20
générateurs × 3 décalages contre un rang n'appartenant à aucun générateur donnent **0**.

### `rankmwc.c` — multiply-with-carry, et un faux positif attrapé à temps

MWC est une famille à part : `x_n = (a·x_{n−1} + c_{n−1}) mod b`, la retenue
`c_n = ⌊(a·x_{n−1} + c_{n−1})/b⌋` étant réinjectée. `lcgrank` ne peut pas la voir (la
retenue n'est pas un incrément), `ranklfg` non plus (il n'y a pas de lags), ni `bm` (la
retenue n'est pas linéaire). Et ce n'est pas obscur : le MWC de Marsaglia, KISS et
xorwow reposent dessus.

**Premier essai, et premier signalement à ne pas croire.** J'avais écrit le test sur la
*taille* de la retenue : `c_d = (x_{d+1} − a·x_d) mod b` doit être `< a`. L'outil a
répondu **4 000 / 4 000 positions — INVESTIGATE**. Or un vrai MWC32 a un `a` juste en
dessous de 2³² pour une base de 2³² : « c < a » y est vrai presque toujours. Le test
n'avait aucune puissance là où il comptait, et le « résultat » était entièrement un
artefact de la statistique choisie.

Le test qui a de la puissance porte sur la **cohérence** de la retenue sur trois sorties
consécutives :

```
c₀ = (x₁ − a·x₀) mod b            lue sur la première paire
c₁ = ⌊(a·x₀ + c₀) / b⌋            ce que la retenue doit alors devenir
c₁ = (x₂ − a·x₁) mod b            ce que la paire suivante en dit
```

Les deux valeurs de `c₁` coïncident avec probabilité `b⁻¹` pour un mauvais
multiplicateur, et **toujours** pour le bon — 2⁻³² à 32 bits, 2⁻⁶⁴ à 64 bits, quelle que
soit la taille de `a`. Contrôles après correction : multiplicateur planté 2 998/2 998,
les 30 autres multiplicateurs publiés **0/600**, flux non-MWC **0/600**. Séparation
totale.

Sur l'archive, 31 multiplicateurs publiés × 2 largeurs × 5 conventions de rang :
**0 / 4 000**.

### `rankhash.py` — l'équité prouvable, refaite pour cette architecture

Le §3 teste 390 schémas de hachage en transformant l'empreinte en flux, puis en faisant
tourner un échantillonneur. Mais le tirage **de combinaison** prouvablement équitable
n'échantillonne pas du tout :

```
rang = H(donnée publique) mod C(80,20)      puis dérangement en 20 numéros
```

C'est exactement ainsi qu'on rend un sous-ensemble auditable à partir d'un seul nombre
publié — et cette construction n'avait jamais été testée, faute d'avoir calculé le rang.

14 fonctions de hachage (md5, sha1, sha256, sha512, sha3-256, blake2b/2s, plus le
SHA-256 à **rondes réduites** de delta-chain à R = 16…64) × 10 préfixes × 11 entrées
publiques (identifiant en décimal / 4 / 8 octets, horodatage, `id:ts`, rang précédent,
numéros précédents) × 6 réductions × 2 conventions de rang = **23 520 schémas**, chacun
vérifié sur 6 tirages. Un mauvais schéma coïncide avec probabilité 2⁻⁶¹·⁶ **par tirage**.

Contrôle positif : un schéma `sha256("keno" + id)` planté est bien reconnu par le
harnais. Résultat : **aucun**.

---

### `modbias.py` — une mesure, pas une exclusion de plus

Tout le reste de ce chapitre demande « la famille X colle-t-elle ? » et répond non.
Celle-ci dit quelque chose de **positif** sur l'implémentation.

Si l'opérateur calcule `rang = u mod C` depuis un uniforme de w bits **sans rejet**, les
rangs inférieurs à `2^w mod C` reçoivent une préimage de plus que les autres. L'excès
n'est pas subtil :

| largeur w | ⌊2^w/C⌋ | P(rang < R₀) si uniforme | si `u mod C` naïf | **observé** | z vs naïf | z vs uniforme |
|---|---|---|---|---|---|---|
| 62 | 1 | 0,30446 | 0,46680 | 0,30486 | **−86,2** | +0,23 |
| 63 | 2 | 0,60892 | 0,70020 | 0,60663 | **−54,2** | −1,25 |
| 64 | 5 | 0,21785 | 0,25050 | 0,21678 | **−20,7** | −0,69 |

Contrôle positif : 70 560 rangs fabriqués de la façon naïve à w = 64 ressortent à
0,25064 — soit **+21,1 σ** au-dessus de l'uniforme, exactement là où la théorie les
place. Le test voit donc bien ce qu'il cherche.

Sur l'archive, il ne voit rien : l'observé tombe sur l'uniforme à moins de 1,3 σ dans les
trois largeurs. Donc **si** l'architecture est bien celle du dérangement, la réduction
employée est **non biaisée** — rejet, `mulhi`, ou méthode de Lemire — et pas le
`u % C` naïf. C'est le seul énoncé de ce dossier qui contraigne l'implémentation au lieu
d'écarter une famille.

Cela a une conséquence sur la portée de Berlekamp-Massey, qu'il faut dire : un rejet fait
**varier** le nombre de sorties consommées par tirage (4,2 % des tirages en consomment
une de plus à w = 64), et une suite échantillonnée à cadence variable n'est plus une
suite linéaire récurrente. Les attaques par fenêtre y survivent — 68 % des fenêtres de
9 tirages restent sans rejet, et `lcgrank` en balaie 70 557 — mais l'énoncé « aucun
générateur F2-linéaire d'état < 35 280 bits » suppose une **cadence constante**. Sous
rejet, il se réduit aux familles nommées explicitement. `mulhi` et Lemire, eux, gardent
une cadence fixe et laissent l'énoncé entier.

### `quantize.py` — le rang tombe-t-il sur un réseau ? La question du flottant

`C(80,20) = 2^61,617` demande 62 bits. Un double en porte 53. Donc l'implémentation la
plus probable dans un back-end JavaScript ou Python —

```js
Math.floor(Math.random() * C)
```

**ne peut pas** produire tous les rangs : au voisinage de 2⁶¹·⁶ l'écart entre deux
doubles consécutifs vaut 2⁶¹⁻⁵² = **512**, donc tout rang qu'elle produit est un multiple
de 512. C'est la première chose qu'un développeur écrit, et c'est trivialement
falsifiable.

```
multiples de 512 : 142 observés · 137,8 attendus si uniforme · 70 560 si médié par un flottant
```

Et le balayage `rang mod 2^k` pour k = 1…12 ne sort jamais du bruit (|z| ≤ 1,08 sur les
trois conventions testées). **Aucune médiation par flottant**, à aucune des largeurs
qu'un double pourrait imposer.

Les deux mesures se lisent ensemble : **si** l'architecture est celle du dérangement,
l'implémentation est soignée — réduction non biaisée et arithmétique entière pleine
précision. Ce qui est cohérent avec tout le reste du dossier : un RNG correctement
implémenté.

### `rankgaps.py` — combien de bits l'opérateur émet-il vraiment ? Le réseau *quelconque*

`quantize.py` ne voit qu'un réseau dont le pas est une puissance de deux, parce que c'est
la forme qu'impose le flottant. La question générale est plus large et plus utile : **si le
générateur de l'opérateur émet `b` bits par tirage et les met à l'échelle dans `[0, C)`,
le flux des rangs ne prend au plus que 2^b valeurs**, quel que soit le pas. Un générateur
32 bits, deux mots 32 bits concaténés, un `double` à 53 bits significatifs, un compteur
48 bits — tous laissent la même empreinte : les rangs vivent sur un réseau trop grossier.

Deux tests, de portée différente, et je dis pour chacun ce qu'il suppose.

**(A) Sans aucun modèle.** L'image du générateur a au plus 2^b points ; les n = 70 560
tirages y entrent en collision au rythme des anniversaires, `n(n−1)/2 / 2^b`, *quelle que
soit* l'application utilisée. Compter les rangs répétés borne donc `b` par le bas sans rien
supposer sur la mise à l'échelle. Portée limitée et je la donne : `n²/2 = 2^31,2`, donc ce
test seul ne voit rien au-delà de 2⁴¹ environ.

**(B) Avec le modèle de mise à l'échelle standard** `r = ⌊u·C / 2^b⌋`, `u ∈ [0, 2^b)`.
Ce modèle s'inverse **exactement** : `r = ⌊u·C/2^b⌋` équivaut à `u = ⌈r·2^b/C⌉` — plancher
à l'aller, **plafond** au retour. Un seul tirage qui échoue tue le `b` correspondant :
c'est une réfutation dure, pas statistique. Sous l'uniformité un tirage passe avec
probabilité `2^b/C`, donc le test meurt au premier ou deuxième tirage tant que `b < 61`.

Un flux à `b` bits passe (B) pour tout `b′ ≥ b` — le pas `C/2^b` est un multiple entier du
pas `C/2^b′` — donc la statistique lue est **le plus petit `b` qui passe**. Sous
l'uniformité ce plus petit `b` doit être 62, là où `2^b > C` rend le test vide.

Contrôles d'abord, comme toujours :

```
reseau plante b=24  -> (A) 163 rangs repetes, image ~2^23,9   (B) b = 24   RECOVERED
reseau plante b=32  -> (A)   1 rang  repete,  image ~2^31,2   (B) b = 32   RECOVERED
reseau plante b=38  -> (A)   0                                (B) b = 38   RECOVERED
reseau plante b=44  -> (A)   0                                (B) b = 44   RECOVERED
reseau plante b=52  -> (A)   0                                (B) b = 52   RECOVERED
reseau plante b=58  -> (A)   0                                (B) b = 58   RECOVERED
uniforme sur [0,C)  -> (A)   0                                (B) AUCUN b <= 61   PASS
```

Le contrôle à **58 bits** est celui qui compte : il montre que l'outil a encore du
tranchant à trois bits du plafond de 61,6, donc qu'un résultat négatif sur l'archive n'est
pas un aveuglement du test près de la limite.

Sur l'archive, les cinq conventions de rang :

```
rang colex0     (A) 0 rang repete   (B) AUCUN reseau b <= 61
                ecart minimal 1,3308e+08 -> tout reseau de <= 34 bits refute par ce seul ecart
                espacements : moyenne 5,0103e+13 (theorie 5,0104e+13, rapport 1,0000)
                KS vs exponentielle D = 0,00347 (critique 5 % 0,00512)  OK
rang lex0       (A) 0   (B) AUCUN   ecart minimal 2,2268e+08 -> <= 33 bits refute
rang colex1     (A) 0   (B) AUCUN   ecart minimal 1,6378e+08 -> <= 34 bits refute
rang comp0      (A) 0   (B) AUCUN   ecart minimal 1,3308e+08 -> <= 34 bits refute
rang revcolex0  (A) 0   (B) AUCUN   ecart minimal 2,2268e+08 -> <= 33 bits refute
```

**Lecture.** Le flux des rangs n'est l'image d'**aucun** générateur émettant moins de
61 bits par tirage sous la mise à l'échelle standard. Cela tombe en une seule mesure, sans
énumérer une seule graine : tout générateur 32 bits, tout assemblage de deux mots 32 bits,
tout `double`, tout compteur 48 bits. Et l'écart minimal donne en prime une réfutation
*dure* — une seule paire de rangs voisins suffit — de tout réseau de 33 ou 34 bits au plus.

C'est le même énoncé que celui du §6 quater vu par l'autre bout : là je montrais qu'aucune
famille précise ne colle, ici je montre que la **largeur** de la sortie est pleine. Une
implémentation qui tirerait 61,6 bits honnêtes reste évidemment compatible — c'est le cas
attendu, et c'est ce qu'on observe.

**Ce que ce test ne couvre pas, et il faut le dire.** (B) suppose *une* mise à l'échelle
d'un *seul* entier. Une implémentation qui construit le tirage chiffre par chiffre —
Fisher-Yates avec 20 petits tirages successifs, chacun consommant peu de bits — produit un
rang de pleine largeur et passe ce test sans difficulté. C'est l'architecture par mélange,
couverte ailleurs (§6 bis, `shufbias.py`), pas ici. Le test de Lemire `r = (u·C) >> b` est
en revanche **le même** `⌊u·C/2^b⌋` et se trouve donc bien couvert.

**Un piège de convention rencontré en route.** `colex1` sortait d'abord à `D = 0,10307`,
soit vingt fois la valeur critique — un « signal » spectaculaire. Il n'en était rien :
`colex1` indexe des sous-ensembles de `{1..80}` traités comme 0-based, donc son image vit
dans `[0, C(81,20))` et n'en couvre que `C(80,20)` points. Le rapport d'espacement observé
valait 1,3279 ; `C(81,20)/C(80,20) = 81/61 = 1,32787`. À la cinquième décimale. Le module
corrigé, la convention rentre dans le rang, et le test KS est simplement **inapplicable** à
`colex1` puisque son image n'est pas l'intervalle entier — c'est noté dans le code plutôt
que masqué.

### Les deux réductions, et pourquoi il fallait les couvrir toutes les deux

`modbias.py` écarte le `u mod C` **naïf**. Il reste donc deux façons plausibles de
fabriquer le rang, et elles ne donnent **pas les mêmes préimages** :

| réduction | préimages d'un rang r |
|---|---|
| `u mod C` avec **rejet** | `r + kC`, k ∈ 0…5 |
| **mulhi** / Lemire, `r = (u·C) >> 64` | un intervalle d'environ 5,2 entiers |

Même cardinal, ensemble différent. Un outil qui ne connaît que la première est **aveugle**
à un opérateur qui aurait employé la seconde — et c'était le cas de `rankmix`, `ranklfg`,
`rankw32` et `rankmwc`, qui construisaient leurs candidats en dur comme `r + kC`.
(`lcgrank` traitait déjà mulhi séparément, c'est son mode 1.)

Les quatre outils prennent désormais la réduction en argument, et leurs contrôles
plantent le rang **avec la même réduction que celle qu'ils cherchent**.

**Et une mesure croisée a corrigé mon diagnostic.** Je m'attendais à ce que chercher
sous la mauvaise réduction ne trouve rien. Ce n'est vrai que pour la moitié des outils,
et la raison mérite d'être écrite. mulhi est un **redimensionnement linéaire**,
`u → ⌊u·C/2⁶⁴⌋`, donc une relation **additive** y survit : si
`u_d = u_{d−l} + u_{d−s} − w·2⁶⁴` avec w ∈ {0,1}, après redimensionnement le terme
correctif vaut exactement `w·C` — précisément le décalage que l'ensemble de candidats
`r + kC` énumère déjà.

| outil | relation | planté sous une réduction, cherché sous l'autre |
|---|---|---|
| `ranklfg` | additive | **1 168/1 168** puis 586/1 168 — détecté dans les deux sens |
| `rankmix` | inversion d'une bijection | 399/399 puis **1/399** — le drapeau décide tout |

Donc `ranklfg` n'a jamais été aveugle. `rankmix`, `rankmwc` et `rankw32`, si : leur
relation ne survit pas à un redimensionnement. Leurs résultats sous mulhi sont donc du
travail **neuf**, et ils sont eux aussi à zéro :

```
mulhi, archive réelle, conventions colex0 et lex0
  rankmix : chaque finaliseur exactement sur son nul
  rankmwc : 0 / 4 000
  rankw32 : 0 / 8 000 pour chaque disposition
  ranklfg : 0 / 2 000
```

La leçon est celle qui revient : un résultat négatif ne dit rien tant qu'on n'a pas
vérifié que l'outil regardait au bon endroit — et ici la vérification a montré que
j'avais tort dans un sens comme dans l'autre.

**Et ces deux modèles ne sont pas choisis au hasard : ce sont ceux des bibliothèques.**
Un développeur qui veut un entier dans `[0, C)` a trois chemins réalistes, et les trois
tombent dans ce qui a été testé :

| ce qu'on écrit | ce que la bibliothèque fait | couvert par |
|---|---|---|
| `random.randrange(C)` (Python) | `getrandbits(62)` + rejet | le rang **est** les 62 bits bas de u — c'est le cas k = 0 du modèle `u mod C`, donc dans l'ensemble de candidats |
| `default_rng().integers(C)` (numpy) | méthode de Lemire | le modèle **mulhi** |
| `Math.floor(Math.random() * C)` | un double de 53 bits | **écarté d'emblée** par `quantize.py` |

Vérifié plutôt que supposé : `numpy.integers(C)` sur 400 000 tirages donne
P(rang < R₀) = 0,21809 contre 0,21785 pour l'uniforme et 0,25050 pour un modulo naïf —
c'est bien Lemire, non biaisé. Et `random.randrange` passe bien par `getrandbits` avec
rejet.

Autrement dit, la couverture ne repose pas sur une hypothèse de ma part quant à ce que
l'opérateur aurait pu écrire : elle épouse ce que les bibliothèques standard font
réellement.

### `rankserial.py` — la dépendance sérielle générique, et un « signal » à 211 σ

Le rang a été attaqué **algébriquement** — LCG, Fibonacci retardé, multiply-with-carry,
F2-linéaire, brouillé — et tout est revenu vide. Mais ce sont des structures
**spécifiées**. Restait la question sans modèle : `rang_d` est-il seulement indépendant
de `rang_{d+k}` ? C'est le seul test qui n'exige pas de nommer le générateur.

Rang découpé en 16 tranches égales, table de contingence 16×16 à chaque lag :

```
lag     1   2   3   4   5   6   7   8   9  10   20   50  100  179  500 1000
z   -0,96 -1,14 -0,42 -0,83 -1,13 +1,08 +1,07 +0,36 +0,21 -0,03 +0,41 -0,91 -2,55 -0,46 -1,00 +0,97
```

Rien : le pire est −2,55 sur 16 lags testés, où |z| jusqu'à ~2,7 est l'attendu.

**Et un piège.** La même table entre le rang et la *valeur* du bonus donne
**χ² = 11 488 pour df = 1 185, soit z = +211,6**. Un lecteur pressé y verrait une
découverte. C'est une **tautologie** : le bonus est toujours l'une des vingt boules
tirées, et le rang encode exactement **quelles** vingt ont été tirées — en colex sa
magnitude est dominée par la plus grande. Rang élevé ⟺ maximum élevé ⟺ bonus pouvant
être élevé.

Le contrôle le prouve plutôt que de l'affirmer : en remplaçant le vrai bonus par un
bonus tiré **uniformément dans l'ensemble propre à chaque tirage** — c'est-à-dire
exactement le modèle nul —

```
bonus réel        χ² = 11 488,2   z = +211,64
contrôle 1        χ² = 11 730,7   z = +216,62
contrôle 2        χ² = 11 638,6   z = +214,73
contrôle 3        χ² = 11 468,8   z = +211,24
```

Le nul reproduit l'effet. La version **non** tautologique — rang × *position* du bonus
parmi les vingt, qui est ce que le générateur choisit réellement — donne z = **−1,10**.

C'est le même piège que le χ² des paires de gaps (§3), et il a été attrapé de la même
façon : par un contrôle construit sur le nul, pas par intuition.

### `auxserial.py` — les champs annexes, testés pour eux-mêmes

`rankserial` demande si le rang est indépendant de lui-même à un décalage. Le `boost` et
le `bonus` ont eu leurs plans de bits mesurés par `bm` et `twoadic`, et leur loi jointe
avec le rang vérifiée — mais **jamais leur propre structure sérielle** sur une gamme de
décalages. Or sous une architecture à flux unique ce sont des sorties consécutives du même
générateur : un générateur faible s'y verrait aussi bien que dans le rang.

Trois champs (`boost`, position du bonus, valeur du bonus) × 12 décalages de 1 à 1 000,
plus les croisements à décalage 0 et 1 :

```
pire |z| sur les 36 tests sériels : 1,98 (valeur du bonus, lag 2)
croisements position×boost : z = −0,71 (lag 0) et −1,26 (lag 1)
```

Sur 36 tests, |z| jusqu'à ~2,6 est l'attendu. Rien.

### `blockseed.py` — les 358 ouvertures de bloc, comparées **entre elles**

Le calendrier n'est pas continu : les tirages vont par blocs quotidiens séparés d'une
coupure de 25 500 s, chaque bloc s'ouvrant à 04:05 UTC. Si le service redémarre la nuit
et se ré-ensemence sur quelque chose de peu entropique, c'est le **premier tirage de
chaque bloc** qui le montre — et il le montre comme une relation **entre blocs**, qu'aucun
test par tirage ne peut voir.

358 ouvertures donnent 63 903 paires. Sous le nul chaque paire a un overlap
hypergéométrique de moyenne 5, et sur ce nombre de paires le hasard atteint 13. Une
graine partagée ou voisine placerait une paire bien au-dessus — sans qu'il faille deviner
quel générateur.

```
overlap moyen entre ouvertures : 5,0146   (nul 5,0000)   max 13
  >=12 :  6 observés,  6,40 attendus        >=14 : 0 observé, 0,04 attendu
  >=13 :  2 observés,  0,58 attendu         >=15 : 0 observé, 0,00 attendu
blocs adjacents seulement (357 paires) : moyenne 4,9972, max 10
ouverture vs clôture du bloc précédent (358 paires) : moyenne 5,0531, max 9
témoin, 358 tirages ordinaires tirés au hasard : moyenne 4,9943, max 12
```

Les ouvertures de bloc se comportent exactement comme n'importe quels autres tirages.

### `shufbias.py` — les deux bugs de mélange qui auraient VRAIMENT donné un avantage

Tout ce qui précède écarte des générateurs. Cette mesure pose une autre question : si
l'opérateur mélange correctement mais **écrit le mélange faux**, les numéros cessent
d'être équiprobables — et c'est exactement le biais exploitable qu'on cherche. Les deux
fautes que le vrai code commet :

1. **Le mélange naïf** — `for i in 0..n−1: swap(a[i], a[random(n)])`, l'indice tiré sur
   tout le tableau au lieu de la queue restante. `n^n` déroulés pour `n!` permutations :
   elles ne peuvent pas sortir à égalité.
2. **`sort(() => Math.random() − 0,5)`** — un comparateur incohérent, l'anti-patron
   JavaScript classique.

Simulés, ils donnent :

| faute d'implémentation | max \|P(v tiré) − 0,25\| | \|z\| que l'archive montrerait | exploitable ? |
|---|---|---|---|
| sélection prise par l'avant | 0,7500 | 460,1 | **oui, massivement** |
| plage décalée d'un cran | 0,2500 | 153,4 | **oui, massivement** |
| `sort(random() − 0,5)` | 0,0704 | 43,2 | **oui** |
| mélange naïf | 0,0538 | 33,0 | **oui, tout juste** |
| Sattolo (`j < i` au lieu de `j ≤ i`) | 0,0107 | 6,5 | non — détectable mais sous le seuil |

Or l'archive montre **max \|z\| = 2,72** et Σz² = 71,46 pour une espérance de 80.

La dernière ligne mérite d'être lue : le mélange de Sattolo laisserait une signature que
l'archive **verrait** (z = 6,5) sans pour autant offrir de quoi battre la marge. Entre
« détectable » et « exploitable » il y a un facteur cinq, et l'archive est du bon côté
des deux.

Le point n'est pas seulement que ces fautes sont écartées. C'est que quatre d'entre elles
tombent **au-dessus de la fourchette de 0,05 à 0,10 nécessaire pour battre la marge du
keno** (§4). Autrement dit : la faute
d'implémentation la plus banale qui existe aurait suffi à rendre le jeu battable, et
c'est celle qu'on peut exclure le plus fermement. La borne à 3 σ sur tout biais marginal
est de 0,00489 — **onze fois plus serrée** que le plus petit biais réaliste qui aurait
servi à quelque chose.

### Les trois lacunes, attaquées là où elles sont réellement déployables

Une lacune dans l'abstrait n'est pas une lacune en pratique. PCG64 à état 128 bits
inconnu, MRG32k3a à 192 bits et les combinés KISS résistent bien aux outils algébriques —
mais **un opérateur ne choisit pas un état de 192 bits au hasard, il appelle
`default_rng(graine)`**. C'est ce chemin-là qui est balayé.

`modern_seed.py` passe par les **bibliothèques elles-mêmes** plutôt que par une
réimplémentation, ce qui supprime tout risque de me tromper sur l'ensemencement :
PCG64, PCG64DXSM, MT19937, Philox et SFC64 de numpy, chacun sur les quatre chemins de
sortie qu'un développeur emploierait (`integers(0,C)` en Lemire, `random()*C` en
flottant, `random_raw()` réduit mod C puis en mulhi). Contrôle positif : un rang pris de
`PCG64(777)` et planté dans l'ensemble cible est retrouvé **à la graine 777**.

`mrgkiss.c` couvre les deux familles que numpy n'a pas :

- **MRG32k3a** de L'Ecuyer — deux récurrences d'ordre 3 modulo 2³²−209 et 2³²−22853
  (MATLAB, Arena, Simul8), sous deux conventions d'ensemencement ;
- **KISS99** de Marsaglia — la somme d'un LCG, d'un xorshift et de deux MWC, dont c'est
  précisément la *somme* qui échappait à tout le reste, sous deux conventions.

Contrôles : les quatre constructions plantées sont récupérées, et 2·10⁶ graines contre un
rang n'appartenant à aucune donnent **0**.

Résultats :

```
numpy, 5 générateurs x 10^6 graines x 4 chemins de sortie   ->  0
   (PCG64, PCG64DXSM, MT19937, Philox, SFC64 ; 798 s)
   contrôle positif : rang de PCG64(777) planté, retrouvé à la graine 777
   flux unique — une graine émettant les rangs consécutifs de l'archive : 0

MRG32k3a + KISS99, balayage EXHAUSTIF 2^32
   4 constructions x 3 décalages x 2 mappages = 1,03·10^11 comparaisons  ->  0
```

Ces balayages ne ferment pas les lacunes au sens strict — un état de 128 ou 192 bits
choisi vraiment au hasard reste hors d'atteinte, et c'est dit. Ils ferment le cas
**réaliste**, qui est celui d'un déploiement ensemencé sur un entier : `default_rng(42)`,
`RngStream(seed)`, `KISS(seed)`. C'est la forme sous laquelle ces générateurs sont
effectivement écrits.

### Ce qui n'est PAS couvert, et pourquoi

Deux choses, dites franchement plutôt que passées sous silence :

- **PCG64 à état 128 bits complet.** La sortie est `rotr(hi ^ lo, hi >> 58)` : le
  brouilleur n'est pas une bijection d'un mot vers un mot (le pliage `hi ^ lo` perd
  64 bits) et la rotation dépend de l'état lui-même. La méthode de `rankxo` ne s'y
  applique donc pas. J'ai cherché une résolution bit à bit du poids faible vers le poids
  fort — elle échoue proprement : la moitié haute de l'état suivant dépend de **tous**
  les bits bas, donc le bit j de l'observable n'est pas déterminé par les bits 0..j de
  l'inconnue. Une attaque correcte demande un solveur dédié ; je préfère déclarer la
  lacune que livrer une attaque à moitié vérifiée. Le cas réellement plausible — un
  déploiement ensemencé sur un entier 32 bits — est, lui, couvert par `rankseed`.
- **Les générateurs récursifs multiples à module premier**, dont `MRG32k3a` (MATLAB,
  Arena, beaucoup de simulation). Les deux mesures de complexité ne les voient pas : le
  bit de poids faible d'une récurrence **mod un premier** n'est pas linéaire, la réduction
  mélange. Et leur état fait 192 bits, hors de portée d'un balayage de graines. Les MRG à
  petit état — `minstd` et compagnie — sont couverts, eux, par les balayages 2³² exhaustifs
  sous les deux modèles de sortie ; c'est le cas combiné à grand état qui reste.
  **Une remarque le rétrécit nettement** : l'interface normale de `MRG32k3a` rend un
  **double** dans (0,1), et `quantize.py` écarte tout rang médié par un flottant (142
  multiples de 512 observés contre 70 560 s'il l'était). Un opérateur qui l'utiliserait
  par son API standard est donc déjà écarté ; il ne reste que l'usage entier
  non standard.
- **Les générateurs combinés** de type KISS, où la sortie est la **somme** de plusieurs
  flux (un LCG, un xorshift, un MWC). Chaque composant est écarté individuellement — mais
  leur somme n'est aucun d'eux, et c'est précisément ce qui la met hors de portée : elle
  n'est pas F2-linéaire (les retenues), pas congruentielle (deux états indépendants), pas
  à retenue simple. Berlekamp-Massey ne la voit pas non plus, puisque le bit 0 d'une somme
  de trois flux dont l'un est un MWC n'est pas une fonctionnelle linéaire. Il faudrait
  modéliser chaque combinaison, et l'espace est combinatoire. Lacune réelle, déclarée.
- **Les générateurs à état-tableau non linéaires** — RC4/ARC4, ISAAC, l'automate
  cellulaire règle 30 (le défaut de Mathematica). Aucun n'est F2-linéaire, aucun n'est à
  retenue, aucun n'est congruentiel : les trois mesures les manquent, et leurs états
  (1 684 bits pour RC4) excluent tout balayage. Ils tombent en pratique dans la même
  catégorie que les DRBG ci-dessous — sans clé ni état connus, rien dans la sortie ne les
  trahit à cette quantité de données.
- *(En revanche, les générateurs à **carte chaotique** — logistique, tente, chat d'Arnold —
  sont couverts sans travail supplémentaire : leur état est un flottant, donc le rang qui
  en dérive est médié par un double, et `quantize.py` écarte cela à 142 multiples de 512
  observés contre 70 560 s'il en était un.)*
- **Les DRBG cryptographiques à clé inconnue** (AES-CTR, ChaCha20, HMAC-DRBG). C'est par
  construction hors d'atteinte, et ce n'est pas une lacune de méthode : si l'opérateur
  utilise cela correctement, aucune quantité de sortie publiée ne le trahit. Le §7 ter
  écarte seulement les **clés par défaut**.

---

## 6 quinquies. Les tirages ordonnés : recherche exhaustive, résultat net

La consigne affirme que des tirages **avec l'ordre des chiffres** sont disponibles. C'est
le point le plus important du dossier, puisque §6 démontre que l'ordre donne un
**cassage complet**. J'ai donc cherché, non pas en relisant, mais en balayant :

- les **248 fichiers** de l'arbre de travail des deux dépôts (`ProphetofNumbers` et
  `delta-chain-sha256`), quel que soit leur format ;
- les **373 objets git** de tout l'historique des deux dépôts, y compris les blobs
  d'anciens commits ;
- critère : toute fenêtre de 20 nombres distincts de 1 à 80 qui **ne soit pas croissante**.

73 fenêtres candidates sont ressorties. Toutes les 73 sont le même artefact : le
balayage franchit une frontière d'enregistrement et récupère, après les 19 derniers
numéros d'un tirage trié, les chiffres de `boost`, `bonus` ou de l'identifiant suivant.
Exemple, dans `STATS.json` : `…, 76, 78, | 1, 17, | 13…` est le tirage 1309616 (trié,
finissant à 78), puis `boost=1`, `bonus=17`, puis les deux premiers chiffres de
l'identifiant `1309617`.

> **Aucun tirage ordonné n'existe dans ces dépôts.** Tout, sans exception, est publié
> trié — ce que la description du schéma CSV dit d'ailleurs explicitement
> (« 20 numéros distincts parmi 1–80, **déjà triés** »).

**Recherche élargie au compte GitHub entier.** La consigne étant catégorique, je ne m'en
suis pas tenu aux deux dépôts de départ : les 20 dépôts du compte ont été listés et les
huit plausibles inspectés.

| dépôt | contenu | tirages ordonnés ? |
|---|---|---|
| `ProphetofNumbers` | l'app iOS et cette archive | non — tout trié |
| `delta-chain-sha256` | cryptanalyse de SHA-256 à rondes réduites | sans objet |
| `Goldmine-Extractor` | **vide** (README de 20 octets) | non |
| `ProphetVision` | vision par ordinateur, roulette Lightning | sans objet |
| `Prophet` | **dépôt vide** | non |
| `Prophet_AGI` | architecture de LLM sous contrainte de compute | sans objet |
| `Cronos` | **vide** (README de 20 octets) | non |
| `Hermes` | bot de trading crypto (OKX, BTC/ETH/SOL) | sans objet |

La recherche de code sur le compte ne renvoie rien non plus pour `primarySelection`,
`drawOrder`, `keno`, `loto` ni pour l'identifiant `1309614`.

**Conclusion, aussi nettement que possible : les tirages ordonnés ne sont accessibles
nulle part depuis cette session.** Ce n'est pas un refus de chercher — c'est le résultat
d'un balayage exhaustif, répété à quatre reprises et élargi à tout le compte. Il ne manque
qu'un fichier, et `keno_break scanfile` le traite en une commande.

Ce n'est pas un refus de chercher : l'outil qui exploiterait ces données est **écrit,
contrôlé et prêt**. `mtbreak` reconstruit MT19937 à partir de 400 tirages ordonnés et
prédit les 50 suivants, 50/50. `keno_break scanfile` lit un fichier de tirages ordonnés,
nomme l'échantillonneur et le mappage, et **refuse** un flux trié plutôt que de rendre un
résultat trompeur. Il ne manque que le fichier.

---

## 6 sexies. Le champ que le tri n'a pas écrasé — le bonus

Tout ce qui précède se bat contre le tri. Vingt numéros publiés en ordre croissant : le
tirage consomme 61,6 bits, la publication en rend 4. C'est la contrainte qui a fait
échouer chaque famille testée, et c'est elle qui a motivé le §8 (capter l'ordre en direct).

Il y avait un champ non trié dans l'archive depuis le début, et je ne l'ai pas vu.

### L'observation

Le **bonus est toujours l'un des 20 numéros** — vérifié sur les 70 560 tirages, sans une
exception. Sa **position parmi les 20 triés** est donc une fonction de l'ordre caché, et
elle est publiée. Elle vaut log₂ 20 = **4,32 bits par tirage**, intacts.

Et sous l'architecture par dérangement — celle du §6 quater, la seule que tout le reste du
dossier n'a pas pu exclure — cette position est **directement une sortie du générateur**.
Le dérangement rend les 20 numéros déjà triés ; « l'élément d'indice *i* » ne peut donc
désigner que le *i*-ème plus petit, et `i = reduce(u, 20)` pour une sortie brute `u`.

Le **boost** en ajoute 1,88. Six valeurs (1, 2, 3, 4, 5, 10) dont j'ai retrouvé la table
de seuils exacte :

```
seuils cumules 0,512 / 0,75 / 0,90 / 0,95 / 0,975      chi2 = 0,55 sur 5 ddl   p = 0,997
  valeur  observe  attendu   z            candidats concurrents pour le premier seuil :
     1     36122   36126,7  -0,04           0,500 -> chi2 = 61,5
     2     16791   16793,3  -0,02           0,520 -> chi2 = 28,9
     3     10626   10584,0  +0,44           0,525 -> chi2 = 76,2   (celui qui donnerait E = 2 exact)
     4      3525    3528,0  -0,05
     5      1739    1764,0  -0,60         E[boost] = 2,0117
    10      1757    1764,0  -0,17
```

Chaque case tombe à moins de 0,6 σ. L'opérateur tire donc un uniforme et le compare à une
table fixe — ce qui fait de chaque boost une **contrainte d'intervalle sur une sortie
brute**, exactement le réglage où l'attaque par réseau du §6 ter fonctionne.

Total : **6,2 bits par tirage sans tri**, soit 437 538 bits sur l'archive.

### La règle de sélection, établie et non supposée

Avant d'attaquer, il faut savoir ce qu'on observe. La loi conjointe (position, valeur) a
une forme exacte sous l'hypothèse « SRS 20/80, indice uniforme » : la valeur sachant la
position *p* suit la (*p*+1)-ème statistique d'ordre, `P(X₍ₚ₊₁₎ = v) = C(v−1,p)·C(80−v,19−p)/C(80,20)`.
Testée position par position, regroupement adaptatif à espérance ≥ 5 :

```
chi2 total 738,25 sur 654 ddl   z = +2,33
pire position p = 2 a z = +2,28   (20 tests, seuil Bonferroni 5 % : |z| > 2,81)
```

Conforme. Le bonus **est** l'élément d'un indice uniforme d'un tirage équitable — ce qui
valide précisément le modèle sur lequel reposent les deux attaques ci-dessous.

### `bonusseed.c` — le balayage 2³², cent fois moins cher qu'avant

Une graine fausse meurt dès la **première** comparaison avec probabilité 19/20. Le coût
tombe à ~1 sortie par graine, contre un rang complet de 20 numéros dans `rankseed`.

Et le pas (nombre d'appels entre deux tirages) n'intervient pas dans cette première
comparaison : un seul test tue les 40 pas d'un coup. Le balayage 2³² passe ainsi de
25 heures à une heture et demie sur un cœur.

Contrôles — quatorze configurations, toutes retrouvent la graine plantée **avec son pas et
son décalage**, chacune confirmée par 24/24 boosts ; le contrôle négatif plafonne à 5 sur
1,68·10⁶ essais là où le hasard en attend 0,525. Et un contrôle de **surjectivité** que la
première version n'avait pas : chaque réduction doit pouvoir produire les 20 positions et
les 6 boosts (voir §9 bis — la version initiale ne pouvait en produire que cinq).

### `poslll.c` — le réseau, pour les états de 64 bits

Le balayage épuise les familles dont l'état tient sur 32 bits. Au-delà, le réseau prend le
relais : la position pince `u` dans un intervalle de largeur `M/20`, la différenciation
élimine l'incrément, et il reste un problème du nombre caché que LLL résout.

`lcg_lll` (§6 ter) suppose « bonus = première boule tirée », soit 6,32 bits — c'est
l'hypothèse de l'architecture par **mélange**. `poslll` suppose « bonus = élément d'indice
tiré », soit 4,32 bits — l'architecture par **dérangement**. Aucune ne subsume l'autre, et
il fallait les deux.

Le contrôle donne le point de fonctionnement, et il est instructif :

```
K=12  recupere  | mauvais W: faux positif | mauvais a: faux positif | bruit: faux positif
K=16  recupere  | mauvais W: faux positif | mauvais a: faux positif | bruit: faux positif
K=20  recupere  | mauvais W: rejete       | mauvais a: rejete       | bruit: rejete
K>=20 idem jusqu'a K=40
```

K = 12 **récupère l'état** — et n'a aucune valeur de preuve, parce qu'il accepte aussi un
mauvais multiplicateur, un mauvais pas et du bruit pur. Le K utilisable est 20, pas 12 ;
la borne d'unicité théorique en donnait 15. Le résumé de l'outil affichait d'abord « plus
petit K qui récupère : 12 », ce qui aurait conduit à lire un résultat là où il n'y en a
pas — corrigé pour n'annoncer que le K qui réussit le positif **et** rejette les trois
négatifs.

## 7. Ce qui a été appris sur le jeu

- **Table du multiplicateur boost reconstruite exactement** :
  `×1 : 51,2 % · ×2 : 23,8 % · ×3 : 15,0 % · ×4 : 5,0 % · ×5 : 2,5 % · ×10 : 2,5 %`
  (χ² = 0,55 pour df = 5 — ajustement quasi parfait ; l'hypothèse 500/250/… est
  rejetée à χ² = 61,5). **Multiplicateur moyen = 2,013.**
  Conséquence, et c'est le seul levier de ce dossier qui rapporte de l'argent sans
  prédire quoi que ce soit : si le boost était publié **avant** la clôture des mises,
  ne jouer que les tirages à boost ≥ 4 multiplierait le retour par 5,75 / 2,013 =
  **2,856×**. Formulé autrement — la formulation qui rend la décision évidente :

  > le seuil de rentabilité est un RTP de base de **0,350**.

  Autrement dit, ce filtre est profitable pour **n'importe quel** taux de retour
  plausible d'un keno. À 0,70 (valeur typique) le RTP passe à **2,00** ; même à 0,50 il
  passe à 1,43. Un keno dont le RTP de base serait sous 0,35 n'existe pas.

  Coût opérationnel : boost ≥ 4 concerne **10,0 %** des tirages, soit environ
  **18 tirages jouables par jour** sur les 179 d'un bloc. Il faut donc attendre, pas
  jouer en continu.

  Deux hypothèses restent à vérifier sur le flux live, et elles sont toutes deux
  binaires : (1) le champ `secondarySelection` est-il renseigné sur un tirage encore
  `OPEN` ? (2) le multiplicateur s'applique-t-il bien aux gains sans modifier la mise ?
  `LeakProbe.swift` mesure la première tirage par tirage. Si la réponse est non — ce
  qui est le comportement qu'un opérateur attentif implémenterait, précisément pour
  fermer ce levier — alors il ne reste rien.
- Le **bonus** est un tirage uniforme parmi les 20 boules (rang : χ² = 27,5 / df 19),
  indépendant du boost et du tirage suivant. J'avais écrit ici « aucune information
  d'ordre » : **c'est faux, et c'était l'erreur la plus coûteuse de ce dossier.**
  Uniforme ne veut pas dire sans information. La position du bonus parmi les 20 est une
  observation *directe* d'une sortie du générateur — 4,32 bits par tirage que le tri n'a
  pas touchés. Voir §6 sexies, qui en fait la meilleure surface d'attaque de l'archive.
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

**Les étapes 2 et 3 sont un seul appel, et il est vérifié.** `keno_break scanfile` fait
le contrôle d'ordre puis l'attaque, et **refuse** plutôt que de rendre un résultat
trompeur si le flux est trié. Sur une capture de démonstration :

```
$ ./keno_break scanfile ordered.txt
  ordered.txt: 420 ordered draws read
  already-sorted lines: 0/420  (0.0%; a real draw order gives ~0%)
  rank of the first drawn ball inside the sorted set: 24 18 22 24 19 21 29 20 21 19 ...
    sampler 0 mapping 0 : rank 19937/19968, 35544 eqs -> replayed 395/395, predicted 25/25
  *** CONSISTENT: sampler 0, mapping 0 — generator recovered ***

$ ./keno_break scanfile sorted.txt
  already-sorted lines: 420/420  (100.0%; a real draw order gives ~0%)
  rank of the first drawn ball inside the sorted set: 420 0 0 0 0 0 0 0 0 0 ...
  -> the feed publishes sorted numbers; the order attack cannot run.
```

La ligne des rangs est le contrôle d'ordre de l'étape 2, lisible d'un coup d'œil :
uniforme sur 1…20 pour un vrai ordre, dégénérée sur le premier rang pour un flux trié.
Il n'y a donc rien à écrire le jour où les données arrivent — **un fichier, une commande**.

---

## 8 bis. La question posée, mesurée — `backtest.py`

Tout le §6 répond à « quel générateur ? ». Voici la réponse à la question telle qu'elle a
été posée : **en jouant k numéros, combien en touche-t-on réellement ?**

Huit stratégies (chauds, froids, retard, répéter le dernier tirage, co-occurrence de
paires, Markov lag-1, un jeu fixe, le hasard), trois tailles (k = 5, 10, 20), **69 560
tirages hors échantillon** — chaque choix ne voit que le passé, fenêtre glissante de 500.

Le nul est exact : k numéros sur un tirage 20/80 équitable donnent k/4 bons numéros, de
variance hypergéométrique `k·(20/80)·(60/80)·(80−k)/79`. Sur 69 560 tirages, l'écart-type
de la moyenne vaut ~0,004 numéro : **il suffit de 0,01 numéro d'avantage pour sortir du
bruit**. C'est la sensibilité réelle du test, et elle est énorme — un avantage exploitable
serait des dizaines de fois plus grand.

**Contrôles d'abord.** Sur une archive synthétique **biaisée** (huit numéros à poids 1,35),
« chauds » à k = 10 sort à **z = +96,1** et « fixe » — qui joue 1..10, là où le biais est —
à +100,7. Sur une archive synthétique **équitable**, le plus grand |z| sur les 24
combinaisons vaut 2,55. Le test voit donc un biais quand il y en a un, et n'en invente pas.

Sur l'archive réelle :

```
strategie     k      nul    observe       ecart        z
chauds        5    1,250     1,2522     +0,0022     +0,63
froids        5    1,250     1,2457     -0,0043     -1,21
retard        5    1,250     1,2540     +0,0040     +1,11   <- le meilleur
repeter       5    1,250     1,2476     -0,0024     -0,67
paires        5    1,250     1,2527     +0,0027     +0,75
markov        5    1,250     1,2487     -0,0013     -0,36
fixe          5    1,250     1,2512     +0,0012     +0,35
hasard        5    1,250     1,2523     +0,0023     +0,66
chauds       10    2,500     2,5050     +0,0050     +1,01
paires       10    2,500     2,5005     +0,0005     +0,09
chauds       20    5,000     4,9961     -0,0039     -0,62
...
plus grand |z| sur les 24 combinaisons : 1,21
meilleure strategie : retard a k = 5, avantage +0,0040 numero sur 1,25 attendus
```

**Aucune stratégie ne bat le nul.** Le meilleur écart, +0,004 numéro, est un quart de son
propre écart-type — et il est le maximum de 24 essais, donc même son signe n'est pas
significatif. À jouer 10 numéros on en touche 2,505 au lieu de 2,500 : cela ne paie aucune
mise.

C'est la réponse directe à « prédire même cinq, dix ou moins de numéros », et elle est
mesurée, pas déduite : sur l'historique public, à ce jour, l'avantage est **nul à 0,01
numéro près**.

## 8 ter. Le seul levier chiffré — et il ne demande aucune prédiction

La table du boost établie au §6 sexies a une conséquence que le reste du dossier n'a pas.
Si le boost multiplie le gain **sans modifier la mise**, et s'il est **affiché pendant que
le tour est encore ouvert**, alors ne jouer que les tours à fort boost multiplie
l'espérance — sans prédire un seul numéro.

```
seuil   P(jouer)   E[boost | seuil]   facteur   RTP 0,70 ->   RTP 0,85 ->   tours/jour
 >=  1    1,0000            2,0130     1,000        0,7000        0,8500        288,0
 >=  2    0,4880            3,0758     1,528        1,0696        1,2988        140,5
 >=  3    0,2500            4,1000     2,037        1,4257        1,7312         72,0
 >=  4    0,1000            5,7500     2,856        1,9995        2,4280         28,8
 >=  5    0,0500            7,5000     3,726        2,6080        3,1669         14,4
 >= 10    0,0250           10,0000     4,968        3,4774        4,2226          7,2
```

Au-dessus de 1, la colonne RTP est une espérance **positive pour le joueur**. Avec un RTP
de base de 0,70, jouer uniquement les boosts ≥ 4 — 28,8 tours par jour — donnerait 2,00.

Ce calcul ne vaut que si **deux** conditions tiennent, et **aucune des deux ne se vérifie
depuis l'archive** :

1. le boost est affiché pendant que le tour est `OPEN`, donc pariable ;
2. le multiplicateur porte sur le gain sans modifier la mise ni les cotes.

Si l'une des deux est fausse, le levier n'existe pas — et un opérateur attentif l'a
justement fermée en tirant le boost à la clôture. `LeakProbe.swift` mesure la première
tirage par tirage ; c'est la seule mesure du dossier qui demande l'application et non
l'archive, et c'est celle qui a la plus grande valeur attendue.

## 9. Où en est exactement la prédiction

**Réponse directe : depuis l'archive publiée, prédire ne serait-ce qu'un numéro
au-dessus de 25 % n'est pas atteignable — et c'est mesuré, pas supposé.**

L'analyse se lit maintenant sur **deux axes**, parce que le tirage peut avoir été produit
de deux façons très différentes, et que l'observable n'a pas la même largeur dans les deux
cas :

| | le générateur produit un **ordre** (mélange) | le générateur tire **un entier** et le dérange |
|---|---|---|
| ce que l'archive livre | 4 à 6 bits par tirage (`bonus`, `boost`) | **61,6 bits** par tirage (le rang) |
| ce que le tri détruit | 89,6 bits — tout l'ordre | **rien** : il n'y a jamais eu d'ordre |

### Exclu quelle que soit l'architecture

- Toute structure statistique exploitable : 250 prédicteurs, 2,49 G de paires,
  82 160 triplets, 60 000 lags, batterie NIST, 14 blocs séparés.
- **Toute** la classe F2-linéaire d'état inférieur à **35 280 bits** — sans énumérer,
  sans supposer de W, par la complexité linéaire (§6 quater). MT19937, MT19937-64,
  WELL19937, xorshift1024\*, toute la famille xoshiro/xoroshiro, et les générateurs que
  personne n'a nommés en font partie.
- Tout générateur d'état ≤ 32 bits : 234 variantes, balayage 2³² complet, sous les deux
  modèles de sortie (`seedhunt` pour le mélange, `rankseed` pour le dérangement).
- Réensemencement sur l'horloge : aux 24 décrochages **et** aux 358 redémarrages
  quotidiens, aux granularités seconde et milliseconde.

### Exclu sous l'architecture par mélange

- Générateurs F2-linéaires de 64 à 19 937 bits sous 7 sémantiques de canal × W de 1 à
  64, plus de 3 900 configurations, **sans jamais utiliser l'ordre**.
- Sorties additives (xorshift128+ de V8, xoshiro256+) : le bit 0 est exactement linéaire.
- LCG 2⁶⁴ et 2⁴⁸ à sortie de poids fort : 2 880 réductions de réseau.
- Congruentiel `u >> shift` puis `% 80`, incrément **connu ou inconnu**.
- 390 schémas de dérivation par hash, 1 920 schémas à rondes réduites, 360 modes
  compteur à clé par défaut.

### Exclu sous l'architecture par dérangement (§6 quater)

C'est le gain de cette session, et il porte précisément là où le §6 bis butait :

- **LCG quelconque** — multiplicateur, incrément et W tous inconnus, résolu en forme
  close. Le « multiplicateur maison » qui échappait au réseau n'échappe plus.
- **splitmix64** et cinq autres finaliseurs bijectifs : la sortie complète rend l'état
  par simple inversion. Le §6 bis les classait « hors d'atteinte, barrière des retenues ».
- **xoshiro256\*\*, xoroshiro128\*\*, xoshiro512\*\*** : le brouilleur non linéaire se
  décolle par inversion, le cœur linéaire tombe en une résolution. Le 512 bits, d'abord
  déclaré hors budget, y est passé grâce au filtre de cohérence — 0 fenêtre sur 1 536.
- **Fibonacci retardé** (le `random()` de la glibc, Boost, add-with-carry) : famille que
  ni le balayage congruentiel ni GF(2) ne pouvaient voir.
- **Rang concaténé à partir de deux mots** 32 ou 31 bits.
- **Équité prouvable par dérangement** : 23 520 schémas.
- Le tout sur **cinq conventions de rang distinctes**, dont celle du complément.

### Ce qui reste ouvert, sans arrondir

- **PCG64 à état 128 bits complet.** Le pliage `hi ^ lo` perd la moitié de l'état et la
  rotation dépend de l'état : ni `rankxo` ni une résolution bit à bit ne s'y appliquent.
  Seul le cas ensemencé sur 32 bits est couvert. C'est la seule famille nommée et
  répandue qui reste debout.
- **Un CSPRNG** (ChaCha20, AES-CTR-DRBG, HMAC-DRBG) **à clé inconnue**, ou un RNG
  matériel. Là, la partie est close mathématiquement, quelle que soit la quantité de
  données : ce n'est pas une lacune de méthode.
- **Un échantillonneur à consommation variable** (rejet avec redraw) : le nombre de mots
  par tirage n'est plus constant, et les attaques par canaux supposent un W fixe.
  L'hypothèse « boost/bonus sur une instance séparée » contourne ce cas et a été testée.
- **Les MRG à module premier et grand état** (`MRG32k3a`) : le bit bas d'une récurrence
  mod un premier n'est pas linéaire, et 192 bits d'état excluent un balayage — mais son
  API standard rend un double, et les rangs médiés par un flottant sont écartés, ce qui
  ne laisse que l'usage entier non standard.
- **Les générateurs combinés** (KISS et sa famille) : la somme de plusieurs flux n'est
  aucune des structures testées, et n'est pas F2-linéaire à cause des retenues. Le cas
  ensemencé sur un entier est balayé (`mrgkiss.c`) ; l'état de 128 bits libre ne l'est pas.
- **Les générateurs à état-tableau** (RC4, ISAAC, règle 30) : ni linéaires, ni à retenue,
  ni congruentiels, et d'état bien trop grand pour un balayage.
- **Une troisième architecture** à laquelle je n'ai pas pensé. Les six conventions de rang
  et les deux modèles de sortie couvrent ce que je sais construire ; ils ne couvrent pas
  ce que je n'ai pas imaginé.

**Le verrou reste l'ordre des boules, et il est chiffrable :** 6,32 bits par tirage
aujourd'hui contre **126 bits** avec l'ordre. C'est un facteur 20, et il fait basculer
chaque famille ci-dessus du côté cassable — `mtbreak` le démontre de bout en bout,
`keno_break` est l'outil prêt à l'emploi. Et §6 quinquies dit où en est la recherche de
ces tirages ordonnés : **ils ne sont pas dans les dépôts**, vérification exhaustive faite.

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
- **Un préfixe de 14/20 signalé, poursuivi, et rendu au hasard.** Le balayage des
  ouvertures de bloc a signalé `pcg32/mulhi/floyd`, graine 1 760 486 308 991, tirage
  6 300 : 14 numéros consécutifs corrects. À ce nombre d'essais (5,19·10⁹) le hasard en
  attend 0,13 — un écart de 7 contre 1, assez pour ne pas hausser les épaules. Trois
  vérifications le rendent au hasard : (1) une vraie graine donnerait **20/20**, pas 14 ;
  (2) le voisinage ±20 000 ms ne s'améliore pas, le suivant tombe à 10 puis 9, alors
  qu'un modèle presque juste progresserait ; (3) le tirage **suivant** ne dépasse pas 9
  dans la fenêtre analogue. Signalé, poursuivi, classé — avec les mesures, pas avec une
  intuition.
- **La même faute deux fois, et c'est le contrôle qui l'a dit les deux fois.** En
  ajoutant le choix de réduction, `rankxo` puis `rankw32` ont gardé une réduction
  **codée en dur** à un endroit — la ligne qui plante le rang pour l'un, la fonction de
  vérification pour l'autre. Résultat : sous mulhi, l'outil plantait avec `u mod C` et
  cherchait avec l'autre, ou l'inverse. Les deux contrôles ont échoué immédiatement et
  franchement (4/4 puis 0/4), ce qui est exactement leur travail. Le résultat de
  `rankw32` sous mulhi, obtenu avant correction, **était sans valeur et a été rejoué**.
  Un audit `grep '% CC'` sur les six outils confirme qu'il n'en reste aucun : seule la
  définition de `mkrank` y figure encore, et `lcgrank` traite les réductions comme ses
  modes, par construction.
- **Un « INVESTIGATE » qui n'en était pas un.** `rankmwc` a d'abord signalé 4 000/4 000
  positions compatibles avec un multiply-with-carry. Le signalement venait entièrement
  de la statistique choisie : tester « la retenue est-elle `< a` » n'a aucune puissance
  quand `a` frôle la base, ce qui est exactement le cas d'un MWC32. Remplacé par la
  cohérence de la retenue sur trois sorties, dont le taux sous le nul est `b⁻¹` quelle
  que soit la taille de `a` — et l'archive retombe à **0/4 000**. Un outil qui signale
  quelque chose mérite le même examen qu'un outil qui ne signale rien, sinon davantage.
- **Un bug de mémoire non initialisée dans `rankxo`, attrapé par le contrôle.**
  `build()` remplissait `D×64` lignes de matrice mais n'en remettait à zéro que `n` :
  les lignes supplémentaires contenaient ce que `malloc` avait rendu. Le symptôme est
  instructif — le premier générateur passait, les suivants échouaient, parce que la
  première allocation tombe sur des pages neuves (donc nulles) et les suivantes sur de
  la mémoire recyclée. Le diagnostic n'a pas été deviné mais mesuré : `A·s ≠ raw` sur
  27 lignes sur 192, alors que la matrice est censée reproduire l'observation exactement.
  **Les résultats de `rankxo` sur l'archive ont été rejoués après correction** — un
  résultat négatif produit par une matrice partiellement aléatoire ne vaut rien. Deux
  autres défauts sont sortis du même examen : `xoshiro512**` brouille `s[1]` et non
  `s[0]`, et les tableaux dimensionnés à 640 débordaient à 704 lignes pour un état de
  512 bits. Audit fait sur les 12 autres outils C : aucun n'a ce motif (tous en `calloc`
  ou entièrement réécrits).
- Le contrôle de `lowlcg3` échouait, et j'ai d'abord accusé un **manque de tirages** :
  une mesure partielle montrait 1 500 survivants à 18 quartets et 0 à 26, ce qui allait
  dans ce sens. En vérifiant trois survivants un par un, ils se sont révélés **réels**.
  L'outil n'était pas en cause, mon critère l'était : l'observable ne détermine la paire
  (état, incrément) qu'à une translation d'orbite près, et la translation est une
  identité algébrique exacte (§7 ter). J'ai réécrit le critère, pas l'outil — et relevé
  l'exigence de preuve de 30 à 48 quartets plutôt qu'abaisser la barre à un « presque ».
- **Un contrôle qui ne contrôlait rien, et que seul le passage à l'échelle a démasqué.**
  Le contrôle de `multibm` plantait un registre à décalage d'ordre R et prenait ses `m`
  plans aux positions de bits 3, 10, 17, 24 — commentaire à l'appui : « m fonctionnelles
  linéaires différentes ». C'est faux, et d'une façon qui se voit une fois écrite : dans
  un registre à décalage la position `p` contient `s[t−p]`, donc ces quatre plans sont
  **une seule suite lue à quatre décalages**. Or les décalés d'une suite n'engendrent rien
  de plus que son propre espace de récurrence : les quatre plans n'apportaient qu'un plan
  d'équations indépendantes. Symptôme : à `L = 42 496` le rang saturait à 28 085 ≈ `n − L`
  au lieu de `L`, et le cas `L < R` ressortait « consistent » — **par manque de rang, pas
  parce qu'une récurrence existait**. Le petit `selftest` passait quand même, et c'est le
  point : à `n = 6 000`, `L = 2 944`, un seul plan fournit déjà 3 056 lignes ≥ 2 944, donc
  la déficience ne pouvait pas s'y manifester. Il a fallu le contrôle **à la taille où la
  revendication est faite** (`n = 70 560`, `L = 48 000`, où un plan seul ne donne que
  22 560 lignes) pour qu'elle apparaisse. Corrigé en tirant chaque fonctionnelle comme la
  **parité d'un masque aléatoire sur tout l'état** — ce que sont réellement les quatre
  plans de bits de l'archive. C'est la justification la plus nette, dans tout ce dossier,
  de la règle « contrôler à l'échelle de l'énoncé » : un contrôle validé à 3 000 bits et
  invoqué à 48 000 aurait laissé passer un résultat négatif entièrement creux.

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

Identique aux indices 0, 1 et 9000, masque compris — et revérifié en fin de session aux
trois points les plus éloignés possibles : **0** (id 1309614), **35 280** (id 1344894,
milieu exact) et **70 559** (id 1380173, dernier tirage). Identifiant, horodatage, les
vingt numéros, boost et bonus concordent avec le chargeur Python à chaque fois, et le
masque de bits ressort à popcount 20.

C'est le contrôle qui compte le plus de tout le dossier : un `draws.bin` décalé d'un seul
enregistrement ferait rejeter **toutes** les hypothèses pour une raison qui n'a rien à
voir avec le générateur — un faux négatif systématique, et invisible, sur l'ensemble du
travail.


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

Et la ligne du rang (§6 quater), qui se rejoue en entier depuis `draws.bin` :

```bash
python3 rank.py           # 5 conventions de rang, formules vérifiées par énumération
python3 modbias.py        # biais de modulo : exclu à 20–86 σ, contrôle positif inclus
python3 quantize.py       # médiation par un double : exclue (multiples de 512)
python3 shufbias.py       # les 5 fautes de mélange qui auraient donné un avantage
python3 blockseed.py      # les 358 ouvertures de bloc comparées entre elles
python3 rankhash.py       # 23 520 schémas provably-fair par dérangement
gcc -O3 -march=native -o lcgrank lcgrank.c && ./lcgrank selftest && ./lcgrank real rank_colex0.bin
gcc -O3 -march=native -o rankmix rankmix.c && ./rankmix selftest && ./rankmix real rank_colex0.bin
gcc -O3 -march=native -o rankxo  rankxo.c  && ./rankxo  selftest && ./rankxo  real rank_colex0.bin 24
gcc -O3 -march=native -o ranklfg ranklfg.c && ./ranklfg selftest && ./ranklfg real rank_colex0.bin 64 3000
gcc -O3 -march=native -o rankw32 rankw32.c && ./rankw32 selftest && ./rankw32 real rank_colex0.bin 20000
gcc -O3 -march=native -o rankmwc rankmwc.c -lm && ./rankmwc selftest && ./rankmwc real rank_colex0.bin
gcc -O3 -march=native -o rankseed rankseed.c -lpthread && ./rankseed selftest
gcc -O3 -march=native -o bm bm.c && ./bm selftest && for f in bits_*.bin; do ./bm $f; done
python3 daily_reseed.py   # les 358 redémarrages quotidiens, deux modèles de sortie
python3 rankserial.py     # dépendance sérielle générique, et la tautologie à 211 σ
python3 bitchannel.py     # les deux canaux de bits, vérifiés au lieu d'être argumentés
python3 lowbit_reach.py   # jusqu'où porte vraiment la complexité linéaire
python3 twoadic.py 70560  # complexité 2-adique : toute la classe FCSR / à retenue
gcc -O3 -march=native -o rankmwc rankmwc.c -lm && ./rankmwc selftest && ./rankmwc real rank_colex0.bin
```

Et chaque outil du rang prend la **réduction** en second argument — `0` pour `u mod C`
avec rejet, `1` pour mulhi/Lemire — les deux devant être passées :

```bash
for M in 0 1; do
  ./rankmix real rank_colex0.bin $M
  ./rankmwc real rank_colex0.bin $M
  ./rankw32 real rank_colex0.bin 20000 $M
  ./ranklfg real rank_colex0.bin 64 3000 $M
  ./rankxo  real rank_colex0.bin 24 $M
done
```

Chacun de ces outils commence par son `selftest` : aucun résultat sur l'archive n'est
lu si le contrôle positif ne passe pas d'abord. C'est la règle qui a rattrapé la matrice
non initialisée de `rankxo` et le faux « INVESTIGATE » de `rankmwc`.

`seedhunt` s'auto-valide : `./seedhunt 0 0 3000000 4 -1 "0,1,0,1234567"`
plante une graine connue et la retrouve.
