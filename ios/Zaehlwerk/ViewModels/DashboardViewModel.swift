import Foundation

/// ViewModel der Übersicht. Lädt das Dashboard-Aggregat und hält den
/// Ladezustand beobachtbar für die View.
@MainActor
@Observable
final class DashboardViewModel {
    private let api = APIClient.shared

    private(set) var data: DashboardData?
    private(set) var isLoading = false
    var errorMessage: String?

    var systems: [DashboardSystem] { data?.systems ?? [] }
    var recent: [RecentReading] { data?.recent ?? [] }

    nonisolated init() {}

    /// Erstladen (zeigt Spinner nur, wenn noch nichts da ist).
    func load() async {
        if data == nil { isLoading = true }
        await fetch()
        isLoading = false
    }

    /// Pull-to-Refresh (ohne Vollbild-Spinner).
    func refresh() async {
        await fetch()
    }

    private func fetch() async {
        errorMessage = nil
        do {
            data = try await api.fetchDashboard()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
