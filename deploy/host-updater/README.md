# Selbst-Update & Rollback (dezentral) — einmalige Einrichtung

Der Update-Tab in Zählwerk (Admin-Tools → Update) prüft GitHub auf neue
Versionen und stößt Update/Rollback an. **Ausgeführt** wird beides von einem
kleinen Host-Skript per systemd-Timer — die über Cloudflare erreichbare Web-App
führt selbst nie `git` oder `docker` aus (kleinstmögliche Angriffsfläche).

Ohne die folgende Einrichtung ist der Update-Tab schlicht ausgeblendet
(`supported = false`) — alle anderen Funktionen laufen unverändert.

## Voraussetzung

Das Repo ist auf dem LXC-Host geklont (der Pfad im Beispiel: `/root/zaehlwerk`)
und läuft über `deploy/docker-compose.yml`. Passe die Pfade unten an, falls dein
Klon woanders liegt.

## 1. Kontrollverzeichnis anlegen

Die `docker-compose.yml` bindet bereits `../control` in den Container als
`/control` ein. Anlegen und Container neu starten, damit der Mount greift:

```sh
cd /root/zaehlwerk
mkdir -p control
cd deploy && docker compose up -d          # übernimmt den neuen Bind-Mount
```

## 2. Host-Skript + systemd-Timer installieren

```sh
cd /root/zaehlwerk/deploy/host-updater
chmod +x zaehlwerk-updater.sh

# Pfade in der .service prüfen (ZAEHLWERK_REPO_DIR / _CONTROL_DIR), falls dein
# Klon nicht unter /root/zaehlwerk liegt.
cp zaehlwerk-updater.service /etc/systemd/system/
cp zaehlwerk-updater.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now zaehlwerk-updater.timer
```

Prüfen:
```sh
systemctl status zaehlwerk-updater.timer
```

## 3. Fertig

Im Update-Tab erscheint jetzt die installierte vs. verfügbare Version. „Update
jetzt ausführen" bzw. „Auf vorherige Version zurücksetzen" legt eine Anforderung
in `control/request.json` ab; der Timer arbeitet sie binnen ~1 Minute ab
(`git reset --hard origin/main` + `docker compose up -d --build`) und schreibt
das Ergebnis nach `control/status.json`, das der Tab wieder anzeigt.

## Sicherheitsnetz

- **Vor jedem Update** erzeugt die App automatisch eine Datenbank-Sicherung
  (in `/data/backups`, persistent).
- **Code-Rollback**: das Skript merkt sich vor dem Update den git-Commit
  (`control/previous_commit`) und stellt ihn beim Rollback wieder her.
- **Internetzugriff**: die Versionsprüfung braucht deaktivierten Offline-Modus
  (Admin-Tools → System → Internetzugriff). Der Update-Trigger selbst funktioniert
  auch offline — er schreibt nur eine lokale Datei.

## Diagnose

- Log des Host-Skripts: `control/updater.log`
- Letztes Ergebnis: `control/status.json`
- Timer-Läufe: `journalctl -u zaehlwerk-updater.service`
