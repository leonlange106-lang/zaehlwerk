import Foundation

/// Benutzerkonto (Spiegel von `UserRead` im Backend).
public struct User: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let username: String
    public let displayName: String
    public let role: String
    public let isAdmin: Bool
    public let aktiv: Bool
    public let source: String                 // "lokal" | "homeassistant"
    public let twoFactorEnabled: Bool
    public let isFirstLogin: Bool
    public let tempPasswordActive: Bool

    enum CodingKeys: String, CodingKey {
        case id, username, role, aktiv, source
        case displayName = "display_name"
        case isAdmin = "is_admin"
        case twoFactorEnabled = "two_factor_enabled"
        case isFirstLogin = "is_first_login"
        case tempPasswordActive = "temp_password_active"
    }
}

/// Ergebnis von `GET /api/auth/status`.
public struct AuthStatus: Codable, Sendable {
    public let mode: String                   // "lokal" | "homeassistant"
    public let authenticated: Bool
    public let setupRequired: Bool
    public let recovery: Bool
    public let cryptoAvailable: Bool
    public let user: User?
    public let permissions: [String: JSONValue]?
    public let roles: [JSONValue]

    enum CodingKeys: String, CodingKey {
        case mode, authenticated, recovery, user, permissions, roles
        case setupRequired = "setup_required"
        case cryptoAvailable = "crypto_available"
    }

    public var canWrite: Bool { boolPermission("write") }
    public var canExport: Bool { boolPermission("export") }
    public var isAdmin: Bool { boolPermission("admin") }

    private func boolPermission(_ key: String) -> Bool {
        if case .bool(let value)? = permissions?[key] { return value }
        return false
    }
}

/// Login-/2FA-Antwort. `status` steuert den Anmeldefluss.
public struct LoginResponse: Codable, Sendable {
    public enum Status: String, Codable, Sendable {
        case success = "SUCCESS"
        case requires2FA = "REQUIRES_2FA"
        case requiresFirstTimeSetup = "REQUIRES_FIRST_TIME_SETUP"
    }

    public let status: Status
    public let needsPasswordChange: Bool
    public let needs2FASetup: Bool
    public let user: User?

    enum CodingKeys: String, CodingKey {
        case status, user
        case needsPasswordChange = "needs_password_change"
        case needs2FASetup = "needs_2fa_setup"
    }
}

/// Antwort von `POST /api/auth/2fa/setup`.
public struct TwoFactorSetup: Codable, Sendable {
    public let secret: String
    public let otpauthURI: String
    public let qrDataURI: String

    enum CodingKeys: String, CodingKey {
        case secret
        case otpauthURI = "otpauth_uri"
        case qrDataURI = "qr_data_uri"
    }
}

// MARK: - Anfrage-Körper

struct LoginRequest: Encodable {
    let username: String
    let password: String
}

struct TwoFactorVerifyRequest: Encodable {
    let code: String
}

struct TwoFactorDisableRequest: Encodable {
    let password: String
    let code: String
}

// MARK: - Versionsverlauf (Changelog)

public struct ChangelogEntry: Decodable, Identifiable, Sendable {
    public let version: String
    public let date: String
    public let title: String
    public let changes: [String]
    public var id: String { version }
}

public struct ChangelogResponse: Decodable, Sendable {
    public let current: String
    public let entries: [ChangelogEntry]
}

struct ChangePasswordRequest: Encodable {
    let current_password: String
    let new_password: String
}
