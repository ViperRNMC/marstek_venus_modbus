"""
Handles all sensor polling via Home Assistant DataUpdateCoordinator,
with per-sensor intervals and optional skipping if not due.
"""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BINARY_SENSOR_DEFINITIONS,
    NUMBER_DEFINITIONS,
    SENSOR_DEFINITIONS,
    SELECT_DEFINITIONS,
    SWITCH_DEFINITIONS,
    EFFICIENCY_SENSOR_DEFINITIONS,
    STORED_ENERGY_SENSOR_DEFINITIONS,
    SCAN_INTERVAL,    
)
from .helpers.modbus_client import MarstekModbusClient

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """Determine entity type based on its class inheritance."""
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


class MarstekCoordinator(DataUpdateCoordinator):
    """Coordinator managing all Marstek Venus Modbus sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator with connection parameters and update interval."""
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.message_wait_ms = entry.data.get("message_wait_milliseconds", 200)
        self.timeout = entry.data.get("timeout", 5)

        # Mapping from sensor key to entity type for logging and processing
        self._entity_types: dict[str, str] = {}

        # Store the config entry for potential future use
        self.config_entry = entry

        # Scaling factors for sensors, if applicable
        self._scales: dict[str, float] = {} 

        # Combine all sensor definitions for polling
        self._all_definitions = (
            SENSOR_DEFINITIONS
            + BINARY_SENSOR_DEFINITIONS
            + SELECT_DEFINITIONS
            + NUMBER_DEFINITIONS
            + SWITCH_DEFINITIONS
        )

        # Initialize Modbus client for communication
        self.client = MarstekModbusClient(
            self.host,
            self.port,
            message_wait_ms=self.message_wait_ms,
            timeout=self.timeout,
        )

        # Data storage for sensor values and timestamps of last updates
        self.data: dict = {}
        self._last_update_times: dict = {}

        # Determine the minimum scan interval among all sensors, default to 30 seconds
        min_interval = min(SCAN_INTERVAL.values()) if SCAN_INTERVAL else 30
        update_interval = timedelta(seconds=min_interval)

        # Initialize the base DataUpdateCoordinator with the calculated interval
        super().__init__(
            hass,
            _LOGGER,
            name="MarstekCoordinator",
            update_interval=update_interval,
        )
         
        _LOGGER.debug("Coordinator initialized with update_interval: %s", update_interval)

    def register_entity_type(self, key: str, entity_type: str):
        """Register the entity type for a given sensor key.
        For calculated sensors with dependencies, ensure all dependency keys are registered.
        """
        self._entity_types[key] = entity_type

        # Register all dependency keys with entity type and scale
        definition = next((d for d in SENSOR_DEFINITIONS if d["key"] == key), None)
        if definition and "dependency_keys" in definition:
            for dep_alias, dep_key in definition["dependency_keys"].items():
                if dep_key not in self._entity_types:
                    # Use the same entity type as the parent sensor
                    self._entity_types[dep_key] = entity_type

                # Retrieve scale from the dependency sensor definition
                dep_def = next((d for d in SENSOR_DEFINITIONS if d["key"] == dep_key), None)
                if dep_def:
                    scale = dep_def.get("scale")
                    if scale is not None:
                        self._scales[dep_key] = scale

    async def async_init(self):
        """Asynchronously initialize the Modbus connection."""
        connected = await self.client.async_connect()
        if not connected:
            _LOGGER.error("Failed to connect to Modbus device at %s:%d", self.host, self.port)
        return connected

    async def async_read_value(self, sensor: dict, key: str):
        """Helper to read a single sensor value from Modbus with logging and type checking."""
        entity_type = self._entity_types.get(key, get_entity_type(sensor))

         # Determine scale and unit
        scale = self._scales.get(key, sensor.get("scale", 1))
        unit = sensor.get("unit", "N/A")

        try:
            value = await self.client.async_read_register(
                register=sensor["register"],
                data_type=sensor.get("data_type", "uint16"),
                count=sensor.get("count", 1),
                sensor_key=key,
            )

            if isinstance(value, (int, float, bool, str)):
                _LOGGER.debug(
                     "Updated %s '%s': register=%d, value=%s, scale=%s, unit=%s",
                    entity_type,
                    key,
                    sensor["register"],
                    value,
                    scale,
                    unit,
            )   
                return value
            else:
                _LOGGER.warning(
                    "Invalid value for %s '%s': %r (type %s)",
                    entity_type, key, value, type(value).__name__,
                )
                return None

        except Exception as e:
            _LOGGER.error(
                "Error reading %s '%s' at register %d: %s",
                entity_type, key, sensor["register"], e,
            )
            return None

    async def async_write_value(
        self,
        register: int,
        value: int,
        key: str,
        scale=None,
        unit=None,
        entity_type="unknown",
    ):
        """Write a value to a Modbus register asynchronously and log the operation."""
        try:
            await self.client.async_write_register(register=register, value=value)
            _LOGGER.debug(
                "Wrote to %s '%s': register=%d (0x%04X), value=%s, scale=%s, unit=%s",
                entity_type,
                key,
                register,
                register,
                value,
                scale if scale is not None else 1,
                unit if unit is not None else "N/A",
            )
            return True
        except Exception as e:
            _LOGGER.error(
                "Failed to write value %s to register 0x%X: %s", value, register, e
            )
            return False

    async def _async_update_data(self):
        """Update all sensors asynchronously with per-sensor interval skipping.

        Buttons are excluded as they are not polled.
        Sensors disabled in Home Assistant are skipped, except dependencies which are always fetched.
        """
        from homeassistant.util.dt import utcnow
        from homeassistant.helpers import entity_registry as er

        now = utcnow()
        updated_data = {}

        _LOGGER.debug("Coordinator poll tick at %s", now.isoformat())

        # Get the entity registry to check for disabled entities
        entity_registry = er.async_get(self.hass)

        # Collect all dependency keys from all definitions
        all_definitions_for_deps = EFFICIENCY_SENSOR_DEFINITIONS + STORED_ENERGY_SENSOR_DEFINITIONS
        dependency_keys_set = {dep_key for defn in all_definitions_for_deps
                            for dep_key in defn.get("dependency_keys", {}).values()
                            if dep_key}

        # Debug logging
        for dep_key in dependency_keys_set:
            _LOGGER.debug("Dependency key '%s'", dep_key)

        # Iterate over each sensor definition to poll if due
        for sensor in self._all_definitions:
            key = sensor["key"]
            entity_type = self._entity_types.get(key, get_entity_type(sensor))
            unique_id = f"{self.config_entry.entry_id}_{sensor['key']}"
            registry_entry = entity_registry.async_get_entity_id(entity_type, self.config_entry.domain, unique_id)

            # Determine if the entity is disabled in Home Assistant
            is_disabled = False
            entry = entity_registry.entities.get(registry_entry) if registry_entry else None
            if entry:
                is_disabled = entry.disabled or entry.disabled_by is not None

            # Check if this key is a dependency key for any sensor
            is_dependency = key in dependency_keys_set

            # Skip polling if entity is disabled unless it is a dependency key
            if is_disabled:
                if is_dependency:
                    _LOGGER.debug("Fetching disabled dependency key '%s'", key)
                else:
                    _LOGGER.debug("Skipping disabled entity '%s'", sensor.get("name", key))
                    continue

            # Determine polling interval for this sensor
            interval_name = sensor.get("scan_interval")
            interval = SCAN_INTERVAL.get(interval_name)

            if interval is None:
                _LOGGER.warning(
                    "%s '%s' has no scan_interval defined, skipping this poll",
                    entity_type,
                    key,
                )
                continue

            # Check when this sensor was last updated and skip if within interval
            last_update = self._last_update_times.get(key)
            elapsed = (now - last_update).total_seconds() if last_update else None

            if elapsed is not None and elapsed < interval:
                _LOGGER.debug(
                    "Skipping %s '%s', last update %.1fs ago (%ds)",
                    entity_type,
                    key,
                    elapsed,
                    interval,
                )
                continue

            # Attempt to read the sensor value from Modbus using helper function
            value = await self.async_read_value(sensor, key)

            if value is not None:
                updated_data[key] = value
                self._last_update_times[key] = now

        # Defensive check
        if self.data is None:
            self.data = {}

        # Update the coordinator's data
        self.data.update(updated_data)
        return self.data
    
