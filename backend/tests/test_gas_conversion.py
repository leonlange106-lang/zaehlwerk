"""Gas-Umrechnung m³ -> kWh (TICKET-2.2): Ablesungen und Statistik weisen für
Gas-Systeme zusätzlich kWh-Werte aus (m³ × Brennwert × Zustandszahl),
konfigurierbar je Zähler. Nicht-Gas-Systeme bleiben unverändert.
"""
from app import logic


def test_gas_factor_gating():
    # Gas -> Standardfaktor, auch ohne Konfiguration.
    assert logic.gas_factor("Gas", None) == logic.DEFAULT_BRENNWERT * logic.DEFAULT_ZUSTANDSZAHL
    # Konfigurierbar je Zähler.
    assert logic.gas_factor("Gas", {"brennwert": 10.0, "zustandszahl": 0.9}) == 9.0
    # Nicht-Gas ohne Konfiguration -> keine Umrechnung.
    assert logic.gas_factor("Wasser", None) is None
    assert logic.gas_factor("Strom", {}) is None
    # Explizite Konfiguration aktiviert die Umrechnung auch ohne "gas" im Typ.
    assert logic.gas_factor("Custom", {"brennwert": 11.0}) is not None


def test_annotate_kwh_noop_without_factor():
    rows = [{"value": 100, "consumption": 50, "consumption_per_day": 1.5}]
    logic.annotate_kwh(rows, None)
    assert "consumption_kwh" not in rows[0]


def test_gas_reading_and_stats_expose_kwh(client):
    factor = 10.0 * 0.9  # 9.0
    sid = client.post("/api/systems", json={
        "name": "Gas Test", "typ": "Gas", "einheit": "m³",
        "zusatzfelder": {"brennwert": 10.0, "zustandszahl": 0.9},
    }).json()["id"]
    for d, v in [("2023-01-01", 0), ("2024-01-01", 1000)]:
        client.post(f"/api/systems/{sid}/readings", json={"datum": d, "value": v, "source": "manual"})

    readings = client.get(f"/api/systems/{sid}/readings").json()
    last = readings[-1]
    assert last["consumption"] == 1000
    assert abs(last["consumption_kwh"] - 1000 * factor) < 0.01
    assert last["value_kwh"] is not None

    stats = client.get(f"/api/systems/{sid}/stats").json()
    assert abs(stats["kwh_factor"] - factor) < 1e-6
    assert abs(stats["total_consumption_kwh"] - stats["total_consumption"] * factor) < 0.01

    chart = client.get(f"/api/systems/{sid}/chart-data").json()
    assert chart["kwh_factor"] is not None
    assert len(chart["consumption_per_day_kwh"]) == len(chart["consumption_per_day"])


def test_non_gas_has_no_kwh(client):
    sid = client.post("/api/systems", json={"name": "Strom kWh-Test", "typ": "Strom", "einheit": "kWh"}).json()["id"]
    client.post(f"/api/systems/{sid}/readings", json={"datum": "2024-01-01", "value": 100, "source": "manual"})
    last = client.get(f"/api/systems/{sid}/readings").json()[-1]
    assert last["consumption_kwh"] is None
    assert client.get(f"/api/systems/{sid}/stats").json()["kwh_factor"] is None
