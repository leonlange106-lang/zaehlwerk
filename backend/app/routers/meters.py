"""Zähler-Metadaten (Hersteller, Modell, Zählernummer, Eichfrist).

Abgrenzung zur Verbrauchslogik: Diese Endpunkte sind rein dokumentarisch.
`logic.py` und die Auswertungen greifen NICHT darauf zu – ein System ohne
hinterlegten Zähler funktioniert unverändert. Damit bleibt die Erweiterung
rückwärtskompatibel, auch für Bestandsdaten ohne jede Metainformation.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Meter, System
from ..schemas import (
    BAUART_VORSCHLAEGE,
    MeterCalibrationEntry,
    MeterCreate,
    MeterRead,
    MeterUpdate,
)

router = APIRouter(tags=["meters"])


def _require_system(system_id: str, session: Session) -> System:
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    return system


def _require_meter(meter_id: str, session: Session) -> Meter:
    meter = session.get(Meter, meter_id)
    if not meter:
        raise HTTPException(404, "Zähler nicht gefunden")
    return meter


def _to_read(m: Meter) -> MeterRead:
    """Reicht die abgeleiteten Felder an, die nicht gespeichert werden."""
    faellig = None
    abgelaufen = False
    if m.eichung_bis:
        faellig = (m.eichung_bis - date.today()).days
        abgelaufen = faellig < 0
    return MeterRead(
        id=m.id, system_id=m.system_id, erstellt_am=m.erstellt_am,
        hersteller=m.hersteller, modell=m.modell, zaehlernummer=m.zaehlernummer,
        bauart=m.bauart, baujahr=m.baujahr, eichung_bis=m.eichung_bis,
        messstellenbetreiber=m.messstellenbetreiber,
        stellen_vor=m.stellen_vor, stellen_nach=m.stellen_nach,
        eingebaut_am=m.eingebaut_am, ausgebaut_am=m.ausgebaut_am, notiz=m.notiz,
        aktiv=m.ausgebaut_am is None,
        eichung_faellig_in_tagen=faellig,
        eichung_abgelaufen=abgelaufen,
    )


def _check_duplicate(session: Session, system_id: str, nummer: str | None,
                     ignore_id: str | None = None) -> None:
    """Zählernummer muss innerhalb eines Systems eindeutig sein – sonst lassen
    sich Alt- und Neugerät nach einem Tausch nicht mehr auseinanderhalten.
    Systemübergreifend ist sie NICHT eindeutig: verschiedene Sparten dürfen
    dieselbe Nummer tragen."""
    if not nummer:
        return
    stmt = select(Meter).where(Meter.system_id == system_id, Meter.zaehlernummer == nummer)
    if ignore_id:
        stmt = stmt.where(Meter.id != ignore_id)
    if session.exec(stmt).first():
        raise HTTPException(409, f"Zählernummer '{nummer}' ist in diesem System bereits vergeben")


# ---------- Vorschlagswerte ----------
@router.get("/api/meters/bauarten", response_model=list[str])
def list_bauarten():
    """Vorschlagsliste für die UI. Freitext bleibt erlaubt."""
    return BAUART_VORSCHLAEGE


# ---------- Eichfristen ----------
@router.get("/api/meters/calibration-due", response_model=list[MeterCalibrationEntry])
def calibration_due(
    within_days: int = Query(90, ge=0, le=3650, description="Vorlauf in Tagen"),
    session: Session = Depends(get_session),
):
    """Zähler, deren Eichfrist abgelaufen ist oder innerhalb des Vorlaufs endet.
    Nur eingebaute Geräte (ausgebaut_am IS NULL)."""
    rows = session.exec(
        select(Meter, System)
        .join(System, System.id == Meter.system_id)
        .where(Meter.eichung_bis.is_not(None), Meter.ausgebaut_am.is_(None))
        .order_by(Meter.eichung_bis)
    ).all()
    today = date.today()
    out = []
    for m, s in rows:
        days = (m.eichung_bis - today).days
        if days > within_days:
            continue
        out.append(MeterCalibrationEntry(
            meter_id=m.id, system_id=s.id, system_name=s.name,
            zaehlernummer=m.zaehlernummer, hersteller=m.hersteller,
            eichung_bis=m.eichung_bis, faellig_in_tagen=days, abgelaufen=days < 0,
        ))
    return out


# ---------- CRUD je System ----------
@router.get("/api/systems/{system_id}/meters", response_model=list[MeterRead])
def list_meters(
    system_id: str,
    include_removed: bool = Query(True, description="auch ausgebaute Zähler zurückgeben"),
    session: Session = Depends(get_session),
):
    _require_system(system_id, session)
    stmt = select(Meter).where(Meter.system_id == system_id)
    if not include_removed:
        stmt = stmt.where(Meter.ausgebaut_am.is_(None))
    # Aktuell verbaute zuerst, danach absteigend nach Einbaudatum
    rows = session.exec(stmt.order_by(Meter.ausgebaut_am, Meter.eingebaut_am.desc())).all()
    return [_to_read(m) for m in rows]


@router.post("/api/systems/{system_id}/meters", response_model=MeterRead, status_code=201)
def create_meter(system_id: str, payload: MeterCreate, session: Session = Depends(get_session)):
    _require_system(system_id, session)
    _check_duplicate(session, system_id, payload.zaehlernummer)
    meter = Meter(system_id=system_id, **payload.model_dump())
    session.add(meter)
    session.commit()
    session.refresh(meter)
    return _to_read(meter)


# ---------- CRUD je Zähler ----------
@router.get("/api/meters/{meter_id}", response_model=MeterRead)
def get_meter(meter_id: str, session: Session = Depends(get_session)):
    return _to_read(_require_meter(meter_id, session))


@router.patch("/api/meters/{meter_id}", response_model=MeterRead)
def update_meter(meter_id: str, payload: MeterUpdate, session: Session = Depends(get_session)):
    meter = _require_meter(meter_id, session)
    data = payload.model_dump(exclude_unset=True)
    if "zaehlernummer" in data:
        _check_duplicate(session, meter.system_id, data["zaehlernummer"], ignore_id=meter_id)
    for key, val in data.items():
        setattr(meter, key, val)
    session.add(meter)
    session.commit()
    session.refresh(meter)
    return _to_read(meter)


@router.delete("/api/meters/{meter_id}", status_code=204)
def delete_meter(meter_id: str, session: Session = Depends(get_session)):
    """Hard delete – Metadaten hängen an keiner Auswertung. Wer die Historie
    behalten will, setzt stattdessen `ausgebaut_am`."""
    meter = session.get(Meter, meter_id)
    if meter:
        session.delete(meter)
        session.commit()
