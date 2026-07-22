"""Systeme = Stammdaten in SQLite. Kein Hard-Delete (nur archivieren via aktiv=False)."""
import json
import os
import urllib.request
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, func, select

from ..database import get_session
from ..models import Meter, Reading, System, Tariff
from ..schemas import SystemCreate, SystemRead, SystemReorder, SystemUpdate

router = APIRouter(prefix="/api/systems", tags=["systems"])


class BindingTest(BaseModel):
    """Live-Prüfung einer Smart-Home-Anbindung, bevor sie am System gespeichert
    wird – speist den „Testen"-Knopf der Konfigurationsmaske."""
    kind: Literal["ha", "rest"]
    entity_id: Optional[str] = None        # kind=ha
    url: Optional[str] = None              # kind=rest
    path: Optional[str] = None             # kind=rest (JSON-Punktpfad, optional)


@router.post("/binding/test")
def test_binding(payload: BindingTest):
    """Fragt die angegebene Quelle EINMAL ab und meldet den aktuellen Wert –
    ohne etwas zu speichern. Der Kill-Switch greift wie überall: lokale Ziele
    (ESPHome/Tasmota im LAN, Supervisor) bleiben erreichbar, öffentliche werden
    im Offline-Modus vom Socket-Guard blockiert."""
    if payload.kind == "ha":
        entity = (payload.entity_id or "").strip()
        if not entity:
            raise HTTPException(422, "entity_id fehlt")
        token = os.environ.get("SUPERVISOR_TOKEN")
        if not token:
            raise HTTPException(501, "HA-Entity-Test nur im Home-Assistant-Add-on verfügbar")
        req = urllib.request.Request(
            f"http://supervisor/core/api/states/{entity}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"HA/Entity nicht erreichbar: {exc}"}
        attrs = data.get("attributes") or {}
        return {"ok": True, "value": data.get("state"),
                "unit": attrs.get("unit_of_measurement"),
                "name": attrs.get("friendly_name"), "matched_path": entity}

    # kind == "rest"
    from .. import rest_poller
    url = (payload.url or "").strip()
    if not url:
        raise HTTPException(422, "url fehlt")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(422, "url muss mit http:// oder https:// beginnen")
    result = rest_poller.fetch_rest_value(url, (payload.path or "").strip() or None)
    return {"ok": result["value"] is not None, "value": result["value"],
            "matched_path": result["matched_path"], "raw": result["raw"],
            "error": result["error"]}


@router.get("", response_model=list[SystemRead])
def list_systems(
    include_archived: bool = Query(False, description="auch inaktive Systeme zurückgeben"),
    session: Session = Depends(get_session),
):
    stmt = select(System)
    if not include_archived:
        stmt = stmt.where(System.aktiv == True)  # noqa: E712
    return session.exec(stmt.order_by(System.sort_index, System.name)).all()


@router.post("", response_model=SystemRead, status_code=201)
def create_system(payload: SystemCreate, session: Session = Depends(get_session)):
    # Neues System hinten anstellen (höchster sort_index + 1).
    max_idx = session.exec(select(func.max(System.sort_index))).one()
    system = System(**payload.model_dump(), sort_index=(max_idx or 0) + 1)
    session.add(system)
    session.commit()
    session.refresh(system)
    return system


@router.put("/reorder")
def reorder_systems(payload: SystemReorder, session: Session = Depends(get_session)):
    """Neue Reihenfolge in EINER Transaktion setzen: [{id, sort_index}, …].
    Unbekannte IDs werden ignoriert; ein Fehler rollt alles zurück."""
    known = {s.id: s for s in session.exec(select(System)).all()}
    for item in payload.order:
        system = known.get(item.id)
        if system is not None:
            system.sort_index = item.sort_index
            session.add(system)
    session.commit()
    return {"reordered": len([i for i in payload.order if i.id in known])}


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
