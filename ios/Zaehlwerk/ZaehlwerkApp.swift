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

/// Wurzel-Router: wählt je Anmeldephase den passenden Screen.
/// Der authentifizierte Zustand zeigt die vollwertige Tab-Oberfläche.
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
            MainTabView()
        }
    }
}
