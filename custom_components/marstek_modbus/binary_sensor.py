"""
Module for creating binary sensor entities for Marstek Venus battery devices.
Binary sensors read Modbus registers asynchronously via the coordinator.
All entities are registered through the coordinator to enable centralized polling.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity
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
    # Retrieve the coordinator instance from hass data and add entities
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MarstekBinarySensor(coordinator, definition) for definition in coordinator.BINARY_SENSOR_DEFINITIONS]
    async_add_entities(entities)   


class MarstekBinarySensor(CoordinatorEntity, BinarySensorEntity):
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
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition     

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]
        
        # Internal state variables
        self._state = None
        self._register = definition["register"]

        # set category if defined in the definition
        if "category" in self.definition:
            self._attr_entity_category = EntityCategory(self.definition.get("category"))

        # Set icon if defined in the button definition
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default if specified in the definition
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "binary_sensor"

    @property
    def available(self) -> bool:
        """
        Return True if the coordinator has successfully fetched data.
        Used by Home Assistant to determine entity availability.
        """
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """
        Return True if binary sensor is on, False if off, None if unknown.
        State is obtained from the coordinator's shared data dictionary.
        """
        data = self.coordinator.data
        if data is None:
            return None
        return bool(data.get(self._key)) if self._key in data else None

    @property
    def device_info(self) -> dict:
        """
        Return device information for Home Assistant's device registry.
        Includes identifiers, name, manufacturer, model, and entry type.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }