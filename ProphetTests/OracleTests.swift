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

    func testOracleProducesFullField() {
        let result = Oracle.run(syntheticHistory())
        XCTAssertEqual(result.scores.count, 80)
        XCTAssertEqual(result.ranks.count, 80)
        XCTAssertEqual(Set(result.ranks).count, 80)
        XCTAssertEqual(result.methods.count, 6)
        XCTAssertEqual(result.stakes.count, 5)
        XCTAssertGreaterThanOrEqual(result.confidence, 18)
        XCTAssertLessThanOrEqual(result.confidence, 86)
        XCTAssertEqual(result.sampleSize, 80)
    }

    func testGridsHaveCorrectCardinality() {
        let result = Oracle.run(syntheticHistory())
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
        let result = Oracle.run([])
        XCTAssertEqual(result.scores.count, 80)
        XCTAssertEqual(result.sampleSize, 0)
        XCTAssertEqual(result.stakes[0].grids[0].numbers.count, 5)
    }

    func testZurichDayKey() {
        let date = Zurich.parseISO("2026-08-24T23:30:00+02:00")
        XCTAssertNotNil(date)
        XCTAssertEqual(Zurich.parts(date!).dayKey, "2026-08-24")
    }

    func testSlotRequiresExactlyTwentyUniqueNumbers() {
        let valid = Schedule.Slot(
            drawNumber: 1,
            drawDate: "2026-09-04T06:05:00+02:00",
            numbers: Array(1...20),
            boost: 2,
            bonus: 1
        )
        XCTAssertTrue(valid.isComplete)

        var partial = valid
        partial.numbers = Array(1...19)
        XCTAssertFalse(partial.isComplete)

        var duplicate = valid
        duplicate.numbers[19] = 1
        XCTAssertFalse(duplicate.isComplete)
    }
}
