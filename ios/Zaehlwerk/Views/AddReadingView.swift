import SwiftUI

/// Formular-Sheet zum Erfassen einer neuen Ablesung. Ruft nach Erfolg den
/// `onSaved`-Callback (Refresh der Detailansicht) und schließt sich.
struct AddReadingView: View {
    @Environment(\.dismiss) private var dismiss
    let system: DashboardSystem
    var onSaved: () -> Void

    @State private var model: AddReadingViewModel

    init(system: DashboardSystem, onSaved: @escaping () -> Void) {
        self.system = system
        self.onSaved = onSaved
        _model = State(initialValue: AddReadingViewModel(systemID: system.id))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    DatePicker("Datum", selection: $model.date, displayedComponents: .date)
                        .datePickerStyle(.compact)

                    HStack {
                        TextField("Zählerstand", text: $model.valueText)
                            .keyboardType(.decimalPad)
                        Text(system.unit).foregroundStyle(.secondary)
                    }
                } header: {
                    Text("Ablesung")
                } footer: {
                    Text("Aktueller Zählerstand in \(system.unit).")
                }

                Section {
                    Toggle("Abrechnung nach Ablesung", isOn: $model.isBilled.animation(.easeInOut))
                    if model.isBilled {
                        HStack {
                            TextField("Abgerechnete Kosten", text: $model.costText)
                                .keyboardType(.decimalPad)
                            Text("€").foregroundStyle(.secondary)
                        }
                        .transition(.move(edge: .top).combined(with: .opacity))
                    }
                    TextField("Notiz", text: $model.note, axis: .vertical)
                        .lineLimit(1...3)
                } footer: {
                    Text("Bei einer Abrechnungsablesung fließen die tatsächlichen Kosten ins Abrechnungsjahr ein.")
                }

                Section {
                    Toggle("Zählertausch", isOn: $model.meterReplaced.animation())
                    if model.meterReplaced {
                        HStack {
                            TextField("Anfangsstand neuer Zähler", text: $model.meterStartText)
                                .keyboardType(.decimalPad)
                            Text(system.unit).foregroundStyle(.secondary)
                        }
                    }
                } footer: {
                    Text("Bei einem Zählertausch wird der Verbrauch korrekt über den Nullpunkt hinweg berechnet.")
                }

                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Neue Ablesung")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Sichern") {
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
        .presentationDetents([.large])
    }
}
