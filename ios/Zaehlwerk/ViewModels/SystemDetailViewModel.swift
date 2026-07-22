import Foundation

/// ViewModel des System-Details. Offline-First: Statistik, Diagramm und
/// Ablesungen werden zuerst aus dem Cache gezeigt, dann parallel über das Netz
/// aktualisiert und zurückgeschrieben.
@MainActor
@Observable
final class SystemDetailViewModel {
    private let api = APIClient.shared
    private let cache = CacheStore.shared
    let systemID: String

    private(set) var stats: SystemStats?
    private(set) var chart: ChartData?
    private(set) var readings: [Reading] = []
    private(set) var isLoading = false
    private(set) var lastUpdated: Date?
    private(set) var isShowingCached = false
    var errorMessage: String?

    nonisolated init(systemID: String) {
        self.systemID = systemID
    }

    func load() async {
        seedFromCache()
        if stats == nil && readings.isEmpty { isLoading = true }
        await fetch()
        isLoading = false
    }

    func refresh() async {
        await fetch()
    }

    private func seedFromCache() {
        guard stats == nil && chart == nil && readings.isEmpty else { return }
        if let cached = cache.load(SystemStats.self, for: CacheStore.Key.stats(systemID)) {
            stats = cached.value
            lastUpdated = cached.updatedAt
            isShowingCached = true
        }
        if let cached = cache.load(ChartData.self, for: CacheStore.Key.chart(systemID)) {
            chart = cached.value
        }
        if let cached = cache.load([Reading].self, for: CacheStore.Key.readings(systemID)) {
            readings = cached.value.sorted { $0.date > $1.date }
        }
    }

    private func fetch() async {
        do {
            async let statsResult = api.fetchStats(systemID: systemID)
            async let chartResult = api.fetchChartData(systemID: systemID)
            async let readingsResult = api.fetchReadings(systemID: systemID)

            let freshStats = try await statsResult
            let freshChart = try await chartResult
            let freshReadings = try await readingsResult.sorted { $0.date > $1.date }

            stats = freshStats
            chart = freshChart
            readings = freshReadings
            lastUpdated = Date()
            isShowingCached = false
            errorMessage = nil

            cache.save(freshStats, for: CacheStore.Key.stats(systemID))
            cache.save(freshChart, for: CacheStore.Key.chart(systemID))
            cache.save(freshReadings, for: CacheStore.Key.readings(systemID))
        } catch let error as APIError {
            if stats != nil || !readings.isEmpty {
                isShowingCached = true
                errorMessage = nil
            } else {
                errorMessage = error.errorDescription
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Lädt die vollständigen Stammdaten (inkl. zusatzfelder) für die
    /// Bearbeiten-Maske.
    func loadEditableSystem() async -> MeterSystem? {
        do {
            return try await api.fetchSystem(id: systemID)
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return nil
        }
    }

    /// Archiviert (aktiv:false) das System. Gibt bei Erfolg `true` zurück.
    func archive() async -> Bool {
        do {
            try await api.setSystemActive(id: systemID, active: false)
            Haptics.success()
            return true
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return false
        }
    }

    /// Löscht das System endgültig (inkl. Ablesungen und Zähler).
    func deleteSystem() async -> Bool {
        do {
            try await api.deleteSystem(id: systemID)
            Haptics.success()
            return true
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return false
        }
    }

    func deleteReading(_ reading: Reading) async {
        do {
            try await api.deleteReading(id: reading.id)
            readings.removeAll { $0.id == reading.id }
            Haptics.success()
            await refresh()
        } catch let error as APIError {
            errorMessage = error.errorDescription
            Haptics.error()
        } catch {
            errorMessage = error.localizedDescription
            Haptics.error()
        }
    }
}
