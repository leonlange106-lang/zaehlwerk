import Foundation

/// ViewModel der Admin-Console: Kontostatus, Sitzungen und Datenbank-Verwaltung.
@MainActor
@Observable
final class AdminConsoleViewModel {
    private let api = APIClient.shared

    private(set) var users: [AdminUserStatus] = []
    private(set) var sessions: [AdminSession] = []
    private(set) var databases: [AdminDatabase] = []
    private(set) var isLoading = false
    var errorMessage: String?

    // Rechte-Matrix der gerade aufgeklappten DB.
    private(set) var access: [DatabaseAccessEntry] = []
    private(set) var accessDatabaseID: String?

    nonisolated init() {}

    func load() async {
        if users.isEmpty { isLoading = true }
        defer { isLoading = false }
        errorMessage = nil
        do {
            async let u = api.fetchMonitoringUsers()
            async let s = api.fetchSessions()
            async let d = api.fetchAdminDatabases()
            users = try await u
            sessions = try await s
            databases = try await d
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func userName(_ id: String) -> String {
        users.first { $0.id == id }?.displayName ?? id
    }

    // MARK: - Session-Kontrolle

    func terminate(session: AdminSession) async {
        await perform {
            try await self.api.terminateSession(jti: session.jti)
            Haptics.success()
        }
    }

    func terminateAll(user: AdminUserStatus) async {
        await perform {
            try await self.api.terminateUserSessions(userID: user.id)
            Haptics.success()
        }
    }

    // MARK: - Rechte-Matrix

    func toggleAccess(for database: AdminDatabase) async {
        if accessDatabaseID == database.id {
            accessDatabaseID = nil
            access = []
            return
        }
        do {
            access = try await api.fetchDatabaseAccess(databaseID: database.id)
            accessDatabaseID = database.id
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func grant(databaseID: String, userID: String, role: String) async {
        await perform {
            try await self.api.grantDatabaseAccess(databaseID: databaseID, userID: userID, role: role)
            self.access = try await self.api.fetchDatabaseAccess(databaseID: databaseID)
            Haptics.success()
        }
    }

    func revoke(databaseID: String, userID: String) async {
        await perform {
            try await self.api.revokeDatabaseAccess(databaseID: databaseID, userID: userID)
            self.access = try await self.api.fetchDatabaseAccess(databaseID: databaseID)
            Haptics.success()
        }
    }

    /// Führt eine mutierende Aktion aus und lädt danach die Übersicht neu.
    private func perform(_ action: @escaping () async throws -> Void) async {
        errorMessage = nil
        do {
            try await action()
            await load()
        } catch let error as APIError {
            errorMessage = error.errorDescription
            Haptics.error()
        } catch {
            errorMessage = error.localizedDescription
            Haptics.error()
        }
    }
}
