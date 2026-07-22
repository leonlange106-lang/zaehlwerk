import SwiftUI

/// TOTP-Code-Eingabe nach erfolgreichem Passwort, wenn 2FA aktiv ist.
struct TwoFactorLoginView: View {
    @Environment(AuthManager.self) private var auth
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("6-stelliger Code", text: $code)
                        .keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                } header: {
                    Text("Zwei-Faktor-Authentifizierung")
                } footer: {
                    Text("Gib den aktuellen Code aus deiner Authenticator-App ein.")
                }

                if let message = auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }

                Section {
                    Button {
                        Task { await auth.submitLoginCode(code) }
                    } label: {
                        HStack {
                            if auth.isBusy { ProgressView() }
                            Text("Bestätigen").frame(maxWidth: .infinity)
                        }
                    }
                    .disabled(auth.isBusy || code.count < 6)
                }

                Section {
                    Button("Abbrechen", role: .cancel) {
                        Task { await auth.cancelTwoFactor() }
                    }
                }
            }
            .navigationTitle("Bestätigung")
        }
    }
}
