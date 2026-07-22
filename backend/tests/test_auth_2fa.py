"""Vollständiger Lebenszyklus: Admin legt Nutzer an -> Temp-Passwort ->
erzwungenes Onboarding (Passwortwechsel + 2FA) -> Folge-Login verlangt 2FA.

Deckt zusätzlich die Passwort-Komplexitätsregeln, das Middleware-Gate und den
Verschlüsselungs-Roundtrip der TOTP-Secrets ab.
"""
import pyotp
from fastapi.testclient import TestClient

from app import twofactor
from app.main import app


def _totp(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def test_full_user_lifecycle(client):
    # 1) Admin legt ein Konto an -> temporäres Passwort wird einmalig geliefert.
    r = client.post("/api/admin/users/create",
                    json={"username": "neu.user", "display_name": "Neu", "role": "writer"})
    assert r.status_code == 201, r.text
    body = r.json()
    temp = body["temp_password"]
    assert len(temp) >= 12
    assert body["user"]["is_first_login"] is True

    nc = TestClient(app)   # eigener Cookie-Jar für den neuen Nutzer

    # 2) Erst-Login mit Temp-Passwort -> Onboarding erzwungen.
    r = nc.post("/api/auth/login", json={"username": "neu.user", "password": temp})
    assert r.status_code == 200
    assert r.json()["status"] == "REQUIRES_FIRST_TIME_SETUP"
    assert r.json()["needs_password_change"] is True
    assert r.json()["needs_2fa_setup"] is True

    # 3) Middleware-Gate: reguläre Route ist gesperrt.
    assert nc.get("/api/systems").status_code == 403

    # 4) Schwaches Passwort wird serverseitig abgelehnt.
    assert nc.post("/api/auth/change-password",
                   json={"current_password": temp, "new_password": "kurz"}).status_code == 422
    # Gleich dem Benutzernamen -> abgelehnt.
    assert nc.post("/api/auth/change-password",
                   json={"current_password": temp, "new_password": "neu.user"}).status_code == 422

    # 5) Gültiger Passwortwechsel -> Temp-Passwort entwertet, aber weiter gesperrt
    #    (2FA fehlt noch).
    r = nc.post("/api/auth/change-password",
                json={"current_password": temp, "new_password": "mein-neues-passwort-1"})
    assert r.status_code == 200, r.text
    assert r.json()["temp_password_active"] is False
    assert r.json()["is_first_login"] is True
    assert nc.get("/api/systems").status_code == 403

    # 6) 2FA einrichten + verifizieren -> Onboarding abgeschlossen.
    r = nc.post("/api/auth/2fa/setup")
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    assert r.json()["qr_data_uri"].startswith("data:image/svg+xml;base64,")
    r = nc.post("/api/auth/2fa/verify", json={"code": _totp(secret)})
    assert r.status_code == 200 and r.json()["status"] == "SUCCESS"
    assert r.json()["user"]["is_first_login"] is False
    assert r.json()["user"]["two_factor_enabled"] is True

    # 7) Voller Zugriff.
    assert nc.get("/api/systems").status_code == 200

    # 8) Abmelden, erneut anmelden -> zweite Stufe verlangt.
    nc.post("/api/auth/logout")
    r = nc.post("/api/auth/login",
                json={"username": "neu.user", "password": "mein-neues-passwort-1"})
    assert r.json()["status"] == "REQUIRES_2FA"
    # Nur Zwischentoken -> reguläre Route bleibt gesperrt (401, keine volle Sitzung).
    assert nc.get("/api/systems").status_code == 401

    # 9) Falscher Code -> abgelehnt; richtiger Code -> volle Sitzung.
    assert nc.post("/api/auth/2fa/verify", json={"code": "000000"}).status_code == 401
    r = nc.post("/api/auth/2fa/verify", json={"code": _totp(secret)})
    assert r.json()["status"] == "SUCCESS"
    assert nc.get("/api/systems").status_code == 200


def test_secret_is_encrypted_at_rest(client):
    """Das gespeicherte TOTP-Secret darf nicht im Klartext in der DB liegen."""
    from sqlmodel import Session, select
    # Konten liegen seit der Multi-DB-Umstellung in der zentralen System-DB.
    from app.database import system_engine as engine
    from app.models import User

    r = client.post("/api/admin/users/create", json={"username": "krypto.user", "role": "viewer"})
    temp = r.json()["temp_password"]
    nc = TestClient(app)
    nc.post("/api/auth/login", json={"username": "krypto.user", "password": temp})
    nc.post("/api/auth/change-password",
            json={"current_password": temp, "new_password": "krypto-passwort-xy1"})
    secret = nc.post("/api/auth/2fa/setup").json()["secret"]

    with Session(engine) as s:
        row = s.exec(select(User).where(User.username == "krypto.user")).first()
        assert row.two_factor_secret and row.two_factor_secret != secret   # verschlüsselt
        assert twofactor.decrypt(row.two_factor_secret) == secret          # entschlüsselbar


def test_admin_create_rejects_duplicate(client):
    client.post("/api/admin/users/create", json={"username": "dupe.user", "role": "viewer"})
    r = client.post("/api/admin/users/create", json={"username": "dupe.user", "role": "viewer"})
    assert r.status_code == 409
