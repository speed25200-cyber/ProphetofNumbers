import SwiftUI

enum ProphetTab: String, CaseIterable, Identifiable {
    case live, grids, analyse, history
    var id: String { rawValue }

    var label: String {
        switch self {
        case .live: return "Tirage"
        case .grids: return "Grilles"
        case .analyse: return "Analyse"
        case .history: return "Séance"
        }
    }

    var symbol: String {
        switch self {
        case .live: return "dot.radiowaves.left.and.right"
        case .grids: return "sparkles"
        case .analyse: return "chart.bar"
        case .history: return "clock.arrow.circlepath"
        }
    }
}

struct RootView: View {
    @EnvironmentObject var store: ProphetStore
    @State private var tab: ProphetTab = .live

    var body: some View {
        ZStack {
            Palette.bg.ignoresSafeArea()
            VStack(spacing: 0) {
                header
                content
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                tabBar
            }
        }
    }

    private var header: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 4) {
                Text("GÉNÉRATEUR MAISON")
                    .font(.system(size: 11, weight: .medium))
                    .tracking(2.4)
                    .foregroundStyle(Palette.subtle)
                Text("Prophet")
                    .font(Typeface.display(34))
                    .foregroundStyle(Palette.fg)
            }
            Spacer()
            HStack(spacing: 8) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(Palette.live)
                        .frame(width: 6, height: 6)
                        .opacity(store.payload == nil ? 0.4 : 1)
                    Text("LIVE")
                        .font(.system(size: 11, weight: .medium))
                        .tracking(1.4)
                        .foregroundStyle(Palette.muted)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Palette.elevated)
                .clipShape(Capsule())
                .overlay(Capsule().stroke(Palette.fg.opacity(0.12), lineWidth: 1))
                if let next = store.payload?.nextDrawNumber {
                    Text("#\(next)")
                        .font(Typeface.mono(12))
                        .foregroundStyle(Palette.muted)
                } else if let last = store.payload?.last {
                    Text("#\(last.drawNumber)")
                        .font(Typeface.mono(12))
                        .foregroundStyle(Palette.muted)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 12)
        .padding(.bottom, 12)
        .background(Palette.bg.opacity(0.92))
    }

    @ViewBuilder
    private var content: some View {
        if let message = store.error, store.payload == nil {
            VStack(spacing: 14) {
                Text("Flux indisponible")
                    .font(Typeface.display(28))
                    .foregroundStyle(Palette.fg)
                Text(message)
                    .font(.system(size: 14))
                    .foregroundStyle(Palette.muted)
                    .multilineTextAlignment(.center)
                Button("Réessayer") { Task { await store.refresh(force: true) } }
                    .buttonStyle(ProphetButtonStyle())
            }
            .padding(24)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if store.payload == nil {
            ProgressView().tint(Palette.accent).frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            ScrollView {
                Group {
                    switch tab {
                    case .live: LiveView()
                    case .grids: GridsView()
                    case .analyse: AnalyseView()
                    case .history: HistoryView()
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .padding(.bottom, 28)
            }
        }
    }

    private var tabBar: some View {
        HStack(spacing: 4) {
            ForEach(ProphetTab.allCases) { item in
                Button {
                    tab = item
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: item.symbol)
                            .font(.system(size: 16, weight: tab == item ? .semibold : .regular))
                        Text(item.label)
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundStyle(tab == item ? Palette.fg : Palette.subtle)
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 8)
        .padding(.top, 8)
        .padding(.bottom, 8)
        .background(Palette.bg.opacity(0.94))
        .overlay(alignment: .top) {
            Rectangle().fill(Palette.fg.opacity(0.12)).frame(height: 1)
        }
    }
}

struct ProphetButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 14, weight: .semibold))
            .foregroundStyle(Palette.accentFg)
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
            .background(Palette.accent.opacity(configuration.isPressed ? 0.8 : 1))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct NumberBall: View {
    var n: Int
    var size: CGFloat = 32
    var tone: Tone = .plain

    enum Tone { case plain, pick, hit, hot, cold }

    var body: some View {
        Text("\(n)")
            .font(Typeface.mono(size * 0.38, weight: .medium))
            .foregroundStyle(fg)
            .frame(width: size, height: size)
            .background(bg)
            .clipShape(Circle())
            .overlay(Circle().stroke(Palette.fg.opacity(0.12), lineWidth: 1))
    }

    private var bg: Color {
        switch tone {
        case .plain: return Palette.elevated
        case .pick: return Palette.elevated
        case .hit: return Palette.accent
        case .hot: return Palette.gain.opacity(0.35)
        case .cold: return Palette.live.opacity(0.28)
        }
    }

    private var fg: Color {
        tone == .hit ? Palette.accentFg : Palette.fg
    }
}

struct Card<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Palette.surface)
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Palette.fg.opacity(0.12), lineWidth: 1)
            )
    }
}
