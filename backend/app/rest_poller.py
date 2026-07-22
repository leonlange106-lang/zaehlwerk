"""REST-/HTTP-Abfrage von Zählerständen (ESPHome web_server, Shelly, Tasmota
HTTP, generische JSON-Endpunkte).

Warum als eigener Poller neben MQTT: nicht jedes Gerät pusht. ESPHome
(`web_server`), Shelly (`/rpc/…`) und viele DIY-Bridges bieten nur einen
HTTP-Endpunkt, den man abfragen muss. Der Poller holt in einem festen Takt den
aktuellen Wert und schreibt ihn – exakt nach denselben Perioden-/Plausibilitäts-
regeln wie der MQTT-Pfad – als Ablesung mit Herkunft ``rest``.

Kill-Switch: Es wird bewusst KEINE Ausnahme von der Socket-Sperre gemacht. Die
Sperre (`outbound._guarded_getaddrinfo`) lässt lokale/private Ziele ohnehin
immer durch – ein ESPHome-Gerät unter 192.168.x.x bleibt also im Offline-Modus
erreichbar, ein Cloud-Endpunkt hinter einer öffentlichen IP wird korrekt
blockiert. Genau das ist gewünscht: Der Kill-Switch trennt das Internet, nicht
das lokale Netz.
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
from datetime import date, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from .database import engine
from .models import Reading, System
from .mqtt_client import (
    DEFAULT_INTERVAL,
    MQTT_INTERVALS,
    _as_number,
    find_candidates,
    period_start,
)

log = logging.getLogger("zaehlwerk.rest")

# Eigene Herkunftskennung, damit REST-Ablesungen von manuellen und MQTT-Werten
# unterscheidbar bleiben (Filter, Watchdog, Export). Die source-Spalte ist ein
# freier String ohne DB-Constraint – kein Schemaeingriff nötig.
SOURCE = "rest"

_REQUEST_TIMEOUT = 8
_MAX_BODY = 64_000       # großzügig; ein Zähler-Endpunkt liefert wenige KB
_state: dict[str, Any] = {"last_run": None, "written": 0, "errors": 0}


def state() -> dict:
    return dict(_state)


# --------------------------------------------------------------------------
# HTTP + Wertextraktion
# --------------------------------------------------------------------------
def _dig(obj: Any, path: str) -> Any:
    """Punkt-Pfad in verschachteltem JSON, ohne Rücksicht auf Groß/Klein.

    Beispiel: ``sensor.total.value`` oder ``ENERGY.Total``. Listenindizes sind
    als Zahl erlaubt: ``sensors.0.state``.
    """
    cur = obj
    for part in path.split("."):
        part = part.strip()
        if part == "":
            continue
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
                continue
            except (ValueError, IndexError):
                return None
        if not isinstance(cur, dict):
            return None
        match = None
        for k, v in cur.items():
            if str(k).lower() == part.lower():
                match = v
                break
        if match is None:
            return None
        cur = match
    return cur


def fetch_rest_value(
    url: str, path: Optional[str] = None, *, timeout: int = _REQUEST_TIMEOUT
) -> dict:
    """Einen HTTP-Endpunkt abfragen und den Zählerstand herauslösen.

    Rückgabe: ``{"value": float|None, "raw": str, "matched_path": str|None,
    "error": str|None}``. Wirft NICHT – Fehler stehen im ``error``-Feld, damit
    sowohl der Poller (still weiter) als auch der Test-Endpunkt (Meldung an den
    Nutzer) dieselbe Funktion nutzen können.
    """
    req = urllib.request.Request(url, headers={
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Zaehlwerk-REST/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(_MAX_BODY + 1)
    except Exception as exc:  # noqa: BLE001 – jede Netz-/DNS-Störung ist hier erwartbar
        return {"value": None, "raw": "", "matched_path": None, "error": str(exc)}

    text = body[:_MAX_BODY].decode("utf-8", "replace").strip()
    raw = text if len(text) <= 400 else text[:400] + " …"

    # 1) Reiner Zahlenkörper (ESPHome `/sensor/x` liefert oft nur "1234.5").
    direct = _as_number(text)

    data: Any = None
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        data = None

    # 2) Expliziter Pfad hat Vorrang – der Nutzer weiß, wo sein Wert steht.
    if path and data is not None:
        val = _as_number(_dig(data, path))
        if val is not None:
            return {"value": val, "raw": raw, "matched_path": path, "error": None}
        return {"value": None, "raw": raw, "matched_path": None,
                "error": f"Pfad '{path}' lieferte keinen Zahlenwert"}

    if direct is not None and data is None:
        return {"value": direct, "raw": raw, "matched_path": "(Zahl)", "error": None}

    # 3) Automatische Erkennung im JSON (gleiche Heuristik wie MQTT).
    if isinstance(data, dict):
        cand = find_candidates(data)
        if cand:
            best = cand[0]
            return {"value": float(best["value"]), "raw": raw,
                    "matched_path": best["path"], "error": None}
        # ESPHome `/sensor/x` als JSON: {"id":"sensor-x","value":1234,"state":"1234 kWh"}
        for key in ("value", "state"):
            val = _as_number(data.get(key))
            if val is not None:
                return {"value": val, "raw": raw, "matched_path": key, "error": None}

    if direct is not None:
        return {"value": direct, "raw": raw, "matched_path": "(Zahl)", "error": None}

    return {"value": None, "raw": raw, "matched_path": None,
            "error": "Kein Zählerstand im Ergebnis gefunden"}


# --------------------------------------------------------------------------
# Persistenz (nach denselben Regeln wie mqtt_client.ingest)
# --------------------------------------------------------------------------
def _interval_for(system: System) -> str:
    value = (system.zusatzfelder or {}).get("rest_interval")
    value = str(value).strip() if value else ""
    return value if value in MQTT_INTERVALS else DEFAULT_INTERVAL


def _store(session: Session, system: System, value: float) -> Optional[str]:
    """Wert in die laufende Periode schreiben/fortschreiben. Gibt die Aktion
    ('angelegt'/'aktualisiert') zurück oder None, wenn nichts geschah."""
    today = date.today()
    start = period_start(_interval_for(system), today)

    existing = session.exec(
        select(Reading)
        .where(Reading.system_id == system.id, Reading.datum >= start,
               Reading.source == SOURCE)
        .order_by(Reading.datum.desc())
    ).first()

    if existing is None:
        # Keine zweite Ablesung am selben Tag wie eine manuelle – sonst 0-Tage-Intervall.
        manual_today = session.exec(
            select(Reading).where(Reading.system_id == system.id,
                                  Reading.datum == today)
        ).first()
        if manual_today is not None:
            return None

    previous = session.exec(
        select(Reading).where(Reading.system_id == system.id, Reading.datum < start)
        .order_by(Reading.datum.desc())
    ).first()
    if previous and value < float(previous.value):
        log.warning("%s: REST-Wert %s unter letztem Stand %s – verworfen",
                    system.name, value, previous.value)
        return None

    if existing:
        # Datum kommt als datetime aus der Spalte zurück, `today` ist ein date –
        # für den Vergleich auf den Kalendertag reduzieren, sonst schriebe jeder
        # Zyklus denselben Wert neu (Audit-Rauschen, 0-Tage-Intervall-Risiko).
        existing_day = existing.datum.date() if isinstance(existing.datum, datetime) else existing.datum
        if float(existing.value) == value and existing_day == today:
            return None
        existing.value = value
        existing.datum = today
        session.add(existing)
        action = "aktualisiert"
    else:
        session.add(Reading(system_id=system.id, datum=today, value=value,
                            meter_replaced=False, source=SOURCE))
        action = "angelegt"
    session.commit()
    return action


def poll_once() -> dict:
    """Alle Systeme mit ``rest_url`` einmal abfragen. Synchron; für den
    Scheduler in einem Thread aufgerufen."""
    written = 0
    checked = 0
    with Session(engine) as session:
        systems = session.exec(
            select(System).where(System.aktiv == True)  # noqa: E712
        ).all()
        for system in systems:
            zf = system.zusatzfelder or {}
            url = str(zf.get("rest_url") or "").strip()
            if not url:
                continue
            checked += 1
            result = fetch_rest_value(url, str(zf.get("rest_path") or "").strip() or None)
            if result["value"] is None:
                _state["errors"] += 1
                log.info("%s: REST-Abfrage ohne Wert (%s)", system.name, result["error"])
                continue
            action = _store(session, system, float(result["value"]))
            if action:
                written += 1
                log.info("%s: %s %s per REST %s", system.name, result["value"],
                         system.einheit, action)
    _state["last_run"] = date.today().isoformat()
    _state["written"] += written
    return {"checked": checked, "written": written}


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------
async def scheduler() -> None:
    """Fragt in festem Takt ab. Takt und Ein/Aus kommen je Zyklus frisch aus den
    Einstellungen -> Änderungen greifen ohne Neustart."""
    await asyncio.sleep(30)                       # Start abwarten (DB, Migrationen)
    while True:
        minutes = 15
        try:
            from .routers.settings import get_setting
            if await asyncio.to_thread(get_setting, "rest_poll_enabled", True):
                await asyncio.to_thread(poll_once)
            minutes = int(await asyncio.to_thread(get_setting, "rest_poll_minutes", 15))
        except Exception:  # noqa: BLE001 – DB/Netz temporär weg -> nächster Zyklus
            _state["errors"] += 1
        await asyncio.sleep(max(1, minutes) * 60)
