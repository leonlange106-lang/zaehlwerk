import Foundation

/// Eine dem Nutzer zugängliche Mandanten-DB (aus `GET /api/databases`).
public struct TenantDatabase: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let role: String                 // owner | read_write | read_only
    public let isDefault: Bool
    public let ownerUserID: String
    public let dbKind: String
    public let sizeBytes: Int

    enum CodingKeys: String, CodingKey {
        case id, name, role
        case isDefault = "is_default"
        case ownerUserID = "owner_user_id"
        case dbKind = "db_kind"
        case sizeBytes = "size_bytes"
    }
}

public struct DatabaseListResponse: Codable, Sendable {
    public let activeID: String?
    public let databases: [TenantDatabase]

    enum CodingKeys: String, CodingKey {
        case activeID = "active_id"
        case databases
    }
}

/// Admin-Übersicht aller Datenbanken (`GET /api/admin/databases`).
public struct AdminDatabase: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let isDefault: Bool
    public let dbKind: String
    public let ownerUserID: String
    public let ownerName: String?
    public let sizeBytes: Int
    public let sharedWith: Int

    enum CodingKeys: String, CodingKey {
        case id, name
        case isDefault = "is_default"
        case dbKind = "db_kind"
        case ownerUserID = "owner_user_id"
        case ownerName = "owner_name"
        case sizeBytes = "size_bytes"
        case sharedWith = "shared_with"
    }
}

/// Zugriffseintrag der Rechte-Matrix einer DB.
public struct DatabaseAccessEntry: Codable, Identifiable, Hashable, Sendable {
    public let userID: String
    public let role: String
    public let implicit: Bool

    public var id: String { userID }

    enum CodingKeys: String, CodingKey {
        case userID = "user_id"
        case role, implicit
    }
}

/// Kontostatus fürs Admin-Monitoring (`GET /api/admin/monitoring/users`).
public struct AdminUserStatus: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let username: String
    public let displayName: String
    public let role: String
    public let isAdmin: Bool
    public let aktiv: Bool
    public let source: String
    public let twoFactorEnabled: Bool
    public let twoFactorStatus: String
    public let passwordStatus: String
    public let isFirstLogin: Bool
    public let lastSeen: Date?
    public let online: Bool
    public let activeSessions: Int

    enum CodingKeys: String, CodingKey {
        case id, username, role, aktiv, source, online
        case displayName = "display_name"
        case isAdmin = "is_admin"
        case twoFactorEnabled = "two_factor_enabled"
        case twoFactorStatus = "two_factor_status"
        case passwordStatus = "password_status"
        case isFirstLogin = "is_first_login"
        case lastSeen = "last_seen"
        case activeSessions = "active_sessions"
    }
}

/// Eine aktive Sitzung (`GET /api/admin/monitoring/sessions`).
public struct AdminSession: Codable, Identifiable, Hashable, Sendable {
    public let jti: String
    public let userID: String
    public let username: String
    public let createdAt: Date?
    public let lastSeen: Date?
    public let expiresAt: Date?
    public let userAgent: String?
    public let ip: String?
    public let current: Bool

    public var id: String { jti }

    enum CodingKeys: String, CodingKey {
        case jti, username, ip, current
        case userID = "user_id"
        case createdAt = "created_at"
        case lastSeen = "last_seen"
        case expiresAt = "expires_at"
        case userAgent = "user_agent"
    }
}

// MARK: - Anfrage-Körper

struct GrantAccessRequest: Encodable {
    let user_id: String
    let role: String
}
