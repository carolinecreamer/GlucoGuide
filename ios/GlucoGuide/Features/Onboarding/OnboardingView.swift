import SwiftUI

struct OnboardingView: View {
    @Environment(AppState.self) private var appState
    @State private var name = ""
    @State private var heightCm = 175.0
    @State private var weightKg = 75.0
    @State private var pumpType = "Manual / not listed"
    @State private var basal = 1.0
    @State private var ratio = 10.0
    @State private var actionHours = 4.0
    @State private var consented = false
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Personal patterns, explained—not autonomous dosing.")
                        .font(.title2.bold())
                    SafetyNotice()
                }

                Section("About you") {
                    TextField("Name", text: $name)
                    TextField("Pump type", text: $pumpType)
                    LabeledContent("Height (cm)") {
                        TextField("Height", value: $heightCm, format: .number)
                            .keyboardType(.decimalPad)
                    }
                    LabeledContent("Weight (kg)") {
                        TextField("Weight", value: $weightKg, format: .number)
                            .keyboardType(.decimalPad)
                    }
                }

                Section("Current prescribed regimen") {
                    LabeledContent("Basal (U/hour)") {
                        TextField("Basal", value: $basal, format: .number)
                            .keyboardType(.decimalPad)
                    }
                    LabeledContent("Insulin:carb (1 unit per g)") {
                        TextField("Ratio", value: $ratio, format: .number)
                            .keyboardType(.decimalPad)
                    }
                    Stepper(
                        "Insulin action: \(actionHours, specifier: "%.1f") hours",
                        value: $actionHours,
                        in: 2...8,
                        step: 0.5
                    )
                }

                Section("Consent") {
                    Toggle(
                        "I understand this app is advisory and does not prescribe or calculate doses.",
                        isOn: $consented
                    )
                }

                if let errorMessage {
                    Text(errorMessage).foregroundStyle(.red)
                }

                Button("Save and continue") {
                    Task { await save() }
                }
                .disabled(!consented || name.isEmpty || isSaving)
            }
            .navigationTitle("Welcome")
        }
    }

    @MainActor
    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let profile = ProfileInput(
                displayName: name,
                heightCm: heightCm,
                weightKg: weightKg,
                pumpType: pumpType,
                insulinActionHours: actionHours,
                glucoseLowThreshold: 70,
                glucoseHighThreshold: 180
            )
            let _: ProfileInput = try await appState.api.put("/api/v1/profile", body: profile)
            let regimen = [
                RegimenInput(
                    startMinute: 0,
                    basalUnitsPerHour: basal,
                    insulinCarbRatio: ratio,
                    correctionFactor: nil,
                    targetGlucose: nil
                )
            ]
            let _: SaveResponse = try await appState.api.put("/api/v1/regimen", body: regimen)
            appState.hasCompletedOnboarding = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct SaveResponse: Codable {
    let saved: Int
}

