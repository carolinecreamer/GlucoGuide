import SwiftUI

struct LogsView: View {
    var body: some View {
        NavigationStack {
            List {
                NavigationLink {
                    MealLogView()
                } label: {
                    Label("Meal", systemImage: "fork.knife")
                }
                NavigationLink {
                    ExerciseLogView()
                } label: {
                    Label("Exercise", systemImage: "figure.run")
                }
                NavigationLink {
                    DoseLogView()
                } label: {
                    Label("Insulin", systemImage: "syringe")
                }
            }
            .navigationTitle("Log")
        }
    }
}

private struct MealLogView: View {
    @Environment(AppState.self) private var appState
    @State private var name = ""
    @State private var carbs = 0.0
    @State private var protein = 0.0
    @State private var fat = 0.0
    @State private var guidance: Guidance?
    @State private var message: String?

    var body: some View {
        Form {
            TextField("Meal name", text: $name)
            macroField("Carbohydrate (g)", value: $carbs)
            macroField("Protein (g)", value: $protein)
            macroField("Fat (g)", value: $fat)
            Button("Compare with prior meals") {
                Task { await checkGuidance() }
            }
            .disabled(name.isEmpty)
            Button("Save meal") {
                Task { await save() }
            }
            .disabled(name.isEmpty)
            if let guidance {
                Section(guidance.headline) {
                    ForEach(guidance.guidance, id: \.self) { Text($0) }
                    ForEach(guidance.evidence, id: \.self) { item in
                        Label(item, systemImage: "clock.arrow.circlepath")
                    }
                    Text(guidance.uncertainty).font(.caption).foregroundStyle(.secondary)
                    Text(guidance.emergencyNote).font(.caption).foregroundStyle(.orange)
                }
            }
            if let message { Text(message) }
        }
        .navigationTitle("Meal")
    }

    private func macroField(_ title: String, value: Binding<Double>) -> some View {
        LabeledContent(title) {
            TextField(title, value: value, format: .number)
                .keyboardType(.decimalPad)
        }
    }

    @MainActor
    private func checkGuidance() async {
        do {
            guidance = try await appState.api.post(
                "/api/v1/guidance/meals",
                body: MealGuidanceInput(
                    name: name,
                    carbsG: carbs,
                    proteinG: protein,
                    fatG: fat,
                    fiberG: 0
                )
            )
        } catch {
            message = error.localizedDescription
        }
    }

    @MainActor
    private func save() async {
        do {
            let input = MealInput(
                occurredAt: .now,
                name: name,
                carbsG: carbs,
                proteinG: protein,
                fatG: fat,
                fiberG: 0,
                notes: nil
            )
            let _: IdentifierResponse = try await appState.api.post(
                "/api/v1/logs/meals",
                body: input
            )
            message = "Meal saved."
        } catch {
            message = error.localizedDescription
        }
    }
}

private struct ExerciseLogView: View {
    @Environment(AppState.self) private var appState
    @State private var exerciseType = "Walking"
    @State private var intensity = "moderate"
    @State private var duration = 30
    @State private var guidance: Guidance?
    @State private var message: String?

    var body: some View {
        Form {
            TextField("Exercise type", text: $exerciseType)
            Picker("Intensity", selection: $intensity) {
                Text("Low").tag("low")
                Text("Moderate").tag("moderate")
                Text("High").tag("high")
            }
            Stepper("Duration: \(duration) minutes", value: $duration, in: 5...300, step: 5)
            Button("Check before exercise") {
                Task { await checkGuidance() }
            }
            Button("Save exercise") {
                Task { await save() }
            }
            if let guidance {
                Section(guidance.headline) {
                    ForEach(guidance.guidance, id: \.self) { Text($0) }
                    Text(guidance.uncertainty).font(.caption).foregroundStyle(.secondary)
                    Text(guidance.emergencyNote).font(.caption).foregroundStyle(.orange)
                }
            }
            if let message { Text(message) }
        }
        .navigationTitle("Exercise")
    }

    @MainActor
    private func checkGuidance() async {
        do {
            guidance = try await appState.api.post(
                "/api/v1/guidance/exercise",
                body: ExerciseGuidanceInput(
                    plannedAt: .now,
                    exerciseType: exerciseType,
                    intensity: intensity,
                    durationMinutes: duration
                )
            )
        } catch {
            message = error.localizedDescription
        }
    }

    @MainActor
    private func save() async {
        do {
            let _: IdentifierResponse = try await appState.api.post(
                "/api/v1/logs/exercise",
                body: ExerciseInput(
                    occurredAt: .now,
                    exerciseType: exerciseType,
                    intensity: intensity,
                    durationMinutes: duration,
                    notes: nil
                )
            )
            message = "Exercise saved."
        } catch {
            message = error.localizedDescription
        }
    }
}

private struct DoseLogView: View {
    @Environment(AppState.self) private var appState
    @State private var units = 0.0
    @State private var doseType = "bolus"
    @State private var message: String?

    var body: some View {
        Form {
            LabeledContent("Units") {
                TextField("Units", value: $units, format: .number)
                    .keyboardType(.decimalPad)
            }
            Picker("Type", selection: $doseType) {
                Text("Meal bolus").tag("bolus")
                Text("Correction").tag("correction")
                Text("Basal").tag("basal")
            }
            Button("Save insulin") {
                Task {
                    do {
                        let _: IdentifierResponse = try await appState.api.post(
                            "/api/v1/logs/doses",
                            body: DoseInput(
                                occurredAt: .now,
                                units: units,
                                doseType: doseType,
                                notes: nil
                            )
                        )
                        message = "Insulin saved."
                    } catch {
                        message = error.localizedDescription
                    }
                }
            }
            .disabled(units <= 0)
            if let message { Text(message) }
        }
        .navigationTitle("Insulin")
    }
}

private struct IdentifierResponse: Codable {
    let id: String
}
