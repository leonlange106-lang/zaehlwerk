"""SQLite-Engine mit WAL-Modus und busy_timeout (robust bei parallelen Zugriffen im HA-Umfeld)."""
from pathlib import Path

from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

from .config import settings

Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """WAL = Write-Ahead-Logging: Leser blockieren Schreiber nicht (und umgekehrt).
    busy_timeout: wartet statt sofort 'database is locked' zu werfen.
    synchronous=NORMAL: sicher in WAL, deutlich schneller als FULL."""
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=15000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def init_db() -> None:
    """Reihenfolge ist wichtig: erst Tabellen anlegen (Neuinstallation),
    dann Migrationen (Bestandsinstallation). Beide Schritte sind idempotent."""
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    from .migrations import run_migrations
    run_migrations(engine)


def get_session():
    with Session(engine) as session:
        yield session
