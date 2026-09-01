import XCTest
@testable import Prophet

final class DrawRevealTests: XCTestCase {
    func testDrawRevealsGradually() {
        let n = DrawReveal.visibleCount(scene: "DrawScene", startTime: 0, progress: 0, ballCount: 20)
        XCTAssertEqual(n, 0)
        let mid = DrawReveal.visibleCount(scene: "DrawScene", startTime: 0, progress: 12_000, ballCount: 20)
        XCTAssertEqual(mid, 2)
        let full = DrawReveal.visibleCount(scene: "DrawScene", startTime: 0, progress: 200_000, ballCount: 20)
        XCTAssertEqual(full, 20)
    }

    func testResultsShowsAll() {
        let n = DrawReveal.visibleCount(scene: "ResultsScene", startTime: 0, progress: 0, ballCount: 20)
        XCTAssertEqual(n, 20)
    }
}
