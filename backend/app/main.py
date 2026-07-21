"""Zählwerk – FastAPI-App. Liefert API + Frontend (statisch) aus einem Prozess."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from sqlmodel import Session

from .database import engine, init_db
from .version import APP_VERSION
from . import (audit, auth as auth_mod, backup as backup_mod, mqtt_client,
               notifier, outbound, updater as updater_mod)
from .routers import (admin, auth as auth_router, backups, dashboard, external,
                      ha, imports, meters, mqtt, ocr as ocr_router, readings,
                      settings as settings_router, systems, tariffs,
                      update as update_router)

app = FastAPI(
    title="Zählwerk API",
    version=APP_VERSION,
    description=(
        "Verbrauchs- und Zählerstands-Tracking (Strom, Gas, Wasser, PV). "
        "Die interaktive Dokumentation liegt unter `/docs` (Swagger UI) und "
        "`/redoc`, das maschinenlesbare Schema unter `/openapi.json`. Die "
        "Contract-Tests im Ordner `tests/` prüfen dieses Schema gegen die "
        "Felder, auf die das Frontend angewiesen ist."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(ocr_router.router)
app.include_router(auth_router.router)
app.include_router(systems.router)
app.include_router(readings.router)
app.include_router(imports.router)
app.include_router(backups.router)
app.include_router(external.router)
app.include_router(meters.router)
app.include_router(tariffs.router)
app.include_router(mqtt.router)
app.include_router(settings_router.router)
app.include_router(ha.router)
app.include_router(update_router.router)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Schützt sämtliche /api-Pfade.

    Reihenfolge der Prüfungen:
      1. Nicht-/api-Pfade (Oberfläche, statische Dateien) laufen durch – ohne
         sie käme nicht einmal die Anmeldemaske zustande.
      2. Pfade aus PUBLIC_PATHS laufen durch.
      3. Identität bestimmen: erst Ingress-Kopfzeilen, dann Cookie bzw.
         Authorization-Kopfzeile.
      4. Keine Identität -> 401. Die Oberfläche wertet das aus und zeigt die
         Anmeldung, statt den Nutzer auf einem Fehler stehen zu lassen.

    Der Nutzer wird an request.state gehängt, damit einzelne Routen ihn über
    die Abhängigkeit current_user beziehen können, ohne erneut zu prüfen.
    """
    path = request.url.path
    if not path.startswith("/api") or path in auth_mod.PUBLIC_PATHS:
        return await call_next(request)

    with Session(engine) as session:
        # Solange kein Konto existiert, ist die Ersteinrichtung offen. Die App
        # sperrt sich sonst selbst aus, bevor ein Konto angelegt werden kann.
        if auth_mod.setup_required(session):
            return await call_next(request)
        user = auth_mod.resolve_user(request, session)

    if user is None:
        return JSONResponse({"detail": "Nicht angemeldet"}, status_code=401)

    # ---------- Erstanmelde-Zwang ----------
    # Solange das Onboarding (Passwortwechsel + 2FA) nicht abgeschlossen ist,
    # bleibt der Zugriff auf alles ausser den Onboarding-Routen gesperrt.
    if getattr(user, "is_first_login", False) and path not in auth_mod.ONBOARDING_ALLOWED:
        return JSONResponse(
            {"detail": "Erstanmeldung erforderlich", "status": "REQUIRES_FIRST_TIME_SETUP"},
            status_code=403,
        )

    # ---------- Autorisierung ----------
    # Die Prüfung sitzt bewusst hier und nicht in den einzelnen Routen: eine
    # neue Route ist damit automatisch abgedeckt, statt erst durch eine
    # vergessene Absicherung offen zu stehen.
    needed = auth_mod.required_role(path, request.method)
    if not auth_mod.at_least(user.role, needed):
        return JSONResponse({
            "detail": f"Keine Berechtigung. Erforderlich: "
                      f"{auth_mod.ROLES.get(needed, {}).get('label', needed)}, "
                      f"vorhanden: {auth_mod.ROLES.get(user.role, {}).get('label', user.role)}."
        }, status_code=403)

    request.state.user = user
    # Konto für das Änderungsprotokoll hinterlegen. Muss nach der Anfrage
    # zurückgesetzt werden, sonst schriebe der nächste Aufruf im selben
    # Arbeitsfaden unter fremdem Namen.
    audit.set_actor(user)
    try:
        return await call_next(request)
    finally:
        audit.clear_actor()


@app.on_event("startup")
async def _startup():
    # Reihenfolge zwingend: Guard VOR allem anderen installieren, damit keine
    # Verbindung in der Startphase durchrutscht. Der Guard laesst im Zweifel
    # nichts nach draussen - die Flagge startet auf True.
    # Protokollpuffer vor allem anderen: sonst fehlen die Meldungen der
    # Startphase genau dann, wenn man sie braucht.
    admin.install_log_buffer()
    # Vor init_db: die Ereignisse sollen auch Änderungen aus Migrationen und
    # dem Startvorgang erfassen.
    audit.install()
    outbound.install_socket_guard()
    init_db()
    if not auth_mod.ingress_mode() and not auth_mod.crypto_available():
        # Ein stilles Weiterlaufen waere hier die schlechtere Antwort: die App
        # stuende ohne jeden Schutz im Netz.
        raise RuntimeError(
            "Standalone-Betrieb ohne bcrypt/PyJWT: Anmeldung nicht moeglich. "
            "Image mit aktueller requirements.txt neu bauen.")
    from .routers.settings import get_setting
    outbound.set_offline(bool(get_setting("offline_mode", True)))
    import asyncio
    asyncio.create_task(notifier.watcher())
    asyncio.create_task(backup_mod.scheduler())
    asyncio.create_task(updater_mod.check_scheduler())
    # MQTT nach dem Socket-Guard starten: ein Broker im eigenen Netz ist von
    # der Sperre nicht betroffen, ein oeffentlicher schon - und genau so soll es sein.
    await asyncio.to_thread(mqtt_client.boot)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version, "db": settings.sqlite_path}


# Frontend statisch mit ausliefern (ein Prozess, ein Port)
_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
