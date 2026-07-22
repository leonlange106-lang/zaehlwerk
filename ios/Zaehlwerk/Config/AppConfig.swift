import Foundation

/// Verbindungs- und Sitzungszustand, persistiert zwischen App-Starts.
/// Die Server-Adresse liegt in `UserDefaults` (kein Geheimnis), das
/// Sitzungstoken und optionale Cloudflare-Access-Zugangsdaten im Keychain.
@Observable
final class AppConfig {
    static let shared = AppConfig()

    private let defaults = UserDefaults.standard
    private let keychain = KeychainStore()

    private enum Keys {
        static let baseURL = "server_base_url"
        static let token = "session_token"
        static let cfClientId = "cf_access_client_id"
        static let cfClientSecret = "cf_access_client_secret"
        static let activeDatabaseID = "active_database_id"
    }

    /// Basis-URL des Backends, z. B. `https://zaehlwerk.example.com`.
    var baseURLString: String {
        didSet { defaults.set(baseURLString, forKey: Keys.baseURL) }
    }

    var baseURL: URL? {
        guard !baseURLString.isEmpty else { return nil }
        return URL(string: baseURLString)
    }

    var isConfigured: Bool { baseURL != nil }

    private init() {
        baseURLString = defaults.string(forKey: Keys.baseURL) ?? ""
        let db = defaults.string(forKey: Keys.activeDatabaseID)
        activeDatabaseID = (db?.isEmpty == false) ? db : nil
    }

    // MARK: - Sitzungstoken

    var sessionToken: String? {
        get { keychain.get(Keys.token) }
        set {
            if let value = newValue { keychain.set(value, for: Keys.token) }
            else { keychain.remove(Keys.token) }
        }
    }

    // MARK: - Cloudflare Access (optional, nur wenn davor geschaltet)

    var cfAccessClientId: String? {
        get { keychain.get(Keys.cfClientId) }
        set {
            if let value = newValue, !value.isEmpty { keychain.set(value, for: Keys.cfClientId) }
            else { keychain.remove(Keys.cfClientId) }
        }
    }

    var cfAccessClientSecret: String? {
        get { keychain.get(Keys.cfClientSecret) }
        set {
            if let value = newValue, !value.isEmpty { keychain.set(value, for: Keys.cfClientSecret) }
            else { keychain.remove(Keys.cfClientSecret) }
        }
    }

    /// Aktive Mandanten-DB (Header `X-Zaehlwerk-Database`). `nil` = Standard-DB.
    /// Bewusst in `UserDefaults`, damit die thread-sichere `ServerSettings` im
    /// `APIClient` denselben Wert liest.
    var activeDatabaseID: String? {
        didSet {
            defaults.set(activeDatabaseID ?? "", forKey: Keys.activeDatabaseID)
        }
    }

    func clearSession() {
        sessionToken = nil
        activeDatabaseID = nil
    }
}
