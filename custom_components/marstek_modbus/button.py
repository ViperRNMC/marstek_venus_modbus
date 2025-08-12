"""
This module defines a ButtonEntity for triggering actions on a Marstek Venus battery
via Modbus register writes.
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .coordinator import MarstekCoordinator
from .const import BUTTON_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Set up the MarstekButton entities using the provided config entry.

    Retrieves the coordinator and creates button entities
    from the button definitions, then adds them to Home Assistant.
    """
    # Retrieve coordinator instance for this config entry
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Ensure coordinator has latest data before creating entities
    await coordinator.async_config_entry_first_refresh()

    # Create button entities for all button definitions
    entities = [MarstekButton(coordinator, definition) for definition in BUTTON_DEFINITIONS]

    # Register all button entities with Home Assistant
    async_add_entities(entities)


class MarstekButton(ButtonEntity):
    """ButtonEntity to trigger actions on the Marstek Venus battery."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the button entity with the coordinator and set attributes.

        Args:
            coordinator: Data update coordinator instance.
            definition: Dictionary with button configuration.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set entity name and unique ID
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True

        # Register and command value to write on button press
        self._register = self.definition["register"]
        self._command = self.definition.get("command", 1)  # Default command is 1

        # Set entity category if defined in the definition
        if "category" in self.definition:
            try:
                self._attr_entity_category = EntityCategory(self.definition["category"])
            except ValueError:
                _LOGGER.warning(
                    "Unknown entity category %s for button %s",
                    self.definition["category"],
                    self._attr_name,
                )

        # Set icon if defined in the button definition
        if "icon" in self.definition:
            self._attr_icon = self.definition["icon"]

        # Disable entity by default if specified in the definition
        if self.definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_press(self) -> None:
        """
        Handle button press by writing the specified value to the Modbus register.
        """
        success = await self.coordinator.client.async_write_register(
            self._register, self._command
        )
        if success:
            _LOGGER.debug(
                "Successfully wrote value %s to register %s on button press",
                self._command,
                self._register,
            )
        else:
            _LOGGER.warning(
                "Failed to write value %s to register %s on button press",
                self._command,
                self._register,
            )

    @property
    def device_info(self):
        """
        Return device information to associate entities with a device in the UI.

        This enables grouping of entities and supports the "Rename associated entities?" dialog.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }