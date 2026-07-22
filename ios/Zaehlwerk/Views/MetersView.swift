import SwiftUI

/// Zähler-Metadaten eines Systems (Hersteller, Modell, Nummer, Eichfrist).
/// Rein dokumentarisch. Native Parität zur Web-MetersCard.
struct MetersView: View {
    @Environment(AuthManager.self) private var auth
    @State private var model: MetersViewModel
    @State private var editMeter: Meter?
    @State private var showingAdd = false

    init(systemID: String) {
        _model = State(initialValue: MetersViewModel(systemID: systemID))
    }

    private var canWrite: Bool { auth.status?.canWrite ?? false }

    var body: some View {
        List {
            if model.meters.isEmpty && !model.isLoading {
                ContentUnavailableView("Kein Zähler hinterlegt",
                                       systemImage: "gauge.medium",
                                       description: Text("Füge Hersteller, Nummer und Eichfrist hinzu."))
            }
            ForEach(model.meters) { meter in
                Button {
                    if canWrite { editMeter = meter }
                } label: {
                    MeterRow(meter: meter)
                }
                .buttonStyle(.plain)
                .swipeActions(edge: .trailing) {
                    if canWrite {
                        Button(role: .destructive) {
                            Task { await model.delete(meter) }
                        } label: { Label("Löschen", systemImage: "trash") }
                    }
                }
            }
        }
        .navigationTitle("Zähler")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if canWrite {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Haptics.tap()
                        showingAdd = true
                    } label: { Image(systemName: "plus") }
                    .accessibilityLabel("Zähler hinzufügen")
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            MeterFormView(systemID: model.systemID, bauarten: model.bauarten) {
                Task { await model.refresh() }
            }
        }
        .sheet(item: $editMeter) { meter in
            MeterFormView(systemID: model.systemID, meter: meter, bauarten: model.bauarten) {
                Task { await model.refresh() }
            }
        }
        .overlay { if model.isLoading { ProgressView() } }
        .task { await model.load() }
        .refreshable { await model.refresh() }
    }
}

private struct MeterRow: View {
    let meter: Meter

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(meter.zaehlernummer ?? "Ohne Nummer")
                    .font(.headline)
                if !meter.aktiv {
                    Text("ausgebaut").font(.caption2)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(.thinMaterial, in: Capsule())
                }
                Spacer()
                calibration
            }
            let subtitle = [meter.hersteller, meter.modell, meter.bauart]
                .compactMap { $0 }.joined(separator: " · ")
            if !subtitle.isEmpty {
                Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    @ViewBuilder private var calibration: some View {
        if meter.eichungBis != nil {
            let days = meter.eichungFaelligInTagen
            if meter.eichungAbgelaufen {
                label("Eichung abgelaufen", .red)
            } else if let d = days, d <= 90 {
                label("Eichung in \(d) T", .orange)
            }
        }
    }

    private func label(_ text: String, _ color: Color) -> some View {
        Text(text).font(.caption2.weight(.medium)).foregroundStyle(color)
    }
}
