"""Admin-Monitoring: Kontostatus, Sicherheits-Metriken, Session-Kontrolle.

Grundlage für das Web-Admin-Dashboard (TICKET-1.3) und die native iOS-Admin-
Console (TICKET-1.4). Sämtliche Endpunkte liegen unter `/api/admin` und sind
damit über die zentrale Rollen-Middleware auf Administratoren beschränkt.
Alle Daten stammen aus der zentralen System-DB (Konten + Sitzungen).
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from .. import auth
from ..database import get_system_session
from ..models import User, UserSession

router = APIRouter(prefix="/api/admin/monitoring", tags=["admin-monitoring"])

# Ab wann gilt ein Konto als „offline": keine Aktivität in diesem Fenster.
ONLINE_WINDOW = timedelta(minutes=5)


def _current_jti(request: Request, session: Session) -> str | None:
    token = request.cookies.get(auth.COOKIE_NAME)
    if not token:
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        return None
    payload = auth.decode_token(token, session)
    return payload.get("jti") if payload else None


def _active_sessions(session: Session, user_id: str) -> list[UserSession]:
    now = datetime.utcnow()
    return session.exec(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.revoked == False)          # noqa: E712
        .where(UserSession.expires_at > now)
        .order_by(UserSession.last_seen.desc())
    ).all()


@router.get("/users")
def monitoring_users(user: User = Depends(auth.current_user),
                     sys: Session = Depends(get_system_session)):
    """Konten mit Live-Status und Sicherheits-Metriken (Account Monitoring)."""
    now = datetime.utcnow()
    out = []
    for u in sys.exec(select(User).order_by(User.username)).all():
        sessions = _active_sessions(sys, u.id)
        last_seen = sessions[0].last_seen if sessions else u.letzter_login
        online = bool(sessions and (now - sessions[0].last_seen) <= ONLINE_WINDOW)
        # Passwort-Status: temporär (erzwungener Wechsel) / gesetzt / keins (HA).
        if u.temp_password_active:
            password_status = "temporär"
        elif u.password_hash:
            password_status = "dauerhaft"
        else:
            password_status = "extern"
        out.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name or u.username,
            "role": u.role,
            "is_admin": u.is_admin,
            "aktiv": u.aktiv,
            "source": "homeassistant" if u.external_id else "lokal",
            "two_factor_enabled": bool(u.two_factor_enabled),
            "two_factor_status": "eingerichtet" if u.two_factor_enabled else "ausstehend",
            "password_status": password_status,
            "is_first_login": bool(u.is_first_login),
            "last_seen": last_seen.isoformat() if last_seen else None,
            "online": online,
            "active_sessions": len(sessions),
        })
    return out


@router.get("/sessions")
def monitoring_sessions(request: Request,
                        user: User = Depends(auth.current_user),
                        sys: Session = Depends(get_system_session)):
    """Alle aktiven Sitzungen über alle Konten hinweg."""
    current = _current_jti(request, sys)
    names = {u.id: (u.display_name or u.username) for u in sys.exec(select(User)).all()}
    now = datetime.utcnow()
    rows = sys.exec(
        select(UserSession)
        .where(UserSession.revoked == False)          # noqa: E712
        .where(UserSession.expires_at > now)
        .order_by(UserSession.last_seen.desc())
    ).all()
    return [{
        "jti": s.jti,
        "user_id": s.user_id,
        "username": names.get(s.user_id, s.user_id),
        "created_at": s.created_at.isoformat(),
        "last_seen": s.last_seen.isoformat(),
        "expires_at": s.expires_at.isoformat(),
        "user_agent": s.user_agent,
        "ip": s.ip,
        "current": s.jti == current,
    } for s in rows]


@router.delete("/sessions/{jti}")
def terminate_session(jti: str,
                      user: User = Depends(auth.current_user),
                      sys: Session = Depends(get_system_session)):
    """Eine einzelne Sitzung per Admin-Override zwangsweise beenden."""
    if not auth.revoke_session(sys, jti):
        raise HTTPException(404, "Sitzung nicht gefunden oder bereits beendet")
    return {"terminated": True}


@router.post("/users/{user_id}/logout")
def terminate_user_sessions(user_id: str,
                            user: User = Depends(auth.current_user),
                            sys: Session = Depends(get_system_session)):
    """Alle Sitzungen eines Kontos per Admin-Override beenden."""
    if sys.get(User, user_id) is None:
        raise HTTPException(404, "Nutzer nicht gefunden")
    count = auth.revoke_user_sessions(sys, user_id)
    return {"terminated": count}
