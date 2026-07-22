import Foundation

/// Ein erfasstes System (Strom, Gas, Wasser, PV …). Spiegel von `SystemRead`.
/// Heisst bewusst `MeterSystem`, um Verwechslungen mit Swifts `System` zu
/// vermeiden; die API-Felder bleiben über `CodingKeys` erhalten.
public struct MeterSystem: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let name: String
    public let type: String                   // "Strom" | "Gas" | "Wasser" | "PV-…"
    public let unit: String                   // "kWh" | "m³" …
    public let colorHex: String
    public let icon: String
    public let extraFields: [String: JSONValue]
    public let aktiv: Bool
    public let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, name, icon, aktiv
        case type = "typ"
        case unit = "einheit"
        case colorHex = "farbe"
        case extraFields = "zusatzfelder"
        case createdAt = "erstellt_am"
    }
}

// MARK: - Anfrage-Körper (Anlegen/Ändern)

struct SystemCreateRequest: Encodable {
    let name: String
    let typ: String
    let einheit: String
    let farbe: String?
    let icon: String?
    let zusatzfelder: [String: JSONValue]?

    init(name: String, typ: String, einheit: String,
         farbe: String? = nil, icon: String? = nil,
         zusatzfelder: [String: JSONValue]? = nil) {
        self.name = name
        self.typ = typ
        self.einheit = einheit
        self.farbe = farbe
        self.icon = icon
        self.zusatzfelder = zusatzfelder
    }
}

/// Teil-Update eines Systems (PATCH). Nur gesetzte Felder werden gesendet;
/// `aktiv: false` archiviert, `aktiv: true` reaktiviert.
struct SystemUpdateRequest: Encodable {
    var name: String?
    var typ: String?
    var einheit: String?
    var farbe: String?
    var icon: String?
    var zusatzfelder: [String: JSONValue]?
    var aktiv: Bool?
}

// MARK: - Smart-Home-Anbindung live prüfen (POST /api/systems/binding/test)

struct BindingTestRequest: Encodable {
    let kind: String            // "ha" | "rest"
    var entity_id: String?
    var url: String?
    var path: String?
}

struct BindingTestResult: Decodable, Sendable {
    let ok: Bool
    let value: JSONValue?
    let unit: String?
    let matched_path: String?
    let error: String?
}
