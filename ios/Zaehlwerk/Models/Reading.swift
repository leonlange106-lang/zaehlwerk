import Foundation

/// Eine Ablesung mit vom Backend abgeleiteten Kennzahlen. Spiegel von `ReadingRead`.
public struct Reading: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let systemID: String
    public let date: Date
    public let value: Double
    public let cost: Double?
    public let meterReplaced: Bool
    public let meterStart: Double?
    public let note: String?
    public let source: String                 // "manual" | "ha_api" | "mqtt" | "import"

    // Abgeleitete Felder
    public let consumption: Double?
    public let consumptionPerDay: Double?
    public let isOutlier: Bool
    public let costEffective: Double?
    public let costEstimated: Bool

    enum CodingKeys: String, CodingKey {
        case id, value, cost, note, source, consumption
        case systemID = "system_id"
        case date = "datum"
        case meterReplaced = "meter_replaced"
        case meterStart = "meter_start"
        case consumptionPerDay = "consumption_per_day"
        case isOutlier = "is_outlier"
        case costEffective = "cost_effective"
        case costEstimated = "cost_estimated"
    }
}

/// Anfrage-Körper für `POST /api/systems/{id}/readings`.
/// Das Datum wird als reines Tagesdatum `yyyy-MM-dd` gesendet.
struct ReadingCreateRequest: Encodable {
    let datum: String
    let value: Double
    let cost: Double?
    let meter_replaced: Bool
    let meter_start: Double?
    let note: String?
    let source: String

    init(date: Date, value: Double, cost: Double? = nil,
         meterReplaced: Bool = false, meterStart: Double? = nil,
         note: String? = nil, source: String = "manual") {
        self.datum = ReadingCreateRequest.dayFormatter.string(from: date)
        self.value = value
        self.cost = cost
        self.meter_replaced = meterReplaced
        self.meter_start = meterStart
        self.note = note
        self.source = source
    }

    static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
}
