"""Abrechnungserfassung (TICKET-3.1): is_billed an Ablesungen schreibt das
Abrechnungsjahr fort; direkte Pflege über den Endpunkt; nur bei Kosten > 0."""


def test_billed_reading_creates_billing_year(client):
    sid = client.post("/api/systems", json={"name": "Strom AB", "typ": "Strom", "einheit": "kWh"}).json()["id"]
    r = client.post(f"/api/systems/{sid}/readings", json={
        "datum": "2025-12-31", "value": 5000, "cost": 1450.55, "is_billed": True, "source": "manual"})
    assert r.status_code == 201 and r.json()["is_billed"] is True

    years = client.get(f"/api/systems/{sid}/billing-years").json()
    assert len(years) == 1 and years[0]["year"] == 2025
    assert abs(years[0]["cost"] - 1450.55) < 1e-6


def test_unbilled_reading_does_not_create_year(client):
    sid = client.post("/api/systems", json={"name": "Strom NB", "typ": "Strom", "einheit": "kWh"}).json()["id"]
    client.post(f"/api/systems/{sid}/readings", json={
        "datum": "2025-06-01", "value": 100, "cost": 40, "is_billed": False, "source": "manual"})
    assert client.get(f"/api/systems/{sid}/billing-years").json() == []


def test_billing_upsert_endpoint_and_guard(client):
    sid = client.post("/api/systems", json={"name": "Gas AB", "typ": "Gas", "einheit": "m³"}).json()["id"]
    # is_billed=false -> 422
    assert client.post(f"/api/systems/{sid}/billing-years",
                       json={"year": 2024, "cost": 900, "is_billed": False}).status_code == 422
    # gültig -> anlegen, dann fortschreiben (Upsert, kein Duplikat).
    assert client.post(f"/api/systems/{sid}/billing-years",
                       json={"year": 2024, "cost": 900, "is_billed": True}).status_code == 201
    client.post(f"/api/systems/{sid}/billing-years", json={"year": 2024, "cost": 950, "is_billed": True})
    years = client.get(f"/api/systems/{sid}/billing-years").json()
    assert len(years) == 1 and abs(years[0]["cost"] - 950) < 1e-6
