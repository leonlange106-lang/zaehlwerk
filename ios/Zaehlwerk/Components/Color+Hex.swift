import SwiftUI

extension Color {
    /// Erzeugt eine Farbe aus einem Hex-String wie `#4F8EF7`, `4F8EF7` oder
    /// `#RGB`/`#RRGGBBAA`. Gibt `nil` bei ungültiger Eingabe zurück, damit der
    /// Aufrufer sauber auf eine Standardfarbe ausweichen kann.
    init?(hex: String?) {
        guard let hex else { return nil }
        var string = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if string.hasPrefix("#") { string.removeFirst() }

        // Kurzform #RGB -> #RRGGBB
        if string.count == 3 {
            string = string.map { "\($0)\($0)" }.joined()
        }

        guard let value = UInt64(string, radix: 16) else { return nil }

        let r, g, b, a: Double
        switch string.count {
        case 6:
            r = Double((value & 0xFF0000) >> 16) / 255
            g = Double((value & 0x00FF00) >> 8) / 255
            b = Double(value & 0x0000FF) / 255
            a = 1
        case 8:
            r = Double((value & 0xFF000000) >> 24) / 255
            g = Double((value & 0x00FF0000) >> 16) / 255
            b = Double((value & 0x0000FF00) >> 8) / 255
            a = Double(value & 0x000000FF) / 255
        default:
            return nil
        }
        self.init(.sRGB, red: r, green: g, blue: b, opacity: a)
    }
}
