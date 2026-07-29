import SwiftUI

struct SafetyNotice: View {
    var body: some View {
        Label {
            Text(
                "Advisory only. Never change insulin or treat an emergency solely from this app. "
                + "Follow your prescribed plan and confirm changes with your clinician."
            )
            .font(.footnote)
        } icon: {
            Image(systemName: "cross.case.fill")
        }
        .foregroundStyle(.orange)
        .padding()
        .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 14))
        .accessibilityLabel("Medical safety notice")
    }
}

