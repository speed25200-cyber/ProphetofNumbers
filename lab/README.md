# Labo — protocole

Ce dossier cherche **de combien les prédictions peuvent être améliorées**, et
sous quelles conditions. Il part d'un fait établi ailleurs et non rediscuté
ici : `claude/AUDIT-CLAUDE.md` a fermé quatorze voies de détection sur les
70 560 tirages, toutes nulles. Le labo ne les refait pas.

## Deux pistes, et pourquoi la distinction décide de tout

**Piste A — détection.** Existe-t-il un biais exploitable ? Sous H₀,
`E[hits] = k/4` pour une grille de `k` numéros, **quel que soit le choix des
numéros**. Ce n'est pas une observation empirique, c'est un théorème :
l'espérance d'une hypergéométrique ne dépend pas de quels numéros on coche.
Donc aucune sélection — chauds, froids, retards, essaim, réseau de neurones —
ne déplace l'espérance d'un iota tant qu'il n'y a pas de biais réel. Toute
amélioration de piste A passe donc par la découverte d'un biais, et rien
d'autre. A priori : nul.

**Piste B — décision à biais nul.** À espérance figée, il reste des degrés de
liberté qui changent réellement le résultat : la **forme** de la loi des gains
(une table de gains non linéaire n'est pas indifférente à la géométrie des
grilles), le choix de la mise, la corrélation entre grilles jouées ensemble,
et la calibration de ce que l'app affiche. Ces gains-là sont démontrables et
n'exigent aucun biais. C'est là que se trouve ce qui est réellement
améliorable.

Confondre les deux est la faute qui produit les applications de loterie
mensongères : elles vendent de la piste B (jolies grilles) en la présentant
comme de la piste A (prédiction).

**Précision apportée après coup (§7.37, §213, §217).** Le théorème ci-dessus est
exact, et il ne porte que sur l'**espérance du nombre de justes**. Or on n'est
pas payé à l'espérance : le barème paie sur `4/5`, sur `5/5`, et à dix numéros
sur `0/10`. Le gain est convexe **aux deux bouts**, et

> `P(les k sortent)` ne dépend **pas** des marges. Elle dépend de la loi jointe.

Deux grilles aux marges identiques — donc à espérance de justes identique — ont
des taux de jackpot **différents** si leurs membres sont liés. C'est un degré de
liberté de piste B que la formulation initiale laissait implicite, et il fallait
le mesurer et non le supposer nul. Le découpage exact est :

| ce qui est fixé | par quoi | mesuré où |
|---|---|---|
| la moyenne du nombre de justes | les marges seules — théorème | §210 A |
| la variance | les marges **et les paires** | §213 A |
| `P(k/k)`, `P(0/k)`, le barème entier | la loi jointe à tous les ordres | §213 B–D, §215, §217 |

Ces trois lignes sont conformes. La piste B garde donc ses degrés de liberté
**de géométrie et de mise** — ceux que le barème lui-même offre — et n'en tire
aucun d'une dépendance interne des tirages, parce qu'il n'y en a pas de mesurable.

## Trois règles

**1. Le null est simulé, jamais tabulé.** L'audit s'est trompé trois fois en
prenant une formule pour l'espérance exacte — χ²/df attendu à 1,00 au lieu de
0,76 (§1), plus longue série à 13,12 au lieu de 12,64 (§5), recouvrement
conditionné au bonus à 5,00 au lieu de 5,57 (§14). Les trois donnaient un
signal franc qui n'existait pas. `lab.calibrate()` n'accepte aucune espérance
fournie à la main.

**2. Pré-enregistrement.** Statistique, null et seuil déclarés avant de
regarder le résultat, via `lab.preregister()`. Le jeton scellé est rendu à
`lab.record()`. Une hypothèse formulée après coup n'est pas un test.

**3. Multiplicité sur le registre entier.** `lab.holm()` compte *tous* les
tests jamais tentés, ceux de l'audit compris (pré-chargés dans
`ledger.jsonl`). Un z de +2 n'est pas une découverte quand on en est au
cinquantième test : c'est la base rate. L'audit en a produit trois par
hasard, sur des données dont l'aléa était garanti par construction.

## Deux obligations

**Puissance mesurée.** Un résultat nul dont on ignore la sensibilité n'est pas
un résultat, c'est une absence d'information. Toute expérience de piste A
fournit `lab.power()` : la fraction des réplicats *contaminés* que le test
détecte. Sans témoin positif, un test qui ne se déclenche jamais est
indistinguable d'un test cassé.

**Contrôle de fuite.** Tout prédicteur passe `lab.leak_check()` avant d'entrer
au registre. Il réécrit l'archive **en place** à partir de `t` inclus, cumuls
compris, et vérifie que le choix en `t` ne bouge pas. Validé contre quatre
tricheurs connus, dont le décalage d'indice `cum[t]` au lieu de `cum[t-1]` —
la fuite accidentelle la plus probable, et la plus discrète : elle ne fait
basculer que 2 sondes sur 10.

## API

```python
import lab
a = lab.load()                      # 70 560 tirages, cache .npz, ~40 ms
a.mask                              # (N,80) bool  : n tiré au tirage i
a.nums, a.boost, a.bonus, a.ts      # champs bruts

null = lab.calibrate(stat, len(a), reps=400)     # H0 par simulation SRS
null.z(obs); null.p_two_sided(obs)               # p empirique, jamais gaussien
lab.power(stat, contaminate, len(a), null)       # sensibilité mesurée

hits = lab.walk_forward(a, predict, k=10)        # predict(past, t), past borné à [0,t)
e, log10_e = lab.evalue(hits, k=10)              # e-process, valide à tout instant d'arrêt
ok, spots = lab.leak_check(a, predict, k=10)     # décisif, pas déclaratif

tok = lab.preregister(id, hypothese, statistique, null_method, decision, track)
lab.record(tok, observed, null=null, power_at=..., verdict=..., notes=...)
lab.holm()                                       # verdict corrigé, registre entier
```

`past.counts` (sorties cumulées), `past.gaps` (retards) et
`past.counts_window(w)` (sorties sur les `w` derniers tirages) sont servis en
O(1) depuis des cumuls précalculés : une marche avant complète sur 70 060
tirages prend ~1 s au lieu de ~10 min. Aucun de ces accesseurs ne lit
au-delà de `t-1`, et `leak_check` réécrit les cumuls en même temps que les
tirages — un décalage d'indice y est donc attrapé, jamais masqué par un
cache périmé.

## Les deux linéarités (§230, §232, §233)

Un générateur peut être linéaire de **deux** façons, et ce sont deux mondes
disjoints qui demandent deux outils sans rapport :

| famille | outil | ce qui la ferme |
|---|---|---|
| **`F₂`-linéaire** — Mersenne Twister, `xorshift`, LFSR, WELL | **Berlekamp-Massey** | §124, sur le flux du bonus : tout état de moins de `47 040` bits |
| **`Z/2^W`-linéaire** — les congruentiels | **réseau euclidien** (LLL + Babai) | §230 (`12` jeux `mod 2⁶⁴`) et §232 (`18` jeux, huit modules, plus un crible **exhaustif** de contrôle) |
| **ni l'un ni l'autre** — PCG, `xoshiro`, `splitmix64`, CSPRNG, matériel | *aucun outil connu* | rien — et le §233 dit pourquoi |

Le §124 avait fermé la première et écrivait noir sur blanc ce qu'il ne fermait
pas : *« les générateurs non `F₂`-linéaires : LCG, PCG, xoshiro, splitmix64,
tout CSPRNG »*. La moitié congruentielle est restée ouverte cent sections
durant, non par difficulté mais faute d'un **canal ordonné** où passer un
réseau — et ce canal était publié depuis le début : le `bonus` est toujours
l'un des vingt (§77), donc un mot précis du flux, à pas constant sous le
budget de bloc fixe du §225.

**La leçon de méthode, réutilisable :** un outil qui rend zéro n'a rien dit
tant qu'on ne lui a pas fait retrouver une solution qu'on y a mise. Le crible
exhaustif du §232 manquait sa propre solution plantée sur toutes les
configurations à incrément non nul — le pas d'un LCG est *affine*, et je
l'inversais comme s'il était *linéaire*. Le bloc `15` du vérificateur garde
cette faute sous contrôle permanent.

## Détecter, identifier, gagner — trois choses différentes

Une borne de détectabilité (« ce biais aurait-il été vu ? ») n'est pas une
borne d'exploitabilité. Le χ² met en commun l'écart des 80 numéros pour dire
*qu'il y a* un biais ; un joueur doit savoir *lesquels* sont biaisés, ce qui
est plus dur, et il ne dispose pour cela que des mêmes données. Toute borne
de piste A doit donc préciser laquelle des trois elle établit —
`c2_apprentissage.py` mesure l'écart entre les deux dernières.

## Vérifier du Swift sans compilateur Swift

Aucune toolchain Swift n'est joignable depuis cet environnement
(`download.swift.org` est bloqué par la politique réseau, et le paquet apt
« swift » est le stockage OpenStack), et SwiftUI ne compile de toute façon
que sur Apple. Compter les accolades ne prouve rien. Deux outils remplacent
ce qu'ils peuvent remplacer, et disent ce qu'ils ne couvrent pas.

```
python3 lab/verif_swift.py [ref]     # syntaxe, par une vraie grammaire Swift
python3 lab/verif_logique.py         # justesse numérique, par exécution
```

`verif_swift.py` parse avec `tree-sitter-swift` et signale les nœuds ERROR
et MISSING. Il compare à une **référence git** plutôt que d'exiger zéro :
la grammaire a des limites connues sur `x as? T ?? y` et sur un opérateur
en tête de ligne de suite, deux constructions présentes dans du code qui
tourne en production. Ce qui se contrôle utilement est le delta.

`verif_logique.py` transcrit fidèlement les fonctions ajoutées — même
formule, même ordre d'opérations — et vérifie que chaque assertion des tests
Swift serait satisfaite, aux cinq mises.

Ce que ces deux outils **ne** couvrent pas : le typage. Un désaccord de types
resterait invisible. Le risque de typage le plus probable ici étant l'ordre
des arguments d'un initialiseur par membre, il est contrôlé à part en
extrayant l'ordre des champs de chaque `struct` et en le comparant à celui
de son site de construction.

## Dépendances

Tout le labo tourne sur **numpy seul**, à une exception près : `h64_seuil_smt.py`
demande **`z3-solver`** (`pip install z3-solver`). En son absence le fichier
l'annonce et s'arrête — il ne fabrique aucun résultat de remplacement.

Cette exception est assumée : le §84 mesure ce qu'un solveur SMT sait faire du
mur nommé au §83, et cette mesure n'a pas d'équivalent en algèbre linéaire.

## Ce qui ne peut pas être tranché ici

L'archive est **triée** : `n1..n20` est croissant sur les 70 560 lignes, donc
l'ordre de sortie des boules — qui doublerait l'information par tirage, de
61,6 à 124 bits — n'y est pas. Et le réseau vers `jeux.loro.ch` est fermé
depuis cet environnement (403 au CONNECT). Les questions qui exigent le flux
live sont donc spécifiées ici comme **instruments à embarquer dans l'app**,
pas conclues.

Ce qui est relevé à l'écran va dans deux fichiers, et la distinction compte :

| fichier | contenu | qui l'utilise |
|---|---|---|
| `draws_ordered.csv` | tirages dont **l'ordre de sortie** est visible | §68 à §86 — et eux seuls |
| `observations_ecran.csv` | ce que l'écran publie tel quel, ordre absent possible, mais avec le **boost affiché** (`1.5` compris) et le **bonus** | §92 |

**Deux relevés manquent, et ils sont petits.** (1) Un enregistrement d'un *seul*
tirage montrant la grille **se remplir boule après boule** puis la boule EXTRA
du même tirage : il tranche le §37, indécidable depuis. (2) **Vingt arrêts de la
roue du boost**, avec la fraction de l'aiguille dans son secteur : ils disent si
la roue publie une variable continue en plus du multiplicateur (§92, section 5).
