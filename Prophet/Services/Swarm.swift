import Foundation

// L'Essaim : 26 têtes de prédiction en compétition, pondérées en ligne par
// un Hedge à part fixe (Freund-Schapire / Herbster-Warmuth) payé sur les hits
// réels, avec évolution des familles paramétriques par mutation du plus
// faible vers le plus fort. Tout est évalué en marche avant : aucune tête ne
// voit jamais le tirage qu'elle prédit.

private let poolN = ProphetConst.poolSize
private let drawK = ProphetConst.drawSize
private let pBase = ProphetConst.baseP

enum HeadTag {
    case momentum, reversion, structure, contrarian
}

protocol SwarmHead: AnyObject {
    var id: String { get }
    var name: String { get }
    var family: String { get }
    var blurb: String { get }
    var tag: HeadTag { get }
    func absorb(_ drawn: Set<Int>)
    func field() -> [Double]
}

// Une tête évolutive expose un paramètre de mémoire (en tirages) que
// l'évolution peut muter.
protocol EvolvingHead: SwarmHead {
    var memory: Double { get set }
}

// MARK: - Famille Bayes — posterior Beta escompté

final class BayesHead: EvolvingHead {
    let family = "Bayes"
    let tag = HeadTag.structure
    var memory: Double
    private let variant: String
    private var a = [Double](repeating: 2, count: poolN)
    private var b = [Double](repeating: 6, count: poolN)

    init(memory: Double, variant: String) {
        self.memory = memory
        self.variant = variant
    }

    var id: String { "bayes.\(variant)" }
    var name: String { "Beta ~\(Int(memory))" }
    var blurb: String { "Posterior Beta escompté, mémoire ≈ \(Int(memory)) tirages." }

    func absorb(_ drawn: Set<Int>) {
        let g = 1 - 1 / max(2, memory)
        for i in 0..<poolN {
            let hit = drawn.contains(i + 1) ? 1.0 : 0.0
            a[i] = g * a[i] + hit
            b[i] = g * b[i] + (1 - hit)
        }
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN { out[i] = a[i] / (a[i] + b[i]) }
        return out
    }
}

// MARK: - Famille EWMA — lissage exponentiel

final class EwmaHead: EvolvingHead {
    let family = "EWMA"
    let tag = HeadTag.momentum
    var memory: Double
    private let variant: String
    private var e = [Double](repeating: pBase, count: poolN)

    init(memory: Double, variant: String) {
        self.memory = memory
        self.variant = variant
    }

    var id: String { "ewma.\(variant)" }
    var name: String { "EWMA \(Int(memory))" }
    var blurb: String { "Lissage exponentiel, mémoire ≈ \(Int(memory)) tirages." }

    func absorb(_ drawn: Set<Int>) {
        let l = 2 / (max(2, memory) + 1)
        for i in 0..<poolN {
            e[i] = (1 - l) * e[i] + l * (drawn.contains(i + 1) ? 1 : 0)
        }
    }

    func field() -> [Double] { e }
}

// MARK: - Famille Hawkes — intensité auto-excitatrice

final class HawkesHead: EvolvingHead {
    let family = "Hawkes"
    let tag = HeadTag.momentum
    var memory: Double // demi-vie en tirages
    private let variant: String
    private var s = [Double](repeating: 0, count: poolN)
    private let jump = 0.42
    private let mu = 0.07

    init(memory: Double, variant: String) {
        self.memory = memory
        self.variant = variant
    }

    var id: String { "hawkes.\(variant)" }
    var name: String { String(format: "Hawkes t½=%.1f", memory) }
    var blurb: String { String(format: "Auto-excitation, demi-vie %.1f tirages — grappes.", memory) }

    func absorb(_ drawn: Set<Int>) {
        let d = exp(-0.6931 / max(0.5, memory))
        for i in 0..<poolN {
            s[i] = s[i] * d + (drawn.contains(i + 1) ? jump : 0)
        }
    }

    func field() -> [Double] { s.map { mu + $0 } }
}

// MARK: - Famille Écarts — survie, hazard empirique, z-score d'absence

final class WeibullHead: SwarmHead {
    let family = "Écarts"
    let tag = HeadTag.reversion
    private let k: Double
    private var gap = [Int](repeating: 0, count: poolN)
    private var gapMean = [Double](repeating: 1 / pBase, count: poolN)
    private var gapCount = [Double](repeating: 0, count: poolN)

    init(k: Double) { self.k = k }

    var id: String { "weibull.\(Int(k * 100))" }
    var name: String { String(format: "Weibull k=%.2f", k) }
    var blurb: String { "Survie des absences : numéros statistiquement « dus »." }

    func absorb(_ drawn: Set<Int>) {
        for i in 0..<poolN {
            gap[i] += 1
            if drawn.contains(i + 1) {
                if gapCount[i] > 0 {
                    gapMean[i] = (gapMean[i] * gapCount[i] + Double(gap[i])) / (gapCount[i] + 1)
                } else {
                    gapMean[i] = Double(gap[i])
                }
                gapCount[i] += 1
                gap[i] = 0
            }
        }
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            let mu = max(1.2, gapMean[i])
            out[i] = 1 - exp(-pow(Double(gap[i]) / mu, k))
        }
        return out
    }
}

final class HazardHead: SwarmHead {
    let family = "Écarts"
    let tag = HeadTag.reversion
    private var gap = [Int](repeating: 0, count: poolN)
    private var attempts = [Double](repeating: 0, count: 61)
    private var hits = [Double](repeating: 0, count: 61)

    var id: String { "hazard" }
    var name: String { "Hazard d'écart" }
    var blurb: String { "P(sortie | écart) estimée globalement, sans forme imposée." }
    // Convention : l'écart est incrémenté avant lecture, à l'absorption comme
    // à la prédiction.

    func absorb(_ drawn: Set<Int>) {
        for i in 0..<poolN {
            gap[i] += 1
            let g = min(60, gap[i])
            attempts[g] += 1
            if drawn.contains(i + 1) {
                hits[g] += 1
                gap[i] = 0
            }
        }
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            let g = min(60, gap[i] + 1)
            out[i] = (hits[g] + 2) / (attempts[g] + 8)
        }
        return out
    }
}

final class GapZHead: SwarmHead {
    let family = "Écarts"
    let tag = HeadTag.reversion
    private var gap = [Int](repeating: 0, count: poolN)
    private var m1 = [Double](repeating: 1 / pBase, count: poolN)
    private var m2 = [Double](repeating: 28, count: poolN)

    var id: String { "gapz" }
    var name: String { "Écart z" }
    var blurb: String { "Absence courante normalisée par l'historique du numéro." }

    func absorb(_ drawn: Set<Int>) {
        for i in 0..<poolN {
            gap[i] += 1
            if drawn.contains(i + 1) {
                let x = Double(gap[i])
                m1[i] += 0.15 * (x - m1[i])
                m2[i] += 0.15 * (x * x - m2[i])
                gap[i] = 0
            }
        }
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            let sd = sqrt(max(1, m2[i] - m1[i] * m1[i]))
            out[i] = (Double(gap[i]) - m1[i]) / sd
        }
        return out
    }
}

// MARK: - Famille Spectre — croisements de moyennes mobiles

final class SpectralHead: SwarmHead {
    let family = "Spectre"
    let tag: HeadTag
    private let short: Int
    private let long: Int
    private let momentum: Bool
    private var queue: [Set<Int>] = []
    private var shortSum = [Double](repeating: 0, count: poolN)
    private var longSum = [Double](repeating: 0, count: poolN)

    init(short: Int, long: Int, momentum: Bool) {
        self.short = short
        self.long = long
        self.momentum = momentum
        self.tag = momentum ? .momentum : .reversion
    }

    var id: String { "\(momentum ? "mom" : "rev").\(short)x\(long)" }
    var name: String { "\(momentum ? "Momentum" : "Résidu") \(short)/\(long)" }
    var blurb: String {
        momentum
            ? "Fréquence courte \(short) au-dessus de la longue \(long)."
            : "Écart de la fréquence courte \(short) sous la longue \(long)."
    }

    func absorb(_ drawn: Set<Int>) {
        queue.append(drawn)
        for n in drawn {
            shortSum[n - 1] += 1
            longSum[n - 1] += 1
        }
        if queue.count > short {
            for n in queue[queue.count - 1 - short] { shortSum[n - 1] -= 1 }
        }
        if queue.count > long {
            let old = queue.removeFirst()
            for n in old { longSum[n - 1] -= 1 }
        }
    }

    func field() -> [Double] {
        let sN = Double(min(short, max(1, queue.count)))
        let lN = Double(min(long, max(1, queue.count)))
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            let s = shortSum[i] / sN
            let l = longSum[i] / lN
            out[i] = momentum ? s - l : l - s
        }
        return out
    }
}

// MARK: - Famille Markov — dépendance aux derniers tirages

final class MarkovHead: SwarmHead {
    let family = "Markov"
    let tag = HeadTag.momentum
    private let k: Int
    private var recent: [Set<Int>] = []
    private var attempts: [Double]
    private var hits: [Double]

    init(k: Int) {
        self.k = k
        attempts = [Double](repeating: 0, count: k + 1)
        hits = [Double](repeating: 0, count: k + 1)
    }

    var id: String { "markov.\(k)" }
    var name: String { "Markov \(k)" }
    var blurb: String { "P(sortie | présences dans les \(k) derniers tirages), estimée en ligne." }

    func absorb(_ drawn: Set<Int>) {
        if recent.count == k {
            for i in 0..<poolN {
                let c = presence(i + 1)
                attempts[c] += 1
                if drawn.contains(i + 1) { hits[c] += 1 }
            }
        }
        recent.append(drawn)
        if recent.count > k { recent.removeFirst() }
    }

    private func presence(_ n: Int) -> Int {
        var c = 0
        for s in recent where s.contains(n) { c += 1 }
        return c
    }

    func field() -> [Double] {
        var out = [Double](repeating: pBase, count: poolN)
        guard recent.count == k else { return out }
        for i in 0..<poolN {
            let c = presence(i + 1)
            out[i] = (hits[c] + 2) / (attempts[c] + 8)
        }
        return out
    }
}

final class StreakHead: SwarmHead {
    let family = "Markov"
    let tag = HeadTag.momentum
    private var streak = [Double](repeating: 0, count: poolN)

    var id: String { "streak" }
    var name: String { "Séries" }
    var blurb: String { "Longueur de la série de sorties consécutives." }

    func absorb(_ drawn: Set<Int>) {
        for i in 0..<poolN {
            streak[i] = drawn.contains(i + 1) ? streak[i] + 1 : 0
        }
    }

    func field() -> [Double] { streak }
}

// MARK: - Famille Graphe — information mutuelle des paires

final class CopairHead: SwarmHead {
    let family = "Graphe"
    let tag = HeadTag.structure
    private var co = [Double](repeating: 0, count: poolN * poolN)
    private var counts = [Double](repeating: 0, count: poolN)
    private var nDraws = 0
    private var lastDraw: [Int] = []

    var id: String { "copair" }
    var name: String { "Graphe de paires" }
    var blurb: String { "Activation PMI des partenaires du dernier tirage." }

    func absorb(_ drawn: Set<Int>) {
        let nums = drawn.sorted()
        for a in 0..<nums.count {
            for b in (a + 1)..<nums.count {
                co[(nums[a] - 1) * poolN + (nums[b] - 1)] += 1
            }
        }
        for n in nums { counts[n - 1] += 1 }
        nDraws += 1
        lastDraw = nums
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        guard nDraws > 8, !lastDraw.isEmpty else { return out }
        for i in 0..<poolN {
            var s = 0.0
            for j in lastDraw {
                let a = min(i, j - 1)
                let b = max(i, j - 1)
                if a == b { continue }
                let cij = co[a * poolN + b]
                let denom = (counts[a] * counts[b] + 1) / Double(nDraws)
                s += log((cij + 0.25) / denom)
            }
            out[i] = s / Double(lastDraw.count)
        }
        return out
    }
}

// MARK: - Famille ACP — axes résiduels par règle d'Oja

final class AcpHead: SwarmHead {
    let family = "ACP"
    let tag = HeadTag.structure
    private let axis: Int
    private var meanV = [Double](repeating: pBase, count: poolN)
    private var pc1 = [Double](repeating: 0, count: poolN)
    private var pc2 = [Double](repeating: 0, count: poolN)
    private var t = 0

    init(axis: Int) { self.axis = axis }

    var id: String { "acp.\(axis)" }
    var name: String { "ACP axe \(axis)" }
    var blurb: String { "Oja en ligne — axe \(axis) du champ résiduel binaire." }

    func absorb(_ drawn: Set<Int>) {
        var x = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            let hit = drawn.contains(i + 1) ? 1.0 : 0.0
            meanV[i] += 0.04 * (hit - meanV[i])
            x[i] = hit - meanV[i]
        }
        oja(&pc1, x)
        if axis == 2 {
            var xr = x
            var d = 0.0
            for i in 0..<poolN { d += pc1[i] * x[i] }
            for i in 0..<poolN { xr[i] -= d * pc1[i] }
            oja(&pc2, xr)
            var dd = 0.0
            for i in 0..<poolN { dd += pc1[i] * pc2[i] }
            for i in 0..<poolN { pc2[i] -= dd * pc1[i] }
            normalize(&pc2)
        }
        t += 1
    }

    private func oja(_ pc: inout [Double], _ x: [Double]) {
        var norm = 0.0
        for v in pc { norm += v * v }
        if norm < 1e-9 {
            pc = x
            normalize(&pc)
            return
        }
        var d = 0.0
        for i in 0..<poolN { d += pc[i] * x[i] }
        let eta = 1 / sqrt(Double(t + 2))
        for i in 0..<poolN { pc[i] += eta * d * (x[i] - d * pc[i]) }
        normalize(&pc)
    }

    private func normalize(_ v: inout [Double]) {
        var n = 0.0
        for x in v { n += x * x }
        n = sqrt(n)
        if n == 0 { n = 1 }
        for i in 0..<v.count { v[i] /= n }
    }

    func field() -> [Double] {
        let pc = axis == 2 ? pc2 : pc1
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN { out[i] = -pc[i] * (meanV[i] - pBase) * 8 }
        return out
    }
}

// MARK: - Famille Contra — sondes contrariennes

final class AntiHead: SwarmHead {
    let family = "Contra"
    let tag = HeadTag.contrarian
    private let base: SwarmHead

    init(base: SwarmHead) { self.base = base }

    var id: String { "anti.\(base.id)" }
    var name: String { "Anti-\(base.name)" }
    var blurb: String { "Inverse de \(base.name) — sonde le biais miroir." }

    func absorb(_ drawn: Set<Int>) { base.absorb(drawn) }
    func field() -> [Double] { base.field().map { -$0 } }
}

// MARK: - Famille Géo — géométrie du tableau officiel (colonnes = dizaines,
// rangées = chiffre des unités). La disposition étant fixe, la géométrie ne
// contient aucune information au-delà des numéros ; ces têtes testent
// honnêtement l'hypothèse — et convergent vers le neutre si elle est fausse.

final class AdjacencyHead: SwarmHead {
    let family = "Géo"
    let tag = HeadTag.structure
    private var last: Set<Int> = []
    private var attempts = [Double](repeating: 0, count: 5)
    private var hits = [Double](repeating: 0, count: 5)

    var id: String { "geo.adj" }
    var name: String { "Voisinage tableau" }
    var blurb: String { "P(sortie | k voisins du tableau sortis au tirage précédent), auto-calibrée." }

    private func neighborCount(_ n: Int, in set: Set<Int>) -> Int {
        var c = 0
        let row = (n - 1) % 10
        if row > 0, set.contains(n - 1) { c += 1 }
        if row < 9, set.contains(n + 1) { c += 1 }
        if n > 10, set.contains(n - 10) { c += 1 }
        if n <= poolN - 10, set.contains(n + 10) { c += 1 }
        return c
    }

    func absorb(_ drawn: Set<Int>) {
        if !last.isEmpty {
            for i in 1...poolN {
                let k = neighborCount(i, in: last)
                attempts[k] += 1
                if drawn.contains(i) { hits[k] += 1 }
            }
        }
        last = drawn
    }

    func field() -> [Double] {
        var out = [Double](repeating: pBase, count: poolN)
        guard !last.isEmpty else { return out }
        for i in 1...poolN {
            let k = neighborCount(i, in: last)
            out[i - 1] = (hits[k] + 2) / (attempts[k] + 8)
        }
        return out
    }
}

final class RowPressureHead: SwarmHead {
    let family = "Géo"
    let tag = HeadTag.reversion
    private var rows = [Double](repeating: Double(drawK) / 10, count: 10)

    var id: String { "geo.rangs" }
    var name: String { "Rangs du tableau" }
    var blurb: String { "Déficit récent des 10 rangées du tableau officiel." }

    func absorb(_ drawn: Set<Int>) {
        var count = [Double](repeating: 0, count: 10)
        for n in drawn { count[(n - 1) % 10] += 1 }
        for r in 0..<10 { rows[r] += 0.12 * (count[r] - rows[r]) }
    }

    func field() -> [Double] {
        let expRow = Double(drawK) / 10
        var out = [Double](repeating: 0, count: poolN)
        for i in 0..<poolN {
            out[i] = (expRow - rows[i % 10]) / expRow
        }
        return out
    }
}

// MARK: - Famille Pression — déficit de zones

final class PressureHead: SwarmHead {
    let family = "Pression"
    let tag = HeadTag.reversion
    private var dec = [Double](repeating: Double(drawK) / 8, count: 8)
    private var par = [Double](repeating: Double(drawK) / 2, count: 2)

    var id: String { "pression" }
    var name: String { "Pression de zones" }
    var blurb: String { "Déficit récent des décades et de la parité." }

    func absorb(_ drawn: Set<Int>) {
        var dCount = [Double](repeating: 0, count: 8)
        var pCount = [Double](repeating: 0, count: 2)
        for n in drawn {
            dCount[(n - 1) / 10] += 1
            pCount[n % 2] += 1
        }
        for d in 0..<8 { dec[d] += 0.12 * (dCount[d] - dec[d]) }
        for p in 0..<2 { par[p] += 0.12 * (pCount[p] - par[p]) }
    }

    func field() -> [Double] {
        var out = [Double](repeating: 0, count: poolN)
        let dExp = Double(drawK) / 8
        let pExp = Double(drawK) / 2
        for i in 0..<poolN {
            let n = i + 1
            out[i] = (dExp - dec[(n - 1) / 10]) / dExp + 0.5 * (pExp - par[n % 2]) / pExp
        }
        return out
    }
}

// MARK: - Moteur de l'essaim
//
// Deux variantes d'analyse, aux résultats identiques :
// - SwarmEngine (incrémental) : l'état des 26 têtes, les poids Hedge, le
//   backtest et l'e-process persistent entre les rafraîchissements —
//   absorber un nouveau tirage coûte quelques millisecondes, les grilles
//   sortent dans la foulée du résultat.
// - Swarm.run (recalcul complet) : moteur neuf à chaque appel, rejoue tout
//   l'historique en marche avant — référence des tests et passe de
//   réconciliation. Les deux chemins exécutent les mêmes opérations dans le
//   même ordre.

final class SwarmEngine {
    private static let pool = ProphetConst.poolSize
    private static let drawN = ProphetConst.drawSize
    private static let baseP = ProphetConst.baseP
    private static let thetaE = 0.15
    private static let uniformExp = Double(ProphetConst.drawSize * ProphetConst.drawSize) / Double(ProphetConst.poolSize)

    private var heads: [SwarmHead] = []
    private var headCount = 0
    private var weights: [Double] = []
    private var headOv: [[Double]] = []
    private var ensembleOv: [Double] = []
    private var eLogUp = 0.0
    private var eLogDown = 0.0
    private var generation = 0
    private var seed: UInt64 = 0
    private var counts: [Double] = []
    private var co: [Double] = []
    private var gap: [Int] = []
    private var recent16: [[Int]] = []
    private var adjSeries: [Double] = []
    private var seen = Set<Int>()
    private var lastDrawNumber = Int.min
    private var absorbed = 0
    private var prevRanks: [Int]?
    private let logMUp: Double
    private let logMDown: Double

    init() {
        var overlapPMF = [Double](repeating: 0, count: Self.drawN + 1)
        for o in 0...Self.drawN {
            overlapPMF[o] = Self.comb(Self.drawN, o)
                * Self.comb(Self.pool - Self.drawN, Self.drawN - o)
                / Self.comb(Self.pool, Self.drawN)
        }
        var mUp = 0.0
        var mDown = 0.0
        for o in 0...Self.drawN {
            mUp += overlapPMF[o] * exp(Self.thetaE * Double(o))
            mDown += overlapPMF[o] * exp(-Self.thetaE * Double(o))
        }
        logMUp = log(mUp)
        logMDown = log(mDown)
        resetState()
    }

    private func resetState() {
        heads = Self.makeHeads()
        headCount = heads.count
        weights = [Double](repeating: 1 / Double(headCount), count: headCount)
        headOv = Array(repeating: [], count: headCount)
        ensembleOv = []
        eLogUp = 0
        eLogDown = 0
        generation = 0
        seed = 0x9E37_79B9_7F4A_7C15
        counts = [Double](repeating: 0, count: Self.pool)
        co = [Double](repeating: 0, count: Self.pool * Self.pool)
        gap = [Int](repeating: 0, count: Self.pool)
        recent16 = []
        adjSeries = []
        seen = []
        lastDrawNumber = Int.min
        absorbed = 0
        prevRanks = nil
    }

    func update(_ drawsNewestFirst: [Draw]) -> OracleResult {
        let ordered = drawsNewestFirst.sorted { $0.drawNumber < $1.drawNumber }
        let fresh = ordered.filter { !seen.contains($0.drawNumber) }
        if fresh.allSatisfy({ $0.drawNumber > lastDrawNumber }) {
            process(fresh)
        } else {
            // Un tirage plus ancien vient d'apparaître (rattrapage) : la
            // marche avant impose de tout rejouer.
            resetState()
            process(ordered)
        }
        return assemble(ordered: ordered)
    }

    // MARK: Absorption en marche avant

    private func process(_ batch: [Draw]) {
        guard !batch.isEmpty else { return }
        let lastIdx = batch.count - 1
        for (i, draw) in batch.enumerated() {
            let nums = draw.numbers
            let drawn = Set(nums)

            if absorbed > 12 {
                evaluate(drawn)
            }
            if i == lastIdx, absorbed > 0 {
                let fields = heads.map { Self.zscore($0.field()) }
                prevRanks = Self.ranksFromScores(blendWeighted(fields))
            }

            for head in heads { head.absorb(drawn) }

            for j in 0..<Self.pool { gap[j] += 1 }
            for num in nums {
                let j = num - 1
                guard (0..<Self.pool).contains(j) else { continue }
                counts[j] += 1
                gap[j] = 0
            }
            for a in 0..<nums.count {
                for b in (a + 1)..<nums.count {
                    let x = min(nums[a], nums[b]) - 1
                    let y = max(nums[a], nums[b]) - 1
                    guard x >= 0, y < Self.pool else { continue }
                    co[x * Self.pool + y] += 1
                }
            }
            recent16.append(nums)
            if recent16.count > 16 { recent16.removeFirst() }
            adjSeries.append(Self.adjacentPairs(drawn))
            if adjSeries.count > 480 { adjSeries.removeFirst() }

            if absorbed >= 48, absorbed % 24 == 0 {
                if evolve() { generation += 1 }
            }

            seen.insert(draw.drawNumber)
            lastDrawNumber = max(lastDrawNumber, draw.drawNumber)
            absorbed += 1
        }
    }

    // Évaluation walk-forward : états et poids figés avant le tirage.
    private func evaluate(_ drawn: Set<Int>) {
        let fields = heads.map { Self.zscore($0.field()) }
        let ens = blendWeighted(fields)
        let overlap = Self.overlapCount(Self.topIndices(ens, k: Self.drawN), drawn)
        ensembleOv.append(overlap)
        if ensembleOv.count > 480 { ensembleOv.removeFirst() }
        eLogUp = min(80, eLogUp + Self.thetaE * overlap - logMUp)
        eLogDown = min(80, eLogDown - Self.thetaE * overlap - logMDown)

        let hedgeEta = 0.6
        let fixedShare = 0.02
        for h in 0..<headCount {
            let ovh = Self.overlapCount(Self.topIndices(fields[h], k: Self.drawN), drawn)
            headOv[h].append(ovh)
            if headOv[h].count > 80 { headOv[h].removeFirst() }
            weights[h] *= exp(hedgeEta * (ovh - Self.uniformExp) / Double(Self.drawN))
        }
        let sum = weights.reduce(0, +)
        if !sum.isFinite || sum <= 0 {
            weights = [Double](repeating: 1 / Double(headCount), count: headCount)
        } else {
            for h in 0..<headCount {
                weights[h] = (1 - fixedShare) * (weights[h] / sum) + fixedShare / Double(headCount)
            }
        }
    }

    // Mutation : la tête la plus faible d'une famille paramétrique adopte la
    // mémoire de la plus forte, avec un jitter déterministe.
    private func evolve() -> Bool {
        var mutated = false
        for fam in ["Bayes", "EWMA", "Hawkes"] {
            let idx = heads.indices.filter { heads[$0].family == fam && heads[$0] is EvolvingHead }
            guard idx.count >= 2 else { continue }
            var means: [(index: Int, mean: Double)] = []
            for i in idx {
                let xs = headOv[i].suffix(40)
                guard xs.count >= 20 else { continue }
                means.append((i, xs.reduce(0, +) / Double(xs.count)))
            }
            guard means.count == idx.count else { continue }
            guard let best = means.max(by: { $0.mean < $1.mean }),
                  let worst = means.min(by: { $0.mean < $1.mean }),
                  best.index != worst.index,
                  best.mean - worst.mean > 0.35,
                  let bestHead = heads[best.index] as? EvolvingHead,
                  let worstHead = heads[worst.index] as? EvolvingHead
            else { continue }
            seed = seed &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
            let jitter = 0.7 + 0.6 * Double((seed >> 33) & 0xFFFF) / 65535
            worstHead.memory = min(400, max(1, bestHead.memory * jitter))
            headOv[worst.index].removeAll()
            weights[worst.index] = 1 / Double(headCount)
            let s = weights.reduce(0, +)
            if s > 0 {
                for i in 0..<weights.count { weights[i] /= s }
            }
            mutated = true
        }
        return mutated
    }

    // MARK: Assemblage du résultat

    private func assemble(ordered: [Draw]) -> OracleResult {
        let n = ordered.count
        let todayKey = Zurich.todayKey()
        let todayDraws = ordered.filter { draw in
            guard let date = Zurich.parseISO(draw.drawDate) else { return false }
            return Zurich.parts(date).dayKey == todayKey
        }.count

        let rawFields = heads.map { $0.field() }
        let zFields = rawFields.map(Self.zscore)
        let ensemble = blendWeighted(zFields)
        let ranks = Self.ranksFromScores(ensemble)

        let methodScores: [MethodScore] = heads.enumerated().map { i, h in
            let xs = Array(headOv[i].suffix(40))
            return MethodScore(
                id: h.id,
                name: h.name,
                blurb: h.blurb,
                family: h.family,
                weight: weights[i],
                overlap: xs.isEmpty ? Self.baseP : Self.mean(xs) / Double(Self.drawN),
                scores: rawFields[i]
            )
        }

        var movers: [RankMove] = []
        if let prevRanks {
            for i in 0..<Self.pool {
                movers.append(RankMove(
                    number: i + 1,
                    rank: ranks[i],
                    prevRank: prevRanks[i],
                    delta: prevRanks[i] - ranks[i],
                    score: ensemble[i]
                ))
            }
            movers.sort { abs($0.delta) > abs($1.delta) }
        }

        let sources = gridSourcesFrom(rawFields: rawFields, zFields: zFields, ensemble: ensemble)
        let stakes: [StakeGrids] = ProphetConst.stakes.map { stake in
            StakeGrids(
                stake: stake,
                grids: makeGrids(stake: stake, sources: sources),
                oddsLabel: Self.formatPlainOdds(Self.hypergeometricPAll(stake))
            )
        }

        let chi2 = Self.chiSquareUniform(counts, nDraws: absorbed)
        let serial = Self.serialCorr(ordered.map(\.numbers))
        let df = Double(Self.pool - 1)
        let chi2Norm = df == 0 ? 0 : chi2 / df
        let structured = chi2Norm > 1.25 || abs(serial) > 0.04

        // Signal honnête : dérivé du backtest réel, 50 = indistinguable du hasard.
        let recentBT = Array(ensembleOv.suffix(60))
        let btMean = recentBT.isEmpty ? Self.uniformExp : Self.mean(recentBT)
        var btVar = 0.0
        for x in recentBT {
            let d = x - btMean
            btVar += d * d
        }
        let btSD = recentBT.count > 1 ? sqrt(btVar / Double(recentBT.count - 1)) : 1.68
        let btZ: Double = recentBT.count >= 12
            ? (btMean - Self.uniformExp) / (max(0.2, btSD) / sqrt(Double(recentBT.count)))
            : 0
        var confidence = Int(round(50 + 14 * btZ))
        confidence = max(5, min(95, confidence))

        let eValue = 0.5 * exp(min(60, eLogUp)) + 0.5 * exp(min(60, eLogDown))

        // Géométrie du tableau : paires adjacentes observées vs hasard.
        let edges = Double(9 * (Self.pool / 10) + 10 * (Self.pool / 10 - 1))
        let adjExpected = edges * Double(Self.drawN * (Self.drawN - 1)) / Double(Self.pool * (Self.pool - 1))
        let recentAdj = Array(adjSeries.suffix(60))
        let adjMean = recentAdj.isEmpty ? adjExpected : Self.mean(recentAdj)
        var adjVar = 0.0
        for x in recentAdj {
            let d = x - adjMean
            adjVar += d * d
        }
        let adjSD = recentAdj.count > 1 ? sqrt(adjVar / Double(recentAdj.count - 1)) : 2.6
        let adjZ: Double = recentAdj.count >= 12
            ? (adjMean - adjExpected) / (max(0.3, adjSD) / sqrt(Double(recentAdj.count)))
            : 0

        var freq16 = [Double](repeating: 0, count: Self.pool)
        for drawNums in recent16 {
            for num in drawNums where (1...Self.pool).contains(num) {
                freq16[num - 1] += 1
            }
        }

        var entropy = 0.0
        for w in weights where w > 1e-12 { entropy -= w * log(w) }
        var famAgg: [String: (weight: Double, heads: Int)] = [:]
        var famOrder: [String] = []
        for (i, h) in heads.enumerated() {
            if famAgg[h.family] == nil {
                famOrder.append(h.family)
                famAgg[h.family] = (0, 0)
            }
            famAgg[h.family]!.weight += weights[i]
            famAgg[h.family]!.heads += 1
        }
        let families = famOrder
            .map { FamilyWeight(name: $0, weight: famAgg[$0]!.weight, heads: famAgg[$0]!.heads) }
            .sorted { $0.weight > $1.weight }

        var bestName = "—"
        var bestMean = Self.uniformExp
        var bestFound = false
        for (i, h) in heads.enumerated() {
            let xs = headOv[i].suffix(40)
            guard xs.count >= 20 else { continue }
            let m = xs.reduce(0, +) / Double(xs.count)
            if !bestFound || m > bestMean {
                bestName = h.name
                bestMean = m
                bestFound = true
            }
        }

        let swarmStats = SwarmStats(
            headCount: headCount,
            effectiveHeads: exp(entropy),
            generation: generation,
            bestHeadName: bestName,
            bestHeadMean: bestMean,
            families: families
        )

        return OracleResult(
            scores: ensemble,
            ranks: ranks,
            methods: methodScores,
            stakes: stakes,
            movers: Array(movers.prefix(12)),
            regimeLabel: structured ? "Structure résiduelle" : "Régime quasi-uniforme",
            regimeDetail: structured
                ? "L'essaim diverge du tirage uniforme. Pondération adaptée."
                : "Aucun biais durable. L'essaim se cale près de 20/80 — diversification maximale.",
            chi2: chi2Norm,
            serial: serial,
            confidence: confidence,
            sampleSize: n,
            todayDraws: todayDraws,
            backtest: ensembleOv,
            backtestMean: btMean,
            uniformExpected: Self.uniformExp,
            backtestZ: btZ,
            eValue: eValue,
            adjacencyMean: adjMean,
            adjacencyExpected: adjExpected,
            adjacencyZ: adjZ,
            gaps: gap,
            freq16: freq16,
            swarm: swarmStats
        )
    }

    // MARK: Sélection des grilles

    struct GridSources {
        var inclusion: [Double]
        var alpha: [Double]
        var omega: [Double]
        var nexus: [Double]
    }

    func gridSources() -> GridSources {
        let rawFields = heads.map { $0.field() }
        let zFields = rawFields.map(Self.zscore)
        let ensemble = blendWeighted(zFields)
        return gridSourcesFrom(rawFields: rawFields, zFields: zFields, ensemble: ensemble)
    }

    private func gridSourcesFrom(rawFields: [[Double]], zFields: [[Double]], ensemble: [Double]) -> GridSources {
        func tagBlend(_ tag: HeadTag) -> [Double] {
            let idx = (0..<headCount).filter { heads[$0].tag == tag }
            guard !idx.isEmpty else { return ensemble }
            var w = idx.map { weights[$0] }
            let s = w.reduce(0, +)
            if s > 0 {
                for k in 0..<w.count { w[k] /= s }
            } else {
                w = [Double](repeating: 1 / Double(idx.count), count: idx.count)
            }
            var out = [Double](repeating: 0, count: Self.pool)
            for (k, i) in idx.enumerated() {
                let f = zFields[i]
                for j in 0..<Self.pool { out[j] += w[k] * f[j] }
            }
            return out
        }
        let inclusionIdx = heads.firstIndex { $0.id == "bayes.b" } ?? 0
        return GridSources(
            inclusion: rawFields[inclusionIdx],
            alpha: tagBlend(.momentum),
            omega: tagBlend(.reversion),
            nexus: ensemble
        )
    }

    func makeGrids(stake: Int, sources: GridSources) -> [SuggestedGrid] {
        var grids: [SuggestedGrid] = []
        for kind in [GridKind.alpha, .omega, .nexus] {
            let source: [Double]
            switch kind {
            case .alpha: source = sources.alpha
            case .omega: source = sources.omega
            case .nexus: source = sources.nexus
            }
            // Variante I : sélection principale. Variante II : disjointe de
            // la I — double la couverture. Variante Anti : le pari inverse —
            // les numéros que la stratégie classe derniers (contre-épreuve
            // vivante : sur un RNG équitable, elle fait jeu égal ; si le
            // modèle se trompait systématiquement, elle gagnerait).
            let first = greedyPick(k: stake, score: source, kind: kind, banned: [])
            let second = greedyPick(k: stake, score: source, kind: kind, banned: Set(first))
            let anti = greedyPick(k: stake, score: source.map { -$0 }, kind: kind, banned: [])
            for (variant, numbers) in [(1, first), (2, second), (3, anti)] {
                let p = numbers.map { sources.inclusion[$0 - 1] }
                let label: String
                let subtitle: String
                switch variant {
                case 1:
                    label = kind.label
                    subtitle = kind.subtitle
                case 2:
                    label = "\(kind.label) II"
                    subtitle = "Variante disjointe de \(kind.label) — double la couverture"
                default:
                    label = "Anti-\(kind.label)"
                    subtitle = "Le pari inverse — les numéros que \(kind.label) classe derniers"
                }
                grids.append(SuggestedGrid(
                    kind: kind,
                    variant: variant,
                    label: label,
                    subtitle: subtitle,
                    numbers: numbers,
                    expectedHits: p.reduce(0, +),
                    baseExpected: Double(stake) * Self.baseP,
                    pAllHit: Self.heterogeneousAllHit(p),
                    basePAllHit: Self.hypergeometricPAll(stake)
                ))
            }
        }
        return grids
    }

    // MARK: Journal du jour — rejeu en marche avant
    //
    // Pour chaque tirage de la journée, reconstruit ce que les 9 grilles
    // auraient prédit avec l'état du modèle d'alors (jamais le tirage
    // lui-même), puis les confronte au résultat réel. Déterministe : mêmes
    // tirages ⇒ même journal, que l'app ait tourné ou non.
    static func replayToday(_ drawsNewestFirst: [Draw], stake: Int, hold: Int = 1) -> DayJournal {
        let holdN = max(1, hold)
        let engine = SwarmEngine()
        let ordered = drawsNewestFirst.sorted { $0.drawNumber < $1.drawNumber }
        let dayKey: String = {
            if let last = ordered.last, let d = Zurich.parseISO(last.drawDate) {
                return Zurich.parts(d).dayKey
            }
            return Zurich.todayKey()
        }()
        var plays: [DayPlay] = []
        // Mode multi-tirages : la même prédiction est jouée sur holdN tirages
        // consécutifs avant d'être régénérée. Le modèle, lui, continue
        // d'apprendre à chaque tirage.
        var currentGrids: [SuggestedGrid] = []
        var playedWithCurrent = holdN
        for draw in ordered {
            let date = Zurich.parseISO(draw.drawDate)
            let isDay = date.map { Zurich.parts($0).dayKey == dayKey } ?? false
            if isDay, engine.absorbed > 12 {
                if playedWithCurrent >= holdN {
                    currentGrids = engine.makeGrids(stake: stake, sources: engine.gridSources())
                    playedWithCurrent = 0
                }
                let drawnSet = Set(draw.numbers)
                plays.append(DayPlay(
                    drawNumber: draw.drawNumber,
                    time: date.map { Zurich.parts($0).time } ?? "—",
                    draw: draw.numbers,
                    plays: currentGrids.map {
                        GridPlay(
                            kind: $0.kind,
                            variant: $0.variant,
                            numbers: $0.numbers,
                            hits: $0.numbers.filter(drawnSet.contains).count
                        )
                    }
                ))
                playedWithCurrent += 1
            }
            engine.process([draw])
        }
        return DayJournal(dayKey: dayKey, stake: stake, hold: holdN, plays: plays)
    }

    private func greedyPick(k: Int, score: [Double], kind: GridKind, banned: Set<Int>) -> [Int] {
        var picked: [Int] = []
        var decade = [Int](repeating: 0, count: 8)
        let cap = kind == .nexus ? max(2, Int(ceil(Double(k) / 5)) + 1) : k

        for _ in 0..<k {
            var best = -1
            var bestS = -Double.infinity
            for num in 1...Self.pool {
                if picked.contains(num) || banned.contains(num) { continue }
                let dec = (num - 1) / 10
                if decade[dec] >= cap { continue }
                var s = score[num - 1]
                if kind == .nexus {
                    s += 0.18 * pmiBoost(picked: picked, candidate: num)
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
                for num in 1...Self.pool where !picked.contains(num) && !banned.contains(num) {
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

    private func pmiBoost(picked: [Int], candidate: Int) -> Double {
        if picked.isEmpty || absorbed == 0 { return 0 }
        var s = 0.0
        for p in picked {
            let a = min(p, candidate) - 1
            let b = max(p, candidate) - 1
            let cij = co[a * Self.pool + b]
            let denom = (counts[a] * counts[b] + 1) / Double(absorbed)
            s += log((cij + 0.25) / denom)
        }
        return s / Double(picked.count)
    }

    private func blendWeighted(_ fields: [[Double]]) -> [Double] {
        var out = [Double](repeating: 0, count: Self.pool)
        for h in 0..<fields.count {
            let w = h < weights.count ? weights[h] : 0
            if w == 0 { continue }
            let f = fields[h]
            for i in 0..<Self.pool { out[i] += w * f[i] }
        }
        return out
    }

    // MARK: Constantes et outils numériques

    private static func makeHeads() -> [SwarmHead] {
        [
            BayesHead(memory: 10, variant: "a"), BayesHead(memory: 33, variant: "b"), BayesHead(memory: 200, variant: "c"),
            EwmaHead(memory: 8, variant: "a"), EwmaHead(memory: 25, variant: "b"), EwmaHead(memory: 64, variant: "c"),
            HawkesHead(memory: 2.3, variant: "a"), HawkesHead(memory: 3.9, variant: "b"), HawkesHead(memory: 8.7, variant: "c"),
            WeibullHead(k: 1.25), WeibullHead(k: 1.55),
            HazardHead(), GapZHead(),
            SpectralHead(short: 16, long: 64, momentum: false),
            SpectralHead(short: 8, long: 32, momentum: true),
            MarkovHead(k: 1), MarkovHead(k: 3), StreakHead(),
            CopairHead(),
            AcpHead(axis: 1), AcpHead(axis: 2),
            AntiHead(base: EwmaHead(memory: 25, variant: "b")),
            AntiHead(base: HawkesHead(memory: 3.9, variant: "b")),
            PressureHead(),
            AdjacencyHead(), RowPressureHead(),
        ]
    }

    // Paires adjacentes du tirage sur le tableau officiel (chaque arête
    // comptée une fois : vers le bas dans la colonne, vers la droite).
    private static func adjacentPairs(_ drawn: Set<Int>) -> Double {
        var c = 0.0
        for n in drawn {
            let row = (n - 1) % 10
            if row < 9, drawn.contains(n + 1) { c += 1 }
            if n <= pool - 10, drawn.contains(n + 10) { c += 1 }
        }
        return c
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
        for x in src {
            let d = x - m
            v += d * d
        }
        let s = sqrt(v / Double(n))
        let denom = s == 0 ? 1 : s
        return src.map { ($0 - m) / denom }
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
}

// Variante « recalcul complet » : un moteur neuf rejoue tout l'historique.
// Référence des tests et passe de réconciliation de l'incrémental.
enum Swarm {
    static func run(_ drawsNewestFirst: [Draw]) -> OracleResult {
        SwarmEngine().update(drawsNewestFirst)
    }
}
