import SwiftUI

struct LiveView: View {
    @EnvironmentObject var store: ProphetStore

    var body: some View {
        let payload = store.payload
        VStack(spacing: 16) {
            heroCard(payload)
            if let oracle = store.oracle {
                SignalCard(oracle: oracle)
            }
            if let last = payload?.last {
                LastDrawCard(last: last, payload: payload)
            }
        }
    }

    private func heroCard(_ payload: LivePayload?) -> some View {
        Card(tint: Palette.gold) {
            let offset = payload?.clockOffset ?? 0
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 10) {
                    Overline(text: "PROCHAIN TIRAGE")
                    if let at = payload?.nextDrawAt {
                        TimelineView(.periodic(from: .now, by: 1)) { ctx in
                            let cd = Format.countdown(to: at, now: ctx.date.addingTimeInterval(offset))
                            Text(cd.label)
                                .font(Typeface.mono(50, weight: .semibold))
                                .foregroundStyle(cd.urgent ? Palette.live : Palette.fg)
                                .lineLimit(1)
                                .minimumScaleFactor(0.4)
                                .contentTransition(.numericText(countsDown: true))
                                .animation(.snappy(duration: 0.3), value: cd.label)
                        }
                        Text(Format.clock(at))
                            .font(.system(size: 13))
                            .foregroundStyle(Palette.muted)
                    } else {
                        Text("—")
                            .font(Typeface.mono(50, weight: .semibold))
                            .foregroundStyle(Palette.subtle)
                    }
                }
                Spacer()
                if let at = payload?.nextDrawAt {
                    VStack(spacing: 6) {
                        CountdownRing(target: at, clockOffset: offset)
                        if let n = payload?.nextDrawNumber {
                            Text("#\(n)")
                                .font(Typeface.mono(11))
                                .foregroundStyle(Palette.muted)
                                .contentTransition(.numericText())
                        }
                    }
                }
            }
            if let pending = payload?.pendingDrawNumber, payload?.hole == true {
                Text("En attente du résultat #\(pending) — les grilles visent déjà le tour suivant.")
                    .font(.system(size: 12))
                    .foregroundStyle(Palette.gold)
            }
            if let jacks = payload?.jackpots, !jacks.isEmpty {
                HStack(spacing: 6) {
                    ForEach(jacks) { j in
                        VStack(spacing: 4) {
                            Text("\(j.stake)/\(j.stake)")
                                .font(Typeface.mono(10))
                                .foregroundStyle(Palette.subtle)
                            Text(Format.chf(j.amount))
                                .font(Typeface.mono(11, weight: .medium))
                                .foregroundStyle(Palette.goldSoft)
                                .lineLimit(1)
                                .minimumScaleFactor(0.7)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 9)
                        .background(Palette.elevated.opacity(0.7))
                        .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
                    }
                }
            }
        }
    }
}

struct SignalCard: View {
    var oracle: OracleResult

    var body: some View {
        Card {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "SIGNAL DU MODÈLE")
                    HStack(alignment: .firstTextBaseline, spacing: 7) {
                        Text("\(oracle.confidence)")
                            .font(Typeface.display(30))
                            .foregroundStyle(Palette.fg)
                            .contentTransition(.numericText())
                        Text("/ 100 · 50 = hasard pur")
                            .font(.system(size: 11))
                            .foregroundStyle(Palette.subtle)
                    }
                }
                Spacer()
                Text(oracle.regimeLabel)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(Palette.gold)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Palette.gold.opacity(0.12), in: Capsule())
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Palette.elevated)
                    Capsule()
                        .fill(Palette.goldGradient)
                        .frame(width: max(8, geo.size.width * CGFloat(oracle.confidence) / 100))
                    Rectangle()
                        .fill(Palette.fg.opacity(0.45))
                        .frame(width: 1.5)
                        .offset(x: geo.size.width / 2)
                }
            }
            .frame(height: 6)
            .animation(.smooth(duration: 0.5), value: oracle.confidence)

            Text("\(oracle.sampleSize) tirages · \(oracle.swarm.headCount) têtes · gén. \(oracle.swarm.generation) · \(oracle.todayDraws) auj.")
                .font(Typeface.mono(11))
                .foregroundStyle(Palette.muted)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
            Text(oracle.regimeDetail)
                .font(.system(size: 12))
                .foregroundStyle(Palette.subtle)
        }
    }
}

struct LastDrawCard: View {
    var last: Draw
    var payload: LivePayload?

    var body: some View {
        let previous = payload?.history.first { $0.drawNumber == last.drawNumber - 1 }
        let repeats = Set(previous?.numbers ?? [])

        Card {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Overline(text: "DERNIER TIRAGE")
                    Text("#\(last.drawNumber)")
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                        .contentTransition(.numericText())
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
                    NumberBall(n: n, size: 38, tone: repeats.contains(n) ? .hot : .plain)
                }
            }
            .id(last.drawNumber)
            .transition(.opacity.combined(with: .scale(scale: 0.92)))

            HStack(spacing: 12) {
                if let boost = last.boost {
                    chip("Boost", "×\(boost)")
                }
                if let bonus = last.bonus {
                    chip("Bonus", "\(bonus)")
                }
                chip("Séance", "\(payload?.today.count ?? 0) tirages")
            }
            if !repeats.isEmpty {
                Text("Teinté chaud = numéro répété du tirage précédent")
                    .font(.system(size: 11))
                    .foregroundStyle(Palette.subtle)
            }
        }
    }

    private func chip(_ label: String, _ value: String) -> some View {
        HStack(spacing: 4) {
            Text(label).foregroundStyle(Palette.subtle)
            Text(value).foregroundStyle(Palette.fg)
        }
        .font(Typeface.mono(12))
    }
}
