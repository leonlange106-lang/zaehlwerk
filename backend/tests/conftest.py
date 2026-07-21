"""Pytest-Fixtures für die Contract- und Schema-Tests.

Die App liest den Datenbankpfad beim Import aus der Umgebung (config.py). Der
Pfad wird deshalb HIER gesetzt – vor dem ersten Import von `app` –, damit die
Tests auf einer wegwerfbaren, frischen SQLite-Datei laufen und nie die
produktive Datenbank berühren.
"""
import os
import tempfile

import pytest

# Frische Test-Datenbank, bevor irgendetwas aus `app` importiert wird.
_TMPDIR = tempfile.mkdtemp(prefix="zw-tests-")
os.environ["SQLITE_PATH"] = os.path.join(_TMPDIR, "contract-test.db")
# Deterministisch offline: die Tests sollen nie nach draußen telefonieren.
os.environ.setdefault("CORS_ORIGINS", "*")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN = {"username": "admin", "password": "test-passwort-12345"}


@pytest.fixture(scope="session")
def client():
    """Ein angemeldeter Administrator-Client. `with TestClient(...)` löst den
    Startup aus (init_db + Migrationen), sodass die Tests gegen das reale,
    migrierte Schema laufen – genau der Stand, den auch die Oberfläche sieht."""
    with TestClient(app) as c:
        c.post("/api/auth/setup", json=ADMIN)
        c.post("/api/auth/login", json=ADMIN)
        yield c


@pytest.fixture()
def system(client):
    """Ein System mit Tarif und zwei Ablesungen – Grundlage für die
    Auswertungs- und Prognose-Endpunkte."""
    sid = client.post("/api/systems", json={
        "name": "Strom Test", "typ": "Strom", "einheit": "kWh",
        "zusatzfelder": {"abschlag": 90, "abrechnungsmonat": 1},
    }).json()["id"]
    client.post(f"/api/systems/{sid}/tariffs", json={
        "gueltig_ab": "2019-01-01", "arbeitspreis": 0.30, "grundpreis": 120.0,
    })
    for d, v in [("2023-01-01", 0), ("2024-01-01", 3650),
                 ("2025-01-01", 7300), ("2026-01-01", 10950)]:
        client.post(f"/api/systems/{sid}/readings",
                    json={"datum": d, "value": v, "source": "manual"})
    return sid
