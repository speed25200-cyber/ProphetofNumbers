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
| `F₂`-linéaire (Mersenne Twister, xorshift, LFSR, WELL) | Berlekamp-Massey | **§124** : tout état de moins de `47 040` bits |
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

Enfin le compte global : **`34 618 170`** tests, plus petit `p` = `1,8·10⁻⁴` contre un seuil de
Holm de `1,4·10⁻⁹`. Il manque un facteur **`125 000`**.

## Ce qui reste ouvert, et pourquoi ce n'est pas de la paresse

1. **Les mélangeurs non linéaires.** `splitmix64` multiplie et décale ; PCG fait une rotation
   dont l'amplitude *est* une partie de l'état ; `xoshiro256++` additionne sur `Z` un état qui
   avance sur `GF(2)`. Aucun n'a de réseau, aucun n'a de complexité linéaire bornée. Avec
   `6,32` bits par tirage, il n'y a **aucune prise algébrique** — c'est précisément pour cela
   qu'on en met.
2. **Un congruentiel à constantes non publiées.** Le réseau exige de connaître `a` et `c` ; un
   `a` inconnu sur `2⁶⁴` ne se balaie pas.
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

## Les deux seules choses à faire, et aucune n'est un calcul

**1. Lire le règlement du jeu : le multiplicateur est-il affiché avant la clôture des mises ?**

C'est le seul point du dossier où le **signe** de l'espérance change. Si oui, ne jouer que les
tirages à `boost = 10` — sept par jour — vaut `+150 %` à `+360 %` par franc (§4). L'archive ne
peut pas trancher : elle ne contient pas l'heure de clôture. **Coût : dix minutes de lecture.**

**2. Filmer vingt tirages et noter les numéros dans l'ordre d'apparition.**

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
