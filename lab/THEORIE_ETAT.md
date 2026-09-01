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

**Limites.** Le pas doit être **constant** — le rejet échappe (4.4), mais pas au
crible des quotients du 7.6, qui en fait son meilleur cas ; le bit doit
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

### 7.5 L'espace des designs, et non le catalogue (§146, §147)

Le §25 avait nommé le trou : *« il fallait **énumérer des constantes publiées** ;
un générateur aux constantes maison lui échappait entièrement »*. Fermé pour les
LCG, il est resté ouvert pour les `F₂`-linéaires jusqu'ici.

`tools/sweep_design.c` balaie l'**espace des paramètres**, pas la liste :

| forme | `W` | espace | designs |
|---|---|---|---|
| Marsaglia `x ^= x<<\|>>a,b,c` | 32 / 64 / 128 | tous décalages × 8 orientations | 2 476 · 10³ |
| xoroshiro128 brut | 128 | toutes rotations, tout mot lu | 500 094 |
| xoshiro256 brut | 256 | toutes rotations, tout mot lu | 31 752 |

**8 994 882 designs testés, zéro compatible.** Témoin 10/10 : design planté
retrouvé, design différant d'**un** paramètre rejeté ; les constantes publiées
sont dans l'espace et en sont rejetées.

**Deux points de méthode qui ont rendu cela possible ou faillible :**

- **Ré-originage.** L'état au début du premier tirage observé est aussi inconnu
  que celui du début de la journée : la profondeur de flux tombe de 1 806 mots à
  63, facteur 28.
- **Porte de puissance (§147).** Une exclusion n'a de sens que là où le système
  est **sur-déterminé**. La première version l'a omise et a rendu 23 288 faux
  « survivants » — 185 équations pour 256 inconnues. Le 4.8 l'avait pourtant
  mesuré : *le point de contradiction vaut la largeur de l'état*.

> Ce n'est plus « aucune famille publiée ne convient » mais **« aucun générateur
> de ces cinq formes ne convient, quels que soient ses paramètres »**.

---

### 7.6 Théorème des quotients (§149, §152) — exclure `2^W` états en n'en criblant que `2^m`

Le 7.5 exclut par **énumération** : `2^32` états par design, jamais `2^48` ni
`2^64`. Le §149 exclut pourtant les `2^48` états de `java.util.Random` en n'en
regardant que `2^21`, et le §152 les `2^64` de `musl`, `newlib` et MMIX en n'en
regardant que `2^37` — ou **seize**. Voici pourquoi cela marche, et pour qui.

**Le quotient.** Soit `f` la transition sur l'espace d'état `S`, `|S| = 2^W`.
Une partition `Q` de `S` est **invariante** si `f` envoie chaque bloc dans un
bloc : `f` passe au quotient, et le générateur est **autonome sur `Q`** — on
peut faire tourner `f̄` sur `Q` sans connaître le reste de l'état.

> **Théorème Q (quotients d'un cycle).** *Si `f` est un cycle unique de
> longueur `L` sur `S`, les partitions invariantes sont exactement les
> **phases modulo `d`** pour `d | L` : le bloc de `s₀` est `{f^{jd}(s₀)}`, les
> autres ses translatés.*
>
> *Preuve.* Soit `B` le bloc de `s₀` et `D = {k : f^k(s₀) ∈ B}`. Si `k ∈ D`,
> `f^k` envoie `B` dans un bloc, qui contient `f^k(s₀) ∈ B` : c'est `B`. Donc
> `k, k′ ∈ D ⇒ f^{k+k′}(s₀) ∈ f^k(B) ⊆ B`, et `D` est un sous-semi-groupe de
> `Z/L` contenant `0`, donc un sous-groupe `dZ/L`. ∎

> **Corollaire (le crible).** *Un crible de coût `|Q|` existe si et seulement
> si une **statistique du mot observé se factorise par la phase** — ici
> `(v−1) mod 16`, qui est une fonction du bloc. Alors :*
>
> - *coût du crible `|Q|` candidats, `~4` opérations par tirage et par candidat
>   grâce au saut affine ;*
> - *porte : `N · b > log₂|Q|`, où `b` est le nombre de bits que chaque tirage
>   retire à un faux candidat ;*
> - *relèvement `|S|/|Q|` par survivant ;*
> - ***l'exclusion ne relève rien** : zéro survivant sur `Q` exclut tout `S`.*

C'est ce dernier point qui fait le prix du théorème. Pour le mot entier de
MMIX (`r = 0`, `m = 4`) il n'y a que **seize** candidats bas, et leur mort
exclut `2^64` états — un relèvement de `2^60` par survivant n'aurait jamais été
fait.

**Ce que chaque tirage retire — les deux lemmes.** Le §149 lisait **un** mot
par tirage et trouvait toujours « 2 candidats bas » sur ses témoins. Les deux
faits ont la même cause.

> **Lemme des deux mots sûrs.** *Dans un Fisher-Yates partiel par modulo
> (`j_k = k + x_k mod (80−k)`) comme dans un shuffle complet lu par ses vingt
> dernières cases (`j_k = x_k mod (80−k)`), le numéro `j_k + 1` est **toujours
> tiré**, pour tout `k ≤ 19` ; et `j_k ≡ x_k (mod 16)` si et seulement si
> `16 | (80 − k)`, soit `k ∈ {0, 16}`.*
>
> *Preuve.* La case `j_k` n'est jamais une case déjà fixée (`j_k ≥ k`, ou
> `j_k ≤ i` dans le shuffle) ; à la **première** étape `k′ ≤ k` qui la vise,
> son contenu d'origine `j_k + 1` part dans une case qui est fixée à cette
> étape et n'est plus jamais visée : il est tiré. Et `x mod (80−k) ≡ x
> (mod 16)` exactement quand `16 | (80−k)` — avec `16 | 80`, `j_k ≡ x_k`. ∎

Donc chaque tirage donne **deux** contraintes sûres — les registres des mots
`0` et `16` — et `ρ = 1 − C(75,20)/C(80,20) = 0,7728` étant la probabilité
qu'une classe mod 16 soit permise, un faux candidat perd `b = 2·log₂(1/ρ)
= 0,744` bit par tirage au lieu de `0,372`. Et le crible **à un mot** a deux
survivants structurels par état vrai : `s₀` et `f^{16}(s₀)`, dont le mot `0`
est le vrai mot `16`, sûr à chaque tirage — le **fantôme**, celui des témoins
du §149. À deux mots le fantôme meurt (son mot `16` est le vrai mot `32`, qui
n'est pas sûr) ; pour `m ≤ 4`, `f^{16} = id` mod `2^m` et le fantôme est
confondu avec le vrai.

> **Lemme des décalés (le rejet).** *Sous le tirage par rejet des doublons
> (`v = x mod 80 + 1` jusqu'à vingt distincts), **chaque** mot du tirage —
> accepté ou doublon — vaut un numéro de l'ensemble publié : les `σ ≥ 20` mots
> sont tous contraints. Le crible branche sur la fin du tirage (`σ = 20..48`)
> et sur `0..P` mots perdus entre deux tirages ; un faux candidat survit à un
> tirage avec probabilité `Σ_{σ≥20} ρ^σ · (P+1) = 0,0254·(P+1)`, soit
> `b = 2,98` bits pour `P = 4`, `5,30` pour `P = 0`. Ses survivants
> structurels sont les registres **décalés** `f^k(s₀)`, `0 ≤ k ≤ σ₀ − 20`, du
> premier tirage ; les décalages `f^{−p}(s₀)` et `f^{σ₀−20+q}(s₀)` survivent
> avec probabilité `ρ^p`, `ρ^q` (ils se réalignent un tirage plus tard) ;
> aucun survivant n'est étranger au vrai flux.*

Le §149 déclarait le rejet « hors du crible » à cause de son pas variable.
C'est l'inverse : **le rejet est le mode le plus criblable**, huit fois plus de
bits par tirage que le pas constant, parce que le pas variable y est
**la conséquence** de la contrainte sur chaque mot. Témoin (`tools/lcg64_sieve.c
--selftest`, 6/6) : à un mot, état planté retrouvé **avec** son fantôme ; à
deux mots, seul ; sous rejet avec deux mots perdus plantés, douze survivants,
**tous** des `f^k(s₀)` pour `k ∈ [−5, 6]`, les six structurels présents ;
fenêtres aléatoires nulles dans les deux modes.

**Le budget de l'archive.** Le plus long segment à 300 s compte `N = 204`
tirages, soit **152 bits** à pas constant (deux mots) et **608 bits** sous le
rejet. Le crible de `musl` (`m = 37`) attend `2^37·ρ^{408} = 3·10⁻³⁵`
survivants par hasard ; l'exclusion est sur-déterminée d'un facteur quatre.

**Qui a un quotient, et qui n'en a pas.** Le théorème décide famille par
famille — c'est sa vraie portée, et elle est étroite :

| générateur | `L` | quotients | `(v−1) mod 16` se factorise ? | crible |
|---|---|---|---|---|
| LCG mod `2^W`, sortie `s >> r` | `2^W` | `s mod 2^m` (anneau) | **oui**, `m = r+4` | `2^{r+4}` — §149, §152 |
| LCG mod `2^W`, sortie tronquée `(x·80) >> 32` | `2^W` | `s mod 2^m` | non : lit les bits **hauts** | aucun |
| LCG mod `p` premier (MINSTD), MWC (`≡` LCG mod `a·2^32−1`) | `p−1` | phases `d \| p−1` | non : `s mod 16` n'est pas une fonction de la phase (cosets multiplicatifs, équidistribués) | aucun |
| MT19937, tout `L` premier | `2^19937−1` | **aucun** (`L` premier de Mersenne) | — | aucun |
| xorshift32 primitif | `2^32−1 = 3·5·17·257·65537` | phases `d \| L` | non pour `d < 2^16` : un bit de `x_k` est `Tr(β α^k)`, et sur un coset de taille `> √q` la somme de caractères est `< ` sa taille (Weil) ; `d ≥ 65537` : question sans objet, l'énumération §150–151 est complète | aucun |
| SplitMix64, PCG, xorshift\* | `2^64` | `s mod 2^m` (compteur, LCG) | non : la sortie **mélange** tous les bits | aucun |
| Fibonacci retardé additif mod `2^32` (glibc `random()` TYPE_1, `r_i = r_{i−3} + r_{i−7}`, sortie `r_i >> 1`) | — | `(Z/2^m)^{7}` | **oui**, `m = 5` (bits 1..4) | `2^{35}` — §155, les treize trinômes de degré `≤ 7` |
| Fibonacci retardé additif mod `2^32` (glibc `random()` TYPE_3, `r_i = r_{i−3} + r_{i−31}`, sortie `r_i >> 1`) | — | `(Z/2^m)^{31}` | **oui**, `m = 5` (bits 1..4) | `2^{155}` : quotient trop large pour l'énumération — voir 7.7 |

La dernière ligne est la **frontière**. Le quotient existe et la statistique
s'y factorise — le théorème dit que l'attaque est possible — mais `2^155`
candidats ne s'énumèrent pas. Le budget dit ce qu'il faut à la place : à pas
constant, `155/0,744 = 208` tirages, **quatre de plus que le plus long segment
de l'archive** ; sous le rejet, 52 tirages suffisent. L'attaque suivante n'est
donc plus un crible mais un **solveur** : 155 inconnues dans `Z/32`, une
récurrence à deux termes, et par mot une contrainte d'appartenance de quatre
bits — un problème de satisfaction que le crible, lui, résout par force brute.
Réduire `m` ne sert à rien : à `m = 4` (bits 1..3) une classe mod 8 n'est
vide qu'avec probabilité `C(70,20)/C(80,20) = 0,046`, soit `0,07` bit par
mot, et `m = 3` n'en donne plus.

> Le crible des bits bas n'est pas une astuce sur `java` : c'est le théorème
> des quotients appliqué à l'anneau `Z/2^W`. Il atteint **toute** la famille
> des LCG à sortie décalée, sous les trois échantillonneurs à modulo, et il
> **nomme** ceux qu'il n'atteint pas — et pourquoi.

### 7.7 La frontière (§153, §154) — le Fibonacci retardé par ses plans de bits, et ce que l'archive triée en voit

Le 7.6 laisse un générateur dont le quotient existe et ne s'énumère pas :
`random()` de la glibc, `r_i = r_{i−3} + r_{i−31} mod 2^32`, sortie `r_i >> 1`.
Voici pourquoi le coût explose, ce que la récurrence a de linéaire malgré tout,
ce que l'archive triée en voit, et ce qu'il faudrait pour la franchir.

> **Corollaire (la dimension).** *Si la récurrence est d'ordre `D` — l'état
> est fait de `D` mots — le quotient mod `2^m` a `2^{mD}` éléments, et le
> crible coûte `2^{mD}`.* Le LCG a `D = 1` : `2^{r+4}`. Le Fibonacci retardé
> de la glibc a `D = 31` : `2^{155}`. Mersenne Twister a `D = 624`. **Le
> théorème des quotients n'atteint que les générateurs d'ordre un.**

**Les plans de bits, et les retenues.** Écrivons `r_i = 2 q_i + b_i` dans
`Z/32` : `b_i` est le bit 0, jamais publié ; `q_i` les bits 1..4, ce que
`(v − 1) mod 16` observe. Alors

    b_i = b_{i−3} ⊕ b_{i−31}                                    (plan 0 : un LFSR)
    q_i = q_{i−3} + q_{i−31} + c_i  (mod 16),   c_i = b_{i−3} ∧ b_{i−31}.

Le plan 0 est le LFSR de polynôme `x^31 + x^3 + 1`, primitif, de période
`2^31 − 1` — **un nombre premier de Mersenne** : par le théorème Q, ce
LFSR n'a aucun quotient propre. Les nibbles suivent une récurrence
**affine** mod 16 dont le terme constant est le ET de deux bits du LFSR, d'où
la **contrainte de cohérence** : `(q_i − q_{i−3} − q_{i−31}) mod 16 ∈ {0, 1}`,
et cette différence *est* la retenue `c_i`.

> **Lemme (la part linéaire de la sortie — §3 complété).** *Soit un
> Fibonacci retardé additif `r_i = r_{i−k} + r_{i−L} mod 2^32` de trinôme
> primitif. Le bit 0 de la sortie (plan 1 de `r`) satisfait une récurrence
> linéaire sur `GF(2)` d'ordre `2L + C(L,2)`, et le bit 1 (plan 2) une
> récurrence d'ordre au plus `3L + 2C(L,2) + 2C(L,3) + C(L,4)`.*
>
> *Preuve du premier énoncé.* `P(E) r^{(1)} = c` avec `P = x^L + x^k + 1` et
> `E` le décalage. La suite `c_i = b_{i−k} b_{i−L}` est un produit de deux
> décalés d'une même m-suite : son polynôme minimal divise `P · P₂`, où `P₂`
> a pour racines les `C(L,2)` produits `α^{2^i + 2^j}` de deux racines de
> `P`. Donc `(P · P₂ · P)(E) r^{(1)} = 0`, d'ordre `2L + C(L,2)`. Le second
> énoncé s'obtient de même avec la retenue `MAJ(r^{(1)}_{i−k}, r^{(1)}_{i−L},
> c_i)`, produits de poids jusqu'à quatre. ∎

Mesuré par Berlekamp-Massey sur états plantés : plan 1 — `35, 77, 135, 527`
pour `L = 7, 11, 15, 31`, **la borne est atteinte** ; plan 2 — `168, 570, 803,
2530, 7565` pour `L = 7, 10, 11, 15, 20`, atteinte, et `387 < 393` pour
`L = 9` (racines confondues). Pour la glibc : **bit 0 de la sortie, ordre
527 ; bit 1, ordre `41 478`** ; les bits 2 et 3 (plans 3 et 4) font
intervenir des produits de poids huit et seize, `C(31,8) = 7,9·10⁶` racines
et au-delà. La sortie n'est donc pas « non linéaire » en bloc : elle est
linéaire de plus en plus cher, plan par plan, et la statistique du dossier lit
les plans 1 à 4 **ensemble**, dans le nibble.

**Ce que l'archive triée voit.** Sous le rejet, chaque mot de la fenêtre du
tirage `t` a son nibble dans `A_t` (12 classes sur 16 en moyenne) — c'est le
lemme des décalés. Mais la fenêtre dit plus : elle contient **exactement** les
vingt numéros une fois chacun, plus des doublons.

> **Lemme du multi-ensemble.** *Soit `n_c` le nombre de numéros publiés dans
> la classe `c` mod 16, `Σ n_c = 20`, et `m_c` le nombre de mots de la fenêtre
> dans la classe `c`. Alors `m_c ≥ n_c` pour tout `c`, donc `m_c = 0` si
> `n_c = 0`. Une fenêtre de `σ` nibbles uniformes satisfait ces inégalités
> avec probabilité*
>
>     P(σ) = σ!/16^σ · [x^σ] Π_{c : n_c>0} ( e^x − Σ_{j<n_c} x^j/j! ),
>
> *qui vaut `20!/(Π n_c!)/16^20` pour `σ = 20`.*

Sur seize tirages plantés (`h132`), un mot vaut `0,41` bit par appartenance,
une fenêtre de vingt mots `8,2` bits ; le multi-ensemble vaut **`28,1` bits** à
`σ = 20` et **`23,5`** au `σ` réel (moyenne `22,8`). En information, `155/23,5
= 6,6` tirages suffisent — au lieu de `18,9` par appartenance seule (`52` pour
le crible du 7.6, qui paie en plus le branchement sur `σ` et sur les mots
perdus), de `208` à pas constant. Le crible du 7.6 n'en a pas besoin (il est
sur-déterminé d'un facteur seize) ; un solveur, oui.

**Ce que le solveur générique en fait : rien.** `h132` encode le problème pour
`z3` (vecteurs de bits de cinq bits, récurrence, appartenance, multi-ensemble en
contraintes de cardinalité), alignement **connu**, seize tirages — `377` bits
d'information — et fait croître le retard `L` : à **`L = 7`, trente-cinq
inconnues**, `z3` rend `unknown` après 300 s. La raison est structurelle : une
contrainte d'appartenance ne propage rien tant que les deux antécédents
`r_{i−k}, r_{i−L}` ne sont pas fixés, et chaque mot ne retire qu'un quart des
valeurs ; le solveur n'apprend rien avant d'avoir fixé les `5L` bits, et
retombe sur l'énumération de `2^{5L}` — le crible, sans son saut affine. La
frontière est donc **algorithmique** : l'information est là (six tirages), la
structure est là (récurrence à deux termes, plan 0 linéaire, plans 1 et 2
linéaires d'ordre `527` et `41 478`), mais aucun algorithme du dossier ne
convertit des **comptes** par classe en équations sur ces plans — la parité
d'un mot, seule quantité linéaire bon marché, n'est jamais contrainte par un
ensemble trié, qui contient toujours les deux parités.

**Ce que les tirages ordonnés donnent, et ce que le §154 en a fait.** Des
tirages **ordonnés** sous rejet changent tout : chaque mot accepté donne
`v − 1 = o mod 80`, donc le nibble `q_i` **exact** et `o mod 5`. Alors la
cohérence `(q_i − q_{i−k} − q_{i−L}) mod 16 = c_i` livre `c_i = b_{i−k} ∧
b_{i−L}` pour tout mot dont les deux antécédents ont un nibble connu ;
`c_i = 1` (un mot sur quatre) fixe **deux bits** du LFSR — deux équations
linéaires sur les `L` bits initiaux — et `c_i = 0` en interdit un couple. Un
mot perdu a lui aussi un nibble : c'est un doublon, sa classe est l'une de
celles déjà sorties, et l'alignement se cherche en profondeur, paresseusement,
chaque hypothèse élaguée par la cohérence (7/8 par mot). Le plan 0 fixé, les
nibbles sont **affines** mod 16 et se relèvent par Hensel plan par plan.

Mais une condition manquait à la première rédaction de ce paragraphe, et elle
est décisive : la cohérence relie le mot `i` à ses antécédents `i − k` et
`i − L`, qui doivent avoir un nibble connu — donc appartenir à la **même suite
de tirages consécutifs**. Entre deux tirages ordonnés séparés d'un écart
inconnu de mots, aucune équation de retenue ne traverse ; un tirage isolé
(« satellite ») ne sert qu'à **vérifier** un état, en rejouant la récurrence
sur l'écart pour chacun des décalages possibles. Les `5L` bits bas demandent
`5L` bits de cohérence ; un tirage donne ~80 bits de nibbles moins
l'alignement, mais TYPE_3 (`L = 31`) a besoin de **trois tirages consécutifs
au moins** avant que les premières retenues n'apparaissent — `i − 31` doit
être dans la fenêtre. Les douze tirages des vidéos sont trois journées : `A`
deux consécutifs, `B` quatre, `C` un seul. Le §154 le fait, sur ces
données :

- **témoins** : 70 états plantés sur 70 retrouvés, aucun faux, `2 062` bits de
  débordement exacts sur `2 065` ; **155 bits bas de TYPE_3 à partir de quatre
  tirages ordonnés consécutifs, en 109 s** — le plan 0, jamais publié, lu par
  ses retenues ;
- **vidéos** : `0` état sur les sept cellules décisives (TYPE_1 sur A, B, C ;
  TYPE_2 sur A, B, C ; TYPE_3 sur B), six d'entre elles mourant à
  l'**alignement** : aucun placement des doublons ne rend cohérents les
  nibbles, donc aucune suite de retenues n'existe.

> **Lemme (le fantôme de décalage).** *Si le premier mot de la fenêtre est
> suivi de son propre doublon, l'état « un pas plus tard » explique les mêmes
> tirages, ordonnés et satellites compris.* Un état est identifié à son
> **orbite** ; deux fantômes sur soixante-dix témoins, comptés à part.

Les bits bas connus, `r_i = 2 o_i + b_i` donne `r_i mod 5` et, avec `2^32 ≡ 1
(mod 5)`, le **bit de débordement** `w_i = (r_{i−k} + r_{i−L} − r_i) mod 5 ∈
{0, 1}` de chaque mot. Ce bit ne vaut pas, comme l'affirmait la première
rédaction, « un bit d'état haut par mot, `837` mots pour TYPE_3 » : il est une
**fonction des résidus** (`w_i ≡ 2(ρ_{i−k} + ρ_{i−L} + κ_i − ρ_i) mod 5`) et
n'ajoute rien à ce que les résidus disent déjà. Ce qui fixe l'état haut est
la **boîte** `0 ≤ H_i < 2^27` imposée à chaque mot, et son prix est celui du
7.8 : `log₂ M(f)` bit par mot, `M(f)` la mesure de Mahler du trinôme —
`1 640` mots, **72 tirages ordonnés consécutifs** pour l'état entier de TYPE_3,
`35` pour TYPE_2, `17` pour TYPE_1.

> Le 7.6 dit *qui* a un quotient ; le 7.7 dit que le quotient ne suffit pas
> quand l'ordre de la récurrence dépasse un, et **nomme le prix exact** de la
> frontière : trois tirages ordonnés **consécutifs** pour les bits bas de la
> glibc — payés au §154, et la réponse est zéro —, soixante-douze pour l'état
> entier. L'archive triée, elle, n'en donne que des comptes ; le 7.8 dit ce
> que ces comptes valent quand même.

### 7.8 Le relèvement (§154, §155) — l'état haut par l'archive triée : paquets, mesure de Mahler, réseau exact

Le 7.7 s'arrête aux `5L` bits bas. Supposons-les connus — par les vidéos
(§154) ou, pour TYPE_1, par l'énumération des `2^35` états bas contre l'archive
(§155). Reste l'état **haut** : `L` mots de 27 bits, `27L` bits, et une
archive qui ne publie que des **ensembles triés**. Ce paragraphe montre que
l'archive triée suffit, dit combien de tirages elle demande — une formule,
vérifiée à 5 % près —, et donne l'algorithme, témoin compris
(`lab/lfg_releve.py`, `lab/lll_exact.py`).

**La chaîne mod 5.** Écrivons `r_i = 32 H_i + ℓ_i`, `ℓ_i = r_i mod 32` connu,
`H_i` les 27 bits hauts. La récurrence `r_i = r_{i−k} + r_{i−L} − 2^32 w_i`
devient

    H_i = H_{i−k} + H_{i−L} + κ_i − 2^27 w_i,    κ_i = [ℓ_{i−k} + ℓ_{i−L} ≥ 32],

`κ_i` la retenue des bits bas, **connue**, `w_i ∈ {0, 1}` le débordement,
inconnu. Le numéro publié `v` s'écrit `v − 1 = (r_i >> 1) mod 80 = 16 (H_i mod
5) + q_i` puisque `16 · 5 = 80` : l'archive triée dit, pour chaque classe `c`
du nibble présente dans le tirage `t`, l'ensemble `Q_t(c) ⊂ {0..4}` des
résidus `ρ = H mod 5` sortis. Comme `2^27 ≡ 3 (mod 5)`, la chaîne des résidus
est

    ρ_i = ρ_{i−k} + ρ_{i−L} + κ_i − 3 w_i    (mod 5),

et un mot de la fenêtre du tirage `t` doit vérifier `ρ_i ∈ Q_t(q_i)`. Sous le
rejet, la fenêtre a une structure de plus : chaque couple `(q_i, ρ_i)` d'un
mot accepté est **nouveau** dans le tirage, un mot perdu **répète** un couple
déjà sorti, et le tirage s'achève au vingtième accepté. L'alignement n'est
donc pas une inconnue de plus : c'est une **conséquence** de la chaîne. Les
seuls choix sont les `5^L` résidus initiaux et les bits `w_i`.

**Le lemme des paquets, et pourquoi la chaîne ne branche pas.** Énumérer les
chemins `(ρ_0..ρ_{L−1}, w_L, w_{L+1}, …)` explose : `6 768` chemins compatibles
après douze tirages sur un état planté, `162 432` à `30 320 640` après vingt.
Mais ces chemins sont presque tous **le même état** :

> **Lemme (les paquets).** *Soient deux chemins `(ρ^a, w^a)` et `(ρ^b, w^b)`
> qui, au mot `i`, ont les mêmes `L` derniers résidus et se poursuivent
> identiquement. Soit `δ` la suite entière définie par `δ_j = 2 m_j` pour
> `j < L`, `m_j ≡ 2(ρ^b_j − ρ^a_j) (mod 5)` dans `[−2, 2]`, et*
>
>     δ_i = δ_{i−k} + δ_{i−L} − 2 (w^b_i − w^a_i)    (i ≥ L).
>
> *Alors `H^b = H^a + 2^26 δ` est un relèvement entier du chemin `b` dès que
> `H^a` en est un du chemin `a` — même récurrence, mêmes résidus. Si `δ` est
> nulle sur `L` indices consécutifs elle est nulle ensuite, et alors `H^b_i =
> H^a_i` hors d'un **support fini** `S`, et `H^b_i ≡ H^a_i (mod 2^27)` sur `S`
> (`δ` est paire).*
>
> *Preuve.* `2^26 · 2 m_j = 2^27 m_j ≡ 3 m_j ≡ ρ^b_j − ρ^a_j (mod 5)` règle les
> mots initiaux ; pour `i ≥ L`, `2^26 δ_i = 2^26 (δ_{i−k} + δ_{i−L}) − 2^27
> (w^b_i − w^a_i)` est exactement la différence des deux récurrences ; la
> parité de `δ` suit par récurrence de celle des `δ_j`. Une suite qui obéit à
> une récurrence linéaire d'ordre `L` et s'annule sur `L` termes consécutifs
> — les différences `w^b − w^a` étant nulles ensuite — est nulle. ∎

Deux chemins d'un même **état** de la programmation dynamique — `(tirage,
acceptés, perdus, couples sortis, L derniers résidus)` — décrivent donc les
mêmes 27 bits hauts sur tous les mots hors de `S`, et les mêmes mod `2^27` sur
`S`. On les **fusionne** : un représentant, un masque `S` accumulé. Un chemin
dont la queue de `δ` n'est pas nulle (« faux jumeau », `δ ≡ 0 mod 10` sur la
queue sans être nulle, une coïncidence en `5^{−L}`) reste un état à part.
Mesuré (`lfg_releve.py`, TYPE_1 planté, vingt tirages) : **`120` à `700` états
vivants** au plus, `26` à `42` mots masqués, `0` faux jumeau, un état final,
un centième de seconde — contre des millions de chemins.

**La boîte, et la mesure de Mahler.** Le représentant choisi, chaque `H_i`
est une **forme affine entière** des `L` inconnues `G_j = (H_j − ρ_j)/5` :

    H_i = 5 Σ_j α_ij G_j + c_i,   α_i = α_{i−k} + α_{i−L},   α_j = e_j (j < L),

et la seule contrainte restante est la **boîte** : `0 ≤ H_i < 2^27` pour tout
mot hors masque. Combien de mots la rendent unique ? L'estimation naïve
(« un bit de débordement par mot, `27L` mots ») est fausse, et la raison est
belle. Décomposons `H` sur les racines `θ` du polynôme caractéristique
`f(x) = x^L − x^{L−k} − 1` : `H_i = Σ_θ a_θ θ^i` (plus une solution
particulière). Pour une racine **hors du cercle unité**, la boîte impose
`|a_θ| ≲ 2^27 |θ|^{−n}` au bout de `n` mots ; pour une racine dedans elle
n'impose rien de plus que `|a_θ| ≲ 2^27`. Le volume des `a` admissibles vaut
donc `(2^27)^L / Π_{|θ|>1} |θ|^n`, et le produit des racines hors du cercle
est la **mesure de Mahler** `M(f)`. Les `G ∈ Z^L` sont un réseau de densité
constante ; le nombre attendu de solutions parasites est `(2^27/5)^L /
M(f)^n`, d'où

> **Théorème (le nombre de mots).** *Le relèvement de l'état haut d'un
> Fibonacci retardé additif de trinôme `f`, sur `n` mots de résidus connus,
> est unique dès que*
>
>     n > n* = L (27 − log₂ 5) / log₂ M(f),
>
> *et la boîte rapporte `log₂ M(f)` bit par mot — pas un.*

Le bit de débordement, en effet, n'est pas une information indépendante : il
vaut `w_i ≡ 2(ρ_{i−k} + ρ_{i−L} + κ_i − ρ_i) (mod 5)`, il est *lu* dans les
résidus ; et les résidus successifs sont corrélés par la récurrence — seules
les directions **instables** perdent du volume à chaque mot. Or, pour tous
les trinômes des Fibonacci retardés, `M(f)` est **presque la même
constante** : elle converge (Boyd) vers `M(1 + x + y) = 1,3813…`, la
constante de Smyth, `0,466` bit par mot. D'où une règle générale, `n* ≈ 53 L`
mots, soit **`≈ 2,3 L` tirages** de `22,85` mots :

| trinôme | générateur | racines hors du cercle | `M(f)` | bit/mot | `n*` mots | tirages |
|---|---|---|---|---|---|---|
| `x⁷ − x⁴ − 1` | glibc TYPE_1 | 3 | 1,3944 | 0,480 | **360** | 16 |
| `x⁷ − x⁶ − 1` | — | 3 | 1,3887 | 0,474 | 365 | 16 |
| `x⁷ − x − 1` | — | 5 | 1,3794 | 0,464 | 372 | 16 |
| `x⁵ − x² − 1` | — | 3 | 1,4092 | 0,495 | 249 | 11 |
| `x¹⁵ − x¹⁴ − 1` | glibc TYPE_2 | 5 | 1,3835 | 0,468 | **790** | 35 |
| `x³¹ − x²⁸ − 1` | glibc TYPE_3 | 11 | 1,3819 | 0,467 | **1 640** | 72 |
| `x⁶³ − x⁶² − 1` | glibc TYPE_4 | 21 | 1,3815 | 0,466 | 3 335 | 146 |
| `x⁵⁵ − x³¹ − 1` | Knuth (55, 24) | 27 | 1,3813 | 0,466 | 2 913 | 128 |
| `x¹⁰⁰ − x⁶³ − 1` | `ran_array` | 45 | 1,3813 | 0,466 | 5 295 | 232 |
| `x²⁵⁰ − x¹⁴⁷ − 1` | r250 | 117 | 1,3814 | 0,466 | 13 237 | 579 |

**Mesuré.** TYPE_1, dix états plantés (graines 11–20), dix-neuf tirages : à
`360` mots le relèvement **échoue 8 fois sur 10** ; à `380` il **réussit 10
fois sur 10** ; `x⁵ − x² − 1` (`n* = 249`) réussit entre `280` et `309`. La
formule est juste à 5–20 % près, et par le bon côté : elle nomme le seuil.
Sur la graine 1 (ci-dessus, `460` mots) : faux à `300`, juste à `380`, `400`,
`460`, et l'état retrouvé **régénère les vingt tirages**.

**Le réseau, et pourquoi il doit être exact.** La boîte est un problème de
**plus proche vecteur** : le réseau `Λ = {5 α G : G ∈ Z^L} ⊂ Z^n` (coordonnées
hors masque), la cible `τ_i = 2^26 − c_i` (le centre de la boîte), et la
solution est le point de `Λ` à distance `≤ 2^26 √n` de `τ`. Babai sur une
base LLL le trouve, et la base réduite donne la **condition suffisante
d'unicité** : deux solutions diffèrent d'un vecteur de `Λ` de norme `≤ 2^27
√n`, donc `λ₁(Λ) > 2^27 √n` suffit. Mesuré : `λ₁/(2^27 √n) = 0,003` à `300`
mots, `0,13` à `380`, `0,34` à `400`, `5,6` à `460` — la condition suffisante
croise 1 entre `400` et `460`, Babai réussit dès `380` : la garantie est
prudente d'un facteur `1,2`, la formule de Mahler est la bonne. Mais les
entrées de la base croissent comme `M(f)^n ≈ 2^{190}` à `400` mots, et
`lll.py`, qui orthogonalise en flottants, **échoue toujours** (0 succès sur 8
tailles, alors que la solution est unique) : la base « réduite » est fausse
et Babai rend n'importe quoi. `lll_exact.py` calcule la matrice de Gram **une
fois**, en entiers exacts (`L²` produits scalaires de longueur `n`), puis
réduit et projette en rationnels exacts de dimension `L` en suivant la
matrice unimodulaire ; une seconde par relèvement.

**L'algorithme complet (`lfg_releve.releve_etat`).** État bas + tirages
triés consécutifs → chaîne mod 5 en programmation dynamique avec fusion des
paquets → pour chaque état final, formes entières du représentant, CVP exact
hors masque, `H = H' mod 2^27`, état `r_j = 32 H_j + ℓ_j` → **vérification
par régénération** des tirages. Témoin : `python3 lab/lfg_releve.py 3 7 20
graine`, `[état] == [vrai]` sur toutes les graines essayées ; les faux états
finaux (graine 5 : treize, d'alignements voisins) meurent à la
régénération.

**Ce que l'archive triée peut donc donner, générateur par générateur.** Deux
étages : les `5L` bits bas, puis le relèvement.

- *Bits bas.* L'archive triée en dit `≈ 0,41` bit par mot par appartenance
  (§153, h132), jusqu'à `23` à `28` bits par tirage avec le multi-ensemble :
  l'information y est dès **deux à quatre tirages**. Mais aucun solveur ne
  la convertit (§153) ; il faut **énumérer** `2^{5L}` états bas contre la
  fenêtre : `2^35` pour TYPE_1 — faisable, et c'est le §155 — ; `2^75` pour
  TYPE_2 et `2^155` pour TYPE_3, hors de portée. C'est là, et là seulement,
  que passe la frontière.
- *Relèvement.* Les bits bas connus, `n*` mots **triés consécutifs**
  suffisent : `17` tirages pour TYPE_1, `35` pour TYPE_2, `72` pour TYPE_3 —
  et l'état entier régénère l'archive et **prédit** le tirage suivant. Pour
  TYPE_2 et TYPE_3 ce second étage est prêt et n'attend que le premier ;
  les vidéos donnent l'état bas par les retenues (§154) mais elles ne
  sont pas suivies de trente-cinq tirages ordonnés ou triés consécutifs
  connus : la chaîne mod 5 peut traverser un écart d'identifiants connu en
  branchant sur le nombre de mots perdus, elle ne traverse pas un écart
  inconnu.
- *Fisher-Yates et brassages.* Le relèvement n'existe que pour
  l'échantillonneur à modulo, où `v − 1 = 16 (H mod 5) + q` publie un résidu
  de `H`. Sous un brassage, `r_i` indexe une position, non un numéro : le
  résidu mod 5 n'est pas publié, la chaîne n'a pas de contrainte, et le
  relèvement redevient une recherche de permutation — non développée ici.

> Le 7.7 chiffre ce que l'archive triée ne voit pas ; le 7.8 chiffre ce
> qu'elle voit : **`log₂ M(f)` bit par mot**, la mesure de Mahler du trinôme,
> `0,47` pour toute la famille — et un algorithme exact, témoin compris, qui
> transforme `n*` tirages triés consécutifs et `5L` bits bas en l'état
> entier. Pour TYPE_1 l'archive fournit les deux ; c'est le §155.

### 7.9 Le crible des bas sous le rejet (§155) — le lemme des courses, la chaîne mod 5 avec perdus, les dégénérés

Le 7.6 dit que le rejet est le mode le plus criblable (2,98 bits par tirage
pour `P = 4` perdus) ; le 7.8 relève l'état haut. Le §155 met les deux bout à
bout sur l'archive pour **tous** les Fibonacci retardés de degré `L ≤ 7` — les
treize trinômes primitifs, TYPE_1 `(3, 7)` compris — et trois points de
théorie manquaient pour que cela tourne : comment cribler `2^35` états sous
un pas variable sans brancher, comment la chaîne mod 5 traverse des mots
perdus entre tirages, et ce que le crible rend de **structurel** à petit `L`.

**Le crible sans branchement.** La définition du survivant sous le rejet
branche : à chaque tirage sur `σ ∈ [20, 48]` et sur `g ∈ [0, P]` perdus, soit
`145^N` chemins pour `N` tirages. Or les départs possibles d'un tirage ne sont
pas des points mais des **courses**.

> **Lemme (les courses).** *Soient `A_d ⊂ Z/16` le masque du tirage `d`, et
> `[a, b]` un intervalle de départs possibles de ce tirage. Appelons course
> maximale `(s, R)` une suite de `R` résidus consécutifs permis par `A_d`
> commençant en `s ∈ [a, b]`, bornée par un résidu interdit. Les départs
> possibles du tirage `d + 1` issus de `[a, b]` sont la réunion, sur les
> courses de longueur `R ≥ 20`, des **intervalles***
>
>     [s + 20,  min(s + R, b_s + 48) + P],     b_s = min(b, s + R − 20).
>
> *Preuve.* Un départ `s′ ∈ [s, b_s]` de la course admet exactement les
> longueurs `σ ∈ [20, min(48, s + R − s′)]` — tous ses mots sont permis
> jusqu'au bout de la course et pas au-delà — puis `g ∈ [0, P]` perdus : ses
> départs suivants forment `[s′ + 20, min(s′ + 48, s + R) + P]`. Deux
> départs consécutifs de la course donnent des intervalles qui se recouvrent
> (`s′ + 21 ≤ s′ + 48 + P`), la réunion sur `s′ ∈ [s, b_s]` est l'intervalle
> annoncé ; un départ hors d'une course de longueur `≥ 20` n'a aucune
> continuation. ∎

La récursion porte donc sur les **courses** et non sur les couples `(σ, g)` :
le nombre de courses de longueur `≥ 20` dans une fenêtre de `w` positions
vaut en moyenne `w · ρ^20 (1 − ρ) ≈ 0,0013 w` pour un faux candidat — la
récursion est presque **sans branchement**, et sur le vrai flux la course du
vrai départ est la seule qui compte. L'autotest de `tools/lfg_low_sieve.c`
vérifie l'égalité des deux définitions — mêmes survivants, mêmes empreintes —
sur `2^20` états et des masques à trente numéros (courses longues, où le
branchement de la définition est le plus lourd). Le reste est de
l'énumération : chaque mot bas est une **forme linéaire** `r_i = Σ_j α_ij r_j
mod 32` des `L` mots initiaux, `α_i = α_{i−k} + α_{i−L}`, énumérée en `L`
boucles imbriquées à sommes courantes ; les seize premières formes sont
testées d'un coup en registre vectoriel (`1,6 %` passent à pas constant, deux
mots sûrs par tirage), les seize suivantes sur les rescapés, le reste en
scalaire. `2^35` états contre 204 masques : une à trois minutes sur quatre
cœurs.

**La chaîne mod 5 traverse les perdus.** Le 7.8 supposait les tirages
**jointifs** : le premier mot du tirage `t + 1` suit le dernier du tirage
`t`. Sous le rejet, `g_t ∈ [0, P]` mots peuvent être consommés entre deux
tirages sans être publiés. Un tel mot n'est soumis à **aucun** masque : sa
classe `q_i` est connue (les bits bas le sont), son résidu `ρ_i` est celui
que la récurrence impose pour `w_i = 0` ou `w_i = 1` — deux branches, pas
cinq. La clé de la programmation dynamique gagne un compteur `g ∈ [0, P]` :
un mot est *libre* dès que le tirage courant n'a encore ni accepté ni perdu
et que `g < P` ; les mots libres ne coûtent qu'un facteur `2^{g}` par tirage,
que les fusions du lemme des paquets absorbent (mesuré, TYPE_1 : `451`
états vivants au plus sur vingt tirages avec `g_t = t mod 3`, `1 066` sur
trente avec `g_t = t mod 5`, contre `120` à `700` sans perdus au 7.8). Le vérificateur, lui, mémoïse les **départs vivants** `(t, s)`
— le tirage `t` peut-il commencer au mot `s` ? — et accepte un état dès qu'un
chemin de départs traverse tous les tirages.

**Les faux jumeaux à petit `L`.** Le 7.8 compte un faux jumeau (`δ ≡ 0 mod
10` sur la queue sans `δ = 0`) pour une coïncidence en `5^{−L}` — `1/25` au
degré 2, `1/125` au degré 3. À cette fréquence, une programmation dynamique
qui garde **un** représentant par clé et rejette dans une clé neuve chaque
jumeau qu'elle ne peut fusionner ne les refusionne plus jamais : au degré 2
les chemins explosent (`200 000` états, abandon) alors que l'état est
déterminé par soixante-dix mots. La réparation est une **liste** de
représentants par clé : un chemin nouveau est confronté à chacun, fusionné au
premier dont la queue de `δ` est nulle, ajouté sinon. Mesuré au degré 2, trente
tirages : `760` états vivants, `34 191` jumeaux confrontés, l'état exact — en
19 secondes ; à `n* = 71` mots (huit tirages), un centième. Le §155 donne à la
chaîne `2,5 n*` mots, ni plus (le degré 2 à trente tirages coûte cher) ni
moins (le degré 4 échoue à huit tirages, TYPE_1 à douze).

**Les dégénérés.** Le sous-groupe `16 · F_2^L` des états bas dont tous les
mots sont `0` ou `16` est **stable** par la récurrence (`16 + 16 ≡ 0 mod
32`) : ses `2^L` états n'ont que les résidus `0` et `8`. Ils survivent à tout
crible dont les `N` masques contiennent tous `0` et `8` — probabilité
`ρ^{2N}` sur des masques quelconques, `10^{−46}` pour l'archive, mais
**fréquent** sur un témoin de degré `≤ 3` : la suite basse y est de période
`(2^L − 1) · 16 ≤ 112`, et si `0` et `8` y sont fréquents, toute fenêtre de
vingt mots les contient, donc tous les masques. Le témoin `(2, 3)` du §155
rend ainsi ses `8` dégénérés en plus des décalés du vrai (ceux de degré 2 et
`(1, 3)`, dont la suite basse omet `0` ou `8` dans quelque fenêtre, n'en
rendent aucun) ; ils sont comptés à part, et sur l'archive aucun ne survit.
Même remarque pour le lemme des décalés : à petit `L` le cycle du vrai est
court, et « décalé » se lit modulo sa période.

> Le 7.9 ferme la boucle du 7.6 au 7.8 : le théorème des quotients dit que
> le crible existe (`(Z/32)^L`), le lemme des courses le rend linéaire sous
> le rejet, la chaîne mod 5 avec perdus et le CVP exact relèvent le
> survivant, et le §155 exécute le tout sur l'archive pour les treize
> trinômes de degré `≤ 7`.

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

**Sauf pour le Fibonacci retardé sous le rejet** (§7.7, §154) : là, les
équations sont des retenues entre un mot et ses antécédents `i − k`, `i − L`,
et elles n'existent qu'entre tirages **consécutifs** — un tirage isolé ne
sert qu'à vérifier. TYPE_3 (`L = 31`) demande trois consécutifs au moins ;
les vidéos en ont quatre (jour B), et la réponse est zéro. Pour l'état
**entier**, c'est le §7.8 qui compte : `n* = L(27 − log₂ 5)/log₂ M(f)` mots,
`72` tirages consécutifs — ordonnés ou **triés**, l'archive suffit — pour
TYPE_3, `35` pour TYPE_2, `17` pour TYPE_1.

| cible (glibc `random()`, sous rejet) | tirages consécutifs requis | disponibles |
|---|---|---|
| état bas TYPE_1, TYPE_2 (35, 75 bits) | 1 à 2 ordonnés (+ satellites) | **jours A, B, C — atteint, réponse 0** |
| état bas TYPE_3 (155 bits) | 3 ordonnés | **jour B (4) — atteint, réponse 0** |
| état bas TYPE_1 par l'archive triée | énumération `2^35` | **archive — §155** |
| état entier TYPE_1 (224 bits) | 17 triés | **archive — §155** |
| état entier TYPE_2, TYPE_3 | 35, 72 triés, **après** les bits bas | bits bas hors de portée par l'archive |

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

**Et le compte en tirages dépend de l'échantillonneur, pas seulement du
générateur.** Les `222` tirages ci-dessus sont ceux de la **troncature**
(`4,48` bits linéaires par mot, théorème du préfixe §105, `≈ 90` équations
par tirage, §110). Sous les deux autres échantillonneurs le même MT19937
coûte autrement, et il faut le dire pour ne pas promettre `222` à un
Fisher-Yates par modulo :

| échantillonneur | bits linéaires par tirage ordonné | MT19937, tirages ordonnés | où est le mur |
|---|---|---|---|
| troncature `(x·K) >> 32` | `≈ 90` (§105, §110) | **222** | aucun — pas constant, alignement connu |
| Fisher-Yates par **modulo** `x mod K` | **22** (`Σ v₂(K)`, `K = 80…61`, §69, §71) | **`≥ 907`** | borne inférieure : les dépendances de rang (§80) ne peuvent que l'élever |
| **rejet** modulo 80 | `80` (4 par mot accepté, §68) | `343` **si l'alignement est connu** (§80) | il ne l'est pas : arbre de rejet `C(19 937/4 + r, r)` (§111), `r ≈ 700` à `1 000` rejets sur 250 à 343 tirages, soit plus de `2^3000` nœuds avant le premier élagage — hors de portée |

Sous le rejet, la seule alternative à l'arbre serait le crible d'un quotient
autonome, comme au §7.6 et au §7.9 — et le théorème Q dit qu'un générateur
`F₂`-linéaire primitif n'en a **aucun**. L'archive **triée**, elle, ne rend à
un `F₂`-linéaire que le rang du bonus sous la troncature (`3,20` bits par
tirage, §106) — c'est la voie du §114, qui a exclu MT19937 à `6 231` tirages
triés ; sous le modulo et sous le rejet, le résidu mod 16 d'un **ensemble**
n'est pas une forme linéaire, et le tri ne publie rien de linéaire du tout.

> Tant qu'on n'a que l'ensemble trié, la voie model-free est la seule. Dès qu'on
> a l'ordre, elle est **cent fois** la plus lente.
