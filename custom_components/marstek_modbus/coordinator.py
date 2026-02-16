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

from .const import DEFAULT_SCAN_INTERVALS, SUPPORTED_VERSIONS, DEFAULT_UNIT_ID

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
        self.message_wait_ms = entry.data.get("message_wait_milliseconds")
        self.timeout = entry.data.get("timeout")
        self.unit_id = entry.data.get("unit_id", DEFAULT_UNIT_ID)

        # Mapping from sensor key to entity type for logging and processing
        self._entity_types: dict[str, str] = {}

        # Store the config entry for potential future use
        self.config_entry = entry

        # Scaling factors for sensors, if applicable
        self._scales: dict[str, float] = {} 

        # Load register/entity definitions for the device version selected in the config entry
        # If device_version is missing (older installs), schedule a reauth flow so the user
        # can pick the correct device version via a popup in the UI. Use a safe default
        # to initialize the coordinator so the integration does not crash while waiting
        # for the user to respond.
        raw_device_version = entry.data.get("device_version", "") or ""
        if not str(raw_device_version).strip():
            # Start a reauth flow so Home Assistant prompts the user to provide the missing value
            try:
                _LOGGER.info(
                    "Config entry %s missing device_version; starting reauth flow",
                    entry.entry_id,
                )
                # Use async_create_task to avoid awaiting in __init__
                self.hass.async_create_task(
                    self.hass.config_entries.async_start_reauth(entry.entry_id)
                )
            except Exception:
                _LOGGER.debug("Failed to start reauth for entry %s", entry.entry_id)

            # Fallback to the first supported version to allow initialization to proceed
            used_version = SUPPORTED_VERSIONS[0]
        else:
            used_version = raw_device_version

        registers = get_registers(used_version)
        self.SENSOR_DEFINITIONS = registers.get("SENSOR_DEFINITIONS", [])
        self.BINARY_SENSOR_DEFINITIONS = registers.get("BINARY_SENSOR_DEFINITIONS", [])
        self.SELECT_DEFINITIONS = registers.get("SELECT_DEFINITIONS", [])
        self.SWITCH_DEFINITIONS = registers.get("SWITCH_DEFINITIONS", [])
        self.NUMBER_DEFINITIONS = registers.get("NUMBER_DEFINITIONS", [])
        self.BUTTON_DEFINITIONS = registers.get("BUTTON_DEFINITIONS", [])
        self.EFFICIENCY_SENSOR_DEFINITIONS = registers.get("EFFICIENCY_SENSOR_DEFINITIONS", [])
        self.STORED_ENERGY_SENSOR_DEFINITIONS = registers.get("STORED_ENERGY_SENSOR_DEFINITIONS", [])

        # Combine all sensor definitions for polling
        self._all_definitions = (
            self.SENSOR_DEFINITIONS
            + self.BINARY_SENSOR_DEFINITIONS
            + self.SELECT_DEFINITIONS
            + self.NUMBER_DEFINITIONS
            + self.SWITCH_DEFINITIONS
        )

        # Initialize Modbus client for communication
        self.client = MarstekModbusClient(
            self.host,
            self.port,
            message_wait_ms=self.message_wait_ms,
            timeout=self.timeout,
            unit_id=self.unit_id,
        )

        # Data storage for sensor values and timestamps of last updates
        self.data: dict = {}
        self._last_update_times: dict = {}
        
        # Connection throttling to prevent endless retry attempts after repeated failures
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._connection_suspended = False
        self._suspension_reset_time = None

        self._consecutive_timeout_cycles = 0
        self._max_consecutive_timeout_cycles = 3
        self._timeout_ratio_reconnect_threshold = 0.5
        
        # Connection health tracking for diagnostics
        self._last_successful_read = None
        self._connection_established_at = None

        # Prepare scan intervals (from config_entry.options or default)
        options = entry.options or {}
        self._update_scan_intervals(options)

        # Initialize the base DataUpdateCoordinator with the calculated interval
        super().__init__(
            hass,
            _LOGGER,
            name="MarstekCoordinator",
            update_interval=self.update_interval,
        )
         
        _LOGGER.debug("Coordinator initialized with update_interval: %s", self.update_interval)

    def _update_scan_intervals(self, options: dict):
        """Update scan intervals from config options and compute update_interval (lowest interval always used)."""
        old_intervals = getattr(self, "scan_intervals", {}).copy() if hasattr(self, "scan_intervals") else {}
        self.scan_intervals = DEFAULT_SCAN_INTERVALS.copy()

        for key in DEFAULT_SCAN_INTERVALS:
            if key in options:
                try:
                    self.scan_intervals[key] = int(options[key])
                except Exception:
                    _LOGGER.warning("Invalid scan interval for %s: %s", key, options[key])

        # Compute minimum interval for coordinator
        min_interval = min(self.scan_intervals.values()) if self.scan_intervals else 30
        self.update_interval = timedelta(seconds=min_interval)

        # Update DataUpdateCoordinator's update_interval if coordinator is already initialized
        if hasattr(self, "_listeners") and self._listeners is not None:
            # update_interval is a property in DataUpdateCoordinator
            try:
                super(MarstekCoordinator, self.__class__).update_interval.fset(self, self.update_interval)
                _LOGGER.debug(
                    "Coordinator update_interval changed dynamically to %s due to options change",
                    self.update_interval,
                )
            except Exception as e:
                _LOGGER.warning("Failed to update coordinator update_interval: %s", e)

        _LOGGER.debug(
            "Scan intervals updated. Old: %s, New: %s, Coordinator update_interval: %s",
            old_intervals,
            self.scan_intervals,
            self.update_interval,
        )


    def register_entity_type(self, key: str, entity_type: str):
        """Register the entity type for a given sensor key.
        For calculated sensors with dependencies, ensure all dependency keys are registered.
        """
        self._entity_types[key] = entity_type

        # Register all dependency keys with entity type and scale
        definition = next((d for d in self.SENSOR_DEFINITIONS if d.get("key") == key), None)
        if definition and "dependency_keys" in definition:
            for dep_alias, dep_key in definition["dependency_keys"].items():
                if dep_key not in self._entity_types:
                    # Use the same entity type as the parent sensor
                    self._entity_types[dep_key] = entity_type

                # Retrieve scale from the dependency sensor definition
                dep_def = next((d for d in self.SENSOR_DEFINITIONS if d.get("key") == dep_key), None)
                if dep_def:
                    scale = dep_def.get("scale")
                    if scale is not None:
                        self._scales[dep_key] = scale

    def get_connection_diagnostics(self) -> dict:
        """Return diagnostic information about the connection."""
        from homeassistant.util.dt import utcnow
        now = utcnow()
        
        diagnostics = {
            "host": self.host,
            "port": self.port,
            "consecutive_failures": self._consecutive_failures,
            "connection_suspended": self._connection_suspended,
            "last_successful_read": self._last_successful_read.isoformat() if self._last_successful_read else None,
            "connection_established_at": self._connection_established_at.isoformat() if self._connection_established_at else None,
        }
        
        if self._connection_suspended and self._suspension_reset_time:
            diagnostics["suspension_expires_in_seconds"] = (self._suspension_reset_time - now).total_seconds()
        
        return diagnostics

    async def async_init(self):
        """Asynchronously initialize the Modbus connection."""
        from homeassistant.util.dt import utcnow
        connected = await self.client.async_connect()
        if not connected:
            _LOGGER.error("Failed to connect to Modbus device at %s:%d", self.host, self.port)
        else:
            self._connection_established_at = utcnow()
            _LOGGER.info("Successfully connected to Modbus device at %s:%d", self.host, self.port)
        return connected

    async def async_read_value(self, sensor: dict, key: str, track_failure: bool = True):
        """Helper to read a single sensor value from Modbus with logging and type checking."""
        entity_type = self._entity_types.get(key, get_entity_type(sensor))

         # Determine scale and unit
        scale = self._scales.get(key, sensor.get("scale", 1))
        unit = sensor.get("unit", "N/A")

        # Guard: ensure client exists
        if not hasattr(self, "client") or self.client is None:
            _LOGGER.error("Modbus client is not available when reading %s '%s'", entity_type, key)
            return None

        try:
            # 10 second timeout for individual reads to prevent hanging
            import asyncio
            value = await asyncio.wait_for(
                self.client.async_read_register(
                    register=sensor["register"],
                    data_type=sensor.get("data_type", "uint16"),
                    count=sensor.get("count", 1),
                    sensor_key=key,
                ),
                timeout=10.0
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

        except asyncio.TimeoutError:
            if track_failure:
                self._timeouts_in_cycle = getattr(self, "_timeouts_in_cycle", 0) + 1
            _LOGGER.warning(
                "Timeout reading %s '%s' at register %d from %s:%d - connection may be slow or incorrect",
                entity_type, key, sensor["register"], self.client.host, self.client.port
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
        # Guard: ensure client exists before attempting write
        if not hasattr(self, "client") or self.client is None:
            _LOGGER.error("Modbus client is not available when writing %s '%s'", entity_type, key)
            return False

        _LOGGER.debug(
            "Writing to %s '%s': register=%d (0x%04X), value=%s",
            entity_type,
            key,
            register,
            register,
            value,
        )

        try:
            success = await self.client.async_write_register(register=register, value=value)
            
            if success:
                _LOGGER.debug(
                    "Successfully wrote to %s '%s': register=%d (0x%04X), value=%s, scale=%s, unit=%s",
                    entity_type,
                    key,
                    register,
                    register,
                    value,
                    scale if scale is not None else 1,
                    unit if unit is not None else "N/A",
                )
                return True
            else:
                _LOGGER.warning(
                    "Write operation failed for %s '%s': register=%d (0x%04X), value=%s",
                    entity_type,
                    key,
                    register,
                    register,
                    value,
                )
                return False
                
        except Exception as e:
            _LOGGER.error(
                "Failed to write value %s to register 0x%X for %s '%s': %s",
                value,
                register,
                entity_type,
                key,
                e
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
        
        # Track if we actually attempted any reads (not just skipped due to intervals)
        attempted_reads = 0
        successful_reads = 0
        self._timeouts_in_cycle = 0

        # Connection throttling: if too many failures, temporarily stop attempting connections
        if self._connection_suspended:
            if self._suspension_reset_time and now > self._suspension_reset_time:
                _LOGGER.info("Connection suspension expired - attempting reconnection")
                self._connection_suspended = False
                self._consecutive_failures = 0

                # Force reconnect after suspension
                try:
                    connected = await self.client.async_reconnect()
                    if connected:
                        _LOGGER.info("Successfully reconnected after suspension")
                    else:
                        _LOGGER.warning("Failed to reconnect after suspension - will retry next cycle")
                        return self.data or {}
                except Exception as exc:
                    _LOGGER.error("Exception during reconnect: %s", exc)
                    return self.data or {}
            else:
                _LOGGER.debug("Connection suspended - skipping update to prevent resource exhaustion")
                return self.data or {}

        _LOGGER.debug("Coordinator poll tick at %s", now.isoformat())

        # Get the entity registry to check for disabled entities
        entity_registry = er.async_get(self.hass)

        # Collect all dependency keys from all definitions
        all_definitions_for_deps = self.EFFICIENCY_SENSOR_DEFINITIONS + self.STORED_ENERGY_SENSOR_DEFINITIONS
        dependency_keys_set = {
            dep_key
            for defn in all_definitions_for_deps
            for dep_key in defn.get("dependency_keys", {}).values()
            if dep_key
        }

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

            # Determine polling interval for this sensor, using self.scan_intervals
            interval_name = sensor.get("scan_interval")
            interval = None
            if interval_name:
                interval = self.scan_intervals.get(interval_name)

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

            # Track that we're attempting a read
            attempted_reads += 1

            # Attempt to read the sensor value from Modbus using helper function
            value = await self.async_read_value(sensor, key)

            if value is not None:
                updated_data[key] = value
                self._last_update_times[key] = now
                successful_reads += 1
            else:
                # Individual sensor read failed
                _LOGGER.warning("Failed to read %s '%s' - value is None", entity_type, key)

        # Connection retry logic: only track failures if we actually attempted reads
        if attempted_reads > 0:
            timeout_reads = int(getattr(self, "_timeouts_in_cycle", 0) or 0)
            if successful_reads > 0:
                # At least some data successfully retrieved - reset failure counter
                if self._consecutive_failures > 0:
                    _LOGGER.info("Connection recovered after %d failures (successful reads: %d/%d)", 
                               self._consecutive_failures, successful_reads, attempted_reads)
                self._consecutive_failures = 0
                self._connection_suspended = False
                self._last_successful_read = now

                if timeout_reads and (timeout_reads / attempted_reads) >= self._timeout_ratio_reconnect_threshold:
                    self._consecutive_timeout_cycles += 1
                    _LOGGER.warning(
                        "High timeout rate detected (%d/%d) - consecutive timeout cycles: %d/%d",
                        timeout_reads,
                        attempted_reads,
                        self._consecutive_timeout_cycles,
                        self._max_consecutive_timeout_cycles,
                    )
                else:
                    self._consecutive_timeout_cycles = 0

                if self._consecutive_timeout_cycles >= self._max_consecutive_timeout_cycles:
                    try:
                        _LOGGER.info(
                            "Attempting reconnect due to repeated timeouts (%d/%d cycles)",
                            self._consecutive_timeout_cycles,
                            self._max_consecutive_timeout_cycles,
                        )
                        connected = await self.client.async_reconnect()
                        if connected:
                            _LOGGER.info("Successfully reconnected after repeated timeouts")
                            self._consecutive_timeout_cycles = 0
                            self._connection_established_at = now
                        else:
                            _LOGGER.warning("Reconnect attempt after repeated timeouts failed")
                    except Exception as exc:
                        _LOGGER.error("Exception during reconnect after repeated timeouts: %s", exc)
            elif successful_reads == 0:
                # We attempted reads but ALL failed - connection issue
                self._consecutive_failures += 1
                _LOGGER.warning("All read attempts failed (%d/%d) - consecutive failures: %d/%d",
                              successful_reads, attempted_reads, 
                              self._consecutive_failures, self._max_consecutive_failures)
                self._consecutive_timeout_cycles = 0
                
                # Try to reconnect immediately on failure
                try:
                    _LOGGER.info("Attempting immediate reconnection after read failures")
                    connected = await self.client.async_reconnect()
                    if connected:
                        _LOGGER.info("Successfully reconnected")
                        self._consecutive_failures = 0
                        self._connection_established_at = now
                    else:
                        _LOGGER.warning("Immediate reconnection failed")
                except Exception as exc:
                    _LOGGER.error("Exception during immediate reconnect: %s", exc)
                
                if self._consecutive_failures >= self._max_consecutive_failures:
                    # Too many failures - suspend connection attempts for 5 minutes
                    self._connection_suspended = True
                    self._suspension_reset_time = now + timedelta(minutes=5)
                    _LOGGER.error(
                        "Connection suspended after %d consecutive failures. "
                        "Will retry in 5 minutes to prevent resource exhaustion.",
                        self._consecutive_failures
                    )
        else:
            _LOGGER.debug("No sensors due for update in this cycle")
            self._consecutive_timeout_cycles = 0

        # Defensive check
        if self.data is None:
            self.data = {}

        # Update the coordinator's data
        self.data.update(updated_data)
        return self.data
    

    async def async_close(self):
        """Close the Modbus client connection cleanly."""
        try:
            await self.client.async_close()
            _LOGGER.debug("Closed Modbus connection to %s:%d", self.host, self.port)
        except Exception as e:
            _LOGGER.warning("Error closing Modbus client: %s", e)


def get_registers(version: str):
    """
    Return a dict with entity/register definitions for the given device version.

    The returned dict contains the keys:
      - SENSOR_DEFINITIONS
      - BINARY_SENSOR_DEFINITIONS
      - SELECT_DEFINITIONS
      - SWITCH_DEFINITIONS
      - NUMBER_DEFINITIONS
      - BUTTON_DEFINITIONS
      - EFFICIENCY_SENSOR_DEFINITIONS
      - STORED_ENERGY_SENSOR_DEFINITIONS

    If an unknown version is requested, the function falls back to the v1/v2
    register set (because v1 and v2 share the same registers in this integration).
    """
    # Normalize incoming version value and accept legacy tokens.
    version_raw = (version or "").strip()
    version = version_raw.lower()

    # Accept legacy tokens 'v1/v2' and 'v3' and automatically map them
    # to the new tokens used by the integration ('e v1/v2', 'e v3').
    legacy_to_new = {
        "v1/v2": "e v1/v2",
        "v3": "e v3",
    }
    if version in legacy_to_new:
        mapped = legacy_to_new[version]
        _LOGGER.info(
            "Mapping legacy device version '%s' to '%s' for backwards compatibility",
            version_raw,
            mapped,
        )
        version = mapped

    # Validate against supported versions (case-insensitive)
    allowed = {str(item).lower() for item in SUPPORTED_VERSIONS}
    if version not in allowed:
        raise ValueError(
            "Unsupported or missing device version %r. Supported versions: %s"
            % (version_raw, ", ".join(sorted(allowed)))
        )

    # Map the validated version token to the correct registers module.
    # Support the new tokens 'e v1/v2' and 'e v3'.
    if version == "e v1/v2":
        from . import registers_v12 as registers
    elif version == "e v3":
        from . import registers_v3 as registers
    elif version == "d":
        from . import registers_v12 as registers
        
    return {
        "SENSOR_DEFINITIONS": getattr(registers, "SENSOR_DEFINITIONS", []),
        "BINARY_SENSOR_DEFINITIONS": getattr(registers, "BINARY_SENSOR_DEFINITIONS", []),
        "SELECT_DEFINITIONS": getattr(registers, "SELECT_DEFINITIONS", []),
        "SWITCH_DEFINITIONS": getattr(registers, "SWITCH_DEFINITIONS", []),
        "NUMBER_DEFINITIONS": getattr(registers, "NUMBER_DEFINITIONS", []),
        "BUTTON_DEFINITIONS": getattr(registers, "BUTTON_DEFINITIONS", []),
        "EFFICIENCY_SENSOR_DEFINITIONS": getattr(registers, "EFFICIENCY_SENSOR_DEFINITIONS", []),
        "STORED_ENERGY_SENSOR_DEFINITIONS": getattr(registers, "STORED_ENERGY_SENSOR_DEFINITIONS", []),
    }