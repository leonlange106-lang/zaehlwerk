# Zählwerk iOS

Nativer SwiftUI-Client für das dezentrale **Zählwerk**-Backend – kein WebView,
keine Weiterleitung, sondern eine eigenständige App mit voller Funktionsparität
zum Web-Tool (Zählerstände, Historie, Statistiken, Einstellungen).

> **Status:** Funktionsvollständige v1. Netzwerk- & Datenschicht, vollwertige
> HIG-Screens (Übersicht, System-Detail mit Swift-Charts-Diagramm, Ablesung
> erfassen, System anlegen, Verlauf, Einstellungen), **SwiftData-Offline-Cache**
> (Offline-First mit „Offline – Stand …"-Hinweis) sowie 2FA/Onboarding. Volle
> Parität zum Web-Tool: Zählerstände, Historie, Statistiken, Einstellungen.
> Look-and-Feel einer Apple-Systemapp mit Liquid-Glass-Materialien, dezenter
> Haptik und Rücksicht auf „Transparenz reduzieren".

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
│   ├── Dashboard.swift        # Dashboard-Aggregat (Systeme, Prognose, letzte Ablesungen)
│   └── CachedResponse.swift   # @Model – generischer Offline-Cache-Eintrag (SwiftData)
├── Services/                  # „Manager“- und Infrastruktur-Schicht
│   ├── APIClient.swift        # generischer async/await-Client, Fehlerabbildung, Cookie→Token
│   ├── ZaehlwerkAPI.swift     # typisierte Endpunkte (ein Aufruf je Route)
│   ├── AuthManager.swift      # @MainActor @Observable: Anmeldefluss & Sitzung
│   ├── CacheStore.swift       # @MainActor SwiftData-Cache (Offline-First, JSON-Blobs)
│   ├── JSONCoding.swift       # De-/Encoder inkl. gemischter Datumsformate des Backends
│   ├── KeychainStore.swift    # Keychain-Wrapper (Security)
│   └── SessionStores.swift    # thread-sichere Wertzugriffe für den APIClient
├── ViewModels/                # @MainActor @Observable – Zustand je Screen
│   ├── DashboardViewModel.swift
│   ├── SystemDetailViewModel.swift   # lädt Stats/Chart/Ablesungen parallel
│   ├── AddReadingViewModel.swift
│   └── AddSystemViewModel.swift
├── Components/                # wiederverwendbare UI-Bausteine
│   ├── Color+Hex.swift        # Color(hex:)-Hilfsinitialisierer
│   ├── GlassCard.swift        # Material-Karte, respektiert „Transparenz reduzieren"
│   ├── StatTile.swift         # Kennzahl-Kachel (Dynamic Type)
│   ├── SystemStyle.swift      # SF-Symbol + Farbe je Systemtyp
│   ├── Format.swift           # lokalisierte Zahlen-/Kosten-/Datumsformate
│   ├── Haptics.swift          # dezente UIImpact-/Notification-Haptik
│   ├── ConsumptionChartView.swift    # Swift-Charts-Verlauf (Detail)
│   ├── Sparkline.swift        # Miniatur-Verlauf (Übersichtskarten)
│   └── CacheStatusBar.swift   # „Offline – Stand …"-Hinweis
└── Views/
    ├── ServerSetupView.swift         # Schritt 1: Auth-Fluss
    ├── LoginView.swift
    ├── TwoFactorLoginView.swift
    ├── OnboardingView.swift
    ├── MainTabView.swift             # Schritt 2: Tab-Shell (Übersicht/Verlauf/Einstellungen)
    ├── DashboardView.swift           # Systemkarten + Prognose, „+" legt System an
    ├── SystemDetailView.swift        # Kennzahlen + Diagramm + Ablesungen
    ├── AddReadingView.swift          # Ablesungs-Eingabe (Sheet)
    ├── AddSystemView.swift           # System anlegen (Sheet, Typ-Vorlagen)
    ├── HistoryView.swift             # Verlauf über alle Systeme
    ├── SettingsView.swift            # Konto, Sicherheit, Verbindung
    └── TwoFactorEnrollView.swift     # 2FA nachträglich aktivieren
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
5. `authenticated` → `MainTabView` (Übersicht / Verlauf / Einstellungen)

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
   `ViewModels`, `Components`, `Views` sowie `ZaehlwerkApp.swift`) per *Add
   Files to „Zaehlwerk“…* mit **„Create groups“** hinzufügen.
5. Deployment Target **iOS 17.0+** (für `@Observable`, `ContentUnavailableView`
   und Swift Charts; Swift-6-Concurrency wird empfohlen). Für die Diagramme ist
   kein zusätzliches Paket nötig – **Swift Charts** (`import Charts`) ist Teil
   des SDK.
6. Build & Run auf Simulator oder Gerät. Beim ersten Start die Server-Adresse
   eingeben, z. B. `https://zaehlwerk.example.com`.

### Hinweis zum Kompilieren

Dieser Code wurde in einer Umgebung **ohne Xcode/Swift-Toolchain** erstellt und
konnte dort nicht kompiliert werden. Bitte in Xcode bauen; kleinere Anpassungen
(Bundle-ID, Signing-Team) sind projektspezifisch vorzunehmen.

## Screens (Schritt 2)

- **Übersicht** – Karten je System mit aktuellem Stand, Verbrauch, Kosten,
  Miniatur-Verlauf (Sparkline) und Jahresprognose (warnt bei Abschlags-
  Überschreitung). Pull-to-Refresh, große Titel, gruppierter Hintergrund.
- **System-Detail** – Kennzahlen-Kacheln, Verlaufsdiagramm (Swift Charts,
  Ausreißer hervorgehoben) und Ablesungsliste mit Herkunfts-Chip und
  Wischen-zum-Löschen. „+" öffnet die Eingabe (nur mit Schreibrecht).
- **Neue Ablesung** – Datum, Zählerstand, optionale Kosten/Notiz und
  Zählertausch mit Anfangsstand; deutsche Zahleneingabe (Komma/Punkt).
- **System anlegen** – Typ-Vorlagen (Strom/Gas/Wasser/PV/…) füllen die passende
  Einheit vor, freie Felder für Name/Typ/Einheit, Farbe über `ColorPicker`.
  Erreichbar über „+" in der Übersicht (nur mit Schreibrecht).
- **Verlauf** – die zuletzt erfassten Ablesungen über alle Systeme.
- **Einstellungen** – Konto, 2FA-Status inkl. nachträglicher Aktivierung,
  Passwort ändern, Server-Adresse, Abmelden.
- **Datenbank-Wechsel** – bei Zugriff auf mehrere Mandanten-Datenbanken
  erscheint in den Einstellungen ein Selektor; die Auswahl schaltet den
  API-Kontext (`X-Zaehlwerk-Database`) um und verwirft den Offline-Cache.
- **Admin-Console** (nur für Admins) – natives Pendant zum Web-Dashboard:
  Kontostatus (online/2FA/Passwort), aktive Sitzungen mit Zwangs-Abmeldung
  (Admin-Override) und Datenbank-Verwaltung inkl. Rechte-Matrix.

### Look-and-Feel

- Liquid-Glass-Karten über `.regularMaterial`; bei aktivem „Transparenz
  reduzieren" (`accessibilityReduceTransparency`) deckendes Systemgrau.
- Dynamic Type über System-Schriftstile, `NavigationStack` mit großen Titeln,
  dezente Haptik (`Haptics`) bei Auswahl, Speichern und Fehlern.
- Light/Dark automatisch über System-Farben und Materialien.

## Offline-First (Schritt 3)

`CacheStore` (SwiftData) legt jede erfolgreich geladene Antwort als JSON-Blob
(`CachedResponse`) unter einem Schlüssel ab (`dashboard`, `readings.<id>`,
`stats.<id>`, `chart.<id>`). Die ViewModels arbeiten write-through:

1. Beim Öffnen wird sofort der letzte Cache-Stand angezeigt.
2. Parallel wird über das Netz aktualisiert und der Cache zurückgeschrieben.
3. Bricht das Netz weg, bleibt der Cache sichtbar; eine dezente Leiste zeigt
   „Offline – Stand vor X Minuten".

Der Cache verwendet ein **eigenes symmetrisches** `.iso8601`-Coder-Paar (der
zentrale `JSONCoding`-Decoder erwartet String-Daten, sein Encoder schreibt aber
Zahlen – ein Round-Trip darüber wäre inkonsistent). Beim Abmelden wird der Cache
vollständig geleert (`CacheStore.clear()`), damit kein Konto fremde Daten sieht.

SwiftData ist Teil des SDK – **kein** zusätzliches Paket nötig.

## Ausbau (optional)

Die App deckt den vollen Funktionsumfang des Web-Tools ab. Denkbare Erweiterungen:

- System bearbeiten/archivieren (`PATCH /api/systems/{id}`, `SystemUpdate` liegt
  im Backend bereits vor).
- Home-Screen-Widgets (WidgetKit) mit dem aktuellen Stand je System.
- Diagramm-Interaktion (Scrubbing) und Export (CSV/PDF).
- Push-Erinnerungen an fällige Ablesungen.
