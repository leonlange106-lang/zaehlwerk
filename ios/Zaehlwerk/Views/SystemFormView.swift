import SwiftUI

/// Sheet zum Anlegen ODER Bearbeiten eines Systems – mit Typ-Vorlagen,
/// typabhängigen Feldern und Smart-Home-Anbindungen (HA, MQTT/Tasmota/ESPHome,
/// REST). Native Parität zur Web-Maske SystemFormModal.
struct SystemFormView: View {
    @Environment(\.dismiss) private var dismiss
    var onSaved: () -> Void

    @State private var model: SystemFormViewModel

    init(system: MeterSystem? = nil, onSaved: @escaping () -> Void) {
        self.onSaved = onSaved
        _model = State(initialValue: SystemFormViewModel(system: system))
    }

    var body: some View {
        NavigationStack {
            Form {
                templateSection
                baseSection
                if model.showsGasFields { gasSection }
                if model.type == "PV-Erzeugung" { pvErzeugungSection }
                if model.type == "PV-Einspeisung" { pvEinspeisungSection }
                costSection
                homeAssistantSection
                mqttSection
                restSection

                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle(model.isEditing ? "System bearbeiten" : "Neues System")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(model.isEditing ? "Speichern" : "Sichern") {
                        Task {
                            if await model.save() {
                                onSaved()
                                dismiss()
                            }
                        }
                    }
                    .disabled(!model.isValid || model.isSaving)
                }
            }
            .overlay {
                if model.isSaving {
                    ProgressView().padding(24)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                }
            }
        }
    }

    // MARK: - Sektionen

    private var templateSection: some View {
        Section("Vorlage") {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(SystemStyle.presets) { preset in
                        PresetChip(preset: preset, isSelected: model.type == preset.type) {
                            Haptics.selection()
                            model.applyPreset(preset)
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            .listRowInsets(EdgeInsets(top: 4, leading: 12, bottom: 4, trailing: 12))
        }
    }

    private var baseSection: some View {
        Section("System") {
            TextField("Name (z. B. Strom Hauptzähler)", text: $model.name)
            TextField("Zählertyp", text: $model.type)
            TextField("Einheit (z. B. kWh)", text: $model.unit)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            ColorPicker("Farbe", selection: $model.color, supportsOpacity: false)
        }
    }

    private var gasSection: some View {
        Section("Gas") {
            numberRow("Brennwert (kWh/m³)", text: $model.brennwert, placeholder: "11,0")
            numberRow("Zustandszahl", text: $model.zustandszahl, placeholder: "0,95")
        }
    }

    private var pvErzeugungSection: some View {
        Section("Photovoltaik") {
            numberRow("Installierte Leistung (kWp)", text: $model.kwp, placeholder: "9,8")
        }
    }

    private var pvEinspeisungSection: some View {
        Section("Einspeisung") {
            numberRow("Vergütung (ct/kWh)", text: $model.verguetungCt, placeholder: "8,2")
        }
    }

    private var costSection: some View {
        Section("Kosten & Fälligkeit") {
            numberRow("Ø-Preis €/Einheit", text: $model.preis, placeholder: "0,32")
            numberRow("Monatl. Abschlag €", text: $model.abschlag, placeholder: "90")
            Picker("Abrechnungsjahr beginnt", selection: $model.abrechnungsmonat) {
                Text("Januar (Kalenderjahr)").tag("")
                ForEach(1...12, id: \.self) { m in
                    Text(Self.monthNames[m - 1]).tag(String(m))
                }
            }
            numberRow("Ablese-Intervall (Tage)", text: $model.ableseIntervallTage, placeholder: "365")
        }
    }

    private var homeAssistantSection: some View {
        Section {
            TextField("Entity (sensor.stromzaehler)", text: $model.haEntity)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            Picker("Einheit des HA-Sensors", selection: $model.haUnit) {
                Text("wie von HA gemeldet").tag("")
                ForEach(["Wh", "kWh", "MWh", "L", "m³"], id: \.self) { Text($0).tag($0) }
            }
            testRow(
                title: "Testen", isBusy: model.isTestingHA,
                disabled: model.haEntity.trimmingCharacters(in: .whitespaces).isEmpty,
                result: model.haTestResult, ok: model.haTestOK
            ) { await model.testHA() }
        } header: {
            Label("Home Assistant", systemImage: "house")
        }
    }

    private var mqttSection: some View {
        Section {
            HStack(spacing: 12) {
                Text("Vorschlag").font(.caption).foregroundStyle(.secondary)
                Button("Tasmota") { model.mqttTopic = "tele/GERAET/SENSOR" }.font(.caption)
                Button("ESPHome") { model.mqttTopic = "NODE/sensor/NAME/state"; model.mqttPath = "" }.font(.caption)
            }
            TextField("MQTT-Topic (tele/hichi/SENSOR)", text: $model.mqttTopic)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            TextField("JSON-Pfad (optional, MT631.Total_in)", text: $model.mqttPath)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            intervalPicker(selection: $model.mqttInterval)
            Text("MQTT wird vom Broker gepusht – ein Live-Test ist erst nach dem Speichern über die Geräteverwaltung möglich.")
                .font(.caption).foregroundStyle(.secondary)
        } header: {
            Label("MQTT · Tasmota · ESPHome", systemImage: "antenna.radiowaves.left.and.right")
        }
    }

    private var restSection: some View {
        Section {
            HStack(spacing: 12) {
                Text("Vorschlag").font(.caption).foregroundStyle(.secondary)
                Button("ESPHome") { model.restURL = "http://GERAET.local/sensor/NAME" }.font(.caption)
                Button("Shelly") { model.restURL = "http://GERAET.local/rpc/Switch.GetStatus?id=0"; model.restPath = "aenergy.total" }.font(.caption)
            }
            TextField("URL (http://192.168.1.50/sensor/strom)", text: $model.restURL)
                .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
            TextField("JSON-Pfad (optional, sensor.total.value)", text: $model.restPath)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            intervalPicker(selection: $model.restInterval)
            testRow(
                title: "Testen", isBusy: model.isTestingREST,
                disabled: model.restURL.trimmingCharacters(in: .whitespaces).isEmpty,
                result: model.restTestResult, ok: model.restTestOK
            ) { await model.testREST() }
        } header: {
            Label("REST / HTTP (ESPHome web_server, Shelly)", systemImage: "globe")
        }
    }

    // MARK: - Bausteine

    private func numberRow(_ title: String, text: Binding<String>, placeholder: String) -> some View {
        HStack {
            Text(title)
            Spacer()
            TextField(placeholder, text: text)
                .keyboardType(.decimalPad)
                .multilineTextAlignment(.trailing)
                .frame(maxWidth: 140)
        }
    }

    private func intervalPicker(selection: Binding<String>) -> some View {
        Picker("Speicherintervall", selection: selection) {
            Text("Globale Vorgabe").tag("")
            Text("Täglich").tag("daily")
            Text("Wöchentlich").tag("weekly")
            Text("Monatlich").tag("monthly")
            Text("Quartalsweise").tag("quarterly")
            Text("Jährlich").tag("yearly")
        }
    }

    private func testRow(
        title: String, isBusy: Bool, disabled: Bool,
        result: String?, ok: Bool, action: @escaping () async -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Button {
                    Task { await action() }
                } label: {
                    if isBusy { ProgressView() } else { Text(title) }
                }
                .disabled(disabled || isBusy)
                Spacer()
            }
            if let result {
                Label(result, systemImage: ok ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .font(.caption)
                    .foregroundStyle(ok ? .green : .red)
            }
        }
    }

    private static let monthNames = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                                     "Juli", "August", "September", "Oktober", "November", "Dezember"]
}

/// Auswahl-Chip für die Typ-Vorlagen (horizontaler Picker).
struct PresetChip: View {
    let preset: SystemStyle.Preset
    let isSelected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(preset.type, systemImage: SystemStyle.symbol(for: preset.type))
                .font(.subheadline)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    isSelected ? AnyShapeStyle(Color.accentColor.opacity(0.18))
                               : AnyShapeStyle(.thinMaterial),
                    in: Capsule()
                )
                .overlay(
                    Capsule().strokeBorder(
                        isSelected ? Color.accentColor : .clear, lineWidth: 1
                    )
                )
        }
        .buttonStyle(.plain)
    }
}
