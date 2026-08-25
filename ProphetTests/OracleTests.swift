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

    func testZurichDayKey() {
        let date = Zurich.parseISO("2026-08-24T23:30:00+02:00")
        XCTAssertNotNil(date)
        XCTAssertEqual(Zurich.parts(date!).dayKey, "2026-08-24")
    }
}
