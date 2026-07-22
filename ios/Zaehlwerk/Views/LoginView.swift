import SwiftUI

/// Anmeldeformular (Benutzername + Passwort).
struct LoginView: View {
    @Environment(AuthManager.self) private var auth
    @State private var username = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Anmeldung") {
                    TextField("Benutzername", text: $username)
                        .textContentType(.username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Passwort", text: $password)
                        .textContentType(.password)
                }

                if let message = auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }

                Section {
                    Button {
                        Task { await auth.login(username: username, password: password) }
                    } label: {
                        HStack {
                            if auth.isBusy { ProgressView() }
                            Text("Anmelden").frame(maxWidth: .infinity)
                        }
                    }
                    .disabled(auth.isBusy || username.isEmpty || password.isEmpty)
                }

                Section {
                    Button("Server ändern", role: .destructive) {
                        Task { await auth.logout() }
                        auth.serverURLString = ""
                        Task { await auth.bootstrap() }
                    }
                    .font(.footnote)
                }
            }
            .navigationTitle("Zählwerk")
        }
    }
}
