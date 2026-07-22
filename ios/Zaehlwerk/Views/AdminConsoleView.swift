import SwiftUI

/// Native Admin-Console (TICKET-1.4): Kontostatus, Sitzungskontrolle und
/// Datenbank-Verwaltung – das Pendant zum Web-Admin-Dashboard, im HIG-Stil.
struct AdminConsoleView: View {
    @State private var model = AdminConsoleViewModel()
    @State private var panel: Panel = .accounts

    enum Panel: String, CaseIterable, Identifiable {
        case accounts = "Konten"
        case sessions = "Sitzungen"
        case databases = "Datenbanken"
        var id: String { rawValue }
    }

    var body: some View {
        List {
            Picker("Bereich", selection: $panel) {
                ForEach(Panel.allCases) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))

            if let message = model.errorMessage {
                Section { Text(message).foregroundStyle(.red) }
            }

            switch panel {
            case .accounts:  accountsSection
            case .sessions:  sessionsSection
            case .databases: databasesSection
            }
        }
        .navigationTitle("Administration")
        .navigationBarTitleDisplayMode(.large)
        .overlay { if model.isLoading { ProgressView() } }
        .refreshable { await model.load() }
        .task { await model.load() }
    }

    // MARK: - Konten

    @ViewBuilder
    private var accountsSection: some View {
        Section("Konten & Status") {
            ForEach(model.users) { u in
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(u.online ? Color.green : Color.secondary.opacity(0.4))
                            .frame(width: 9, height: 9)
                        Text(u.displayName).font(.body.weight(.medium))
                        Text(u.role).font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        if u.activeSessions > 0 {
                            Button("Abmelden", role: .destructive) {
                                Task { await model.terminateAll(user: u) }
                            }
                            .font(.caption)
                            .buttonStyle(.borderless)
                        }
                    }
                    HStack(spacing: 6) {
                        Badge(text: u.twoFactorStatus,
                              tint: u.twoFactorEnabled ? .green : .orange)
                        Badge(text: u.passwordStatus,
                              tint: u.passwordStatus == "temporär" ? .orange : .secondary)
                        Spacer()
                        Text(u.lastSeen != nil ? Format.relative(u.lastSeen) : "nie")
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 2)
            }
        }
    }

    // MARK: - Sitzungen

    @ViewBuilder
    private var sessionsSection: some View {
        Section("Aktive Sitzungen") {
            if model.sessions.isEmpty {
                Text("Keine aktiven Sitzungen.").foregroundStyle(.secondary)
            }
            ForEach(model.sessions) { s in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(spacing: 6) {
                            Text(s.username).font(.body.weight(.medium))
                            if s.current { Badge(text: "aktuell", tint: .green) }
                        }
                        Text("\(shortAgent(s.userAgent)) · \(s.ip ?? "–")")
                            .font(.caption).foregroundStyle(.secondary)
                        Text("zuletzt \(Format.relative(s.lastSeen))")
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    Spacer()
                    if !s.current {
                        Button("Beenden", role: .destructive) {
                            Task { await model.terminate(session: s) }
                        }
                        .font(.caption)
                        .buttonStyle(.borderless)
                    }
                }
                .padding(.vertical, 2)
            }
        }
    }

    private func shortAgent(_ ua: String?) -> String {
        guard let ua, !ua.isEmpty else { return "unbekannt" }
        for token in ["iPhone", "iPad", "Android", "Macintosh", "Windows", "Linux"] {
            if ua.contains(token) { return token }
        }
        return String(ua.prefix(20))
    }

    // MARK: - Datenbanken

    @ViewBuilder
    private var databasesSection: some View {
        Section("Datenbanken") {
            ForEach(model.databases) { db in
                VStack(alignment: .leading, spacing: 6) {
                    Button {
                        Haptics.tap()
                        Task { await model.toggleAccess(for: db) }
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 6) {
                                    Text(db.name).foregroundStyle(.primary)
                                    if db.isDefault { Badge(text: "Standard", tint: .secondary) }
                                }
                                Text("\(db.ownerName ?? "–") · \(Format.bytes(db.sizeBytes)) · \(db.sharedWith) geteilt")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: model.accessDatabaseID == db.id ? "chevron.up" : "chevron.down")
                                .font(.caption).foregroundStyle(.tertiary)
                        }
                    }
                    .buttonStyle(.plain)

                    if model.accessDatabaseID == db.id {
                        AccessMatrix(model: model, database: db)
                            .padding(.top, 4)
                    }
                }
                .padding(.vertical, 2)
            }
        }
    }
}

// MARK: - Rechte-Matrix

private struct AccessMatrix: View {
    let model: AdminConsoleViewModel
    let database: AdminDatabase

    @State private var selectedUser = ""
    @State private var selectedRole = "read_only"

    private var grantableUsers: [AdminUserStatus] {
        model.users.filter { u in !model.access.contains { $0.userID == u.id } }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(model.access) { entry in
                HStack {
                    Text(model.userName(entry.userID)).font(.subheadline)
                    Badge(text: Format.dbRole(entry.role),
                          tint: entry.role == "owner" ? .green : .secondary)
                    Spacer()
                    if !entry.implicit {
                        Button("Entziehen", role: .destructive) {
                            Task { await model.revoke(databaseID: database.id, userID: entry.userID) }
                        }
                        .font(.caption).buttonStyle(.borderless)
                    }
                }
            }
            Divider()
            HStack(spacing: 8) {
                Picker("Konto", selection: $selectedUser) {
                    Text("Konto …").tag("")
                    ForEach(grantableUsers) { Text($0.displayName).tag($0.id) }
                }
                .labelsHidden()
                Picker("Rolle", selection: $selectedRole) {
                    Text("Lesen").tag("read_only")
                    Text("Schreiben").tag("read_write")
                    Text("Eigentümer").tag("owner")
                }
                .labelsHidden()
                Spacer()
                Button("Zuweisen") {
                    guard !selectedUser.isEmpty else { return }
                    let uid = selectedUser
                    let role = selectedRole
                    selectedUser = ""
                    Task { await model.grant(databaseID: database.id, userID: uid, role: role) }
                }
                .font(.caption.weight(.semibold))
                .buttonStyle(.borderless)
                .disabled(selectedUser.isEmpty)
            }
        }
        .padding(10)
        .background(Color(.secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

/// Kleines Status-Etikett im HIG-Stil.
private struct Badge: View {
    let text: String
    var tint: Color = .secondary

    var body: some View {
        Text(text)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 7)
            .padding(.vertical, 2)
            .background(tint.opacity(0.16), in: Capsule())
            .foregroundStyle(tint == .secondary ? Color.secondary : tint)
    }
}
