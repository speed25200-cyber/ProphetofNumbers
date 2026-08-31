import Foundation

// Le budget de fuite modulaire — cf. `lab/experiments/h50_fuite_modulaire.py`
// (§68) et `h51_budget_de_fuite.py` (§69).
//
// LE THÉORÈME. 80 = 16 × 5, donc `n = (out mod 80) + 1` entraîne
// `out ≡ n − 1 (mod 16)` : les QUATRE bits de poids faible du mot de sortie du
// générateur sont publiés en clair par chaque numéro tiré. Ce n'est pas une
// approximation, c'est une égalité.
//
// COROLLAIRE. Pour un générateur linéaire sur F₂ — xorshift, LFSR, Tausworthe,
// et le tempérage de MT19937 — chaque bit de sortie est une forme linéaire des
// bits d'état. Chaque numéro donne donc quatre équations linéaires, et un
// tirage ORDONNÉ en donne quatre-vingts. L'état se retrouve par élimination de
// Gauss, quelle que soit la graine : on ne cherche plus la graine, on résout
// l'état, et la taille de l'espace cesse d'être une variable.
//
// CE QUE CETTE CARTE FAIT. L'app collectait déjà l'ordre de sortie sans savoir
// ce qu'il vaut. Le théorème le dit : chaque palier de tirages ORDONNÉS ferme
// une classe de générateurs de plus. Le compteur devient donc un instrument,
// avec une cible.
//
// LES TIRAGES N'ONT PAS À ÊTRE CONSÉCUTIFS (§72, théorème du trou) : avancer un
// générateur F₂-linéaire de k pas reste une application linéaire, donc un trou
// ne détruit aucune équation dès qu'on sait de combien de mots il a avancé
// l'état — ce qui est exact sous Fisher-Yates. Une première version de cette
// carte comptait la plus longue suite CONSÉCUTIVE et jetait donc trois des cinq
// tirages ordonnés du dossier.
//
// CE QU'ELLE NE DIT PAS. Le théorème suppose (a) l'échantillonnage par rejet
// modulo 80 — un Fisher-Yates ne fuit que 22 bits par tirage au lieu de 80,
// cf. `fisherYatesBitsPerDraw` — et (b) la linéarité sur F₂. Les générateurs à
// sortie brouillée non linéairement (PCG, xoshiro ** et ++, splitmix64) et tout
// CSPRNG restent hors d'atteinte quel que soit le nombre de tirages collectés.
enum LeakBudget {

    static let pool = 80
    static let drawn = 20

    /// Valuation 2-adique : le nombre de bits de poids faible qu'un modulo `n`
    /// publie exactement.
    static func v2(_ n: Int) -> Int {
        guard n > 0 else { return 0 }
        var x = n, k = 0
        while x % 2 == 0 { x /= 2; k += 1 }
        return k
    }

    /// Rejet modulo 80 : tous les numéros passent par le même modulo.
    /// `v2(80) = 4`, donc 4 × 20 = 80 bits par tirage.
    static var rejectionBitsPerDraw: Int { drawn * v2(pool) }

    /// Fisher-Yates : le pas `i` tire modulo `80 − i`. La plupart de ces
    /// modules sont IMPAIRS et ne publient rien ; le pas modulo 64 = 2⁶ en
    /// publie six à lui seul.
    static var fisherYatesBitsPerDraw: Int {
        (0..<drawn).reduce(0) { $0 + v2(pool - $1) }
    }

    /// Familles à sortie ADDITIVE (xorshift128+, xoroshiro128+) : seul le
    /// bit 0 d'une somme est exactement linéaire, d'où 20 bits par tirage.
    static let additiveBitsPerDraw = 20

    // MARK: Les trois échantillonneurs (§82)

    // Tout ce qui précède suppose `n = (out mod 80) + 1`. Ce n'est qu'un des
    // trois idiomes, et le §82 a mesuré que c'est **le moins fuyant**.
    //
    //   (A) modulo            `out % 80`            — C, PHP historique
    //   (B) troncature        `floor(u × 80)`       — JavaScript, Java, Python
    //   (C) bits de poids fort avec rejet           — Python randrange, Go, Rust
    //
    // Deux conséquences que le dossier avait écrites à l'envers :
    //
    // 1. Le §74 concluait qu'un vivier IMPAIR (79, 81) annulerait la fuite.
    //    Vrai contre (A) seulement : un vivier de 79 publie 0 bit sous (A),
    //    4,48 sous (B) et 7 sous (C). La valuation 2-adique ne gouverne que
    //    le modulo.
    // 2. Le §71 concluait que Fisher-Yates divise la fuite par 3,6. Vrai
    //    contre (A) seulement : sous (B) il fuit 89,7 bits par tirage contre
    //    22, soit **plus** que le rejet modulo lui-même, parce que la
    //    troncature ne demande pas que le module soit pair.

    /// Bits exactement publiés par mot sous **troncature** : `n − 1 =
    /// floor(out × pool / 2^w)` contraint `out` à un intervalle de largeur
    /// `2^w / pool`, donc tous les bits de poids fort communs aux deux bornes
    /// sont déterminés. Calculé, jamais tabulé — la valeur est stable dès
    /// `w = 32` (5,2 pour un vivier de 80).
    static func truncationBitsPerWord(pool: Int = pool, wordBits: Int = 32) -> Double {
        let scale = UInt64(1) << UInt64(wordBits)
        var total = 0.0
        for n in 0..<pool {
            let lo = (UInt64(n) * scale + UInt64(pool) - 1) / UInt64(pool)
            let hi = (UInt64(n + 1) * scale + UInt64(pool) - 1) / UInt64(pool) - 1
            var shared = 0
            while shared < wordBits {
                let sh = UInt64(wordBits - shared - 1)
                if (lo >> sh) != (hi >> sh) { break }
                shared += 1
            }
            total += Double(hi - lo + 1) / Double(scale) * Double(shared)
        }
        return total
    }

    /// Bits publiés par mot accepté sous **bits de poids fort avec rejet** :
    /// les `k = ceil(log2(pool))` bits tirés *sont* le numéro.
    static var highBitsPerWord: Int { Int.bitWidth - (pool - 1).leadingZeroBitCount }

    /// Les trois, par tirage de 20 numéros. Le modulo est le plus avare.
    static var bitsPerDrawBySampler: (modulo: Double, truncation: Double, highBits: Double) {
        (Double(rejectionBitsPerDraw),
         Double(drawn) * truncationBitsPerWord(),
         Double(drawn * highBitsPerWord))
    }

    // MARK: Le mur, en une ligne (§83, §84)

    // Le §83 a réduit ce que le dossier ne sait pas atteindre à une seule
    // combinaison : **sortie ADDITIVE + échantillonneur par TRONCATURE**,
    // c'est-à-dire `Math.random` de V8 (xorshift128+) avec le JavaScript
    // idiomatique `Math.floor(Math.random() * 80)`.
    //
    // Le théorème de la retenue du §83 rend 1,875 équation linéaire par mot au
    // lieu d'une chez les additifs — mais il part de la retenue nulle, donc des
    // bits de POIDS FAIBLE, quand la troncature publie les bits de POIDS FORT.
    //
    // Le §84 mesure la distance au lieu de la déclarer : un solveur SMT
    // retrouve l'état de xorshift128+ à 16 bits publiés par mot et cale à 12, à
    // redondance fixée — et ajouter des tirages n'y change rien, ce qui bloque
    // étant la LARGEUR de chaque contrainte, pas leur nombre. Le vivier de 80
    // n'en publie que 5,2.
    /// Bits par mot qu'un solveur SMT exige pour retrouver un état additif de
    /// 128 bits (§84, mesuré). Le vivier réel en publie `truncationBitsPerWord()`.
    static let smtSolvableFromBitsPerWord = 16

    /// Ce qui manque pour que le mur tombe, en facteur sur la fuite par mot.
    static var wallFactor: Double {
        Double(smtSolvableFromBitsPerWord) / truncationBitsPerWord()
    }

    struct Milestone {
        let draws: Int
        let family: String
    }

    /// MT19937 ne se compte PAS comme les autres, et le §69 s'était trompé en
    /// le faisant. Ses 80 équations par tirage cessent d'être indépendantes au
    /// mot 2 493 — exactement quatre blocs de 624, quand les brassages
    /// commencent à se recouvrir. Le rang plein demande donc 6 853 mots et non
    /// 19 937/4, soit **343 tirages ordonnés au mieux** au lieu des 250 que
    /// l'ancienne échelle annonçait : +37 %.
    ///
    /// Mesuré au §80 (`h60_appartenance.py`), par élimination exacte sur les
    /// 19 937 inconnues. Les autres paliers ne sont pas touchés : leurs états
    /// sont assez petits pour être résolus avant le quatrième bloc.
    ///
    /// « Au mieux » parce que le calcul suppose les quatre bits de CHAQUE mot
    /// consécutif connus. Sous rejet un tirage consomme ~22,85 mots dont 20
    /// seulement sont identifiés (§74) ; sous Fisher-Yates la fuite tombe à 22
    /// bits (§71). C'est une borne inférieure, jamais une promesse.
    static let mtWordsForFullRank = 6_853
    static let mtDrawsForFullRank = 343

    /// L'échelle, dans l'ordre. Chaque palier est `ceil(bits d'état / bits par
    /// tirage)` — calculé, jamais tabulé à la main.
    static let ladder: [Milestone] = {
        let r = rejectionBitsPerDraw
        let a = additiveBitsPerDraw
        func need(_ bits: Int, _ per: Int) -> Int { (bits + per - 1) / per }
        return [
            Milestone(draws: need(64, r), family: "xorshift32 et xorshift64"),
            Milestone(draws: need(128, r), family: "xorshift96, xorshift128, taus88"),
            Milestone(draws: need(256, r), family: "xoshiro256, si sa sortie n'est pas brouillée"),
            Milestone(draws: need(128, a), family: "les familles additives (xorshift128+, xoroshiro128+)"),
            Milestone(draws: need(256, a), family: "toute famille additive jusqu'à 256 bits"),
            Milestone(draws: mtDrawsForFullRank, family: "MT19937 — random de Python, mt_rand de PHP"),
        ]
    }()

    /// Ce qu'un jeu de `n` tirages ordonnés a déjà fermé, et ce qu'il reste à
    /// collecter pour le palier suivant.
    ///
    /// `n` est un NOMBRE, pas une suite consécutive — c'est le théorème du
    /// trou (§72) : avancer un générateur F₂-linéaire de k pas reste linéaire,
    /// donc deux tirages séparés se chaînent comme deux voisins dès qu'on sait
    /// de combien de mots le trou a avancé l'état. Sous Fisher-Yates c'est
    /// exact (20 mots par tirage), donc gratuit.
    ///
    /// Une première version de cette carte passait `longestConsecutiveRun` et
    /// affichait donc une cible inutilement pessimiste : elle jetait trois des
    /// cinq tirages ordonnés du dossier. C'est le §72 qui l'a corrigée.
    static func status(count n: Int) -> (closed: Int, next: Milestone?, minutes: Int) {
        let done = ladder.filter { $0.draws <= n }.count
        let next = ladder.first { $0.draws > n }
        let missing = next.map { $0.draws - n } ?? 0
        return (done, next, missing * 5)
    }

    // MARK: Les deux lectures du budget

    /// Longueur d'une session, et premier début de session complet observé —
    /// mesurés sur l'archive au §65 : 345 sessions de 204 tirages exactement,
    /// chacune ouvrant à 04:05:00 UTC.
    static let sessionAnchor = 1_309_794

    /// Index de session d'un tirage. Les numéros de tirage sont consécutifs à
    /// travers les coupures, donc la session ne se lit QUE par ce découpage.
    static func session(of drawNumber: Int) -> Int {
        (drawNumber - sessionAnchor) / sessionLength
    }

    /// Le budget a deux lectures, et le dossier ne sait pas trancher entre
    /// elles (§65 : le générateur se ré-amorce-t-il à l'ouverture ?).
    ///
    /// - `continuous` : si le générateur traverse les coupures, TOUS les
    ///   tirages ordonnés se chaînent — c'est leur nombre total.
    /// - `perSession` : s'il se ré-amorce chaque matin, seuls ceux d'une même
    ///   session se chaînent — c'est le maximum par session.
    ///
    /// Les afficher tous les deux est la seule lecture honnête tant que la
    /// question du §65 n'est pas tranchée.
    static func budgets(drawNumbers: [Int]) -> (continuous: Int, perSession: Int) {
        guard !drawNumbers.isEmpty else { return (0, 0) }
        var perSession: [Int: Int] = [:]
        for n in drawNumbers { perSession[session(of: n), default: 0] += 1 }
        return (drawNumbers.count, perSession.values.max() ?? 0)
    }

    /// Le mur que la collecte ne franchira pas si le générateur se ré-amorce à
    /// chaque ouverture de session : une session dure 204 tirages (§65), or
    /// MT19937 en demande 343 (§80) — et non 250, comme le §69 le comptait.
    ///
    /// Le §78 avait laissé espérer un raccourci : prédire trois formes
    /// linéaires n'exige pas le rang plein, seulement leur appartenance à
    /// l'espace engendré. Le §80 a mesuré ce raccourci sur MT19937 — il est
    /// RÉEL (un bit devient prédictible 2 490 mots avant le rang plein, deux
    /// bits 621 mots avant) mais INSUFFISANT : il en faudrait trois, et trois
    /// n'arrivent jamais avant le rang plein. Le raccourci ne rattrape donc
    /// pas la session.
    static let sessionLength = 204
    static var mtReachableWithinOneSession: Bool {
        sessionLength >= mtDrawsForFullRank
    }
}
