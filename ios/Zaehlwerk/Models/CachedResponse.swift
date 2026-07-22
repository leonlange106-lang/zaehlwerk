import Foundation
import SwiftData

/// Generischer Offline-Cache-Eintrag. Statt für jedes Domänenobjekt ein
/// eigenes `@Model` zu pflegen (fehleranfällig, Schema-Migrationen), legen wir
/// die bereits dekodierten `Codable`-Nutzdaten als JSON-Blob unter einem
/// Schlüssel ab. Das hält das SwiftData-Schema minimal und stabil.
@Model
final class CachedResponse {
    @Attribute(.unique) var key: String
    var payload: Data
    var updatedAt: Date

    init(key: String, payload: Data, updatedAt: Date) {
        self.key = key
        self.payload = payload
        self.updatedAt = updatedAt
    }
}
