"""MQTT-Ingestion: Zählerstände aus Broker-Nachrichten übernehmen.

**Zugangsdaten.** Läuft das Add-on unter Home Assistant und ist das
Mosquitto-Add-on installiert, holt sich Zählwerk Host, Port, Benutzer und
Passwort über die Supervisor-Schnittstelle `/services/mqtt`. Dann muss – und
soll – hier gar kein Passwort gespeichert werden. Die manuelle Eingabe ist
nur die Rückfallebene für den Standalone-Betrieb; das Passwort liegt dann
unverschlüsselt in der SQLite-Datei, was in den Einstellungen auch so
ausgewiesen wird.

**Warum nicht jede Nachricht eine neue Ablesung ergibt.** Ein Smart Meter
sendet im Sekundentakt. Für jede Nachricht eine Zeile anzulegen, würde die
Datenbank binnen Wochen um Millionen Zeilen aufblähen und die gesamte
Auswertung entwerten: Verbrauch, Ausreißer und Fälligkeiten rechnen mit
Intervallen zwischen Ablesungen, nicht mit einem Messstrom. Der Listener
schreibt deshalb **höchstens eine Ablesung je System und Tag** und
aktualisiert den Wert des laufenden Tages, statt anzuhängen.

**Kill-Switch.** Ein Broker im eigenen Netz ist von der Sperre aus 2.12.0 nicht
betroffen – sie greift nur für öffentliche Adressen. Ein Broker im Internet
wird dagegen blockiert, solange der Offline-Modus aktiv ist.
"""
import json
import logging
import os
import re
import threading
import urllib.request
from collections import deque
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlmodel import Session, select

from .database import engine
from .models import Reading, System

log = logging.getLogger("zaehlwerk.mqtt")

# Ringpuffer der letzten Ereignisse – reine Diagnosehilfe für die Oberfläche,
# damit man beim Einrichten sieht, ob und was ankommt.
EVENTS: deque = deque(maxlen=60)

# Auto-Discovery: erkannte Tasmota-Geräte. Schlüssel = Gerätename aus dem
# Topic (tele/<gerät>/SENSOR). Bewusst nur im Arbeitsspeicher – die Liste ist
# eine Einrichtungshilfe, kein Bestand, und baut sich nach einem Neustart
# binnen eines Telemetrie-Intervalls (Standard 300 s) von selbst wieder auf.
DISCOVERED: dict[str, dict] = {}

# Ignorierte Geräte: dauerhaft in der Datenbank, sonst wäre "Ignorieren" nach
# jedem Neustart hinfällig - die Discovery-Liste selbst baut sich ja bewusst
# von selbst wieder auf (siehe oben). Im Arbeitsspeicher gecacht, weil
# _on_message() bei jeder eingehenden Nachricht danach fragt und ein
# Datenbankzugriff je Nachricht unnötig wäre.
_ignored_devices: set[str] = set()
IGNORED_SETTING_KEY = "mqtt_ignored_devices"

_client = None
_lock = threading.Lock()
# --------------------------------------------------------------------------
# Speicherintervall
# --------------------------------------------------------------------------
# Je Periode wird höchstens EIN Datensatz geführt und innerhalb der laufenden
# Periode aktualisiert. Feiner als täglich ist nicht möglich, weil
# `Reading.datum` eine Datumsspalte ist – ein stündlicher Takt bräuchte einen
# Zeitstempel und damit eine Schemaänderung.
MQTT_INTERVALS = {
    "daily":     {"label": "Täglich",       "hint": "ein Wert je Tag"},
    "weekly":    {"label": "Wöchentlich",   "hint": "ein Wert je Kalenderwoche, ab Montag"},
    "monthly":   {"label": "Monatlich",     "hint": "ein Wert je Kalendermonat"},
    "quarterly": {"label": "Quartalsweise", "hint": "ein Wert je Quartal"},
    "yearly":    {"label": "Jährlich",      "hint": "ein Wert je Kalenderjahr"},
}
DEFAULT_INTERVAL = "daily"


def period_start(interval: str, day: date) -> date:
    """Beginn der Periode, in die `day` fällt."""
    if interval == "weekly":
        return day - timedelta(days=day.weekday())      # Montag
    if interval == "monthly":
        return day.replace(day=1)
    if interval == "quarterly":
        return day.replace(month=((day.month - 1) // 3) * 3 + 1, day=1)
    if interval == "yearly":
        return day.replace(month=1, day=1)
    return day                                           # daily


def _interval_for(system: System, fallback: str) -> str:
    """Einstellung am System schlägt die globale Vorgabe."""
    value = (system.zusatzfelder or {}).get("mqtt_interval")
    value = str(value).strip() if value else ""
    return value if value in MQTT_INTERVALS else fallback


_state: dict[str, Any] = {
    "connected": False,
    "broker": None,
    "source": None,          # "supervisor" | "manuell"
    "last_error": None,
    "subscriptions": [],
    "messages": 0,
    "written": 0,
    "discovery": False,
    "discovery_prefix": "tele",
    "interval": DEFAULT_INTERVAL,
}

# Übliche Schlüssel in JSON-Nutzlasten, Reihenfolge = Priorität. Der Vergleich
# ist bewusst ohne Rücksicht auf Groß-/Kleinschreibung: Tasmota sendet
# {"ENERGY":{"Total":…}}, ESPHome {"value":…}, Shelly {"total":…}.
JSON_KEYS = ["value", "total", "total_kwh", "total_in", "energy", "state",
             "reading", "counter", "consumption", "volume", "meter_reading"]


# --------------------------------------------------------------------------
# Tasmota
# --------------------------------------------------------------------------
# Tasmota veröffentlicht unter tele/<gerät>/SENSOR ein JSON-Objekt, dessen
# Aufbau vom angeschlossenen Sensor abhängt. Für Zählwerk sind drei Zweige
# relevant:
#   ENERGY.Total      Stromzähler bzw. SML-Lesekopf (Hichi), Einheit kWh
#   ENERGY.Total_In   Zweirichtungszähler, Bezug
#   COUNTER.C1..C4    Impulseingänge – Reed-Kontakt am Gas- oder Wasserzähler
# Die Reihenfolge ist die Priorität: ein Gerät mit ENERGY liefert dort den
# Zählerstand, COUNTER wäre dann nur ein Nebenwert.
# Bekannte Direktpfade. Sie werden zuerst geprüft, weil sie eindeutig sind.
TASMOTA_PATHS = [
    (("energy", "total"),     "kWh",     "Stromzähler / SML-Lesekopf"),
    (("energy", "total_in"),  "kWh",     "Zweirichtungszähler (Bezug)"),
    (("counter", "c1"),       "Impulse", "Impulseingang C1"),
    (("counter", "c2"),       "Impulse", "Impulseingang C2"),
]

# Rekursive Suche als zweite Stufe.
#
# Grund: Beim SML-Skript von Tasmota bestimmt der Anwender den Gruppennamen
# selbst. Ein Skript mit der Zeile `+1,3,s,16,9600,MT631` veröffentlicht unter
# {"MT631":{"Total_in":…}} – der Pfad ist also weder "ENERGY" noch sonst
# vorhersagbar. Fest verdrahtete Pfade können das prinzipiell nicht treffen.
# Gesucht wird deshalb nach dem BLATTNAMEN, unabhängig davon, wo er hängt.
#
# Reihenfolge = Priorität. Kleinere Zahl gewinnt.
READING_KEYS = [
    # OBIS 1.8.0 ist der Bezugszähler – die eindeutigste Angabe überhaupt
    ("1_8_0", 0), ("1-0:1.8.0", 0), ("obis_1_8_0", 0), ("1.8.0", 0),
    ("total_in", 1), ("totalin", 1), ("e_in", 1), ("ein", 1), ("bezug", 1),
    ("zaehlerstand", 1), ("zählerstand", 1), ("meter_reading", 1),
    ("total", 2), ("total_kwh", 2), ("energy_total", 2), ("kwh_total", 2),
    ("counter", 3), ("c1", 3), ("value", 3), ("reading", 3), ("stand", 3),
    ("verbrauch", 4), ("consumption", 4), ("volume", 4), ("m3", 4),
]
READING_KEY_MAP = dict(READING_KEYS)

# Blattnamen, die sicher KEIN Zählerstand sind. Ohne diese Liste würde die
# Suche bei einem Telegramm ohne Zählerstand irgendeine Zahl greifen –
# Momentanleistung, Spannung oder Signalstärke – und sie als Stand speichern.
IGNORE_KEYS = {
    "power", "power_curr", "power_in", "power_out", "curr", "current",
    "voltage", "volt", "amperage", "factor", "frequency", "freq",
    "today", "yesterday", "period", "apparentpower", "reactivepower",
    "rssi", "signal", "linkcount", "temperature", "humidity", "pressure",
    "total_out", "totalout", "e_out", "eout", "einspeisung", "2_8_0",
    "1-0:2.8.0", "id", "index", "seconds", "uptime", "heap", "loadavg",
}

# Obergrenze gegen offensichtlichen Unsinn: kein Haushaltszähler steht bei
# 10 Mio., wohl aber liefern manche Skripte Zeitstempel oder Seriennummern
# als Zahl – die sollen nicht als Zählerstand durchgehen.
MAX_PLAUSIBLE = 10_000_000

TASMOTA_SENSOR_RE = re.compile(r"^(?P<prefix>[^/]+)/(?P<device>[^/]+)/SENSOR$")
TASMOTA_LWT_RE = re.compile(r"^(?P<prefix>[^/]+)/(?P<device>[^/]+)/LWT$")


def _norm_key(key: str) -> str:
    return str(key).strip().lower().replace(" ", "_")


def _as_number(value) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        # Einheiten abschneiden: manche Skripte liefern "11265.043 kWh"
        parts = text.split()
        if parts:
            text = parts[0]
        try:
            return float(text)
        except ValueError:
            return None
    return None


def walk_numeric(obj, prefix: str = "", depth: int = 0) -> list[dict]:
    """Alle Zahlenblätter im Baum mit vollständigem Pfad einsammeln.

    Dient zwei Zwecken: der Kandidatensuche und – wenn nichts passt – der
    Diagnose. Im Fehlerfall sieht man damit sofort, welche Pfade es überhaupt
    gibt, statt im rohen JSON suchen zu müssen.
    """
    found = []
    if depth > 6:
        return found
    if isinstance(obj, dict):
        for key, val in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            number = _as_number(val)
            if number is not None:
                found.append({"path": path, "key": _norm_key(key), "value": number})
            else:
                found += walk_numeric(val, path, depth + 1)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            found += walk_numeric(val, f"{prefix}[{i}]", depth + 1)
    return found


def find_candidates(data: dict) -> list[dict]:
    """Zählerstand-Kandidaten, bester zuerst."""
    out = []
    for leaf in walk_numeric(data):
        key = leaf["key"]
        if key in IGNORE_KEYS:
            continue
        rank = READING_KEY_MAP.get(key)
        if rank is None:
            # Auch Teiltreffer zulassen: "Total_in_kwh", "SML_Total" …
            for name, r in READING_KEYS:
                if name in key:
                    rank = r + 5
                    break
        if rank is None:
            continue
        if leaf["value"] < 0 or leaf["value"] > MAX_PLAUSIBLE:
            continue
        out.append({**leaf, "rank": rank})
    # Bei gleichem Rang gewinnt der größere Wert: ein Zählerstand ist praktisch
    # immer größer als ein danebenliegender Tages- oder Teilwert.
    return sorted(out, key=lambda c: (c["rank"], -c["value"]))


def _get_ci(obj: dict, key: str):
    """Schlüsselzugriff ohne Rücksicht auf Groß-/Kleinschreibung."""
    if not isinstance(obj, dict):
        return None
    for k, v in obj.items():
        if str(k).lower() == key:
            return v
    return None


def _unit_for(key: str) -> str:
    if key in {"counter", "c1", "c2", "c3", "c4"}:
        return "Impulse"
    if key in {"volume", "m3"}:
        return "m³"
    return "kWh"


def parse_tasmota(payload: str, prefer_path: Optional[str] = None) -> Optional[dict]:
    """Tasmota-Nutzlast auswerten.

    Drei Stufen:
      1. `prefer_path` – vom Anwender festgelegter Pfad, schlägt alles andere.
      2. Bekannte Direktpfade (ENERGY.Total, COUNTER.C1 …).
      3. Rekursive Suche nach bekannten Blattnamen im gesamten Baum.

    Rückgabe enthält zusätzlich `candidates`, damit die Oberfläche die
    Alternativen anzeigen kann, wenn die Automatik danebenliegt.
    """
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    inner = _get_ci(data, "statussns")
    if isinstance(inner, dict):
        data = inner

    candidates = find_candidates(data)

    # --- Stufe 1: ausdrücklich gesetzter Pfad ---
    if prefer_path:
        wanted = prefer_path.strip().lower()
        for leaf in walk_numeric(data):
            if leaf["path"].lower() == wanted:
                return {"value": leaf["value"], "path": leaf["path"],
                        "unit": _unit_for(leaf["key"]), "kind": "fester Pfad",
                        "source": "manuell", "candidates": candidates,
                        "extra": _extra(data)}

    # --- Stufe 2: bekannte Direktpfade ---
    for path, unit, kind in TASMOTA_PATHS:
        node = data
        for part in path:
            node = _get_ci(node, part)
            if node is None:
                break
        number = _as_number(node)
        if number is None:
            continue
        return {"value": number, "path": ".".join(p.upper() for p in path),
                "unit": unit, "kind": kind, "source": "direkt",
                "candidates": candidates, "extra": _extra(data)}

    # --- Stufe 3: rekursive Suche ---
    if candidates:
        best = candidates[0]
        return {"value": best["value"], "path": best["path"],
                "unit": _unit_for(best["key"]),
                "kind": "erkannt über Feldnamen", "source": "gesucht",
                "candidates": candidates, "extra": _extra(data)}
    return None


def _extra(data: dict) -> dict:
    """Momentanwerte für die Anzeige – nicht zum Speichern."""
    energy = _get_ci(data, "energy") or {}
    power = _get_ci(energy, "power")
    if power is None:
        for leaf in walk_numeric(data):
            if leaf["key"] in {"power", "power_curr"}:
                power = leaf["value"]
                break
    return {"power": power, "time": _get_ci(data, "time")}


# Rohdaten werden gekappt: ein SML-Telegramm ist selten groesser, aber ein
# fehlkonfiguriertes Geraet koennte den Ringpuffer sonst sprengen.
RAW_LIMIT = 4000


def _remember_device(topic: str, payload: str) -> None:
    """Gerät aus einer Discovery-Nachricht aufnehmen.

    Die rohe Nutzlast wird IMMER mitgeführt, nicht nur im Fehlerfall. Ohne sie
    lässt sich hinterher nicht klären, warum ein Gerät nicht erkannt wurde –
    und genau das war beim Hichi-Lesekopf das Problem.
    """
    match = TASMOTA_SENSOR_RE.match(topic)
    if not match:
        return
    device = match.group("device")
    if device in _ignored_devices:
        return
    parsed = parse_tasmota(payload)
    entry = DISCOVERED.setdefault(device, {"device": device, "topic": topic,
                                           "online": None, "assigned": False})
    raw = payload if len(payload) <= RAW_LIMIT else payload[:RAW_LIMIT] + " …[gekürzt]"

    numeric_paths = []
    try:
        numeric_paths = [{"path": l["path"], "value": l["value"]}
                         for l in walk_numeric(json.loads(payload))][:40]
    except (ValueError, TypeError):
        pass

    entry.update({
        "topic": topic,
        "last_seen": datetime.now().isoformat(timespec="seconds"),
        "value": parsed["value"] if parsed else None,
        "path": parsed["path"] if parsed else None,
        "unit": parsed["unit"] if parsed else None,
        "kind": parsed["kind"] if parsed else "kein Zählerstand erkannt",
        "source": parsed["source"] if parsed else None,
        "candidates": (parsed or {}).get("candidates") or [],
        "power": (parsed or {}).get("extra", {}).get("power"),
        "usable": parsed is not None,
        "raw": raw,
        "numeric_paths": numeric_paths,
    })

    if not parsed:
        # Vollständige Nutzlast ins Log – das ist die Information, mit der sich
        # der richtige Pfad bestimmen lässt.
        log.warning("Kein Zählerstand erkannt auf %s. Rohe Nutzlast: %s", topic, raw)
        log.warning("Gefundene Zahlenpfade: %s",
                    ", ".join(f"{p['path']}={p['value']}" for p in numeric_paths) or "keine")
        _event("warn", f"{device}: kein Zählerstand erkannt – Rohdaten im Gerät hinterlegt",
               topic=topic, raw=raw)


def _remember_lwt(topic: str, payload: str) -> None:
    """Last Will and Testament: Tasmota meldet hier Online bzw. Offline.
    Das Retain-Flag sorgt dafür, dass der Zustand direkt beim Abonnieren
    ankommt – auch für Geräte, die gerade nicht senden."""
    match = TASMOTA_LWT_RE.match(topic)
    if not match:
        return
    device = match.group("device")
    if device in _ignored_devices:
        return
    entry = DISCOVERED.setdefault(device, {"device": device,
                                           "topic": f"{match.group('prefix')}/{device}/SENSOR",
                                           "usable": False, "assigned": False})
    entry["online"] = str(payload).strip().lower() == "online"
    entry["lwt_seen"] = datetime.now().isoformat(timespec="seconds")


def _event(level: str, text: str, **extra) -> None:
    EVENTS.appendleft({"ts": datetime.now().isoformat(timespec="seconds"),
                       "level": level, "text": text, **extra})
    (log.warning if level == "warn" else log.info)(text)


# --------------------------------------------------------------------------
# Broker-Zugangsdaten
# --------------------------------------------------------------------------
def supervisor_broker() -> Optional[dict]:
    """Zugangsdaten vom Supervisor. None, wenn kein MQTT-Dienst bereitsteht."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        "http://supervisor/services/mqtt",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8")).get("data") or {}
    except Exception as exc:  # noqa: BLE001
        log.info("Kein MQTT-Dienst über den Supervisor verfügbar: %s", exc)
        return None
    if not data.get("host"):
        return None
    return {
        "host": data["host"],
        "port": int(data.get("port") or 1883),
        "username": data.get("username") or None,
        "password": data.get("password") or None,
        "source": "supervisor",
    }


def resolve_broker(cfg: dict) -> Optional[dict]:
    """Supervisor hat Vorrang, sofern nicht ausdrücklich abgewählt."""
    if cfg.get("mqtt_use_supervisor", True):
        found = supervisor_broker()
        if found:
            return found
    host = (cfg.get("mqtt_host") or "").strip()
    if not host:
        return None
    return {
        "host": host,
        "port": int(cfg.get("mqtt_port") or 1883),
        "username": (cfg.get("mqtt_username") or "").strip() or None,
        "password": cfg.get("mqtt_password") or None,
        "source": "manuell",
    }


# --------------------------------------------------------------------------
# Nutzlast auswerten
# --------------------------------------------------------------------------
def parse_payload(payload: str) -> Optional[float]:
    """Zahl aus der Nachricht ziehen.

    Unterstützt drei Formen, weil in der Praxis alle drei vorkommen:
    reine Zahl (`1234.5`), JSON mit bekanntem Schlüssel
    (`{"value": 1234.5}`) und verschachteltes JSON (`{"data": {"total": …}}`).
    Komma als Dezimaltrennzeichen wird akzeptiert.
    """
    text = (payload or "").strip()
    if not text:
        return None

    try:
        return float(text.replace(",", "."))
    except ValueError:
        pass

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None

    def dig(obj, depth=0):
        if depth > 3 or not isinstance(obj, dict):
            return None
        lowered = {str(k).lower(): v for k, v in obj.items()}
        for key in JSON_KEYS:
            if key in lowered:
                try:
                    return float(str(lowered[key]).replace(",", "."))
                except (ValueError, TypeError):
                    continue
        for val in obj.values():
            found = dig(val, depth + 1)
            if found is not None:
                return found
        return None

    return dig(data)


# --------------------------------------------------------------------------
# Schreiben
# --------------------------------------------------------------------------
def _reading_path(system: System) -> Optional[str]:
    """Vom Anwender festgelegter JSON-Pfad, falls hinterlegt."""
    value = (system.zusatzfelder or {}).get("mqtt_path")
    return str(value).strip() or None if value else None


def _topic_map(session: Session) -> dict[str, System]:
    """Topic -> System. Das Topic steht in `zusatzfelder["mqtt_topic"]`,
    analog zur bereits vorhandenen `ha_entity`. Kein Schemaeingriff nötig."""
    out = {}
    for system in session.exec(select(System).where(System.aktiv == True)).all():  # noqa: E712
        topic = (system.zusatzfelder or {}).get("mqtt_topic")
        if topic:
            out[str(topic).strip()] = system
    return out


def ingest(topic: str, payload: str) -> Optional[dict]:
    """Eine Nachricht verarbeiten. Gibt das Ergebnis zurück oder None."""
    with Session(engine) as session:
        system = _topic_map(session).get(topic)
        if not system:
            return None

        # Tasmota zuerst, mit dem am System hinterlegten Pfad als Vorgabe.
        # Die allgemeine Suche würde bei einem Gerät ohne Zählerstand, aber mit
        # anderen Zahlenfeldern, den falschen Wert greifen.
        tas = parse_tasmota(payload, prefer_path=_reading_path(system))
        value = tas["value"] if tas else parse_payload(payload)

        if value is None:
            # Vollständige Nutzlast, nicht nur eine Fehlermeldung – nur damit
            # lässt sich der richtige Pfad bestimmen.
            raw = payload if len(payload) <= RAW_LIMIT else payload[:RAW_LIMIT] + " …[gekürzt]"
            log.warning("Nutzlast auf %s nicht auswertbar. Roh: %s", topic, raw)
            try:
                paths = ", ".join(f"{l['path']}={l['value']}"
                                  for l in walk_numeric(json.loads(payload))[:40])
                log.warning("Gefundene Zahlenpfade: %s", paths or "keine")
            except (ValueError, TypeError):
                pass
            _event("warn", f"{system.name}: Nutzlast nicht auswertbar – Rohdaten im Log",
                   topic=topic, raw=raw)
            return None

        today = date.today()
        interval = _interval_for(system, _state.get("interval") or DEFAULT_INTERVAL)
        start = period_start(interval, today)

        # Nur EIGENE Datensätze der laufenden Periode werden fortgeschrieben.
        # Von Hand erfasste Ablesungen bleiben unangetastet – sie sind die
        # verlässlichere Quelle und dürfen nicht überschrieben werden.
        existing = session.exec(
            select(Reading)
            .where(Reading.system_id == system.id, Reading.datum >= start,
                   Reading.source == "mqtt")
            .order_by(Reading.datum.desc())
        ).first()

        # Liegt für heute bereits eine manuelle Ablesung vor, wird nichts
        # geschrieben: zwei Datensätze mit gleichem Datum ergäben ein Intervall
        # von null Tagen und damit einen unbrauchbaren Tagesverbrauch.
        if existing is None:
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

        # Plausibilität: Zählerstände laufen aufwärts. Ein kleinerer Wert deutet
        # auf einen Zählertausch oder eine Fehlmessung hin – beides gehört von
        # Hand erfasst, nicht automatisch geschrieben.
        if previous and value < float(previous.value):
            _event("warn",
                   f"{system.name}: {value} liegt unter dem letzten Stand "
                   f"{previous.value} – verworfen", topic=topic, system=system.name)
            return None

        if existing:
            if float(existing.value) == value and existing.datum == today:
                return None                      # nichts Neues
            existing.value = value
            existing.datum = today               # Datum auf die jüngste Messung ziehen
            session.add(existing)
            action = "aktualisiert"
        else:
            # Notizfeld bleibt frei – es gehört dem Nutzer. Die Herkunft steht
            # seit 3.7.0 in einer eigenen Spalte.
            session.add(Reading(system_id=system.id, datum=today, value=value,
                                meter_replaced=False, source="mqtt"))
            action = "angelegt"

        session.commit()
        _state["written"] += 1
        label = MQTT_INTERVALS[interval]["label"].lower()
        _event("info", f"{system.name}: {value} {system.einheit} {action} ({label})",
               topic=topic, system=system.name, value=value, interval=interval)
        return {"system": system.name, "value": value, "action": action,
                "interval": interval, "period_start": start.isoformat()}


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------
def _on_connect(client, userdata, flags, reason_code, properties=None):
    ok = getattr(reason_code, "is_failure", None)
    success = (reason_code == 0) if ok is None else not reason_code.is_failure
    _state["connected"] = bool(success)
    if not success:
        _state["last_error"] = f"Verbindung abgelehnt: {reason_code}"
        _event("warn", _state["last_error"])
        return
    _state["last_error"] = None
    with Session(engine) as session:
        mapped = _topic_map(session)
    topics = list(mapped.keys())
    for topic in topics:
        client.subscribe(topic, qos=0)

    # Discovery: Wildcards zusätzlich zu den zugeordneten Topics. Sie schreiben
    # nichts in die Datenbank, sondern füllen nur die Geräteliste.
    if _state.get("discovery"):
        prefix = _state.get("discovery_prefix") or "tele"
        for wildcard in (f"{prefix}/+/SENSOR", f"{prefix}/+/LWT"):
            client.subscribe(wildcard, qos=0)
            topics.append(wildcard)
        _mark_assigned(mapped)
    _state["subscriptions"] = topics
    _event("info", f"Verbunden, {len(topics)} Abonnement(s)"
                   + (" inkl. Tasmota-Discovery" if _state.get("discovery") else ""))


def _mark_assigned(mapped: dict) -> None:
    """Geräte kennzeichnen, deren Topic bereits einem System zugeordnet ist."""
    for entry in DISCOVERED.values():
        system = mapped.get(entry.get("topic"))
        entry["assigned"] = bool(system)
        entry["system"] = system.name if system else None


def _on_disconnect(client, userdata, flags, reason_code=None, properties=None):
    _state["connected"] = False
    _event("warn", "Verbindung getrennt – automatischer Neuaufbau läuft")


def _on_message(client, userdata, msg):
    _state["messages"] += 1
    payload = msg.payload.decode("utf-8", errors="replace")
    try:
        if _state.get("discovery"):
            if TASMOTA_LWT_RE.match(msg.topic):
                _remember_lwt(msg.topic, payload)
                return                      # LWT enthält keinen Zählerstand
            if TASMOTA_SENSOR_RE.match(msg.topic):
                _remember_device(msg.topic, payload)
        # Geschrieben wird nur, wenn das Topic einem System zugeordnet ist.
        ingest(msg.topic, payload)
    except Exception as exc:  # noqa: BLE001
        _event("warn", f"Verarbeitung fehlgeschlagen: {exc}", topic=msg.topic)


def start(cfg: dict) -> dict:
    """Client starten. Idempotent: ein laufender Client wird zuvor beendet."""
    global _client
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        _state["last_error"] = "paho-mqtt ist nicht installiert"
        return dict(_state)

    stop()
    broker = resolve_broker(cfg)
    if not broker:
        _state["last_error"] = "Kein Broker konfiguriert"
        return dict(_state)

    with _lock:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"zaehlwerk-{os.getpid()}")
        if broker["username"]:
            client.username_pw_set(broker["username"], broker["password"])
        client.on_connect = _on_connect
        client.on_disconnect = _on_disconnect
        client.on_message = _on_message
        # Neuaufbau der Verbindung übernimmt paho selbst, mit wachsendem Abstand
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        _state.update({"broker": f"{broker['host']}:{broker['port']}",
                       "source": broker["source"], "last_error": None,
                       "discovery": bool(cfg.get("mqtt_tasmota_discovery")),
                       "discovery_prefix": (cfg.get("mqtt_base_topic") or "tele").strip("/"),
                       "interval": cfg.get("mqtt_interval") or DEFAULT_INTERVAL})
        try:
            client.connect_async(broker["host"], broker["port"], keepalive=60)
            client.loop_start()
            _client = client
        except Exception as exc:  # noqa: BLE001
            _state["last_error"] = str(exc)
            _event("warn", f"Verbindungsaufbau fehlgeschlagen: {exc}")
    return dict(_state)


def stop() -> None:
    global _client
    with _lock:
        if _client is not None:
            try:
                _client.loop_stop()
                _client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            _client = None
    _state.update({"connected": False, "subscriptions": []})


def resubscribe() -> None:
    """Nach Änderung der Topics erneut abonnieren, ohne neu zu verbinden."""
    if _client is not None and _state["connected"]:
        _on_connect(_client, None, None, 0)


def status() -> dict:
    devices = sorted(DISCOVERED.values(),
                     key=lambda d: (not d.get("usable"), d.get("device", "")))
    return {**_state, "available": _paho_available(),
            "events": list(EVENTS)[:25], "devices": devices,
            "ignored": sorted(_ignored_devices)}


def forget_devices() -> int:
    n = len(DISCOVERED)
    DISCOVERED.clear()
    return n


# --------------------------------------------------------------------------
# Ignorierte Geräte
# --------------------------------------------------------------------------
def _load_ignored() -> set[str]:
    """Direkter Zugriff auf AppSetting statt über read_settings()/get_setting():
    jene sind bewusst auf die dort registrierten Skalarwerte beschränkt (siehe
    routers/settings.py) und würden diesen Schlüssel sonst stillschweigend
    ignorieren, weil er nicht in DEFAULTS steht - keine Geräteliste soll aber
    auch nicht als gewöhnliche Einstellung über PUT /api/settings überschreibbar sein."""
    from .models import AppSetting
    with Session(engine) as session:
        row = session.get(AppSetting, IGNORED_SETTING_KEY)
    if not row:
        return set()
    try:
        return set(json.loads(row.value))
    except (TypeError, ValueError):
        return set()


def _save_ignored(devices: set[str]) -> None:
    from .models import AppSetting
    with Session(engine) as session:
        session.merge(AppSetting(key=IGNORED_SETTING_KEY, value=json.dumps(sorted(devices))))
        session.commit()


def ignore_device(device: str) -> list[str]:
    """Gerät dauerhaft aus der Discovery-Liste ausblenden. Wirkt sofort auf
    die aktuelle Liste UND auf künftige Nachrichten desselben Geräts."""
    _ignored_devices.add(device)
    _save_ignored(_ignored_devices)
    DISCOVERED.pop(device, None)
    return sorted(_ignored_devices)


def unignore_device(device: str) -> list[str]:
    _ignored_devices.discard(device)
    _save_ignored(_ignored_devices)
    return sorted(_ignored_devices)


def _paho_available() -> bool:
    try:
        import paho.mqtt.client  # noqa: F401
        return True
    except ImportError:
        return False


def boot() -> None:
    """Beim Start aufrufen. Läuft still weiter, wenn MQTT nicht aktiv ist."""
    global _ignored_devices
    try:
        _ignored_devices = _load_ignored()
    except Exception as exc:  # noqa: BLE001
        log.warning("Ignorierliste nicht ladbar: %s", exc)
    try:
        from .routers.settings import read_settings
        with Session(engine) as session:
            cfg = read_settings(session)
        if cfg.get("mqtt_enabled"):
            start(cfg)
    except Exception as exc:  # noqa: BLE001
        log.error("MQTT-Start fehlgeschlagen: %s", exc)
