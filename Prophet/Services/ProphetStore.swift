import Combine
import Foundation
import SwiftUI

@MainActor
final class ProphetStore: ObservableObject {
    @Published var payload: LivePayload?
    @Published var oracle: OracleResult?
    @Published var error: String?
    @Published var loading = false
    @Published var stake: Int = 10
    @Published var tickets: [SavedTicket] = []

    struct KindPerf: Identifiable {
        var kind: GridKind
        var plays: Int
        var hits: Int
        var expected: Double
        var id: String { kind.rawValue }
    }

    private var poll: Timer?
    private static let memoryKey = "prophet.tickets.v1"
    private static let ticketRetentionDraws = 48

    init() {
        tickets = Self.readTickets()
        poll = Timer.scheduledTimer(withTimeInterval: 8, repeats: true) { [weak self] _ in
            Task { await self?.refresh() }
        }
        Task { await refresh(force: true) }
    }

    nonisolated deinit {
        // Le timer ne tient qu'une référence faible ; il est invalidé via RunLoop.
    }

    func refresh(force: Bool = false) async {
        if payload == nil { loading = true }
        do {
            let live = try await LoroClient.shared.loadLive(force: force)
            let history = live.history
            // L'oracle balaie ~200 tirages × 80 numéros : hors du main thread.
            let result = await Task.detached(priority: .userInitiated) {
                Oracle.run(history)
            }.value
            withAnimation(.smooth(duration: 0.5)) {
                payload = live
                oracle = result
            }
            error = nil
            rememberTickets(live: live)
        } catch {
            self.error = error.localizedDescription
        }
        loading = false
    }

    // Bilan honnête : chaque grille proposée est mémorisée pour le tirage suivant,
    // puis confrontée au résultat réel.
    func performance(stake: Int) -> [KindPerf] {
        guard let payload else { return [] }
        var byNumber: [Int: Draw] = [:]
        for d in payload.history { byNumber[d.drawNumber] = d }
        var out: [KindPerf] = []
        for kind in GridKind.allCases {
            var plays = 0
            var hits = 0
            for t in tickets where t.kind == kind && t.stake == stake {
                guard let draw = byNumber[t.targetDraw] else { continue }
                plays += 1
                hits += Hits.inDraw(t.numbers, draw)
            }
            if plays > 0 {
                out.append(KindPerf(
                    kind: kind,
                    plays: plays,
                    hits: hits,
                    expected: Double(plays * stake) * ProphetConst.baseP
                ))
            }
        }
        return out
    }

    private func rememberTickets(live: LivePayload) {
        guard let last = live.last, let oracle else { return }
        let next = last.drawNumber + 1
        if tickets.contains(where: { $0.targetDraw == next }) { return }
        let fresh: [SavedTicket] = oracle.stakes.flatMap { pack in
            pack.grids.map {
                SavedTicket(targetDraw: next, stake: pack.stake, kind: $0.kind, numbers: $0.numbers)
            }
        }
        tickets = tickets.filter { $0.targetDraw >= next - Self.ticketRetentionDraws } + fresh
        Self.writeTickets(tickets)
    }

    private static func readTickets() -> [SavedTicket] {
        guard let data = UserDefaults.standard.data(forKey: memoryKey) else { return [] }
        return (try? JSONDecoder().decode([SavedTicket].self, from: data)) ?? []
    }

    private static func writeTickets(_ tickets: [SavedTicket]) {
        let clipped = Array(tickets.suffix(800))
        if let data = try? JSONEncoder().encode(clipped) {
            UserDefaults.standard.set(data, forKey: memoryKey)
        }
    }
}
