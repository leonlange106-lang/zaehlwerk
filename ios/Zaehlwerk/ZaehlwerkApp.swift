import SwiftUI

@main
struct ZaehlwerkApp: App {
    @State private var auth = AuthManager.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(auth)
                .task { await auth.bootstrap() }
        }
    }
}

/// Minimaler Wurzel-Router für den Network-Layer-Meilenstein (Schritt 1).
/// Er zeigt je Anmeldephase eine schlanke, funktionsfähige Ansicht, mit der
/// sich Netzwerk- und Auth-Schicht gegen ein echtes Backend prüfen lassen.
/// Die vollwertigen, HIG-konformen Screens (Dashboard, Detail, Eingabe,
/// Einstellungen) folgen in den nächsten Schritten und ersetzen diese Hüllen.
struct RootView: View {
    @Environment(AuthManager.self) private var auth

    var body: some View {
        switch auth.phase {
        case .launching:
            ProgressView("Verbinde …")
        case .unconfigured:
            ServerSetupView()
        case .loggedOut:
            LoginView()
        case .twoFactorRequired:
            TwoFactorLoginView()
        case .onboarding:
            OnboardingView()
        case .authenticated:
            ConnectedPlaceholderView()
        }
    }
}
