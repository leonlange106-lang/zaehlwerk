"""Änderungsprotokoll.

**Warum Ereignisse der Sitzung und keine SQLite-Trigger.** Ein Trigger sieht
die Zeile, aber nicht das Konto: SQLite kennt keinen Sitzungskontext, und der
Verursacher wäre damit nicht feststellbar – also genau das, worum es geht.
Die Ereignisse der SQLAlchemy-Sitzung greifen dagegen dort, wo der Nutzer noch
bekannt ist. Er wird von der Middleware in eine Kontextvariable gelegt und hier
ausgelesen.

**Unveränderlichkeit setzt trotzdem die Datenbank durch.** Ereignisse schützen
nur vor Schreibzugriffen über das ORM. Migration 8 legt deshalb zusätzlich
Trigger an, die jedes ``UPDATE`` und ``DELETE`` auf ``audit_logs`` abweisen –
auch aus der SQL-Konsole der Admin-Werkzeuge oder aus künftigem Code.

**Warum im selben Vorgang und nicht nebenläufig.** Eine Warteschlange wäre
schneller, verlöre aber genau dann Einträge, wenn man sie braucht: beim Absturz
mitten in einer Änderung. Die Einträge entstehen deshalb in derselben
Transaktion wie die Änderung. Geschrieben wird gebündelt über die bestehende
Verbindung, nicht über das ORM – ein zweiter Durchlauf des Sitzungsablaufs
würde die Ereignisse erneut auslösen.
"""
import json
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import event, insert
from sqlmodel import Session

log = logging.getLogger("zaehlwerk.audit")

# Wer die Änderung ausgelöst hat. Wird je Anfrage von der Middleware gesetzt.
# ContextVar statt globaler Variable: bei nebenläufigen Anfragen käme es sonst
# zu Verwechslungen zwischen den Konten.
current_actor: ContextVar[Optional[dict]] = ContextVar("audit_actor", default=None)

# Beobachtete Tabellen. Bewusst begrenzt: protokolliert wird, was den
# Datenbestand und die Rechte betrifft – nicht Diagnosezustände.
WATCHED = {"readings", "systems", "tariffs", "meters", "users", "app_settings"}

# Felder, deren Inhalt nie ins Protokoll gehört. Ein Änderungsprotokoll ist
# lesbar für jeden Administrator; Geheimnisse hätten darin nichts verloren.
REDACTED_FIELDS = {"password_hash", "value_of_secret"}
REDACTED_SETTINGS = {"auth_jwt_secret", "mqtt_password"}
MASK = "***"

# Felder, die den Eintrag nur aufblähen, ohne etwas auszusagen.
SKIP_FIELDS = {"dashboard_layout"}

# Ein CSV-Import kann tausende Zeilen anlegen. Ein Eintrag je Zeile wäre
# nutzlos und würde die Tabelle in einem Vorgang um ein Vielfaches vergrößern.
# Oberhalb dieser Schwelle wird je Tabelle ein Sammeleintrag geschrieben.
BULK_THRESHOLD = 25


def set_actor(user) -> None:
    """Konto für die laufende Anfrage hinterlegen."""
    current_actor.set(
        {"id": user.id, "username": user.username, "role": getattr(user, "role", None)}
        if user else None)


def clear_actor() -> None:
    current_actor.set(None)


# --------------------------------------------------------------------------
# Werte aufbereiten
# --------------------------------------------------------------------------
def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # dict/list (z. B. System.zusatzfelder) sind bereits JSON-fähig - als
    # Python-Repr-Text zu speichern (frühere Fassung) machte sie weder lesbar
    # noch aus dem Protokoll rekonstruierbar.
    if isinstance(value, (str, int, float, bool, dict, list, type(None))):
        return value
    return str(value)


def _snapshot(obj, table: str, only: Optional[set] = None) -> dict:
    """Zustand eines Datensatzes als einfaches Wörterbuch."""
    out = {}
    for column in obj.__table__.columns:
        name = column.name
        if name in SKIP_FIELDS or (only is not None and name not in only):
            continue
        value = getattr(obj, name, None)
        if name in REDACTED_FIELDS and value:
            value = MASK
        # app_settings ist Schlüssel/Wert – die Geheimnisse stecken im Wert,
        # nicht im Spaltennamen.
        if table == "app_settings" and getattr(obj, "key", None) in REDACTED_SETTINGS:
            if name == "value" and value:
                value = MASK
        out[name] = _jsonable(value)
    return out


def _changed_fields(obj, session) -> dict:
    """Nur die tatsächlich geänderten Felder, mit altem und neuem Wert."""
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(obj)
    old, new = {}, {}
    for attr in state.attrs:
        name = attr.key
        if name in SKIP_FIELDS:
            continue
        hist = attr.history
        if not hist.has_changes():
            continue
        before = hist.deleted[0] if hist.deleted else None
        after = hist.added[0] if hist.added else None
        if name in REDACTED_FIELDS:
            before, after = (MASK if before else None), (MASK if after else None)
        old[name] = _jsonable(before)
        new[name] = _jsonable(after)
    return {"old": old, "new": new}


def _pk(obj) -> Optional[str]:
    for column in obj.__table__.primary_key.columns:
        value = getattr(obj, column.name, None)
        if value is not None:
            return str(value)
    return None


# --------------------------------------------------------------------------
# Ereignisse
# --------------------------------------------------------------------------
def _collect(session) -> list[dict]:
    actor = current_actor.get() or {}
    now = datetime.utcnow()
    rows: list[dict] = []
    counts: dict[tuple[str, str], int] = {}

    def add(action: str, obj, old: Optional[dict], new: Optional[dict]):
        table = obj.__table__.name
        if table not in WATCHED:
            return
        counts[(table, action)] = counts.get((table, action), 0) + 1
        rows.append({
            "ts": now, "action": action, "table": table, "target_id": _pk(obj),
            "old": old, "new": new,
            "user_id": actor.get("id"), "username": actor.get("username"),
        })

    for obj in session.new:
        if obj.__table__.name in WATCHED:
            add("INSERT", obj, None, _snapshot(obj, obj.__table__.name))
    for obj in session.dirty:
        if obj.__table__.name not in WATCHED or not session.is_modified(obj):
            continue
        diff = _changed_fields(obj, session)
        if not diff["new"]:
            continue                     # nur Berührung, keine Änderung
        add("UPDATE", obj, diff["old"], diff["new"])
    for obj in session.deleted:
        if obj.__table__.name in WATCHED:
            add("DELETE", obj, _snapshot(obj, obj.__table__.name), None)

    # Massenvorgänge zusammenfassen
    bulk = {key for key, count in counts.items() if count > BULK_THRESHOLD}
    if not bulk:
        return rows
    kept = [r for r in rows if (r["table"], r["action"]) not in bulk]
    for table, action in bulk:
        kept.append({
            "ts": now, "action": action, "table": table, "target_id": None,
            "old": None,
            "new": {"bulk": True, "count": counts[(table, action)],
                    "hinweis": "Sammelvorgang – Einzeleinträge zusammengefasst"},
            "user_id": actor.get("id"), "username": actor.get("username"),
        })
    return kept


def _write(session, rows: list[dict]) -> None:
    """Gebündelt über die bestehende Verbindung schreiben.

    Bewusst nicht über die Sitzung: ein weiterer Durchlauf des Ablaufs würde
    die Ereignisse erneut auslösen und sich selbst protokollieren.
    """
    from .models import AuditLog

    payload = [{
        "ts": r["ts"], "user_id": r["user_id"], "username": r["username"],
        "action": r["action"], "target_table": r["table"], "target_id": r["target_id"],
        "old_value": json.dumps(r["old"], ensure_ascii=False) if r["old"] else None,
        "new_value": json.dumps(r["new"], ensure_ascii=False) if r["new"] else None,
    } for r in rows]
    session.connection().execute(insert(AuditLog.__table__), payload)


_installed = False


def install() -> None:
    """Ereignisse anmelden. Idempotent."""
    global _installed
    if _installed:
        return

    @event.listens_for(Session, "before_flush")
    def _before_flush(session, flush_context, instances):  # noqa: ANN001
        try:
            rows = _collect(session)
        except Exception as exc:  # noqa: BLE001
            # Das Protokoll darf die eigentliche Änderung nie verhindern.
            log.warning("Protokollierung übersprungen: %s", exc)
            return
        if rows:
            session.info.setdefault("_audit_rows", []).extend(rows)

    @event.listens_for(Session, "after_flush")
    def _after_flush(session, flush_context):  # noqa: ANN001
        rows = session.info.pop("_audit_rows", None)
        if not rows:
            return
        try:
            # Kennungen stehen erst nach dem Schreiben fest.
            _write(session, rows)
        except Exception as exc:  # noqa: BLE001
            log.error("Protokolleintrag nicht geschrieben: %s", exc)

    _installed = True
    log.info("Änderungsprotokoll aktiv für: %s", ", ".join(sorted(WATCHED)))


# Unterhalb dieser Frist lässt der Trigger aus Migration 8 kein Löschen zu.
# Damit lässt sich Bestand altern, aber kein frischer Eintrag beseitigen –
# genau die Eigenschaft, auf die es bei einem Änderungsprotokoll ankommt.
MIN_RETENTION_DAYS = 30


class RollbackError(Exception):
    """Ein Protokolleintrag lässt sich nicht rückgängig machen."""


# Tabellenname -> SQLModel-Klasse. Nur die auch protokollierten Tabellen -
# für alles andere existiert ohnehin kein alter Zustand im Protokoll.
def _table_models() -> dict:
    from .models import AppSetting, Meter, Reading, System, Tariff, User
    return {"readings": Reading, "systems": System, "tariffs": Tariff,
            "meters": Meter, "users": User, "app_settings": AppSetting}


def _restore_kwargs(model, snapshot: dict) -> dict:
    """Zeichenketten aus der JSON-Momentaufnahme in die vom Modell erwarteten
    Python-Typen zurückwandeln. SQLModel validiert bei der Konstruktion über
    Schlüsselwortargumente nicht wie bei einer Anfrage über die API - ein
    ISO-Datum bliebe sonst eine Zeichenkette und die Einfügung schlüge an der
    SQLite-Spalte fehl."""
    from datetime import date, datetime

    out = {}
    fields = model.model_fields
    for key, value in snapshot.items():
        info = fields.get(key)
        if isinstance(value, str) and info is not None:
            args = getattr(info.annotation, "__args__", None)
            base = next((a for a in args if a is not type(None)), info.annotation) if args else info.annotation
            try:
                if base is datetime:
                    value = datetime.fromisoformat(value)
                elif base is date:
                    value = date.fromisoformat(value)
            except ValueError:
                pass
        out[key] = value
    return out


def rollback(session: Session, log) -> dict:
    """Macht einen einzelnen Protokolleintrag rückgängig.

    Die drei Aktionen brauchen je einen eigenen Weg zurück:
    * ``UPDATE``  schreibt die im Eintrag vermerkten alten Feldwerte zurück.
    * ``DELETE``  legt den Datensatz aus der vollständigen Momentaufnahme neu an.
    * ``INSERT``  entfernt den seinerzeit angelegten Datensatz wieder.

    Der Rückweg läuft bewusst über das ORM (``session.add``/``session.delete``
    auf einer echten Modellinstanz) und nicht über rohes SQL: die
    Änderungsprotokollierung aus diesem Modul hängt an denselben
    Sitzungsereignissen und erfasst den Rückgängig-Vorgang dadurch von selbst
    als neuen Eintrag - ohne das müsste diese Funktion ihr eigenes Protokoll
    von Hand nachführen.

    Was diese Funktion NICHT prüft: ob der Datensatz nach diesem Eintrag noch
    einmal geändert wurde. Ein Rollback überschreibt in dem Fall die
    zwischenzeitliche Änderung - das ist bei einem Protokoll-Rückgängig ohne
    vollständige Versionierung ein bewusst hingenommener Kompromiss, keine
    Kleinigkeit für ein Nebenbei-Feature.
    """
    models = _table_models()
    model = models.get(log.target_table)
    if model is None:
        raise RollbackError(f"Tabelle „{log.target_table}“ wird nicht unterstützt")

    def parse(raw):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    old, new = parse(log.old_value), parse(log.new_value)
    if isinstance(new, dict) and new.get("bulk"):
        raise RollbackError(
            "Sammelvorgänge lassen sich nicht rückgängig machen - "
            "dafür wurden keine Einzeldaten protokolliert")
    if not log.target_id:
        raise RollbackError("Kein Datensatzbezug im Eintrag vorhanden")

    if log.action == "UPDATE":
        if not old:
            raise RollbackError("Keine alten Werte im Eintrag vorhanden")
        obj = session.get(model, log.target_id)
        if obj is None:
            raise RollbackError("Datensatz existiert nicht mehr")
        for field, value in old.items():
            setattr(obj, field, value)
        session.add(obj)
    elif log.action == "DELETE":
        if not old:
            raise RollbackError("Keine Momentaufnahme im Eintrag vorhanden")
        if session.get(model, log.target_id) is not None:
            raise RollbackError("Ein Datensatz mit dieser Kennung besteht bereits wieder")
        try:
            obj = model(**_restore_kwargs(model, old))
        except (TypeError, ValueError) as exc:
            raise RollbackError(f"Momentaufnahme nicht rekonstruierbar: {exc}") from exc
        session.add(obj)
    elif log.action == "INSERT":
        obj = session.get(model, log.target_id)
        if obj is None:
            raise RollbackError("Datensatz ist bereits entfernt")
        session.delete(obj)
    else:
        raise RollbackError(f"Unbekannte Aktion „{log.action}“")

    try:
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        raise RollbackError(f"Rückgängig machen fehlgeschlagen: {exc}") from exc
    return {"table": log.target_table, "target_id": log.target_id, "action": log.action}


def prune(session, keep_days: int) -> int:
    """Abgelaufene Einträge entfernen.

    Wird vom täglichen Sicherungslauf aufgerufen. Ändern bleibt ausnahmslos
    gesperrt; gelöscht werden darf nur, was älter ist als die Mindestfrist.
    Ein zu klein gewählter Wert wird deshalb angehoben statt abgewiesen – der
    Trigger würde den Vorgang sonst mitten im Lauf abbrechen.
    """
    from sqlalchemy import text

    if keep_days <= 0:
        return 0
    days = max(int(keep_days), MIN_RETENTION_DAYS)
    result = session.connection().execute(text(
        "DELETE FROM audit_logs WHERE ts < datetime('now', :cutoff)"),
        {"cutoff": f"-{days} days"})
    return result.rowcount or 0
