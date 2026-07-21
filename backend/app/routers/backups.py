"""Sicherungen: Status, manuelle Auslösung, Download, Bereinigung, Wiederherstellung."""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from .. import auth
from .. import backup as bk
from ..database import get_session
from ..schemas import BackupStatus, RestoreResult
from .settings import read_settings

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("", response_model=BackupStatus)
def status(session: Session = Depends(get_session)):
    cfg = read_settings(session)
    entries = bk.list_backups()
    directory = bk.backup_dir()
    return BackupStatus(
        enabled=bool(cfg.get("backup_enabled", True)),
        directory=str(directory),
        supervisor_backup_dir=directory == bk.PRIMARY_DIR,
        time=str(cfg.get("backup_time", "03:30")),
        keep_days=int(cfg.get("backup_keep_days", 7)),
        entries=entries,
        total_bytes=sum(e["size_bytes"] for e in entries),
    )


@router.post("/run")
def run_now(session: Session = Depends(get_session)):
    """Manuelle Sicherung. Läuft synchron – bei den hier üblichen Datenmengen
    dauert das Millisekunden, und die Rückmeldung soll den echten Ausgang
    zeigen statt nur die Annahme des Auftrags."""
    keep = int(read_settings(session).get("backup_keep_days", 7))
    try:
        return bk.run_once(keep)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Sicherung fehlgeschlagen: {exc}")


@router.post("/prune")
def prune_now(session: Session = Depends(get_session)):
    keep = int(read_settings(session).get("backup_keep_days", 7))
    return {"removed": bk.prune(keep)}


@router.get("/{filename}")
def download(filename: str):
    """Herunterladen. Der Dateiname wird gegen das eigene Muster geprüft –
    ohne das wäre der Parameter ein Pfad-Traversal auf das Dateisystem."""
    if not bk.FILENAME_RE.match(filename):
        raise HTTPException(400, "Ungültiger Dateiname")
    path: Path = bk.backup_dir() / filename
    if not path.is_file():
        raise HTTPException(404, "Sicherung nicht gefunden")
    return FileResponse(path, media_type="application/gzip", filename=filename)


@router.delete("/{filename}", status_code=204)
def remove(filename: str):
    if not bk.FILENAME_RE.match(filename):
        raise HTTPException(400, "Ungültiger Dateiname")
    (bk.backup_dir() / filename).unlink(missing_ok=True)


@router.post("/restore/{filename}", response_model=RestoreResult)
def restore(filename: str, response: Response):
    """Stellt die Datenbank aus einer bereits vorhandenen eigenen Sicherung
    wieder her. Der Dateiname wird wie beim Download/Löschen gegen das eigene
    Muster geprüft – ohne das wäre der Parameter ein Pfad-Traversal."""
    if not bk.FILENAME_RE.match(filename):
        raise HTTPException(400, "Ungültiger Dateiname")
    path = bk.backup_dir() / filename
    try:
        result = bk.restore_from_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except bk.RestoreError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Wiederherstellung fehlgeschlagen: {exc}")
    # Die wiederhergestellte Datenbank bringt ihren eigenen Signaturschlüssel
    # mit (app_settings.auth_jwt_secret) - das noch im Browser liegende Cookie
    # ist damit ab jetzt ungültig. Explizit löschen statt es dem nächsten,
    # fehlschlagenden Aufruf zu überlassen: sonst wertet die Oberfläche einen
    # stillen 401-Folgefehler fälschlich als "Wiederherstellung fehlgeschlagen",
    # obwohl sie gerade erfolgreich war.
    auth.clear_cookie(response)
    return result


@router.post("/import", response_model=RestoreResult)
async def import_and_restore(response: Response, file: UploadFile = File(...)):
    """Stellt die Datenbank aus einer hochgeladenen gzip-Sicherung wieder her.

    Die Datei landet zunächst in einer temporären Datei außerhalb des
    Sicherungsverzeichnisses – erst `restore_from_file` entscheidet nach
    erfolgreicher Prüfung, ob sie live geschaltet wird."""
    content = await file.read()
    if len(content) > bk.MAX_IMPORT_BYTES:
        raise HTTPException(413, "Datei zu groß")
    if not content:
        raise HTTPException(400, "Leere Datei")

    tmp = tempfile.NamedTemporaryFile(suffix=".gz", delete=False)
    tmp_path = Path(tmp.name)
    try:
        tmp.write(content)
        tmp.close()
        result = bk.restore_from_file(tmp_path)
    except bk.RestoreError as exc:
        raise HTTPException(422, str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Wiederherstellung fehlgeschlagen: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)
    # Siehe restore(): das Browser-Cookie ist mit dem Signaturschlüssel der
    # NEUEN Datenbank nicht mehr gültig - explizit löschen statt es beim
    # nächsten Aufruf als rätselhaften 401 auflaufen zu lassen.
    auth.clear_cookie(response)
    return result
