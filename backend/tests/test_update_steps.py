"""Update-Statusfluss (TICKET P1): die Versionsprüfung führt ein Schritt-
Protokoll (Suche gestartet → erreichbar/nicht → Version), das die Oberfläche als
Ladebalken/Log zeigt. status() reicht Schritte, Fortschritt und Offline-Zustand
mit durch.
"""
import base64

from app import outbound, updater
from app.version import APP_VERSION


def _fake_content(version: str) -> dict:
    src = f'APP_VERSION = "{version}"\n'
    return {"content": base64.b64encode(src.encode()).decode()}


def test_check_latest_records_steps(monkeypatch):
    was_offline = outbound.is_offline()
    outbound._cache.clear()
    outbound.set_offline(False)
    try:
        monkeypatch.setattr(outbound, "fetch_json", lambda *a, **k: _fake_content("9.9.9"))
        result = updater.check_latest(force=True)
        phases = [s["phase"] for s in result["steps"]]
        assert phases[0] == "search"
        assert "reachable" in phases and "version" in phases
        assert result["version"] == "9.9.9"
        # Neuere Version -> als verfügbar gemeldet.
        assert any("verfügbar" in s["message"] for s in result["steps"])
    finally:
        outbound._cache.clear()
        outbound.set_offline(was_offline)


def test_check_latest_failure_marks_unreachable(monkeypatch):
    outbound._cache.clear()

    def _boom(*a, **k):
        raise RuntimeError("DNS kaputt")
    monkeypatch.setattr(outbound, "fetch_json", _boom)
    result = updater.check_latest(force=True)
    assert result["error"] and "DNS" in result["error"]
    last = result["steps"][-1]
    assert last["phase"] == "reachable" and last["ok"] is False


def test_status_exposes_steps_and_current(monkeypatch):
    outbound._cache.clear()
    monkeypatch.setattr(outbound, "fetch_json", lambda *a, **k: _fake_content(APP_VERSION))
    updater.check_latest(force=True)
    st = updater.status()
    assert st["current"] == APP_VERSION
    assert isinstance(st["check_steps"], list) and st["check_steps"]
    # Gleiche Version -> kein Update, aber Schritt vorhanden.
    assert st["update_available"] is False
    assert "progress" in st
