import SwiftUI

/// Dezenter Hinweis, dass gerade zwischengespeicherte (Offline-)Daten gezeigt
/// werden, samt Zeitpunkt der letzten erfolgreichen Aktualisierung.
struct CacheStatusBar: View {
    let isShowingCached: Bool
    let lastUpdated: Date?

    var body: some View {
        if isShowingCached {
            HStack(spacing: 8) {
                Image(systemName: "wifi.slash")
                    .font(.caption)
                Text("Offline – Stand \(Format.relative(lastUpdated))")
                    .font(.caption)
                Spacer()
            }
            .foregroundStyle(.secondary)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(.thinMaterial)
            .clipShape(Capsule())
            .padding(.horizontal)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Offline. Daten vom Stand \(Format.relative(lastUpdated)).")
        }
    }
}
