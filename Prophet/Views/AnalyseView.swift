import Charts
import SwiftUI

struct AnalyseView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let oracle = store.oracle {
            VStack(spacing: 16) {
                BacktestCard(oracle: oracle)
                SwarmCard(oracle: oracle)
                FieldCard(oracle: oracle, last: store.payload?.last)
                HotColdCard(oracle: oracle)
                if !oracle.movers.isEmpty {
                    MoversCard(movers: oracle.movers)
                }
                Text("Le Loto Express tire 20 boules parmi 80 toutes les 5 minutes, via un générateur certifié. Aucun modèle — pas même un essaim de 24 têtes — ne peut battre un RNG équitable sur la durée. Prophet mesure honnêtement son propre écart au hasard, et le backtest ci-dessus en est la preuve en continu.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
                    .padding(.horizontal, 4)
            }
        } else {
            ProgressView().tint(Palette.gold)
        }
    }
}

struct BacktestCard: View {
    var oracle: OracleResult

    var body: some View {
        let pts = Array(oracle.backtest.suffix(60))
        let roll = Self.rollingMean(pts, window: 8)
        let top = max(11.0, (pts.max() ?? 0) + 1)

        Card(tint: Palette.gold) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "VÉRITÉ TERRAIN")
                    Text("Backtest de l’ensemble")
                        .font(Typeface.display(22))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                verdictChip
            }

            if pts.isEmpty {
                Text("Pas encore assez de tirages pour mesurer le modèle.")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.muted)
            } else {
                Chart {
                    RuleMark(y: .value("Hasard", oracle.uniformExpected))
                        .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                        .foregroundStyle(Palette.subtle)
                    ForEach(Array(pts.enumerated()), id: \.offset) { i, v in
                        PointMark(x: .value("Tirage", i), y: .value("Hits", v))
                            .foregroundStyle(Palette.muted.opacity(0.4))
                            .symbolSize(14)
                    }
                    ForEach(Array(roll.enumerated()), id: \.offset) { i, v in
                        LineMark(x: .value("Tirage", i), y: .value("Moyenne", v))
                            .foregroundStyle(Palette.gold)
                            .interpolationMethod(.catmullRom)
                            .lineStyle(StrokeStyle(lineWidth: 2.5, lineCap: .round))
                    }
                }
                .chartXAxis(.hidden)
                .chartYAxis { AxisMarks(values: [0.0, 5.0, 10.0]) }
                .chartYScale(domain: 0...top)
                .frame(height: 140)

                HStack(spacing: 8) {
                    StatPill(
                        label: "MOYENNE TOP-20",
                        value: String(format: "%.2f hits", oracle.backtestMean),
                        accent: Palette.goldSoft
                    )
                    StatPill(label: "HASARD", value: String(format: "%.2f hits", oracle.uniformExpected))
                    StatPill(
                        label: "ÉCART (Z)",
                        value: String(format: "%+.2f", oracle.backtestZ),
                        accent: abs(oracle.backtestZ) < 2 ? Palette.fg : Palette.gold
                    )
                }

                Text(verdictText)
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.muted)

                if oracle.swarm.bestHeadName != "—" {
                    Text("Meilleure tête a posteriori : \(oracle.swarm.bestHeadName) à \(String(format: "%.2f", oracle.swarm.bestHeadMean)) hits. Choisir le vainqueur après coup surestime toujours — l'essaim, lui, est jugé en marche avant.")
                        .font(.system(size: 11))
                        .foregroundStyle(Palette.subtle)
                }
            }
        }
    }

    private var verdictChip: some View {
        let (label, color) = verdictBadge
        return Text(label)
            .font(.system(size: 11, weight: .semibold))
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.13), in: Capsule())
    }

    private var verdictBadge: (String, Color) {
        if oracle.backtest.count < 20 { return ("Échantillon court", Palette.subtle) }
        if oracle.backtestZ >= 2 { return ("Sur-performance", Palette.gain) }
        if oracle.backtestZ <= -2 { return ("Sous-performance", Palette.live) }
        return ("Conforme au hasard", Palette.gold)
    }

    private var verdictText: String {
        if oracle.backtest.count < 20 {
            return "Chaque point = nombre de hits du top-20 du modèle sur un tirage réel, prédit avant le tirage. Encore trop peu de données pour conclure."
        }
        if oracle.backtestZ >= 2 {
            return "Le top-20 du modèle bat le hasard sur la fenêtre récente. Probablement transitoire : sur un RNG certifié, la moyenne régresse vers 5.00."
        }
        if oracle.backtestZ <= -2 {
            return "Le top-20 du modèle fait moins bien que le hasard sur la fenêtre récente — le miroir statistique d’une série chaude. Régression vers 5.00 attendue."
        }
        return "Chaque point = hits du top-20 du modèle sur un tirage réel, prédit avant le tirage. La moyenne colle à 5.00 : le générateur est équitable et le modèle le mesure honnêtement."
    }

    static func rollingMean(_ xs: [Double], window: Int) -> [Double] {
        guard !xs.isEmpty else { return [] }
        var out: [Double] = []
        out.reserveCapacity(xs.count)
        for i in 0..<xs.count {
            let start = max(0, i - window + 1)
            let slice = xs[start...i]
            out.append(slice.reduce(0, +) / Double(slice.count))
        }
        return out
    }
}

struct FieldCard: View {
    var oracle: OracleResult
    var last: Draw?

    var body: some View {
        let maxAbs = max(oracle.scores.map { abs($0) }.max() ?? 0.001, 0.001)

        Card {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "CHAMP 1–80")
                    Text("Intensité de l’ensemble")
                        .font(Typeface.display(22))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                Image(systemName: "waveform.path.ecg")
                    .foregroundStyle(Palette.subtle)
            }
            Text("Plus doré = mieux classé pour le prochain tirage. Plein = sorti au dernier tirage.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 10), spacing: 6) {
                ForEach(1...ProphetConst.poolSize, id: \.self) { n in
                    let score = oracle.scores[n - 1]
                    let t = (score + maxAbs) / (2 * maxAbs)
                    let hit = last?.numbers.contains(n) == true
                    Text("\(n)")
                        .font(Typeface.mono(9, weight: .medium))
                        .foregroundStyle(hit ? Palette.accentFg : Palette.fg)
                        .frame(height: 28)
                        .frame(maxWidth: .infinity)
                        .background(hit ? Palette.gold : Palette.gold.opacity(0.06 + t * 0.42))
                        .clipShape(Circle())
                }
            }
        }
    }
}

struct HotColdCard: View {
    var oracle: OracleResult

    var body: some View {
        let hot = oracle.freq16.enumerated()
            .sorted { $0.element > $1.element }
            .prefix(5)
        let cold = oracle.gaps.enumerated()
            .sorted { $0.element > $1.element }
            .prefix(5)

        Card {
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 10) {
                    Overline(text: "EN FORME · 16 TIRAGES", color: Palette.live.opacity(0.8))
                    ForEach(Array(hot), id: \.offset) { item in
                        HStack(spacing: 8) {
                            NumberBall(n: item.offset + 1, size: 28, tone: .hot)
                            Text("\(Int(item.element))× sorti")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                VStack(alignment: .leading, spacing: 10) {
                    Overline(text: "ABSENTS DEPUIS", color: Palette.cold.opacity(0.9))
                    ForEach(Array(cold), id: \.offset) { item in
                        HStack(spacing: 8) {
                            NumberBall(n: item.offset + 1, size: 28, tone: .cold)
                            Text("\(item.element) tirages")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            Text("Sur un tirage équitable, « chaud » et « dû » sont des illusions — affichés pour lecture, pas comme promesse.")
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)
        }
    }
}

struct SwarmCard: View {
    var oracle: OracleResult

    var body: some View {
        let swarm = oracle.swarm
        let topHeads = Array(oracle.methods.sorted { $0.weight > $1.weight }.prefix(6))
        let maxFam = max(0.0001, swarm.families.map(\.weight).max() ?? 1)

        Card(tint: Palette.violet) {
            VStack(alignment: .leading, spacing: 4) {
                Overline(text: "L'ESSAIM")
                Text("\(swarm.headCount) têtes en compétition")
                    .font(Typeface.display(22))
                    .foregroundStyle(Palette.fg)
            }
            Text("Hedge à part fixe : chaque tête est payée sur ses hits réels, en marche avant. Les familles paramétriques évoluent — la tête la plus faible mute vers la plus forte.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            HStack(spacing: 8) {
                StatPill(label: "TÊTES EFFECTIVES", value: String(format: "%.1f", swarm.effectiveHeads))
                StatPill(label: "GÉNÉRATION", value: "\(swarm.generation)")
                StatPill(label: "MEILLEURE TÊTE", value: swarm.bestHeadName, accent: Palette.goldSoft)
            }

            VStack(spacing: 8) {
                ForEach(swarm.families) { fam in
                    HStack(spacing: 8) {
                        Text(fam.name)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Palette.fg)
                            .frame(width: 74, alignment: .leading)
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Palette.elevated)
                                Capsule()
                                    .fill(Palette.goldGradient)
                                    .frame(width: max(3, geo.size.width * CGFloat(fam.weight / maxFam)))
                            }
                        }
                        .frame(height: 5)
                        Text("\(Int(round(fam.weight * 100)))% · \(fam.heads)t")
                            .font(Typeface.mono(11))
                            .foregroundStyle(Palette.muted)
                            .frame(width: 66, alignment: .trailing)
                    }
                }
            }

            Divider().overlay(Color.white.opacity(0.07))

            Overline(text: "TÊTES DE PROUE")
            VStack(spacing: 10) {
                ForEach(topHeads) { m in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 8) {
                            Text(m.name)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(Palette.fg)
                            Text(m.family)
                                .font(.system(size: 10, weight: .medium))
                                .foregroundStyle(Palette.subtle)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Palette.elevated, in: Capsule())
                            Spacer()
                            Text("\(String(format: "%.1f", m.weight * 100))% · \(String(format: "%.1f", m.overlap * 20))/20")
                                .font(Typeface.mono(11))
                                .foregroundStyle(Palette.muted)
                        }
                        Text(m.blurb)
                            .font(.system(size: 10))
                            .foregroundStyle(Palette.subtle)
                    }
                }
            }
        }
    }
}

struct MoversCard: View {
    var movers: [RankMove]

    var body: some View {
        Card {
            VStack(alignment: .leading, spacing: 4) {
                Overline(text: "MOUVEMENT")
                Text("Après le dernier tirage")
                    .font(Typeface.display(22))
                    .foregroundStyle(Palette.fg)
            }
            VStack(spacing: 0) {
                ForEach(Array(movers.prefix(8))) { m in
                    HStack {
                        NumberBall(n: m.number, size: 28, tone: m.delta > 0 ? .hot : .cold)
                        Text("rang \(m.rank)")
                            .font(.system(size: 13))
                            .foregroundStyle(Palette.muted)
                        Spacer()
                        Text(m.delta > 0 ? "+\(m.delta)" : "\(m.delta)")
                            .font(Typeface.mono(13, weight: .semibold))
                            .foregroundStyle(m.delta > 0 ? Palette.gain : m.delta < 0 ? Palette.live : Palette.muted)
                    }
                    .padding(.vertical, 7)
                }
            }
        }
    }
}
