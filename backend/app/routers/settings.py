"""Einstellungen.

Bewusste Trennung, die sich aus dem Add-on-Modell ergibt:

* **Anwendungsparameter** (Benachrichtigungsintervall, Ausreißer-Sigma …)
  gehören der App und liegen in SQLite. Schreibbar über PUT /api/settings.
* **Laufzeit-/Containerparameter** (DB-Pfad, CORS, Port, Architektur) gehören
  dem Supervisor bzw. dem Image. Die App liefert sie ausschließlich LESEND
  über GET /api/system/info aus. Würde sie sie selbst ändern, liefe der
  Zustand gegen `config.yaml` auseinander und wäre nach jedem Add-on-Update
  wieder überschrieben.

Validierung passiert in den Pydantic-Schemas und damit VOR jedem Schreibzugriff:
FastAPI antwortet bei Regelverstoß mit 422 und Feldnamen, gespeichert wird nichts.
"""
import os
import platform
import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from .. import outbound
from ..config import settings as runtime_settings
from ..database import engine, get_session
from ..migrations import schema_version
from ..models import AppSetting, Meter, Reading, System
from ..schemas import AppSettingsRead, AppSettingsUpdate, SystemInfo
from ..version import APP_VERSION

router = APIRouter(tags=["settings"])

# Anwendungsparameter mit Standardwerten. Nur diese Schlüssel werden gelesen
# und geschrieben – unbekannte Keys in der Tabelle werden ignoriert.
DEFAULTS: dict[str, object] = {
    # Kill-Switch: Auslieferungszustand ist offline.
    "offline_mode": True,
    "notify_enabled": True,
    "notify_interval_hours": 6,
    "default_interval_days": 0,
    "outlier_sigma": 2.0,
    # Automatische Sicherung
    "backup_enabled": True,
    "backup_time": "03:30",
    "backup_keep_days": 7,
    # MQTT. Der Supervisor liefert die Zugangsdaten, wenn Mosquitto laeuft -
    # dann bleiben Host/Benutzer/Passwort hier leer.
    "mqtt_enabled": False,
    "mqtt_use_supervisor": True,
    "mqtt_host": "",
    "mqtt_port": 1883,
    "mqtt_username": "",
    "mqtt_password": "",
    "mqtt_base_topic": "tele",
    "mqtt_tasmota_discovery": False,
    # Globale Vorgabe; je System über zusatzfelder["mqtt_interval"] übersteuerbar.
    "mqtt_interval": "daily",
    # Watchdog: meldet über persistent_notification, wenn ein per MQTT
    # angebundenes System zu lange keinen neuen Wert geliefert hat.
    "mqtt_watchdog_enabled": True,
    "mqtt_watchdog_hours": 48,
    # REST-Poller: fragt Systeme mit hinterlegter zusatzfelder["rest_url"] im
    # festen Takt ab (ESPHome web_server, Shelly, generische JSON-Endpunkte).
    "rest_poll_enabled": True,
    "rest_poll_minutes": 15,
    # Rolle für neu übernommene Home-Assistant-Konten.
    "default_role": "writer",
    # Aufbewahrung des Änderungsprotokolls. Untergrenze 30 Tage, weil der
    # Trigger jüngere Einträge ohnehin schützt.
    "audit_keep_days": 365,
    # Aufbewahrung hochfrequenter MQTT-Telemetrie in voller Auflösung, in Tagen.
    # 0 = unbegrenzt (nichts wird reduziert). Ist der Wert > 0, werden ältere
    # MQTT-Ablesungen im täglichen Lauf auf einen Datensatz je Monat verdünnt;
    # von Hand erfasste, importierte oder aus HA übernommene Werte bleiben immer
    # unangetastet. Da Zählerstände kumulativ sind, bleiben Gesamtverbräuche
    # dabei exakt erhalten – nur die zeitliche Auflösung alter Telemetrie sinkt.
    "telemetry_keep_days": 0,
}

_BOOL = lambda v: str(v).lower() in {"1", "true", "ja", "yes"}  # noqa: E731

_CASTS = {
    "offline_mode": _BOOL,
    "notify_enabled": lambda v: str(v).lower() in {"1", "true", "ja", "yes"},
    "notify_interval_hours": int,
    "default_interval_days": int,
    "outlier_sigma": float,
    "backup_enabled": _BOOL,
    "backup_time": str,
    "backup_keep_days": int,
    "mqtt_enabled": _BOOL,
    "mqtt_use_supervisor": _BOOL,
    "mqtt_host": str,
    "mqtt_port": int,
    "mqtt_username": str,
    "mqtt_password": str,
    "mqtt_base_topic": str,
    "mqtt_tasmota_discovery": _BOOL,
    "mqtt_interval": str,
    "mqtt_watchdog_enabled": _BOOL,
    "mqtt_watchdog_hours": int,
    "rest_poll_enabled": _BOOL,
    "rest_poll_minutes": int,
    "default_role": str,
    "audit_keep_days": int,
    "telemetry_keep_days": int,
}

# Diese Schluessel verlassen den Server NIE im Klartext. Die Leseantwort meldet
# nur, OB ein Wert gesetzt ist.
SECRET_KEYS = {"mqtt_password"}


def read_settings(session: Session) -> dict:
    """Gespeicherte Werte über die Defaults legen. Defekte Einträge fallen
    auf den Standard zurück, statt die App beim Start scheitern zu lassen."""
    values = dict(DEFAULTS)
    for row in session.exec(select(AppSetting)).all():
        if row.key not in DEFAULTS:
            continue
        try:
            values[row.key] = _CASTS[row.key](row.value)
        except (TypeError, ValueError):
            pass
    return values


def get_setting(key: str, default=None):
    """Einzelwert außerhalb eines Request-Kontexts (z. B. im Notifier-Loop)."""
    with Session(engine) as session:
        return read_settings(session).get(key, default)


def _redacted(values: dict) -> dict:
    """Geheimnisse durch ein Ja/Nein ersetzen, bevor etwas den Server verlaesst."""
    out = {k: v for k, v in values.items() if k not in SECRET_KEYS}
    out["mqtt_password_set"] = bool(values.get("mqtt_password"))
    return out


@router.get("/api/settings", response_model=AppSettingsRead)
def get_settings(session: Session = Depends(get_session)):
    return AppSettingsRead(**_redacted(read_settings(session)))


@router.put("/api/settings", response_model=AppSettingsRead)
def update_settings(payload: AppSettingsUpdate, session: Session = Depends(get_session)):
    """Teil-Update. Die Validierung hat bereits stattgefunden, wenn dieser
    Rumpf läuft – ungültige Werte erreichen die Datenbank nie."""
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key not in DEFAULTS:
            continue
        row = session.get(AppSetting, key)
        raw = "true" if value is True else "false" if value is False else str(value)
        if row:
            row.value = raw
        else:
            row = AppSetting(key=key, value=raw)
        session.add(row)
    session.commit()
    values = read_settings(session)
    # Modulweite Flagge sofort nachziehen, sonst greift der Socket-Guard erst
    # nach einem Neustart.
    outbound.set_offline(bool(values.get("offline_mode", True)))
    # MQTT-Verbindung an den neuen Stand anpassen, ohne Add-on-Neustart
    try:
        from .. import mqtt_client
        if values.get("mqtt_enabled"):
            mqtt_client.start(values)
        else:
            mqtt_client.stop()
    except Exception:  # noqa: BLE001
        pass
    return AppSettingsRead(**_redacted(values))


@router.get("/api/changelog")
def changelog():
    """Versionsverlauf für die Oberfläche (aktuelle Version + Einträge)."""
    from ..changelog import CHANGELOG
    return {"current": APP_VERSION, "entries": CHANGELOG}


@router.get("/api/system/info", response_model=SystemInfo)
def system_info(session: Session = Depends(get_session)):
    """Read-only Diagnose. Enthält bewusst keine Tokens oder URLs."""
    db_path = Path(runtime_settings.sqlite_path)
    size = 0
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            size += p.stat().st_size

    with engine.connect() as conn:
        from sqlalchemy import text
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = bool(conn.execute(text("PRAGMA foreign_keys")).scalar())

    supervised = bool(os.environ.get("SUPERVISOR_TOKEN"))
    return SystemInfo(
        app_version=os.environ.get("ZW_VERSION", APP_VERSION),
        schema_version=schema_version(engine),
        python_version=sys.version.split()[0],
        platform=platform.machine(),
        db_path=str(db_path),
        db_exists=db_path.exists(),
        db_size_bytes=size,
        journal_mode=str(journal),
        foreign_keys=fk,
        runtime="Home Assistant Add-on" if supervised else "Standalone (Docker/lokal)",
        supervisor_available=supervised,
        offline_mode=outbound.is_offline(),
        socket_guard_active=outbound._guard_installed,
        system_count=session.exec(select(func.count()).select_from(System)).one(),
        reading_count=session.exec(select(func.count()).select_from(Reading)).one(),
        meter_count=session.exec(select(func.count()).select_from(Meter)).one(),
    )
