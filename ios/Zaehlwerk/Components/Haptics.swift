import UIKit

/// Dezente haptische Rückmeldungen im Stil der Apple-Systemapps.
/// Bewusst zurückhaltend eingesetzt: nur bei bewussten Aktionen (Speichern,
/// Auswahl, Fehler), nie bei reinem Scrollen oder Laden.
enum Haptics {
    static func tap(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .light) {
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.prepare()
        generator.impactOccurred()
    }

    static func selection() {
        UISelectionFeedbackGenerator().selectionChanged()
    }

    static func success() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    static func warning() {
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
    }

    static func error() {
        UINotificationFeedbackGenerator().notificationOccurred(.error)
    }
}
