import SwiftUI

/// Erzwungene Erstanmeldung: zuerst Passwortwechsel, danach 2FA einrichten.
/// Nach erfolgreicher 2FA-Aktivierung aktualisiert `refreshStatus()` die Phase
/// automatisch auf `.authenticated`.
struct OnboardingView: View {
    @Environment(AuthManager.self) private var auth

    private enum Step { case password, twoFactor }
    @State private var step: Step = .password

    // Passwort-Schritt
    @State private var current = ""
    @State private var newPassword = ""
    @State private var confirm = ""

    // 2FA-Schritt
    @State private var setup: TwoFactorSetup?
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                switch step {
                case .password:  passwordSection
                case .twoFactor: twoFactorSection
                }

                if let message = auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Einrichtung")
        }
    }

    // MARK: - Schritt 1: Passwort

    @ViewBuilder
    private var passwordSection: some View {
        Section {
            SecureField("Aktuelles (temporäres) Passwort", text: $current)
            SecureField("Neues Passwort", text: $newPassword)
            SecureField("Neues Passwort bestätigen", text: $confirm)
        } header: {
            Text("Passwort festlegen")
        } footer: {
            Text("Aus Sicherheitsgründen musst du bei der Erstanmeldung ein eigenes Passwort vergeben.")
        }

        Section {
            Button {
                Task {
                    let ok = await auth.changePassword(current: current, new: newPassword)
                    if ok { step = .twoFactor }
                }
            } label: {
                HStack {
                    if auth.isBusy { ProgressView() }
                    Text("Weiter").frame(maxWidth: .infinity)
                }
            }
            .disabled(auth.isBusy || newPassword.isEmpty || newPassword != confirm || current.isEmpty)
        }
    }

    // MARK: - Schritt 2: 2FA

    @ViewBuilder
    private var twoFactorSection: some View {
        Section {
            if let setup {
                if let image = qrImage(from: setup.qrDataURI) {
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
            }
        } header: {
            Text("Zwei-Faktor-Authentifizierung")
        } footer: {
            Text("Scanne den QR-Code mit deiner Authenticator-App und gib anschließend den erzeugten Code ein.")
        }

        Section {
            TextField("6-stelliger Code", text: $code)
                .keyboardType(.numberPad)
                .textContentType(.oneTimeCode)
            Button {
                Task { _ = await auth.verifyTwoFactor(code: code) }
            } label: {
                HStack {
                    if auth.isBusy { ProgressView() }
                    Text("Aktivieren & Fertig").frame(maxWidth: .infinity)
                }
            }
            .disabled(auth.isBusy || setup == nil || code.count < 6)
        }
        .task {
            if setup == nil { setup = await auth.setupTwoFactor() }
        }
    }

    /// Wandelt eine Data-URI (`data:image/...;base64,...`) in ein `Image`.
    private func qrImage(from dataURI: String) -> Image? {
        guard let commaIndex = dataURI.firstIndex(of: ",") else { return nil }
        let base64 = String(dataURI[dataURI.index(after: commaIndex)...])
        guard let data = Data(base64Encoded: base64),
              let uiImage = UIImage(data: data) else { return nil }
        return Image(uiImage: uiImage)
    }
}
