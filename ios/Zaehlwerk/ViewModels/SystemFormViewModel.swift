import SwiftUI

/// ViewModel für Anlegen UND Bearbeiten eines Systems, inkl. typabhängiger
/// Zusatzfelder und Smart-Home-Anbindungen (HA, MQTT/Tasmota/ESPHome, REST).
/// Spiegelt die Web-Maske SystemFormModal.
@MainActor
@Observable
final class SystemFormViewModel {
    private let api = APIClient.shared

    /// Bei nil wird angelegt, sonst das System mit dieser ID geändert.
    let editingID: String?
    private let originalExtra: [String: JSONValue]

    // Stammdaten
    var name = ""
    var type = "Strom"
    var unit = "kWh"
    var color: Color = .blue

    // Kosten & Fälligkeit
    var preis = ""
    var abschlag = ""
    var abrechnungsmonat = ""          // "" | "1"…"12"
    var ableseIntervallTage = ""

    // Typabhängig
    var brennwert = ""
    var zustandszahl = ""
    var kwp = ""
    var verguetungCt = ""

    // Home Assistant
    var haEntity = ""
    var haUnit = ""

    // MQTT / Tasmota / ESPHome
    var mqttTopic = ""
    var mqttPath = ""
    var mqttInterval = ""              // "" = globale Vorgabe

    // REST / HTTP
    var restURL = ""
    var restPath = ""
    var restInterval = ""

    private(set) var isSaving = false
    var errorMessage: String?

    /// Ergebnis eines Live-Bindungstests, für die jeweilige Sektion.
    var haTestResult: String?
    var haTestOK = false
    var restTestResult: String?
    var restTestOK = false
    private(set) var isTestingHA = false
    private(set) var isTestingREST = false

    init(system: MeterSystem? = nil) {
        editingID = system?.id
        originalExtra = system?.extraFields ?? [:]
        if let s = system {
            name = s.name
            type = s.type
            unit = s.unit
            color = SystemStyle.color(s.colorHex)
            let zf = s.extraFields
            preis = Self.numString(zf["preis"])
            abschlag = Self.numString(zf["abschlag"])
            abrechnungsmonat = zf["abrechnungsmonat"]?.stringValue ?? ""
            ableseIntervallTage = Self.numString(zf["ablese_intervall_tage"])
            brennwert = Self.numString(zf["brennwert"])
            zustandszahl = Self.numString(zf["zustandszahl"])
            kwp = Self.numString(zf["kwp"])
            verguetungCt = Self.numString(zf["verguetung_ct"])
            haEntity = zf["ha_entity"]?.stringValue ?? ""
            haUnit = zf["ha_unit"]?.stringValue ?? ""
            mqttTopic = zf["mqtt_topic"]?.stringValue ?? ""
            mqttPath = zf["mqtt_path"]?.stringValue ?? ""
            mqttInterval = zf["mqtt_interval"]?.stringValue ?? ""
            restURL = zf["rest_url"]?.stringValue ?? ""
            restPath = zf["rest_path"]?.stringValue ?? ""
            restInterval = zf["rest_interval"]?.stringValue ?? ""
        }
    }

    var isEditing: Bool { editingID != nil }

    var isValid: Bool {
        !name.trimmingCharacters(in: .whitespaces).isEmpty
            && !unit.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var showsGasFields: Bool {
        type.lowercased().contains("gas") || !brennwert.isEmpty || !zustandszahl.isEmpty
    }

    /// Vorlage anwenden: Einheit/Farbe nur bei leerem Zustand vorbelegen.
    func applyPreset(_ preset: SystemStyle.Preset) {
        type = preset.type
        if unit.trimmingCharacters(in: .whitespaces).isEmpty
            || SystemStyle.presets.contains(where: { $0.unit == unit }) {
            if !preset.unit.isEmpty { unit = preset.unit }
        }
    }

    // MARK: - Speichern

    func save() async -> Bool {
        guard isValid else {
            errorMessage = "Bitte Name und Einheit angeben."
            return false
        }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let zf = buildZusatzfelder()
        let trimmedName = name.trimmingCharacters(in: .whitespaces)
        let trimmedType = type.trimmingCharacters(in: .whitespaces)
        let trimmedUnit = unit.trimmingCharacters(in: .whitespaces)
        let icon = SystemStyle.iconName(for: trimmedType)

        do {
            if let id = editingID {
                _ = try await api.updateSystem(id: id, SystemUpdateRequest(
                    name: trimmedName, typ: trimmedType, einheit: trimmedUnit,
                    farbe: color.hexString, icon: icon, zusatzfelder: zf))
            } else {
                _ = try await api.createSystem(SystemCreateRequest(
                    name: trimmedName, typ: trimmedType, einheit: trimmedUnit,
                    farbe: color.hexString, icon: icon, zusatzfelder: zf))
            }
            Haptics.success()
            return true
        } catch let error as APIError {
            errorMessage = error.errorDescription
            Haptics.error()
            return false
        } catch {
            errorMessage = error.localizedDescription
            Haptics.error()
            return false
        }
    }

    /// Bekannte Schlüssel setzen/entfernen, unbekannte (fremde) bewahren.
    private func buildZusatzfelder() -> [String: JSONValue] {
        var zf = originalExtra
        func setNum(_ key: String, _ text: String) {
            let t = text.replacingOccurrences(of: ",", with: ".").trimmingCharacters(in: .whitespaces)
            if let v = Double(t) { zf[key] = .number(v) } else { zf[key] = nil }
        }
        func setStr(_ key: String, _ text: String) {
            let t = text.trimmingCharacters(in: .whitespaces)
            zf[key] = t.isEmpty ? nil : .string(t)
        }
        setNum("preis", preis)
        setNum("abschlag", abschlag)
        setNum("ablese_intervall_tage", ableseIntervallTage)
        setStr("abrechnungsmonat", abrechnungsmonat)
        setNum("brennwert", brennwert)
        setNum("zustandszahl", zustandszahl)
        setNum("kwp", kwp)
        setNum("verguetung_ct", verguetungCt)
        setStr("ha_entity", haEntity)
        setStr("ha_unit", haUnit)
        setStr("mqtt_topic", mqttTopic)
        setStr("mqtt_path", mqttPath)
        setStr("mqtt_interval", mqttInterval)
        setStr("rest_url", restURL)
        setStr("rest_path", restPath)
        setStr("rest_interval", restInterval)
        return zf
    }

    // MARK: - Live-Test

    func testHA() async {
        let entity = haEntity.trimmingCharacters(in: .whitespaces)
        guard !entity.isEmpty else { return }
        isTestingHA = true; haTestResult = nil
        defer { isTestingHA = false }
        do {
            let r = try await api.testBinding(BindingTestRequest(kind: "ha", entity_id: entity))
            applyTestResult(r, ha: true)
        } catch {
            haTestOK = false
            haTestResult = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func testREST() async {
        let url = restURL.trimmingCharacters(in: .whitespaces)
        guard !url.isEmpty else { return }
        isTestingREST = true; restTestResult = nil
        defer { isTestingREST = false }
        do {
            let path = restPath.trimmingCharacters(in: .whitespaces)
            let r = try await api.testBinding(BindingTestRequest(
                kind: "rest", url: url, path: path.isEmpty ? nil : path))
            applyTestResult(r, ha: false)
        } catch {
            restTestOK = false
            restTestResult = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func applyTestResult(_ r: BindingTestResult, ha: Bool) {
        let ok = r.ok
        let msg: String
        if ok {
            var parts: [String] = []
            if let v = r.value?.stringValue { parts.append(v) }
            if let u = r.unit, !u.isEmpty { parts.append(u) }
            if let p = r.matched_path, !p.isEmpty { parts.append("· \(p)") }
            msg = "Wert: " + parts.joined(separator: " ")
            Haptics.success()
        } else {
            msg = r.error ?? "Kein Wert erkannt"
            Haptics.error()
        }
        if ha { haTestOK = ok; haTestResult = msg } else { restTestOK = ok; restTestResult = msg }
    }

    private static func numString(_ v: JSONValue?) -> String {
        guard let d = v?.doubleValue else { return "" }
        // Ganzzahlen ohne ".0" darstellen.
        return d == d.rounded() ? String(Int(d)) : String(d)
    }
}
