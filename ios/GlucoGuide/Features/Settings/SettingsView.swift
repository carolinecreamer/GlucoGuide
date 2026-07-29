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
                                message = "Imported \(result.inserted ?? 0) new readings."
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
                                message = "Created \(result.created ?? 0) sample readings."
                            } catch {
                                message = error.localizedDescription
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

