# tools — balayage d'espace d'états

Ferment la dernière classe de générateurs atteignable par le calcul :
les états de 48 bits (`java.util.Random`, LCG modulo 2⁴⁸). Contexte et
justification dans [`../claude/AUDIT-CLAUDE.md`](../claude/AUDIT-CLAUDE.md).

Un état n'est retenu que s'il reproduit **les 20 numéros** du tirage
cible. Confirmer ensuite sur le tirage suivant élimine tout faux positif
résiduel (probabilité d'un faux positif sur 2⁴⁸ : ≈ 8 × 10⁻⁷).

## CPU — `sweep48.c`

```sh
cc -O3 -march=native -o sweep48 sweep48.c
./sweep48 0 1099511627776  5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
```

Mesuré : **156 M états/s par cœur**. Tranche `[lo, hi)` en argument —
parallélisation triviale, aucune communication entre workers.

| Configuration | 2⁴⁸ intégral |
|---|---|
| 1 cœur | 20,9 jours |
| 64 cœurs | ~8 heures |

## GPU — `sweep48.cu`

```sh
nvcc -O3 -arch=sm_80 -o sweep48cu sweep48.cu     # sm_80 = A100, sm_89 = L40S/4090
./sweep48cu 0 281474976710656  5 6 10 11 13 22 26 28 32 35 37 38 39 41 50 55 66 68 78 79
```

Logique identique à la version CPU (validée à 156 M états/s/cœur), portée
en noyau à boucle à pas de grille. Le programme affiche son débit réel et
extrapole la durée d'une couverture complète.

Estimation A100 80 Go : **1 h 30 à 3 h** pour les 2⁴⁸ complets. La VRAM
est sans objet — le noyau tient en registres, aucun accès mémoire globale
dans la boucle interne ; il tournerait à l'identique sur une carte 8 Go.
Le facteur limitant est le débit entier et la divergence de warp.

> Le noyau CUDA n'a pas pu être compilé ni mesuré dans l'environnement de
> développement (aucun GPU disponible). Sa logique est celle de la version
> CPU, testée. Vérifier le débit affiché sur une petite tranche avant de
> lancer une couverture complète.

## Découper le travail

```sh
# 8 tranches de 2^45 sur 8 GPU
for i in $(seq 0 7); do
  LO=$(( i * 35184372088832 )); HI=$(( (i+1) * 35184372088832 ))
  CUDA_VISIBLE_DEVICES=$i ./sweep48cu $LO $HI <20 numéros> &
done
```

Toute sortie `HIT <état>` est à vérifier immédiatement sur le tirage
suivant — et, si elle se confirme, à signaler à l'exploitant avant toute
autre chose.

---

# sweep_order et sweep_mt — la région du RÉ-AMORÇAGE

## Ce que ces deux outils couvrent, et que rien d'autre ne couvrait

Toutes les attaques du labo (h4 à h20) supposent un générateur qui **tourne
en continu** : l'état à la fin d'un tirage est celui du début du suivant.
C'est ce qui permet de résoudre (a, c) sur plusieurs tirages au lieu de les
énumérer.

Une implémentation qui **ré-amorce le générateur à chaque tirage** les défait
toutes d'un coup — et c'est le cas le plus courant en pratique, celui qu'on
écrit quand on tape `new Random(seed)` au début de la fonction de tirage.
Contre lui, la seule attaque possible est le balayage de l'espace des
graines.

`sweep48.c` faisait cela pour **une** famille, **un** échantillonneur, et
contre l'**ensemble** des vingt numéros. Ces deux outils changent les trois
points.

## L'ordre change tout

Travailler sur l'ORDRE de sortie plutôt que sur l'ensemble fait passer le
filtre de 1/4 à 1/80 par pas. Deux conséquences, et la seconde est la plus
importante :

* le balayage est plus rapide — une graine fausse meurt au premier numéro,
  soit 1,01 pas de générateur en moyenne au lieu de 1,33 ;
* la probabilité qu'une graine fausse survive tombe de C(80,20)⁻¹ ≈ 3·10⁻¹⁹
  à (80!/60!)⁻¹ ≈ **1·10⁻³⁷**. Sur 2³² graines et 32 combinaisons, le nombre
  attendu de faux positifs vaut 1,4·10⁻²⁷.

**Toute touche est donc réelle, et aucune confirmation n'est nécessaire.**

## Une erreur de protocole, et sa correction

Les premiers balayages ont été lancés avec une confirmation : une graine
n'était retenue que si elle reproduisait AUSSI un second tirage ordonné.
C'était une faute, et elle allait précisément contre le but.

Dans l'hypothèse du ré-amorçage, chaque tirage a sa PROPRE graine — c'est
toute la définition. Exiger qu'une même graine reproduise deux tirages
différents ne teste pas le ré-amorçage : cela teste un opérateur qui
utiliserait la même graine à chaque tirage, ce qui n'a aucun sens. Un
générateur réellement amorcé par le numéro de tirage aurait été trouvé sur
le premier tirage, puis **jeté** par la confirmation.

La correction est de balayer sans confirmation. Elle ne coûte rien en
rigueur, puisque le filtre d'ordre à 10⁻³⁷ rend une touche fausse
impossible ; et elle rend le balayage universel sur les schémas d'amorçage :

> balayer sans confirmation les graines de [0, 2³²) contre UN tirage ordonné
> écarte d'un coup TOUT schéma d'amorçage dont la graine tombe dans cette
> plage — numéro de tirage, numéro plus constante, seconde d'époque, petite
> graine fixe, compteur. Il n'est pas nécessaire de les énumérer.

## sweep_order — huit familles, quatre échantillonneurs

```sh
cc -O3 -march=native -pthread -o sweep_order sweep_order.c
./sweep_order --selftest
./sweep_order 0 4294967296  33 35 45 44 27 70 34 77 7 64 73 22 63 61 8 14 2 26 72 43
```

Générateurs : java.util.Random, LCG 32 MSVC, LCG 32 glibc, xorshift32,
xorshift64\*, splitmix64, pcg32, LCG 64 MMIX.
Échantillonneurs : modulo + rejet, multiply-shift + rejet, Fisher-Yates
modulaire, Fisher-Yates multiply-shift.

Débit mesuré : **1,3·10⁹ tests graine×combinaison par seconde** sur quatre
cœurs, soit 2³² × 32 combinaisons en 2 min 13 s.

`--selftest` fabrique un tirage depuis une graine connue pour chacune des
trente-deux combinaisons et exige de la retrouver : **32/32**, avec
exactement une graine compatible à chaque fois.

## sweep_mt — Mersenne Twister, et les algorithmes de CPython

```sh
cc -O3 -march=native -pthread -o sweep_mt sweep_mt.c
./sweep_mt --selftest
./sweep_mt 0 4294967296  <o1..o20>
```

MT19937 mérite son propre programme : son amorçage coûte deux mille
opérations là où un LCG en coûte une, et il ne peut pas partager la même
boucle sans la ralentir d'un facteur mille. Il le mérite aussi parce que
c'est le générateur le plus répandu du logiciel ordinaire — `random` de
Python, `mt_rand` de PHP, `RandomState` de numpy, la bibliothèque standard
de Ruby.

Amorçages : `init_genrand(s)` (forme canonique) et `init_by_array([s])`
(ce que fait `random.seed(n)` de CPython).
Échantillonneurs : `random.sample` méthode pool, Fisher-Yates modulaire,
Fisher-Yates multiply-shift, modulo + rejet, `random.shuffle` puis les vingt
premiers.

Les algorithmes de CPython sont transcrits à la ligne près, et **vérifiés
contre CPython lui-même** : `random.seed(987654)` puis `random.sample` et
`random.shuffle` sont exécutés en Python, et le balayage doit retrouver la
graine 987654 depuis leurs sorties. Il la retrouve, pour les deux.

Cette confrontation a d'ailleurs attrapé une transcription fausse. Le
`_randbelow` de CPython demande `n.bit_length()` bits et non
`(n-1).bit_length()` — les deux coïncident partout sauf quand n est une
puissance de deux, et n parcourt ici 80, 79, …, 61. La divergence tombait
donc pile sur n = 64, au **dix-septième** numéro : seize numéros justes puis
une dérive silencieuse, qu'aucun autotest interne n'aurait pu voir.

Débit : 2³² graines × 10 combinaisons en ≈ 2 h 20 sur quatre cœurs.

## sweep_java48 — l'état 48 bits COMPLET, en secondes

```sh
cc -O3 -march=native -pthread -o sweep_java48 sweep_java48.c
./sweep_java48 --selftest
./sweep_java48 <o1..o20>
```

`java.util.Random` est la faille classique des loteries en ligne. Les outils
ci-dessus la couvrent pour les graines de [0, 2³²) ; il reste 2⁴⁸ états, soit
78 heures de force brute par échantillonneur sur quatre cœurs.

Il n'y a pas besoin de force brute. `next(31)` rend `(int)(s >>> 17)`, et
`nextInt(bound)` pour un `bound` qui n'est pas une puissance de deux rend
`next(31) % bound`. Donc pour une borne PAIRE,

    p_i mod 2^v  =  ((s_i >>> 17) mod 16) mod 2^v,   v = v₂(bound) ∧ 4

c'est-à-dire **les bits 17 à 20 de l'état**. Ni les bits de poids faible, où
vit le levier 2-adique habituel ; ni ceux de poids fort, où vivent les
attaques par réseau : ceux du **milieu**. Et ils sont exploitables parce que
le LCG modulo 2⁴⁸ reste clos modulo 2²¹.

| phase | ce qu'elle fait | coût |
|---|---|---|
| 1 | énumérer s mod 2²¹, propager, exiger les bits 17-20 à chaque pas | 2·10⁶ |
| 2 | pour les ≈ 30 survivants, énumérer les 27 bits de poids fort et rejouer | 4·10⁹ |

La couverture de 2⁴⁸ passe ainsi de 78 heures à quelques dizaines de
secondes — un facteur 10⁴.

**Le piège de la borne 64.** `nextInt` traite les puissances de deux à part :
`r = (int)((bound * (long)next(31)) >> 31)`, ce qui prend les bits de poids
FORT. Parmi 80, 79, …, 61, une seule borne est concernée — 64, au dix-septième
pas. La phase 1 doit donc la sauter, et la phase 2 la vérifier comme le reste.
L'oublier ferait rater le vrai état sans rien signaler.

`--selftest` récupère trois états témoins dont deux hors de portée d'un
balayage 2³² (140 737 488 355 327 et 20 015 998 343 868) : **3/3**, avec
exactement un état 48 bits trouvé à chaque fois.

## sweep_linked — l'amorçage LIÉ AU NUMÉRO DE TIRAGE, sur l'archive entière

```sh
cc -O3 -march=native -pthread -o sweep_linked sweep_linked.c
./sweep_linked --selftest
./sweep_linked 0 4294967296 tirages.txt      # « id n1 … n20 » par ligne
```

`sweep_order` balaie les graines contre UN tirage ordonné. Il écarte donc
tout schéma d'amorçage dont la graine tombe dans la plage — mais pour ce
tirage seulement, et le dossier ne dispose que de cinq tirages ordonnés, tous
du même jour.

L'archive contient 70 560 tirages étalés sur des mois. Elle est triée, donc
son filtre est plus faible (1/4 par numéro au lieu de 1/80), mais elle permet
ce que cinq tirages ne permettent pas : tester une **relation** entre la
graine et le numéro de tirage, et la confirmer sur des tirages séparés dans
le temps.

L'hypothèse testée est

    graine du tirage t  =  numéro du tirage t  +  B

pour tout décalage B de [0, 2³²). C'est la forme qu'on écrit quand on veut un
tirage reproductible et vérifiable — `new Random(drawId)` — et elle est
**invisible** pour un balayage qui exigerait la même graine à deux tirages
différents.

Un B faux meurt au premier ou au deuxième numéro du premier tirage. Un B faux
qui survivrait au premier tirage entier a une probabilité C(80,20)⁻¹ ≈
2,8·10⁻¹⁹ de le faire ; dix tirages liés la portent sous 10⁻¹⁸⁰.

`--selftest` fabrique dix tirages liés par un décalage témoin et exige de le
retrouver : **48/48**, chacun rendant exactement le décalage témoin.

---

# sweep_keys — l'échantillonneur qui consomme QUATRE-VINGTS sorties

Tous les échantillonneurs ci-dessus consomment **vingt** sorties : un numéro
par sortie. Aucun n'en consomme quatre-vingts. Or

```sql
SELECT numero FROM boules ORDER BY RANDOM() LIMIT 20
```

et son équivalent en une ligne dans n'importe quel langage —
`argsort(rand(80))[:20]`, `sorted(range(80), key=lambda _: rng())[:20]` —
tirent **une clé par numéro du bocal** et gardent les vingt plus petites.
C'est un idiome extrêmement répandu, et il était couvert nulle part.

Il est invisible pour tous les autres outils, et pour une raison de fond :

* les attaques algébriques (h4 à h21) supposent vingt sorties consécutives
  reliées par une récurrence — ici les vingt numéros publiés dépendent des
  quatre-vingts clés à la fois, et rien ne relie deux numéros voisins ;
* les balayages précédents rejettent une graine dès que le **premier** numéro
  ne tombe pas juste — ce qui n'a aucun sens ici, puisque le premier numéro
  publié est celui dont la clé est la plus petite parmi les quatre-vingts, et
  ne peut donc être jugé qu'une fois les quatre-vingts tirées.

```sh
cc -O3 -march=native -pthread -o sweep_keys sweep_keys.c
./sweep_keys --selftest
./sweep_keys 0 4294967296  <o1..o20>
```

Douze familles × deux conventions (clés croissantes ou décroissantes). Le
test vérifie que les vingt numéros publiés sont exactement ceux de plus
petite clé, **et dans l'ordre des clés**.

Pas de sortie anticipée possible : il faut les quatre-vingts clés avant de
pouvoir juger. Le balayage coûte donc ≈ 57 min par tirage pour 2³² graines
et 24 combinaisons sur quatre cœurs, contre 2 min pour `sweep_order`.

`--selftest` : **24/24**, chacune rendant exactement une graine — le témoin,
seul parmi trois millions.

---

# sweep_rand — trois angles morts, dont un qui rendait les autres FAUX

Trois familles et un échantillonneur manquaient, et ce sont trois des
chemins les plus fréquentés du logiciel ordinaire.

## 1. Le vrai `rand()` de la glibc

`sweep_order` nomme une famille « LCG32 glibc » : s → 1103515245·s + 12345
mod 2³¹. C'est le TYPE_0 de la glibc, qu'on n'obtient qu'en réduisant
explicitement l'état à huit octets. **Le `rand()` qu'on obtient en tapant
`srand(); rand();` sur Linux n'est pas un LCG** : c'est une récurrence
additive décalée, r[i] = r[i−3] + r[i−31], dont le LCG ne sert qu'à remplir
la table. 992 bits d'état au lieu de 31, pas la même sortie, pas la même
trace. Balayer l'un ne dit rien de l'autre.

C'était l'omission la plus grave du dossier : « le `rand()` du C » est la
première chose qu'écrit quiconque n'a pas réfléchi au sujet — exactement le
profil recherché. Les quatre tailles de table sont couvertes (TYPE_1 à
TYPE_4, soit `initstate` à 32, 64, 128 et 256 octets).

## 2. Les LCG à module premier

Toutes les attaques algébriques du labo vivent dans Z/2^k : valuation
2-adique, inverses modulo une puissance de deux, racines de Hensel. Un
générateur de Lehmer — s → a·s mod (2³¹−1) — n'offre **aucune** de ces
prises. MINSTD est pourtant `minstd_rand` du C++11 et le générateur de
référence de tous les manuels. Ajoutés : 16807, 48271, plus RANDU (65539) et
le LCG de Borland/Delphi.

## 3. L'échantillonneur par flottant — et pourquoi il invalidait le reste

Les quatre échantillonneurs existants consomment **un** mot par numéro. Or

```java
int n = (int)(Math.random() * 80) + 1;
```

est de très loin la façon la plus répandue d'écrire « un numéro au hasard »
en Java — et `nextDouble()` consomme **deux** appels à `next()` :

    d = ((next(26) << 27) + next(27)) / 2⁵³

Un balayage qui consomme un mot par numéro se **désynchronise donc dès le
premier**, et meurt en croyant avoir éliminé la graine. Les sorties sont les
mêmes, la graine est la bonne, et le test répond non.

C'est le pire type d'angle mort : celui qui rend un résultat négatif faux
sans jamais rien signaler. Les deux échantillonneurs par flottant sont donc
appliqués aux **vingt** familles, y compris les douze déjà balayées.

## Économie

L'amorçage de la glibc coûte 341 pas là où un LCG en coûte un. Pour ne pas
le payer six fois, chaque graine est amorcée une fois et ses sorties passent
par un **tampon paresseux** : les six échantillonneurs lisent le même flux,
qui ne se remplit qu'à la demande. Une graine fausse mourant au premier
numéro, le tampon dépasse rarement deux entrées.

Les couples (famille 0-11, échantillonneur 0-3) sont affichés « déjà
couvert » et non rebalayés.

## Validation — contre les implémentations RÉELLES

L'autotest interne ne prouve que la cohérence du programme avec lui-même.
Comme pour `sweep_mt`, chaque transcription est donc confrontée à
l'implémentation d'origine :

| confronté à | ce qui est vérifié | résultat |
|---|---|---|
| `rand()` de la glibc | 280 sorties, 7 graines dont 0, 2³¹ et 2³²−1 | 0 écart |
| `random()` + `initstate` | 270 sorties, tailles 32/64/256 o | 0 écart |
| `java.util.Random` (JVM) | tirage par `nextDouble()`, avec rejet | graine retrouvée |
| `java.util.Random` (JVM) | tirage par Fisher-Yates `nextDouble()` | graine retrouvée |
| `std::minstd_rand` | tirage par modulo, C++11 | graine retrouvée |
| `std::minstd_rand0` | tirage par Fisher-Yates | graine retrouvée |
| arithmétique flottante | `(w·80)>>53` contre `(int)(d*80)` | 0 écart / 4·10⁶ |

Les deux dernières lignes méritent un mot. La forme entière `(w·80)>>53` ne
va **pas** de soi : `w·80` demande jusqu'à 60 bits, que la mantisse de 53
bits d'un `double` ne porte pas, et l'arrondi pourrait franchir un entier.
La borne critique est w ≡ 0 mod 2⁴⁹ — testée explicitement à ±3 près, où
l'arrondi est le plus tendu. Aucun écart.

Cette confrontation a aussi corrigé deux étiquetages faux, du même genre que
celui qu'avait attrapé `sweep_mt` : MINSTD était amorcé `graine mod (m−1) + 1`
et RANDU forçait le bit de poids faible. Dans les deux cas la **couverture**
était complète — mais une touche aurait rendu une graine décalée, c'est-à-dire
inutilisable pour qui aurait voulu la vérifier.

Enfin, le critère de l'autotest a dû être corrigé. Exiger que la première
graine compatible soit le témoin est un critère **faux** : RANDU et glibc
TYPE_0 vivent modulo 2³¹, MINSTD modulo 2³¹−1, si bien que deux graines
distinctes de [0, 2³²) mènent au même état et sont légitimement toutes deux
compatibles. La seule question qui compte est : le témoin survit-il ?

`--selftest` : **70/70**.
