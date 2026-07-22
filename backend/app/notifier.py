"""Überfälligkeits-Benachrichtigungen nach Home Assistant (persistent_notification).
Feste notification_id pro System -> ersetzt sich selbst statt zu spammen; wird
automatisch entfernt, sobald wieder abgelesen wurde. Läuft alle 6 h."""
import asyncio
import json
import os
import urllib.request
from datetime import datetime

from sqlmodel import Session, select

from .database import engine
from .due import system_due_entries


def _ha_service(path: str, payload: dict) -> None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return
    req = urllib.request.Request(
        f"http://supervisor/core/api/services/{path}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def check_and_notify() -> None:
    with Session(engine) as session:
        for e in system_due_entries(session):
            s = e["system"]
            od = e.get("overdue_days")
            nid = f"zaehlwerk_due_{s.id}"
            if od is not None and od > 0:
                span = f"{round(od / 30)} Monaten" if od >= 60 else f"{od} Tagen"
                _ha_service("persistent_notification/create", {
                    "notification_id": nid,
                    "title": f"Zählwerk: {s.name} ablesen",
                    "message": (
                        f"Die Ablesung für \u201e{s.name}\u201c ist seit {span} überfällig "
                        f"(letzter Stand {e['value']:g} {s.einheit} am {e['datum'].strftime('%d.%m.%Y')})."
                    ),
                })
            else:
                try:
                    _ha_service("persistent_notification/dismiss", {"notification_id": nid})
                except Exception:  # noqa: BLE001
                    pass


# Mindest-Kulanz je Speicherintervall, bevor Funkstille als Ausfall gilt.
# Ohne diesen Faktor meldete ein System mit Speicherintervall "wöchentlich"
# jede Woche fälschlich einen toten Sensor - es schreibt ja per Design nur
# einmal je Periode einen Datensatz, MQTT-Nachrichten selbst werden dabei
# nicht mitgezählt (die würden das eigentliche Ziel - weniger Zeilen -
# wieder aufheben). Das 1,5-fache der Periode als Untergrenze lässt Spielraum
# für einen leicht verspäteten, aber noch gesunden Sensor.
INTERVAL_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 91, "yearly": 365}


def _mqtt_watchdog_threshold_hours(interval: str, base_hours: int) -> float:
    days = INTERVAL_DAYS.get(interval, 1)
    return max(base_hours, days * 24 * 1.5)


def check_mqtt_watchdog(base_hours: int = 48) -> None:
    """Meldet MQTT-Systeme, die seit der Schwelle keinen neuen Wert geliefert
    haben. Bewusst nur MQTT: Werte über eine Home-Assistant-Entity kommen erst
    zustande, wenn jemand die App öffnet und den Wert übernimmt - Stille dort
    heißt "niemand hat abgelesen", nicht "Sensor tot", und ist bereits über
    die reguläre Fälligkeits-Benachrichtigung abgedeckt.

    Systeme ohne bisherige MQTT-Ablesung werden übersprungen: ohne einen
    ersten empfangenen Wert gibt es keine Basis, ab der "Stille" beginnt, und
    ein frisch eingerichtetes System hätte sonst sofort Alarm geschlagen.
    """
    from .models import Reading, System
    from .mqtt_client import DEFAULT_INTERVAL, _interval_for

    now = datetime.utcnow()
    with Session(engine) as session:
        systems = session.exec(select(System).where(System.aktiv == True)).all()  # noqa: E712
        for s in systems:
            if not (s.zusatzfelder or {}).get("mqtt_topic"):
                continue
            nid = f"zaehlwerk_mqtt_dead_{s.id}"
            last = session.exec(
                select(Reading)
                .where(Reading.system_id == s.id, Reading.source == "mqtt")
                .order_by(Reading.datum.desc())
            ).first()
            if last is None:
                continue
            age_hours = (now - last.datum).total_seconds() / 3600
            threshold = _mqtt_watchdog_threshold_hours(
                _interval_for(s, DEFAULT_INTERVAL), base_hours)
            if age_hours > threshold:
                _ha_service("persistent_notification/create", {
                    "notification_id": nid,
                    "title": f"Zählwerk: {s.name} sendet nicht mehr",
                    "message": (
                        f"Seit {age_hours / 24:.1f} Tagen ist über MQTT kein neuer Wert für "
                        f"„{s.name}“ eingegangen. Sensor, Gerät und Broker-Verbindung prüfen."
                    ),
                })
            else:
                try:
                    _ha_service("persistent_notification/dismiss", {"notification_id": nid})
                except Exception:  # noqa: BLE001
                    pass


def check_contract_endings(within_days: int = 30) -> None:
    """Meldet Verträge, deren Kündigungstermin (gueltig_bis − Kündigungsfrist)
    innerhalb des Vorlaufs liegt – rechtzeitig, um noch kündigen zu können.
    Feste notification_id je Tarif ersetzt sich selbst statt zu spammen."""
    from datetime import date, timedelta

    from .models import System, Tariff

    today = date.today()
    with Session(engine) as session:
        rows = session.exec(
            select(Tariff, System).join(System, System.id == Tariff.system_id)
            .where(Tariff.gueltig_bis.is_not(None), Tariff.notice_period_days.is_not(None))
        ).all()
        for t, s in rows:
            deadline = t.gueltig_bis - timedelta(days=t.notice_period_days or 0)
            days = (deadline - today).days
            nid = f"zaehlwerk_contract_{t.id}"
            if 0 <= days <= within_days:
                label = t.name or s.name
                if t.anbieter:
                    label = f"{label} ({t.anbieter})"
                _ha_service("persistent_notification/create", {
                    "notification_id": nid,
                    "title": f"Zählwerk: Vertrag {s.name} kündbar",
                    "message": (
                        f"Der Tarif {label} läuft am {t.gueltig_bis:%d.%m.%Y} aus. "
                        f"Letzter Kündigungstermin: {deadline:%d.%m.%Y} (in {days} Tagen)."
                    ),
                })
            else:
                try:
                    _ha_service("persistent_notification/dismiss", {"notification_id": nid})
                except Exception:  # noqa: BLE001
                    pass


async def watcher() -> None:
    """Intervall und Ein/Aus kommen aus den Anwendungseinstellungen und werden
    in JEDEM Zyklus neu gelesen -> Änderungen greifen ohne Add-on-Neustart."""
    if not os.environ.get("SUPERVISOR_TOKEN"):
        return                                   # Standalone ohne HA
    await asyncio.sleep(90)                      # HA nach Add-on-Start Zeit geben
    while True:
        hours = 6
        try:
            from .routers.settings import get_setting
            if await asyncio.to_thread(get_setting, "notify_enabled", True):
                await asyncio.to_thread(check_and_notify)
                await asyncio.to_thread(check_contract_endings)
            if await asyncio.to_thread(get_setting, "mqtt_watchdog_enabled", True):
                watchdog_hours = int(await asyncio.to_thread(get_setting, "mqtt_watchdog_hours", 48))
                await asyncio.to_thread(check_mqtt_watchdog, watchdog_hours)
            hours = int(await asyncio.to_thread(get_setting, "notify_interval_hours", 6))
        except Exception:  # noqa: BLE001
            pass                                 # HA/DB temporär weg -> nächster Zyklus
        await asyncio.sleep(max(1, hours) * 3600)
