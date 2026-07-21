"""Schema-Validierung der Eingaben: ungültige Anfragen müssen VOR dem
Schreibzugriff mit 422 (bzw. 401/403 bei fehlender Berechtigung) abgewiesen
werden. So bleibt der Vertrag auch auf der Eingabeseite verbindlich."""
from fastapi.testclient import TestClient

from app.main import app


def test_system_requires_core_fields(client):
    r = client.post("/api/systems", json={"name": "Ohne Typ"})
    assert r.status_code == 422


def test_reading_meter_start_without_replace_rejected(client, system):
    r = client.post(f"/api/systems/{system}/readings", json={
        "datum": "2026-09-01", "value": 20000, "meter_start": 10})
    assert r.status_code == 422


def test_reading_meter_start_above_value_rejected(client, system):
    r = client.post(f"/api/systems/{system}/readings", json={
        "datum": "2026-09-01", "value": 100, "meter_replaced": True,
        "meter_start": 500})
    assert r.status_code == 422


def test_reading_below_last_without_replace_rejected(client, system):
    # Ohne Zählertausch darf ein Wert nicht unter den letzten fallen.
    r = client.post(f"/api/systems/{system}/readings", json={
        "datum": "2026-10-01", "value": 1})
    assert r.status_code == 422


def test_tariff_arbeitspreis_upper_bound(client, system):
    r = client.post(f"/api/systems/{system}/tariffs", json={
        "gueltig_ab": "2020-01-01", "arbeitspreis": 999, "grundpreis": 100})
    assert r.status_code == 422


def test_dashboard_custom_timeframe_needs_range(client, system):
    r = client.put("/api/user/dashboard", json={"tiles": [{
        "id": "bad", "type": "line_chart", "x": 0, "y": 0, "w": 2, "h": 2,
        "timeframe": "custom"}]})
    assert r.status_code == 422


def test_unauthenticated_request_is_rejected(client):
    """Ein NICHT angemeldeter Client bekommt an geschützten /api-Pfaden 401 –
    die zentrale Absicherung der Middleware. Der `client`-Parameter stellt
    sicher, dass bereits ein Konto existiert (sonst ist die Ersteinrichtung
    offen und der Pfad läuft absichtlich durch). Ein eigener Client ohne
    Anmeldung teilt dieselbe App/Datenbank, löst aber keinen erneuten Startup
    aus (kein `with`-Block)."""
    anon = TestClient(app)
    r = anon.get("/api/systems")
    assert r.status_code == 401
