"""Anmeldung, Abmeldung, Ersteinrichtung, Zwei-Faktor, Passwortwechsel."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from .. import auth, twofactor
from ..database import get_session
from ..models import User
from ..schemas import (AuthStatus, ChangePasswordRequest, LoginRequest,
                       LoginResponse, SetupRequest, TwoFactorDisableRequest,
                       TwoFactorSetupResponse, TwoFactorVerifyRequest, UserRead,
                       UserUpdate)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _is_secure(request: Request) -> bool:
    """HTTPS erkennen – auch hinter einem Reverse Proxy."""
    if request.url.scheme == "https":
        return True
    return request.headers.get("x-forwarded-proto", "").lower() == "https"


def _to_read(user: User) -> UserRead:
    return UserRead(id=user.id, username=user.username,
                    display_name=user.display_name or user.username,
                    role=user.role, is_admin=auth.at_least(user.role, "admin"),
                    aktiv=user.aktiv,
                    source="homeassistant" if user.external_id else "lokal",
                    two_factor_enabled=bool(user.two_factor_enabled),
                    is_first_login=bool(user.is_first_login),
                    temp_password_active=bool(user.temp_password_active))


@router.get("/status", response_model=AuthStatus)
def status(request: Request, session: Session = Depends(get_session)):
    """Immer erreichbar. Die Oberfläche entscheidet daran, ob sie eine
    Anmeldemaske, die Ersteinrichtung oder direkt die App zeigt."""
    user = auth.resolve_user(request, session)
    needs_setup = auth.setup_required(session)
    return AuthStatus(
        mode="homeassistant" if auth.ingress_mode() else "lokal",
        authenticated=user is not None,
        setup_required=needs_setup,
        # Wiederherstellungsfall: Einrichtung nötig, obwohl schon Konten da sind.
        recovery=needs_setup and auth.user_count(session) > 0,
        crypto_available=auth.crypto_available(),
        user=_to_read(user) if user else None,
        permissions=auth.permissions(user.role) if user else None,
        roles=[{"key": k, **v} for k, v in auth.ROLES.items()],
    )


@router.post("/setup", response_model=UserRead)
def setup(payload: SetupRequest, response: Response, request: Request,
          session: Session = Depends(get_session)):
    """Erstes lokales Administratorkonto anlegen.

    Zulässig, solange sich niemand lokal anmelden kann (`setup_required`): auf
    einer frischen Instanz (kein Konto) genauso wie im Wiederherstellungsfall,
    wenn eine eingespielte HA-Sicherung nur Konten ohne lokales Passwort
    enthält. Sobald ein anmeldbares Konto existiert, ist der Endpunkt zu –
    sonst wäre er eine offene Tür für ein beliebiges Administratorkonto.
    """
    if not auth.setup_required(session):
        raise HTTPException(409, "Es existiert bereits ein anmeldbares Konto")
    if not auth.crypto_available():
        raise HTTPException(503, "bcrypt oder PyJWT fehlen im Image")

    username = payload.username.strip().lower()
    # Wiederherstellungsfall: trägt ein bereits vorhandenes Konto (z. B. aus
    # der HA-Sicherung) denselben Namen, wird es übernommen – Passwort setzen,
    # aktivieren, zum Administrator machen – statt eine zweite Kennung anzulegen.
    # So kann der Nutzer sein gewohntes Konto "adoptieren"; ein neuer Name legt
    # dagegen ein frisches Administratorkonto an.
    user = session.exec(select(User).where(User.username == username)).first()
    if user:
        user.password_hash = auth.hash_password(payload.password)
        user.aktiv = True
        user.role = "admin"
        user.is_admin = True
        if payload.display_name:
            user.display_name = payload.display_name
    else:
        user = User(username=username,
                    display_name=payload.display_name or payload.username,
                    password_hash=auth.hash_password(payload.password),
                    role="admin", is_admin=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    auth.set_cookie(response, auth.create_token(user, session), _is_secure(request))
    return _to_read(user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, request: Request,
          session: Session = Depends(get_session)):
    if auth.ingress_mode():
        raise HTTPException(400, "Unter Home Assistant erfolgt die Anmeldung bereits dort")
    if not auth.crypto_available():
        raise HTTPException(503, "bcrypt oder PyJWT fehlen im Image")

    user = session.exec(
        select(User).where(User.username == payload.username.strip().lower())).first()

    # Gleiche Meldung für unbekannten Benutzer und falsches Passwort: sonst
    # ließe sich über die Antwort ermitteln, welche Benutzernamen existieren.
    if not user or not user.aktiv or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Benutzername oder Passwort falsch")

    user.letzter_login = datetime.utcnow()
    session.add(user)
    session.commit()

    # Erstanmeldung: volles Cookie, aber die Middleware sperrt bis zum Abschluss
    # des Onboardings (Passwortwechsel + 2FA) alle regulären Routen.
    if user.is_first_login:
        auth.set_cookie(response, auth.create_token(user, session), _is_secure(request))
        return LoginResponse(
            status="REQUIRES_FIRST_TIME_SETUP",
            needs_password_change=bool(user.temp_password_active),
            needs_2fa_setup=not bool(user.two_factor_enabled),
        )

    # Zweiter Faktor aktiv: NICHT voll anmelden, nur ein kurzlebiges
    # Zwischentoken ausgeben. Die volle Sitzung entsteht erst nach /2fa/verify.
    if user.two_factor_enabled:
        auth.set_cookie(response, auth.create_token(user, session, stage=auth.STAGE_2FA),
                        _is_secure(request))
        return LoginResponse(status="REQUIRES_2FA")

    auth.set_cookie(response, auth.create_token(user, session), _is_secure(request))
    return LoginResponse(status="SUCCESS", user=_to_read(user))


def _maybe_finish_onboarding(user: User) -> None:
    """Onboarding gilt als abgeschlossen, sobald das temporäre Passwort ersetzt
    UND 2FA eingerichtet ist. Dann fällt die Erstanmelde-Sperre weg."""
    if user.is_first_login and not user.temp_password_active and user.two_factor_enabled:
        user.is_first_login = False


@router.post("/logout", status_code=204)
def logout(response: Response):
    auth.clear_cookie(response)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(auth.current_user)):
    return _to_read(user)


@router.get("/users", response_model=list[UserRead])
def list_users(user: User = Depends(auth.current_user),
               session: Session = Depends(get_session)):
    rows = session.exec(select(User).order_by(User.username)).all()
    return [_to_read(u) for u in rows]


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: str, payload: UserUpdate,
                actor: User = Depends(auth.current_user),
                session: Session = Depends(get_session)):
    """Rolle oder Aktivstatus ändern."""
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(404, "Konto nicht gefunden")

    data = payload.model_dump(exclude_unset=True)
    new_role = data.get("role", target.role)
    new_aktiv = data.get("aktiv", target.aktiv)

    # Sperre gegen das Aussperren: der letzte aktive Administrator darf sich
    # weder herabstufen noch deaktivieren. Sonst käme niemand mehr an die
    # Einstellungen und die Rollenverwaltung.
    if auth.at_least(target.role, "admin") and target.aktiv:
        losing = not auth.at_least(new_role, "admin") or not new_aktiv
        if losing:
            remaining = [u for u in session.exec(select(User)).all()
                         if u.id != target.id and u.aktiv and auth.at_least(u.role, "admin")]
            if not remaining:
                raise HTTPException(
                    409, "Das ist der letzte aktive Administrator – "
                         "erst ein weiteres Konto zum Administrator machen.")

    if "role" in data:
        if data["role"] not in auth.ROLES:
            raise HTTPException(422, "Unbekannte Rolle")
        target.role = data["role"]
        target.is_admin = auth.at_least(target.role, "admin")
    if "aktiv" in data:
        target.aktiv = bool(data["aktiv"])
    session.add(target)
    session.commit()
    session.refresh(target)
    return _to_read(target)


@router.post("/change-password", response_model=UserRead)
def change_password(payload: ChangePasswordRequest, request: Request,
                    user: User = Depends(auth.current_user),
                    session: Session = Depends(get_session)):
    """Eigenes Passwort ändern (Self-Service, auch als erster Onboarding-Schritt).

    Prüft das bisherige Passwort und setzt die serverseitigen
    Komplexitätsregeln durch. Im Erstanmelde-Fall wird damit zugleich das
    temporäre Passwort entwertet."""
    if user.external_id:
        raise HTTPException(400, "Konten aus Home Assistant haben kein Passwort")
    if not auth.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(403, "Bisheriges Passwort falsch")
    try:
        auth.validate_password(payload.new_password, username=user.username,
                               current_hash=user.password_hash)
    except auth.PasswordPolicyError as exc:
        raise HTTPException(422, str(exc))

    user.password_hash = auth.hash_password(payload.new_password)
    user.temp_password_active = False          # temporäres Passwort ist entwertet
    _maybe_finish_onboarding(user)
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_read(user)


# --------------------------------------------------------------------------
# Zwei-Faktor-Authentifizierung (TOTP)
# --------------------------------------------------------------------------
@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def twofactor_setup(user: User = Depends(auth.current_user),
                    session: Session = Depends(get_session)):
    """Erzeugt (oder erneuert, solange noch nicht aktiviert) das TOTP-Secret,
    speichert es verschlüsselt und liefert QR-Code + otpauth-URI. Erst
    /2fa/verify aktiviert die zweite Stufe."""
    if user.external_id:
        raise HTTPException(400, "Konten aus Home Assistant nutzen die HA-Anmeldung")
    if user.two_factor_enabled:
        raise HTTPException(409, "Zwei-Faktor ist bereits aktiv")
    secret = twofactor.generate_secret()
    user.two_factor_secret = twofactor.encrypt(secret)
    session.add(user)
    session.commit()
    uri = twofactor.otpauth_uri(secret, user.username)
    return TwoFactorSetupResponse(secret=secret, otpauth_uri=uri,
                                  qr_data_uri=twofactor.qr_data_uri(uri))


@router.post("/2fa/verify", response_model=LoginResponse)
def twofactor_verify(payload: TwoFactorVerifyRequest, response: Response,
                     request: Request, session: Session = Depends(get_session)):
    """Verifiziert einen TOTP-Code. Zwei Kontexte:

    - **Einrichtung** (voll angemeldet): aktiviert die zweite Stufe.
    - **Anmeldung** (kurzlebiges 2fa-Zwischentoken): schliesst den Login ab und
      gibt die volle Sitzung aus.
    """
    # Kontext 1: bereits vollwertig angemeldet -> Einrichtung abschliessen.
    full_user = auth.resolve_user(request, session)
    if full_user is not None:
        secret = twofactor.decrypt(full_user.two_factor_secret)
        if not secret:
            raise HTTPException(409, "Kein Secret vorbereitet – zuerst /2fa/setup aufrufen")
        if not twofactor.verify(secret, payload.code):
            raise HTTPException(401, "Code ungültig")
        full_user.two_factor_enabled = True
        _maybe_finish_onboarding(full_user)
        session.add(full_user)
        session.commit()
        session.refresh(full_user)
        return LoginResponse(status="SUCCESS", user=_to_read(full_user))

    # Kontext 2: Login-Zwischenschritt (nur 2fa-Zwischentoken vorhanden).
    pending = auth.resolve_pending_2fa(request, session)
    if pending is None:
        raise HTTPException(401, "Keine offene Anmeldung")
    secret = twofactor.decrypt(pending.two_factor_secret)
    if not secret or not twofactor.verify(secret, payload.code):
        raise HTTPException(401, "Code ungültig")
    auth.set_cookie(response, auth.create_token(pending, session), _is_secure(request))
    return LoginResponse(status="SUCCESS", user=_to_read(pending))


@router.post("/2fa/disable", response_model=UserRead)
def twofactor_disable(payload: TwoFactorDisableRequest,
                      user: User = Depends(auth.current_user),
                      session: Session = Depends(get_session)):
    """Zwei-Faktor abschalten. Verlangt Passwort UND einen gültigen Code, damit
    ein kurzzeitig unbeaufsichtigter Login das nicht heimlich tun kann."""
    if not user.two_factor_enabled:
        raise HTTPException(409, "Zwei-Faktor ist nicht aktiv")
    if not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(403, "Passwort falsch")
    secret = twofactor.decrypt(user.two_factor_secret)
    if not secret or not twofactor.verify(secret, payload.code):
        raise HTTPException(401, "Code ungültig")
    user.two_factor_enabled = False
    user.two_factor_secret = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return _to_read(user)
