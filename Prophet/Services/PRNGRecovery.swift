import Foundation

// Reconstruction d'état de générateur.
//
// Tente ce qui a réellement fonctionné dans l'histoire des loteries et des
// casinos en ligne : retrouver l'état interne d'un générateur
// pseudo-aléatoire faible à partir des seules sorties publiées.
//
// Familles couvertes : LCG glibc, LCG MSVC, java.util.Random (48 bits),
// xorshift32, xorshift128+, splitmix64, PCG32, Mersenne Twister 19937.
// Échantillonneurs : modulo avec rejet des doublons, multiplication-décalage,
// mélange de Fisher-Yates partiel — les trois façons standard de tirer 20
// numéros parmi 80 à partir d'un flux d'entiers.
// Amorçages : horloge du tirage en secondes (±2 h) et en millisecondes
// (±5 s), numéro de tirage, et toutes les graines de 0 à 2²⁰.
//
// Règle d'honnêteté : un état n'est déclaré trouvé que s'il reproduit le
// tirage cible EN ENTIER **et** le tirage suivant en continuant le même
// flux. Un préfixe partiel n'est pas une découverte : sur des dizaines de
// millions de candidats, le hasard en produit toujours un d'une douzaine
// de numéros — le rapport affiche d'ailleurs le préfixe attendu par pur
// hasard à côté du meilleur trouvé.

struct RecoveryResult {
    var candidatesTested: Int
    var familiesTested: Int
    var samplersTested: Int
    var bestPrefix: Int
    var bestFamily: String
    var bestSampler: String
    var bestSeedLabel: String
    var expectedPrefix: Double
    var solved: Bool
    var solvedDescription: String
    var elapsed: Double
    var targetDraw: Int
    var verdict: String
    var detail: String
}

// MARK: - Flux d'entiers

protocol StreamGenerator {
    mutating func next32() -> UInt32
}

struct GlibcLCG: StreamGenerator {
    var s: UInt32
    mutating func next32() -> UInt32 {
        s = (1103515245 &* s &+ 12345) & 0x7FFF_FFFF
        return s
    }
}

struct MsvcLCG: StreamGenerator {
    var s: UInt32
    mutating func next32() -> UInt32 {
        s = 214013 &* s &+ 2531011
        return (s >> 16) & 0x7FFF
    }
}

struct JavaRandom: StreamGenerator {
    private static let mask: UInt64 = (1 << 48) - 1
    var s: UInt64
    init(seed: UInt64) { s = (seed ^ 0x5DEECE66D) & Self.mask }
    mutating func next32() -> UInt32 {
        s = (s &* 0x5DEECE66D &+ 0xB) & Self.mask
        return UInt32(truncatingIfNeeded: s >> 16)
    }
}

struct Xorshift32: StreamGenerator {
    var s: UInt32
    mutating func next32() -> UInt32 {
        var x = s == 0 ? 0x9E37_79B9 : s
        x ^= x << 13
        x ^= x >> 17
        x ^= x << 5
        s = x
        return x
    }
}

struct SplitMix64: StreamGenerator {
    var s: UInt64
    mutating func next64() -> UInt64 {
        s = s &+ 0x9E37_79B9_7F4A_7C15
        var z = s
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
    mutating func next32() -> UInt32 {
        UInt32(truncatingIfNeeded: next64() >> 32)
    }
}

struct Xorshift128Plus: StreamGenerator {
    var s0: UInt64
    var s1: UInt64
    init(seed: UInt64) {
        var sm = SplitMix64(s: seed)
        s0 = sm.next64()
        s1 = sm.next64()
    }
    mutating func next32() -> UInt32 {
        var x = s0
        let y = s1
        s0 = y
        x ^= x << 23
        x ^= x >> 17
        x ^= y ^ (y >> 26)
        s1 = x
        return UInt32(truncatingIfNeeded: (x &+ y) >> 32)
    }
}

struct Pcg32: StreamGenerator {
    var state: UInt64
    var inc: UInt64 = 1442695040888963407
    mutating func next32() -> UInt32 {
        let old = state
        state = old &* 6364136223846793005 &+ inc
        let xorshifted = UInt32(truncatingIfNeeded: ((old >> 18) ^ old) >> 27)
        let rot = UInt32(truncatingIfNeeded: old >> 59)
        return (xorshifted >> rot) | (xorshifted << ((~rot &+ 1) & 31))
    }
}

struct MT19937: StreamGenerator {
    private var mt = [UInt32](repeating: 0, count: 624)
    private var idx = 624
    init(seed: UInt32) {
        mt[0] = seed
        for i in 1..<624 {
            mt[i] = 1812433253 &* (mt[i - 1] ^ (mt[i - 1] >> 30)) &+ UInt32(i)
        }
    }
    mutating func next32() -> UInt32 {
        if idx >= 624 { twist() }
        var y = mt[idx]
        idx += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C_5680
        y ^= (y << 15) & 0xEFC6_0000
        y ^= y >> 18
        return y
    }
    private mutating func twist() {
        for i in 0..<624 {
            let y = (mt[i] & 0x8000_0000) | (mt[(i + 1) % 624] & 0x7FFF_FFFF)
            mt[i] = mt[(i + 397) % 624] ^ (y >> 1)
            if y & 1 == 1 { mt[i] ^= 0x9908_B0DF }
        }
        idx = 0
    }
}

// MARK: - Attaque

enum PRNGRecovery {
    private static let pool = ProphetConst.poolSize
    private static let drawN = ProphetConst.drawSize

    enum Sampler: Int, CaseIterable {
        case modulo, multiplyShift, shuffle
        var label: String {
            switch self {
            case .modulo: return "modulo + rejet"
            case .multiplyShift: return "multiplication-décalage"
            case .shuffle: return "Fisher-Yates partiel"
            }
        }
    }

    // Masque binaire du tirage cible : appartenance en O(1).
    struct Target {
        var lo: UInt64 = 0
        var hi: UInt64 = 0
        init(_ nums: [Int]) {
            for n in nums where (1...80).contains(n) {
                let b = n - 1
                if b < 64 { lo |= UInt64(1) << UInt64(b) } else { hi |= UInt64(1) << UInt64(b - 64) }
            }
        }
        @inline(__always) func contains(_ n: Int) -> Bool {
            let b = n - 1
            if b < 0 || b >= 80 { return false }
            return b < 64 ? (lo >> UInt64(b)) & 1 == 1 : (hi >> UInt64(b - 64)) & 1 == 1
        }
    }

    // Longueur du préfixe du tirage cible reproduit par le flux, arrêt dès
    // le premier écart. Renvoie 20 si le tirage entier est reproduit.
    @inline(__always)
    private static func prefixByRejection<G: StreamGenerator>(
        _ gen: inout G, target: Target, multiplyShift: Bool
    ) -> Int {
        var lo: UInt64 = 0
        var hi: UInt64 = 0
        var matched = 0
        var guardSteps = 0
        while matched < drawN && guardSteps < 400 {
            guardSteps += 1
            let r = gen.next32()
            let n = multiplyShift
                ? Int((UInt64(r) &* UInt64(pool)) >> 32) + 1
                : Int(r % UInt32(pool)) + 1
            let b = n - 1
            let seen = b < 64 ? (lo >> UInt64(b)) & 1 : (hi >> UInt64(b - 64)) & 1
            if seen == 1 { continue }
            if b < 64 { lo |= UInt64(1) << UInt64(b) } else { hi |= UInt64(1) << UInt64(b - 64) }
            if target.contains(n) { matched += 1 } else { return matched }
        }
        return matched
    }

    @inline(__always)
    private static func prefixByShuffle<G: StreamGenerator>(
        _ gen: inout G, target: Target, perm: inout [Int], undo: inout [Int]
    ) -> Int {
        undo.removeAll(keepingCapacity: true)
        var matched = 0
        for i in 0..<drawN {
            let span = UInt32(pool - i)
            let r = Int(gen.next32() % span) + i
            if r != i {
                perm.swapAt(i, r)
                undo.append(i)
                undo.append(r)
            }
            if target.contains(perm[i] + 1) { matched += 1 } else { break }
        }
        var k = undo.count - 2
        while k >= 0 {
            perm.swapAt(undo[k], undo[k + 1])
            k -= 2
        }
        return matched
    }

    // Un état candidat n'est retenu que s'il reproduit aussi le tirage
    // suivant en continuant le même flux.
    private static func confirms<G: StreamGenerator>(
        _ gen: inout G, sampler: Sampler, next: Target, perm: inout [Int], undo: inout [Int]
    ) -> Bool {
        switch sampler {
        case .modulo: return prefixByRejection(&gen, target: next, multiplyShift: false) == drawN
        case .multiplyShift: return prefixByRejection(&gen, target: next, multiplyShift: true) == drawN
        case .shuffle: return prefixByShuffle(&gen, target: next, perm: &perm, undo: &undo) == drawN
        }
    }

    private struct SeedRange {
        var label: String
        var from: UInt64
        var count: Int
        var heavyOK: Bool // familles à initialisation coûteuse (MT)
    }

    static func attack(_ drawsNewestFirst: [Draw], budget: TimeInterval = 12) -> RecoveryResult {
        let ordered = drawsNewestFirst.sorted { $0.drawNumber < $1.drawNumber }
        guard ordered.count >= 2 else {
            return empty("Historique insuffisant", "Deux tirages consécutifs au minimum sont nécessaires.")
        }
        let targetDraw = ordered[ordered.count - 2]
        let nextDraw = ordered[ordered.count - 1]
        let target = Target(targetDraw.numbers)
        let confirm = Target(nextDraw.numbers)

        let ts: UInt64 = {
            guard let d = Zurich.parseISO(targetDraw.drawDate) else { return 0 }
            return UInt64(max(0, d.timeIntervalSince1970))
        }()

        var ranges: [SeedRange] = [
            SeedRange(label: "horloge ±2 h (s)", from: ts &- 7200, count: 14401, heavyOK: true),
            SeedRange(label: "horloge ±5 s (ms)", from: ts &* 1000 &- 5000, count: 10001, heavyOK: true),
            SeedRange(label: "n° de tirage", from: UInt64(max(0, targetDraw.drawNumber - 8)), count: 17, heavyOK: true),
            SeedRange(label: "petites graines", from: 0, count: 1 << 20, heavyOK: false),
        ]
        if ts == 0 { ranges.removeFirst(2) }

        let started = Date()
        var tested = 0
        var bestPrefix = -1
        var bestFamily = "—"
        var bestSampler = "—"
        var bestSeed = "—"
        var solved = false
        var solvedDescription = ""

        var perm = Array(0..<pool)
        var undo: [Int] = []

        // Un balayage par famille : la fermeture construit le générateur
        // pour une graine donnée.
        func sweep(_ family: String, heavy: Bool, _ make: (UInt64) -> any StreamGenerator) {
            for sampler in Sampler.allCases {
                for range in ranges {
                    if heavy && !range.heavyOK { continue }
                    for k in 0..<range.count {
                        if solved { return }
                        if tested & 0xFFFF == 0, Date().timeIntervalSince(started) > budget { return }
                        let seed = range.from &+ UInt64(k)
                        var gen = make(seed)
                        tested += 1
                        let prefix: Int
                        switch sampler {
                        case .modulo:
                            prefix = prefixByRejection(&gen, target: target, multiplyShift: false)
                        case .multiplyShift:
                            prefix = prefixByRejection(&gen, target: target, multiplyShift: true)
                        case .shuffle:
                            prefix = prefixByShuffle(&gen, target: target, perm: &perm, undo: &undo)
                        }
                        if prefix > bestPrefix {
                            bestPrefix = prefix
                            bestFamily = family
                            bestSampler = sampler.label
                            bestSeed = range.label
                        }
                        if prefix == drawN,
                           confirms(&gen, sampler: sampler, next: confirm, perm: &perm, undo: &undo) {
                            solved = true
                            solvedDescription = "\(family) · \(sampler.label) · graine \(seed) (\(range.label))"
                            return
                        }
                    }
                }
            }
        }

        sweep("LCG glibc", heavy: false) { GlibcLCG(s: UInt32(truncatingIfNeeded: $0)) }
        sweep("LCG MSVC", heavy: false) { MsvcLCG(s: UInt32(truncatingIfNeeded: $0)) }
        sweep("java.util.Random", heavy: false) { JavaRandom(seed: $0) }
        sweep("xorshift32", heavy: false) { Xorshift32(s: UInt32(truncatingIfNeeded: $0)) }
        sweep("xorshift128+", heavy: false) { Xorshift128Plus(seed: $0) }
        sweep("splitmix64", heavy: false) { SplitMix64(s: $0) }
        sweep("PCG32", heavy: false) { Pcg32(state: $0) }
        sweep("Mersenne Twister", heavy: true) { MT19937(seed: UInt32(truncatingIfNeeded: $0)) }

        let elapsed = Date().timeIntervalSince(started)
        // Préfixe le plus long attendu par pur hasard : chaque numéro tombe
        // dans la cible avec p ≈ 1/4, donc max ≈ log₄(candidats).
        let expected = tested > 1 ? log(Double(tested)) / log(4) : 0

        let verdict: String
        let detail: String
        if solved {
            verdict = "ÉTAT RECONSTRUIT"
            detail = "Un générateur reproduit le tirage #\(targetDraw.drawNumber) en entier et confirme le #\(nextDraw.drawNumber) en continuant le flux : \(solvedDescription). C'est un défaut critique du générateur, à signaler à l'exploitant."
        } else {
            verdict = "Aucun état reconstruit"
            detail = "\(tested) états candidats testés sur 8 familles et 3 échantillonneurs. Le meilleur candidat reproduit \(max(0, bestPrefix)) numéros sur 20, alors que le pur hasard en produit \(String(format: "%.1f", expected)) sur ce nombre d'essais : aucun signal. La source ne se comporte comme aucun générateur pseudo-aléatoire à état court — elle est compatible avec un CSPRNG ou un générateur quantique, dont l'état n'est pas reconstructible depuis les sorties."
        }

        return RecoveryResult(
            candidatesTested: tested,
            familiesTested: 8,
            samplersTested: Sampler.allCases.count,
            bestPrefix: max(0, bestPrefix),
            bestFamily: bestFamily,
            bestSampler: bestSampler,
            bestSeedLabel: bestSeed,
            expectedPrefix: expected,
            solved: solved,
            solvedDescription: solvedDescription,
            elapsed: elapsed,
            targetDraw: targetDraw.drawNumber,
            verdict: verdict,
            detail: detail
        )
    }

    private static func empty(_ verdict: String, _ detail: String) -> RecoveryResult {
        RecoveryResult(
            candidatesTested: 0, familiesTested: 0, samplersTested: 0,
            bestPrefix: 0, bestFamily: "—", bestSampler: "—", bestSeedLabel: "—",
            expectedPrefix: 0, solved: false, solvedDescription: "",
            elapsed: 0, targetDraw: 0, verdict: verdict, detail: detail
        )
    }
}
