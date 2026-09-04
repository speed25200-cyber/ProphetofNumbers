import Foundation
import XCTest
@testable import Prophet

final class OracleTests: XCTestCase {
    private func parsedRestSlot(main: Any, drawNumber: Any = 42) -> Schedule.Slot? {
        let matrix: [String: Any] = [
            "main": main,
            "boost": [2],
            "bonus": [80],
        ]
        let result: [String: Any] = ["matrix1": matrix]
        return LoroClient.shared.parseSlot([
            "drawNumber": drawNumber,
            "drawDate": "2026-09-04T06:05:00+02:00",
            "drawResult": result,
        ])
    }

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

    func testRestParserSortsExactlyTwentyScalarsWithoutInventingOrder() throws {
        let slot = try XCTUnwrap(parsedRestSlot(main: Array((1...20).reversed())))
        XCTAssertEqual(slot.numbers, Array(1...20))
        XCTAssertNil(slot.drawOrder)
        XCTAssertTrue(slot.isComplete)
        XCTAssertEqual(slot.boost, 2)
        XCTAssertEqual(slot.bonus, 80)
    }

    func testRestParserKeepsOnlyAnExplicitCompletePositionOrder() throws {
        let order = [20] + Array(1...19)
        let positioned: [[String: Any]] = order.enumerated().map { index, number in
            ["number": number, "position": index]
        }
        let slot = try XCTUnwrap(parsedRestSlot(main: positioned))
        XCTAssertEqual(slot.numbers, Array(1...20))
        XCTAssertEqual(slot.drawOrder, order)
        XCTAssertTrue(slot.isComplete)
    }

    func testRestParserRejectsWrongCardinalityDuplicatesAndInvalidElements() throws {
        let prefix = Array(1...19).map { $0 as Any }
        let malformed: [[Any]] = [
            Array(1...19).map { $0 as Any },
            Array(1...21).map { $0 as Any },
            Array(1...20).map { $0 as Any } + ["bad"],
            Array(1...20).map { $0 as Any } + [20],
            prefix + [19],
            prefix + [0],
            prefix + [81],
            prefix + [true],
        ]

        for main in malformed {
            let slot = try XCTUnwrap(parsedRestSlot(main: main))
            XCTAssertEqual(slot.numbers, [], "accepted malformed main selection: \(main)")
            XCTAssertFalse(slot.isComplete)
        }
    }

    func testRestParserRejectsFractionalAndNonFiniteNumbers() throws {
        let prefix = Array(1...19).map { $0 as Any }
        let invalidNumbers: [Any] = [
            20.5,
            NSNumber(value: 20.5),
            Double.nan,
            Double.infinity,
            -Double.infinity,
            NSNumber(value: Double.nan),
            NSNumber(value: Double.infinity),
        ]

        for invalid in invalidNumbers {
            let slot = try XCTUnwrap(parsedRestSlot(main: prefix + [invalid]))
            XCTAssertEqual(slot.numbers, [])
            XCTAssertFalse(slot.isComplete)
        }

        XCTAssertNil(parsedRestSlot(main: Array(1...20), drawNumber: 42.5))
        XCTAssertNil(parsedRestSlot(main: Array(1...20), drawNumber: NSNumber(value: Double.nan)))
        XCTAssertEqual(
            parsedRestSlot(
                main: Array(1...20),
                drawNumber: NSNumber(value: Int64(9_007_199_254_740_993))
            )?.drawNumber,
            9_007_199_254_740_993
        )
        XCTAssertNil(parsedRestSlot(
            main: Array(1...20),
            drawNumber: NSNumber(value: UInt64.max)
        ))
        XCTAssertNil(parsedRestSlot(
            main: Array(1...20),
            drawNumber: "9007199254740993.5"
        ))
        XCTAssertEqual(
            parsedRestSlot(
                main: Array(1...20),
                drawNumber: "9007199254740993.0"
            )?.drawNumber,
            9_007_199_254_740_993
        )

        let integral = try XCTUnwrap(parsedRestSlot(
            main: Array(1...19).map { $0 as Any } + [NSNumber(value: 20.0)],
            drawNumber: "42.0"
        ))
        XCTAssertEqual(integral.drawNumber, 42)
        XCTAssertTrue(integral.isComplete)
    }

    func testCachePreservesOrderOnlyForTheSameDrawAndNumberSet() {
        let numbers = Array(1...20)
        let order = [20] + Array(1...19)
        let previous = Draw(
            drawNumber: 42,
            drawDate: "2026-09-04T06:05:00+02:00",
            numbers: numbers,
            boost: 2,
            bonus: 80,
            drawOrder: order
        )
        let refresh = Draw(
            drawNumber: 42,
            drawDate: previous.drawDate,
            numbers: numbers,
            boost: 2,
            bonus: 80
        )

        XCTAssertEqual(
            LoroClient.mergingForCache(refresh, previous: previous).drawOrder,
            order
        )

        var corrected = refresh
        corrected.numbers = Array(1...19) + [21]
        XCTAssertNil(LoroClient.mergingForCache(corrected, previous: previous).drawOrder)

        var otherDraw = refresh
        otherDraw.drawNumber = 43
        XCTAssertNil(LoroClient.mergingForCache(otherDraw, previous: previous).drawOrder)

        var invalidPrevious = previous
        invalidPrevious.drawOrder = [1] + Array(1...19)
        XCTAssertNil(LoroClient.mergingForCache(refresh, previous: invalidPrevious).drawOrder)

        var invalidIncoming = refresh
        invalidIncoming.drawOrder = Array(2...21)
        XCTAssertNil(LoroClient.mergingForCache(invalidIncoming, previous: previous).drawOrder)
    }
}
