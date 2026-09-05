import Foundation

/// Measures whether a draw's result is reachable in the LoRo feed **before** its own
/// wager window closes.
///
/// The offline audit of `claude/RECHERCHE.md` ruled out every way of predicting the
/// numbers from the published history: no statistical structure; no generator with a
/// state of 32 bits or fewer; no F2-linear generator of state below 35280 bits, by
/// linear complexity and without enumerating families; no LCG of any multiplier or
/// increment; no lagged Fibonacci, multiply-with-carry, or bijectively-finalised
/// additive state. What it could not test offline is the publication pipeline itself,
/// and that is the one place an edge could still live: if a complete result exists in
/// the API even a second before `wagerEndDate`, no cryptanalysis is needed at all.
///
/// This records, per draw, the earliest moment the app saw its twenty numbers and how
/// that compares to the moment betting closed. A negative margin is the normal case
/// (the result appears after the window shuts). A positive margin on any draw is the
/// finding, and it needs a single observation to be worth acting on.
///
/// It also records the boost multiplier of any draw seen while still open, because the
/// multiplier table is known exactly (x1 51.2%, x2 23.8%, x3 15.0%, x4 5.0%, x5 2.5%,
/// x10 2.5%, mean 2.013). Betting only when boost >= 4 multiplies the return by
/// 5.75/2.013 = 2.856, which breaks even at a base RTP of 0.350 — profitable at any
/// return rate a keno plausibly has, with no prediction involved. That is why the VALUE
/// matters and not just the presence: only boost >= 4 is worth acting on, and it covers
/// 10% of draws.
final class LeakProbe: @unchecked Sendable {
    static let shared = LeakProbe()

    /// Reached from the LoroClient actor and from the main actor, so every access to
    /// the mutable state goes through this lock.
    private let lock = NSLock()

    struct Observation: Codable {
        var drawNumber: Int
        /// Seconds between the result first being visible and the wager window closing.
        /// Positive means the result was readable while bets were still open.
        var marginSeconds: Double
        var seenAt: Date
        var boostWhileOpen: Bool
        /// The multiplier read while the draw was still open. Only >= 4 is actionable.
        /// Optional so that rows written by earlier builds still decode.
        var boostValue: Int?
    }

    private let key = "prophet.leakprobe.v1"
    private let cap = 400
    /// Kept apart on purpose: noting a boost on an open draw must not consume the
    /// slot that the later, complete sighting of the same draw needs to measure its
    /// margin. One draw can legitimately produce both observations.
    private var seenComplete = Set<Int>()
    private var seenOpenBoost = Set<Int>()
    private var rows: [Observation] = []

    private init() {
        if let data = UserDefaults.standard.data(forKey: key),
           let rows = try? JSONDecoder().decode([Observation].self, from: data) {
            self.rows = rows
            seenComplete = Set(rows.filter { !$0.boostWhileOpen }.map(\.drawNumber))
            seenOpenBoost = Set(rows.filter { $0.boostWhileOpen }.map(\.drawNumber))
        }
    }

    /// Called for every slot the client parses. Only the first sighting of a given
    /// draw counts — later ones say nothing about how early the result was reachable.
    func note(drawNumber: Int, complete: Bool, wagerEndDate: String?, boost: Int?, phase: String?) {
        lock.lock(); defer { lock.unlock() }
        let open = (phase ?? "").uppercased() == "OPEN"
        if open, let boost, !seenOpenBoost.contains(drawNumber) {
            // Multiplier exposed before the draw: worth recording even without a result,
            // and the value decides whether the draw is worth betting at all.
            seenOpenBoost.insert(drawNumber)
            record(drawNumber: drawNumber, margin: nil, boostWhileOpen: true, boost: boost)
            return
        }
        guard complete, !seenComplete.contains(drawNumber) else { return }
        seenComplete.insert(drawNumber)
        guard let raw = wagerEndDate, let end = Zurich.parseISO(raw) else { return }
        record(drawNumber: drawNumber, margin: end.timeIntervalSince(Date()), boostWhileOpen: false)
    }

    private func record(drawNumber: Int, margin: Double?, boostWhileOpen: Bool,
                        boost: Int? = nil) {
        rows.append(Observation(drawNumber: drawNumber,
                                marginSeconds: margin ?? 0,
                                seenAt: Date(),
                                boostWhileOpen: boostWhileOpen,
                                boostValue: boost))
        if rows.count > cap { rows.removeFirst(rows.count - cap) }
        if let data = try? JSONEncoder().encode(rows) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    /// Worst case seen so far — the largest margin is the one that matters, since a
    /// single draw readable before its window shuts is enough to prove the leak.
    var best: Observation? {
        lock.lock(); defer { lock.unlock() }
        return rows.filter { !$0.boostWhileOpen }.max { $0.marginSeconds < $1.marginSeconds }
    }

    var boostSeenOpen: Bool {
        lock.lock(); defer { lock.unlock() }
        return rows.contains { $0.boostWhileOpen }
    }

    /// Draws seen open while carrying a multiplier of 4 or more. These are the only ones
    /// the boost lever is about: they are 10% of draws and betting only on them breaks
    /// even at a base RTP of 0.350.
    var actionableBoostCount: Int {
        lock.lock(); defer { lock.unlock() }
        return rows.filter { $0.boostWhileOpen && ($0.boostValue ?? 0) >= 4 }.count
    }

    /// One compact line for the UI.
    var summary: String {
        lock.lock()
        let n = rows.filter { !$0.boostWhileOpen }.count
        let best = rows.filter { !$0.boostWhileOpen }.max { $0.marginSeconds < $1.marginSeconds }
        let boostSeen = rows.contains { $0.boostWhileOpen }
        let high = rows.filter { $0.boostWhileOpen && ($0.boostValue ?? 0) >= 4 }.count
        lock.unlock()
        guard let best, n > 0 else { return "sonde · en attente" }
        let m = best.marginSeconds
        let sign = m > 0 ? "+" : ""
        let verdict = m > 0 ? "RÉSULTAT LISIBLE AVANT CLÔTURE" : "après clôture"
        // Only boost >= 4 is worth acting on, so report that count rather than mere presence.
        let boost = high > 0 ? " · \(high) tirages ouverts à boost ≥ 4"
                  : boostSeen ? " · boost visible ouvert (tous < 4)" : ""
        let margin = String(format: "%.1f", m)
        return "sonde · \(n) tirages · marge max \(sign)\(margin) s · \(verdict)\(boost)"
    }
}
