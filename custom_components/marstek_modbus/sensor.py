"""
This module creates sensor entities for Marstek Venus battery devices by reading Modbus registers.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity

from .const import (
    SENSOR_DEFINITIONS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    EFFICIENCY_SENSOR_DEFINITIONS,
    STORED_ENERGY_SENSOR_DEFINITIONS,
)
from .coordinator import MarstekCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

def get_entity_type(entity) -> str:
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """
    Set up sensor entities when the config entry is loaded.

    This function creates a coordinator and uses sensor definitions
    to instantiate sensor entities, then adds them to Home Assistant.
    """
    # Get the coordinator instance from hass.data
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Await the first data refresh so coordinator.data is populated before use it
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Add entities defined in SENSOR_DEFINITIONS
    for definition in SENSOR_DEFINITIONS:
        entities.append(MarstekSensor(coordinator, definition))

    # Add battery efficiency entities from definitions
    for definition in EFFICIENCY_SENSOR_DEFINITIONS:
        entities.append(MarstekEfficiencySensor(coordinator, definition))

    # Add stored energy entities from definitions
    for definition in STORED_ENERGY_SENSOR_DEFINITIONS:
        entities.append(MarstekStoredEnergySensor(coordinator, definition))

    # Register all created sensor entities with Home Assistant
    async_add_entities(entities)


class MarstekSensor(SensorEntity):
    """
    Sensor entity representing a single Marstek Venus battery sensor.

    Reads data via the coordinator and updates state accordingly.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the sensor entity.

        Args:
            coordinator (MarstekCoordinator): Coordinator managing data.
            definition (dict): Sensor configuration including register info.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set entity attributes from definition
        self._attr_name = f"{definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True
        self._attr_should_poll = True  # Enable polling updates

        # Set optional attributes if provided in definition
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self.states = definition.get("states", None)

        self._state = None

        # Optionally disable entity by default if specified
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self):
        """Return True if coordinator data update was successful and state is set."""
        return self.coordinator.last_update_success and self._state is not None

    def _combine_registers(self, registers):
        """
        Combine multiple 16-bit registers into one integer.

        Assumes little-endian byte order.
        """
        value = 0
        for i, reg in enumerate(registers):
            value |= (reg & 0xFFFF) << (16 * i)
        return value

    async def async_update(self):
        """
        Asynchronously update the sensor state.

        Reads register values via the coordinator's client and processes
        them based on the sensor's data type and configuration.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self.definition["register"]
        count = self.definition.get("count", 1)

        try:
            # Request the register value asynchronously
            raw_value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self.definition.get("key", self.definition.get("name", "unknown")),
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            return


        # If multiple registers returned, combine them
        if isinstance(raw_value, (list, tuple)):
            raw_value = self._combine_registers(raw_value)

        # Process raw_value based on sensor config
        if raw_value is not None:
            if self.definition.get("bit_descriptions"):
                # For bitmask sensors, convert bits to labels
                active_flags = []
                bit_map = self.definition["bit_descriptions"]
                for bit, label in bit_map.items():
                    if raw_value & (1 << bit):
                        active_flags.append(label)
                self._state = ", ".join(active_flags) if active_flags else "Normal"

            elif data_type == "char":
                # Character/string data type is stored as is
                self._state = str(raw_value)

            elif isinstance(raw_value, (int, float)):
                # Apply scale and offset if specified, round to precision
                scaled = raw_value * self.definition.get("scale", 1)
                scaled += self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)

            else:
                # Fallback: just store raw_value directly
                self._state = raw_value

            await self.coordinator.async_update_sensor(
                self.definition["key"],
                self._state,
                register=self.definition.get("register"),
                scale=self.definition.get("scale"),
                unit=self.definition.get("unit"),
                entity_type=get_entity_type(self)
            )

            # Map integer state to predefined states if applicable
            if self.states and isinstance(self._state, int) and self._state in self.states:
                self._state = self.states[self._state]

    @property
    def native_value(self):
        """
        Return the current state value for Home Assistant.
        """
        # Use the coordinator's data for the sensor value
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            return self.coordinator.data.get(self.definition["key"])
        return None

    @property
    def device_info(self):
        """
        Return device information for Home Assistant device registry.

        Groups entities under the same device in the UI.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }


class MarstekEfficiencySensor(SensorEntity):
    """
    Sensor entity calculating round-trip battery efficiency.

    Uses charge, discharge, SOC, and max energy values from coordinator data.
    """

    def __init__(self, coordinator, definition):
        """
        Initialize efficiency sensor entity.
        """
        self.coordinator = coordinator
        self.definition = definition

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['unique_id_key']}"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = "battery"
        self._attr_state_class = "measurement"
        self._attr_enabled_by_default = True
        self._attr_has_entity_name = True

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        self.async_write_ha_state()

    @property
    def should_poll(self):
        """Efficiency sensor does not require polling."""
        return False

    @property
    def available(self):
        """Return True if coordinator data update was successful."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self):
        """Device info for grouping entities in UI."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    @property
    def native_value(self):
        """Calculate and return efficiency percentage."""
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
                efficiency = ((discharge + stored) / charge) * 100
                return round(efficiency, 1)
        except (ValueError, TypeError):
            return None

        return 0


class MarstekStoredEnergySensor(SensorEntity):
    """
    Sensor entity for stored battery energy based on SOC and max energy.
    """

    def __init__(self, coordinator, definition):
        """
        Initialize stored energy sensor entity.
        """
        self.coordinator = coordinator
        self.definition = definition

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['unique_id_key']}"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = "energy"
        self._attr_state_class = "measurement"
        self._attr_enabled_by_default = True
        self._attr_has_entity_name = True

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        self.async_write_ha_state()

    @property
    def should_poll(self):
        """Stored energy sensor does not require polling."""
        return False

    @property
    def available(self):
        """Return True if coordinator data update was successful."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self):
        """Device info for grouping entities in UI."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    @property
    def native_value(self):
        """Calculate and return stored energy value in kWh."""
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
