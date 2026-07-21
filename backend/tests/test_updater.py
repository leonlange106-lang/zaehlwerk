"""Tests für den dezentralen Selbst-Update-Weg (ohne Netzwerkzugriff).

Geprüft wird die App-Seite: Versionsvergleich, die Erkennung, ob der
Selbst-Update-Weg eingerichtet ist, und dass eine Anforderung samt
Sicherheits-Backup atomar im Kontrollverzeichnis landet. Das eigentliche
Ausführen (git/docker) macht das Host-Skript und ist nicht Teil der App.
"""
import json
import os

from app import updater


def test_version_compare():
    assert updater._is_newer("3.22.7", "3.22.6") is True
    assert updater._is_newer("3.23.0", "3.22.6") is True
    assert updater._is_newer("3.22.6", "3.22.6") is False
    assert updater._is_newer("3.22.5", "3.22.6") is False
    assert updater._is_newer(None, "3.22.6") is False


def test_not_supported_without_control_dir(monkeypatch):
    monkeypatch.delenv(updater.CONTROL_DIR_ENV, raising=False)
    assert updater.control_dir() is None
    assert updater.supported() is False
    # status() bleibt abrufbar und meldet einfach "nicht unterstützt".
    st = updater.status()
    assert st["supported"] is False
    assert st["current"]


def test_request_action_writes_control_file(client, monkeypatch, tmp_path):
    # client-Fixture: stellt sicher, dass die DB angelegt ist (create_backup
    # braucht sie für das Sicherheits-Backup vor dem Update).
    monkeypatch.setenv(updater.CONTROL_DIR_ENV, str(tmp_path))
    assert updater.supported() is True          # kein Ingress in Tests + Control-Dir

    payload = updater.request_action("update", actor="admin")
    assert payload["action"] == "update"
    # Vor dem Update MUSS eine Sicherung erzeugt worden sein.
    assert payload["safety_backup"], "Update ohne Sicherheits-Backup ist unzulässig"

    req_file = tmp_path / updater.REQUEST_FILE
    assert req_file.is_file()
    on_disk = json.loads(req_file.read_text("utf-8"))
    assert on_disk["action"] == "update"
    assert on_disk["requested_by"] == "admin"

    # status() spiegelt die schwebende Anforderung.
    st = updater.status()
    assert st["pending"] and st["pending"]["action"] == "update"

    # Rollback braucht kein Backup, schreibt aber ebenfalls eine Anforderung.
    rb = updater.request_action("rollback", actor="admin")
    assert rb["action"] == "rollback"
    assert json.loads(req_file.read_text("utf-8"))["action"] == "rollback"


def test_reads_host_status(monkeypatch, tmp_path):
    monkeypatch.setenv(updater.CONTROL_DIR_ENV, str(tmp_path))
    (tmp_path / updater.STATUS_FILE).write_text(json.dumps({
        "action": "update", "ok": True, "from": "3.22.5", "to": "3.22.6",
    }), "utf-8")
    st = updater.status()
    assert st["last_action"]["ok"] is True
    assert st["last_action"]["to"] == "3.22.6"
