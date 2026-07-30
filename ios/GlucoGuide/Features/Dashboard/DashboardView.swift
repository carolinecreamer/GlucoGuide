import Charts
import SwiftUI

struct DashboardView: View {
    @Environment(AppState.self) private var appState
    @State private var readings: [GlucoseReading] = []
    @State private var insights: [Insight] = []
    @State private var readiness: PersonalizationReadiness?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 16) {
                    SafetyNotice()

                    if let latest = readings.first {
                        HStack(alignment: .firstTextBaseline) {
                            Text("\(latest.valueMgDl)")
                                .font(.system(size: 54, weight: .bold, design: .rounded))
                            Text("mg/dL").foregroundStyle(.secondary)
                            Spacer()
                            Text(latest.trend ?? "")
                        }
                        .padding()
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18))
                    }

                    if !readings.isEmpty {
                        Chart(readings.reversed()) { reading in
                            LineMark(
                                x: .value("Time", reading.observedAt),
                                y: .value("Glucose", reading.valueMgDl)
                            )
                            .foregroundStyle(.indigo)
                        }
                        .chartYScale(domain: 40...300)
                        .frame(height: 220)
                        .padding()
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18))
                    }

                    Text("Insights").font(.title2.bold())
                    if insights.isEmpty {
                        ContentUnavailableView(
                            "No supported pattern yet",
                            systemImage: "chart.xyaxis.line",
                            description: Text(
                                "GlucoGuide waits for repeated evidence before suggesting a clinician review."
                            )
                        )
                        if let readiness {
                            ReadinessCard(readiness: readiness)
                        }
                    } else {
                        ForEach(insights) { insight in
                            InsightCard(insight: insight)
                        }
                    }

                    if let errorMessage {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
                .padding()
            }
            .navigationTitle("Today")
            .toolbar {
                Button {
                    Task { await refresh() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .disabled(isLoading)
            }
            .task { await refresh() }
        }
    }

    @MainActor
    private func refresh() async {
        isLoading = true
        defer { isLoading = false }
        errorMessage = nil

        do {
            readings = try await appState.api.get("/api/v1/glucose/recent")
        } catch {
            errorMessage = "Glucose: \(error.localizedDescription)"
        }

        do {
            insights = try await appState.api.post(
                "/api/v1/insights/generate",
                body: EmptyBody()
            )
        } catch {
            let insightError = "Insights: \(error.localizedDescription)"
            errorMessage = errorMessage.map { "\($0)\n\(insightError)" } ?? insightError
        }

        do {
            readiness = try await appState.api.get("/api/v1/insights/readiness")
        } catch {
            let readinessError = "Readiness: \(error.localizedDescription)"
            errorMessage = errorMessage.map { "\($0)\n\(readinessError)" } ?? readinessError
        }
    }
}

private struct EmptyBody: Codable {}

private struct InsightCard: View {
    let insight: Insight

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(insight.title, systemImage: "person.crop.circle.badge.checkmark")
                .font(.headline)
            Text(insight.summary)
            Divider()
            ForEach(insight.evidence.keys.sorted(), id: \.self) { key in
                LabeledContent(key.replacingOccurrences(of: "_", with: " ").capitalized) {
                    Text(insight.evidence[key]?.description ?? "—")
                }
                .font(.caption)
            }
            Text("Confidence: \(insight.confidence, format: .percent)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.indigo.opacity(0.09), in: RoundedRectangle(cornerRadius: 18))
    }
}

private struct ReadinessCard: View {
    let readiness: PersonalizationReadiness

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Personalization progress").font(.headline)
            ProgressView(
                value: Double(readiness.overnightNightsReady),
                total: Double(readiness.overnightNightsRequired)
            ) {
                Text(
                    "Overnight: \(readiness.overnightNightsReady)/"
                    + "\(readiness.overnightNightsRequired) qualifying nights"
                )
            }
            ForEach(["breakfast", "lunch", "dinner"], id: \.self) { period in
                let count = readiness.mealPeriodCounts[period] ?? 0
                Text(
                    "\(period.capitalized): \(count)/"
                    + "\(readiness.mealsPerPeriodRequired) meals with outcome data"
                )
                .font(.subheadline)
            }
            ForEach(readiness.explanation, id: \.self) { item in
                Text(item).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18))
    }
}
