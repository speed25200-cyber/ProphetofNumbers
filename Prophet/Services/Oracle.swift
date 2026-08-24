import Foundation

enum Oracle {
    private static let pool = ProphetConst.poolSize
    private static let drawN = ProphetConst.drawSize
    private static let baseP = ProphetConst.baseP

    private static let methods: [(id: String, name: String, blurb: String)] = [
        ("beta", "Beta-Bayes", "Posterior Beta empirique, prior calé sur 20/80."),
        ("ewma", "EWMA", "Lissage exponentiel intra-séance, mémoire ~2 h."),
        ("hawkes", "Hawkes", "Intensité auto-excitatrice — détection des grappes."),
        ("weibull", "Weibull", "Survie des absences : numéros statistiquement dus."),
        ("spectral", "Résidu spectral", "Écart MA16 vs MA64 sur la série binaire."),
        ("crf", "CRF · ACP", "Champ résiduel chronospectral, 1er axe en ligne."),
    ]

    static func run(_ drawsNewestFirst: [Draw]) -> OracleResult {
        let ordered = drawsNewestFirst.sorted { $0.drawNumber < $1.drawNumber }
        let n = ordered.count
        let today = Zurich.todayKey()
        let todayDraws = ordered.filter { draw in
            guard let date = Zurich.parseISO(draw.drawDate) else { return false }
            return Zurich.parts(date).dayKey == today
        }.count

        var beta = [Double](repeating: 2, count: pool)
        var betaB = [Double](repeating: 6, count: pool)
        var ewma = [Double](repeating: baseP, count: pool)
        var hawkes = [Double](repeating: 0, count: pool)
        var gap = [Int](repeating: 0, count: pool)
        var gapMean = [Double](repeating: 1 / baseP, count: pool)
        var gapN = [Double](repeating: 0, count: pool)
        var counts = [Double](repeating: 0, count: pool)
        var co = [Double](repeating: 0, count: pool * pool)
        var pc = [Double](repeating: 0, count: pool)
        var meanV = [Double](repeating: baseP, count: pool)
        var window: [[Int]] = []
        let W = 64
        let lambda = 2.0 / (25 + 1)
        let hawkesDecay = exp(-0.18)
        let hawkesJump = 0.42
        let hawkesMu = 0.07

        var ov: [String: [Double]] = [
            "beta": [], "ewma": [], "hawkes": [],
            "weibull": [], "spectral": [], "crf": [],
        ]
        var prevRanks: [Int]?
        var lastRanks = Array(1...pool)
        var lastScores = [Double](repeating: 0, count: pool)

        func snapshot() -> [String: [Double]] {
            var weibull = [Double](repeating: 0, count: pool)
            var spectral = [Double](repeating: 0, count: pool)
            var crf = [Double](repeating: 0, count: pool)
            var betaP = [Double](repeating: 0, count: pool)
            var hawkesI = [Double](repeating: 0, count: pool)
            for i in 0..<pool {
                betaP[i] = beta[i] / (beta[i] + betaB[i])
                hawkesI[i] = hawkesMu + hawkes[i]
                let g = Double(gap[i])
                let mu = max(1.2, gapMean[i])
                weibull[i] = 1 - exp(-pow(g / mu, 1.55))
                let longW = max(1, min(W, window.count))
                var long = 0.0
                if window.count > 0 {
                    let start = window.count - longW
                    for t in start..<window.count where window[t].contains(i + 1) {
                        long += 1
                    }
                    long /= Double(longW)
                }
                let shortN = min(16, window.count)
                var short = 0.0
                if shortN > 0 {
                    let start = window.count - shortN
                    for t in start..<window.count where window[t].contains(i + 1) {
                        short += 1
                    }
                    short /= Double(shortN)
                }
                spectral[i] = long - short
                crf[i] = -pc[i] * (meanV[i] - baseP) * 8 - (long - baseP)
            }
            return [
                "betaP": betaP, "ewma": ewma, "hawkesI": hawkesI,
                "weibull": weibull, "spectral": spectral, "crf": crf,
            ]
        }

        if n > 0 {
            for t in 0..<n {
                let nums = ordered[t].numbers
                let drawn = Set(nums)

                if t > 12 {
                    let snap = snapshot()
                    let pack: [String: [Double]] = [
                        "beta": snap["betaP"]!,
                        "ewma": snap["ewma"]!,
                        "hawkes": snap["hawkesI"]!,
                        "weibull": snap["weibull"]!,
                        "spectral": snap["spectral"]!,
                        "crf": snap["crf"]!,
                    ]
                    for (id, vec) in pack {
                        let top = topIndices(vec, k: drawN)
                        ov[id, default: []].append(overlapCount(top, drawn) / Double(drawN))
                    }
                }

                for i in 0..<pool {
                    hawkes[i] *= hawkesDecay
                    ewma[i] = (1 - lambda) * ewma[i] + lambda * (drawn.contains(i + 1) ? 1 : 0)
                    gap[i] += 1
                    meanV[i] += 0.04 * ((drawn.contains(i + 1) ? 1.0 : 0.0) - meanV[i])
                }

                var x0 = [Double](repeating: 0, count: pool)
                for num in nums {
                    let i = num - 1
                    guard (0..<pool).contains(i) else { continue }
                    beta[i] += 1
                    hawkes[i] += hawkesJump
                    if gapN[i] > 0 {
                        gapMean[i] = (gapMean[i] * gapN[i] + Double(gap[i])) / (gapN[i] + 1)
                    } else {
                        gapMean[i] = Double(gap[i])
                    }
                    gapN[i] += 1
                    gap[i] = 0
                    counts[i] += 1
                }
                for i in 0..<pool {
                    if !drawn.contains(i + 1) { betaB[i] += 1 }
                    x0[i] = (drawn.contains(i + 1) ? 1.0 : 0.0) - meanV[i]
                }

                var norm = 0.0
                for i in 0..<pool { norm += pc[i] * pc[i] }
                if norm < 1e-9 {
                    pc = x0
                } else {
                    var d = 0.0
                    for i in 0..<pool { d += pc[i] * x0[i] }
                    let eta = 1 / sqrt(Double(t + 2))
                    for i in 0..<pool {
                        pc[i] += eta * d * (x0[i] - d * pc[i])
                    }
                }
                var pn = 0.0
                for i in 0..<pool { pn += pc[i] * pc[i] }
                pn = sqrt(pn)
                if pn == 0 { pn = 1 }
                for i in 0..<pool { pc[i] /= pn }

                for a in 0..<nums.count {
                    for b in a..<nums.count {
                        let i = nums[a] - 1
                        let j = nums[b] - 1
                        guard (0..<pool).contains(i), (0..<pool).contains(j) else { continue }
                        let lo = min(i, j)
                        let hi = max(i, j)
                        co[lo * pool + hi] += 1
                    }
                }

                window.append(nums)
                if window.count > W { window.removeFirst() }

                if t == n - 2 || (n == 1 && t == 0) {
                    let snap = snapshot()
                    let weightsT = currentWeights(ov)
                    prevRanks = ranksFromScores(blend(snap, weightsT))
                }
                if t == n - 1 {
                    let snap = snapshot()
                    let weightsT = currentWeights(ov)
                    lastScores = blend(snap, weightsT)
                    lastRanks = ranksFromScores(lastScores)
                }
            }
        }

        let snap = snapshot()
        let weights = currentWeights(ov)
        let ensemble = n > 0 ? lastScores : blend(snap, weights)
        let scores = ensemble
        let ranks = n > 0 ? lastRanks : ranksFromScores(scores)

        let pack: [String: [Double]] = [
            "beta": snap["betaP"]!,
            "ewma": snap["ewma"]!,
            "hawkes": snap["hawkesI"]!,
            "weibull": snap["weibull"]!,
            "spectral": snap["spectral"]!,
            "crf": snap["crf"]!,
        ]
        let methodScores: [MethodScore] = methods.enumerated().map { i, m in
            MethodScore(
                id: m.id,
                name: m.name,
                blurb: m.blurb,
                weight: weights[i],
                overlap: mean(Array((ov[m.id] ?? []).suffix(40))),
                scores: pack[m.id] ?? []
            )
        }

        var movers: [RankMove] = []
        if let prevRanks {
            for i in 0..<pool {
                movers.append(RankMove(
                    number: i + 1,
                    rank: ranks[i],
                    prevRank: prevRanks[i],
                    delta: prevRanks[i] - ranks[i],
                    score: scores[i]
                ))
            }
            movers.sort { abs($0.delta) > abs($1.delta) }
        }

        let inclusion = snap["betaP"]!
        let kinds: [GridKind] = [.alpha, .omega, .nexus]
        let stakes: [StakeGrids] = ProphetConst.stakes.map { stake in
            let grids: [SuggestedGrid] = kinds.map { kind in
                let source: [Double]
                switch kind {
                case .alpha:
                    source = blendHeads([snap["hawkesI"]!, snap["ewma"]!], [0.62, 0.38])
                case .omega:
                    source = blendHeads([snap["weibull"]!, snap["spectral"]!], [0.58, 0.42])
                case .nexus:
                    source = ensemble
                }
                let numbers = greedyPick(k: stake, score: source, kind: kind, co: co, counts: counts, nDraws: n)
                let p = numbers.map { inclusion[$0 - 1] }
                let exp = p.reduce(0, +)
                let pAll = heterogeneousAllHit(p)
                return SuggestedGrid(
                    kind: kind,
                    label: kind.label,
                    subtitle: kind.subtitle,
                    numbers: numbers,
                    expectedHits: exp,
                    baseExpected: Double(stake) * baseP,
                    pAllHit: pAll,
                    basePAllHit: hypergeometricPAll(stake)
                )
            }
            return StakeGrids(
                stake: stake,
                grids: grids,
                oddsLabel: formatPlainOdds(hypergeometricPAll(stake))
            )
        }

        let chi2 = chiSquareUniform(counts, nDraws: n)
        let serial = serialCorr(ordered.map(\.numbers))
        let df = Double(pool - 1)
        let chi2Norm = df == 0 ? 0 : chi2 / df
        let structured = chi2Norm > 1.25 || abs(serial) > 0.04
        let agreement = gridAgreement(stakes)
        let sampleBoost = min(1, Double(n) / 80)
        var confidence = Int(round(100 * (0.28 + 0.34 * sampleBoost + 0.22 * agreement + 0.16 * (structured ? 0.7 : 0.45))))
        confidence = max(18, min(86, confidence))

        return OracleResult(
            scores: scores,
            ranks: ranks,
            methods: methodScores,
            stakes: stakes,
            movers: Array(movers.prefix(12)),
            regimeLabel: structured ? "Structure résiduelle" : "Régime quasi-uniforme",
            regimeDetail: structured
                ? "Les têtes du modèle divergent du tirage uniforme. Pondération adaptée."
                : "Aucun biais durable. L’ensemble se cale près de 20/80 — diversification maximale.",
            chi2: chi2Norm,
            serial: serial,
            confidence: confidence,
            sampleSize: n,
            todayDraws: todayDraws
        )
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

    private static func hypergeometricPAll(_ k: Int) -> Double {
        comb(drawN, k) / comb(pool, k)
    }

    private static func mean(_ xs: [Double]) -> Double {
        guard !xs.isEmpty else { return 0 }
        return xs.reduce(0, +) / Double(xs.count)
    }

    private static func zscore(_ src: [Double]) -> [Double] {
        let n = src.count
        guard n > 0 else { return src }
        let m = src.reduce(0, +) / Double(n)
        var v = 0.0
        for x in src { let d = x - m; v += d * d }
        let s = sqrt(v / Double(n))
        let denom = s == 0 ? 1 : s
        return src.map { ($0 - m) / denom }
    }

    private static func softmax(_ xs: [Double], t: Double) -> [Double] {
        let mx = xs.max() ?? 0
        let ex = xs.map { exp(($0 - mx) / t) }
        let s = ex.reduce(0, +)
        let denom = s == 0 ? 1 : s
        return ex.map { $0 / denom }
    }

    private static func topIndices(_ scores: [Double], k: Int) -> [Int] {
        scores.enumerated()
            .sorted { $0.element > $1.element }
            .prefix(k)
            .map(\.offset)
    }

    private static func overlapCount(_ topIdx: [Int], _ drawn: Set<Int>) -> Double {
        var n = 0.0
        for i in topIdx where drawn.contains(i + 1) { n += 1 }
        return n
    }

    private static func ranksFromScores(_ scores: [Double]) -> [Int] {
        let idx = scores.enumerated().sorted { $0.element > $1.element }.map(\.offset)
        var ranks = [Int](repeating: 0, count: scores.count)
        for (order, numIdx) in idx.enumerated() {
            ranks[numIdx] = order + 1
        }
        return ranks
    }

    private static func pmiBoost(picked: [Int], candidate: Int, co: [Double], counts: [Double], nDraws: Int) -> Double {
        if picked.isEmpty || nDraws == 0 { return 0 }
        var s = 0.0
        for p in picked {
            let a = min(p, candidate) - 1
            let b = max(p, candidate) - 1
            let cij = co[a * pool + b]
            let denom = (counts[a] * counts[b] + 1) / Double(nDraws)
            s += log((cij + 0.25) / denom)
        }
        return s / Double(picked.count)
    }

    private static func greedyPick(k: Int, score: [Double], kind: GridKind, co: [Double], counts: [Double], nDraws: Int) -> [Int] {
        var picked: [Int] = []
        var decade = [Int](repeating: 0, count: 8)
        let cap = kind == .nexus ? max(2, Int(ceil(Double(k) / 5)) + 1) : k

        for _ in 0..<k {
            var best = -1
            var bestS = -Double.infinity
            for num in 1...pool {
                if picked.contains(num) { continue }
                let dec = (num - 1) / 10
                if decade[dec] >= cap { continue }
                var s = score[num - 1]
                if kind == .nexus {
                    s += 0.18 * pmiBoost(picked: picked, candidate: num, co: co, counts: counts, nDraws: nDraws)
                    let odd = num % 2 == 1
                    let oddNow = picked.filter { $0 % 2 == 1 }.count
                    let targetOdd = Double(k) / 2
                    if odd && Double(oddNow) >= targetOdd + 1 { s -= 0.25 }
                    if !odd && Double(picked.count - oddNow) >= targetOdd + 1 { s -= 0.25 }
                } else if kind == .omega {
                    if picked.contains(where: { abs($0 - num) == 1 }) { s -= 0.15 }
                }
                if s > bestS {
                    bestS = s
                    best = num
                }
            }
            if best < 0 {
                for num in 1...pool where !picked.contains(num) {
                    if score[num - 1] > bestS {
                        bestS = score[num - 1]
                        best = num
                    }
                }
            }
            if best > 0 {
                picked.append(best)
                decade[(best - 1) / 10] += 1
            }
        }
        return picked.sorted()
    }

    private static func heterogeneousAllHit(_ p: [Double]) -> Double {
        let k = p.count
        if k == 0 { return 0 }
        let sorted = p.sorted(by: >)
        var remaining = Double(drawN)
        var poolLeft = Double(pool)
        var prod = 1.0
        for i in 0..<k {
            let pi = min(0.92, max(0.02, sorted[i]))
            let cond = min(0.96, (pi * poolLeft) / max(1, remaining))
            prod *= cond
            remaining -= 1
            poolLeft -= 1
            if remaining <= 0 { break }
        }
        return min(prod, 0.5)
    }

    private static func chiSquareUniform(_ counts: [Double], nDraws: Int) -> Double {
        let expected = Double(nDraws) * baseP
        if expected <= 0 { return 0 }
        var x = 0.0
        for i in 0..<pool {
            let d = counts[i] - expected
            x += (d * d) / expected
        }
        return x
    }

    private static func serialCorr(_ draws: [[Int]]) -> Double {
        if draws.count < 8 { return 0 }
        let w = min(40, draws.count - 1)
        var acc = 0.0
        for t in (draws.count - w)..<draws.count {
            let a = Set(draws[t])
            var o = 0.0
            for n in draws[t - 1] where a.contains(n) { o += 1 }
            acc += o
        }
        let avg = acc / Double(w)
        return (avg - (Double(drawN * drawN) / Double(pool))) / Double(drawN)
    }

    private static func formatPlainOdds(_ p: Double) -> String {
        let inv = p > 0 ? Int(round(1 / p)) : 0
        return "1 / \(Format.ch.string(from: NSNumber(value: inv)) ?? "\(inv)")"
    }

    private static func currentWeights(_ ov: [String: [Double]]) -> [Double] {
        let ids = methods.map(\.id)
        let avgs = ids.map { id -> Double in
            let xs = Array((ov[id] ?? []).suffix(48))
            return xs.isEmpty ? baseP : mean(xs)
        }
        return softmax(avgs, t: 0.035)
    }

    private static func blend(_ snap: [String: [Double]], _ weights: [Double]) -> [Double] {
        let heads = [
            snap["betaP"]!, snap["ewma"]!, snap["hawkesI"]!,
            snap["weibull"]!, snap["spectral"]!, snap["crf"]!,
        ].map(zscore)
        var out = [Double](repeating: 0, count: pool)
        for h in 0..<heads.count {
            let w = h < weights.count ? weights[h] : 1 / Double(heads.count)
            for i in 0..<pool { out[i] += w * heads[h][i] }
        }
        return out
    }

    private static func blendHeads(_ heads: [[Double]], _ w: [Double]) -> [Double] {
        let zs = heads.map(zscore)
        var out = [Double](repeating: 0, count: pool)
        for h in 0..<zs.count {
            for i in 0..<pool { out[i] += w[h] * zs[h][i] }
        }
        return out
    }

    private static func gridAgreement(_ stakes: [StakeGrids]) -> Double {
        guard let g = stakes.first(where: { $0.stake == 10 })?.grids, g.count >= 3 else { return 0.5 }
        let sets = g.map { Set($0.numbers) }
        var acc = 0.0
        var c = 0.0
        for i in 0..<sets.count {
            for j in (i + 1)..<sets.count {
                let inter = Double(sets[i].intersection(sets[j]).count)
                let uni = Double(sets[i].union(sets[j]).count)
                acc += uni == 0 ? 0 : inter / uni
                c += 1
            }
        }
        return c == 0 ? 0.5 : acc / c
    }
}
