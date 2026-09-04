import Foundation

/// Measures whether a draw's result is reachable in the LoRo feed **before** its own
/// wager window closes.
///
/// The offline audit of `claude/RECHERCHE.md` ruled out every way of predicting the
/// numbers from the published history: no statistical structure, no generator with a
/// state of 32 bits or fewer, no F2-linear generator up to 19937 bits, no 64-bit LCG
/// with a standard multiplier. What it could not test offline is the publication
/// pipeline itself, and that is the one place an edge could still live: if a complete
/// result exists in the API even a second before `wagerEndDate`, no cryptanalysis is
/// needed at all.
///
/// This records, per draw, the earliest moment the app saw its twenty numbers and how
/// that compares to the moment betting closed. A negative margin is the normal case
/// (the result appears after the window shuts). A positive margin on any draw is the
/// finding, and it needs a single observation to be worth acting on.
///
/// It also notes whether a draw ever carried a boost multiplier while still open,
/// because the multiplier table is known exactly (x1 51.2%, x2 23.8%, x3 15.0%,
/// x4 5.0%, x5 2.5%, x10 2.5%, mean 2.013) and betting only when boost >= 4 would
/// multiply the return by 2.86 — again with no prediction involved.
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
        if open, boost != nil, !seenOpenBoost.contains(drawNumber) {
            // Multiplier exposed before the draw: worth recording even without a result.
            seenOpenBoost.insert(drawNumber)
            record(drawNumber: drawNumber, margin: nil, boostWhileOpen: true)
            return
        }
        guard complete, !seenComplete.contains(drawNumber) else { return }
        seenComplete.insert(drawNumber)
        guard let raw = wagerEndDate, let end = Zurich.parseISO(raw) else { return }
        record(drawNumber: drawNumber, margin: end.timeIntervalSince(Date()), boostWhileOpen: false)
    }

    private func record(drawNumber: Int, margin: Double?, boostWhileOpen: Bool) {
        rows.append(Observation(drawNumber: drawNumber,
                                marginSeconds: margin ?? 0,
                                seenAt: Date(),
                                boostWhileOpen: boostWhileOpen))
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

    /// One compact line for the UI.
    var summary: String {
        lock.lock()
        let n = rows.filter { !$0.boostWhileOpen }.count
        let best = rows.filter { !$0.boostWhileOpen }.max { $0.marginSeconds < $1.marginSeconds }
        let boostSeen = rows.contains { $0.boostWhileOpen }
        lock.unlock()
        guard let best, n > 0 else { return "sonde · en attente" }
        let m = best.marginSeconds
        let sign = m > 0 ? "+" : ""
        let verdict = m > 0 ? "RÉSULTAT LISIBLE AVANT CLÔTURE" : "après clôture"
        let boost = boostSeen ? " · boost visible ouvert" : ""
        let margin = String(format: "%.1f", m)
        return "sonde · \(n) tirages · marge max \(sign)\(margin) s · \(verdict)\(boost)"
    }
}
