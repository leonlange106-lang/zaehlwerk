import SwiftUI

/// ViewModel der Zähler-Metadaten eines Systems (Liste, Vorschläge, Löschen).
@MainActor
@Observable
final class MetersViewModel {
    private let api = APIClient.shared
    let systemID: String

    private(set) var meters: [Meter] = []
    private(set) var bauarten: [String] = []
    private(set) var isLoading = false
    var errorMessage: String?

    nonisolated init(systemID: String) {
        self.systemID = systemID
    }

    func load() async {
        if meters.isEmpty { isLoading = true }
        defer { isLoading = false }
        await refresh()
        if bauarten.isEmpty {
            bauarten = (try? await api.fetchBauarten()) ?? []
        }
    }

    func refresh() async {
        do {
            meters = try await api.fetchMeters(systemID: systemID)
            errorMessage = nil
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func delete(_ meter: Meter) async {
        do {
            try await api.deleteMeter(id: meter.id)
            meters.removeAll { $0.id == meter.id }
            Haptics.success()
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
        }
    }
}
