import Foundation
import Observation

@Observable
final class AppState {
    var hasCompletedOnboarding: Bool {
        didSet {
            UserDefaults.standard.set(hasCompletedOnboarding, forKey: "hasCompletedOnboarding")
        }
    }
    var apiBaseURL: String {
        didSet {
            UserDefaults.standard.set(apiBaseURL, forKey: "apiBaseURL")
        }
    }

    init() {
        hasCompletedOnboarding = UserDefaults.standard.bool(forKey: "hasCompletedOnboarding")
        apiBaseURL = UserDefaults.standard.string(forKey: "apiBaseURL")
            ?? "http://localhost:8000"
    }

    var api: APIClient {
        APIClient(
            baseURL: URL(string: apiBaseURL)
                ?? URL(string: "http://localhost:8000")!
        )
    }
}
