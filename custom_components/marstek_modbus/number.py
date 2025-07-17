"""
Module for creating number entities for Marstek Venus battery devices.
The number retrieve data by reading Modbus registers.
"""

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity

from .const import (
    NUMBER_DEFINITIONS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import MarstekCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

def get_entity_type(entity) -> str:
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """
    Set up sensor entities when the config entry is loaded.

    This function creates a coordinator and uses sensor definitions
    to instantiate sensor entities, then adds them to Home Assistant.
    """
    # Get the coordinator instance from hass.data
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Await the first data refresh so coordinator.data is populated before use it
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Add entities defined in NUMBER_DEFINITIONS
    for definition in NUMBER_DEFINITIONS:
        entities.append(MarstekNumber(coordinator, definition))

    # Register all created sensor entities with Home Assistant
    async_add_entities(entities)


class MarstekNumber(NumberEntity):
    """Representation of a Modbus number entity for Marstek Venus."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """Initialize the number entity."""
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True
        self._attr_native_min_value = definition["min"]
        self._attr_native_max_value = definition["max"]
        self._attr_native_step = definition["step"]
        self._attr_native_unit_of_measurement = definition["unit"]
        self._register = definition["register"]
        self._key = definition["key"]

        if self.definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self):
        """Return True if coordinator data update was successful and state is set."""
        return self.coordinator.last_update_success and self._state is not None

    async def async_update(self):
        """
        Asynchronously update the sensor state.

        Reads register values via the coordinator's client and processes
        them based on the sensor's data type and configuration.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self.definition["register"]
        count = self.definition.get("count", 1)

        try:
            # Request the register value asynchronously
            raw_value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self.definition.get("key", self.definition.get("name", "unknown")),
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            return

        # Process raw_value based on sensor config
        if raw_value is not None:
            if isinstance(raw_value, (int, float)):
                # Apply scale and offset if specified, round to precision
                scaled = raw_value * self.definition.get("scale", 1)
                scaled += self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)

            else:
                # Fallback: just store raw_value directly
                self._state = raw_value

            await self.coordinator.async_update_sensor(
                self.definition["key"],
                self._state,
                register=self.definition.get("register"),
                scale=self.definition.get("scale"),
                unit=self.definition.get("unit"),
                entity_type=get_entity_type(self)
            )


    @property
    def native_value(self):
        """
        Return the current state value for Home Assistant.
        """
        # Use the coordinator's data for the sensor value
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            return self.coordinator.data.get(self.definition["key"])
        return None

    @property
    def device_info(self):
        """
        Return device information for Home Assistant device registry.

        Groups entities under the same device in the UI.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }  