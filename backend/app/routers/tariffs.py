"""Tarifperioden je System, inkl. Vertragsunterlagen-Upload/OCR und der
Vertragsende-Übersicht (Kündigungstermin naht)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from .. import tariff_docs
from ..database import get_session
from ..models import System, Tariff
from ..schemas import (
    TariffExpiring,
    TariffOcrSuggestion,
    TariffPlanCreate,
    TariffPlanRead,
    TariffPlanUpdate,
    TariffUploadResult,
)

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
    deadline = tariff_docs.notice_deadline(t.gueltig_bis, t.notice_period_days)
    due_soon = bool(deadline and 0 <= (deadline - today).days <= 30)
    return TariffPlanRead(
        id=t.id, system_id=t.system_id, name=t.name, anbieter=t.anbieter,
        gueltig_ab=t.gueltig_ab, gueltig_bis=t.gueltig_bis,
        arbeitspreis=t.arbeitspreis, grundpreis=t.grundpreis,
        notiz=t.notiz, erstellt_am=t.erstellt_am,
        contract_document_url=t.contract_document_url,
        notice_period_days=t.notice_period_days,
        notice_deadline=deadline, notice_due_soon=due_soon,
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


# --------------------------------------------------------------------------
# Vertragsunterlage: Upload + OCR-Vorschläge, Abruf
# --------------------------------------------------------------------------
@router.post("/api/tariffs/upload", response_model=TariffUploadResult)
async def upload_document(file: UploadFile = File(...)):
    """Vertrag (PDF/Bild) hochladen: ablegen, Text gewinnen und Felder
    vorschlagen. Der Tarif selbst wird danach über create/patch mit der
    zurückgegebenen document_url und den (ggf. korrigierten) Feldern gespeichert.
    """
    ctype = (file.content_type or "").split(";")[0].strip()
    if ctype not in tariff_docs.ALLOWED_TYPES:
        raise HTTPException(415, "Nur PDF, JPEG, PNG, WEBP oder HEIC")
    data = await file.read()
    if not data:
        raise HTTPException(422, "Leere Datei")
    if len(data) > tariff_docs.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Datei zu groß (max. 20 MB)")

    name, url = tariff_docs.save_document(data, ctype)
    text, ocr_available = tariff_docs.extract_text(data, ctype)
    fields = tariff_docs.extract_fields(text)
    excerpt = (text[:600] + " …") if len(text) > 600 else (text or None)
    return TariffUploadResult(
        document_url=url, filename=name, text_excerpt=excerpt,
        ocr_available=ocr_available, suggestion=TariffOcrSuggestion(**fields),
    )


@router.get("/api/tariffs/documents/{name}")
def get_document(name: str):
    path = tariff_docs.document_path(name)
    if not path:
        raise HTTPException(404, "Dokument nicht gefunden")
    return FileResponse(str(path))


# --------------------------------------------------------------------------
# Vertragsende-Übersicht (Kündigungstermin naht)
# --------------------------------------------------------------------------
@router.get("/api/tariffs/expiring", response_model=list[TariffExpiring])
def expiring_tariffs(
    within_days: int = Query(30, ge=0, le=3650, description="Vorlauf bis zum Kündigungstermin"),
    session: Session = Depends(get_session),
):
    """Verträge, deren Kündigungstermin (gueltig_bis − Kündigungsfrist) heute
    bis in `within_days` Tagen liegt. Basis für die In-App-Warnung."""
    today = date.today()
    rows = session.exec(
        select(Tariff, System).join(System, System.id == Tariff.system_id)
        .where(Tariff.gueltig_bis.is_not(None), Tariff.notice_period_days.is_not(None))
    ).all()
    out: list[TariffExpiring] = []
    for t, s in rows:
        deadline = tariff_docs.notice_deadline(t.gueltig_bis, t.notice_period_days)
        if not deadline:
            continue
        days = (deadline - today).days
        if days < 0 or days > within_days:
            continue
        out.append(TariffExpiring(
            tariff_id=t.id, system_id=s.id, system_name=s.name,
            name=t.name, anbieter=t.anbieter, gueltig_bis=t.gueltig_bis,
            notice_period_days=t.notice_period_days, notice_deadline=deadline,
            days_until_deadline=days,
        ))
    out.sort(key=lambda e: e.days_until_deadline)
    return out
