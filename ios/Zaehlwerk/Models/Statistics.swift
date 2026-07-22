import Foundation

/// Kennzahlen eines Systems über einen Zeitraum. Spiegel von `StatsRead`.
public struct SystemStats: Codable, Hashable, Sendable {
    public let totalConsumption: Double
    public let totalCost: Double
    public let totalDays: Double
    public let avgPerDay: Double?
    public let costPerDay: Double?
    public let costPerUnit: Double?
    public let minPerDay: Double?
    public let maxPerDay: Double?
    public let totalCostTariff: Double?
    public let avgPriceEffective: Double?
    public let coverageRatio: Double

    enum CodingKeys: String, CodingKey {
        case totalConsumption = "total_consumption"
        case totalCost = "total_cost"
        case totalDays = "total_days"
        case avgPerDay = "avg_per_day"
        case costPerDay = "cost_per_day"
        case costPerUnit = "cost_per_unit"
        case minPerDay = "min_per_day"
        case maxPerDay = "max_per_day"
        case totalCostTariff = "total_cost_tariff"
        case avgPriceEffective = "avg_price_effective"
        case coverageRatio = "coverage_ratio"
    }
}

/// Zeitreihen für Diagramme. Spiegel von `ChartData`. Die Arrays sind
/// gleich lang und parallel zu `labels` indexiert.
public struct ChartData: Codable, Hashable, Sendable {
    public let systemID: String
    public let name: String
    public let unit: String
    public let color: String
    public let labels: [String]
    public let values: [Double?]
    public let consumption: [Double?]
    public let consumptionPerDay: [Double?]
    public let outliers: [Bool]
    public let meterReplaced: [Bool]

    enum CodingKeys: String, CodingKey {
        case name, unit, color, labels, values, consumption, outliers
        case systemID = "system_id"
        case consumptionPerDay = "consumption_per_day"
        case meterReplaced = "meter_replaced"
    }

    /// Gepaarte Punkte für SwiftUI-Charts (Label + Tagesverbrauch).
    public struct Point: Identifiable, Hashable, Sendable {
        public let id: Int
        public let label: String
        public let value: Double?
        public let isOutlier: Bool
    }

    public var perDayPoints: [Point] {
        labels.indices.map { index in
            Point(id: index,
                  label: labels[index],
                  value: index < consumptionPerDay.count ? consumptionPerDay[index] : nil,
                  isOutlier: index < outliers.count ? outliers[index] : false)
        }
    }
}
