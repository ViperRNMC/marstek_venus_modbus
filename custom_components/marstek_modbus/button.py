"""
This module defines a ButtonEntity for triggering actions on a Marstek Venus battery
via Modbus register writes.
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import BUTTON_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class MarstekButton(ButtonEntity):
    """ButtonEntity to trigger actions on the Marstek Venus battery."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the button entity with the coordinator and set attributes.
        This includes the name, unique ID, and register information.
        """
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._register = self.definition["register"]
        self._value = self.definition.get("value", 1)  # Default value to write on press

        # Set icon if defined in the button definition
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default if specified in the definition
        if self.definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        """Handle button press by writing the specified value to the Modbus register."""
        success = await self.coordinator.client.async_write_register(self._register, self._value)
        if success:
            _LOGGER.debug("Successfully wrote value %s to register %s on button press", self._value, self._register)
        else:
            _LOGGER.warning("Failed to write value %s to register %s on button press", self._value, self._register)

    @property
    def device_info(self):
        """Return device information to associate entities with a device in the UI.

        This enables the "Rename associated entities?" dialog when the user renames the integration instance.
        It also groups all entities under one device in the Home Assistant device registry.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service"
        }    

# Setup function to add the button entities to Home Assistant
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the MarstekButton entities using the provided config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()
    entities = [MarstekButton(coordinator, definition) for definition in BUTTON_DEFINITIONS]
    async_add_entities(entities)