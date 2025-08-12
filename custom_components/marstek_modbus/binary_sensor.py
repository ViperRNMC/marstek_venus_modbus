"""
Module for creating binary sensor entities for Marstek Venus battery devices.
Binary sensors read Modbus registers asynchronously via the coordinator.
"""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, BINARY_SENSOR_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """
    Determine the entity type based on its class inheritance.

    Args:
        entity: The entity instance.

    Returns:
        A lowercase string representing the entity type
        (e.g., 'switch', 'sensor', 'binary_sensor').
    """
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Set up binary sensor entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates binary sensor entities based on BINARY_SENSOR_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback to add entities.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_config_entry_first_refresh()

    entities = []

    for definition in BINARY_SENSOR_DEFINITIONS:
        entities.append(MarstekBinarySensor(coordinator, definition))

    async_add_entities(entities)


class MarstekBinarySensor(BinarySensorEntity):
    """
    Representation of a Modbus binary sensor entity for Marstek Venus.

    Sensor state is read asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the binary sensor entity.

        Args:
            coordinator: The data update coordinator instance.
            definition: Dictionary containing sensor configuration.
        """
        self.coordinator = coordinator
        self.definition = definition

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True

        self._state = None
        self._key = definition["key"]
        self._register = definition["register"]

        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """Handle entity added to Home Assistant by fetching initial state."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if coordinator update succeeded and state is known."""
        return self.coordinator.last_update_success and (self._state is not None)

    @property
    def is_on(self) -> bool | None:
        """Return True if binary sensor is on, False if off, None if unknown."""
        return self._state

    async def async_update(self):
        """
        Fetch the latest binary sensor state from the coordinator's Modbus client.

        Reads the configured register asynchronously and updates internal state.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self._register
        count = self.definition.get("count", 1)

        try:
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self._key,
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            self._state = None
            return

        if value is not None:
            if value == 1: 
                self._state = True
            elif value == 0:
                self._state = False
            else:
                _LOGGER.warning(
                    "Unknown register value %s for binary sensor %s", value, self._attr_name
                )
                self._state = None
        else:
            self._state = None

        await self.coordinator.async_update_value(
            self._key,
            self._state,
            register=register,
            scale=self.definition.get("scale"),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )

    @property
    def device_info(self) -> dict:
        """Return device info for device registry grouping."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }