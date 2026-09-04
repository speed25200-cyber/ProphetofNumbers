import Combine
import Foundation

@MainActor
final class ProphetStore: ObservableObject {
    @Published var payload: LivePayload?
    @Published var oracle: OracleResult?
    @Published var error: String?
    @Published var loading = false
    @Published var stake: Int = 10
    @Published var tickets: [SavedTicket] = []
    @Published var now = Date()
    /// Publication-timing probe: is a result readable before its wager window closes?
    @Published var probe: String = LeakProbe.shared.summary

    private var timer: Timer?
    private var poll: Timer?
    private var inFlight = false
    private let memoryKey = "prophet.tickets.v1"

    init() {
        tickets = Self.readTickets()
        timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.now = Date() }
        }
        poll = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            Task { await self?.tick() }
        }
        Task { await refresh(force: true) }
    }

    nonisolated deinit {
        // Timers are invalidated from the main actor when the store is released
        // via RunLoop; they hold only a weak reference back to self.
    }

    func tick() async {
        now = Date()
        if inFlight { return }
        let delay = Schedule.pollDelay(nextDrawAt: payload?.nextDrawAt, hole: payload?.hole ?? false, now: now)
        let age = payload.map { now.timeIntervalSince($0.fetchedAt) } ?? 999
        if age >= delay { await refresh() }
    }

    func refresh(force: Bool = false) async {
        if inFlight && !force { return }
        inFlight = true
        if payload == nil { loading = true }
        defer { inFlight = false }
        do {
            let live = try await LoroClient.shared.loadLive(force: force)
            payload = live
            oracle = Oracle.run(live.history)
            error = nil
            rememberTickets(live: live)
            probe = LeakProbe.shared.summary
        } catch {
            self.error = error.localizedDescription
        }
        loading = false
    }

    var countdown: (label: String, urgent: Bool) {
        guard let at = payload?.nextDrawAt else { return ("—", false) }
        return Format.countdown(to: at, now: now)
    }

    private func rememberTickets(live: LivePayload) {
        guard let oracle else { return }
        let target = live.nextDrawNumber ?? (live.last.map { $0.drawNumber + 1 } ?? 0)
        guard target > 0 else { return }
        let fresh: [SavedTicket] = oracle.stakes.flatMap { pack in
            pack.grids.map {
                SavedTicket(targetDraw: target, stake: pack.stake, kind: $0.kind, numbers: $0.numbers)
            }
        }
        tickets = tickets.filter { $0.targetDraw != target && $0.targetDraw >= target - 12 } + fresh
        Self.writeTickets(tickets)
    }

    private static func readTickets() -> [SavedTicket] {
        guard let data = UserDefaults.standard.data(forKey: "prophet.tickets.v1") else { return [] }
        return (try? JSONDecoder().decode([SavedTicket].self, from: data)) ?? []
    }

    private static func writeTickets(_ tickets: [SavedTicket]) {
        let clipped = Array(tickets.suffix(80))
        if let data = try? JSONEncoder().encode(clipped) {
            UserDefaults.standard.set(data, forKey: "prophet.tickets.v1")
        }
    }
}
