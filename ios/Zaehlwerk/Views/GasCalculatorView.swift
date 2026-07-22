import SwiftUI

/// Gas-Rechner: rechnet m³ ↔ kWh (kWh = m³ × Brennwert × Zustandszahl).
/// Zwei-Wege-Bindung – die Eingabe auf einer Seite aktualisiert die andere. Der
/// kWh-Wert wird groß in SF-Rundschrift dargestellt.
struct GasCalculatorView: View {
    @State private var cubicMeters: Double = 100
    @State private var brennwert: Double = 11.0
    @State private var zustandszahl: Double = 0.95

    private var factor: Double { brennwert * zustandszahl }
    private var kWh: Double { cubicMeters * factor }

    // Zwei-Wege-Bindung: kWh bearbeiten schreibt m³ zurück.
    private var kWhBinding: Binding<Double> {
        Binding(
            get: { kWh },
            set: { newValue in cubicMeters = factor > 0 ? newValue / factor : 0 }
        )
    }

    var body: some View {
        Form {
            Section("Verbrauch") {
                HStack {
                    Text("m³")
                    Spacer()
                    TextField("m³", value: $cubicMeters, format: .number.precision(.fractionLength(0...3)))
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                }
                HStack {
                    Text("kWh")
                    Spacer()
                    TextField("kWh", value: kWhBinding, format: .number.precision(.fractionLength(0...1)))
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                }
            }

            Section {
                VStack(spacing: 4) {
                    Text(kWh, format: .number.precision(.fractionLength(0...1)))
                        .font(.system(size: 52, weight: .bold, design: .rounded))
                        .monospacedDigit()
                        .minimumScaleFactor(0.5)
                        .lineLimit(1)
                    Text("kWh")
                        .font(.title3.weight(.medium))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
            } footer: {
                Text("kWh = m³ × Brennwert × Zustandszahl = m³ × \(factor, format: .number.precision(.fractionLength(0...3)))")
            }

            Section("Parameter") {
                Stepper(value: $brennwert, in: 8...14, step: 0.1) {
                    LabeledContent("Brennwert (kWh/m³)",
                                   value: brennwert, format: .number.precision(.fractionLength(0...1)))
                }
                Stepper(value: $zustandszahl, in: 0.8...1.0, step: 0.01) {
                    LabeledContent("Zustandszahl",
                                   value: zustandszahl, format: .number.precision(.fractionLength(0...2)))
                }
            }
        }
        .navigationTitle("Gas-Rechner")
        .navigationBarTitleDisplayMode(.inline)
    }
}
