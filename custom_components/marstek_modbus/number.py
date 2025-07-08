"""
Module for creating number entities for Marstek Venus battery devices.
The number retrieve data by reading Modbus registers.
"""

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import NUMBER_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator



# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """
    Set up number entities for the Marstek device from a config entry.
    Retrieves the coordinator instance and creates MarstekNumber entities
    based on the predefined NUMBER_ENTITIES list, then adds them to Home Assistant.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    numbers = [MarstekNumber(coordinator, desc) for desc in NUMBER_DEFINITIONS]
    async_add_entities(numbers)

class MarstekNumber(NumberEntity):
    """
    Representation of a Marstek number entity that can be read from and written to
    a Modbus register via the coordinator's client.
    """
    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the number entity with coordinator and descriptor dictionary.
        Sets up attributes such as name, unique ID, min/max values, step, and unit.
        """
        self.coordinator = coordinator
        self.definition = definition
        self._register = definition["register"]
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_should_poll = True  # Enable polling to refresh data
        self._attr_native_min_value = self.definition["min"]
        self._attr_native_max_value = self.definition["max"]
        self._attr_native_step = self.definition["step"]
        self._attr_native_unit_of_measurement = self.definition["unit"]
        self._value = None

    def set_native_value(self, value: float) -> None:
        """
        Write a new value to the device register.
        Converts the float value to int and writes it using the coordinator's client.
        If successful, updates the internal value.
        """
        int_val = int(value)
        success = self.coordinator.client.write_register(self._register, int_val)
        if success:
            self._value = int_val

    @property
    def native_value(self):
        """
        Return the current native value of the entity.
        """
        return self._value

    async def async_update(self):
        """
        Asynchronously update the entity's value by reading from the device register.
        Logs a warning if the read operation fails.
        """
        raw_value = self.coordinator.client.read_register(
            register=self._register,
            data_type="uint16",
            count=1
        )
        if raw_value is not None:
            self._value = raw_value
        else:
            _LOGGER.warning("Failed to update register value at register %s", self._register)

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