import Foundation

enum ProphetConst {
    static let poolSize = 80
    static let drawSize = 20
    static let stakes: [Int] = [5, 6, 7, 8, 10]
    static let baseP = Double(drawSize) / Double(poolSize)
}

struct Draw: Identifiable, Hashable, Codable {
    var drawNumber: Int
    var drawDate: String
    var numbers: [Int]
    // Numéros dans l'ordre publié par l'API. S'il diffère de l'ordre trié,
    // c'est l'ordre de sortie des boules — et la suite des sorties du
    // générateur devient observable (cf. PRNGRecovery).
    var order: [Int] = []
    var boost: Int?
    var bonus: Int?

    var id: Int { drawNumber }

    // L'ordre publié porte-t-il de l'information ?
    var hasDrawOrder: Bool {
        order.count == numbers.count && !order.isEmpty && order != numbers
    }
}

struct Jackpot: Identifiable, Hashable {
    var stake: Int
    var amount: Double
    var id: Int { stake }
    // L'API mélange francs et centimes selon les rangs ; au-delà de 10 000 la
    // valeur est en centimes. Normalisation en UN seul endroit, pour que le
    // journal et l'affichage ne puissent pas diverger.
    var francs: Double { amount >= 10_000 ? amount / 100 : amount }
}

// Un tirage dont l'ORDRE DE SORTIE est connu, conservé sur disque.
//
// C'est la donnée la plus rare et la plus précieuse du dossier. Un tirage
// trié porte 61,62 bits ; ordonné, 122,69 — et h14 a montré que cinq tirages
// ordonnés CONSÉCUTIFS referment la classe de générateurs candidats sur trois
// éléments là où cinq tirages épars en laissent dix-sept.
//
// L'app reçoit l'ordre à chaque tirage quand l'API le publie, et le jetait
// à chaque relance : l'historique refetché revient trié. Ce journal le garde,
// et c'est ce qui permet à l'accumulation de tirages CONSÉCUTIFS de se faire
// toute seule, à raison d'un toutes les cinq minutes.
struct OrderedDraw: Codable, Identifiable, Hashable {
    var drawNumber: Int
    var order: [Int]
    var bonus: Int?
    var at: Date
    var id: Int { drawNumber }
    /// Position du bonus dans l'ordre de sortie — la mesure de h19.
    var bonusPosition: Int? {
        guard let bonus, let idx = order.firstIndex(of: bonus) else { return nil }
        return idx + 1
    }
}

// MARK: - La règle du bonus

// Le bonus est-il la boule d'une POSITION FIXE de l'ordre de sortie, ou un
// choix uniforme parmi les vingt ?
//
// h19 (§32) a établi sur les 70 560 tirages archivés que le bonus est
// TOUJOURS l'un des vingt numéros sortis : ce n'est pas un tirage de plus,
// c'est une DÉSIGNATION parmi les vingt. h22 (§36) a ensuite montré que
// l'archive ne peut PAS dire selon quelle règle, et l'a montré par un calcul
// de puissance et non par une intuition :
//
//   • sous une loi d'ordre échangeable — Fisher-Yates, ou un rejet à loi de
//     base uniforme, qui est la même loi — la position du bonus est uniforme
//     parmi les vingt CONDITIONNELLEMENT à l'ensemble tiré. Les deux
//     hypothèses produisent alors exactement la même loi sur (ensemble trié,
//     bonus) : la question n'est pas difficile hors ligne, elle est NON
//     IDENTIFIABLE ;
//   • sous une loi de base biaisée elle redevient identifiable, mais il
//     faudrait un biais tel que le χ² des fréquences marginales — un test
//     déjà passé, et conforme — l'aurait vu des milliers de fois plus tôt.
//
// D'où cet instrument. La mesure ne peut se faire que là où l'ordre de sortie
// existe : dans l'app, qui le reçoit et le conserve (`OrderedDraw`).
//
// LE CRITÈRE EST ASYMÉTRIQUE, et il est écrit comme tel.
//
//   Côté RÈGLE : une seule position discordante la réfute. Il faut donc que
//   les n positions coïncident toutes, et P(cela | uniforme) = 20·20^(−n)
//   passe sous le seuil de Holm du registre entier (1,5·10⁻⁵) à n = 5.
//
//   Côté UNIFORME : c'est une acceptation, et une acceptation exige une borne
//   d'équivalence. Une position discordante tue la règle DÉTERMINISTE en un
//   coup, mais laisse vivante une règle presque déterministe (« la vingtième
//   dans 90 % des cas »), qui vaudrait presque autant. Conclure à
//   l'uniformité, c'est donc rejeter la famille « ∃ j : P(position j) ≥ 1/2 »
//   — le seuil où l'énoncé « le bonus est à la position j » cesse d'être vrai
//   plus souvent que faux, soit le plus faible énoncé qui mérite encore le
//   mot « règle ». Au plus une position peut le vérifier, donc le maximum des
//   comptages est une statistique suffisante et aucune correction de
//   multiplicité n'est due. Le plancher vaut alors 25 tirages ordonnés, et
//   h22 mesure par simulation que sous une uniformité vraie le critère se
//   déclenche à 32 tirages en médiane, 35 au 80ᵉ centile.
enum BonusRuleVerdict: String {
    case undecided      // pas encore assez de tirages ordonnés
    case positionRule   // règle de position établie
    case uniform        // choix uniforme parmi les vingt
}

struct BonusRuleReading {
    var verdict: BonusRuleVerdict
    /// Tirages ordonnés dont la position du bonus est connue.
    var observations: Int
    /// Bonus publié HORS de l'ordre de sortie. Devrait rester à zéro : ce
    /// serait un démenti du fait structurel de §32, pas un détail.
    var outside: Int
    /// Position la plus fréquente, 1…20. Zéro tant qu'il n'y a rien.
    var dominant: Int
    var dominantCount: Int
    /// P(les n positions coïncident | bonus uniforme) = 20^(1−n).
    var pRule: Double
    /// P(Binomiale(n, 1/2) ≤ comptage dominant) — le versant équivalence.
    var pConcentrated: Double
    /// Tirages ordonnés encore manquants AU MIEUX, c'est-à-dire si les
    /// positions à venir tombaient aussi régulièrement que possible. Un
    /// minorant du délai, jamais une prévision.
    var needed: Int
}

enum BonusRule {
    /// Seuil de Holm du registre entier du labo (114 tests consignés).
    static let alpha = 1.5e-5
    /// Borne d'équivalence : au-delà, « le bonus est à la position j » est
    /// vrai plus souvent que faux et mérite le mot « règle ».
    static let concentration = 0.5

    /// Plus petit n tel que 20·20^(−n) ≤ alpha. Calculé, pas choisi.
    static let minimumForRule: Int = {
        let k = Double(ProphetConst.drawSize)
        var n = 1
        while n < 100 && k * pow(1 / k, Double(n)) > alpha { n += 1 }
        return n
    }()

    /// Plus petit n tel que le critère d'uniformité soit ATTEIGNABLE, c'est-
    /// à-dire avec des comptages aussi plats que possible. Calculé, pas choisi.
    static let minimumForUniform: Int = {
        let k = ProphetConst.drawSize
        var n = 1
        while n < 10_000
            && binomialLowerTail((n + k - 1) / k, n, concentration) > alpha { n += 1 }
        return n
    }()

    static func read(_ log: [OrderedDraw]) -> BonusRuleReading {
        var positions: [Int] = []
        var outside = 0
        for d in log where d.bonus != nil {
            if let p = d.bonusPosition { positions.append(p) } else { outside += 1 }
        }
        return read(positions: positions, outside: outside)
    }

    static func read(positions raw: [Int], outside: Int = 0) -> BonusRuleReading {
        let k = ProphetConst.drawSize
        let positions = raw.filter { (1...k).contains($0) }
        let n = positions.count
        var counts = [Int](repeating: 0, count: k)
        for p in positions { counts[p - 1] += 1 }
        let top = counts.enumerated().max(by: { $0.element < $1.element })
        let dominant = n > 0 ? (top?.offset ?? 0) + 1 : 0
        let m = n > 0 ? (top?.element ?? 0) : 0
        let pRule = n > 0 ? pow(Double(k), Double(1 - n)) : 1
        let pConc = n > 0 ? binomialLowerTail(m, n, concentration) : 1

        // La règle : toutes les positions identiques, et assez nombreuses.
        if n >= minimumForRule && m == n {
            return BonusRuleReading(
                verdict: .positionRule, observations: n, outside: outside,
                dominant: dominant, dominantCount: m,
                pRule: pRule, pConcentrated: pConc, needed: 0)
        }
        // L'uniformité : la règle est réfutée ET aucune position ne peut
        // encore prétendre à la moitié des tirages.
        if m < n && pConc <= alpha {
            return BonusRuleReading(
                verdict: .uniform, observations: n, outside: outside,
                dominant: dominant, dominantCount: m,
                pRule: pRule, pConcentrated: pConc, needed: 0)
        }
        return BonusRuleReading(
            verdict: .undecided, observations: n, outside: outside,
            dominant: dominant, dominantCount: m,
            pRule: pRule, pConcentrated: pConc,
            needed: missing(n: n, dominantCount: m))
    }

    /// Ce qu'il manque AU MIEUX pour atteindre un verdict — donc en supposant
    /// les positions à venir aussi régulières que possible. C'est un
    /// minorant : les données réelles fluctuent et repoussent l'échéance.
    static func missing(n: Int, dominantCount m: Int) -> Int {
        let k = ProphetConst.drawSize
        // Tant que toutes les positions coïncident, la règle est vivante et
        // c'est elle qui se conclut le plus tôt.
        if n == 0 || m == n { return max(0, minimumForRule - n) }
        var extra = 0
        while extra < 4000 {
            let total = n + extra
            let best = max(m, (total + k - 1) / k)
            if binomialLowerTail(best, total, concentration) <= alpha { return extra }
            extra += 1
        }
        return 4000
    }

    /// P(Binomiale(n, p) ≤ k), sommée en échelle logarithmique — le
    /// coefficient binomial est mis à jour terme à terme, jamais formé.
    static func binomialLowerTail(_ k: Int, _ n: Int, _ p: Double) -> Double {
        if k < 0 { return 0 }
        if k >= n { return 1 }
        guard n > 0, p > 0, p < 1 else { return 1 }
        var logC = 0.0
        var total = 0.0
        for i in 0...k {
            total += exp(logC + Double(i) * log(p) + Double(n - i) * log1p(-p))
            logC += log(Double(n - i)) - log(Double(i + 1))
        }
        return min(1, total)
    }
}

extension BonusRuleReading {
    /// La ligne unique que lisent la forensique et l'écran d'analyse — une
    /// seule formulation, pour que les deux ne puissent pas diverger.
    var summary: String {
        switch verdict {
        case .positionRule:
            return "position \(dominant) sur les \(observations) tirages ordonnés"
                + " — RÈGLE FIXE (p = 20^−\(max(0, observations - 1)))"
        case .uniform:
            return "uniforme parmi les vingt — dominante \(dominant) :"
                + " \(dominantCount)/\(observations)"
        case .undecided:
            if observations == 0 {
                return outside > 0
                    ? "\(outside) bonus hors de l'ordre publié"
                    : "ordre de sortie non publié"
            }
            return "\(observations) mesuré\(observations > 1 ? "s" : "")"
                + " — encore \(needed) au mieux"
        }
    }

    /// Ce que le verdict veut dire, en une phrase.
    var detail: String {
        switch verdict {
        case .positionRule:
            return "Le bonus marque la position \(dominant) de l'ordre de sortie."
                + " Il porte donc 4,32 bits d'ordre par tirage, sur toute l'archive"
                + " — assez pour ancrer une sortie du générateur à une position connue."
        case .uniform:
            return "Le bonus est un choix uniforme parmi les vingt : il ne porte"
                + " aucune information d'ordre. Mesuré sur \(observations) tirages"
                + " ordonnés, aucune position ne peut plus en concentrer la moitié."
        case .undecided:
            let n = observations
            return "Position du bonus dans l'ordre de sortie : \(n) relevé\(n > 1 ? "s" : "")."
                + " \(BonusRule.minimumForRule) positions identiques établiraient une règle ;"
                + " conclure à l'uniformité en demande \(BonusRule.minimumForUniform) au minimum."
        }
    }
}

// Un relevé de cagnotte, daté par le tirage. C'est la matière première de
// `JackpotLaw` — et, d'après lab/experiments/h15_loi_cagnotte.py, la donnée
// manquante la plus rentable de tout le dossier : elle seule dit à quelle
// FRÉQUENCE le seuil de bascule de l'espérance est franchi.
struct JackpotReading: Codable, Identifiable, Hashable {
    var drawNumber: Int
    var stake: Int
    var francs: Double
    var at: Date
    var id: String { "\(drawNumber).\(stake)" }
}

// Ce qu'une série de relevés permet de dire, et avec quelle incertitude.
struct JackpotLawEstimate: Identifiable {
    var stake: Int
    var readings: Int
    var spanDraws: Int
    var latest: Double
    var threshold: Double
    /// r — accumulation par tirage, médiane des accroissements observés.
    var accrual: Double?
    /// Nombre de chutes observées : autant de fois où la cagnotte est tombée.
    var drops: Int
    /// exp(−seuil/μ) avec μ = r/q. nil tant que r n'est pas mesurable.
    var favourable: Double?
    var favourableLo: Double?
    var favourableHi: Double?
    /// Gain espéré par franc misé en ne jouant QUE au-dessus du seuil.
    /// Vaut μ/S par absence de mémoire (h16), donc s'estime directement par
    /// la moyenne des relevés divisée par le seuil — sans passer par r ni q,
    /// et beaucoup mieux conditionné que `favourable`, qui dépend de μ
    /// exponentiellement là où celui-ci en dépend linéairement.
    var conditionalEdge: Double?
    var edgeLo: Double?
    var edgeHi: Double?
    var id: Int { stake }
}

enum GridKind: String, Codable, CaseIterable, Identifiable {
    case alpha, omega, nexus
    var id: String { rawValue }

    var tone: String {
        switch self {
        case .alpha: return "Momentum"
        case .omega: return "Retour"
        case .nexus: return "Ensemble"
        }
    }

    var label: String {
        switch self {
        case .alpha: return "Alpha"
        case .omega: return "Omega"
        case .nexus: return "Nexus"
        }
    }

    var subtitle: String {
        switch self {
        case .alpha: return "Momentum — têtes Hawkes · EWMA · Markov"
        case .omega: return "Retour — écarts · spectre · pression"
        case .nexus: return "Essaim complet + graphe de paires"
        }
    }
}

struct SuggestedGrid: Identifiable {
    var kind: GridKind
    // 1 = sélection principale, 2 = variante disjointe (couverture doublée).
    var variant: Int = 1
    var label: String
    var subtitle: String
    var numbers: [Int]
    // Espérance de hits. EXACTE et égale à `baseExpected` : sous un tirage
    // sans remise 20/80, elle vaut k/4 quel que soit le contenu de la grille.
    // Elle portait auparavant une estimation issue du posterior de l'essaim,
    // qui surestimait de 18 à 34 % par malédiction du vainqueur — la grille
    // était notée avec l'estimateur qui avait servi à la choisir.
    var expectedHits: Double
    var baseExpected: Double
    // Loi de survie EXACTE : `tail[t]` = P(la grille atteint au moins t hits),
    // pour t de 0 à k. Hypergéométrique(80, 20, k), sans estimation.
    var tail: [Double]
    var basePAllHit: Double
    var id: String { "\(kind.rawValue).\(variant)" }
}

struct StakeGrids: Identifiable {
    var stake: Int
    var grids: [SuggestedGrid]
    var oddsLabel: String
    // P(au moins une des 12 grilles est pleine), EXACTE par inclusion-exclusion
    // sur le paquet réellement produit. C'est la seule quantité que la
    // géométrie déplace tant que les gains ne se partagent pas ; dès qu'un
    // rang est partagé, la géométrie déplace aussi l'ESPÉRANCE (cf. h13).
    var packPAllHit: Double
    // Diagnostic de forme du paquet (lab/experiments/h13_portefeuille.py) :
    // recouvrement maximal et moyen entre deux grilles, plancher atteignable
    // à couverture équilibrée, et seuil neutre ω* = k²/80 au-delà duquel
    // deux grilles deviennent positivement corrélées.
    var overlapMax: Int = 0
    var overlapMean: Double = 0
    var overlapFloor: Double = 0
    var overlapNeutral: Double = 0
    var id: Int { stake }
}

struct MethodScore: Identifiable {
    var id: String
    var name: String
    var blurb: String
    var family: String
    var weight: Double
    var overlap: Double
    var scores: [Double]
}

struct FamilyWeight: Identifiable {
    var name: String
    var weight: Double
    var heads: Int
    var id: String { name }
}

struct SwarmStats {
    var headCount: Int
    var effectiveHeads: Double
    var generation: Int
    var bestHeadName: String
    var bestHeadMean: Double
    var families: [FamilyWeight]
}

struct RankMove: Identifiable {
    var number: Int
    var rank: Int
    var prevRank: Int
    var delta: Int
    var score: Double
    var id: Int { number }
}

struct OracleResult {
    var scores: [Double]
    var ranks: [Int]
    var methods: [MethodScore]
    var stakes: [StakeGrids]
    var movers: [RankMove]
    var regimeLabel: String
    var regimeDetail: String
    var chi2: Double
    var serial: Double
    var confidence: Int
    var sampleSize: Int
    var todayDraws: Int
    // Backtest walk-forward de l'ensemble : hits du top-20 par tirage évalué (0…20).
    var backtest: [Double]
    var backtestMean: Double
    var uniformExpected: Double
    var backtestZ: Double
    // Test séquentiel par pari : e-valeur anytime-valid, ≥ 20 ⇒ alerte à 5 %.
    var eValue: Double
    // Géométrie du tableau officiel : paires adjacentes par tirage.
    var adjacencyMean: Double
    var adjacencyExpected: Double
    var adjacencyZ: Double
    // Anti-rejeu : recouvrement max entre deux tirages de l'historique.
    var duplicateMax: Int
    var duplicateAlert: Bool
    // État courant du champ 1–80.
    var gaps: [Int]
    var freq16: [Double]
    // Écho du bonus : le numéro bonus du dernier tirage, départagé dans la
    // sélection. nil tant qu'aucun tirage absorbé n'a publié de bonus.
    var bonusEcho: Int?
    // Taille APPRISE du départage, en unités relatives : (0,25 − posterior)
    // / 0,25, posterior Beta(1,3) de P(bonus précédent ∈ tirage). Sous un
    // générateur équitable elle s'éteint en 1/√n ; sur l'archive réelle
    // elle converge d'elle-même vers le déficit mesuré par le labo.
    var bonusEchoHat: Double
    // Diagnostics de l'essaim.
    var swarm: SwarmStats
}

struct LivePayload {
    var status: String
    var nextDrawAt: Date?
    // Le vrai prochain tirage ouvert (le endpoint jeu retarde d'un tirage).
    var nextDrawNumber: Int?
    var wagerEndAt: Date?
    // « Hole » : un résultat attendu entre le dernier connu et le prochain
    // ouvert n'est pas encore publié — polling agressif jusqu'à résolution.
    var hole: Bool = false
    var pendingDrawNumber: Int?
    var last: Draw?
    var jackpots: [Jackpot]
    var today: [Draw]
    var history: [Draw]
    var fetchedAt: Date
    var source: String
    // Boost déjà visible sur le tirage OPEN visé, avant tout résultat.
    // Question distincte de la latence : pas « quand », mais « quoi » est
    // exposé avant clôture (cf. lab/RAPPORT.md §4 et a1_instruments.md B).
    var nextBoost: Int? = nil
    // Horloge serveur Loro − horloge appareil : à ajouter à l'heure locale
    // pour se caler sur le flux réel.
    var clockOffset: TimeInterval = 0
}

// Question distincte du générateur lui-même, et que l'archive historique
// ne peut pas trancher (wagerEndDate n'y est jamais consigné) : le
// résultat devient-il lisible avant la fermeture officielle des mises ?
// Une fuite de publication serait un défaut d'infrastructure, pas de
// cryptographie — donc invisible à toute analyse rétrospective du flux
// de numéros. Seule une collecte en direct, tirage après tirage, peut
// répondre. `latencySeconds` négatif serait le signal à chercher.
// Un instantané par tirage : la valeur de boost vue pendant qu'il était
// encore OPEN, puis la valeur définitive une fois publiée. C'est le seul
// point du dossier où une réponse positive changerait le SIGNE de
// l'espérance (lab/RAPPORT.md §4) — d'où un instrument, pas une supposition.
struct OpenBoostObservation: Codable, Identifiable {
    var drawNumber: Int
    var boostAtOpen: Int?
    var secondsBeforeClose: Double?
    var boostAtResult: Int?
    var id: Int { drawNumber }
    // nil tant que les deux valeurs ne sont pas connues — jamais un false
    // par défaut, pour ne pas confondre « pas encore comparable » et
    // « comparé et différent ».
    var consistent: Bool? {
        guard let boostAtOpen, let boostAtResult else { return nil }
        return boostAtOpen == boostAtResult
    }
}

enum OpenBoostAudit {
    // La première valeur vue est gelée : si le champ apparaît puis change
    // avant clôture, c'est `recordResult` + `consistent` qui le montrera.
    static func recordOpen(_ list: [OpenBoostObservation], drawNumber: Int,
                           boost: Int?, secondsBeforeClose: Double?) -> [OpenBoostObservation] {
        guard !list.contains(where: { $0.drawNumber == drawNumber }) else { return list }
        return list + [OpenBoostObservation(drawNumber: drawNumber, boostAtOpen: boost,
                                            secondsBeforeClose: secondsBeforeClose,
                                            boostAtResult: nil)]
    }

    // Complète avec la valeur définitive une fois le tirage publié.
    static func recordResult(_ list: [OpenBoostObservation], drawNumber: Int,
                             boost: Int?) -> [OpenBoostObservation] {
        guard let idx = list.firstIndex(where: { $0.drawNumber == drawNumber && $0.boostAtResult == nil })
        else { return list }
        var out = list
        out[idx].boostAtResult = boost
        return out
    }
}

struct PublicationLatency: Codable, Identifiable {
    var drawNumber: Int
    var wagerEndAt: Date
    var observedAt: Date
    var latencySeconds: Double
    var id: Int { drawNumber }
}

struct SavedTicket: Codable, Identifiable, Hashable {
    var targetDraw: Int
    var stake: Int
    var kind: GridKind
    var variant: Int
    var numbers: [Int]
    var id: String { "\(targetDraw)-\(stake)-\(kind.rawValue)-\(variant)" }
}

// Journal du jour : ce que chaque grille aurait prédit, tirage par tirage.
struct GridPlay: Identifiable, Hashable {
    var kind: GridKind
    var variant: Int
    var numbers: [Int]
    var hits: Int
    var id: String { "\(kind.rawValue).\(variant)" }
    var label: String {
        switch variant {
        case 2: return "\(kind.label) II"
        case 3: return "Anti-\(kind.label)"
        case 4: return "\(kind.label) Furtif"
        default: return kind.label
        }
    }
}

struct DayPlay: Identifiable, Hashable {
    var drawNumber: Int
    var time: String
    var draw: [Int]
    var plays: [GridPlay]
    var id: Int { drawNumber }
}

struct DayJournal {
    var dayKey: String
    var stake: Int
    // Chaque prédiction est jouée sur `hold` tirages consécutifs avant
    // d'être régénérée (le mode multi-tirages du jeu réel).
    var hold: Int = 1
    var plays: [DayPlay]
}

enum Zurich {
    static let tz = TimeZone(identifier: "Europe/Zurich")!

    static func parts(_ date: Date) -> (date: String, time: String, dayKey: String) {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = tz
        let c = cal.dateComponents([.year, .month, .day, .hour, .minute], from: date)
        let y = c.year ?? 0
        let m = c.month ?? 0
        let d = c.day ?? 0
        let h = c.hour ?? 0
        let min = c.minute ?? 0
        return (
            date: String(format: "%02d.%02d.%04d", d, m, y),
            time: String(format: "%02d:%02d", h, min),
            dayKey: String(format: "%04d-%02d-%02d", y, m, d)
        )
    }

    static func parseISO(_ raw: String) -> Date? {
        let f1 = ISO8601DateFormatter()
        f1.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f1.date(from: raw) { return d }
        let f2 = ISO8601DateFormatter()
        f2.formatOptions = [.withInternetDateTime]
        if let d = f2.date(from: raw) { return d }
        let f3 = DateFormatter()
        f3.locale = Locale(identifier: "en_US_POSIX")
        f3.timeZone = tz
        f3.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f3.date(from: raw)
    }

    static func todayKey(_ date: Date = Date()) -> String {
        parts(date).dayKey
    }
}

enum Format {
    static let ch: NumberFormatter = {
        let f = NumberFormatter()
        f.locale = Locale(identifier: "fr_CH")
        f.numberStyle = .decimal
        f.maximumFractionDigits = 0
        return f
    }()

    static func chf(_ amount: Double) -> String {
        let francs = amount >= 10_000 ? amount / 100 : amount
        let f = NumberFormatter()
        f.locale = Locale(identifier: "fr_CH")
        f.numberStyle = .currency
        f.currencyCode = "CHF"
        f.maximumFractionDigits = francs >= 1000 ? 0 : 2
        return f.string(from: NSNumber(value: francs)) ?? "CHF \(francs)"
    }

    static func odds(_ p: Double) -> String {
        guard p > 0 else { return "—" }
        let inv = 1 / p
        if inv >= 1000 {
            return "1 / \(ch.string(from: NSNumber(value: round(inv))) ?? "\(Int(round(inv)))")"
        }
        if inv >= 20 {
            return "1 / \(Int(round(inv)))"
        }
        return String(format: "1 / %.1f", inv)
    }

    static func pad2(_ n: Int) -> String {
        String(format: "%02d", n)
    }

    static func clock(_ date: Date) -> String {
        let p = Zurich.parts(date)
        return "\(p.time) · \(p.date)"
    }

    static func countdown(to date: Date, now: Date) -> (label: String, urgent: Bool) {
        let ms = date.timeIntervalSince(now)
        if ms <= 0 { return ("Tirage en cours", true) }
        // ceil : « 05 » tant qu'il reste plus de 4 s — la convention d'un
        // compte à rebours calé sur l'instant réel du tirage.
        let total = Int(ceil(ms))
        let h = total / 3600
        let m = (total % 3600) / 60
        let s = total % 60
        let label = h > 0 ? "\(pad2(h)):\(pad2(m)):\(pad2(s))" : "\(pad2(m)):\(pad2(s))"
        return (label, ms < 30)
    }
}

enum Hits {
    static func inDraw(_ numbers: [Int], _ draw: Draw) -> Int {
        let set = Set(draw.numbers)
        return numbers.filter { set.contains($0) }.count
    }
}
