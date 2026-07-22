import SwiftUI

/// Detailansicht eines Systems: Kennzahlen, Verlaufsdiagramm (Statistik) und
/// die Liste der Ablesungen. Neue Ablesung über „+" (nur mit Schreibrecht).
struct SystemDetailView: View {
    @Environment(AuthManager.self) private var auth
    let system: DashboardSystem

    @Environment(\.dismiss) private var dismiss

    @State private var model: SystemDetailViewModel
    @State private var showingAdd = false
    @State private var editSystem: MeterSystem?
    @State private var showingDeleteConfirm = false

    init(system: DashboardSystem) {
        self.system = system
        _model = State(initialValue: SystemDetailViewModel(systemID: system.id))
    }

    private var color: Color { SystemStyle.color(system.colorHex) }
    private var canWrite: Bool { auth.status?.canWrite ?? false }

    var body: some View {
        List {
            statsSection
            chartSection
            metersSection
            readingsSection
        }
        .listStyle(.insetGrouped)
        .navigationTitle(system.name)
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            if canWrite {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Haptics.tap()
                        showingAdd = true
                    } label: {
                        Image(systemName: "plus")
                    }
                    .accessibilityLabel("Ablesung hinzufügen")
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button {
                            Task {
                                Haptics.tap()
                                editSystem = await model.loadEditableSystem()
                            }
                        } label: { Label("Bearbeiten", systemImage: "pencil") }
                        Button {
                            Task {
                                if await model.archive() { dismiss() }
                            }
                        } label: { Label("Archivieren", systemImage: "archivebox") }
                        Divider()
                        Button(role: .destructive) {
                            showingDeleteConfirm = true
                        } label: { Label("Löschen …", systemImage: "trash") }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                    .accessibilityLabel("Systemaktionen")
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            AddReadingView(system: system) {
                Task { await model.refresh() }
            }
        }
        .sheet(item: $editSystem) { editable in
            SystemFormView(system: editable) {
                Task { await model.refresh() }
            }
        }
        .confirmationDialog(
            "System „\(system.name)" mit ALLEN Ablesungen und Zählern endgültig löschen?",
            isPresented: $showingDeleteConfirm, titleVisibility: .visible
        ) {
            Button("Endgültig löschen", role: .destructive) {
                Task { if await model.deleteSystem() { dismiss() } }
            }
            Button("Abbrechen", role: .cancel) {}
        }
        .refreshable { await model.refresh() }
        .task { await model.load() }
        .safeAreaInset(edge: .top, spacing: 0) {
            CacheStatusBar(isShowingCached: model.isShowingCached,
                           lastUpdated: model.lastUpdated)
        }
        .overlay {
            if model.isLoading { ProgressView() }
        }
    }

    // MARK: - Zähler-Metadaten

    private var metersSection: some View {
        Section {
            NavigationLink {
                MetersView(systemID: system.id)
            } label: {
                Label("Zähler verwalten", systemImage: "gauge.medium")
            }
            NavigationLink {
                ReportViewerView(systemID: system.id, systemName: system.name)
            } label: {
                Label("PDF-Bericht", systemImage: "doc.text")
            }
        }
    }

    // MARK: - Kennzahlen

    @ViewBuilder
    private var statsSection: some View {
        if let stats = model.stats {
            Section("Kennzahlen") {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                    StatTile(title: "Gesamtverbrauch",
                             value: Format.value(stats.totalConsumption, unit: system.unit),
                             systemImage: SystemStyle.symbol(for: system.type), tint: color)
                    StatTile(title: "Ø pro Tag",
                             value: Format.value(stats.avgPerDay, unit: system.unit),
                             systemImage: "calendar", tint: color)
                    StatTile(title: "Kosten gesamt",
                             value: Format.cost(stats.totalCostTariff ?? stats.totalCost),
                             systemImage: "eurosign.circle", tint: color)
                    StatTile(title: "Preis/Einheit",
                             value: Format.cost(stats.costPerUnit),
                             footnote: "je \(system.unit)",
                             systemImage: "tag", tint: color)
                }
                .padding(.vertical, 4)
            }
        }
    }

    // MARK: - Diagramm

    @ViewBuilder
    private var chartSection: some View {
        if let chart = model.chart {
            Section("Verlauf") {
                ConsumptionChartView(chart: chart, color: color)
                    .padding(.vertical, 4)
            }
        }
    }

    // MARK: - Ablesungen

    @ViewBuilder
    private var readingsSection: some View {
        Section("Ablesungen") {
            if model.readings.isEmpty && !model.isLoading {
                Text("Noch keine Ablesungen erfasst.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(model.readings) { reading in
                    ReadingRow(reading: reading, unit: system.unit)
                        .swipeActions(edge: .trailing) {
                            if canWrite {
                                Button(role: .destructive) {
                                    Task { await model.deleteReading(reading) }
                                } label: {
                                    Label("Löschen", systemImage: "trash")
                                }
                            }
                        }
                }
            }
        }
    }
}

/// Eine Zeile in der Ablesungsliste.
private struct ReadingRow: View {
    let reading: Reading
    let unit: String

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 3) {
                Text(Format.value(reading.value, unit: unit))
                    .font(.body.weight(.medium))
                HStack(spacing: 6) {
                    Text(Format.date(reading.date))
                    if reading.meterReplaced {
                        Label("Zählertausch", systemImage: "arrow.triangle.2.circlepath")
                            .labelStyle(.iconOnly)
                            .foregroundStyle(.orange)
                    }
                    if reading.isOutlier {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                    }
                    SourceBadge(source: reading.source)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
            Spacer()
            if let perDay = reading.consumptionPerDay {
                VStack(alignment: .trailing, spacing: 2) {
                    Text("\(Format.number(perDay))")
                        .font(.subheadline.weight(.semibold))
                        .monospacedDigit()
                    Text("\(unit)/Tag")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 2)
    }
}

/// Kleiner Herkunfts-Chip (manuell, HA, MQTT, Import).
private struct SourceBadge: View {
    let source: String

    private var label: String {
        switch source {
        case "manual": return "manuell"
        case "ha_api": return "HA"
        case "mqtt":   return "MQTT"
        case "import": return "Import"
        default:        return source
        }
    }

    var body: some View {
        Text(label)
            .font(.caption2)
            .padding(.horizontal, 6)
            .padding(.vertical, 1)
            .background(Color.secondary.opacity(0.15), in: Capsule())
    }
}
