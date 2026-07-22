import Foundation

/// Stark typisierter, async/await-basierter Client für die Zählwerk-REST-API.
///
/// - Authentifizierung über das `zw_session`-Token als `Bearer`-Header. Das
///   Token wird beim Login/2FA aus dem `Set-Cookie` der Antwort übernommen und
///   im Keychain gehalten; beim Abmelden wieder entfernt.
/// - Optionale Cloudflare-Access-Service-Token-Header, falls das Backend hinter
///   Cloudflare Access liegt.
/// - Einheitliche Fehlerabbildung auf `APIError`.
///
/// `@unchecked Sendable`: der Client hält nur eine `URLSession` (Sendable) und
/// liest Konfiguration ausschliesslich über thread-sichere Primitive
/// (`UserDefaults`, Keychain).
final class APIClient: @unchecked Sendable {
    static let shared = APIClient()

    private let session: URLSession
    private let server = ServerSettings()
    private let tokens = SessionTokenStore()

    init(session: URLSession = .shared) {
        self.session = session
    }

    // MARK: - Öffentliche Aufrufe

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        try await send(method: "GET", path: path, query: query, body: Optional<Empty>.none)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await send(method: "POST", path: path, query: [:], body: body)
    }

    func post<T: Decodable>(_ path: String) async throws -> T {
        try await send(method: "POST", path: path, query: [:], body: Optional<Empty>.none)
    }

    func patch<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await send(method: "PATCH", path: path, query: [:], body: body)
    }

    func put<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        try await send(method: "PUT", path: path, query: [:], body: body)
    }

    @discardableResult
    func postNoContent<B: Encodable>(_ path: String, body: B) async throws -> Bool {
        _ = try await raw(method: "POST", path: path, query: [:], body: body)
        return true
    }

    @discardableResult
    func postNoContent(_ path: String) async throws -> Bool {
        _ = try await raw(method: "POST", path: path, query: [:], body: Optional<Empty>.none)
        return true
    }

    @discardableResult
    func delete(_ path: String) async throws -> Bool {
        _ = try await raw(method: "DELETE", path: path, query: [:], body: Optional<Empty>.none)
        return true
    }

    // MARK: - Multipart-Upload (Dokumente)

    /// Lädt eine Datei (PDF/Bild) als multipart/form-data hoch und dekodiert die
    /// Antwort. Trägt dieselben Auth-/CF-/DB-Header wie alle anderen Aufrufe.
    func uploadDocument<T: Decodable>(
        path: String, fileData: Data, filename: String, mimeType: String
    ) async throws -> T {
        guard let base = server.baseURL else { throw APIError.notConfigured }
        var baseString = base.absoluteString
        if baseString.hasSuffix("/") { baseString.removeLast() }
        guard let url = URL(string: baseString + path) else { throw APIError.invalidURL }

        let boundary = "ZW-\(UUID().uuidString)"
        var body = Data()
        func append(_ s: String) { body.append(s.data(using: .utf8)!) }
        append("--\(boundary)\r\n")
        append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n")
        append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(fileData)
        append("\r\n--\(boundary)--\r\n")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token = tokens.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let id = tokens.cfClientId, let secret = tokens.cfClientSecret {
            request.setValue(id, forHTTPHeaderField: "CF-Access-Client-Id")
            request.setValue(secret, forHTTPHeaderField: "CF-Access-Client-Secret")
        }
        if let dbID = server.activeDatabaseID {
            request.setValue(dbID, forHTTPHeaderField: "X-Zaehlwerk-Database")
        }
        request.httpBody = body

        let data: Data, response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError where error.code == .notConnectedToInternet {
            throw APIError.offline
        } catch {
            throw APIError.transport(error)
        }
        guard let http = response as? HTTPURLResponse else {
            throw APIError.server(status: -1, detail: nil)
        }
        syncToken(from: http)
        switch http.statusCode {
        case 200...299:
            do { return try JSONCoding.decoder.decode(T.self, from: data) }
            catch { throw APIError.decoding(error) }
        case 401: throw APIError.unauthorized
        case 403:
            let parsed = try? JSONCoding.decoder.decode(APIErrorBody.self, from: data)
            throw APIError.forbidden(parsed?.detail ?? "Keine Berechtigung.")
        default:
            let parsed = try? JSONCoding.decoder.decode(APIErrorBody.self, from: data)
            throw APIError.server(status: http.statusCode, detail: parsed?.detail)
        }
    }

    // MARK: - Kern

    private func send<B: Encodable, T: Decodable>(
        method: String, path: String, query: [String: String], body: B?
    ) async throws -> T {
        let (data, _) = try await raw(method: method, path: path, query: query, body: body)
        if T.self == EmptyResponse.self, let empty = EmptyResponse() as? T { return empty }
        do {
            return try JSONCoding.decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private func raw<B: Encodable>(
        method: String, path: String, query: [String: String], body: B?
    ) async throws -> (Data, HTTPURLResponse) {
        guard let base = server.baseURL else { throw APIError.notConfigured }
        // Basis-URL (ohne Schluss-Slash) direkt mit dem Pfad ("/api/…")
        // verketten – zuverlässiger als appendingPathComponent bei führenden
        // Slashes und Query-Parametern.
        var baseString = base.absoluteString
        if baseString.hasSuffix("/") { baseString.removeLast() }
        guard var components = URLComponents(string: baseString + path) else {
            throw APIError.invalidURL
        }
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = tokens.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let id = tokens.cfClientId, let secret = tokens.cfClientSecret {
            request.setValue(id, forHTTPHeaderField: "CF-Access-Client-Id")
            request.setValue(secret, forHTTPHeaderField: "CF-Access-Client-Secret")
        }
        // Aktive Mandanten-DB mitschalten (Kontextwechsel im Multi-DB-Betrieb).
        if let dbID = server.activeDatabaseID {
            request.setValue(dbID, forHTTPHeaderField: "X-Zaehlwerk-Database")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONCoding.encoder.encode(body)
        }

        let data: Data, response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError where error.code == .notConnectedToInternet {
            throw APIError.offline
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.server(status: -1, detail: nil)
        }

        // Sitzungstoken aus einem gesetzten Cookie übernehmen bzw. entfernen.
        syncToken(from: http)

        switch http.statusCode {
        case 200...299:
            return (data, http)
        case 401:
            throw APIError.unauthorized
        case 403:
            let parsed = try? JSONCoding.decoder.decode(APIErrorBody.self, from: data)
            if parsed?.status == "REQUIRES_FIRST_TIME_SETUP" { throw APIError.requiresFirstTimeSetup }
            throw APIError.forbidden(parsed?.detail ?? "Keine Berechtigung.")
        default:
            let parsed = try? JSONCoding.decoder.decode(APIErrorBody.self, from: data)
            throw APIError.server(status: http.statusCode, detail: parsed?.detail)
        }
    }

    // MARK: - Token aus Set-Cookie

    private func syncToken(from http: HTTPURLResponse) {
        guard let header = http.value(forHTTPHeaderField: "Set-Cookie"),
              header.contains("zw_session=") else { return }
        // Wert bis zum nächsten ';' extrahieren.
        guard let range = header.range(of: "zw_session=") else { return }
        let after = header[range.upperBound...]
        let value = String(after.prefix { $0 != ";" })
        let cleared = value.isEmpty
            || header.range(of: "Max-Age=0") != nil
            || header.range(of: "max-age=0", options: .caseInsensitive) != nil
        tokens.set(cleared ? nil : value)
    }
}

/// Leerer Body/Antwort-Platzhalter.
struct Empty: Codable {}
struct EmptyResponse: Codable {}
