import SwiftUI

/// Sheet zum Anlegen/Bearbeiten eines Zählers. Native Parität zur Web-
/// MeterFormModal.
struct MeterFormView: View {
    @Environment(\.dismiss) private var dismiss
    let systemID: String
    let meter: Meter?
    let bauarten: [String]
    var onSaved: () -> Void

    init(systemID: String, meter: Meter? = nil, bauarten: [String], onSaved: @escaping () -> Void) {
        self.systemID = systemID
        self.meter = meter
        self.bauarten = bauarten
        self.onSaved = onSaved
        _model = State(initialValue: MeterFormViewModel(meter: meter))
    }

    @State private var model: MeterFormViewModel

    private var editing: Bool { meter != nil }

    var body: some View {
        NavigationStack {
            Form {
                Section("Zähler") {
                    TextField("Zählernummer", text: $model.zaehlernummer)
                        .textInputAutocapitalization(.characters).autocorrectionDisabled()
                    HStack {
                        TextField("Bauart", text: $model.bauart)
                        if !bauarten.isEmpty {
                            Menu {
                                ForEach(bauarten, id: \.self) { b in
                                    Button(b) { model.bauart = b }
                                }
                            } label: { Image(systemName: "chevron.down.circle") }
                        }
                    }
                    TextField("Hersteller", text: $model.hersteller)
                    TextField("Modell", text: $model.modell)
                }

                Section("Eichung & Technik") {
                    numberField("Baujahr", text: $model.baujahr, placeholder: "2019")
                    DatePicker("Eichung gültig bis", selection: eichungBinding, displayedComponents: .date)
                        .opacity(model.hasEichung ? 1 : 0.6)
                    Toggle("Eichfrist hinterlegt", isOn: $model.hasEichung)
                    numberField("Vorkommastellen", text: $model.stellenVor, placeholder: "6")
                    numberField("Nachkommastellen", text: $model.stellenNach, placeholder: "2")
                }

                Section("Einbau") {
                    TextField("Messstellenbetreiber", text: $model.messstellenbetreiber)
                    optionalDate("Eingebaut am", has: $model.hasEingebaut, date: $model.eingebautAm)
                    optionalDate("Ausgebaut am", has: $model.hasAusgebaut, date: $model.ausgebautAm)
                }

                Section("Notiz") {
                    TextField("Notiz", text: $model.notiz, axis: .vertical).lineLimit(1...4)
                }

                if let message = model.errorMessage {
                    Section { Text(message).foregroundStyle(.red) }
                }
            }
            .navigationTitle(editing ? "Zähler bearbeiten" : "Zähler hinzufügen")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(editing ? "Speichern" : "Hinzufügen") {
                        Task {
                            if await model.save(systemID: systemID) {
                                onSaved(); dismiss()
                            }
                        }
                    }
                    .disabled(model.isSaving)
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

    private var eichungBinding: Binding<Date> {
        Binding(get: { model.eichungBis ?? Date() },
                set: { model.eichungBis = $0; model.hasEichung = true })
    }

    private func numberField(_ title: String, text: Binding<String>, placeholder: String) -> some View {
        HStack {
            Text(title); Spacer()
            TextField(placeholder, text: text)
                .keyboardType(.numberPad).multilineTextAlignment(.trailing).frame(maxWidth: 120)
        }
    }

    private func optionalDate(_ title: String, has: Binding<Bool>, date: Binding<Date?>) -> some View {
        VStack {
            Toggle(title, isOn: has)
            if has.wrappedValue {
                DatePicker(title, selection: Binding(
                    get: { date.wrappedValue ?? Date() }, set: { date.wrappedValue = $0 }),
                    displayedComponents: .date)
                    .labelsHidden()
            }
        }
    }
}

/// ViewModel des Zähler-Formulars.
@MainActor
@Observable
final class MeterFormViewModel {
    private let api = APIClient.shared
    private let editingID: String?

    var hersteller = ""
    var modell = ""
    var zaehlernummer = ""
    var bauart = ""
    var baujahr = ""
    var messstellenbetreiber = ""
    var stellenVor = ""
    var stellenNach = ""
    var notiz = ""

    var hasEichung = false
    var eichungBis: Date?
    var hasEingebaut = false
    var eingebautAm: Date?
    var hasAusgebaut = false
    var ausgebautAm: Date?

    private(set) var isSaving = false
    var errorMessage: String?

    init(meter: Meter?) {
        editingID = meter?.id
        guard let m = meter else { return }
        hersteller = m.hersteller ?? ""
        modell = m.modell ?? ""
        zaehlernummer = m.zaehlernummer ?? ""
        bauart = m.bauart ?? ""
        baujahr = m.baujahr.map(String.init) ?? ""
        messstellenbetreiber = m.messstellenbetreiber ?? ""
        stellenVor = m.stellenVor.map(String.init) ?? ""
        stellenNach = m.stellenNach.map(String.init) ?? ""
        notiz = m.notiz ?? ""
        hasEichung = m.eichungBis != nil; eichungBis = m.eichungBis
        hasEingebaut = m.eingebautAm != nil; eingebautAm = m.eingebautAm
        hasAusgebaut = m.ausgebautAm != nil; ausgebautAm = m.ausgebautAm
    }

    func save(systemID: String) async -> Bool {
        isSaving = true; errorMessage = nil
        defer { isSaving = false }

        func s(_ v: String) -> String? {
            let t = v.trimmingCharacters(in: .whitespaces); return t.isEmpty ? nil : t
        }
        let request = MeterRequest(
            hersteller: s(hersteller), modell: s(modell), zaehlernummer: s(zaehlernummer),
            bauart: s(bauart), baujahr: Int(baujahr),
            eichung_bis: hasEichung ? MeterRequest.day(eichungBis) : nil,
            messstellenbetreiber: s(messstellenbetreiber),
            stellen_vor: Int(stellenVor), stellen_nach: Int(stellenNach),
            eingebaut_am: hasEingebaut ? MeterRequest.day(eingebautAm) : nil,
            ausgebaut_am: hasAusgebaut ? MeterRequest.day(ausgebautAm) : nil,
            notiz: s(notiz))
        do {
            if let id = editingID {
                _ = try await api.updateMeter(id: id, request)
            } else {
                _ = try await api.createMeter(systemID: systemID, request)
            }
            Haptics.success()
            return true
        } catch {
            errorMessage = (error as? APIError)?.errorDescription ?? error.localizedDescription
            Haptics.error()
            return false
        }
    }
}
