import XCTest
@testable import Prophet

final class OracleTests: XCTestCase {
    // Source « équitable » de référence des tests : tout ce qui suit
    // suppose que cet historique est indiscernable du hasard.
    //
    // Les bits de POIDS FORT du LCG, jamais `seed % 80`. Dans un LCG
    // modulo 2^64, le bit k a une période de 2^(k+1) : le quartet de
    // poids faible se répète toutes les 16 valeurs. Comme 80 = 16 × 5,
    // `seed % 80` hérite directement de ce cycle de 16 et l'historique
    // « aléatoire » porte alors une structure réelle. Elle est invisible
    // sur les moyennes (recouvrement moyen entre tirages : 4,996 contre
    // 5,000 en théorie) mais gonfle la queue haute, précisément ce que
    // regarde l'anti-rejeu : sur 1 000 graines, dupMax montait à 14-15 et
    // `duplicateAlert` se déclenchait sur 1,7 % d'entre elles — dont
    // 20260824, la graine par défaut, d'où l'échec CI de
    // testBacktestIsWalkForward. Le détecteur avait raison ; c'est le
    // montage de test qui n'était pas aléatoire.
    //
    // Avec `>> 33`, sur les mêmes 1 000 graines : dupMax plafonne à 13 et
    // le taux d'alerte tombe à 0 %. Même convention que la source
    // équitable de testAnalogueTestStaysSilentOnAFairSource.
    func syntheticHistory(count: Int = 80, seed initialSeed: UInt64 = 20260824) -> [Draw] {
        var draws: [Draw] = []
        var seed: UInt64 = initialSeed
        func next() -> UInt64 {
            seed = seed &* 6364136223846793005 &+ 1
            return seed >> 33
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
        // Anti-rejeu : recouvrement plausible sur du hasard, aucune alerte.
        // Le taux, plutôt que cette seule graine, est vérifié par
        // testDuplicateAlertIsCalibrated.
        XCTAssertTrue((0...20).contains(result.duplicateMax))
        XCTAssertGreaterThanOrEqual(result.duplicateMax, 5)
        XCTAssertFalse(result.duplicateAlert)
    }

    // MARK: Écho du bonus (23ᵉ voie du labo)

    func testBonusEchoTargetsThePreviousBonus() {
        // Le câblage vise-t-il le bon numéro ? C'est le bonus du tirage le
        // plus récent, pas celui d'un tirage quelconque de l'historique.
        let history = syntheticHistory()
        let result = Swarm.run(history)
        XCTAssertEqual(result.bonusEcho, history.first?.bonus)
        XCTAssertNotNil(result.bonusEcho)
    }

    func testBonusEchoPenalisesOnATie() {
        // Témoin POSITIF : sur un champ plat, le départage doit faire tomber
        // le bonus précédent en dernier. Sans cela le mécanisme serait
        // indistinguable d'un mécanisme cassé.
        let flat = [Double](repeating: 1.0, count: 80)
        let adjusted = SwarmEngine.applyBonusEcho(flat, bonus: 42)
        XCTAssertEqual(adjusted.firstIndex(of: adjusted.min()!), 41)
        for (i, v) in adjusted.enumerated() where i != 41 {
            XCTAssertEqual(v, 1.0, accuracy: 1e-12)
        }
        XCTAssertEqual(adjusted[41], 1.0 - SwarmEngine.bonusEchoRelative, accuracy: 1e-12)
    }

    func testBonusEchoIsInertWithoutABonus() {
        // Témoin NÉGATIF : sans bonus connu, ou hors du champ 1–80, le
        // départage ne doit toucher à rien.
        let field = (0..<80).map { Double($0) * 0.1 }
        XCTAssertEqual(SwarmEngine.applyBonusEcho(field, bonus: nil), field)
        XCTAssertEqual(SwarmEngine.applyBonusEcho(field, bonus: 0), field)
        XCTAssertEqual(SwarmEngine.applyBonusEcho(field, bonus: 81), field)
        // Champ de mauvaise taille : inerte plutôt que fautif.
        XCTAssertEqual(SwarmEngine.applyBonusEcho([1.0, 2.0], bonus: 1), [1.0, 2.0])
    }

    func testBonusEchoIsSizedAsATieBreak() {
        // Le point qui compte : l'écart mesuré vaut +0,02 % d'avantage
        // exploitable. Il doit donc trancher une égalité et RIEN de plus.
        // Un écart de score franc ne doit pas bouger, sinon on aurait
        // transformé deux centièmes de pourcent en coefficient de décision.
        XCTAssertEqual(SwarmEngine.bonusEchoRelative,
                       SwarmEngine.bonusEchoDeficit / ProphetConst.baseP,
                       accuracy: 1e-4,
                       "le départage doit rester la traduction du déficit mesuré")
        XCTAssertLessThan(SwarmEngine.bonusEchoRelative, 0.05,
                          "au-delà, ce n'est plus un départage mais une pondération")

        var field = [Double](repeating: 0, count: 80)
        field[41] = 0.10                      // le bonus précédent mène nettement
        let adjusted = SwarmEngine.applyBonusEcho(field, bonus: 42)
        XCTAssertEqual(adjusted.firstIndex(of: adjusted.max()!), 41,
                       "un écart franc doit survivre au départage")
    }

    func testBonusEchoLeavesGridsValid() {
        // Le départage ne doit rien casser en aval : cardinalité, unicité et
        // bornes des grilles restent celles que teste déjà la suite.
        let result = Swarm.run(syntheticHistory())
        guard let echo = result.bonusEcho else { return XCTFail("écho absent") }
        XCTAssertTrue((1...80).contains(echo))
        for pack in result.stakes {
            for grid in pack.grids {
                XCTAssertEqual(grid.numbers.count, pack.stake)
                XCTAssertEqual(Set(grid.numbers).count, pack.stake)
                XCTAssertTrue(grid.numbers.allSatisfy { (1...80).contains($0) })
            }
        }
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
            XCTAssertEqual(pack.grids.count, 12)
            for grid in pack.grids {
                XCTAssertEqual(grid.numbers.count, pack.stake)
                XCTAssertEqual(Set(grid.numbers).count, pack.stake)
                XCTAssertTrue(grid.numbers.allSatisfy { (1...80).contains($0) })
                XCTAssertEqual(grid.numbers, grid.numbers.sorted())
            }
            for kind in GridKind.allCases {
                let variants = pack.grids.filter { $0.kind == kind }
                XCTAssertEqual(variants.count, 4)
                // I et II sont disjointes ; l'Anti joue le bas du classement,
                // donc ne recoupe pas la sélection principale.
                let one = variants.first { $0.variant == 1 }!
                let two = variants.first { $0.variant == 2 }!
                let anti = variants.first { $0.variant == 3 }!
                XCTAssertTrue(Set(one.numbers).isDisjoint(with: Set(two.numbers)))
                XCTAssertTrue(Set(one.numbers).isDisjoint(with: Set(anti.numbers)))
            }
            // Identifiants uniques (I, II et Anti ne se confondent pas).
            XCTAssertEqual(Set(pack.grids.map(\.id)).count, 12)
        }
    }

    func testGridPackIsSpreadAcrossTheField() {
        // Audit `lab/experiments/e1_audit_grilles.py` : le paquet dupliquait
        // ses grilles (30 numéros couverts sur 80 à la mise 5, pour 60
        // emplacements) et perdait 24,8 % de P(au moins une grille pleine).
        // La préférence de couverture doit désormais atteindre le maximum
        // possible : douze grilles de k couvrent min(12k, 80) numéros.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            let all = pack.grids.flatMap(\.numbers)
            let distinct = Set(all).count
            XCTAssertEqual(distinct, min(12 * pack.stake, 80),
                           "mise \(pack.stake) : couverture non maximale")

            var cover = [Int](repeating: 0, count: 81)
            for n in all { cover[n] += 1 }
            let maxCover = cover.max() ?? 0
            let ceiling = (12 * pack.stake + 79) / 80
            XCTAssertLessThanOrEqual(maxCover, ceiling,
                                     "mise \(pack.stake) : un numéro est repris \(maxCover) fois")
        }
    }

    func testGridPackHasNoNearDuplicatePair() {
        // Le défaut mesuré était que « Furtif » reprenait 4 numéros sur 5 de
        // la variante I, et que l'Anti d'une famille était la principale
        // d'une autre (alpha et omega sont anti-corrélées à −0,70). Aucune
        // paire de grilles ne doit plus se recouvrir au-delà de ce que la
        // place impose.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            // Aucune paire ne doit partager plus de la moitié de sa grille.
            // Sous l'ancienne géométrie, Furtif reprenait 4 numéros sur 5 de
            // la variante I — ce seuil l'aurait attrapé.
            let ceiling = pack.stake / 2
            for i in 0..<pack.grids.count {
                for j in (i + 1)..<pack.grids.count {
                    let common = Set(pack.grids[i].numbers)
                        .intersection(pack.grids[j].numbers).count
                    XCTAssertLessThanOrEqual(
                        common, ceiling,
                        "mise \(pack.stake) : \(pack.grids[i].label) et "
                        + "\(pack.grids[j].label) partagent \(common) numéros")
                }
            }
        }
    }

    func testSpreadDoesNotTouchTheExpectation() {
        // Témoin : étaler change la FORME de la loi, jamais son espérance.
        // Chaque grille reste un k-sous-ensemble, donc son espérance de hits
        // vaut k/4 quel que soit son contenu — c'est ce que l'affichage
        // « HASARD » doit continuer de dire.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            for grid in pack.grids {
                XCTAssertEqual(grid.baseExpected, Double(pack.stake) * 0.25, accuracy: 1e-12)
            }
        }
    }

    func testIncrementalEngineMatchesFullRebuild() {
        let history = syntheticHistory() // du plus récent au plus ancien
        let full = Swarm.run(history)
        let engine = SwarmEngine()
        // Les 60 tirages les plus anciens d'abord, puis le reste en incrémental.
        _ = engine.update(Array(history.suffix(60)))
        let incremental = engine.update(history)
        XCTAssertEqual(incremental.scores, full.scores)
        XCTAssertEqual(incremental.backtest, full.backtest)
        XCTAssertEqual(incremental.confidence, full.confidence)
        XCTAssertEqual(incremental.eValue, full.eValue)
        XCTAssertEqual(incremental.duplicateMax, full.duplicateMax)
        XCTAssertEqual(incremental.swarm.generation, full.swarm.generation)
        XCTAssertEqual(incremental.methods.map(\.weight), full.methods.map(\.weight))
        for (ga, gb) in zip(incremental.stakes, full.stakes) {
            XCTAssertEqual(ga.grids.map(\.numbers), gb.grids.map(\.numbers))
        }
        XCTAssertEqual(incremental.movers.map(\.number), full.movers.map(\.number))
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
        XCTAssertEqual(result.duplicateMax, 0)
        XCTAssertFalse(result.duplicateAlert)
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
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(15), hole: false, now: now), 0.4)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(5), hole: false, now: now), 0.1)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: now.addingTimeInterval(400), hole: true, now: now), 0.1)
        XCTAssertEqual(Schedule.pollDelay(nextDrawAt: nil, hole: false, now: now), 8)
        // Le Turbo est partout au moins aussi rapide que la cadence normale.
        for secs in [400.0, 300, 40, 15, 5] {
            let at = now.addingTimeInterval(secs)
            XCTAssertLessThanOrEqual(
                Schedule.turboDelay(nextDrawAt: at, hole: false, now: now),
                Schedule.pollDelay(nextDrawAt: at, hole: false, now: now)
            )
        }
        XCTAssertEqual(Schedule.turboDelay(nextDrawAt: now.addingTimeInterval(5), hole: false, now: now), 0.08)
        XCTAssertEqual(Schedule.turboDelay(nextDrawAt: now.addingTimeInterval(400), hole: true, now: now), 0.08)
    }

    func testDayReplayJournalsEveryEvaluableDraw() {
        let history = syntheticHistory()
        let journal = SwarmEngine.replayToday(history, stake: 10)
        XCTAssertEqual(journal.stake, 10)
        // Tous les tirages du jour dès que le modèle a 13 tirages d'amorce.
        XCTAssertEqual(journal.plays.count, 67)
        for play in journal.plays {
            XCTAssertEqual(play.plays.count, 12)
            XCTAssertEqual(play.draw.count, 20)
            for gp in play.plays {
                XCTAssertEqual(gp.numbers.count, 10)
                XCTAssertTrue((0...10).contains(gp.hits))
                // Le hit est bien le recouvrement réel grille/tirage.
                XCTAssertEqual(gp.hits, gp.numbers.filter(Set(play.draw).contains).count)
            }
        }
        // Chronologique, et déterministe.
        XCTAssertEqual(journal.plays.map(\.drawNumber), journal.plays.map(\.drawNumber).sorted())
        let again = SwarmEngine.replayToday(history, stake: 10)
        XCTAssertEqual(again.plays, journal.plays)
    }

    func testDayReplayHoldsPredictionAcrossThreeDraws() {
        let history = syntheticHistory()
        let journal = SwarmEngine.replayToday(history, stake: 10, hold: 3)
        XCTAssertEqual(journal.hold, 3)
        XCTAssertEqual(journal.plays.count, 67)
        // La même grille est tenue sur des blocs de 3 tirages consécutifs.
        for (idx, play) in journal.plays.enumerated() {
            let blockStart = (idx / 3) * 3
            XCTAssertEqual(
                play.plays.map(\.numbers),
                journal.plays[blockStart].plays.map(\.numbers)
            )
        }
        // Les hits restent le vrai recouvrement grille/tirage.
        for play in journal.plays {
            for gp in play.plays {
                XCTAssertEqual(gp.hits, gp.numbers.filter(Set(play.draw).contains).count)
            }
        }
        // Les autres formules tiennent aussi la grille sur leur bloc.
        for hold in [2, 5, 10] {
            let jh = SwarmEngine.replayToday(history, stake: 10, hold: hold)
            XCTAssertEqual(jh.hold, hold)
            XCTAssertEqual(jh.plays.count, 67)
            for (idx, play) in jh.plays.enumerated() {
                let blockStart = (idx / hold) * hold
                XCTAssertEqual(
                    play.plays.map(\.numbers),
                    jh.plays[blockStart].plays.map(\.numbers)
                )
            }
        }
    }

    func testForensicsReportIsWellFormed() {
        let report = Forensics.run(syntheticHistory(count: 200))
        XCTAssertEqual(report.tests.count, 8)
        XCTAssertEqual(report.sampleSize, 200)
        XCTAssertTrue(report.tests.allSatisfy { $0.sigma.isFinite && $0.sigma >= 0 })
        // Classé du plus suspect au moins suspect.
        XCTAssertEqual(report.tests.map(\.sigma), report.tests.map(\.sigma).sorted(by: >))
        // Déterministe.
        let again = Forensics.run(syntheticHistory(count: 200))
        XCTAssertEqual(again.tests.map(\.statistic), report.tests.map(\.statistic))
        // Échantillon trop court : pas de verdict.
        let short = Forensics.run(syntheticHistory(count: 20))
        XCTAssertTrue(short.tests.isEmpty)
        XCTAssertEqual(short.flagged, 0)
    }

    func testForensicsCatchesABrokenSource() {
        // Témoin positif : source de période 3 (le bug Corriveau caricaturé).
        let cycle = [Array(1...20), Array(21...40), Array(41...60)]
        var draws: [Draw] = []
        for i in 1...120 {
            draws.append(Draw(
                drawNumber: 20_000 + i,
                drawDate: "2026-08-24T12:00:00+02:00",
                numbers: cycle[i % 3],
                boost: nil,
                bonus: nil
            ))
        }
        let report = Forensics.run(draws.reversed())
        XCTAssertGreaterThan(report.flagged, 0)
        XCTAssertTrue(report.tests.contains { $0.name == "Périodicité" && $0.flagged })
        XCTAssertTrue(report.tests.contains { $0.name == "Uniformité du champ" && $0.flagged })
    }

    func testAnalogueTestCatchesASmallStateSource() {
        // Témoin positif du 8e test : un générateur dont l'état tient sur
        // 12 bits revisite ses états dans la fenêtre observée, donc la
        // méthode des analogues doit le voir — sans qu'on lui ait dit
        // qu'il s'agissait d'un LCG.
        var s = 1234
        func nextDraw() -> [Int] {
            var seen: [Int] = []
            var guardCount = 0
            while seen.count < 20 && guardCount < 100_000 {
                s = (2045 * s + 1) % 4096
                let v = (s >> 4) % 80 + 1
                if !seen.contains(v) { seen.append(v) }
                guardCount += 1
            }
            return seen.sorted()
        }
        var draws: [Draw] = []
        for i in 1...400 {
            draws.append(Draw(
                drawNumber: 30_000 + i,
                drawDate: "2026-08-24T12:00:00+02:00",
                numbers: nextDraw(), boost: nil, bonus: nil
            ))
        }
        let report = Forensics.run(draws.reversed())
        let test = report.tests.first { $0.name == "Reconstruction par analogues" }
        XCTAssertNotNil(test)
        XCTAssertTrue(test!.flagged, "un état de 12 bits doit être vu par les analogues")
        XCTAssertGreaterThan(test!.sigma, 5)
    }

    func testAnalogueTestStaysSilentOnAFairSource() {
        // Témoin négatif : une source sans état revisitable ne doit pas
        // déclencher le test, sinon il ne vaut rien.
        var rngState: UInt64 = 0xDEAD_BEEF_CAFE_1234
        func next() -> UInt64 {
            rngState ^= rngState << 13
            rngState ^= rngState >> 7
            rngState ^= rngState << 17
            return rngState
        }
        var draws: [Draw] = []
        for i in 1...400 {
            var set = Set<Int>()
            while set.count < 20 { set.insert(Int((next() >> 33) % 80) + 1) }
            draws.append(Draw(
                drawNumber: 40_000 + i,
                drawDate: "2026-08-24T12:00:00+02:00",
                numbers: set.sorted(), boost: nil, bonus: nil
            ))
        }
        let report = Forensics.run(draws.reversed())
        let test = report.tests.first { $0.name == "Reconstruction par analogues" }
        XCTAssertNotNil(test)
        XCTAssertFalse(test!.flagged, "xorshift128 64 bits est hors de portée : aucun signal attendu")
    }

    func testDuplicateAlertIsCalibrated() {
        // Garde-fou de la régression CI qui faisait tomber
        // testBacktestIsWalkForward : `duplicateAlert` se déclenchait sur
        // la graine par défaut parce que syntheticHistory tirait les bits
        // de poids faible du LCG (cf. son commentaire). Un XCTAssertFalse
        // sur UNE graine fixe ne distingue pas « le détecteur est calibré »
        // de « cette graine a de la chance » ; le taux sur plusieurs
        // graines, si.
        //
        // La formule est une borne d'union à 1 % : sur une source vraiment
        // équitable elle plafonne donc à ~1 % par construction. Mesuré sur
        // 1 000 graines du générateur corrigé : 0 alerte. Si ce test
        // repasse au rouge, c'est soit le détecteur soit le montage qui a
        // cessé d'être aléatoire — les deux valent qu'on regarde.
        var alerts = 0
        let seeds: [UInt64] = Array(1...60)
        for seed in seeds {
            let result = Swarm.run(syntheticHistory(count: 80, seed: seed))
            if result.duplicateAlert { alerts += 1 }
        }
        XCTAssertLessThanOrEqual(
            Double(alerts) / Double(seeds.count), 0.05,
            "Taux d'alerte anti-rejeu anormalement élevé sur du hasard (attendu 0, borne théorique 1 %)"
        )
    }

    func testGapDistributionIsCalibratedUnderRandomness() {
        // Régression : la formule KS « avant/après » appliquée à une loi
        // de référence DISCRÈTE (la géométrique de gapDistribution)
        // enregistrait à tort toute la masse de F(1) comme un écart —
        // un artefact garanti par la borne du support à g=1, indépendant
        // du nombre de tirages. Sur des données parfaitement aléatoires,
        // ça déclenchait le test 100% du temps avec un sigma constant
        // ≈6,8, quelle que soit la taille de l'échantillon. Vérifié sur
        // plusieurs graines indépendantes que ce n'est plus le cas.
        var flaggedCount = 0
        for seed: UInt64 in [1, 2, 3, 4, 5, 6, 7, 8] {
            let report = Forensics.run(syntheticHistory(count: 400, seed: seed))
            if let test = report.tests.first(where: { $0.name == "Distribution des écarts" }), test.flagged {
                flaggedCount += 1
            }
        }
        XCTAssertEqual(flaggedCount, 0, "Ne doit pas se déclencher systématiquement sur du hasard")
    }

    func testRecoveryBreaksAClockSeededLCG() {
        // Témoin positif : si le générateur était faible et amorcé sur
        // l'horloge — le bug Corriveau — l'attaque doit le casser.
        let dateString = "2026-08-25T12:00:00+02:00"
        let date = Zurich.parseISO(dateString)!
        let ts = UInt64(date.timeIntervalSince1970)
        var gen = GlibcLCG(s: UInt32(truncatingIfNeeded: ts &+ 137))
        func nextDraw() -> [Int] {
            var out: [Int] = []
            var seen = Set<Int>()
            while out.count < 20 {
                let n = Int(gen.next32() % 80) + 1
                if seen.insert(n).inserted { out.append(n) }
            }
            return out.sorted()
        }
        let first = nextDraw()
        let second = nextDraw()
        let draws = [
            Draw(drawNumber: 5002, drawDate: dateString, numbers: second, boost: nil, bonus: nil),
            Draw(drawNumber: 5001, drawDate: dateString, numbers: first, boost: nil, bonus: nil),
        ]
        let result = PRNGRecovery.attack(draws, budget: 60)
        XCTAssertTrue(result.solved, "Une graine horloge sur LCG doit être retrouvée")
        XCTAssertEqual(result.bestPrefix, 20)
        XCTAssertTrue(result.solvedDescription.contains("LCG glibc"))
        XCTAssertGreaterThan(result.candidatesTested, 0)
    }

    func testRecoveryBreaksAnOrderedStreamByStateSearch() {
        // Quand l'ordre de sortie est publié, l'espace d'états devient
        // balayable : la graine n'a plus besoin d'être devinable.
        var gen = GlibcLCG(rawSeed: 4321)
        func nextOrdered() -> [Int] {
            var out: [Int] = []
            var seen = Set<Int>()
            while out.count < 20 {
                let n = Int(gen.next32() % 80) + 1
                if seen.insert(n).inserted { out.append(n) }
            }
            return out
        }
        let first = nextOrdered()
        let second = nextOrdered()
        let draws = [
            Draw(drawNumber: 7002, drawDate: "2026-01-01T12:00:00+01:00",
                 numbers: second.sorted(), order: second, boost: nil, bonus: nil),
            Draw(drawNumber: 7001, drawDate: "2026-01-01T12:00:00+01:00",
                 numbers: first.sorted(), order: first, boost: nil, bonus: nil),
        ]
        XCTAssertTrue(draws[1].hasDrawOrder)
        let result = PRNGRecovery.attack(draws, budget: 30)
        XCTAssertTrue(result.orderAvailable)
        XCTAssertTrue(result.solved)
        XCTAssertTrue(result.solvedDescription.contains("4321"))
    }

    func testExhaustiveStateSearchWorksWithoutDrawOrder() {
        // Résultat clé : le balayage exhaustif ne dépend pas de l'ordre.
        // L'appartenance à l'ensemble trié suffit (1,34 pas par candidat).
        var gen = GlibcLCG(rawSeed: 2600)
        func nextSorted() -> [Int] {
            var out: [Int] = []
            var seen = Set<Int>()
            while out.count < 20 {
                let n = Int(gen.next32() % 80) + 1
                if seen.insert(n).inserted { out.append(n) }
            }
            return out.sorted()
        }
        let first = nextSorted()
        let second = nextSorted()
        let draws = [
            Draw(drawNumber: 8002, drawDate: "2026-01-01T12:00:00+01:00",
                 numbers: second, order: second, boost: nil, bonus: nil),
            Draw(drawNumber: 8001, drawDate: "2026-01-01T12:00:00+01:00",
                 numbers: first, order: first, boost: nil, bonus: nil),
        ]
        let result = PRNGRecovery.attack(draws, budget: 30)
        XCTAssertFalse(result.orderAvailable, "ordre trié : aucune information d'ordre")
        XCTAssertTrue(result.solved, "le balayage exhaustif doit aboutir sans l'ordre")
        XCTAssertTrue(result.solvedDescription.contains("2600"))
    }

    func testDrawWithoutOrderInfoIsFlaggedAsSuch() {
        let sorted = Array(1...20)
        let d = Draw(drawNumber: 1, drawDate: "2026-01-01T12:00:00+01:00",
                     numbers: sorted, order: sorted, boost: nil, bonus: nil)
        XCTAssertFalse(d.hasDrawOrder)
    }

    func testRecoveryNeedsTwoDraws() {
        let result = PRNGRecovery.attack([])
        XCTAssertFalse(result.solved)
        XCTAssertEqual(result.candidatesTested, 0)
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
