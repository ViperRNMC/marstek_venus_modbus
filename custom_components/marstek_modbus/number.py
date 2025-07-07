"""
Module for creating number entities for Marstek Venus battery devices.
The number retrieve data by reading Modbus registers.
"""

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import NUMBER_DEFINITIONS, DOMAIN
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
    def __init__(self, coordinator: MarstekCoordinator, desc: dict):
        """
        Initialize the number entity with coordinator and descriptor dictionary.
        Sets up attributes such as name, unique ID, min/max values, step, and unit.
        """
        self.coordinator = coordinator
        self._address = desc["address"]
        self._attr_name = f"{coordinator.config_entry.title} {desc['name']}"
        self._attr_unique_id = f"marstek_{coordinator.config_entry.entry_id}_{desc['key']}"
        self._attr_native_min_value = desc["min"]
        self._attr_native_max_value = desc["max"]
        self._attr_native_step = desc["step"]
        self._attr_native_unit_of_measurement = desc["unit"]
        self._value = None

    def set_native_value(self, value: float) -> None:
        """
        Write a new value to the device register.
        Converts the float value to int and writes it using the coordinator's client.
        If successful, updates the internal value.
        """
        int_val = int(value)
        success = self.coordinator.client.write_register(self._address, int_val)
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
            address=self._address,
            data_type="uint16",
            count=1
        )
        if raw_value is not None:
            self._value = raw_value
        else:
            _LOGGER.warning("Failed to update register value at address %s", self._address)