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

    // MARK: - Attaque algébrique par rang
    //
    // La seule voie du dossier qui vise la prédiction LITTÉRALE des 20
    // numéros. Elle n'est bloquée par aucun théorème : l'invariance suppose
    // un tirage uniforme, or un générateur dont on retrouve l'état n'est plus
    // uniforme conditionnellement — il est déterministe.

    /// Fabrique un historique dont les tirages SONT le dérangement d'un LCG.
    private func lcgHistory(a: UInt64, c: UInt64, count: Int = 40,
                            floorMapping: Bool = false) -> [Draw] {
        var s: UInt64 = 0x0123_4567_89AB_CDEF
        var draws: [Draw] = []
        for i in 1...count {
            s = a &* s &+ c
            let r: UInt64 = floorMapping
                ? s.multipliedFullWidth(by: RankAttack.modulus).high
                : s % RankAttack.modulus
            draws.append(Draw(drawNumber: 90_000 + i,
                              drawDate: "2026-08-30T12:00:00+02:00",
                              numbers: RankAttack.unrank(r),
                              boost: 2, bonus: 7))
        }
        return draws
    }

    func testRankIsABijectionOnTheWholeDomain() {
        // Si `rank` et `unrank` ne sont pas exactement inverses, toute
        // l'attaque repose sur du sable — et l'erreur serait invisible sur
        // les petits rangs.
        XCTAssertEqual(RankAttack.modulus, 3_535_316_142_212_174_320,
                       "M = C(80,20) — la table des binomiaux est fausse sinon")
        XCTAssertEqual(RankAttack.rank(Array(1...20)), 0)
        XCTAssertEqual(RankAttack.rank(Array(61...80)), RankAttack.modulus - 1)
        XCTAssertEqual(RankAttack.unrank(0), Array(1...20))
        XCTAssertEqual(RankAttack.unrank(RankAttack.modulus - 1), Array(61...80))
        // Aller-retour sur un échantillon déterministe couvrant tout le champ.
        var seed: UInt64 = 20_260_830
        for _ in 0..<300 {
            var set = Set<Int>()
            while set.count < 20 {
                seed = seed &* 6364136223846793005 &+ 1
                set.insert(Int(seed >> 33) % 80 + 1)
            }
            let g = set.sorted()
            XCTAssertEqual(RankAttack.unrank(RankAttack.rank(g)!), g)
        }
        // Une taille invalide ne doit pas produire un rang muet.
        XCTAssertNil(RankAttack.rank(Array(1...19)))
        XCTAssertNil(RankAttack.rank(Array(1...20).map { $0 + 70 }))
    }

    func testRankLeavesOnlyASixWayAmbiguity() {
        // Le cœur de l'attaque : 2^64 / M = 5,22, donc au plus 6 états par
        // tirage. Si ce nombre explosait, l'attaque deviendrait infaisable —
        // ce test est la sentinelle de sa faisabilité.
        var seed: UInt64 = 4242
        for _ in 0..<200 {
            seed = seed &* 6364136223846793005 &+ 1
            let r = seed % RankAttack.modulus
            for floorMapping in [false, true] {
                let cand = RankAttack.candidates(r, b: 64, floorMapping: floorMapping)
                XCTAssertGreaterThanOrEqual(cand.count, 5)
                XCTAssertLessThanOrEqual(cand.count, 6)
            }
        }
        // Le rang maximal est le cas limite qui fait déborder la borne haute
        // (elle vaudrait 2^64) : il doit rendre des candidats, pas planter.
        for floorMapping in [false, true] {
            let cand = RankAttack.candidates(RankAttack.modulus - 1, b: 64,
                                             floorMapping: floorMapping)
            XCTAssertFalse(cand.isEmpty)
        }
    }

    func testRankAttackSolvesAKnownGeneratorAndPredictsTheNextDraw() {
        // TÉMOIN POSITIF. Sans lui, « rien trouvé » sur l'archive réelle
        // serait indistinguable d'une attaque cassée.
        let a: UInt64 = 6364136223846793005, c: UInt64 = 1442695040888963407
        for floorMapping in [false, true] {
            let history = lcgHistory(a: a, c: c, count: 40, floorMapping: floorMapping)
            // On cache le dernier tirage : l'attaque doit le PRÉDIRE.
            let known = Array(history.dropLast())
            guard let sol = RankAttack.solve(known) else {
                XCTFail("le LCG n'a pas été résolu (mapping floor = \(floorMapping))")
                continue
            }
            XCTAssertTrue(sol.family.hasPrefix("LCG"), "famille : \(sol.family)")
            XCTAssertEqual(sol.predicted, history.last!.numbers,
                           "les 20 numéros prédits doivent être exacts")
        }
    }

    func testRankAttackStaysSilentOnFairDraws() {
        // TÉMOIN NÉGATIF. Une fausse solution devrait survivre à 20
        // confirmations avec probabilité ~M⁻²⁰ ≈ 10⁻³⁷⁰ : zéro attendu.
        XCTAssertNil(RankAttack.solve(Array(syntheticHistory(count: 60).reversed())))
        XCTAssertNil(RankAttack.solve(Array(syntheticHistory(count: 60, seed: 987_654_321).reversed())))
        // Et un historique trop court ne doit rien affirmer.
        XCTAssertNil(RankAttack.solve(Array(syntheticHistory(count: 8).reversed())))
    }

    func testNarrowSourceIsDetectedAndFairSourceIsNot() {
        // Le détecteur de LARGEUR : il ne suppose aucune récurrence, donc il
        // voit ce que l'attaque algébrique ne peut pas. Un tirage consomme
        // 61,62 bits ; si la source n'en fournit que B, les rangs atteignables
        // ne sont que 2^B sur 2^61,6 — à B = 53 (un double, donc
        // `Math.random()`), la densité tombe à 1/392.
        func narrowHistory(bits: Int, count: Int = 60) -> [Draw] {
            var seed: UInt64 = 0xDEAD_BEEF_1234_5678
            var draws: [Draw] = []
            for i in 1...count {
                seed = seed &* 6364136223846793005 &+ 1
                let k = seed >> UInt64(64 - bits)          // k < 2^bits
                let r = k.multipliedFullWidth(by: RankAttack.modulus)
                let rank = bits >= 64 ? r.high
                    : (r.high << UInt64(64 - bits)) | (r.low >> UInt64(bits))
                draws.append(Draw(drawNumber: 80_000 + i,
                                  drawDate: "2026-08-30T12:00:00+02:00",
                                  numbers: RankAttack.unrank(rank),
                                  boost: 2, bonus: 9))
            }
            return draws
        }

        // TÉMOINS POSITIFS : trois largeurs, toutes détectées — et NOMMÉES
        // exactement. Un simple test de significativité renverrait B−1, car
        // la moitié des rangs d'une source de B bits sont aussi atteignables
        // à B−1 (via k pair) ; c'est le critère de taux quasi total qui
        // tranche.
        for bits in [32, 48, 53] {
            XCTAssertEqual(RankAttack.narrowSourceWidth(narrowHistory(bits: bits)), bits,
                           "une source de \(bits) bits doit être vue ET nommée")
        }
        // TÉMOIN NÉGATIF : un historique pseudo-aléatoire consomme ses bits
        // pleins et ne doit rien déclencher.
        XCTAssertNil(RankAttack.narrowSourceWidth(syntheticHistory(count: 200)))
        XCTAssertNil(RankAttack.narrowSourceWidth(syntheticHistory(count: 200, seed: 13_579)))
        // Et un historique trop court ne doit rien affirmer.
        XCTAssertNil(RankAttack.narrowSourceWidth(syntheticHistory(count: 10)))

        // La brique elle-même : un rang tiré d'une source 53 bits est
        // atteignable à 53 bits, un rang quelconque ne l'est presque jamais.
        var seed: UInt64 = 4242
        var honest = 0
        for _ in 0..<400 {
            seed = seed &* 6364136223846793005 &+ 1
            if RankAttack.reachable(seed % RankAttack.modulus, bits: 53) { honest += 1 }
        }
        XCTAssertLessThan(honest, 10, "densité attendue 1/392 : ~1 sur 400")
    }

    func testRecoveryReportsThePredictionWhenItSolves() {
        // Le chemin complet, tel que l'écran le voit.
        let history = lcgHistory(a: 6364136223846793005, c: 1442695040888963407, count: 40)
        let r = PRNGRecovery.attack(Array(history.reversed()), budget: 1)
        XCTAssertTrue(r.solved)
        XCTAssertEqual(r.mode, "algébrique (rang)")
        XCTAssertEqual(r.predicted.count, 20)
        // Sur du hasard, l'écran ne doit annoncer aucune prédiction.
        let fair = PRNGRecovery.attack(syntheticHistory(count: 60), budget: 1)
        XCTAssertTrue(fair.predicted.isEmpty)
    }

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

    // MARK: Exactitude de ce qui est affiché

    /// Coefficient binomial, recalculé ici pour ne rien emprunter au code testé.
    private func binom(_ n: Int, _ k: Int) -> Double {
        if k < 0 || k > n { return 0 }
        if k == 0 || k == n { return 1 }
        let kk = min(k, n - k)
        var r = 1.0
        for i in 1...kk { r *= Double(n - kk + i) / Double(i) }
        return r
    }

    func testLogOnePlusExpIsStableAtBothEnds() {
        // Brique de la récurrence de Shiryaev-Roberts. Elle doit valoir 0 en
        // −∞ (R₀ = 0, donc le premier pas donne R₁ = f₁) et ne pas déborder
        // pour un x grand, où log(1+eˣ) ≈ x.
        XCTAssertEqual(SwarmEngine.logOnePlusExp(-.infinity), 0, accuracy: 1e-15)
        XCTAssertEqual(SwarmEngine.logOnePlusExp(0), log(2.0), accuracy: 1e-12)
        XCTAssertEqual(SwarmEngine.logOnePlusExp(-40), log(1 + exp(-40.0)), accuracy: 1e-15)
        XCTAssertEqual(SwarmEngine.logOnePlusExp(700), 700, accuracy: 1e-9)
        XCTAssertTrue(SwarmEngine.logOnePlusExp(700).isFinite,
                      "exp(700) déborde — la forme x + log1p(e^-x) ne doit pas être évaluée naïvement")
    }

    func testRestartMixtureSeesALateDefectThatACumulativeBetCannot() {
        // Deux résultats du labo se superposent ici.
        //
        // f2 : un pari jamais relancé est aveugle à un défaut tardif — sa
        // valeur finale vaut exp(Σ log f), et une somme ne dépend pas de
        // l'ordre ; son maximum courant ne bouge plus une fois la richesse
        // effondrée.
        //
        // h1 : la relance NAÏVE R_t/t est elle-même fautive. R_t est une
        // sous-martingale, donc sup_t R_t/t n'est pas couvert par Ville :
        // 12 % de fausses alertes mesurées pour 5 % promis. La forme
        // honnête arme une relance par BLOC de 16 tirages, pesée par le
        // prior 1/(j(j+1)) sur l'indice de bloc, trésorerie comptée —
        // une vraie martingale de moyenne 1, budget 2·ln(k/16) nats
        // (h2 : fausses alertes 0,025 ± 0,010 sur 240 archives, puissance
        // 0,57 → 0,82 sur le cas frontière).
        //
        // Ce test rejoue le mécanisme corrigé sur la famille de l'écho du
        // bonus, dont la loi sous H0 est une Bernoulli(20/80) exacte.
        let theta = 0.40
        let p = ProphetConst.baseP
        let logM = log(p * exp(theta) + (1 - p))

        func trajectory(defectFirst: Bool) -> (cumFinal: Double, cumSup: Double,
                                               nFinal: Double, nSup: Double) {
            var seed: UInt64 = 20260827
            func bernoulli(_ q: Double) -> Double {
                seed = seed &* 6364136223846793005 &+ 1442695040888963407
                return Double(seed >> 33) / 2147483648.0 < q ? 1 : 0
            }
            let quiet = 20_000, loud = 400
            let block = SwarmEngine.restartBlock
            var cum = 0.0, sr = -Double.infinity
            var maxCum = 0.0, maxN = 0.0
            var n = 0.0
            for t in 0..<(quiet + loud) {
                let biased = defectFirst ? t < loud : t >= quiet
                let x = biased ? 1.0 : bernoulli(p)
                let logF = theta * x - logM
                cum += logF
                if t % block == 0 {
                    let jb = Double(t / block + 1)
                    sr = SwarmEngine.logAddExp(sr, -log(jb * (jb + 1)))
                }
                sr = min(700, sr + logF)
                maxCum = max(maxCum, cum)
                n = exp(min(700, sr)) + 1 / Double(t / block + 2)
                maxN = max(maxN, n)
            }
            return (exp(cum), exp(maxCum), n, maxN)
        }

        let late = trajectory(defectFirst: false)
        let early = trajectory(defectFirst: true)

        // Le pari cumulé finit au même endroit dans les deux cas — la preuve
        // que sa valeur finale ignore QUAND le défaut s'est produit.
        XCTAssertEqual(late.cumFinal, early.cumFinal, accuracy: 1e-12 * max(1, early.cumFinal))

        // Défaut TARDIF : le pari cumulé ne franchit jamais le seuil de 20,
        // même en regardant son maximum sur toute la trajectoire.
        XCTAssertLessThan(late.cumSup, 20,
                          "un pari jamais relancé reste aveugle à un défaut tardif")
        // Le mélange de relances martingale, lui, le voit — et de très loin
        // (valeur exacte re-dérivée en Python : 3,114e43).
        XCTAssertGreaterThan(late.nFinal, 1e40)

        // Témoin POSITIF : quand le défaut est au DÉBUT, le pari cumulé le
        // voit parfaitement. Sans ce témoin, le test ne distinguerait pas
        // « aveugle à un défaut tardif » de « cassé ».
        XCTAssertGreaterThan(early.cumSup, 20)
        XCTAssertGreaterThan(early.nSup, 1e45)
        // Et l'honnêteté du schéma : une fois le défaut passé depuis 20 000
        // pas, la richesse relancée est DÉPENSÉE (7,8e-4 re-dérivé) — c'est
        // le supremum courant qu'un moniteur en direct aurait lu, pas la
        // valeur finale.
        XCTAssertLessThan(early.nFinal, 1)
    }

    func testBonusEchoLearnsItsOwnSize() {
        // Le départage n'est plus une constante : c'est le posterior
        // Beta(1,3) de P(bonus précédent ∈ tirage), appris en rejouant
        // l'historique. Ce test recompte les observations À LA MAIN depuis
        // l'historique synthétique et exige que l'app tombe sur le même
        // posterior — au bit près.
        let history = syntheticHistory()
        let ordered = history.sorted { $0.drawNumber < $1.drawNumber }
        var hits = 0.0, tries = 0.0
        var prevBonus: Int?
        for d in ordered {
            if let pb = prevBonus, (1...80).contains(pb) {
                tries += 1
                if d.numbers.contains(pb) { hits += 1 }
            }
            if let b = d.bonus, (1...80).contains(b) { prevBonus = b }
        }
        XCTAssertGreaterThan(tries, 70, "l'historique synthétique doit nourrir l'estimateur")
        let posterior = (1 + hits) / (4 + tries)
        let expected = (0.25 - posterior) / 0.25
        let result = Swarm.run(history)
        XCTAssertEqual(result.bonusEchoHat, expected, accuracy: 1e-12)
        // Et l'ordre de grandeur sous un historique pseudo-aléatoire : la
        // correction apprise doit rester petite — c'est son intérêt même.
        XCTAssertLessThan(abs(result.bonusEchoHat), 0.5)
    }

    // Instrument B (a1) : le boost avant clôture — la seule hypothèse du
    // théorème d'invariance qui soit une affirmation sur les HORLOGES du
    // système et non des mathématiques. Quatre témoins, dont deux positifs :
    // sans eux, un instrument qui ne dit jamais rien serait indistinguable
    // d'un instrument cassé.

    func testOpenBoostAuditCatchesBoostPresentBeforeResult() {
        // Témoin positif : le champ existe déjà à l'ouverture des mises, et
        // vaut la même chose que le résultat final.
        var list = OpenBoostAudit.recordOpen([], drawNumber: 1, boost: 3, secondsBeforeClose: 12)
        list = OpenBoostAudit.recordResult(list, drawNumber: 1, boost: 3)
        let obs = list.first!
        XCTAssertEqual(obs.boostAtOpen, 3)
        XCTAssertEqual(obs.boostAtResult, 3)
        XCTAssertEqual(obs.consistent, true)
    }

    func testOpenBoostAuditCatchesBoostAbsentBeforeResult() {
        // Témoin négatif : si le champ n'apparaît qu'après le tirage,
        // l'instrument doit le montrer sans jamais inventer une valeur.
        var list = OpenBoostAudit.recordOpen([], drawNumber: 2, boost: nil, secondsBeforeClose: 12)
        list = OpenBoostAudit.recordResult(list, drawNumber: 2, boost: 4)
        let obs = list.first!
        XCTAssertNil(obs.boostAtOpen)
        XCTAssertEqual(obs.boostAtResult, 4)
        XCTAssertNil(obs.consistent, "pas comparable : rien à comparer côté OPEN")
    }

    func testOpenBoostAuditFreezesFirstOpenSighting() {
        // Deux sondages du même tirage encore ouvert ne doivent pas se
        // remplacer l'un l'autre : on garde la première valeur vue.
        var list = OpenBoostAudit.recordOpen([], drawNumber: 3, boost: 2, secondsBeforeClose: 30)
        list = OpenBoostAudit.recordOpen(list, drawNumber: 3, boost: 5, secondsBeforeClose: 5)
        XCTAssertEqual(list.count, 1)
        XCTAssertEqual(list.first?.boostAtOpen, 2)
    }

    func testOpenBoostAuditFlagsInconsistentValue() {
        // Témoin positif d'un cas différent, tout aussi important : le champ
        // existe avant clôture mais change — donc pas exploitable tel quel,
        // et l'instrument doit le dire plutôt que compter une confirmation.
        var list = OpenBoostAudit.recordOpen([], drawNumber: 4, boost: 2, secondsBeforeClose: 10)
        list = OpenBoostAudit.recordResult(list, drawNumber: 4, boost: 5)
        XCTAssertEqual(list.first?.consistent, false)
    }

    func testLogAddExpMatchesItsDefinition() {
        // Brique de la récurrence martingale S_t = f_t·(S_{t−1} + w_t).
        XCTAssertEqual(SwarmEngine.logAddExp(-.infinity, -2.5), -2.5, accuracy: 1e-15)
        XCTAssertEqual(SwarmEngine.logAddExp(-2.5, -.infinity), -2.5, accuracy: 1e-15)
        XCTAssertEqual(SwarmEngine.logAddExp(0, 0), log(2.0), accuracy: 1e-12)
        XCTAssertEqual(SwarmEngine.logAddExp(3.0, 1.0), log(exp(3.0) + exp(1.0)),
                       accuracy: 1e-12)
        XCTAssertEqual(SwarmEngine.logAddExp(700, 700), 700 + log(2.0), accuracy: 1e-9)
        XCTAssertTrue(SwarmEngine.logAddExp(700, 690).isFinite)
        // Symétrie — la définition ne distingue pas ses arguments.
        XCTAssertEqual(SwarmEngine.logAddExp(-1.3, 2.2),
                       SwarmEngine.logAddExp(2.2, -1.3), accuracy: 1e-15)
    }

    func testDisplayedSigmaUsesTheExactLawNotAnEstimate() {
        // « ÉCART AU HASARD — +x.xx σ » divisait par un écart-type ESTIMÉ sur
        // les 60 derniers tirages. Or cet écart-type est une CONSTANTE : pour
        // tout top-20 choisi sans voir le tirage, le recouvrement suit une
        // hypergéométrique(80, 20, 20). L'estimer sur 60 points ajoutait
        // ±9 % de bruit au dénominateur — le chiffre affiché était un t de
        // Student à 59 degrés déguisé en σ.
        //
        // Ce test recalcule l'écart-type À PARTIR DE LA LOI, terme à terme,
        // sans réutiliser la formule fermée du code : les deux chemins doivent
        // tomber sur le même nombre, sinon l'un des deux est faux.
        let tot = binom(80, 20)
        var mean = 0.0
        var square = 0.0
        for o in 0...20 {
            let p = binom(20, o) * binom(60, 20 - o) / tot
            mean += Double(o) * p
            square += Double(o * o) * p
        }
        XCTAssertEqual(mean, 5.0, accuracy: 1e-9,
                       "l'espérance du recouvrement vaut 5 pour TOUT top-20")
        XCTAssertEqual((square - mean * mean).squareRoot(), SwarmEngine.overlapSD,
                       accuracy: 1e-9)
        // Et la valeur elle-même, pour qu'une régression se voie à l'œil.
        XCTAssertEqual(SwarmEngine.overlapSD, 1.6876317, accuracy: 1e-6)
    }

    func testDisplayedExpectationIsExact() {
        // Régression de fond : « ESPÉRANCE » portait la somme du posterior de
        // l'essaim sur les numéros SÉLECTIONNÉS par un score corrélé à ce même
        // posterior, ce qui surestimait de 18 à 34 % sur des données pourtant
        // équitables. L'espérance d'une hypergéométrique ne dépend pas du
        // contenu de la grille : elle vaut k/4, exactement.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            for grid in pack.grids {
                XCTAssertEqual(grid.expectedHits, Double(pack.stake) * 0.25, accuracy: 1e-12)
                XCTAssertEqual(grid.expectedHits, grid.baseExpected, accuracy: 1e-12,
                               "l'affiché et la base ne peuvent pas diverger : c'est le même nombre")
            }
        }
    }

    func testTailLawIsExactHypergeometric() {
        // La loi de survie affichée doit être la loi exacte, recalculée ici
        // indépendamment du code testé.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            let k = pack.stake
            guard let grid = pack.grids.first else { return XCTFail("paquet vide") }
            XCTAssertEqual(grid.tail.count, k + 1)
            XCTAssertEqual(grid.tail[0], 1.0, accuracy: 1e-12, "P(>= 0 hit) vaut 1")
            for t in 0...k {
                var expected = 0.0
                for h in t...k { expected += binom(20, h) * binom(60, k - h) }
                expected /= binom(80, k)
                XCTAssertEqual(grid.tail[t], expected, accuracy: 1e-9,
                               "mise \(k), rang \(t)")
            }
            // Décroissante, et le dernier rang coïncide avec la cote affichée.
            for t in 1...k {
                XCTAssertLessThanOrEqual(grid.tail[t], grid.tail[t - 1])
            }
            XCTAssertEqual(grid.tail[k], grid.basePAllHit, accuracy: 1e-12)
            // Toutes les grilles d'une même mise partagent la même loi : elle
            // ne dépend pas de leur contenu. C'est le théorème, pas un hasard.
            for other in pack.grids {
                XCTAssertEqual(other.tail, grid.tail)
            }
        }
    }

    func testPackProbabilityIsExactAndNearItsCeiling() {
        // P(au moins une des 12 grilles pleine). Encadrement dur : au moins
        // celle d'une grille seule, au plus douze fois. Et comme le paquet est
        // désormais étalé, la valeur doit frôler la borne haute — c'est
        // précisément ce que la duplication faisait perdre (−24,8 % à la mise 5).
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            guard let single = pack.grids.first?.basePAllHit else { return XCTFail("paquet vide") }
            let ceiling = 12 * single
            XCTAssertGreaterThan(pack.packPAllHit, single)
            XCTAssertLessThanOrEqual(pack.packPAllHit, ceiling)
            XCTAssertGreaterThan(pack.packPAllHit, 0.98 * ceiling,
                                 "mise \(pack.stake) : le paquet perd trop à la duplication")
        }
    }

    func testPackOverlapReportsTheRightFloorAndThreshold() {
        // Le diagnostic de forme du paquet (h13). Trois façons de se tromper
        // en silence, donc trois assertions :
        //
        //  1. le seuil neutre vaut EXACTEMENT k²/80 — c'est le recouvrement
        //     où Cov(H₁,H₂) s'annule, pas une approximation ;
        //  2. le plancher est Σ C(cₓ,2)/C(n,2) à couverture équilibrée, donc
        //     nul tant que 12·k ≤ 80 et strictement positif au-delà ;
        //  3. le recouvrement moyen mesuré ne peut jamais passer SOUS ce
        //     plancher — s'il y arrivait, le plancher serait faux.
        let result = Swarm.run(syntheticHistory())
        for pack in result.stakes {
            let k = pack.stake
            let n = pack.grids.count
            XCTAssertEqual(pack.overlapNeutral, Double(k * k) / 80.0, accuracy: 1e-12,
                           "mise \(k) : seuil neutre faux")
            let base = (n * k) / 80
            let rem = (n * k) % 80
            let expectedFloor = Double(rem * (base + 1) * base / 2
                                       + (80 - rem) * base * (base - 1) / 2)
                / Double(n * (n - 1) / 2)
            XCTAssertEqual(pack.overlapFloor, expectedFloor, accuracy: 1e-12,
                           "mise \(k) : plancher faux")
            XCTAssertGreaterThanOrEqual(pack.overlapMean, pack.overlapFloor - 1e-12,
                                        "mise \(k) : moyenne sous le plancher")
            XCTAssertLessThan(pack.overlapMax, k,
                              "mise \(k) : deux grilles identiques dans le paquet")
            if n * k <= 80 {
                XCTAssertEqual(pack.overlapFloor, 0, accuracy: 1e-12)
                XCTAssertEqual(pack.overlapMax, 0,
                               "mise \(k) : la place permettait des grilles disjointes")
            } else {
                XCTAssertGreaterThan(pack.overlapFloor, 0)
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
        // Et l'écho n'a rien appris : correction nulle (prior centré à 0,25).
        XCTAssertEqual(result.bonusEchoHat, 0, accuracy: 1e-12)
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
