"""Tarifperioden je System."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import System, Tariff
from ..schemas import TariffPlanCreate, TariffPlanRead, TariffPlanUpdate

router = APIRouter(tags=["tariffs"])


def _require_system(system_id: str, session: Session) -> System:
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    return system


def _overlaps(a_ab: date, a_bis: Optional[date], b_ab: date, b_bis: Optional[date]) -> bool:
    """Zwei halboffene Perioden überschneiden sich, wenn keine vollständig vor
    der anderen liegt. `None` als Ende bedeutet 'läuft weiter'."""
    if a_bis is not None and a_bis < b_ab:
        return False
    if b_bis is not None and b_bis < a_ab:
        return False
    return True


def _check_overlap(session: Session, system_id: str, ab: date, bis: Optional[date],
                   ignore_id: Optional[str] = None) -> None:
    """Überschneidungsfreiheit ist die Voraussetzung dafür, dass die
    Kostenrechnung je Tag genau einen Preis findet. Ohne diese Prüfung würde
    stillschweigend der zuerst gefundene Tarif gewinnen."""
    stmt = select(Tariff).where(Tariff.system_id == system_id)
    if ignore_id:
        stmt = stmt.where(Tariff.id != ignore_id)
    for other in session.exec(stmt).all():
        if _overlaps(ab, bis, other.gueltig_ab, other.gueltig_bis):
            label = other.name or other.gueltig_ab.strftime("%d.%m.%Y")
            raise HTTPException(
                409, f"Zeitraum überschneidet sich mit '{label}' "
                     f"({other.gueltig_ab:%d.%m.%Y} – "
                     f"{other.gueltig_bis:%d.%m.%Y})" if other.gueltig_bis
                     else f"Zeitraum überschneidet sich mit '{label}' "
                          f"(ab {other.gueltig_ab:%d.%m.%Y}, offen)")


def _to_read(t: Tariff) -> TariffPlanRead:
    today = date.today()
    return TariffPlanRead(
        id=t.id, system_id=t.system_id, name=t.name, anbieter=t.anbieter,
        gueltig_ab=t.gueltig_ab, gueltig_bis=t.gueltig_bis,
        arbeitspreis=t.arbeitspreis, grundpreis=t.grundpreis,
        notiz=t.notiz, erstellt_am=t.erstellt_am,
        aktiv=t.gueltig_ab <= today and (t.gueltig_bis is None or today <= t.gueltig_bis),
    )


@router.get("/api/systems/{system_id}/tariffs", response_model=list[TariffPlanRead])
def list_tariffs(system_id: str, session: Session = Depends(get_session)):
    _require_system(system_id, session)
    rows = session.exec(
        select(Tariff).where(Tariff.system_id == system_id)
        .order_by(Tariff.gueltig_ab.desc())
    ).all()
    return [_to_read(t) for t in rows]


@router.post("/api/systems/{system_id}/tariffs", response_model=TariffPlanRead, status_code=201)
def create_tariff(system_id: str, payload: TariffPlanCreate,
                  session: Session = Depends(get_session)):
    _require_system(system_id, session)
    _check_overlap(session, system_id, payload.gueltig_ab, payload.gueltig_bis)
    t = Tariff(system_id=system_id, **payload.model_dump())
    session.add(t)
    session.commit()
    session.refresh(t)
    return _to_read(t)


@router.patch("/api/tariffs/{tariff_id}", response_model=TariffPlanRead)
def update_tariff(tariff_id: str, payload: TariffPlanUpdate,
                  session: Session = Depends(get_session)):
    t = session.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(404, "Tarif nicht gefunden")
    data = payload.model_dump(exclude_unset=True)
    ab = data.get("gueltig_ab", t.gueltig_ab)
    bis = data.get("gueltig_bis", t.gueltig_bis)
    if bis is not None and bis < ab:
        raise HTTPException(422, "Ende darf nicht vor dem Beginn liegen")
    _check_overlap(session, t.system_id, ab, bis, ignore_id=tariff_id)
    for key, val in data.items():
        setattr(t, key, val)
    session.add(t)
    session.commit()
    session.refresh(t)
    return _to_read(t)


@router.delete("/api/tariffs/{tariff_id}", status_code=204)
def delete_tariff(tariff_id: str, session: Session = Depends(get_session)):
    t = session.get(Tariff, tariff_id)
    if t:
        session.delete(t)
        session.commit()
