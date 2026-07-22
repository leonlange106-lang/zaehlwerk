"""Datenbank-Schicht mit Multi-Tenant-Routing.

Architektur (SQLite pro Nutzer):

* **System-DB** (`system.db`, zentral): Identität & Routing – `User`,
  `UserDatabase`, `DatabaseAccess` sowie der Signaturschlüssel (`app_settings`).
  Die Anmeldung muss funktionieren, *bevor* feststeht, welche Mandanten-DB gilt;
  deshalb liegen Konten hier und nicht in den Mandanten-Datenbanken.
* **Mandanten-DB** (pro Nutzer eine eigene Datei): die eigentlichen Fachdaten –
  `System`, `Reading`, `Meter`, `Tariff`, `AuditLog`, `AppSetting`.

Der bestehende Bestands-Pfad (`settings.sqlite_path`) bleibt unverändert die
*Standard*-Mandanten-DB (`engine`). Beim ersten Start werden lediglich die
Konten in die neue System-DB gehoben und die Bestands-DB als Standard-Mandant
registriert – die Fachdaten wandern nicht, es entsteht kein Kopieraufwand und
kein Migrationsrisiko für die Messreihen.
"""
from pathlib import Path
from typing import Iterator

from fastapi import Request
from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, create_engine, func, select

from .config import settings

# --------------------------------------------------------------------------
# Pfade
# --------------------------------------------------------------------------
_PRIMARY_PATH = Path(settings.sqlite_path)
_DATA_DIR = _PRIMARY_PATH.parent
SYSTEM_DB_PATH = _DATA_DIR / "system.db"
TENANTS_DIR = _DATA_DIR / "tenants"

_DATA_DIR.mkdir(parents=True, exist_ok=True)
TENANTS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Engine-Fabrik (einheitliche PRAGMAs für alle SQLite-Verbindungen)
# --------------------------------------------------------------------------
def _apply_pragmas(dbapi_connection, _record) -> None:
    """WAL: Leser blockieren Schreiber nicht; busy_timeout wartet statt sofort
    'database is locked' zu werfen; synchronous=NORMAL ist sicher in WAL."""
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=15000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def make_engine(path: str | Path) -> Engine:
    """Erzeugt eine SQLite-Engine mit WAL & busy_timeout."""
    eng = create_engine(
        f"sqlite:///{path}",
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    event.listen(eng, "connect", _apply_pragmas)
    return eng


# Zentrale System-DB (Identität/Routing) und Standard-Mandant (Bestands-DB).
system_engine: Engine = make_engine(SYSTEM_DB_PATH)
engine: Engine = make_engine(_PRIMARY_PATH)  # Rückwärtskompatibler Name = Standard-Mandant

# Cache der Mandanten-Engines je Dateipfad.
_tenant_engines: dict[str, Engine] = {str(_PRIMARY_PATH): engine}


# --------------------------------------------------------------------------
# Tabellen-Aufteilung
# --------------------------------------------------------------------------
def _system_tables() -> list:
    from .models import User, UserDatabase, DatabaseAccess, AppSetting
    return [User.__table__, UserDatabase.__table__, DatabaseAccess.__table__,
            AppSetting.__table__]


def _domain_tables() -> list:
    from .models import System, Reading, Meter, Tariff, AuditLog, AppSetting
    return [System.__table__, Reading.__table__, Meter.__table__,
            Tariff.__table__, AuditLog.__table__, AppSetting.__table__]


# --------------------------------------------------------------------------
# Mandanten-Engines
# --------------------------------------------------------------------------
def resolve_tenant_path(filename: str) -> Path:
    """Absoluter Pfad einer Mandanten-DB. Absolute `filename` (Bestand) werden
    unverändert genutzt, relative liegen unter dem Tenants-Verzeichnis."""
    p = Path(filename)
    return p if p.is_absolute() else (TENANTS_DIR / filename)


def tenant_engine(path: str | Path) -> Engine:
    """Engine für eine Mandanten-DB (gecacht, Schema + Migrationen sichergestellt)."""
    key = str(Path(path))
    eng = _tenant_engines.get(key)
    if eng is None:
        eng = make_engine(path)
        _tenant_engines[key] = eng
        _ensure_domain_schema(eng)
    return eng


def _ensure_domain_schema(eng: Engine) -> None:
    from . import models  # noqa: F401 – Modelle registrieren
    SQLModel.metadata.create_all(eng, tables=_domain_tables())
    from .migrations import run_migrations
    run_migrations(eng)


# --------------------------------------------------------------------------
# Start / Migration
# --------------------------------------------------------------------------
def init_db() -> None:
    """Reihenfolge: System-DB anlegen, Standard-Mandant anlegen+migrieren,
    Konten in die System-DB heben, Bestand als Standard-Mandant registrieren,
    danach alle weiteren registrierten Mandanten migrieren. Alles idempotent."""
    from . import models  # noqa: F401

    # 1. System-DB (nur Identität/Routing)
    SQLModel.metadata.create_all(system_engine, tables=_system_tables())

    # 2. Standard-Mandant (Bestands-DB) – Fachschema + Migrationen
    _ensure_domain_schema(engine)

    # 3. Konten in die System-DB übernehmen + Bestand registrieren
    _bootstrap_tenancy()

    # 4. Alle weiteren registrierten Mandanten migrieren
    migrate_all_tenants()


def _bootstrap_tenancy() -> None:
    """Hebt vorhandene Konten in die System-DB und registriert die Bestands-DB
    als Standard-Mandant des ersten Admins. Läuft nur, solange nötig."""
    from .models import User, UserDatabase, DatabaseAccess, DatabaseRole

    with Session(system_engine) as sys:
        has_users = sys.exec(select(func.count()).select_from(User)).one()
        default_db = sys.exec(
            select(UserDatabase).where(UserDatabase.is_default == True)  # noqa: E712
        ).first()
        if has_users and default_db:
            return

        # Konten aus der Bestands-DB kopieren, falls die System-DB leer ist.
        if not has_users:
            _copy_users_from_primary(sys)

        if default_db is None:
            owner = (
                sys.exec(select(User).where(User.is_admin == True)).first()  # noqa: E712
                or sys.exec(select(User)).first()
            )
            record = UserDatabase(
                name="Hauptdatenbank",
                owner_user_id=(owner.id if owner else "system"),
                filename=str(_PRIMARY_PATH),   # absolut = Bestand am ursprünglichen Ort
                is_default=True,
            )
            sys.add(record)
            sys.commit()
            sys.refresh(record)
            if owner:
                sys.add(DatabaseAccess(user_id=owner.id, database_id=record.id,
                                       role=DatabaseRole.owner.value))
                sys.commit()


def _copy_users_from_primary(sys_session: Session) -> None:
    """Konten aus der Bestands-DB in die System-DB übernehmen (nicht-destruktiv:
    die alte `users`-Tabelle bleibt als Fallback liegen)."""
    from .models import User

    insp = sa_inspect(engine)
    if "users" not in insp.get_table_names():
        return
    with Session(engine) as prim:
        rows = prim.exec(select(User)).all()
        dumps = [row.model_dump() for row in rows]
    for data in dumps:
        sys_session.merge(User(**data))
    if dumps:
        sys_session.commit()


def migrate_all_tenants() -> None:
    """Schema-Updates über alle registrierten Mandanten-Datenbanken ausführen."""
    from .models import UserDatabase

    with Session(system_engine) as sys:
        records = sys.exec(select(UserDatabase)).all()
        paths = [resolve_tenant_path(r.filename) for r in records]
    for path in paths:
        tenant_engine(path)  # legt Schema an und migriert beim ersten Zugriff


# --------------------------------------------------------------------------
# Sessions (FastAPI-Abhängigkeiten)
# --------------------------------------------------------------------------
def get_system_session() -> Iterator[Session]:
    """Session auf die zentrale System-DB (Auth, Registry, Rechte)."""
    with Session(system_engine) as session:
        yield session


def get_session(request: Request) -> Iterator[Session]:
    """Session auf die *aktive* Mandanten-DB des Requests.

    Die Middleware legt `request.state.tenant_engine` fest (aufgelöst aus dem
    angemeldeten Nutzer und optional dem Header `X-Zaehlwerk-Database`). Fehlt
    der Zustand (Hintergrunddienste, Ersteinrichtung), fällt der Aufruf auf den
    Standard-Mandanten zurück – rückwärtskompatibel zum bisherigen Verhalten.
    """
    eng = getattr(getattr(request, "state", None), "tenant_engine", None) or engine
    with Session(eng) as session:
        yield session


def default_tenant_engine() -> Engine:
    """Engine des Standard-Mandanten – für Hintergrunddienste ohne Request-Kontext."""
    return engine


def iter_tenant_engines() -> Iterator[tuple[str, Engine]]:
    """Alle registrierten Mandanten-Engines (id, engine) – für Fan-out-Aufgaben."""
    from .models import UserDatabase

    with Session(system_engine) as sys:
        records = sys.exec(select(UserDatabase)).all()
        items = [(r.id, resolve_tenant_path(r.filename)) for r in records]
    for db_id, path in items:
        yield db_id, tenant_engine(path)
