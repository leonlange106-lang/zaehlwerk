import SwiftUI

/// Wurzel der angemeldeten App: drei Tabs im Stil einer Apple-Systemapp.
/// Ersetzt die frühere Platzhalter-Ansicht aus Schritt 1.
struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Übersicht", systemImage: "square.grid.2x2") }

            HistoryView()
                .tabItem { Label("Verlauf", systemImage: "clock.arrow.circlepath") }

            SettingsView()
                .tabItem { Label("Einstellungen", systemImage: "gearshape") }
        }
    }
}
