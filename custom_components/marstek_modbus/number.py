"""
Module for creating number entities for Marstek Venus battery devices.
Numbers read Modbus registers asynchronously via the coordinator.

SCALING NOTE: coordinator.data already contains scaled values.
native_value returns coordinator data as-is.
async_set_native_value converts engineering-unit input back to raw register value.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities when the config entry is loaded."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MarstekNumber(coordinator, definition)
        for definition in coordinator.NUMBER_DEFINITIONS
    ]
    async_add_entities(entities)


class MarstekNumber(CoordinatorEntity, NumberEntity):
    """Modbus number entity for Marstek Venus."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        super().__init__(coordinator)

        self._key = definition["key"]
        self.definition = definition
        self.coordinator._entity_types[self._key] = self.entity_type

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]

        self._register = definition["register"]
        self._attr_native_min_value = definition.get("min", 0)
        self._attr_native_max_value = definition.get("max", 100)
        self._attr_native_step = definition.get("step", 1)
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._scale = definition.get("scale", 1)

        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    @property
    def entity_type(self) -> str:
        return "number"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        """
        Return the current value.
        coordinator.data already contains scaled values – return as-is.
        """
        data = self.coordinator.data
        if data is None:
            return None
        return data.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """
        Write the given engineering-unit value to the Modbus register.

        Convert back to raw register value (reverse the scale), then
        optimistically store the engineering-unit value in coordinator.data
        so HA shows the correct state immediately.
        """
        scale = self._scale if self._scale else 1
        raw_value = int(round(value / scale))

        # Optimistic update: store the SCALED (engineering-unit) value so
        # native_value returns the correct number without waiting for next poll
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()

        success = await self.coordinator.async_write_value(
            register=self._register,
            value=raw_value,
            key=self._key,
            scale=scale,
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

        if not success:
            _LOGGER.debug(
                "Write failed for %s, refreshing to get actual state", self._key
            )
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }
