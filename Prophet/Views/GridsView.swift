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
                Text("Cote de base \(pack.oddsLabel) · modèle recalibré après chaque tirage")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.subtle)
                ledgerCard
                ForEach(pack.grids) { grid in
                    GridCard(grid: grid, last: store.payload?.last)
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
    var last: Draw?
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

            FlexibleBalls(numbers: grid.numbers, last: last)

            HStack(spacing: 8) {
                StatPill(label: "ESPÉRANCE", value: String(format: "%.2f hits", grid.expectedHits))
                StatPill(label: "HASARD", value: String(format: "%.2f hits", grid.baseExpected))
                StatPill(label: "COTE MAX", value: Format.odds(grid.basePAllHit))
            }

            if let last {
                Text("Recouvrement vs #\(last.drawNumber) : \(Hits.inDraw(grid.numbers, last))/\(grid.numbers.count)")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
            }
        }
        .sensoryFeedback(.success, trigger: copied) { _, newValue in newValue }
    }
}
