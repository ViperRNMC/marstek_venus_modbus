"""
Module for creating number entities for Marstek Venus battery devices.
Numbers read Modbus registers asynchronously via the coordinator.
All entities are registered through the coordinator to enable centralized polling.
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
    """
    Set up number entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates number entities based on NUMBER_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback to add entities.
    """
    # Retrieve the coordinator instance from hass data and add entities
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MarstekNumber(coordinator, definition) for definition in coordinator.NUMBER_DEFINITIONS]
    async_add_entities(entities)   


class MarstekNumber(CoordinatorEntity, NumberEntity):
    """
    Representation of a Modbus number entity for Marstek Venus.

    Number state is read and write asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the number entity.

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
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True

        # Internal state variables
        self._state = None
        self._register = definition["register"]
        
        # Set min, max, and step from definition if provided
        self._attr_native_min_value = self.definition.get('min', 0)
        self._attr_native_max_value = self.definition.get('max', 100)
        self._attr_native_step = self.definition.get('step', 1)
        self._scale = definition.get("scale", 1)
        self._unit = definition.get("unit", None)

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
        return "number"

    @property
    def available(self) -> bool:
        """
        Return True if the coordinator has successfully fetched data.
        Used by Home Assistant to determine entity availability.
        """
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        """
        Return the current value of the number entity.
        Value is obtained from the coordinator's shared data dictionary.
        """
        data = self.coordinator.data
        if data is None:
            return None
        raw_value = data.get(self._key)
        return raw_value * self._scale if raw_value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """
        Write the given value to the Modbus register via the coordinator.
        This updates the number entity in Home Assistant.
        """
        # Convert the float value to an integer for Modbus
        raw_value = int(value / self._scale)
        
        # Optimistically update the coordinator data so HA shows the new state immediately
        self.coordinator.data[self._key] = raw_value
        self.async_write_ha_state()

        # Write the value using the coordinator's async_write_value method
        success = await self.coordinator.async_write_value(
            register=self._register,
            value=raw_value,
            key=self._key,
            scale=self._scale,
            unit=self._unit,
            entity_type=self.entity_type,
        )
        
        # Only refresh if write failed to get actual device state
        if not success:
            _LOGGER.debug("Write failed for %s, refreshing to get actual state", self._key)
            await self.coordinator.async_read_value(self.definition, self._key)

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