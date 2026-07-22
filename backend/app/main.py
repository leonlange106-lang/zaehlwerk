"""Zählwerk – FastAPI-App. Liefert API + Frontend (statisch) aus einem Prozess."""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

log = logging.getLogger("zaehlwerk.main")

from .config import settings
from sqlmodel import Session

from .database import engine, system_engine, tenant_engine, init_db
from .version import APP_VERSION
from . import (audit, auth as auth_mod, backup as backup_mod, cf_access, mqtt_client,
               notifier, outbound, tenancy, updater as updater_mod)
from .routers import (admin, auth as auth_router, backups, billing, dashboard,
                      databases as databases_router, external,
                      ha, imports, meters, monitoring as monitoring_router,
                      mqtt, ocr as ocr_router, readings,
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
app.include_router(databases_router.router)
app.include_router(monitoring_router.router)
app.include_router(dashboard.router)
app.include_router(ocr_router.router)
app.include_router(auth_router.router)
app.include_router(systems.router)
app.include_router(readings.router)
app.include_router(billing.router)
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
async def cf_access_middleware(request: Request, call_next):
    """Optionale Cloudflare-Access-Prüfung (TICKET-5.1). Nur aktiv, wenn
    konfiguriert; validiert das Access-JWT VOR der eigentlichen Anmeldung.
    Läuft vor auth_middleware (zuletzt registriert = äußerste Schicht)."""
    path = request.url.path
    if cf_access.enabled() and path.startswith("/api") and path != "/api/health":
        token = cf_access.token_from_request(request.headers, request.cookies)
        if not token:
            return JSONResponse({"detail": "Cloudflare Access erforderlich"}, status_code=403)
        try:
            await run_in_threadpool(cf_access.verify, token)
        except Exception as exc:  # noqa: BLE001 – jede Ursache = Ablehnung
            log.warning("Cloudflare-Access-Token abgelehnt: %s", exc)
            return JSONResponse({"detail": "Cloudflare Access: Zugriff verweigert"}, status_code=403)
    return await call_next(request)


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

    # Identität & aktive Mandanten-DB werden gegen die zentrale System-DB
    # aufgelöst (Konten und Routing liegen dort, nicht in den Fachdaten).
    active = None
    with Session(system_engine) as session:
        # Solange kein Konto existiert, ist die Ersteinrichtung offen. Die App
        # sperrt sich sonst selbst aus, bevor ein Konto angelegt werden kann.
        if auth_mod.setup_required(session):
            return await call_next(request)
        user = auth_mod.resolve_user(request, session)
        if user is not None:
            requested_db = request.headers.get("x-zaehlwerk-database")
            active = tenancy.resolve_active(session, user, requested_db)

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

    # ---------- Aktive Mandanten-DB festlegen ----------
    # get_session() liest diese Engine; ohne sie fiele der Request auf den
    # Standard-Mandanten zurück (rückwärtskompatibel).
    if active is not None:
        request.state.tenant_engine = tenant_engine(active["path"])
        request.state.db_role = active["role"]
        request.state.active_db_id = active["id"]
        request.state.active_db_name = active["name"]

        # ---------- Nur-Lese-Freigaben durchsetzen ----------
        # Schreibende Fachzugriffe auf eine read_only freigegebene DB werden
        # zentral abgewiesen. Konto-/Freigabe-Routen (System-DB) bleiben frei.
        if (request.method in auth_mod.WRITE_METHODS
                and active["role"] == "read_only"
                and not path.startswith(("/api/auth", "/api/databases", "/api/admin"))):
            return JSONResponse(
                {"detail": "Nur-Lese-Zugriff auf diese Datenbank."},
                status_code=403,
            )

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
    # REST-Poller: fragt Geräte mit hinterlegter rest_url ab. Nach dem
    # Socket-Guard gestartet, damit die Kill-Switch-Regeln greifen (lokale Ziele
    # bleiben erreichbar, öffentliche werden im Offline-Modus blockiert).
    from . import rest_poller
    asyncio.create_task(rest_poller.scheduler())
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
