import SwiftUI

enum Palette {
    static let bg = Color(red: 0.031, green: 0.031, blue: 0.047)
    static let surface = Color(red: 0.071, green: 0.071, blue: 0.094)
    static let elevated = Color(red: 0.106, green: 0.106, blue: 0.133)
    static let fg = Color(red: 0.953, green: 0.945, blue: 0.918)
    static let muted = Color(red: 0.604, green: 0.596, blue: 0.565)
    static let subtle = Color(red: 0.431, green: 0.424, blue: 0.400)
    static let accent = Color(red: 0.773, green: 0.804, blue: 0.847)
    static let accentFg = Color(red: 0.031, green: 0.031, blue: 0.047)
    static let live = Color(red: 0.769, green: 0.361, blue: 0.290)
    static let gain = Color(red: 0.561, green: 0.647, blue: 0.549)
    static let warn = Color(red: 0.769, green: 0.647, blue: 0.455)
}

enum Typeface {
    static func display(_ size: CGFloat) -> Font {
        .system(size: size, weight: .regular, design: .serif)
    }

    static func mono(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}
