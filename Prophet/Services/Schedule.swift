import Foundation

enum Schedule {
    static let interval: TimeInterval = 5 * 60
    static let ahead = 16

    struct Slot {
        var drawNumber: Int
        var drawDate: String
        var numbers: [Int]
        var boost: Int?
        var bonus: Int?
        var phase: String?
        var wagerEndDate: String?
        var isComplete: Bool { numbers.count >= 15 }

        func asDraw() -> Draw? {
            guard isComplete else { return nil }
            return Draw(
                drawNumber: drawNumber,
                drawDate: drawDate,
                numbers: numbers,
                boost: boost,
                bonus: bonus
            )
        }
    }

    struct Clock {
        var last: Draw?
        var nextDrawAt: Date?
        var nextDrawNumber: Int?
        var wagerEndAt: Date?
        var hole: Bool
        var pendingDrawNumber: Int?
        var phase: String?
    }

    static func resolve(
        slots: [Slot],
        fallbackNext: Date?,
        fallbackNextRaw: String?,
        fallbackLast: Draw?,
        now: Date = Date()
    ) -> Clock {
        var completed = slots.compactMap { $0.asDraw() }
        if let fallbackLast, !completed.contains(where: { $0.drawNumber == fallbackLast.drawNumber }) {
            completed.append(fallbackLast)
        }
        completed.sort { $0.drawNumber > $1.drawNumber }
        let last = completed.first

        let open = slots.filter { slot in
            guard !slot.isComplete else { return false }
            let phase = (slot.phase ?? "").uppercased()
            if phase == "RESULTS_AVAILABLE" || phase == "CLOSED" || phase == "DRAWING" {
                return false
            }
            guard let t = Zurich.parseISO(slot.drawDate) else { return false }
            return t.timeIntervalSince(now) >= -60
        }
        .sorted { $0.drawNumber < $1.drawNumber }

        var next = open.first
        if let fallbackNextRaw {
            next = open.first(where: { $0.drawDate == fallbackNextRaw })
                ?? slots.first(where: { $0.drawDate == fallbackNextRaw && !$0.isComplete })
                ?? next
        }

        var nextDrawAt = next.flatMap { Zurich.parseISO($0.drawDate) } ?? fallbackNext
        if nextDrawAt == nil, let last, let lastDate = Zurich.parseISO(last.drawDate) {
            var t = lastDate.addingTimeInterval(interval)
            while t.timeIntervalSince(now) < -15 { t = t.addingTimeInterval(interval) }
            nextDrawAt = t
        }

        let nextDrawNumber: Int? = {
            if let n = next?.drawNumber { return n }
            guard let last, let nextDrawAt, let lastDate = Zurich.parseISO(last.drawDate) else {
                return last.map { $0.drawNumber + 1 }
            }
            let steps = Int((nextDrawAt.timeIntervalSince(lastDate) / interval).rounded())
            return last.drawNumber + max(1, steps)
        }()

        let hole = last != nil && nextDrawNumber != nil && nextDrawNumber! > last!.drawNumber + 1
        return Clock(
            last: last,
            nextDrawAt: nextDrawAt,
            nextDrawNumber: nextDrawNumber,
            wagerEndAt: next.flatMap { Zurich.parseISO($0.wagerEndDate ?? "") } ?? nextDrawAt,
            hole: hole,
            pendingDrawNumber: hole ? last!.drawNumber + 1 : nil,
            phase: next?.phase
        )
    }

    static func pollDelay(nextDrawAt: Date?, hole: Bool, now: Date = Date()) -> TimeInterval {
        if hole { return 1 }
        guard let nextDrawAt else { return 8 }
        let ms = nextDrawAt.timeIntervalSince(now)
        if ms < 12 { return 1 }
        if ms < 45 { return 2 }
        if ms < 360 { return 5 }
        return 12
    }

    static func cacheTtl(nextDrawAt: Date?, hole: Bool, now: Date = Date()) -> TimeInterval {
        if hole { return 0.8 }
        guard let nextDrawAt else { return 4 }
        return nextDrawAt.timeIntervalSince(now) < 20 ? 0.8 : 4
    }
}
