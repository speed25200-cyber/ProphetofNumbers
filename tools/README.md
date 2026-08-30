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
