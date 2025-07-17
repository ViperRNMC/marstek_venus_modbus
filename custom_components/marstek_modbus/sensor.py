"""
This module defines sensor entities for the Marstek Venus Modbus integration.

It includes:
- Basic sensors reading registers via Modbus.
- Specialized sensors for battery efficiency and stored energy calculations.
"""

import logging

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

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """
    Determine the entity type (sensor, switch, select, etc.) based on the class name.

    Args:
        entity: Home Assistant entity instance.

    Returns:
        Lowercase string representing the type of the entity.
    """
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Set up sensor entities when the config entry is loaded.

    Retrieves the coordinator from hass.data, waits for the initial refresh,
    and creates sensor entities based on definitions.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback function to add entities to Home Assistant.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Add basic sensors defined in SENSOR_DEFINITIONS
    for definition in SENSOR_DEFINITIONS:
        entities.append(MarstekSensor(coordinator, definition))

    # Add battery efficiency sensors from definitions
    for definition in EFFICIENCY_SENSOR_DEFINITIONS:
        entities.append(MarstekEfficiencySensor(coordinator, definition))

    # Add stored energy sensors from definitions
    for definition in STORED_ENERGY_SENSOR_DEFINITIONS:
        entities.append(MarstekStoredEnergySensor(coordinator, definition))

    async_add_entities(entities)


class MarstekSensor(SensorEntity):
    """
    Represents a single Modbus sensor for the Marstek Venus battery.

    Reads data from registers via the coordinator and updates its state accordingly.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the sensor entity.

        Args:
            coordinator: Coordinator managing data retrieval.
            definition: Sensor definition dictionary with config like register, scale, unit.
        """
        self.coordinator = coordinator
        self.definition = definition

        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self.states = definition.get("states")
        self._state = None

        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """Call on entity addition, update state immediately."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self):
        """Return True if sensor data is available and last update succeeded."""
        return self.coordinator.last_update_success and self._state is not None

    def _combine_registers(self, registers):
        """
        Combine multiple 16-bit registers into a single integer value (little-endian).

        Args:
            registers: List of register values.

        Returns:
            Combined integer value.
        """
        value = 0
        for i, reg in enumerate(registers):
            value |= (reg & 0xFFFF) << (16 * i)
        return value

    async def async_update(self):
        """
        Asynchronously update the sensor's state by reading Modbus registers.

        Handles bit flags, char types, scaling, offset, and rounding.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self.definition["register"]
        count = self.definition.get("count", 1)

        try:
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self.definition.get("key", self.definition.get("name", "unknown")),
            )
        except Exception as err:
            _LOGGER.error("Error reading register 0x%X: %s", register, err)
            return

        if isinstance(value, (list, tuple)):
            value = self._combine_registers(value)

        if value is not None:
            if self.definition.get("bit_descriptions"):
                # Decode bit flags into human-readable labels
                active_flags = [
                    label for bit, label in self.definition["bit_descriptions"].items() if value & (1 << bit)
                ]
                self._state = ", ".join(active_flags) if active_flags else "Normal"

            elif data_type == "char":
                self._state = str(value)

            elif isinstance(value, (int, float)):
                scaled = value * self.definition.get("scale", 1)
                scaled += self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)

            else:
                self._state = value

            # Update coordinator with new value for logging and data storage
            await self.coordinator.async_update_value(
                self.definition["key"],
                self._state,
                register=register,
                scale=self.definition.get("scale"),
                unit=self.definition.get("unit"),
                entity_type=get_entity_type(self),
            )

            # Map integer states to readable strings if defined
            if self.states and isinstance(self._state, int) and self._state in self.states:
                self._state = self.states[self._state]

    @property
    def native_value(self):
        """Return current sensor value from coordinator data."""
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            return self.coordinator.data.get(self.definition["key"])
        return None

    @property
    def device_info(self):
        """
        Provide device info for Home Assistant device registry.

        Groups all entities under the same device.
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
    Sensor for round-trip battery efficiency calculation.

    Uses charge, discharge, SOC, and max energy values from coordinator data.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """Initialize the efficiency sensor."""
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
        """No polling needed, data derived from coordinator."""
        return False

    @property
    def available(self):
        """True if coordinator data is valid and updated."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self):
        """Device info for grouping entities."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    @property
    def native_value(self):
        """Calculate and return the round-trip efficiency percentage."""
        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}

        charge = data.get(self.definition["charge_key"])
        discharge = data.get(self.definition["discharge_key"])
        soc = data.get(self.definition["soc_key"])
        max_energy = data.get(self.definition["max_energy_key"])
        if None in (charge, discharge, soc, max_energy):
            return None

        try:
            charge = float(charge)
            discharge = float(discharge)
            soc = float(soc)
            max_energy = float(max_energy)

            stored_energy = soc / 100 * max_energy

            if charge > 0:
                efficiency = ((discharge + stored_energy) / charge) * 100
                return round(efficiency, 1)
        except (ValueError, TypeError):
            return None

        return 0


class MarstekStoredEnergySensor(SensorEntity):
    """
    Sensor calculating stored battery energy (kWh).

    Uses SOC and max energy values from coordinator data.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """Initialize stored energy sensor."""
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
        """No polling required since value derived from coordinator data."""
        return False

    @property
    def available(self):
        """True if coordinator data is valid and updated."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def device_info(self):
        """Device info for grouping entities."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    @property
    def native_value(self):
        """Calculate and return stored energy in kWh."""
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