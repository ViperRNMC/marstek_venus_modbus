"""
This module creates sensor entities for Marstek Venus battery devices by reading Modbus registers.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SENSOR_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL, EFFICIENCY_SENSOR_DEFINITIONS, STORED_ENERGY_SENSOR_DEFINITIONS
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

    # Fetch the first update to ensure coordinator.data is available for sensors
    await coordinator.async_config_entry_first_refresh()

    # Create a list of MarstekSensor objects, one per sensor definition
    sensors = []
    for sensor_def in SENSOR_DEFINITIONS:
        sensors.append(MarstekSensor(coordinator, sensor_def))

    # Add efficiency sensors from definitions
    for definition in EFFICIENCY_SENSOR_DEFINITIONS:
        sensors.append(MarstekEfficiencySensor(coordinator, definition))

    # Add stored energy sensors from definitions
    for definition in STORED_ENERGY_SENSOR_DEFINITIONS:
        sensors.append(MarstekStoredEnergySensor(coordinator, definition))

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
            # Generic dynamic bit flag decoding if bit_descriptions is present
            if self.definition.get("bit_descriptions"):
                """
                Decode bit flags dynamically from bit_descriptions defined in const.py.
                """
                active_flags = []
                bit_map = self.definition["bit_descriptions"]

                for bit, label in bit_map.items():
                    if raw_value & (1 << bit):
                        active_flags.append(label)

                self._state = ", ".join(active_flags) if active_flags else "Normal"

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
        """
        Return device information to associate entities with a device in the UI.

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


class MarstekEfficiencySensor(SensorEntity):
    """
    Sensor entity to calculate round-trip efficiency of the battery based on
    total, monthly, or daily charging/discharging registers and live SOC.
    """

    def __init__(self, coordinator, definition):
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['unique_id_key']}"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = "battery"
        self._attr_state_class = "measurement"
        self._attr_enabled_by_default = True
        self._attr_has_entity_name = True

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service"
        }

    @property
    def native_value(self):
        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        charge = data.get(self.definition["charge_key"])
        discharge = data.get(self.definition["discharge_key"])
        soc = data.get(self.definition["soc_key"])
        max_energy = data.get(self.definition["max_energy_key"])

        if None in (charge, discharge, soc, max_energy):
            return None

        try:
            soc = float(soc)
            max_energy = float(max_energy)
            charge = float(charge)
            discharge = float(discharge)
            stored = soc / 100 * max_energy

            if charge > 0:
                return round(((discharge + stored) / charge) * 100, 1)
        except (ValueError, TypeError):
            return None

        return 0

    @property
    def available(self):
        return isinstance(self.coordinator.data, dict)

class MarstekStoredEnergySensor(SensorEntity):
    """
    Sensor entity to calculate current stored energy based on SOC and max battery energy.
    """

    def __init__(self, coordinator, definition):
        self.coordinator = coordinator
        self.definition = definition
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['unique_id_key']}"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = "energy"
        self._attr_state_class = "measurement"
        self._attr_enabled_by_default = True
        self._attr_has_entity_name = True

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service"
        }

    @property
    def native_value(self):
        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        soc = data.get(self.definition["soc_key"])
        max_energy = data.get(self.definition["max_energy_key"])

        if None in (soc, max_energy):
            return None
        try:
            soc = float(soc)
            max_energy = float(max_energy)
            return round(soc / 100 * max_energy, 2)
        except (ValueError, TypeError):
            return None

    @property
    def available(self):
        return isinstance(self.coordinator.data, dict)