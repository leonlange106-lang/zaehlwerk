"""Anmeldung, Abmeldung, Ersteinrichtung."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from .. import auth
from ..database import get_session
from ..models import User
from ..schemas import AuthStatus, LoginRequest, SetupRequest, UserRead, UserUpdate

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
                    source="homeassistant" if user.external_id else "lokal")


@router.get("/status", response_model=AuthStatus)
def status(request: Request, session: Session = Depends(get_session)):
    """Immer erreichbar. Die Oberfläche entscheidet daran, ob sie eine
    Anmeldemaske, die Ersteinrichtung oder direkt die App zeigt."""
    user = auth.resolve_user(request, session)
    return AuthStatus(
        mode="homeassistant" if auth.ingress_mode() else "lokal",
        authenticated=user is not None,
        setup_required=auth.setup_required(session),
        crypto_available=auth.crypto_available(),
        user=_to_read(user) if user else None,
        permissions=auth.permissions(user.role) if user else None,
        roles=[{"key": k, **v} for k, v in auth.ROLES.items()],
    )


@router.post("/setup", response_model=UserRead)
def setup(payload: SetupRequest, response: Response, request: Request,
          session: Session = Depends(get_session)):
    """Erstes Konto anlegen.

    Nur zulässig, solange KEIN Konto existiert. Andernfalls wäre der Endpunkt
    eine offene Tür, über die sich jeder ein Administratorkonto anlegen könnte.
    """
    if auth.user_count(session) > 0:
        raise HTTPException(409, "Es existiert bereits ein Konto")
    if not auth.crypto_available():
        raise HTTPException(503, "bcrypt oder PyJWT fehlen im Image")

    user = User(username=payload.username.strip().lower(),
                display_name=payload.display_name or payload.username,
                password_hash=auth.hash_password(payload.password),
                role="admin", is_admin=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    auth.set_cookie(response, auth.create_token(user, session), _is_secure(request))
    return _to_read(user)


@router.post("/login", response_model=UserRead)
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
    auth.set_cookie(response, auth.create_token(user, session), _is_secure(request))
    return _to_read(user)


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


@router.post("/password", status_code=204)
def change_password(payload: LoginRequest, request: Request,
                    user: User = Depends(auth.current_user),
                    session: Session = Depends(get_session)):
    """Passwort ändern. `username` trägt hier das bisherige Passwort."""
    if user.external_id:
        raise HTTPException(400, "Konten aus Home Assistant haben kein Passwort")
    if not auth.verify_password(payload.username, user.password_hash):
        raise HTTPException(403, "Bisheriges Passwort falsch")
    user.password_hash = auth.hash_password(payload.password)
    session.add(user)
    session.commit()
