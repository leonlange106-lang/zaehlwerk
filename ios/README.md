# Zählwerk iOS

Nativer SwiftUI-Client für das dezentrale **Zählwerk**-Backend – kein WebView,
keine Weiterleitung, sondern eine eigenständige App mit voller Funktionsparität
zum Web-Tool (Zählerstände, Historie, Statistiken, Einstellungen).

> **Status:** Schritt 1 (Netzwerk- & Datenschicht) ist umgesetzt. Die Views in
> `Views/` sind bewusst schlanke, funktionsfähige Hüllen, mit denen sich die
> Auth- und API-Schicht gegen ein echtes Backend prüfen lässt. Die
> vollwertigen, HIG-konformen Screens (Dashboard, Detail, Eingabe,
> Einstellungen inkl. Liquid-Glass-Materialien, Haptik und SwiftData-Offline-
> Cache) folgen in den nächsten Schritten und ersetzen diese Hüllen.

## Architektur

MVVM-M (Model – View – ViewModel – **Manager**) mit Swift Concurrency
(`async/await`) und dem `@Observable`-Makro (Observation-Framework, Swift 6).

```
ios/Zaehlwerk/
├── ZaehlwerkApp.swift        # @main + Wurzel-Router (schaltet je AuthPhase)
├── Config/
│   └── AppConfig.swift        # @Observable: Server-URL (UserDefaults) + Token/CF-Access (Keychain)
├── Models/                    # Reine Codable-Spiegel der Backend-Schemata
│   ├── JSONValue.swift        # dynamische JSON-Werte (zusatzfelder, permissions, roles)
│   ├── APIError.swift         # typisierte Fehler + LocalizedError (deutsch)
│   ├── AuthModels.swift       # User, AuthStatus, LoginResponse, TwoFactorSetup, Request-Bodies
│   ├── MeterSystem.swift      # System (Strom/Gas/Wasser/PV …)
│   ├── Reading.swift          # Ablesung
│   ├── Statistics.swift       # SystemStats + ChartData
│   └── Dashboard.swift        # Dashboard-Aggregat (Systeme, Prognose, letzte Ablesungen)
├── Services/                  # „Manager“- und Infrastruktur-Schicht
│   ├── APIClient.swift        # generischer async/await-Client, Fehlerabbildung, Cookie→Token
│   ├── ZaehlwerkAPI.swift     # typisierte Endpunkte (ein Aufruf je Route)
│   ├── AuthManager.swift      # @MainActor @Observable: Anmeldefluss & Sitzung
│   ├── JSONCoding.swift       # De-/Encoder inkl. gemischter Datumsformate des Backends
│   ├── KeychainStore.swift    # Keychain-Wrapper (Security)
│   └── SessionStores.swift    # thread-sichere Wertzugriffe für den APIClient
├── Components/
│   └── Color+Hex.swift        # Color(hex:)-Hilfsinitialisierer
└── Views/                     # schlanke Auth-/Platzhalter-Ansichten (Schritt 1)
    ├── ServerSetupView.swift
    ├── LoginView.swift
    ├── TwoFactorLoginView.swift
    ├── OnboardingView.swift
    └── ConnectedPlaceholderView.swift
```

### Schichtentrennung

- **Models** kennen weder Netzwerk noch UI – reine `Codable`/`Sendable`-Typen.
- **APIClient** ist der einzige Ort, der URLs, Header und Statuscodes kennt.
  ViewModels/Manager rufen ausschließlich typisierte Methoden aus
  `ZaehlwerkAPI.swift` auf, nie eine URL.
- **AuthManager** (das „M“ in MVVM-M) hält den beobachtbaren Anmeldezustand
  (`AuthPhase`) und kapselt alle Auth-Aufrufe. Views lesen `phase`, `isBusy`,
  `errorMessage` reaktiv über `@Observable`.

## Authentifizierung

Das Backend setzt das Sitzungstoken als HttpOnly-Cookie `zw_session`. Der
`APIClient` liest dessen Wert aus dem `Set-Cookie`-Header der Login-/2FA-Antwort
(`syncToken(from:)`), legt ihn im Keychain ab und sendet ihn danach als
`Authorization: Bearer …`. `resolve_user` im Backend akzeptiert beides
(Cookie **oder** Bearer), daher sind **keine CORS-/Backend-Änderungen** nötig.

Anmeldefluss (`AuthPhase`):

1. `unconfigured` – keine Server-Adresse → `ServerSetupView`
2. `loggedOut` – Anmeldung → `LoginView`
3. `twoFactorRequired` – Passwort ok, TOTP fehlt → `TwoFactorLoginView`
4. `onboarding` – erzwungene Erstanmeldung (Passwort + 2FA) → `OnboardingView`
5. `authenticated` → `ConnectedPlaceholderView`

Optional werden **Cloudflare-Access-Service-Token** (`CF-Access-Client-Id` /
`-Secret`) mitgesendet, falls das Backend hinter Cloudflare Access liegt; die
Werte liegen im Keychain und bleiben leer, wenn nicht benötigt.

## Projekt in Xcode einrichten

Es ist bewusst **keine** `.xcodeproj`/`.xcworkspace` eingecheckt (Merge-Konflikte,
absolute Pfade). Das Projekt wird lokal erzeugt:

1. **Xcode 16+** öffnen → *File ▸ New ▸ Project… ▸ iOS ▸ App*.
2. Product Name `Zaehlwerk`, Interface **SwiftUI**, Language **Swift**,
   Storage **None** (SwiftData folgt in einem späteren Schritt).
3. Das automatisch erzeugte `ContentView.swift` und die generierte
   `…App.swift`-Datei löschen.
4. Den Inhalt von `ios/Zaehlwerk/` (Ordner `Config`, `Models`, `Services`,
   `Components`, `Views` sowie `ZaehlwerkApp.swift`) per *Add Files to
   „Zaehlwerk“…* mit **„Create groups“** hinzufügen.
5. Deployment Target **iOS 17.0+** (für das `@Observable`-Makro; Swift-6-
   Concurrency wird empfohlen).
6. Build & Run auf Simulator oder Gerät. Beim ersten Start die Server-Adresse
   eingeben, z. B. `https://zaehlwerk.example.com`.

### Hinweis zum Kompilieren

Dieser Code wurde in einer Umgebung **ohne Xcode/Swift-Toolchain** erstellt und
konnte dort nicht kompiliert werden. Bitte in Xcode bauen; kleinere Anpassungen
(Bundle-ID, Signing-Team) sind projektspezifisch vorzunehmen.

## Nächste Schritte

- Schritt 2: Vollständige SwiftUI-Views (Dashboard, System-Detail mit Chart,
  Zählereingabe, Einstellungen) im Look-and-Feel einer Apple-Systemapp.
- Schritt 3: SwiftData-Offline-Cache (Offline-First) mit Hintergrund-Sync.
- Schritt 4: HIG-Feinschliff – Liquid-Glass-Materialien
  (`.ultraThinMaterial`/`.regularMaterial`, Rücksicht auf
  `UIAccessibility.isReduceTransparencyEnabled`), Dynamic Type, dezente
  `UIImpactFeedbackGenerator`-Haptik, Light/Dark.
