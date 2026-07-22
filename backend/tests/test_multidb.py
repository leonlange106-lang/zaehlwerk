"""Multi-Tenant-Datenbanken (TICKET-1.1 / 1.2).

Deckt ab: eigene DB je Nutzer, zentrale System-DB fürs Routing, Rechte-Matrix
(Freigabe/Entzug), Datenisolation zwischen Mandanten und die Durchsetzung von
Nur-Lese-Freigaben beim Kontextwechsel (Header `X-Zaehlwerk-Database`).
"""
import pyotp
from conftest import ADMIN
from fastapi.testclient import TestClient

from app.main import app


def _create_user(client, username, role="writer"):
    r = client.post("/api/admin/users/create", json={"username": username, "role": role})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["user"]["id"], body["temp_password"]


def _onboard(username, temp, new_password):
    """Erzwungenes Onboarding vollständig durchlaufen (Passwort + 2FA) und den
    angemeldeten Client zurückgeben."""
    c = TestClient(app)
    c.post("/api/auth/login", json={"username": username, "password": temp})
    c.post("/api/auth/change-password",
           json={"current_password": temp, "new_password": new_password})
    secret = c.post("/api/auth/2fa/setup").json()["secret"]
    c.post("/api/auth/2fa/verify", json={"code": pyotp.TOTP(secret).now()})
    return c


def _default_db_id(client):
    dbs = client.get("/api/databases").json()["databases"]
    return next(d["id"] for d in dbs if d["is_default"])


def test_admin_owns_default_database(client):
    r = client.get("/api/databases")
    assert r.status_code == 200
    data = r.json()
    assert data["active_id"]
    default = [d for d in data["databases"] if d["is_default"]]
    assert default and default[0]["role"] == "owner"


def test_new_user_gets_isolated_database(client):
    uid, _ = _create_user(client, "tenant.owner")
    overview = client.get("/api/admin/databases").json()
    assert any(db["owner_user_id"] == uid for db in overview)


def test_grant_and_revoke_access(client):
    uid, _ = _create_user(client, "share.target", role="viewer")
    default_id = _default_db_id(client)

    r = client.post(f"/api/admin/databases/{default_id}/access",
                    json={"user_id": uid, "role": "read_only"})
    assert r.status_code == 200

    entries = client.get(f"/api/admin/databases/{default_id}/access").json()
    assert any(e["user_id"] == uid and e["role"] == "read_only" for e in entries)

    r = client.delete(f"/api/admin/databases/{default_id}/access/{uid}")
    assert r.status_code == 200
    entries = client.get(f"/api/admin/databases/{default_id}/access").json()
    assert not any(e["user_id"] == uid for e in entries)


def test_owner_cannot_be_revoked(client):
    default_id = _default_db_id(client)
    owner_entry = next(e for e in client.get(f"/api/admin/databases/{default_id}/access").json()
                       if e["role"] == "owner")
    r = client.delete(f"/api/admin/databases/{default_id}/access/{owner_entry['user_id']}")
    assert r.status_code == 400


def test_isolation_and_readonly_enforcement(client):
    # Admin legt ein System in seiner eigenen (Standard-)DB an.
    sid = client.post("/api/systems", json={
        "name": "Admin Strom", "typ": "Strom", "einheit": "kWh"}).json()["id"]

    uid, temp = _create_user(client, "iso.user", role="writer")
    user = _onboard("iso.user", temp, "iso-passwort-123")

    # Eigene DB des Nutzers sieht das Admin-System NICHT (Isolation).
    own = user.get("/api/systems")
    assert own.status_code == 200
    assert all(s["id"] != sid for s in own.json())

    # ... darf dort aber selbst schreiben.
    created = user.post("/api/systems", json={
        "name": "User Gas", "typ": "Gas", "einheit": "kWh"})
    assert created.status_code in (200, 201)

    # Admin gibt seine DB read_only frei.
    default_id = _default_db_id(client)
    client.post(f"/api/admin/databases/{default_id}/access",
                json={"user_id": uid, "role": "read_only"})

    headers = {"X-Zaehlwerk-Database": default_id}
    # Lesen der fremden DB im Kontextwechsel: erlaubt, Admin-System sichtbar.
    switched = user.get("/api/systems", headers=headers)
    assert switched.status_code == 200
    assert any(s["id"] == sid for s in switched.json())

    # Schreiben in die read_only freigegebene DB: zentral geblockt.
    blocked = user.post("/api/systems", headers=headers, json={
        "name": "Unerlaubt", "typ": "Strom", "einheit": "kWh"})
    assert blocked.status_code == 403
