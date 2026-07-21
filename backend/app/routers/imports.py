"""CSV-Import: Vorlage bereitstellen + Bulk-Upload nach SQLite."""
import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from ..database import get_session
from ..models import Reading, System
from ..schemas import ImportResult

router = APIRouter(tags=["import"])

TEMPLATE = (
    "datum,wert,kosten,zaehlertausch,notiz\n"
    "2024-01-01,12345.6,,,Jahresanfang\n"
    "2024-02-01,12480.2,42.50,,\n"
    "2024-03-01,15.0,,ja,Zaehlertausch neuer Zaehler ab 0\n"
)

_TRUE = {"1", "true", "ja", "yes", "x", "wahr"}


def _parse_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Datum nicht lesbar: '{raw}'")


def _parse_float(raw: str):
    raw = (raw or "").strip().replace(",", ".")
    return float(raw) if raw else None


@router.get("/api/import/template", response_class=PlainTextResponse)
def import_template():
    return PlainTextResponse(
        TEMPLATE, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_template.csv"},
    )


@router.post("/api/systems/{system_id}/import", response_model=ImportResult)
async def import_readings(
    system_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")

    content = (await file.read()).decode("utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(content[:2048], delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)

    imported, skipped, errors = 0, 0, []
    for lineno, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        try:
            d = _parse_date(row.get("datum", ""))
            value = _parse_float(row.get("wert", ""))
            if value is None:
                raise ValueError("Wert fehlt")
            session.add(Reading(
                # Herkunft: aus einer CSV eingelesen, nicht von Hand erfasst.
                source="import",
                system_id=system_id,
                datum=datetime(d.year, d.month, d.day),
                value=value,
                cost=_parse_float(row.get("kosten", "")),
                meter_replaced=(row.get("zaehlertausch", "").strip().lower() in _TRUE),
                note=(row.get("notiz") or "").strip() or None,
            ))
            imported += 1
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            errors.append(f"Zeile {lineno}: {exc}")
    session.commit()

    return ImportResult(imported=imported, skipped=skipped, errors=errors[:50])
