# A1 — Instruments à embarquer

Ce document ne conclut rien : `lab/README.md` le dit déjà, l'archive de
70 560 tirages est triée et le réseau vers `jeux.loro.ch` est fermé depuis
cet environnement (403 au CONNECT). Tout ce qui suit a été établi en lisant
le code de l'app (`Prophet/`), jamais en observant un payload réel. Chaque
fois qu'une phrase porte sur *ce que l'API fait*, c'est une hypothèse à
vérifier par l'instrument lui-même — marquée comme telle.

Trois questions instrumentées (A, B, C) plus une quatrième trouvée en
lisant le code (D, qui conditionne la validité de C). Pour chacune :
état des lieux avec numéros de ligne, ce qui manque avec le code Swift
exact, les tests avec témoin positif et négatif, le critère de lecture.

Aucun fichier de `Prophet/` ni `ProphetTests/` n'a été modifié — tout le
code ci-dessous est une proposition à appliquer par le propriétaire.
Aucun toolchain Swift n'était disponible ici pour compiler ; le code a été
relu à la main contre le style existant, et les points laissés incertains
sont signalés en fin de document.

---

## A. L'ordre de publication des numéros

### État des lieux

Déjà en place :

- `LoroClient.parseMatrix` (`Prophet/Services/LoroClient.swift:367-380`)
  conserve l'ordre brut du champ `main` de l'API dans `order`, et renvoie
  aussi `numbers = order.sorted()`. Commentaire explicite lignes 373-375 sur
  l'enjeu.
- `Draw.hasDrawOrder` (`Prophet/Models/Types.swift:24-26`) : vrai si
  `order.count == numbers.count && !order.isEmpty && order != numbers` —
  un test *par tirage*.
- `PRNGRecovery.attack` (`Prophet/Services/PRNGRecovery.swift:417-418`)
  utilise `hasDrawOrder` sur les deux derniers tirages pour choisir le mode
  d'attaque (`orderAvailable`), et `AnalyseView.RecoveryCard`
  (`Prophet/Views/AnalyseView.swift:169-176`) affiche ce booléen pour la
  dernière attaque lancée.

Ce qui n'existe nulle part : un **agrégat** sur l'historique observé. Ni
compteur, ni persistance, ni affichage de « sur N tirages vus depuis
l'installation, l'ordre différait du tri X fois ». `hasDrawOrder` n'est
consommé qu'au vol par une attaque ponctuelle sur les deux derniers
tirages — jamais accumulé. C'est exactement la mesure « à faire une fois »
que le README réclame et qui manque.

Remarque utile pour le design de l'instrument, établie en lisant
`LoroClient.parseSlot`/`parseMatrix` (lignes 313-328, 367-380) et
`Schedule.Slot.asDraw()` (`Prophet/Services/Schedule.swift:22-32`) :
`numbers` est *dérivé* de `order` par tri (`numbers = order.sorted()`), et
`Schedule.Slot.isComplete` (numbers.count ≥ 15) doit être vrai avant qu'un
`Draw` existe. Un `Draw` construit par `LoroClient` a donc **toujours**
`order` non vide et de même longueur que `numbers` — la branche « champ
absent » de `hasDrawOrder` ne peut se produire que pour un `Draw`
construit ailleurs (les tests le font, avec `order` par défaut à `[]`,
cf. `syntheticHistory()` dans `OracleTests.swift`). L'instrument doit donc
distinguer ces deux catégories plutôt que les confondre.

### Ce qui manque

**`Prophet/Models/Types.swift`** — deux structures et une fonction pure
(donc testable sans réseau ni `ProphetStore`), à ajouter près de `Draw` :

```swift
// Piste A du labo (lab/README.md) : l'archive est triée par construction,
// donc cette question ne peut être tranchée qu'en direct, tirage après
// tirage. `Draw.hasDrawOrder` sait répondre pour UN tirage ; rien
// n'agrégeait la réponse sur l'historique observé avant ceci.
struct OrderAudit: Codable {
    var drawsSeen: Int = 0        // tirages où `order` était exploitable
    var invalidCount: Int = 0     // tirages sans donnée d'ordre exploitable
    var permutedCount: Int = 0    // parmi drawsSeen, order != numbers triés
    var firstDrawNumber: Int?
    var lastDrawNumber: Int?
    // Preuve tangible, pas seulement un compteur : quelques tirages bruts
    // pour relecture manuelle. Les non-triés sont toujours gardés, même
    // au-delà du plafond, puisqu'ils sont la preuve décisive.
    var samples: [OrderSample] = []

    // Fonction pure : testable sans réseau. Ne recompte jamais un tirage
    // déjà vu (`lastDrawNumber` sert de filigrane), donc un nouveau sondage
    // qui renvoie une fenêtre glissante d'historique ne fausse rien.
    static func absorbing(_ audit: OrderAudit, draws: [Draw], sampleCap: Int = 200) -> OrderAudit {
        var out = audit
        let fresh = draws
            .filter { $0.drawNumber > (out.lastDrawNumber ?? 0) }
            .sorted { $0.drawNumber < $1.drawNumber }
        for draw in fresh {
            let hasOrderField = !draw.order.isEmpty && draw.order.count == draw.numbers.count
            if hasOrderField {
                out.drawsSeen += 1
                let permuted = draw.hasDrawOrder
                if permuted { out.permutedCount += 1 }
                if permuted || out.samples.count < sampleCap {
                    out.samples.append(OrderSample(drawNumber: draw.drawNumber, order: draw.order, permuted: permuted))
                }
            } else {
                out.invalidCount += 1
            }
            out.lastDrawNumber = draw.drawNumber
            if out.firstDrawNumber == nil { out.firstDrawNumber = draw.drawNumber }
        }
        out.samples = Array(out.samples.suffix(sampleCap))
        return out
    }
}

struct OrderSample: Codable, Identifiable {
    var drawNumber: Int
    var order: [Int]
    var permuted: Bool
    var id: Int { drawNumber }
}
```

**`Prophet/Services/ProphetStore.swift`** — propriété, clé, lecture/écriture
(même convention que `publicationLatencies` / `latencyKey`, lignes 23,
61, 320-330), et point de collecte dans `refresh()` :

```swift
// Propriété publiée, à côté de `publicationLatencies` (ligne 23).
@Published var orderAudit = OrderAudit()

// Clé UserDefaults, à côté de `latencyKey` (ligne 61).
private static let orderAuditKey = "prophet.orderaudit.v1"

// Dans init(), à côté de `publicationLatencies = Self.readLatencies()` (ligne 69).
orderAudit = Self.readOrderAudit()

// Lecture/écriture, même forme que readLatencies/writeLatencies (lignes 320-330).
private static func readOrderAudit() -> OrderAudit {
    guard let data = UserDefaults.standard.data(forKey: orderAuditKey) else { return OrderAudit() }
    return (try? JSONDecoder().decode(OrderAudit.self, from: data)) ?? OrderAudit()
}

private static func writeOrderAudit(_ audit: OrderAudit) {
    if let data = try? JSONEncoder().encode(audit) {
        UserDefaults.standard.set(data, forKey: orderAuditKey)
    }
}
```

Point de collecte : dans `refresh()`, juste après l'appel existant à
`recordPublicationLatency(...)` (ligne 122). `live.history` suffit — pas
besoin d'attendre un tirage isolé, la fonction pure ignore ce qui est déjà
vu :

```swift
recordOrderObservations(live: live)

private func recordOrderObservations(live: LivePayload) {
    let updated = OrderAudit.absorbing(orderAudit, draws: live.history)
    guard updated.drawsSeen != orderAudit.drawsSeen || updated.invalidCount != orderAudit.invalidCount else { return }
    orderAudit = updated
    Self.writeOrderAudit(orderAudit)
}
```

**`Prophet/Views/AnalyseView.swift`** — une carte, dans le style de
`PublicationLatencyCard` (lignes 107-136), insérée dans `analyseBody`
avant elle :

```swift
if store.orderAudit.drawsSeen >= 5 {
    OrderAuditCard(audit: store.orderAudit)
}

// Piste A du labo : l'archive triée ne peut pas répondre, seule une
// collecte en direct le peut (lab/README.md, « Ce qui ne peut pas être
// tranché ici »).
struct OrderAuditCard: View {
    var audit: OrderAudit

    private var fraction: Double {
        audit.drawsSeen > 0 ? Double(audit.permutedCount) / Double(audit.drawsSeen) : 0
    }

    var body: some View {
        Card(tint: audit.permutedCount > 0 ? Palette.gold : Palette.teal) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "ORDRE DE PUBLICATION")
                    Text(audit.permutedCount > 0 ? "Ordre réel détecté" : "Toujours reçu trié")
                        .font(Typeface.display(20))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                Image(systemName: audit.permutedCount > 0 ? "list.number" : "arrow.up.arrow.down.circle")
                    .font(.system(size: 18))
                    .foregroundStyle(audit.permutedCount > 0 ? Palette.gold : Palette.muted)
            }
            Text("L'archive de 70 560 tirages est triée par construction : impossible d'y voir si l'API publie l'ordre de sortie des boules. Relevé ici tirage après tirage depuis l'installation — \(audit.drawsSeen) échantillons.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)
            HStack(spacing: 16) {
                StatPill(label: "TIRAGES VUS", value: "\(audit.drawsSeen)")
                StatPill(label: "NON TRIÉS", value: "\(audit.permutedCount)",
                         accent: audit.permutedCount > 0 ? Palette.gold : Palette.fg)
                StatPill(label: "FRACTION", value: audit.drawsSeen > 0 ? String(format: "%.0f %%", fraction * 100) : "—")
            }
            if audit.drawsSeen < 20 {
                Text("Sous 20 échantillons (~100 min) : encore trop tôt pour conclure côté « toujours trié ». Un seul tirage non trié suffirait, lui, à trancher immédiatement.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
            }
        }
    }
}
```

### Tests (`ProphetTests/InstrumentTests.swift`, nouveau fichier)

```swift
import XCTest
@testable import Prophet

final class InstrumentTests: XCTestCase {

    func testOrderAuditDetectsRealPublicationOrder() {
        // Témoin positif : l'API publierait un ordre réellement différent
        // du tri — exactement ce que l'archive triée ne peut pas montrer.
        let nums = Array(1...20)
        let draws = (1...10).map {
            Draw(drawNumber: 50_000 + $0, drawDate: "2026-08-24T12:00:00+02:00",
                 numbers: nums, order: Array(nums.reversed()), boost: nil, bonus: nil)
        }
        let audit = OrderAudit.absorbing(OrderAudit(), draws: draws)
        XCTAssertEqual(audit.drawsSeen, 10)
        XCTAssertEqual(audit.permutedCount, 10)
        XCTAssertEqual(audit.invalidCount, 0)
    }

    func testOrderAuditStaysZeroOnPreSortedDraws() {
        // Témoin négatif : si l'API renvoie des numéros déjà triés (le cas
        // de l'archive), l'instrument ne doit jamais déclarer de
        // permutation — sinon il ne vaut rien pour trancher la question.
        let nums = Array(1...20)
        let draws = (1...10).map {
            Draw(drawNumber: 60_000 + $0, drawDate: "2026-08-24T12:00:00+02:00",
                 numbers: nums, order: nums, boost: nil, bonus: nil)
        }
        let audit = OrderAudit.absorbing(OrderAudit(), draws: draws)
        XCTAssertEqual(audit.drawsSeen, 10)
        XCTAssertEqual(audit.permutedCount, 0)
    }

    func testOrderAuditFlagsDrawsWithoutOrderDataSeparately() {
        // Les Draw construits sans `order` (comme syntheticHistory() dans
        // OracleTests.swift) ne doivent pas être comptés comme « triés » —
        // c'est une catégorie différente : la donnée manque, elle n'est
        // pas informative.
        let draws = (1...5).map {
            Draw(drawNumber: 70_000 + $0, drawDate: "2026-08-24T12:00:00+02:00",
                 numbers: Array(1...20), boost: nil, bonus: nil)
        }
        let audit = OrderAudit.absorbing(OrderAudit(), draws: draws)
        XCTAssertEqual(audit.drawsSeen, 0)
        XCTAssertEqual(audit.invalidCount, 5)
    }

    func testOrderAuditNeverRecountsAnAlreadySeenDraw() {
        let nums = Array(1...20)
        let draws = (1...5).map {
            Draw(drawNumber: 80_000 + $0, drawDate: "2026-08-24T12:00:00+02:00",
                 numbers: nums, order: Array(nums.reversed()), boost: nil, bonus: nil)
        }
        let once = OrderAudit.absorbing(OrderAudit(), draws: draws)
        // Un nouveau sondage renvoie la même fenêtre d'historique glissante :
        // rien ne doit être recompté.
        let twice = OrderAudit.absorbing(once, draws: draws)
        XCTAssertEqual(twice.drawsSeen, once.drawsSeen)
        XCTAssertEqual(twice.permutedCount, once.permutedCount)
    }
}
```

### Critère de lecture

Le test est **asymétrique**, ce qui change la taille d'échantillon requise
selon le sens de la conclusion :

- **Un seul tirage avec `order != order.sorted()` est décisif.** Si le
  champ était en réalité toujours trié avant transmission, cette
  observation serait *impossible*, pas seulement improbable — ce n'est
  pas un test statistique, c'est une contradiction logique directe. Dès
  `permutedCount ≥ 1`, l'ordre de sortie est réel : la piste PRNGRecovery
  côté « ordre disponible » (déjà codée, `PRNGRecovery.swift:417-419`)
  s'applique à l'historique entier, pas seulement aux deux derniers
  tirages.
- **Conclure « toujours trié » demande plus de prudence**, parce qu'une
  coïncidence (un ordre réel qui retomberait pile trié) a une probabilité
  de 1/20! par tirage — donc en pratique aucune incertitude statistique,
  mais un risque d'*artefact d'implémentation* (un endpoint qui trie côté
  serveur alors qu'un autre non, une regression de parsing côté app).
  Seuil retenu : **`drawsSeen ≥ 20`** (~100 minutes à 5 min/tirage,
  `Schedule.interval`), et vérifier dans `orderAudit.samples` que les
  tirages proviennent bien de plusieurs chemins d'ingestion (`gameSlot`,
  `probe`, `openTask`/`publishedTask` — tous fusionnés dans `live.history`
  par `LoroClient.ensureRange`, donc déjà mélangés). Si `permutedCount`
  reste à 0 à ce seuil, conclure que ce endpoint ne publie pas l'ordre de
  sortie, et fermer cette piste au même titre que les quatorze de l'audit.

---

## B. Le champ `boost` des tirages ouverts

### État des lieux

Rien n'existe. `fetchOpen()` (`LoroClient.swift:237-240`) interroge
`?status=OPEN&size=8`, et `parseSlot`/`parseMatrix` (lignes 313-328,
367-380) extraient `boost` **de la même façon quel que soit le statut** du
tirage — rien ne distingue dans le code un tirage encore ouvert d'un
tirage déjà publié. `Schedule.Slot.boost` (`Schedule.swift:16`) porte
cette valeur pour tous les statuts.

Seul affichage existant de `boost` : `LiveView.swift:185-186` et
`HistoryView.swift:447-448`, tous deux sur des tirages **déjà résultés**
(`last`/`Draw`), jamais sur le tirage à venir. `LivePayload` ne porte
d'ailleurs aucune information sur le tirage OPEN au-delà de
`nextDrawNumber`/`nextDrawAt`/`wagerEndAt` — il n'y a littéralement nulle
part où loger la valeur même si on voulait l'inspecter au débogueur.

`lab/RAPPORT.md` §4 souligne pourquoi c'est la question la plus
importante du lot : *« s'il était publié avant la clôture des mises, ne
jouer que les tirages à boost = 10 vaudrait +150 % à +360 % par franc »* —
et conclut que l'a priori est négatif mais que « cela mérite un instrument
plutôt qu'une supposition ». C'est très exactement ce paragraphe qui
manque de code.

Hypothèse non vérifiée (à ne pas confondre avec un fait) : je suppose
seulement que le endpoint `?status=OPEN` renvoie un JSON qui *peut*
contenir un champ `boost` nul ou absent ; je n'ai vu aucun payload réel et
je ne sais pas dans quel sens (toujours nul avant tirage, toujours
renseigné, ou intermittent) — c'est exactement pour ça que l'instrument
existe.

### Ce qui manque

**`Prophet/Services/Schedule.swift`** — porter le boost du tirage OPEN visé
jusqu'à `Clock` :

```swift
struct Clock {
    var last: Draw?
    var nextDrawAt: Date?
    var nextDrawNumber: Int?
    var wagerEndAt: Date?
    var hole: Bool
    var pendingDrawNumber: Int?
    var phase: String?
    // Boost du tirage encore OPEN visé par nextDrawNumber, tel que reçu —
    // question B de lab/experiments/a1_instruments.md.
    var nextBoost: Int?
}
```

Et dans `resolve()`, au `return Clock(...)` (lignes 107-115), ajouter
`nextBoost: playSlot?.boost` à la liste des arguments.

**`Prophet/Models/Types.swift`** — porter la même valeur jusqu'à
`LivePayload`, et les structures d'audit :

```swift
struct LivePayload {
    var status: String
    var nextDrawAt: Date?
    var nextDrawNumber: Int?
    var wagerEndAt: Date?
    var hole: Bool = false
    var pendingDrawNumber: Int?
    var last: Draw?
    var jackpots: [Jackpot]
    var today: [Draw]
    var history: [Draw]
    var fetchedAt: Date
    var source: String
    var clockOffset: TimeInterval = 0
    // Boost déjà visible sur le tirage OPEN visé, avant tout résultat.
    // Question distincte de PublicationLatency : pas « quand », mais
    // « quoi » est exposé avant clôture (cf. lab/RAPPORT.md §4).
    var nextBoost: Int? = nil
}

// Un instantané par tirage : la valeur vue pendant qu'il était encore
// OPEN, puis la valeur définitive une fois publiée, pour comparaison.
struct OpenBoostObservation: Codable, Identifiable {
    var drawNumber: Int
    var boostAtOpen: Int?
    var secondsBeforeClose: Double?
    var boostAtResult: Int?
    var id: Int { drawNumber }
    // nil tant que les deux valeurs ne sont pas connues — pas un booléen
    // par défaut à false, pour ne jamais confondre « pas encore comparable »
    // et « comparé et différent ».
    var consistent: Bool? {
        guard let boostAtOpen, let boostAtResult else { return nil }
        return boostAtOpen == boostAtResult
    }
}

enum OpenBoostAudit {
    // Ajoute l'instantané pré-tirage, une seule fois par tirage : la
    // première valeur vue est gelée (si le champ apparaît puis change
    // avant clôture, c'est `recordResult` + `consistent` qui le montrera).
    static func recordOpen(_ list: [OpenBoostObservation], drawNumber: Int, boost: Int?, secondsBeforeClose: Double?) -> [OpenBoostObservation] {
        guard !list.contains(where: { $0.drawNumber == drawNumber }) else { return list }
        return list + [OpenBoostObservation(drawNumber: drawNumber, boostAtOpen: boost, secondsBeforeClose: secondsBeforeClose, boostAtResult: nil)]
    }

    // Complète avec la valeur définitive une fois le tirage publié.
    static func recordResult(_ list: [OpenBoostObservation], drawNumber: Int, boost: Int?) -> [OpenBoostObservation] {
        guard let idx = list.firstIndex(where: { $0.drawNumber == drawNumber && $0.boostAtResult == nil }) else { return list }
        var out = list
        out[idx].boostAtResult = boost
        return out
    }
}
```

**`Prophet/Services/LoroClient.swift`** — propager `clock.nextBoost` aux
deux endroits où `LivePayload(...)` est construit (lignes 76-90 et
166-180) : ajouter `nextBoost: clock.nextBoost,` dans les deux appels.

**`Prophet/Services/ProphetStore.swift`** — glue, dans le style de
`rememberTickets` :

```swift
@Published var openBoostAudit: [OpenBoostObservation] = []
private static let openBoostKey = "prophet.openboost.v1"

// init() : openBoostAudit = Self.readOpenBoostAudit()

private static func readOpenBoostAudit() -> [OpenBoostObservation] {
    guard let data = UserDefaults.standard.data(forKey: openBoostKey) else { return [] }
    return (try? JSONDecoder().decode([OpenBoostObservation].self, from: data)) ?? []
}

private static func writeOpenBoostAudit(_ list: [OpenBoostObservation]) {
    let clipped = Array(list.suffix(500))
    if let data = try? JSONEncoder().encode(clipped) {
        UserDefaults.standard.set(data, forKey: openBoostKey)
    }
}

// Appelé depuis refresh(), à côté de recordPublicationLatency/recordOrderObservations.
private func recordOpenBoostObservation(live: LivePayload) {
    if let next = live.nextDrawNumber {
        let serverNow = Date().addingTimeInterval(live.clockOffset)
        let secondsBeforeClose = live.wagerEndAt.map { $0.timeIntervalSince(serverNow) }
        openBoostAudit = OpenBoostAudit.recordOpen(openBoostAudit, drawNumber: next, boost: live.nextBoost, secondsBeforeClose: secondsBeforeClose)
    }
    if let last = live.last {
        openBoostAudit = OpenBoostAudit.recordResult(openBoostAudit, drawNumber: last.drawNumber, boost: last.boost)
    }
    Self.writeOpenBoostAudit(openBoostAudit)
}
```

**`Prophet/Views/AnalyseView.swift`** :

```swift
if store.openBoostAudit.count >= 5 {
    OpenBoostAvailabilityCard(audit: store.openBoostAudit)
}

// Voir lab/RAPPORT.md §4 : le seul endroit du dossier où une réponse
// positive changerait le SIGNE de l'espérance, pas seulement son ampleur.
struct OpenBoostAvailabilityCard: View {
    var audit: [OpenBoostObservation]

    private var withBoostAtOpen: Int { audit.filter { $0.boostAtOpen != nil }.count }
    private var matched: [OpenBoostObservation] { audit.filter { $0.consistent != nil } }
    private var consistentCount: Int { matched.filter { $0.consistent == true }.count }

    var body: some View {
        Card(tint: withBoostAtOpen > 0 ? Palette.live : Palette.teal) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "BOOST AVANT CLÔTURE")
                    Text(withBoostAtOpen > 0 ? "Renseigné avant le tirage" : "Absent avant le tirage")
                        .font(Typeface.display(20))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                Image(systemName: withBoostAtOpen > 0 ? "exclamationmark.triangle.fill" : "checkmark.shield.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(withBoostAtOpen > 0 ? Palette.live : Palette.gain)
            }
            Text("Le endpoint ?status=OPEN expose-t-il déjà le multiplicateur avant la fermeture des mises ? \(audit.count) tirages ouverts observés.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)
            HStack(spacing: 16) {
                StatPill(label: "OUVERTS VUS", value: "\(audit.count)")
                StatPill(label: "AVEC BOOST", value: "\(withBoostAtOpen)",
                         accent: withBoostAtOpen > 0 ? Palette.live : Palette.fg)
                StatPill(label: "COHÉRENT", value: matched.isEmpty ? "—" : "\(consistentCount)/\(matched.count)")
            }
        }
    }
}
```

### Tests

```swift
func testOpenBoostAuditCatchesBoostPresentBeforeResult() {
    // Témoin positif : le champ existe déjà à l'ouverture des mises, et
    // vaut la même chose que le résultat final.
    var list = OpenBoostAudit.recordOpen([], drawNumber: 1, boost: 3, secondsBeforeClose: 12)
    list = OpenBoostAudit.recordResult(list, drawNumber: 1, boost: 3)
    let obs = list.first!
    XCTAssertEqual(obs.boostAtOpen, 3)
    XCTAssertEqual(obs.boostAtResult, 3)
    XCTAssertEqual(obs.consistent, true)
}

func testOpenBoostAuditCatchesBoostAbsentBeforeResult() {
    // Témoin négatif : si le champ n'apparaît qu'après le tirage,
    // l'instrument doit le montrer sans jamais inventer une valeur.
    var list = OpenBoostAudit.recordOpen([], drawNumber: 2, boost: nil, secondsBeforeClose: 12)
    list = OpenBoostAudit.recordResult(list, drawNumber: 2, boost: 4)
    let obs = list.first!
    XCTAssertNil(obs.boostAtOpen)
    XCTAssertEqual(obs.boostAtResult, 4)
    XCTAssertNil(obs.consistent, "pas comparable : rien à comparer côté OPEN")
}

func testOpenBoostAuditFreezesFirstOpenSighting() {
    // Deux sondages du même tirage encore ouvert ne doivent pas se
    // remplacer l'un l'autre : on garde la première valeur vue.
    var list = OpenBoostAudit.recordOpen([], drawNumber: 3, boost: 2, secondsBeforeClose: 30)
    list = OpenBoostAudit.recordOpen(list, drawNumber: 3, boost: 5, secondsBeforeClose: 5)
    XCTAssertEqual(list.count, 1)
    XCTAssertEqual(list.first?.boostAtOpen, 2)
}

func testOpenBoostAuditFlagsInconsistentValue() {
    // Témoin positif d'un cas différent, tout aussi intéressant : le champ
    // existe avant clôture mais change — donc pas fiable tel quel.
    var list = OpenBoostAudit.recordOpen([], drawNumber: 4, boost: 2, secondsBeforeClose: 10)
    list = OpenBoostAudit.recordResult(list, drawNumber: 4, boost: 5)
    XCTAssertEqual(list.first?.consistent, false)
}
```

### Critère de lecture

Question de **disponibilité de donnée**, pas de force statistique : il n'y
a pas de bruit à moyenner, un champ est soit renseigné soit non.

- **Un seul `boostAtOpen != nil` est décisif dans le sens positif** : le
  champ est exposé avant clôture. Passer alors immédiatement à la
  question suivante, la seule qui compte vraiment pour l'app :
  `consistentCount == matched.count` ? Si oui sur au moins **5 paires
  comparées** (`matched.count ≥ 5`), le multiplicateur est déterminé
  avant la fermeture des mises et peut être affiché à l'utilisateur comme
  fiable — c'est le scénario « +150 % à +360 % » de `lab/RAPPORT.md` §4
  qui devient actionnable. Si `consistentCount < matched.count`, le champ
  existe mais n'est pas définitif : ne pas l'afficher comme un fait avant
  résultat.
- **Conclure « jamais renseigné avant tirage »** demande, comme pour A,
  de couvrir suffisamment de tirages pour exclure un artefact de fenêtre
  d'observation plutôt qu'un vrai « jamais » : **`audit.count ≥ 20`**
  tirages ouverts effectivement vus (même raison qu'en A — 20 tirages
  couvre ~100 minutes, largement suffisant pour une question binaire sans
  composante de bruit). En dessous, ne rien conclure, seulement continuer
  à observer.

---

## C. La latence de publication — état de l'instrument, et corrections

### État des lieux

`PublicationLatency` existe et tourne déjà (`claude/AUDIT-CLAUDE.md` §16
en documente l'intention). Précisément :

- Struct : `Prophet/Models/Types.swift:182-188`.
- État : `ProphetStore.publicationLatencies` (ligne 23), `LatencyStats`
  et son calcul (lignes 25-43).
- Persistance : `readLatencies`/`writeLatencies` (lignes 320-330), clé
  `prophet.latency.v1`, plafond `suffix(3000)`.
- Collecte : `recordPublicationLatency` (lignes 300-318), appelée depuis
  `refresh()` (ligne 122).
- Affichage : `AnalyseView.PublicationLatencyCard` (lignes ~107-136),
  visible dès `stats.count >= 5` (`AnalyseView.swift:26`).

L'instrument est donc **complet dans son principe** mais j'ai trouvé trois
défauts en relisant `recordPublicationLatency` (lignes 300-318) contre
`Schedule.resolve` (`Schedule.swift:45-116`), qui le rendent incomplet ou
mal lisible en pratique :

**1. Censure silencieuse pendant un « hole ».** La garde ligne 303,
`previous.nextDrawNumber == newLast.drawNumber`, échoue systématiquement
pour tout tirage retardé. Mécanique exacte : quand un tirage `N+1` tarde,
`Schedule.resolve` bascule sur `hole = true` et avance `nextDrawNumber` à
`N+2` ou plus (`Schedule.swift:93-106`, `hole = ... playNumber! >
last!.drawNumber + 1`, ligne 106). Quand le résultat de `N+1` arrive
enfin, `previous.nextDrawNumber` vaut déjà `N+2` — pas `N+1` — donc la
garde échoue et **rien n'est enregistré** pour ce tirage. C'est
exactement la sous-population la plus intéressante (retards de
publication) qui disparaît sans laisser de trace. `testScheduleDetectsHole`
(`OracleTests.swift:211-233`) déjà dans le dépôt reproduit ce scénario
côté `Schedule` — il montre que le cas existe et est testé ailleurs, mais
rien ne relie ce cas à `recordPublicationLatency`.

**2. Aucun dénominateur.** Rien ne compte combien de nouveaux tirages
l'app a vus au total, seulement combien ont produit un échantillon. Sans
ce chiffre, `publicationLatencyStats.count` ne dit pas si l'instrument
capture 95 % des tirages ou 20 % (par exemple à cause du défaut 1) — deux
situations qui ne se lisent pas pareil.

**3. Pas d'incertitude de mesure associée à l'échantillon.** La
conversion `wagerEndAt` → heure appareil (ligne 308) utilise
`previous.clockOffset`, une EMA calée sur l'en-tête HTTP `Date`
(résolution à la seconde + moitié du round-trip,
`LoroClient.swift:349-359`) — donc bruitée de l'ordre de ±0,5 à 1 s. Cette
incertitude n'est stockée nulle part sur l'échantillon. Une latence
observée à −0,3 s ne peut donc pas être distinguée, *a posteriori*, d'un
simple bruit d'horloge — ce qui est justement la question que le critère
de lecture (plus bas) doit trancher, et il lui faut la donnée pour ça.

### Ce qui manque / corrections

**`Prophet/Models/Types.swift`** — un champ optionnel (pour rester
compatible avec les échantillons `prophet.latency.v1` déjà persistés sur
les appareils qui font déjà tourner l'instrument : un champ non-optionnel
casserait leur décodage au premier lancement après mise à jour) :

```swift
struct PublicationLatency: Codable, Identifiable {
    var drawNumber: Int
    var wagerEndAt: Date
    var observedAt: Date
    var latencySeconds: Double
    // Décalage horloge serveur au moment de l'échantillon
    // (LoroClient.clockOffset) : l'incertitude de mesure est de cet
    // ordre. Optionnel pour ne pas casser le décodage des échantillons
    // déjà persistés avant ce champ (cf. lab/experiments/a1_instruments.md §C).
    var clockOffsetAtSample: TimeInterval?
    var id: Int { drawNumber }
}

// Un tirage dont la clôture annoncée change entre deux lectures pendant
// qu'il est encore OPEN invaliderait la mesure de latence ci-dessus, qui
// gèle la première lecture. Question D : ça arrive-t-il ?
struct WagerEndDrift: Codable, Identifiable {
    var drawNumber: Int
    var driftSeconds: Double
    var id: Int { drawNumber }
}

// Remplace la logique de recordPublicationLatency : mémorise la clôture
// de CHAQUE tirage dès qu'elle est connue (pas seulement celle du payload
// immédiatement précédent), donc ne perd plus les tirages retardés.
struct LatencyTracker {
    private(set) var pending: [Int: (wagerEndAt: Date, clockOffset: TimeInterval)] = [:]
    private(set) var wagerEndDrifts: [WagerEndDrift] = []

    mutating func noteOpen(drawNumber: Int, wagerEndAt: Date?, clockOffset: TimeInterval) {
        guard let wagerEndAt else { return }
        if let existing = pending[drawNumber] {
            // Question D : la clôture annoncée a-t-elle bougé depuis la
            // première lecture ?
            let drift = wagerEndAt.timeIntervalSince(existing.wagerEndAt)
            if abs(drift) > 0.5 {
                wagerEndDrifts.append(WagerEndDrift(drawNumber: drawNumber, driftSeconds: drift))
            }
            return
        }
        pending[drawNumber] = (wagerEndAt, clockOffset)
    }

    // À appeler quand `drawNumber` vient d'apparaître comme résultat.
    mutating func noteResult(drawNumber: Int, now: Date = Date()) -> PublicationLatency? {
        guard let (wagerEndAt, clockOffset) = pending.removeValue(forKey: drawNumber) else { return nil }
        // Borne la table : les entrées plus anciennes qu'une fenêtre de
        // hole plausible ne seront jamais réclamées.
        pending = pending.filter { $0.key > drawNumber - 20 }
        let deviceWagerEndAt = wagerEndAt.addingTimeInterval(-clockOffset)
        return PublicationLatency(
            drawNumber: drawNumber,
            wagerEndAt: deviceWagerEndAt,
            observedAt: now,
            latencySeconds: now.timeIntervalSince(deviceWagerEndAt),
            clockOffsetAtSample: clockOffset
        )
    }
}
```

**`Prophet/Services/ProphetStore.swift`** — remplace
`recordPublicationLatency` (lignes 300-318) et son appel (ligne 122) :

```swift
// Avant (ligne 122 dans refresh()) :
//     recordPublicationLatency(previous: previous, live: live)
// Après — plus besoin de `previous`, tout l'état vit dans latencyTracker :
recordPublicationLatency(live: live)
recordOrderObservations(live: live)      // § A
recordOpenBoostObservation(live: live)   // § B

// `let previous = payload` (ligne 114) devient mort et peut être retiré.

private var latencyTracker = LatencyTracker()
private var lastLatencyDraw = Int.min
@Published var drawsObservedForLatency = 0
@Published var wagerEndDrifts: [WagerEndDrift] = []
private static let drawsObservedKey = "prophet.latency.observed.v1"
private static let wagerEndDriftKey = "prophet.wagerend.drift.v1"

// init() :
// drawsObservedForLatency = UserDefaults.standard.integer(forKey: Self.drawsObservedKey)
// wagerEndDrifts = Self.readWagerEndDrifts()

private func recordPublicationLatency(live: LivePayload) {
    if let next = live.nextDrawNumber {
        latencyTracker.noteOpen(drawNumber: next, wagerEndAt: live.wagerEndAt, clockOffset: live.clockOffset)
        if wagerEndDrifts.count != latencyTracker.wagerEndDrifts.count {
            wagerEndDrifts = latencyTracker.wagerEndDrifts
            Self.writeWagerEndDrifts(wagerEndDrifts)
        }
    }
    guard let last = live.last, last.drawNumber != lastLatencyDraw else { return }
    lastLatencyDraw = last.drawNumber
    drawsObservedForLatency += 1
    UserDefaults.standard.set(drawsObservedForLatency, forKey: Self.drawsObservedKey)
    if let entry = latencyTracker.noteResult(drawNumber: last.drawNumber) {
        publicationLatencies.append(entry)
        Self.writeLatencies(publicationLatencies)
    }
}

private static func readWagerEndDrifts() -> [WagerEndDrift] {
    guard let data = UserDefaults.standard.data(forKey: wagerEndDriftKey) else { return [] }
    return (try? JSONDecoder().decode([WagerEndDrift].self, from: data)) ?? []
}

private static func writeWagerEndDrifts(_ list: [WagerEndDrift]) {
    if let data = try? JSONEncoder().encode(Array(list.suffix(100))) {
        UserDefaults.standard.set(data, forKey: wagerEndDriftKey)
    }
}
```

Et `LatencyStats` (lignes 25-43), pour exposer le plancher de bruit et la
couverture réclamés par les défauts 2 et 3 :

```swift
struct LatencyStats {
    var count: Int
    var mean: Double
    var sd: Double
    var min: Double
    var max: Double
    // |décalage d'horloge| moyen au moment des échantillons : une latence
    // sous ce plancher n'est pas distinguable du bruit de synchronisation.
    var noiseFloor: Double
    // publicationLatencies.count / drawsObservedForLatency.
    var coverage: Double
}

var publicationLatencyStats: LatencyStats? {
    guard !publicationLatencies.isEmpty else { return nil }
    let vals = publicationLatencies.map(\.latencySeconds)
    let n = Double(vals.count)
    let mean = vals.reduce(0, +) / n
    let variance = n > 1 ? vals.reduce(0) { $0 + ($1 - mean) * ($1 - mean) } / (n - 1) : 0
    let offsets = publicationLatencies.compactMap(\.clockOffsetAtSample).map(abs)
    let noiseFloor = offsets.isEmpty ? 0 : offsets.reduce(0, +) / Double(offsets.count)
    let coverage = drawsObservedForLatency > 0 ? Double(publicationLatencies.count) / Double(drawsObservedForLatency) : 0
    return LatencyStats(
        count: vals.count, mean: mean, sd: variance.squareRoot(),
        min: vals.min() ?? 0, max: vals.max() ?? 0,
        noiseFloor: noiseFloor, coverage: coverage
    )
}
```

**`Prophet/Views/AnalyseView.swift`** — ajouter deux `StatPill` à
`PublicationLatencyCard` existante (après le `HStack` des lignes
~128-132) :

```swift
HStack(spacing: 16) {
    StatPill(label: "COUVERTURE", value: String(format: "%.0f %%", stats.coverage * 100))
    StatPill(label: "BRUIT HORLOGE", value: String(format: "±%.1f s", stats.noiseFloor))
}
```

### Tests

```swift
func testLatencyTrackerCatchesADelayedHoleDraw() {
    // Témoin positif du correctif : sous l'ancienne logique
    // (previous.nextDrawNumber == newLast.drawNumber), ce tirage n'aurait
    // jamais été mesuré — c'est le cas de testScheduleDetectsHole.
    var tracker = LatencyTracker()
    let closeAt = Date(timeIntervalSince1970: 1_000_000)
    tracker.noteOpen(drawNumber: 101, wagerEndAt: closeAt, clockOffset: 0)
    // Le tirage 102 ouvre pendant que 101 est en retard (hole) : le
    // tracker mémorise sa clôture aussi, sans perdre celle de 101.
    tracker.noteOpen(drawNumber: 102, wagerEndAt: closeAt.addingTimeInterval(300), clockOffset: 0)
    let entry = tracker.noteResult(drawNumber: 101, now: closeAt.addingTimeInterval(6))
    XCTAssertNotNil(entry)
    XCTAssertEqual(entry?.drawNumber, 101)
    XCTAssertEqual(entry?.latencySeconds ?? -1, 6, accuracy: 0.001)
}

func testLatencyTrackerIgnoresResultWithNoRecordedOpen() {
    // Témoin négatif : un tirage jamais vu OPEN (démarrage de l'app en
    // cours de route) ne doit produire ni entrée fantaisiste ni crash.
    var tracker = LatencyTracker()
    XCTAssertNil(tracker.noteResult(drawNumber: 999))
}

func testLatencyTrackerWouldCatchAnEarlyLeak() {
    // Témoin positif de sensibilité : le réseau ne peut pas être testé ici
    // (403 au CONNECT), mais l'instrument doit démontrablement signaler
    // une latence négative s'il en existait une.
    var tracker = LatencyTracker()
    let closeAt = Date(timeIntervalSince1970: 2_000_000)
    tracker.noteOpen(drawNumber: 55, wagerEndAt: closeAt, clockOffset: 0)
    let entry = tracker.noteResult(drawNumber: 55, now: closeAt.addingTimeInterval(-3))
    XCTAssertNotNil(entry)
    XCTAssertLessThan(entry!.latencySeconds, 0)
}

func testLatencyTrackerAppliesClockOffsetCorrection() {
    var tracker = LatencyTracker()
    // wagerEndAt en temps serveur ; horloge serveur 2 s « en retard » sur
    // l'appareil (clockOffset = serveur − appareil = −2).
    let serverClose = Date(timeIntervalSince1970: 3_000_000)
    tracker.noteOpen(drawNumber: 7, wagerEndAt: serverClose, clockOffset: -2)
    let now = serverClose.addingTimeInterval(3) // 1 s après la clôture réelle en temps appareil
    let entry = tracker.noteResult(drawNumber: 7, now: now)
    XCTAssertEqual(entry?.latencySeconds ?? -1, 1, accuracy: 0.001)
    XCTAssertEqual(entry?.clockOffsetAtSample, -2)
}

func testLatencyTrackerFlagsWagerEndDrift() {
    // Témoin positif de D : la clôture annoncée bouge entre deux lectures.
    var tracker = LatencyTracker()
    let t0 = Date(timeIntervalSince1970: 4_000_000)
    tracker.noteOpen(drawNumber: 9, wagerEndAt: t0, clockOffset: 0)
    tracker.noteOpen(drawNumber: 9, wagerEndAt: t0.addingTimeInterval(5), clockOffset: 0)
    XCTAssertEqual(tracker.wagerEndDrifts.count, 1)
    XCTAssertEqual(tracker.wagerEndDrifts.first?.driftSeconds ?? 0, 5, accuracy: 0.001)
}

func testLatencyTrackerStaysSilentWhenWagerEndIsStable() {
    // Témoin négatif de D : re-sonder la même clôture, à la seconde près,
    // ne doit rien déclencher — sinon le compteur de dérive ne vaut rien.
    var tracker = LatencyTracker()
    let t0 = Date(timeIntervalSince1970: 5_000_000)
    tracker.noteOpen(drawNumber: 10, wagerEndAt: t0, clockOffset: 0)
    tracker.noteOpen(drawNumber: 10, wagerEndAt: t0, clockOffset: 0)
    XCTAssertTrue(tracker.wagerEndDrifts.isEmpty)
}
```

### Critère de lecture

L'audit (`claude/AUDIT-CLAUDE.md` §16) posait déjà le bon signal à
chercher : un `latencySeconds` négatif, au-delà du bruit d'horloge.
Précisé ici en seuils concrets, avec l'asymétrie habituelle de ce
document :

- **Une seule observation `latencySeconds < −2 s`** (marge large sur
  `noiseFloor`, qui devrait rester sous ~1 s d'après la conversion EMA de
  `LoroClient`) est un signal à escalader manuellement, quel que soit `N` —
  ce n'est pas un test à seuil fixe qui attend un lot, une fuite de
  timing n'a pas besoin d'être répétée pour être réelle.
- **Conclure à l'absence de fuite** est une question de puissance contre
  un événement rare (une race condition côté serveur est typiquement
  intermittente). Règle de trois : pour être sûr à ~95 % de voir au moins
  un événement de taux `p` sur `N` tirages sans en voir aucun, il faut
  `N ≈ 3/p`.
  - `N = 300` (~25 h) exclut un taux de fuite ≥ 1 %.
  - `N = 3000` (~10,4 jours) exclut un taux ≥ 0,1 % — **et c'est
    précisément le plafond déjà choisi pour `writeLatencies`**
    (`suffix(3000)`, ligne 326) : la capacité de stockage existante colle
    déjà à ce second seuil, sans qu'il ait été motivé explicitement dans
    le code d'origine.
  - Ces deux `N` supposent `coverage ≈ 1`. Si `stats.coverage` (nouveau
    champ ci-dessus) est significativement sous 1, diviser le `N` requis
    par `coverage` — les tirages non couverts ne réduisent pas le risque
    réel, seulement l'échantillon visible.
- **Préalable de validité (question D)** : si `wagerEndDrifts` n'est pas
  vide, chaque tirage concerné doit être exclu de la lecture du critère
  ci-dessus (la clôture gelée par `noteOpen` n'était pas la bonne),
  jusqu'à ce que la fraction de tirages touchés soit assez faible pour
  être négligée — au jugé, sous 1 % des tirages couverts.

---

## Ce qui n'a pas pu être vérifié

- Aucun compilateur Swift disponible dans cet environnement : tout le
  code ci-dessus a été relu à la main contre le style et les signatures
  déjà présentes dans le dépôt, pas compilé. Points les plus fragiles à
  vérifier en premier après application : l'inférence de type sur les
  `XCTAssertEqual` comparant un `TimeInterval?` à un littéral entier
  (`testLatencyTrackerAppliesClockOffsetCorrection`), et les deux points
  d'appel de `LivePayload(...)` dans `LoroClient.swift` (lignes ~76-90 et
  ~166-180) où `nextBoost: clock.nextBoost` doit être inséré sans casser
  l'ordre des labels existants.
- Comportement réel de l'API `jeux.loro.ch` : entièrement non vérifié
  (403 au CONNECT depuis cet environnement). Toute phrase de ce document
  qui décrit ce que l'API *fait* est une hypothèse que seul l'instrument,
  une fois embarqué, peut trancher — pas une conclusion.
- `OrderAudit`/`OpenBoostObservation`/`WagerEndDrift` sont de nouveaux
  formats persistés (`UserDefaults`) : comme ce sont des clés neuves
  (`prophet.orderaudit.v1`, `prophet.openboost.v1`,
  `prophet.wagerend.drift.v1`, `prophet.latency.observed.v1`), il n'y a
  pas de migration à écrire. Seul `PublicationLatency` touche un format
  déjà déployé, d'où le champ `clockOffsetAtSample` en `Optional` plutôt
  qu'en valeur requise.
