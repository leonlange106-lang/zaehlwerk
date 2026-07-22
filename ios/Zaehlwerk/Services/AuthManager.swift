import Foundation

/// Zustand des Anmeldeflusses, aus dem die Wurzel-View ableitet, was sie zeigt.
enum AuthPhase: Equatable {
    case launching             // Startprüfung läuft
    case unconfigured          // keine Server-Adresse hinterlegt
    case loggedOut             // Anmeldung nötig
    case twoFactorRequired     // Passwort ok, TOTP-Code fehlt noch
    case onboarding            // Erstanmeldung: Passwort + 2FA erzwungen
    case authenticated
}

/// Zentrale Auth-/Sitzungssteuerung (MVVM-M: das „Manager"-Modell).
/// Hält den beobachtbaren Anmeldezustand und kapselt alle Auth-Aufrufe.
@MainActor
@Observable
final class AuthManager {
    static let shared = AuthManager()

    private let api = APIClient.shared
    private let config = AppConfig.shared

    private(set) var phase: AuthPhase = .launching
    private(set) var status: AuthStatus?
    var errorMessage: String?
    var isBusy = false

    var user: User? { status?.user }
    var isConfigured: Bool { config.isConfigured }
    var serverURLString: String {
        get { config.baseURLString }
        set { config.baseURLString = newValue }
    }

    private init() {}

    // MARK: - Start & Status

    func bootstrap() async {
        guard config.isConfigured else { phase = .unconfigured; return }
        await refreshStatus()
    }

    func refreshStatus() async {
        do {
            let status = try await api.fetchAuthStatus()
            self.status = status
            derivePhase(from: status)
        } catch {
            // Unerreichbar/abgelaufen -> zurück zur Anmeldung (Offline-Cache
            // übernimmt später die Anzeige der letzten Daten).
            self.status = nil
            phase = config.isConfigured ? .loggedOut : .unconfigured
        }
    }

    private func derivePhase(from status: AuthStatus) {
        if status.authenticated, let user = status.user, user.isFirstLogin {
            phase = .onboarding
        } else if status.authenticated {
            phase = .authenticated
        } else {
            phase = .loggedOut
        }
    }

    // MARK: - Server-Adresse

    func configureServer(_ urlString: String) {
        config.baseURLString = urlString.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: - Anmeldung

    func login(username: String, password: String) async {
        await run {
            let response = try await self.api.login(username: username, password: password)
            switch response.status {
            case .success:
                await self.refreshStatus()
            case .requires2FA:
                self.phase = .twoFactorRequired
            case .requiresFirstTimeSetup:
                await self.refreshStatus()   // lädt User mit is_first_login -> .onboarding
            }
        }
    }

    func submitLoginCode(_ code: String) async {
        await run {
            _ = try await self.api.verifyTwoFactor(code: code)
            await self.refreshStatus()
        }
    }

    func cancelTwoFactor() async {
        await logout()
    }

    // MARK: - Onboarding & eigenes Konto

    /// Passwortwechsel – erster Onboarding-Schritt und zugleich Self-Service.
    func changePassword(current: String, new: String) async -> Bool {
        await run {
            _ = try await self.api.changePassword(current: current, new: new)
            await self.refreshStatus()
        }
        return errorMessage == nil
    }

    func setupTwoFactor() async -> TwoFactorSetup? {
        var result: TwoFactorSetup?
        await run { result = try await self.api.setupTwoFactor() }
        return result
    }

    /// Aktiviert 2FA (Onboarding-Schritt 2 bzw. Einstellungen).
    func verifyTwoFactor(code: String) async -> Bool {
        await run {
            _ = try await self.api.verifyTwoFactor(code: code)
            await self.refreshStatus()
        }
        return errorMessage == nil
    }

    // MARK: - Abmelden

    func logout() async {
        try? await api.logout()
        config.clearSession()
        CacheStore.shared.clear()
        status = nil
        phase = config.isConfigured ? .loggedOut : .unconfigured
    }

    // MARK: - Hilfsfunktion

    /// Führt einen Auth-Aufruf aus, kapselt busy-Flag und Fehlerabbildung.
    private func run(_ operation: @escaping () async throws -> Void) async {
        isBusy = true
        errorMessage = nil
        do {
            try await operation()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = error.localizedDescription
        }
        isBusy = false
    }
}
