import SwiftUI

/// Einstellungen: Konto, Sicherheit (2FA, Passwort), Verbindung, Abmelden.
struct SettingsView: View {
    @Environment(AuthManager.self) private var auth
    @State private var showingPasswordSheet = false
    @State private var showingTwoFactorSheet = false
    @State private var showingTwoFactorDisable = false
    @State private var showingLogoutConfirm = false
    @State private var dbModel = DatabaseSelectorViewModel()
    @State private var appVersion: String?

    var body: some View {
        NavigationStack {
            List {
                accountSection
                databaseSection
                adminSection
                securitySection
                connectionSection
                infoSection
                logoutSection
            }
            .task {
                await dbModel.load()
                appVersion = try? await APIClient.shared.fetchChangelog().current
            }
            .listStyle(.insetGrouped)
            .navigationTitle("Einstellungen")
            .sheet(isPresented: $showingPasswordSheet) { ChangePasswordView() }
            .sheet(isPresented: $showingTwoFactorSheet) { TwoFactorEnrollView() }
            .sheet(isPresented: $showingTwoFactorDisable) { TwoFactorDisableView() }
            .confirmationDialog("Wirklich abmelden?", isPresented: $showingLogoutConfirm,
                                titleVisibility: .visible) {
                Button("Abmelden", role: .destructive) { Task { await auth.logout() } }
                Button("Abbrechen", role: .cancel) {}
            }
        }
    }

    // MARK: - Konto

    @ViewBuilder
    private var accountSection: some View {
        if let user = auth.user {
            Section("Konto") {
                LabeledContent("Name", value: user.displayName)
                LabeledContent("Benutzername", value: user.username)
                LabeledContent("Rolle", value: user.role.capitalized)
                LabeledContent("Quelle",
                               value: user.source == "homeassistant" ? "Home Assistant" : "Lokal")
            }
        }
    }

    // MARK: - Datenbank (Multi-DB-Kontext)

    @ViewBuilder
    private var databaseSection: some View {
        if dbModel.hasChoice {
            Section {
                NavigationLink {
                    DatabaseSelectorView()
                } label: {
                    LabeledContent("Aktive Datenbank",
                                   value: dbModel.activeName ?? "Standard")
                }
            } header: {
                Text("Datenbank")
            } footer: {
                Text("Wechsle zwischen den Datenbanken, auf die du Zugriff hast.")
            }
        }
    }

    // MARK: - Administration (nur für Admins)

    @ViewBuilder
    private var adminSection: some View {
        if auth.isAdmin {
            Section("Administration") {
                NavigationLink {
                    AdminConsoleView()
                } label: {
                    Label("Admin-Console", systemImage: "person.2.badge.gearshape")
                }
            }
        }
    }

    // MARK: - Sicherheit

    private var securitySection: some View {
        Section("Sicherheit") {
            HStack {
                Label("Zwei-Faktor", systemImage: "lock.shield")
                Spacer()
                if auth.user?.twoFactorEnabled == true {
                    Label("Aktiv", systemImage: "checkmark.circle.fill")
                        .labelStyle(.titleAndIcon)
                        .foregroundStyle(.green)
                        .font(.subheadline)
                } else {
                    Button("Aktivieren") {
                        Haptics.tap()
                        showingTwoFactorSheet = true
                    }
                }
            }
            if auth.user?.twoFactorEnabled == true {
                Button(role: .destructive) {
                    Haptics.tap()
                    showingTwoFactorDisable = true
                } label: {
                    Label("Zwei-Faktor deaktivieren", systemImage: "lock.open")
                }
            }
            Button {
                Haptics.tap()
                showingPasswordSheet = true
            } label: {
                Label("Passwort ändern", systemImage: "key")
            }
        }
    }

    // MARK: - Info / Versionsverlauf

    private var infoSection: some View {
        Section("Info") {
            NavigationLink {
                ChangelogView()
            } label: {
                LabeledContent("Version", value: appVersion.map { "v\($0)" } ?? "…")
            }
        }
    }

    // MARK: - Verbindung

    private var connectionSection: some View {
        Section {
            LabeledContent("Server") {
                Text(auth.serverURLString)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
        } header: {
            Text("Verbindung")
        } footer: {
            Text("Zählwerk – nativer Client. Anmeldung über zw_session-Token, sicher im Schlüsselbund abgelegt.")
        }
    }

    private var logoutSection: some View {
        Section {
            Button(role: .destructive) {
                showingLogoutConfirm = true
            } label: {
                Label("Abmelden", systemImage: "rectangle.portrait.and.arrow.right")
                    .frame(maxWidth: .infinity)
            }
        }
    }
}

/// Versionsverlauf des verbundenen Servers.
private struct ChangelogView: View {
    @State private var response: ChangelogResponse?
    @State private var error: String?

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(.red)
            } else if let response {
                ForEach(response.entries) { entry in
                    Section {
                        Text(entry.title).font(.headline)
                        ForEach(entry.changes, id: \.self) { change in
                            Label(change, systemImage: "checkmark.circle")
                                .labelStyle(.titleAndIcon)
                                .font(.subheadline)
                        }
                    } header: {
                        HStack {
                            Text("v\(entry.version)")
                            if entry.version == response.current {
                                Text("aktuell").font(.caption2)
                                    .padding(.horizontal, 6).padding(.vertical, 2)
                                    .background(.tint.opacity(0.15), in: Capsule())
                            }
                            Spacer()
                            Text(entry.date).foregroundStyle(.secondary)
                        }
                    }
                }
            } else {
                ProgressView()
            }
        }
        .navigationTitle("Versionsverlauf")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            do { response = try await APIClient.shared.fetchChangelog() }
            catch { self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription }
        }
    }
}

/// Sheet zum Deaktivieren der Zwei-Faktor-Authentisierung (Passwort + Code).
private struct TwoFactorDisableView: View {
    @Environment(AuthManager.self) private var auth
    @Environment(\.dismiss) private var dismiss
    @State private var password = ""
    @State private var code = ""
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Passwort", text: $password)
                    TextField("6-stelliger Code", text: $code)
                        .keyboardType(.numberPad)
                } footer: {
                    Text("Zur Bestätigung Passwort und aktuellen Authenticator-Code eingeben.")
                }
                if let error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Zwei-Faktor deaktivieren")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Abbrechen") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Deaktivieren") {
                        busy = true; error = nil
                        Task {
                            do {
                                _ = try await APIClient.shared.disableTwoFactor(password: password, code: code)
                                await auth.refreshStatus()
                                Haptics.success()
                                dismiss()
                            } catch {
                                self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
                                Haptics.error()
                            }
                            busy = false
                        }
                    }
                    .disabled(password.isEmpty || code.count < 6 || busy)
                }
            }
        }
    }
}

/// Sheet zum Ändern des eigenen Passworts.
private struct ChangePasswordView: View {
    @Environment(AuthManager.self) private var auth
    @Environment(\.dismiss) private var dismiss

    @State private var current = ""
    @State private var newPassword = ""
    @State private var confirm = ""
    @State private var localError: String?

    private var isValid: Bool {
        !current.isEmpty && newPassword.count >= 1 && newPassword == confirm
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Aktuelles Passwort", text: $current)
                    SecureField("Neues Passwort", text: $newPassword)
                    SecureField("Neues Passwort bestätigen", text: $confirm)
                }
                if let message = localError ?? auth.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Passwort ändern")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Sichern") {
                        localError = nil
                        guard newPassword == confirm else {
                            localError = "Die Passwörter stimmen nicht überein."
                            return
                        }
                        Task {
                            if await auth.changePassword(current: current, new: newPassword) {
                                dismiss()
                            }
                        }
                    }
                    .disabled(!isValid || auth.isBusy)
                }
            }
        }
    }
}
