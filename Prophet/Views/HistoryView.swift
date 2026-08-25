import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let payload = store.payload {
            historyBody(payload: payload)
        } else {
            ProgressView().tint(Palette.gold)
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
        let byNumber: [Int: Draw] = {
            var out: [Int: Draw] = [:]
            for d in payload.history { out[d.drawNumber] = d }
            return out
        }()

        VStack(alignment: .leading, spacing: 16) {
            sessionCard(rows: rows, isToday: !payload.today.isEmpty)

            if rows.isEmpty {
                Card {
                    Text("Pas encore de tirage aujourd’hui. Reprise à 06:05.")
                        .font(.system(size: 14))
                        .foregroundStyle(Palette.muted)
                }
            } else {
                ForEach(rows) { d in
                    row(d, previous: byNumber[d.drawNumber - 1])
                }
            }
        }
    }

    private func sessionCard(rows: [Draw], isToday: Bool) -> some View {
        var freq = [Int](repeating: 0, count: ProphetConst.poolSize)
        for d in rows {
            for n in d.numbers where (1...ProphetConst.poolSize).contains(n) {
                freq[n - 1] += 1
            }
        }
        let top = freq.enumerated().sorted { $0.element > $1.element }.prefix(3)

        return Card {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: isToday ? "SÉANCE DU JOUR" : "DERNIÈRE SÉANCE")
                    Text("\(rows.count) tirages")
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                        .contentTransition(.numericText())
                    Text("Source Loterie Romande · fenêtre continue")
                        .font(.system(size: 12))
                        .foregroundStyle(Palette.subtle)
                }
                Spacer()
                if !rows.isEmpty {
                    VStack(alignment: .trailing, spacing: 6) {
                        Overline(text: "TOP SÉANCE")
                        HStack(spacing: 6) {
                            ForEach(Array(top), id: \.offset) { item in
                                NumberBall(n: item.offset + 1, size: 28, tone: .hit)
                            }
                        }
                    }
                }
            }
        }
    }

    private func row(_ d: Draw, previous: Draw?) -> some View {
        let repeats = Set(previous?.numbers ?? [])
        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("#\(d.drawNumber)")
                    .font(Typeface.mono(12, weight: .medium))
                    .foregroundStyle(Palette.muted)
                if let boost = d.boost {
                    Text("Boost ×\(boost)")
                        .font(Typeface.mono(10, weight: .semibold))
                        .foregroundStyle(Palette.gold)
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(Palette.gold.opacity(0.12), in: Capsule())
                }
                Spacer()
                if let date = Zurich.parseISO(d.drawDate) {
                    Text(Zurich.parts(date).time)
                        .font(Typeface.mono(12))
                        .foregroundStyle(Palette.subtle)
                }
            }
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 30), spacing: 6)], spacing: 6) {
                ForEach(d.numbers, id: \.self) { n in
                    NumberBall(n: n, size: 30, tone: repeats.contains(n) ? .hot : .plain)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Palette.surface.opacity(0.8))
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
        )
    }
}
