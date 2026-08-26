import Foundation

// Forensique du générateur.
//
// Cette batterie ne prédit aucun tirage : elle répond à la question
// « quel type de source produit cette série ? ». Chaque test cible un
// mode de défaillance réel et documenté d'un générateur de loterie :
// roue biaisée, période courte, graine horaire, structure en réseau d'un
// LCG, mémoire résiduelle, périodicité cachée.
//
// Un PRNG faible s'y trahit en quelques centaines de tirages. Un CSPRNG
// (AES-CTR, SHA-DRBG) ou un générateur quantique (type Quantis) les passe
// toutes par construction — et dans ce cas la série n'est pas seulement
// difficile à prédire, elle est sans état reconstructible : il n'y a rien
// à trouver dans les sorties.

struct ForensicTest: Identifiable {
    var name: String
    var catches: String     // le mode de défaillance visé
    var statistic: String   // valeur observée, formatée
    var sigma: Double       // écart en sigmas (après correction de multiplicité)
    var flagged: Bool
    var id: String { name }
}

struct ForensicsReport {
    var tests: [ForensicTest]
    var sampleSize: Int
    var flagged: Int
    var verdict: String
    var detail: String
}

enum Forensics {
    private static let pool = ProphetConst.poolSize
    private static let drawN = ProphetConst.drawSize
    private static let p1 = Double(ProphetConst.drawSize) / Double(ProphetConst.poolSize)

    // Recouvrement entre deux tirages indépendants : hypergéométrique
    // (80, 20, 20) — moyenne 5, écart-type ≈ 1,688.
    private static let ovMean = Double(drawN * drawN) / Double(pool)
    private static let ovSD: Double = {
        let n = Double(pool), k = Double(drawN)
        return sqrt(k * (k / n) * ((n - k) / n) * ((n - k) / (n - 1)))
    }()

    // Masque binaire : intersection de deux tirages en deux instructions.
    private struct Mask {
        var lo: UInt64 = 0
        var hi: UInt64 = 0
        init(_ nums: [Int]) {
            for n in nums where (1...80).contains(n) {
                let b = n - 1
                if b < 64 { lo |= (UInt64(1) << UInt64(b)) } else { hi |= (UInt64(1) << UInt64(b - 64)) }
            }
        }
        func overlap(_ o: Mask) -> Int {
            (lo & o.lo).nonzeroBitCount + (hi & o.hi).nonzeroBitCount
        }
    }

    static func run(_ drawsNewestFirst: [Draw]) -> ForensicsReport {
        let ordered = drawsNewestFirst.sorted { $0.drawNumber < $1.drawNumber }
        guard ordered.count >= 40 else {
            return ForensicsReport(
                tests: [], sampleSize: ordered.count, flagged: 0,
                verdict: "Échantillon insuffisant",
                detail: "Au moins 40 tirages sont nécessaires pour caractériser la source."
            )
        }
        let masks = ordered.map { Mask($0.numbers) }
        let numbers = ordered.map(\.numbers)

        var tests = [
            uniformity(numbers),
            autocorrelation(masks),
            gapDistribution(numbers),
            runsTest(numbers),
            periodicity(masks),
            clockSeed(ordered, masks),
            spectral(numbers),
            analogue(masks),
        ]
        tests.sort { $0.sigma > $1.sigma }
        let flagged = tests.filter(\.flagged).count

        let verdict: String
        let detail: String
        if flagged == 0 {
            verdict = "Aucune signature de générateur faible"
            detail = "Les huit tests sont conformes au hasard. Aucune période, aucune graine horaire, aucune structure de réseau, aucune mémoire résiduelle, et aucun analogue exploitable : la série est compatible avec une source cryptographique ou quantique — sans état reconstructible depuis les sorties."
        } else {
            verdict = "\(flagged) test\(flagged > 1 ? "s" : "") en anomalie"
            detail = "Un ou plusieurs tests s'écartent du hasard au-delà du seuil de 1 %. À confronter à l'e-valeur de la carte Vérité terrain avant toute conclusion : un test isolé peut dévier par malchance, une martingale qui monte durablement, non."
        }
        return ForensicsReport(
            tests: tests, sampleSize: ordered.count, flagged: flagged,
            verdict: verdict, detail: detail
        )
    }

    // MARK: 1 — Uniformité du champ (roue biaisée, numéro pondéré)

    private static func uniformity(_ draws: [[Int]]) -> ForensicTest {
        var counts = [Double](repeating: 0, count: pool)
        for d in draws {
            for n in d where (1...pool).contains(n) { counts[n - 1] += 1 }
        }
        let expected = Double(draws.count) * p1
        var chi2 = 0.0
        for c in counts {
            let d = c - expected
            chi2 += d * d / expected
        }
        let df = Double(pool - 1)
        let z = (chi2 - df) / sqrt(2 * df)
        let p = 2 * (1 - normalCDF(abs(z)))
        return ForensicTest(
            name: "Uniformité du champ",
            catches: "Roue biaisée, numéro sur- ou sous-pondéré",
            statistic: String(format: "χ² = %.1f / %d ddl", chi2, pool - 1),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 2 — Autocorrélation multi-décalages (mémoire, cycle court)

    private static func autocorrelation(_ masks: [Mask]) -> ForensicTest {
        let maxLag = min(24, masks.count - 2)
        guard maxLag >= 1 else { return short("Autocorrélation", "Mémoire entre tirages, cycle court") }
        var worstZ = 0.0
        var worstLag = 1
        for lag in 1...maxLag {
            var sum = 0.0
            let count = masks.count - lag
            for t in lag..<masks.count { sum += Double(masks[t].overlap(masks[t - lag])) }
            let mean = sum / Double(count)
            let z = (mean - ovMean) / (ovSD / sqrt(Double(count)))
            if abs(z) > abs(worstZ) { worstZ = z; worstLag = lag }
        }
        // Bonferroni sur les décalages testés.
        let p = min(1, 2 * (1 - normalCDF(abs(worstZ))) * Double(maxLag))
        return ForensicTest(
            name: "Autocorrélation",
            catches: "Mémoire entre tirages, cycle court",
            statistic: String(format: "z = %+.2f au décalage %d", worstZ, worstLag),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 3 — Distribution des écarts (source à mémoire)

    private static func gapDistribution(_ draws: [[Int]]) -> ForensicTest {
        var last = [Int](repeating: -1, count: pool)
        var gaps: [Int] = []
        for (t, d) in draws.enumerated() {
            for n in d where (1...pool).contains(n) {
                let i = n - 1
                if last[i] >= 0 { gaps.append(t - last[i]) }
                last[i] = t
            }
        }
        guard gaps.count >= 200 else { return short("Distribution des écarts", "Source à mémoire, tirage sans remise") }
        gaps.sort()
        let n = Double(gaps.count)
        var d = 0.0
        for (i, g) in gaps.enumerated() {
            // Géométrique(p = 1/4) : F(g) = 1 − (3/4)^g.
            let f = 1 - pow(1 - p1, Double(g))
            d = max(d, max(Double(i + 1) / n - f, f - Double(i) / n))
        }
        let ks = sqrt(n) * d
        // Queue de Kolmogorov (premier terme).
        let p = min(1, 2 * exp(-2 * ks * ks))
        return ForensicTest(
            name: "Distribution des écarts",
            catches: "Source à mémoire, tirage sans remise",
            statistic: String(format: "KS = %.3f · %d écarts", ks, gaps.count),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 4 — Séquences (alternance ou agglutination anormale)

    private static func runsTest(_ draws: [[Int]]) -> ForensicTest {
        let m = draws.count
        var sets: [Set<Int>] = draws.map(Set.init)
        var zSum = 0.0
        var used = 0.0
        for num in 1...pool {
            var runs = 1
            var ones = 0
            var prev = sets[0].contains(num)
            if prev { ones += 1 }
            for t in 1..<m {
                let cur = sets[t].contains(num)
                if cur { ones += 1 }
                if cur != prev { runs += 1 }
                prev = cur
            }
            let n1 = Double(ones), n2 = Double(m - ones), mm = Double(m)
            guard n1 > 1, n2 > 1 else { continue }
            let mu = 2 * n1 * n2 / mm + 1
            let varR = 2 * n1 * n2 * (2 * n1 * n2 - mm) / (mm * mm * (mm - 1))
            guard varR > 0 else { continue }
            zSum += (Double(runs) - mu) / sqrt(varR)
            used += 1
        }
        sets.removeAll()
        guard used > 0 else { return short("Séquences", "Alternance ou agglutination anormale") }
        let z = zSum / sqrt(used)
        let p = 2 * (1 - normalCDF(abs(z)))
        return ForensicTest(
            name: "Séquences",
            catches: "Alternance ou agglutination anormale",
            statistic: String(format: "z = %+.2f sur %d numéros", z, Int(used)),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 5 — Périodicité par décalage (période du générateur, rejeu)

    private static func periodicity(_ masks: [Mask]) -> ForensicTest {
        let maxLag = min(150, masks.count - 1)
        guard maxLag >= 1 else { return short("Périodicité", "Période du générateur, rejeu de séquence") }
        var best = 0
        var bestLag = 1
        var comparisons = 0.0
        for lag in 1...maxLag {
            comparisons += Double(masks.count - lag)
            for t in lag..<masks.count {
                let o = masks[t].overlap(masks[t - lag])
                if o > best { best = o; bestLag = lag }
            }
        }
        let p = min(1, comparisons * hypergeometricTail(best))
        return ForensicTest(
            name: "Périodicité",
            catches: "Période du générateur, rejeu de séquence",
            statistic: "max \(best)/\(drawN) au décalage \(bestLag)",
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 6 — Graine horaire (le mode de défaillance Corriveau, 1994)

    private static func clockSeed(_ draws: [Draw], _ masks: [Mask]) -> ForensicTest {
        var byTime: [String: [Int]] = [:]
        for (i, d) in draws.enumerated() {
            guard let date = Zurich.parseISO(d.drawDate) else { continue }
            let parts = Zurich.parts(date)
            byTime[parts.time, default: []].append(i)
        }
        var sum = 0.0
        var pairs = 0.0
        for (_, idx) in byTime where idx.count >= 2 {
            for a in 0..<idx.count {
                for b in (a + 1)..<idx.count {
                    sum += Double(masks[idx[a]].overlap(masks[idx[b]]))
                    pairs += 1
                }
            }
        }
        guard pairs >= 20 else {
            return ForensicTest(
                name: "Graine horaire",
                catches: "Générateur ré-amorcé sur l’horloge",
                statistic: "\(Int(pairs)) paires — échantillon court",
                sigma: 0,
                flagged: false
            )
        }
        let mean = sum / pairs
        let z = (mean - ovMean) / (ovSD / sqrt(pairs))
        let p = 2 * (1 - normalCDF(abs(z)))
        return ForensicTest(
            name: "Graine horaire",
            catches: "Générateur ré-amorcé sur l’horloge",
            statistic: String(format: "%.2f vs 5,00 · %d paires", mean, Int(pairs)),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: 7 — Spectral (périodicité cachée, structure de réseau d'un LCG)

    private static func spectral(_ draws: [[Int]]) -> ForensicTest {
        let m = min(256, draws.count)
        guard m >= 64 else { return short("Spectral", "Périodicité cachée, réseau d’un LCG") }
        let window = Array(draws.suffix(m)).map(Set.init)
        var cosT = [Double](repeating: 0, count: m)
        var sinT = [Double](repeating: 0, count: m)
        for k in 0..<m {
            let a = 2 * Double.pi * Double(k) / Double(m)
            cosT[k] = cos(a)
            sinT[k] = sin(a)
        }
        let half = m / 2
        var maxPower = 0.0
        var maxNumber = 0
        var maxFreq = 0
        var x = [Double](repeating: 0, count: m)
        for num in 1...pool {
            var energy = 0.0
            for t in 0..<m {
                x[t] = (window[t].contains(num) ? 1.0 : 0.0) - p1
                energy += x[t] * x[t]
            }
            guard energy > 0 else { continue }
            for f in 1..<half {
                var re = 0.0
                var im = 0.0
                for t in 0..<m {
                    let k = (f * t) % m
                    re += x[t] * cosT[k]
                    im -= x[t] * sinT[k]
                }
                // Périodogramme normalisé : ~ Exp(1) sous l'hypothèse nulle.
                let power = (re * re + im * im) / energy
                if power > maxPower {
                    maxPower = power
                    maxNumber = num
                    maxFreq = f
                }
            }
        }
        let comparisons = Double(pool * (half - 1))
        let p = min(1, comparisons * exp(-maxPower))
        let period = maxFreq > 0 ? Double(m) / Double(maxFreq) : 0
        return ForensicTest(
            name: "Spectral",
            catches: "Périodicité cachée, réseau d’un LCG",
            statistic: String(format: "pic %.1f · n°%d · période %.1f", maxPower, maxNumber, period),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    // MARK: Outils

    // MARK: 8 — Reconstruction d'état par analogues

    // Les sept tests précédents sont paramétriques : chacun vise une
    // signature nommée (roue biaisée, période, graine horaire, réseau
    // d'un LCG). Un générateur d'une famille non prévue leur échappe par
    // construction.
    //
    // Celui-ci ne suppose aucune famille. Soit S_t l'état interne, g la
    // transition et f la sortie : S_{t+1} = g(S_t), tirage_t = f(S_t).
    // Si g est déterministe, alors S_i = S_j implique tirage_{i+1} =
    // tirage_{j+1}. Le recouvrement entre deux tirages est donc un proxy
    // observable de la proximité d'états. D'où le test : chercher dans le
    // passé le meilleur analogue du dernier tirage, et jouer SON
    // successeur. Sous H0 le score vaut 5,000 quel que soit l'analogue
    // retenu — la méthode des analogues de Lorenz (1969), appliquée ici à
    // un flux de générateur.
    //
    // Portée : un flux continu consomme ~23 sorties brutes par tirage.
    // Une application déterministe sur n bits revisite un état après
    // ~sqrt(pi/2 · 2^n) pas. Le test voit donc tout générateur dont
    // l'état effectif tient sous 2·log2(23·m) − 0,65 bits, sans jamais
    // nommer son algorithme. Sur la fenêtre de l'app (399 tirages) cela
    // couvre ~25 bits ; sur l'historique public complet, ~40 bits.
    private static func analogue(_ masks: [Mask]) -> ForensicTest {
        let m = masks.count
        let warm = 20
        let name = "Reconstruction par analogues"
        let catches = "État interne de petite taille, toute famille confondue"
        guard m >= warm + 30 else { return short(name, catches) }

        var scores: [Double] = []
        scores.reserveCapacity(m - warm)
        for t in warm..<m {
            // Meilleur analogue du contexte courant, strictement antérieur.
            var bestJ = 0
            var bestOverlap = -1
            for j in 0..<(t - 1) {
                let o = masks[t - 1].overlap(masks[j])
                if o > bestOverlap {
                    bestOverlap = o
                    bestJ = j
                }
            }
            // On joue le successeur de l'analogue, et on note le recouvrement réel.
            scores.append(Double(masks[bestJ + 1].overlap(masks[t])))
        }

        let n = Double(scores.count)
        let mean = scores.reduce(0, +) / n
        var variance = 0.0
        for s in scores {
            let d = s - mean
            variance += d * d
        }
        let sd = sqrt(variance / max(n - 1, 1))
        guard sd > 0 else {
            // Écart-type nul : tous les analogues rendent le même score.
            // C'est le cas dégénéré d'une source qui se répète à l'identique.
            return ForensicTest(
                name: name, catches: catches,
                statistic: String(format: "score %.3f constant", mean),
                sigma: mean > ovMean + 1 ? 12 : 0,
                flagged: mean > ovMean + 1
            )
        }
        let z = (mean - ovMean) / (sd / sqrt(n))
        let p = 2 * (1 - normalCDF(abs(z)))
        let reach = 2 * log2(23 * Double(m)) - 0.65
        return ForensicTest(
            name: name,
            catches: catches,
            statistic: String(format: "score %.3f vs 5,000 · portée %.0f bits", mean, reach),
            sigma: sigma(p),
            flagged: p < 0.01
        )
    }

    private static func short(_ name: String, _ catches: String) -> ForensicTest {
        ForensicTest(name: name, catches: catches, statistic: "échantillon court", sigma: 0, flagged: false)
    }

    private static func normalCDF(_ x: Double) -> Double {
        0.5 * (1 + erf(x / 1.4142135623730951))
    }

    private static func normalPDF(_ x: Double) -> Double {
        exp(-0.5 * x * x) / 2.5066282746310002
    }

    // Écart en sigmas correspondant à une p-valeur bilatérale.
    private static func sigma(_ p: Double) -> Double {
        let q = min(max(p, 1e-12), 1)
        if q > 0.99 { return 0 }
        var z = sqrt(2 * log(1 / q))
        for _ in 0..<4 {
            let f = 2 * (1 - normalCDF(z)) - q
            let d = -2 * normalPDF(z)
            if abs(d) < 1e-15 { break }
            z -= f / d
            if z < 0 { return 0 }
        }
        return min(z, 12)
    }

    // P(recouvrement ≥ o) pour deux tirages indépendants.
    private static func hypergeometricTail(_ o: Int) -> Double {
        guard o <= drawN else { return 0 }
        var tail = 0.0
        for i in max(0, o)...drawN {
            tail += comb(drawN, i) * comb(pool - drawN, drawN - i) / comb(pool, drawN)
        }
        return min(1, max(tail, 0))
    }

    private static func comb(_ n: Int, _ k: Int) -> Double {
        if k < 0 || k > n { return 0 }
        if k == 0 || k == n { return 1 }
        let kk = min(k, n - k)
        var r = 1.0
        for i in 1...kk {
            r *= Double(n - kk + i) / Double(i)
        }
        return r
    }
}
