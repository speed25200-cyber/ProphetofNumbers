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
    @Published var turbo = false
    @Published var journal: DayJournal?
    @Published var journalHold = 1

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
    // Variante incrémentale : l'état de l'essaim persiste, absorber un
    // nouveau tirage coûte quelques millisecondes.
    private let engine = SwarmEngine()
    private static let memoryKey = "prophet.tickets.v1"
    private static let notifKey = "prophet.notifs.v1"
    private static let turboKey = "prophet.turbo.v1"
    private static let holdKey = "prophet.journal.hold.v1"
    private static let ticketRetentionDraws = 48

    init() {
        tickets = Self.readTickets()
        notificationsOn = UserDefaults.standard.bool(forKey: Self.notifKey)
        turbo = UserDefaults.standard.bool(forKey: Self.turboKey)
        let storedHold = UserDefaults.standard.integer(forKey: Self.holdKey)
        journalHold = storedHold > 0 ? storedHold : 1
        // Tick à 100 ms : la cadence réelle est décidée par Schedule
        // (12 s loin du tirage → 250 ms en fenêtre chaude, 120 ms en Turbo).
        poll = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
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
        let delay = turbo
            ? Schedule.turboDelay(nextDrawAt: payload?.nextDrawAt, hole: payload?.hole ?? false, now: serverNow)
            : Schedule.pollDelay(nextDrawAt: payload?.nextDrawAt, hole: payload?.hole ?? false, now: serverNow)
        guard now.timeIntervalSince(lastFetchAt) >= delay - 0.05 else { return }
        // En Turbo rapproché, le cache client est court-circuité.
        await refresh(force: turbo && delay < 0.5)
    }

    func toggleTurbo() {
        turbo.toggle()
        UserDefaults.standard.set(turbo, forKey: Self.turboKey)
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

            // Deux temps : le résultat s'affiche immédiatement, puis l'essaim
            // digère le nouveau tirage hors du main thread et les grilles du
            // prochain tirage se recalent juste derrière.
            withAnimation(.smooth(duration: 0.4)) {
                payload = live
            }
            if oracle == nil || newestDraw != lastOracleDraw {
                // Variante incrémentale : grilles disponibles dans la foulée
                // du résultat.
                let result = await Task.detached(priority: .userInitiated) { [engine] in
                    engine.update(history)
                }.value
                lastOracleDraw = newestDraw
                withAnimation(.smooth(duration: 0.5)) {
                    oracle = result
                }
                // Variante existante (recalcul complet) en réconciliation :
                // mêmes opérations, même résultat — filet de sécurité.
                Task.detached(priority: .utility) { [weak self] in
                    let full = Swarm.run(history)
                    await self?.reconcile(full, draw: newestDraw)
                }
            }
            error = nil
            rememberTickets(live: live)
        } catch {
            self.error = error.localizedDescription
        }
        loading = false
    }

    private func reconcile(_ full: OracleResult, draw: Int) {
        guard lastOracleDraw == draw else { return }
        oracle = full
    }

    // Journal du jour : rejeu déterministe, recalculé uniquement quand un
    // nouveau tirage arrive ou que la mise change.
    private var journalKey = ""

    func setJournalHold(_ hold: Int) {
        journalHold = max(1, hold)
        UserDefaults.standard.set(journalHold, forKey: Self.holdKey)
    }

    func loadJournal() async {
        guard let payload else { return }
        let key = "\(payload.last?.drawNumber ?? 0)-\(stake)-\(journalHold)"
        if journalKey == key, journal != nil { return }
        let history = payload.history
        let stakeNow = stake
        let holdNow = journalHold
        let result = await Task.detached(priority: .userInitiated) {
            SwarmEngine.replayToday(history, stake: stakeNow, hold: holdNow)
        }.value
        journalKey = key
        withAnimation(.smooth(duration: 0.4)) {
            journal = result
        }
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
                SavedTicket(targetDraw: target, stake: pack.stake, kind: $0.kind, variant: $0.variant, numbers: $0.numbers)
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
