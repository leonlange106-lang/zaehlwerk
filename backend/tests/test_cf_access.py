"""Cloudflare Access (TICKET-5.1): optionale JWT-Prüfung vor der Anwendung.
Ohne Konfiguration ein No-Op; konfiguriert verlangt sie ein gültiges Token."""
import os

from app import cf_access


def test_disabled_by_default(client):
    # Ohne Env-Variablen ist die Schicht inaktiv -> normale Anfrage geht durch.
    assert cf_access.enabled() is False
    assert client.get("/api/systems").status_code == 200


def test_team_domain_normalisation(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "meinteam")
    monkeypatch.setenv("CF_ACCESS_AUD", "abc123")
    assert cf_access.enabled() is True
    assert cf_access.certs_url() == "https://meinteam.cloudflareaccess.com/cdn-cgi/access/certs"


def test_missing_token_forbidden(client, monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "meinteam.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "abc123")
    # Ohne Access-Kopf -> 403 (Health bleibt frei).
    assert client.get("/api/systems").status_code == 403
    assert client.get("/api/health").status_code == 200


def test_valid_token_passes(client, monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "meinteam.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "abc123")
    monkeypatch.setattr(cf_access, "verify", lambda token: {"aud": "abc123", "email": "u@x"})
    r = client.get("/api/systems", headers={"Cf-Access-Jwt-Assertion": "dummy"})
    assert r.status_code == 200


def test_invalid_token_forbidden(client, monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "meinteam.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "abc123")
    def _boom(token):
        raise ValueError("ungültig")
    monkeypatch.setattr(cf_access, "verify", _boom)
    r = client.get("/api/systems", headers={"Cf-Access-Jwt-Assertion": "bad"})
    assert r.status_code == 403
