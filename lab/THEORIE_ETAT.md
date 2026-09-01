# Théorie de la reconstitution d'état et de la prédiction
### pour une loterie publiant des tirages triés

*Document autonome. Chaque énoncé renvoie à la section du `RAPPORT.md` qui le
mesure. Rien ici n'est supposé : ce qui n'est pas démontré est mesuré, ce qui
n'est ni l'un ni l'autre est signalé comme limite.*

> **Ce document est distinct de `THEORIE.md`**, qui développe les théorèmes A à
> O — la mathématique de la **mise** : loi jointe de deux grilles, étalement,
> regret de l'essaim, frontière de détection, loi de la cagnotte. Celui-ci
> traite du **générateur** : reconstituer son état, et prédire.
>
> Les deux ne se recouvrent pas et ne se contredisent pas. Le premier dit
> comment jouer si l'on ne sait rien ; le second, ce qu'il faudrait savoir pour
> ne plus avoir à jouer.

---

## 0. Le problème, posé

Une plateforme tire vingt numéros sur quatre-vingts, plus un « bonus » et un
multiplicateur de « boost ». Elle publie, pour chaque tirage :

- l'**ensemble trié** des vingt numéros — l'ordre d'émission est perdu ;
- le **bonus**, qui est toujours l'un des vingt (70 560 / 70 560, §106) ;
- le **boost**, valeur dans {1, 2, 3, 4, 5, 10} ;
- l'**identifiant** du tirage et son **horodatage** à la seconde.

**Question.** Peut-on reconstituer l'état interne du générateur, et prédire les
tirages futurs ?

La théorie qui suit répond en trois temps : ce que les observations
**contiennent**, ce qu'on peut en **extraire**, et ce que l'extraction
**coûte**.

---

## 1. Le modèle de consommation

Un générateur produit une suite de mots `w₀, w₁, w₂, …`. Un échantillonneur les
transforme en numéros. **Cinq axes** décrivent cette transformation, et chacun
a été trouvé — trois d'entre eux *après coup*, parce qu'un axe mal deviné fait
échouer une attaque **sans bruit** :

| axe | valeurs | § |
|---|---|---|
| **échantillonneur** | modulo `w mod K` / troncature `⌊u·K⌋` | 94, 105 |
| **pas** | fixe (Fisher-Yates) / variable (rejet) | 95, 111 |
| **consommation** | un / deux mots par numéro | 113 |
| **ordre de service** | direct / cache renversé | 112 |
| **décalage** | 0 à `stride−1` | 115 |

> **Règle du modèle.** Une attaque algébrique qui rend « incompatible » ne dit
> pas *« ce n'est pas ce générateur »*. Elle dit *« ce n'est pas ce générateur
> **sous ce modèle de consommation** »*. Le modèle doit être **énuméré, pas
> supposé**.

Le coût de l'énumération est nul en puissance statistique — voir §7.

---

## 2. Les observables, et ce qu'elles publient

### 2.1 Théorème du contenu (§94) — l'échantillonneur modulo

Comme `16 | 80`, sous un échantillonneur modulo le numéro publié donne
exactement les **quatre bits bas** du mot :

    (n − 1) mod 16 = w mod 16

### 2.2 Théorème du préfixe (§105) — l'échantillonneur par troncature

> Soit un mot de `W` bits, `u = w/2^W`, et l'observation `m = ⌊u·K⌋`. Les `j`
> premiers bits de `u` sont déterminés **si et seulement si**
>
>     ⌊m·2ʲ / K⌋ = ⌊((m+1)·2ʲ − 1) / K⌋
>
> et la valeur commune **est** le préfixe. ∎

L'intervalle a pour largeur `1/K` ; il tient dans une cellule dyadique de
niveau `j` avec probabilité `1 − 2ʲ/K`. D'où l'espérance `Σⱼ max(0, 1 − 2ʲ/K)` :

| observable | `K` | bits F₂ **exacts** |
|---|---|---|
| numéro sous Fisher-Yates | 80…61 | **4,48** |
| numéro sous rejet | 80 | **5,20** |
| rang du bonus | 20 | **3,20** |
| bits bas sous modulo (§94) | — | 4,00 |

### 2.3 Théorème de l'intervalle cumulé (§118) — le boost

> Une loi discrète de bornes cumulées `F(0) < … < F(k)`, échantillonnée par
> comparaison (`u` tiré, on rend `i` tel que `u ∈ [F(i−1), F(i))`), **encadre
> `u` exactement comme une troncature**. Le théorème du préfixe s'y applique
> tel quel. ∎

Les bornes étant *estimées*, chaque intervalle est élargi de **4 σ** — ce qui
coûte des bits et ne peut pas en inventer. Rendement mesuré : **0,762 bit
exact** par tirage.

### 2.4 Théorème du confinement (§110) — l'ensemble trié

> Sous Fisher-Yates, au pas `k`, la valeur émise vaut `jₖ + 1` sauf si `jₖ` a
> déjà été échangé, ce qui arrive avec probabilité au plus `k/80`. Si `S` est
> l'**ensemble** non ordonné, `P(jₖ + 1 ∈ S) ≥ 1 − k/80`, et au pas 0
> l'inclusion est **exacte**. ∎

Chaque mot est donc confiné à 20 intervalles sur 80 : **2 bits** sans connaître
l'ordre — soit **2,8 millions de bits** sur l'archive. Cette information est
pourtant **inutilisable**, et le §7 dit pourquoi.

### 2.5 Le budget total de l'archive

    ensemble trié des 20 numéros   61,6 bits/tirage   INUTILISABLE (§7)
    rang du bonus                   3,20 bits/tirage   utilisé
    boost                           0,762 bit/tirage   utilisé
    ─────────────────────────────────────────────────────────────────
                                    3,96 équations F₂ exactes/tirage
                                    279 000 sur l'archive entière

**Il n'y a pas de quatrième champ.**

---

## 3. Quelle part de la sortie est linéaire

C'est la question qui décide si l'algèbre linéaire mord. Elle se **calcule**.

### 3.1 Théorème du bit zéro, forme additive (§117)

> Si `A` et `B` sont F₂-linéaires en l'état, alors
> `bit₀(A + B) = bit₀(A) ⊕ bit₀(B)` : l'addition propage les retenues vers le
> **haut**, et rien n'entre dans le bit 0. ∎

*(Le §100 en donne la forme à constante additive : pour
`sᵢ = Σ aⱼ sᵢ₋ⱼ + c (mod 2ᵏ)`, le bit 0 suit une récurrence F₂-affine de même
ordre.)*

### 3.2 Théorème du défaut de linéarité (§119)

> Soit `Ψ : F₂ⁿ → F₂^W` l'application « état → sortie ». Posons
>
>     D(x, y) = Ψ(x ⊕ y) ⊕ Ψ(x) ⊕ Ψ(y) ⊕ Ψ(0)
>
> Alors `c` est une forme F₂-linéaire de l'état **ssi** `c·D(x,y) = 0` pour tous
> `x, y`. Donc **L = vect{D}^⊥** et **dim L = W − rang(D)**. ∎

On ne cherche plus une forme linéaire au jugé : on calcule la **dimension de
l'espace de toutes celles qui existent**. Mesure sur onze familles :

| sortie | dim L | familles |
|---|---|---|
| brute | **tous les bits** | xorshift\*, xoshiro brut, **V8 `Math.random`** |
| additive | **1 par mot** (le bit 0) | **xorshift128+**, xoroshiro128+, xoshiro256+ |
| addition + **rotation** | **0** | xoshiro256++ |
| multiplication + rotation | **0** | xoshiro256\*\*, xoroshiro128\*\* |
| rotation variable | **0** | PCG32 |
| chaîne de mélange | **0** | splitmix64 |

> **Ce qui protège n'est jamais l'addition, ni la multiplication par un impair —
> c'est toujours un décalage à droite ou une rotation appliqués APRÈS elles.**

---

## 4. Les attaques

### 4.1 Élimination F₂ — quand `dim L > 0`

Les formes linéaires du mot `k` se calculent en propageant l'état sur les
vecteurs unitaires (légitime tant que la transition est F₂-linéaire ; pour une
sortie additive, légitime **pour le bit 0 seul**). Chaque observation donne ses
bits de préfixe comme équations. On échelonne, on parcourt le noyau, **on
rejoue**.

> **Le rejeu n'est pas facultatif.** Les équations ne portent que sur les bits
> de préfixe ; une direction du noyau peut les laisser intactes et changer le
> numéro. Sans rejeu, le §111 avait consigné **15 104 « états compatibles »**
> dont aucun ne reproduisait le tirage.

### 4.2 Théorème de la fenêtre (§103) — sans graine ni état

> Si `s_t = a·s_{t−p} + g·s_{t−q} + b (mod M)` et que la sortie est tronquée,
> alors `θ = b/M` appartient à un **arc** calculable, le même pour tout `t`.
> **Le module et la constante disparaissent de l'énoncé.** ∎

Portée : `‖λ‖₁ ≪ K`. Couvre les Fibonacci retardés, AWC, SWB — à **n'importe
quel module**. Ne couvre **pas** les LCG (`‖λ‖₁ = 1 + a`), et aucune relation
plus longue n'y aide : le plus court vecteur du réseau des relations vaut
≈ 90 pour `M = 2⁴⁸`.

### 4.3 Réduction de réseau (§104) — les LCG

Paramètres fixés, état cherché : `s_t = aᵗ s₀ + c_t (mod M)`, encadré à `M/K_t`
près. Une inconnue, `log₂ M / 6,3` contraintes suffisent — **un seul tirage**
jusqu'à `2⁶⁴`. LLL puis plan le plus proche de Babai, **en arithmétique entière
exacte** : une base flottante fait dériver le réseau, et l'échec est silencieux.

### 4.4 Arbre de rejet (§111) — le pas variable

> L'ordre étant connu, on ne branche que sur les **rejets** : `C(20+r, r)`
> motifs, et l'incompatibilité n'apparaît qu'après `n/5,20` numéros. L'arbre
> avant élagage compte `C(n/5,20 + r, r)` nœuds. ∎

---

## 5. Le théorème de prédiction

> **Un générateur déterministe identifié prédit exactement tous les tirages
> futurs.** « Peut-on prédire ? » se réduit *entièrement* à « peut-on
> identifier ? », et l'horizon est **infini**.

Et le corollaire qui surprend (§116) :

> Le rang du bonus ne publie que **3,20 bits** par tirage — un vingtième des
> 61,6 bits de l'ensemble. On pourrait croire la prédiction partielle. **Elle
> ne l'est pas** : une fois l'état identifié, tout est déterminé — les vingt
> numéros, leur **ordre d'émission jamais observé**, le bonus, et la suite.
>
>     observation : 3,20 bits/tirage
>     prédiction  : 61,6 bits/tirage, PLUS l'ordre, à horizon infini
>
> L'information de l'**observation** ne borne pas celle de la **prédiction** ;
> elle ne borne que le **nombre de tirages à observer**. ∎

**Vérifié de bout en bout** : ensembles triés → rangs du bonus → équations F₂ →
état → ordre d'émission et tirages futurs. **11 familles sur 12** annoncent le
tirage suivant exactement, MT19937 compris (19 937 bits, 6 430 tirages triés).

---

## 6. La carte de portée

Avec `3,96` équations par tirage trié, un état de `n` bits demande `n/3,96`
tirages — et l'archive en compte 70 560.

| état | tirages requis | l'archive suffit ? |
|---|---|---|
| 128 (xorshift128, V8) | 33 | oui |
| 512 (WELL512a) | 130 | oui |
| **19 937 (MT19937)** | **5 035** | **oui** |
| ~279 000 | 70 560 | limite |

**La donnée n'est pas le facteur limitant.** Ce qui limite est le coût de
calcul des formes linéaires — et il tombe avec un solveur en C (`tools/f2solve.c`,
25 908 équations de 19 937 bits en 57 s).

---

## 7. Les bornes — ce qui est démontré impossible

### 7.1 Corollaire de branchement (§110) — l'ensemble trié

> Le confinement ne détermine **aucun** bit : une réunion de 20 intervalles sur
> 80 n'est jamais contenue dans une moitié dyadique (probabilité `7,8·10⁻⁸`).
> Il faut donc **brancher** — `log₂ 20 = 4,32` bits — pour `4,48` bits
> d'équations, soit `+0,16` par mot. Mais **aucun branchement n'est élagable
> tant que le système est sous-déterminé** : l'arbre atteint `20^(n/4,48)`
> nœuds **avant** de se contracter. ∎

| état | nœuds |
|---|---|
| 128 | **2¹²³** |
| 256 | 2²⁴⁷ |

Les 2,8 millions de bits de l'ensemble trié sont donc réels et hors d'atteinte
**par manque de levier, pas de bits**.

> **Le levier, c'est l'ordre.** Il change 4,32 bits de branchement en 4,48 bits
> d'équations **gratuites**. Un tirage ordonné ne vaut pas 89,7 bits de plus
> qu'un tirage trié : il vaut la différence entre **2¹²³ nœuds et un pivot de
> Gauss**.

### 7.2 Trois régimes, trois coûts

    ordre connu, pas connu     →  pivot de Gauss
    ordre connu, pas inconnu   →  arbre combinatoire, C(n/5,2 + r, r)
    ordre inconnu              →  arbre exponentiel, 20^(n/4,48)

### 7.3 `dim L = 0`

Pour xoshiro\*\*, xoshiro++, PCG32, splitmix64 : **aucune** fonctionnelle de la
sortie n'est linéaire en l'état. Ce n'est pas « je n'en ai pas trouvé » — c'est
une dimension **calculée**.

### 7.4 La graine

L'état de ces familles est hors de portée ; leur **graine** de 32 bits ne
l'était pas. **120 259 084 288** graines balayées (§120) plus **336 000 000**
en millisecondes (§121) : zéro. Probabilité de faux positif `2,8·10⁻¹⁹` par
graine.

---

## 8. Application à ce dossier

Toutes les attaques ci-dessus fonctionnent — chacune avec un **témoin positif**
sur générateur planté. Appliquées à l'archive réelle, elles rendent **zéro état
compatible sur ~11 000 systèmes**, et la plupart des systèmes sont
**incohérents** : pas « aucune solution trouvée », mais **« aucun état ne peut
produire ces données »**.

Sont donc **exclus, avec témoin** : tous les F₂-linéaires jusqu'à 19 937 bits
(MT19937 compris), le `Math.random` de V8, les LCG publiés jusqu'à 2⁶⁴, les
récurrences à trois termes à tout module, MWC1616, et les sorties additives par
leur bit zéro (xorshift128+ de Firefox et Safari).

**Ce qui subsiste** — et c'est démontrable, pas conjectural :

- une graine de **plus de 32 bits** ou tirée d'un CSPRNG ;
- un **état brouillé jamais réamorcé** (`dim L = 0`) ;
- le **matériel**.

Ces trois hypothèses sont **indistinguables des données publiées**. Ce n'est pas
un échec de recherche : c'est un résultat, et il a la forme d'une borne.

---

## 9. Ce qu'il faudrait collecter

Une seule donnée changerait la conclusion, et l'archive ne la contient pas :
**des tirages ordonnés**.

| cible | tirages ordonnés requis | disponibles |
|---|---|---|
| tout le catalogue ≤ 807 bits | 9 | **9 — déjà fait** |
| WELL1024a | 12 | il en manque **3** |
| MT19937 par l'ordre | 223 | il en manque 214 |

Et ils **n'ont pas besoin d'être consécutifs** (§110) : sous stride constant, un
identifiant manquant est un décalage connu, pas une rupture. Trois captures
d'écran de plus, prises n'importe quand, ouvrent la marche suivante.
