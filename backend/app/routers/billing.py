"""Abrechnungsjahre (TICKET-3.1): offiziell abgerechnete Jahreskosten je System.

Getrennt von der tarifbasierten Schätzung: hier steht der Betrag der echten
Rechnung. Wird über eine Abrechnungsablesung (is_billed + Kosten) automatisch
fortgeschrieben oder direkt gepflegt. Je System und Jahr höchstens ein Eintrag.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import BillingYear, System
from ..schemas import BillingYearCreate, BillingYearRead

router = APIRouter(tags=["billing"])


def _upsert_billing_year(session: Session, system_id: str, year: int, cost: float) -> BillingYear:
    """Abrechnungsjahr anlegen oder fortschreiben. Nur bei cost > 0 sinnvoll –
    die Prüfung liegt beim Aufrufer (Ablesung) bzw. im Schema (Endpunkt)."""
    row = session.exec(
        select(BillingYear).where(BillingYear.system_id == system_id, BillingYear.year == year)
    ).first()
    if row:
        row.cost = cost
        row.is_billed = True
    else:
        row = BillingYear(system_id=system_id, year=year, cost=cost, is_billed=True)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _require_system(system_id: str, session: Session) -> System:
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    return system


@router.get("/api/systems/{system_id}/billing-years", response_model=list[BillingYearRead])
def list_billing_years(system_id: str, session: Session = Depends(get_session)):
    _require_system(system_id, session)
    rows = session.exec(
        select(BillingYear).where(BillingYear.system_id == system_id)
        .order_by(BillingYear.year.desc())
    ).all()
    return rows


@router.post("/api/systems/{system_id}/billing-years", response_model=BillingYearRead, status_code=201)
def upsert_billing_year(system_id: str, payload: BillingYearCreate,
                        session: Session = Depends(get_session)):
    """Legt ein Abrechnungsjahr an bzw. schreibt es fort – aber nur, wenn es als
    abgerechnet markiert ist UND Kosten > 0 hat (sonst gäbe es nichts zu
    verbuchen). Genau die Bedingung aus TICKET-3.1."""
    _require_system(system_id, session)
    if not payload.is_billed or payload.cost <= 0:
        raise HTTPException(422, "Abrechnungsjahr braucht is_billed=true und Kosten > 0")
    return _upsert_billing_year(session, system_id, payload.year, payload.cost)


@router.delete("/api/billing-years/{billing_id}", status_code=204)
def delete_billing_year(billing_id: str, session: Session = Depends(get_session)):
    row = session.get(BillingYear, billing_id)
    if row:
        session.delete(row)
        session.commit()
