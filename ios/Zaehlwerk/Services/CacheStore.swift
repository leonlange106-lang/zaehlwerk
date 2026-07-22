import Foundation
import SwiftData

/// Offline-First-Cache auf Basis von SwiftData.
///
/// Speichert dekodierte `Codable`-Nutzdaten als JSON-Blob (`CachedResponse`).
/// Verwendet ein **eigenes, symmetrisches** Coder-Paar (`.iso8601` in beide
/// Richtungen): Der zentrale `JSONCoding`-Decoder erwartet String-Daten, sein
/// Encoder schreibt aber Zahlen – ein Round-Trip darüber wäre inkonsistent.
/// Hier kontrollieren wir beide Enden selbst.
@MainActor
final class CacheStore {
    static let shared = CacheStore()

    private let context: ModelContext?

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    private init() {
        do {
            let container = try ModelContainer(
                for: CachedResponse.self,
                configurations: ModelConfiguration(isStoredInMemoryOnly: false)
            )
            context = ModelContext(container)
        } catch {
            // Ohne persistenten Store läuft die App weiter – nur ohne Offline-Cache.
            context = nil
        }
    }

    // MARK: - Schlüssel

    enum Key {
        static let dashboard = "dashboard"
        static func readings(_ systemID: String) -> String { "readings.\(systemID)" }
        static func stats(_ systemID: String) -> String { "stats.\(systemID)" }
        static func chart(_ systemID: String) -> String { "chart.\(systemID)" }
    }

    // MARK: - Lesen / Schreiben

    func save<T: Encodable>(_ value: T, for key: String) {
        guard let context else { return }
        guard let data = try? encoder.encode(value) else { return }
        let descriptor = FetchDescriptor<CachedResponse>(
            predicate: #Predicate { $0.key == key }
        )
        if let existing = try? context.fetch(descriptor).first {
            existing.payload = data
            existing.updatedAt = Date()
        } else {
            context.insert(CachedResponse(key: key, payload: data, updatedAt: Date()))
        }
        try? context.save()
    }

    /// Liefert den zwischengespeicherten Wert samt Zeitpunkt der Ablage.
    func load<T: Decodable>(_ type: T.Type, for key: String) -> (value: T, updatedAt: Date)? {
        guard let context else { return nil }
        let descriptor = FetchDescriptor<CachedResponse>(
            predicate: #Predicate { $0.key == key }
        )
        guard let record = try? context.fetch(descriptor).first,
              let value = try? decoder.decode(T.self, from: record.payload) else { return nil }
        return (value, record.updatedAt)
    }

    /// Beim Abmelden alle zwischengespeicherten Daten verwerfen.
    func clear() {
        guard let context else { return }
        try? context.delete(model: CachedResponse.self)
        try? context.save()
    }
}
