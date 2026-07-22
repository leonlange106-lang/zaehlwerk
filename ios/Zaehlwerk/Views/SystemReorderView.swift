import SwiftUI

/// Systeme per Drag neu anordnen (TICKET-4.2). List mit .onMove, aktualisiert
/// die @Observable-Liste sofort und sendet die neue Reihenfolge async an den
/// Server; beim Ablegen gibt es haptisches Feedback.
struct SystemReorderView: View {
    @Environment(\.dismiss) private var dismiss
    var onSaved: () -> Void

    @State private var model = SystemReorderViewModel()

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(model.systems) { system in
                        HStack(spacing: 10) {
                            Circle().fill(SystemStyle.color(system.colorHex)).frame(width: 10, height: 10)
                            Text(system.name)
                            Spacer()
                            Text(system.type).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .onMove { from, to in
                        model.move(from: from, to: to)
                    }
                } footer: {
                    Text("Ziehen zum Anordnen. Die Reihenfolge gilt in Übersicht und Zählerständen.")
                }
                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .environment(\.editMode, .constant(.active))
            .navigationTitle("Systeme sortieren")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Fertig") { onSaved(); dismiss() }
                }
            }
            .overlay {
                if model.isLoading { ProgressView() }
            }
            .task { await model.load() }
        }
    }
}

@MainActor
@Observable
final class SystemReorderViewModel {
    private let api = APIClient.shared
    private(set) var systems: [MeterSystem] = []
    private(set) var isLoading = false
    var errorMessage: String?

    nonisolated init() {}

    func load() async {
        if systems.isEmpty { isLoading = true }
        defer { isLoading = false }
        do { systems = try await api.fetchSystems() }
        catch { errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription }
    }

    func move(from: IndexSet, to: Int) {
        systems.move(fromOffsets: from, toOffset: to)
        Haptics.tap(.medium)                 // UIImpactFeedbackGenerator beim Ablegen
        let ids = systems.map(\.id)
        Task {
            do { try await api.updateSystemOrder(ids) }
            catch {
                errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
                Haptics.error()
                await load()                 // Serverstand zurückholen (Rollback)
            }
        }
    }
}
