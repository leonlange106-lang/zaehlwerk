import SwiftUI

/// Übersicht aller Systeme mit Kennzahlen, Miniatur-Verlauf und Prognose.
/// Große Navigationstitel, gruppierter Hintergrund, Karten aus Material.
struct DashboardView: View {
    @Environment(AuthManager.self) private var auth
    @State private var model = DashboardViewModel()
    @State private var showingAddSystem = false

    private var canWrite: Bool { auth.status?.canWrite ?? false }
    private let columns = [GridItem(.adaptive(minimum: 320), spacing: 16)]

    var body: some View {
        NavigationStack {
            ScrollView {
                if model.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, minHeight: 240)
                } else if let message = model.errorMessage, model.systems.isEmpty {
                    ErrorState(message: message) { Task { await model.load() } }
                        .padding(.top, 60)
                } else if model.systems.isEmpty {
                    ContentUnavailableView {
                        Label("Keine Systeme", systemImage: "square.grid.2x2")
                    } description: {
                        Text("Lege ein System an, um hier Kennzahlen zu sehen.")
                    } actions: {
                        if canWrite {
                            Button("System anlegen") {
                                Haptics.tap()
                                showingAddSystem = true
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    }
                    .padding(.top, 60)
                } else {
                    LazyVGrid(columns: columns, spacing: 16) {
                        ForEach(model.systems) { system in
                            NavigationLink {
                                SystemDetailView(system: system)
                            } label: {
                                SystemCard(system: system)
                            }
                            .buttonStyle(.plain)
                            .simultaneousGesture(TapGesture().onEnded { Haptics.selection() })
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 4)
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Übersicht")
            .toolbar {
                if canWrite {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            Haptics.tap()
                            showingAddSystem = true
                        } label: {
                            Image(systemName: "plus")
                        }
                        .accessibilityLabel("System anlegen")
                    }
                }
            }
            .refreshable { await model.refresh() }
            .task { await model.load() }
            .safeAreaInset(edge: .top, spacing: 0) {
                CacheStatusBar(isShowingCached: model.isShowingCached,
                               lastUpdated: model.lastUpdated)
            }
            .sheet(isPresented: $showingAddSystem) {
                SystemFormView {
                    Task { await model.refresh() }
                }
            }
        }
    }
}

/// Eine Systemkarte: Kopf mit Symbol/Name, aktueller Stand, Verbrauch/Kosten,
/// Sparkline und – falls vorhanden – Prognose-Hinweis.
private struct SystemCard: View {
    let system: DashboardSystem

    private var color: Color { SystemStyle.color(system.colorHex) }

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 14) {
                header
                divider
                metrics
                if !system.series.isEmpty {
                    Sparkline(points: system.series, color: color)
                }
                if let prognosis = system.prognosis {
                    PrognosisBadge(prognosis: prognosis, unit: system.unit)
                }
            }
        }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Image(systemName: SystemStyle.symbol(for: system.type))
                .font(.title3)
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(color.gradient, in: RoundedRectangle(cornerRadius: 11, style: .continuous))
            VStack(alignment: .leading, spacing: 2) {
                Text(system.name)
                    .font(.headline)
                    .foregroundStyle(.primary)
                Text(system.type)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.tertiary)
        }
    }

    private var divider: some View {
        Rectangle()
            .fill(Color.primary.opacity(0.06))
            .frame(height: 1)
    }

    private var metrics: some View {
        HStack(alignment: .top) {
            StatTile(
                title: "Aktueller Stand",
                value: Format.value(system.latest, unit: system.unit),
                footnote: Format.date(system.latestDate)
            )
            StatTile(
                title: "Verbrauch",
                value: Format.value(system.totalConsumption, unit: system.unit),
                footnote: "Ø \(Format.value(system.avgPerDay, unit: system.unit))/Tag"
            )
            StatTile(
                title: "Kosten",
                value: Format.cost(system.totalCostTariff ?? system.totalCost)
            )
        }
    }
}

/// Kompakter Prognose-Hinweis; warnt farblich, wenn der Abschlag überschritten wird.
private struct PrognosisBadge: View {
    let prognosis: Prognosis
    let unit: String

    var body: some View {
        let exceeds = prognosis.exceedsAbschlag ?? false
        HStack(spacing: 8) {
            Image(systemName: exceeds ? "exclamationmark.triangle.fill" : "chart.line.uptrend.xyaxis")
                .font(.caption)
                .foregroundStyle(exceeds ? .orange : .secondary)
            VStack(alignment: .leading, spacing: 1) {
                Text("Jahresprognose")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text("\(Format.value(prognosis.projectedConsumption, unit: unit)) · \(Format.cost(prognosis.projectedCost))")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(exceeds ? .orange : .primary)
            }
            Spacer()
        }
        .padding(10)
        .background(
            (exceeds ? Color.orange : Color.secondary).opacity(0.10),
            in: RoundedRectangle(cornerRadius: 12, style: .continuous)
        )
    }
}

/// Wiederverwendbarer Fehlerzustand mit Wiederholen-Aktion.
struct ErrorState: View {
    let message: String
    var retry: () -> Void

    var body: some View {
        ContentUnavailableView {
            Label("Etwas ist schiefgelaufen", systemImage: "wifi.exclamationmark")
        } description: {
            Text(message)
        } actions: {
            Button("Erneut versuchen", action: retry)
                .buttonStyle(.borderedProminent)
        }
    }
}
