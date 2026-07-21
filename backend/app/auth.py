"""Authentifizierung.

**Zwei Betriebsarten, automatisch erkannt.**

*Unter Home Assistant* (Ingress) hat der Supervisor den Nutzer bereits
angemeldet, bevor der Request hier ankommt, und reicht ihn über die Kopfzeilen
``X-Remote-User-Id`` und ``X-Remote-User-Name`` durch. Zählwerk übernimmt diese
Identität und legt bei Bedarf einen Datensatz an. Es gibt dort **keine**
Anmeldemaske und **kein** Passwort – ein eigener Login wäre eine zweite
Anmeldung für dieselbe Person und würde Passwort-Hashes in einer Datei
ablegen, die in jedem Backup liegt.

*Standalone* (docker-compose, direkter Port) fehlt diese Vorstufe. Dort gilt
lokale Anmeldung mit bcrypt-Hash und JWT.

**Warum HttpOnly-Cookie statt localStorage.** Ein Token im localStorage ist für
jedes Skript im Dokument lesbar; eine einzige Cross-Site-Scripting-Lücke – etwa
über eine der eingebundenen CDN-Bibliotheken – genügt, um es abzugreifen. Ein
HttpOnly-Cookie ist für JavaScript unsichtbar. Gegen Cross-Site-Request-Forgery
wirkt ``SameSite=Strict``; die Oberfläche liegt ohnehin auf demselben Ursprung
wie die API, ein zweiter Ursprung ist nicht vorgesehen.

**Verhalten bei fehlenden Bibliotheken.** Ohne ``bcrypt`` und ``PyJWT`` ist der
lokale Login nicht möglich. Unter Ingress ist das folgenlos, weil dort keine
Kryptografie gebraucht wird. Standalone verweigert die App dann den Dienst,
statt ungeschützt zu laufen – ein stilles Öffnen wäre die schlechtere Antwort.
"""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session, func, select

from .database import get_session
from .models import User

log = logging.getLogger("zaehlwerk.auth")

COOKIE_NAME = "zw_session"
TOKEN_TTL_HOURS = 24 * 14          # 14 Tage; Verlängerung bei jedem Aufruf
ALGORITHM = "HS256"

# --------------------------------------------------------------------------
# Rollen
# --------------------------------------------------------------------------
# Aufsteigend geordnet. Der Rang erlaubt Vergleiche der Form "mindestens".
ROLES = {
    "guest":  {"rank": 0, "label": "Gast",         "hint": "sieht nur Auswertungen"},
    "viewer": {"rank": 1, "label": "Leser",        "hint": "sieht alles, ändert nichts"},
    "writer": {"rank": 2, "label": "Schreiber",    "hint": "erfasst Werte und pflegt Systeme"},
    "admin":  {"rank": 3, "label": "Administrator", "hint": "zusätzlich Einstellungen und Konten"},
}
DEFAULT_ROLE = "writer"


def rank(role: str) -> int:
    return ROLES.get(role or "", {}).get("rank", -1)


def at_least(role: str, needed: str) -> bool:
    return rank(role) >= rank(needed)


# Verändernde Verfahren. Alles andere gilt als lesend.
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Zusätzliche Anforderungen je Pfadanfang. Geprüft wird der ERSTE passende
# Eintrag, deshalb stehen spezifischere Pfade oben.
#
# Aufbau: (Pfadanfang, Verfahren oder None für alle, Mindestrolle)
#
# Grundregel darunter: lesend ab "guest" bzw. "viewer", schreibend ab "writer".
# Diese Tabelle hebt nur an, wo mehr nötig ist.
ROUTE_RULES: list[tuple[str, Optional[set], str]] = [
    # Admin-Werkzeuge: Einblick in sämtliche Daten und den Systemzustand.
    # Steht bewusst an erster Stelle, damit keine spätere Regel sie aufweicht.
    ("/api/admin",        None,          "admin"),
    # Erkennung schreibt nichts, gehört aber zur Erfassung: Rolle Schreiber.
    ("/api/ocr",          None,          "writer"),
    # Eigenes Dashboard: jedes angemeldete Konto darf sein Layout lesen UND
    # schreiben. Ohne diese Ausnahme verlangte die Grundregel für schreibende
    # Verfahren die Rolle Schreiber – ein Leser könnte seine eigene Startseite
    # dann nicht einrichten.
    ("/api/user/dashboard", None,        "guest"),
    # Konten und Rollen ändern: ausschließlich Administratoren
    ("/api/auth/users",   None,          "admin"),
    # Betriebsparameter, Sicherungen, Broker, externe Dienste
    # Auch LESEND nur für Administratoren: die Antwort nennt Broker-Host,
    # Benutzernamen und Sicherungspfade.
    ("/api/settings",     None,          "admin"),
    ("/api/system/info",  None,          "viewer"),
    ("/api/backup",       None,          "admin"),
    ("/api/mqtt",         None,          "admin"),
    # Lesende Abrufe lösen ausgehende Verbindungen aus – nicht für Gäste.
    ("/api/external",     WRITE_METHODS, "admin"),
    ("/api/external",     None,          "viewer"),
    # Datenausleitung: für Gäste gesperrt, sonst lesend erlaubt
    ("/api/export",       None,          "viewer"),
    ("/api/report.pdf",   None,          "viewer"),
]


def required_role(path: str, method: str) -> str:
    """Mindestrolle für diesen Aufruf."""
    for prefix, methods, role in ROUTE_RULES:
        if path.startswith(prefix) and (methods is None or method in methods):
            return role
    return "writer" if method in WRITE_METHODS else "guest"


def permissions(role: str) -> dict:
    """Rechteübersicht für die Oberfläche. Sie entscheidet damit, was sie
    anzeigt – die Durchsetzung bleibt aber in der Middleware."""
    return {
        "role": role,
        "label": ROLES.get(role, {}).get("label", role),
        "read": at_least(role, "guest"),
        "write": at_least(role, "writer"),
        "admin": at_least(role, "admin"),
        "export": at_least(role, "viewer"),
        "settings": at_least(role, "admin"),
    }


# Diese Pfade sind ohne Anmeldung erreichbar. Bewusst kurz gehalten:
# Statusabfrage, Anmeldung, Ersteinrichtung, Health-Check.
PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/setup",
    "/api/auth/logout",
}


# --------------------------------------------------------------------------
# Abhängigkeiten
# --------------------------------------------------------------------------
def _bcrypt():
    try:
        import bcrypt
        return bcrypt
    except ImportError:
        return None


def _jwt():
    try:
        import jwt
        return jwt
    except ImportError:
        return None


def crypto_available() -> bool:
    return _bcrypt() is not None and _jwt() is not None


# --------------------------------------------------------------------------
# Betriebsart
# --------------------------------------------------------------------------
def ingress_mode() -> bool:
    """Läuft die App als Home-Assistant-Add-on hinter Ingress?"""
    return bool(os.environ.get("SUPERVISOR_TOKEN"))


def ha_user_from_request(request: Request) -> Optional[dict]:
    """Identität aus den Ingress-Kopfzeilen.

    Diesen Kopfzeilen darf nur vertraut werden, wenn der Supervisor
    tatsächlich davorsteht – sonst könnte sie jeder selbst setzen. Deshalb die
    Bindung an SUPERVISOR_TOKEN: ohne den Token gilt die Umgebung als
    Standalone und die Kopfzeilen werden ignoriert.
    """
    if not ingress_mode():
        return None
    user_id = request.headers.get("x-remote-user-id")
    if not user_id:
        return None
    return {
        "external_id": user_id,
        "username": request.headers.get("x-remote-user-name") or "ha-user",
        "display_name": request.headers.get("x-remote-user-display-name")
                        or request.headers.get("x-remote-user-name") or "Home Assistant",
    }


# --------------------------------------------------------------------------
# Passwörter
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    bcrypt = _bcrypt()
    if bcrypt is None:
        raise RuntimeError("bcrypt ist nicht installiert")
    # cost=12: rund 250 ms je Prüfung auf üblicher Hardware. Hoch genug gegen
    # Brute-Force, niedrig genug für eine Anmeldung ohne spürbare Wartezeit.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    bcrypt = _bcrypt()
    if bcrypt is None or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Schlüssel
# --------------------------------------------------------------------------
def _secret(session: Session) -> str:
    """Signaturschlüssel. Wird beim ersten Bedarf erzeugt und in der Datenbank
    abgelegt. Ein fest im Code stehender Schlüssel wäre für jede Installation
    derselbe und damit wertlos."""
    from .models import AppSetting
    row = session.get(AppSetting, "auth_jwt_secret")
    if row and row.value:
        return row.value
    value = secrets.token_urlsafe(48)
    session.merge(AppSetting(key="auth_jwt_secret", value=value))
    session.commit()
    log.info("Signaturschlüssel erzeugt")
    return value


def rotate_secret(session: Session) -> None:
    """Schlüssel wechseln – macht alle ausgegebenen Token ungültig."""
    from .models import AppSetting
    session.merge(AppSetting(key="auth_jwt_secret", value=secrets.token_urlsafe(48)))
    session.commit()


# --------------------------------------------------------------------------
# Token
# --------------------------------------------------------------------------
def create_token(user: User, session: Session) -> str:
    jwt = _jwt()
    if jwt is None:
        raise RuntimeError("PyJWT ist nicht installiert")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "name": user.username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, _secret(session), algorithm=ALGORITHM)


def decode_token(token: str, session: Session) -> Optional[dict]:
    jwt = _jwt()
    if jwt is None:
        return None
    try:
        # algorithms explizit angeben: ohne diese Angabe akzeptierte die
        # Bibliothek historisch auch "none" als Verfahren.
        return jwt.decode(token, _secret(session), algorithms=[ALGORITHM])
    except Exception:  # noqa: BLE001
        return None


def set_cookie(response: Response, token: str, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=TOKEN_TTL_HOURS * 3600,
        httponly=True,          # für JavaScript unsichtbar
        samesite="strict",      # wird bei Fremdaufrufen nicht mitgesendet
        secure=secure,          # nur über HTTPS, wenn verfügbar
        path="/",
    )


def clear_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


# --------------------------------------------------------------------------
# Nutzer
# --------------------------------------------------------------------------
def _default_role(session: Session) -> str:
    """Vorgaberolle für neu übernommene Konten, einstellbar."""
    from .models import AppSetting
    row = session.get(AppSetting, "default_role")
    value = row.value if row else None
    return value if value in ROLES else DEFAULT_ROLE


def user_count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User)).one()


def local_login_available(session: Session) -> bool:
    """Gibt es mindestens ein aktives Konto mit lokalem Passwort?

    Aus einem Home-Assistant-Add-on übernommene Konten haben
    `password_hash = None` – dort meldet der Supervisor an. Wird eine solche
    Sicherung in eine Standalone-Instanz eingespielt, existieren zwar Konten,
    aber keines kann sich lokal anmelden. Ohne diese Unterscheidung bliebe die
    Instanz dauerhaft ausgesperrt: `user_count` wäre > 0, also erschiene keine
    Ersteinrichtung, und zugleich könnte sich niemand anmelden.
    """
    row = session.exec(
        select(User)
        .where(User.aktiv == True)                       # noqa: E712
        .where(User.password_hash.is_not(None))
        .where(User.password_hash != "")
    ).first()
    return row is not None


def setup_required(session: Session) -> bool:
    """Erste Einrichtung nötig?

    Im Standalone-Betrieb gilt sie als nötig, solange sich niemand lokal
    anmelden kann – nicht nur bei null Konten (frische Instanz), sondern auch
    nach dem Einspielen einer HA-Sicherung, deren Konten kein lokales Passwort
    tragen. Sonst wäre die Instanz nach der Migration ausgesperrt.
    """
    return not ingress_mode() and not local_login_available(session)



def ensure_ha_user(session: Session, info: dict) -> User:
    """Home-Assistant-Nutzer übernehmen bzw. anlegen."""
    user = session.exec(
        select(User).where(User.external_id == info["external_id"])).first()
    if user:
        if user.display_name != info["display_name"]:
            user.display_name = info["display_name"]
            session.add(user)
            session.commit()
        return user
    # Das erste Konto wird Administrator – sonst käme niemand an die
    # Einstellungen. Alle weiteren bekommen die eingestellte Vorgabe.
    first = user_count(session) == 0
    role = "admin" if first else _default_role(session)
    user = User(username=info["username"], display_name=info["display_name"],
                external_id=info["external_id"], password_hash=None,
                role=role, is_admin=role == "admin")
    session.add(user)
    session.commit()
    session.refresh(user)
    log.info("Home-Assistant-Nutzer übernommen: %s", user.username)
    return user


# --------------------------------------------------------------------------
# Abhängigkeit für geschützte Routen
# --------------------------------------------------------------------------
def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(401, "Nicht angemeldet")
    return user


def resolve_user(request: Request, session: Session) -> Optional[User]:
    """Identität für einen Request bestimmen – erst Ingress, dann Cookie."""
    info = ha_user_from_request(request)
    if info:
        return ensure_ha_user(session, info)

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # Zusätzlich Authorization-Kopfzeile zulassen: für Skripte und
        # Fremdwerkzeuge, die keine Cookies führen.
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        return None

    payload = decode_token(token, session)
    if not payload:
        return None
    user = session.get(User, payload.get("sub"))
    if not user or not user.aktiv:
        return None
    return user
