import Foundation

/// Thread-sichere, wertbasierte Zugriffe auf die Verbindungs-Basisdaten.
/// Bewusst über `UserDefaults`/Keychain statt über den `@Observable`-`AppConfig`,
/// damit der `APIClient` sie gefahrlos von Hintergrund-Tasks aus lesen kann
/// (Swift-6-Nebenläufigkeit).

enum StorageKeys {
    static let baseURL = "server_base_url"
    static let sessionToken = "session_token"
    static let cfClientId = "cf_access_client_id"
    static let cfClientSecret = "cf_access_client_secret"
    static let keychainService = "de.zaehlwerk.app"
}

struct ServerSettings: Sendable {
    var baseURL: URL? {
        guard let raw = UserDefaults.standard.string(forKey: StorageKeys.baseURL),
              !raw.isEmpty else { return nil }
        return URL(string: raw)
    }
}

struct SessionTokenStore: Sendable {
    private let keychain = KeychainStore(service: StorageKeys.keychainService)

    var token: String? { keychain.get(StorageKeys.sessionToken) }

    func set(_ token: String?) {
        if let token, !token.isEmpty { keychain.set(token, for: StorageKeys.sessionToken) }
        else { keychain.remove(StorageKeys.sessionToken) }
    }

    var cfClientId: String? { keychain.get(StorageKeys.cfClientId) }
    var cfClientSecret: String? { keychain.get(StorageKeys.cfClientSecret) }
}
