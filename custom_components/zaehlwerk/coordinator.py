"""DataUpdateCoordinator: hält die Zählwerk-Kennzahlen frisch."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZaehlwerkClient, ZaehlwerkError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZaehlwerkCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Pollt `/api/dashboard/data` und legt die Systeme nach id ab."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ZaehlwerkClient,
        scan_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry.title})",
            update_interval=scan_interval,
        )
        self._client = client
        self.entry = entry

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            systems = await self._client.async_get_dashboard()
        except ZaehlwerkError as err:
            raise UpdateFailed(str(err)) from err
        # Nach System-id indizieren, damit die Sensoren stabil zuordnen.
        return {s["id"]: s for s in systems if s.get("id")}
