import Charts
import SwiftUI

struct AnalyseView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let oracle = store.oracle {
            analyseBody(oracle: oracle)
                .task(id: store.payload?.last?.drawNumber ?? 0) {
                    await store.loadForensics()
                }
        } else {
            ProgressView().tint(Palette.gold)
        }
    }

    @ViewBuilder
    private func analyseBody(oracle: OracleResult) -> some View {
            VStack(spacing: 16) {
                BacktestCard(oracle: oracle)
                SwarmCard(oracle: oracle)
                if let report = store.forensics {
                    ForensicsCard(report: report)
                }
                RecoveryCard()
                FieldCard(oracle: oracle, last: store.payload?.last)
                GeoCard(oracle: oracle)
                HotColdCard(oracle: oracle)
                if !oracle.movers.isEmpty {
                    MoversCard(movers: oracle.movers)
                }
                Text("Le Loto Express tire 20 boules parmi 80 toutes les 5 minutes, via un générateur certifié. Aucun modèle — pas même un essaim de 26 têtes — ne peut battre un RNG équitable sur la durée. Prophet mesure honnêtement son propre écart au hasard, et le backtest ci-dessus en est la preuve en continu.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
                    .padding(.horizontal, 4)
        }
    }
}

// Forensique du générateur : sept tests qui caractérisent la source à
// partir des seuls tirages publiés.
struct ForensicsCard: View {
    var report: ForensicsReport

    var body: some View {
        Card(tint: report.flagged > 0 ? Palette.live : Palette.teal) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "FORENSIQUE DU GÉNÉRATEUR")
                    Text(report.verdict)
                        .font(Typeface.display(22))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                Image(systemName: report.flagged > 0 ? "exclamationmark.triangle.fill" : "checkmark.shield.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(report.flagged > 0 ? Palette.live : Palette.gain)
            }
            Text("Sept tests qui identifient la source — pas pour prédire un tirage, pour savoir à quel type de générateur on a affaire. \(report.sampleSize) tirages analysés.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            VStack(spacing: 10) {
                ForEach(report.tests) { t in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 6) {
                            Image(systemName: t.flagged ? "xmark.octagon.fill" : "checkmark.circle")
                                .font(.system(size: 10))
                                .foregroundStyle(t.flagged ? Palette.live : Palette.gain.opacity(0.85))
                            Text(t.name)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundStyle(Palette.fg)
                            Spacer()
                            Text(t.statistic)
                                .font(Typeface.mono(11))
                                .foregroundStyle(Palette.muted)
                                .lineLimit(1)
                                .minimumScaleFactor(0.65)
                        }
                        HStack(spacing: 6) {
                            Text(t.catches)
                                .font(.system(size: 10))
                                .foregroundStyle(Palette.subtle)
                            Spacer()
                            Text(String(format: "%.1f σ", t.sigma))
                                .font(Typeface.mono(10))
                                .foregroundStyle(t.flagged ? Palette.live : Palette.subtle)
                        }
                    }
                }
            }

            Text(report.detail)
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)
        }
    }
}

// Reconstruction d'état : l'attaque qui a fonctionné historiquement,
// lancée à la demande sur les tirages publiés.
struct RecoveryCard: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        Card(tint: store.recovery?.solved == true ? Palette.live : Palette.violet) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "RECONSTRUCTION D’ÉTAT")
                    Text(store.recovery?.verdict ?? "Attaque par recherche de graine")
                        .font(Typeface.display(22))
                        .foregroundStyle(Palette.fg)
                }
                Spacer()
                if store.recoveryRunning {
                    ProgressView().tint(Palette.gold)
                } else {
                    Image(systemName: store.recovery?.solved == true ? "key.fill" : "lock.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(store.recovery?.solved == true ? Palette.live : Palette.muted)
                }
            }

            Text("Cherche l’état interne du générateur : 8 familles (LCG glibc et MSVC, java.util.Random, xorshift32 et 128+, splitmix64, PCG32, Mersenne Twister) × 3 façons de tirer 20 numéros sur 80 × amorçages horloge, n° de tirage et graines courtes. Un état ne compte que s’il reproduit un tirage entier **et** confirme le suivant.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            if let r = store.recovery {
                HStack(spacing: 8) {
                    StatPill(label: "CANDIDATS", value: Format.ch.string(from: NSNumber(value: r.candidatesTested)) ?? "\(r.candidatesTested)")
                    StatPill(
                        label: "MEILLEUR",
                        value: "\(r.bestPrefix)/20",
                        accent: r.solved ? Palette.live : Palette.fg
                    )
                    StatPill(label: "HASARD", value: String(format: "%.1f/20", r.expectedPrefix))
                    StatPill(label: "DURÉE", value: String(format: "%.1f s", r.elapsed))
                }
                Text(r.detail)
                    .font(.system(size: 11))
                    .foregroundStyle(r.solved ? Palette.live : Palette.subtle)
                if !r.solved {
                    Text("Meilleur candidat : \(r.bestFamily) · \(r.bestSampler) · \(r.bestSeedLabel) — au niveau du bruit.")
                        .font(.system(size: 10))
                        .foregroundStyle(Palette.subtle)
                }
            }

            Button {
                Task { await store.runRecovery() }
            } label: {
                Text(store.recoveryRunning ? "Balayage en cours…" : (store.recovery == nil ? "Lancer l’attaque" : "Relancer sur le dernier tirage"))
            }
            .buttonStyle(ProphetButtonStyle())
            .disabled(store.recoveryRunning)
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
                    StatPill(
                        label: "E-VALEUR",
                        value: oracle.eValue < 100
                            ? String(format: "%.2f", oracle.eValue)
                            : String(format: "%.0f", oracle.eValue),
                        accent: oracle.eValue >= 20 ? Palette.live : Palette.fg
                    )
                }

                Text("E-valeur : test séquentiel par pari, valide à tout instant. Une richesse ≥ 20 signalerait un générateur biaisé (α = 5 %) — sous ce seuil, aucune anomalie.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)

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

    // Ordre du tableau officiel Loro : colonnes = dizaines, rangées =
    // chiffre des unités (rendu rangée par rangée, 8 cases par ligne).
    private static let boardOrder: [Int] = {
        var out: [Int] = []
        for row in 0..<10 {
            for col in 0..<8 { out.append(col * 10 + row + 1) }
        }
        return out
    }()

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
            Text("Disposition officielle du tableau Loro (colonnes = dizaines). Plus doré = mieux classé. Plein = sorti au dernier tirage.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 8), spacing: 6) {
                ForEach(Self.boardOrder, id: \.self) { n in
                    let score = oracle.scores[n - 1]
                    let t = (score + maxAbs) / (2 * maxAbs)
                    let hit = last?.numbers.contains(n) == true
                    Text("\(n)")
                        .font(Typeface.mono(10, weight: .medium))
                        .foregroundStyle(hit ? Palette.accentFg : Palette.fg)
                        .frame(height: 30)
                        .frame(maxWidth: .infinity)
                        .background(hit ? Palette.gold : Palette.gold.opacity(0.06 + t * 0.42))
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
    }
}

struct GeoCard: View {
    var oracle: OracleResult

    var body: some View {
        let geoWeight = oracle.swarm.families.first { $0.name == "Géo" }?.weight ?? 0

        Card {
            VStack(alignment: .leading, spacing: 4) {
                Overline(text: "GÉOMÉTRIE DU TABLEAU")
                Text("Paires adjacentes sur la grille")
                    .font(Typeface.display(22))
                    .foregroundStyle(Palette.fg)
            }
            Text("Les grappes que l’œil voit à l’écran sont mesurées : nombre de cases voisines (colonne/rangée) sorties ensemble, comparé au hasard exact.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            HStack(spacing: 8) {
                StatPill(
                    label: "OBSERVÉ",
                    value: String(format: "%.2f paires", oracle.adjacencyMean),
                    accent: Palette.goldSoft
                )
                StatPill(label: "HASARD", value: String(format: "%.2f paires", oracle.adjacencyExpected))
                StatPill(
                    label: "ÉCART (Z)",
                    value: String(format: "%+.2f", oracle.adjacencyZ),
                    accent: abs(oracle.adjacencyZ) < 2 ? Palette.fg : Palette.gold
                )
            }

            Text(verdict)
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)
            Text("Deux têtes « Géo » (voisinage, rangées) concourent dans l’essaim — poids actuel \(String(format: "%.1f", geoWeight * 100)) %. Si la géométrie payait, le Hedge les ferait monter tout seul.")
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)

            HStack(spacing: 5) {
                Image(systemName: oracle.duplicateAlert ? "exclamationmark.triangle.fill" : "checkmark.shield")
                    .font(.system(size: 10))
                    .foregroundStyle(oracle.duplicateAlert ? Palette.live : Palette.gain)
                Text(oracle.duplicateAlert
                    ? "Recouvrement anormal entre deux tirages (\(oracle.duplicateMax)/20) — signature d’un rejeu de séquence (bug type Corriveau 1994)."
                    : "Anti-rejeu : recouvrement max entre deux tirages \(oracle.duplicateMax)/20 — aucun rejeu de séquence suspect.")
                    .font(.system(size: 11))
                    .foregroundStyle(oracle.duplicateAlert ? Palette.live : Palette.subtle)
            }
        }
    }

    private var verdict: String {
        if abs(oracle.adjacencyZ) < 2 {
            return "Les grappes sont exactement au niveau du hasard : la paréidolie est mesurée, pas subie. La disposition du tableau étant fixe, la géométrie n’ajoute aucune information aux numéros."
        }
        return oracle.adjacencyZ > 0
            ? "Sur-représentation récente des paires voisines — à surveiller via l’e-valeur avant d’y croire : régression vers le hasard attendue."
            : "Sous-représentation récente des paires voisines — le miroir d’une série de grappes. Régression vers le hasard attendue."
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
