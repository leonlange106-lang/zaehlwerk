import Foundation

/// ViewModel für das Erfassen einer neuen Ablesung.
@MainActor
@Observable
final class AddReadingViewModel {
    private let api = APIClient.shared
    let systemID: String

    var date = Date()
    var valueText = ""
    var costText = ""
    var note = ""
    var meterReplaced = false
    var meterStartText = ""
    var isBilled = false

    private(set) var isSaving = false
    var errorMessage: String?

    nonisolated init(systemID: String) {
        self.systemID = systemID
    }

    /// Zahl aus deutscher oder englischer Eingabe (Komma/Punkt) parsen.
    private func parse(_ text: String) -> Double? {
        let normalized = text
            .trimmingCharacters(in: .whitespaces)
            .replacingOccurrences(of: ".", with: "")
            .replacingOccurrences(of: ",", with: ".")
        return Double(normalized)
    }

    var isValid: Bool {
        parse(valueText) != nil
    }

    /// Legt die Ablesung an. Gibt bei Erfolg `true` zurück.
    func save() async -> Bool {
        guard let value = parse(valueText) else {
            errorMessage = "Bitte einen gültigen Zählerstand eingeben."
            return false
        }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let request = ReadingCreateRequest(
            date: date,
            value: value,
            // Kosten nur bei einer Abrechnungsablesung übernehmen.
            cost: isBilled ? parse(costText) : nil,
            meterReplaced: meterReplaced,
            meterStart: meterReplaced ? parse(meterStartText) : nil,
            note: note.isEmpty ? nil : note,
            isBilled: isBilled
        )
        do {
            _ = try await api.addReading(systemID: systemID, request)
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
