import Foundation

// Attaque algébrique par RANG COMBINATOIRE.
//
// PRNGRecovery cherche une graine : il énumère des candidats et rejoue la
// génération. C'est structurellement borné aux graines minuscules — un état
// de 64 bits lui est fermé pour toujours.
//
// Cette attaque-ci ne cherche pas : elle RÉSOUT. Le levier est arithmétique.
// Un tirage de 20 numéros parmi 80 a un rang combinatoire dans [0, M) avec
//
//     M = C(80, 20) = 3 535 316 142 212 174 320 ≈ 2^61,6165
//
// Si l'implémentation « dérange » (unranking) une seule sortie de 64 bits
// pour produire le tirage — un schéma très répandu —, alors le rang publié
// révèle 61,62 des 64 bits d'état : **il n'en manque que 2,38**. Chaque
// tirage laisse donc au plus ⌈2^64/M⌉ = 6 états candidats, et trois tirages
// consécutifs suffisent à résoudre un LCG en deux lignes :
//
//     a = (s₂ − s₁) · (s₁ − s₀)⁻¹  mod 2^b
//     c = s₁ − a·s₀                mod 2^b
//
// puis on confirme sur 20 tirages suivants — une fausse solution y survit
// avec probabilité ~M⁻²⁰ ≈ 10⁻³⁷⁰.
//
// Deux propriétés qui font la différence entre un outil et un jouet :
//
//   * Le PAS du générateur entre deux tirages n'a pas besoin d'être connu :
//     si l'état avance de j pas, la relation reste un LCG de multiplicateur
//     a^j. Tous les pas fixes sont donc couverts automatiquement.
//   * Deux mappings sont testés — `s mod M` et `⌊s·M / 2^b⌋` — parce que les
//     deux se rencontrent en production et ne donnent pas les mêmes candidats.
//
// Les familles à sortie INVERSIBLE (splitmix64, xorshift64*) tombent encore
// plus vite : on inverse la sortie pour retrouver l'état, et deux tirages
// consécutifs suffisent à vérifier la transition. java.util.Random est traité
// à part : son LCG 48 bits ne publie que les 32 bits de poids fort, donc un
// rang de 64 bits vaut deux sorties, et les 16 bits bas du premier état
// s'énumèrent (2¹⁶) — la seconde sortie les filtre à ~1 survivant.
//
// Le labo a validé chaque famille sur son propre générateur
// (`lab/experiments/h4_rangs.py`, `h5_familles.py`) : 12 témoins positifs sur
// 12, récupérés AVEC prédiction exacte du tirage suivant, et 0 fausse
// récupération sur 20 archives équitables.
//
// Angles morts, nommés plutôt que tus : MT19937 par rang (il faudrait 624
// sorties exactes, soit 6³¹² combinaisons), tout générateur dont l'état est
// plus large que la sortie (PCG64, xoshiro256), tout générateur
// cryptographique — et surtout, si le tirage n'est PAS le dérangement d'une
// sortie unique (rejet, Fisher-Yates, tirage physique), le rang n'est pas la
// sortie du générateur et toute cette classe est muette.

struct RankSolution {
    var family: String
    var mapping: String
    var detail: String
    /// Les 20 numéros du prochain tirage, si l'état a été résolu.
    var predicted: [Int]
}

enum RankAttack {
    static let pool = 80
    static let drawn = 20

    // C(n, k) pour n ≤ 80, k ≤ 20. Le plus grand vaut C(80,20) ≈ 3,5·10¹⁸,
    // qui tient dans UInt64 (max ≈ 1,8·10¹⁹).
    static let binomial: [[UInt64]] = {
        var t = [[UInt64]](repeating: [UInt64](repeating: 0, count: drawn + 1), count: pool + 1)
        for n in 0...pool {
            t[n][0] = 1
            for k in 1...drawn where k <= n {
                t[n][k] = t[n - 1][k - 1] + (k <= n - 1 ? t[n - 1][k] : 0)
            }
        }
        return t
    }()

    static var modulus: UInt64 { binomial[pool][drawn] }

    /// Rang colex d'un tirage trié — bijection sur [0, M).
    static func rank(_ numbers: [Int]) -> UInt64? {
        let s = numbers.sorted()
        guard s.count == drawn, s.first! >= 1, s.last! <= pool else { return nil }
        var r: UInt64 = 0
        for (i, n) in s.enumerated() { r &+= binomial[n - 1][i + 1] }
        return r
    }

    /// Inverse exact de `rank` : du rang vers les 20 numéros.
    static func unrank(_ value: UInt64) -> [Int] {
        var r = value
        var out: [Int] = []
        var i = drawn
        while i >= 1 {
            var c = i - 1
            while c + 1 <= pool, binomial[c + 1][i] <= r { c += 1 }
            out.append(c + 1)
            r &-= binomial[c][i]
            i -= 1
        }
        return out.sorted()
    }

    private static func mask(_ b: Int) -> UInt64 {
        b >= 64 ? UInt64.max : (UInt64(1) << UInt64(b)) &- 1
    }

    /// États compatibles avec un rang observé — au plus 6.
    static func candidates(_ r: UInt64, b: Int, floorMapping: Bool) -> [UInt64] {
        let m = mask(b)
        var out: [UInt64] = []
        if !floorMapping {
            var s = r
            while s <= m {
                out.append(s)
                let (next, over) = s.addingReportingOverflow(modulus)
                if over { break }
                s = next
            }
            return out
        }
        // ⌊s·M / 2^b⌋ == r  ⇔  s ∈ [⌈r·2^b / M⌉, ⌈(r+1)·2^b / M⌉)
        func ceilDiv(_ hi: UInt64, _ lo: UInt64) -> UInt64 {
            // ⌈(hi·2^64 + lo) / M⌉ réduit ensuite au module voulu.
            let q = M128.divide(hi: hi, lo: lo, by: modulus)
            return q.remainder == 0 ? q.quotient : q.quotient &+ 1
        }
        let shift = UInt64(64 - b)
        let loA = ceilDiv(r >> shift, r << UInt64(b))
        let rb = r &+ 1
        var s = loA
        // r = M−1 est le rang maximal : la borne haute vaut alors 2^b, qui ne
        // tient pas dans UInt64 pour b = 64 — et `dividingFullWidth` piégerait
        // sur hi == diviseur. Borner par le masque est exact dans ce cas.
        if rb >= modulus {
            while s <= m {
                out.append(s)
                if s == m { break }
                s &+= 1
            }
            return out
        }
        let loB = ceilDiv(rb >> shift, rb << UInt64(b))
        while s < loB, s <= m {
            out.append(s)
            s &+= 1
        }
        return out
    }

    private static func rankOf(_ s: UInt64, b: Int, floorMapping: Bool) -> UInt64 {
        if !floorMapping { return s % modulus }
        let full = s.multipliedFullWidth(by: modulus)
        return b >= 64 ? full.high : (full.high << UInt64(64 - b)) | (full.low >> UInt64(b))
    }

    /// Inverse de x modulo 2^64 par itération de Newton — x doit être impair.
    static func inverse64(_ x: UInt64) -> UInt64? {
        guard x % 2 == 1 else { return nil }
        var inv: UInt64 = 1
        for _ in 0..<7 { inv = inv &* (2 &- x &* inv) }
        return inv
    }

    // MARK: LCG

    private static func solveLCG(_ ranks: [UInt64], b: Int, floorMapping: Bool,
                                 starts: Int, confirm: Int) -> RankSolution? {
        let m = mask(b)
        let limit = min(starts, max(0, ranks.count - confirm - 3))
        guard limit > 0 else { return nil }
        for t0 in 0..<limit {
            let c0 = candidates(ranks[t0], b: b, floorMapping: floorMapping)
            let c1 = candidates(ranks[t0 + 1], b: b, floorMapping: floorMapping)
            let c2 = candidates(ranks[t0 + 2], b: b, floorMapping: floorMapping)
            for s0 in c0 {
                for s1 in c1 {
                    guard let inv = inverse64((s1 &- s0) & m) else { continue }
                    for s2 in c2 {
                        let a = ((s2 &- s1) & m) &* inv & m
                        let c = (s1 &- a &* s0) & m
                        var s = s2
                        var good = true
                        for j in 3..<(3 + confirm) {
                            s = (a &* s &+ c) & m
                            if rankOf(s, b: b, floorMapping: floorMapping) != ranks[t0 + j] {
                                good = false
                                break
                            }
                        }
                        guard good else { continue }
                        // Rejoue jusqu'au dernier tirage connu : prédire le
                        // prochain exige que la chaîne tienne jusqu'au bout.
                        // Une rupture invalide CE candidat, pas la recherche
                        // entière — sinon un seul faux départ fermerait les
                        // autres modules et les autres mappings.
                        for j in (3 + confirm)..<(ranks.count - t0) {
                            s = (a &* s &+ c) & m
                            if rankOf(s, b: b, floorMapping: floorMapping) != ranks[t0 + j] {
                                good = false
                                break
                            }
                        }
                        guard good else { continue }
                        s = (a &* s &+ c) & m
                        return RankSolution(
                            family: "LCG 2^\(b)",
                            mapping: floorMapping ? "⌊s·M/2^\(b)⌋" : "s mod M",
                            detail: "a = \(a), c = \(c)",
                            predicted: unrank(rankOf(s, b: b, floorMapping: floorMapping)))
                    }
                }
            }
        }
        return nil
    }

    // MARK: Sorties inversibles

    private static let golden: UInt64 = 0x9E37_79B9_7F4A_7C15
    private static let smA: UInt64 = 0xBF58_476D_1CE4_E5B9
    private static let smB: UInt64 = 0x94D0_49BB_1331_11EB
    private static let xsMul: UInt64 = 0x2545_F491_4F6C_DD1D

    private static func unshiftRight(_ y: UInt64, _ k: UInt64) -> UInt64 {
        var x = y
        for _ in 0..<(64 / Int(k) + 1) { x = y ^ (x >> k) }
        return x
    }

    static func splitmixOutput(_ state: UInt64) -> UInt64 {
        var w = state &+ golden
        w = (w ^ (w >> 30)) &* smA
        w = (w ^ (w >> 27)) &* smB
        return w ^ (w >> 31)
    }

    /// Inverse la sortie splitmix64 : rend l'état DÉJÀ incrémenté.
    static func splitmixState(_ out: UInt64) -> UInt64 {
        var w = unshiftRight(out, 31)
        w = w &* inverse64(smB)!
        w = unshiftRight(w, 27)
        w = w &* inverse64(smA)!
        return unshiftRight(w, 30)
    }

    static func xorshiftStep(_ state: UInt64) -> UInt64 {
        var s = state
        s ^= s >> 12
        s ^= s << 25
        s ^= s >> 27
        return s
    }

    private static func solveInvertible(_ ranks: [UInt64], floorMapping: Bool,
                                        starts: Int, confirm: Int) -> RankSolution? {
        let limit = min(starts, max(0, ranks.count - confirm - 2))
        guard limit > 0 else { return nil }
        for family in ["splitmix64", "xorshift64*"] {
            for t0 in 0..<limit {
                let c0 = candidates(ranks[t0], b: 64, floorMapping: floorMapping)
                let c1 = candidates(ranks[t0 + 1], b: 64, floorMapping: floorMapping)
                for o0 in c0 {
                    let z0 = family == "splitmix64" ? splitmixState(o0)
                                                    : o0 &* inverse64(xsMul)!
                    for o1 in c1 {
                        let z1 = family == "splitmix64" ? splitmixState(o1)
                                                        : o1 &* inverse64(xsMul)!
                        let linked = family == "splitmix64" ? (z1 &- z0 == golden)
                                                            : (xorshiftStep(z0) == z1)
                        guard linked else { continue }
                        var z = z1
                        var good = true
                        var j = 2
                        while j < ranks.count - t0 {
                            let o: UInt64
                            if family == "splitmix64" {
                                o = splitmixOutput(z)
                                z = z &+ golden
                            } else {
                                z = xorshiftStep(z)
                                o = z &* xsMul
                            }
                            if rankOf(o, b: 64, floorMapping: floorMapping) != ranks[t0 + j] {
                                good = false
                                break
                            }
                            j += 1
                        }
                        guard good, j >= 2 + confirm else { continue }
                        let o: UInt64
                        if family == "splitmix64" { o = splitmixOutput(z) } else { o = xorshiftStep(z) &* xsMul }
                        return RankSolution(
                            family: family,
                            mapping: floorMapping ? "⌊s·M/2⁶⁴⌋" : "s mod M",
                            detail: "état résolu par inversion de la sortie",
                            predicted: unrank(rankOf(o, b: 64, floorMapping: floorMapping)))
                    }
                }
            }
        }
        return nil
    }

    // MARK: java.util.Random

    private static let javaA: UInt64 = 0x5DEE_CE66D
    private static let javaC: UInt64 = 0xB
    private static let java48: UInt64 = (UInt64(1) << 48) &- 1

    private static func javaNext32(_ state: UInt64) -> (UInt64, UInt64) {
        let s = (state &* javaA &+ javaC) & java48
        return (s, s >> 16)
    }

    private static func solveJava(_ ranks: [UInt64], floorMapping: Bool,
                                  starts: Int, confirm: Int) -> RankSolution? {
        let limit = min(starts, max(0, ranks.count - confirm - 1))
        guard limit > 0 else { return nil }
        for t0 in 0..<limit {
            for v in candidates(ranks[t0], b: 64, floorMapping: floorMapping) {
                let hi = v >> 32, lo = v & 0xFFFF_FFFF
                for k in 0..<(UInt64(1) << 16) {
                    let s1 = (hi << 16) | k
                    let (s2, out2) = javaNext32(s1)
                    guard out2 == lo else { continue }
                    var s = s2
                    var good = true
                    var j = 1
                    while j < ranks.count - t0 {
                        let (sa, a) = javaNext32(s)
                        let (sb, b2) = javaNext32(sa)
                        s = sb
                        if rankOf((a << 32) | b2, b: 64, floorMapping: floorMapping) != ranks[t0 + j] {
                            good = false
                            break
                        }
                        j += 1
                    }
                    guard good, j >= 1 + confirm else { continue }
                    let (sa, a) = javaNext32(s)
                    let (_, b2) = javaNext32(sa)
                    return RankSolution(
                        family: "java.util.Random",
                        mapping: floorMapping ? "⌊s·M/2⁶⁴⌋" : "s mod M",
                        detail: "LCG 48 bits, 32 bits hauts publiés, 2 sorties par tirage",
                        predicted: unrank(rankOf((a << 32) | b2, b: 64, floorMapping: floorMapping)))
                }
            }
        }
        return nil
    }

    // MARK: Largeur de la source — un détecteur qui ne suppose aucune récurrence

    /// Le rang r est-il de la forme ⌊k·M / 2^B⌋ pour un entier k < 2^B ?
    ///
    /// C'est le test de GRANULARITÉ. Un tirage honnête consomme les 61,62 bits
    /// de M ; si la source n'en fournit que B, les rangs atteignables ne sont
    /// que 2^B valeurs sur 2^61,6 et un rang réel évite tous les autres. À
    /// B = 53 — un double, c'est-à-dire `Math.random()` en JavaScript ou
    /// `random.random()` en Python — la densité tombe à 1/392 : sur quelques
    /// centaines de tirages, la séparation est totale.
    ///
    /// Contrairement à `solve`, ce test ne suppose RIEN sur la récurrence du
    /// générateur — ni LCG, ni xorshift, ni rien. Il ne mesure que la largeur
    /// de la source, et se déclencherait donc là où l'attaque algébrique est
    /// muette. Le labo l'a séparé sur témoins : 2 000/2 000 sur des archives
    /// fabriquées à 32, 48 et 53 bits, densité théorique exacte sur des
    /// archives honnêtes (`lab/experiments/h6_granularite.py`).
    static func reachable(_ r: UInt64, bits b: Int) -> Bool {
        guard b < 62 else { return true }          // 2^62 > M : tout est atteignable
        let twoB = UInt64(1) << UInt64(b)
        let prod = r.multipliedFullWidth(by: twoB)
        let q = M128.divide(hi: prod.high, lo: prod.low, by: modulus)
        let kMin = q.remainder == 0 ? q.quotient : q.quotient &+ 1
        guard kMin < twoB else { return false }
        return rankOf(kMin, b: b, floorMapping: true) == r
    }

    /// Largeur de source détectée, ou nil si le tirage consomme ses bits pleins.
    ///
    /// Un déclenchement serait majeur : l'espace d'états s'effondrerait de
    /// 2^61,62 à 2^B, et la prédiction exacte redeviendrait une question de
    /// force brute — 2^32 tient en une seconde.
    static func narrowSourceWidth(_ draws: [Draw]) -> Int? {
        let ranks = draws.compactMap { rank($0.numbers) }
        guard ranks.count >= 24 else { return nil }
        let n = Double(ranks.count)
        let widths = [24, 31, 32, 48, 53, 56, 60, 61]
        var rate: [Int: Double] = [:]
        var share: [Int: Double] = [:]
        for b in widths {
            share[b] = Double(UInt64(1) << UInt64(b)) / Double(modulus)
            rate[b] = Double(ranks.filter { reachable($0, bits: b) }.count) / n
        }
        // Sous une source de B bits, le taux vaut EXACTEMENT 1 à B, et ~1/2 à
        // B−1 (un rang atteignable à B−1 l'est aussi à B, via k pair). Exiger
        // un taux quasi total nomme donc la bonne largeur, là où un simple
        // test de significativité renverrait B−1.
        for b in widths where share[b]! < 0.8 && rate[b]! >= 0.9 { return b }
        // Filet de sécurité : une source qui n'est pas exactement une
        // puissance de deux peut rester très au-dessus du hasard sans
        // atteindre 1. On la signale quand même, au seuil de 8 σ.
        for b in widths {
            let p = share[b]!, sd = (n * p * (1 - p)).squareRoot()
            if rate[b]! * n > n * p + 8 * max(sd, 1) { return b }
        }
        return nil
    }

    // MARK: Entrée

    /// Tente de résoudre le générateur à partir des tirages, du plus ancien au
    /// plus récent. Renvoie nil quand aucune famille ne colle.
    static func solve(_ drawsOldestFirst: [Draw], starts: Int = 24, confirm: Int = 20) -> RankSolution? {
        let ranks = drawsOldestFirst.compactMap { rank($0.numbers) }
        guard ranks.count >= confirm + 4 else { return nil }
        for floorMapping in [false, true] {
            for b in [64, 63, 62] {
                if let s = solveLCG(ranks, b: b, floorMapping: floorMapping,
                                    starts: starts, confirm: confirm) { return s }
            }
            if let s = solveInvertible(ranks, floorMapping: floorMapping,
                                       starts: starts, confirm: confirm) { return s }
            if let s = solveJava(ranks, floorMapping: floorMapping,
                                 starts: min(starts, 4), confirm: min(confirm, 12)) { return s }
        }
        return nil
    }
}

// Division 128 ÷ 64 sans dépendance externe, pour le mapping ⌊s·M/2^b⌋.
enum M128 {
    static func divide(hi: UInt64, lo: UInt64, by d: UInt64) -> (quotient: UInt64, remainder: UInt64) {
        guard hi != 0 else { return (lo / d, lo % d) }
        // hi < d est garanti par les appelants (hi vaut r >> (64−b) < M).
        let r = d.dividingFullWidth((high: hi, low: lo))
        return (r.quotient, r.remainder)
    }
}
