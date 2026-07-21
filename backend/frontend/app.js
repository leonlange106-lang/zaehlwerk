/* =========================================================================
   Zählwerk – Frontend (Vue 3, ohne Build-Step)
   ========================================================================= */
const { createApp, reactive } = Vue;

/* ---------- Version & Changelog ---------- */
const APP_VERSION = "3.22.2";
const APP_CHANGELOG = [
  { v: "3.22.2", d: "21.07.2026", items: [
    "Mobil: die Bericht-Markierung in der unteren Navigationsleiste bleibt nicht mehr hängen, wenn der Berichtsdialog geschlossen oder ein Bericht erstellt wird",
    "Mobil: die Tab-Leiste in der Detailansicht schneidet lange Beschriftungen (z. B. „Auswertung“) nicht mehr ab, sondern scrollt bei Bedarf horizontal",
    "Diagramm: die Umschalter zum Überlagern anderer Systeme zeigen lange Systemnamen vollständig an und brechen sauber um",
    "Die schwebende ＋-Schaltfläche legt im Tarife-Tab jetzt einen Tarif an (statt einer Ablesung); ihre Beschriftung folgt wieder dem aktiven Tab (Wert / Zähler / Tarif)",
  ]},
  { v: "3.22.1", d: "21.07.2026", items: [
    "Startseite mit mehreren Systemen lädt schneller (Verbrauch wird je System nur noch einmal berechnet statt doppelt)",
    "Aufräumen: ungenutzter Code entfernt (Wartung, keine Funktionsänderung)",
  ]},
  { v: "3.22.0", d: "20.07.2026", items: [
    "Diagramme mit sehr langer Historie werden für die Anzeige automatisch verdichtet – schnellere Darstellung ohne Verlust von Verlauf oder Summe. Die Werte-Tabelle bleibt vollständig",
  ]},
  { v: "3.21.0", d: "20.07.2026", items: [
    "Umfangreiche Testabdeckung der Verbrauchs- und Abrechnungslogik: Zählertausch bei Tarifwechsel, Preissenkungen mitten im Zeitraum, Lücken ohne Ablesung, Prognose-Randfälle",
    "Tests laufen automatisch bei jedem Push und Pull Request (Absicherung gegen Regressionen)",
  ]},
  { v: "3.20.0", d: "20.07.2026", items: [
    "Aufbewahrungsregel für MQTT-Telemetrie: ältere Werte lassen sich automatisch auf einen Datensatz je Monat verdünnen (einstellbar unter Admin-Tools → Datenmanagement, Standard: unbegrenzt)",
    "Von Hand erfasste, importierte und aus HA übernommene Werte bleiben immer vollständig erhalten; Gesamtverbräuche ändern sich durch die Verdünnung nicht",
    "Tägliche Datenpflege läuft jetzt auch, wenn die automatische Sicherung ausgeschaltet ist",
  ]},
  { v: "3.19.0", d: "20.07.2026", items: [
    "Automatisierte Vertragstests für alle wichtigen API-Endpunkte – schlagen Alarm, sobald ein Feld fehlt, auf das die Oberfläche angewiesen ist",
    "Interaktive API-Dokumentation unter /docs (Swagger) und /redoc, Schema unter /openapi.json",
  ]},
  { v: "3.18.0", d: "20.07.2026", items: [
    "Grundpreis ist jetzt ein Jahresbetrag (€/Jahr) und wird taggenau abgerechnet – bestehende Monatswerte wurden automatisch umgerechnet",
    "Zählertausch: optionaler Startstand des neuen Zählers – der Verbrauch ist dann die Differenz, ein Sprung auf 0 erzeugt keine negativen Werte mehr",
    "Kostenprognose komplett neu: 5-Jahres-Schnitt fürs nächste Abrechnungsjahr statt naiver Hochrechnung über die ganze Historie",
    "Warnung auf der Kostenprognose-Kachel, sobald die Jahresprognose den hinterlegten Abschlag übersteigt",
    "Je System einstellbar: monatlicher Abschlag und Startmonat des Abrechnungsjahres",
  ]},
  { v: "3.17.1", d: "20.07.2026", items: [
    "Logo/Titel oben links führt jetzt von überall zurück zur Startseite",
    "„Berichterstellung“ wieder in der unteren Navigationsleiste (jetzt fünf Ziele)",
    "Die schwebende ＋-Schaltfläche erscheint nur noch dort, wo sie etwas anlegt – nicht mehr über den Speichern-Dialogen der Admin-Tools",
  ]},
  { v: "3.17.0", d: "20.07.2026", items: [
    "Mobile Startseite: je Zähler eine eigene Karte mit großem „＋ Wert erfassen“-Knopf – ein Tipp führt direkt in die Ablesung des jeweiligen Zählers, ohne Umweg über die Auswahl",
    "Kamera-Schnellzugriff je Zähler direkt auf der Startseite",
    "Zum Startbildschirm hinzugefügt startet die App jetzt im Vollbild (app-artig)",
  ]},
  { v: "3.16.0", d: "20.07.2026", items: [
    "Dashboard-Kacheln vom Typ Verlauf/Trend/Kostenprognose: benutzerdefinierter Zeitraum mit freier Wahl von Start- und Enddatum",
    "Behebt einen seltenen Absturz von Dashboard-Diagrammen, wenn eine Kachel kurz nach dem Anlegen bearbeitet oder das Dashboard schnell hintereinander gespeichert und neu geladen wurde",
  ]},
  { v: "3.15.0", d: "20.07.2026", items: [
    "Herkunfts-Badges (HA/Import/Manuell) und der Quellen-Filter in der Werte-Tabelle funktionierten in der Detailansicht eines Systems nicht (\"sourceLabel is not a function\") - behoben",
  ]},
  { v: "3.14.0", d: "20.07.2026", items: [
    "Änderungsprotokoll: einzelne Einträge lassen sich per „Rückgängig“ direkt zurücknehmen (Anlegen, Ändern, Löschen)",
  ]},
  { v: "3.13.0", d: "20.07.2026", items: [
    "Behebt einen Bug, durch den die Herkunft (Quelle) jeder Ablesung unabhängig vom tatsächlichen Ursprung immer als „manuell“ gespeichert wurde",
    "MQTT Auto-Discovery: unbeteiligte Geräte lassen sich dauerhaft ausblenden (Ignorieren-Button, wieder einblendbar)",
    "Watchdog meldet über Home Assistant, wenn ein per MQTT angebundenes System zu lange keinen neuen Wert liefert",
  ]},
  { v: "3.12.0", d: "20.07.2026", items: [
    "Admin-Tools zum Tab-Dashboard erweitert: System, Netzwerk, Zugriff, Datenmanagement, Diagnose, Abfrage, Protokoll, Änderungen",
    "Kill-Switch, Anwendungsparameter, MQTT-Einrichtung, Konten & Rollen und der Sicherungs-Zeitplan sind aus den Einstellungen in die Admin-Tools umgezogen",
    "Einstellungen zeigen jetzt für alle Konten Darstellung, Diagrammfarben und das eigene Konto (vorher nur für Administratoren erreichbar)",
  ]},
  { v: "3.11.1", d: "20.07.2026", items: [
    "Wiederherstellung verlangt jetzt die Bestätigung durch Eingabe des Wortes RESTORE statt eines einfachen Ja/Nein-Dialogs",
  ]},
  { v: "3.11.0", d: "20.07.2026", items: [
    "Behebt einen mit 3.10.1 eingeführten Build-Fehler auf CPUs ohne SSE4.2 (opencv/numpy zurückgestuft)",
    "Neuer Menüpunkt „Datenmanagement“ in den Admin-Tools: Sicherungen erstellen, herunterladen und wiederherstellen an einem Ort",
    "Wiederherstellung per Upload einer .gz-Sicherung oder aus einer bestehenden eigenen Sicherung",
    "Vor jeder Wiederherstellung wird der aktuelle Stand automatisch als Sicherheitskopie weggesichert",
  ]},
  { v: "3.10.1", d: "20.07.2026", items: [
    "Build-Pipeline stabilisiert: Abhängigkeiten fest verpinnt statt Untergrenzen",
  ]},
  { v: "3.10.0", d: "19.07.2026", items: [
    "Eigene Startseite für Smartphones: drei Kennzahlen, Ablesung, letzte Erfassungen",
    "Beim Start entscheidet die Bildschirmbreite über die erste Ansicht",
  ]},
  { v: "3.9.0", d: "19.07.2026", items: [
    "Dashboard und Bericht unter „Auswertungen“ zusammengefasst",
    "Kacheln über einen Dialog einrichten statt über Inline-Schaltflächen",
    "Zeitraum je Kachel, mehrere Systeme in einem Verlauf",
    "Kreisdiagramm zeigt absolute Werte, neue Kacheln Trend und Kostenprognose",
  ]},
  { v: "3.8.1", d: "19.07.2026", items: [
    "Bericht und Rohdaten-Export lassen sich auf einzelne Datenquellen einschränken",
    "Build bricht ab, wenn Tesseract oder die deutschen Sprachdaten fehlen",
    "Zustand der Texterkennung in der Admin-Diagnose sichtbar",
  ]},
  { v: "3.8.0", d: "19.07.2026", items: [
    "Änderungsprotokoll für Ablesungen, Systeme, Tarife, Zähler, Konten und Einstellungen",
    "Einträge sind unveränderlich – die Datenbank weist Änderungen selbst ab",
    "Neuer Reiter „Änderungen“ in den Admin-Tools mit Filtern und Seitenaufteilung",
  ]},
  { v: "3.7.0", d: "19.07.2026", items: [
    "Herkunft je Ablesung: Manuell, MQTT, HA oder Import",
    "Chips in der Werte-Tabelle und Filter nach Quelle",
    "Notizfeld bleibt frei – MQTT belegt es nicht mehr",
    "Kamera-Schaltfläche wieder sichtbar, mit Grund bei fehlender Erkennung",
  ]},
  { v: "3.6.0", d: "19.07.2026", items: [
    "Zählerstand-Erkennung läuft serverseitig mit Tesseract und Bildvorverarbeitung",
    "Letzter Stand entscheidet zwischen Zählwerk, Seriennummer und Eichjahr",
    "Hinweis samt Alternativen nach der Erkennung; erkannte Werte sind Vorschläge",
    "Keine Bibliothek mehr aus dem Netz – Erkennung funktioniert offline",
  ]},
  { v: "3.5.1", d: "19.07.2026", items: [
    "Changelog erscheint jetzt im Update-Dialog von Home Assistant",
    "deploy.ps1 prüft die Versionsgleichheit und setzt das Git-Tag selbst",
  ]},
  { v: "3.5.0", d: "19.07.2026", items: [
    "Dashboard mit frei anordenbaren Kacheln, je Konto gespeichert",
    "Kacheln: Letzter Stand, Verlauf, Verteilung, Kosten",
    "Bearbeitungsmodus zum Verschieben, Skalieren und Entfernen",
    "Unter 768 px einspaltig, darüber zwei bzw. vier Spalten",
  ]},
  { v: "3.4.1", d: "19.07.2026", items: [
    "Admin-Tools jetzt auch in der unteren Navigationsleiste – nur für Administratoren",
    "Einstellungen wieder für alle Konten erreichbar (Darstellung, Palette, Diagrammfarben)",
    "Schwebende Schaltfläche liegt nicht mehr über der Navigationsleiste",
    "Freiraum berücksichtigt den Home-Indikator",
  ]},
  { v: "3.4.0", d: "19.07.2026", items: [
    "Sammelauswahl in der Werte-Tabelle mit Aktionsleiste",
    "Seite oder alle Treffer auswählen, Auswahl überlebt Seitenwechsel",
    "Sammellöschung in einem Vorgang statt vieler Einzelaufrufe",
  ]},
  { v: "3.3.1", d: "19.07.2026", items: [
    "Schwebende Schaltfläche verdeckt die letzte Tabellenzeile nicht mehr",
    "Datumsfelder haben dieselbe Höhe wie Textfelder",
    "Auswahlsegmente einheitlich hoch, auf schmalen Anzeigen als 2×2-Raster",
  ]},
  { v: "3.3.0", d: "19.07.2026", items: [
    "Admin-Tools: Diagnose, lesende Datenbankabfrage, Anwendungsprotokoll",
    "Nur für Administratoren, serverseitig durchgesetzt",
    "Kein Shell-Zugang – dafür ist das Add-on „Advanced SSH & Web Terminal\" vorgesehen",
  ]},
  { v: "3.2.2", d: "19.07.2026", items: [
    "Erneute Auslieferung des 3.2.1-Standes unter neuer Nummer",
  ]},
  { v: "3.2.1", d: "19.07.2026", items: [
    "Startabbruch behoben: Modulkonstante wurde vor ihrer Definition verwendet",
    "Auslieferung als vollständiges Paket statt Einzeldateien",
  ]},
  { v: "3.2.0", d: "18.07.2026", items: [
    "Rollen: Administrator, Schreiber, Leser, Gast",
    "Verändernde Aufrufe werden für Leser und Gast serverseitig abgewiesen",
    "Oberfläche blendet Aktionen ohne Berechtigung aus",
    "Rollenverwaltung in den Einstellungen",
  ]},
  { v: "3.1.0", d: "18.07.2026", items: [
    "MQTT-Speicherintervall wählbar: täglich, wöchentlich, monatlich, quartalsweise, jährlich",
    "Je System abweichend einstellbar, sonst gilt die globale Vorgabe",
    "Von Hand erfasste Ablesungen werden nie durch MQTT überschrieben",
  ]},
  { v: "3.0.0", d: "18.07.2026", items: [
    "Benutzerkonten und Anmeldung; alle API-Pfade sind geschützt",
    "Unter Home Assistant übernimmt Zählwerk die dortige Anmeldung – kein zweiter Login",
    "Standalone: bcrypt-Passwörter, JWT im HttpOnly-Cookie, Ersteinrichtung beim ersten Start",
  ]},
  { v: "2.21.1", d: "18.07.2026", items: [
    "Reiter „Zähler\" und „Tarife\" zeigen ihre Anzahl schon beim Laden der Seite",
    "Anzahlen kommen aus dem Dashboard-Request – keine zusätzlichen Abfragen",
  ]},
  { v: "2.21.0", d: "18.07.2026", items: [
    "Mobile Systemauswahl als Modal Bottom Sheet über die untere Navigationsleiste",
    "Tipp auf das bereits aktive Zählwerk-Ziel öffnet die Liste, sonst führt er zur Übersicht",
    "Gleiche Sprungziele wie in der Desktop-Sidebar",
  ]},
  { v: "2.20.0", d: "18.07.2026", items: [
    "SML-Telegramme werden erkannt, auch wenn der Gruppenname frei gewählt ist",
    "Rohdaten und alle Zahlenpfade werden bei nicht erkanntem Telegramm angezeigt",
    "JSON-Pfad je System festlegbar – schlägt die automatische Erkennung",
  ]},
  { v: "2.19.1", d: "18.07.2026", items: [
    "Speichern-Leiste am Ende der Einstellungen statt mitten auf der Seite",
    "Bleibt beim Scrollen am unteren Rand sichtbar und zeigt die Zahl der Änderungen",
    "Speichern gesperrt, solange ein Feld fehlerhaft ist",
  ]},
  { v: "2.19.0", d: "18.07.2026", items: [
    "Rohdaten-Export als flaches CSV über alle Systeme und als strukturiertes JSON",
    "CSV wahlweise für Excel (Semikolon, Dezimalkomma, BOM) oder pandas/R",
    "Beide Formate mit Verbrauch, Tagesverbrauch, Ausreißern und Kosten",
  ]},
  { v: "2.18.0", d: "18.07.2026", items: [
    "Tasmota nativ: ENERGY.Total, Total_In und COUNTER.C1 ohne manuelle JSON-Pfade",
    "Auto-Discovery über tele/+/SENSOR mit Geräteliste und Ein-Klick-Zuordnung",
    "Online-/Offline-Anzeige je Gerät über das LWT-Topic",
  ]},
  { v: "2.17.0", d: "18.07.2026", items: [
    "MQTT-Ingestion: Zählerstände aus Broker-Nachrichten übernehmen",
    "Zugangsdaten kommen vom Mosquitto-Add-on – kein Passwort nötig",
    "Höchstens eine Ablesung je System und Tag; Werte laufen nie rückwärts",
    "Topic je System im Bearbeiten-Dialog, Ereignisprotokoll in den Einstellungen",
  ]},
  { v: "2.16.0", d: "18.07.2026", items: [
    "Tarifperioden je System: Arbeitspreis, Grundgebühr, Gültigkeitszeitraum",
    "Kostenrechnung tageweise – ein Tarifwechsel mitten im Intervall wird korrekt aufgeteilt",
    "Effektivpreis inklusive Grundgebühr in der Auswertung",
  ]},
  { v: "2.15.0", d: "18.07.2026", items: [
    "Sidebar: „Zählwerk\" lässt sich aufklappen und listet alle aktiven Systeme",
    "Direkter Sprung in ein System aus der Sidebar, aktives System hervorgehoben",
    "Pfeil klappt auf, der Eintrag selbst führt weiterhin zur Übersicht",
  ]},
  { v: "2.14.0", d: "18.07.2026", items: [
    "Tägliche automatische Sicherung der Datenbank nach /backup",
    "Konsistent trotz laufender Schreibzugriffe (SQLite Online-Backup + Integritätsprüfung)",
    "Rollierende Bereinigung; die drei neuesten Sicherungen bleiben immer erhalten",
    "Manuelle Sicherung und Download in den Einstellungen",
  ]},
  { v: "2.13.0", d: "18.07.2026", items: [
    "Bericht öffnet einen Konfigurationsdialog statt sofort zu exportieren",
    "Zeitraum-Vorauswahl, System-Checkboxen, Diagramm/Tabelle abwählbar",
    "PDF übernimmt auf Wunsch die App-Farben; Diagramme je System in Systemfarbe",
  ]},
  { v: "2.12.2", d: "18.07.2026", items: [
    "Tabs schließen sich gegenseitig aus – Werte und Zähler wurden gleichzeitig angezeigt",
    "FAB passt sich dem aktiven Tab an (Zähler statt Ablesung)",
  ]},
  { v: "2.12.1", d: "18.07.2026", items: [
    "Nur noch eine Navigation je Viewport: mobil Bottom-Bar, Desktop Sidebar",
    "Kamera-Button im Ablesedialog wieder quadratisch und mittig zum Eingabefeld",
  ]},
  { v: "2.12.0", d: "18.07.2026", items: [
    "Internet-Kill-Switch: sperrt ausgehende Verbindungen auf Socket-Ebene, Standard ist gesperrt",
    "Optionale externe Daten: Wetter (Open-Meteo) und Day-Ahead-Preise (aWATTar)",
    "Anbieter-Allowlist fest im Code, keine Schlüssel, keine frei setzbaren URLs",
    "Offline fehlertolerant: zwischengespeicherte Daten bleiben abrufbar",
  ]},
  { v: "2.11.0", d: "18.07.2026", items: [
    "Zähler-Tab: Metadaten aus 2.10.0 endlich in der Oberfläche pflegbar",
    "Hardware-Empfehlung je Zähler (Hichi IR, Reed-Kontakt, AI-on-the-edge, wM-Bus …)",
    "Live-Vorschau der Empfehlung schon beim Eintippen der Bauart",
    "Eichfrist-Badge je Zähler",
  ]},
  { v: "2.10.1", d: "18.07.2026", items: [
    "Systemverwaltung wieder erreichbar: „✎ Bearbeiten\" in der Systemansicht",
    "Systeme endgültig löschbar – der Button fehlte seit 2.4.0",
    "Kachelwerte und Fälligkeits-Badges aktualisieren sich nach dem Erfassen sofort",
  ]},
  { v: "2.10.0", d: "18.07.2026", items: [
    "Zähler-Metadaten: Hersteller, Modell, Zählernummer, Bauart, Eichfrist je System",
    "Eichfristen-Übersicht über die API",
    "Zähler-Metadaten im Gesamt-Export enthalten",
  ]},
  { v: "2.9.1", d: "18.07.2026", items: [
    "Dialoge auf dem Handy als Bottom-Sheet mit feststehender Aktionsleiste",
    "Alle Trefferflächen auf 48 px, Formularfelder auf 16 px (kein iOS-Auto-Zoom mehr)",
    "Ablesedialog: Zählerstand steht zuoberst, Scanner-Button vergrößert",
    "Layout springt nicht mehr bei Tastatur, Scrollbar oder Validierungsmeldung",
  ]},
  { v: "2.9.0", d: "18.07.2026", items: [
    "Einstellungen als eigene Seite mit Sektion A (System) und B (Web-App)",
    "Serverseitige Anwendungsparameter: Benachrichtigungsintervall, Standard-Ableseintervall, Ausreißer-Schwelle",
    "Schema-Migrationen über PRAGMA user_version",
    "Laufzeit- und Datenbankdiagnose (read-only)",
    "Import/Export direkt in der Systemansicht statt in den Einstellungen",
  ]},
  { v: "2.8.0", d: "18.07.2026", items: [
    "Freie Farbwahl je System zusätzlich zu den acht Presets",
    "Diagrammfarben für Ausreißer, Gitternetz und Achsen in den Einstellungen konfigurierbar",
    "Kontrastwarnung bei schwer erkennbaren Farben (WCAG-Verhältnis unter 3:1)",
  ]},
  { v: "2.7.0", d: "18.07.2026", items: [
    "Wählbare Farbpaletten: Teal, Indigo, Ember – unabhängig vom Hell-/Dunkel-Modus",
    "Hochkontrast-Theme (WCAG AAA) für beide Modi und alle Paletten",
    "Sichtbarer Fokusring auf allen bedienbaren Elementen",
    "Systempräferenz „prefers-contrast\" wird automatisch übernommen",
  ]},
  { v: "2.6.0", d: "18.07.2026", items: [
    "Einklappbare Navigations-Sidebar (Rail 80px ↔ Drawer 264px), Zustand bleibt gespeichert",
    "Mobile: Sidebar als modaler Drawer mit Scrim über den Menü-Button in der Top-App-Bar",
    "Navigationsziele Zählwerk, Bericht, Einstellungen und Admin-Tools (Platzhalter)",
  ]},
  { v: "2.5.1", d: "17.07.2026", items: [
    "OCR anhand echter Zählerfotos kalibriert: adaptiver Otsu-Threshold, PSM-6-Segmentierung, Mehrfach-Pass",
    "Realistischere Scanner-Hinweise (Beta)",
  ]},
  { v: "2.5.0", d: "17.07.2026", items: [
    "HA-Benachrichtigung bei überfälliger Ablesung (persistent, verschwindet nach Ablesung automatisch)",
    "Gesamt-Export: alle Systeme als CSV + Systemkonfiguration in einem ZIP",
    "Einheiten-Umrechnung für HA-Sensoren (Wh/kWh/MWh, L/m³) mit wählbarer Quelleinheit",
    "Löschen-Buttons ans UI-Design angeglichen (Pill-Form)",
    "Chart: X-Labels dünnen ab 40 Punkten automatisch aus",
  ]},
  { v: "2.4.0", d: "17.07.2026", items: [
    "Löschen überarbeitet: 3-Sekunden-Halten mit Fortschritts-Outline + Bestätigung",
    "Systeme endgültig löschbar (Falschanlage) inkl. aller Ablesungen",
    "Zählerstand-Übernahme aus Home Assistant (Entity pro System konfigurierbar)",
    "Versionsverlauf in den Optionen", "Foto-Scanner als Beta markiert", "Fälligkeit ab 2 Monaten in Monaten angezeigt",
  ]},
  { v: "2.3.x", d: "17.07.2026", items: [
    "Material-Design-3-Redesign (Farben, Typografie, Navigation Rail/Bottom-Bar, FAB, Ripple)",
    "Ablesungen bearbeitbar", "Zählertausch: Endstand alt + Startstand neu am selben Tag",
    "Foto-Scan: 7-Segment-Modell, Galerie-Upload mit EXIF-Datum", "Diverse Mobile-Fixes",
  ]},
  { v: "2.2.0", d: "17.07.2026", items: [
    "Ø-Preis pro System (Kostenschätzung, als ≈ markiert)", "Ablese-Intervall pro System",
    "SQLite-WAL + DB im HA-Backup (/config)", "Dashboard-Endpoint (1 Request statt 3)", "OCR-Scanner (Beta)",
  ]},
  { v: "2.1.0", d: "16.07.2026", items: ["HA-Add-on-Repository mit Auto-Update", "Ein-Klick-Deploy (deploy.ps1)"] },
  { v: "2.0.0", d: "16.07.2026", items: ["Standalone: InfluxDB durch SQLite ersetzt, LXC überflüssig"] },
  { v: "1.x", d: "15.07.2026", items: ["Erstversion: FastAPI + InfluxDB + Vue 3, CSV-Import, PDF-Berichte, Dark Mode"] },
];

/* ---------- Theme (Light/Dark, System-follow + manuell) ---------- */
/* Drei unabhaengige Achsen: Modus (hell/dunkel/auto), Palette, Kontrast.
   Alle drei werden als data-Attribute am <html> gesetzt; das CSS kombiniert sie. */
const PALETTES = [
  { key: "teal",   label: "Teal",   swatch: "#00696F" },
  { key: "indigo", label: "Indigo", swatch: "#4A5C92" },
  { key: "ember",  label: "Ember",  swatch: "#984716" },
];
const CONTRASTS = [
  { key: "standard", label: "Standard" },
  { key: "high",     label: "Hoher Kontrast" },
];
const themeStore = reactive({
  mode:     localStorage.getItem("zw_theme") || "auto",
  palette:  localStorage.getItem("zw_palette") || "teal",
  contrast: localStorage.getItem("zw_contrast") || "standard",
  dark: false,
});
function applyTheme() {
  const sysDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const sysContrast = window.matchMedia("(prefers-contrast: more)").matches;
  themeStore.dark = themeStore.mode === "dark" || (themeStore.mode === "auto" && sysDark);
  const el = document.documentElement;
  el.setAttribute("data-theme", themeStore.dark ? "dark" : "light");
  el.setAttribute("data-palette", themeStore.palette);
  // Systemweite Kontrastpraeferenz gewinnt, wenn der Nutzer nichts Eigenes gewaehlt hat
  el.setAttribute("data-contrast",
    themeStore.contrast === "standard" && sysContrast ? "high" : themeStore.contrast);
}
function setTheme(mode) {
  themeStore.mode = mode;
  localStorage.setItem("zw_theme", mode);
  applyTheme();
}
function setPalette(key) {
  themeStore.palette = key;
  localStorage.setItem("zw_palette", key);
  applyTheme();
}
function setContrast(key) {
  themeStore.contrast = key;
  localStorage.setItem("zw_contrast", key);
  applyTheme();
}
applyTheme();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (themeStore.mode === "auto") applyTheme();
});
window.matchMedia("(prefers-contrast: more)").addEventListener("change", () => {
  if (themeStore.contrast === "standard") applyTheme();
});
// aktuelle Theme-Farbe aus CSS lesen (für Chart.js)
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/* ---------- Chart-Farben (nutzerdefiniert, geraetelokal) ----------
   Bewusst localStorage statt SQLite: das Repo hat KEIN Schema-Migrations-
   verfahren (SQLModel.create_all legt nur an, aendert nichts). Eine neue
   Spalte wuerde Bestandsinstallationen mit "no such column" brechen.
   Systemfarben (System.farbe) bleiben dagegen in SQLite - sie werden auch
   serverseitig fuer die PDF-Berichte gebraucht.
   null / "" = Theme-Standard verwenden (Fallback auf die M3-Rolle).        */
const CHART_COLOR_KEYS = [
  { key: "outlier", label: "Ausreißer-Markierung", role: "--md-outlier" },
  { key: "grid",    label: "Gitternetz",           role: "--chart-grid" },
  { key: "axis",    label: "Achsenbeschriftung",   role: "--ink-soft" },
];
function loadChartPrefs() {
  try { return JSON.parse(localStorage.getItem("zw_chart_colors")) || {}; }
  catch (_) { return {}; }
}
const chartPrefs = reactive(loadChartPrefs());
function setChartColor(key, value) {
  if (value) chartPrefs[key] = value; else delete chartPrefs[key];
  localStorage.setItem("zw_chart_colors", JSON.stringify(chartPrefs));
}
function resetChartColors() {
  Object.keys(chartPrefs).forEach((k) => delete chartPrefs[k]);
  localStorage.removeItem("zw_chart_colors");
}
/* Nutzerwert schlaegt Theme-Rolle schlaegt Literal-Fallback */
function chartColor(key, fallback) {
  const def = CHART_COLOR_KEYS.find((c) => c.key === key);
  return chartPrefs[key] || (def && cssVar(def.role)) || fallback;
}

/* ---------- Kontrastpruefung (WCAG 2.1 relative Luminanz) ---------- */
function hexToRgb(hex) {
  const h = String(hex || "").replace("#", "");
  const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  if (f.length !== 6) return null;
  return [0, 2, 4].map((i) => parseInt(f.slice(i, i + 2), 16));
}
function luminance(hex) {
  const rgb = hexToRgb(hex);
  if (!rgb) return null;
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrastRatio(a, b) {
  const la = luminance(a), lb = luminance(b);
  if (la === null || lb === null) return null;
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}
/* Verhaeltnis der Farbe zur aktuellen Chart-Flaeche; <3:1 = auf dem Untergrund kaum sichtbar */
function contrastToSurface(hex) {
  const surface = cssVar("--md-surface-c-low") || (themeStore.dark ? "#161D1D" : "#EFF5F5");
  return contrastRatio(hex, surface);
}

/* ---------- Stammdaten / Konstanten ---------- */
const SYSTEM_TYPES = [
  { v: "Strom",          unit: "kWh", icon: "⚡" },
  { v: "Gas",            unit: "m³",  icon: "🔥" },
  { v: "Wasser",         unit: "m³",  icon: "💧" },
  { v: "PV-Erzeugung",   unit: "kWh", icon: "☀" },
  { v: "PV-Einspeisung", unit: "kWh", icon: "⬆" },
  { v: "Custom",         unit: "",    icon: "▦" },
];
// Felder, die es bei JEDEM System gibt (Kosten-Fallback + Fälligkeit)
const COMMON_FIELDS = [
  { key: "preis", label: "Ø-Preis €/Einheit (für Kostenschätzung, optional)", type: "number" },
  { key: "abschlag", label: "Monatlicher Abschlag € (für Prognose-Warnung, optional)", type: "number" },
  { key: "abrechnungsmonat", label: "Abrechnungsjahr beginnt im Monat (leer = Januar)", type: "select",
    options: ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    labels: { "": "Januar (Kalenderjahr)", "1": "Januar", "2": "Februar", "3": "März", "4": "April",
              "5": "Mai", "6": "Juni", "7": "Juli", "8": "August", "9": "September",
              "10": "Oktober", "11": "November", "12": "Dezember" } },
  { key: "ablese_intervall_tage", label: "Ablese-Intervall in Tagen (für Fälligkeit, optional)", type: "number" },
  { key: "ha_entity", label: "HA-Entity Zählerstand (optional, z. B. sensor.stromzaehler)", type: "text" },
  { key: "mqtt_topic", label: "MQTT-Topic (optional, z. B. tele/hichi/SENSOR)", type: "text" },
  { key: "mqtt_path", label: "MQTT JSON-Pfad (optional, z. B. MT631.Total_in)", type: "text" },
  { key: "mqtt_interval", label: "MQTT-Speicherintervall (leer = globale Vorgabe)", type: "select",
    options: ["", "daily", "weekly", "monthly", "quarterly", "yearly"],
    labels: { "": "Globale Vorgabe", daily: "Täglich", weekly: "Wöchentlich",
              monthly: "Monatlich", quarterly: "Quartalsweise", yearly: "Jährlich" } },
  { key: "ha_unit", label: "Einheit des HA-Sensors (leer = wie von HA gemeldet)", type: "select",
    options: ["", "Wh", "kWh", "MWh", "L", "m³"] },
];

/* ---------- Einheiten-Umrechnung (HA-Sensor -> Systemeinheit) ---------- */
const UNIT_FACTORS = {
  energie: { "wh": 0.001, "kwh": 1, "mwh": 1000 },        // Basis kWh
  volumen: { "l": 0.001, "dm³": 0.001, "dm3": 0.001, "m³": 1, "m3": 1 },  // Basis m³
};
function normUnit(u) { return String(u || "").trim().toLowerCase().replace("m3", "m³"); }
function convertUnit(value, fromU, toU) {
  const f = normUnit(fromU), t = normUnit(toU);
  if (!f || !t || f === t) return { value, converted: false };
  for (const cat of Object.values(UNIT_FACTORS)) {
    if (f in cat && t in cat) return { value: value * cat[f] / cat[t], converted: true };
  }
  return null;  // inkompatibel (z. B. Wh -> m³)
}
const EXTRA_FIELDS = {
  "Gas":            [{ key: "brennwert", label: "Brennwert (kWh/m³)", type: "number" },
                     { key: "zustandszahl", label: "Zustandszahl (Standard 0,95)", type: "number" }],
  "PV-Erzeugung":   [{ key: "kwp",           label: "Installierte Leistung (kWp)", type: "number" }],
  "PV-Einspeisung": [{ key: "verguetung_ct", label: "Einspeisevergütung (ct/kWh)", type: "number" }],
};
const PALETTE = ["#0e7c86", "#d9820a", "#3b6fb5", "#2f8f5b", "#a4508b", "#c0453b", "#6b7280", "#0891b2"];

/* ---------- Navigation (Sidebar) ----------
   Zentrale Deklaration statt dupliziertem Markup in Rail und Bottom-Bar.
   `action` verweist auf eine Methode der Root-App; `disabled` = Platzhalter
   für noch nicht implementierte Bereiche (Admin-Tools).                     */
const SVG = {
  home:   '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11 L12 3 L21 11"/><path d="M5 10 V20 H19 V10"/></svg>',
  report: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="M9 15l3 3 3-3"/></svg>',
  cog:    '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  admin:  '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 4.4-2.9 8.2-7 10-4.1-1.8-7-5.6-7-10V6z"/><path d="M9.5 12l1.8 1.8L15 10"/></svg>',
  chart: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/></svg>',
  grid: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>',
  menu:   '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>',
};
const NAV_ITEMS = [
  /* "Auswertungen" ist ein reiner Elternpunkt: er navigiert auf sein erstes
     Kind statt auf eine eigene Seite. Ein Menüpunkt ohne Ziel wäre eine
     Sackgasse, und M3 verlangt, dass ein Navigationsziel navigiert. */
  { key: "auswertungen", label: "Auswertungen", short: "Analyse",   icon: SVG.chart,  action: "openDashboard",      primary: true,
    children: [
      { key: "dashboard", label: "Dashboard", icon: SVG.grid,   action: "openDashboard" },
      { key: "bericht",   label: "Bericht",   icon: SVG.report, action: "openCombinedReport", needsExport: true },
    ] },
  { key: "zaehlwerk",    label: "Zählwerk",     short: "Zählwerk",  icon: SVG.home,   action: "back",               primary: true, expandable: true },
  { key: "einstellungen",label: "Einstellungen",short: "Optionen",  icon: SVG.cog,    action: "openSettings",       primary: true },
  { key: "admin",        label: "Admin-Tools",  short: "Admin",     icon: SVG.admin,  action: "openAdmin",          primary: true, adminOnly: true },
];
const NAV_BREAKPOINT = 840;   // identisch zum CSS-Breakpoint Rail <-> Bottom-Bar

/* =========================================================================
   Hardware-Empfehlung fuer Smart-Meter-Nachruestung
   -------------------------------------------------------------------------
   Regelbasiert, bewusst kein Scoring-Modell: die Zuordnung Zaehlerbauart ->
   Ausleseverfahren ist deterministisch und nachvollziehbar. Jede Regel
   liefert mit, WORAN sie erkannt hat und wie sicher das ist - damit der
   Nutzer eine Fehlzuordnung sofort sieht, statt einer Blackbox zu vertrauen.

   Reihenfolge = Spezifitaet. Die erste zutreffende Regel je Medium gewinnt,
   generische Regeln greifen nur als Rueckfallebene.
   ========================================================================= */
const HW_CONFIDENCE = {
  sicher:       { label: "eindeutig",   rank: 3 },
  wahrscheinlich:{ label: "wahrscheinlich", rank: 2 },
  generisch:    { label: "Rückfallebene", rank: 1 },
};

/* Normalisiert Freitext: Kleinschreibung, Umlaute, Sonderzeichen raus.
   "Balgengaszähler" / "balgengas-zaehler" / "BALGENGASZAEHLER" -> gleich. */
function hwNorm(s) {
  return String(s || "").toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, " ").trim();
}
const hwHas = (hay, ...needles) => needles.some((n) => hwNorm(hay).includes(hwNorm(n)));

const HW_RULES = [
  /* ---------------- Strom ---------------- */
  {
    id: "strom-imsys",
    medium: "Strom",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "imsys", "intelligentes messsystem", "smart meter gateway", "smgw")
               || hwHas(c.modell, "smgw"),
    grund: "iMSys bzw. Smart-Meter-Gateway erkannt",
    titel: "Auslesung über die HAN-Schnittstelle des Gateways",
    hardware: [
      "HAN-Adapter des Messstellenbetreibers (CLS-Schnittstelle)",
      "Alternativ: separater eigener Zähler hinter dem iMSys",
    ],
    hinweis: "Ein iMSys gehört dem Messstellenbetreiber und ist plombiert. Der Zugang zur HAN-Schnittstelle wird beim Betreiber beantragt – ein optischer Lesekopf ist hier weder nötig noch zulässig.",
  },
  {
    id: "strom-mme",
    medium: "Strom",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "mme", "moderne messeinrichtung", "ehz")
               || hwHas(c.modell, "mme", "ehz", "q3a", "q3b", "e220", "dd3", "dd4", "sml"),
    grund: "moderne Messeinrichtung mit optischer Schnittstelle (D0/SML)",
    titel: "Optischer Lesekopf an der Infrarot-Schnittstelle",
    hardware: [
      "Hichi IR-Lesekopf (Tasmota vorinstalliert) – Magnethalterung, berührungslos",
      "Alternativ: Tibber Pulse IR oder volkszaehler-Lesekopf mit ESPHome",
    ],
    hinweis: "Für die vollständigen Daten inklusive momentaner Leistung ist meist die vierstellige INF-PIN nötig – kostenlos beim Messstellenbetreiber anzufordern. Ohne PIN liefert der Zähler nur den Zählerstand.",
  },
  {
    id: "strom-ferraris",
    medium: "Strom",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "ferraris", "drehscheibe", "induktionszaehler")
               || hwHas(c.bauart, "wechselstromzaehler", "drehstromzaehler"),
    grund: "mechanischer Zähler mit rotierender Scheibe",
    titel: "Reflexlichtschranke auf die Markierung der Drehscheibe",
    hardware: [
      "TCRT5000 Reflexkoppler an ESP32/ESP8266 mit ESPHome",
      "Alternativ: Hichi Ferraris-Sensor (fertig konfektioniert)",
    ],
    hinweis: "Die Umdrehungszahl pro kWh steht auf dem Typenschild (z. B. 75 U/kWh) und muss in der Konfiguration hinterlegt werden. Der Sensor wird außen aufgeklebt, die Plombe bleibt unberührt.",
  },

  /* ---------------- Gas ---------------- */
  {
    id: "gas-balgen",
    medium: "Gas",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "balgengas", "balgen")
               || hwHas(c.modell, "bk g4", "bk g6", "bk4", "g4 rf1", "g4"),
    grund: "Balgengaszähler erkannt",
    titel: "Reed-Kontakt an der Magnetziffer",
    hardware: [
      "Reed-Kontakt oder Hall-Sensor an ESP32/ESP8266 mit ESPHome",
      "Fertiglösung: Impulsgeber des Herstellers (z. B. Elster IN-Z61)",
    ],
    hinweis: "Voraussetzung ist ein Magnet in der letzten Ziffernrolle – erkennbar an einem Punkt oder Stern neben der Ziffer, oder per Reed-Test. Fehlt er, bleibt nur die Kameralösung.",
    fallbackId: "universal-kamera",
  },
  {
    id: "gas-ultraschall",
    medium: "Gas",
    confidence: "wahrscheinlich",
    match: (c) => hwHas(c.bauart, "ultraschall", "drehkolben", "turbinenrad"),
    grund: "elektronischer Gaszähler",
    titel: "Auslesung über die vorhandene Datenschnittstelle",
    hardware: [
      "Optischer Lesekopf, falls IR-Schnittstelle vorhanden",
      "M-Bus- oder wM-Bus-Empfänger, je nach Ausstattung",
    ],
    hinweis: "Elektronische Gaszähler bringen die Schnittstelle meist mit. Welche es ist, steht im Datenblatt zum Modell – Bauart und Modell hier vollständig eintragen hilft bei der Eingrenzung.",
  },

  /* ---------------- Wasser ---------------- */
  {
    id: "wasser-ultraschall",
    medium: "Wasser",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "ultraschall") || hwHas(c.modell, "ultraschall"),
    grund: "Ultraschall-Wasserzähler, sendet in der Regel per Funk",
    titel: "wM-Bus-Empfänger auf 868 MHz",
    hardware: [
      "ESP32 mit CC1101-Funkmodul und wM-Bus-Firmware",
      "Alternativ: USB-Stick mit wM-Bus-Empfang plus wmbusmeters",
    ],
    hinweis: "Viele Zähler senden verschlüsselt. Der AES-Schlüssel gehört zum Zähler und wird beim Versorger angefragt – ohne ihn kommen nur Telegramme ohne lesbare Werte an.",
  },
  {
    id: "wasser-fluegelrad",
    medium: "Wasser",
    confidence: "sicher",
    match: (c) => hwHas(c.bauart, "fluegelrad", "woltmann", "mehrstrahl", "einstrahl")
               || hwHas(c.hersteller, "pipersberg"),
    grund: "mechanischer Wasserzähler mit Rollenzählwerk",
    titel: "Kamerabasierte Zifferblatt-Erkennung",
    hardware: [
      "AI-on-the-edge-device auf ESP32-CAM",
      "Alternativ: Reed-Kontakt, falls eine Ziffernrolle einen Magneten trägt",
    ],
    hinweis: "Die Kameralösung braucht eine feste Halterung und gleichmäßige Beleuchtung – beides bringt das fertige Gehäuse mit. Sie ist berührungslos und damit unabhängig von Plomben.",
  },

  /* ---------------- Medienunabhängig ---------------- */
  {
    id: "universal-kamera",
    medium: null,
    confidence: "generisch",
    match: (c) => ["Strom", "Gas", "Wasser"].includes(c.typ),
    grund: "funktioniert an jedem Rollenzählwerk, unabhängig von Bauart und Hersteller",
    titel: "Kamerabasierte Zifferblatt-Erkennung",
    hardware: ["AI-on-the-edge-device auf ESP32-CAM"],
    hinweis: "Die Rückfallebene, wenn keine elektrische oder optische Schnittstelle existiert. Liefert den Zählerstand, aber keine Momentanwerte.",
  },
  {
    id: "pv-wechselrichter",
    medium: null,
    confidence: "wahrscheinlich",
    match: (c) => c.typ === "PV-Erzeugung" || c.typ === "PV-Einspeisung",
    grund: "PV-Daten kommen vom Wechselrichter, nicht vom Zähler",
    titel: "Anbindung des Wechselrichters statt des Zählers",
    hardware: [
      "Modbus TCP oder RTU zum Wechselrichter (SunSpec)",
      "Alternativ: Hersteller-Integration in Home Assistant",
    ],
    hinweis: "Für die Einspeisung ist zusätzlich der Zweirichtungszähler relevant – dafür gelten die Empfehlungen zu Strom.",
  },
];

/* Liefert die Empfehlungen zu einem Zaehler. Erste passende spezifische Regel
   je Medium plus die generische Rueckfallebene, falls sie nicht ohnehin traf. */
function hwSuggest(meter, system) {
  const ctx = {
    typ: system ? system.typ : null,
    bauart: meter ? meter.bauart : null,
    modell: meter ? meter.modell : null,
    hersteller: meter ? meter.hersteller : null,
  };
  const hits = [];
  const spezifisch = HW_RULES.filter(
    (r) => r.medium && r.medium === ctx.typ && r.match(ctx));
  if (spezifisch.length) hits.push(spezifisch[0]);
  HW_RULES.filter((r) => !r.medium && r.match(ctx)).forEach((r) => {
    if (!hits.some((h) => h.id === r.id)) hits.push(r);
  });
  // Wenn eine spezifische Regel griff, ist die generische Kamera nur noch
  // Beiwerk -> nach hinten und als solche markiert.
  return hits.map((r) => ({ ...r, conf: HW_CONFIDENCE[r.confidence] }))
             .sort((a, b) => b.conf.rank - a.conf.rank);
}

/* =========================================================================
   Dashboard-Kacheln
   -------------------------------------------------------------------------
   Bewusst ohne zusätzliche Bibliothek. Eine Drag-and-Drop-Rasterbibliothek
   käme über ein Auslieferungsnetz herein und liefe damit dem Offline-Ziel
   und dem Kill-Switch aus 2.12.0 zuwider. Die native Drag-Schnittstelle des
   Browsers reicht für ein Raster mit vier Spalten vollständig aus.
   ========================================================================= */
/* Herkunft eines Datensatzes. Die Kennungen stehen so in der Datenbank; die
   Beschriftung bleibt hier, damit sie sich ändern lässt, ohne Daten anzufassen. */
const SOURCE_LABELS = {
  manual: "Manuell", mqtt: "MQTT", ha_api: "HA", import: "Import",
};
// function-Deklaration statt const: kompilierte Vue-Templates laufen ohne
// Zugriff auf den umgebenden Modul-Scope und lösen Bezeichner nur über `this`
// oder `window` auf. Eine function-Deklaration hängt sich am Skript-Top-Level
// an window - eine const-Zuweisung mit Pfeilfunktion (wie bisher hier) tut
// das nicht und wäre im Template als "sourceLabel is not a function"
// gescheitert, sobald tatsächlich eine Ablesung mit abweichender Quelle
// existiert (bis zum Fix des source-Persistenz-Bugs kam das nie vor).
function sourceLabel(s) { return SOURCE_LABELS[s] || s; }

const WIDGET_TYPES = [
  { key: "latest_reading", label: "Letzter Stand",   needsSystem: true,  multi: false, w: 1, h: 1 },
  { key: "line_chart",     label: "Verlauf",         needsSystem: true,  multi: true,  w: 2, h: 2 },
  { key: "pie_chart",      label: "Verteilung",      needsSystem: false, multi: false, w: 1, h: 2 },
  { key: "cost_summary",   label: "Kosten",          needsSystem: false, multi: false, w: 1, h: 1 },
  { key: "trend",          label: "Trend",           needsSystem: true,  multi: false, w: 1, h: 1 },
  { key: "cost_forecast",  label: "Kostenprognose",  needsSystem: true,  multi: false, w: 1, h: 1 },
];

/* Zeiträume je Kachel. Die Tagesangaben werden clientseitig auf die vom
   Server gelieferte Reihe angewandt – ein eigener Abruf je Kachel wäre bei
   acht Kacheln ein Vielfaches an Anfragen. */
const TIMEFRAMES = [
  { key: "7d",  label: "7 Tage",   days: 7 },
  { key: "30d", label: "30 Tage",  days: 30 },
  { key: "90d", label: "90 Tage",  days: 90 },
  { key: "ytd", label: "Lfd. Jahr", days: null },
  { key: "12m", label: "12 Monate", days: 365 },
  { key: "all", label: "Gesamt",   days: null },
  { key: "custom", label: "Benutzerdefiniert", days: null },
];

function sliceSeries(series, timeframe, from, to) {
  if (!series || !series.length || timeframe === "all") return series || [];
  if (timeframe === "custom") {
    if (!from && !to) return series;
    return series.filter((p) => (!from || p.d >= from) && (!to || p.d <= to));
  }
  const now = new Date();
  let cutoff;
  if (timeframe === "ytd") cutoff = new Date(now.getFullYear(), 0, 1);
  else {
    const def = TIMEFRAMES.find((t) => t.key === timeframe);
    if (!def || !def.days) return series;
    cutoff = new Date(now.getTime() - def.days * 86400000);
  }
  const iso = cutoff.toISOString().slice(0, 10);
  return series.filter((p) => p.d >= iso);
}
const WIDGET_LABEL = Object.fromEntries(WIDGET_TYPES.map((w) => [w.key, w.label]));

/* Kleines Verlaufsdiagramm. Eigene Komponente statt EnergyChart: die dort
   verbaute Achsen- und Legendenlogik ist für eine Kachel zu schwer, und ein
   zweiter Chart.js-Aufbau je Kachel kostet spürbar Zeit. */
const WidgetLineChart = {
  props: ["data", "series"],
  data: () => ({ chart: null }),
  mounted() { this.draw(); },
  unmounted() { this.destroyChart(); },
  watch: { series: { handler() { this.draw(); }, deep: true } },
  methods: {
    // stop() vor destroy(): ohne sie kann Chart.js' Animator noch einen
    // Frame für die alte Instanz einplanen, der nach destroy() auf
    // ctx == null trifft ("Cannot read properties of null (reading 'save')") –
    // besonders wenn eine Kachel kurz nach dem Anlegen erneut konfiguriert wird.
    destroyChart() {
      if (!this.chart) return;
      this.chart.stop();
      this.chart.destroy();
      this.chart = null;
    },
    draw() {
      const sets = (this.series || []).filter((s) => s.points && s.points.length);
      if (!this.$refs.cv || !sets.length) return;
      this.destroyChart();

      // Gemeinsame Zeitachse über alle Reihen: ohne sie zeichnete Chart.js
      // die zweite Reihe gegen die Beschriftungen der ersten und verschöbe sie.
      const labels = [...new Set(sets.flatMap((s) => s.points.map((p) => p.d)))].sort();
      const multi = sets.length > 1;
      // Bei mehreren Systemen jede Reihe auf eigener Achse: kWh und m³ haben
      // keinen gemeinsamen Maßstab, übereinandergelegt wäre eine davon platt.
      const datasets = sets.map((s, i) => {
        const byDay = Object.fromEntries(s.points.map((p) => [p.d, p.v]));
        return {
          label: `${s.name} (${s.einheit})`,
          data: labels.map((d) => (d in byDay ? byDay[d] : null)),
          borderColor: s.farbe || cssVar("--md-primary") || "#0e7c86",
          borderWidth: 2, tension: 0.25, pointRadius: 0, fill: false, spanGaps: true,
          yAxisID: multi ? `y${i}` : "y",
        };
      });
      const scales = {
        x: { display: false },
      };
      if (multi) {
        sets.forEach((s, i) => {
          scales[`y${i}`] = {
            position: i === 0 ? "left" : "right",
            display: i < 2,                    // mehr als zwei Achsen sind unlesbar
            grid: { drawOnChartArea: i === 0, color: chartColor("grid", "#e2e8ee") },
            ticks: { maxTicksLimit: 4, color: s.farbe, font: { size: 9 } },
          };
        });
      } else {
        scales.y = { ticks: { maxTicksLimit: 4, color: chartColor("axis", "#5b6b7b"), font: { size: 9 } },
                     grid: { color: chartColor("grid", "#e2e8ee") } };
      }

      this.chart = new Chart(this.$refs.cv, {
        type: "line",
        data: { labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          // Kacheln werden im Bearbeitungsmodus gezogen, skaliert und neu
          // eingerichtet – oft innerhalb der sonst rund einsekündigen
          // Eintrittsanimation der vorigen Instanz. Läuft dabei ein Resize
          // in Chart.js' Animator hinein, greift dessen Redraw teils auf
          // eine schon zerstörte Instanz zu ("Cannot read properties of
          // null (reading 'save')"). Ohne Animation entfällt das Zeitfenster.
          animation: false,
          interaction: { intersect: false, mode: "index" },
          plugins: {
            legend: { display: multi, position: "bottom",
                      labels: { boxWidth: 10, font: { size: 10 },
                                color: cssVar("--md-on-surface-variant") } },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.parsed.y, 2)}`,
              },
            },
          },
          scales,
        },
      });
    },
  },
  template: `
    <div class="wg-body wg-chart">
      <canvas ref="cv"></canvas>
      <div class="wg-empty" v-if="!series || !series.some(s => s.points && s.points.length)">
        Keine Werte im Zeitraum
      </div>
    </div>`,
};

/* Verteilung über alle Systeme. Verglichen werden Kosten, nicht Verbräuche:
   kWh und m³ lassen sich nicht sinnvoll in einem Kreis gegenüberstellen. */
const WidgetPieChart = {
  props: ["systems"],
  data: () => ({ chart: null }),
  mounted() { this.draw(); },
  unmounted() { this.destroyChart(); },
  watch: { systems: { handler() { this.draw(); }, deep: true } },
  computed: {
    withCost() {
      return (this.systems || []).filter((s) => (s.total_cost_tariff || s.total_cost) > 0);
    },
  },
  methods: {
    // Siehe WidgetLineChart.destroyChart(): stop() vor destroy() verhindert
    // einen bereits eingeplanten Animationsframe der alten Instanz.
    destroyChart() {
      if (!this.chart) return;
      this.chart.stop();
      this.chart.destroy();
      this.chart = null;
    },
    draw() {
      if (!this.$refs.cv || !this.withCost.length) return;
      this.destroyChart();
      this.chart = new Chart(this.$refs.cv, {
        type: "doughnut",
        data: {
          labels: this.withCost.map((s) => s.name),
          datasets: [{
            data: this.withCost.map((s) => s.total_cost_tariff || s.total_cost),
            backgroundColor: this.withCost.map((s) => s.farbe),
            borderWidth: 0,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "58%",
          // Siehe WidgetLineChart: Animation aus, damit ein Resize während
          // der Bearbeitung nicht in eine laufende Eintrittsanimation läuft.
          animation: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                boxWidth: 10, font: { size: 10 },
                color: cssVar("--md-on-surface-variant"),
                // Absolutwert schon in der Legende: der Anteil allein sagt
                // nichts darüber, worüber man spricht.
                generateLabels: (chart) => {
                  const ds = chart.data.datasets[0];
                  const sum = ds.data.reduce((a, b) => a + b, 0) || 1;
                  return chart.data.labels.map((label, i) => ({
                    text: `${label} · ${fmt(ds.data[i])} € (${Math.round(ds.data[i] / sum * 100)} %)`,
                    fillStyle: ds.backgroundColor[i], strokeStyle: ds.backgroundColor[i],
                    index: i,
                  }));
                },
              },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const sum = ctx.dataset.data.reduce((a, b) => a + b, 0) || 1;
                  const s = this.withCost[ctx.dataIndex];
                  const menge = s && s.total_consumption
                    ? ` · ${fmt(s.total_consumption)} ${s.einheit}` : "";
                  return `${fmt(ctx.parsed)} € (${(ctx.parsed / sum * 100).toFixed(1)} %)${menge}`;
                },
              },
            },
          },
        },
      });
    },
  },
  template: `
    <div class="wg-body wg-chart">
      <canvas ref="cv"></canvas>
      <div class="wg-empty" v-if="!withCost.length">Keine Kosten hinterlegt</div>
    </div>`,
};

const WidgetLatestReading = {
  props: ["data"],
  template: `
    <div class="wg-body wg-metric" v-if="data">
      <div class="wg-val num">{{ data.latest === null ? '–' : fmt(data.latest, 1) }}<span class="wg-unit">{{ data.einheit }}</span></div>
      <div class="wg-sub">{{ data.latest_datum ? fmtDate(data.latest_datum) : 'noch keine Ablesung' }}</div>
      <div class="wg-sub" v-if="data.avg_per_day">Ø {{ fmt(data.avg_per_day, 2) }} {{ data.einheit }}/Tag</div>
    </div>
    <div class="wg-body wg-empty" v-else>Kein System zugeordnet</div>`,
  methods: { fmt, fmtDate },
};

/* Trend: laufende gegen vorherige Periode gleicher Länge. Aussagekräftiger
   als ein absoluter Wert, weil Verbrauch stark saisonal schwankt. */
const WidgetTrend = {
  props: ["data", "timeframe", "rangeFrom", "rangeTo"],
  computed: {
    calc() {
      const pts = sliceSeries((this.data || {}).series, this.timeframe || "30d", this.rangeFrom, this.rangeTo);
      if (!pts.length) return null;
      const half = Math.floor(pts.length / 2);
      if (half < 1) return null;
      const avg = (arr) => arr.reduce((s, p) => s + p.v, 0) / arr.length;
      const prev = avg(pts.slice(0, half));
      const curr = avg(pts.slice(half));
      if (!prev) return null;
      const pct = (curr - prev) / prev * 100;
      return { curr, prev, pct,
               dir: pct > 2 ? "up" : pct < -2 ? "down" : "flat" };
    },
  },
  template: `
    <div class="wg-body wg-metric" v-if="calc">
      <div class="wg-val num" :class="'trend-' + calc.dir">
        {{ calc.pct > 0 ? '▲' : calc.pct < 0 ? '▼' : '▬' }}
        {{ Math.abs(calc.pct).toFixed(1) }}<span class="wg-unit">%</span>
      </div>
      <div class="wg-sub">{{ fmt(calc.curr, 2) }} statt {{ fmt(calc.prev, 2) }} {{ data.einheit }}/Tag</div>
      <div class="wg-sub">{{ calc.dir === 'down' ? 'weniger als zuvor' : calc.dir === 'up' ? 'mehr als zuvor' : 'unverändert' }}</div>
    </div>
    <div class="wg-body wg-empty" v-else>Zu wenige Werte für einen Trend</div>`,
  methods: { fmt },
};

/* Kostenprognose fürs NÄCHSTE Abrechnungsjahr. Grundlage ist ein serverseitig
   berechneter 5-Jahres-Rolling-Average (nicht mehr die frühere naive
   Jahreshochrechnung über die gesamte Historie). Ist ein Abschlag hinterlegt,
   warnt die Kachel, sobald die Prognose den Jahresabschlag übersteigt. */
const WidgetCostForecast = {
  props: ["data", "timeframe", "rangeFrom", "rangeTo"],
  computed: {
    p() { return (this.data || {}).prognosis || null; },
    prognLabel() {
      const p = this.p;
      if (!p || !p.billing_year_start) return "";
      const s = String(p.billing_year_start), e = String(p.billing_year_end);
      const sy = s.slice(0, 4), ey = e.slice(0, 4);
      return sy === ey ? `Abrechnungsjahr ${sy}`
                       : `${s.slice(5, 7)}/${sy} – ${e.slice(5, 7)}/${ey}`;
    },
  },
  template: `
    <div class="wg-body wg-metric" v-if="p && p.projected_cost !== null">
      <div class="wg-val num" :class="{ 'wg-over': p.exceeds_abschlag }">{{ fmt(p.projected_cost) }}<span class="wg-unit">€</span></div>
      <div class="wg-sub">{{ prognLabel }} · ≈ {{ fmt(p.projected_consumption) }} {{ data.einheit }}</div>
      <div class="wg-sub">Ø {{ fmt(p.avg_per_day, 2) }} {{ data.einheit }}/Tag ({{ p.window_years }}-Jahre-Schnitt)</div>
      <div class="wg-warn" v-if="p.exceeds_abschlag">⚠ {{ fmt(p.shortfall) }} € über dem Jahresabschlag ({{ fmt(p.abschlag_annual) }} €)</div>
      <div class="wg-ok" v-else-if="p.abschlag_annual">✓ im Rahmen des Abschlags ({{ fmt(p.abschlag_annual) }} €)</div>
    </div>
    <div class="wg-body wg-metric" v-else-if="p">
      <div class="wg-val num">≈ {{ fmt(p.projected_consumption) }}<span class="wg-unit">{{ data.einheit }}</span></div>
      <div class="wg-sub">{{ prognLabel }} · Ø {{ fmt(p.avg_per_day, 2) }}/Tag</div>
      <div class="wg-sub">Kein Preis hinterlegt – Tarif ergänzen</div>
    </div>
    <div class="wg-body wg-empty" v-else>Zu wenige Werte für eine Prognose</div>`,
  methods: { fmt },
};

const WidgetCostSummary = {
  props: ["systems"],
  computed: {
    total() {
      return (this.systems || []).reduce(
        (sum, s) => sum + (s.total_cost_tariff || s.total_cost || 0), 0);
    },
    tariffBased() {
      return (this.systems || []).some((s) => s.total_cost_tariff);
    },
  },
  template: `
    <div class="wg-body wg-metric">
      <div class="wg-val num">{{ fmt(total) }}<span class="wg-unit">€</span></div>
      <div class="wg-sub">{{ tariffBased ? 'nach hinterlegten Tarifen' : 'aus erfassten Kosten' }}</div>
      <div class="wg-sub">{{ (systems || []).length }} Systeme im Zeitraum</div>
    </div>`,
  methods: { fmt },
};

/* ---------- Helfer ---------- */
/* Zentrale Stelle für Sitzungsverlust. Statt an jedem Aufruf einzeln auf 401
   zu prüfen, meldet der Interceptor es einmal – die Oberfläche blendet dann
   die Anmeldung ein. Der Rückruf wird von der App beim Start gesetzt. */
const authStore = reactive({ status: null, checked: false });

/* Rechte modulweit verfügbar machen: die Root-App und die Unterkomponenten
   müssen dieselbe Quelle nutzen, sonst blendet die eine aus, was die andere
   noch anzeigt. Durchgesetzt werden die Rechte ohnehin im Backend. */
function perms() {
  return (authStore.status || {}).permissions
         || { role: "guest", write: false, admin: false, export: false, settings: false };
}
const canWriteNow = () => !!perms().write;
const canExportNow = () => !!perms().export;
let onUnauthorized = () => {};

async function api(path, opts = {}) {
  // Führenden Slash entfernen -> relativer Request. Funktioniert direkt (LXC)
  // UND hinter Home-Assistant-Ingress (dynamischer Basis-Pfad).
  const url = path.replace(/^\//, "");
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    // Sitzungscookie mitsenden. Nötig, weil das Token als HttpOnly-Cookie
    // gehalten wird und für JavaScript unsichtbar ist.
    credentials: "same-origin",
    ...opts,
  });
  if (res.status === 401) {
    authStore.status = { ...(authStore.status || {}), authenticated: false };
    onUnauthorized();
    throw new Error("Sitzung abgelaufen – bitte neu anmelden");
  }
  if (!res.ok) {
    let d;
    try { d = await res.json(); } catch (_) {}
    throw new Error((d && d.detail) || res.statusText || "Fehler");
  }
  return res.status === 204 ? null : res.json();
}
const today = () => new Date().toISOString().slice(0, 10);

// Ingress-sicherer Download: holt die Datei im authentifizierten Kontext (fetch mit
// Session-Cookie) und bietet sie als lokalen Blob an. Kein externer Browser -> kein 401.
async function fetchBlobDownload(path, filename) {
  const res = await fetch(path.replace(/^\//, ""));
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
}
function fmt(n, dec = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return Number(n).toLocaleString("de-DE", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function fmtDate(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("de-DE");
}
function typeIcon(typ) {
  const t = SYSTEM_TYPES.find((x) => x.v === typ);
  return t ? t.icon : "▦";
}

/* =========================================================================
   Hold-to-Delete-Button: 3 s halten, Outline zeichnet sich im Uhrzeigersinn,
   erst DANACH feuert @held (Aufrufer zeigt zusätzlich Bestätigungs-Popup).
   ========================================================================= */
const HoldButton = {
  props: { small: Boolean, round: Boolean, title: String },
  emits: ["held"],
  data: () => ({ holding: false }),
  template: `
  <button type="button" class="holdbtn" :class="{small, round, holding}"
          :title="title || 'Zum Löschen 3 Sekunden gedrückt halten'"
          @pointerdown.stop.prevent="start" @pointerup="cancel" @pointerleave="cancel"
          @pointercancel="cancel" @contextmenu.prevent @click.stop.prevent>
    <svg class="hold-ring" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <rect x="3" y="3" width="94" height="94" :rx="round ? 50 : 16" ry="50" pathLength="100" />
    </svg>
    <span class="hold-inner"><slot></slot></span>
  </button>`,
  methods: {
    start() {
      this.holding = true;
      this._t = setTimeout(() => { this.holding = false; this.$emit("held"); }, 3000);
    },
    cancel() { this.holding = false; clearTimeout(this._t); },
  },
  beforeUnmount() { clearTimeout(this._t); },
};

/* =========================================================================
   Chart-Komponente – reiner Renderer (Datasets kommen fertig vom Parent)
   ========================================================================= */
const EnergyChart = {
  props: { labels: Array, datasets: Array, chartType: String, hasY2: Boolean, y2Label: String },
  template: `<div class="chart-box"><canvas ref="cv"></canvas></div>`,
  mounted() { this.schedule(); },
  beforeUnmount() { this.destroy(); },
  computed: {
    isDark() { return themeStore.dark; },
    prefSignature() { return JSON.stringify(chartPrefs); },
  },
  watch: {
    prefSignature() { this.schedule(); },   // Farbwahl -> Chart sofort neu zeichnen
    labels() { this.schedule(); },
    datasets() { this.schedule(); },
    chartType() { this.schedule(); },
    hasY2() { this.schedule(); },
    isDark() { this.schedule(); },   // Theme-Wechsel -> Chartfarben neu
  },
  methods: {
    destroy() {
      const cv = this.$refs.cv;
      if (cv && typeof Chart !== "undefined") {
        const existing = Chart.getChart(cv);   // offizieller Weg: JEDE Instanz am Canvas killen
        if (existing) existing.destroy();
      }
    },
    schedule() {
      if (this._pending) return;
      this._pending = true;
      this.$nextTick(() => { this._pending = false; this.build(); });
    },
    build() {
      const cv = this.$refs.cv;
      if (!cv || typeof Chart === "undefined") return;
      this.destroy();
      const ctx = cv.getContext("2d");
      const grid = chartColor("grid", "#e2e8ee");
      const tick = chartColor("axis", "#5b6b7b");

      // Datasets klonen (Props nicht mutieren) + Gradient-Fläche fürs Primärsystem (Linie)
      const datasets = this.datasets.map((d, i) => {
        const ds = { ...d };
        if (i === 0 && (this.chartType || "line") === "line" && ds.fill !== false) {
          const col = ds.borderColor || "#0e7c86";
          const grad = ctx.createLinearGradient(0, 0, 0, cv.clientHeight || 320);
          grad.addColorStop(0, col + "59");   // oben ~35%
          grad.addColorStop(1, col + "05");   // unten fast transparent
          ds.backgroundColor = grad;
          ds.fill = true;
        }
        return ds;
      });

      const scales = {
        x: { grid: { color: grid }, ticks: {
          color: tick, maxRotation: 90, minRotation: 90, font: { size: 9 },
          // <=40 Punkte: jedes Datum (wie gehabt); darüber automatisch ausdünnen
          autoSkip: this.labels.length > 40, maxTicksLimit: this.labels.length > 40 ? 40 : undefined,
        } },
        y: { grid: { color: grid }, ticks: { color: tick, font: { size: 11 } }, beginAtZero: false, position: "left" },
      };
      if (this.hasY2) {
        scales.y2 = {
          position: "right", beginAtZero: true,
          grid: { drawOnChartArea: false },
          ticks: { color: tick, font: { size: 11 } },
          title: { display: !!this.y2Label, text: this.y2Label, color: tick, font: { size: 10 } },
        };
      }
      new Chart(ctx, {
        type: this.chartType || "line",
        data: { labels: this.labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: datasets.length > 1, position: "bottom", labels: { color: tick, boxWidth: 12, font: { size: 12 } } },
            tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${fmt(c.parsed.y)}` } },
          },
          scales,
        },
      });
    },
  },
};

/* =========================================================================
   System-Detail – Chart + Tabelle + Erfassung + Import
   ========================================================================= */
const SystemDetail = {
  components: { EnergyChart, HoldButton },
  inject: ["notify"],
  props: { system: Object },
  emits: ["back", "edit", "changed", "tab"],
  data: () => ({
    tab: "chart",
    /* Sammelauswahl. Die Kennungen liegen in einem Set, nicht als Marke am
       Datensatz: so überlebt die Auswahl Seitenwechsel, Sortierung und
       Neuladen der Zeilen. */
    sourceFilter: "all",
    selectMode: false,
    selected: new Set(),
    bulkBusy: false,
    // Zähler-Metadaten (v2.10.0) + Hardware-Empfehlung
    meters: [],
    metersLoaded: false,
    // Anzahlen getrennt von den Listen: sie stammen aus dem Dashboard-Request
    // und stehen damit schon vor dem ersten Öffnen des jeweiligen Reiters.
    meterCount: null,
    tariffCount: null,
    showMeter: false,
    meterForm: null,
    bauarten: [],
    tariffs: [],
    tariffsLoaded: false,
    showTariff: false,
    tariffForm: null,
    loading: true,
    readings: [],
    stats: null,
    chartData: null,
    // Chart-Steuerung
    mode: "consumption",       // value | consumption | per_day
    chartType: "line",         // line | bar
    range: "all",              // week | month | year | all
    overlayIds: [],
    overlayData: {},
    allSystems: [],
    // Tabelle
    expandedId: null,
    sortKey: "datum",
    sortDir: "desc",
    filter: "",
    onlyOutliers: false,
    page: 1,
    perPage: 15,
    // Modals
    showReading: false,
    showScanner: false,
    scanFileMode: false,
    ocrHint: null,
    ocrAvailable: null,
    scanBusy: false,
    scanStatus: "",
    showImport: false,
    reading: null,
    importFile: null,
    importResult: null,
    busy: false,
  }),
  computed: {
    fromParam() {
      if (this.range === "all") return null;
      const d = new Date();
      if (this.range === "week") d.setDate(d.getDate() - 7);
      if (this.range === "month") d.setMonth(d.getMonth() - 1);
      if (this.range === "year") d.setFullYear(d.getFullYear() - 1);
      return d.toISOString().slice(0, 10);
    },
    haEntity() { return (this.system.zusatzfelder || {}).ha_entity || null; },
    modeLabel() {
      return { value: "Zählerstand", consumption: "Verbrauch", per_day: "Verbrauch/Tag" }[this.mode];
    },
    // C: Jahres-Hochrechnung (klar als Prognose markiert, keine echten Werte)
    forecast() {
      const s = this.stats;
      if (!s || s.avg_per_day == null) return null;
      const cons = s.avg_per_day * 365;
      return { cons, cost: s.cost_per_unit != null ? cons * s.cost_per_unit : null };
    },
    // D: Gas zusätzlich in kWh (nur Zusatz zu m³, nie Ersatz)
    gasKwh() {
      if (this.system.typ !== "Gas") return null;
      const z = this.system.zusatzfelder || {};
      const bw = parseFloat(z.brennwert);
      if (!bw) return null;
      const zz = parseFloat(z.zustandszahl) || 0.95;
      const s = this.stats;
      if (!s) return null;
      return { total: s.total_consumption * bw * zz, faktor: bw * zz };
    },
    overlayOptions() {
      return this.allSystems.filter((s) => s.id !== this.system.id && s.aktiv);
    },
    outlierColor() { return chartColor("outlier", "#9A6A00"); },

    canWrite() { return canWriteNow(); },
    availableSources() {
      return [...new Set(this.readings.map((r) => r.source || "manual"))].sort();
    },

    /* Grundlage aller Auswahllogik ist die GEFILTERTE Menge, nicht die
       Rohdaten: "alle auswählen" bei gesetztem Filter darf nur das treffen,
       was der Nutzer auch sieht. */
    selectableIds() { return this.filtered.map((r) => r.id); },
    pageIds() { return this.paged.map((r) => r.id); },
    selectedCount() { return this.selected.size; },
    pageAllSelected() {
      const ids = this.pageIds;
      return ids.length > 0 && ids.every((id) => this.selected.has(id));
    },
    pageSomeSelected() {
      return !this.pageAllSelected && this.pageIds.some((id) => this.selected.has(id));
    },
    allFilteredSelected() {
      const ids = this.selectableIds;
      return ids.length > 0 && ids.every((id) => this.selected.has(id));
    },
    /* Hinweis anbieten, sobald die Seite vollständig markiert ist, es aber
       außerhalb der Seite noch weitere Treffer gibt. Ohne diesen Schritt
       glaubt man leicht, mit dem Kopf-Häkchen alles erfasst zu haben. */
    canSelectAllFiltered() {
      return this.pageAllSelected && !this.allFilteredSelected
             && this.selectableIds.length > this.pageIds.length;
    },
    selectedSwaps() {
      return this.filtered.filter((r) => this.selected.has(r.id) && r.meter_replaced).length;
    },
    canExport() { return canExportNow(); },
    chart() {
      if (!this.chartData) return { labels: [], datasets: [] };
      const pick = (cd) =>
        this.mode === "value" ? cd.values : this.mode === "per_day" ? cd.consumption_per_day : cd.consumption;
      const labelSet = new Set(this.chartData.labels);
      const overlays = this.overlayIds.map((id) => this.overlayData[id]).filter(Boolean);
      overlays.forEach((cd) => cd.labels.forEach((l) => labelSet.add(l)));
      const labels = [...labelSet].sort();
      const toMap = (cd) => { const m = {}; const p = pick(cd); cd.labels.forEach((l, i) => (m[l] = p[i])); return m; };

      const pm = toMap(this.chartData);
      const idxOf = (l) => this.chartData.labels.indexOf(l);
      const primData = labels.map((l) => (l in pm ? pm[l] : null));
      const ptColor = labels.map((l) => { const i = idxOf(l); return i >= 0 && this.chartData.outliers[i] ? chartColor("outlier", "#9A6A00") : this.chartData.color; });
      const ptRad = labels.map((l) => { const i = idxOf(l); return i >= 0 && this.chartData.outliers[i] ? 5 : this.chartType === "bar" ? 0 : 2; });

      // E: im Zählerstand-Modus die Linie an Zählertausch-Punkten trennen (Segmente je Zähler)
      const swapLabels = new Set(
        this.chartData.labels.filter((l, i) => this.chartData.meter_replaced && this.chartData.meter_replaced[i])
      );
      const isValue = this.mode === "value";
      const prim = {
        label: this.system.name, data: primData,
        borderColor: this.chartData.color,
        backgroundColor: this.chartType === "bar" ? this.chartData.color + "cc" : this.chartData.color + "22",
        pointBackgroundColor: ptColor, pointRadius: ptRad, borderWidth: 2, tension: 0.25,
        fill: this.chartType === "line" && !isValue, spanGaps: true,
      };
      if (isValue && this.chartType === "line") {
        prim.segment = {
          borderColor: (ctx) => (swapLabels.has(labels[ctx.p1DataIndex]) ? "transparent" : undefined),
        };
      }
      const datasets = [prim];
      const overlayUnits = new Set();
      overlays.forEach((cd) => {
        const m = toMap(cd);
        overlayUnits.add(cd.unit);
        datasets.push({
          label: `${cd.name} (${cd.unit})`, data: labels.map((l) => (l in m ? m[l] : null)),
          borderColor: cd.color, backgroundColor: cd.color + "18",
          pointRadius: this.chartType === "bar" ? 0 : 2, borderWidth: 1.5,
          borderDash: [5, 4], tension: 0.25, fill: false, spanGaps: true,
          yAxisID: "y2",   // eigene rechte Achse (unterschiedliche Größenordnung/Einheit)
        });
      });
      return {
        labels, datasets,
        hasY2: overlays.length > 0,
        y2Label: [...overlayUnits].join(" / "),
      };
    },
    filtered() {
      let rows = this.readings.slice();
      if (this.onlyOutliers) rows = rows.filter((r) => r.is_outlier);
      if (this.sourceFilter !== "all") {
        rows = rows.filter((r) => (r.source || "manual") === this.sourceFilter);
      }
      if (this.filter.trim()) {
        const q = this.filter.toLowerCase();
        rows = rows.filter((r) => (r.note || "").toLowerCase().includes(q) || fmtDate(r.datum).includes(q));
      }
      const dir = this.sortDir === "asc" ? 1 : -1;
      rows.sort((a, b) => {
        let av = a[this.sortKey], bv = b[this.sortKey];
        if (this.sortKey === "datum") {
          // ISO-Strings sortieren lexikographisch korrekt – kein Date-Parsing
          // (neuere WebViews parsen uneinheitlich -> nicht-deterministische Reihenfolge)
          av = String(av); bv = String(bv);
        }
        av = av ?? -Infinity; bv = bv ?? -Infinity;
        return av < bv ? -dir : av > bv ? dir : 0;
      });
      return rows;
    },
    pageCount() { return Math.max(1, Math.ceil(this.filtered.length / this.perPage)); },
    paged() { const s = (this.page - 1) * this.perPage; return this.filtered.slice(s, s + this.perPage); },
    latestValue() {
      if (!this.readings.length) return null;
      return this.readings.reduce((a, b) => (new Date(a.datum) > new Date(b.datum) ? a : b)).value;
    },
    extraFields() { return EXTRA_FIELDS[this.system.typ] || []; },
  },
  watch: {
    range() { this.loadDynamic(); },
    /* Ändert sich die gefilterte Menge, wären zuvor markierte Zeilen unsichtbar
       ausgewählt – und ein Klick auf Löschen träfe Datensätze, die gerade
       niemand sieht. Deshalb Auswahl verwerfen. */
    filter() { if (this.selected.size) this.clearSelection(); },
    onlyOutliers() { if (this.selected.size) this.clearSelection(); },
    sourceFilter() { if (this.selected.size) this.clearSelection(); },
    tab(v) {
      // Auswahlmodus gehört zur Werte-Tabelle; beim Verlassen aufräumen.
      if (v !== "list" && this.selectMode) { this.selectMode = false; this.clearSelection(); }
      if (v === "meters" && !this.metersLoaded) this.loadMeters();
      if (v === "tariffs" && !this.tariffsLoaded) this.loadTariffs();
      // Nach oben melden: $refs sind nicht reaktiv, die kontextbezogene
      // FAB-Beschriftung im Eltern-Scope hört sonst keinen Tab-Wechsel.
      this.$emit("tab", v);
    },
    overlayIds() { this.loadOverlays(); },
  },
  async mounted() {
    // Startwert des aktiven Tabs an den Eltern-Scope melden – sonst behält
    // dieser den Tab eines zuvor geöffneten Systems (FAB-Kontext liefe falsch).
    this.$emit("tab", this.tab);
    await this.loadAll();
    try { this.allSystems = await api("/api/systems"); } catch (_) {}
  },
  methods: {
    fmt, fmtDate, typeIcon, sourceLabel,
    async loadAll() {
      this.loading = true;
      await this.loadDynamic();
      this.loading = false;
      // Einmal je Ansicht: fehlt Tesseract im Abbild, wird die Kamera gar nicht
      // erst angeboten statt erst nach dem Hochladen einen Fehler zu zeigen.
      if (this.ocrAvailable === null) {
        try { this.ocrAvailable = (await api("/api/ocr/status")).available; }
        catch (_) { this.ocrAvailable = false; }
      }
    },

    /* ---------- Zähler-Metadaten ---------- */
    async loadMeters() {
      try {
        const [ms, ba] = await Promise.all([
          api(`/api/systems/${this.system.id}/meters`),
          this.bauarten.length ? Promise.resolve(this.bauarten) : api("/api/meters/bauarten"),
        ]);
        this.meters = ms;
        this.bauarten = ba;
        this.metersLoaded = true;
        // Nach dem Laden gilt die Liste als maßgeblich – so bleibt die Zahl
        // auch nach Anlegen oder Löschen korrekt, ohne erneuten Dashboard-Aufruf.
        this.meterCount = ms.length;
      } catch (e) { this.notify("Zähler nicht ladbar: " + e.message, "err"); }
    },
    openMeter(m) {
      this.meterForm = m
        ? { ...m }
        : { id: null, hersteller: "", modell: "", zaehlernummer: "", bauart: "",
            baujahr: null, eichung_bis: null, messstellenbetreiber: "",
            stellen_vor: null, stellen_nach: null,
            eingebaut_am: null, ausgebaut_am: null, notiz: "" };
      this.showMeter = true;
    },
    async saveMeter() {
      const f = this.meterForm;
      // Leerstrings zu null: das Backend trimmt zwar auch, aber so bleibt die
      // Vorschau der Empfehlung schon vor dem Speichern konsistent.
      const clean = (v) => (v === "" || v === undefined ? null : v);
      const body = JSON.stringify({
        hersteller: clean(f.hersteller), modell: clean(f.modell),
        zaehlernummer: clean(f.zaehlernummer), bauart: clean(f.bauart),
        baujahr: f.baujahr ? Number(f.baujahr) : null,
        eichung_bis: clean(f.eichung_bis),
        messstellenbetreiber: clean(f.messstellenbetreiber),
        stellen_vor: f.stellen_vor ? Number(f.stellen_vor) : null,
        stellen_nach: f.stellen_nach !== null && f.stellen_nach !== "" ? Number(f.stellen_nach) : null,
        eingebaut_am: clean(f.eingebaut_am), ausgebaut_am: clean(f.ausgebaut_am),
        notiz: clean(f.notiz),
      });
      this.busy = true;
      try {
        if (f.id) await api(`/api/meters/${f.id}`, { method: "PATCH", body });
        else await api(`/api/systems/${this.system.id}/meters`, { method: "POST", body });
        this.showMeter = false;
        this.notify(f.id ? "Zähler aktualisiert" : "Zähler angelegt", "ok");
        await this.loadMeters();
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.busy = false; }
    },
    async deleteMeter(m) {
      try {
        await api(`/api/meters/${m.id}`, { method: "DELETE" });
        this.notify("Zähler gelöscht", "ok");
        await this.loadMeters();
      } catch (e) { this.notify(e.message, "err"); }
    },

    /* ---------- Tarife ---------- */
    async loadTariffs() {
      try {
        this.tariffs = await api(`/api/systems/${this.system.id}/tariffs`);
        this.tariffsLoaded = true;
        this.tariffCount = this.tariffs.length;
      } catch (e) { this.notify("Tarife nicht ladbar: " + e.message, "err"); }
    },
    openTariff(t) {
      this.tariffForm = t
        ? { ...t }
        : { id: null, name: "", anbieter: "", gueltig_ab: today(), gueltig_bis: null,
            arbeitspreis: null, grundpreis: 0, notiz: "" };
      this.showTariff = true;
    },
    async saveTariff() {
      const f = this.tariffForm;
      if (f.arbeitspreis === null || f.arbeitspreis === "") {
        this.notify("Arbeitspreis fehlt", "err"); return;
      }
      const clean = (v) => (v === "" || v === undefined ? null : v);
      const body = JSON.stringify({
        name: clean(f.name), anbieter: clean(f.anbieter),
        gueltig_ab: f.gueltig_ab, gueltig_bis: clean(f.gueltig_bis),
        arbeitspreis: Number(f.arbeitspreis),
        grundpreis: Number(f.grundpreis || 0),
        notiz: clean(f.notiz),
      });
      this.busy = true;
      try {
        if (f.id) await api(`/api/tariffs/${f.id}`, { method: "PATCH", body });
        else await api(`/api/systems/${this.system.id}/tariffs`, { method: "POST", body });
        this.showTariff = false;
        this.notify(f.id ? "Tarif aktualisiert" : "Tarif angelegt", "ok");
        await this.loadTariffs();
        await this.loadDynamic();      // Kosten neu rechnen lassen
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.busy = false; }
    },
    async deleteTariff(t) {
      try {
        await api(`/api/tariffs/${t.id}`, { method: "DELETE" });
        this.notify("Tarif gelöscht", "ok");
        await this.loadTariffs();
        await this.loadDynamic();
      } catch (e) { this.notify(e.message, "err"); }
    },
    tariffRange(t) {
      const ab = fmtDate(t.gueltig_ab);
      return t.gueltig_bis ? `${ab} – ${fmtDate(t.gueltig_bis)}` : `ab ${ab}`;
    },

    /* ---------- Hardware-Empfehlung ---------- */
    suggestFor(meter) { return hwSuggest(meter, this.system); },
    eichungLabel(m) {
      if (m.eichung_bis === null || m.eichung_faellig_in_tagen === null) return null;
      const d = m.eichung_faellig_in_tagen;
      if (d < 0) return { level: "over", text: `Eichung abgelaufen seit ${Math.abs(d)} T` };
      if (d <= 180) return { level: "soon", text: `Eichung endet in ${d} T` };
      return { level: "ok", text: `Eichung bis ${fmtDate(m.eichung_bis)}` };
    },
    async loadDynamic() {
      const q = this.fromParam ? `?from=${this.fromParam}` : "";
      // Ein kombinierter Request statt drei (eine Berechnung im Backend)
      const d = await api(`/api/systems/${this.system.id}/dashboard${q}`);
      this.readings = d.readings; this.stats = d.stats; this.chartData = d.chart;
      // Anzahlen kommen direkt mit – die Reiter zeigen sie ab dem ersten
      // Rendern, ohne dass die vollständigen Listen geladen werden müssen.
      if (d.counts) {
        this.meterCount = d.counts.meters;
        this.tariffCount = d.counts.tariffs;
      }
      this.page = 1;
      this.expandedId = null;
      await this.loadOverlays();
    },
    async loadOverlays() {
      const q = this.fromParam ? `?from=${this.fromParam}` : "";
      for (const id of this.overlayIds) {
        if (!this.overlayData[id]) {
          try {
            const cd = await api(`/api/systems/${id}/chart-data${q}`);
            this.overlayData = { ...this.overlayData, [id]: cd };  // neue Referenz -> sicher reaktiv
          } catch (_) {}
        }
      }
    },
    toggleOverlay(id) {
      const i = this.overlayIds.indexOf(id);
      if (i >= 0) this.overlayIds.splice(i, 1);
      else this.overlayIds.push(id);
    },
    /* ---------- Sammelauswahl ---------- */
    toggleSelectMode() {
      this.selectMode = !this.selectMode;
      if (!this.selectMode) this.clearSelection();
      // Aufgeklappte Zeile schließen: im Auswahlmodus wäre der Klick auf die
      // Zeile doppelt belegt.
      this.expandedId = null;
    },
    clearSelection() { this.selected = new Set(); },
    toggleSelect(id) {
      // Neues Set statt Mutation: Vue 3 verfolgt Set-Änderungen zwar, aber
      // eine neue Referenz macht abgeleitete Werte zuverlässig neu berechnet.
      const next = new Set(this.selected);
      next.has(id) ? next.delete(id) : next.add(id);
      this.selected = next;
    },
    togglePage() {
      const next = new Set(this.selected);
      if (this.pageAllSelected) this.pageIds.forEach((id) => next.delete(id));
      else this.pageIds.forEach((id) => next.add(id));
      this.selected = next;
    },
    selectAllFiltered() { this.selected = new Set(this.selectableIds); },

    async deleteSelected() {
      if (!this.selected.size) return;
      this.bulkBusy = true;
      try {
        const res = await api(`/api/systems/${this.system.id}/readings/bulk-delete`, {
          method: "POST", body: JSON.stringify({ ids: [...this.selected] }),
        });
        const swaps = res.meter_replacements_removed
          ? ` – darunter ${res.meter_replacements_removed} Zählertausch`
          : "";
        this.notify(`${res.deleted} Ablesung${res.deleted === 1 ? "" : "en"} gelöscht${swaps}`, "ok");
        this.clearSelection();
        this.selectMode = false;
        await this.loadDynamic();
        this.$emit("changed");
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.bulkBusy = false; }
    },

    toggleRow(id) {
      if (this.selectMode) { this.toggleSelect(id); return; } this.expandedId = this.expandedId === id ? null : id; },
    setSort(k) { if (this.sortKey === k) this.sortDir = this.sortDir === "asc" ? "desc" : "asc"; else { this.sortKey = k; this.sortDir = "desc"; } },
    arrow(k) { return this.sortKey === k ? (this.sortDir === "asc" ? "↑" : "↓") : ""; },

    /* Ablesung */
    focusValue() {
      // Nur auf Zeigergeraeten automatisch fokussieren: auf Touch wuerde die
      // Tastatur sofort hochfahren und den Dialog zusammenschieben, bevor der
      // Nutzer ueberhaupt sieht, welches System er erfasst.
      if (window.matchMedia("(pointer: fine)").matches) {
        this.$nextTick(() => this.$refs.valueInput && this.$refs.valueInput.focus());
      }
    },
    openReading() {
      this.reading = { id: null, datum: today(), value: null, cost: null,
                       meter_replaced: false, meter_start: "", note: "", source: "manual" };
      this.ocrHint = null;
      this.showReading = true;
      this.focusValue();
    },
    openEditReading(r) {
      this.reading = {
        id: r.id,
        datum: String(r.datum).slice(0, 10),
        value: r.value,
        cost: r.cost,
        meter_replaced: !!r.meter_replaced,
        meter_start: r.meter_start === null || r.meter_start === undefined ? "" : r.meter_start,
        note: r.note || "",
      };
      this.showReading = true;
    },
    async fetchHaValue() {
      try {
        const r = await api(`/api/ha/state/${encodeURIComponent(this.haEntity)}`);
        const raw = parseFloat(String(r.state).replace(",", "."));
        if (!isFinite(raw)) throw new Error(`Entity liefert '${r.state}' – kein numerischer Zählerstand`);
        // Quelleinheit: konfigurierte Einheit schlägt HA-Meldung; Ziel: Systemeinheit
        const srcUnit = (this.system.zusatzfelder || {}).ha_unit || r.unit || this.system.einheit;
        const res = convertUnit(raw, srcUnit, this.system.einheit);
        if (res === null) throw new Error(`Einheit '${srcUnit}' ist nicht nach '${this.system.einheit}' umrechenbar`);
        const v = Math.round(res.value * 1000) / 1000;
        this.reading.value = v;
        this.reading.source = "ha_api";
        this.notify(res.converted
          ? `Übernommen: ${fmt(raw)} ${srcUnit} → ${fmt(v)} ${this.system.einheit} (${r.name || this.haEntity})`
          : `Übernommen: ${fmt(v)} ${this.system.einheit} (${r.name || this.haEntity})`, "ok");
      } catch (e) { this.notify(e.message, "err"); }
    },

    /* ---------- Foto-Erfassung (Stream ODER natives Foto), Erkennung serverseitig ---------- */
    async openScanner() {
      // Fehlt die Erkennung im Abbild, wird der Grund genannt statt die
      // Schaltfläche auszublenden. Ein verschwundener Knopf sieht wie ein
      // Fehler aus und lässt sich nicht nachvollziehen.
      if (this.ocrAvailable === false) {
        this.notify("Texterkennung nicht verfügbar – Add-on neu bauen lassen "
                  + "(Tesseract fehlt im Abbild).", "err");
        return;
      }
      // HA-App-WebViews (v.a. iOS) stellen keinen Kamera-Stream bereit -> natives Foto als Fallback
      const hasStream = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
      this.scanFileMode = !hasStream;
      this.showScanner = true;
      if (!hasStream) {
        this.scanStatus = "Diese Umgebung erlaubt keinen Live-Stream – nutze die native Kamera per Foto.";
        return;
      }
      this.scanStatus = "Kamera wird gestartet …";
      this.$nextTick(async () => {
        try {
          this._stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment", width: { ideal: 1920 } }, audio: false,
          });
          this.$refs.scanVideo.srcObject = this._stream;
          await this.$refs.scanVideo.play();
          this.scanStatus = "Zählerstand mittig ins Feld halten, dann auslösen.";
        } catch (e) {
          // Stream verweigert (Berechtigung etc.) -> ebenfalls auf natives Foto wechseln
          this.scanFileMode = true;
          this.scanStatus = "Kein Stream (" + e.message + ") – nutze die native Kamera per Foto.";
        }
      });
    },
    closeStreamOnly() {
      if (this._stream) { this._stream.getTracks().forEach((t) => t.stop()); this._stream = null; }
    },
    closeScanner() {
      this.closeStreamOnly();
      this.showScanner = false; this.scanBusy = false;
    },
    triggerScanFile() { this.$refs.scanFile && this.$refs.scanFile.click(); },
    triggerGalleryFile() { this.$refs.galleryFile && this.$refs.galleryFile.click(); },
    async exifDate(file) {
      // Minimal-EXIF: DateTimeOriginal (0x9003) aus JPEG-APP1 lesen. Fallback: Datei-Änderungsdatum.
      try {
        const buf = new DataView(await file.slice(0, 256 * 1024).arrayBuffer());
        if (buf.getUint16(0) !== 0xFFD8) throw 0;                    // kein JPEG
        let off = 2;
        while (off < buf.byteLength - 4) {
          if (buf.getUint8(off) !== 0xFF) break;
          const marker = buf.getUint8(off + 1);
          const size = buf.getUint16(off + 2);
          if (marker === 0xE1 && buf.getUint32(off + 4) === 0x45786966) {  // "Exif"
            const t = off + 10;                                       // TIFF-Header
            const le = buf.getUint16(t) === 0x4949;                   // Byte-Order
            const g16 = (o) => buf.getUint16(o, le), g32 = (o) => buf.getUint32(o, le);
            const scanIfd = (ifd, wantTag) => {
              const n = g16(ifd);
              for (let i = 0; i < n; i++) {
                const e = ifd + 2 + i * 12;
                if (g16(e) === wantTag) return e;
              }
              return null;
            };
            const ifd0 = t + g32(t + 4);
            const exifPtr = scanIfd(ifd0, 0x8769);
            if (exifPtr) {
              const exifIfd = t + g32(exifPtr + 8);
              const dto = scanIfd(exifIfd, 0x9003);
              if (dto) {
                const strOff = t + g32(dto + 8);
                let str = "";
                for (let i = 0; i < 19; i++) str += String.fromCharCode(buf.getUint8(strOff + i));
                const m = str.match(/^(\d{4}):(\d{2}):(\d{2})/);
                if (m) return `${m[1]}-${m[2]}-${m[3]}`;
              }
            }
            break;
          }
          off += 2 + size;
        }
      } catch (_) {}
      if (file.lastModified) return new Date(file.lastModified).toISOString().slice(0, 10);
      return null;
    },
    async onScanFile(ev) {
      const file = ev.target.files && ev.target.files[0];
      ev.target.value = "";
      if (!file) return;
      if (!this.reading.id) {
        const d = await this.exifDate(file);
        if (d) { this.reading.datum = d; this.notify("Ablesedatum aus Foto: " + fmtDate(d), "ok"); }
      }
      const img = new Image();
      img.onload = () => {
        // mittleren Streifen ausschneiden (dort liegt das Zählwerk)
        const cw = img.naturalWidth, ch = img.naturalHeight;
        const cropH = Math.round(ch * 0.34);
        const canvas = document.createElement("canvas");
        canvas.width = cw; canvas.height = cropH;
        canvas.getContext("2d").drawImage(img, 0, (ch - cropH) / 2, cw, cropH, 0, 0, cw, cropH);
        URL.revokeObjectURL(img.src);
        this.runOcr(canvas);
      };
      img.src = URL.createObjectURL(file);
    },
    async captureScan() {
      if (this.scanFileMode) { this.triggerScanFile(); return; }
      const video = this.$refs.scanVideo;
      if (!video || !video.videoWidth) return;
      const cw = video.videoWidth, ch = video.videoHeight;
      const cropH = Math.round(ch * 0.28);
      const canvas = document.createElement("canvas");
      canvas.width = cw; canvas.height = cropH;
      canvas.getContext("2d").drawImage(video, 0, (ch - cropH) / 2, cw, cropH, 0, 0, cw, cropH);
      this.runOcr(canvas);
    },
    /* Erkennung läuft serverseitig. Der bisherige Weg über tesseract.js kam
       von einem Auslieferungsnetz, scheiterte im Offline-Modus und konnte das
       Bild nicht vorverarbeiten. Hier wird nur noch das Foto hochgeladen. */
    async runOcr(canvas) {
      this.scanBusy = true;
      this.scanStatus = "Bild wird ausgewertet …";
      try {
        const blob = await new Promise((res) =>
          canvas.toBlob(res, "image/jpeg", 0.92));
        if (!blob) throw new Error("Bild nicht lesbar");

        const form = new FormData();
        form.append("file", blob, "zaehler.jpg");
        // Systemkennung mitgeben: mit dem letzten Stand entscheidet der Server
        // zwischen Zählwerk, Seriennummer und Eichjahr.
        if (this.system && this.system.id) form.append("system_id", this.system.id);

        // Kein Content-Type setzen – der Browser ergänzt die Trennmarke selbst.
        const res = await fetch("api/ocr/scan", {
          method: "POST", body: form, credentials: "same-origin",
        });
        if (!res.ok) {
          let d; try { d = await res.json(); } catch (_) {}
          throw new Error((d && d.detail) || res.statusText);
        }
        const r = await res.json();

        if (r.value === null || r.value === undefined) {
          this.scanStatus = "Nichts erkannt – Zählwerk formatfüllend in den Rahmen, "
                          + "mehr Licht, nochmal versuchen.";
          return;
        }

        this.reading.value = String(r.value);
        this.ocrHint = {
          value: r.value,
          confidence: r.confidence,
          plausible: r.matched_previous !== false,
          previous: r.previous,
          candidates: (r.candidates || []).map((c) => c.value).slice(0, 5),
        };
        this.closeScanner();
        this.notify(this.ocrHint.plausible
          ? `Erkannt: ${fmt(r.value, 3)} – bitte prüfen`
          : `Erkannt: ${fmt(r.value, 3)} – unplausibel, bitte prüfen`,
          this.ocrHint.plausible ? "ok" : "err");
      } catch (e) {
        this.scanStatus = "Fehler: " + e.message;
      } finally {
        this.scanBusy = false;
      }
    },

    async saveReading() {
      if (this.reading.value === null || this.reading.value === "") { this.notify("Zählerwert fehlt", "err"); return; }
      this.busy = true;
      try {
        const body = JSON.stringify({
          datum: this.reading.datum,
          value: Number(this.reading.value),
          cost: this.reading.cost === "" || this.reading.cost === null ? null : Number(this.reading.cost),
          meter_replaced: this.reading.meter_replaced,
          // Startstand nur bei Tausch mitschicken; leer = neuer Zähler ab 0.
          meter_start: this.reading.meter_replaced && this.reading.meter_start !== "" && this.reading.meter_start !== null
            ? Number(this.reading.meter_start) : null,
          note: this.reading.note || null,
          // Herkunft: 'ha_api', wenn der Wert aus einer Home-Assistant-Entity
          // übernommen wurde, sonst Tastatureingabe. Wird der Wert danach von
          // Hand geändert, fällt die Kennzeichnung zurück auf 'manual'.
          source: this.reading.source || "manual",
        });
        if (this.reading.id) {
          await api(`/api/readings/${this.reading.id}`, { method: "PUT", body });
        } else {
          await api(`/api/systems/${this.system.id}/readings`, { method: "POST", body });
        }
        this.showReading = false;
        this.notify(this.reading.id ? "Ablesung aktualisiert" : "Ablesung gespeichert", "ok");
        await this.loadDynamic();
        this.$emit("changed");   // Parent aktualisiert Kachelwerte und Fälligkeits-Badges
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.busy = false; }
    },
    async deleteReading(r) {
      if (!confirm(`Ablesung vom ${fmtDate(r.datum)} löschen?`)) return;
      try { await api(`/api/readings/${r.id}`, { method: "DELETE" }); this.notify("Ablesung gelöscht", "ok"); await this.loadDynamic(); }
      catch (e) { this.notify(e.message, "err"); }
    },

    /* Import */
    openImport() { this.importFile = null; this.importResult = null; this.showImport = true; },
    downloadTemplate() {
      fetchBlobDownload("api/import/template", "import_template.csv")
        .catch((e) => this.notify("Download fehlgeschlagen: " + e.message, "err"));
    },
    openReport() {
      const q = this.fromParam ? `?from=${this.fromParam}` : "";
      const name = this.system.name.replace(/\s+/g, "_");
      fetchBlobDownload(`api/systems/${this.system.id}/report.pdf${q}`, `zaehlwerk-bericht_${name}.pdf`)
        .catch((e) => this.notify("PDF fehlgeschlagen: " + e.message, "err"));
    },
    openExport() {
      const name = this.system.name.replace(/\s+/g, "_");
      fetchBlobDownload(`api/systems/${this.system.id}/export.csv`, `zaehlwerk_${name}.csv`)
        .catch((e) => this.notify("Export fehlgeschlagen: " + e.message, "err"));
    },
    onFile(e) { this.importFile = e.target.files[0] || null; },
    async runImport() {
      if (!this.importFile) { this.notify("Keine Datei gewählt", "err"); return; }
      this.busy = true;
      try {
        const fd = new FormData(); fd.append("file", this.importFile);
        const res = await fetch(`api/systems/${this.system.id}/import`, { method: "POST", body: fd });
        if (!res.ok) throw new Error((await res.json()).detail || "Import fehlgeschlagen");
        this.importResult = await res.json();
        this.notify(`${this.importResult.imported} Werte importiert`, "ok");
        await this.loadDynamic();
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.busy = false; }
    },
  },
  template: `
  <div>
    <div class="detail-head">
      <div class="dh-main">
        <div class="dh-type">{{ typeIcon(system.typ) }} {{ system.typ }} · {{ system.einheit }}</div>
        <h2>{{ system.name }}</h2>
      </div>
      <div class="counter" v-if="latestValue !== null">
        <div>
          <span class="clabel">Letzter Stand</span>
          <span class="cval">{{ fmt(latestValue, 1) }}</span>
          <span class="cunit">{{ system.einheit }}</span>
        </div>
      </div>
      <div class="dh-actions">
        <button v-if="canWrite" class="btn btn-sm" @click="$emit('edit', system)"
                title="System bearbeiten, archivieren oder löschen">✎ Bearbeiten</button>
        <button v-if="canWrite" class="btn btn-sm" @click="openImport">⇪ Import</button>
        <button v-if="canExport" class="btn btn-sm" @click="openExport">⇩ CSV</button>
        <button v-if="canExport" class="btn btn-tonal btn-sm" @click="openReport">⇩ PDF</button>
      </div>
    </div>

    <div class="tabs">
      <button class="tab" :class="{active: tab==='chart'}" @click="tab='chart'">Auswertung</button>
      <button class="tab" :class="{active: tab==='list'}" @click="tab='list'">Werte ({{ readings.length }})</button>
      <button class="tab" :class="{active: tab==='meters'}" @click="tab='meters'">Zähler<span v-if="meterCount"> ({{ meterCount }})</span></button>
      <button class="tab" :class="{active: tab==='tariffs'}" @click="tab='tariffs'">Tarife<span v-if="tariffCount"> ({{ tariffCount }})</span></button>
    </div>

    <transition name="m3sw" mode="out-in">
    <div v-if="loading" class="center-load" key="load"><span class="spin"></span></div>

    <!-- AUSWERTUNG -->
    <div v-else-if="tab==='chart'" key="chart">
      <div class="stats" v-if="stats">
        <div class="stat"><div class="s-label">Gesamtverbrauch</div><div class="s-val num">{{ fmt(stats.total_consumption) }}<span class="u">{{ system.einheit }}</span></div></div>
        <div class="stat"><div class="s-label">Ø / Tag</div><div class="s-val num">{{ fmt(stats.avg_per_day, 3) }}<span class="u">{{ system.einheit }}</span></div></div>
        <div class="stat"><div class="s-label">Gesamtkosten <span v-if="stats.cost_estimated" class="s-tag">≈ inkl. Schätzung</span></div><div class="s-val num">{{ stats.cost_estimated ? '≈ ' : '' }}{{ fmt(stats.total_cost) }}<span class="u">€</span></div></div>
        <div class="stat"><div class="s-label">Kosten / Einheit <span v-if="stats.cost_estimated" class="s-tag">≈</span></div><div class="s-val num">{{ fmt(stats.cost_per_unit, 4) }}<span class="u">€</span></div></div>
        <div class="stat"><div class="s-label">Max / Tag</div><div class="s-val num">{{ fmt(stats.max_per_day, 3) }}</div><div class="s-sub">{{ fmtDate(stats.max_per_day_datum) }}</div></div>
        <div class="stat"><div class="s-label">Min / Tag</div><div class="s-val num">{{ fmt(stats.min_per_day, 3) }}</div><div class="s-sub">{{ fmtDate(stats.min_per_day_datum) }}</div></div>
        <div class="stat" v-if="gasKwh"><div class="s-label">Gesamt in kWh <span class="s-tag">Zusatz</span></div><div class="s-val num">{{ fmt(gasKwh.total) }}<span class="u">kWh</span></div><div class="s-sub">Brennwert × Zustandszahl = {{ fmt(gasKwh.faktor, 3) }}</div></div>
        <div class="stat tariff" v-if="stats.total_cost_tariff !== null && stats.total_cost_tariff !== undefined">
          <div class="s-label">Kosten nach Tarif
            <span class="s-tag" v-if="stats.coverage_ratio < 1">{{ Math.round(stats.coverage_ratio*100) }} % abgedeckt</span>
          </div>
          <div class="s-val num">{{ fmt(stats.total_cost_tariff) }}<span class="u">€</span></div>
          <div class="s-sub">{{ fmt(stats.total_energy_cost) }} € Arbeit + {{ fmt(stats.total_base_cost) }} € Grund</div>
        </div>
        <div class="stat tariff" v-if="stats.avg_price_effective">
          <div class="s-label">Effektivpreis <span class="s-tag">inkl. Grundgebühr</span></div>
          <div class="s-val num">{{ fmt(stats.avg_price_effective, 4) }}<span class="u">€/{{ system.einheit }}</span></div>
          <div class="s-sub">{{ stats.covered_intervals }} Intervalle mit Tarif</div>
        </div>
        <div class="stat forecast" v-if="forecast"><div class="s-label">⌁ Hochrechnung Jahr <span class="s-tag warn">Prognose</span></div><div class="s-val num">{{ fmt(forecast.cons) }}<span class="u">{{ system.einheit }}</span></div><div class="s-sub" v-if="forecast.cost !== null">≈ {{ fmt(forecast.cost) }} € Kosten</div></div>
      </div>

      <div class="card">
        <div class="chart-controls">
          <div class="seg">
            <button v-for="m in [['consumption','Verbrauch'],['per_day','pro Tag'],['value','Zählerstand']]" :key="m[0]" :class="{active: mode===m[0]}" @click="mode=m[0]">{{ m[1] }}</button>
          </div>
          <div class="seg">
            <button :class="{active: chartType==='line'}" @click="chartType='line'">Linie</button>
            <button :class="{active: chartType==='bar'}" @click="chartType='bar'">Balken</button>
          </div>
          <div class="seg">
            <button v-for="r in [['week','Woche'],['month','Monat'],['year','Jahr'],['all','Alles']]" :key="r[0]" :class="{active: range===r[0]}" @click="range=r[0]">{{ r[1] }}</button>
          </div>
          <div class="overlay-seg" v-if="overlayOptions.length">
            <button v-for="s in overlayOptions" :key="s.id"
                    :class="{active: overlayIds.includes(s.id)}"
                    @click="toggleOverlay(s.id)" :title="'System überlagern: ' + s.name">
              + {{ s.name }}
            </button>
          </div>
        </div>
        <energy-chart :labels="chart.labels" :datasets="chart.datasets" :chart-type="chartType" :has-y2="chart.hasY2" :y2-label="chart.y2Label" />
        <div class="legend-hint">
          <span><span class="dot" :style="{background: chartData ? chartData.color : '#0e7c86'}"></span>{{ modeLabel }}</span>
          <span><span class="dot" :style="{background: outlierColor}"></span>Ausreißer (Ø + 2σ)</span>
        </div>
      </div>
    </div>

    <!-- WERTE-TABELLE -->
    <div v-else-if="tab==='list'" key="list">
      <div class="table-tools">
        <input class="input" v-model="filter" placeholder="Filtern (Notiz / Datum)…" />
        <label class="check"><input type="checkbox" v-model="onlyOutliers" /> nur Ausreißer</label>
        <!-- Herkunftsfilter erscheint erst, wenn es überhaupt mehr als eine
             Quelle gibt – bei rein manueller Erfassung wäre er nur Ballast. -->
        <div class="seg src-seg" v-if="availableSources.length > 1">
          <button :class="{active: sourceFilter === 'all'}" @click="sourceFilter = 'all'">Alle</button>
          <button v-for="s in availableSources" :key="s"
                  :class="{active: sourceFilter === s}" @click="sourceFilter = s">
            {{ sourceLabel(s) }}
          </button>
        </div>
        <div class="spacer" style="flex:1"></div>
        <button v-if="canWrite && readings.length" class="btn btn-sm"
                :class="{'btn-tonal': selectMode}" @click="toggleSelectMode">
          {{ selectMode ? '✕ Auswahl beenden' : '☑ Auswählen' }}
        </button>
      </div>

      <div v-if="!readings.length" class="empty">
        <h3>Noch keine Werte</h3>
        <p>Erfasse deine erste Ablesung oder importiere die bestehende Historie per CSV.</p>
        <button class="btn btn-primary" @click="openReading">Erste Ablesung erfassen</button>
      </div>

      <div class="card" v-else>
        <div v-if="selectMode && canSelectAllFiltered" class="select-hint">
          Alle {{ pageIds.length }} auf dieser Seite ausgewählt.
          <button class="crumb" @click="selectAllFiltered">
            Alle {{ selectableIds.length }} Treffer auswählen
          </button>
        </div>

        <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-if="selectMode" class="col-sel">
                <!-- Zwischenstand über :indeterminate, sonst wäre eine teilweise
                     markierte Seite optisch nicht von einer leeren zu unterscheiden. -->
                <input type="checkbox" :checked="pageAllSelected"
                       :indeterminate.prop="pageSomeSelected"
                       @change="togglePage" :title="pageAllSelected ? 'Seite abwählen' : 'Seite auswählen'" />
              </th>
              <th @click="setSort('datum')">Datum <span class="arrow">{{ arrow('datum') }}</span></th>
              <th @click="setSort('value')" class="r">Zählerstand <span class="arrow">{{ arrow('value') }}</span></th>
              <th @click="setSort('consumption')" class="r">Verbrauch <span class="arrow">{{ arrow('consumption') }}</span></th>
              <th @click="setSort('cost')" class="r col-cost">Kosten <span class="arrow">{{ arrow('cost') }}</span></th>
              <th class="col-note">Notiz</th>
              <th class="col-del"></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="r in paged" :key="r.id">
            <tr class="row-main" :class="{expanded: expandedId===r.id, picked: selected.has(r.id)}"
                @click="toggleRow(r.id)">
              <td v-if="selectMode" class="col-sel">
                <input type="checkbox" :checked="selected.has(r.id)" @click.stop="toggleSelect(r.id)" />
              </td>
              <td>{{ fmtDate(r.datum) }}</td>
              <td class="r num">{{ fmt(r.value, 1) }}</td>
              <td class="r num">
                {{ fmt(r.consumption) }}
                <span v-if="r.meter_replaced" class="tag tag-swap">Tausch</span>
                <span v-if="r.is_outlier" class="tag tag-out">Ausreißer</span>
                <span class="chevron" aria-hidden="true">{{ expandedId===r.id ? '▾' : '▸' }}</span>
              </td>
              <td class="r num col-cost">{{ r.cost_effective === null || r.cost_effective === undefined ? '–' : (r.cost_estimated ? '≈ ' : '') + fmt(r.cost_effective) }}</td>
              <td class="col-note">
                <span v-if="r.source && r.source !== 'manual'"
                      class="chip" :class="'chip-' + r.source">{{ sourceLabel(r.source) }}</span>
                {{ r.note || '' }}
              </td>
              <td class="r col-del" style="white-space:nowrap" v-if="!selectMode">
                <button class="iconbtn" style="width:32px;height:32px" @click.stop="openEditReading(r)" title="Bearbeiten">✎</button>
                <hold-button :small="true" :round="true" @held="deleteReading(r)">✕</hold-button>
              </td>
            </tr>
            <tr v-if="expandedId===r.id && !selectMode" class="row-detail">
              <td colspan="6">
                <div class="detail-grid">
                  <div><span class="dg-label">Kosten</span><span class="num">{{ r.cost_effective === null || r.cost_effective === undefined ? '–' : (r.cost_estimated ? '≈ ' : '') + fmt(r.cost_effective) + ' €' }}<span v-if="r.cost_estimated" class="hint-inline"> (geschätzt via Ø-Preis)</span></span></div>
                  <div><span class="dg-label">Verbrauch/Tag</span><span class="num">{{ fmt(r.consumption_per_day, 3) }}</span></div>
                  <div v-if="r.note"><span class="dg-label">Notiz</span><span>{{ r.note }}</span></div>
                  <div style="display:flex;gap:8px">
                    <button class="btn btn-sm btn-tonal" @click.stop="openEditReading(r)">✎ Bearbeiten</button>
                    <hold-button :small="true" @held="deleteReading(r)">✕ Löschen (halten)</hold-button>
                  </div>
                </div>
              </td>
            </tr>
            </template>
          </tbody>
        </table>
        </div>
        <div class="pager" v-if="pageCount > 1">
          <button class="btn btn-sm" :disabled="page<=1" @click="page--">‹ Zurück</button>
          <span>Seite {{ page }} / {{ pageCount }}</span>
          <button class="btn btn-sm" :disabled="page>=pageCount" @click="page++">Weiter ›</button>
        </div>
      </div>
    </div>

    <!-- Aktionsleiste der Sammelauswahl -->
    <div class="bulk-bar" v-if="selectMode && selectedCount">
      <div class="bb-info">
        <strong>{{ selectedCount }}</strong> ausgewählt
        <small v-if="selectedSwaps">· {{ selectedSwaps }} Zählertausch</small>
      </div>
      <button class="btn btn-sm" :disabled="bulkBusy" @click="clearSelection">Aufheben</button>
      <hold-button :small="true" :disabled="bulkBusy" @held="deleteSelected">
        {{ bulkBusy ? 'Löscht …' : '✕ Löschen (halten)' }}
      </hold-button>
    </div>

    <!-- TAB: Zähler + Hardware-Empfehlung -->
    <div v-else-if="tab==='meters'" key="meters">
      <div v-if="!metersLoaded" class="center-load"><span class="spin"></span></div>
      <div class="empty" v-else-if="!meters.length">
        <h3>Noch kein Zähler hinterlegt</h3>
        <p>Trag Hersteller, Modell und Bauart ein – daraus leitet Zählwerk passende Auslese-Hardware für die Smart-Meter-Nachrüstung ab.</p>
        <button class="btn btn-primary" v-if="canWrite" @click="openMeter(null)">＋ Zähler anlegen</button>
      </div>

      <div v-else>
        <div class="eyebrow">
          Zähler
          <button class="btn btn-sm" v-if="canWrite" @click="openMeter(null)">＋ Zähler</button>
        </div>

        <div v-for="m in meters" :key="m.id" class="card meter-card" :class="{removed: !m.aktiv}">
          <div class="meter-head">
            <div>
              <div class="m-title">
                {{ m.hersteller || 'Hersteller unbekannt' }}<span v-if="m.modell"> · {{ m.modell }}</span>
              </div>
              <div class="m-sub">
                <span v-if="m.bauart">{{ m.bauart }}</span>
                <span v-if="m.zaehlernummer" class="num">Nr. {{ m.zaehlernummer }}</span>
                <span v-if="!m.aktiv">ausgebaut {{ fmtDate(m.ausgebaut_am) }}</span>
              </div>
            </div>
            <div class="m-actions" v-if="canWrite">
              <button class="btn btn-sm" @click="openMeter(m)">✎</button>
              <hold-button :small="true" @held="deleteMeter(m)">✕ halten</hold-button>
            </div>
          </div>

          <div v-if="eichungLabel(m)" class="due-badge" :class="eichungLabel(m).level">
            {{ eichungLabel(m).level === 'ok' ? '✓' : '⚠' }} {{ eichungLabel(m).text }}
          </div>

          <!-- Auto-Suggest -->
          <div class="hw-block" v-if="m.aktiv">
            <div class="hw-head">Auslese-Hardware</div>
            <div v-for="s in suggestFor(m)" :key="s.id" class="hw-item" :class="'conf-' + s.confidence">
              <div class="hw-top">
                <span class="hw-titel">{{ s.titel }}</span>
                <span class="hw-conf">{{ s.conf.label }}</span>
              </div>
              <div class="hw-grund">erkannt an: {{ s.grund }}</div>
              <ul class="hw-list"><li v-for="(h,i) in s.hardware" :key="i">{{ h }}</li></ul>
              <div class="hw-hinweis">{{ s.hinweis }}</div>
            </div>
            <div class="hint hw-disclaimer">
              Vorschläge ohne Gewähr. Zähler sind plombiert – alle genannten Verfahren arbeiten
              berührungslos von außen. Plomben nicht öffnen, Zähler nicht umbauen.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB: Tarife -->
    <div v-else-if="tab==='tariffs'" key="tariffs">
      <div v-if="!tariffsLoaded" class="center-load"><span class="spin"></span></div>
      <div class="empty" v-else-if="!tariffs.length">
        <h3>Noch kein Tarif hinterlegt</h3>
        <p>Mit Arbeitspreis und Grundgebühr je Zeitraum rechnet Zählwerk die Kosten
           jedes Intervalls selbst aus – auch wenn mitten darin der Tarif gewechselt hat.</p>
        <button class="btn btn-primary" v-if="canWrite" @click="openTariff(null)">＋ Tarif anlegen</button>
      </div>
      <div v-else>
        <div class="eyebrow">Tarife <button class="btn btn-sm" v-if="canWrite" @click="openTariff(null)">＋ Tarif</button></div>
        <div v-for="t in tariffs" :key="t.id" class="card tariff-card" :class="{current: t.aktiv}">
          <div class="tf-head">
            <div>
              <div class="tf-name">{{ t.name || 'Ohne Bezeichnung' }}<span v-if="t.anbieter"> · {{ t.anbieter }}</span></div>
              <div class="tf-range">{{ tariffRange(t) }}<span v-if="t.aktiv" class="tf-now">aktuell</span></div>
            </div>
            <div class="m-actions" v-if="canWrite">
              <button class="btn btn-sm" @click="openTariff(t)">✎</button>
              <hold-button :small="true" @held="deleteTariff(t)">✕ halten</hold-button>
            </div>
          </div>
          <div class="tf-prices">
            <span><small>Arbeitspreis</small>{{ fmt(t.arbeitspreis, 4) }} €/{{ system.einheit }}</span>
            <span><small>Grundpreis</small>{{ fmt(t.grundpreis, 2) }} €/Jahr</span>
          </div>
          <div class="hint" v-if="t.notiz">{{ t.notiz }}</div>
        </div>
      </div>
    </div>

    </transition>

    <!-- MODAL: Tarif -->
    <div class="overlay" v-if="showTariff" @click.self="showTariff=false">
      <div class="modal" v-if="tariffForm">
        <div class="modal-head"><h3>{{ tariffForm.id ? 'Tarif bearbeiten' : 'Neuer Tarif' }}</h3></div>
        <div class="modal-body">
          <div class="field-row">
            <div class="field"><label>Bezeichnung</label>
              <input class="input" v-model="tariffForm.name" placeholder="z. B. Grundversorgung 2024" /></div>
            <div class="field"><label>Anbieter</label>
              <input class="input" v-model="tariffForm.anbieter" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Gültig ab</label>
              <input class="input" type="date" v-model="tariffForm.gueltig_ab" /></div>
            <div class="field"><label>Gültig bis</label>
              <input class="input" type="date" v-model="tariffForm.gueltig_bis" />
              <div class="hint">Leer = läuft bis auf Weiteres.</div></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Arbeitspreis (€/{{ system.einheit }})</label>
              <input class="input" type="number" step="0.0001" min="0" inputmode="decimal"
                     v-model="tariffForm.arbeitspreis" placeholder="0,2950" /></div>
            <div class="field"><label>Grundpreis (€/Jahr)</label>
              <input class="input" type="number" step="0.01" min="0" inputmode="decimal"
                     v-model="tariffForm.grundpreis" /></div>
          </div>
          <label class="tf"><input class="tf-input" v-model="tariffForm.notiz" placeholder=" " /><span class="tf-label">Notiz (optional)</span></label>
          <div class="hint">
            Zeiträume dürfen sich nicht überschneiden – sonst wäre für einen Tag nicht
            eindeutig, welcher Preis gilt. Der Server weist das ab.
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="showTariff=false">Abbrechen</button>
          <button class="btn btn-primary" :disabled="busy" @click="saveTariff">Speichern</button>
        </div>
      </div>
    </div>

    <!-- MODAL: Zähler -->
    <div class="overlay" v-if="showMeter" @click.self="showMeter=false">
      <div class="modal">
        <div class="modal-head"><h3>{{ meterForm.id ? 'Zähler bearbeiten' : 'Neuer Zähler' }}</h3></div>
        <div class="modal-body">
          <div class="field-row">
            <div class="field"><label>Hersteller</label>
              <input class="input" v-model="meterForm.hersteller" placeholder="z. B. Pipersberg" /></div>
            <div class="field"><label>Modell</label>
              <input class="input" v-model="meterForm.modell" placeholder="z. B. mMe4.0" /></div>
          </div>
          <div class="field">
            <label>Bauart</label>
            <input class="input" v-model="meterForm.bauart" list="zw-bauarten" placeholder="Vorschläge verfügbar" />
            <datalist id="zw-bauarten"><option v-for="b in bauarten" :key="b" :value="b"></option></datalist>
          </div>

          <!-- Live-Vorschau: reagiert auf jede Eingabe, noch vor dem Speichern -->
          <div class="hw-preview" v-if="suggestFor(meterForm).length">
            <div class="hw-head">Passende Hardware</div>
            <div v-for="s in suggestFor(meterForm)" :key="s.id" class="hw-item" :class="'conf-' + s.confidence">
              <div class="hw-top">
                <span class="hw-titel">{{ s.titel }}</span>
                <span class="hw-conf">{{ s.conf.label }}</span>
              </div>
              <ul class="hw-list"><li v-for="(h,i) in s.hardware" :key="i">{{ h }}</li></ul>
            </div>
          </div>

          <div class="field-row">
            <div class="field"><label>Zählernummer</label>
              <input class="input" v-model="meterForm.zaehlernummer" /></div>
            <div class="field"><label>Baujahr</label>
              <input class="input" type="number" inputmode="numeric" min="1900" max="2100" v-model="meterForm.baujahr" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Eichung gültig bis</label>
              <input class="input" type="date" v-model="meterForm.eichung_bis" /></div>
            <div class="field"><label>Messstellenbetreiber</label>
              <input class="input" v-model="meterForm.messstellenbetreiber" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Stellen vor dem Komma</label>
              <input class="input" type="number" inputmode="numeric" min="1" max="12" v-model="meterForm.stellen_vor" /></div>
            <div class="field"><label>Stellen nach dem Komma</label>
              <input class="input" type="number" inputmode="numeric" min="0" max="6" v-model="meterForm.stellen_nach" /></div>
          </div>
          <div class="field-row">
            <div class="field"><label>Eingebaut am</label>
              <input class="input" type="date" v-model="meterForm.eingebaut_am" /></div>
            <div class="field"><label>Ausgebaut am</label>
              <input class="input" type="date" v-model="meterForm.ausgebaut_am" /></div>
          </div>
          <label class="tf"><input class="tf-input" v-model="meterForm.notiz" placeholder=" " /><span class="tf-label">Notiz (optional)</span></label>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="showMeter=false">Abbrechen</button>
          <button class="btn btn-primary" :disabled="busy" @click="saveMeter">Speichern</button>
        </div>
      </div>
    </div>

    <!-- MODAL: Ablesung -->
    <div class="overlay" v-if="showReading" @click.self="showReading=false">
      <div class="modal">
        <div class="modal-head"><h3>{{ reading.id ? 'Ablesung bearbeiten' : 'Neue Ablesung' }} – {{ system.name }}</h3></div>
        <div class="modal-body">
          <!-- Primaerfeld zuerst und ueber die volle Breite: im Keller wird
               zuerst der Zaehlerstand getippt, das Datum ist vorbelegt. -->
          <div class="field reading-value">
            <div class="input-scan">
              <label class="tf"><input class="tf-input" type="number" step="any"
                     inputmode="decimal" enterkeyhint="done" autocomplete="off"
                     v-model="reading.value" placeholder=" " ref="valueInput"
                     @input="ocrHint = null; reading.source = 'manual'" /><span class="tf-label">Zählerstand ({{ system.einheit }})</span></label>
              <button class="btn scan-trigger" @click="openScanner"
                      aria-label="Zählerstand per Kamera scannen" title="Zählerstand per Kamera scannen (Beta)">📷</button>
            </div>
          </div>
          <!-- Hinweis nach automatischer Erkennung: der Wert ist ein Vorschlag,
               keine Messung. Wird beim Tippen ausgeblendet. -->
          <div class="ocr-hint" v-if="ocrHint" :class="{ warn: !ocrHint.plausible }">
            <div class="oh-main">
              {{ ocrHint.plausible ? '✓' : '⚠' }} Wert automatisch erkannt – bitte prüfen
            </div>
            <div class="oh-sub">
              Sicherheit {{ Math.round(ocrHint.confidence) }} %
              <span v-if="ocrHint.previous">· letzter Stand {{ fmt(ocrHint.previous, 1) }}</span>
              <span v-if="!ocrHint.plausible">· liegt außerhalb des erwarteten Bereichs</span>
            </div>
            <div class="oh-alt" v-if="ocrHint.candidates.length > 1">
              Alternativen:
              <button v-for="c in ocrHint.candidates" :key="c" class="crumb"
                      v-show="c !== ocrHint.value" @click="reading.value = String(c)">
                {{ fmt(c, 3) }}
              </button>
            </div>
          </div>

          <div class="field"><label>Datum</label><input class="input" type="date" v-model="reading.datum" /></div>
          <label class="tf"><input class="tf-input" type="number" step="any"
                 inputmode="decimal" autocomplete="off"
                 v-model="reading.cost" placeholder=" " /><span class="tf-label">Kosten € (optional)</span></label>
          <div class="field">
            <button v-if="haEntity && !reading.id" class="btn btn-tonal btn-sm" style="margin-bottom:14px" :disabled="busy" @click="fetchHaValue">⌂ Zählerstand aus Home Assistant übernehmen</button>
            <label class="check"><input type="checkbox" v-model="reading.meter_replaced" /> Zählertausch (neuer Zähler)</label>
            <div class="hint" v-if="reading.meter_replaced">Vorgehen beim Tausch: <strong>1.</strong> Endstand des alten Zählers als normale Ablesung erfassen. <strong>2.</strong> Diesen Eintrag hier mit dem aktuellen Stand des NEUEN Zählers anlegen (gleiches Datum ist ok). Startet der neue Zähler nicht bei 0, dessen Startstand unten eintragen – der Verbrauch ist dann die Differenz.</div>
            <label class="tf" v-if="reading.meter_replaced" style="margin-top:12px"><input class="tf-input" type="number" step="any" inputmode="decimal" autocomplete="off" v-model="reading.meter_start" placeholder=" " /><span class="tf-label">Startstand neuer Zähler (optional, meist 0)</span></label>
            <div class="hint" v-if="latestValue!==null && !reading.meter_replaced">Letzter Stand: {{ fmt(latestValue,1) }} {{ system.einheit }} – neuer Wert muss ≥ sein.</div>
          </div>
          <label class="tf"><input class="tf-input" v-model="reading.note" placeholder=" " /><span class="tf-label">Notiz (optional)</span></label>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="showReading=false">Abbrechen</button>
          <button class="btn btn-primary" :disabled="busy" @click="saveReading">Speichern</button>
        </div>
      </div>
    </div>

    <!-- OVERLAY: OCR-Scanner -->
    <div class="overlay" v-if="showScanner" @click.self="closeScanner">
      <div class="modal modal-scan">
        <div class="modal-head"><h3>📷 Zählerstand scannen <span class="beta">Beta</span></h3></div>
        <div class="modal-body">
          <div class="scan-stage" v-if="!scanFileMode">
            <video ref="scanVideo" playsinline muted></video>
            <div class="scan-frame"></div>
          </div>
          <button v-else class="scan-filebtn" @click="triggerScanFile">📷 Foto mit nativer Kamera aufnehmen</button>
          <button class="scan-filebtn scan-gallery" @click="triggerGalleryFile">🖼 Foto aus Galerie wählen<br /><small>Ablesedatum wird aus den Foto-Metadaten übernommen</small></button>
          <input ref="scanFile" type="file" accept="image/*" capture="environment" style="display:none" @change="onScanFile" />
          <input ref="galleryFile" type="file" accept="image/*" style="display:none" @change="onScanFile" />
          <div class="hint" style="margin-top:8px">{{ scanStatus }}</div>
          <button v-if="!scanFileMode" class="crumb" style="margin-top:6px" @click="scanFileMode=true; closeStreamOnly()">Stream klappt nicht? → Stattdessen natives Foto nutzen</button>
          <div class="hint"><strong>Beta.</strong> Für beste Ergebnisse: Zählwerk <strong>formatfüllend</strong> und <strong>gerade</strong> in den Rahmen, gutes Licht, keine Spiegelung. Am zuverlässigsten bei geraden schwarz-weißen Rollenzählwerken. Digitale LCD-Displays und runde/schräge Zähler sind fehleranfällig – Wert immer prüfen.</div>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="closeScanner">Abbrechen</button>
          <button class="btn btn-primary" :disabled="scanBusy" @click="captureScan">{{ scanBusy ? 'Erkenne …' : (scanFileMode ? 'Foto aufnehmen' : 'Auslösen') }}</button>
        </div>
      </div>
    </div>

    <!-- MODAL: Import -->
    <div class="overlay" v-if="showImport" @click.self="showImport=false">
      <div class="modal">
        <div class="modal-head"><h3>CSV-Import – {{ system.name }}</h3></div>
        <div class="modal-body">
          <p class="hint">Spalten: <code>datum, wert, kosten, zaehlertausch, notiz</code>. Datum als <code>JJJJ-MM-TT</code> oder <code>TT.MM.JJJJ</code>.</p>
          <div class="field"><button class="btn btn-sm" @click="downloadTemplate">⤓ Vorlage herunterladen</button></div>
          <div class="field"><label>CSV-Datei</label><input class="input" type="file" accept=".csv" @change="onFile" /></div>
          <div v-if="importResult" class="hint">
            <strong>{{ importResult.imported }}</strong> importiert, {{ importResult.skipped }} übersprungen.
            <ul v-if="importResult.errors.length"><li v-for="(e,i) in importResult.errors" :key="i">{{ e }}</li></ul>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="showImport=false">Schließen</button>
          <button class="btn btn-primary" :disabled="busy || !importFile" @click="runImport">Importieren</button>
        </div>
      </div>
    </div>
  </div>
  `,
};

/* =========================================================================
   Root-App
   ========================================================================= */
createApp({
  components: { SystemDetail, HoldButton, WidgetLineChart, WidgetPieChart,
                WidgetLatestReading, WidgetCostSummary, WidgetTrend,
                WidgetCostForecast },
  provide() { return { notify: this.notify }; },
  data: () => ({
    systems: [],
    loading: true,
    view: "menu",
    selected: null,
    showArchived: false,
    showSystem: false,
    sysForm: null,
    busy: false,
    toast: null,
    palette: PALETTE,
    palettes: PALETTES,
    contrasts: CONTRASTS,
    chartColorKeys: CHART_COLOR_KEYS,
    chartPrefs,
    types: SYSTEM_TYPES,
    latest: {},                // system_id -> { value, datum }
    showChangelog: false,
    /* Sektion A: serverseitige Anwendungsparameter */
    appSettings: null,
    appSettingsDraft: null,
    settingsErrors: {},
    settingsSaving: false,
    sysInfo: null,
    extStatus: null,
    backupStatus: null,
    backupBusy: false,
    restoreBusy: null,       // Dateiname der laufenden Wiederherstellung, sonst null
    restoreFile: null,       // hochgeladene Datei, noch nicht bestätigt
    restoreConfirm: null,    // { kind: 'existing'|'upload', filename } während der Bestätigung
    restoreConfirmText: "",
    mqttStatus: null,
    mqttPassword: "",
    assignTarget: {},
    /* Pre-Export-Dialog: expCfg ist die einzige Sichtbarkeitsquelle. Es steuert
       zugleich die Bottom-Nav-Markierung (activeNav -> "bericht"), darum muss es
       auf jedem Schließpfad wieder auf null gesetzt werden. */
    expCfg: null,
    /* Vom Detail-Component gemeldeter aktiver Tab – reaktive Basis für die
       kontextbezogene FAB-Beschriftung (statt des nicht-reaktiven $refs). */
    detailTab: "chart",
    appVersion: APP_VERSION,
    changelog: APP_CHANGELOG,
    /* Sidebar: navExpanded = Desktop (Rail <-> Drawer), navDrawer = Mobile-Overlay */
    navExpanded: localStorage.getItem("zw_nav_expanded") === "1",
    navDrawer: false,
    navItems: NAV_ITEMS,
    // Je Elternpunkt ein eigener Zustand – mit einer gemeinsamen Flagge
    // klappten beide Listen zusammen auf und zu.
    navSubOpen: (() => {
      try { return JSON.parse(localStorage.getItem("zw_nav_sub")) || {}; }
      catch (_) { return {}; }
    })(),
    showSysSheet: false,
    auth: authStore,
    authForm: { username: "", display_name: "", password: "", password2: "" },
    authError: null,
    authBusy: false,
    users: [],
    dashTiles: [],
    dashData: [],
    dashRecent: [],
    dashEdit: false,
    dashDirty: false,
    dashLoading: false,
    dashDragId: null,
    widgetTypes: WIDGET_TYPES,
    timeframes: TIMEFRAMES,
    tileCfg: null,
    adminDiag: null,
    adminSchema: [],
    adminLogs: [],
    adminTab: "system",
    auditEntries: [],
    auditUndoBusy: null,
    auditFacets: { actions: [], tables: [], users: [] },
    auditFilter: { action: null, target_table: null, user_id: null, from: "", to: "" },
    auditPage: 1, auditPages: 1, auditTotal: 0, auditLoading: false,
    logLevel: "INFO",
    sqlText: "SELECT name, typ, einheit FROM systems ORDER BY name",
    sqlResult: null,
    sqlError: null,
    sqlBusy: false,
  }),
  computed: {
    visibleSystems() { return this.systems.filter((s) => this.showArchived || s.aktiv); },
    selectedSystem() { return this.systems.find((s) => s.id === this.selected) || null; },
    formExtra() { return this.sysForm ? [...(EXTRA_FIELDS[this.sysForm.typ] || []), ...COMMON_FIELDS] : []; },
    themeMode() { return themeStore.mode; },
    themePalette() { return themeStore.palette; },
    themeContrast() { return themeStore.contrast; },
    /* aktiver Navigationspunkt (Einstellungen als Modal hat Vorrang vor der Ansicht) */
    activeNav() {
      // Der Bericht ist ein Modal, keine eigene Ansicht: solange der
      // Export-/Berichtsdialog offen ist, gilt dessen Bottom-Nav-Ziel als aktiv.
      if (this.expCfg) return "bericht";
      if (this.view === "dashboard") return "auswertungen";
      if (this.view === "settings") return "einstellungen";
      if (this.view === "admin") return "admin";
      return "zaehlwerk";
    },
    navMenuIcon() { return SVG.menu; },
    chevronIcon() { return SVG.chevron; },
    navHomeIcon() { return SVG.home; },
    greeting() {
      const h = new Date().getHours();
      return h < 5 ? "Gute Nacht" : h < 11 ? "Guten Morgen"
           : h < 18 ? "Guten Tag" : "Guten Abend";
    },
    todayLong() {
      return new Date().toLocaleDateString("de-DE",
        { weekday: "long", day: "numeric", month: "long" });
    },
    /* Die drei Systeme mit dem höchsten Tagesverbrauch – das sind die, bei
       denen sich Hinsehen lohnt. Jeweils mit Trend gegen die Vorperiode. */
    /* Alle aktiven Zähler für die Schnellerfassung, meistgenutzte (höchster
       Tagesverbrauch) zuerst – der am häufigsten abgelesene Zähler steht damit
       ohne Scrollen oben. */
    mobileMeters() {
      return this.dashData
        .map((s) => ({ ...s, trend: this.trendOf(s) }))
        .sort((a, b) => (b.avg_per_day || 0) - (a.avg_per_day || 0));
    },
    tileTypeDef() {
      return WIDGET_TYPES.find((w) => w.key === (this.tileCfg || {}).type) || WIDGET_TYPES[0];
    },
    /* Maske nur zeigen, wenn der Status bekannt UND die Anmeldung nötig ist.
       Vor der ersten Antwort würde sie sonst kurz aufblitzen. */
    authNeeded() {
      const s = this.auth.status;
      return !!(this.auth.checked && s && !s.authenticated);
    },
    currentUser() { return (this.auth.status || {}).user || null; },
    authRoles() { return (this.auth.status || {}).roles || []; },
    /* Einzige Quelle für die Sichtbarkeit im UI. Sie kommt vom Server, damit
       Oberfläche und Middleware nicht auseinanderlaufen können. Das Ausblenden
       ist Bequemlichkeit – durchgesetzt werden die Rechte im Backend. */
    perms() { return perms(); },
    canWrite() { return !!this.perms.write; },
    isAdmin() { return !!this.perms.admin; },
    canExport() { return !!this.perms.export; },
    setupValid() {
      const f = this.authForm;
      return f.username.trim().length >= 3 && f.password.length >= 12
             && f.password === f.password2;
    },
    /* Unterpunkte = aktive Systeme in der Reihenfolge der Übersicht.
       Archivierte bleiben draußen: die Sidebar ist ein Sprungziel für den
       Alltag, nicht der Ort, an dem Altbestand verwaltet wird. */
    navSubItems() { return this.systems.filter((s) => s.aktiv); },
    /* Die Bottom-Bar zeigt dieselben Ziele wie die Seitenleiste, gefiltert auf
       die primären. Der Rollenfilter steckt bereits in visibleNavItems – das
       Admin-Ziel wird also gar nicht erst gerendert, nicht bloß versteckt.

       Zusätzlich bekommt „Berichterstellung“ hier ein eigenes Ziel: im Rail ist
       der Bericht ein aufklappbarer Unterpunkt von Auswertungen, doch die
       schmale Bottom-Bar kennt keine Unterlisten. Ohne diesen Eintrag wäre der
       Bericht über die untere Navigation gar nicht erreichbar. Er erscheint nur
       mit Export-Recht – ohne das öffnet der Dialog ohnehin nichts Sinnvolles. */
    bottomNavItems() {
      const items = this.visibleNavItems.filter((i) => i.primary);
      if (!this.canExport) return items;
      const out = [...items];
      const at = out.findIndex((i) => i.key === "auswertungen");
      out.splice(at >= 0 ? at + 1 : out.length, 0, {
        key: "bericht", label: "Berichterstellung", short: "Bericht",
        icon: SVG.report, action: "openCombinedReport", primary: true,
      });
      return out;
    },
    fabLabel() {
      if (this.view === "menu") return "System";
      if (this.detailTab === "meters") return "Zähler";
      if (this.detailTab === "tariffs") return "Tarif";
      return "Wert";
    },
    /* Der FAB erscheint nur, wo er auch etwas anlegt: in der Systemübersicht
       (neues System) und in der Zähler-Detailansicht (neue Ablesung bzw. neuer
       Zähler). Auf Dashboard, Startseite, Einstellungen und Admin-Tools hatte er
       keine Funktion und verdeckte dort Speicher-Dialoge – deshalb wird er auf
       diesen Ansichten gar nicht erst gerendert, statt nur wirkungslos zu sein. */
    showFab() {
      return this.canWrite && (this.view === "menu" || this.view === "detail");
    },
    visibleNavItems() {
      return this.navItems.filter((i) => {
        if (i.needsSystems && !this.systems.length) return false;
        // Einstellungen bleiben für ALLE erreichbar: Sektion B (Darstellung,
        // Palette, Diagrammfarben) ist gerätelokal und betrifft jedes Konto.
        // Nur Sektion A ist administratorenpflichtig und wird dort ausgeblendet.
        if (i.adminOnly && !this.isAdmin) return false;

        return true;
      });
    },
  },
  async mounted() {
    // Rückruf des Interceptors: bei 401 wird der Status neu geholt, wodurch
    // die Maske erscheint – ohne dass jede Aufrufstelle das selbst behandeln muss.
    onUnauthorized = () => { this.auth.checked = true; };
    this.applyNavClass();
    window.addEventListener("keydown", this.onNavKey);
    window.addEventListener("resize", this.onNavResize);
    if (await this.checkAuth()) {
      await this.load();
      // Auf schmalen Geräten die kompakte Startseite, sonst die Systemliste.
      if (this.isMobileViewport()) this.openMobileHome();
    }
  },
  unmounted() {
    window.removeEventListener("keydown", this.onNavKey);
    window.removeEventListener("resize", this.onNavResize);
  },
  methods: {
    fmt, typeIcon, fmtDate, sourceLabel,

    /* ---------- Sidebar ---------- */
    isCompact() { return window.innerWidth <= NAV_BREAKPOINT; },
    applyNavClass() { document.body.classList.toggle("nav-expanded", this.navExpanded); },
    toggleNav() {
      // Unterhalb des Breakpoints gibt es ausschliesslich die Bottom-Bar; der
      // Menue-Button ist dort per CSS ausgeblendet. Der Guard bleibt als
      // Absicherung, falls der Klick auf anderem Weg ausgeloest wird.
      if (this.isCompact()) return;
      this.navExpanded = !this.navExpanded;
      localStorage.setItem("zw_nav_expanded", this.navExpanded ? "1" : "0");
      // navSubOpen bleibt gespeichert: klappt die Rail wieder auf, steht die
      // Unterliste so, wie der Nutzer sie zuletzt verlassen hat.
      this.applyNavClass();
    },
    closeDrawer() { this.navDrawer = false; },
    toggleNavSub(key) {
      this.navSubOpen = { ...this.navSubOpen, [key]: !this.navSubOpen[key] };
      localStorage.setItem("zw_nav_sub", JSON.stringify(this.navSubOpen));
    },
    /* Unterpunkte kommen entweder aus einer festen Liste am Navigationseintrag
       oder – beim Zählwerk – dynamisch aus den aktiven Systemen. */
    subItemsFor(item) {
      if (item.children) {
        return item.children.filter((c) => !c.needsExport || this.canExport);
      }
      return item.expandable ? this.navSubItems : [];
    },
    subItemActive(sub) {
      if (sub.id) return this.view === "detail" && this.selected === sub.id;
      return sub.key === "dashboard" && this.view === "dashboard";
    },
    goSubItem(sub) {
      this.closeDrawer();
      if (sub.id) { this.open(sub); return; }
      this[sub.action]();
    },
    goSystem(s) {
      this.closeDrawer();
      this.open(s);
    },

    /* ---------- Anmeldung ---------- */
    async checkAuth() {
      try {
        this.auth.status = await api("/api/auth/status");
      } catch (_) {
        this.auth.status = { authenticated: false, setup_required: false,
                             mode: "lokal", crypto_available: true };
      } finally {
        this.auth.checked = true;
      }
      return this.auth.status.authenticated;
    },
    async doLogin() {
      this.authBusy = true; this.authError = null;
      try {
        await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ username: this.authForm.username.trim(),
                                 password: this.authForm.password }),
        });
        this.authForm = { username: "", display_name: "", password: "", password2: "" };
        await this.checkAuth();
        await this.load();
      } catch (e) { this.authError = e.message; }
      finally { this.authBusy = false; }
    },
    async doSetup() {
      if (!this.setupValid) return;
      this.authBusy = true; this.authError = null;
      try {
        await api("/api/auth/setup", {
          method: "POST",
          body: JSON.stringify({ username: this.authForm.username.trim(),
                                 display_name: this.authForm.display_name || null,
                                 password: this.authForm.password }),
        });
        this.authForm = { username: "", display_name: "", password: "", password2: "" };
        await this.checkAuth();
        await this.load();
      } catch (e) { this.authError = e.message; }
      finally { this.authBusy = false; }
    },
    async doLogout() {
      try { await api("/api/auth/logout", { method: "POST" }); } catch (_) {}
      await this.checkAuth();
    },

    /* ---------- Mobile Bottom Sheet ---------- */
    /* M3: die Primäraktion eines Navigationsziels muss immer zuerst greifen.
       Der erste Tipp führt daher zur Übersicht; erst ein Tipp auf das BEREITS
       aktive Ziel öffnet die Systemauswahl. So ist die Übersicht nie hinter
       einem Overlay versteckt, und der Pfeil am aktiven Eintrag zeigt an,
       dass dort noch etwas liegt. */
    goNavMobile(item) {
      if (item.expandable && this.navSubItems.length && this.activeNav === item.key) {
        this.showSysSheet = true;
        return;
      }
      this.goNav(item);
    },
    sheetGoOverview() {
      this.showSysSheet = false;
      this.back();
    },
    sheetGoSystem(s) {
      this.showSysSheet = false;
      this.open(s);
    },
    sheetNewSystem() {
      this.showSysSheet = false;
      this.newSystem();
    },
    onNavKey(ev) {
      if (ev.key !== "Escape") return;
      if (this.showSysSheet) { this.showSysSheet = false; return; }
      if (this.navDrawer) this.navDrawer = false;
    },
    /* Beim Wechsel auf einen schmalen Viewport darf kein Drawer offen bleiben,
       sonst laege er unsichtbar ueber der Bottom-Bar und blockierte Klicks. */
    onNavResize() {
      if (this.isCompact() && this.navDrawer) this.navDrawer = false;
      if (!this.isCompact() && this.showSysSheet) this.showSysSheet = false;
    },
    /* Startseite je nach Gerät. Entschieden wird einmal beim Start, nicht bei
       jeder Größenänderung: ein Wechsel der Ansicht mitten in der Bedienung
       wäre überraschend. Über die Navigation bleibt beides erreichbar. */
    isMobileViewport() { return window.innerWidth < 768; },
    openMobileHome() {
      this.view = "mobile-home";
      window.scrollTo(0, 0);
      if (!this.dashData.length) this.loadDashboard();
    },
    openSystemById(id) {
      const s = this.systems.find((x) => x.id === id);
      if (s) this.open(s);
    },
    /* Schnellerfassung je Zähler: öffnet direkt den Ablesedialog des gewählten
       Systems – ohne den Umweg über die Übersicht und die Systemauswahl. Genau
       das war der Reibungspunkt beim Ablesen „im Vorbeigehen“. */
    async mobileQuickRead(systemId, withScanner) {
      const s = this.systems.find((x) => x.id === systemId);
      if (!s) { this.notify("System nicht gefunden", "err"); return; }
      this.open(s);
      await this.$nextTick();
      const d = this.$refs.detail;
      if (!d) return;
      d.openReading();
      if (withScanner) { await this.$nextTick(); d.openScanner(); }
    },

    openDashboard() {
      this.view = "dashboard";
      window.scrollTo(0, 0);
      if (!this.dashTiles.length) this.loadDashboard();
    },
    openAdmin() {
      this.view = "admin";
      window.scrollTo(0, 0);
      this.loadAdmin();
      this.loadSettings();     // Systemparameter, Netzwerk, Zugriff, Zeitplan haengen alle davon ab
    },
    async loadAdmin() {
      try {
        const [d, s] = await Promise.all([
          api("/api/admin/diagnostics"), api("/api/admin/schema"),
        ]);
        this.adminDiag = d;
        this.adminSchema = s.tables;
      } catch (e) { this.notify(e.message, "err"); }
      this.loadAdminLogs();
    },
    async loadBackupStatus() {
      try { this.backupStatus = await api("/api/backup"); }
      catch (e) { this.notify(e.message, "err"); }
    },
    /* Wiederherstellung ist destruktiv: der aktuelle Bestand wird zwar vorher
       automatisch weggesichert, alles seit der gewählten Sicherung geht aber
       verloren. Ein einfaches Ja/Nein ist dafür zu leicht wegzuklicken – die
       Bestätigung verlangt deshalb, das Wort RESTORE abzutippen. */
    restoreBackup(filename) {
      this.restoreConfirm = { kind: "existing", filename };
      this.restoreConfirmText = "";
    },
    onRestoreFile(e) { this.restoreFile = e.target.files[0] || null; },
    importRestore() {
      if (!this.restoreFile) return;
      this.restoreConfirm = { kind: "upload", filename: this.restoreFile.name };
      this.restoreConfirmText = "";
    },
    cancelRestore() { this.restoreConfirm = null; this.restoreConfirmText = ""; },
    async confirmRestore() {
      const target = this.restoreConfirm;
      if (!target || this.restoreConfirmText !== "RESTORE" || this.restoreBusy) return;
      this.restoreBusy = target.filename;
      try {
        let r;
        if (target.kind === "existing") {
          r = await api(`/api/backup/restore/${encodeURIComponent(target.filename)}`, { method: "POST" });
        } else {
          const fd = new FormData();
          fd.append("file", this.restoreFile);
          // Kein Content-Type setzen – der Browser ergänzt die Trennmarke selbst.
          const res = await fetch("api/backup/import", {
            method: "POST", body: fd, credentials: "same-origin",
          });
          if (!res.ok) {
            let d; try { d = await res.json(); } catch (_) {}
            throw new Error((d && d.detail) || res.statusText);
          }
          r = await res.json();
        }
        this.notify(`Wiederhergestellt aus ${r.restored_from}`
          + (r.safety_backup ? ` · Sicherheitskopie: ${r.safety_backup}` : ""), "ok");
        this.restoreFile = null;
        this.restoreConfirm = null;
        this.restoreConfirmText = "";
        await this.loadBackupStatus();
        await this.load();          // Systeme/Ablesungen: Datenbestand hat sich geändert
      } catch (e) { this.notify("Wiederherstellung fehlgeschlagen: " + e.message, "err"); }
      finally { this.restoreBusy = null; }
    },
    async loadAudit(page = 1) {
      this.auditLoading = true;
      try {
        const p = new URLSearchParams({ page: String(page), per_page: "50" });
        for (const [k, v] of Object.entries(this.auditFilter)) {
          if (v) p.set(k, v);
        }
        const r = await api(`/api/admin/audit?${p}`);
        this.auditEntries = r.entries;
        this.auditPage = r.page;
        this.auditPages = r.pages;
        this.auditTotal = r.total;
        if (!this.auditFacets.actions.length) {
          this.auditFacets = await api("/api/admin/audit/facets");
        }
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.auditLoading = false; }
    },
    resetAuditFilter() {
      this.auditFilter = { action: null, target_table: null, user_id: null, from: "", to: "" };
      this.loadAudit(1);
    },
    /* Kurzfassung der Änderung. Der vollständige Vergleich stünde in der
       Tabelle unlesbar; die geänderten Felder genügen zur Einordnung. */
    auditSummary(e) {
      if (e.new_value && e.new_value.bulk) {
        return `${e.new_value.count} Datensätze (Sammelvorgang)`;
      }
      if (e.action === "UPDATE" && e.new_value) {
        return Object.entries(e.new_value)
          .map(([k, v]) => `${k}: ${e.old_value && e.old_value[k] !== undefined ? e.old_value[k] : '–'} → ${v}`)
          .join(", ");
      }
      const src = e.action === "DELETE" ? e.old_value : e.new_value;
      if (!src) return "–";
      return Object.entries(src)
        .filter(([k]) => !["id", "system_id", "erstellt_am"].includes(k))
        .slice(0, 4).map(([k, v]) => `${k}: ${v}`).join(", ");
    },
    /* Sammelvorgänge (CSV-Import, Bulk-Delete) haben keine Einzeldaten im
       Protokoll und lassen sich serverseitig deshalb nicht rückgängig machen -
       der Knopf bleibt dafür verborgen statt jedes Mal fehlzuschlagen. */
    auditCanRollback(e) {
      return !!e.target_id && !(e.new_value && e.new_value.bulk);
    },
    async undoAuditEntry(e) {
      if (!confirm(`Diese Änderung rückgängig machen?\n\n${this.auditSummary(e)}\n\n`
        + "Wurde der Datensatz seither erneut geändert, geht diese neuere Änderung dabei verloren.")) return;
      this.auditUndoBusy = e.id;
      try {
        await api(`/api/admin/audit/rollback/${e.id}`, { method: "POST" });
        this.notify("Rückgängig gemacht", "ok");
        await this.loadAudit(this.auditPage);
      } catch (err) {
        this.notify("Rückgängig machen fehlgeschlagen: " + err.message, "err");
      } finally { this.auditUndoBusy = null; }
    },

    async loadAdminLogs() {
      try {
        const r = await api(`/api/admin/logs?lines=200&level=${this.logLevel}`);
        this.adminLogs = r.entries;
      } catch (_) { this.adminLogs = []; }
    },
    async runQuery() {
      if (!this.sqlText.trim()) return;
      this.sqlBusy = true; this.sqlError = null;
      try {
        this.sqlResult = await api("/api/admin/query", {
          method: "POST", body: JSON.stringify({ sql: this.sqlText }),
        });
      } catch (e) { this.sqlError = e.message; this.sqlResult = null; }
      finally { this.sqlBusy = false; }
    },
    useSample(sql) { this.sqlText = sql; this.runQuery(); },

    openSettings() {
      this.view = "settings";
      window.scrollTo(0, 0);
    },
    goNav(item) {
      if (item.disabled || !item.action) return;
      this.closeDrawer();
      this[item.action]();
    },
    /* Globaler Sprung zur Startseite über das Logo/den Titel oben links.
       Ziel ist dieselbe Startseite wie beim App-Start: auf schmalen Geräten die
       kompakte Startseite, sonst die Systemübersicht. Offene Overlays (Drawer,
       System-Sheet) werden dabei geschlossen, damit der Klick nicht ins Leere
       läuft. Auf allen Ansichten erreichbar – auch aus Admin-Tools heraus. */
    goHome() {
      this.closeDrawer();
      this.showSysSheet = false;
      if (this.isMobileViewport()) this.openMobileHome();
      else this.back();
    },
    notify(msg, type = "ok") { this.toast = { msg, type }; setTimeout(() => (this.toast = null), 3200); },
    async load() {
      this.loading = true;
      try {
        this.systems = await api("/api/systems?include_archived=true");
        try { this.latest = await api("/api/overview"); } catch (_) { this.latest = {}; }
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.loading = false; }
    },
    open(s) {
      this.selected = s.id;
      this.view = "detail";
      // Kontext zeigen: wer in ein System springt, sieht in der Sidebar, wo er ist
      if (this.navExpanded && !this.navSubOpen.zaehlwerk) this.toggleNavSub("zaehlwerk");
      window.scrollTo(0, 0);
    },
    back() { this.view = "menu"; this.selected = null; this.load(); },
    exportAll() {
      fetchBlobDownload("api/export.zip", "zaehlwerk-backup.zip")
        .then(() => this.notify("Backup erstellt (alle Systeme + Konfiguration)", "ok"))
        .catch((e) => this.notify("Export fehlgeschlagen: " + e.message, "err"));
    },
    /* Sammelt die Theme-Farben aus dem lebenden CSS – so spiegelt der Export
       exakt die aktive Palette samt Kontraststufe und Nutzer-Chartfarben.
       Der Export ist ein Dokument auf weißem Papier: im Dunkelmodus wären die
       hellen Rollen unbrauchbar, deshalb wird dort auf die Hell-Werte gemappt. */
    exportTheme() {
      const dark = themeStore.dark;
      const v = (n, fb) => cssVar(n) || fb;
      return {
        accent:   dark ? v("--md-primary-container", "#0e7c86") : v("--md-primary", "#0e7c86"),
        ink:      dark ? "#172533" : v("--md-on-surface", "#172533"),
        ink_soft: dark ? "#5b6b7b" : v("--md-on-surface-variant", "#5b6b7b"),
        line:     dark ? "#cfd8e1" : v("--md-outline-variant", "#cfd8e1"),
        warn:     chartColor("outlier", "#d9820a"),
      };
    },
    openExportConfig() {
      const t = this.exportTheme();
      this.expCfg = {
        format: "pdf",
        preset: "all",
        from: "", to: "",
        systemIds: this.systems.filter((s) => s.aktiv).map((s) => s.id),
        includeInactive: false,
        useTheme: true,
        systemColors: true,
        includeChart: true,
        includeTable: true,
        dialect: "de",
        sources: [],
        includeDerived: true,
        includeMeta: true,
        theme: t,
      };
    },
    expApplyPreset(p) {
      const c = this.expCfg;
      c.preset = p;
      const today = new Date();
      const iso = (d) => d.toISOString().slice(0, 10);
      if (p === "all") { c.from = ""; c.to = ""; return; }
      if (p === "ytd") { c.from = `${today.getFullYear()}-01-01`; c.to = iso(today); return; }
      if (p === "12m") {
        const d = new Date(today); d.setFullYear(d.getFullYear() - 1);
        c.from = iso(d); c.to = iso(today); return;
      }
      if (p === "lastyear") {
        const y = today.getFullYear() - 1;
        c.from = `${y}-01-01`; c.to = `${y}-12-31`;
      }
    },
    expToggleSource(key) {
      const a = this.expCfg.sources;
      const i = a.indexOf(key);
      if (i >= 0) a.splice(i, 1); else a.push(key);
    },
    expToggleSystem(id) {
      const a = this.expCfg.systemIds;
      const i = a.indexOf(id);
      if (i >= 0) a.splice(i, 1); else a.push(id);
    },
    expSelectAll(on) {
      this.expCfg.systemIds = on
        ? this.systems.filter((s) => this.expCfg.includeInactive || s.aktiv).map((s) => s.id)
        : [];
    },
    expQuery() {
      const c = this.expCfg;
      const p = new URLSearchParams();
      if (c.from) p.set("from", c.from);
      if (c.to) p.set("to", c.to);
      // Nur einschraenken, wenn nicht ohnehin alles gewaehlt ist – kuerzere URL
      const all = this.systems.filter((s) => c.includeInactive || s.aktiv);
      if (c.systemIds.length && c.systemIds.length < all.length) {
        p.set("systems", c.systemIds.join(","));
      }
      if (c.includeInactive) p.set("include_inactive", "true");
      // Leere Auswahl = alle Quellen; dann bleibt der Parameter weg.
      if (c.sources.length && c.sources.length < this.expSourceOptions.length) {
        p.set("sources", c.sources.join(","));
      }
      if (c.useTheme) Object.entries(c.theme).forEach(([k, v]) => v && p.set(k, v));
      if (c.systemColors) p.set("system_colors", "true");
      if (!c.includeChart) p.set("include_chart", "false");
      if (!c.includeTable) p.set("include_table", "false");
      return p.toString() ? "?" + p.toString() : "";
    },
    expCount() { return this.expCfg ? this.expCfg.systemIds.length : 0; },
    /* Nur Quellen anbieten, die tatsächlich vorkommen – eine Auswahl, die
       nichts trifft, führt sonst zu einem leeren Bericht ohne erkennbaren Grund. */
    expSourceOptions() {
      return Object.entries(SOURCE_LABELS).map(([key, label]) => ({ key, label }));
    },
    /* Rohdaten-Export braucht nur Zeitraum und Auswahl - Farben und
       Diagrammoptionen gelten ausschliesslich fuer das PDF. */
    expDataQuery() {
      const c = this.expCfg;
      const p = new URLSearchParams();
      if (c.from) p.set("from", c.from);
      if (c.to) p.set("to", c.to);
      const all = this.systems.filter((s) => c.includeInactive || s.aktiv);
      if (c.systemIds.length && c.systemIds.length < all.length) {
        p.set("systems", c.systemIds.join(","));
      }
      if (c.includeInactive) p.set("include_inactive", "true");
      if (c.sources.length && c.sources.length < this.expSourceOptions.length) {
        p.set("sources", c.sources.join(","));
      }
      return p;
    },
    runExport() {
      const c = this.expCfg;
      if (!c.systemIds.length) { this.notify("Kein System ausgewählt", "err"); return; }
      const stamp = today();
      const fail = (e) => this.notify(e.message, "err");

      // URL zuerst bauen: expDataQuery()/expQuery() lesen this.expCfg, das gleich
      // auf null gesetzt wird, um den Dialog (und die Bericht-Markierung) zu schließen.
      let url, filename;
      if (c.format === "zip") {
        url = "api/export.zip"; filename = "zaehlwerk-export.zip";
      } else if (c.format === "csv") {
        const p = this.expDataQuery();
        p.set("dialect", c.dialect);
        url = `api/export/data.csv?${p}`; filename = `zaehlwerk-daten_${stamp}.csv`;
      } else if (c.format === "json") {
        const p = this.expDataQuery();
        if (!c.includeDerived) p.set("include_derived", "false");
        if (!c.includeMeta) p.set("include_meta", "false");
        url = `api/export/data.json?${p}`; filename = `zaehlwerk-daten_${stamp}.json`;
      } else {
        url = `api/report.pdf${this.expQuery()}`; filename = "zaehlwerk-gesamtbericht.pdf";
      }
      this.expCfg = null;
      fetchBlobDownload(url, filename).catch(fail);
    },
    openCombinedReport() {
      this.openExportConfig();
    },
    pickTheme(mode) { setTheme(mode); },
    pickPalette(key) { setPalette(key); },
    pickContrast(key) { setContrast(key); },

    /* ---------- Chart-Farben ---------- */
    chartColorValue(key) { return chartColor(key, "#000000"); },
    isChartColorCustom(key) { return !!this.chartPrefs[key]; },
    onChartColor(key, ev) { setChartColor(key, ev.target.value); },
    clearChartColor(key) { setChartColor(key, null); },
    resetChartColors() { resetChartColors(); this.notify("Chart-Farben zurückgesetzt", "ok"); },
    /* Warnt, wenn eine Farbe auf der Chart-Fläche zu schwach kontrastiert */
    colorWarning(hex) {
      const r = contrastToSurface(hex);
      return r !== null && r < 3 ? `Kontrast ${r.toFixed(1)}:1 – auf dieser Fläche schwer erkennbar` : null;
    },
    fabAction() {
      if (!this.canWrite || ["settings", "admin", "dashboard", "mobile-home"].includes(this.view)) return;
      const d = this.$refs.detail;
      if (this.view === "detail" && d) {
        // Kontextbezogen: der FAB legt an, was zum aktiven Tab passt –
        // im Zähler-Tab einen Zähler, im Tarife-Tab einen Tarif, sonst eine Ablesung.
        if (this.detailTab === "meters") d.openMeter(null);
        else if (this.detailTab === "tariffs") d.openTariff(null);
        else d.openReading();
        return;
      }
      this.newSystem();
    },
    async confirmDeleteSystem() {
      // Bestaetigung liefert bereits das 3-Sekunden-Halten des HoldButton -
      // kein zusaetzliches confirm(), das im HA-WebView ohnehin unterdrueckt
      // werden kann.
      const sys = this.sysForm;
      if (!sys || !sys.id) return;
      try {
        await api(`/api/systems/${sys.id}`, { method: "DELETE" });
        this.showSystem = false;
        this.notify("System gelöscht", "ok");
        this.view = "menu"; this.selected = null;
        await this.load();
      } catch (e) { this.notify(e.message, "err"); }
    },
    /* ---------- Admin-Tools: Anwendungsparameter ---------- */
    async loadSettings() {
      try {
        if (!this.isAdmin) return;
        const [s, i, x, b] = await Promise.all([
          api("/api/settings"), api("/api/system/info"), api("/api/external/status"),
          api("/api/backup"),
        ]);
        this.backupStatus = b;
        this.loadMqtt();
        if (this.isAdmin) this.loadUsers();
        this.appSettings = s;
        this.appSettingsDraft = { ...s };
        this.sysInfo = i;
        this.extStatus = x;
        this.settingsErrors = {};
      } catch (e) { this.notify("Einstellungen nicht ladbar: " + e.message, "err"); }
    },
    /* Clientseitige Vorpruefung – spiegelt die Grenzen der Pydantic-Schemas.
       Der Server prueft unabhaengig davon nochmal; das hier spart nur den Roundtrip. */
    validateSettings() {
      const d = this.appSettingsDraft || {};
      const err = {};
      const num = (v) => (v === "" || v === null ? NaN : Number(v));
      const h = num(d.notify_interval_hours);
      if (!Number.isInteger(h) || h < 1 || h > 168) err.notify_interval_hours = "Ganzzahl zwischen 1 und 168 Stunden";
      const iv = num(d.default_interval_days);
      if (!Number.isInteger(iv) || iv < 0 || iv > 3650) err.default_interval_days = "Ganzzahl zwischen 0 und 3650 Tagen";
      const sg = num(d.outlier_sigma);
      if (!(sg >= 1 && sg <= 5)) err.outlier_sigma = "Wert zwischen 1,0 und 5,0";
      if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(String(d.backup_time || ""))) {
        err.backup_time = "Uhrzeit im Format HH:MM";
      }
      const bk = num(d.backup_keep_days);
      if (!Number.isInteger(bk) || bk < 1 || bk > 365) err.backup_keep_days = "1 bis 365 Tage";
      const tk = num(d.telemetry_keep_days);
      if (!Number.isInteger(tk) || tk < 0 || tk > 36500) err.telemetry_keep_days = "0 (unbegrenzt) bis 36500 Tage";
      const wd = num(d.mqtt_watchdog_hours);
      if (!Number.isInteger(wd) || wd < 1 || wd > 336) err.mqtt_watchdog_hours = "1 bis 336 Stunden (14 Tage)";
      this.settingsErrors = err;
      return Object.keys(err).length === 0;
    },
    settingsChangedKeys() {
      if (!this.appSettings || !this.appSettingsDraft) return [];
      return Object.keys(this.appSettings).filter(
        (k) => String(this.appSettings[k]) !== String(this.appSettingsDraft[k]));
    },
    settingsChangeCount() {
      // Das Passwort steckt nicht in appSettings – es wird nie zurückgegeben –
      // zählt aber als Änderung, sobald etwas eingetippt wurde.
      return this.settingsChangedKeys().length + (this.mqttPassword ? 1 : 0);
    },
    settingsDirty() { return this.settingsChangeCount() > 0; },
    settingsErrorCount() { return Object.keys(this.settingsErrors || {}).length; },
    async saveSettings() {
      if (!this.validateSettings()) { this.notify("Bitte Eingaben prüfen", "err"); return; }
      this.settingsSaving = true;
      const d = this.appSettingsDraft;
      try {
        const saved = await api("/api/settings", {
          method: "PUT",
          body: JSON.stringify({
            offline_mode: !!d.offline_mode,
            notify_enabled: !!d.notify_enabled,
            notify_interval_hours: Number(d.notify_interval_hours),
            default_interval_days: Number(d.default_interval_days),
            outlier_sigma: Number(d.outlier_sigma),
            backup_enabled: !!d.backup_enabled,
            backup_time: d.backup_time,
            backup_keep_days: Number(d.backup_keep_days),
            telemetry_keep_days: Number(d.telemetry_keep_days || 0),
            mqtt_enabled: !!d.mqtt_enabled,
            mqtt_use_supervisor: !!d.mqtt_use_supervisor,
            mqtt_host: d.mqtt_host || "",
            mqtt_port: Number(d.mqtt_port || 1883),
            mqtt_username: d.mqtt_username || "",
            mqtt_base_topic: d.mqtt_base_topic || "tele",
            mqtt_tasmota_discovery: !!d.mqtt_tasmota_discovery,
            mqtt_interval: d.mqtt_interval || "daily",
            mqtt_watchdog_enabled: !!d.mqtt_watchdog_enabled,
            mqtt_watchdog_hours: Number(d.mqtt_watchdog_hours || 48),
            // Leeres Feld = unveraendert lassen, nicht loeschen
            ...(this.mqttPassword ? { mqtt_password: this.mqttPassword } : {}),
          }),
        });
        this.appSettings = saved;
        this.appSettingsDraft = { ...saved };
        this.mqttPassword = "";
        this.loadMqtt();
        this.notify(saved.offline_mode
          ? "Gespeichert – Internetzugriff gesperrt"
          : "Gespeichert – Internetzugriff freigegeben", "ok");
        try { this.extStatus = await api("/api/external/status"); } catch (_) {}
      } catch (e) {
        // 422 vom Server: Feldfehler sichtbar machen statt nur zu toasten
        this.notify("Nicht gespeichert: " + e.message, "err");
      } finally { this.settingsSaving = false; }
    },
    /* ---------- Dashboard ---------- */
    async loadDashboard() {
      this.dashLoading = true;
      try {
        // Layout zuerst: ein benutzerdefinierter Zeitraum kann weiter als die
        // sonst üblichen 24 Monate zurückreichen, das Fenster für den
        // Daten-Aufruf richtet sich danach statt fest verdrahtet zu sein.
        const layout = await api("/api/user/dashboard");
        this.dashTiles = layout.tiles;
        if (layout.recovered) this.notify("Layout war beschädigt – Vorgabe geladen", "err");
        const data = await api(`/api/dashboard/data?months=${this.dashMonthsNeeded()}`);
        this.dashData = data.systems;
        this.dashRecent = data.recent || [];
        this.dashDirty = false;
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.dashLoading = false; }
    },
    dashMonthsNeeded() {
      let months = 24;
      const now = new Date();
      for (const t of this.dashTiles) {
        if (t.timeframe !== "custom" || !t.range_from) continue;
        const from = new Date(t.range_from);
        const diff = (now.getFullYear() - from.getFullYear()) * 12 + (now.getMonth() - from.getMonth()) + 1;
        if (diff > months) months = Math.min(diff, 240); // Deckel: 20 Jahre
      }
      return months;
    },
    trendOf(s) {
      const pts = sliceSeries(s.series, "90d");
      if (pts.length < 4) return { dir: "flat", text: "zu wenige Werte" };
      const half = Math.floor(pts.length / 2);
      const avg = (a) => a.reduce((x, p) => x + p.v, 0) / a.length;
      const prev = avg(pts.slice(0, half)), curr = avg(pts.slice(half));
      if (!prev) return { dir: "flat", text: "kein Vergleich möglich" };
      const pct = (curr - prev) / prev * 100;
      const dir = pct > 5 ? "up" : pct < -5 ? "down" : "flat";
      return { dir, pct,
               text: dir === "flat" ? "stabil gegenüber Vorperiode"
                   : `${Math.abs(pct).toFixed(0)} % ${dir === "up" ? "mehr" : "weniger"} als zuvor` };
    },
    dashSystem(tile) {
      const id = (tile.system_ids && tile.system_ids[0]) || tile.system_id;
      return this.dashData.find((s) => s.id === id) || null;
    },
    dashTitle(tile) {
      if (tile.title) return tile.title;
      const ids = (tile.system_ids && tile.system_ids.length)
        ? tile.system_ids : (tile.system_id ? [tile.system_id] : []);
      if (ids.length > 1) return `${WIDGET_LABEL[tile.type]} · ${ids.length} Systeme`;
      const s = this.dashSystem(tile);
      return s ? `${typeIcon(s.typ)} ${s.name}` : WIDGET_LABEL[tile.type] || tile.type;
    },
    toggleDashEdit() {
      if (this.dashEdit && this.dashDirty) { this.saveDashboard(); return; }
      this.dashEdit = !this.dashEdit;
    },
    addTile(type) {
      const def = WIDGET_TYPES.find((w) => w.key === type);
      // Neue Kachel unten anhängen: freie Lücken im Raster zu suchen wäre
      // aufwendig und das Ergebnis für den Nutzer schwer vorhersehbar.
      const maxY = this.dashTiles.reduce((m, t) => Math.max(m, t.y + t.h), 0);
      const first = def.needsSystem ? (this.dashData[0] || {}).id || null : null;
      this.dashTiles.push({
        id: "w_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        type, x: 0, y: maxY, w: def.w, h: def.h,
        system_id: first, system_ids: first ? [first] : [],
        timeframe: "12m", title: null,
      });
      this.dashDirty = true;
    },
    removeTile(tile) {
      this.dashTiles = this.dashTiles.filter((t) => t.id !== tile.id);
      this.dashDirty = true;
    },
    /* ---------- Kachel einrichten ---------- */
    tileNeedsTimeframe(t) {
      return t && ["line_chart", "trend", "cost_forecast"].includes(t.type);
    },
    tfLabel(t) {
      const key = (t && t.timeframe) || "12m";
      if (key === "custom" && t && t.range_from && t.range_to) {
        return `${fmtDate(t.range_from)} – ${fmtDate(t.range_to)}`;
      }
      const tf = TIMEFRAMES.find((x) => x.key === key);
      return tf ? tf.label : key;
    },
    /* Reihen einer Kachel: `system_ids` hat Vorrang, `system_id` bleibt als
       Rückfall für Layouts aus 3.5.0 bestehen. */
    tileSeries(t) {
      const ids = (t.system_ids && t.system_ids.length)
        ? t.system_ids : (t.system_id ? [t.system_id] : []);
      return ids.map((id) => {
        const s = this.dashData.find((x) => x.id === id);
        if (!s) return null;
        return { ...s, points: sliceSeries(s.series, t.timeframe || "12m", t.range_from, t.range_to) };
      }).filter(Boolean);
    },
    openTileConfig(tile) {
      // Arbeitskopie: Abbrechen soll die Kachel unverändert lassen.
      this.tileCfg = {
        ...tile,
        timeframe: tile.timeframe || "12m",
        range_from: tile.range_from || "",
        range_to: tile.range_to || "",
        system_ids: (tile.system_ids && tile.system_ids.length)
          ? [...tile.system_ids] : (tile.system_id ? [tile.system_id] : []),
      };
    },
    /* Benutzerdefinierter Zeitraum braucht Start und Ende, Start darf nicht
       nach dem Ende liegen – sonst weist der Server die ganze Anordnung ab. */
    tileRangeValid(t) {
      if (!t || t.timeframe !== "custom") return true;
      return !!(t.range_from && t.range_to && t.range_from <= t.range_to);
    },
    setTileType(key) {
      const def = WIDGET_TYPES.find((w) => w.key === key);
      this.tileCfg.type = key;
      // Beim Wechsel auf einen einwertigen Typ die Mehrfachauswahl kürzen,
      // sonst bliebe eine unsichtbare Auswahl bestehen.
      if (!def.multi && this.tileCfg.system_ids.length > 1) {
        this.tileCfg.system_ids = this.tileCfg.system_ids.slice(0, 1);
      }
      if (!def.needsSystem) this.tileCfg.system_ids = [];
    },
    toggleTileSystem(id) {
      const def = this.tileTypeDef;
      const a = this.tileCfg.system_ids;
      if (!def.multi) { this.tileCfg.system_ids = a.includes(id) ? [] : [id]; return; }
      const i = a.indexOf(id);
      if (i >= 0) a.splice(i, 1); else a.push(id);
    },
    applyTileConfig() {
      if (!this.tileRangeValid(this.tileCfg)) return;
      const t = this.dashTiles.find((x) => x.id === this.tileCfg.id);
      if (t) {
        const custom = this.tileCfg.timeframe === "custom";
        Object.assign(t, {
          type: this.tileCfg.type,
          w: Math.min(4 - t.x, Math.max(1, this.tileCfg.w)),
          h: Math.min(4, Math.max(1, this.tileCfg.h)),
          timeframe: this.tileCfg.timeframe,
          range_from: custom ? this.tileCfg.range_from : null,
          range_to: custom ? this.tileCfg.range_to : null,
          system_ids: [...this.tileCfg.system_ids],
          // Erstes System zusätzlich in system_id: ältere Fassungen und der
          // Vorgabe-Aufbau lesen weiterhin dieses Feld.
          system_id: this.tileCfg.system_ids[0] || null,
          title: (this.tileCfg.title || "").trim() || null,
        });
        this.reflow();
        this.dashDirty = true;
      }
      this.tileCfg = null;
    },
    removeTileFromConfig() {
      const id = this.tileCfg.id;
      this.tileCfg = null;
      this.removeTile({ id });
    },

    onTileDragStart(tile, ev) {
      if (!this.dashEdit) return;
      this.dashDragId = tile.id;
      ev.dataTransfer.effectAllowed = "move";
      // Firefox startet den Vorgang nur, wenn Daten gesetzt sind.
      ev.dataTransfer.setData("text/plain", tile.id);
    },
    onTileDrop(target) {
      if (!this.dashDragId || this.dashDragId === target.id) return;
      const from = this.dashTiles.findIndex((t) => t.id === this.dashDragId);
      const to = this.dashTiles.findIndex((t) => t.id === target.id);
      if (from < 0 || to < 0) return;
      // Umsortieren statt Koordinaten tauschen: die Kacheln fließen im Raster,
      // dadurch entstehen keine Löcher und keine Überlappungen.
      const [moved] = this.dashTiles.splice(from, 1);
      this.dashTiles.splice(to, 0, moved);
      this.reflow();
      this.dashDragId = null;
      this.dashDirty = true;
    },
    /* Koordinaten aus der Reihenfolge neu berechnen. Der Server prüft x + w
       gegen die Spaltenzahl; ohne diesen Schritt wären gespeicherte Layouts
       nach dem Verschieben ungültig. */
    reflow() {
      let x = 0, y = 0, rowH = 1;
      for (const t of this.dashTiles) {
        if (x + t.w > 4) { x = 0; y += rowH; rowH = 1; }
        t.x = x; t.y = y;
        x += t.w;
        rowH = Math.max(rowH, t.h);
      }
    },
    async saveDashboard() {
      this.reflow();
      try {
        const res = await api("/api/user/dashboard", {
          method: "PUT",
          body: JSON.stringify({ tiles: this.dashTiles.map((t) => ({
            id: t.id, type: t.type, x: t.x, y: t.y, w: t.w, h: t.h,
            system_id: t.system_id || null, system_ids: t.system_ids || [],
            timeframe: t.timeframe || "12m", title: t.title || null,
            range_from: t.timeframe === "custom" ? (t.range_from || null) : null,
            range_to: t.timeframe === "custom" ? (t.range_to || null) : null,
          })) }),
        });
        this.dashTiles = res.tiles;
        this.dashDirty = false;
        this.dashEdit = false;
        this.notify("Dashboard gespeichert", "ok");
      } catch (e) { this.notify(e.message, "err"); }
    },
    async resetDashboard() {
      try {
        await api("/api/user/dashboard", { method: "DELETE" });
        this.dashEdit = false;
        await this.loadDashboard();
        this.notify("Auf Vorgabe zurückgesetzt", "ok");
      } catch (e) { this.notify(e.message, "err"); }
    },

    async loadUsers() {
      try { this.users = await api("/api/auth/users"); }
      catch (_) { this.users = []; }
    },
    async setUserRole(user, role) {
      if (role === user.role) return;
      try {
        const updated = await api(`/api/auth/users/${user.id}`, {
          method: "PATCH", body: JSON.stringify({ role }),
        });
        this.notify(`${updated.display_name}: ${updated.role}`, "ok");
        await this.loadUsers();
        // Eigene Rolle geändert? Dann Rechte neu holen, sonst zeigt die
        // Oberfläche weiter, was der Server bereits ablehnt.
        if (this.currentUser && user.id === this.currentUser.id) await this.checkAuth();
      } catch (e) { this.notify(e.message, "err"); await this.loadUsers(); }
    },
    async loadMqtt() {
      try { this.mqttStatus = await api("/api/mqtt/status"); }
      catch (_) { this.mqttStatus = null; }
    },
    async assignDevice(d) {
      const systemId = this.assignTarget[d.device];
      if (!systemId) return;
      try {
        const r = await api("/api/mqtt/assign", {
          method: "POST",
          body: JSON.stringify({ system_id: systemId, topic: d.topic }),
        });
        this.notify(`${r.topic} → ${r.system}`, "ok");
        this.assignTarget[d.device] = null;
        await this.load();          // zusatzfelder neu laden
        await this.loadMqtt();
      } catch (e) { this.notify(e.message, "err"); }
    },
    async forgetDevices() {
      try { await api("/api/mqtt/devices/forget", { method: "POST" }); await this.loadMqtt(); }
      catch (e) { this.notify(e.message, "err"); }
    },
    async ignoreDevice(d) {
      try {
        await api("/api/mqtt/devices/ignore", { method: "POST", body: JSON.stringify({ device: d.device }) });
        this.notify(`${d.device} wird nicht mehr angezeigt`, "ok");
        await this.loadMqtt();
      } catch (e) { this.notify(e.message, "err"); }
    },
    async unignoreDevice(device) {
      try {
        await api("/api/mqtt/devices/unignore", { method: "POST", body: JSON.stringify({ device }) });
        await this.loadMqtt();
      } catch (e) { this.notify(e.message, "err"); }
    },
    async restartMqtt() {
      try {
        await api("/api/mqtt/restart", { method: "POST" });
        await this.loadMqtt();
        this.notify(this.mqttStatus && this.mqttStatus.connected
          ? "MQTT verbunden" : "Nicht verbunden – siehe Status", 
          this.mqttStatus && this.mqttStatus.connected ? "ok" : "err");
      } catch (e) { this.notify(e.message, "err"); }
    },
    async runBackup() {
      this.backupBusy = true;
      try {
        const r = await api("/api/backup/run", { method: "POST" });
        this.backupStatus = await api("/api/backup");
        const pruned = r.pruned && r.pruned.length ? `, ${r.pruned.length} alte entfernt` : "";
        this.notify(`Gesichert: ${this.fmtBytes(r.size_bytes)} in ${r.duration_ms} ms${pruned}`, "ok");
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.backupBusy = false; }
    },
    async clearExtCache() {
      try {
        const r = await api("/api/external/cache/clear", { method: "POST" });
        this.extStatus = await api("/api/external/status");
        this.notify(`Zwischenspeicher geleert (${r.cleared})`, "ok");
      } catch (e) { this.notify(e.message, "err"); }
    },
    revertSettings() { this.appSettingsDraft = { ...this.appSettings }; this.settingsErrors = {}; },
    fmtBytes(n) {
      if (!n) return "0 B";
      const u = ["B", "KB", "MB", "GB"];
      const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), u.length - 1);
      return (n / Math.pow(1024, i)).toFixed(i ? 1 : 0) + " " + u[i];
    },
    dueInfo(id) {
      const l = this.latest[id];
      if (!l || l.overdue_days === undefined || l.overdue_days === null) return null;
      const od = l.overdue_days;
      const span = (n) => (n >= 60 ? `${Math.round(n / 30)} Mon.` : `${n} T`);
      if (od > 0) return { level: "over", text: `Ablesung überfällig · seit ${span(od)}` };
      if (od >= -30) return { level: "soon", text: `Ablesung bald fällig · in ${-od} T` };
      return null;
    },

    /* System anlegen / bearbeiten */
    newSystem() {
      this.sysForm = { name: "", typ: "Strom", einheit: "kWh", farbe: PALETTE[0], icon: "⚡", zusatzfelder: {}, aktiv: true };
      this.showSystem = true;
    },
    editSystem(s) {
      this.sysForm = { id: s.id, name: s.name, typ: s.typ, einheit: s.einheit, farbe: s.farbe, icon: s.icon, zusatzfelder: { ...s.zusatzfelder }, aktiv: s.aktiv };
      this.showSystem = true;
    },
    onTypeChange() {
      const t = SYSTEM_TYPES.find((x) => x.v === this.sysForm.typ);
      if (t) { if (t.unit) this.sysForm.einheit = t.unit; this.sysForm.icon = t.icon; }
    },
    async saveSystem() {
      if (!this.sysForm.name.trim()) { this.notify("Name fehlt", "err"); return; }
      this.busy = true;
      const body = {
        name: this.sysForm.name, typ: this.sysForm.typ, einheit: this.sysForm.einheit,
        farbe: this.sysForm.farbe, icon: this.sysForm.icon, zusatzfelder: this.sysForm.zusatzfelder,
      };
      try {
        if (this.sysForm.id) {
          await api(`/api/systems/${this.sysForm.id}`, { method: "PATCH", body: JSON.stringify({ ...body, aktiv: this.sysForm.aktiv }) });
          this.notify("System aktualisiert", "ok");
        } else {
          await api("/api/systems", { method: "POST", body: JSON.stringify(body) });
          this.notify("System angelegt", "ok");
        }
        this.showSystem = false;
        await this.load();
      } catch (e) { this.notify(e.message, "err"); }
      finally { this.busy = false; }
    },
  },
  template: `
  <div class="topbar">
    <div class="topbar-inner">
      <button class="iconbtn nav-toggle" @click="toggleNav"
              :aria-expanded="String(navExpanded || navDrawer)" aria-controls="zw-nav"
              aria-label="Navigation ein-/ausklappen" title="Navigation ein-/ausklappen"
              v-html="navMenuIcon"></button>
      <button type="button" class="brand" @click="goHome"
              title="Zur Startseite" aria-label="Zur Startseite">
        <span class="logo"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 19a9 9 0 1 1 14 0"/><path d="M12 5v2"/><path d="M5.6 8.5l1.5 1.2"/><path d="M18.4 8.5l-1.5 1.2"/><path d="M12 15l3.5-4.5"/><circle cx="12" cy="16" r="1.6" fill="currentColor" stroke="none"/></svg></span>
        <h1>{{ view==='mobile-home' ? 'Zählwerk' : view==='dashboard' ? 'Dashboard' : view==='admin' ? 'Admin-Tools' : view==='settings' ? 'Einstellungen' : (view==='detail' && selectedSystem ? selectedSystem.name : 'Zählwerk') }}</h1>
      </button>
      <div class="spacer"></div>
    </div>
  </div>

  <!-- Sidebar: Navigation Rail (Desktop) / modaler Drawer (Mobile) -->
  <nav id="zw-nav" class="nav-rail" :class="{ expanded: navExpanded, drawer: navDrawer }" aria-label="Hauptnavigation">
    <button class="fab rail-fab" v-if="showFab" @click="fabAction" :title="'Neu: ' + fabLabel">
      <span class="fab-plus">＋</span><span class="fab-text">{{ fabLabel }}</span>
    </button>
    <template v-for="it in visibleNavItems" :key="it.key">
      <div class="nav-row">
        <button class="nav-item"
                :class="{ active: activeNav===it.key, disabled: it.disabled }"
                :disabled="it.disabled"
                :title="it.disabled ? it.label + ' (noch nicht verfügbar)' : it.label"
                @click="goNav(it)">
          <span class="nav-pill" v-html="it.icon"></span>
          <span class="nav-label">{{ it.label }}</span>
          <span v-if="it.badge" class="nav-badge">{{ it.badge }}</span>
        </button>
        <!-- Getrennte Schaltfläche: der Pfeil klappt auf, der Eintrag navigiert.
             M3 trennt diese beiden Aktionen bewusst - ein Klick auf den Eintrag
             darf nie nur ein Menü öffnen, wenn er auch ein Ziel hat. -->
        <button v-if="navExpanded && subItemsFor(it).length"
                class="nav-expander" :class="{ open: navSubOpen }"
                :aria-expanded="String(navSubOpen)" :aria-controls="'zw-sub-' + it.key"
                :title="navSubOpen ? 'Systeme einklappen' : 'Systeme aufklappen'"
                @click.stop="toggleNavSub(it.key)" v-html="chevronIcon"></button>
      </div>

      <div v-if="navExpanded && navSubOpen[it.key] && subItemsFor(it).length" class="nav-sub"
           :id="'zw-sub-' + it.key" role="group" :aria-label="it.label + ' – Systeme'">
        <button v-for="s in subItemsFor(it)" :key="s.id || s.key"
                class="nav-subitem" :class="{ active: subItemActive(s) }"
                :title="s.name || s.label" @click="goSubItem(s)">
          <span v-if="s.icon" class="ns-icon" v-html="s.icon"></span>
          <span v-else class="dot" :style="{background: s.farbe}"></span>
          <span class="ns-label">{{ s.name || s.label }}</span>
          <span class="ns-unit" v-if="s.einheit">{{ s.einheit }}</span>
        </button>
      </div>
    </template>
    <div class="nav-foot">v{{ appVersion }}</div>
  </nav>
  <div class="nav-scrim" v-if="navDrawer" @click="closeDrawer"></div>

  <!-- Bottom Navigation (Mobile) -->
  <nav class="nav-bottom" aria-label="Schnellzugriff">
    <button v-for="it in bottomNavItems" :key="it.key"
            class="nav-item" :class="{ active: activeNav===it.key, 'has-sub': it.expandable && navSubItems.length }"
            :aria-haspopup="it.expandable && navSubItems.length ? 'dialog' : null"
            :aria-expanded="it.expandable ? String(showSysSheet) : null"
            @click="goNavMobile(it)">
      <span class="nav-pill" v-html="it.icon"></span>
      <span>{{ it.short || it.label }}</span>
      <!-- Hinweis, dass hinter dem aktiven Eintrag mehr steckt -->
      <span v-if="it.expandable && navSubItems.length && activeNav===it.key"
            class="nav-caret" v-html="chevronIcon" aria-hidden="true"></span>
    </button>
  </nav>

  <!-- Modal Bottom Sheet: Systemauswahl (Mobile) -->
  <div class="sheet-scrim" v-if="showSysSheet" @click="showSysSheet=false"></div>
  <div class="sys-sheet" v-if="showSysSheet" role="dialog" aria-modal="true"
       aria-label="System wählen">
    <div class="sheet-handle" @click="showSysSheet=false"></div>
    <div class="sheet-head">
      <h3>System wählen</h3>
      <span class="sheet-count">{{ navSubItems.length }}</span>
    </div>
    <div class="sheet-list">
      <button class="sheet-item" :class="{ active: view==='menu' }" @click="sheetGoOverview">
        <span class="si-icon" v-html="navHomeIcon"></span>
        <span class="si-label">Übersicht</span>
        <span class="si-meta">alle Systeme</span>
      </button>
      <div class="sheet-sep"></div>
      <button v-for="s in navSubItems" :key="s.id" class="sheet-item"
              :class="{ active: view==='detail' && selected===s.id }" @click="sheetGoSystem(s)">
        <span class="si-dot" :style="{background: s.farbe}"></span>
        <span class="si-label">{{ typeIcon(s.typ) }} {{ s.name }}</span>
        <span class="si-meta">{{ s.einheit }}</span>
      </button>
    </div>
    <div class="sheet-foot">
      <button class="btn" @click="showSysSheet=false">Schließen</button>
      <button class="btn btn-primary" v-if="canWrite" @click="sheetNewSystem">＋ System anlegen</button>
    </div>
  </div>

  <!-- FAB (Mobile) – nur auf Ansichten, wo er auch etwas anlegt -->
  <div class="fab-screen" v-if="showFab"><button class="fab" @click="fabAction" :title="'Neu: ' + fabLabel">＋</button></div>

  <div class="wrap">
    <div v-if="loading" class="center-load"><span class="spin"></span></div>

    <!-- MENÜ -->
    <template v-else-if="view==='menu'">
      <div class="eyebrow">
        Systeme
        <label class="check" style="font-family:var(--sans);text-transform:none;letter-spacing:0"><input type="checkbox" v-model="showArchived" /> archivierte zeigen</label>
      </div>

      <div v-if="!visibleSystems.length" class="empty">
        <h3>Noch kein System angelegt</h3>
        <p>Lege Strom, Gas, Wasser, PV o. Ä. an, um Ablesungen zu erfassen.</p>
        <button class="btn btn-primary" @click="newSystem">Erstes System anlegen</button>
      </div>

      <div class="tiles" v-else>
        <div v-for="s in visibleSystems" :key="s.id" class="tile" :class="{archived: !s.aktiv, 'due-over': dueInfo(s.id) && dueInfo(s.id).level==='over', 'due-soon': dueInfo(s.id) && dueInfo(s.id).level==='soon'}" @click="open(s)">
          <span class="swatch" :style="{background: s.farbe}"></span>
          <div class="t-type">{{ typeIcon(s.typ) }} {{ s.typ }}</div>
          <div class="t-name">{{ s.name }}</div>
          <div class="readout" v-if="latest[s.id]">
            <span class="val num">{{ fmt(latest[s.id].value, 1) }}</span>
            <span class="unit">{{ s.einheit }}</span>
          </div>
          <div class="t-meta">
            <template v-if="latest[s.id]">Stand: {{ fmtDate(latest[s.id].datum) }}</template>
            <template v-else>Einheit: {{ s.einheit }} · noch keine Werte</template>
            <span v-if="!s.aktiv"> · archiviert</span>
          </div>
          <div v-if="dueInfo(s.id)" class="due-badge" :class="dueInfo(s.id).level">⚠ {{ dueInfo(s.id).text }}</div>
        </div>
      </div>
    </template>

    <!-- MOBILE STARTSEITE -->
    <template v-else-if="view==='mobile-home'">
      <div v-if="dashLoading" class="center-load"><span class="spin"></span></div>
      <template v-else>
        <div class="mh-greet">
          <div class="mh-hello">{{ greeting }}<span v-if="currentUser">, {{ currentUser.display_name.split(' ')[0] }}</span></div>
          <div class="mh-date">{{ todayLong }}</div>
        </div>

        <!-- Je Zähler eine Karte: Status oben (antippen öffnet die Details),
             darunter die Schnellerfassung mit großen Touch-Zielen. -->
        <div class="mh-cards">
          <div v-for="s in mobileMeters" :key="s.id" class="card mh-card">
            <button class="mh-card-status" @click="openSystemById(s.id)">
              <div class="mh-head">
                <span class="dot" :style="{background: s.farbe}"></span>
                <span class="mh-name">{{ typeIcon(s.typ) }} {{ s.name }}</span>
                <!-- Ampel über Form UND Farbe: allein farbig wäre sie im
                     Hochkontrast-Theme und bei Farbfehlsichtigkeit wertlos. -->
                <span class="mh-trend" :class="'tr-' + s.trend.dir" :title="s.trend.text">
                  {{ s.trend.dir === 'up' ? '▲' : s.trend.dir === 'down' ? '▼' : '▬' }}
                </span>
              </div>
              <div class="mh-val num">{{ s.latest === null ? '–' : fmt(s.latest, 1) }}<span class="mh-unit">{{ s.einheit }}</span></div>
              <div class="mh-sub">{{ s.trend.text }}</div>
            </button>
            <div class="mh-quick" v-if="canWrite">
              <button class="btn btn-primary mh-quick-add" @click="mobileQuickRead(s.id, false)">
                ＋ Wert erfassen
              </button>
              <button class="btn mh-quick-cam" @click="mobileQuickRead(s.id, true)"
                      :aria-label="'Zählerstand für ' + s.name + ' fotografieren'">
                📷
              </button>
            </div>
          </div>
          <div class="hint" v-if="!mobileMeters.length">Noch keine Systeme angelegt.</div>
        </div>

        <!-- Unten: letzte Erfassungen -->
        <div class="card mh-log" v-if="dashRecent.length">
          <div class="hw-head">Zuletzt erfasst</div>
          <button v-for="r in dashRecent.slice(0,3)" :key="r.id" class="mh-log-row"
                  @click="openSystemById(r.system_id)">
            <span class="dot" :style="{background: r.farbe}"></span>
            <span class="ml-sys">{{ r.system }}</span>
            <span class="ml-val num">{{ fmt(r.value, 1) }} {{ r.einheit }}</span>
            <span class="ml-date">{{ fmtDate(r.datum) }}</span>
            <span v-if="r.source !== 'manual'" class="chip" :class="'chip-' + r.source">{{ sourceLabel(r.source) }}</span>
          </button>
        </div>

        <div class="mh-foot">
          <button class="crumb" @click="openDashboard">Vollständiges Dashboard →</button>
        </div>
      </template>
    </template>

    <!-- DASHBOARD -->
    <template v-else-if="view==='dashboard'">
      <div class="dash-head">
        <div class="eyebrow">Dashboard</div>
        <div class="dash-actions">
          <button class="btn btn-sm" v-if="dashEdit" @click="resetDashboard">↺ Vorgabe</button>
          <button class="btn btn-sm" :class="{'btn-primary': dashEdit && dashDirty}"
                  @click="toggleDashEdit">
            {{ dashEdit ? (dashDirty ? '✓ Speichern' : '✕ Fertig') : '✎ Anpassen' }}
          </button>
        </div>
      </div>

      <div v-if="dashLoading" class="center-load"><span class="spin"></span></div>

      <template v-else>
        <div class="dash-palette" v-if="dashEdit">
          <span class="hint">Kachel hinzufügen:</span>
          <button v-for="w in widgetTypes" :key="w.key" class="crumb" @click="addTile(w.key)">
            ＋ {{ w.label }}
          </button>
          <span class="hint dash-hint">Kacheln lassen sich per Ziehen umsortieren.</span>
        </div>

        <div class="dash-grid" :class="{ editing: dashEdit }">
          <div v-for="t in dashTiles" :key="t.id"
               class="card wg" :class="{ 'wg-edit': dashEdit }"
               :style="{ gridColumn: 'span ' + t.w, gridRow: 'span ' + t.h }"
               :draggable="dashEdit"
               @dragstart="onTileDragStart(t, $event)"
               @dragover.prevent
               @drop.prevent="onTileDrop(t)"
               @click="dashEdit && openTileConfig(t)">
            <div class="wg-head">
              <span class="wg-title">{{ dashTitle(t) }}</span>
              <span class="wg-type" v-if="dashEdit">{{ widgetTypes.find(w => w.key === t.type).label }}</span>
              <button v-if="dashEdit" class="iconbtn wg-del" @click="removeTile(t)" title="Entfernen">✕</button>
            </div>

            <widget-latest-reading v-if="t.type==='latest_reading'" :data="dashSystem(t)" />
            <widget-line-chart     v-else-if="t.type==='line_chart'"  :series="tileSeries(t)" />
            <widget-pie-chart      v-else-if="t.type==='pie_chart'"   :systems="dashData" />
            <widget-cost-summary   v-else-if="t.type==='cost_summary'" :systems="dashData" />
            <widget-trend          v-else-if="t.type==='trend'"        :data="dashSystem(t)" :timeframe="t.timeframe" :range-from="t.range_from" :range-to="t.range_to" />
            <widget-cost-forecast  v-else-if="t.type==='cost_forecast'" :data="dashSystem(t)" :timeframe="t.timeframe" :range-from="t.range_from" :range-to="t.range_to" />

            <div class="wg-tools" v-if="dashEdit">
              <button class="btn btn-sm wg-cfg" @click.stop="openTileConfig(t)">⚙ Einrichten</button>
              <span class="wg-meta">{{ t.w }}×{{ t.h }}<span v-if="tileNeedsTimeframe(t)"> · {{ tfLabel(t) }}</span></span>
            </div>
          </div>
        </div>

        <div class="empty" v-if="!dashTiles.length">
          <h3>Dashboard ist leer</h3>
          <p>Schalte auf „Anpassen" und füge Kacheln hinzu.</p>
        </div>
      </template>
    </template>

    <!-- MODAL: Kachel einrichten -->
    <div class="overlay" v-if="tileCfg" @click.self="tileCfg = null">
      <div class="modal">
        <div class="modal-head"><h3>Kachel einrichten</h3></div>
        <div class="modal-body">
          <div class="field">
            <label>Art</label>
            <div class="seg exp-seg tile-types">
              <button v-for="w in widgetTypes" :key="w.key"
                      :class="{active: tileCfg.type === w.key}" @click="setTileType(w.key)">
                {{ w.label }}
              </button>
            </div>
          </div>

          <div class="field">
            <label>Größe</label>
            <div class="tile-size">
              <div class="ts-grid">
                <button v-for="c in [1,2,3,4]" :key="'w'+c" class="crumb"
                        :class="{sel: tileCfg.w === c}" :disabled="tileCfg.x + c > 4"
                        @click="tileCfg.w = c">{{ c }}</button>
                <span class="hint">Spalten</span>
              </div>
              <div class="ts-grid">
                <button v-for="c in [1,2,3,4]" :key="'h'+c" class="crumb"
                        :class="{sel: tileCfg.h === c}" @click="tileCfg.h = c">{{ c }}</button>
                <span class="hint">Zeilen</span>
              </div>
            </div>
            <div class="hint">Auf Mobilgeräten wird jede Kachel einspaltig dargestellt.</div>
          </div>

          <div class="field" v-if="tileTypeDef.needsSystem">
            <label>{{ tileTypeDef.multi ? 'Systeme (mehrere möglich)' : 'System' }}</label>
            <div class="tile-systems">
              <label v-for="s in dashData" :key="s.id" class="check tile-sys"
                     :class="{sel: tileCfg.system_ids.includes(s.id)}">
                <input type="checkbox" :checked="tileCfg.system_ids.includes(s.id)"
                       @change="toggleTileSystem(s.id)" />
                <span class="dot" :style="{background: s.farbe}"></span>
                <span>{{ s.name }}</span>
              </label>
            </div>
            <div class="hint" v-if="tileTypeDef.multi">
              Mehrere Systeme werden übereinandergelegt. Unterschiedliche Einheiten
              bekommen eine eigene Achse – dargestellt werden höchstens zwei.
            </div>
          </div>

          <div class="field" v-if="tileNeedsTimeframe(tileCfg)">
            <label>Zeitraum</label>
            <div class="seg exp-seg">
              <button v-for="tf in timeframes" :key="tf.key"
                      :class="{active: tileCfg.timeframe === tf.key}"
                      @click="tileCfg.timeframe = tf.key">{{ tf.label }}</button>
            </div>
            <div class="field-row exp-dates" v-if="tileCfg.timeframe === 'custom'">
              <div class="field"><label>Von</label>
                <input class="input" type="date" v-model="tileCfg.range_from" :max="tileCfg.range_to || undefined" /></div>
              <div class="field"><label>Bis</label>
                <input class="input" type="date" v-model="tileCfg.range_to" :min="tileCfg.range_from || undefined" /></div>
            </div>
            <div class="hint" v-if="tileCfg.timeframe === 'custom' && !tileRangeValid(tileCfg)">
              Bitte Start und Ende wählen – das Ende darf nicht vor dem Start liegen.
            </div>
          </div>

          <div class="field">
            <label>Überschrift (optional)</label>
            <input class="input" v-model="tileCfg.title" :placeholder="dashTitle(tileCfg)" />
          </div>
        </div>
        <div class="modal-foot has-danger">
          <hold-button :small="true" @held="removeTileFromConfig">✕ Entfernen (halten)</hold-button>
          <span class="foot-spacer"></span>
          <button class="btn" @click="tileCfg = null">Abbrechen</button>
          <button class="btn btn-primary" :disabled="!tileRangeValid(tileCfg)" @click="applyTileConfig">Übernehmen</button>
        </div>
      </div>
    </div>

    <!-- ADMIN-TOOLS -->
    <template v-else-if="view==='admin'">
      <div class="eyebrow">Admin-Tools</div>
      <div class="seg settings-seg">
        <button :class="{active: adminTab==='system'}"   @click="adminTab='system'">System</button>
        <button :class="{active: adminTab==='netzwerk'}" @click="adminTab='netzwerk'">Netzwerk</button>
        <button :class="{active: adminTab==='zugriff'}"  @click="adminTab='zugriff'">Zugriff</button>
        <button :class="{active: adminTab==='daten'}"    @click="adminTab='daten'; loadBackupStatus()">Datenmanagement</button>
        <button :class="{active: adminTab==='diag'}"     @click="adminTab='diag'">Diagnose</button>
        <button :class="{active: adminTab==='sql'}"      @click="adminTab='sql'">Abfrage</button>
        <button :class="{active: adminTab==='logs'}"     @click="adminTab='logs'; loadAdminLogs()">Protokoll</button>
        <button :class="{active: adminTab==='audit'}"    @click="adminTab='audit'; loadAudit()">Änderungen</button>
      </div>

      <!-- System -->
      <template v-if="adminTab==='system'">
        <div class="card set-card killswitch" :class="{armed: appSettingsDraft && appSettingsDraft.offline_mode}">
          <h3>Internetzugriff</h3>
          <p class="hint">Zählwerk funktioniert vollständig ohne Internet. Externe Abrufe sind
            im Auslieferungszustand gesperrt und müssen bewusst freigegeben werden.</p>
          <div class="field" v-if="appSettingsDraft">
            <label class="check ks-toggle">
              <input type="checkbox" v-model="appSettingsDraft.offline_mode" @change="validateSettings" />
              <span>
                <strong>Offline-Modus (Kill-Switch)</strong>
                <small>{{ appSettingsDraft.offline_mode
                  ? 'Aktiv – alle ausgehenden Verbindungen ins Internet werden blockiert.'
                  : 'Aus – Abrufe bei Wetter- und Tarifdienst sind erlaubt.' }}</small>
              </span>
            </label>
          </div>
          <table class="info-table" v-if="extStatus">
            <tr><td>Zustand</td><td>{{ extStatus.offline_mode ? 'gesperrt' : 'freigegeben' }}</td></tr>
            <tr><td>Socket-Sperre</td><td>{{ extStatus.socket_guard_active ? 'installiert' : 'nicht aktiv' }}</td></tr>
            <tr v-for="p in extStatus.providers" :key="p.key">
              <td>{{ p.label }}</td><td class="num">{{ p.host }}</td>
            </tr>
          </table>
          <div class="hint ks-note">
            Die Sperre gilt für das Backend. Die Oberfläche lädt Vue, Chart.js und die
            Schriftart weiterhin per CDN – für vollständige Datensouveränität müssen diese
            Dateien lokal ausgeliefert werden.
          </div>
          <div class="settings-actions" v-if="extStatus && extStatus.cache.length">
            <button class="btn btn-sm" @click="clearExtCache">↺ Zwischenspeicher leeren ({{ extStatus.cache.length }})</button>
          </div>
        </div>

        <div class="card set-card">
          <h3>Anwendungsparameter</h3>
          <p class="hint">Serverseitig in SQLite gespeichert, gilt für alle Geräte. Wird vor dem Speichern validiert.</p>

          <div class="field">
            <label class="check"><input type="checkbox" v-model="appSettingsDraft.notify_enabled" v-if="appSettingsDraft" />
              Benachrichtigung bei überfälliger Ablesung</label>
          </div>
          <div class="field" v-if="appSettingsDraft">
            <label>Prüfintervall (Stunden)</label>
            <input class="input" type="number" min="1" max="168" step="1"
                   v-model="appSettingsDraft.notify_interval_hours"
                   :class="{invalid: settingsErrors.notify_interval_hours}" @input="validateSettings" />
            <div class="err-inline" v-if="settingsErrors.notify_interval_hours">{{ settingsErrors.notify_interval_hours }}</div>
            <div class="hint" v-else>Wie oft der Hintergrunddienst auf Fälligkeiten prüft. Greift ohne Neustart.</div>
          </div>
          <div class="field" v-if="appSettingsDraft">
            <label>Standard-Ableseintervall (Tage)</label>
            <input class="input" type="number" min="0" max="3650" step="1"
                   v-model="appSettingsDraft.default_interval_days"
                   :class="{invalid: settingsErrors.default_interval_days}" @input="validateSettings" />
            <div class="err-inline" v-if="settingsErrors.default_interval_days">{{ settingsErrors.default_interval_days }}</div>
            <div class="hint" v-else>0 = Fälligkeit aus dem Median der bisherigen Intervalle schätzen.</div>
          </div>
          <div class="field" v-if="appSettingsDraft">
            <label>Ausreißer-Schwelle (σ)</label>
            <input class="input" type="number" min="1" max="5" step="0.1"
                   v-model="appSettingsDraft.outlier_sigma"
                   :class="{invalid: settingsErrors.outlier_sigma}" @input="validateSettings" />
            <div class="err-inline" v-if="settingsErrors.outlier_sigma">{{ settingsErrors.outlier_sigma }}</div>
            <div class="hint" v-else>Ø + n·σ gilt als Ausreißer. Kleiner = empfindlicher. Standard 2,0.</div>
          </div>
        </div>

        <div class="save-bar" :class="{ dirty: settingsDirty(), invalid: settingsErrorCount() > 0 }"
             v-if="appSettingsDraft">
          <div class="sb-info">
            <span v-if="settingsSaving">Speichert …</span>
            <span v-else-if="settingsErrorCount()" class="sb-err">
              ⚠ {{ settingsErrorCount() }} {{ settingsErrorCount()===1 ? 'Feld' : 'Felder' }} prüfen
            </span>
            <span v-else-if="settingsDirty()">
              {{ settingsChangeCount() }} ungespeicherte Änderung{{ settingsChangeCount()===1 ? '' : 'en' }}
            </span>
            <span v-else class="sb-clean">✓ Alles gespeichert</span>
          </div>
          <button class="btn" :disabled="!settingsDirty() || settingsSaving" @click="revertSettings">Verwerfen</button>
          <button class="btn btn-primary"
                  :disabled="settingsSaving || !settingsDirty() || settingsErrorCount() > 0"
                  @click="saveSettings">Speichern</button>
        </div>
      </template>

      <!-- Netzwerk (MQTT/HA) -->
      <template v-else-if="adminTab==='netzwerk'">
        <div class="card set-card" v-if="appSettingsDraft">
          <h3>MQTT-Ingestion</h3>
          <p class="hint">Übernimmt Zählerstände aus Broker-Nachrichten. Je System und Tag
            wird höchstens eine Ablesung geschrieben – der Wert des laufenden Tages wird
            aktualisiert statt angehängt.</p>

          <div class="hint ks-note" v-if="mqttStatus && !mqttStatus.available">
            <code>paho-mqtt</code> fehlt im Image. Das Add-on nach dem Update neu bauen lassen.
          </div>

          <div class="field">
            <label class="check"><input type="checkbox" v-model="appSettingsDraft.mqtt_enabled" @change="validateSettings" />
              <span>MQTT aktiv</span></label>
          </div>

          <template v-if="appSettingsDraft.mqtt_enabled">
            <div class="field">
              <label class="check"><input type="checkbox" v-model="appSettingsDraft.mqtt_use_supervisor" />
                <span>Zugangsdaten von Home Assistant beziehen
                  <small>{{ mqttStatus && mqttStatus.supervisor_offer
                    ? 'Mosquitto-Add-on erkannt – kein Passwort nötig'
                    : 'Kein MQTT-Dienst gemeldet; unten manuell eintragen' }}</small></span></label>
            </div>

            <template v-if="!appSettingsDraft.mqtt_use_supervisor || (mqttStatus && !mqttStatus.supervisor_offer)">
              <div class="field-row">
                <div class="field"><label>Broker-Host</label>
                  <input class="input" v-model="appSettingsDraft.mqtt_host" placeholder="192.168.1.10" /></div>
                <div class="field"><label>Port</label>
                  <input class="input" type="number" min="1" max="65535" v-model="appSettingsDraft.mqtt_port" /></div>
              </div>
              <div class="field-row">
                <div class="field"><label>Benutzer</label>
                  <input class="input" v-model="appSettingsDraft.mqtt_username" autocomplete="off" /></div>
                <div class="field"><label>Passwort</label>
                  <input class="input" type="password" v-model="mqttPassword" autocomplete="new-password"
                         :placeholder="appSettings && appSettings.mqtt_password_set ? '•••••••• (hinterlegt)' : ''" />
                  <div class="hint">Nur ausfüllen, um es zu ändern.</div></div>
              </div>
              <div class="hint ks-note">
                Manuell eingetragene Zugangsdaten liegen unverschlüsselt in der SQLite-Datei.
                Über das Mosquitto-Add-on entfällt das.
              </div>
            </template>

            <div class="field">
              <label class="check"><input type="checkbox" v-model="appSettingsDraft.mqtt_tasmota_discovery" />
                <span>Tasmota Auto-Discovery aktivieren
                  <small>Hört auf <code>{{ (appSettingsDraft.mqtt_base_topic || 'tele') }}/+/SENSOR</code> und
                    <code>/+/LWT</code> und listet gefundene Geräte. Es wird nichts gespeichert,
                    solange kein Topic zugeordnet ist.</small></span></label>
            </div>
            <div class="field">
              <label>Speicherintervall (Vorgabe)</label>
              <select class="select" v-model="appSettingsDraft.mqtt_interval" @change="validateSettings">
                <option value="daily">Täglich – ein Wert je Tag</option>
                <option value="weekly">Wöchentlich – ein Wert je Kalenderwoche</option>
                <option value="monthly">Monatlich – ein Wert je Kalendermonat</option>
                <option value="quarterly">Quartalsweise – ein Wert je Quartal</option>
                <option value="yearly">Jährlich – ein Wert je Kalenderjahr</option>
              </select>
              <div class="hint">
                Je Periode wird ein Datensatz geführt und innerhalb der laufenden Periode
                fortgeschrieben. Einzelne Systeme lassen sich unter „✎ Bearbeiten“ abweichend
                einstellen. Von Hand erfasste Ablesungen werden nie überschrieben.
              </div>
            </div>

            <div class="field" v-if="appSettingsDraft.mqtt_tasmota_discovery">
              <label>Telemetrie-Präfix</label>
              <input class="input" v-model="appSettingsDraft.mqtt_base_topic" placeholder="tele" />
              <div class="hint">Tasmota-Standard ist <code>tele</code>. Nur ändern, wenn im Gerät angepasst.</div>
            </div>

            <div class="field">
              <label class="check"><input type="checkbox" v-model="appSettingsDraft.mqtt_watchdog_enabled" @change="validateSettings" />
                <span>Watchdog aktiv
                  <small>Meldet über Home Assistant, wenn ein zugeordnetes System zu lange keinen neuen
                    MQTT-Wert liefert. Systeme mit längerem Speicherintervall (wöchentlich, monatlich …)
                    bekommen automatisch mehr Kulanz, damit die reguläre Speicherpause keinen Fehlalarm auslöst.</small></span></label>
            </div>
            <div class="field" v-if="appSettingsDraft.mqtt_watchdog_enabled">
              <label>Schwelle (Stunden)</label>
              <input class="input" type="number" min="1" max="336" step="1"
                     v-model="appSettingsDraft.mqtt_watchdog_hours"
                     :class="{invalid: settingsErrors.mqtt_watchdog_hours}" @input="validateSettings" />
              <div class="err-inline" v-if="settingsErrors.mqtt_watchdog_hours">{{ settingsErrors.mqtt_watchdog_hours }}</div>
              <div class="hint" v-else>Gilt für täglich speichernde Systeme; Standard 48 Stunden.</div>
            </div>

            <div class="settings-actions">
              <button class="btn" @click="restartMqtt">↻ Neu verbinden</button>
              <button class="btn btn-sm" @click="loadMqtt">Status aktualisieren</button>
              <button class="btn btn-sm" v-if="mqttStatus && mqttStatus.devices && mqttStatus.devices.length"
                      @click="forgetDevices">Geräteliste leeren</button>
            </div>

            <div class="mqtt-devices" v-if="mqttStatus && mqttStatus.devices && mqttStatus.devices.length">
              <div class="hw-head">Erkannte Geräte ({{ mqttStatus.devices.length }})</div>
              <div v-for="d in mqttStatus.devices" :key="d.device" class="mq-dev" :class="{unusable: !d.usable}">
                <div class="mq-dev-head">
                  <span class="mq-dot" :class="d.online===true ? 'on' : (d.online===false ? 'off' : 'unknown')"
                        :title="d.online===true ? 'Online' : (d.online===false ? 'Offline (LWT)' : 'Status unbekannt')"></span>
                  <strong>{{ d.device }}</strong>
                  <span class="mq-assigned" v-if="d.assigned">→ {{ d.system }}</span>
                </div>
                <div class="mq-dev-sub">
                  <code>{{ d.topic }}</code>
                  <span v-if="d.usable">{{ fmt(d.value, 3) }} {{ d.unit }} · {{ d.path }}</span>
                  <span v-else>kein Zählerstand im Telegramm</span>
                  <span v-if="d.power !== null && d.power !== undefined">{{ d.power }} W</span>
                </div>
                <!-- Diagnose: bei nicht erkanntem Telegramm die rohe Nutzlast und
                     alle Zahlenpfade zeigen – damit lässt sich der Pfad ablesen. -->
                <details class="mq-raw" v-if="!d.usable && d.raw">
                  <summary>Rohdaten anzeigen ({{ (d.numeric_paths || []).length }} Zahlenfelder)</summary>
                  <div class="mq-paths" v-if="d.numeric_paths && d.numeric_paths.length">
                    <div v-for="p in d.numeric_paths" :key="p.path" class="mq-path">
                      <code>{{ p.path }}</code><span>{{ p.value }}</span>
                    </div>
                  </div>
                  <pre class="mq-json">{{ d.raw }}</pre>
                  <div class="hint">
                    Den passenden Pfad im System unter „✎ Bearbeiten“ → <strong>MQTT JSON-Pfad</strong>
                    eintragen. Er hat dann Vorrang vor der automatischen Erkennung.
                  </div>
                </details>
                <details class="mq-raw" v-else-if="d.candidates && d.candidates.length > 1">
                  <summary>{{ d.candidates.length }} mögliche Felder – Zuordnung prüfen</summary>
                  <div class="mq-paths">
                    <div v-for="c in d.candidates" :key="c.path" class="mq-path"
                         :class="{sel: c.path === d.path}">
                      <code>{{ c.path }}</code><span>{{ c.value }}</span>
                    </div>
                  </div>
                </details>

                <div class="mq-dev-act" v-if="!d.assigned">
                  <template v-if="d.usable">
                    <select class="select" v-model="assignTarget[d.device]">
                      <option :value="null">System wählen …</option>
                      <option v-for="s in systems.filter(x => x.aktiv)" :key="s.id" :value="s.id">{{ s.name }}</option>
                    </select>
                    <button class="btn btn-sm" :disabled="!assignTarget[d.device]" @click="assignDevice(d)">Zuordnen</button>
                  </template>
                  <button class="btn btn-sm" @click="ignoreDevice(d)"
                          title="Unbeteiligtes Gerät dauerhaft ausblenden">✕ Ignorieren</button>
                </div>
              </div>
            </div>

            <div class="mqtt-devices" v-if="mqttStatus && mqttStatus.ignored && mqttStatus.ignored.length">
              <details>
                <summary class="hw-head">Ignorierte Geräte ({{ mqttStatus.ignored.length }})</summary>
                <div v-for="device in mqttStatus.ignored" :key="device" class="mq-dev">
                  <div class="mq-dev-head"><strong>{{ device }}</strong></div>
                  <div class="mq-dev-act">
                    <button class="btn btn-sm" @click="unignoreDevice(device)">Wieder anzeigen</button>
                  </div>
                </div>
              </details>
            </div>

            <table class="info-table" v-if="mqttStatus">
              <tr><td>Verbindung</td><td>{{ mqttStatus.connected ? 'verbunden' : 'getrennt' }}</td></tr>
              <tr v-if="mqttStatus.broker"><td>Broker</td><td class="num">{{ mqttStatus.broker }} · {{ mqttStatus.source }}</td></tr>
              <tr v-if="mqttStatus.last_error"><td>Letzter Fehler</td><td>{{ mqttStatus.last_error }}</td></tr>
              <tr><td>Nachrichten</td><td class="num">{{ mqttStatus.messages }} empfangen · {{ mqttStatus.written }} geschrieben</td></tr>
              <tr v-for="m in mqttStatus.mapped" :key="m.topic">
                <td>{{ m.system }}<small class="bk-age"> · {{ m.interval_label }}{{ m.own_interval ? ' (eigen)' : '' }}</small></td>
                <td class="num">{{ m.topic }}</td>
              </tr>
            </table>
            <div class="hint" v-if="mqttStatus && !mqttStatus.mapped.length">
              Noch kein Topic zugeordnet. Trag es je System unter „✎ Bearbeiten“ im Feld
              <strong>MQTT-Topic</strong> ein.
            </div>

            <div class="mqtt-log" v-if="mqttStatus && mqttStatus.events.length">
              <div class="hw-head">Letzte Ereignisse</div>
              <div v-for="(e,i) in mqttStatus.events" :key="i" class="mq-row" :class="e.level">
                <span class="mq-ts">{{ e.ts.slice(11,19) }}</span><span>{{ e.text }}</span>
              </div>
            </div>
          </template>
        </div>

        <div class="save-bar" :class="{ dirty: settingsDirty(), invalid: settingsErrorCount() > 0 }"
             v-if="appSettingsDraft">
          <div class="sb-info">
            <span v-if="settingsSaving">Speichert …</span>
            <span v-else-if="settingsErrorCount()" class="sb-err">
              ⚠ {{ settingsErrorCount() }} {{ settingsErrorCount()===1 ? 'Feld' : 'Felder' }} prüfen
            </span>
            <span v-else-if="settingsDirty()">
              {{ settingsChangeCount() }} ungespeicherte Änderung{{ settingsChangeCount()===1 ? '' : 'en' }}
            </span>
            <span v-else class="sb-clean">✓ Alles gespeichert</span>
          </div>
          <button class="btn" :disabled="!settingsDirty() || settingsSaving" @click="revertSettings">Verwerfen</button>
          <button class="btn btn-primary"
                  :disabled="settingsSaving || !settingsDirty() || settingsErrorCount() > 0"
                  @click="saveSettings">Speichern</button>
        </div>
      </template>

      <!-- Zugriff (RBAC) -->
      <template v-else-if="adminTab==='zugriff'">
        <div class="card set-card">
          <h3>Konten &amp; Rollen</h3>
          <p class="hint">Änderungen greifen beim nächsten Aufruf des jeweiligen Kontos.
            Die Rechte werden serverseitig durchgesetzt, das Ausblenden in der Oberfläche
            ist nur Beiwerk.</p>
          <div class="field" v-if="appSettingsDraft">
            <label>Rolle für neu übernommene Home-Assistant-Konten</label>
            <select class="select" v-model="appSettingsDraft.default_role" @change="validateSettings">
              <option v-for="r in authRoles" :key="r.key" :value="r.key">{{ r.label }} – {{ r.hint }}</option>
            </select>
          </div>
          <table class="info-table" v-if="users.length">
            <tr v-for="u in users" :key="u.id">
              <td>
                {{ u.display_name }}
                <small class="bk-age"> · {{ u.username }}{{ u.source === 'homeassistant' ? ' · HA' : '' }}</small>
              </td>
              <td class="num">
                <select class="select role-select" :value="u.role" @change="setUserRole(u, $event.target.value)">
                  <option v-for="r in authRoles" :key="r.key" :value="r.key">{{ r.label }}</option>
                </select>
              </td>
            </tr>
          </table>
          <div class="hint" v-else>Konten erscheinen, sobald sie sich erstmals angemeldet haben.</div>
        </div>

        <div class="save-bar" :class="{ dirty: settingsDirty(), invalid: settingsErrorCount() > 0 }"
             v-if="appSettingsDraft">
          <div class="sb-info">
            <span v-if="settingsSaving">Speichert …</span>
            <span v-else-if="settingsDirty()">
              {{ settingsChangeCount() }} ungespeicherte Änderung{{ settingsChangeCount()===1 ? '' : 'en' }}
            </span>
            <span v-else class="sb-clean">✓ Alles gespeichert</span>
          </div>
          <button class="btn" :disabled="!settingsDirty() || settingsSaving" @click="revertSettings">Verwerfen</button>
          <button class="btn btn-primary"
                  :disabled="settingsSaving || !settingsDirty() || settingsErrorCount() > 0"
                  @click="saveSettings">Speichern</button>
        </div>
      </template>

      <!-- Diagnose -->
      <template v-else-if="adminTab==='diag'">
        <div class="card set-card" v-if="adminDiag">
          <h3>Datenbank</h3>
          <table class="info-table">
            <tr><td>Pfad</td><td class="num">{{ adminDiag.database.path }}</td></tr>
            <tr><td>Version / Schema</td><td class="num">{{ adminDiag.app_version }} · Schema {{ adminDiag.schema_version }}</td></tr>
            <tr><td>Integritätsprüfung</td>
                <td :class="adminDiag.database.integrity_check === 'ok' ? '' : 'sb-err'">
                  {{ adminDiag.database.integrity_check }}</td></tr>
            <tr><td>Fremdschlüsselfehler</td>
                <td :class="adminDiag.database.foreign_key_errors ? 'sb-err' : ''">
                  {{ adminDiag.database.foreign_key_errors }}</td></tr>
            <tr><td>Journal</td><td class="num">{{ adminDiag.database.journal_mode }}</td></tr>
            <tr><td>Größe</td><td class="num">
              {{ fmtBytes(adminDiag.database.sizes_bytes.db) }}
              <small class="bk-age"> + WAL {{ fmtBytes(adminDiag.database.sizes_bytes.wal) }}</small></td></tr>
            <tr><td>Fragmentierung</td><td class="num">{{ adminDiag.database.fragmentation_pct }} %
              <small class="bk-age" v-if="adminDiag.database.fragmentation_pct > 25"> · VACUUM sinnvoll</small></td></tr>
          </table>
        </div>
        <div class="card set-card" v-if="adminDiag">
          <h3>Dienste</h3>
          <table class="info-table">
            <tr><td>Offline-Modus</td><td>{{ adminDiag.outbound.offline_mode ? 'aktiv' : 'aus' }}</td></tr>
            <tr><td>Socket-Sperre</td><td>{{ adminDiag.outbound.socket_guard ? 'installiert' : 'nicht aktiv' }}</td></tr>
            <tr><td>MQTT</td><td class="num">
              {{ adminDiag.mqtt.connected ? 'verbunden' : 'getrennt' }}
              <span v-if="adminDiag.mqtt.broker"> · {{ adminDiag.mqtt.broker }}</span></td></tr>
            <tr v-if="adminDiag.mqtt.last_error"><td>MQTT-Fehler</td><td class="sb-err">{{ adminDiag.mqtt.last_error }}</td></tr>
            <tr><td>Nachrichten</td><td class="num">{{ adminDiag.mqtt.messages }} empfangen · {{ adminDiag.mqtt.written }} geschrieben</td></tr>
            <tr><td>Sicherungen</td><td class="num">{{ adminDiag.backup.entries }} in {{ adminDiag.backup.directory }}</td></tr>
          </table>
          <div class="settings-actions"><button class="btn btn-sm" @click="loadAdmin">↻ Aktualisieren</button></div>
        </div>
        <div class="card set-card" v-if="sysInfo">
          <h3>Laufzeit &amp; Datenbank</h3>
          <p class="hint">Read-only. Container, Port und DB-Pfad gehören dem Supervisor und werden über
            <code>config.yaml</code> bzw. das Add-on-Panel gesteuert, nicht hier.</p>
          <table class="info-table">
            <tr><td>Betriebsart</td><td>{{ sysInfo.runtime }}</td></tr>
            <tr><td>App-Version</td><td class="num">{{ appVersion }}</td></tr>
            <tr><td>Schema-Version</td><td class="num">{{ sysInfo.schema_version }}</td></tr>
            <tr><td>Python</td><td class="num">{{ sysInfo.python_version }} · {{ sysInfo.platform }}</td></tr>
            <tr><td>Supervisor-API</td><td>{{ sysInfo.supervisor_available ? 'verbunden' : 'nicht verfügbar' }}</td></tr>
            <tr><td>DB-Pfad</td><td class="num">{{ sysInfo.db_path }}</td></tr>
            <tr><td>DB-Größe</td><td class="num">{{ fmtBytes(sysInfo.db_size_bytes) }}</td></tr>
            <tr><td>Journal-Modus</td><td class="num">{{ sysInfo.journal_mode }}</td></tr>
            <tr><td>Foreign Keys</td><td>{{ sysInfo.foreign_keys ? 'aktiv' : 'inaktiv' }}</td></tr>
            <tr><td>Datenbestand</td><td class="num">{{ sysInfo.system_count }} Systeme · {{ sysInfo.reading_count }} Ablesungen</td></tr>
          </table>
        </div>
      </template>

      <!-- Abfrage -->
      <template v-else-if="adminTab==='sql'">
        <div class="card set-card">
          <h3>Datenbankabfrage</h3>
          <p class="hint">Nur lesend. Die Verbindung wird schreibgeschützt geöffnet,
            zugelassen sind ausschließlich <code>SELECT</code> und <code>WITH</code>,
            höchstens 500 Zeilen je Abfrage. Jede Abfrage wird mit Konto protokolliert.</p>
          <textarea class="input sql-input" rows="4" v-model="sqlText"
                    spellcheck="false" @keydown.ctrl.enter="runQuery"></textarea>
          <div class="settings-actions">
            <button class="btn btn-primary" :disabled="sqlBusy" @click="runQuery">
              {{ sqlBusy ? 'Läuft …' : 'Ausführen' }}</button>
            <span class="hint sql-hint">Strg + Eingabe</span>
          </div>
          <div class="err-inline" v-if="sqlError">{{ sqlError }}</div>

          <div class="sql-samples">
            <button class="crumb" @click="useSample('SELECT name, typ, einheit FROM systems ORDER BY name')">Systeme</button>
            <button class="crumb" @click="useSample('SELECT s.name, COUNT(r.id) AS werte, MAX(r.datum) AS letzte FROM systems s LEFT JOIN readings r ON r.system_id = s.id GROUP BY s.name')">Werte je System</button>
            <button class="crumb" @click="useSample('SELECT datum, value, note FROM readings ORDER BY datum DESC LIMIT 20')">Letzte Ablesungen</button>
            <button class="crumb" @click="useSample('SELECT username, role, aktiv, letzter_login FROM users')">Konten</button>
          </div>
        </div>

        <div class="card set-card" v-if="sqlResult">
          <h3>{{ sqlResult.row_count }} Zeile{{ sqlResult.row_count===1 ? '' : 'n' }}
            <small class="bk-age">· {{ sqlResult.duration_ms }} ms{{ sqlResult.truncated ? ' · gekürzt auf 500' : '' }}</small></h3>
          <div class="sql-scroll">
            <table class="sql-table">
              <thead><tr><th v-for="c in sqlResult.columns" :key="c">{{ c }}</th></tr></thead>
              <tbody>
                <tr v-for="(row,i) in sqlResult.rows" :key="i">
                  <td v-for="(v,j) in row" :key="j">{{ v === null ? '—' : v }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card set-card" v-if="adminSchema.length">
          <h3>Tabellen</h3>
          <div v-for="t in adminSchema" :key="t.table" class="sql-schema">
            <button class="crumb" @click="useSample('SELECT * FROM ' + t.table + ' LIMIT 20')">{{ t.table }}</button>
            <small>{{ t.rows }} Zeilen · {{ t.columns.map(c => c.name).join(', ') }}</small>
          </div>
        </div>
      </template>

      <!-- Änderungsprotokoll -->
      <template v-else-if="adminTab==='audit'">
        <div class="card set-card">
          <h3>Änderungsprotokoll</h3>
          <p class="hint">Schreibgeschützt. Einträge lassen sich weder ändern noch
            innerhalb der ersten 30 Tage löschen – das setzt die Datenbank selbst durch.</p>

          <div class="audit-filters">
            <select class="select" v-model="auditFilter.action" @change="loadAudit(1)">
              <option :value="null">Alle Aktionen</option>
              <option v-for="a in auditFacets.actions" :key="a" :value="a">{{ a }}</option>
            </select>
            <select class="select" v-model="auditFilter.target_table" @change="loadAudit(1)">
              <option :value="null">Alle Tabellen</option>
              <option v-for="t in auditFacets.tables" :key="t" :value="t">{{ t }}</option>
            </select>
            <select class="select" v-model="auditFilter.user_id" @change="loadAudit(1)">
              <option :value="null">Alle Konten</option>
              <option v-for="u in auditFacets.users" :key="u.id || 'sys'" :value="u.id">{{ u.username }}</option>
            </select>
            <input class="input" type="date" v-model="auditFilter.from" @change="loadAudit(1)" title="von" />
            <input class="input" type="date" v-model="auditFilter.to" @change="loadAudit(1)" title="bis" />
            <button class="btn btn-sm" @click="resetAuditFilter">↺</button>
          </div>

          <div v-if="auditLoading" class="center-load"><span class="spin"></span></div>
          <div class="hint" v-else-if="!auditEntries.length">Keine Einträge für diese Auswahl.</div>

          <template v-else>
            <div class="sql-scroll">
              <table class="sql-table audit-table">
                <thead>
                  <tr><th>Zeit</th><th>Konto</th><th>Aktion</th><th>Tabelle</th><th>Datensatz</th><th>Änderung</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="e in auditEntries" :key="e.id">
                    <td>{{ e.ts.replace('T', ' ').slice(0, 19) }}</td>
                    <td>{{ e.username }}</td>
                    <td><span class="chip" :class="'chip-act-' + e.action.toLowerCase()">{{ e.action }}</span></td>
                    <td>{{ e.target_table }}</td>
                    <td class="au-id">{{ e.target_id || '–' }}</td>
                    <td class="au-diff">{{ auditSummary(e) }}</td>
                    <td>
                      <button v-if="auditCanRollback(e)" class="btn btn-sm" :disabled="auditUndoBusy === e.id"
                              @click="undoAuditEntry(e)" title="Diese Änderung rückgängig machen">
                        {{ auditUndoBusy === e.id ? '…' : '↺ Rückgängig' }}</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="pager audit-pager">
              <button class="btn btn-sm" :disabled="auditPage<=1" @click="loadAudit(auditPage-1)">‹ Zurück</button>
              <span>Seite {{ auditPage }} / {{ auditPages }} · {{ auditTotal }} Einträge</span>
              <button class="btn btn-sm" :disabled="auditPage>=auditPages" @click="loadAudit(auditPage+1)">Weiter ›</button>
            </div>
          </template>
        </div>
      </template>

      <!-- Datenmanagement -->
      <template v-else-if="adminTab==='daten'">
        <div class="card set-card" v-if="appSettingsDraft">
          <h3>Zeitplan</h3>
          <p class="hint">Legt eine konsistente Kopie der Datenbank in
            <code>{{ backupStatus ? backupStatus.directory : '/backup' }}</code> ab.
            Home Assistant nimmt dieses Verzeichnis in seine eigenen Voll-Sicherungen auf.</p>

          <div class="hint ks-note" v-if="backupStatus && !backupStatus.supervisor_backup_dir">
            <code>/backup</code> ist nicht gemappt – es wird nach <code>/share</code> gesichert.
            Diese Dateien landen NICHT im Home-Assistant-Backup. Ergänze
            <code>backup:rw</code> unter <code>map:</code> in der <code>config.yaml</code>.
          </div>

          <div class="field">
            <label class="check"><input type="checkbox" v-model="appSettingsDraft.backup_enabled" @change="validateSettings" />
              <span>Tägliche Sicherung aktiv</span></label>
          </div>
          <div class="field-row">
            <div class="field"><label>Uhrzeit</label>
              <input class="input" type="time" v-model="appSettingsDraft.backup_time"
                     :class="{invalid: settingsErrors.backup_time}" @input="validateSettings" />
              <div class="err-inline" v-if="settingsErrors.backup_time">{{ settingsErrors.backup_time }}</div>
            </div>
            <div class="field"><label>Aufbewahrung (Tage)</label>
              <input class="input" type="number" min="1" max="365" step="1"
                     v-model="appSettingsDraft.backup_keep_days"
                     :class="{invalid: settingsErrors.backup_keep_days}" @input="validateSettings" />
              <div class="err-inline" v-if="settingsErrors.backup_keep_days">{{ settingsErrors.backup_keep_days }}</div>
              <div class="hint" v-else>Die drei neuesten bleiben immer erhalten.</div>
            </div>
          </div>
          <div class="field">
            <label>Telemetrie in voller Auflösung behalten (Tage, 0 = unbegrenzt)</label>
            <input class="input" type="number" min="0" max="36500" step="1"
                   v-model="appSettingsDraft.telemetry_keep_days"
                   :class="{invalid: settingsErrors.telemetry_keep_days}" @input="validateSettings" />
            <div class="err-inline" v-if="settingsErrors.telemetry_keep_days">{{ settingsErrors.telemetry_keep_days }}</div>
            <div class="hint" v-else>Ältere MQTT-Werte werden auf einen Datensatz je Monat verdünnt. Von Hand erfasste, importierte und aus HA übernommene Werte bleiben immer vollständig erhalten; Gesamtverbräuche ändern sich nicht.</div>
          </div>
        </div>

        <div class="save-bar" :class="{ dirty: settingsDirty(), invalid: settingsErrorCount() > 0 }"
             v-if="appSettingsDraft">
          <div class="sb-info">
            <span v-if="settingsSaving">Speichert …</span>
            <span v-else-if="settingsErrorCount()" class="sb-err">
              ⚠ {{ settingsErrorCount() }} {{ settingsErrorCount()===1 ? 'Feld' : 'Felder' }} prüfen
            </span>
            <span v-else-if="settingsDirty()">
              {{ settingsChangeCount() }} ungespeicherte Änderung{{ settingsChangeCount()===1 ? '' : 'en' }}
            </span>
            <span v-else class="sb-clean">✓ Alles gespeichert</span>
          </div>
          <button class="btn" :disabled="!settingsDirty() || settingsSaving" @click="revertSettings">Verwerfen</button>
          <button class="btn btn-primary"
                  :disabled="settingsSaving || !settingsDirty() || settingsErrorCount() > 0"
                  @click="saveSettings">Speichern</button>
        </div>

        <div class="card set-card">
          <h3>Sicherungen</h3>
          <div class="settings-actions">
            <button class="btn btn-primary" :disabled="backupBusy" @click="runBackup">
              {{ backupBusy ? 'Sichere …' : '⇩ Jetzt sichern' }}</button>
            <button class="btn" @click="exportAll">⇩ Sicherung (ZIP)</button>
            <button class="btn" @click="openExportConfig">⇩ Rohdaten (CSV / JSON) …</button>
          </div>

          <table class="info-table" v-if="backupStatus && backupStatus.entries.length">
            <tr v-for="b in backupStatus.entries" :key="b.file">
              <td>{{ fmtDate(b.created.slice(0,10)) }}<small class="bk-age"> · {{ b.age_days }} T</small></td>
              <td class="num">
                {{ fmtBytes(b.size_bytes) }}
                <a class="crumb" :href="'api/backup/' + b.file" download title="Herunterladen">⇩</a>
                <button class="btn btn-sm" :disabled="!!restoreBusy"
                        @click="restoreBackup(b.file)" title="Aus dieser Sicherung wiederherstellen">
                  {{ restoreBusy === b.file ? '…' : '↺ Wiederherstellen' }}</button>
              </td>
            </tr>
          </table>
          <div class="hint" v-else-if="backupStatus">Noch keine Sicherung vorhanden.</div>
        </div>

        <div class="card set-card">
          <h3>Sicherung importieren</h3>
          <p class="hint">Stellt die Datenbank aus einer hochgeladenen <code>.gz</code>-Sicherung
            wieder her – z. B. nach einem Umzug oder einer Wiederherstellung aus einem
            Home-Assistant-Backup. Der aktuelle Bestand wird vorher automatisch gesichert.</p>
          <div class="settings-actions">
            <input class="input" type="file" accept=".gz" @change="onRestoreFile" />
            <button class="btn btn-primary" :disabled="!restoreFile || !!restoreBusy" @click="importRestore">
              {{ restoreBusy && restoreBusy === (restoreFile && restoreFile.name) ? 'Stelle wieder her …' : '⇧ Hochladen & wiederherstellen' }}</button>
          </div>
        </div>
      </template>

      <!-- Protokoll -->
      <template v-else-if="adminTab==='logs'">
        <div class="card set-card">
          <h3>Anwendungsprotokoll</h3>
          <div class="settings-actions">
            <div class="seg">
              <button v-for="l in ['INFO','WARNING','ERROR']" :key="l"
                      :class="{active: logLevel===l}" @click="logLevel=l; loadAdminLogs()">{{ l }}</button>
            </div>
            <button class="btn btn-sm" @click="loadAdminLogs">↻ Aktualisieren</button>
          </div>
          <div class="mqtt-log" v-if="adminLogs.length">
            <div v-for="(e,i) in adminLogs" :key="i" class="mq-row"
                 :class="{ warn: e.level === 'WARNING' || e.level === 'ERROR' }">
              <span class="mq-ts">{{ e.ts.slice(11,19) }}</span>
              <span class="log-src">{{ e.logger.replace('zaehlwerk.','') }}</span>
              <span>{{ e.message }}</span>
            </div>
          </div>
          <div class="hint" v-else>Keine Meldungen auf dieser Stufe.</div>
        </div>
      </template>
    </template>

    <!-- EINSTELLUNGEN -->
    <template v-else-if="view==='settings'">
      <div class="eyebrow">Einstellungen</div>

        <div class="card set-card" v-if="currentUser">
          <h3>Konto</h3>
          <table class="info-table">
            <tr><td>Angemeldet als</td><td>{{ currentUser.display_name }}</td></tr>
            <tr><td>Benutzername</td><td class="num">{{ currentUser.username }}</td></tr>
            <tr><td>Herkunft</td><td>{{ currentUser.source === 'homeassistant'
              ? 'Home Assistant (Ingress)' : 'lokales Konto' }}</td></tr>
          </table>
          <p class="hint" v-if="currentUser.source === 'homeassistant'">
            Die Anmeldung erfolgt bereits in Home Assistant. Zählwerk übernimmt sie und
            speichert kein Passwort.
          </p>
          <div class="settings-actions" v-else>
            <button class="btn" @click="doLogout">Abmelden</button>
          </div>
        </div>

        <div class="card set-card">
          <h3>Darstellung</h3>
          <p class="hint">Gerätelokal in diesem Browser gespeichert, kein Serverzugriff.</p>
          <div class="field">
            <label>Modus</label>
            <div class="theme-opts">
              <button class="theme-opt" :class="{sel: themeMode==='auto'}" @click="pickTheme('auto')"><span class="ic">🖥️</span> Automatisch (System)</button>
              <button class="theme-opt" :class="{sel: themeMode==='light'}" @click="pickTheme('light')"><span class="ic">☀️</span> Hell</button>
              <button class="theme-opt" :class="{sel: themeMode==='dark'}" @click="pickTheme('dark')"><span class="ic">🌙</span> Dunkel</button>
            </div>
          </div>
          <div class="field">
            <label>Farbpalette</label>
            <div class="theme-opts">
              <button v-for="p in palettes" :key="p.key" class="theme-opt"
                      :class="{sel: themePalette===p.key}" @click="pickPalette(p.key)">
                <span class="ic pal-dot" :style="{background: p.swatch}"></span> {{ p.label }}
              </button>
            </div>
          </div>
          <div class="field">
            <label>Kontrast</label>
            <div class="theme-opts">
              <button v-for="c in contrasts" :key="c.key" class="theme-opt"
                      :class="{sel: themeContrast===c.key}" @click="pickContrast(c.key)">
                <span class="ic">{{ c.key==='high' ? '◐' : '◔' }}</span> {{ c.label }}
              </button>
            </div>
            <div class="hint">Meldet dein System bereits eine Kontrastpräferenz, greift sie automatisch.</div>
          </div>
        </div>

        <div class="card set-card">
          <h3>Diagrammfarben</h3>
          <div class="chart-colors">
            <div v-for="c in chartColorKeys" :key="c.key" class="cc-row">
              <label class="cc-swatch" :style="{background: chartColorValue(c.key)}" :title="c.label">
                <input type="color" :value="chartColorValue(c.key)" @input="onChartColor(c.key, $event)" />
              </label>
              <span class="cc-label">
                {{ c.label }}
                <small>{{ isChartColorCustom(c.key) ? chartColorValue(c.key) : 'Theme-Standard' }}</small>
              </span>
              <button v-if="isChartColorCustom(c.key)" class="crumb cc-reset"
                      @click="clearChartColor(c.key)" title="Auf Theme-Standard zurücksetzen">↺</button>
            </div>
          </div>
          <div class="hint">Die <strong>Kurvenfarbe</strong> gehört zum jeweiligen System und wird dort bearbeitet.</div>
          <div class="settings-actions">
            <button class="btn btn-sm" @click="resetChartColors">↺ Alle auf Theme-Standard</button>
          </div>
        </div>

        <div class="card set-card">
          <h3>Über</h3>
          <div class="settings-actions">
            <button class="btn" @click="showChangelog=true">Zählwerk v{{ appVersion }} · Versionsverlauf</button>
          </div>
        </div>
    </template>

    <!-- DETAIL -->
    <system-detail
      ref="detail"
      v-else-if="selectedSystem && view==='detail'"
      :key="selectedSystem.id"
      :system="selectedSystem"
      @back="back"
      @edit="editSystem"
      @tab="detailTab = $event"
      @changed="load" />
  </div>

  <!-- MODAL: System -->
  <div class="overlay" v-if="showSystem" @click.self="showSystem=false">
    <div class="modal">
      <div class="modal-head"><h3>{{ sysForm.id ? 'System bearbeiten' : 'Neues System' }}</h3></div>
      <div class="modal-body">
        <label class="tf"><input class="tf-input" v-model="sysForm.name" placeholder=" " /><span class="tf-label">Name (z. B. Strom Hauptzähler)</span></label>
        <div class="field-row">
          <div class="field"><label>Typ</label>
            <select class="select" v-model="sysForm.typ" @change="onTypeChange">
              <option v-for="t in types" :key="t.v" :value="t.v">{{ t.v }}</option>
            </select>
          </div>
          <div class="field"><label>Einheit</label><input class="input" v-model="sysForm.einheit" placeholder="kWh, m³ …" /></div>
        </div>
        <div class="field">
          <label>Farbe</label>
          <div class="swatch-row">
            <span v-for="c in palette" :key="c" class="swatch-pick" :class="{sel: sysForm.farbe===c}" :style="{background:c}" @click="sysForm.farbe=c"></span>
            <label class="swatch-pick swatch-custom" :class="{sel: !palette.includes(sysForm.farbe)}"
                   :style="{background: sysForm.farbe}" title="Eigene Farbe wählen">
              <input type="color" v-model="sysForm.farbe" />
            </label>
          </div>
          <div class="hint">{{ sysForm.farbe }}<span v-if="colorWarning(sysForm.farbe)" class="warn-inline"> · {{ colorWarning(sysForm.farbe) }}</span></div>
        </div>
        <div class="field" v-for="f in formExtra" :key="f.key">
          <label>{{ f.label }}</label>
          <select v-if="f.type==='select'" class="select" style="width:100%" v-model="sysForm.zusatzfelder[f.key]">
            <!-- f.labels erlaubt lesbare Beschriftungen; ohne sie bleibt der Wert selbst stehen. -->
            <option v-for="o in f.options" :key="o" :value="o">{{
              (f.labels && f.labels[o]) || (o === '' ? '– automatisch –' : o) }}</option>
          </select>
          <input v-else class="input" :type="f.type" v-model="sysForm.zusatzfelder[f.key]" />
        </div>
        <div class="field" v-if="sysForm.id">
          <label class="check"><input type="checkbox" v-model="sysForm.aktiv" /> aktiv (deaktivieren = archivieren, Werte bleiben erhalten)</label>
        </div>
      </div>
      <div class="modal-foot" :class="{'has-danger': sysForm.id}">
        <hold-button v-if="sysForm.id" @held="confirmDeleteSystem">✕ Löschen (halten)</hold-button>
        <span class="foot-spacer"></span>
        <button class="btn" @click="showSystem=false">Abbrechen</button>
        <button class="btn btn-primary" :disabled="busy" @click="saveSystem">Speichern</button>
      </div>
    </div>
  </div>

  <!-- ANMELDUNG / ERSTEINRICHTUNG -->
  <div class="auth-gate" v-if="authNeeded">
    <div class="auth-card">
      <div class="auth-brand">◷ Zählwerk</div>

      <template v-if="auth.status && auth.status.setup_required">
        <h2>Erstes Konto anlegen</h2>
        <p class="hint">Zählwerk läuft ohne Home Assistant. Lege ein Konto an –
          danach ist die Anwendung nur noch angemeldet erreichbar.</p>
        <div class="field"><label>Benutzername</label>
          <input class="input" v-model="authForm.username" autocomplete="username"
                 @keyup.enter="doSetup" /></div>
        <div class="field"><label>Anzeigename (optional)</label>
          <input class="input" v-model="authForm.display_name" /></div>
        <div class="field"><label>Passwort</label>
          <input class="input" type="password" v-model="authForm.password"
                 autocomplete="new-password" @keyup.enter="doSetup" />
          <div class="err-inline" v-if="authForm.password && authForm.password.length < 12">
            Mindestens 12 Zeichen
          </div>
          <div class="hint" v-else>Mindestens 12 Zeichen. Länge wirkt stärker als Sonderzeichen.</div>
        </div>
        <div class="field"><label>Passwort wiederholen</label>
          <input class="input" type="password" v-model="authForm.password2"
                 autocomplete="new-password" @keyup.enter="doSetup" />
          <div class="err-inline" v-if="authForm.password2 && authForm.password2 !== authForm.password">
            Stimmt nicht überein
          </div>
        </div>
        <button class="btn btn-primary auth-submit" :disabled="!setupValid || authBusy" @click="doSetup">
          {{ authBusy ? 'Legt an …' : 'Konto anlegen' }}
        </button>
      </template>

      <template v-else>
        <h2>Anmelden</h2>
        <div class="hint ks-note" v-if="auth.status && !auth.status.crypto_available">
          <code>bcrypt</code> oder <code>PyJWT</code> fehlen im Image. Das Add-on
          nach dem Update neu bauen lassen.
        </div>
        <div class="field"><label>Benutzername</label>
          <input class="input" v-model="authForm.username" autocomplete="username"
                 @keyup.enter="doLogin" /></div>
        <div class="field"><label>Passwort</label>
          <input class="input" type="password" v-model="authForm.password"
                 autocomplete="current-password" @keyup.enter="doLogin" /></div>
        <div class="err-inline auth-err" v-if="authError">{{ authError }}</div>
        <button class="btn btn-primary auth-submit"
                :disabled="!authForm.username || !authForm.password || authBusy" @click="doLogin">
          {{ authBusy ? 'Prüft …' : 'Anmelden' }}
        </button>
      </template>
    </div>
  </div>

  <!-- MODAL: Bericht konfigurieren (Pre-Export) -->
  <div class="overlay" v-if="expCfg" @click.self="expCfg=null">
    <div class="modal modal-wide">
      <div class="modal-head"><h3>Bericht erstellen</h3></div>
      <div class="modal-body">

        <div class="field">
          <label>Zeitraum</label>
          <div class="seg exp-seg">
            <button :class="{active: expCfg.preset==='all'}"      @click="expApplyPreset('all')">Gesamt</button>
            <button :class="{active: expCfg.preset==='ytd'}"      @click="expApplyPreset('ytd')">Lfd. Jahr</button>
            <button :class="{active: expCfg.preset==='12m'}"      @click="expApplyPreset('12m')">12 Monate</button>
            <button :class="{active: expCfg.preset==='lastyear'}" @click="expApplyPreset('lastyear')">Vorjahr</button>
          </div>
          <div class="field-row exp-dates">
            <div class="field"><label>Von</label>
              <input class="input" type="date" v-model="expCfg.from" @change="expCfg.preset='custom'" /></div>
            <div class="field"><label>Bis</label>
              <input class="input" type="date" v-model="expCfg.to" @change="expCfg.preset='custom'" /></div>
          </div>
          <div class="hint" v-if="!expCfg.from && !expCfg.to">Ohne Angabe wird der gesamte Bestand ausgewertet.</div>
        </div>

        <div class="field">
          <label>Systeme ({{ expCount() }} ausgewählt)</label>
          <div class="exp-actions">
            <button class="btn btn-sm" @click="expSelectAll(true)">Alle</button>
            <button class="btn btn-sm" @click="expSelectAll(false)">Keins</button>
            <label class="check exp-inactive">
              <input type="checkbox" v-model="expCfg.includeInactive" />
              <span>Archivierte einbeziehen</span>
            </label>
          </div>
          <div class="exp-systems">
            <label v-for="s in systems.filter(x => expCfg.includeInactive || x.aktiv)" :key="s.id"
                   class="exp-sys" :class="{sel: expCfg.systemIds.includes(s.id)}">
              <input type="checkbox" :checked="expCfg.systemIds.includes(s.id)" @change="expToggleSystem(s.id)" />
              <span class="dot" :style="{background: s.farbe}"></span>
              <span class="exp-name">{{ typeIcon(s.typ) }} {{ s.name }}</span>
              <small v-if="!s.aktiv">archiviert</small>
            </label>
          </div>
        </div>

        <div class="field">
          <label>Datenquellen</label>
          <div class="exp-sources">
            <label v-for="s in expSourceOptions" :key="s.key" class="check exp-src"
                   :class="{sel: expCfg.sources.includes(s.key)}">
              <input type="checkbox" :checked="expCfg.sources.includes(s.key)"
                     @change="expToggleSource(s.key)" />
              <span>{{ s.label }}</span>
            </label>
          </div>
          <div class="hint" v-if="!expCfg.sources.length">
            Keine Auswahl bedeutet <strong>alle Quellen</strong>.
          </div>
          <div class="hint ks-note" v-else-if="expCfg.sources.length < expSourceOptions.length">
            Der Bericht enthält nur die gewählten Quellen. Verbrauch und Kosten werden
            aus den verbleibenden Ablesungen berechnet – bei Lücken fallen die Intervalle
            entsprechend länger aus.
          </div>
        </div>

        <div class="field">
          <label>Darstellung</label>
          <label class="check">
            <input type="checkbox" v-model="expCfg.useTheme" />
            <span>App-Farben übernehmen
              <small>Akzent, Text und Linien aus der aktiven Palette</small></span>
          </label>
          <div class="exp-swatches" v-if="expCfg.useTheme">
            <span v-for="(v,k) in expCfg.theme" :key="k" class="exp-sw" :title="k">
              <i :style="{background: v}"></i>{{ k }}
            </span>
          </div>
          <label class="check">
            <input type="checkbox" v-model="expCfg.systemColors" />
            <span>Diagramm je System in dessen Farbe
              <small>Sonst durchgehend Akzentfarbe</small></span>
          </label>
          <label class="check"><input type="checkbox" v-model="expCfg.includeChart" /><span>Diagramm einschließen</span></label>
          <label class="check"><input type="checkbox" v-model="expCfg.includeTable" /><span>Ablesungstabelle einschließen</span></label>
        </div>

        <div class="field">
          <label>Format</label>
          <div class="seg exp-seg">
            <button :class="{active: expCfg.format==='pdf'}"  @click="expCfg.format='pdf'">PDF-Bericht</button>
            <button :class="{active: expCfg.format==='csv'}"  @click="expCfg.format='csv'">CSV (Rohdaten)</button>
            <button :class="{active: expCfg.format==='json'}" @click="expCfg.format='json'">JSON (Rohdaten)</button>
            <button :class="{active: expCfg.format==='zip'}"  @click="expCfg.format='zip'">ZIP (Sicherung)</button>
          </div>

          <div class="hint ks-note" v-if="expCfg.format==='zip'">
            Sicherungsformat. Enthält immer den <strong>vollständigen</strong> Bestand –
            Zeitraum, Systemauswahl und Farben gelten dafür nicht. Nur dieses Format und
            die systemweise CSV lassen sich wieder <strong>einlesen</strong>.
          </div>
          <div class="hint ks-note" v-else-if="expCfg.format==='csv' || expCfg.format==='json'">
            Ausgabeformat für externe Auswertung, mit Verbrauch, Tagesverbrauch und Kosten.
            <strong>Nicht</strong> nach Zählwerk zurück importierbar – dafür ZIP verwenden.
          </div>

          <div class="field-row" v-if="expCfg.format==='csv'">
            <div class="field">
              <label>CSV-Variante</label>
              <div class="seg">
                <button :class="{active: expCfg.dialect==='de'}" @click="expCfg.dialect='de'">Excel (DE)</button>
                <button :class="{active: expCfg.dialect==='international'}" @click="expCfg.dialect='international'">pandas / R</button>
              </div>
              <div class="hint">
                {{ expCfg.dialect==='de'
                  ? 'Semikolon, Dezimalkomma, UTF-8 mit BOM – öffnet in Excel direkt korrekt.'
                  : 'Komma, Dezimalpunkt, ohne BOM.' }}
              </div>
            </div>
          </div>
          <div class="field" v-if="expCfg.format==='json'">
            <label class="check"><input type="checkbox" v-model="expCfg.includeDerived" />
              <span>Abgeleitete Werte einschließen
                <small>Verbrauch, Tagesverbrauch, Ausreißer, Kosten</small></span></label>
            <label class="check"><input type="checkbox" v-model="expCfg.includeMeta" />
              <span>Zähler-Metadaten und Tarife einschließen</span></label>
          </div>
        </div>

      </div>
      <div class="modal-foot">
        <button class="btn" @click="expCfg=null">Abbrechen</button>
        <button class="btn btn-primary" :disabled="!expCount()" @click="runExport">
          {{ expCfg.format==='zip' ? 'ZIP herunterladen' : 'PDF erstellen' }}
        </button>
      </div>
    </div>
  </div>

  <!-- MODAL: Wiederherstellung bestätigen -->
  <div class="overlay" v-if="restoreConfirm" @click.self="cancelRestore">
    <div class="modal">
      <div class="modal-head"><h3>Datenbank wiederherstellen</h3></div>
      <div class="modal-body">
        <p class="hint">
          Ersetzt die komplette Datenbank durch <code>{{ restoreConfirm.filename }}</code>.
          Der aktuelle Stand wird vorher automatisch gesichert, aber alle Änderungen
          seit dieser Sicherung gehen unwiderruflich verloren.
        </p>
        <div class="field">
          <label>Zum Bestätigen <code>RESTORE</code> eingeben</label>
          <input class="input" v-model="restoreConfirmText" autocomplete="off"
                 spellcheck="false" placeholder="RESTORE" @keydown.enter="confirmRestore" />
        </div>
      </div>
      <div class="modal-foot has-danger">
        <button class="btn" @click="cancelRestore">Abbrechen</button>
        <button class="btn btn-primary" :disabled="restoreConfirmText !== 'RESTORE' || !!restoreBusy"
                @click="confirmRestore">
          {{ restoreBusy ? 'Stelle wieder her …' : 'Wiederherstellen' }}</button>
      </div>
    </div>
  </div>

  <!-- MODAL: Versionsverlauf -->
  <div class="overlay" v-if="showChangelog" @click.self="showChangelog=false">
    <div class="modal">
      <div class="modal-head"><h3>Versionsverlauf</h3></div>
      <div class="modal-body">
        <div v-for="rel in changelog" :key="rel.v" class="rel">
          <div class="rel-head"><span class="rel-v num">v{{ rel.v }}</span><span class="rel-d">{{ rel.d }}</span></div>
          <ul class="rel-items"><li v-for="(it, i) in rel.items" :key="i">{{ it }}</li></ul>
        </div>
      </div>
      <div class="modal-foot"><button class="btn btn-primary" @click="showChangelog=false">Schließen</button></div>
    </div>
  </div>

  <!-- TOAST -->
  <div v-if="toast" class="toast" :class="toast.type">{{ toast.msg }}</div>
  `,
}).mount("#app");

/* ---------- M3 Ink-Ripple: geht physikalisch vom Beruehrungspunkt aus ---------- */
document.addEventListener("pointerdown", (ev) => {
  const host = ev.target.closest(".btn, .tab, .tile, .nav-item .nav-pill, .seg button, .fab, .iconbtn, .theme-opt");
  if (!host) return;
  const rect = host.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const ink = document.createElement("span");
  ink.className = "ripple-ink";
  ink.style.width = ink.style.height = size + "px";
  ink.style.left = (ev.clientX - rect.left - size / 2) + "px";
  ink.style.top = (ev.clientY - rect.top - size / 2) + "px";
  host.appendChild(ink);
  setTimeout(() => ink.remove(), 550);
}, { passive: true });
