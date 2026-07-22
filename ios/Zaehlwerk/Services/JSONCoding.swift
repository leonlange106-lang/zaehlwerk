import Foundation

/// Zentrale JSON-Konfiguration. Das Backend liefert Datumsfelder in mehreren
/// Formen: ISO-Zeitstempel mit/ohne Sekundenbruchteile und mit/ohne Zeitzone
/// (naive `datetime.utcnow()`), sowie reine Tagesdaten `yyyy-MM-dd`. Die
/// Decoder-Strategie probiert die Varianten der Reihe nach durch.
enum JSONCoding {
    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let raw = try container.decode(String.self)
            if let date = parseDate(raw) { return date }
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "Unlesbares Datum: \(raw)")
        }
        return decoder
    }()

    static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        // Anfrage-Modelle formatieren Datumsfelder selbst als String – hier
        // ist keine Datumsstrategie nötig.
        return encoder
    }()

    // MARK: - Datumsparser

    private static let isoWithFraction: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoPlain: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    /// Naive (zeitzonenlose) `datetime`-Werte des Backends, z. B.
    /// `2026-07-21T20:47:09.149429`. Als UTC interpretiert.
    private static func makeNaiveFormatter(_ format: String) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = format
        return formatter
    }

    private static let naiveWithFraction = makeNaiveFormatter("yyyy-MM-dd'T'HH:mm:ss.SSSSSS")
    private static let naiveNoFraction = makeNaiveFormatter("yyyy-MM-dd'T'HH:mm:ss")
    private static let dayOnly = makeNaiveFormatter("yyyy-MM-dd")

    static func parseDate(_ raw: String) -> Date? {
        if raw.contains("+") || raw.hasSuffix("Z") {
            if let date = isoWithFraction.date(from: raw) { return date }
            if let date = isoPlain.date(from: raw) { return date }
        }
        if let date = naiveWithFraction.date(from: raw) { return date }
        if let date = naiveNoFraction.date(from: raw) { return date }
        if let date = dayOnly.date(from: raw) { return date }
        return nil
    }
}
