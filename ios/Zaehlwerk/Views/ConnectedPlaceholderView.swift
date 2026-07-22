import SwiftUI

/// Authentifizierte Platzhalter-Ansicht (Schritt 1).
/// Sie lädt die echten Systeme über die API und beweist damit, dass Netzwerk-,
/// Auth- und Decoding-Schicht end-to-end funktionieren. Dashboard, Detail,
/// Eingabe und Einstellungen ersetzen diese Ansicht in den nächsten Schritten.
struct ConnectedPlaceholderView: View {
    @Environment(AuthManager.self) private var auth

    @State private var systems: [MeterSystem] = []
    @State private var loadError: String?
    @State private var isLoading = false

    private let api = APIClient.shared

    var body: some View {
        NavigationStack {
            List {
                if let user = auth.user {
                    Section("Angemeldet") {
                        LabeledContent("Benutzer", value: user.displayName)
                        LabeledContent("Rolle", value: user.role)
                        LabeledContent("2FA", value: user.twoFactorEnabled ? "aktiv" : "inaktiv")
                    }
                }

                Section("Systeme") {
                    if isLoading {
                        ProgressView()
                    } else if let loadError {
                        Text(loadError).foregroundStyle(.red)
                    } else if systems.isEmpty {
                        Text("Keine Systeme vorhanden.").foregroundStyle(.secondary)
                    } else {
                        ForEach(systems) { system in
                            HStack {
                                Circle()
                                    .fill(Color(hex: system.colorHex) ?? .accentColor)
                                    .frame(width: 12, height: 12)
                                VStack(alignment: .leading) {
                                    Text(system.name)
                                    Text(system.type).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(system.unit).foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                Section {
                    Button("Abmelden", role: .destructive) {
                        Task { await auth.logout() }
                    }
                }
            }
            .navigationTitle("Zählwerk")
            .refreshable { await load() }
            .task { await load() }
        }
    }

    private func load() async {
        isLoading = true
        loadError = nil
        do {
            systems = try await api.fetchSystems()
        } catch let error as APIError {
            loadError = error.errorDescription
        } catch {
            loadError = error.localizedDescription
        }
        isLoading = false
    }
}
