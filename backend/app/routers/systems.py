"""Systeme = Stammdaten in SQLite. Kein Hard-Delete (nur archivieren via aktiv=False)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Meter, Reading, System, Tariff
from ..schemas import SystemCreate, SystemRead, SystemUpdate

router = APIRouter(prefix="/api/systems", tags=["systems"])


@router.get("", response_model=list[SystemRead])
def list_systems(
    include_archived: bool = Query(False, description="auch inaktive Systeme zurückgeben"),
    session: Session = Depends(get_session),
):
    stmt = select(System)
    if not include_archived:
        stmt = stmt.where(System.aktiv == True)  # noqa: E712
    return session.exec(stmt.order_by(System.name)).all()


@router.post("", response_model=SystemRead, status_code=201)
def create_system(payload: SystemCreate, session: Session = Depends(get_session)):
    system = System(**payload.model_dump())
    session.add(system)
    session.commit()
    session.refresh(system)
    return system


@router.get("/{system_id}", response_model=SystemRead)
def get_system(system_id: str, session: Session = Depends(get_session)):
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    return system


@router.patch("/{system_id}", response_model=SystemRead)
def update_system(
    system_id: str, payload: SystemUpdate, session: Session = Depends(get_session)
):
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(system, key, val)
    session.add(system)
    session.commit()
    session.refresh(system)
    return system


@router.delete("/{system_id}", status_code=204)
def delete_system(system_id: str, session: Session = Depends(get_session)):
    """Endgültige Löschung (Falschanlage): System + ALLE zugehörigen Ablesungen
    UND Zähler-Metadaten. Ohne das Mitlöschen schlägt der Commit fehl, weil
    PRAGMA foreign_keys=ON gesetzt ist."""
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    for r in session.exec(select(Reading).where(Reading.system_id == system_id)).all():
        session.delete(r)
    for m in session.exec(select(Meter).where(Meter.system_id == system_id)).all():
        session.delete(m)
    for t in session.exec(select(Tariff).where(Tariff.system_id == system_id)).all():
        session.delete(t)
    session.delete(system)
    session.commit()
