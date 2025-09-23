"""
This module defines a ButtonEntity for triggering actions on a Marstek Venus battery
via Modbus register writes.
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL

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
    Also registers the entity type in the coordinator to skip polling for buttons.
    """
    # Retrieve the coordinator instance from hass data and add entities
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MarstekButton(coordinator, definition) for definition in coordinator.BUTTON_DEFINITIONS]
    async_add_entities(entities)


class MarstekButton(ButtonEntity):
    """ButtonEntity to trigger actions on the Marstek Venus battery."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the button entity.

        Args:
            coordinator: Data update coordinator instance.
            definition: Dictionary with button configuration.
        """
        # Store the coordinator
        self.coordinator = coordinator
        self._key = definition["key"]
        self.definition = definition
        self._command = definition.get("command", 1)  # default command value
        self._register = definition["register"]

        # Register entity type in coordinator
        self.coordinator._entity_types[self._key] = "button"

        # Set entity attributes from definition
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._key}"
        self._attr_has_entity_name = True

        # Optional: set entity category
        if "category" in self.definition:
            self._attr_entity_category = EntityCategory(self.definition.get("category"))

        # Optional: set icon
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "button"

    @property
    def available(self) -> bool:
        """
        Return True if the coordinator has successfully fetched data.
        Used by Home Assistant to determine entity availability.
        """
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """
        Handle button press by writing the specified value to the Modbus register.
        """
        # Write the command value to the Modbus register asynchronously
        success = await self.coordinator.async_write_value(
            register=self._register,
            value=self._command,
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

        if success:
            import asyncio

            _LOGGER.debug(
                "Successfully wrote value %s to register %s on button press",
                self._command,
                self._register,
            )

            # Wait briefly to allow the device to process the change
            await asyncio.sleep(0.5)
            # Request coordinator to refresh data
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning(
                "Failed to write value %s to register %s on button press",
                self._command,
                self._register,
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