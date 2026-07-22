"""Update-Prüfung und -Auslösung für den dezentralen (Standalone-)Betrieb.

**Sicherheitsmodell.** Die Web-App führt **niemals selbst** git oder docker aus.
Sie tut nur zweierlei:

1. Sie prüft gegen GitHub, welche Version im Repo steht (nur lesend, über das
   Anwendungs-Gate `outbound.fetch_json`).
2. Sie legt im **Kontrollverzeichnis** eine Anforderungsdatei ab
   (`request.json`).

Das eigentliche Update bzw. Rollback führt ein **separates Host-Skript**
(systemd-Timer auf dem LXC) aus: es liest die Anforderung, sichert den aktuellen
Stand, führt `git pull` + `docker compose up -d --build` bzw. den Checkout der
Vorversion aus und schreibt das Ergebnis nach `status.json` zurück. Damit hat
der über Cloudflare erreichbare Webdienst zu keinem Zeitpunkt die Fähigkeit,
Host-Befehle auszuführen – die kleinstmögliche Angriffsfläche.

**Unter Home Assistant** ist das Modul inaktiv: dort kommen Updates über den
Add-on-Store, ein git-basierter Selbst-Update-Weg wäre dort falsch. Erkannt wird
das an `auth.ingress_mode()` sowie am Fehlen des Kontrollverzeichnisses.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import outbound
from .version import APP_VERSION

log = logging.getLogger("zaehlwerk.updater")

CONTROL_DIR_ENV = "ZAEHLWERK_CONTROL_DIR"
REQUEST_FILE = "request.json"
STATUS_FILE = "status.json"

# Intervall der Hintergrundprüfung. Bewusst großzügig: neue Releases erscheinen
# nicht im Minutentakt, und die GitHub-API hat unangemeldet ein Limit von 60
# Anfragen pro Stunde und IP.
CHECK_INTERVAL_SECONDS = 6 * 3600

_latest: dict = {"version": None, "checked_at": 0.0, "error": None}


# --------------------------------------------------------------------------
# Umgebung
# --------------------------------------------------------------------------
def control_dir() -> Optional[Path]:
    """Das mit dem Host geteilte Kontrollverzeichnis, falls eingerichtet."""
    raw = os.environ.get(CONTROL_DIR_ENV)
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() else None


def supported() -> bool:
    """Selbst-Update nur im Standalone-Betrieb mit eingerichtetem Host-Skript."""
    from . import auth
    return not auth.ingress_mode() and control_dir() is not None


# --------------------------------------------------------------------------
# Versionsvergleich
# --------------------------------------------------------------------------
def _vtuple(v: Optional[str]) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4]) if v else ()


def _is_newer(remote: Optional[str], local: str) -> bool:
    r, l = _vtuple(remote), _vtuple(local)
    return bool(r) and r > l


def check_latest(force: bool = False) -> dict:
    """Neueste Version aus dem Repo lesen (gecacht). Wirft nie – Fehler landen
    im Ergebnis, damit die Oberfläche sie anzeigen kann, statt zu scheitern."""
    now = time.time()
    if not force and _latest["version"] and (now - _latest["checked_at"] < CHECK_INTERVAL_SECONDS):
        return dict(_latest)
    try:
        # allow_offline: der Versionscheck darf seine fest verdrahtete, auf der
        # Allowlist stehende GitHub-URL auch im Offline-Modus erreichen – sonst
        # wäre der Update-Tab bei aktivem Kill-Switch dauerhaft funktionslos.
        data = outbound.fetch_json("github_version", {"ref": "main"}, allow_offline=True)
        content = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
        if not m:
            raise ValueError("Versionszeile nicht gefunden")
        _latest.update(version=m.group(1), checked_at=now, error=None)
        log.info("Versionsprüfung: Repo=%s, lokal=%s", m.group(1), APP_VERSION)
    except Exception as exc:  # noqa: BLE001 – jede Ursache wird als Text gemeldet
        _latest.update(checked_at=now, error=str(exc))
        log.warning("Versionsprüfung fehlgeschlagen: %s", exc)
    return dict(_latest)


async def check_scheduler() -> None:
    """Hintergrundprüfung in festem Intervall (nur wo Selbst-Update greift)."""
    import asyncio
    while True:
        if supported():
            try:
                check_latest(force=True)
            except Exception:  # noqa: BLE001
                pass
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


# --------------------------------------------------------------------------
# Kontrolldateien
# --------------------------------------------------------------------------
def _read_json(name: str) -> Optional[dict]:
    d = control_dir()
    if not d:
        return None
    path = d / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except (ValueError, OSError):
        return None


def last_status() -> Optional[dict]:
    """Ergebnis des letzten vom Host ausgeführten Vorgangs."""
    return _read_json(STATUS_FILE)


def pending_request() -> Optional[dict]:
    """Eine noch nicht vom Host abgearbeitete Anforderung, falls vorhanden."""
    return _read_json(REQUEST_FILE)


def status() -> dict:
    latest = check_latest(force=False)
    return {
        "supported": supported(),
        "current": APP_VERSION,
        "latest": latest.get("version"),
        "update_available": _is_newer(latest.get("version"), APP_VERSION),
        "checked_at": (datetime.fromtimestamp(latest["checked_at"], timezone.utc).isoformat()
                       if latest.get("checked_at") else None),
        "check_error": latest.get("error"),
        "pending": pending_request(),
        "last_action": last_status(),
    }


def request_action(action: str, actor: Optional[str] = None) -> dict:
    """Eine Update-/Rollback-Anforderung im Kontrollverzeichnis ablegen.

    Vor einem Update wird zusätzlich eine Datenbank-Sicherung erzeugt – schlägt
    die fehl, wird die Anforderung NICHT geschrieben (kein Update ohne
    Sicherheitsnetz). Das Code-Rollback selbst leistet das Host-Skript über den
    zuvor gemerkten git-Stand.
    """
    if action not in ("update", "rollback"):
        raise ValueError("Ungültige Aktion")
    d = control_dir()
    if not d:
        raise RuntimeError("Kein Kontrollverzeichnis eingerichtet – Selbst-Update nicht verfügbar")

    safety_backup = None
    if action == "update":
        from . import backup as bk
        safety_backup = bk.create_backup().get("file")

    payload = {
        "action": action,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": actor,
        "from_version": APP_VERSION,
        "safety_backup": safety_backup,
    }
    tmp = d / (REQUEST_FILE + ".part")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
    tmp.replace(d / REQUEST_FILE)          # atomar sichtbar machen
    log.warning("%s angefordert von %s (Sicherung: %s)", action, actor, safety_backup)
    return payload
