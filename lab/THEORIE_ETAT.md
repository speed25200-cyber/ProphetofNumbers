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
| **la journée** | flux continu / **ré-amorçage quotidien** | **130** |

Le sixième axe a été trouvé en cherchant à dater trois vidéos : l'archive est
faite de **346 blocs de 204 tirages, 06:05 → 23:00**, séparés par des pauses de
25 500 s **exactement**. Deux tirages de journées différentes n'appartiennent
peut-être pas au même flux — et le « flux unique » du §110 enjambe une nuit.

> **Règle du modèle.** Une attaque algébrique qui rend « incompatible » ne dit
> pas *« ce n'est pas ce générateur »*. Elle dit *« ce n'est pas ce générateur
> **sous ce modèle de consommation** »*. Le modèle doit être **énuméré, pas
> supposé**.

Le coût de l'énumération est nul en puissance statistique — voir §7.

**Un axe est passé de supposé à mesuré (§137).** Sur les trois tirages filmés
portant un bonus, l'indice de celui-ci n'est constant **ni** dans l'ordre
d'émission (2, 18, 9) **ni** dans le tableau trié (10, 3, 4). L'indice est donc
**tiré**, un appel de générateur le tire, et

> le tirage consomme **vingt et un mots**, pas vingt.

Aucun résultat ne change — les balayages énuméraient déjà 20 à 22. **Et ce
point-là tient inconditionnellement** (§140).

> ⚠ **Ce que le §137 concluait en trop, et que le §140 corrige.** Il ajoutait
> *« le modèle B est donc le seul survivant »* : c'est une **omission de cas**.
> Réfuter les deux lectures à indice *constant* laisse **deux** modèles à indice
> *tiré*, selon que `j = ⌊20u⌋` indexe le tableau **trié** (B) ou l'**ordre
> d'émission** (B″). Voir 7.5.

**Et cet axe est une défense (§137).** Observer un mot sur `σ`, c'est observer un
LCG de multiplicateur `a^σ` — de réseau **fin** même quand celui de `a` est
grossier. Mesuré : les LCG `a = 5`, RANDU et glibc sont anéantis par
l'équidistribution en dimensions 2 et 3 **au pas 1** (`p = 0, 0, 5·10⁻⁵`) et
**aucun** ne tombe **au pas 21** (`p = 3·10⁻³, 2·10⁻², 6·10⁻²`).

> La plateforme n'est pas protégée parce que son générateur serait bon, mais
> parce qu'elle n'en publie qu'**un mot sur vingt et un**. C'est le 4.6 (b) vu de
> l'autre côté : la décimation détruit la structure de réseau comme elle détruit
> la complexité linéaire.

Conséquence pratique : un test spectral n'a de puissance que sur des mots
**consécutifs**, donc uniquement à l'intérieur d'un tirage **ordonné**.

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

### 2.3 bis L'angle de la roue (§131) — la porte qui semblait la plus large

Le §92 laissait ouverte la meilleure observation que le dossier pouvait espérer :
si l'angle d'arrêt de la roue était **tiré**, il publierait les bits de poids fort
du mot brut — **7,00 bits par tirage filmé** (§87). Trois arrêts mesurés :

| tirage | boost | fraction du secteur |
|---|---|---|
| 1381278 | ×1,5 | 0,4865 |
| 1381481 | ×3 | 0,4787 |
| 1381483 | ×1,5 | 0,4865 |

> Étendue **0,40° sur 51,43°**. Sous l'hypothèse de l'angle tiré,
> `P(étendue ≤ r) = n·r^(n−1) − (n−1)·r^n = 1,8·10⁻⁴`. **L'angle est constant.**

La roue est une **animation**. Elle ne publie que le multiplicateur, déjà compté
en 2.3. Il n'y a pas de cinquième observable.

### 2.3 Théorème de l'intervalle cumulé (§118) — le boost

> Une loi discrète de bornes cumulées `F(0) < … < F(k)`, échantillonnée par
> comparaison (`u` tiré, on rend `i` tel que `u ∈ [F(i−1), F(i))`), **encadre
> `u` exactement comme une troncature**. Le théorème du préfixe s'y applique
> tel quel. ∎

Les bornes étaient *estimées*, donc chaque intervalle était élargi de **4 σ** —
ce qui coûte des bits et ne peut pas en inventer. Rendement : **0,762 bit exact**
par tirage.

**Corrigé au §125 : les bornes sont exactes.** La loi du boost est portée par la
grille **1/80** — soit la taille du vivier — avec les secteurs
`(41, 19, 12, 4, 2, 2)` : χ² = 0,66 pour 5 ddl, loi entièrement spécifiée, et
toutes les grilles de 6 à 78 rejetées. L'élargissement de 4 σ disparaît :

> **1,150 bit exact par tirage au lieu de 0,762 — et démontré au lieu
> qu'estimé.**

Deux faits départagent 80 de 79, le seul autre dénominateur ≤ 100 qui ajuste, et
aucun n'est une fréquence : **80 est le modulus déjà présent dans le tirage des
numéros** ; et les **sept** valeurs filmées au §92 se ferment sur
`39 + 2 + 19 + 12 + 4 + 2 + 2 = 80`, ce qui **prédit** `E[multiplicateur] = 162/80
= 2,025` contre **2,0242 ± 0,0062** mesuré — 0,13 σ, sur une quantité non
ajustée.

*(Ce que la mesure ne donne pas : les **longueurs** des plages, oui ; leurs
**positions** dans la table, jamais.)*

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
    boost (§125, bornes exactes)    1,150 bit/tirage   utilisé
    ─────────────────────────────────────────────────────────────────
                                    4,35 équations F₂ exactes/tirage
                                    307 000 sur l'archive entière

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
| rotation variable | **1 par mot** (la parité) | PCG32 — corrigé au §123 |
| chaîne de mélange | **0** | splitmix64 |

> **Ce qui protège n'est jamais l'addition, ni la multiplication par un impair —
> c'est toujours un décalage à droite ou une rotation appliqués APRÈS elles.**

### 3.3 Le degré algébrique (§123) — le défaut porté au degré `d`

`D` est la **dérivée seconde** : elle ne teste que le degré 1. Or un bit de
degré 2 donne une équation exploitable **par linéarisation**, au prix de
`1 + W + C(W,2)` inconnues — que l'archive peut payer jusqu'à `W = 375`.

> Pour des directions `a₁..a_{d+1}` et un point `x`, la dérivée (d+1)-ième
> `T = ⊕_{S} Ψ(x ⊕ ⊕_{i∈S} a_i)` vérifie : `deg(c·Ψ) ≤ d` **ssi** `c·T = 0`
> partout, car `deg(Δ_a f) ≤ deg f − 1`. Donc **`dim L_d = W − rang(T)`**, et
> §119 est le cas `d = 1`. ∎

**Calibration.** L'arithmétique de la retenue impose, pour une sortie additive,
`dim L₁ / L₂ / L₃ = 1 / 2 / 3` **par mot** (bits 0, 1, 2). La mesure les rend
exactement.

**Mesure.** `xoshiro256++`, `xoshiro256**`, `xoroshiro128**` et `splitmix64`
rendent **0 aux trois degrés** : il n'y a rien à linéariser. `PCG32` rend
`1 / 3 / 7`, mais sa forme de degré 1 est la **parité du mot entier** — donc

- **non observable** : l'archive n'en publie que deux bits (§122) ;
- **non chaînable** : la transition est un LCG, pas une matrice sur F₂.

> Une dimension non nulle ne suffit pas. Une forme n'est exploitable que si elle
> est **observable** dans ce que la source publie **et chaînable** par la
> transition. Ces deux colonnes appartiennent au même tableau que la dimension.

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

### 4.5 Théorème de la complexité linéaire universelle (§122) — ne rien nommer

Les quatre attaques précédentes ont toutes le même défaut : elles exigent qu'on
**nomme** le générateur avant de le tester, et le §121 a recensé cinq axes de
modèle dont **trois** n'ont été trouvés qu'après coup, chacun faisant échouer
les attaques en silence.

> Soit un état dans `F₂^W` évoluant par `s ↦ A·s` (`A` quelconque), un mot
> `w = Λ·s` (`Λ` F₂-linéaire quelconque), une forme F₂-linéaire `β` du mot, et
> une consommation aux positions d'une **progression arithmétique** `c + σi`.
> Alors la suite `b_i = β(Λ·A^{c+σi}·s)` vérifie la récurrence de polynôme
> caractéristique `minpoly(A^σ)`, de degré ≤ `W` :
>
> **`L(b) ≤ W`**, et Berlekamp-Massey rend *exactement* `L`. ∎

Le membre de droite ne contient ni `A`, ni `Λ`, ni `β`, ni `σ`, ni `c` : un
seul nombre teste **toute** famille F₂-linéaire, tout pas, tout décalage, tout
nombre de mots par numéro — les axes 2, 3 et 5 du §1 disparaissent de l'énoncé.

**Corollaire du second bit (§124).** L'énoncé du ppcm que portait d'abord cette
section était **faux** : sur une suite finie, Berlekamp-Massey rend un
annulateur du *préfixe*, et le ppcm **majore** la borne conjointe au lieu de la
minorer. Ce qui est vrai :

> `χ` annule les **deux** préfixes à la fois, donc
> **`W ≥ L_conjointe = min { deg g : g annule les deux préfixes }`** —
> rigoureux pour tout `W`, sans condition sur `N`. ∎

Et le second bit n'agit pas là où on l'attend. Les suites annulées par `χ`
forment un module `F₂[x]/(χ)` ; si `χ` est **irréductible** — MT19937, les WELL,
tout polynôme primitif — ce module est **cyclique**, donc `b′ = h(x)·b` : la
seconde fonctionnelle est une combinaison de décalages de la première et
**n'apporte aucune équation neuve**.

> **Le second bit ne rehausse pas le signal : il rehausse le null.** Deux suites
> *indépendantes* ont une complexité conjointe de `2N/3` et non `N/2`, car un `g`
> de degré `d` a `d+1` coefficients pour `2(N−d)` équations.

Mesure : un état planté de 44 497 bits rend `L_conjointe = 35 283` quand le
hasard rend `47 040` — 11 757 bits d'écart, là où le test scalaire rend 35 281
contre 35 280 et **ne sépare rien**. Le calcul se fait par réduction de base sur
`F₂[x]` en forme faiblement de Popov (`tools/jointf2.c`).

**Corollaire arithmétique.** Pour `x_t = Σ a_i x_{t−i} + b (mod 2^e)`, la
réduction modulo 2 est une récurrence **affine** d'ordre `r`, homogénéisée par
`(1+x)` : `L(bit 0) ≤ r + 1`. Cela prend les LCG (`L ≤ 2`) et les Fibonacci
additifs (`L ≤ r`) **à module puissance de deux et si le mot porte le bit 0 de
l'état** — mais ni les modules premiers, ni les implantations qui ne rendent que
les bits hauts, où la retenue brise la linéarité dès le bit 1.

**Corollaire de prédiction — le seul du dossier qui prédise sans reconstituer.**
Si `L` est petit, Berlekamp-Massey rend la récurrence elle-même et tout bit
suivant se calcule à partir des `L` derniers, **sans avoir identifié la famille,
le pas ni l'échantillonneur**. L'identification n'est pas nécessaire à la
prédiction.

**Deux bits à position fixe, et pourquoi.** Le §106 comptait 3,20 bits en
moyenne — un nombre *variable*, donc inutilisable ici. Comme **4 divise 20** :
sous troncature `⌊4u⌋ = ⌊m/5⌋` sans exception (les deux bits hauts) ; sous
modulo `w mod 4 = m mod 4` (les deux bits bas).

**Limites.** Le pas doit être **constant** — le rejet échappe (4.4) ; le bit doit
être **F₂-linéaire** — les sorties brouillées échappent, mais 3.2 les ferme par
`dim L = 0`. Sous l'ordre de service renversé du cache (§112) le théorème ne
vaut que **par classe modulo 64**, et la portée tombe d'un facteur 64.

### 4.5 bis Le canal de confinement (§141) — l'attaque qui ne suppose rien

Le 4.5 et tout ce qui en découle lisent le **rang du bonus**, donc dépendent du
modèle B (voir 7.4 bis). Cette attaque-ci n'en dépend pas.

> À l'étape 0 de Fisher-Yates le tableau est **encore l'identité**, donc la valeur
> émise vaut exactement `j₀ + 1` avec `j₀ = ⌊80·u₀⌋`, et elle appartient à
> l'ensemble publié — **uniformément**, par symétrie. L'archive donne donc, pour
> chaque tirage, une **loi a posteriori complète** sur `u₀`, et
> `q = ⌊j₀/5⌋ = u₀ >> 28` en est la partie exacte.

**Budget.** `H(q) = 4`, `E[H(q|S)] = 3,487`, donc **`I = 0,513 bit par tirage`**.
Contrôle : `I(j₀;S) = log₂80 − log₂20 = 2` bits — le 2.4 par un autre chemin.
Les 70 560 tirages portent donc **36 199 bits**, et **MT19937 (19 937) est
dedans**.

**Algorithme, et il est exact.** Les quatre bits de `q` sont linéaires en l'état,
`q_i(s) = ⟨m_i, s⟩` ; en développant `log P(q|S)` sur la base de Walsh des quatre
bits, la log-vraisemblance de **tous** les `2^W` états est **une seule
transformée de Walsh-Hadamard** :

    LL(s) = Σ_m B[m]·(−1)^⟨m,s⟩        O(N·16 + W·2^W), exact.

**Témoin.** États de 16, 18, 20 et 22 bits **retrouvés et rejoués** à partir des
seuls ensembles triés, en 40 à 120 tirages contre `W/0,513 = 31` à `43`
théoriques. **4/4.** C'est la première reconstitution d'état du dossier sans
l'ordre et sans le bonus.

**La limite, et elle est algorithmique, pas informationnelle.** `2^W` bloque dès
`W = 128`. Le problème est du **LPN structuré** de biais `0,075`.

**La brèche, chiffrée et fermée (§142).** L'échappatoire est la corrélation
rapide. Un contrôle de poids `w` a un biais `δ = 2^{w−2}ε^{w−1}` et il en faut
`m* = c/δ²` par bit — la constante `c = 0,022` est **mesurée**, pas supposée, et
elle a corrigé un premier modèle **pessimiste d'un facteur 45**. Les multiples de
poids `w` et degré `< D` en fournissent `w·D^{w−2}/((w−1)!·2^W)`. En optimisant
le poids, sur les **1 552 320** bits que l'archive observe (22 par tirage, biais
0,075 à 0,026 selon le mot) :

| `W` | 64 | 128 | 256 | 512 | 1 024 | MT19937 |
|---|---|---|---|---|---|---|
| coût | `2^50` | `2^83` | `2^143` | `2^285` | **impossible** | **impossible** |
| contre | `2^64` | `2^128` | `2^256` | `2^512` | — | — |

> Elle fait tomber `2^128` à `2^83` — quarante-cinq bits gagnés sur un mur qui en
> fait encore quatre-vingt-trois — et **au-delà de 512 bits elle se referme**,
> faute de contrôles à tout poids.

Le canal de confinement et sa corrélation rapide sont donc **le meilleur qu'on
puisse tirer d'une archive triée**. L'ordre, lui, ramène tout à un pivot de
Gauss (§139).

### 4.6 Théorème du plafond universel (§134) — `T/2`, et une seule suite

Le 4.5 borne `W` par le bas ; reste à savoir **jusqu'où** cette borne peut
monter. La réponse est close, et elle est décevante de la meilleure façon : elle
interdit toute une classe de tentatives.

**(a) Décimation, validité.** Pour tout pas `d` et tout décalage `r`,
`b_{r+nd} = ℓ(A^r (A^d)^n s)` est la suite d'un générateur de matrice `A^d`, **de
même largeur `W`**. Donc `W ≥ L(b^{(d,r)})` et `W ≥ L_conjointe` des `d` résidus.

**(b) Décimation, chute.** Les racines de `χ_d` sont les `α_i^d` ; si l'ordre de
`α_i/α_j` divise `d`, deux racines fusionnent et le degré minimal chute. Pour
`χ = x³+x+1` (racines d'ordre 7), `b_{7n}` est **constante** : `L` tombe de 3
à 1. Un pas mal choisi n'affaiblit pas le signal, il l'**anéantit**.

**(c) Le plafond.** `M` suites de longueur `N`, c'est `T = M·N` bits observés au
total ; un `g` de degré `L` a `L+1` inconnues pour `T − M·L` équations, donc le
seuil aléatoire est là où `T − M·L = L+1` :

> **`plafond = T/(M+1)`.** Il est **maximal pour `M = 1`**, où il vaut `T/2`. La
> décimation en `d` résidus est le cas `M = d`, `N' = N/d`, de plafond
> `N/(d+1)` — strictement pire. ∎

**Ce que cela ferme.** Aucune façon de **découper** l'observation ne rehausse le
plafond model-free : ni un second bit (§124, cas `d=1, M=2`), ni un second pas,
ni un second observable. Le §126 en est le cas `d = 1`.

**Ce que cela dit à qui collecte.** Le plafond est **atteint**, pas dépassé, et
il est **linéaire** en la donnée : doubler l'archive double la borne. Donc

> **un tirage de plus vaut mieux qu'un bit de plus par tirage** — à bits égaux,
> `M = 1` bat `M = 2` d'un facteur `3/2`.

Vérifié 38/38, témoin positif inclus : le test **détecte** la chute du (b).
Spectre de décimation de l'archive, 12 pas de 1 à 21 : **le seuil du hasard
partout**, à une unité près.

### 4.7 Théorème de la complexité polynomiale (§135) — la fin de l'exemption

Le 4.5 se refusait aux sorties brouillées : *« le bit doit être F₂-linéaire ».*
C'était l'exemption la plus coûteuse du document — elle laissait dehors tout ce
qui a été écrit après 2014. Elle se lève en une ligne.

> Si `s_n = A^n s₀`, chaque bit de `s_n` est linéaire en `s₀` ; donc tout
> **produit** de `k` bits de `s_n` est une somme de produits de `k` bits de `s₀`.
> Le **vecteur des monômes** de degré ≤ `d` évolue donc **linéairement**, dans un
> espace de dimension `N_d(W) = Σ_{k≤d} C(W,k)`.

Un bit de sortie polynomial de degré ≤ `d` est une forme **linéaire** de ce
vecteur : on retombe sur 4.5, largeur `N_d(W)` au lieu de `W`.

> **`L(b) ≤ N_d(W)`**, sans aucune hypothèse de linéarité de la sortie. Le 4.5
> est le cas `d = 1`. ∎

**La forme maîtresse.** Avec `N_d(W) ~ W^d/d!` et le plafond `L ≤ T/2` du 4.6 :

> **`W ≥ (d! · T/2)^{1/d}`** — le pouvoir d'exclusion s'effondre comme `T^{1/d}`.

C'est le prix chiffré du refus de supposer la sortie linéaire. Pour
`T = 70 560` : `35 279` en degré 1, **266** en degré 2, **60** en degré 3,
**31** en degré 4.

**Corollaire de prédiction, et il est neuf.** Avec `2·N_d(W)` bits,
Berlekamp-Massey rend la récurrence et **prédit** — sans connaître la famille, le
brouilleur, le pas ni l'état. Témoin : une sortie **quadratique** prédite
**300/300**, là où l'attaque de degré 1 fait 145/300 sur les mêmes bits.

| `W` | `d` | tirages requis (`2·N_d`) |
|---|---|---|
| 64 | 4 | **1 358 242** — atteignable |
| 128 | 4 | 22 035 266 |
| 256 | 4 | 355 178 114 |

**Ce que cela change au 7.3.** `dim L = 0` n'est plus un mur qualitatif : c'est
une position `(W, d)` dans un plan, et le coût de l'atteindre est **chiffré et
linéaire en la donnée**.

---

### 4.8 Le critère de prédictibilité (§144) — la bonne question

Toutes les attaques ci-dessus demandent *« l'état est-il déterminé ? »*. Pour
**prédire**, ce n'est pas la bonne question. Un bit cible `b = ⟨λ, s⟩` est
prédictible **ssi `λ` appartient à l'espace des lignes du système observé** —
condition **strictement plus faible** que le rang plein.

> **La prédiction peut réussir sur un système sous-déterminé.** Noyau de
> dimension `d` : on énumère ses `2^d` états, on garde ceux qui **rejouent** les
> observations, et s'ils s'accordent tous sur la cible, la prédiction est
> **certaine** même si l'état ne l'est pas.

**Mesuré (§144).** LFSR113, rang **108 sur 128** : **32 768** états distincts
rejouent tous les tirages observés, et **tous** donnent les mêmes vingt numéros du
tirage suivant. Idem taus88 à rang 79/96, 256 états. Cinq familles sur cinq
prédites **20/20 dans l'ordre**, probabilité au hasard `10⁻³⁷`.

`lab/experiments/h123_predicteur.py` est la chaîne complète et autonome :
tirages ordonnés + indice cible → vingt numéros, ou diagnostic exact de l'échec.

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

**La carte sans le catalogue.** La ligne du §122, corrigée au §124, se lit
autrement : avec les **deux** bits à position fixe du rang, la borne de
complexité **conjointe** atteint `2N/3` bits d'état pour `N` tirages — soit
**47 040** aujourd'hui, sans qu'aucune famille figure dans l'énoncé, et cela
suffit tout juste à couvrir WELL44497b. C'est la seule ligne de cette carte dont la pente
soit de **un pour un** et qui n'ait rien à ajouter quand une famille nouvelle
paraît.

| lecture | portée mesurée sur l'archive |
|---|---|
| ~~conjointe, 4 bits — modèle §89~~ ⚠ **modèle réfuté au §129** | ~~56 448~~ |
| **conjointe, 2 bits — modèle §106, `K = 20` (§124)** ⚠ **conditionnel à B (§140)** | **`W ≥ 47 040`** *(la borne du dossier)* |
| scalaire, bit par bit (§89, §122) | `W ≥ 35 280` |
| cache renversé de V8 (§112), par classe mod 64 | `W ≥ 1 096` |
| **plafond absolu, `M → ∞`** (§126) | **`< 70 560`** |

Le nombre de bits à position fixe vaut `v₂(K)` et le seuil conjoint `M·N/(M+1)`
(§126) : la portée est donc entièrement dictée par le modulus que la plateforme
a choisi, et bornée par `N` quoi qu'il arrive.

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

### 7.2 bis Le brouilleur est affine sur `Z/2⁶⁴` (§145) — `dim L = 0` ne dit pas ce qu'on croyait

`dim L_d = 0` (7.3) est un énoncé sur **`F₂`**. Sur **`Z/2⁶⁴`**, la sortie de
xoshiro est **affine** :

> `rotl(y,7) = 128y + (y>>57)` sans bits communs, d'où pour xoshiro256\*\* et
> xoroshiro128\*\* : **`sortie = 5760·x + 9c (mod 2⁶⁴)`**, `c = (5x)>>57 ∈ [0,128)`,
> `5760 = 2⁷·45`. Vérifié 200 000/200 000. Pour xoshiro256++ :
> `2²³·(s₀+s₃) + (s₀+s₃)>>41 + s₀`.

**Et le terme `9c` ne résiste pas.** `5760·x` a ses sept bits bas nuls, donc
`sortie mod 128 = 9c mod 128` et 9 est inversible mod 128 : **`c` est déterminé**.
Puis 45 est inversible mod `2⁵⁷`. **Un mot complet détermine `x`** (20 000/20 000).

**Reconstitution.** La mise à jour étant `F₂`-linéaire, `état → (x₀..x_{n−1})` est
carrée et inversible : **4 mots pour les 256 bits de xoshiro256\*\*, 2 pour les
128 de xoroshiro128\*\***. 40/40, avec rejeu **et** prédiction de six mots
(`2⁻³⁸⁴` par hasard).

**Ce qui protège l'archive n'est donc pas le brouilleur.** L'inversion exige les
bits de **poids faible** ; Fisher-Yates publie 6,3 bits de **poids fort**. Il en
faudrait **56**.

> La plateforme est protégée par la façon dont elle **consomme** (§137, pas de 21
> mots) et **publie** (§145, 6 bits sur 64) son générateur — **pas par le
> générateur**.

### 7.3 `dim L = 0` — et ce que le §135 en fait

Pour xoshiro\*\*, xoshiro++, PCG32, splitmix64 : **aucune** fonctionnelle de la
sortie n'est linéaire en l'état, et le §123 pousse la mesure jusqu'au degré 3.
Ce n'est pas « je n'en ai pas trouvé » — c'est une dimension **calculée**.

Le 4.7 change le statut de ce mur. Il n'est plus qualitatif : une sortie de degré
`d` reste justiciable de Berlekamp-Massey, à la largeur `N_d(W)` près. Le mur
devient donc une **position dans le plan `(W, d)`**, et son franchissement a un
prix chiffré, `2·N_d(W)` tirages :

| | `W` | `d` mesuré | tirages requis | archive |
|---|---|---|---|---|
| xoroshiro64\*\* | 64 | ≥ 4 | 1 358 242 | ×19 |
| xoroshiro128\*\* | 128 | ≥ 4 | 22 035 266 | ×312 |
| xoshiro256++/\*\* | 256 | ≥ 4 | 355 178 114 | ×5 034 |

Le coût est **linéaire en la donnée** (4.6) : il n'y a pas de raccourci, mais il
n'y a pas de mur non plus — seulement une échelle.

### 7.3 bis L'enveloppe de l'archive triée (§143)

Trois attaques du 4.5 bis / 4.7 se répartissent la difficulté, et l'archive triée
a désormais une **courbe** plutôt qu'un « impossible » :

| `W` | ML exact (§141) | corrélation (§142) | branchement (§143) | **meilleur** |
|---|---|---|---|---|
| 64 | `2^64` | `2^50` | ≥ `2^54` | **`2^50`** |
| 128 | `2^128` | `2^83` | ≥ `2^97` | **`2^83`** |
| 512 | `2^512` | `2^285` | ≥ `2^360` | **`2^285`** |
| 19 937 | `2^19937` | impossible | ≥ `2^13602` | **`2^13602`** |

**Le branchement, corrigé.** Le corollaire du 2.4 comptait **vingt** choix par
mot ; au pas `k` il n'en reste que `20−k`, donc l'arbre d'un tirage vaut
`20! = 2^61,08` et non `20²⁰ = 2^86,44` — vérifié **exhaustivement** sur quatre
petits bassins, où le nombre de vecteurs `j` compatibles avec un ensemble trié
vaut exactement `tirés!`, **le même pour tous** (ce qui reprouve l'uniformité du
4.5 bis). L'exposant passe de `0,965·W` à **`0,682·W`**.

**Et c'est un minorant.** L'attaque est écrite et retrouve l'état (4/4, `W = 12`
à 18, rejeu exigé), mais elle visite `2^4,6` à `2^6,0` fois plus de nœuds que
l'arbre à la profondeur d'information : l'élagage exige une **contradiction**,
pas une sur-détermination.

### 7.4 bis La condition sous laquelle la borne du dossier tient (§140)

Toute la colonne « portée model-free » ci-dessus lit le **rang du bonus**, et
suppose que ce rang vaut `⌊20·u₂₀⌋` — c'est le **modèle B**. Le §140 montre que
ce n'est pas acquis :

> `j = ⌊20·u₂₀⌋` est **tiré** (§137), mais rien ne dit s'il indexe le tableau
> **trié** (B) ou l'**ordre d'émission** (B″). Les deux sont **indiscernables** :
> le couple `(indice d'émission, rang trié)` est uniforme sur `20×20` sous les
> deux, parce que l'ordre d'émission est une permutation uniforme du tableau
> trié.

Et l'écart n'est pas marginal. Sur **le même** générateur F₂-linéaire de 128 bits,
**les mêmes** 1 200 tirages :

| modèle | observable | `L` |
|---|---|---|
| B | bit 31 de `u₂₀`, position fixe | **128** — la borne 4.5 tient |
| B″ | rang de `ordre[j]` dans le tableau | **601** = `N/2` — la borne est **vide** |

> **Énoncé corrigé.** *Sous le modèle B, l'archive impose `W ≥ 47 040`. La
> condition n'est pas vérifiable sur les données publiées.*

**Ce qui n'en dépend pas.** Le §136 (120 systèmes sur 120 **incompatibles**), les
§132, §133 et §138 (balayages de graines), le 2.4 (confinement) et le 4.6
(plafond `T/(M+1)`, théorème sur les suites) lisent l'**ordre** ou l'ensemble
trié : ils sont **intacts**. Le dégât est circonscrit à la borne model-free — ce
qui est déjà beaucoup, car c'est le seul résultat qui ne nomme aucune famille.

**Comment trancher.** Reconstituer l'état, prédire `u₂₀`, regarder lequel des deux
modèles produit le bonus observé. C'est le programme du §139.

### 7.4 La graine

L'état de ces familles est hors de portée ; leur **graine** de 32 bits ne
l'était pas. **120 259 084 288** graines balayées (§120) plus **336 000 000**
en millisecondes (§121), **618 648 090 624** couples contre l'ordre d'émission
daté (§132) et **1 232 352 352** contre les 346 journées de l'archive (§133) :
zéro. Probabilité de faux positif `2,8·10⁻¹⁹` par graine sur l'ensemble trié,
`10⁻³⁷` sur l'ordre.

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
| tout le catalogue ≤ 807 bits | 9 | **12 — dépassé** |
| WELL1024a | 12 | **12 — atteint** |
| MT19937 par l'ordre | 223 | il en manque 211 |

Et ils **n'ont pas besoin d'être consécutifs** (§110) : sous stride constant, un
identifiant manquant est un décalage connu, pas une rupture. C'est ce qui rend
les captures d'écran utilisables : douze tirages ordonnés, pris six jours et
trois journées différentes, valent douze équations du même flux.

**Ce que le §134 ajoute, et il change la consigne de collecte.** Le plafond
model-free vaut `T/(M+1)` où `T` est le nombre **total** de bits observés et `M`
le nombre de suites en lesquelles on les découpe. Il est maximal à `M = 1`. Donc

> collecter un **observable de plus** par tirage — un second bit, le boost,
> l'angle — **abaisse** le plafond ; collecter un **tirage de plus** le relève.
> À bits égaux, `M = 1` bat `M = 2` d'un facteur `3/2`.

C'est l'inverse de ce que le dossier a fait entre le §89 et le §127, où chaque
section cherchait un observable supplémentaire. La bonne consigne est la plus
ennuyeuse : **le même bit, plus longtemps**.

**Et la consigne qui reste la meilleure**, elle, n'est pas model-free : **des
tirages ordonnés**. Un tirage ordonné vaut **≈ 90 équations** (§110 : 807 → 897
en passant de 9 à 10 tirages) ; un tirage trié en vaut **zéro**, parce qu'il
faudrait brancher sur vingt valeurs par mot pour en extraire une.

**Le flux en direct (§139).** Si la plateforme pousse les boules une par une,
l'ordre d'arrivée des messages **est** l'ordre d'émission, et le rendement passe
de « une vidéo filmée à la main » à **204 tirages ordonnés par jour**, soit
18 360 équations par jour :

| cible | bits | tirages ordonnés | capture |
|---|---|---|---|
| WELL512a | 512 | 6 | 20 min |
| WELL1024a | 1 024 | 12 | 35 min |
| **MT19937** | 19 937 | 222 | **1,1 jour** |
| **WELL44497b** | 44 497 | 494 | **2,4 jours** |

Deux jours et demi ferment le catalogue F₂-linéaire en entier. `tools/
signalr_capture.py` fait la capture et le décodage, sans dépendance, témoin 14/14
sur deux schémas.

**Et l'ordre renverse la hiérarchie des voies.** Un tirage ordonné donne aussi
**22 bits exacts à position fixe** (théorème I du §126, `v₂(K)` pour
`K = 80…61`), contre 2 pour le seul rang du bonus — mais par le plafond du 4.6
cela ne donne que `22n/23 ≈ 0,96·n` au lieu de `n/2`, donc **228 jours** pour
WELL44497b contre 2,4 par la voie algébrique.

> Tant qu'on n'a que l'ensemble trié, la voie model-free est la seule. Dès qu'on
> a l'ordre, elle est **cent fois** la plus lente.
