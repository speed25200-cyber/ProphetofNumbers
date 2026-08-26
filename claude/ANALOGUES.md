# Reconstruction d'état par analogues

Dixième vecteur d'attaque sur le flux Loto Express, et le premier
**non paramétrique**. Note de méthode et résultat.

---

## 1. Ce qui manquait aux neuf vecteurs précédents

| # | Vecteur | Ce qu'il postule |
|---|---|---|
| 1 | Balayage exhaustif ≤ 2³² | l'algorithme est dans {glibc, MSVC, xorshift32, …} |
| 2 | Dérivation de graine (horloge, n° de tirage) | idem + la graine est devinable |
| 3 | Ré-amorçage par session | idem + le motif de ré-amorçage |
| 4 | Graines pratiques 48 bits | l'algorithme est java.util.Random ou un LCG mod 2⁴⁸ |
| 5 | Berlekamp-Massey | le générateur est **F₂-linéaire** |
| 6 | Algébrique (Hensel, réseaux) | l'algorithme est un LCG |
| 7 | Anti-rejeu | une graine a été réutilisée à l'identique |
| 8 | Batterie statistique | la faiblesse se voit sur les marginales |
| 9 | Noyau C 48 bits | idem 4, à plus grande échelle |

Tous rendent zéro. Mais tous ont le même angle mort : **chacun nomme une
famille d'algorithme**, ou une structure (la F₂-linéarité pour
Berlekamp-Massey). Un générateur hors des familles postulées y échappe
par construction, quelle que soit sa faiblesse par ailleurs.

Et aucun n'a jamais mesuré sa propre puissance. Un résultat nul dont on
ignore la sensibilité n'est pas un résultat : c'est une absence
d'information.

## 2. La méthode

Soit `S_t` l'état interne, `g` la transition, `f` la sortie :

```
S_{t+1} = g(S_t)        tirage_t = f(S_t)
```

On ne cherche à connaître **ni `g` ni `f`**. Il suffit que `g` soit
déterministe. Alors, trivialement :

```
S_i = S_j   =>   tirage_{i+k} = tirage_{j+k}   pour tout k
```

Le recouvrement entre deux tirages est donc un **proxy observable de la
proximité d'états**. D'où le test : chercher dans tout le passé le
meilleur analogue du dernier tirage, et jouer **son successeur**.

C'est la méthode des analogues de Lorenz (1969), conçue pour prédire un
système dynamique déterministe sans en connaître les équations. Elle n'a,
à ma connaissance, jamais été appliquée à un flux de générateur.

Sous H₀ (tirages indépendants), le score vaut exactement 5,000 quel que
soit l'analogue retenu — le choix de `j` ne porte aucune information sur
`tirage_t`.

Deux volets :

- **T1** — histogramme conjoint de `(O(i,j), O(i+1,j+1))` sur toutes les
  paires. La pente porte toute l'information de propagation.
- **T2** — prédicteur par analogue en avant glissant, contexte de 1 à 3
  tirages, k = 1 et k = 20 plus proches voisins.

## 3. Enveloppe de puissance — mesurée, pas supposée

Modèle générique d'un générateur inconnu de `n` bits :

```
s <- H(s) mod 2^n        (H = SHA-256 tronqué)
```

Toute application déterministe de `n` bits vers `n` bits se comporte, en
distribution, comme une fonction aléatoire. Mesurer la puissance
là-dessus, c'est la mesurer **pour toute famille d'algorithme à `n` bits
d'état — y compris celles que personne n'a écrites**.

Prédiction : un flux continu consomme ≈ 23 sorties brutes par tirage,
soit `R = 23m`. Une fonction aléatoire sur 2ⁿ états revisite un état
après ≈ `sqrt(π/2 · 2ⁿ)` pas. Le test voit donc le générateur dès que

```
n <= 2·log2(R) − 0,65
```

### Mesure à m = 70 560 (la taille réelle de l'échantillon)

| Source | Sorties brutes | Score | z | Verdict |
|---|---:|---:|---:|---|
| fonction aléatoire 36 bits | 1 612 072 | 17,68 | +601,3 | **détecté** |
| fonction aléatoire 38 bits | 1 612 324 | 16,74 | +488,1 | **détecté** |
| fonction aléatoire 40 bits | 1 612 561 | 11,76 | +231,1 | **détecté** |
| fonction aléatoire 41 bits | 1 610 782 | 5,00 | −0,5 | invisible |
| fonction aléatoire 42 bits | 1 612 351 | 5,01 | +0,8 | invisible |
| fonction aléatoire 44 bits | 1 611 792 | 5,01 | +1,1 | invisible |

Seuil théorique : **40,4 bits**. Falaise mesurée : entre 40 et 41.
L'accord est exact.

### Témoins

| Source | Score | z | Attendu |
|---|---:|---:|---|
| LCG 48 bits (bits hauts) | 5,019 | +1,6 | invisible ✓ |
| splitmix64 (avalanche pleine) | 4,988 | −1,0 | invisible ✓ |
| SHA-256 en compteur | 4,998 | −0,2 | invisible ✓ |
| SRS idéal | 5,004 | +0,3 | invisible ✓ |

Le test ne produit pas de faux positif, et il s'éteint proprement au-delà
de sa portée. C'est ce qui rend son résultat nul interprétable.

**Le gain, en régime de flux continu : 40 bits contre 32 pour le
balayage exhaustif — 256 fois plus d'espace d'états — et sans nommer un
seul algorithme.** Le § 5 précise ce qu'il en est en régime ré-amorcé,
où la borne est différente et plus basse.

## 4. Résultat sur les 70 560 tirages réels

### T1 — propagation sur 4 978 431 364 paires

```
corrélation  rho(O(i,j), O(i+1,j+1)) = -0,000009
pente        dE[O(i+1,j+1)]/dO(i,j)  = -0,000009
```

Moyenne conditionnelle `E[O(i+1,j+1) | O(i,j) = k]` :

| k | paires | E[succ] |
|---:|---:|---:|
| 2 | 247 505 880 | 4,9999 |
| 3 | 621 650 292 | 5,0000 |
| 4 | 1 020 721 348 | 5,0000 |
| 5 | 1 161 389 703 | 5,0000 |
| 6 | 946 759 919 | 4,9999 |
| 7 | 563 983 490 | 5,0000 |
| 8 | 248 263 299 | 5,0002 |
| 9 | 81 047 927 | 4,9993 |
| 10 | 19 622 176 | 4,9999 |
| 11 | 3 492 582 | 4,9997 |
| 12 | 453 551 | 5,0038 |
| 13 | 42 319 | 4,9977 |
| 14 | 2 744 | 5,0911 |
| 15 | 130 | 5,0769 |

La colonne est plate sur quatre décimales, de k = 2 à k = 13. Les deux
dernières lignes (k = 14, 15) ont respectivement 2 744 et 130 paires :
leur écart-type d'échantillonnage vaut 1,688/√n, soit 0,032 et 0,148 —
les écarts observés (+0,09 et +0,08) sont à +2,8 σ et +0,5 σ, et sur
14 cases testées le premier n'est pas significatif.

### T2 — prédicteur par analogue, en avant glissant

| Contexte | k | n | Score | H₀ | z | p |
|---|---:|---:|---:|---:|---:|---:|
| 1 tirage | 1 | 68 560 | 5,0031 | 5,000 | +0,48 | 0,63 |
| 1 tirage | 20 | 68 560 | 4,9985 | 5,000 | −0,23 | 0,82 |
| 2 tirages | 1 | 68 560 | 4,9927 | 5,000 | −1,14 | 0,26 |
| 2 tirages | 20 | 68 560 | 5,0025 | 5,000 | +0,39 | 0,69 |
| 3 tirages | 1 | 68 560 | 4,9938 | 5,000 | −0,96 | 0,34 |
| 3 tirages | 20 | 68 560 | 5,0013 | 5,000 | +0,20 | 0,84 |

Six configurations, aucune au-delà de 1,2 σ, et le signe alterne.

### Calibration : deux répliques nulles à taille réelle

Les paires ne sont pas indépendantes — chaque tirage entre dans 70 559
d'entre elles — donc l'écart-type de rho ne peut pas se calculer
analytiquement. Il faut le simuler : deux flux SRS synthétiques de
70 560 tirages, passés dans exactement la même chaîne.

| Flux | rho | queue O≥12 | T2, pire des 6 configurations |
|---|---:|---:|---:|
| **Réel** | **−0,000009** | **5,0038** | **−1,14 σ** |
| Nul, graine 1 | +0,000025 | 4,9971 | +1,15 σ |
| Nul, graine 2 | −0,000003 | 4,9973 | **+2,33 σ** |

Trois lectures :

1. Le rho réel (−0,9 × 10⁻⁵) tombe **strictement entre** les deux nuls
   (+2,5 × 10⁻⁵ et −0,3 × 10⁻⁵). Deux répliques ne donnent pas un
   écart-type fiable, donc je ne cite pas de p-valeur ici — mais
   l'encadrement suffit à écarter toute lecture d'anomalie.
2. Sur la queue `O ≥ 12` (498 748 paires), l'écart-type
   d'échantillonnage vaut 1,688/√n = 0,0024. Le réel est à +1,6 σ, les
   deux nuls à −1,2 σ. Rien de significatif, et l'ordre de grandeur des
   trois écarts est le même.
3. La réplique nulle 2 produit une configuration à **+2,33 σ**
   (p = 0,02) — plus bruyante que tout ce qu'on observe sur les données
   réelles, dont le maximum est 1,14 σ. Autrement dit **le flux réel est
   plus calme qu'un vrai tirage aléatoire ne l'est en moyenne**. C'est le
   rappel utile : sur six configurations, un z de 2,3 arrive par hasard
   environ une fois sur huit. Un écart isolé de cette taille, sur les
   données réelles, n'aurait rien voulu dire non plus.

## 5. Ce que cela exclut, et ce que cela n'exclut pas

La borne dépend du **régime d'amorçage**, et il faut les distinguer —
les confondre reviendrait à surestimer la portée.

**Régime « flux continu »** (un seul état itéré à travers tous les
tirages, ≈ 23 sorties brutes consommées par tirage). C'est le régime
mesuré au § 3. Exclu : tout générateur déterministe d'état effectif
≤ **40 bits**, **quelle que soit sa famille** — y compris non linéaire, y
compris inconnue, y compris jamais publiée. La détection passe par le
revisit de cycle, qui survient après ≈ `sqrt(π/2 · 2ⁿ)` pas.

**Régime « ré-amorcé à chaque tirage »**. Ici il n'y a pas de cycle à
revisiter : la détection passe par une collision de graines entre deux
tirages. Avec `m = 70 560` tirages et zéro collision observée, le
paradoxe des anniversaires donne, à 95 % :

```
exp(−m²/2N) < 0,05   =>   N > m²/6 = 8,30 × 10⁸ = 2^29,6
```

Soit **29,6 bits** — nettement moins que les 40 du flux continu, et moins
que les 32 bits du balayage exhaustif. Mais cette borne-ci ne suppose
aucun algorithme, là où les 32 bits n'étaient valables que pour huit
familles nommées. Elle recoupe le vecteur anti-rejeu, qui avait déjà
établi l'absence de tirage répété à l'identique sur 2,489 milliards de
paires.

**Non exclu** : en flux continu, un état ≥ 41 bits avec avalanche
correcte ; en ré-amorçage, une graine de ≥ 30 bits. Le test s'éteint là,
et il le dit. Un AES-CTR, un SHA-DRBG ou un Quantis y sont
par construction hors d'atteinte — non par difficulté calculatoire, mais
parce qu'il n'y a alors **rien dans les sorties** à reconstruire.

C'est un résultat négatif, et un résultat négatif quantifié est un
résultat. La différence avec les neuf vecteurs précédents n'est pas qu'il
trouve quelque chose : c'est qu'il dit exactement ce qu'il aurait trouvé.

## 6. Mise en production

Le test est branché dans `Prophet/Services/Forensics.swift` comme
huitième test de la batterie, sous le nom **« Reconstruction par
analogues »**. Sur la fenêtre de l'app (399 tirages) sa portée tombe à
≈ 25 bits — suffisant pour voir en direct un basculement de la source
vers un générateur dégradé, ce qu'aucun des sept autres tests ne
couvrirait.

Deux témoins déterministes en intégration continue :

- un état de 12 bits **doit** être vu — z = +22,9 ;
- xorshift64 **ne doit pas** l'être — z = −0,09.

Sans le témoin positif, un test qui ne déclenche jamais est
indistinguable d'un test cassé.

---

*Scripts : `analogue.py` (T1/T2), `power.py` et `power_full.py`
(enveloppe de puissance).*
