"""
This module defines a SelectEntity for setting and reading the user work mode
of a Marstek Venus battery via Modbus register 43000.
"""

# Import necessary components and modules
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import SELECT_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

class MarstekUserModeSelect(SelectEntity):
    """SelectEntity to manage the user work mode of the Marstek Venus battery."""

    def __init__(self, coordinator: MarstekCoordinator):
        """
        Initialize the select entity with the coordinator and set attributes.
        This includes the name, unique ID, options, and mapping for the work modes.
        """
        self.coordinator = coordinator
        self.definition = SELECT_DEFINITIONS[0]
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_should_poll = True  # Enable polling to refresh data
        self._attr_options = self.definition["options"]
        self._map_to_int = self.definition["map_to_int"]
        self._int_to_map = self.definition["int_to_map"]
        self._register = self.definition["register"]
        self._value = self._attr_options[0]

        # Optional: disable entity by default if specified in the sensor definition
        if self.definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    def select_option(self, option: str) -> None:
        """Handle selection of a new work mode option and write it to the Modbus register."""
        int_value = self._map_to_int.get(option)
        if int_value is not None:
            success = self.coordinator.client.write_register(self._register, int_value)
            if success:
                self._value = option

    async def async_update(self):
        """Fetch the current work mode from the Modbus register and update the entity state."""
        raw_value = self.coordinator.client.read_register(register=self._register, data_type="uint16", count=1)
        if raw_value is not None:
            if raw_value in self._int_to_map:
                self._value = self._int_to_map[raw_value]
            else:
                _LOGGER.warning("Unknown mode value read from register %s: %s", self._register, raw_value)

    @property
    def current_option(self):
        """Return the currently selected work mode option."""
        return self._value

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

# Setup function to add the select entity to Home Assistant
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the MarstekUserModeSelect entity using the provided config entry."""
    coordinator = MarstekCoordinator(hass, entry)
    async_add_entities([MarstekUserModeSelect(coordinator)])