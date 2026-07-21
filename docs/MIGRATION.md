# Umzug: Add-on → dezentral (ohne Datenverlust)

Ziel: Zählwerk läuft künftig eigenständig (VM/LXC), Home Assistant greift über
die Custom-Integration darauf zu. Das **bestehende Add-on bleibt bis zum
erfolgreichen Umzug unangetastet** – erst abschalten, wenn dezentral bewiesen
läuft.

## Reihenfolge

1. **Dezentrales Backend starten** – siehe `deploy/PROXMOX_LXC.md`. Beim ersten
   Start ein Admin-Konto anlegen (oder unten die Alt-DB übernehmen).
2. **Daten übernehmen.** Zwei Wege:
   - **Backup/Restore (empfohlen):** im Add-on ein Backup ziehen (Einstellungen
     → Datensicherung), im dezentralen Zählwerk wiederherstellen.
   - **DB-Datei kopieren:** die SQLite-Datei des Add-ons liegt unter
     `/config/zaehlwerk.db` (im HA-Backup enthalten). Sie in das Daten-Volume
     des Containers legen (`SQLITE_PATH`, z. B. `/data/zaehlwerk.db`) – WAL-
     Sidecars (`-wal`, `-shm`) mitnehmen, falls vorhanden. Das Backend migriert
     Alt-Schemata beim Start automatisch.
3. **Integration einrichten.** In HA: *Einstellungen → Geräte & Dienste →
   Integration hinzufügen → Zählwerk*. Modus **dezentral** wählen, URL +
   Zugangsdaten (ggf. Cloudflare-Access-Token) eintragen.
4. **Parallelbetrieb prüfen.** Beide laufen lassen, Werte vergleichen. Erst wenn
   die dezentrale Instanz vollständig stimmt und gesichert ist:
5. **Add-on abschalten** (nicht sofort deinstallieren – als Rückfallebene
   behalten, bis der dezentrale Betrieb über mehrere Abrechnungszyklen trägt).

## Der Umschalter HA-intern / Dezentral

Die Integration kennt beide Modi. Für einen sanften Übergang kann sie zuerst im
Modus **HA-intern** gegen das noch laufende Add-on eingerichtet werden und
später – nach dem Datenumzug – auf **dezentral** umgestellt werden. Beide Modi
sprechen dieselbe REST-API; nur URL/Zugang (und optional die Cloudflare-Header)
ändern sich.

> Hinweis: HA-**Add-on** und HA-**Custom-Integration** sind zwei verschiedene
> Erweiterungstypen. Das Add-on bleibt das Add-on; die Integration ist das neue,
> dauerhafte Bindeglied zwischen HA und Zählwerk – unabhängig davon, wo das
> Backend läuft.
