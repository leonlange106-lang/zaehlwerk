"""Admin-Monitoring & Session-Kontrolle (TICKET-1.3-Backend).

Deckt ab: Kontostatus/Sicherheits-Metriken, aktive Sitzungen, Zwangs-Abmeldung
per Admin-Override sowie den server-seitigen Widerruf beim regulären Logout.
"""
import pyotp
from fastapi.testclient import TestClient

from app.main import app


def _create_user(client, username, role="writer"):
    r = client.post("/api/admin/users/create", json={"username": username, "role": role})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["user"]["id"], body["temp_password"]


def _onboard(username, temp, new_password):
    c = TestClient(app)
    c.post("/api/auth/login", json={"username": username, "password": temp})
    c.post("/api/auth/change-password",
           json={"current_password": temp, "new_password": new_password})
    secret = c.post("/api/auth/2fa/setup").json()["secret"]
    c.post("/api/auth/2fa/verify", json={"code": pyotp.TOTP(secret).now()})
    return c


def test_monitoring_users_reports_status(client):
    rows = client.get("/api/admin/monitoring/users").json()
    admin = next(r for r in rows if r["role"] == "admin")
    assert admin["online"] is True
    assert admin["two_factor_status"] in ("eingerichtet", "ausstehend")
    assert admin["password_status"] == "dauerhaft"
    assert admin["active_sessions"] >= 1


def test_sessions_list_marks_current(client):
    sessions = client.get("/api/admin/monitoring/sessions").json()
    assert any(s["current"] for s in sessions)


def test_admin_can_force_terminate_session(client):
    uid, temp = _create_user(client, "kick.me")
    victim = _onboard("kick.me", temp, "kick-passwort-123")
    # Opfer ist angemeldet und kommt an geschützte Routen.
    assert victim.get("/api/systems").status_code == 200

    # Admin findet die Sitzung des Opfers und beendet sie.
    sessions = client.get("/api/admin/monitoring/sessions").json()
    jti = next(s["jti"] for s in sessions if s["user_id"] == uid)
    assert client.delete(f"/api/admin/monitoring/sessions/{jti}").status_code == 200

    # Ab jetzt ist das Token des Opfers ungültig (Zwangs-Abmeldung greift sofort).
    assert victim.get("/api/systems").status_code == 401


def test_terminate_all_user_sessions(client):
    uid, temp = _create_user(client, "multi.session")
    a = _onboard("multi.session", temp, "multi-passwort-123")
    assert a.get("/api/systems").status_code == 200

    r = client.post(f"/api/admin/monitoring/users/{uid}/logout")
    assert r.status_code == 200 and r.json()["terminated"] >= 1
    assert a.get("/api/systems").status_code == 401


def test_logout_revokes_session_server_side(client):
    uid, temp = _create_user(client, "logout.user")
    c = _onboard("logout.user", temp, "logout-passwort-123")
    assert c.get("/api/systems").status_code == 200
    c.post("/api/auth/logout")
    # Selbst mit weiterhin gesetztem Cookie ist die Sitzung serverseitig beendet.
    assert c.get("/api/systems").status_code == 401
