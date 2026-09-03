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
| Reconstruction d'état à partir des tirages **ordonnés** | **CASSAGE COMPLET démontré** — voir §5 |

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
| **hash** | 390 schémas « provably fair » (6 hashs × 13 entrées publiques × 5 dérivations) | chance pure (max 11/20) | ~10/20 |
| **seed** | Balayage 2³² × 234 combinaisons (16 familles PRNG × 4 mappings × 4 échantillonneurs, + .NET, V8, Python `random.sample`, PHP `mt_rand`) | meilleur 15/20 = exactement le bruit attendu (4,0 attendus) | — |

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

## 9. Reproduire

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
gcc -O3 -o pairs pairs.c -lpthread -lm && ./pairs             # 2,49 G de paires
gcc -O3 -o seedhunt seedhunt.c -lpthread && ./seedhunt 0 0 4294967296 4
gcc -O3 -o seedhunt2 seedhunt2.c -lpthread && ./seedhunt2 0 0 100000000
gcc -O3 -o mtbreak mtbreak.c && ./mtbreak 400 0xC0FFEE42 0    # cassage complet
```

`seedhunt` s'auto-valide : `./seedhunt 0 0 3000000 4 -1 "0,1,0,1234567"`
plante une graine connue et la retrouve.
