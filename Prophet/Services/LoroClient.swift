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
    private let drawsURL = URL(string: "https://jeux.loro.ch/api/dbg/game/lotoexpress/draws")!
    private let source = "https://jeux.loro.ch/games/lotoexpress/results"
    private let historyWindow = 399
    private let pageSize = 100

    private var cache: [Int: Draw] = [:]
    private var live: LivePayload?
    private var liveAt: Date = .distantPast

    func loadLive(force: Bool = false) async throws -> LivePayload {
        let ttl = Schedule.cacheTtl(nextDrawAt: live?.nextDrawAt, hole: live?.hole ?? false)
        if !force, let live, Date().timeIntervalSince(liveAt) < ttl {
            return live
        }
        async let edgeTask = fetchEdge()
        let json = try await fetchJSON(gameURL)
        var slots = await edgeTask
        let details = dict(json["details"])
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
        let gameSlot = parseSlot(rawDraw)
        if let draw = gameSlot?.asDraw() {
            cache[draw.drawNumber] = draw
        }

        let hint = max(
            gameSlot?.asDraw()?.drawNumber ?? 0,
            slots.filter(\.isComplete).map(\.drawNumber).max() ?? 0
        )
        let pending = await fetchDraws(ids: [hint + 1, hint + 2, hint + 3])
        let recent = await fetchRecent(previous: hint)
        slots.append(contentsOf: pending)
        slots.append(contentsOf: recent)
        if let gameSlot { slots.append(gameSlot) }

        let fallbackNextRaw = details["drawDate"] as? String
        let fallbackNext = fallbackNextRaw.flatMap(Zurich.parseISO)
        var clock = Schedule.resolve(
            slots: slots,
            fallbackNext: fallbackNext,
            fallbackNextRaw: fallbackNextRaw,
            fallbackLast: gameSlot?.asDraw()
        )
        if let pendingId = clock.pendingDrawNumber, let extra = await fetchDraw(pendingId) {
            slots.append(extra)
            clock = Schedule.resolve(
                slots: slots,
                fallbackNext: fallbackNext,
                fallbackNextRaw: fallbackNextRaw,
                fallbackLast: gameSlot?.asDraw()
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
            source: source
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

    private func fetchEdge() async -> [Schedule.Slot] {
        let url = URL(string: "\(drawsURL.absoluteString)?pageSize=20")!
        return await parseSlotList(url)
    }

    private func fetchRecent(previous: Int) async -> [Schedule.Slot] {
        guard previous > 0 else { return [] }
        let url = URL(string: "\(drawsURL.absoluteString)?previousDraw=\(previous)&pageSize=40")!
        return await parseSlotList(url)
    }

    private func fetchDraw(_ id: Int) async -> Schedule.Slot? {
        guard id > 0 else { return nil }
        let url = URL(string: "\(drawsURL.absoluteString)/\(id)")!
        guard let json = try? await fetchJSON(url) else { return nil }
        guard let slot = parseSlot(json) else { return nil }
        if let draw = slot.asDraw() { cache[draw.drawNumber] = draw }
        return slot
    }

    private func fetchDraws(ids: [Int]) async -> [Schedule.Slot] {
        var out: [Schedule.Slot] = []
        for id in ids {
            if let slot = await fetchDraw(id) { out.append(slot) }
        }
        return out
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
        var req = URLRequest(url: url, timeoutInterval: 12)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("https://jeux.loro.ch", forHTTPHeaderField: "Origin")
        req.setValue("https://jeux.loro.ch/games/lotoexpress/results", forHTTPHeaderField: "Referer")
        req.setValue(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            forHTTPHeaderField: "User-Agent"
        )
        let (data, resp) = try await URLSession.shared.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw LoroError.http(http.statusCode)
        }
        guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LoroError.decode
        }
        return obj
    }

    private func parseDraw(_ raw: [String: Any]) -> Draw? {
        guard let drawNumber = asInt(raw["drawNumber"]) else { return nil }
        let drawDate = raw["drawDate"] as? String ?? ""
        guard !drawDate.isEmpty else { return nil }
        let matrix = parseMatrix(raw["drawResult"] ?? raw["result"] ?? raw)
        guard matrix.numbers.count >= 15 else { return nil }
        return Draw(
            drawNumber: drawNumber,
            drawDate: drawDate,
            numbers: matrix.numbers,
            boost: matrix.boost,
            bonus: matrix.bonus
        )
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
