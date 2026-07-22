import Foundation

/// Einheitliche, lokalisierte Formatierung von Zahlen, Werten, Kosten und Daten.
/// Deutschsprachig (Dezimalkomma, €), damit alle Screens identisch aussehen.
enum Format {
    private static let numberFormatter: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.numberStyle = .decimal
        formatter.groupingSeparator = "."
        formatter.decimalSeparator = ","
        return formatter
    }()

    private static let currencyFormatter: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.numberStyle = .currency
        formatter.currencyCode = "EUR"
        return formatter
    }()

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.dateFormat = "dd.MM.yyyy"
        return formatter
    }()

    private static let monthFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.setLocalizedDateFormatFromTemplate("MMM yyyy")
        return formatter
    }()

    /// Reine Zahl mit fester Nachkommastellen-Zahl. `nil` -> "–".
    static func number(_ value: Double?, fraction: Int = 1) -> String {
        guard let value else { return "–" }
        numberFormatter.minimumFractionDigits = fraction
        numberFormatter.maximumFractionDigits = fraction
        return numberFormatter.string(from: NSNumber(value: value)) ?? "–"
    }

    /// Wert mit Einheit, z. B. „1.234,5 kWh".
    static func value(_ value: Double?, unit: String, fraction: Int = 1) -> String {
        guard value != nil else { return "–" }
        return "\(number(value, fraction: fraction)) \(unit)"
    }

    /// Betrag in Euro. `nil` -> "–".
    static func cost(_ value: Double?) -> String {
        guard let value else { return "–" }
        return currencyFormatter.string(from: NSNumber(value: value)) ?? "–"
    }

    /// Tagesdatum „dd.MM.yyyy". `nil` -> "–".
    static func date(_ date: Date?) -> String {
        guard let date else { return "–" }
        return dayFormatter.string(from: date)
    }

    static func month(_ date: Date?) -> String {
        guard let date else { return "–" }
        return monthFormatter.string(from: date)
    }

    private static let relativeFormatter: RelativeDateTimeFormatter = {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "de_DE")
        formatter.unitsStyle = .full
        return formatter
    }()

    /// Relativer Zeitpunkt, z. B. „vor 5 Minuten". `nil` -> "–".
    static func relative(_ date: Date?) -> String {
        guard let date else { return "–" }
        return relativeFormatter.localizedString(for: date, relativeTo: Date())
    }
}
