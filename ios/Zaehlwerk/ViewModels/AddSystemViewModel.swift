import SwiftUI

/// ViewModel zum Anlegen eines neuen Systems.
@MainActor
@Observable
final class AddSystemViewModel {
    private let api = APIClient.shared

    var name = ""
    var type = ""
    var unit = ""
    var color: Color = .blue

    private(set) var isSaving = false
    var errorMessage: String?

    nonisolated init() {}

    var isValid: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty
            && !type.trimmingCharacters(in: .whitespaces).isEmpty
            && !unit.trimmingCharacters(in: .whitespaces).isEmpty
    }

    /// Legt das System an. Gibt bei Erfolg `true` zurück.
    func save() async -> Bool {
        guard isValid else {
            errorMessage = "Bitte Name, Typ und Einheit angeben."
            return false
        }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let request = SystemCreateRequest(
            name: name.trimmingCharacters(in: .whitespaces),
            typ: type.trimmingCharacters(in: .whitespaces),
            einheit: unit.trimmingCharacters(in: .whitespaces),
            farbe: color.hexString,
            icon: SystemStyle.iconName(for: type)
        )
        do {
            _ = try await api.createSystem(request)
            Haptics.success()
            return true
        } catch let error as APIError {
            errorMessage = error.errorDescription
            Haptics.error()
            return false
        } catch {
            errorMessage = error.localizedDescription
            Haptics.error()
            return false
        }
    }
}
