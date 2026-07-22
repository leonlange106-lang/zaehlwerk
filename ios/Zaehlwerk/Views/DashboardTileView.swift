import SwiftUI
import Charts

/// Rendert eine einzelne Dashboard-Kachel anhand ihres Typs. Native Parität
/// zum Web-TileBody.
struct DashboardTileView: View {
    let tile: DashboardTile
    let data: DashboardData

    private var systems: [DashboardSystem] {
        let ids = tile.resolvedSystemIDs()
        let map = Dictionary(uniqueKeysWithValues: data.systems.map { ($0.id, $0) })
        if ids.isEmpty { return [] }
        return ids.compactMap { map[$0] }
    }

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(tile.title?.isEmpty == false ? tile.title! : tile.type.label)
                    .font(.caption).foregroundStyle(.secondary)
                    .textCase(.uppercase)
                content
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @ViewBuilder private var content: some View {
        switch tile.type {
        case .latestReading: latestReading
        case .lineChart: lineChart
        case .pieChart: pieChart
        case .costSummary: costSummary
        case .trend: trend
        case .costForecast: costForecast
        }
    }

    private func empty(_ text: String) -> some View {
        Text(text).font(.subheadline).foregroundStyle(.secondary)
    }

    // MARK: - Typen

    @ViewBuilder private var latestReading: some View {
        if let s = systems.first {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Circle().fill(SystemStyle.color(s.colorHex)).frame(width: 8, height: 8)
                    Text(s.name).font(.subheadline.weight(.semibold))
                }
                Text(Format.value(s.latest, unit: s.unit))
                    .font(.system(.title, design: .rounded).weight(.bold))
                Text("Stand \(Format.date(s.latestDate)) · Ø \(Format.value(s.avgPerDay, unit: s.unit))/Tag")
                    .font(.caption).foregroundStyle(.secondary)
            }
        } else { empty("Kein System zugeordnet") }
    }

    @ViewBuilder private var lineChart: some View {
        let list = systems.isEmpty ? Array(data.systems.prefix(1)) : systems
        if list.isEmpty {
            empty("Keine Daten")
        } else {
            Chart {
                ForEach(list) { s in
                    ForEach(filtered(s.series)) { p in
                        LineMark(x: .value("Tag", p.day), y: .value("Wert", p.value))
                            .foregroundStyle(SystemStyle.color(s.colorHex))
                            .interpolationMethod(.monotone)
                    }
                }
            }
            .chartXAxis(.hidden)
            .frame(height: 160)
        }
    }

    @ViewBuilder private var pieChart: some View {
        let list = (systems.isEmpty ? data.systems : systems)
            .filter { ($0.totalCostTariff ?? $0.totalCost ?? 0) > 0 }
        if list.isEmpty {
            empty("Keine Kostendaten")
        } else {
            Chart(list) { s in
                SectorMark(angle: .value("Kosten", s.totalCostTariff ?? s.totalCost ?? 0),
                           innerRadius: .ratio(0.55), angularInset: 1.5)
                    .foregroundStyle(SystemStyle.color(s.colorHex))
            }
            .frame(height: 160)
        }
    }

    @ViewBuilder private var costSummary: some View {
        let list = systems.isEmpty ? data.systems : systems
        let total = list.reduce(0.0) { $0 + ($1.totalCostTariff ?? $1.totalCost ?? 0) }
        VStack(alignment: .leading, spacing: 6) {
            Text(Format.cost(total)).font(.system(.title, design: .rounded).weight(.bold))
            ForEach(list.prefix(5)) { s in
                HStack {
                    Circle().fill(SystemStyle.color(s.colorHex)).frame(width: 7, height: 7)
                    Text(s.name).font(.caption)
                    Spacer()
                    Text(Format.cost(s.totalCostTariff ?? s.totalCost)).font(.caption).foregroundStyle(.secondary)
                }
            }
        }
    }

    @ViewBuilder private var trend: some View {
        if let s = systems.first {
            let series = filtered(s.series)
            let first = series.first(where: { $0.value != 0 })?.value
            let last = series.last?.value
            let delta: Double? = {
                guard let f = first, let l = last, f != 0 else { return nil }
                return (l - f) / abs(f) * 100
            }()
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(s.name).font(.subheadline.weight(.semibold))
                    if let d = delta {
                        Text("\(d > 0 ? "+" : "")\(Format.number(d)) %")
                            .font(.caption.weight(.medium))
                            .foregroundStyle(d > 1 ? .orange : d < -1 ? .green : .secondary)
                    }
                }
                Sparkline(points: series, color: SystemStyle.color(s.colorHex))
            }
        } else { empty("Kein System zugeordnet") }
    }

    @ViewBuilder private var costForecast: some View {
        let s = systems.first ?? data.systems.first
        if let s, let p = s.prognosis {
            VStack(alignment: .leading, spacing: 4) {
                Text(s.name).font(.subheadline.weight(.semibold))
                Text(Format.cost(p.projectedCost)).font(.system(.title2, design: .rounded).weight(.bold))
                Text("Hochrechnung · \(Format.value(p.projectedConsumption, unit: s.unit))")
                    .font(.caption).foregroundStyle(.secondary)
                if let annual = p.abschlagAnnual {
                    let over = p.exceedsAbschlag ?? false
                    Text("\(over ? "über" : "im") Abschlag (\(Format.cost(annual)))")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(over ? .orange : .green)
                }
            }
        } else { empty("Keine Prognose verfügbar") }
    }

    // MARK: - Zeitfenster

    private func filtered(_ series: [SeriesPoint]) -> [SeriesPoint] {
        guard tile.timeframe != .all, !series.isEmpty else { return series }
        let cal = Calendar.current
        let now = Date()
        let from: Date? = {
            switch tile.timeframe {
            case .d7: return cal.date(byAdding: .day, value: -7, to: now)
            case .d30: return cal.date(byAdding: .day, value: -30, to: now)
            case .d90: return cal.date(byAdding: .day, value: -90, to: now)
            case .ytd: return cal.date(from: cal.dateComponents([.year], from: now))
            case .m12: return cal.date(byAdding: .month, value: -12, to: now)
            default: return nil
            }
        }()
        guard let from else { return series }
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.dateFormat = "yyyy-MM-dd"
        return series.filter { point in
            guard let d = fmt.date(from: point.day) else { return true }
            return d >= from
        }
    }
}
