import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

/// Vertragsunterlage hochladen (Foto oder PDF) und die per OCR erkannten
/// Tariffelder anzeigen. Native Parität zur Web-Upload-Zone.
struct TariffUploadView: View {
    @State private var photoItem: PhotosPickerItem?
    @State private var showingFileImporter = false
    @State private var busy = false
    @State private var result: TariffUploadResult?
    @State private var error: String?

    var body: some View {
        Form {
            Section {
                PhotosPicker(selection: $photoItem, matching: .images) {
                    Label("Foto auswählen", systemImage: "photo")
                }
                Button {
                    showingFileImporter = true
                } label: {
                    Label("PDF auswählen", systemImage: "doc")
                }
            } header: {
                Text("Vertrag hochladen")
            } footer: {
                Text("Aus dem Dokument werden Anbieter, Preise, Laufzeit und Kündigungsfrist vorgeschlagen.")
            }

            if busy {
                Section { HStack { ProgressView(); Text("Dokument wird gelesen …") } }
            }
            if let error {
                Section { Text(error).foregroundStyle(.red) }
            }
            if let result {
                resultSection(result)
            }
        }
        .navigationTitle("Tarif-Upload")
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: photoItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self) {
                    await upload(data: data, filename: "vertrag.jpg", mime: "image/jpeg")
                }
            }
        }
        .fileImporter(isPresented: $showingFileImporter,
                      allowedContentTypes: [.pdf], allowsMultipleSelection: false) { res in
            switch res {
            case .success(let urls):
                guard let url = urls.first else { return }
                Task { await importPDF(url) }
            case .failure(let err):
                error = err.localizedDescription
            }
        }
    }

    @ViewBuilder
    private func resultSection(_ r: TariffUploadResult) -> some View {
        Section("Erkannte Felder") {
            if !r.ocrAvailable {
                Text("Texterkennung auf dem Server nicht verfügbar – Dokument wurde gespeichert.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            row("Anbieter", r.suggestion.anbieter)
            row("Arbeitspreis", r.suggestion.arbeitspreis.map { "\($0.formatted(.number.precision(.fractionLength(0...4)))) €/Einheit" })
            row("Grundpreis", r.suggestion.grundpreis.map { "\($0.formatted(.number.precision(.fractionLength(0...2)))) €/Jahr" })
            row("Kündigungsfrist", r.suggestion.noticePeriodDays.map { "\($0) Tage" })
            if r.suggestion.gueltigAb != nil || r.suggestion.gueltigBis != nil {
                row("Laufzeit", [r.suggestion.gueltigAb, r.suggestion.gueltigBis]
                    .compactMap { $0.map { Format.date($0) } }.joined(separator: " – "))
            }
        }
        if let excerpt = r.textExcerpt, !excerpt.isEmpty {
            Section("Textauszug") {
                Text(excerpt).font(.footnote).foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private func row(_ label: String, _ value: String?) -> some View {
        if let value, !value.isEmpty {
            LabeledContent(label, value: value)
        }
    }

    private func importPDF(_ url: URL) async {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        guard let data = try? Data(contentsOf: url) else {
            error = "PDF konnte nicht gelesen werden."
            return
        }
        await upload(data: data, filename: url.lastPathComponent, mime: "application/pdf")
    }

    private func upload(data: Data, filename: String, mime: String) async {
        busy = true; error = nil; result = nil
        defer { busy = false }
        do {
            result = try await APIClient.shared.uploadTariffDocument(
                data: data, filename: filename, mimeType: mime)
            Haptics.success()
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
        }
    }
}
