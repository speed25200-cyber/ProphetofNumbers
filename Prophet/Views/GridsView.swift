import SwiftUI
import UIKit

struct GridsView: View {
    @EnvironmentObject var store: ProphetStore
    @Namespace private var stakeNS

    var body: some View {
        if let oracle = store.oracle,
           let pack = oracle.stakes.first(where: { $0.stake == store.stake }) {
            VStack(alignment: .leading, spacing: 16) {
                Overline(text: "MISE")
                stakePicker
                let caption: String = {
                    if let target = store.payload?.nextDrawNumber {
                        if let at = store.payload?.nextDrawAt {
                            return "Pour le #\(target) · \(Zurich.parts(at).time) · cote de base \(pack.oddsLabel)"
                        }
                        return "Pour le #\(target) · cote de base \(pack.oddsLabel)"
                    }
                    return "Cote de base \(pack.oddsLabel) · modèle recalibré après chaque tirage"
                }()
                Text(caption)
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.subtle)
                if let pending = store.payload?.pendingDrawNumber, store.payload?.hole == true {
                    Text("Résultat #\(pending) pas encore publié — grilles déjà calées pour le tour suivant.")
                        .font(.system(size: 12))
                        .foregroundStyle(Palette.gold)
                }
                jackpotCard(oracle: oracle)
                lastReadCard
                ledgerCard
                // 1 colonne sur iPhone, 2 sur iPad.
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 320), spacing: 16)], spacing: 16) {
                    ForEach(pack.grids) { grid in
                        GridCard(grid: grid, targetDraw: store.payload?.nextDrawNumber)
                    }
                }
            }
            .sensoryFeedback(.impact(weight: .light), trigger: store.stake)
        } else {
            ProgressView().tint(Palette.gold)
        }
    }

    private var stakePicker: some View {
        HStack(spacing: 0) {
            ForEach(ProphetConst.stakes, id: \.self) { s in
                Button {
                    withAnimation(.snappy(duration: 0.28)) { store.stake = s }
                } label: {
                    Text("\(s)")
                        .font(Typeface.mono(15, weight: .semibold))
                        .foregroundStyle(store.stake == s ? Palette.accentFg : Palette.muted)
                        .frame(maxWidth: .infinity)
                        .frame(height: 42)
                        .contentShape(Rectangle())
                        .background {
                            if store.stake == s {
                                Capsule()
                                    .fill(Palette.goldGradient)
                                    .matchedGeometryEffect(id: "stakepill", in: stakeNS)
                            }
                        }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(5)
        .background(Palette.surface, in: Capsule())
        .overlay(Capsule().strokeBorder(Color.white.opacity(0.08), lineWidth: 1))
    }

    // La comparaison au tirage sorti se fait ici — sur les grilles qui le
    // visaient — jamais sur les grilles fraîches, qui visent le prochain.
    @ViewBuilder
    private var lastReadCard: some View {
        if let last = store.payload?.last {
            let scored = store.tickets.filter { $0.targetDraw == last.drawNumber && $0.stake == store.stake }
            if !scored.isEmpty {
                Card {
                    Overline(text: "LECTURE DU #\(last.drawNumber)")
                    VStack(spacing: 8) {
                        ForEach(scored) { t in
                            HStack(spacing: 6) {
                                Circle()
                                    .fill(Palette.kindColor(t.kind))
                                    .frame(width: 6, height: 6)
                                Text(t.kind.label + (t.variant == 2 ? " II" : ""))
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundStyle(Palette.fg)
                                Spacer()
                                Text("\(Hits.inDraw(t.numbers, last))/\(store.stake) hits")
                                    .font(Typeface.mono(13, weight: .medium))
                                    .foregroundStyle(Palette.fg)
                            }
                        }
                    }
                    Text("Grilles qui visaient ce tirage, jugées après coup.")
                        .font(.system(size: 11))
                        .foregroundStyle(Palette.subtle)
                }
            }
        }
    }

    // Retour espéré du seul jackpot, par franc misé, à la cote de base.
    // Le seul levier de décision réel : plus le jackpot monte, moins la
    // mise correspondante est défavorable.
    @ViewBuilder
    private func jackpotCard(oracle: OracleResult) -> some View {
        let jacks = store.payload?.jackpots ?? []
        let rows: [(stake: Int, francs: Double, ret: Double)] = jacks.compactMap { j in
            guard let pack = oracle.stakes.first(where: { $0.stake == j.stake }),
                  let p = pack.grids.first?.basePAllHit else { return nil }
            let francs = j.amount >= 10_000 ? j.amount / 100 : j.amount
            return (j.stake, francs, francs * p * 100)
        }
        if !rows.isEmpty {
            let bestStake = rows.max { $0.ret < $1.ret }?.stake
            Card {
                Overline(text: "VALEUR DU JACKPOT")
                VStack(spacing: 8) {
                    ForEach(rows, id: \.stake) { row in
                        HStack(spacing: 8) {
                            Text("\(row.stake)/\(row.stake)")
                                .font(Typeface.mono(13, weight: .semibold))
                                .foregroundStyle(row.stake == bestStake ? Palette.goldSoft : Palette.fg)
                                .frame(width: 52, alignment: .leading)
                            Text("CHF \(Format.ch.string(from: NSNumber(value: row.francs.rounded())) ?? "—")")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                            Spacer()
                            if row.stake == bestStake {
                                Image(systemName: "star.fill")
                                    .font(.system(size: 9))
                                    .foregroundStyle(Palette.gold)
                            }
                            Text(String(format: "%.2f ct/CHF", row.ret))
                                .font(Typeface.mono(12, weight: .semibold))
                                .foregroundStyle(row.stake == bestStake ? Palette.goldSoft : Palette.fg)
                        }
                    }
                }
                Text("Retour espéré du seul jackpot par franc misé (hors rangs intermédiaires). L'étoile marque la mise au jackpot le plus « rentable » du moment — l'espérance totale reste négative.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
            }
        }
    }

    @ViewBuilder
    private var ledgerCard: some View {
        let perf = store.performance(stake: store.stake)
        if !perf.isEmpty {
            Card {
                Overline(text: "BILAN RÉEL DES GRILLES")
                VStack(spacing: 10) {
                    ForEach(perf) { row in
                        HStack(spacing: 6) {
                            Circle()
                                .fill(Palette.kindColor(row.kind))
                                .frame(width: 6, height: 6)
                            Text(row.kind.label)
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(Palette.fg)
                            Text("· \(row.plays) tirages")
                                .font(.system(size: 12))
                                .foregroundStyle(Palette.subtle)
                            Spacer()
                            Text("\(row.hits) hits")
                                .font(Typeface.mono(13, weight: .medium))
                                .foregroundStyle(Palette.fg)
                            deltaChip(Double(row.hits) - row.expected)
                        }
                    }
                }
                Text("Attendu au hasard : \(String(format: "%.2f", ProphetConst.baseP * Double(store.stake))) hit par grille. Chaque grille proposée est mémorisée puis confrontée au tirage réel — comptage honnête, sans tri.")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
            }
        }
    }

    private func deltaChip(_ delta: Double) -> some View {
        let positive = delta >= 0
        return Text(String(format: "%@%.1f", positive ? "+" : "", delta))
            .font(Typeface.mono(11, weight: .semibold))
            .foregroundStyle(positive ? Palette.gain : Palette.live)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background((positive ? Palette.gain : Palette.live).opacity(0.13), in: Capsule())
    }
}

struct GridCard: View {
    var grid: SuggestedGrid
    var targetDraw: Int?
    @State private var copied = false

    private var kindColor: Color { Palette.kindColor(grid.kind) }

    private var icon: String {
        switch grid.kind {
        case .alpha: return "flame.fill"
        case .omega: return "arrow.uturn.backward"
        case .nexus: return "sparkles"
        }
    }

    var body: some View {
        Card(tint: kindColor) {
            HStack(alignment: .center, spacing: 12) {
                ZStack {
                    Circle().fill(kindColor.opacity(0.15))
                    Image(systemName: icon)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(kindColor)
                }
                .frame(width: 38, height: 38)
                VStack(alignment: .leading, spacing: 2) {
                    Text(grid.label)
                        .font(Typeface.display(24))
                        .foregroundStyle(Palette.fg)
                    Text(grid.subtitle)
                        .font(.system(size: 11))
                        .foregroundStyle(Palette.muted)
                }
                Spacer()
                Button {
                    UIPasteboard.general.string = grid.numbers.map(String.init).joined(separator: " ")
                    withAnimation(.snappy(duration: 0.25)) { copied = true }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) {
                        withAnimation(.smooth(duration: 0.3)) { copied = false }
                    }
                } label: {
                    Image(systemName: copied ? "checkmark.circle.fill" : "square.on.square")
                        .font(.system(size: 15, weight: .medium))
                        .foregroundStyle(copied ? Palette.gain : Palette.muted)
                        .frame(width: 38, height: 38)
                        .background(Palette.elevated, in: Circle())
                }
                .buttonStyle(.plain)
            }

            FlexibleBalls(numbers: grid.numbers, last: nil)

            HStack(spacing: 8) {
                StatPill(label: "ESPÉRANCE", value: String(format: "%.2f hits", grid.expectedHits))
                StatPill(label: "HASARD", value: String(format: "%.2f hits", grid.baseExpected))
                StatPill(label: "COTE MAX", value: Format.odds(grid.basePAllHit))
            }

            if let targetDraw {
                HStack(spacing: 5) {
                    Image(systemName: "arrow.right.circle.fill")
                        .font(.system(size: 11))
                        .foregroundStyle(Palette.gold)
                    Text("Prête pour le tirage #\(targetDraw)")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(Palette.goldSoft)
                        .contentTransition(.numericText())
                }
            }
        }
        .sensoryFeedback(.success, trigger: copied) { _, newValue in newValue }
    }
}
