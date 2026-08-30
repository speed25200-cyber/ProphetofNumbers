import Foundation

// Le barème de Loto Express, relevé — et ce qu'il permet enfin de calculer.
//
// Le §5 bis du dossier n'avait pas le barème et s'en passait par une
// condition SUFFISANTE : tous les rangs intermédiaires étant positifs ou
// nuls, `jackpot·P(k/k) ≥ mise` suffit à rendre le pari favorable. C'est ce
// que la carte du jackpot affiche depuis, sous la forme d'un seuil à
// 100 ct/CHF.
//
// Le barème a depuis été relevé sur les cinq mises (lab/bareme_observed.csv,
// §56 du rapport). Il donne trois choses que la condition suffisante jetait :
//
//   1. l'espérance de gain de BASE, hors cagnotte, égalisée par l'opérateur
//      à 2,6 % près entre les cinq mises — ce qui est à la fois le contrôle
//      de transcription et la mesure du théorème de collapse du §50 ;
//   2. le gain FIXE du rang plein, que le seuil suffisant ignorait ;
//   3. une borne INFÉRIEURE sur le prix du ticket : le taux de retour vaut
//      E/c et ne peut pas dépasser 1, donc c > CHF 1,20. Le ticket à un
//      franc que l'app supposait est arithmétiquement exclu.
//
// D'où le seuil exact, nécessaire ET suffisant :
//
//      J* = (c − E[base]) / P(k/k)
//
// soit environ 41 % du seuil suffisant à c = 2. La carte l'emploie dès que
// le prix du ticket est renseigné, et retombe sur l'ancienne règle sinon.
//
// AVERTISSEMENT, et c'est la raison d'être de `legacyRuleValidUpTo` : la
// règle des 100 ct/CHF suppose le ticket à un franc. Elle reste une
// condition suffisante valide tant que c ≤ 1 + E[base], soit CHF 2,17 avec
// le barème relevé — au-delà elle annoncerait « favorable » à tort. Ce
// n'était pas visible avant d'avoir le barème.
enum PayTable {

    static let pool = 80
    static let drawn = 20

    /// Gain fixe en CHF par nombre de numéros trouvés, pour une grille de k.
    /// Relevé sur jeux.loro.ch le 30 août 2026 à 22:16, BOOST ×1.
    /// La colonne EXTRA n'est pas portée ici : son prix et sa portée ne sont
    /// pas établis (§56, limite 3), et l'inclure fausserait E[base].
    static let base: [Int: [Int: Double]] = [
        5: [5: 360, 4: 36, 3: 6, 2: 0, 1: 0, 0: 0],
        6: [6: 1000, 5: 60, 4: 12, 3: 4, 2: 0, 1: 0, 0: 0],
        7: [7: 2000, 6: 200, 5: 25, 4: 5, 3: 3, 2: 0, 1: 0, 0: 0],
        8: [8: 10000, 7: 1000, 6: 80, 5: 20, 4: 5, 3: 0, 2: 0, 1: 0, 0: 0],
        10: [10: 100000, 9: 5000, 8: 500, 7: 100, 6: 10, 5: 5, 4: 3, 3: 0, 2: 0, 1: 0, 0: 2],
    ]

    /// Prix du ticket compatibles avec le barème. CHF 1 est EXCLU par le
    /// calcul ci-dessus, pas par choix : à ce prix l'opérateur perdrait de
    /// l'argent sur chaque mise avant même de servir la cagnotte.
    static let admissiblePrices: [Double] = [1.5, 2, 2.5, 3]

    // MARK: Loi hypergéométrique

    /// log(n!) par sommation directe. n ≤ 80 ici : pas de fonction gamma,
    /// donc pas de dépendance de plateforme sur `lgamma`.
    private static func logFactorial(_ n: Int) -> Double {
        guard n > 1 else { return 0 }
        var s = 0.0
        for i in 2...n { s += log(Double(i)) }
        return s
    }

    private static func logChoose(_ n: Int, _ k: Int) -> Double {
        guard k >= 0, k <= n, n >= 0 else { return -.infinity }
        return logFactorial(n) - logFactorial(k) - logFactorial(n - k)
    }

    /// P(exactement h numéros trouvés) sur une grille de k.
    static func probability(stake k: Int, hits h: Int) -> Double {
        let l = logChoose(k, h) + logChoose(pool - k, drawn - h) - logChoose(pool, drawn)
        return l.isFinite ? exp(l) : 0
    }

    // MARK: Ce que le barème donne

    /// Espérance du gain de base, hors cagnotte, en CHF par ticket.
    /// nil si la mise n'est pas au barème relevé.
    static func baseExpectation(stake k: Int) -> Double? {
        guard let table = base[k] else { return nil }
        return table.reduce(0) { $0 + $1.value * probability(stake: k, hits: $1.key) }
    }

    /// Seuil de bascule EXACT : la cagnotte à partir de laquelle
    /// `E[base] + J·P(k/k) ≥ c`. Zéro si le barème rembourse déjà la mise.
    /// nil si la mise est inconnue ou le prix non renseigné.
    static func threshold(stake k: Int, pAllHit: Double, ticketPrice c: Double) -> Double? {
        guard c > 0, pAllHit > 0, let e = baseExpectation(stake: k) else { return nil }
        return max(0, (c - e) / pAllHit)
    }

    /// Taux de retour de base — la part de la mise que le barème rend avant
    /// toute cagnotte. À c = 2 il vaut 58,9 %, égalisé entre les mises.
    static func baseReturn(stake k: Int, ticketPrice c: Double) -> Double? {
        guard c > 0, let e = baseExpectation(stake: k) else { return nil }
        return e / c
    }

    /// Prix maximal du ticket au-delà duquel la règle des 100 ct/CHF cesse
    /// d'être une condition suffisante : `1/p ≥ (c − E)/p` ⟺ `c ≤ 1 + E`.
    /// La mise la plus contraignante décide.
    static var legacyRuleValidUpTo: Double {
        let mins = base.keys.compactMap { baseExpectation(stake: $0) }
        return 1 + (mins.min() ?? 0)
    }

    /// Prix minimal compatible : le taux de retour ne peut pas dépasser 1,
    /// donc c > max_k E[base]. Vaut CHF 1,1971 avec le barème relevé.
    static var priceLowerBound: Double {
        base.keys.compactMap { baseExpectation(stake: $0) }.max() ?? 0
    }
}
