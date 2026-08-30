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
// ce qu'il vaut. Le théorème le dit : chaque palier de tirages ORDONNÉS
// CONSÉCUTIFS ferme une classe de générateurs de plus. Le compteur devient donc
// un instrument, avec une cible.
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

    struct Milestone {
        let draws: Int
        let family: String
    }

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
            Milestone(draws: need(19_937, r), family: "MT19937 — random de Python, mt_rand de PHP"),
        ]
    }()

    /// Ce qu'une suite de `run` tirages ordonnés consécutifs a déjà fermé, et
    /// ce qu'il reste à collecter pour le palier suivant.
    static func status(run: Int) -> (closed: Int, next: Milestone?, minutes: Int) {
        let done = ladder.filter { $0.draws <= run }.count
        let next = ladder.first { $0.draws > run }
        let missing = next.map { $0.draws - run } ?? 0
        return (done, next, missing * 5)
    }

    /// Le mur que la collecte ne franchira pas si le générateur se ré-amorce à
    /// chaque ouverture de session : une session dure 204 tirages (§65), or
    /// MT19937 en demande 250. `204 × 80 = 16 320` bits contre 19 937.
    static let sessionLength = 204
    static var mtReachableWithinOneSession: Bool {
        sessionLength * rejectionBitsPerDraw >= 19_937
    }
}
