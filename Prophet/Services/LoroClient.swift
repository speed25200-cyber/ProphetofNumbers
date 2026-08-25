import Foundation

enum LoroError: LocalizedError {
    case http(Int)
    case decode
    case empty

    var errorDescription: String? {
        switch self {
        case .http(let code): return "Loro \(code)"
        case .decode: return "Réponse Loro illisible"
        case .empty: return "Aucun tirage dans le flux"
        }
    }
}

actor LoroClient {
    static let shared = LoroClient()

    private let gameURL = URL(string: "https://jeux.loro.ch/api/dbg/game/lotoexpress")!
    private let resultsURL = URL(string: "https://jeux.loro.ch/api/dbg/game/lotoexpress/results")!
    private let drawsURL = URL(string: "https://jeux.loro.ch/api/dbg/game/lotoexpress/draws")!
    private let source = "https://jeux.loro.ch/games/lotoexpress/results"
    private let historyWindow = 399
    private let pageSize = 100

    private var cache: [Int: Draw] = [:]
    private var live: LivePayload?
    private var liveAt: Date = .distantPast
    // Décalage horloge serveur Loro − horloge appareil, lissé (EMA).
    private var clockOffset: TimeInterval = 0
    private var clockSamples = 0

    private static let httpDateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "GMT")
        f.dateFormat = "EEE, dd MMM yyyy HH:mm:ss zzz"
        return f
    }()

    func loadLive(force: Bool = false) async throws -> LivePayload {
        let serverNow = Date().addingTimeInterval(clockOffset)
        let ttl = Schedule.cacheTtl(nextDrawAt: live?.nextDrawAt, hole: live?.hole ?? false, now: serverNow)
        if !force, let live, Date().timeIntervalSince(liveAt) < ttl {
            return live
        }

        let probeId = (live?.last?.drawNumber ?? 0) + 1
        let hot = live?.hole == true
            || (live?.nextDrawAt.map { $0.timeIntervalSince(serverNow) < 25 } ?? false)

        // Fenêtre chaude : sonde last+1 en cassant le cache public 3 s de
        // Loro — le résultat est ingéré à l'instant où il existe, sans
        // attendre les listes qui retardent.
        if hot, probeId > 1, let prev = live {
            async let probeHot = fetchDraw(probeId, bust: true)
            async let openHot = fetchOpen()
            let probe = await probeHot
            let openSlots = await openHot
            if let probe, probe.isComplete, let landed = probe.asDraw() {
                let clock = Schedule.resolve(
                    slots: [probe] + openSlots,
                    fallbackNext: openSlots.first.flatMap { Zurich.parseISO($0.drawDate) } ?? prev.nextDrawAt,
                    fallbackNextRaw: openSlots.first?.drawDate,
                    fallbackLast: landed,
                    now: serverNow
                )
                var history = prev.history.filter { $0.drawNumber != landed.drawNumber }
                history.insert(landed, at: 0)
                let key = Zurich.todayKey()
                let today = history.filter { draw in
                    guard let date = Zurich.parseISO(draw.drawDate) else { return false }
                    return Zurich.parts(date).dayKey == key
                }
                let payload = LivePayload(
                    status: prev.status,
                    nextDrawAt: clock.nextDrawAt,
                    nextDrawNumber: clock.nextDrawNumber,
                    wagerEndAt: clock.wagerEndAt,
                    hole: clock.hole,
                    pendingDrawNumber: clock.pendingDrawNumber,
                    last: clock.last,
                    jackpots: prev.jackpots,
                    today: today,
                    history: history,
                    fetchedAt: Date(),
                    source: source,
                    clockOffset: clockOffset
                )
                live = payload
                liveAt = Date()
                return payload
            }
        }

        // La page résultats Loro suit deux flux : status=OPEN (le tirage
        // jouable, saute celui en cours) et RESULTS_AVAILABLE du jour ; le
        // endpoint /results sert de secours au endpoint jeu.
        let day = Zurich.todayKey()
        async let openTask = fetchOpen()
        async let publishedTask = fetchPublished(day: day)
        async let resultsTask = fetchJSONOptional(resultsURL)
        async let probeTask = fetchProbe(probeId)
        let json = try await fetchJSON(gameURL)
        let openSlots = await openTask
        let published = await publishedTask
        let resultsJson = await resultsTask
        let probe = await probeTask
        var slots = published + openSlots

        let details = dict(json["details"])
        let resultsDetails = dict(resultsJson?["details"])
        let gameSlot = slotFromDetails(details) ?? slotFromDetails(resultsDetails)
        if let draw = gameSlot?.asDraw() {
            cache[draw.drawNumber] = draw
        }

        // Les listes sautent le dernier résultat pendant ~1 min ;
        // GET /draws/{id} autour du bord l'a immédiatement.
        let hint = max(
            gameSlot?.asDraw()?.drawNumber ?? 0,
            published.filter(\.isComplete).map(\.drawNumber).max() ?? 0,
            probe?.asDraw()?.drawNumber ?? 0
        )
        let minOpen = openSlots.filter { !$0.isComplete }.map(\.drawNumber).min()
        var ids = [hint + 1, hint + 2, hint + 3]
        if let minOpen {
            ids.append(contentsOf: [minOpen - 1, minOpen, minOpen + 1])
        }
        let pending = await fetchDraws(ids: Array(Set(ids.filter { $0 > 0 && $0 != probeId })).sorted(), bust: hot)
        slots.append(contentsOf: pending)
        if let gameSlot { slots.append(gameSlot) }
        if let probe { slots.append(probe) }

        let fallbackNextRaw = (details["drawDate"] as? String) ?? (resultsDetails["drawDate"] as? String)
        let fallbackNext = fallbackNextRaw.flatMap(Zurich.parseISO)
        var clock = Schedule.resolve(
            slots: slots,
            fallbackNext: fallbackNext,
            fallbackNextRaw: fallbackNextRaw,
            fallbackLast: gameSlot?.asDraw(),
            now: serverNow
        )
        if let pendingId = clock.pendingDrawNumber, let extra = await fetchDraw(pendingId, bust: true) {
            slots.append(extra)
            clock = Schedule.resolve(
                slots: slots,
                fallbackNext: fallbackNext,
                fallbackNextRaw: fallbackNextRaw,
                fallbackLast: gameSlot?.asDraw(),
                now: serverNow
            )
        }

        let last = clock.last
        let latestId = last?.drawNumber ?? 0
        let from = max(1, latestId - historyWindow)
        let history = latestId > 0 ? try await ensureRange(from: from, to: latestId) : []
        let key = Zurich.todayKey()
        let today = history.filter { draw in
            guard let date = Zurich.parseISO(draw.drawDate) else { return false }
            return Zurich.parts(date).dayKey == key
        }

        let payload = LivePayload(
            status: details["status"] as? String ?? "UNKNOWN",
            nextDrawAt: clock.nextDrawAt,
            nextDrawNumber: clock.nextDrawNumber,
            wagerEndAt: clock.wagerEndAt,
            hole: clock.hole,
            pendingDrawNumber: clock.pendingDrawNumber,
            last: last,
            jackpots: parseJackpots(details["extraJackpots"]),
            today: today,
            history: history,
            fetchedAt: Date(),
            source: source,
            clockOffset: clockOffset
        )
        live = payload
        liveAt = Date()
        return payload
    }

    private func ensureRange(from: Int, to: Int) async throws -> [Draw] {
        var end = to
        while end >= from {
            let start = max(from, end - (pageSize - 1))
            var missing = false
            for id in start...end {
                if cache[id] == nil { missing = true; break }
            }
            if missing {
                _ = await fetchSlots(from: start, to: end)
            }
            end -= pageSize
        }
        var out: [Draw] = []
        var id = to
        while id >= from {
            if let d = cache[id] { out.append(d) }
            id -= 1
        }
        return out
    }

    private func fetchSlots(from: Int, to: Int) async -> [Schedule.Slot] {
        guard to >= from else { return [] }
        let url = URL(string: "\(drawsURL.absoluteString)?from=\(from)&to=\(to)&pageSize=\(pageSize)")!
        return await parseSlotList(url)
    }

    private func slotFromDetails(_ details: [String: Any]) -> Schedule.Slot? {
        let results = dict(details["results"])
        let raw = dict(results["raw"])
        var rawDraw: [String: Any] = [
            "drawNumber": raw["drawNumber"] as Any,
            "drawDate": (raw["drawDate"] ?? results["drawDate"]) as Any,
            "phase": raw["phase"] as Any,
            "wagerEndDate": raw["wagerEndDate"] as Any,
        ]
        if let result = raw["result"] {
            rawDraw["drawResult"] = result
        } else {
            rawDraw["drawResult"] = [
                "matrix1": [
                    "main": results["primarySelection"] as Any,
                    "boost": results["secondarySelection"] as Any,
                    "bonus": results["tertiarySelection"] as Any,
                ]
            ]
        }
        return parseSlot(rawDraw)
    }

    private func fetchOpen() async -> [Schedule.Slot] {
        let url = URL(string: "\(drawsURL.absoluteString)?status=OPEN&size=8")!
        return await parseSlotList(url)
    }

    private func fetchPublished(day: String) async -> [Schedule.Slot] {
        let url = URL(string: "\(drawsURL.absoluteString)?page=1&size=40&status=RESULTS_AVAILABLE&startDate=\(day)&endDate=\(day)")!
        return await parseSlotList(url)
    }

    private func fetchJSONOptional(_ url: URL) async -> [String: Any]? {
        try? await fetchJSON(url)
    }

    private func fetchDraw(_ id: Int, bust: Bool = false) async -> Schedule.Slot? {
        guard id > 0 else { return nil }
        var raw = "\(drawsURL.absoluteString)/\(id)"
        if bust { raw += "?_=\(Int(Date().timeIntervalSince1970 * 1000))" }
        guard let url = URL(string: raw) else { return nil }
        guard let json = try? await fetchJSON(url) else { return nil }
        guard let slot = parseSlot(json) else { return nil }
        if let draw = slot.asDraw() { cache[draw.drawNumber] = draw }
        return slot
    }

    private func fetchProbe(_ id: Int) async -> Schedule.Slot? {
        guard id > 1 else { return nil }
        return await fetchDraw(id, bust: true)
    }

    private func fetchDraws(ids: [Int], bust: Bool = false) async -> [Schedule.Slot] {
        await withTaskGroup(of: Schedule.Slot?.self) { group in
            for id in ids {
                group.addTask { await self.fetchDraw(id, bust: bust) }
            }
            var out: [Schedule.Slot] = []
            for await slot in group {
                if let slot { out.append(slot) }
            }
            return out
        }
    }

    private func parseSlotList(_ url: URL) async -> [Schedule.Slot] {
        guard let json = try? await fetchJSON(url) else { return [] }
        let rows = json["results"] as? [Any] ?? []
        var out: [Schedule.Slot] = []
        for row in rows {
            guard let rec = row as? [String: Any], let slot = parseSlot(rec) else { continue }
            if let draw = slot.asDraw() { cache[draw.drawNumber] = draw }
            out.append(slot)
        }
        return out
    }

    private func parseSlot(_ raw: [String: Any]) -> Schedule.Slot? {
        guard let drawNumber = asInt(raw["drawNumber"]) else { return nil }
        let drawDate = raw["drawDate"] as? String ?? ""
        guard !drawDate.isEmpty else { return nil }
        let matrix = parseMatrix(raw["drawResult"] ?? raw["result"] ?? raw)
        return Schedule.Slot(
            drawNumber: drawNumber,
            drawDate: drawDate,
            numbers: matrix.numbers,
            boost: matrix.boost,
            bonus: matrix.bonus,
            phase: raw["phase"] as? String,
            wagerEndDate: raw["wagerEndDate"] as? String
        )
    }

    private func fetchJSON(_ url: URL) async throws -> [String: Any] {
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 8)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("fr-CH,fr;q=0.9", forHTTPHeaderField: "Accept-Language")
        req.setValue("https://jeux.loro.ch", forHTTPHeaderField: "Origin")
        req.setValue(source, forHTTPHeaderField: "Referer")
        req.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        req.setValue("no-cache", forHTTPHeaderField: "Pragma")
        req.setValue(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            forHTTPHeaderField: "User-Agent"
        )
        let t0 = Date()
        let (data, resp) = try await URLSession.shared.data(for: req)
        let t1 = Date()
        if let http = resp as? HTTPURLResponse {
            if !(200...299).contains(http.statusCode) {
                throw LoroError.http(http.statusCode)
            }
            // Offset d'horloge : Date serveur (tronquée à la seconde, donc
            // +0,5 s en moyenne) + moitié de l'aller-retour, vs réception.
            if let raw = http.value(forHTTPHeaderField: "Date"),
               let server = Self.httpDateFormatter.date(from: raw) {
                let rtt = t1.timeIntervalSince(t0)
                let sample = server.addingTimeInterval(0.5 + rtt / 2).timeIntervalSince(t1)
                if abs(sample) < 120 {
                    clockOffset = clockSamples == 0 ? sample : 0.8 * clockOffset + 0.2 * sample
                    clockSamples += 1
                }
            }
        }
        guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LoroError.decode
        }
        return obj
    }

    private func parseMatrix(_ raw: Any) -> (numbers: [Int], boost: Int?, bonus: Int?) {
        let obj = dict(raw)
        let matrix1 = dict(obj["matrix1"])
        let result = dict(obj["result"])
        let matrix = matrix1.isEmpty ? dict(result["matrix1"]) : matrix1
        let src = matrix.isEmpty ? obj : matrix
        let numbers = parseNumbers(src["main"] ?? obj["primarySelection"])
        let boostArr = parseLoose(src["boost"])
        let bonusArr = parseNumbers(src["bonus"] ?? obj["tertiarySelection"])
        return (numbers, boostArr.first, bonusArr.first)
    }

    private func parseNumbers(_ raw: Any?) -> [Int] {
        guard let arr = raw as? [Any] else { return [] }
        var out: [Int] = []
        for item in arr {
            if let rec = item as? [String: Any], let n = asInt(rec["number"]), (1...80).contains(n) {
                out.append(n)
            } else if let n = asInt(item), (1...80).contains(n) {
                out.append(n)
            }
        }
        return Array(Set(out)).sorted()
    }

    private func parseLoose(_ raw: Any?) -> [Int] {
        guard let arr = raw as? [Any] else { return [] }
        return arr.compactMap(asInt)
    }

    private func parseJackpots(_ raw: Any?) -> [Jackpot] {
        guard let arr = raw as? [Any] else { return [] }
        var out: [Jackpot] = []
        for row in arr {
            let rec = dict(row)
            if let stake = asInt(rec["id"]), let amount = asDouble(rec["amount"]) {
                out.append(Jackpot(stake: stake, amount: amount))
            }
        }
        return out.sorted { $0.stake < $1.stake }
    }

    private func dict(_ raw: Any?) -> [String: Any] {
        raw as? [String: Any] ?? [:]
    }

    private func asInt(_ v: Any?) -> Int? {
        if let n = v as? Int { return n }
        if let n = v as? Double { return Int(n) }
        if let s = v as? String, let n = Int(s) { return n }
        if let n = v as? NSNumber { return n.intValue }
        return nil
    }

    private func asDouble(_ v: Any?) -> Double? {
        if let n = v as? Double { return n }
        if let n = v as? Int { return Double(n) }
        if let s = v as? String, let n = Double(s) { return n }
        if let n = v as? NSNumber { return n.doubleValue }
        return nil
    }
}
