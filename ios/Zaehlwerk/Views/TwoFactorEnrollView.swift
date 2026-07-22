import SwiftUI

/// Sheet zum nachträglichen Aktivieren der Zwei-Faktor-Authentifizierung
/// aus den Einstellungen. Nutzt dieselben AuthManager-Aufrufe wie das
/// Onboarding (`setupTwoFactor` + `verifyTwoFactor`).
struct TwoFactorEnrollView: View {
    @Environment(AuthManager.self) private var auth
    @Environment(\.dismiss) private var dismiss

    @State private var setup: TwoFactorSetup?
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if let setup {
                        if let image = Self.qrImage(from: setup.qrDataURI) {
                            image
                                .resizable()
                                .interpolation(.none)
                                .scaledToFit()
                                .frame(maxWidth: 220)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 8)
                        }
                        LabeledContent("Schlüssel", value: setup.secret)
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                    } else {
                        ProgressView("Richte 2FA ein …")
                            .frame(maxWidth: .infinity)
                    }
                } header: {
                    Text("Authenticator einrichten")
                } footer: {
                    Text("Scanne den QR-Code (oder gib den Schlüssel manuell ein) in deiner Authenticator-App und bestätige mit dem erzeugten Code.")
                }

                Section {
                    TextField("6-stelliger Code", text: $code)
                        .keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                }

                if let message = auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Zwei-Faktor")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Aktivieren") {
                        Task {
                            if await auth.verifyTwoFactor(code: code) { dismiss() }
                        }
                    }
                    .disabled(setup == nil || code.count < 6 || auth.isBusy)
                }
            }
            .task {
                if setup == nil { setup = await auth.setupTwoFactor() }
            }
        }
    }

    /// Data-URI (`data:image/...;base64,...`) -> `Image`. Bei SVG-Inhalt schlägt
    /// die Bild-Dekodierung fehl; dann greift die manuelle Schlüsseleingabe.
    static func qrImage(from dataURI: String) -> Image? {
        guard let commaIndex = dataURI.firstIndex(of: ","),
              dataURI.lowercased().contains("base64") else { return nil }
        let base64 = String(dataURI[dataURI.index(after: commaIndex)...])
        guard let data = Data(base64Encoded: base64),
              let uiImage = UIImage(data: data) else { return nil }
        return Image(uiImage: uiImage)
    }
}
