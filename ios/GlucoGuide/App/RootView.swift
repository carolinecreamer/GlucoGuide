import SwiftUI

struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        Group {
            if appState.hasCompletedOnboarding {
                TabView {
                    DashboardView()
                        .tabItem { Label("Today", systemImage: "waveform.path.ecg") }
                    LogsView()
                        .tabItem { Label("Log", systemImage: "plus.circle") }
                    SettingsView()
                        .tabItem { Label("Settings", systemImage: "gearshape") }
                }
            } else {
                OnboardingView()
            }
        }
        .tint(.indigo)
    }
}

