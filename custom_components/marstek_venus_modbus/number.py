from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import MarstekCoordinator
from .const import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

NUMBER_ENTITIES = [
    {
        "name": "Set Forcible Charge Power",
        "address": 42020,
        "key": "set_charge_power",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W"
    },
    {
        "name": "Set Forcible Discharge Power",
        "address": 42021,
        "key": "set_discharge_power",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W"
    }
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    numbers = [MarstekNumber(coordinator, desc) for desc in NUMBER_ENTITIES]
    async_add_entities(numbers)

class MarstekNumber(NumberEntity):
    def __init__(self, coordinator: MarstekCoordinator, desc: dict):
        self.coordinator = coordinator
        self._address = desc["address"]
        self._attr_name = f"Marstek Venus {desc['name']}"
        self._attr_unique_id = f"marstek_{desc['key']}"
        self._attr_native_min_value = desc["min"]
        self._attr_native_max_value = desc["max"]
        self._attr_native_step = desc["step"]
        self._attr_native_unit_of_measurement = desc["unit"]
        self._value = None

    def set_native_value(self, value: float) -> None:
        int_val = int(value)
        success = self.coordinator.client.write_register(self._address, int_val)
        if success:
            self._value = int_val

    @property
    def native_value(self):
        return self._value