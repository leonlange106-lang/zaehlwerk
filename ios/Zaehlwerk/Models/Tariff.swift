import Foundation

/// Aus einer hochgeladenen Vertragsunterlage vorgeschlagene Tariffelder.
public struct TariffOcrSuggestion: Decodable, Sendable {
    public let anbieter: String?
    public let arbeitspreis: Double?
    public let grundpreis: Double?
    public let gueltigAb: Date?
    public let gueltigBis: Date?
    public let noticePeriodDays: Int?

    enum CodingKeys: String, CodingKey {
        case anbieter, arbeitspreis, grundpreis
        case gueltigAb = "gueltig_ab"
        case gueltigBis = "gueltig_bis"
        case noticePeriodDays = "notice_period_days"
    }
}

/// Antwort von POST /api/tariffs/upload.
public struct TariffUploadResult: Decodable, Sendable {
    public let documentURL: String
    public let filename: String
    public let textExcerpt: String?
    public let ocrAvailable: Bool
    public let suggestion: TariffOcrSuggestion

    enum CodingKeys: String, CodingKey {
        case documentURL = "document_url"
        case filename
        case textExcerpt = "text_excerpt"
        case ocrAvailable = "ocr_available"
        case suggestion
    }
}
