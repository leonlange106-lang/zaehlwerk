"""Tarif-Vertragsunterlagen (TICKET-2.1): Feld-Erkennung aus Text, Upload/Abruf,
Kündigungstermin und Vertragsende-Übersicht.
"""
import io
from datetime import date, timedelta

from app import tariff_docs


# ---------- Feld-Erkennung ----------
def test_extract_fields_prices_and_notice():
    text = (
        "Stromliefervertrag der Vattenfall Europe. "
        "Arbeitspreis: 34,90 ct/kWh. Grundpreis: 12,50 € / Monat. "
        "Vertragslaufzeit vom 01.03.2025 bis 28.02.2026. "
        "Kündigungsfrist: 3 Monate zum Vertragsende."
    )
    f = tariff_docs.extract_fields(text)
    assert abs(f["arbeitspreis"] - 0.349) < 1e-6         # ct -> €/kWh
    assert abs(f["grundpreis"] - 150.0) < 1e-6            # €/Monat -> €/Jahr
    assert f["notice_period_days"] == 90                  # 3 Monate
    assert f["anbieter"] == "Vattenfall"
    assert f["gueltig_ab"] == date(2025, 3, 1)
    assert f["gueltig_bis"] == date(2026, 2, 28)


def test_extract_fields_empty_is_safe():
    assert tariff_docs.extract_fields("") == {}
    assert tariff_docs.extract_fields("nichts verwertbares hier") == {}


def test_notice_deadline():
    assert tariff_docs.notice_deadline(None, 30) is None
    assert tariff_docs.notice_deadline(date(2026, 2, 28), None) is None
    assert tariff_docs.notice_deadline(date(2026, 2, 28), 90) == date(2026, 2, 28) - timedelta(days=90)


# ---------- Upload + Abruf ----------
def test_upload_rejects_unknown_type(client):
    r = client.post("/api/tariffs/upload",
                    files={"file": ("x.txt", io.BytesIO(b"hallo"), "text/plain")})
    assert r.status_code == 415


def test_upload_stores_and_serves(client):
    # Minimales PNG (1x1) – wird abgelegt; OCR liefert evtl. nichts, das ist ok.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082")
    r = client.post("/api/tariffs/upload",
                    files={"file": ("vertrag.png", io.BytesIO(png), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["document_url"].startswith("/api/tariffs/documents/")
    # Abruf der abgelegten Datei.
    got = client.get(body["document_url"])
    assert got.status_code == 200


# ---------- Vertragsende-Übersicht ----------
def test_expiring_endpoint(client):
    sid = client.post("/api/systems", json={"name": "Strom X", "typ": "Strom", "einheit": "kWh"}).json()["id"]
    # gueltig_bis in 100 Tagen, Kündigungsfrist 90 Tage -> Termin in 10 Tagen.
    bis = date.today() + timedelta(days=100)
    client.post(f"/api/systems/{sid}/tariffs", json={
        "gueltig_ab": "2020-01-01", "gueltig_bis": bis.isoformat(),
        "arbeitspreis": 0.30, "grundpreis": 120.0, "notice_period_days": 90,
    })
    rows = client.get("/api/tariffs/expiring?within_days=30").json()
    match = [e for e in rows if e["system_id"] == sid]
    assert match and match[0]["days_until_deadline"] == 10

    # Tarif-Read weist Kündigungstermin + due_soon aus.
    t = client.get(f"/api/systems/{sid}/tariffs").json()[0]
    assert t["notice_deadline"] is not None and t["notice_due_soon"] is True
