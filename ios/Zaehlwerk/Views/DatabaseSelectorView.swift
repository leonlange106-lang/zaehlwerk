import SwiftUI

/// Wechsel der aktiven Mandanten-Datenbank (TICKET-1.4). Zeigt alle zugänglichen
/// Datenbanken mit Rolle und Größe; die Auswahl schaltet den API-Kontext um und
/// verwirft den Offline-Cache der vorherigen Datenbank.
struct DatabaseSelectorView: View {
    @Environment(AuthManager.self) private var auth
    @Environment(\.dismiss) private var dismiss
    @State private var model = DatabaseSelectorViewModel()

    var body: some View {
        List {
            if let message = model.errorMessage {
                Section { Text(message).foregroundStyle(.red) }
            }
            Section {
                ForEach(model.databases) { db in
                    Button {
                        select(db)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "cylinder.split.1x2")
                                .foregroundStyle(.secondary)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(db.name).foregroundStyle(.primary)
                                Text("\(Format.dbRole(db.role)) · \(Format.bytes(db.sizeBytes))")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if db.id == model.activeID {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.tint)
                                    .fontWeight(.semibold)
                            }
                        }
                    }
                }
            } header: {
                Text("Datenbank")
            } footer: {
                Text("Die aktive Datenbank bestimmt, welche Systeme und Ablesungen die App anzeigt.")
            }
        }
        .navigationTitle("Datenbank wählen")
        .navigationBarTitleDisplayMode(.inline)
        .overlay { if model.isLoading { ProgressView() } }
        .task { await model.load() }
    }

    private func select(_ db: TenantDatabase) {
        guard db.id != model.activeID else { dismiss(); return }
        Haptics.selection()
        // Immer die explizite ID setzen: der Server löst damit für jede Rolle
        // eindeutig die richtige DB auf (ein leerer Header würde stattdessen die
        // eigene Eigentümer-DB wählen).
        auth.switchDatabase(to: db.id)
        dismiss()
    }
}
