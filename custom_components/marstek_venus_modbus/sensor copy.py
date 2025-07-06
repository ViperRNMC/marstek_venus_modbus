from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SENSOR_DEFINITIONS, DOMAIN
from .coordinator import MarstekCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = MarstekCoordinator(hass, entry)
    # await coordinator.async_config_entry_first_refresh()

    sensors = [
        MarstekSensor(coordinator, sensor_def)
        for sensor_def in SENSOR_DEFINITIONS
    ]

    async_add_entities(sensors)

class MarstekSensor(SensorEntity):
    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = f"Marstek Venus {definition['name']}"
        self._attr_unique_id = f"marstek_{definition['key']}"
        self._attr_native_unit_of_measurement = definition["unit"]
        self._attr_device_class = definition["device_class"]
        self._attr_should_poll = True
        self._state = None

    def update(self):
        registers = self.coordinator.client.read_register(self.definition["address"], count=1)
        if registers:
            raw = registers[0]
            scaled = raw * self.definition.get("scale", 1) + self.definition.get("offset", 0)
            precision = self.definition.get("precision", 0)
            self._state = round(scaled, precision)

    @property
    def native_value(self):
        return self._state