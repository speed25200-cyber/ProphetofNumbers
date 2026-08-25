import SwiftUI

// Fond aurora : trois halos statiques — zéro repaint en continu,
// le GPU reste disponible pour le défilement.
struct AuroraBackground: View {
    var body: some View {
        ZStack {
            Palette.bg
            RadialGradient(
                colors: [Palette.violet.opacity(0.16), .clear],
                center: UnitPoint(x: 0.12, y: 0.02),
                startRadius: 0, endRadius: 440
            )
            RadialGradient(
                colors: [Palette.gold.opacity(0.08), .clear],
                center: UnitPoint(x: 0.95, y: 0.18),
                startRadius: 0, endRadius: 400
            )
            RadialGradient(
                colors: [Palette.teal.opacity(0.07), .clear],
                center: UnitPoint(x: 0.5, y: 1.05),
                startRadius: 0, endRadius: 520
            )
        }
        .ignoresSafeArea()
    }
}

struct Card<Content: View>: View {
    var tint: Color?
    @ViewBuilder var content: Content

    init(tint: Color? = nil, @ViewBuilder content: () -> Content) {
        self.tint = tint
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) { content }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 26, style: .continuous)
                    .fill(Palette.surface)
                    .overlay(
                        RoundedRectangle(cornerRadius: 26, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [(tint ?? .white).opacity(0.06), .clear],
                                    startPoint: .topLeading,
                                    endPoint: .center
                                )
                            )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 26, style: .continuous)
                    .strokeBorder(Palette.cardStroke, lineWidth: 1)
            )
            // Aplatir la carte avant l'ombre : une seule texture à ombrer.
            .compositingGroup()
            .shadow(color: .black.opacity(0.35), radius: 14, x: 0, y: 8)
    }
}

struct Overline: View {
    var text: String
    var color: Color = Palette.subtle

    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .tracking(1.4)
            .foregroundStyle(color)
    }
}

struct NumberBall: View {
    var n: Int
    var size: CGFloat = 36
    var tone: Tone = .plain

    enum Tone { case plain, pick, hit, hot, cold }

    var body: some View {
        Text("\(n)")
            .font(Typeface.mono(size * 0.36, weight: .semibold))
            .foregroundStyle(tone == .hit ? Palette.accentFg : Palette.fg)
            .frame(width: size, height: size)
            .background(background)
            .overlay(Circle().strokeBorder(stroke, lineWidth: 1))
            .shadow(color: tone == .hit ? Palette.gold.opacity(0.45) : .clear, radius: 7)
    }

    @ViewBuilder private var background: some View {
        switch tone {
        case .hit:
            Circle().fill(Palette.goldGradient)
        case .hot:
            Circle().fill(Palette.live.opacity(0.22))
        case .cold:
            Circle().fill(Palette.cold.opacity(0.20))
        case .plain, .pick:
            Circle().fill(Palette.elevated)
        }
    }

    private var stroke: Color {
        switch tone {
        case .hit: return Palette.goldSoft.opacity(0.8)
        case .hot: return Palette.live.opacity(0.4)
        case .cold: return Palette.cold.opacity(0.4)
        case .plain, .pick: return Color.white.opacity(0.10)
        }
    }
}

struct FlexibleBalls: View {
    var numbers: [Int]
    var last: Draw?

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 38), spacing: 8)], spacing: 8) {
            ForEach(numbers, id: \.self) { n in
                NumberBall(n: n, size: 38, tone: last?.numbers.contains(n) == true ? .hit : .pick)
            }
        }
    }
}

struct StatPill: View {
    var label: String
    var value: String
    var accent: Color = Palette.fg

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .tracking(1.1)
                .foregroundStyle(Palette.subtle)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(value)
                .font(Typeface.mono(13, weight: .medium))
                .foregroundStyle(accent)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(Palette.elevated.opacity(0.7))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

// Anneau de progression sur le cycle de 5 minutes du Loto Express.
struct CountdownRing: View {
    var target: Date
    var clockOffset: TimeInterval = 0
    var cycle: Double = 300

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { ctx in
            let remaining = max(0, target.timeIntervalSince(ctx.date.addingTimeInterval(clockOffset)))
            let progress = 1 - min(1, remaining / cycle)
            ZStack {
                Circle()
                    .stroke(Palette.elevated, lineWidth: 5)
                Circle()
                    .trim(from: 0, to: max(0.001, progress))
                    .stroke(Palette.goldGradient, style: StrokeStyle(lineWidth: 5, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .animation(.linear(duration: 1), value: progress)
                Image(systemName: "bolt.fill")
                    .font(.system(size: 15))
                    .foregroundStyle(remaining < 30 ? Palette.live : Palette.gold)
            }
            .frame(width: 60, height: 60)
        }
    }
}

// Témoin de synchronisation : vert = flux frais (< 30 s), rouge = retard.
struct LiveBadge: View {
    var fetchedAt: Date?
    @State private var pulse = false

    var body: some View {
        TimelineView(.periodic(from: .now, by: 2)) { ctx in
            let age = fetchedAt.map { ctx.date.timeIntervalSince($0) }
            let (color, label): (Color, String) = {
                guard let age else { return (Palette.subtle, "SYNC…") }
                return age < 30 ? (Palette.gain, "LIVE") : (Palette.live, "RETARD")
            }()
            HStack(spacing: 6) {
                Circle()
                    .fill(color)
                    .frame(width: 6, height: 6)
                    .overlay(
                        Circle()
                            .stroke(color.opacity(0.6), lineWidth: 1)
                            .scaleEffect(pulse ? 2.8 : 1)
                            .opacity(pulse ? 0 : 0.8)
                    )
                Text(label)
                    .font(.system(size: 10, weight: .semibold))
                    .tracking(1.6)
                    .foregroundStyle(Palette.muted)
            }
            .padding(.horizontal, 11)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay(Capsule().strokeBorder(Color.white.opacity(0.10), lineWidth: 1))
        }
        .onAppear {
            withAnimation(.easeOut(duration: 1.8).repeatForever(autoreverses: false)) {
                pulse = true
            }
        }
    }
}

struct ProphetButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 14, weight: .semibold))
            .foregroundStyle(Palette.accentFg)
            .padding(.horizontal, 20)
            .padding(.vertical, 13)
            .background(Palette.goldGradient)
            .clipShape(Capsule())
            .opacity(configuration.isPressed ? 0.8 : 1)
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(.snappy(duration: 0.2), value: configuration.isPressed)
    }
}
