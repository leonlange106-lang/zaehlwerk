"""Telemetrie-Retention (v3.20.0): alte MQTT-Daten werden auf Monatswerte
verdünnt, ohne den Gesamtverbrauch zu verändern oder andere Quellen anzufassen."""
from collections import Counter
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app import backup, logic
from app.database import engine
from app.models import Reading, System


def _total_consumption(system_id: str) -> float:
    with Session(engine) as s:
        rows = [{
            "datum": r.datum, "value": r.value, "source": r.source,
            "meter_replaced": r.meter_replaced, "meter_start": r.meter_start,
        } for r in s.exec(
            select(Reading).where(Reading.system_id == system_id)
            .order_by(Reading.datum)
        ).all()]
    iv = logic.compute_intervals(rows)
    return sum(e["consumption"] for e in iv if e["consumption"] is not None)


def _new_system() -> str:
    with Session(engine) as s:
        sys = System(name="Retention", typ="Strom", einheit="kWh",
                     farbe="#000", icon="bolt", zusatzfelder={})
        s.add(sys); s.commit(); s.refresh(sys)
        return sys.id


def _seed_mqtt(sid: str, days: int = 800):
    with Session(engine) as s:
        base = date.today() - timedelta(days=days)
        v = 0.0
        for i in range(days):
            d = base + timedelta(days=i)
            v += 10
            s.add(Reading(system_id=sid, datum=datetime(d.year, d.month, d.day),
                          value=v, source="mqtt"))
        s.commit()


def test_retention_preserves_total_for_cumulative_telemetry(client):
    """Kernvorgabe: verdünnen, ohne den Gesamtverbrauch zu verändern."""
    sid = _new_system()
    _seed_mqtt(sid)
    before = _total_consumption(sid)
    with Session(engine) as s:
        removed = backup.apply_telemetry_retention(s, 365)
    assert removed > 0
    after = _total_consumption(sid)
    assert abs(before - after) < 1e-6, f"Gesamtverbrauch verändert: {before} -> {after}"

    # Alte MQTT-Werte: höchstens einer je Kalendermonat.
    cutoff = date.today() - timedelta(days=365)
    with Session(engine) as s:
        rows = s.exec(select(Reading).where(Reading.system_id == sid)).all()
    months = Counter((r.datum.year, r.datum.month)
                     for r in rows if r.source == "mqtt" and r.datum.date() < cutoff)
    assert months and max(months.values()) == 1
    # Die jüngsten 365 Tage bleiben in voller Auflösung erhalten.
    recent = [r for r in rows if r.source == "mqtt" and r.datum.date() >= cutoff]
    assert len(recent) > 300


def test_retention_spares_non_mqtt_sources(client):
    """Von Hand erfasste / importierte / HA-Werte werden NIE angetastet."""
    sid = _new_system()
    _seed_mqtt(sid, days=800)
    old = date.today() - timedelta(days=700)
    with Session(engine) as s:
        for src in ("manual", "import", "ha_api"):
            s.add(Reading(system_id=sid, datum=datetime(old.year, old.month, old.day),
                          value=123, source=src))
        s.commit()
    with Session(engine) as s:
        backup.apply_telemetry_retention(s, 365)
    with Session(engine) as s:
        rows = s.exec(select(Reading).where(Reading.system_id == sid)).all()
    survivors = {r.source for r in rows if r.source != "mqtt"}
    assert survivors == {"manual", "import", "ha_api"}


def test_retention_disabled_is_noop(client):
    sid = _new_system()
    _seed_mqtt(sid, days=500)
    with Session(engine) as s:
        assert backup.apply_telemetry_retention(s, 0) == 0
    with Session(engine) as s:
        n = len(s.exec(select(Reading).where(Reading.system_id == sid)).all())
    assert n == 500


def test_retention_setting_in_contract(client):
    """Das neue Feld muss im Settings-Vertrag auftauchen (Frontend liest es)."""
    assert "telemetry_keep_days" in client.get("/api/settings").json()
