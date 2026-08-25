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
    @Published var notificationsOn = false

    struct KindPerf: Identifiable {
        var kind: GridKind
        var plays: Int
        var hits: Int
        var expected: Double
        var id: String { kind.rawValue }
    }

    private var poll: Timer?
    private var lastFetchAt = Date.distantPast
    private var refreshing = false
    private var lastOracleDraw = Int.min
    private static let memoryKey = "prophet.tickets.v1"
    private static let notifKey = "prophet.notifs.v1"
    private static let ticketRetentionDraws = 48

    init() {
        tickets = Self.readTickets()
        notificationsOn = UserDefaults.standard.bool(forKey: Self.notifKey)
        // Tick rapide : la cadence réelle est décidée dans pollTick —
        // 2 s forcées autour du tirage, 8 s en croisière.
        poll = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { await self?.pollTick() }
        }
        Task { await refresh(force: true) }
    }

    nonisolated deinit {
        // Le timer ne tient qu'une référence faible ; il est invalidé via RunLoop.
    }

    private func pollTick() async {
        let now = Date()
        let hot = inDrawWindow(now)
        let interval: TimeInterval = hot ? 2 : 8
        guard now.timeIntervalSince(lastFetchAt) >= interval - 0.1 else { return }
        await refresh(force: hot)
    }

    // Fenêtre chaude : de 5 s avant le tirage annoncé jusqu'à ce que l'API
    // publie le nouveau numéro (nextDrawAt repasse alors dans le futur).
    private func inDrawWindow(_ now: Date) -> Bool {
        guard let payload else { return true }
        guard let next = payload.nextDrawAt else { return false }
        return now >= next.addingTimeInterval(-5)
    }

    func refresh(force: Bool = false) async {
        if refreshing { return }
        refreshing = true
        defer { refreshing = false }
        lastFetchAt = Date()
        if payload == nil { loading = true }
        do {
            let live = try await LoroClient.shared.loadLive(force: force)
            let history = live.history
            let newestDraw = live.last?.drawNumber ?? -1
            if oracle == nil || newestDraw != lastOracleDraw {
                // L'essaim balaie ~200 tirages × 80 numéros × 26 têtes :
                // hors du main thread, et seulement sur un nouveau tirage.
                let result = await Task.detached(priority: .userInitiated) {
                    Swarm.run(history)
                }.value
                lastOracleDraw = newestDraw
                withAnimation(.smooth(duration: 0.5)) {
                    payload = live
                    oracle = result
                }
            } else {
                payload = live
            }
            error = nil
            rememberTickets(live: live)
        } catch {
            self.error = error.localizedDescription
        }
        loading = false
    }

    func toggleNotifications() {
        if notificationsOn {
            notificationsOn = false
            UserDefaults.standard.set(false, forKey: Self.notifKey)
            Notifier.cancelDrawNotifications()
        } else {
            Task { @MainActor in
                let granted = await Notifier.requestAuthorization()
                notificationsOn = granted
                UserDefaults.standard.set(granted, forKey: Self.notifKey)
            }
        }
    }

    // En arrière-plan : programme les prochaines fins de tirage avec la
    // dernière prédiction Nexus. Au retour au premier plan, tout est annulé —
    // le live prend le relais.
    func armBackgroundNotifications() {
        guard notificationsOn,
              let payload,
              let next = payload.nextDrawAt,
              let last = payload.last else { return }
        let prediction = oracle?.stakes
            .first { $0.stake == stake }?
            .grids.first { $0.kind == .nexus }?
            .numbers ?? []
        Notifier.scheduleDrawNotifications(
            nextDrawAt: next,
            nextDrawNumber: last.drawNumber + 1,
            prediction: prediction,
            stake: stake
        )
    }

    func disarmBackgroundNotifications() {
        Notifier.cancelDrawNotifications()
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
