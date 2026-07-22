"""Versionsverlauf als strukturierte Daten – eine Quelle für die Oberfläche
(Web-Header-Badge → Changelog-Dialog, iOS-Einstellungen).

Bewusst im Code statt in einer Markdown-Datei: so ist der Verlauf Teil des
ausgelieferten Images, unabhängig davon, ob das Repo mitgeliefert wird, und die
Einträge lassen sich typisiert über die API ausliefern. Neueste Version zuerst.
"""
from __future__ import annotations

from .version import APP_VERSION

# Jeder Eintrag: {"version", "date" (ISO), "title", "changes": [str, ...]}
CHANGELOG: list[dict] = [
    {
        "version": "3.28.0",
        "date": "2026-07-22",
        "title": "Wiederhergestellte Verwaltung: Systeme, Zähler, Dashboard, Update",
        "changes": [
            "Systemkonfiguration zurück: Zählertyp-Auswahl (inkl. Wärmepumpe), "
            "typabhängige Felder und Smart-Home-Masken (Home Assistant, MQTT/"
            "Tasmota/ESPHome, REST/HTTP) mit Live-Test.",
            "Neuer REST-/HTTP-Poller: Geräte mit hinterlegter URL (ESPHome "
            "web_server, Shelly) werden im festen Takt abgefragt.",
            "Systeme lassen sich bearbeiten, archivieren und löschen.",
            "Zähler-Metadaten (Hersteller, Nummer, Bauart, Eichfrist) verwaltbar.",
            "Dashboard mit frei anordenbaren Kacheln (Bearbeiten-Modus, 6 Typen).",
            "Selbst-Update mit Ladebalken und Schritt-Protokoll.",
            "Prominente Versionsanzeige und dieser Changelog in der Oberfläche.",
        ],
    },
    {
        "version": "3.27.0",
        "date": "2026-07-21",
        "title": "Gas-Umrechnung m³ → kWh",
        "changes": [
            "Gas-Systeme weisen zusätzlich kWh aus (Brennwert × Zustandszahl, "
            "je Zähler konfigurierbar) – in Ablesungen, Statistik und Diagramm.",
        ],
    },
    {
        "version": "3.26.0",
        "date": "2026-07-20",
        "title": "Oberfläche neu: React + Mantine",
        "changes": [
            "Vollständige Migration des Web-Frontends von Vue auf React/Mantine "
            "mit ECharts, Command-Palette und DB-Selektor.",
            "Neuer VBA-Standard-PDF-Übersichtsbericht (Strom/Gas/Wasser).",
            "Versionscheck funktioniert auch bei aktivem Offline-Modus.",
        ],
    },
    {
        "version": "3.25.0",
        "date": "2026-07-19",
        "title": "Mehrmandanten-Datenbanken & Rechte-Matrix",
        "changes": [
            "Pro Nutzer isolierte SQLite-Datenbanken mit Freigabe-Rollen.",
            "Session-Registry und Admin-Monitoring (aktive Sitzungen, Abmelden).",
        ],
    },
]

# Sicherheitsnetz: Die oberste Changelog-Version sollte der App-Version
# entsprechen. Läuft sie auseinander, ist das ein Hinweis auf einen vergessenen
# Eintrag – hier nur dokumentiert, kein harter Fehler.
LATEST_LOGGED = CHANGELOG[0]["version"] if CHANGELOG else None


def current_matches_changelog() -> bool:
    return LATEST_LOGGED == APP_VERSION
