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
    var expectedHits: Double
    var baseExpected: Double
    var pAllHit: Double
    var basePAllHit: Double
    var id: String { "\(kind.rawValue).\(variant)" }
}

struct StakeGrids: Identifiable {
    var stake: Int
    var grids: [SuggestedGrid]
    var oddsLabel: String
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
    // Horloge serveur Loro − horloge appareil : à ajouter à l'heure locale
    // pour se caler sur le flux réel.
    var clockOffset: TimeInterval = 0
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
