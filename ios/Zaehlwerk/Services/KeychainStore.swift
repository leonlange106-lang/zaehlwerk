import Foundation
import Security

/// Schmaler Keychain-Wrapper für das Sitzungstoken. Bewusst nur String-Werte;
/// der Zugriff ist auf „nach dem ersten Entsperren dieses Geräts" beschränkt,
/// damit die App im Hintergrund starten kann, das Token aber nicht über ein
/// Backup auf ein anderes Gerät wandert.
struct KeychainStore {
    let service: String

    init(service: String = "de.zaehlwerk.app") {
        self.service = service
    }

    func set(_ value: String, for key: String) {
        let data = Data(value.utf8)
        var query = baseQuery(for: key)
        SecItemDelete(query as CFDictionary)
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(query as CFDictionary, nil)
    }

    func get(_ key: String) -> String? {
        var query = baseQuery(for: key)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func remove(_ key: String) {
        SecItemDelete(baseQuery(for: key) as CFDictionary)
    }

    private func baseQuery(for key: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
    }
}
