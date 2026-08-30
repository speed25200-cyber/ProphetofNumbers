import Foundation

// La loi de la cagnotte — cf. `lab/experiments/h15_loi_cagnotte.py`.
//
// h9 a établi le seul fait capable de changer le SIGNE de l'espérance : dès
// que la cagnotte dépasse mise/P(k/k), le pari devient favorable, quel que
// soit le barème des rangs intermédiaires. Il manquait la FRÉQUENCE de ce
// franchissement, et une observation isolée ne la donne pas.
//
// Le modèle, en trois hypothèses nommées :
//   H1  la cagnotte croît d'un montant fixe r par tirage ;
//   H2  elle est remportée avec une probabilité q par tirage, sans mémoire ;
//   H3  elle repart d'un plancher J₀ après un gain.
//
// Sous H1–H3, l'âge de la cagnotte à un instant quelconque est géométrique,
// donc P(J ≥ S) = exp(−(S − J₀)/μ) avec μ = r/q. Le calcul ci-dessous prend
// J₀ = 0, le cas le MOINS favorable au joueur : un plancher non nul ne peut
// que rendre le franchissement plus fréquent.
//
// Pourquoi mesurer r et q séparément plutôt qu'estimer μ directement : une
// exponentielle a un écart-type égal à sa moyenne, si bien qu'estimer μ sur
// la loi stationnaire demande une centaine de relevés pour situer la
// fraction favorable à un facteur 3 près. Alors que r est simplement la
// différence entre deux relevés successifs, et q le taux de chutes — deux
// quantités que l'app observe directement en tournant.
enum JackpotLaw {

    /// Ajoute les relevés du tirage courant, sans doublon.
    static func record(_ log: [JackpotReading], drawNumber: Int,
                       jackpots: [Jackpot], at: Date) -> [JackpotReading] {
        guard drawNumber > 0, !jackpots.isEmpty else { return log }
        var out = log
        for j in jackpots where j.francs > 0 {
            let already = out.contains { $0.drawNumber == drawNumber && $0.stake == j.stake }
            if already { continue }
            out.append(JackpotReading(drawNumber: drawNumber, stake: j.stake,
                                      francs: j.francs, at: at))
        }
        return out
    }

    /// Seuil de bascule.
    ///
    /// Sans prix de ticket, c'est la condition SUFFISANTE du §5 bis :
    /// `1 / P(k/k)`, qui suppose le ticket à un franc et jette les rangs
    /// intermédiaires. Avec un prix, c'est la condition NÉCESSAIRE ET
    /// SUFFISANTE que le barème relevé permet enfin d'écrire (§56) :
    /// `(c − E[base]) / P(k/k)`, soit environ 41 % de l'autre à c = 2.
    static func threshold(pAllHit: Double, ticketPrice: Double = 0,
                          stake: Int = 0) -> Double {
        guard pAllHit > 0 else { return .infinity }
        if ticketPrice > 0,
           let exact = PayTable.threshold(stake: stake, pAllHit: pAllHit,
                                          ticketPrice: ticketPrice) {
            return exact
        }
        return 1 / pAllHit
    }

    static func estimate(_ log: [JackpotReading], stake: Int,
                         pAllHit: Double,
                         ticketPrice: Double = 0) -> JackpotLawEstimate? {
        let rows = log.filter { $0.stake == stake }
            .sorted { $0.drawNumber < $1.drawNumber }
        guard let last = rows.last else { return nil }
        let seuil = threshold(pAllHit: pAllHit, ticketPrice: ticketPrice,
                              stake: stake)
        let span = rows.count >= 2 ? rows[rows.count - 1].drawNumber - rows[0].drawNumber : 0

        // Accroissements par tirage entre relevés successifs. Une CHUTE est
        // un gain : elle ne renseigne pas r, elle renseigne q.
        var rates: [Double] = []
        var drops = 0
        for i in 1..<max(rows.count, 1) {
            let step = rows[i].drawNumber - rows[i - 1].drawNumber
            guard step > 0 else { continue }
            let delta = rows[i].francs - rows[i - 1].francs
            if delta < 0 {
                drops += 1
            } else {
                rates.append(delta / Double(step))
            }
        }
        // Médiane plutôt que moyenne : une seule lecture erronée d'écran
        // suffirait à emporter une moyenne, pas une médiane.
        let accrual = median(rates.filter { $0 > 0 })

        var fav: Double?
        var favLo: Double?
        var favHi: Double?
        if let r = accrual, r > 0, span > 0, seuil.isFinite {
            // Intervalle de Poisson exact sur le nombre de chutes, transporté
            // en intervalle sur q puis sur μ = r/q. p = exp(−S/μ) est
            // croissante en μ, donc les bornes ne se croisent pas.
            let (loRate, hiRate) = poissonRateInterval(count: drops,
                                                       exposure: Double(span))
            let qHat = Double(drops) / Double(span)
            if qHat > 0 {
                fav = exp(-seuil * qHat / r)
            }
            favLo = hiRate > 0 ? exp(-seuil * hiRate / r) : 0
            favHi = loRate > 0 ? exp(-seuil * loRate / r) : 1
        }

        // Gain conditionnel (h16). Par absence de mémoire, E[J | J ≥ S] =
        // S + μ. Le gain d'un ticket joué au-dessus du seuil vaut donc
        // E[base] + (S + μ)·p, et le seuil est précisément le point où
        // E[base] + S·p = c : le profit par franc misé se réduit à μ·p/c.
        // C'est le nombre qui décide s'il faut miser, et il ne demande ni r
        // ni q — seulement la moyenne des relevés.
        //
        // Sans prix de ticket, c = 1 et S = 1/p : la formule redonne μ/S,
        // qui était l'écriture du §32. Avec le prix, écrire μ/S surestimerait
        // le gain d'un facteur c/(c − E[base]) — soit ×2,4 à c = 2, parce
        // que le seuil exact est plus bas SANS que la mise le soit.
        //
        // L'intervalle vient de 2n·J̄/μ ~ khi-deux(2n), obtenu ici depuis la
        // même fonction de répartition de Poisson :
        // P(khi-deux(2n) ≤ x) = P(Poisson(x/2) ≥ n).
        var edge: Double?
        var edgeLo: Double?
        var edgeHi: Double?
        if seuil.isFinite, pAllHit > 0 {
            let n = rows.count
            let unit = ticketPrice > 0 ? ticketPrice : 1
            let mean = rows.reduce(0) { $0 + $1.francs } / Double(n)
            edge = mean * pAllHit / unit
            let hiChi = chiSquareQuantile(0.975, dfHalf: n)
            let loChi = chiSquareQuantile(0.025, dfHalf: n)
            if hiChi > 0 { edgeLo = 2 * Double(n) * mean * pAllHit / hiChi / unit }
            if loChi > 0 { edgeHi = 2 * Double(n) * mean * pAllHit / loChi / unit }
        }

        return JackpotLawEstimate(
            stake: stake, readings: rows.count, spanDraws: span,
            latest: last.francs, threshold: seuil, accrual: accrual,
            drops: drops, favourable: fav, favourableLo: favLo,
            favourableHi: favHi, conditionalEdge: edge, edgeLo: edgeLo,
            edgeHi: edgeHi)
    }

    /// Quantile de la loi du khi-deux à 2·dfHalf degrés de liberté.
    ///
    /// Aucune fonction gamma n'est disponible ici. L'identité
    /// P(khi-deux(2n) ≤ x) = P(Poisson(x/2) ≥ n) = 1 − F_Poisson(n−1, x/2)
    /// ramène le quantile à la même bissection que l'intervalle de Poisson.
    static func chiSquareQuantile(_ p: Double, dfHalf n: Int) -> Double {
        guard n >= 1, p > 0, p < 1 else { return 0 }
        return 2 * solve(target: 1 - p, k: n - 1)
    }

    // MARK: Outils

    static func median(_ xs: [Double]) -> Double? {
        guard !xs.isEmpty else { return nil }
        let s = xs.sorted()
        let n = s.count
        return n % 2 == 1 ? s[n / 2] : (s[n / 2 - 1] + s[n / 2]) / 2
    }

    /// P(X ≤ k) pour X ~ Poisson(λ), en sommant en échelle logarithmique.
    static func poissonCDF(_ k: Int, _ lambda: Double) -> Double {
        if k < 0 { return 0 }
        if lambda <= 0 { return 1 }
        var logTerm = -lambda
        var total = exp(logTerm)
        var i = 1
        while i <= k {
            logTerm += log(lambda) - log(Double(i))
            total += exp(logTerm)
            i += 1
        }
        return min(1, total)
    }

    /// Intervalle de confiance exact à 95 % sur le taux d'un comptage de
    /// Poisson (méthode de Garwood), obtenu par bissection sur la fonction
    /// de répartition — sans fonction gamma, donc sans dépendance.
    ///
    /// À zéro chute observée la borne basse est 0 et la borne haute vaut
    /// −ln(0,025)/exposition ≈ 3,69/exposition : c'est la règle de trois, et
    /// elle donne déjà une borne INFÉRIEURE utile sur la fraction favorable.
    static func poissonRateInterval(count: Int, exposure: Double,
                                    alpha: Double = 0.05) -> (Double, Double) {
        guard exposure > 0 else { return (0, .infinity) }
        let lo = count == 0 ? 0 : solve(target: 1 - alpha / 2, k: count - 1)
        let hi = solve(target: alpha / 2, k: count)
        return (lo / exposure, hi / exposure)
    }

    /// Plus petit λ tel que poissonCDF(k, λ) ≤ target. La fonction de
    /// répartition est DÉCROISSANTE en λ à k fixé, d'où la bissection.
    private static func solve(target: Double, k: Int) -> Double {
        var lo = 0.0
        var hi = Double(k) + 10
        while poissonCDF(k, hi) > target && hi < 1e9 { hi *= 2 }
        for _ in 0..<200 {
            let mid = (lo + hi) / 2
            if poissonCDF(k, mid) > target { lo = mid } else { hi = mid }
        }
        return (lo + hi) / 2
    }
}
