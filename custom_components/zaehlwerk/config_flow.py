"""Config-Flow: Modus wählen (HA-intern / Dezentral) und Verbindung prüfen."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ZaehlwerkAuthError,
    ZaehlwerkClient,
    ZaehlwerkConnectionError,
)
from .const import (
    CONF_CF_CLIENT_ID,
    CONF_CF_CLIENT_SECRET,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_INTERN_URL,
    DOMAIN,
    MODE_DEZENTRAL,
    MODE_INTERN,
    MODES,
)


class ZaehlwerkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Zwei Schritte: erst den Betriebsmodus, dann die Verbindungsdaten."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt 1: HA-intern oder Dezentral."""
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODE, default=MODE_INTERN): vol.In(MODES)}
            ),
        )

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt 2: URL + Zugangsdaten, dann Anmeldung testen."""
        errors: dict[str, str] = {}
        dezentral = self._mode == MODE_DEZENTRAL
        default_url = "" if dezentral else DEFAULT_INTERN_URL

        if user_input is not None:
            client = ZaehlwerkClient(
                async_get_clientsession(self.hass),
                base_url=user_input[CONF_URL],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                verify_ssl=user_input.get(CONF_VERIFY_SSL, True),
                cf_client_id=user_input.get(CONF_CF_CLIENT_ID) or None,
                cf_client_secret=user_input.get(CONF_CF_CLIENT_SECRET) or None,
            )
            try:
                await client.async_login()
            except ZaehlwerkAuthError:
                errors["base"] = "invalid_auth"
            except ZaehlwerkConnectionError:
                errors["base"] = "cannot_connect"
            else:
                # Eine Instanz je URL: verhindert doppelte Einträge.
                await self.async_set_unique_id(
                    f"{self._mode}:{user_input[CONF_URL].rstrip('/')}"
                )
                self._abort_if_unique_id_configured()
                title = (
                    "Zählwerk (dezentral)" if dezentral else "Zählwerk (HA-intern)"
                )
                return self.async_create_entry(
                    title=title, data={CONF_MODE: self._mode, **user_input}
                )

        schema: dict[Any, Any] = {
            vol.Required(CONF_URL, default=default_url): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_VERIFY_SSL, default=True): bool,
        }
        # Cloudflare-Access-Header nur im dezentralen Modus anbieten.
        if dezentral:
            schema[vol.Optional(CONF_CF_CLIENT_ID, default="")] = str
            schema[vol.Optional(CONF_CF_CLIENT_SECRET, default="")] = str

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
