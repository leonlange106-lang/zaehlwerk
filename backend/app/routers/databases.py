"""Mandanten-Datenbanken: Selbstauskunft & Admin-Verwaltung (TICKET-1.2).

* Selbstauskunft (`/api/databases`): Jedes angemeldete Konto sieht die
  Datenbanken, auf die es Zugriff hat, samt eigener Rolle und der aktuell
  aktiven DB (Kontextwechsel per Header `X-Zaehlwerk-Database`).
* Verwaltung (`/api/admin/databases`, nur Admin – über die zentrale
  Rollen-Middleware abgesichert): Übersicht aller DBs, Anlegen neuer DBs sowie
  die Rechte-Matrix (Zuweisen/Entziehen von Owner/Read-Write/Read-Only).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import auth, tenancy
from ..database import get_system_session
from ..models import DatabaseRole, User, UserDatabase

router = APIRouter(tags=["databases"])


# --------------------------------------------------------------------------
# Schemata
# --------------------------------------------------------------------------
class DatabaseInfo(BaseModel):
    id: str
    name: str
    role: str
    is_default: bool
    owner_user_id: str
    db_kind: str
    size_bytes: int


class DatabaseListResponse(BaseModel):
    active_id: str | None
    databases: list[DatabaseInfo]


class CreateDatabaseRequest(BaseModel):
    name: str
    owner_user_id: str


class GrantAccessRequest(BaseModel):
    user_id: str
    role: str


# --------------------------------------------------------------------------
# Selbstauskunft
# --------------------------------------------------------------------------
@router.get("/api/databases", response_model=DatabaseListResponse)
def my_databases(request: Request,
                 user: User = Depends(auth.current_user),
                 sys: Session = Depends(get_system_session)):
    """Datenbanken, auf die der angemeldete Nutzer Zugriff hat."""
    dbs = tenancy.accessible_databases(sys, user)
    return DatabaseListResponse(
        active_id=getattr(request.state, "active_db_id", None),
        databases=[DatabaseInfo(**d) for d in dbs],
    )


# --------------------------------------------------------------------------
# Admin-Verwaltung
# --------------------------------------------------------------------------
@router.get("/api/admin/databases")
def all_databases(user: User = Depends(auth.current_user),
                  sys: Session = Depends(get_system_session)):
    """Übersicht aller Datenbanken (für das Admin-Dashboard, TICKET-1.3)."""
    return tenancy.admin_overview(sys)


@router.post("/api/admin/databases", status_code=201)
def create_database(payload: CreateDatabaseRequest,
                    user: User = Depends(auth.current_user),
                    sys: Session = Depends(get_system_session)):
    owner = sys.get(User, payload.owner_user_id)
    if owner is None:
        raise HTTPException(404, "Eigentümer nicht gefunden")
    record = tenancy.create_database(sys, name=payload.name.strip(),
                                     owner_user_id=owner.id)
    return {"id": record.id, "name": record.name}


@router.get("/api/admin/databases/{database_id}/access")
def list_access(database_id: str,
                user: User = Depends(auth.current_user),
                sys: Session = Depends(get_system_session)):
    if sys.get(UserDatabase, database_id) is None:
        raise HTTPException(404, "Datenbank nicht gefunden")
    return tenancy.access_entries(sys, database_id)


@router.post("/api/admin/databases/{database_id}/access")
def grant(database_id: str, payload: GrantAccessRequest,
          user: User = Depends(auth.current_user),
          sys: Session = Depends(get_system_session)):
    if sys.get(UserDatabase, database_id) is None:
        raise HTTPException(404, "Datenbank nicht gefunden")
    if sys.get(User, payload.user_id) is None:
        raise HTTPException(404, "Nutzer nicht gefunden")
    valid = {r.value for r in DatabaseRole}
    if payload.role not in valid:
        raise HTTPException(422, f"Unbekannte Rolle. Erlaubt: {', '.join(sorted(valid))}")
    entry = tenancy.grant_access(sys, database_id, payload.user_id, payload.role)
    return {"user_id": entry.user_id, "database_id": entry.database_id, "role": entry.role}


@router.delete("/api/admin/databases/{database_id}/access/{user_id}")
def revoke(database_id: str, user_id: str,
           user: User = Depends(auth.current_user),
           sys: Session = Depends(get_system_session)):
    ok = tenancy.revoke_access(sys, database_id, user_id)
    if not ok:
        raise HTTPException(400, "Freigabe nicht vorhanden oder Eigentümer nicht entziehbar")
    return {"revoked": True}
