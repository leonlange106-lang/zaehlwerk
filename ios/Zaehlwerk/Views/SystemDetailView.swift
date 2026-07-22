import SwiftUI

/// Detailansicht eines Systems: Kennzahlen, Verlaufsdiagramm (Statistik) und
/// die Liste der Ablesungen. Neue Ablesung über „+" (nur mit Schreibrecht).
struct SystemDetailView: View {
    @Environment(AuthManager.self) private var auth
    let system: DashboardSystem

    @State private var model: SystemDetailViewModel
    @State private var showingAdd = false

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
            }
        }
        .sheet(isPresented: $showingAdd) {
            AddReadingView(system: system) {
                Task { await model.refresh() }
            }
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
