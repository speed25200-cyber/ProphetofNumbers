import XCTest
@testable import Prophet

final class OracleTests: XCTestCase {
    func syntheticHistory(count: Int = 80) -> [Draw] {
        var draws: [Draw] = []
        var seed: UInt64 = 20260824
        func next() -> UInt64 {
            seed = seed &* 6364136223846793005 &+ 1
            return seed
        }
        for i in 1...count {
            var set = Set<Int>()
            while set.count < 20 {
                let n = Int(next() % 80) + 1
                set.insert(n)
            }
            draws.append(Draw(
                drawNumber: 10_000 + i,
                drawDate: "2026-08-24T12:00:00+02:00",
                numbers: set.sorted(),
                boost: Int(next() % 5) + 2,
                bonus: Int(next() % 80) + 1
            ))
        }
        return draws.reversed()
    }

    func testSwarmProducesFullField() {
        let result = Swarm.run(syntheticHistory())
        XCTAssertEqual(result.scores.count, 80)
        XCTAssertEqual(result.ranks.count, 80)
        XCTAssertEqual(Set(result.ranks).count, 80)
        XCTAssertEqual(result.stakes.count, 5)
        XCTAssertGreaterThanOrEqual(result.confidence, 5)
        XCTAssertLessThanOrEqual(result.confidence, 95)
        XCTAssertEqual(result.sampleSize, 80)
        XCTAssertEqual(result.gaps.count, 80)
        XCTAssertEqual(result.freq16.count, 80)
    }

    func testSwarmHeadsAndWeights() {
        let result = Swarm.run(syntheticHistory())
        XCTAssertEqual(result.methods.count, result.swarm.headCount)
        XCTAssertGreaterThanOrEqual(result.swarm.headCount, 20)
        // Les identifiants des têtes restent uniques après évolution.
        XCTAssertEqual(Set(result.methods.map(\.id)).count, result.methods.count)
        // Les poids Hedge forment une distribution.
        let total = result.methods.map(\.weight).reduce(0, +)
        XCTAssertEqual(total, 1.0, accuracy: 0.001)
        XCTAssertTrue(result.methods.allSatisfy { $0.weight > 0 })
        // L'entropie des poids est bornée par la taille de l'essaim.
        XCTAssertGreaterThanOrEqual(result.swarm.effectiveHeads, 1)
        XCTAssertLessThanOrEqual(result.swarm.effectiveHeads, Double(result.swarm.headCount) + 0.001)
        XCTAssertFalse(result.swarm.families.isEmpty)
        let famHeads = result.swarm.families.map(\.heads).reduce(0, +)
        XCTAssertEqual(famHeads, result.swarm.headCount)
    }

    func testBacktestIsWalkForward() {
        let result = Swarm.run(syntheticHistory())
        // Évaluation à partir du 14e tirage : 80 - 13 points.
        XCTAssertEqual(result.backtest.count, 67)
        XCTAssertTrue(result.backtest.allSatisfy { (0...20).contains($0) })
        XCTAssertEqual(result.uniformExpected, 5.0, accuracy: 0.0001)
        XCTAssertGreaterThanOrEqual(result.backtestMean, 0)
        XCTAssertLessThanOrEqual(result.backtestMean, 20)
        // Sur un historique pseudo-aléatoire, la moyenne doit rester proche du hasard.
        XCTAssertEqual(result.backtestMean, 5.0, accuracy: 2.0)
        // E-valeur : strictement positive, et pas d'alerte attendue sur du hasard.
        XCTAssertGreaterThan(result.eValue, 0)
        XCTAssertLessThan(result.eValue, 20)
        // Géométrie : 142 arêtes × 20·19/(80·79) ≈ 8,54 paires attendues.
        XCTAssertEqual(result.adjacencyExpected, 8.538, accuracy: 0.01)
        XCTAssertGreaterThanOrEqual(result.adjacencyMean, 0)
        XCTAssertTrue(result.adjacencyZ.isFinite)
    }

    func testSwarmIsDeterministic() {
        let history = syntheticHistory()
        let a = Swarm.run(history)
        let b = Swarm.run(history)
        XCTAssertEqual(a.scores, b.scores)
        XCTAssertEqual(a.backtest, b.backtest)
        XCTAssertEqual(a.confidence, b.confidence)
        XCTAssertEqual(a.eValue, b.eValue)
        XCTAssertEqual(a.swarm.generation, b.swarm.generation)
        XCTAssertEqual(a.methods.map(\.weight), b.methods.map(\.weight))
        for (ga, gb) in zip(a.stakes, b.stakes) {
            XCTAssertEqual(ga.grids.map(\.numbers), gb.grids.map(\.numbers))
        }
    }

    func testGridsHaveCorrectCardinality() {
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            XCTAssertEqual(pack.grids.count, 3)
            for grid in pack.grids {
                XCTAssertEqual(grid.numbers.count, pack.stake)
                XCTAssertEqual(Set(grid.numbers).count, pack.stake)
                XCTAssertTrue(grid.numbers.allSatisfy { (1...80).contains($0) })
                XCTAssertEqual(grid.numbers, grid.numbers.sorted())
            }
        }
    }

    func testHitsInDraw() {
        let draw = Draw(drawNumber: 1, drawDate: "2026-08-24T12:00:00+02:00", numbers: [1, 2, 3, 4, 5], boost: nil, bonus: nil)
        XCTAssertEqual(Hits.inDraw([1, 9, 3], draw), 2)
        XCTAssertEqual(Hits.inDraw([10, 11], draw), 0)
    }

    func testEmptyHistoryIsStable() {
        let result = Swarm.run([])
        XCTAssertEqual(result.scores.count, 80)
        XCTAssertEqual(result.sampleSize, 0)
        XCTAssertEqual(result.stakes[0].grids[0].numbers.count, 5)
        XCTAssertTrue(result.backtest.isEmpty)
        XCTAssertEqual(result.confidence, 50)
        // Sans tirage, la martingale n'a pas parié : richesse neutre.
        XCTAssertEqual(result.eValue, 1.0, accuracy: 0.0001)
        XCTAssertEqual(result.swarm.generation, 0)
        XCTAssertEqual(result.swarm.bestHeadName, "—")
    }

    func testScheduleResolvePicksOpenSlot() {
        let now = Zurich.parseISO("2026-08-25T12:00:00+02:00")!
        let slots = [
            Schedule.Slot(
                drawNumber: 100, drawDate: "2026-08-25T11:55:00+02:00",
                numbers: Array(1...20), boost: nil, bonus: nil,
                phase: "RESULTS_AVAILABLE", wagerEndDate: nil
            ),
            Schedule.Slot(
                drawNumber: 101, drawDate: "2026-08-25T12:05:00+02:00",
                numbers: [], boost: nil, bonus: nil,
                phase: "OPEN", wagerEndDate: "2026-08-25T12:04:30+02:00"
            ),
        ]
        let clock = Schedule.resolve(
            slots: slots, fallbackNext: nil, fallbackNextRaw: nil, fallbackLast: nil, now: now
        )
        XCTAssertEqual(clock.last?.drawNumber, 100)
        XCTAssertEqual(clock.nextDrawNumber, 101)
        XCTAssertFalse(clock.hole)
        XCTAssertNil(clock.pendingDrawNumber)
        XCTAssertNotNil(clock.wagerEndAt)
        XCTAssertEqual(clock.nextDrawAt, Zurich.parseISO("2026-08-25T12:05:00+02:00"))
    }

    func testScheduleDetectsHole() {
        let now = Zurich.parseISO("2026-08-25T12:01:00+02:00")!
        let slots = [
            Schedule.Slot(
                drawNumber: 100, drawDate: "2026-08-25T11:55:00+02:00",
                numbers: Array(1...20), boost: nil, bonus: nil,
                phase: "RESULTS_AVAILABLE", wagerEndDate: nil
            ),
            // Le résultat du 101 n'est pas encore publié : le prochain ouvert est 102.
            Schedule.Slot(
                drawNumber: 102, drawDate: "2026-08-25T12:05:00+02:00",
                numbers: [], boost: nil, bonus: nil,
                phase: "OPEN", wagerEndDate: nil
            ),
        ]
        let clock = Schedule.resolve(
            slots: slots, fallbackNext: nil, fallbackNextRaw: nil, fallbackLast: nil, now: now
        )
        XCTAssertEqual(clock.last?.drawNumber, 100)
        XCTAssertEqual(clock.nextDrawNumber, 102)
        XCTAssertTrue(clock.hole)
        XCTAssertEqual(clock.pendingDrawNumber, 101)
    }

    func testScheduleLocksOntoFollowingDrawNearClose() {
        // À 10 s du tirage (≤ lockAhead), la cible jouable saute au suivant.
        let now = Zurich.parseISO("2026-08-25T12:04:50+02:00")!
        let slots = [
            Schedule.Slot(
                drawNumber: 100, drawDate: "2026-08-25T12:00:00+02:00",
                numbers: Array(1...20), boost: nil, bonus: nil,
                phase: "RESULTS_AVAILABLE", wagerEndDate: nil
            ),
            Schedule.Slot(
                drawNumber: 101, drawDate: "2026-08-25T12:05:00+02:00",
                numbers: [], boost: nil, bonus: nil,
                phase: "OPEN", wagerEndDate: nil
            ),
            Schedule.Slot(
                drawNumber: 102, drawDate: "2026-08-25T12:10:00+02:00",
                numbers: [], boost: nil, bonus: nil,
                phase: "OPEN", wagerEndDate: "2026-08-25T12:09:30+02:00"
            ),
        ]
        let clock = Schedule.resolve(
            slots: slots, fallbackNext: nil, fallbackNextRaw: nil, fallbackLast: nil, now: now
        )
        XCTAssertEqual(clock.nextDrawNumber, 102)
        XCTAssertEqual(clock.nextDrawAt, Zurich.parseISO("2026-08-25T12:10:00+02:00"))
        XCTAssertTrue(clock.hole)
        XCTAssertEqual(clock.pendingDrawNumber, 101)
    }

    func testSchedulePollDelayTiers() {
        let now = Date(timeIntervalSince1970: 1_000_000)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(400), hole: false, now: now), 12)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(300), hole: false, now: now), 5)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(40), hole: false, now: now), 2)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(5), hole: false, now: now), 1)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(400), hole: true, now: now), 1)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: nil, hole: false, now: now), 8)
    }

    func testCountdownIsCeiledAndAnchored() {
        let target = Date(timeIntervalSince1970: 1_000_000)
        // 4,2 s restantes → afficher 05, pas 04.
        let a = Format.countdown(to: target, now: target.addingTimeInterval(-4.2))
        XCTAssertEqual(a.label, "00:05")
        XCTAssertTrue(a.urgent)
        // Pile 60 s → 01:00.
        let b = Format.countdown(to: target, now: target.addingTimeInterval(-60))
        XCTAssertEqual(b.label, "01:00")
        XCTAssertFalse(b.urgent)
        // Échu → tirage en cours.
        let c = Format.countdown(to: target, now: target.addingTimeInterval(1))
        XCTAssertEqual(c.label, "Tirage en cours")
        XCTAssertTrue(c.urgent)
    }

    func testZurichDayKey() {
        let date = Zurich.parseISO("2026-08-24T23:30:00+02:00")
        XCTAssertNotNil(date)
        XCTAssertEqual(Zurich.parts(date!).dayKey, "2026-08-24")
    }
}
