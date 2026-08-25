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
        // Tick à 1 s : la cadence réelle est décidée par Schedule.pollDelay
        // (12 s loin du tirage → 1 s pendant la fenêtre de publication).
        poll = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { await self?.pollTick() }
        }
        Task { await refresh(force: true) }
    }

    nonisolated deinit {
        // Le timer ne tient qu'une référence faible ; il est invalidé via RunLoop.
    }

    private func pollTick() async {
        let now = Date()
        // Cadence en temps serveur Loro ; le TTL du client se resserre de la
        // même façon près du tirage et pendant un « hole ».
        let serverNow = now.addingTimeInterval(payload?.clockOffset ?? 0)
        let delay = Schedule.pollDelay(
            nextDrawAt: payload?.nextDrawAt,
            hole: payload?.hole ?? false,
            now: serverNow
        )
        guard now.timeIntervalSince(lastFetchAt) >= delay - 0.1 else { return }
        await refresh()
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
              let number = payload.nextDrawNumber ?? payload.last.map({ $0.drawNumber + 1 })
        else { return }
        let prediction = oracle?.stakes
            .first { $0.stake == stake }?
            .grids.first { $0.kind == .nexus }?
            .numbers ?? []
        // nextDrawAt est en temps serveur : reconverti en horloge appareil
        // pour que la notification parte au bon instant local.
        Notifier.scheduleDrawNotifications(
            nextDrawAt: next.addingTimeInterval(-payload.clockOffset),
            nextDrawNumber: number,
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
        guard let oracle else { return }
        // Cible le vrai prochain tirage ouvert ; les grilles du même tirage
        // sont remplacées quand le modèle se recale sur un résultat tardif.
        let target = live.nextDrawNumber ?? (live.last.map { $0.drawNumber + 1 } ?? 0)
        guard target > 0 else { return }
        let fresh: [SavedTicket] = oracle.stakes.flatMap { pack in
            pack.grids.map {
                SavedTicket(targetDraw: target, stake: pack.stake, kind: $0.kind, numbers: $0.numbers)
            }
        }
        let existing = tickets.filter { $0.targetDraw == target }
        if existing.count == fresh.count, Set(existing) == Set(fresh) { return }
        tickets = tickets.filter { $0.targetDraw != target && $0.targetDraw >= target - Self.ticketRetentionDraws } + fresh
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
