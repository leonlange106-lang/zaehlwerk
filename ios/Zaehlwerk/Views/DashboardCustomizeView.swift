import SwiftUI

/// Bearbeitungs-Sheet des Dashboards: Kacheln anordnen (.onMove), hinzufügen,
/// entfernen und je Kachel konfigurieren. Native Parität zum Web-Edit-Mode.
struct DashboardCustomizeView: View {
    @Environment(\.dismiss) private var dismiss
    let systems: [DashboardSystem]
    var onSaved: () -> Void

    @State private var model: DashboardCustomizeViewModel

    init(tiles: [DashboardTile], systems: [DashboardSystem], onSaved: @escaping () -> Void) {
        self.systems = systems
        self.onSaved = onSaved
        _model = State(initialValue: DashboardCustomizeViewModel(tiles: tiles))
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach($model.tiles) { $tile in
                        NavigationLink {
                            TileConfigView(tile: $tile, systems: systems)
                        } label: {
                            Label {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(tile.title?.isEmpty == false ? tile.title! : tile.type.label)
                                    Text("Breite \(tile.w) · Höhe \(tile.h)")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            } icon: {
                                Image(systemName: tile.type.symbol)
                            }
                        }
                    }
                    .onMove { model.tiles.move(fromOffsets: $0, toOffset: $1); Haptics.selection() }
                    .onDelete { model.tiles.remove(atOffsets: $0) }
                } footer: {
                    Text("Ziehen zum Anordnen, wischen zum Entfernen. Tippen für Einstellungen.")
                }

                Section {
                    Menu {
                        ForEach(TileType.allCases, id: \.self) { type in
                            Button {
                                model.addTile(type, defaultSystemID: systems.first?.id)
                                Haptics.tap()
                            } label: { Label(type.label, systemImage: type.symbol) }
                        }
                    } label: {
                        Label("Kachel hinzufügen", systemImage: "plus")
                    }
                    Button(role: .destructive) {
                        Task { if await model.reset() { onSaved(); dismiss() } }
                    } label: {
                        Label("Auf Standard zurücksetzen", systemImage: "arrow.counterclockwise")
                    }
                }

                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .environment(\.editMode, .constant(.active))
            .navigationTitle("Dashboard anpassen")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        Task { if await model.save() { onSaved(); dismiss() } }
                    }
                    .disabled(model.isSaving)
                }
            }
        }
    }
}

/// Konfiguration einer einzelnen Kachel.
private struct TileConfigView: View {
    @Binding var tile: DashboardTile
    let systems: [DashboardSystem]

    var body: some View {
        Form {
            Section("Allgemein") {
                TextField("Titel", text: Binding(
                    get: { tile.title ?? "" }, set: { tile.title = $0.isEmpty ? nil : $0 }))
                Picker("Typ", selection: $tile.type) {
                    ForEach(TileType.allCases, id: \.self) { Text($0.label).tag($0) }
                }
            }

            Section("Systeme") {
                if tile.type.allowsMultiple {
                    ForEach(systems) { s in
                        Toggle(s.name, isOn: Binding(
                            get: { tile.resolvedSystemIDs().contains(s.id) },
                            set: { on in
                                var ids = tile.systemIDs.isEmpty
                                    ? (tile.systemID.map { [$0] } ?? []) : tile.systemIDs
                                if on { if !ids.contains(s.id) { ids.append(s.id) } }
                                else { ids.removeAll { $0 == s.id } }
                                tile.systemIDs = ids
                                tile.systemID = ids.first
                            }))
                    }
                } else {
                    Picker("System", selection: Binding(
                        get: { tile.systemID ?? "" },
                        set: { tile.systemID = $0.isEmpty ? nil : $0; tile.systemIDs = $0.isEmpty ? [] : [$0] })) {
                        Text("—").tag("")
                        ForEach(systems) { Text($0.name).tag($0.id) }
                    }
                }
            }

            if tile.type == .lineChart || tile.type == .trend {
                Section("Zeitraum") {
                    Picker("Zeitraum", selection: $tile.timeframe) {
                        ForEach(Timeframe.allCases.filter { $0 != .custom }, id: \.self) {
                            Text($0.label).tag($0)
                        }
                    }
                }
            }

            Section("Größe") {
                Stepper("Breite: \(tile.w)", value: $tile.w, in: 1...4)
                Stepper("Höhe: \(tile.h)", value: $tile.h, in: 1...3)
            }
        }
        .navigationTitle(tile.type.label)
        .navigationBarTitleDisplayMode(.inline)
    }
}

@MainActor
@Observable
final class DashboardCustomizeViewModel {
    private let api = APIClient.shared
    var tiles: [DashboardTile]
    private(set) var isSaving = false
    var errorMessage: String?

    init(tiles: [DashboardTile]) {
        self.tiles = tiles
    }

    func addTile(_ type: TileType, defaultSystemID: String?) {
        let id = "w_\(type.rawValue)_\(Int(Date().timeIntervalSince1970 * 1000))"
        tiles.append(DashboardTile(
            id: id, type: type,
            w: type == .lineChart ? 2 : 1,
            h: (type == .lineChart || type == .pieChart) ? 2 : 1,
            systemID: type.allowsMultiple ? nil : defaultSystemID,
            timeframe: .m12))
    }

    /// Kacheln links-nach-rechts packen und daraus x/y ableiten (Backend prüft
    /// x+w <= 4).
    private func repacked() -> [DashboardTile] {
        var cx = 0, cy = 0
        return tiles.map { tile in
            var t = tile
            let w = min(max(t.w, 1), 4)
            if cx + w > 4 { cx = 0; cy += 1 }
            t.w = w; t.x = cx; t.y = cy
            cx += w
            return t
        }
    }

    func save() async -> Bool {
        isSaving = true; errorMessage = nil
        defer { isSaving = false }
        do {
            _ = try await api.saveDashboardLayout(repacked())
            Haptics.success()
            return true
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return false
        }
    }

    func reset() async -> Bool {
        do {
            try await api.resetDashboardLayout()
            Haptics.success()
            return true
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return false
        }
    }
}
