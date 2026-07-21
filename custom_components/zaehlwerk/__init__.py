"""Zählwerk-Integration: verbindet HA mit einem Zählwerk-Backend.

Der Betriebsmodus (HA-intern / Dezentral) bestimmt nur die Vorgaben im
Config-Flow – zur Laufzeit spricht die Integration in beiden Fällen dieselbe
REST-API. So lässt sich beim Umzug der Schalter umlegen, ohne die Entitäten
neu einzurichten.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZaehlwerkClient, ZaehlwerkError
from .const import (
    CONF_CF_CLIENT_ID,
    CONF_CF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import ZaehlwerkCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = ZaehlwerkClient(
        async_get_clientsession(hass),
        base_url=entry.data[CONF_URL],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, True),
        cf_client_id=entry.data.get(CONF_CF_CLIENT_ID) or None,
        cf_client_secret=entry.data.get(CONF_CF_CLIENT_SECRET) or None,
    )
    coordinator = ZaehlwerkCoordinator(hass, entry, client, DEFAULT_SCAN_INTERVAL)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ZaehlwerkError as err:
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
