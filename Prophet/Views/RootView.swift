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
        case .analyse: return "waveform"
        case .history: return "clock.arrow.circlepath"
        }
    }
}

struct RootView: View {
    @EnvironmentObject var store: ProphetStore
    @State private var tab: ProphetTab = .live
    @Namespace private var tabNS

    var body: some View {
        ZStack {
            AuroraBackground()
            VStack(spacing: 0) {
                header
                content
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .safeAreaInset(edge: .bottom) { tabBar }
        .sensoryFeedback(.selection, trigger: tab)
    }

    private var header: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 3) {
                Overline(text: "LOTO EXPRESS · LORO")
                Text("Prophet")
                    .font(Typeface.display(30, weight: .bold))
                    .tracking(-0.5)
                    .foregroundStyle(Palette.goldGradient)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 6) {
                LiveBadge(fetchedAt: store.payload?.fetchedAt)
                if let payload = store.payload, let last = payload.last {
                    TimelineView(.periodic(from: .now, by: 1)) { ctx in
                        let age = Int(max(0, ctx.date.timeIntervalSince(payload.fetchedAt)))
                        Text("#\(last.drawNumber) · sync \(age) s")
                            .font(Typeface.mono(11))
                            .foregroundStyle(Palette.subtle)
                            .contentTransition(.numericText())
                    }
                }
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 8)
        .padding(.bottom, 14)
    }

    @ViewBuilder
    private var content: some View {
        if let message = store.error, store.payload == nil {
            VStack(spacing: 16) {
                Image(systemName: "antenna.radiowaves.left.and.right.slash")
                    .font(.system(size: 30))
                    .foregroundStyle(Palette.subtle)
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
            VStack(spacing: 14) {
                ProgressView().tint(Palette.gold)
                Text("Connexion au flux Loro…")
                    .font(.system(size: 13))
                    .foregroundStyle(Palette.subtle)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            ScrollView {
                VStack(spacing: 16) {
                    switch tab {
                    case .live: LiveView()
                    case .grids: GridsView()
                    case .analyse: AnalyseView()
                    case .history: HistoryView()
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 6)
                .padding(.bottom, 20)
                .id(tab)
                .transition(
                    .asymmetric(
                        insertion: .opacity.combined(with: .offset(y: 14)),
                        removal: .opacity
                    )
                )
            }
            .scrollIndicators(.hidden)
        }
    }

    private var tabBar: some View {
        HStack(spacing: 2) {
            ForEach(ProphetTab.allCases) { item in
                Button {
                    guard tab != item else { return }
                    withAnimation(.snappy(duration: 0.32)) { tab = item }
                } label: {
                    VStack(spacing: 3) {
                        Image(systemName: item.symbol)
                            .font(.system(size: 15, weight: .semibold))
                        Text(item.label)
                            .font(.system(size: 10, weight: .semibold))
                    }
                    .foregroundStyle(tab == item ? Palette.accentFg : Palette.muted)
                    .frame(maxWidth: .infinity)
                    .frame(height: 52)
                    .contentShape(Rectangle())
                    .background {
                        if tab == item {
                            Capsule()
                                .fill(Palette.goldGradient)
                                .matchedGeometryEffect(id: "tabpill", in: tabNS)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(5)
        .background(.ultraThinMaterial, in: Capsule())
        .overlay(Capsule().strokeBorder(Color.white.opacity(0.10), lineWidth: 1))
        .shadow(color: .black.opacity(0.5), radius: 18, x: 0, y: 8)
        .padding(.horizontal, 20)
        .padding(.bottom, 4)
    }
}
