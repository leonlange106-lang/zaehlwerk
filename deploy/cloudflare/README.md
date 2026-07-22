# Zählwerk hinter Cloudflare Tunnel + Access (TICKET-5.1)

Macht die Instanz sicher aus dem Internet erreichbar (z. B. für die iOS-App
unterwegs), ohne einen Port zu öffnen. Cloudflare Access übernimmt die
Identitätsprüfung; Zählwerk validiert das Access-JWT zusätzlich serverseitig.

## 1. Tunnel einrichten (auf dem LXC-Host)

```bash
cloudflared tunnel login
cloudflared tunnel create zaehlwerk
# UUID + credentials-file merken
cp deploy/cloudflare/config.example.yml /etc/cloudflared/config.yml
# Platzhalter (<TUNNEL-UUID>, hostname) ersetzen
cloudflared tunnel route dns zaehlwerk zaehlwerk.example.com
systemctl enable --now cloudflared
```

Zählwerk selbst bleibt auf `127.0.0.1:8000` (docker-compose Port-Binding auf
localhost beschränken).

## 2. Cloudflare Access-Anwendung anlegen (Dashboard)

- **Zero Trust → Access → Applications → Add application → Self-hosted**
- Domain: `zaehlwerk.example.com`
- Richtlinien nach Bedarf (E-Mail-OTP, IdP, Gerätezustand …).
- **Application Audience (AUD) Tag** notieren – der lange Hex-String.
- Für die iOS-App: **Service Auth → Service Token** erstellen und eine
  zusätzliche Richtlinie „Service Auth" mit diesem Token hinzufügen. Client-Id
  und Client-Secret in der App unter „Cloudflare Access" hinterlegen.

## 3. Serverseitige JWT-Validierung aktivieren

Als Umgebungsvariablen des Backends (docker-compose `environment:`):

```yaml
environment:
  CF_ACCESS_TEAM_DOMAIN: "meinteam"          # oder meinteam.cloudflareaccess.com
  CF_ACCESS_AUD: "<Application-Audience-Tag>"
```

Sind beide gesetzt, weist Zählwerk jede `/api`-Anfrage OHNE gültiges
`Cf-Access-Jwt-Assertion` mit **403** ab (Ausnahme: `/api/health`). Fehlen die
Variablen, ist die Prüfung inaktiv (unveränderter lokaler/HA-Betrieb).

> Hinweis: Die Validierung lädt die Cloudflare-Public-Keys von
> `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`. Das ist ein
> Online-Feature – bei aktivem Offline-Kill-Switch schlägt sie bewusst fehl
> (wer öffentlich exponiert, ist ohnehin online).

## iOS

Server-Adresse + optional die Service-Token-Zugangsdaten (Client-Id/Secret)
werden im Verbindungsdialog eingegeben und im Schlüsselbund abgelegt; der
`APIClient` sendet sie als `CF-Access-Client-Id` / `CF-Access-Client-Secret`.
Cloudflare wandelt sie am Rand in das Access-JWT um.
