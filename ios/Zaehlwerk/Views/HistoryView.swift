import SwiftUI

/// Verlauf: die zuletzt erfassten Ablesungen über alle Systeme hinweg.
struct HistoryView: View {
    @State private var model = DashboardViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if model.isLoading {
                    ProgressView().frame(maxWidth: .infinity, minHeight: 240)
                } else if let message = model.errorMessage, model.recent.isEmpty {
                    ErrorState(message: message) { Task { await model.load() } }
                } else if model.recent.isEmpty {
                    ContentUnavailableView(
                        "Kein Verlauf",
                        systemImage: "clock.arrow.circlepath",
                        description: Text("Sobald Ablesungen erfasst wurden, erscheinen sie hier.")
                    )
                } else {
                    List(model.recent) { reading in
                        RecentRow(reading: reading)
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("Verlauf")
            .refreshable { await model.refresh() }
            .task { await model.load() }
            .safeAreaInset(edge: .top, spacing: 0) {
                CacheStatusBar(isShowingCached: model.isShowingCached,
                               lastUpdated: model.lastUpdated)
            }
        }
    }
}

private struct RecentRow: View {
    let reading: RecentReading

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(SystemStyle.color(reading.colorHex))
                .frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text(reading.systemName)
                    .font(.body.weight(.medium))
                Text(Format.date(reading.date))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(Format.value(reading.value, unit: reading.unit))
                .font(.subheadline.weight(.semibold))
                .monospacedDigit()
        }
        .padding(.vertical, 2)
    }
}
