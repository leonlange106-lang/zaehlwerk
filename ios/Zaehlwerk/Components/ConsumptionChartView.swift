import SwiftUI
import Charts

/// Verlaufsdiagramm des Tagesverbrauchs auf Basis von `ChartData`.
/// Nutzt Swift Charts, hebt Ausreißer hervor und färbt in der Systemfarbe.
struct ConsumptionChartView: View {
    let chart: ChartData
    let color: Color

    private struct Entry: Identifiable {
        let id: Int
        let date: Date
        let value: Double
        let isOutlier: Bool
    }

    private var entries: [Entry] {
        chart.perDayPoints.compactMap { point in
            guard let value = point.value,
                  let date = Self.parse(point.label) else { return nil }
            return Entry(id: point.id, date: date, value: value, isOutlier: point.isOutlier)
        }
    }

    var body: some View {
        if entries.isEmpty {
            ContentUnavailableView("Noch keine Verlaufsdaten",
                                   systemImage: "chart.xyaxis.line")
                .frame(height: 220)
        } else {
            Chart(entries) { entry in
                AreaMark(
                    x: .value("Datum", entry.date),
                    y: .value("Verbrauch", entry.value)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(
                    .linearGradient(
                        colors: [color.opacity(0.35), color.opacity(0.02)],
                        startPoint: .top, endPoint: .bottom
                    )
                )

                LineMark(
                    x: .value("Datum", entry.date),
                    y: .value("Verbrauch", entry.value)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(color)
                .lineStyle(StrokeStyle(lineWidth: 2))

                if entry.isOutlier {
                    PointMark(
                        x: .value("Datum", entry.date),
                        y: .value("Verbrauch", entry.value)
                    )
                    .foregroundStyle(.orange)
                    .symbolSize(60)
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading)
            }
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 4)) { value in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.abbreviated).year(.twoDigits))
                }
            }
            .frame(height: 220)
            .accessibilityLabel("Verlauf des Tagesverbrauchs in \(chart.unit)")
        }
    }

    /// Versucht, ein Achsen-Label als Datum zu deuten (yyyy-MM-dd oder yyyy-MM).
    private static func parse(_ label: String) -> Date? {
        for format in ["yyyy-MM-dd", "yyyy-MM"] {
            formatter.dateFormat = format
            if let date = formatter.date(from: label) { return date }
        }
        return nil
    }

    private static let formatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter
    }()
}
