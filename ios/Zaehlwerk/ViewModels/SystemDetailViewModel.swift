import Foundation

/// ViewModel des System-Details: lädt Statistik, Diagrammdaten und Ablesungen
/// eines Systems parallel und hält sie beobachtbar.
@MainActor
@Observable
final class SystemDetailViewModel {
    private let api = APIClient.shared
    let systemID: String

    private(set) var stats: SystemStats?
    private(set) var chart: ChartData?
    private(set) var readings: [Reading] = []
    private(set) var isLoading = false
    var errorMessage: String?

    nonisolated init(systemID: String) {
        self.systemID = systemID
    }

    func load() async {
        if stats == nil && readings.isEmpty { isLoading = true }
        await fetch()
        isLoading = false
    }

    func refresh() async {
        await fetch()
    }

    private func fetch() async {
        errorMessage = nil
        do {
            // Parallel laden – die drei Aufrufe sind unabhängig.
            async let statsResult = api.fetchStats(systemID: systemID)
            async let chartResult = api.fetchChartData(systemID: systemID)
            async let readingsResult = api.fetchReadings(systemID: systemID)

            stats = try await statsResult
            chart = try await chartResult
            // Neueste Ablesungen zuerst.
            readings = try await readingsResult.sorted { $0.date > $1.date }
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
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
