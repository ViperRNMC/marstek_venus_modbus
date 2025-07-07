"""
This module creates sensor entities for Marstek Venus battery devices by reading Modbus registers.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SENSOR_DEFINITIONS, DOMAIN
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
        if sensor_def.get("key") == "alarm_status":
            sensors.append(MarstekAlarmSensor(coordinator, sensor_def))
        else:
            sensors.append(MarstekSensor(coordinator, sensor_def))
    # ]

    #  # add alarm sensor for combined alarm status
    # alarm_defs = [d for d in SENSOR_DEFINITIONS if d.get("key") == "alarm_status"]
    # for alarm_def in alarm_defs:
    #     sensors.append(MarstekAlarmSensor(coordinator, alarm_def))   

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
        self._attr_name = f"{coordinator.config_entry.title} {definition['name']}"
        self._attr_unique_id = f"marstek_{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self.states = definition.get("states", None)
        self._attr_should_poll = True  # Enable polling to refresh data
        self._state = None

    def update(self):
        """
        Update sensor state using appropriate data type handling.
        """
        data_type = self.definition.get("type", "uint16")  # Default type

        # Use read_register instead of read_value
        raw_value = self.coordinator.client.read_register(
            address=self.definition["address"],
            data_type=data_type,
            count=self.definition.get("count", 1)
        )

        if raw_value is not None:
            if isinstance(raw_value, (int, float)):
                scaled = raw_value * self.definition.get("scale", 1) + self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)
            else:
                self._state = raw_value  # e.g., for char/string values

            if self.states and isinstance(self._state, int) and self._state in self.states:
                self._state = self.states[self._state]

    @property
    def native_value(self):
        """
        Returns the current value of the sensor to Home Assistant,
        so it can be displayed and used in automations.
        """
        return self._state
    
class MarstekAlarmSensor(MarstekSensor):
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

    def update(self):
        # Read 1 register (16 bits) from the configured address (should be 36001)
        raw_value = self.coordinator.client.read_register(
            address=self.definition["address"],
            data_type="uint16",
            count=1
        )

        if raw_value is not None:
            alarms = []

            # Check each relevant bit and append descriptive string if set
            if raw_value & (1 << 0):
                alarms.append("WiFi Abnormal")
            if raw_value & (1 << 1):
                alarms.append("BLE Abnormal")
            if raw_value & (1 << 2):
                alarms.append("Network Abnormal")
            if raw_value & (1 << 3):
                alarms.append("CT Connection Abnormal")

            # Set the sensor state as a joined string of active alarms,
            # or "Normal" if no alarms are active
            if alarms:
                self._state = ", ".join(alarms)
            else:
                self._state = "Normal"
