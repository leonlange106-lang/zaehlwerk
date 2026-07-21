# Zählwerk dezentral auf Proxmox (LXC)

Empfehlung aus dem Architektur-Review: **LXC statt VM**. Für einen
Python/SQLite-Dienst ist ein Debian-LXC deutlich leichter als eine vollwertige
VM; eine VM lohnt nur bei Kernel-Isolation oder GPU-Passthrough – hier nicht
nötig.

## 1. Container anlegen

- Debian-12-LXC (unprivileged genügt), 2 vCPU / 1 GB RAM / 8 GB Disk als Start.
- Docker im LXC: bei unprivileged Containern `keyctl`/`nesting` in den Optionen
  aktivieren (`Options → Features: nesting=1, keyctl=1`).

## 2. Zählwerk starten

```sh
apt update && apt install -y docker.io docker-compose-plugin git
git clone https://github.com/leonlange106-lang/zaehlwerk.git
cd zaehlwerk/deploy
docker compose up -d --build
```

Zählwerk lauscht dann auf `http://<lxc-ip>:8000`. Beim ersten Aufruf wird das
Admin-Konto angelegt (Ersteinrichtung).

## 3. Absicherung (Zugriff von außen / iOS)

Kein Portforwarding. Stattdessen ein **Cloudflare Tunnel** (`cloudflared`) mit
**Cloudflare Access** davor – siehe Architektur-Review, Abschnitt 04:

- Tunnel macht die Origin erreichbar, ohne eingehende Firewall-Öffnung.
- Access setzt die Identitätsschicht davor (Service-Token oder mTLS), bevor
  eine Anfrage die Origin erreicht.
- Die HA-Integration kann den Service-Token als `CF-Access-Client-Id` /
  `CF-Access-Client-Secret` mitschicken (im Config-Flow, Modus „dezentral").

## 4. Sicherung

Ohne HA-Backup braucht der LXC eine eigene Sicherungskette:

- Zählwerks eingebautes Backup-Modul (Einstellungen → Datensicherung), **plus**
- Proxmox-Snapshots/`vzdump` des Containers.

## 5. MQTT (optional)

Läuft der MQTT-Broker weiter unter HA, trägt man Host/Port/Zugang in Zählwerk
manuell ein (Einstellungen → MQTT). Die Supervisor-Durchreichung entfällt im
dezentralen Betrieb – das ist erwartet und wird in der Oberfläche so
ausgewiesen.
