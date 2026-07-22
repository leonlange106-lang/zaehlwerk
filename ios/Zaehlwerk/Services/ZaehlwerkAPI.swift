import Foundation

/// Stark typisierte Endpunkte, aufgesetzt auf den generischen `APIClient`.
/// Ein Aufruf je Backend-Route – die ViewModels sprechen ausschliesslich diese
/// Methoden an, nie URLs.
extension APIClient {

    // MARK: - Authentifizierung

    func fetchAuthStatus() async throws -> AuthStatus {
        try await get("/api/auth/status")
    }

    func login(username: String, password: String) async throws -> LoginResponse {
        try await post("/api/auth/login", body: LoginRequest(username: username, password: password))
    }

    func verifyTwoFactor(code: String) async throws -> LoginResponse {
        try await post("/api/auth/2fa/verify", body: TwoFactorVerifyRequest(code: code))
    }

    func setupTwoFactor() async throws -> TwoFactorSetup {
        try await post("/api/auth/2fa/setup")
    }

    func changePassword(current: String, new: String) async throws -> User {
        try await post("/api/auth/change-password",
                       body: ChangePasswordRequest(current_password: current, new_password: new))
    }

    func fetchMe() async throws -> User {
        try await get("/api/auth/me")
    }

    func logout() async throws {
        try await postNoContent("/api/auth/logout")
    }

    // MARK: - Systeme

    func fetchSystems() async throws -> [MeterSystem] {
        try await get("/api/systems")
    }

    func fetchSystem(id: String) async throws -> MeterSystem {
        try await get("/api/systems/\(id)")
    }

    func createSystem(_ request: SystemCreateRequest) async throws -> MeterSystem {
        try await post("/api/systems", body: request)
    }

    // MARK: - Ablesungen

    func fetchReadings(systemID: String) async throws -> [Reading] {
        try await get("/api/systems/\(systemID)/readings")
    }

    func addReading(systemID: String, _ request: ReadingCreateRequest) async throws -> Reading {
        try await post("/api/systems/\(systemID)/readings", body: request)
    }

    func deleteReading(id: String) async throws {
        try await delete("/api/readings/\(id)")
    }

    // MARK: - Statistik / Verläufe

    func fetchStats(systemID: String) async throws -> SystemStats {
        try await get("/api/systems/\(systemID)/stats")
    }

    func fetchChartData(systemID: String) async throws -> ChartData {
        try await get("/api/systems/\(systemID)/chart-data")
    }

    // MARK: - Dashboard

    func fetchDashboard(months: Int = 24) async throws -> DashboardData {
        try await get("/api/dashboard/data", query: ["months": String(months)])
    }

    // MARK: - Mandanten-Datenbanken (Multi-DB)

    func fetchDatabases() async throws -> DatabaseListResponse {
        try await get("/api/databases")
    }

    // MARK: - Admin: Datenbanken & Rechte-Matrix

    func fetchAdminDatabases() async throws -> [AdminDatabase] {
        try await get("/api/admin/databases")
    }

    func fetchDatabaseAccess(databaseID: String) async throws -> [DatabaseAccessEntry] {
        try await get("/api/admin/databases/\(databaseID)/access")
    }

    func grantDatabaseAccess(databaseID: String, userID: String, role: String) async throws {
        try await postNoContent("/api/admin/databases/\(databaseID)/access",
                                body: GrantAccessRequest(user_id: userID, role: role))
    }

    func revokeDatabaseAccess(databaseID: String, userID: String) async throws {
        try await delete("/api/admin/databases/\(databaseID)/access/\(userID)")
    }

    // MARK: - Admin: Monitoring & Session-Kontrolle

    func fetchMonitoringUsers() async throws -> [AdminUserStatus] {
        try await get("/api/admin/monitoring/users")
    }

    func fetchSessions() async throws -> [AdminSession] {
        try await get("/api/admin/monitoring/sessions")
    }

    func terminateSession(jti: String) async throws {
        try await delete("/api/admin/monitoring/sessions/\(jti)")
    }

    func terminateUserSessions(userID: String) async throws {
        try await postNoContent("/api/admin/monitoring/users/\(userID)/logout")
    }
}
