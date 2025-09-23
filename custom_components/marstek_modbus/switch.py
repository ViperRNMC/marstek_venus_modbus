"""
Module for creating switch sensor entities for Marstek Venus battery devices.
switch sensors read and write Modbus registers asynchronously via the coordinator.
All entities are registered through the coordinator to enable centralized polling.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity
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
    Set up switch sensor entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates switch entities based on SWITCH_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback to add entities.
    """
    # Retrieve the coordinator instance from hass data and add entities
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MarstekSwitch(coordinator, definition) for definition in coordinator.SWITCH_DEFINITIONS]
    async_add_entities(entities)


class MarstekSwitch(CoordinatorEntity, SwitchEntity):
    """
    Representation of a Modbus switch entity for Marstek Venus.

    Sensor state is read and write asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the switch entity.

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
        return "switch"

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
        Return True if switch sensor is on, False if off, None if unknown.

        Uses the coordinator's shared data dictionary and compares
        with the command_on value from the definition to handle
        inverted logic (0 = on, 1 = off).
        """
        data = self.coordinator.data
        if data is None or self._key not in data:
            return None

        current_value = data[self._key]
        return current_value == self.definition.get("command_on")

    async def async_turn_on(self, **kwargs) -> None:
        """
        Turn the switch on via the coordinator.
        This should trigger writing to the Modbus register.
        """
        value = self.definition.get("command_on")
        if value is None:
            _LOGGER.error("No command_on value defined for switch %s", self._attr_name)
            return

        # Optimistically update the coordinator data so HA shows the new state immediately
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()

        # Write the value using the coordinator's async_write_value method
        await self.coordinator.async_write_value(
            register=self._register,
            value=value,
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

    async def async_turn_off(self, **kwargs) -> None:
        """
        Turn the switch off via the coordinator.
        This should trigger writing to the Modbus register.
        """
        value = self.definition.get("command_off")
        if value is None:
            _LOGGER.error("No command_off value defined for switch %s", self._attr_name)
            return

        # Optimistically update the coordinator data so HA shows the new state immediately
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()

        # Write the value using the coordinator's async_write_value method
        await self.coordinator.async_write_value(
            register=self._register,
            value=value,
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

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