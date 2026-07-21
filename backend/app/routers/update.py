"""Selbst-Update (dezentral): Versionsprüfung, Auslösung, Rollback.

Alle Endpunkte erfordern Administratorrechte (Middleware). Das eigentliche
Ausführen übernimmt das Host-Skript – siehe app/updater.py. Unter Home Assistant
ist die Funktion nicht verfügbar (`supported() == False`).
"""
from fastapi import APIRouter, Depends, HTTPException

from .. import auth, updater
from ..models import User

router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/status")
def status(user: User = Depends(auth.current_user)):
    """Aktueller Stand: lokale vs. verfügbare Version, letzte Aktion, ob der
    Selbst-Update-Weg überhaupt eingerichtet ist (`supported`)."""
    return updater.status()


@router.post("/check")
def check(user: User = Depends(auth.current_user)):
    """Sofortige Prüfung gegen GitHub (umgeht den Intervall-Cache)."""
    updater.check_latest(force=True)
    return updater.status()


@router.post("/run")
def run(user: User = Depends(auth.current_user)):
    if not updater.supported():
        raise HTTPException(501, "Selbst-Update ist in dieser Umgebung nicht verfügbar")
    try:
        return updater.request_action("update", actor=user.username)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Update konnte nicht angefordert werden: {exc}")


@router.post("/rollback")
def rollback(user: User = Depends(auth.current_user)):
    if not updater.supported():
        raise HTTPException(501, "Rollback ist in dieser Umgebung nicht verfügbar")
    try:
        return updater.request_action("rollback", actor=user.username)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Rollback konnte nicht angefordert werden: {exc}")
