import SwiftUI
import Charts

/// Miniatur-Verlauf für die Übersichtskarten (kein Achsen-Chrome).
struct Sparkline: View {
    let points: [SeriesPoint]
    let color: Color

    var body: some View {
        if points.count < 2 {
            EmptyView()
        } else {
            Chart(points) { point in
                LineMark(
                    x: .value("Tag", point.day),
                    y: .value("Wert", point.value)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(color)
                .lineStyle(StrokeStyle(lineWidth: 1.5))

                AreaMark(
                    x: .value("Tag", point.day),
                    y: .value("Wert", point.value)
                )
                .interpolationMethod(.monotone)
                .foregroundStyle(
                    .linearGradient(
                        colors: [color.opacity(0.25), color.opacity(0.0)],
                        startPoint: .top, endPoint: .bottom
                    )
                )
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .frame(height: 40)
            .accessibilityHidden(true)
        }
    }
}
