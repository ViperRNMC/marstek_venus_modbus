"""
This module creates sensor entities for Marstek Venus battery devices by reading Modbus registers.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SENSOR_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """
    Setup function called by Home Assistant when loading the config entry.
    Creates a coordinator to manage communication and adds sensors based on predefined sensor definitions.
    """
    coordinator = MarstekCoordinator(hass, entry)

    # Create a list of MarstekSensor objects, one per sensor definition
    sensors = []
    for sensor_def in SENSOR_DEFINITIONS:
        sensors.append(MarstekSensor(coordinator, sensor_def))

    # Add the sensors to Home Assistant so they become visible and usable
    async_add_entities(sensors)
    
class MarstekSensor(SensorEntity):
    """
    Sensor entity for an individual Marstek Venus battery sensor.
    Tracks state and reads data via the coordinator.
    """
    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the sensor with a coordinator (responsible for data) and the sensor configuration.
        Sets name, unique ID, unit, device class, and state class based on the definition.
        """
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_should_poll = True  # Enable polling to refresh data
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self.states = definition.get("states", None)
        self._state = None

        # Optional: disable entity by default if specified in the sensor definition
        if self.definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    def update(self):
        """
        Update sensor state using appropriate data type handling.
        """
        data_type = self.definition.get("data_type", "uint16")

        # Read raw value from Modbus register using defined data type and count
        raw_value = self.coordinator.client.read_register(
            register=self.definition["register"],
            data_type=data_type,
            count=self.definition.get("count", 1)
        )

        if raw_value is not None:
            # Handle alarm_status sensor by decoding bit flags
            if self.definition.get("key") == "alarm_status":
                # Decode bits 0-3 for individual alarm flags
                """
                Special sensor entity for combined alarm status.

                Reads a 16-bit register containing alarm bit flags, where each bit
                indicates a different alarm condition.

                Bits decoded:
                - Bit 0: WiFi Abnormal
                - Bit 1: BLE Abnormal
                - Bit 2: Network Abnormal
                - Bit 3: CT Connection Abnormal

                The sensor state is a comma-separated list of active alarms,
                or "Normal" if none are active.
                """
                alarms = []
                if raw_value & (1 << 0):
                    alarms.append("WiFi Abnormal")
                if raw_value & (1 << 1):
                    alarms.append("BLE Abnormal")
                if raw_value & (1 << 2):
                    alarms.append("Network Abnormal")
                if raw_value & (1 << 3):
                    alarms.append("CT Connection Abnormal")

                # Combine all active alarm labels or set state to "Normal"
                self._state = ", ".join(alarms) if alarms else "Normal"

            # Handle string data types
            elif data_type == "char":
                # Convert raw value to string
                self._state = str(raw_value)

            # Handle numeric values with scaling and precision
            elif isinstance(raw_value, (int, float)):
                # Apply scaling and offset, then round to desired precision
                scaled = raw_value * self.definition.get("scale", 1) + self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)

            # Default fallback: use raw value directly
            else:
                self._state = raw_value

            # Map integer state to a friendly name if a states dictionary is defined
            if self.states and isinstance(self._state, int) and self._state in self.states:
                self._state = self.states[self._state]

    @property
    def native_value(self):
        """
        Returns the current value of the sensor to Home Assistant,
        so it can be displayed and used in automations.
        """
        return self._state
    
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