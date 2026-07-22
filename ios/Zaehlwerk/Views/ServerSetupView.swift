import SwiftUI

/// Erste Ansicht, wenn noch keine Server-Adresse hinterlegt ist.
/// Bewusst schlank gehalten (Schritt 1): sie prüft die Netzwerk-/Auth-Schicht,
/// die HIG-konforme Endfassung folgt in einem späteren Schritt.
struct ServerSetupView: View {
    @Environment(AuthManager.self) private var auth
    @State private var urlString = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://zaehlwerk.example.com", text: $urlString)
                        .textContentType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                } header: {
                    Text("Server-Adresse")
                } footer: {
                    Text("Vollständige Basis-Adresse deiner Zählwerk-Instanz, inkl. https://.")
                }

                if let message = auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }

                Section {
                    Button {
                        auth.configureServer(urlString)
                        Task { await auth.bootstrap() }
                    } label: {
                        Text("Verbinden")
                            .frame(maxWidth: .infinity)
                    }
                    .disabled(urlString.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
            .navigationTitle("Zählwerk")
            .onAppear { urlString = auth.serverURLString }
        }
    }
}
