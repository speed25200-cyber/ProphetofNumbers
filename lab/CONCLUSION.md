# Ce qu'il faut retenir — une page

Le rapport fait vingt-trois mille lignes et deux cent quatre-vingt-cinq expériences. Cette
page-ci dit ce qu'il en sort, pour quelqu'un qui veut décider quoi faire.

## La question, et la réponse

> **Peut-on prédire, même partiellement, les numéros de Loto Express à partir des 70 560
> tirages publiés ?**

**Non.** Et depuis le §227 et le §235, ce n'est plus « je n'ai pas trouvé » : la quantité
cherchée a été **mesurée**.

    entropie d'un tirage                       61,616545 bits   (= log₂ C(80,20))
    information extraite par le meilleur
    modèle du dossier, hors échantillon        −0,000181 bit    (négative)
    la même chose sous SRS pur                 −0,000236 ± 0,000163

Le modèle prédit **moins bien** que de ne rien savoir, hors échantillon — exactement comme il
le fait sur des données dont on sait qu'il n'y a rien.

## Ce qui a été fermé, et par quel outil

Un générateur est linéaire de **trois** façons — trois mondes disjoints, trois outils sans
rapport. Le troisième a été trouvé en relisant ma propre carte : ni Berlekamp-Massey ni le
réseau ne voient un Fibonacci retardé.

| famille | outil | ce qui la ferme |
|---|---|---|
| `F₂`-linéaire (Mersenne Twister, xorshift, LFSR, WELL) | complexité linéaire conjointe | **§124** : tout état de moins de `47 040` bits — **à condition que les sorties observées soient des fonctionnelles linéaires de l'état**, ce que la carte de rang `⌊u·20⌋` n'est pas (voir la précision du §124) |
| `MT19937` **derrière la carte de rang** — le cas que la ligne ci-dessus ne couvre pas | élimination `GF(2)`, `19 937` inconnues | **§254** : les 22 pas de bloc `20`–`41` rendent tous un système **incompatible**, sur les données déjà publiées et sans capture |
| `Z/2^W`-linéaire (tous les congruentiels) | réseau euclidien | **§230** + **§232** : `30` jeux de constantes, **neuf** modules (`2¹⁶+1` à `2⁶⁴`), `614 400` relèvements, plus `1 024` cribles **exhaustifs** |
| **coefficients unités** — Fibonacci retardé (`System.Random` .NET `21`/`55`, Go `273`/`607`, `ran3`) | concentration circulaire, **sans aucun paramètre** | **§242** : `1 537 600` relations, lags jusqu'à `620`, deux canaux. Les témoins plantés sont retrouvés *à leurs lags exacts* |
| mélangeur non linéaire (PCG, splitmix64, xoshiro, CSPRNG, matériel) | *aucun outil connu* | **rien** |

Et trois **formes** de défaut, fermées sans viser aucune famille :

| forme | section | portée |
|---|---|---|
| la suite reboucle | **§228** | tous les `35 280` retards d'un coup |
| l'espace d'états est petit | **§229** | `2 489 321 520` paires, **zéro doublon** → vivier `> 2³¹` |
| une parité est constante | **§231** | `2¹²⁸¹` sous-ensembles sur seize tirages |
| « chaud reste chaud » | **§239** | `24` statistiques, nulle **calculée** et non simulée, `70 000` tirages |
| les stratégies du joueur (chauds, froids, « en retard », récents, liés au tirage précédent) | **§240** | `21` statistiques, même nulle exacte, plus une grille fixe de contrôle |

Et le seul fil qui ait jamais répliqué — l'énergie à trois termes au triplet `(3,1,1)`,
`z = +3,267` — a été chassé trois fois sur cible fixe et clos au **§245** : `6/8` signes
positifs sur huit blocs disjoints (`p = 0,14`), et un excès relatif de `1,26·10⁻⁴` qui vit
entièrement à l'intérieur de la borne d'information du §235. Y trancher sur des tirages neufs
demanderait `59 498` tirages, soit **dix mois de jeu**.

Enfin le compte global : plus de **`36,1` millions** de tests, plus petit `p` = `1,8·10⁻⁴` —
et encore, celui-là (`§h114`, l'angle de la roue du multiplicateur) est un résultat de
**fermeture**, pas une piste : il dit que la roue ne publie *rien*. Le seuil de Holm est à
`1,4·10⁻⁹`. Il manque un facteur **`125 000`**.

## Le relevé ordonné : ce qui a changé, et ce que ça coûte vraiment

Deux corrections tardives touchent la seule voie qui restait, et elles vont en sens contraire.

**Ce qui se ferme.** J'ai écrit au §247 que l'archive se re-téléchargerait *ordonnée* par une
simple boucle `HTTP`, et j'en tirais un facteur `5 880`. C'est faux : chaque endpoint `REST`,
dans les trois langues, sert un ensemble **déjà trié**, et aucun objet de boule ne porte de
position. La seule source d'ordre est le flux d'animation `SignalR` — et il est **direct**. Il
n'y a pas de levier à `5 880` ; il y a un **débit**, d'un tirage ordonné toutes les cinq
minutes.

**Ce qui se ferme aussi, et personne ne l'avait chiffré.** Le plan de capture demande `450`
tirages consécutifs à pas fixe (`~1 400` pour les mappings modulo) et refuse — à raison — de
concaténer deux segments séparés par la nuit. Or les `70 560` horodatages du dossier donnent
le plafond sans qu'il faille capturer quoi que ce soit :

    la plus longue plage a id consecutif et pas de 300 s exactement : 204 tirages (17 h)
    plages de >= 300 : 0        plages de >= 450 : 0        plages de >= 1400 : 0

**`450` demande `2,21` fois le plus long segment *temporellement* contigu.**

**Mais « contigu » a deux sens, et le plan a pris le plus contraignant sans le dire.** Un pas
de bloc fixe `W` compte `W` mots **par tirage**, pas par seconde : ce qu'il lui faut, ce sont
des **identifiants consécutifs**. Or l'archive n'en a pas une seule rupture, et les `345`
coupures de nuit sont franchies par la numérotation **sans exception** :

    ruptures d'identifiant sur toute l'archive           :      0
    coupures de nuit ou l'identifiant s'incremente de 1  : 345 / 345
    la plus longue plage a IDENTIFIANT consecutif        : 70 560

Le `204` est donc le plafond de la **règle**, pas de la **donnée**. Si le générateur avance par
tirage, `450` s'obtient en `2,2` jours de capture ; s'il avance par horloge, la nuit consomme
`85·P` mots — un décalage **connu**, puisque les `345` coupures sont toutes un nombre entier
de créneaux. Dans les deux cas c'est une hypothèse de plus à balayer, pas un mur.

**Ce qui reste ouvert.** Le coût, lui, reste asymétrique, et c'est tout l'intérêt :

| famille | état | ce qu'il faut | ce que ça coûte |
|---|---|---|---|
| `MT19937` | `19 937` bits | `≈ 400` tirages | `2,2` jours de capture, deux nuits comprises |
| congruentiels `m ≤ 2³²` | `≤ 32` bits | **un seul** tirage ordonné (`126` bits) | cinq minutes |
| congruentiels `m ≤ 2⁶⁴` | `64` bits | `≈ 11` numéros ordonnés | cinq minutes |

Le §248 tire la conséquence : un crible qui tranche sur **un tirage isolé**, par énumération
complète et en simulant le rejet dès le filtre, ferme la moitié `m ≤ 2³²` de la famille
congruentielle *sans aucune heuristique* — là où le §246 la fermait par un réseau qui suppose
un préfixe sans rejet, hypothèse fausse dans `17` à `87 %` des tirages selon le module.

## Ce qui reste ouvert, et pourquoi ce n'est pas de la paresse

1. **Les mélangeurs non linéaires.** `splitmix64` multiplie et décale ; PCG fait une rotation
   dont l'amplitude *est* une partie de l'état ; `xoshiro256++` additionne sur `Z` un état qui
   avance sur `GF(2)`. Aucun n'a de réseau, aucun n'a de complexité linéaire bornée. Avec
   `6,32` bits par tirage, il n'y a **aucune prise algébrique** — c'est précisément pour cela
   qu'on en met.
2. **Un congruentiel à constantes non publiées** — et c'est la seule des trois qui ait un
   **prix fini**, alors que je l'écrivais jusqu'ici comme un mur. Les §250 et §251 ont fermé
   toute la famille **à constantes publiées**, par énumération complète en dessous de `2³²` et
   par énumération exacte au-dessus. Pour les constantes inconnues, deux arguments cernent ce
   qui reste, chacun par un bout :

   * **par le bas**, l'argument des doublons du §229 ferme tout espace d'états `S ≲ 2²⁸`
     (`P(au moins un doublon) = 1 − 9,2·10⁻⁵`), quelle que soit la famille — mais il s'éteint
     vers `2³¹`, où il ne vaut plus que `0,69` ;
   * **par le haut**, les **différences** `y_i = x_{i+1} − x_i` vérifient `y_{i+1} = a·y_i` :
     l'incrément **s'élimine**, et il ne reste qu'un seul inconnu. Sur `2³²`, ce n'est plus
     `2⁶⁴` couples mais `2³⁰` multiplicateurs.

   Le prix est mesuré, pas supposé : une énumération exacte en dimension `8` retrouve le `y₀`
   planté, et coûte `220 ms` de réduction contre `0,6 ms` de parcours. Six ans sur un cœur en
   `Python` — mais c'est une `LLL` en dimension huit sur des entiers de trente-deux bits, et
   `220 ms` est le prix de `Fraction`, pas celui du problème. **En `C`, `2³⁰` réductions
   tiennent en une dizaine d'heures.**

   > **Et c'est fait, pour trois des quatre modules.** Le §253 balaie `1 879 048 192`
   > multiplicateurs impairs — `2²⁹`, `2³⁰`, `2³¹` — et n'en retient **aucun** : aucun
   > générateur congruentiel de ces modules ne produit le flux du bonus, quel que soit son
   > multiplicateur, son incrément **et** son pas de bloc. C'est la première fois que le
   > dossier ferme une famille sans connaître ses constantes. Reste `2³²`, chiffré à `8,1 h`
   > sur quatre cœurs et **non fait**. Au-dessus, le balayage redevient impossible (`2⁴⁶` à
   > `2⁶²` valeurs de `a`).

   Et une relation **sans paramètre** aurait tout réglé — trois différences consécutives
   vérifient `y_1·y_3 ≡ y_2² (mod m)`, indépendamment de `a` et de `c`. Mais avec des `y_i`
   connus à `m/40` près, l'erreur du produit est de l'ordre de `m²/40`, très supérieure à `m` :
   la relation ne porte aucune information à cette troncature. Ce n'est pas une piste, et il
   vaut mieux le dire que de la laisser croire.
3. **Un générateur matériel.** L'hypothèse la plus probable pour un opérateur régulé, et
   aucune quantité de données ne la distingue d'un bon PRNG.

## Le chiffre qui tranche : rentabilité contre détection

Le barème est relevé (`Prophet/Models/PayTable.swift`, §56), donc la question peut se poser
dans l'autre sens : **quelle marge faudrait-il pour que le jeu devienne rentable ?**

La loi exacte d'un biais qui garde vingt numéros tirés est la **hypergéométrique non centrale
de Fisher** — dix numéros joués à la cote `w`, soixante-dix à la cote `1`, conditionné sur
vingt sorties. Elle se calcule sans simulation :

| | marge des dix joués | justes sur une grille de dix | `E[base]` |
|---|---|---|---|
| **nulle** (`w = 1`) | `0,25000` | `2,5000` | `1,17612` CHF |
| équilibre à `CHF 1,50` | `0,26618` | `2,6618` | `1,50` CHF |
| équilibre à `CHF 2,00` | `0,28446` | `2,8446` | `2,00` CHF |
| équilibre à `CHF 3,00` | `0,30918` | `3,0918` | `3,00` CHF |

Le prix du ticket est borné à `> CHF 1,20` par le barème lui-même. Donc, à la mise la moins
chère, il faudrait **`+0,162` juste** sur une grille de dix pour seulement rentrer dans ses
frais.

> Le seuil de **rentabilité** est à `+0,162` juste. Le seuil de **détection** de l'instrument
> du §236 — trois écarts-types, l'écart-type valant `0,0069` — est à `+0,021` juste. Ce que
> l'archive montre est `+0,013`.
>
> **Il faudrait près de huit fois plus de biais que ce que l'instrument sait voir, et douze
> fois plus que ce qu'il voit.** Ce n'est pas « on cherche encore » : un biais assez gros pour
> rapporter de l'argent serait à vingt-trois écarts-types, et aurait été vu depuis longtemps.

## Le seul endroit où le signe peut changer, et il ne demande aucun biais

Le barème est relevé. La cagnotte `J*` à partir de laquelle une grille de `k` numéros devient
favorable au prix `c` vaut `(c − E[base](k))/P(k/k)`, et le résultat **va à l'inverse de
l'intuition** :

| `k` | `J*` à `CHF 2` | rapporté au gain fixe du rang plein |
|---|---|---|
| **`5`** | **`1 285` CHF** | `3,6 ×` |
| `6` | `6 385` CHF | `6,4 ×` |
| `8` | `191 727` CHF | `19,2 ×` |
| `10` | `7 342 190` CHF | `73,4 ×` |

> **La plus petite grille bascule `5 713` fois plus tôt que la plus grande.** Le rang plein pèse
> `20 %` de l'espérance sur une grille de cinq et `1 %` sur une grille de dix ; une cagnotte agit
> sur ce rang, elle a donc vingt fois plus de levier là où il pèse vingt fois plus.

Si l'on chasse un pari favorable, on le chasse sur la **plus petite** grille, pas sur la plus
grande. C'est du §244, c'est exact, et le bloc `16` du vérificateur le recalcule.

## Les quatre questions qui décident, et aucune n'est un calcul



**1. Lire le règlement du jeu : le multiplicateur est-il affiché avant la clôture des mises ?**

C'est le seul point du dossier où le **signe** de l'espérance change. Si oui, ne jouer que les
tirages à `boost = 10` — sept par jour — vaut `+150 %` à `+360 %` par franc (§4). L'archive ne
peut pas trancher : elle ne contient pas l'heure de clôture. **Coût : dix minutes de lecture.**

**2. Lire le prix exact du ticket, et si le multiplicateur s'applique au barème publié.**

Le barème a été relevé à `BOOST ×1`. Si le multiplicateur multiplie bien ce barème-là, le taux
de retour à `CHF 2` vaudrait `118,3 %` — impossible pour un opérateur régulé, donc quelque
chose ne colle pas, et ce quelque chose vaut `18 %` par franc. La lecture cohérente est que le
multiplicateur ne multiplie pas ce barème (`58,8 %` de retour), mais **cela se vérifie sur un
ticket**, pas dans l'archive. §244.

**3. Récupérer un tirage par l'API sans le trier — et le même tirage filmé.**

C'est le levier le plus lourd du dossier, et le moins cher. `lab/draws_ordered.csv` porte une
ligne de source **`jeux.loro.ch`** qui **n'est pas triée** : l'API publie un ordre, et le §247
établit qu'il n'est pas un artefact (`302` comparaisons discordantes contre `0` attendues pour
tout ordre déterministe). Restent deux questions qu'un seul tirage capté **des deux côtés**
tranche : cet ordre est-il l'ordre physique, et l'API le sert-elle pour l'historique ?

Si oui, l'archive se re-télécharge **ordonnée** — `70 560` tirages à `126,4` bits au lieu de
`61,6`, et `29 600` tirages exploitables au lieu de cinq. **×5 880 sur la donnée, pour une
boucle HTTP.** Protocole : `lab/RELEVE_ORDONNE.md`.

**4. À défaut, filmer vingt tirages et noter les numéros dans l'ordre d'apparition.**

Le `bonus` fournit déjà **un** mot ordonné par tirage (§230). Un tirage filmé en fournit
**vingt consécutifs**, ce qui fixe le pas de bloc au lieu de le balayer et ouvre les
échantillonneurs à rejet. Format et protocole : `lab/RELEVE_ORDONNE.md`. L'attaque tourne
ensuite en moins d'une heure, et son verdict est en entiers exacts — juste ou faux, pas de
zone grise.

## Ce qu'il ne faut pas faire

  * **Ne pas payer un modèle de plus.** Le §236 a porté le plus gros modèle du dossier —
    non linéaire, `90` colonnes, interactions et courbures, plus la structure de paires que
    personne n'avait jamais donnée à un prédicteur. Sa règle pré-enregistrée s'est déclenchée
    à `k = 10` (`z = +1,99`, `p = 0,059`) — et quatre sections ont suivi pour en avoir le cœur
    net. Le **§237** refait la nulle : ses répliques gardaient les colonnes `bonus` et `boost`
    réelles sur des tirages synthétiques, si bien que l'archive et sa nulle n'avaient pas la
    même géométrie de traits ; réparée, la nulle s'élargit, `z` tombe à `+1,80`, la tranche
    entière ne dépasse plus son seuil, et l'excès vit **entièrement dans la première moitié**
    de la tranche de mesure (`+2,31` contre `+0,23`). **INFIRMÉ.** Le **§238** fige la grille :
    celle du modèle retombe sur `2,50018` juste, `z = +0,02`. Le **§239** tue « chaud reste
    chaud » à pleine puissance, sans une seule simulation. Le **§240** fait de même pour les
    sept stratégies qu'un joueur essaie vraiment, contrôle compris.
  * **Ne pas confondre jolies grilles et prédiction.** Sous absence de biais,
    `E[justes] = k/4` **quel que soit** le choix des numéros — c'est un théorème, pas une
    observation. Chauds, froids, retards, essaims, réseaux de neurones : aucun ne déplace
    l'espérance d'un iota. C'est la faute qui produit les applications de loterie mensongères.
  * **Ne pas jouer en espérant un avantage.** Avec le barème relevé (`Prophet/Models/PayTable.swift`,
    §56), le taux de retour borne le prix du ticket à `> CHF 1,20` : le pari est à espérance
    négative hors cagnotte exceptionnelle, et le seuil exact est `J* = (c − E[base])/P(k/k)`.

## Où lire le détail

| | |
|---|---|
| le rapport complet, section par section | `lab/RAPPORT.md` |
| la théorie de la reconstruction d'état | `lab/THEORIE_ETAT.md` |
| le protocole du labo et les deux pistes | `lab/README.md` |
| le relevé ordonné à produire | `lab/RELEVE_ORDONNE.md` |
| tout recalculé depuis les sources | `python3 lab/verifier.py` |
| les 285 lignes de registre | `lab/ledger.jsonl` |
