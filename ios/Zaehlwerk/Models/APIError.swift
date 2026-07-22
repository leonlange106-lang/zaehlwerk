import Foundation

/// Typisierte Fehler des Netzwerk-Layers. Jede Fehlerquelle wird auf einen
/// klaren Fall abgebildet, damit ViewModels gezielt reagieren können (z. B.
/// `.unauthorized` -> zurück zum Login).
public enum APIError: Error, LocalizedError, Sendable {
    case invalidURL
    case notConfigured                 // keine Server-Adresse hinterlegt
    case unauthorized                  // 401 – Sitzung abgelaufen / nicht angemeldet
    case forbidden(String)             // 403 – keine Berechtigung / Onboarding nötig
    case requiresFirstTimeSetup        // 403 mit Status REQUIRES_FIRST_TIME_SETUP
    case server(status: Int, detail: String?)
    case decoding(Error)
    case transport(Error)              // URLSession-/Verbindungsfehler
    case offline

    public var errorDescription: String? {
        switch self {
        case .invalidURL: return "Ungültige Adresse."
        case .notConfigured: return "Keine Server-Adresse hinterlegt."
        case .unauthorized: return "Sitzung abgelaufen. Bitte erneut anmelden."
        case .forbidden(let detail): return detail
        case .requiresFirstTimeSetup: return "Erstanmeldung erforderlich."
        case .server(let status, let detail):
            return detail ?? "Serverfehler (\(status))."
        case .decoding: return "Antwort konnte nicht gelesen werden."
        case .transport(let error): return error.localizedDescription
        case .offline: return "Keine Internetverbindung."
        }
    }
}

/// Fehlerkörper des Backends: `{ "detail": "…" }` bzw. bei der Middleware
/// zusätzlich `{ "status": "REQUIRES_FIRST_TIME_SETUP" }`.
struct APIErrorBody: Decodable {
    let detail: String?
    let status: String?
}
