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

**Addendum (§161, h141) — la graine de `random()` elle-même, quelle que soit sa
source.** Les quatre balayages ci-dessus ont chacun un angle mort, et c'est le
même : ils balaient soit **une graine quelconque contre un seul tirage** (§120,
§121 : familles brouillées, premier tirage), soit **une graine dérivée d'une
quantité publiée** contre les journées (§133 : six formes, sept familles
brouillées) ou l'ordre daté (§132). Aucun n'a balayé les 2³² amorçages de
**`random()`** — la famille du §7.1, celle dont l'état bas a été rejeté sur
l'archive entière — contre **tous** les blocs ou **tous** les tirages, pour
une graine dont on ne suppose **rien** : `getpid()`, une adresse, `getrandom`,
un compteur de processus, une horloge d'un autre fuseau.

L'attaque tient en deux index sur l'archive triée :

- **une graine par bloc** : les 370 premiers ensembles de bloc forment un index
  bitmap `M[v] ⊂ {blocs}` (`v = 1..80`) ; l'émission `x₀, x₁, …` d'une graine
  est intersectée numéro par numéro, `M[x₀] ∩ M[x₁] ∩ …`, et meurt en ~5
  numéros pour une graine fausse. Fausse touche `1/C(80,20) = 2,8·10⁻¹⁹` par
  (graine, combinaison, bloc), donc `2³² · 149 · 370 · 2,8·10⁻¹⁹ = 6,6·10⁻⁴`
  par balayage complet ;
- **une graine par tirage** : index **inverse des 5-sous-ensembles**. Chaque
  tirage inscrit ses `C(20,5) = 15 504` sous-ensembles au rang combinatoire
  `r(a<b<c<d<e) = C(a,1)+C(b,2)+C(c,3)+C(d,4)+C(e,5) < C(80,5) = 24 040 016`
  (bijection de Lehmer), soit `1,09·10⁹` entrées ; une émission lit le rang de
  ses cinq plus petits numéros et ne compare ses vingt numéros qu'aux ~45
  tirages de la liste, filtrés d'abord par une empreinte 15 bits de leur masque.
  Fausse touche `70 560/C(80,20) = 2·10⁻¹⁴` par (graine, combinaison), `3·10⁻³`
  par balayage de 2³² × 32.

Quatre amorçages (glibc `srandom`/`initstate` TYPE_1..4, FreeBSD/macOS, 4.4BSD,
musl — 16 variantes), 21 échantillonneurs, décalages de mots avant le tirage,
et une **confirmation** indépendante : `--suite` doit rendre le tirage
**suivant** du même bloc (fausse continuation `2,8·10⁻¹⁹`), ou deux touches
doivent partager une convention. Témoins : 0 écart contre la libc réelle,
149/149 plantes × 16 variantes, 4/4 plantes noyées dans 70 000 tirages, 0
fausse touche. Résultat et couverture au §161 (balayage en cours, journalisé
segment par segment).

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
ensemble trié, qui contient toujours les deux parités. *(Révisé au 7.10 :
la conversion existe dès que les plans `0..2` sont devinés — chaque plan
suivant est affine en `L` inconnues et les mots sûrs le contraignent ; la
frontière passe de `2^{5L}` à `2^{3L}`. La phrase ci-dessus reste vraie
du solveur générique, qui ne devine pas.)*

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
  que passe la frontière. *(Révisé au 7.10 : `2^{3L}` hypothèses suffisent
  — `2^{45}` pour TYPE_2, une identification d'une heure de carte graphique
  ou de quelques années-cœur ; `2^{93}` pour TYPE_3, toujours hors de
  portée.)*
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

### 7.10 Les trois plans muets (§156) — `2^{3L}` au lieu de `2^{5L}`, le mot 16 à six bits, les mots sûrs gradués

Le 7.7 disait que la frontière était **algorithmique** : « aucun algorithme
du dossier ne convertit des comptes par classe en équations sur ces plans »,
et le 7.8 plaçait la frontière à l'énumération des `2^{5L}` états bas —
« c'est là, et là seulement, que passe la frontière ». Les deux phrases sont à
**réviser** : l'algorithme existe, il est écrit (`tools/lfg_trois_plans.c`,
témoin `h136`, §156), et la frontière passe à `2^{3L}`. Il ne va pas jusqu'à
TYPE_3, et il **identifie** sans relever ; mais il déplace la borne d'un
facteur `2^{2L}` et change le statut de TYPE_2. Voici le théorème, ses
nombres exacts, deux lemmes nouveaux sur les mots sûrs, la mesure, et ce
qui reste fermé.

**Le principe.** Le 7.7 mesurait la complexité linéaire de chaque plan de
bits *comme fonction de l'état entier* : `2L + C(L,2)` pour le plan 1,
`41 478` pour le plan 2 de la glibc, des produits de poids huit et seize
au-delà. C'est le bon objet si l'on veut des équations **sans rien deviner**.
Mais si l'on **devine** les plans bas, les retenues deviennent des
constantes, et chaque plan est affine en `L` inconnues seulement. La
question n'est plus « quel est l'ordre du plan `p` » mais « combien de plans
faut-il deviner avant que l'archive triée ne fournisse assez d'équations pour
les suivants ». La réponse est **trois**.

> **Théorème des trois plans muets.** *Soit `r_i = r_{i−K} + r_{i−L} mod
> 2^32`, sortie `x_i = r_i >> 1`, et notons `b^p_i` le bit `p` de `r_i`.
> Les plans `0..p−1` des `L` mots initiaux étant fixés, les plans `0..p−1`
> de **tous** les mots sont connus (autonomie mod `2^p`), et le plan `p` de
> tout mot est une forme **affine** sur `F₂` du plan `p` initial
> `x_p ∈ F₂^L` :*
>
>     b^p_i = ⟨α_i, x_p⟩ ⊕ γ_i,
>     α_i = α_{i−K} ⊕ α_{i−L}   (α_j = e_j pour j < L),
>     γ_i = γ_{i−K} ⊕ γ_{i−L} ⊕ c^p_i,   γ_j = 0 pour j < L,
>     c^p_i = [ (r_{i−K} mod 2^p) + (r_{i−L} mod 2^p) ≥ 2^p ].
>
> *Un mot sûr (lemme du 7.6) dont le masque, sachant ses bits `1..p−1`, ne
> permet **aucun** bit `p` tue l'hypothèse ; qui n'en permet qu'**un** donne
> l'équation linéaire `⟨α_i, x_p⟩ = b ⊕ γ_i` ; qui permet les deux ne dit
> rien. Les plans `0..2` énumérés (`2^{3L}` hypothèses), les plans `3, 4`
> (mot lu mod 16) et `3..6` (mot lu mod 64) se résolvent par Gauss sur
> `F₂^L`, plan après plan.*
>
> *Preuve.* `r_i mod 2^{p+1} = (r_{i−K} + r_{i−L}) mod 2^{p+1}` ; le bit `p`
> de la somme est `b^p_{i−K} ⊕ b^p_{i−L} ⊕ c^p_i`, où `c^p_i` est la retenue
> sortant des `p` bits bas, fonction des seuls `r mod 2^p`, donc connue.
> Par récurrence sur `i`, `b^p_i` est une combinaison affine des `b^p_j`,
> `j < L`, de partie linéaire `α_i` (la récurrence de `α` est celle du LFSR
> de `x^L + x^K + 1`) et de constante `γ_i`. Le reste est la définition d'une
> équation sur `F₂`. ∎

Le théorème est banal ; ce qui ne l'est pas, c'est le nombre de plans à
deviner, et il vient des taux exacts. Notons `hyp(m) = C(80−m,20)/C(80,20)`
la probabilité qu'un ensemble donné de `m` numéros soit **entièrement
absent** d'un tirage de vingt, et `hyp*(m) = C(79−m,19)/C(79,19)` la même
sachant qu'un numéro hors de ces `m` est tiré (le cas du vrai état, dont le
résidu est toujours permis).

**Pourquoi trois.** Le plan 0 n'est jamais publié — `x = r >> 1` — et
n'agit que par ses retenues : aucune équation ne le concerne, il faut le
deviner. Le plan 1 (bit 0 de `x`) est forcé, au mot 0, quand une **parité
entière** des seize classes est absente du tirage : `2 · hyp(40) ≈ 8·10⁻⁸`
par mot — jamais. Le plan 2, sachant le plan 1, est forcé quand une
demi-classe de quatre résidus (vingt numéros) est absente : `2 · hyp(20) ≈
0,0024` par mot au mot 0, `≈ 0,011` au mot 16 lu mod 64 — soit **trois
équations** par fenêtre de 204 tirages pour `L` inconnues, et le plan 2 se
devine aussi. Au plan 3 les demi-classes n'ont plus que dix numéros
(mot 0) ou huit (mot 16 mod 64), et les équations arrivent :

| canal | plan | classe morte (faux) | équation (faux) | équation (vrai) |
|---|---|---|---|---|
| mot 0, mod 16 | 3 | 0,00119 | 0,0893 | 0,0523 |
| mot 0, mod 16 | 4 | — | 0,3802 | 0,2423 |
| mot 16, mod 64 | 3 | 0,00555 | 0,1664 | 0,0981 |
| mot 16, mod 64 | 4 | — | 0,4827 | 0,3245 |
| mot 16, mod 64 | 5 | — | 0,7281 | 0,5745 |
| mot 16, mod 64 | 6 | — | 0,8633 | 0,7595 |

Par mot sûr et par plan. Pour un **faux** état (résidu au hasard) : mort si
sa classe est vide, `hyp(classe)` ; équation, sachant la classe vivante,
`2 (hyp(demi) − hyp(classe)) / (1 − hyp(classe))`. Pour le **vrai** (résidu
toujours permis) : équation si l'autre demi-classe est vide, `hyp*(demi)`.
Au plan `p ≥ 4` la classe est vivante par construction — le plan `p−1`
résolu a choisi une moitié non vide — et seule la colonne « équation »
s'applique. Sur 204 tirages le vrai état reçoit au plan 3 **21,4
équations** au canal 4 (408 mots) et **30,7** au canal 6 ; un faux en
reçoit 36,4 ou 52,2 — et sur `L = 7` inconnues elles se contredisent vite :
le témoin du §156 voit un faux état de TYPE_1 mourir après `108` mots sûrs
en moyenne sur `408` (`85` au canal 6), presque toujours par
**contradiction de Gauss** (`2 097 149` sur `2^21`) et non par classe vide
(`2`, contre `758 086` sur le contrôle : la classe vide est un événement
rare — `0,0012` par mot — dont le compte dépend de l'endroit où il tombe,
et n'est pas le moteur du crible). Au plan 4 le vrai reçoit `99` équations
(canal 4) ou `116` (canal 6) : le plan 3 résolu, tout le reste est
sur-déterminé.

**Le rang.** `21,4` équations pour `L` inconnues suffisent à `L = 7` et
`L = 15`, pas à `L = 31` : le système du plan 3 est alors de rang `< L`
pour le vrai état comme pour ses voisins. Ce n'est **pas fatal** : les
solutions sont énumérées (`2^{L − rang}`, borné à `4096`) et chacune est
portée au plan 4, où `99` équations la tranchent — le témoin TYPE_3 du §156
compte `128 384` rejets au plan 4 pour `2^21` hypothèses, contre `0` à
`L ≤ 15`. À `L = 63` (TYPE_4) il faudrait `≈ 340` tirages au canal 6
(`≈ 490` au canal 4) pour que `2^{L − rang}` repasse sous la borne, et
`≈ 420` (`600`) pour le rang plein ; TYPE_4 est de toute façon à `2^{189}`.

> **Lemme du mot 16 à six bits.** *Dans le Fisher-Yates partiel par modulo
> au pas constant, `j_{16} = 16 + x_{16} mod 64` et `j_{16} + 1` est tiré
> (lemme des deux mots sûrs) : donc `x_{16} mod 64 ∈ {v − 17 : v tiré,
> v ≥ 17}`. Chaque résidu mod 64 correspond à **un seul** numéro de
> `17..80`, tiré avec probabilité `20/80 = 1/4` : le mot 16 publie
> **exactement `log₂ 4 = 2` bits** par tirage, contre `log₂(1/ρ) = 0,372`
> pour sa lecture mod 16.*
>
> *Preuve.* `80 − 16 = 64` ; le lemme du 7.6 donne `j_{16} + 1 ∈ tirage`
> et `j_{16} ≡ x_{16} (mod 64)`, ce qui est plus fort que la congruence
> mod 16 qu'il retenait. Les `64` numéros `17..80` sont en bijection avec
> les résidus, et un `20`-sous-ensemble de `80` en contient chacun avec
> probabilité `1/4`. ∎

C'est le **canal 6** : l'état bas devient `7L` bits (`r mod 128`) au lieu
de `5L`, et la fenêtre de 204 tirages en dit `204 · (0,372 + 2) = 484` bits
au lieu de `152`. Le canal 4 n'identifie que `5L ≤ 152`, soit `L ≤ 30`
d'information brute (`L ≤ 15` avec marge) ; le canal 6 identifie `7L ≤
484`, `L ≤ 69` — TYPE_3 (`217` bits) est **identifiable en principe**,
TYPE_4 (`441`) à la limite. Le témoin du §156 le montre à petite fenêtre :
TYPE_2, `50` tirages, cinq mots libres (`2^15 · 2^{2·15} = 2^45` états bas
au canal 4, `37` bits d'information) : **`1 663` survivants** dont le
planté — deux cents attendus par le compte de bits, mais les survivants
viennent en familles : le plan 3 n'y reçoit que cinq équations pour quinze
inconnues — ; au canal 6 (`119` bits) : **le planté seul**. Le même lemme
se **gradue** :

> **Lemme des mots sûrs gradués.** *Pour tout `k ≤ 19`, `x_k mod (80 − k) ∈
> {v − 1 − k : v tiré, v > k}` exactement ; donc `x_k mod 2^{e_k}` est
> contraint, avec `e_k = v₂(80 − k)` : `e = 4` au mot 0, `6` au mot 16,
> **`3` au mot 8**, `2` aux mots 4 et 12, `1` aux autres mots pairs, `0`
> aux mots impairs.*
>
> *Preuve.* Le lemme du 7.6 dit que `j_k + 1` est tiré pour tout `k ≤ 19`,
> avec `j_k = k + x_k mod (80−k)` ; et `x mod (80−k)` détermine `x mod
> 2^e` pour tout `2^e | 80 − k`. ∎

Le mot 8 (`80 − 8 = 72 = 8 · 9`) publie donc `x_8 mod 8` : un résidu mod 8
permis avec probabilité `1 − hyp(9) ≈ 0,94`, `0,095` bit par tirage — et,
plan par plan, une équation au plan 3 avec probabilité `0,123` (faux) ou
`0,072` (vrai) par tirage. L'outil du §156 ne lit que les mots 0 et 16 ;
le mot 8 vaudrait de moitié à deux tiers d'équations en plus au plan 3
(`0,072` contre `0,105` au canal 4, `0,150` au canal 6) et une mort plus
précoce des faux — un facteur `1,3` à `1,7` sur le coût, non mesuré, non
exploité. Les autres mots (`e ≤ 2`) ne contraignent que les plans 1 et 2,
devinés.

**L'algorithme et sa mesure.** `lfg_trois_plans.c` parcourt `(Z/8)^L`
mots initiaux ; pour chaque hypothèse il engendre `r mod 8` et `γ`
**paresseusement**, tirage par tirage, et ajoute à un Gauss incrémental
sur `F₂^L` (une ligne par pivot, `L` mots de 64 bits) l'équation de chaque
mot sûr forcé — un faux état est abandonné à la première contradiction ou
classe vide, sans engendrer la suite. Les hypothèses vivantes ont leur plan
3 énuméré (`g_solutions`, au plus `4096`), puis le plan 4 et, au canal 6,
les plans 5 et 6 par le même Gauss (`etage`), chaque survivant vérifié mot
par mot mod `2^{PFIN}`. Mesuré (§156, 204 tirages, graine `20260902`,
`2^21` hypothèses par ligne, une machine à quatre cœurs **chargée** par
deux autres balayages — les nanosecondes sont des majorants ; « planté » :
masques d'un état planté, tout `(Z/8)^7` parcouru pour TYPE_1, sous-cube
de sept mots libres autour du planté pour `L > 7` ; « contrôle » : mêmes
hypothèses contre des tirages de vingt numéros au hasard) :

| générateur | canal | mots sûrs lus, planté / contrôle | ns/hypothèse, planté / contrôle | survivants |
|---|---|---|---|---|
| TYPE_1 `(3,7)` | 4 | `108` / `65` | `1 741` / `1 082` | le bas planté seul / `0` |
| TYPE_1 | 6 | `85` / `52` | `1 385` / `832` | idem / `0` |
| TYPE_2 `(1,15)` | 4 | `88` / `185` | `2 392` / `4 843` | idem / `0` |
| TYPE_2 | 6 | `55` / `125` | `1 585` / `3 620` | idem / `0` |
| TYPE_3 `(3,31)` | 4 | `229` / `377` | `5 598` / `185 126` | idem / `0` |
| TYPE_3 | 6 | `152` / `217` | `3 764` / `4 768` | idem / `0` |

Autotest du §156 : `13/13`. Le coût par hypothèse est celui des mots
engendrés avant la mort, et la mort vient de deux sources : la **classe
vide**, rare (`0,0012`–`0,0056` par mot) mais qui, tombant tôt, emporte un
quart des hypothèses d'un coup — d'où les écarts planté/contrôle, qui ne
tiennent qu'à l'endroit où tombent ces cellules — ; et la **contradiction
de Gauss**, qui n'arrive qu'une fois le rang atteint, soit `≈ L/0,179`
tirages au canal 4 (`L/0,256` au canal 6) : `84` tirages, `168` mots pour
TYPE_2 au canal 4, mesuré `185`. Le coût croît donc **linéairement en
`L`**, et le contrôle est la valeur à retenir. À `L = 31` au canal 4
s'ajoute le rang déficient du plan 3 : `73` solutions en moyenne par
hypothèse vivante (`797 322` vivantes, `58,5` millions de rejets au
plan 4), d'où `185` µs ; le
canal 6, dont les `30,7` équations suffisent, reste à `4,8` µs. Sur
l'archive (fenêtre du §155, `1309794..1309997`, description des masques et
non test) : aucune classe mod 4 vide au mot 0 (`0,97` attendue), huit au
mot 16 lu mod 64 (`4,5` attendues), la première au tirage `43` ;
`16,05` numéros `≥ 17` par tirage (`16` attendus). Le sous-cube ne mesure
que le coût par hypothèse et la présence du planté ; il **ne remplace pas**
le parcours de `2^{3L}`. D'où les coûts :

- **TYPE_1** : `2^21` hypothèses, **trois secondes**. Il n'y a rien à
  relancer sur l'archive : le crible du §155 (mode 0, pas 20, canal 4)
  énumère `2^{35}` états bas et n'en garde aucun ; tout survivant du
  crible à trois plans est un état bas mod 32 compatible avec les mêmes
  masques, donc un survivant du §155 — l'ensemble est vide **par
  corollaire**, pas par expérience nouvelle. Le canal 6 ne peut que
  restreindre davantage.
- **TYPE_2** : `2^45` hypothèses à `3,6`–`4,8` µs (contrôle), soit **`4`
  à `5,4` années-cœur**, plus d'un an sur cette machine, `1,8` à `2,7`
  années-cœur si les cellules vides de l'archive tombent bien (planté) ;
  `≈ 3,5·10^{16}` opérations élémentaires, **de l'ordre de l'heure à la
  journée sur une carte graphique** (les hypothèses sont indépendantes,
  l'état tient dans des registres). C'est une identification, pas un
  relèvement (ci-dessous), et elle n'a pas été lancée : elle est hors de
  ce dossier, non hors de portée.
- **TYPE_3** : `2^93` à `5` µs, `≈ 5·10^{22}` secondes, `10^{15}` ans.
  Hors de portée, et de loin ; l'information (`484` bits pour `217`) y
  est, l'algorithme non. TYPE_4 : `2^{189}`.

**Ce que le solveur générique en fait, encore rien.** `h135` encode le
même problème pour CryptoMiniSat (XOR natifs) et CaDiCaL : `36 665`
variables, `86 904` clauses, `20 350` XOR pour TYPE_1 à 204 tirages ; CMS
n'a pas répondu en `300` s, sur le planté comme sur le contrôle, et CaDiCaL
(`233 424` clauses, XOR développés) a épuisé un budget de trois millions
de conflits sans répondre, `1 825` s sur le planté et `1 505` s sur le
contrôle — là où l'énumération à trois plans répond en trois secondes. La
raison est celle
du 7.7 : une contrainte d'appartenance ne propage rien avant que les deux
antécédents ne soient fixés, et le solveur ne « voit » pas que trois plans
devinés rendent le reste linéaire — il faut le lui dire, et le lui dire,
c'est l'algorithme ci-dessus.

**Ce qui reste fermé — et pourquoi c'est une identification.** Le crible
à trois plans rend `r mod 32` ou `r mod 128` : `5L` ou `7L` bits sur `32L`.
Sous le tirage par modulo au pas constant, le relèvement du 7.8 n'existe
pas — la chaîne mod 5 lit `v − 1 = 16 (H mod 5) + q`, ce que le
Fisher-Yates ne publie pas. Les contraintes exactes du relèvement sont
pourtant écrites par le lemme gradué : pour chaque mot `k ≤ 19` de chaque
tirage, `x_k mod (80 − k) ∈ {v − 1 − k}` — vingt congruences à modules
mixtes (`80, 79, …, 61`), `≈ 2` bits chacune, `≈ 40` bits par tirage pour
`32L` bits d'état plus un bit de débordement par mot. En information, huit
tirages suffiraient à TYPE_1, trente à TYPE_2. Mais un résidu mod `79`
n'est pas un plan de bits, les ensembles permis ne sont pas des intervalles
(pas de CVP), et le passage de `r mod 128` à `r mod 2^32` par ces
congruences est une programmation dynamique à modules mixtes que le
dossier **n'a pas développée** : c'est la frontière nouvelle, au-dessus
de l'identification. Sous le **rejet**, le filtre des classes vides
(`0,0012`–`0,0056` par mot) est trop faible pour fixer l'alignement des
mots perdus : le crible à cinq plans du 7.9, qui branche sur `σ`, reste
l'outil, et un crible à trois plans avec un Gauss par alignement est une
extension non écrite.

> Le 7.10 déplace la frontière du 7.8 de `2^{5L}` à `2^{3L}` : trois plans
> devinés, les autres résolus sur `F₂^L` par les mots sûrs, et le mot 16 lu
> mod 64 publie deux bits par tirage. TYPE_1 était exclu, il le reste par
> corollaire ; TYPE_2 devient un calcul d'une heure de carte graphique ou
> de deux cents jours de cette machine — une **identification**, `7L` bits
> sur `32L`, sans relèvement ni prédiction tant que les congruences à
> modules mixtes du lemme gradué n'ont pas leur algorithme ; TYPE_3 reste
> hors de portée par le coût, non par l'information.

---

### 7.11 Le flux continu (§157) — un plan deviné au lieu de trois, `2^L` au lieu de `2^{3L}`, et les 70 560 tirages comme une seule lecture

Le 7.10 devine **trois** plans parce qu'une fenêtre de 204 tirages ne dit
presque rien des plans 1 et 2 : le plan 1 y est forcé une fois sur dix
millions, le plan 2 trois fois. Mais la fenêtre est un choix, pas une
donnée. L'archive a `70 560` tirages en `346` journées séparées par `345`
pauses nocturnes (`343` de `25 500` s), coupées par `24` sauts de quelques
secondes en `370` blocs de cadence ; si le générateur est **réensemencé**
chaque matin, chaque journée est une fenêtre et le 7.10 est le bon outil ;
s'il ne l'est **jamais** — un seul flux, lu à pas constant `S` à travers les
pauses, ce que fait tout processus qui tourne sans redémarrer — alors le
tirage `t` lit les mots `x_{S·t+k}` du **même** état, et les `70 560`
tirages sont `70 560` lectures d'un seul état de `32L` bits. C'est
l'**hypothèse du flux continu**, et sous elle les plans 1 et 2 reçoivent
assez d'équations pour n'être plus devinés. Le théorème qui suit ramène le
coût de `2^{3L}` à `2^L` — pour TYPE_2, de `2^{45}` à `2^{15}` — au prix
d'une linéarisation cubique.

**Ce que l'archive triée publie, mot par mot.** Le lemme gradué du 7.10
donne `x_k mod 2^{e_k}` contraint aux mots `k = 0, 4, 8, 12, 16` avec `e =
4, 2, 3, 2, 6` (mots 4 et 12 : `76 = 4·19`, `68 = 4·17`). Sous
`Collections.shuffle` lu par ses vingt dernières cases, le mot `k` sert la
case `i = 79 − k` et `x_k mod (i+1)` est contraint de même, aux mêmes cinq
mots. Chaque contrainte est un **masque** : l'ensemble des résidus
`mod 2^e` permis par le tirage. Le plan 0 de `r` n'est pas publié
(`x = r >> 1`) ; le bit 0 de `x` est le **plan 1** de `r`, le bit 1 son
**plan 2**. Deux événements, par (tirage, mot, parité `a` du bit 0 de `x`) :

    MORT    aucun résidu permis n'a la parité a        →  bit 0 de x ≠ a
    FORCE   tous les résidus permis de parité a ont     →  (bit 0 de x = a) ⇒ (bit 1 de x = f)
            le même bit 1, égal à f

La MORT est une classe entière (une parité, `2^{e−1}` résidus, `n_k/2`
numéros) absente du tirage : `2·hyp(40) = 7,8·10^{−8}` au mot 0, `9,5·10^{−6}`
au mot 16 — jamais, ou presque. La FORCE est un **quart** de classe absent :
`4·hyp(20) = 0,0047` au mot 0, `0,0071` (mot 4), `0,0104` (mot 8),
`0,0153` (mot 12), `0,0222` (mot 16) — **`0,0597` par tirage**, `3 577`
sur les `60 000` premiers tirages de l'archive (`0,0596`), `4 244` sur un
flux planté de `70 560`. Pour le **vrai** état la FORCE est toujours
satisfaite (son résidu est permis, donc de la bonne parité et du bon bit 1)
; pour un faux, c'est une équation au hasard.

> **Théorème du flux continu.** *Soit `r_i = r_{i−K} + r_{i−L} mod 2^32`,
> et `p^b_i` le plan `b` de `r_i`. Le plan 0 des `L` mots initiaux étant
> fixé (`2^L` hypothèses), le plan 0 de tout mot est connu, et, notant
> `y, z ∈ F₂^L` les plans 1 et 2 des mots initiaux :*
>
>     p^1_i = ⟨α_i, y⟩ ⊕ δ_i
>     p^2_i = ⟨α_i, z⟩ ⊕ Q_i(y),      Q_i quadratique en y,
>
> *avec, pour `a = i − K`, `b = i − L`, `c^1_i = p^0_a p^0_b` :*
>
>     α_i = α_a ⊕ α_b,   δ_i = δ_a ⊕ δ_b ⊕ c^1_i,
>     Q_i = Q_a ⊕ Q_b ⊕ ⟨α_a,y⟩⟨α_b,y⟩ ⊕ δ_b⟨α_a,y⟩ ⊕ δ_a⟨α_b,y⟩ ⊕ δ_a δ_b
>                       ⊕ c^1_i (⟨α_a ⊕ α_b, y⟩ ⊕ δ_a ⊕ δ_b).
>
> *Un événement MORT au mot `i` est l'équation **linéaire** `⟨α_i, y⟩ =
> δ_i ⊕ a ⊕ 1` ; un événement FORCE est l'équation **cubique**
> `(⟨α_i,y⟩ ⊕ δ_i ⊕ a ⊕ 1)·(⟨α_i,z⟩ ⊕ Q_i(y) ⊕ f) = 0`, de degré 3 en `y`,
> 1 en `z`, 2 en `(y,z)`. Linéarisées sur les monômes `{y_j, z_j, y_j y_k,
> y_j z_k, y_j y_k y_l, 1}`, ces équations sont un système sur*
>
>     M(L) = 2L + C(L,2) + L² + C(L,3) + 1      (120, 220, 816, 1 140 pour L = 7, 9, 15, 17)
>
> *inconnues, que le vrai plan 0 satisfait et qu'un faux contredit dès que
> le nombre d'équations dépasse le rang.*
>
> *Preuve.* Le plan 1 est le théorème du 7.10 avec `p = 1` : la retenue
> `c^1_i` ne dépend que du plan 0, connu. Le plan 2 : la retenue sortant des
> deux bits bas de `r_a + r_b` est `c^2_i = p^1_a p^1_b ⊕ c^1_i (p^1_a ⊕
> p^1_b)` ; on y substitue `p^1 = ⟨α, y⟩ ⊕ δ`, et `p^2_i = p^2_a ⊕ p^2_b ⊕
> c^2_i` se propage par récurrence : la partie en `z` est linéaire de
> matrice `α` (même LFSR), le reste est `Q_i`, quadratique en `y` puisque
> `c^2_i` l'est et que la récurrence est additive. Les événements sont la
> définition des masques. La linéarisation est le remplacement de chaque
> monôme par une inconnue ; les monômes possibles d'un produit (affine en
> `y`) × (affine en `z`, quadratique en `y`) sont ceux listés. ∎

Le mot 0 du tirage `t` est le mot `S·t` du flux ; le pas `S` et le schéma
(`fy` : Fisher-Yates partiel, mots `0..19`, `S = 20..24` avec des mots
perdus, `79..80` pour un shuffle complet lu par ses vingt **premières**
cases ; `shuffle` : `Collections.shuffle` lu par ses vingt **dernières**,
`S = 79..80`) sont des paramètres du crible, et tout décalage constant du
flux est absorbé par l'état initial : la **place** des mots perdus dans un
pas est sans objet. Deux sorties : `x = r >> 1` (glibc, plan 0 muet) et
`x = r` (« shift 0 » : le plan 0 est publié, la MORT tue directement et la
FORCE est linéaire en `y` — le crible est alors un Gauss sur `L` bits, et
`2^L` hypothèses coûtent quelques secondes à `L = 17`).

**Le rang, mesuré.** Le système linéarisé n'est pas de rang plein — les
monômes sont plus nombreux que les degrés de liberté du problème (`2L`) —
et c'est le rang qui fixe le nombre d'événements nécessaires. Prototype
(`proto137`, pas 20, `x = r >> 1`, flux planté) :

| `L` | `M` | rang | y lu | z lu | faux plan 0 contredit à l'équation |
|---|---|---|---|---|---|
| 9 | 220 | 117 | oui | — | rang + 1..3 |
| 15 | 816 | 710 | oui | oui | `711`, `712`, `711` sur `1 246` |
| 17 | 1 140 | 1 003 | oui | oui | `1 005`, `1 002`, `1 004` sur `2 486` |

Le vrai plan 0 n'est jamais contredit et les colonnes `y` (puis `z`) sont
**triangulaires** dans la réduction : `y` est lu bit par bit, `z` aussi à
`L ≥ 15`, bien que `137` monômes restent libres à `L = 17` — les degrés de
liberté résiduels sont dans les monômes cubiques, pas dans les inconnues.
Un faux plan 0 meurt **une à trois équations après le rang** : il faut
`≈ R(L) + 3` événements, soit `R/0,0597` tirages — `16 800` à `L = 17`,
`12 000` à `L = 15`. Le flux continu est nécessaire : une fenêtre de 204
tirages (`12` événements) ne fait rien, et même une journée n'y suffit pas.
Sur 60 000 tirages l'archive fournit `3 577` événements ; le plafond de la
linéarisation est `M(L) ≤ 3 577`, soit **`L ≤ 25`** (`M(25) = 3 276`,
`M(26) = 3 654`). TYPE_3 (`L = 31`, `M = 5 984`) est **hors du plafond** :
sur cette archive, la linéarisation ne ferme pas à `L = 31`, quel que
soit le coût par hypothèse (il faudrait `100 000` tirages, ou une
relinéarisation qui exploite la structure creuse — non écrite).

**L'algorithme (`tools/lfg_flux_continu.c`).** Les `2^L` plans 0 sont
parcourus par **blocs de 64** en tranches de bits (bit-slicing) : un mot de
64 bits porte le plan 0 de 64 hypothèses, et la récurrence `p^0_i = p^0_a
⊕ p^0_b`, `c^1_i = p^0_a ∧ p^0_b`, `δ_i = δ_a ⊕ δ_b ⊕ c^1_i` et la partie
**dépendante** de `Q_i` (linéaire en `y` plus constante — la partie
`⟨α_a,y⟩⟨α_b,y⟩`, indépendante de l'hypothèse, est précalculée une fois) se
propagent en trois opérations par mot. Aux positions des événements
(précalculées, `≈ 0,06` par tirage) chaque hypothèse du bloc reçoit sa
ligne — `M` bits, construite à partir de tables fixes (`FIX1`, `FIX2`, `T`
: les contributions de `α_i`, de `Q^{yy}_i`, de `f`) et des trois quantités
de l'hypothèse (`δ_i`, `Q^{dep}_i`) — et un **Gauss incrémental** par
hypothèse (pivot = monôme de tête, la constante exclue : une ligne réduite
à `1 = 0` est la contradiction). L'hypothèse morte cesse d'exister ; le
bloc s'arrête quand ses 64 hypothèses sont mortes, en général vers le
tirage `17 000` à `L = 17`, sans engendrer le reste du flux. Une hypothèse
vivante au bout de `N` tirages a ses colonnes `y` triangulaires ; `y` est
lu, les bits libres énumérés (au plus `2^{12}`, sinon **indécis**, compté),
et l'état `r mod 4` est **relevé** plan par plan jusqu'au plan `5 + shift`
par le principe du 7.10 (Gauss sur `L` bits avec retenues exactes, masques
pliés `mod 2^{p+1}`), puis **vérifié** par simulation mot par mot sur les
`N` tirages. Sortie : `r_0..r_{L−1} mod 2^{6+shift}`.

Mesuré (autotest, machine à quatre cœurs chargée par deux autres
balayages, deux fils) : TYPE_1 `60 000` tirages `0,2` s ; `(4, 9)` shuffle
pas 79 `0,9` s ; TYPE_2 pas 21, `20 000` tirages, `29,5` s pour `2^{15}` ;
`(3, 17)` pas 20, `70 560` tirages, **`270` s pour `2^{17}`** — `≈ 4`
ms par hypothèse et par cœur à `L = 17`, contre `2^{2L}` fois plus
d'hypothèses à `5` µs pour les trois plans du 7.10. L'état planté ressort
**seul**, avec `0` indécis, et un flux de tirages aléatoires ne rend rien,
sous `fy` et `shuffle`, shift 1 et 0. Coût de l'archive entière — `31`
trinômes primitifs `L ≤ 17` (`13` de degré `≤ 7`, `2` de degré `9`, `10`,
`11`, `6` de degré `15` et `17`), `9` variantes (`fy` pas `20..24, 79, 80`
; `shuffle` pas `79, 80`), `2` shifts, **`558` cribles** : `≈ 10^7`
hypothèses à `≤ 4` ms, `≈ 5` heures sur deux cœurs.

**Ce que ça change, et ce que ça ne change pas.** Le 7.10 laissait TYPE_2
à `2^{45}` — quatre à cinq années-cœur, « hors de ce dossier ». Sous le
flux continu c'est `2^{15}` hypothèses et **une minute**. Le prix est une
hypothèse de plus — pas de réensemencement — mais elle est la plus
naturelle de toutes : un service qui tourne. Le crible rend l'état **bas**
(`6` ou `7` bits par mot) : c'est encore une identification, et le
relèvement à `32L` bits sous le modulo reste la frontière du 7.10 (les
congruences à modules mixtes, sans algorithme). Un survivant aurait
pourtant déjà un pouvoir prédictif **testable** : `r mod 2^{6+shift}` est
autonome, donc les résidus `x_k mod 2^{e_k}` de **tous** les tirages futurs
sont connus — cinq numéros candidats pour le premier tiré, quatre
numéros exclus sur cinq au mot 16 (`x_{16} mod 64` connu, `j_{16}` connu,
mais le contenu de la case dépend des mots hauts) — et c'est ce que le §157
vérifie sur `10 560` tirages retenus. Restent hors du crible : TYPE_3 et
TYPE_4 (plafond de linéarisation **et** `2^{31}`, `2^{63}` hypothèses) ; le
**rejet** (pas variable : l'alignement des mots n'est plus une constante
absorbée par l'état) ; la troncature ; les vingt premières cases d'un
shuffle ; le Fibonacci **soustractif** ; et, bien sûr, le réensemencement
quotidien — sous lequel le 7.10 reste le seul outil, à son prix.

**Résultat (h137, RAPPORT §157).** Le crible a tourné sur l'archive :
`31` trinômes primitifs de degré `L ≤ 17` (TYPE_1 `(3, 7)` et TYPE_2
`(1, 15)` compris), `9` variantes (fy à pas `20`–`24`, `79`, `80` ;
shuffle à pas `79`, `80`), shifts `0` et `1` — `558` cribles, `2^L`
hypothèses de plan 0 chacun, plans 1–2 par linéarisation cubique sur
`10 560` tirages retenus. **Zéro survivant, zéro indécis**, six témoins
plantés retrouvés seuls dans le régime de l'archive (`L = 7, 9, 15, 17`,
shifts `0` et `1`). Verdict conforme, jeton `a0905869bb411907`, `14 728` s
de crible. Sous le flux continu, TYPE_1 et TYPE_2 sont **exclus** de
l'archive pour ces échantillonneurs à pas fixe. Le troisième
échantillonneur à vingt mots — le retrait par échange avec le dernier,
dont le masque est celui du shuffle — a été criblé aux pas `20`–`24` par
h138 (§158, jeton `71fff0fc2e5270dc`) : `310` cribles, `0` survivant,
`0` indécis, quatre témoins retrouvés seuls, `19 499` s ; avec le §157,
`868` cribles sous onze schémas à pas fixe, aucun état. Le pas variable
(rejet) reste hors des cribles exacts du flux continu.

---

### 7.12 Le relèvement sous le flux continu : les équations exactes, le bit de débordement, et le compte — sans algorithme sur l'archive triée, un algorithme sur les tirages ordonnés

Le crible du 7.11 rend `r mod 2^m` pour tous les mots (`m = 6 + shift`),
autonome par la récurrence ; il reste `32 − m` bits par mot initial. Cette
section écrit exactement ce que l'archive triée dit de ces bits, et
pourquoi quatre des cinq voies naturelles — les décompositions de la
récurrence — n'en font pas un algorithme : c'est la frontière du 7.10,
mise en équations. La cinquième, le réseau des tirages **ordonnés**, en
est un, et il est mis en machine et mesuré (TYPE_1 à cinq tirages, TYPE_2
à huit) : ce qui manque à l'archive n'est pas l'information, c'est
l'ordre.

**Les inconnues.** Posons `r_i = ℓ_i + 2^m h_i`, `ℓ_i ∈ [0, 2^m)` connu,
`h_i ∈ [0, 2^{32−m})` inconnu. La récurrence `r_i = r_a + r_b mod 2^32`
(`a = i − K`, `b = i − L`) se coupe en deux :

    ℓ_a + ℓ_b = ℓ_i + 2^m κ_i,                     κ_i ∈ {0, 1} connu (retenue basse)
    h_i = h_a + h_b + κ_i − 2^{32−m} c_i,          c_i ∈ {0, 1} inconnu (débordement)

où `c_i = [h_a + h_b + κ_i ≥ 2^{32−m}]` est le **bit de débordement** de
l'addition 32 bits : une inconnue binaire par mot engendré, déterminée par
les bits hauts. Sur `Z/2^{32−m}` la seconde ligne est affine et exacte —
`h_i = ⟨F_i, H⟩ + g_i mod 2^{32−m}` avec `F` la matrice du Fibonacci sur
l'anneau et `g` la récurrence des `κ` — mais c'est l'**entier** `h_i` que
l'observation contraint, et l'entier s'écrit `⟨F_i, H⟩ + g_i − 2^{32−m}
N_i` avec `N_i = N_a + N_b + c_i` le quotient accumulé, qui croît comme
`Σ_j |F_{ij}|`, c'est-à-dire comme `ρ^i` (`ρ` racine de `x^L − x^{L−K} −
1`, `1,15` pour TYPE_2, `1,16` pour TYPE_1, `1,06` pour TYPE_3) : au-delà de quelques dizaines de mots, `N_i` a
autant de bits que `h_i`.

**Les observations.** Le lemme gradué donne, pour le mot `k` du tirage
`t`, `x mod n_k ∈ A_{t,k}` avec `n_k = 80 − k = 2^{e_k} o_k` et `A_{t,k} =
{v − 1 − k : v tiré, v ≥ k + 1}`. La partie `2^{e_k}` est acquise (`x mod
2^{e_k}` se lit dans `ℓ` puisque `m − shift = 6 ≥ e_k`) ; elle réduit
`A_{t,k}` aux candidats `v` de la bonne classe `mod 2^{e_k}`, et la partie
**impaire** reste : avec `x_i = (ℓ_i ≫ shift) + 2^{m−shift} h_i` et
`2^{m−shift}` inversible modulo `o_k`,

    h_i mod o_k ∈ B_{t,k},     |B_{t,k}| ≈ (20 − k/4) / 2^{e_k}

Les modules impairs sont `o = 5, 79, 39, 77, 19, 75, 37, 73, 9, 71, 35,
69, 17, 67, 33, 65, 1, 63, 31, 61` pour `k = 0..19` : le mot 16 (`o = 1`)
ne dit plus rien, les dix-neuf autres disent chacun `log₂(o_k/|B_{t,k}|)
≈ 2` bits — au mot 0, `1,25` candidats en moyenne parmi `5` résidus, et
`40 %` des tirages (`5·C(75,19)/C(80,20)`) n'en ont qu'**un** : `r_{S·t}
mod 5` y est **exact**. Total : **`≈ 38` bits par tirage** sur les bits
hauts, contre `S = 20` bits de débordement nouveaux par tirage et `(32 −
m) L` bits d'état. Le compte ferme : `(32 − m)L / 18` tirages — **dix**
pour TYPE_1, **vingt et un** pour TYPE_2 (`m = 7`), **quarante-trois** pour
TYPE_3 — et l'archive en a soixante mille. L'information est là, en
excès d'un facteur mille.

**L'identité du débordement.** Modulo tout `q` divisant `2^32 − 1` (`3, 5,
17, 257, 65 537` et leurs produits), `2^32 ≡ 1`, et la récurrence entière
`r_a + r_b = r_i + 2^32 c_i` devient

    c_i ≡ r_a + r_b − r_i   (mod 255)

le bit de débordement **est** l'écart de la récurrence modulo `255`. Si
`r mod 5` était connu à tous les mots, chaque `c_i` se lirait ; il n'est
connu, et partiellement, qu'au mot `0` de chaque tirage — un mot sur `S`.

**Pourquoi les cinq voies échouent, par le compte.**

1. *Plans montants* (7.10, 7.11) : exacts et sans inconnue par mot — mais
   une observation `h mod o_k` avec `o_k` impair n'est fonction d'**aucun**
   nombre de plans bas inférieur à tous : les plans `≥ 7` ne reçoivent
   aucune équation avant le dernier, et le crible est `2^{(32−m)L}`.
2. *Plans descendants* : `T` plans hauts devinés (`2^{TL}`) fixent `c_i`
   sauf au bord (`2^{−T}`), mais le plan haut de `h_i` reçoit une retenue
   **entrante** des bits du milieu, inconnue : une inconnue binaire par mot,
   et l'erreur se propage par `F` comme une marche aléatoire.
3. *Débordements devinés* : `c` fixé sur une fenêtre de `W` mots rend `h_i`
   affine **sur `Z`** et chaque observation une congruence linéaire
   `⟨F_i, H⟩ ≡ b − g_i + 2^{32−m} N_i (mod o_k)`, `b ∈ B_{t,k}` — un réseau
   d'indice `Π o_k`, un point dans la boîte dès `W ≈ (32 − m) L / 2` :
   mais `2^W · Π |B_{t,k}|` choix, `≈ 2^{190} · 10^{190}` pour TYPE_2.
4. *Chaîne modulo 5* : `L` symboles initiaux (`5^L`) et un `c_i` par mot
   contre `2` bits d'observation au mot 0 par tirage : `20` inconnues
   binaires pour `2` bits, à chaque tirage. C'est ici que le 7.8 **ne se
   transporte pas** : sous le rejet, le modulo est `80` à *tous* les mots,
   la chaîne mod 5 est observée à chaque mot, le débordement s'y **lit**
   (`w ≡ 2(ρ_a + ρ_b + κ − ρ_i) mod 5`) et la programmation dynamique à
   paquets tient en `5^L` états ; sous le modulo décroissant, la chaîne
   mod 5 n'est observée qu'un mot sur vingt, et les chaînes mod `79`, `39`,
   `77`, … ne le sont chacune qu'une fois par tirage — leur état joint est
   `r mod lcm(o_k)`, un modulo de `71` bits, c'est-à-dire l'état entier.
5. *Tirages ordonnés* (vidéos) : le résidu `x_k mod (80 − k)` est **exact**
   à chaque mot, le choix `b ∈ B` disparaît, et le problème devient un
   réseau — `(H, c) ∈ Z^{L+20T}` sous `≈ 100` bits de congruences exactes par
   tirage (`Σ_k log₂ o_k = 100,7` ; `122,7` si l'on ne fixe que le plan 0,
   `m = 1`), unique dès `T ≥ 25L/80` tirages, cinq pour TYPE_2. Mais les `c` centrés pèsent autant que les `H` centrés
   (`2^{24}` chacun après mise à l'échelle) : la solution n'est plus courte
   que l'heuristique gaussienne que d'un facteur `1,2` à `T = 5`, `4` à
   `T = 10`, `8` à `T = 20`, `11` à `T = 40`, en dimension `115`, `215`,
   `415`, `815` — un plus-court-vecteur unique à écart presque constant en
   dimension croissante. Ce n'est pas le CVP du 7.8, où les `c` sont lus
   dans la chaîne et n'entrent pas dans le réseau. Cette voie-là est la
   seule des cinq qui soit un **algorithme**, et elle est mise en machine
   (`lab/reseau_ordonne.py`, ci-dessous) : elle ne s'applique qu'à des
   tirages ordonnés, que l'archive n'a pas.

**La voie 5 en machine : le réseau des tirages ordonnés.** Le module
`lab/reseau_ordonne.py` construit le réseau du point 5 pour un `m` quelconque
— inconnues `(H, c, z)`, coordonnées centrées `(2H − 2^{32−m} z, 2^{33−m} c −
2^{32−m} z, 2^{32−m} z)`, congruences `2^{m−1}(⟨A_i, H⟩ + ⟨C_i, c⟩ + g_i) ≡
j_k − (ℓ_i ≫ 1) (mod 80 − k)`, c'est-à-dire `h_i` modulo `q_k = (80 − k) /
2^{min(m−1, e_k)}`, imposées par LLL à poids, plongement de Kannan en `z` —
puis le réduit (LLL, BKZ progressif) et régénère l'état à partir de toute
ligne de coordonnée `z = ±2^{32−m}`. Avec `m = 7` (le crible du 7.11 donné),
`q_k = o_k` et le réseau reçoit `100,7` bits par tirage ; avec `m = 1` (le seul
plan 0 donné), `q_k = 80 − k` entier et il en reçoit **`122,7`** — l'écart à
l'heuristique gaussienne y est plus grand (`3,9` contre `2,8` pour TYPE_2 à
`T = 8`), et `m = 1` est la bonne formulation. Trois faits, tous vérifiés sur
données plantées :

- *Le réseau a des parasites plus courts que la cible.* Pour chaque mot
  initial `r_j`, `r_j + 2^{32}` ne change rien modulo `2^{32}` : `(H_j,
  c_{j+L}) → (H_j − 2^{32−m}, c_{j+L} − 1)` (et `c_{j+K} − 1` aussi si `j ≥ L −
  K`) est une symétrie exacte, un vecteur de norme `2^{33,5−m}` ou `2^{33,8−m}`
  contre `2^{35,7−m}` pour la cible ; le débordement du mot 16 du dernier
  tirage (`o = 1`) se confond de même avec celui du mot 19 quand `m > 1`.
  `L + 1` parasites : la cible n'est pas le plus court vecteur, elle est le
  plus court de sa classe `z = ±1` modulo les parasites, et le décodeur ne lit
  que `H mod 2^{32−m}` avant de vérifier par régénération.
- *Le plan 0 se lit sans crible.* Le plan 0 de `r` n'apparaît jamais dans
  `x = r ≫ 1`, mais il commande les retenues du plan 1, qui est le bit 0 de
  `x`, observé **exactement** aux dix mots pairs de chaque tirage ordonné
  (`e_k ≥ 1`). Pour chacun des `2^L` plans 0, le plan 1 est affine en ses `L`
  bits initiaux : `10 T` équations sur `GF(2)`, une élimination de Gauss —
  un survivant sur `2^7` pour TYPE_1 à `T = 5`, un sur `2^{15}` pour TYPE_2 à
  `T = 8`, en une seconde. C'est le plan 0 du 7.11 sans la linéarisation
  cubique, parce que l'ordre rend le bit exact au lieu d'un masque. Mieux :
  la constante `δ_i(p)` du plan 1 est une forme **quadratique** en `p`
  (`Γ_i = Γ_{i−K} ⊕ Γ_{i−L} ⊕ α_{i−K} ⊗ α_{i−L}`), et le noyau à gauche des
  `n` équations en `y` donne `n − L` conditions `Q_λ(p) = ⟨λ, obs⟩` qui ne
  portent que sur `p` : leur table de vérité sur les `2^L` plans 0 se
  construit en `2^L` opérations par doublement (la restriction à `p_a = 1`
  est la table à `p_a = 0` XOR une forme linéaire), soixante-quatre formes à
  la fois sur `uint64`, `2^{31}` points par tranches de `2^{22}`. Le crible
  du plan 0 est alors un calcul et non une énumération de Gauss, et `(3,
  31)` y passe en neuf secondes — c'est le crible de `h139` (§159) : douze
  tirages ordonnés, `32` trinômes TYPE_3 compris, deux échantillonneurs,
  sept pas, deux shifts, deux ordres, `5 264` cellules exactes.
- *Le compte est le bon, et le bloc mesuré est plus petit que le bloc
  calculé.* TYPE_1 `(3, 7)`, tirages ordonnés à pas `20`, chaîne complète
  (plan 0 par crible linéaire, `m = 1`, LLL seul) : **cinq tirages** rendent
  l'état exact et le sixième tirage en `9 s` (graines 2, 3, 4) ; avec `ℓ = r
  mod 2^7` donné, cinq tirages LLL `10 s`, six tirages LLL `18 s`, huit
  tirages BKZ-30 `57 s`, écart mesuré à `T = 8` `6,6` pour `6,8` calculé.
  TYPE_2 `(1, 15)`, `ℓ = r mod 2^7` donné, **huit tirages** : état exact et
  neuvième tirage prédit par **BKZ-50** en `122 s` (graine 1), là où
  l'estimation usuelle (`√(β/n)·‖v‖ ≤ δ_β^{2β−n−1}·vol^{1/n}`) demandait `β ≈
  76`. Chaîne complète à `m = 1`, **huit tirages ordonnés et rien d'autre** :
  plan 0 par le crible linéaire, un survivant sur `2^{15}` en `1 s`, puis
  état exact et neuvième tirage prédit par BKZ-60 en `316 s` et `322 s`
  (graines 1, 2) et par BKZ-50 en `130 s` (graine 3) — trois réussites sur
  trois, pour `β ≈ 56` calculé.
  La même estimation donne, avec `m = 1`, `β ≈ 56–58` pour TYPE_2 à `T = 8–10`
  et `β ≈ 164` pour TYPE_3 à `T = 15` (`≈ 2^{64}` par crible) : même corrigée
  du facteur mesuré sur TYPE_2, TYPE_3 reste hors de portée de cette machine,
  et au-delà de `T ≈ 12` l'écart croît moins vite que la dimension et le bloc
  requis remonte.

La chaîne complète — plan 0 par `2^L` éliminations linéaires, bits hauts par
le réseau à `m = 1` — est donc un **algorithme** pour TYPE_1 (cinq tirages,
dix secondes) et TYPE_2 (huit tirages, deux à cinq minutes) sous le flux
continu,
**à la condition de connaître l'ordre des tirages**. L'archive donne les
tirages triés ; c'est exactement ce que les points 1 à 4 ne savent pas
surmonter : sans l'ordre, `j_k` n'est plus exact mais un ensemble `B_{t,k}`,
le bit 0 de `x` n'est plus lu qu'à travers un masque, et le réseau perd ses
congruences. Appliquée aux douze tirages ordonnés des vidéos (§159), la
première moitié de la chaîne — le crible exact des plans bas, `5 264`
cellules : `32` trinômes TYPE_3 compris, deux échantillonneurs, sept pas,
deux shifts, deux ordres, en flux continu ou avec réamorçage journalier —
ne rend **aucun** survivant, avec dix-neuf témoins plantés retrouvés : sur
les vidéos, le réseau n'a rien à relever, et la conclusion du §154 (sous
le rejet) s'étend au pas constant.

Ce que le 7.7, le 7.10 et le §153 ont vu du solveur générique est le même
mur sous un autre nom : une appartenance `h mod 79 ∈ B` ne propage rien
tant que `h` n'est pas entier, et `h` n'est entier qu'avec ses
débordements. Le relèvement sous le flux continu est donc un problème
**exactement posé** — `(32 − m) L` inconnues entières bornées, un bit de
débordement par mot lié aux bits hauts par une inégalité, `≈ 400`
congruences à dix-neuf modules mixtes sur vingt et un tirages — dont le compte
ferme d'un facteur mille et dont l'algorithme manque **sur l'archive
triée**. Une identification du 7.11 en resterait une, avec cinq candidats
sur le premier numéro tiré ; la prédiction complète des tirages passe par
cette porte, et sur l'archive elle n'est pas ouverte. Sur des tirages
ordonnés elle l'est — cinq tirages pour TYPE_1, huit pour TYPE_2, l'état
entier et le tirage suivant en minutes — et les douze que l'on a disent
non.

### 7.14 Les relations de poids 3 sur `Z/4` (§162) — le plan 1 sans deviner le plan 0 : TYPE_3 à shift 1 en `2^{31}` au lieu de `2^{62}`

Le 7.13 s'arrête devant une porte : à shift 1 (`x = r >> 1`, la
`random()` de la glibc), le bit publié par chaque mot pair est le **plan 1**
de `r`, et le plan 1 n'est pas linéaire dans l'état — il porte les retenues
du plan 0. Décoder le plan 1 par la transformée de Walsh–Hadamard du 7.13
exigeait de **deviner le plan 0** (`2^L` hypothèses) et, pour chacune, de
décoder le plan 1 (`2^L`) : `2^{2L}`, soit `2^{62}` pour TYPE_3 — hors de
portée, et c'est la case que le §160 laisse ouverte. Cette section la
ferme. L'idée est de ne jamais deviner le plan 0 : sur `Z/4`, le plan 1
est **linéaire dans le plan 1 de l'état et quadratique dans son plan 0**,
et sur trois positions bien choisies la partie linéaire s'annule
exactement. Ce qui reste est une fonction du seul plan 0 — `2^{31}` états —
dont le signe, pour un état candidat, est une somme de quatre caractères :
la statistique de vraisemblance sur **toutes** les hypothèses de plan 0 est
de nouveau une seule transformée de Walsh–Hadamard, et le plan 1 suit
linéairement une fois le plan 0 connu.

La section établit (i) l'algèbre des deux plans bas sur `Z/4` — le lemme
des plans, avec sa preuve ; (ii) le théorème des relations de poids 3 et
l'énumération par le logarithme de Zech ; (iii) la statistique, l'identité
qui la rend transformable, sa variance nulle **exacte** et indépendante de
l'état, la condition (une relation par triple de tirages) qui la garantit,
le `z` attendu ; (iv) le cas `L > 28` par un `χ²` par morceaux ; (v) le
plan suivant, la cohérence, et le shift 0 comme cas particulier ; (vi) le
coût et les témoins ; (vii) ce qui reste hors de portée. Le résultat sur
l'archive est au §162.

**(i) Le lemme des plans.** Soit `r_i = r_{i−K} + r_{i−L} mod 2^{32}`,
`p ∈ F₂^L` le plan 0 des `L` mots initiaux, `y ∈ F₂^L` leur plan 1, et
`r⁰_i, r¹_i` les plans 0 et 1 de `r_i`. Mod 4, l'addition s'écrit

    r⁰_i = r⁰_{i−K} ⊕ r⁰_{i−L},        r¹_i = r¹_{i−K} ⊕ r¹_{i−L} ⊕ (r⁰_{i−K} ∧ r⁰_{i−L})

— le terme `∧` est la retenue du bit 0. Le plan 0 est l'`m`-suite du trinôme
`(K, L)` — `x^L + x^K + 1` dans la notation du 7.7, `x^L + x^{L−K} + 1` pour
son polynôme caractéristique, la même suite : `r⁰_i = <α_i, p>` avec
`α_i = e_i` (`i < L`) et `α_i = α_{i−K} ⊕ α_{i−L}`. Notons `e₂(w) = C(|w|, 2) mod 2 =
(popcount(w) >> 1) & 1` la deuxième fonction symétrique élémentaire des
bits de `w` (la retenue de la somme des bits de `w`).

> **Lemme des plans.** *`r¹_i = <α_i, y> ⊕ <α'_i, p> ⊕ e₂(α_i ∧ p)`, où
> `α'_i = 0` pour `i < L` et `α'_i = α'_{i−K} ⊕ α'_{i−L} ⊕ (α_{i−K} ∧ α_{i−L})`.*
>
> *Preuve.* Pour deux mots `u, v` et `m = |u ∧ v|`,
> `C(|u| + |v| − 2m, 2) ≡ C(|u|,2) + C(|v|,2) + |u||v| + m (mod 2)`
> (développer `(n)(n−1)/2` en `n = |u| + |v| − 2m`), soit
>
>     e₂(u ⊕ v) = e₂(u) ⊕ e₂(v) ⊕ |u||v| ⊕ |u ∧ v|      (mod 2).
>
> Avec `u = α_{i−K} ∧ p`, `v = α_{i−L} ∧ p` : `|u| = <α_{i−K}, p>`,
> `|v| = <α_{i−L}, p>`, `u ∧ v = (α_{i−K} ∧ α_{i−L}) ∧ p`, `u ⊕ v = α_i ∧ p`,
> donc la retenue `<α_{i−K},p><α_{i−L},p> = e₂(α_i ∧ p) ⊕ e₂(α_{i−K} ∧ p) ⊕
> e₂(α_{i−L} ∧ p) ⊕ <α_{i−K} ∧ α_{i−L}, p>`. Par récurrence sur `i`, la
> partie quadratique `q_i(p)` de `r¹_i` vérifie `q_i = q_{i−K} ⊕ q_{i−L} ⊕
> (retenue)` avec `q_i = 0` pour `i < L` (`e₂(e_i ∧ p) = 0`), d'où
> `q_i = <α'_i, p> ⊕ e₂(α_i ∧ p)` avec la récurrence annoncée pour `α'`. La
> partie en `y` est la même récurrence linéaire que le plan 0. ∎

Vérifié sur `400 077` positions d'un flux planté : `0` violation. Le lemme
dit exactement ce qu'il en coûte de lire le plan 1 : `L` inconnues `y`
linéaires et `L` inconnues `p` **quadratiques** — la forme quadratique
`e₂(α_i ∧ p)` est de rang plein dès que `α_i` a plusieurs bits, et c'est
elle qui interdit une élimination gaussienne directe. Une remarque en
passant : le plan 0 est périodique de période `P = 2^L − 1`, donc
`α_{i+P} = α_i` et `r¹_i ⊕ r¹_{i+P} = <α'_i ⊕ α'_{i+P}, p>` est **linéaire**
en `p` (la partie `y` et le `e₂` s'annulent) ; deux mots à `P` d'écart
suffiraient à lire `p` linéairement. Pour `L ≤ 20`, `P < 1,05·10^6` est plus
court que l'archive sous le flux (`1,41·10^6` positions) ; pour TYPE_3,
`P = 2,1·10^9` ne l'est pas. Il faut annuler `y` autrement.

**(ii) Les relations de poids 3.** Trois positions `a, b, c` sont une
*relation* si `α_a ⊕ α_b ⊕ α_c = 0` — c'est-à-dire `x^a + x^b + x^c ≡ 0
mod (x^L + x^K + 1)`.

> **Théorème des relations de poids 3.** *Si `α_a ⊕ α_b ⊕ α_c = 0`, alors*
>
>     r¹_a ⊕ r¹_b ⊕ r¹_c = <β, p> ⊕ maj(<α_a, p>, <α_b, p>, <α_c, p>),
>     β = α'_a ⊕ α'_b ⊕ α'_c ⊕ maj(α_a, α_b, α_c)      (maj bit à bit)
>
> *— une fonction du seul plan 0.*
>
> *Preuve.* Par le lemme, la partie en `y` vaut `<α_a ⊕ α_b ⊕ α_c, y> = 0`.
> Avec `α_c = α_a ⊕ α_b` et l'identité de `e₂` : `e₂(α_c ∧ p) = e₂(α_a ∧ p)
> ⊕ e₂(α_b ∧ p) ⊕ <α_a,p><α_b,p> ⊕ <α_a ∧ α_b, p>`, donc la somme des trois
> `e₂` vaut `<α_a,p><α_b,p> ⊕ <α_a ∧ α_b, p>`. Enfin, pour `x ⊕ y ⊕ z = 0`,
> `maj(x, y, z) = x ∨ y = x ⊕ y ⊕ xy`, soit `xy = maj ⊕ z` avec `x = <α_a,p>`,
> `y = <α_b,p>`, `z = <α_c,p>` ; et bit à bit, `α_c ⊕ (α_a ∧ α_b) = maj(α_a,
> α_b, α_c)` puisque `α_c = α_a ⊕ α_b`. ∎

Vérifié sur `500 587` relations d'un flux planté : `0` violation. Le
théorème remplace `2^{2L}` par `2^L` : le plan 1 de l'état a disparu, il
ne reste que `p`, et l'observable est **exacte** — pas une approximation
linéaire comme la linéarisation cubique du 7.11, qui devinait un plan pour
linéariser les deux autres.

*Énumération.* Par invariance de translation, `(a, a + d, a + j)` est une
relation pour tout `a` dès que `x^j + x^d + 1 ≡ 0`, c'est-à-dire
`d = Z(j)`, le **logarithme de Zech** de `j` dans `F_{2^L}` (`x^{Z(j)} =
x^j + 1`). L'outil marche `j = 1 … Σ − 1` sur l'étendue `Σ = S(N − 1) + 80 +
L` du flux, lit `d = log(α_j ⊕ 1)` dans une table de hachage des `α_d`,
`d < Σ`, garde `0 < d < j` (triple canonique), puis tout `a` tel que les
trois positions soient des mots pairs observés (`k = 0, 2, …, 18`) de
**trois tirages distincts**. Les couples `(j, d)` sont de deux sortes :
les **structurels** `(j, d) = (L·2^m, (L−K)·2^m)` — la récurrence elle-même,
`α_i ⊕ α_{i−K} ⊕ α_{i−L} = 0`, et ses puissances de deux (Frobenius :
`(u + v)^{2^m} = u^{2^m} + v^{2^m}` dans `F_{2^L}`) — et les **fortuits**,
`Z(j) < Σ` pour un `j < Σ` pris au hasard, au nombre de `≈ Σ²/(2P)` : pour
TYPE_3 sur l'archive `≈ 460` (mesuré `414`), pour `L = 17` tout `j` en
fournit. Chaque couple donne jusqu'à `10 N` triples ; pour un pas `S` pair,
`d` et `j` doivent être pairs (les mots pairs sont aux positions paires) ;
pour `S = 79` chaque décalage tombe sur un mot pair observé avec
probabilité `10/79`. Au plafond `M_max = 2·10^7` la marche s'arrête : les
relations les plus courtes viennent d'abord.

**(iii) La statistique.** Chaque mot pair `(t, k)` livre le bit mou du
7.13, sous la forme `t_{t,k} = (n_0 − n_1)/n ∈ [−1, 1]` — la moyenne a
posteriori de `(−1)^{r¹}` sur l'ensemble trié (`n_0` numéros admissibles
de résidu pair, `n_1` impair). Pour une relation `R = (a, b, c)` et un
état candidat `p`, le signe prédit est `ε_R(p) = (−1)^{<β_R, p> ⊕ maj(…)}` et

    u_R = t_a t_b t_c,        Λ(p) = Σ_R u_R ε_R(p),        z(p) = Λ(p)/√V.

*L'identité.* Pour `x ⊕ y ⊕ z = 0` (et seulement là, ce que le théorème
garantit), `(−1)^{maj(x,y,z)} = ½[(−1)^x + (−1)^y + (−1)^z − 1]` — les
quatre triplets pairs se vérifient. Donc `ε_R(p)` est la somme de **quatre
caractères** de `p`, et

    Λ(p) = Σ_w g[w] (−1)^{<w, p>},   g[β⊕α_a] += u/2,  g[β⊕α_b] += u/2,  g[β⊕α_c] += u/2,  g[β] −= u/2 :

`Λ` sur les `2^L` états est **une** transformée de Walsh–Hadamard de `g`,
en `L·2^L` opérations, après une passe sur les `M` relations. C'est le
même geste qu'au 7.13, mais sur une observable cubique dont on a montré
qu'elle ne dépend que du plan 0.

> **Lemme (variance nulle exacte, indépendante de l'état).** *Sous `H0`
> (l'archive n'a pas de rapport avec l'hypothèse : tirages indépendants,
> `E t_{t,k} = 0`), si deux relations distinctes ne portent jamais sur le
> même triple de tirages, alors pour tout `p` : `E Λ(p) = 0` et*
>
>     Var Λ(p) = V = Σ_R τ₀²(k_a) τ₀²(k_b) τ₀²(k_c),      τ₀²(k) = E₀[t_{t,k}²].
>
> *Preuve.* `E t = 0` est exact : à `k` fixé, la fenêtre `{k+1, …, 80}`
> (FY) ou `{1, …, 80−k}` (shuffle) est de cardinal pair et la réflexion
> `v ↦ 81 + k − v` (resp. `81 − k − v`) la préserve en changeant la parité
> du résidu ; conditionnellement au nombre de numéros du tirage dans la
> fenêtre, ceux-ci sont un sous-ensemble uniforme, invariant par la
> réflexion — donc `E[n_0 − n_1] = 0` (mesuré : `|E₀ t| ≤ 3·10^{−4}` sur
> `400 000` tirages). Les trois positions d'une relation sont dans trois
> tirages distincts, donc `E u_R = 0` et `E u_R² = ∏ τ₀²`. Pour `R ≠ R'`,
> `E[u_R u_{R'}]` est un produit sur les tirages ; un tirage qui ne porte
> qu'un seul des six facteurs contribue `E t = 0`. Comme les triples de
> tirages diffèrent, l'un des deux triples contient un tirage absent de
> l'autre : `E[u_R u_{R'}] = 0`. Les `ε_R(p) = ±1` sont des constantes :
> `Var Λ(p) = Σ_R E u_R² = V` pour tout `p`. ∎

La condition est essentielle et elle n'est pas gratuite : les dix bits mous
d'un même tirage sont corrélés à `0,9` (7.13 (ii) — ils comptent la même
parité du même ensemble), et une relation `(a, b, c)` a neuf sœurs `(a+2m,
b+2m, c+2m)` dans les **mêmes** trois tirages, dont les `u` sont presque
égaux. Les compter toutes donnerait une variance qui dépend de l'état —
la faute du 7.13 (ii) sous une autre forme. L'outil garde, par famille
décalée, celle qui touche le mot `0`, puis une seule relation par triple
de tirages trié (table de hachage des `M` triples). Sous la condition, le
`z` est un `z` pour tout état, et — `u` étant borné — de queue gaussienne :
la borne d'union sur les `2^L` plans 0 donne le seuil

    Z₁ = Φ^{−1}(1 − 10^{−7}/2^L) :    6,88 (L = 15),  7,07 (17),  8,31 (31),

et le maximum nul attendu est `√(2 ln 2^L) ≈ 4,6` (`L = 15`), `6,6`
(`L = 31`) — mesurés `4,4–4,8` et `6,3`. La borne porte sur `2^L` états et
non `2^{2L}` : `y` n'est pas énuméré, il est **déduit**.

*Sous `H1`.* Pour l'état vrai `p*`, chaque relation a le signe prédit :
`u_R ε_R(p*) = ∏ t (−1)^{r¹}`. Le bit mou est la moyenne a posteriori de
`(−1)^{r¹}` sur l'ensemble trié, donc `E[t (−1)^{r¹}] = E[t · E[(−1)^{r¹}
∣ ensemble]] = E[t²] = τ₀²` — la même quantité qui fait la variance nulle.
D'où

    E Λ(p*) = Σ_R ∏ τ₀² = V,        z_attendu = √V ≈ τ₀³ √M,

`τ₀² = 0,038 … 0,050` selon le mot (`k = 0 … 18`, table `CALIB`), soit
`z_attendu ≈ 38` au plafond `M = 2·10^7` et `≈ 15–25` pour `M = 4–8·10^6`.
Mesuré sur flux plantés (`N = 20 000`, `M = 2·10^7`) : `z = 35,0–40,3`
pour `38,0` attendu. La détection est donc à `4,5` écarts-types au-dessus
du seuil au plafond, et la marge reste large tant que `M ≳ 10^6`.

**(iv) `L > 28` : le `χ²` par morceaux.** Le tableau `g` d'un `L = 31` fait
`2^{31}` entiers ; la WHT complète tient en mémoire (`8` Go en `int32`)
mais pas à côté du reste, et surtout la même transformée sert ensuite au
plan `y`. On écrit `w = (w_bas, w_haut)`, `p = (p_bas, p_haut)` avec
`CB = 28` bits bas :

    Λ(p) = Σ_h (−1)^{<h, p_haut>} G_h(p_bas),        G_h = WHT_{CB}(g_h)

— `2^{L−CB} = 8` transformées de `2^{28}` (les tranches `g_h` de bits
hauts `h`). Reconstituer `Λ` pour tous les `p_haut` coûterait `4^{L−CB}`
tranches ; on les combine de façon **incohérente** :

    χ²(p_bas) = Σ_h G_h(p_bas)²,

qui ne dépend pas de `p_haut`. Par Cauchy–Schwarz, `χ²(p*_bas) ≥
Λ(p*)²/2^{L−CB}` : au bon `p_bas`, `χ²/(V/8) ≥ z²` (`≈ 1 440` pour
`z = 38`, `≈ 86` pour `z = 9,3`), contre, ailleurs, une somme de huit
carrés de variance `≈ V/8` dont le maximum sur `2^{28}` valeurs vaut
`≈ 65` (le `256`-ième, `≈ 43`). Le vrai `p_bas` est donc parmi les
`NCAND = 256` premiers avec probabilité `≈ 1` dès `z ≥ Z₁ + 1` ; pour ces
`256` candidats, `Λ(p_bas, p_haut)` est calculé **exactement** pour les
`2^{L−CB}` valeurs de `p_haut` par une passe sur les relations
(histogramme des `u` par motif de Walsh des quatre mots, `2^{L−CB}`
caractères). Le maximum sur ce sous-ensemble est `≤` celui sur `2^L` : le
seuil `Z₁` reste **conservatif** (la borne d'union sur `2^L` majore la
probabilité de fausse détection, quel que soit le sous-ensemble examiné) ;
seule la puissance dépend du classement `χ²`, et elle est `≈ 1`. Sur le
témoin TYPE_3 (`N = 70 560`, `M = 2·10^7`) : `rang_χ² = 0`, `z = 40,3`
(`37,9` attendu), `p` exact ; sur le flux nul, `z_max = 6,28 < 8,31`.

**(v) Le plan suivant, la cohérence, le shift 0.** `p` trouvé, le lemme
des plans se lit à l'envers : pour chaque mot pair `i`,

    <α_i, y> = r¹_i ⊕ <α'_i, p> ⊕ e₂(α_i ∧ p)

est **linéaire** en `y`, et l'observation molle `t_i` signée par la
correction connue donne `Λ_y(y) = Σ_i s_i (−1)^{<α_i, y>}`, une WHT des
`10 N` mots (`g_y[α_i] += s_i`), `z_y = Λ_y/√Σ t_i²` d'espérance
`√Σ τ₀² ≈ 0,66 √N` — `94` pour `20 000` tirages, `175` pour l'archive
(témoin TYPE_3 : `176,1`). La confirmation est ainsi bien plus forte que
la détection : elle porte sur `10 N` observations linéaires et non sur `M`
produits triples. Pour `L > CB`, `y_bas` vient des mots dont `α_i` a ses
bits hauts nuls (un huitième d'entre eux, `z_y ≈ 60`), puis `y_haut` d'une
petite WHT de `2^{L−CB}`. Enfin `(p, y)` prédit la parité de chaque mot
pair de chaque tirage ; un mot dont la classe prédite est **vide** dans
l'ensemble trié est une contradiction — `0` pour l'état vrai, quelques-unes
(`7` sur le flux nul TYPE_3) pour un état faux.

*Shift 0.* Si la sortie est `x = r` (plan 0 observé), la même WHT des mots
avec `p = 0` — `s_i = t_i`, adresse `α_i` — est le test **exact** du plan
0 sur `2^L` états (`z_lin`, `p_lin`), sans relation. Un flux à shift 0
apparaît aussi dans le test des relations, en `p̂ = 0` (aucune retenue :
`ε_R(0) = +1` pour toute relation), avec un `z` **plus grand** que
`√V` — `134` contre `38` sur le même témoin. La raison est instructive :
au plan 0, les neuf relations sœurs `(a+2m, b+2m, c+2m)` d'une relation
sont satisfaites avec le **même** signe `+1`, et le bit mou de chaque mot,
qui compte les parités de tout l'ensemble, les porte toutes ; au plan 1,
chaque sœur a son propre `ε_{R+2m}(p*)`, décorrélé du premier, et seule
la relation propre est cohérente. L'amplification n'est pas exploitable
au plan 1 ; elle est un signe de plus qu'un flux linéaire se reconnaît de
loin.

**(vi) Le coût et les témoins.** Énumération : une passe par couple
`(j, d)` sur les `Σ` positions, `≈ 10^9` tests pour l'archive, plus `M`
insertions dans la table des triples ; `g` : `4·2^{CB}` octets par tranche
; `χ²` : `2^{L−CB}` WHT de `2^{CB}` (`≈ 15` s chacune sur deux fils) ; les
candidats : `256` passes sur `M` relations. Sur la machine du dossier
(quatre cœurs partagés), un décodage complet — relations, `χ²`, candidats,
`y`, cohérence, `z_lin` — prend `≈ 4` min pour TYPE_3 (`2,3` Go), une
minute ou moins pour `L ≤ 28`. Témoins plantés puis flux nuls, avec le
binaire compilé par le script (`identifié` = `p` exact, `y` exact, `0`
contradiction) :

| trinôme | pas, schéma | shift | `N` | `Z₁` | `z` attendu | `z` | `z_y` | identifié | nul `z_max` |
|---|---|---|---|---|---|---|---|---|---|
| `(3, 17)` | 20, FY | 1 | 20 000 | 7,07 | 38,0 | 36,4–38,7 | 93 | oui | 4,4–4,8 |
| `(3, 17)` | 79, shuffle | 1 | 8 000 | 7,07 | 38,0 | 35,0 | 59 | oui | < 5 |
| `(1, 15)` TYPE_2 | 80, shuffle | 1 | 8 000 | 6,88 | 38,1 | 40,2 | — | oui | < 5 |
| `(3, 17)` | 20, FY | 0 | 20 000 | 7,07 | — | `z_lin` 93,5 (`z` 134,5 en `p̂ = 0`) | — | oui | < 5 |
| `(3, 31)` TYPE_3 | 20, FY | 1 | 70 560 | 8,31 | 37,9 | 40,3 | 176 | oui | 6,28 |

Le chemin par morceaux (`WHT_CB = 14` forcé sur `L = 17`) rend le même
`p`, le même `y` et le même `z` que la WHT directe.

**(vii) Ce qui reste hors de portée.** *TYPE_4* `(1, 63)` : les relations
de poids 3 dans l'étendue de l'archive se réduisent aux structurelles
(`Σ²/(2P) ≈ 10^{−7}` à `2·10^{−6}` fortuites selon le pas), soit `14` à
`17` couples `(63·2^m, 62·2^m)`, `M ≈ 2·10^5` (pas 79) à `10^6` (pas 20),
`z_attendu ≈ 4` à `8,5` contre `Z₁(63) = 10,6`, et surtout `2^{63}` plans
0 sans WHT possible : le théorème réduit `2^{126}` à `2^{63}`, ce qui ne
suffit pas. *Réamorçage
nocturne* : par nuit (`204` tirages, `Σ ≈ 4 000`), il ne reste que les
structurels courts — `M ≈ 10^3` pour TYPE_3, `z_attendu ≈ 0,3` — le
flux continu est ce qui donne des relations, et sans lui cette section ne
dit rien (le 7.13 couvre la nuit à shift 0 seulement). *Shift `≥ 2`* : le
plan 2 porte les retenues des retenues, cubiques en `p` et quadratiques
en `y` ; les relations de poids 3 n'annulent que la partie linéaire en
`y`, et l'identité de `maj` n'a pas d'analogue de degré 3 en quatre
caractères — il faudrait des relations de poids supérieur, dont la
variance croît comme `τ₀^{−2}` par facteur. *Rejet, troncature, pas
variable, Fibonacci soustractif* : non couverts, comme au 7.13.

**(viii) Le budget d'information de l'archive triée, et ce qu'il dit du
reste du catalogue.** Le théorème est un décodeur ; il vaut la peine de
compter ce qu'il y a à décoder. Un mot pair `k` d'un tirage trié ne livre
que le bit mou `t_k` de son plan observé, et l'information qu'il porte sur
ce bit est `I_k = 1 − E[H_b((1 + t_k)/2)]`, calculable exactement par la
loi hypergéométrique de `(n_0, n_1)` dans la fenêtre de `80 − k` numéros
(qui rend aussi `τ₀²(k) = 0,0380 … 0,0499`, la table `CALIB` au
dix-millième près) : `0,0280` bit pour `k = 0`, `0,0370` pour `k = 18`,
`0,321` bit par tirage en sommant les dix. Les dix bits d'un même tirage
sont dépendants, et la somme des informations individuelles **minore**
l'information conjointe (`H(bits ∣ ensemble) = Σ_k H(bit_k ∣ ensemble,
bits_{<k}) ≤ Σ_k H(bit_k ∣ ensemble)`) ; celle-ci se calcule par Monte
Carlo, l'ensemble trié fixé et ses `20!` ordres équiprobables (le
Fisher–Yates est une bijection entre suites de `j` et arrangements) :
`0,45` bit par tirage sous FY, `0,36` sous le shuffle. L'archive entière
porte donc, sur les plans observés des mots pairs à pas constant, **`≈ 32
000` bits (FY) ou `26 000` (shuffle)** — et rien de linéaire sur les mots
impairs, dont le module est impair.

Trois conséquences. *TYPE_3 à shift 1* demande `62` bits (plans 0 et 1) :
le budget est cinq cents fois plus grand, et la difficulté n'a jamais été
l'information mais le décodeur — c'est ce que (ii)–(v) fournissent, et le
`z_y = 176` du témoin est la mesure de l'excédent. *Par nuit* (`204`
tirages), le budget est `92` bits (FY) : le plan 0 de TYPE_3 (`31` bits) y
tient trois fois — c'est le 7.13 nuit par nuit, à `z ≈ 9,4` pour `Z₁ =
8,31`, une marge courte — ; ses plans 0 et 1 (`62` bits) y tiennent à
peine, sans marge pour un décodeur de longueur finie, et le décodeur
manque (`2^{62}`). *MT19937* : `19 937` bits contre un budget de `26 000` à
`32 000` sur toute l'archive, à la condition d'un flux ininterrompu de
346 nuits ; le rapport `1,3` à `1,6` est celui d'un code lu au voisinage
de sa capacité — pas d'exclusion possible par l'information seule, mais
aucun décodeur : le bit 0 de chaque sortie tempérée est une forme de
poids `6` du mot non tempéré, la récurrence est creuse, et décoder
`19 937` inconnues sur `700 000` contrôles mous à ce rapport signal sur
bruit est un problème de code aléatoire, sans la structure de poids 3 qui
fait ici la WHT. L'archive triée exclut MT19937 par une autre voie, le
rang du bonus sous la troncature (§114) ; sous le modulo elle ne le peut
pas, et le compte ci-dessus dit pourquoi ce n'est pas seulement une
question de calcul.

---

### 7.15 Le distingueur structurel (§163) — le plan 0 sans état, à tout retard : les relations de poids 3 comme test d'hypothèse

Les 7.11, 7.13 et 7.14 **décodent** : ils cherchent l'état parmi `2^L`
hypothèses, et c'est ce `2^L` qui les arrête à `L = 31`. Cette section
pose la question d'avant : *l'archive est-elle engendrée par un Fibonacci
retardé de retard `L`, quel qu'en soit l'état ?* — et y répond sans
état, en temps **linéaire** en la taille de l'archive, pour tout retard
jusqu'à `1 279`. L'outil est le même objet qu'au 7.14, les relations de
poids 3 du trinôme, mais employé autrement : non plus comme les contrôles
d'un décodeur, mais comme un **test d'hypothèse** dont la statistique ne
dépend d'aucun état. Le plan 0 d'un Fibonacci additif, soustractif ou
xor est l'`m`-suite du trinôme ; chaque relation `x^j + x^d + 1 ≡ 0 (mod
f)` est une équation de parité vraie pour **tout** état ; et l'archive
triée, par le bit mou du 7.13, livre pour chaque mot pair une estimation
bruitée de ce plan. La somme des produits de trois bits mous sur toutes
les relations à portée est une variable dont l'espérance est nulle si
l'hypothèse est fausse, et vaut un multiple connu de `(3/79)^{3/2}` fois
la racine du nombre de triples si elle est vraie.

La section établit (i) le théorème des relations sans état, et ce qu'il
couvre ; (ii) le bit mou d'un tirage entier et son calibrage **exact**,
`C = τ₀² = 3/79` ; (iii) la statistique, sa variance nulle exacte, le
`z` attendu en forme close, et l'optimalité des poids ; (iv)
l'énumération de **toutes** les relations à portée, et pourquoi la
famille structurelle n'en est qu'une partie ; (v) ce que voient les plans
supérieurs — la proposition de la retenue, qui dit exactement pourquoi la
`random()` de la glibc est invisible ici et pourquoi c'est le 7.14 qui
la voit (et, pour TYPE_1 et TYPE_2, le 7.16 par la période `2(2^L −
1)` de leur plan 1) ; (vi) la cible par nuit ; (vii) les témoins, la troncature à `L
≤ 20` ; (viii) le chemin vers l'état si le test détecte, et les limites.
Le résultat sur l'archive est au §163 : `D = 0` sur `2 006` statistiques pleines (`z` max `3,14`, écart-type `1,022`), conforme ; `236` cases faibles et `262` vides restent ouvertes, presque toutes aux pas 79–80 et de degré `≥ 21`.

**(i) Les relations sans état.** Soit `r_i = r_{i−K} ⊕ r_{i−L}` (xor),
`r_i = r_{i−K} + r_{i−L}` ou `r_i = r_{i−L} − r_{i−K} mod 2^{32}`, et
`f(x) = x^L + x^{L−K} + 1` son polynôme caractéristique (`r_{a+L} =
r_{a+L−K} ± r_a`). Notons `b_i` le bit 0 de `r_i` (plan 0), `b^s_i` son
bit `s`.

> **Théorème (relations sans état).** *Pour `+` et `−`, le plan 0 vérifie
> `b_{a+L} = b_{a+L−K} ⊕ b_a` pour tout `a` ; pour xor, tout plan `s` le
> vérifie. Par conséquent, pour tout polynôme `g = Σ g_e x^e` multiple de
> `f`, `Σ_e g_e b_{a+e} = 0` pour tout `a` — en particulier, pour toute
> relation de poids 3, `x^j + x^d + 1 ≡ 0 (mod f)`, `0 < d < j` :*
>
>     b_a ⊕ b_{a+d} ⊕ b_{a+j} = 0        pour tout a ≥ 0,
>
> *quel que soit l'état initial, que `f` soit primitif ou non.*
>
> *Preuve.* Le bit 0 d'une somme ou d'une différence est le xor des bits
> 0 : aucune retenue n'entre dans le bit 0. La suite `b` est donc dans le
> noyau de `f(E)`, `E` l'opérateur de décalage, et `g(E) = h(E) f(E)`
> l'annule aussi. ∎

Le théorème ne suppose rien de l'état — ni sa valeur, ni qu'il soit
« aléatoire » ; il ne suppose pas non plus `f` primitif : si `f` est
réductible, la suite est plus courte, mais toujours annulée par `f`. Ce
qu'il suppose, c'est le **pas constant** (`S` mots par tirage, les
positions `S·t + k`), comme tout le 7.11–7.14 : sous le rejet, la
position d'un mot n'est plus connue et le théorème n'a plus de prise.

**(ii) Le bit mou d'un tirage entier, et `C = τ₀² = 3/79`.** Le 7.13
lit, mot pair par mot pair, un bit mou `t_{t,k}` fondé sur les résidus
modulo `80 − k`. Ici une seule variable par tirage suffit, et elle est
plus simple : `T_t = (n_impairs − n_pairs)/20`, le déséquilibre de parité
des vingt numéros tirés. Sa liaison avec les mots pairs tient à un fait
combinatoire des deux échantillonneurs.

> **Lemme (le numéro désigné).** *Dans le Fisher–Yates partiel (`j_k = k +
> (r_k mod (80 − k))`, échange `k ↔ j_k`, tirés = positions `0…19`) comme
> dans le `Collections.shuffle` (`i = 79…60`, `k = 79 − i`, `j_k = r_k mod
> (i + 1)`, échange `i ↔ j_k`, tirés = positions `60…79`), pour tout `k =
> 0…19` le numéro `j_k + 1` appartient à l'ensemble tiré ; et pour `k`
> pair, `j_k ≡ r_k (mod 2)`, donc la parité de ce numéro est `1 ⊕ b_{t,k}`.*
>
> *Preuve.* Au pas `k`, l'élément en position `j_k` passe en position
> `k` (FY) ou `i` (shuffle), position finale qui n'est plus touchée : les
> pas suivants échangent des positions `k' > k` avec des `j' ≥ k'` (FY)
> ou des `i' < i` avec des `j' ≤ i'`. Si la position `j_k` n'a pas encore
> été visitée, elle contient encore `j_k + 1` ; si elle l'a été au pas
> `k'' < k`, c'est que `j_{k''} = j_k`, et `j_k + 1` est alors passé en
> position `k''` (FY) ou `i''` (shuffle), finale. Dans les deux cas
> `j_k + 1` est tiré. Enfin `80 − k` et `i + 1 = 80 − k` sont pairs pour
> `k` pair, donc `r_k mod (80 − k) ≡ r_k (mod 2)` et `j_k ≡ k + r_k ≡
> r_k`. ∎

Le numéro désigné par un mot pair est donc toujours dans l'ensemble, avec
la parité du bit 0 du mot. Posons `ε(n) = (−1)^{n+1}` (`+1` impair), `T_t
= (1/20) Σ_{n tiré} ε(n)`, et pour `k` pair `β_{t,k} = (−1)^{b_{t,k}} =
ε(j_k + 1)`.

> **Proposition (calibrage exact).** *Sous des mots uniformes, `E[T] = 0`,
> `τ₀² = Var T = 3/79 = 0,037975`, et pour le mot `0` du Fisher–Yates
> `C(0) = E[T · β_{t,0}] = 3/79` exactement.*
>
> *Preuve.* L'ensemble tiré est un `20`-sous-ensemble uniforme de `{1…80}`
> (les deux échantillonneurs sont exacts sous des mots uniformes) :
> `n_impairs` est hypergéométrique `(80, 40, 20)`, de variance `20 · ½ · ½
> · 60/79 = 300/79`, et `T = (2 n_impairs − 20)/20` donne `Var T = 3/79`.
> Pour `k = 0` (FY), `j_0 + 1 = arr[0]` est l'un des vingt numéros tirés,
> échangeable avec les dix-neuf autres, donc `Cov(T, ε(arr[0])) = Var T`. ∎

Pour les autres mots pairs le numéro désigné peut être arrivé en position
finale par un détour, et l'échangeabilité n'est plus exacte ; le
calibrage Monte Carlo de l'outil (`10^6` tirages du schéma nourri de
mots uniformes) donne `C(k') = 0,0378 … 0,0383` pour les dix mots pairs,
FY comme shuffle, contre `3/79 = 0,0380` — la formule vaut pour tous à
un pour cent près, et `τ₀² = 0,03793` mesuré. Sur l'archive, `Var T =
0,03787` et `E[T] = −0,00031` (`N = 70 560`, écart-type de la moyenne
`0,00073`) — à `0,5` écart-type de `3/79` l'un et l'autre ; l'outil
centre `T` sur sa moyenne empirique et prend `τ²` empirique, ce qui ne
suppose rien de l'archive.

Autrement dit, `T_t ≈ Σ_{k pair} C · β_{t,k} + bruit` : un seul nombre par
tirage porte, avec le même poids `C = 3/79`, les dix bits du plan 0 des
mots pairs, à un rapport signal sur bruit `C/τ₀ = √(3/79) = 0,195` par
bit. Il n'est pas besoin de savoir lequel des dix parle : les relations
le disent.

**(iii) La statistique, sa variance exacte, le `z` attendu.** Une
relation `(d, j)` et un mot pair `k = 2m` d'un tirage `t_a` désignent les
positions `p₁ = 2m + d`, `p₂ = 2m + j` — soit les tirages `t_a + δ₁`,
`t_a + δ₂` (`δ = p div S`) et les mots `k₁ = p₁ mod S`, `k₂ = p₂ mod S`.
Le triplet est **valide** si `k₁, k₂` sont pairs `≤ 18` et `1 ≤ δ₁ <
δ₂` (trois tirages distincts). Deux relations ou deux mots qui tombent sur
le même **motif** `(δ₁, δ₂)` se cumulent : `c_p` est le nombre de
triplets valides `(m, d, j)` du motif `p`, `w_p = C(m) C(k₁/2) C(k₂/2)`
sommé sur eux (`≈ c_p C³`), et `n_p` le nombre de `t_a` tels que `t_a +
δ₂ < N` (cible flux) ou `BLOC(t_a) = BLOC(t_a + δ₂)` (cible bloc). La
statistique est

    Λ = Σ_p w_p Σ_{t_a} T_{t_a} T_{t_a+δ₁} T_{t_a+δ₂},      z = Λ / √V,
    V = τ⁶ Σ_p w_p² n_p.

> **Proposition (variance nulle exacte, `z` attendu, optimalité).**
> *Sous `H₀` — les `T_t` indépendants, centrés, de variance `τ²` —,
> `E[Λ] = 0` et `Var Λ = V` exactement. Sous `H₁` — l'archive engendrée par
> le schéma sur le plan 0 de `f` —, `E[Λ] = Σ_p w_p² n_p`, donc*
>
>     z_attendu = √(Σ_p w_p² n_p) / τ³ ≈ (3/79)^{3/2} √(Σ_p c_p² n_p) = 0,0074 √(Σ_p c_p² n_p),
>
> *et, parmi toutes les combinaisons linéaires des sommes de motifs, les
> poids `w_p` maximisent `E[Λ]/√(Var Λ)`.*
>
> *Preuve.* Un même triple de tirages `{t_a, t_a + δ₁, t_a + δ₂}` ne
> provient que d'un seul motif (son plus petit élément fixe `t_a`, les
> deux écarts fixent `p`) ; deux produits de triples distincts ont pour
> covariance un produit contenant un `E[T] = 0` — même s'ils partagent
> deux tirages. Les produits sont donc deux à deux non corrélés, de
> variance `τ⁶`, d'où `Var Λ = Σ_p w_p² n_p τ⁶`. Sous `H₁`,
> `E[T_{t_a} T_{t_a+δ₁} T_{t_a+δ₂}]` se développe sur les `10³` triplets de
> mots pairs ; par le théorème (i) les `c_p` triplets qui sont des
> relations valent `+C(m)C(k₁/2)C(k₂/2)`, les autres portent `(−1)^{<v,p>}`
> avec un `v ≠ 0` qui change avec `t_a`, de somme `O(√n_p)` — du bruit,
> pas du signal. Donc `E[Σ_{t_a} T T T] = w_p n_p` et `E[Λ] = Σ w_p² n_p`.
> Pour l'optimalité, `Λ_u = Σ_p u_p Σ TTT` a `E = Σ u_p w_p n_p` et
> `Var = τ⁶ Σ u_p² n_p` ; Cauchy–Schwarz donne `E/√Var ≤ √(Σ w_p² n_p)/τ³`
> avec égalité pour `u = w`. ∎

L'outil rapporte aussi `z_p = Λ_p/√(n_p τ⁶)` par motif et son maximum
`zmax_motif` — un diagnostic, non un test ; et la détection est déclarée
sur `z ≥ Z_c = Q⁻¹(10⁻⁷/n_tests)` unilatéral, le signal étant positif par
construction. Sans état à énumérer, il n'y a pas de borne d'union sur
`2^L` : `n_tests` est le nombre de statistiques de la grille, `2 268` au
§163, `Z_c = 6,49`.

**(iv) Toutes les relations à portée.** L'outil énumère `x^e mod f` pour
`e = 0 … j_max = S(N − 1) + 18` (la position du dernier mot pair
observé), par décalages successifs dans `F₂[x]/(f)` — `⌈L/64⌉` mots de
64 bits, clé exacte si `L ≤ 64`, hachage `GF(2)`-linéaire sinon avec
vérification par exponentiation — et retient tout `(d, j)` tel que `x^j +
1 = x^d`, `0 < d < j`. C'est le logarithme de Zech du 7.14 poussé jusqu'à
`1,41 · 10^6`, et **sans hypothèse de primitivité**. Le compte est
instructif :

| trinôme | relations à portée (`j ≤ 1 411 198`) | structurelles `((L−K)2^m, L2^m)` | autres |
|---|---|---|---|
| `x^63 + x^62 + 1` (TYPE_4) | 87 | 15 | 72, à partir de `j = 4 029 ≈ (L+1)²` |
| `x^63 + x^32 + 1`, `x^63 + x^31 + 1` | 90 | 15 | 75 |
| `x^63 + x^58 + 1`, `x^63 + x^5 + 1` | 15 | 15 | 0 |
| `x^60 + x^59 + 1` | 33 | 15 | 18, à partir de `j = 3 835` |
| `x^31 + x^28 + 1` (TYPE_3) | 764 | 21 | 743 (fortuites, `≈ j_max²/2P = 463` attendues, plus une famille à `j = 980, 1 023`) |
| `x^127 + x^97 + 1`, `x^250 + x^147 + 1`, … `x^1279 + x^1063 + 1` | 14, 13, … 11 | toutes | 0 |

La famille structurelle — la récurrence et ses images par Frobenius,
`(u + v)^{2^m} = u^{2^m} + v^{2^m}` en caractéristique 2, valable dans
toute `F₂`-algèbre — n'est donc pas tout : certains trinômes (`K = 1`,
`K = L − 1`, `(31, 63)`, `(32, 63)`, `(1, 60)`…) ont d'autres multiples de
poids 3 dès `j ≈ L²`, d'autres non (`(5, 63)`, `(24, 55)`, tous les
retards classiques à portée). Nous ne caractérisons pas ces familles
algébriquement — c'est précisément ce que l'énumération brute dispense
de faire : toutes les relations à portée sont trouvées, vérifiées
exactes (arithmétique polynomiale sans hachage pour `L ≤ 64`), et
comptées dans `z_attendu`. Pour `L ≥ 40`, les fortuites (`j_max²/2^{L+1}`)
disparaissent ; pour `L ≤ 20`, la période `2^L − 1` est plus courte que
`j_max` et les relations pullulent — l'outil plafonne à `400 000`
relations et `65 536` motifs (drapeaux « tronquées », « plein »), et le
test reste exact sur le sous-ensemble retenu (toute sous-famille de
relations est un test valide ; seule la prédiction `z_attendu` devient
approximative, voir (vii)). Le coût total est `O(j_max · L/64)` pour
l'énumération et `O(Σ_p n_p)` pour la statistique : `1` à `2` secondes
par trinôme au pas 20 sur l'archive entière, `15` au pas 80 avec
shuffle. Aucun `2^L`, nulle part.

**(v) Ce que voient les plans supérieurs — la proposition de la
retenue.** Le théorème (i) porte sur le plan 0 pour `+` et `−`. Le shift
1 de la `random()` de la glibc publie le plan 1. Que valent les relations
de poids 3 sur les plans `s ≥ 1` ?

> **Proposition (la retenue).** *Pour `r_i = r_{i−K} ± r_{i−L} mod 2^{32}`
> et la relation de base `(d, j) = (L − K, L)` :*
>
>     b¹_a ⊕ b¹_{a+L−K} ⊕ b¹_{a+L} = b_a ∧ b_{a+L−K}      (la retenue du bit 0),
>
> *de biais `E[(−1)^{…}] = 1/2` sous des mots uniformes, et le plan `s`
> y a le biais `2^{−s}`. Pour toute autre relation de poids 3 — les
> doubles de Frobenius `m ≥ 1` comme les familles supplémentaires —, la
> parité du plan 1 est `<β_a, p> ⊕ maj(<α_a, p>, <α_{a+d}, p>, <α_{a+j},
> p>)` (théorème du 7.14), d'espérance sur l'état*
>
>     ½ [ 1(β_a = α_a) + 1(β_a = α_{a+d}) + 1(β_a = α_{a+j}) − 1(β_a = 0) ],
>
> *nulle dès que `β_a` n'est ni nul ni l'un des trois vecteurs — ce qui
> est le cas mesuré : sur un flux planté `(1, 63)` de `3 · 10^5`
> positions, `57` relations, biais `+0,500` (plan 1) et `+0,252` (plan
> 2) pour `(62, 63)`, `|biais| < 0,006` pour les 56 autres sur les deux
> plans.*
>
> *Preuve.* Pour la base, `r_{a+L} = r_{a+L−K} ± r_a` et le bit 1 d'une
> somme est le xor des bits 1 et de la retenue du bit 0, `b_a ∧
> b_{a+L−K}` (pour la différence, l'emprunt `¬b_{a+L} ∧ b_{a+L−K}`, de
> même loi) ; la retenue entrant au bit `s` d'une somme de deux mots
> uniformes vaut 1 avec probabilité `½ − 2^{−(s+1)}`, d'où le biais
> `2^{−s}`. Pour la base encore, on vérifie `β_a = α_{a+L}` (le 7.14
> donne `β = α'_a ⊕ α'_{a+L−K} ⊕ α'_{a+L} ⊕ maj(α_a, α_{a+L−K}, α_{a+L})`,
> et la récurrence de `α'` réduit les trois premiers à `α_a ∧ α_{a+L−K}`,
> tandis que `maj(u, v, u ⊕ v) = u ⊕ v ⊕ (u ∧ v)`), ce qui redonne `½`.
> Pour une relation quelconque, avec `x ⊕ y ⊕ z = 0` : `(−1)^{maj(x,y,z)} =
> ½[(−1)^x + (−1)^y + (−1)^z − 1]`, et l'espérance sur `p` uniforme de
> `(−1)^{<β_a, p>}` fois chaque terme est l'indicatrice annoncée. ∎

La conséquence est exacte et elle est double. *D'un côté*, la seule
relation qui parle sur les plans supérieurs est la récurrence elle-même
`(L − K, L)`, et elle **ne tombe jamais** sur trois mots pairs de trois
tirages distincts dans la grille : au pas pair, `d` et `j` doivent être
pairs, or un trinôme primitif a `L` impair, ou `L` pair et `L − K` impair
(sinon `f` serait un carré) ; au pas `79`, il faudrait `L − K ≥ 61` et
`L ≤ 97` avec les bonnes parités après franchissement, ce qu'aucun trinôme
de la grille ne satisfait (vérifié cas par cas sur les 126 : `(2, 63)`
conviendrait, il n'est pas primitif). Donc **le distingueur structurel
est aveugle, par construction, à la `random()` de la glibc** (shift 1) et
à tout Fibonacci additif publiant un plan `≥ 1` : le témoin `(1, 63)` add
shift 1 donne `z = −1,60` pour `z_attendu(plan 0) = 101`, comme il se
doit. *De l'autre*, c'est cette même retenue que le 7.14 exploite —
non pas son biais sur trois positions, mais sa valeur exacte, fonction
du seul plan 0, décodée par une WHT sur `2^L` — et c'est pourquoi les
deux sections sont complémentaires : le 7.15 couvre le plan 0 de tout
retard sans état, le 7.14 le plan 1 de `L ≤ 31` avec `2^L`. Pour `xor`,
il n'y a pas de retenue, tous les plans sont des `m`-suites, et le test
voit tout shift : les témoins `(37, 100)` xor shift 3 et `(103, 250)`
xor shift 1 le confirment.

**(vi) La cible par nuit.** Si chaque nuit part d'un état neuf (le 7.4),
seules valent les relations dont `j` tient dans la nuit : `j ≤ S(l_max −
1) + 18`, `≈ 4 000` au pas 20 — pour `(1, 63)`, `18` relations et `23`
motifs au lieu de `87` et `166`, et `n_p` compte les `t_a` dont le triple
reste dans le même bloc (`BLOC(t_a) = BLOC(t_a + δ₂)`). Le `z_attendu`
tombe de `103` à `14,6` : moins de relations, et les longues sont
perdues. Il reste très au-dessus de `Z_c = 6,49` pour `L ≤ 63` au pas
20 ; pour les retards classiques, `L · 2^m ≤ 4 000` ne laisse que
quelques relations et la cible bloc perd sa puissance — la table du §163
la donne ligne à ligne. Les deux cibles sont deux hypothèses distinctes
(un état pour l'année ; un état par nuit), et le §163 les teste toutes
deux.

**(vii) Les témoins, et la troncature.** Sept flux plantés, décodés par
le binaire du §163 puis remplacés par des tirages nuls (`Z_c = 6,49`, `0`
faux positif) :

| trinôme | op, shift | variante | `N`, blocs | relations, motifs | `z_attendu` | `z` |
|---|---|---|---|---|---|---|
| `(1, 63)` | add 0 | fy 20 | 70 560, 1 | 87, 166 | 102,3 | **104,5** |
| `(1, 63)` | add 1 | fy 20 | 70 560, 1 | 87, 166 | 101,3 | −1,6 (aveugle, (v)) |
| `(24, 55)` | sub 0 | fy 22 | 70 560, 1 | 15, 26 | 51,8 | **52,7** |
| `(37, 100)` | xor 3 | fy 20 | 70 560, 1 | 14, 26 | 52,0 | **51,1** |
| `(1, 63)` | add 0 | fy 20, **bloc** | 70 560, 370 | 18, 23 | 14,6 | **14,6** |
| `(3, 31)` | add 0 | shuffle 79 | 20 000, 1 | 887, 32 | 15,0 | **15,8** |
| `(103, 250)` | xor 1 | shuffle 80 | 70 560, 1 | 15, 5 | 8,6 | **8,2** |

`z` suit `z_attendu` à `3 %` près partout — la formule close de (iii) est
une prédiction, pas un ajustement. Deux remarques. *Au pas 79/80*, les
relations doivent faire tomber `2m + d` et `2m + j` sur des mots pairs `≤
18` après réduction modulo `79` ou `80` : la plupart n'y arrivent pas,
`887` relations ne font que `32` motifs pour TYPE_3, et pour bien des
trinômes **aucun** — la statistique est alors *vide* (`z = 0`, elle ne
teste rien, et le §163 les compte à part). *Pour `L ≤ 20`*, la période
`2^L − 1` est plus courte que le flux : sous `H₁` les `T_t` sont
périodiques, les produits de triples ne sont plus indépendants, et la
variance sous `H₁` dépasse celle sous `H₀` — `(3, 7)` donne `z = 1 715`
pour `z_attendu = 5 054` : le test reste valide (sa variance sous `H₀`
est exacte) et la détection écrasante, seule la prédiction est
optimiste ; `(1, 15)` donne `2 160` pour `2 133`.

**(viii) Le chemin vers l'état, et les limites.** Si le §163 détectait —
un `z ≥ Z_c` pour un `(K, L)` et une variante —, le plan 0 s'ensuivrait
sans `2^L` : les relations sont un code LDPC de poids 3 sur `≈ 700 000`
bits mous de rapport signal sur bruit `0,195`, et la propagation de
croyances (l'attaque par corrélation rapide de Meier–Staffelbach, dont
c'est exactement le cadre) converge en temps linéaire dès que le nombre
de relations par bit dépasse quelques unités — `87` relations sur `1,4 ·
10^6` positions en donnent `≈ 0,6 × 10` par mot pair pour `(1, 63)`, `764
× 10/S` pour TYPE_3 : assez au pas 20, juste au pas 79. Les plans
suivants viendraient ensuite par le relèvement du 7.12 sur des tirages
ordonnés, ou par le `Z/4` du 7.14. Ce chemin n'est pas construit : il
n'a de sens qu'après une détection.

Ce que le test **ne couvre pas** : les plans `≥ 1` des Fibonacci `+`/`−`
(la proposition (v) : c'est le 7.14, à `2^L`) ; le Fibonacci
multiplicatif (bit 0 constant) et la soustraction avec emprunt de
Marsaglia–Zaman (l'emprunt entre dans le bit 0) ; le rejet et le pas
variable (les positions ne sont plus `S·t + k`) ; et MT19937 — non parce
qu'il n'est pas un trinôme, mais parce que ses multiples de poids 3 les
plus courts ont `j ≈ 2^{L/2} = 2^{9 968}` : le théorème (i) vaut pour
tout polynôme, l'archive n'est simplement pas assez longue, et le
polynôme lui-même (poids `135`) donnerait un signal `C^{135}`. C'est le
sens de la borne du 7.14 (viii) vue de l'autre côté : le budget
d'information suffit, ce sont les relations courtes qui manquent.

---

### 7.16 Le balayage d'autocorrélation du plan 0 (§164) — les relations de poids 2 : tout générateur congruentiel de module `2^W` sans ses paramètres, toute période à portée, sans état

Le 7.15 teste les relations de poids **3** d'un trinôme donné : il faut
nommer le trinôme. Cette section descend d'un cran et ne nomme plus
rien : elle demande seulement si le bit que lit l'échantillonneur — la
parité du numéro désigné, mots pairs, 7.15 (ii) — satisfait une relation
de poids **2** quelque part dans le flux,

    b_{p+D} = b_p            (ou son complément)      pour tout p,

pour un décalage `D` quelconque jusqu'à quelques millions de mots. Trois
familles en découlent : un décalage isolé (`A`), une période `P` et tous
ses multiples (`B`), une anti-période `H` (`b_{p+qH} = b_p ⊕ (q mod 2)`,
`C`). Ce que cela couvre est plus large qu'il n'y paraît, et c'est le
théorème (i) qui le dit : **tout** générateur congruentiel linéaire de
module `2^W` — `x_{i+1} = a x_i + c mod 2^W` à sortie `x >> s` — a un
bit `s` de période exactement `2^{s+1}` et d'anti-période `2^s`, quels
que soient `a ≡ 1 (mod 4)`, `c` impair et `W`. `java.util.Random` (`s =
17`), `rand()` de MSVC (`s = 16`), TYPE_0 de la glibc (`s = 0`), le
MMIX de Knuth à 64 bits et n'importe quel LCG maison tombent ainsi sous
un même test, sans que l'on connaisse `a`, `c` ni `W` ; s'y ajoutent
tout registre à décalage ou Fibonacci retardé dont la période du plan 0,
`2^L − 1`, tient dans le flux, et — par la période exacte `2(2^L − 1)`
du plan 1 d'un Fibonacci additif — la `random()` de la glibc en TYPE_1
et TYPE_2 à shift 1, celle-là même que le 7.15 (v) déclare invisible
aux relations de poids 3. La statistique est une autocorrélation, la
grille est balayée par transformée de Fourier, et le tout coûte moins
d'une heure pour `32,7` millions de statistiques.

La section établit (i) le théorème des bits d'un LCG, avec la correction
d'une affirmation antérieure sur le décalage `2^{s+1}` ; (ii) la
projection d'un décalage de mots sur la grille des tirages, les tables
`c_q(ρ)` et leurs conditions de parité ; (iii) la statistique `T` non
centrée et ses moments exacts ; (iv) la variance nulle exacte, le `z`
attendu en forme close et l'optimalité ; (v) les familles `B` et `C`,
le lemme de non-recouvrement et le coût ; (vi) la famille `D`, les
paires d'un même tirage ; (vii) le seuil, le nombre effectif de
statistiques et la queue ; (viii) la couverture exacte et les angles
morts ; (ix) la théorie au premier ordre `T ≈ C·U`, qui **prédit** les
témoins au lieu de les fixer à la main, et l'échelle des corrélations
partielles d'un LCG — deux résultats nouveaux. Le résultat sur l'archive
est au §164.

**(i) Les bits d'un générateur congruentiel de module `2^W`.** Soit
`x_{i+1} = a x_i + c (mod 2^W)`, `a ≡ 1 (mod 4)`, `c` impair — les
conditions de Hull–Dobell pour la période pleine, que tout LCG déployé
respecte —, et `b^s_i` le bit `s` de `x_i`. Notons `Σ_n = Σ_{j<n} a^j`
et `v₂` la valuation 2-adique.

> **Théorème (période et anti-période du bit `s`).** *Pour tout `s ≤ W −
> 1` et tout `i` :*
>
>     x_{i+2^s} ≡ x_i + 2^s   (mod 2^{s+1}),      donc   b^s_{i+2^s} = 1 ⊕ b^s_i,   b^s_{i+2^{s+1}} = b^s_i,
>
> *et `2^{s+1}` est la période exacte du bit `s`. En particulier, sous un
> échantillonneur à modulo de borne paire (`j = k + (r mod (80 − k))`,
> `r = x >> s`, `k` pair), la parité du numéro désigné est exactement
> `b^s`, et vérifie les deux relations.*
>
> *Preuve.* `x_{i+n} = a^n x_i + c Σ_n`. Par le lemme de relèvement des
> exposants en `p = 2` (`a ≡ 1 mod 4`) : `v₂(a^n − 1) = v₂(a − 1) +
> v₂(n)`, d'où `v₂(Σ_n) = v₂((a^n − 1)/(a − 1)) = v₂(n)`. Pour `n =
> 2^s` : `v₂(a^n − 1) ≥ 2 + s`, donc `a^n x_i ≡ x_i (mod 2^{s+1})` ; et
> `c Σ_n = 2^s × impair ≡ 2^s (mod 2^{s+1})`. Ajouter `2^s` modulo
> `2^{s+1}` inverse le bit `s` sans retenue. La période divise `2^{s+1}`
> et ne divise pas `2^s` : elle vaut `2^{s+1}`. Pour une borne paire `b`,
> `(r mod b) mod 2 = r mod 2 = b^s`. ∎

Le théorème ne dépend ni de `W` (les `s + 1` bits bas forment un LCG
modulo `2^{s+1}` clos sur lui-même), ni de la valeur de `a` au-delà de
`a ≡ 1 (mod 4)`, ni de `c` au-delà de sa parité : c'est ce qui permet de
tester **tous** les LCG à la fois, `s` étant la seule inconnue, et `s`
n'est qu'un index de la grille. Une remarque corrige au passage une
affirmation faite plus haut dans ce dossier : au décalage `2^{s+1}`, la
sortie `r = x >> s` **n'est pas** translatée d'une constante. En effet
`x_{i+2^{s+1}} − x_i = (a^{2^{s+1}} − 1) x_i + c Σ_{2^{s+1}}` avec
`v₂(a^{2^{s+1}} − 1) ≥ s + 3` et `v₂(c Σ) = s + 1` : la différence des
sorties vaut `c Σ/2^s + 8 m x_i` — ses trois bits bas seulement sont
constants (`≡ 2 mod 4`), le reste dépend de `x_i`. Seul le bit `s` (bit
0 de la sortie) porte une relation exacte ; c'est lui, et lui seul, que
le balayage lit.

Pour une borne **impaire** `b` (les mots `k` impairs, et tous les mots au
pas 79 du shuffle sauf `i + 1 = 64`), `(r mod b) mod 2 = r ⊕ ⌊r/b⌋ (mod
2)` : le quotient `⌊r/b⌋` est équiréparti modulo 2 sur une plage de `r`
bien plus longue que `b`, et la parité du résidu ne porte plus le bit
`s` (corrélation `≈ 0`, mesurée `< 0,003`). C'est pourquoi la grille ne
prend que les mots pairs `k ≤ 18` — les mêmes qu'au 7.13 et 7.15. La
borne `64` de `java.util.Random` (`k = 16` au FY, `i + 1 = 64` au
shuffle) est un cas à part : `nextInt(64)` renvoie `(64 · r) >> 31`, les
bits `42–47` de l'état, qui n'ont aucune relation à portée ; ce mot est
exclu des relations exactes des témoins Java, et la prédiction de (ix)
le traite d'elle-même.

**(ii) Du décalage de mots au retard de tirages.** Le mot `k` du tirage
`t` est à la position `p = S t + k`. Un décalage `D = S q + ρ` (`0 ≤ ρ <
S`) l'envoie sur le mot `k + ρ` du tirage `t + q` si `k + ρ < S`, sur le
mot `k + ρ − S` du tirage `t + q + 1` sinon. Soit `E = {0, 2, …, 18}`
les mots lus ; posons

    c_q(ρ)     = #{k ∈ E : k + ρ ∈ E},           c_{q+1}(ρ) = #{k ∈ E : k + ρ − S ∈ E}.

Explicitement `c_q(ρ) = 10 − ρ/2` pour `ρ` pair `≤ 18`, `0` sinon ; et
`c_{q+1}(ρ) = 10 − (S − ρ)/2` pour `S − ρ` pair `≤ 18`, `0` sinon. Les
**conditions de parité** en découlent : `c_q` ne vit que sur `ρ` pair,
`c_{q+1}` que sur `ρ ≡ S (mod 2)`. Au pas pair, tout décalage pair
envoie les dix mots pairs sur dix mots pairs (`c_q + c_{q+1} = 10`) et
tout décalage impair sur rien ; au pas impair, seuls `20` résidus `ρ`
sur `S` portent des paires (`ρ ∈ {0, …, 18}` pair, ou `ρ ∈ {S − 18, …, S
− 1}` impair), et les multiples `qP` d'une période, réduits modulo `S`,
n'en atteignent qu'une fraction — `2^{17} ≡ 11`, `2^{18} ≡ 22`, `2^{22} ≡
36 (mod 79)`, et il faut aller à `7 · 2^{17} = 79 · 11 614 − 2` pour
trouver les premières paires de Java au shuffle 79 (`9` paires, retard
de tirage `11 614`). Un décalage `D` vaut donc, sur les tirages, la
combinaison `c_q(ρ) A(q) + c_{q+1}(ρ) A(q + 1)` des autocorrélations

    A(d) = Σ_t T_t T_{t+d},        d ≥ 1,

calculées une fois pour toutes par transformée de Fourier (flux :
`n_d = N − d` ; par nuit : somme des autocorrélations internes des `370`
blocs). Le terme `q = 0` — deux mots du **même** tirage — n'est pas un
produit de tirages distincts et sort des familles `A`, `B`, `C` : il
fait la famille `D` de (vi).

**(iii) `T` non centrée et ses moments exacts.** `T_t = (n_impairs −
n_pairs)/20` comme au 7.15, mais **sans centrage ni `τ²` supposé** :
sous `H₀` le nombre d'impairs est hypergéométrique `(80, 40, 20)`, donc

    E[T] = 0,      E[T²] = Var T = (1/100) · 20 · (1/2)(1/2) · (60/79) = 3/79 = 0,037975,      σ(T²) = 0,052908

exactement (le quatrième moment hypergéométrique donne `σ(T²)`). Ne pas
centrer est une décision, pas une négligence : une relation `b_{p+S} =
b_p` (période divisant `S`) rend chaque mot pair `k` **constant** d'un
tirage à l'autre, et `E[T_t] = C Σ_k (−1)^{b_k}` vaut jusqu'à `±10 C =
±0,38` — un signal énorme que le centrage effacerait, et que la famille
`B` lit au contraire à tous les retards (`P | S`). Sous `H₀`, `E[T] = 0`
n'est pas une estimation : c'est une identité de l'échantillonnage
uniforme, et elle rend la variance de (iv) exacte.

**(iv) Variance nulle exacte, `z` attendu, optimalité.** Une famille
(un `D`, un `P` ou un `H`) désigne des comptes signés `s_d` de paires
(mot pair `→` mot pair de rang `≤ 18`, tirages distincts) au retard `d`,
et la statistique

    Λ = Σ_{d≥1} s_d A(d),        z = Λ / √V,        V = τ⁴ Σ_d s_d² n_d,

`τ²` la moyenne empirique de `T²` (`0,03787` sur l'archive, pour `3/79 =
0,03797`).

> **Proposition (variance exacte, `z` attendu, optimalité).** *Sous
> `H₀` — tirages indépendants, `E[T] = 0`, `E[T²] = τ²` —, `E[Λ] = 0` et
> `Var Λ = V` exactement. Sous `H₁` — la relation vraie, `e_d` paires
> signées au retard `d` —, `E[T_t T_{t+d}] = e_d C²` au premier ordre de
> (ix), donc `E[Λ] = C² Σ_d s_d e_d n_d`, et pour les poids adaptés `s =
> e` :*
>
>     z_attendu = (C²/τ²) √(Σ_d e_d² n_d) ≈ C √(Σ_d e_d² n_d) = 0,038 √(Σ_d e_d² n_d),
>
> *maximum de `E[Λ]/√(Var Λ)` sur toutes les combinaisons linéaires des
> `A(d)`.*
>
> *Preuve.* Deux paires de tirages distinctes `{t, t + d} ≠ {t', t' +
> d'}` ont une covariance `E[T_t T_{t+d} T_{t'} T_{t'+d'}]` qui contient
> un facteur `E[T] = 0` (un indice non partagé) ou vaut
> `E[T²]·E[T]·E[T]` (un indice partagé) : elle est nulle, et `Var Λ = Σ
> s_d² Σ_t Var(T_t T_{t+d}) = τ⁴ Σ s_d² n_d`. L'espérance sous `H₁` est
> (ix) ; l'optimalité est Cauchy–Schwarz sur `Σ s_d e_d n_d / √(Σ s_d²
> n_d)`. ∎

Une paire au retard `d` vaut donc `z ≈ 0,038 √n_d` : `9,3` sur le flux
entier (`n_d ≈ 60 000`), `3,8` au `n` minimal `10 000` — une seule paire
isolée est au bord du seuil, deux le dépassent, et une période en
apporte des dizaines par ses multiples. Le `z_rel` des témoins du §164
est cette forme close, calculée sur les seules relations **exactes** ;
il ne compte ni les corrélations partielles ni le mot `64` de Java, et
(ix) fait mieux.

**(v) Les familles `B` et `C` : les multiples, et le lemme de
non-recouvrement.** `B(P)` somme `Λ_A(qP)` sur `q = 1, 2, …, ⌊D_max/P⌋`,
`C(H)` de même avec le signe `(−1)^q`. Il faut agréger les comptes quand
deux multiples tombent sur le même retard de tirages.

> **Lemme (non-recouvrement).** *Si `P ≥ 2S`, deux multiples distincts
> `qP`, `q'P` ne contribuent jamais au même retard de tirages, ni par
> `c_q` ni par `c_{q+1}`.*
>
> *Preuve.* `qP = S d + ρ`, `q'P = S d' + ρ'` avec `d ≤ d' ≤ d + 1` et
> `q < q'` donneraient `(q' − q) P = S(d' − d) + ρ' − ρ ≤ S + S − 1 <
> 2S ≤ P`. ∎

Pour `P ≥ 2S` la statistique `B(P)` est donc une simple tranche
`Λ_A(P), Λ_A(2P), …` — variance comprise, `V_B = Σ_q V_A(qP)` —, ce que
l'outil calcule par tranches vectorisées en `O(D_max log D_max)` par
pas ; pour `P < 2S` (au plus `159` valeurs) les comptes signés `s_d`
sont accumulés explicitement. Le coût total est de l'ordre de `2 ·
10^8` opérations par cible : `2` minutes pour la grille entière, contre
`2^L` pour un décodeur.

**(vi) La famille `D` : les paires d'un même tirage.** Une relation de
période `P ≤ 18` lie deux mots pairs `k, k + P` du **même** tirage et
force deux numéros désignés à la même parité (ou à des parités opposées
pour une anti-période impaire). Sous `H₀` deux numéros désignés ont la
même parité avec probabilité `39/79` ; la relation la porte à `1` (ou
`0`), et

    E[T²] − 3/79 = ± δ_D,      δ_D = (40/79)(E[T² | mêmes] − E[T² | opposées]) = 236/79 079 = 0,0029844

par paire, exactement (les deux espérances conditionnelles sont
hypergéométriques `(78, 38 ou 40, 18)`). La statistique `z_D = (T̄² −
3/79) √N / σ(T²)` vaut alors `≈ 15` par paire sur l'archive : la famille
`D` est une seule statistique, mais la plus sensible de toutes — et
c'est elle que voit TYPE_0 de la glibc (`s = 0` : bit 0 d'anti-période
1, dix numéros désignés de même parité, `z_D = 219` au témoin), en plus
de `B(1)` et `C(1)` qui voient ses `2 000` multiples.

**(vii) Le seuil, le nombre effectif, la queue.** La grille compte, par
pas `S` et par cible, `S · d_max − 1` statistiques `A` et autant pour `B
+ C` (`P, H ≤ D_max/2`) : `M = 2 Σ_S Σ_{cible} (S d_max − 1) + 1 = 32 673
251` avec `d_max = 60 559` (flux, `n_d ≥ 10 000`) et `172` (bloc). Le
seuil bilatéral `Z_c = Q^{−1}(10^{−7}/2M) = 7,89` est Bonferroni sur ce
`M` nominal ; mais toutes les statistiques sont des combinaisons
linéaires des `60 559 + 172` autocorrélations `A(d)`, et le nombre
**effectif** est plutôt `M_eff ≈ 10^6` : le maximum de `|z|` sous `H₀`
attendu est `√(2 ln M_eff) ≈ 5,3`, et les quatre flux nuls des témoins
donnent `5,3` à `5,5` — `2,5` unités sous le seuil. La queue gaussienne
de `z` est une hypothèse, non un théorème : `T` est sous-gaussienne
(Hoeffding sans remise, facteur `1,3` sur sa variance) et `Λ` une somme
de `n_d ≥ 10 000` produits bornés, mais les bornes de concentration
génériques ne donnent que `≈ 10^{−8}` par statistique au `n` minimal —
insuffisant pour `3 · 10^7` statistiques —, et ce sont les flux nuls
(quatre fois `M` statistiques, maximum `5,5`) qui attestent la queue là
où elle compte.

**(viii) Couverture exacte, et angles morts.** `D_max = S · d_max − 1`
vaut `1 211 179` au pas 20 et `4 844 719` au pas 80 (flux), `3 439` par
nuit. Un LCG à sortie `>> s` est vu par `C` si `2^s ≤ D_max/2`, par `A`
seule si `2^s ≤ D_max` :

| cible | pas 20 (flux) | pas 80 (flux) | pas 20 (bloc) |
|---|---|---|---|
| LCG, anti-période `2^s` (`C`, tous les multiples) | `s ≤ 19` | `s ≤ 21` | `s ≤ 10` |
| LCG, un décalage `2^s` (`A` seule) | `s ≤ 20` | `s ≤ 22` | `s ≤ 11` |
| plan 0 d'un Fibonacci ou registre, période `2^L − 1` (`B`) | `L ≤ 19` | `L ≤ 21` | `L ≤ 10` |
| plan 1 de `random()` additif, période `2(2^L − 1)` (`B`) | TYPE_1, TYPE_2 | TYPE_1, TYPE_2 | TYPE_1 |

`java.util.Random` (`s = 17`), MSVC (`s = 16`), TYPE_0 (`s = 0`), le
MMIX `>> 19 … 22` sont couverts sous le flux ; par nuit, seuls `s ≤ 10`
— MSVC par nuit est hors de portée (témoin `attendu 0`, `détecté 0`),
et c'est le §161 qui traite la graine par nuit. La `random()` de la
glibc à shift 1 : le bit 1 d'un Fibonacci additif `r_i = r_{i−K} +
r_{i−L}` de trinôme primitif a pour période exactement `2(2^L − 1)`
(Brent, 1994 : le plan `j` a pour période `2^j (2^L − 1)` dès qu'un mot
initial est impair — le plan 1 est le plan 0 forcé par la retenue `b⁰_{i−K}
b⁰_{i−L}`, périodique de période `2^L − 1`, et `b¹_{i+P₀} ⊕ b¹_i` est
une `m`-suite non nulle), soit `254` pour TYPE_1 et `65 534` pour
TYPE_2 : à portée sous le flux, et TYPE_1 même par nuit. TYPE_3 (`2^{32}
− 2`) et TYPE_4 restent hors de portée — c'est le 7.14 (`2^{31}`) qui
les tient, et le §157 les a exclus à pas fixe.

Les angles morts sont ceux du pas constant et du bit lu : (a) une lecture
**multiplicative** (`⌊b · r/2^{32}⌋`, Delphi, `nextInt` de Java pour une
borne puissance de 2) lit les bits **hauts**, dont la période est `2^W`
— rien à portée, et le mot `64` de Java en est l'exemple ; (b) PCG,
xoshiro, MT19937 : aucun bit de période courte ; (c) le rejet et le pas
variable : la position `S t + k` n'existe plus ; (d) un `ρ` qui retombe
sur un mot **impair** ou hors des `19` premiers : la relation existe,
la grille ne la voit pas — c'est l'« angle mort exact » du MMIX `>> 22`
au shuffle 79 (`2^{22} ≡ 36 (mod 79)`, aucun multiple à portée ne
retombe sur un mot pair, `z_rel = 0`), que (ix) va rattraper par un
autre chemin.

**(ix) La théorie au premier ordre `T ≈ C · U`, et l'échelle des
corrélations partielles.** Les témoins du §164 ne reçoivent pas une
« détection attendue » fixée à la main : elle est **prédite**. Le lemme
du numéro désigné (7.15 (ii)) vaut pour les vingt pas `k = 0 … 19` de
l'un et l'autre échantillonneur, bornes paires et impaires — le numéro
`j_k + 1` est tiré, et `E[T · (−1)^{j_k}] = C = 3/79` pour tout `k`.
Posons `U_t = Σ_{k<20} β_{t,k}`, `β_{t,k} = (−1)^{j_{t,k}}`, la somme
des vingt **signes désignés** réellement tirés par l'échantillonneur.
Un détail compte : les signes des dix bornes **impaires** `b = 61, 63,
…, 79` (l'un et l'autre échantillonneur les parcourent toutes, Java
compris, sa borne `64` étant paire) ne sont pas centrés — `r mod b`
uniforme sur `{0, …, b − 1}` tombe pair `(b + 1)/2` fois sur `b` —
alors que `E T = 0` exactement ; et le **signe** de ce biais dépend de
l'échantillonneur : Fisher–Yates lit `j = k + (r mod b)` avec `b = 80 −
k`, donc `k` impair quand `b` l'est, et `E β = m_b = −1/b` ; le shuffle
lit `j = r mod b` et `E β = m_b = +1/b`. Posons `μ = E U = ε Σ_{b impair}
1/b = ε · 0,14383` (`ε = −1` pour Fisher–Yates, `+1` pour le shuffle) et
`σ_U² = Var U = 20 − Σ_{b impair} 1/b² = 19,9979`.

> **Proposition (premier ordre).** *Sous des mots indépendants et
> uniformes à l'intérieur de chaque tirage, `T_t = C (U_t − μ) + ε_t` à
> un facteur `1/(1 − m_b²) ≤ 1,0003` près sur chaque signe de borne
> impaire, avec `E[ε_t β] = 0` pour chaque signe `β` du tirage `t` ;
> `Var(C (U − μ)) = σ_U² C² = 0,02884`, et `corr(T, U) = √(σ_U² · 3/79)
> = 0,871`. Si deux tirages `t`, `t + d` ne partagent qu'**un** signe, de
> borne paire (`β_{t+d,k'} = ± β_{t,k}`, les autres indépendants), alors*
>
>     E[T_t T_{t+d}] = C² E[(U_t − μ)(U_{t+d} − μ)]        exactement.
>
> *Preuve.* Les vingt signes d'un tirage sont indépendants (chaque `j_k`
> ne dépend que de son mot), donc les `β_k − m_k` sont orthogonaux ;
> `E[T β_k] = C` pour tout `k` (7.15 (ii) : le numéro `j_k + 1` est tiré
> quel que soit le biais de `j_k`) et `E T = 0` donnent `Cov(T, β_k) =
> C`, `Var β_k = 1 − m_k²`, et la projection de `T` sur l'espace engendré
> par `1` et les signes est `Σ_k C (β_k − m_k)/(1 − m_k²)`. Pour deux
> tirages, `E[T_t T_{t+d}] = E[ E[T_t | β_{t,k}] E[T_{t+d} | β_{t+d,k'}] ]`
> puisque, le signe partagé fixé, les deux tirages sont indépendants ;
> `E[T | β]` est affine en un signe binaire, `= C (β − m)/(1 − m²)`, et
> `m = 0` pour une borne paire. ∎

Mesuré sur `30 000` tirages de chaque témoin : `corr(T, U) = 0,875`,
pente `E[TU]/E[U²] = 0,0380 = C`. La prédiction d'une grille entière
s'ensuit : on passe `A_att(d) = C² A_{U−μ}(d)` dans la **même** grille
que l'archive, et l'on obtient `z_att` en chaque statistique, relations
exactes et **partielles** confondues, borne `64` de Java comprise ; pour
la famille `D`, `E[T²] − 3/79 ≈ (m_mêmes − m_opp)(Var U − σ_U²)/4` avec
`m_mêmes − m_opp = 0,0058940` (chaque paire de signes de covariance `ρ`
déplace `E[T²]` de `(m_mêmes − m_opp) ρ/2`). Le centrage par `μ` n'est
pas un raffinement : sans lui, la constante `μ² n_d` de `A_U(d)` se
somme sur les `60 559` retards de la famille « tous les retards » (`B` à
`P = S`, ou `P = 1`) et fabrique un `z_att` fantôme `≈ μ² √(Σ n_d)/τ² ≈
40` — les témoins MMIX au shuffle 79 l'ont montré (`z_att 48,6` à `B
79`, observé `1,7`) — là où `T`, non centré mais de moyenne **nulle**
exactement, ne voit rien ; et le centrage au mauvais signe (`+μ` pour
Fisher–Yates) laisse `2μ` et fabrique un fantôme quatre fois plus grand
(`z_att 154` à `B 1`, `B 3`, … pour Java au FY 20, observé `−0,7`, les
moyennes par mot valant `−0,0117, −0,0088, …` aux `k` impairs contre
`+1/b = +0,0127, +0,0130, …`). La même famille rend la grille sensible à
`T̄²` : un biais de parité de `0,3 %` sur l'archive la déclencherait
(`z ≈ 12`) ; l'archive donne `T̄ = −0,00031`, soit `z ≈ 0,1`. Quand
plusieurs signes sont partagés, la formule reste une prédiction au
premier ordre : à `2 %` près pour les `9` paires de Java (`z_att
148,4`, observé `147,1` au FY 20 ; `101,4` et `102,5` au shuffle 79),
mais en excès de `30 %` sur la grille et de `3×` sur `D` pour TYPE_0,
dont les **dix** signes désignés sont égaux — la loi conjointe à
l'intérieur du tirage n'est plus celle de `H₀`, et `T` sature. Un
témoin est déclaré *attendu* si `max(|z_att|, |z_D,att|) ≥ Z_c + 2`,
*non attendu* si `≤ Z_c − 2`, indéterminé entre les deux ; il est
*raté* si la détection observée contredit la prédiction.

Ce que cette prédiction a révélé, et que les relations exactes
cachaient : un LCG n'a pas **que** ses relations exactes.

> **Proposition (l'échelle des corrélations partielles).** *Soit `Δ =
> 2^{s−j}`, `1 ≤ j ≤ (s + 1)/2`. Pour les positions `i` d'une même classe
> `x_i ≡ x_ℓ (mod 2^{j−1})`, `b^s_{i+Δ} = b^s_i ⊕ κ ⊕ retenue`, où `κ`
> est constant sur la classe et la retenue vaut 1 avec probabilité
> `w/2^j`, `w` impair, `0 < w < 2^j`, fonction de la classe et de `c`.
> La corrélation `E[(−1)^{b_i} (−1)^{b_{i+Δ}}]` sur la classe vaut donc*
>
>     ± (2^{j−1} − w) / 2^{j−1}  —  un multiple impair de 2^{−(j−1)} :
>     0 (j = 1), ±1/2 (j = 2), ±1/4, ±3/4 (j = 3), ±1/8 … ±7/8 (j = 4), …
>
> *et les classes `x_ℓ` et `x_ℓ + 2^{j−2}` portent le même `w` et des
> signes opposés, de sorte que la corrélation moyenne sur toutes les
> positions est nulle.*
>
> *Preuve.* `a^Δ = 1 + 2^{s−j+2} u` (`u` impair, lemme des exposants) et
> `c Σ_Δ = 2^{s−j} v` (`v` impair), donc `x_{i+Δ} ≡ x_i + 2^{s−j+2} u
> x_i + 2^{s−j} v (mod 2^{s+1})`. Écrivons `x_i = 2^{j−1} x_h + x_ℓ` :
> `2^{s−j+2} u x_i ≡ 2^{s−j+2} u x_ℓ (mod 2^{s+1})`, et `x_ℓ`, résidu des
> `j − 1` bits bas, est constant sur la classe (ils ont pour période
> `2^{j−1}`). Ainsi `x_{i+Δ} ≡ x_i + K (mod 2^{s+1})` avec `K = 2^{s−j}
> W`, `W = (4 u x_ℓ + v) mod 2^{j+1}` impair, constant sur la classe. Le
> bit `s` de `x_i + K` est `b^s_i ⊕ κ ⊕ retenue`, `κ = ⌊W/2^j⌋` le bit
> `s` de `K`, la retenue arrivant au bit `s` si et seulement si `x_i mod
> 2^s ≥ 2^s − 2^{s−j} w`, `w = W mod 2^j` ; pour `x_i` uniforme dans la
> classe et `s − j ≥ j − 1`, ce seuil est un multiple de `2^{j−1}` et la
> probabilité vaut exactement `w/2^j`, indépendamment de `b^s_i`. D'où
> la corrélation `(−1)^κ (1 − 2w/2^j)`. Passer de `x_ℓ` à `x_ℓ + 2^{j−2}`
> ajoute `2^j u ≡ 2^j (mod 2^{j+1})` à `W` : `w` ne change pas, `κ`
> bascule, le signe s'inverse. Pour `j = 1`, `x_ℓ = 0`, `w = 1` et la
> corrélation est exactement nulle. ∎

Mesurée sur le MMIX `>> 22` (`5,6 · 10^6` mots) : au retard `2^{21}`,
`0,000` sur les deux classes ; à `2^{20}`, `+0,500` (positions paires)
et `−0,500` (impaires) ; à `2^{19}`, `−0,750, −0,250, +0,750, +0,250`
selon la classe modulo 4 ; à `2^{18}`, les huit multiples impairs de
`1/8` ; à `2^{17}`, ceux de `1/16` — la proposition au chiffre près. Sur
la grille, ces corrélations sont **cohérentes** dès que `2^{j−1}` divise
le pas : au pas 20 ou 24 jusqu'à `j = 3`, au pas 80 jusqu'à `j = 5`, au
pas impair pas du tout (la classe alterne avec `t`, et la somme sur `t`
s'annule). C'est ce qui a rendu détectable le témoin MMIX `>> 22` au FY
20, dont la relation exacte `2^{22}` est **hors de portée** (`D_max = 1
211 179 < 4 194 304`) : au retard `2^{20} = 20 · 52 428 + 16`, `10` paires
de corrélation `±1/2` donnent `z ≈ 0,5 · 10 · 0,038 · √18 131 = 26`,
observé `−21,8` — la grille lit un LCG **deux octaves** sous sa période.
Et une seconde source, sans structure de puissance de 2 : le multiplicateur
`a^D mod 2^{s+1}` peut être **petit** pour un `D` quelconque ; le bit haut
de `x ↦ a^D x + c_D (mod 2^{s+1})` est alors corrélé à celui de `x` — pour
le MMIX `>> 22`, `a^{582 149} ≡ −3 (mod 2^{23})`, corrélation `+0,088`, et
`582 149 = 79 · 7 368 + 77` retombe sur `9` paires au shuffle 79 : c'est
l'« angle mort exact » de (viii), prédit par `U` à `z_att = −9,2` (famille
`C`, `H = 582 143`) et observé à `−9,6` au même point — maximum de la
grille, avec `8,9` en `A` (`D = 582 133`) et en `B` (`P = 582 135`) — ;
comme `|z_att|` tombe entre `Z_c − 2` et `Z_c + 2`, ce témoin est le seul
« indéterminé » de la grille, et sa détection ne compte ni pour ni
contre. Ces corrélations partielles ne sont pas une faiblesse du test mais
une **extension** de sa couverture, que seule la prédiction par `U`
pouvait mettre en chiffres : la grille reste exacte sous `H₀`, et sous
`H₁` elle voit plus que ses relations.

Les témoins du §164 — onze sous le flux, trois par nuit, à l'échelle de
l'archive (`70 560` tirages, `370` blocs), même grille, même seuil —
sont au tableau du §164 avec, pour chacun, `z_rel` (forme close des
relations exactes), `z_att` (prédiction par `U`, et où), le `z` observé
au point prédit, le maximum de la grille, `z_D` prédit et observé, et
le verdict : treize prédictions confirmées (douze « attendu » détectés,
et le MSVC par nuit, hors de portée, « non attendu » et non détecté), un
indéterminé (l'angle mort du MMIX `>> 22`, prédit `−9,2`, détecté
`−9,6`), aucun raté, aucun faux positif sur `4 × M` statistiques
nulles. Un effet de parité vaut d'être noté : à un
pas **pair**, un décalage de mots impair n'envoie jamais un mot pair sur
un mot pair (`c = 0`), donc pour une période impaire `P₀` les
statistiques `B` et `C` à `P₀` coïncident avec celles à `2 P₀` — seuls
les multiples pairs sont lus — et l'argmax rapporte le plus petit index :
TYPE_2 à shift 1, de période `65 534`, est détecté « à `B 32 767` », et
TYPE_1 par nuit, de période `254`, « à `B 127` » (le Fibonacci `(3, 17)`,
de période impaire `131 071`, l'est à son vrai index). Le test est un
**distingueur** : s'il détecte, le pas, la
famille et l'index désignent la période du bit lu, donc `s` pour un
LCG ou `L` pour un registre, et le décodage de l'état suit (2^{s+1}
hypothèses pour les bits bas d'un LCG, le 7.11 ou le 7.14 pour un
Fibonacci) ; s'il ne détecte pas, aucun générateur de la couverture
(viii) n'a engendré l'archive à pas constant, quels que soient ses
paramètres. Sur l'archive (§164, jeton `381e09440a2b6e25`) : `D = 0` sur `32 673 251` statistiques, max `|z| = 5,07` (flux, pas 21, C `187 227`) à la place d'un maximum de gaussiennes, `z_D = -0,53`, `τ² = 0,03787` — aucun bit lu de l'archive n'a de période, d'anti-période ni de décalage corrélé à portée, sous aucun pas, ni sous le flux ni par nuit : toute la couverture (viii) est fermée.

### 7.17 La synchronisation sous le rejet (§165) — le pas variable lu par la position absolue : vraisemblance exacte d'une fenêtre, chaîne cachée sur `Z/P` et martingale de Ville

Tout ce qui précède depuis le 7.11 lit le générateur **à pas constant** :
le tirage `t` consomme `S` mots (`S = 20…24, 79, 80`), l'alignement
mot–tirage est connu à une constante près, et c'est cet alignement qui
fait des relations de récurrence des équations entre tirages. Or
l'échantillonneur le plus naïf de tous, celui du programmeur pressé,

    tant que |A| < 20 :  x = suivant() ;  v = 1 + (x mod 80) ;  si v ∉ A, A ← A ∪ {v}

consomme un nombre **variable** de mots : `N = 20` acceptés plus les
rejets, `E[N] = 80 (H_80 − H_60) = 22,85`, écart-type `1,85`, `P(N > 40)
= 8,3·10⁻⁹`. Après `t` tirages l'alignement a dérivé de `1,85 √t` mots —
`26` en une nuit, `490` sur l'archive — et un seul mot de décalage suffit
à fausser une relation `r_i = r_{i−K} + r_{i−L}` : les `868` cribles du
7.11 (§157, §158), le décodage mou du 7.13 (§160), les relations de poids
3 du 7.14 et du 7.15 et le balayage du 7.16 sont **aveugles** à cet
échantillonneur, et chacune de ces sections l'a dit — « le rejet est
explicitement hors des cribles ». Cette section le lit. L'idée est de
changer d'inconnue : non plus l'état de `L` bits, mais la **position
absolue** `q ∈ Z/P` dans la suite périodique du bit lu, `P = 2^L − 1` ;
cette position, augmentée du nombre de mots consommés, suit le
générateur à travers les rejets, et le nombre de mots consommés est une
variable cachée que l'on **somme** au lieu de la deviner.

La section établit (i) le canal — ce que l'échantillonneur fait du bit
lu, et la variable cachée ; (ii) la vraisemblance **exacte** d'une
fenêtre de `n` mots, en nombres de Stirling, et son identité de
normalisation ; (iii) la statistique suffisante, le nombre de numéros
impairs, et sa capacité ; (iv) la programmation dynamique de
synchronisation, une chaîne cachée sur `Z/P` à pas variable, et son coût
; (v) le plan 1 pour la sortie décalée de la glibc : les `2^{L−1}`
orbites de période `2P` du Fibonacci modulo 4 ; (vi) les tirages
impossibles, qui sont des exclusions **exactes** ; (vii) le rapport de
vraisemblance du mélange, martingale sous `H₀`, l'inégalité de Ville et
le seuil valable **à tout instant**, sous le flux et par nuit ; (viii) le
taux d'information sous `H₁` et les témoins ; (ix) la couverture, les
angles morts, et la voie qui les ouvre — la DP élaguée, dont on montre
qu'elle reste une surmartingale. Le résultat sur l'archive est au §165.

**(i) Le canal et la variable cachée.** Soit `(β_i)_{i ∈ Z/P}` la suite
périodique du bit que lit l'échantillonneur : le bit 0 du mot `x = r >>
shift`, donc le plan `shift` du générateur. Le mot `x` désigne le numéro
`v = 1 + (x mod 80)`, et `(v − 1) mod 2 = x mod 2 = β` : un mot de bit
`β` désigne un numéro de la **classe** `β` — pair ou impair de `v − 1`,
quarante numéros par classe. Le modèle `H₁` de cette section retient du
générateur **ce seul bit** et tient le reste du mot pour uniforme : un
mot de classe `β` est uniforme sur les `40` numéros de sa classe,
indépendamment des autres mots. Le tirage `t` commence au mot de position
`q_t`, consomme `N_t` mots `q_t, …, q_t + N_t − 1`, et `q_{t+1} = q_t +
N_t (mod P)`. On n'observe ni `q_t` ni `N_t`, seulement l'ensemble
`A_t` — et, pour l'archive triée, seulement `A_t` sans ordre, ce qui ne
perd rien ici (le canal est symétrique dans l'ordre des acceptés). Sous
`H₀`, les `A_t` sont des `20`-sous-ensembles uniformes indépendants, `P₀(A)
= 1/C(80, 20)`.

**(ii) La vraisemblance exacte d'une fenêtre.** Fixons une fenêtre de `n`
mots de bits `β_q, …, β_{q+n−1}`, dont `w₁` valent `1` et `w₀ = n − w₁`
valent `0`, et notons `b = β_{q+n−1}` le bit du dernier mot. Pour un
ensemble `A` de `20` numéros, soit `a₀` (resp. `a₁`) le nombre de ses
numéros de classe `0` (resp. `1`), `a₀ + a₁ = 20`. `S(w, a)` désigne le
nombre de Stirling de seconde espèce.

> **Théorème (vraisemblance d'une fenêtre).** *La probabilité que
> l'échantillonneur à rejet, lancé au mot `q` sur la suite `β`, accepte
> exactement l'ensemble `A` et s'arrête au `n`-ième mot vaut*
>
>     P(A, n | β_q … β_{q+n−1}) = F(w_{1−b}, a_{1−b}) · G(w_b, a_b),
>
>     F(w, a) = a! S(w, a) / 40^w,        G(w, a) = a! S(w − 1, a − 1) / 40^w,
>
> *avec `F(w, a) = 0` si `w < a` ou si `a = 0 < w`, et `G(w, a) = 0` si `a
> = 0` ou `w < a`. Elle ne dépend de `A` que par `a₀`.*
>
> *Preuve.* Un mot est rejeté si et seulement si son numéro a déjà été
> vu ; la suite des numéros désignés détermine donc tout, et
> l'événement « `A` accepté, arrêt au mot `n` » est exactement :
> l'ensemble des numéros désignés par les `n` premiers mots est `A`, et
> le `n`-ième désigne un numéro qu'aucun mot précédent ne désignait. Les
> mots de classe `0` et ceux de classe `1` sont indépendants et ne
> peuvent désigner que des numéros de leur classe. Les `w_{1−b}` mots de
> la classe `1 − b` doivent couvrir exactement les `a_{1−b}` numéros de
> `A` de cette classe : `a_{1−b}! S(w_{1−b}, a_{1−b})` surjections sur
> `40^{w_{1−b}}` suites, soit `F`. Les `w_b` mots de la classe `b`
> doivent couvrir exactement les `a_b` numéros de `A` de la classe `b`, le
> dernier étant une première occurrence : on choisit ce dernier numéro
> (`a_b` façons), et les `w_b − 1` premiers mots couvrent exactement les
> `a_b − 1` autres, `(a_b − 1)! S(w_b − 1, a_b − 1)` façons ; au total `a_b!
> S(w_b − 1, a_b − 1)` sur `40^{w_b}`, soit `G`. Le produit ne dépend de `A`
> que par `(a₀, a₁)`, donc par `a₀`. ∎

> **Corollaire (normalisation).** *Pour toute suite de bits `β` et toute
> position `q`, `Σ_A Σ_{n ≥ 20} P(A, n | β_q…) = 1`. En moyenne sur des
> bits uniformes indépendants, `Σ_A Σ_β 2^{−n} P(A, n | β) = P₀(N = n) =
> 20! S(n − 1, 19) / 80^n · C(80, 20)`, terme à terme.*
>
> *Preuve.* L'échantillonneur s'arrête presque sûrement sur toute suite
> `β` (chaque mot désigne un numéro nouveau avec probabilité `≥ 21/40`
> tant que `|A| < 20`), et les événements `{(A, N) = (A, n)}` forment une
> partition de l'espace des suites de numéros. La seconde identité est le
> théorème appliqué à des bits marginalisés : `v` est alors uniforme sur
> `80` et `N` est le temps de collection de `20` numéros distincts. ∎

Vérifié numériquement à `6·10⁻¹⁷` près. La troncature `n ≤ 40` retenue
par le calcul (`P₀(N > 40) = 8,3·10⁻⁹`, soit `6·10⁻⁴` tirage attendu sur
l'archive) fait de `H₁` une **sous-**probabilité : c'est ce qui rend le
rapport de (vii) une surmartingale plutôt qu'une martingale, et
l'inégalité de Ville n'y perd rien.

**(iii) La statistique suffisante.** Le théorème ne lit de `A_t` que
`a₀(A_t)`, le **nombre de numéros impairs** du tirage (`v` impair ⇔ `v −
1` pair ⇔ classe `0`) : c'est la statistique suffisante du canal, et le
test entier tient dans les `70 560` entiers `a₀(A_t) ∈ {0, …, 20}`. Sous
`H₀`, `a₀ ~ Hypergéométrique(80, 40, 20)`, d'entropie `H(a₀) = 3,010`
bits ; l'archive en donne la moyenne `9,997` et l'entropie empirique
`3,007`. C'est la **capacité** du canal : aucune synchronisation ne peut
apprendre plus de `3,01` bits par tirage sur la position, quel que soit
l'algorithme ; le taux réalisé est en (viii). On notera ce que ce canal
n'est pas : il ne voit ni les plans `1` à `3` du mot (qui, avec le
plan 0, fixent `x mod 16`) ni son résidu modulo `5` — le 7.14 et le 7.15
lisent le plan 1 par ses relations, le rejet les leur cache ; ici, tout
passe par la parité et par la longueur des fenêtres.

**(iv) La programmation dynamique de synchronisation.** Soit `C(i) =
Σ_{j<i} β_j` les sommes cumulées de la suite périodique (prolongée sur
deux périodes), de sorte que `w₁(q, n) = C(q + n) − C(q)` et `b(q, n) =
β_{q+n−1}` s'obtiennent en temps constant. La chaîne cachée est `(q_t)`
sur `Z/P`, à transitions `q → q + n` de probabilité conditionnelle
`P(A_t, n | β_q, …, β_{q+n−1})`, `n ∈ [20, 40]`, prior uniforme `α₀(q) =
1/P` (le générateur a tourné un nombre inconnu de mots avant le premier
tirage), et **évasion** `ε = 10⁻³` par tirage — avec probabilité `ε` la
position est retirée uniformément, ce qui autorise une
resynchronisation après une rupture non modélisée (réamorçage, tirage
sauté, sortie de la troncature). La récurrence avant est

    α_t(q + n) += α_{t−1}(q) · T_{a₀(A_t)}[n][b(q, n)][w₁(q, n)],        puis    α_t ← (1 − ε) α_t + ε Σα_t / P,

avec `T_{a₀}` la table du théorème (ii), `21 × 2 × 41` réels par valeur
de `a₀`, et `Σ_q α_t(q) = P_mél(A_1, …, A_t)`, la vraisemblance du
mélange. Le facteur de Bayes est

    BF_t = P_mél(A_1 … A_t) / P₀(A_1 … A_t) = Σ_q α_t(q) · C(80, 20)^t,

que le calcul porte en `log₂` après normalisation de `α` à chaque
tirage. L'évasion coûte au plus `log₂ 1/(1 − ε) = 0,0014` bit par tirage
sous `H₁` synchronisée. Le coût est `21 · N` évaluations de table par
tirage, `N = P` pour le plan 0 : `L = 11` en `2` s, `L = 15` en `30` s, `L
= 17` en `271` s sur les `70 560` tirages (outil C, machine chargée). Deux
chaînes sont menées : sous le **flux** (une seule position, jamais
remise à zéro — un générateur jamais réamorcé), et par **nuit** (`α`
remis à l'uniforme au début de chacun des `370` blocs — un générateur
réamorcé chaque jour), dont on garde le `log₂ BF` cumulé sur l'archive et
le `log₂ BF` de **chaque** bloc.

**(v) Le plan 1 : la sortie décalée de la glibc.** `random()` rend `(r_i)
>> 1` : le bit lu est le **plan 1** du Fibonacci, `r_i ≡ r_{i−K} + r_{i−L}
(mod 4)`. La suite `(r_i mod 4)` vit sur `(Z/4)^L` ; la récurrence y est
une bijection (`r_{i−L} = r_i − r_{i−K}`), et les `(2^L − 1) 2^L` états de
plan 0 non nul se répartissent en **orbites**. Le plan 0 y est une
`m`-suite de période `P`, et le plan 1 a la période exacte `2P` (Brent,
1994 : `2^{w−1}(2^L − 1)` modulo `2^w` pour un trinôme primitif et un
plan 0 non nul, ici `w = 2`) : chaque orbite compte `2P` états, il y en a
donc `(2^L − 1) 2^L / 2P = 2^{L−1}`, et la variable cachée est le couple
(orbite, position), `N = 2^{L−1} · 2P = (2^L − 1) 2^L` positions —
`16 256` pour TYPE_1, `1,07·10⁹` pour TYPE_2, `4,6·10¹⁸` pour TYPE_3. Les
orbites sont énumérées par épuisement des états, et le calcul vérifie
qu'elles ont toutes la période `2P`. Le cas du plan 0 nul est couvert
par la grille du plan 0 : le plan 1 y est alors lui-même une `m`-suite
(ou zéro). La chaîne (iv) court sur `Z/2P` dans chaque orbite ; `L = 9`
coûte `8` ms par tirage, `L = 10` `34` ms, `L = 11` `150` ms (`3` h par
trinôme). Une troisième suite est lue en sus : la suite **alternée**
`0101…` (`N = 2`), qui est le bit 0 de tout générateur congruentiel
linéaire à module `2^k` et incrément impair rendant son état (TYPE_0 de
la glibc, `rand()` naïfs) — le 7.16 (i) en donne la période `2`.

**(vi) Les tirages impossibles sont des exclusions exactes.** `F(w, a) = 0`
pour `w < a` : une fenêtre qui contient moins de mots de classe `b` que
`A` n'a de numéros de cette classe ne peut pas produire `A`. Si pour un
tirage `a_b(A_t) > max_{q,n} w_b(q, n)`, **aucune** position ne l'explique
: `Σα_t = 0`, `log₂ BF = −∞`, et la configuration (trinôme, shift) est
exclue — non par un seuil, mais par une incompatibilité : le modèle ne
peut produire ce tirage à aucune position, à aucun pas. Le calcul le
consigne comme tel (`−∞`, compteur des tirages impossibles), garde le
maximum courant atteint avant la mort de la chaîne, et par nuit
recommence au bloc suivant. Ainsi `x² + x + 1` (période `3`, deux `1`
pour un `0`) a `w₀ ≤ 14` dans toute fenêtre de `40` mots : tout tirage à
`a₀ ≥ 15` numéros impairs le tue — l'archive en compte `666`, contre
`662,3` attendus sous `H₀` (`P₀(a₀ ≥ 15) = 0,94 %`) ; et les deux trinômes
de degré `3` (période `7`, quatre `1` pour trois `0`, `w₀ ≤ 18`) meurent
sur `a₀ ≥ 19`, un tirage de l'archive (`0,11` attendu sous `H₀`). Dès `L
= 4`, aucune fenêtre n'est trop déséquilibrée et aucun tirage n'est
impossible : l'exclusion redevient statistique.

**(vii) Martingale et inégalité de Ville : un seuil valable à tout
instant.**

> **Théorème.** *Sous `H₀` (tirages uniformes indépendants), `(BF_t)_{t ≥
> 0}` est une surmartingale positive de valeur initiale `1` — une
> martingale sans la troncature `n ≤ 40` — pour la filtration des tirages
> observés. Donc, pour tout `c > 0`,*
>
>     P₀( sup_t BF_t ≥ c ) ≤ 1/c                                     (Ville),
>
> *et la règle « déclarer si `max_{t ≤ T} log₂ BF_t ≥ 23,25` », quel que
> soit `T`, choisi ou non à l'avance, a une erreur de première espèce `≤
> 10⁻⁷`.*
>
> *Preuve.* `P_mél` est une (sous-)probabilité sur les suites de tirages
> : un prior uniforme sur `q_1`, des transitions de chaîne cachée
> (évasion comprise) et, à chaque tirage, une loi conditionnelle `Σ_n
> P(A_t, n | β_{q_t}…)` dont la somme sur `A_t` vaut `1` par le corollaire
> (ii) — `≤ 1` avec la troncature — pour **chaque** trajectoire cachée,
> donc pour leur mélange. D'où `E₀[BF_t | A_1 … A_{t−1}] = BF_{t−1} ·
> Σ_{A_t} P_mél(A_t | A_1 … A_{t−1}) ≤ BF_{t−1}`. L'inégalité maximale de
> Ville pour les surmartingales positives conclut. ∎

Le seuil ne dépend ni de `N`, ni de `t`, ni d'aucune approximation
gaussienne : le prix de l'état — les `log₂ N` bits qu'il faut pour
trouver la position — est payé **dans** la vraisemblance, par le prior
uniforme, et non par le seuil. C'est ce qui distingue ce test des
grilles gaussiennes des 7.13–7.16 : plus de nombre effectif de
statistiques, plus de correction de queue, et un `T` que l'on peut
choisir après coup — le maximum courant est la statistique. Par nuit,
chaque bloc porte sa propre surmartingale issue de `1`, et l'on retient
son `log₂ BF` final ; sur `370` blocs, l'union donne le seuil `23,25 +
log₂ 370 = 31,78` pour « une nuit au-dessus ». La chaîne cumulée par
nuit — produit des `370` surmartingales successives — est encore une
surmartingale au seuil `23,25`. Sur la grille (ix), `51` configurations
× (flux, nuit cumulée) = `102` chaînes à `10⁻⁷` et `51` maxima de nuit
à `10⁻⁷` : `E₀[D] ≤ 1,53·10⁻⁵`.

**(viii) Le taux d'information et les témoins.** À position connue, sur
le canal idéal de (i) (bits indépendants uniformes, résidus uniformes),
`E_{H₁}[log₂ Σ_n P(A, n | β) / P₀(A)] = 1,31` bit par tirage
(Monte-Carlo, écart-type `1,33`, `20 000` tirages), contre `−5,0` bits par
tirage pour une position fausse, et `E₀[LR] = 1,002` sous `H₀` (la
martingale, vérifiée). Le mélange se verrouille donc en `≈ log₂ N /
6,3` tirages et gagne ensuite `1,31` bit par tirage : une nuit de `204`
tirages vaut `≈ 266 − log₂ N` bits, le flux `9·10⁴`. Sur des Fibonacci
**réels** à 32 bits — dont les plans `1` à `3` et le résidu modulo `5` ne
sont pas uniformes, `r_i mod 80 = (r_{i−K} + r_{i−L} − 16·[retenue]) mod
80` : le modèle `H₁` est là **mal spécifié** — le gain mesuré est de `0,8`
à `1,1` bit par tirage, ce qui porte le `log₂ BF` au-dessus du seuil
en une trentaine de tirages après le verrouillage. Témoins (`--selftest`, huit configurations plantées
de `L = 3` à `17`, shifts `0` et `1`, flux et blocs, générateurs 32 bits
avec rejet exact) : le postérieur pique sur la bonne orbite à moins de
`N_T` mots de la vraie position — la DP filtre, elle ne lisse pas : les
rejets du dernier tirage ne sont pas observés, et sa position finale reste
floue de `N_T` — qui porte `0,05` à `0,23` de masse ; `log₂ BF ≫ 23,25`
pour chacun (`30` à `567` bits, seuil franchi entre le `32`ᵉ et le `48`ᵉ
tirage), `< 23,25` pour chaque témoin nul (maximum courant `≤ 2,3`). Témoins croisés
numpy/outil C (`croise.py`, mêmes données, un générateur neuf par bloc)
: `(3, 7)` shift 1, `612` tirages en blocs de `204` — flux `490,7`, nuit
cumulée `508,2`, meilleure nuit `185,8` (nul : `−375,9`, `−373,1`, `−115,7`,
maximum courant `0,19`) ; `(1, 15)` shift 0 — `525,5`, `543,4`, `193,2`
(nul `−441,4`, `−434,8`, `−134,8`, max `0,00`) ; `(3, 7)` shift 0, `300`
tirages en blocs de `100` — `234,4`, `243,4`, `88,2` (nul `−403,4`) ; suite
alternée — `326,6`, `326,6`, `166,3` (nul `−714,5`) ; écart numpy/C `≤
5·10⁻⁵` bit, mêmes instants de maximum, outil C `13` fois plus rapide.
Sous `H₀`, le `log₂ BF` **descend** (Jensen : `E₀[log LR] < 0`), d'environ
`−2,2` bits par tirage à `L = 4` et `−0,6` à `L = 15` — la place d'une
surmartingale nulle est loin sous zéro, et le maximum courant reste
au voisinage des premiers tirages.

**(ix) Couverture, angles morts, et la DP élaguée.** Sont lus, sous le
flux et par nuit : au **shift 0** (sortie brute, le bit 0 est le plan 0)
les `31` trinômes primitifs de degré `≤ 17` — un de degré `2`, deux de
`3`, `4`, `5`, `6`, `9`, `10`, `11`, quatre de `7`, six de `15` et de `17`
(il n'existe pas de trinôme primitif de degré `8`, `12`, `13`, `14`, `16`)
— ; au **shift 1** (`random()`, le bit 0 est le plan 1) les `19` de degré
`≤ 11`, TYPE_1 compris ; la suite alternée. Ne sont pas lus : le plan 0
de TYPE_3 (`N = 2^{31} − 1`) et de TYPE_4 ; le plan 1 de degré `≥ 15`
(TYPE_2 : `N = 1,07·10⁹` ; TYPE_3 : `4,6·10¹⁸`) ; les plans `≥ 2` ; les
échantillonneurs par troncature `(x · 80) >> 32`, qui lisent les bits
hauts et non le bit 0 (7.5) ; et, bien sûr, les échantillonneurs à pas
fixe, cribles ailleurs. Le mur n'est pas l'information — une nuit
rendrait `266 − 31 = 235` bits contre TYPE_3 — mais le coût `21 · N` par
tirage : `4,5·10¹⁰` pour TYPE_3 au plan 0, `64` s par tirage, `52` jours
pour l'archive sur un cœur. La voie qui l'ouvre est l'**élagage** : après
`m` tirages en DP pleine, ne garder que les `B` positions de plus fort
`α` et poursuivre sur elles.

> **Lemme (la DP élaguée reste une surmartingale).** *Soit `α'_t` la DP
> (iv) où, après chaque tirage, une règle quelconque — dépendante des
> données — annule une partie des `α'_t(q)`. Alors `BF'_t = Σ_q α'_t(q) ·
> C(80, 20)^t` est une surmartingale positive sous `H₀`, `BF'_0 = 1`, et
> Ville s'applique au même seuil.*
>
> *Preuve.* La propagation d'un tirage est un noyau positif dont, sous
> `H₀`, l'espérance conditionnelle de la masse sortante vaut au plus la
> masse entrante (corollaire (ii), trajectoire par trajectoire) ; annuler
> des coordonnées après coup ne fait que diminuer la masse. Donc
> `E₀[Σα'_t | passé] ≤ Σα'_{t−1}`. ∎

Sous `H₁`, la vraie position gagne `6,3` bits par tirage sur une position
fausse : après `m = 6` tirages pleins elle domine de `38` bits en moyenne
le gros des positions, et un faisceau `B = 2^{24}` (le `2^{−7}`-quantile
des positions nulles) la retient avec une marge de plusieurs
écarts-types. Le coût devient `m · 21 · N` puis `21 · B` par tirage : pour
TYPE_3 au plan 0, `≈ 6,4` min de DP pleine par nuit puis `0,5` s par
tirage — `≈ 50` h de cœur pour les `370` nuits, `≈ 10` h sous le flux ;
pour TYPE_2 au plan 1 (`N = 1,07·10⁹`), la moitié. TYPE_3 au plan 1 reste
hors de portée : ses `4,6·10¹⁸` positions ne se laissent même pas
parcourir une fois, et le canal (iii) n'offre aucune prise linéaire
pour les chercher autrement — l'inconnue est le couple (plan 0, plan
1) entier, `62` bits, et la vraisemblance d'une fenêtre en est une
fonction symétrique du poids de Hamming, sans transformée qui la
sépare. C'est l'angle mort qui demeure, et il est nommé.

Sur l'archive (§165, jeton `f11c611488262d18`) : grille de `51` configurations en cours, pré-enregistrée avant toute lecture (jeton scellé le 2026-09-02 à 12:41Z) ; les `25` premières (plan 0, degré `≤ 15`) sont lues : `D = 0`, maximum courant du flux `1,46` bit, meilleure nuit `3,12` bits (`x² + x + 1`, avant sa mort au bloc 68), `668` tirages impossibles, tous sur les trinômes de degré `≤ 3` — les valeurs finales sont au §165.


### 7.18 La DP élaguée (§166) — un seul passage en flot, un faisceau, la martingale qui survit : le plan 0 jusqu'à `2³¹`, le plan 1 de TYPE_2

Le §7.17 donne la lecture exacte du pas variable, et bute sur son coût :
`21 · N` par tirage. Pour `N = 2³¹ − 1` (le plan 0 de TYPE_3, `x³¹ + x³ +
1`) cela fait `4,5·10¹⁰` opérations par tirage, `52` jours d'un cœur pour
les `70 560` tirages — et, second verrou aussi net que le premier,
`8,6` Go pour un seul tableau `α` en simple précision. Deux idées lèvent
les deux verrous : **le passage en flot**, qui supprime le tableau et les
`m` passages, et **le faisceau**, qui supprime le facteur `N`.

**(i) Le passage en flot.** La récurrence (iv) du §7.17,

    α_t(p) = Σ_{n=20}^{40} α_{t−1}(p − n) · w_t(p, n),    α_0 ≡ 1,

est **locale à gauche** : `α_t(p)` ne dépend que des `21` valeurs
`α_{t−1}(p − 20), …, α_{t−1}(p − 40)`. En balayant les positions `p` dans
l'ordre croissant, on peut donc calculer **d'un seul coup, à chaque
position, les `m` valeurs** `α_1(p), …, α_m(p)` : chacune ne demande que
des valeurs déjà calculées, aux positions `p − 20 … p − 40`.

> **Lemme (un passage, mémoire `O(m)`).** *Les `m` premiers étages de la
> DP sur les `N` positions se calculent en **un seul balayage** de la
> séquence, avec un anneau de `41` positions × `m` étages — `41 m`
> flottants — au lieu d'un tableau de `N` et de `m` balayages.*
>
> *Preuve.* Récurrence sur `p` : au moment de traiter `p`, l'anneau
> contient `α_1(p′), …, α_{m−1}(p′)` pour `p′ ∈ [p − 41, p − 1]`, ce qui
> suffit à former les `m` sommes ci-dessus ; on y écrit ensuite
> `α_1(p), …, α_{m−1}(p)` et on retient `α_m(p)`. ∎

> **Corollaire (le découpage est exact, donc parallèle).** *Comme
> `α_0 ≡ 1` — la loi a priori est uniforme, et en unités de rapport de
> vraisemblance elle vaut `1` partout — `α_t(p)` ne dépend que des
> `40 t` bits qui précèdent `p`. Un **prologue** de `40 m` positions
> avant le début d'un morceau amorce donc l'anneau à sa valeur EXACTE :
> le balayage se découpe en autant de morceaux qu'on veut, sans aucune
> approximation ni communication.*

C'est ce qui distingue cette DP d'une DP séquentielle ordinaire : le
temps `t` n'est pas la position `p`, et la dépendance en `p` est bornée
par `40 m`. Le coût par position est de `21 m` multiplications-additions
et **une seule** lecture de la fenêtre : les `21` poids de Hamming
`w₁(n) = #{bits 1 dans [p − n, p)}` se lisent d'un registre glissant de
`64` bits par un `popcount` et `20` incréments (`w₁(n+1) = w₁(n) +
bit(p − n − 1)`), et servent aux `m` étages à la fois. Mesure : `1,4·10⁷`
positions par seconde à `m = 40` sur quatre cœurs (chargés), soit
`150` s pour `N = 2³¹` — contre `52` jours pour la DP pleine sur
`70 560` tirages.

**(ii) Le faisceau, et la coupe de Markov.** Après `m` tirages pleins on
ne garde que les `B` positions de plus grand `α_m`, et on poursuit sur
elles seules. Le lemme du §7.17 (l'élagage laisse une surmartingale) dit
que cela ne coûte **aucune** validité. Ce que cela coûte se borne
exactement :

> **Lemme (coupe).** *Sous `H₀`, `E[#{q : LR_q ≥ 2ˣ}] ≤ N 2^{−x}`, où
> `LR_q` est le rapport de vraisemblance de la position `q` seule.*
>
> *Preuve.* `E₀[LR_q] = 1` pour chaque `q` (c'est une martingale de
> moyenne `1`, corollaire (ii) du §7.17), et Markov position par
> position ; puis on somme sur les `N` positions. ∎

Un faisceau de largeur `B` retient donc tout ce qui dépasse la **coupe**
`x = log₂(N / B)` : la vraie position survit dès que son `log₂ LR` cumulé
après `m` tirages dépasse cette coupe. Or la vraie position gagne, mesuré
sur générateurs plantés (Fibonacci 32 bits, rejet exact, plans 0 et 1,
degrés `9`, `15` et `17`, `20` témoins) :

| `m` | `5` | `10` | `15` | `20` | `25` | `30` | `40` |
|---|---|---|---|---|---|---|---|
| `log₂ LR` de la vraie position, moyenne ± é.-t. | `5,5 ± 3,5` | `11,9 ± 3,7` | `17,8 ± 8,7` | `21,4 ± 9,9` | `27,7 ± 10,7` | `33,5 ± 11,5` | `43,6 ± 12,0` |
| minimum sur les `20` témoins | `−1,6` | `4,5` | `4,7` | `6,0` | `8,7` | `16,4` | `23,6` |
| rang médian parmi les `N` positions | `346` | `7` | `4` | `4` | `2` | `2` | `2` |
| rang maximal | `7 957` | `101` | `37` | `19` | `7` | `11` | `20` |

soit `1,09` bit par tirage — et le nombre de positions nulles au-dessus
d'un seuil suit bien `N 2^{−x}` (mesuré à `x = 4, 8, 12` sur `N = 3,3·10⁴`
à `2,6·10⁵`, toujours sous la borne). Pour `N = 2³¹` et `B = 2¹⁶` la
coupe vaut `15` bits : avec `m = 40` tirages pleins la vraie position est
au-dessus dans **tous** les témoins (minimum `23,6`), avec `8` bits de
marge sur le pire. C'est le couple retenu — `m = 40`, `B₁ = 2¹⁶` pendant
`20` tirages, puis `B₂ = 1024` pour la suite, la vraie position étant
alors de rang `≤ 20` : le coût tombe à `21 · B` par tirage, `2·10⁴`
opérations au lieu de `4,5·10¹⁰`.

**(iii) Le faisceau mort, et le mélange qui le ressuscite.** Sous `H₀` le
faisceau finit par mourir : il ne garde que des positions « chanceuses »,
donc corrélées (souvent voisines), et un tirage un peu extrême les tue
toutes à la fois (mesuré : une mort toutes les `≈ 10⁴` nuits-tirages à
`B₂ = 1024`). Ce n'est pas le modèle qui meurt, c'est l'élagage. On
redémarre alors à l'uniforme, et le prix est exactement `log₂ R` :

> **Lemme (mélange sur les redémarrages).** *Soit `τ_1 < … < τ_R` des
> temps d'arrêt et `BF^{(i)}` la surmartingale de la chaîne redémarrée à
> `τ_i` (valant `1` avant `τ_i`). Alors `BF* = (1/R) Σ_i BF^{(i)}` est
> une surmartingale positive de moyenne `≤ 1`, et
> `P₀(sup_t max_i BF^{(i)}_t ≥ 2^s) ≤ R · 2^{−s}`.*
>
> *Preuve.* Chaque `BF^{(i)}` est une surmartingale de moyenne `≤ 1`
> (arrêtée à `1` avant `τ_i` : sa masse de départ est `1`) ; une
> combinaison convexe de surmartingales en est une ; Ville sur `BF*` et
> `BF* ≥ (1/R) max_i BF^{(i)}`. ∎

D'où, pour les chaînes de flux, le seuil `log₂(10⁷) + log₂ 64 = 29,25`
avec un budget de `R = 64` redémarrages — jamais atteint : `≤ 3` par
configuration sur `70 560` tirages.

**(iv) Les dénormaux comme règle d'élagage.** En unités de rapport de
vraisemblance, `α` part de `1` et une position fausse perd `≈ 5` bits par
tirage : après `25` tirages elle est sous `2^{−126}`, la limite des
flottants simples normalisés. Laisser le matériel traiter ces dénormaux
coûte **onze fois** le passage (assistance microcode, mesuré) ; les
mettre matériellement à zéro (`FTZ`/`DAZ`) est *exactement* une règle
d'élagage de plus — donc licite par le lemme du §7.17, et gratuite. Le
détail numérique n'est pas un détail : c'est la règle d'élagage la moins
chère qui soit, et elle rend la sélection des `B` meilleures presque
gratuite (seules les positions au-dessus de `2^{−126}` sont même
proposées).

**(v) Ce que cela ouvre.** Le plan 0 des `32` trinômes primitifs de degré
`18 ≤ L ≤ 31` — `x³¹ + x³ + 1`, celui de TYPE_3, compris — sous le flux :
`3` min par configuration au lieu de `52` jours. Le plan 1 des `6`
trinômes de degré `15` — `x¹⁵ + x + 1`, celui de TYPE_2, `N = 2¹⁴ ·
65 534` — sous le flux : `2` min. Par nuit (`370` chaînes indépendantes,
une par bloc), le coût est celui de la phase pleine multiplié par le
nombre de nuits : accessible jusqu'à `L = 25` (`15` min par
configuration), il vaut `15` h pour `L = 31`, d'où l'échantillon
systématique **d'une nuit sur dix** pour les deux séquences nommées, fixé
d'avance.

**(vi) Ce qui reste hors de portée, et pourquoi — le plan 1 de TYPE_3.**
Les deux plans bas du Fibonacci `r_i = r_{i−K} + r_{i−L} mod 2³²`
s'écrivent

    b_i = b_{i−K} ⊕ b_{i−L}                                (plan 0 : m-suite, `2³¹ − 1` positions)
    c_i = c_{i−K} ⊕ c_{i−L} ⊕ (b_{i−K} ∧ b_{i−L})          (plan 1 : la même récurrence, forcée par la retenue)

Le plan 1 est donc, **à position `q` du plan 0 fixée**, une fonction
*affine* de ses `L` bits initiaux `γ` : `c = A γ ⊕ f(q)`, où `A` est le
déroulement du LFSR et `f(q)` le terme forcé par les retenues. L'inconnue
se factorise en `(q, γ) ∈ Z/(2³¹ − 1) × F₂³¹` : `4,6·10¹⁸` positions, que
l'on ne peut même pas parcourir une fois. Cette factorisation est une
prise réelle — mais aucune des deux moitiés ne se laisse attaquer seule,
et l'obstruction est exactement celle qu'on a démontrée au §7.17 :

> sous des bits uniformes, `(A_t, n_t)` est **indépendant** : la loi
> jointe se factorise en `P₀(A) · P₀(N = n)` (l'identité vérifiée terme à
> terme au §7.17 (iii)). L'alignement seul ne dit **rien** ; et sans
> l'alignement, un tirage ne dit rien non plus sur un bit particulier.
> L'information n'existe que dans le couple.

Ce n'est pas un mur d'information : une nuit rend `204 · 1,31 = 267` bits
contre `62` inconnues. C'est un mur de recherche jointe, et il a deux
issues nommées, qu'il faudra essayer :

1. **L'alternance (type turbo).** Traiter l'alignement comme variable
   latente et les bits comme paramètres : partir de marginales `P(c_j =
   1)` à `1/2`, calculer la loi a posteriori de l'alignement par
   avant-arrière sur la grille `(t, position)` — de largeur `20 t`, donc
   quadratique en la nuit —, en déduire des marginales de bits, itérer.
   Chaque tirage est une mesure « fenêtrée » du poids de Hamming local ;
   c'est un problème de décodage à alignement inconnu, et l'alternance en
   est l'attaque naturelle. Rien ne garantit la convergence : la
   dépendance est faible (`1,31` bit par tirage réparti sur `≈ 23` bits).
2. **La corrélation rapide sur la retenue.** La parité
   `c_i ⊕ c_{i−K} ⊕ c_{i−L}` vaut `b_{i−K} ∧ b_{i−L}`, donc `0` avec
   probabilité `3/4` sous bits uniformes : le plan 1 est un mot de code
   du LFSR `(K, L)` **bruité à `1/4`**, très au-dessus du seuil des
   attaques par corrélation rapide — dès qu'on dispose de bits souples,
   la transformée de Walsh du §7.13 retrouve `γ` en `2³¹` opérations pour
   chaque `q`… mais il faut encore les bits souples, donc (1) d'abord.

**(vii) Pourquoi la linéarisation ne sauve pas non plus.** Le plan 1 est
une suite linéaire récurrente d'ordre `2L + C(L,2)` (7.7, borne atteinte,
mesurée par Berlekamp-Massey : `35, 77, 135, 527` pour `L = 7, 11, 15,
31`) : pour TYPE_3, **`527`** — la forme close est `L(L+3)/2`, vérifiée
ici encore pour `L = 3, 5, 7, 9, 11` (`9, 20, 35, 54, 77`). Autrement
dit, `527` bits **durs** du plan 1, à des positions **connues**,
détermineraient toute la suite par une simple élimination. L'échantillonneur
à rejet ne donne ni l'un ni l'autre :

- *pas de bits durs* : un tirage ne contraint que le **nombre** `a₀` de
  numéros impairs de sa fenêtre, soit `1,31` bit réparti sur `≈ 23` bits —
  `0,057` bit par bit, un canal de capacité si faible qu'aucune recherche
  séquentielle sur les bits ne peut converger (à la profondeur `d`,
  `0,057 d` bits d'information contre `2^d` feuilles) ; seuls les tirages
  extrêmes durcissent (`a₀ = 20` forcerait `n ≥ 20` zéros consécutifs, mais
  son espérance sur l'archive est `0,01`) ;
- *pas de positions connues* : la dérive de l'alignement est `1,85 √t`
  mots, soit `± 26` mots après une nuit ;
- *pas de propagation* : les contrôles de parité du plan 1 sont
  `c_i ⊕ c_{i−K} ⊕ c_{i−L} = b_{i−K} ∧ b_{i−L}`, **exacts** si la position
  du plan 0 est connue, mais **bruités à `1/4`** si elle ne l'est pas.
  Un canal de capacité `0,057` bit rend au mieux un biais `δ = 1 − 2p ≈
  0,28` par bit (`1 − h(p) = 0,057`) ; un contrôle de poids `3` à bruit
  `1/4` transporte un facteur `1 − 2·(1/4) = 0,5`, donc un extrinsèque
  `0,5 δ² ≈ 0,04` contre `0,28` d'a priori, et chaque bit n'appartient
  qu'à **trois** contrôles (le trinôme). La structure n'ajoute presque
  rien, et l'on ne peut pas en fabriquer d'autres : le polynôme minimal
  d'ordre `527` n'a pas de multiple de petit poids à un degré accessible
  (anniversaire : un multiple de poids `4` vit au degré `≈ 2^{176}`).

Le mur est donc nommé, réduit, et chiffré : ce n'est ni l'information
(`92 000` bits disponibles sous le flux pour `527` inconnues linéarisées,
`62` réelles), ni la structure (linéaire d'ordre `527`), c'est le
**décodage souple à alignement inconnu** — et le seul levier qui reste
serait un canal plus riche que la parité, c'est-à-dire une statistique du
tirage qui contraigne plus d'un bit par mot sans faire exploser l'état
caché (7.7 : le nibble vaut `23,5` bits par tirage, mais son état est
`2^{3L−3}`).

Sur l'archive (§166, jeton `061f95021fc425e2`) : grille de `56` configurations (`38` de flux, `18` par nuit), pré-enregistrée avant toute lecture — RESULTAT_718.



### 7.19 Le rejet **masqué** (§167) — l'écriture recommandée d'un tirage sans biais, et pourquoi la vraisemblance ne change pas de forme

Les §7.17 et §7.18 lisent l'échantillonneur du programmeur **pressé** :
`v = 1 + (x mod 80)`, biaisé d'un cheveu (`2³²` n'est pas multiple de
`80`) mais direct. Le programmeur **soigneux** écrit autre chose, et c'est
l'écriture recommandée partout :

    répéter : x = suivant() ; v = 1 + (x mod M) ; jusqu'à v ≤ 80     (M = 100, 128, 256…)

— masquer (`x & 127`) ou prendre `x mod 100`, et **recommencer** si le
résidu dépasse `80`. Le pas devient encore plus variable : `E[N] = 22,85 /
ρ` mots par tirage, `ρ = 80/M`, soit `28,6` (`M = 100`), `36,6`
(`M = 128`), `73,1` (`M = 256`). Aucun crible du dossier ne le lisait.

**(i) Le masque n'est pas corrélé au bit lu.** Parmi les `80` résidus
retenus `0 … 79`, il y a `40` pairs et `40` impairs ; parmi les rejetés
aussi (`M = 100` : `10`/`10` ; `M = 128` : `24`/`24` ; `M = 256` : `88`/`88`).
Donc *un mot est dans la plage avec probabilité `ρ` indépendamment de son
bit `0`*, et un mot dans la plage donne un numéro uniforme parmi les `40`
de sa classe. C'est tout ce qu'il faut.

> **Lemme (la vraisemblance masquée).** *Soit une fenêtre de `n` mots, `W₁`
> de bit `1`, `W₀ = n − W₁` de bit `0`, dernier bit `b`. Alors*
>
>     P(A, n | fenêtre) = Σ_{S ∋ n} ρ^{|S|} (1−ρ)^{n−|S|} · F(w_{1−b}(S), a_{1−b}) · G(w_b(S), a_b)
>
> *où `S` parcourt les parties « dans la plage », et cette somme se
> **factorise** :*
>
>     Ff[W][a] = Σ_j C(W, j)   ρ^j (1−ρ)^{W−j} F(j, a)
>     Gg[W][a] = Σ_j C(W−1, j−1) ρ^j (1−ρ)^{W−j} G(j, a)      (le dernier mot est dans la plage)
>     b = 1 : P = Gg[W₁][a₁] · Ff[W₀][a₀]        b = 0 : P = Ff[W₁][a₁] · Gg[W₀][a₀]
>
> *`ρ = 1` redonne exactement le 7.17.*
>
> *Preuve.* Conditionnellement à `S`, les `|S|` mots dans la plage sont
> exactement le modèle du 7.17 (uniformes dans leur classe, le dernier
> étant la vingtième nouveauté), d'où le facteur `F·G` évalué en
> `w₁(S), w₀(S)`. Le nombre de parties `S ∋ n` à `j` uns et `z` zéros ne
> dépend que des **comptes** : `C(W₁−1, j−1) C(W₀, z)` si `b = 1`,
> `C(W₁, j) C(W₀−1, z−1)` si `b = 0`. Le poids `ρ^{j+z}(1−ρ)^{n−j−z}` se
> scinde en `(j ; W₁)` et `(z ; W₀)`, et `F·G` aussi puisque `F` ne porte
> que sur une classe et `G` sur l'autre : la double somme est un produit
> de deux sommes simples. ∎

**Conséquence.** La statistique suffisante reste `(n, W₁, dernier bit)` —
la seule chose qui change dans les `21 · N` opérations par tirage est le
contenu de la table. **Toute** la machinerie du 7.18 (passage en flot,
faisceau, redémarrages mélangés, Ville) s'applique sans une ligne de
preuve nouvelle. Normalisation vérifiée : `Σ_{A,n} P = 1` à `10⁻⁷` près
pour `M = 80, 100, 128, 256` (le défaut est la troncature `n ≤ n_max`),
et l'outil à `M = 80` reproduit celui du §166 **chiffre pour chiffre**.

**(ii) Ce que le masque coûte en information.** Le tirage consomme `1/ρ`
fois plus de mots, et les mots hors plage ne disent **rien** : ils
diluent la fenêtre. Mesuré sur générateur planté (`x¹⁵ + x + 1`, plan 0,
`1 500` tirages) :

| `M` | `80` | `100` | `128` | `256` |
|---|---|---|---|---|
| `ρ = 80/M` | `1` | `0,80` | `0,625` | `0,3125` |
| mots par tirage | `22,9` | `28,7` | `36,5` | `72,5` |
| `n_max` (à `9 σ`) | `40` | `61` | `87` | `176` |
| **bits par tirage** | `1,02` | `0,475` | `0,314` | `0,092` |

L'information décroît comme `≈ ρ^{1,3}`, mais elle reste **très** au-dessus
du seuil sur l'archive : même à `M = 256`, `70 560` tirages rendraient
`6 500` bits contre un seuil de `29,25`. Le masque ne protège pas ; il
ralentit.

**(iii) Le masque doit être deviné juste.** Planté à `M = 128` et lu à
`M = 80` ou `M = 100`, le facteur de Bayes ne décolle pas (`1,2` et `2,7`
bits sur `250` tirages, contre `187` au bon masque) : le modèle de pas
faux tue la synchronisation. C'est pourquoi le §167 balaie `M` comme il
balaie les trinômes — trois masques de plus, un facteur `3` sur la borne
d'union, rien de plus.

**(iv) Le prix en calcul.** `n` monte à `176` : la fenêtre glissante passe
à **`128` bits** (deux `popcount`), l'anneau du passage en flot à `256`
positions, et le coût par position est multiplié par `n_max/40` — `1,5`
(`M = 100`), `2,2` (`M = 128`), `4,4` (`M = 256`). Le faisceau, lui, ne
change pas de largeur. C'est le prix d'un échantillonneur plus honnête :
on le paie une fois.

Sur l'archive (§167) : grille de `181` chaînes de flux (`M = 100` et `128` sur les `63` trinômes du plan 0 et les `25` du plan 1, `M = 256` sur les types nommés) — RESULTAT_719.



### 7.20 L'excédent par tirage (§168) — ce que le procédé tolère, et la limite exacte où il s'arrête

Tout le §7.17 suppose que le générateur ne sert **qu'à** tirer les vingt
numéros : la fenêtre du tirage `t` est exactement ce qu'il consomme. Un
programme réel en consomme souvent plus — l'ordre d'affichage, une
animation, un « numéro chance », une seconde partie servie par le même
générateur. Soit `delta` mots de plus par tirage. La transition devient

    α_t[(q + n + δ) mod Pi] += α_{t−1}[q] · C(80, 20) · P(A_t, n | bits q … q+n−1)

— **la fenêtre de vraisemblance ne bouge pas, seule la cible se décale.**
Dans le passage en flot, cela se lit d'une ligne : on décale le registre
glissant de `δ` bits (`V' = V >> δ`) et on lit la source `δ` positions
plus tôt. Le coût est nul.

**(i) Un excédent fixe ne coûte qu'un mélange.** `δ` est inconnu mais
constant : on balaie `|Δ|` valeurs, une chaîne par valeur, et le mélange
uniforme (lemme du 7.18 (iii), même preuve) monte le seuil de
`log₂|Δ|` — `4,3` bits pour les vingt valeurs balayées au §168, contre un
gain de `1,09` bit **par tirage**. Autant dire rien.

Témoin (planté `x¹⁵ + x + 1`, plan 0, `7` mots muets par tirage, `300`
tirages) : lu à `δ = 7`, `360` bits ; à `δ = 6`, `309` bits — une fenêtre
peut absorber un mot de plus, le modèle est légèrement dégénéré, ce qui
ne fait qu'aider ; à `δ = 0, 3, 8, 12`, respectivement `0,4`, `1,5`,
`13,6`, `2,5` bits. Le balayage trouve, et ne trouve que, le bon excédent.

**(ii) Un excédent variable : la limite, et elle est exacte.** Si `δ`
change d'un tirage à l'autre, il faut le mélanger **à chaque pas** : la
vraisemblance devient `Σ_δ π(δ) P(A_t, n | …)` et le gain moyen par
tirage tombe de `1,09` à `1,09 − H(π)` bits, où `H` est l'entropie du
mélange (au premier ordre : mélanger `D` valeurs équiprobables divise la
masse par `D`).

> **Critère.** *La synchronisation du 7.17 dérive vers le haut sous `H₁`
> si et seulement si `H(π) < 1,09` bit par tirage — c'est-à-dire pour un
> excédent variable prenant au plus **deux** valeurs. Au-delà,
> l'alignement consomme plus d'information que le canal n'en apporte, et
> aucune longueur de flux n'y change quoi que ce soit : le facteur de
> Bayes dérive vers zéro.*

C'est la limite exacte de toute la série 7.17-7.20, et elle mérite d'être
dite en clair : **un générateur partagé avec un autre jeu**, dont
l'entrelacement varie librement d'un tirage à l'autre, est hors de portée
de ce procédé — non par manque de puissance de calcul, mais parce que le
canal ne porte que `1,09` bit par tirage et que l'alignement en coûte
davantage. Pour l'atteindre il faudrait un canal plus riche (le nibble du
7.7 vaut `23,5` bits par tirage, mais son état caché est `2^{3L−3}`), ou
un tirage ordonné (les douze du §159), ou une autre statistique que la
parité.

**(iii) L'autre axe : à quelle fréquence peut-on réamorcer ?** La même
arithmétique borne une hypothèse voisine — non plus l'excédent, mais le
**réamorçage**. Si le générateur repart d'un état neuf tous les `k`
tirages, chaque bloc doit payer `log₂ N` d'inconnue et le seuil de Ville
augmenté du nombre de blocs, avec `1,09` bit par tirage pour tout revenu :

    k · débit  ≥  log₂(10⁷) + log₂(70 560 / k) + log₂ N

| séquence | `N` | `k` minimal, canal **parité** | `k` minimal, canal **mod 4** |
|---|---|---|---|
| `x⁷ + x³ + 1` plan 0 | `127` | `38` tirages (`3,2` h) | `9` (`0,8` h) |
| `x¹⁵ + x + 1` plan 0 | `32 767` | `45` (`3,8` h) | `10` (`0,8` h) |
| `x⁷ + x³ + 1` plan 1 | `16 256` | `44` (`3,7` h) | `10` (`0,8` h) |
| `x¹⁵ + x + 1` plan 1 | `1,07·10⁹` | `59` (`4,9` h) | `13` (`1,1` h) |
| `x³¹ + x³ + 1` plan 0 | `2³¹ − 1` | `60` (`5,0` h) | `13` (`1,1` h) |

Autrement dit : **un opérateur qui réamorce plus souvent que toutes les
cinq heures échappe au canal de parité** — et les nuits de l'archive
comptant `204` tirages, l'hypothèse « un état par nuit » des §165, §166 et
§170 est confortablement dans le domaine détectable, mais « un état par
heure » (`12` tirages) ne l'est pour aucune des cinq. Le canal mod 4 du
7.21 ramène la barre à `9`-`13` tirages, soit **moins d'une heure et
demie** : c'est la seconde raison, après l'entrelacement, de payer l'état
carré.

**(iv) Ce que le §168 balaie.** Les cinq séquences **nommées** de la
glibc — plans 0 et 1 de `x⁷ + x³ + 1` (TYPE_1) et de `x¹⁵ + x + 1`
(TYPE_2), plan 0 de `x³¹ + x³ + 1` (TYPE_3) — sous les deux
échantillonneurs (`M = 80` et `M = 128`) et vingt excédents `δ ∈ {1 … 12,
14, 16, 20, 24, 30, 40, 59, 79}`, soit `200` chaînes de flux au seuil
`log₂(10⁷) + log₂ 64 + log₂ 20 = 33,57`.

Sur l'archive (§168) : RESULTAT_720.


### 7.21 Le canal **mod 4** (§169) — deux bits par mot au lieu d'un : `5,37` bits par tirage, et l'entrelacement redevient lisible

Le 7.20 se termine sur une limite : la synchronisation ne dérive vers le
haut que si l'entropie de l'excédent par tirage est inférieure au débit
du canal, `1,09` bit. Un générateur **partagé** — servant un autre jeu
entre deux de nos tirages — coûte l'entropie du nombre de mots qu'il
consomme, `H(N) = 2,85` bits (loi exacte du 7.17), donc `1,31 − 2,85 =
−1,54` bit par tirage : illisible, quelle que soit la longueur du flux.
La seule issue est un **canal plus riche**. En voici un, et il est gratuit
en information : il était sous nos yeux.

**(i) Deux bits par mot, pas un.** Le numéro publié donne `v − 1 = x mod
80`, donc `x mod 4` — **deux** bits du mot, pas seulement sa parité
(`80 = 4 · 20` : chaque classe modulo 4 contient exactement `20` des
quatre-vingts numéros). Le 7.17 n'en lisait qu'un parce que l'état caché
du plan 0 seul est une m-suite de `2^L − 1` positions. Lire `x mod 4`
demande le couple (plan 0, plan 1) — c'est-à-dire **exactement les orbites
du Fibonacci mod 4** déjà construites au 7.17 pour le plan 1 de la
glibc : `N = (2^L − 1) · 2^L` positions.

> **Lemme (vraisemblance mod 4).** *Soit une fenêtre de `n` mots dont
> `w_c` sont de classe `c = x mod 4`, le dernier de classe `c*`, et soit
> `a_c` le nombre de numéros tirés dans la classe `c` (`Σ a_c = 20`).
> Alors*
>
>     P(A, n | fenêtre) = [ Π_{c ≠ c*} F₂₀(w_c, a_c) ] · G₂₀(w_{c*}, a_{c*})
>     F₂₀(w, a) = a! S(w, a) / 20^w,   G₂₀(w, a) = a! S(w−1, a−1) / 20^w
>
> *et `Σ_{A, n} P(A, n | fenêtre) = 1` pour toute fenêtre.*
>
> *Preuve.* Même découpage qu'au 7.17 : les mots d'une classe sont
> uniformes parmi les `20` numéros de cette classe, indépendamment ; ils
> doivent couvrir **exactement** les `a_c` numéros tirés de leur classe
> (surjection : `F₂₀`), et le dernier mot, de classe `c*`, est la première
> occurrence de l'un des siens (`G₂₀`). La statistique suffisante est le
> quadruplet `(w_0, w_1, w_2, w_3)` et la classe du dernier mot.
> Normalisation vérifiée numériquement : `1,000000000` (trois fenêtres
> aléatoires, somme sur les `1 771` quadruplets `(a_c)` avec leurs
> multiplicités `Π C(20, a_c)` et sur `n ≤ 60`). ∎

**(ii) Le débit : `5,37` bits par tirage.** Mesuré par Monte-Carlo exact
(`20 000` tirages, fenêtres uniformes) :

    canal de parité (7.17) : 1,31 ± 1,33 bit par tirage
    canal mod 4 (ce lemme) : 5,37 ± 2,34 bit par tirage      (× 4,1)

Quatre fois plus, pour un état caché **carré** (`2^{2L}` au lieu de
`2^L`) : le compromis est bon tant que `2^{2L}` reste parcourable, c'est-à-dire
jusqu'à `L = 15` au plan 0 (`N = 1,07·10⁹`, le coût du §166) et `L = 10`
au plan 1 (`N = 2^{30}`, l'état mod 8). TYPE_3 au plan 0 (`2^{62}`) reste
dehors — c'est le même mur qu'au 7.18 (vi), et il ne bouge pas.

**(iii) Ce que cela ouvre : l'entrelacement.** Le critère du 7.20 devient
`H(π) < 5,37` bits, soit **41** valeurs équiprobables au lieu de `2,5`.
En particulier, un **jumeau entrelacé** — le même générateur servant, entre
deux de nos tirages, un autre tirage du même jeu, donc `N'` mots de loi
`P₀(N')` — coûte `H(N) = 2,85` bits par tirage :

| canal | débit | entrelacement d'un jumeau | net |
|---|---|---|---|
| parité (§7.17) | `1,31` | `−2,85` | **`−1,54`** : illisible |
| mod 4 (ici) | `5,37` | `−2,85` | **`+2,53`** : lisible — `1,8·10⁵` bits sur l'archive |

Et le coût en calcul est nul : le noyau entrelacé est une **convolution**,
`K[Δ] = Σ_{n + n' = Δ} T[n] · P₀(n')` pour `Δ ∈ [40, 80]`, soit `41`
transitions au lieu de `21`. La DP en flot du 7.18 s'applique mot pour
mot ; seules les tables changent (cinq tables indexées par `w_c ≤ 40`, au
lieu d'une indexée par `(n, w₁, b)` — elles sont même **plus petites**).

**(iv) Le prix, et où il s'arrête.** Le coût par position passe de deux à
dix opérations vectorielles (`5` consultations, `4` produits, une
multiplication-addition), et l'état est carré. On paie donc `≈ 5 · 2^L`
fois plus cher qu'au 7.17 pour un canal `4,1` fois plus riche : c'est
rentable exactement quand la richesse achète quelque chose que la
longueur du flux ne peut pas acheter — l'alignement. C'est le cas ici, et
seulement ici.

Sur l'archive (§169, jeton `06785fcaa1f3e711`, scellé le 2026-09-02 à 15:33Z) : grille de `84` chaînes (`25` trinômes `L ≤ 15` à la sortie brute, `17` `L ≤ 10` à la sortie décalée, chacun sans et avec jumeau) — RESULTAT_721.


### 7.22 La calibration de la nulle — ce que les maxima disent quand ils ne disent rien

Les §165 à §170 ne rendent pas seulement « aucune détection » : ils rendent
un **échantillon** de maxima courants, un par chaîne, et cet échantillon est
lui-même une vérification. Sous `H₀`, l'inégalité de Ville donne, pour chaque
chaîne et à tout instant, `P₀(sup_t BF_t ≥ 2ˣ) ≤ 2^{−x}` ; donc, sur `n_eff`
chaînes (en comptant chaque redémarrage du faisceau comme une chaîne, ce que
le mélange du 7.18 (iii) impose de toute façon),

    E₀[#{chaînes de maximum ≥ x bits}] ≤ n_eff · 2^{−x}.

C'est une **borne d'espérance** : elle vaut quelle que soit la dépendance
entre les chaînes — et elles sont fortement dépendantes, puisqu'elles lisent
toutes la même archive. Voici ce qu'on observe, toutes séries confondues :

| `x` (bits) | chaînes de maximum `≥ x` | borne `n_eff · 2^{−x}` |
|---|---|---|
| `2` | `49` | `359,8` |
| `4` | `34` | `89,9` |
| `6` | `25` | `22,5` |
| `8` | `10` | `5,6` |
| `10` | `4` | `1,4` |
| `12` | `0` | `0,35` |
| `16` | `0` | `0,02` |
| `23,25` (seuil) | **`0`** | `1,5·10⁻⁵` |

`217` chaînes lues, `1 439` effectives. La queue colle à la borne — `10` contre
`5,6` à huit bits, `4` contre `1,4` à dix — ce que Markov autorise sans
réserve (`P(# ≥ k) ≤ E[#]/k`), et le maximum absolu de toute la série vaut
`11,76` bits, atteint par une nuit de `x¹⁸ + x⁷ + 1` : **la moitié du seuil, en
bits, et un facteur `2 900` en facteur de Bayes.**

**Et les coordonnées que ces canaux lisent ne bougent pas non plus.** Les
DP des 7.17 à 7.21 lisent `v − 1` modulo `2` (parité), `4` (canal mod 4),
et le crible du 7.6 lit modulo `16` ; le relèvement du 7.8 lit modulo `5`.
Sur les `70 560 × 20 = 1 411 200` numéros publiés :

| `(v − 1) mod` | `2` | `4` | `5` | `8` | `16` | `80` |
|---|---|---|---|---|---|---|
| `χ²` | `0,14` | `0,45` | `2,74` | `1,41` | `6,38` | `53,60` |
| degrés de liberté | `1` | `3` | `4` | `7` | `15` | `79` |
| `z = (χ² − ddl)/√(2 ddl)` | `−0,61` | `−1,04` | `−0,44` | `−1,49` | `−1,57` | `−2,02` |

Tous **en deçà** de leur espérance — et c'est attendu, non suspect : les
vingt numéros d'un tirage étant **distincts**, les comptes par classe sont
négativement corrélés à l'intérieur d'un tirage et leur variance est plus
petite que multinomiale ; le `χ²` classique est ici conservateur. Quant à
la statistique suffisante du canal de parité, son autocorrélation vaut
`−0,0025` à `+0,0039` aux décalages `1, 2, 3, 5, 10` et `204` (une nuit
entière), contre un écart-type de `0,0038` : rien, à tous les décalages
qui comptent.

Ce n'est donc pas seulement « rien n'a été détecté ». C'est : *la loi
entière de l'évidence, sur des centaines de chaînes et des milliards de
positions, est celle que `H₀` prédit* — une martingale de moyenne `1` qui monte un peu, au
hasard, et retombe. Le test n'est pas aveugle (les témoins plantés donnent
`500` à `1 500` bits sur les mêmes chaînes) ; il est **calibré**, et il ne voit
rien parce qu'il n'y a rien à voir.



### 7.23 Du pic à l'état complet — ce qu'une détection donnerait, et pourquoi la chaîne est entière

Une objection légitime, et il faut y répondre en chiffres : la DP des 7.17
à 7.21 ne lit qu'**un ou deux bits par mot**. À supposer qu'elle détecte,
elle rendrait la position `q̂` et le plan bas — pas les `32` plans. Que
vaudrait cette victoire ?

**(i) Ce qu'une détection donne — et ce qu'elle ne donne pas.** Le pic a
posteriori concentre la masse sur une position (mesuré : `0,1` à `0,4`),
et le lissage avant-arrière rend la position de **chaque** tirage :
mesuré sur trois témoins de `60` tirages, la position lissée est exacte
`9` à `22` fois sur `61`, à **`± 2` mots près `34` à `52` fois**, à `± 5`
près `54` à `61` fois, la vraie position portant `0,13` à `0,19` de masse
en médiane. En revanche le chemin de Viterbi ne rend que `15` à `21` pas
**exacts** sur `60`, avec une dérive cumulée de `± 7` à `± 20` mots — et
c'est attendu, pas décevant : le canal de parité porte `1,31` bit par
tirage contre `H(N) = 2,85` bits d'entropie du pas. *Les `n_t` ne sont pas
identifiables par ce canal seul, et ils n'ont pas à l'être.*

Ce que la détection livre, c'est donc : la **suite** (donc le trinôme, le
plan, l'orbite), et l'alignement **à quelques mots près**. C'est
précisément l'ingrédient qui manquait à toute la machinerie de relèvement
des 7.7 à 7.12 — *ces algorithmes-là supposent l'alignement connu*, et
c'est pour cela qu'ils ne s'appliquaient pas sous pas variable.

**(ii) Ce qui resterait.** Les plans hauts : `32 L` bits d'état, soit
`224` (TYPE_1), `480` (TYPE_2), `992` (TYPE_3), `2 016` (TYPE_4).

**(iii) Ce que l'archive en dit, une fois l'alignement connu.** Chaque mot
consommé satisfait `x mod 80 ∈ A_t` — vingt valeurs sur quatre-vingts,
donc `log₂(80/20) = 2` bits par mot, `45,7` bits par tirage (`22,85` mots
en moyenne). D'où le compte :

| | TYPE_1 | TYPE_2 | TYPE_3 | TYPE_4 |
|---|---|---|---|---|
| état à relever | `224` bits | `480` | `992` | `2 016` |
| tirages nécessaires (`45,7` bits chacun) | `4,9` | `10,5` | **`21,7`** | `44,1` |
| soit, à un tirage par `5` minutes | `25` min | `53` min | **`1 h 49`** | `3 h 40` |

**(iv) Comment, et où est le coût.** Le pas fin se résout **avec** les
plans hauts, pas avant eux — et c'est là que le rapport de forces
s'inverse : la contrainte `x mod 80 ∈ A_t` vaut `2` bits par mot, `45,7`
par tirage, contre `2,85` bits d'entropie d'alignement. Autrement dit, le
canal du relèvement est **seize fois** plus riche que ce qu'il faut pour
fixer les `n_t` : la recherche jointe (alignement fin × plans hauts) est
sur-déterminée d'un facteur `16`, et elle part d'une fenêtre de `± 2` à
`± 5` mots au lieu des `21` valeurs a priori. Il n'y a donc rien à
inventer en algèbre — mais il reste un coût, et il faut le dire : la DP ne rend que les plans `0` (ou `0-1`),
tandis que le relèvement de réseau du 7.8 part des **cinq** plans bas
(`r mod 32`). Les plans intermédiaires se prennent au crible incrémental
du 7.6, celui du §155, qui élague à chaque mot sur `x mod 80 ∈ A_t` et
dont le coût mesuré est très en deçà de son `2^{5L}` nominal ; puis le
réseau LLL exact du 7.8 (`lab/lfg_releve.py`, témoin positif au §154)
remonte l'état haut. La difficulté qui bloquait tout était l'alignement,
et c'est elle que cette série lève.

**(v) Et alors la prédiction est exacte.** L'état complet d'un Fibonacci
retardé détermine *tous* les tirages suivants — jusqu'au prochain
réamorçage, que le mode « par nuit » des §165, §166 et §170 teste
séparément. Ce n'est pas « améliorer un peu les chances » : c'est
connaître le tirage.

**(vi) Le témoin de bout en bout (§171).** La jonction n'est plus une
promesse : elle est programmée et vérifiée. Sur un TYPE_1 planté
(`x⁷ + x³ + 1`, sortie `r >> 1`, `224` bits d'état) lu par
l'échantillonneur à rejet, **`25` tirages triés — deux heures de jeu —
suffisent** :

| étape | coût | résultat |
|---|---|---|
| détection (DP sur les orbites mod 4) | `0,3` s | orbite et position trouvées, `15,6` à `29,8` bits de facteur de Bayes |
| crible des plans 2-4 (`2^{21}` candidats) | `23` s | `15` à `157` états bas, **le vrai parmi eux, 3 fois sur 3** |
| relèvement (réseau LLL exact, 7.8) | `2` à `16` s | **l'état 32 bits exact, 3 fois sur 3** |
| prédiction du tirage suivant | immédiat | **ses vingt numéros exacts, 3 fois sur 3** |

Le crible n'utilise qu'une contrainte, mais elle est dure : *sous rejet,
tout mot consommé — accepté ou doublon — a sa classe `x mod 16` dans le
tirage courant*, ce qui tue `30 %` des candidats par mot ; appliquée au
seul intérieur sûr de chaque tirage (marge de `8` mots autour des
frontières lissées, décalages `± 6` balayés), elle fait tomber `2^{21}` à
quelques dizaines. Le reste est l'algèbre du 7.8.

**Ce qui rend le résultat négatif significatif.** La chaîne
détection → alignement → relèvement → état → prédiction est **complète en
principe** :
elle a été **parcourue en entier**, sur générateur planté, en moins d'une
minute de calcul et vingt-cinq tirages de données (§171). Que `D = 0` sur
toutes les grilles ne dit donc pas « nous n'avons pas su chercher » : cela
dit que le **premier** maillon ne se ferme pas, alors que tous les
suivants ont été vérifiés bout à bout, et qu'ils auraient suffi en moins
de deux heures de jeu.


---


### 7.24 La lecture par **troncature** sous pas variable (§172) — pourquoi la DP des 7.17-7.21 ne s'y applique pas, et le crible qui la remplace

Le §8 nomme, parmi ce que la série des §165-§170 laisse dehors, « la
troncature `(x · 80) >> 32` sous pas variable, dont le bit lu n'est pas un
plan bas ». C'est l'écriture *sans biais de modulo* — celle que recommande
tout manuel — et c'est le seul des quatre échantillonneurs usuels qu'aucune
section ne lit quand le pas varie. Cette section la lit. Elle établit (i)
ce que la troncature publie, (ii) un théorème d'**inapplicabilité** — aucun
état fini *déterministe* n'existe ici, et ce n'est pas faute d'ingéniosité
—, (iii) le **lemme du quasi-morphisme**, qui rend la classe additive à un
bit près et donne un automate **non déterministe** sur `(Z/80)^L`, (iv) le
**lemme de la classe** (`2` bits d'élagage par mot), (v) le fait que
l'alignement **ne se branche pas**, (vi) la comptabilité du crible et son
coût `20^L`, (vii) le relèvement par les `δ`, et (viii-x) ce que tout cela
ouvre — **TYPE_1 en vingt secondes** — et ce qu'il laisse dehors.

#### (i) Ce qu'un tirage trié publie sous troncature

> **Lemme de monotonie.** *La classe `c(r) = ⌊80 r / 2³²⌋` est une fonction
> croissante de `r`. Donc **trier les vingt numéros d'un tirage, c'est trier
> les vingt mots acceptés qui les ont produits**.*

*Preuve.* `c` est croissante par construction, et l'échantillonneur publie
`v = 1 + c(x)` ; l'ordre des `v` est donc l'ordre des `x`. ∎

Le tri ne détruit donc **pas** les valeurs — il détruit seulement
l'**affectation** des vingt classes aux positions de la fenêtre. C'est une
différence de nature avec le canal de parité : sous modulo, `v − 1 = x mod
80` ne dit du mot que son bit `0` (7.17) ; sous troncature, `v − 1` dit ses
`log₂ 80 = 6,32` bits de **poids fort**. Un tirage trié porte

`log₂ C(80, 20) = 61,62` bits par tirage

sur la suite des mots — soixante fois ce que la statistique suffisante du
canal de parité expose (`1,02` bit par tirage, 7.17). Toute la difficulté
tient en une phrase : **ces `61,62` bits ne transitent par aucun quotient
fini de l'état.**

#### (ii) Le lemme de la retenue — un théorème d'inapplicabilité

> **Lemme de la retenue.** *Soit `h_i = ⌊r_i / 2^{32−t}⌋` les `t` bits de
> poids fort du mot `i`. Alors*
>
> `h_i = h_{i−K} + h_{i−L} + γ_i (mod 2^t)`,  `γ_i ∈ {0, 1}`
>
> *où `γ_i` est la retenue sortant des `32 − t` bits bas. Sous des mots
> uniformes, `P(γ_i = 1) = 1/2 − O(2^{−t})`, et les deux valeurs sont
> atteintes quel que soit `(h_{i−K}, h_{i−L})`.*

*Preuve.* `r_i = r_{i−K} + r_{i−L} (mod 2³²)` ; en écrivant `r = h·2^{32−t}
+ ℓ`, la somme des parties basses vaut `ℓ_{i−K} + ℓ_{i−L} = γ_i 2^{32−t} +
ℓ_i` avec `γ_i ∈ {0,1}`, d'où la relation. Les parties basses étant libres,
les deux valeurs de `γ_i` sont réalisables. ∎

> **Corollaire (inapplicabilité).** *Pour tout `t < 32`, la suite des `t`
> bits hauts n'est pas autonome : aucun quotient de l'état de cardinal `<
> 2^{32L}` ne **détermine** la sortie de l'échantillonneur par troncature.*

Il n'y a donc **ni plan `0`, ni orbite `Z/P`, ni position absolue, ni
faisceau** : la chaîne cachée du 7.17, la DP en flot du 7.18, le canal
`mod 4` du 7.21 — toute la machinerie des §165-§170 — sont *inapplicables*
à la troncature. Ce n'est pas un aveu : c'est la raison pour laquelle il
fallait un autre outil. Noter le mot **détermine** : le corollaire interdit
un état fini *déterministe*, et rien de plus. Le (iii) passe par la porte
qu'il laisse ouverte.

#### (iii) Le lemme du quasi-morphisme — la classe est additive **à un bit près**

Le corollaire (ii) interdit un état fini **déterministe**. Il n'interdit
pas un automate **non déterministe**, et c'est par là que la chose passe.

> **Lemme du quasi-morphisme de classe.** *Pour tous `a, b ∈ Z/2³²`,*
>
> `c(a + b mod 2³²) = c(a) + c(b) + δ (mod 80)`,  `δ ∈ Δ`, `|Δ| = 2`,
>
> *avec `Δ = {0, 1}` pour la troncature `c(r) = ⌊80r/2³²⌋` et `Δ = {0, −16}`
> pour le modulo `c(r) = r mod 80` (où `−16 ≡ −2³² (mod 80)`).*

*Preuve.* Posons `u = 80r/2³² ∈ [0, 80)`, de sorte que `c(r) = ⌊u⌋`. La
somme `s = a + b` vérifie `u_s = u_a + u_b`, et `⌊x + y⌋ ∈ {⌊x⌋+⌊y⌋,
⌊x⌋+⌊y⌋+1}` ; la réduction `mod 2³²` retranche `80` à `u`, donc rien
`mod 80`. D'où `Δ = {0,1}`. Pour le modulo, `(a+b) mod 80` vaut
`(a mod 80 + b mod 80) mod 80`, ou cela moins `2³² mod 80 = 16` selon qu'il
y a eu débordement. ∎

*Vérification.* Sur `400 000` couples uniformes : exactement deux écarts
observés, `{0, 1}` pour la troncature (`50,1 % / 49,9 %`) et `{0, 64}` pour
le modulo (`49,9 % / 50,1 %`) — jamais un troisième. Et sur `3 993` pas
d'une vraie suite `(3, 7)` : `0` écart hors de l'ensemble prédit.

> **Corollaire (l'automate de classes).** *La suite des classes d'un
> Fibonacci retardé additif est engendrée par un automate **non
> déterministe** d'état `(Z/80)^L` : `c_i = c_{i−K} + c_{i−L} + δ_i`, un
> **bit** de non-déterminisme par mot.*

Au décalage `1` (`x = r >> 1`, l'écriture de `random()`), le bit perdu
ajoute une unité au mot avant la classe : `Δ = {0, 1, 2}`, la troisième
valeur n'étant atteinte qu'avec probabilité `80/2³¹ = 3,7·10⁻⁸`. On la
garde pour rester **exact**.

#### (iv) Le lemme de la classe — deux bits d'élagage par mot

> **Lemme de la classe.** *Sous le rejet, **tout** mot consommé — accepté
> comme refusé — a sa classe parmi les **vingt** valeurs `v − 1` publiées
> par le tirage qui le contient.*

*Preuve.* Un mot accepté publie sa classe, qui est donc dans le tirage. Un
mot refusé l'est parce que sa classe a **déjà** été acceptée dans le même
tirage : elle y est aussi. ∎

Sous `H₀`, un mot satisfait la contrainte avec probabilité `20/80 = 1/4` :
**deux bits d'élagage par mot**, contre **un bit** de non-déterminisme. Le
front décroît. C'est toute la section en une ligne.

*Ce qu'on gagne à passer par la classe plutôt que par un réseau.* Les deux
autres statistiques invariantes par permutation — la somme de fenêtre
`Σ_{i∈A} r_i = (2³²/80)(Σ_j (v_j − 1) + U)`, connue à `2^{26,05}` près,
soit `3,91` bits par tirage, et les bandes extrêmes `(v₍₁₎−1)/80 ≤ r/2³² <
v₍₂₀₎/80`, soit `0,1255` bit par mot ou `2,87` par tirage — sont
**linéaires**, donc utilisables par un réseau, mais elles ne totalisent que
`6,78` bits par tirage, et un réseau sous-déterminé ne rend **aucun verdict
partiel** : il faudrait `32L/6,78` tirages (`33` pour TYPE_1, `146` pour un
degré `31`) avant le premier test, en portant `2,85` bits d'alignement par
tirage sans jamais les élaguer. La règle de classe donne `45,70` bits par
tirage et un test **à chaque mot**. C'est pourquoi le crible, et non le
réseau, mène la marche — le réseau ne servant qu'au relèvement (vii).

#### (v) Et l'alignement ne se branche pas

C'est le point qui distingue ce crible de tout ce que les §165-§170 ont
fait. Le tirage courant n'est pas une inconnue : il se **déduit** des
classes posées. On tient le compte des classes distinctes acceptées depuis
le début du bloc ; dès qu'il atteint `20`, le tirage est clos et le suivant
commence. Un mot dont la classe est déjà acceptée est un **refus**, et il
ne clôt rien.

Le pas variable, qui coûtait `H(N) = 2,846` bits par tirage aux §7.17-§7.21
et qui a imposé toute la machinerie de synchronisation, **coûte ici zéro**.

Reste le plafond par tirage. Je l'ai d'abord présenté comme une simple
précaution contre les chemins dégénérés. **C'est faux : c'est le moteur du
crible**, et il vaut la peine de dire pourquoi.

> **Lemme du contraste de collectionneur.** *Un chemin **vrai** tire ses
> classes dans les `80` et s'arrête quand il en a `20` distinctes : c'est un
> collectionneur sur `80` coupons arrêté à `20`, d'espérance*
>
> `E[N] = Σ_{j=0}^{19} 80/(80 − j) = 22,849` mots.
>
> *Un chemin **faux** a, par construction du crible, toutes ses classes parmi
> les `20` publiées : c'est un collectionneur sur `20` coupons, complet,
> d'espérance*
>
> `E[N] = 20 · H₂₀ = 71,955` mots — **`3,15` fois plus.**

Le plafond exploite exactement cet écart : il coupe la queue longue du faux
chemin sans toucher au vrai. Les deux lois se calculent exactement (chaîne du
nombre de distincts en arithmétique rationnelle d'un côté, `20! S(n,20)/20ⁿ`
de l'autre) :

| plafond `n` | vrai : `P(N > n)` | × `25 000` tirages | faux : `P(clôture)` | élagage |
|---|---|---|---|---|
| `30` | `9,6·10⁻⁴` | `24` | `0,00132` | `9,57` bits |
| `35` | `3,7·10⁻⁶` | `9,4·10⁻²` | `0,00975` | `6,68` bits |
| `40` | `8,3·10⁻⁹` | `2,1·10⁻⁴` | `0,03589` | `4,80` bits |
| **`45`** | **`1,3·10⁻¹¹`** | **`3,3·10⁻⁷`** | **`0,08750`** | **`3,51` bits** |
| `60` | `1,8·10⁻²⁰` | `4,6·10⁻¹⁶` | `0,36061` | `1,47` bits |

`45` est le point retenu : la perte de puissance sur toute une grille vaut
`3,3·10⁻⁷`, et l'élagage `3,51` bits par tirage **en plus** des deux bits par
mot. Passer à `40` gagnerait `1,29` bit de plus pour une perte de `2,1·10⁻⁴`,
ce qui reste défendable ; passer à `60`, comme la première conception le
faisait, jette les deux tiers de l'élagage — et c'est la vraie raison de son
échec, bien plus que l'absence de l'élagage de clôturabilité.

**Combien reste-t-il sur la table ?** Un tirage publie `61,6165` bits et
consomme `22,849` mots : le plafond informationnel est de **`2,697` bits par
mot**, et rien ne peut le dépasser. Le crible en extrait `2` (la classe) plus
`3,51/22,849 = 0,154` (la clôture), soit **`2,154` bits par mot — `79,8 %` du
plafond**. Les `0,543` bits manquants par mot, soit `12,4` bits par tirage,
sont ceux que seule la **vraisemblance complète** donnerait : pondérer chaque
chemin par la loi de `N` au lieu de la couper à `45`. Un crible **dur** ne
peut pas le faire — il n'a que des verdicts, pas des poids — et un traitement
souple ferait perdre l'exactitude. La décroissance passerait de `1,154` à
`1,697` bit par mot, soit `47 %` de mieux ; mais **le pic resterait `20^L`**,
puisqu'il est atteint avant que le premier tirage ne se referme. Ce qui
manque n'ouvre donc aucun degré nouveau : c'est une accélération, pas une
portée.

**Et cela explique la queue lourde du (vi).** Un tirage dont les classes
publiées contiennent des suites consécutives laisse le faux chemin
*collectionner plus vite* : les deux valeurs de `δ` y tombent dans l'ensemble
publié, donc le chemin y gagne des coupons au lieu d'en manquer. La
probabilité de clôture monte, l'élagage tombe, et l'arbre grossit. Les deux
constats — poches surcritiques et contraste de collectionneur — sont le même
phénomène vu par deux bouts.

#### (vi) La comptabilité, et ce qu'elle coûte

| poste | bits |
|---|---|
| mot **libre** (les `L` premiers) : sa classe est choisie parmi les `20` publiées | `+log₂ 20 = +4,3219` |
| mot **déterminé** : `+1` bit de `δ`, `−2` bits de classe | `−1` |
| alignement | `0` |

Le front culmine donc à `20^L` juste après le `L`-ième mot libre, puis
décroît d'un bit par mot : le parcours entier coûte `≈ 2,5 · 20^L` nœuds.

| `L` | `20^L` | nœuds | mesuré (1 fil) | sur `4` fils |
|---|---|---|---|---|
| `4` | `2^{17,3}` | `3,2·10⁵` | `< 0,1` s | — |
| `5` | `2^{21,6}` | `6,4·10⁶` | `0,3` s | — |
| `6` | `2^{25,9}` | `1,3·10⁸` | `3,5` s | `1` s |
| **`7`** | `2^{30,3}` | `2,6·10⁹` | **`69` s** | `20` s |
| `8` | `2^{34,6}` | `6,4·10¹⁰` | `29` min | `7` min |
| `9` | `2^{38,9}` | `1,3·10¹²` | `9,7` h | `2,4` h |
| `10` | `2^{43,2}` | `2,6·10¹³` | `8` j | `2` j |
| `15` | `2^{64,8}` | `6·10¹⁹` | hors de portée | |
| `31` | `2^{134}` | | hors de portée | |

Sur `400` tirages tirés sous `H₀`, la configuration `(3, 7)` visite
`2 564 985 164` nœuds — contre `2,5 · 20⁷ = 3,2·10⁹` prédits — en `69` s,
soit `27` ns par nœud, et rend **zéro survivant**. Le modèle a l'air juste.
Il ne l'est pas.

> **Le modèle est une moyenne, pas une borne — et la queue est lourde.**
> *Le facteur de branchement `2 × P(classe publiée) = 0,50` est
> sous-critique **en moyenne** (mesuré sur `2 000` tirages de l'archive :
> moyenne `0,500`, minimum `0,318`, maximum `0,705`, jamais au-dessus de
> `1`). Mais un tirage qui contient des classes **consécutives** — `25, 26,
> 27, 28` par exemple — crée des **poches surcritiques** : les deux valeurs
> de `δ` y sont publiées à la fois, et le nœud a deux successeurs vivants.
> Un arbre sous-critique en moyenne peut y grossir sans fin.*

C'est une mesure, pas une crainte : au degré `3`, l'ancrage de la **nuit 20**
de l'archive coûte `2,4·10⁹` nœuds contre `2·10⁴` prédits — **dix mille fois
le modèle** —, là où les nuits `0`, `10`, `30`, `40` et `60` coûtent
`1,5·10⁴` à `2,0·10⁴` comme annoncé. C'est ce qui a rendu la partie « par
nuit » de la première grille infaisable.

**Deux corrections suffisent, et elles sont exactes ou nommées.**

1. *Un élagage exact, qui manquait.* Clôturer un tirage demande encore
   `20 − nacc` mots acceptants, donc au moins autant de mots : tout chemin
   vérifiant

   `wd + (20 − nacc) > N_max`

   est **mort**. Le chemin vrai vérifie `wd + (20 − nacc) ≤ N ≤ N_max` à
   chaque instant, donc l'élagage ne perd rien. **Facteur `6` mesuré.**
2. *Le plafond par tirage, de `60` à `45` mots.* `P(N > 45) = 1,3·10⁻¹¹` par
   tirage, soit `3,2·10⁻⁷` sur les `≈ 24 700` tirages qu'une grille
   parcourt : la perte de puissance est **nommée** et négligeable.
   **Facteur `67` mesuré.**

Ensemble, l'ancrage pathologique passe de `2,4·10⁹` à `5,6·10⁶` nœuds au
degré `3`, et le degré `6` n'y coûte que `2,2·10⁹` nœuds — sept secondes. La
morale est générale et vaut pour tout crible dur de ce type : **le coût d'un
parcours sous-critique en moyenne n'est pas borné par sa moyenne**, et il
faut un plafond de nœuds *et* l'exigence d'un parcours complet — une
configuration coupée au plafond n'exclut rien.

*De ce type, et pas des autres.* Les cribles durs antérieurs du dossier —
celui des bits bas du 7.6 (`2^{5L}` états), celui du flux continu du 7.11
(`2^L` hypothèses), celui des trois plans du 7.10 (`2^{3L}`) — sont des
**énumérations à coût fixe** : ils parcourent un espace d'états dont la
taille est connue d'avance, sans arbre de chemins ni boucle interne de
longueur variable. Ils n'ont donc aucun plafond de nœuds dans leur code, et
ils n'en ont pas besoin : la pathologie décrite ici leur est étrangère. Elle
est propre au crible de classes, qui parcourt des **chemins** dont la
longueur à l'intérieur d'un tirage n'est pas bornée d'avance.

*Et elle vaut a fortiori pour le crible en cascade du (xi).* Hors ordre de
flux, l'alignement n'est plus déduit et la comptabilité des classes
acceptées n'est plus disponible : **l'élagage de clôturabilité, qui vaut ici
un facteur `6`, y est inutilisable**. Les pics annoncés au (xi) sont donc
des moyennes eux aussi, et il faudra les mesurer avant de les croire — ce
que la présente section vient d'apprendre à ses dépens.

#### (vii) Le relèvement : les `δ` lus sur la solution donnent le réseau (§173)

Le crible ne pince que les classes — `log₂ 80 = 6,32` bits par mot — et
laisse les `25,68` bits bas. Il n'a pas à faire mieux : les **retenues** les
rendent, et le §173 le **mesure** au lieu de l'affirmer.

Écrivons `r_i = M_i + s_i`, où `M_i = ⌈c_i · 2³²/80⌉` est le bas de la
classe (connu dès que le crible a rendu les `c_i`) et `s_i ∈ [0, W)` avec
`W = 2³²/80` (inconnu, `25,68` bits). La récurrence `r_i = r_{i−K} + r_{i−L}
− 2³² e_i` donne

`s_i = s_{i−K} + s_{i−L} + D_i`,  `D_i = M_{i−K} + M_{i−L} − M_i − 2³² e_i`,

et **`e_i` est déterminé** : une seule des deux valeurs met `D_i` dans
`(−2W, W)`. C'est le même `δ` que le crible branchait — non pas un
artefact, mais la retenue des parties fractionnaires. Les `s_i` sont donc
des formes **affines entières** des `L` premières, `s_i = Σ_m a_{i,m} s_m +
β_i` avec `a_i = a_{i−K} + a_{i−L}` sur les entiers, et la contrainte
`0 ≤ s_i < W` pour tout `i < T` est un problème de **vecteur le plus
proche** dans un réseau de rang `L` plongé dans `Z^T` — exactement la forme
que `lab/lll_exact.py` résout en exact (LLL par la matrice de Gram, puis
Babai).

> **Le bon critère, et ce n'est pas un compte de mots.** *Le point vrai est
> l'unique point du réseau dans la boîte `[0, W)^T` dès que*
>
> `log₂ det Λ ≥ L · (32 − log₂ 80) = 25,68 L`.
>
> *Or `det Λ` croît à la vitesse de la **racine dominante** du trinôme
> `x^L = x^{L−K} + 1`, qui dépend du trinôme et pas seulement de son degré,
> et qui tend vers `1` quand le degré monte. Le nombre de mots nécessaires
> se calcule donc trinôme par trinôme — par élimination de **Bareiss** sur
> la matrice de Gram entière, un calcul flottant n'en gardant aucun chiffre
> puisque les colonnes de la matrice sont presque parallèles.*

| `(K, L)` | | mots nécessaires | tirages |
|---|---|---|---|
| `(2, 5)` | | `311` | `13,6` |
| `(1, 6)` | | `362` | `15,8` |
| **`(3, 7)`** | **TYPE_1** | `399` | `17,5` |
| `(2, 11)` | | `634` | `27,7` |
| `(1, 15)` | TYPE_2 | `848` | `37,1` |
| `(3, 17)` | | `965` | `42,2` |
| `(3, 31)` | TYPE_3 | `1 739` | `76,1` |

Soit, pour TYPE_1, **dix-huit tirages** — une nuit en compte `204`, et même
le degré `31` tient dans une seule nuit. Et le §173 mesure la chaîne
entière sur suite plantée : aux deux décalages, l'état de `32L` bits est
retrouvé **exactement**, et les **vingt numéros du tirage suivant** sont
prédits juste.

*Une correction à consigner.* Une version antérieure de ce paragraphe
annonçait `T ≥ 25,68 L` mots, soit `8` tirages pour TYPE_1. C'était faux :
ce compte confond le nombre de **bits** à trouver avec le nombre de
**coordonnées** qui les donnent. La mesure le corrige d'un facteur cinq — et
il fallait la faire pour s'en apercevoir.

#### (viii) Ce que le crible rend, et ce qu'il ne rend pas

Les témoins plantés (une suite `(K, L)` engendrée, lue par troncature avec
rejet, triée) confirment les deux moitiés :

- **sous `H₀`** — `400` tirages uniformes — le crible rend **`0` survivant**
  pour toutes les configurations essayées, et son coût suit exactement
  `2,5 · 20^L`. C'est le verdict que l'archive doit produire ;
- **sous `H₁`** — l'archive plantée — l'état vrai est **toujours retenu**
  (vérifié classe par classe), mais il n'est pas seul : le crible rend une
  **famille**, parfois vaste, de `L`-uplets compatibles. C'est attendu : les
  tirages publiés étant *engendrés par la suite elle-même*, les chemins
  voisins du vrai survivent aussi. La famille se réduit au relèvement (vii),
  qui, lui, ne laisse passer qu'un point.

Il faut donc dire les choses exactement : **le crible est un test
d'exclusion, pas un identificateur.** Zéro survivant exclut la
configuration — exactement, pas au seuil près. Un survivant ne l'établit
pas : il faut le relever et rejouer.

#### (ix) La variante par plans de bits, et pourquoi on ne la retient pas

On peut aussi cribler les `t` bits de poids fort, avec un élagage `p(t) =
−log₂(1 − P₀(t))` où `P₀(t)` est la probabilité qu'aucune des classes
rencontrées par un intervalle de largeur `80/2^t` ne soit publiée
(`P₀ = 0,524` à `t = 6`, `0,631` à `t = 7`, `0,750` à la limite). Un mot
libre coûte alors `t − p(t)`, un mot déterminé `1 − p(t)`, et l'alignement
`H(N)/E[N] = 0,1246` par mot puisqu'il n'est plus déduit :

> **Théorème (seuil d'auto-entretien).** *Le front décroît si et seulement
> si `p(t) > 1 + H(N)/E[N] = 1,1246`, c'est-à-dire si et seulement si
> `t ≥ 7 = ⌈log₂ 80⌉`.*

Le seuil est le bon — c'est la précision à laquelle la classe devient
presque toujours exacte — mais le pic vaut `2^{6,43 L}` au mieux (`t = 8`)
contre `2^{4,32 L}` pour l'automate de classes : `2^{45}` au lieu de
`2^{30}` pour TYPE_1. L'automate de classes le domine partout, et il est la
bonne lecture : **la classe, et non le bit, est l'observable.**

#### (x) Ce que cela ouvre, et ce que cela laisse dehors

**Ce qui est à portée** : les trinômes primitifs de degré `L ≤ 8`
en quelques minutes, `L = 9` en deux heures, `L = 10` en deux jours —
**TYPE_1 `(3, 7)` compris, en vingt secondes**. Sous les deux décalages, en
flux continu comme par nuit (chaque nuit est un ancrage indépendant, donc
le mode « par nuit » couvre *aussi* le réamorçage quotidien). C'est l'objet
du §172.

**Ce qui reste dehors, et il faut le nommer** : TYPE_2 (`2^{64,8}`),
TYPE_3 (`2^{134}`), TYPE_4 (`2^{272}`) — hors de portée de *cet* ordre de
parcours. Le (xi) en récupère une partie (TYPE_2 tombe à `2^{37}`) ; TYPE_3
et TYPE_4 restent dehors quoi qu'on fasse ici. Le crible rend par ailleurs un verdict **dur** et
non une martingale : l'absence de survivant *exclut* une configuration
parcourue, mais ne se convertit pas en borne de couverture au sens de
Ville pour les configurations **non** parcourues. Les deux régimes sont
complémentaires et doivent être cités séparément.

**Deux remarques pour finir.** D'abord, le lemme du quasi-morphisme vaut
aussi pour l'échantillonneur à **modulo** (`Δ = {0, −16}`) au décalage `0`
— c'est-à-dire un canal à **deux bits par mot** là où les §7.17-§7.21 n'en
lisaient qu'un par *tirage* ; au décalage `1`, `2³¹ mod 80 = 48` double
l'ensemble (`Δ = {0, 1, −48, −47}`, deux bits) et le crible n'est plus
auto-entretenu. Ensuite, le compte en tirages est dérisoire : `25` tirages
suffisent au crible, `8` au relèvement. Ce qui coûte ici n'est pas la
donnée — c'est le front.


#### (xiii) Ce que le crible tolère d'entropie **fraîche** — et la zone grise qu'il laisse

Le 7.26 pose la question que ce dossier n'avait jamais posée : et si le
générateur absorbait un peu d'entropie fraîche **à chaque tirage** ? C'est le
régime intermédiaire `0 < R < b`, celui d'un logiciel qui tire quelques
octets de QRNG par tirage et les mélange à un état — une architecture
courante, et qu'aucune section n'a testée : toutes supposent `R = 0`.

Le crible de classes y répond dans sa propre comptabilité. Sa décroissance
vaut `E[N] = 22,85` bits par tirage (un bit de `δ` contre deux bits de
classe, sur `22,85` mots). Chaque bit d'entropie fraîche injecté est un bit
de branchement de plus. Donc :

> **Limite d'entropie fraîche du crible de classes.** *Le front décroît
> encore tant que*
>
> `R + δ̄ + H(δ) < E[N] = 22,85` bits par tirage,
>
> *soit `R < 2,86` octets par tirage en l'absence d'excédent. Dans la
> variante « mots frais » — le générateur remplace `f` de ses mots par de
> l'entropie pure —, un tel mot coûte `+log₂ 80 − 2 = +4,32` au lieu de
> `−1`, soit un écart de `5,32` : le crible tolère `f ≤ 4` mots frais par
> tirage sur les `23` consommés.*

C'est la même limite que celle de l'excédent (xii), et pour la même raison :
un mot dont la classe n'est pas publiée coûte sans rien rapporter, qu'il
vienne d'un autre jeu ou d'un photon.

**Et cela dessine une zone grise qu'il faut nommer.** Le seuil
informationnel du 7.26 est à `61,62` bits par tirage ; celui du crible est à
`22,85`. Entre les deux —

`2,86 octets < R < 7,70 octets` d'entropie fraîche par tirage

— **l'état est déterminé et le crible ne le trouve pas**. C'est le seul
régime du dossier où l'écart entre *déterminé* et *trouvé* est chiffré des
deux côtés, et il vaut un facteur `2,7`. Combler cet écart — un crible qui
supporterait `61` bits d'injection par tirage — demanderait un élagage de
`61` bits par tirage, soit `2,7` bits par mot au lieu de `2` : il faudrait un
canal plus large que la classe, et il n'y en a pas ici, puisque `log₂ 80 =
6,32` bits par mot est tout ce que le tirage publie.

#### (xi) L'ordre des mots libres : la cascade triangulaire, et ce qu'elle rachète

Le pic `20^L` vient de ce qu'en ordre de flux les `L` premiers mots sont
libres avant que la récurrence ne morde. Mais la relation à trois termes se
lit **dans les deux sens** — connaître deux des indices `(i−L, i−K, i)`
donne le troisième, en avant (`r_i`) comme en arrière (`r_{i−L} = r_i −
r_{i−K}`, au prix d'un bit d'emprunt au lieu d'un bit de retenue). On peut
donc poser les mots libres **n'importe où**, et il y a un placement qui fait
tomber les mots déterminés bien plus tôt :

> **Lemme de la cascade triangulaire.** *Si les mots libres sont placés aux
> positions `p_j = j(L − K)`, `j = 0, …, k−1`, la clôture à trois termes
> détermine exactement les `k(k−1)/2` mots `p_j + mL` pour `1 ≤ m ≤ k−1` et
> `0 ≤ j ≤ k−1−m`.*

*Preuve.* Par récurrence sur `m`. Le mot `p_j + mL` a pour antécédents
`(p_j + mL) − L = p_j + (m−1)L`, du niveau `m−1`, et `(p_j + mL) − K =
(p_j + L − K) + (m−1)L = p_{j+1} + (m−1)L`, du niveau `m−1` lui aussi. Deux
des trois indices étant connus, le troisième l'est. Le compte est
`Σ_{m=1}^{k−1}(k − m) = k(k−1)/2`. ∎

`k` mots libres achètent donc `k(k−1)/2` mots déterminés : **quadratique
contre linéaire**. C'est ce qui casse le `20^L`.

**Mais il faut payer l'alignement.** En ordre de flux, le tirage courant se
déduit (v) ; hors ordre, il ne se déduit plus — pour savoir dans quel tirage
tombe un mot placé en position `p`, il faut avoir branché **toutes** les
frontières en deçà. Et pour un crible **dur**, on n'a pas droit à l'entropie
`H(N) = 2,846` : il faut énumérer *toutes* les valeurs possibles de `N`,
c'est-à-dire `N ∈ [20, 60]`, soit `log₂ 41 = 5,358` bits par tirage franchi.
Le pic devient

`max_k [ k · log₂ 20 − d(k) + 5,358 · (p_max(k) / 22,85) ]`.

| `(K, L)` | | flux `20^L` | ordre choisi, `H(N) = 2,846` | ordre choisi, **crible dur** `log₂ 41` |
|---|---|---|---|---|
| `(3, 7)` | TYPE_1 | `2^{30,3}` | `2^{18,4}` | **`2^{20,9}`** |
| `(4, 9)` | | `2^{38,9}` | `2^{19,0}` | **`2^{22,3}`** |
| `(2, 11)` | | `2^{47,5}` | `2^{22,0}` | **`2^{28,3}`** |
| `(1, 15)` | **TYPE_2** | `2^{64,8}` | `2^{25,8}` | **`2^{37,2}`** |
| `(3, 17)` | | `2^{73,5}` | `2^{26,5}` | `2^{45,9}` |
| `(2, 21)` | | `2^{90,8}` | `2^{30,1}` | `2^{47,3}` |
| `(3, 25)` | | `2^{108,0}` | `2^{42,6}` | `2^{58,9}` |
| `(13, 31)` | | `2^{134,0}` | `2^{39,6}` | `2^{52,4}` |
| `(3, 31)` | TYPE_3 | `2^{134,0}` | `2^{49,6}` | `2^{81,9}` |
| `(31, 63)` | | `2^{272,3}` | `2^{72,0}` | `2^{98,0}` |
| `(1, 63)` | TYPE_4 | `2^{272,3}` | `2^{74,3}` | `2^{129,7}` |

Trois choses à en retenir. D'abord, **la portée passe du degré `7` au degré
`15`** : TYPE_2 tombe à `2^{37,2}`, soit `1,4·10¹¹` nœuds — un quart d'heure.
Ensuite, **le pic dépend du trinôme, pas seulement de son degré** : `(13,31)`
vaut `2^{52,4}` quand `(3,31)` vaut `2^{81,9}`, parce que le pas de la
cascade `L − K` décide de la portée qu'il faut couvrir. Enfin, **TYPE_3 et
TYPE_4 restent dehors** (`2^{82}`, `2^{130}`) : la cascade divise le pic par
`1,6` à `2,1`, elle ne l'annule pas.

C'est un **calcul de conception**, pas une mesure : l'outil du §172 est celui
de l'ordre de flux (alignement déduit, pic `20^L`, degré `≤ 7`). Le crible
hors ordre, qui doit brancher les frontières et propager la clôture dans les
deux sens, est un second outil — il porterait la lecture par troncature
jusqu'à TYPE_2, et c'est la suite naturelle de cette section.

#### (xii) Ce que le crible de classes tolère : l'excédent, et la limite exacte

Le 7.20 a établi, pour le canal de **parité**, une limite sévère : un
excédent **variable** — le générateur consomme `δ_t` mots de plus par
tirage, pour habiller une page, servir un second jeu, ou brouiller — noie
le signal dès que `H(δ) ≥ 1,09` bit, c'est-à-dire dès **deux valeurs**. Le
canal de classes est d'un autre ordre de grandeur, et il vaut la peine de
dire exactement pourquoi.

Un mot **publié** coûte `+1` bit (le `δ` du quasi-morphisme) et rapporte
`−2` bits (sa classe est parmi les vingt) : **`−1` bit net**. Un mot
**d'excédent** est engendré par la même récurrence — il coûte donc lui aussi
`+1` bit de branchement — mais sa classe n'est **pas** publiée : il ne
rapporte rien. Le bilan par tirage devient

`décroissance = E[N] − δ̄ − H(δ) = 22,85 − δ̄ − H(δ)` bits,

où `δ̄` est le nombre moyen de mots d'excédent et `H(δ)` l'entropie de sa
loi (nulle si l'excédent est fixe).

> **Théorème (limite d'excédent du canal de classes).** *Le crible reste
> auto-entretenu tant que `δ̄ + H(δ) < E[N] = 22,85`. Pour un excédent
> **fixe**, cela autorise jusqu'à `δ = 22` mots muets par tirage ; pour un
> excédent **uniforme sur `[0, D−1]`**, jusqu'à `D = 36` valeurs.*

| excédent | reste par tirage | tirages nécessaires |
|---|---|---|
| aucun | `+22,85` | `0,19 L` |
| fixe `δ = 10` | `+12,85` | `0,34 L` |
| fixe `δ = 20` | `+2,85` | `1,52 L` |
| fixe `δ = 22` | `+0,85` | `5,09 L` |
| fixe `δ = 23` | `−0,15` | **le crible diverge** |
| uniforme sur `[0, 15]` | `+11,35` | `0,38 L` |
| uniforme sur `[0, 31]` | `+2,35` | `1,84 L` |
| uniforme sur `[0, 35]` | `+0,18` | `24 L` |
| uniforme sur `[0, 37]` | `−0,90` | **le crible diverge** |

Autrement dit : **un générateur qui consomme jusqu'à deux fois plus de mots
qu'il n'en publie, et dont le surplus est tiré au hasard parmi trente-six
valeurs, reste lisible.** Là où la parité s'arrêtait à deux valeurs, la
classe en tolère trente-six — le rapport des deux canaux, `45,7` contre
`1,02` bit par tirage, se lit directement dans cette limite.

Deux remarques pour être exact. D'abord, ce compte suppose l'excédent
**entre** les tirages ou **dedans**, peu importe : seul le nombre de mots
non publiés compte. Ensuite, il suppose le crible en ordre de flux, où
l'alignement est déduit ; l'excédent y est alors une inconnue de plus à
brancher à chaque frontière, et c'est bien `H(δ)` qu'on paie, pas
`log₂` du nombre de valeurs — car la frontière suivante se **vérifie**
(vingt classes distinctes acceptées), ce qui élague les mauvaises valeurs
au lieu de les porter.

*Note sur le (xi).* Le même argument allège le `log₂ 41 = 5,358` bits par
tirage qui y est facturé à l'alignement du crible hors ordre : c'est une
**borne supérieure**, car les classes déjà posées contraignent les
frontières (un tirage se ferme exactement quand vingt classes distinctes
ont été acceptées). Une mise en œuvre qui propage cette contrainte paierait
moins, et les pics du tableau (xi) sont donc pessimistes.


### 7.25 La source elle-même : ce que le fournisseur annonce, ce que l'archive borne, et où il reste quelque chose

Tout ce qui précède teste des **générateurs logiciels** : glibc, MT19937, les
congruentiels, les Fibonacci retardés, xoshiro, PCG, MWC. Aucune section ne
s'était demandée ce que l'opérateur dit employer. C'est une question de
documentation, pas de mathématiques, et elle change la lecture de tout le
reste.

#### (i) Ce qui est public

Deux faits, tous deux publics et tous deux de seconde main :

- **ID Quantique nomme la Loterie Romande parmi ses clients Quantis**, pour
  son « application de tirage des numéros gagnants » (page *Gaming &
  Lotteries* du fournisseur) ;
- **IGT a signé en 2022 un contrat de longue durée** (jusqu'en 2031) pour la
  plateforme *iLottery* de la Loterie Romande.

L'archive court du **14 septembre 2025** au **25 août 2026** : elle est donc
entièrement dans la période IGT.

**Statut de ces deux faits.** Ce sont une page commerciale et un communiqué,
pas une spécification. Ni l'un ni l'autre ne dit (a) si *Loto Express* — le
tirage aux cinq minutes — passe par le même chemin que les tirages
principaux, ni (b) si l'entropie quantique est **consommée directement** ou
sert de **graine** à un générateur déterministe. Ces deux inconnues sont
exactement celles qui décident si quoi que ce soit est attaquable.

#### (ii) Ce que cela fait au reste du dossier

Il faut le dire sans détour : **si la source est un QRNG consommé
directement, tous les résultats négatifs de ce dossier étaient attendus**, et
le programme entier — les onze mille systèmes, les martingales de Ville, les
cribles de classes — testait une famille à laquelle le système n'appartient
pas. Sa valeur n'est alors plus celle d'une recherche mais celle d'une
**borne** : il établit ce que l'archive ne peut pas être, ce qui reste utile
et n'est pas ce qu'on cherchait.

#### (iii) Le biais publié, et pourquoi il n'arrive pas au tirage

Hurley-Smith et Hernandez-Castro (2020) rapportent des biais au niveau de
l'**octet** sur la sortie brute de Quantis. Le tirage publié n'est pas la
sortie brute : il en est l'image par l'échantillonneur. Ce que l'archive
borne se calcule exactement.

Sur `70 560 × 20 = 1 411 200` numéros publiés, l'effectif attendu par classe
vaut `17 640`. Un biais relatif `d_i` par classe ajoute `17 640 · Σ d_i²` au
`χ²`. Le seuil de détection à `3σ` sur `79` degrés de liberté vaut
`79 + 3√158 = 116,7`. Donc :

> **Toute déviation marginale d'écart quadratique moyen supérieur à
> `0,91 %` par classe aurait été vue.** Le `χ²` mesuré vaut `53,60`
> (`z = −2,02`), **en deçà** de son espérance.

#### (iv) Ce que l'archive exclut de la **chaîne de mise en forme**

C'est le point neuf, et il ne porte pas sur le hasard mais sur le logiciel
qui l'habille. Si l'opérateur lit le flux par mots de `W` bits et les envoie
sur `1…80` par modulo ou par troncature **sans rejet**, le biais de repli
est calculable, et l'archive tranche :

| largeur `W` du mot lu | `χ²` ajouté | écart max | verdict |
|---|---|---|---|
| `8` (un **octet**) | `22 050` | `25,0 %` | **exclu, massivement** |
| `10` | `1 378` | `6,25 %` | **exclu** |
| `12` | `86,1` | `1,56 %` | **exclu** (`χ²` total `165`, `z = 6,8`) |
| `14` | `5,4` | `0,39 %` | invisible |
| `16` | `0,3` | `0,098 %` | invisible |
| `≥ 20` | `< 0,01` | `< 0,01 %` | invisible |

> **L'opérateur ne réduit pas un octet — ni aucun mot de `12` bits ou
> moins — sur `1…80` par modulo ou troncature sans rejet.** C'est la
> première chose que l'archive dise de la chaîne matérielle, et c'est un
> verdict dur. À partir de `14` bits, plus rien ne se voit.

Autrement dit : un biais d'octet du QRNG ne peut atteindre les fréquences
publiées qu'à travers une mise en forme *large* (`≥ 14` bits) ou *avec
rejet*, et dans ce cas il est lissé sous le seuil de `0,91 %`.

#### (v) La fourche, et c'est la seule qui compte

- **QRNG → graine d'un petit générateur (32 bits).** Attaquable, et c'est
  déjà en cours : le balayage des `2³²` amorçages du 7.4 addendum (§161)
  couvre exactement cette branche, pour quatre libc et vingt-et-un
  échantillonneurs.
- **QRNG consommé directement, ou graine d'un CSPRNG (`≥ 256` bits).**
  Hors de portée — et c'est un énoncé sur l'**information**, pas sur
  l'effort : il n'y a pas assez de bits dans l'archive pour distinguer un
  état de `256` bits, quelle que soit la puissance de calcul.

L'archive penche déjà pour la seconde branche : `3 160` paires, `6 400`
covariances, les `χ²` de résidus, les autocorrélations et — désormais —
plusieurs centaines de configurations de la série du rejet donnent toutes le
même verdict.

#### (vi) Ce qui reste, et ce qui n'est pas de ce dossier

Ce qui reste est **documentaire** : la chaîne exacte de mise en forme entre
le photon et les vingt numéros. Le CSV ne la donnera pas — aucune analyse,
si fine soit-elle, ne peut lire une spécification qu'elle n'a pas.

Et il reste, hors du générateur, le **protocole** : c'est par là que les
loteries cassées l'ont été (résultat visible trop tôt, graine égale à
l'heure, réutilisation de flux, complicité interne), et jamais par une
réduction de réseau sur un fichier de résultats. Le dossier en tire déjà la
conclusion défendable — **l'échantillonneur protège plus que le
brouilleur** — et s'arrête là : l'objet est ici la mathématique du
générateur, et le mode d'emploi d'une fraude n'y figurera pas.



### 7.26 Le seuil de reconstructibilité — combien d'entropie fraîche il faut par tirage, et pourquoi l'archive a toujours suffi

Le 7.25 pose une fourche — entropie consommée directement, ou graine d'un
générateur — sans dire où passe exactement la frontière. Elle se pose en une
ligne, et elle est nette.

#### (i) Le lemme du budget

Soit un système qui publie, à chaque tirage, `b = log₂ C(80, 20) = 61,6165`
bits (l'ensemble trié), dont l'état interne compte `S` bits et qui absorbe
`R` bits d'entropie **fraîche** par tirage.

> **Lemme du budget.** *Après `T` tirages, l'inconnu total vaut `S + R·T`
> bits et l'observé `b·T`. L'état est **déterminé au sens de l'information**
> dès que*
>
> `b·T ≥ S + R·T`,  c'est-à-dire  `T ≥ S / (b − R)`  si `R < b`,
>
> *et il ne l'est **jamais**, quels que soient `T` et la puissance de calcul,
> si `R ≥ b`.*

*Preuve.* La suite publiée est une fonction déterministe de `(état initial,
entropie fraîche)`, donc son entropie conditionnelle sachant ces `S + R·T`
bits est nulle. Le nombre de préimages compatibles avec `T` tirages observés
vaut en moyenne `2^{S + R·T − b·T}` : il tombe sous `1` exactement au seuil
annoncé, et reste `≥ 2^{S}` — donc sans espoir — si `R ≥ b`. ∎

#### (ii) Le tableau, et il est brutal

Nombre de tirages nécessaires pour déterminer l'état :

| `S` (bits d'état) | `R = 0` | `R = 8` | `R = 16` | `R = 32` | `R = 48` | `R = 56` | `R ≥ 61,62` |
|---|---|---|---|---|---|---|---|
| `32` | `1` | `1` | `1` | `2` | `3` | `6` | **jamais** |
| `64` | `2` | `2` | `2` | `3` | `5` | `12` | **jamais** |
| `128` | `3` | `3` | `3` | `5` | `10` | `23` | **jamais** |
| **`256`** | **`5`** | `5` | `6` | `9` | `19` | `46` | **jamais** |
| `512` | `9` | `10` | `12` | `18` | `38` | `92` | **jamais** |
| `1 024` | `17` | `20` | `23` | `35` | `76` | `183` | **jamais** |
| `19 937` (MT19937) | `324` | `372` | `438` | `674` | `1 465` | `3 550` | **jamais** |

> **Un CSPRNG de `256` bits réamorcé chaque nuit est déterminé par CINQ des
> `204` tirages de la nuit.** Sa protection n'est pas informationnelle : elle
> est **entièrement calculatoire**. Et symétriquement, une source qui verse
> `≥ 61,62` bits d'entropie fraîche par tirage — **`7,70` octets** — est à
> l'abri de tout, pour toujours, y compris d'une mathématique qu'on n'a pas
> encore inventée.

#### (iii) Le critère de conception, et son prix dérisoire

`7,70` octets par tirage, c'est `1,53` Kio par nuit et **`0,52` Mio pour
l'année entière**. Un Quantis produit cela en une fraction de seconde. Il
n'y a donc **aucune raison de coût** de réamorcer un générateur plutôt que de
tirer frais ; il n'y a qu'une raison d'architecture — on branche une source
d'entropie sur un générateur, parce que c'est ainsi que les bibliothèques
sont faites. C'est exactement là que se joue la fourche du 7.25, et le prix
de la bonne branche est nul.

#### (iv) Ce que ce lemme dit du dossier tout entier

L'archive publie `70 560 × 61,6165 = 4,35` Mbit. **Tout générateur
déterministe jamais proposé pour une loterie a un état très inférieur à
`4,35` Mbit** — MT19937 et ses `19 937` bits sont déterminés par `324`
tirages, soit une heure et demie de jeu.

> **Corollaire.** *L'archive a toujours suffi, informationnellement. Toute la
> difficulté de ce dossier était, depuis le début, **calculatoire**.*

C'est pourquoi le dossier est une collection d'**algorithmes** — la DP de
synchronisation, le faisceau, le crible de classes, le relèvement par
réseau — et non une demande de données supplémentaires. Et cela dit
exactement ce que le §9 peut acheter :

- **plus de tirages** n'achètent rien contre un générateur déterministe
  (déjà déterminé au bout de quelques centaines), et rien du tout contre une
  source rafraîchie ;
- **des tirages ordonnés**, en revanche, changent le débit : `log₂(80!/60!) =
  122,69` bits par tirage au lieu de `61,62`, soit **exactement le double**
  (`×1,991`). Ils divisent par deux le nombre de tirages nécessaires — `163`
  au lieu de `324` pour MT19937, `3` au lieu de `5` pour un état de `256`
  bits — et ils montent le seuil de sécurité à `15,34` octets frais par
  tirage. C'est la seule donnée dont l'acquisition change un ordre de
  grandeur, et c'est bien celle que le §9 réclame depuis le début.

#### (v) Où le lemme ne dit rien, et il faut le dire

Le lemme est une comptabilité d'information, pas un algorithme. « Déterminé »
ne veut pas dire « trouvable » : les `5` tirages qui déterminent un CSPRNG de
`256` bits ne disent pas comment le trouver, et il n'existe aucune méthode
connue pour le faire. Tout l'écart entre les deux — entre *déterminé* et
*trouvé* — est le sujet des 7.6 à 7.24, et le tableau ci-dessus ne fait que
dire **combien de données il faut une fois qu'un algorithme existe**.

Ce qu'il apporte, et qui manquait : la frontière est nette, elle est à
`7,70` octets frais par tirage, et elle sépare deux mondes qui ne se
ressemblent pas — d'un côté un problème de calcul, éventuellement soluble
un jour ; de l'autre une impossibilité de principe, que rien ne lèvera.

#### (vi) Et pourquoi l'archive ne dira jamais de quel côté on est

Il serait commode de **mesurer** `R` sur les données. On ne peut pas, et la
raison est un théorème et non une limite de nos outils.

L'entropie conditionnelle d'un tirage sachant tout le passé vaut exactement
`min(R, b)` : si l'état est déterminé, le seul inconnu restant est l'entropie
fraîche. Donc mesurer `R < b` revient à mesurer un déficit du taux
d'entropie, c'est-à-dire à **compresser** la suite publiée sous `61,6165`
bits par tirage.

> **Corollaire (la fourche est empiriquement indécidable).** *Un test qui
> sépare `R < b` de `R ≥ b` à partir de la seule suite publiée est un
> distingueur ; par l'argument de Yao, un distingueur d'avantage `ε` fournit
> un prédicteur d'avantage `ε / b`. Pour un générateur sûr au sens
> calculatoire, un tel test n'existe pas — quel que soit le volume de
> l'archive.*

C'est la forme exacte de l'impasse, et elle explique une chose qui pouvait
passer pour de la paresse : **la documentation du fournisseur n'est pas un
raccourci autour des mathématiques, c'est le seul instrument disponible.**
Le codeur universel du §52 est la meilleure tentative possible dans cette
direction — `5 133` paramètres, `0` bit extrait de `4,35` Mbit, un déficit
mesuré de `−6,18·10⁻⁵` bit par tirage, c'est-à-dire *négatif* — et il ne
pouvait pas faire mieux : sa classe ne contient pas les générateurs qu'il
faudrait y mettre, et aucune classe traitable ne les contient.


### 7.27 Le **tirage unitaire** (§175) — la portée exacte du crible de classes, et pourquoi le verdict ne dépend pas du protocole

Le §7.24 construit le crible de classes et le §172 l'applique : *aucun* Fibonacci
retardé additif de degré `≤ 7` lu par troncature avec rejet n'engendre l'archive
triée. Ce verdict est dur, mais il portait sur un modèle précis — la machine
consomme des mots jusqu'à vingt classes distinctes, puis passe au tirage suivant,
et rien de plus. Cette section montre que l'hypothèse « et rien de plus » est
**inutile** : le crible meurt à l'intérieur du premier tirage, et l'on peut dire
exactement pourquoi.

**(i) Le mot du bonus, et pourquoi il fallait le regarder.** L'archive publie un
`bonus`, et le §77 avait établi qu'il est **toujours** l'un des vingt numéros
tirés — `70 560` sur `70 560`, là où l'uniforme sur `1..80` en donnerait `17 640`.
Le bonus n'est donc pas un vingt-et-unième numéro : c'est un **index dans le
tirage**, `bonus = triés[⌊u·20⌋]` (§106). S'il vient du même flux, la machine
consomme **au moins un mot de plus par tirage** — et le crible du §172, qui n'en
consomme aucun, teste alors un modèle *décalé d'un mot par tirage*. Après le
vingtième accepté, son automate exige du mot suivant une classe du tirage
**suivant**, là où la machine y met le mot du bonus : le chemin vrai meurt à la
frontière. Zéro survivant, et ce zéro ne dirait rien du générateur.

Le contrôle est exécutable, et il a été exécuté (`h159 --selftest`) : on plante
une suite **avec** mot de bonus, on la donne au crible **sans**, et le chemin vrai
est écarté — `30` cas sur `30` (trois trinômes, deux décalages, cinq règles). Le
trou était donc réel. Le §175 le comble en modélisant la phase bonus :

| règle | ce que la machine fait | ce que le crible en tire |
|---|---|---|
| `bmode 1` | un mot après les vingt, index dans le tableau **trié** | `⌊c/4⌋ = r` publié : **4 classes sur 80** |
| `bmode 2` | retirage dans `1..80` jusqu'à retomber sur un numéro sorti | classe `= bonus − 1` exactement, après une géométrique d'espérance `4` |
| `bmode 3` | index dans l'ordre d'**acceptation** | `⌊c/4⌋ = q`, `q` inconnu de l'archive mais **reconstruit par le chemin** |
| `bmode 4` | index tiré **avant** les vingt | `4` classes sur `80`, en tête de tirage |

Le point de comptabilité vaut d'être noté : sous la troncature,
`⌊x·20/2³²⌋ = ⌊⌊x·80/2³²⌋/4⌋ = ⌊c(x)/4⌋`, donc l'index publie deux bits de la
classe et en laisse deux. Le mot du bonus **rapporte** `log₂(80/4) = 4,3219` bits
d'élagage contre `1` bit de branchement pour son `δ` : la phase bonus rend le
crible *plus* rapide et *plus* informatif, pas moins. Le `bmode 3` est le plus
instructif des quatre : l'ordre d'acceptation n'est pas publié par l'archive
triée, mais le chemin le porte — le crible pose les mots un par un, donc il sait
dans quel ordre les classes ont été acceptées. **Une information que la donnée ne
contient pas devient utilisable parce que la reconstruction la fabrique.**

**(ii) La mesure qui rend tout cela sans objet — `d_max = 0`.** Le crible étendu
a été instrumenté pour publier `d_max`, le plus grand nombre de tirages qu'un
chemin **clôture**. Sur l'archive, à tous les degrés testés :

| `(K, L)` | nœuds | pic du front | `d_max` |
|---|---|---|---|
| `(1,5)` | `7 543 286` | `176 000` | **0** |
| `(2,5)` | `7 564 530` | `176 000` | **0** |
| `(3,5)` | `7 616 000` | `176 000` | **0** |
| `(1,6)` | `149 404 546` | `3 520 000` | **0** |
| `(5,6)` | `154 462 915` | `3 520 000` | **0** |
| `(1,7)` | `2 973 024 814` | `70 400 000` | **0** |

Aucun chemin ne clôture **un seul** tirage. Tout ce que la machine pourrait faire
*entre* deux tirages — mot de bonus, mot de multiplicateur, mots muets,
regrainage, frontière de nuit — arrive après une mort qui a déjà eu lieu. C'est
pourquoi les quatre règles ci-dessus rendent, sur l'archive, exactement le même
compte de nœuds que `bmode 0` : la phase bonus n'est jamais atteinte.

**(iii) Le théorème du tirage unitaire.** Ce n'est pas un accident de mesure : le
nombre attendu de chemins compatibles avec un tirage se calcule **exactement**.

> **Théorème (du tirage unitaire).** Sous la lecture par troncature avec rejet,
> le nombre espéré de chemins de classes qu'un trinôme de degré `L` laisse
> survivre à `T` tirages consécutifs vaut
>
> ```
>     E[survivants] = 40^L · ( Π_{a=0}^{19} m_a/(40 − a) )^T ,
> ```
>
> où `m_a` est le nombre de classes qu'un mot acceptant peut prendre au niveau
> `a`. Pour l'**archive triée** `m_a = 20 − a` et le produit vaut `1/C(40,20)`
> avec `C(40,20) = 137 846 528 820` ; pour un tirage **ordonné** `m_a = 1` et il
> vaut `20!/40!`. D'où
>
> ```
>     trié     :  E = 40^L / C(40,20)^T          37,0043 bits par tirage
>     ordonné  :  E = 40^L · (20!/40!)^T          98,0817 bits par tirage
> ```
>
> Autrement dit : **chaque mot d'état libre rapporte `log₂ 40 = 5,3219` bits, et
> chaque tirage clôturé en coûte `37,0043` bits s'il est trié, `98,0817` s'il est
> ordonné.**

*Démonstration.* Elle se fait **niveau par niveau**, et sous cette forme elle
couvre d'un coup les deux lectures — triée et ordonnée. Appelons *niveau* `a` le
nombre de classes déjà acceptées dans le tirage courant, `a = 0, …, 19`. Un mot
déterminé (`i ≥ L`) offre `2` valeurs de `δ`, chacune tombant sur une classe
donnée avec poids `1/80`. À un niveau `a`, un mot est :

- un **refus** s'il retombe sur l'une des `a` classes déjà acceptées : poids
  `2a/80 = a/40` ;
- un **acceptant** s'il tombe sur l'une des `m_a` classes admissibles : poids
  `2·m_a/80 = m_a/40`.

Le poids total du passage du niveau `a` au niveau `a+1`, en sommant sur le nombre
`m ≥ 0` de refus, est une série géométrique :

```
    w_a = Σ_{m≥0} (a/40)^m · (m_a/40) = (m_a/40)/(1 − a/40) = m_a/(40 − a).
```

Enfin, un mot **libre** (`i < L`) n'a pas le facteur `1/40` du `δ` et de la
classe : il pèse `40` fois un mot déterminé. D'où, pour `T` tirages,

```
    E = 40^L · ( Π_{a=0}^{19} m_a/(40 − a) )^T .                          (★)
```

Il ne reste qu'à instancier `m_a`, le nombre de classes qu'un acceptant peut
prendre :

| lecture | `m_a` | `Π_a m_a/(40−a)` | bits par tirage |
|---|---|---|---|
| archive **triée** — n'importe laquelle des `20 − a` classes non encore sorties | `20 − a` | `20!·20!/40! = 1/C(40,20)` | `37,0043` |
| tirage **ordonné** — la prochaine classe est *lue*, une seule valeur | `1` | `20!/40! = 1/3,354·10²⁹` | `98,0817` |

∎

Trois remarques que la forme (★) rend visibles et que la démonstration par le
collectionneur laissait dans l'ombre.

*Le `δ` du quasi-morphisme vaut exactement `24,6123` bits par tirage.* Sans lui —
c'est-à-dire si la classe était additive — les poids seraient `m_a/(80 − a)` au
lieu de `m_a/(40 − a)`, et le produit trié vaudrait `1/C(80,20)`, l'information
brute du tirage. L'écart est
`Σ_{a=0}^{19} log₂((80−a)/(40−a)) = 61,6165 − 37,0043 = 24,6123` bits, **le même
pour les deux lectures** (`122,6907 − 98,0817 = 24,6090`, à l'arrondi près) : le
prix du bit de retenue ne dépend pas de ce que le tirage publie. C'est la mesure
exacte de ce que coûte la non-additivité de `c(·)`, et elle est faible devant les
`61,6` bits qu'un tirage trié publie — ce qui est précisément la raison pour
laquelle le crible de classes fonctionne.

*L'ordre vaut `61,08` bits et le crible en récupère `61,08`.* Un tirage ordonné
publie `log₂(80!/60!) = 122,6907` bits contre `log₂ C(80,20) = 61,6165` pour un
tirage trié — `log₂ 20! = 61,0742` bits de plus — et le crible passe de `37,00` à
`98,08`, soit exactement `61,08` de plus. **Tout** le supplément d'information de
l'ordre est capté, sans perte. C'est ce que h158 exploitait sans le savoir : sa
portée réelle est `L*(1) = 98,0817/log₂ 40 = 18,4` pour un seul tirage ordonné,
`36,9` pour deux, `73,7` pour quatre — d'où la couverture des degrés `≤ 21` sur
les groupes de deux et quatre tirages consécutifs des vidéos.

*Et le rendement, lui, dépend de la lecture.* Le crible extrait `37,00/61,62 =
60,1 %` de ce qu'un tirage trié publie, contre `98,08/122,69 = 79,9 %` d'un
tirage ordonné. La perte absolue est la même — `24,61` bits — mais elle pèse
deux fois plus lourd sur une donnée qui en publie deux fois moins.

Le seuil `E = 1` tombe à `L* = log₂C(40,20)/log₂ 40 = 37,0043/5,3219 = 6,95`.
D'où la table de portée, qui n'a aucun paramètre ajusté :

| `L` | `E` par tirage | lecture |
|---|---|---|
| `4` | `1,86·10⁻⁵` | un tirage exclut, très largement |
| `5` | `7,43·10⁻⁴` | un tirage exclut |
| `6` | `0,0297` | un tirage exclut |
| `7` | `1,19` | **marginal** : il faut deux tirages (`8,6·10⁻¹²`) |
| `8` | `47,5` | un tirage ne dit rien |
| `9` | `1 902` | — |

et, pour `T` tirages consécutifs, `L* = T · 6,95` : `T = 2` porte jusqu'au degré
`13,9`, `T = 3` jusqu'à `20,9`, `T = 25` — la fenêtre du §172 — jusqu'à `173,8`.
Sur des tirages **ordonnés**, le même seuil vaut `L* = T · 18,43` : *un seul*
tirage porte jusqu'au degré `18` — au-delà de TYPE_2 — et quatre jusqu'au degré
`73`, c'est-à-dire au-delà de TYPE_4. **C'est l'ordre, et lui seul, qui sépare
les degrés que l'on peut exclure d'un tirage de ceux qui en demandent trois.**

**(iii bis) Le nombre de valeurs de `δ` entre dans la formule — et il y a un point
critique.** La démonstration niveau par niveau ne suppose rien sur `n_δ`, le nombre
de valeurs que prend le `δ` du quasi-morphisme. En le gardant :

```
    E = (80/n_δ)^L · ( Π_{a=0}^{19} m_a/(80/n_δ − a) )^T .                (★★)
```

`n_δ = 2` pour la troncature (aux deux décalages) et pour l'échantillonneur à
modulo au décalage `0` (`δ ∈ {0, −16}`) ; `n_δ = 4` pour le modulo au décalage
`1` (`δ ∈ {0, 1, −48, −47}`, le bit perdu). Les trois cas donnent :

| échantillonneur | `n_δ` | archive **triée** | tirage **ordonné** |
|---|---|---|---|
| troncature, décalages `0` et `1` | `2` | `37,0043` bits, `L* = 6,95` | `98,0817` bits, `L* = 18,43` |
| modulo, décalage `0` | `2` | `37,0043` bits, `L* = 6,95` | `98,0817` bits, `L* = 18,43` |
| modulo, décalage `1` | `4` | **`0,0000` bit**, `L*` indéfini | `61,0774` bits, `L* = 14,13` |

La dernière ligne n'est pas un arrondi malheureux, c'est une **identité** : avec
`n_δ = 4` la base tombe à `80/4 = 20`, et sur l'archive triée `m_a = 20 − a`, donc

```
    Π_{a=0}^{19} (20 − a)/(20 − a) = 1     et     E = 20^L   pour TOUT T.
```

> **Corollaire (le point critique).** *Sur l'archive triée, le crible de classes
> appliqué à l'échantillonneur à modulo au décalage `1` est exactement critique :
> chaque mot rapporte autant qu'il coûte, le front ne décroît jamais, et aucun
> nombre de tirages ne le fait converger. Ce n'est pas une question de puissance
> de calcul — la méthode ne s'applique pas.*

C'est la limite structurelle du §172, et elle explique après coup pourquoi son
outil fixait `δ ∈ {0,1}` : au décalage `1` du modulo, il n'avait rien à trouver.
Ce cas-là n'est pas perdu pour autant — il est simplement *hors de portée de
cette lecture-ci* : sur un tirage **ordonné**, `m_a = 1` et le produit vaut
`1/20!`, soit `61,0774` bits par tirage et `L* = 14,13`. **L'ordre rachète le
point critique.** C'est ce que h161 exploite pour cribler les douze tirages des
vidéos sous les quatre lectures, celle-là comprise.

**(iv) Le corollaire qui compte : le verdict est intra-tirage.**

> **Corollaire.** Pour `L ≤ 6`, l'exclusion d'un trinôme se joue **à l'intérieur
> d'un seul tirage**. Elle est donc valable quel que soit le comportement de la
> machine entre deux tirages : mot de bonus (quatre règles), mot de
> multiplicateur, `f` mots muets pour `f` arbitraire, regrainage par tirage,
> frontière de nuit, changement de pas. Aucune de ces variantes n'a besoin d'être
> criblée séparément.

C'est un renforcement net du §7.24 (xiii), qui bornait la tolérance à
`f ≤ 4` mots frais par tirage : au degré `≤ 6`, la borne saute — `f` peut être
quelconque, y compris un regrainage complet à chaque tirage, puisque le crible
n'a jamais besoin de traverser une frontière. Le degré `7` reste, lui, dépendant
de l'enchaînement : `E = 1,19` par tirage, il faut deux tirages consécutifs, et
c'est exactement là que les variantes de protocole ont un sens — d'où la grille
du §175, qui les crible toutes les cinq.

**(iv bis) Le détecteur que la formule fait apparaître, et qui rend le crible
inutile sur cette famille.** La démonstration du (iii) repose sur une seule
quantité : la probabilité qu'une classe *déterminée* tombe sur une classe
publiée. Ce n'est pas une abstraction — c'est une propriété mesurable du tirage,
son **énergie additive** :

```
    T(g₁, g₂) = #{ (u,v) ∈ C_{t−g₁} × C_{t−g₂} : (u+v+δ) mod 80 ∈ C_t , δ ∈ {0,1} }
```

Un Fibonacci retardé additif en laisse par construction, puisque sa relation
*est* une somme de deux classes. Le couple qui porte la trace se lit sur le
générateur : `g₁ ≈ L/22,85`, `g₂ ≈ K/22,85` — c'est-à-dire à combien de tirages
en arrière tombent les deux antécédents, sachant qu'un tirage consomme
`E[N] = 22,85` mots.

La puissance a été mesurée sur générateurs plantés (§177, §178), ramenée aux
`70 560` tirages de l'archive :

| `(K, L)` | | couple | `z` attendu |
|---|---|---|---|
| `(3, 7)` | TYPE_1 | `(0,0)` | `+157` |
| `(1, 15)` | TYPE_2 | `(1,0)` | `+118` |
| `(3, 31)` | TYPE_3 | `(1,0)` | `+120` |
| `(13, 31)` | | `(2,1)` | `+91` |
| `(1, 63)` | TYPE_4 | `(3,0)` | `+143` |
| `(31, 63)` | | `(3,1)` | `+111` |

Mesuré sur l'archive : `|z| ≤ 2,44` sur les quinze couples, `p = 0,22`. **Les
quatre types de la glibc sont écartés, du degré `7` au degré `63`, pour trois
minutes de calcul** — contre les `286` milliards de nœuds que le crible du §172 a
dépensés pour couvrir le degré `≤ 7`.

C'est un renversement de méthode qu'il vaut la peine d'énoncer : *le crible a
buté au degré 7 ; en cherchant pourquoi, on a nommé la quantité dont il se
nourrit ; une fois nommée, elle se mesure sans lui.* Le prix à payer est réel —
un détecteur écarte une famille, il ne rend pas d'état et ne prédit rien — mais
il dit où il vaut la peine de lancer le crible, et sur cette famille-ci la réponse
est : nulle part.

**(v) Ce que la formule dit de la limite du crible.** Elle sépare proprement les
deux murs. L'**information** ne manque jamais : `T = ⌈L/6,95⌉` tirages suffisent
à exclure un degré `L`, soit *trois* tirages pour le degré `20` et *dix* pour le
degré `69`. Le mur est **calculatoire** : le pic du front vaut `20^L`, mesuré
`70 400 000` au degré `7` (contre `20⁷/…` — le front effectif, après élagage de
clôturabilité, vaut `1,28·10⁹/18`). C'est pourquoi le crible s'arrête au degré
`7` en flux et `6` par nuit, alors qu'il aurait assez d'information pour aller
bien plus loin. Toute avancée sur cette famille passe donc par une réduction du
front — pas par plus de données.

Et cela referme la question posée au §7.26 sous un autre angle : on savait que
l'archive publie toujours *assez* de bits pour déterminer l'état ; on sait
maintenant, pour cette famille précise, **combien de tirages** il en faut, et que
c'en est un seul dès le degré `6`.


### 7.28 La famille des **détecteurs d'énergie** — un principe, et sa règle de portée

Le §7.27 démontre le théorème du tirage unitaire et, au (iv bis), en tire un
détecteur. Les §177 à §182 en construisent six. Ils ont tous la même forme, et il
vaut la peine de l'écrire une fois pour toutes — parce que la forme dit
exactement ce qu'ils couvrent, et surtout ce qu'ils ne couvrent pas.

**(i) Le principe.** Soit un générateur dont l'état évolue par une récurrence à
deux termes dans un groupe `(G, ⋆)` :

```
    r_i = (α · r_{i−K}) ⋆ (β · r_{i−L}) .
```

Soit `φ` la lecture — ce que le tirage publie du mot. Si `φ` est un
**quasi-morphisme** de `(G, ⋆)` vers un groupe fini `(H, ⊙)`, c'est-à-dire si

```
    φ(x ⋆ y) = φ(x) ⊙ φ(y) ⊙ δ ,     δ dans un support S petit,
```

alors *tout triplet de mots liés par la récurrence laisse une coïncidence dans
`H`*, et cette coïncidence se compte par une **convolution dans `H`** :

```
    T(α, β, g₁, g₂) = # { (u,v) ∈ C_{t−g₁} × C_{t−g₂} : (α·u) ⊙ (β·v) ⊙ δ ∈ C_t , δ ∈ S } .
```

Les deux instanciations utilisées :

| `(G, ⋆)` | lecture `φ` | `(H, ⊙)` | `S` | convolution | section |
|---|---|---|---|---|---|
| `Z/2³²`, `+` | troncature `⌊x·80/2³²⌋` | `Z/80`, `+` | `{0,1}` | circulaire | §177–§179 |
| `Z/2³²`, `+` | modulo `x mod 80` | `Z/80`, `+` | `{0,−16}` | circulaire | §180 |
| `Z/2³²`, `⊕` | six bits de tête | `F₂⁶`, `⊕` | `{0}` | Walsh-Hadamard | §182 |

La ligne du milieu mérite un mot : `2³² mod 80 = 16`, d'où `δ ∈ {0,−16}` au
décalage `0` et `{0,1,−48,−47}` au décalage `1`. La ligne du bas est la plus
propre — le `XOR` n'a pas de retenue, donc `S = {0}` exactement — mais elle paye
ailleurs : la classe ne détermine les six bits de tête qu'à une ambiguïté de deux
près, puisque l'intervalle d'une classe est large de `2^{25,68}` contre `2^{26}`
par case.

**(ii) La règle de portée.** Le couple de décalages qui porte le signal se lit
sur le générateur, sans rien calculer. Il faut d'abord écrire la relation sous la
forme *« somme = … »*, puis compter les retards **depuis le mot de la somme** :

```
    r_s = r_{s−d₁} ⋆ r_{s−d₂}     ⟹     g_j = d_j / E[N] ,
    E[N] = Σ_{k=0}^{19} 80/(80−k) = 22,848709…  mots par tirage
```

(la constante est exacte, `80·(H₈₀ − H₆₀)`, de variance `3,4319` — ce sont les
deux valeurs que le budget du crible du §172 utilise déjà). Vérification sur les
cas mesurés :

| générateur | forme « somme = … » | `(d₁, d₂)` | `(g₁, g₂)` prédit | couple observé |
|---|---|---|---|---|
| TYPE_1 `(3,7)` additif | `r_i = r_{i−3} + r_{i−7}` | `(7, 3)` | `(0,31 ; 0,13)` | `(0, 0)` |
| TYPE_2 `(1,15)` | `r_i = r_{i−1} + r_{i−15}` | `(15, 1)` | `(0,66 ; 0,04)` | `(1, 0)` |
| TYPE_3 `(3,31)` | `r_i = r_{i−3} + r_{i−31}` | `(31, 3)` | `(1,36 ; 0,13)` | `(1, 0)` |
| TYPE_4 `(1,63)` | `r_i = r_{i−1} + r_{i−63}` | `(63, 1)` | `(2,76 ; 0,04)` | `(3, 0)` |
| Knuth `(24,55)` **soustractif** | `r_{i−24} = r_i + r_{i−55}` | `(31, −24)` | `(1,36 ; −1,05)` | `(1, −1)` |

La dernière ligne est celle qui compte : réécrite avec la somme à gauche, la
relation de Knuth a un retard **négatif** — l'un des opérandes est `24` mots
*après* la somme. La règle le donne sans rien essayer, et c'est exactement le
couple `(1, −1)` que la mesure trouve.

C'est *tout* le contenu du balayage : un retard de `L` mots est un retard de
`L/22,85` tirages. TYPE_3 `(3,31)` sort en `(1,0)` parce que `31/22,85 = 1,36` et
`3/22,85 = 0,13` ; TYPE_4 `(1,63)` en `(3,0)` ; `(31,63)` en `(3,1)`.

Et la règle dit aussi **où sont les angles morts**, ce qui a servi deux fois :

- si `K` dépasse un tirage, `g₂ ≥ 1` : un balayage limité à `g₂ = 0` manque
  `(13,31)` et `(31,63)` — c'est ce que le §178 a dû corriger ;
- si la récurrence est **soustractive**, la somme tombe dans un tirage *antérieur*
  aux opérandes, donc l'un des décalages est **négatif** : un balayage positif
  manque le `ran_array` de Knuth `(24,55)` — c'est ce que le §179 a dû corriger.

Les deux fois, l'angle mort a été trouvé en posant la même question : *quelle
forme de la relation ce balayage ne peut-il pas voir ?*

**(iii) La loi de dégradation.** La puissance décroît quand le support `S`
grandit — une coïncidence est d'autant plus banale que `δ` a plus de valeurs.
Mesuré, sur `(1,15)` planté, `z` ramené aux `70 560` tirages :

| lecture | `\|S\|` | `z` |
|---|---|---|
| troncature | `2` | `+119` |
| modulo décalage `0` | `2` | `+130` |
| coefficients `(1,2)` | `≤ 3` | `+92` |
| modulo décalage `1` | `4` | `+87` |

L'ordre de grandeur suit `1/√\|S\|`, ce qui est exactement ce qu'on attend d'un
comptage : le signal est le même, le bruit croît comme la racine du nombre de
cases comptées.

**(iii bis) La robustesse au masquage — et pourquoi elle est structurelle.** Le
§7.24 (xii) donne la limite du *crible* face à un excédent de mots muets :
`δ̄ + H(δ) < 22,85`. Le détecteur, lui, s'en moque presque. Mesuré sur générateurs
plantés, `2 500` tirages, `z` ramené aux `70 560` de l'archive :

| masquage par tirage | `(3,7)` | `(1,15)` | `(3,31)` |
|---|---|---|---|
| aucun | `+158` | `+108` | `+118` |
| fixe `10` | `+164` | `+76` | `+146` |
| fixe `40` | `+153` | `+77` | `−19` |
| aléatoire `0..10` | `+162` | `+66` | `+145` |
| aléatoire `0..40` | `+162` | `+65` | `+68` |
| **aléatoire `0..200`** | `+156` | `+75` | `−22` |

Deux cents mots muets tirés au hasard à chaque tirage — dix fois la consommation
utile — et le signal tient encore à `|z| ≥ 19`, là où le seuil de Bonferroni est à
`3,5`. La raison est structurelle et se lit sur la règle de portée : quand le
masquage brouille l'alignement *entre* tirages, le couple gagnant **retombe sur
`(0,0)`**, c'est-à-dire sur la part de la relation qui vit *à l'intérieur* d'un
tirage — et celle-là, aucun mot muet inséré entre les tirages ne peut l'atteindre.

C'est l'inverse exact de la faiblesse du crible : le crible a besoin de traverser
les frontières, le détecteur non.

**(iii ter) La nulle est calculable — et il faut la calculer.** Toutes ces
statistiques ont une espérance **exacte** sous SRS, et s'en passer coûte cher :

> **Proposition.** Sous SRS `20/80`, `E[T] = 100·|S|` pour la forme à deux termes
> et `2 000·|S|` pour celle à trois termes, **dans toutes les configurations de
> coïncidence** — que les tirages impliqués soient distincts, partiellement ou
> totalement confondus.

La démonstration est une énumération exhaustive sur les `80²·|S|` triples
`(u,v,δ)`, pondérée par les probabilités hypergéométriques `p₁ = 20/80`,
`p₂ = 20·19/(80·79)`, `p₃ = 20·19·18/(80·79·78)`. Dans le cas le plus emmêlé — tout
dans le même tirage — les `12 800` triples se répartissent en `2` entièrement
confondus, `474` à deux indices égaux et `12 324` à trois distincts, et
`2·p₁ + 474·p₂ + 12 324·p₃ = 0,5 + 28,5 + 171 = 200` exactement.

Le §184 montre ce que coûte de l'ignorer. Une nulle simulée sur `40 × 70 560`
tirages garde une erreur d'estimation de `0,08` sur une statistique dont l'écart
mesuré vaut `0,89` : elle déplace les `z` d'environ un écart-type, et elle a
fabriqué un `ECART` à `p = 0,038` là où la valeur exacte donne `p = 0,587`. Pire,
cet écart **s'est répliqué** sur deux moitiés disjointes de l'archive — parce que
les deux moitiés partagent la même nulle simulée, donc la même erreur. *Une
réplication ne teste pas la nulle ; elle teste la stabilité de l'effet étant donné
la nulle.*

**(iv) Ce que la forme ne couvre pas.** Elle demande un quasi-morphisme, donc :

- **un LCG à grand multiplicateur** n'en a pas — `c(a·x)` n'est pas
  `a·c(x) + petit` dès que `a` est grand — et reste traité par le réseau (§144) ;
- **Mersenne Twister** n'est pas une récurrence à deux termes sur des *mots* : son
  pas décale d'un bit, ce qui casse l'alignement des têtes (le tempering, lui, est
  `F₂`-linéaire et ne gêne pas) ;
- **un CSPRNG** n'a par construction aucun quasi-morphisme lisible, et le §7.26
  dit pourquoi aucun test ne peut en avoir un.

**(v) Ce que la famille a coûté, et ce qu'elle a rapporté.** Le crible exact du
§172 couvre le degré `≤ 7` pour `286` milliards de nœuds. Les six détecteurs
couvrent, ensemble, les récurrences à deux termes additives et soustractives, à
coefficients `±1, ±2`, aux degrés `7` à `100`, sous cinq échantillonneurs
différents — pour une vingtaine de minutes de calcul au total. Le crible reste
irremplaçable pour ce qu'un détecteur ne fait pas : **rendre un état**. Mais pour
*écarter*, il n'y a aucune raison de le payer.

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

### 8.1 Et l'échantillonneur à **rejet** — celui dont le pas varie (§165-§170)

Tous les cribles ci-dessus lisent un générateur à **pas fixe** : vingt mots
par tirage, ou soixante-dix-neuf, ou quatre-vingts. Chacune de ces sections
disait explicitement ne pas lire le plus naïf des échantillonneurs, celui du
programmeur pressé — `v = 1 + (x mod 80)`, **recommencer si le numéro est
déjà sorti** —, dont le pas varie (`E[N] = 22,85` mots par tirage,
`H(N) = 2,846` bits). C'est ce que la série des §165 à §170 lit, par une
programmation dynamique de synchronisation (7.17), élaguée en faisceau
(7.18), au sens fort d'une **martingale de Ville** : valable à tout instant,
sans hypothèse de distribution, avec témoin positif à chaque fois.

| § | canal | échantillonneur | plan 0 | plan 1 | état |
|---|---|---|---|---|---|
| 165 | parité | rejet `mod 80` | `L ≤ 17` | `L ≤ 11` | flux **et** `370` nuits |
| 166 | parité | rejet `mod 80` | `18 ≤ L ≤ 31` (**TYPE_3**) | `L = 15` (**TYPE_2**) | flux ; nuits `L ≤ 25` |
| 167 | parité | rejet **masqué** (`M = 100, 128, 256`) | `L ≤ 31` | `L ≤ 15` | flux |
| 168 | parité | + **excédent** fixe `δ ∈ [1, 79]` | types nommés | types nommés | flux |
| 169 | **mod 4** | rejet `mod 80`, seul ou **entrelacé** avec un autre jeu | `L ≤ 15` | `L ≤ 10` | flux |
| 170 | parité | rejet **masqué**, **par nuit** | `L ≤ 18` | `L ≤ 11` | `370` nuits |
| **172** | **classes `mod 80`** | **troncature `(x·80) >> 32`** avec rejet | `L ≤ 7` | — | flux **et** nuits |

Soit, en une phrase : **le plan 0 de tous les trinômes primitifs de degré
`≤ 31` et le plan 1 de tous ceux de degré `≤ 15` — TYPE_1, TYPE_2, TYPE_3
compris — sous les quatre écritures usuelles d'un tirage à rejet, avec un
excédent quelconque, et même partagé avec un autre jeu.**

Le §172 est d'une autre nature et il faut le dire : la troncature n'admet
**aucun état fini déterministe** (lemme de la retenue, 7.24 (ii)), donc
aucune martingale. Elle admet en revanche un **automate non déterministe**
sur `(Z/80)^L` — la classe est additive à un bit près — et le crible qui en
sort rend un verdict **dur** : zéro survivant *exclut*, exactement. Deux
régimes complémentaires, à citer séparément.

### 8.2 Ce qu'une trouvaille vaudrait — vérifié, pas supposé (§171)

Sur un TYPE_1 planté, la chaîne entière a été parcourue : détection
(`0,2` s), crible des plans `2-4` (`24` s, `2^{21}` candidats), relèvement
par réseau LLL exact (`2` à `16` s), puis **prédiction du tirage suivant —
ses vingt numéros exacts, trois fois sur trois** — à partir de `20` à `25`
tirages publiés et triés, soit moins de deux heures de jeu. Le `D = 0`
ci-dessus n'est donc pas un aveu d'impuissance : c'est le **premier maillon**
d'une chaîne complète et vérifiée qui ne se ferme pas sur l'archive.

### 8.3 Ce que cette série laisse ouvert, et il faut le nommer

- le **plan 1 de TYPE_3** (`2^{62}` positions : hors de portée du parcours,
  et le décodage souple à alignement inconnu n'a pas de seuil — 7.18) ;
- **TYPE_4** (`2^{63} − 1` au plan 0) ;
- la **troncature** au-delà du degré `7` : le crible en ordre de flux coûte
  `20^L` ; l'ordre en cascade (7.24 (xi)) le ramène à `2^{37}` pour TYPE_2 —
  c'est une conception, pas encore une mesure — et laisse TYPE_3 (`2^{82}`)
  et TYPE_4 (`2^{130}`) dehors ;
- un **excédent variable** d'entropie supérieure au débit du canal : `1,09`
  bit pour la parité, `5,37` pour le mod 4 (7.20, 7.21) — mais il faut
  `δ̄ + H(δ) ≥ 22,85` pour noyer le canal de **classes**, soit trente-six
  valeurs au lieu de deux (7.24 (xii)) ;
- et, toujours, les trois hypothèses de fond ci-dessus : graine de plus de
  `32` bits, état jamais réamorcé, matériel.

---

## 9. Ce qu'il faudrait collecter

Une seule donnée changerait la conclusion, et l'archive ne la contient pas :
**des tirages ordonnés**. Le 7.26 dit exactement ce qu'ils valent : `log₂(80!/60!)
= 122,69` bits par tirage au lieu de `61,62`, soit **le double** (`×1,991`) —
ils divisent par deux le nombre de tirages nécessaires quel que soit l'état,
et montent le seuil de sécurité de `7,70` à `15,34` octets frais par tirage.
Plus de tirages **triés**, en revanche, n'achètent rien : `4,35` Mbit
déterminent déjà tout état déterministe jamais proposé pour une loterie.

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
et elles n'existent qu'entre tirages **consécutifs**. TYPE_3 (`L = 31`) demande
trois consécutifs au moins ; les vidéos en ont quatre (jour B), et la réponse
est zéro.

> **Correction (§7.27).** La phrase « un tirage isolé ne sert qu'à vérifier »,
> écrite ici avant le théorème du tirage unitaire, est **fausse pour le canal de
> classes**. Un tirage consomme `E[N] = 22,85` mots, donc `22,85 − L` d'entre eux
> sont déjà déterminés par la récurrence *à l'intérieur du tirage* : les équations
> ne commencent pas à la frontière, elles commencent au `L`-ième mot. Le théorème
> chiffre exactement ce que cela vaut — `98,0817` bits par tirage ordonné contre
> `5,3219` par mot d'état libre, soit un seuil `L* = 18,43`. **Un seul tirage
> ordonné exclut tous les degrés jusqu'à 18**, TYPE_2 compris. Les six tirages
> *isolés* des vidéos, que l'on croyait bons seulement pour vérifier, sont donc six
> tests indépendants de plein droit — c'est ce que h161 exécute (§176).
>
> Ce qui reste vrai : au-delà du degré `18`, il faut des consécutifs, et le compte
> est `T = ⌈L/18,43⌉` tirages ordonnés — `2` pour TYPE_3 `(3,31)`, `4` pour TYPE_4
> `(1,63)`. Ce sont des bornes d'**information** ; le calcul, lui, s'arrête bien
> avant, vers le degré `17`. Pour l'état
**entier**, c'est le §7.8 qui compte : `n* = L(27 − log₂ 5)/log₂ M(f)` mots,
`72` tirages consécutifs — ordonnés ou **triés**, l'archive suffit — pour
TYPE_3, `35` pour TYPE_2, `17` pour TYPE_1.

| cible (glibc `random()`, sous rejet) | tirages consécutifs requis | disponibles |
|---|---|---|
| état bas TYPE_1, TYPE_2 (35, 75 bits) | 1 à 2 ordonnés (+ satellites) | **jours A, B, C — atteint, réponse 0** |
| état bas TYPE_3 (155 bits) | 3 ordonnés | **jour B (4) — atteint, réponse 0** |
| état bas TYPE_1 par l'archive triée | énumération `2^35` | **archive — §155** |
| état entier TYPE_1 (224 bits) | 17 triés | **archive — §155** |
| état bas TYPE_2 par l'archive triée, pas constant | `2^45` hypothèses à trois plans (§7.10) | archive — calcul **non lancé** (une heure de carte graphique, des années-cœur ici) |
| état bas TYPE_3 par l'archive triée | `2^93` (§7.10) | hors de portée |
| état bas TYPE_1, TYPE_2 et 29 trinômes par l'archive triée, **flux continu** à pas constant (§7.11) | `2^L` plans 0, plans 1–2 par linéarisation cubique | **archive — §157 (fy 20–24, 79, 80 ; shuffle 79, 80), §158 (shuffle 20–24) : §157 et §158 **conformes**, 558 + 310 = 868 cribles, 0 survivant, 0 indécis : TYPE_1, TYPE_2 et les 29 autres trinômes exclus sous les onze schémas à pas fixe** |
| état bas TYPE_1, TYPE_2, TYPE_3 et 29 trinômes sous flux continu, **tirages ordonnés** (§7.12) | `2^L` par table de vérité, `5 264` cellules exactes | **vidéos — §159 : 0 survivant sur 5 264 cellules, TYPE_1, TYPE_2, TYPE_3 exclus à pas constant** |
| état **entier** TYPE_1 (224 bits) par des tirages ordonnés à pas constant | 5 ordonnés, plan 0 par crible linéaire puis LLL (§7.12) | **algorithme, témoins 3/3 ; vidéos : aucune cellule survivante (§159)** |
| état **entier** TYPE_2 (480 bits) par des tirages ordonnés à pas constant | 8 ordonnés, BKZ-50/60, deux à cinq minutes (§7.12) | **algorithme, témoins 3/3 ; vidéos : aucune cellule survivante (§159)** |
| état entier TYPE_2, TYPE_3 | 35, 72 triés, **après** les bits bas, sous rejet | bits bas hors de portée par l'archive ; à pas constant, pas de relèvement (§7.10) |
| état bas TYPE_2, TYPE_3 et 42 trinômes (degré 15 à 31) sous flux continu à pas constant, **shift 1** (`random()` de la glibc), par les relations de poids 3 sur `Z/4` (§7.14) | `2^L` plans 0 par une WHT (`L ≤ 28`) ou un `χ²` par morceaux (`L = 31`), plan 1 déduit linéairement | **archive — §162 : 396 décodages (fy 20–24, 79, 80 ; shuffle 79, 80 ; shifts 1 et 0), pré-enregistré, en cours** |
| plan 0 de tout Fibonacci retardé (`+`, `−` à shift 0 ; `xor` à tout shift), 110 trinômes primitifs de degré 7 à 63 + 16 retards classiques jusqu'à 1279, sous flux continu et par nuit, **sans état** (§7.15) | linéaire en `N` : 2 268 statistiques, ≈ 1–3 h | **archive — §163 : `D = 0` sur 2 268 statistiques (2 006 pleines), conforme** |
| toute relation de **poids 2** du bit lu — période, anti-période ou décalage isolé jusqu'à `Δ_max = S × 60 559` — donc tout LCG modulo `2^W` à sortie décalée (`java.util.Random`, MSVC, TYPE_0, LCG maison : `s ≤ 20` au pas 20, `s ≤ 22` au pas 80), le plan 1 de TYPE_1/TYPE_2 à shift 1 (périodes 254 et 65 534), et les corrélations partielles des LCG deux octaves sous leur période, sous flux et par nuit, sans état (§7.16) | linéaire en `N` : `32,7 M` statistiques, `30 min` témoins compris | **archive — §164 : `D = 0` sur `32 673 251` statistiques (max `|z| = 5,07`, `z_D = -0,53`), conforme** |
| la **graine** de `random()` (32 bits), une par bloc ou une par tirage, quelle que soit sa source (§7.4 addendum) | `2^32` × 16 variantes × 21 échantillonneurs, index bitmap des 370 blocs et index inverse des 5-sous-ensembles | **archive — §161 : balayage en cours, journalisé ; couverture consignée au registre** |
| la synchronisation sous le **rejet** (pas variable, `E[N] = 22,85` mots par tirage) : plan 0 des 31 trinômes de degré `≤ 17`, plan 1 des 19 de degré `≤ 11` (TYPE_1 compris), suite alternée (TYPE_0), sous le flux et par nuit, par la **position absolue** dans la suite du bit lu (§7.17) | `21 · N` par tirage, `N = 2^L − 1` (plan 0) ou `(2^L − 1) 2^L` (plan 1) ; surmartingale de Ville, seuil `23,25` (flux) / `31,78` (nuit), valable à tout instant | **archive — §165 : en cours (jeton `f11c611488262d18`)** |
| la même synchronisation **élaguée** (§7.18) : plan 0 des 32 trinômes primitifs de degré `18 ≤ L ≤ 31` — `x³¹ + x³ + 1` (TYPE_3) compris, `N = 2³¹ − 1` — et plan 1 des 6 trinômes de degré 15 — `x¹⁵ + x + 1` (TYPE_2), `N = 2¹⁴ · 65 534` —, sous le flux et par nuit | un seul passage en flot pour les `m = 40` tirages pleins (mémoire `O(m)`, découpage exact), puis faisceau `2¹⁶` puis `1024` : `21 · B` par tirage ; l'élagage laisse une surmartingale, Ville au seuil `29,25` (flux, mélange sur `64` redémarrages) / `23,25 + log₂(blocs)` (nuit) | **archive — §166 : en cours (jeton `061f95021fc425e2`)** |
| le rejet **masqué** — `v = 1 + (x mod M)`, refusé si `v > 80` (`M = 100, 128, 256`), l'écriture recommandée d'un tirage sans biais : mêmes trinômes, plan 0 (`L ≤ 31`) et plan 1 (`L ≤ 15`), sous le flux (§7.19) | la vraisemblance garde la même forme, `F` et `G` étalés par la binomiale du masque ; `n` jusqu'à `176`, fenêtre de 128 bits ; `1,02 → 0,092` bit par tirage de `M = 80` à `256` ; Ville au seuil `29,25` | **archive — §167 : en cours (jeton `3e34b826a3ea5e8f`), 122 des 181 configurations lues, `D = 0`** |
| l'**excédent** par tirage : le générateur consomme `δ` mots de plus (habillage, seconde partie, autre jeu) — cinq séquences nommées, deux échantillonneurs, `δ` dans vingt valeurs de 1 à 79 (§7.20) | la cible se décale, la fenêtre ne bouge pas : coût nul en calcul, `log₂ 20` de seuil ; limite exacte — un excédent VARIABLE d'entropie `≥ 1,09` bit par tirage noie le signal, quelle que soit la longueur du flux | **archive — §168 : à lancer, chaîné après le §165** |
| la **source elle-même** : un QRNG matériel (ID Quantique nomme la Loterie Romande parmi ses clients Quantis pour le tirage des numéros gagnants ; IGT tient la plateforme depuis 2022, et l'archive court de septembre 2025 à août 2026) — biais d'octet publié sur la sortie brute (Hurley-Smith & Hernandez-Castro, 2020) (§7.25) | le tirage n'est pas la sortie brute : l'archive borne toute déviation marginale à `0,91 %` d'écart quadratique moyen par classe (`χ²` mesuré `53,60` contre `79` attendus). Et elle EXCLUT la mise en forme naïve : un mot de `12` bits ou moins envoyé sur `1…80` par modulo ou troncature sans rejet donne `χ² ≥ 86` de plus, vu à `6,8σ` ; à partir de `14` bits, invisible | **acquis — §7.25. Reste la fourche : QRNG → graine de 32 bits (attaquable, §161 la balaie) contre QRNG direct ou CSPRNG ≥ 256 bits (hors de portée, faute de bits dans l'archive, non faute de calcul)** |
| la lecture par **troncature** `v = 1 + ((x·80) >> 32)` sous **pas variable** (rejet) — l'échantillonneur sans biais de modulo, le seul des quatre que les §165-§170 ne lisent pas (§7.24) | aucun état fini DÉTERMINISTE n'existe (lemme de la retenue) ; mais la classe est additive à un bit près (quasi-morphisme `c(a+b) = c(a)+c(b)+δ`, `δ ∈ {0,1}`), d'où un automate NON DÉTERMINISTE sur `(Z/80)^L` : `1` bit de branchement contre `2` bits d'élagage par mot (lemme de la classe), et l'alignement se DÉDUIT des classes acceptées — coût nul. Front `20^L`, puis relèvement des fractions par LLL | **archive — §172 : en cours (jeton `c7b3095602e2e126`, h155), `D = 0`, 0 coupe. Le degré 9 suit (§174, h154). Première conception (h152) ABANDONNÉE et NON consignée : sa partie par nuit s'est révélée infaisable sous un plafond de 60 mots par tirage — le coût est à queue lourde, deux configurations y ont été coupées. Degré 10 (`2^{43,2}` par configuration) et au-delà hors de portée ; TYPE_2 `2^{64,8}`, TYPE_3 `2^{134}`, TYPE_4 `2^{272}` hors de portée de l'ordre de flux** |
| le canal **mod 4** : `v − 1 = x mod 80` donne `x mod 4`, deux bits par mot — plan 0 des trinômes `L ≤ 15` (`N = (2^L − 1)2^L`), plan 1 des `L ≤ 10` (état mod 8), avec ou sans **jumeau entrelacé** (§7.21) | vraisemblance `Π_c F₂₀(w_c, a_c) · G₂₀` (normalisation vérifiée) ; `5,37` bits par tirage contre `1,31` ; l'entrelacement d'un jumeau coûte `2,85` bits : net `+2,53` au lieu de `−1,54` | **archive — §169 : en cours (jeton `06785fcaa1f3e711`)** |
| le rejet **masqué par nuit** (§7.19 × §7.4) : le générateur réamorcé chaque soir ET lu au masque — plan 0 des trinômes `L ≤ 18`, plan 1 des `L ≤ 11`, `M = 100` et `128`, les 370 nuits | une phase pleine par nuit (`370 · N`) ; une chaîne par bloc, seuil `31,78`, plus la chaîne des blocs cumulés au seuil `23,25` | **archive — §170 : à lancer, chaîné après le §169** |

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

### 7.29 L'**autocorrélation exacte** — pourquoi la variance se calcule sans une seule simulation

Soit `m[t,v] ∈ {0,1}` l'indicatrice « le numéro `v` est sorti au tirage `t` », et
`x[t,v] = m[t,v] − 1/4` sa version centrée (`E[m] = 20/80 = 1/4`). Pour un décalage
`d ≥ 1`, on pose

        C_v(d) = Σ_t  x[t,v] · x[t+d,v]  .

> **Théorème.** Sous SRS `20/80` indépendants d'un tirage à l'autre,
>
>     E[C_v(d)] = 0        et        Var(C_v(d)) = (n − d) · (3/16)²
>
> **exactement**, pour tout `v` et tout `d ≥ 1`.

*Démonstration.* En trois points.

**(i) L'espérance.** Les tirages `t` et `t+d` sont indépendants et `x` est centré,
donc `E[x_t x_{t+d}] = E[x_t]·E[x_{t+d}] = 0`. La somme est nulle terme à terme.

**(ii) La variance d'un terme.** Toujours par indépendance,
`Var(x_t x_{t+d}) = E[x²_t]·E[x²_{t+d}] = (3/16)²`, puisque
`Var(m) = (1/4)(3/4) = 3/16`.

**(iii) L'annulation identique de la covariance.** Deux termes ne partagent un
tirage que si leurs indices diffèrent de `d`. Dans ce cas

    Cov(x_t x_{t+d}, x_{t+d} x_{t+2d}) = E[x_t · x²_{t+d} · x_{t+2d}]
                                       = E[x_t] · E[x²] · E[x_{t+2d}] = 0 ,

la factorisation étant licite par indépendance des trois tirages, et le résultat
nul parce que `x` est **centré**. Les termes sont donc deux à deux non corrélés et
les variances s'ajoutent. ∎

C'est le point (iii) — et lui seul — qui rend la nulle exacte. Il tombe parce que
le centrage est fait avec la valeur **vraie** `1/4` et non avec une moyenne
estimée ; centrer sur la moyenne empirique réintroduirait une covariance d'ordre
`1/n` et détruirait l'exactitude.

**Corollaire (la somme redonne le recouvrement).**

    Σ_v C_v(d) = Σ_t ( |A_t ∩ A_{t+d}| − 5 )

car `Σ_v m[t,v] = 20` pour tout `t`, donc les termes croisés valent
`−(1/4)·20 − (1/4)·20 + 80/16 = −5`. La variance de cette somme est
`(n−d) · 20·(20/80)·(60/80)·(60/79) = (n−d)·2,8481`, la variance hypergéométrique
du recouvrement. Les deux familles de statistiques se contrôlent donc l'une
l'autre : la seconde est la projection de la première sur la direction constante,
et sa nulle se calcule par un chemin entièrement différent.

**Version masquée.** Si les tirages sont posés sur une grille d'horloge à trous
(l'archive en a `345`), on annule `x` hors du masque et l'on compte
les paires réellement présentes par autocorrélation du masque. Les deux
autocorrélations se calculent par une seule paire de transformées de Fourier, et
la formule de variance devient `n_d · (3/16)²` avec `n_d` = nombre de paires
présentes. Rien d'autre ne change : les points (i) à (iii) ne dépendent pas de la
régularité des indices.

**Ce que cela coûte.** Quatre-vingts transformées de longueur `2¹⁸` par famille,
soit quelques secondes pour `6 889 050` statistiques — contre `286` milliards de
nœuds pour le crible de classes du §172, qui ne couvre que les degrés `≤ 7`.

---

### 7.30 Le **budget** — ce qu'une contrainte comptable laisse comme trace, et pourquoi c'est le seul défaut qui rend prévisible sans casser le générateur

Les §7.1 à §7.29 attaquent toutes le **générateur**. Il existe une seconde cible,
et c'est historiquement celle qui cède : le **protocole**. Un exploitant qui
contraint le résultat pour des raisons comptables — un quota de gros
multiplicateurs par nuit, un plafond de gains, un rééquilibrage des numéros —
laisse une trace d'un type que **tous** les tests de générateur manquent par
construction.

**Pourquoi les tests de générateur la manquent.** Un budget conserve les
fréquences globales : la marge est juste, le `χ²` d'ajustement est juste,
l'autocorrélation est nulle au premier ordre. Ce qu'il change est la **variance
inter-blocs**, et aucune statistique du dossier ne la regarde.

**La signature.** Soit `X_k` le compte d'un symbole dans le bloc `k` de taille
`n_k`, et `π` sa fréquence globale. L'indice de dispersion

        D = Σ_k (X_k − n_k π)² / (n_k π (1 − π))

vaut en moyenne `K` (le nombre de blocs) sous une source sans mémoire. Un budget
**parfait** — exactement `n_k π` exemplaires par bloc — donne `D = 0` exactement.
Un budget **partiel**, qui ne retire qu'une fraction `ρ` de la variance, donne
`E[D] = K(1 − ρ)`, donc `z = −ρ·K/√(2K) = −ρ√(K/2)`.

> **Le budget est le seul défaut qui rend prévisible sans casser le générateur.**
> Sous budget, la loi conditionnelle du tirage `t` sachant le début de la nuit
> n'est plus la loi marginale : le quota consommé retire de la masse. En fin de
> nuit, un quota épuisé rend un symbole **impossible** — probabilité exactement
> nulle, prédiction certaine — sans qu'aucun bit du générateur n'ait été deviné.

**La nulle correcte est une permutation, pas une binomiale.** Tester la
sous-dispersion contre une binomiale `Bin(n_k, π̂)` avec `π̂` estimé sur les mêmes
données mélange deux questions et biaise le résultat. La permutation de l'ordre
des tirages conserve exactement les fréquences globales et teste précisément
l'hypothèse voulue — *l'affectation des symboles aux blocs est échangeable* — sans
estimer quoi que ce soit.

**Sens du test.** La sous-dispersion est **impossible à produire par hasard** à
grande taille : c'est une contrainte, pas une fluctuation. C'est pourquoi le signe
compte autant que la taille, et pourquoi un `z` négatif est une découverte alors
qu'un `z` positif du même module ne serait qu'un regroupement.

---

### 7.31 La **borne de prédiction** — comment un test négatif se convertit en garantie chiffrée

Un test qui ne trouve rien ne dit rien, tant qu'on n'a pas dit **ce qu'il aurait
trouvé**. Voici la conversion, et elle est exacte.

**La mesure.** Un prédicteur produit vingt numéros par tirage ; on compte le
recouvrement `R_t` avec le tirage réel. Sous SRS, `R_t` est hypergéométrique de
moyenne `5` et de variance `σ² = 20·(20/80)·(60/80)·(60/79) = 2,8481`. Sur `n`
tirages **hors échantillon** — donc indépendants de l'ajustement — la moyenne `R̄`
a pour écart-type exact `σ/√n = 1,6876/√n`.

**L'avantage.** Définissons l'avantage d'un prédicteur comme
`ε = E[R_t] − 5`, en numéros par tirage. C'est la seule quantité qui compte
économiquement : le gain d'un billet est une fonction croissante du nombre de
numéros justes, donc un prédicteur d'avantage `ε` déplace l'espérance de gain de
`ε · ∂(gain)/∂(numéro juste)` et de rien d'autre.

> **Borne.** Si la moyenne mesurée vaut `R̄` sur `n` tirages hors échantillon,
> alors, au niveau de confiance `1 − α` unilatéral,
>
>     ε  <  (R̄ − 5) + z_{1−α} · σ/√n .

**Deux conditions, et elles ne sont pas décoratives.**

  * **Hors échantillon.** Si l'ajustement a vu les tirages de mesure, `R̄` est
    biaisé vers le haut d'une quantité inconnue et la borne est fausse dans le
    mauvais sens. C'est pourquoi la tranche de mesure doit être disjointe.
  * **Causalité stricte.** Si un trait lit le tirage qu'il prédit, le biais peut
    ne pas se voir sur `R̄` du tout et se loger dans la **queue** de la loi — c'est
    exactement ce qui s'est produit au §185, où une fuite invisible au centre
    (`z = +0,26`) valait `+12,08` écarts-types sur les tirages à dix numéros ou
    plus. **Vérifier la loi entière fait partie de la vérification de la borne**,
    pas d'un raffinement facultatif.

**La portée de la borne est celle de la classe.** Une borne obtenue sur un
prédicteur donné ne vaut que pour lui. Elle ne vaut pour une **classe** que si le
prédicteur mesuré est le meilleur de la classe *sur les données d'ajustement* —
ce qui est exactement ce que fait une régression logistique ajustée par maximum de
vraisemblance sur les traits de la classe. D'où la règle de construction :

> Pour borner une classe de défauts, il faut mettre **un trait par forme de
> défaut** dans le modèle, et vérifier par un **témoin planté par forme** que le
> trait correspondant s'allume. Un témoin manquant est un trou dans la borne, et
> il ne se voit pas : le §188 a d'abord donné `z = −1,07` sur un Fibonacci planté
> parce qu'il n'avait aucun trait capable de le lire.

**Ce qu'une borne ne dit pas.** Elle ne dit rien des défauts hors de la classe. Un
générateur cryptographique et un générateur faible dont le défaut n'a aucun trait
correspondant donnent la même borne. La valeur d'une borne se lit donc **au
nombre et à la variété des témoins qui l'accompagnent**, jamais au nombre de
tirages.

---

### 7.32 Le **maximum permuté** — pourquoi un Bonferroni gaussien sur des khi² est faux des deux côtés

Soit `M` statistiques `T_1..T_M`, chacune normalisée en `z_i = (T_i − μ_i)/σ_i` où
`μ_i` et `σ_i` viennent d'une nulle simulée. La lecture habituelle compare
`max_i |z_i|` au quantile gaussien de Bonferroni `Φ⁻¹(1 − α/2M)`. Cette lecture est
fausse dès que les `T_i` sont des `khi²`, et elle est fausse **dans les deux sens à
la fois**.

**(i) La dissymétrie.** Un `khi²` à `d` degrés de liberté a pour asymétrie
`√(8/d)`. Sa version centrée-réduite garde cette asymétrie : la queue droite est
plus lourde qu'une gaussienne, et d'autant plus que `d` est petit. Le maximum de
`M` telles variables dépasse donc systématiquement le quantile gaussien. Avec les
`1 971` statistiques du §189, la médiane du maximum vaut `5,33` là où le seuil de
Bonferroni gaussien vaut `4,212` : **une lecture gaussienne déclarerait un écart
une fois sur deux sur des données parfaitement conformes**.

**(ii) La dépendance.** Les `M` statistiques partagent les mêmes tirages. Le
nombre de tests *effectivement indépendants* est inférieur à `M`, donc Bonferroni
est conservateur — dans l'autre sens. Les deux effets ne se compensent pas : ils
portent sur des aspects différents de la loi du maximum, et leur somme est
imprévisible.

**La correction, qui ne suppose rien.** On dispose déjà des `R` réplicats de la
nulle. Il suffit de calculer, pour chaque réplicat `r`, sa propre statistique de
maximum en le **laissant de côté** dans l'estimation de `μ` et `σ` :

    μ_i^{(-r)} = (Σ_s T_i^{(s)} − T_i^{(r)}) / (R−1) ,     idem pour σ ,
    m_r = max_i | (T_i^{(r)} − μ_i^{(-r)}) / σ_i^{(-r)} |

et à comparer `max_i |z_i|` observé à la loi empirique des `m_r`. Le `p` vaut
`(1 + #{r : m_r ≥ observé}) / (1 + R)`. Cette lecture est **exacte sous la nulle de
permutation**, pour tout `M`, toute dissymétrie et toute dépendance.

**Le laissé-de-côté n'est pas cosmétique.** Sans lui, `T_i^{(r)}` entre dans sa
propre moyenne et dans son propre écart-type, ce qui rétrécit `m_r` d'un facteur
`√(1 − 1/R)` et biaise le `p` vers la découverte — exactement le sens qu'on
cherche à éviter.

**Le prix.** La résolution du `p` est `1/(R+1)`. Avec `R = 200`, on peut conclure
« conforme » (`p > 0,05`) mais pas proclamer une découverte forte. C'est le bon
compromis : un test de balayage sert à **écarter**, et une découverte se chasse
ensuite sur sa propre statistique, où l'on peut se payer bien plus de réplicats.

---

### 7.33 La règle de portée **résiste à la gigue** — et le seul défaut qu'aucun détecteur d'énergie ne peut lire

La règle de portée du §7.28 convertit un retard en **mots** `d` en un retard en
**tirages** `g = d / E[N]`, avec `E[N] = 22,8487`. Elle suppose implicitement que le
partenaire d'un mot du tirage `t`, situé `d` mots en arrière, tombe dans le tirage
`t − g`. Or ce n'est pas exact : l'indice du premier mot du tirage `t` vaut
`W_t = Σ_{s<t} N_s`, une **marche aléatoire** de moyenne `22,8487·t` et d'écart-type
`1,8525·√t` (§7.27). Le partenaire **flotte**.

*Fallait-il en conclure que la règle a une clause manquante ?* Non — c'est mesuré.

> **Proposition (la gigue ne casse pas la portée, au moins jusqu'à `g = 3`).**
> À portée nominale égale, un régime à consommation variable lit la relation **au
> moins aussi bien** qu'un régime à consommation constante.

*Vérification* (`h176b`, `70 560` tirages plantés, trait à trois termes seul) :

| régime | retards en mots | portée | flottement | `z` |
|---|---|---|---|---|
| A | `(23, 46, 69)` | `1,006 ; 2,013 ; 3,019` | `1,85` à `3,21` mots | `+5,29` |
| B | `(45, 90, 135)`, bloc fixe `45` | `1 ; 2 ; 3` | nul | `+3,15` |
| C | contrôle SRS | — | — | `+0,75` |

*Pourquoi cela marche.* Le flottement à la portée `g` a pour écart-type `1,85·√g`,
soit `1,85`, `2,62` et `3,21` mots pour `g = 1, 2, 3`. Un tirage occupe `22,85` mots.
Le partenaire reste donc **dans le bon tirage** dans la très grande majorité des cas,
et la relation ne se disperse pas. La clause à retenir n'est pas « consommation
constante » mais la condition, bien plus faible :

        1,8525 · √g  ≪  E[N] = 22,8487        c'est-à-dire        g ≪ 152 .

Tant que la portée reste très inférieure à cent cinquante tirages, la gigue est
négligeable. Elle ne devient une limite que pour des retards de plusieurs milliers de
mots, hors de portée de tout le catalogue.

**Le corollaire négatif, qui est le vrai contenu.** Un détecteur d'énergie lit une
**relation entre sorties** : deux ou trois mots liés par une somme ou un XOR. Il ne
lit rien d'un générateur qui n'en a pas.

> Un générateur `F₂`-linéaire à **un seul pas** — `x_{i+1} = M x_i`, dont les
> xorshift sont l'exemple — ne satisfait aucune relation de poids `2` ou `3` entre
> sorties à des retards de l'ordre du tirage. Ses multiples de poids `3` existent,
> mais à des degrés dictés par son polynôme caractéristique, très supérieurs. **Aucun
> détecteur d'énergie ne peut donc le voir**, quelle que soit la longueur de
> l'archive.

Mesuré : `z = −0,97` sur un xorshift32 planté de `70 560` tirages, contre `+20,07`
sur une relation XOR à deux termes plantée à portée `(1, 2)`.

Cette famille se ferme donc **ailleurs et autrement** : par le crible de classes, qui
énumère l'état au lieu de chercher une relation (`h127`, `972` designs × `2³²` sous
troncature), et par les distingueurs sans état des §163 et §164. C'est la raison
d'être de deux instruments là où un seul semblerait suffire :

> **Un détecteur de relation et un crible d'état ne couvrent pas la même chose, et
> aucun des deux ne subsume l'autre.** Le détecteur voit loin en degré et ne voit que
> les relations creuses ; le crible voit toute forme et ne voit pas loin. Une borne
> qui ne cite qu'un des deux ment par omission.

---

### 7.34 Le **flux mince** — l'observable le plus net d'une archive de loterie, et pourquoi ce n'est pas celui qu'on regarde

Tout le dossier lit les vingt numéros. C'est l'observable le plus **gros** et le moins
**net**, et il vaut la peine de dire pourquoi.

**La netteté d'un observable.** Appelons *netteté* le nombre de bits qu'un observable fixe
sur un mot **identifié** du flux. Un tirage de vingt parmi quatre-vingts publie `61,62`
bits pour environ `22,85` mots consommés, soit `2,70` bits par mot — mais l'ensemble est
**trié**, donc on ignore quel mot a produit quel élément. Chaque mot n'est contraint que
par « ma classe appartient à cet ensemble de vingt », et son identité dans le flux est
ambiguë.

Le bonus est d'une autre nature. Le §175 établit `bonus = triés[⌊20u/2³²⌋]`, donc le rang
`b` vaut `⌊20u/2³²⌋`, tandis que la classe du même mot vaut `c = ⌊80u/2³²⌋`.

> **Lemme.** `c = 4b + k` avec `k ∈ {0,1,2,3}`, exactement.
>
> *Démonstration.* Posons `x = 20u/2³²`. Alors `80u/2³² = 4x`, et pour tout réel positif
> `⌊4x⌋ = 4⌊x⌋ + ⌊4{x}⌋` avec `{x} ∈ [0,1)`, donc `⌊4{x}⌋ ∈ {0,1,2,3}`. ∎

Le rang du bonus fixe donc la classe d'**un mot précis** — le `(N+1)`-ième du tirage — à
quatre valeurs sur quatre-vingts, soit `4,32` bits sur un mot **identifié**. C'est
`1,6` fois la netteté des numéros, et surtout sans ambiguïté d'identité.

> L'archive porte ainsi une seconde suite, de `70 560` mots fortement contraints, espacés
> de `E[N] + 2 = 24,85` mots. Je l'appelle le **flux mince**. Il est plus court, plus
> régulier et plus net que celui des numéros, et rien dans le dossier ne l'avait traité
> comme un flux.

**La nulle exacte y est plus simple qu'ailleurs.** Les vingt blocs `B_j = {4j..4j+3}`
**partitionnent** `Z/80`. Donc, pour une cible `w` quelconque, `P(w ∈ B_t) = 1/20`
exactement, sans dépendre de `w`. D'où, pour tout couple de décalages `g₁, g₂ ≥ 1` :

        E[T2] = |B| · |B| · |S| · (1/20) = 16·|S|/20 = 0,8·|S|   par tirage, exactement.

Aucune énumération de configurations de coïncidence n'est nécessaire, contrairement au
§184 : les décalages étant tous `≥ 1`, le tirage cible est toujours distinct des tirages
opérandes, et le résultat vaut même quand `g₁ = g₂`. *Vérifié* : `3,20217` mesuré sur
l'archive contre `3,20000` exact pour `|S| = 4`.

**Le chaînage — mesuré, et contre ma propre prédiction.** J'avais dérivé qu'une récurrence
de retards courts en mots, disons `(3, 7)`, serait **hors de portée** du flux mince :
rapportés à un espacement de `24,85`, ces retards donnent des portées de `0,12` et `0,28`,
et aucun couple entier ne peut les lire. La mesure dit le contraire — un tel générateur
planté rend un écart de `+0,53` par tirage, du même ordre que les générateurs plantés
exprès à portée `(1,2)` ou `(2,1)`.

> **La récurrence se chaîne.** Sur les vingt-cinq pas qui séparent deux mots du bonus, un
> mot est une combinaison linéaire de **nombreux** mots antérieurs, et la trace survit à la
> composition. Un détecteur sur le flux mince couvre donc à la fois les retards courts et
> les retards à l'échelle du tirage — plus large que sa dérivation ne le laissait croire.

C'est la troisième fois dans ce dossier qu'un témoin planté contredit une limitation que
j'avais dérivée, et c'est la raison d'être des témoins : **une portée se mesure, elle ne se
déduit pas.**

**La recette, générale.** Elle ne tient pas à cette loterie :

> Dans toute archive de loterie, chercher le champ dont la valeur est une **troncature
> déterministe d'un seul mot** — une balle bonus tirée parmi les principales, un numéro
> chance, un multiplicateur porté par une grille. Sa suite est un flux mince : plus net que
> le tirage principal, identifié mot par mot, et de nulle exacte. C'est là qu'un défaut de
> générateur se verrait en premier.

---

### 7.35 La **dimension du modèle** — ce qu'un balayage de graine suppose sans le dire, et comment le borner

Un balayage de graine énonce toujours plus que ce qu'il croit énoncer. Écrit sans
raccourci, son résultat est :

> Aucune graine de l'ensemble `G` ne reproduit un tirage de l'archive **sous le modèle
> `(générateur, échantillonneur)` choisi**.

Trois quantificateurs, pas un. Et les deux derniers ne sont pas symétriques du premier :

* `G`, l'ensemble des graines, **peut** être épuisé — `2³²` l'a été (§203).
* L'ensemble des générateurs peut être couvert **par famille**, et le §199 mesure ce
  qu'une famille laisse voir.
* L'ensemble des échantillonneurs **ne peut pas** être épuisé. Il n'y a pas de liste
  finie de façons de réduire un mot à une classe.

**La leçon que ce dossier a apprise à ses dépens.** Les §200 à §205 balayent `1,56·10¹¹`
graines sous **deux** échantillonneurs — troncature et modulo. Si la machine en emploie un
troisième, ces cent cinquante-six milliards d'essais ne pouvaient pas apparier, et leur
résultat négatif ne disait rien de la graine. Le §206 bis porte le compte à six, mais six
n'est pas *tous*.

> **Un balayage exhaustif dans une dimension et borgne dans une autre ne prouve rien de
> plus que le produit de ses couvertures.** L'exhaustivité en graines n'achète pas
> l'exhaustivité en modèles, et l'annoncer comme telle est une faute.

**Comment on borne quand même.** Trois règles, toutes appliquées ici :

1. **Prendre les échantillonneurs des bibliothèques réelles, pas ceux qu'on imagine.**
   `nextInt` de Java rejette pour débiaiser ; `C++`, Rust et Go modernes utilisent Lemire ;
   `Math.random()*n` construit un double de cinquante-trois bits sur **deux** mots.
   Chacun consomme les mots différemment, et cette consommation est ce que le crible voit.

2. **Un témoin planté par échantillonneur, pas un par famille.** Le témoin du §203 en
   validait deux ; celui du §206 bis en valide trente — cinq générateurs × six
   échantillonneurs. Un échantillonneur qu'aucun témoin n'allume est un échantillonneur
   **non couvert**, et le compte des essais ne le dit pas.

3. **Énoncer le modèle dans le résultat.** « Zéro appariement sur `1,29·10¹¹` essais »
   n'est pas un résultat ; « zéro appariement sur `2³²` graines × cinq générateurs à un
   seul pas × six échantillonneurs de bibliothèque » en est un. La différence n'est pas
   rhétorique : la seconde formulation dit **ce qu'il resterait à faire**.

**Ce que cela vaut pour un résultat négatif.** Il reste conditionnel, et il faut l'écrire.
Mais sa valeur ne tient pas à une exhaustivité impossible : elle tient à ce que la classe
couverte contienne **ce qu'on aurait employé en pratique**. Un dossier qui balaye les cinq
générateurs et les six échantillonneurs qu'un ingénieur choisirait vraiment a fermé la
porte par laquelle on serait entré — pas toutes les portes concevables, et il doit dire
laquelle est laquelle.

---

### 7.36 Pourquoi le crible qui a cassé Java meurt sur PCG — le côté de l'état que la sortie regarde

Le §7.33 dit que les générateurs modernes à un seul pas sont hors de portée « parce que
leur état fait `64` bits ». C'est vrai mais paresseux : le §128 a bien cassé un état de
`48` bits, et sans énumérer `2⁴⁸`. La vraie raison est ailleurs, et elle se mesure.

**Ce qui a rendu Java attaquable (§128).** `java.util.Random` est un LCG modulo `2⁴⁸` dont
la sortie est un **décalage fixe**, `s >>> 17`. Or « modulo `2^k` » est une congruence :
les bits **bas** d'un LCG modulo `2^W` évoluent **entre eux**, sans rien devoir aux bits
hauts. Comme `80 = 16 × 5`, le numéro publié donne `(v−1) mod 16 = (s >>> 17) mod 16`,
c'est-à-dire quatre bits **bas** de l'état — et le crible descend sur `2²¹` au lieu de
`2⁴⁸`. Même mécanique pour les sept LCG nommés du §131.

> Le crible marche parce que la sortie regarde le **bas** de l'état, et que le bas d'un
> LCG est un sous-système fermé.

**Ce que PCG fait, et pourquoi cela suffit.** `PCG32` sort
`rotr32( ((s>>18) ^ s) >> 27 , s>>59 )`. Deux mesures :

> **(i)** La sortie ne dépend que des **trente-sept bits hauts** de l'état.
> *Vérifié* : sur `20 000` états, faire varier les vingt-sept bits bas ne change **jamais**
> la sortie — `0/20 000`.
>
> *Raison.* Le bit `i` de `(s>>18)^s` vaut `s_i ⊕ s_{i+18}` ; on n'en lit que les bits `27`
> à `58`, qui ne mobilisent donc que `s₂₇..s₆₃`. La rotation, elle, lit `s>>59`, déjà
> dedans.

> **(ii)** Avancer d'un mot **mélange les bits bas dans les hauts**.
> *Vérifié* : deux états de mêmes trente-sept bits hauts et de bits bas différents donnent
> une sortie suivante différente **à chaque fois** — `20 000/20 000`.

Les deux ensemble ferment la porte. La première invite à cribler les `2³⁷` bits hauts ; la
seconde interdit d'utiliser une **deuxième** observation pour continuer, puisqu'il faudrait
les vingt-sept bits bas pour avancer.

**Le meilleur crible constructible, chiffré.** Une classe observée coupe l'espace des
trente-sept bits hauts par `80`, soit `2³⁷/80 = 1,72·10⁹` candidats — parfaitement
énumérable. Mais chacun se relève ensuite sur `2²⁷` bits bas libres :

        2³⁷/80 × 2²⁷  =  2⁶⁴/80  =  2,3·10¹⁷ .

> **Le gain vaut exactement un facteur `80`, et rien de plus** — c'est-à-dire l'information
> d'**une seule** observation. Toutes les autres sont inutilisables tant que l'état complet
> n'est pas fixé. À `2,3·10⁵` états/s/cœur, cela reste `3,2·10⁴` années-cœur.

**L'énoncé général, qui vaut au-delà de PCG.**

> Un crible d'état par les bits ne fonctionne que si la sortie observée lit **le côté de
> l'état qui forme un sous-système fermé** sous la transition. Pour un LCG modulo `2^W`,
> c'est le bas. Lire le haut — ce que font PCG par décalage, `splitmix64` par mélange et
> `xoshiro` par rotation — suffit à détruire la décomposition, sans rien changer à la
> taille de l'état.

C'est donc le **côté** que la sortie regarde, et non le nombre de bits, qui sépare un
générateur criblable d'un générateur qui ne l'est pas. Un état de `48` bits lu par le bas
tombe ; un état de `64` bits lu par le haut ne tombe pas.

## 7.37 — La moyenne, la variance, et le jackpot : ce que les marges bornent et ce qu'elles ne bornent pas

Le §210 conclut, et c'est exact :

> « Une grille ne peut pas battre le hasard si aucun de ses membres n'est biaisé. »

Cette phrase est vraie **de la moyenne**, et de rien d'autre. Elle mérite d'être découpée,
parce que le découpage dit exactement ce qu'un dossier de nullités permet de garantir.

### La moyenne : bornée par les marges, et par elles seules

Soit `G` une grille fixe de `k` numéros, `D` l'ensemble des vingt numéros sortis, et
`X_G = |G ∩ D|` le nombre de justes. Par linéarité,

    E[X_G] = Σ_{i ∈ G} p_i,     p_i = P(i ∈ D).

C'est **exactement** une fonction des marges, sans aucune hypothèse d'indépendance. Les
marges de l'archive étant conformes (§210 A, `max |z| = 2,72` sur quatre-vingts), aucune
grille ne bat la moyenne. Démontré, définitif.

### La variance : bornée par les paires

    Var(X_G) = Σ_{i∈G} p_i(1−p_i) + Σ_{i≠j ∈ G} (p_ij − p_i p_j).

La variance ne dépend donc **que** des marges et des lois de paires. Sous SRS,

    Var(X_G) = k · (1/4) · (3/4) · (80−k)/79     exactement,

soit `0,8900` pour `k = 5`. Le §213 mesure les `3 160` paires : le maximum de `|z|` vaut
`3,682` contre une loi empirique de maximum de moyenne `3,694` et d'écart-type `0,333`.
Le 95ᵉ centile simultané est donc `4,24`, et comme `N·p₂ = 4 242,5` avec un écart-type de
`63,15` :

> **Toute** paire de l'archive a un taux de co-sortie à moins de **`6,3 %`** en valeur
> relative de sa valeur SRS `19/316`, simultanément, à 95 %.

La variance de n'importe quelle grille est donc elle aussi épinglée à quelques pour cent.

### Le jackpot : **non borné** par ce qui précède, et c'est le point

On n'est pas payé à la moyenne. Le gain d'un keno est

    Π = Σ_h π_h · 1{X_G = h},     E[Π] = Σ_h π_h · P(X_G = h),

et `π` est **convexe** : on paie sur `4/5`, sur `5/5`. Or pour `k ≥ 3`, `P(X_G = k)` n'est
pas une fonction des marges ni des paires. Définissons le **relèvement d'ordre `k`**

    λ_G = P(G ⊆ D) / ∏_{j<k} (20−j)/(80−j).

Une grille de `λ_G > 1` est rentable, à marges rigoureusement conformes, dès que le
barème concentre le gain sur `h = k`. **C'est la brèche que laisse l'argument du §210.**

Ce que le §213 en borne :

| ordre | statistiques | 95ᵉ centile du max | borne sur `λ − 1` |
|---|---|---|---|
| `2` paires | `3 160` | `4,24` | `± 6,3 %` |
| `3` triplets | `82 160` | `4,90` | `± 15,6 %` |
| `≥ 4` | — | — | **non borné par ce qui précède** |

### La limite honnête

Un relèvement d'ordre cinq peut exister avec des paires et des triplets rigoureusement
nuls. La construction est classique : prendre une dépendance de type parité, où toute
marge d'ordre `< k` est exactement uniforme et où seule la coïncidence complète est
biaisée. Aucune borne d'ordre deux ou trois ne l'atteint.

C'est pourquoi le §213 mesure **aussi** la grille convexe directement, hors échantillon,
pour `k = 2, 3, 4, 5` et dans les deux sens. Mais la puissance y est faible : on attend
`22,75` jackpots de `5/5` sur `35 280` tirages avec un écart-type de `4,77`, de sorte que
le test ne tranche que sur un **doublement** du taux. Il exclut une dépendance d'ordre cinq
forte, non une dépendance fine.

> **Ce qui reste possible après le §213** : une dépendance d'ordre quatre ou plus, de
> relèvement inférieur à environ deux, invisible à tous les ordres inférieurs. Rien
> d'autre. C'est peu, ce n'est pas rien, et le dire est plus utile que d'écrire
> « conforme ».

### Le corollaire de méthode, et il vaut pour tout le dossier

Le §213 mesure, sur la première moitié, la grille de `k` numéros de plus fort taux de
`k/k`, puis la joue sur la seconde :

| `k` | `z` **en échantillon** (choix) | `z` **hors échantillon** (mesure) |
|---|---|---|
| `2` | `+3,24` | `+0,26` |
| `3` | `+4,44` | `−1,16` |
| `4` | `+5,58` | `−1,07` |
| `5` | `+6,34` | `−0,79` |

Le `z` en échantillon **croît avec `k`** — parce que le nombre de grilles parmi lesquelles
on choisit croît avec `k`, de `3 160` à `1,58 million`. Ce n'est pas un signal qui se
renforce : c'est un biais de sélection qui s'amplifie. Hors échantillon, tout s'effondre à
zéro.

> Toute « grille chaude » trouvée par recherche affiche un `z` spectaculaire. Ce `z` mesure
> la taille de la recherche, pas la qualité de la grille. C'est la raison mathématique pour
> laquelle un dossier de prédiction sans fenêtre de mesure disjointe ne vaut rien — et
> pourquoi le seul chiffre à regarder, ici comme ailleurs, est celui de la colonne de
> droite.
