import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        if let payload = store.payload {
            historyBody(payload: payload)
                .task(id: "\(payload.last?.drawNumber ?? 0)-\(store.stake)") {
                    await store.loadJournal()
                }
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

            if let journal = store.journal, !journal.plays.isEmpty {
                JournalCard(journal: journal, jackpots: payload.jackpots)
            } else {
                Card {
                    HStack(spacing: 10) {
                        ProgressView().tint(Palette.gold)
                        Text("Rejeu de la journée en cours…")
                            .font(.system(size: 13))
                            .foregroundStyle(Palette.muted)
                    }
                }
            }

            if rows.isEmpty {
                Card {
                    Text("Pas encore de tirage aujourd’hui. Reprise à 06:05.")
                        .font(.system(size: 14))
                        .foregroundStyle(Palette.muted)
                }
            } else {
                // 1 colonne sur iPhone, 2 sur iPad.
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 320), spacing: 12)], spacing: 12) {
                    ForEach(rows) { d in
                        row(d, previous: byNumber[d.drawNumber - 1])
                    }
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
        historyRow(d, previous: previous)
    }
}

// Journal du jour : chaque tirage rejoué avec les 9 grilles que le modèle
// aurait proposées à ce moment-là, et le verdict — quoi, quand, combien.
struct JournalCard: View {
    var journal: DayJournal
    var jackpots: [Jackpot]

    private struct Line: Identifiable {
        var label: String
        var plays: Int
        var hits: Int
        var expected: Double
        var best: Int
        var bestAt: String
        var id: String { label }
    }

    private var lines: [Line] {
        var out: [Line] = []
        for kind in GridKind.allCases {
            for variant in [1, 2, 3] {
                var plays = 0
                var hits = 0
                var best = 0
                var bestAt = "—"
                var label = ""
                for day in journal.plays {
                    guard let gp = day.plays.first(where: { $0.kind == kind && $0.variant == variant }) else { continue }
                    label = gp.label
                    plays += 1
                    hits += gp.hits
                    if gp.hits > best {
                        best = gp.hits
                        bestAt = day.time
                    }
                }
                if plays > 0 {
                    out.append(Line(
                        label: label,
                        plays: plays,
                        hits: hits,
                        expected: Double(plays * journal.stake) * ProphetConst.baseP,
                        best: best,
                        bestAt: bestAt
                    ))
                }
            }
        }
        return out
    }

    private var bestMoves: [(label: String, hits: Int, drawNumber: Int, time: String)] {
        var all: [(String, Int, Int, String)] = []
        for day in journal.plays {
            for gp in day.plays {
                all.append((gp.label, gp.hits, day.drawNumber, day.time))
            }
        }
        return Array(all.sorted { $0.1 > $1.1 }.prefix(3))
    }

    private var jackpotResult: (count: Int, francs: Double) {
        let amount = jackpots.first { $0.stake == journal.stake }.map { j in
            j.amount >= 10_000 ? j.amount / 100 : j.amount
        } ?? 0
        var count = 0
        for day in journal.plays {
            for gp in day.plays where gp.hits == journal.stake {
                count += 1
            }
        }
        return (count, Double(count) * amount)
    }

    var body: some View {
        let jackpot = jackpotResult

        Card(tint: Palette.gold) {
            VStack(alignment: .leading, spacing: 4) {
                Overline(text: "JOURNAL DU JOUR · MISE \(journal.stake)")
                Text("\(journal.plays.count) tirages rejoués")
                    .font(Typeface.display(22))
                    .foregroundStyle(Palette.fg)
            }
            Text("Pour chaque tirage de la journée, l’app reconstruit ce que ses 9 grilles auraient prédit avec l’état du modèle d’alors — jamais avec le tirage lui-même — puis les confronte au résultat.")
                .font(.system(size: 12))
                .foregroundStyle(Palette.muted)

            if jackpot.count > 0 {
                Text("Jackpot \(journal.stake)/\(journal.stake) touché \(jackpot.count)× — ≈ CHF \(Format.ch.string(from: NSNumber(value: jackpot.francs.rounded())) ?? "—") au montant du jour !")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Palette.gain)
            } else {
                Text("Jackpot \(journal.stake)/\(journal.stake) : aucun touché aujourd’hui — gains CHF publiés : 0.")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(Palette.muted)
            }

            Overline(text: "MEILLEURS COUPS")
            VStack(spacing: 6) {
                ForEach(Array(bestMoves.enumerated()), id: \.offset) { _, move in
                    HStack(spacing: 8) {
                        Text("\(move.hits)/\(journal.stake)")
                            .font(Typeface.mono(13, weight: .semibold))
                            .foregroundStyle(Palette.goldSoft)
                            .frame(width: 44, alignment: .leading)
                        Text(move.label)
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(Palette.fg)
                        Spacer()
                        Text("#\(move.drawNumber) · \(move.time)")
                            .font(Typeface.mono(11))
                            .foregroundStyle(Palette.subtle)
                    }
                }
            }

            Divider().overlay(Color.white.opacity(0.07))

            VStack(spacing: 7) {
                ForEach(lines) { line in
                    HStack(spacing: 8) {
                        Text(line.label)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Palette.fg)
                            .frame(width: 96, alignment: .leading)
                        Text("\(line.hits) hits")
                            .font(Typeface.mono(11))
                            .foregroundStyle(Palette.muted)
                        deltaChip(Double(line.hits) - line.expected)
                        Spacer()
                        Text("max \(line.best)/\(journal.stake) · \(line.bestAt)")
                            .font(Typeface.mono(11))
                            .foregroundStyle(Palette.subtle)
                    }
                }
            }

            Text("L’API Loro publie les montants des jackpots k/k mais pas le barème des rangs intermédiaires : l’app compte les rangs sans inventer leurs montants.")
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)
        }
    }

    private func deltaChip(_ delta: Double) -> some View {
        let positive = delta >= 0
        return Text(String(format: "%@%.1f", positive ? "+" : "", delta))
            .font(Typeface.mono(10, weight: .semibold))
            .foregroundStyle(positive ? Palette.gain : Palette.live)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background((positive ? Palette.gain : Palette.live).opacity(0.13), in: Capsule())
    }
}

extension HistoryView {
    private func historyRow(_ d: Draw, previous: Draw?) -> some View {
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
