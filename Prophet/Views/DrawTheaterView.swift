import SwiftUI

struct DrawTheaterView: View {
    @EnvironmentObject var draw: DrawStream

    var body: some View {
        let copy = DrawReveal.copy(scene: draw.state?.scene ?? "")
        let shown = draw.revealed
        let extra = draw.state?.meta.extra
        let boost = draw.state?.meta.boost
        let drawing = draw.state?.scene == "DrawScene" || draw.state?.scene == "ExtraScene"

        Card {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(copy.kicker.uppercased())
                        .font(.system(size: 11, weight: .medium))
                        .tracking(1.8)
                        .foregroundStyle(Palette.subtle)
                    Text(copy.title)
                        .font(Typeface.display(26))
                        .foregroundStyle(Palette.fg)
                    HStack(spacing: 8) {
                        if let id = draw.state?.meta.id {
                            Text("#\(id)").font(Typeface.mono(12)).foregroundStyle(Palette.muted)
                        }
                        if let boost {
                            Text("Boost ×\(formatBoost(boost))")
                                .font(Typeface.mono(12))
                                .foregroundStyle(Palette.muted)
                        }
                    }
                }
                Spacer()
                HStack(spacing: 6) {
                    Circle()
                        .fill(draw.status == .live ? Palette.live : Palette.subtle)
                        .frame(width: 6, height: 6)
                    Text(draw.status == .live ? (drawing ? "TIRAGE" : "LIVE") : (draw.status == .error ? "COUPÉ" : "SYNC"))
                        .font(.system(size: 11, weight: .medium))
                        .tracking(1.4)
                        .foregroundStyle(Palette.muted)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Palette.elevated)
                .clipShape(Capsule())
                .overlay(Capsule().stroke(Palette.fg.opacity(0.12), lineWidth: 1))
            }

            if shown.isEmpty && !drawing {
                Text(draw.state?.scene == "NightModeScene" ? "Reprise à 06:05" : "En attente du prochain tour.")
                    .font(.system(size: 14))
                    .foregroundStyle(Palette.muted)
                    .padding(.top, 12)
            } else {
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 5), spacing: 8) {
                    ForEach(0..<20, id: \.self) { i in
                        if i < shown.count {
                            NumberBall(
                                n: shown[i],
                                size: 36,
                                tone: extra == shown[i] ? .hit : .plain
                            )
                        } else {
                            Circle()
                                .stroke(Palette.fg.opacity(0.12), lineWidth: 1)
                                .background(Palette.elevated.opacity(0.4))
                                .clipShape(Circle())
                                .frame(width: 36, height: 36)
                        }
                    }
                }
                .padding(.top, 12)
                if drawing && shown.count > 0 && shown.count < 20 {
                    Text("Boule \(shown.count) / 20")
                        .font(.system(size: 11, weight: .medium))
                        .tracking(1.6)
                        .foregroundStyle(Palette.subtle)
                        .padding(.top, 8)
                }
            }

            if extra != nil || boost != nil {
                HStack(spacing: 12) {
                    if let extra {
                        (Text("Extra ").foregroundStyle(Palette.muted) +
                         Text("\(extra)").foregroundStyle(Palette.fg))
                    }
                    if let boost {
                        (Text("Boost ").foregroundStyle(Palette.muted) +
                         Text("×\(formatBoost(boost))").foregroundStyle(Palette.fg))
                    }
                }
                .font(Typeface.mono(12))
                .padding(.top, 12)
            }

            if draw.status == .error {
                Button("Relancer le flux") { draw.retryNow() }
                    .buttonStyle(ProphetButtonStyle())
                    .padding(.top, 8)
            }

            Text("Flux officiel LoRo (animation ONLINE), pas une caméra de café.")
                .font(.system(size: 11))
                .foregroundStyle(Palette.subtle)
                .padding(.top, 8)
        }
    }

    private func formatBoost(_ n: Double) -> String {
        n == floor(n) ? String(Int(n)) : String(format: "%g", n)
    }
}
