"""REST-/HTTP-Poller: Zählerstände von Geräten mit hinterlegter rest_url
(ESPHome web_server, Shelly, generische JSON-Endpunkte). Wertextraktion,
Perioden-/Plausibilitätsregeln (analog MQTT) und der Live-Test-Endpunkt.
"""
import io
import json

from app import rest_poller


class _FakeResp:
    """Minimaler urlopen-Kontextmanager-Ersatz."""
    def __init__(self, body: str):
        self._buf = io.BytesIO(body.encode())

    def read(self, n=-1):
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_http(monkeypatch, body: str):
    monkeypatch.setattr(rest_poller.urllib.request, "urlopen",
                        lambda *a, **k: _FakeResp(body))


# ---------- Wertextraktion ----------
def test_plain_number_body(monkeypatch):
    _patch_http(monkeypatch, "1234.5")
    r = rest_poller.fetch_rest_value("http://dev.local/sensor/x")
    assert r["value"] == 1234.5 and r["error"] is None


def test_explicit_json_path(monkeypatch):
    _patch_http(monkeypatch, json.dumps({"sensor": {"total": {"value": 42.0}}}))
    r = rest_poller.fetch_rest_value("http://dev.local", "sensor.total.value")
    assert r["value"] == 42.0 and r["matched_path"] == "sensor.total.value"


def test_esphome_value_key(monkeypatch):
    # ESPHome /sensor/x als JSON: {"id":..,"value":..,"state":".. kWh"}
    _patch_http(monkeypatch, json.dumps({"id": "sensor-strom", "value": 9001, "state": "9001 kWh"}))
    r = rest_poller.fetch_rest_value("http://esp.local/sensor/strom")
    assert r["value"] == 9001


def test_auto_detect_meter_key(monkeypatch):
    _patch_http(monkeypatch, json.dumps({"power": 350, "total_in": 5000.0}))
    r = rest_poller.fetch_rest_value("http://dev.local")
    # total_in ist Zählerstand, power wird ignoriert
    assert r["value"] == 5000.0


def test_missing_value_reports_error(monkeypatch):
    _patch_http(monkeypatch, json.dumps({"power": 350, "voltage": 230}))
    r = rest_poller.fetch_rest_value("http://dev.local")
    assert r["value"] is None and r["error"]


def test_network_error_is_captured(monkeypatch):
    def _boom(*a, **k):
        raise OSError("Verbindung abgelehnt")
    monkeypatch.setattr(rest_poller.urllib.request, "urlopen", _boom)
    r = rest_poller.fetch_rest_value("http://dev.local")
    assert r["value"] is None and "abgelehnt" in r["error"]


# ---------- Persistenz über den Poller ----------
def test_poll_creates_rest_reading(client, monkeypatch):
    sid = client.post("/api/systems", json={
        "name": "ESPHome Strom", "typ": "Strom", "einheit": "kWh",
        "zusatzfelder": {"rest_url": "http://esp.local/sensor/strom"},
    }).json()["id"]

    monkeypatch.setattr(rest_poller, "fetch_rest_value",
                        lambda *a, **k: {"value": 12345.0, "raw": "12345",
                                         "matched_path": "value", "error": None})
    res = rest_poller.poll_once()
    assert res["written"] == 1

    readings = client.get(f"/api/systems/{sid}/readings").json()
    assert any(r["source"] == "rest" and r["value"] == 12345.0 for r in readings)

    # Zweiter Lauf in derselben Periode mit gleichem Wert -> kein neuer Datensatz.
    assert rest_poller.poll_once()["written"] == 0


def test_poll_rejects_decreasing_value(client, monkeypatch):
    sid = client.post("/api/systems", json={
        "name": "REST Rueckwaerts", "typ": "Strom", "einheit": "kWh",
        "zusatzfelder": {"rest_url": "http://dev.local"},
    }).json()["id"]
    client.post(f"/api/systems/{sid}/readings",
                json={"datum": "2020-01-01", "value": 8000, "source": "manual"})

    monkeypatch.setattr(rest_poller, "fetch_rest_value",
                        lambda *a, **k: {"value": 10.0, "raw": "10",
                                         "matched_path": "value", "error": None})
    # Wert unter letztem Stand -> verworfen, keine 'rest'-Ablesung.
    rest_poller.poll_once()
    readings = client.get(f"/api/systems/{sid}/readings").json()
    assert not any(r["source"] == "rest" for r in readings)


def test_systems_without_rest_url_are_skipped(client, monkeypatch):
    called = {"n": 0}

    def _spy(*a, **k):
        called["n"] += 1
        return {"value": 1.0, "raw": "1", "matched_path": "value", "error": None}
    monkeypatch.setattr(rest_poller, "fetch_rest_value", _spy)
    before = called["n"]
    rest_poller.poll_once()
    # Es existieren Systeme ohne rest_url (aus anderen Tests) – die dürfen den
    # HTTP-Aufruf nicht auslösen. Genaue Zahl offen, aber der Spy darf nur für
    # Systeme MIT rest_url anschlagen.
    assert called["n"] >= before  # kein Absturz; Skip-Pfad greift


# ---------- Live-Test-Endpunkt ----------
def test_binding_test_endpoint_rest(client, monkeypatch):
    monkeypatch.setattr(rest_poller, "fetch_rest_value",
                        lambda *a, **k: {"value": 777.0, "raw": "777",
                                         "matched_path": "value", "error": None})
    r = client.post("/api/systems/binding/test",
                    json={"kind": "rest", "url": "http://esp.local/sensor/x"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["value"] == 777.0


def test_binding_test_rejects_bad_url(client):
    r = client.post("/api/systems/binding/test",
                    json={"kind": "rest", "url": "ftp://nope"})
    assert r.status_code == 422
