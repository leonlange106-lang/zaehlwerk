"""Contract-Tests: die Felder, auf die das Frontend angewiesen ist.

Ziel ist ein sofortiger Alarm, wenn eine API-Änderung ein Feld entfernt oder
umbenennt, das die Oberfläche liest. Die Verträge sind bewusst als schlichte
Feldlisten notiert – nah an dem, was `frontend/app.js` tatsächlich verwendet.
Ein fehlendes Feld lässt den zugehörigen Test rot werden und nennt es beim
Namen, statt dass es später still in der Oberfläche verschwindet.
"""
import pytest


def _require(payload: dict, fields, where: str):
    missing = [f for f in fields if f not in payload]
    assert not missing, f"{where}: fehlende Felder {missing}. Vorhanden: {sorted(payload)}"


# --------------------------------------------------------------------------
# Basis / Auth
# --------------------------------------------------------------------------
def test_health_contract(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    _require(r.json(), ["status", "version", "db"], "GET /api/health")


def test_auth_status_contract(client):
    body = client.get("/api/auth/status").json()
    _require(body, ["mode", "authenticated", "setup_required",
                    "crypto_available", "user", "permissions", "roles"],
             "GET /api/auth/status")
    # Angemeldet -> user und permissions dürfen nicht null sein.
    assert body["authenticated"] is True
    _require(body["user"], ["id", "username", "role", "is_admin"], "auth.user")
    _require(body["permissions"], ["read", "write", "admin"], "auth.permissions")


# --------------------------------------------------------------------------
# Systeme
# --------------------------------------------------------------------------
SYSTEM_FIELDS = ["id", "name", "typ", "einheit", "farbe", "icon",
                 "zusatzfelder", "aktiv", "erstellt_am"]


def test_system_create_and_list_contract(client):
    created = client.post("/api/systems", json={
        "name": "Vertrag", "typ": "Gas", "einheit": "m³"}).json()
    _require(created, SYSTEM_FIELDS, "POST /api/systems")
    lst = client.get("/api/systems").json()
    assert isinstance(lst, list) and lst
    _require(lst[0], SYSTEM_FIELDS, "GET /api/systems[0]")


# --------------------------------------------------------------------------
# Ablesungen
# --------------------------------------------------------------------------
READING_FIELDS = ["id", "system_id", "datum", "value", "cost",
                  "meter_replaced", "meter_start", "note", "source",
                  "consumption", "consumption_per_day", "is_outlier",
                  "cost_effective", "cost_estimated"]


def test_reading_create_contract(client, system):
    r = client.post(f"/api/systems/{system}/readings",
                    json={"datum": "2026-06-01", "value": 12000, "source": "manual"})
    assert r.status_code == 201
    _require(r.json(), READING_FIELDS, "POST readings")


def test_reading_meter_start_roundtrip(client, system):
    """meter_start ist neu (v3.18.0) und wird vom Ablesedialog geschrieben und
    gelesen – er muss im Vertrag bleiben."""
    r = client.post(f"/api/systems/{system}/readings", json={
        "datum": "2026-08-01", "value": 500, "meter_replaced": True,
        "meter_start": 100, "source": "manual"})
    assert r.status_code == 201
    body = r.json()
    assert body["meter_start"] == 100
    assert body["meter_replaced"] is True


# --------------------------------------------------------------------------
# Statistik
# --------------------------------------------------------------------------
def test_stats_contract(client, system):
    stats = client.get(f"/api/systems/{system}/stats").json()
    _require(stats, [
        "total_consumption", "total_cost", "total_days", "avg_per_day",
        "cost_per_day", "cost_per_unit", "reading_count", "cost_estimated",
        # Tarif-Kennzahlen (v2.16.0), vom Effektivpreis-Panel gelesen
        "total_cost_tariff", "avg_price_effective", "coverage_ratio",
    ], "GET stats")


# --------------------------------------------------------------------------
# System-Dashboard (readings + stats + chart + counts + prognosis)
# --------------------------------------------------------------------------
def test_system_dashboard_contract(client, system):
    d = client.get(f"/api/systems/{system}/dashboard").json()
    _require(d, ["readings", "stats", "chart", "counts", "prognosis"],
             "GET system dashboard")
    _require(d["chart"], ["system_id", "name", "unit", "color", "labels",
                          "values", "consumption", "consumption_per_day",
                          "outliers", "meter_replaced"], "dashboard.chart")
    _require(d["counts"], ["meters", "tariffs"], "dashboard.counts")


def test_prognosis_contract(client, system):
    """Die Prognose-Kachel (v3.18.0) liest ein festes Feldset. Das Fixture
    liefert genug Historie, sodass die Prognose nicht None ist."""
    p = client.get(f"/api/systems/{system}/dashboard").json()["prognosis"]
    assert p is not None, "Prognose sollte bei ausreichender Historie vorhanden sein"
    _require(p, [
        "window_years", "window_from", "window_to", "window_days", "avg_per_day",
        "billing_year_start", "billing_year_end", "billing_days",
        "projected_consumption", "projected_energy_cost", "projected_base_cost",
        "projected_cost", "abschlag_monthly", "abschlag_annual",
        "exceeds_abschlag", "shortfall",
    ], "prognosis")


# --------------------------------------------------------------------------
# Gesamt-Dashboard (Startseite + Kacheln)
# --------------------------------------------------------------------------
def test_dashboard_data_contract(client, system):
    dd = client.get("/api/dashboard/data?months=24").json()
    _require(dd, ["systems", "months", "recent"], "GET /api/dashboard/data")
    assert dd["systems"], "mindestens ein System erwartet"
    _require(dd["systems"][0], [
        "id", "name", "typ", "einheit", "farbe", "latest", "latest_datum",
        "total_consumption", "total_cost", "total_cost_tariff", "avg_per_day",
        "series", "prognosis",
    ], "dashboard/data.systems[0]")


def test_recent_contract(client, system):
    recent = client.get("/api/dashboard/data?months=24").json()["recent"]
    assert recent, "letzte Erfassungen erwartet"
    _require(recent[0], ["id", "system_id", "system", "farbe", "einheit",
                         "datum", "value", "source"], "dashboard/data.recent[0]")


# --------------------------------------------------------------------------
# Tarife
# --------------------------------------------------------------------------
def test_tariff_contract(client, system):
    lst = client.get(f"/api/systems/{system}/tariffs").json()
    assert isinstance(lst, list) and lst
    _require(lst[0], ["id", "system_id", "name", "anbieter", "gueltig_ab",
                      "gueltig_bis", "arbeitspreis", "grundpreis", "notiz",
                      "erstellt_am", "aktiv"], "GET tariffs[0]")


# --------------------------------------------------------------------------
# Persönliches Dashboard-Layout
# --------------------------------------------------------------------------
def test_user_dashboard_contract(client):
    d = client.get("/api/user/dashboard").json()
    _require(d, ["tiles", "is_default"], "GET /api/user/dashboard")


# --------------------------------------------------------------------------
# Übersicht (Startseite / Fälligkeit)
# --------------------------------------------------------------------------
def test_overview_contract(client, system):
    ov = client.get("/api/overview").json()
    assert isinstance(ov, dict)
    assert system in ov, "System sollte in der Übersicht auftauchen"
    _require(ov[system], ["value", "datum"], "overview[system]")
