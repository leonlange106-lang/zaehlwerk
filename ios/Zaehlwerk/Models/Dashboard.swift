import Foundation

/// Antwort von `GET /api/dashboard/data` – Kennzahlen aller aktiven Systeme
/// samt kompakten Verlaufsdaten und den letzten Erfassungen.
public struct DashboardData: Codable, Sendable {
    public let systems: [DashboardSystem]
    public let months: Int
    public let recent: [RecentReading]
}

public struct DashboardSystem: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let type: String
    public let unit: String
    public let colorHex: String
    public let latest: Double?
    public let latestDate: Date?
    public let totalConsumption: Double?
    public let totalCost: Double?
    public let totalCostTariff: Double?
    public let avgPerDay: Double?
    public let series: [SeriesPoint]
    public let prognosis: Prognosis?

    enum CodingKeys: String, CodingKey {
        case id, name, series, prognosis
        case type = "typ"
        case unit = "einheit"
        case colorHex = "farbe"
        case latest
        case latestDate = "latest_datum"
        case totalConsumption = "total_consumption"
        case totalCost = "total_cost"
        case totalCostTariff = "total_cost_tariff"
        case avgPerDay = "avg_per_day"
    }
}

public struct SeriesPoint: Codable, Hashable, Sendable, Identifiable {
    public let day: String
    public let value: Double
    public var id: String { day }

    enum CodingKeys: String, CodingKey {
        case day = "d"
        case value = "v"
    }
}

/// Jahresprognose (Rolling-Average). Es werden nur die vom UI genutzten Felder
/// deklariert; unbekannte Schlüssel ignoriert Codable.
public struct Prognosis: Codable, Hashable, Sendable {
    public let projectedConsumption: Double?
    public let projectedCost: Double?
    public let abschlagAnnual: Double?
    public let exceedsAbschlag: Bool?
    public let shortfall: Double?

    enum CodingKeys: String, CodingKey {
        case projectedConsumption = "projected_consumption"
        case projectedCost = "projected_cost"
        case abschlagAnnual = "abschlag_annual"
        case exceedsAbschlag = "exceeds_abschlag"
        case shortfall
    }
}

public struct RecentReading: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let systemID: String
    public let systemName: String
    public let colorHex: String?
    public let unit: String
    public let date: Date?
    public let value: Double
    public let source: String

    enum CodingKeys: String, CodingKey {
        case id, value, source
        case systemID = "system_id"
        case systemName = "system"
        case colorHex = "farbe"
        case unit = "einheit"
        case date = "datum"
    }
}
