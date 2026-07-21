#!/usr/bin/env bash
# Zählwerk Host-Updater
# --------------------------------------------------------------------------
# Führt die vom Web-Dienst ANGEFORDERTEN Update-/Rollback-Vorgänge aus.
# Läuft als systemd-Timer auf dem LXC-Host (siehe *.service / *.timer).
#
# Sicherheitsmodell: die über Cloudflare erreichbare Web-App führt selbst NIE
# git oder docker aus. Sie legt nur eine Anforderungsdatei ab
# (control/request.json). Dieses Skript liest sie, sichert den aktuellen Stand
# (git-Commit + die DB-Sicherung, die die App vor dem Schreiben angelegt hat),
# führt den Vorgang aus und schreibt das Ergebnis nach control/status.json.
#
# Konfiguration über Umgebungsvariablen (siehe .service):
#   ZAEHLWERK_REPO_DIR     Pfad zum geklonten Repo   (Default: /root/zaehlwerk)
#   ZAEHLWERK_CONTROL_DIR  geteiltes Kontrollverzeichnis (Default: $REPO_DIR/control)
set -euo pipefail

REPO_DIR="${ZAEHLWERK_REPO_DIR:-/root/zaehlwerk}"
CONTROL_DIR="${ZAEHLWERK_CONTROL_DIR:-$REPO_DIR/control}"
COMPOSE="$REPO_DIR/deploy/docker-compose.yml"

REQ="$CONTROL_DIR/request.json"
STATUS="$CONTROL_DIR/status.json"
PREV="$CONTROL_DIR/previous_commit"
LOG="$CONTROL_DIR/updater.log"

mkdir -p "$CONTROL_DIR"
log() { echo "$(date -Is) $*" >> "$LOG"; }

# JSON-Status atomar schreiben:  write_status <action> <ok:true|false> <message> <from> <to>
write_status() {
  local tmp="$STATUS.part"
  printf '{"action":"%s","ok":%s,"message":"%s","from":"%s","to":"%s","finished_at":"%s"}\n' \
    "$1" "$2" "$3" "$4" "$5" "$(date -Is)" > "$tmp"
  mv "$tmp" "$STATUS"
}

# Nichts zu tun? Sofort raus (der Timer läuft häufig, die Arbeit ist selten).
[ -f "$REQ" ] || exit 0

action="$(python3 -c "import json;print(json.load(open('$REQ')).get('action',''))" 2>/dev/null || echo "")"
rm -f "$REQ"   # Anforderung sofort konsumieren, damit sie nicht doppelt läuft

cd "$REPO_DIR"
from_commit="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"

case "$action" in
  update)
    log "UPDATE angefordert (aktuell $from_commit)"
    git rev-parse HEAD > "$PREV"                    # für ein späteres Rollback merken
    if git fetch origin main \
       && git checkout main \
       && git reset --hard origin/main \
       && docker compose -f "$COMPOSE" up -d --build; then
      to="$(git rev-parse --short HEAD)"
      log "UPDATE erfolgreich: $from_commit -> $to"
      write_status "update" true "Update erfolgreich" "$from_commit" "$to"
    else
      log "UPDATE fehlgeschlagen"
      write_status "update" false "git pull oder docker build fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
    fi
    ;;

  rollback)
    log "ROLLBACK angefordert (aktuell $from_commit)"
    if [ -f "$PREV" ]; then
      target="$(cat "$PREV")"
      if git reset --hard "$target" \
         && docker compose -f "$COMPOSE" up -d --build; then
        to="$(git rev-parse --short HEAD)"
        log "ROLLBACK erfolgreich -> $to"
        write_status "rollback" true "Rollback erfolgreich" "$from_commit" "$to"
      else
        log "ROLLBACK fehlgeschlagen"
        write_status "rollback" false "Checkout oder Build fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
      fi
    else
      log "ROLLBACK ohne gemerkte Vorversion"
      write_status "rollback" false "Keine Vorversion gemerkt (noch kein Update ausgeführt)" "$from_commit" "$from_commit"
    fi
    ;;

  "")
    log "Leere/ungültige Anforderung ignoriert"
    ;;
  *)
    log "Unbekannte Aktion: $action"
    write_status "$action" false "Unbekannte Aktion" "$from_commit" "$from_commit"
    ;;
esac
