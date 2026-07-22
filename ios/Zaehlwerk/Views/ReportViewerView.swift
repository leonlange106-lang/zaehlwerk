import SwiftUI
import PDFKit

/// Zeigt den serverseitig erzeugten PDF-Bericht eines Systems (TICKET-3.2) mit
/// PDFKit an und bietet ihn per ShareLink zum Teilen/Sichern an.
struct ReportViewerView: View {
    let systemID: String
    let systemName: String

    @State private var document: PDFDocument?
    @State private var fileURL: URL?
    @State private var error: String?
    @State private var loading = true

    var body: some View {
        Group {
            if loading {
                ProgressView("Bericht wird erstellt …")
            } else if let document {
                PDFKitView(document: document)
                    .ignoresSafeArea(edges: .bottom)
            } else {
                ContentUnavailableView("Bericht nicht verfügbar",
                                       systemImage: "doc.text.magnifyingglass",
                                       description: Text(error ?? "Unbekannter Fehler"))
            }
        }
        .navigationTitle("Bericht")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let fileURL {
                ToolbarItem(placement: .topBarTrailing) {
                    ShareLink(item: fileURL) {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .accessibilityLabel("Bericht teilen")
                }
            }
        }
        .task { await load() }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do {
            let data = try await APIClient.shared.fetchData(path: "/api/systems/\(systemID)/report.pdf")
            guard let doc = PDFDocument(data: data) else {
                error = "Antwort ist kein gültiges PDF."
                return
            }
            document = doc
            // Für den ShareLink in eine Datei mit sprechendem Namen schreiben.
            let safeName = systemName.replacingOccurrences(of: "/", with: "-")
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("Zaehlwerk-\(safeName).pdf")
            try? data.write(to: url)
            fileURL = url
        } catch {
            self.error = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}

/// UIViewRepresentable-Hülle um PDFView.
struct PDFKitView: UIViewRepresentable {
    let document: PDFDocument

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.document = document
        return view
    }

    func updateUIView(_ uiView: PDFView, context: Context) {
        if uiView.document !== document {
            uiView.document = document
        }
    }
}
