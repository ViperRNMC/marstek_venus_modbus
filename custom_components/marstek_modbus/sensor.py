"""
Marstek Venus Modbus sensor entities.

All sensors now derive their values from the shared coordinator data.
No separate async_update needed; coordinator handles polling.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MarstekCoordinator
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_DEFINITIONS,
    BINARY_SENSOR_DEFINITIONS,
    EFFICIENCY_SENSOR_DEFINITIONS,
    STORED_ENERGY_SENSOR_DEFINITIONS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all Marstek sensors from definitions."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create sensor entities from definitions
    entities = [MarstekSensor(coordinator, d) for d in SENSOR_DEFINITIONS]
    entities.extend(
        MarstekEfficiencySensor(coordinator, d) for d in EFFICIENCY_SENSOR_DEFINITIONS
    )
    entities.extend(
        MarstekStoredEnergySensor(coordinator, d) for d in STORED_ENERGY_SENSOR_DEFINITIONS
    )

    # Add all entities to Home Assistant
    async_add_entities(entities)


class MarstekSensor(CoordinatorEntity, SensorEntity):
    """Generic Modbus sensor reading from the coordinator."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition     

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True

        # Set basic attributes from definition
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")

        # Optional: entity category and icon
        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Optional states mapping for int → label conversion
        self.states = definition.get("states")

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "sensor"

    @property
    def available(self) -> bool:
        """Return True if coordinator has valid data for this sensor."""
        # Ensure coordinator data is a dict and contains the key, and update was successful
        return (
            getattr(self.coordinator, "last_update_success", False)
            and isinstance(getattr(self.coordinator, "data", None), dict)
            and self._key in self.coordinator.data
        )

    @property
    def native_value(self):
        """Return the value from coordinator data with scaling and states applied."""
        if self._key not in self.coordinator.data:
            return None
        value = self.coordinator.data[self._key]

        if isinstance(value, (int, float)):
            value = value * self.definition.get("scale", 1) + self.definition.get("offset", 0)
            value = round(value, self.definition.get("precision", 0))

        if self.states and value in self.states:
            return self.states[value]

        return value

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }


class MarstekCalculatedSensor(CoordinatorEntity, SensorEntity):
    """
    Base class for calculated sensors that depend on multiple coordinator keys.

    Handles registration of dependency keys and provides update handling.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """Initialize the calculated sensor and register dependencies."""
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_name = f"{self.definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True

        # Set basic attributes from definition
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")
        self._attr_has_entity_name = True

        # Optional: entity category and icon
        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Register dependency keys in coordinator and set scales
        for alias, dep_key in self.get_dependency_keys().items():
            if not dep_key:
                continue

            self.coordinator._entity_types[dep_key] = "sensor"

            # Combine all definitions for iteration
            if not hasattr(self, "_all_definitions"):
                self._all_definitions = (
                    SENSOR_DEFINITIONS
                    + BINARY_SENSOR_DEFINITIONS
                )
            all_definitions = self._all_definitions

            # Get scale from all definitions or fallback to current sensor dependency_defs
            scale = next((d.get("scale", 1) for d in all_definitions if d.get("key") == dep_key), None)
            scale = scale or self.definition.get("dependency_defs", {}).get(alias, 1)

            self.coordinator._scales[dep_key] = scale

    def get_dependency_keys(self):
        """Return the keys this sensor depends on."""
        return self.definition.get("dependency_keys", {})

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "sensor"

    @property
    def device_info(self) -> dict:
        """Return device info so sensor is linked to the integration/device."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    def _handle_coordinator_update(self) -> None:
        """
        Handle coordinator update by recalculating the sensor value.

        Calls the subclass's calculate_value method and updates state.
        """
        if not getattr(self.coordinator, "last_update_success", False):
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}

        self._calculate(data)
        self.async_write_ha_state()

    def _calculate(self, data: dict) -> None:
        """
        Centralized method to check dependencies, log missing values,
        calculate value, and update native_value attribute.
        """
        dependency_keys = self.get_dependency_keys()
        dep_values = {}
        missing = []

        # dependency_keys is a dict alias -> actual key
        for alias, actual_key in dependency_keys.items():
            val = data.get(actual_key)
            scale = self.coordinator._scales.get(actual_key, 1)
            if val is None:
                missing.append(alias)
            else:
                dep_values[alias] = float(val) * scale

        if missing:
            _LOGGER.warning(
                "%s missing required value(s): %s. Current data: %s. Cannot calculate value.",
                self._attr_name, ", ".join(missing), {k: data.get(v) for k, v in dependency_keys.items()},
            )
            self._attr_native_value = None
            return

        try:
            value = self.calculate_value(dep_values)
            _LOGGER.debug(
                "Calculated value for %s: %s (input values: %s)",
                self._attr_name,
                value,
                dep_values
            )
            self._attr_native_value = value
        except Exception as ex:
            _LOGGER.warning(
                "Error calculating value for sensor %s: %s", self._attr_name, ex
            )
            self._attr_native_value = None

    def calculate_value(self, dep_values: dict):
        """
        Calculate the sensor value from scaled dependency values.

        Must be implemented by subclasses.
        """
        raise NotImplementedError


class MarstekStoredEnergySensor(MarstekCalculatedSensor):
    """
    Sensor calculating stored battery energy (kWh).

    Uses SOC (%) and battery total energy (kWh) from coordinator data.
    """
    def calculate_value(self, dep_values: dict):
        """Calculate stored energy based on SOC and capacity dynamically."""
        soc = dep_values.get("soc")
        capacity = dep_values.get("capacity")
        stored_energy = round((soc / 100) * capacity, 2)
        self._attr_native_value = stored_energy
        return stored_energy


class MarstekEfficiencySensor(MarstekCalculatedSensor):
    """
    Calculate Round Trip Efficiency (RTE) as a percentage.

    Uses charge (kWh) and discharge (kWh) energy values from coordinator data. 
    """
    def calculate_value(self, dep_values: dict):
        """Calculate efficiency dynamically from definition."""
        charge = dep_values.get("charge")
        discharge = dep_values.get("discharge")
        efficiency = min((discharge / charge) * 100, 100.0)
        efficiency_rounded = round(efficiency, 1)
        self._attr_native_value = efficiency_rounded
        return efficiency_rounded