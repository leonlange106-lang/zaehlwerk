import SwiftUI

/// Karten-Container mit „Liquid Glass"-Material im Stil von Wallet/Fitness.
/// Respektiert `accessibilityReduceTransparency`: ist die Einstellung aktiv,
/// wird auf ein deckendes Systemgrau ausgewichen (keine Durchsicht).
struct GlassCard<Content: View>: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    var cornerRadius: CGFloat = 22
    var padding: CGFloat = 16
    @ViewBuilder var content: () -> Content

    var body: some View {
        content()
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(fillStyle)
            }
            .overlay {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(.white.opacity(reduceTransparency ? 0 : 0.08), lineWidth: 0.5)
            }
            .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
    }

    private var fillStyle: AnyShapeStyle {
        reduceTransparency
            ? AnyShapeStyle(Color(.secondarySystemGroupedBackground))
            : AnyShapeStyle(.regularMaterial)
    }
}
