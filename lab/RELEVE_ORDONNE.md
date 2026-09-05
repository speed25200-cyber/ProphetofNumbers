# Relevé ordonné — la seule donnée qui manque, et comment la produire

## Pourquoi ce fichier

Le §216 se termine sur une asymétrie précise. RSA-260 est tombé à quelqu'un **qui avait le
nombre** : toute l'information était sur la table, il manquait une technique. Ici c'est
l'inverse — le §223 démontre que **j'ai la technique**, et il me manque l'entrée.

Le chiffre exact :

    log₂ C(80,20) = 61,617 bits     l'ensemble des vingt numéros — ce qui est publié
    log₂ 20!      = 61,077 bits     l'ORDRE de sortie — ce qui ne l'est pas
    log₂ 80!/60!  = 122,694 bits    le tirage complet

**Le tri jette `49,8 %` de l'information de chaque tirage** — et il jette la moitié qui sert
à reconstruire un état, parce que l'ordre épingle la **suite des mots** là où l'ensemble
trié est invariant par permutation.

> **Vingt tirages ordonnés valent plus, pour cette question, que les 70 560 tirages triés
> dont je dispose.** Cent seraient confortables.

## Ce qu'il faut relever, exactement

Pour chaque tirage, **les vingt numéros dans l'ordre où ils apparaissent à l'écran** — pas
triés, pas regroupés. Rien d'autre n'est indispensable ; le reste est du bonus.

| champ | indispensable | pourquoi |
|---|---|---|
| `o1 … o20` — les numéros **dans l'ordre de sortie** | **oui** | c'est toute la valeur du relevé |
| `id` — l'identifiant du tirage | oui | pour recoller à l'archive |
| `bonus` | non | permet de croiser avec le §222 |
| `boost` | non | permet de croiser avec le §224 |

**Ce qui rend un relevé inutilisable :** avoir noté les numéros triés, ou avoir perdu
l'ordre entre deux d'entre eux. Un tirage à l'ordre douteux vaut mieux marqué douteux que
deviné.

## Le format

Un CSV, exactement comme `lab/draws_ordered.csv` :

    id,source,o1,o2,o3,o4,o5,o6,o7,o8,o9,o10,o11,o12,o13,o14,o15,o16,o17,o18,o19,o20,bonus
    1381023,ecran-live,33,35,45,44,27,70,34,77,7,64,73,22,63,61,8,14,2,26,72,43,

Le champ `bonus` peut rester vide. `source` sert à tracer d'où vient la ligne.

## Combien, et pourquoi ce nombre

L'attaque du §223 a besoin de **classes de mots consécutifs**. Sous un échantillonneur à
rejet, les premiers numéros d'un tirage sont les classes des premiers mots **tant qu'aucun
doublon n'est apparu** :

| on utilise les `n` premiers numéros | `P(aucun rejet)` | `P(au moins un tirage sur N s'y prête)` |
|---|---|---|
| `n = 12` (le minimum pour `64` bits) | `0,4199` | `1 − 0,58ᴺ` |
| `N = 12` tirages | | `99,85 %` |
| `N = 20` tirages | | `99,99 %` |
| `N = 100` tirages | | `> 1 − 10⁻²³` |

**Vingt tirages suffisent pour essayer. Cent ferment la question.**

## Ce que j'en fais, et en combien de temps

    python3 lab/experiments/h202_attaque_par_reseau.py

L'attaque tourne sur `12` LCG `mod 2⁶⁴` à constantes publiées × `2` règles de sortie ×
`14` motifs de rejet. Chaque résolution de réseau prend `~0,4` s ; vingt tirages, c'est
`6 720` résolutions, soit **moins d'une heure**. La vérification est en entiers **exacts** :
un candidat est juste ou faux, il n'y a pas de zone grise.

Si un candidat passe, il donne l'**état complet** du générateur — donc tous les tirages
suivants, et tous les précédents.

## Et si le générateur n'est pas linéaire ?

Alors le réseau ne mord pas : un mélangeur non linéaire (splitmix64, la rotation de PCG, le
brasseur de xoshiro) n'a **aucun** réseau, et le mur de `2⁵⁷·⁷` du §7.36 reste entier.

Mais le relevé ordonné garde sa valeur : il double l'information par tirage, ce qui remet
en jeu toute la famille d'attaques que le §7.33 avait fermées faute d'alignement. C'est le
seul levier de ce dossier qui n'est pas une question de puissance de calcul.

## Les deux autres relevés qui vaudraient le détour

1. **Le nom du logiciel ou du fournisseur du générateur.** Il supprime le balayage aveugle
   des familles et transforme une recherche en vérification.
2. **Une seconde source du même tirage** — deux écrans, deux horodatages. Un horodatage à la
   milliseconde rétrécirait la fenêtre de graine du §212 d'un facteur `1 000`.

---

## Addendum (§230) — une partie de ce relevé était déjà publiée

Ce fichier dit qu'il manque au dossier *une suite ordonnée de sorties*. C'était exact **sous le
modèle en vigueur quand il a été écrit** : à pas variable — le rejet consommant un nombre
aléatoire de mots par tirage — un mot isolé par tirage ne sert à rien, faute de savoir de
combien de pas ses voisins sont séparés.

Le **§225** a corrigé ce modèle. Sous un budget **fixe** de `P` mots par tirage, le rejet se
faisant *à l'intérieur*, deux mots au même décalage dans deux blocs consécutifs sont séparés
d'exactement `P` pas. Alors **un mot par tirage suffit** — et l'archive en publie un :

> Le `bonus` est toujours l'un des vingt numéros (§77, `70 560` sur `70 560`), donc une
> **position distinguée** dans le tirage, donc un mot précis du flux. Le flux du bonus est une
> suite ordonnée de `70 560` sorties à pas constant, à `6,32` bits (son numéro) ou `4,32` (son
> rang).

Le §230 y a passé le réseau — `245 760` relèvements, zéro survivant — et le §232 l'a élargi à
dix-huit autres générateurs et huit modules.

**Ce que le relevé filmé apporterait encore**, et qui reste vrai : `6,32` bits par tirage ne
donnent qu'**un** mot, à un décalage inconnu dans le bloc. Un tirage filmé donne **vingt mots
consécutifs**, ce qui (a) fixe le pas au lieu de le balayer, (b) permet d'attaquer les
échantillonneurs à rejet dont le décalage varie, et (c) rend l'attaque possible sur les nuits
courtes. La demande tient — elle est simplement moins urgente qu'écrit ici, et elle porte
désormais sur ce que le bonus ne donne pas plutôt que sur tout.


---

## Addendum (§247) — il y a peut-être beaucoup plus simple qu'une caméra

Ce fichier suppose que l'ordre de sortie doit être **filmé**. Le §247 montre que ce n'est
peut-être pas nécessaire :

> La quatrième ligne de `lab/draws_ordered.csv` a pour source **`jeux.loro.ch`** — le serveur —
> et elle **n'est pas triée**. L'API publie donc un ordre, et le §h223 établit que cet ordre
> n'est pas un artefact de sérialisation (`302` comparaisons discordantes, là où un ordre
> déterministe de la valeur en donnerait `0`).

### Les deux questions à trancher, dans cet ordre

**1. Un seul tirage, deux sources.** Filmer un tirage à l'écran *et* récupérer le même
identifiant par l'API, puis comparer les deux ordres. S'ils coïncident, l'ordre publié **est**
l'ordre physique, et tout le reste suit. Aucun des douze relevés n'est doublé : c'est le trou
à combler en premier, et il coûte cinq minutes.

    GET https://jeux.loro.ch/api/dbg/game/lotoexpress/draws/{id}
    -> results[0].primarySelection      (à conserver VERBATIM, sans trier)

**2. L'API sert-elle l'ordre pour l'historique ?** La ligne `1381028` est un tirage récent
récupéré à chaud. Les `70 560` lignes de l'archive sont triées — mais **aucun script de
capture ne figure dans le dépôt**, donc personne ne sait si c'est le serveur ou le script qui
a trié. Une seule requête sur un identifiant ancien répond.

### Ce que ça vaut, si les deux réponses sont oui

    12 relevés ordonnés   ->   70 560
    61,6 bits par tirage  ->   126,4

Le §246 a passé trente générateurs sur douze tirages ordonnés. La même attaque sur
soixante-dix mille multiplie les chances par `5 880`, supprime le pari sur le préfixe sans
rejet — `42 %` des tirages en ont un de longueur douze, soit `29 600` utilisables — et rouvre
les attaques d'alignement que le §7.33 avait fermées faute de mots consécutifs.

**C'est le seul levier du dossier qui multiplie la donnée par cinq mille, et il ne demande ni
caméra ni calcul.**

---

## Addendum (§258) — un relevé de plus, et la voie qui l'a produit

Le levier « ni caméra ni calcul » ci-dessus est **retiré** : le §247 (correction) établit que
chaque endpoint `REST`, dans les trois langues, sert un ensemble **déjà trié**, et qu'aucun
objet de boule ne porte de position. La seule source d'ordre est le flux d'animation
`SignalR` (`POST /api/animation/negotiate`, puis `SendCurrentState`, champ `meta[lang].balls`),
et il est **direct** : un tirage ordonné toutes les cinq minutes, jamais l'historique.

Ce flux a déjà été capté une fois, et la capture est dans le dépôt — pas dans un fichier de
données, dans la prose de `claude/REPRISE_ETAT.md` de la branche
`codex/state-reconstruction-continuation` (PR #3) :

    1382010   22 24 30 41 6 76 73 9 45 36 37 54 39 21 72 15 10 38 64 79   bonus 37   boost 2
    DrawScene a +30,107 s de la cloture (2026-09-04T04:05:00Z), ExtraScene a +146,1 s

C'est la **treizième** ligne de `draws_ordered.csv`, et la seule qui soit le **premier tirage
de sa journée** (créneau `0` sur `204`). Le §258 dit ce qu'elle rend.

**Pour en produire d'autres**, l'outil existe sur cette branche : `claude/research/capture_order.py`
(un tirage, avec validation contre le `REST` du même identifiant) et `capture_campaign.py`
(une série, segmentée aux nuits et aux trous d'identifiant). Il faut une machine qui joigne
`loro.ch` — cet environnement ne le peut pas (`403` au `CONNECT`) — et le §249 donne le
plafond de ce qu'une campagne peut contenir : `204` tirages à pas de `300 s` exactement, mais
`70 560` à identifiant consécutif, la nuit ne cassant jamais la numérotation.
