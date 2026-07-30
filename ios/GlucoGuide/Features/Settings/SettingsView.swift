import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @Environment(\.openURL) private var openURL
    @State private var apiURL = ""
    @State private var message: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend") {
                    TextField("API URL", text: $apiURL)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                    Button("Save API URL") {
                        appState.apiBaseURL = apiURL
                        message = "API URL saved."
                    }
                }

                Section("Dexcom") {
                    Button("Connect Dexcom sandbox") {
                        Task {
                            do {
                                let start: DexcomStart = try await appState.api.get(
                                    "/api/v1/integrations/dexcom/start"
                                )
                                openURL(start.authorizationUrl)
                            } catch {
                                message = error.localizedDescription
                            }
                        }
                    }
                    Button("Synchronize glucose") {
                        Task {
                            do {
                                let result: CountResponse = try await appState.api.post(
                                    "/api/v1/integrations/dexcom/sync",
                                    body: EmptySettingsBody()
                                )
                                let count = result.inserted ?? 0
                                message = count == 0
                                    ? "Glucose is already up to date; no new readings were returned."
                                    : "Imported \(count) new readings."
                            } catch {
                                message = error.localizedDescription
                            }
                        }
                    }
                    Button("Load local sample data") {
                        Task {
                            do {
                                let result: CountResponse = try await appState.api.post(
                                    "/api/v1/sample-data",
                                    body: EmptySettingsBody()
                                )
                                let count = result.created ?? 0
                                message = count == 0
                                    ? "Existing glucose data was kept; sample data was not added."
                                    : "Created \(count) sample readings."
                            } catch {
                                message = error.localizedDescription
                            }
                        }
                        Button("Load demo learning history") {
                            Task {
                                do {
                                    let result: CountResponse = try await appState.api.post(
                                        "/api/v1/sample-history",
                                        body: EmptySettingsBody()
                                    )
                                    let count = result.created ?? 0
                                    message = count == 0
                                        ? "Demo learning history is already loaded."
                                        : "Loaded synthetic history. Refresh Today to generate insights."
                                } catch {
                                    message = error.localizedDescription
                                }
                            }
                        }
                        Text(
                            "Demo history is synthetic and affects the timeline and insights. "
                            + "Remove it before evaluating your real patterns."
                        )
                        .font(.caption)
                        .foregroundStyle(.orange)
                        Button("Remove demo learning history", role: .destructive) {
                            Task {
                                do {
                                    let result: CountResponse = try await appState.api.delete(
                                        "/api/v1/sample-history"
                                    )
                                    message = "Removed \(result.deleted ?? 0) synthetic records."
                                } catch {
                                    message = error.localizedDescription
                                }
                            }
                        }
                    }
                }

                Section("Safety and privacy") {
                    SafetyNotice()
                    Text(
                        "Dexcom tokens are exchanged and stored by the backend. "
                        + "The client secret must never be placed in this app."
                    )
                    .font(.footnote)
                }

                if let message {
                    Text(message)
                }
            }
            .navigationTitle("Settings")
            .onAppear { apiURL = appState.apiBaseURL }
        }
    }
}

private struct EmptySettingsBody: Codable {}
