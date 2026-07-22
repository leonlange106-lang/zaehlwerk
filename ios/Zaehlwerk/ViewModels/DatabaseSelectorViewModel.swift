import Foundation

/// Lädt die dem Nutzer zugänglichen Mandanten-Datenbanken und kennt die aktive.
@MainActor
@Observable
final class DatabaseSelectorViewModel {
    private let api = APIClient.shared

    private(set) var databases: [TenantDatabase] = []
    private(set) var activeID: String?
    private(set) var isLoading = false
    var errorMessage: String?

    nonisolated init() {}

    var hasChoice: Bool { databases.count > 1 }

    func load() async {
        if databases.isEmpty { isLoading = true }
        defer { isLoading = false }
        errorMessage = nil
        do {
            let response = try await api.fetchDatabases()
            databases = response.databases
            activeID = response.activeID
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    var activeName: String? {
        databases.first { $0.id == activeID }?.name
    }
}
