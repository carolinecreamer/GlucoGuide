import Foundation

struct ProfileInput: Codable {
    let displayName: String
    let heightCm: Double?
    let weightKg: Double?
    let pumpType: String?
    let insulinActionHours: Double
    let glucoseLowThreshold: Int
    let glucoseHighThreshold: Int
}

struct RegimenInput: Codable, Identifiable {
    var id: Int { startMinute }
    let startMinute: Int
    let basalUnitsPerHour: Double
    let insulinCarbRatio: Double
    let correctionFactor: Double?
    let targetGlucose: Int?
}

struct GlucoseReading: Codable, Identifiable {
    let id: String
    let observedAt: Date
    let valueMgDl: Int
    let trend: String?
}

struct Insight: Codable, Identifiable {
    let id: String
    let insightType: String
    let title: String
    let summary: String
    let evidence: [String: JSONValue]
    let confidence: Double
    let safetyClassification: String
    let createdAt: Date
}

enum JSONValue: Codable, CustomStringConvertible {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else {
            self = .array(try container.decode([JSONValue].self))
        }
    }

    var description: String {
        switch self {
        case .string(let value): value
        case .number(let value): value.formatted()
        case .bool(let value): value ? "Yes" : "No"
        case .object(let value): value.description
        case .array(let value): value.description
        case .null: "—"
        }
    }
}

struct MealInput: Codable {
    let occurredAt: Date
    let name: String
    let carbsG: Double
    let proteinG: Double
    let fatG: Double
    let fiberG: Double
    let notes: String?
}

struct ExerciseInput: Codable {
    let occurredAt: Date
    let exerciseType: String
    let intensity: String
    let durationMinutes: Int
    let notes: String?
}

struct DoseInput: Codable {
    let occurredAt: Date
    let units: Double
    let doseType: String
    let notes: String?
}

struct MealWithDoseInput: Codable {
    let meal: MealInput
    let confirmedUnits: Double?
}

struct MealDoseEstimateInput: Codable {
    let occurredAt: Date
    let carbsG: Double
}

struct MealDoseEstimate: Codable {
    let prescribedRatio: Double
    let estimatedUnits: Double
    let periodStartMinute: Int
    let explanation: String
    let disclaimer: String
}

struct MealWithDoseResponse: Codable {
    let mealId: String
    let doseId: String?
}

struct HistoryItem: Codable, Identifiable {
    let id: String
    let occurredAt: Date
    let itemType: String
    let title: String
    let detail: String
    let relatedId: String?
}

struct PersonalizationReadiness: Codable {
    let overnightNightsReady: Int
    let overnightNightsRequired: Int
    let mealPeriodCounts: [String: Int]
    let mealsPerPeriodRequired: Int
    let explanation: [String]
}

struct Guidance: Codable {
    let status: String
    let headline: String
    let guidance: [String]
    let evidence: [String]
    let uncertainty: String
    let emergencyNote: String
}

struct ExerciseGuidanceInput: Codable {
    let plannedAt: Date
    let exerciseType: String
    let intensity: String
    let durationMinutes: Int
}

struct MealGuidanceInput: Codable {
    let name: String
    let carbsG: Double
    let proteinG: Double
    let fatG: Double
    let fiberG: Double
}

struct DexcomStart: Codable {
    let authorizationUrl: URL
}

struct CountResponse: Codable {
    let created: Int?
    let inserted: Int?
    let deleted: Int?
}
