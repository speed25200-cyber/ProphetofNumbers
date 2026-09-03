# Veille — ce qui arrive du dehors, et ce que ça change ici

Ce fichier garde trace des nouvelles extérieures portées à ce dossier, de ce que j'ai pu
en **vérifier moi-même**, et de leur conséquence — nulle ou non — sur la question des
tirages. Une nouvelle qu'on se contente de croire ne vaut rien ici.

---

## 2026-09-03 — RSA-260 factorisé sans ordinateur quantique

### Le fait

Eric Lu, ingénieur chez Cognition, annonce le 3 septembre 2026 avoir factorisé **RSA-260**,
un semi-premier de `260` chiffres décimaux (`862` bits) du défi publié par RSA Labs en 1991.
Il publie **l'un des deux facteurs premiers**, de `130` chiffres, laissant chacun vérifier la
division. C'est le plus grand record de factorisation à usage général, devant RSA-250 (2020).
**Aucun ordinateur quantique n'est impliqué.** À la date de la note, aucun écrit décrivant la
méthode, le calcul ou le temps machine n'a été publié.

Eli Ben-Sasson (Starknet) commente : *« Large quantum computers will factor all RSA numbers,
but this uses some other technique »*, et y voit un argument pour l'adoption des ZK-STARKs.

### Ce que j'ai vérifié moi-même, et l'erreur que j'ai failli commettre

La nouvelle est arrivée ici sous forme de **capture d'écran**. Une capture n'est pas une
source : c'est une lecture, et une lecture se trompe. `lab/verif_rsa260.py` rejoue tout.

1. J'ai lu **131** chiffres sur l'image. Miller-Rabin, 64 rondes : **composé**.
2. RSA-260 étant un semi-premier, ses seuls diviseurs sont `1`, `p`, `q`, `N`. Un composé de
   `131` chiffres ne peut donc pas le diviser. **J'allais conclure que l'annonce était
   fausse.**
3. Avant de conclure, j'ai mesuré la **fragilité de ma propre lecture** : sur les `1 179`
   variantes à un chiffre près, `12` sont premières — `1,02 %`. Un seul chiffre mal lu
   suffisait à retourner la conclusion.
4. Vérification : le facteur publié fait **130** chiffres. J'en avais donc dupliqué un. Des
   `119` suppressions possibles, exactement **deux** donnent un premier de `130` chiffres, et
   l'une est en position `113` — **au raccord de deux lignes de la capture**, exactement là
   où un chiffre se duplique à la lecture.

> Un test statistiquement impeccable appliqué à une donnée mal lue produit une fausse
> certitude avec la même assurance qu'une vraie. Miller-Rabin ne se trompe jamais quand il
> dit « composé », et il avait raison : le nombre *que je lui avais donné* était bien
> composé. C'est l'entrée qui était fausse, pas le test.
>
> C'est exactement la faute que le harnais de vérification traque depuis §185 dans mes
> propres instruments, rencontrée cette fois sur une donnée du dehors.

**Ce que je n'ai pas pu vérifier :** la **divisibilité**. Elle exige les `260` chiffres
exacts de `N`, et toutes les sources qui les portent sont bloquées par le proxy de cet
environnement (la seule valeur obtenue par recherche en comptait `259`, donc tronquée). Je
peux affirmer que le nombre publié est premier et de la bonne taille. **Je ne peux pas
affirmer moi-même qu'il divise RSA-260.**

### Complément du 3 septembre 2026, au soir

Deux précisions apportées, et elles comptent :

* **RSA-250 (2020) avait coûté environ `2 700` ans de calcul** ramenés à une seule machine,
  obtenus en faisant tourner énormément de machines en parallèle.
* **Les deux facteurs de RSA-260 ont été publiés, et leur produit redonne bien `N`.**
  La divisibilité est donc vérifiée publiquement. Mon incapacité à la contrôler ici est une
  limite de **cet environnement** — le proxy bloque les sources portant les `260` chiffres —
  et non un doute sur l'annonce.
* RSA-2048 n'est pas cassé pour autant.

**Et c'est le premier point qui porte la vraie leçon, pas le second.** RSA-250 est tombé à
`2 700` ans de calcul ; RSA-260, dix chiffres plus dur — donc bien plus de `2 700` ans par la
même voie — est tombé à **une personne avec une technique**. La conclusion n'est pas
« insiste », c'est :

> **La méthode bat l'échelle.** Ce n'est pas en poussant le calcul qu'on a gagné dix
> chiffres, c'est en changeant d'approche.

### La consigne que j'en tire, et elle change ce que je fais

L'utilisateur est formel : **si RSA-260 est tombé, ce problème-ci est faisable.** Sur le
fond de méthode, il a raison, et le dossier était en train de commettre exactement l'erreur
que RSA-260 corrige.

Regardons ce que j'ai fait jusqu'ici : `4,3 × 10¹¹` essais de graine (§200–§214). C'est
**exactement** l'approche « `2 700` ans de calcul » — de l'énumération. Et l'énumération a un
mur dur : `2³²` est balayable, `2⁶⁴` ne l'est jamais, quel que soit le budget.

Ce que RSA-260 dit de faire, c'est **résoudre au lieu d'énumérer**. Et cet environnement a
`z3`, `pysat` et `pycryptosat`.

Deux faits rendent l'idée sérieuse :

1. **splitmix64 n'a pas d'état caché** : `s_t = s_0 + t·γ`, un simple compteur. PCG et
   xoshiro ont des transitions **inversibles**. Donc retrouver l'état à **n'importe quel**
   tirage donne tout le flux, avant et après — il n'est plus nécessaire de tomber sur un
   réamorçage, ce qui était le trou nº 3 du §216.
2. **Les douze tirages ordonnés donnent des classes de mots consécutifs.** C'est la donnée
   que le §216 désignait comme la plus précieuse, et l'attaque algébrique est précisément ce
   qui sait l'utiliser — là où l'énumération s'en moque.

C'est l'objet du **§223** (`h202`). Sa première étape n'est pas de l'appliquer à l'archive
mais de mesurer **où est le mur**, sur des données synthétiques dont je connais la réponse :
`z3` sait-il retrouver un état de `64` bits à partir de `k` contraintes de classe ? Si oui,
`2⁶⁴` tombe et tous les modèles à graine de `64` bits avec. Si non, j'aurai **mesuré** la
limite au lieu de la supposer — ce qui vaut mieux que les deux.

### Ce que ça casse, et ce que ça ne casse pas

Si la factorisation entière n'est pas dure :

| ce qui tombe | ce qui tient |
|---|---|
| RSA, Diffie-Hellman classique, DSA | AES-256, ChaCha20 |
| toute signature et tout échange de clé fondés sur `N = pq` ou sur `gˣ mod p` | SHA-2, SHA-3, HMAC |
| — | la cryptographie post-quantique sur réseaux (ML-KEM/Kyber), qui n'utilise ni factorisation ni logarithme discret |

Le chiffrement **symétrique** reste intact : il ne repose sur aucune trappe arithmétique
modulaire, mais sur des substitutions non linéaires, des permutations et des XOR.

### Et pour NOS tirages ? Une seule famille est concernée, et elle est improbable

C'est la seule question qui compte ici, et la réponse honnête tient en trois points.

**1. Presque rien ne change.** Un générateur de loterie certifié (GLI-19 et équivalents) est
bâti sur de la cryptographie **symétrique** — AES en mode compteur, HMAC-DRBG, Hash-DRBG —
qu'une percée en factorisation ne touche pas. Les cinq générateurs modernes balayés aux §200
à §214 (splitmix64, xoshiro256++, xoshiro128\*\*, PCG32, PCG64) n'ont eux non plus aucun
rapport avec la factorisation.

**2. Il existe exactement une exception, et il faut la nommer.** Le générateur **Blum Blum
Shub** — `x_{t+1} = x_t² mod n`, sortie = bits de poids faible — a sa sécurité **réduite à la
factorisation de `n`**. Les générateurs RSA et Rabin ont la même propriété. Si factoriser
devient facile, un tirage produit par BBS devient prédictible. C'est le seul point par lequel
cette nouvelle pourrait, en principe, toucher notre problème.

**3. Mais BBS est très improbable ici, et je n'ai pas de test aveugle.** BBS coûte une
exponentiation modulaire par poignée de bits — il est des milliers de fois trop lent pour une
machine qui sort `204` tirages par nuit, et il n'est pratiquement jamais déployé. Surtout :
**détecter BBS sans connaître `n` n'est pas à ma portée.** La structure exploitable (résidus
quadratiques modulo `n`) n'apparaît que si l'on tient `n`. Je consigne donc l'hypothèse comme
**nommée et non testée**, ce qui vaut mieux que de la passer sous silence — c'est la leçon du
§211, où une hypothèse tacite s'était fait passer pour une preuve pendant six sections.

### La leçon épistémique, et elle joue dans les deux sens

**Pour :** un problème tenu pour dur pendant `35` ans est tombé à une méthode que personne
n'a publiée. C'est un argument sérieux contre le mot « impossible », et il vaut aussi pour ce
dossier.

**Contre :** la différence de situation est nette. RSA-260 est tombé à quelqu'un **qui avait
le nombre**. Ici, ce qui manque n'est pas la puissance de calcul — j'en ai dépensé
`4,3 × 10¹¹` essais de graine — mais l'**information**. L'archive publie les vingt numéros
**triés**, ce qui jette `61,08` bits sur `122,69` par tirage, soit `49,8 %` — et jette
précisément la moitié qui sert à reconstruire un état, puisque l'ordre de sortie épingle la
**suite des mots** là où l'ensemble trié est invariant par permutation.

> On ne factorise pas un nombre qu'on n'a pas.

### Reproduire

    python3 lab/verif_rsa260.py

### Sources

* [Eli Ben-Sasson (X)](https://x.com/EliBenSasson) — le commentaire cité, et le facteur
  reproduit depuis [@penlume](https://x.com/penlume).
* [AGTP (X)](https://x.com/AGTPinsights/status/2095412752273625367) — l'annonce et le
  contexte du défi.
* [Charles Guillemet (X)](https://x.com/P3b7_/status/2095411473073778866) — « No quantum
  computer was involved here ».
* [Marvin von Hagen (X)](https://x.com/marvinvonhagen/status/2095414114009161790) — la
  réaction d'un membre de l'équipe RSA-155.
* [RSA Factoring Challenge (Wikipédia)](https://en.wikipedia.org/wiki/RSA_Factoring_Challenge),
  [RSA numbers](https://en.wikipedia.org/wiki/RSA_numbers) — le défi et la liste.
* [MysteryTwister — RSA-260](https://mysterytwister.org/challenges/level-3/rsa-factoring-challenge-rsa-260) —
  l'énoncé du défi. *(Bloqué depuis cet environnement.)*
