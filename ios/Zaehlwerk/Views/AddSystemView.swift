import SwiftUI

/// Formular-Sheet zum Anlegen eines neuen Systems. Typ-Vorlagen füllen die
/// passende Standardeinheit vor; Name, Typ und Einheit bleiben frei editierbar.
struct AddSystemView: View {
    @Environment(\.dismiss) private var dismiss
    var onSaved: () -> Void

    @State private var model = AddSystemViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Vorlage") {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            ForEach(SystemStyle.presets) { preset in
                                PresetChip(
                                    preset: preset,
                                    isSelected: model.type == preset.type
                                ) {
                                    Haptics.selection()
                                    model.type = preset.type
                                    model.unit = preset.unit
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listRowInsets(EdgeInsets(top: 4, leading: 12, bottom: 4, trailing: 12))
                }

                Section("System") {
                    TextField("Name (z. B. Zähler Keller)", text: $model.name)
                    TextField("Typ (z. B. Strom)", text: $model.type)
                    TextField("Einheit (z. B. kWh)", text: $model.unit)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    ColorPicker("Farbe", selection: $model.color, supportsOpacity: false)
                }

                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Neues System")
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
    }
}

private struct PresetChip: View {
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
