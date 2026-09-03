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
