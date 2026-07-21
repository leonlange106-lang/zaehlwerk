"""Sensoren je Zählwerk-System.

Pro System werden mehrere Kennzahlen aus `/api/dashboard/data` exponiert:
letzter Zählerstand, Ø-Verbrauch/Tag, Gesamtkosten und – wenn vorhanden – die
Jahresprognose. Alle teilen sich ein HA-Gerät je System.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZaehlwerkCoordinator


@dataclass(frozen=True, kw_only=True)
class ZaehlwerkSensorDescription(SensorEntityDescription):
    """Beschreibung samt Zugriff auf das System-Dict."""

    value_fn: Callable[[dict], float | None]
    # Einheit dynamisch (System-Einheit) statt fest, wenn None.
    dynamic_unit: bool = False


SENSOR_TYPES: tuple[ZaehlwerkSensorDescription, ...] = (
    ZaehlwerkSensorDescription(
        key="latest",
        translation_key="latest",
        state_class=SensorStateClass.TOTAL_INCREASING,
        dynamic_unit=True,
        value_fn=lambda s: s.get("latest"),
    ),
    ZaehlwerkSensorDescription(
        key="avg_per_day",
        translation_key="avg_per_day",
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_unit=True,
        value_fn=lambda s: s.get("avg_per_day"),
    ),
    ZaehlwerkSensorDescription(
        key="total_cost",
        translation_key="total_cost",
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda s: s.get("total_cost_tariff")
        if s.get("total_cost_tariff") is not None
        else s.get("total_cost"),
    ),
    ZaehlwerkSensorDescription(
        key="prognosis",
        translation_key="prognosis",
        state_class=SensorStateClass.MEASUREMENT,
        dynamic_unit=True,
        value_fn=lambda s: (s.get("prognosis") or {}).get("cons"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZaehlwerkCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ZaehlwerkSensor] = []
    for system_id, system in coordinator.data.items():
        for description in SENSOR_TYPES:
            entities.append(
                ZaehlwerkSensor(coordinator, system_id, system, description)
            )
    async_add_entities(entities)


class ZaehlwerkSensor(CoordinatorEntity[ZaehlwerkCoordinator], SensorEntity):
    """Eine Kennzahl eines Systems."""

    entity_description: ZaehlwerkSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZaehlwerkCoordinator,
        system_id: str,
        system: dict,
        description: ZaehlwerkSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._system_id = system_id
        self.entity_description = description
        self._attr_unique_id = f"{system_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, system_id)},
            name=system.get("name"),
            manufacturer="Zählwerk",
            model=system.get("typ"),
        )
        if description.dynamic_unit:
            self._attr_native_unit_of_measurement = system.get("einheit")

    @property
    def _system(self) -> dict:
        return self.coordinator.data.get(self._system_id, {})

    @property
    def available(self) -> bool:
        return super().available and self._system_id in self.coordinator.data

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self._system)
