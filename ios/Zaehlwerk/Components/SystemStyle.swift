import SwiftUI

/// Ableitung von SF-Symbol und Farbe aus dem Systemtyp, damit Übersicht,
/// Detail und Verlauf konsistent aussehen – wie eine offizielle Systemapp.
enum SystemStyle {
    static func symbol(for type: String) -> String {
        let value = type.lowercased()
        switch true {
        case value.contains("strom"), value.contains("elektr"): return "bolt.fill"
        case value.contains("gas"):                              return "flame.fill"
        case value.contains("wasser"):                           return "drop.fill"
        case value.contains("pv"), value.contains("solar"), value.contains("photovolt"):
            return "sun.max.fill"
        case value.contains("wärme"), value.contains("waerme"), value.contains("heiz"),
             value.contains("therm"):
            return "thermometer.medium"
        case value.contains("öl"), value.contains("oel"):        return "fuelpump.fill"
        default:                                                 return "gauge.medium"
        }
    }

    /// Farbe aus dem Hex-Wert des Backends, mit sinnvollem Rückfall.
    static func color(_ hex: String?) -> Color {
        Color(hex: hex) ?? .accentColor
    }

    /// Backend-Icon-Token (Feld `icon`), abgeleitet aus dem Typ.
    static func iconName(for type: String) -> String {
        let value = type.lowercased()
        switch true {
        case value.contains("strom"), value.contains("elektr"): return "bolt"
        case value.contains("gas"):                              return "flame"
        case value.contains("wasser"):                           return "droplet"
        case value.contains("pv"), value.contains("solar"), value.contains("photovolt"):
            return "sun"
        case value.contains("wärme"), value.contains("waerme"), value.contains("heiz"),
             value.contains("therm"):
            return "thermometer"
        case value.contains("öl"), value.contains("oel"):        return "fuel"
        default:                                                 return "gauge"
        }
    }

    /// Häufige Systemtypen mit passender Standardeinheit für das Anlege-Formular.
    struct Preset: Identifiable, Hashable {
        let type: String
        let unit: String
        var id: String { type }
    }

    static let presets: [Preset] = [
        Preset(type: "Strom", unit: "kWh"),
        Preset(type: "Gas", unit: "m³"),
        Preset(type: "Wasser", unit: "m³"),
        Preset(type: "Wärmepumpe", unit: "kWh"),
        Preset(type: "PV-Erzeugung", unit: "kWh"),
        Preset(type: "PV-Einspeisung", unit: "kWh"),
        Preset(type: "Heizöl", unit: "l"),
    ]
}
