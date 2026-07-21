"""Admin-Werkzeuge: Diagnose, Protokoll, lesende Datenbankabfrage.

**Bewusst keine Shell.** Ein Endpunkt, der beliebige Befehle im Container
ausführt, wäre Remote Code Execution als Funktion. Der Container hält
`SUPERVISOR_TOKEN`; wer darin Befehle absetzen kann, erreicht die gesamte
Supervisor-API und die Einbindungen von /config, /share und /backup. Da die
Oberfläche Bibliotheken über ein Auslieferungsnetz einbindet, würde bereits
eine Cross-Site-Scripting-Lücke genügen: das Sitzungscookie geht bei jedem
`fetch` aus dem Dokument automatisch mit. Für echten Shell-Zugriff ist das
Add-on „Advanced SSH & Web Terminal" vorgesehen.

Dieses Modul deckt den tatsächlichen Bedarf ab – nachsehen, was das System
gerade tut – ohne die Angriffsfläche zu verändern:

* **Diagnose**  Zustand von Datenbank, Migrationen, Sicherung, Broker und
  ausgehenden Verbindungen.
* **Protokoll**  die letzten Meldungen der Anwendung aus einem Ringpuffer.
  Der Puffer ersetzt das Anzapfen der Standardausgabe, die im Container dem
  Supervisor gehört.
* **Abfrage**  lesende SQL-Abfragen auf einer schreibgeschützt geöffneten
  Verbindung.

Alle drei sind auf die Rolle Administrator beschränkt; die Prüfung erfolgt
zentral in der Middleware.
"""
import json
import logging
import re
import sqlite3
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from .. import audit, auth
from .. import backup as backup_mod, mqtt_client, ocr as ocr_mod, outbound
from ..config import settings as runtime_settings
from ..database import engine, get_session
from ..migrations import schema_version
from ..models import AuditLog, User
from ..auth import current_user
from ..schemas import SqlQueryRequest, UserCreateRequest, UserCreateResponse, UserRead
from ..version import APP_VERSION

log = logging.getLogger("zaehlwerk.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/users/create", response_model=UserCreateResponse, status_code=201)
def create_user(payload: UserCreateRequest,
                actor: User = Depends(current_user),
                session: Session = Depends(get_session)):
    """Neues Konto anlegen. Das System vergibt ein sicheres temporäres Passwort
    und gibt es dem Administrator EINMALIG im Klartext zurück (nie erneut
    abrufbar). Der neue Nutzer wird beim ersten Login zu Passwortwechsel und
    2FA-Einrichtung gezwungen (`temp_password_active` + `is_first_login`)."""
    if not auth.crypto_available():
        raise HTTPException(503, "bcrypt oder PyJWT fehlen im Image")
    username = payload.username.strip().lower()
    if session.exec(select(User).where(User.username == username)).first():
        raise HTTPException(409, "Benutzername bereits vergeben")
    if payload.role not in auth.ROLES:
        raise HTTPException(422, "Unbekannte Rolle")

    temp_password = auth.generate_temp_password()
    user = User(
        username=username,
        display_name=payload.display_name or payload.username,
        password_hash=auth.hash_password(temp_password),
        role=payload.role,
        is_admin=auth.at_least(payload.role, "admin"),
        aktiv=True,
        temp_password_active=True,
        is_first_login=True,
        two_factor_enabled=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    log.info("Konto angelegt: %s (Rolle %s) durch %s", username, payload.role, actor.username)
    read = UserRead(id=user.id, username=user.username,
                    display_name=user.display_name or user.username,
                    role=user.role, is_admin=user.is_admin, aktiv=user.aktiv,
                    source="lokal", two_factor_enabled=False, is_first_login=True)
    return UserCreateResponse(user=read, temp_password=temp_password)


# --------------------------------------------------------------------------
# Protokoll-Ringpuffer
# --------------------------------------------------------------------------
LOG_BUFFER: deque = deque(maxlen=500)


class BufferHandler(logging.Handler):
    """Hängt sich in das Protokoll der Anwendung.

    Die Standardausgabe des Containers liest der Supervisor; von innen ist sie
    nicht zugänglich. Ein Ringpuffer im Prozess liefert dieselbe Information,
    ohne dafür eine Datei mitschreiben zu müssen.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            LOG_BUFFER.appendleft({
                "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            })
        except Exception:  # noqa: BLE001
            pass


def install_log_buffer() -> None:
    """Einmal beim Start aufrufen."""
    root = logging.getLogger("zaehlwerk")
    if any(isinstance(h, BufferHandler) for h in root.handlers):
        return
    handler = BufferHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


# --------------------------------------------------------------------------
# Lesende Abfrage
# --------------------------------------------------------------------------
# Nur diese Anfänge sind zugelassen. Alles andere wird abgewiesen, bevor die
# Datenbank es überhaupt sieht.
ALLOWED_PREFIX = re.compile(r"^\s*(select|with)\s", re.IGNORECASE)

# Zusätzlicher Riegel gegen Anweisungen, die SQLite auch lesend anbietet
# (ATTACH bindet fremde Dateien ein, PRAGMA kann Einstellungen verändern).
FORBIDDEN = re.compile(
    r"\b(attach|detach|pragma|vacuum|insert|update|delete|drop|alter|create|"
    r"replace|reindex|analyze|begin|commit|rollback|savepoint)\b", re.IGNORECASE)

MAX_ROWS = 500
QUERY_TIMEOUT_S = 5

# Schlüssel in app_settings, deren Werte auch Administratoren nicht im Klartext
# sehen sollen. Der Signaturschlüssel erlaubt das Fälschen von Sitzungen für
# BELIEBIGE Konten – das geht über die Befugnis eines Administrators hinaus, der
# Rollen ohnehin regulär vergeben kann. Das Broker-Passwort ist ein fremdes
# Zugangsdatum, das hier nur zufällig liegt.
SECRET_SETTING_KEYS = {"auth_jwt_secret", "mqtt_password"}
MASK = "●●●●●●●● (verborgen)"


def _secret_values() -> set:
    """Aktuelle Geheimniswerte einsammeln, um sie in Ergebnissen zu ersetzen.

    Bewusst wertbasiert statt spaltenbasiert: der Wert wird auch dann
    unkenntlich, wenn er über einen Alias, eine Unterabfrage oder eine
    Verkettung nach außen getragen wird.
    """
    path = Path(runtime_settings.sqlite_path)
    if not path.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        try:
            rows = conn.execute(
                "SELECT key, value FROM app_settings WHERE key IN ({})".format(
                    ",".join("?" * len(SECRET_SETTING_KEYS))),
                tuple(SECRET_SETTING_KEYS)).fetchall()
        finally:
            conn.close()
        return {v for _, v in rows if v}
    except sqlite3.Error:
        return set()


def _mask(value, secrets: set):
    if not secrets or value is None:
        return value
    if isinstance(value, str):
        if value in secrets:
            return MASK
        for s in secrets:
            if s and s in value:
                return value.replace(s, MASK)
    return value


def _run_query(sql: str) -> dict:
    """Abfrage auf einer schreibgeschützten Verbindung ausführen.

    Drei voneinander unabhängige Riegel: Prüfung des Anweisungsanfangs,
    Sperrliste für verändernde Schlüsselwörter, und – entscheidend – die
    Verbindung selbst wird im Modus `ro` geöffnet und zusätzlich auf
    `query_only` gestellt. Selbst wenn die beiden Textprüfungen umgangen
    würden, weist SQLite jeden Schreibversuch ab.
    """
    text = (sql or "").strip().rstrip(";")
    if not text:
        raise HTTPException(422, "Leere Abfrage")
    if ";" in text:
        raise HTTPException(422, "Nur eine einzelne Anweisung je Aufruf")
    if not ALLOWED_PREFIX.match(text):
        raise HTTPException(422, "Nur SELECT- und WITH-Abfragen sind zulässig")
    hit = FORBIDDEN.search(text)
    if hit:
        raise HTTPException(422, f"Nicht zulässiges Schlüsselwort: {hit.group(0).upper()}")

    path = Path(runtime_settings.sqlite_path)
    if not path.exists():
        raise HTTPException(404, "Datenbank nicht gefunden")

    started = time.time()
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=QUERY_TIMEOUT_S)
    try:
        conn.execute("PRAGMA query_only = ON")
        # Abbruchbedingung gegen Abfragen, die sich festlaufen: der Rückruf
        # wird alle 10.000 Anweisungen aufgerufen und bricht nach Zeitablauf ab.
        deadline = started + QUERY_TIMEOUT_S
        conn.set_progress_handler(lambda: 1 if time.time() > deadline else 0, 10_000)

        cur = conn.execute(f"SELECT * FROM ({text}) LIMIT {MAX_ROWS + 1}")
        columns = [d[0] for d in (cur.description or [])]
        rows = cur.fetchall()
    except sqlite3.OperationalError as exc:
        raise HTTPException(422, f"SQL-Fehler: {exc}")
    except sqlite3.DatabaseError as exc:
        raise HTTPException(422, f"Datenbankfehler: {exc}")
    finally:
        conn.close()

    truncated = len(rows) > MAX_ROWS
    secrets = _secret_values()
    return {
        "columns": columns,
        "rows": [[_mask(v, secrets) for v in r] for r in rows[:MAX_ROWS]],
        "row_count": min(len(rows), MAX_ROWS),
        "truncated": truncated,
        "duration_ms": int((time.time() - started) * 1000),
    }


@router.post("/query")
def query(payload: SqlQueryRequest, user: User = Depends(current_user)):
    # Jede Abfrage wird mit Konto protokolliert – bei einem Werkzeug mit
    # Einblick in sämtliche Daten gehört das zur Nachvollziehbarkeit.
    log.info("SQL-Abfrage von %s: %s", user.username, (payload.sql or "")[:300])
    return _run_query(payload.sql)


@router.get("/schema")
def schema():
    """Tabellen und Spalten – Nachschlagehilfe für die Abfrage."""
    path = Path(runtime_settings.sqlite_path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        out = []
        for table in tables:
            cols = [{"name": r[1], "type": r[2]} for r in
                    conn.execute(f"PRAGMA table_info({table})")]
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            out.append({"table": table, "rows": count, "columns": cols})
        return {"tables": out}
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Diagnose und Protokoll
# --------------------------------------------------------------------------
@router.get("/diagnostics")
def diagnostics(session: Session = Depends(get_session)):
    path = Path(runtime_settings.sqlite_path)
    sizes = {}
    for suffix, label in (("", "db"), ("-wal", "wal"), ("-shm", "shm")):
        p = Path(str(path) + suffix)
        sizes[label] = p.stat().st_size if p.exists() else 0

    with engine.connect() as conn:
        from sqlalchemy import text as sa_text
        integrity = conn.execute(sa_text("PRAGMA integrity_check")).scalar()
        fk_errors = conn.execute(sa_text("PRAGMA foreign_key_check")).fetchall()
        journal = conn.execute(sa_text("PRAGMA journal_mode")).scalar()
        page_count = conn.execute(sa_text("PRAGMA page_count")).scalar()
        page_size = conn.execute(sa_text("PRAGMA page_size")).scalar()
        freelist = conn.execute(sa_text("PRAGMA freelist_count")).scalar()

    return {
        "app_version": APP_VERSION,
        "schema_version": schema_version(engine),
        "database": {
            "path": str(path),
            "sizes_bytes": sizes,
            "journal_mode": journal,
            "integrity_check": integrity,
            "foreign_key_errors": len(fk_errors),
            "page_count": page_count,
            "page_size": page_size,
            "freelist_pages": freelist,
            # Anteil ungenutzter Seiten – ab etwa einem Viertel lohnt ein VACUUM
            "fragmentation_pct": round(100 * (freelist or 0) / (page_count or 1), 1),
        },
        "outbound": {
            "offline_mode": outbound.is_offline(),
            "socket_guard": outbound._guard_installed,
            "cache": outbound.cache_state(),
        },
        "mqtt": {
            "connected": mqtt_client._state.get("connected"),
            "broker": mqtt_client._state.get("broker"),
            "messages": mqtt_client._state.get("messages"),
            "written": mqtt_client._state.get("written"),
            "last_error": mqtt_client._state.get("last_error"),
            "subscriptions": mqtt_client._state.get("subscriptions"),
        },
        "ocr": dict(zip(("available", "missing"), ocr_mod.deps_available())),
        "backup": {
            "directory": str(backup_mod.backup_dir()),
            "supervisor_dir": backup_mod.backup_dir() == backup_mod.PRIMARY_DIR,
            "entries": len(backup_mod.list_backups()),
        },
    }


@router.get("/audit")
def audit_logs(
    page: int = 1,
    per_page: int = 50,
    action: Optional[str] = None,
    target_table: Optional[str] = None,
    user_id: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Änderungsprotokoll, seitenweise.

    Die Seitenaufteilung erfolgt in der Datenbank, nicht im Browser: die
    Tabelle wächst mit jeder Änderung, und ein vollständiger Abruf wäre nach
    wenigen Monaten unbrauchbar.
    """
    from sqlalchemy import func as sa_func

    per_page = max(1, min(per_page, 200))
    page = max(1, page)

    stmt = select(AuditLog)
    count_stmt = select(sa_func.count()).select_from(AuditLog)

    def apply(s):
        if action:
            s = s.where(AuditLog.action == action.upper())
        if target_table:
            s = s.where(AuditLog.target_table == target_table)
        if user_id:
            s = s.where(AuditLog.user_id == user_id)
        if from_:
            s = s.where(AuditLog.ts >= from_)
        if to:
            # Bis einschließlich des genannten Tages
            s = s.where(AuditLog.ts <= f"{to} 23:59:59")
        return s

    total = session.exec(apply(count_stmt)).one()
    rows = session.exec(
        apply(stmt).order_by(AuditLog.ts.desc(), AuditLog.id.desc())
        .offset((page - 1) * per_page).limit(per_page)
    ).all()

    def parse(value):
        if not value:
            return None
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {"_roh": value[:200]}

    return {
        "entries": [{
            "id": r.id, "ts": r.ts.isoformat(timespec="seconds") if r.ts else None,
            "user_id": r.user_id, "username": r.username or "System",
            "action": r.action, "target_table": r.target_table, "target_id": r.target_id,
            "old_value": parse(r.old_value), "new_value": parse(r.new_value),
        } for r in rows],
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.post("/audit/rollback/{log_id}")
def audit_rollback(log_id: int, session: Session = Depends(get_session)):
    """Macht einen einzelnen Protokolleintrag rückgängig.

    Nur genau diesen Eintrag - ohne Prüfung, ob der Datensatz seither erneut
    geändert wurde (siehe audit.rollback). Der Vorgang selbst erscheint
    danach als neuer Eintrag im Protokoll.
    """
    log = session.get(AuditLog, log_id)
    if log is None:
        raise HTTPException(404, "Eintrag nicht gefunden")
    try:
        return audit.rollback(session, log)
    except audit.RollbackError as exc:
        raise HTTPException(422, str(exc))


@router.get("/audit/facets")
def audit_facets(session: Session = Depends(get_session)):
    """Auswahlwerte für die Filter – nur was tatsächlich vorkommt."""
    from sqlalchemy import distinct

    def values(column):
        return sorted(v for (v,) in session.exec(select(distinct(column))).all() if v)

    users = session.exec(
        select(distinct(AuditLog.user_id), AuditLog.username)).all()
    return {
        "actions": values(AuditLog.action),
        "tables": values(AuditLog.target_table),
        "users": [{"id": uid, "username": name or "System"}
                  for uid, name in {(u, n) for u, n in users}],
        "retention_min_days": 30,
    }


@router.get("/logs")
def logs(lines: int = 200, level: str = "INFO"):
    ranking = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
    threshold = ranking.get(level.upper(), 20)
    out = [e for e in LOG_BUFFER if ranking.get(e["level"], 20) >= threshold]
    return {"entries": out[:max(1, min(lines, 500))], "buffered": len(LOG_BUFFER)}
