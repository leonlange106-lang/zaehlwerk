"""Zählerstand aus einem Foto erkennen."""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import ocr
from ..auth import current_user
from ..database import get_session
from ..models import Reading, System, User

log = logging.getLogger("zaehlwerk.ocr")
router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.get("/status")
def status():
    """Ob die Erkennung einsatzbereit ist. Die Oberfläche blendet die Kamera
    andernfalls aus, statt einen Fehler erst nach dem Hochladen zu zeigen."""
    ok, missing = ocr.deps_available()
    return {"available": ok, "missing": missing,
            "max_upload_mb": round(ocr.MAX_UPLOAD_BYTES / 1024 / 1024, 1)}


@router.post("/scan")
async def scan(
    file: UploadFile = File(...),
    system_id: str | None = Form(None),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Foto auswerten.

    `system_id` ist optional, aber wirkungsvoll: mit dem zuletzt erfassten Stand
    lässt sich aus mehreren erkannten Zahlen die richtige bestimmen. Ohne ihn
    bleibt nur die Stellenzahl als Anhaltspunkt.
    """
    ok, missing = ocr.deps_available()
    if not ok:
        raise HTTPException(503, f"Erkennung nicht verfügbar – es fehlt: {missing}")

    if file.content_type and file.content_type not in ocr.ALLOWED_TYPES:
        raise HTTPException(415, f"Dateityp {file.content_type} wird nicht unterstützt")

    # Begrenzt einlesen: ohne Obergrenze ließe sich der Prozess über eine
    # beliebig große Datei zum Erliegen bringen.
    data = await file.read(ocr.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(422, "Leere Datei")
    if len(data) > ocr.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Datei größer als {ocr.MAX_UPLOAD_BYTES // 1024 // 1024} MB")

    previous = None
    if system_id:
        system = session.get(System, system_id)
        if system:
            last = session.exec(
                select(Reading).where(Reading.system_id == system.id)
                .order_by(Reading.datum.desc())
            ).first()
            previous = float(last.value) if last else None

    try:
        result = ocr.analyze(data, previous=previous)
    except Exception as exc:  # noqa: BLE001
        # Das Bild selbst nie protokollieren – nur, dass es fehlschlug.
        log.warning("Erkennung fehlgeschlagen (%s): %s", user.username, exc)
        raise HTTPException(422, f"Bild nicht auswertbar: {exc}")

    log.info("Erkennung durch %s: %s (Sicherheit %s, Vorwert %s)",
             user.username, result.get("value"), result.get("confidence"), previous)
    return {**result, "previous": previous}
