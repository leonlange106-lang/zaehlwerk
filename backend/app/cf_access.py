"""Cloudflare Access – optionale Zusatzabsicherung hinter einem Tunnel (TICKET-5.1).

Wenn die App über einen Cloudflare Tunnel öffentlich erreichbar gemacht wird,
setzt Cloudflare Access VOR jeder Anfrage eine Identitätsprüfung und reicht das
Ergebnis als signiertes JWT im Kopf ``Cf-Access-Jwt-Assertion`` durch (bzw. im
Cookie ``CF_Authorization``). Diese Schicht validiert dieses JWT serverseitig als
Tiefenverteidigung: Ohne gültiges Access-Token kommt keine Anfrage an die
eigentliche Anwendung.

Aktiv nur, wenn KONFIGURIERT (Umgebungsvariablen ``CF_ACCESS_TEAM_DOMAIN`` und
``CF_ACCESS_AUD``). Ohne Konfiguration ist die Schicht ein No-Op – der lokale
Betrieb und das HA-Add-on bleiben unberührt.

Service-Tokens (z. B. der iOS-Client) senden ``CF-Access-Client-Id`` /
``CF-Access-Client-Secret``; Cloudflare Access wandelt sie am Rand in genau
dasselbe JWT um. Diese Schicht muss die Client-Secrets daher nie sehen.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger("zaehlwerk.cfaccess")

JWT_HEADER = "Cf-Access-Jwt-Assertion"
COOKIE_NAME = "CF_Authorization"
ALGORITHMS = ["RS256", "ES256"]

_jwks_client = None
_jwks_url: Optional[str] = None


def _team_domain() -> Optional[str]:
    """Voll qualifizierte Team-Domain, z. B. ``meinteam.cloudflareaccess.com``.
    Ein reiner Teamname wird ergänzt."""
    raw = (os.environ.get("CF_ACCESS_TEAM_DOMAIN") or "").strip().rstrip("/")
    if not raw:
        return None
    if "." not in raw:
        return f"{raw}.cloudflareaccess.com"
    return raw.replace("https://", "").replace("http://", "")


def audience() -> Optional[str]:
    aud = (os.environ.get("CF_ACCESS_AUD") or "").strip()
    return aud or None


def enabled() -> bool:
    """Aktiv nur bei vollständiger Konfiguration."""
    return bool(_team_domain() and audience())


def certs_url() -> Optional[str]:
    domain = _team_domain()
    return f"https://{domain}/cdn-cgi/access/certs" if domain else None


def _client():
    """Zwischengespeicherter JWKS-Client (holt/rotiert die Cloudflare-Schlüssel).
    Der Abruf läuft über die Socket-Sperre – Access ist ein Online-Feature; im
    Offline-Modus schlägt die Prüfung bewusst fehl (kein öffentlicher Zugang)."""
    global _jwks_client, _jwks_url
    url = certs_url()
    if not url:
        return None
    if _jwks_client is None or _jwks_url != url:
        from jwt import PyJWKClient
        _jwks_client = PyJWKClient(url, cache_keys=True)
        _jwks_url = url
    return _jwks_client


def verify(token: str) -> dict:
    """Validiert Signatur, Audience und Ablauf des Access-JWT. Gibt die Claims
    zurück oder wirft (jede Ausnahme = Ablehnung)."""
    import jwt

    client = _client()
    if client is None:
        raise RuntimeError("Cloudflare Access nicht konfiguriert")
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token, signing_key.key, algorithms=ALGORITHMS,
        audience=audience(), options={"require": ["exp", "aud"]},
    )


def token_from_request(headers, cookies) -> Optional[str]:
    """Access-Token aus Kopfzeile oder Cookie lesen."""
    token = headers.get(JWT_HEADER)
    if token:
        return token
    return cookies.get(COOKIE_NAME)
