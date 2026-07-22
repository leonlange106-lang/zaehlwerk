"""Mandanten-Routing & Rechte-Matrix (TICKET-1.1 / 1.2).

Diese Schicht kennt die zentrale System-DB und beantwortet: *welche*
Datenbanken darf ein Nutzer sehen, mit *welcher* Rolle, und *welche* ist im
aktuellen Request aktiv. Die reine Engine-Verwaltung liegt in `database.py`.
"""
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from . import database as db
from .models import DatabaseAccess, DatabaseRole, User, UserDatabase

# Rangfolge für „mindestens"-Vergleiche auf DB-Ebene.
_ROLE_RANK = {
    DatabaseRole.read_only.value: 0,
    DatabaseRole.read_write.value: 1,
    DatabaseRole.owner.value: 2,
}


def role_at_least(role: Optional[str], needed: str) -> bool:
    return _ROLE_RANK.get(role or "", -1) >= _ROLE_RANK.get(needed, 99)


# --------------------------------------------------------------------------
# Zugriff / Rollen
# --------------------------------------------------------------------------
def access_role(sys: Session, user: User, database_id: str) -> Optional[str]:
    """Rolle eines Nutzers auf einer DB, oder None ohne Zugriff.

    Eigentümerschaft (UserDatabase.owner_user_id) sticht immer; danach ein
    expliziter Eintrag der Rechte-Matrix; Administratoren sehen jede DB
    (mindestens lesend), damit das Admin-Dashboard vollständig ist.
    """
    record = sys.get(UserDatabase, database_id)
    if record is None:
        return None
    if record.owner_user_id == user.id:
        return DatabaseRole.owner.value
    entry = sys.exec(
        select(DatabaseAccess)
        .where(DatabaseAccess.database_id == database_id)
        .where(DatabaseAccess.user_id == user.id)
    ).first()
    if entry:
        return entry.role
    if user.is_admin:
        return DatabaseRole.read_only.value
    return None


def _file_size(record: UserDatabase) -> int:
    path = db.resolve_tenant_path(record.filename)
    total = 0
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            total += p.stat().st_size
    return total


def _summary(record: UserDatabase, role: str) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "role": role,
        "is_default": record.is_default,
        "owner_user_id": record.owner_user_id,
        "db_kind": record.db_kind,
        "size_bytes": _file_size(record),
    }


def accessible_databases(sys: Session, user: User) -> list[dict]:
    """Alle Datenbanken, die der Nutzer sehen darf, mit seiner jeweiligen Rolle."""
    records = sys.exec(select(UserDatabase)).all()
    out: list[dict] = []
    for record in records:
        role = access_role(sys, user, record.id)
        if role is not None:
            out.append(_summary(record, role))
    # Standard-DB zuerst, dann alphabetisch – stabile Anzeige.
    out.sort(key=lambda d: (not d["is_default"], d["name"].lower()))
    return out


def resolve_active(sys: Session, user: User,
                   requested_id: Optional[str]) -> Optional[dict]:
    """Aktive Mandanten-DB für den Request bestimmen.

    Vorrang: ausdrücklich angeforderte (und zugängliche) DB → eigene
    (Eigentümer-)DB → irgendeine zugängliche DB → globale Standard-DB.
    Gibt `{path, role, id, name}` zurück oder None, wenn gar keine DB existiert.
    """
    # 1. Ausdrücklich angefordert
    if requested_id:
        role = access_role(sys, user, requested_id)
        if role is not None:
            record = sys.get(UserDatabase, requested_id)
            return _active(record, role)

    # 2. Eigene DB (Eigentümer) – bevorzugt die als Standard markierte
    owned = sys.exec(
        select(UserDatabase).where(UserDatabase.owner_user_id == user.id)
    ).all()
    if owned:
        owned.sort(key=lambda r: (not r.is_default, r.name.lower()))
        return _active(owned[0], DatabaseRole.owner.value)

    # 3. Irgendeine zugängliche DB (z. B. Freigabe)
    for record in sys.exec(select(UserDatabase)).all():
        role = access_role(sys, user, record.id)
        if role is not None:
            return _active(record, role)

    # 4. Globale Standard-DB als letzter Rückfall
    default = sys.exec(
        select(UserDatabase).where(UserDatabase.is_default == True)  # noqa: E712
    ).first()
    if default:
        role = DatabaseRole.owner.value if user.is_admin else DatabaseRole.read_only.value
        return _active(default, role)
    return None


def _active(record: UserDatabase, role: str) -> dict:
    return {
        "path": db.resolve_tenant_path(record.filename),
        "role": role,
        "id": record.id,
        "name": record.name,
    }


# --------------------------------------------------------------------------
# Verwaltung (Anlegen / Freigeben / Entziehen)
# --------------------------------------------------------------------------
def create_database(sys: Session, name: str, owner_user_id: str) -> UserDatabase:
    """Neue isolierte Mandanten-DB anlegen (Datei + Schema + Owner-Zugriff)."""
    record = UserDatabase(
        name=name,
        owner_user_id=owner_user_id,
        filename=f"{__import__('uuid').uuid4()}.db",  # relativ zu TENANTS_DIR
        is_default=False,
    )
    sys.add(record)
    sys.commit()
    sys.refresh(record)
    # Datei + Fachschema erzeugen.
    db.tenant_engine(db.resolve_tenant_path(record.filename))
    sys.add(DatabaseAccess(user_id=owner_user_id, database_id=record.id,
                           role=DatabaseRole.owner.value))
    sys.commit()
    return record


def provision_for_user(sys: Session, user: User) -> UserDatabase:
    """Standard-DB für einen neuen Nutzer bereitstellen (idempotent)."""
    existing = sys.exec(
        select(UserDatabase).where(UserDatabase.owner_user_id == user.id)
    ).first()
    if existing:
        return existing
    label = user.display_name or user.username
    return create_database(sys, name=f"{label}s Datenbank", owner_user_id=user.id)


def claim_default_database(sys: Session, user: User) -> None:
    """Den (bei frischer Installation noch herrenlosen) Standard-Mandanten dem
    ersten angelegten Admin zuweisen. Idempotent und ohne Wirkung, wenn die
    Standard-DB bereits einen echten Eigentümer hat."""
    default = sys.exec(
        select(UserDatabase).where(UserDatabase.is_default == True)  # noqa: E712
    ).first()
    if default is None or default.owner_user_id not in ("system", "", None):
        return
    default.owner_user_id = user.id
    sys.add(default)
    sys.commit()
    grant_access(sys, default.id, user.id, DatabaseRole.owner.value)


def grant_access(sys: Session, database_id: str, user_id: str, role: str) -> DatabaseAccess:
    """Zugriff eines Nutzers auf eine DB setzen/aktualisieren."""
    if role not in _ROLE_RANK:
        raise ValueError(f"Unbekannte Rolle: {role}")
    entry = sys.exec(
        select(DatabaseAccess)
        .where(DatabaseAccess.database_id == database_id)
        .where(DatabaseAccess.user_id == user_id)
    ).first()
    if entry:
        entry.role = role
    else:
        entry = DatabaseAccess(user_id=user_id, database_id=database_id, role=role)
    sys.add(entry)
    sys.commit()
    sys.refresh(entry)
    return entry


def revoke_access(sys: Session, database_id: str, user_id: str) -> bool:
    """Freigabe entziehen. Der Eigentümer kann nicht entzogen werden."""
    record = sys.get(UserDatabase, database_id)
    if record and record.owner_user_id == user_id:
        return False
    entry = sys.exec(
        select(DatabaseAccess)
        .where(DatabaseAccess.database_id == database_id)
        .where(DatabaseAccess.user_id == user_id)
    ).first()
    if not entry:
        return False
    sys.delete(entry)
    sys.commit()
    return True


def access_entries(sys: Session, database_id: str) -> list[dict]:
    """Rechte-Matrix einer DB inkl. Eigentümer (implizit) für die Admin-Ansicht."""
    record = sys.get(UserDatabase, database_id)
    if record is None:
        return []
    out: list[dict] = [{
        "user_id": record.owner_user_id,
        "role": DatabaseRole.owner.value,
        "implicit": True,
    }]
    entries = sys.exec(
        select(DatabaseAccess).where(DatabaseAccess.database_id == database_id)
    ).all()
    for entry in entries:
        if entry.user_id == record.owner_user_id:
            continue
        out.append({"user_id": entry.user_id, "role": entry.role, "implicit": False})
    return out


def admin_overview(sys: Session) -> list[dict]:
    """Übersicht aller Datenbanken für das Admin-Dashboard (TICKET-1.3)."""
    records = sys.exec(select(UserDatabase)).all()
    users = {u.id: u for u in sys.exec(select(User)).all()}
    out = []
    for record in records:
        owner = users.get(record.owner_user_id)
        shared = sys.exec(
            select(DatabaseAccess).where(DatabaseAccess.database_id == record.id)
        ).all()
        out.append({
            "id": record.id,
            "name": record.name,
            "is_default": record.is_default,
            "db_kind": record.db_kind,
            "owner_user_id": record.owner_user_id,
            "owner_name": (owner.display_name or owner.username) if owner else None,
            "size_bytes": _file_size(record),
            "shared_with": len({e.user_id for e in shared} - {record.owner_user_id}),
            "erstellt_am": record.erstellt_am,
        })
    out.sort(key=lambda d: (not d["is_default"], d["name"].lower()))
    return out
