import Foundation

/// ViewModel der Übersicht. Offline-First: zeigt zunächst den zuletzt
/// gecachten Stand, aktualisiert dann über das Netz und schreibt den frischen
/// Stand zurück in den Cache. Bricht das Netz weg, bleibt der Cache sichtbar.
@MainActor
@Observable
final class DashboardViewModel {
    private let api = APIClient.shared
    private let cache = CacheStore.shared

    private(set) var data: DashboardData?
    private(set) var isLoading = false
    private(set) var lastUpdated: Date?
    private(set) var isShowingCached = false
    var errorMessage: String?

    var systems: [DashboardSystem] { data?.systems ?? [] }
    var recent: [RecentReading] { data?.recent ?? [] }

    nonisolated init() {}

    func load() async {
        // 1. Sofort aus dem Cache anzeigen, falls noch nichts geladen wurde.
        if data == nil, let cached = cache.load(DashboardData.self, for: CacheStore.Key.dashboard) {
            data = cached.value
            lastUpdated = cached.updatedAt
            isShowingCached = true
        }
        if data == nil { isLoading = true }
        await fetch()
        isLoading = false
    }

    func refresh() async {
        await fetch()
    }

    private func fetch() async {
        do {
            let fresh = try await api.fetchDashboard()
            data = fresh
            lastUpdated = Date()
            isShowingCached = false
            errorMessage = nil
            cache.save(fresh, for: CacheStore.Key.dashboard)
        } catch let error as APIError {
            handle(error)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Bei Netzfehler den Cache behalten und nur kennzeichnen; sonst Fehler zeigen.
    private func handle(_ error: APIError) {
        if data != nil {
            isShowingCached = true
            errorMessage = nil
        } else {
            errorMessage = error.errorDescription
        }
    }
}
