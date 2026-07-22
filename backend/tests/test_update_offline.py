"""Der Selbst-Update-Versionscheck muss auch bei aktivem Kill-Switch
(Offline-Modus) funktionieren – seine GitHub-URL ist fest verdrahtet und steht
auf der Allowlist. Allgemeine ausgehende Abfragen bleiben weiterhin gesperrt.
"""
import json

import pytest

from app import outbound


class _FakeResp:
    def __init__(self, payload: dict):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def geturl(self):
        return "https://api.github.com/repos/x/contents/version.py"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_version_check_bypasses_offline(monkeypatch):
    was_offline = outbound.is_offline()
    outbound._cache.clear()
    outbound.set_offline(True)
    try:
        # Ohne Ausnahme: im Offline-Modus geblockt.
        with pytest.raises(outbound.OutboundBlocked):
            outbound.fetch_json("github_version", {"ref": "main"}, allow_offline=False)

        # Mit Ausnahme: erreicht die Netzwerkschicht (hier gemockt).
        monkeypatch.setattr(outbound.urllib.request, "urlopen",
                            lambda *a, **k: _FakeResp({"content": "QVBQ"}))
        out = outbound.fetch_json("github_version", {"ref": "main"}, allow_offline=True)
        assert out.get("content") == "QVBQ"
    finally:
        outbound._cache.clear()
        outbound.set_offline(was_offline)
