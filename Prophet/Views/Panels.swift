import SwiftUI
import UIKit

struct LiveView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        let payload = store.payload
        let count = store.countdown
        VStack(spacing: 16) {
            Card {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("PROCHAIN TIRAGE")
                            .font(.system(size: 11, weight: .medium))
                            .tracking(1.8)
                            .foregroundStyle(Palette.subtle)
                        Text(count.label)
                            .font(Typeface.mono(48, weight: .medium))
                            .foregroundStyle(count.urgent ? Palette.live : Palette.fg)
                            .monospacedDigit()
                        if let at = payload?.nextDrawAt {
                            Text(Format.clock(at))
                                .font(.system(size: 14))
                                .foregroundStyle(Palette.muted)
                        }
                        if let pending = payload?.pendingDrawNumber, payload?.hole == true {
                            Text("En attente du résultat #\(pending). Les grilles visent déjà le tour suivant.")
                                .font(.system(size: 12))
                                .foregroundStyle(Palette.warn)
                                .padding(.top, 8)
                        } else {
                            Text("Grilles à jouer maintenant, avant le tirage.")
                                .font(.system(size: 12))
                                .foregroundStyle(Palette.subtle)
                                .padding(.top, 8)
                        }
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 8) {
                        Image(systemName: "timer")
                            .foregroundStyle(Palette.subtle)
                        if let n = payload?.nextDrawNumber {
                            Text("#\(n)")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                        }
                    }
                }
                if let jacks = payload?.jackpots, !jacks.isEmpty {
                    HStack(spacing: 6) {
                        ForEach(jacks) { j in
                            VStack(spacing: 4) {
                                Text("\(j.stake)/\(j.stake)")
                                    .font(Typeface.mono(10))
                                    .foregroundStyle(Palette.subtle)
                                Text(Format.chf(j.amount))
                                    .font(Typeface.mono(11))
                                    .foregroundStyle(Palette.fg)
                                    .lineLimit(1)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                            .background(Palette.elevated)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }
                    }
                    .padding(.top, 16)
                }
            }

            if let oracle = store.oracle {
                Card {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("CRF-9 · CONFIANCE")
                                .font(.system(size: 11, weight: .medium))
                                .tracking(1.8)
                                .foregroundStyle(Palette.subtle)
                            Text("\(oracle.confidence)%")
                                .font(Typeface.display(28))
                                .foregroundStyle(Palette.fg)
                        }
                        Spacer()
                        Text(oracle.regimeLabel)
                            .font(.system(size: 12))
                            .foregroundStyle(Palette.muted)
                            .multilineTextAlignment(.trailing)
                            .frame(maxWidth: 180, alignment: .trailing)
                    }
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule().fill(Palette.elevated)
                            Capsule()
                                .fill(Palette.accent)
                                .frame(width: geo.size.width * CGFloat(oracle.confidence) / 100)
                        }
                    }
                    .frame(height: 6)
                    .padding(.top, 10)
                    Text("\(oracle.sampleSize) tirages en mémoire · \(oracle.todayDraws) aujourd’hui · \(oracle.regimeDetail)")
                        .font(.system(size: 12))
                        .foregroundStyle(Palette.subtle)
                        .padding(.top, 8)
                }
            }

            if let last = payload?.last {
                Card {
                    HStack(alignment: .firstTextBaseline) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("DERNIER TIRAGE")
                                .font(.system(size: 11, weight: .medium))
                                .tracking(1.8)
                                .foregroundStyle(Palette.subtle)
                            Text("#\(last.drawNumber)")
                                .font(Typeface.display(26))
                                .foregroundStyle(Palette.fg)
                        }
                        Spacer()
                        if let date = Zurich.parseISO(last.drawDate) {
                            Text(Format.clock(date))
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                        }
                    }
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 5), spacing: 8) {
                        ForEach(last.numbers, id: \.self) { n in
                            NumberBall(n: n, size: 36)
                        }
                    }
                    .padding(.top, 12)
                    HStack(spacing: 12) {
                        if let boost = last.boost {
                            (Text("Boost ").foregroundStyle(Palette.muted) +
                             Text("×\(boost)").foregroundStyle(Palette.fg))
                        }
                        if let bonus = last.bonus {
                            (Text("Bonus ").foregroundStyle(Palette.muted) +
                             Text("\(bonus)").foregroundStyle(Palette.fg))
                        }
                        (Text("Séance ").foregroundStyle(Palette.muted) +
                         Text("\(payload?.today.count ?? 0) tirages").foregroundStyle(Palette.fg))
                    }
                    .font(Typeface.mono(12))
                    .padding(.top, 12)
                }
            }
        }
    }
}

struct GridsView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let oracle = store.oracle,
           let pack = oracle.stakes.first(where: { $0.stake == store.stake }) {
            gridsBody(pack: pack)
        } else {
            ProgressView().tint(Palette.accent)
        }
    }

    @ViewBuilder
    private func gridsBody(pack: StakeGrids) -> some View {
        let last = store.payload?.last
        let scored = last.map { draw in
            store.tickets.filter { $0.targetDraw == draw.drawNumber && $0.stake == store.stake }
        } ?? []
        let target = store.payload?.nextDrawNumber
        let gridCaption: String = {
            if let target {
                if let at = store.payload?.nextDrawAt {
                    return "Pour le #\(target) · \(Format.clock(at)) · cote de base \(pack.oddsLabel)"
                }
                return "Pour le #\(target) · cote de base \(pack.oddsLabel)"
            }
            return "Cote de base \(pack.oddsLabel) · modèle recalibré après chaque tirage"
        }()

        VStack(alignment: .leading, spacing: 16) {
            Text("MISE")
                .font(.system(size: 11, weight: .medium))
                .tracking(1.8)
                .foregroundStyle(Palette.subtle)
            HStack(spacing: 4) {
                ForEach(ProphetConst.stakes, id: \.self) { s in
                    Button {
                        store.stake = s
                    } label: {
                        Text("\(s)/\(s)")
                            .font(Typeface.mono(13))
                            .foregroundStyle(store.stake == s ? Palette.accentFg : Palette.muted)
                            .frame(maxWidth: .infinity)
                            .frame(height: 44)
                            .background(store.stake == s ? Palette.accent : Color.clear)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(6)
            .background(Palette.surface)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

            Text(gridCaption)
                .font(.system(size: 12))
                .foregroundStyle(Palette.subtle)
            if let pending = store.payload?.pendingDrawNumber, store.payload?.hole == true {
                Text("Résultat #\(pending) pas encore publié — grilles déjà calées pour le tour suivant.")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.warn)
            }

            if !scored.isEmpty, let last {
                Card {
                    Text("LECTURE DU #\(last.drawNumber)")
                        .font(.system(size: 11, weight: .medium))
                        .tracking(1.8)
                        .foregroundStyle(Palette.subtle)
                    VStack(spacing: 8) {
                        ForEach(scored) { t in
                            HStack {
                                Text(t.kind.tone).foregroundStyle(Palette.muted)
                                Spacer()
                                Text("\(Hits.inDraw(t.numbers, last))/\(store.stake)")
                                    .font(Typeface.mono(14))
                                    .foregroundStyle(Palette.fg)
                            }
                            .font(.system(size: 14))
                        }
                    }
                    .padding(.top, 10)
                }
            }

            ForEach(pack.grids) { grid in
                GridCard(grid: grid, last: last)
            }
        }
    }
}

struct GridCard: View {
    var grid: SuggestedGrid
    var last: Draw?
    @State private var copied = false

    var body: some View {
        Card {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(grid.label)
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                    Text(grid.subtitle)
                        .font(.system(size: 12))
                        .foregroundStyle(Palette.muted)
                }
                Spacer()
                Button {
                    UIPasteboard.general.string = grid.numbers.map(String.init).joined(separator: " ")
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) { copied = false }
                } label: {
                    Image(systemName: copied ? "checkmark" : "square.on.square")
                        .foregroundStyle(Palette.muted)
                        .frame(width: 36, height: 36)
                }
                .buttonStyle(.plain)
            }
            FlexibleBalls(numbers: grid.numbers, last: last)
                .padding(.top, 12)
            HStack(spacing: 8) {
                stat("Espérance", String(format: "%.2f hits", grid.expectedHits))
                stat("Uniforme", String(format: "%.2f hits", grid.baseExpected))
                stat("Cote k/k", Format.odds(grid.basePAllHit))
            }
            .padding(.top, 12)
            if let last {
                Text("Recouvrement vs dernier tirage : \(Hits.inDraw(grid.numbers, last))/\(grid.numbers.count)")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.subtle)
                    .padding(.top, 8)
            }
        }
    }

    private func stat(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.system(size: 11)).foregroundStyle(Palette.subtle)
            Text(value).font(Typeface.mono(12)).foregroundStyle(Palette.fg)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Palette.elevated)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

struct FlexibleBalls: View {
    var numbers: [Int]
    var last: Draw?
    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 36), spacing: 8)], spacing: 8) {
            ForEach(numbers, id: \.self) { n in
                NumberBall(n: n, size: 36, tone: last?.numbers.contains(n) == true ? .hit : .pick)
            }
        }
    }
}

struct AnalyseView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let oracle = store.oracle {
            analyseBody(oracle: oracle)
        } else {
            ProgressView().tint(Palette.accent)
        }
    }

    @ViewBuilder
    private func analyseBody(oracle: OracleResult) -> some View {
        let last = store.payload?.last
        let maxAbs = max(oracle.scores.map { abs($0) }.max() ?? 0.001, 0.001)

        VStack(spacing: 16) {
            Card {
                HStack {
                    Text("Champ 1–80")
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                    Spacer()
                    Image(systemName: "waveform.path.ecg").foregroundStyle(Palette.subtle)
                }
                Text("Intensité CRF-9. Plus clair = plus fort pour le prochain tirage.")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.muted)
                    .padding(.top, 4)
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 10), spacing: 6) {
                    ForEach(1...80, id: \.self) { n in
                        let score = oracle.scores[n - 1]
                        let t = (score + maxAbs) / (2 * maxAbs)
                        let hit = last?.numbers.contains(n) == true
                        Text("\(n)")
                            .font(Typeface.mono(9))
                            .foregroundStyle(hit ? Palette.accentFg : Palette.fg)
                            .frame(height: 28)
                            .frame(maxWidth: .infinity)
                            .background(hit ? Palette.accent : Palette.accent.opacity(0.08 + t * 0.45))
                            .clipShape(Circle())
                    }
                }
                .padding(.top, 12)
            }

            Card {
                Text("Têtes du modèle")
                    .font(Typeface.display(26))
                    .foregroundStyle(Palette.fg)
                Text("Poids adaptés selon le recouvrement glissant des 20 meilleurs.")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.muted)
                    .padding(.top, 4)
                VStack(spacing: 12) {
                    ForEach(oracle.methods) { m in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(m.name).foregroundStyle(Palette.fg)
                                Spacer()
                                Text("\(Int(round(m.weight * 100)))% · \(String(format: "%.1f", m.overlap * 20))/20")
                                    .font(Typeface.mono(12))
                                    .foregroundStyle(Palette.muted)
                            }
                            .font(.system(size: 14))
                            GeometryReader { geo in
                                ZStack(alignment: .leading) {
                                    Capsule().fill(Palette.elevated)
                                    Capsule()
                                        .fill(Palette.accent)
                                        .frame(width: geo.size.width * CGFloat(max(0.06, m.weight)))
                                }
                            }
                            .frame(height: 6)
                            Text(m.blurb)
                                .font(.system(size: 11))
                                .foregroundStyle(Palette.subtle)
                        }
                    }
                }
                .padding(.top, 12)
            }

            if !oracle.movers.isEmpty {
                Card {
                    Text("Mouvement")
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                    Text("Variation de rang après le dernier tirage.")
                        .font(.system(size: 12))
                        .foregroundStyle(Palette.muted)
                        .padding(.top, 4)
                    VStack(spacing: 0) {
                        ForEach(Array(oracle.movers.prefix(8))) { m in
                            HStack {
                                NumberBall(n: m.number, size: 28, tone: m.delta > 0 ? .hot : .cold)
                                Text("rang \(m.rank)")
                                    .font(.system(size: 14))
                                    .foregroundStyle(Palette.muted)
                                Spacer()
                                Text(m.delta > 0 ? "+\(m.delta)" : "\(m.delta)")
                                    .font(Typeface.mono(14))
                                    .foregroundStyle(m.delta > 0 ? Palette.gain : m.delta < 0 ? Palette.live : Palette.muted)
                            }
                            .padding(.vertical, 8)
                        }
                    }
                    .padding(.top, 8)
                }
            }

            Text("Le Loto Express tire 20 boules parmi 80, toutes les 5 minutes. CRF-9 est un ensemble statistique. Un RNG équitable reste imbattable au sens strict — le modèle se recale tout seul dans ce cas.")
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)
                .padding(.horizontal, 4)
        }
    }
}

struct HistoryView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let payload = store.payload {
            historyBody(payload: payload)
        } else {
            ProgressView().tint(Palette.accent)
        }
    }

    @ViewBuilder
    private func historyBody(payload: LivePayload) -> some View {
        let key: String? = {
            if let first = payload.today.first, let d = Zurich.parseISO(first.drawDate) {
                return Zurich.parts(d).dayKey
            }
            if let last = payload.last, let d = Zurich.parseISO(last.drawDate) {
                return Zurich.parts(d).dayKey
            }
            return nil
        }()
        let rows: [Draw] = {
            if let key {
                return payload.history.filter {
                    guard let d = Zurich.parseISO($0.drawDate) else { return false }
                    return Zurich.parts(d).dayKey == key
                }
            }
            return Array(payload.history.prefix(40))
        }()

        VStack(alignment: .leading, spacing: 12) {
            Text(payload.today.isEmpty ? "Dernière séance" : "Séance du jour")
                .font(Typeface.display(26))
                .foregroundStyle(Palette.fg)
            Text("\(rows.count) tirages · source Loterie Romande")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            if rows.isEmpty {
                Card {
                    Text("Pas encore de tirage aujourd’hui. Reprise à 06:05.")
                        .font(.system(size: 14))
                        .foregroundStyle(Palette.muted)
                }
            } else {
                ForEach(rows) { d in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("#\(d.drawNumber)")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                            Spacer()
                            if let date = Zurich.parseISO(d.drawDate) {
                                Text(Zurich.parts(date).time)
                                    .font(Typeface.mono(12))
                                    .foregroundStyle(Palette.subtle)
                            }
                        }
                        FlexibleBalls(numbers: d.numbers, last: nil)
                    }
                    .padding(12)
                    .background(Palette.surface)
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .stroke(Palette.fg.opacity(0.12), lineWidth: 1)
                    )
                }
            }
        }
    }
}
