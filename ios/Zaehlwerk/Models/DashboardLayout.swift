import Foundation

/// Kacheltyp einer Dashboard-Kachel. Rohwerte spiegeln den Backend-Contract.
public enum TileType: String, Codable, CaseIterable, Sendable {
    case latestReading = "latest_reading"
    case lineChart = "line_chart"
    case pieChart = "pie_chart"
    case costSummary = "cost_summary"
    case trend
    case costForecast = "cost_forecast"

    var label: String {
        switch self {
        case .latestReading: return "Aktueller Stand"
        case .lineChart: return "Verlaufsdiagramm"
        case .pieChart: return "Kostenverteilung"
        case .costSummary: return "Kostenübersicht"
        case .trend: return "Trend"
        case .costForecast: return "Kostenprognose"
        }
    }

    var symbol: String {
        switch self {
        case .latestReading: return "gauge.medium"
        case .lineChart: return "chart.xyaxis.line"
        case .pieChart: return "chart.pie"
        case .costSummary: return "eurosign.circle"
        case .trend: return "chart.line.uptrend.xyaxis"
        case .costForecast: return "chart.line.flattrend.xyaxis"
        }
    }

    /// Kacheln, die mehrere Systeme aufnehmen können.
    var allowsMultiple: Bool {
        self == .lineChart || self == .pieChart || self == .costSummary
    }
}

public enum Timeframe: String, Codable, CaseIterable, Sendable {
    case d7 = "7d", d30 = "30d", d90 = "90d", ytd, m12 = "12m", all, custom

    var label: String {
        switch self {
        case .d7: return "7 Tage"
        case .d30: return "30 Tage"
        case .d90: return "90 Tage"
        case .ytd: return "Lfd. Jahr"
        case .m12: return "12 Monate"
        case .all: return "Gesamt"
        case .custom: return "Zeitraum"
        }
    }
}

/// Eine Dashboard-Kachel. Spiegel von `DashboardTile` im Backend.
public struct DashboardTile: Codable, Identifiable, Hashable, Sendable {
    public var id: String
    public var type: TileType
    public var x: Int
    public var y: Int
    public var w: Int
    public var h: Int
    public var systemID: String?
    public var systemIDs: [String]
    public var timeframe: Timeframe
    public var title: String?

    enum CodingKeys: String, CodingKey {
        case id, type, x, y, w, h, timeframe, title
        case systemID = "system_id"
        case systemIDs = "system_ids"
    }

    public init(id: String, type: TileType, x: Int = 0, y: Int = 0, w: Int = 1, h: Int = 1,
                systemID: String? = nil, systemIDs: [String] = [],
                timeframe: Timeframe = .m12, title: String? = nil) {
        self.id = id; self.type = type; self.x = x; self.y = y; self.w = w; self.h = h
        self.systemID = systemID; self.systemIDs = systemIDs; self.timeframe = timeframe; self.title = title
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        type = try c.decode(TileType.self, forKey: .type)
        x = (try? c.decode(Int.self, forKey: .x)) ?? 0
        y = (try? c.decode(Int.self, forKey: .y)) ?? 0
        w = (try? c.decode(Int.self, forKey: .w)) ?? 1
        h = (try? c.decode(Int.self, forKey: .h)) ?? 1
        systemID = try? c.decodeIfPresent(String.self, forKey: .systemID)
        systemIDs = (try? c.decode([String].self, forKey: .systemIDs)) ?? []
        timeframe = (try? c.decode(Timeframe.self, forKey: .timeframe)) ?? .m12
        title = try? c.decodeIfPresent(String.self, forKey: .title)
    }

    /// Die zugeordneten Systeme (system_ids hat Vorrang, sonst system_id).
    func resolvedSystemIDs() -> [String] {
        if !systemIDs.isEmpty { return systemIDs }
        if let id = systemID { return [id] }
        return []
    }
}

public struct DashboardLayoutResponse: Codable, Sendable {
    public let tiles: [DashboardTile]
    public let isDefault: Bool

    enum CodingKeys: String, CodingKey {
        case tiles
        case isDefault = "is_default"
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        tiles = try c.decode([DashboardTile].self, forKey: .tiles)
        // Die PUT-Antwort liefert nur {tiles, saved}, kein is_default.
        isDefault = (try? c.decode(Bool.self, forKey: .isDefault)) ?? false
    }
}

/// PUT-Körper für das Speichern des Layouts.
struct DashboardLayoutRequest: Encodable {
    let tiles: [DashboardTile]
}
