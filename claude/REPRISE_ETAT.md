# Reprise de la recherche — reconstruction d'état

Mise à jour vérifiée le 4 septembre 2026. Ce document distingue les faits
reproduits, les hypothèses et les prochaines expériences. Il corrige les verdicts
trop larges de `RECHERCHE.md` sans effacer l'historique des essais.

## Résultat actuel

Il n'existe encore **aucune prédiction validée sur un tirage LoRo réel**.

La récupération MT19937 est néanmoins reproduite de bout en bout sur données
synthétiques lorsque le modèle est exact : ordre des 20 boules, Fisher-Yates,
mapping et consommation du flux. Avec la graine de démonstration :

| Expérience | Rang | Holdout | Verdict |
|---|---:|---:|---|
| `mtbreak`, 300 tirages | 19 935 / 19 937 | 50/50 pour cette complétion | **inconclusif** : deux dimensions observables restent libres |
| `mtbreak`, 400 tirages | 19 937 / 19 937 | 50/50 | récupération complète |
| `keno_break`, stride 20, 400 tirages | 19 937 / 19 937 | 50/50 | récupération complète |
| `keno_break`, stride 21, 400 tirages | 19 937 / 19 937 | 50/50 | récupération complète |
| `keno_break`, mapping modulo, 400 tirages | 8 800 / 19 937 | — | inconclusif, données insuffisantes |

Le seuil de 300 tirages n'est donc pas un minimum robuste. Sur plusieurs graines,
400 est la cible prudente pour `mulhi`; les mappings modulo demandent environ 1 400
tirages, auxquels il faut ajouter un holdout.

## Source de l'ordre : correction décisive

Les huit CSV et tous les endpoints REST testés publient un **ensemble déjà trié** :

- 70 560 / 70 560 lignes CSV sont strictement croissantes ;
- `/draws/{id}`, la liste `/draws`, `/game` et `/results` renvoient le même tri ;
- aucun objet de boule ne contient de position ;
- `fr-CH`, `de-CH` et `it-CH` ne changent pas ce résultat.

Par conséquent, `primarySelection` ne permet pas de récupérer l'ordre. Le patch
Swift ne doit plus présenter l'ordre du tableau REST comme `drawOrder`.

La source candidate correcte est le flux d'animation public SignalR :

1. `POST /api/animation/negotiate?negotiateVersion=1` ;
2. connexion au WebSocket Azure retourné ;
3. invocation `ConnectLoop("ONLINE")` ;
4. réception de `SendCurrentState` ;
5. lecture de `meta[lang].balls`.

Le frontend LoRo attribue à chaque élément de ce tableau un `originalIndex`, anime
les valeurs dans cet ordre pendant `DrawScene`, puis les trie pour `ReorderScene`.
C'est une preuve structurelle forte, mais une capture pendant les heures actives
reste nécessaire pour vérifier que le tableau contient bien 20 valeurs non triées
et qu'il correspond au set REST.

`research/capture_order.py` implémente maintenant cette capture. Chaque événement
est écrit immédiatement en JSONL avec payload brut, UTC et horloge monotone de
réception, UUID de session, index de frame/message et empreintes SHA-256. Le hash
`hub_message_sha256` porte sur le record SignalR exact, lui-même conservé pour
permettre le recalcul ; `state_canonical_sha256` porte sur l'état JSON canonisé.
Le token de négociation
n'est jamais journalisé et le logger WebSocket est isolé, même si le logger racine
est en mode DEBUG.

Le décodeur conserve les records SignalR coupés entre deux lectures, refuse le JSON
complet invalide et met en quarantaine les divergences entre langues. Il ne compacte
jamais 21 éléments dont un invalide en un faux tirage de 20 valeurs. Seul un
`DrawScene` complet et non trié est une source d'ordre ; `ReorderScene` et
`ResultsScene` ne le sont pas. Le client émet le keepalive Hub type 6 toutes les
15 secondes et impose une deadline absolue au premier état : des pings entrants ne
peuvent donc pas masquer une souscription muette.

```bash
cd claude/research
python3 -m pip install -r requirements.txt
python3 capture_order.py capture capture.jsonl --duration 900 --max-draws 1 \
  --expected-draw-id ID_DU_TIRAGE
python3 capture_order.py inspect capture.jsonl
python3 capture_order.py validate capture.jsonl --draw-id ID_DU_TIRAGE
python3 capture_order.py export capture.jsonl ordered.txt \
  --validation capture.jsonl.validation.json
```

`validate` conserve les octets REST exacts en base64 et leur hash, l'en-tête HTTP
`Date`, les bornes murales et monotones de la requête, le RTT, `wagerEndDate` et chaque contrôle
set/boost/bonus. Le rapport est lié au fichier de capture complet. Lors de l'export,
le corps REST, tous les hashes et le verdict sont recalculés ; une simple étiquette
`VERIFIED_ORDER` fabriquée est refusée. Une corrélation explicite `--draw-id` reste
exportable même si le hub omet l'ID. Les scènes non autoritaires, les séquences
contradictoires et tout trou d'identifiants sont refusés. L'ancien contournement
`--allow-gaps` a été supprimé : concaténer
deux segments ferait croire à tort au solveur qu'ils sont contigus.

Les hashes détectent les modifications accidentelles, mais n'authentifient pas la
machine de capture. Une affirmation temporelle forte demanderait en plus un
horodatage externe signé ; le verdict courant indique donc explicitement la marge
d'horloge/RTT plutôt que de transformer l'heure locale en preuve absolue.

## Corrections du solveur

`keno_break` modélise désormais un stride fixe `W >= 20`. Les contraintes du tirage
`d` portent sur les sorties `d*W ... d*W+19`; les `W-20` sorties suivantes restent
latentes mais sont consommées pendant le replay.

Les verdicts sont tri-valués :

- `RECOVERED` : rang 19 937, replay d'apprentissage exact et holdout exact ;
- `REJECTED` : contradiction exacte ou échec de replay à rang complet ;
- `INCONCLUSIVE` : rang inférieur à 19 937.

Une collision ambiguë de Floyd consomme maintenant une sortie sans inventer une
équation. Cela conserve une condition nécessaire sûre, au prix de davantage de
tirages. Rejection sampling à consommation variable et le vrai `javaNextInt`
restent à implémenter ; ils ne doivent pas être annoncés comme couverts.

Exemples :

```bash
gcc -O3 -std=c11 -Wall -Wextra -Werror -o keno_break keno_break.c
./keno_break demo 400 0xC0FFEE42 41 0 0 20
./keno_break demo 400 0xC0FFEE42 41 0 0 21
./keno_break scanfile ordered.txt 20 64 --state-out recovered-state.txt --predict 1
./keno_break predict recovered-state.txt 10
```

Un checkpoint n'est écrit que pour un modèle **unique**, de rang complet, rejoué
sur l'apprentissage et exact sur le holdout intact. Il contient les 624 mots MT,
`mti`, sampler, mapping, stride et le nombre de tirages consommés. La commande
`predict` part d'une copie, respecte le tail du stride et ne modifie pas le fichier.
L'écriture est atomique et privée (`0600`), et refuse d'écraser l'entrée même via
un hardlink. Son checksum FNV-1a détecte la corruption accidentelle ; ce n'est ni
une signature cryptographique ni une preuve que MT19937 est le générateur réel.

## Quantité d'information

Les valeurs exactes sont :

- ensemble trié : `log2(C(80,20)) = 61,617` bits ;
- ordre ajouté : `log2(20!) = 61,077` bits ;
- tirage ordonné : `log2(80!/60!) = 122,694` bits ;
- contraintes linéaires certaines utilisées par `mulhi` : environ 89,66 bits par
  tirage, et non toute l'entropie du tirage.

L'ensemble trié contient donc beaucoup d'information, mais sous forme d'une grande
disjonction. L'absence d'ordre est une difficulté calculatoire, pas une absence
d'information.

### Mesure directe du canal « première boule dans l'ensemble »

`research/sorted_prefix_audit.py` mesure maintenant ce canal sur les 70 560
ensembles réels, sous l'hypothèse Fisher-Yates avant + `mulhi`. Pour un préfixe de
7 bits de la première sortie, 44,146995 préfixes sur 128 sont permis en moyenne,
soit **1,537557 bit par tirage**, et non les 1,9 bits précédemment annoncés dans
`satbreak.py`. À 8 bits, la moyenne est 76,147860 sur 256, soit 1,749572 bit.

| Préfixe | Information moyenne | Tirages heuristiques pour 19 937 + 64 bits | Rang affine des masques |
|---:|---:|---:|---:|
| 7 bits | 1,537557 bit | 13 009 | 7/7 pour 70 560 / 70 560 |
| 8 bits | 1,749572 bit | 11 432 | 8/8 pour 70 560 / 70 560 |

Le rang affine complet signifie qu'aucune parité certaine ne peut être extraite :
une élimination gaussienne pure perd toute l'information. Un solveur doit conserver
la disjonction complète (XOR-SAT/SMT/BDD). L'encodage Tseitin dense actuel de
`satbreak.py` ne passe pas à MT19937 ; un timeout ne rejetterait donc que la méthode,
jamais le générateur. Reproduction :

```bash
python3 sorted_prefix_audit.py
```

## Protocole falsifiable

### 1. Valider un tirage actif

Lancer le collecteur avant un tirage et vérifier :

- exactement 20 valeurs uniques dans `balls` ;
- séquence non triée ;
- `sorted(balls) == drawResult.matrix1.main` du même ID ;
- `extra` et `boost` concordent avec le REST ;
- heure de première apparition comparée à `wagerEndDate` avec la latence mesurée.

Si `balls` est absent, trié ou divergent, la piste d'ordre est réfutée.

Préparation du premier essai actif du 4 septembre 2026 : l'endpoint REST annonçait
le tirage ouvert **1382010** avec `wagerEndDate = 2026-09-04T04:05:00Z`
(06:05 Europe/Zurich). Une nouvelle capture nocturne a confirmé la négociation et
`NightModeScene`, sans constituer une validation de l'ordre actif.

### 2. Construire une capture exploitable

- minimum prudent : 500 tirages pour `mulhi` avec réserve ;
- 1 600 à 2 000 pour couvrir aussi `mod` et `shr16` ;
- ordre chronologique strict, IDs et provenance conservés ;
- 50 tirages intacts réservés au holdout ;
- aucun choix de modèle fondé sur le holdout.

À environ 204 tirages actifs par jour, 400 tirages prennent environ 47 heures
murales à cause de l'arrêt nocturne ; 2 000 prennent environ dix jours.

### 3. Tester sans surinterpréter

Balayer explicitement sampler, mapping et stride. Un modèle n'est retenu que s'il
reproduit tout l'apprentissage et le holdout. Un échec n'exclut que la configuration
exactement testée : il ne prouve ni CSPRNG ni RNG matériel.

La validation prospective finale consiste à publier l'empreinte d'une prédiction
avant publication du résultat, puis révéler la prédiction après le tirage.

## Voies encore ouvertes

1. Capture SignalR active et mesure de chronologie — priorité immédiate.
2. Rejection sampling et consommations variables dans le solveur.
3. XOR-SAT/SMT sur les ensembles triés, avec contrôle synthétique et holdout.
4. Sorties non linéaires à état arbitraire : PCG, SplitMix64, xoshiro/xoroshiro.
5. Reconstruction LCG avec récupération réelle de l'état et de l'incrément, pas
   seulement détection heuristique d'un vecteur court.

Les résultats statistiques historiques restent utiles pour écarter des biais
simples. Ils ne prouvent pas l'imprédictibilité d'un PRNG à petit état.
