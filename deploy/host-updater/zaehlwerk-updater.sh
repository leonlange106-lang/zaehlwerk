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
PROGRESS="$CONTROL_DIR/progress.json"
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

# Fortschritt mit Schritt-Protokoll atomar schreiben. Die Schritte werden über
# Läufe hinweg akkumuliert (Python liest die bisherige Datei und hängt an), damit
# die Oberfläche einen fortlaufenden Ladebalken + Log zeigen kann.
#   write_progress <action> <running:true|false> <percent> <phase> <message>
PROGRESS_ACTION=""
write_progress() {
  PROGRESS_ACTION="$1"
  ACTION="$1" RUNNING="$2" PERCENT="$3" PHASE="$4" MESSAGE="$5" PFILE="$PROGRESS" \
  python3 - <<'PY' || true
import json, os, datetime
pfile = os.environ["PFILE"]
try:
    prev = json.load(open(pfile))
    steps = prev.get("steps", []) if isinstance(prev, dict) else []
except Exception:
    steps = []
ok = None
running = os.environ["RUNNING"] == "true"
phase = os.environ["PHASE"]
if phase == "done":
    ok = True
elif phase == "failed":
    ok = False
steps.append({"phase": phase, "ok": ok, "message": os.environ["MESSAGE"]})
out = {
    "action": os.environ["ACTION"], "running": running,
    "percent": int(os.environ["PERCENT"]), "phase": phase,
    "message": os.environ["MESSAGE"], "steps": steps,
    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
tmp = pfile + ".part"
json.dump(out, open(tmp, "w"), ensure_ascii=False)
os.replace(tmp, pfile)
PY
}
# Frischen Fortschritt beginnen (verwirft Schritte des vorigen Laufs).
reset_progress() { rm -f "$PROGRESS"; }

# Nichts zu tun? Sofort raus (der Timer läuft häufig, die Arbeit ist selten).
[ -f "$REQ" ] || exit 0

action="$(python3 -c "import json;print(json.load(open('$REQ')).get('action',''))" 2>/dev/null || echo "")"
rm -f "$REQ"   # Anforderung sofort konsumieren, damit sie nicht doppelt läuft

cd "$REPO_DIR"
from_commit="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"

case "$action" in
  update)
    log "UPDATE angefordert (aktuell $from_commit)"
    reset_progress
    write_progress "update" true 10 "start" "Update gestartet (aktuell $from_commit)"
    git rev-parse HEAD > "$PREV"                    # für ein späteres Rollback merken
    write_progress "update" true 30 "download" "Neue Version wird geladen (git fetch)"
    if git fetch origin main && git checkout main && git reset --hard origin/main; then
      write_progress "update" true 60 "install" "Download fertig – Docker-Image wird gebaut"
      if docker compose -f "$COMPOSE" up -d --build; then
        to="$(git rev-parse --short HEAD)"
        log "UPDATE erfolgreich: $from_commit -> $to"
        write_progress "update" false 100 "done" "Update erfolgreich: $from_commit -> $to"
        write_status "update" true "Update erfolgreich" "$from_commit" "$to"
      else
        log "UPDATE fehlgeschlagen (build)"
        write_progress "update" false 100 "failed" "Docker-Build fehlgeschlagen – siehe updater.log"
        write_status "update" false "docker build fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
      fi
    else
      log "UPDATE fehlgeschlagen (fetch)"
      write_progress "update" false 100 "failed" "git fetch/reset fehlgeschlagen – siehe updater.log"
      write_status "update" false "git pull fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
    fi
    ;;

  rollback)
    log "ROLLBACK angefordert (aktuell $from_commit)"
    reset_progress
    write_progress "rollback" true 10 "start" "Rollback gestartet (aktuell $from_commit)"
    if [ -f "$PREV" ]; then
      target="$(cat "$PREV")"
      write_progress "rollback" true 40 "download" "Vorversion wird ausgecheckt"
      if git reset --hard "$target"; then
        write_progress "rollback" true 60 "install" "Docker-Image wird gebaut"
        if docker compose -f "$COMPOSE" up -d --build; then
          to="$(git rev-parse --short HEAD)"
          log "ROLLBACK erfolgreich -> $to"
          write_progress "rollback" false 100 "done" "Rollback erfolgreich -> $to"
          write_status "rollback" true "Rollback erfolgreich" "$from_commit" "$to"
        else
          log "ROLLBACK fehlgeschlagen (build)"
          write_progress "rollback" false 100 "failed" "Docker-Build fehlgeschlagen – siehe updater.log"
          write_status "rollback" false "Build fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
        fi
      else
        log "ROLLBACK fehlgeschlagen (checkout)"
        write_progress "rollback" false 100 "failed" "Checkout fehlgeschlagen – siehe updater.log"
        write_status "rollback" false "Checkout fehlgeschlagen - siehe updater.log" "$from_commit" "$from_commit"
      fi
    else
      log "ROLLBACK ohne gemerkte Vorversion"
      write_progress "rollback" false 100 "failed" "Keine Vorversion gemerkt"
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
