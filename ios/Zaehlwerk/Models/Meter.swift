import Foundation

/// Zähler-Metadaten (Hersteller, Modell, Nummer, Eichfrist). Rein
/// dokumentarisch – ohne Einfluss auf die Verbrauchslogik. Spiegel von
/// `MeterRead`.
public struct Meter: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let systemID: String
    public var hersteller: String?
    public var modell: String?
    public var zaehlernummer: String?
    public var bauart: String?
    public var baujahr: Int?
    public var eichungBis: Date?
    public var messstellenbetreiber: String?
    public var stellenVor: Int?
    public var stellenNach: Int?
    public var eingebautAm: Date?
    public var ausgebautAm: Date?
    public var notiz: String?
    public let aktiv: Bool
    public let eichungFaelligInTagen: Int?
    public let eichungAbgelaufen: Bool

    enum CodingKeys: String, CodingKey {
        case id, hersteller, modell, bauart, baujahr, notiz, aktiv
        case systemID = "system_id"
        case zaehlernummer
        case eichungBis = "eichung_bis"
        case messstellenbetreiber
        case stellenVor = "stellen_vor"
        case stellenNach = "stellen_nach"
        case eingebautAm = "eingebaut_am"
        case ausgebautAm = "ausgebaut_am"
        case eichungFaelligInTagen = "eichung_faellig_in_tagen"
        case eichungAbgelaufen = "eichung_abgelaufen"
    }
}

/// Anfrage-Körper für Anlegen (POST) und Ändern (PATCH). Datumsfelder werden –
/// wie bei Ablesungen – als reines Tagesdatum `yyyy-MM-dd` gesendet.
///
/// Alle Schlüssel werden IMMER kodiert (auch als `null`), damit ein per PATCH
/// geleertes Feld tatsächlich gelöscht wird – analog zur Web-Maske, die leere
/// Felder ausdrücklich als `null` sendet.
struct MeterRequest: Encodable {
    var hersteller: String?
    var modell: String?
    var zaehlernummer: String?
    var bauart: String?
    var baujahr: Int?
    var eichung_bis: String?
    var messstellenbetreiber: String?
    var stellen_vor: Int?
    var stellen_nach: Int?
    var eingebaut_am: String?
    var ausgebaut_am: String?
    var notiz: String?

    enum CodingKeys: String, CodingKey {
        case hersteller, modell, zaehlernummer, bauart, baujahr, eichung_bis
        case messstellenbetreiber, stellen_vor, stellen_nach, eingebaut_am, ausgebaut_am, notiz
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try encodeOpt(&c, hersteller, .hersteller)
        try encodeOpt(&c, modell, .modell)
        try encodeOpt(&c, zaehlernummer, .zaehlernummer)
        try encodeOpt(&c, bauart, .bauart)
        try encodeIntOpt(&c, baujahr, .baujahr)
        try encodeOpt(&c, eichung_bis, .eichung_bis)
        try encodeOpt(&c, messstellenbetreiber, .messstellenbetreiber)
        try encodeIntOpt(&c, stellen_vor, .stellen_vor)
        try encodeIntOpt(&c, stellen_nach, .stellen_nach)
        try encodeOpt(&c, eingebaut_am, .eingebaut_am)
        try encodeOpt(&c, ausgebaut_am, .ausgebaut_am)
        try encodeOpt(&c, notiz, .notiz)
    }

    private func encodeOpt(_ c: inout KeyedEncodingContainer<CodingKeys>,
                           _ value: String?, _ key: CodingKeys) throws {
        if let value { try c.encode(value, forKey: key) } else { try c.encodeNil(forKey: key) }
    }
    private func encodeIntOpt(_ c: inout KeyedEncodingContainer<CodingKeys>,
                              _ value: Int?, _ key: CodingKeys) throws {
        if let value { try c.encode(value, forKey: key) } else { try c.encodeNil(forKey: key) }
    }

    static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    static func day(_ date: Date?) -> String? {
        guard let date else { return nil }
        return dayFormatter.string(from: date)
    }
}
