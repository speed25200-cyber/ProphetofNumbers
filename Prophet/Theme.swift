import SwiftUI

enum Palette {
    // Fond obsidienne, très légèrement bleuté
    static let bg = Color(red: 0.024, green: 0.024, blue: 0.043)
    static let surface = Color(red: 0.055, green: 0.055, blue: 0.086)
    static let elevated = Color(red: 0.098, green: 0.098, blue: 0.137)

    static let fg = Color(red: 0.957, green: 0.945, blue: 0.910)
    static let muted = Color(red: 0.635, green: 0.616, blue: 0.573)
    static let subtle = Color(red: 0.447, green: 0.435, blue: 0.404)

    // Or champagne — signature visuelle de Prophet
    static let gold = Color(red: 0.851, green: 0.702, blue: 0.420)
    static let goldSoft = Color(red: 0.949, green: 0.867, blue: 0.686)
    static let accentFg = Color(red: 0.055, green: 0.043, blue: 0.020)

    static let live = Color(red: 0.878, green: 0.412, blue: 0.290)
    static let gain = Color(red: 0.506, green: 0.706, blue: 0.533)
    static let cold = Color(red: 0.435, green: 0.573, blue: 0.769)
    static let violet = Color(red: 0.478, green: 0.408, blue: 0.780)
    static let teal = Color(red: 0.263, green: 0.620, blue: 0.600)

    static let goldGradient = LinearGradient(
        colors: [goldSoft, gold],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let cardStroke = LinearGradient(
        colors: [Color.white.opacity(0.16), Color.white.opacity(0.03)],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static func kindColor(_ kind: GridKind) -> Color {
        switch kind {
        case .alpha: return live
        case .omega: return teal
        case .nexus: return gold
        }
    }
}

enum Typeface {
    // Titres : SF Pro semibold, serré — le registre des apps Apple.
    static func display(_ size: CGFloat, weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .default)
    }

    // Chiffres et données : SF Rounded avec chiffres à chasse fixe
    // (style Timer / Fitness) — stable pendant les comptes à rebours.
    static func mono(_ size: CGFloat, weight: Font.Weight = .medium) -> Font {
        Font.system(size: size, weight: weight, design: .rounded).monospacedDigit()
    }
}
