"""Schmaler async-Client für die Zählwerk-REST-API.

Die Integration hält bewusst keine tiefe Kopplung: sie meldet sich mit
Benutzername/Passwort an (erhält ein JWT) und liest danach die
Dashboard-Kennzahlen mit `Authorization: Bearer`. Genau diesen Header wertet
das Backend in `auth.resolve_user` neben dem Cookie aus.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = 15


class ZaehlwerkError(Exception):
    """Basisfehler."""


class ZaehlwerkAuthError(ZaehlwerkError):
    """Anmeldung fehlgeschlagen (falsche Zugangsdaten)."""


class ZaehlwerkConnectionError(ZaehlwerkError):
    """Backend nicht erreichbar."""


class ZaehlwerkClient:
    """Minimaler Client: anmelden, Kennzahlen holen."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
        *,
        verify_ssl: bool = True,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._token: str | None = None
        # Cloudflare-Access-Header, falls davor eine Zero-Trust-Schicht sitzt.
        self._extra_headers: dict[str, str] = {}
        if cf_client_id and cf_client_secret:
            self._extra_headers["CF-Access-Client-Id"] = cf_client_id
            self._extra_headers["CF-Access-Client-Secret"] = cf_client_secret

    def _headers(self) -> dict[str, str]:
        h = dict(self._extra_headers)
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def async_login(self) -> None:
        """JWT holen. Wirft bei falschen Daten bzw. Nichterreichbarkeit."""
        url = f"{self._base}/api/auth/login"
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.post(
                    url,
                    json={"username": self._username, "password": self._password},
                    headers=self._extra_headers,
                    ssl=self._verify_ssl,
                )
        except aiohttp.ClientError as err:
            raise ZaehlwerkConnectionError(str(err)) from err
        if resp.status in (401, 403):
            raise ZaehlwerkAuthError("Zugangsdaten abgelehnt")
        if resp.status >= 400:
            raise ZaehlwerkConnectionError(f"HTTP {resp.status}")
        # Das Backend setzt das JWT als Cookie; für den Bearer-Weg lesen wir es
        # aus dem Set-Cookie-Header der Antwort.
        token = None
        for morsel in resp.cookies.values():
            token = morsel.value
        if not token:
            # Rückfall: manche Reverse-Proxys schlucken Set-Cookie – dann bleibt
            # die Cookie-Jar der Session unser Träger.
            filtered = self._session.cookie_jar.filter_cookies(self._base)
            for morsel in filtered.values():
                token = morsel.value
        if not token:
            raise ZaehlwerkAuthError("Kein Sitzungstoken in der Antwort")
        self._token = token

    async def async_get_dashboard(self) -> list[dict[str, Any]]:
        """Kennzahlen aller aktiven Systeme in einem Aufruf."""
        if not self._token:
            await self.async_login()
        data = await self._get("/api/dashboard/data")
        systems = data.get("systems") if isinstance(data, dict) else data
        return systems or []

    async def _get(self, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.get(
                    url, headers=self._headers(), ssl=self._verify_ssl
                )
                if resp.status in (401, 403):
                    # Token evtl. abgelaufen: einmal neu anmelden und wiederholen.
                    self._token = None
                    await self.async_login()
                    resp = await self._session.get(
                        url, headers=self._headers(), ssl=self._verify_ssl
                    )
                if resp.status >= 400:
                    raise ZaehlwerkConnectionError(f"HTTP {resp.status} für {path}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise ZaehlwerkConnectionError(str(err)) from err
