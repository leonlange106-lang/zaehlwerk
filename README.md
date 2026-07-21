# Zählwerk (dezentral)

Verbrauchs- & Zählerstands-Tracking für Strom, Gas, Wasser und PV – als
**eigenständiger Dienst** (VM/LXC/Docker) mit einer **Home-Assistant-Integration**,
die HA an dieses Backend anbindet.

Dieses Repository ist die dezentrale Heimat von Zählwerk. Das bisherige
Home-Assistant-**Add-on** (`energy-tracker`) bleibt bestehen und lauffähig, bis
der dezentrale Betrieb erwiesen stabil ist.

## Aufbau

| Pfad | Inhalt |
|------|--------|
| `backend/` | Das Zählwerk-Backend (FastAPI · SQLModel · SQLite). Standalone lauffähig, HA-Kopplung optional. Hub-vorbereitet (Router je Werkzeug), damit weitere Dienste andocken können. |
| `custom_components/zaehlwerk/` | Die Home-Assistant-Custom-Integration mit Umschalter **HA-intern / Dezentral**. HACS-installierbar. |
| `deploy/` | Standalone-Betrieb: `docker-compose.yml` und der Proxmox-LXC-Leitfaden. |
| `docs/MIGRATION.md` | Umzug vom Add-on auf dezentral, ohne Datenverlust. |

## Schnellstart (Backend)

```sh
cd deploy
docker compose up -d --build
# Zählwerk läuft auf http://<host>:8000 – beim ersten Aufruf Admin-Konto anlegen
```

Details und Absicherung (Cloudflare Tunnel + Access): `deploy/PROXMOX_LXC.md`.

## Home-Assistant-Integration

Über HACS als Custom-Repository (Kategorie *Integration*) hinzufügen, dann in HA
*Einstellungen → Geräte & Dienste → Integration hinzufügen → Zählwerk*.

Im ersten Schritt den **Betriebsmodus** wählen:

- **HA-intern** – Zählwerk läuft noch als Add-on in dieser HA-Instanz.
- **Dezentral** – Zählwerk läuft ausgelagert; URL + Zugangsdaten (optional
  Cloudflare-Access-Service-Token) eintragen.

Beide Modi sprechen dieselbe REST-API. Der Schalter erlaubt einen sanften Umzug:
zuerst intern anbinden, nach dem Datenumzug auf dezentral umstellen – ohne die
Entitäten neu einzurichten.

## Status

Frühe Phase (`0.1.0`). Das Backend ist der erprobte Zählwerk-Stand aus dem
Add-on; die Integration und der dezentrale Betrieb werden hier aufgebaut und
stabilisiert, bevor das Add-on abgelöst wird.
