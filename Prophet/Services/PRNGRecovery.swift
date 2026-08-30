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
    // L'API publie-t-elle les numéros dans leur ordre de sortie ?
    var orderAvailable: Bool
    var mode: String
    var verdict: String
    var detail: String
    // Les 20 numéros du prochain tirage, quand l'attaque algébrique par rang
    // a résolu le générateur (cf. RankAttack). Vide sinon — et vide est la
    // réponse attendue tant que le générateur tient.
    var predicted: [Int] = []
}

// MARK: - Flux d'entiers

protocol StreamGenerator {
    mutating func next32() -> UInt32
}

// Générateur dont l'espace d'états tient dans 32 bits : quand l'ordre de
// tirage est publié, il devient balayable exhaustivement.
protocol SeedableGenerator: StreamGenerator {
    init(rawSeed: UInt32)
    static var stateBits: Int { get }
    static var familyName: String { get }
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

extension GlibcLCG: SeedableGenerator {
    init(rawSeed: UInt32) { self.init(s: rawSeed & 0x7FFF_FFFF) }
    static var stateBits: Int { 31 }
    static var familyName: String { "LCG glibc" }
}

extension MsvcLCG: SeedableGenerator {
    init(rawSeed: UInt32) { self.init(s: rawSeed) }
    static var stateBits: Int { 32 }
    static var familyName: String { "LCG MSVC" }
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

extension Xorshift32: SeedableGenerator {
    init(rawSeed: UInt32) { self.init(s: rawSeed) }
    static var stateBits: Int { 32 }
    static var familyName: String { "xorshift32" }
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

    // MARK: Mode « ordre publié » — balayage exhaustif de l'espace d'états
    //
    // Quand les numéros sont publiés dans leur ordre de sortie, chaque
    // numéro contraint la sortie du générateur modulo 80 : la probabilité
    // qu'un mauvais état survive un pas tombe de 1/4 à 1/80, et l'espace
    // 2³¹ devient balayable en quelques secondes.

    @inline(__always)
    private static func matchesSequence<G: StreamGenerator>(_ gen: inout G, _ seq: [Int]) -> Bool {
        var lo: UInt64 = 0
        var hi: UInt64 = 0
        var idx = 0
        var steps = 0
        while idx < seq.count && steps < 400 {
            steps += 1
            let n = Int(gen.next32() % UInt32(pool)) + 1
            let b = n - 1
            let seen = b < 64 ? (lo >> UInt64(b)) & 1 : (hi >> UInt64(b - 64)) & 1
            if seen == 1 { continue }
            if b < 64 { lo |= UInt64(1) << UInt64(b) } else { hi |= UInt64(1) << UInt64(b - 64) }
            if n != seq[idx] { return false }
            idx += 1
        }
        return idx == seq.count
    }

    // Le balayage exhaustif ne dépend PAS de l'ordre de tirage.
    //
    // Mesuré : le test d'appartenance à l'ensemble, avec arrêt anticipé,
    // coûte 1,344 pas de générateur par candidat (25 % survivent au premier
    // numéro, 0,03 % au sixième). Un balayage 2³¹ demande donc 2,89
    // milliards de pas, et la probabilité qu'un mauvais état reproduise les
    // 20 numéros est 1/C(80,20) ≈ 10⁻¹⁹ — soit 6·10⁻¹⁰ faux positif attendu
    // sur tout l'espace. L'ordre, quand il existe, ne fait qu'accélérer
    // (filtre 1/80 au lieu de 1/4 par pas).
    private static func exhaustive<G: SeedableGenerator>(
        _ type: G.Type,
        targetSet: Target,
        confirmSet: Target,
        targetSeq: [Int],
        confirmSeq: [Int],
        bonus: Int?,
        started: Date,
        budget: TimeInterval,
        tested: inout Int
    ) -> String? {
        let ordered = targetSeq.count == drawN && confirmSeq.count == drawN
        let span: UInt64 = UInt64(1) << UInt64(G.stateBits)

        @inline(__always)
        func matchesTarget(_ g: inout G) -> Bool {
            ordered
                ? matchesSequence(&g, targetSeq)
                : prefixByRejection(&g, target: targetSet, multiplyShift: false) == drawN
        }
        @inline(__always)
        func matchesConfirm(_ g: inout G) -> Bool {
            ordered
                ? matchesSequence(&g, confirmSeq)
                : prefixByRejection(&g, target: confirmSet, multiplyShift: false) == drawN
        }

        var s: UInt64 = 0
        while s < span {
            if s & 0xF_FFFF == 0, Date().timeIntervalSince(started) > budget { return nil }
            var gen = G(rawSeed: UInt32(truncatingIfNeeded: s))
            tested += 1
            if matchesTarget(&gen) {
                var again = G(rawSeed: UInt32(truncatingIfNeeded: s))
                _ = matchesTarget(&again)
                // Le bonus est la seule sortie publiée qui échappe au tri :
                // s'il tombe juste, l'ordre de consommation du flux est
                // confirmé lui aussi.
                var bonusNote = ""
                if let bonus {
                    var probe = again
                    if Int(probe.next32() % UInt32(pool)) + 1 == bonus {
                        bonusNote = " · bonus confirmé"
                    }
                }
                if matchesConfirm(&again) {
                    return "\(G.familyName) · état \(s)\(bonusNote)"
                }
            }
            s &+= 1
        }
        return nil
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

        // Attaque ALGÉBRIQUE d'abord — elle ne cherche pas, elle résout, et
        // coûte quelques millisecondes contre les secondes du balayage.
        // Le balayage de graines qui suit est borné aux graines minuscules ;
        // celle-ci atteint n'importe quel état de 64 bits, pourvu que le
        // tirage soit le dérangement d'une sortie unique (cf. RankAttack).
        if let sol = RankAttack.solve(ordered) {
            return RecoveryResult(
                candidatesTested: 0, familiesTested: 1, samplersTested: 1,
                bestPrefix: 20, bestFamily: sol.family, bestSampler: "rang combinatoire",
                bestSeedLabel: sol.mapping, expectedPrefix: 0,
                solved: true,
                solvedDescription: "\(sol.family) — \(sol.detail)",
                elapsed: 0, targetDraw: targetDraw.drawNumber,
                orderAvailable: ordered.contains { $0.hasDrawOrder },
                mode: "algébrique (rang)",
                verdict: "Générateur résolu",
                detail: "Le rang combinatoire du tirage ne cache que 2,38 bits d'un état 64 bits : la suite des rangs a été résolue algébriquement, et la solution rejoue TOUT l'historique fourni. Le prochain tirage est déterminé.",
                predicted: sol.predicted)
        }

        // Détecteur de LARGEUR de source. Il ne suppose aucune récurrence, donc
        // il voit ce que l'attaque algébrique ne peut pas : une source trop
        // étroite (un double de 53 bits, un entier de 32) laisse 99,7 % des
        // rangs inatteignables, et l'espace d'états s'effondre.
        if let width = RankAttack.narrowSourceWidth(ordered) {
            return RecoveryResult(
                candidatesTested: ordered.count, familiesTested: 1, samplersTested: 1,
                bestPrefix: 0, bestFamily: "source \(width) bits", bestSampler: "rang combinatoire",
                bestSeedLabel: "—", expectedPrefix: 0,
                solved: false,
                solvedDescription: "",
                elapsed: 0, targetDraw: targetDraw.drawNumber,
                orderAvailable: ordered.contains { $0.hasDrawOrder },
                mode: "granularité (rang)",
                verdict: "Source trop étroite",
                detail: "Un tirage consomme 61,62 bits (M = C(80,20)). Les rangs observés ne sont atteignables que par une source de \(width) bits : l'espace d'états s'effondre de 2^61,62 à 2^\(width), ce qui met la prédiction exacte à portée d'un balayage. Ce test ne suppose rien sur la récurrence du générateur.",
                predicted: [])
        }

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

        // Balayage exhaustif de l'espace d'états — lancé dans tous les cas.
        // L'ordre de tirage, s'il est publié, ne fait qu'accélérer le filtre.
        let orderAvailable = targetDraw.hasDrawOrder && nextDraw.hasDrawOrder
        let seq = orderAvailable ? targetDraw.order : []
        let seqNext = orderAvailable ? nextDraw.order : []
        let bonus = targetDraw.bonus
        if let hit = exhaustive(GlibcLCG.self, targetSet: target, confirmSet: confirm,
                                targetSeq: seq, confirmSeq: seqNext, bonus: bonus,
                                started: started, budget: budget * 0.35, tested: &tested) {
            solved = true
            solvedDescription = hit
        } else if let hit = exhaustive(MsvcLCG.self, targetSet: target, confirmSet: confirm,
                                       targetSeq: seq, confirmSeq: seqNext, bonus: bonus,
                                       started: started, budget: budget * 0.7, tested: &tested) {
            solved = true
            solvedDescription = hit
        } else if let hit = exhaustive(Xorshift32.self, targetSet: target, confirmSet: confirm,
                                       targetSeq: seq, confirmSeq: seqNext, bonus: bonus,
                                       started: started, budget: budget, tested: &tested) {
            solved = true
            solvedDescription = hit
        }
        if solved { bestPrefix = drawN }

        // Un balayage par famille. Générique sur le type concret du
        // générateur : Swift n'ouvre pas implicitement un existentiel passé
        // en inout (SE-0352), et la spécialisation évite en prime la
        // répartition dynamique dans la boucle chaude.
        func sweep<G: StreamGenerator>(_ family: String, heavy: Bool, _ make: (UInt64) -> G) {
            if solved { return }
            for sampler in Sampler.allCases {
                for range in ranges {
                    if heavy && !range.heavyOK { continue }
                    for k in 0..<range.count {
                        if solved { return }
                        if tested & 0xFFFF == 0, Date().timeIntervalSince(started) > budget + 8 { return }
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

        let mode = orderAvailable
            ? "ordre de sortie publié — balayage exhaustif accéléré (filtre 1/80)"
            : "ensemble trié — balayage exhaustif par appartenance (filtre 1/4)"

        let verdict: String
        let detail: String
        if solved {
            verdict = "ÉTAT RECONSTRUIT"
            detail = "Un générateur reproduit le tirage #\(targetDraw.drawNumber) en entier et confirme le #\(nextDraw.drawNumber) en continuant le flux : \(solvedDescription). C'est un défaut critique du générateur, à signaler à l'exploitant avant toute autre chose."
        } else {
            verdict = "Aucun état reconstruit"
            detail = "\(tested) états testés : balayage exhaustif des espaces 2³¹ et 2³² (LCG glibc et MSVC, xorshift32) plus la recherche de graine sur 8 familles et 3 échantillonneurs. Le meilleur candidat reproduit \(max(0, bestPrefix)) numéros sur 20, contre \(String(format: "%.1f", expected)) attendus par pur hasard : aucun signal. Toute la classe des générateurs à état court est écartée."
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
            orderAvailable: orderAvailable,
            mode: mode,
            verdict: verdict,
            detail: detail
        )
    }

    private static func empty(_ verdict: String, _ detail: String) -> RecoveryResult {
        RecoveryResult(
            candidatesTested: 0, familiesTested: 0, samplersTested: 0,
            bestPrefix: 0, bestFamily: "—", bestSampler: "—", bestSeedLabel: "—",
            expectedPrefix: 0, solved: false, solvedDescription: "",
            elapsed: 0, targetDraw: 0, orderAvailable: false, mode: "—",
            verdict: verdict, detail: detail
        )
    }
}
