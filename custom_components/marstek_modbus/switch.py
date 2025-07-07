from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SWITCH_DEFINITIONS
from .const import DOMAIN
from .coordinator import MarstekCoordinator

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        MarstekSwitch(coordinator, switch_def)
        for switch_def in SWITCH_DEFINITIONS
    ]

    async_add_entities(switches)

class MarstekSwitch(SwitchEntity):
    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = f"Marstek Venus {definition['name']}"
        self._attr_unique_id = f"marstek_{coordinator.config_entry.entry_id}_{definition['key']}"
        self._state = False

    def turn_on(self, **kwargs):
        try:
            success = self.coordinator.client.write_register(self.definition["address"], self.definition["command_on"])
            if success:
                self._state = True
            else:
                _LOGGER.error(f"Failed to write to Modbus address {self.definition['address']}")
        except Exception as e:
            _LOGGER.error(f"Error turning on switch at address {self.definition['address']}: {e}")

    def turn_off(self, **kwargs):
        try:
            success = self.coordinator.client.write_register(self.definition["address"], self.definition["command_off"])
            if success:
                self._state = False
            else:
                _LOGGER.error(f"Failed to write to Modbus address {self.definition['address']}")
        except Exception as e:
            _LOGGER.error(f"Error turning off switch at address {self.definition['address']}: {e}")

    @property
    def is_on(self):
        return self._state